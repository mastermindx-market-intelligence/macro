"""F0b: the financials binder over the EXISTING Fundamental Forensics service.

The binder (``scripts.build_capital_structure_capacity_inputs``) maps a CS
issuer to its FIF entity over the shipped coverage contracts, selects ONE
instant balance-sheet date provable at the cutoff, runs the real
``execute_financial_query`` over exactly the three bound metrics, and emits
``capital_structure.financial_item_observation.v1`` facts — or one internal
DETAIL beside the closed published denial
``companyfacts_snapshot_unavailable`` (SPEC_U1B §2 vocabulary is closed).

Tests are hermetic: the fake provider serves the committed FIP1 fixture
dataset through the real query kernel.  ``execute_financial_query`` is
monkeypatched only where no fixture can express the case (a receipt with
every cell refused; a filing that became available after the cutoff).

Test map (FROZEN SPEC): T1 mode gate · T2 store failure · T3 coverage ·
T4 resolve failures · T5 happy path · T6 point-in-time · T7 missing cells ·
T8 forbidden fields · T9 funding intake · T10 build determinism ·
T11 ambiguous coverage.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import tests.test_capital_structure_funding as F
import tests.test_capital_structure_scenario_inputs as U1B
from engine.capital_structure.funding import FORBIDDEN_FIELDS, ITEM_RULES
from engine.capital_structure.issuer_state_contracts import sha256_of
from engine.capital_structure.scenario_inputs import (
    CAPACITY_INPUTS_FILENAME,
    financial_inputs_from_record,
)
from engine.fundamental_forensics.query_service import (
    FinancialQueryAdmissionError,
    FinancialQueryUnavailableError,
    fip1_fixture_dataset,
)
import scripts.build_capital_structure_capacity_inputs as producer

REPO = Path(__file__).resolve().parents[1]

#: After the fixture's last filing (available 2025-02-15) AND the governed
#: metric rules (available 2026-08-02T00:00:00Z in the shipped registry).
AS_OF = "2026-09-30T00:00:00Z"
FIP1_ENTITY = "mmx.issuer.fip1"
AAPL_ISSUER = "sec:cik:0000320193"  # covered: coverage/five_issuer_v1.json -> ISS:US-XNAS-AAPL
COMPANYFACTS_DENIAL = ("companyfacts_snapshot_unavailable",)
FACT_KEYS = {
    "schema",
    "item_id",
    "item_kind",
    "availability",
    "amount",
    "measured_at",
    "period_start",
    "period_end",
    "due_date",
    "gross_net",
    "condition",
    "source",
    "available_at",
}
SOURCE_KEYS = {"owner", "metric_id", "term_name", "receipt_sha256", "accession", "filed"}
ITEM_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9:._/-]{0,199}\Z")
DECIMAL_RE = re.compile(r"\A-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


# ---------------------------------------------------------------------------
# Fakes (hermetic; the query kernel itself stays real)
# ---------------------------------------------------------------------------


class _Fip1Provider:
    """Serves the committed FIP1 fixture dataset for its entity id alone."""

    def __init__(self, dataset: Any) -> None:
        self._dataset = dataset
        self.resolved: list[str] = []

    def resolve(self, entity_id: str) -> Any:
        self.resolved.append(entity_id)
        if entity_id == FIP1_ENTITY:
            return self._dataset
        raise FinancialQueryAdmissionError(400, "unknown entity")


class _RaisingProvider:
    """resolve() that always raises the given exception."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def resolve(self, entity_id: str) -> Any:
        raise self._exc


def _fip1_provider() -> _Fip1Provider:
    return _Fip1Provider(fip1_fixture_dataset(REPO))


def _resolver(_issuer: str) -> str:
    """The tests-only entity seam (F0b §1): covered CS issuer -> fixture entity."""
    return FIP1_ENTITY


def _resolved_happy(
    provider: Any = None, as_of: str = AS_OF, issuer: str = AAPL_ISSUER
) -> tuple[tuple[dict[str, Any], ...], str, str | None]:
    return producer._resolve_financial_facts(
        issuer,
        as_of,
        provider=provider if provider is not None else _fip1_provider(),
        entity_resolver=_resolver,
    )


