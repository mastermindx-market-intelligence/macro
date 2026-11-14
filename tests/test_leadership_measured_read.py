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
import copy
import hashlib
import json
from datetime import date, timedelta
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

    # Observe the public projection through the full compute path, regardless of
    # which pure-core helper owns the call after source capture.
    projection_calls = []
    original_projection = lrc.measured_group_read

    def _observe_projection(cycles, *args, **kwargs):
        projection_calls.append((cycles, kwargs))
        return original_projection(cycles, *args, **kwargs)

    monkeypatch.setattr(lrc, "measured_group_read", _observe_projection)
    out_a = sector_central.compute()
    assert out_a is not None
    assert out_a["measured_read"]["schema"] == MEASURED_READ_SCHEMA
    assert out_a["measured_read"]["confirmed_events"]["status"] == "available"
    assert out_a["measured_read"]["confirmed_events"]["n_active"] == 2
    dossier = out_a["measured_read"]["sector_dossiers"]
    assert dossier["schema"] == "leadership_rotation_context.sector_dossiers/v1"
    assert len(dossier["groups"]) == 11
    # This original fixture omits provenance: the published addendum stays null.
    assert dossier["measurement_status"] == "unavailable"

    assert len(projection_calls) == 1
    assert projection_calls[0][0] == cyc
    assert projection_calls[0][1]["rotation_payload"] == rot

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


# --- Persistent Sector Leadership: opt-in, separately qualified dossiers -------
# The legacy fixture and all preceding assertions remain unchanged. These tests
# qualify raw owner metadata independently of the permissive legacy projection.

def _qualified_dossier_payload():
    payload = _build_cyc_payload()
    payload["meta"]["rs_history"].update(
        basis="tr", benchmark="SPY", mode="reconstructed_price_history",
        naturally_observed=False,
    )
    return payload


def _compose_dossier(payload=None, read=None, **kwargs):
    compose_sector_dossiers = lrc._compose_sector_dossiers

    if payload is None:
        payload = _qualified_dossier_payload()
    if read is None:
        read = lrc.measured_group_read(payload)
    return compose_sector_dossiers(
        payload, read, expected_group_ids=us_sector_cohort(), **kwargs,
    )


def _dossier_rows(dossier):
    return {row["group_id"]: row for row in dossier["groups"]}


def _assert_dossier_withheld(dossier, reason):
    assert dossier["measurement_status"] == "unavailable"
    assert reason in dossier["diagnostics"]["qualification_reasons"]
    assert all(value is None for row in dossier["groups"]
               for value in row["relative_wealth_pct"].values())
    assert all(counts["positive_n"] is None
               for counts in dossier["cross_sector_breadth_counts"].values())
    json.dumps(dossier, allow_nan=False)


def test_dossier_opt_in_preserves_every_legacy_field_and_input():
    import copy

    payload = _qualified_dossier_payload()
    rotation = _build_rotation_payload()
    before = copy.deepcopy((payload, rotation))
    legacy = lrc.measured_group_read(payload, rotation_payload=rotation)
    enabled = lrc.measured_group_read(
        payload, rotation_payload=rotation, include_sector_dossiers=True,
    )
    dossier = enabled.pop("sector_dossiers")
    assert enabled == legacy
    assert (payload, rotation) == before
    assert "sector_dossiers" not in legacy
    assert len(_serialize({**enabled, "sector_dossiers": dossier}).encode()) <= 32768
    assert not _forbidden_keys(dossier)
    json.dumps(dossier, allow_nan=False)


@pytest.mark.parametrize("flag", [None, 0, 1, "false", [], {}])
def test_dossier_opt_in_requires_explicit_boolean(flag):
    with pytest.raises(ValueError, match="include_sector_dossiers"):
        lrc.measured_group_read(_qualified_dossier_payload(), include_sector_dossiers=flag)


def test_dossier_keeps_eleven_identities_zero_and_exact_native_windows():
    dossier = _compose_dossier()
    rows = _dossier_rows(dossier)
    assert list(rows) == list(us_sector_cohort())
    assert len(rows) == 11
    assert rows["XLK"]["relative_wealth_pct"]["rs_63d"] == 0.0
    assert rows["XLK"]["null_reasons"]["rs_63d"] is None
    assert rows["XLU"]["status"] == rows["XLRE"]["status"] == "unavailable"
    assert "thin_history" in rows["XLU"]["qualification_reasons"]
    assert "missing_group" in rows["XLRE"]["qualification_reasons"]
    assert dossier["windows_sessions"] == [21, 63]
    assert dossier["unavailable_windows"] == {
        "sessions": [5, 20], "reason": "not_supplied_by_owner",
    }
    assert dossier["cross_sector_breadth_counts"]["63"] == {
        "expected_n": 11, "measured_n": 9, "positive_n": 5,
    }
    assert dossier["population"] == "eleven_sector_etf_proxies"
    assert dossier["constituent_breadth"]["status"] == "unavailable"
    assert dossier["constituent_concentration"]["status"] == "unavailable"
    assert dossier["measurement_status"] == dossier["status"] == "partial"


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"),
                                   -float("inf"), "3.2", [], {}])
def test_dossier_rejects_malformed_measurements_without_losing_other_window(value):
    payload = _qualified_dossier_payload()
    next(row for row in payload["sectors"] if row["ticker"] == "XLK")["now"]["rs_63d"] = value
    row = _dossier_rows(_compose_dossier(payload))["XLK"]
    assert row["relative_wealth_pct"] == {"rs_21d": -0.5, "rs_63d": None}
    assert row["null_reasons"]["rs_63d"] == "invalid_measurement"
    assert row["status"] == "partial"


@pytest.mark.parametrize("where", ["native", "projected"])
def test_dossier_duplicate_identity_is_withheld_not_last_writer_wins(where):
    import copy

    payload = _qualified_dossier_payload()
    read = lrc.measured_group_read(payload)
    if where == "native":
        duplicate = copy.deepcopy(next(row for row in payload["sectors"] if row["ticker"] == "XLK"))
        duplicate["now"]["rs_63d"] = 900.0
        payload["sectors"].append(duplicate)
        read = lrc.measured_group_read(payload)
    else:
        read["groups"].append(copy.deepcopy(read["groups"][0]))
    duplicate_id = "XLK" if where == "native" else read["groups"][0]["group_id"]
    dossier = _compose_dossier(payload, read)
    assert dossier["diagnostics"]["duplicate_groups"] == [duplicate_id]
    row = _dossier_rows(dossier)[duplicate_id]
    assert row["status"] == "unavailable"
    assert "duplicate_group_identity" in row["qualification_reasons"]


@pytest.mark.parametrize("path,value,reason", [
    (("meta", "asOf"), None, "source_session_missing_or_invalid"),
    (("meta", "asOf"), "2026-02-30", "source_session_missing_or_invalid"),
    (("meta", "asOf"), "20261009", "source_session_missing_or_invalid"),
    (("meta", "benchmark"), None, "benchmark_missing_or_invalid"),
    (("meta", "benchmark"), "UNKNOWN", "benchmark_missing_or_invalid"),
    (("meta", "rs_history", "as_of"), None, "history_session_missing_or_invalid"),
    (("meta", "rs_history", "as_of"), "2026-10-08", "history_session_mismatch"),
    (("meta", "rs_history", "basis"), None, "return_basis_not_qualified"),
    (("meta", "rs_history", "basis"), "price", "return_basis_not_qualified"),
    (("meta", "rs_history", "basis"), [], "return_basis_not_qualified"),
    (("meta", "rs_history", "benchmark"), "QQQ", "benchmark_identity_mismatch"),
    (("meta", "rs_history", "schema"), "other", "history_schema_not_qualified"),
    (("meta", "rs_history", "mode"), None, "evidence_mode_not_qualified"),
    (("meta", "rs_history", "naturally_observed"), True, "evidence_mode_not_qualified"),
])
def test_dossier_withholds_unqualified_source_contract(path, value, reason):
    payload = _qualified_dossier_payload()
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    _assert_dossier_withheld(_compose_dossier(payload), reason)


