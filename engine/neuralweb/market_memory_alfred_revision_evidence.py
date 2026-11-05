"""engine.neuralweb.market_memory_alfred_revision_evidence — SOURCE_ONLY ALFRED revision evidence.

CLASSIFICATION: internal, unregistered, source-only retrospective evidence.
This module reads ONE already published, generation-pinned ALFRED ``CPIAUCSL``
source receipt out of the private Market Memory source store and projects the
retrospective revision history of at most eight requested monthly periods into
a closed, display-only context.

It is NOT a feature projection, NOT a fit, NOT a training input, NOT a study
admission and NOT a customer surface.  Every claim it emits is false, its
units are ``not_retained``, its conversion is ``not_performed`` and its
authority is ``display_only`` for an ``internal_unregistered`` audience.  The
existing five-house-field source grant does NOT extend to raw constituent
redistribution or to training; this module performs neither.

BOUNDARY OF THIS PRODUCER
-------------------------
* It never writes.  It never captures, never intakes and never publishes a
  source artifact; it only reads bytes the native source owner already
  admitted and published.
* It accepts NO caller path, root, rows, reader, report, policy, callback,
  clock or eligibility flag.  The store root, the canonical vintage path and
  the whole qualification chain are fixed by the native owner.
* The one capability it hands back is sealed in-process.  A serialized dict,
  a copied packet or a subclass of the capability type is NOT a capability.
* Disclosure re-runs the native owner checks (generation ancestry, receipt
  membership and copy identity, canonical file byte binding, source code
  bytes) immediately before and immediately after the answer is produced.  A
  changed source, receipt, file or module denies; it never refreshes, repins
  or silently re-derives.
* The module keeps no full-matrix cache, export or store.  The capability
  owns only the bounded closed body.

HOW TO CITE A ROW
-----------------
A row is cited by composition, never by inventing a byte span: the parent
source digest (``source.upstream_sha256``), the series (``source.series_id``),
the period, the row's ``source_date``, the row's ``row_sha256`` and the
parser identity (``source_ref.source_owner_sha256`` /
``source_ref.normalizer_sha256``).  Parquet is a columnar format: there is no
text-byte span to quote, and this module never pretends otherwise.
"""

from __future__ import annotations

import io
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from engine import release_target_truth as normalizer
from engine.neuralweb import market_memory_sources as sources
from engine.release_target_truth import (
    default_vintage_path,
    normalize_full_vintage_frame,
)

__all__ = [
    "AlfredRevisionEvidenceCapability",
    "AlfredRevisionEvidenceError",
    "disclose_alfred_revision_evidence",
    "read_published_alfred_revision_evidence",
]

# --------------------------------------------------------------------------- #
# Frozen contract constants
# --------------------------------------------------------------------------- #
SCHEMA = "market_memory.alfred_revision_source_context.v1"
MODE = "SOURCE_ONLY_RETROSPECTIVE_EVIDENCE"
AUTHORITY = "display_only"
AUDIENCE = "internal_unregistered"
UNITS = "not_retained"
CONVERSION = "not_performed"
ASSURANCE = "imported_source_bytes_not_external_runtime_attestation"

CONTEXT_ID_PREFIX = "mmalfredrevision_"
SOURCE_ID = "fred_alfred:CPIAUCSL"
SERIES_ID = "CPIAUCSL"
SOURCE_OUTPUT_TYPE = 2

# The closed context is a bounded projection, never a matrix export.
CONTEXT_MAX_BYTES = 64 * 1024
# Upstream byte ceiling is the native owner's (32 MiB); the row ceiling below
# is this module's own decompression bound and is checked against the parquet
# METADATA before any frame is materialized.
MAX_MATRIX_ROWS = 1_000_000
MAX_REQUESTED_PERIODS = 8
MAX_VINTAGES = 32
SELECTION_RULE = "first_observation_then_value_changes.v1"

