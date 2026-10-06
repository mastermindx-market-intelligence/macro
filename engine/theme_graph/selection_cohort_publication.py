"""Existing-publisher W3C provenance I/O; no selection or query authority.

§§0/9: controlled source proof is not natural publication/rights/UI/Evaluation
acceptance. The accepted selection_cohort compiler is the only semantic owner.
A supplied callable is an incumbent capture capability, not an authenticated
receipt constructed from strings. Current natural call sites have NO such
capability and refuse archival. Family display/internal-compute classes do not
supply mixed-vendor capture permission. No public payload is emitted here.
"""
from __future__ import annotations

import copy
import datetime as dt
import gzip
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import zlib
from typing import Callable, Mapping

log = logging.getLogger(__name__)

import jsonschema
from engine.theme_graph.selection_cohort import (
    FLAGS, compose_selection_cohort, content_sha256, validate_selection_cohort,
)

SCHEMA = "mastermind.selection_cohort_source.v1"
POLICY = "owner-current-context-at-finalization/v1"
REASONS = ("conviction", "entry_signal", "risk_sizing")
MARKETS = {"us_today": "US_COMPLETE_NATIVE_FEATURED/v1",
           "cn_featured": "CN_COMPLETE_SERVED_WIDE_BUY/v1"}
ROOT = Path(__file__).resolve().parents[2]
# These are internal output path identities, not inputs opened at import time.
SOURCES = "theme_graph/selection_cohort_sources"  # ci-trigger-closure: data — internal output family identity
RECEIPTS = "theme_graph/selection_cohort_receipts"  # ci-trigger-closure: data — internal output family identity


class PublicationRefusal(ValueError):
    """A concrete publication/binding failure; preserve the existing board."""


def default_capture_capability():
    try:
        from engine.theme_graph.rights_use import capture_capability
        return capture_capability()
    except ImportError:
        return None


def _log_capture_refusal(authorize_capture):
    verdict = getattr(authorize_capture, "last_verdict", None)
    if isinstance(verdict, dict) and verdict.get("reason_codes"):
        log.info("W3C capture refused: %s", verdict["reason_codes"])


def _time(value):
    if not isinstance(value, str) or "T" not in value:
        raise PublicationRefusal("IMPRECISE_OWNER_CLOCK")
    try:
        value = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PublicationRefusal("MALFORMED_OWNER_CLOCK") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise PublicationRefusal("NAIVE_OWNER_CLOCK")
    return value.astimezone(dt.timezone.utc)


def _json(raw):
    def refuse(value):
        raise PublicationRefusal("NONFINITE_SOURCE")
    try:
        value = json.loads(raw, parse_constant=refuse)
        content_sha256(value)
    except (UnicodeError, TypeError, ValueError) as exc:
        raise PublicationRefusal("INVALID_SOURCE_BYTES") from exc
    if not isinstance(value, dict):
        raise PublicationRefusal("SOURCE_NOT_OBJECT")
    return value


