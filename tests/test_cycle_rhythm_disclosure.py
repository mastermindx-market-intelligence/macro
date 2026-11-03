"""SIC-D-B06 — honest rhythm/overdue disclosure contract tests.

Covers engine/cycle_rhythm.py (pure rhythm window + estimate kinds) and the
additive `_stamp_rhythm_disclosure` seam in engine/sector_cycles.py: the four
window states, no-roll-forward anchoring, equality with
`cycle_ontology.project_next`, provisional-turn exclusion, per-horizon estimate
kinds, series provenance, per-record fault isolation, and the compute() meta
declarations.  Synthetic turns/records only — no network, no site, no data/.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import cycle_ontology as onto  # noqa: E402
from engine import sector_cycles as sc  # noqa: E402
from engine.cycle_rhythm import (  # noqa: E402
    RHYTHM_SCHEMA,
    estimate_kinds,
    rhythm_window,
)

# Hand-built confirmed turns: five alternating pivots with VARYING half-cycle
# lengths so the P25/median/P75 edges are distinct and every window state is
# reachable.  halves = [0.8, 1.2, 0.7, 1.0] -> med 0.9, p25 0.775, p75 1.05.
_XS = [2020.0, 2020.8, 2022.0, 2022.7, 2023.7]


def _turns(xs=None, provisional_extra=None):
    xs = _XS if xs is None else xs
    ks = ["trough", "peak"] if len(xs) % 2 else ["peak", "trough"]
    out = [
        {"t": f"{int(x)}-{(int(round((x % 1) * 12)) + 1):02d}", "x": x,
         "k": ks[i % 2], "provisional": False}
        for i, x in enumerate(xs)
    ]
    if provisional_extra is not None:
        out.append(dict(out[-1], x=provisional_extra, provisional=True))
    return out


def _edges(turns):
    """(lo_x, central_x, hi_x) replicated from project_next's own arithmetic."""
    confirmed = [t for t in turns if not t.get("provisional")]
    xs = [t["x"] for t in confirmed]
    halves = [b - a for a, b in zip(xs, xs[1:])]
    last = confirmed[-1]
    return (last["x"] + float(np.percentile(halves, 25)),
            last["x"] + float(np.median(halves)),
            last["x"] + float(np.percentile(halves, 75)))


# ── the four window states + unavailable ────────────────────────────────────

def test_window_state_before_window():
    lo, _, _ = _edges(_turns())
    r = rhythm_window(_turns(), lo - 0.05)
    assert r["schema"] == RHYTHM_SCHEMA
    assert r["kind"] == "descriptive_rhythm"
    assert r["status"] == "before_window"
    assert r["overdue"] is False
    assert r["exceeded_central_years"] is None
    assert r["exceeded_window_years"] is None


def test_window_state_inside_before_central():
    lo, central, _ = _edges(_turns())
    r = rhythm_window(_turns(), (lo + central) / 2)
    assert r["status"] == "inside_window_before_central"
    assert r["overdue"] is False
    assert r["exceeded_central_years"] is None
    assert r["exceeded_window_years"] is None


def test_window_state_inside_past_central():
    _, central, hi = _edges(_turns())
    r = rhythm_window(_turns(), (central + hi) / 2)
    assert r["status"] == "inside_window_past_central"
    assert r["overdue"] is True
    assert r["exceeded_central_years"] > 0
    assert r["exceeded_window_years"] is None


def test_window_state_past_window():
    _, _, hi = _edges(_turns())
    r = rhythm_window(_turns(), hi + 0.05)
    assert r["status"] == "past_window"
    assert r["overdue"] is True
    assert r["exceeded_central_years"] > 0
    assert r["exceeded_window_years"] > 0


def test_window_unavailable_below_three_confirmed_turns():
    for turns in ([], _turns()[:2]):
        r = rhythm_window(turns, 2026.0)
        assert r["schema"] == RHYTHM_SCHEMA
        assert r["status"] == "unavailable"
        assert r["reason"] == "fewer_than_3_confirmed_turns"
        for key in ("anchor_turn", "anchor_x", "next_turn", "window", "window_x",
                    "as_of_x", "elapsed_half_cycle_ratio",
                    "exceeded_central_years", "exceeded_window_years",
                    "n_confirmed_halves", "overdue"):
            assert r[key] is None, key


