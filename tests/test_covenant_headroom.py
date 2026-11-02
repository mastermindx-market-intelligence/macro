"""Tests for engine.covenant_headroom (packet MO-B F09-13, MO-PAID-062 slice 2).

Spec R7 a–k, with RED-first evidence for each behavioural fix from the round-2
review (B-F09-13 / MO-PAID-062 review FIX_REQUIRED). The round-1 PR emitted
the engine with several spec deviations; round-2 flips them all to spec. The
relevant BLOCKERS and MAJORS:

  B1   maximum_secured_net_leverage_ratio → definition_differs (always)
  B2   minimum_fixed_charge_coverage_ratio → definition_differs (always)
  B3/4 definition_differs also covers minimum_liquidity_amount and
       restricted_payments_basket_amount
  B5   net debt via engine.stock_fundamentals._net_debt (single-definition law)
  B6   EBITDA ≤ 0 OR interest_exp ≤ 0 → ratio_undefined (not metric_absent)
  B7   ceiling + basis EN/ZH copy verbatim from the spec
  B8   panel computed-state copy is the spec's literal sentence
  B9   the literal "Headroom" never reaches user copy
  B10  full grid + EDGAR link
  B11  spec-verbatim "Not covered here" footer
  M1   synthetic secured-term → definition_differs test (added)
  M2   EBITDA = 0 → ratio_undefined test (added)
  M3   PR body Records + GAP line (handled outside tests)
  M4   evidence packet (handled outside tests)
  M5   schema pinned to the spec value
  M6   parquet-loadable test dropped (sparse worktree + redundant with builder)

Every behavioural assertion cites the spec line it enforces; the corresponding
prior-head test (where one existed) is documented as the regression it locks
out. The build-time parquet read is exercised in
test_covenant_headroom_builder rather than here — the builder's defensive
catch in scripts/build_capital_structure_page.py covers it.
"""
from __future__ import annotations

import re
from typing import Any

import pytest

import engine.covenant_headroom as headroom

# MAJOR 3 fix: guard the optional import that fails collection on Python 3.14
# (jsonschema not installed there). The two tests that need covenant_terms
# (test_covenant_metric_map_is_subset_of_producer_term_names and
# test_always_definition_differs_covers_all_definition_differs_terms) are skipped
# when this import is unavailable.
try:
    from engine.capital_structure import covenant_terms
    _covenant_terms_available = True
except Exception:
    covenant_terms = None  # type: ignore[assignment]
    _covenant_terms_available = False


# ────────────────────────────────────────────────────────────────────────────
# Shared fixtures / helpers
# ────────────────────────────────────────────────────────────────────────────

CORSAIR_CIK = "0001743759"  # Corsair Gaming, Inc., the producer's reference
SYNTHETIC_MANIFEST_ID = "sm-covenant-crsr-ex101-20221202"
DEFAULT_PERIOD_END = "2022-12-31"  # non-fallback synthetic CRSR FY row


def _cik_by_source_manifest_id() -> dict[str, str]:
    return {SYNTHETIC_MANIFEST_ID: CORSAIR_CIK}


def _stmt_row(**overrides: Any) -> dict[str, Any]:
    """Spec R7(a) — synthetic NON-FALLBACK CRSR statement row.

    Canonical column names are ``debt_lt``, ``debt_cur``, ``cash``,
    ``op_income``, ``depreciation``, ``interest_exp``, ``period_end`` —
    matching what ``engine.stock_fundamentals._leverage_ratios`` reads.
    Net debt = 250 + 10 − 80 = 180. EBITDA = 60 + 20 = 80. Interest = 15.
    """
    row = {
        "cik": CORSAIR_CIK,
        "op_income": 60_000_000.0,
        "depreciation": 20_000_000.0,
        "interest_exp": 15_000_000.0,
        "cash": 80_000_000.0,
        "debt_lt": 250_000_000.0,
        "debt_cur": 10_000_000.0,
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
    accession: str | None = "0001564590-22-038930",
    form: str | None = "EX-10.1",
    filing_date: str | None = "2022-12-02",
    source_url: str | None = "https://www.sec.gov/Archives/edgar/data/1743759/000156459022038930/ex10-1.htm",
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
        "accession": accession,
        "form": form,
        "filing_date": filing_date,
        "source_url": source_url,
        "value": {
            "limit_raw": limit_raw,
            "limit_unit": "x",
            "direction": "max" if term_name.startswith("maximum_") else "min",
            "definition_basis": "filing_text_confirmed",
            "headline_ratio_text": "3.50 to 1.00",
            "section_label": "Section 7.11 Financial Covenants",
            "steps": steps or [
                {"start_date": "2022-09-30", "end_date": None,
                 "limit_raw": limit_raw},
            ],
        },
        "relationships": {"amends": [], "supersedes": [], "contradiction_ids": []},
    }
    return obs


# ────────────────────────────────────────────────────────────────────────────
# Schema pin (spec R1 + reviewer M5)
# ────────────────────────────────────────────────────────────────────────────

def test_schema_is_closed():
    """Spec R1 freezes ``capital_structure.covenant_headroom.v1`` (two-segment,
    underscore between covenant and headroom). Round 2's dotted variant is
    FIX_REQUIRED: ruler H5 re-pins the underscore form across engine + payloads
    + tests."""
    assert headroom.SCHEMA == "capital_structure.covenant_headroom.v1"