def _bound_happy(provider: Any = None, as_of: str = AS_OF):
    return producer._bind_financials(
        AAPL_ISSUER,
        as_of,
        provider=provider if provider is not None else _fip1_provider(),
        entity_resolver=_resolver,
    )


def _keys(value: Any) -> "set[str]":
    """Every mapping key anywhere inside a JSON-able value (recursive)."""
    out: set[str] = set()
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, nested in item.items():
                out.add(key)
                stack.append(nested)
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
    return out


# ---------------------------------------------------------------------------
# T1 — dataset mode gate: no provider without explicit production mode
# ---------------------------------------------------------------------------


def test_t1_dataset_mode_gate_selects_no_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    class _NoGolden:  # pragma: no cover - constructed only on a violation
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise AssertionError("golden corpus is not reachable from production code")

    monkeypatch.setattr(
        "engine.fundamental_forensics.ixbrl_raw_ledger.GoldenAaplFinancialQueryProvider",
        _NoGolden,
    )
    monkeypatch.delenv(producer.FIF_FINANCIAL_DATASET_MODE_ENV, raising=False)
    assert producer._default_financial_provider() == (
        None,
        "fif_production_store_not_selected",
    )
    monkeypatch.setenv(producer.FIF_FINANCIAL_DATASET_MODE_ENV, "golden")
    assert producer._default_financial_provider() == (
        None,
        "fif_production_store_not_selected",
    )

    facts, cash_basis, detail = producer._resolve_financial_facts(
        AAPL_ISSUER, AS_OF, provider=None, provider_detail=None
    )
    assert (facts, cash_basis, detail) == ((), "unknown", "fif_production_store_not_selected")

    entry = producer._bind_financials(AAPL_ISSUER, AS_OF)
    assert entry.family == "financials"
    assert entry.support == "unavailable"
    assert entry.reason_codes == COMPANYFACTS_DENIAL
    assert entry.binding is None
    assert entry.record is None

    from app.forensics import FIF_FINANCIAL_DATASET_MODE_ENV as APP_MODE_ENV

    assert APP_MODE_ENV == producer.FIF_FINANCIAL_DATASET_MODE_ENV


# ---------------------------------------------------------------------------
# T2 — production mode with no usable store
# ---------------------------------------------------------------------------


def test_t2_production_without_a_store_is_dataset_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(producer.FIF_FINANCIAL_DATASET_MODE_ENV, "production")
    monkeypatch.setattr(
        "engine.fundamental_forensics.production_datasets.build_production_dataset_store",
        lambda *args: None,
    )
    assert producer._default_financial_provider() == (None, "fif_dataset_unavailable")

    def _explode(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("store exploded")

    monkeypatch.setattr(
        "engine.fundamental_forensics.production_datasets.build_production_dataset_store",
        _explode,
    )
    assert producer._default_financial_provider() == (None, "fif_dataset_unavailable")


# ---------------------------------------------------------------------------
# T3 — coverage mapping: uncovered and malformed issuer ids
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "issuer_id",
    [
        "sec:cik:9999999999",  # well-formed 10-digit CIK, absent from coverage
        "cik:0001234567",  # not the sec:cik spelling
        "sec:cik:12345",  # not zero-padded 10 digits
        "sec:cik:0000320193X",  # trailing junk
    ],
)
def test_t3_uncovered_or_malformed_issuer_binds_nothing(issuer_id: str) -> None:
    provider = _fip1_provider()
    facts, cash_basis, detail = producer._resolve_financial_facts(
        issuer_id, AS_OF, provider=provider
    )
    assert (facts, cash_basis, detail) == ((), "unknown", "fif_entity_not_covered")
    assert provider.resolved == []  # mapping fails before any dataset is touched

    entry = producer._bind_financials(issuer_id, AS_OF, provider=provider)
    assert entry.support == "unavailable"
    assert entry.reason_codes == COMPANYFACTS_DENIAL


