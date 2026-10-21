"""Measured phase age for the Cycles kernel — masterplan B05.

`record_series` is a single-bar call: it sees today's `phase_v2` but not how
long that phase has been running.  The retained forward log
(``data/<engine>/forward_log.parquet``, appended nightly by
``cycle_forward_log``) holds one observed ``phase_v2`` stamp per (date, id),
so replaying it backwards from the current session MEASURES how many
contiguous sessions the current phase has already run — and, when a transition
is observed, when the run started.  Shipping ``phase_v2_age_bars = 0`` was the
known placeholder; blanket "unknown" was the interim honesty repair; this
module is the measured replacement, with an explicit status for every
boundary (``measured`` / ``lower_bound`` / ``insufficient_history`` /
``source_unavailable`` / ``unknown_phase``; ``not_logged`` is stamped by the
caller for records the log never captures, e.g. amalgam families).

Reader discipline: this module is READ-ONLY over the log (the writer owns it —
never write, truncate or create it from here) and never raises; every failure
degrades to a status string a renderer can display verbatim.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# Method stamp — receivers render this beside the count so an age is never
# mistaken for a bar-by-bar replay of the price tape inside the kernel.
PHASE_AGE_METHOD = "forward_log_replay.v1"

# Contiguity: two sessions are contiguous when at most 2 business days span
# them — the next session, or one weekday holiday in between.  np.busday_count
# counts Mon–Fri in [earlier, later): Tue→Wed = 1, Fri→Mon = 1, Thu→Mon = 2,
# so a one-weekday-holiday long weekend stays contiguous and a real hole does
# not.  A holiday calendar is deliberately NOT consulted: the tolerance is the
# contract, and pinning calendars here would couple age to exchange geometry.
_MAX_GAP_BUSDAYS = 2

# A log row is usable only with these; `basis` is optional (a log predating
# W2.2 has no basis column — every row then reads basis "tr").
_REQUIRED_COLUMNS = ("date", "id", "phase_v2")


def load_phase_history(engine: str = "sector_cycles") -> tuple[pd.DataFrame | None, str]:
    """Read the retained forward log reduced to the four columns age needs.

    Returns ``(df, "ok")`` | ``(None, "absent")`` | ``(None, "read_error")``.
    Never raises, never writes, never creates a directory — the log belongs to
    ``cycle_forward_log``; this side only ever reads it.
    """
    try:
        from lib import config  # local: keeps importing this module side-effect free
        path = config.data_dir() / engine / "forward_log.parquet"
        if not path.exists():
            return None, "absent"
        raw = pd.read_parquet(path)
        missing = [c for c in _REQUIRED_COLUMNS if c not in raw.columns]
        if missing:
            log.warning("cycle_phase_age: %s is missing column(s) %s", path, missing)
            return None, "read_error"
        out = raw.loc[:, list(_REQUIRED_COLUMNS)].copy()
        out["basis"] = raw["basis"] if "basis" in raw.columns else "tr"
        return out, "ok"
    except Exception as e:  # noqa: BLE001 — never raise past this boundary
        log.warning("cycle_phase_age: cannot load phase history for %r: %s", engine, e)
        return None, "read_error"


def _iso_date(v) -> str | None:
    """Normalize a log ``date`` cell to a ``YYYY-MM-DD`` string.

    The writer stamps meta.asOf strings; the slice tolerates a stray Timestamp
    round-trip.  None/NaN/NaT → None (an undated row is unusable, never fatal).
    """
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):  # unhashable/exotic cell — fall through to str()
        pass
    return str(v)[:10] or None


def _contiguous(earlier: str, later: str) -> bool:
    """≤ ``_MAX_GAP_BUSDAYS`` business days between two sessions."""
    return int(np.busday_count(earlier, later)) <= _MAX_GAP_BUSDAYS


def measure_phase_age(history: pd.DataFrame | None, *, entity_id, current_phase,
                      current_asof, basis) -> dict:
    """Measure how many contiguous sessions ``current_phase`` has been running.

    Walks the retained history for ``entity_id`` backwards from the CURRENT
    session (rows dated on/after ``current_asof`` are ignored — the live read
    stands for the current session), counting consecutive same-phase rows.
    Returns exactly ``sessions, status, method, run_start, observed_from,
    basis, history_rows`` (plus ``error`` only when an internal exception was
    absorbed).  Statuses:

    ``measured``           a contiguous prior row with a different phase_v2 was
                           observed → the transition bounds the run;
                           ``run_start`` is the run's earliest date (the current
                           session when ``sessions == 1``) and ``observed_from``
                           is the transition row's date.
    ``lower_bound``        the walk ended at the start of usable history or at
                           a non-contiguous hole without observing a transition
                           → ``sessions`` is a MINIMUM, ``run_start`` is None,
                           ``observed_from`` is the earliest date counted.
    ``insufficient_history``  no usable prior row, or the latest one is not
                           contiguous with ``current_asof`` → the log cannot
                           see the boundary the live read sits on.
    ``source_unavailable`` ``history`` is None (absent/unreadable log), or an
                           internal exception was absorbed.
    ``unknown_phase``      ``current_phase`` falsy — nothing to age.

    Never raises.
    """
    out: dict = {
        "sessions": None,
        "status": "source_unavailable",
        "method": PHASE_AGE_METHOD,
        "run_start": None,
        "observed_from": None,
        "basis": "tr" if basis is None or pd.isna(basis) else str(basis),
        "history_rows": 0,
    }
    try:
        if history is None:
            return out
        asof = _iso_date(current_asof)
        # usable rows: this entity, strictly before the live session, with an
        # observed phase_v2 on the SAME structure basis (a null basis reads
        # "tr", mirroring the writer's default).
        dates = history["date"].astype(object).map(_iso_date)
        phases = history["phase_v2"]
        if "basis" in history.columns:
            basis_rows = history["basis"].astype(object).map(
                lambda v: "tr" if v is None or pd.isna(v) else str(v))
        else:
            basis_rows = pd.Series("tr", index=history.index)
        mask = ((history["id"] == entity_id) & dates.notna() & phases.notna()
                & (basis_rows == out["basis"]))
        if asof is None:
            # no comparable session boundary — nothing is usable, never fatal
            out["status"] = "insufficient_history"
            return out
        mask &= dates < asof
        usable = pd.DataFrame({"date": dates[mask], "phase": phases[mask]})
        # keep-first per date on read (the writer's keep-FIRST invariant),
        # then chronological order for the backwards walk.
        usable = usable.drop_duplicates(subset=["date"], keep="first")
        usable = usable.sort_values("date", kind="stable")
        out["history_rows"] = len(usable)
        if not current_phase:
            out["status"] = "unknown_phase"
            return out
        rows = list(usable.itertuples(index=False, name=None))
        if not rows:
            out["status"] = "insufficient_history"
            return out
        if not _contiguous(rows[-1][0], asof):
            out["status"] = "insufficient_history"
            return out
        counted: list[str] = []          # newest → oldest same-phase dates
        status = "lower_bound"           # default: walk exhausted usable history
        for i in range(len(rows) - 1, -1, -1):
            d, ph = rows[i]
            later = rows[i + 1][0] if i + 1 < len(rows) else asof
            if not _contiguous(d, later):
                # a hole inside the retained history — the run may extend
                # past it, so the count is a minimum, not a measurement.
                break
            if ph != current_phase:
                status = "measured"      # transition observed at d
                out["observed_from"] = d
                break
            counted.append(d)
        out["status"] = status
        out["sessions"] = 1 + len(counted)
        if status == "measured":
            out["run_start"] = counted[-1] if counted else asof
        else:
            out["observed_from"] = counted[-1] if counted else None
        return out
    except Exception as e:  # noqa: BLE001 — never raise past this boundary
        out.update({"status": "source_unavailable", "sessions": None,
                    "run_start": None, "observed_from": None,
                    "error": str(e)[:120]})
        return out
