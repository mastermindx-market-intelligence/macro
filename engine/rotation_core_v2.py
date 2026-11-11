"""Rotation Core v2 — two-key defensive-rotation evaluation on Ken French 49 industries (corrected v1 engine).

Implements protocol_header_v2 (draft rev 7; the frozen JSON governs once it exists). Pure functions; research only.
Nothing here sizes, gates, ranks, alerts or trades.

Seal: any input path under `sealed_post2019/` is refused unless research/rotation_core/HOLDOUT_RELEASE_v2.json is
committed and clean; every loader also truncates at the caller's `end` before computing anything.
"""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from engine import rotation_core_evaluation as rc

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "research/rotation_core/HOLDOUT_RELEASE_v2.json"
SEALED_MARK = "sealed_post2019"
FROZEN_V2_SHA256 = "ca5af27429b54df534e959bde8a3db037c95f7fe5c7c430fe7e6bb5b03d01728"
HEADER_V2 = ROOT / "research/rotation_core/protocol_header_v2.json"
GRID = [(3, 25.0), (3, 37.5), (5, 25.0), (5, 37.5)]


def verify_header_v2(path=HEADER_V2, expected: str = FROZEN_V2_SHA256) -> dict:
    """Refuse any header bytes other than the frozen v2 header."""
    import hashlib, json
    raw = Path(path).read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != expected:
        raise rc.HeaderMismatch(f"protocol header v2 sha256 {got} != frozen {expected}")
    return json.loads(raw)      # (h near-high %, b breadth-drop pp)
FEE_INDUSTRY_BP = 10.0
FEE_FUND_BP = 5.0


class SealedRefusal(PermissionError):
    pass


RELEASE2 = ROOT / "research/rotation_core/HOLDOUT_RELEASE_v2_stage2.json"
W_PRE = "pre1998_1928_1997"
W_H = "2020-01-02..2025-12-31"
PRE_END = pd.Timestamp("1997-12-31")
H_START, H_END = pd.Timestamp("2020-01-02"), pd.Timestamp("2025-12-31")


def _committed_clean(path: Path) -> bool:
    try:
        rel = str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return False                                   # outside the repo: never counts as committed
    try:
        subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return False
    out = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", rel], capture_output=True).stdout
    return out.strip() == b""


def _load_release(path: Path) -> dict | None:
    import json
    if not (Path(path).exists() and _committed_clean(path)):
        return None
    return json.loads(Path(path).read_text())


SELECTION_RESULT = ROOT / "research/rotation_core/results_v2_selection_rerun.json"   # R15: rerun pins the setting
SELECTED_REF = (3.0, 25.0)            # grid point selected at 1ca5228b3c (R13-g(i)); R14(d) sensitivity uses it
SEALED_STAGE1_DIR = Path("/home/ubuntu2/tmp/rotation-core/data/sealed_stage1")
STAGE1_SEALED = SEALED_STAGE1_DIR / "results_v2_stage1_pre1998.json"
STAGE1_GATE = ROOT / "research/rotation_core/results_v2_stage1_gate.json"


def selected_setting(selection: Path | None = None) -> tuple[float, float]:
    """R13-g(i)/R15.6: the gate setting is read from the committed selection result (the R15 rerun), never from
    an argument."""
    import json, re
    selection = SELECTION_RESULT if selection is None else selection
    if not _committed_clean(selection):
        raise SealedRefusal("refused: selection result is not committed")
    sel = json.loads(Path(selection).read_text())["selection"]["selected"]
    m = re.fullmatch(r"h(\d+)_b([\d.]+)", sel)
    return float(m.group(1)), float(m.group(2))


def check_engine_commit(commit: str) -> None:
    """Refuse unless engine, scripts and tests at HEAD are identical to `commit` and the tree is clean."""
    for args in (["diff", "--quiet", commit, "HEAD", "--", "engine", "scripts", "tests"],
                 ["diff", "--quiet", "HEAD", "--", "engine", "scripts", "tests"]):
        if subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True).returncode != 0:
            raise SealedRefusal(f"refused: engine/scripts/tests differ from release engine_commit {commit}")


