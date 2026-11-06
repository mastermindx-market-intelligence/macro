"""SIC-D-B13 — activate the dormant basket crowding cap under a versioned score.

Synthetic fixtures only — no data/ or site/ reads; loaders are monkeypatched. Pins:

(1) the crowding member read resolves `ticker` first (fallback `symbol`, entries with
    neither skipped), so `_crowd_for_members` finally receives members and the
    `frac >= 0.34` cap fires on a basket scoring >= 58 (capped to exactly 57);
(2) score deltas are bounded: on one synthetic membership doc, only baskets whose
    crowd frac >= 0.34 AND pre-cap score >= 58 change score — every sector and every
    other basket is identical between the base `symbol` read and the new read;
(3) every Central row carries `conviction.score_version == 2`, meta carries
    `conviction_score_version == 2`, and `append_central_log` (lane gate enabled)
    writes the `score_version` column while prior rows keep their columns, values
    and keep-first precedence;
(4) grader byte-identity: every base key of `grade()` on a legacy-only frame equals
    the same key on a mixed frame (JSON-dump equal), and a frame without the column
    equals the same frame with an all-null column — post rows never enter a base key;
(5) segmentation: version-2 rows appear only under `by_score_version["2"]`, a cohort
    month containing both versions is split across segments, `score_version_segments`
    counts/dates/roles are exact, and `by_score_version == {}` with no v2 rows;
(6) the publication record's `crowding_input` discloses resolved / partial /
    no_members_resolved / grader-unavailable without ever raising.

Run: python3 -m pytest -q -p no:cacheprovider tests/test_sector_central_score_version.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine import sector_central as cen
from engine import sector_central_grader as scg

# ── hand-built cycle records (same shape as tests/test_sector_central.py) ─────


def _rec(ticker="XLK", name="Technology", pos=10.0, phase="Recovery", signal="BUY",
         rs_rank=1, above200d=True, rs_63d=5.0, kind="sector"):
    """A bullish, washed-out cycle record (the strongest setup) unless overridden."""
    return {
        "id": ticker.lower(), "ticker": ticker, "kind": kind, "name": name,
        "accent": "#38bdf8", "group": "Growth",
        "proj": {"tilt": "tailwind", "nextTurn": "trough", "low": "2026-07", "high": "2027-01"},
        "now": {"pos": pos, "phase": phase, "phaseLabel": phase, "signal": signal,
                "osc_slope": 1.0, "rs_rank": rs_rank, "above200d": above200d, "rs_63d": rs_63d},
    }


def _mkt(crowd=None):
    return {"risk_on": 0.5, "gate_factor": 1.0, "state_en": "Risk-on",
            "quad_name": "Goldilocks", "liquidity": "expanding", "derisk_blended": 0.25,
            "_crowd_by_ticker": (crowd or {})}


def _old_read(members):
    """The base crowding member read this lane replaces (`symbol` only)."""
    return [m.get("symbol") for m in (members or []) if m.get("symbol")]


# ── (a) the member read + the cap ─────────────────────────────────────────────

def test_member_read_ticker_first_symbol_fallback_neither_skipped():
    members = [{"ticker": "AAA"},
               {"ticker": "", "symbol": "BBB"},      # empty ticker → symbol fallback
               {"symbol": "CCC"},                     # symbol-only still resolves
               {"ticker": None, "symbol": None},      # neither → skipped
               {"name": "no ids at all"}]             # neither → skipped
    assert cen._crowding_member_ids(members) == ["AAA", "BBB", "CCC"]   # order kept
    assert cen._crowding_member_ids([]) == []
    assert cen._crowding_member_ids(None) == []


def test_ticker_members_resolve_crowding_and_cap_to_57():
    crowd = {"NVDA": {}, "AMD": {}}
    rec = _rec(ticker="SMH", name="AI Infra", kind="basket")
    # pre-cap baseline: same basket, members the crowd map does not hold → no cap
    base = cen._fuse(rec, _mkt(crowd), 5, trend={"pass": True}, members=["XXX", "YYY"])
    assert base["conviction"]["score"] >= 58            # the cap condition is live
    assert base["crowding"] is None
    # ticker-keyed members reach _crowd_for_members → frac 1.0 → capped to exactly 57
    ids = cen._crowding_member_ids([{"ticker": "NVDA"}, {"ticker": "AMD"}])
    fused = cen._fuse(rec, _mkt(crowd), 5, trend={"pass": True}, members=ids)
    assert ids == ["NVDA", "AMD"]
    assert fused["crowding"] == {"n_crowded": 2, "n_members": 2, "frac": 1.0,
                                 "names": ["NVDA", "AMD"]}
    assert fused["conviction"]["score"] == 57
    # symbol-only membership still resolves (the fallback path)
    sym_ids = cen._crowding_member_ids([{"symbol": "NVDA"}, {"symbol": "AMD"}])
    assert (cen._fuse(rec, _mkt(crowd), 5, trend={"pass": True}, members=sym_ids)
            ["conviction"]["score"] == 57)
    # a member with neither id is skipped (1 crowded of 1 fed member)
    assert cen._crowding_member_ids([{"ticker": "NVDA"}, {"note": "no id"}]) == ["NVDA"]


def test_compute_resolves_ticker_membership_versions_and_meta(tmp_path, monkeypatch):
    """The module's own compute() with a monkeypatched cycle spine + market context and
    a real (tmp) membership.json: the ticker read resolves, the cap fires, and every row
    plus meta carry the score version."""
    (tmp_path / "baskets").mkdir()
    (tmp_path / "baskets" / "membership.json").write_text(json.dumps({
        "version": "v-test",
        "baskets": {"ai_infra": {"name": "AI Infra", "members": [
            {"ticker": "NVDA", "added": "2023-01-01", "curated_added": "2023-01-01",
             "removed": None},
            {"ticker": "AMD", "added": "2023-01-01", "curated_added": "2023-01-01",
             "removed": None}]}}}), encoding="utf-8")
    monkeypatch.setattr(cen.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(cen, "market_context", lambda: {
        "risk_on": 0.5, "gate_factor": 1.0, "heat": {},
        "_crowd_by_ticker": {"NVDA": {}, "AMD": {}}})
    import engine.sector_cycles as spine
    import engine.inputs as inputs
    basket = _rec(ticker="SMH", name="AI Infra", kind="basket")
    basket["id"] = "b-ai_infra"
    monkeypatch.setattr(spine, "compute", lambda: {
        "sectors": [_rec()], "baskets": [basket], "meta": {"asOf": "2026-10-20"}})
    monkeypatch.setattr(inputs, "yahoo_closes", lambda: None)
    out = cen.compute()
    assert out is not None
    assert out["meta"]["conviction_score_version"] == cen.CONVICTION_SCORE_VERSION == 2
    sec, bsk = out["sectors"][0], out["baskets"][0]
    assert sec["conviction"]["score_version"] == 2
    assert bsk["conviction"]["score_version"] == 2
    # the ticker read reached the crowding input: frac 1.0, capped, coverage resolved
    assert bsk["crowding"]["frac"] == 1.0
    assert bsk["conviction"]["score"] == 57
    cov = bsk["membership_coverage"]
    assert cov["crowding_input_members"] == 2
    assert cov["crowding_input_status"] == "resolved"
    assert out["meta"]["membership_coverage"]["n_crowding_unresolved"] == 0


def test_score_deltas_bounded_to_capped_baskets():
    """Old read (`symbol`) vs new read (`ticker` first) on one synthetic doc: only the
    basket whose frac >= 0.34 AND pre-cap score >= 58 changes; sectors and every other
    basket are identical."""
    crowd = {t: {} for t in ("AAA", "BBB", "CCC", "DDD")}
    capped_doc = [{"ticker": t} for t in ("AAA", "BBB", "CCC", "DDD")]   # frac 1.00
    sub34_doc = [{"ticker": t} for t in ("AAA", "EEE", "FFF", "GGG")]    # frac 0.25
    low = _rec(pos=55.0, phase="Peak", signal="SELL", rs_rank=6, above200d=False)
    rows = [  # (label, cycle record, membership doc)
        ("sector", _rec(), None),                       # sectors never carry crowding
        ("capped", _rec(ticker="SMH", name="A", kind="basket"), capped_doc),
        ("sub34", _rec(ticker="XBI", name="B", kind="basket"), sub34_doc),
        ("lowscore", low | {"ticker": "XLU", "name": "C", "kind": "basket"}, capped_doc),
    ]
    mkt = _mkt(crowd)
    for label, rec, doc in rows:
        old_ids = _old_read(doc)
        new_ids = cen._crowding_member_ids(doc)
        if doc is not None:
            assert old_ids == [] and new_ids                # ticker-keyed doc: base saw nothing
        old = cen._fuse(rec, mkt, 5, trend={"pass": True}, members=old_ids)
        new = cen._fuse(rec, mkt, 5, trend={"pass": True}, members=new_ids)
        so, sn = old["conviction"]["score"], new["conviction"]["score"]
        if label == "capped":
            assert so >= 58 and sn == 57 and so != sn       # the one changed score
        else:
            assert sn == so, f"{label} moved: {so} -> {sn}"
            if label == "lowscore":
                assert so < 58                              # crowded but below the cap line
            if label == "sub34":
                assert new["crowding"]["frac"] == 0.25 < 0.34


# ── (b) score_version on rows, meta and the ledger append ─────────────────────

def test_fuse_stamps_score_version_on_sector_and_basket_rows():
    for rec in (_rec(), _rec(ticker="SMH", kind="basket")):
        fused = cen._fuse(rec, _mkt(), 11, trend={"pass": True})
        assert fused["conviction"]["score_version"] == cen.CONVICTION_SCORE_VERSION == 2


def test_append_central_log_writes_score_version_keeps_prior_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(scg, "_ledger_advance_enabled", lambda: True)   # lane gate ON
    monkeypatch.setattr(scg.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(scg, "_yahoo_panel", lambda: None)
    p = tmp_path / "sector_central" / "calls.parquet"
    p.parent.mkdir(parents=True)
    prior_cols = ["date", "id", "kind", "ticker", "basket_id", "name", "score",
                  "label", "dir", "confluence", "trend_pass", "ret_12m",
                  "gate_factor", "level"]
    prior = pd.DataFrame([{  # a pre-B13 legacy row: no score_version column at all
        "date": "2026-06-01", "id": "xlk", "kind": "sector", "ticker": "XLK",
        "basket_id": None, "name": "Technology", "score": 70, "label": "Accumulate",
        "dir": "up", "confluence": 3, "trend_pass": True, "ret_12m": 0.2,
        "gate_factor": 0.6, "level": 100.0}])
    prior.to_parquet(p, index=False)
    data = {"as_of": "2026-06-01",
            "sectors": [
                {"id": "xlk", "kind": "sector", "ticker": "XLK", "name": "Technology",
                 "conviction": {"score": 55, "label_en": "Neutral", "dir": "flat",
                                "confluence": {"agree": 1}, "score_version": 2},
                 "forward": {"trend_pass": True, "ret_12m": 0.2},
                 "components": {"gate_factor": 0.6}},
                {"id": "xle", "kind": "sector", "ticker": "XLE", "name": "Energy",
                 "conviction": {"score": 62, "label_en": "Constructive", "dir": "up",
                                "confluence": {"agree": 2}, "score_version": 2},
                 "forward": {"trend_pass": True, "ret_12m": 0.1},
                 "components": {"gate_factor": 0.6}}],
            "baskets": []}
    assert scg.append_central_log(data) == 2
    df = pd.read_parquet(p)
    assert "score_version" in df.columns
    assert list(df.columns) == prior_cols + ["score_version"]   # prior columns untouched
    xlk = df[df["id"] == "xlk"].iloc[0]
    assert xlk["score"] == 70                       # keep-first keeps the earlier row …
    assert xlk["label"] == "Accumulate" and xlk["dir"] == "up"
    assert pd.isna(xlk["score_version"])            # … and the prior row is not rewritten
    xle = df[df["id"] == "xle"].iloc[0]
    assert xle["score"] == 62 and xle["score_version"] == 2   # score and version together


# ── (c) segmented grader ───────────────────────────────────────────────────────

N_BARS = 180
IDX = pd.bdate_range("2026-01-02", periods=N_BARS)   # IDX[1]=Jan 5, IDX[21]=Feb 3
BASE_KEYS = ("available", "n_calls", "grader_schema_version", "interpretation",
             "dates", "horizons_d", "by_horizon", "freeze_start",
             "basket_return_valid_start", "pre_freeze_note", "n_graded")
D_JAN = str(IDX[1].date())
D_FEB = str(IDX[21].date())
M_JAN = IDX[1].strftime("%Y-%m")
M_FEB = IDX[21].strftime("%Y-%m")


def _call(i, date, ticker, direction, score=50.0, version=None) -> dict:
    row = {"date": date, "id": f"s-{i}", "kind": "sector",
           "ticker": ticker, "basket_id": None, "name": ticker,
           "score": score, "label": "Constructive", "dir": direction,
           "confluence": True, "trend_pass": True, "ret_12m": 0.1,
           "gate_factor": 1.0, "level": None}
    if version is not None:
        row["score_version"] = version
    return row


def _two_point(f: float, call_date: str, h: int = 21) -> list[float]:
    """Path whose h-bar forward return from call_date is exactly f (next-bar fill)."""
    v = [100.0] * N_BARS
    pos = IDX.get_loc(pd.Timestamp(call_date))
    v[pos + 1 + h] = 100.0 * (1.0 + f)
    return v


def _grade(tmp_path, monkeypatch, rows, paths) -> dict:
    p = tmp_path / "sector_central" / "calls.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(p, index=False)
    panel = pd.DataFrame({t: pd.Series(v, index=IDX) for t, v in paths.items()})
    panel["SPY"] = 100.0                      # flat bench → excess == fwd exactly
    monkeypatch.setattr(scg.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(scg, "_yahoo_panel", lambda: panel)
    monkeypatch.setattr(scg, "_basket_levels", lambda: {})
    return scg.grade()


def _legacy_rows():
    """4 matured legacy rows on two dates, hand-computable: Jan 5 → 1 up ok, 1 up flat;
    Feb 3 → 1 down ok, 1 neutral. dir_hit_rate = 2/4 = 0.5."""
    return [_call(1, D_JAN, "T1", "up", score=10.0),
            _call(2, D_JAN, "T2", "up", score=20.0),
            _call(3, D_FEB, "T3", "down", score=30.0),
            _call(4, D_FEB, "T4", "neutral", score=40.0)]


def _legacy_paths():
    return {"T1": _two_point(.05, D_JAN), "T2": _two_point(0.0, D_JAN),
            "T3": _two_point(-.06, D_FEB), "T4": _two_point(-.01, D_FEB)}


def test_base_keys_byte_identical_legacy_vs_mixed(tmp_path, monkeypatch):
    legacy = _grade(tmp_path, monkeypatch, _legacy_rows(), _legacy_paths())
    assert legacy["by_horizon"]["21d"]["dir_hit_rate"] == 0.5     # graded, not accruing
    # the mixed frame adds two version-2 rows (one on a NEW March date, one on the
    # SAME Feb date) — the Feb cohort month therefore spans the activation
    d_mar = str(IDX[41].date())
    mixed_rows = _legacy_rows() + [
        _call(5, d_mar, "V1", "up", score=50.0, version=2),
        _call(6, D_FEB, "V2", "down", score=60.0, version=2)]
    mixed_paths = {**_legacy_paths(), "V1": _two_point(.02, d_mar),
                   "V2": _two_point(.09, D_FEB)}   # v2 down call is WRONG (+9%)
    mixed = _grade(tmp_path, monkeypatch, mixed_rows, mixed_paths)
    for k in BASE_KEYS:
        assert json.dumps(mixed[k]) == json.dumps(legacy[k]), f"base key drifted: {k}"
    # the wrong v2 call never leaks into the legacy hit rate (pooled it would be 2/6)
    assert mixed["by_horizon"]["21d"]["dir_hit_rate"] == 0.5


def test_frame_without_column_equals_all_null_column(tmp_path, monkeypatch):
    rows = _legacy_rows()
    paths = _legacy_paths()
    no_col = _grade(tmp_path, monkeypatch, rows, paths)
    null_col = _grade(tmp_path, monkeypatch,
                      [dict(r, score_version=None) for r in rows], paths)
    for k in BASE_KEYS + ("score_version_segments", "by_score_version"):
        assert json.dumps(no_col[k]) == json.dumps(null_col[k]), f"null column drifted: {k}"
    assert no_col["by_score_version"] == {}


def test_segmentation_splits_versions_and_cohort_months(tmp_path, monkeypatch):
    d_mar = str(IDX[41].date())
    m_mar = IDX[41].strftime("%Y-%m")
    rows = _legacy_rows() + [
        _call(5, d_mar, "V1", "up", score=50.0, version=2),     # +2% → correct
        _call(6, D_FEB, "V2", "down", score=60.0, version=2),   # +9% → WRONG
        _call(7, d_mar, "V3", "up", score=70.0, version=2)]     # +3% → correct
    paths = {**_legacy_paths(), "V1": _two_point(.02, d_mar),
             "V2": _two_point(.09, D_FEB), "V3": _two_point(.03, d_mar)}
    g = _grade(tmp_path, monkeypatch, rows, paths)

    # segments: exact counts, dates as stored, roles
    assert g["score_version_segments"] == {
        "1": {"n_calls": 4, "first_date": D_JAN, "last_date": D_FEB,
              "role": "legacy — the top-level fields"},
        "2": {"n_calls": 3, "first_date": D_FEB, "last_date": d_mar,
              "role": "score version 2 — graded only under by_score_version"},
    }
    # the legacy top-level never sees the v2 rows: n_calls, dates, cohort months
    assert g["n_calls"] == 4
    assert g["dates"] == [D_JAN, D_FEB]
    h21 = g["by_horizon"]["21d"]
    assert h21["by_cohort_month"][M_FEB] == {"n_logged": 2, "n_matured": 2,
                                             "n_accruing": 0, "n_excluded": 0}
    assert h21["dir_hit_rate"] == 0.5                        # 2/4 legacy, v2 excluded

    # the v2 block is a full same-structure scorecard on the v2 rows ONLY (3 rows
    # → the graded path, so every legacy + v2 by_horizon key is present)
    v2 = g["by_score_version"]["2"]
    assert v2["available"] is True and v2["n_calls"] == 3
    assert v2["grader_schema_version"] == 2 and v2["interpretation"] == scg._INTERPRETATION
    assert v2["dates"] == [D_FEB, d_mar]
    v2h = v2["by_horizon"]["21d"]
    assert v2h["n"] == 3 and "note" not in v2h
    assert v2h["dir_hit_rate"] == round(2 / 3, 3)            # the wrong v2 call scores HERE
    assert v2h["dir_hit_rate_definition"] == scg._DIR_HIT_RATE_DEFINITION
    for k in ("n_directional", "n_neutral", "n_correct_directional", "counts",
              "rank_ic_distribution", "excess_distribution", "by_cohort_month",
              "by_tier", "invalidated_membership", "invalidated_pre_chain"):
        assert k in v2h, f"v2 by_horizon lost key {k}"
    # the cohort month that spans the activation is SPLIT, never pooled:
    # Feb = 2 legacy (top-level above) + 1 v2 (here); Mar = 2 v2 only
    assert v2h["by_cohort_month"] == {M_FEB: {"n_logged": 1, "n_matured": 1,
                                              "n_accruing": 0, "n_excluded": 0},
                                      m_mar: {"n_logged": 2, "n_matured": 2,
                                              "n_accruing": 0, "n_excluded": 0}}
    assert v2["n_graded"] == 3


def test_no_v2_rows_by_score_version_empty_and_segments_legacy_only(tmp_path, monkeypatch):
    g = _grade(tmp_path, monkeypatch, _legacy_rows(), _legacy_paths())
    assert g["by_score_version"] == {}
    assert list(g["score_version_segments"]) == ["1"]
    assert g["score_version_segments"]["1"]["n_calls"] == g["n_calls"] == 4


# ── (d) publication record crowding_input ─────────────────────────────────────

class _StubTemplate:
    def render(self, **kwargs):
        return "<html>stub</html>"


class _StubEnvironment:
    def __init__(self, *args, **kwargs):
        self.globals = {}

    def get_template(self, name):
        return _StubTemplate()


_SEG_WITH_2 = {"available": True,
               "score_version_segments": {
                   "1": {"n_calls": 9, "first_date": "2026-09-01",
                         "last_date": "2026-10-20", "role": "legacy — the top-level fields"},
                   "2": {"n_calls": 1, "first_date": "2026-10-21",
                         "last_date": "2026-10-21", "role": "score version 2 — graded only under by_score_version"}},
               "by_score_version": {}}


def _run_main(monkeypatch, tmp_path, *, meta, grader=_SEG_WITH_2, grade_raises=False) -> dict:
    """The smallest builder path tests/test_sector_central_publication.py already
    uses: main() with the engine, the grader, the flows board, the accumulation panel
    and the Jinja environment stubbed. Returns the free JSON's publication record."""
    import lib.config as config_mod
    monkeypatch.setattr(config_mod, "ROOT", tmp_path)
    monkeypatch.setattr(
        config_mod, "load",
        lambda: {"storage": {"site_dir": "site"},
                 "sector_central_gate": {"gated": True, "preview_rows": 1}})
    site = tmp_path / "site"
    (site / "basketdata").mkdir(parents=True, exist_ok=True)
    (site / "basketdata" / "action_board.json").write_text(json.dumps(
        {"as_of": "2026-10-18", "action_board": {"buy_now": [
            {"slug": "FREE-ROW-A", "name": "Free Row A"},
            {"slug": "LOCKED-ROW-B", "name": "Locked Row B"},
            {"slug": "LOCKED-ROW-C", "name": "Locked Row C"}]}}), encoding="utf-8")

    import engine.sector_central as sc
    monkeypatch.setattr(sc, "compute", lambda: {
        "as_of": "2026-10-18",
        "sectors": [{"id": "xlk", "name": "Technology",
                     "conviction": {"score": 60, "label_en": "Constructive"}}],
        "baskets": [], "meta": meta})
    import engine.sector_central_grader as cg
    monkeypatch.setattr(cg, "append_central_log", lambda data: 0)
    if grade_raises:
        def _boom():
            raise RuntimeError("grader down")
        monkeypatch.setattr(cg, "grade", _boom)
    else:
        monkeypatch.setattr(cg, "grade", lambda: grader)

    import scripts.build_sector_central as bsc
    monkeypatch.setattr(bsc, "Environment", _StubEnvironment)
    monkeypatch.setattr(bsc, "_flows_section_html", lambda: "<div>flows</div>")
    monkeypatch.setattr(bsc, "_accumulation_rows", lambda: ([], None))
    assert bsc.main() == 0
    free = json.loads((site / "sectordata" / "sector_central.json").read_text(encoding="utf-8"))
    return free["publication"]


