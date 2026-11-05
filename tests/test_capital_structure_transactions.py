"""SPEC_X0 §1-§9 (lane X0a): transaction reconciliation, versions and cash.

Every §0 item, every §4 fixture and every §9 bullet has its own named test here,
asserted with EXACT decimal strings — never approximately and never against a
formatted rendering.  Fixtures are built in-file or loaded from the hand-built
adjudicated-gold records under ``tests/fixtures/capital_structure/transactions``:
no network, no ``data/`` read, no fabricated filing text, and no digest is ever
hard-coded (every digest is derived with :func:`stable_id` or :func:`sha256_of`).

Two laws shape every assertion:

* a cumulative figure and the individual transactions it covers never both
  decrement (A15, L98), and a resale never funds the company (A23);
* unknown is never 0 and never infinity (A20) — an incomplete history yields an
  ``evidenced_floor`` and a named Unknown, never a usage of zero.

The only float literals in this file are inside the float-refusal tests.
"""
from __future__ import annotations

import ast
import dataclasses
import json
import random
from decimal import Decimal
from pathlib import Path

import pytest

import tests.test_capital_structure_instrument_economics as IE
import tests.test_capital_structure_issuer_state_contracts as T
import tests.test_capital_structure_supply_scenarios as SS
from engine.capital_structure import issuer_state_contracts as c
from engine.capital_structure import transactions as tx
from engine.capital_structure.supply_scenarios import evaluate_supply
from engine.capital_structure.transactions import (
    IMPLEMENTATION,
    LEDGER_SCHEMA,
    RULES,
    TransactionBinding,
    TransactionLedger,
    TransactionObservation,
    apply_outstanding,
    receipt_inputs,
    reconcile_transactions,
)

ISSUER = T.ISSUER
CLASS = T.CLASS
WARRANT_CLASS = "class:warrant:series-u"
HASH = "a" * 64
OTHER_HASH = "b" * 64
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "capital_structure" / "transactions"
MODULE = Path("engine/capital_structure/transactions.py")

SHELF_PATH = "path:shelf:2025"
SECOND_PATH = "path:shelf:2026"
INCEPTION = "2025-01-02"
AS_OF = "2026-09-30"

OBSERVATION_KEYS = (
    "schema", "observation_id", "issuer_id", "kind", "reporting_basis", "event_date",
    "period_start", "period_end", "shares", "price_per_share", "gross_proceeds_usd",
    "net_proceeds_usd", "principal_usd", "instruments", "settlement",
    "security_class_id", "source", "evidence", "origin", "extraction_method",
    "decided_at", "available_at",
)
BINDING_KEYS = (
    "schema", "binding_id", "observation_id", "target_kind", "target_id",
    "transaction_id", "usage_class", "programme_key", "programme_inception_date",
    "origin", "decided_at", "supersedes", "evidence",
)
COVERAGE_KEYS = (
    "schema", "coverage_id", "issuer_id", "form_class", "covered_from",
    "complete_through", "source", "extractor_implementation", "available_at",
)
LEDGER_KEYS = (
    "schema", "implementation", "issuer_id", "as_of", "support", "transactions",
    "usage", "instrument_versions", "share_reconciliations", "realized_cash",
    "deferred", "unknowns", "receipt",
)


# ---------------------------------------------------------------------------
# Builders — every id is derived, never invented, and never hard-coded
# ---------------------------------------------------------------------------


def ts(day: str) -> str:
    return f"{day}T00:00:00Z"


def ev(n: int = 1, digest: str = HASH) -> c.EvidenceRef:
    return c.EvidenceRef(f"manifest:{n}", f"span:{n}", digest)


def filing_source(form: str = "424B5", accepted: str = "2026-06-30",
                  file_number: str | None = None, accession: str = "0001-26-000001") -> dict:
    return {
        "accession": accession,
        "form": form,
        "sec_accepted_at": ts(accepted),
        "mastermind_available_at": ts(accepted),
        "file_number": file_number,
    }


def observation(kind: str = "registered_takedown", basis: str = "individual", *,
                event_date: str | None = None, period_start: str | None = None,
                period_end: str | None = None, shares: str | None = None,
                price: str | None = None, gross: str | None = None, net: str | None = None,
                principal: str | None = None, instruments: str | None = None,
                settlement: str | None = None, security_class_id: str | None = CLASS,
                form: str = "424B5", accepted: str = "2026-06-30",
                available: str | None = None, origin: str = "adjudicated_gold",
                decided: str | None = None, extraction_method: str | None = None,
                file_number: str | None = None, evidence: tuple | None = None,
                issuer_id: str = ISSUER, accession: str = "0001-26-000001") -> TransactionObservation:
    gold = origin == "adjudicated_gold"
    return TransactionObservation.build(
        issuer_id=issuer_id,
        kind=kind,
        reporting_basis=basis,
        event_date=event_date,
        period_start=period_start,
        period_end=period_end,
        shares=shares,
        price_per_share=price,
        gross_proceeds_usd=gross,
        net_proceeds_usd=net,
        principal_usd=principal,
        instruments=instruments,
        settlement=settlement,
        security_class_id=security_class_id,
        source=filing_source(form, accepted, file_number, accession),
        evidence=(ev(1), ev(2)) if evidence is None else evidence,
        origin=origin,
        extraction_method=None if gold else (extraction_method or "capital_structure.transaction_extraction.v1"),
        decided_at=ts(decided or accepted) if gold else None,
        available_at=available or ts(accepted),
    )


def binding(obs: TransactionObservation, transaction_id: str, *, target_kind: str | None = None,
            target_id: str | None = None, usage_class: str | None = None,
            origin: str = "adjudicated_gold", decided: str | None = None,
            programme_key: str | None = None, programme_inception_date: str | None = None,
            supersedes: str | None = None, evidence: tuple | None = None) -> TransactionBinding:
    usage = usage_class or tx.USAGE_CLASS_FOR_KIND[obs.kind]
    kind = target_kind or tx.TARGET_KIND_FOR_USAGE_CLASS[usage]
    target = target_id or (SHELF_PATH if kind == "registration_path" else "inst:default")
    if evidence is None:
        evidence = (ev(3),) if origin == "adjudicated_gold" else ()
    return TransactionBinding.build(
        observation_id=obs.observation_id,
        target_kind=kind,
        target_id=target,
        transaction_id=transaction_id,
        usage_class=usage,
        programme_key=programme_key,
        programme_inception_date=programme_inception_date,
        origin=origin,
        decided_at=decided or obs.available_at,
        supersedes=supersedes,
        evidence=evidence,
    )


def instrument_binding(obs: TransactionObservation, transaction_id: str, instrument_id: str, **over) -> TransactionBinding:
    return binding(obs, transaction_id, target_kind="instrument", target_id=instrument_id,
                   usage_class="not_applicable", **over)


def shelf_path_record(path_id: str = SHELF_PATH, file_number: str | None = "333-000001",
                      accepted: str = INCEPTION, issuer_id: str = ISSUER) -> dict:
    """The registration-path facts X0a reads (SPEC_L1 §A.3 shape)."""
    return {
        "schema": "capital_structure.registration_path.v1",
        "path_id": path_id,
        "as_of": ts(AS_OF),
        "issuer": {"issuer_id": issuer_id},
        "registration": {"file_number": file_number, "registration_family": "registration_s3", "form": "S-3"},
        "origin": {
            "event_id": f"evt:{path_id}",
            "accession": "0001-25-000001",
            "form": "S-3",
            "sec_accepted_at": ts(accepted),
            "mastermind_available_at": ts(accepted),
        },
    }


def coverage_record(form_class: str = "424B", covered_from: str = "2025-01-01",
                    complete_through: str = AS_OF, available: str = AS_OF,
                    issuer_id: str = ISSUER) -> tx.FilingCoverage:
    return tx.FilingCoverage.build(
        issuer_id=issuer_id,
        form_class=form_class,
        covered_from=covered_from,
        complete_through=complete_through,
        source={"manifest_generation_id": "manifest:e0:2026-10-01", "filing_index_sha256": HASH},
        extractor_implementation="capital_structure.transaction_extraction.v1",
        available_at=ts(available),
    )


def share_ref(day: str, value: str | None, basis: str = "issued_and_outstanding",
              security_class_id: str = CLASS, available: str | None = None) -> c.ShareObservationRef:
    return c.ShareObservationRef(
        observation_id=c.stable_id("shareref", {"day": day, "value": value, "class": security_class_id,
                                                "basis": basis}),
        basis=basis,
        as_of_date=day,
        security_class_id=security_class_id,
        value=value,
        source=c.Provenance("share_count_observations", generation_id=T.GEN,
                            available_at=available or ts(day)),
    )


# ---------------------------------------------------------------------------
# The ONE shared ledger check every test calls
# ---------------------------------------------------------------------------


def check_ledger(ledger: TransactionLedger, kwargs: dict) -> dict:
    """Schema-validate every record kind the ledger emits and re-derive its receipt."""
    record = ledger.as_record()
    assert tuple(record) == LEDGER_KEYS
    assert record["schema"] == LEDGER_SCHEMA
    assert record["implementation"] == IMPLEMENTATION
    SS.assert_no_float(record, "transaction_ledger")

    for item in kwargs.get("observations", ()):
        assert sorted(item.as_record()) == sorted(OBSERVATION_KEYS)
        c.validate_state_record("transaction_observation", item.as_record())
    for item in kwargs.get("bindings", ()):
        assert sorted(item.as_record()) == sorted(BINDING_KEYS)
        c.validate_state_record("transaction_binding", item.as_record())
    for item in kwargs.get("filing_coverage", ()):
        assert sorted(item.as_record()) == sorted(COVERAGE_KEYS)
        c.validate_state_record("transaction_filing_coverage", item.as_record())

    for item in ledger.usage:
        c.validate_state_record("transaction_usage", item)
    for item in ledger.instrument_versions:
        c.validate_state_record("instrument_version", item)
    for item in ledger.share_reconciliations:
        c.validate_state_record("share_reconciliation", item)
    for item in ledger.realized_cash:
        c.validate_state_record("realized_cash", item)
    for item in ledger.unknowns:
        c.validate_state_record("unknown", item.as_record())
    for item in ledger.deferred:
        assert set(item) == {"observation_id", "reason"}
        assert item["reason"] in tx.DEFERRAL_REASONS
    c.validate_state_record("calculation_receipt", ledger.receipt.as_record())
    family = ledger.family_state()
    c.validate_state_record("family_state", family.as_record())
    assert family.family == "transactions"
    assert family.provenance.support == ledger.support

    inputs = receipt_inputs(
        issuer_id=kwargs["issuer_id"],
        as_of=kwargs["as_of"],
        observations=tuple(kwargs.get("observations", ())),
        bindings=tuple(kwargs.get("bindings", ())),
        filing_coverage=tuple(kwargs.get("filing_coverage", ())),
        registration_paths=tuple(kwargs.get("registration_paths", ())),
        instruments=kwargs.get("instruments"),
        share_observations=tuple(kwargs.get("share_observations", ())),
    )
    assert ledger.receipt.input_digest == c.sha256_of(inputs)
    assert ledger.receipt.rule_digest == c.sha256_of(RULES)
    assert ledger.receipt.implementation_digest == c.sha256_of(
        {"contract": c.STATE_CONTRACT_VERSION, "implementation": IMPLEMENTATION}
    )
    assert ledger.receipt.computed_at == ledger.as_of
    return record


def reconcile(**kwargs) -> TransactionLedger:
    """Reconcile and run the shared check; every ledger in this suite passes it."""
    kwargs.setdefault("issuer_id", ISSUER)
    kwargs.setdefault("as_of", ts(AS_OF))
    kwargs.setdefault("observations", ())
    kwargs.setdefault("bindings", ())
    ledger = reconcile_transactions(**kwargs)
    check_ledger(ledger, kwargs)
    return ledger


def usage_of(ledger: TransactionLedger, usage_key: str | None = None) -> dict:
    records = [item for item in ledger.usage if usage_key is None or item["usage_key"] == usage_key]
    assert len(records) == 1, [item["usage_key"] for item in ledger.usage]
    return records[0]


def exact(record: dict, field: str, expected: str | None) -> None:
    """Assert an exact decimal value — never approximately, never by formatting."""
    quantity = record[field]
    if expected is None:
        assert quantity is None or quantity["status"] != "known", quantity
        assert quantity is None or quantity["value"] is None, quantity
        return
    assert quantity is not None and quantity["status"] == "known", quantity
    assert quantity["value"] == expected
    assert Decimal(quantity["value"]) == Decimal(expected)


def unknown_ids(ledger: TransactionLedger) -> list[str]:
    return [item.unknown_id for item in ledger.unknowns]