def stage1_release(release: Path = RELEASE) -> dict:
    r = _load_release(release)
    if r is None or r.get("windows_released") != [W_PRE]:
        raise SealedRefusal(f"refused: stage 1 needs a committed {Path(release).name} with windows_released exactly "
                            f"[\"{W_PRE}\"]")
    if r.get("protocol_header_sha256") != FROZEN_V2_SHA256:
        raise SealedRefusal("refused: release names a different header sha256")
    sc = r.get("selection_results_commit", "<missing>")
    if subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", sc, "HEAD", "--",
                       str(SELECTION_RESULT.relative_to(ROOT))], capture_output=True).returncode != 0:
        raise SealedRefusal("refused: selection results differ from the release's selection_results_commit")
    h, b = selected_setting()
    g = r.get("selected_grid_point", {})
    if (float(g.get("h_near_high_pct", -1)), float(g.get("b_breadth_drop_pp", -1))) != (h, b):
        raise SealedRefusal("refused: release names a configuration other than the committed selection")
    check_engine_commit(r.get("engine_commit", "<missing>"))
    return r


def stage2_release(release2: Path = RELEASE2, stage1_result: Path = STAGE1_GATE) -> dict:
    """Stage 2 opens only with a committed second release AND a committed stage-1 result that satisfies the
    release's opening condition (checked here from the file, not from the release's word)."""
    import json
    r = _load_release(release2)
    if r is None or r.get("windows_released") != [W_H]:
        raise SealedRefusal(f"refused: stage 2 needs a committed {Path(release2).name} with windows_released [\"{W_H}\"]")
    if not (Path(stage1_result).exists() and _committed_clean(stage1_result)):
        raise SealedRefusal("refused: stage 2 needs the committed stage-1 gate file")
    res = json.loads(Path(stage1_result).read_text())
    hyps = r.get("opening_condition_hypotheses", ["H1", "H3"])
    gs = res["gate_signs"]
    readings = list(gs) if all(k.startswith("base_") for k in gs) else [None]
    sig = lambda b_, h: (gs[b_] if b_ else gs).get(h)
    ok = [h for h in hyps if all(sig(b_, h) is not None and all(sig(b_, h)[e] == "+" for e in ("E1_1928_1945", "E2_1946_1997"))
                                 for b_ in readings)]
    if not ok:
        raise SealedRefusal(f"refused: opening condition not met in the committed stage-1 result for {hyps}")
    r["_opened_by"] = ok
    return r


def seal_guard(path, release2: Path = RELEASE2, stage1_result: Path = STAGE1_GATE) -> None:
    """Any path under the seal needs a valid stage-2 release (with its opening condition met)."""
    if SEALED_MARK in str(path):
        stage2_release(release2, stage1_result)


def assert_window(end, release2: Path = RELEASE2, stage1_result: Path = STAGE1_GATE) -> None:
    if pd.Timestamp(end) > rc.D_END:
        stage2_release(release2, stage1_result)


def canonical_bytes(obj) -> bytes:
    import json
    return (json.dumps(obj, sort_keys=True, default=float, separators=(",", ":")) + "\n").encode()