# ── parity with project_next + the no-roll-forward law ──────────────────────

def test_window_edges_equal_project_next():
    turns, today = _turns(), 2026.4
    r, p = rhythm_window(turns, today), onto.project_next(turns, today)
    assert p is not None
    assert r["window"] == {"low": p["low"], "central": p["central"], "high": p["high"]}
    assert r["window_x"]["central"] == p["central_x"]
    lo, _, hi = _edges(turns)
    assert r["window_x"]["low"] == round(lo, 3)
    assert r["window_x"]["high"] == round(hi, 3)
    assert r["next_turn"] == p["nextTurn"]
    assert r["anchor_x"] == p["last_confirmed_x"]
    assert r["anchor_turn"] == p["last_confirmed_t"]
    assert r["overdue"] == p["overdue"]


def test_window_never_rolls_forward_when_today_advances():
    turns = _turns()
    lo, central, hi = _edges(turns)
    today = (central + hi) / 2                    # inside the window today
    r_now = rhythm_window(turns, today)
    r_late = rhythm_window(turns, today + 3.0)    # three years later

    # the dated, anchored window is IDENTICAL — only the state read moved
    assert r_late["window"] == r_now["window"]
    assert r_late["window_x"] == r_now["window_x"]
    assert r_late["anchor_turn"] == r_now["anchor_turn"]
    assert r_late["anchor_x"] == r_now["anchor_x"]

    assert r_now["status"] == "inside_window_past_central"
    assert r_now["exceeded_window_years"] is None
    assert r_late["status"] == "past_window"
    assert r_late["exceeded_window_years"] > 0
    assert r_late["exceeded_central_years"] > r_now["exceeded_central_years"]
    assert r_late["as_of_x"] == round(today + 3.0, 3)


def test_overdue_true_exactly_for_the_two_past_central_states():
    lo, central, hi = _edges(_turns())
    cases = [
        (lo - 0.05, False),
        ((lo + central) / 2, False),
        ((central + hi) / 2, True),
        (hi + 0.05, True),
    ]
    for today, want in cases:
        r = rhythm_window(_turns(), today)
        assert r["overdue"] is want, (today, r["status"])
        assert (r["status"] == "inside_window_past_central"
                or r["status"] == "past_window") == want


def test_provisional_turns_are_excluded_from_the_window():
    confirmed_only = _turns()
    with_prov = _turns(provisional_extra=2026.9)   # wild running extreme
    r_plain = rhythm_window(confirmed_only, 2026.4)
    r_prov = rhythm_window(with_prov, 2026.4)
    assert r_prov["window"] == r_plain["window"]
    assert r_prov["window_x"] == r_plain["window_x"]
    assert r_prov["anchor_turn"] == r_plain["anchor_turn"]
    assert r_prov["n_confirmed_halves"] == len(confirmed_only) - 1
    # project_next itself also filters provisional — parity holds both ways
    p = onto.project_next(with_prov, 2026.4)
    assert r_prov["window"]["central"] == p["central"]


# ── estimate_kinds ──────────────────────────────────────────────────────────

def _rhythm_ok():
    return rhythm_window(_turns(), 2026.4)


def test_estimate_kinds_model_pass_cell_is_qualified_with_parity_caveat():
    now = {"hazard": {
        "1m": {"p": 0.12, "source": "MODEL", "cell_verdict": "PASS"},
        "3m": {"p": 0.3, "source": "PRIOR", "cell_verdict": "PRIOR"},
        "6m": {"p": 0.4, "source": "PRIOR", "cell_verdict": "PRIOR"},
    }}
    ek = estimate_kinds(now, _rhythm_ok())
    assert ek["schema"] == "sector_cycles.estimate_kinds.v1"
    assert ek["rhythm"] == "descriptive_rhythm"
    assert ek["hazard"] == {"1m": "qualified_model_cell",
                            "3m": "baseline_prior",
                            "6m": "baseline_prior"}
    assert ek["model_cell_current_claim"] == "parity_failed"  # B12: measured PARITY_FAILS
    # B12r2 (RB12 repair): qualified records carry the sub-KiB pointer only
    lp = ek["live_feature_parity"]
    assert lp is not None and "report" not in lp
    assert lp["report_ref"] == "meta.live_hazard_parity"


