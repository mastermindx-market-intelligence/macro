"""Versioned US/China cohort delivery contract — a pure reader over the W3C cohort owners.

GMI recovery §9 step 6. A Terminal or Prophet consumer of the US (``us_today``) or
China (``cn_featured``) selection cohort gets exactly ONE typed delivery state for one
market and one finalized generation:

``POSITIVE``
    A separately authorized capture. The incumbent read returned AVAILABLE with a
    finalized receipt that validates, is bound to the requested market, and was
    captured under the incumbent purpose ``selection_cohort_internal_capture``. The
    incumbent product projection is also available.
``DEGRADED_REFUSAL``
    The honest, typed "not available". The incumbent natural binding today is
    ``authorize_capture=None``, which reads as ``CAPTURE_RIGHTS_UNAVAILABLE``. That is
    a rights refusal, not a source mismatch
    (DSC:GMI-CAPTURE-RIGHTS-REFUSAL-IS-NOT-SOURCE-MISMATCH). There are no members, and
    the incumbent reason codes are carried verbatim.
``REFUSED``
    An unauthorized or unlawful capture: a forged, altered or mismatched receipt; a
    non-capability authority; a mixed market; THS-basket laundering; or an
    HKEX-scrape source. It is never silently downgraded to DEGRADED_REFUSAL, and it
    delivers no projection and no members.

The document also records two INDEPENDENT blocks: the viewer's disclosure grant, and
Prophet-board graph-source enrollment. A disclosure-purpose grant never grants
enrollment, and enrollment never grants the disclosure. The grant block is computed
after the decision. The decision function never receives it.

What this module is NOT (gate #8): a producer, a store, a writer, a rights resolver, a
ThemeState owner or a publication control plane. It composes over
``selection_cohort_publication.read_finalized_cohort`` and
``selection_cohort_projection.project_selection_cohort_for_product`` and nothing else.
It writes no file and never calls ``write_product_projection``. It passes the
supplied capture capability to the incumbent unchanged and never defaults it to an
allow-all. It is display-only and never ranks, sizes, gates or originates a signal.
"""
from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

from engine.theme_graph import selection_cohort_publication as _pub
from engine.theme_graph import selection_cohort_projection as _proj
from engine.theme_graph.selection_cohort import FLAGS
from engine.theme_graph.rights_use import PURPOSE as CAPTURE_PURPOSE

SCHEMA = "theme_graph.cohort_us_china_delivery/v1"

MARKETS: dict[str, dict[str, str]] = {
    "us": {"incumbent_market": "us_today",
           "cohort_scope": "US_COMPLETE_NATIVE_FEATURED/v1",
           "reason_projection": "native-owner-reasons/v1",
           "owner": "build_stock_library"},
    "cn": {"incumbent_market": "cn_featured",
           "cohort_scope": "CN_COMPLETE_SERVED_WIDE_BUY/v1",
           "reason_projection": "cn-served-reasons/v1",
           "owner": "build_china"},
}

DISCLOSURE_PURPOSE = "private_company_intelligence_context"
DISCLOSURE_AUDIENCE = "company_intelligence_entitled"
LAUNDERING_PREFIX = "basket:baskets_china_ths:"
AUTHORITY_CEILING = "research_internal_only"
ENROLLMENT_BASIS = "incumbent_capture_gate:" + CAPTURE_PURPOSE

DELIVERIES = ("POSITIVE", "DEGRADED_REFUSAL", "REFUSED")

LIMITATIONS: tuple[str, ...] = (
    "display-only; never ranks, sizes, gates or originates signals",
    "a disclosure grant never grants Prophet-board graph-source enrollment",
    "REFUSED delivers no members; DEGRADED_REFUSAL is an honest typed unavailability",
    "composes over the incumbent W3C cohort readers; it is not a producer, store, rights resolver or publication control plane",
    "enrollment is scoped to this one read of one finalized generation and is never persisted here",
)

