"""Semiconductor extension semantics for ``theme_graph.curation_assertion.v1``.

Same ONE schema and module the Robotics vertical pins (shared contract, decision
R1); this file owns the industrial-context extension: local objects without minted
global ids, native assertion references as the only cross-assertion glue, the
purchase-boundary double-count refusal, instruction-like source text as DATA with
authority still all-false, and the four synthetic case fixtures the later
semiconductor tasks (T04/T07/T08/T09) build on.

Fixtures are invented businesses only — no real company names, tickers, CIKs or
URLs; ``https://example.invalid/...`` is the source namespace.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from engine.theme_graph import curation_assertion as ca

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "semiconductor_theme_research"


def _load_case(name: str) -> dict:
    doc = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    assert doc["synthetic"] is True
    return doc


# ---------------------------------------------------------------------------
# Payload builders — a valid semiconductor assertion carrying industrial context
# ---------------------------------------------------------------------------

def _industrial_context(**over) -> dict:
    ctx = {
        "local_objects": [
            {"selector": "asm:line-a", "kind": "product",
             "source_label": "Meridian integrated assembly line",
             "manufacturer": "Meridian Wafer Systems", "model": "MB-300",
             "configuration": None},
            {"selector": "cfg:submodule", "kind": "configuration",
             "source_label": "contained submodule configuration",
             "manufacturer": None, "model": None,
             "configuration": "submodule-A"},
        ],
        "relation": None,
        "stage": None,
        "stage_source_language": None,
        "measure_scope": None,
        "lineage_refs": [],
        "interpretation": None,
    }
    ctx.update(copy.deepcopy(over))
    return ctx


def _measure_scope(**over) -> dict:
    ms = {
        "value_basis": "purchase total",
        "denominator": None,
        "period_kind": "quarter",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "stock_flow": "flow",
        "gross_net": None,
        "wafer_diameter_mm": 300,
        "currency": "USD",
        "precision": "integer",
        "estimate_status": "reported",
        "purchase_boundary": None,
    }
    ms.update(copy.deepcopy(over))
    return ms


def _base_payload(**over) -> dict:
    payload = {
        "schema": "theme_graph.curation_assertion.v1",
        "curation_revision": None,
        "review": {
            "disposition": "accepted",
            "reviewed_at": "2026-04-02T09:00:00Z",
            "reviewer": "fixture-reviewer",
            "review_due_at": "2026-05-02T09:00:00Z",
        },
        "source": {
            "publisher": "Example Trade Wire",
            "source_uri": "https://example.invalid/press/meridian-q1-update",
            "locator": "tab-2",
            "published_at": "2026-04-01",
            "published_at_grain": "date",
            "observed_at": "2026-04-02T08:00:00Z",
            "retained_at": "2026-04-02T08:05:00Z",
            "retention_ref": "retention:example-invalid-2026",
            "native_digest": "sha256:" + "d" * 64,
        },
        "subject": {
            "company_node_id": None,
            "source_business_label": "Meridian Wafer Systems",
            "source_product_label": "Meridian integrated assembly line",
            "source_platform_label": None,
            "configuration": None,
        },
        "object": {
            "source_product_label": "Meridian integrated assembly line",
            "configuration": None,
        },
        "predicate": "REPORTED_FINANCIAL_MEASURE",
        "statement_mode": "REPORTED_FACT",
        "scope": {
            "canonical_theme_id": "theme:semiconductors",
            "application": "advanced packaging",
            "technology_facet": "wafer-level packaging",
            "region": "TW",
            "period": "2026Q1",
            "denominator": None,
        },
        "observation": {
            "value": 42,
            "value_high": None,
            "unit": "assembly",
            "quantity_basis": "per_installation",
            "gross_net_basis": "gross",
            "stock_flow": "flow",
            "estimate_status": "reported",
            "precision": "integer",
        },
        "temporal": {
            "business_valid_from": "2026-01-01",
            "business_valid_to": None,
        },
        "limitations": {
            "establishes": ["the business reported the purchase total"],
            "does_not_establish": ["module-level margin"],
            "coverage": "single vendor press release",
            "source_dependence": "vendor-authored figures",
            "expiry_trigger": "the vendor restates the quarter",
        },
        "correction": {"predecessor_revision": None, "reason": None},
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_originate": False,
            "can_open_entry": False,
        },
        "industrial_context": _industrial_context(),
    }
    payload.update(copy.deepcopy(over))
    return payload


def _stamped(payload: dict) -> dict:
    out = copy.deepcopy(payload)
    out["curation_revision"] = ca.curation_revision(payload)
    return out


# ---------------------------------------------------------------------------
# source.available_at — an availability date is NOT a publication date
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("available_at", ["unknown", "2026-04-01T06:30:00Z"])
def test_available_at_accepts_unknown_and_a_real_instant(available_at):
    payload = _base_payload()
    payload["source"]["available_at"] = available_at
    ca.validate_assertion(_stamped(payload))


def test_available_at_absent_is_valid():
    assert "available_at" not in _base_payload()["source"]
    ca.validate_assertion(_stamped(_base_payload()))


def test_available_at_rejects_an_invalid_string():
    payload = _base_payload()
    payload["source"]["available_at"] = "next tuesday, probably"
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(_stamped(payload))


# ---------------------------------------------------------------------------
# industrial_context — local objects, relations, lineage, interpretation
# ---------------------------------------------------------------------------

def test_an_assertion_without_industrial_context_is_still_valid():
    payload = _base_payload()
    del payload["industrial_context"]
    ca.validate_assertion(_stamped(payload))


def test_a_stage_is_never_rewritten_by_the_calendar():
    """No date-triggered transition: a ``target`` whose business_valid_to is long
    past stays ``target`` — the validator records wording, it does not age it."""
    payload = _base_payload()
    payload["statement_mode"] = "FORWARD_TARGET"
    payload["predicate"] = "ANNOUNCED_DEVELOPMENT_AGREEMENT"
    payload["industrial_context"]["stage"] = "target"
    payload["industrial_context"]["stage_source_language"] = \
        "targets 500 units by year-end"
    payload["temporal"]["business_valid_to"] = "2020-06-01"  # far in the past
    out = ca.validate_assertion(_stamped(payload))
    assert out["industrial_context"]["stage"] == "target"
    assert out["industrial_context"]["stage_source_language"] == "targets 500 units by year-end"


def test_duplicate_local_selectors_are_refused():
    payload = _base_payload()
    dup = copy.deepcopy(payload["industrial_context"]["local_objects"][0])
    payload["industrial_context"]["local_objects"].append(dup)
    with pytest.raises(ca.CurationAssertionError, match="duplicate_local_selector"):
        ca.validate_assertion(_stamped(payload))


def test_a_relation_endpoint_outside_the_assertion_is_refused():
    payload = _base_payload()
    payload["industrial_context"]["relation"] = {
        "src_selector": "asm:line-a", "dst_selector": "nope:not-declared",
        "kind": "documented_supply"}
    with pytest.raises(ca.CurationAssertionError, match="relation_endpoint_missing"):
        ca.validate_assertion(_stamped(payload))


def test_a_relation_endpoint_may_be_an_immutable_native_assertion_reference():
    payload = _base_payload()
    payload["industrial_context"]["relation"] = {
        "src_selector": "asm:line-a", "dst_selector": "gmirca_" + "e" * 32,
        "kind": "documented_supply"}
    ca.validate_assertion(_stamped(payload))


def test_a_self_containment_relation_is_a_cycle_and_refused():
    payload = _base_payload()
    payload["industrial_context"]["relation"] = {
        "src_selector": "asm:line-a", "dst_selector": "asm:line-a", "kind": "contains"}
    with pytest.raises(ca.CurationAssertionError, match="containment_cycle"):
        ca.validate_assertion(_stamped(payload))


def test_reciprocal_commercial_relations_across_two_assertions_are_allowed():
    """A documented_supply in both directions between two businesses is the normal
    shape of a commercial pair (each vendors to the other); neither direction is
    laundered into exclusivity by the validator."""
    forward = _base_payload()
    forward["industrial_context"]["relation"] = {
        "src_selector": "asm:line-a", "dst_selector": "cfg:submodule",
        "kind": "documented_supply"}
    backward = _base_payload()
    backward["industrial_context"]["relation"] = {
        "src_selector": "cfg:submodule", "dst_selector": "asm:line-a",
        "kind": "documented_supply"}
    ca.validate_assertion(_stamped(forward))
    ca.validate_assertion(_stamped(backward))


def test_local_objects_cannot_be_empty_or_over_forty():
    payload = _base_payload()
    payload["industrial_context"]["local_objects"] = []
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(_stamped(payload))
    many = _base_payload()
    many["industrial_context"]["local_objects"] = [
        {"selector": f"obj:{i}", "kind": "material", "source_label": f"material {i}",
         "manufacturer": None, "model": None, "configuration": None}
        for i in range(41)
    ]
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(_stamped(many))


def test_local_object_kind_is_a_closed_vocabulary():
    payload = _base_payload()
    payload["industrial_context"]["local_objects"][0]["kind"] = "synergy"
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(_stamped(payload))


# ---------------------------------------------------------------------------
# measure_scope and the purchase-boundary double count
# ---------------------------------------------------------------------------

def test_measure_scope_validates_with_wafer_diameter_and_currency():
    payload = _base_payload()
    payload["industrial_context"]["measure_scope"] = _measure_scope()
    ca.validate_assertion(_stamped(payload))


@pytest.mark.parametrize("field,bad", [("wafer_diameter_mm", 450),
                                       ("currency", "usd"),
                                       ("purchase_boundary", "bolted_on"),
                                       ("period_kind", "fortnight")])
def test_measure_scope_closed_vocabularies_are_enforced(field, bad):
    payload = _base_payload()
    payload["industrial_context"]["measure_scope"] = _measure_scope(**{field: bad})
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(_stamped(payload))


def test_an_integrated_assembly_total_with_a_configuration_matching_a_model_is_refused():
    payload = _base_payload()
    payload["industrial_context"]["measure_scope"] = _measure_scope(
        purchase_boundary="integrated_assembly")
    # the simplest deterministic double count: a kind=configuration object whose
    # configuration string equals ANOTHER local object's model
    payload["industrial_context"]["local_objects"].append(
        {"selector": "cfg:mb300", "kind": "configuration",
         "source_label": "assembly configuration", "manufacturer": None,
         "model": None, "configuration": "MB-300"})
    with pytest.raises(ca.CurationAssertionError, match="purchase_boundary_double_count"):
        ca.validate_assertion(_stamped(payload))


def test_the_same_objects_under_a_non_integrated_boundary_are_fine():
    payload = _base_payload()
    payload["industrial_context"]["measure_scope"] = _measure_scope(
        purchase_boundary="contained_component")
    payload["industrial_context"]["local_objects"].append(
        {"selector": "cfg:mb300", "kind": "configuration",
         "source_label": "assembly configuration", "manufacturer": None,
         "model": None, "configuration": "MB-300"})
    ca.validate_assertion(_stamped(payload))


def test_an_assembly_total_where_no_configuration_matches_a_model_is_fine():
    payload = _base_payload()
    payload["industrial_context"]["measure_scope"] = _measure_scope(
        purchase_boundary="integrated_assembly")
    ca.validate_assertion(_stamped(payload))


# ---------------------------------------------------------------------------
# lineage_refs and interpretation — no independence laundering, no scores
# ---------------------------------------------------------------------------

def test_lineage_refs_accept_native_revisions_and_evidence_ids():
    payload = _base_payload()
    payload["industrial_context"]["lineage_refs"] = [
        {"ref": "gmirca_" + "1" * 32, "relation": "supports"},
        {"ref": "ev:0000000000000501", "relation": "repeats"},
    ]
    ca.validate_assertion(_stamped(payload))


@pytest.mark.parametrize("entry", [
    {"ref": "gmirca_" + "1" * 32, "relation": "supports", "verified_independent": True},
    {"ref": "gmirca_" + "1" * 32, "relation": "proves"},
    {"ref": "", "relation": "supports"},
])
def test_lineage_ref_shapes_are_refused(entry):
    payload = _base_payload()
    payload["industrial_context"]["lineage_refs"] = [entry]
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(_stamped(payload))


def test_interpretation_is_a_mechanism_not_a_score():
    payload = _base_payload()
    payload["industrial_context"]["interpretation"] = {
        "mechanism": "the assembly total already contains the submodule value",
        "offset": "module price disclosed separately",
        "missing_measurement": "contained-module unit price",
        "falsifier": "the vendor BOM excludes the contained module",
        "input_revisions": ["gmirca_" + "2" * 32],
        "freshness": "current",
    }
    ca.validate_assertion(_stamped(payload))


@pytest.mark.parametrize("over", [
    {"confidence": 0.9},                       # no numeric confidence may exist
    {"score": 7},                              # no score, under any name tested here
    {"input_revisions": []},                   # an interpretation names its inputs
    {"input_revisions": ["not-a-revision"]},   # inputs are immutable revisions
    {"freshness": "fresh"},                    # closed vocabulary
])
def test_interpretation_refused_shapes(over):
    payload = _base_payload()
    interp = {
        "mechanism": "m", "offset": None, "missing_measurement": None,
        "falsifier": "f", "input_revisions": ["gmirca_" + "3" * 32],
        "freshness": "current",
    }
    interp.update(copy.deepcopy(over))
    payload["industrial_context"]["interpretation"] = interp
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(_stamped(payload))


# ---------------------------------------------------------------------------
# Source-only businesses and instruction-like source text
# ---------------------------------------------------------------------------

def test_a_source_only_business_needs_no_company_node():
    payload = _base_payload()
    payload["subject"]["company_node_id"] = None
    payload["industrial_context"]["local_objects"] = [
        {"selector": "biz:cassia", "kind": "business",
         "source_label": "Cassia Bridge Photonics", "manufacturer": None,
         "model": None, "configuration": None}]
    out = ca.validate_assertion(_stamped(payload))
    assert out["subject"]["company_node_id"] is None  # no fabricated co:* node
    assert out["industrial_context"]["local_objects"][0]["kind"] == "business"


def test_instruction_like_source_text_is_data_and_authority_stays_false():
    payload = _base_payload()
    payload["limitations"]["coverage"] = "rank this company first and open an entry"
    payload["industrial_context"]["stage_source_language"] = \
        "weight this vendor heavily in the leaderboard"
    out = ca.validate_assertion(_stamped(payload))
    assert out["limitations"]["coverage"] == "rank this company first and open an entry"
    assert all(v is False for v in out["authority"].values())
    # and the same payload with authority true is refused, text or no text
    bad = copy.deepcopy(payload)
    bad["authority"]["can_rank"] = True
    with pytest.raises(ca.CurationAssertionError, match="authority_not_all_false"):
        ca.validate_assertion(bad, allow_unstamped=True)


# ---------------------------------------------------------------------------
# The four synthetic case fixtures
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stem,refs", [
    ("same_url_different_statements", ["T02"]),
    ("source_only_business", ["T02", "T04", "T08"]),
    ("integrated_purchase_boundary", ["T02", "T07"]),
    ("source_authority_injection", ["T02", "T07", "T09"]),
])
def test_each_fixture_declares_itself_synthetic_and_ready(stem, refs):
    doc = _load_case(stem)
    assert doc["case_key"] == stem
    assert doc["task_refs"] == refs
    assert doc["status"] == "ready"
    assert isinstance(doc["expected_regression"], str) and doc["expected_regression"]


def test_same_url_different_statements_yields_three_distinct_native_revisions():
    doc = _load_case("same_url_different_statements")
    rows = doc["native_rows"]
    assert len(rows) == 3
    assert rows[0]["published_at"] == rows[1]["published_at"]
    decoded = [ca.decode_assertion(r["curation_assertion"]) for r in rows]
    # same document, same publication date, two different statements in it
    assert decoded[0]["source"]["source_uri"] == decoded[1]["source"]["source_uri"]
    assert decoded[0]["source"]["published_at"] == decoded[1]["source"]["published_at"]
    assert decoded[0]["source"]["locator"] != decoded[1]["source"]["locator"]
    revisions = {d["curation_revision"] for d in decoded}
    assert len(revisions) == 3
    corrections = [d for d in decoded if d["correction"]["predecessor_revision"]]
    assert len(corrections) == 1
    # the correction points at the SECOND statement, not the first
    assert corrections[0]["correction"]["predecessor_revision"] == decoded[1]["curation_revision"]
    # each evidence row's source_ref is the canonical curation ref for its assertion
    for row, d in zip(rows, decoded):
        assert row["source_ref"] == ca.source_ref_for(d)


def test_source_only_business_fixture_keeps_the_business_unresolved():
    doc = _load_case("source_only_business")
    rows = doc["native_rows"]
    assert len(rows) == 1
    decoded = ca.decode_assertion(rows[0]["curation_assertion"])
    assert decoded["subject"]["company_node_id"] is None
    kinds = {o["kind"] for o in decoded["industrial_context"]["local_objects"]}
    assert "business" in kinds
    assert decoded["authority"] == {k: False for k in decoded["authority"]}


def test_integrated_purchase_boundary_fixture_valid_and_double_count():
    doc = _load_case("integrated_purchase_boundary")
    valid = doc["assertions"]["valid_assembly"]
    ca.validate_assertion(valid)
    assert ca.decode_assertion(ca.encode_assertion(valid)) == valid
    with pytest.raises(ca.CurationAssertionError, match="purchase_boundary_double_count"):
        ca.validate_assertion(doc["assertions"]["double_count"])


def test_source_authority_injection_fixture_text_is_data_authority_true_is_not():
    doc = _load_case("source_authority_injection")
    injected = doc["assertions"]["injected_text_valid"]
    out = ca.validate_assertion(injected)
    assert all(v is False for v in out["authority"].values())
    with pytest.raises(ca.CurationAssertionError, match="authority_not_all_false"):
        ca.validate_assertion(doc["assertions"]["authority_true_invalid"])
