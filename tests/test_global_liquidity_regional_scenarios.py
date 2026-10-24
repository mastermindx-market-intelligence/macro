"""Tests for the T10 measurement-only regional scenario map (F1).

Each refusal is asserted both via ``pytest.raises`` AND via
``exc.value.code == "<code>"``. ``full_owners`` returns a FRESH deep-copied
dict so no test mutates another.  ``cfg`` is the S11 yaml; ``AS_OF`` and
``make_outlook`` are imported from the T08 test module.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

import engine.global_liquidity_regional_scenarios as regional
from engine.global_liquidity_regional_scenarios import (
    AGGREGATE_NULL_STATUS,
    AGGREGATE_NULL_REASON,
    BOJ_MONTH_END_ANCHOR,
    CLAIM_LEVEL,
    CN_NO_QUANTITY_ASSUMPTION,
    CN_TSF_NON_COMPARABLE,
    ESTIMATE_TYPES,
    FIT_POLICY,
    FX_RESERVES_NOT_BALANCE_SHEET,
    HK_CURRENCY_BOARD_AGG_BALANCE,
    HK_MISSING_TEXT,
    LOCAL_UNIT_STOCK,
    NO_GLOBAL_SCALAR,
    PBOC_MISSING_TEXT,
    PIT_STATUS_VOCAB,
    REGIONS,
    SCHEMA,
    STATUSES,
    US_CONDITIONAL_ACCOUNTING,
    US_FUNDING_IDENTITY,
    US_LAW_IDS,
    US_RESERVE_IDENTITY,
    VALIDATED,
    RegionalScenarioRefused,
    build_scenario_map,
    qualify_region,
    refuse_fx_reserves_substitute,
    refuse_future_fixing,
    refuse_global_aggregate,
    refuse_us_law_transfer,
)
from engine.global_liquidity_outlook import ESTIMATE_TYPES as OUTLOOK_ESTIMATE_TYPES
from engine.global_liquidity_outlook import compose_component_paths
from tests.test_global_liquidity_outlook import AS_OF, make_outlook

NY = ZoneInfo("America/New_York")

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


_CFG = _load_yaml(REPO_ROOT / "config" / "global_liquidity_transmission_v1.yml")
_SOURCES = _load_yaml(REPO_ROOT / "config" / "global_liquidity_sources_v2.yml")


# ---------------------------------------------------------------------------
# fixtures (module-level helpers, not hidden state)
# ---------------------------------------------------------------------------

def _ecb():
    return regional.s11_stock_owner(
        _CFG, "ecb",
        observed_at=date(2026, 9, 2), known_at=AS_OF, value=6_400_000.0,
    )


def _boj():
    return regional.s11_stock_owner(
        _CFG, "boj",
        observed_at=date(2026, 8, 31), known_at=AS_OF, value=7_500_000.0,
    )


def _fed():
    return regional.s11_stock_owner(
        _CFG, "fed",
        observed_at=date(2026, 9, 2), known_at=date(2026, 9, 3), value=6_600_000.0,
    )


def _eur_fix():
    return {
        **regional.s11_fx_pair(_CFG, "ecb"),
        "fixing_date": AS_OF,
        "quote": 1.10,
    }


def _jpy_fix():
    return {
        **regional.s11_fx_pair(_CFG, "boj"),
        "fixing_date": AS_OF,
        "quote": 145.0,
    }


_STANCE = {
    "schema": "china_pboc_stance.v1",
    "is_context_only": True,
    "asof": "2026-09-01",
    "built": "x",
    "stance": "easing",
    "stance_en": "Easing",
    "stance_zh": "宽松",
    "score": -2,
    "rationale": ["r"],
    "corridor": {},
    "fx": {"reserves": 3.3e12},
    "last_moves": [],
}


def _tsf(latest=30000.0, prior=25000.0):
    return {
        "latest": latest,
        "prior": prior,
        "observed_at": date(2026, 7, 31),
        "known_at": date(2026, 8, 16),
    }


_HK_FULL = {
    "concept": "hkma_aggregate_balance",
    "owner_module": "test-owner",
    "store": "data/hkma/x.parquet",
    "column": "agg",
    "local_unit": "HKD",
    "unit_multiplier": 1e6,
    "release_basis": "daily",
    "observed_at": date(2026, 9, 3),
    "known_at": date(2026, 9, 3),
    "pit_status": "release_lag_aligned_revision_unknown",
    "value": 45000.0,
}


def full_owners():
    """FRESH deep-copied owner dict (S7)."""
    return {
        "us": {"stock": copy.deepcopy(_fed()), "outlook": make_outlook()},
        "euro_area": {"stock": copy.deepcopy(_ecb()), "fx_fixing": copy.deepcopy(_eur_fix())},
        "japan": {"stock": copy.deepcopy(_boj()), "fx_fixing": copy.deepcopy(_jpy_fix())},
        "china": {"stance": copy.deepcopy(_STANCE), "tsf": _tsf()},
        "hong_kong": {},
    }


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_keys(item)

# ---------------------------------------------------------------------------
# T1  C19 -- US law ids are refused when applied outside the US
# ---------------------------------------------------------------------------


def test_c19_us_law_ids_refused_for_china_and_hong_kong():
    for region in ("china", "hong_kong", "euro_area", "japan"):
        for law_id in US_LAW_IDS:
            with pytest.raises(RegionalScenarioRefused) as ei:
                build_scenario_map({region: {"law_ids": [law_id]}}, as_of=AS_OF)
            assert ei.value.code == "us_law_transfer"
            with pytest.raises(RegionalScenarioRefused) as qi:
                qualify_region(region, owners={region: {"law_ids": [law_id]}}, as_of=AS_OF)
            assert qi.value.code == "us_law_transfer"
            for shape in (law_id, (law_id,), {law_id}, {"law": law_id}, [[law_id]]):
                with pytest.raises(RegionalScenarioRefused) as si:
                    build_scenario_map({region: {"law_ids": shape}}, as_of=AS_OF)
                assert si.value.code == "us_law_transfer"

    # US itself: refuse helper returns None (no refusal)
    assert refuse_us_law_transfer("us", US_LAW_IDS) is None
    assert refuse_us_law_transfer("china", "cn_local_law") is None
    assert refuse_us_law_transfer("china", None) is None

    # The full map's china/hong_kong entries list the US laws as refused and
    # never apply them.
    m = build_scenario_map(full_owners(), as_of=AS_OF)
    for region in ("china", "hong_kong", "euro_area", "japan"):
        entry = m["regions"][region]
        assert entry["laws_refused"] == list(US_LAW_IDS)
        for lid in US_LAW_IDS:
            assert lid not in entry["laws_applied"]


# ---------------------------------------------------------------------------
# T2  C19 -- US outlook is refused outside the US
# ---------------------------------------------------------------------------


def test_c19_us_outlook_refused_outside_us():
    outlook = make_outlook()
    for region in ("china", "hong_kong", "euro_area", "japan"):
        with pytest.raises(RegionalScenarioRefused) as ei:
            build_scenario_map({region: {"outlook": outlook}}, as_of=AS_OF)
        assert ei.value.code == "us_scenario_transfer"


# ---------------------------------------------------------------------------
# T3  C19 -- FX reserves are refused as a PBoC balance-sheet substitute
# ---------------------------------------------------------------------------


def test_c19_fx_reserves_refused_as_pboc_balance_sheet():
    base = {
        "owner_module": "test",
        "store": "data/china_pboc/fx_reserves.parquet",
        "column": "fx_reserves",
        "local_unit": "CNY",
        "unit_multiplier": 1.0,
        "release_basis": "monthly",
        "observed_at": date(2026, 8, 31),
        "known_at": AS_OF,
        "pit_status": "release_lag_aligned_revision_unknown",
        "value": 3.3e12,
    }
    variants = [
        {**base, "concept": "fx_reserves"},
        {**base, "store": "data/china_pboc/fx_reserves.parquet"},
        {**base, "column": "fx_reserves"},
    ]
    for v in variants:
        with pytest.raises(RegionalScenarioRefused) as ei:
            build_scenario_map({"china": {"stock": v}}, as_of=AS_OF)
        assert ei.value.code == "fx_reserves_as_balance_sheet"

    # Direct helper refusal
    with pytest.raises(RegionalScenarioRefused) as ei:
        refuse_fx_reserves_substitute("central_bank_assets", {"concept": "fx_reserves"})
    assert ei.value.code == "fx_reserves_as_balance_sheet"
    with pytest.raises(RegionalScenarioRefused) as ei:
        refuse_fx_reserves_substitute(
            "central_bank_assets",
            {"store": "data/china_pboc/fx_reserves.parquet"},
        )
    assert ei.value.code == "fx_reserves_as_balance_sheet"

    # OMO store -> concept_mismatch (build the OMO variant WITHOUT any
    # fx-reserves indicator, so we test the store check, not the column check).
    omo = {**base, "store": "data/china_omo/operations.parquet", "column": "net_injection"}
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"china": {"stock": omo}}, as_of=AS_OF)
    assert ei.value.code == "concept_mismatch"

    # No china stock -> missing_inputs[0] is the verbatim PBoC missing text
    m = build_scenario_map({"china": {}}, as_of=AS_OF)
    china = m["regions"]["china"]
    assert china["missing_inputs"][0] == PBOC_MISSING_TEXT
    assert china["stock"] is None


# ---------------------------------------------------------------------------
# T4  protocol 9 -- FX fixing after as_of is refused
# ---------------------------------------------------------------------------


def test_protocol9_fx_fixing_after_as_of_refused():
    after = {**_eur_fix(), "fixing_date": AS_OF + timedelta(days=1)}
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"euro_area": {"stock": _ecb(), "fx_fixing": after}}, as_of=AS_OF)
    assert ei.value.code == "fx_fixing_after_as_of"
    assert refuse_future_fixing(AS_OF, AS_OF) is None

    undated = {k: v for k, v in _eur_fix().items() if k != "fixing_date"}
    mu = build_scenario_map({"euro_area": {"stock": _ecb(), "fx_fixing": undated}}, as_of=AS_OF)
    eu = mu["regions"]["euro_area"]
    assert eu["status"] == "measured"
    assert eu["stock"]["value"] == 6_400_000.0
    assert eu["fx_translation"]["fixing_date"] is None
    assert eu["fx_translation"]["usd_per_local"] is None
    assert eu["fx_translation"]["usd_value"] is None
    assert eu["fx_translation"]["null_reason"] == "fx_fixing_missing"
    assert eu["fx_translation"]["is_fresh_money"] is False
    undated_jp = {**_jpy_fix(), "fixing_date": None}
    mj = build_scenario_map({"japan": {"stock": _boj(), "fx_fixing": undated_jp}}, as_of=AS_OF)
    assert mj["regions"]["japan"]["status"] == "measured"
    assert mj["regions"]["japan"]["fx_translation"]["usd_value"] is None
    assert mj["regions"]["japan"]["fx_translation"]["null_reason"] == "fx_fixing_missing"


# ---------------------------------------------------------------------------
# T5  C06 -- global aggregate refused; global_scalar stays None
# ---------------------------------------------------------------------------


def test_c06_global_aggregate_refused_and_scalar_null():
    # aggregate != None -> global_aggregate_requested
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({}, as_of=AS_OF, aggregate="usd_sum")
    assert ei.value.code == "global_aggregate_requested"

    # owners key "global" -> global_aggregate_requested
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"global": {"stock": _fed()}}, as_of=AS_OF)
    assert ei.value.code == "global_aggregate_requested"

    # unknown region key -> unknown_region
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"mars": {}}, as_of=AS_OF)
    assert ei.value.code == "unknown_region"

    # refuse helper: None returns None, anything else raises
    assert refuse_global_aggregate(None) is None
    with pytest.raises(RegionalScenarioRefused) as ei:
        refuse_global_aggregate("usd_sum")
    assert ei.value.code == "global_aggregate_requested"

    m = build_scenario_map(full_owners(), as_of=AS_OF)
    assert m["global_scalar"] is None

    # AGGREGATE_NULL_STATUS matches every global_scalars.*.status in the v2 yaml
    statuses = [s["status"] for s in _SOURCES["global_scalars"].values()]
    assert statuses, "yaml should expose global_scalars entries"
    assert all(s == AGGREGATE_NULL_STATUS for s in statuses)
    assert m["aggregate_null_status"] == AGGREGATE_NULL_STATUS
    assert m["aggregate_null_reason"] == AGGREGATE_NULL_REASON
    assert m["aggregate_law_id"] == NO_GLOBAL_SCALAR


# ---------------------------------------------------------------------------
# T6  regional purity -- changing the china slice must not move other regions
# ---------------------------------------------------------------------------


def test_regional_independence_china_change_cannot_move_japan():
    baseline = build_scenario_map(full_owners(), as_of=AS_OF)

    tight_stance = copy.deepcopy(_STANCE)
    tight_stance["stance"] = "tightening"
    tight_stance["stance_en"] = "Tightening"
    tight_stance["stance_zh"] = "收紧"

    var_a = build_scenario_map(
        {
            **full_owners(),
            "china": {"stance": tight_stance, "tsf": _tsf()},
        },
        as_of=AS_OF,
    )
    var_b = build_scenario_map(
        {
            **full_owners(),
            "china": {"stance": _STANCE, "tsf": _tsf(latest=20000.0, prior=25000.0)},
        },
        as_of=AS_OF,
    )
    var_c = build_scenario_map(
        {r: v for r, v in full_owners().items() if r != "china"},
        as_of=AS_OF,
    )

    for region in ("us", "euro_area", "japan", "hong_kong"):
        assert var_a["regions"][region] == baseline["regions"][region]
        assert var_b["regions"][region] == baseline["regions"][region]
        assert var_c["regions"][region] == baseline["regions"][region]

    # qualify_region for japan with and without a china slice -> identical
    owners_a = full_owners()
    owners_b = {r: v for r, v in owners_a.items() if r != "china"}
    assert qualify_region("japan", owners=owners_a, as_of=AS_OF).to_dict() == \
        qualify_region("japan", owners=owners_b, as_of=AS_OF).to_dict()


# ---------------------------------------------------------------------------
# T7  HK without an owner is missing_input; partial owner stays missing
# ---------------------------------------------------------------------------


def test_hk_without_owner_is_missing_input():
    # No HK slice at all
    m = build_scenario_map(full_owners(), as_of=AS_OF)
    hk = m["regions"]["hong_kong"]
    assert hk["status"] == "missing_input"
    assert hk["missing_inputs"] == [HK_MISSING_TEXT]
    assert "HKMA aggregate balance" in hk["missing_inputs"][0]
    assert hk["laws_applied"] == [HK_CURRENCY_BOARD_AGG_BALANCE]

    # Partial owner (only store): missing text names the absent fields
    partial = {"stock": {"store": "data/hkma/x.parquet"}}
    m2 = build_scenario_map({"hong_kong": partial}, as_of=AS_OF)
    hk2 = m2["regions"]["hong_kong"]
    assert hk2["status"] == "missing_input"
    text = hk2["missing_inputs"][0]
    assert text.startswith("HKMA aggregate balance: missing owner field(s)")
    assert "local_unit" in text
    assert "known_at" in text

    # hk_full -> measured, local_unit HKD
    m3 = build_scenario_map({"hong_kong": {"stock": copy.deepcopy(_HK_FULL)}}, as_of=AS_OF)
    hk3 = m3["regions"]["hong_kong"]
    assert hk3["status"] == "measured"
    assert hk3["local_unit"] == "HKD"

    # hk_full with wrong concept -> concept_mismatch
    bad = copy.deepcopy(_HK_FULL)
    bad["concept"] = "central_bank_assets"
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"hong_kong": {"stock": bad}}, as_of=AS_OF)
    assert ei.value.code == "concept_mismatch"
    for col in ("gold_reserves", "fx_reserves"):
        hk_fx = copy.deepcopy(_HK_FULL)
        hk_fx["column"] = col
        with pytest.raises(RegionalScenarioRefused) as ei:
            build_scenario_map({"hong_kong": {"stock": hk_fx}}, as_of=AS_OF)
        assert ei.value.code == "fx_reserves_as_balance_sheet"
    hk_store = copy.deepcopy(_HK_FULL)
    hk_store["store"] = "data/china_pboc/fx_reserves.parquet"
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"hong_kong": {"stock": hk_store}}, as_of=AS_OF)
    assert ei.value.code == "fx_reserves_as_balance_sheet"
    with pytest.raises(RegionalScenarioRefused) as ei:
        refuse_fx_reserves_substitute("hkma_aggregate_balance", {"column": "fx_reserves"})
    assert ei.value.code == "fx_reserves_as_balance_sheet"
    hk_concept = copy.deepcopy(_HK_FULL)
    hk_concept["concept"] = "fx_reserves"
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"hong_kong": {"stock": hk_concept}}, as_of=AS_OF)
    assert ei.value.code == "concept_mismatch"


# ---------------------------------------------------------------------------
# T8  ECB/BoJ keep local units; usd is a separate translation line
# ---------------------------------------------------------------------------


def test_ecb_eur_local_unit_with_separate_usd_translation():
    m = build_scenario_map(full_owners(), as_of=AS_OF)
    ea = m["regions"]["euro_area"]
    assert ea["status"] == "measured"
    assert ea["local_unit"] == "EUR"
    assert ea["stock"]["local_unit"] == "EUR"
    assert ea["stock"]["value"] == 6_400_000.0
    assert not any("usd" in k for k in ea["stock"].keys())
    fx = ea["fx_translation"]
    assert fx is not None
    assert fx["is_fresh_money"] is False
    assert fx["basis"] == "translation_only"
    assert fx["usd_per_local"] == pytest.approx(1.10)
    assert fx["usd_value"] == pytest.approx(6_400_000.0 * 1e6 * 1.10)
    assert fx["law_id"] == "fx_translation_not_fresh_money"

    # No fixing -> still measured, usd_value None with null_reason
    owners = full_owners()
    owners["euro_area"] = {"stock": _ecb()}
    m2 = build_scenario_map(owners, as_of=AS_OF)
    ea2 = m2["regions"]["euro_area"]
    assert ea2["status"] == "measured"
    assert ea2["fx_translation"]["usd_value"] is None
    assert ea2["fx_translation"]["null_reason"] == "fx_fixing_missing"

    # Quote None -> fx_quote_unusable
    fix_none_quote = {**_eur_fix(), "quote": None}
    owners["euro_area"] = {"stock": _ecb(), "fx_fixing": fix_none_quote}
    m3 = build_scenario_map(owners, as_of=AS_OF)
    assert m3["regions"]["euro_area"]["fx_translation"]["usd_value"] is None
    assert m3["regions"]["euro_area"]["fx_translation"]["null_reason"] == "fx_quote_unusable"

    # ECB stock mis-labelled USD -> not_local_unit
    bad = _ecb()
    bad["local_unit"] = "USD"
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"euro_area": {"stock": bad, "fx_fixing": _eur_fix()}}, as_of=AS_OF)
    assert ei.value.code == "not_local_unit"

    # Japan: usd_per_local == 1/quote (invert), BOJ_MONTH_END_ANCHOR present
    jp = m["regions"]["japan"]
    assert jp["fx_translation"]["usd_per_local"] == pytest.approx(1.0 / 145.0)
    assert BOJ_MONTH_END_ANCHOR in jp["laws_applied"]
    bad_v = _ecb()
    bad_v["value"] = "6400000"
    with pytest.raises(TypeError):
        build_scenario_map({"euro_area": {"stock": bad_v}}, as_of=AS_OF)
    bad_m = _ecb()
    bad_m["unit_multiplier"] = "1e6"
    with pytest.raises(TypeError):
        build_scenario_map({"euro_area": {"stock": bad_m, "fx_fixing": _eur_fix()}}, as_of=AS_OF)
    bad_q = {**_eur_fix(), "quote": "1.10"}
    with pytest.raises(TypeError):
        build_scenario_map({"euro_area": {"stock": _ecb(), "fx_fixing": bad_q}}, as_of=AS_OF)


# ---------------------------------------------------------------------------
# T9  US reuses T08 estimate types and has no probability key
# ---------------------------------------------------------------------------


def test_us_reuses_t08_estimate_types_and_has_no_probability():
    assert regional.ESTIMATE_TYPES is OUTLOOK_ESTIMATE_TYPES

    m = build_scenario_map(full_owners(), as_of=AS_OF)
    us = m["regions"]["us"]
    assert us["status"] == "measured"
    sc = us["scenario"]
    assert sc is not None
    assert sc["source_schema"] == "glt_component_outlook_v1"
    for k in (
        "component_estimate_types",
        "reserves_estimate_type",
        "statistical_residual_estimate_type",
    ):
        assert k in sc
    # every estimate type listed is in ESTIMATE_TYPES
    for et in list(sc["component_estimate_types"].values()):
        assert et in OUTLOOK_ESTIMATE_TYPES
    assert sc["reserves_estimate_type"] in OUTLOOK_ESTIMATE_TYPES
    assert sc["statistical_residual_estimate_type"] in OUTLOOK_ESTIMATE_TYPES
    # no key anywhere in the US entry contains "probability"
    assert not any("probability" in k for k in _walk_keys(us))
    assert sc["authority"] == "measurement_only"
    assert sc["validated"] is False

    # Add a probability key to the outlook doc -> us_scenario_invalid
    doc = make_outlook()
    doc["probability"] = 0.5
    owners = full_owners()
    owners["us"] = {"stock": _fed(), "outlook": doc}
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map(owners, as_of=AS_OF)
    assert ei.value.code == "us_scenario_invalid"

    # A path estimate_type of "probabilistic" -> us_scenario_invalid
    doc2 = make_outlook()
    doc2["paths"]["total_assets"]["estimate_type"] = "probabilistic"
    owners["us"] = {"stock": _fed(), "outlook": doc2}
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map(owners, as_of=AS_OF)
    assert ei.value.code == "us_scenario_invalid"

    # No outlook -> scenario None
    owners_no = {"us": {"stock": _fed()}}
    m_no = build_scenario_map(owners_no, as_of=AS_OF)
    assert m_no["regions"]["us"]["scenario"] is None
    assert m_no["regions"]["us"]["status"] == "measured"
    doc3 = make_outlook()
    doc3["paths"]["total_assets"] = "not-a-mapping"
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"us": {"stock": _fed(), "outlook": doc3}}, as_of=AS_OF)
    assert ei.value.code == "us_scenario_invalid"
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"us": {"stock": _fed(), "outlook": "not-a-mapping"}}, as_of=AS_OF)
    assert ei.value.code == "us_scenario_invalid"


# ---------------------------------------------------------------------------
# T10  payload key scan -- no forbidden keys anywhere in the map
# ---------------------------------------------------------------------------


def test_payload_key_scan():
    m = build_scenario_map(full_owners(), as_of=AS_OF)
    forbidden = ("global_liquidity", "probability", "score", "confidence", "forecast", "calibrat")
    keys = list(_walk_keys(m))
    for k in keys:
        for f in forbidden:
            assert f not in k, f"forbidden fragment {f!r} in key {k!r}"
    # "global_scalar" occurs exactly once, top level, value None
    g_hits = [k for k in keys if k == "global_scalar"]
    assert len(g_hits) == 1
    assert m["global_scalar"] is None
    assert "global_scalar" in m  # top-level


# ---------------------------------------------------------------------------
# T11  PIT status / store / unit_multiplier are copied verbatim from S11
# ---------------------------------------------------------------------------


def test_pit_status_copied_from_s11():
    for component, maker, cfg_key in (
        ("fed", _fed, "fed"),
        ("ecb", _ecb, "ecb"),
        ("boj", _boj, "boj"),
    ):
        stock = maker()
        spec = _CFG["monetary_components"][cfg_key]
        assert stock["pit_status"] == spec["pit_status"]
        assert stock["unit_multiplier"] == spec["unit_multiplier"]
        assert stock["column"] == spec["column"]
        assert stock["store"] == f"data/{spec['store']}/{spec['key']}.parquet"
        assert stock["pit_status"] in PIT_STATUS_VOCAB

    # A stock whose pit_status is "exact" -> missing_input naming pit_status
    bad = copy.deepcopy(_fed())
    bad["pit_status"] = "exact"
    m = build_scenario_map({"us": {"stock": bad, "outlook": make_outlook()}}, as_of=AS_OF)
    text = m["regions"]["us"]["missing_inputs"][0]
    assert "pit_status" in text
    assert "missing owner field(s)" in text


# ---------------------------------------------------------------------------
# T12  China stance copies no score/fx/reserves/rationale/corridor/last_moves/built
# ---------------------------------------------------------------------------


def test_china_stance_copies_no_score_or_fx():
    m = build_scenario_map(full_owners(), as_of=AS_OF)
    cn = m["regions"]["china"]
    assert cn["status"] == "assumption_only_context"
    ctx = cn["context"]
    assert ctx[0]["kind"] == "pboc_stance"
    assert set(ctx[0].keys()) == {"kind", "owner_module", "schema", "stance", "asof"}
    # No forbidden key anywhere in the china entry
    forbidden_in_entry = {"score", "fx", "reserves", "rationale", "corridor", "last_moves", "built"}
    for k in _walk_keys(cn):
        assert k not in forbidden_in_entry, f"forbidden key {k!r} in china entry"
    assert cn["assumptions"] == [CN_NO_QUANTITY_ASSUMPTION]

    tsf_item = ctx[1]
    assert tsf_item["kind"] == "tsf_direction"
    assert tsf_item["direction"] == "higher"
    assert tsf_item["unit"] == "CNY 100 millions, monthly increment (flow)"
    assert tsf_item["comparability"] == "non_comparable_to_us_credit"
    assert tsf_item["law_id"] == CN_TSF_NON_COMPARABLE

    # latest None -> direction None with explicit null reason
    owners = full_owners()
    owners["china"] = {"stance": _STANCE, "tsf": _tsf(latest=None, prior=25000.0)}
    m2 = build_scenario_map(owners, as_of=AS_OF)
    cn2 = m2["regions"]["china"]
    tsf2 = cn2["context"][1]
    assert tsf2["direction"] is None
    assert tsf2["direction_null_reason"] == "tsf_value_null"

    # No stance and no tsf -> missing_input with three texts
    m3 = build_scenario_map({"china": {}}, as_of=AS_OF)
    cn3 = m3["regions"]["china"]
    assert cn3["status"] == "missing_input"
    assert len(cn3["missing_inputs"]) == 3
    assert PBOC_MISSING_TEXT in cn3["missing_inputs"]
    assert any("PBoC stance context" in t for t in cn3["missing_inputs"])
    assert any("China TSF" in t for t in cn3["missing_inputs"])

    # Wrong stance schema -> not in context
    bad = copy.deepcopy(_STANCE)
    bad["schema"] = "china_pboc_stance.v0"
    owners_bad = {"china": {"stance": bad}}
    m4 = build_scenario_map(owners_bad, as_of=AS_OF)
    cn4 = m4["regions"]["china"]
    assert cn4["status"] == "missing_input"
    # The stance item should NOT be in the context list
    assert not any(c.get("kind") == "pboc_stance" for c in cn4["context"])
    owners_s = full_owners()
    owners_s["china"] = {"stance": _STANCE, "tsf": _tsf(latest="9000.0", prior="25000.0")}
    with pytest.raises(TypeError):
        build_scenario_map(owners_s, as_of=AS_OF)


# ---------------------------------------------------------------------------
# T13  known_after_as_of refused for stock, stance, tsf and outlook
# ---------------------------------------------------------------------------


def test_known_after_as_of_refused():
    # Stock with known_at == AS_OF + 1 day
    fed_late = _fed()
    fed_late["known_at"] = AS_OF + timedelta(days=1)
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"us": {"stock": fed_late, "outlook": make_outlook()}}, as_of=AS_OF)
    assert ei.value.code == "known_after_as_of"

    # Stance with asof after as_of
    stance_late = copy.deepcopy(_STANCE)
    stance_late["asof"] = (AS_OF + timedelta(days=1)).isoformat()
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"china": {"stance": stance_late}}, as_of=AS_OF)
    assert ei.value.code == "known_after_as_of"

    # TSF known_at after as_of
    tsf_late = _tsf()
    tsf_late["known_at"] = AS_OF + timedelta(days=1)
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"china": {"tsf": tsf_late}}, as_of=AS_OF)
    assert ei.value.code == "known_after_as_of"

    # Outlook whose anchor was published after as_of -> known_after_as_of
    anchor_late = {
        "observed_on": date(2026, 9, 2),
        "published_at": datetime(AS_OF.year, AS_OF.month, AS_OF.day + 7, 16, 30, tzinfo=NY),
        "publication_tz": "America/New_York",
        "row": {},
    }
    outlook_late = compose_component_paths(
        anchor_late, [], [], as_of=AS_OF + timedelta(days=7),
    )
    owners = full_owners()
    owners["us"] = {"stock": _fed(), "outlook": outlook_late}
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map(owners, as_of=AS_OF)
    assert ei.value.code == "known_after_as_of"

    ecb_obs_late = _ecb()
    ecb_obs_late["observed_at"] = AS_OF + timedelta(days=1)
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"euro_area": {"stock": ecb_obs_late, "fx_fixing": _eur_fix()}}, as_of=AS_OF)
    assert ei.value.code == "known_after_as_of"
    tsf_obs_late = _tsf()
    tsf_obs_late["observed_at"] = AS_OF + timedelta(days=1)
    with pytest.raises(RegionalScenarioRefused) as ei:
        build_scenario_map({"china": {"tsf": tsf_obs_late}}, as_of=AS_OF)
    assert ei.value.code == "known_after_as_of"


# ---------------------------------------------------------------------------
# T14  map shape is measurement-only and two builds are equal
# ---------------------------------------------------------------------------


def test_map_shape_is_measurement_only():
    m = build_scenario_map(full_owners(), as_of=AS_OF)
    assert m["schema"] == SCHEMA
    assert list(m["regions"].keys()) == list(REGIONS)
    assert m["authority"] == "measurement_only"
    assert m["validated"] is False
    assert m["claim_level"] == CLAIM_LEVEL
    assert m["fit_policy"] == FIT_POLICY
    assert FIT_POLICY == "new empirical fits use T14"
    for entry in m["regions"].values():
        assert entry["status"] in STATUSES
    # Two builds are equal
    m2 = build_scenario_map(full_owners(), as_of=AS_OF)
    assert m == m2
    us_laws = [regional.LOCAL_UNIT_STOCK, regional.US_RESERVE_IDENTITY, regional.US_FUNDING_IDENTITY,
               regional.US_CONDITIONAL_ACCOUNTING]
    us_missing = build_scenario_map({}, as_of=AS_OF)["regions"]["us"]
    assert us_missing["status"] == "missing_input"
    assert us_missing["laws_applied"] == us_laws
    assert us_missing["laws_refused"] == []
    assert m["regions"]["us"]["laws_applied"] == us_laws
    assert m["regions"]["us"]["laws_refused"] == []
    for bad_stock in ("x", ["x"], 7):
        mm = build_scenario_map({"euro_area": {"stock": bad_stock}, "hong_kong": {"stock": bad_stock}}, as_of=AS_OF)
        assert mm["regions"]["euro_area"]["status"] == "missing_input"
        assert mm["regions"]["hong_kong"]["status"] == "missing_input"