# The only two path constants in this module.  They exist so a synthetic test
# store can stand in for the fixed production locations; they are never
# caller-selectable and they never come from a receipt.
_STORE_ROOT = Path("/var/lib/macro-market-memory/state/sources")
_REPOSITORY_ROOT = sources._REPOSITORY_ROOT

_GENERATION_ID_RE = re.compile(r"mmsgen_[a-f0-9]{64}\Z")
_RECEIPT_ID_RE = re.compile(r"mmsrc_[a-f0-9]{64}\Z")
_MONTH_RE = re.compile(r"[0-9]{4}-(?:0[1-9]|1[0-2])-01\Z")
_UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"
    r"(?:Z|\+00:00)\Z"
)

_LIMITATIONS: tuple[str, ...] = (
    "retained_source_not_fresh_provider_authentication",
    "source_dates_are_retrospective_vendor_dates_not_house_knowledge",
    "units_not_retained_and_conversion_not_performed",
    "no_regime_coordinates_or_retrieval_membership",
    "rows_periods_vintages_not_independent_episodes",
    "internal_source_context_not_customer_or_study_admission",
)

_CLAIM_FIELDS: tuple[str, ...] = (
    "feature_projection_eligible",
    "fit_eligible",
    "training_eligible",
    "promotion_eligible",
    "operational_study_admission",
    "action_admitted",
    "customer_disclosure_admitted",
    "historical_intraday_availability",
    "forecast_skill_established",
    "independent_episodes_established",
    "source_authenticated_by_fresh_provider",
    "source_activated",
)

# The supported constructor is private to the source owner. This in-process
# seal is neither source provenance nor a customer authorization grant.
_SEAL = object()


class AlfredRevisionEvidenceError(RuntimeError):
    """The requested ALFRED revision evidence cannot be produced or disclosed."""


# --------------------------------------------------------------------------- #
# Canonical helpers
# --------------------------------------------------------------------------- #
def _canonical(value: object) -> bytes:
    """The native store's canonical finite JSON encoding."""
    try:
        return sources._canonical_bytes(value)
    except Exception as exc:  # noqa: BLE001 — surfaced as a boundary error
        raise AlfredRevisionEvidenceError(
            "value is not canonical finite JSON"
        ) from exc


def _sha256_hex(body: bytes) -> str:
    return sha256(body).hexdigest()


