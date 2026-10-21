"""B06 — honest rhythm / overdue disclosure for Sector Cycles records.

`sector_cycles.compute()` already projects each record's next turn through
`cycle_ontology.project_next`, which anchors the window at the last CONFIRMED
turn and stamps `overdue` instead of rolling the date forward.  What the record
never said out loud is (a) the WINDOW STATE that projection implies — before /
inside-before-central / inside-past-central / past-window — and (b) which KIND
of estimate each timing number is: a descriptive rhythm read off the record's
own confirmed turns, a historically qualified hazard-model cell, a baseline
prior, or no estimate at all.

This module is PURE: no I/O, and every entry point returns a disclosure dict
rather than raising.  `rhythm_window` replicates `project_next`'s arithmetic
line for line (equality is asserted by tests/test_cycle_rhythm_disclosure.py)
so the two can never drift apart silently; the window edges are recomputed from
the record's own confirmed turns and NEVER depend on `today_x` — which is what
makes an "overdue" stamp an honest state instead of a receding horizon.
"""
from __future__ import annotations

import numpy as np

from engine import cycle_ontology as onto

RHYTHM_SCHEMA = "sector_cycles.rhythm.v1"
ESTIMATE_KINDS_SCHEMA = "sector_cycles.estimate_kinds.v1"

# Reason vocabulary: the only two ways a rhythm disclosure can be absent —
# not enough confirmed turns to describe a rhythm at all, or the stamping
# wrapper hitting an error it must not propagate.
REASON_FEW_TURNS = "fewer_than_3_confirmed_turns"
REASON_STAMP_ERROR = "stamp_error"

_HORIZONS = ("1m", "3m", "6m")


def _unavailable(reason: str) -> dict:
    """The absent-rhythm disclosure: labels present, every data field None."""
    return {
        "schema": RHYTHM_SCHEMA,
        "kind": "descriptive_rhythm",
        "status": "unavailable",
        "anchor_turn": None,
        "anchor_x": None,
        "next_turn": None,
        "window": None,
        "window_x": None,
        "as_of_x": None,
        "elapsed_half_cycle_ratio": None,
        "exceeded_central_years": None,
        "exceeded_window_years": None,
        "n_confirmed_halves": None,
        "overdue": None,
        "reason": reason,
    }


def rhythm_window(turns: list[dict], today_x: float) -> dict:
    """Dated, anchored descriptive rhythm window + explicit state for one record.

    Recomputes the window edges from the record's OWN confirmed turns with
    exactly `cycle_ontology.project_next`'s arithmetic (median / P25 / P75
    half-cycle off the last CONFIRMED turn).  The window itself never depends
    on `today_x`; only the state read (`status`, `overdue`, `exceeded_*`,
    `as_of_x`, `elapsed_half_cycle_ratio`) does.  Never raises: malformed or
    insufficient turns return `status="unavailable"` with a reason.
    """
    try:
        return _rhythm_window(turns, today_x)
    except Exception:  # noqa: BLE001 — pure module contract: never raises
        return _unavailable(REASON_STAMP_ERROR)


def _rhythm_window(turns: list[dict] | None, today_x: float) -> dict:
    # ── project_next arithmetic, replicated line for line ─────────────────────
    confirmed = [t for t in (turns or []) if not t.get("provisional")]
    if len(confirmed) < 3:
        return _unavailable(REASON_FEW_TURNS)

    xs = [t["x"] for t in confirmed]
    halves = [xs[i] - xs[i - 1] for i in range(1, len(xs))]
    if not halves:
        return _unavailable(REASON_FEW_TURNS)

    med = float(np.median(halves))
    lo_h = float(np.percentile(halves, 25))
    hi_h = float(np.percentile(halves, 75))
    last = confirmed[-1]
    next_kind = "peak" if last["k"] == "trough" else "trough"

    central_x = last["x"] + med
    lo_x = last["x"] + lo_h
    hi_x = last["x"] + hi_h

    overdue = bool(today_x > central_x)
    elapsed = round((today_x - last["x"]) / med, 3) if med > 0 else None

    # ── the honest state read — the piece project_next only implied ───────────
    if today_x < lo_x:
        status = "before_window"
    elif today_x <= central_x:
        status = "inside_window_before_central"
    elif today_x <= hi_x:
        status = "inside_window_past_central"
    else:
        status = "past_window"

    return {
        "schema": RHYTHM_SCHEMA,
        "kind": "descriptive_rhythm",
        "status": status,
        "anchor_turn": last.get("t"),
        "anchor_x": round(float(last["x"]), 3),
        "next_turn": next_kind,
        # YYYY-MM strings via project_next's own converter (deliberate private
        # reuse: parity with the projection is the contract, not a side effect).
        "window": {"low": onto._x_to_ym(lo_x),
                   "central": onto._x_to_ym(central_x),
                   "high": onto._x_to_ym(hi_x)},
        "window_x": {"low": round(lo_x, 3),
                     "central": round(central_x, 3),
                     "high": round(hi_x, 3)},
        "as_of_x": round(float(today_x), 3),
        "elapsed_half_cycle_ratio": elapsed,
        "exceeded_central_years": round(today_x - central_x, 3) if overdue else None,
        "exceeded_window_years": round(today_x - hi_x, 3) if today_x > hi_x else None,
        "n_confirmed_halves": len(halves),
        "overdue": overdue,
        "reason": None,
    }


