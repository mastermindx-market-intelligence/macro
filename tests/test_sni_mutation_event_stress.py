"""MUT2 killing tests for SNI event-response and US-stress survivors.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay false.
Fixtures are synthetic. Residuals and event-study numbers are descriptive,
never causal, never a news-impact claim.

Each test_mut2_<module>_<function>_<n> docstring names the surviving mutant
from the 2026-10-13 sweep (seed 20261014).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/us_stress"))

from s2_collapse import (  # noqa: E402
    Episode,
    EventRecord,
    _inside,
    _matching_exclusion,
    _session_index_map,
    step0_admit,
    step3_bundle,
)
from s2_clocklaw import session_dates  # noqa: E402
from s2_outcomes import OutcomeEngine  # noqa: E402
from s2_seal import EVENT_SOURCE_CELL, GRADE_HORIZONS  # noqa: E402
from s2_selection import (  # noqa: E402
    coverage_census_rows,
    earnings_census_rows,
    event_census_rows,
    event_source_cells,
)
from s2_splits import (  # noqa: E402
    build_membership,
    canonical_line,
    enrich_membership_rows_with_graded,
    membership_table_rows,
)
from s2_stats import hit_rate_test  # noqa: E402
from stress_set import (  # noqa: E402
    AuthorityMap,
    _earliest_close_date,
    _load_closes_map,
    _parquet_path_for,
)
import lib.hk_calendar as hk_calendar  # noqa: E402
import lib.nyse_calendar as nyse_calendar  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _record(**kw) -> EventRecord:
    defaults = dict(
        issuer_key="alibaba",
        family="results",
        t_avail_utc="2026-05-13T09:30:00+00:00",
        evidence_pointer="synthetic#a",
        s_us="2026-05-13",
        s_hk="2026-05-14",
        member_ids=["a"],
        member_families=["results"],
    )
    defaults.update(kw)
    return EventRecord(**defaults)


def _episode(s_us: str = "2023-06-15", **kw) -> Episode:
    rec = _record(s_us=s_us, s_hk="2023-06-16", **kw)
    return Episode(opener=rec, horizon=5)


class _PriceLoader:
    def __init__(self, baba: pd.DataFrame, spy: pd.DataFrame) -> None:
        self._frames = {
            "data/yahoo/BABA.parquet": baba,
            "data/yahoo/SPY.parquet": spy,
        }

    def read_parquet(self, path, columns=None):
        df = self._frames[path]
        return df if columns is None else df[[c for c in columns if c in df.columns]]


def _frame(dates, close, raw=None) -> pd.DataFrame:
    raw = list(close) if raw is None else list(raw)
    return pd.DataFrame({"Date": list(dates), "close": list(close), "close_price": raw})


def _engine_from_sessions(sessions, baba_close, spy_close, baba_raw=None, spy_raw=None):
    return OutcomeEngine(_PriceLoader(
        _frame(sessions, baba_close, baba_raw),
        _frame(sessions, spy_close, spy_raw),
    ))


def _nyse_slice(end_iso: str, n: int) -> list[str]:
    us = session_dates(nyse_calendar)
    idx = us.index(end_iso)
    return us[idx - n + 1: idx + 1]


# ---------------------------------------------------------------------------
# s2_stats
# ---------------------------------------------------------------------------

def test_mut2_s2_stats_hit_rate_test_21() -> None:
    """Mutant: hit_rate_test L56 `k / n` -> `k * n` (arith_swap)."""
    res = hit_rate_test([1, 0, 0, 0])
    assert res["hit_rate"] == round(1 / 4, 6)
    assert res["hit_rate"] != round(1 * 4, 6)


def test_mut2_s2_stats_hit_rate_test_22() -> None:
    """Mutant: hit_rate_test L56 `round(k / n, 6)` -> `round(..., 7)` (const_int)."""
    res = hit_rate_test([1, 0, 0])
    assert res["hit_rate"] == round(1 / 3, 6)
    assert res["hit_rate"] != round(1 / 3, 7)


# ---------------------------------------------------------------------------
# s2_splits
# ---------------------------------------------------------------------------

def test_mut2_s2_splits_canonical_line_26() -> None:
    """Mutant: canonical_line L105 `ensure_ascii=False` -> `True` (const_bool)."""
    line = canonical_line({"title": "配售", "n": 1})
    assert "配售" in line
    assert "\\u" not in line


def test_mut2_s2_splits_build_membership_28() -> None:
    """Mutant: build_membership L132 `census_only=False` -> `True` on graded rows."""
    ep = _episode(s_us="2023-06-15", evidence_pointer="synthetic#g",
                  member_ids=["g1"], t_avail_utc="2023-06-15T09:00:00+00:00")
    lines, _, _ = build_membership("P04", {h: [ep] for h in GRADE_HORIZONS}, None)
    flags = [json.loads(ln)["flags"]["census_only"] for ln in lines]
    assert flags and all(v is False for v in flags)


def test_mut2_s2_splits_build_membership_29() -> None:
    """Mutant: build_membership L138 `census_only=True` -> `False` on census-only rows."""
    graded = _episode(s_us="2023-06-15", evidence_pointer="synthetic#g",
                      member_ids=["g1"], t_avail_utc="2023-06-15T09:00:00+00:00")
    census = _episode(s_us="2023-06-16", issuer_key="tencent",
                      evidence_pointer="synthetic#c", member_ids=["c1"],
                      t_avail_utc="2023-06-16T09:00:00+00:00")
    lines, _, _ = build_membership(
        "P04", {h: [graded] for h in GRADE_HORIZONS},
        {h: [census] for h in GRADE_HORIZONS})
    census_flags = [
        json.loads(ln)["flags"]["census_only"]
        for ln in lines if json.loads(ln)["issuer_key"] == "tencent"
    ]
    assert census_flags and all(v is True for v in census_flags)


def test_mut2_s2_splits_membership_table_rows_32() -> None:
    """Mutant: membership_table_rows L173 `counts.get(split, 0)` -> default 1."""
    rows = membership_table_rows({}, {}, "P04")
    assert rows
    assert all(r["count"] == 0 for r in rows)


def test_mut2_s2_splits_enrich_membership_rows_with_graded_38() -> None:
    """Mutant: enrich_membership_rows_with_graded L200 `line + '\\n'` -> `-`."""
    original_sha = "ab" * 32
    rows = [{"protocol_id": "P04", "horizon": 5, "split": "TUNE",
             "count": 1, "membership_sha256": original_sha}]
    graded_line = json.dumps(
        {"split": "TUNE", "flags": {"census_only": False}, "episode_key": "g"},
        sort_keys=True)
    assert not graded_line.endswith("\n")
    out = enrich_membership_rows_with_graded(rows, {5: [graded_line]})
    payload = graded_line + "\n"
    assert out[0]["graded_membership_count"] == 1
    assert out[0]["graded_membership_sha256"] == hashlib.sha256(
        payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# s2_selection
# ---------------------------------------------------------------------------

def _events_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_mut2_s2_selection_event_census_rows_13() -> None:
    """Mutant: event_census_rows L121 `news_id in selected_ids` -> `not in`.

    A row that carries both the exact local_code token and a near-token must
    stay SELECTED only (no double EXCLUDED_AND_LISTED listing).
    """
    df = _events_df([{
        "news_id": "n1",
        "stock_code": "09988<br/>89988",
        "announced_at": datetime(2026, 5, 13, 17, 30),
        "category": "final_results",
        "title": "RESULTS",
    }])
    rows = event_census_rows(df, {"hkd_9988": "alibaba"})
    disps = [(r["disposition"], r["near_token"]) for r in rows]
    assert ("SELECTED", None) in disps
    assert all(d != "EXCLUDED_AND_LISTED" for d, _ in disps)


def test_mut2_s2_selection_earnings_census_rows_15() -> None:
    """Mutant: earnings_census_rows L156 `ticker == 'BABA'` -> `!=`."""
    df = pd.DataFrame([
        {"ticker": "BABA", "next_date": "2026-05-01", "next_time": "BMO",
         "as_of": "2026-04-01"},
        {"ticker": "OTHER", "next_date": "2026-05-02", "next_time": "AMC",
         "as_of": "2026-04-01"},
    ])
    rows = earnings_census_rows(df)
    assert len(rows) == 1
    assert rows[0]["identity_security_id"] == "SEC:US-XNYS-BABA"
    assert "BABA" in rows[0]["id"]


def test_mut2_s2_selection_event_source_cells_21() -> None:
    """Mutant: event_source_cells L223 `return out` -> `return None`."""
    reports = {
        "alibaba": {"metrics": {
            EVENT_SOURCE_CELL["alibaba"]: {"status": "OK", "evidence_rows": 3}}},
        "tencent": {"metrics": {
            EVENT_SOURCE_CELL["tencent"]: {"status": "OK", "evidence_rows": 1}}},
    }
    out = event_source_cells(reports)
    assert isinstance(out, dict)
    assert out["alibaba"]["cell"] == EVENT_SOURCE_CELL["alibaba"]
    assert out["alibaba"]["state"] == "OK"


def test_mut2_s2_selection_coverage_census_rows_22() -> None:
    """Mutant: coverage_census_rows L234 `cell == source_cell` -> `!=`."""
    cell = EVENT_SOURCE_CELL["alibaba"]
    reports = {
        "alibaba": {"metrics": {
            cell: {"status": "OK", "evidence_rows": 1},
            "other.hkd_9988": {"status": "GAP", "evidence_rows": 0}}},
        "tencent": {"metrics": {
            EVENT_SOURCE_CELL["tencent"]: {"status": "OK", "evidence_rows": 1}}},
    }
    rows = coverage_census_rows(reports)
    ali = [r for r in rows if r["issuer_key"] == "alibaba"]
    src = [r for r in ali if r["cell"] == cell]
    other = [r for r in ali if r["cell"] != cell]
    assert src and "event source used" in src[0]["disposition"]
    assert other and "not an S2 event source" in other[0]["disposition"]


def test_mut2_s2_selection_coverage_census_rows_23() -> None:
    """Mutant: coverage_census_rows L240 `issuer == 'alibaba'` -> `!=` (E1/E2)."""
    reports = {
        "alibaba": {"metrics": {
            EVENT_SOURCE_CELL["alibaba"]: {"status": "OK", "evidence_rows": 1}}},
        "tencent": {"metrics": {
            EVENT_SOURCE_CELL["tencent"]: {"status": "OK", "evidence_rows": 1}}},
    }
    rows = coverage_census_rows(reports)
    by_issuer = {r["issuer_key"]: r["report"] for r in rows}
    assert by_issuer["alibaba"] == "E1"
    assert by_issuer["tencent"] == "E2"


def test_mut2_s2_selection_coverage_census_rows_25() -> None:
    """Mutant: coverage_census_rows L242 `cell.split('.', 1)[0]` index 0 -> 1."""
    cell = EVENT_SOURCE_CELL["alibaba"]
    reports = {
        "alibaba": {"metrics": {cell: {"status": "OK", "evidence_rows": 1}}},
        "tencent": {"metrics": {
            EVENT_SOURCE_CELL["tencent"]: {"status": "OK", "evidence_rows": 1}}},
    }
    rows = coverage_census_rows(reports)
    ali = next(r for r in rows if r["issuer_key"] == "alibaba")
    family, counter = cell.split(".", 1)
    assert ali["family"] == family
    assert ali["counter"] == counter


def test_mut2_s2_selection_coverage_census_rows_27() -> None:
    """Mutant: coverage_census_rows L243 `cell.split('.', 1)[1]` index 1 -> 2."""
    cell = EVENT_SOURCE_CELL["alibaba"]
    reports = {
        "alibaba": {"metrics": {cell: {"status": "OK", "evidence_rows": 1}}},
        "tencent": {"metrics": {
            EVENT_SOURCE_CELL["tencent"]: {"status": "OK", "evidence_rows": 1}}},
    }
    rows = coverage_census_rows(reports)
    ali = next(r for r in rows if r["issuer_key"] == "alibaba")
    assert ali["counter"] == cell.split(".", 1)[1]


def test_mut2_s2_selection_coverage_census_rows_28() -> None:
    """Mutant: coverage_census_rows L249 `return rows` -> `return None`."""
    reports = {
        "alibaba": {"metrics": {
            EVENT_SOURCE_CELL["alibaba"]: {"status": "OK", "evidence_rows": 1}}},
        "tencent": {"metrics": {
            EVENT_SOURCE_CELL["tencent"]: {"status": "OK", "evidence_rows": 1}}},
    }
    rows = coverage_census_rows(reports)
    assert isinstance(rows, list) and len(rows) >= 2


# ---------------------------------------------------------------------------
# s2_collapse
# ---------------------------------------------------------------------------

def test_mut2_s2_collapse_Episode_confounded_00() -> None:
    """Mutant: Episode.confounded L58 `return len(...) > 1` -> `return None`."""
    ep = Episode(opener=_record(member_families=["results", "capital_action"]),
                 horizon=5)
    assert ep.confounded is True


def test_mut2_s2_collapse_Episode_confounded_01() -> None:
    """Mutant: Episode.confounded L58 `>` -> `<`."""
    two = Episode(opener=_record(member_families=["results", "capital_action"]),
                  horizon=5)
    one = Episode(opener=_record(member_families=["results"]), horizon=5)
    assert two.confounded is True
    assert one.confounded is False


def test_mut2_s2_collapse_Episode_confounded_02() -> None:
    """Mutant: Episode.confounded L58 `> 1` -> `> 2` (exactly two families)."""
    two = Episode(opener=_record(member_families=["results", "capital_action"]),
                  horizon=5)
    assert two.confounded is True


def test_mut2_s2_collapse_step0_admit_05() -> None:
    """Mutant: step0_admit L78 `disposition == 'EXCLUDED_AND_LISTED'` -> `!=`."""
    rows = [{
        "id": "x", "issuer_key": "alibaba", "family": "results",
        "disposition": "EXCLUDED_AND_LISTED",
        "listed_exclusion_reason": "synthetic_named_exclusion",
        "t_avail_quality": "PUBLISHER_STATED",
    }]
    kept, excl = step0_admit(rows, "alibaba")
    assert kept == []
    assert excl and excl[0].id == "x" and excl[0].step == "step0_admission"


def test_mut2_s2_collapse_step0_admit_06() -> None:
    """Mutant: step0_admit L78 `== EXCLUDED_AND_LISTED and reason` -> `or`."""
    rows = [{
        "id": "y", "issuer_key": "alibaba", "family": "results",
        "disposition": "SELECTED",
        "listed_exclusion_reason": "noise-string-not-an-exclusion",
        "t_avail_quality": "PUBLISHER_STATED",
        "t_avail_utc": "2026-05-13T09:30:00+00:00",
        "s_us": "2026-05-13", "s_hk": "2026-05-14",
        "evidence_pointer": "synthetic#y",
    }]
    kept, excl = step0_admit(rows, "alibaba")
    assert [r["id"] for r in kept] == ["y"]
    assert excl == []


def test_mut2_s2_collapse_step3_bundle_19() -> None:
    """Mutant: step3_bundle.union L183 `if ra != rb` -> `if ra == rb`.

    Two same-issuer, same-session, different-family events must form one bundle.
    """
    a = _record(family="results", member_ids=["a"], member_families=["results"],
                evidence_pointer="synthetic#a",
                t_avail_utc="2026-05-13T09:30:00+00:00")
    b = _record(family="capital_action", member_ids=["b"],
                member_families=["capital_action"], evidence_pointer="synthetic#b",
                t_avail_utc="2026-05-13T10:00:00+00:00")
    out = step3_bundle([a, b])
    assert len(out) == 1
    assert sorted(out[0].member_ids) == ["a", "b"]
    assert "results" in out[0].member_families
    assert "capital_action" in out[0].member_families


def test_mut2_s2_collapse_step3_bundle_20() -> None:
    """Mutant: step3_bundle L191 `idxs[1:]` -> `idxs[2:]` (drops the 2nd member)."""
    evs = [
        _record(family=fam, member_ids=[i], member_families=[fam],
                evidence_pointer=f"synthetic#{i}",
                t_avail_utc=f"2026-05-13T0{n}:30:00+00:00")
        for n, (i, fam) in enumerate(
            (("a", "results"), ("b", "capital_action"),
             ("c", "regulatory_material")), start=9)
    ]
    out = step3_bundle(evs)
    assert len(out) == 1
    assert sorted(out[0].member_ids) == ["a", "b", "c"]


def test_mut2_s2_collapse__inside_28() -> None:
    """Mutant: _inside L264 HK `i is not None` -> `i is None`.

    Absorption on the HK clock with US dates outside W_h must still return True.
    """
    idx_us = _session_index_map(session_dates(nyse_calendar))
    idx_hk = _session_index_map(session_dates(hk_calendar))
    opener = _record(s_us="2026-05-13", s_hk="2026-05-14",
                     evidence_pointer="synthetic#op")
    other = _record(s_us="2026-08-03", s_hk="2026-05-15",
                    evidence_pointer="synthetic#ot", member_ids=["z"],
                    t_avail_utc="2026-05-15T09:30:00+00:00")
    assert _inside(opener, other, 5, idx_us, idx_hk) is True


def test_mut2_s2_collapse__inside_30() -> None:
    """Mutant: _inside L265 HK branch `return True` -> `return False`."""
    idx_us = _session_index_map(session_dates(nyse_calendar))
    idx_hk = _session_index_map(session_dates(hk_calendar))
    opener = _record(s_us="2026-05-13", s_hk="2026-05-14",
                     evidence_pointer="synthetic#op")
    other = _record(s_us="2026-08-03", s_hk="2026-05-15",
                    evidence_pointer="synthetic#ot", member_ids=["z"],
                    t_avail_utc="2026-05-15T09:30:00+00:00")
    assert _inside(opener, other, 5, idx_us, idx_hk) is True


def test_mut2_s2_collapse__matching_exclusion_39() -> None:
    """Mutant: _matching_exclusion L329 `event.family == match['family']` -> `!=`."""
    ev = _record(family="results", programme=None)
    rule = {"match": {"family": "results"}, "reason": "synthetic_coverage_gap"}
    assert _matching_exclusion(ev, [rule]) is rule
    other = _record(family="capital_action", programme=None,
                    evidence_pointer="synthetic#o")
    assert _matching_exclusion(other, [rule]) is None


# ---------------------------------------------------------------------------
# s2_outcomes
# ---------------------------------------------------------------------------

def _march_engine() -> OutcomeEngine:
    sessions = _nyse_slice("2024-03-11", 20)
    n = len(sessions)
    return _engine_from_sessions(
        sessions,
        baba_close=[100.0 + i for i in range(n)],
        spy_close=[200.0 + 0.5 * i for i in range(n)],
    )


def test_mut2_s2_outcomes_resolve_window_04() -> None:
    """Mutant: resolve_window L64 `s_us - timedelta(days=1)` -> `+` (arith_swap)."""
    eng = _march_engine()
    s = date(2024, 3, 4)
    w = eng.resolve_window(s, 5)
    assert w is not None
    assert w.fill_date == s


def test_mut2_s2_outcomes_resolve_window_05() -> None:
    """Mutant: resolve_window L64 `timedelta(days=1)` -> `days=2` (const_int)."""
    eng = _march_engine()
    s = date(2024, 3, 5)  # Tuesday: days=1 fill matches s; days=2 fills Monday
    w = eng.resolve_window(s, 5)
    assert w is not None
    assert w.fill_date == s


def test_mut2_s2_outcomes_resolve_window_06() -> None:
    """Mutant: resolve_window L65 `return resolve_horizon_window(...)` -> None."""
    eng = _march_engine()
    assert eng.resolve_window(date(2024, 3, 4), 5) is not None


def test_mut2_s2_outcomes_leg_return_08() -> None:
    """Mutant: leg_return L75 `return e1/e0 - 1` -> `return None`.

    Distinct from MNZ-F2 (NaN/+inf truthiness on the `if not e0 or not e1` guard).
    """
    eng = _march_engine()
    fill, cov = date(2024, 3, 4), date(2024, 3, 11)
    got = eng.leg_return(eng.baba_close, fill, cov)
    e0 = float(eng.baba_close.loc[pd.Timestamp(fill)])
    e1 = float(eng.baba_close.loc[pd.Timestamp(cov)])
    assert got == pytest.approx(e1 / e0 - 1.0)


def test_mut2_s2_outcomes_leg_return_09() -> None:
    """Mutant: leg_return L75 `e1 / e0` -> `e1 * e0` (arith_swap)."""
    eng = _march_engine()
    fill, cov = date(2024, 3, 4), date(2024, 3, 11)
    got = eng.leg_return(eng.baba_close, fill, cov)
    e0 = float(eng.baba_close.loc[pd.Timestamp(fill)])
    e1 = float(eng.baba_close.loc[pd.Timestamp(cov)])
    assert got == pytest.approx(e1 / e0 - 1.0)
    assert got != pytest.approx(e1 * e0 - 1.0)


def test_mut2_s2_outcomes_leg_return_10() -> None:
    """Mutant: leg_return L75 `e1/e0 - 1.0` -> `e1/e0 + 1.0` (arith_swap)."""
    eng = _march_engine()
    fill, cov = date(2024, 3, 4), date(2024, 3, 11)
    got = eng.leg_return(eng.baba_close, fill, cov)
    e0 = float(eng.baba_close.loc[pd.Timestamp(fill)])
    e1 = float(eng.baba_close.loc[pd.Timestamp(cov)])
    assert got == pytest.approx(e1 / e0 - 1.0)
    assert got != pytest.approx(e1 / e0 + 1.0)


def test_mut2_s2_outcomes_leg_return_11() -> None:
    """Mutant: leg_return L75 ` - 1.0` -> ` - 1.001` (const_float)."""
    eng = _march_engine()
    fill, cov = date(2024, 3, 4), date(2024, 3, 11)
    got = eng.leg_return(eng.baba_close, fill, cov)
    e0 = float(eng.baba_close.loc[pd.Timestamp(fill)])
    e1 = float(eng.baba_close.loc[pd.Timestamp(cov)])
    assert got == pytest.approx(e1 / e0 - 1.0)
    assert got != pytest.approx(e1 / e0 - 1.001)


def test_mut2_s2_outcomes_episode_excess_12() -> None:
    """Mutant: episode_excess L81 `if w is None` -> `if w is not None`."""
    eng = _march_engine()
    out = eng.episode_excess(date(2024, 3, 4), 5)
    assert out["state"] == "OK"
    assert out["excess"] is not None


def test_mut2_s2_outcomes_episode_excess_18() -> None:
    """Mutant: episode_excess L94 OK-payload `return {...}` -> `return None`."""
    eng = _march_engine()
    out = eng.episode_excess(date(2024, 3, 4), 5)
    assert isinstance(out, dict)
    assert out["state"] == "OK"
    assert "subject_ret" in out and "bench_ret" in out and "excess" in out


def test_mut2_s2_outcomes_episode_excess_20() -> None:
    """Mutant: episode_excess L99 `subj - bench` -> `subj + bench` (arith_swap)."""
    eng = _march_engine()
    out = eng.episode_excess(date(2024, 3, 4), 5)
    assert out["excess"] == pytest.approx(out["subject_ret"] - out["bench_ret"])
    assert out["excess"] != pytest.approx(out["subject_ret"] + out["bench_ret"])


def _trailing63_anchors(s: date):
    d = s - timedelta(days=1)
    while not nyse_calendar.is_session(d):
        d -= timedelta(days=1)
    d63 = d
    seen = 0
    while seen < 63:
        d63 -= timedelta(days=1)
        if nyse_calendar.is_session(d63):
            seen += 1
    d64 = d
    seen = 0
    while seen < 64:
        d64 -= timedelta(days=1)
        if nyse_calendar.is_session(d64):
            seen += 1
    return d, d63, d64


def test_mut2_s2_outcomes_trailing63_direction_01() -> None:
    """Mutant: TRAILING63_SESSIONS L35 `63` -> `64` (module const_int)."""
    s = date(2024, 6, 3)
    d, d63, d64 = _trailing63_anchors(s)
    us = session_dates(nyse_calendar)
    win = us[us.index(d64.isoformat()): us.index(s.isoformat()) + 2]
    baba_map = {dt: 100.0 for dt in win}
    baba_map[d.isoformat()] = 110.0
    baba_map[d63.isoformat()] = 100.0
    baba_map[d64.isoformat()] = 200.0  # 64-session window would flip sign
    spy = [200.0] * len(win)
    baba = [baba_map[dt] for dt in win]
    eng = _engine_from_sessions(win, baba, spy)
    assert eng.trailing63_direction(s) == 1


def test_mut2_s2_outcomes_trailing63_direction_25() -> None:
    """Mutant: trailing63_direction L125 zero-close `return 0` -> `return 1`."""
    s = date(2024, 6, 3)
    d, d63, d64 = _trailing63_anchors(s)
    us = session_dates(nyse_calendar)
    win = us[us.index(d64.isoformat()): us.index(s.isoformat()) + 2]
    baba_map = {dt: 100.0 for dt in win}
    baba_map[d.isoformat()] = 0.0  # D(s) close 0 -> documented ABSTAIN 0
    spy = [200.0] * len(win)
    baba = [baba_map[dt] for dt in win]
    eng = _engine_from_sessions(win, baba, spy)
    assert eng.trailing63_direction(s) == 0


def test_mut2_s2_outcomes_info_leak_scan_31() -> None:
    """Mutant: info_leak_scan L134 `is not None` -> `is None` (scanned flag)."""
    eng = _march_engine()
    scan = eng.info_leak_scan(date(2024, 3, 1))
    assert scan["scanned"] is True
    assert scan["first_tune_anchor"] == "2024-03-01"


def test_mut2_s2_outcomes_info_leak_scan_33() -> None:
    """Mutant: info_leak_scan L139 `return out` (empty TUNE) -> `return None`."""
    eng = _march_engine()
    scan = eng.info_leak_scan(None)
    assert isinstance(scan, dict)
    assert scan["scanned"] is False
    assert scan["first_tune_anchor"] is None


def test_mut2_s2_outcomes_info_leak_scan_34() -> None:
    """Mutant: info_leak_scan L146 `q / q.shift(1)` -> `q * q.shift(1)`."""
    sessions = _nyse_slice("2024-03-11", 15)
    n = len(sessions)
    close = [100.0] * n
    raw = [50.0] * n  # q = 2.0
    raw[8] = 50.0 / 1.05  # q steps from 2.0 to 2.10
    eng = _engine_from_sessions(sessions, close, [200.0] * n, baba_raw=raw,
                                spy_raw=[200.0] * n)
    scan = eng.info_leak_scan(date.fromisoformat(sessions[0]))
    assert scan["leak"] is True
    # product path would be ~2.1*2-1 = 3.2, ratio path is 0.05; pin the ratio.
    assert scan["series"]["BABA"]["max_abs_step"] == pytest.approx(0.05, abs=1e-9)


def test_mut2_s2_outcomes_info_leak_scan_37() -> None:
    """Mutant: info_leak_scan L149 `offenders.index[0]` -> `index[1]`."""
    sessions = _nyse_slice("2024-03-11", 12)
    n = len(sessions)
    close = [100.0] * n
    raw = [100.0] * n
    raw[5] = 100.0 / 1.02  # a single q step of 0.02, then back
    eng = _engine_from_sessions(sessions, close, [200.0] * n, baba_raw=raw,
                                spy_raw=[200.0] * n)
    scan = eng.info_leak_scan(date.fromisoformat(sessions[0]))
    assert scan["leak"] is True
    # two steps (up then down); first offending date is the first jump bar.
    first = scan["series"]["BABA"]["first_offending_date"]
    assert first == sessions[5]


def test_mut2_s2_outcomes_info_leak_scan_00() -> None:
    """Mutant: INFO_LEAK_STEP_TOLERANCE L34 `1e-6` -> `1.001e-6` (const_float)."""
    sessions = _nyse_slice("2024-03-11", 10)
    n = len(sessions)
    close = [100.0] * n
    raw = [100.0] * n
    # step of 1.0005e-6: above 1e-6, below 1.001e-6
    raw[5] = 100.0 / (1.0 + 1.0005e-6)
    eng = _engine_from_sessions(sessions, close, [200.0] * n, baba_raw=raw,
                                spy_raw=[200.0] * n)
    scan = eng.info_leak_scan(date.fromisoformat(sessions[0]))
    assert scan["series"]["BABA"]["steps_above_tolerance"] >= 1
    assert scan["leak"] is True


# ---------------------------------------------------------------------------
# stress_set
# ---------------------------------------------------------------------------

def test_mut2_stress_set_AuthorityMap_setdefault_03() -> None:
    """Mutant: AuthorityMap.setdefault L100 `if key not in self` -> `in`."""
    m = AuthorityMap()
    assert m.setdefault("descriptive_only", False) is False
    assert m["descriptive_only"] is False


def test_mut2_stress_set_AuthorityMap___copy___05() -> None:
    """Mutant: AuthorityMap.__copy__ L108 `return self.copy()` -> `return None`."""
    m = AuthorityMap({"rank_authority": False})
    dup = copy.copy(m)
    assert isinstance(dup, AuthorityMap)
    assert dup is not m
    assert dup["rank_authority"] is False


def test_mut2_stress_set_AuthorityMap___or___06() -> None:
    """Mutant: AuthorityMap.__or__ L113 `return dup` -> `return None`."""
    m = AuthorityMap({"rank_authority": False})
    out = m | {"note": "synthetic"}
    assert isinstance(out, AuthorityMap)
    assert out["rank_authority"] is False
    assert out["note"] == "synthetic"


def test_mut2_stress_set_AuthorityMap___ror___07() -> None:
    """Mutant: AuthorityMap.__ror__ L118 `return dup` -> `return None`."""
    m = AuthorityMap({"rank_authority": False})
    out = {"note": "synthetic"} | m
    assert isinstance(out, AuthorityMap)
    assert out["rank_authority"] is False
    assert out["note"] == "synthetic"


def test_mut2_stress_set_AuthorityMap___ior___08() -> None:
    """Mutant: AuthorityMap.__ior__ L122 `return self` -> `return None`."""
    m = AuthorityMap({"rank_authority": False})
    m |= {"note": "synthetic"}
    assert isinstance(m, AuthorityMap)
    assert m["note"] == "synthetic"


def test_mut2_stress_set__earliest_close_date_30() -> None:
    """Mutant: _earliest_close_date L635 `not closes or not dated` -> `and`."""
    assert _earliest_close_date([10.0, 11.0, 12.0]) is None


def test_mut2_stress_set__parquet_path_for_37() -> None:
    """Mutant: _parquet_path_for L944 `'%s.parquet' % ticker` -> `//` (arith_swap)."""
    path = _parquet_path_for({}, "SYNTH", "/tmp/sni-mut2-data")
    assert path.name == "SYNTH.parquet"


def test_mut2_stress_set__load_closes_map_38() -> None:
    """Mutant: _load_closes_map L963 `return closes` -> `return None`."""
    out = _load_closes_map({}, "/tmp/sni-mut2-missing")
    assert isinstance(out, dict)
    assert out == {}