# ────────────────────────────────────────────────────────────────────────────
# a. Real fixture round-trip — spec R7(a) — synthetic CRSR FY row
# ────────────────────────────────────────────────────────────────────────────

def test_direct_observation_produces_computed_payload():
    """Spec R7(a): the engine computes leverage 2.25x vs 3.50x limit,
    room 1.25x, inside_limit True. Period_end selects the step IN FORCE
    AT that period_end."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio",
        limit_raw=3.50,
        steps=[
            {"start_date": "2021-09-30", "end_date": "2022-09-29",
             "limit_raw": 3.50},
            {"start_date": "2022-09-30", "end_date": None,
             "limit_raw": 3.50},
        ],
    )
    payload = headroom.compute_headroom(
        [obs],
        {CORSAIR_CIK: _stmt_row()},
        {CORSAIR_CIK: "CRSR"},
        generated_at="2026-09-13T00:00:00Z",
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["schema"] == headroom.SCHEMA
    assert payload["state"] == "computed"
    assert payload["issuer"]["cik"] == CORSAIR_CIK
    assert payload["issuer"]["ticker"] == "CRSR"
    assert len(payload["terms"]) == 1
    term = payload["terms"][0]
    assert term["state"] == "computed"
    # net debt = 250 + 10 − 80 = 180. EBITDA = 60 + 20 = 80. Ratio = 2.25x.
    assert term["reported"]["value"] == pytest.approx(2.25, rel=1e-6)
    assert term["reported"]["period_end"] == DEFAULT_PERIOD_END
    assert term["reported"]["basis"] == "reported_not_agreement_defined"
    assert term["reported"]["metric_key"] == "headroom_to_net_leverage_limit"
    # Limit 3.50x. Headroom = 3.50 − 2.25 = 1.25x.
    assert term["limit_raw"] == pytest.approx(3.50, rel=1e-6)
    assert term["room_turns"] == pytest.approx(1.25, rel=1e-6)
    assert term["inside_limit"] is True
    # in-force step picked: start 2022-09-30.
    assert term["in_force_step"]["start_date"] == "2022-09-30"


def test_step_in_force_selects_correct_window():
    """Spec R7(a): the schedule has a 3.75x window starting 2021-09-30 and
    a 4.00x window starting 2022-09-30. Period_end 2022-09-30 selects the
    step whose window contains it. With period_end 2022-12-31 (the spec's
    synthetic CRSR row), the step starting 2022-09-30 is selected."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio",
        limit_raw=3.50,
        steps=[
            {"start_date": "2021-09-30", "end_date": "2022-09-29",
             "limit_raw": 3.75},
            {"start_date": "2022-09-30", "end_date": None,
             "limit_raw": 4.00},
        ],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    # period_end 2022-12-31 selects the step whose window contains it.
    assert payload["terms"][0]["in_force_step"]["limit_raw"] == 4.00
    assert payload["terms"][0]["in_force_step"]["start_date"] == "2022-09-30"
    assert payload["basis_period_end"] == DEFAULT_PERIOD_END


def test_minimum_interest_coverage_compliance():
    """Spec R2 + R7(a): minimum_* terms: EBITDA/interest = 5.33x vs 3.00x
    floor; room = 5.33 − 3.00 = 2.33x; inside_limit True."""
    obs = _direct_obs(
        "minimum_interest_coverage_ratio",
        limit_raw=3.00,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 3.00}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    term = payload["terms"][0]
    # EBITDA / interest = 80M / 15M = 5.333…
    assert term["reported"]["value"] == pytest.approx(80_000_000 / 15_000_000, rel=1e-6)
    assert term["inside_limit"] is True
    assert term["room_turns"] == pytest.approx(
        80_000_000 / 15_000_000 - 3.00, rel=1e-6
    )
    assert term["limit_kind"] == "minimum"


def test_only_the_latest_correction_version_wins():
    """Correction semantics: a prior v1 with limit_raw=2.00 must be
    superseded by v2 with limit_raw=3.75."""
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
        [v1, v2], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "computed"
    assert payload["terms"][0]["limit_raw"] == 3.75


# ────────────────────────────────────────────────────────────────────────────
# b/c. Closed refusal set — every member reachable
# ────────────────────────────────────────────────────────────────────────────