@pytest.mark.parametrize("key,value,reason", [
    ("session_end", "2026-10-08", "source_session_mismatch"),
    ("benchmark", "QQQ", "benchmark_identity_mismatch"),
    ("cohort_id", "top_6", "cohort_identity_mismatch"),
    ("price_basis", "price_only", "return_basis_mismatch"),
])
def test_dossier_rejects_incompatible_projection_generation(key, value, reason):
    payload = _qualified_dossier_payload()
    read = lrc.measured_group_read(payload)
    read["generation"][key] = value
    _assert_dossier_withheld(_compose_dossier(payload, read), reason)


def test_dossier_checks_row_provenance_and_projection_values():
    payload = _qualified_dossier_payload()
    raw = next(row for row in payload["sectors"] if row["ticker"] == "XLK")
    raw["series_provenance"] = {"rs_basis": "price", "benchmark": "QQQ"}
    row = _dossier_rows(_compose_dossier(payload))["XLK"]
    assert row["status"] == "unavailable"
    assert set(row["qualification_reasons"]) == {
        "row_return_basis_mismatch", "row_benchmark_mismatch",
    }
    del raw["series_provenance"]
    read = lrc.measured_group_read(payload)
    group = next(row for row in read["groups"] if row["group_id"] == "XLK")
    group["current"]["rs_63d"] = 999.0
    row = _dossier_rows(_compose_dossier(payload, read))["XLK"]
    assert row["relative_wealth_pct"]["rs_63d"] is None
    assert row["null_reasons"]["rs_63d"] == "measurement_projection_mismatch"


@pytest.mark.parametrize("cutoff,reason", [
    ("2026-10-08T23:59:00Z", "source_session_after_decision_cutoff"),
    ("2026-10-09T00:00:00Z", "availability_time_missing"),
    ("2026-11-06T10:00:00+00:00", "availability_time_missing"),
    ("2026-11-06T10:00:00", "invalid_decision_cutoff"),
    ("not-a-time", "invalid_decision_cutoff"),
    (True, "invalid_decision_cutoff"),
])
def test_dossier_as_known_never_fabricates_original_availability(cutoff, reason):
    dossier = _compose_dossier(decision_cutoff=cutoff)
    _assert_dossier_withheld(dossier, reason)
    assert dossier["availability"]["mode"] == "as_known"
    assert dossier["availability"]["original_available_at"] is None
    assert dossier["availability"]["historically_admissible"] is False


def test_dossier_uses_only_actual_root_without_independence_or_trade_authority():
    payload = _qualified_dossier_payload()
    read = lrc.measured_group_read(payload, rotation_payload=_build_rotation_payload())
    read["source_roots"] += ["engine.sector_cycles", "irrelevant.source"]
    dossier = _compose_dossier(payload, read)
    audit = dossier["dependency_audit"]
    assert audit["source_roots"] == ["engine.sector_cycles"]
    assert audit["source_family_count"] == 1
    assert audit["independence"] == "not_established"
    assert audit["shared_rolling_windows"] is True
    assert all(value is False for value in dossier["authority"].values())
    assert dossier["source_generation"]["id"] is None
    assert dossier["source_generation"]["status"] == "unavailable"
    assert dossier["compatibility_key"] == read["generation"]["id"]
    assert dossier["freshness"]["status"] == "unverified"
    assert dossier["history"]["naturally_observed"] is False
    assert dossier["forecasts"] == {
        "status": "not_qualified", "expected_return": None,
        "persistence_estimate": None, "allocation_weight": None,
    }
    assert dossier["mechanism"]["status"] == dossier["risk"]["status"] == "unavailable"
    read["source_roots"] = ["engine.rotation_events"]
    _assert_dossier_withheld(_compose_dossier(payload, read), "measurement_source_root_missing")


@pytest.mark.parametrize("bad", [None, False, 1, "bad", [], {"sectors": {}}])
def test_dossier_malformed_inputs_degrade_to_bounded_missingness(bad):
    compose_sector_dossiers = lrc._compose_sector_dossiers

    dossier = compose_sector_dossiers(bad, bad, expected_group_ids=us_sector_cohort())
    assert len(dossier["groups"]) == 11
    assert dossier["measurement_status"] == "unavailable"
    assert len(json.dumps(dossier, allow_nan=False).encode()) < 32768


def test_dossier_bounds_input_before_indexing_and_excludes_outside_cohort():
    MAX_INPUT_ROWS = lrc._DOSSIER_MAX_INPUT_ROWS

    payload = _qualified_dossier_payload()
    read = lrc.measured_group_read(payload)
    payload["sectors"] = [{"ticker": "XLK"}] * (MAX_INPUT_ROWS + 1)
    _assert_dossier_withheld(_compose_dossier(payload, read), "input_rows_exceed_bound")
    payload = _qualified_dossier_payload()
    payload["sectors"] += [{"ticker": "QQQ", "now": {"rs_63d": 999.0}}, None,
                           {"ticker": ["XLK"]}]
    dossier = _compose_dossier(payload)
    assert dossier["diagnostics"]["outside_cohort"] == ["QQQ"]
    assert dossier["diagnostics"]["malformed_source_rows"] == 2
    assert len(dossier["groups"]) == 11
    assert dossier["cross_sector_breadth_counts"]["63"]["measured_n"] == 9


@pytest.mark.parametrize("provenance", [None, False, [], "total_return", {}])
def test_dossier_explicit_malformed_provenance_cannot_become_absent(provenance):
    payload = _qualified_dossier_payload()
    next(row for row in payload["sectors"] if row["ticker"] == "XLK")["series_provenance"] = provenance
    row = _dossier_rows(_compose_dossier(payload))["XLK"]
    assert row["status"] == "unavailable"
    assert "row_provenance_invalid" in row["qualification_reasons"]


@pytest.mark.parametrize("value,expected", [(-100.1, None), (-200.0, None),
                                           (-100.0, -100.0), (0.0, 0.0),
                                           (1200.0, 1200.0)])
def test_dossier_enforces_relative_wealth_domain_without_clipping_valid_values(value, expected):
    payload = _qualified_dossier_payload()
    next(row for row in payload["sectors"] if row["ticker"] == "XLK")["now"]["rs_63d"] = value
    row = _dossier_rows(_compose_dossier(payload))["XLK"]
    assert row["relative_wealth_pct"]["rs_63d"] == expected
    assert row["null_reasons"]["rs_63d"] == (
        "outside_relative_wealth_domain" if expected is None else None
    )


# --- Central publication adoption: the existing producer carries the addendum ---

