"""Private candidate inspection through one native pinned retained SEC document.

This API consumes an already supplied native authority; it creates no store,
credentials, latest pointer, snapshot, filing/earnings event, or publication.
Native custody replay is relative to that supplied reader. It does not prove
the reader's production ownership, SEC authorship, economic truth, rights,
canonical issuer identity, historical served state, or Graph1 admission.

The candidate document must use the exact native document_id and archive_url,
version "sha256:<raw body digest>", and published_date=null. Native filed_on and
report_date remain separate DATE metadata, never inferred publication instants.
Manual annotations may contain source text; no output mode certifies public-safe
content. Source witnesses are suppressed on every non-inspectable outcome.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

from engine.company_intelligence.relationship_candidates import MAX_SOURCE_BYTES, inspect_candidate
from engine.fundamental_forensics.filing_attestation import (
    FilingAttestationError, PinnedSourceAuthority, gzip_stored_byte_ceiling,
)
from engine.fundamental_forensics.sec_document_spine import (
    FilingManifestError, HARD_MAX_FILING_MANIFEST_BYTES, manifest_from_json_bytes,
)
from engine.fundamental_forensics.source_sync import SourceSyncError
from engine.research_vault.r2_store import BoundedReadError
from lib.dataos.temporal import TemporalError, utc


class PinnedCandidateError(ValueError):
    """Stable adapter refusal without reflected source or host details."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PinnedCandidateError(code)


def _base() -> dict[str, Any]:
    return {
        "schema": "company_intelligence.pinned_relationship_inspection/v1",
        "inspection_status": "REFUSED",
        "refusal": None,
        "candidate_inspection": None,
        "native_source_binding": None,
        "admission": "NOT_ADMITTED",
        "graph1_projection": None,
        "authority": {key: False for key in ("rank", "gate", "size", "trade", "prediction")},
        "content_boundary": {
            "annotations": "caller_supplied_may_contain_source_text",
            "quote_free_payload": "NOT_CERTIFIED",
            "public_safe_payload": "NOT_CERTIFIED",
            "public_export": "NOT_AUTHORIZED",
        },
        "gaps": {
            "reader_owner": ["supplied_reader_production_owner_not_independently_authenticated"],
            "source_authorship": ["sec_authorship_not_cryptographically_authenticated"],
            "native_adoption": ["relationship_dataset_and_owner_adoption_required"],
            "identity": ["canonical_as_of_issuer_identity_not_established"],
            "time": ["source_capture_is_not_registered_known_at_or_historical_served_state"],
            "rights": ["purpose_specific_rights_not_established", "downstream_emission_purposes_unresolved"],
        },
        "limitations": [
            "native_source_binding_is_relative_to_supplied_native_reader",
            "native_custody_replay_is_not_economic_truth_or_rights_admission",
            "manual_annotations_remain_supplied_and_unauthenticated",
            "native_filing_lineage_is_not_candidate_correction_or_termination",
        ],
    }