def by_id(ledger: TransactionLedger) -> dict[str, dict]:
    return {item["transaction_id"]: item for item in ledger.transactions}


def cash_of(ledger: TransactionLedger, transaction_id: str) -> dict:
    rows = [item for item in ledger.realized_cash if item["transaction_id"] == transaction_id]
    assert len(rows) == 1, [item["transaction_id"] for item in ledger.realized_cash]
    return rows[0]


def versions_of(ledger: TransactionLedger, instrument_id: str) -> list[dict]:
    return [item for item in ledger.instrument_versions if item["instrument_id"] == instrument_id]


# ---------------------------------------------------------------------------
# Gold fixture loader — the files are hand-built adjudicated gold, never filings
# ---------------------------------------------------------------------------


def load_fixture(name: str) -> dict:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert payload["origin"] == "adjudicated_gold"
    assert "NOT extracted filing text" in payload["provenance_note"]
    return payload


def fixture_case(name: str, label: str | None = None) -> tuple[dict, dict]:
    """Build the reconcile kwargs and the expected block of one fixture case."""
    payload = load_fixture(name)
    cases = payload["cases"]
    chosen = cases[0] if label is None else next(item for item in cases if item["label"] == label)
    observations = []
    bindings = []
    for key in chosen["observations"]:
        row = payload["observations"][key]
        accepted = row["accepted"]
        obs = observation(
            kind=row["kind"],
            basis=row["reporting_basis"],
            event_date=row.get("event_date"),
            period_start=row.get("period_start"),
            period_end=row.get("period_end"),
            shares=row.get("shares"),
            price=row.get("price_per_share"),
            gross=row.get("gross_proceeds_usd"),
            net=row.get("net_proceeds_usd"),
            principal=row.get("principal_usd"),
            instruments=row.get("instruments"),
            settlement=row.get("settlement"),
            security_class_id=row.get("security_class_id") or payload["security_class_id"],
            form=row["form"],
            accepted=accepted,
            available=row.get("available_at"),
            file_number=row.get("file_number"),
            issuer_id=payload["issuer_id"],
        )
        observations.append(obs)
        bindings.append(binding(
            obs, row["transaction_id"],
            target_kind=row.get("target_kind", "registration_path"),
            target_id=row["target_id"],
            usage_class=row["usage_class"],
            programme_key=row.get("programme_key"),
            programme_inception_date=row.get("programme_inception_date"),
            decided=row.get("decided"),
        ))
    paths = [
        shelf_path_record(row["path_id"], row.get("file_number"),
                          row["sec_accepted_at"][:10], payload["issuer_id"])
        for row in payload["paths"]
    ]
    coverage = [
        coverage_record(payload["coverage"][key]["form_class"],
                        payload["coverage"][key]["covered_from"],
                        payload["coverage"][key]["complete_through"],
                        payload["coverage"][key]["available_at"][:10],
                        payload["issuer_id"])
        for key in chosen.get("coverage", ())
    ]
    kwargs = {
        "issuer_id": payload["issuer_id"],
        "as_of": ts(chosen["as_of"]),
        "observations": tuple(observations),
        "bindings": tuple(bindings),
        "filing_coverage": tuple(coverage),
        "registration_paths": tuple(paths),
    }
    return kwargs, chosen


def run_fixture(name: str, label: str | None = None) -> tuple[TransactionLedger, dict]:
    kwargs, chosen = fixture_case(name, label)
    ledger = reconcile(**kwargs)
    assert ledger.support == chosen["expected_support"], ledger.support_limits()
    assert_usage_matches(ledger, chosen["expected"])
    return ledger, chosen["expected"]


def assert_usage_matches(ledger: TransactionLedger, expected: dict) -> None:
    record = usage_of(ledger, expected["usage_key"])
    assert record["status"] == expected["status"]
    exact(record, "evidenced_floor", expected["evidenced_floor"])
    exact(record, "usage", expected["usage"])
    if "complete_through" in expected:
        assert record["complete_through"] == expected["complete_through"]
    if "usage_through_complete" in expected:
        exact(record, "usage_through_complete", expected["usage_through_complete"])
    if "post_window_additions" in expected:
        exact(record, "post_window_additions", expected["post_window_additions"])
    if "roles" in expected:
        assert {row["transaction_id"]: row["role"] for row in record["contributors"]} == expected["roles"]
    for forbidden in expected.get("never", ()):
        assert record["usage"]["value"] != forbidden
        assert record["evidenced_floor"]["value"] != forbidden
    if "note_contains" in expected:
        assert expected["note_contains"] in (record["usage"]["note"] or "")
    if "unknown_id" in expected:
        assert expected["unknown_id"] in unknown_ids(ledger)
    if expected.get("resolving_fact_contains"):
        match = next(item for item in ledger.unknowns if item.unknown_id == expected["unknown_id"])
        assert expected["resolving_fact_contains"] in match.resolving_fact
    if "transaction_count" in expected:
        assert len(ledger.transactions) == expected["transaction_count"]


# ---------------------------------------------------------------------------
# §0 item 1 / A15 — a cumulative figure and its individuals never both count
# ---------------------------------------------------------------------------


def test_a15_cumulative_and_individual_never_both_decrement():
    """§0 item 1: ITD 5,000,000 plus an individual 1,000,000 it already covers."""
    ledger, expected = run_fixture("f1_cumulative_covers_individual.json")
    record = usage_of(ledger)
    assert record["usage"]["value"] == "5000000"
    assert record["usage"]["value"] != "6000000"
    assert record["status"] == "known"
    roles = {row["transaction_id"]: row["role"] for row in record["contributors"]}
    assert roles["tx:f1-2026-05-01"] == "covered"
    assert expected["never"] == ["6000000"]


def test_a15_an_individual_inside_the_window_never_adds_even_with_more_evidence():
    """The same law with the individual stated twice under one transaction_id."""
    window = observation(basis="cumulative", period_end="2026-06-30", gross="5000000", accepted="2026-06-30")
    first = observation(event_date="2026-05-01", gross="1000000", accepted="2026-05-02")
    second = observation(event_date="2026-05-01", gross="1000000", accepted="2026-05-09",
                         form="8-K", accession="0001-26-000009")
    ledger = reconcile(
        as_of=ts("2026-06-30"),
        observations=(window, first, second),
        bindings=(binding(window, "tx:itd"), binding(first, "tx:may"), binding(second, "tx:may")),
        registration_paths=(shelf_path_record(),),
    )
    record = usage_of(ledger)
    assert record["status"] == "known"
    assert record["usage"]["value"] == "5000000"
    assert len(ledger.transactions) == 2
    assert {row["transaction_id"]: row["role"] for row in record["contributors"]} == {
        "tx:itd": "window", "tx:may": "covered",
    }


# ---------------------------------------------------------------------------
# §0 item 2 / A20 — incomplete history is unknown, never zero
# ---------------------------------------------------------------------------


def test_incomplete_history_is_unknown_not_zero_with_an_evidenced_floor():
    """No cumulative window and one 2,000,000 takedown: floor known, usage unknown."""
    individual = observation(event_date="2026-05-01", gross="2000000", accepted="2026-05-02")
    ledger = reconcile(
        observations=(individual,),
        bindings=(binding(individual, "tx:only-takedown"),),
        registration_paths=(shelf_path_record(),),
    )
    record = usage_of(ledger)
    assert record["status"] == "unknown"
    exact(record, "evidenced_floor", "2000000")
    exact(record, "usage", None)
    assert record["usage"]["value"] is None
    assert record["usage"]["value"] != "0"
    assert record["complete_through"] is None
    unknown_id = f"usage_history_incomplete:{record['usage_key']}"
    assert unknown_id in unknown_ids(ledger)
    named = next(item for item in ledger.unknowns if item.unknown_id == unknown_id)
    assert "not complete through" in named.description
    assert "424B final pricing supplements" in named.resolving_fact
    assert named.affects == (record["usage_key"],)


def test_incomplete_history_names_the_missing_history_for_a_programme():
    individual = observation(kind="atm_sales", event_date="2026-05-01", gross="1500000",
                             form="10-Q", accepted="2026-05-02")
    ledger = reconcile(
        observations=(individual,),
        bindings=(binding(individual, "tx:atm", target_id=SECOND_PATH),),
        registration_paths=(shelf_path_record(SECOND_PATH, "333-000002"),),
    )
    record = usage_of(ledger, f"programme_usage:{SECOND_PATH}")
    assert record["status"] == "unknown"
    exact(record, "evidenced_floor", "1500000")
    named = next(item for item in ledger.unknowns
                 if item.unknown_id == f"usage_history_incomplete:{record['usage_key']}")
    assert "10-Q/10-K ATM sales disclosures" in named.resolving_fact


# ---------------------------------------------------------------------------
# §0 item 3 / A23 — a resale funds nobody and mints nothing
# ---------------------------------------------------------------------------


def test_a23_resale_no_shares_no_cash_and_no_usage():
    resale = observation(kind="resale", event_date="2026-05-01", shares="500000",
                         gross=None, accepted="2026-05-02", form="424B4")
    takedown = observation(event_date="2026-06-01", gross="1000000", shares="100000",
                           accepted="2026-06-02")
    ledger = reconcile(
        observations=(resale, takedown),
        bindings=(binding(resale, "tx:resale", usage_class="resale"),
                  binding(takedown, "tx:takedown")),
        registration_paths=(shelf_path_record(),),
        share_observations=(share_ref("2026-03-31", "10000000"), share_ref("2026-06-30", "10100000")),
    )
    # Never a usage record of its own, and never inside shelf or programme usage.
    assert [item["usage_key"] for item in ledger.usage] == [f"shelf_usage:{SHELF_PATH}"]
    record = usage_of(ledger)
    # The 500,000 resold shares and their value never enter shelf usage; only the
    # takedown does, and without a completeness proof the usage stays unknown.
    assert record["status"] == "unknown"
    exact(record, "evidenced_floor", "1000000")
    assert {row["transaction_id"] for row in record["contributors"]} == {"tx:takedown"}
    assert "tx:resale" not in {row["transaction_id"] for row in record["contributors"]}
    # 0 incremental shares: the observed +100,000 is entirely the takedown.
    reconciliation = ledger.share_reconciliations[0]
    assert reconciliation["status"] == "known"
    assert reconciliation["observed_delta"] == "100000"
    assert reconciliation["evidenced_net_issuance"] == "100000"
    assert reconciliation["unexplained_delta"] == "0"
    assert "tx:resale" in reconciliation["transaction_ids"]
    # A no_cash row, structurally zero, never a proceeds claim.
    cash = cash_of(ledger, "tx:resale")
    assert cash["realized_cash_kind"] == "no_cash"
    assert cash["gross_usd"] == "0"
    assert cash["net_usd"] == "0"
    assert cash["status"] == "known"
    assert cash_of(ledger, "tx:takedown")["realized_cash_kind"] == "proceeds"
    # And no instrument is decremented by a resale.
    assert ledger.instrument_versions == ()


# ---------------------------------------------------------------------------
# §0 items 4 and 5 / A27 — one decrement per event, prior versions kept
# ---------------------------------------------------------------------------


def warrant_set(series: str = "series_u_cash_warrants", status: str = "outstanding", **terms):
    defaults = dict(instruments_outstanding="1000000", shares_per_instrument="1",
                    exercise_price=SS.STRIKE)
    defaults.update(terms)
    instrument_id, instrument = SS.make_instrument(series, status=status, **defaults)
    return instrument_id, SS.instrument_set((instrument_id, instrument))


def a27_ledger(series: str = "series_u_cash_warrants", status: str = "outstanding",
               exercise_count: str = "100000", as_of: str = "2026-06-30"):
    """The §0 item 4 fixture: a 1,000,000 balance and a 100,000-share cash exercise."""
    instrument_id, instruments = warrant_set(series, status)
    balance = observation(kind="outstanding_balance", basis="point_in_time",
                          event_date="2026-03-31", instruments="1000000",
                          security_class_id=WARRANT_CLASS, accepted="2026-03-31", form="10-Q")
    exercise_8k = observation(kind="warrant_exercise", event_date="2026-05-01",
                              shares=exercise_count, instruments=exercise_count,
                              settlement="cash", price="1.00", gross=exercise_count,
                              accepted="2026-05-01", form="8-K", accession="0001-26-000010")
    exercise_10q = observation(kind="warrant_exercise", event_date="2026-05-01",
                               shares=exercise_count, instruments=exercise_count,
                               settlement="cash", price="1.00", gross=exercise_count,
                               accepted="2026-06-15", form="10-Q", accession="0001-26-000011")
    ledger = reconcile(
        as_of=ts(as_of),
        observations=(balance, exercise_8k, exercise_10q),
        bindings=(instrument_binding(balance, "tx:balance-2026-03-31", instrument_id),
                  instrument_binding(exercise_8k, "tx:exercise-2026-05-01", instrument_id),
                  instrument_binding(exercise_10q, "tx:exercise-2026-05-01", instrument_id)),
        instruments=instruments,
        share_observations=(share_ref("2026-03-31", "10000000"),
                            share_ref("2026-06-30", "10100000")),
    )
    return ledger, instrument_id, instruments


