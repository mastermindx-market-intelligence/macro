"""PSS-W3 — Prophet tailored-gate shadow (pure accrual, never a gate).

The forward-shadow the personality-timing charter left open (masterplan
research/PERSONALITY_SIGNAL_SUITE_MASTERPLAN_BY_FABLE.md §W3; candidate pinned by
ruling R-W1T-2 in research/PERSONALITY_TIMING_TAILORING_HANDOFF_FOR_FABLE.md §8).
Mirrors engine/mag7_washout_shadow.py and engine/prophet_stage_shadow.py: PURE
ACCRUAL + MEASUREMENT — this module NEVER gates, ranks, sizes, or alters any
Prophet, washout, or board decision. Every artifact is display / shadow tier. A
null here NEVER blocks anything, and no gate change ships from this lane: promotion
of any gate change needs its own prereg + ruling (contamination row absolute).

WHAT IT LOGS. For each covered name, nightly, it fires the SAME Stoch-RSI reset
construction two ways and logs where they DISAGREE (both directions is the product):

  uniform gate  — Stoch-RSI(14/14/3/3) cross up from K<20 on the INCUMBENT fixed
                  rung. The incumbent washout / Prophet lane fires on the 2W bar
                  (engine/mag7_washout.py two_week_bars + stoch_rsi; the same 2W
                  Stoch-RSI carrier index_momentum.py runs). UNIFORM_RUNG = "2W".
  tailored gate — the identical Stoch-RSI cross at each NAME'S structure-derived
                  rung (codex column `rung_derived` ∈ {3D, 1W, 2W}, the R-W1T-2
                  pinned S-family-at-derived-rung construction).

Both gates reuse the pinned stoch machinery verbatim — nothing is re-implemented:
scripts.research.ptt_w1_persistence_of_fit.bars_for + tool_dates(bars, "S"), which
themselves call engine.mag7_washout.stoch_rsi / cross_up. The flat-RSI window
(hi==lo → NaN, not a crash) is handled inside that shared stoch_rsi.

Per name we classify the most-recent evaluable bar of each rung:
  fired_uniform_only · fired_tailored_only · both · neither
Disagreements (the *_only classes) are the readout. When the derived rung IS 2W
the two gates are identical by construction (agree_by_construction=True) — logged
but never a "disagreement".

COPY LAW (R-W1T-3): these tools CONFIRM RESETS, they do not call bottoms. Nothing
here says "bottom"; the word "validated" is CI-banned and absent by design.

FORWARD LEDGER (house law). data/personality_timing/gate_shadow.jsonl is an
append-only forward ledger, keyed (as_of, sym); NIGHTLY IS THE SOLE ADVANCER
(engine.ledger_lane.nightly_advance_enabled(), COLLECT_LANE=nightly). A same-day
rerun appends nothing (idempotent on the key). Each fire row stores enough state
(entry_date + a positional entry index into the name's daily close) to grade later
under the DUAL rulers once 63td of forward tape accrues:
  legacy ruler  — fwd63 (forward 63td close return)
  timing ruler  — mae63 / prox / td_to_trough (charter §7 reset-confirmation set)
Grading is DEFERRED (grade_matured, nightly-gated): a fire graded prematurely would
read future prices that do not yet exist, so a not-yet-matured fire stays null and
is re-checked on a later nightly. The quarterly miss-rate readout is a separate
scan over this ledger (first readout ≈ 3 months post-ship).

data/personality_timing/gate_shadow_state.json is the display tally (coverage
census + disagreement counts + timing scorecard shares), rewritten each nightly.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from engine.ledger_lane import nightly_advance_enabled
from lib import config
from lib.market_session import (
    calendar_verified, cash_market_for_symbol, expected_session, is_session_date,
)

# Pinned stoch construction — reused verbatim (never re-implemented). bars_for +
# tool_dates(bars, "S") is the S-family (Stoch-RSI<20 cross) firing rule; both call
# engine.mag7_washout.stoch_rsi / cross_up under the hood.
from scripts.research.ptt_w1_persistence_of_fit import bars_for, tool_dates

log = logging.getLogger(__name__)

LEDGER_SCHEMA = "personality_gate_shadow.ledger/v1"
STATE_SCHEMA = "personality_gate_shadow.v1"
FORWARD_BASIS = "first_seen_next_session_close/v2"  # Calendar-certified new rows only
OBSERVATION_CLOCK = "as_of_date_utc_midnight_lower_bound/v1"
FILL_CAPTURE_MAX_CALENDAR_DAYS = 7  # after the first eligible T+1 session; otherwise abstain

# The incumbent uniform gate fires on the 2W Stoch-RSI bar (mag7_washout /
# index_momentum). Pinned — a change is a construction change, not a config knob.
UNIFORM_RUNG = "2W"
VALID_RUNGS = ("3D", "1W", "2W")

HORIZON = 63   # forward days for the legacy ruler (fwd63)
PROX = 31      # ±31td local-trough proximity window (charter §7 timing ruler)


def _base(root: Path | None) -> Path:
    return (root if root is not None else config.data_dir()) / "personality_timing"


def _codex_path(root: Path | None) -> Path:
    return _base(root) / "codex.parquet"


def ledger_path(root: Path | None) -> Path:
    return _base(root) / "gate_shadow.jsonl"


def state_path(root: Path | None) -> Path:
    return _base(root) / "gate_shadow_state.json"


def _closes(root: Path | None, sym: str) -> pd.Series | None:
    """Daily close series for one name from the baskets/ohlcv store (the same
    store the codex is built from). Fail-open per name."""
    try:
        p = (root if root is not None else config.data_dir()) / "baskets" / "ohlcv" / f"{sym}.parquet"
        s = pd.read_parquet(p)["close"].dropna()
        return s if not s.empty else None
    except Exception as e:  # noqa: BLE001 — per-name fail-open
        log.debug("personality_gate_shadow: %s closes unavailable (%s)", sym, e)
        return None


def _load_codex(root: Path | None) -> pd.DataFrame | None:
    """The per-name structure store (sym, as_of, rung_derived). Read as-of its
    build date — nightly evaluates only the newest bar, so the current codex rung
    is the PIT rung for today's fire (no historical rung lookahead)."""
    p = _codex_path(root)
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p, columns=["sym", "as_of", "rung_derived"])
        return df if not df.empty else None
    except Exception as e:  # noqa: BLE001
        log.warning("personality_gate_shadow: codex unreadable (%s)", e)
        return None