def test_publication_crowding_input_resolved(tmp_path, monkeypatch):
    pub = _run_main(monkeypatch, tmp_path, meta={
        "n_baskets": 2, "conviction_score_version": 2,
        "membership_coverage": {"n_crowding_unresolved": 0}})
    assert pub["crowding_input"] == {
        "status": "resolved", "score_version": 2,
        "first_active_session": "2026-10-21",
        "n_baskets": 2, "n_baskets_resolved": 2}


def test_publication_crowding_input_partial_no_v2_note(tmp_path, monkeypatch):
    grader = {"available": True,
              "score_version_segments": {"1": {"n_calls": 9, "first_date": "2026-09-01",
                                               "last_date": "2026-10-20", "role": "legacy"}},
              "by_score_version": {}}
    pub = _run_main(monkeypatch, tmp_path, meta={
        "n_baskets": 2, "conviction_score_version": 2,
        "membership_coverage": {"n_crowding_unresolved": 1}}, grader=grader)
    assert pub["crowding_input"] == {
        "status": "partial", "score_version": 2,
        "first_active_session": None,
        "n_baskets": 2, "n_baskets_resolved": 1,
        "first_active_note": "no version-2 call logged yet"}


def test_publication_crowding_input_no_members_resolved(tmp_path, monkeypatch):
    grader = {"available": True,
              "score_version_segments": {"1": {"n_calls": 9, "first_date": "2026-09-01",
                                               "last_date": "2026-10-20", "role": "legacy"}},
              "by_score_version": {}}
    pub = _run_main(monkeypatch, tmp_path, grader=grader, meta={
        "n_baskets": 2, "conviction_score_version": 2,
        "membership_coverage": {"n_crowding_unresolved": 2}})
    assert pub["crowding_input"]["status"] == "no_members_resolved"
    assert pub["crowding_input"]["n_baskets_resolved"] == 0
    assert pub["crowding_input"]["first_active_note"] == "no version-2 call logged yet"