def test_a27_exercise_decrements_once_with_the_8k_and_10q_duplicate():
    ledger, instrument_id, instruments = a27_ledger()
    # Two observations of one event, one transaction_id, one decrement.
    assert len(ledger.transactions) == 2
    assert sorted(by_id(ledger)) == ["tx:balance-2026-03-31", "tx:exercise-2026-05-01"]
    exercise = by_id(ledger)["tx:exercise-2026-05-01"]
    assert len(exercise["observation_ids"]) == 2
    assert exercise["status"] == "observed"
    versions = versions_of(ledger, instrument_id)
    assert [item["outstanding"] for item in versions] == ["1000000", "900000"]
    assert versions[-1]["status"] == "known"

    applied = apply_outstanding(instruments, ledger)
    IE.check_instrument_set(applied)
    instrument = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    terms = {item.name: item for item in instrument.economic_terms}
    assert terms["instruments_outstanding"].value.value == "900000"
    assert terms["instruments_outstanding"].value.status == "known"
    assert Decimal(terms["instruments_outstanding"].value.value) == Decimal("900000")
    assert instrument.outstanding.value == "900000"
    assert instrument.outstanding.share_basis == "assumed_as_converted"
    # The input was never mutated.
    original = next(item for item in instruments.instruments if item.instrument_id == instrument_id)
    original_terms = {item.name: item for item in original.economic_terms}
    assert original_terms["instruments_outstanding"].value.value == "1000000"


def test_a27_exercise_shares_appear_once_in_the_share_reconciliation():
    ledger, _instrument_id, _instruments = a27_ledger()
    assert len(ledger.share_reconciliations) == 1
    reconciliation = ledger.share_reconciliations[0]
    assert reconciliation["observed_delta"] == "100000"
    assert reconciliation["evidenced_net_issuance"] == "100000"
    assert reconciliation["unexplained_delta"] == "0"
    assert reconciliation["transaction_ids"] == ["tx:exercise-2026-05-01"]
    assert reconciliation["status"] == "known"


def test_a27_prior_versions_kept_and_never_overwritten():
    ledger, instrument_id, instruments = a27_ledger()
    versions = versions_of(ledger, instrument_id)
    assert len(versions) == 2
    first, second = versions
    assert first["supersedes_version_id"] is None
    assert first["outstanding"] == "1000000"
    assert first["effective_date"] == "2026-03-31"
    assert first["basis_transaction_ids"] == ["tx:balance-2026-03-31"]
    assert second["supersedes_version_id"] == first["version_id"]
    assert second["outstanding"] == "900000"
    assert second["effective_date"] == "2026-05-01"
    assert second["basis_transaction_ids"] == ["tx:balance-2026-03-31", "tx:exercise-2026-05-01"]
    # Ids are content-addressed, never hard-coded, and the chain is ordered.
    assert first["version_id"] == c.stable_id("instver", {
        "instrument_id": instrument_id, "supersedes_version_id": None,
        **{key: value for key, value in first.items()
           if key not in ("schema", "version_id", "instrument_id", "supersedes_version_id")},
    })
    assert [item["effective_date"] for item in versions] == sorted(item["effective_date"] for item in versions)
    applied = apply_outstanding(instruments, ledger)
    IE.check_instrument_set(applied)


# ---------------------------------------------------------------------------
# Refusal builders — one observation built field by field, never by keyword magic
# ---------------------------------------------------------------------------


def raw_observation(**over) -> TransactionObservation:
    """A fully explicit observation, so a refusal test names the one bad field."""
    fields: dict = dict(
        issuer_id=ISSUER,
        kind="registered_takedown",
        reporting_basis="individual",
        event_date="2026-05-01",
        period_start=None,
        period_end=None,
        shares=None,
        price_per_share=None,
        gross_proceeds_usd="1000000",
        net_proceeds_usd=None,
        principal_usd=None,
        instruments=None,
        settlement=None,
        security_class_id=CLASS,
        source=filing_source("424B5", "2026-05-02"),
        evidence=(ev(1),),
        origin="adjudicated_gold",
        extraction_method=None,
        decided_at=ts("2026-05-02"),
        available_at=ts("2026-05-02"),
    )
    fields.update(over)
    return TransactionObservation.build(**fields)


# ---------------------------------------------------------------------------
# §0 item 6 / A09 — only two origins may state a transaction
# ---------------------------------------------------------------------------


REFUSED_ORIGINS = ("model_prose", "llm", "manual", "heuristic", "extracted", "", "ADJUDICATED_GOLD")


def test_origin_refused_for_every_origin_outside_the_two_admitted():
    """Model prose never mints a transaction, a binding or a coverage record."""
    assert c.TRANSACTION_ORIGINS == ("canonical_extraction", "adjudicated_gold")
    for origin in REFUSED_ORIGINS:
        with pytest.raises(ValueError) as refused:
            raw_observation(origin=origin)
        assert "origin" in str(refused.value)

    gold = raw_observation()
    assert gold.origin == "adjudicated_gold"
    assert gold.decided_at is not None and gold.extraction_method is None
    extracted = raw_observation(origin="canonical_extraction", decided_at=None,
                                extraction_method="capital_structure.transaction_extraction.v1")
    assert extracted.origin == "canonical_extraction"
    assert extracted.decided_at is None
    # Each admitted origin carries its own proof, and never the other's.
    with pytest.raises(ValueError):
        raw_observation(origin="canonical_extraction", decided_at=None, extraction_method=None)
    with pytest.raises(ValueError):
        raw_observation(origin="adjudicated_gold",
                        extraction_method="capital_structure.transaction_extraction.v1")

    assert c.BINDING_ORIGINS == ("canonical_join", "adjudicated_gold")
    row = raw_observation()
    for origin in ("manual", "model_prose", ""):
        with pytest.raises(ValueError) as refused:
            binding(row, "tx:origin", origin=origin)
        assert "origin" in str(refused.value)
    joined = binding(row, "tx:origin", origin="canonical_join")
    assert joined.origin == "canonical_join" and joined.evidence == ()
    # An adjudicated_gold binding without evidence is not an adjudication.
    with pytest.raises(ValueError):
        TransactionBinding.build(observation_id=row.observation_id, target_kind="registration_path",
                                 target_id=SHELF_PATH, transaction_id="tx:origin",
                                 usage_class="shelf_takedown", origin="adjudicated_gold",
                                 decided_at=ts("2026-05-02"), supersedes=None, evidence=())


def test_origin_refused_before_a_ledger_can_exist():
    """A refused origin can never reach a ledger: the record itself does not build."""
    with pytest.raises(ValueError):
        observation(event_date="2026-05-01", gross="1000000", accepted="2026-05-02",
                    origin="model_prose")
    ledger = reconcile(observations=(), bindings=())
    assert ledger.support == "unavailable"
    assert ledger.transactions == () and ledger.usage == () and ledger.records() == ()


# ---------------------------------------------------------------------------
# §0 item 7 / A20 — no float anywhere; unknown is never 0 and never infinity
# ---------------------------------------------------------------------------


def test_float_refusal_in_every_numeric_field():
    """A float is refused as a float; an int is not an exact decimal string either."""
    for field, value in (
        ("shares", 100000.0),
        ("price_per_share", 1.0),
        ("gross_proceeds_usd", 3000000.0),
        ("net_proceeds_usd", 2900000.0),
        ("principal_usd", 2000000.0),
        ("instruments", 1000.0),
    ):
        with pytest.raises(TypeError) as refused:
            raw_observation(**{field: value})
        assert "float is never accepted" in str(refused.value)
    with pytest.raises(TypeError):
        raw_observation(shares=100000)
    with pytest.raises(TypeError):
        raw_observation(source={**filing_source("424B5", "2026-05-02"), "sec_accepted_at": 20260502.0})
    with pytest.raises(TypeError):
        tx.FilingCoverage.build(
            issuer_id=ISSUER, form_class="424B", covered_from=2025.0, complete_through="2026-09-30",
            source={"manifest_generation_id": "manifest:e0:2026-10-01", "filing_index_sha256": HASH},
            extractor_implementation="capital_structure.transaction_extraction.v1",
            available_at=ts("2026-09-30"),
        )
    # A float ledger cursor is refused as a float, never silently stringified.
    with pytest.raises(TypeError):
        reconcile_transactions(issuer_id=ISSUER, as_of=2026.5, observations=(), bindings=())
    # The same magnitude as an exact decimal string is kept byte for byte.
    assert raw_observation(gross_proceeds_usd="3000000.000").gross_proceeds_usd == "3000000.000"


def test_float_refusal_never_leaves_a_float_in_a_built_record():
    """Every numeric field of every emitted record is an exact decimal string."""
    ledger, instrument_id, instruments = a27_ledger()
    SS.assert_no_float(ledger.as_record(), "transaction_ledger")
    for transaction in ledger.transactions:
        for field in ("shares", "price_per_share", "gross_proceeds_usd", "net_proceeds_usd",
                      "principal_usd", "instruments"):
            value = transaction[field]
            assert value is None or isinstance(value, str), (field, value)
            if value is not None:
                assert Decimal(value).is_finite()
    for version in versions_of(ledger, instrument_id):
        for field in ("outstanding", "explained_decrease", "explained_increase", "unexplained_delta"):
            assert version[field] is None or isinstance(version[field], str)
    applied = apply_outstanding(instruments, ledger)
    SS.assert_no_float(applied.as_record(), "applied_instrument_set")


def test_unknown_is_never_zero_and_never_infinity():
    """A20: an unknown usage carries no value at all, and nothing is an infinity."""
    individual = observation(event_date="2026-05-01", gross="2000000", accepted="2026-05-02")
    ledger = reconcile(observations=(individual,), bindings=(binding(individual, "tx:only"),),
                       registration_paths=(shelf_path_record(),))
    record = usage_of(ledger)
    assert record["usage"]["status"] == "unknown"
    assert record["usage"]["value"] is None
    assert record["usage"]["value"] != "0"
    assert record["usage_through_complete"] is None
    assert record["post_window_additions"] is None
    exact(record, "evidenced_floor", "2000000")
    for value in (record["usage"]["value"], record["usage_through_complete"],
                  record["post_window_additions"], record["evidenced_floor"]["value"]):
        assert value is None or Decimal(value).is_finite()
    # An unstated instrument balance is unknown, never a zero balance.
    instrument_id, instruments = warrant_set("series_u_unknown_balance")
    balance = observation(kind="outstanding_balance", basis="point_in_time", event_date="2026-03-31",
                          instruments=None, security_class_id=WARRANT_CLASS, form="10-Q",
                          accepted="2026-03-31")
    unknown_ledger = reconcile(observations=(balance,),
                               bindings=(instrument_binding(balance, "tx:balance", instrument_id),),
                               instruments=instruments)
    version = versions_of(unknown_ledger, instrument_id)[-1]
    assert version["status"] == "unknown"
    assert version["outstanding"] is None
    applied = apply_outstanding(instruments, unknown_ledger)
    term = next(item for instrument in applied.instruments if instrument.instrument_id == instrument_id
                for item in instrument.economic_terms if item.name == "instruments_outstanding")
    assert term.value.status == "unknown" and term.value.value is None
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    assert replaced.outstanding.status == "unknown" and replaced.outstanding.value is None


# ---------------------------------------------------------------------------
# §0 item 8 — point in time: nothing dated after ``as_of`` is visible
# ---------------------------------------------------------------------------


def assert_invisible(item: TransactionObservation, *, as_of: str = "2026-06-30",
                     transaction_id: str = "tx:late", instruments=None) -> TransactionLedger:
    """A record dated after ``as_of`` mints no transaction, no usage and no deferral."""
    if instruments is None:
        bind: TransactionBinding = binding(item, transaction_id, target_id=SHELF_PATH)
        paths: tuple = (shelf_path_record(),)
    else:
        bind = instrument_binding(item, transaction_id, instruments.instruments[0].instrument_id)
        paths = ()
    ledger = reconcile(as_of=ts(as_of), observations=(item,), bindings=(bind,),
                       registration_paths=paths, instruments=instruments)
    assert ledger.support == "unavailable"
    assert ledger.transactions == ()
    assert ledger.usage == ()
    assert ledger.records() == ()
    assert ledger.deferred == ()
    assert ledger.unknowns == ()
    family = ledger.family_state()
    assert family.records == ()
    assert family.provenance.support == "unavailable"
    return ledger