def write_sealed(obj, path: Path = STAGE1_SEALED) -> str:
    """Write the full stage-1 results sealed (mode 000) and return their sha256. Never prints a magnitude."""
    import hashlib, os
    raw = canonical_bytes(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SealedRefusal("refused: sealed stage-1 file already exists (run once)")
    path.write_bytes(raw); os.chmod(path, 0)
    return hashlib.sha256(raw).hexdigest()


def verify_reproduction(obj, expected_sha: str) -> None:
    """Final run: its pre-1998 numbers must reproduce the sealed file byte for byte (by sha) before printing."""
    import hashlib
    got = hashlib.sha256(canonical_bytes(obj)).hexdigest()
    if got != expected_sha:
        raise SealedRefusal(f"refused: pre-1998 recomputation sha {got} != sealed {expected_sha}")


def open_sealed_stage1(gate: Path = STAGE1_GATE, release2: Path = RELEASE2, path: Path = STAGE1_SEALED) -> dict:
    """Readable only after a recorded gate-CLOSED result, or with a valid stage-2 release."""
    import json, os, hashlib
    if not (Path(gate).exists() and _committed_clean(gate)):
        raise SealedRefusal("refused: no committed stage-1 gate file")
    g = json.loads(Path(gate).read_text())
    if g.get("gate_open") is not False:
        stage2_release(release2, gate)
    os.chmod(path, 0o400)
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != g["sealed_sha256"]:
        raise SealedRefusal("refused: sealed file sha does not match the committed gate file")
    return json.loads(raw)


def assert_stage1_window(end) -> None:
    if pd.Timestamp(end) > PRE_END:
        raise SealedRefusal(f"refused: stage 1 reads nothing after {PRE_END.date()} (asked {end})")


# --------------------------------------------------------------------------- loaders
def load_french_industries(path, end) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(value-weighted, equal-weighted) daily returns as fractions, NaN where missing (-99.99 / -999), dates <= end.
    Lines dated after `end` are skipped by their date field before any value is parsed."""
    seal_guard(path); assert_window(end)
    endk = pd.Timestamp(end).strftime("%Y%m%d")
    secs, cur = {}, None
    for ln in open(path):
        if "Weighted Returns -- Daily" in ln:
            cur = "vw" if "Value" in ln else "ew"; secs[cur] = {"cols": None, "rows": []}; continue
        if cur is None:
            continue
        if secs[cur]["cols"] is None and ln.startswith(","):
            secs[cur]["cols"] = [c.strip() for c in ln.split(",")[1:]]; continue
        k = ln.split(",", 1)[0].strip()
        if len(k) == 8 and k.isdigit():
            if k > endk:
                continue
            secs[cur]["rows"].append(ln.rstrip("\n").split(","))
    out = []
    for key in ("vw", "ew"):
        r = secs[key]["rows"]
        df = pd.DataFrame([x[1:] for x in r], index=pd.to_datetime([x[0].strip() for x in r], format="%Y%m%d"),
                          columns=secs[key]["cols"]).astype(float)
        out.append(df.where(df > -99.0) / 100.0)
    return out[0], out[1]


def load_yahoo_tr(path, end) -> pd.Series:
    """F1: daily total return from a Yahoo parquet, rows filtered on the Date column at the Arrow level before any
    pandas frame exists; a window end after 2019-12-31 needs a valid stage-2 release (R13)."""
    import pyarrow.parquet as pq
    seal_guard(path); assert_window(end)
    end = pd.Timestamp(end)
    t = pq.read_table(path, columns=["Date", "Adj Close"], filters=[("Date", "<=", end.to_pydatetime())])
    d = t.to_pandas()
    if "Date" not in d.columns:
        d = d.reset_index()
    x = d["Adj Close"].astype(float)
    x.index = pd.to_datetime(d["Date"]).dt.normalize().values
    assert x.index.max() <= end, "post-seal row reached a frame"
    return x.sort_index()


def load_french_market(path, end) -> tuple[pd.Series, pd.Series]:
    seal_guard(path); assert_window(end)
    endk = pd.Timestamp(end).strftime("%Y%m%d")
    rows = []
    for ln in open(path):
        p = [x.strip() for x in ln.split(",")]
        if len(p[0]) == 8 and p[0].isdigit() and p[0] <= endk:
            rows.append(p)
    idx = pd.to_datetime([r[0] for r in rows], format="%Y%m%d")
    mkt = pd.Series([float(r[1]) + float(r[4]) for r in rows], index=idx) / 100
    rf = pd.Series([float(r[4]) for r in rows], index=idx) / 100
    return mkt, rf


# --------------------------------------------------------------------------- legs, breadth
@dataclass
class Legs:
    formed: dict          # month-end -> (offence list, defence list, eligible list)
    returns: pd.DataFrame  # daily OFF, DEF, BASE leg returns (net of intra-leg re-formation cost at the leg level)
    valid: pd.DataFrame    # daily valid-member counts per leg
    dropped_industry_days: int


def form_legs(vw: pd.DataFrame, mkt: pd.Series, start=None, min_valid: int = 252, min_pairs: int = 200,
              fee_bp: float = FEE_INDUSTRY_BP, leg_size: int | None = None, fixed: tuple | None = None) -> Legs:
    """Industries: legs = top / bottom third by trailing beta. Funds (F4): leg_size=3. fixed=(offence, defence)
    holds named members (named mapping, descriptive), base = all eligible."""
    s = vw.index
    valid = vw.notna()
    nvalid = valid.cumsum()
    me = pd.DatetimeIndex(pd.Series(s, index=s).groupby([s.year, s.month]).max().values)
    if start is not None:
        me = me[me >= pd.Timestamp(start) - pd.offsets.MonthEnd(2)]
    formed = {}
    for t in me:
        i = s.get_loc(t)
        if i < 253:
            continue
        w = slice(s[i - 252], s[i - 1])                    # data to t-1
        y, x = vw.loc[w], mkt.reindex(s).loc[w]
        b = {}
        for c in vw.columns:
            ok = y[c].notna() & x.notna()
            if nvalid[c].iloc[i - 1] >= min_valid and ok.sum() >= min_pairs:
                b[c] = float(np.cov(y[c][ok], x[ok])[0, 1] / np.var(x[ok], ddof=1))
        if len(b) < 6:
            continue
        bs = pd.Series(b).sort_values(kind="mergesort")
        if fixed is not None:
            off = [c for c in fixed[0] if c in b]; dfn = [c for c in fixed[1] if c in b]
            if off and dfn:
                formed[t] = (off, dfn, list(bs.index))
            continue
        k = leg_size if leg_size is not None else len(bs) // 3
        formed[t] = (list(bs.index[-k:]), list(bs.index[:k]), list(bs.index))
    keys = pd.DatetimeIndex(sorted(formed))
    R = pd.DataFrame(np.nan, index=s, columns=["OFF", "DEF", "BASE", "BASE_DRIFT"])
    V = pd.DataFrame(0, index=s, columns=["OFF", "DEF", "BASE", "BASE_DRIFT"])
    dropped = 0
    prev = None
    fee = fee_bp / 1e4
    for j, t in enumerate(keys):
        a = s.get_loc(t) + 1
        z = s.get_loc(keys[j + 1]) + 1 if j + 1 < len(keys) else len(s)
        days = s[a:z]
        legs = formed[t]
        for col, mem in zip(["OFF", "DEF", "BASE"], legs):
            blk = vw.loc[days, mem]
            ok = blk.notna()
            dropped += int((~ok).sum().sum())
            R.loc[days, col] = blk.mean(axis=1, skipna=True)     # missing industry-day dropped, not imputed
            V.loc[days, col] = ok.sum(axis=1)
            if prev is not None and len(days):
                old = set(prev[["OFF", "DEF", "BASE"].index(col)])
                repl = len(set(mem) - old) / max(1, len(mem))
                R.loc[days[0], col] = (1 + R.loc[days[0], col]) / (1 + 2 * repl * fee) - 1   # re-formation cost
        # R14(b): BASE_DRIFT = same members, equal weights at the month's first session, then drifting
        mem = legs[2]
        if len(days):
            blk = vw.loc[days, mem].to_numpy(dtype=float)
            w = np.full(len(mem), 1.0 / len(mem))
            out = np.full(len(days), np.nan)
            for d_ in range(len(days)):
                ok = np.isfinite(blk[d_])
                if ok.any():
                    out[d_] = float((w[ok] * blk[d_][ok]).sum() / w[ok].sum())
                    w = w.copy(); w[ok] = w[ok] * (1 + blk[d_][ok]); w = w / w.sum()
            R.loc[days, "BASE_DRIFT"] = out
            V.loc[days, "BASE_DRIFT"] = V.loc[days, "BASE"]
            if prev is not None:
                repl = len(set(mem) - set(prev[2])) / max(1, len(mem))
                R.loc[days[0], "BASE_DRIFT"] = (1 + R.loc[days[0], "BASE_DRIFT"]) / (1 + 2 * repl * fee) - 1
        prev = legs
    return Legs(formed, R, V, dropped)


def breadth_i(vw: pd.DataFrame, legs: Legs, n: int = 50) -> pd.Series:
    """Share of the offence leg's industries above their own 50-session SMA (missing industry-days dropped)."""
    lvl = (1 + vw.fillna(0)).cumprod().where(vw.notna().cumsum() > 0)
    sma = lvl.rolling(n, min_periods=n).mean()
    above = (lvl > sma).astype(float).where(sma.notna() & vw.notna())
    out = pd.Series(np.nan, index=vw.index)
    keys = pd.DatetimeIndex(sorted(legs.formed))
    for j, t in enumerate(keys):
        a = vw.index.get_loc(t) + 1
        z = vw.index.get_loc(keys[j + 1]) + 1 if j + 1 < len(keys) else len(vw.index)
        days = vw.index[a:z]
        out.loc[days] = above.loc[days, legs.formed[t][0]].astype(float).mean(axis=1, skipna=True).to_numpy(dtype=float)
    return out


def relative_line(legs: Legs) -> pd.Series:
    r = legs.returns
    return (1 + r["OFF"].fillna(0)).cumprod() / (1 + r["DEF"].fillna(0)).cumprod()


# --------------------------------------------------------------------------- state machines (draft rev 4)
NEUTRAL, DEFEND, ATTACK = 0, 1, 2
ARM_MEMORY = 21          # fixed setting (R4), not in the grid
ATTACK_MIN_HOLD = 63     # fixed (R1), not in the grid
WASH_LO, WASH_MAX = 0.25, 20


def washout_spells(sh: np.ndarray, lo: float = WASH_LO):
    """For each close i: if close i is the first close above `lo` after a run of closes <= `lo` (a spell ending at
    i-1), return the spell length and the sessions from the spell's lowest close (earliest if tied) to i.
    Otherwise NaN. Uses only closes <= i."""
    n = len(sh); run_len = np.full(n, np.nan); from_low = np.full(n, np.nan)
    start = None; low_i = None
    for i in range(n):
        v = sh[i]
        if np.isfinite(v) and v <= lo:
            if start is None:
                start, low_i = i, i
            elif v < sh[low_i]:
                low_i = i
        else:
            if start is not None and np.isfinite(v):
                run_len[i] = i - start
                from_low[i] = i - low_i
            if np.isfinite(v):
                start, low_i = None, None
    return run_len, from_low


def current_leg_breadth(vw: pd.DataFrame, legs: Legs, lookback: int = 126, n: int = 50) -> dict:
    """R2: for each day t, breadth history over the look-back is recomputed on the CURRENT leg's members.
    Returns per-day arrays: br (today), br_max126 (max over t-125..t on current members), wash_run_prev (length of
    the washout spell ending at t-1 when t is its recovery close), wash_from_low (sessions from that spell's lowest
    close to t), n_members."""
    lvl = (1 + vw.fillna(0)).cumprod().where(vw.notna().cumsum() > 0)
    sma = lvl.rolling(n, min_periods=n).mean()
    above = (lvl > sma).astype(float).where(sma.notna() & vw.notna())
    s = vw.index
    br = pd.Series(np.nan, index=s); bmax = br.copy(); run_prev = br.copy(); from_low = br.copy(); nm = br.copy()
    keys = pd.DatetimeIndex(sorted(legs.formed))
    for j, t in enumerate(keys):
        a_ = s.get_loc(t) + 1
        z = s.get_loc(keys[j + 1]) + 1 if j + 1 < len(keys) else len(s)
        if a_ >= z:
            continue
        mem = legs.formed[t][0]
        lo = max(0, a_ - lookback - 400)
        sh = above.iloc[lo:z][mem].mean(axis=1, skipna=True).to_numpy(dtype=float)
        mx = pd.Series(sh).rolling(lookback, min_periods=lookback).max().to_numpy()
        rl, fl = washout_spells(sh)
        k0 = a_ - lo
        br.iloc[a_:z] = sh[k0:]
        bmax.iloc[a_:z] = mx[k0:]
        run_prev.iloc[a_:z] = rl[k0:]
        from_low.iloc[a_:z] = fl[k0:]
        nm.iloc[a_:z] = len(mem)
    return {"br": br, "bmax": bmax, "wash_run_prev": run_prev, "wash_from_low": from_low, "n_members": nm}


def h1_states(rel: pd.Series, bd: dict, h: float, b: float, use_breadth: bool = True,
              arm_memory: int = ARM_MEMORY, return_log: bool = False):
    """H1 / price-only control state decided at each close, draft rev 4 rules R1-R5.
    Entry: DEFEND when armed within the last `arm_memory` sessions and the relative line crosses below its 50-session
    SMA; ATTACK on the first close above 25% after a washout spell (consecutive closes <= 25%) if the spell QUALIFIES
    (R12: on at least one close inside the spell the relative line is within h% of its 126-session low, i.e.
    rel <= (1 + h/100) * min(rel over the 126 sessions ending at that close)) and that close is within 20 sessions of
    the spell's lowest breadth close (earliest if tied). Same-day DEFEND and ATTACK: DEFEND wins (counted).
    Exits: DEFEND -> ATTACK at an ATTACK confirm, or -> NEUTRAL at the first month-end (after the entry day) on which
    the relative line closes above its SMA50. ATTACK -> DEFEND at a DEFEND trigger, or -> NEUTRAL at the first
    month-end at least 63 sessions after entry. A state is never exited on its entry day. Re-triggering the state
    already in force is ignored (its clock is not reset)."""
    s = rel.index
    hi = rel.rolling(126, min_periods=126).max()
    sma = rel.rolling(50, min_periods=50).mean()
    br, bmax = bd["br"].reindex(s), bd["bmax"].reindex(s)
    runp, fromlow = bd["wash_run_prev"].reindex(s), bd["wash_from_low"].reindex(s)
    near = (rel >= (1 - h / 100) * hi)
    lo126 = rel.rolling(126, min_periods=126).min()
    near_low = (rel <= (1 + h / 100) * lo126).fillna(False).values      # R12: literal mirror of `near`
    armed = near & ((br <= bmax - b / 100 + 1e-12) if use_breadth else True)
    armed = armed & hi.notna() & (bmax.notna() if use_breadth else True)
    armed_recent = armed.astype(float).rolling(arm_memory + 1, min_periods=1).max() > 0
    month_end = (pd.Series(s, index=s).groupby([s.year, s.month]).transform("max") == s).values
    cross_dn = ((rel < sma) & (rel.shift(1) >= sma.shift(1))).values
    above_sma = (rel > sma).values
    runp_v, fromlow_v = runp.values, fromlow.values
    st = np.full(len(s), np.nan)
    log = {"conflicts": 0, "wash_fired": 0, "wash_expired": 0, "wash_spells": 0, "wash_qualified": 0,
           "armed": armed.values.copy(), "exit": {"DEFEND_by_ATTACK": 0, "DEFEND_by_month_end_above_sma": 0,
                                                  "ATTACK_by_DEFEND": 0, "ATTACK_by_63_month_end": 0}}
    state, entry_i = NEUTRAL, None
    ready = (hi.notna() & sma.notna() & bmax.notna()).values
    for i in range(len(s)):
        if not ready[i]:
            continue
        defend = bool(armed_recent.iloc[i]) and bool(cross_dn[i])
        attack = False
        if np.isfinite(runp_v[i]) and runp_v[i] > 0:          # recovery close of a washout spell
            log["wash_spells"] += 1
            k = int(runp_v[i])
            qualifies = bool(near_low[max(0, i - k):i].any())   # R12: line near its 126-session low inside the spell
            log["wash_qualified"] += qualifies
            if qualifies and fromlow_v[i] <= WASH_MAX:          # trough clock (final R3)
                attack = True; log["wash_fired"] += 1
            else:
                log["wash_expired"] += 1
        if defend and attack:
            log["conflicts"] += 1
            attack = False
        if defend and state != DEFEND:
            if state == ATTACK:
                log["exit"]["ATTACK_by_DEFEND"] += 1
            state, entry_i = DEFEND, i
        elif attack and state != ATTACK:
            if state == DEFEND:
                log["exit"]["DEFEND_by_ATTACK"] += 1
            state, entry_i = ATTACK, i
        elif state == DEFEND and i != entry_i and month_end[i] and above_sma[i]:
            log["exit"]["DEFEND_by_month_end_above_sma"] += 1
            state, entry_i = NEUTRAL, None
        elif state == ATTACK and i != entry_i and month_end[i] and (i - entry_i) >= ATTACK_MIN_HOLD:
            log["exit"]["ATTACK_by_63_month_end"] += 1
            state, entry_i = NEUTRAL, None
        st[i] = state
    out = pd.Series(st, index=s)
    return (out, log) if return_log else out


def h3_states(legs: Legs) -> pd.Series:
    r = legs.returns
    lo = (1 + r["OFF"].fillna(0)).cumprod(); ld = (1 + r["DEF"].fillna(0)).cumprod()
    m126 = (lo / lo.shift(126)) - (ld / ld.shift(126))
    s = r.index
    me = pd.Series(s, index=s).groupby([s.year, s.month]).transform("max") == s
    st = pd.Series(np.nan, index=s)
    st[me & m126.notna()] = np.where(m126[me & m126.notna()] > 0, ATTACK, DEFEND)
    return st.ffill()


def targets_from_states(st: pd.Series, cash_for_defend: bool = False) -> pd.DataFrame:
    cols = ["OFF", "DEF", "BASE"]
    T = pd.DataFrame(np.nan, index=st.index, columns=cols)
    ok = st.notna()
    T.loc[ok] = 0.0
    T.loc[ok & (st == NEUTRAL), "BASE"] = 1.0
    T.loc[ok & (st == ATTACK), "OFF"] = 1.0
    if not cash_for_defend:
        T.loc[ok & (st == DEFEND), "DEF"] = 1.0
    return T


def base_view(legs_r: pd.DataFrame, base: str = "eq") -> pd.DataFrame:
    """R14: 'eq' = equal weight every session over the month's set (code reading); 'drift' = equal at month start,
    drifting. Returns OFF/DEF/BASE columns with BASE from the chosen reading."""
    out = legs_r[["OFF", "DEF", "BASE"]].copy()
    if base == "drift":
        out["BASE"] = legs_r["BASE_DRIFT"]
    return out


# --------------------------------------------------------------------------- F4: tradable fund tier
FUNDS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLRE", "XLC"]
NAMED_OFFENCE, NAMED_DEFENCE = ["XLK"], ["XLP", "XLU", "XLV"]


def load_fund_panel(yahoo_dir, end, tickers=FUNDS) -> tuple[pd.DataFrame, pd.Series]:
    """Fund daily total returns and SPY (the fund tier's beta reference), all via the sealed loader."""
    yd = Path(yahoo_dir)
    rets = {t: load_yahoo_tr(yd / f"{t}.parquet", end).pct_change(fill_method=None) for t in tickers}
    spy = load_yahoo_tr(yd / "SPY.parquet", end).pct_change(fill_method=None)
    sess = spy.index
    R = pd.DataFrame({t: r.reindex(sess) for t, r in rets.items()})
    return R, spy


def form_fund_legs(fund_r: pd.DataFrame, spy_r: pd.Series, fixed=None) -> Legs:
    """Header tradable tier: offence = 3 highest trailing-252-session beta (to SPY, data to t-1), defence = 3 lowest,
    among funds with >= 252 observed sessions; base = equal weight of eligible funds; 5 bp per side."""
    return form_legs(fund_r, spy_r, min_valid=252, min_pairs=200, fee_bp=FEE_FUND_BP, leg_size=3, fixed=fixed)


def map_states_to_sessions(st: pd.Series, sessions: pd.DatetimeIndex) -> pd.Series:
    """Industry state decided at the last industry date <= each fund session (signals from the industry
    portfolios, execution on funds)."""
    s = st.dropna()
    pos = np.searchsorted(s.index.values, pd.DatetimeIndex(sessions).values, side="right") - 1
    vals = np.full(len(sessions), np.nan)
    ok = pos >= 0
    vals[ok] = s.values[pos[ok]]
    return pd.Series(vals, index=sessions)


def tradable_veto(fund_estimates: dict) -> bool:
    """Header rule: 'A pass on industry portfolios with a negative point estimate on the tradable funds in
    2020-2025 is reported as signal not shown to be tradable, not as a pass.' True = veto fires. fund_estimates
    maps each evaluated reading (both R14 base readings; 5 bp and 2x = 10 bp fees) to the point estimate of the fund
    book's excess over its exposure-matched mix on 2020-2025. Any negative estimate fires the veto."""
    return any(v < 0 for v in fund_estimates.values())


def simulate_states(st: pd.Series, legs: Legs, rf: pd.Series, start, end, cash_for_defend=False,
                    fee_bp=FEE_INDUSTRY_BP, name="v2", base: str = "eq") -> rc.Book:
    R = base_view(legs.returns, base).loc[start:end]
    avail = legs.valid[["OFF", "DEF", "BASE"]].loc[start:end] > 0
    return rc.simulate(targets_from_states(st.loc[start:end], cash_for_defend), R, rf.reindex(R.index),
                       fee_bp, name, start=pd.Timestamp(start), end=pd.Timestamp(end), avail=avail,
                       equity_cols=("OFF", "DEF", "BASE"))


# --------------------------------------------------------------------------- matched-mix contrast
def ann_factor(idx) -> float:
    """252 sessions per year of weekday sessions; Saturday sessions (French data before 1952) raise it in
    proportion: 252 * n_sessions / n_weekday_sessions. Exactly 252 on any window without Saturdays, so every
    1998-2019 figure is unchanged (replaces b7ef827b1d's sessions-per-calendar-year factor before any read)."""
    idx = pd.DatetimeIndex(idx)
    wk = int((idx.dayofweek < 5).sum())
    return float(rc.TRADING_DAYS) * len(idx) / wk if wk else float(rc.TRADING_DAYS)


def window_excess(book: rc.Book, legs_r: pd.DataFrame, cash: pd.Series, a, z) -> float:
    """THE gate / sign-leg statistic (R13-g): annualised mean daily excess of the book over its exposure-matched
    static mix, the mix built from the book's own average weights on [a, z] alone; annualised by observed sessions
    per year in [a, z]. One function for the gate and for the final conjunction."""
    idx = book.returns.index
    m = (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(z))
    ii = idx[m]
    r = book.returns.loc[ii].values
    W = book.holdings.loc[ii, ["OFF", "DEF", "BASE"]].values
    W = np.concatenate([W, 1 - W.sum(axis=1, keepdims=True)], axis=1)
    L = np.concatenate([legs_r.loc[ii, ["OFF", "DEF", "BASE"]].fillna(0).values,
                        cash.reindex(ii).fillna(0).values[:, None]], axis=1)
    return float(matched_mix_stat(r[None], W[None], L[None], ann=ann_factor(ii))[0])


def matched_mix_stat(r, w, legs_r, ann: float = rc.TRADING_DAYS):
    """Annualised mean of r - (matched static mix), mix weights = this sample's own average weights.
    r: (B, n); w: (B, n, 3) start-of-day weights in OFF/DEF/BASE; legs_r: (B, n, 3); cash = 1 - sum(w) earns 0
    in the reference only if the strategy held cash (ablation), handled by the caller via the 4th column."""
    wbar = w.mean(axis=1, keepdims=True)
    ref = (wbar * legs_r).sum(axis=2)
    return (r - ref).mean(axis=1) * ann


def matched_contrast(book: rc.Book, legs_r: pd.DataFrame, cash: pd.Series, mask, B=10_000, block=21, seed=20261111,
                     ann: float | None = None):
    idx = book.returns.index[mask.reindex(book.returns.index).fillna(False).values]
    ann = ann_factor(idx) if ann is None else ann
    r = book.returns.loc[idx].values
    W = book.holdings.loc[idx, ["OFF", "DEF", "BASE"]].values
    W = np.concatenate([W, 1 - W.sum(axis=1, keepdims=True)], axis=1)       # cash column
    L = np.concatenate([legs_r.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0).values,
                        cash.reindex(idx).fillna(0).values[:, None]], axis=1)
    obs = float(matched_mix_stat(r[None], W[None], L[None], ann)[0])
    out = []
    for c in range(0, B, 1000):
        ii = rc.stationary_bootstrap_indices(len(r), min(1000, B - c), block, seed + c)
        out.append(matched_mix_stat(r[ii], W[ii], L[ii], ann))
    dist = np.concatenate(out)
    return {"observed": obs, "ci95": rc.ci95(dist), "p_one_sided_centred": rc.centred_p(dist, obs),
            "se": float(np.nanstd(dist, ddof=1)), "finite_draws": rc.finite_draws(dist), "n": int(len(r))}