# ---------------------------------------------------------------------------
# T4 — provider.resolve failures split by admission vs unavailability
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exc", "detail"),
    [
        (FinancialQueryAdmissionError(400, "unknown entity"), "fif_entity_unknown"),
        (FinancialQueryUnavailableError(), "fif_dataset_unavailable"),
        (RuntimeError("kernel down"), "fif_dataset_unavailable"),
    ],
)
def test_t4_resolve_failures_carry_distinct_details(exc: Exception, detail: str) -> None:
    facts, cash_basis, got = producer._resolve_financial_facts(
        AAPL_ISSUER, AS_OF, provider=_RaisingProvider(exc), entity_resolver=_resolver
    )
    assert (facts, cash_basis, got) == ((), "unknown", detail)


# ---------------------------------------------------------------------------
# T5 — happy path: partial bind with exactly the §5 fact shape
# ---------------------------------------------------------------------------


def test_t5_happy_path_binds_partial_financials() -> None:
    provider = _fip1_provider()
    facts, cash_basis, detail = _resolved_happy(provider)
    assert detail is None
    assert cash_basis == "unrestricted_cash"
    assert len(facts) == 2
    assert {fact["item_kind"] for fact in facts} == {"unrestricted_cash", "receivables"}
    assert [fact["item_id"] for fact in facts] == sorted(fact["item_id"] for fact in facts)
    assert all(called == FIP1_ENTITY for called in provider.resolved)

    by_kind = {fact["item_kind"]: fact for fact in facts}
    assert Decimal(by_kind["unrestricted_cash"]["amount"]["value"]) == Decimal("15")
    assert Decimal(by_kind["receivables"]["amount"]["value"]) == Decimal("155")

    as_of_moment = datetime.fromisoformat(AS_OF.replace("Z", "+00:00"))
    for fact in facts:
        assert set(fact) == FACT_KEYS
        assert fact["schema"] == "capital_structure.financial_item_observation.v1"
        assert ITEM_ID_RE.fullmatch(fact["item_id"]) is not None
        assert fact["item_id"].startswith(f"fif:")
        assert fact["availability"] == ITEM_RULES[fact["item_kind"]]["availability"]
        amount = fact["amount"]
        assert set(amount) == {"value", "unit", "status"}
        assert amount["unit"] == "usd" and amount["status"] == "known"
        assert DECIMAL_RE.fullmatch(amount["value"]) is not None
        assert fact["measured_at"] == "2024-12-31"
        assert fact["period_start"] is None and fact["period_end"] is None
        assert fact["due_date"] is None and fact["condition"] is None
        assert fact["gross_net"] == "not_applicable"
        source = fact["source"]
        assert set(source) == SOURCE_KEYS
        assert source["owner"] == "fundamental_forensics"
        assert source["term_name"] is None
        assert re.fullmatch(r"\A[0-9a-f]{64}\Z", source["receipt_sha256"]) is not None
        assert source["accession"] == "0000999999-25-000010"  # the provable filing
        assert source["filed"] == "2025-02-15"
        available = datetime.fromisoformat(fact["available_at"].replace("Z", "+00:00"))
        assert available.tzinfo is not None and available <= as_of_moment

    entry = _bound_happy(provider)
    assert entry.support == "partial"
    assert entry.reason_codes == ()
    assert entry.binding is not None
    assert entry.binding.input_family == "financials"
    assert entry.binding.support == "partial"
    assert entry.binding.as_of == AS_OF
    assert entry.binding.artifact_sha256 == sha256_of(list(facts))
    assert entry.record is not None
    assert entry.record.cash_basis == "unrestricted_cash"
    assert entry.record.facts == facts

    rebuilt = financial_inputs_from_record(entry.record.as_record())
    assert rebuilt.cash_basis == entry.record.cash_basis
    assert rebuilt.facts == entry.record.facts


# ---------------------------------------------------------------------------
# T6 — point-in-time: only filings readable at the cutoff exist
# ---------------------------------------------------------------------------