def test_point_in_time_available_at_after_as_of_is_invisible():
    late = raw_observation(available_at=ts("2026-07-15"))
    assert late.available_at == ts("2026-07-15")
    assert_invisible(late, as_of="2026-06-30")
    # The identical record available inside as_of is visible, and does count.
    control = raw_observation()
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(control,),
                       bindings=(binding(control, "tx:control"),),
                       registration_paths=(shelf_path_record(),))
    assert ledger.support == "supported"
    exact(usage_of(ledger), "evidenced_floor", "1000000")


def test_point_in_time_decided_at_after_as_of_is_invisible():
    """Only ``decided_at`` moves: ``available_at`` stays inside as_of."""
    late = raw_observation(decided_at=ts("2026-07-15"))
    assert late.available_at == ts("2026-05-02")
    assert_invisible(late, as_of="2026-06-30")
    # A binding decided after as_of is invisible even when its observation is not.
    row = raw_observation()
    late_binding = binding(row, "tx:late-binding", target_id=SHELF_PATH, decided=ts("2026-07-15"))
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(row,), bindings=(late_binding,),
                       registration_paths=(shelf_path_record(),))
    assert ledger.support == "partial"
    assert ledger.transactions == ()
    assert ledger.deferred == ({"observation_id": row.observation_id, "reason": "binding_not_visible"},)


def test_point_in_time_event_date_after_as_of_is_invisible():
    """An event dated after ``as_of`` never lands, and §2 makes the date non-bypassable."""
    late = raw_observation(event_date="2026-07-15", source=filing_source("424B5", "2026-07-16"),
                           available_at=ts("2026-07-16"), decided_at=ts("2026-07-16"))
    assert_invisible(late, as_of="2026-06-30")
    # An event may never postdate its own availability, so the event-date gate cannot
    # be reached with a visible available_at: the two gates coincide by construction.
    with pytest.raises(ValueError):
        raw_observation(event_date="2026-07-15", source=filing_source("424B5", "2026-05-02"),
                        available_at=ts("2026-05-02"))
    control = raw_observation(event_date="2026-06-15", source=filing_source("424B5", "2026-06-16"),
                              available_at=ts("2026-06-16"), decided_at=ts("2026-06-16"))
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(control,),
                       bindings=(binding(control, "tx:control"),),
                       registration_paths=(shelf_path_record(),))
    assert ledger.support == "supported"
    exact(usage_of(ledger), "evidenced_floor", "1000000")


def test_point_in_time_period_end_after_as_of_is_invisible():
    late = observation(basis="cumulative", period_end="2026-07-31", gross="5000000",
                       accepted="2026-07-31", available=ts("2026-07-31"))
    assert_invisible(late, as_of="2026-06-30")
    with pytest.raises(ValueError):
        observation(basis="cumulative", period_end="2026-07-31", gross="5000000",
                    accepted="2026-05-02", available=ts("2026-05-02"))
    control = observation(basis="cumulative", period_end="2026-06-30", gross="5000000",
                          accepted="2026-06-30")
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(control,),
                       bindings=(binding(control, "tx:control"),),
                       registration_paths=(shelf_path_record(),))
    assert ledger.support == "supported"
    record = usage_of(ledger)
    assert record["status"] == "known"
    exact(record, "usage", "5000000")
    assert record["complete_through"] == "2026-06-30"


def test_point_in_time_a_late_record_never_shadows_a_visible_one():
    """Both at once: only the visible takedown counts, and nothing is zero-filled."""
    visible = raw_observation(event_date="2026-05-01", gross_proceeds_usd="1000000")
    late = raw_observation(event_date="2026-08-15", gross_proceeds_usd="4000000",
                           source=filing_source("424B5", "2026-08-16", accession="0001-26-000030"),
                           available_at=ts("2026-08-16"), decided_at=ts("2026-08-16"))
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(visible, late),
                       bindings=(binding(visible, "tx:visible"), binding(late, "tx:late")),
                       registration_paths=(shelf_path_record(),))
    assert ledger.support == "supported"
    assert [item["transaction_id"] for item in ledger.transactions] == ["tx:visible"]
    record = usage_of(ledger)
    exact(record, "evidenced_floor", "1000000")
    assert record["status"] == "unknown"
    assert f"usage_history_incomplete:{record['usage_key']}" in unknown_ids(ledger)


def test_point_in_time_a_late_coverage_record_completes_nothing():
    """A filing-coverage attestation published after ``as_of`` is invisible too."""
    individual = observation(event_date="2026-05-01", gross="1000000", accepted="2026-05-02")
    late_coverage = coverage_record(complete_through="2026-09-30", available="2026-10-15")
    ledger = reconcile(as_of=ts("2026-09-30"), observations=(individual,),
                       bindings=(binding(individual, "tx:only"),),
                       filing_coverage=(late_coverage,),
                       registration_paths=(shelf_path_record(),))
    record = usage_of(ledger)
    assert record["status"] == "unknown"
    assert record["complete_through"] is None
    exact(record, "evidenced_floor", "1000000")


def test_point_in_time_a_share_figure_with_no_availability_is_invisible():
    """A share figure that states no availability time is never visible; it is a named unknown."""
    undated = c.ShareObservationRef(
        observation_id=c.stable_id("shareref", {"day": "2026-06-30", "undated": True}),
        basis="issued_and_outstanding", as_of_date="2026-06-30", security_class_id=CLASS,
        value="10100000", source=c.Provenance("share_count_observations", generation_id=T.GEN),
    )
    unsourced = c.ShareObservationRef(
        observation_id=c.stable_id("shareref", {"day": "2026-07-31", "unsourced": True}),
        basis="issued_and_outstanding", as_of_date="2026-07-31", security_class_id=CLASS,
        value="10200000",
    )
    first, last = share_ref("2026-03-31", "10000000"), share_ref("2026-09-30", "10240000")
    ledger = reconcile(as_of=ts("2026-09-30"), share_observations=(first, undated, unsourced, last))
    assert [(item["from_observation_id"], item["to_observation_id"])
            for item in ledger.share_reconciliations] == [(first.observation_id, last.observation_id)]
    for item in (undated, unsourced):
        assert f"share_observation_availability_unstated:{item.observation_id}" in unknown_ids(ledger)


# ---------------------------------------------------------------------------
# One ledger carrying every record kind — reused by the contract, order and
# determinism tests
# ---------------------------------------------------------------------------


def rich_ledger_inputs() -> tuple[dict, str]:
    """Usage, versions, share reconciliations and realized cash in a single ledger."""
    instrument_id, instruments = warrant_set("series_u_cash_warrants")
    window = observation(basis="cumulative", period_end="2026-06-30", gross="5000000",
                         accepted="2026-06-30")
    inside = observation(event_date="2026-05-01", gross="1000000", shares="100000",
                         accepted="2026-05-02")
    after = observation(event_date="2026-08-15", gross="2000000", shares="80000",
                        accepted="2026-08-16", accession="0001-26-000020")
    atm = observation(kind="atm_sales", event_date="2026-07-01", gross="1500000", shares="60000",
                      form="10-Q", accepted="2026-07-02", accession="0001-26-000021")
    balance = observation(kind="outstanding_balance", basis="point_in_time", event_date="2026-03-31",
                          instruments="1000000", security_class_id=WARRANT_CLASS, form="10-Q",
                          accepted="2026-03-31", accession="0001-26-000022")
    exercise = observation(kind="warrant_exercise", event_date="2026-05-01", shares="100000",
                           instruments="100000", settlement="cash", price="1.00",
                           accepted="2026-05-01", accession="0001-26-000023")
    resale = observation(kind="resale", event_date="2026-06-01", shares="500000", form="424B4",
                         accepted="2026-06-02", accession="0001-26-000024")
    kwargs = {
        "issuer_id": ISSUER,
        "as_of": ts(AS_OF),
        "observations": (window, inside, after, atm, balance, exercise, resale),
        "bindings": (
            binding(window, "tx:window"),
            binding(inside, "tx:inside"),
            binding(after, "tx:after"),
            binding(atm, "tx:atm", target_id=SECOND_PATH),
            instrument_binding(balance, "tx:balance", instrument_id),
            instrument_binding(exercise, "tx:exercise", instrument_id),
            binding(resale, "tx:resale", usage_class="resale"),
        ),
        "filing_coverage": (coverage_record(),),
        "registration_paths": (shelf_path_record(), shelf_path_record(SECOND_PATH, "333-000002")),
        "instruments": instruments,
        "share_observations": (share_ref("2026-03-31", "10000000"),
                               share_ref("2026-06-30", "10100000"),
                               share_ref("2026-09-30", "10240000")),
    }
    return kwargs, instrument_id


# ---------------------------------------------------------------------------
# §1 / §0 item 9 — C0 2.2.0 is purely additive over 2.0.0 and 2.1.0
# ---------------------------------------------------------------------------


BASE_COMMIT = "e32d41092080be8adb24bdd10bfeb4115765a0ce"
BASELINE_FILE = FIXTURES / "c0_2_1_0_contract_baseline.json"
NEW_FAMILIES = {
    "transaction_observations": ("capital_structure.transaction_observation.v1",),
    "transaction_bindings": ("capital_structure.transaction_binding.v1",),
    "transaction_filing_coverage": ("capital_structure.transaction_filing_coverage.v1",),
}
NEW_DEFS = ("transaction_observation", "transaction_binding", "transaction_filing_coverage",
            "transaction_usage", "instrument_version", "share_reconciliation", "realized_cash")
DELTA_DEFS = ("compatibility", "input_family", "input_schema")
DELTA_TABLES = ("COMPATIBLE_INPUT_SCHEMAS", "PROJECTION_COMPATIBILITY")
# I2 (SPEC_I2 §1, state contract 2.3.0) landed after X0 and is itself purely
# additive over this frozen 2.1.0 surface: it widens three $defs / five tables
# (a structure on economic_term, the I2 term names and units, and the
# conversion-only ``physical`` settlement) and adds the structure vocabularies
# below. Everything else X0 froze must still be byte-identical; the I2 names are
# listed explicitly so an undeclared change can never hide behind the delta.
I2_DELTA_DEFS = ("economic_term", "economic_term_name", "settlement")
I2_DELTA_TABLES = ("ECONOMIC_TERM_EFFECTIVE_NAMES", "ECONOMIC_TERM_FLAG_NAMES",
                   "ECONOMIC_TERM_NAMES", "ECONOMIC_TERM_UNITS", "SETTLEMENTS")