def test_publication_crowding_input_grader_failure_never_raises(tmp_path, monkeypatch):
    pub = _run_main(monkeypatch, tmp_path, grade_raises=True, meta={
        "n_baskets": 2, "conviction_score_version": 2,
        "membership_coverage": {"n_crowding_unresolved": 0}})
    assert pub["crowding_input"] == {
        "status": "resolved", "score_version": 2,
        "first_active_session": None,
        "n_baskets": 2, "n_baskets_resolved": 2,
        # RB13 F2: the builder's own except-path scorecard says why — propagated as-is
        "first_active_note": "grader error"}


def test_publication_crowding_input_unavailable_grader_carries_its_note(tmp_path, monkeypatch):
    """RB13 F2: a scorecard that says available=False carries its own reason
    ("no calls logged yet" / "unreadable: ..." / "empty") — propagate it instead
    of the generic "grader unavailable", which is reserved for a missing/raising grader."""
    pub = _run_main(monkeypatch, tmp_path, grader={"available": False, "note": "no calls logged yet"},
                    meta={"n_baskets": 2, "conviction_score_version": 2,
                          "membership_coverage": {"n_crowding_unresolved": 0}})
    assert pub["crowding_input"]["first_active_session"] is None
    assert pub["crowding_input"]["first_active_note"] == "no calls logged yet"
    pub = _run_main(monkeypatch, tmp_path, grader={"available": False},
                    meta={"n_baskets": 2, "conviction_score_version": 2,
                          "membership_coverage": {"n_crowding_unresolved": 0}})
    assert pub["crowding_input"]["first_active_note"] == "grader unavailable"


def test_grader_surfaces_frame_the_version_one_scorecard():
    """RB13 F1: after v2 activation the legacy top-level scorecard is the
    version-1 cohort; both the page grader and the rail footer must say so from
    score_version_segments['1'].last_date and mark v2 accruing from by_score_version['2']."""
    root = Path(__file__).resolve().parents[1]
    page = (root / "templates" / "sector_central.html.j2").read_text(encoding="utf-8")
    rail = (root / "templates" / "si_workspace.js").read_text(encoding="utf-8")
    for src in (page, rail):
        assert "score_version_segments" in src and "by_score_version" in src
        assert "graderVersionFrame(" in src
    assert "Scorecard above: score version 1 calls through " in page
    assert "version 2 accruing (n=" in page
    assert "v1 calls through " in rail and "v2 accruing n=" in rail
    # the framing uses the existing rg-k span, never an undefined chip class
    frame = page[page.index("function graderVersionFrame"):]
    frame = frame[:frame.index("return out+'</div>';")]
    assert 'class="rg-k"' in frame and "chip" not in frame


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