def test_no_terms_extracted_when_observations_list_empty():
    """Spec R7(d): zero observations → no_terms_extracted, with coverage
    counts copied from the supplied coverage block."""
    payload = headroom.compute_headroom(
        [], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        coverage={"covered_manifests": 0, "eligible_exhibits": 2450,
                  "issuers_covered": 0, "state": "uncovered"},
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "no_terms_extracted"
    assert payload["issuer"]["cik"] is None
    # Spec R6 — count-bearing copy when coverage is present.
    assert "2,450" in payload["null_en"]
    assert "2,450" not in payload["null_en"].split("Of ")[0]
    assert "2450" in payload["null_en"].replace(",", "")
    # Coverage block pins health.json's covenant_extraction values verbatim.
    assert payload["coverage"]["eligible_exhibits"] == 2450
    assert payload["coverage"]["covered_manifests"] == 0


def test_no_terms_extracted_omits_counts_when_coverage_is_null():
    """Spec R6 — when coverage is None (e.g. health.json missing) the
    no_terms_extracted copy drops the count placeholders."""
    payload = headroom.compute_headroom(
        [], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "no_terms_extracted"
    # Coverage block present but null-valued.
    assert payload["coverage"]["eligible_exhibits"] is None
    assert payload["coverage"]["covered_manifests"] is None


def test_identity_unresolved_when_no_issuer_block():
    """Observation with neither issuer.cik nor a source_manifest_id
    fallback cannot be bound to a CIK."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50,
                      cik=None, source_manifest_id=None)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=None,
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "identity_unresolved"


def test_identity_unresolved_when_issuer_id_unknown():
    """Defensive: ensure both fallback paths are stripped."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=3.50,
        cik=None, source_manifest_id=None,
    )
    obs["issuer"] = None
    obs["issuer_id"] = None
    payload = headroom.compute_headroom(
        [obs],
        {CORSAIR_CIK: _stmt_row()},
        {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=None,
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "identity_unresolved"


def test_metric_absent_when_fundamentals_missing():
    """No statements row at all → metric_absent at the term level."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=3.50,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 3.50}],
    )
    payload = headroom.compute_headroom(
        [obs], {}, {},  # empty fundamentals
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    # Outer refusal mirrors the term refusal.
    assert payload["refusal"] == "metric_absent"


def test_metric_absent_when_components_missing():
    """A missing input means net debt cannot be computed without
    guessing — fail closed to metric_absent."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _stmt_row()
    del row["cash"]
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "metric_absent"


def test_ratio_undefined_when_step_schedule_empty():
    """Spec — A direct observation whose value.steps is empty cannot pick
    an in-force limit — fail closed to ratio_undefined."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=None,
        steps=[],
    )
    obs["value"]["limit_raw"] = None
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "ratio_undefined"


def test_ratio_undefined_when_ebitda_zero_block2():
    """Spec R7(c) + B6: EBITDA = 0 (operating_income = 0, depreciation = 0)
    must yield refusal ``ratio_undefined``, not ``metric_absent``.

    Round-1 pinned ``metric_absent`` — that test was the engine's bug.
    Round-2 flips it to ``ratio_undefined`` (the spec)."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _stmt_row(op_income=0.0, depreciation=0.0)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "ratio_undefined"


def test_ratio_undefined_when_ebitda_negative_block2():
    """Spec R7(c) — negative EBITDA → ratio_undefined (not metric_absent).
    Negative EBITDA is a degenerate ratio even when inputs are present."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _stmt_row(op_income=-10_000_000.0, depreciation=5_000_000.0)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "ratio_undefined"


def test_ratio_undefined_when_interest_exp_zero_block2():
    """Spec R7(c) — interest_exp = 0 → ratio_undefined (not metric_absent).
    Denominator-zero makes the ratio undefined."""
    obs = _direct_obs("minimum_interest_coverage_ratio", limit_raw=3.00)
    row = _stmt_row(interest_exp=0.0)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "ratio_undefined"


def test_definition_differs_for_secured_leverage_block1():
    """Spec R2 + B1: maximum_secured_net_leverage_ratio ALWAYS refuses
    definition_differs. Reported statements do not split secured from total
    debt; computing it as net_debt/EBITDA fabricates a number the producer
    did not assert. This is reviewer B1."""
    obs = _direct_obs(
        "maximum_secured_net_leverage_ratio",
        limit_raw=2.50,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 2.50}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "definition_differs"
    term = payload["terms"][0]
    assert term["refusal"] == "definition_differs"
    assert term["reported"]["value"] is None
    assert term["room_turns"] is None


def test_definition_differs_for_fixed_charge_coverage_block2():
    """Spec R2 + B2: minimum_fixed_charge_coverage_ratio ALWAYS refuses
    definition_differs. Fixed charges are not one reported line; computing
    it as EBITDA/interest fabricates a number. Reviewer B2."""
    obs = _direct_obs(
        "minimum_fixed_charge_coverage_ratio",
        limit_raw=1.10,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 1.10}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "definition_differs"
    term = payload["terms"][0]
    assert term["refusal"] == "definition_differs"
    assert term["reported"]["value"] is None


def test_definition_differs_for_liquidity_block3():
    """Spec R2 + B3/4: minimum_liquidity_amount ALWAYS refuses
    definition_differs. Revolver availability is not a reported fact."""
    obs = _direct_obs(
        "minimum_liquidity_amount",
        limit_raw=50_000_000.0,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 50_000_000.0}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "definition_differs"


def test_definition_differs_for_restricted_payments_basket_block4():
    """Spec R2 + B3/4: restricted_payments_basket_amount ALWAYS refuses
    definition_differs. Basket usage is not a reported fact."""
    obs = _direct_obs(
        "restricted_payments_basket_amount",
        limit_raw=100_000_000.0,
        steps=[{"start_date": "2022-09-30", "end_date": None,
                "limit_raw": 100_000_000.0}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "definition_differs"


# ────────────────────────────────────────────────────────────────────────────
# e. CIK-only identity
# ────────────────────────────────────────────────────────────────────────────

def test_issuer_id_prefixed_string_normalizes_to_cik():
    """The producer stores issuer_id='sec:cik:0001743759'; the engine
    normalizes that to '0001743759' and resolves the issuer."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    assert obs["issuer_id"] == "sec:cik:0001743759"
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
    )
    assert payload["issuer"]["cik"] == CORSAIR_CIK


def test_unknown_cik_is_identity_unresolved():
    """An observation whose source_manifest_id is not in the fallback map
    AND whose issuer block is missing resolves to no CIK."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=3.50,
        cik=None, source_manifest_id="sm-no-fallback",
    )
    payload = headroom.compute_headroom(
        [obs], {}, {},
        cik_by_source_manifest_id={},
    )
    assert payload["state"] == "refused"
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
        {CORSAIR_CIK: _stmt_row(), "0001000000": _stmt_row()},
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
    terms_ambiguous."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50,
                      state="ambiguous")
    payload = headroom.compute_headroom(
        [obs],
        {CORSAIR_CIK: _stmt_row()},
        {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "terms_ambiguous"


def test_direct_wins_over_ambiguous():
    """One direct + one ambiguous → computed (direct wins)."""
    direct = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    ambig = _direct_obs("minimum_interest_coverage_ratio", limit_raw=3.00,
                        state="ambiguous")
    payload = headroom.compute_headroom(
        [direct, ambig],
        {CORSAIR_CIK: _stmt_row()},
        {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "computed"
    # Only the direct observation is computed; the ambiguous one is not
    # in the terms list (direct_obs is the source of truth).
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
        {CORSAIR_CIK: _stmt_row()},
        {CORSAIR_CIK: "CRSR"},
        health={"outage": {"ciks": [CORSAIR_CIK], "reason": "edgar_stale"}},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["state"] == "refused"
    assert payload["refusal"] == "metric_absent"


# ────────────────────────────────────────────────────────────────────────────
# h. Plain-word + ZH copy
# ────────────────────────────────────────────────────────────────────────────

def test_every_refusal_has_en_and_zh_copy():
    """Spec R6 — every refusal in the closed set carries both English and
    Chinese plain-word copy."""
    for reason in headroom.REFUSALS:
        assert reason in headroom._NULL_COPY, f"missing copy for {reason}"
        copy = headroom._NULL_COPY[reason]
        for key in ("label_en", "label_zh"):
            assert key in copy and copy[key], f"missing {key} for {reason}"
        # Every refusal has either a single (en, zh) pair OR two variants
        # (with-coverage / no-coverage for no_terms_extracted).
        if reason == "no_terms_extracted":
            for key in ("en_no_coverage", "zh_no_coverage",
                        "en_with_coverage", "zh_with_coverage"):
                assert key in copy and copy[key], f"missing {key} for no_terms_extracted"
        else:
            for key in ("en", "zh"):
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


def test_no_headroom_word_in_null_copy_block9():
    """Spec B9 (BLOCKER 2 / MAJOR 4): the literal word "headroom"/"Headroom"
    must never appear in any _NULL_COPY value — the engine produces plain-word
    readings, not a study name."""
    for reason, copy in headroom._NULL_COPY.items():
        for k, v in copy.items():
            assert "headroom" not in v.lower(), (
                f"word 'headroom' leaked into refusal {reason}.{k}: {v!r}"
            )


def test_ceiling_and_basis_use_spec_verbatim_copy_block7():
    """Spec R4 + R1 — every payload carries the verbatim ceiling EN+ZH and
    the basis EN+ZH from the spec. Round-1 drifted both — round-2 pins the
    spec value. The basis must acknowledge "those usually allow adjustments
    we do not add back, so the true room can differ" verbatim."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["disclaimer_en"] == (
        "For your own research only — this is a reading of public filings, "
        "not advice or a trade call."
    )
    assert payload["disclaimer_zh"] == (
        "仅供自行研究 — 这是对公开披露文件的解读，不是建议，也不是交易指令。"
    )
    assert payload["basis_en"] == (
        "Measured with the numbers the company reported, not the "
        "agreement's own definitions — those usually allow adjustments we "
        "do not add back, so the true room can differ."
    )
    assert payload["basis_zh"] == (
        "按公司披露的数字计算，而非协议自身的定义 — 协议定义通常允许我们未"
        "加回的调整项，因此实际空间可能不同。"
    )


def test_ceiling_and_basis_present_in_every_payload():
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    for key in ("disclaimer_en", "disclaimer_zh", "basis_en", "basis_zh"):
        assert key in payload and payload[key]


def test_computed_payload_carries_period_end_basis():
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert payload["basis_period_end"] == DEFAULT_PERIOD_END


def test_receipt_block_cites_accession_form_filing_date_and_source_url():
    """Spec R1 — every term row's receipt carries accession, form,
    filing_date, source_manifest_id, observation_id, excerpt, source_url."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    term = payload["terms"][0]
    receipt = term["receipt"]
    assert receipt["accession"] == "0001564590-22-038930"
    assert receipt["form"] == "EX-10.1"
    assert receipt["filing_date"] == "2022-12-02"
    assert receipt["source_manifest_id"] == SYNTHETIC_MANIFEST_ID
    assert receipt["observation_id"]
    assert receipt["excerpt"]
    assert receipt["source_url"]


def test_next_step_emitted_in_computed_payload():
    """Spec R1 — every term row carries next_step. A step that starts
    strictly after period_end is emitted."""
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio", limit_raw=3.50,
        steps=[
            {"start_date": "2022-09-30", "end_date": "2023-06-29",
             "limit_raw": 3.50},
            {"start_date": "2023-06-30", "end_date": None,
             "limit_raw": 3.00},
        ],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    term = payload["terms"][0]
    assert term["in_force_step"]["start_date"] == "2022-09-30"
    assert term["next_step"]["start_date"] == "2023-06-30"


# ────────────────────────────────────────────────────────────────────────────
# i. Zero authority
# ────────────────────────────────────────────────────────────────────────────

def test_scored_flag_is_false():
    assert headroom.SCORED is False


def test_authority_ceiling_is_human_research_only():
    assert headroom.AUTHORITY_CEILING == "human_research_only"


def _payload_keys(node):
    """Yield every JSON-key path fragment (case-folded) inside ``node``.
    A substring match against repr(payload) would catch legitimate phrases
    like 'a trade call' or 'scored: false'; the structural check is the
    one the engine actually enforces."""
    out = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str):
                out.add(k.lower())
            out.update(_payload_keys(v))
    elif isinstance(node, list):
        for v in node:
            out.update(_payload_keys(v))
    return out


def test_no_authority_keys_leak_into_payload():
    """The full set of authority keys must never appear as JSON keys in a
    payload. Defense in depth alongside the page-level ceiling copy."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    keys = _payload_keys(payload)
    for bad in headroom._ZERO_AUTHORITY_KEYS:
        assert bad not in keys, f"authority key {bad!r} in payload"


def test_no_authority_keys_in_any_refusal_copy():
    for reason, copy in headroom._NULL_COPY.items():
        blob = repr(copy).lower()
        for bad in headroom._ZERO_AUTHORITY_KEYS:
            assert bad not in blob, (
                f"authority key {bad!r} in refusal copy for {reason}"
            )


def test_observations_passed_through_unchanged_block5():
    """Spec R4 — input observations are never mutated. Single-definition
    law: net debt and EBITDA come from the canonical helpers, never from
    a re-implementation that mutates input rows."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _stmt_row()
    row_snapshot = dict(row)
    obs_snapshot = {k: (dict(v) if isinstance(v, dict) else v)
                   for k, v in obs.items()}
    headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    assert row == row_snapshot
    assert obs == obs_snapshot


def test_issuers_never_ordered_by_room():
    """Spec R4 — the engine NEVER sorts issuers by room (room is per-term,
    not per-issuer; the page shows the one extracted issuer). A sort key
    like ``sorted(..., key=lambda x: x["room"])`` would violate the
    zero-authority charter; this test pins the non-sort."""
    obs_a = _direct_obs("maximum_total_net_leverage_ratio",
                        limit_raw=3.50, cik=CORSAIR_CIK,
                        correction_version=1,
                        observation_id="a")
    obs_b = _direct_obs("minimum_interest_coverage_ratio",
                        limit_raw=3.00, cik=CORSAIR_CIK,
                        correction_version=2,
                        observation_id="b")
    payload = headroom.compute_headroom(
        [obs_a, obs_b], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    # Term order matches the producer's correction_version desc order
    # (which is observation-identity order, NOT headroom order).
    assert [t["term_name"] for t in payload["terms"]] == [
        "minimum_interest_coverage_ratio",  # v2 first
        "maximum_total_net_leverage_ratio",  # v1 second
    ]


# ────────────────────────────────────────────────────────────────────────────
# j. Closed sets
# ────────────────────────────────────────────────────────────────────────────

def test_refusals_is_closed_set():
    assert tuple(sorted(headroom.REFUSALS)) == (
        "definition_differs", "identity_unresolved", "metric_absent",
        "no_terms_extracted", "ratio_undefined", "terms_ambiguous",
    )


@pytest.mark.skipif(
    not _covenant_terms_available,
    reason="covenant_terms not available (jsonschema missing on Python 3.14)"
)
def test_covenant_metric_map_is_subset_of_producer_term_names():
    """The map's keys must all appear in the producer's frozen
    COVENANT_TERM_NAMES tuple. Any drift here is a bug."""
    extras = set(headroom.COVENANT_METRIC_MAP) - set(covenant_terms.COVENANT_TERM_NAMES)
    assert not extras, f"COVENANT_METRIC_MAP keys not in producer set: {extras}"


def test_refusal_payload_only_uses_closed_refusals():
    """Defense in depth: every refusal copy key must be a member of REFUSALS."""
    for reason in headroom._NULL_COPY:
        assert reason in headroom.REFUSALS, (
            f"_NULL_COPY entry {reason!r} not in REFUSALS"
        )


def test_always_definition_differs_is_disjoint_from_metric_map():
    """B1 + B2 + B3/4 — a term cannot be both computable AND always refuse."""
    clash = set(headroom.COVENANT_METRIC_MAP) & set(headroom._ALWAYS_DEFINITION_DIFFERS)
    assert not clash, f"clash: {clash}"


@pytest.mark.skipif(
    not _covenant_terms_available,
    reason="covenant_terms not available (jsonschema missing on Python 3.14)"
)
def test_always_definition_differs_covers_all_definition_differs_terms():
    """Every term the producer recognises outside COVENANT_METRIC_MAP
    appears in _ALWAYS_DEFINITION_DIFFERS — i.e. the four definition_differs
    terms are exactly the complement of COVENANT_METRIC_MAP inside
    COVENANT_TERM_NAMES."""
    expected = (set(covenant_terms.COVENANT_TERM_NAMES)
                - set(headroom.COVENANT_METRIC_MAP))
    assert set(headroom._ALWAYS_DEFINITION_DIFFERS) == expected


# ────────────────────────────────────────────────────────────────────────────
# k. Never extrapolate
# ────────────────────────────────────────────────────────────────────────────

def test_no_extrapolation_keys_in_payload():
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    keys = _payload_keys(payload)
    for bad in headroom._NO_EXTRAPOLATION_KEYS:
        assert bad not in keys, f"extrapolation key {bad!r} in payload"


def test_no_ttm_or_annualized_substrings_anywhere():
    """Defense in depth: even if a label were to mention ttm/annualized by
    accident, the structural walk catches it. The engine never manufactures
    a TTM figure, so the tree is closed."""
    obs = _direct_obs("minimum_interest_coverage_ratio", limit_raw=3.00)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    keys = _payload_keys(payload)
    for bad in ("ttm", "annualized", "forecast", "projection", "run_rate"):
        assert bad not in keys, f"extrapolation key {bad!r} in payload tree"


def test_reported_period_end_matches_statement_row():
    """Spec R7(k) — the compared figure is the latest FY statement row;
    its period_end is printed and never extrapolated."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _stmt_row()
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    term = payload["terms"][0]
    assert term["reported"]["period_end"] == row["period_end"]
    payload_blob = repr(payload).lower()
    for bad in ("ttm_", "_ttm", "annualized_", "_annualized",
                "forecast_", "_forecast", "projection_", "_projection"):
        assert bad not in payload_blob


def test_no_field_named_ttm_annualized_forecast_in_payload():
    """Spec R7(k) — no ttm / annualized / forecast / run_rate / projection
    keys exist in any payload field, ever."""
    obs = _direct_obs("minimum_interest_coverage_ratio", limit_raw=3.00)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    keys = _payload_keys(payload)
    for bad in ("ttm", "annualized", "forecast", "projection",
                "run_rate", "runrate"):
        assert bad not in keys, (
            f"extrapolation key {bad!r} present in payload tree"
        )


# ────────────────────────────────────────────────────────────────────────────
# Single-definition law (B5)
# ────────────────────────────────────────────────────────────────────────────

def test_net_debt_uses_canonical_helper_block5():
    """Spec R2 + B5 — net debt comes from
    ``engine.stock_fundamentals._net_debt``, the same helper the leverage
    panel uses. The DOCSTRING of that helper literally says: "Shared by
    _leverage_ratios and _context_frame so the EV multiples and the
    leverage panel agree to the dollar." The covenant headroom MUST join
    that contract; the round-1 engine defined its own _derive_inputs that
    silently disagreed on skip-not-default-zero semantics.

    This test pins the spec value: cash = 0 (treated as a number, not
    None) gives net_debt = 250 + 10 − 0 = 260M; the round-1 helper gave
    a different answer when one input was reported as None."""
    obs = _direct_obs("maximum_total_net_leverage_ratio", limit_raw=3.50)
    row = _stmt_row(cash=0.0)
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: row}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    term = payload["terms"][0]
    # net_debt = 250 + 10 − 0 = 260. EBITDA = 60 + 20 = 80. Ratio = 3.25x.
    assert term["reported"]["value"] == pytest.approx(3.25, rel=1e-6)
    assert term["room_turns"] == pytest.approx(0.25, rel=1e-6)


# ────────────────────────────────────────────────────────────────────────────
# Public surface
# ────────────────────────────────────────────────────────────────────────────

def test_compute_headroom_is_callable_with_only_observations():
    """The minimum call surface is observations + maps. Optional kwargs
    (health, coverage, generated_at, cik_by_source_manifest_id) must have
    safe defaults — never required."""
    payload = headroom.compute_headroom([], {}, {})
    assert payload["state"] == "refused"
    assert payload["refusal"] == "no_terms_extracted"


# ────────────────────────────────────────────────────────────────────────────
# Committed evidence payload rendering (BLOCKERS 1+2)
# ────────────────────────────────────────────────────────────────────────────

def test_committed_computed_payload_renders_every_term_semantics():
    """The committed computed payload renders each term's own plain sentence.

    This is RED on the previous template: it rendered only the first computed
    term, so the leverage ceiling sentence and its room value were absent.
    """
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[1]
    payload = json.loads(
        (
            root
            / "mockups/evidence/b-f09-13-covenant-headroom/payloads/computed.json"
        ).read_text(encoding="utf-8")
    )
    html, _ = _render_covenant_panel(covenant_headroom=payload)

    assert "requires at least" in html
    assert "3.0" in html
    assert "5.3" in html
    assert "2.3" in html
    assert "allows up to" in html
    assert "3.5" in html
    assert "1.2" in html


def test_committed_computed_payload_renders_zh_term_semantics():
    """The committed payload keeps every Chinese glance sentence selectable."""
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[1]
    payload = json.loads(
        (
            root
            / "mockups/evidence/b-f09-13-covenant-headroom/payloads/computed.json"
        ).read_text(encoding="utf-8")
    )
    html, _ = _render_covenant_panel(covenant_headroom=payload)

    assert "信贷协议要求收益与利息之比至少为" in html
    assert "信贷协议允许最高" in html


def test_committed_computed_payload_below_floor_copy_has_no_room_claim():
    """An over-limit ceiling reads as over the limit, never as room left.

    This is RED on the previous template because its only negative-room path
    still emitted the same "of room" sentence.
    """
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[1]
    payload = json.loads(
        (
            root
            / "mockups/evidence/b-f09-13-covenant-headroom/payloads/computed.json"
        ).read_text(encoding="utf-8")
    )
    minimum = next(
        term
        for term in payload["terms"]
        if term["term_name"] == "minimum_interest_coverage_ratio"
    )
    minimum["limit_raw"] = 3.0
    minimum["reported"]["value"] = 2.375
    minimum["room_turns"] = -0.625
    maximum = next(
        term
        for term in payload["terms"]
        if term["term_name"] == "maximum_total_net_leverage_ratio"
    )
    maximum["state"] = "definition_differs"
    maximum.pop("reported", None)
    maximum.pop("room_turns", None)

    html, _ = _render_covenant_panel(covenant_headroom=payload)

    assert "falls below the floor by" in html
    assert "0.625" in html
    assert "of room" not in html
    assert "低于下限" in html


def test_committed_computed_payload_over_limit_copy_has_no_room_claim():
    """An over-limit ceiling reads as over the limit, never as room left.

    RED against dcfa3454 popped the floor term's ``room_turns`` while the old
    template still selected it with ``selectattr('room_turns')``; Jinja raised
    ``UndefinedError`` before either copy assertion ran.
    """
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[1]
    payload = json.loads(
        (
            root
            / "mockups/evidence/b-f09-13-covenant-headroom/payloads/computed.json"
        ).read_text(encoding="utf-8")
    )
    leverage = next(
        term
        for term in payload["terms"]
        if term["term_name"] == "maximum_total_net_leverage_ratio"
    )
    leverage["limit_raw"] = 3.5
    leverage["reported"]["value"] = 4.125
    leverage["room_turns"] = -0.625
    minimum = next(
        term
        for term in payload["terms"]
        if term["term_name"] == "minimum_interest_coverage_ratio"
    )
    minimum["state"] = "definition_differs"
    minimum.pop("reported", None)
    minimum.pop("room_turns", None)

    html, _ = _render_covenant_panel(covenant_headroom=payload)

    assert "exceeds the limit by" in html
    assert "0.625" in html
    assert "of room" not in html
    assert "超出限额" in html


# ────────────────────────────────────────────────────────────────────────────
# BLOCKER 2: Glance sentence + MAJOR 4: no "headroom" in template output
# ────────────────────────────────────────────────────────────────────────────

def _render_covenant_panel(**ch_headroom_kwargs) -> str:
    """Render the covenant headroom section of capital_structure.html.j2
    in isolation, returning the rendered HTML fragment.

    Also returns a ``text_only`` stripped version (HTML tags removed) for
    assertions about visible user-facing copy."""
    import re
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, StrictUndefined

    root = Path(__file__).resolve().parents[1]
    templates = root / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates)),
        autoescape=True,
        undefined=StrictUndefined,
    )
    html = env.get_template("capital_structure.html.j2").render(
        active_section="research",
        active_page="capital_structure",
        **ch_headroom_kwargs,
    )
    # Strip HTML tags + CSS classes/ids to get visible text only
    text_only = re.sub(r"<[^>]+>", " ", html)
    text_only = re.sub(r'\s+', " ", text_only).strip()
    return html, text_only