I2_NEW_DEFS = (
    "accrual", "accrual_compounding", "accrual_day_count", "anti_dilution",
    "anti_dilution_method", "below_floor_rule", "branch_elected_by", "condition_comparison",
    "condition_threshold_kind", "conversion_condition", "floor_basis", "nullable_rounding",
    "percent_quantity", "price_aggregation", "price_combine", "price_component",
    "price_component_source", "price_formula", "price_measure", "price_term_name",
    "price_window_end", "reset_event", "reset_rule", "reset_schedule", "rounding",
    "rounding_mode", "settlement_branch_name", "settlement_branches", "share_adjustment",
    "structure_kind",
)
I2_NEW_TABLES = (
    "ACCRUAL_COMPOUNDING", "ACCRUAL_DAY_COUNTS", "ANTI_DILUTION_METHODS", "BELOW_FLOOR_RULES",
    "BRANCH_ELECTED_BY", "CONDITION_COMPARISONS", "CONDITION_THRESHOLD_KINDS",
    "ECONOMIC_TERM_PRICE_FORMULA_NAMES", "ECONOMIC_TERM_STRUCTURE_NAMES",
    "ECONOMIC_TERM_STRUCTURE_TYPES", "FLOOR_BASES", "PRICE_AGGREGATIONS", "PRICE_COMBINES",
    "PRICE_COMPONENT_SOURCES", "PRICE_MEASURES", "PRICE_TERM_NAMES", "PRICE_WINDOW_ENDS",
    "RESET_RULES", "ROUNDING_MODES", "SETTLEMENT_BRANCH_NAMES", "SHARE_ADJUSTMENTS",
    "STRUCTURE_KINDS", "_QUANTITY_FIELDS", "_STRUCTURE_CLASS_NAMES", "_STRUCTURE_RECORD_KEYS",
)
# The public surface I2 exports: its vocabularies plus the structure classes and
# the record decoder. STRUCTURE_TYPES_BY_KIND maps names to classes, so it is
# exported but not a digestible table.
I2_ALL_ADDITIONS = tuple(name for name in I2_NEW_TABLES if not name.startswith("_")) + (
    "Accrual", "AntiDilution", "ConversionCondition", "PriceComponent", "PriceFormula",
    "ResetEvent", "ResetSchedule", "SettlementBranches", "STRUCTURE_TYPES_BY_KIND",
    "structure_from_record",
)
# S0 (SPEC_S0 §8, state contract 2.4.0) landed after I2 and is likewise purely
# additive over this frozen 2.1.0 surface: it adds the ``scenario_result`` record
# and the seven declarative sub-records a composer emits beside the three
# component records, plus their vocabularies. It widens exactly two tables —
# ``RECORD_SCHEMAS`` (one new record schema) and ``INTERFACE_OWNERSHIP`` (the
# composer's own row, which §8 requires) — and rewrites no existing $def.
S0_DELTA_TABLES = ("INTERFACE_OWNERSHIP", "RECORD_SCHEMAS")
S0_NEW_DEFS = (
    "action_check", "action_check_status", "action_owner", "authorized_headroom_disclosure",
    "authorized_headroom_status", "cash_reconciliation", "coverage_period", "coverage_status",
    "exact_number_text", "issuance_row", "joint_check", "joint_check_status",
    "nullable_exact_number_text", "nullable_signed_decimal", "nullable_signed_usd_quantity",
    "price_basis", "reconciliation_status", "result_id", "scenario_result",
    "scenario_share_quantity", "signed_decimal", "signed_usd_quantity",
)
S0_NEW_TABLES = (
    "ACTION_CHECK_STATUSES", "ACTION_OWNERS", "AUTHORIZED_HEADROOM_STATUSES", "COVERAGE_STATUSES",
    "ISSUANCE_ROW_BASES", "JOINT_CHECK_STATUSES", "PRICE_BASIS_COMPONENTS", "PRICE_BASIS_KINDS",
    "RECONCILIATION_STATUSES",
)
S0_ALL_ADDITIONS = S0_NEW_TABLES + (
    "ActionCheck", "AuthorizedHeadroomDisclosure", "COVERAGE_SCENARIO_ONLY_NOTE",
    "CashReconciliation", "CoveragePeriod", "IssuanceRow", "JointCheck", "PriceBasis",
    "ScenarioResult", "SignedQuantity",
)


def load_baseline() -> dict:
    """The frozen C0 2.1.0 surface; its digests are re-derived live, never trusted."""
    payload = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    assert payload["origin"] == "adjudicated_gold"
    assert "NOT extracted filing text" in payload["provenance_note"]
    assert payload["base_commit"] == BASE_COMMIT
    assert payload["base_state_contract_version"] == "capital-structure-state-contracts/2.1.0"
    return payload


def live_tables() -> dict:
    """A digest of every digestible table in the live contracts module."""
    tables = {}
    for name in sorted(vars(c)):
        if name.startswith("__"):
            continue
        value = getattr(c, name)
        if not isinstance(value, (tuple, dict, frozenset, list)):
            continue
        try:
            tables[name] = c.sha256_of(sorted(value) if isinstance(value, frozenset) else value)
        except Exception:  # not a JSON-able vocabulary table
            continue
    return tables


def test_c0_2_0_0_and_2_1_0_digests_are_byte_identical_after_2_2_0():
    """§0 item 9: every pre-existing schema ``$def`` and vocabulary is untouched."""
    baseline = load_baseline()
    defs = c.load_state_schema()["$defs"]

    unchanged = 0
    for name, digest in baseline["schema_defs"].items():
        assert name in defs, name
        if name in DELTA_DEFS or name in I2_DELTA_DEFS:
            continue
        assert c.sha256_of(defs[name]) == digest, f"$def {name} changed"
        unchanged += 1
    assert unchanged == len(baseline["schema_defs"]) - len(DELTA_DEFS) - len(I2_DELTA_DEFS)
    assert set(defs) == (set(baseline["schema_defs"]) | set(baseline["added_schema_defs"])
                         | set(I2_NEW_DEFS) | set(S0_NEW_DEFS))
    assert sorted(baseline["added_schema_defs"]) == sorted(NEW_DEFS)
    # I2 only widened the three $defs it declares: the structure attachment, the
    # term-name enum and the settlement enum each grow, nothing is dropped.
    for name in I2_DELTA_DEFS:
        assert c.sha256_of(defs[name]) != baseline["schema_defs"][name], name
    assert set(defs["settlement"]["enum"]) == set(c.SETTLEMENTS)
    assert "physical" in defs["settlement"]["enum"]
    assert set(defs["economic_term_name"]["enum"]) == set(c.ECONOMIC_TERM_NAMES)

    # The three forced deltas: the version const and the two mirrored enums.
    base_compatibility = baseline["declared_schema_deltas"]["compatibility"]
    assert defs["compatibility"] == {
        **base_compatibility,
        "properties": {
            **base_compatibility["properties"],
            "state_contract_version": {"const": c.STATE_CONTRACT_VERSION},
        },
    }
    for name, added in (("input_family", set(NEW_FAMILIES)),
                        ("input_schema", {schema for schemas in NEW_FAMILIES.values() for schema in schemas})):
        base_def = baseline["declared_schema_deltas"][name]
        live_def = defs[name]
        assert set(live_def) == set(base_def), name
        assert set(live_def["enum"]) - set(base_def["enum"]) == added, name
        assert set(base_def["enum"]) <= set(live_def["enum"]), name
        assert len(live_def["enum"]) == len(set(live_def["enum"])), name
        assert {key: value for key, value in live_def.items() if key != "enum"} == \
            {key: value for key, value in base_def.items() if key != "enum"}, name
    assert set(defs["input_family"]["enum"]) == set(c.COMPATIBLE_INPUT_SCHEMAS)
    assert set(defs["input_schema"]["enum"]) == {
        schema for schemas in c.COMPATIBLE_INPUT_SCHEMAS.values() for schema in schemas
    }

    # The module side: every 2.0.0/2.1.0 vocabulary table is byte-identical.
    live = live_tables()
    for name, digest in baseline["module_tables"].items():
        assert name in live, name
        if name in DELTA_TABLES or name in I2_DELTA_TABLES or name in S0_DELTA_TABLES:
            continue
        assert live[name] == digest, f"vocabulary {name} changed"
    assert set(live) - set(baseline["module_tables"]) == (
        set(baseline["declared_module_deltas"]["added_module_tables"]) | set(I2_NEW_TABLES)
        | set(S0_NEW_TABLES))
    for name in I2_DELTA_TABLES:
        assert live[name] != baseline["module_tables"][name], name
    for name in S0_DELTA_TABLES:
        assert live[name] != baseline["module_tables"][name], name

    for family, schemas in baseline["base_compatible_input_schemas"].items():
        assert list(c.COMPATIBLE_INPUT_SCHEMAS[family]) == schemas, family
    gained = {family: tuple(schemas) for family, schemas in c.COMPATIBLE_INPUT_SCHEMAS.items()
              if family not in baseline["base_compatible_input_schemas"]}
    assert gained == NEW_FAMILIES
    assert c.PROJECTION_COMPATIBILITY == {
        **baseline["base_projection_compatibility"],
        "state_contract_version": c.STATE_CONTRACT_VERSION,
    }
    assert set(baseline["base_all"]) <= set(c.__all__)
    assert set(c.__all__) - set(baseline["base_all"]) == (
        set(baseline["declared_module_deltas"]["added_module_tables"]) | set(I2_ALL_ADDITIONS)
        | set(S0_ALL_ADDITIONS))
    for name, values in baseline["declared_module_deltas"]["added_module_tables"].items():
        assert list(getattr(c, name)) == values, name


def test_contract_version_at_least_2_2_0():
    # X0 shipped as 2.2.0; later additive minors (I2 = 2.3.0) may follow, but the
    # major stays 2 and the minor never regresses below the X0 delta.
    major, minor, _patch = c.STATE_CONTRACT_VERSION.rsplit("/", 1)[1].split(".")
    assert (int(major), int(minor)) >= (2, 2)
    schema = c.load_state_schema()
    assert schema["properties"]["contract_version"]["const"] == c.STATE_CONTRACT_VERSION
    compatibility = schema["$defs"]["compatibility"]["properties"]["state_contract_version"]
    assert compatibility["const"] == c.STATE_CONTRACT_VERSION
    assert c.PROJECTION_COMPATIBILITY["state_contract_version"] == c.STATE_CONTRACT_VERSION
    ledger = reconcile(observations=(), bindings=())
    assert ledger.receipt.implementation_digest == c.sha256_of(
        {"contract": c.STATE_CONTRACT_VERSION, "implementation": IMPLEMENTATION})
    # 2.1.0's own input families survive the bump untouched.
    assert c.COMPATIBLE_INPUT_SCHEMAS["instrument_economic_terms"] == (
        "capital_structure.instrument_economic_term.v1",)
    assert c.COMPATIBLE_INPUT_SCHEMAS["instrument_term_bindings"] == (
        "capital_structure.instrument_term_binding.v1",)


def test_contract_new_schemas_registered():
    for family, schemas in NEW_FAMILIES.items():
        assert c.COMPATIBLE_INPUT_SCHEMAS[family] == schemas
    assert c.TRANSACTION_KINDS == (
        "registered_takedown", "atm_sales", "warrant_exercise", "conversion", "redemption",
        "repurchase", "cancellation", "resale", "outstanding_balance", "instrument_issuance")
    assert c.REPORTING_BASES == ("individual", "cumulative", "point_in_time")
    assert c.TRANSACTION_ORIGINS == ("canonical_extraction", "adjudicated_gold")
    assert c.BINDING_ORIGINS == ("canonical_join", "adjudicated_gold")
    assert c.BINDING_TARGET_KINDS == ("registration_path", "instrument")
    assert c.USAGE_CLASSES == ("shelf_takedown", "programme_sale", "resale", "not_applicable")
    assert c.REALIZED_CASH_KINDS == ("proceeds", "repayment", "no_cash")
    assert tx.TRANSACTION_KINDS is c.TRANSACTION_KINDS
    # C0 already admits the family that carries the ledger records.
    assert "transactions" in c.STATE_FAMILIES
    defs = c.load_state_schema()["$defs"]
    for name in NEW_DEFS:
        assert name in defs, name
        assert defs[name]["additionalProperties"] is False, name
        assert defs[name]["properties"]["schema"]["const"].startswith("capital_structure."), name


def test_contract_records_validate():
    """Every record kind this lane emits validates against its ``$def``."""
    row = raw_observation()
    c.validate_state_record("transaction_observation", row.as_record())
    c.validate_state_record("transaction_binding", binding(row, "tx:validate").as_record())
    c.validate_state_record("transaction_filing_coverage", coverage_record().as_record())

    kwargs, instrument_id = rich_ledger_inputs()
    ledger = reconcile(**kwargs)
    for kind, records in (("transaction_usage", ledger.usage),
                          ("instrument_version", ledger.instrument_versions),
                          ("share_reconciliation", ledger.share_reconciliations),
                          ("realized_cash", ledger.realized_cash)):
        assert records, kind
        for record in records:
            c.validate_state_record(kind, record)
    assert versions_of(ledger, instrument_id)[-1]["outstanding"] == "900000"

    # additionalProperties: false, and the schema literal is a const.
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("transaction_observation", {**row.as_record(), "score": "1"})
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("transaction_observation",
                                {**row.as_record(), "schema": "capital_structure.transaction_observation.v2"})
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("transaction_usage", {**ledger.usage[0], "rank": "1"})
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("instrument_version",
                                {key: value for key, value in ledger.instrument_versions[0].items()
                                 if key != "supersedes_version_id"})


def test_no_float_call_in_the_engine_source():
    source = (ROOT / MODULE).read_text(encoding="utf-8")
    assert "float(" not in source
    # Not even a float literal survives in the engine: the AST is the proof.
    tree = ast.parse(source)
    literals = [node.lineno for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, float)]
    assert literals == []
    calls = [node.lineno for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == "float"]
    assert calls == []


# ---------------------------------------------------------------------------
# §4 fixtures F1-F9 — every one asserts the exact stated usage state and value
# ---------------------------------------------------------------------------


SHELF_KEY = f"shelf_usage:{SHELF_PATH}"
ATM_PATH = "path:atm:2026"
PROGRAMME_KEY = f"programme_usage:{ATM_PATH}"


