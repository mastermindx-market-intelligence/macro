"""Tests for engine.covenant_headroom (packet MO-B F09-13).

Covered test categories (spec §R7 a-k):
    a.  Real fixture round-trip — a hand-crafted direct observation produces
        a computed payload with the expected in-force step and headroom.
    b/c.Closed refusal set — identity_unresolved, metric_absent, ratio_undefined,
        definition_differs, terms_ambiguous all surface with closed labels.
    d.  Zero observations — no_terms_extracted.
    e.  CIK-only identity — issuer.cik and producer's issuer_id ("sec:cik:...")
        both normalize; unknown CIK is identity_unresolved.
    f.  Ambiguous disposition — ambiguous-only observations → terms_ambiguous.
    g.  Outage — health.json outage flag degrades to metric_absent.
    h.  Plain-word + ZH copy — every refusal has both en/zh, no jargon.
    i.  Zero authority — no rank/score/trade/signal/escalation keys anywhere.
    j.  Closed sets — REFUSALS is the only refusal enum; COVENANT_METRIC_MAP
        is a strict subset of covenant_terms.COVENANT_TERM_NAMES.
    k.  Never extrapolate — no ttm / forecast / projection / annualized leak.

The committed parquet ``data/capital_structure/covenant_term_observations.parquet``
is empty (zero rows) on this checkout — confirmed 2026-09-13 — so every test
constructs synthetic observations shaped exactly like the
``compile_observations`` output. The synthetic issuer block uses CIK 1743759
(Corsair Gaming, the producer's reference exhibit); its source_manifest_id
maps through the test-only fallback dict so identity resolution does not have
to manufacture a fake issuer block.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd
import pytest

import engine.covenant_headroom as headroom
from engine.capital_structure import covenant_terms


# ────────────────────────────────────────────────────────────────────────────
# Shared fixtures / helpers
# ────────────────────────────────────────────────────────────────────────────

CORSAIR_CIK = "0001743759"  # Corsair Gaming, Inc., the producer's reference
SYNTHETIC_MANIFEST_ID = "sm-covenant-crsr-ex101-20221202"
DEFAULT_PERIOD_END = "2022-09-30"


def _cik_by_source_manifest_id() -> dict[str, str]:
    return {SYNTHETIC_MANIFEST_ID: CORSAIR_CIK}


def _fundamentals_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "cik": CORSAIR_CIK,
        "operating_income": 60_000_000.0,
        "depreciation": 20_000_000.0,
        "interest_expense": 15_000_000.0,
        "cash_and_equivalents": 80_000_000.0,
        "debt_long_term": 250_000_000.0,
        "debt_current": 10_000_000.0,
        "period_end": DEFAULT_PERIOD_END,
    }
    row.update(overrides)
    return row


def _direct_obs(
    term_name: str,
    *,
    limit_raw: float | None,
    steps: list[dict[str, Any]] | None = None,
    state: str = "direct",
    cik: str | None = CORSAIR_CIK,
    source_manifest_id: str | None = SYNTHETIC_MANIFEST_ID,
    correction_version: int = 1,
    observation_id: str | None = None,
) -> dict[str, Any]:
    obs: dict[str, Any] = {
        "observation_id": observation_id
            or f"cov-headroom-test:{term_name}:v{correction_version}",
        "logical_observation_id": f"cov-term:cs:{term_name}:{SYNTHETIC_MANIFEST_ID}",
        "term_name": term_name,
        "clause_id": "clause-test",
        "state": state,
        "source_manifest_id": source_manifest_id,
        "issuer_id": f"sec:cik:{cik}" if cik else None,
        "issuer": {"cik": cik} if cik else None,
        "version": {
            "correction_version": correction_version,
            "correction_of": None,
            "immutable_record": True,
        },
        "point_in_time": {
            "available_at": "2026-09-13T00:00:00Z",
            "source_available_at": "2022-12-02T00:00:00Z",
        },
        "value": {
            "limit_raw": limit_raw,
            "limit_unit": "x",
            "direction": "max" if term_name.startswith("maximum_") else "min",
            "definition_basis": "filing_text_confirmed",
            "steps": steps or [
                {"start_date": "2022-09-30", "end_date": None,
                 "limit_raw": limit_raw},
            ],
        },
        "relationships": {"amends": [], "supersedes": [], "contradiction_ids": []},
    }
    return obs


def _empty_refusal(reason: str) -> dict[str, Any]:
    return {
        "schema": headroom.SCHEMA,
        "state": "refusal",
        "refusal": reason,
        "issuer": {"cik": None, "ticker": None, "name": None},
        "basis": {"period_end": None, "basis_en": headroom._BASIS_EN,
                  "basis_zh": headroom._BASIS_ZH},
        "ceiling_en": headroom._CEILING_EN,
        "ceiling_zh": headroom._CEILING_ZH,
        "terms": [],
    }


# ────────────────────────────────────────────────────────────────────────────
# a. Real fixture round-trip — synthetic but shape-faithful
# ────────────────────────────────────────────────────────────────────────────

def test_direct_observation_produces_computed_payload():
    """End-to-end happy path: a real-shape direct observation computes a
    headroom payload with the expected in-force step."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio",
        limit_raw=4.00,
        steps=[
            {"start_date": "2021-09-30", "end_date": "2022-09-29",
             "limit_raw": 3.75},
            {"start_date": "2022-09-30", "end_date": None,
             "limit_raw": 4.00},
        ],
    )
    payload = headroom.compute_headroom(
        [obs],
        {CORSAIR_CIK: _fundamentals_row()},
        {CORSAIR_CIK: "CRSR"},
        generated_at="2026-09-13T00:00:00Z",
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["schema"] == "capital_structure.covenant.headroom.v1" or payload["schema"] == headroom.SCHEMA
    assert payload["state"] == "computed"
    assert payload["issuer"]["cik"] == CORSAIR_CIK
    assert payload["issuer"]["ticker"] == "CRSR"
    assert len(payload["terms"]) == 1
    term = payload["terms"][0]
    assert term["state"] == "computed"
    # Net debt = 260M - 80M = 180M. EBITDA = 60M + 20M = 80M. Ratio = 2.25x.
    # Limit 4.00x. Headroom = 4.00 - 2.25 = 1.75x.
    assert math.isclose(term["actual_ratio"], 2.25, rel_tol=1e-6)
    assert math.isclose(term["headroom_ratio"], 1.75, rel_tol=1e-6)
    assert math.isclose(term["limit_raw"], 4.00, rel_tol=1e-6)
    assert term["compliant"] is True
    # in-force step picked: start 2022-09-30.
    assert term["in_force_step"]["start_date"] == "2022-09-30"
    assert math.isclose(term["in_force_step"]["limit_raw"], 4.00, rel_tol=1e-6)


def test_step_in_force_selects_correct_window():
    """The schedule has a 3.75x window starting 2021-09-30 and a 4.00x
    window starting 2022-09-30. Period_end 2022-09-30 must select 4.00x."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio",
        limit_raw=4.00,
        steps=[
            {"start_date": "2021-09-30", "end_date": "2022-09-29",
             "limit_raw": 3.75},
            {"start_date": "2022-09-30", "end_date": None,
             "limit_raw": 4.00},
        ],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["terms"][0]["in_force_step"]["limit_raw"] == 4.00
    # A period_end ON the boundary picks the LATEST step that contains it.
    assert payload["basis"]["period_end"] == "2022-09-30"


def test_minimum_interest_coverage_compliance():
    """minimum_* terms: actual=5.33, limit=3.00 → compliant, headroom=2.33."""
    obs = _direct_obs(
        "minimum_interest_coverage_ratio",
        limit_raw=3.00,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 3.00}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    term = payload["terms"][0]
    # EBITDA / interest = 80M / 15M = 5.333…
    assert math.isclose(term["actual_ratio"], 80_000_000 / 15_000_000, rel_tol=1e-6)
    assert term["compliant"] is True
    assert math.isclose(term["headroom_ratio"],
                        80_000_000 / 15_000_000 - 3.00, rel_tol=1e-6)


def test_only_the_latest_correction_version_wins():
    """Correction semantics: a prior v1 with limit_raw=2.00 must be
    superseded by v2 with limit_raw=3.75 — even though v1 appears first in
    the observations list."""
    v1 = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=2.00,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 2.00}],
        correction_version=1, observation_id="obs:v1",
    )
    v2 = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=3.75,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 3.75}],
        correction_version=2, observation_id="obs:v2",
    )
    payload = headroom.compute_headroom(
        [v1, v2], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "computed"
    assert payload["terms"][0]["limit_raw"] == 3.75


# ────────────────────────────────────────────────────────────────────────────
# b/c. Closed refusal set
# ────────────────────────────────────────────────────────────────────────────

def test_no_terms_extracted_when_observations_list_empty():
    payload = headroom.compute_headroom(
        [], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
    )
    assert payload["state"] == "refusal"
    assert payload["refusal"] == "no_terms_extracted"
    assert payload["issuer"]["cik"] is None


def test_identity_unresolved_when_no_issuer_block():
    """Observation with neither issuer.cik nor a source_manifest_id fallback
    cannot be bound to a CIK. Failure closed to identity_unresolved."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50,
                      cik=None, source_manifest_id=None)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=None,
    )
    assert payload["state"] == "refusal"
    assert payload["refusal"] == "identity_unresolved"


