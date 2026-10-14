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