def test_f1_cumulative_window_covers_the_individual_it_explains():
    """F1: ITD 5,000,000 through 06-30 plus a 1,000,000 sale on 05-01."""
    ledger, _expected = run_fixture("f1_cumulative_covers_individual.json", "as_of_2026_06_30")
    record = usage_of(ledger, SHELF_KEY)
    assert record["status"] == "known"
    exact(record, "usage", "5000000")
    exact(record, "evidenced_floor", "5000000")
    exact(record, "usage_through_complete", "5000000")
    exact(record, "post_window_additions", "0")
    assert record["complete_through"] == "2026-06-30"
    # Never 6,000,000: the individual is inside the window, so it is covered.
    assert record["usage"]["value"] != "6000000"
    assert record["evidenced_floor"]["value"] != "6000000"
    assert Decimal(record["usage"]["value"]) == Decimal("5000000")
    roles = {row["transaction_id"]: row["role"] for row in record["contributors"]}
    assert roles == {"tx:f1-inception-to-date": "window", "tx:f1-2026-05-01": "covered"}
    assert ledger.support == "supported"
    assert unknown_ids(ledger) == []


def test_f2_a_post_window_individual_leaves_usage_unknown_with_a_floor():
    """F2: the 08-15 sale is evidenced, but the history is not complete."""
    ledger, _expected = run_fixture("f2_post_window_individual_is_not_complete.json")
    record = usage_of(ledger, SHELF_KEY)
    assert record["status"] == "unknown"
    exact(record, "evidenced_floor", "7000000")
    exact(record, "usage_through_complete", "5000000")
    exact(record, "post_window_additions", "2000000")
    exact(record, "usage", None)
    assert record["usage"]["value"] is None
    assert record["complete_through"] == "2026-06-30"
    assert {row["transaction_id"]: row["role"] for row in record["contributors"]} == {
        "tx:f2-inception-to-date": "window",
        "tx:f2-2026-05-01": "covered",
        "tx:f2-2026-08-15": "added",
    }
    unknown_id = f"usage_history_incomplete:{SHELF_KEY}"
    assert unknown_id in unknown_ids(ledger)
    named = next(item for item in ledger.unknowns if item.unknown_id == unknown_id)
    assert "424B final pricing supplements" in named.resolving_fact
    assert named.affects == (SHELF_KEY,)
    # The floor is a real lower bound: 5,000,000 + 2,000,000, never 0.
    assert Decimal(record["evidenced_floor"]["value"]) == Decimal("5000000") + Decimal("2000000")


def test_f3_a_later_window_dominates_the_earlier_one():
    """F3: the ITD 8,000,000 window contains the 5,000,000 one."""
    ledger, _expected = run_fixture("f3_later_window_dominates.json")
    record = usage_of(ledger, SHELF_KEY)
    assert record["status"] == "known"
    exact(record, "usage", "8000000")
    exact(record, "evidenced_floor", "8000000")
    assert record["complete_through"] == "2026-09-30"
    assert {row["transaction_id"]: row["role"] for row in record["contributors"]} == {
        "tx:f3-inception-to-0630": "dominated",
        "tx:f3-inception-to-0930": "window",
        "tx:f3-2026-05-01": "covered",
        "tx:f3-2026-08-15": "covered",
    }
    # Neither the sum of both windows nor the dominated window alone.
    for forbidden in ("13000000", "5000000", "15000000"):
        assert record["usage"]["value"] != forbidden
        assert record["evidenced_floor"]["value"] != forbidden


def test_f4_a_contained_window_exceeding_its_container_is_contradicted():
    """F4: ITD 4,000,000 through 09-30 cannot be below ITD 5,000,000 through 06-30."""
    ledger, _expected = run_fixture("f4_contained_window_exceeds_container.json")
    record = usage_of(ledger, SHELF_KEY)
    assert record["status"] == "contradicted"
    exact(record, "usage", None)
    assert record["usage"]["value"] is None
    assert "contained_window_exceeds_container:tx:f4-inception-to-0630" in record["usage"]["note"]
    # A contradicted usage states no floor: 4,000,000 is not a bound once the
    # windows disagree, and neither is 5,000,000.
    exact(record, "evidenced_floor", None)
    assert record["evidenced_floor"]["status"] == "contradicted"
    assert {row["transaction_id"]: row["role"] for row in record["contributors"]} == {
        "tx:f4-inception-to-0630": "dominated",
        "tx:f4-inception-to-0930": "window",
    }
    assert ledger.support == "partial"
    assert f"contradicted:{SHELF_KEY}" in ledger.support_limits()


def test_f5_partially_overlapping_windows_are_not_apportionable():
    """F5: [01-01,06-30] 3,000,000 against [04-01,09-30] 2,000,000."""
    ledger, _expected = run_fixture("f5_overlapping_windows_not_apportionable.json")
    record = usage_of(ledger, SHELF_KEY)
    assert record["status"] == "unknown"
    exact(record, "usage", None)
    assert "overlapping_cumulative_windows_not_apportionable:path:shelf:2025" in record["usage"]["note"]
    # The floor is the larger window, never their sum: the overlap is not apportioned.
    exact(record, "evidenced_floor", "3000000")
    assert record["evidenced_floor"]["value"] != "5000000"
    assert record["complete_through"] is None
    assert {row["transaction_id"]: row["role"] for row in record["contributors"]} == {
        "tx:f5-2026-h1": "window",
        "tx:f5-2026-0401-0930": "window",
    }


def test_f6_covered_individuals_exceeding_their_window_are_contradicted():
    """F6: 700,000 + 600,000 of individuals cannot sit inside a 1,000,000 window."""
    ledger, _expected = run_fixture("f6_individual_exceeds_cumulative.json")
    record = usage_of(ledger, SHELF_KEY)
    assert record["status"] == "contradicted"
    exact(record, "usage", None)
    assert "individual_exceeds_cumulative:tx:f6-inception-to-date" in record["usage"]["note"]
    exact(record, "evidenced_floor", None)
    assert record["evidenced_floor"]["status"] == "contradicted"
    assert {row["transaction_id"]: row["role"] for row in record["contributors"]} == {
        "tx:f6-inception-to-date": "window",
        "tx:f6-2026-05-01": "covered",
        "tx:f6-2026-06-15": "covered",
    }
    assert ledger.support == "partial"
    # 1,300,000 is never chosen: a contradiction is reported, never resolved.
    assert record["usage"]["value"] != "13000000" and record["usage"]["value"] != "1300000"


def test_f7_one_takedown_in_two_filings_counts_once():
    """F7: a 424B5 and an 8-K stating the same takedown share one transaction_id."""
    ledger, _expected = run_fixture("f7_one_event_two_filings_counts_once.json")
    assert len(ledger.transactions) == 1
    transaction = ledger.transactions[0]
    assert transaction["transaction_id"] == "tx:f7-2026-03-01"
    assert len(transaction["observation_ids"]) == 2
    assert transaction["status"] == "observed"
    exact_value = transaction["gross_proceeds_usd"]
    assert exact_value == "3000000"
    record = usage_of(ledger, SHELF_KEY)
    assert record["status"] == "known"
    exact(record, "usage", "3000000")
    exact(record, "evidenced_floor", "3000000")
    assert record["usage"]["value"] != "6000000"
    assert [row["transaction_id"] for row in record["contributors"]] == ["tx:f7-2026-03-01"]


def test_f8_a_filing_coverage_record_completes_the_floor():
    """F8: individuals alone never establish completeness; a 424B attestation does."""
    with_coverage, _expected = run_fixture("f8_coverage_record_completes_the_floor.json",
                                          "with_coverage")
    record = usage_of(with_coverage, SHELF_KEY)
    assert record["status"] == "known"
    exact(record, "usage", "7000000")
    exact(record, "evidenced_floor", "7000000")
    assert record["complete_through"] == "2026-09-30"
    assert {row["role"] for row in record["contributors"]} == {"added"}

    without, _expected = run_fixture("f8_coverage_record_completes_the_floor.json",
                                     "without_coverage")
    bare = usage_of(without, SHELF_KEY)
    assert bare["status"] == "unknown"
    exact(bare, "usage", None)
    exact(bare, "evidenced_floor", "7000000")
    assert bare["complete_through"] is None
    assert bare["usage_through_complete"] is None
    assert bare["post_window_additions"] is None
    assert bare["evidenced_floor"]["value"] != "0"
    assert f"usage_history_incomplete:{SHELF_KEY}" in unknown_ids(without)
    # The two ledgers differ only by the coverage record, so their floors agree.
    assert record["evidenced_floor"]["value"] == bare["evidenced_floor"]["value"]


def test_f9_a_contiguous_programme_window_chain_is_known():
    """F9: Q1 + Q2 chain from the programme inception; a gap stops the chain."""
    chain, _expected = run_fixture("f9_programme_window_chain.json", "contiguous_chain")
    record = usage_of(chain, PROGRAMME_KEY)
    assert record["usage_key"] == PROGRAMME_KEY
    assert record["status"] == "known"
    exact(record, "usage", "2500000")
    exact(record, "evidenced_floor", "2500000")
    assert record["complete_through"] == "2026-06-30"
    assert {row["transaction_id"]: row["role"] for row in record["contributors"]} == {
        "tx:f9-2026-q1": "window", "tx:f9-2026-q2": "window",
    }

    gap, _expected = run_fixture("f9_programme_window_chain.json", "gap_after_q1")
    broken = usage_of(gap, PROGRAMME_KEY)
    assert broken["status"] == "unknown"
    exact(broken, "usage", None)
    exact(broken, "evidenced_floor", "3000000")
    exact(broken, "usage_through_complete", "1000000")
    assert broken["complete_through"] == "2026-03-31"
    unknown_id = f"usage_history_incomplete:{PROGRAMME_KEY}"
    assert unknown_id in unknown_ids(gap)
    named = next(item for item in gap.unknowns if item.unknown_id == unknown_id)
    assert "10-Q/10-K ATM sales disclosures" in named.resolving_fact


# ---------------------------------------------------------------------------
# §5 instrument versions — anchor, flows, contradictions and the version chain
# ---------------------------------------------------------------------------


def transaction_id_for(item: TransactionObservation) -> str:
    """One economic event per observation here; the id is derived, never invented."""
    return f"tx:{item.observation_id}"


def balance(day: str, amount: str | None, *, unit: str = "instruments", form: str = "10-Q",
            accession: str = "0001-26-000040",
            security_class_id: str = WARRANT_CLASS) -> TransactionObservation:
    return observation(kind="outstanding_balance", basis="point_in_time", event_date=day,
                       instruments=amount if unit == "instruments" else None,
                       principal=amount if unit == "principal_usd" else None,
                       security_class_id=security_class_id, form=form, accepted=day,
                       accession=accession)


def flow(kind: str, day: str, amount: str | None, *, unit: str = "instruments",
         settlement: str | None = None, shares: str | None = None, price: str | None = None,
         accession: str = "0001-26-000041", form: str = "8-K",
         security_class_id: str = WARRANT_CLASS) -> TransactionObservation:
    if shares is None and unit == "instruments":
        shares = amount
    return observation(kind=kind, event_date=day,
                       instruments=amount if unit == "instruments" else None,
                       principal=amount if unit == "principal_usd" else None,
                       shares=shares, price=price,
                       settlement=settlement or ("cash" if kind == "warrant_exercise" else None),
                       security_class_id=security_class_id, form=form, accepted=day,
                       accession=accession)


def note_set(series: str = "series_x0_convertible_notes", status: str = "outstanding",
             principal: str = "2000000", conversion_price: str = "0.50"):
    instrument_id, instrument = SS.make_instrument(
        series, kind="convertible_note", status=status,
        principal_outstanding=principal, conversion_price=conversion_price)
    return instrument_id, SS.instrument_set((instrument_id, instrument))


def version_ledger(events, *, series: str = "series_u_cash_warrants", status: str = "outstanding",
                   note: bool = False, as_of: str = AS_OF, share_observations=(),
                   instruments=None):
    """One instrument, every event bound to it under its own transaction_id."""
    if instruments is None:
        instrument_id, instruments = (note_set(series, status) if note
                                      else warrant_set(series, status))
    else:
        instrument_id = instruments.instruments[0].instrument_id
    bindings = tuple(instrument_binding(item, transaction_id_for(item), instrument_id)
                     for item in events)
    ledger = reconcile(as_of=ts(as_of), observations=tuple(events), bindings=bindings,
                       instruments=instruments, share_observations=share_observations)
    return ledger, instrument_id, instruments