_HKEX = re.compile(r"hkex", re.IGNORECASE)
# A capability is an incumbent callable. A rights string, registry class, HTTP
# status, verdict dict or grant record is never one, even when a subclass makes it
# callable.
_NOT_CAPABILITIES = (str, bytes, bytearray, bool, int, float, Mapping)


# --------------------------------------------------------------------------- blocks

def _grant_block(grant: Any) -> dict[str, Any]:
    """Record the viewer's disclosure grant. It is recorded only: it confers nothing."""
    def block(state: str, reason: str | None) -> dict[str, Any]:
        return dict(state=state, purpose=DISCLOSURE_PURPOSE, audience=DISCLOSURE_AUDIENCE,
                    reason=reason, confers_enrollment=False)

    if grant is None:
        return block("NOT_EVALUATED", None)
    try:
        if not isinstance(grant, Mapping):
            return block("NOT_GRANTED", "MALFORMED")
        purpose, audience, granted = grant.get("purpose"), grant.get("audience"), grant.get("granted")
        if not isinstance(purpose, str) or not isinstance(audience, str) or not isinstance(granted, bool):
            return block("NOT_GRANTED", "MALFORMED")
        if purpose != DISCLOSURE_PURPOSE:
            return block("NOT_GRANTED", "PURPOSE_MISMATCH")
        if audience != DISCLOSURE_AUDIENCE:
            return block("NOT_GRANTED", "AUDIENCE_MISMATCH")
        if granted is not True:
            return block("NOT_GRANTED", "NOT_GRANTED")
        return block("GRANTED", None)
    except Exception:  # an exotic Mapping must not break the delivery document
        return block("NOT_GRANTED", "MALFORMED")


def _document(market: Any, delivery: str, reason_codes: list[str], *,
              receipt: Mapping | None = None, projection: Mapping | None = None,
              grant: Any = None) -> dict[str, Any]:
    spec = MARKETS.get(market) if isinstance(market, str) else None
    positive = delivery == "POSITIVE"
    n_selected = projection.get("n_selected", 0) if positive and isinstance(projection, Mapping) else 0
    return dict(
        schema=SCHEMA,
        market=market if isinstance(market, str) and market else None,
        incumbent_market=spec["incumbent_market"] if spec else None,
        cohort_scope=spec["cohort_scope"] if spec else None,
        reason_projection=spec["reason_projection"] if spec else None,
        delivery=delivery,
        reason_codes=[] if positive else list(reason_codes),
        capture=dict(purpose=CAPTURE_PURPOSE, authorized=positive,
                     receipt_sha256=receipt["receipt_sha256"] if positive else None,
                     generation_id=receipt["generation_id"] if positive else None),
        prophet_board_graph_source_enrollment=dict(
            state="ENROLLED_FOR_THIS_READ" if positive else "NOT_ENROLLED",
            basis=ENROLLMENT_BASIS if positive else None,
            derived_from_disclosure_grant=False),
        viewer_disclosure_grant=_grant_block(grant),
        projection=None if delivery == "REFUSED" or projection is None else copy.deepcopy(dict(projection)),
        n_selected=n_selected,
        authority_ceiling=AUTHORITY_CEILING,
        public_display_allowed=False,
        **{flag: False for flag in FLAGS},
        limitations=list(LIMITATIONS),
    )


# --------------------------------------------------------------------------- probes

def _strings(value: Any):
    """Every string key and value, walked iteratively (no recursion limit)."""
    stack, seen = [value], set()
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            yield current
        elif isinstance(current, Mapping):
            if id(current) in seen:
                continue
            seen.add(id(current))
            for key, item in current.items():
                if isinstance(key, str):
                    yield key
                stack.append(item)
        elif isinstance(current, (list, tuple)):
            if id(current) in seen:
                continue
            seen.add(id(current))
            stack.extend(current)


