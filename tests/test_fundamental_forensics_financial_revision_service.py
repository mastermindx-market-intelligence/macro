"""FIF-2B: cutoff-safe revision projection over the frozen FIP assembler."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dataclasses import replace
from datetime import datetime, timezone

from engine.fundamental_forensics.financial_intelligence_packet import (
    EntityInput,
    PacketEvidenceDigests,
    PacketQueryRequest,
    assemble_financial_intelligence_packet,
    canonical_json,
    sha256_file,
)
from engine.fundamental_forensics.query import (
    FILING_METADATA_SCHEMA,
    PeriodRequest,
    QueryPolicy,
    QueryValidationError,
)
from engine.fundamental_forensics.query_service import (
    CanonicalEntityBinding,
    FinancialQueryAdmissionError,
    FinancialQueryDataset,
    FinancialQueryUnavailableError,
    UnavailableFinancialQueryProvider,
    execute_financial_query,
    fip1_fixture_dataset,
)
from engine.fundamental_forensics.revision_service import (
    FinancialPacketDataset,
    UnavailableFinancialPacketProvider,
    execute_financial_revisions,
    fip1_packet_dataset,
    packet_dataset_from_fixture,
)
from engine.fundamental_forensics.synthetic_filing_package import (
    build_multihop_revenue_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
_REVISION_SCHEMA = "fundamental_forensics.financial_revision_request/v1"
_QUERY_SCHEMA = "fundamental_forensics.financial_query_request/v1"

# FIP1 is a synthetic industrial issuer with no shipped coverage record; the
# hermetic production-path tests inject its SIC (R1-SIC/R2).
_FIP1_CIK = "0000999999"
_INDUSTRIAL_SIC = "3571"


def _fip1_issuer_sic_resolver(cik: str) -> str | None:
    return _INDUSTRIAL_SIC if cik == _FIP1_CIK else None

T0_SOURCE = "2024-01-01T00:00:00Z"
T1_SOURCE = "2024-12-31T23:59:59Z"
T2_SOURCE = "2025-12-31T23:59:59Z"
T2_RECORDED = "2026-08-03T12:00:00Z"
T3_SOURCE = "2025-12-31T23:59:59Z"
T3_RECORDED = "2026-08-05T12:00:02Z"
HOP_C_SOURCE = "2026-08-05T12:00:02Z"
HOP_B_SYSTEM_READY = "2026-08-04T17:59:59Z"
DELAYED_MAPPING_AFTER = "2026-08-07T00:00:00Z"

FY2023 = {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}
AR_INSTANT = {"kind": "instant", "start": None, "end": "2023-12-31", "label": "2023-12-31"}
FY2023_PERIOD = PeriodRequest.duration("2023-01-01", "2023-12-31", label="FY2023")
AR_PERIOD = PeriodRequest.instant("2023-12-31", label="2023-12-31")

# FIF-2A / PR #5983 accepted kernel query_hash pins. Shared admission must not move them.
_HASH_AS_REPORTED_T1_T2 = "58d438ec81d287f81e6981cf01ac6d16d57cf50689cc826cad39962742efa821"
_HASH_LATEST_KNOWN_T1_T2 = "f275a7e02aff6e1119f1275365549e1fa9aa2d3f45dbc3cd0f4ba5fdb76f1d37"
_HASH_LATEST_KNOWN_T3 = "2f8d30baf2d49aef0cc6936613eca1f9aa980e10ed56da135a75dd4238349915"
_HASH_LATEST_RESTATED_T3 = "531309e192ac923e466365b05380a197f67d6df01c1d5fd9062a0e93aaf20b9f"
_HASH_MIXED_T3 = "26a7ed7d95f861d3352c3a7e5fb6a0f52833ccf69947b10ca9da1f9662c44133"


def _make_request(
    *,
    schema: str = _REVISION_SCHEMA,
    entity_id: str = "mmx.issuer.fip1",
    policy: dict | None = None,
    metric_ids: list | None = None,
    periods: list | None = None,
) -> bytes:
    if policy is None:
        policy = {
            "selection": "latest_known_as_of",
            "source_snapshot_at": T3_SOURCE,
            "recorded_at": T3_RECORDED,
        }
    if metric_ids is None:
        metric_ids = ["revenue"]
    if periods is None:
        periods = [FY2023]
    return json.dumps(
        {
            "schema": schema,
            "entity_id": entity_id,
            "policy": policy,
            "metric_ids": metric_ids,
            "periods": periods,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _fip1_provider(resolved_calls: list | None = None):
    dataset = fip1_packet_dataset(ROOT)

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            if resolved_calls is not None:
                resolved_calls.append(entity_id)
            if entity_id == "mmx.issuer.fip1":
                return dataset
            raise FinancialQueryAdmissionError(400, "unknown entity")

    return _Provider()


def _direct_packet(
    *,
    metric_ids: tuple[str, ...],
    periods: tuple[PeriodRequest, ...],
    source_snapshot_at: str,
    recorded_at: str,
    selection: str = "latest_known_as_of",
    dataset: FinancialPacketDataset | None = None,
) -> dict:
    loaded = dataset if dataset is not None else fip1_packet_dataset(ROOT)
    return assemble_financial_intelligence_packet(
        entity=loaded.entity,
        ledger=loaded.ledger,
        filing_metadata=loaded.filing_metadata,
        query_request=PacketQueryRequest(
            policy=QueryPolicy(
                source_snapshot_at=source_snapshot_at,
                recorded_at=recorded_at,
                selection=selection,
            ),
            metrics=metric_ids,
            periods=periods,
        ),
        metric_registry=loaded.registry,
        context=loaded.context,
        input_digests=loaded.input_digests,
    )


def _t3_latest(**kwargs):
    policy = {
        "selection": "latest_known_as_of",
        "source_snapshot_at": T3_SOURCE,
        "recorded_at": T3_RECORDED,
    }
    policy.update(kwargs.pop("policy_update", {}))
    return _make_request(policy=policy, **kwargs)


# ---------------------------------------------------------------------------
# Direct packet vs HTTP projection
# ---------------------------------------------------------------------------


def test_http_revisions_equal_direct_packet_revisions() -> None:
    provider = _fip1_provider()
    body = _t3_latest()
    result = execute_financial_revisions(body=body, provider=provider)
    packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T3_SOURCE,
        recorded_at=T3_RECORDED,
    )
    assert result.envelope["revisions"] == packet["revisions"]
    assert canonical_json(result.envelope["revisions"]) == canonical_json(packet["revisions"])
    assert result.envelope["packet_ref"]["packet_id"] == packet["packet_id"]
    assert result.envelope["packet_ref"]["content_sha256"] == packet["content_sha256"]
    assert (
        result.envelope["packet_ref"]["governance_bundle_id"]
        == packet["governance"]["governance_bundle_id"]
    )


def test_t2_does_not_leak_t3_revision_or_value() -> None:
    body = _make_request(
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": T2_SOURCE,
            "recorded_at": T2_RECORDED,
        }
    )
    result = execute_financial_revisions(body=body, provider=_fip1_provider())
    packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T2_SOURCE,
        recorded_at=T2_RECORDED,
    )
    assert packet["revisions"] == []
    assert result.envelope["revisions"] == []
    blob = result.body.decode("utf-8")
    assert "1060" not in blob
    assert result.envelope["revisions"] == packet["revisions"]


def test_t3_emits_1050_to_1060_revenue_revision() -> None:
    result = execute_financial_revisions(body=_t3_latest(), provider=_fip1_provider())
    rows = [row for row in result.envelope["revisions"] if row["metric_id"] == "revenue"]
    assert rows
    revenue = rows[0]
    assert revenue["root_value"] == "1050"
    assert revenue["prior_value"] == "1050"
    assert revenue["revised_value"] == "1060"
    assert revenue["revision_hop"] == 1
    assert "1060" in result.body.decode("utf-8")


def test_t3_accounts_receivable_revision_matches_packet() -> None:
    body = _t3_latest(
        metric_ids=["revenue", "accounts_receivable_net"],
        periods=[FY2023, AR_INSTANT],
    )
    result = execute_financial_revisions(body=body, provider=_fip1_provider())
    packet = _direct_packet(
        metric_ids=("revenue", "accounts_receivable_net"),
        periods=(FY2023_PERIOD, AR_PERIOD),
        source_snapshot_at=T3_SOURCE,
        recorded_at=T3_RECORDED,
    )
    assert result.envelope["revisions"] == packet["revisions"]
    ar_rows = [row for row in result.envelope["revisions"] if row["metric_id"] == "accounts_receivable_net"]
    assert ar_rows
    assert ar_rows[0]["root_value"] == "120"
    assert ar_rows[0]["revised_value"] == "121"


def test_revenue_only_request_excludes_ar_revisions() -> None:
    result = execute_financial_revisions(body=_t3_latest(), provider=_fip1_provider())
    assert result.envelope["revisions"]
    assert all(row["metric_id"] == "revenue" for row in result.envelope["revisions"])


def test_multihop_preserves_root_prior_revised() -> None:
    fixture = build_multihop_revenue_fixture()
    dataset = packet_dataset_from_fixture(ROOT, fixture)

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            if entity_id != "mmx.issuer.fip1":
                raise FinancialQueryAdmissionError(400, "unknown entity")
            return dataset

    body = _make_request(
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": HOP_C_SOURCE,
            "recorded_at": T3_RECORDED,
        }
    )
    result = execute_financial_revisions(body=body, provider=_Provider())
    packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=HOP_C_SOURCE,
        recorded_at=T3_RECORDED,
        dataset=dataset,
    )
    assert result.envelope["revisions"] == packet["revisions"]
    hops = {row["revision_hop"]: row for row in result.envelope["revisions"] if row["metric_id"] == "revenue"}
    assert 1 in hops and 2 in hops
    hop1 = hops[1]
    hop2 = hops[2]
    assert hop1["root_value"] == "1050"
    assert hop1["prior_value"] == "1050"
    assert hop1["revised_value"] == "1060"
    assert hop1["root_occurrence_id"] == hop1["parent_occurrence_id"]
    assert hop2["root_value"] == "1050"
    assert hop2["prior_value"] == "1060"
    assert hop2["revised_value"] == "1070"
    assert hop2["lineage_occurrence_ids"] == [
        hop2["root_occurrence_id"],
        hop2["parent_occurrence_id"],
        hop2["revised_occurrence_id"],
    ]
    assert hop2["root_occurrence_id"] == hop1["root_occurrence_id"]
    assert hop2["parent_occurrence_id"] == hop1["revised_occurrence_id"]
    assert hop2["lineage_occurrence_ids"] != [
        hop2["root_occurrence_id"],
        hop2["revised_occurrence_id"],
    ]


def test_multihop_hides_hop_c_before_lineage_readiness() -> None:
    fixture = build_multihop_revenue_fixture()
    dataset = packet_dataset_from_fixture(ROOT, fixture)

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return dataset

    body = _make_request(
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": T2_SOURCE,
            "recorded_at": T2_RECORDED,
        }
    )
    result = execute_financial_revisions(body=body, provider=_Provider())
    assert result.envelope["revisions"] == []
    assert "1070" not in result.body.decode("utf-8")


def test_multihop_intermediate_shows_b_hides_c_until_system_ready() -> None:
    fixture = build_multihop_revenue_fixture()
    dataset = packet_dataset_from_fixture(ROOT, fixture)

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return dataset

    intermediate = _make_request(
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": HOP_C_SOURCE,
            "recorded_at": HOP_B_SYSTEM_READY,
        }
    )
    mid = execute_financial_revisions(body=intermediate, provider=_Provider())
    mid_packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=HOP_C_SOURCE,
        recorded_at=HOP_B_SYSTEM_READY,
        dataset=dataset,
    )
    assert mid.envelope["revisions"] == mid_packet["revisions"]
    hops = {
        row["revision_hop"]: row
        for row in mid.envelope["revisions"]
        if row["metric_id"] == "revenue"
    }
    assert 1 in hops
    assert 2 not in hops
    assert hops[1]["revised_value"] == "1060"
    blob = mid.body.decode("utf-8")
    assert "1060" in blob
    assert "1070" not in blob

    later = _make_request(
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": HOP_C_SOURCE,
            "recorded_at": T3_RECORDED,
        }
    )
    after = execute_financial_revisions(body=later, provider=_Provider())
    after_packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=HOP_C_SOURCE,
        recorded_at=T3_RECORDED,
        dataset=dataset,
    )
    assert after.envelope["revisions"] == after_packet["revisions"]
    later_hops = {
        row["revision_hop"]: row
        for row in after.envelope["revisions"]
        if row["metric_id"] == "revenue"
    }
    assert 2 in later_hops
    assert later_hops[2]["prior_value"] == "1060"
    assert later_hops[2]["revised_value"] == "1070"


def test_delayed_mapping_hides_revision_until_mapping_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_fundamental_forensics_financial_intelligence_packet_r3 import (
        FUTURE_CONCEPT_QNAME,
        _mini_revision_fixture,
        _register_future_concept,
        _registry_with_future_revenue_mapping,
    )

    _register_future_concept(monkeypatch)
    fixture = _mini_revision_fixture(
        child_recorded="2026-08-04T12:00:00Z",
        parent_recorded="2024-02-15T16:05:00Z",
        concept=FUTURE_CONCEPT_QNAME,
    )
    delayed_registry = _registry_with_future_revenue_mapping(
        datetime(2026, 8, 6, tzinfo=timezone.utc)
    )
    dataset = replace(
        packet_dataset_from_fixture(ROOT, fixture),
        registry=delayed_registry,
    )

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return dataset

    before_body = _make_request(
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": T3_SOURCE,
            "recorded_at": T3_RECORDED,
        }
    )
    before = execute_financial_revisions(body=before_body, provider=_Provider())
    before_packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T3_SOURCE,
        recorded_at=T3_RECORDED,
        dataset=dataset,
    )
    assert before.envelope["revisions"] == before_packet["revisions"] == []
    assert [row for row in before.envelope["revisions"] if row["metric_id"] == "revenue"] == []

    after_body = _make_request(
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": T3_SOURCE,
            "recorded_at": DELAYED_MAPPING_AFTER,
        }
    )
    after = execute_financial_revisions(body=after_body, provider=_Provider())
    after_packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T3_SOURCE,
        recorded_at=DELAYED_MAPPING_AFTER,
        dataset=dataset,
    )
    assert after.envelope["revisions"] == after_packet["revisions"]
    rows = [row for row in after.envelope["revisions"] if row["metric_id"] == "revenue"]
    assert len(rows) == 1
    assert rows[0]["root_value"] == "1050"
    assert rows[0]["prior_value"] == "1050"
    assert rows[0]["revised_value"] == "1060"


def test_future_metric_contract_does_not_change_historical_unsupported_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace
    from datetime import datetime, timezone

    from engine.fundamental_forensics import metric_registry as registry_module
    from engine.fundamental_forensics.metric_registry import ConceptAlias, KnownConcept

    historical_t = T3_RECORDED
    future_at = datetime(2026, 8, 6, 0, 0, tzinfo=timezone.utc)
    body = _make_request(
        metric_ids=["future_metric"],
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": T3_SOURCE,
            "recorded_at": historical_t,
        },
    )

    class _R1:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return fip1_packet_dataset(ROOT)

    with pytest.raises(FinancialQueryAdmissionError) as r1:
        execute_financial_revisions(body=body, provider=_R1())
    assert r1.value.status_code == 400
    assert r1.value.detail == "unsupported metric"

    base = fip1_packet_dataset(ROOT)
    revenue = base.registry.metric("revenue")
    mapping = revenue.mappings[0]
    future_concept = "FutureMetricNotYetGoverned"
    monkeypatch.setitem(
        registry_module.KNOWN_CONCEPT_ALLOWLIST,
        ("us-gaap", future_concept),
        KnownConcept(
            taxonomy="us-gaap",
            concept=future_concept,
            taxonomy_version_start=2009,
            taxonomy_version_end=2026,
            period_kind="duration",
            contract_units=("USD",),
        ),
    )
    future_contract = replace(
        revenue,
        metric_id="future_metric",
        label="FUTURE LEAK LABEL",
        rule=replace(
            revenue.rule,
            rule_id="metric.future_metric/v1",
            available_at=future_at,
        ),
        mappings=(
            replace(
                mapping,
                metric_id="future_metric",
                rule=replace(
                    mapping.rule,
                    rule_id="mapping.future_metric/v1",
                    available_at=future_at,
                ),
                taxonomy_concept_aliases=(
                    ConceptAlias("us-gaap", future_concept, 10, 2009, 2026),
                ),
            ),
        ),
        formula=None,
        declared_formula_dependencies=(),
    )
    r2_registry = replace(base.registry, contracts=base.registry.contracts + (future_contract,))
    r2_dataset = replace(base, registry=r2_registry)
    assert "future_metric" in r2_registry.metric_ids

    class _R2:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return r2_dataset

    with pytest.raises(FinancialQueryAdmissionError) as r2:
        execute_financial_revisions(body=body, provider=_R2())
    assert r2.value.status_code == 400
    assert r2.value.detail == "unsupported metric"


def test_source_misbound_dataset_is_unavailable() -> None:
    fip1 = fip1_packet_dataset(ROOT)
    misbound = FinancialPacketDataset(
        binding=CanonicalEntityBinding(
            entity_id="mmx.issuer.fip1",
            cik="0000111111",
            ticker="FIP1",
            source_entity_id="0000111111",
        ),
        entity=fip1.entity,
        ledger=fip1.ledger,
        filing_metadata=fip1.filing_metadata,
        registry=fip1.registry,
        context=fip1.context,
        input_digests=fip1.input_digests,
    )

    class _SourceMisbound:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return misbound

    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_revisions(body=_t3_latest(), provider=_SourceMisbound())


def test_same_source_wrong_canonical_entity_is_unavailable() -> None:
    fip1 = fip1_packet_dataset(ROOT)
    misbound = FinancialPacketDataset(
        binding=fip1.binding,
        entity=EntityInput(
            entity_id="mmx.issuer.other",
            cik="0000999999",
            ticker="FIP1",
            name=fip1.entity.name,
            identity_basis=fip1.entity.identity_basis,
            source_entity_id="0000999999",
        ),
        ledger=fip1.ledger,
        filing_metadata=fip1.filing_metadata,
        registry=fip1.registry,
        context=fip1.context,
        input_digests=fip1.input_digests,
    )

    class _WrongCanonical:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return misbound

    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_revisions(body=_t3_latest(), provider=_WrongCanonical())


def test_unavailable_provider_raises_unavailable_error() -> None:
    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_revisions(
            body=_t3_latest(),
            provider=UnavailableFinancialPacketProvider(),
        )


def test_provider_not_called_before_admission() -> None:
    calls: list[str] = []

    class _TrackingProvider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            calls.append(entity_id)
            raise FinancialQueryUnavailableError()

    with pytest.raises(FinancialQueryAdmissionError):
        execute_financial_revisions(body=b"x" * 65537, provider=_TrackingProvider())
    assert calls == []


def test_duplicate_period_label_is_400_before_provider_resolve() -> None:
    calls: list[str] = []
    factory_calls: list[str] = []

    class _TrackingProvider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            calls.append(entity_id)
            return fip1_packet_dataset(ROOT)

    def _factory():
        factory_calls.append("opened")
        return _TrackingProvider()

    body = _t3_latest(
        periods=[
            {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"},
            {"kind": "duration", "start": "2024-01-01", "end": "2024-12-31", "label": "FY2023"},
        ]
    )
    with pytest.raises(FinancialQueryAdmissionError) as exc_info:
        execute_financial_revisions(body=body, provider_factory=_factory)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "request contract violation"
    assert factory_calls == []
    assert calls == []


def test_unsupported_metric_raises_400() -> None:
    body = _t3_latest(metric_ids=["revenue", "not_a_real_metric_xyz"])
    with pytest.raises(FinancialQueryAdmissionError) as exc_info:
        execute_financial_revisions(body=body, provider=_fip1_provider())
    assert exc_info.value.status_code == 400
    assert "unsupported metric" in exc_info.value.detail


def test_wrong_request_schema_is_400() -> None:
    body = _make_request(schema=_QUERY_SCHEMA)
    with pytest.raises(FinancialQueryAdmissionError) as exc_info:
        execute_financial_revisions(body=body, provider=UnavailableFinancialPacketProvider())
    assert exc_info.value.status_code == 400


def test_two_calls_with_changed_wall_clock_produce_identical_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    provider = _fip1_provider()
    body = _t3_latest()
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.0)
    r1 = execute_financial_revisions(body=body, provider=provider)
    monkeypatch.setattr(time, "time", lambda: 1_800_000_000.0)
    r2 = execute_financial_revisions(body=body, provider=provider)
    assert r1.body == r2.body
    assert r1.sha256 == r2.sha256
    assert r1.envelope["packet_ref"]["packet_id"] == r2.envelope["packet_ref"]["packet_id"]
    assert r1.envelope["revisions"] == r2.envelope["revisions"]


def test_execute_does_not_append_to_the_ledger() -> None:
    provider = _fip1_provider()
    dataset = fip1_packet_dataset(ROOT)
    before = len(dataset.ledger.events)

    class _SpyProvider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            resolved = provider.resolve(entity_id)

            def _forbidden_write(*args, **kwargs):
                raise AssertionError("revisions must not append to the ledger")

            object.__setattr__(resolved.ledger, "append", _forbidden_write)
            object.__setattr__(resolved.ledger, "extend", _forbidden_write)
            return resolved

    execute_financial_revisions(body=_t3_latest(), provider=_SpyProvider())
    assert len(dataset.ledger.events) == before


def test_execute_does_not_open_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def _forbidden_socket(*args, **kwargs):
        raise AssertionError("revisions must not open a network socket")

    monkeypatch.setattr(socket, "socket", _forbidden_socket)
    execute_financial_revisions(body=_t3_latest(), provider=_fip1_provider())


def test_envelope_entity_is_canonical_mastermind_binding() -> None:
    result = execute_financial_revisions(body=_t3_latest(), provider=_fip1_provider())
    entity = result.envelope["entity"]
    assert entity["entity_id"] == "mmx.issuer.fip1"
    assert entity["cik"] == "0000999999"
    assert entity["ticker"] == "FIP1"
    assert entity["source_entity_id"] == "0000999999"
    assert result.envelope["schema"] == "fundamental_forensics.financial_revision_response/v1"
    assert result.envelope["authority"] == {"class": "context_only", "display_only": True}


def test_fip1_canonical_entity_does_not_rewrite_raw_identity() -> None:
    dataset = fip1_packet_dataset(ROOT)
    assert dataset.entity.entity_id == "mmx.issuer.fip1"
    assert dataset.entity.cik == "0000999999"
    assert dataset.entity.source_entity_id == "0000999999"
    assert dataset.entity.ticker == "FIP1"
    event = dataset.ledger.events[0]
    assert event.source.entity_id == "0000999999"
    assert event.context.entity_identifier == "0000999999"
    result = execute_financial_revisions(body=_t3_latest(), provider=_fip1_provider())
    packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T3_SOURCE,
        recorded_at=T3_RECORDED,
    )
    assert packet["entity"]["entity_id"] == "mmx.issuer.fip1"
    assert packet["entity"]["cik"] == "0000999999"
    assert result.envelope["packet_ref"]["packet_id"] == packet["packet_id"]


def test_arbitrary_fixture_does_not_claim_committed_fip1_digest() -> None:
    committed = fip1_packet_dataset(ROOT)
    committed_digest = sha256_file(
        ROOT / "tests" / "fixtures" / "fundamental_forensics" / "filing_package_raw_ledger_v1.json"
    )
    assert committed.input_digests.filing_package_fixture_sha256 == committed_digest
    fixture = build_multihop_revenue_fixture()
    arbitrary = packet_dataset_from_fixture(ROOT, fixture)
    assert arbitrary.input_digests == PacketEvidenceDigests()
    assert arbitrary.input_digests.filing_package_fixture_sha256 is None
    assert arbitrary.input_digests.filing_package_fixture_sha256 != committed_digest
    later = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=HOP_C_SOURCE,
        recorded_at=T3_RECORDED,
        dataset=arbitrary,
    )
    assert later["receipts"]["filing_package_fixture_sha256"] is None
    assert later["receipts"]["filing_package_fixture_sha256"] != committed_digest


# ---------------------------------------------------------------------------
# FIF-2A #5983 regression after shared admission
# ---------------------------------------------------------------------------


def _query_hash(*, selection: str, source: str, recorded: str, metric_ids: list, periods: list) -> str:
    class _P:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return fip1_fixture_dataset(ROOT)

    body = json.dumps(
        {
            "schema": _QUERY_SCHEMA,
            "entity_id": "mmx.issuer.fip1",
            "policy": {
                "selection": selection,
                "source_snapshot_at": source,
                "recorded_at": recorded,
            },
            "metric_ids": metric_ids,
            "periods": periods,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    result = execute_financial_query(
        body=body, provider=_P(), issuer_sic_resolver=_fip1_issuer_sic_resolver
    )
    return result.envelope["receipt"]["query_hash"]


def test_fif2a_query_hashes_unchanged_after_shared_admission() -> None:
    metrics = ["revenue", "gross_margin"]
    fy = [FY2023]
    assert (
        _query_hash(
            selection="as_reported",
            source=T1_SOURCE,
            recorded=T2_RECORDED,
            metric_ids=metrics,
            periods=fy,
        )
        == _HASH_AS_REPORTED_T1_T2
    )
    assert (
        _query_hash(
            selection="latest_known_as_of",
            source=T1_SOURCE,
            recorded=T2_RECORDED,
            metric_ids=metrics,
            periods=fy,
        )
        == _HASH_LATEST_KNOWN_T1_T2
    )
    assert (
        _query_hash(
            selection="latest_known_as_of",
            source=T3_SOURCE,
            recorded=T3_RECORDED,
            metric_ids=metrics,
            periods=fy,
        )
        == _HASH_LATEST_KNOWN_T3
    )
    assert (
        _query_hash(
            selection="latest_restated",
            source=T3_SOURCE,
            recorded=T3_RECORDED,
            metric_ids=metrics,
            periods=fy,
        )
        == _HASH_LATEST_RESTATED_T3
    )
    mixed = _query_hash(
        selection="latest_known_as_of",
        source=T3_SOURCE,
        recorded=T3_RECORDED,
        metric_ids=["revenue", "accounts_receivable_net"],
        periods=[FY2023, AR_INSTANT],
    )
    assert mixed == _HASH_MIXED_T3


# ---------------------------------------------------------------------------
# FIF D3: revision envelope delivery — absent for golden, exact for production
# ---------------------------------------------------------------------------

_FROZEN_FIP1_REVISIONS_SHA = "fbbf595719d45e021cb9b8c16dfe0f1c7c30695884d35981064bd7c584d73bef"


def test_revision_envelope_delivery_absent_for_golden_present_for_production() -> None:
    # Golden/FIP1: no delivery key, byte-identical to the pre-D3 response
    # (frozen baseline captured on the untouched tree at 5267c66846e).
    golden = execute_financial_revisions(
        body=_make_request(),
        provider=_fip1_provider(),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    assert "delivery" not in golden.envelope
    assert golden.sha256 == _FROZEN_FIP1_REVISIONS_SHA

    # Production: the exact five-key production object, validated by the one
    # shared delivery law.
    from datetime import datetime, timezone

    from engine.fundamental_forensics import production_datasets as PDS
    from engine.fundamental_forensics.financial_intelligence_packet import EntityInput
    from engine.fundamental_forensics.production_provider import (
        ProductionFinancialPacketProvider,
    )

    base = fip1_fixture_dataset(ROOT)
    material = PDS.ProductionDatasetMaterial(
        binding=base.binding,
        entity=EntityInput(
            entity_id=base.binding.entity_id,
            cik=base.binding.cik,
            ticker=base.binding.ticker,
            name="FIP1 Fixture",
            identity_basis="sec-cik",
            source_entity_id=base.binding.source_entity_id,
        ),
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        source_recorded_at_floor=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, material)
    provider = ProductionFinancialPacketProvider(store, repo_root=ROOT)
    production = execute_financial_revisions(
        body=_make_request(),
        provider=provider,
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    delivery = production.envelope["delivery"]
    assert delivery["kind"] == "production_issuer_dataset"
    assert delivery["attested"] is False
    assert delivery["production_issuer_service"] is True
    assert delivery["capture_basis"] == "reconstruction"
    assert PDS.GENERATION_ID_RE.fullmatch(delivery["dataset_generation_id"])
    assert production.sha256 != golden.sha256

    # An unlawful delivery on a packet dataset is unavailable, never served.
    from engine.fundamental_forensics.financial_intelligence_packet import (
        load_filing_package_fixture,
    )

    unlawful = packet_dataset_from_fixture(
        ROOT, load_filing_package_fixture(ROOT / "tests/fixtures/fundamental_forensics/filing_package_raw_ledger_v1.json")
    )
    object.__setattr__(
        unlawful,
        "delivery",
        {"kind": "production_issuer_dataset", "attested": True},
    )
    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_revisions(body=_make_request(), provider=_StaticPacketProvider(unlawful))


class _StaticPacketProvider:
    def __init__(self, dataset) -> None:
        self._dataset = dataset

    def resolve(self, entity_id: str) -> FinancialPacketDataset:
        return self._dataset


# ---------------------------------------------------------------------------
# A0-h1 (MINOR-4): metadata keying runs AFTER the typed admission gates and
# its ValueError is converted to a typed FinancialQueryUnavailableError
# ---------------------------------------------------------------------------

# A key that is neither a ledger occurrence id nor an accession: the
# occurrence-keyed helper fails closed on it (raw ValueError pre-fix). The
# revisions metric gate also loads the raw metadata into its engine, so this
# defect is visible to BOTH layers — right for the floor-ordering test.
_UNKNOWN_METADATA_KEY = "not-an-occurrence-id-or-accession"


def _unknown_metadata_key_dataset(**replacements) -> FinancialPacketDataset:
    base = fip1_packet_dataset(ROOT)
    filing_metadata = dict(base.filing_metadata)
    filing_metadata[_UNKNOWN_METADATA_KEY] = dict(
        next(iter(base.filing_metadata.values()))
    )
    return replace(base, filing_metadata=filing_metadata, **replacements)


def _gate_invisible_conflict_dataset(**replacements) -> FinancialPacketDataset:
    """A filing-metadata defect ONLY the occurrence-keyed helper refuses.

    The same occurrences are bound twice — once by their occurrence ids,
    once via the accession — with values that differ RAW (the accession
    entry carries an explicit ``schema`` key, the occurrence entries omit
    it) but coerce to the SAME FilingMetadata in the query engine (the
    engine defaults ``schema``; ``schema`` is allowed-but-optional in
    ``_strict_wire_mapping``). The admission gates' engine construction
    therefore accepts the dataset, while the helper's raw ``!=`` conflict
    check fails closed — the NIT-1 asymmetry, pinned here as the defect
    carrier. If R-4 ever canonicalizes the helper's comparison, switch
    this fixture to an unknown-key defect.
    """
    base = fip1_packet_dataset(ROOT)
    filing_metadata = dict(base.filing_metadata)
    _occurrence_id, meta = next(iter(base.filing_metadata.items()))
    filing_metadata[meta["accession"]] = {
        **meta,
        "schema": FILING_METADATA_SCHEMA,
    }
    return replace(base, filing_metadata=filing_metadata, **replacements)


def test_t6a_floor_refusal_wins_over_metadata_defect() -> None:
    """Unknown metadata key AND a dataset whose admission clock is after the
    request's recorded_at: the admission floor's typed refusal (the exception
    enforce_dataset_admission_floor raises in its own tests —
    FinancialQueryUnavailableError) wins, never the helper's raw
    ValueError and never the metric gate's engine refusal. ``__context__ is
    None`` proves the floor raised outside any except block: a converted
    ValueError/QueryValidationError would survive as the implicit context
    even under ``from None``."""
    dataset = _unknown_metadata_key_dataset(
        dataset_admitted_at=datetime(2026, 8, 6, tzinfo=timezone.utc)
    )
    # _t3_latest() records at T3_RECORDED (2026-08-05T12:00:02Z), strictly
    # before the clock above, so the floor excludes the generation.
    with pytest.raises(FinancialQueryUnavailableError) as exc_info:
        execute_financial_revisions(
            body=_t3_latest(), provider=_StaticPacketProvider(dataset)
        )
    assert exc_info.value.__context__ is None


def test_t6b_unsupported_metric_refusal_wins_over_metadata_defect() -> None:
    """A metadata defect AND an unsupported metric: the metric gate's typed
    400 ``unsupported metric`` wins — never a 503-shaped unavailability and
    never the helper's raw ValueError. The defect carrier is engine-invisible
    (see _gate_invisible_conflict_dataset) so the gate reaches its metric
    verdict before the helper ever runs."""
    dataset = _gate_invisible_conflict_dataset()
    body = _t3_latest(metric_ids=["revenue", "not_a_real_metric_xyz"])
    with pytest.raises(FinancialQueryAdmissionError) as exc_info:
        execute_financial_revisions(
            body=body, provider=_StaticPacketProvider(dataset)
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "unsupported metric"


def test_t6f_engine_visible_metadata_defect_alone_is_typed_unavailable() -> None:
    """A0-h1 review F1: an unknown metadata key is visible to the metric
    gate's engine construction, which refuses it with QueryValidationError.
    That is a DATASET defect, so revisions answers the typed
    FinancialQueryUnavailableError (503) — the same answer the packet path
    gives the same dataset (test_t6e) — never the request-side 400
    ``request contract violation``."""
    dataset = _unknown_metadata_key_dataset()
    with pytest.raises(FinancialQueryUnavailableError) as exc_info:
        execute_financial_revisions(
            body=_t3_latest(), provider=_StaticPacketProvider(dataset)
        )
    assert not isinstance(exc_info.value, (ValueError, FinancialQueryAdmissionError))


def test_t6g_query_matrix_contract_violation_still_400(monkeypatch) -> None:
    """The F1 split narrows ONLY engine construction: a QueryValidationError
    raised by ``query_matrix`` (which reads the request's metrics, periods
    and policy) on a clean dataset keeps its 400 ``request contract
    violation``."""
    import engine.fundamental_forensics.revision_service as revision_service_module

    def _refuse(self, **kwargs):
        raise QueryValidationError("probe: request-side violation")

    monkeypatch.setattr(
        revision_service_module.BitemporalMetricQueryEngine, "query_matrix", _refuse
    )
    with pytest.raises(FinancialQueryAdmissionError) as exc_info:
        execute_financial_revisions(
            body=_t3_latest(), provider=_StaticPacketProvider(fip1_packet_dataset(ROOT))
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "request contract violation"


def test_t6c_metadata_defect_alone_is_typed_unavailable() -> None:
    """A metadata defect the gates cannot see (engine-invisible conflict):
    the helper's ValueError is converted to the typed
    FinancialQueryUnavailableError inside the service, never escaping as a
    raw ValueError into the API catch-all."""
    dataset = _gate_invisible_conflict_dataset()
    with pytest.raises(FinancialQueryUnavailableError) as exc_info:
        execute_financial_revisions(
            body=_t3_latest(), provider=_StaticPacketProvider(dataset)
        )
    assert not isinstance(exc_info.value, ValueError)