def inspect_pinned_candidate(
    candidate: Any, *, authority: Any, snapshot_id: str, manifest_key: str,
    document_id: str, as_of: Any = None, registry: Any = None,
    maximum_bytes: int = MAX_SOURCE_BYTES, include_support_text: bool = False,
) -> dict[str, Any]:
    """Inspect one exact manifest document using the actual native pinned reader.

    Supply an exact PinnedSourceAuthority backed by the existing owner's strict
    store and explicit source selectors. The authority is reconstructed over the
    same store to prevent caller-edited session snapshot mappings from becoming
    authority. This does not independently authenticate that supplied store.

    No discovery, full filing fan-out, acquisition, mutation, or local clock law
    is introduced. Source capture causality uses native utc; requested historical
    eligibility still belongs to the existing candidate inspector/native DataOS
    owners. Refused/excluded historical requests expose no current source witness.
    """
    result = _base()
    try:
        _require(type(include_support_text) is bool, "INPUT_INVALID")
        _require(type(maximum_bytes) is int and 0 < maximum_bytes <= MAX_SOURCE_BYTES,
                 "SOURCE_LIMIT_INVALID")
        _require(type(snapshot_id) is str and re.fullmatch(r"ffsecsrc_[0-9a-f]{64}", snapshot_id) is not None,
                 "SNAPSHOT_SELECTOR_INVALID")
        _require(type(manifest_key) is str and 0 < len(manifest_key) <= 700,
                 "MANIFEST_SELECTOR_INVALID")
        _require(type(document_id) is str and 0 < len(document_id) <= 512,
                 "DOCUMENT_SELECTOR_INVALID")
        if as_of is not None:
            utc(as_of)
        _require(type(authority) is PinnedSourceAuthority, "EXACT_NATIVE_AUTHORITY_REQUIRED")
        _require(authority.snapshot_id == snapshot_id, "SNAPSHOT_SELECTOR_MISMATCH")
        # Mirror the native filing-materializer boundary: never trust a mutable
        # nominal authority's cached snapshot mapping or overridden read methods.
        native = PinnedSourceAuthority(store=authority._store, snapshot_id=snapshot_id)
        manifest_read = native.read_file(
            kind="archive", relative_path=manifest_key,
            maximum_bytes=HARD_MAX_FILING_MANIFEST_BYTES,
        )
        manifest = manifest_from_json_bytes(manifest_read.content)
        from collectors.sec_document_spine import manifest_storage_key

        _require(manifest_storage_key(manifest) == manifest_key, "MANIFEST_SELECTOR_MISMATCH")
        selected = [row for row in manifest["documents"] if row["document_id"] == document_id]
        _require(len(selected) == 1, "DOCUMENT_NOT_UNIQUELY_SELECTED")
        document = selected[0]
        _require(document["availability"] == "stored", "DOCUMENT_NOT_STORED")
        retrieval = document["retrieval"]
        _require(type(retrieval) is dict, "SOURCE_RECEIPT_REQUIRED")
        raw_length = retrieval["byte_length"]
        _require(type(raw_length) is int and 0 < raw_length <= maximum_bytes,
                 "SOURCE_RAW_SIZE_OUTSIDE_LIMIT")
        snapshot_clock = utc(native.snapshot_at)
        _require(utc(manifest["clocks"]["recorded_at"]) <= snapshot_clock,
                 "MANIFEST_RECORDED_AFTER_SNAPSHOT")
        _require(utc(retrieval["retrieved_at"]) <= snapshot_clock,
                 "DOCUMENT_RETRIEVED_AFTER_SNAPSHOT")
        read = native.read_archive_document(
            storage_key=document["storage_key"], expected_receipt=retrieval,
            maximum_bytes=maximum_bytes,
            maximum_stored_bytes=gzip_stored_byte_ceiling(raw_length),
        )
        _require(read.receipt_sidecar_verified is True, "SOURCE_SIDECAR_NOT_VERIFIED")
        digest = sha256(read.content).hexdigest()
        _require(len(read.content) == raw_length and digest == document["content_sha256"],
                 "SOURCE_RAW_DIGEST_MISMATCH")
        source = read.content.decode("utf-8")
        # UTF-8 is decoded strictly, with no newline or markup transformation.
        _require(source.encode("utf-8") == read.content, "SOURCE_UTF8_ROUNDTRIP_FAILED")
        supplied = candidate.get("document") if type(candidate) is dict else None
        _require(type(supplied) is dict, "CANDIDATE_DOCUMENT_INVALID")
        expected = {
            "document_id": document_id, "version": "sha256:" + digest,
            "source_ref": document["archive_url"], "published_date": None,
        }
        _require(supplied == expected, "CANDIDATE_SOURCE_METADATA_MISMATCH")
        inspected = inspect_candidate(
            candidate, source=source, as_of=as_of, registry=registry,
            include_support_text=include_support_text,
        )
        result["candidate_inspection"] = inspected
        result["inspection_status"] = inspected["inspection_status"]
        result["refusal"] = inspected["refusal"]
        if inspected["inspection_status"] != "INSPECTABLE":
            return result
        # Keep this separate from the inspector's unauthenticated caller metadata
        # and manual semantics. No generated ffatt_ or identity/rights seal.
        result["native_source_binding"] = {
            "status": "NATIVE_PINNED_SOURCE_REPLAYED",
            "source_custody": "verified_relative_to_supplied_native_reader",
            "reader_owner_authenticity": "not_independently_established",
            "sec_authorship": "not_cryptographically_authenticated",
            "snapshot_id": native.snapshot_id,
            "snapshot_at": native.snapshot_at,
            "manifest_id": manifest["manifest_id"],
            "manifest_key": manifest_key,
            "source_local_issuer": dict(manifest["issuer"]),
            "source_local_filing": dict(manifest["filing"]),
            "source_local_clocks": dict(manifest["clocks"]),
            "source_local_lineage": dict(manifest["lineage"]),
            "document_id": document_id,
            "document_name": document["document_name"],
            "archive_url": document["archive_url"],
            "document_version": "sha256:" + digest,
            "raw_sha256": digest,
            "raw_byte_length": len(read.content),
            "retrieval_receipt": dict(retrieval),
            "manifest_witness": manifest_read.witness.to_dict(),
            "receipt_sidecar_witness": read.receipt_read.witness.to_dict(),
            "gzip_object_witness": read.object_read.witness.to_dict(),
            "receipt_sidecar_verified": True,
            "rights": "not_established",
            "canonical_identity": "not_resolved",
            "historical_served_state": "not_established",
        }
        return result
    except PinnedCandidateError as exc:
        code = exc.code
    except UnicodeError:
        code = "SOURCE_UTF8_INVALID"
    except TemporalError:
        code = "NATIVE_TEMPORAL_REFUSAL"
    except PermissionError:
        code = "SOURCE_ACCESS_DENIED"
    except BoundedReadError:
        code = "SOURCE_BOUNDED_READ_FAILED"
    except FilingManifestError:
        code = "NATIVE_MANIFEST_INVALID"
    except FilingAttestationError:
        code = "NATIVE_ARCHIVE_REPLAY_FAILED"
    except SourceSyncError as exc:
        # Only the native owner's exact absence branches mean absence. Other
        # integrity/protocol failures are never collapsed into "not found".
        message = str(exc)
        code = (
            "PINNED_SOURCE_MISSING"
            if message.startswith(("private source-store object not found:",
                                   "pinned source snapshot does not contain "))
            else "PINNED_SOURCE_CONTRACT_INVALID"
        )
    except (OSError, RuntimeError):
        code = "SOURCE_READER_UNAVAILABLE"
    except ValueError as exc:
        # LocalStore's native positional-cap read exposes overflow as ValueError,
        # unlike typed remote bounded-read errors. Preserve this owner branch as
        # a read failure, never absence; do not echo its path or error details.
        code = ("SOURCE_BOUNDED_READ_FAILED"
                if str(exc).startswith("local object exceeds bounded read limit (")
                else "INPUT_OR_NATIVE_CONTRACT_INVALID")
    except (TypeError, KeyError, AttributeError, RecursionError):
        code = "INPUT_OR_NATIVE_CONTRACT_INVALID"
    except Exception:
        # Native strict readers propagate SDK-specific errors as well. Unknown
        # failures are bounded and explicit; none can become a missing result.
        code = "SOURCE_READER_FAILED"
    result["refusal"] = {"code": code}
    return result