def _late_filing_dataset() -> SimpleNamespace:
    """Two bound-concept instants; the later filing is readable only later."""
    early = SimpleNamespace(
        concept_qname="us-gaap:CashAndCashEquivalentsAtCarryingValue",
        context=SimpleNamespace(instant=date(2030, 12, 31)),
        source=SimpleNamespace(accession="acc-early"),
    )
    late = SimpleNamespace(
        concept_qname="us-gaap:CashAndCashEquivalentsAtCarryingValue",
        context=SimpleNamespace(instant=date(2031, 12, 31)),
        source=SimpleNamespace(accession="acc-late"),
    )
    return SimpleNamespace(
        ledger=SimpleNamespace(events=(late, early)),
        filing_metadata={
            "acc-early": {"accession": "acc-early", "available_at": "2030-06-30T00:00:00Z"},
            "acc-late": {"accession": "acc-late", "available_at": "2031-06-30T00:00:00Z"},
        },
    )


def test_t6a_selection_never_uses_a_filing_after_the_cutoff() -> None:
    dataset = _late_filing_dataset()
    as_of_moment = datetime(2031, 1, 1, tzinfo=timezone.utc)
    assert producer._select_instant_date(dataset, as_of_moment) == "2030-12-31"


def test_t6b_no_filing_readable_at_the_cutoff_is_no_balance_sheet() -> None:
    provider = _Fip1Provider(_late_filing_dataset())
    facts, cash_basis, detail = producer._resolve_financial_facts(
        AAPL_ISSUER,
        "2030-01-01T00:00:00Z",
        provider=provider,
        entity_resolver=_resolver,
    )
    assert (facts, cash_basis, detail) == ((), "unknown", "fif_no_balance_sheet_before_as_of")
    assert provider.resolved == [FIP1_ENTITY]  # the dataset resolved, then refused


def test_t6c_a_late_filing_is_never_queried_and_never_emitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_bodies: list[dict[str, Any]] = []

    def _spy(*, body: bytes, provider: Any) -> SimpleNamespace:
        request = json.loads(body.decode("utf-8"))
        seen_bodies.append(request)
        return SimpleNamespace(
            sha256="c" * 64,
            envelope={
                "receipt": {
                    "root_cell_ids": ["cell-early", "cell-late"],
                    "nodes": [
                        {
                            "cell_id": "cell-early",
                            "metric_id": "cash_and_cash_equivalents",
                            "period": {"kind": "instant", "end": "2030-12-31"},
                            "state": "value",
                            "value": "7000",
                            "unit": "USD",
                            "provenance": {
                                "accession": "acc-early",
                                "form": "10-K",
                                "filed_at": "2030-02-15",
                                "accepted_at": "2030-06-30T00:00:00Z",
                                "recorded_at": "2030-06-30T00:00:00Z",
                                "filing_metadata_available_at": "2030-06-30T00:00:00Z",
                            },
                        },
                        {
                            "cell_id": "cell-late",
                            "metric_id": "cash_and_cash_equivalents",
                            "period": {"kind": "instant", "end": "2031-12-31"},
                            "state": "value",
                            "value": "999999",
                            "unit": "USD",
                            "provenance": {
                                "accession": "acc-late",
                                "form": "10-K",
                                "filed_at": "2032-02-15",
                                "accepted_at": "2031-06-30T00:00:00Z",
                                "recorded_at": "2031-06-30T00:00:00Z",
                                "filing_metadata_available_at": "2031-06-30T00:00:00Z",
                            },
                        },
                    ],
                }
            },
        )

    monkeypatch.setattr(producer, "execute_financial_query", _spy)
    provider = _Fip1Provider(_late_filing_dataset())
    facts, cash_basis, detail = producer._resolve_financial_facts(
        AAPL_ISSUER,
        "2031-01-01T00:00:00Z",
        provider=provider,
        entity_resolver=_resolver,
    )
    assert detail is None and cash_basis == "unrestricted_cash"
    assert len(facts) == 1
    # the late filing's instant was never requested …
    assert len(seen_bodies) == 1
    request = seen_bodies[0]
    assert request["schema"] == "fundamental_forensics.financial_query_request/v1"
    assert request["entity_id"] == FIP1_ENTITY
    assert request["metric_ids"] == [
        "cash_and_cash_equivalents",
        "short_term_investments",
        "accounts_receivable_net",
    ]
    assert request["policy"]["selection"] == "latest_known_as_of"
    assert request["policy"]["source_snapshot_at"] == "2031-01-01T00:00:00Z"
    assert request["policy"]["recorded_at"] == "2031-01-01T00:00:00Z"
    assert request["periods"] == [
        {"kind": "instant", "start": None, "end": "2030-12-31", "label": "2030-12-31"}
    ]
    # … and its value cannot leak through a hostile receipt either
    assert facts[0]["measured_at"] == "2030-12-31"
    assert facts[0]["amount"] == {"value": "7000", "unit": "usd", "status": "known"}
    assert facts[0]["source"]["receipt_sha256"] == "c" * 64
    assert facts[0]["source"]["accession"] == "acc-early"


