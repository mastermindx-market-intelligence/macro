"""One AI Brief consumer of the existing application Fabric owner.

Capacity, accounts, model fallback, authorization, usage and admission remain in
provider_production_modes/llm_auth and the Fabric gateway. This module never
opens a second provider, replays an uncertain call, or uses a legacy secret.
The live read uses Master Brain's existing state, prompt and output vocabulary;
it does not append research theses or originate a trading signal.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.aibrief_live import LISTS, SCALARS, content_id, validate_brief


@dataclass
class Prepared:
    factory: Any
    workload: dict
    identity: str


@dataclass
class Outcome:
    state: str
    reason: str
    brief: dict | None = None
    close_confirmed: bool = False


def prepare(root: Path, cfg: dict) -> Prepared:
    """Local eligibility only; no credential read, client or provider request."""
    from engine import provider_production_modes as owner

    maker = getattr(owner, "make_application_fabric_factory", None)
    if not callable(maker):
        raise RuntimeError("fabric_owner_not_installed")
    selected = os.environ.get("MM_PROVIDER_APPLICATION_MODE")
    if not selected:
        raise RuntimeError("fabric_not_selected")
    workload = {
        "provider_order": ["fabric"], "workload_profile": "site_batch",
        "usage_lane": "master-brain", "client_timeout_s": 180,
    }
    factory = maker(mode_id=selected, lane="master-brain", workload_cfg=workload, root=root)
    # Binding rechecks this exact eligibility snapshot before opening a client.
    identity = factory.inspect(workload)
    factory = factory.with_inspection(identity)
    return Prepared(factory, workload, content_id(identity))


def generate(state: dict, cfg: dict, *, lens: str, root: Path,
             operation_id: str, prepared: Prepared, brain=None) -> Outcome:
    """Exactly one intentional inference step. All fallback is owner-controlled."""
    from engine import llm_auth
    if brain is None:
        from engine import master_brain as brain

    provider = None
    terminal_returned = False
    result = Outcome("unavailable", "fabric_binding_unavailable")
    try:
        provider = llm_auth.build_fabric_provider(
            prepared.factory, request_id=operation_id, workload_cfg=prepared.workload)
        provider.update(usage_lane="master-brain", usage_stage=lens, usage_cycle_id=operation_id)
        system = brain.LENSES[lens]["system"].format(thesis=brain._thesis_for(lens, cfg))
        # Keep one output/operation. Chinese may fail open to English in the
        # incumbent renderer; a translation outage cannot discard a valid read.
        system += ("\nReturn the existing JSON fields. Include a zh object with Chinese "
                   "translations of summary, regime_read, tldr, conflicts, transmission, "
                   "rotation_check and watch_items. Do not add or change claims in translation. "
                   "Honor each source's date; do not describe old observations as current. "
                   "This read must not originate trades, sizing or a new signal.")
        user = ("Today's deterministic state (JSON):\n<state>\n"
                + json.dumps(state, ensure_ascii=False, sort_keys=True, allow_nan=False)
                + "\n</state>")

        def call(client, model):
            response = client.messages.create(
                model=model, max_tokens=min(max(int(cfg.get("max_tokens", 8000)), 1000), 12000),
                system=system, messages=[{"role": "user", "content": user}])
            if getattr(response, "stop_reason", None) not in ("end_turn", "stop_sequence"):
                return None, "incomplete_response", response
            if any(getattr(block, "type", None) != "text" for block in response.content):
                return None, "non_text_response", response
            text = "".join(block.text for block in response.content)
            return text, None, response

        text, reason, _ = llm_auth.make_call([provider], call, context="master_brain")
        terminal_returned = True
        parsed = brain._extract_json(text) if text else None
        if reason and reason not in ("incomplete_response", "non_text_response"):
            # Unexpected owner outcomes cannot be rewritten into retryable
            # parser failures. Refusal/uncertainty is evaluated before text.
            result = Outcome("effect_unknown" if "unknown" in reason else "refused", "owner_outcome_held")
        elif reason or not isinstance(parsed, dict):
            result = Outcome("unavailable", "invalid_output")
        else:
            # Copy display fields only. Never persist model-supplied timestamps,
            # provenance, key readings, raw prompts, confidence outside its enum,
            # or thesis/ledger instructions.
            brief = {key: parsed[key] for key in (*SCALARS, *LISTS, "confidence", "zh", "forward_watch") if key in parsed}
            brief.update(schema="master_brief.v2", lens=lens, is_context_only=True,
                         generated_at=datetime.now(timezone.utc).isoformat(),
                         state_asof=state[lens]["date"], model=provider["model"],
                         served_by=provider["provider"], degraded_reason=None, theses=[])
            if validate_brief(brief, lens=lens) and not brain._collect_style_violations(brief):
                result = Outcome("succeeded", "ok", brief)
            else:
                result = Outcome("unavailable", "invalid_output")
    except Exception as exc:
        # Unknown is a hard latch for the original operation, including a lost
        # response after dispatch. Never convert it into a new request ID.
        disposition = (provider or {}).get("_fabric_native_disposition")
        pending = bool((provider or {}).get("_fabric_pending"))
        steps = (provider or {}).get("_fabric_step", 0)
        terminal_known = (terminal_returned or (provider or {}).get("_fabric_known_responses", 0) > 0
                          or disposition in ("terminal", "terminal_receipt_only"))
        unknown = bool(getattr(exc, "effect_unknown", pending or
                              steps > 0 and not terminal_known and disposition != "refused"))
        # The incumbent adapter's generic failure is not proof of an eligible
        # capacity retry. Only a correlated terminal disposition proves this
        # attempt completed; an explicit refusal never crosses another route.
        state_name = ("effect_unknown" if unknown else "refused" if disposition == "refused" else
                      "unavailable" if provider is None or terminal_known or steps == 0 else "refused")
        result = Outcome(state_name, "fabric_effect_unknown" if unknown else "fabric_unavailable")
    finally:
        if provider is not None:
            try:
                llm_auth.close_fabric_provider(provider)
            except Exception:
                pass  # No retry of an uncertain close; metadata below stays held.
            close = provider.get("_fabric_close") or {}
            confirmed = close.get("closed") is True and close.get("effect_unknown") is False
            # Legacy gateways cannot prove native turn release. A successful
            # original text remains usable, but a second operation stays held.
            result.close_confirmed = confirmed
            no_admission = (provider.get("_fabric_step", 0) == 0 and
                            close.get("attempted") is False and close.get("effect_unknown") is False)
            # The incumbent qualified legacy protocol has no native turn-close
            # effect. Keep that observation distinct from a native CLOSED receipt.
            local_complete = (terminal_returned and close.get("disposition") == "local_only"
                              and close.get("attempted") is False and close.get("effect_unknown") is False)
            if not confirmed and not no_admission and not local_complete:
                result.state, result.reason = "effect_unknown", "fabric_close_unconfirmed"
    return result
