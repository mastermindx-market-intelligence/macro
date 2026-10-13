"""Publish one composer dossier onto the company-first fragment.

The test calls the composer, then the publisher. The publisher module does
not import the composer or the curation contract. Identifiers are synthetic.
No network.
"""
from __future__ import annotations

import importlib
import json

import pytest

import tests.test_market_ontology_technology_dossier_page as pages
import tests.test_market_ontology_technology_economic_change as econ
from engine.market_ontology.technology_published_signal import (
    TechnologyPublishedSignalRefusal,
    publish_technology_dossier,
)

_ESTABLISHES = (
    "Synthetic attributed statement: product workload role for compute acceleration."
)


def test_conformant_composer_dossier_publishes_one_workload_role_row() -> None:
    module = importlib.import_module("engine.theme_graph.curation_assertion")
    payload = json.loads(econ.CONFORMANT_ASSERTION_PATH.read_text(encoding="utf-8"))
    validated = module.validate_assertion(payload)
    dossier = econ._compose(business_assertions=[validated])
    html = publish_technology_dossier(dossier)
    assert "product_workload_role" in html
    assert _ESTABLISHES in html
    focus = next(
        entity
        for entity in dossier["identity"]["entities"]
        if entity["entity_id"] == econ.COMPANY
    )
    assert focus["display_ticker"] == "SYNTH.A"
    assert focus["display_ticker"] in html
    assert "enrichment_out_of_first_unit_scope" in html
    assert "shared_contract_unavailable" not in html


def test_stand_in_default_dossier_is_not_published() -> None:
    dossier = econ._compose()
    assert dossier["business"]["rows"] == []
    assert dossier["coverage"]["counts"]["invalid_assertions"] == 3
    with pytest.raises(TechnologyPublishedSignalRefusal) as excinfo:
        publish_technology_dossier(dossier)
    assert excinfo.value.code == "no_published_row"
    assert str(excinfo.value) == "no_published_row"


def test_hand_built_row_without_curation_revision_is_refused() -> None:
    """The dossier dict from the fragment test's hand-built row (no stamp)."""
    dossier = pages._dossier(
        display_ticker="ACME",
        binding_state="bound",
        company_first=pages._COMPANY_FIRST,
        business={
            "rows": [
                {
                    "row_id": "tecrow_0123456789ab",
                    "predicate": "product_workload_role",
                    "statement": "synthetic workload role",
                }
            ],
            "cards": [],
            "relationships": [],
            "ordering": "identifier_lexicographic",
        },
        enrichment_reason="enrichment_out_of_first_unit_scope",
    )
    row = dossier["business"]["rows"][0]
    assert row["statement"] == "synthetic workload role"
    assert "curation_revision" not in row
    with pytest.raises(TechnologyPublishedSignalRefusal) as excinfo:
        publish_technology_dossier(dossier)
    assert excinfo.value.code == "no_published_row"