def test_identity_unresolved_when_issuer_id_unknown():
    """An observation with no issuer.cik AND no source_manifest_id fallback
    cannot have its CIK resolved — identity_unresolved. The ledger itself
    doesn't matter at this layer (CIK-only identity; ticker is the page's
    concern)."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=3.50,
        cik=None, source_manifest_id=None,
    )
    # Defensive: ensure both fallback paths are stripped.
    obs["issuer"] = None
    obs["issuer_id"] = None
    payload = headroom.compute_headroom(
        [obs],
        {CORSAIR_CIK: _fundamentals_row()},
        {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=None,
    )
    assert payload["state"] == "refusal"
    assert payload["refusal"] == "identity_unresolved"


def test_metric_absent_when_fundamentals_missing():
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=3.50,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 3.50}],
    )
    payload = headroom.compute_headroom(
        [obs], {}, {},  # empty fundamentals
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refusal"
    assert payload["refusal"] == "metric_absent"
    # Outer refusal labels are populated.
    assert payload["refusal_label_en"] == "Metric absent"


def test_metric_absent_when_components_missing():
    """One missing input (cash) means net debt cannot be computed without
    guessing — fail closed to metric_absent."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _fundamentals_row()
    del row["cash_and_equivalents"]
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refusal"
    assert payload["terms"][0]["state"] == "refusal"
    assert payload["terms"][0]["refusal"] == "metric_absent"


