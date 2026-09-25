"""Correction lineage for Nuclear evidence (R-ENE-29).

The walk reads only records the same query may serve. A predecessor it may not
serve is named by the pointer the last served record carries itself, and the
walk stops there: nothing is ever read out of a withheld record.
"""

from __future__ import annotations

import pytest

from engine.market_ontology import nuclear_theme_research as nuclear
from engine.theme_graph.curation_assertion import source_ref_for
from tests.nuclear_research_helpers import N04, nuclear_bundle, nuclear_query, variant

QUERY = nuclear_query("nuclear_components", "economics")
REPLAY = nuclear_query(
    "nuclear_components", "economics", time_mode="system_replay",
    source_cutoff="2026-12-31T00:00:00Z", recorded_cutoff="2026-12-31")
REJECTED = {"disposition": "rejected", "reviewer": "synthetic-energy-test",
            "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": None}
LATER = "2027-06-01T00:00:00Z"

WITHHELD_PREDECESSOR = {
    "rejected": ({"review": REJECTED}, {}, QUERY),
    "rejected_chain": ({"review": REJECTED}, {"review": REJECTED}, QUERY),
    "other_slice": ({"scope": {"technology_facet": "fuel_cycle"},
                     "subject": {"company_node_id": "co:us:CCJ",
                                 "source_business_label": "Cameco"}}, {}, QUERY),
    "rights_refused": ({"source": {
        "source_uri": "https://www.nrc.gov/synthetic/lineage"}}, {}, QUERY),
    "outside_cohort": ({"subject": {"company_node_id": "co:us:SMR",
                                    "source_business_label": "NuScale Power"}},
                       {}, QUERY),
    "not_yet_recorded": ({"source": {"observed_at": LATER, "retained_at": LATER}},
                         {}, REPLAY),
}


def corrects(base, case, predecessor, **changes):
    return variant(base, case, correction={
        "predecessor_revision": predecessor["curation_revision"],
        "reason": "Synthetic correction."}, **changes)


def lineage(served, *others, query=QUERY):
    evidence = nuclear.select_authorized_evidence(
        query, nuclear_bundle(served, *others), source_ref_for(served))
    return evidence["lineage"]


def refs(*records):
    return [source_ref_for(record) for record in records]


def test_an_all_accepted_chain_is_walked_to_its_root():
    root = variant("N05", "L1C")
    middle = corrects("N05", "L1B", root)
    served = corrects("N05", "L1A", middle)
    assert lineage(served, middle, root) == refs(middle, root)


@pytest.mark.parametrize("case", sorted(WITHHELD_PREDECESSOR))
def test_a_predecessor_this_query_cannot_serve_ends_the_walk(case):
    middle_changes, root_changes, query = WITHHELD_PREDECESSOR[case]
    root = variant("N05", f"L2{case}C", **root_changes)
    middle = corrects("N05", f"L2{case}B", root, **middle_changes)
    served = corrects("N05", f"L2{case}A", middle)
    assert lineage(served, middle, root, query=query) == refs(middle)


def test_a_malformed_row_is_never_read_as_a_predecessor():
    root = variant("N05", "L3C")
    middle = corrects("N05", "L3B", root)
    served = corrects("N05", "L3A", middle)
    malformed = dict(middle, observation=None, correction={
        "predecessor_revision": "gmirca_" + "f" * 32, "reason": "Synthetic correction."})
    assert lineage(served, root, malformed) == refs(middle)


def test_a_collapsed_copy_is_walked_because_the_selector_serves_it():
    other = {"source": {"publisher": "Synthetic Grid Filings"}}
    root = variant("N05", "L4C", **other)
    syndicated = corrects("X05", "L4X", root)
    served = corrects("N05", "L4A", syndicated, **other)
    payload = nuclear.compose_nuclear_research(
        QUERY, nuclear_bundle(served, syndicated, root, N04))
    assert "syndicated_collapsed" in payload["limitations"]
    assert lineage(served, syndicated, root, N04) == refs(syndicated, root)