# ---------------------------------------------------------------------------
# T7 — refused cells produce absence, never a zero
# ---------------------------------------------------------------------------


def test_t7a_a_missing_kernel_cell_produces_no_fact() -> None:
    facts, _cash_basis, detail = _resolved_happy()
    assert detail is None
    # the fixture ledger carries no short-term-investment concept: the kernel
    # answers "missing", and the binder emits nothing for it
    assert all(fact["item_kind"] != "marketable_securities" for fact in facts)
    assert all(fact["amount"]["value"] != "0" for fact in facts)


def test_t7b_all_cells_refused_is_no_reported_cells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provenance = {
        "accession": "0000999999-25-000010",
        "form": "10-K",
        "filed_at": "2025-02-15",
        "accepted_at": "2025-02-15T16:00:00Z",
        "recorded_at": "2025-02-15T16:00:00Z",
        "filing_metadata_available_at": "2025-02-15T16:00:00Z",
    }

    def _node(cell_id: str, metric_id: str, state: str) -> dict[str, Any]:
        return {
            "cell_id": cell_id,
            "metric_id": metric_id,
            "period": {"kind": "instant", "end": "2024-12-31"},
            "state": state,
            "provenance": dict(provenance),
        }

    def _refused(*, body: bytes, provider: Any) -> SimpleNamespace:
        return SimpleNamespace(
            sha256="d" * 64,
            envelope={
                "receipt": {
                    "root_cell_ids": ["c1", "c2", "c3"],
                    "nodes": [
                        _node("c1", "cash_and_cash_equivalents", "missing"),
                        _node("c2", "short_term_investments", "not_evaluable"),
                        _node("c3", "accounts_receivable_net", "not_applicable"),
                    ],
                }
            },
        )

    monkeypatch.setattr(producer, "execute_financial_query", _refused)
    facts, cash_basis, detail = _resolved_happy()
    assert (facts, cash_basis, detail) == ((), "unknown", "fif_no_reported_cells")


def test_t7c_a_non_usd_cell_is_carried_unknown_not_converted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _eur(*, body: bytes, provider: Any) -> SimpleNamespace:
        return SimpleNamespace(
            sha256="e" * 64,
            envelope={
                "receipt": {
                    "root_cell_ids": ["c1"],
                    "nodes": [
                        {
                            "cell_id": "c1",
                            "metric_id": "cash_and_cash_equivalents",
                            "period": {"kind": "instant", "end": "2024-12-31"},
                            "state": "value",
                            "value": "42",
                            "unit": "iso4217:EUR",
                            "provenance": {
                                "accession": "acc",
                                "form": "10-K",
                                "filed_at": "2025-02-15",
                                "accepted_at": "2025-02-15T16:00:00Z",
                                "recorded_at": "2025-02-15T16:00:00Z",
                                "filing_metadata_available_at": "2025-02-15T16:00:00Z",
                            },
                        }
                    ],
                }
            },
        )

    monkeypatch.setattr(producer, "execute_financial_query", _eur)
    facts, cash_basis, detail = _resolved_happy()
    assert detail is None
    assert len(facts) == 1
    assert facts[0]["amount"] == {"value": None, "unit": "iso4217:eur", "status": "unknown"}
    assert cash_basis == "unknown"  # no known unrestricted cash was bound


