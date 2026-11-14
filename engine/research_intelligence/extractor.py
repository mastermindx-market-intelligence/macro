"""Long-form research extraction inside the existing qualitative-intelligence spine."""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
from typing import Any, Callable

from lib import fabric_client
from engine.qual_extraction import quote_span_verified
from .schema import SCHEMA, claim_statement_supported, thesis_direction_values, validate_rio
from .selection import (
    MAX_BODY_BYTES,
    MAX_FINAL_RIO_BYTES,
    _VerifierBudget,
    source_context_receipt,
    SELECTOR_SYSTEM_PROMPT,
    SELECTOR_VERSION,
    SelectionUnavailable,
    build_selector_prompt,
    parse_selector_output,
)

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)
PROMPT_VERSION = "mastermind.research_intelligence.extractor.v3"
SYSTEM_PROMPT = SELECTOR_SYSTEM_PROMPT

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Capacity Fabric cutover — the DEEP-READ WRITER only (Chairman order 2026-11-12)
# --------------------------------------------------------------------------- #
#: Operator kill-switch. "0" disables the fabric lane even when a token exists.
_FABRIC_KILL_SWITCH = "MACRO_RESEARCH_INTEL_FABRIC"
#: Attribution project id — the same constant the AI Brief writer uses.
_FABRIC_PROJECT_ID = "macro-dashboard"
#: Attribution session id for this vertical.
_FABRIC_SESSION_ID = "macro-research-intel"
#: Ledger lane — unchanged from the legacy descriptor's ``usage_lane`` so the
#: spend drill-down keeps one research-intelligence series.
_FABRIC_LEDGER_LANE = "research-intelligence"


def _fabric_research_intel_enabled() -> bool:
    """True when this writer should route through the Capacity Fabric.

    Default ON whenever the router token is present; ``MACRO_RESEARCH_INTEL_FABRIC=0``
    is the operator kill-switch. With no token this is False and the legacy
    ladder below runs byte-identically.
    """
    if os.environ.get(_FABRIC_KILL_SWITCH, "").strip() == "0":
        return False
    return fabric_client.is_configured()


def _book_fabric_usage(comp: Any) -> None:
    """Append one ``lib.ai_costs`` row for a router-served call. NEVER raises.

    The SDK reports ``cache_read_input_tokens`` / ``cache_creation_input_tokens``;
    ``record_usage`` expects ``cache_read_tokens`` / ``cache_creation_tokens``.
    Attribution, not billing: the consumer must not book router spend as Claude
    OAuth, so the row names ``provider="fabric"`` and the model the router
    actually served.
    """
    try:
        from lib import ai_costs  # noqa: PLC0415 — optional at import time

        usage = getattr(comp, "usage", None) or {}
        if not isinstance(usage, dict):
            try:
                usage = dict(usage)
            except Exception:  # noqa: BLE001
                usage = {}

        def _int(key: str) -> int:
            try:
                return int(usage.get(key) or 0)
            except Exception:  # noqa: BLE001
                return 0

        ai_costs.record_usage(
            lane=_FABRIC_LEDGER_LANE,
            provider="fabric",
            model=getattr(comp, "model_served", None) or None,
            input_tokens=_int("input_tokens"),
            output_tokens=_int("output_tokens"),
            cache_read_tokens=_int("cache_read_input_tokens"),
            cache_creation_tokens=_int("cache_creation_input_tokens"),
            stage="research_intelligence",
        )
    except Exception as exc:  # noqa: BLE001 — usage accounting must never break a served call
        log.debug("research_intelligence: fabric usage capture failed (%s)", exc)


def _fabric_default_call(system: str, user: str, *, max_tokens: int) -> tuple[str, str, str]:
    """ONE extraction call through the router. Never retries, never fails over.

    The router owns provider selection, cooldown and account pooling, so this
    makes exactly one request: a raised transport error is left to propagate to
    the caller's existing ``except Exception`` handler, which degrades it to
    ``call_failed`` exactly as a legacy ladder failure would. A local retry or a
    second provider would double-serve a call the router already resolved.

    ``FabricUnavailable`` is the one exception and is re-raised: it means no
    request ever left this host (no token, or the SDK will not import), so
    nothing was served and nothing was billed. ``_default_call`` catches it and
    runs the unchanged legacy ladder.

    A refusal is a refusal even when it carries partial text: ``""`` is returned
    so the fail-closed selector parser never sees a complete-looking object.
    """
    comp = fabric_client.complete(
        [{"role": "user", "content": user}],
        system=system,
        lane="balanced",
        max_tokens=int(max_tokens),
        project_id=_FABRIC_PROJECT_ID,
        session_id=_FABRIC_SESSION_ID,
    )
    _book_fabric_usage(comp)
    served_model = str(comp.model_served or "")
    if getattr(comp.raw, "stop_reason", None) == "refusal":
        return "", "fabric", served_model
    return str(comp.text or ""), "fabric", served_model