def test_central_publishes_dossiers_without_changing_legacy_projection(monkeypatch):
    import copy
    from engine import sector_central

    cycles = _qualified_dossier_payload()
    rotation = _build_rotation_payload()
    before = copy.deepcopy((cycles, rotation))
    monkeypatch.setattr(sector_central, "_load_rotation_events", lambda: rotation)

    published = sector_central._measured_read(cycles)
    dossier = published.pop("sector_dossiers")
    assert published == lrc.measured_group_read(cycles, rotation_payload=rotation)
    assert (cycles, rotation) == before
    assert list(_dossier_rows(dossier)) == list(us_sector_cohort())
    rows = _dossier_rows(dossier)
    assert rows["XLK"]["relative_wealth_pct"] == {"rs_21d": -0.5, "rs_63d": 0.0}
    assert rows["XLK"]["null_reasons"] == {"rs_21d": None, "rs_63d": None}
    assert rows["XLU"]["null_reasons"]["rs_63d"] == "thin_history"
    assert rows["XLRE"]["null_reasons"]["rs_21d"] == "missing_group"
    assert dossier["cross_sector_breadth_counts"]["63"] == {
        "expected_n": 11, "measured_n": 9, "positive_n": 5,
    }
    assert all(value is False for value in dossier["authority"].values())
    assert dossier["source_generation"]["id"] is None
    assert dossier["availability"]["historically_admissible"] is False
    assert dossier["freshness"]["status"] == "unverified"
    assert dossier["history"]["naturally_observed"] is False
    json.dumps(dossier, allow_nan=False)


def test_central_keeps_legacy_numbers_when_dossier_source_is_unqualified(monkeypatch):
    from engine import sector_central

    cycles, rotation = _build_fixture_payload()
    monkeypatch.setattr(sector_central, "_load_rotation_events", lambda: rotation)
    published = sector_central._measured_read(cycles)
    dossier = published.pop("sector_dossiers")

    # Old owner metadata supports the legacy read but cannot be upgraded into a
    # qualified dossier merely because Central now publishes the optional field.
    assert published == lrc.measured_group_read(cycles, rotation_payload=rotation)
    assert published["cohort"]["measured_n"] == 9
    assert next(row for row in published["groups"] if row["group_id"] == "XLK")[
        "current"
    ]["rs_63d"] == 0.0
    _assert_dossier_withheld(dossier, "return_basis_not_qualified")
    assert list(_dossier_rows(dossier)) == list(us_sector_cohort())


# ---------------------------------------------------------------------------
# Persistent Sector Leadership: exact 5/20/63-session window measurements
# ---------------------------------------------------------------------------
#
# The exact-window measurement is a PURE function over an explicit captured
# panel, an explicit end/source session and an explicit canonical US session
# calendar. These tests are the counterexamples that pin the arithmetic:
# a 5-session return spans six session endpoints, interior gaps never move an
# endpoint, and the legacy rolling rs coordinate is preserved untouched.

PSL_FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "leadership_rotation"
PSL_COMPLETE_FIXTURE = PSL_FIXTURE_DIR / "sector_window_measurements.complete.v1.json"
PSL_UNAVAILABLE_FIXTURE = PSL_FIXTURE_DIR / "sector_window_measurements.unavailable.v1.json"

_PSL_END = "2026-11-05"
_PSL_BENCHMARK = "SPY"
_PSL_WINDOWS = (5, 20, 63)


def _psl_calendar(n: int = 300, end: str = _PSL_END) -> list[str]:
    """n canonical US sessions ending at *end*, from the incumbent US owner.

    The reference is ``lib.nyse_calendar`` -- the incumbent canonical US
    session reference that ``engine/session_anchor.py`` binds the US market
    to -- and NOT a weekday approximation. A weekday calendar counts US Labor
    Day 2026-09-07 as a session, so the 63-session window would start on
    2026-08-10 and every endpoint inside the window would sit one session
    late. The owner computes the scheduled full-day closures it knows; it is
    the reference, not a restatement of the whole exchange rule book.
    """
    from lib import nyse_calendar

    last = date.fromisoformat(end)
    if not nyse_calendar.is_session(last):
        raise ValueError(f"the calendar end {end} is not a canonical US session")
    start = nyse_calendar.session_n_back(last, n - 1)
    if start is None:
        raise ValueError(
            f"the US session reference cannot reach {n} sessions back from {end}")
    return [day.isoformat() for day in nyse_calendar.sessions_between(start, last)]


def _psl_path(seed: int, n: int) -> list[float]:
    """A deterministic, NON-UNIFORM strictly positive price path.

    The wobble is a fixed integer pattern, never a random draw, so every
    expected value in this file is reproducible byte-for-byte.
    """
    path: list[float] = []
    level = 50.0 * (1.0 + 0.01 * seed)
    for i in range(n):
        wobble = 1.0 + 0.0012 * (((i * 7 + seed * 3) % 7) - 3)
        level *= (1.0011 if i % 3 else 1.0006) * wobble
        path.append(level)
    return path


def _psl_panel(calendar: list[str], tickers: tuple[str, ...]) -> list[dict]:
    """The captured WIDE total-return panel: one row per session, one column per ticker."""
    n = len(calendar)
    bench = _psl_path(-1, n)
    paths = {ticker: _psl_path(index, n) for index, ticker in enumerate(tickers)}
    rows = []
    for i, day in enumerate(calendar):
        row = {"session": day, _PSL_BENCHMARK: bench[i]}
        for ticker in tickers:
            row[ticker] = paths[ticker][i]
        rows.append(row)
    return rows


def _psl_measure(closes=None, *, calendar=None, end=_PSL_END, source=None,
                 tickers=None, windows=_PSL_WINDOWS, population=None, binding=None):
    calendar = calendar if calendar is not None else _psl_calendar()
    tickers = tickers if tickers is not None else us_sector_cohort()
    closes = _psl_panel(calendar, tickers) if closes is None else closes
    return lrc.measure_sector_windows(
        closes,
        benchmark=_PSL_BENCHMARK,
        end_session=end,
        source_session=source if source is not None else end,
        reference_sessions=calendar,
        windows=windows,
        population=population,
        source_binding=binding,
    )


def _psl_cell(out: dict, ticker: str, window: str) -> dict:
    return next(g for g in out["groups"] if g["group_id"] == ticker)["windows"][window]


def _psl_composition(calendar: list[str], end: str, **overrides) -> dict:
    """The exact-window composition argument for one canonical calendar."""
    composition = {
        "closes": _psl_panel(calendar, us_sector_cohort()),
        "benchmark": _PSL_BENCHMARK,
        "end_session": end,
        "source_session": end,
        "reference_sessions": calendar,
    }
    composition.update(overrides)
    return composition


def _psl_frozen_panel() -> tuple[list[str], list[dict], tuple[str, ...]]:
    """The exact panel behind the two frozen PSL fixtures."""
    calendar = _psl_calendar()
    tickers = us_sector_cohort()
    return calendar, _psl_panel(calendar, tickers), tickers


def _psl_legacy_rs(closes: list[dict], ticker: str, sessions: int) -> float | None:
    """The incumbent ROLLING rs coordinate over the same captured panel.

    engine.sector_cycles._relative_strength_series_counted drops the rows whose
    price is missing and forward-fills the benchmark for up to five sessions;
    the legacy coordinate is then pct_change over the SURVIVING rows. This
    helper calls the incumbent itself, so the two semantics are compared
    against the real owner rather than a re-implementation.
    """
    import pandas as pd

    from engine import sector_cycles

    frame = pd.DataFrame([{k: v for k, v in row.items()} for row in closes])
    frame["session"] = pd.to_datetime(frame["session"])
    frame = frame.set_index("session").sort_index()
    rs, _excluded = sector_cycles._relative_strength_series_counted(
        frame, ticker, bench=_PSL_BENCHMARK)
    if len(rs) <= sessions:
        return None
    return float(rs.pct_change(sessions).iloc[-1] * 100)