def _parse_utc(value: object, *, field: str) -> datetime:
    if type(value) is not str or not _UTC_RE.fullmatch(value):
        raise AlfredRevisionEvidenceError(
            f"{field} must be an exact RFC3339 UTC timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AlfredRevisionEvidenceError(f"{field} is not a valid timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise AlfredRevisionEvidenceError(f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _utc_stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


# --------------------------------------------------------------------------- #
# Request validation (always before any source open)
# --------------------------------------------------------------------------- #
def _validate_request(
    generation_id: Any,
    receipt_id: Any,
    knowledge_cutoff: Any,
    periods: Any,
    maximum_vintages: Any,
) -> dict[str, Any]:
    if type(generation_id) is not str or not _GENERATION_ID_RE.fullmatch(generation_id):
        raise AlfredRevisionEvidenceError(
            "generation_id must be an exact native source generation identifier"
        )
    if type(receipt_id) is not str or not _RECEIPT_ID_RE.fullmatch(receipt_id):
        raise AlfredRevisionEvidenceError(
            "receipt_id must be an exact native source receipt identifier"
        )
    cutoff_dt = _parse_utc(knowledge_cutoff, field="knowledge_cutoff")
    if type(periods) is not tuple:
        raise AlfredRevisionEvidenceError("periods must be an exact tuple")
    if not 1 <= len(periods) <= MAX_REQUESTED_PERIODS:
        raise AlfredRevisionEvidenceError(
            f"periods must hold between 1 and {MAX_REQUESTED_PERIODS} periods"
        )
    clean_periods: list[str] = []
    seen: set[str] = set()
    for value in periods:
        if type(value) is not str or not _MONTH_RE.fullmatch(value):
            raise AlfredRevisionEvidenceError(
                "periods must contain exact YYYY-MM-01 real month strings"
            )
        try:
            date(int(value[0:4]), int(value[5:7]), 1)
        except ValueError as exc:
            raise AlfredRevisionEvidenceError(
                "periods must contain real calendar months"
            ) from exc
        if value in seen:
            raise AlfredRevisionEvidenceError("periods must not repeat a month")
        seen.add(value)
        clean_periods.append(value)
    if type(maximum_vintages) is not int:
        raise AlfredRevisionEvidenceError(
            "maximum_vintages must be an exact integer, not a boolean"
        )
    if not 1 <= maximum_vintages <= MAX_VINTAGES:
        raise AlfredRevisionEvidenceError(
            f"maximum_vintages must be between 1 and {MAX_VINTAGES}"
        )
    return {
        "generation_id": generation_id,
        "receipt_id": receipt_id,
        "knowledge_cutoff": _utc_stamp(cutoff_dt),
        "periods": clean_periods,
        "maximum_vintages": maximum_vintages,
    }


# --------------------------------------------------------------------------- #
# Native owner checks
# --------------------------------------------------------------------------- #
def _require_qualified_receipt(receipt: Any) -> dict[str, Any]:
    """Require a complete, live-captured, non-projected native source receipt."""
    if not isinstance(receipt, Mapping):
        raise AlfredRevisionEvidenceError("native source receipt is not an object")
    if receipt.get("source_system") != "FRED/ALFRED":
        raise AlfredRevisionEvidenceError("source receipt is not a FRED/ALFRED receipt")
    if receipt.get("series_id") != SERIES_ID:
        raise AlfredRevisionEvidenceError("source receipt is not a CPIAUCSL receipt")
    output_type = receipt.get("source_output_type")
    if type(output_type) is not int or output_type != SOURCE_OUTPUT_TYPE:
        raise AlfredRevisionEvidenceError(
            "source receipt is not an ALFRED output_type=2 receipt"
        )
    quality = receipt.get("quality")
    if not isinstance(quality, Mapping):
        raise AlfredRevisionEvidenceError("source receipt carries no quality block")
    if quality.get("status") != "complete":
        raise AlfredRevisionEvidenceError("source receipt is not complete")
    if quality.get("reconstruction_only") is not False:
        raise AlfredRevisionEvidenceError(
            "legacy reconstructed source receipts are not source evidence"
        )
    if quality.get("source_evidence_eligible") is not True:
        raise AlfredRevisionEvidenceError(
            "source receipt is not source-evidence eligible"
        )
    for field in (
        "feature_projection_eligible",
        "training_eligible",
        "promotion_eligible",
    ):
        if quality.get(field) is not False:
            raise AlfredRevisionEvidenceError(
                f"source receipt must keep {field} false"
            )
    provenance = receipt.get("provenance")
    if not isinstance(provenance, Mapping):
        raise AlfredRevisionEvidenceError("source receipt carries no provenance block")
    if provenance.get("evidence_basis") != "live_captured_source_vintage":
        raise AlfredRevisionEvidenceError(
            "source receipt is not bound to live captured source bytes"
        )
    return dict(receipt)


def _canonical_upstream_path() -> Path:
    """The fixed canonical CPIAUCSL vintage artifact owned by the native owner."""
    return default_vintage_path(_REPOSITORY_ROOT, SERIES_ID)


def _read_bound_canonical_upstream(receipt: Mapping[str, Any]) -> tuple[bytes, str, int]:
    """Read the canonical vintage artifact and bind it to the receipt bytes."""
    path = _canonical_upstream_path()
    try:
        bounded = sources._read_bounded(
            path,
            limit=sources._MAX_UPSTREAM_BYTES,
            label="CPIAUCSL canonical vintage artifact",
        )
    except Exception as exc:  # noqa: BLE001 — surfaced as a boundary error
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact is unavailable"
        ) from exc
    body = bounded.body
    digest = _sha256_hex(body)
    provenance = receipt["provenance"]
    if digest != provenance.get("upstream_artifact_sha256"):
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact does not match the receipt digest"
        )
    if len(body) != provenance.get("upstream_artifact_bytes"):
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact does not match the receipt size"
        )
    return body, digest, len(body)