# ---------------------------------------------------------------------------
# T8 — no forbidden field anywhere in an emitted fact
# ---------------------------------------------------------------------------


def test_t8_no_forbidden_field_in_any_fact() -> None:
    facts, _cash_basis, detail = _resolved_happy()
    assert detail is None
    assert facts
    for fact in facts:
        assert _keys(fact).isdisjoint(FORBIDDEN_FIELDS)


# ---------------------------------------------------------------------------
# T9 — funding intake: the opening balance is the unrestricted cash only
# ---------------------------------------------------------------------------


def test_t9_project_funding_consumes_the_binder_record() -> None:
    entry = _bound_happy()
    assert entry.record is not None
    schedule = F.project_funding(
        entry.record,
        F.covenants(F.covenant("cov-min-1", "1000000")),
        F.scenario(),
    )  # raises no FundingInputError
    opening = schedule.periods[0].opening_balance
    assert opening.status == "known"
    # unrestricted cash only: receivables (155) are context_only and the
    # (absent) marketable securities are available_after_sale — neither is a
    # member of the unrestricted_cash basis
    assert Decimal(opening.value) == Decimal("15")


# ---------------------------------------------------------------------------
# T10 — two builds over one injected provider are byte-identical
# ---------------------------------------------------------------------------


def test_t10_two_builds_are_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    served = U1B._served_root(tmp_path / "served")
    state = json.loads((served / "state_bundle.json").read_text(encoding="utf-8"))
    issuer_id = str(state["issuers"][0]["request"]["issuer_id"])
    cik = issuer_id.rsplit(":", 1)[-1].zfill(10)
    monkeypatch.setattr(
        producer, "_COVERAGE_INDEX_CACHE", {cik: frozenset({FIP1_ENTITY})}
    )
    provider = _fip1_provider()

    common = {"root": served, "generated_at": "2026-09-30T12:00:00Z"}
    one = producer.build_from_disk(financial_provider=provider, **common)
    bytes_one = (served / CAPACITY_INPUTS_FILENAME).read_bytes()
    two = producer.build_from_disk(financial_provider=provider, **common)
    bytes_two = (served / CAPACITY_INPUTS_FILENAME).read_bytes()

    assert one["status"] == "ok" and two["status"] == "ok"
    assert bytes_one == bytes_two

    parsed = json.loads(bytes_one.decode("utf-8"))
    entry = parsed["issuers"][issuer_id]["financials"]
    assert entry["support"] == "partial"
    assert entry["reason_codes"] == []
    assert entry["record"]["cash_basis"] == "unrestricted_cash"
    assert len(entry["record"]["facts"]) == 2
    assert entry["binding"]["artifact_sha256"] == sha256_of(entry["record"]["facts"])


# ---------------------------------------------------------------------------
# T11 — one CIK bound to two entity ids is refused, never picked
# ---------------------------------------------------------------------------


def test_t11_ambiguous_coverage_mapping_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        producer,
        "_COVERAGE_INDEX_CACHE",
        {"0000320193": frozenset({"ISS:US-XNAS-AAPL", "ISS:US-XNAS-APPL2"})},
    )
    provider = _fip1_provider()
    facts, cash_basis, detail = producer._resolve_financial_facts(
        AAPL_ISSUER, AS_OF, provider=provider
    )
    assert (facts, cash_basis, detail) == ((), "unknown", "fif_entity_ambiguous")
    assert provider.resolved == []

    entry = producer._bind_financials(AAPL_ISSUER, AS_OF, provider=provider)
    assert entry.support == "unavailable"
    assert entry.reason_codes == COMPANYFACTS_DENIAL