def estimate_kinds(now: dict, rhythm: dict) -> dict:
    """Per-horizon estimate-kind labels for one record's timing numbers.

    Separates what each number IS: `descriptive_rhythm` (the anchored window
    above), `qualified_model_cell` (hazard cell with source MODEL and a PASS
    verdict), `baseline_prior` (source PRIOR) or `missing_estimate`.  A
    historically qualified cell is NOT a current calibrated claim until the live
    feature vector has earned one — B12 measured that parity
    (engine/hazard_parity.py, LIVE_HAZARD_PARITY) — so any qualified cell now
    carries `model_cell_current_claim: "parity_holds" | "parity_failed"` from the
    recorded verdict, plus a `live_feature_parity` {verdict, failing, report_ref}
    pointer.  B12r2 (RB12 repair): the ~10 KiB report itself is NEVER stamped per
    record — only qualified records carry the pointer, and the full report is
    published once in the payload meta (`meta.live_hazard_parity`,
    engine/sector_cycles.compute).

    Reads `now["hazard"]`; never writes it.  Never raises.
    """
    try:
        rhythm_kind = ("missing_estimate"
                       if not isinstance(rhythm, dict)
                       or rhythm.get("status") == "unavailable"
                       or rhythm.get("kind") != "descriptive_rhythm"
                       else "descriptive_rhythm")

        hazard = now.get("hazard") if isinstance(now, dict) else None
        hazard_kinds: dict[str, str] = {}
        any_qualified = False
        for h in _HORIZONS:
            cell = hazard.get(h) if isinstance(hazard, dict) else None
            if isinstance(cell, dict):
                if cell.get("source") == "MODEL" and cell.get("cell_verdict") == "PASS":
                    hazard_kinds[h] = "qualified_model_cell"
                    any_qualified = True
                    continue
                if cell.get("source") == "PRIOR":
                    hazard_kinds[h] = "baseline_prior"
                    continue
            hazard_kinds[h] = "missing_estimate"

        # B12: the recorded live-feature parity verdict gates the current claim.
        # B12r2 (RB12 repair): a record carries only {verdict, failing,
        # report_ref} — never the report — and only when a qualified cell exists.
        try:
            from engine.hazard_parity import LIVE_HAZARD_PARITY as _parity
            claim = ("parity_holds" if _parity.get("verdict") == "PARITY_HOLDS"
                     else "parity_failed" if _parity.get("verdict") == "PARITY_FAILS"
                     else "parity_not_established")
            live_parity = ({"verdict": _parity.get("verdict"),
                            "failing": _parity.get("failing"),
                            "report_ref": "meta.live_hazard_parity"}
                           if any_qualified else None)
        except Exception:  # noqa: BLE001 — disclosure degrades, never raises
            claim = "parity_not_established"
            live_parity = None

        return {
            "schema": ESTIMATE_KINDS_SCHEMA,
            "rhythm": rhythm_kind,
            "hazard": hazard_kinds,
            "model_cell_current_claim": claim if any_qualified else None,
            "live_feature_parity": live_parity,
        }
    except Exception:  # noqa: BLE001 — pure module contract: never raises
        return {
            "schema": ESTIMATE_KINDS_SCHEMA,
            "rhythm": "missing_estimate",
            "hazard": {h: "missing_estimate" for h in _HORIZONS},
            "model_cell_current_claim": None,
            "live_feature_parity": None,
        }