def _fires_on_latest_bar(close: pd.Series, rung: str) -> tuple[bool, int | None]:
    """Did the S-family Stoch-RSI cross print on the MOST RECENT bar of `rung`?

    Returns (fired, entry_idx) where entry_idx is the positional index into the
    DAILY close of the fire bar. A fire means: the newest bar of this rung is a
    Stoch-RSI cross-up from K<20 (the pinned reset-confirmation construction). We
    only look at the latest bar because the nightly lane logs today's tape — a fire
    on an older bar was (or will be) logged on the nightly of its own bar-date.

    The rung bar-date is mapped to its daily index via searchsorted (mirroring the
    canonical scripts.research.ptt_w1_timing_regrade.sig_metrics: idx.searchsorted(t),
    default side). A W-FRI label can fall past the last daily close (a Friday-holiday
    or Thursday-anchored week tail) — that bar is NOT reported as a fire (sig_metrics
    skips it identically), so no fire is ever stored with an unresolvable entry."""
    bars = bars_for(close, rung)
    if bars.empty:
        return False, None
    dates = tool_dates(bars, "S")  # bar-dates where the S-cross printed
    if not dates or dates[-1] != bars.index[-1]:
        return False, None
    i = int(close.index.searchsorted(dates[-1]))  # default side (== sig_metrics)
    if i >= len(close):
        return False, None  # W-FRI tail stamped past the last daily close — not a fire
    return True, i


def _classify(uniform: bool, tailored: bool) -> str:
    if uniform and tailored:
        return "both"
    if uniform:
        return "fired_uniform_only"
    if tailored:
        return "fired_tailored_only"
    return "neither"


