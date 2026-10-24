"""FIF-2C: authenticated full packet read over the frozen FIP assembler."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics.financial_intelligence_packet import (
    PACKET_MAX_SERIALIZED_BYTES,
    EntityInput,
    PacketEvidenceDigests,
    PacketQueryRequest,
    assemble_financial_intelligence_packet,
    canonical_packet_bytes,
    load_packet_schema,
    packet_digest,
    sha256_file,
    validate_packet,
    validate_packet_semantics,
)
from engine.fundamental_forensics.packet_service import execute_financial_packet
from engine.fundamental_forensics.query import PeriodRequest, QueryPolicy
from engine.fundamental_forensics.query_service import (
    CanonicalEntityBinding,
    FinancialQueryAdmissionError,
    FinancialQueryDataset,
    FinancialQueryUnavailableError,
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
_PACKET_SCHEMA = "fundamental_forensics.financial_packet_request/v1"
_REVISION_SCHEMA = "fundamental_forensics.financial_revision_request/v1"
_QUERY_SCHEMA = "fundamental_forensics.financial_query_request/v1"
_GOLDEN_PACKET_ID = "fip_efe52d02d4a72a5a19f85a60"  # re-captured by FIF G0-r1p3 P2-E; fixture carried in e94ba62aa89

# FIP1 is a synthetic industrial issuer with no shipped coverage record; the
# hermetic production-path tests inject its SIC (R1-SIC/R2).
_FIP1_CIK = "0000999999"
_INDUSTRIAL_SIC = "3571"


def _fip1_issuer_sic_resolver(cik: str) -> str | None:
    return _INDUSTRIAL_SIC if cik == _FIP1_CIK else None

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

RICH_METRICS = ["revenue", "accounts_receivable_net", "gross_margin", "CustomerCount"]
RICH_PERIODS = [FY2023, AR_INSTANT]

_HASH_AS_REPORTED_T1_T2 = "58d438ec81d287f81e6981cf01ac6d16d57cf50689cc826cad39962742efa821"
_HASH_LATEST_KNOWN_T1_T2 = "f275a7e02aff6e1119f1275365549e1fa9aa2d3f45dbc3cd0f4ba5fdb76f1d37"
_HASH_LATEST_KNOWN_T3 = "2f8d30baf2d49aef0cc6936613eca1f9aa980e10ed56da135a75dd4238349915"
_HASH_LATEST_RESTATED_T3 = "531309e192ac923e466365b05380a197f67d6df01c1d5fd9062a0e93aaf20b9f"
_HASH_MIXED_T3 = "26a7ed7d95f861d3352c3a7e5fb6a0f52833ccf69947b10ca9da1f9662c44133"


def _make_request(
    *,
    schema: str = _PACKET_SCHEMA,
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


def _cell(packet: dict, metric_id: str, label: str) -> dict:
    matches = [
        cell
        for cell in packet["cells"]
        if cell["metric_id"] == metric_id and cell["period"]["label"] == label
    ]
    assert len(matches) == 1, (metric_id, label, len(matches))
    return matches[0]


def _t3_latest(**kwargs):
    policy = {
        "selection": "latest_known_as_of",
        "source_snapshot_at": T3_SOURCE,
        "recorded_at": T3_RECORDED,
    }
    policy.update(kwargs.pop("policy_update", {}))
    return _make_request(policy=policy, **kwargs)


def test_http_bytes_equal_direct_canonical_packet_bytes() -> None:
    provider = _fip1_provider()
    body = _t3_latest()
    result = execute_financial_packet(body=body, provider=provider)
    packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T3_SOURCE,
        recorded_at=T3_RECORDED,
    )
    direct_bytes = canonical_packet_bytes(packet)
    assert result.body == direct_bytes
    assert result.packet == packet
    assert result.packet["packet_id"] == packet["packet_id"]
    assert result.packet["content_sha256"] == packet["content_sha256"]
    assert (
        result.packet["governance"]["governance_bundle_id"]
        == packet["governance"]["governance_bundle_id"]
    )
    assert result.packet["content_sha256"] == packet_digest(result.packet)
    assert result.packet["packet_id"] == "fip_" + result.packet["content_sha256"][:24]
    assert result.response_sha256 == hashlib.sha256(result.body).hexdigest()


def test_committed_golden_packet_id_remains_a_regression_witness() -> None:
    golden = json.loads(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "fundamental_forensics"
            / "expected_financial_intelligence_packet_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert golden["packet_id"] == _GOLDEN_PACKET_ID
    result = execute_financial_packet(body=_t3_latest(), provider=_fip1_provider())
    assert result.packet["entity"]["entity_id"] == "mmx.issuer.fip1"
    assert result.packet["packet_id"] == "fip_" + result.packet["content_sha256"][:24]


def test_rich_packet_is_the_complete_research_artifact() -> None:
    body = _t3_latest(metric_ids=RICH_METRICS, periods=RICH_PERIODS)
    result = execute_financial_packet(
        body=body, provider=_fip1_provider(), issuer_sic_resolver=_fip1_issuer_sic_resolver
    )
    packet = result.packet
    schema = load_packet_schema(ROOT / "contracts" / "financial_intelligence_packet.schema.json")
    validate_packet(packet, schema)
    validate_packet_semantics(packet)
    assert packet["schema"] == "financial_intelligence_packet.v1"
    assert result.body == canonical_packet_bytes(packet)
    assert len(result.body) <= PACKET_MAX_SERIALIZED_BYTES
    assert len(result.body) > 0

    revenue = _cell(packet, "revenue", "FY2023")
    assert revenue["value"] == "1060"
    assert revenue["non_value_state"] is None

    ar = _cell(packet, "accounts_receivable_net", "2023-12-31")
    assert ar["value"] == "121"
    assert ar["non_value_state"] is None

    margin = _cell(packet, "gross_margin", "FY2023")
    assert margin["value"] is not None
    assert margin["formula_rule_id"]
    assert margin["dependency_cell_ids"]
    assert packet["evidence_cells"]

    unsupported = [
        cell
        for cell in packet["cells"]
        if cell["metric_id"] == "CustomerCount" and cell["non_value_state"] == "unsupported"
    ]
    assert unsupported
    assert all(cell["value"] is None for cell in unsupported)
    assert all(cell["coverage_state"] == "unmapped" for cell in unsupported)
    assert all(cell["quality_state"] == "unsupported" for cell in unsupported)

    assert packet["revisions"]
    assert packet["governance"]["governance_bundle_id"]
    assert packet["coverage"]
    assert "limitations" in packet
    assert packet["receipts"]
    assert packet["authority"] == {"class": "context_only", "display_only": True}


def test_customercount_is_packet_200_not_api_400() -> None:
    body = _t3_latest(metric_ids=["CustomerCount"])
    result = execute_financial_packet(body=body, provider=_fip1_provider())
    cells = [cell for cell in result.packet["cells"] if cell["metric_id"] == "CustomerCount"]
    assert cells
    assert all(cell["non_value_state"] == "unsupported" for cell in cells)
    assert all(cell["value"] is None for cell in cells)


def test_query_and_revisions_still_refuse_unsupported_metrics() -> None:
    class _QueryProvider:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return fip1_fixture_dataset(ROOT)

    query_body = _make_request(schema=_QUERY_SCHEMA, metric_ids=["CustomerCount"])
    with pytest.raises(FinancialQueryAdmissionError) as query_exc:
        execute_financial_query(body=query_body, provider=_QueryProvider())
    assert query_exc.value.status_code == 400
    assert query_exc.value.detail == "unsupported metric"

    revision_body = _make_request(schema=_REVISION_SCHEMA, metric_ids=["CustomerCount"])
    with pytest.raises(FinancialQueryAdmissionError) as rev_exc:
        execute_financial_revisions(body=revision_body, provider=_fip1_provider())
    assert rev_exc.value.status_code == 400
    assert rev_exc.value.detail == "unsupported metric"


def test_packet_revisions_equal_fif2b_envelope() -> None:
    metrics = ["revenue", "accounts_receivable_net", "gross_margin"]
    packet_body = _t3_latest(metric_ids=metrics, periods=RICH_PERIODS)
    packet_result = execute_financial_packet(
        body=packet_body,
        provider=_fip1_provider(),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    revision_body = _make_request(
        schema=_REVISION_SCHEMA,
        metric_ids=metrics,
        periods=RICH_PERIODS,
    )
    revision_result = execute_financial_revisions(
        body=revision_body,
        provider=_fip1_provider(),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    assert packet_result.packet["revisions"] == revision_result.envelope["revisions"]


def test_valued_packet_cells_agree_with_governed_query() -> None:
    metrics = ["revenue", "accounts_receivable_net", "gross_margin"]
    packet_result = execute_financial_packet(
        body=_t3_latest(metric_ids=metrics, periods=RICH_PERIODS),
        provider=_fip1_provider(),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )

    class _QueryProvider:
        def resolve(self, entity_id: str) -> FinancialQueryDataset:
            return fip1_fixture_dataset(ROOT)

    query_result = execute_financial_query(
        body=_make_request(schema=_QUERY_SCHEMA, metric_ids=metrics, periods=RICH_PERIODS),
        provider=_QueryProvider(),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    receipt = query_result.envelope["receipt"]
    nodes = {node["cell_id"]: node for node in receipt["nodes"]}
    for root_id in receipt["root_cell_ids"]:
        node = nodes[root_id]
        if node["state"] != "value":
            continue
        cell = _cell(packet_result.packet, node["metric_id"], node["period"]["label"])
        assert cell["value"] == node["value"]


def test_t2_does_not_leak_t3_revision_or_value() -> None:
    body = _make_request(
        policy={
            "selection": "latest_known_as_of",
            "source_snapshot_at": T2_SOURCE,
            "recorded_at": T2_RECORDED,
        }
    )
    result = execute_financial_packet(body=body, provider=_fip1_provider())
    packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T2_SOURCE,
        recorded_at=T2_RECORDED,
    )
    assert result.body == canonical_packet_bytes(packet)
    assert packet["revisions"] == []
    assert result.packet["revisions"] == []
    assert "1060" not in result.body.decode("utf-8")
    assert _cell(result.packet, "revenue", "FY2023")["value"] == "1050"


def test_t3_emits_1060_and_1050_to_1060_revision() -> None:
    result = execute_financial_packet(body=_t3_latest(), provider=_fip1_provider())
    assert _cell(result.packet, "revenue", "FY2023")["value"] == "1060"
    rows = [row for row in result.packet["revisions"] if row["metric_id"] == "revenue"]
    assert rows
    assert rows[0]["root_value"] == "1050"
    assert rows[0]["prior_value"] == "1050"
    assert rows[0]["revised_value"] == "1060"
    revision_result = execute_financial_revisions(
        body=_make_request(schema=_REVISION_SCHEMA),
        provider=_fip1_provider(),
    )
    assert result.packet["revisions"] == revision_result.envelope["revisions"]


def test_multihop_intermediate_shows_b_hides_c() -> None:
    fixture = build_multihop_revenue_fixture()
    dataset = packet_dataset_from_fixture(ROOT, fixture)

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return dataset

    mid = execute_financial_packet(
        body=_make_request(
            policy={
                "selection": "latest_known_as_of",
                "source_snapshot_at": HOP_C_SOURCE,
                "recorded_at": HOP_B_SYSTEM_READY,
            }
        ),
        provider=_Provider(),
    )
    mid_packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=HOP_C_SOURCE,
        recorded_at=HOP_B_SYSTEM_READY,
        dataset=dataset,
    )
    assert mid.body == canonical_packet_bytes(mid_packet)
    hops = {
        row["revision_hop"]: row
        for row in mid.packet["revisions"]
        if row["metric_id"] == "revenue"
    }
    assert 1 in hops
    assert 2 not in hops
    assert hops[1]["revised_value"] == "1060"
    assert b"1070" not in mid.body

    later = execute_financial_packet(
        body=_make_request(
            policy={
                "selection": "latest_known_as_of",
                "source_snapshot_at": HOP_C_SOURCE,
                "recorded_at": T3_RECORDED,
            }
        ),
        provider=_Provider(),
    )
    later_hops = {
        row["revision_hop"]: row
        for row in later.packet["revisions"]
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
    dataset = replace(
        packet_dataset_from_fixture(ROOT, fixture),
        registry=_registry_with_future_revenue_mapping(datetime(2026, 8, 6, tzinfo=timezone.utc)),
    )

    class _Provider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            return dataset

    before = execute_financial_packet(body=_t3_latest(), provider=_Provider())
    before_packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T3_SOURCE,
        recorded_at=T3_RECORDED,
        dataset=dataset,
    )
    assert before.body == canonical_packet_bytes(before_packet)
    assert before.packet["revisions"] == []

    after = execute_financial_packet(
        body=_make_request(
            policy={
                "selection": "latest_known_as_of",
                "source_snapshot_at": T3_SOURCE,
                "recorded_at": DELAYED_MAPPING_AFTER,
            }
        ),
        provider=_Provider(),
    )
    after_packet = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=T3_SOURCE,
        recorded_at=DELAYED_MAPPING_AFTER,
        dataset=dataset,
    )
    assert after.body == canonical_packet_bytes(after_packet)
    rows = [row for row in after.packet["revisions"] if row["metric_id"] == "revenue"]
    assert len(rows) == 1
    assert rows[0]["root_value"] == "1050"
    assert rows[0]["revised_value"] == "1060"


def test_canonical_entity_and_source_native_identity() -> None:
    dataset = fip1_packet_dataset(ROOT)
    assert dataset.entity.entity_id == "mmx.issuer.fip1"
    assert dataset.entity.cik == "0000999999"
    assert dataset.entity.source_entity_id == "0000999999"
    event = dataset.ledger.events[0]
    assert event.source.entity_id == "0000999999"
    assert event.context.entity_identifier == "0000999999"
    result = execute_financial_packet(body=_t3_latest(), provider=_fip1_provider())
    entity = result.packet["entity"]
    assert entity["entity_id"] == "mmx.issuer.fip1"
    assert entity["cik"] == "0000999999"
    assert entity["source_entity_id"] == "0000999999"


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
        execute_financial_packet(body=_t3_latest(), provider=_SourceMisbound())


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
        execute_financial_packet(body=_t3_latest(), provider=_WrongCanonical())


def test_unavailable_provider_raises_unavailable_error() -> None:
    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_packet(
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
        execute_financial_packet(body=b"x" * 65537, provider=_TrackingProvider())
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
        execute_financial_packet(body=body, provider_factory=_factory)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "request contract violation"
    assert factory_calls == []
    assert calls == []


def test_wrong_request_schema_is_400() -> None:
    body = _make_request(schema=_QUERY_SCHEMA)
    with pytest.raises(FinancialQueryAdmissionError) as exc_info:
        execute_financial_packet(body=body, provider=UnavailableFinancialPacketProvider())
    assert exc_info.value.status_code == 400


def test_duplicate_json_key_is_400_before_provider() -> None:
    calls: list[str] = []

    class _TrackingProvider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            calls.append(entity_id)
            raise FinancialQueryUnavailableError()

    body = b'{"schema":"fundamental_forensics.financial_packet_request/v1","schema":"x"}'
    with pytest.raises(FinancialQueryAdmissionError) as exc_info:
        execute_financial_packet(body=body, provider=_TrackingProvider())
    assert exc_info.value.status_code == 400
    assert calls == []


def test_two_calls_with_changed_wall_clock_produce_identical_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    provider = _fip1_provider()
    body = _t3_latest(metric_ids=RICH_METRICS, periods=RICH_PERIODS)
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.0)
    r1 = execute_financial_packet(
        body=body, provider=provider, issuer_sic_resolver=_fip1_issuer_sic_resolver
    )
    monkeypatch.setattr(time, "time", lambda: 1_800_000_000.0)
    r2 = execute_financial_packet(
        body=body, provider=provider, issuer_sic_resolver=_fip1_issuer_sic_resolver
    )
    assert r1.body == r2.body
    assert r1.response_sha256 == r2.response_sha256
    assert r1.packet["packet_id"] == r2.packet["packet_id"]
    assert r1.packet["content_sha256"] == r2.packet["content_sha256"]
    assert "built_at" not in r1.packet


def test_execute_does_not_append_to_the_ledger() -> None:
    provider = _fip1_provider()
    dataset = fip1_packet_dataset(ROOT)
    before = len(dataset.ledger.events)

    class _SpyProvider:
        def resolve(self, entity_id: str) -> FinancialPacketDataset:
            resolved = provider.resolve(entity_id)

            def _forbidden_write(*args, **kwargs):
                raise AssertionError("packet read must not append to the ledger")

            object.__setattr__(resolved.ledger, "append", _forbidden_write)
            object.__setattr__(resolved.ledger, "extend", _forbidden_write)
            return resolved

    execute_financial_packet(body=_t3_latest(), provider=_SpyProvider())
    assert len(dataset.ledger.events) == before


def test_execute_does_not_open_the_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def _forbidden_socket(*args, **kwargs):
        raise AssertionError("packet read must not open a network socket")

    monkeypatch.setattr(socket, "socket", _forbidden_socket)
    execute_financial_packet(body=_t3_latest(), provider=_fip1_provider())


def test_arbitrary_fixture_does_not_claim_committed_fip1_digest() -> None:
    committed = fip1_packet_dataset(ROOT)
    committed_digest = sha256_file(
        ROOT / "tests" / "fixtures" / "fundamental_forensics" / "filing_package_raw_ledger_v1.json"
    )
    assert committed.input_digests.filing_package_fixture_sha256 == committed_digest
    fixture = build_multihop_revenue_fixture()
    arbitrary = packet_dataset_from_fixture(ROOT, fixture)
    assert arbitrary.input_digests == PacketEvidenceDigests()
    later = _direct_packet(
        metric_ids=("revenue",),
        periods=(FY2023_PERIOD,),
        source_snapshot_at=HOP_C_SOURCE,
        recorded_at=T3_RECORDED,
        dataset=arbitrary,
    )
    assert later["receipts"]["filing_package_fixture_sha256"] is None
    assert later["receipts"]["filing_package_fixture_sha256"] != committed_digest


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


def test_fif2a_query_hashes_unchanged() -> None:
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


def test_fif2b_t2_t3_regression_remains_green() -> None:
    t2 = execute_financial_revisions(
        body=_make_request(
            schema=_REVISION_SCHEMA,
            policy={
                "selection": "latest_known_as_of",
                "source_snapshot_at": T2_SOURCE,
                "recorded_at": T2_RECORDED,
            },
        ),
        provider=_fip1_provider(),
    )
    assert t2.envelope["revisions"] == []
    t3 = execute_financial_revisions(
        body=_make_request(schema=_REVISION_SCHEMA),
        provider=_fip1_provider(),
    )
    rows = [row for row in t3.envelope["revisions"] if row["metric_id"] == "revenue"]
    assert rows[0]["root_value"] == "1050"
    assert rows[0]["revised_value"] == "1060"


# ---------------------------------------------------------------------------
# A0-h1 (MINOR-4): metadata keying runs AFTER the admission floor and its
# ValueError is converted to a typed FinancialQueryUnavailableError
# ---------------------------------------------------------------------------

# A key that is neither a ledger occurrence id nor an accession: the
# occurrence-keyed helper fails closed on it (raw ValueError pre-fix).
_UNKNOWN_METADATA_KEY = "not-an-occurrence-id-or-accession"


class _StaticPacketProvider:
    def __init__(self, dataset) -> None:
        self._dataset = dataset

    def resolve(self, entity_id: str) -> FinancialPacketDataset:
        return self._dataset


def _metadata_defect_dataset(**replacements) -> FinancialPacketDataset:
    base = fip1_packet_dataset(ROOT)
    filing_metadata = dict(base.filing_metadata)
    filing_metadata[_UNKNOWN_METADATA_KEY] = dict(
        next(iter(base.filing_metadata.values()))
    )
    return replace(base, filing_metadata=filing_metadata, **replacements)


def test_t6d_floor_refusal_wins_over_metadata_defect() -> None:
    """Unknown metadata key AND a dataset whose admission clock is after the
    request's recorded_at: the admission floor's typed refusal (the exception
    enforce_dataset_admission_floor raises in its own tests —
    FinancialQueryUnavailableError) wins, never the helper's raw
    ValueError. ``__context__ is None`` proves the floor raised outside any
    except block: a converted helper ValueError would survive as the
    implicit context even under ``from None``."""
    dataset = _metadata_defect_dataset(
        dataset_admitted_at=datetime(2026, 8, 6, tzinfo=timezone.utc)
    )
    # _t3_latest() records at T3_RECORDED (2026-08-05T12:00:02Z), strictly
    # before the clock above, so the floor excludes the generation.
    with pytest.raises(FinancialQueryUnavailableError) as exc_info:
        execute_financial_packet(
            body=_t3_latest(), provider=_StaticPacketProvider(dataset)
        )
    assert exc_info.value.__context__ is None


def test_t6e_metadata_defect_alone_is_typed_unavailable() -> None:
    """Unknown metadata key only: the service raises the typed
    FinancialQueryUnavailableError, never the helper's raw ValueError (which
    would reach the API catch-all instead of the typed service path)."""
    dataset = _metadata_defect_dataset()
    with pytest.raises(FinancialQueryUnavailableError) as exc_info:
        execute_financial_packet(
            body=_t3_latest(), provider=_StaticPacketProvider(dataset)
        )
    assert not isinstance(exc_info.value, ValueError)
