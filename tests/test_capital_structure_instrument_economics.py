"""SPEC_I1 §2-§4: pre-instrument term records, bindings and their attachment.

Every case named in §6 for the term path has its own test here.  Fixtures are
built in-file: no network, no ``data/`` read, no digest hard-coded (every digest
is derived with :func:`stable_id` or :func:`sha256_of`).  The only float
literals in this file are inside the float-refusal tests.
"""
from __future__ import annotations

import dataclasses
import inspect
import random
from copy import deepcopy
from decimal import Decimal

import pytest

import tests.test_capital_structure_issuer_state_contracts as T
from engine.capital_structure import issuer_state_contracts as c
from engine.capital_structure.instrument_economics import (
    ATTACHABLE_INSTRUMENT_STATUSES,
    BINDING_RECORD_KEYS,
    EXTRACTION_METHOD_ORIGINS,
    IMPLEMENTATION,
    TERM_BINDING_SCHEMA,
    TERM_RECORD_KEYS,
    TERM_RECORD_SCHEMA,
    UNATTACHED_REASONS,
    attach_economic_terms,
    validate_economic_term_record,
    validate_term_binding,
)
from engine.capital_structure.instrument_resolution import instrument_id_for
from engine.capital_structure.supply_scenarios import evaluate_supply, supply_trace
from engine.capital_structure.term_integration import INSTRUMENT_IDENTITY_KEYS

ISSUER = T.ISSUER
AS_OF = T.AS_OF
SERIES = "series_a_warrants_2026_06"
OTHER_SERIES = "series_b_warrants_2026_09"
HASH = "a" * 64
HASH_UPPER = "A" * 64
GOLD_HASH = "b" * 64
EARLY = "2026-06-01T00:00:00Z"
EFFECTIVE = "2026-06-01T00:00:00Z"
AVAILABLE = "2026-06-02T00:00:00Z"
DECIDED = "2026-06-03T00:00:00Z"
LATER_EFFECTIVE = "2026-09-30T00:00:00Z"


# ---------------------------------------------------------------------------
# Shared validation helpers (used by every test in both I1a suites)
# ---------------------------------------------------------------------------


def check_instrument_set(instruments: c.InstrumentSet) -> dict:
    """Serialize and schema-validate an InstrumentSet; return the record."""
    record = instruments.as_record()
    c.validate_state_record("instrument_set", record)
    return record


def check_supply_envelope(envelope: c.SupplyEnvelope) -> dict:
    """Serialize and schema-validate a SupplyEnvelope; return the record."""
    record = envelope.as_record()
    c.validate_state_record("supply_envelope", record)
    return record


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def term_record(name: str, **over) -> dict:
    """One §2 occurrence record; the id is always the evidence digest."""
    unit, _basis = c.ECONOMIC_TERM_UNITS.get(name, (None, None))
    record = {
        "schema": TERM_RECORD_SCHEMA,
        "occurrence_id": "",
        "issuer_id": ISSUER,
        "security_scope": SERIES,
        "name": name,
        "value": None,
        "unit": unit,
        "currency": "USD" if unit == "usd" else None,
        "flag": None,
        "expression": None,
        "date_value": None,
        "evidence": {"manifest_id": "manifest:1", "span_id": f"span:{name}", "text_sha256": HASH},
        "extraction": {"method": "deterministic", "parser_version": "1.0.0"},
        "fact_origin": "canonical_extraction",
        "point_in_time": {"available_at": AVAILABLE, "event_time": EFFECTIVE},
        "status": "observed",
    }
    allowed = set(record) | {
        "method", "parser_version", "manifest", "span", "text_sha256",
        "available_at", "event_time", "occurrence_id",
    }
    unexpected = sorted(set(over) - allowed)
    assert not unexpected, unexpected
    if "method" in over:
        record["extraction"]["method"] = over["method"]
    if "parser_version" in over:
        record["extraction"]["parser_version"] = over["parser_version"]
    if "manifest" in over:
        record["evidence"]["manifest_id"] = over["manifest"]
    if "span" in over:
        record["evidence"]["span_id"] = over["span"]
    if "text_sha256" in over:
        record["evidence"]["text_sha256"] = over["text_sha256"]
    if "available_at" in over:
        record["point_in_time"]["available_at"] = over["available_at"]
    if "event_time" in over:
        record["point_in_time"]["event_time"] = over["event_time"]
    for key in ("value", "unit", "currency", "flag", "expression", "date_value", "issuer_id",
                "security_scope", "fact_origin", "status", "name", "schema"):
        if key in over:
            record[key] = over[key]
    if record["status"] == "deferred" and "method" not in over:
        record["extraction"]["method"] = "deferred"
    record["occurrence_id"] = over.get("occurrence_id") or c.stable_id(
        "econterm",
        {
            "manifest_id": record["evidence"]["manifest_id"],
            "span_id": record["evidence"]["span_id"],
            "name": record["name"],
            "parser_version": record["extraction"]["parser_version"],
        },
    )
    return record


def binding(occurrence_id: str, **over) -> dict:
    """One §3 adjudicated-gold binding for ``SERIES`` unless told otherwise."""
    issuer_id = over.get("issuer_id", ISSUER)
    series_key = over.get("series_key", SERIES)
    instrument_id = over.get("instrument_id") or instrument_id_for(issuer_id, series_key)
    record = {
        "schema": TERM_BINDING_SCHEMA,
        "binding_id": "",
        "occurrence_id": occurrence_id,
        "issuer_id": issuer_id,
        "series_key": series_key,
        "instrument_id": instrument_id,
        "fact_origin": "adjudicated_gold",
        "decided_at": DECIDED,
        "effective_at": DECIDED,
        "evidence": [{"manifest_id": "manifest:9", "span_id": "span:9", "text_sha256": GOLD_HASH}],
        "supersedes": [],
    }
    for key in ("decided_at", "effective_at", "fact_origin", "series_key", "instrument_id", "issuer_id", "schema"):
        if key in over:
            record[key] = over[key]
    if "supersedes" in over:
        record["supersedes"] = list(over["supersedes"])
    if "evidence" in over:
        record["evidence"] = list(over["evidence"])
    record["binding_id"] = over.get("binding_id") or c.stable_id(
        "termbind",
        {"occurrence_id": record["occurrence_id"], "instrument_id": record["instrument_id"]},
    )
    return record


def instrument_for(series_key: str, kind: str = "warrant", status: str = "outstanding", **over):
    """A resolved instrument whose id is derived, never invented."""
    method = {"outstanding": "supported_identity", "amended": "amendment_join",
              "retired": "retirement", "unresolved_candidate": "unresolved"}[status]
    instrument_id = instrument_id_for(ISSUER, series_key)
    defaults = dict(instrument_id=instrument_id, security_class_id=f"class:{series_key}", kind=kind, status=status)
    if status == "unresolved_candidate":
        defaults["outstanding"] = None
    defaults.update(over)
    return instrument_id, T.instrument(method=method, **defaults)


def set_for(*pairs, **over) -> c.InstrumentSet:
    defaults = dict(
        issuer_id=ISSUER,
        as_of=AS_OF,
        instruments=tuple(item for _instrument_id, item in pairs),
        provenance=T.family_provenance("instruments"),
        receipt=T.receipt(),
        unresolved_candidate_ids=(),
    )
    defaults.update(over)
    return c.InstrumentSet(**defaults)


def attach(instruments, records, bindings, as_of=AS_OF):
    """Attach and schema-validate: every InstrumentSet this suite builds is checked."""
    attached = attach_economic_terms(instruments, records, bindings, as_of)
    check_instrument_set(attached)
    return attached