def _scan(root: Path | None, as_of: str) -> tuple[list[dict], dict]:
    """Evaluate both gates for every covered name on the latest bar. Returns
    (fire_rows, census). Deterministic from the stores; idempotency enforced by the
    caller on the (as_of, sym) key."""
    codex = _load_codex(root)
    census = {
        "codex_names": 0, "covered": 0, "no_prices": 0, "bad_rung": 0,
        "rung_distribution": {}, "classes": {
            "both": 0, "fired_uniform_only": 0, "fired_tailored_only": 0, "neither": 0},
        "disagreements": 0, "agree_by_construction": 0,
        "future_codex": 0,
    }
    fires: list[dict] = []
    if codex is None:
        return fires, census

    census["codex_names"] = int(codex["sym"].nunique())
    for _, r in codex.iterrows():
        sym = str(r["sym"])
        rung = str(r["rung_derived"])
        codex_asof = str(r["as_of"])
        # A future-date structure profile is not valid point-in-time context.
        try:
            if pd.Timestamp(codex_asof).date() > pd.Timestamp(as_of).date():
                census["future_codex"] += 1
                continue
        except (ValueError, TypeError):
            census["future_codex"] += 1
            continue
        if rung not in VALID_RUNGS:
            census["bad_rung"] += 1
            continue
        close = _closes(root, sym)
        # Admit the observation's tape BEFORE either indicator or entry lookup.
        # A stored future tail must not change an earlier published source event.
        try:
            if close is not None:
                close = close.loc[close.index <= pd.Timestamp(as_of).normalize()]
        except (ValueError, TypeError):
            close = None
        if close is None or close.empty:
            census["no_prices"] += 1
            continue
        census["covered"] += 1
        census["rung_distribution"][rung] = census["rung_distribution"].get(rung, 0) + 1

        try:
            uni_fired, uni_e = _fires_on_latest_bar(close, UNIFORM_RUNG)
            tai_fired, tai_e = _fires_on_latest_bar(close, rung)
        except Exception as e:  # noqa: BLE001 — per-name fail-open
            log.debug("personality_gate_shadow: %s eval failed (%s)", sym, e)
            census["covered"] -= 1
            census["rung_distribution"][rung] -= 1
            census["no_prices"] += 1
            continue

        cls = _classify(uni_fired, tai_fired)
        census["classes"][cls] += 1
        by_construction = rung == UNIFORM_RUNG
        if by_construction and (uni_fired or tai_fired):
            census["agree_by_construction"] += 1
        if cls in ("fired_uniform_only", "fired_tailored_only"):
            census["disagreements"] += 1

        # Only fires (either gate) become ledger rows — 'neither' is the silent
        # majority and is counted in the census, never stored.
        if not (uni_fired or tai_fired):
            continue

        # Frozen entry state per FIRED rung, so a later nightly grades the exact
        # same entry. A fire on the uniform bar and a fire on the tailored bar can
        # have different bar-dates (different rungs), so each carries its own entry.
        row: dict = {
            "schema": LEDGER_SCHEMA,
            "as_of": as_of,
            "sym": sym,
            "codex_asof": codex_asof,
            "uniform_rung": UNIFORM_RUNG,
            "tailored_rung": rung,
            "agree_by_construction": by_construction,
            "fired_uniform": bool(uni_fired),
            "fired_tailored": bool(tai_fired),
            "disagreement_class": cls,
            # entry state for deferred DUAL-ruler grading (null until matured)
            "uniform_entry": _entry_row(close, uni_e) if uni_fired else None,
            "tailored_entry": _entry_row(close, tai_e) if tai_fired else None,
            # grade fields — nightly-advanced at maturity; null until 63td accrues
            "graded": False,
            "graded_asof": None,
            "uniform_grade": None,
            "tailored_grade": None,
            "note": "reset-confirmer shadow — logs uniform/tailored gate "
                    "disagreements; never gates/ranks/alters any decision",
        }
        fires.append(row)

    return fires, census


def _entry_row(close: pd.Series, e: int | None) -> dict | None:
    """Frozen entry state at daily positional index `e` (the resolved fire bar).
    `e` is guaranteed in-bounds by _fires_on_latest_bar (an unresolvable W-FRI-tail
    fire is never reported), so no null-entry fire is ever stored."""
    if e is None:
        return None
    return {
        "entry_date": str(close.index[e].date()),
        "entry_idx": int(e),
        "entry_px": round(float(close.iloc[e]), 4),
    }