def test_w1_exact_windows_distinguish_5_20_21_63():
    """A non-uniform price path separates the exact 5/20 windows from the
    legacy 21 and 63 coordinates: the four numbers are genuinely different."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    out = _psl_measure(closes, calendar=calendar)
    assert out["status"] == "available"
    assert out["windows_sessions"] == [5, 20, 63]
    cell5 = _psl_cell(out, "XLK", "5")
    cell20 = _psl_cell(out, "XLK", "20")
    cell63 = _psl_cell(out, "XLK", "63")
    values = [cell5["absolute_return_pct"], cell20["absolute_return_pct"], cell63["absolute_return_pct"]]
    assert len(set(values)) == 3, values
    # the legacy 21-session coordinate is a DIFFERENT window than the exact 20
    legacy21 = _psl_legacy_rs(closes, "XLK", 21)
    assert legacy21 is not None
    assert abs(legacy21 - cell20["relative_wealth_pct"]) > 0.05
    legacy63 = _psl_legacy_rs(closes, "XLK", 63)
    assert abs(legacy63 - cell63["relative_wealth_pct"]) <= 0.05 + 1e-9


def test_w2_endpoints_land_on_canonical_sessions_not_calendar_days():
    """S_N is a POSITION on the canonical calendar, not a calendar day."""
    calendar = _psl_calendar()
    out = _psl_measure(calendar=calendar)
    end_index = calendar.index(_PSL_END)
    for size in _PSL_WINDOWS:
        window = out["windows"][str(size)]
        assert window["start_session"] == calendar[end_index - size]
        assert window["end_session"] == calendar[end_index]
        # a 5-session return spans SIX session endpoints
        assert window["benchmark_coverage"]["expected_n"] == size + 1
    # no endpoint falls on a weekend
    for size in _PSL_WINDOWS:
        for day in (out["windows"][str(size)]["start_session"], out["windows"][str(size)]["end_session"]):
            assert date.fromisoformat(day).weekday() < 5


def test_w3_missing_start_endpoint_nulls_only_that_window():
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    start_63 = calendar[calendar.index(_PSL_END) - 63]
    for row in closes:
        if row["session"] == start_63:
            row["XLK"] = None
    out = _psl_measure(closes, calendar=calendar)
    cell = _psl_cell(out, "XLK", "63")
    assert cell["absolute_return_pct"] is None
    assert cell["null_reasons"]["absolute_return_pct"] == "missing_input"
    assert cell["null_reasons"]["relative_wealth_pct"] == "missing_input"
    # the other windows keep their own endpoints
    assert _psl_cell(out, "XLK", "5")["absolute_return_pct"] is not None
    assert _psl_cell(out, "XLK", "20")["absolute_return_pct"] is not None


def test_w4_missing_end_endpoint_nulls_the_measurement():
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    for row in closes:
        if row["session"] == _PSL_END:
            row["XLU"] = None
    out = _psl_measure(closes, calendar=calendar)
    cell = _psl_cell(out, "XLU", "63")
    assert cell["absolute_return_pct"] is None
    assert cell["null_reasons"]["absolute_return_pct"] == "missing_input"


def test_w5_benchmark_missing_keeps_absolute_and_marks_relative_unknown():
    """A missing benchmark nulls ONLY the relative wealth; the ETF absolute
    return is still qualified, and the two reasons are distinct."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    for row in closes:
        row.pop(_PSL_BENCHMARK)
    out = _psl_measure(closes, calendar=calendar)
    cell = _psl_cell(out, "XLK", "5")
    assert cell["absolute_return_pct"] is not None
    assert cell["relative_wealth_pct"] is None
    assert cell["null_reasons"]["absolute_return_pct"] is None
    assert cell["null_reasons"]["relative_wealth_pct"] == "benchmark_missing"
    assert out["windows"]["5"]["benchmark_return_pct"] is None
    assert out["windows"]["5"]["benchmark_null_reason"] == "benchmark_missing"


def test_w6_interior_gap_never_moves_endpoints_and_is_disclosed_as_coverage():
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    end_index = calendar.index(_PSL_END)
    interior = calendar[end_index - 30]
    for row in closes:
        if row["session"] == interior:
            row["XLB"] = None
    out = _psl_measure(closes, calendar=calendar)
    cell = _psl_cell(out, "XLB", "63")
    # the endpoints are still S_63 and T, and the return is still measured
    assert out["windows"]["63"]["start_session"] == calendar[end_index - 63]
    assert cell["absolute_return_pct"] is not None
    # the gap is disclosed, not absorbed
    assert cell["coverage"]["expected_n"] == 64
    assert cell["coverage"]["observed_n"] == 63
    assert cell["coverage"]["ratio"] < 1.0
    # a member with no gap keeps full coverage
    assert _psl_cell(out, "XLK", "63")["coverage"]["observed_n"] == 64


def test_w7_benchmark_and_sector_share_the_same_endpoint_sessions():
    """The common benchmark return is computed once per window over the SAME
    endpoints every member uses -- never a private or rolling window."""
    calendar = _psl_calendar()
    out = _psl_measure(calendar=calendar)
    end_index = calendar.index(_PSL_END)
    for size in _PSL_WINDOWS:
        window = out["windows"][str(size)]
        start, end = calendar[end_index - size], calendar[end_index]
        bench_start = out["groups"]  # every member shares the common block
        assert window["start_session"] == start
        assert window["end_session"] == end
        assert window["benchmark_coverage"]["expected_n"] == size + 1
        for group in bench_start:
            cell = group["windows"][str(size)]
            assert cell["coverage"]["expected_n"] == size + 1


def test_w8_future_tail_is_unavailable():
    """A capture that carries sessions AFTER the declared end session is
    refused whole: the measurement never reads past its own end."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    closes.append({"session": "2026-11-06", _PSL_BENCHMARK: 101.0, "XLK": 52.0})
    out = _psl_measure(closes, calendar=calendar)
    assert out["status"] == "unavailable"
    assert out["reason"] == "future_tail"
    assert len(out["groups"]) == 11
    for group in out["groups"]:
        for cell in group["windows"].values():
            assert cell["absolute_return_pct"] is None
            assert cell["relative_wealth_pct"] is None
            assert cell["null_reasons"]["absolute_return_pct"] == "future_tail"


def test_w9_non_session_end_session_is_rejected():
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    with pytest.raises(ValueError, match="canonical session"):
        _psl_measure(closes, calendar=calendar, end="2026-11-07")  # a Saturday
    with pytest.raises(ValueError, match="canonical session"):
        _psl_measure(closes, calendar=calendar, end="2026-11-06")  # not on the calendar


def test_w10_source_session_mismatch_is_unavailable():
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    out = _psl_measure(closes, calendar=calendar, source="2026-11-04")
    assert out["status"] == "unavailable"
    assert out["reason"] == "source_session_mismatch"
    assert len(out["groups"]) == 11


def test_w11_unsorted_calendar_is_rejected():
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    scrambled = list(calendar)
    scrambled[10], scrambled[11] = scrambled[11], scrambled[10]
    with pytest.raises(ValueError, match="ascending"):
        _psl_measure(closes, calendar=scrambled)


def test_w12_duplicate_calendar_session_is_rejected():
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    duplicated = calendar[:50] + [calendar[49]] + calendar[50:]
    with pytest.raises(ValueError, match="ascending"):
        _psl_measure(closes, calendar=duplicated)


def test_w13_duplicate_price_index_is_ambiguous():
    """Two rows carrying one session are an ambiguous index, never collapsed."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    closes.append(dict(closes[-1]))
    out = _psl_measure(closes, calendar=calendar)
    assert out["status"] == "unavailable"
    assert out["reason"] == "ambiguous_duplicate_price_index"
    assert len(out["groups"]) == 11