def test_versions_anchor_is_the_latest_balance_on_or_before_as_of():
    first = balance("2026-03-31", "1000000", accession="0001-26-000040")
    second = balance("2026-06-30", "1000000", accession="0001-26-000041")
    later = balance("2026-08-31", "500000", accession="0001-26-000042")
    ledger, instrument_id, instruments = version_ledger([first, second, later], as_of="2026-06-30")
    versions = versions_of(ledger, instrument_id)
    assert [item["effective_date"] for item in versions] == ["2026-03-31", "2026-06-30"]
    assert [item["outstanding"] for item in versions] == ["1000000", "1000000"]
    assert all(item["status"] == "known" for item in versions)
    assert all(item["unit"] == "instruments" for item in versions)
    # The post-as_of balance is invisible: it is not the anchor and mints no version.
    assert transaction_id_for(later) not in versions[-1]["basis_transaction_ids"]
    applied = apply_outstanding(instruments, ledger)
    IE.check_instrument_set(applied)
    term = next(item for instrument in applied.instruments
                if instrument.instrument_id == instrument_id
                for item in instrument.economic_terms if item.name == "instruments_outstanding")
    assert term.value.value == "1000000" and term.value.status == "known"


def test_versions_anchor_missing_is_unknown_never_zero():
    only_flow = flow("warrant_exercise", "2026-05-01", "100000", price="1.00")
    ledger, instrument_id, instruments = version_ledger([only_flow], as_of="2026-06-30")
    versions = versions_of(ledger, instrument_id)
    assert len(versions) == 1
    assert versions[0]["status"] == "unknown"
    assert versions[0]["outstanding"] is None
    assert versions[0]["outstanding"] != "0"
    assert f"instrument_balance_missing:{instrument_id}" in unknown_ids(ledger)
    applied = apply_outstanding(instruments, ledger)
    term = next(item for instrument in applied.instruments
                if instrument.instrument_id == instrument_id
                for item in instrument.economic_terms if item.name == "instruments_outstanding")
    assert term.value.status == "unknown" and term.value.value is None


def test_versions_post_anchor_flows_are_applied_in_date_order():
    events = [
        balance("2026-03-31", "1000000"),
        flow("warrant_exercise", "2026-05-01", "100000", price="1.00"),
        flow("cancellation", "2026-06-01", "50000", accession="0001-26-000042"),
        flow("instrument_issuance", "2026-07-01", "20000", accession="0001-26-000043"),
    ]
    ledger, instrument_id, instruments = version_ledger(events)
    versions = versions_of(ledger, instrument_id)
    assert [item["effective_date"] for item in versions] == [
        "2026-03-31", "2026-05-01", "2026-06-01", "2026-07-01"]
    assert [item["outstanding"] for item in versions] == ["1000000", "900000", "850000", "870000"]
    assert all(item["status"] == "known" for item in versions)
    # Every version is emitted in date order and supersedes exactly its predecessor.
    assert versions[0]["supersedes_version_id"] is None
    for previous, current in zip(versions, versions[1:]):
        assert current["supersedes_version_id"] == previous["version_id"]
    assert versions[-1]["basis_transaction_ids"] == sorted(
        transaction_id_for(item) for item in events)
    applied = apply_outstanding(instruments, ledger)
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    assert replaced.outstanding.value == "870000"
    assert replaced.outstanding.share_basis == "assumed_as_converted"


def test_versions_pre_anchor_flows_are_never_applied_again():
    """A flow already reflected in the anchor balance must not decrement twice."""
    events = [
        flow("warrant_exercise", "2026-02-01", "100000", price="1.00"),
        balance("2026-03-31", "1000000"),
    ]
    ledger, instrument_id, instruments = version_ledger(events, as_of="2026-06-30")
    versions = versions_of(ledger, instrument_id)
    assert len(versions) == 1
    assert versions[0]["effective_date"] == "2026-03-31"
    assert versions[0]["outstanding"] == "1000000"
    assert versions[0]["outstanding"] != "900000"
    assert versions[0]["basis_transaction_ids"] == [transaction_id_for(events[1])]
    applied = apply_outstanding(instruments, ledger)
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    assert replaced.outstanding.value == "1000000"


def test_versions_negative_balance_is_contradicted_never_clamped():
    events = [balance("2026-03-31", "100000"),
              flow("warrant_exercise", "2026-05-01", "250000", price="1.00")]
    ledger, instrument_id, instruments = version_ledger(events, as_of="2026-06-30")
    versions = versions_of(ledger, instrument_id)
    assert [item["outstanding"] for item in versions] == ["100000", "-150000"]
    assert versions[-1]["status"] == "contradicted"
    assert f"flows_exceed_balance:{instrument_id}" in versions[-1]["flags"]
    assert versions[-1]["outstanding"] != "0"
    assert Decimal(versions[-1]["outstanding"]) == Decimal("-150000")
    assert ledger.support == "partial"
    assert f"contradicted:{instrument_id}" in ledger.support_limits()
    applied = apply_outstanding(instruments, ledger)
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    term = next(item for item in replaced.economic_terms if item.name == "instruments_outstanding")
    assert term.status == "contradicted"
    assert term.value.status == "contradicted" and term.value.value is None
    assert replaced.outstanding.status == "contradicted" and replaced.outstanding.value is None


def test_versions_two_balances_explained_by_the_flows_between_them():
    events = [balance("2026-03-31", "1000000", accession="0001-26-000040"),
              flow("warrant_exercise", "2026-05-01", "100000", price="1.00"),
              balance("2026-06-30", "900000", accession="0001-26-000041")]
    ledger, instrument_id, _instruments = version_ledger(events)
    versions = versions_of(ledger, instrument_id)
    # SPEC_X0 §5: a flow between two reported balances is explained by the later
    # balance; it does not mint its own version. Post-anchor flows (after the
    # latest balance) are the only flows that carry the running balance forward.
    assert [item["effective_date"] for item in versions] == ["2026-03-31", "2026-06-30"]
    second_balance = versions[-1]
    assert second_balance["supersedes_version_id"] == versions[0]["version_id"]
    assert second_balance["outstanding"] == "900000"
    assert second_balance["explained_decrease"] == "100000"
    assert second_balance["explained_increase"] == "0"
    assert second_balance["unexplained_delta"] == "0"
    assert Decimal(second_balance["unexplained_delta"]) == Decimal("0")
    assert second_balance["status"] == "known"
    assert unknown_ids(ledger) == []


def test_versions_two_balances_leave_an_unexplained_delta_that_is_never_plugged():
    events = [balance("2026-03-31", "1000000", accession="0001-26-000040"),
              flow("warrant_exercise", "2026-05-01", "100000", price="1.00"),
              balance("2026-06-30", "950000", accession="0001-26-000041")]
    ledger, instrument_id, _instruments = version_ledger(events)
    versions = versions_of(ledger, instrument_id)
    second_balance = versions[-1]
    # 950,000 - (1,000,000 - 100,000 + 0) = +50,000, reported exactly, never plugged.
    assert second_balance["outstanding"] == "950000"
    assert second_balance["explained_decrease"] == "100000"
    assert second_balance["explained_increase"] == "0"
    assert second_balance["unexplained_delta"] == "50000"
    assert Decimal(second_balance["unexplained_delta"]) == Decimal("950000") - (
        Decimal("1000000") - Decimal("100000"))
    assert second_balance["status"] == "known"
    assert second_balance["flags"] == []
    assert ledger.support == "supported"


def test_versions_retired_instrument_is_not_decremented_again():
    events = [balance("2026-03-31", "0"),
              flow("warrant_exercise", "2026-05-01", "100000", price="1.00")]
    ledger, instrument_id, instruments = version_ledger(events, series="series_x0_retired_warrants",
                                                        status="retired", as_of="2026-06-30")
    versions = versions_of(ledger, instrument_id)
    assert [item["outstanding"] for item in versions] == ["0", "0"]
    assert versions[-1]["flags"] == [f"already_retired"]
    assert versions[-1]["status"] == "known"
    assert versions[-1]["outstanding"] != "-100000"
    assert ledger.support == "supported"
    applied = apply_outstanding(instruments, ledger)
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    assert replaced.status == "retired"
    assert replaced.outstanding.value == "0"


def test_versions_zero_balance_flags_a_pending_retirement_decision():
    events = [balance("2026-03-31", "1000000"),
              flow("warrant_exercise", "2026-05-01", "1000000", price="1.00")]
    ledger, instrument_id, instruments = version_ledger(events, as_of="2026-06-30")
    versions = versions_of(ledger, instrument_id)
    assert versions[-1]["outstanding"] == "0"
    assert versions[-1]["status"] == "known"
    assert versions[-1]["flags"] == [f"retirement_decision_pending:{instrument_id}"]
    # X0 flags the decision; it never changes the I0 status.
    assert next(item for item in instruments.instruments
                if item.instrument_id == instrument_id).status == "outstanding"
    applied = apply_outstanding(instruments, ledger)
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    assert replaced.status == "outstanding"
    assert replaced.outstanding.value == "0"


def test_versions_positive_balance_after_an_i0_retirement_is_contradicted():
    events = [balance("2026-03-31", "500000")]
    ledger, instrument_id, instruments = version_ledger(events, series="series_x0_retired_conflict",
                                                        status="retired", as_of="2026-06-30")
    versions = versions_of(ledger, instrument_id)
    assert versions[-1]["outstanding"] == "500000"
    assert versions[-1]["status"] == "contradicted"
    assert f"retired_instrument_with_positive_balance:{instrument_id}" in versions[-1]["flags"]
    assert ledger.support == "partial"
    assert f"contradicted:{instrument_id}" in ledger.support_limits()
    applied = apply_outstanding(instruments, ledger)
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    assert replaced.outstanding.status == "contradicted"


def test_versions_a_flow_with_no_amount_is_unknown_never_zero():
    events = [balance("2026-03-31", "1000000"),
              flow("warrant_exercise", "2026-05-01", None, shares=None, price="1.00")]
    ledger, instrument_id, _instruments = version_ledger(events, as_of="2026-06-30")
    versions = versions_of(ledger, instrument_id)
    assert [item["outstanding"] for item in versions] == ["1000000", None]
    assert versions[-1]["status"] == "unknown"
    assert f"instrument_flow_amount_unknown:{transaction_id_for(events[1])}" in unknown_ids(ledger)


def test_versions_a_convertible_note_is_tracked_in_principal_usd():
    events = [balance("2026-03-31", "2000000", unit="principal_usd", security_class_id=CLASS),
              flow("conversion", "2026-05-01", "500000", unit="principal_usd",
                   shares="1000000", security_class_id=CLASS)]
    ledger, instrument_id, instruments = version_ledger(events, note=True)
    versions = versions_of(ledger, instrument_id)
    assert [item["unit"] for item in versions] == ["principal_usd", "principal_usd"]
    assert [item["outstanding"] for item in versions] == ["2000000", "1500000"]
    applied = apply_outstanding(instruments, ledger)
    IE.check_instrument_set(applied)
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    terms = {item.name: item for item in replaced.economic_terms}
    assert terms["principal_outstanding"].value.value == "1500000"
    assert replaced.outstanding.unit == "usd"
    assert replaced.outstanding.value == "1500000"
    assert replaced.provenance.input_family == "transaction_observations"
    # A conversion pays the issuer nothing (§7).
    assert cash_of(ledger, transaction_id_for(events[1]))["realized_cash_kind"] == "no_cash"


def test_realized_cash_of_a_redemption_is_never_its_principal():
    """§7: a redemption can pay a premium or a discount, so principal is not cash paid."""
    events = [balance("2026-03-31", "2000000", unit="principal_usd", security_class_id=CLASS),
              flow("redemption", "2026-05-01", "500000", unit="principal_usd",
                   security_class_id=CLASS)]
    ledger, instrument_id, _ = version_ledger(events, note=True)
    cash = cash_of(ledger, transaction_id_for(events[1]))
    assert cash["realized_cash_kind"] == "repayment"
    assert cash["gross_usd"] is None
    assert cash["net_usd"] is None
    assert cash["status"] == "unknown"
    # The principal still decrements the note; only the cash claim is withheld.
    assert [item["outstanding"] for item in versions_of(ledger, instrument_id)] == ["2000000", "1500000"]


def test_realized_cash_of_a_redemption_is_the_reported_cash_paid():
    paid = observation(kind="redemption", event_date="2026-05-01", principal="500000",
                       gross="510000", net="510000", security_class_id=CLASS, form="8-K",
                       accepted="2026-05-01", accession="0001-26-000041")
    events = [balance("2026-03-31", "2000000", unit="principal_usd", security_class_id=CLASS), paid]
    ledger, _, _ = version_ledger(events, note=True)
    cash = cash_of(ledger, transaction_id_for(paid))
    assert cash["realized_cash_kind"] == "repayment"
    assert (cash["gross_usd"], cash["net_usd"], cash["status"]) == ("510000", "510000", "known")