# --------------------------------------------------------------------------- #
# Deferred DUAL-ruler grading (nightly-gated; frozen-until-matured).          #
# --------------------------------------------------------------------------- #
def _verified_session_dates(market: str, start: pd.Timestamp, count: int,
                            direction: int = 1) -> list[pd.Timestamp] | None:
    """Project the incumbent calendar; never infer a holiday from missing tape."""
    if not calendar_verified(market, start.year):
        return None
    dates: list[pd.Timestamp] = []
    day = start
    for _ in range(count * 14 + 31):
        day += pd.Timedelta(days=direction)
        if not calendar_verified(market, day.year):
            return None
        if is_session_date(market, day.date()):
            dates.append(day)
            if len(dates) == count:
                return dates[::-1] if direction < 0 else dates
    return None


def _completed_through(market: str, as_of: str) -> pd.Timestamp | None:
    """A date-only observation proves at most its UTC-midnight lower bound.

    This does not invent an end-of-day collection timestamp or certify vendor
    finality. The existing market calendar supplies its own settle buffer.
    """
    stamp = pd.Timestamp(as_of)
    if pd.isna(stamp):
        return None
    clock = pd.Timestamp(stamp.date(), tz="UTC")
    if not calendar_verified(market, clock.year):
        return None
    last = expected_session(market, clock.to_pydatetime())
    return pd.Timestamp(last) if calendar_verified(market, last.year) else None


def _grade_entry(close: pd.Series, execution: dict) -> dict | None:
    """Score a frozen research mark on 63 exact, completed market sessions.

    The caller clips to its completed-session observation boundary. A missing
    session withholds the grade; a later available row cannot move the horizon.
    """
    if execution.get("basis") != FORWARD_BASIS:
        return None
    try:
        date = pd.Timestamp(execution["entry_date"])
        market = execution["market"]
        entry_px = float(execution["entry_px"])
        if pd.isna(date) or not np.isfinite(entry_px) or entry_px <= 0:
            return None
        future = _verified_session_dates(market, date, HORIZON)
        if future is None or not is_session_date(market, date.date()):
            return None
        win = close.reindex([date, *future]).to_numpy(dtype=float, copy=True)
    except (KeyError, ValueError, TypeError, IndexError):
        return None
    if not np.isfinite(win).all() or (win <= 0).any():
        return None
    win[0] = entry_px  # the frozen observed entry, never today's revised entry
    out = {
        "fwd63": round((float(win[-1]) / entry_px - 1) * 100, 2),
        "mae63": round((float(win.min()) / entry_px - 1) * 100, 2),
        "prox": None, "td_to_trough": None, "timing_label": None,
        "grade_basis": FORWARD_BASIS,
        "first_seen_asof": execution["first_seen_asof"],
        "execution_date": execution["entry_date"],
        "execution_price": entry_px,
    }
    past = _verified_session_dates(market, date, PROX, direction=-1)
    if past is not None:
        w = close.reindex([*past, date, *future[:PROX]]).to_numpy(dtype=float, copy=True)
        if np.isfinite(w).all() and (w > 0).all():
            w[PROX] = entry_px
            lo = float(w.min())
            out["prox"] = round((entry_px / lo - 1) * 100, 2)
            tdt = int(np.argmin(w)) - PROX
            out["td_to_trough"] = tdt
            out["timing_label"] = ("called_low" if -2 <= tdt <= 5
                                   else "confirmed_reset" if tdt < -2 else "early")
    return out


