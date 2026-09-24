"""Seat-authored per-case truth table for the T04a composition (ruling R-MIN-31). Frozen RED before
the round-3 repair lane; the lane may not edit this file.

R-MIN-31: (1) withdrawal keys on the case's omissions — a withdrawn case composes no native block and
no expectation row and carries every mapped omission code; a usable case composes exactly its
casebook signed block(s); (2) slice-definitional limitations are minted for the SLICE, on every case
of that slice, from the domain file: the rare-earth definition's own `stream_threshold_unknown` and
`industry_total_unknown` plus `definition_unqualified:management_estimate_vs_actual` for its null
comparison legs; the copper definition mints none; (3) an expectation row exists ONLY when the bundle
carries a measured `management_estimate_vs_actual` financial packet — the synthetic casebook carries
none, so a usable copper case withholds the channel with `omitted:expectations` and never fabricates
a leg; (4) `limitations` is sorted and duplicate-free; (5) `missing_derivation` is never minted on a
usable case.
"""
import pytest

from engine.market_ontology import mining_theme_research as composition
from tests.mining_casebook import CASE_NAMES, synthetic_case

RE_DEF = {"stream_threshold_unknown", "industry_total_unknown", "definition_unqualified:management_estimate_vs_actual"}

# case -> (research_usable, native block count, expectation row count, exact limitation set)
TRUTH = {
    "copper_complete": (True, 1, 0, {"omitted:expectations"}),
    "signed_loss": (True, 1, 0, {"omitted:expectations"}),
    "missing_basis": (False, 0, 0, {"missing_basis"}),
    "missing_issuer": (False, 0, 0, {"missing_issuer"}),
    "source_only": (False, 0, 0, {"source_only"}),
    "changed_source": (False, 0, 0, {"changed_source"}),
    "denied_source": (False, 0, 0, {"denied_source"}),
    "rare_earth_complete": (True, 1, 0, RE_DEF),
    "missing_stream_threshold": (False, 0, 0, RE_DEF),
    "page_generation_change": (False, 0, 0, RE_DEF | {"page_generation_change"}),
    "same_horizon_revision": (False, 0, 0, RE_DEF | {"missing_derivation"}),
}


def test_truth_table_covers_every_case():
    assert set(TRUTH) == set(CASE_NAMES)


@pytest.mark.parametrize("name, row", sorted(TRUTH.items()))
def test_composition_matches_the_frozen_truth_table(name, row):
    usable, n_blocks, n_rows, limitations = row
    case = synthetic_case(name)
    assert (case.bundle.omissions == ()) is usable
    result = composition.compose_mining_research(case.query, case.bundle)
    assert len(result["economics"]["native_blocks"]) == n_blocks, result["economics"]["native_blocks"]
    assert len(result["expectations"]) == n_rows, result["expectations"]
    assert result["limitations"] == sorted(limitations), result["limitations"]
    assert len(set(result["limitations"])) == len(result["limitations"])
    if name == "signed_loss":
        block = result["economics"]["native_blocks"][0]
        assert block["value"] < 0
    for block in result["economics"]["native_blocks"]:
        assert block["stable_subject_id"] != "subject:unknown"
