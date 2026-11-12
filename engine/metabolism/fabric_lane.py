"""Capacity Fabric lane for the Metabolism loop (Chairman order 2026-11-12).

Every metabolism LLM call today walks ``engine.llm_auth``'s provider waterfall,
whose primary pool — the ``CLAUDE_CODE_OAUTH_TOKEN_1..7`` keys — has been
``auth_failed`` / ``rate_limited`` since 2026-11-06, so the loop produces
floor-only artifacts. This module is the ONE place the loop can instead route
through the Capacity Fabric ``unified_router``, so each cutover site is a short
branch rather than nine copies of adapter plumbing.

INERT BY DEFAULT. Nothing changes unless ``FABRIC_ROUTER_TOKEN`` is present in
the process environment (``fabric_client.is_configured()``). A host without the
token runs the legacy ladder byte-identically. ``MACRO_METABOLISM_FABRIC=0`` is
the operator kill-switch for a host that HAS the token but must not spend it.

THE ROUTER OWNS FALLBACK. One logical call = one request. This module makes
exactly one attempt and never retries or walks a second provider: a raised SDK
error degrades the caller exactly as a legacy ladder failure would, and a local
retry would double-serve a call the router already resolved. The single
exception is ``FabricUnavailable`` (no token, or the SDK will not import):
nothing was served and nothing was billed, so callers catch it and run their
unchanged legacy ladder rather than blanking an artifact the old path can still
produce.

This module deliberately does not change provider routing for any non-metabolism
consumer: ``engine/llm_auth.py`` remains the shared client for the neural-web /
cortex / brain lane and is not touched by this cutover.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from lib import fabric_client

log = logging.getLogger(__name__)

#: Operator kill-switch. "0" disables the fabric lane even when a token exists.
KILL_SWITCH_ENV = "MACRO_METABOLISM_FABRIC"

#: Attribution project id — same constant the AI Brief writer uses.
PROJECT_ID = "macro-dashboard"

#: Loop step -> fabric lane. The two fail-closed production-protection gates
#: (audit, adjudicate) take the balanced lane; the rest are routine generation
#: and take the fast lane. Deliberately NOT "frontier": the loop is unattended
#: and its artifacts are advisory.
_STAGE_LANES: dict[str, str] = {
    "attention": "fast",
    "agenda": "fast",
    "propose": "fast",
    "adjudicate": "balanced",
    "audit": "balanced",
    "standout": "fast",
    "autopsy": "fast",
    "dream": "fast",
    "shadow": "fast",
}

#: The one exception callers must handle by falling back to their legacy ladder.
FabricUnavailable = fabric_client.FabricUnavailable

#: provider label returned to callers / written into artifacts.
PROVIDER = "fabric"


def enabled(stage: str | None = None) -> bool:
    """True when this stage should route through the router.

    False (never raises) when the kill-switch is set to "0", when the stage is
    unknown, or when no router token is configured.
    """
    if stage is not None and stage not in _STAGE_LANES:
        log.warning("fabric_lane: unknown stage %r — staying on the legacy ladder", stage)
        return False
    if os.environ.get(KILL_SWITCH_ENV, "").strip() == "0":
        return False
    try:
        return bool(fabric_client.is_configured())
    except Exception as exc:  # noqa: BLE001 — a broken adapter must not break the loop
        log.warning("fabric_lane: is_configured failed (%s) — legacy ladder", exc)
        return False


def session_id(stage: str, suffix: str | None = None) -> str:
    """Attribution session id: ``macro-metab-<stage>[-<suffix>]``."""
    base = f"macro-metab-{stage}"
    return f"{base}-{suffix}" if suffix else base


def _usage_row(comp: Any) -> dict[str, Any]:
    """Map the router's usage block onto the ``lib.ai_costs`` row shape.

    The SDK reports ``cache_read_input_tokens`` / ``cache_creation_input_tokens``;
    ``lib.ai_costs.record_usage`` expects ``cache_read_tokens`` /
    ``cache_creation_tokens``. A missing or malformed block yields zeros rather
    than raising — usage accounting must never break a served call.
    """
    raw = getattr(comp, "usage", None) or {}
    if not isinstance(raw, dict):
        try:
            raw = dict(raw)
        except Exception:  # noqa: BLE001
            raw = {}

    def _int(key: str) -> int:
        try:
            return int(raw.get(key) or 0)
        except Exception:  # noqa: BLE001
            return 0

    return {
        "input_tokens": _int("input_tokens"),
        "output_tokens": _int("output_tokens"),
        "cache_read_tokens": _int("cache_read_input_tokens"),
        "cache_creation_tokens": _int("cache_creation_input_tokens"),
        "model": getattr(comp, "model_served", None) or "",
    }


def call(
    *,
    stage: str,
    system: str,
    user: str,
    max_tokens: int = 4000,
    session_suffix: str | None = None,
    lane: str | None = None,
    usage_out: list[dict[str, Any]] | None = None,
) -> tuple[str | None, str | None, str | None]:
    """ONE metabolism call through the router.

    Returns ``(text, degraded_reason, provider)`` — the same shape every
    metabolism caller already returns — where ``provider`` is ``"fabric"``.
    ``degraded_reason`` is None on success.

    Raises ``FabricUnavailable`` when the router cannot be reached AT ALL, so the
    caller can run its unchanged legacy ladder. Every other error is degraded
    here and NOT retried: the router already walked its own ladder, and a second
    request would double-serve.

    When ``usage_out`` is a list, one ``lib.ai_costs``-shaped usage row is
    appended so the script-level ``record_usage`` call still books fabric spend.
    """
    chosen_lane = lane or _STAGE_LANES.get(stage, "fast")
    try:
        comp = fabric_client.complete(
            [{"role": "user", "content": user}],
            system=system,
            lane=chosen_lane,
            max_tokens=int(max_tokens),
            project_id=PROJECT_ID,
            session_id=session_id(stage, session_suffix),
        )
    except fabric_client.FabricUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 — degrade, never raise, never retry
        log.warning("fabric_lane[%s]: router call failed (%s)", stage, exc)
        return None, f"llm_error: {exc}", PROVIDER

    if usage_out is not None:
        try:
            usage_out.append(_usage_row(comp))
        except Exception as exc:  # noqa: BLE001 — telemetry only
            log.debug("fabric_lane[%s]: usage capture failed (%s)", stage, exc)

    text = (comp.text or "").strip()
    if not text:
        reason = ("stop_refusal"
                  if getattr(comp.raw, "stop_reason", None) == "refusal"
                  else "empty_reply")
        return None, reason, PROVIDER
    return text, None, PROVIDER