def _capture_next_close(close: pd.Series, row: dict, side: str,
                        as_of: str) -> dict | str | None:
    """Observe the exact next completed cash session within the capture window.

    A missing/null expected session is not a holiday and cannot slide to a later
    row. Late observations retain their actual captured_asof. This calendar-
    completed research-price mark is neither vendor-finality nor broker-fill proof.
    """
    source = row.get(f"{side}_entry")
    if not isinstance(source, dict) or not source.get("entry_date"):
        return None
    market = cash_market_for_symbol(row.get("sym"))
    if market is None:
        return "unsupported_cash_market"
    try:
        known_dates = [pd.Timestamp(row["first_seen_asof"]),
                       pd.Timestamp(source["entry_date"])]
        if side == "tailored":
            known_dates.append(pd.Timestamp(row["codex_asof"]))
        observed = pd.Timestamp(as_of)
        if any(pd.isna(d) for d in [*known_dates, observed]):
            return "invalid_known_at"
        known = max(pd.Timestamp(d.date()) for d in known_dates)
        now = pd.Timestamp(observed.date())
    except (KeyError, ValueError, TypeError):
        return "invalid_known_at"
    if now < known:
        return None
    expected = _verified_session_dates(market, known, 1)
    if expected is None:
        return "unverified_cash_calendar"
    date = expected[0]
    # The clock starts at the calendar date even if no price row ever arrives.
    if (now - date).days > FILL_CAPTURE_MAX_CALENDAR_DAYS:
        return "missed_first_close_observation"
    completed = _completed_through(market, as_of)
    if completed is None:
        return "unverified_cash_calendar"
    if date > completed:
        return None
    try:
        price = float(close.loc[date])
        e = int(close.index.get_loc(date))
    except (KeyError, ValueError, TypeError, IndexError):
        return None
    if not np.isfinite(price) or price <= 0:
        return None  # may arrive/correct within the original, unextended window
    return {
        "basis": FORWARD_BASIS, "first_seen_asof": row["first_seen_asof"],
        "source_entry_date": source["entry_date"],
        "entry_date": str(date.date()), "entry_idx": e,
        "entry_px": round(price, 4), "captured_asof": as_of,
        "market": market, "observation_clock": OBSERVATION_CLOCK,
        "completed_through": str(completed.date()),
    }


def _grade_one(root: Path | None, row: dict, *, as_of: str) -> bool:
    """Two-stage first-seen grading; legacy and uncertified v1 values stay frozen.

    1. Capture the next closed-session mark within seven calendar days.
    2. Require 63 exact completed market-session closes before recording a grade.
    """
    if row.get("grade_basis") != FORWARD_BASIS or row.get("graded"):
        return False
    market = cash_market_for_symbol(row.get("sym"))
    close = _closes(root, str(row.get("sym")))
    if close is None:
        close = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    try:
        completed = _completed_through(market, as_of) if market else None
        close = close.loc[close.index <= completed] if completed is not None else close.iloc[:0]
    except (ValueError, TypeError):
        return False
    changed = False
    for side in ("uniform", "tailored"):
        if row.get(f"{side}_entry") is None:
            continue
        if row.get(f"{side}_execution") is None and not row.get(f"{side}_execution_skip"):
            candidate = _capture_next_close(close, row, side, as_of)
            if isinstance(candidate, dict):
                row[f"{side}_execution"] = candidate
                changed = True
            elif isinstance(candidate, str):
                row[f"{side}_execution_skip"] = candidate
                changed = True
        execution = row.get(f"{side}_execution")
        if (execution is not None and execution.get("market") == market
                and row.get(f"{side}_grade") is None):
            grade = _grade_entry(close, execution)
            if grade is not None:
                row[f"{side}_grade"] = grade
                changed = True
    sides = [s for s in ("uniform", "tailored") if row.get(f"{s}_entry")]
    if sides and all(row.get(f"{s}_grade") is not None for s in sides):
        if not row.get("graded"):
            row["graded"] = True
            changed = True
    return changed


# --------------------------------------------------------------------------- #
# Ledger I/O — append-only fires; keyed (as_of, sym); atomic rewrite on grade. #
# --------------------------------------------------------------------------- #
def _load_ledger(root: Path | None) -> list[dict]:
    p = ledger_path(root)
    if not p.exists():
        return []
    rows = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            pass
    return rows


def _ledger_keys(rows: list[dict]) -> set[tuple]:
    return {(r.get("as_of"), r.get("sym")) for r in rows}


def _source_event_key(row: dict, side: str) -> tuple | None:
    """The source event, not its (possibly repeated) publication wall date."""
    if not row.get(f"fired_{side}"):
        return None
    entry = row.get(f"{side}_entry")
    rung = row.get(f"{side}_rung")
    if not isinstance(entry, dict) or not entry.get("entry_date") or not rung:
        return None
    return row.get("sym"), side, rung, entry["entry_date"]