def _receipt_source_strings(receipt: Mapping):
    for key in ("source_ref", "source_schema", "source_origin_ref"):
        yield receipt.get(key)
    selection = receipt.get("source_selection")
    if isinstance(selection, Mapping):
        for key in ("source_ref", "source_schema", "owner"):
            yield selection.get(key)
    ancestry = receipt.get("ancestry")
    if isinstance(ancestry, (list, tuple)):
        for row in ancestry:
            if isinstance(row, Mapping):
                yield from (v for v in row.values() if isinstance(v, str))
    clocks = receipt.get("source_clocks")
    if isinstance(clocks, Mapping):
        yield from clocks.keys()
        yield from (v for v in clocks.values() if isinstance(v, str))


def _flags_escalated(*containers: Any) -> bool:
    return any(isinstance(c, Mapping) and flag in c and c[flag] is not False
               for c in containers for flag in FLAGS)


def _reason_codes(value: Any) -> list[str]:
    if (isinstance(value, list) and value
            and all(isinstance(code, str) and code for code in value)):
        return list(value)
    return ["SOURCE_UNAVAILABLE"]


def _project(wrapper: Any, rights_path: Any) -> dict[str, Any] | None:
    try:
        projection = _proj.project_selection_cohort_for_product(wrapper, rights_path=rights_path)
    except Exception:
        return None
    return projection if isinstance(projection, dict) else None


# --------------------------------------------------------------------------- decision

def _decide(market: Any, wrapper: Any, rights_path: Any):
    """The decision order. It never sees the viewer's disclosure grant.

    Returns ``(delivery, reason_codes, receipt, projection)``.
    """
    if not isinstance(market, str) or market not in MARKETS:
        return "REFUSED", ["UNSUPPORTED_MARKET"], None, None
    spec = MARKETS[market]
    if not isinstance(wrapper, dict):
        return "DEGRADED_REFUSAL", ["WRAPPER_MISSING"], None, _project(None, rights_path)
    if any(LAUNDERING_PREFIX in text for text in _strings(wrapper)):
        return "REFUSED", ["LAUNDERING_REFUSED"], None, None
    receipt = wrapper.get("receipt")
    explanation = wrapper.get("explanation")
    if isinstance(receipt, Mapping) and any(
            isinstance(text, str) and _HKEX.search(text) for text in _receipt_source_strings(receipt)):
        return "REFUSED", ["PROHIBITED_SOURCE"], None, None
    if _flags_escalated(wrapper, receipt, explanation):
        return "REFUSED", ["AUTHORITY_ESCALATION_REFUSED"], None, None
    if wrapper.get("schema") != _pub.SCHEMA:
        return "REFUSED", ["UNAUTHORIZED_CAPTURE:SCHEMA"], None, None
    if wrapper.get("status") == "UNAVAILABLE":
        if receipt is not None or explanation is not None:
            return "REFUSED", ["UNAUTHORIZED_CAPTURE:INCONSISTENT_WRAPPER"], None, None
        projection = _project(wrapper, rights_path)
        if projection is None:
            return "DEGRADED_REFUSAL", ["PROJECTION_RUNTIME_UNAVAILABLE"], None, None
        return "DEGRADED_REFUSAL", _reason_codes(wrapper.get("reason_codes")), None, projection
    if wrapper.get("status") != "AVAILABLE" or wrapper.get("reason_codes") != []:
        return "REFUSED", ["UNAUTHORIZED_CAPTURE:STATUS"], None, None
    if not isinstance(receipt, dict):
        return "REFUSED", ["UNAUTHORIZED_CAPTURE:RECEIPT_MISSING"], None, None
    selection = receipt.get("source_selection")
    if not isinstance(selection, dict):
        return "REFUSED", ["UNAUTHORIZED_CAPTURE:RECEIPT_INVALID"], None, None
    if (receipt.get("market") != spec["incumbent_market"]
            or receipt.get("reason_projection") != spec["reason_projection"]
            or selection.get("cohort_scope") != spec["cohort_scope"]):
        return "REFUSED", ["MIXED_MARKET_REFUSED"], None, None
    try:
        _pub.validate_publication(copy.deepcopy(receipt))
    except Exception:  # jsonschema errors, PublicationRefusal, malformed clocks, ...
        return "REFUSED", ["UNAUTHORIZED_CAPTURE:RECEIPT_INVALID"], None, None
    if (receipt.get("capture_use") != CAPTURE_PURPOSE
            or receipt.get("public_display_allowed") is not False
            or receipt.get("status") != "FINALIZED"):
        return "REFUSED", ["UNAUTHORIZED_CAPTURE:CAPTURE_USE"], None, None
    if explanation is not None and (not isinstance(explanation, dict)
                                    or explanation.get("source_selection") != selection):
        # An explanation spliced from another selection is not this capture.
        return "REFUSED", ["UNAUTHORIZED_CAPTURE:EXPLANATION_BINDING"], None, None
    projection = _project(wrapper, rights_path)
    if projection is None:
        return "DEGRADED_REFUSAL", ["PROJECTION_RUNTIME_UNAVAILABLE"], None, None
    availability = projection.get("availability")
    status = availability.get("status") if isinstance(availability, Mapping) else None
    if projection.get("unavailable_reason") is not None or status in (None, "UNAVAILABLE"):
        reason = projection.get("unavailable_reason")
        return ("DEGRADED_REFUSAL", [reason if isinstance(reason, str) and reason else "PROJECTION_UNAVAILABLE"],
                None, projection)
    n_selected = projection.get("n_selected")
    if not isinstance(n_selected, int) or isinstance(n_selected, bool) or n_selected < 0:
        return "DEGRADED_REFUSAL", ["PROJECTION_INVALID"], None, projection
    return "POSITIVE", [], receipt, projection