def test_w14_duplicate_column_is_ambiguous():
    """Two columns resolving to one ticker identity are ambiguous."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    for row in closes:
        row["spy"] = row[_PSL_BENCHMARK]
    out = _psl_measure(closes, calendar=calendar)
    assert out["status"] == "unavailable"
    assert out["reason"] == "ambiguous_duplicate_column"


@pytest.mark.parametrize("bad,reason", [
    (True, "invalid_price"),
    (False, "invalid_price"),
    (float("nan"), "non_finite_input"),
    (float("inf"), "non_finite_input"),
    (float("-inf"), "non_finite_input"),
    (0.0, "invalid_price"),
    (-3.5, "invalid_price"),
    ("12.5", "invalid_price"),
    (None, "missing_input"),
])
def test_w15_invalid_prices_are_rejected_with_a_stable_reason(bad, reason):
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    for row in closes:
        if row["session"] == _PSL_END:
            row["XLK"] = bad
    out = _psl_measure(closes, calendar=calendar)
    cell = _psl_cell(out, "XLK", "5")
    assert cell["absolute_return_pct"] is None
    assert cell["null_reasons"]["absolute_return_pct"] == reason
    assert cell["relative_wealth_pct"] is None
    assert cell["null_reasons"]["relative_wealth_pct"] == reason


def test_w16_large_finite_overflow_is_not_finite():
    """Two finite prices can still overflow their ratio; the outcome is
    unmeasured, never an infinity in the JSON."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    end_index = calendar.index(_PSL_END)
    for row in closes:
        if row["session"] == calendar[end_index - 5]:
            row["XLK"] = 1e-300
        if row["session"] == _PSL_END:
            row["XLK"] = 1e300
    out = _psl_measure(closes, calendar=calendar)
    cell = _psl_cell(out, "XLK", "5")
    assert cell["absolute_return_pct"] is None
    assert cell["null_reasons"]["absolute_return_pct"] == "non_finite_input"
    json.dumps(out, allow_nan=False)


def test_w17_absolute_relative_wealth_and_return_difference_are_distinct():
    """Absolute return, relative wealth and a plain return difference are
    three different quantities; the block publishes the first two."""
    calendar = _psl_calendar()
    out = _psl_measure(calendar=calendar)
    cell = _psl_cell(out, "XLK", "20")
    absolute = cell["absolute_return_pct"] / 100.0
    benchmark = out["windows"]["20"]["benchmark_return_pct"] / 100.0
    relative = cell["relative_wealth_pct"] / 100.0
    assert abs(relative - ((1.0 + absolute) / (1.0 + benchmark) - 1.0)) < 1e-6
    difference = absolute - benchmark
    assert abs(relative - difference) > 1e-9
    # the module's own definitions agree with the published numbers
    assert abs(lrc.relative_wealth(absolute, benchmark) - relative) < 1e-6
    assert abs(lrc.return_difference(absolute, benchmark) - difference) < 1e-9


def test_w18_eleven_rows_survive_valid_partial_and_all_null():
    """The population is FIXED: eleven native identities in the canonical
    cohort order, whatever the data does."""
    calendar = _psl_calendar()
    tickers = us_sector_cohort()
    assert len(tickers) == 11
    valid = _psl_measure(calendar=calendar)
    assert [g["group_id"] for g in valid["groups"]] == list(tickers)
    assert all(g["name_en"] for g in valid["groups"])

    closes = _psl_panel(calendar, tickers)
    for row in closes:
        for ticker in tickers:
            row[ticker] = None
    partial = _psl_measure(closes, calendar=calendar)
    assert len(partial["groups"]) == 11
    assert partial["status"] == "unavailable"
    for group in partial["groups"]:
        for cell in group["windows"].values():
            assert cell["status"] == "unavailable"
            assert cell["absolute_return_pct"] is None
            assert cell["relative_wealth_pct"] is None

    # a PARTIAL population: one member measured, the rest missing
    closes = _psl_panel(calendar, tickers)
    for row in closes:
        for ticker in tickers[1:]:
            row[ticker] = None
    mixed = _psl_measure(closes, calendar=calendar)
    assert len(mixed["groups"]) == 11
    assert mixed["status"] == "partial"
    assert _psl_cell(mixed, tickers[0], "5")["absolute_return_pct"] is not None
    assert _psl_cell(mixed, tickers[1], "5")["absolute_return_pct"] is None


def test_w19_insufficient_reference_history_keeps_eleven_rows_and_no_dates():
    """Too little calendar history makes that window unavailable with NO
    invented window dates -- and the eleven rows are still there."""
    calendar = _psl_calendar(n=30)
    closes = _psl_panel(calendar, us_sector_cohort())
    out = _psl_measure(closes, calendar=calendar)
    assert len(out["groups"]) == 11
    assert out["windows"]["5"]["status"] == "available"
    assert out["windows"]["20"]["status"] == "available"
    assert out["windows"]["63"]["status"] == "unavailable"
    assert out["windows"]["63"]["start_session"] is None
    assert out["windows"]["63"]["null_reason"] == "insufficient_reference_history"
    for group in out["groups"]:
        cell = group["windows"]["63"]
        assert cell["absolute_return_pct"] is None
        assert cell["null_reasons"]["absolute_return_pct"] == "insufficient_reference_history"


def test_w20_no_ambient_read_and_input_immutability():
    """The measurement reads nothing ambient and mutates nothing it is given."""
    import builtins

    calendar = _psl_calendar()
    tickers = us_sector_cohort()
    closes = _psl_panel(calendar, tickers)
    binding = {"source_roots": ["engine.sector_cycles"],
               "clocks": {"publication": "2026-11-05T21:00:00Z"},
               "receipt": {"capture_id": "abc"}}
    snapshot = copy.deepcopy(closes)
    calendar_copy = list(calendar)
    binding_copy = copy.deepcopy(binding)

    from engine import sector_cycles  # pre-import: the population owner is not ambient

    real_open = builtins.open

    def _no_open(*args, **kwargs):
        raise AssertionError("the window measurement must not read a file")

    builtins.open = _no_open
    try:
        out = lrc.measure_sector_windows(
            closes, benchmark=_PSL_BENCHMARK, end_session=_PSL_END,
            source_session=_PSL_END, reference_sessions=calendar,
            source_binding=binding)
    finally:
        builtins.open = real_open

    assert out["status"] == "available"
    assert closes == snapshot
    assert calendar == calendar_copy
    assert binding == binding_copy

    # no clock, file or environment read anywhere in the new section
    tree = ast.parse(Path(lrc.__file__).read_text(encoding="utf-8"))
    forbidden = {"now", "today", "utcnow", "time", "open", "read_text", "read_bytes",
                 "environ", "getenv", "urlopen", "requests"}
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not (node.name.startswith("_window") or node.name == "measure_sector_windows"):
            continue
        for call in ast.walk(node):
            if isinstance(call, ast.Call):
                func = call.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                if name in forbidden:
                    offenders.append(f"{node.name}:{name}")
    assert offenders == []


