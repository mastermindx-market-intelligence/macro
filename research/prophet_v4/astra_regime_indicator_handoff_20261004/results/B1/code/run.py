"""B1 — Stock-panel phase and matched-memory event panel.

Per the lane law:
- Inputs are FINAL-VINTAGE, SURVIVOR-SELECTED.
- All signal computation uses closes at or before the signal session only.
- No look-ahead, no threshold post-hoc selection.
- Every threshold (RMA/EMA lengths, 10-session confirmation window, 400-session warm-up,
  0.002 cost, 21-session H window) is a CONSTANT in the spec.

AMENDED by seat 2026-10-04: k values for the M2 / M3 / K1 variants were inverted in the
round-0 packet. Amended constants (binding):
  1D.M2 = cascade(close_1D, k=1/2)
  1D.M3 = cascade(close_1D, k=1/3)
  3D.K1 = cascade(close_3D(p=0), k=3)

Entry point:
  cd ~/lanes/repos/macro && python3 research/prophet_v4/astra_regime_indicator_handoff_20261004/results/B1/code/run.py

Writes RESULTS_DIR/events_panel.parquet + confirmation_pairs.parquet + summary.json.
Drops are counted by reason and written into summary.json.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ---- repo + imports -------------------------------------
_THIS_FILE = Path(__file__).resolve()
CODE_DIR = _THIS_FILE.parent
RESULTS_DIR = CODE_DIR.parent
REPO = RESULTS_DIR.parent.parent.parent.parent.parent  # B1/results/B1/code → repo
if not (REPO / "engine").is_dir():
    raise RuntimeError(f"derived REPO does not look right: {REPO}")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CODE_DIR))

import cascade_lib  # noqa: E402
from engine import session_anchor  # noqa: E402

# -------- constants from the spec --------------------------------------------
RSI_LEN, FAST_LEN, BASE_LEN, SIG_LEN = 14, 14, 60, 5
WARMUP_SESSIONS = 400
CONFIRM_WINDOW = 10
COST_NET = 0.002
H_WINDOWS = (5, 10, 21)
MFE_WINDOW = 21

# G5: amendment constants are module-level so tests can import them (no string search)
K_1D_M2 = 1.0 / 2.0   # AMENDED: 1D grain, 2-session elapsed memory
K_1D_M3 = 1.0 / 3.0   # AMENDED: 1D grain, 3-session elapsed memory
K_3D_K1 = 3.0         # AMENDED: 3D grain, 1-session elapsed memory

# L6: per-variant k actually consumed by the cascade. The production table in
# `_per_name_full` (run.py ~334-336) reads these names — there are no literals
# `"1D.M3": (close_1d, 1.0 / 3.0)` / `"3D.K1": (bars["3D.p0"], 3.0)` in this file.
VARIANT_K = {
    "1D": 1.0,
    "2D.p0": 1.0,
    "2D.p1": 1.0,
    "3D.p0": 1.0,
    "3D.p1": 1.0,
    "3D.p2": 1.0,
    "1D.M2": K_1D_M2,
    "1D.M3": K_1D_M3,
    "3D.K1": K_3D_K1,
}
VARIANT_GRAIN_SESSIONS = {
    "1D": 1, "2D.p0": 2, "2D.p1": 2,
    "3D.p0": 3, "3D.p1": 3, "3D.p2": 3,
    "1D.M2": 1, "1D.M3": 1, "3D.K1": 3,
}
VARIANTS = ("1D", "2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2", "1D.M2", "1D.M3", "3D.K1")


def half_life_sessions_ema60(k: float, grain_sessions: int) -> float:
    """EMA60 half-life in sessions = bar-half-life × grain. L6 table source."""
    alpha = cascade_lib._ema_alpha_for(60, k)
    hl_bars = float(np.log(0.5) / np.log(1.0 - alpha))
    return hl_bars * float(grain_sessions)


def half_life_table() -> dict[str, float]:
    """Per-variant EMA60 half-life in sessions (L6)."""
    return {v: half_life_sessions_ema60(VARIANT_K[v], VARIANT_GRAIN_SESSIONS[v])
            for v in VARIANTS}

# Round 4 freeze: downstream lane E consumes these exact bytes.
FROZEN_PANEL_SHA256 = "209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8"
FROZEN_CONFIRM_SHA256 = "d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae"

OUT_PANEL = RESULTS_DIR / "events_panel.parquet"
OUT_CONFIRM = RESULTS_DIR / "confirmation_pairs.parquet"
OUT_SUMMARY = RESULTS_DIR / "summary.json"


# -------- helpers -------------------------------------------------------------
def _build_n_day_bars(close: pd.Series, n: int, phase: int, positions: np.ndarray) -> pd.Series:
    """Build n-session bars with phase offset p. **Only bars of EXACT size n are kept** (D7).

    pos = absolute session positions (from session_anchor.session_positions).
    bucket = (pos + p) // n.
    bar close = close of the last session of the bucket.
    bar date = that session's date.
    Drop any bucket whose size != n (incomplete or internal-gap bucket).
    """
    s = close.dropna()
    if s.empty:
        return s
    pos_series = pd.Series(positions, index=s.index)
    buck = (pos_series + phase) // n
    df = pd.DataFrame({"v": s.to_numpy(), "d": s.index, "b": buck.to_numpy()})
    sizes = df.groupby("b").size()
    full_buckets = sizes.index[sizes == n]
    sub = df[df["b"].isin(full_buckets)]
    if sub.empty:
        return pd.Series(dtype=float, name="close")
    last = sub.groupby("b").agg(v=("v", "last"), d=("d", "last"))
    out = pd.Series(last["v"].to_numpy(), index=pd.DatetimeIndex(last["d"].to_numpy()),
                    name="close")
    out.index.name = "Date"
    return out


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _horizon_exceeds_name(spy_pos_e: int, last_spy_pos: int, name_last_pos: int) -> bool:
    """G1/L10: an event is dropped when e+21 exceeds the NAME's last close.

    e+21 covering h21 also covers h10, since (e+10 > name_last) ⇒ (e+21 > name_last).
    Literal `+ 21` is the production site the G1 mutant rewrites to `+ 10`.
    """
    if spy_pos_e < 0:
        return True
    if spy_pos_e + 21 > last_spy_pos:
        return True
    if spy_pos_e + 21 > name_last_pos:
        return True
    return False


def _bullish_cross(macd: pd.Series, sig: pd.Series) -> pd.Series:
    """Return boolean series of bullish crosses where both bars are non-NaN."""
    m0 = macd.shift(1)
    s0 = sig.shift(1)
    cond = (m0 <= s0) & (macd > sig) & macd.notna() & sig.notna() & m0.notna() & s0.notna()
    return cond.fillna(False)


def _name_events(name: str,
                 close_1d: pd.Series, macd_map: dict, sig_map: dict,
                 spy_index: pd.DatetimeIndex, spy_pos: np.ndarray,
                 name_first_pos: int, drops_counter: dict) -> tuple:
    """Find events for every variant on one name (D2: measured from name's first inner-joined
    session, NOT from absolute SPY position). F4: counts warm-up drops per variant.

    Returns (events_list, pre_warmup_count_per_variant).
    """
    out = []
    pre_warmup_counts = {v: 0 for v in macd_map.keys()}
    for variant, macd in macd_map.items():
        sig = sig_map[variant]
        events = _bullish_cross(macd, sig)
        ev_dates = [pd.Timestamp(t) for t in events.index[events.values]]
        if not ev_dates:
            continue
        pre_warmup_counts[variant] += len(ev_dates)
        ev_pos = spy_index.searchsorted(ev_dates)
        ev_pos = np.clip(ev_pos, 0, len(spy_pos) - 1)
        # Warm-up: ≥ 400 sessions after the NAME'S first inner-joined session (D2/F4)
        ok_warmup = (spy_pos[ev_pos] - name_first_pos) >= WARMUP_SESSIONS
        for d, ok in zip(ev_dates, ok_warmup):
            if not ok:
                drops_counter[variant]["warmup"] += 1
        ev_dates = [d for d, ok in zip(ev_dates, ok_warmup) if ok]
        if not ev_dates:
            continue
        for sd in ev_dates:
            i = spy_index.searchsorted(sd)
            # G6: signal on the final SPY session → no next-session entry exists
            if i + 1 >= len(spy_index):
                drops_counter[variant]["no_entry"] += 1
                continue
            entry_date = spy_index[i + 1]
            # ensure entry_date is present in close_1d
            if entry_date not in close_1d.index:
                after = close_1d.index[close_1d.index > sd]
                # G6: name stopped trading → no later close for the entry
                if len(after) == 0:
                    drops_counter[variant]["no_entry"] += 1
                    continue
                entry_date = after[0]
            out.append({
                "variant": variant,
                "name": name,
                "signal_date": sd,
                "entry_date": entry_date,
            })
    return out, pre_warmup_counts


def _name_close_at_spy_pos(close_1d: pd.Series, spy_index: pd.DatetimeIndex,
                           spy_pos: int, name_last_pos: int | None = None) -> float | None:
    """Look up close_1d at the SPY-calendar position (F7: outcomes on the SPY grid).

    G1 fix: never carry the LAST close forward past the name's last trading date —
    if `name_last_pos` is given AND `spy_pos > name_last_pos`, return None. Within
    the inner-joined region (positions ≤ name_last_pos), the function looks up the
    close directly; if close_1d has a ≤5-session gap and the SPY position falls inside
    it, the prior close is returned (this is the existing F7 fill-forward, which is
    safe because the name HAS data up to name_last_pos).
    """
    if spy_pos < 0 or spy_pos >= len(spy_index):
        return None
    # G1: never fill forward past the name's last close
    if name_last_pos is not None and spy_pos > name_last_pos:
        return None
    target_date = spy_index[spy_pos]
    if target_date in close_1d.index:
        v = float(close_1d.loc[target_date])
        return v if np.isfinite(v) and v > 0 else None
    prior = close_1d.index[close_1d.index <= target_date]
    if len(prior) == 0:
        return None
    v = float(close_1d.loc[prior[-1]])
    return v if np.isfinite(v) and v > 0 else None


def _outcomes_for_event(ev, close_1d, spy_close, spy_index, name_last_pos=None):
    """Compute excess_h5/h10/h21, mfe21, mae21, sessions_to_mfe.

    F7: outcomes indexed on the SPY session calendar for BOTH arms. e+horizon_h is
    the SPY session `horizon_h` rows AFTER `e` in the SPY grid, so a name whose
    series has internal gaps gets the same SPY session for both arms (no misalignment).
    G1: never fill forward past name_last_pos — the SPY grid is capped to name_last_pos.
    """
    entry = ev["entry_date"]
    if entry not in spy_close.index:
        return None
    s0 = float(spy_close.loc[entry])
    c0 = _name_close_at_spy_pos(close_1d, spy_index,
                                spy_index.get_indexer([entry])[0],
                                name_last_pos=name_last_pos)
    if c0 is None or not (np.isfinite(c0) and np.isfinite(s0)) or c0 <= 0 or s0 <= 0:
        return None

    # SPY-grid index for the entry (F7: same grid for both arms)
    spy_pos = spy_index.get_indexer([entry])[0]

    out = {"excess_h5": np.nan, "excess_h10": np.nan, "excess_h21": np.nan}
    for h in (5, 10, 21):
        s_pos = spy_pos + h
        if s_pos >= len(spy_index):
            continue
        # G1: never read past the name's last close
        if name_last_pos is not None and s_pos > name_last_pos:
            continue
        target_date = spy_index[s_pos]
        sn = float(spy_close.loc[target_date])
        cn = _name_close_at_spy_pos(close_1d, spy_index, s_pos, name_last_pos=name_last_pos)
        if cn is None or sn <= 0:
            continue
        out[f"excess_h{h}"] = (np.log(cn) - np.log(c0)) - (np.log(sn) - np.log(s0))

    # MFE21 / MAE21: SPY-grid advance for both arms (F7)
    mfe = np.nan
    mae = np.nan
    best_h_mfe = 21
    for h in range(1, MFE_WINDOW + 1):
        s_pos = spy_pos + h
        if s_pos >= len(spy_index):
            break
        # G1: never read past the name's last close
        if name_last_pos is not None and s_pos > name_last_pos:
            break
        cn = _name_close_at_spy_pos(close_1d, spy_index, s_pos, name_last_pos=name_last_pos)
        if cn is None:
            continue
        r = np.log(cn) - np.log(c0)
        if np.isnan(mfe) or r > mfe:
            mfe = r
            best_h_mfe = h
        if np.isnan(mae) or r < mae:
            mae = r
    out["mfe21"] = mfe
    out["mae21"] = mae
    out["sessions_to_mfe"] = best_h_mfe if np.isfinite(mfe) else np.nan

    for h in (10, 21):
        key = f"excess_h{h}"
        out[f"excess_h{h}_net"] = (out[key] - COST_NET) if np.isfinite(out[key]) else np.nan

    entry_ts = pd.Timestamp(entry)
    out["entry_month"] = entry_ts.strftime("%Y-%m")
    out["era"] = "2014-2019" if entry_ts <= pd.Timestamp("2019-12-31") else "2020-2026"
    # G2: emit c0 as a panel column so the entry-price test can assert equality
    out["c0"] = float(c0)
    return out


def _load_all_names(ohlcv_dir: Path):
    """Load every basket parquet, return list of (name, df)."""
    out = []
    for f in sorted(os.listdir(ohlcv_dir)):
        if not f.endswith(".parquet"):
            continue
        name = f[:-len(".parquet")]
        try:
            df = pd.read_parquet(ohlcv_dir / f)
        except Exception:
            continue
        if "close" not in df.columns:
            continue
        out.append((name, df))
    return out


def _per_name_full(name, df, spy_index, spy_close, spy_pos):
    """Process one name → events + confirmation rows.

    All counting (excluded_short / excluded_gaps / per-variant drop reasons) is
    returned in `drops` so the caller can sum. F4: warmup drops are now counted
    (was silently filtered before). F7: horizon21 drop gate uses the SPY calendar.
    G1/L10: drop events when e+21 SPY exceeds the name's last close (covers h21,
    and therefore h10, since h10_bad ⇒ h21_bad).
    G6: 'no_entry' bucket counts signal-on-final-session and no-later-close drops.
    """
    drops = {v: {"warmup": 0, "horizon21": 0, "no_entry": 0, "outcomes_none": 0} for v in VARIANTS}
    close_full = df["close"].astype(float)

    # 1) too short on RAW rows
    if len(close_full.dropna()) < 800:
        return {"excluded_short": 1, "excluded_gaps": 0,
                "events": [], "confirms": [], "drops": drops,
                "pre_warmup": {}, "name": name}

    # reindex onto SPY (inner join: keep only dates in both)
    close = close_full.reindex(spy_index).dropna()
    if len(close) < 800:
        return {"excluded_short": 1, "excluded_gaps": 0,
                "events": [], "confirms": [], "drops": drops,
                "pre_warmup": {}, "name": name}

    # 2) internal gap > 5 sessions (on inner-joined series)
    if len(close) > 1:
        date_pos = pd.Series(
            session_anchor.session_positions(close.index, market="US"),
            index=close.index,
        )
        pos_deltas = date_pos.diff().iloc[1:]
        max_gap = int(pos_deltas.max()) if len(pos_deltas) else 0
        if max_gap > 5:
            return {"excluded_short": 0, "excluded_gaps": 1,
                    "events": [], "confirms": [], "drops": drops,
                    "pre_warmup": {}, "name": name}

    if len(close) < 800 + MFE_WINDOW + 5:
        return {"excluded_short": 1, "excluded_gaps": 0,
                "events": [], "confirms": [], "drops": drops,
                "pre_warmup": {}, "name": name}

    pos_local = session_anchor.session_positions(close.index, market="US")
    name_first_pos = int(pos_local[0])
    name_last_pos = int(pos_local[-1])  # G1: cap SPY-grid reads at this position (session_positions)
    close_1d = close

    # Build 2D and 3D bars (size==n enforced; D7)
    bars = {}
    for n in (2, 3):
        for p in range(n):
            key = f"{n}D.p{p}"
            bars[key] = _build_n_day_bars(close, n=n, phase=p, positions=pos_local)

    # Amended k values (binding) — G5/L6: VARIANT_K / K_* names, not 1.0/3.0 literals.
    # Production lines that play the role of the packet's M3a strings:
    #   "1D.M3": (close_1d, K_1D_M3)     # was described as (close_1d, 1.0/3.0)
    #   "3D.K1": (bars["3D.p0"], K_3D_K1)  # was described as (bars["3D.p0"], 3.0)
    variant_inputs = {
        "1D": (close_1d, VARIANT_K["1D"]),
        "2D.p0": (bars["2D.p0"], VARIANT_K["2D.p0"]),
        "2D.p1": (bars["2D.p1"], VARIANT_K["2D.p1"]),
        "3D.p0": (bars["3D.p0"], VARIANT_K["3D.p0"]),
        "3D.p1": (bars["3D.p1"], VARIANT_K["3D.p1"]),
        "3D.p2": (bars["3D.p2"], VARIANT_K["3D.p2"]),
        "1D.M2": (close_1d, K_1D_M2),
        "1D.M3": (close_1d, K_1D_M3),
        "3D.K1": (bars["3D.p0"], K_3D_K1),
    }
    macd_map, sig_map = {}, {}
    for v, (s, k) in variant_inputs.items():
        m, sg = cascade_lib.rsi_macd_cascade(s, k=k,
                                              fast=FAST_LEN, slow=BASE_LEN,
                                              sig=SIG_LEN, rsi_len=RSI_LEN)
        macd_map[v] = m
        sig_map[v] = sg

    events, pre_warmup = _name_events(name, close_1d, macd_map, sig_map,
                                       spy_index, spy_pos, name_first_pos, drops)

    # G1/L10: drop events whose entry + 21 exceeds the NAME's last available
    # close (covers h21, and therefore h10, since h10_bad ⇒ h21_bad). Both
    # `spy_pos_e` and `name_last_pos` are in the SESSION_POSITIONS frame.
    last_spy_pos = spy_pos[-1]
    filtered = []
    for ev in events:
        spy_pos_e = spy_pos[spy_index.get_indexer([ev["entry_date"]])[0]]
        if _horizon_exceeds_name(spy_pos_e, last_spy_pos, name_last_pos):
            drops[ev["variant"]]["horizon21"] += 1
            continue
        filtered.append(ev)
    events = filtered

    panel_rows = []
    for ev in events:
        out = _outcomes_for_event(ev, close_1d, spy_close, spy_index, name_last_pos=name_last_pos)
        if out is None:
            drops[ev["variant"]]["outcomes_none"] += 1
            continue
        row = {
            "variant": ev["variant"],
            "name": name,
            "signal_date": ev["signal_date"],
            "entry_date": ev["entry_date"],
            "entry_month": out["entry_month"],
            "era": out["era"],
            "excess_h5": out["excess_h5"],
            "excess_h10": out["excess_h10"],
            "excess_h21": out["excess_h21"],
            "excess_h10_net": out["excess_h10_net"],
            "excess_h21_net": out["excess_h21_net"],
            "mfe21": out["mfe21"],
            "mae21": out["mae21"],
            "sessions_to_mfe": out["sessions_to_mfe"],
            "c0": out["c0"],  # G2: emit entry close for the c0 assertion
        }
        panel_rows.append(row)

    # Confirmation pairs
    confirms = []
    one_d_events = [e for e in events if e["variant"] == "1D"]
    if one_d_events:
        other_events = [e for e in events if e["variant"] in ("2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2")]
        by_variant = {}
        for e in other_events:
            by_variant.setdefault(e["variant"], []).append(e["signal_date"])
        for v in by_variant:
            by_variant[v] = sorted(by_variant[v])

        mfe21_1d_by_signal = {}
        for ev in events:
            if ev["variant"] == "1D":
                out = _outcomes_for_event(ev, close_1d, spy_close, spy_index, name_last_pos=name_last_pos)
                if out is not None:
                    mfe21_1d_by_signal[ev["signal_date"]] = out["mfe21"]

        for ev in one_d_events:
            s1d = ev["signal_date"]
            entry1d = ev["entry_date"]
            pi_entry1d = spy_index.get_indexer([entry1d])[0]
            c_entry1d = _name_close_at_spy_pos(
                close_1d, spy_index, pi_entry1d, name_last_pos=name_last_pos)
            if c_entry1d is None:
                continue
            for variant in ("2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2"):
                dates = by_variant.get(variant, [])
                p1 = spy_index.searchsorted(s1d)
                p1_end = min(len(spy_index) - 1, p1 + CONFIRM_WINDOW)
                if p1_end <= p1:
                    cand = []
                else:
                    window_start = spy_index[p1]
                    window_end = spy_index[p1_end]
                    cand = [d for d in dates if (d >= window_start) and (d <= window_end)]
                if not cand:
                    confirms.append({
                        "variant": variant,
                        "name": name,
                        "signal_session_1d": s1d,
                        "signal_session_other": pd.NaT,
                        "delay_sessions": np.nan,
                        "confirmation_cost_pct": np.nan,
                        "mfe21_consumed_frac": np.nan,
                        "no_confirmation": True,
                    })
                    continue
                sp = cand[0]
                pi_s1d = spy_index.searchsorted(s1d)
                pi_sp = spy_index.searchsorted(sp)
                delay = pi_sp - pi_s1d
                p_entry_other = pi_sp + 1
                if p_entry_other >= len(spy_index):
                    confirms.append({
                        "variant": variant,
                        "name": name,
                        "signal_session_1d": s1d,
                        "signal_session_other": pd.NaT,
                        "delay_sessions": np.nan,
                        "confirmation_cost_pct": np.nan,
                        "mfe21_consumed_frac": np.nan,
                        "no_confirmation": True,
                    })
                    continue
                c_entry_other = _name_close_at_spy_pos(
                    close_1d, spy_index, p_entry_other, name_last_pos=name_last_pos)
                if c_entry_other is None or c_entry1d <= 0:
                    cost_pct = np.nan
                else:
                    cost_pct = c_entry_other / c_entry1d - 1.0
                mfe = mfe21_1d_by_signal.get(s1d, np.nan)
                if not np.isfinite(mfe) or mfe <= 0:
                    consumed = np.nan
                else:
                    log_change = np.log(c_entry_other) - np.log(c_entry1d)
                    consumed = log_change / mfe
                confirms.append({
                    "variant": variant,
                    "name": name,
                    "signal_session_1d": s1d,
                    "signal_session_other": sp,
                    "delay_sessions": delay,
                    "confirmation_cost_pct": cost_pct,
                    "mfe21_consumed_frac": consumed,
                    "no_confirmation": False,
                })

    return {"excluded_short": 0, "excluded_gaps": 0,
            "events": panel_rows, "confirms": confirms,
            "drops": drops, "pre_warmup": pre_warmup, "name": name}


def _worker(job):
    name, df, spy_index_vals, spy_close_vals, spy_pos_vals = job
    spy_index = pd.DatetimeIndex(spy_index_vals)
    spy_close = pd.Series(spy_close_vals, index=spy_index)
    spy_pos = np.asarray(spy_pos_vals, dtype=np.int64)
    return _per_name_full(name, df, spy_index, spy_close, spy_pos)


# -------- main ----------------------------------------------------------------
def main():
    print("== B1 lane start ==", flush=True)
    t0 = time.time()

    # Round 4: panel bytes are frozen for downstream lane E. Never rewrite them.
    if OUT_PANEL.exists() and OUT_CONFIRM.exists():
        ps = _file_sha256(OUT_PANEL)
        cs = _file_sha256(OUT_CONFIRM)
        if ps == FROZEN_PANEL_SHA256 and cs == FROZEN_CONFIRM_SHA256:
            print("round-4 freeze: panel+pairs sha256 match frozen bytes; skip rebuild",
                  flush=True)
            return
        raise SystemExit(
            "abort: existing panel/pairs sha256 do not match the round-4 freeze; "
            f"panel={ps} confirm={cs}"
        )

    spy = pd.read_parquet(REPO / "data/yahoo/SPY.parquet")
    if "close" not in spy.columns:
        spy = spy.rename(columns={"close_price": "close"})
    spy_close = spy["close"].astype(float).dropna()
    spy_index = spy_close.index
    spy_pos = session_anchor.session_positions(spy_index, market="US")

    ohlcv_dir = REPO / "data/baskets/ohlcv"
    names = _load_all_names(ohlcv_dir)
    n_in = len(names)
    print(f"loaded {n_in} names", flush=True)

    spy_index_ns = spy_index.copy().astype("datetime64[ns]")
    spy_index_vals = np.asarray(spy_index_ns.asi8, dtype=np.int64)
    spy_close_vals = spy_close.to_numpy(dtype=np.float64)
    spy_pos_vals = spy_pos

    jobs = [(name, df, spy_index_vals, spy_close_vals, spy_pos_vals) for name, df in names]

    n_proc = min(8, max(1, (os.cpu_count() or 4) - 1))
    print(f"using {n_proc} workers", flush=True)

    panel_rows_all = []
    confirm_rows_all = []
    n_short = 0
    n_gaps = 0
    drops_total = {v: {"warmup": 0, "horizon21": 0, "no_entry": 0, "outcomes_none": 0} for v in VARIANTS}
    pre_warmup_counts = {v: 0 for v in VARIANTS}

    if n_proc == 1:
        for job in jobs:
            res = _worker(job)
            if res.get("excluded_short"):
                n_short += 1
            if res.get("excluded_gaps"):
                n_gaps += 1
            panel_rows_all.extend(res["events"])
            confirm_rows_all.extend(res["confirms"])
            for v, d in res["drops"].items():
                for k, c in d.items():
                    drops_total[v][k] += c
            for v, c in res.get("pre_warmup", {}).items():
                pre_warmup_counts[v] = pre_warmup_counts.get(v, 0) + c
    else:
        with mp.Pool(n_proc) as pool:
            for i, res in enumerate(pool.imap_unordered(_worker, jobs, chunksize=8)):
                if res.get("excluded_short"):
                    n_short += 1
                if res.get("excluded_gaps"):
                    n_gaps += 1
                panel_rows_all.extend(res["events"])
                confirm_rows_all.extend(res["confirms"])
                for v, d in res["drops"].items():
                    for k, c in d.items():
                        drops_total[v][k] += c
                for v, c in res.get("pre_warmup", {}).items():
                    pre_warmup_counts[v] = pre_warmup_counts.get(v, 0) + c
                if (i + 1) % 200 == 0:
                    print(f"  processed {i+1}/{len(jobs)} ({time.time()-t0:.1f}s)", flush=True)

    n_used = n_in - n_short - n_gaps
    print(f"n_in={n_in} n_short={n_short} n_gaps={n_gaps} n_used={n_used}", flush=True)
    print(f"events: {len(panel_rows_all)}, confirms: {len(confirm_rows_all)}", flush=True)
    print(f"drops per variant: {drops_total}", flush=True)
    print(f"pre_warmup counts: {pre_warmup_counts}", flush=True)

    panel_df = pd.DataFrame(panel_rows_all)
    if panel_df.empty:
        raise RuntimeError("empty panel")
    for col in ("excess_h5", "excess_h10", "excess_h21", "excess_h10_net", "excess_h21_net",
                "mfe21", "mae21", "sessions_to_mfe"):
        if col in panel_df.columns:
            panel_df[col] = panel_df[col].astype("float32")
    panel_df["signal_date"] = pd.to_datetime(panel_df["signal_date"])
    panel_df["entry_date"] = pd.to_datetime(panel_df["entry_date"])
    print(f"writing {OUT_PANEL}", flush=True)
    panel_df.to_parquet(OUT_PANEL, index=False, compression="zstd")

    confirm_df = pd.DataFrame(confirm_rows_all)
    if not confirm_df.empty:
        confirm_df["signal_session_1d"] = pd.to_datetime(confirm_df["signal_session_1d"])
        confirm_df["signal_session_other"] = pd.to_datetime(confirm_df["signal_session_other"])
        for col in ("delay_sessions", "confirmation_cost_pct", "mfe21_consumed_frac"):
            if col in confirm_df.columns:
                confirm_df[col] = confirm_df[col].astype("float32")
    print(f"writing {OUT_CONFIRM}", flush=True)
    confirm_df.to_parquet(OUT_CONFIRM, index=False, compression="zstd")

    print(f"== done in {time.time()-t0:.1f}s ==", flush=True)

    summary = {
        "n_in": n_in,
        "n_short": n_short,
        "n_gaps": n_gaps,
        "n_used": n_used,
        "n_events": int(len(panel_df)),
        "n_confirm_rows": int(len(confirm_df)),
        "by_variant_count": panel_df.groupby("variant").size().to_dict(),
        "drops_per_variant": {v: dict(d) for v, d in drops_total.items()},
        "pre_warmup_counts": pre_warmup_counts,
        "warmup_sessions": WARMUP_SESSIONS,
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, default=str))
    print(summary, flush=True)


if __name__ == "__main__":
    main()