def _unique_new_fires(fires: list[dict], existing: list[dict]) -> list[dict]:
    """Deduplicate by source event SIDE against v1 and v2, preserving all v1 rows.

    When a name's second comparator has a new event while the first merely
    repeats an older bar, retain only the new leg on the new publication.
    """
    known = {k for old in existing for side in ("uniform", "tailored")
             if (k := _source_event_key(old, side)) is not None}
    occupied = _ledger_keys(existing)  # preserve one-row/name/publication-date
    fresh: list[dict] = []
    for row in fires:
        wall_key = row.get("as_of"), row.get("sym")
        if wall_key in occupied:
            continue
        new = dict(row)
        for side in ("uniform", "tailored"):
            k = _source_event_key(new, side)
            if k is None or k in known:
                new[f"fired_{side}"] = False
                new[f"{side}_entry"] = None
            else:
                known.add(k)
        if not (new["fired_uniform"] or new["fired_tailored"]):
            continue
        new["disagreement_class"] = _classify(
            bool(new["fired_uniform"]), bool(new["fired_tailored"]))
        new["agree_by_construction"] = bool(
            new["tailored_rung"] == UNIFORM_RUNG and
            new["fired_uniform"] and new["fired_tailored"])
        new["grade_basis"] = FORWARD_BASIS
        new["first_seen_asof"] = row["as_of"]
        fresh.append(new)
        occupied.add(wall_key)
    return fresh