def terms_of(attached: c.InstrumentSet, instrument_id: str) -> dict:
    instrument = next(item for item in attached.instruments if item.instrument_id == instrument_id)
    return {term.name: term for term in instrument.economic_terms}


def expected_receipt(instruments: c.InstrumentSet, *, term_ids, binding_ids, unattached, superseded,
                     superseded_bindings, as_of: str = AS_OF) -> c.CalculationReceipt:
    """Rebuild the receipt from the C7 input keys; no digest is ever hard-coded."""
    inputs = {
        "instrument_set_receipt_id": instruments.receipt.receipt_id,
        "as_of": as_of,
        "term_ids": list(term_ids),
        "binding_ids": list(binding_ids),
        "unattached": [dict(item) for item in unattached],
        "superseded": [dict(item) for item in superseded],
        "superseded_bindings": list(superseded_bindings),
    }
    return c.CalculationReceipt.build(
        inputs=inputs,
        rule_digest=c.sha256_of(c.ECONOMIC_TERM_NAMES),
        implementation=IMPLEMENTATION,
        computed_at=as_of,
    )


def receipt_of(attached: c.InstrumentSet) -> dict:
    """The receipt record of an attached set, for byte comparisons."""
    return attached.receipt.as_record()


def warrant_set(series_key: str = SERIES, kind: str = "warrant", status: str = "outstanding"):
    """The common fixture: one resolved instrument plus its derived id."""
    instrument_id, instrument = instrument_for(series_key, kind=kind, status=status)
    return instrument_id, set_for((instrument_id, instrument))


def assert_receipt(attached: c.InstrumentSet, base: c.InstrumentSet, *, term_ids, binding_ids,
                   unattached=(), superseded=(), superseded_bindings=(), as_of: str = AS_OF) -> None:
    """Pin the C7 receipt inputs exactly, by rebuilding the receipt from them."""
    receipt = expected_receipt(
        base,
        term_ids=term_ids,
        binding_ids=binding_ids,
        unattached=unattached,
        superseded=superseded,
        superseded_bindings=superseded_bindings,
        as_of=as_of,
    )
    assert attached.receipt == receipt
    assert attached.receipt.receipt_id == receipt.receipt_id
    assert attached.receipt.scenario_id is None
    assert attached.receipt.computed_at == as_of


# ---------------------------------------------------------------------------
# §2 — the closed pre-instrument term record
# ---------------------------------------------------------------------------


def test_contract_term_record_quantity_validates_and_is_deep_copied():
    record = term_record("exercise_price", value="1.00")
    validated = validate_economic_term_record(record)
    assert validated == record
    assert validated is not record
    validated["value"] = "9.99"
    validated["evidence"]["span_id"] = "span:mutated"
    assert record["value"] == "1.00"
    assert record["evidence"]["span_id"] == "span:exercise_price"
    assert set(TERM_RECORD_KEYS) == set(record)


def test_contract_term_record_flag_and_date_shapes_validate():
    flag = validate_economic_term_record(term_record("cash_exercise_permitted", flag=True))
    assert flag["flag"] is True
    assert flag["unit"] is None and flag["currency"] is None and flag["value"] is None
    expiry = validate_economic_term_record(term_record("expiry", date_value="2029-06-01"))
    assert expiry["date_value"] == "2029-06-01"
    assert expiry["unit"] is None and expiry["currency"] is None
    assert expiry["value"] is None and expiry["flag"] is None


def test_contract_term_record_deferred_validates_and_carries_no_fact():
    record = validate_economic_term_record(term_record("exercise_price", status="deferred"))
    assert record["status"] == "deferred"
    assert record["extraction"]["method"] == "deferred"
    assert record["value"] is None and record["expression"] is None
    assert record["flag"] is None and record["date_value"] is None
    assert record["unit"] == "usd" and record["currency"] == "USD"


def test_contract_term_record_is_closed():
    record = term_record("exercise_price", value="1.00")
    with pytest.raises(c.ContractViolation, match="unexpected keys"):
        validate_economic_term_record({**record, "overhang": "5000000"})
    with pytest.raises(c.ContractViolation, match="missing keys"):
        validate_economic_term_record({key: value for key, value in record.items() if key != "status"})
    with pytest.raises(c.ContractViolation, match="unexpected keys"):
        validate_economic_term_record({**record, "evidence": {**record["evidence"], "page": "42"}})


def test_contract_term_record_refuses_every_identity_key_at_any_depth():
    record = term_record("exercise_price", value="1.00")
    for key in sorted(INSTRUMENT_IDENTITY_KEYS):
        with pytest.raises(c.ContractViolation, match=key):
            validate_economic_term_record({**record, key: "x:1"})
        nested = deepcopy(record)
        nested["evidence"][key] = "x:1"
        with pytest.raises(c.ContractViolation, match=key):
            validate_economic_term_record(nested)


def test_float_refusal_record_term_value():
    with pytest.raises(c.ContractViolation, match="decimal strings only"):
        validate_economic_term_record(term_record("exercise_price", value=1.5))
    with pytest.raises(c.ContractViolation, match="decimal strings only"):
        validate_economic_term_record(term_record("instruments_outstanding", value=2000000))
    with pytest.raises(c.ContractViolation, match="decimal strings only"):
        validate_economic_term_record(term_record("beneficial_ownership_cap", value=Decimal("9.99")))
    nested = term_record("exercise_price", value="1.00")
    nested["point_in_time"]["event_time"] = 1750000000.5
    with pytest.raises(c.ContractViolation, match="decimal strings only"):
        validate_economic_term_record(nested)


def test_contract_term_record_refuses_an_exponent_or_a_negative_value():
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        validate_economic_term_record(term_record("exercise_price", value="1e3"))
    with pytest.raises(c.ContractViolation, match="nonnegative"):
        validate_economic_term_record(term_record("exercise_price", value="-1.00"))


def test_contract_term_record_occurrence_id_is_the_evidence_digest():
    record = term_record("exercise_price", value="1.00", span="span:price-1", parser_version="1.2.0")
    expected = c.stable_id(
        "econterm",
        {"manifest_id": "manifest:1", "span_id": "span:price-1", "name": "exercise_price", "parser_version": "1.2.0"},
    )
    assert record["occurrence_id"] == expected
    other = c.stable_id(
        "econterm",
        {"manifest_id": "manifest:1", "span_id": "span:price-2", "name": "exercise_price", "parser_version": "1.2.0"},
    )
    with pytest.raises(c.ContractViolation, match="evidence digest"):
        validate_economic_term_record({**record, "occurrence_id": other})