def test_estimate_kinds_prior_only_has_no_model_cell_claim():
    now = {"hazard": {h: {"p": 0.3, "source": "PRIOR", "cell_verdict": "PRIOR"}
                      for h in ("1m", "3m", "6m")}}
    ek = estimate_kinds(now, _rhythm_ok())
    assert set(ek["hazard"].values()) == {"baseline_prior"}
    assert ek["model_cell_current_claim"] is None
    assert ek["live_feature_parity"] is None   # B12r2: unqualified carries no payload


def test_estimate_kinds_absent_hazard_and_horizons_read_missing():
    assert estimate_kinds({}, _rhythm_ok())["hazard"] == {
        "1m": "missing_estimate", "3m": "missing_estimate", "6m": "missing_estimate"}
    ek = estimate_kinds({"hazard": {"1m": {"p": 0.1, "source": "PRIOR",
                                           "cell_verdict": "PRIOR"}}}, _rhythm_ok())
    assert ek["hazard"]["1m"] == "baseline_prior"
    assert ek["hazard"]["3m"] == "missing_estimate"
    assert ek["hazard"]["6m"] == "missing_estimate"


def test_estimate_kinds_malformed_hazard_never_raises():
    for bad in (None, [], "x", {"1m": "nonsense"}, {"1m": 7, "3m": [1]},
                {"1m": {"p": 0.1}},                     # no source/verdict
                {"1m": {"source": "MODEL", "cell_verdict": "PRIOR"}},  # MODEL, not PASS
                {"1m": {"source": "WEIRD", "cell_verdict": "PASS"}}):
        ek = estimate_kinds({"hazard": bad}, _rhythm_ok())
        assert ek["hazard"]["1m"] == "missing_estimate", bad
        assert ek["model_cell_current_claim"] is None, bad
    # a fully malformed now / rhythm never raises either
    ek = estimate_kinds(None, None)
    assert ek["rhythm"] == "missing_estimate"
    assert set(ek["hazard"].values()) == {"missing_estimate"}


def test_estimate_kinds_rhythm_missing_when_window_unavailable():
    ek = estimate_kinds({}, rhythm_window(_turns()[:2], 2026.4))
    assert ek["rhythm"] == "missing_estimate"


def test_estimate_kinds_never_writes_now():
    now = {"hazard": {"1m": {"p": 0.12, "source": "MODEL", "cell_verdict": "PASS"},
                      "3m": {"p": 0.3, "source": "PRIOR", "cell_verdict": "PRIOR"}}}
    frozen = copy.deepcopy(now)
    estimate_kinds(now, _rhythm_ok())
    assert now == frozen


# ── series provenance + the stamp seam ──────────────────────────────────────

def _sector_rec():
    return {"id": "xlk", "kind": "sector", "basis": "price",
            "turns": _turns(), "now": {"phase": "Expansion"},
            "proj": None, "osc": [], "price": []}


def _basket_rec():
    return {"id": "b-ai", "kind": "basket", "basis": "tr",
            "turns": _turns(), "now": {}, "proj": None, "osc": [], "price": []}


