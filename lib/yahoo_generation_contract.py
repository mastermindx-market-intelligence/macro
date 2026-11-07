"""Semantic adapter for the incumbent publisher's private Yahoo generations.

Publication, selection, locking and byte verification stay in the live
orchestrator. This module encodes explicit acquisition values and validates the
same captured bytes on admission and read. It never acquires or selects data.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any

from lib.yahoo_runtime_profile import (
    COHORT, MIN_SECTOR_HISTORY_SESSIONS, SECTOR_CLOSE_TICKERS, SNAPSHOT_SCHEMA,
    VerifiedYahooCohort, capture_sector_history,
)

YAHOO_GENERATION_DOMAIN = "yahoo-sector-close-14"
YAHOO_GENERATION_MEMBERS = tuple(f"yahoo/{ticker}.parquet" for ticker in SECTOR_CLOSE_TICKERS)
# Engineering decode bounds, not claimed observed history sizes. The generic
# publisher's 64MiB encoded-member and 512MiB cohort limits remain unchanged.
MAX_HISTORY_ROWS = 50_000
MAX_YAHOO_MEMBER_BYTES = 8 * 1024 * 1024
MAX_PARQUET_FOOTER_BYTES = 256 * 1024
MAX_PARQUET_DECODE_BYTES = 16 * 1024 * 1024
_VALUE_COLUMNS = ("open", "high", "low", "close", "close_price", "volume")
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,191}\Z")
_VENDOR = re.compile(r"[A-Za-z0-9^][A-Za-z0-9^=.-]{0,39}\Z")
_UNKNOWN_CLOCKS = {
    "vendor_publication_clock": "Not supplied per bar by yfinance",
    "provider_available_at": "First retrievable time is not observed",
    "vendor_session_metadata": "No per-bar session-completion proof supplied",
    "upstream_correction_clock": "Corrections are observed only on a later request",
}
_KNOWN_CLOCK_KEYS = frozenset(("evaluation_instant", "expected_session", "session_calendar",
    "target_calendar_verified", "completed_sessions_only", "minimum_history_sessions",
    "basis_tolerance", "fetch_period", "batch_size", "retries", "backoff_base_s"))
_LINEAGE_KEYS = frozenset(("provider", "ticker", "vendor_symbol", "alias_applied", "field",
    "basis", "close_price_basis", "attempt_periods", "basis_comparison", "prior",
    "completed_sessions_only", "expected_session", "rows", "first_session", "last_session", "status"))


class YahooGenerationContractError(ValueError):
    """Closed private-input failure code; no provider payload or path attached."""


@dataclass(frozen=True)
class EncodedYahooInputs:
    members: Mapping[str, bytes]
    input_identity: Mapping[str, Any]


@dataclass(frozen=True)
class YahooBootstrapCapture:
    """Explicit legacy byte capture, not an admitted runtime cohort."""
    members: Mapping[str, bytes | None]
    source_ref: str
    source_revision: str
    captured_at: datetime


@dataclass(frozen=True)
class VerifiedYahooGeneration:
    cohort: VerifiedYahooCohort
    snapshot: Any

    def prior_identity(self, *, captured_at: datetime) -> dict:
        """Identity of the exact captured bytes, not a lookup of current again."""
        stamp = _instant(captured_at)
        if stamp < _instant(self.snapshot.published_at):
            raise YahooGenerationContractError("prior_capture_before_publication")
        return {
            "kind": "generation", "source_ref": self.snapshot.generation_id,
            "content_id": self.snapshot.content_id, "captured_at": stamp.isoformat(),
            "domain": YAHOO_GENERATION_DOMAIN,
            "source_revision": self.snapshot.manifest["source_revision"],
            "member_bytes": {ticker: len(self.snapshot.members[name])
                             for ticker, name in zip(SECTOR_CLOSE_TICKERS, YAHOO_GENERATION_MEMBERS)},
            "member_sha256": {
                ticker: hashlib.sha256(self.snapshot.members[name]).hexdigest()
                for ticker, name in zip(SECTOR_CLOSE_TICKERS, YAHOO_GENERATION_MEMBERS)
            },
        }


def _instant(value: Any) -> datetime:
    try:
        stamp = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError
        return stamp.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError, OverflowError):
        raise YahooGenerationContractError("aware_clock_required") from None


def _session(value: Any) -> str:
    try:
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except (TypeError, ValueError):
        raise YahooGenerationContractError("invalid_source_session") from None
    return value


def _completed_target(instant: datetime) -> str:
    from lib import market_session
    try:
        local = market_session.market_local_date("US", instant)
        if not market_session.calendar_verified("US", local.year):
            raise ValueError
        target = market_session.expected_session("US", instant)
        if not market_session.calendar_verified("US", target.year):
            raise ValueError
        return target.isoformat()
    except Exception:
        raise YahooGenerationContractError("target_calendar_unavailable") from None


def _json_copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False))
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise YahooGenerationContractError("invalid_identity_json") from None


def _prior(value: Any, *, evaluation: datetime) -> dict:
    required = {"kind", "source_ref", "content_id", "captured_at", "member_sha256",
                "domain", "source_revision", "member_bytes"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise YahooGenerationContractError("invalid_prior_identity")
    result = _json_copy(dict(value))
    if (result["kind"] not in ("generation", "bootstrap")
            or not isinstance(result["source_ref"], str) or not _REFERENCE.fullmatch(result["source_ref"])
            or _instant(result["captured_at"]) > evaluation
            or not isinstance(result["member_sha256"], dict)
            or set(result["member_sha256"]) != set(SECTOR_CLOSE_TICKERS)
            or result["domain"] != YAHOO_GENERATION_DOMAIN
            or not isinstance(result["source_revision"], str) or not _REVISION.fullmatch(result["source_revision"])
            or not isinstance(result["member_bytes"], dict)
            or set(result["member_bytes"]) != set(SECTOR_CLOSE_TICKERS)):
        raise YahooGenerationContractError("invalid_prior_identity")
    cid = result["content_id"]
    if result["kind"] == "generation":
        if not isinstance(cid, str) or not _HEX.fullmatch(cid):
            raise YahooGenerationContractError("invalid_prior_identity")
    elif cid is not None:
        raise YahooGenerationContractError("invalid_prior_identity")
    for ticker, digest in result["member_sha256"].items():
        length = result["member_bytes"][ticker]
        if digest is None and length is None and result["kind"] == "bootstrap":
            continue
        if (not isinstance(digest, str) or not _HEX.fullmatch(digest)
                or type(length) is not int or length <= 0):
            raise YahooGenerationContractError("invalid_prior_identity")
    return result


def encode_history(frame: Any, *, source_session: str) -> bytes:
    """Encode a canonical primitive schema, with no pandas/extension metadata."""
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    captured = capture_sector_history(frame, source_session=source_session)
    if len(captured) > MAX_HISTORY_ROWS or not set(captured.columns).issubset(_VALUE_COLUMNS):
        raise YahooGenerationContractError("history_shape_invalid")
    names = [name for name in _VALUE_COLUMNS if name in captured]
    arrays = [pa.array(captured.index.to_numpy(dtype="datetime64[ns]"), type=pa.timestamp("ns"))]
    for name in names:
        column = captured[name]
        if (not pd.api.types.is_numeric_dtype(column) or pd.api.types.is_bool_dtype(column)
                or pd.api.types.is_complex_dtype(column)):
            raise YahooGenerationContractError("history_value_invalid")
        values = column.to_numpy(dtype=float, na_value=np.nan)
        present = ~np.isnan(values)
        if not np.isfinite(values[present]).all() or (values[present] < 0).any():
            raise YahooGenerationContractError("history_value_invalid")
        if name != "volume" and (values[present] == 0).any():
            raise YahooGenerationContractError("history_value_invalid")
        arrays.append(pa.array(values, type=pa.float64(), from_pandas=True))
    table = pa.Table.from_arrays(arrays, names=["session", *names])
    output = BytesIO()
    pq.write_table(table, output, version="2.6", compression="snappy", use_dictionary=False,
                   row_group_size=4096, store_schema=False, write_page_checksum=True)
    raw = output.getvalue()
    if len(raw) > MAX_YAHOO_MEMBER_BYTES:
        raise YahooGenerationContractError("history_bytes_invalid")
    return raw


def _open_history_parquet(raw: bytes):
    import pyarrow.parquet as pq
    if (not isinstance(raw, bytes) or not 12 <= len(raw) <= MAX_YAHOO_MEMBER_BYTES
            or raw[:4] != b"PAR1" or raw[-4:] != b"PAR1"):
        raise YahooGenerationContractError("history_bytes_invalid")
    footer = int.from_bytes(raw[-8:-4], "little")
    if not 0 < footer <= min(MAX_PARQUET_FOOTER_BYTES, len(raw) - 12):
        raise YahooGenerationContractError("history_footer_invalid")
    return pq.ParquetFile(BytesIO(raw), thrift_string_size_limit=1024 * 1024,
        thrift_container_size_limit=128_000, arrow_extensions_enabled=False,
        page_checksum_verification=True)


def decode_history(raw: bytes, *, source_session: str) -> Any:
    """Check bounded primitive parquet metadata before materializing values."""
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    try:
        with _open_history_parquet(raw) as parquet:
            metadata = parquet.metadata
            # No serialized Arrow/pandas schema or arbitrary metadata is accepted.
            if (metadata.metadata or not MIN_SECTOR_HISTORY_SESSIONS <= metadata.num_rows <= MAX_HISTORY_ROWS
                    or not 1 <= metadata.num_row_groups <= 32):
                raise YahooGenerationContractError("history_shape_invalid")
            schema = parquet.schema_arrow
            names = schema.names
            columns = [name for name in _VALUE_COLUMNS if name in names]
            if (names != ["session", *columns] or not {"close", "close_price"}.issubset(columns)
                    or schema.field("session").type != pa.timestamp("ns")
                    or any(schema.field(name).type != pa.float64() for name in columns)
                    or any(field.metadata for field in schema)):
                raise YahooGenerationContractError("history_schema_invalid")
            decoded_size = sum(metadata.row_group(i).total_byte_size for i in range(metadata.num_row_groups))
            if decoded_size > MAX_PARQUET_DECODE_BYTES:
                raise YahooGenerationContractError("history_decode_bound")
            table = parquet.read(use_threads=False, use_pandas_metadata=False)
        if table.num_rows != metadata.num_rows or table.nbytes > MAX_PARQUET_DECODE_BYTES:
            raise YahooGenerationContractError("history_decode_bound")
        frame = pd.DataFrame({name: table[name].to_numpy() for name in columns},
                             index=pd.DatetimeIndex(table["session"].to_numpy()))
        for name in columns:
            values = frame[name].to_numpy(dtype=float)
            present = ~np.isnan(values)
            if (not np.isfinite(values[present]).all()
                    or (values[present] < 0).any()
                    or (name != "volume" and (values[present] == 0).any())):
                raise YahooGenerationContractError("history_value_invalid")
        return capture_sector_history(frame, source_session=source_session)
    except YahooGenerationContractError:
        raise
    except Exception:
        raise YahooGenerationContractError("history_decode_invalid") from None


def _evidence(identity: Mapping[str, Any], *, published_at: str, now: datetime,
              source_revision: str, computed_at: str, require_current: bool) -> tuple[dict, str]:
    value = identity.get("yahoo_cohort") if isinstance(identity, Mapping) else None
    required = {"schema", "cohort", "source_session", "prepared_at", "producer_source_sha",
                "clocks", "prior", "members", "acquisition"}
    if not isinstance(value, dict) or set(value) != required:
        raise YahooGenerationContractError("invalid_yahoo_identity")
    if (value["schema"] != SNAPSHOT_SCHEMA or value["cohort"] != COHORT
            or not isinstance(source_revision, str) or not _REVISION.fullmatch(source_revision)
            or value["producer_source_sha"] != source_revision or value["prepared_at"] != computed_at):
        raise YahooGenerationContractError("invalid_yahoo_identity")
    source = _session(value["source_session"])
    evidence = value["acquisition"]
    if (not isinstance(evidence, dict)
            or set(evidence) != {"accepted", "reason", "requested", "returned", "failed", "primary_failed", "failure_reasons", "notes"}
            or evidence["accepted"] is not True or evidence["reason"] != "accepted"
            or not isinstance(evidence["requested"], list)
            or len(evidence["requested"]) != len(SECTOR_CLOSE_TICKERS)
            or any(not isinstance(t, str) for t in evidence["requested"])
            or set(evidence["requested"]) != set(SECTOR_CLOSE_TICKERS)
            or evidence["returned"] != evidence["requested"]
            or evidence["failed"] != [] or evidence["primary_failed"] != []
            or evidence["failure_reasons"] != {} or evidence["notes"] != []):
        raise YahooGenerationContractError("invalid_acquisition_evidence")
    clocks = value["clocks"]
    if not isinstance(clocks, dict) or set(clocks) != {"known", "unknown"}:
        raise YahooGenerationContractError("invalid_acquisition_clock")
    known, unknown = clocks["known"], clocks["unknown"]
    if (not isinstance(known, dict) or not isinstance(unknown, dict)
            or set(known) != _KNOWN_CLOCK_KEYS or unknown != _UNKNOWN_CLOCKS
            or known.get("expected_session") != source or known.get("session_calendar") != "US"
            or known.get("target_calendar_verified") is not True
            or known.get("completed_sessions_only") is not True
            or type(known.get("minimum_history_sessions")) is not int
            or known["minimum_history_sessions"] != MIN_SECTOR_HISTORY_SESSIONS
            or known.get("fetch_period") not in ("1mo", "max")):
        raise YahooGenerationContractError("invalid_acquisition_clock")
    # Reuse the acquisition owner's request policy validation; it also detaches
    # primitives and rejects bool/nonfinite retry/backoff/tolerance values.
    from collectors.yahoo import YahooRequestSettings
    try:
        YahooRequestSettings.capture({**known, "upsert_basis_tol": known.get("basis_tolerance")})
    except (TypeError, ValueError):
        raise YahooGenerationContractError("invalid_acquisition_policy") from None
    evaluation, prepared, publication, admission = map(_instant, (
        known.get("evaluation_instant"), value["prepared_at"], published_at, now))
    if not evaluation <= prepared <= publication <= admission:
        raise YahooGenerationContractError("invalid_acquisition_chronology")
    if _completed_target(evaluation) != source or _completed_target(publication) != source:
        raise YahooGenerationContractError("source_not_completed_target")
    if require_current and _completed_target(admission) != source:
        raise YahooGenerationContractError("source_not_current_target")
    _prior(value["prior"], evaluation=evaluation)
    if not isinstance(value["members"], dict) or set(value["members"]) != set(SECTOR_CLOSE_TICKERS):
        raise YahooGenerationContractError("invalid_yahoo_member_set")
    return value, source


def validate_yahoo_bundle(*, member_bytes: Mapping[str, bytes], input_identity: Mapping[str, Any],
                          published_at: str, now: datetime, source_revision: str,
                          computed_at: str, require_current: bool = False) -> dict:
    """Validate origin facts; older verified generations remain usable as priors."""
    if not isinstance(member_bytes, Mapping) or set(member_bytes) != set(YAHOO_GENERATION_MEMBERS):
        raise YahooGenerationContractError("invalid_yahoo_member_set")
    value, source = _evidence(input_identity, published_at=published_at, now=now,
        source_revision=source_revision, computed_at=computed_at, require_current=require_current)
    frames, vendors = {}, set()
    from lib import store
    comparisons = {store.BASIS_ALIGNED, store.BASIS_SHIFTED, store.BASIS_NO_OVERLAP,
                   store.BASIS_NO_PRIOR, store.BASIS_INCOMPARABLE, store.BASIS_COMPARISON_FAILED}
    for ticker, name in zip(SECTOR_CLOSE_TICKERS, YAHOO_GENERATION_MEMBERS):
        declared = value["members"][ticker]
        if not isinstance(declared, dict) or set(declared) != {"name", "sha256", "lineage"}:
            raise YahooGenerationContractError("invalid_yahoo_lineage")
        raw, lineage = member_bytes[name], declared["lineage"]
        if declared["name"] != name or declared["sha256"] != hashlib.sha256(raw).hexdigest():
            raise YahooGenerationContractError("member_identity_mismatch")
        if not isinstance(lineage, dict) or set(lineage) != _LINEAGE_KEYS:
            raise YahooGenerationContractError("invalid_yahoo_lineage")
        vendor, attempts, comparison = lineage.get("vendor_symbol"), lineage.get("attempt_periods"), lineage.get("basis_comparison")
        if (lineage.get("provider") != "yahoo" or lineage.get("ticker") != ticker
                or not isinstance(vendor, str) or not _VENDOR.fullmatch(vendor) or vendor in vendors
                or type(lineage.get("alias_applied")) is not bool or lineage["alias_applied"] != (vendor != ticker)
                or lineage.get("field") != "Adj Close" or lineage.get("basis") != "total_return"
                or lineage.get("close_price_basis") != "split_adjusted_dividend_unadjusted"
                or lineage.get("completed_sessions_only") is not True
                or lineage.get("expected_session") != source or lineage.get("status") != "accepted"
                or attempts not in (["1mo"], ["max"], ["1mo", "max"])
                or attempts[0] != value["clocks"]["known"]["fetch_period"]
                or not isinstance(comparison, dict)
                or (comparison and set(comparison) != {"close", "close_price"})
                or any(status not in comparisons for status in comparison.values())):
            raise YahooGenerationContractError("invalid_yahoo_lineage")
        vendors.add(vendor)
        present = value["prior"]["member_sha256"][ticker] is not None
        if lineage.get("prior") != ("present" if present else "absent"):
            raise YahooGenerationContractError("prior_identity_mismatch")
        if (attempts == ["max"] or not present) and comparison:
            raise YahooGenerationContractError("invalid_yahoo_lineage")
        if attempts[-1] == "1mo" and (not present or comparison != {"close": "aligned", "close_price": "aligned"}):
            raise YahooGenerationContractError("unqualified_window_merge")
        frame = decode_history(raw, source_session=source)
        if (type(lineage.get("rows")) is not int or lineage["rows"] != len(frame)
                or lineage.get("first_session") != frame.index[0].date().isoformat()
                or lineage.get("last_session") != source):
            raise YahooGenerationContractError("history_lineage_mismatch")
        frames[ticker] = frame
    return frames


def encode_yahoo_acquisition(acquisition: Any, *, prior_identity: Mapping[str, Any],
                             prepared_at: datetime, source_revision: str) -> EncodedYahooInputs:
    """Prepare explicit values; this does not publish or create verified authority."""
    from collectors.yahoo import CycleBenchmarkAcquisition
    if (not isinstance(acquisition, CycleBenchmarkAcquisition) or acquisition.accepted is not True
            or acquisition.reason != "accepted" or not isinstance(acquisition.requested, tuple)
            or len(acquisition.requested) != len(SECTOR_CLOSE_TICKERS)
            or set(acquisition.requested) != set(SECTOR_CLOSE_TICKERS)
            or acquisition.returned != acquisition.requested or acquisition.notes or acquisition.failed
            or acquisition.primary_failed or acquisition.failure_reasons
            or set(acquisition.frames) != set(SECTOR_CLOSE_TICKERS)
            or set(acquisition.lineage) != set(SECTOR_CLOSE_TICKERS)):
        raise YahooGenerationContractError("acquisition_not_accepted")
    clocks = _json_copy(dict(acquisition.clocks))
    evaluation = _instant(clocks.get("known", {}).get("evaluation_instant"))
    source = _session(clocks.get("known", {}).get("expected_session"))
    prepared = _instant(prepared_at).isoformat()
    members = {name: encode_history(acquisition.frames[ticker], source_session=source)
               for ticker, name in zip(SECTOR_CLOSE_TICKERS, YAHOO_GENERATION_MEMBERS)}
    identity = {"yahoo_cohort": {
        "schema": SNAPSHOT_SCHEMA, "cohort": COHORT, "source_session": source,
        "prepared_at": prepared, "producer_source_sha": source_revision,
        "clocks": clocks, "prior": _prior(prior_identity, evaluation=evaluation),
        "acquisition": {"accepted": acquisition.accepted, "reason": acquisition.reason,
            "requested": list(acquisition.requested), "returned": list(acquisition.returned),
            "failed": list(acquisition.failed), "primary_failed": list(acquisition.primary_failed),
            "failure_reasons": dict(acquisition.failure_reasons), "notes": list(acquisition.notes)},
        "members": {ticker: {"name": name, "sha256": hashlib.sha256(members[name]).hexdigest(),
                              "lineage": _json_copy(acquisition.lineage[ticker])}
                    for ticker, name in zip(SECTOR_CLOSE_TICKERS, YAHOO_GENERATION_MEMBERS)},
    }}
    # Validate at the preparation boundary, then again against the publisher's
    # actual target receipt after capture. No preparation timestamp authorizes
    # a delayed publication across the next completed-session boundary.
    validate_yahoo_bundle(member_bytes=members, input_identity=identity,
        published_at=prepared, now=_instant(prepared), source_revision=source_revision,
        computed_at=prepared, require_current=True)
    return EncodedYahooInputs(MappingProxyType(members), MappingProxyType(identity))


def prepare_yahoo_generation_request(*, sources: Mapping[str, Path], input_identity: Mapping[str, Any],
                                     generation_id: str, source_revision: str, lane: str):
    from scripts.vps_live_orchestrator import GenerationArtifact, GenerationRequest
    if set(sources) != set(YAHOO_GENERATION_MEMBERS):
        raise YahooGenerationContractError("invalid_yahoo_member_set")
    if not isinstance(generation_id, str) or not _REFERENCE.fullmatch(generation_id):
        raise YahooGenerationContractError("invalid_yahoo_generation_id")
    identity = _json_copy(dict(input_identity))
    declared = identity.get("yahoo_cohort", {})
    source, prepared = _session(declared.get("source_session")), declared.get("prepared_at")
    if declared.get("producer_source_sha") != source_revision:
        raise YahooGenerationContractError("producer_revision_mismatch")

    def validate_member(path: Path) -> str | None:
        try:
            decode_history(path.read_bytes(), source_session=source)
        except Exception as exc:
            return "yahoo_member_rejected:" + type(exc).__name__
        return None

    def validate_bundle(context) -> str | None:
        if (context.domain != YAHOO_GENERATION_DOMAIN or context.generation_id != generation_id
                or context.input_identity != identity or context.source_revision != source_revision
                or context.computed_at != prepared):
            return "yahoo_identity_changed_during_admission"
        try:
            validate_yahoo_bundle(member_bytes=context.members, input_identity=context.input_identity,
                published_at=context.published_at, now=context.admission_time,
                source_revision=context.source_revision, computed_at=context.computed_at,
                require_current=True)
        except Exception as exc:
            return "yahoo_semantic_rejected:" + type(exc).__name__
        return None

    return GenerationRequest(generation_id=generation_id, domain=YAHOO_GENERATION_DOMAIN,
        lane=lane, source_revision=source_revision, computed_at=prepared,
        input_identity=deepcopy(identity), bundle_validator=validate_bundle,
        artifacts=tuple(GenerationArtifact(name=name, source=Path(sources[name]), validator=validate_member)
                        for name in YAHOO_GENERATION_MEMBERS))


def read_verified_yahoo_cohort(*, generations_root: Path, now: datetime,
                               snapshot_reader=None, require_current: bool = False) -> VerifiedYahooGeneration:
    from scripts.vps_live_orchestrator import read_selected_generation
    root = Path(generations_root)
    if not root.is_absolute():
        raise YahooGenerationContractError("absolute_private_root_required")
    snapshot = (snapshot_reader or read_selected_generation)(generations_root=root,
        domain=YAHOO_GENERATION_DOMAIN, members=YAHOO_GENERATION_MEMBERS)
    return verify_yahoo_snapshot(snapshot, now=now, require_current=require_current)


def verify_yahoo_snapshot(snapshot, *, now: datetime, require_current: bool = False) -> VerifiedYahooGeneration:
    """One semantic decoder for selected and pinned retained captures."""
    if snapshot.domain != YAHOO_GENERATION_DOMAIN:
        raise YahooGenerationContractError("invalid_yahoo_domain")
    manifest = snapshot.manifest
    frames = validate_yahoo_bundle(member_bytes=snapshot.members,
        input_identity=manifest.get("input_identity"), published_at=snapshot.published_at,
        now=now, source_revision=manifest.get("source_revision"),
        computed_at=manifest.get("computed_at"), require_current=require_current)
    source = manifest["input_identity"]["yahoo_cohort"]["source_session"]
    return VerifiedYahooGeneration(VerifiedYahooCohort(
        generation_id=snapshot.generation_id, source_session=source,
        frames=MappingProxyType(frames)), snapshot)


def _unique_metadata(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise YahooGenerationContractError("legacy_metadata_ambiguous")
        output[key] = value
    return output


def decode_legacy_bootstrap_history(raw: bytes) -> Any:
    """Decode a bounded explicit legacy prior; never an accepted snapshot.

    The installed legacy format has one physical timestamp index named by
    pandas metadata. Only that index declaration is used. No pandas object,
    attrs, extension column, path, loader or fallback is reconstructed.
    A prior can be shallow; strict acquisition must recover it before admission.
    """
    import numpy as np
    import pandas as pd
    import pyarrow as pa

    try:
        with _open_history_parquet(raw) as parquet:
            meta = parquet.metadata
            if not 1 <= meta.num_rows <= MAX_HISTORY_ROWS or not 1 <= meta.num_row_groups <= 32:
                raise YahooGenerationContractError("legacy_history_shape_invalid")
            raw_metadata = meta.metadata or {}
            if not set(raw_metadata).issubset({b"pandas", b"ARROW:schema"}) or b"pandas" not in raw_metadata:
                raise YahooGenerationContractError("legacy_index_metadata_required")
            pandas = json.loads(raw_metadata[b"pandas"].decode("utf-8"), object_pairs_hook=_unique_metadata)
            indices = pandas.get("index_columns") if isinstance(pandas, dict) else None
            if (not isinstance(indices, list) or len(indices) != 1
                    or not isinstance(indices[0], str) or indices[0] in _VALUE_COLUMNS):
                raise YahooGenerationContractError("legacy_index_metadata_required")
            index_name = indices[0]
            schema = parquet.schema_arrow
            names = schema.names
            columns = [name for name in _VALUE_COLUMNS if name in names]
            if (len(set(names)) != len(names) or set(names) != {index_name, *columns}
                    or not {"close", "close_price"}.issubset(columns)):
                raise YahooGenerationContractError("legacy_history_schema_invalid")
            index_type = schema.field(index_name).type
            if (not pa.types.is_timestamp(index_type) or index_type.tz is not None
                    or index_type.unit not in ("ms", "us", "ns")
                    or any(not (pa.types.is_floating(schema.field(name).type)
                                or pa.types.is_integer(schema.field(name).type)) for name in columns)
                    or any(field.metadata for field in schema)):
                raise YahooGenerationContractError("legacy_history_schema_invalid")
            if sum(meta.row_group(i).total_byte_size for i in range(meta.num_row_groups)) > MAX_PARQUET_DECODE_BYTES:
                raise YahooGenerationContractError("history_decode_bound")
            table = parquet.read(columns=[index_name, *columns], use_threads=False, use_pandas_metadata=False)
        if table.num_rows != meta.num_rows or table.nbytes > MAX_PARQUET_DECODE_BYTES:
            raise YahooGenerationContractError("history_decode_bound")
        frame = pd.DataFrame({name: table[name].to_numpy() for name in columns},
            index=pd.DatetimeIndex(table[index_name].to_numpy(), name=index_name))
        for name in columns:
            values = frame[name].to_numpy(dtype=float)
            present = ~np.isnan(values)
            if (not np.isfinite(values[present]).all() or (values[present] < 0).any()
                    or (name != "volume" and (values[present] == 0).any())):
                raise YahooGenerationContractError("history_value_invalid")
        return capture_sector_history(frame, minimum_sessions=1)
    except YahooGenerationContractError:
        raise
    except Exception:
        raise YahooGenerationContractError("legacy_history_decode_invalid") from None


def decode_bootstrap_capture(capture: YahooBootstrapCapture) -> tuple[dict, dict]:
    """Derive actual prior values and identities from the same explicit bytes."""
    if (not isinstance(capture, YahooBootstrapCapture) or not isinstance(capture.members, Mapping)
            or len(capture.members) != len(SECTOR_CLOSE_TICKERS)):
        raise YahooGenerationContractError("invalid_bootstrap_capture")
    raw = dict(capture.members)
    if set(raw) != set(SECTOR_CLOSE_TICKERS) or any(
        value is not None and (type(value) is not bytes or not 0 < len(value) <= MAX_YAHOO_MEMBER_BYTES)
        for value in raw.values()
    ):
        raise YahooGenerationContractError("invalid_bootstrap_capture")
    stamp = _instant(capture.captured_at)
    prior = _prior({"kind": "bootstrap", "source_ref": capture.source_ref,
        "source_revision": capture.source_revision, "domain": YAHOO_GENERATION_DOMAIN,
        "content_id": None, "captured_at": stamp.isoformat(),
        "member_sha256": {ticker: hashlib.sha256(value).hexdigest() if value is not None else None
                          for ticker, value in raw.items()},
        "member_bytes": {ticker: len(value) if value is not None else None for ticker, value in raw.items()},
    }, evaluation=stamp)
    frames = {ticker: decode_legacy_bootstrap_history(raw[ticker]) if raw[ticker] is not None else None
              for ticker in SECTOR_CLOSE_TICKERS}
    return frames, prior