def test_w21_complete_aligned_new63_agrees_with_the_legacy_rounding():
    """On a complete, aligned capture the EXACT 63-session relative wealth
    agrees with the incumbent rolling rs_63d inside the legacy's own 1-decimal
    rounding -- without the legacy being changed."""
    import pandas as pd

    from engine import sector_cycles

    calendar = _psl_calendar(n=300)
    tickers = us_sector_cohort()
    closes = _psl_panel(calendar, tickers)
    out = _psl_measure(closes, calendar=calendar)
    frame = pd.DataFrame([{k: v for k, v in row.items()} for row in closes])
    frame["session"] = pd.to_datetime(frame["session"])
    frame = frame.set_index("session").sort_index()
    asof = pd.Timestamp(_PSL_END)
    worst = 0.0
    for ticker in tickers:
        legacy = sector_cycles._leadership(frame, ticker, bench=_PSL_BENCHMARK, asof=asof)
        published = _psl_cell(out, ticker, "63")["relative_wealth_pct"]
        assert published is not None
        worst = max(worst, abs(published - legacy["rs_63d"]))
    assert worst <= 0.05 + 1e-9, worst


def test_w22_gapped_semantics_stay_separate_from_the_legacy():
    """With an interior gap the legacy coordinate SLIDES onto a different
    window; the exact measurement does not. The two semantics stay separate."""
    import pandas as pd

    from engine import sector_cycles

    calendar = _psl_calendar(n=300)
    tickers = us_sector_cohort()
    closes = _psl_panel(calendar, tickers)
    end_index = calendar.index(_PSL_END)
    gap = calendar[end_index - 30]
    for row in closes:
        if row["session"] == gap:
            row["XLK"] = None
    out = _psl_measure(closes, calendar=calendar)
    exact = _psl_cell(out, "XLK", "63")["relative_wealth_pct"]
    assert exact is not None
    assert _psl_cell(out, "XLK", "63")["coverage"]["observed_n"] == 63

    frame = pd.DataFrame([{k: v for k, v in row.items()} for row in closes])
    frame["session"] = pd.to_datetime(frame["session"])
    frame = frame.set_index("session").sort_index()
    legacy = sector_cycles._leadership(frame, "XLK", bench=_PSL_BENCHMARK,
                                        asof=pd.Timestamp(_PSL_END))["rs_63d"]
    # the legacy dropped the gapped row, so its 63-row lookback spans 64
    # calendar sessions and lands on a different pair of endpoints
    assert abs(exact - legacy) > 0.05


def test_w23_default_measured_read_bytes_are_unchanged():
    """The default read is byte-identical to the frozen v1 producer bytes and
    carries NO companion key."""
    cyc, rot = _build_fixture_payload()
    blob = _serialize(lrc.measured_group_read(cyc, rotation_payload=rot))
    assert FIXTURE.read_text(encoding="utf-8") == blob
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    assert "sector_window_measurements" not in out
    assert "sector_dossiers" not in out


def test_w24_companion_key_leaves_the_closed_v1_dossier_byte_identical():
    """Supplying a BOUND composition adds a COMPANION key; the closed
    sector_dossiers/v1 block is untouched, byte-for-byte."""
    cyc, rot = _build_fixture_payload()
    plain = lrc.measured_group_read(cyc, rotation_payload=rot, include_sector_dossiers=True)
    calendar = _psl_calendar(end=AS_OF)
    composed = lrc.measured_group_read(
        cyc, rotation_payload=rot, include_sector_dossiers=True,
        sector_window_inputs=_psl_composition(calendar, AS_OF))
    assert "sector_window_measurements" not in plain
    assert "sector_window_measurements" in composed
    assert composed["sector_dossiers"] == plain["sector_dossiers"]
    for key in plain:
        assert composed[key] == plain[key]


def test_w25_complete_fixture_is_frozen():
    """The representative COMPLETE measurement is frozen byte-for-byte."""
    calendar, closes, tickers = _psl_frozen_panel()
    out = _psl_measure(closes, calendar=calendar)
    assert out["status"] == "available"
    assert PSL_COMPLETE_FIXTURE.exists(), f"missing frozen fixture: {PSL_COMPLETE_FIXTURE}"
    assert PSL_COMPLETE_FIXTURE.read_text(encoding="utf-8") == _serialize(out)
    frozen = json.loads(PSL_COMPLETE_FIXTURE.read_text(encoding="utf-8"))
    assert frozen["schema"] == lrc.SECTOR_WINDOW_MEASUREMENTS_SCHEMA
    assert len(frozen["groups"]) == 11


def test_w26_unavailable_fixture_is_frozen():
    """The representative UNAVAILABLE measurement is frozen byte-for-byte."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    closes.append({"session": "2026-11-06", _PSL_BENCHMARK: 101.0})
    out = _psl_measure(closes, calendar=calendar)
    assert out["status"] == "unavailable"
    assert PSL_UNAVAILABLE_FIXTURE.exists(), f"missing frozen fixture: {PSL_UNAVAILABLE_FIXTURE}"
    assert PSL_UNAVAILABLE_FIXTURE.read_text(encoding="utf-8") == _serialize(out)
    frozen = json.loads(PSL_UNAVAILABLE_FIXTURE.read_text(encoding="utf-8"))
    assert frozen["reason"] == "future_tail"
    assert len(frozen["groups"]) == 11


def test_w27_no_forbidden_fields_and_every_authority_flag_is_false():
    """No rank, score, forecast, allocation, target or trade field; every
    authority flag stays false; no compatibility key is manufactured."""
    out = _psl_measure()
    assert _forbidden_keys(out) == []
    banned = ("rank", "score", "forecast", "allocation", "target", "trade",
              "compatibility_key", "source_generation", "hash", "content_hash")
    def _scan(obj, path=""):
        found = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "authority":
                    # the authority block only ever says "no": its flag NAMES
                    # are not a rank, a score or a trade
                    continue
                if any(b in str(key).lower() for b in banned):
                    found.append(f"{path}.{key}")
                found.extend(_scan(value, f"{path}.{key}"))
        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                found.extend(_scan(value, f"{path}[{index}]"))
        return found
    assert _scan(out) == []
    assert out["authority"] == {"may_rank": False, "may_gate": False, "may_size": False,
                                "may_trade": False, "may_escalate": False}
    assert out["price_basis"] == "total_return"
    assert out["units"] == "pct"
    assert out["benchmark"] == _PSL_BENCHMARK
    assert out["cohort_id"] == lrc.US_SECTOR_COHORT_ID
    # unknown clocks stay unknown; nothing is manufactured
    assert out["clocks"] == {"publication": None, "availability": None,
                             "correction": None, "history": None}
    assert out["limitations"]["availability"]["status"] == "unknown"
    assert out["limitations"]["point_in_time"]["status"] == "not_qualified"


def test_w28_measured_group_read_rejects_unknown_composition_keys():
    cyc, rot = _build_fixture_payload()
    with pytest.raises(ValueError, match="unknown sector_window_inputs keys"):
        lrc.measured_group_read(cyc, rotation_payload=rot,
                                sector_window_inputs={"closes": [], "nonsense": 1})
    with pytest.raises(ValueError, match="sector_window_inputs must be a mapping"):
        lrc.measured_group_read(cyc, rotation_payload=rot, sector_window_inputs=[])


def test_w29_every_published_reason_is_in_the_closed_vocabulary():
    """Every reason the block can publish comes from a bounded vocabulary:
    measurement missingness reasons and limitation reasons are separate."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    for row in closes:
        row["XLK"] = None
        row[_PSL_BENCHMARK] = None
    out = _psl_measure(closes, calendar=calendar)
    published, limitations = [], []

    def _scan(obj, in_limitations=False):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "limitations":
                    _scan(value, True)
                    continue
                if in_limitations:
                    if key == "reason" and value is not None:
                        limitations.append(value)
                    _scan(value, True)
                    continue
                if key in ("reason", "null_reason", "benchmark_null_reason") and value is not None:
                    published.append(value)
                elif key == "null_reasons" and isinstance(value, dict):
                    published.extend(v for v in value.values() if v is not None)
                _scan(value)

    _scan(out)
    assert published
    for reason in published:
        assert reason in lrc._WINDOW_REASONS, reason
    assert limitations
    for reason in limitations:
        assert reason in lrc._WINDOW_LIMITATION_REASONS, reason


