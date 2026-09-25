"""Synthetic Nuclear research fixtures built through the shared assertion API.

Every payload and number in this module is synthetic. No value is copied from
NuScale, Oklo, BWX Technologies, Cameco or Centrus.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from engine.market_ontology.nuclear_theme_research import OwnerBundle, ResearchQuery
from engine.theme_graph.curation_assertion import encode_assertion

COMPANIES = {
    "NuScale": "co:us:SMR",
    "Oklo": "co:us:OKLO",
    "BWX Technologies": "co:us:BWXT",
    "Cameco": "co:us:CCJ",
    "Centrus": "co:us:LEU",
}


def _assertion(
    *,
    case: str,
    company: str,
    facet: str,
    predicate: str,
    mode: str,
    establishes: list[str],
    does_not_establish: list[str],
    observation: dict[str, Any] | None = None,
    product: str | None = None,
    configuration: str | None = None,
    object_product: str | None = None,
    period: str | None = None,
    valid_to: str | None = None,
    valid_from: str | None = None,
    retained_equal_published: bool = False,
    publisher: str | None = None,
    source_dependence: str | None = None,
    business: str | None = None,
    application: str | None = None,
    source_uri: str | None = None,
    predecessor: str | None = None,
) -> dict[str, Any]:
    value = {
        "schema": "theme_graph.curation_assertion.v1",
        "curation_revision": None,
        "review": {
            "disposition": "accepted", "reviewed_at": "2026-09-20T00:00:00Z",
            "reviewer": "synthetic-energy-test", "review_due_at": None,
        },
        "source": {
            "publisher": publisher or "Synthetic Energy Filings",
            "source_uri": source_uri or (
                f"https://www.sec.gov/Archives/edgar/data/synthetic/{case}.htm"
            ),
            "locator": f"synthetic-{case}",
            "published_at": "2026-09-19", "published_at_grain": "date",
            "observed_at": "2026-09-20T00:00:00Z",
            "retained_at": "2026-09-19T00:00:00Z" if retained_equal_published else "2026-09-20T00:00:00Z",
            "retention_ref": f"synthetic://{case}", "native_digest": None,
        },
        "subject": {
            "company_node_id": COMPANIES[company],
            "source_business_label": business if business is not None else company,
            "source_product_label": product,
            "source_platform_label": None,
            "configuration": configuration,
        },
        "object": {
            "source_product_label": object_product or product or case,
            "configuration": configuration,
        },
        "predicate": predicate,
        "statement_mode": mode,
        "scope": {
            "canonical_theme_id": "theme:nuclear_power", "application": application,
            "technology_facet": facet, "region": None, "period": period,
            "denominator": None,
        },
        "observation": observation or {
            "value": None, "value_high": None, "unit": None,
            "quantity_basis": "absolute", "gross_net_basis": None,
            "stock_flow": None, "estimate_status": "reported",
            "precision": "integer",
        },
        "temporal": {
            "business_valid_from": valid_from or "2026-09-19",
            "business_valid_to": valid_to,
        },
        "limitations": {
            "establishes": establishes,
            "does_not_establish": does_not_establish,
            "coverage": f"Synthetic coverage statement for {case}.",
            "source_dependence": source_dependence or "Synthetic source dependence.",
            "expiry_trigger": valid_to,
        },
        "correction": {"predecessor_revision": predecessor, "reason": (
            "Synthetic correction." if predecessor else None)},
        "authority": {
            "can_rank": False, "can_gate": False, "can_size": False,
            "can_originate": False, "can_open_entry": False,
        },
    }
    return json.loads(encode_assertion(value))


def _observed(value: float, unit: str, basis: str, *,
              flow: str | None = None) -> dict[str, Any]:
    return {
        "value": value, "value_high": None, "unit": unit,
        "quantity_basis": basis, "gross_net_basis": None,
        "stock_flow": flow, "estimate_status": "reported",
        "precision": "decimal",
    }


N01 = _assertion(
    case="N01", company="NuScale", facet="reactor_technology",
    predicate="PRODUCT_CAPABILITY", mode="CATALOG_DESCRIPTION",
    product="Synthetic seventy-seven module", configuration="Synthetic module block",
    observation=_observed(77, "MWe", "per_unit"),
    establishes=["standard design approval of the module rating by the regulator"],
    does_not_establish=["current operation", "site operating licence",
                        "definitive customer agreement"],
)
N02 = _assertion(
    case="N02", company="NuScale", facet="reactor_technology",
    predicate="ANNOUNCED_DEVELOPMENT_AGREEMENT", mode="ANNOUNCED_ARRANGEMENT",
    product="Synthetic energy recovery module",
    object_product="Synthetic commercialization partner",
    establishes=["a synthetic commercialization arrangement has been announced"],
    does_not_establish=["definitive agreement", "funded revenue", "delivered units"],
)
N03 = _assertion(
    case="N03", company="Oklo", facet="reactor_technology",
    predicate="DEPLOYMENT_TARGET", mode="FORWARD_TARGET",
    product="Synthetic powerhouse", valid_to="2027-12-31",
    observation=_observed(6, "units", "absolute", flow=None),
    establishes=["a separate test reactor reached first criticality (technical milestone)"],
    does_not_establish=["current operation", "commercial grid generation",
                        "operating licence"],
)
N03B = _assertion(
    case="N03B", company="Oklo", facet="reactor_technology",
    predicate="DEPLOYMENT_TARGET", mode="FORWARD_TARGET",
    product="Synthetic powerhouse", valid_to="2026-01-31",
    observation=_observed(6, "units", "absolute", flow=None),
    establishes=["a separate test reactor reached first criticality (technical milestone)"],
    does_not_establish=["current operation", "commercial grid generation",
                        "operating licence"],
)
N04 = _assertion(
    case="N04", company="BWX Technologies", facet="nuclear_components",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic government operations", period="2025Q4",
    observation=_observed(100, "USD million", "per_period", flow="flow"),
    establishes=["synthetic government-operations revenue was reported"],
    does_not_establish=["consolidated company revenue"],
)
N05 = _assertion(
    case="N05", company="BWX Technologies", facet="nuclear_components",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic commercial operations", period="2025Q4",
    observation=_observed(200, "USD million", "per_period", flow="flow"),
    establishes=["synthetic commercial-operations revenue was reported"],
    does_not_establish=["consolidated company revenue"],
)
N06 = _assertion(
    case="N06", company="BWX Technologies", facet="nuclear_components",
    predicate="OWNERSHIP_EVENT", mode="REPORTED_FACT",
    product="Synthetic components business", object_product="Synthetic acquired line",
    establishes=["a synthetic acquisition closed after quarter end"],
    does_not_establish=["revenue in the reported quarter", "organic growth"],
)
N07 = _assertion(
    case="N07", company="Cameco", facet="fuel_cycle",
    predicate="REPORTED_OPERATING_MEASURE", mode="REPORTED_FACT",
    product="Synthetic fuel services", period="2025Q4",
    observation=_observed(50, "CAD/kgU", "per_unit"),
    establishes=["a synthetic realized fuel-services price was reported"],
    does_not_establish=["consolidated revenue"],
)
N08 = _assertion(
    case="N08", company="Cameco", facet="fuel_cycle",
    predicate="REPORTED_OPERATING_MEASURE", mode="REPORTED_FACT",
    product="Synthetic fuel services", period="2025Q4",
    observation=_observed(40, "CAD/kgU", "per_unit"),
    establishes=["a synthetic unit cost including depreciation was reported"],
    does_not_establish=["the price-minus-cost spread is EBITDA per unit"],
)
N09 = _assertion(
    case="N09", company="Cameco", facet="fuel_cycle",
    predicate="OWNERSHIP_EVENT", mode="REPORTED_FACT",
    product="Synthetic investee interest", object_product="Synthetic Westinghouse fixture",
    establishes=["a synthetic equity interest in an equity-method investee was reported"],
    does_not_establish=["consolidated revenue"],
)
N10 = _assertion(
    case="N10", company="Centrus", facet="fuel_cycle",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic contract backlog", period="2025Q4",
    observation=_observed(3, "USD billion", "absolute", flow="stock"),
    establishes=["a synthetic total backlog was reported"],
    does_not_establish=["funded revenue"],
)
N11 = _assertion(
    case="N11", company="Centrus", facet="fuel_cycle",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic contingent backlog", period="2025Q4",
    observation=_observed(1, "USD billion", "absolute", flow="stock"),
    establishes=["a synthetic contingent backlog contained within the total was reported"],
    does_not_establish=["funded revenue", "definitive agreement",
                        "additive with the total"],
)
N12 = _assertion(
    case="N12", company="Centrus", facet="fuel_cycle",
    predicate="REPORTED_DEPLOYMENT", mode="REPORTED_FACT",
    product="Synthetic enriched material", period="2025Q4",
    observation=_observed(5, "kg", "per_period", flow="flow"),
    establishes=["synthetic material was delivered under a government contract"],
    does_not_establish=["funded revenue"],
)

N13 = _assertion(
    case="N13", company="Cameco", facet="fuel_cycle",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic consolidated operations", period="2025Q4",
    observation=_observed(100, "USD million", "per_period", flow="flow"),
    establishes=["synthetic consolidated revenue was reported"],
    does_not_establish=["equity-method investee revenue"],
)

N14 = _assertion(
    case="N14", company="Cameco", facet="fuel_cycle",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic equity-method investee", period="2025Q4",
    observation=_observed(50, "USD million", "per_period", flow="flow"),
    establishes=["the synthetic investee share is equity-accounted"],
    does_not_establish=["consolidated revenue", "netting against consolidated revenue"],
)

N03C = _assertion(
    case="N03C", company="Oklo", facet="reactor_technology",
    predicate="DEPLOYMENT_TARGET", mode="FORWARD_TARGET",
    product="Synthetic powerhouse", valid_to="2026-01-31",
    observation=_observed(5, "units", "absolute"),
    establishes=["a synthetic earlier target was met"],
    does_not_establish=["current operation"], retained_equal_published=True,
)

N03D = _assertion(
    case="N03D", company="Oklo", facet="reactor_technology",
    predicate="DEPLOYMENT_TARGET", mode="FORWARD_TARGET",
    product="Synthetic powerhouse", valid_to="2027-12-31",
    observation=_observed(4, "units", "absolute"),
    establishes=["a synthetic later target is open"],
    does_not_establish=["current operation"], retained_equal_published=True,
)
X01 = _assertion(
    case="X01", company="BWX Technologies", facet="nuclear_components",
    predicate="OWNERSHIP_EVENT", mode="ATTRIBUTED_INTERPRETATION",
    product="Synthetic interpretation", object_product="Synthetic demand view",
    establishes=["a synthetic interpretation was attributed"],
    does_not_establish=["current operation", "revenue"],
)
X02 = _assertion(
    case="X02", company="BWX Technologies", facet="nuclear_components",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic regulator-cited work", period="2025Q4",
    observation=_observed(9, "USD million", "per_period", flow="flow"),
    source_uri="https://www.nrc.gov/synthetic/X02.htm",
    establishes=["a synthetic regulator-cited value exists"],
    does_not_establish=["emission rights"],
)
X02B = _assertion(
    case="X02B", company="BWX Technologies", facet="nuclear_components",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic regulator-cited work", period="2025Q4",
    observation=_observed(10, "USD million", "per_period", flow="flow"),
    source_uri="https://www.nrc.gov/synthetic/X02B.htm",
    establishes=["a second synthetic regulator-cited value exists"],
    does_not_establish=["emission rights"],
)
X03 = _assertion(
    case="X03", company="BWX Technologies", facet="nuclear_components",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic government operations", period="2025Q4",
    observation=_observed(101, "USD million", "per_period", flow="flow"),
    predecessor=N04["curation_revision"],
    establishes=["the synthetic government-operations revenue was corrected"],
    does_not_establish=["consolidated company revenue"],
)
X04 = _assertion(
    case="X04", company="Cameco", facet="fuel_cycle",
    predicate="REPORTED_OPERATING_MEASURE", mode="REPORTED_FACT",
    product="Synthetic misfaceted fuel service", period="2025Q4",
    observation=_observed(44, "CAD/kgU", "per_unit"),
    establishes=["a mis-faceted synthetic value exists"],
    does_not_establish=["primary slice membership"],
)
X04B = _assertion(
    case="X04B", company="Centrus", facet="reactor_technology",
    predicate="REPORTED_OPERATING_MEASURE", mode="REPORTED_FACT",
    product="Synthetic fuel service", period="2025Q4",
    observation=_observed(45, "CAD/kgU", "per_unit"),
    establishes=["a second synthetic fuel-service value exists"],
    does_not_establish=["primary slice membership"],
)
X05 = _assertion(
    case="X05", company="BWX Technologies", facet="nuclear_components",
    predicate="REPORTED_FINANCIAL_MEASURE", mode="REPORTED_FACT",
    product="Synthetic syndicated work", period="2025Q4",
    observation=_observed(100, "USD million", "per_period", flow="flow"),
    publisher="Synthetic Wire",
    source_dependence="syndicated_copy_of:Synthetic Energy Filings",
    establishes=["a synthetic syndicated copy exists"],
    does_not_establish=["independent corroboration"],
)
X06 = _assertion(
    case="X06", company="NuScale", facet="reactor_technology",
    predicate="PRODUCT_CAPABILITY", mode="CATALOG_DESCRIPTION",
    product="Synthetic smaller module", configuration="Synthetic A block",
    observation=_observed(10, "MWe", "per_unit"),
    establishes=["a synthetic smaller capability was catalogued"],
    does_not_establish=["deployment"],
)
X07 = _assertion(
    case="X07", company="Oklo", facet="reactor_technology",
    predicate="PRODUCT_CAPABILITY", mode="CATALOG_DESCRIPTION",
    product="Synthetic larger module", configuration="Synthetic Z block",
    observation=_observed(200, "MWe", "per_unit"),
    establishes=["a synthetic larger capability was catalogued"],
    does_not_establish=["deployment"],
)
X08 = _assertion(
    case="X08", company="Oklo", facet="reactor_technology",
    predicate="PRODUCT_CAPABILITY", mode="CATALOG_DESCRIPTION", product="Synthetic product only",
    business=None, observation=_observed(8, "MWe", "per_unit"),
    establishes=["a synthetic product without a business label exists"],
    does_not_establish=["business identity"],
)
X08["subject"]["source_business_label"] = None
X08["curation_revision"] = None
X08 = json.loads(encode_assertion(X08))
X09 = _assertion(
    case="X09", company="NuScale", facet="reactor_technology",
    predicate="OWNERSHIP_EVENT", mode="REPORTED_FACT",
    product="Synthetic acquired line", object_product="Synthetic acquired assets",
    valid_from="2026-02-01",
    establishes=["a synthetic ownership event became effective"],
    does_not_establish=["future acquisitions"],
)
X10 = _assertion(
    case="X10", company="NuScale", facet="reactor_technology",
    predicate="OWNERSHIP_EVENT", mode="ANNOUNCED_ARRANGEMENT",
    product="Synthetic ownership arrangement", object_product="Synthetic counterparty",
    establishes=["a synthetic ownership arrangement was announced"],
    does_not_establish=["closing"],
)

FIXTURES = {
    "N01": N01, "N02": N02, "N03": N03, "N03b": N03B, "N04": N04,
    "N05": N05, "N06": N06, "N07": N07, "N08": N08, "N09": N09,
    "N10": N10, "N11": N11, "N12": N12, "N13": N13, "N14": N14,
    "N03C": N03C, "N03D": N03D, "X01": X01, "X02": X02, "X03": X03,
    "X04": X04, "X04B": X04B, "X02B": X02B, "X05": X05,
    "X06": X06, "X07": X07, "X08": X08,
    "X09": X09, "X10": X10,
}


def nuclear_bundle(*assertions: dict[str, Any], omissions: tuple[str, ...] = (),
                   rights_revision: str = "synthetic-rights-2026-09-25") -> OwnerBundle:
    selected = list(assertions)
    revisions = [(fixture["curation_revision"], "assertions")
                 for fixture in selected]
    return OwnerBundle(
        revision_tuple=tuple(sorted(revisions)),
        rights_revision=rights_revision,
        assertions=tuple(selected),
        identity_results=(),
        event_workspaces=(),
        financial_packets=(),
        interpretation_blocks=(),
        native_refs=(),
        omissions=omissions,
    )


def nuclear_query(slice_key: str = "reactor_technology", view: str = "commercial",
                  **changes: Any) -> ResearchQuery:
    fields = {
        "anchor_theme_id": "nuclear_power", "slice_key": slice_key,
        "view": view, "time_mode": "latest", "source_cutoff": None,
        "recorded_cutoff": None, "offset": 0, "limit": 50,
        "expected_generation": None,
    }
    fields.update(changes)
    return ResearchQuery(**fields)


def clone(name: str) -> dict[str, Any]:
    return copy.deepcopy(FIXTURES[name])


def variant(name: str, case: str, **changes: Any) -> dict[str, Any]:
    value = clone(name)
    value["curation_revision"] = None
    value["source"]["source_uri"] = (
        f"https://www.sec.gov/Archives/edgar/data/synthetic/{case}.htm")
    value["source"]["locator"] = f"synthetic-{case}"
    value["source"]["retention_ref"] = f"synthetic://{case}"
    for key, change in changes.items():
        if key in ("source", "subject", "scope", "temporal", "limitations"):
            value[key].update(change)
        else:
            value[key] = change
    return json.loads(encode_assertion(value))