def test_versions_apply_outstanding_leaves_an_unbound_instrument_byte_identical():
    bound_id, warrant = warrant_set("series_u_cash_warrants")
    other_id, other = warrant_set("series_untouched_warrants")
    mixed = SS.instrument_set((bound_id, warrant.instruments[0]), (other_id, other.instruments[0]))
    events = [balance("2026-03-31", "1000000"),
              flow("warrant_exercise", "2026-05-01", "100000", price="1.00")]
    bindings = tuple(instrument_binding(item, transaction_id_for(item), bound_id) for item in events)
    ledger = reconcile(as_of=ts("2026-06-30"), observations=tuple(events), bindings=bindings,
                       instruments=mixed)
    applied = apply_outstanding(mixed, ledger)
    IE.check_instrument_set(applied)
    untouched = next(item for item in applied.instruments if item.instrument_id == other_id)
    original = next(item for item in mixed.instruments if item.instrument_id == other_id)
    assert untouched.as_record() == original.as_record()
    replaced = next(item for item in applied.instruments if item.instrument_id == bound_id)
    assert replaced.outstanding.value == "900000"
    assert replaced.provenance.input_family == "transaction_observations"
    assert original.provenance.input_family != "transaction_observations"


# ---------------------------------------------------------------------------
# Review focus (2) end to end — I1 reads the post-X0 claim
# ---------------------------------------------------------------------------


def test_apply_outstanding_evaluate_supply_end_to_end():
    """900,000 in ``as_converted_claims``; the 100,000 shares appear once, in §6."""
    ledger, instrument_id, instruments = a27_ledger()
    applied = apply_outstanding(instruments, ledger)
    IE.check_instrument_set(applied)
    selected_scenario = SS.scenario([SS.selection(instrument_id, "warrant_exercise", "cash")])
    share_basis = SS.basis()
    before_envelope, before_trace = SS.evaluate(instruments, share_basis, selected_scenario)
    after_envelope, after_trace = SS.evaluate(applied, share_basis, selected_scenario)

    claims_before = SS.component(before_envelope, "as_converted_claims")
    claims_after = SS.component(after_envelope, "as_converted_claims")
    assert claims_before.status == "known" and claims_before.value == "1000000"
    assert claims_after.status == "known" and claims_after.value == "900000"
    assert Decimal(claims_after.value) == Decimal("900000")
    assert SS.unknown_ids(after_envelope) == []

    row = SS.rows_by_route(after_trace)[instrument_id]
    assert row["underlying_shares"] == "900000"
    assert row["incremental_shares"] == "900000"
    # The already-exercised 100,000 is never counted again as future issuance.
    assert "100000" not in (row["underlying_shares"], row["incremental_shares"])
    assert SS.rows_by_route(before_trace)[instrument_id]["underlying_shares"] == "1000000"

    assert len(ledger.share_reconciliations) == 1
    reconciliation = ledger.share_reconciliations[0]
    assert reconciliation["evidenced_net_issuance"] == "100000"
    assert reconciliation["observed_delta"] == "100000"
    assert reconciliation["unexplained_delta"] == "0"
    assert reconciliation["transaction_ids"] == ["tx:exercise-2026-05-01"]

    # The two components stay separate facts: the historical exercise is not supply.
    assert SS.component(after_envelope, "existing_outstanding").value == "10000000"
    assert SS.cash_by_route(after_envelope)[instrument_id].gross.value == "900000"
    assert cash_of(ledger, "tx:exercise-2026-05-01")["realized_cash_kind"] == "proceeds"


# ---------------------------------------------------------------------------
# Audit repair — one shared window cover; a contradiction never yields a number
# ---------------------------------------------------------------------------


def warrant_balance(day: str = "2026-03-31", value: str = "1000000", **over) -> TransactionObservation:
    over.setdefault("accepted", day)
    over.setdefault("form", "10-Q")
    return observation(kind="outstanding_balance", basis="point_in_time", event_date=day,
                       instruments=value, security_class_id=WARRANT_CLASS, **over)


def exercise_window(start: str, end: str = "2026-06-30") -> TransactionObservation:
    return observation(kind="warrant_exercise", basis="cumulative", period_start=start, period_end=end,
                       shares="100000", instruments="100000", settlement="cash", gross="100000",
                       form="10-Q", accepted=end, accession="0001-26-000012")


def test_a_contradicted_exercise_leaves_the_balance_contradicted_never_partly_decremented():
    """Two filings disagreeing on one exercise: no version is the anchor less either of them."""
    instrument_id, instruments = warrant_set()
    balance = warrant_balance()
    first = observation(kind="warrant_exercise", event_date="2026-05-01", shares="100000",
                        instruments="100000", settlement="cash", price="1.00", gross="100000",
                        form="8-K", accepted="2026-05-01", accession="0001-26-000010")
    second = observation(kind="warrant_exercise", event_date="2026-05-01", shares="150000",
                         instruments="150000", settlement="cash", price="1.00", gross="150000",
                         form="10-Q", accepted="2026-06-15", accession="0001-26-000011")
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(balance, first, second),
                       bindings=(instrument_binding(balance, "tx:bal", instrument_id),
                                 instrument_binding(first, "tx:ex", instrument_id),
                                 instrument_binding(second, "tx:ex", instrument_id)),
                       instruments=instruments)
    assert by_id(ledger)["tx:ex"]["status"] == "contradicted"
    latest = versions_of(ledger, instrument_id)[-1]
    assert latest["effective_date"] == "2026-05-01"
    assert latest["outstanding"] is None and latest["status"] == "contradicted"
    assert any(flag.endswith(":tx:ex") for flag in latest["flags"]), latest["flags"]
    assert all(item["outstanding"] in (None, "1000000") for item in versions_of(ledger, instrument_id))

    applied = apply_outstanding(instruments, ledger)
    IE.check_instrument_set(applied)
    replaced = next(item for item in applied.instruments if item.instrument_id == instrument_id)
    terms = {term.name: term for term in replaced.economic_terms}
    assert terms["instruments_outstanding"].value.status == "contradicted"
    assert terms["instruments_outstanding"].value.value is None


def test_an_individual_sale_inside_a_counted_window_is_listed_but_never_added_twice():
    """Usage and §6 share the §4 cover: the May sale is inside the Q2 window total."""
    window = observation(kind="atm_sales", basis="cumulative", period_start="2026-04-01",
                         period_end="2026-06-30", shares="500000", gross="5000000",
                         form="10-Q", accepted="2026-06-30")
    sale = observation(kind="atm_sales", event_date="2026-05-01", shares="100000", gross="1000000",
                       form="8-K", accepted="2026-05-02", accession="0001-26-000002")
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(window, sale),
                       bindings=(binding(window, "tx:q2-window", programme_inception_date="2026-04-01"),
                                 binding(sale, "tx:may-sale")),
                       registration_paths=(shelf_path_record(),),
                       share_observations=(share_ref("2026-03-31", "10000000"),
                                           share_ref("2026-06-30", "10500000")))
    exact(usage_of(ledger), "usage", "5000000")
    reconciliation = ledger.share_reconciliations[0]
    assert reconciliation["status"] == "known"
    assert reconciliation["observed_delta"] == "500000"
    assert reconciliation["evidenced_net_issuance"] == "500000"
    assert reconciliation["unexplained_delta"] == "0"
    assert reconciliation["transaction_ids"] == ["tx:may-sale", "tx:q2-window"]


def test_two_inception_to_date_totals_for_one_period_end_are_a_contradiction_with_no_floor():
    first = observation(basis="cumulative", period_end="2026-06-30", gross="5000000", accepted="2026-06-30")
    second = observation(basis="cumulative", period_end="2026-06-30", gross="5200000",
                         accepted="2026-07-02", form="10-Q", accession="0001-26-000003")
    ledger = reconcile(observations=(first, second),
                       bindings=(binding(first, "tx:itd-a"), binding(second, "tx:itd-b")),
                       registration_paths=(shelf_path_record(),))
    record = usage_of(ledger)
    assert record["usage"]["status"] == "contradicted"
    exact(record, "usage", None)
    exact(record, "evidenced_floor", None)
    assert record["evidenced_floor"]["status"] == "contradicted"


def test_a_cumulative_exercise_window_wholly_after_the_balance_is_counted_when_it_closes():
    """SPEC_X0 §5 step 2: only the window total is known, so no version is stated mid-window."""
    instrument_id, instruments = warrant_set()
    balance = warrant_balance()
    window = exercise_window("2026-04-01")
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(balance, window),
                       bindings=(instrument_binding(balance, "tx:bal", instrument_id),
                                 instrument_binding(window, "tx:q2-exercises", instrument_id)),
                       instruments=instruments)
    versions = versions_of(ledger, instrument_id)
    assert [item["effective_date"] for item in versions] == ["2026-03-31", "2026-06-30"]
    assert (versions[-1]["outstanding"], versions[-1]["status"]) == ("900000", "known")


def test_an_exercise_window_straddling_the_balance_date_is_unknown_never_apportioned():
    instrument_id, instruments = warrant_set()
    balance = warrant_balance()
    window = exercise_window("2026-03-01")
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(balance, window),
                       bindings=(instrument_binding(balance, "tx:bal", instrument_id),
                                 instrument_binding(window, "tx:q2-exercises", instrument_id)),
                       instruments=instruments)
    latest = versions_of(ledger, instrument_id)[-1]
    assert latest["effective_date"] == "2026-04-01"
    assert (latest["outstanding"], latest["status"]) == (None, "unknown")
    assert latest["flags"] == ["window_straddles_interval:tx:q2-exercises"]
    assert "instrument_flow_window_not_apportioned:tx:q2-exercises" in unknown_ids(ledger)


def test_a_programme_key_stated_by_one_filing_only_is_a_contradiction_not_a_crash():
    first = observation(kind="atm_sales", event_date="2026-05-01", gross="1000000", form="8-K",
                        accepted="2026-05-02")
    second = observation(kind="atm_sales", event_date="2026-05-01", gross="1000000", form="10-Q",
                         accepted="2026-06-15", accession="0001-26-000004")
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(first, second),
                       bindings=(binding(first, "tx:may", programme_key="atm1"), binding(second, "tx:may")),
                       registration_paths=(shelf_path_record(),))
    assert by_id(ledger)["tx:may"]["status"] == "contradicted"


def test_one_amount_written_two_ways_is_one_value_not_a_contradiction():
    first = observation(kind="atm_sales", event_date="2026-05-01", gross="1000000", form="8-K",
                        accepted="2026-05-02")
    second = observation(kind="atm_sales", event_date="2026-05-01", gross="1000000.00", form="10-Q",
                         accepted="2026-06-15", accession="0001-26-000004")
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(first, second),
                       bindings=(binding(first, "tx:may"), binding(second, "tx:may")),
                       registration_paths=(shelf_path_record(),))
    record = by_id(ledger)["tx:may"]
    assert record["status"] == "observed"
    assert Decimal(record["gross_proceeds_usd"]) == Decimal("1000000")


def test_two_balances_for_one_day_that_disagree_are_contradicted_never_chosen_between():
    instrument_id, instruments = warrant_set()
    first = warrant_balance()
    second = warrant_balance(value="900000", form="8-K", accession="0001-26-000020")
    ledger = reconcile(as_of=ts("2026-06-30"), observations=(first, second),
                       bindings=(instrument_binding(first, "tx:bal-a", instrument_id),
                                 instrument_binding(second, "tx:bal-b", instrument_id)),
                       instruments=instruments)
    versions = versions_of(ledger, instrument_id)
    assert len(versions) == 1
    assert versions[0]["effective_date"] == "2026-03-31"
    assert (versions[0]["outstanding"], versions[0]["status"]) == (None, "contradicted")
    assert versions[0]["flags"] == [f"conflicting_balances:{instrument_id}"]


def test_apply_outstanding_refuses_a_ledger_dated_after_the_instrument_set():
    instrument_id, instruments = warrant_set()
    balance = warrant_balance()
    ledger = reconcile(as_of=ts("2026-12-31"), observations=(balance,),
                       bindings=(instrument_binding(balance, "tx:bal", instrument_id),),
                       instruments=instruments)
    with pytest.raises(c.ContractViolation, match="is after instrument set as_of"):
        apply_outstanding(instruments, ledger)


@pytest.mark.parametrize("text", ["1E+6", "1_000", "+5", " 5", "5.", ".5", "05"])
def test_only_plain_decimal_text_is_an_exact_amount(text):
    with pytest.raises(c.ContractViolation, match="is not a plain exact decimal"):
        observation(event_date="2026-05-01", gross=text)


def test_no_float_literal_in_this_test_file_outside_the_refusal_tests():
    """The suite states exact values; only the float-refusal tests hold a float."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            offenders.append(node.lineno)
    allowed = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_float_refusal"):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Constant) and isinstance(inner.value, float):
                    allowed.add(inner.lineno)
    assert allowed, "the float-refusal tests must still hold a float literal"
    assert sorted(offenders) == sorted(allowed), sorted(set(offenders) - allowed)
