"""Data OS identity consumer for the W1-A request edge.

No identifiers are minted here.  Every security is looked up through the current
``store`` alias space and the committed security master.  Current alias lookup is
only an input convenience; it never becomes historical symbol evidence.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from lib.dataos.identity import (
    IdentityError,
    IssuerMaster,
    VendorAliasTable,
    XASE,
    XNAS,
    XNYS,
    AliasRow,
    _CLOCKED_ALIAS_VENDORS,
    _aware_utc,
    option_underlying_kind,
    parse_id,
    parse_listing_key,
)
from engine.entry_radar.replay.identity_observation_snapshot import read_reference_generation

from .contracts import CanonicalEntity, EntityRequest


REPO_ROOT = Path(__file__).resolve().parents[2]
SECURITY_MASTER = Path("data/reference/security_master.parquet")
VENDOR_ALIASES = Path("data/reference/vendor_aliases.parquet")
INDUSTRY_RANKS = Path("data/stage_analysis/industry_ranks.json")
CURRENT_EDGE_VENDOR = "store"
US_EQUITY_MICS = frozenset({XASE, XNAS, XNYS})


class IdentityResolutionError(ValueError):
    """Canonical identity could not be proved from current owner artifacts."""


@dataclass(frozen=True)
class IdentityArtifactRead:
    """Exact bytes and an externally retained read observation, never a grant.

    The assigning input reader must bind the digest and actual completion clock.
    These caller-supplied values prove neither provenance nor authentication here.
    No path, mutable-head lookup, new store or implicit current time is used.
    """

    body: bytes
    sha256: str
    read_at: datetime | str


@dataclass(frozen=True)
class OptionUnderlyingIdentity:
    """Current-record identity in captured inputs, not historical issuer lineage.

    This value grants no Options/IW2 admission, entitlement or Save permission.
    Index records require a separate existing canonical reader; no coercion to SEC.
    """

    binding: AliasRow
    listing_key: str
    master_sha256: str
    aliases_sha256: str
    available_at: datetime


_IDENTITY_MAX_BYTES = 16 * 1024 * 1024
_IDENTITY_MAX_ROWS = 200_000


def _identity_evidence_clock(value: object) -> datetime:
    # Preserve nanoseconds through the existing conservative ceiling. Storage
    # timestamp timezone interpretation occurs only after schema validation below.
    if isinstance(value, datetime):
        value = value.isoformat()
    return _aware_utc(value, "known_at")


def _identity_read(read: IdentityArtifactRead, cutoff: datetime) -> datetime:
    if not isinstance(read, IdentityArtifactRead):
        raise IdentityResolutionError("captured identity artifact read required")
    if type(read.body) is not bytes or not 0 < len(read.body) <= _IDENTITY_MAX_BYTES:
        raise IdentityResolutionError("identity artifact bytes missing or exceed bound")
    if (type(read.sha256) is not str or len(read.sha256) != 64
            or hashlib.sha256(read.body).hexdigest() != read.sha256):
        raise IdentityResolutionError("identity artifact digest mismatch")
    observed = _identity_evidence_clock(read.read_at)
    if observed > cutoff:
        raise IdentityResolutionError("identity artifact read is after decision cutoff")
    return observed


def _identity_parquet(read: IdentityArtifactRead, required: frozenset[str],
                      clocks: frozenset[str], optional: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
    import pyarrow as pa
    import pyarrow.parquet as pq

    try:
        source = pq.ParquetFile(io.BytesIO(read.body))
        schema = source.schema_arrow
        if len(schema.names) != len(set(schema.names)) or not required <= set(schema.names):
            raise IdentityResolutionError("identity artifact columns missing or duplicated")
        if source.metadata.num_rows > _IDENTITY_MAX_ROWS:
            raise IdentityResolutionError("identity artifact exceeds row bound")
        selected = required | (optional & set(schema.names))
        for name in selected:
            typ = schema.field(name).type
            if name in clocks:
                # The existing producer explicitly writes naive UTC datetime64[ns]
                # under the registry's timezone: UTC. String clocks do not get
                # this storage interpretation, nor do arbitrary timezone types.
                valid = pa.types.is_timestamp(typ) and typ.tz in (None, "UTC")
            elif name in ("valid_from", "valid_to"):
                valid = pa.types.is_date(typ) or pa.types.is_null(typ)
            else:
                valid = pa.types.is_string(typ) or pa.types.is_large_string(typ) or pa.types.is_null(typ)
            if not valid:
                raise IdentityResolutionError(f"identity artifact invalid column type: {name}")
        rows = source.read(columns=sorted(selected), use_threads=False).to_pylist()
        for row in rows:
            for name in clocks:
                value = row[name]
                if value is not None and value.tzinfo is None:
                    row[name] = value.replace(tzinfo=timezone.utc)
        return rows
    except IdentityResolutionError:
        raise
    except Exception as exc:
        raise IdentityResolutionError("identity artifact is not readable Parquet") from exc


def _captured_option_security_target(security_id, on, *, decision_at, security_master):
    """Validate an existing canonical target; resolves no vendor/root or alias."""
    cutoff = _aware_utc(decision_at, "decision_at")
    master_at = _identity_read(security_master, cutoff)
    fields = frozenset({"security_id", "listing_key", "country", "mic", "inception_code",
                        "effective_at", "ingested_at", "security_state", "superseded_by"})
    records = _identity_parquet(security_master, fields,
                                frozenset({"effective_at", "ingested_at"}))
    ids = [r["security_id"] for r in records]
    if any(not isinstance(s, str) or option_underlying_kind(s) != "security" for s in ids):
        raise IdentityResolutionError("master contains noncanonical security ids")
    if len(ids) != len(set(ids)):
        raise IdentityResolutionError("master contains duplicate security ids")
    master = IssuerMaster.from_records(records)
    by_id = dict(zip(ids, records, strict=True))
    state = _security_state(security_id, master, by_id)
    row = by_id[security_id]
    if state != "active" or row["security_state"] is not None or row["superseded_by"] is not None:
        raise IdentityResolutionError("option underlying is retired or superseded")
    listing = parse_listing_key(row["listing_key"])
    if (listing.render() != row["listing_key"] or "SEC:" + listing.render() != security_id
            or master.listing_key_of_security(security_id) != listing.render()
            or (row["country"], row["mic"], row["inception_code"]) !=
               (listing.country, listing.mic, listing.code)):
        raise IdentityResolutionError("canonical security listing fields conflict")
    effective = _identity_evidence_clock(row["effective_at"])
    ingested = _identity_evidence_clock(row["ingested_at"])
    if not effective <= ingested <= master_at or effective.date() > on:
        raise IdentityResolutionError("canonical security evidence clocks conflict")
    return listing.render(), master_at


def resolve_option_underlying_security(
    vendor: str, root: str, on: date, *, decision_at: datetime | str,
    aliases: IdentityArtifactRead, security_master: IdentityArtifactRead,
    root_evidence: IdentityArtifactRead,
) -> OptionUnderlyingIdentity | None:
    """Join an explicit root relation to one active canonical SEC record.

    Uses the existing VendorAliasTable and IssuerMaster readers on the same
    byte-bound input bodies. Their observation clocks must precede the decision.
    Row ingested_at alone cannot prove availability of later amended bytes.
    Root evidence semantics and capture authenticity remain the source intake's
    responsibility; this is an offline integrity/consistency composition only.
    """
    try:
        cutoff = _aware_utc(decision_at, "decision_at")
        aliases_at = _identity_read(aliases, cutoff)
        master_at = _identity_read(security_master, cutoff)
        source_at = _identity_read(root_evidence, cutoff)
        alias_fields = frozenset({"alias_kind", "vendor", "vendor_symbol", "security_id",
                                 "valid_from", "valid_to", "known_at", "evidence_sha256",
                                 "binding_sha256", "ingested_at"})
        alias_rows = _identity_parquet(aliases, alias_fields, frozenset({"ingested_at"}),
                                       frozenset({"attempt_id", "alias_family_id", "alias_revision_id"}))
        table = VendorAliasTable.from_records(alias_rows)
        binding = table.resolve_option_underlying(vendor, root, on,
                                                  decision_at=cutoff,
                                                  evidence_bytes=root_evidence.body)
        if binding is None:
            return None
        if binding.underlying_kind != "security":
            raise IdentityResolutionError("index underlying canonical record reader unavailable")
        position = table.rows.index(binding)
        alias_ingested = _identity_evidence_clock(alias_rows[position]["ingested_at"])
        # Writer ingested_at is second-precision UTC. Do not invent subsecond
        # ordering between it and source known_at; both must be observed by the
        # exact alias read, while source bytes must also be available independently.
        if max(binding.known_at, alias_ingested) > aliases_at or binding.known_at > source_at:
            raise IdentityResolutionError("option alias/source availability clocks conflict")

        listing_key, master_at = _captured_option_security_target(binding.security_id, on,
            decision_at=cutoff, security_master=security_master)
        return OptionUnderlyingIdentity(binding, listing_key, security_master.sha256,
                                        aliases.sha256, max(aliases_at, master_at, source_at))
    except IdentityError as exc:
        raise IdentityResolutionError(f"option identity contract invalid: {exc}") from exc


def _records(path: Path) -> list[dict[str, Any]]:
    """Compatibility reader for existing non-IW callers; no coherent-set claim."""
    if not path.is_file():
        raise IdentityResolutionError(f"required Data OS identity artifact missing: {path}")
    try:
        import pandas as pd

        return pd.read_parquet(path).to_dict("records")
    except Exception as exc:  # noqa: BLE001
        raise IdentityResolutionError(f"Data OS identity artifact unreadable: {path}: {exc}") from exc


def _security_sources(root: Path) -> tuple[IssuerMaster, VendorAliasTable, dict[str, dict[str, Any]]]:
    """One coherent LEGACY acquisition for this call, with no process cache.

    Explicitly project whole unrelated clocked namespaces through their owner's
    legacy API; never strip revision keys to reinterpret their rows as legacy.
    This does not provide native resolution or cross-adapter request pinning.
    """
    try:
        captured = read_reference_generation(root / SECURITY_MASTER.parent)
        master_rows = captured.records(SECURITY_MASTER.name)
        alias_rows = captured.records(VENDOR_ALIASES.name)
        legacy_rows = VendorAliasTable.legacy_only_records(alias_rows)
        issuer_master = IssuerMaster.from_records(master_rows)
        aliases = VendorAliasTable.from_records(legacy_rows)
    except IdentityError as exc:
        raise IdentityResolutionError(f"Data OS identity contract invalid: {exc}") from exc
    ids = [str(row.get("security_id") or "") for row in master_rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise IdentityResolutionError("security master contains missing or duplicate security_id")
    return issuer_master, aliases, {security_id: row for security_id, row in zip(ids, master_rows, strict=True)}


def _nonnull(value: object) -> str | None:
    if value is None or (isinstance(value, float) and value != value):  # noqa: PLR0124
        return None
    text = str(value).strip()
    return text or None


def _security_state(
    security_id: str,
    issuer_master: IssuerMaster,
    master_rows: dict[str, dict[str, Any]],
) -> str:
    if security_id not in master_rows:
        raise IdentityResolutionError(f"unknown canonical security: {security_id}")
    state = _nonnull(issuer_master.security_state_of(security_id))
    superseded_by = _nonnull(issuer_master.superseded_by_of(security_id))
    if superseded_by or (state and "SUPERSEDED" in state.upper()):
        return "superseded"
    if state:
        # The current owner enum contains supersession only.  Any future non-null
        # terminal state must remain unavailable until this consumer is amended.
        return "retired"
    return "active"


def _validate_us_equity_security_id(security_id: str) -> None:
    """Prove the canonical ID belongs to the frozen US-equity universe."""
    try:
        kind, listing = parse_id(security_id)
    except IdentityError as exc:
        raise IdentityResolutionError(
            f"malformed canonical security id: {security_id!r}"
        ) from exc
    if kind != "security":
        raise IdentityResolutionError(
            f"entity id is not a SEC:* security: {security_id!r}"
        )
    if listing.country != "US" or listing.mic not in US_EQUITY_MICS:
        raise IdentityResolutionError(
            f"canonical security is outside frozen us_equity scope: {security_id!r}"
        )


def load_current_symbol_map(
    root: str | Path = REPO_ROOT,
    vendor: str = CURRENT_EDGE_VENDOR,
    *,
    on: date | None = None,
) -> dict[str, str]:
    """Read one current vendor space into ``SEC:* -> symbol``.

    Callers should invoke this through ``RequestContext.memoize``.  The function
    deliberately carries no process cache: W1-A owns no cross-request identity or
    value cache.
    """
    if vendor in _CLOCKED_ALIAS_VENDORS:
        raise IdentityResolutionError("clocked alias vendor requires native observation proof")
    _issuer_master, table, _master_rows = _security_sources(Path(root))
    current = on or date.today()
    security_ids = sorted({row.security_id for row in table.rows if row.vendor == vendor})
    result: dict[str, str] = {}
    for security_id in security_ids:
        symbol = table.vendor_symbol_for(vendor, security_id, current)
        if symbol is not None:
            result[security_id] = symbol
    return result


def current_symbol_resolver(
    root: str | Path = REPO_ROOT,
    vendor: str = CURRENT_EDGE_VENDOR,
    *,
    on: date | None = None,
) -> Callable[[CanonicalEntity], str | None]:
    """Return a callable over one freshly loaded current catalog.

    Construct this at a request boundary.  Batch adapters should prefer
    :func:`load_current_symbol_map` through ``RequestContext.memoize``.
    """
    symbols = load_current_symbol_map(root, vendor, on=on)
    return lambda entity: symbols.get(entity.id) if entity.type == "security" else None


def _industry_ids(root: Path) -> frozenset[str]:
    path = root / INDUSTRY_RANKS
    if not path.is_file():
        raise IdentityResolutionError(f"current Stage industry identity artifact missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityResolutionError(f"current Stage industry identity artifact unreadable: {exc}") from exc
    if payload.get("schema") != "stage_industry_ranks.v1":
        raise IdentityResolutionError("current Stage industry identity schema is invalid")
    rows = (payload.get("regions") or {}).get("USA")
    if not isinstance(rows, list):
        raise IdentityResolutionError("current Stage industry artifact has no USA region rows")
    ids = [str(row.get("industry_id") or "").strip() for row in rows if isinstance(row, dict)]
    if not all(ids) or len(ids) != len(set(ids)):
        raise IdentityResolutionError("current Stage industry artifact has missing/duplicate industry_id")
    return frozenset(ids)


class DataOSIdentityNormalizer:
    """Request-scoped canonicalizer over current Data OS and Stage identity."""

    def __init__(
        self,
        root: str | Path = REPO_ROOT,
        *,
        today: Callable[[], date] | None = None,
    ) -> None:
        self.root = Path(root)
        self._today = today or date.today

    def normalize_many(self, entities: Sequence[EntityRequest]) -> tuple[CanonicalEntity, ...]:
        needs_security = any(entity.type == "security" for entity in entities)
        needs_industry = any(entity.type == "industry" for entity in entities)
        issuer_master: IssuerMaster | None = None
        aliases: VendorAliasTable | None = None
        master_rows: dict[str, dict[str, Any]] = {}
        industry_ids: frozenset[str] = frozenset()
        if needs_security:
            issuer_master, aliases, master_rows = _security_sources(self.root)
        if needs_industry:
            industry_ids = _industry_ids(self.root)

        current = self._today()
        result: list[CanonicalEntity] = []
        for entity in entities:
            if entity.type == "security":
                assert issuer_master is not None and aliases is not None
                if entity.symbol is not None:
                    symbol = str(entity.symbol).strip().upper()
                    security_id = aliases.resolve(CURRENT_EDGE_VENDOR, symbol, current)
                    if security_id is None:
                        raise IdentityResolutionError(
                            f"current symbol alias is unknown in Data OS {CURRENT_EDGE_VENDOR!r}: {symbol!r}"
                        )
                    alias_interpretation = "current_alias_only"
                else:
                    security_id = str(entity.id or "").strip()
                    alias_interpretation = None
                _validate_us_equity_security_id(security_id)
                state = _security_state(security_id, issuer_master, master_rows)
                result.append(
                    CanonicalEntity(
                        type="security",
                        id=security_id,
                        universe="us_equity",
                        state=state,
                        alias_interpretation=alias_interpretation,
                    )
                )
            elif entity.type == "industry":
                industry_id = str(entity.id or "").strip()
                if industry_id not in industry_ids:
                    raise IdentityResolutionError(
                        f"industry id is not present in current Stage USA identity: {industry_id!r}"
                    )
                result.append(CanonicalEntity("industry", industry_id, "us_industry"))
            else:
                raise IdentityResolutionError(f"unsupported entity type: {entity.type!r}")
        return tuple(result)