def test_w30_a_foreign_cohort_carries_no_native_cohort_identity():
    """An explicit population is a bounded FOREIGN cohort: it never claims the
    native cohort id, and the native population/order is unchanged."""
    calendar = _psl_calendar()
    foreign = ("AAA", "BBB")
    closes = _psl_panel(calendar, us_sector_cohort())
    for row in closes:
        for ticker in foreign:
            row[ticker] = 25.0
    out = _psl_measure(closes, calendar=calendar, population=foreign)
    assert out["cohort_id"] is None
    assert out["population"] == "explicit_population"
    assert [g["group_id"] for g in out["groups"]] == list(foreign)
    native = _psl_measure(calendar=calendar)
    assert native["cohort_id"] == lrc.US_SECTOR_COHORT_ID
    assert native["population"] == "eleven_sector_etf_proxies"
    assert [g["group_id"] for g in native["groups"]] == list(us_sector_cohort())


def test_w31_source_binding_compatibility_is_enforced():
    """A binding that contradicts the measured identity makes the block
    unavailable instead of publishing an incompatible number."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    base = {"closes": closes, "benchmark": _PSL_BENCHMARK, "end_session": _PSL_END,
            "source_session": _PSL_END, "reference_sessions": calendar}
    ok = lrc.measure_sector_windows(**base, source_binding={
        "cohort_id": lrc.US_SECTOR_COHORT_ID, "benchmark": _PSL_BENCHMARK,
        "source_session": _PSL_END, "price_basis": "total_return",
        "source_roots": ["engine.sector_cycles"],
        "clocks": {"publication": "2026-11-05T21:00:00Z"},
        "receipt": {"capture_id": "abc"}})
    assert ok["status"] == "available"
    assert ok["clocks"]["publication"] == "2026-11-05T21:00:00Z"
    assert ok["clocks"]["availability"] is None
    assert ok["source_roots"] == ["engine.sector_cycles"]
    assert ok["receipt"] == {"capture_id": "abc"}
    assert ok["limitations"]["publication"]["status"] == "supplied"
    assert ok["limitations"]["availability"]["status"] == "unknown"

    for binding, reason in [
        ({"cohort_id": "us_sectors_09"}, "cohort_identity_mismatch"),
        ({"benchmark": "QQQ"}, "benchmark_identity_mismatch"),
        ({"source_session": "2026-11-04"}, "source_session_mismatch"),
        ({"price_basis": "price_only"}, "return_basis_not_qualified"),
    ]:
        out = lrc.measure_sector_windows(**base, source_binding=binding)
        assert out["status"] == "unavailable", binding
        assert out["reason"] == reason, binding
        assert len(out["groups"]) == 11


def test_w32_a_finite_fraction_that_overflows_the_percent_scale_is_published_as_null():
    """A FINITE return fraction can still overflow when it is scaled to PERCENT
    (1e307 * 100 is an infinity). The publication is null with the stable
    non-finite reason, and the block still encodes as strict JSON."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    end_index = calendar.index(_PSL_END)
    for row in closes:
        if row["session"] == calendar[end_index - 5]:
            row["XLK"] = 1.0            # a finite, ordinary start price
        if row["session"] == _PSL_END:
            row["XLK"] = 1e307          # a finite end price: the RATIO is finite
    # the raw fraction is FINITE: this is NOT the already-infinite case
    assert (1e307 / 1.0 - 1.0) < 1.8e308
    assert (1e307 / 1.0 - 1.0) * 100.0 == float("inf")
    out = _psl_measure(closes, calendar=calendar)
    cell = _psl_cell(out, "XLK", "5")
    assert cell["absolute_return_pct"] is None
    assert cell["null_reasons"]["absolute_return_pct"] == "non_finite_input"
    assert cell["relative_wealth_pct"] is None
    assert cell["null_reasons"]["relative_wealth_pct"] == "non_finite_input"
    assert cell["status"] == "unavailable"
    # strict JSON encoding succeeds: no infinity and no NaN anywhere
    json.dumps(out, allow_nan=False)

    # a large but REPRESENTABLE fraction is still published -- the rule is the
    # percent scale, not "a big number"
    control = _psl_panel(calendar, us_sector_cohort())
    for row in control:
        if row["session"] == calendar[end_index - 5]:
            row["XLK"] = 1.0
        if row["session"] == _PSL_END:
            row["XLK"] = 1e300
    control_out = _psl_measure(control, calendar=calendar)
    control_cell = _psl_cell(control_out, "XLK", "5")
    assert control_cell["absolute_return_pct"] == pytest.approx(1e302, rel=1e-9)
    assert control_cell["null_reasons"]["absolute_return_pct"] is None
    json.dumps(control_out, allow_nan=False)

    # the same rule governs the COMMON benchmark percentage: an unpublishable
    # benchmark leaves the member's absolute qualified and its relative unknown
    bench = _psl_panel(calendar, us_sector_cohort())
    for row in bench:
        if row["session"] == calendar[end_index - 5]:
            row[_PSL_BENCHMARK] = 1e-300
        if row["session"] == _PSL_END:
            row[_PSL_BENCHMARK] = 1e8
    assert (1e8 / 1e-300 - 1.0) < 1.8e308
    assert (1e8 / 1e-300 - 1.0) * 100.0 == float("inf")
    bench_out = _psl_measure(bench, calendar=calendar)
    assert bench_out["windows"]["5"]["benchmark_return_pct"] is None
    assert bench_out["windows"]["5"]["benchmark_null_reason"] == "non_finite_input"
    bench_cell = _psl_cell(bench_out, "XLK", "5")
    assert bench_cell["relative_wealth_pct"] is None
    assert bench_cell["null_reasons"]["relative_wealth_pct"] == "non_finite_input"
    assert bench_cell["absolute_return_pct"] is not None
    json.dumps(bench_out, allow_nan=False)


def test_w33_the_companion_must_be_bound_to_the_parent_generation():
    """The companion block is published INSIDE the parent read, so it must
    describe the SAME generation. A composition whose session end is not the
    parent's session end is a PROGRAMMER error, never a silently attached
    companion."""
    cyc, rot = _build_fixture_payload()
    calendar = _psl_calendar()
    # the parent names AS_OF; the companion names _PSL_END -> unbound
    with pytest.raises(ValueError, match="cannot be bound"):
        lrc.measured_group_read(
            cyc, rotation_payload=rot,
            sector_window_inputs=_psl_composition(calendar, _PSL_END))
    # the same composition bound to the parent's own session end attaches
    bound = _psl_calendar(end=AS_OF)
    read = lrc.measured_group_read(
        cyc, rotation_payload=rot,
        sector_window_inputs=_psl_composition(bound, AS_OF))
    assert read["sector_window_measurements"]["end_session"] == AS_OF