def test_contract_term_record_unit_and_currency_follow_the_name():
    with pytest.raises(c.ContractViolation, match="unit"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", unit="shares"))
    with pytest.raises(c.ContractViolation, match="currency"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", currency=None))
    with pytest.raises(c.ContractViolation, match="carries no unit"):
        validate_economic_term_record(term_record("cash_exercise_permitted", flag=True, unit="usd"))
    record = validate_economic_term_record(term_record("instruments_outstanding", value="2000000"))
    # The share basis is NOT a record field: it comes from the vocabulary.
    assert "share_basis" not in record
    assert record["unit"] == "shares" and record["currency"] is None
    assert c.ECONOMIC_TERM_UNITS["instruments_outstanding"] == ("shares", "assumed_as_converted")
    assert c.ECONOMIC_TERM_UNITS["resale_registered_shares"] == ("shares", "potentially_resalable_existing")


def test_contract_term_record_percent_value_is_percentage_points():
    assert validate_economic_term_record(term_record("beneficial_ownership_cap", value="9.99"))["value"] == "9.99"
    assert Decimal("9.99") / Decimal(100) == Decimal("0.0999")
    assert validate_economic_term_record(term_record("beneficial_ownership_cap", value="100"))["value"] == "100"
    with pytest.raises(c.ContractViolation, match="percentage points"):
        validate_economic_term_record(term_record("beneficial_ownership_cap", value="0"))
    with pytest.raises(c.ContractViolation, match="percentage points"):
        validate_economic_term_record(term_record("beneficial_ownership_cap", value="100.01"))


def test_contract_term_record_method_and_status_must_pair():
    with pytest.raises(c.ContractViolation, match="requires status"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", method="deferred"))
    with pytest.raises(c.ContractViolation, match="requires status"):
        validate_economic_term_record(term_record("exercise_price", status="deferred", method="deterministic"))
    with pytest.raises(c.ContractViolation, match="extraction.method"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", method="model_read"))


def test_contract_term_record_deferred_carries_no_fact():
    with pytest.raises(c.ContractViolation, match="carries no fact"):
        validate_economic_term_record(term_record("exercise_price", status="deferred", value="1.00"))
    with pytest.raises(c.ContractViolation, match="carries no fact"):
        validate_economic_term_record(term_record("exercise_price", status="deferred", expression="90% of VWAP"))
    with pytest.raises(c.ContractViolation, match="carries no fact"):
        validate_economic_term_record(term_record("cash_exercise_permitted", status="deferred", flag=False))


def test_contract_term_record_observed_quantity_carries_exactly_one_of_value_or_expression():
    with pytest.raises(c.ContractViolation, match="exactly one of value or expression"):
        validate_economic_term_record(term_record("exercise_price"))
    with pytest.raises(c.ContractViolation, match="exactly one of value or expression"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", expression="90% of VWAP"))
    formula = validate_economic_term_record(term_record("exercise_price", expression="the lower of $1.00 and 90% of VWAP"))
    assert formula["value"] is None and formula["expression"] == "the lower of $1.00 and 90% of VWAP"


def test_contract_term_record_observed_flag_and_date_carry_only_their_own_payload():
    with pytest.raises(c.ContractViolation, match="carries its boolean"):
        validate_economic_term_record(term_record("cash_exercise_permitted"))
    with pytest.raises(c.ContractViolation, match="carries no unit"):
        validate_economic_term_record(term_record("cash_exercise_permitted", flag=True, value="1.00", unit="usd", currency="USD"))
    with pytest.raises(c.ContractViolation, match="carries no quantity"):
        validate_economic_term_record(term_record("cash_exercise_permitted", flag=True, value="1.00"))
    with pytest.raises(c.ContractViolation, match="carries its ISO date"):
        validate_economic_term_record(term_record("expiry"))


def test_contract_term_record_origin_is_canonical_or_gold_only():
    assert dict(EXTRACTION_METHOD_ORIGINS) == {
        "deterministic": "canonical_extraction",
        "deferred": "canonical_extraction",
    }
    for method, origin in sorted(EXTRACTION_METHOD_ORIGINS.items()):
        status = "observed" if method == "deterministic" else "deferred"
        payload = {"value": "1.00"} if status == "observed" else {}
        record = term_record("exercise_price", method=method, status=status, fact_origin=origin, **payload)
        assert validate_economic_term_record(record)["fact_origin"] == origin
    gold = term_record("exercise_price", value="1.00", fact_origin="adjudicated_gold")
    assert validate_economic_term_record(gold)["fact_origin"] == "adjudicated_gold"
    for origin in ("model_narrative", "issuer_assertion", "llm_span", "canonical", "prophet"):
        with pytest.raises(c.ContractViolation):
            validate_economic_term_record(term_record("exercise_price", value="1.00", fact_origin=origin))


def test_contract_term_record_evidence_sha_is_lowercase_hex():
    with pytest.raises(c.ContractViolation, match="lowercase hex"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", text_sha256=HASH_UPPER))
    with pytest.raises(c.ContractViolation, match="lowercase hex"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", text_sha256="a" * 63))


def test_contract_term_record_requires_an_available_instant():
    with pytest.raises(c.ContractViolation, match="available_at"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", available_at=None))
    with pytest.raises(c.ContractViolation, match="timezone"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", available_at="2026-06-02T00:00:00"))
    undated = validate_economic_term_record(term_record("exercise_price", value="1.00", event_time=None))
    assert undated["point_in_time"]["event_time"] is None


def test_contract_term_record_date_value_is_an_iso_date():
    with pytest.raises(c.ContractViolation, match="ISO date"):
        validate_economic_term_record(term_record("expiry", date_value="June 2029"))
    with pytest.raises(c.ContractViolation, match="carries no date"):
        validate_economic_term_record(term_record("exercise_price", value="1.00", date_value="2029-06-01"))


# ---------------------------------------------------------------------------
# §3 — the adjudicated-gold binding record
# ---------------------------------------------------------------------------


def test_contract_binding_validates_and_its_id_is_the_digest():
    record = term_record("exercise_price", value="1.00")
    binding_record = binding(record["occurrence_id"])
    expected_id = c.stable_id(
        "termbind",
        {"occurrence_id": record["occurrence_id"], "instrument_id": instrument_id_for(ISSUER, SERIES)},
    )
    assert binding_record["binding_id"] == expected_id
    assert validate_term_binding(binding_record) == binding_record
    assert set(BINDING_RECORD_KEYS) == set(binding_record)
    with pytest.raises(c.ContractViolation, match="digest"):
        validate_term_binding({**binding_record, "binding_id": expected_id[:-1] + "0"})


def test_contract_binding_is_closed():
    record = binding("econterm:cs:00000000000000000000000000000000")
    with pytest.raises(c.ContractViolation, match="unexpected keys"):
        validate_term_binding({**record, "outstanding_quantity": "1000"})
    with pytest.raises(c.ContractViolation, match="missing keys"):
        validate_term_binding({key: value for key, value in record.items() if key != "supersedes"})


def test_contract_binding_requires_the_gold_origin():
    for origin in ("canonical_extraction", "model_narrative", "issuer_assertion"):
        with pytest.raises(c.ContractViolation, match="adjudicated_gold"):
            validate_term_binding(binding("econterm:cs:00000000000000000000000000000000", fact_origin=origin))


def test_contract_binding_instrument_id_must_be_the_derived_identity():
    with pytest.raises(c.ContractViolation, match="instrument_id_for"):
        validate_term_binding(binding("econterm:cs:00000000000000000000000000000000", instrument_id="inst:invented"))
    moved = binding("econterm:cs:00000000000000000000000000000000", series_key=OTHER_SERIES)
    assert moved["instrument_id"] == instrument_id_for(ISSUER, OTHER_SERIES)
    assert validate_term_binding(moved)["series_key"] == OTHER_SERIES


def test_contract_binding_evidence_is_non_empty_and_retained():
    occurrence = "econterm:cs:00000000000000000000000000000000"
    with pytest.raises(c.ContractViolation, match="non-empty"):
        validate_term_binding(binding(occurrence, evidence=[]))
    with pytest.raises(c.ContractViolation, match="lowercase hex"):
        validate_term_binding(
            binding(occurrence, evidence=[{"manifest_id": "manifest:9", "span_id": "span:9", "text_sha256": HASH_UPPER}])
        )
    with pytest.raises(c.ContractViolation, match="unexpected keys"):
        validate_term_binding(
            binding(occurrence, evidence=[{"manifest_id": "manifest:9", "span_id": "span:9", "text_sha256": HASH, "page": "4"}])
        )


def test_contract_binding_supersedes_is_a_list_of_ids():
    occurrence = "econterm:cs:00000000000000000000000000000000"
    prior = "termbind:cs:11111111111111111111111111111111"
    record = binding(occurrence, supersedes=[prior])
    assert validate_term_binding(record)["supersedes"] == [prior]
    assert validate_term_binding(binding(occurrence))["supersedes"] == []
    with pytest.raises(c.ContractViolation, match="may not supersede itself"):
        validate_term_binding(binding(occurrence, supersedes=[binding(occurrence)["binding_id"]]))
    with pytest.raises(c.ContractViolation, match="identifier required"):
        validate_term_binding(binding(occurrence, supersedes=["not an id"]))
    with pytest.raises(c.ContractViolation, match="duplicate binding ids"):
        validate_term_binding(binding(occurrence, supersedes=[prior, prior]))


def test_float_refusal_record_binding():
    occurrence = "econterm:cs:00000000000000000000000000000000"
    record = binding(occurrence)
    record["decided_at"] = 1750000000.0
    with pytest.raises(c.ContractViolation, match="decimal strings only"):
        validate_term_binding(record)
    nested = binding(occurrence)
    nested["evidence"][0]["span_id"] = 7.5
    with pytest.raises(c.ContractViolation, match="decimal strings only"):
        validate_term_binding(nested)


# ---------------------------------------------------------------------------
# §4 — attachment: visibility, grouping, unattached reasons and the receipt
# ---------------------------------------------------------------------------


def bound(name: str, series_key: str = SERIES, **over) -> tuple[dict, dict]:
    """One visible occurrence plus the adjudicated-gold binding that attaches it."""
    record = term_record(name, **over)
    return record, binding(record["occurrence_id"], series_key=series_key)


def sort_unattached(items) -> list:
    return sorted(
        (dict(item) for item in items),
        key=lambda item: (item["binding_id"], item["instrument_id"], item["reason"]),
    )


def sort_superseded(items) -> list:
    return sorted(
        (dict(item) for item in items),
        key=lambda item: (item["instrument_id"], item["name"], item["occurrence_id"], item["effective_at"] or ""),
    )


def test_attach_canonical_and_gold_origins_both_attach():
    instrument_id, base = warrant_set()
    canonical, canonical_binding = bound("exercise_price", value="1.00")
    gold = term_record("shares_per_instrument", value="1", span="span:gold", fact_origin="adjudicated_gold")
    attached = attach(base, [gold, canonical], [binding(gold["occurrence_id"]), canonical_binding])
    terms = terms_of(attached, instrument_id)
    assert sorted(terms) == ["exercise_price", "shares_per_instrument"]
    assert terms["exercise_price"].fact_origin == "canonical_extraction"
    assert terms["exercise_price"].value.decimal == Decimal("1.00")
    assert terms["shares_per_instrument"].fact_origin == "adjudicated_gold"
    assert terms["shares_per_instrument"].value.unit == "ratio"
    assert terms["shares_per_instrument"].value.share_basis is None


def test_attach_a_group_with_a_gold_member_is_gold_and_joins_parser_versions():
    instrument_id, base = warrant_set()
    canonical, canonical_binding = bound("exercise_price", value="1.00", span="span:a")
    gold = term_record("exercise_price", value="1.00", span="span:b", parser_version="1.1.0", fact_origin="adjudicated_gold")
    attached = attach(base, [gold, canonical], [canonical_binding, binding(gold["occurrence_id"])])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "admitted"
    assert term.fact_origin == "adjudicated_gold"
    assert term.interpretation_version == "1.0.0+1.1.0"
    assert term.term_id == min(canonical["occurrence_id"], gold["occurrence_id"])
    assert term.available_at == AVAILABLE
    assert term.effective_at == EFFECTIVE
    assert [(item.manifest_id, item.span_id, item.text_sha256) for item in term.evidence] == [
        ("manifest:1", "span:a", HASH),
        ("manifest:1", "span:b", HASH),
    ]


def test_attach_model_origin_is_refused_before_anything_attaches():
    _instrument_id, base = warrant_set()
    for origin in ("model_narrative", "issuer_assertion", "model_estimate"):
        prose = term_record("exercise_price", value="1.00", fact_origin=origin)
        with pytest.raises(c.ContractViolation, match="fact_origin"):
            attach(base, [prose], [binding(prose["occurrence_id"])])
    # Even a well-formed binding cannot launder a prose occurrence.
    prose = term_record("exercise_price", value="1.00", fact_origin="model_narrative")
    with pytest.raises(c.ContractViolation, match="fact_origin"):
        attach(base, [term_record("notice_days", value="30"), prose], [binding(prose["occurrence_id"])])


def test_attach_identity_key_is_refused_at_any_depth():
    _instrument_id, base = warrant_set()
    for key in sorted(INSTRUMENT_IDENTITY_KEYS):
        smuggled = term_record("exercise_price", value="1.00")
        smuggled[key] = "inst:smuggled"
        with pytest.raises(c.ContractViolation, match=key):
            attach(base, [smuggled], [])
        nested = term_record("exercise_price", value="1.00")
        nested["evidence"][key] = "inst:smuggled"
        with pytest.raises(c.ContractViolation, match=key):
            attach(base, [nested], [])


def test_attach_conflict_with_the_same_effective_instant_is_one_contradicted_term():
    instrument_id, base = warrant_set()
    first, first_binding = bound("exercise_price", value="1.00", span="span:a", available_at="2026-06-02T00:00:00Z")
    second, second_binding = bound("exercise_price", value="1.50", span="span:b", available_at="2026-07-02T00:00:00Z")
    attached = attach(base, [second, first], [second_binding, first_binding])
    terms = terms_of(attached, instrument_id)
    assert sorted(terms) == ["exercise_price"]
    term = terms["exercise_price"]
    assert term.status == "contradicted"
    assert term.term_id == c.stable_id(
        "econterm-conflict", sorted([first["occurrence_id"], second["occurrence_id"]])
    )
    assert term.value.status == "contradicted"
    assert term.value.value is None
    assert term.expression is None and term.flag is None and term.date_value is None
    assert term.available_at == "2026-07-02T00:00:00Z"
    assert term.effective_at == EFFECTIVE
    assert [(item.manifest_id, item.span_id) for item in term.evidence] == [
        ("manifest:1", "span:a"),
        ("manifest:1", "span:b"),
    ]
    assert_receipt(
        attached,
        base,
        term_ids=sorted([first["occurrence_id"], second["occurrence_id"]]),
        binding_ids=sorted([first_binding["binding_id"], second_binding["binding_id"]]),
    )


def test_attach_later_effective_value_wins_and_the_earlier_one_is_receipt_history():
    instrument_id, base = warrant_set()
    old, old_binding = bound("exercise_price", value="1.00", span="span:old", event_time="2025-01-02T00:00:00Z")
    new, new_binding = bound("exercise_price", value="0.50", span="span:new", event_time="2026-06-01T00:00:00Z")
    attached = attach(base, [old, new], [old_binding, new_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "admitted"
    assert term.value.decimal == Decimal("0.50")
    assert term.term_id == new["occurrence_id"]
    assert term.effective_at == "2026-06-01T00:00:00Z"
    assert term.available_at == AVAILABLE
    assert_receipt(
        attached,
        base,
        term_ids=sorted([old["occurrence_id"], new["occurrence_id"]]),
        binding_ids=sorted([old_binding["binding_id"], new_binding["binding_id"]]),
        superseded=sort_superseded(
            [
                {
                    "instrument_id": instrument_id,
                    "name": "exercise_price",
                    "occurrence_id": old["occurrence_id"],
                    "effective_at": "2025-01-02T00:00:00Z",
                }
            ]
        ),
    )
    # A27-compatible: supersession is receipt history, never a mutation or a
    # deletion.  A receipt that dropped the superseded occurrence is a different
    # receipt, and the occurrence is still named among the visible term ids.
    assert expected_receipt(
        base,
        term_ids=sorted([old["occurrence_id"], new["occurrence_id"]]),
        binding_ids=sorted([old_binding["binding_id"], new_binding["binding_id"]]),
        unattached=[],
        superseded=[],
        superseded_bindings=[],
    ) != attached.receipt


def test_attach_the_latest_effective_instant_stating_two_values_is_contradicted():
    instrument_id, base = warrant_set()
    old, old_binding = bound("exercise_price", value="1.00", span="span:old", event_time="2025-01-02T00:00:00Z")
    left, left_binding = bound("exercise_price", value="0.50", span="span:left", event_time="2026-06-01T00:00:00Z")
    right, right_binding = bound("exercise_price", value="0.75", span="span:right", event_time="2026-06-01T00:00:00Z")
    attached = attach(base, [old, right, left], [old_binding, right_binding, left_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "contradicted"
    assert term.term_id == c.stable_id("econterm-conflict", sorted([left["occurrence_id"], right["occurrence_id"]]))
    assert term.effective_at == "2026-06-01T00:00:00Z"
    assert_receipt(
        attached,
        base,
        term_ids=sorted([old["occurrence_id"], left["occurrence_id"], right["occurrence_id"]]),
        binding_ids=sorted([old_binding["binding_id"], left_binding["binding_id"], right_binding["binding_id"]]),
        superseded=sort_superseded(
            [
                {
                    "instrument_id": instrument_id,
                    "name": "exercise_price",
                    "occurrence_id": old["occurrence_id"],
                    "effective_at": "2025-01-02T00:00:00Z",
                }
            ]
        ),
    )


def test_attach_values_that_cannot_be_ordered_are_one_contradicted_term():
    instrument_id, base = warrant_set()
    dated, dated_binding = bound("instruments_outstanding", value="1000000", span="span:dated")
    undated, undated_binding = bound("instruments_outstanding", value="1200000", span="span:undated", event_time=None)
    attached = attach(base, [undated, dated], [undated_binding, dated_binding])
    term = terms_of(attached, instrument_id)["instruments_outstanding"]
    assert term.status == "contradicted"
    assert term.effective_at is None
    assert term.value.status == "contradicted"
    assert term.value.unit == "shares"
    assert term.value.share_basis == "assumed_as_converted"
    assert_receipt(attached, base, term_ids=sorted([dated["occurrence_id"], undated["occurrence_id"]]),
                   binding_ids=sorted([dated_binding["binding_id"], undated_binding["binding_id"]]))


def test_attach_deferred_bytes_are_an_unknown_term_never_a_number():
    instrument_id, base = warrant_set()
    record, record_binding = bound("exercise_price", status="deferred")
    assert record["extraction"]["method"] == "deferred"
    assert record["value"] is None
    attached = attach(base, [record], [record_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "unknown"
    assert term.value.status == "unknown"
    assert term.value.value is None
    assert term.value.unit == "usd"
    assert term.term_id == record["occurrence_id"]
    assert term.effective_at is None
    assert [(item.manifest_id, item.span_id) for item in term.evidence] == [("manifest:1", "span:exercise_price")]


def test_attach_a_deferred_record_does_not_outvote_an_observed_one():
    instrument_id, base = warrant_set()
    observed, observed_binding = bound("exercise_price", value="1.00", span="span:observed")
    deferred = term_record("exercise_price", status="deferred", span="span:deferred")
    attached = attach(base, [deferred, observed], [observed_binding, binding(deferred["occurrence_id"])])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "admitted"
    assert term.value.decimal == Decimal("1.00")
    assert term.term_id == observed["occurrence_id"]


def test_attach_an_undated_price_is_deferred_not_a_timeless_number():
    instrument_id, base = warrant_set()
    record, record_binding = bound("exercise_price", value="1.00", event_time=None)
    assert record["status"] == "observed"
    attached = attach(base, [record], [record_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "unknown"
    assert term.value.status == "unknown"
    assert term.value.value is None
    assert term.effective_at is None


def test_attach_an_expression_price_admits_the_formula_without_a_number():
    instrument_id, base = warrant_set()
    formula = "the greater of $1.00 and 90% of the ten trading day VWAP"
    record, record_binding = bound("exercise_price", value=None, expression=formula)
    attached = attach(base, [record], [record_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "admitted"
    assert term.expression == formula
    assert term.value.status == "unknown"
    assert term.value.value is None
    assert term.effective_at == EFFECTIVE


def test_attach_evidence_is_a_deduplicated_sorted_union():
    instrument_id, base = warrant_set()
    first, first_binding = bound("notice_days", value="30", span="span:same", text_sha256=GOLD_HASH)
    second = term_record("notice_days", value="30", span="span:same", text_sha256=GOLD_HASH, parser_version="1.1.0")
    attached = attach(base, [first, second], [first_binding, binding(second["occurrence_id"])])
    term = terms_of(attached, instrument_id)["notice_days"]
    assert term.status == "admitted"
    assert term.value.decimal == Decimal("30")
    assert term.value.unit == "days"
    assert [(item.manifest_id, item.span_id, item.text_sha256) for item in term.evidence] == [
        ("manifest:1", "span:same", GOLD_HASH)
    ]
    assert term.interpretation_version == "1.0.0+1.1.0"


def test_attach_a_binding_to_a_retired_instrument_is_unattached():
    retired_id, retired = instrument_for(SERIES, status="retired")
    base = set_for((retired_id, retired))
    record, record_binding = bound("exercise_price", value="1.00")
    attached = attach(base, [record], [record_binding])
    assert terms_of(attached, retired_id) == {}
    assert attached.instruments[0] is base.instruments[0]
    assert_receipt(
        attached,
        base,
        term_ids=[record["occurrence_id"]],
        binding_ids=[record_binding["binding_id"]],
        unattached=sort_unattached(
            [{"binding_id": record_binding["binding_id"], "instrument_id": retired_id, "reason": "retired"}]
        ),
    )


def test_attach_a_binding_to_an_unresolved_candidate_is_unattached():
    candidate_id, candidate = instrument_for(SERIES, status="unresolved_candidate")
    base = set_for((candidate_id, candidate))
    record, record_binding = bound("exercise_price", value="1.00")
    attached = attach(base, [record], [record_binding])
    assert terms_of(attached, candidate_id) == {}
    assert_receipt(
        attached,
        base,
        term_ids=[record["occurrence_id"]],
        binding_ids=[record_binding["binding_id"]],
        unattached=sort_unattached(
            [{"binding_id": record_binding["binding_id"], "instrument_id": candidate_id, "reason": "unresolved_candidate"}]
        ),
    )


def test_attach_a_binding_to_an_absent_instrument_is_unattached():
    _instrument_id, base = warrant_set()
    absent_series = "series_absent_2026_01"
    record, record_binding = bound("exercise_price", value="1.00", series_key=absent_series)
    assert record_binding["instrument_id"] == instrument_id_for(ISSUER, absent_series)
    attached = attach(base, [record], [record_binding])
    assert_receipt(
        attached,
        base,
        term_ids=[record["occurrence_id"]],
        binding_ids=[record_binding["binding_id"]],
        unattached=sort_unattached(
            [
                {
                    "binding_id": record_binding["binding_id"],
                    "instrument_id": instrument_id_for(ISSUER, absent_series),
                    "reason": "absent",
                }
            ]
        ),
    )


def test_attach_one_occurrence_bound_to_two_instruments_attaches_to_neither():
    first_id, first = instrument_for(SERIES)
    second_id, second = instrument_for(OTHER_SERIES)
    base = set_for((first_id, first), (second_id, second))
    record = term_record("exercise_price", value="1.00")
    to_first = binding(record["occurrence_id"], series_key=SERIES)
    to_second = binding(record["occurrence_id"], series_key=OTHER_SERIES)
    attached = attach(base, [record], [to_second, to_first])
    assert terms_of(attached, first_id) == {}
    assert terms_of(attached, second_id) == {}
    assert attached.instruments[0] is base.instruments[0]
    assert attached.instruments[1] is base.instruments[1]
    assert_receipt(
        attached,
        base,
        term_ids=[record["occurrence_id"]],
        binding_ids=sorted([to_first["binding_id"], to_second["binding_id"]]),
        unattached=sort_unattached(
            [
                {"binding_id": to_first["binding_id"], "instrument_id": first_id, "reason": "ambiguous_binding"},
                {"binding_id": to_second["binding_id"], "instrument_id": second_id, "reason": "ambiguous_binding"},
            ]
        ),
    )
    assert set(UNATTACHED_REASONS) == {
        "ambiguous_binding",
        "occurrence_not_visible",
        "retired",
        "unresolved_candidate",
        "absent",
    }
    assert set(ATTACHABLE_INSTRUMENT_STATUSES) == {"outstanding", "amended"}


def test_attach_point_in_time_hides_a_term_available_after_as_of():
    instrument_id, base = warrant_set()
    record, record_binding = bound("exercise_price", value="1.00", available_at="2026-11-01T00:00:00Z")
    attached = attach(base, [record], [record_binding])
    assert terms_of(attached, instrument_id) == {}
    assert attached.instruments[0] is base.instruments[0]
    assert_receipt(
        attached,
        base,
        term_ids=[],
        binding_ids=[record_binding["binding_id"]],
        unattached=sort_unattached(
            [
                {
                    "binding_id": record_binding["binding_id"],
                    "instrument_id": instrument_id,
                    "reason": "occurrence_not_visible",
                }
            ]
        ),
    )


def test_attach_a_binding_decided_or_effective_after_as_of_is_invisible():
    instrument_id, base = warrant_set()
    record, _record_binding = bound("exercise_price", value="1.00")
    for over in ({"decided_at": "2026-11-01T00:00:00Z"}, {"effective_at": "2026-11-01T00:00:00Z"}):
        late = binding(record["occurrence_id"], **over)
        attached = attach(base, [record], [late])
        assert terms_of(attached, instrument_id) == {}
        assert_receipt(attached, base, term_ids=[record["occurrence_id"]], binding_ids=[])


def test_attach_timestamps_compare_as_instants_not_as_strings():
    instrument_id, base = warrant_set()
    record, _record_binding = bound("exercise_price", value="1.00")
    # As text "2026-10-13T13:00:00+02:00" sorts AFTER the as_of "2026-10-13T12:00:00Z",
    # but as an instant it is 11:00:00Z, so the binding is visible (C2).
    offset = binding(
        record["occurrence_id"],
        decided_at="2026-10-13T13:00:00+02:00",
        effective_at="2026-10-13T13:00:00+02:00",
    )
    attached = attach(base, [record], [offset])
    assert terms_of(attached, instrument_id)["exercise_price"].value.decimal == Decimal("1.00")


def test_attach_supersedes_drops_the_named_binding():
    instrument_id, base = warrant_set()
    old, _old_binding = bound("exercise_price", value="1.00", span="span:old")
    new, _new_binding = bound("exercise_price", value="0.50", span="span:new")
    old_binding = binding(old["occurrence_id"])
    new_binding = binding(new["occurrence_id"], supersedes=[old_binding["binding_id"]])
    attached = attach(base, [old, new], [old_binding, new_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "admitted"
    assert term.value.decimal == Decimal("0.50")
    assert term.term_id == new["occurrence_id"]
    assert_receipt(
        attached,
        base,
        term_ids=sorted([old["occurrence_id"], new["occurrence_id"]]),
        binding_ids=[new_binding["binding_id"]],
        superseded_bindings=[old_binding["binding_id"]],
    )


def test_attach_an_invisible_binding_supersedes_nothing():
    instrument_id, base = warrant_set()
    old, _old_binding = bound("exercise_price", value="1.00", span="span:old")
    new, _new_binding = bound("exercise_price", value="0.50", span="span:new")
    old_binding = binding(old["occurrence_id"])
    future = binding(new["occurrence_id"], decided_at="2026-12-01T00:00:00Z", supersedes=[old_binding["binding_id"]])
    attached = attach(base, [old, new], [old_binding, future])
    assert terms_of(attached, instrument_id)["exercise_price"].value.decimal == Decimal("1.00")
    assert_receipt(
        attached,
        base,
        term_ids=sorted([old["occurrence_id"], new["occurrence_id"]]),
        binding_ids=[old_binding["binding_id"]],
        superseded_bindings=[],
    )


def test_attach_as_of_later_than_the_identity_snapshot_is_refused():
    _instrument_id, base = warrant_set()
    record, record_binding = bound("exercise_price", value="1.00")
    with pytest.raises(c.ContractViolation, match="later than the instrument snapshot"):
        attach_economic_terms(base, [record], [record_binding], "2026-10-13T12:00:01Z")
    assert attach(base, [record], [record_binding], AS_OF).instruments[0].economic_terms


def test_attach_records_of_another_issuer_are_refused():
    _instrument_id, base = warrant_set()
    foreign_term = term_record("exercise_price", value="1.00", issuer_id="cik:0009999999")
    with pytest.raises(c.ContractViolation, match="differs from the instrument set issuer"):
        attach(base, [foreign_term], [])
    foreign_binding = binding(
        "econterm:cs:00000000000000000000000000000000", issuer_id="cik:0009999999", series_key=SERIES
    )
    assert foreign_binding["instrument_id"] != instrument_id_for(ISSUER, SERIES)
    with pytest.raises(c.ContractViolation, match="differs from the instrument set issuer"):
        attach(base, [], [foreign_binding])


def test_attach_an_instrument_that_receives_no_term_is_byte_identical():
    first_id, first = instrument_for(SERIES)
    second_id, second = instrument_for(OTHER_SERIES)
    base = set_for((first_id, first), (second_id, second))
    record, record_binding = bound("exercise_price", value="1.00")
    attached = attach(base, [record], [record_binding])
    assert [item.instrument_id for item in attached.instruments] == [first_id, second_id]
    assert attached.instruments[1] is base.instruments[1]
    assert attached.instruments[1].as_record() == base.instruments[1].as_record()
    assert c.sha256_of(attached.instruments[1].as_record()) == c.sha256_of(base.instruments[1].as_record())
    assert attached.instruments[0] is not base.instruments[0]
    assert "economic_terms" not in attached.instruments[1].as_record()


def test_attach_terms_are_sorted_by_name_then_term_id():
    _instrument_id, base = warrant_set()
    records, bindings = [], []
    for name, over in (
        ("shares_per_instrument", {"value": "1"}),
        ("exercise_price", {"value": "1.00"}),
        ("notice_days", {"value": "30"}),
        ("cash_exercise_permitted", {"flag": True}),
        ("expiry", {"date_value": "2029-06-01"}),
    ):
        record, record_binding = bound(name, **over)
        records.append(record)
        bindings.append(record_binding)
    attached = attach(base, records, bindings)
    names = [term.name for term in attached.instruments[0].economic_terms]
    assert names == sorted(names)
    assert names == [
        "cash_exercise_permitted",
        "exercise_price",
        "expiry",
        "notice_days",
        "shares_per_instrument",
    ]
    expiry = terms_of(attached, attached.instruments[0].instrument_id)["expiry"]
    assert expiry.date_value == "2029-06-01"
    assert expiry.value is None
    permission = terms_of(attached, attached.instruments[0].instrument_id)["cash_exercise_permitted"]
    assert permission.flag is True
    assert permission.value is None


def test_attach_receipt_inputs_are_the_c7_keys_exactly():
    _instrument_id, base = warrant_set()
    record, record_binding = bound("exercise_price", value="1.00")
    attached = attach(base, [record], [record_binding])
    assert_receipt(attached, base, term_ids=[record["occurrence_id"]], binding_ids=[record_binding["binding_id"]])
    assert attached.receipt != base.receipt
    assert attached.receipt.rule_digest == c.sha256_of(c.ECONOMIC_TERM_NAMES)
    assert attached.receipt.computed_at == AS_OF
    assert attached.receipt.scenario_id is None
    renamed = {
        "instrument_set_receipt_id": base.receipt.receipt_id,
        "as_of": AS_OF,
        "term_ids": [record["occurrence_id"]],
        "binding_ids": [record_binding["binding_id"]],
        "unattached": [],
        "superseded": [],
        "detached_bindings": [],
    }
    dropped = {key: value for key, value in renamed.items() if key != "detached_bindings"}
    dropped.pop("superseded")
    for mutated in (renamed, dropped):
        assert c.CalculationReceipt.build(
            inputs=mutated,
            rule_digest=c.sha256_of(c.ECONOMIC_TERM_NAMES),
            implementation=IMPLEMENTATION,
            computed_at=AS_OF,
        ) != attached.receipt


def test_attach_receipt_input_lists_are_sorted_not_input_ordered():
    first_id, first = instrument_for(SERIES)
    retired_id, retired = instrument_for(OTHER_SERIES, status="retired")
    base = set_for((first_id, first), (retired_id, retired))
    old, _old_binding = bound("exercise_price", value="1.00", span="span:old", event_time="2025-01-02T00:00:00Z")
    new, _new_binding = bound("exercise_price", value="0.50", span="span:new", event_time="2026-06-01T00:00:00Z")
    notice_old, _notice_old_binding = bound("notice_days", value="60", span="span:notice-old")
    notice_new, _notice_new_binding = bound("notice_days", value="30", span="span:notice-new")
    retired_record, _retired_binding = bound("shares_per_instrument", value="1", series_key=OTHER_SERIES)
    old_binding = binding(old["occurrence_id"])
    new_binding = binding(new["occurrence_id"])
    notice_old_binding = binding(notice_old["occurrence_id"])
    notice_new_binding = binding(notice_new["occurrence_id"], supersedes=[notice_old_binding["binding_id"]])
    retired_binding = binding(retired_record["occurrence_id"], series_key=OTHER_SERIES)
    attached = attach(
        base,
        [new, retired_record, notice_new, old, notice_old],
        [retired_binding, notice_new_binding, new_binding, notice_old_binding, old_binding],
    )
    term_ids = sorted(
        [old["occurrence_id"], new["occurrence_id"], notice_old["occurrence_id"],
         notice_new["occurrence_id"], retired_record["occurrence_id"]]
    )
    binding_ids = sorted(
        [old_binding["binding_id"], new_binding["binding_id"],
         notice_new_binding["binding_id"], retired_binding["binding_id"]]
    )
    unattached = sort_unattached(
        [{"binding_id": retired_binding["binding_id"], "instrument_id": retired_id, "reason": "retired"}]
    )
    superseded = sort_superseded(
        [
            {
                "instrument_id": first_id,
                "name": "exercise_price",
                "occurrence_id": old["occurrence_id"],
                "effective_at": "2025-01-02T00:00:00Z",
            }
        ]
    )
    superseded_bindings = [notice_old_binding["binding_id"]]
    assert_receipt(
        attached,
        base,
        term_ids=term_ids,
        binding_ids=binding_ids,
        unattached=unattached,
        superseded=superseded,
        superseded_bindings=superseded_bindings,
    )
    assert terms_of(attached, first_id)["exercise_price"].value.decimal == Decimal("0.50")
    assert terms_of(attached, first_id)["notice_days"].value.decimal == Decimal("30")
    assert terms_of(attached, retired_id) == {}
    # Every list is pinned as SORTED: the same items in the order they were handed
    # in produce a different receipt, so the output cannot follow the input order.
    for mutated in (
        {"term_ids": list(reversed(term_ids))},
        {"binding_ids": list(reversed(binding_ids))},
        {"unattached": []},
        {"superseded": []},
        {"superseded_bindings": []},
    ):
        assert expected_receipt(
            base,
            term_ids=mutated.get("term_ids", term_ids),
            binding_ids=mutated.get("binding_ids", binding_ids),
            unattached=mutated.get("unattached", unattached),
            superseded=mutated.get("superseded", superseded),
            superseded_bindings=mutated.get("superseded_bindings", superseded_bindings),
        ) != attached.receipt


def test_attach_a_record_claiming_an_occurrence_id_twice_is_refused():
    _instrument_id, base = warrant_set()
    record, _record_binding = bound("exercise_price", value="1.00")
    twin = deepcopy(record)
    twin["value"] = "1.50"
    with pytest.raises(c.ContractViolation, match="two different records claim"):
        attach(base, [record, twin], [])


def test_attach_two_identical_copies_of_one_record_are_one_occurrence():
    instrument_id, base = warrant_set()
    record, record_binding = bound("exercise_price", value="1.00")
    attached = attach(base, [record, deepcopy(record)], [record_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "admitted"
    assert term.value.decimal == Decimal("1.00")
    assert_receipt(attached, base, term_ids=[record["occurrence_id"]], binding_ids=[record_binding["binding_id"]])


def test_attach_values_spelled_differently_but_equal_are_one_value():
    instrument_id, base = warrant_set()
    first, first_binding = bound("exercise_price", value="1.5", span="span:a")
    second, second_binding = bound("exercise_price", value="1.50", span="span:b")
    attached = attach(base, [first, second], [first_binding, second_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "admitted"
    assert term.value.decimal == Decimal("1.5")
    assert term.term_id == min(first["occurrence_id"], second["occurrence_id"])
    assert_receipt(attached, base, term_ids=sorted([first["occurrence_id"], second["occurrence_id"]]),
                   binding_ids=sorted([first_binding["binding_id"], second_binding["binding_id"]]))


def test_attach_two_expressions_are_two_readings_even_when_equivalent():
    instrument_id, base = warrant_set()
    first, first_binding = bound("exercise_price", value=None, expression="the greater of $1.00 and 90% of VWAP", span="span:a")
    second, second_binding = bound("exercise_price", value=None, expression="the greater of $1.00 and 90% of the VWAP", span="span:b")
    attached = attach(base, [first, second], [first_binding, second_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    assert term.status == "contradicted"
    assert term.expression is None


def test_attach_no_records_returns_the_same_instruments_with_a_new_receipt():
    _instrument_id, base = warrant_set()
    attached = attach(base, [], [])
    assert attached.instruments == base.instruments
    assert attached.instruments[0] is base.instruments[0]
    assert attached.receipt != base.receipt
    assert_receipt(attached, base, term_ids=[], binding_ids=[])
    assert attached.issuer_id == base.issuer_id
    assert attached.as_of == base.as_of
    assert attached.provenance == base.provenance


def test_determinism_shuffled_records_and_bindings_give_a_byte_identical_record():
    first_id, first = instrument_for(SERIES)
    retired_id, retired = instrument_for(OTHER_SERIES, status="retired")
    base = set_for((first_id, first), (retired_id, retired))
    records: list[dict] = []
    bindings: list[dict] = []

    def add(record: dict, series_key: str = SERIES, **over) -> dict:
        records.append(record)
        record_binding = binding(record["occurrence_id"], series_key=series_key, **over)
        bindings.append(record_binding)
        return record_binding

    # An admitted price whose earlier reading stays as receipt history.
    superseded_price = term_record("exercise_price", value="2.00", span="span:price-old",
                                   event_time="2025-01-02T00:00:00Z")
    add(superseded_price)
    winner_price = term_record("exercise_price", value="1.00", span="span:price-new",
                               event_time="2026-06-01T00:00:00Z", fact_origin="adjudicated_gold")
    add(winner_price)
    # A ratio superseded at the BINDING level: the older binding is dropped.
    superseded_ratio = term_record("shares_per_instrument", value="2", span="span:ratio-old")
    superseded_ratio_binding = add(superseded_ratio)
    winner_ratio = term_record("shares_per_instrument", value="1", span="span:ratio-new")
    add(winner_ratio, supersedes=[superseded_ratio_binding["binding_id"]])
    # Deferred bytes: an unknown term, never a number.
    deferred = term_record("principal_outstanding", status="deferred", span="span:deferred")
    add(deferred)
    # An occurrence bound to a retired instrument, and one that is not yet visible.
    retired_record = term_record("notice_days", value="30", span="span:retired")
    retired_binding = add(retired_record, series_key=OTHER_SERIES)
    invisible = term_record("conversion_price", value="0.50", span="span:invisible",
                            available_at="2026-12-01T00:00:00Z")
    invisible_binding = add(invisible)

    reference = attach(base, records, bindings)
    reference_record = reference.as_record()
    reference_digest = c.sha256_of(reference_record)
    terms = terms_of(reference, first_id)
    assert terms["exercise_price"].status == "admitted"
    assert terms["exercise_price"].value.decimal == Decimal("1.00")
    assert terms["exercise_price"].fact_origin == "adjudicated_gold"
    assert terms["shares_per_instrument"].value.decimal == Decimal("1")
    assert terms["principal_outstanding"].status == "unknown"
    assert terms_of(reference, retired_id) == {}
    assert_receipt(
        reference,
        base,
        term_ids=sorted(
            record["occurrence_id"]
            for record in records
            if record["point_in_time"]["available_at"] <= AS_OF
        ),
        binding_ids=sorted(
            item["binding_id"]
            for item in bindings
            if item["binding_id"] != superseded_ratio_binding["binding_id"]
        ),
        unattached=sort_unattached(
            [
                {"binding_id": invisible_binding["binding_id"], "instrument_id": first_id,
                 "reason": "occurrence_not_visible"},
                {"binding_id": retired_binding["binding_id"], "instrument_id": retired_id, "reason": "retired"},
            ]
        ),
        superseded=sort_superseded(
            [
                {"instrument_id": first_id, "name": "exercise_price",
                 "occurrence_id": superseded_price["occurrence_id"], "effective_at": "2025-01-02T00:00:00Z"}
            ]
        ),
        superseded_bindings=[superseded_ratio_binding["binding_id"]],
    )

    shuffled_records = list(records)
    shuffled_bindings = list(bindings)
    generator = random.Random(20261014)
    for _attempt in range(24):
        generator.shuffle(shuffled_records)
        generator.shuffle(shuffled_bindings)
        permuted = attach(base, shuffled_records, shuffled_bindings)
        assert permuted.as_record() == reference_record
        assert c.sha256_of(permuted.as_record()) == reference_digest
        assert permuted.receipt == reference.receipt


def test_float_refusal_record_as_of():
    _instrument_id, base = warrant_set()
    with pytest.raises(c.ContractViolation, match="timestamp required"):
        attach(base, [], [], 1760000000.0)


# ---------------------------------------------------------------------------
# Contracts — C0 2.1.0 byte identity, schema and the §0 arity pin
# ---------------------------------------------------------------------------


C0_INSTRUMENT_KEYS = (
    "instrument_id",
    "security_class_id",
    "kind",
    "status",
    "candidate_term_ids",
    "resolution",
    "amendments",
    "outstanding",
    "provenance",
)


def test_contract_arity_of_evaluate_supply_is_three():
    assert list(inspect.signature(evaluate_supply).parameters) == ["instruments", "basis", "scenario"]
    assert list(inspect.signature(supply_trace).parameters) == ["instruments", "basis", "scenario"]


def test_contract_instrument_without_terms_is_byte_identical_to_the_2_0_0_record():
    instrument = T.instrument()
    record = instrument.as_record()
    assert "economic_terms" not in record
    assert tuple(record) == C0_INSTRUMENT_KEYS
    c.validate_state_record("instrument", record)
    rebuilt = dataclasses.replace(instrument, economic_terms=())
    assert rebuilt.as_record() == record
    assert c.sha256_of(rebuilt.as_record()) == c.sha256_of(record)
    assert c.sha256_of(T.instrument_set().as_record()) == c.sha256_of(T.instrument_set().as_record())
    assert "economic_terms" not in T.instrument_set().as_record()["instruments"][0]


def test_contract_instrument_with_terms_validates_against_the_schema():
    instrument_id, base = warrant_set()
    record, record_binding = bound("exercise_price", value="1.00")
    attached = attach(base, [record], [record_binding])
    term = terms_of(attached, instrument_id)["exercise_price"]
    with_terms = dataclasses.replace(base.instruments[0], economic_terms=(term,))
    payload = with_terms.as_record()
    assert tuple(payload) == C0_INSTRUMENT_KEYS + ("economic_terms",)
    c.validate_state_record("instrument", payload)
    check_instrument_set(dataclasses.replace(base, instruments=(with_terms,)))
    assert payload["economic_terms"][0]["term_id"] == term.term_id


def test_contract_a_term_of_another_instrument_or_an_unresolved_candidate_is_refused():
    instrument_id, base = warrant_set()
    record, record_binding = bound("exercise_price", value="1.00")
    term = terms_of(attach(base, [record], [record_binding]), instrument_id)["exercise_price"]
    with pytest.raises(c.ContractViolation, match="belongs to"):
        dataclasses.replace(T.instrument(instrument_id="inst:other"), economic_terms=(term,))
    _candidate_id, candidate = instrument_for(OTHER_SERIES, status="unresolved_candidate")
    with pytest.raises(c.ContractViolation, match="carries no economic terms"):
        dataclasses.replace(candidate, economic_terms=(term,))
    twin = dataclasses.replace(term, term_id="econterm:cs:twin")
    with pytest.raises(c.ContractViolation, match="admitted names"):
        dataclasses.replace(base.instruments[0], economic_terms=(term, twin))