def _authorize(capability, request):
    # Closed phases belong to the same injected incumbent capability. A pre-read
    # grant needs the owner's own digest/generation knowledge; this request does
    # not infer source-family permission. No permissive unphased fallback exists.
    if (request.get("phase") not in {"capture_write", "pre_read", "read_use"}
            or request.get("market") not in MARKETS
            or not isinstance(request.get("source_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", request["source_sha256"])
            or not isinstance(request.get("source_ref"), str)
            or not request["source_ref"]
            or request.get("purpose") != "selection_cohort_internal_capture"):
        raise PublicationRefusal("INVALID_CAPTURE_AUTHORIZATION_REQUEST")
    _generation(request.get("generation_id"))
    if capability is None:
        return False
    try:
        allowed = capability(copy.deepcopy(request)) is True
        if not allowed:
            _log_capture_refusal(capability)
        return allowed
    except Exception as exc:  # narrowly isolate an upstream capability failure
        raise PublicationRefusal("CAPTURE_CAPABILITY_UNAVAILABLE") from exc


def _result(reason, *, receipt=None, explanation=None):
    return dict(schema=SCHEMA, status="AVAILABLE" if receipt else "UNAVAILABLE",
                reason_codes=[] if receipt else [reason], receipt=receipt,
                explanation=explanation, **{flag: False for flag in FLAGS})


def source_handoff(*, generation_id, availability, available_at):
    """Library provenance only, deliberately never a FINALIZED selection.

    Caller supplies its real prospective owner generation/clock. Existing fallbacks
    without this handoff remain unavailable; rendering never creates one for them.
    """
    _generation(generation_id)
    _time(available_at)
    if availability not in {"VALID", "PARTIAL", "OUTAGE"}:
        raise PublicationRefusal("INVALID_SOURCE_AVAILABILITY")
    return dict(schema="mastermind.selection_cohort_library_source.v1",
                generation_id=generation_id, availability=availability,
                available_at=available_at)


def _generation(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", value):
        raise PublicationRefusal("MISSING_OR_UNSAFE_OWNER_GENERATION")
    return value


def _rows(document, market):
    buy = document.get("buy")
    if not isinstance(buy, list) or any(not isinstance(row, dict) for row in buy):
        raise PublicationRefusal("MALFORMED_OWNER_COHORT")
    # The native predicate and complete denominator precede every preview split.
    return [row for row in buy if row.get("featured")] if market == "us_today" else buy


def _selection(document, *, market, generation_id, source_ref, source_schema,
               source_sha256, finalized_at):
    rows = [dict(selection_id=f"{market}:{generation_id}:{i}",
                 original_identity={key: copy.deepcopy(row[key]) for key in
                                    ("ticker", "security_id", "issuer_id") if key in row},
                 original_reasons={key: copy.deepcopy(row.get(key)) for key in REASONS},
                 source_row=copy.deepcopy(row))
            for i, row in enumerate(_rows(document, market))]
    source = dict(owner="build_stock_library" if market == "us_today" else "build_china",
                  source_schema=source_schema, source_ref=source_ref,
                  source_sha256=source_sha256, generation_id=generation_id,
                  cohort_scope=MARKETS[market], effective_at=finalized_at,
                  selected_at=finalized_at, known_at=finalized_at,
                  n_selected=len(rows), rows=rows, rows_sha256=content_sha256(rows),
                  ordered_identity_sha256=content_sha256([r["original_identity"] for r in rows]),
                  ordered_reasons_sha256=content_sha256([r["original_reasons"] for r in rows]))
    # Public accepted compiler validates its source input; no copied compiler rules.
    compose_selection_cohort(source, identity_reads={}, membership_reads={}, state_reads={})
    return source


def validate_publication(receipt):
    schema = json.loads((ROOT / "contracts/theme_graph/selection_cohort_source.v1.schema.json").read_text())
    # Outer envelope only; accepted compiler below owns selection semantics.
    jsonschema.Draft202012Validator(schema).validate(receipt)
    source = receipt["source_selection"]
    compose_selection_cohort(source, identity_reads={}, membership_reads={}, state_reads={})
    event = _time(source["selected_at"])
    if (source["effective_at"] != source["selected_at"]
            or source["known_at"] != source["selected_at"]
            or receipt["source_sha256"] != source["source_sha256"]
            or receipt["generation_id"] != source["generation_id"]
            or receipt["source_ref"] != source["source_ref"]
            or receipt["source_ref"] != _source_ref(receipt["source_sha256"])
            or receipt["source_schema"] != source["source_schema"]
            or source["owner"] != ("build_stock_library" if receipt["market"] == "us_today" else "build_china")
            or receipt["reason_projection"] != ("native-owner-reasons/v1" if receipt["market"] == "us_today" else "cn-served-reasons/v1")
            or source["cohort_scope"] != MARKETS[receipt["market"]]):
        raise PublicationRefusal("PUBLICATION_SELECTION_BINDING_MISMATCH")
    for value in receipt["source_clocks"].values():
        if value is None:
            continue
        if "T" in value:
            if _time(value) > event:
                raise PublicationRefusal("FUTURE_SOURCE_CLOCK")
        else:
            try:
                date = dt.date.fromisoformat(value)
            except ValueError as exc:
                raise PublicationRefusal("MALFORMED_SOURCE_CLOCK") from exc
            if date > event.date():
                raise PublicationRefusal("FUTURE_SOURCE_CLOCK")
    for row in receipt["ancestry"]:
        if row["available_at"] is None or _time(row["available_at"]) > event:
            raise PublicationRefusal("UNKNOWABLE_OR_FUTURE_SOURCE_ANCESTRY")
    if receipt["receipt_sha256"] != content_sha256({k:v for k,v in receipt.items() if k != "receipt_sha256"}):
        raise PublicationRefusal("PUBLICATION_DIGEST_MISMATCH")


def _source_ref(digest):
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise PublicationRefusal("INVALID_SOURCE_DIGEST")
    return "data/" + SOURCES + "/" + digest + ".json.gz"


def _paths(data_dir, market, generation_id, digest):
    _generation(generation_id)
    return (Path(data_dir) / SOURCES / (digest + ".json.gz"),
            Path(data_dir) / RECEIPTS / market / (generation_id + ".v1.json"))


def _exclusive(path, data):
    """No clobber: existing exact bytes are reusable; any partial pair refuses."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except FileExistsError:
        if path.read_bytes() != data:
            raise PublicationRefusal("IMMUTABLE_CONTENT_COLLISION")


def publish_finalized_cohort(raw_bytes, *, market, generation_id, source_ref,
                             source_schema, finalized_at, data_dir, ancestry,
                             availability="VALID", source_clocks=None,
                             authorize_capture: Callable | None = None):
    """Attended existing-owner capture; callers supply final serialized bytes.

    The authorizer must be an actual incumbent per-use capability, never a rights
    string/registry class/HTTP status. None is the current natural binding. A
    controlled callable in tests proves mechanics only. Authorization is checked
    BEFORE filesystem inspection or any archive write, including retries/revocation.
    """
    try:
        if market not in MARKETS:
            raise PublicationRefusal("UNSUPPORTED_MARKET")
        _generation(generation_id)
        instant = _time(finalized_at)
        if availability not in {"VALID", "PARTIAL"}:
            raise PublicationRefusal("SOURCE_UNAVAILABLE")
        if not isinstance(raw_bytes, bytes):
            raise PublicationRefusal("SOURCE_BYTES_REQUIRED")
        document = _json(raw_bytes)
        digest = hashlib.sha256(raw_bytes).hexdigest()
        request = dict(market=market, generation_id=generation_id, source_ref=source_ref,
                       source_schema=source_schema, source_sha256=digest,
                       purpose="selection_cohort_internal_capture", phase="capture_write",
                       ancestry=copy.deepcopy(ancestry))
        if not _authorize(authorize_capture, request):
            return _result("CAPTURE_RIGHTS_UNAVAILABLE")
        # Bound ancestry is supplied by the actual owner, not inferred from a path.
        if not ancestry:
            raise PublicationRefusal("MISSING_SOURCE_ANCESTRY")
        for row in ancestry:
            if row.get("available_at") is None or _time(row["available_at"]) > instant:
                raise PublicationRefusal("UNKNOWABLE_OR_FUTURE_SOURCE_ANCESTRY")
        sp, rp = _paths(data_dir, market, generation_id, digest)
        # Same-generation retries retain FIRST event/cutoffs. A new render is no event.
        if rp.exists():
            # Retry uses the same strict pair/request/source-projection reader,
            # including pre-read and current-use grants. An echoed/rehashed receipt
            # is not a request binding; preserve its first valid event only.
            bound = read_finalized_cohort(raw_bytes, market=market,
                generation_id=generation_id, data_dir=data_dir,
                authorize_capture=authorize_capture)
            if bound["status"] != "AVAILABLE":
                return bound
            prior = bound["receipt"]
            requested = dict(source_schema=source_schema, source_origin_ref=source_ref,
                ancestry=ancestry, source_clocks=source_clocks or {},
                source_availability=availability)
            if content_sha256({k: prior[k] for k in requested}) != content_sha256(requested):
                raise PublicationRefusal("OWNER_GENERATION_COLLISION")
            return bound
        if sp.exists():
            # No sealed receipt means the original finalization event is unknown.
            # Even exact durable orphan bytes cannot acquire a later retry cutoff.
            # This source-only scope adds no pending-event persistence surface.
            raise PublicationRefusal("UNSEALED_FINALIZATION_EVENT")
        relative = _source_ref(digest)
        selection = _selection(document, market=market, generation_id=generation_id,
                               source_ref=relative, source_schema=source_schema,
                               source_sha256=digest, finalized_at=finalized_at)
        receipt = dict(schema=SCHEMA, status="FINALIZED", market=market,
                       generation_id=generation_id, policy=POLICY,
                       reason_projection="native-owner-reasons/v1" if market == "us_today" else "cn-served-reasons/v1",
                       source_schema=source_schema, source_ref=relative,
                       source_origin_ref=source_ref, source_sha256=digest,
                       source_availability=availability, source_clocks=copy.deepcopy(source_clocks or {}),
                       ancestry=copy.deepcopy(ancestry), source_selection=selection,
                       capture_use="selection_cohort_internal_capture", public_display_allowed=False,
                       **{flag: False for flag in FLAGS})
        receipt["receipt_sha256"] = content_sha256(receipt)
        validate_publication(receipt)
        _exclusive(sp, gzip.compress(raw_bytes, mtime=0))
        _exclusive(rp, (json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode())
        # Readback of both durable members, not success based on a write syscall.
        return read_finalized_cohort(raw_bytes, market=market, generation_id=generation_id,
                                     data_dir=data_dir, authorize_capture=authorize_capture)
    except (OSError, ValueError, TypeError, KeyError, jsonschema.ValidationError, EOFError, zlib.error) as exc:
        return _result(str(exc) if isinstance(exc, PublicationRefusal) else "PUBLICATION_IO_OR_VALIDATION_FAILURE")


def read_finalized_cohort(raw_bytes, *, market, generation_id, data_dir,
                          authorize_capture=None, qualified_reads=None,
                          previous_explanation=None, consequence_reference=None):
    """Exact immutable pair; no current-only/PIT/rights/state fallback algorithm."""
    try:
        if market not in MARKETS:
            raise PublicationRefusal("UNSUPPORTED_MARKET")
        digest = hashlib.sha256(raw_bytes).hexdigest()
        sp, rp = _paths(data_dir, market, generation_id, digest)
        # Only actual request identifiers exist at this point. The incumbent
        # capability must already know this owner digest/generation. Its bounded
        # pre_read decision precedes any protected receipt rows read or parsing.
        pre_read = dict(market=market, generation_id=generation_id,
                        source_ref=_source_ref(digest), source_sha256=digest,
                        purpose="selection_cohort_internal_capture", phase="pre_read")
        if not _authorize(authorize_capture, pre_read):
            return _result("CAPTURE_RIGHTS_UNAVAILABLE")
        receipt = _json(rp.read_bytes())
        validate_publication(receipt)
        request = dict(market=market, generation_id=generation_id,
                       source_ref=receipt["source_origin_ref"], source_schema=receipt["source_schema"],
                       source_sha256=digest, purpose="selection_cohort_internal_capture",
                       phase="read_use", ancestry=copy.deepcopy(receipt["ancestry"]))
        if not _authorize(authorize_capture, request):
            return _result("CAPTURE_RIGHTS_UNAVAILABLE")
        if (receipt["market"] != market or receipt["generation_id"] != generation_id
                or receipt["source_sha256"] != digest or gzip.decompress(sp.read_bytes()) != raw_bytes):
            raise PublicationRefusal("MIXED_SOURCE_GENERATION")
        document = _json(raw_bytes)
        expected = _selection(document, market=market, generation_id=generation_id,
                              source_ref=receipt["source_ref"], source_schema=receipt["source_schema"],
                              source_sha256=digest, finalized_at=receipt["source_selection"]["selected_at"])
        if content_sha256(expected) != content_sha256(receipt["source_selection"]):
            raise PublicationRefusal("SOURCE_PROJECTION_MISMATCH")
        explanation = None
        if qualified_reads is not None:
            reads = qualified_reads(copy.deepcopy(expected))
            explanation = compose_selection_cohort(expected, **reads,
                previous_explanation=previous_explanation, consequence_reference=consequence_reference)
            validate_selection_cohort(explanation)
        return _result(None, receipt=receipt, explanation=explanation)
    except (OSError, ValueError, TypeError, KeyError, jsonschema.ValidationError, EOFError, zlib.error) as exc:
        return _result(str(exc) if isinstance(exc, PublicationRefusal) else "PUBLICATION_IO_OR_VALIDATION_FAILURE")


def consume_us_source(raw_bytes, *, data_dir, authorize_capture=None, qualified_reads=None):
    """Read before display attaches; never manufacture a receipt at rendering."""
    try:
        source = _json(raw_bytes)
        generation = source.get("emit", {}).get("pair_id")
        return read_finalized_cohort(raw_bytes, market="us_today", generation_id=generation,
                                    data_dir=data_dir, authorize_capture=authorize_capture,
                                    qualified_reads=qualified_reads)
    except (ValueError, TypeError, AttributeError):
        return _result("INVALID_OWNER_SOURCE")


def publish_us_source(raw_bytes, *, data_dir, finalized_at, authorize_capture=None):
    """The publisher calls this AFTER its incumbent serialize-once boundary."""
    try:
        source = _json(raw_bytes)
        generation = source.get("emit", {}).get("pair_id")
        _generation(generation)
        handoff = source.get("w3c_source")
        if (not isinstance(handoff, dict) or handoff.get("generation_id") != generation
                or handoff.get("schema") != "mastermind.selection_cohort_library_source.v1"):
            return _result("MISSING_OR_MIXED_LIBRARY_HANDOFF")
        return publish_finalized_cohort(raw_bytes, market="us_today", generation_id=generation,
            source_ref="site/factordata/us_standouts.json",  # ci-trigger-closure: data — supplied publisher source identity; not opened here
            source_schema="us-final-serialized-Featured/v1", finalized_at=finalized_at,
            data_dir=data_dir, availability=handoff["availability"],
            source_clocks={"as_of": source.get("as_of"), "pair_emitted_at": source.get("emit", {}).get("at_utc")},
            ancestry=[dict(owner="build_stock_library", source_family="mixed_owner_library",
                           source_ref="site/factordata/us_standouts.json",  # ci-trigger-closure: data — supplied source identity; not opened here
                           sha256=hashlib.sha256(raw_bytes).hexdigest(), generation_id=generation,
                           available_at=handoff["available_at"])], authorize_capture=authorize_capture)
    except (ValueError, TypeError, AttributeError):
        return _result("INVALID_OWNER_SOURCE")


def publish_cn_source(served_bytes, *, library_bytes, data_dir, finalized_at,
                      reason_ancestry, authorize_capture=None, fallback=False):
    """ONE finalizer AFTER served reasons/fallback/board_since, never in library.

    Library handoff is provenance/validity. Persisted fallback may only READ its
    already finalized exact served generation, never mint an event on rendering.
    Unknown per-stock generation/availability is not invented; qualification
    refuses until the actual owner provides it.
    """
    try:
        library, served = _json(library_bytes), _json(served_bytes)
        handoff = library.get("w3c_source")
        if not isinstance(handoff, dict) or handoff != served.get("w3c_source"):
            return _result("MISSING_OR_MIXED_LIBRARY_HANDOFF")
        generation = handoff["generation_id"]
        _generation(generation)
        if handoff["schema"] != "mastermind.selection_cohort_library_source.v1":
            return _result("INVALID_LIBRARY_HANDOFF")
        if handoff["availability"] not in {"VALID", "PARTIAL"}:
            return _result("SOURCE_UNAVAILABLE")
        # Declared source order/denominator must survive reason enrichment. No
        # ticker/security normalization or re-selection occurs in this wrapper.
        identities = lambda doc: [{k: copy.deepcopy(row[k]) for k in
            ("ticker", "security_id", "issuer_id") if k in row}
            for row in _rows(doc, "cn_featured")]
        if content_sha256(identities(library)) != content_sha256(identities(served)):
            return _result("SERVED_COHORT_ORDER_MISMATCH")
        if fallback:
            result = read_finalized_cohort(served_bytes, market="cn_featured", generation_id=generation,
                data_dir=data_dir, authorize_capture=authorize_capture)
            if result["receipt"] is not None and result["receipt"]["ancestry"][0]["sha256"] != hashlib.sha256(library_bytes).hexdigest():
                return _result("MIXED_LIBRARY_ANCESTRY")
            return result
        # Every replaced original reason is bound to its actual owner row receipt.
        # A digest checks a supplied projection; it is NOT proof of source authority.
        # Current natural caller has no such per-stock receipt and cannot fill it in.
        changed = {i for i, (old, new) in enumerate(zip(_rows(library, "cn_featured"), _rows(served, "cn_featured")))
                   if content_sha256({k: old.get(k) for k in REASONS})
                   != content_sha256({k: new.get(k) for k in REASONS})}
        indices = [row.get("row_index") for row in reason_ancestry if isinstance(row, dict)]
        if (len(indices) != len(reason_ancestry) or len(set(indices)) != len(indices)
                or set(indices) != changed):
            return _result("REQUIRED_REASON_SOURCE_ANCESTRY_UNAVAILABLE")
        for row in reason_ancestry:
            original = {k: _rows(served, "cn_featured")[row["row_index"]].get(k) for k in REASONS}
            if row.get("reason_projection_sha256") != content_sha256(original):
                return _result("REASON_SOURCE_PROJECTION_MISMATCH")
        ancestry = [dict(owner="build_china_library", source_family="mixed_owner_library",
                         source_ref="site/factordata/china_standouts.json",  # ci-trigger-closure: data — supplied source identity; not opened here
                         sha256=hashlib.sha256(library_bytes).hexdigest(), generation_id=generation,
                         available_at=handoff["available_at"])] + copy.deepcopy(reason_ancestry)
        return publish_finalized_cohort(served_bytes, market="cn_featured", generation_id=generation,
            source_ref="build_china:served-wide-buy", source_schema="cn-served-wide-buy/v1",
            finalized_at=finalized_at, data_dir=data_dir, ancestry=ancestry,
            availability=handoff["availability"],
            source_clocks={"library_available_at": handoff["available_at"], "as_of": library.get("as_of")},
            authorize_capture=authorize_capture)
    except (ValueError, TypeError, KeyError, AttributeError):
        return _result("INVALID_OWNER_SOURCE")
