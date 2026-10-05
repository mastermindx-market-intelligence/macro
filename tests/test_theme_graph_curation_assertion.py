"""The shared curation-assertion contract (``theme_graph.curation_assertion.v1``).

The Robotics-pinned tests (accepted Robotics plan Task 1, adopted verbatim as the
shared owner contract — shared with the Semiconductor vertical, decision R1) travel
with the module, so every vertical that mints assertions holds the SAME grammar:
the revision is a pure function of the payload, the stamp is tamper-evident, an
unknown publication stays null instead of being borrowed from another date, and
authority is literal all-false in BOTH the schema (``const: false``) and the code.

Fixtures here are synthetic and dated with constants that have no relation to the
wall clock — a contract test that ages is a scheduled red.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from engine.theme_graph import curation_assertion as ca

CONTRACTS = Path(__file__).resolve().parent.parent / "contracts" / "theme_graph"
SCHEMA_FILE = CONTRACTS / "curation_assertion.v1.schema.json"


# ---------------------------------------------------------------------------
# The smallest valid SEMICONDUCTOR-shaped payload (non-null review_due_at and
# native_digest) — unstamped, so tests can stamp it, mutate it, or validate it
# with allow_unstamped=True. The frozen Robotics reference payload (null
# review_due_at / native_digest) is `_robotics_reference_payload` below.
# ---------------------------------------------------------------------------

_TEMPLATE: dict = {
    "schema": "theme_graph.curation_assertion.v1",
    "curation_revision": None,
    "review": {
        "disposition": "accepted",
        "reviewed_at": "2026-03-15T09:00:00Z",
        "reviewer": "fixture-reviewer",
        "review_due_at": "2026-04-15T09:00:00Z",
    },
    "source": {
        "publisher": "Example Wire Service",
        "source_uri": "https://example.invalid/press/meridian-line-update",
        "locator": "para-3",
        "published_at": "2026-03-14",
        "published_at_grain": "date",
        "observed_at": "2026-03-15T08:00:00Z",
        "retained_at": "2026-03-15T08:05:00Z",
        "retention_ref": "retention:example-invalid-2026",
        "native_digest": "sha256:" + "a" * 64,
    },
    "subject": {
        "company_node_id": None,
        "source_business_label": "Meridian Wafer Systems",
        "source_product_label": "Meridian Deposition Tool",
        "source_platform_label": None,
        "configuration": "300mm",
    },
    "object": {
        "source_product_label": "Meridian Deposition Tool",
        "configuration": "300mm",
    },
    "predicate": "DOCUMENTED_PRODUCT_INCLUSION",
    "statement_mode": "REPORTED_FACT",
    "scope": {
        "canonical_theme_id": "theme:semiconductors",
        "application": "logic",
        "technology_facet": "advanced packaging",
        "region": "TW",
        "period": "2026",
        "denominator": None,
    },
    "observation": {
        "value": 12,
        "value_high": None,
        "unit": "tool",
        "quantity_basis": "per_installation",
        "gross_net_basis": None,
        "stock_flow": "flow",
        "estimate_status": "reported",
        "precision": "integer",
    },
    "temporal": {
        "business_valid_from": "2026-03-01",
        "business_valid_to": None,
    },
    "limitations": {
        "establishes": ["the business publicly described the product line"],
        "does_not_establish": ["shipping volume", "revenue impact"],
        "coverage": "single vendor press description",
        "source_dependence": "vendor-authored claim",
        "expiry_trigger": "the vendor withdraws the product page",
    },
    "correction": {"predecessor_revision": None, "reason": None},
    "authority": {
        "can_rank": False,
        "can_gate": False,
        "can_size": False,
        "can_originate": False,
        "can_open_entry": False,
    },
}


def _base_payload() -> dict:
    return copy.deepcopy(_TEMPLATE)


def _stamped(payload: dict) -> dict:
    out = copy.deepcopy(payload)
    out["curation_revision"] = ca.curation_revision(payload)
    return out


def _robotics_reference_payload() -> dict:
    """The frozen Robotics smallest-valid assertion (Robotics plan Task 1
    Step 1, `valid_assertion()`), verbatim. The ONE shared contract must
    represent its own owner's reference payload — nulls included.

    The publisher/URL are the Robotics owner's own public example (a vendor
    case-study page, not a semiconductor issuer and not paid data); they are
    kept byte-for-byte so this test pins the reference, not a paraphrase."""
    return {
        "schema": "theme_graph.curation_assertion.v1",
        "curation_revision": None,
        "review": {
            "disposition": "accepted",
            "reviewed_at": "2026-09-23T07:00:00Z",
            "reviewer": "sol",
            "review_due_at": None,
        },
        "source": {
            "publisher": "Orbbec",
            "source_uri": "https://www.orbbec.com/case-studies/example",
            "locator": "NarGo configuration paragraph",
            "published_at": None,
            "published_at_grain": "unknown",
            "observed_at": "2026-09-23T06:00:00Z",
            "retained_at": "2026-09-23T06:05:00Z",
            "retention_ref": "research-vault://source/orbbec-nargo",
            "native_digest": None,
        },
        "subject": {
            "company_node_id": "co:us:ORBBEC_PRIVATE_EXAMPLE",
            "source_business_label": "Orbbec",
            "source_product_label": "Gemini 335",
            "source_platform_label": None,
            "configuration": None,
        },
        "object": {
            "source_product_label": "NarGo order-picking robot",
            "configuration": "described case-study configuration",
        },
        "predicate": "DOCUMENTED_PRODUCT_INCLUSION",
        "statement_mode": "REPORTED_FACT",
        "scope": {
            "canonical_theme_id": "robotics_automation",
            "application": "warehouse_robotics",
            "technology_facet": "perception",
            "region": None,
            "period": None,
            "denominator": None,
        },
        "observation": {
            "value": 2,
            "value_high": None,
            "unit": "camera",
            "quantity_basis": "per_robot",
            "gross_net_basis": None,
            "stock_flow": None,
            "estimate_status": "reported",
            "precision": "integer",
        },
        "temporal": {
            "business_valid_from": None,
            "business_valid_to": None,
        },
        "limitations": {
            "establishes": ["two cameras in the described configuration"],
            "does_not_establish": ["price", "annual shipments", "all generations"],
            "coverage": "single described configuration",
            "source_dependence": "publisher_statement",
            "expiry_trigger": "new configuration or corrected source",
        },
        "correction": {
            "predecessor_revision": None,
            "reason": None,
        },
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_originate": False,
            "can_open_entry": False,
        },
    }


# ---------------------------------------------------------------------------
# The frozen Robotics reference payload is representable — nulls included —
# and encode_assertion is the mint path the reference defines.
# ---------------------------------------------------------------------------

def test_the_frozen_robotics_reference_payload_validates_with_its_nulls():
    payload = _robotics_reference_payload()
    out = ca.validate_assertion(payload, allow_unstamped=True)
    assert out["review"]["review_due_at"] is None
    assert out["source"]["native_digest"] is None
    assert out["source"]["published_at"] is None
    assert out["curation_revision"] is None


def test_encode_assertion_mints_an_unstamped_payload_and_matches_the_prestamped_bytes():
    payload = _robotics_reference_payload()
    text = ca.encode_assertion(payload)          # mint: stamp + serialize
    decoded = ca.decode_assertion(text)
    assert decoded["curation_revision"] == ca.curation_revision(payload)
    assert ca.REVISION_RE.match(decoded["curation_revision"])
    # minting the unstamped form and encoding the pre-stamped form are the same bytes
    assert text == ca.encode_assertion(_stamped(payload))
    # the reference's source_ref: decode(encode(unstamped)) → gmi-curation://<theme>/<rev>
    assert ca.source_ref_for(payload) == (
        f"gmi-curation://robotics_automation/{decoded['curation_revision']}")
    assert ca.source_ref_for(payload) == ca.source_ref_for(_stamped(payload))
    # the mint never mutates the caller's payload
    assert payload["curation_revision"] is None


def test_encode_assertion_still_refuses_a_wrong_stamp():
    payload = _stamped(_base_payload())
    payload["curation_revision"] = "gmirca_" + "0" * 32
    with pytest.raises(ca.CurationAssertionError, match="curation_revision_mismatch"):
        ca.encode_assertion(payload)


def test_null_review_due_and_null_native_digest_are_content_of_the_revision():
    base = _robotics_reference_payload()
    dated = _robotics_reference_payload()
    dated["review"]["review_due_at"] = "2026-12-31T00:00:00Z"
    digested = _robotics_reference_payload()
    digested["source"]["native_digest"] = "sha256:" + "a" * 64
    revs = {ca.curation_revision(base), ca.curation_revision(dated),
            ca.curation_revision(digested)}
    assert len(revs) == 3


def test_curation_revision_refuses_structurally_invalid_payloads():
    with pytest.raises(ca.CurationAssertionError, match="schema_violation"):
        ca.curation_revision({"schema": ca.SCHEMA_ID})
    bad = _base_payload()
    bad["authority"]["can_rank"] = True
    with pytest.raises(ca.CurationAssertionError, match="authority_not_all_false"):
        ca.curation_revision(bad)
    with pytest.raises(ca.CurationAssertionError, match="not_a_mapping"):
        ca.curation_revision("gmirca_" + "0" * 32)  # type: ignore[arg-type]


def test_decode_assertion_treats_a_parquet_nan_as_null_but_not_other_numbers():
    assert ca.decode_assertion(float("nan")) is None
    with pytest.raises(ca.CurationAssertionError, match="not_a_string"):
        ca.decode_assertion(1.5)
    with pytest.raises(ca.CurationAssertionError, match="not_a_string"):
        ca.decode_assertion(0)


# ---------------------------------------------------------------------------
# The schema file is itself a valid Draft 2020-12 schema (the draft evidence.v1
# and the other theme_graph contracts declare).
# ---------------------------------------------------------------------------

def test_the_schema_file_is_a_valid_draft_2020_12_schema():
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("curation_assertion.v1.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)


def test_the_schema_declares_the_frozen_schema_id_and_additional_properties_closed():
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "theme_graph.curation_assertion.v1"
    assert schema["additionalProperties"] is False
    # every object layer is closed, not only the top one
    for name in ("review", "source", "subject", "object", "scope", "observation",
                 "temporal", "limitations", "correction", "authority"):
        assert schema["properties"][name]["additionalProperties"] is False, name
    for key in ("can_rank", "can_gate", "can_size", "can_originate", "can_open_entry"):
        assert schema["properties"]["authority"]["properties"][key]["const"] is False, key


# ---------------------------------------------------------------------------
# Robotics-pinned semantics
# ---------------------------------------------------------------------------

def test_the_smallest_valid_payload_validates_and_returns_a_deep_copy():
    payload = _stamped(_base_payload())
    out = ca.validate_assertion(payload)
    assert out == payload
    out["source"]["locator"] = "mutated-after-validation"
    assert payload["source"]["locator"] == "para-3", "the return must be a deep copy"


def test_unknown_publication_stays_null_and_is_never_replaced():
    payload = _base_payload()
    payload["source"]["published_at"] = None
    payload["source"]["published_at_grain"] = "unknown"
    observed_at = payload["source"]["observed_at"]
    reviewed_at = payload["review"]["reviewed_at"]
    out = ca.validate_assertion(_stamped(payload))
    assert out["source"]["published_at"] is None
    assert out["source"]["observed_at"] == observed_at
    assert out["review"]["reviewed_at"] == reviewed_at


@pytest.mark.parametrize("predicate,mode", [
    ("REPORTED_DEPLOYMENT", "FORWARD_TARGET"),
    ("DEPLOYMENT_TARGET", "REPORTED_FACT"),
])
def test_refused_predicate_mode_pairings_are_rejected(predicate, mode):
    payload = _base_payload()
    payload["predicate"] = predicate
    payload["statement_mode"] = mode
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(_stamped(payload))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), -1, -0.5])
def test_quantities_reject_nan_inf_and_negative_values(bad):
    payload = _base_payload()
    payload["observation"]["value"] = bad
    # validated unstamped: NaN cannot be stamped (canonical JSON refuses it),
    # and the rule must fire during validation, not during serialization
    with pytest.raises(ca.CurationAssertionError, match="observation_value_invalid"):
        ca.validate_assertion(payload, allow_unstamped=True)


def test_a_value_without_quantity_basis_is_rejected():
    payload = _base_payload()
    payload["observation"]["quantity_basis"] = None
    with pytest.raises(ca.CurationAssertionError, match="quantity_basis_required"):
        ca.validate_assertion(_stamped(payload))


def test_an_unresolved_company_node_id_may_be_null():
    payload = _base_payload()
    payload["subject"]["company_node_id"] = None
    assert ca.validate_assertion(_stamped(payload))["subject"]["company_node_id"] is None


def test_a_resolved_company_node_id_is_also_valid():
    payload = _base_payload()
    payload["subject"]["company_node_id"] = "co:us:EXMP"
    assert ca.validate_assertion(_stamped(payload))["subject"]["company_node_id"] == "co:us:EXMP"


@pytest.mark.parametrize("key", ["can_rank", "can_gate", "can_size", "can_originate",
                                 "can_open_entry"])
def test_authority_must_be_literal_all_false(key):
    payload = _base_payload()
    payload["authority"][key] = True
    # `match` pins the CODE check (named rule), not merely the schema const:false
    with pytest.raises(ca.CurationAssertionError, match="authority_not_all_false"):
        ca.validate_assertion(payload, allow_unstamped=True)
    with pytest.raises(ca.CurationAssertionError, match="authority_not_all_false"):
        ca.curation_revision(payload)


# ---------------------------------------------------------------------------
# The revision is a pure function of the payload's content
# ---------------------------------------------------------------------------

def test_two_assertions_differing_only_in_locator_get_different_revisions():
    a = _base_payload()
    b = _base_payload()
    b["source"]["locator"] = "para-9"
    assert a["source"]["locator"] != b["source"]["locator"]
    assert ca.curation_revision(a) != ca.curation_revision(b)


@pytest.mark.parametrize("field,value", [
    ("native_digest", "sha256:" + "b" * 64),
    ("retained_at", "2026-03-16T08:05:00Z"),
])
def test_changing_native_digest_or_retained_at_mints_a_new_revision(field, value):
    a = _base_payload()
    b = _base_payload()
    b["source"][field] = value
    assert ca.curation_revision(a) != ca.curation_revision(b)


def test_a_correction_on_the_successor_does_not_change_the_predecessors_revision():
    pred = _stamped(_base_payload())
    pred_revision_before = pred["curation_revision"]

    succ = _base_payload()
    succ["source"]["locator"] = "para-11"
    succ["source"]["native_digest"] = "sha256:" + "c" * 64
    succ["correction"] = {"predecessor_revision": pred_revision_before,
                          "reason": "unit basis restated"}
    succ = _stamped(succ)

    assert ca.curation_revision(pred) == pred_revision_before
    assert succ["correction"]["predecessor_revision"] == pred_revision_before
    ca.validate_assertion(pred)
    ca.validate_assertion(succ)


def test_the_revision_grammar_is_enforced():
    payload = _stamped(_base_payload())
    assert ca.curation_revision(payload) == payload["curation_revision"]
    tampered = {**payload, "curation_revision": "gmirca_" + "0" * 31}  # 31 hex, not 32
    with pytest.raises(ca.CurationAssertionError):
        ca.validate_assertion(tampered)


def test_an_unstamped_payload_validates_only_with_allow_unstamped():
    payload = _base_payload()
    out = ca.validate_assertion(payload, allow_unstamped=True)
    assert out["curation_revision"] is None
    with pytest.raises(ca.CurationAssertionError, match="unstamped"):
        ca.validate_assertion(payload)


# ---------------------------------------------------------------------------
# encode / decode / source_ref_for
# ---------------------------------------------------------------------------

def test_encode_then_decode_is_the_identity():
    payload = _stamped(_base_payload())
    encoded = ca.encode_assertion(payload)
    assert isinstance(encoded, str)
    assert json.loads(encoded) == payload
    assert ca.decode_assertion(encoded) == payload


def test_decode_of_a_tampered_stamp_raises_curation_revision_mismatch():
    encoded = ca.encode_assertion(_stamped(_base_payload()))
    doc = json.loads(encoded)
    doc["curation_revision"] = "gmirca_" + "f" * 32  # grammar-valid, wrong stamp
    with pytest.raises(ca.CurationAssertionError, match="curation_revision_mismatch"):
        ca.decode_assertion(json.dumps(doc))


def test_decode_of_json_with_an_unknown_extra_key_raises():
    encoded = ca.encode_assertion(_stamped(_base_payload()))
    doc = json.loads(encoded)
    doc["mystery_key"] = 1
    with pytest.raises(ca.CurationAssertionError):
        ca.decode_assertion(json.dumps(doc))


def test_decode_of_malformed_json_raises_curation_assertion_error():
    with pytest.raises(ca.CurationAssertionError, match="malformed_json"):
        ca.decode_assertion("{not json")


@pytest.mark.parametrize("empty", [None, ""])
def test_decode_of_none_and_empty_string_returns_none(empty):
    assert ca.decode_assertion(empty) is None


def test_source_ref_for_uses_scope_canonical_theme_id():
    payload = _stamped(_base_payload())
    ref = ca.source_ref_for(payload)
    assert ref == f"gmi-curation://theme:semiconductors/{payload['curation_revision']}"
    # decision R1: the theme id comes from the payload, never a vertical literal
    payload["scope"]["canonical_theme_id"] = "theme:robotics"
    payload = _stamped(payload)
    assert ca.source_ref_for(payload) == (
        f"gmi-curation://theme:robotics/{payload['curation_revision']}")