def _read_native_receipt(
    generation_id: str, receipt_id: str
) -> dict[str, Any]:
    """Read the receipt through the genuine native reader, pinned to a generation.

    ``SourceArtifactReader`` walks the published ancestry from HEAD to the
    pinned generation, so a generation that is no longer published is refused
    by the native owner, and ``read_receipt`` refuses a receipt that is not a
    member of that generation or whose two receipt copies disagree.
    """
    try:
        reader = sources.SourceArtifactReader(_STORE_ROOT, generation_id=generation_id)
    except Exception as exc:  # noqa: BLE001 — surfaced as a boundary error
        raise AlfredRevisionEvidenceError(
            "the native source store is not readable at the fixed store root"
        ) from exc
    try:
        receipt = reader.read_receipt(receipt_id, generation_id=generation_id)
    except Exception as exc:  # noqa: BLE001 — surfaced as a boundary error
        raise AlfredRevisionEvidenceError(
            "the receipt is not a member of the pinned published generation"
        ) from exc
    return _require_qualified_receipt(receipt)


def _module_sha256(module: Any) -> str:
    path = getattr(module, "__file__", None)
    if not path:
        raise AlfredRevisionEvidenceError("source module has no readable file")
    try:
        return _sha256_hex(Path(path).read_bytes())
    except OSError as exc:
        raise AlfredRevisionEvidenceError("source module bytes are unavailable") from exc


def _producer_module_sha256() -> str:
    try:
        return _sha256_hex(Path(__file__).read_bytes())
    except OSError as exc:
        raise AlfredRevisionEvidenceError(
            "producer module bytes are unavailable"
        ) from exc


def _capture_owner_state(
    generation_id: str, receipt_id: str, *, knowledge_cutoff: datetime
) -> dict[str, Any]:
    """Run the full native owner check chain and return the bound lineage."""
    receipt = _read_native_receipt(generation_id, receipt_id)
    observed_dt = _parse_utc(receipt["clocks"]["observed_at"], field="observed_at")
    # Native current time is fixed by this owner, never a caller clock. The
    # receipt clock describes this snapshot's observation, not first-ever
    # series knowledge or an exact durable-publication timestamp.
    if knowledge_cutoff > datetime.now(timezone.utc):
        raise AlfredRevisionEvidenceError("knowledge_cutoff is in the future")
    if knowledge_cutoff < observed_dt:
        raise AlfredRevisionEvidenceError(
            "knowledge_cutoff precedes the native house observation clock"
        )
    body, upstream_sha256, upstream_bytes = _read_bound_canonical_upstream(receipt)
    return {
        "receipt": receipt,
        "receipt_sha256": _sha256_hex(_canonical(receipt)),
        "upstream_body": body,
        "upstream_sha256": upstream_sha256,
        "upstream_bytes": upstream_bytes,
        "source_owner_sha256": _module_sha256(sources),
        "normalizer_sha256": _module_sha256(normalizer),
        "producer_sha256": _producer_module_sha256(),
    }


