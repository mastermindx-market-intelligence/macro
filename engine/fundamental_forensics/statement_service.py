"""FIF-3A1/3A2: authenticated as-reported statement read over golden AAPL packages.

Admission is a dedicated statement contract. It reuses FIF-2 transport laws
(duplicate JSON keys, UTF-8, 64 KiB, binary-float rejection) without opening
the query metric/period kernel. Provider.resolve is never called before
admission succeeds. No request-time network. No implicit now.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .financial_intelligence_packet import load_core_registry
from .models import parse_utc
from .query_service import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    FinancialQueryAdmissionError,
    FinancialQueryUnavailableError,
    admit_request_bytes,
    canonical_financial_delivery,
)
from .raw_ledger import canonical_json
from .statement_graph import (
    GOLDEN_AAPL_FIXTURES,
    GoldenFilingPackage,
    StatementGraphError,
    load_golden_aapl_package,
    reconstruct_primary_statements,
)

_REQUEST_SCHEMA = "fundamental_forensics.financial_statement_request/v1"
_RESPONSE_SCHEMA = "fundamental_forensics.financial_statement_response/v1"
_REQUIRED_ROOT_FIELDS = frozenset({"schema", "entity_id", "accession"})
_OPTIONAL_ROOT_FIELDS = frozenset({"recorded_at"})
_GOLDEN_ENTITY_ID = "ISS:US-XNAS-AAPL"
_RELATED_EVENT_REF_KEYS = frozenset(
    {"plane", "event_id", "relation", "source_filing_distinction"}
)


@dataclass(frozen=True)
class AdmittedStatementRequest:
    entity_id: str
    accession: str
    recorded_at: datetime | None = None


@dataclass(frozen=True)
class FinancialStatementResult:
    body: bytes
    sha256: str
    envelope: dict[str, Any]


class FinancialStatementProvider:
    def resolve(self, entity_id: str, accession: str) -> GoldenFilingPackage:
        raise NotImplementedError


class UnavailableFinancialStatementProvider:
    def resolve(self, entity_id: str, accession: str) -> GoldenFilingPackage:
        raise FinancialQueryUnavailableError()


class GoldenAaplStatementProvider:
    """Serves only the committed AAPL golden filing set. No ticker. No latest."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]


    def resolve(self, entity_id: str, accession: str) -> GoldenFilingPackage:
        if entity_id != _GOLDEN_ENTITY_ID:
            raise FinancialQueryAdmissionError(400, "unknown entity")
        if accession not in GOLDEN_AAPL_FIXTURES:
            raise FinancialQueryAdmissionError(400, "unknown filing")
        try:
            return load_golden_aapl_package(self.repo_root, accession=accession)
        except StatementGraphError:
            raise FinancialQueryUnavailableError() from None


def admit_statement_request(body: bytes) -> AdmittedStatementRequest:
    parsed = admit_request_bytes(body)
    extra = set(parsed) - _REQUIRED_ROOT_FIELDS - _OPTIONAL_ROOT_FIELDS
    missing = _REQUIRED_ROOT_FIELDS - set(parsed)
    if extra or missing:
        raise FinancialQueryAdmissionError(400, "request contract violation")
    if parsed.get("schema") != _REQUEST_SCHEMA:
        raise FinancialQueryAdmissionError(400, "request contract violation")
    entity_id = parsed["entity_id"]
    accession = parsed["accession"]
    if isinstance(entity_id, float) or isinstance(accession, float):
        raise FinancialQueryAdmissionError(400, "request contract violation")
    if not isinstance(entity_id, str) or not entity_id:
        raise FinancialQueryAdmissionError(400, "request contract violation")
    if not isinstance(accession, str) or not accession:
        raise FinancialQueryAdmissionError(400, "request contract violation")
    # R-9761 follow-up: the optional rule-clock cutoff, admitted under the
    # same law as the financial query body's timestamp — an aware RFC 3339
    # instant, never a naive machine-local guess.
    recorded_at_raw = parsed.get("recorded_at")
    recorded_at = None
    if recorded_at_raw is not None:
        if isinstance(recorded_at_raw, float) or not isinstance(recorded_at_raw, str):
            raise FinancialQueryAdmissionError(400, "request contract violation")
        try:
            recorded_at = parse_utc(recorded_at_raw, field="recorded_at")
        except ValueError:
            raise FinancialQueryAdmissionError(400, "request contract violation") from None
        if recorded_at is None:
            raise FinancialQueryAdmissionError(400, "request contract violation")
    return AdmittedStatementRequest(
        entity_id=entity_id, accession=accession, recorded_at=recorded_at
    )