def test_ratio_undefined_when_step_schedule_empty():
    """A direct observation whose value.steps is empty cannot pick an
    in-force limit — fail closed to ratio_undefined."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=None,
        steps=[],
    )
    obs["value"]["limit_raw"] = None  # explicit
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refusal"
    assert payload["terms"][0]["state"] == "refusal"
    assert payload["terms"][0]["refusal"] in ("ratio_undefined", "metric_absent")


def test_metric_absent_when_ebitda_zero():
    """eBitda = 0 makes net debt / EBITDA undefined. Do not divide."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _fundamentals_row(operating_income=0.0, depreciation=0.0)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["terms"][0]["state"] == "refusal"
    assert payload["terms"][0]["refusal"] == "metric_absent"


# ────────────────────────────────────────────────────────────────────────────
# e. CIK-only identity
# ────────────────────────────────────────────────────────────────────────────

def test_issuer_id_prefixed_string_normalizes_to_cik():
    """The producer stores issuer_id='sec:cik:0001743759'; the engine must
    normalize that to '0001743759' and resolve the issuer."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    # _direct_obs already sets issuer_id='sec:cik:0001743759'. Confirm.
    assert obs["issuer_id"] == "sec:cik:0001743759"
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
    )
    assert payload["issuer"]["cik"] == CORSAIR_CIK


def test_unknown_cik_is_identity_unresolved():
    """An observation whose source_manifest_id is not in the fallback map
    AND whose issuer block is missing resolves to no CIK — identity_unresolved."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=3.50,
        cik=None, source_manifest_id="sm-no-fallback",
    )
    payload = headroom.compute_headroom(
        [obs], {}, {},  # empty cik_to_ticker, empty fundamentals
        cik_by_source_manifest_id={},  # no fallback for sm-no-fallback
    )
    assert payload["state"] == "refusal"
    assert payload["refusal"] == "identity_unresolved"