# --------------------------------------------------------------------------- #
# Matrix materialization (bounded, native normalizer, no release targets)
# --------------------------------------------------------------------------- #
def _materialize_matrix(
    body: bytes, receipt: Mapping[str, Any]
) -> Any:
    """Decode and normalize the canonical vintage matrix under fixed bounds."""
    try:
        import pyarrow.parquet as pq  # noqa: PLC0415 — decoder-local import

        metadata = pq.ParquetFile(io.BytesIO(body)).metadata
        row_count = int(metadata.num_rows)
    except Exception as exc:  # noqa: BLE001 — surfaced as a boundary error
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact metadata is unreadable"
        ) from exc
    if row_count > MAX_MATRIX_ROWS:
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact exceeds the qualified matrix row bound"
        )
    import pandas as pd  # noqa: PLC0415 — decoder-local import

    try:
        raw = pd.read_parquet(io.BytesIO(body))
    except Exception as exc:  # noqa: BLE001 — surfaced as a boundary error
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact is not a readable parquet matrix"
        ) from exc
    if "source_output_type" not in raw.columns:
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact lacks the mandatory source_output_type marker"
        )
    try:
        normalized = normalize_full_vintage_frame(raw, series_id=SERIES_ID)
    except Exception as exc:  # noqa: BLE001 — the native normalizer refuses
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact is not a valid full-vintage matrix"
        ) from exc
    if len(normalized) != len(raw):
        raise AlfredRevisionEvidenceError(
            "CPIAUCSL normalization dropped or deduplicated source rows"
        )
    if set(normalized["series"]) != {SERIES_ID}:
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact contains another series"
        )
    output_types = normalized["source_output_type"]
    if len(output_types) and set(output_types) != {SOURCE_OUTPUT_TYPE}:
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact is not ALFRED output_type=2"
        )
    if not normalized["value"].map(
        lambda value: math.isfinite(float(value))
    ).all():
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact contains a non-finite value"
        )
    provenance = receipt["provenance"]
    if len(normalized) != provenance.get("matrix_rows"):
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact does not match the receipt row count"
        )
    if int(normalized["period"].nunique()) != provenance.get("matrix_periods"):
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact does not match the receipt period count"
        )
    if int(normalized["realtime_start"].nunique()) != provenance.get(
        "matrix_release_dates"
    ):
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL vintage artifact does not match the receipt source-date count"
        )
    newest_source_date = normalized["realtime_start"].max().date().isoformat()
    if newest_source_date != receipt["clocks"]["source_date"]:
        raise AlfredRevisionEvidenceError(
            "canonical CPIAUCSL newest source date does not match the receipt source date"
        )
    return normalized


# --------------------------------------------------------------------------- #
# Projection
# --------------------------------------------------------------------------- #
def _row_digest(
    series: str,
    period: Any,
    value: Any,
    realtime_start: Any,
    realtime_end: Any,
) -> str:
    preimage = {
        "series": series,
        "period": period.date().isoformat() if hasattr(period, "date") else str(period),
        "value": float(value),
        "realtime_start": (
            realtime_start.date().isoformat()
            if hasattr(realtime_start, "date")
            else str(realtime_start)
        ),
        "realtime_end": (
            realtime_end.isoformat()
            if hasattr(realtime_end, "isoformat")
            else str(realtime_end)
        ),
    }
    return _sha256_hex(_canonical(preimage))


