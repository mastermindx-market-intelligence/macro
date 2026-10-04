"""Compare accepted Company Intelligence guidance; never extract or originate it.

Pure, known-now descriptive context. Callers supply owner-native workspace
bodies obtained through the existing verified readers. Association checks here
do not certify the upstream extractor or recreate its byte-replay authority.
No source fetch, storage, ambient clock, model, or trade input. The bounded
release-history selector consumes the existing owner reader without replacing it.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import (Context, Decimal, DivisionByZero, InvalidOperation,
                     Overflow, ROUND_HALF_EVEN, localcontext)
import re
from typing import Any

from .documents import SourceSpan, _sha as _source_sha
from .identity import ListingAlias
from .events import parse_canonical_event_id

AUTHORITY = "context_only"
SCHEMA = "news_guidance_context.v1"
_FLAGS = {"may_rank": False, "may_size": False, "may_gate": False, "prophet_authority": False}
_PUBLIC_RIGHTS = frozenset({"rp_public_primary_v1", "public_primary"})
_HORIZON = re.compile(r"^FY(?:19|20|21)\d{2}(?: Q[1-4])?$")
_GENERATION = re.compile(r"^[0-9a-f]{24,64}$")
_STATUSES = frozenset({"introduced", "reiterated", "raised", "cut", "revised"})


class _Refusal(ValueError):
    pass


def _clock(value: Any) -> datetime:
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise _Refusal("clock_invalid") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise _Refusal("clock_invalid")
    return result.astimezone(timezone.utc)


def _workspace(value: Any, now: datetime, ticker: str | None, expected_security_id: str | None = None) -> tuple[Mapping, str, datetime]:
    if not isinstance(value, Mapping):
        raise _Refusal("workspace_invalid")
    if (value.get("schema") != "event_workspace.v1" or value.get("authority") != AUTHORITY
            or value.get("prophet_flags") != _FLAGS
            or any(value["prophet_flags"].get(k) is not False for k in _FLAGS)
            or not _GENERATION.fullmatch(str(value.get("generation_id") or ""))
            or not isinstance(value.get("guidance"), list)
            or not isinstance(value.get("sources"), list)):
        raise _Refusal("workspace_invalid")
    try:
        issuer, _, _ = parse_canonical_event_id(value.get("event_id"))
        block = value["issuer"]
        if not isinstance(block, Mapping) or block.get("company_id") != issuer:
            raise ValueError("issuer does not match event")
    except (ValueError, KeyError, TypeError) as exc:
        raise _Refusal("workspace_invalid") from exc
    if ticker is not None:
        if not isinstance(expected_security_id, str) or not expected_security_id:
            raise _Refusal("listing_binding_missing")
        listings = block.get("listings")
        matches = []
        for row in listings if isinstance(listings, list) else []:
            if not isinstance(row, Mapping) or row.get("ticker") != ticker:
                continue
            try:
                alias = ListingAlias(**{k: row[k] for k in (
                    "ticker", "mic", "share_class", "trading_currency",
                    "valid_from", "valid_to")})
            except (ValueError, KeyError, TypeError):
                continue
            if (alias.security_id == expected_security_id and alias.covers(now.date())
                    and row.get("security_id", alias.security_id) == alias.security_id):
                matches.append(alias)
        if len(matches) != 1:
            raise _Refusal("issuer_listing_mismatch")
    lifecycle = value.get("lifecycle")
    if not isinstance(lifecycle, Mapping):
        raise _Refusal("clock_invalid")
    if (not isinstance(lifecycle.get("state"), str) or lifecycle.get("state") not in {
            "completed_partial", "complete", "corrected", "derived_ready", "distributed"}):
        raise _Refusal("event_state_ineligible")
    observed = _clock(lifecycle.get("observed_at"))
    available = _clock(lifecycle.get("source_available_at"))
    if available > observed or observed > now:
        raise _Refusal("clock_invalid")
    return value, issuer, observed


def _key(item: Any) -> tuple[str, str] | None:
    if not isinstance(item, Mapping):
        return None
    metric, horizon = item.get("metric"), item.get("horizon")
    if (not isinstance(metric, str) or not metric or len(metric) > 120
            or not isinstance(horizon, str) or not _HORIZON.fullmatch(horizon)):
        return None
    return metric, horizon


def _number(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise _Refusal("guidance_invalid")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise _Refusal("guidance_invalid") from exc
    # Bound serialization and exact arithmetic, not a market materiality rule.
    # Unsupported precision is absence; never silently round source values.
    if (not result.is_finite() or result.as_tuple().exponent < -30
            or len(result.as_tuple().digits) > 64 or result.copy_abs() > Decimal("1e30")):
        raise _Refusal("guidance_invalid")
    return result


def _guidance_clocks(source: Mapping, workspace: Mapping, now: datetime) -> tuple[datetime, datetime]:
    """Use the cited document's existing clock; never borrow a sibling's time.

    Legacy lifecycle clocks belong to the issuer release and remain usable for
    release-bound guidance only. Other source clocks are validated by their
    existing owner. No timestamps, source identities or history are invented.
    """
    kind = source.get("kind")
    if not isinstance(kind, str) or kind not in {"issuer_release", "transcript"}:
        raise _Refusal("guidance_source_kind_unsupported")
    raw = source.get("source_clock")
    if raw is None:
        if kind != "issuer_release":
            raise _Refusal("guidance_source_clock_missing")
        releases = [s for s in workspace["sources"] if isinstance(s, Mapping)
                    and s.get("kind") == "issuer_release"]
        if len(releases) != 1:
            raise _Refusal("guidance_source_clock_ambiguous")
        return (_clock(workspace["lifecycle"]["source_available_at"]),
                _clock(workspace["lifecycle"]["observed_at"]))
    from .qa_exchange import validate_source_clock
    try:
        clock = validate_source_clock(raw, document_id=source["document_id"],
                                      source_sha256=source["source_sha256"])
    except (ValueError, TypeError, KeyError) as exc:
        raise _Refusal("guidance_source_clock_invalid") from exc
    if clock["clock_state"] != "known":
        raise _Refusal("guidance_source_clock_unknown")
    try:
        available = _clock(clock["source_available_at"])
        observed = _clock(clock["system_recorded_at"])
    except _Refusal as exc:
        raise _Refusal("guidance_source_clock_invalid") from exc
    if available > observed or observed > now:
        raise _Refusal("guidance_source_clock_invalid")
    return available, observed


def _guidance(item: Mapping, workspace: Mapping, now: datetime) -> tuple[Decimal, Decimal, dict]:
    if item.get("status") == "withdrawn":
        raise _Refusal("guidance_withdrawn")
    if (item.get("schema") != "guidance_item.v1" or not isinstance(item.get("status"), str)
            or item.get("status") not in _STATUSES
            or item.get("typed_absence") is not None or _key(item) is None
            or not isinstance(item.get("unit"), str) or not item.get("unit")):
        raise _Refusal("guidance_invalid")
    low, high = _number(item.get("low")), _number(item.get("high"))
    if low > high or (item["unit"] == "vehicles" and
                     (low < 0 or low != low.to_integral_value() or high != high.to_integral_value())):
        raise _Refusal("guidance_invalid")
    raw = item.get("source_span")
    if not isinstance(raw, Mapping) or raw.get("schema") != "source_span.v1" or raw.get("authority") != AUTHORITY:
        raise _Refusal("guidance_evidence_invalid")
    # Two missing identifiers must not count as an evidence association.
    # These are shape checks, not a replacement source identity or byte replay.
    if (any(not isinstance(raw.get(k), str) or not raw[k].strip() or len(raw[k]) > 128
            for k in ("document_id", "span_id"))
            or type(raw.get("document_version")) is not int or raw["document_version"] < 1):
        raise _Refusal("guidance_evidence_invalid")
    try:
        span = SourceSpan(**{key: raw.get(key) for key in (
            "span_id", "document_id", "document_version", "locator", "receipt_state",
            "text_sha256", "display_excerpt", "rights_profile", "receipt", "unreplayable_reason")})
    except (ValueError, TypeError, KeyError) as exc:
        raise _Refusal("guidance_evidence_invalid") from exc
    if (not span.is_replayable or not isinstance(span.rights_profile, str)
            or span.rights_profile not in _PUBLIC_RIGHTS):
        raise _Refusal("guidance_evidence_invalid")
    try:
        _source_sha((span.receipt or {}).get("source_sha256"), field_name="source_sha256")
    except (ValueError, TypeError) as exc:
        raise _Refusal("guidance_evidence_invalid") from exc
    sources = [s for s in workspace["sources"] if isinstance(s, Mapping)
               and s.get("document_id") == span.document_id]
    if (len(sources) != 1 or sources[0].get("receipt_state") != "byte_replayed"
            or sources[0].get("source_sha256") != (span.receipt or {}).get("source_sha256")):
        raise _Refusal("guidance_evidence_invalid")
    available, observed = _guidance_clocks(sources[0], workspace, now)
    evidence = {"event_id": workspace["event_id"], "generation_id": workspace["generation_id"],
                "document_id": span.document_id, "span_id": span.span_id,
                "receipt_state": span.receipt_state,
                "observed_at": observed.isoformat(),
                "source_available_at": available.isoformat()}
    return low, high, evidence


def _fmt(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def _empty_context() -> dict[str, Any]:
    return {"schema": SCHEMA, "authority": AUTHORITY,
        "is_context_only": True, "display_only": True, "prophet_flags": dict(_FLAGS),
        "temporal_basis": "known_now", "as_of": None, "available": False,
        "comparisons": [], "reasons": [], "consensus": None}


def compare_guidance_workspaces(current: Any, prior: Any, *, as_of: datetime,
                                ticker: str | None = None,
                                expected_security_id: str | None = None) -> dict[str, Any]:
    """Descriptive paired comparison; no baseline selection or consensus inference.

    ``current`` and ``prior`` are explicit accepted-owner bodies, not arbitrary
    news text. Missing/unsupported evidence has named reasons. Financial amounts
    require explicit equal currency/accounting basis; v1 physical counts/rates
    can compare directly, while any supplied basis/scope must still agree.
    """
    result = _empty_context()
    reasons: list[str] = result["reasons"]
    try:
        now = _clock(as_of); result["as_of"] = now.isoformat()
        c, issuer, _ = _workspace(current, now, ticker, expected_security_id)
        if prior is None:
            raise _Refusal("prior_not_supplied")
        p, p_issuer, _ = _workspace(prior, now, None)
        if issuer != p_issuer:
            raise _Refusal("issuer_mismatch")
        current_counts = Counter(_key(g) for g in c["guidance"])
        if not c["guidance"]:
            raise _Refusal("guidance_absent")
        for item in c["guidance"]:
            try:
                key = _key(item)
                if key is None:
                    raise _Refusal("guidance_invalid")
                if current_counts[key] != 1:
                    raise _Refusal("current_ambiguous")
                low, high, c_ev = _guidance(item, c, now)
                matches = [g for g in p["guidance"] if _key(g) == key]
                if not matches:
                    raise _Refusal("prior_comparable_missing")
                if len(matches) != 1:
                    raise _Refusal("prior_ambiguous")
                previous = matches[0]
                p_low, p_high, p_ev = _guidance(previous, p, now)
                # Order the documents supporting THIS metric, not sibling releases.
                if (_clock(p_ev["observed_at"]) >= _clock(c_ev["observed_at"])
                        or _clock(p_ev["source_available_at"]) > _clock(c_ev["source_available_at"])):
                    raise _Refusal("revision_order_invalid")
                if item["unit"] != previous["unit"]:
                    raise _Refusal("measurement_mismatch")
                if any(item.get(k) != previous.get(k) for k in ("basis", "currency", "scope")):
                    raise _Refusal("measurement_mismatch")
                if item["unit"] not in {"vehicles", "percent"} and (
                        not isinstance(item.get("basis"), str)
                        or item.get("basis") not in {"gaap", "adjusted"}
                        or not re.fullmatch(r"[A-Z]{3}", str(item.get("currency") or ""))):
                    raise _Refusal("measurement_basis_missing")
                # Fix precision, rounding, exponent bounds and traps; unrelated
                # Decimal callers must not change the same evidence result.
                with localcontext(Context(prec=96, rounding=ROUND_HALF_EVEN,
                                          Emin=-999999, Emax=999999, capitals=1,
                                          clamp=0, flags=[],
                                          traps=[InvalidOperation, DivisionByZero, Overflow])):
                    midpoint = (low + high) / 2; p_midpoint = (p_low + p_high) / 2
                    delta = midpoint - p_midpoint
                    percentage = None; pct_reason = None
                    if item["unit"] == "percent":
                        pct_reason = "rate_comparison_uses_percentage_points"
                    elif p_midpoint == 0:
                        pct_reason = "zero_prior_midpoint"
                    else:
                        percentage = _fmt((delta / abs(p_midpoint) * 100).quantize(Decimal("0.000001")))
                    direction = "higher" if delta > 0 else "lower" if delta < 0 else (
                        "unchanged" if (low, high) == (p_low, p_high) else "range_changed")
                    result["comparisons"].append({"metric": key[0], "horizon": key[1],
                        "unit": item["unit"], "current_low": _fmt(low), "current_high": _fmt(high),
                        "prior_low": _fmt(p_low), "prior_high": _fmt(p_high),
                        "current_midpoint": _fmt(midpoint), "prior_midpoint": _fmt(p_midpoint),
                        "midpoint_delta": _fmt(delta), "relative_change_pct": percentage,
                        "relative_change_reason": pct_reason,
                        "delta_unit": "percentage_points" if item["unit"] == "percent" else item["unit"],
                        "direction": direction, "interpretation": ("source_correction_difference"
                            if c["lifecycle"].get("state") == "corrected" else "numeric_difference_only"),
                        "evidence": [{"role": "current", **c_ev}, {"role": "prior", **p_ev}]})
            except _Refusal as exc:
                reasons.append(str(exc))
    except _Refusal as exc:
        reasons.append(str(exc))
    result["reasons"] = sorted(set(reasons))
    result["available"] = bool(result["comparisons"])
    return result


def compare_release_guidance_history(revisions: Any, *, event_id: str,
                                    as_of: datetime, ticker: str | None = None,
                                    expected_security_id: str | None = None) -> dict[str, Any]:
    """Compare adjacent releases from the existing verified history reader.

    Input is the complete, oldest-first output for ONE event from the existing
    Company Intelligence release-revision reader. The reader, not this selector,
    authenticates raw workspace bytes and chain completeness. Receipt checks here
    bind metadata and refuse malformed transport; a dict is not proof of replay.

    Only the final release and its immediate predecessor may supply a baseline.
    No sorting, back-search, deduplication, transcript-history inference or I/O.
    The 64-revision display bound refuses rather than silently truncating history.
    A later actual-only release never revives an older guidance comparison.
    """
    result = _empty_context()
    try:
        now = _clock(as_of); result["as_of"] = now.isoformat()
        if not isinstance(revisions, list):
            raise _Refusal("release_history_invalid")
        if not revisions:
            raise _Refusal("release_history_empty")
        if len(revisions) > 64:
            raise _Refusal("release_history_bound_exceeded")
        if not isinstance(event_id, str) or not event_id:
            raise _Refusal("release_history_identity_mismatch")
        workspaces: list[Mapping] = []
        generations: set[str] = set()
        previous_clocks = None
        previous_source = None
        for revision in revisions:
            if not isinstance(revision, Mapping):
                raise _Refusal("release_history_invalid")
            ws, _, observed = _workspace(revision.get("workspace"), now, None)
            if ws["event_id"] != event_id:
                raise _Refusal("release_history_identity_mismatch")
            sources = [source for source in ws["sources"] if isinstance(source, Mapping)
                       and source.get("kind") == "issuer_release"]
            if len(sources) != 1:
                raise _Refusal("release_history_guidance_source_mismatch")
            source = sources[0]
            native = {"generation_id": ws["generation_id"],
                      "source_sha256": source.get("source_sha256"),
                      "source_available_at": ws["lifecycle"]["source_available_at"],
                      "observed_at": ws["lifecycle"]["observed_at"],
                      "lifecycle_state": ws["lifecycle"]["state"], "form": source.get("form")}
            if any(key not in revision or revision[key] != value for key, value in native.items()):
                raise _Refusal("release_history_metadata_mismatch")
            try:
                _source_sha(native["source_sha256"], field_name="source_sha256")
            except (ValueError, TypeError) as exc:
                raise _Refusal("release_history_metadata_mismatch") from exc
            if previous_source == native["source_sha256"]:
                raise _Refusal("release_history_duplicate_source")
            previous_source = native["source_sha256"]
            receipt = revision.get("workspace_receipt")
            if (not isinstance(receipt, Mapping) or set(receipt) != {"sha256", "bytes"}
                    or not isinstance(receipt.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"])
                    or type(receipt.get("bytes")) is not int or not 0 < receipt["bytes"] <= 524288):
                raise _Refusal("release_history_receipt_invalid")
            if ws["generation_id"] in generations:
                raise _Refusal("release_history_duplicate_generation")
            generations.add(ws["generation_id"])
            available = _clock(native["source_available_at"])
            if previous_clocks is not None and (observed <= previous_clocks[1] or available < previous_clocks[0]):
                raise _Refusal("release_history_order_invalid")
            previous_clocks = (available, observed)
            workspaces.append(ws)
        # The release-only index cannot guarantee completeness of transcript
        # guidance, even when a transcript happens to be in one returned body.
        for ws in workspaces[-2:]:
            release = next(source for source in ws["sources"]
                           if isinstance(source, Mapping) and source.get("kind") == "issuer_release")
            for guidance in ws["guidance"]:
                if not isinstance(guidance, Mapping):
                    raise _Refusal("guidance_invalid")
                span = guidance.get("source_span")
                if not isinstance(span, Mapping) or span.get("document_id") != release.get("document_id"):
                    raise _Refusal("release_history_guidance_source_mismatch")
        return compare_guidance_workspaces(workspaces[-1], workspaces[-2] if len(workspaces) > 1 else None,
            as_of=now, ticker=ticker, expected_security_id=expected_security_id)
    except _Refusal as exc:
        result["reasons"] = [str(exc)]
        return result


def public_guidance_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Use the existing public-glance boundary: no raw span/document locators."""
    out = {k: context[k] for k in ("schema", "authority", "is_context_only", "display_only",
        "prophet_flags", "temporal_basis", "as_of", "available", "reasons", "consensus")}
    public_keys = ("metric", "horizon", "unit", "current_low", "current_high", "prior_low", "prior_high",
        "current_midpoint", "prior_midpoint", "midpoint_delta", "relative_change_pct",
        "relative_change_reason", "delta_unit", "direction", "interpretation")
    out["comparisons"] = [{**{k: row[k] for k in public_keys},
        "evidence": [{k: ev[k] for k in ("role", "event_id", "generation_id", "receipt_state", "observed_at", "source_available_at")}
                     for ev in row["evidence"]]} for row in context["comparisons"]]
    return out