class _ProvidersUnavailable(RuntimeError):
    """No configured provider can serve this extraction request."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _identity(document: dict[str, Any], body: str) -> dict[str, str]:
    doc_id = str(document.get("id") or "").strip()
    if not doc_id:
        raise ValueError("document.id is required")
    source_type = str(document.get("source_type") or "").strip()
    if not source_type:
        raise ValueError("document.source_type is required")
    identity = {
        key: str(document.get(key) or "").strip()
        for key in ("id", "source_type", "source_name", "institution", "desk", "title", "published_at")
    }
    identity["content_sha256"] = _sha(body)
    return identity


def _output_shape(identity: dict[str, str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "document": identity,
        "claims": [{
            "statement": "",
            "evidence": [{"quote_span": ""}],
            "numbers": [], "entities": [], "horizon": "", "explicit": False,
        }],
        "analysis": {
            "thesis": {
                "summary": "", "direction": "unclear", "mechanism": [],
                "conviction": "", "support_claim_indices": [0],
            },
            "assumptions": [], "forecasts": [], "catalysts": [],
            "falsifiers": [], "counterarguments": [], "implications": [],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
            "uncertainties": [],
        },
        "authority": "descriptive_research_only",
    }


def build_prompt(document: dict[str, Any], markdown: str, *, source_record=None, layout_scope=None) -> tuple[str, str]:
    """Build the deterministic private v3 prompt; no copy-only fallback."""
    body = str(markdown or "")
    system, user, _ = build_selector_prompt(_identity(document, body), body, source_record=source_record, layout_scope=layout_scope)
    return system, user


def _parse_json(raw_text: str) -> dict[str, Any]:
    text = _FENCE.sub("", str(raw_text or "").strip())
    try:
        obj = json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("model output contains no JSON object")
        obj = json.loads(text[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("model output JSON must be an object")
    return obj


def _remap(indices: list[int], mapping: dict[int, int]) -> list[int]:
    """Keep an assertion only when every referenced claim survives grounding."""
    if any(i not in mapping for i in indices):
        return []
    return [mapping[i] for i in indices]


def _ground_rio(rio: dict[str, Any], body: str) -> dict[str, Any]:
    """Enforce the canonical qualitative citation law and remap synthesis support."""
    obj = validate_rio(rio, require_grounded_claims=False)
    mapping: dict[int, int] = {}
    claims: list[dict[str, Any]] = []
    for old_index, claim in enumerate(obj["claims"]):
        verified = [
            evidence for evidence in claim["evidence"]
            if quote_span_verified(body, evidence["quote_span"], require_complete_clause=True)
        ]
        if not verified:
            continue
        if not quote_span_verified(body, claim["statement"], require_complete_clause=True):
            continue
        if not claim_statement_supported(claim["statement"], verified):
            continue
        grounded = dict(claim)
        grounded["evidence"] = verified
        grounded["numbers"] = [
            number for number in claim["numbers"]
            if any(
                quote_span_verified(evidence["quote_span"], number, minimum_chars=1)
                for evidence in verified
            )
        ]
        mapping[old_index] = len(claims)
        claims.append(grounded)
    if not claims:
        raise ValueError("no source claim survived verbatim quote verification")

    out = copy.deepcopy(obj)
    out["claims"] = claims
    analysis = out["analysis"]
    if quote_span_verified(body, analysis["thesis"]["summary"], minimum_chars=4):
        raise ValueError("analysis.thesis.summary must be synthesis, not verbatim source text")
    thesis_support = _remap(analysis["thesis"]["support_claim_indices"], mapping)
    if not thesis_support:
        raise ValueError("analysis.thesis lost referenced grounded claim support")
    analysis["thesis"]["support_claim_indices"] = thesis_support

    for field in ("assumptions", "forecasts", "catalysts", "falsifiers", "counterarguments", "implications", "uncertainties"):
        kept: list[dict[str, Any]] = []
        for row in analysis[field]:
            support = _remap(row["support_claim_indices"], mapping)
            if support:
                updated = dict(row)
                updated["support_claim_indices"] = support
                kept.append(updated)
        analysis[field] = kept
    for field in ("belief_delta", "consensus_relation"):
        row = analysis[field]
        support = _remap(row["support_claim_indices"], mapping)
        analysis[field] = (
            {"statement": row["statement"], "support_claim_indices": support}
            if row["statement"] and support
            else {"statement": "", "support_claim_indices": []}
        )
    return validate_rio(out)


def parse_model_output(
    raw_text: str,
    *,
    expected_document_id: str,
    expected_document: dict[str, Any],
    source_body: str,
) -> dict[str, Any]:
    obj = _parse_json(raw_text)
    normalized = validate_rio(
        obj,
        expected_document_id=expected_document_id,
        expected_document=expected_document,
        require_grounded_claims=False,
    )
    return _ground_rio(normalized, source_body)


def _default_call(system: str, user: str, *, model_id: str, max_tokens: int) -> tuple[str, str, str]:
    # Capacity Fabric first (Chairman order 2026-11-12). FabricUnavailable means
    # no request ever left the host, so the legacy ladder below runs unchanged;
    # any other router error propagates to _analyze_document_selector_v3's
    # existing handler and degrades to call_failed, never retried.
    if _fabric_research_intel_enabled():
        try:
            return _fabric_default_call(system, user, max_tokens=max_tokens)
        except fabric_client.FabricUnavailable as exc:
            log.warning(
                "research_intelligence: fabric router unavailable (%s); "
                "using the legacy ladder", exc)

    from engine import llm_auth

    providers = llm_auth.build_providers({"usage_lane": "research-intelligence"}, opus_model=model_id)
    if not providers:
        raise _ProvidersUnavailable("no configured provider")
    served_model = ""

    def do_call(client, model):
        nonlocal served_model
        served_model = str(model or "")
        resp = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        return (text or None), None, resp

    raw, _reason, provider = llm_auth.make_call(
        providers, do_call, context="research_intelligence"
    )
    return str(raw or ""), str(provider or ""), served_model


def analyze_document(
    document: dict[str, Any],
    markdown: str,
    *,
    model_id: str,
    max_tokens: int = 6000,
    call: Callable[..., tuple[str, str, str]] | None = None,
    source_record=None,
    layout_scope=None,
) -> dict[str, Any]:
    """Select original source slices under v3 and ground one frozen RIO."""
    requested_model = str(model_id or "").strip()
    if not requested_model:
        raise ValueError("model_id is required")
    return _analyze_document_selector_v3(
        document, str(markdown or ""), model_id=requested_model,
        max_tokens=max_tokens, call=call, source_record=source_record, layout_scope=layout_scope,
    )


def _analyze_document_selector_v3(
    document: dict[str, Any],
    body: str,
    *,
    model_id: str,
    max_tokens: int,
    call: Callable[..., tuple[str, str, str]] | None,
    source_record=None,
    layout_scope=None,
) -> dict[str, Any]:
    """Private selector-v3 edge: the model selects IDs; the system writes claim text.

    Selection-catalog failures are distinct pre-call refusals with ``rio=None``
    and no model call; provider error, provenance, and requested-model states
    match the frozen legacy edge, and nothing is ever retried automatically.
    """
    prompt_contract_sha = _sha(PROMPT_VERSION + "\n" + SYSTEM_PROMPT)
    work_budget = _VerifierBudget()
    try:
        if not body.strip():
            raise SelectionUnavailable("EMPTY_DOCUMENT_BODY", "document body is empty")
        if len(body.encode("utf-8")) > MAX_BODY_BYTES:
            raise SelectionUnavailable("BODY_SIZE_OVERFLOW", "document body exceeds its byte bound")
        try:
            identity = _identity(document, body)
        except (ValueError, TypeError, AttributeError) as exc:
            raise SelectionUnavailable("IDENTITY_UNAVAILABLE", "document identity is unavailable") from exc
        system, user, catalog = build_selector_prompt(identity, body, _work_budget=work_budget, source_record=source_record, layout_scope=layout_scope)
    except SelectionUnavailable as exc:
        return {
            "state": "selection_unavailable", "rio": None,
            "provider": "", "model": "",
            "error_code": exc.code,
            "requested_model": model_id,
            "prompt_version": PROMPT_VERSION,
            "prompt_contract_sha256": prompt_contract_sha,
            "prompt_sha256": "",
        }
    receipt = {
        "document": identity,
        "requested_model": model_id,
        "prompt_version": PROMPT_VERSION,
        "prompt_contract_sha256": prompt_contract_sha,
        "prompt_sha256": _sha(system + "\n" + user),
        "source_context": source_context_receipt(catalog),
    }
    fn = call or _default_call
    try:
        raw, provider, used_model = fn(
            system, user, model_id=model_id, max_tokens=max_tokens
        )
    except _ProvidersUnavailable:
        return {
            "state": "providers_unavailable", "rio": None,
            "provider": "", "model": "",
            "error_code": "NO_PROVIDER_AVAILABLE", **receipt,
        }
    except Exception as exc:  # noqa: BLE001 - provider failures are degraded data, never truth.
        return {
            "state": "call_failed", "rio": None, "provider": "", "model": "",
            "error_class": type(exc).__name__[:120], **receipt,
        }
    raw = str(raw or "")
    provider = str(provider or "").strip()
    used_model = str(used_model or "").strip()
    base = {
        "provider": provider,
        "model": used_model,
        **receipt,
    }
    if not raw:
        return {"state": "no_model_output", "rio": None, **base}
    if not provider or not used_model:
        return {
            "state": "model_provenance_unavailable", "rio": None,
            "error_code": "SERVING_PROVENANCE_MISSING", **base,
        }
    try:
        parsed = parse_selector_output(raw, identity, body, _work_budget=work_budget, source_record=source_record, layout_scope=layout_scope)
        rio = _ground_rio(parsed["rio"], body)
        if len(json.dumps(rio, ensure_ascii=False).encode("utf-8")) > MAX_FINAL_RIO_BYTES:
            raise ValueError("final rio exceeds the 128KiB persistence bound")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return {
            "state": "invalid_model_output", "rio": None,
            "error_class": type(exc).__name__[:120], **base,
        }
    return {"state": "ok", "rio": rio, **base}