def test_series_provenance_sector_record(monkeypatch):
    monkeypatch.setattr(
        sc.config, "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}})
    rec = _sector_rec()
    sc._stamp_rhythm_disclosure([rec], today_x=2026.4)
    assert rec["series_provenance"] == {
        "schema": "sector_cycles.series_provenance.v1",
        "structure_basis": "price",
        "rs_basis": "tr",
        "membership": "single_instrument",
        "point_in_time": True,
        "benchmark": "SPY",
        "benchmark_ffill_limit_sessions": sc.RS_BENCH_FFILL_LIMIT,
        "history_mode": "reconstructed_price_history",
    }
    assert rec["rhythm"]["status"] in ("past_window", "inside_window_past_central")
    assert rec["estimate_kinds"]["rhythm"] == "descriptive_rhythm"
    # additive only: the pre-existing keys are untouched
    assert rec["basis"] == "price" and rec["now"] == {"phase": "Expansion"}


def test_series_provenance_basket_record(monkeypatch):
    monkeypatch.setattr(
        sc.config, "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}})
    rec = _basket_rec()
    sc._stamp_rhythm_disclosure([rec], today_x=2026.4)
    assert rec["series_provenance"] == {
        "schema": "sector_cycles.series_provenance.v1",
        "structure_basis": "tr",
        "rs_basis": "tr",
        "membership": "current_membership",
        "point_in_time": False,
        "benchmark": "SPY",
        "benchmark_ffill_limit_sessions": None,   # _basket_rs ffill is unbounded
        "history_mode": "reconstructed_price_history",
    }


def test_series_provenance_amalgam_record_uses_family_benchmark(monkeypatch):
    monkeypatch.setattr(
        sc.config, "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}})
    rec = dict(_basket_rec(), id="nasdaq-semis", kind="nasdaq")
    sc._stamp_rhythm_disclosure([rec], today_x=2026.4)
    prov = rec["series_provenance"]
    assert prov["membership"] == "current_membership"
    assert prov["point_in_time"] is False
    assert prov["benchmark"] == "QQQ"
    assert prov["benchmark_ffill_limit_sessions"] is None


def test_stamp_error_on_one_record_leaves_the_others_stamped(monkeypatch):
    good = _sector_rec()

    # (a) malformed turns -> the pure module's never-raise path: unavailable,
    #     reason stamp_error, and the rest of the record is still stamped.
    bad_turns = _sector_rec()
    bad_turns["turns"] = [{"x": 2020.0, "k": "trough", "provisional": False},
                          {"x": 2021.0, "k": "peak", "provisional": False},
                          {"k": "peak", "provisional": False}]     # missing "x"
    sc._stamp_rhythm_disclosure([bad_turns, good], today_x=2026.4)
    assert bad_turns["rhythm"]["status"] == "unavailable"
    assert bad_turns["rhythm"]["reason"] == "stamp_error"
    assert good["rhythm"]["status"] != "unavailable"
    assert good["estimate_kinds"]["schema"] == "sector_cycles.estimate_kinds.v1"
    assert good["series_provenance"]["benchmark"] == "SPY"

    # (b) an exception inside the stamp wrapper -> the minimal stamp_error
    #     rhythm, build continues, sibling record fully stamped.  (boom's now is
    #     non-empty so the wrapper passes that exact dict object through.)
    boom = _basket_rec()
    boom["now"] = {"phase": "Peak"}
    good2 = _basket_rec()
    real = sc.estimate_kinds

    def raising_estimate_kinds(now, rhythm):
        if now is boom["now"]:
            raise RuntimeError("boom")
        return real(now, rhythm)

    monkeypatch.setattr(sc, "estimate_kinds", raising_estimate_kinds)
    sc._stamp_rhythm_disclosure([boom, good2], today_x=2026.4)
    assert boom["rhythm"] == {"schema": RHYTHM_SCHEMA, "status": "unavailable",
                              "reason": "stamp_error"}
    assert good2["rhythm"]["status"] != "unavailable"
    assert good2["estimate_kinds"]["rhythm"] == "descriptive_rhythm"


# ── compute() meta declarations ─────────────────────────────────────────────

def _panel(rows=520):
    idx = pd.bdate_range("2024-01-01", periods=rows)
    spy = pd.Series(np.linspace(400, 500, rows), index=idx)
    return pd.DataFrame({"SPY": spy, "XLK": spy * 1.05}, index=idx)


def test_compute_meta_declares_rhythm_version_and_correction_contract(monkeypatch):
    panel = _panel()
    monkeypatch.setattr(sc, "yahoo_closes", lambda basis="tr": panel.copy())
    monkeypatch.setattr(
        sc.config, "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}})

    def fake_build_sector(ticker, meta, closes, win_start, closes_px=None):
        if ticker != "XLK":
            return None
        rec = _sector_rec()
        rec.update({"ticker": "XLK", "name": "Technology",
                    "rs_history": sc._leadership_history(closes, ticker)})
        rec["now"].update(sc._leadership(closes, ticker))
        return rec

    monkeypatch.setattr(sc, "build_sector", fake_build_sector)
    monkeypatch.setattr(sc, "_load_baskets", lambda: {})
    monkeypatch.setattr(sc, "build_amalgam_family", lambda *a, **k: [])

    data = sc.compute()
    assert data is not None
    meta = data["meta"]
    assert meta["rhythm_version"] == 1
    assert meta["correction_contract"] == {
        "status": "none_native",
        "basis": "no native correction or revision field in Cycles inputs "
                 "(capability row R3A-92)",
    }
    # every record the build produced carries the three B06 stamps
    for rec in data["sectors"]:
        assert rec["rhythm"]["schema"] == RHYTHM_SCHEMA
        assert rec["rhythm"]["status"] != "unavailable"     # hand-built turns
        assert rec["estimate_kinds"]["rhythm"] == "descriptive_rhythm"
        assert rec["series_provenance"]["benchmark"] == "SPY"
        # additive only — pre-existing keys unchanged by the stamp
        assert rec["basis"] == "price"
        assert rec["proj"] is None and rec["turns"] == _turns()


def test_compute_publishes_parity_report_once_records_carry_pointer(monkeypatch):
    """B12r2 (RB12 repair): the ~10 KiB live-feature parity report is published
    exactly ONCE per payload, in meta — never per record.

    One qualified record (a MODEL/PASS cell) carries only the sub-KiB
    {verdict, failing, report_ref} pointer; one unqualified record carries None;
    meta.live_hazard_parity holds the full recorded report."""
    from engine.hazard_parity import LIVE_HAZARD_PARITY

    idx = pd.bdate_range("2024-01-01", periods=520)
    spy = pd.Series(np.linspace(400, 500, 520), index=idx)
    panel = pd.DataFrame({"SPY": spy, "XLK": spy * 1.05, "XLV": spy * 0.98},
                         index=idx)
    monkeypatch.setattr(sc, "yahoo_closes", lambda basis="tr": panel.copy())
    monkeypatch.setattr(
        sc.config, "load",
        lambda: {"engine": {"rs_ranking": {"benchmark": "SPY"}}})

    def fake_build_sector(ticker, meta, closes, win_start, closes_px=None):
        if ticker not in ("XLK", "XLV"):
            return None
        rec = _sector_rec()
        rec.update({"ticker": ticker, "name": meta.get("name", ticker),
                    "rs_history": sc._leadership_history(closes, ticker)})
        rec["now"].update(sc._leadership(closes, ticker))
        if ticker == "XLK":        # qualified: a MODEL/PASS hazard cell exists
            rec["now"]["hazard"] = {
                "1m": {"p": 0.12, "source": "MODEL", "cell_verdict": "PASS"},
                "3m": {"p": 0.3, "source": "PRIOR", "cell_verdict": "PRIOR"},
                "6m": {"p": 0.4, "source": "PRIOR", "cell_verdict": "PRIOR"},
            }
        else:                       # unqualified: priors only, no qualified cell
            rec["now"]["hazard"] = {
                h: {"p": 0.3, "source": "PRIOR", "cell_verdict": "PRIOR"}
                for h in ("1m", "3m", "6m")}
        return rec

    monkeypatch.setattr(sc, "build_sector", fake_build_sector)
    monkeypatch.setattr(sc, "_load_baskets", lambda: {})
    monkeypatch.setattr(sc, "build_amalgam_family", lambda *a, **k: [])

    data = sc.compute()
    assert data is not None
    by_ticker = {rec["ticker"]: rec for rec in data["sectors"]}
    assert set(by_ticker) == {"XLK", "XLV"}

    qual = by_ticker["XLK"]["estimate_kinds"]["live_feature_parity"]
    assert qual is not None
    assert "report" not in qual
    assert len(json.dumps(qual)) < 1024
    assert qual == {"verdict": LIVE_HAZARD_PARITY["verdict"],
                    "failing": LIVE_HAZARD_PARITY["failing"],
                    "report_ref": "meta.live_hazard_parity"}

    assert by_ticker["XLV"]["estimate_kinds"]["live_feature_parity"] is None

    meta_rep = data["meta"]["live_hazard_parity"]
    assert meta_rep is not None
    assert meta_rep["report"] == LIVE_HAZARD_PARITY["report"]
    assert meta_rep["verdict"] == LIVE_HAZARD_PARITY["verdict"]