# --------------------------------------------------------------------------- public

def classify_cohort_wrapper(market: Any, wrapper: Any, *, viewer_disclosure_grant: Any = None,
                            rights_path: Any = None) -> dict[str, Any]:
    """Classify an already-read incumbent wrapper. Never raises on data problems."""
    try:
        delivery, codes, receipt, projection = _decide(market, wrapper, rights_path)
        return _document(market, delivery, codes, receipt=receipt, projection=projection,
                         grant=viewer_disclosure_grant)
    except Exception:  # fail closed: a classifier fault is never a delivery
        return _document(market, "REFUSED", ["CLASSIFICATION_FAULT"], grant=viewer_disclosure_grant)


def read_cohort_delivery(market: Any, raw_bytes: Any, *, generation_id: Any, data_dir: Any,
                         authorize_capture: Any = None, qualified_reads: Any = None,
                         viewer_disclosure_grant: Any = None, rights_path: Any = None) -> dict[str, Any]:
    """Read one finalized generation through the incumbent reader, then classify it.

    ``authorize_capture`` and ``qualified_reads`` reach the incumbent unchanged.
    """
    try:
        if not isinstance(market, str) or market not in MARKETS:
            return _document(market, "REFUSED", ["UNSUPPORTED_MARKET"], grant=viewer_disclosure_grant)
        if authorize_capture is not None and (not callable(authorize_capture)
                                              or isinstance(authorize_capture, _NOT_CAPABILITIES)):
            return _document(market, "REFUSED", ["CAPTURE_AUTHORITY_NOT_A_CAPABILITY"],
                             grant=viewer_disclosure_grant)
    except Exception:
        return _document(market, "REFUSED", ["CLASSIFICATION_FAULT"], grant=viewer_disclosure_grant)
    try:
        wrapper = _pub.read_finalized_cohort(
            raw_bytes, market=MARKETS[market]["incumbent_market"], generation_id=generation_id,
            data_dir=data_dir, authorize_capture=authorize_capture, qualified_reads=qualified_reads)
    except Exception:
        return _document(market, "DEGRADED_REFUSAL", ["SOURCE_RUNTIME_UNAVAILABLE"],
                         grant=viewer_disclosure_grant)
    return classify_cohort_wrapper(market, wrapper, viewer_disclosure_grant=viewer_disclosure_grant,
                                   rights_path=rights_path)