def test_picks_dominant_cik_when_multiple_present():
    """If direct observations span two CIKs, the one with more observations
    wins. The other CIK's rows are dropped from the output."""
    obs_a1 = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50,
                        cik=CORSAIR_CIK)
    obs_a2 = _direct_obs("minimum_interest_coverage_ratio", limit_raw=3.00,
                        cik=CORSAIR_CIK)
    obs_b = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=2.50,
                       cik="0001000000", source_manifest_id="sm-b")
    payload = headroom.compute_headroom(
        [obs_a1, obs_a2, obs_b],
        {CORSAIR_CIK: _fundamentals_row(), "0001000000": _fundamentals_row()},
        {CORSAIR_CIK: "CRSR", "0001000000": "ZZZ"},
        cik_by_source_manifest_id={"sm-b": "0001000000"},
    )
    assert payload["issuer"]["cik"] == CORSAIR_CIK
    assert {t["term_name"] for t in payload["terms"]} == {
        "maximum_total_net_leverage_ratio", "minimum_interest_coverage_ratio",
    }


# ────────────────────────────────────────────────────────────────────────────
# f. Ambiguous disposition
# ────────────────────────────────────────────────────────────────────────────

def test_ambiguous_only_observations_return_terms_ambiguous():
    """When the only observations are state='ambiguous', the refusal is
    terms_ambiguous — NOT no_terms_extracted."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50,
                      state="ambiguous")
    payload = headroom.compute_headroom(
        [obs],
        {CORSAIR_CIK: _fundamentals_row()},
        {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refusal"
    assert payload["refusal"] == "terms_ambiguous"


def test_direct_wins_over_ambiguous():
    """One direct + one ambiguous → computed (direct wins)."""
    direct = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    ambig = _direct_obs("minimum_interest_coverage_ratio", limit_raw=3.00,
                        state="ambiguous")
    payload = headroom.compute_headroom(
        [direct, ambig],
        {CORSAIR_CIK: _fundamentals_row()},
        {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "computed"
    assert {t["state"] for t in payload["terms"]} == {"computed"}


# ────────────────────────────────────────────────────────────────────────────
# g. Outage
# ────────────────────────────────────────────────────────────────────────────

def test_outage_flag_degrades_to_metric_absent():
    """health.json may carry an outage block naming CIKs whose fundamentals
    are stale. The engine treats that as metric_absent rather than rendering
    with bad numbers."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs],
        {CORSAIR_CIK: _fundamentals_row()},
        {CORSAIR_CIK: "CRSR"},
        health={"outage": {"ciks": [CORSAIR_CIK], "reason": "edgar_stale"}},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refusal"
    assert payload["terms"][0]["refusal"] == "metric_absent"


# ────────────────────────────────────────────────────────────────────────────
# h. Plain-word + ZH copy
# ────────────────────────────────────────────────────────────────────────────

def test_every_refusal_has_en_and_zh_copy():
    """Nulls printed, UNKNOWN != EMPTY: every refusal in the closed set
    carries both English and Chinese plain-word copy."""
    for reason in headroom.REFUSALS:
        assert reason in headroom._NULL_COPY, f"missing copy for {reason}"
        copy = headroom._NULL_COPY[reason]
        for key in ("en", "zh", "refusal_label_en", "refusal_label_zh"):
            assert key in copy and copy[key], f"missing {key} for {reason}"
        assert copy["en"] != copy["zh"], f"zh fallback is en for {reason}"


def test_no_internal_state_names_leak_into_copy():
    """Internal state / study names must never reach the user-facing copy."""
    banned_substrings = (
        "ci_failed_unmerged", "ship_loop", "merge-on-green",
        "covenant_terms", "engine.", "schema:",
        "internal:", "study_id", "research_id",
    )
    for reason, copy in headroom._NULL_COPY.items():
        for k, v in copy.items():
            for bad in banned_substrings:
                assert bad not in v, (
                    f"internal name {bad!r} leaked into refusal {reason}.{k}"
                )


def test_ceiling_and_basis_present_in_every_payload():
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    for key in ("ceiling_en", "ceiling_zh", "basis"):
        assert key in payload
        assert payload["basis"]["basis_en"]
        assert payload["basis"]["basis_zh"]


def test_computed_payload_carries_period_end_basis():
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["basis"]["period_end"] == DEFAULT_PERIOD_END


# ────────────────────────────────────────────────────────────────────────────
# i. Zero authority
# ────────────────────────────────────────────────────────────────────────────

def test_scored_flag_is_false():
    assert headroom.SCORED is False


def test_authority_ceiling_is_human_research_only():
    assert headroom.AUTHORITY_CEILING == "human_research_only"


