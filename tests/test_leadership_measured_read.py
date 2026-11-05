"""T17 contract tests: the bounded measured group read (lane LR-T17-1).

One bounded, display-tier ``measured_read`` projection over the existing owners
(engine.sector_cycles payload + engine.rotation_events payload) plus its
sector_central wiring. Semantics 1-11 follow the ORCH-PROD frozen spec
(FROZEN_AT 2026-10-14T05:15:44Z); each has at least one ``test_s<N>_`` test.

Pure synthetic inputs only: no network, no ``data/`` or ``site/`` reads, no
clock reads, no builder invocations. The producer->parser pin (s9) freezes
``tests/fixtures/leadership_rotation/measured_read_v1.json`` byte-identically;
the Terminal lane parses that fixture with the real TS reader.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from engine import leadership_rotation_context as lrc
from engine.leadership_rotation_context import (
    MEASURED_READ_MAX_EVENT_ROWS,
    MEASURED_READ_SCHEMA,
    ResearchEstimate,
    Unmeasured,
    breadth,
    is_measured,
    us_sector_cohort,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "leadership_rotation" / "measured_read_v1.json"
FORBIDDEN_KEY_SUBSTRINGS = ("score", "combined", "composite", "entry", "probability", "conviction")

# --- semantic 11: scratch-only sentinel (owner bytes must be byte-identical) ---
_SENTINEL_PATHS = (
    REPO_ROOT / "data" / "us_sector_rotation" / "latest.json",
    REPO_ROOT / "data" / "baskets" / "membership.json",
    REPO_ROOT / "site" / "marketdata" / "rotation_events.json",
    REPO_ROOT / "site" / "sectordata" / "sector_central.json",
)


def _sha(path: Path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


_SENTINEL_BEFORE = {str(p): _sha(p) for p in _SENTINEL_PATHS}

# --- frozen synthetic producer inputs ------------------------------------------
AS_OF = "2026-10-09"
# 9 measured members of the 11-ticker cohort; XLK carries a literal 0.0 (a valid
# measurement), XLU is thin_history, XLRE is entirely absent from the payload.
_H63 = {"XLB": -1.4, "XLC": 2.3, "XLE": 4.1, "XLF": 1.2, "XLI": -0.7,
        "XLK": 0.0, "XLP": -2.2, "XLV": 0.9, "XLY": 3.3}
_H21 = {"XLB": -0.6, "XLC": 1.1, "XLE": 2.4, "XLF": 0.3, "XLI": -0.2,
        "XLK": -0.5, "XLP": -1.0, "XLV": 0.2, "XLY": 1.7}
_HISTORY_DATES = ("2026-10-07", "2026-10-08", "2026-10-09")


def _history(ticker: str) -> list[dict]:
    return [
        {"date": d,
         "rs_21d": round(_H21[ticker] + i * 0.1, 1),
         "rs_63d": round(_H63[ticker] + i * 0.25, 1)}
        for i, d in enumerate(_HISTORY_DATES)
    ]


def _sector_rec(ticker: str, meta_info: dict) -> dict:
    measured = ticker in _H63
    return {
        "id": ticker.lower(), "ticker": ticker, "kind": "sector",
        "name": meta_info["name"], "name_zh": meta_info["name_zh"],
        "group": meta_info["group"], "accent": meta_info["accent"],
        "proj": {"tilt": "mixed", "nextTurn": "peak", "low": "2026-07", "high": "2027-01"},
        "now": {"pos": 55.0, "phase": "Expansion", "phaseLabel": "Trending", "signal": None,
                "osc_slope": -0.2, "rs_rank": 1, "above200d": True,
                "rs_21d": _H21.get(ticker), "rs_63d": _H63.get(ticker),
                "thin_history": ticker == "XLU"},
        "rs_history": _history(ticker) if measured else [],
    }


def _build_cyc_payload(as_of: str = AS_OF, history_as_of: str | None = None) -> dict:
    from engine import sector_cycles

    sectors = [_sector_rec(t, info) for t, info in sorted(sector_cycles.SECTORS.items())
               if t != "XLRE"]  # XLRE: the missing member
    return {
        "meta": {"asOf": as_of, "benchmark": "SPY",
                 "rs_history": {"schema": "sector_cycles.rs_history.v1",
                                "as_of": history_as_of if history_as_of is not None else as_of}},
        "sectors": sectors,
    }


def _build_rotation_payload(as_of: str = AS_OF) -> dict:
    active = [
        # v1 in-sector shape (step_pairs): from_leg/to_leg, no event_type
        {"id": "xlk-xle:handoff", "sector": "Technology",
         "sector_name_en": "Technology", "sector_name_zh": "科技",
         "from_leg": {"key": "ai_semis", "name_en": "AI Semis", "name_zh": "AI半导体",
                      "tier": "primary"},
         "to_leg": {"key": "energy", "name_en": "Energy", "name_zh": "能源", "tier": "primary"},
         "started": "2026-09-21", "day_n": 14, "asof": as_of, "severity": "major",
         "receipts": {}, "confirmed_tonight": False, "copy_en": "e", "copy_zh": "z"},
        # v2 cross shape (step_cross_pairs): event_type/donor/receiver
        {"id": "xly-xlp:cross", "event_type": "cross_handoff",
         "from_sector": "Consumer Discretionary", "to_sector": "Consumer Staples",
         "donor": {"key": "disc", "name_en": "Discretionary", "name_zh": "非必需消费",
                   "tier": "secondary"},
         "receiver": {"key": "staples", "name_en": "Staples", "name_zh": "必需消费"},
         "started": "2026-10-01", "day_n": 6, "asof": as_of, "severity": "notable",
         "severity_effective": "notable", "receipts": {}, "confirmed_tonight": False,
         "lapse_count": 0, "neg_run": 0},
    ]
    return {
        "schema": "rotation_events.v1", "ok": True, "as_of": as_of,
        "generated_utc": "2026-10-09T22:05:00Z", "active": active,
        "early_context": {
            "schema": "rotation_early_context/v1",
            "definition_id": "rotation_early_context/1",
            "as_of": as_of, "display_only": True, "state": "watch",
            "reason_codes": ["PARTIAL_COVERAGE"],
            "pairs": [{"pair_id": "ec-xlf-xlu", "num": "XLF", "den": "XLU",
                       "context_group": "defensive_sector"}],
            "prior_loser_constituent_claim": False,
            "coverage": {"registered_pairs": 2, "evaluable_2s": 2, "positive_2s": 1,
                         "missing_pair_ids": [],
                         "groups": {"defensive_sector": {"registered": 1, "evaluable_2s": 1,
                                                         "positive_2s": 0},
                                    "retailer_context": {"registered": 1, "evaluable_2s": 1,
                                                         "positive_2s": 1},
                                    "broadening_proxy": {"registered": 0, "evaluable_2s": 0,
                                                         "positive_2s": 0}}},
            "availability": {"status": "AVAILABLE", "available_at": None},
            "lineage": {"definition_id": "rotation_early_context/1", "status": "AVAILABLE",
                        "roots": [], "revisions": {},
                        "dependency_groups": ["equity_price"],
                        "derived_from": ["oracle.ratio_lens"]},
        },
    }


def _build_fixture_payload():
    """The frozen producer inputs behind measured_read_v1.json (9 measured,
    1 thin_history, 1 missing, a literal 0.0 member, early_context available,
    confirmed_events available with 2 rows)."""
    return _build_cyc_payload(), _build_rotation_payload()


def _build_many_events(n: int = 50, dup: int = 3) -> list[dict]:
    evs = [
        {"id": f"ev-{i:02d}", "event_type": "into_strength", "sector": "Technology",
         "from_leg": {"key": f"d{i:02d}"}, "to_leg": {"key": f"r{i:02d}"},
         "started": "2026-10-01", "day_n": i + 1, "asof": AS_OF, "severity": "standard"}
        for i in range(n - dup)
    ]
    evs.extend(dict(evs[j]) for j in range(dup))  # duplicate ids: first wins
    return evs


def _serialize(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def _forbidden_keys(obj) -> list:
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(s in str(k).lower() for s in FORBIDDEN_KEY_SUBSTRINGS):
                found.append(str(k))
            found.extend(_forbidden_keys(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_forbidden_keys(v))
    return found


# ---------------------------------------------------------------- semantics ----

def test_s1_distinct_objects_never_merged():
    cyc, rot = _build_fixture_payload()
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    # the five generations of evidence are separate top-level keys
    for key in ("groups", "early_context", "confirmed_events", "research_estimate"):
        assert key in out
    for g in out["groups"]:
        assert set(g) == {"group_id", "group_kind", "name_en", "name_zh",
                          "current", "reconstruction"}
        assert set(g["current"]) == {"status", "reason", "rs_21d", "rs_63d", "units",
                                     "metric", "rank", "z"}
        assert set(g["reconstruction"]) == {"mode", "naturally_observed", "status", "reason",
                                            "points", "first", "last", "source"}
        assert g["reconstruction"]["naturally_observed"] is False
    # early-context pairs are never confirmed-event rows and never counted
    ec_pair_ids = {p["pair_id"] for p in rot["early_context"]["pairs"]}
    row_ids = {r["id"] for r in out["confirmed_events"]["rows"]}
    assert ec_pair_ids and not (ec_pair_ids & row_ids)
    assert out["confirmed_events"]["n_active"] == len(rot["active"])
    assert out["early_context"]["context_only"] is True
    assert out["research_estimate"] == {"status": "unavailable", "reason": "no_admitted_model"}


def test_s2_generation_mismatch_withholds_events():
    cyc, rot = _build_fixture_payload()
    off = "2026-10-08"
    rot_off = dict(rot, as_of=off, early_context=dict(rot["early_context"], as_of=off))
    out = lrc.measured_group_read(cyc, rotation_payload=rot_off)
    ce = out["confirmed_events"]
    assert ce["status"] == "incompatible_generation"
    assert ce["rows"] == [] and ce["n_active"] is None and ce["truncated"] is False
    # both mismatched dates stay printed
    assert ce["as_of"] == off
    assert out["generation"]["session_end"] == AS_OF
    ec = out["early_context"]
    assert ec["status"] == "incompatible_generation"
    assert ec["state"] is None and ec["as_of"] == off
    # rs_history generation mismatch withholds EVERY reconstruction
    cyc_hist = _build_cyc_payload(history_as_of=off)
    out2 = lrc.measured_group_read(cyc_hist, rotation_payload=rot)
    assert all(g["reconstruction"]["status"] == "incompatible_generation"
               and g["reconstruction"]["reason"] == "history_as_of_mismatch"
               for g in out2["groups"])
    assert out2["generation"]["history_as_of"] == off  # the mismatch stays visible


def test_s3_unknown_is_never_zero():
    cyc, rot = _build_fixture_payload()
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    by_id = {g["group_id"]: g for g in out["groups"]}
    xlk, xlre, xlu = by_id["XLK"]["current"], by_id["XLRE"]["current"], by_id["XLU"]["current"]
    # a literal 0.0 IS measured
    assert xlk["status"] == "measured" and xlk["rs_63d"] == 0.0 and xlk["reason"] is None
    assert isinstance(xlk["rank"], int) and isinstance(xlk["z"], float)
    # unknown stays null, is never ranked, never z-scored
    assert xlre["status"] == "unmeasured" and xlre["rs_63d"] is None
    assert xlre["rank"] is None and xlre["z"] is None and xlre["reason"] == "missing_input"
    assert xlu["status"] == "unmeasured" and xlu["reason"] == "thin_history"
    # breadth counts XLK (0.0 is not positive) in n but NOT in k; XLRE/XLU in neither
    assert out["cohort"]["measured_n"] == 9
    assert out["cohort"]["positive_breadth"]["coverage"] == 9 / 11
    positives = sum(1 for t in _H63 if _H63[t] > 0)
    assert out["cohort"]["positive_breadth"]["k_over_n"] == positives / 9
    assert ["XLRE", "missing_input"] in out["cohort"]["missing"]
    assert ["XLU", "thin_history"] in out["cohort"]["missing"]
    assert out["cohort"]["expected_n"] == 11 and out["status"] == "partial"
    # 0 measured -> unavailable, breadth from breadth(0, 0, 11)
    out0 = lrc.measured_group_read({"meta": {"asOf": AS_OF, "benchmark": "SPY"}, "sectors": []})
    assert out0["status"] == "unavailable" and out0["cohort"]["measured_n"] == 0
    assert out0["cohort"]["positive_breadth"] == breadth(0, 0, 11).to_dict()
    assert out0["cohort"]["positive_breadth"]["coverage"] == 0.0


def test_s4_no_double_count():
    cyc, rot = _build_fixture_payload()
    many = dict(rot, active=_build_many_events(50, dup=3))
    out = lrc.measured_group_read(cyc, rotation_payload=many)
    ce = out["confirmed_events"]
    assert ce["n_active"] == 47  # 50 rows, 3 duplicate ids -> first wins
    assert len(ce["rows"]) == MEASURED_READ_MAX_EVENT_ROWS == 12
    assert ce["truncated"] is True
    ids = [r["id"] for r in ce["rows"]]
    assert len(ids) == len(set(ids))  # no repeated id
    # the reconstructed trail is referenced, never copied (no embedded points)
    for g in out["groups"]:
        if g["group_id"] in _H63:
            assert g["reconstruction"]["points"] == 3  # count only
        else:  # thin_history / missing members carry no trail count
            assert g["reconstruction"]["points"] == 0
        assert "rs_history" not in g["reconstruction"]
    # source_roots deduped + sorted; rotation root only when actually read
    assert out["source_roots"] == ["engine.rotation_events", "engine.sector_cycles"]
    assert lrc.measured_group_read(cyc)["source_roots"] == ["engine.sector_cycles"]


def test_s5_no_combined_entry_score():
    cyc, rot = _build_fixture_payload()
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    assert _forbidden_keys(out) == []
    # an admitted ResearchEstimate is the ONLY object allowed its own vocabulary
    est = ResearchEstimate(
        target="sector_relative_wealth_sign_21d", horizon_sessions=21, origin="t0",
        exit_rule="hold_to_horizon", model="m", protocol="prereg",
        cohort_id="us_sectors_11", training_cutoff="2026-01-01",
        supported_population="us_sectors_11", uncertainty_definition="oos_ci",
        evidence_tier="research", probability=0.4)
    out_est = lrc.measured_group_read(cyc, rotation_payload=rot, research_estimate=est)
    assert out_est["research_estimate"] == est.to_dict()
    rest = {k: v for k, v in out_est.items() if k != "research_estimate"}
    assert _forbidden_keys(rest) == []


def test_s6_bounded_output():
    cyc, rot = _build_fixture_payload()
    out = lrc.measured_group_read(cyc, rotation_payload=dict(rot, active=_build_many_events(50)))
    blob = json.dumps(out, allow_nan=False)  # must succeed AND stay bounded
    assert len(blob) <= 16384
    assert len(out["groups"]) == 11
    # json round-trips (parser pin precondition)
    assert json.loads(blob)["schema"] == MEASURED_READ_SCHEMA


def test_s7_invalid_payloads_degrade_never_raise():
    cyc, _ = _build_fixture_payload()
    bad_payloads = ("not-a-mapping", 42,
                    {"schema": "wrong.v1", "ok": True, "as_of": AS_OF},
                    {"schema": "rotation_events.v1", "ok": False, "as_of": AS_OF},
                    {"schema": "rotation_events.v1", "ok": "true", "as_of": AS_OF})
    for bad in bad_payloads:
        out = lrc.measured_group_read(cyc, rotation_payload=bad)
        assert out["early_context"] == {
            "context_only": True, "status": "unavailable", "reason": "invalid_payload",
            "as_of": None, "state": None, "reason_codes": [], "coverage": None,
            "source": "/marketdata/rotation_events.json#early_context"}
        assert out["confirmed_events"]["status"] == "unavailable"
        assert out["confirmed_events"]["reason"] == "invalid_payload"
    out = lrc.measured_group_read(cyc, rotation_payload=None)
    assert out["early_context"]["reason"] == "missing_input"
    assert out["confirmed_events"]["reason"] == "missing_input"
    # malformed cycles payloads degrade to an all-unmeasured read, never raise
    for bad_cyc in (None, 42, {}, {"sectors": "nope"}, {"meta": None, "sectors": None}):
        out = lrc.measured_group_read(bad_cyc)
        assert out["schema"] == MEASURED_READ_SCHEMA
        assert out["status"] == "unavailable"
        assert len(out["groups"]) == 11
        assert all(g["current"]["status"] == "unmeasured" for g in out["groups"])
        assert out["generation"]["session_end"] is None
    # one hostile event leg never collapses the whole read to a projection error:
    # the bad row projects null legs and the valid row next to it still projects.
    # MUTATION: unguarded leg `.get` (a truthy non-mapping leg raises AttributeError)
    rot = _build_rotation_payload()
    hostile = dict(rot, active=[
        dict(rot["active"][0], id="hostile-legs", from_leg="x", to_leg=1,
             donor=["a"], receiver="r"),
        rot["active"][1],
    ])
    out = lrc.measured_group_read(cyc, rotation_payload=hostile)
    assert out["schema"] == MEASURED_READ_SCHEMA
    assert out.get("reason") != "projection_error"
    hostile_ce = out["confirmed_events"]
    assert hostile_ce["status"] == "available" and hostile_ce["n_active"] == 2
    rows = {row["id"]: row for row in hostile_ce["rows"]}
    assert rows["hostile-legs"]["from_key"] is None
    assert rows["hostile-legs"]["to_key"] is None
    assert rows["hostile-legs"]["sector"] == "Technology"   # the row still projects
    assert rows["xly-xlp:cross"]["from_key"] == "disc"
    assert rows["xly-xlp:cross"]["to_key"] == "staples"
    # a dict `sectors` container reads as empty and is never iterated by key
    dict_cyc = {"meta": {"asOf": AS_OF, "benchmark": "SPY",
                         "rs_history": {"schema": "sector_cycles.rs_history.v1",
                                        "as_of": AS_OF}},
                "sectors": {"XLK": {}}}
    out = lrc.measured_group_read(dict_cyc)
    assert out["schema"] == MEASURED_READ_SCHEMA
    assert out["status"] == "unavailable"
    assert out["cohort"]["measured_n"] == 0 and out["cohort"]["outside_cohort"] == []
    assert all(g["current"]["status"] == "unmeasured" for g in out["groups"])
    # horizon outside {rs_21d, rs_63d} is a programmer error
    with pytest.raises(ValueError):
        lrc.measured_group_read(cyc, horizon="rs_126d")
    with pytest.raises(ValueError):
        lrc.measured_group_read(cyc, horizon="")
    assert lrc.measured_group_read(cyc, horizon="rs_21d")["cohort"]["horizon"] == "rs_21d"


def test_s8_unchanged_downstream_and_fail_soft(tmp_path, monkeypatch):
    from engine import inputs as engine_inputs
    from engine import narrative_rotation
    from engine import sector_central
    from lib import config

    cyc, rot = _build_fixture_payload()
    # scratch root: every read (config.ROOT, data_dir, site_dir) lands in tmp_path
    site_root = tmp_path / "site"
    (site_root / "marketdata").mkdir(parents=True)
    (site_root / "marketdata" / "rotation_events.json").write_text(json.dumps(rot), encoding="utf-8")
    (tmp_path / "config.yml").write_text("storage:\n  site_dir: site\n  data_dir: data\n",
                                         encoding="utf-8")

    monkeypatch.setattr("engine.sector_cycles.compute", lambda: cyc)
    monkeypatch.setattr(sector_central, "market_context", lambda: {"heat": {}})
    monkeypatch.setattr(engine_inputs, "yahoo_closes", lambda: None)
    monkeypatch.setattr(narrative_rotation, "compute_narrative_rotation", lambda region: None)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(config, "ROOT", tmp_path)

    out_a = sector_central.compute()
    assert out_a is not None
    assert out_a["measured_read"]["schema"] == MEASURED_READ_SCHEMA
    assert out_a["measured_read"]["confirmed_events"]["status"] == "available"
    assert out_a["measured_read"]["confirmed_events"]["n_active"] == 2

    # wiring pin: compute() itself calls _measured_read and ships the key
    tree = ast.parse(Path(sector_central.__file__).read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "compute")
    calls = {ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}
    assert any("_measured_read" in c for c in calls)

    # forcing the projection to raise changes ONLY the measured_read key
    def _boom(*args, **kwargs):
        raise RuntimeError("forced projection failure")

    monkeypatch.setattr(lrc, "measured_group_read", _boom)
    out_b = sector_central.compute()
    assert out_b is not None
    stub = out_b.pop("measured_read")
    live = out_a.pop("measured_read")
    assert stub == {"schema": MEASURED_READ_SCHEMA, "status": "unavailable",
                    "reason": "projection_error"}
    assert out_b == out_a
    # the existing conviction score surface is untouched by the read
    assert all("conviction" in s for s in out_b["sectors"])


def test_s9_fixture_byte_identical():
    cyc, rot = _build_fixture_payload()
    assert FIXTURE.exists(), f"missing frozen fixture: {FIXTURE}"
    blob = _serialize(lrc.measured_group_read(cyc, rotation_payload=rot))
    assert FIXTURE.read_text(encoding="utf-8") == blob
    # deterministic: a fresh run reproduces the same bytes
    cyc2, rot2 = _build_fixture_payload()
    assert _serialize(lrc.measured_group_read(cyc2, rotation_payload=rot2)) == blob
    out = json.loads(blob)
    assert out["schema"] == MEASURED_READ_SCHEMA
    assert out["cohort"]["measured_n"] == 9 and out["status"] == "partial"
    by_id = {g["group_id"]: g for g in out["groups"]}
    assert by_id["XLK"]["current"]["rs_63d"] == 0.0
    assert by_id["XLRE"]["current"]["rs_63d"] is None
    assert out["early_context"]["status"] == "available"
    assert out["confirmed_events"]["status"] == "available"
    assert len(out["confirmed_events"]["rows"]) == 2


def test_s10_receipt_side_unknown_is_not_zero():
    from engine.leadership_receipt import build_receipt

    receipt = build_receipt(basket={}, theme={}, theme_intel={}, region="us", site=None)
    assert receipt.get("rel_20d") is None  # real owner output, unknown really is None
    gm = lrc.from_leadership_receipt(receipt, group_id="ai_semis",
                                     cohort_id="curated_themes", horizon="rel_20d")
    assert isinstance(gm.value, Unmeasured) and not is_measured(gm.value)
    assert gm.to_dict()["value"] == {"status": "unmeasured", "reason": "missing_input"}


def test_s11_scratch_only_no_owner_bytes_touched():
    after = {str(p): _sha(p) for p in _SENTINEL_PATHS}
    assert after == _SENTINEL_BEFORE, "suite touched owner data/site bytes"


# ------------------------------------------------- module invariants (extra) ----

def test_cohort_is_the_frozen_owner_cohort():
    assert us_sector_cohort() == tuple(sorted(us_sector_cohort()))
    assert len(us_sector_cohort()) == 11


# -------------------------------------- LR-FIX-A repairs (#9257 R1/R2, N-PB1) ----

def test_fix_a4_non_list_active_is_invalid_payload_not_zero():
    # MUTATION: `or []` coercion (a truthy non-list `active` reads as zero events)
    cyc, rot = _build_fixture_payload()
    for bad_active in ({}, "x", 7, True):
        ce = lrc.measured_group_read(cyc, rotation_payload=dict(
            rot, active=bad_active))["confirmed_events"]
        assert ce["status"] == "unavailable", bad_active
        assert ce["reason"] == "invalid_payload", bad_active
        assert ce["n_active"] is None, bad_active      # unknown, never a measured 0
        assert ce["rows"] == [] and ce["truncated"] is False
    # unmeasured is not zero: an absent or explicitly None `active` is MISSING input
    absent = {key: value for key, value in rot.items() if key != "active"}
    for no_active in (absent, dict(rot, active=None)):
        ce = lrc.measured_group_read(cyc, rotation_payload=no_active)["confirmed_events"]
        assert ce["status"] == "unavailable"
        assert ce["reason"] == "missing_input"
        assert ce["n_active"] is None and ce["rows"] == []
    # an empty list IS a measured zero and stays exactly as before
    ce = lrc.measured_group_read(cyc, rotation_payload=dict(rot, active=[]))["confirmed_events"]
    assert ce["status"] == "none" and ce["n_active"] == 0 and ce["rows"] == []
    # the as-of mismatch branch still takes precedence over both
    off = lrc.measured_group_read(cyc, rotation_payload=dict(
        rot, as_of="2026-10-08", active="x"))["confirmed_events"]
    assert off["status"] == "incompatible_generation"
    assert off["reason"] == "as_of_mismatch" and off["n_active"] is None


def test_fix_npb1_price_basis_reads_declared_basis():
    # MUTATION: hard-coded literal (`price_basis` never reads meta.rs_history.basis)
    rot = _build_rotation_payload()
    declared = (("tr", "total_return"), ("price", "price_only"),
                (None, "total_return"), ("px", "unknown"))
    projections = []
    for basis, expected in declared:
        cyc = _build_cyc_payload()
        if basis is None:
            assert "basis" not in cyc["meta"]["rs_history"]     # the absent case
        else:
            cyc["meta"]["rs_history"]["basis"] = basis
        out = lrc.measured_group_read(cyc, rotation_payload=rot)
        assert out["generation"]["price_basis"] == expected, basis
        projections.append(out)
    # the declared basis is a LABEL axis only: every measured value is identical
    blobs = {json.dumps([{"current": [g["current"] for g in proj["groups"]],
                          "cohort": proj["cohort"]}], sort_keys=True, allow_nan=False)
             for proj in projections}
    assert len(blobs) == 1
    assert projections[-1]["generation"]["price_basis"] == "unknown"
    assert projections[-1]["cohort"]["measured_n"] == projections[0]["cohort"]["measured_n"] == 9
    # a non-str basis is unknown too, and the reconstruction label stays hard-coded:
    # a source that LIES about its mode is still labelled reconstructed
    for lying in ({"basis": 7}, {"basis": ["tr"]},
                  {"basis": "tr", "mode": "original_retained", "naturally_observed": True}):
        cyc = _build_cyc_payload()
        cyc["meta"]["rs_history"].update(lying)
        out = lrc.measured_group_read(cyc, rotation_payload=rot)
        expected_basis = "total_return" if isinstance(lying["basis"], str) else "unknown"
        assert out["generation"]["price_basis"] == expected_basis, lying
        assert all(g["reconstruction"]["mode"] == "reconstructed_price_history"
                   and g["reconstruction"]["naturally_observed"] is False
                   for g in out["groups"])