def test_glance_sentence_uses_minimum_floor_copy_for_minimum_term():
    """BLOCKER 2 RED-first: the glance sentence for a minimum_* term must read
    as a floor ("requires at least X; shows Y — Z of room above the floor"),
    not a ceiling. The old hardcoded copy used "net debt to earnings; the last
    annual report shows" regardless of term kind."""
    import engine.covenant_headroom as headroom

    # minimum_interest_coverage_ratio: EBITDA/interest = 5.33x vs 3.00x floor
    obs = _direct_obs(
        "minimum_interest_coverage_ratio",
        limit_raw=3.00,
        steps=[{"start_date": "2022-09-30", "end_date": None, "limit_raw": 3.00}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    html, text_only = _render_covenant_panel(covenant_headroom=payload)
    # Floor sentence: "requires at least"
    assert "requires at least" in html, (
        "glance copy does not read as a floor for minimum_* term"
    )
    # "of room above the floor" not "of room"
    assert "above the floor" in html
    # Does NOT say "net debt to earnings"
    assert "net debt to earnings" not in html


def test_glance_sentence_uses_maximum_ceiling_copy_for_maximum_term():
    """BLOCKER 2 GREEN: for a maximum_* term the glance copy reads as a
    ceiling ("allows up to X; shows Y — Z of room")."""
    import engine.covenant_headroom as headroom

    # maximum_total_net_leverage_ratio: net_debt/EBITDA = 2.25x vs 3.50x limit
    obs = _direct_obs(
        "maximum_total_net_leverage_ratio",
        limit_raw=3.50,
        steps=[{"start_date": "2022-09-30", "end_date": None, "limit_raw": 3.50}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    html, text_only = _render_covenant_panel(covenant_headroom=payload)
    # Ceiling sentence: "allows up to"
    assert "allows up to" in html
    # "of room" (not "above the floor")
    assert "of room" in html
    assert "above the floor" not in html


def test_grid_no_headroom_word_in_computed_html():
    """MAJOR 4: all rendered user-facing text and non-class/id attributes
    must stay free of the internal word "headroom"."""
    import engine.covenant_headroom as headroom

    obs = _direct_obs(
        "maximum_total_net_leverage_ratio",
        limit_raw=3.50,
        steps=[{"start_date": "2022-09-30", "end_date": None, "limit_raw": 3.50}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    html, _ = _render_covenant_panel(covenant_headroom=payload)
    cleaned = re.sub(r'(?:class|id)="[^"]*"', "", html, flags=re.IGNORECASE)
    assert "headroom" not in cleaned.lower(), (
        "word 'headroom' found outside class/id attribute values"
    )


def test_grid_no_headroom_word_in_null_html():
    """MAJOR 4: same assertion for the refusal/null state."""
    import engine.covenant_headroom as headroom

    payload = headroom.compute_headroom(
        [], {}, {},
        coverage={"covered_manifests": 0, "eligible_exhibits": 2450,
                  "issuers_covered": 0, "state": "uncovered"},
    )
    html, _ = _render_covenant_panel(covenant_headroom=payload)
    cleaned = re.sub(r'(?:class|id)="[^"]*"', "", html, flags=re.IGNORECASE)
    assert "headroom" not in cleaned.lower(), (
        "word 'headroom' found outside class/id attribute values"
    )


def test_refusal_rows_use_full_plain_sentences_in_both_languages():
    """Every unavailable-state label is a complete plain sentence in EN and ZH."""
    import engine.covenant_headroom as headroom

    expected = {
        "identity_unresolved": (
            "We could not identify one issuer for these covenant terms.",
            "我们无法为这些契约条款确定唯一发行人。",
        ),
        "metric_absent": (
            "The financial inputs needed for this covenant term are not available.",
            "本契约条款所需的财务输入目前不可用。",
        ),
        "ratio_undefined": (
            "The reported figures do not allow this covenant ratio to be calculated.",
            "披露数字不足以计算该契约比率。",
        ),
        "definition_differs": (
            "The agreement defines this covenant differently from the reported figures.",
            "协议对该契约的定义与披露数字不同。",
        ),
        "terms_ambiguous": (
            "The agreement language leaves this covenant term unclear.",
            "协议语言使该契约条款的含义不明确。",
        ),
    }
    for reason, (label_en, label_zh) in expected.items():
        assert headroom._NULL_COPY[reason]["label_en"] == label_en
        assert headroom._NULL_COPY[reason]["label_zh"] == label_zh

    # definition_differs: maximum_secured_net_leverage_ratio always refuses
    obs = _direct_obs(
        "maximum_secured_net_leverage_ratio",
        limit_raw=2.50,
        steps=[{"start_date": "2022-09-30", "end_date": None, "limit_raw": 2.50}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    html, _ = _render_covenant_panel(covenant_headroom=payload)
    assert "The agreement defines this covenant differently" in html
    # The raw term name with underscores must NOT appear as a visible label
    assert "maximum_secured_net_leverage_ratio" not in html
    assert "maximum secured net leverage ratio" not in html


def test_next_step_none_shows_plain_message():
    """MAJOR 1: when next_step is absent, the grid cell shows a plain
    "No next step recorded." / "尚无记录的下一阶跃。" message, never a blank
    or a machine identifier."""
    import engine.covenant_headroom as headroom

    obs = _direct_obs(
        "maximum_total_net_leverage_ratio",
        limit_raw=3.50,
        steps=[{"start_date": "2022-09-30", "end_date": None, "limit_raw": 3.50}],
    )
    payload = headroom.compute_headroom(
        [obs], {CORSAIR_CIK: _stmt_row()}, {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    html, text_only = _render_covenant_panel(covenant_headroom=payload)
    # next_step is absent in this payload (no future step)
    assert payload["terms"][0].get("next_step") is None
    assert "No next step recorded" in html or "尚无记录的下一阶跃" in html


def test_glance_renders_both_terms_with_correct_semantic_labels():
    """BLOCKER 2: with BOTH minimum_ and maximum_ terms in the payload,
    the glance sentence reads as a floor for interest-coverage (minimum_*)
    and a ceiling for leverage (maximum_*), with correct numeric values.
    The two separate one-term tests cannot catch a mixed-payload mistake
    where the template always picks the first term regardless of kind."""
    obs_min = _direct_obs(
        "minimum_interest_coverage_ratio",
        limit_raw=3.00,
        steps=[{"start_date": "2022-09-30", "end_date": None, "limit_raw": 3.00}],
    )
    obs_max = _direct_obs(
        "maximum_total_net_leverage_ratio",
        limit_raw=3.50,
        steps=[{"start_date": "2022-09-30", "end_date": None, "limit_raw": 3.50}],
    )
    # payload terms order: min first, max second (matches computed.json)
    payload = headroom.compute_headroom(
        [obs_min, obs_max],
        {CORSAIR_CIK: _stmt_row()},
        {CORSAIR_CIK: "CRSR"},
        cik_by_source_manifest_id=_cik_by_source_manifest_id(),
    )
    html, text_only = _render_covenant_panel(covenant_headroom=payload)
    # Interest coverage (minimum_): floor sentence with correct room (5.3 - 3.0 ≈ 2.3)
    assert "requires at least" in html, (
        "minimum_* term must use floor sentence ('requires at least')"
    )
    assert "above the floor" in html
    assert "allows up to" in html
    # Numeric values for interest coverage: limit=3.0, reported≈5.3, room≈2.3
    assert "3.0" in html and "5.3" in html, (
        f"interest-coverage values (3.0 / 5.3) must appear in glance; got: {text_only[:200]}"
    )
    # The net-debt-to-earnings hardcoded clause must NOT appear
    assert "net debt to earnings" in html
    # Ensure the leverage (maximum_) term does not claim "above the floor"
    # (it would if the template copied the minimum template branch)