def _rewrite_ledger(root: Path | None, rows: list[dict]) -> None:
    """Atomic full rewrite (temp + os.replace) — used only when grades advance."""
    base = _base(root)
    base.mkdir(parents=True, exist_ok=True)
    p = ledger_path(root)
    header = (
        "# personality_gate_shadow forward ledger — schema " + LEDGER_SCHEMA + "\n"
        "# One row per FIRED (as_of, sym): uniform vs tailored Stoch-RSI reset gate\n"
        "# + frozen entry state; DUAL-ruler grades (nightly-advanced at 63td maturity).\n"
        "# Reset-confirmer shadow — NEVER gates/ranks/alters any decision.\n"
    )
    body = "\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rows)
    text = header + (body + "\n" if body else "")
    fd, tmp = tempfile.mkstemp(dir=str(base), prefix=".gate_shadow.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _append_fires(root: Path | None, fresh: list[dict]) -> None:
    base = _base(root)
    base.mkdir(parents=True, exist_ok=True)
    p = ledger_path(root)
    write_header = not p.exists()
    with p.open("a", encoding="utf-8") as f:
        if write_header:
            f.write(
                "# personality_gate_shadow forward ledger — schema " + LEDGER_SCHEMA + "\n"
                "# One row per FIRED (as_of, sym): uniform vs tailored Stoch-RSI reset gate\n"
                "# + frozen entry state; DUAL-ruler grades (nightly-advanced at 63td maturity).\n"
                "# Reset-confirmer shadow — NEVER gates/ranks/alters any decision.\n")
        for r in fresh:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def _timing_shares(rows: list[dict]) -> dict:
    """Display tally of graded timing labels per gate side (nulls printed)."""
    out: dict = {}
    for side in ("uniform", "tailored"):
        graded = [r.get(f"{side}_grade") for r in rows
                  if r.get("grade_basis") == FORWARD_BASIS
                  and r.get(f"{side}_grade")]
        labels = [g.get("timing_label") for g in graded if g and g.get("timing_label")]
        n = len(labels)
        out[side] = {
            "n_graded": len(graded),
            "n_timing_labeled": n,
            "confirmed_reset": labels.count("confirmed_reset"),
            "called_low": labels.count("called_low"),
            "early": labels.count("early"),
            "median_fwd63": (round(float(pd.Series(
                [g["fwd63"] for g in graded if g and g.get("fwd63") is not None]).median()), 2)
                if any(g and g.get("fwd63") is not None for g in graded) else None),
        }
    return out


def update(root: Path | None = None, *, as_of: str | None = None) -> dict | None:
    """Nightly entrypoint (engine/run.py, after mag7_washout_shadow.update()).

    1. Scans both gates over every covered name on the latest bar; appends FRESH
       fire rows (nightly-gated, idempotent on (as_of, sym)).
    2. Advances DUAL-ruler grades for matured fires (nightly-gated, frozen-until-
       matured, idempotent).
    3. Rewrites gate_shadow_state.json — the coverage census + disagreement counts
       + timing scorecard (display tier; nulls printed). Never raises."""
    try:
        as_of = as_of or pd.Timestamp.now("UTC").date().isoformat()
        gate_open = nightly_advance_enabled()

        fires, census = _scan(root, as_of)

        appended = 0
        existing = _load_ledger(root)
        if gate_open and fires:
            fresh = _unique_new_fires(fires, existing)
            if fresh:
                _append_fires(root, fresh)
                existing.extend(fresh)
                appended = len(fresh)

        advanced = 0
        rows_changed = 0
        if gate_open and existing:
            for r in existing:
                try:
                    old_grade = bool(r.get("graded"))
                    if _grade_one(root, r, as_of=as_of):
                        rows_changed += 1
                        if r.get("graded") and not old_grade:
                            r["graded_asof"] = as_of
                            advanced += 1
                except Exception as e:  # noqa: BLE001 — per-row fail-open
                    log.debug("personality_gate_shadow: grade %s failed (%s)",
                              r.get("sym"), e)
            if rows_changed:
                _rewrite_ledger(root, existing)

        n_graded = sum(1 for r in existing
                       if r.get("grade_basis") == FORWARD_BASIS and r.get("graded"))
        legacy_graded = sum(1 for r in existing
                            if r.get("grade_basis") != FORWARD_BASIS and r.get("graded"))
        state = {
            "schema": STATE_SCHEMA,
            "is_context_only": True,
            "display_only": True,
            "authority_tier": "display",
            "as_of": as_of,
            "generated_utc": pd.Timestamp.now("UTC").isoformat(),
            "spec": "research/PERSONALITY_SIGNAL_SUITE_MASTERPLAN_BY_FABLE.md §W3",
            "gate_open": gate_open,
            "uniform_rung": UNIFORM_RUNG,
            "coverage_census": census,
            "ledger": {
                "fire_rows": len(existing),
                "appended_today": appended,
                "graded": n_graded,
                "graded_prospective": n_graded,
                "legacy_graded_excluded": legacy_graded,
                "legacy_rows": sum(1 for r in existing
                                   if r.get("grade_basis") != FORWARD_BASIS),
                "prospective_rows": sum(1 for r in existing
                                        if r.get("grade_basis") == FORWARD_BASIS),
                "grades_advanced_today": advanced,
            },
            "timing": _timing_shares(existing),
            "note": (
                "PSS-W3 reset-confirmer shadow (masterplan §W3, ruling R-W1T-2). "
                "Logs uniform-gate (2W Stoch-RSI) vs tailored-gate (Stoch-RSI at the "
                "codex structure-derived rung) disagreements both directions; graded "
                "later under dual rulers (fwd63 + timing). Display/shadow tier only: "
                "it NEVER gates, ranks, sizes, or alters any Prophet, washout, or board "
                "decision. Promotion of any gate change needs its own prereg + ruling. "
                "Legacy chart-date and uncertified v1 grade values are preserved but "
                "EXCLUDED from prospective timing. New v2 rows require the exact "
                "next calendar-completed close and 63 exact completed sessions. "
                "Date-only observations use a UTC-midnight lower bound; "
                "captured_asof records late observation, not vendor finality. "
                "Neither arm creates trading, rank, or gate authority."
            ),
        }
        base = _base(root)
        base.mkdir(parents=True, exist_ok=True)
        p = state_path(root)
        fd, tmp = tempfile.mkstemp(dir=str(base), prefix=".gate_shadow_state.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=1, default=str)
            os.replace(tmp, p)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        if appended or advanced:
            log.info("personality_gate_shadow: +%d fires, +%d grades advanced",
                     appended, advanced)
        return state
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("personality_gate_shadow update failed (%s)", e)
        return None