def _project_periods(
    normalized: Any, periods: list[str], maximum_vintages: int
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Project the requested periods and the full-source accounting counters."""
    frame = normalized.sort_values(["period", "realtime_start"], kind="stable")
    by_period: dict[str, list[tuple[Any, ...]]] = {}
    changed_periods = 0
    for row in frame.itertuples(index=False):
        key = row.period.date().isoformat()
        by_period.setdefault(key, []).append(row)
    for key, rows in by_period.items():
        if len({float(item.value) for item in rows}) > 1:
            changed_periods += 1

    projected: list[dict[str, Any]] = []
    returned_rows = 0
    omitted_rows = 0
    for period in periods:
        rows = by_period.get(period, [])
        total = len(rows)
        source_distinct = len({float(item.value) for item in rows})
        # Inspect reported changes, rather than spending the bound on a flat
        # vintage prefix. Compare consecutive observations so A->B->A retains
        # both changes; global value deduplication would erase the reversion.
        change_rows = []
        previous_value = None
        for item in rows:
            value = float(item.value)
            if not change_rows or value != previous_value:
                change_rows.append(item)
            previous_value = value
        returned = change_rows[:maximum_vintages]
        omitted = total - len(returned)
        returned_rows += len(returned)
        omitted_rows += omitted
        projected.append(
            {
                "period": period,
                "status": "OBSERVED" if total else "ABSENT",
                "selection_rule": SELECTION_RULE,
                "total_vintages": total,
                "returned_vintages": len(returned),
                "omitted_vintages": omitted,
                "source_value_change_count": max(0, len(change_rows) - 1),
                "unchanged_vintages_omitted": total - len(change_rows),
                "omitted_change_rows": len(change_rows) - len(returned),
                "source_distinct_values": source_distinct,
                "returned_distinct_values": len({float(item.value) for item in returned}),
                "revision_value_change_observed": source_distinct > 1,
                "rows": [
                    {
                        "source_date": item.realtime_start.date().isoformat(),
                        "source_valid_through_date": item.realtime_end.isoformat(),
                        "value": float(item.value),
                        "row_sha256": _row_digest(
                            SERIES_ID,
                            item.period,
                            item.value,
                            item.realtime_start,
                            item.realtime_end,
                        ),
                    }
                    for item in returned
                ],
            }
        )
    accounting = {
        "matrix_rows": int(len(frame)),
        "matrix_periods": int(frame["period"].nunique()),
        "matrix_source_dates": int(frame["realtime_start"].nunique()),
        "periods_with_changed_values": changed_periods,
        "returned_rows": returned_rows,
        "omitted_rows": omitted_rows,
    }
    return projected, accounting


# --------------------------------------------------------------------------- #
# Capability
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True, init=False, repr=False)
class AlfredRevisionEvidenceCapability:
    """Owner-produced immutable evidence; every disclosure rechecks custody.

    Copying evidence supplies no current access or customer authorization.
    Serialized dictionaries cannot call the supported owner constructor.
    """

    _body: bytes
    _body_sha256: str
    _request: bytes
    _lineage: bytes
    _binding_digest: str
    _seal: object

    def __init__(self, body, request, lineage, *, _key=None):
        if (_key is not _SEAL or type(body) is not bytes
                or type(request) is not bytes or type(lineage) is not bytes
                or not 0 < len(body) <= CONTEXT_MAX_BYTES):
            raise AlfredRevisionEvidenceError("owner-produced revision evidence required")
        for name, value in (("_body", body), ("_body_sha256", _sha256_hex(body)),
                            ("_request", request), ("_lineage", lineage),
                            ("_binding_digest", _sha256_hex(body + b"\0" + request + b"\0" + lineage)),
                            ("_seal", _SEAL)):
            object.__setattr__(self, name, value)

    def _seal_matches(self) -> bool:
        return (getattr(self, "_seal", None) is _SEAL
            and type(getattr(self, "_body", None)) is bytes
            and type(getattr(self, "_request", None)) is bytes
            and type(getattr(self, "_lineage", None)) is bytes
            and 0 < len(self._body) <= CONTEXT_MAX_BYTES
            and _sha256_hex(self._body) == self._body_sha256
            and _sha256_hex(self._body + b"\0" + self._request + b"\0" + self._lineage)
                == self._binding_digest)

    def _sealed_body(self) -> dict[str, Any]:
        if not self._seal_matches():
            raise AlfredRevisionEvidenceError(
                "the sealed capability body has been altered"
            )
        return json.loads(self._body)


def _seal_capability(
    body: dict[str, Any],
    request: Mapping[str, Any],
    lineage: Mapping[str, Any],
) -> AlfredRevisionEvidenceCapability:
    body_bytes = _canonical(body)
    request_bytes = _canonical(request)
    lineage_bytes = _canonical(lineage)
    return AlfredRevisionEvidenceCapability(
        body_bytes, request_bytes, lineage_bytes, _key=_SEAL,
    )


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
def read_published_alfred_revision_evidence(
    generation_id: str,
    receipt_id: str,
    *,
    knowledge_cutoff: str,
    periods: tuple[str, ...],
    maximum_vintages: int = 32,
) -> AlfredRevisionEvidenceCapability:
    """Read one published ALFRED revision and seal its closed source context.

    ``generation_id`` and ``receipt_id`` are exact opaque native identifiers.
    ``knowledge_cutoff`` is an exact RFC3339 UTC timestamp and must not
    precede this snapshot's house observation clock or exceed native current
    UTC time. That observation clock is neither series-first knowledge nor
    exact durable publication. ``periods`` is an exact
    tuple of 1..8 unique ``YYYY-MM-01`` months.  ``maximum_vintages`` is an
    exact integer in 1..32, bounding the first observation plus chronological
    value-change rows for each period; it does not bound a flat vintage prefix.

    Returns an :class:`AlfredRevisionEvidenceCapability`.  Use
    :func:`disclose_alfred_revision_evidence` to obtain the closed context.
    """
    request = _validate_request(
        generation_id, receipt_id, knowledge_cutoff, periods, maximum_vintages
    )
    cutoff_dt = _parse_utc(request["knowledge_cutoff"], field="knowledge_cutoff")

    state = _capture_owner_state(
        request["generation_id"], request["receipt_id"], knowledge_cutoff=cutoff_dt
    )
    receipt = state["receipt"]
    normalized = _materialize_matrix(state["upstream_body"], receipt)
    projected, accounting = _project_periods(
        normalized, request["periods"], request["maximum_vintages"]
    )

    observed = sum(1 for row in projected if row["status"] == "OBSERVED")
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": MODE,
        "authority": AUTHORITY,
        "audience": AUDIENCE,
        "knowledge_cutoff": request["knowledge_cutoff"],
        "source": {
            "source_id": SOURCE_ID,
            "series_id": SERIES_ID,
            "source_output_type": SOURCE_OUTPUT_TYPE,
            "store_id": receipt["store_id"],
            "generation_id": request["generation_id"],
            "receipt_id": request["receipt_id"],
            "receipt_sha256": state["receipt_sha256"],
            "capture_id": receipt["capture_id"],
            "vintage_id": receipt["vintage_id"],
            "revision_id": receipt["revision_id"],
            "upstream_sha256": state["upstream_sha256"],
            "upstream_bytes": state["upstream_bytes"],
        },
        "clocks": dict(receipt["clocks"]),
        "availability_evidence": dict(receipt["availability_evidence"]),
        "quality": dict(receipt["quality"]),
        "units": UNITS,
        "conversion": CONVERSION,
        "accounting": {
            "matrix_rows": accounting["matrix_rows"],
            "matrix_periods": accounting["matrix_periods"],
            "matrix_source_dates": accounting["matrix_source_dates"],
            "periods_with_changed_values": accounting["periods_with_changed_values"],
            "maximum_vintages": request["maximum_vintages"],
            "requested_periods": len(request["periods"]),
            "observed_requested_periods": observed,
            "absent_requested_periods": len(request["periods"]) - observed,
            "returned_rows": accounting["returned_rows"],
            "omitted_rows": accounting["omitted_rows"],
        },
        "periods": projected,
        "claims": {field: False for field in _CLAIM_FIELDS},
        "limitations": list(_LIMITATIONS),
        "source_ref": {
            "source_owner_module": "engine.neuralweb.market_memory_sources",
            "source_owner_sha256": state["source_owner_sha256"],
            "normalizer_module": "engine.release_target_truth",
            "normalizer_sha256": state["normalizer_sha256"],
            "producer_module": "engine.neuralweb.market_memory_alfred_revision_evidence",
            "producer_sha256": state["producer_sha256"],
            "assurance": ASSURANCE,
        },
    }
    body["context_id"] = CONTEXT_ID_PREFIX + _sha256_hex(
        _canonical({key: value for key, value in body.items() if key != "context_id"})
    )
    body_bytes = _canonical(body)
    if len(body_bytes) > CONTEXT_MAX_BYTES:
        raise AlfredRevisionEvidenceError(
            "the closed source context exceeds its canonical byte bound"
        )

    lineage = {
        "store_id": receipt["store_id"],
        "generation_id": request["generation_id"],
        "receipt_id": request["receipt_id"],
        "receipt_sha256": state["receipt_sha256"],
        "capture_id": receipt["capture_id"],
        "vintage_id": receipt["vintage_id"],
        "revision_id": receipt["revision_id"],
        "upstream_sha256": state["upstream_sha256"],
        "upstream_bytes": state["upstream_bytes"],
        "source_owner_sha256": state["source_owner_sha256"],
        "normalizer_sha256": state["normalizer_sha256"],
        "producer_sha256": state["producer_sha256"],
    }
    capability = _seal_capability(body, request, lineage)

    # Before returning: re-run the native owner checks and prove that the
    # lineage, the sealed body and the sealed request still agree.
    _verify_owner_state(capability._request, capability._lineage)
    return capability


def _verify_owner_state(request_bytes: bytes, lineage_bytes: bytes) -> None:
    """Re-run the native owner checks against the sealed request and lineage."""
    request = json.loads(request_bytes)
    lineage = json.loads(lineage_bytes)
    cutoff_dt = _parse_utc(request["knowledge_cutoff"], field="knowledge_cutoff")
    state = _capture_owner_state(
        request["generation_id"], request["receipt_id"], knowledge_cutoff=cutoff_dt
    )
    if (
        state["receipt_sha256"] != lineage["receipt_sha256"]
        or state["upstream_sha256"] != lineage["upstream_sha256"]
        or state["upstream_bytes"] != lineage["upstream_bytes"]
        or state["source_owner_sha256"] != lineage["source_owner_sha256"]
        or state["normalizer_sha256"] != lineage["normalizer_sha256"]
        or state["producer_sha256"] != lineage["producer_sha256"]
    ):
        raise AlfredRevisionEvidenceError(
            "the source owner state changed since the capability was sealed"
        )
    receipt = state["receipt"]
    for field in (
        "store_id",
        "capture_id",
        "vintage_id",
        "revision_id",
    ):
        if receipt[field] != lineage[field]:
            raise AlfredRevisionEvidenceError(
                "the sealed source lineage changed since the capability was sealed"
            )


def disclose_alfred_revision_evidence(
    capability: AlfredRevisionEvidenceCapability,
) -> dict[str, Any]:
    """Disclose the closed source context held by a sealed native capability.

    The returned dictionary is detached from the capability.  The native owner
    checks run immediately before and immediately after the disclosure; a
    changed source, receipt, canonical file or module denies the disclosure
    instead of refreshing or repinning anything.
    """
    if type(capability) is not AlfredRevisionEvidenceCapability:
        raise AlfredRevisionEvidenceError(
            "an exact native ALFRED revision evidence capability is required"
        )
    if not capability._seal_matches():
        raise AlfredRevisionEvidenceError(
            "the capability seal does not bind the sealed body and request"
        )
    snapshot = (capability._body, capability._body_sha256, capability._request,
                capability._lineage, capability._binding_digest, capability._seal)
    body_bytes, _, request_bytes, lineage_bytes, _, _ = snapshot
    _verify_owner_state(request_bytes, lineage_bytes)
    disclosed = json.loads(body_bytes)
    _verify_owner_state(request_bytes, lineage_bytes)
    if (not capability._seal_matches() or snapshot != (
            capability._body, capability._body_sha256, capability._request,
            capability._lineage, capability._binding_digest, capability._seal)):
        raise AlfredRevisionEvidenceError("capability changed during disclosure")
    return disclosed