def _load_security_records(repo_root: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        raise FinancialQueryUnavailableError() from exc
    path = Path(repo_root) / "data" / "reference" / "security_master.parquet"
    if not path.is_file():
        raise FinancialQueryUnavailableError()
    return pd.read_parquet(path).to_dict("records")


def _load_issuer_metadata(repo_root: Path, entity_id: str) -> dict[str, str]:
    try:
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        raise FinancialQueryUnavailableError() from exc
    path = Path(repo_root) / "data" / "reference" / "issuer_master.parquet"
    if not path.is_file():
        raise FinancialQueryUnavailableError()
    issuers = pd.read_parquet(path)
    rows = issuers[issuers["issuer_id"] == entity_id]
    if len(rows) != 1:
        raise FinancialQueryAdmissionError(400, "unknown entity")
    row = rows.iloc[0]
    cik = str(row["cik"]).zfill(10)
    return {
        "cik": cik,
        "legal_name": str(row.get("legal_name") or ""),
    }


def bind_canonical_identity(
    entity_id: str,
    *,
    issuer_master: Any,
    issuer_metadata: dict[str, str],
) -> dict[str, str]:
    """Resolve issuer→security through IssuerMaster only.

    Raw issuer/security tables may supply metadata after that canonical
    membership is known. FIF must not independently pick among securities.
    IssuerMaster is imported here so API module load does not pull Data OS
    identity into unrelated job import closures.
    """
    from lib.dataos.identity import IssuerMaster

    if not isinstance(issuer_master, IssuerMaster):
        raise FinancialQueryUnavailableError()
    securities = issuer_master.securities_of_issuer(entity_id)
    if len(securities) != 1:
        raise FinancialQueryAdmissionError(400, "unknown entity")
    security_id = securities[0]
    row = next((item for item in issuer_master.rows if item.security_id == security_id), None)
    if row is None:
        raise FinancialQueryAdmissionError(400, "unknown entity")
    cik = str(issuer_metadata.get("cik") or "").zfill(10)
    if len(cik) != 10 or not cik.isdigit():
        raise FinancialQueryUnavailableError()
    return {
        "entity_id": entity_id,
        "cik": cik,
        "security_id": security_id,
        "listing_key": row.listing_key,
        "legal_name": str(issuer_metadata.get("legal_name") or ""),
    }


def _bind_data_os_issuer(
    repo_root: Path,
    entity_id: str,
    *,
    issuer_master: Any | None = None,
    issuer_metadata: dict[str, str] | None = None,
) -> dict[str, str]:
    from lib.dataos.identity import IssuerMaster

    if issuer_master is None:
        issuer_master = IssuerMaster.from_records(_load_security_records(repo_root))
    if issuer_metadata is None:
        issuer_metadata = _load_issuer_metadata(repo_root, entity_id)
    return bind_canonical_identity(
        entity_id,
        issuer_master=issuer_master,
        issuer_metadata=issuer_metadata,
    )


def bind_production_issuer_identity(
    entity_id: str,
    *,
    issuer_master: Any,
    issuer_metadata: dict[str, str],
    security_id: str | None,
    listing_key: str | None,
    expected_cik: str | None = None,
) -> dict[str, str]:
    """Issuer-level production binding (FIF D3 / A14): CIK once, no class pick.

    Differs from :func:`bind_canonical_identity` in exactly one way: identity
    is the Data OS *issuer* axis, so a two-class issuer (one ``ISS:`` id, one
    registrant CIK, two securities) binds ONCE through
    ``IssuerMaster.cik_of_issuer`` instead of being refused by the
    single-security membership rule — which stays untouched for the golden
    path. This function never calls ``securities_of_issuer``: the single
    kernel label was chosen at dataset admission and is recorded in the
    generation manifest; the request path must not pick among securities.
    Conflicting CIK observations are an ambiguous identity fact and are
    refused as unavailable, never guessed.
    """
    from lib.dataos.identity import IdentityError, IssuerMaster

    if not isinstance(issuer_master, IssuerMaster):
        raise FinancialQueryUnavailableError()
    try:
        cik = issuer_master.cik_of_issuer(entity_id)
    except IdentityError as exc:
        raise FinancialQueryUnavailableError() from exc
    if cik is None:
        raise FinancialQueryAdmissionError(400, "unknown entity")
    if expected_cik is not None and cik != expected_cik:
        # The generation's binding and the identity owner disagree: drift,
        # never a silent substitution of either side.
        raise FinancialQueryUnavailableError()
    if not isinstance(security_id, str) or not security_id:
        raise FinancialQueryUnavailableError()
    if not isinstance(listing_key, str) or not listing_key:
        raise FinancialQueryUnavailableError()
    return {
        "entity_id": entity_id,
        "cik": cik,
        "security_id": security_id,
        "listing_key": listing_key,
        "legal_name": str(issuer_metadata.get("legal_name") or ""),
    }


def _related_event_ref(manifest: dict[str, Any]) -> dict[str, Any] | None:
    raw = manifest.get("related_event_ref")
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != _RELATED_EVENT_REF_KEYS:
        raise FinancialQueryUnavailableError()
    distinction = raw.get("source_filing_distinction")
    if not isinstance(distinction, dict):
        raise FinancialQueryUnavailableError()
    eight_k = distinction.get("earnings_release_8k_accession")
    periodic = distinction.get("periodic_report_accession")
    if eight_k == periodic:
        raise FinancialQueryUnavailableError()
    return {
        "plane": raw["plane"],
        "event_id": raw["event_id"],
        "relation": raw["relation"],
        "source_filing_distinction": {
            "earnings_release_8k_accession": eight_k,
            "periodic_report_accession": periodic,
        },
    }


def _precomputed_registry_horizon(registry: Any) -> datetime:
    """The newest rule clock the registry carries.

    Precomputed trees are published under the full, unclocked registry, so
    they cannot honestly answer a clock older than any rule they already
    bake in — that view must be refused, never re-labelled as clocked.
    """
    clocks = [
        registry.available_at,
        registry.mapping_pack_available_at,
        registry.formula_pack_available_at,
    ]
    for contract in getattr(registry, "contracts", None) or ():
        clocks.append(contract.rule.available_at)
        for mapping in getattr(contract, "mappings", None) or ():
            clocks.append(mapping.rule.available_at)
        formula = getattr(contract, "formula", None)
        if formula is not None:
            clocks.append(formula.rule.available_at)
            policy = getattr(formula, "not_presented_policy", None)
            if policy is not None:
                clocks.append(policy.rule.available_at)
        definition = getattr(contract, "definition", None)
        if definition is not None:
            clocks.append(definition.rule.available_at)
    return max(clocks)


def _refuse_early_clock_on_precomputed_trees(
    repo_root: Path, recorded_at: datetime | None
) -> None:
    """A cutoff older than the registry horizon cannot reuse published trees."""
    if recorded_at is None:
        return
    try:
        horizon = _precomputed_registry_horizon(load_core_registry(repo_root))
    except FinancialQueryAdmissionError:
        raise
    except Exception:
        raise FinancialQueryUnavailableError() from None
    if recorded_at < horizon:
        raise FinancialQueryAdmissionError(
            400, "recorded_at precedes the precomputed trees' registry rules"
        )


def execute_financial_statements(
    *,
    body: bytes,
    repo_root: Path,
    provider: FinancialStatementProvider | None = None,
    provider_factory: Callable[[], FinancialStatementProvider] | None = None,
    issuer_master: Any | None = None,
    issuer_metadata: dict[str, str] | None = None,
) -> FinancialStatementResult:
    admitted = admit_statement_request(body)
    # Provider construction precedes binding so a production provider — whose
    # issuer-level binding needs the admitted generation — can supply it.
    # Construction opens no dataset; resolve still happens only after
    # admission, exactly as before.
    if provider is None:
        if provider_factory is None:
            raise FinancialQueryUnavailableError()
        provider = provider_factory()
    if getattr(provider, "issuer_level_binding", False):
        binding = provider.bind_issuer(
            repo_root,
            admitted.entity_id,
            issuer_master=issuer_master,
            issuer_metadata=issuer_metadata,
        )
    else:
        binding = _bind_data_os_issuer(
            repo_root,
            admitted.entity_id,
            issuer_master=issuer_master,
            issuer_metadata=issuer_metadata,
        )
    package = provider.resolve(admitted.entity_id, admitted.accession)
    if package.manifest.get("entity_id") != binding["entity_id"]:
        raise FinancialQueryUnavailableError()
    if package.manifest.get("cik") != binding["cik"]:
        raise FinancialQueryUnavailableError()
    if package.manifest.get("accession") != admitted.accession:
        raise FinancialQueryUnavailableError()
    # FIF P1 (F1): a production package serves the statement trees that were
    # precomputed at dataset publication; only the golden demonstration
    # path (no delivery object) reconstructs — i.e. parses — at request
    # time, byte-for-byte as before. A production package whose trees are
    # missing NEVER falls back to parsing the members.
    package_delivery = getattr(package, "delivery", None)
    precomputed_trees = getattr(package, "statement_trees", None)
    if precomputed_trees is not None:
        # R-9761 follow-up: trees published under the unclocked registry answer
        # only clocks at or after its newest rule; an earlier cutoff must be
        # refused, never served 1.1.0 bytes as if clocked.
        _refuse_early_clock_on_precomputed_trees(repo_root, admitted.recorded_at)
        reconstructed = precomputed_trees
    elif package_delivery is None:
        try:
            registry = load_core_registry(repo_root)
            if admitted.recorded_at is not None:
                # R-9761 follow-up: reconstruct through the registry view the
                # caller's clock makes visible, mirroring the query API cutoff.
                registry = registry.governance_bundle_at(admitted.recorded_at)
            reconstructed = reconstruct_primary_statements(package=package, registry=registry)
        except FinancialQueryAdmissionError:
            raise
        except StatementGraphError:
            raise FinancialQueryUnavailableError() from None
        except Exception:
            raise FinancialQueryUnavailableError() from None
    else:
        raise FinancialQueryUnavailableError()

    # FIF P1-b (I3): boundary pin, not a conversion. Every served cell value
    # must already be the parser's canonical decimal TEXT or an explicit null;
    # any other type (int, float, Decimal, ...) is a producer contract break
    # answered with this file's typed unavailability — no re-formatting, no
    # rounding, no scale math here. Scale and decimals already ride beside the
    # value as display hints, and both paths above (precomputed trees and the
    # golden reconstruction) sit behind this same rule.
    for statement in reconstructed["statements"]:
        for statement_row in statement["rows"]:
            for cell in statement_row["cells"]:
                value = cell["value"]
                if value is not None and not isinstance(value, str):
                    raise FinancialQueryUnavailableError()

    envelope = {
        "schema": _RESPONSE_SCHEMA,
        "entity": {
            "entity_id": binding["entity_id"],
            "cik": binding["cik"],
            "source_entity_id": binding["cik"],
            "security_id": binding["security_id"],
            "listing_key": binding["listing_key"],
            "legal_name": binding["legal_name"],
        },
        "filing": {
            "accession": package.manifest["accession"],
            "form": package.manifest["form"],
            "primary_document": package.manifest["primary_document"],
            "period_of_report": package.manifest["period_of_report"],
            "filing_date": package.manifest["filing_date"],
            "source_accepted_at": package.manifest["source_accepted_at"],
            "fixture_recorded_at": package.manifest.get("fixture_recorded_at"),
        },
        "package": {
            "archive_index_url": package.manifest["archive_index_url"],
            "index_sha256": package.manifest["index_sha256"],
            "member_count": package.manifest["member_count"],
            "retained_count": package.manifest["retained_count"],
            "members": [
                {
                    "name": item["name"],
                    "state": item["state"],
                    "role": item.get("role"),
                    "content_sha256": item.get("content_sha256"),
                    "byte_length": item.get("byte_length"),
                }
                for item in package.manifest["members"]
            ],
        },
        "authority": {
            "class": "context_only",
            "display_only": True,
        },
        "statements": reconstructed["statements"],
        "coverage": {
            "parsed_document_kind": reconstructed["parsed_document_kind"],
            "fact_count": reconstructed["fact_count"],
            "context_count": reconstructed["context_count"],
        },
    }
    # FIF D3: delivery is provider-supplied. A package that does not carry one
    # (every golden fixture package and every directly-constructed test
    # package) keeps today's exact golden object, so those responses stay
    # byte-identical; a production package supplies the exact production
    # object, fail-closed by the shared delivery law.
    if package_delivery is None:
        envelope["delivery"] = {
            "kind": "committed_golden_fixture",
            "attested": False,
            "production_issuer_service": False,
        }
    else:
        envelope["delivery"] = canonical_financial_delivery(package_delivery)
    related = _related_event_ref(package.manifest)
    if related is not None:
        envelope["related_event_ref"] = related
    body_out = canonical_json(envelope).encode("utf-8")
    if len(body_out) > MAX_RESPONSE_BYTES:
        raise FinancialQueryAdmissionError(413, "response exceeds bound")
    digest = hashlib.sha256(body_out).hexdigest()
    return FinancialStatementResult(body=body_out, sha256=digest, envelope=envelope)


__all__ = [
    "AdmittedStatementRequest",
    "FinancialStatementProvider",
    "FinancialStatementResult",
    "GoldenAaplStatementProvider",
    "UnavailableFinancialStatementProvider",
    "admit_statement_request",
    "bind_canonical_identity",
    "bind_production_issuer_identity",
    "execute_financial_statements",
    "MAX_REQUEST_BYTES",
]
