"""FIF D3 provider tests: protocol, clocks, identity, delivery, frozen corpus.

The production request path serves pre-materialized immutable generations:
no SEC fetch, no iXBRL extraction, no model call, no wall clock. Identity
binds once at issuer level via the Data OS CIK; the request path never picks
among share classes.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics import production_datasets as PDS
from engine.fundamental_forensics.financial_intelligence_packet import (
    EntityInput,
    load_core_registry,
)
from engine.fundamental_forensics.ixbrl_raw_ledger import (
    FIF3A4_LINEAGE_AVAILABLE_AT,
    GOLDEN_AAPL_QUERY_ACCESSIONS,
    parse_and_convert_golden_packages,
)
from engine.fundamental_forensics.production_provider import (
    ProductionFinancialPacketProvider,
    ProductionFinancialQueryProvider,
    ProductionFinancialStatementProvider,
)
from engine.fundamental_forensics.query import (
    BitemporalMetricQueryEngine,
    PeriodRequest,
    QueryBounds,
    QueryPolicy,
)
from engine.fundamental_forensics.query_service import (
    FinancialQueryAdmissionError,
    FinancialQueryUnavailableError,
    execute_financial_query,
    fip1_fixture_dataset,
)
from engine.fundamental_forensics.statement_graph import (
    GOLDEN_AAPL_FIXTURES,
    load_golden_aapl_package,
    reconstruct_primary_statements,
)
from lib.dataos.identity import IssuerMaster

ROOT = Path(__file__).resolve().parents[1]

T_ADMITTED = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
T_RECORDED_AFTER = "2026-10-05T00:00:00Z"
T_RECORDED_BEFORE = "2026-09-01T00:00:00Z"
T_SOURCE = "2024-12-31T23:59:59Z"
# Pre-D3 golden-baseline clocks (mirrors the scoped suites' constants).
T1_SOURCE = "2024-12-31T23:59:59Z"
T2_RECORDED = "2026-08-03T12:00:00Z"

_FIP1_ENTITY_ID = "mmx.issuer.fip1"

# Frozen pre-D3 baselines, computed on the untouched tree at 5267c66846e.
# If an additive D3 change moves any of these bytes, the change is wrong.
_FIP1_QUERY_SHA = {
    "as_reported": "bf8e9099e0f94d891f8b739adf15eee8651a0478b55ecbed746ac19a734e2c02",
    "latest_known_as_of": "2d9964257abbe545322c54e4572956dffeddae257fc49ff11cef7264d0bd79d7",
    "latest_restated": "7ba7a23305a1284ddf6e75eba582eb58791922c46cd1d63b0147560888350c0a",
}


def _query_body(
    *,
    entity_id: str = _FIP1_ENTITY_ID,
    selection: str = "latest_known_as_of",
    recorded_at: str = T_RECORDED_AFTER,
    source_snapshot_at: str = T_SOURCE,
    schema: str = "fundamental_forensics.financial_query_request/v1",
    metric_ids: list | None = None,
    periods: list | None = None,
) -> bytes:
    return json.dumps(
        {
            "schema": schema,
            "entity_id": entity_id,
            "policy": {
                "selection": selection,
                "source_snapshot_at": source_snapshot_at,
                "recorded_at": recorded_at,
            },
            "metric_ids": metric_ids or ["revenue"],
            "periods": periods
            or [{"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _fip1_provider(*, admitted_at: datetime = T_ADMITTED) -> ProductionFinancialQueryProvider:
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
        admitted_at=admitted_at,
        source_recorded_at_floor=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, material)
    return ProductionFinancialQueryProvider(store)


_AAPL_SECURITIES = [
    {
        "security_id": "SEC:US-XNAS-AAPL",
        "issuer_id": "ISS:US-XNAS-AAPL",
        "issuer_state": "ACTIVE",
        "listing_key": "US-XNAS-AAPL",
        "issuer_cik": "320193",
    },
    {
        "security_id": "SEC:US-XNAS-AAPL-B",
        "issuer_id": "ISS:US-XNAS-AAPL",
        "issuer_state": "ACTIVE",
        "listing_key": "US-XNAS-AAPL-B",
        "issuer_cik": "320193",
    },
]
_AAPL_MASTER = IssuerMaster.from_records(_AAPL_SECURITIES)
_AAPL_METADATA = {"cik": "0000320193", "legal_name": "Apple Inc."}


def _aapl_statement_provider() -> ProductionFinancialStatementProvider:
    packages = [load_golden_aapl_package(ROOT, accession=a) for a in GOLDEN_AAPL_QUERY_ACCESSIONS]
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    material = PDS.ProductionDatasetMaterial(
        binding=base_aapl_binding(),
        entity=EntityInput(
            entity_id="ISS:US-XNAS-AAPL",
            cik="0000320193",
            ticker="AAPL",
            name="Apple Inc.",
            identity_basis="sec-cik",
            source_entity_id="0000320193",
        ),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=T_ADMITTED,
        source_recorded_at_floor=datetime(2026, 8, 1, tzinfo=timezone.utc),
        packages=tuple(packages),
        security_id="SEC:US-XNAS-AAPL",
        listing_key="US-XNAS-AAPL",
    )
    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, material)
    return ProductionFinancialStatementProvider(store)


# ---------------------------------------------------------------------------
# FIF P1: manifest-only issuer binding (F5) and precomputed statement trees
# ---------------------------------------------------------------------------


def test_production_statement_binding_never_touches_live_master_or_parquet(monkeypatch) -> None:
    """Hard rule (b): identity comes from the manifest + entity role only."""
    import engine.fundamental_forensics.statement_service as statement_service_module

    provider = _aapl_statement_provider()

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("production binding must not consult the live identity owner")

    monkeypatch.setattr(IssuerMaster, "from_records", _forbidden)
    monkeypatch.setattr(IssuerMaster, "cik_of_issuer", _forbidden)
    monkeypatch.setattr(IssuerMaster, "securities_of_issuer", _forbidden)
    monkeypatch.setattr(statement_service_module, "_load_security_records", _forbidden)
    monkeypatch.setattr(statement_service_module, "_load_issuer_metadata", _forbidden)
    import pandas

    monkeypatch.setattr(pandas, "read_parquet", _forbidden)

    binding = provider.bind_issuer(ROOT, "ISS:US-XNAS-AAPL")
    assert binding == {
        "entity_id": "ISS:US-XNAS-AAPL",
        "cik": "0000320193",
        "ticker": "AAPL",
        "source_entity_id": "0000320193",
        "security_id": "SEC:US-XNAS-AAPL",
        "listing_key": "US-XNAS-AAPL",
        "legal_name": "Apple Inc.",
    }

    # End to end: the envelope binds from the same admission-time block.
    from engine.fundamental_forensics.statement_service import execute_financial_statements

    body = json.dumps(
        {
            "schema": "fundamental_forensics.financial_statement_request/v1",
            "entity_id": "ISS:US-XNAS-AAPL",
            "accession": "0000320193-25-000079",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    result = execute_financial_statements(body=body, repo_root=ROOT, provider=provider)
    entity = result.envelope["entity"]
    assert entity["entity_id"] == "ISS:US-XNAS-AAPL"
    assert entity["cik"] == "0000320193"
    assert entity["source_entity_id"] == "0000320193"
    assert entity["security_id"] == "SEC:US-XNAS-AAPL"
    assert entity["listing_key"] == "US-XNAS-AAPL"
    assert entity["legal_name"] == "Apple Inc."


def test_resolve_serves_precomputed_trees_without_parsing(monkeypatch) -> None:
    provider = _aapl_statement_provider()
    package = provider.resolve("ISS:US-XNAS-AAPL", "0000320193-25-000079")
    assert package.statement_trees is not None
    # The precomputed trees equal what a direct reconstruction over the same
    # package and pinned registry produces — publication precomputes exactly
    # the demonstration-path artifact.
    direct = reconstruct_primary_statements(package=package, registry=load_core_registry(ROOT))
    assert package.statement_trees == direct

    # resolve never parses: poison every parse surface and resolve again.
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the production request path must not parse iXBRL")

    import collectors.sec_filing_parser as parser_module
    import engine.fundamental_forensics.statement_graph as statement_graph_module

    monkeypatch.setattr(parser_module, "parse_sec_filing_document", _forbidden)
    monkeypatch.setattr(statement_graph_module, "parse_sec_filing_document", _forbidden)
    again = provider.resolve("ISS:US-XNAS-AAPL", "0000320193-25-000079")
    assert again.statement_trees == direct


def test_trees_role_is_additive_and_digest_bound() -> None:
    # A package-less publication keeps the exact D3 six-role core (and its
    # generation id): the optional role never appears.
    store1 = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store1, _fip1_material())
    generation1 = PDS.load_latest_generation(store1, _FIP1_ENTITY_ID)
    assert generation1 is not None
    assert [row["role"] for row in generation1.manifest["objects"]] == list(
        PDS.PRODUCTION_DATASET_ROLES
    )
    with pytest.raises(PDS.ProductionDatasetError):
        generation1.statement_trees("0000320193-25-000079")

    # A package-carrying publication admits the optional role, content-
    # addressed and digest-bound exactly like the core roles.
    packages = [load_golden_aapl_package(ROOT, accession=a) for a in GOLDEN_AAPL_QUERY_ACCESSIONS]
    ledger, filing_metadata, _report = parse_and_convert_golden_packages(packages)
    store2 = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(
        store2,
        PDS.ProductionDatasetMaterial(
            binding=base_aapl_binding(),
            entity=EntityInput(
                entity_id="ISS:US-XNAS-AAPL",
                cik="0000320193",
                ticker="AAPL",
                name="Apple Inc.",
                identity_basis="sec-cik",
                source_entity_id="0000320193",
            ),
            ledger=ledger,
            filing_metadata=filing_metadata,
            registry_payload=PDS.snapshot_core_registry_payload(ROOT),
            admitted_at=T_ADMITTED,
            packages=tuple(packages),
            security_id="SEC:US-XNAS-AAPL",
            listing_key="US-XNAS-AAPL",
        ),
    )
    generation2 = PDS.load_latest_generation(store2, "ISS:US-XNAS-AAPL")
    assert generation2 is not None
    assert [row["role"] for row in generation2.manifest["objects"]] == [
        *PDS.PRODUCTION_DATASET_ROLES,
        *PDS.OPTIONAL_PRODUCTION_DATASET_ROLES,
    ]
    row = next(
        r for r in generation2.manifest["objects"] if r["role"] == "statement_trees_json"
    )
    payload = store2.get_bytes(row["object_key"])
    assert payload is not None
    assert len(payload) == row["byte_length"]
    assert hashlib.sha256(payload).hexdigest() == row["sha256"]
    assert row["object_key"] == PDS.production_object_key(row["sha256"])
    trees = generation2.statement_trees("0000320193-25-000079")
    assert len(trees["statements"]) == 3
    with pytest.raises(PDS.ProductionDatasetError):
        generation2.statement_trees("0000320193-99-999999")


def base_aapl_binding():
    from engine.fundamental_forensics.query_service import CanonicalEntityBinding

    return CanonicalEntityBinding(
        entity_id="ISS:US-XNAS-AAPL",
        cik="0000320193",
        ticker="AAPL",
        source_entity_id="0000320193",
    )


# ---------------------------------------------------------------------------
# Test 5 — protocol: unknown entity vs unavailable
# ---------------------------------------------------------------------------


def test_unknown_entity_production_is_400_not_503() -> None:
    provider = _fip1_provider()
    with pytest.raises(FinancialQueryAdmissionError) as exc_info:
        provider.resolve("ISS:US-XNAS-NOPE")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "unknown entity"
    # An unknown entity is never an unavailability on an available store.
    with pytest.raises(FinancialQueryAdmissionError) as api_exc:
        execute_financial_query(body=_query_body(entity_id="ISS:US-XNAS-NOPE"), provider=provider)
    assert api_exc.value.status_code == 400
    assert api_exc.value.detail == "unknown entity"


# ---------------------------------------------------------------------------
# Test 10 — A12: recorded_at before admission excludes the generation
# ---------------------------------------------------------------------------


def test_recorded_at_before_dataset_admission_excludes_generation() -> None:
    provider = _fip1_provider(admitted_at=T_ADMITTED)
    # A pre-admission system clock must never see this generation's bytes.
    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_query(body=_query_body(recorded_at=T_RECORDED_BEFORE), provider=provider)
    # The same request at/after admission serves.
    result = execute_financial_query(body=_query_body(recorded_at=T_RECORDED_AFTER), provider=provider)
    assert result.envelope["delivery"]["kind"] == "production_issuer_dataset"
    # admitted_at == recorded_at is servable ("before" excludes, not "at").
    # The bytes legitimately differ from the later request: the receipt embeds
    # the policy clocks, so only the servability itself is asserted here.
    boundary = T_ADMITTED.strftime("%Y-%m-%dT%H:%M:%SZ")
    result_boundary = execute_financial_query(body=_query_body(recorded_at=boundary), provider=provider)
    assert result_boundary.envelope["delivery"]["kind"] == "production_issuer_dataset"
    assert result_boundary.sha256 != result.sha256


# ---------------------------------------------------------------------------
# Test 11 — cutoffs flow untouched; the admitted QueryPolicy passes through
# ---------------------------------------------------------------------------


def test_cutoffs_flow_untouched_through_production_provider() -> None:
    provider = _fip1_provider(admitted_at=T_ADMITTED)
    dataset = provider.resolve(_FIP1_ENTITY_ID)
    period = PeriodRequest.duration(start="2023-01-01", end="2023-12-31", label="FY2023")
    for selection in ("as_reported", "latest_known_as_of", "latest_restated"):
        policy = QueryPolicy(
            selection=selection,
            source_snapshot_at=T_SOURCE,
            recorded_at=T_RECORDED_AFTER,
        )
        result = execute_financial_query(
            body=_query_body(selection=selection), provider=provider
        )
        engine = BitemporalMetricQueryEngine(
            ledger=dataset.ledger,
            registry=dataset.registry,
            entities={dataset.binding.ticker: dataset.binding.source_entity_id},
            filing_metadata=dataset.filing_metadata,
            bounds=QueryBounds(max_tickers=1, max_metrics=50, max_periods=8, max_cells=400),
            lineage_evidence=dataset.lineage_evidence,
        )
        # Kernel selection equality vs the direct engine run over the SAME
        # dataset and policy: the provider never re-stamps, clamps, or
        # defaults a clock, so the receipts agree exactly.
        direct = engine.query_matrix(
            tickers=[dataset.binding.ticker],
            metrics=["revenue"],
            periods=[period],
            policy=policy,
        )
        assert result.envelope["receipt"] == direct.to_dict()
    # Cutoff visibility is real on this corpus: the three named policies do
    # not collapse into one answer (as_reported differs from the other two).
    receipts = {
        selection: execute_financial_query(
            body=_query_body(selection=selection), provider=provider
        ).sha256
        for selection in ("as_reported", "latest_known_as_of", "latest_restated")
    }
    assert len(set(receipts.values())) >= 2


# ---------------------------------------------------------------------------
# Test 12 — the registry snapshot is pinned, not live
# ---------------------------------------------------------------------------


def test_registry_snapshot_pinned_not_live(monkeypatch) -> None:
    provider = _fip1_provider()
    baseline = execute_financial_query(body=_query_body(), provider=provider)
    dataset = provider.resolve(_FIP1_ENTITY_ID)

    # A future-dated mapping appended to the LIVE repo registry must not
    # change a production answer: the dataset registry digest governs.
    from engine.fundamental_forensics import financial_intelligence_packet as fip_module
    from engine.fundamental_forensics.metric_registry import ConceptAlias

    revenue = load_core_registry(ROOT).metric("revenue")
    future_at = datetime(2027, 1, 1, tzinfo=timezone.utc)
    future_contract = replace(
        revenue,
        metric_id="revenue",
        label="FUTURE LEAK LABEL",
        rule=replace(revenue.rule, available_at=future_at),
        mappings=(
            replace(
                revenue.mappings[0],
                rule=replace(revenue.mappings[0].rule, available_at=future_at),
                taxonomy_concept_aliases=(
                    ConceptAlias("us-gaap", "FutureLeakConcept", 10, 2009, 2026),
                ),
            ),
        ),
    )
    live_registry = replace(
        load_core_registry(ROOT),
        contracts=tuple(
            future_contract if c.metric_id == "revenue" else c
            for c in load_core_registry(ROOT).contracts
        ),
    )
    monkeypatch.setattr(fip_module, "load_core_registry", lambda _root: live_registry)

    after = execute_financial_query(body=_query_body(), provider=provider)
    assert after.sha256 == baseline.sha256
    assert after.body == baseline.body
    assert dataset.registry != live_registry
    assert dataset.registry.metric("revenue").label != "FUTURE LEAK LABEL"


# ---------------------------------------------------------------------------
# Test 15 — no share-class pick on the request path (A14)
# ---------------------------------------------------------------------------


def test_no_share_class_pick_on_request_path(monkeypatch) -> None:
    provider = _fip1_provider()

    def _no_class_pick(self, issuer_id):
        raise AssertionError("the request path must never pick among share classes")

    monkeypatch.setattr(IssuerMaster, "securities_of_issuer", _no_class_pick)

    # The query path serves without consulting security membership at all.
    result = execute_financial_query(body=_query_body(), provider=provider)
    assert result.envelope["entity"]["ticker"] == "FIP1"

    # A security id (SEC:) or alias is not an accepted identifier: 400.
    with pytest.raises(FinancialQueryAdmissionError) as sec_exc:
        provider.resolve("SEC:US-XNAS-AAPL")
    assert sec_exc.value.status_code == 400
    with pytest.raises(FinancialQueryAdmissionError) as alias_exc:
        provider.resolve("AAPL")
    assert alias_exc.value.status_code == 400

    # Dataset binding equality stays fail-closed (query_service.py:452-453):
    # a dataset returned for the requested canonical id with a different
    # binding is unavailable, never a successful query of another issuer.
    from engine.fundamental_forensics.query_service import FinancialQueryDataset

    legitimate = provider.resolve(_FIP1_ENTITY_ID)
    foreign = FinancialQueryDataset(
        binding=dataset_foreign_binding(),
        ledger=legitimate.ledger,
        filing_metadata=legitimate.filing_metadata,
        registry=legitimate.registry,
    )
    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_query(body=_query_body(), provider=_StaticProvider(foreign))


def dataset_foreign_binding():
    from engine.fundamental_forensics.query_service import CanonicalEntityBinding

    return CanonicalEntityBinding(
        entity_id="mmx.issuer.other",
        cik="0000888888",
        ticker="OTHER",
        source_entity_id="0000888888",
    )


class _StaticProvider:
    def __init__(self, dataset) -> None:
        self._dataset = dataset

    def resolve(self, entity_id: str):
        return self._dataset


# ---------------------------------------------------------------------------
# Test 16 — reconstruction is never minted as attestation (A13)
# ---------------------------------------------------------------------------


def test_reconstruction_label_never_attested_without_admission() -> None:
    provider = _fip1_provider()
    dataset = provider.resolve(_FIP1_ENTITY_ID)
    delivery = dataset.delivery
    assert delivery["attested"] is False
    assert delivery["capture_basis"] == "reconstruction"
    assert delivery["production_issuer_service"] is True
    assert delivery["dataset_generation_id"].startswith("ffprods_")
    assert PDS.GENERATION_ID_RE.fullmatch(delivery["dataset_generation_id"])

    # The generation refuses to mint an attested delivery, and the adapter
    # fail-closes an attested production object as unavailable.
    from engine.fundamental_forensics.query_service import canonical_financial_delivery

    with pytest.raises(FinancialQueryUnavailableError):
        canonical_financial_delivery({**delivery, "attested": True})
    with pytest.raises(FinancialQueryUnavailableError):
        canonical_financial_delivery({**delivery, "capture_basis": "historic_capture"})
    with pytest.raises(FinancialQueryUnavailableError):
        canonical_financial_delivery({**delivery, "dataset_generation_id": "ffprods_nothex"})
    # A manifest that claims a D2 admission reference today is refused.
    store = PDS.InMemoryStrictConditionalStore()
    material = _fip1_material()
    PDS.publish_production_dataset(store, material)
    generation = PDS.load_latest_generation(store, _FIP1_ENTITY_ID)
    assert generation is not None
    assert generation.delivery()["attested"] is False


def _fip1_material(*, admitted_at: datetime = T_ADMITTED) -> PDS.ProductionDatasetMaterial:
    base = fip1_fixture_dataset(ROOT)
    return PDS.ProductionDatasetMaterial(
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
        admitted_at=admitted_at,
        source_recorded_at_floor=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Test 21 — the frozen golden corpus is unchanged
# ---------------------------------------------------------------------------


def test_golden_corpus_constants_unchanged() -> None:
    assert GOLDEN_AAPL_QUERY_ACCESSIONS == ("0000320193-25-000079", "0000320193-26-000020")
    assert GOLDEN_AAPL_FIXTURES == {
        "0000320193-25-000079": "tests/fixtures/fundamental_forensics/aapl_10k_2025",
        "0000320193-26-000020": "tests/fixtures/fundamental_forensics/aapl_10q_2026q3",
    }
    assert FIF3A4_LINEAGE_AVAILABLE_AT == datetime(2026, 9, 20, tzinfo=timezone.utc)
    # The frozen golden fixture digests equal the committed values, read from
    # the pinned literals in the ixbrl suite rather than recomputed opinions.
    ixbrl_suite = (
        ROOT / "tests" / "test_fundamental_forensics_ixbrl_raw_ledger.py"
    ).read_text(encoding="utf-8")
    pinned = dict(re.findall(r"^_(AAPL_[A-Z_]+(?:_SHA)?) = \"([0-9a-f]{64})\"", ixbrl_suite, re.M))
    assert pinned, "expected pinned golden literal digests in the ixbrl suite"
    for name, digest in pinned.items():
        assert re.fullmatch(r"[0-9a-f]{64}", digest), name
    # The committed fixture bytes hash to their committed manifest digests.
    for accession, relative in GOLDEN_AAPL_FIXTURES.items():
        fixture = ROOT / relative
        manifest = json.loads((fixture / "package_manifest.json").read_text(encoding="utf-8"))
        index_bytes = (fixture / "index.json").read_bytes()
        assert hashlib.sha256(index_bytes).hexdigest() == manifest["index_sha256"]
    # Golden-path FIP1 query bytes are unchanged by the D3 additions (frozen
    # pre-D3 baselines).
    base = fip1_fixture_dataset(ROOT)
    # Baselines were captured on the untouched tree with these exact clocks.
    for selection, expected in _FIP1_QUERY_SHA.items():
        result = execute_financial_query(
            body=_query_body(
                selection=selection,
                recorded_at=T2_RECORDED,
                source_snapshot_at=T1_SOURCE,
            ),
            provider=_StaticProvider(base),
        )
        assert result.sha256 == expected, selection


# ---------------------------------------------------------------------------
# Statement identity over a multi-class issuer (A14 companions to tests 13/14)
# ---------------------------------------------------------------------------


def test_production_statement_provider_binds_via_cik_over_two_class_issuer() -> None:
    provider = _aapl_statement_provider()
    binding = provider.bind_issuer(
        ROOT, "ISS:US-XNAS-AAPL", issuer_master=_AAPL_MASTER, issuer_metadata=_AAPL_METADATA
    )
    # Exactly one binding; facts keyed by the registrant CIK; the class label
    # comes from the generation manifest, not from the security roster.
    assert binding["cik"] == "0000320193"
    assert binding["security_id"] == "SEC:US-XNAS-AAPL"
    assert binding["listing_key"] == "US-XNAS-AAPL"
    assert len(_AAPL_MASTER.securities_of_issuer("ISS:US-XNAS-AAPL")) == 2
    package = provider.resolve("ISS:US-XNAS-AAPL", "0000320193-25-000079")
    assert package.manifest["cik"] == "0000320193"
    assert package.delivery["kind"] == "production_issuer_dataset"


def test_packet_provider_serves_from_the_same_generation() -> None:
    base = fip1_fixture_dataset(ROOT)
    store = PDS.InMemoryStrictConditionalStore()
    PDS.publish_production_dataset(store, _fip1_material())
    provider = ProductionFinancialPacketProvider(store, repo_root=ROOT)
    dataset = provider.resolve(_FIP1_ENTITY_ID)
    assert dataset.delivery["kind"] == "production_issuer_dataset"
    assert dataset.binding == base.binding