@pytest.mark.parametrize("case, fragment", [
    ("benchmark", "companion benchmark"),
    ("population", "native sector cohort"),
    ("windows", "exact 5/20/63-session windows"),
    ("unknown_parent", "no known session end"),
    ("unknown_parent_benchmark", "no known benchmark"),
])
def test_w34_an_unbound_composition_is_never_attached(case, fragment):
    """Every way a composition can fail to describe the parent's generation
    is a programmer error: it is never attached, never dropped and never
    restamped."""
    cyc, rot = _build_fixture_payload()
    calendar = _psl_calendar(end=AS_OF)
    overrides = {}
    if case == "unknown_parent":
        cyc = {"meta": {}, "sectors": []}
    elif case == "unknown_parent_benchmark":
        cyc = {"meta": {"asOf": AS_OF}, "sectors": []}
    elif case == "benchmark":
        overrides["benchmark"] = "QQQ"
    elif case == "population":
        overrides["population"] = ("AAA", "BBB")
    elif case == "windows":
        overrides["windows"] = (5, 20)
    with pytest.raises(ValueError, match=fragment):
        lrc.measured_group_read(
            cyc, rotation_payload=rot,
            sector_window_inputs=_psl_composition(calendar, AS_OF, **overrides))


def test_w35_a_bound_composition_is_attached_unchanged():
    """A bound composition is published as the child's own block: neither side
    is restamped and no compatibility key is minted."""
    cyc, rot = _build_fixture_payload()
    calendar = _psl_calendar(end=AS_OF)
    read = lrc.measured_group_read(
        cyc, rotation_payload=rot,
        sector_window_inputs=_psl_composition(calendar, AS_OF))
    block = read["sector_window_measurements"]
    generation = read["generation"]
    assert block["end_session"] == generation["session_end"] == AS_OF
    assert block["source_session"] == generation["session_end"]
    assert block["benchmark"] == generation["benchmark"]
    assert block["cohort_id"] == generation["cohort_id"] == lrc.US_SECTOR_COHORT_ID
    assert block["price_basis"] == generation["price_basis"] == "total_return"
    assert [g["group_id"] for g in block["groups"]] == list(us_sector_cohort())
    assert block["windows_sessions"] == [5, 20, 63]
    # the parent generation is untouched and no compatibility key is invented
    assert generation["session_end"] == AS_OF
    assert set(read) == set(lrc.measured_group_read(cyc, rotation_payload=rot)) | {
        "sector_window_measurements"}


def test_w36_the_source_binding_is_bounded_and_published_detached():
    """The binding carries METADATA only: short control-free strings, aware
    clocks, and a receipt that is finite, bounded and cycle-free JSON. The
    published receipt is DETACHED from the caller's object."""
    calendar = _psl_calendar()
    closes = _psl_panel(calendar, us_sector_cohort())
    base = {"closes": closes, "benchmark": _PSL_BENCHMARK, "end_session": _PSL_END,
            "source_session": _PSL_END, "reference_sessions": calendar}

    # a NaN inside the receipt is refused
    with pytest.raises(ValueError, match="non-finite"):
        lrc.measure_sector_windows(**base, source_binding={"receipt": {"x": float("nan")}})
    # an infinity is refused as well
    with pytest.raises(ValueError, match="non-finite"):
        lrc.measure_sector_windows(**base, source_binding={"receipt": {"x": float("inf")}})
    # a cycle is refused
    cyclic = {}
    cyclic["self"] = cyclic
    with pytest.raises(ValueError, match="cycle"):
        lrc.measure_sector_windows(**base, source_binding={"receipt": cyclic})
    # a value JSON cannot carry is refused
    with pytest.raises(ValueError, match="JSON values only"):
        lrc.measure_sector_windows(**base, source_binding={"receipt": {"x": object()}})
    # an unbounded container is refused
    with pytest.raises(ValueError, match="bounded"):
        lrc.measure_sector_windows(**base, source_binding={"receipt": {"x": ["v"] * 1000}})
    # a wall-clock (naive) timestamp names no instant and is refused
    with pytest.raises(ValueError, match="UTC offset"):
        lrc.measure_sector_windows(
            **base, source_binding={"clocks": {"publication": "2026-11-05T21:00:00"}})
    # a control character in a root is refused
    with pytest.raises(ValueError, match="control characters"):
        lrc.measure_sector_windows(
            **base, source_binding={"source_roots": ["engine.\x00sector_cycles"]})
    # a malformed session date is refused
    with pytest.raises(ValueError, match="strict YYYY-MM-DD"):
        lrc.measure_sector_windows(**base, source_binding={"source_session": "2026-13-45"})
    # an over-long identity is refused
    with pytest.raises(ValueError, match="bounded length"):
        lrc.measure_sector_windows(**base, source_binding={"benchmark": "S" * 500})

    # the published receipt is a DETACHED copy of the caller's object
    receipt = {"capture_id": "abc", "detail": {"n": 1}}
    out = lrc.measure_sector_windows(**base, source_binding={"receipt": receipt})
    assert out["receipt"] == receipt
    assert out["receipt"] is not receipt
    receipt["detail"]["n"] = 99
    assert out["receipt"]["detail"]["n"] == 1

    # a supplied clock and receipt establish NOTHING by themselves
    supplied = lrc.measure_sector_windows(**base, source_binding={
        "clocks": {"publication": "2026-11-05T21:00:00Z",
                   "availability": "2026-11-05T21:00:00Z"},
        "receipt": {"capture_id": "abc"}})
    assert supplied["limitations"]["freshness"]["status"] == "unverified"
    assert supplied["limitations"]["point_in_time"]["status"] == "not_qualified"
    assert supplied["limitations"]["availability"]["status"] == "supplied"


def test_w37_the_canonical_us_session_reference_keeps_a_holiday_out_of_the_window():
    """US Labor Day 2026-09-07 is not a session. The canonical 63-session
    window therefore starts on 2026-08-07, where the weekday approximation
    started on 2026-08-10 and counted the holiday as one of the sixty-three.
    A capture row on the holiday is never promoted to a session either."""
    from lib import nyse_calendar

    calendar = _psl_calendar()
    end = date.fromisoformat(_PSL_END)
    assert not nyse_calendar.is_session(date(2026, 9, 7))
    assert "2026-09-07" not in calendar
    # exactly 63 canonical sessions before T -- the owner agrees
    assert nyse_calendar.session_n_back(end, 63) == date(2026, 8, 7)
    assert calendar[-64] == "2026-08-07"
    assert calendar[-64:] == [day.isoformat() for day in
                              nyse_calendar.sessions_between(date(2026, 8, 7), end)]
    # the weekday approximation is the counterexample: it counts the holiday
    weekday, day = [], end
    while len(weekday) < 300:
        if day.weekday() < 5:
            weekday.append(day.isoformat())
        day -= timedelta(days=1)
    weekday = list(reversed(weekday))
    assert "2026-09-07" in weekday[-64:]
    assert weekday[-64] == "2026-08-10"
    # the measurement reports the canonical endpoints
    out = _psl_measure(calendar=calendar)
    assert out["windows"]["63"]["start_session"] == "2026-08-07"
    assert out["windows"]["63"]["end_session"] == _PSL_END
    assert out["windows"]["5"]["start_session"] == "2026-10-29"
    assert out["windows"]["20"]["start_session"] == "2026-10-08"

    # a capture row on the holiday never becomes a session and never moves an
    # endpoint
    holiday_closes = _psl_panel(calendar, us_sector_cohort())
    holiday_row = {"session": "2026-09-07", _PSL_BENCHMARK: 100.0}
    for ticker in us_sector_cohort():
        holiday_row[ticker] = 100.0
    holiday_closes.append(holiday_row)
    holiday_out = _psl_measure(holiday_closes, calendar=calendar)
    assert holiday_out["windows"]["63"]["start_session"] == "2026-08-07"
    assert holiday_out["windows"]["63"]["status"] == "available"
    assert _psl_cell(holiday_out, "XLK", "63")["absolute_return_pct"] is not None