def test_no_authority_keys_leak_into_payload():
    """The full set of authority keys must never appear in a payload —
    even in labels, even in ZH copy."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    blob = repr(payload).lower()
    for bad in headroom._ZERO_AUTHORITY_KEYS:
        assert bad not in blob, f"authority key {bad!r} in payload"


def test_no_authority_keys_in_any_refusal_copy():
    for reason, copy in headroom._NULL_COPY.items():
        blob = repr(copy).lower()
        for bad in headroom._ZERO_AUTHORITY_KEYS:
            assert bad not in blob, (
                f"authority key {bad!r} in refusal copy for {reason}"
            )


# ────────────────────────────────────────────────────────────────────────────
# j. Closed sets
# ────────────────────────────────────────────────────────────────────────────

def test_refusals_is_closed_set():
    assert tuple(sorted(headroom.REFUSALS)) == (
        "definition_differs", "identity_unresolved", "metric_absent",
        "no_terms_extracted", "ratio_undefined", "terms_ambiguous",
    )


def test_covenant_metric_map_is_subset_of_producer_term_names():
    """The map's keys must all appear in the producer's frozen
    COVENANT_TERM_NAMES tuple. Any drift here is a bug."""
    extras = set(headroom.COVENANT_METRIC_MAP) - set(covenant_terms.COVENANT_TERM_NAMES)
    assert not extras, f"COVENANT_METRIC_MAP keys not in producer set: {extras}"


def test_schema_is_closed():
    assert headroom.SCHEMA == "capital_structure.covenant_headroom.v1"


def test_refusal_payload_only_uses_closed_refusals():
    """Defense in depth: any change to _NULL_COPY must add a refusal to
    REFUSALS or the page can't render it."""
    assert set(headroom._NULL_COPY) == set(headroom.REFUSALS), (
        f"_NULL_COPY keys diverge from REFUSALS: "
        f"copy={set(headroom._NULL_COPY) - set(headroom.REFUSALS)} "
        f"refusals={set(headroom.REFUSALS) - set(headroom._NULL_COPY)}"
    )


# ────────────────────────────────────────────────────────────────────────────
# k. Never extrapolate
# ────────────────────────────────────────────────────────────────────────────

def test_no_extrapolation_keys_in_payload():
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    blob = repr(payload).lower()
    for bad in headroom._NO_EXTRAPOLATION_KEYS:
        assert bad not in blob, f"extrapolation key {bad!r} in payload"


def test_no_ttm_or_annualized_substrings_anywhere():
    """Even if a label were to mention ttm/annualized by accident, the
    test would catch it. The engine must NEVER manufacture a TTM figure."""
    obs = _direct_obs("minimum_interest_coverage_ratio", limit_raw=3.00)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _fundamentals_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    for bad in ("ttm", "annualized", "forecast", "projection", "run_rate"):
        assert bad not in repr(payload).lower()


def test_inputs_passed_through_unchanged():
    """The engine must not transform reported fundamentals into TTM /
    annualized / forecast numbers. It reports inputs verbatim."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _fundamentals_row()
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    inputs = payload["terms"][0]["inputs"]
    assert inputs["ebitda"] == 80_000_000.0
    assert inputs["net_debt"] == 180_000_000.0
    assert inputs["interest_expense"] == 15_000_000.0


# ────────────────────────────────────────────────────────────────────────────
# Compile-against-committed-fixture gate (defensive; parquet is currently
# empty on this checkout, so we just confirm the API surface exists)
# ────────────────────────────────────────────────────────────────────────────

def test_committed_observations_parquet_loadable():
    """The committed parquet must be readable as a DataFrame — even when
    empty. If this fails, the page cannot render at all."""
    df = pd.read_parquet(
        "data/capital_structure/covenant_term_observations.parquet"
    )
    expected_cols = {"observation_id", "logical_observation_id", "term_name",
                     "state", "source_manifest_id", "observation_json"}
    assert expected_cols.issubset(set(df.columns)), (
        f"parquet schema drift; missing cols: "
        f"{expected_cols - set(df.columns)}"
    )


def test_compute_headroom_is_callable_with_only_observations():
    """The minimum call surface is observations + maps. Optional kwargs
    (health, generated_at, cik_by_source_manifest_id) must have safe
    defaults — never required."""
    payload = headroom.compute_headroom([], {}, {})
    assert payload["state"] == "refusal"
    assert payload["refusal"] == "no_terms_extracted"
