"""FIF D3: production providers over the immutable dataset store.

Three providers implementing the existing transport protocols
(``FinancialQueryProvider.resolve(entity_id)``,
``FinancialPacketProvider.resolve(entity_id)``,
``FinancialStatementProvider.resolve(entity_id, accession)``) on top of
:mod:`engine.fundamental_forensics.production_datasets`.

Request-path law (pinned by tests): the providers read only
``latest.json`` → generation manifest → role objects via strict bounded reads,
verify digests, and rebuild the datasets IN MEMORY. There is no SEC fetch, no
iXBRL parse/convert, no model call, and no wall clock anywhere on this path —
production datasets arrive pre-materialized because extraction is exactly
what D3 forbids at request time.

Selection law: in production mode these providers never fall back to the
golden corpus, and the golden providers never consult this store. An
available store with no admitted generation for the requested canonical
issuer is a 400 ``unknown entity``; a missing store, a damaged manifest, a
digest mismatch, or a pre-admission ``recorded_at`` is an indistinguishable
503 unavailability. Identity binds once, at issuer level via the Data OS
CIK, from the generation manifest (A14): the request path never picks among
share classes.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .production_datasets import (
    ProductionDatasetError,
    ProductionDatasetGeneration,
    load_latest_generation,
    load_query_dataset_payloads,
)
from .query_service import (
    CanonicalEntityBinding,
    FinancialQueryAdmissionError,
    FinancialQueryDataset,
    FinancialQueryUnavailableError,
)
from .revision_service import FinancialPacketDataset
from .statement_graph import GoldenFilingPackage
from .statement_service import bind_production_issuer_identity


@dataclass(frozen=True)
class ProductionFilingPackage(GoldenFilingPackage):
    """A generation-rebuilt statement package carrying its delivery object.

    ``GoldenFilingPackage`` proper (every committed golden fixture) carries
    none, which keeps the golden statement response byte-identical; a
    production package carries the exact production delivery object.
    """

    delivery: Mapping[str, Any] | None = None


class _ProductionProviderBase:
    """Shared generation loading: strict reads, digest verification, caching."""

    issuer_level_binding = False

    def __init__(self, store: Any) -> None:
        self._store = store
        self._lock = threading.Lock()
        self._generations: dict[tuple[str, str], ProductionDatasetGeneration] = {}

    def _load_generation(self, entity_id: str) -> ProductionDatasetGeneration | None:
        """Latest verified generation, or None when the issuer has none.

        Every damage class — absent store, unreadable pointer, truncated
        manifest, digest mismatch, missing role object — collapses into one
        typed unavailability. None (the 400 ``unknown entity`` case) is
        reserved for an available store that simply carries no generation for
        this issuer.
        """
        try:
            generation = load_latest_generation(self._store, entity_id)
        except FinancialQueryAdmissionError:
            raise
        except FinancialQueryUnavailableError:
            raise
        except ProductionDatasetError:
            raise FinancialQueryUnavailableError() from None
        except Exception:  # noqa: BLE001 - never leak a store detail
            raise FinancialQueryUnavailableError() from None
        return generation

    def _cached_generation(self, entity_id: str) -> ProductionDatasetGeneration | None:
        generation = self._load_generation(entity_id)
        if generation is None:
            return None
        key = (entity_id, generation.generation_id)
        with self._lock:
            cached = self._generations.get(key)
        if cached is not None:
            return cached
        with self._lock:
            self._generations[key] = generation
        return generation


class ProductionFinancialQueryProvider(_ProductionProviderBase):
    """Serves governed query over pre-materialized immutable generations."""

    def resolve(self, entity_id: str) -> FinancialQueryDataset:
        generation = self._cached_generation(entity_id)
        if generation is None:
            raise FinancialQueryAdmissionError(400, "unknown entity")
        try:
            payloads = load_query_dataset_payloads(generation)
            binding_document = payloads["binding_document"]
            binding = CanonicalEntityBinding(
                entity_id=binding_document["entity_id"],
                cik=binding_document["cik"],
                ticker=binding_document["ticker"],
                source_entity_id=binding_document["source_entity_id"],
            )
            if binding.entity_id != generation.binding.entity_id:
                raise FinancialQueryUnavailableError()
            dataset = FinancialQueryDataset(
                binding=binding,
                ledger=payloads["ledger"],
                filing_metadata=payloads["filing_metadata"],
                registry=payloads["registry"],
                delivery=generation.delivery(),
                lineage_evidence=payloads["lineage_evidence"],
                dataset_admitted_at=generation.admitted_at,
            )
        except FinancialQueryAdmissionError:
            raise
        except FinancialQueryUnavailableError:
            raise
        except Exception:  # noqa: BLE001 - any rebuild failure is unavailability
            raise FinancialQueryUnavailableError() from None
        return dataset


class ProductionFinancialPacketProvider(_ProductionProviderBase):
    """Serves revision/packet builds over pre-materialized generations."""

    def __init__(self, store: Any, *, repo_root: Path | None = None) -> None:
        super().__init__(store)
        self.repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
        self._packet_schema = None

    def _packet_context(self, generation: ProductionDatasetGeneration):
        from .financial_intelligence_packet import (  # noqa: PLC0415
            PacketBuildContext,
            load_packet_schema,
            PACKET_SCHEMA_PATH,
        )

        if self._packet_schema is None:
            self._packet_schema = load_packet_schema(PACKET_SCHEMA_PATH)
        return PacketBuildContext(
            packet_builder_digest=generation.manifest["packet_builder_digest"],
            packet_schema=self._packet_schema,
        )

    def resolve(self, entity_id: str) -> FinancialPacketDataset:
        generation = self._cached_generation(entity_id)
        if generation is None:
            raise FinancialQueryAdmissionError(400, "unknown entity")
        try:
            payloads = load_query_dataset_payloads(generation)
            binding = generation.binding
            context = self._packet_context(generation)
            dataset = FinancialPacketDataset(
                binding=binding,
                entity=payloads["entity"],
                ledger=payloads["ledger"],
                filing_metadata=payloads["filing_metadata"],
                registry=payloads["registry"],
                context=context,
                input_digests=payloads["input_digests"],
                delivery=generation.delivery(),
                dataset_admitted_at=generation.admitted_at,
            )
        except FinancialQueryAdmissionError:
            raise
        except FinancialQueryUnavailableError:
            raise
        except Exception:  # noqa: BLE001
            raise FinancialQueryUnavailableError() from None
        return dataset


class ProductionFinancialStatementProvider(_ProductionProviderBase):
    """Serves as-reported statement packages from immutable generations.

    Statement identity binds at the issuer level (A14): the CIK comes from
    the Data OS issuer axis via ``IssuerMaster.cik_of_issuer`` and must agree
    with the generation manifest; the single listing label was chosen at
    dataset admission and is read from the manifest. ``securities_of_issuer``
    is never called on this path, so a two-class issuer contributes exactly
    one dataset and can never be double-counted.
    """

    issuer_level_binding = True

    def bind_issuer(
        self,
        repo_root: Path | str,
        entity_id: str,
        *,
        issuer_master: Any | None = None,
        issuer_metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        from .statement_service import (  # noqa: PLC0415
            _load_issuer_metadata,
            _load_security_records,
        )
        from lib.dataos.identity import IssuerMaster  # noqa: PLC0415

        generation = self._cached_generation(entity_id)
        if generation is None:
            raise FinancialQueryAdmissionError(400, "unknown entity")
        if issuer_master is None:
            issuer_master = IssuerMaster.from_records(_load_security_records(Path(repo_root)))
        if issuer_metadata is None:
            issuer_metadata = _load_issuer_metadata(Path(repo_root), entity_id)
        manifest_issuer = generation.manifest.get("issuer") or {}
        return bind_production_issuer_identity(
            entity_id,
            issuer_master=issuer_master,
            issuer_metadata=issuer_metadata,
            security_id=manifest_issuer.get("security_id"),
            listing_key=manifest_issuer.get("listing_key"),
            expected_cik=manifest_issuer.get("cik"),
        )

    def resolve(self, entity_id: str, accession: str) -> GoldenFilingPackage:
        generation = self._cached_generation(entity_id)
        if generation is None:
            raise FinancialQueryAdmissionError(400, "unknown entity")
        try:
            if accession not in generation.statement_accessions():
                raise FinancialQueryAdmissionError(400, "unknown filing")
            manifest, members = generation.statement_package(accession)
        except FinancialQueryAdmissionError:
            raise
        except FinancialQueryUnavailableError:
            raise
        except Exception:  # noqa: BLE001
            raise FinancialQueryUnavailableError() from None
        return ProductionFilingPackage(
            manifest=manifest,
            members=members,
            delivery=generation.delivery(),
        )


__all__ = [
    "ProductionFinancialPacketProvider",
    "ProductionFinancialQueryProvider",
    "ProductionFinancialStatementProvider",
    "ProductionFilingPackage",
]
