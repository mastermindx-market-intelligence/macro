"""Machine translation of sourced English free-text → 简体中文 (gated, degrade-never-raise).

The dashboards are bilingual by DUAL-EMITTING both languages in the DOM (see
engine/i18n.py) — but that only works for strings WE compose. A few fields are
sourced English prose (the single-stock analyzer's company blurb, from
Wikipedia/SEC) that cannot be hand-translated at the source. This module is the
escape hatch: an OPTIONAL, provider-agnostic LLM translator used by a CACHED batch
job (scripts/translate_profiles.py), never on the hot path.

Design contract (mirrors engine/commodity_news.py's gated LLM helper):
  * GATED — returns "no translations" unless `enabled` AND the configured key is set.
  * DEGRADE-NEVER-RAISE — any error/parse-failure yields None for the affected items;
    the caller then keeps the English text. Translation never breaks a build.
  * PROVIDER-AGNOSTIC — uses the `anthropic` SDK's wire format; `base_url` points it at
    DeepSeek's Anthropic-compatible endpoint (the documented cheap/中文-native choice)
    or, when null, at native Anthropic. `api_key_env` names the key.
  * BATCHED + VALIDATED — N short blurbs per call via a strict JSON-array contract; a
    count mismatch fails the whole batch closed (all None), never silently misaligns.
"""
from __future__ import annotations

import json
import logging
import uuid

from lib import config

log = logging.getLogger("translate")

# --------------------------------------------------------------------------- #
# The incumbent Fabric application binding.
#
# When the trusted host (or the trusted caller config) selects the shared
# Fabric application transport, the incumbent owner composes the ONLY
# transport this module may use: no native credential read, no direct client,
# no provider fallback, no resend. An owner refusal degrades to this module's
# existing contract (every item stays English).
#
# ABSENT selection keeps the legacy provider path exactly as it was. A PRESENT
# but invalid selection stays SELECTED with no factory, so the module refuses
# instead of quietly reverting to a native credential. The selection is read
# through llm_auth's own semantics, so this module keeps NO shadow selector
# of its own: the host environment wins over the caller config, and a present
# invalid/null/empty value refuses. The text being translated can never
# choose a factory, an endpoint or a credential.
# --------------------------------------------------------------------------- #
FABRIC_LANE = "translate-profiles"
FABRIC_WORKLOAD_PROFILE = "site_batch"

_SYSTEM = (
    "You are a professional financial translator. Translate each English company "
    "description into concise, natural Simplified Chinese (简体中文). Preserve company "
    "names, ticker symbols, and place names; translate the rest faithfully. Do not add, "
    "omit, or comment. Return ONLY a JSON array of strings — exactly one translation per "
    "input item, in the same order, and nothing else."
)


def is_enabled(cfg: dict | None = None) -> bool:
    """True only when the feature is on AND a key is actually present — so callers can
    short-circuit (and tests can assert the no-op path) without constructing a client."""
    cfg = cfg if cfg is not None else config.load().get("profile_translation", {})
    if not cfg.get("enabled"):
        return False
    selected, mode_id = _fabric_selection(cfg)
    if selected:
        # A SELECTED transport owns readiness: the incumbent owner composes the
        # binding, and no native credential is discovered on this path. The
        # readiness allocation is closed before returning — a local close never
        # claims the upstream settled.
        factory = _fabric_factory(cfg, mode_id)
        provider = _fabric_provider(factory, cfg, _operation_id())
        if provider is None:
            return False
        from engine import llm_auth

        operation = llm_auth.begin_operation(
            [provider], operation_id=provider.get("_fabric_request_id") or "",
            context="translate-profiles")
        try:
            return True
        finally:
            operation.close()
    return bool(config.secret(cfg.get("api_key_env", "DEEPSEEK_API_KEY")))


def _extract_json_array(text: str) -> list | None:
    """Tolerant parse: strip code fences / prose and pull the first JSON array. Returns a
    list, or None if nothing array-shaped is found / it isn't a list of scalars."""
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.lstrip().startswith("json"):
            s = s.lstrip()[4:]
    i, j = s.find("["), s.rfind("]")
    if i == -1 or j == -1 or j < i:
        return None
    try:
        out = json.loads(s[i:j + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return out if isinstance(out, list) else None


def _client(cfg: dict):
    """Build an Anthropic-SDK client pointed at the configured endpoint, or None when the
    SDK is missing or no key is set. Never raises.

    REFUSED once a transport is selected: this path would read a native
    credential and build a direct client. Reaching it directly still refuses,
    so no selected host can discover a native credential behind the selection.
    """
    selected, _mode_id = _fabric_selection(cfg)
    if selected:
        return None
    key = config.secret(cfg.get("api_key_env", "DEEPSEEK_API_KEY"))
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        log.warning("anthropic SDK not installed — translation skipped")
        return None
    base_url = cfg.get("base_url")
    try:
        return anthropic.Anthropic(api_key=key, base_url=base_url) if base_url \
            else anthropic.Anthropic(api_key=key)
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("translation client init failed (%s)", e)
        return None


def _translate_one_batch(client, texts: list[str], cfg: dict) -> list[str | None]:
    """One API call for a batch; returns a same-length list (None per item on any failure).
    The JSON-array contract is validated by COUNT — a mismatch fails the batch closed."""
    none = [None] * len(texts)
    max_chars = int(cfg.get("max_chars", 600))
    payload = [t[:max_chars] for t in texts]
    user = ("Translate each item of this JSON array to Simplified Chinese and return a "
            "JSON array of the same length and order:\n" + json.dumps(payload, ensure_ascii=False))
    try:
        resp = client.messages.create(
            model=cfg.get("model", "deepseek-chat"),
            max_tokens=int(cfg.get("max_tokens", 4000)),
            system=_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        from lib import ai_costs as _ac  # noqa: PLC0415
        _prov, _basis = _ac.infer_provider(cfg.get("base_url"))
        _ac.record_response_usage(lane="translate-profiles", response=resp,
                                  model=cfg.get("model", "deepseek-chat"),
                                  provider=_prov, cost_basis=_basis)
        if getattr(resp, "stop_reason", None) in ("refusal", "max_tokens"):
            log.warning("translation batch stopped (%s) — keeping English", resp.stop_reason)
            return none
        text = "".join(getattr(b, "text", "") for b in resp.content
                       if getattr(b, "type", "") == "text")
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("translation batch failed (%s) — keeping English", e)
        return none
    arr = _extract_json_array(text)
    if arr is None or len(arr) != len(texts):
        log.warning("translation batch malformed (got %s for %d items) — keeping English",
                    None if arr is None else len(arr), len(texts))
        return none
    # only accept non-empty strings that actually contain CJK; else keep English
    out: list[str | None] = []
    for v in arr:
        s = str(v).strip() if v is not None else ""
        out.append(s if (s and any("一" <= ch <= "鿿" for ch in s)) else None)
    return out


_FABRIC_UNSET = object()


def translate_to_zh(texts: list[str], cfg: dict | None = None, *,
                    fabric_operation_id=_FABRIC_UNSET,
                    fabric_inspection=_FABRIC_UNSET) -> list[str | None]:
    """Translate a list of English strings to 简体中文, batched. Returns a list aligned to
    `texts`; each element is the translation or None (caller keeps the English original).
    A no-op (all None) when disabled / unkeyed / SDK-missing. Never raises."""
    cfg = cfg if cfg is not None else config.load().get("profile_translation", {})
    if not texts:
        return []
    if not cfg.get("enabled"):
        return [None] * len(texts)
    selected, mode_id = _fabric_selection(cfg)
    supplied = fabric_operation_id is not _FABRIC_UNSET or fabric_inspection is not _FABRIC_UNSET
    if supplied:
        try:
            if (not selected or mode_id is None or fabric_operation_id is _FABRIC_UNSET
                    or fabric_inspection is _FABRIC_UNSET or type(fabric_inspection) is not dict):
                raise ValueError("translation_original_invalid")
            from engine.fabric_inference_client import validate_native_operation_id
            validate_native_operation_id(fabric_operation_id)
        except Exception:
            return [None] * len(texts)
    if selected:
        return _fabric_translate(texts, cfg, mode_id,
            fabric_operation_id=fabric_operation_id if supplied else None,
            fabric_inspection=fabric_inspection if supplied else None)
    client = _client(cfg)
    if client is None:
        return [None] * len(texts)
    batch = max(1, int(cfg.get("batch_size", 20)))
    out: list[str | None] = []
    for i in range(0, len(texts), batch):
        out.extend(_translate_one_batch(client, texts[i:i + batch], cfg))
    return out


# --------------------------------------------------------------------------- #
# The incumbent Fabric application binding — the only transport a SELECTED
# host may use. See the FABRIC_LANE note at the top of this module.
#
# THE SPEND SINK. Under a selected transport the spend is recorded by the
# incumbent llm_auth writer (make_call), NOT by this module's own ai_costs
# write — one writer, one row, never two. A caller that declared
# ``usage_sink: "none"`` keeps that declaration: the owner carries it into the
# bound operation and suppresses only its own repository ledger row.
# --------------------------------------------------------------------------- #
def _fabric_selection(cfg: dict) -> tuple[bool, str | None]:
    """The trusted selection in force -> (selected, mode_id).

    This module keeps NO shadow selector of its own: the incumbent owner's own
    semantics decide. The host environment wins over the caller config; a
    PRESENT but invalid/null/empty value stays SELECTED with no mode id, so the
    module refuses instead of reverting to a native credential; an ABSENT
    selection leaves the legacy path untouched.
    """
    from engine import llm_auth

    try:
        mode_id = llm_auth.application_mode_id(cfg if isinstance(cfg, dict) else {})
    except llm_auth.FabricProviderError:
        return True, None
    if mode_id is None:
        return False, None
    return True, mode_id


def _fabric_factory(cfg: dict, mode_id: str | None):
    """The incumbent owner's factory for the selected mode, or None.

    The owner root is this module's explicit ``config.ROOT`` — never the owner's
    internal repository root: a recipe conversion must not silently retarget
    the root the caller configured.
    """
    if not mode_id:
        return None
    try:
        from engine.provider_production_modes import make_application_fabric_factory
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("translation: Fabric owner unavailable (%s)", e)
        return None
    try:
        return make_application_fabric_factory(
            mode_id=mode_id, lane=FABRIC_LANE, root=config.ROOT,
            workload_cfg={"workload_profile": FABRIC_WORKLOAD_PROFILE,
                          "provider_order": ["fabric"]},
        )
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("translation: Fabric selection failed (%s)", e)
        return None


def _operation_id() -> str:
    """ONE operation identity for ONE logical batch.

    Allocated once, BEFORE the batch's intentional inference steps and outside
    every retry branch: the incumbent client stamps each intentional step with
    it. A later batch allocates its own.
    """
    return f"{FABRIC_LANE}:{uuid.uuid4().hex[:24]}"


def _fabric_provider(factory, cfg: dict, request_id: str) -> dict | None:
    """Compose ONE turn-scoped Fabric provider through the incumbent owner.

    None when the owner refuses: the module degrades to its existing contract
    instead of reaching for a native credential or a direct client. The
    caller's own cfg travels with the binding, so its declared workload
    profile (presence AND value) and its declared spend sink are preserved.
    """
    from engine import llm_auth

    if factory is None:
        return None
    try:
        provider = llm_auth.build_fabric_provider(
            factory, request_id=request_id,
            workload_cfg=cfg if isinstance(cfg, dict) else None)
    except llm_auth.FabricProviderError as exc:
        log.warning("translation: Fabric binding unavailable (%s)", exc.code)
        return None
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("translation: Fabric binding failed (%s)", e)
        return None
    provider["usage_lane"] = "translate-profiles"
    return provider


def _fabric_response_text(resp) -> str:
    """The response's text. Text translation never accepts tools: a tool_use
    block in a translation reply is unsolicited, so the batch is refused rather
    than half-parsed. A truncated reply is refused too — the legacy contract
    already fails a cut-off reply closed, because the batch may be cut
    mid-item and the caller must keep the English.
    """
    if getattr(resp, "stop_reason", None) == "max_tokens":
        raise ValueError("fabric_response_truncated")
    blocks = getattr(resp, "content", None)
    if not isinstance(blocks, list):
        raise ValueError("fabric_content_invalid")
    for block in blocks:
        if getattr(block, "type", "") == "tool_use":
            raise ValueError("fabric_tools_unsolicited")
    return "".join(getattr(b, "text", "") for b in blocks
                   if getattr(b, "type", "") == "text")


def _fabric_call_text(provider: dict, cfg: dict, user: str) -> str | None:
    """ONE Anthropic-shaped batch through the incumbent llm_auth path.

    Returns the reply's text, or None when the operation STOPPED. The
    incumbent wrapper owns the response/model/usage validation, the request
    identity and the uncertainty: an unknown execution, an empty reply, a
    truncated reply or an unsolicited tool ends the operation. This module
    never retries, falls back to another provider or resends.
    """
    from engine import llm_auth

    def _call(client, model):
        resp = client.messages.create(
            model=model,
            max_tokens=int(cfg.get("max_tokens", 4000)),
            system=_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        return _fabric_response_text(resp), None, resp

    try:
        text, _reason, _used = llm_auth.make_call(
            [provider], _call, context="translate-profiles")
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("translation Fabric batch failed (%s) — keeping English", e)
        return None
    return text


def _fabric_fill(provider: dict, cfg: dict, chunk: list[str]) -> list[str | None] | None:
    """One batch; None means the operation stopped (no retry/fallback)."""
    max_chars = int(cfg.get("max_chars", 600))
    payload = [t[:max_chars] for t in chunk]
    user = ("Translate each item of this JSON array to Simplified Chinese and return a "
            "JSON array of the same length and order:\n"
            + json.dumps(payload, ensure_ascii=False))
    text = _fabric_call_text(provider, cfg, user)
    if text is None:
        return None
    arr = _extract_json_array(text)
    if arr is None or len(arr) != len(chunk):
        log.warning("translation Fabric batch malformed (got %s for %d items) — keeping English",
                    None if arr is None else len(arr), len(chunk))
        return None
    # only accept non-empty strings that actually contain CJK; else keep English
    out: list[str | None] = []
    for v in arr:
        s = str(v).strip() if v is not None else ""
        out.append(s if (s and any("一" <= ch <= "鿿" for ch in s)) else None)
    return out


def _fabric_translate(texts: list[str], cfg: dict, mode_id: str | None, *,
                      fabric_operation_id=None, fabric_inspection=None) -> list[str | None]:
    """Translate one logical batch through the incumbent Fabric binding.

    The module's existing contract is preserved: a list aligned to ``texts``
    where a missing translation is None. Batch order, batch count and the
    JSON-array contract are the legacy ones — only the transport changes.
    """
    if mode_id is None:
        # SELECTED with no eligible binding: the honest unavailable contract.
        return [None] * len(texts)
    factory = _fabric_factory(cfg, mode_id)
    if factory is None:
        return [None] * len(texts)
    if fabric_inspection is not None:
        try:
            factory = factory.with_inspection(fabric_inspection)
        except Exception:
            return [None] * len(texts)

    from engine import llm_auth

    request_id = fabric_operation_id if fabric_operation_id is not None else _operation_id()
    provider = None
    operation = None
    try:
        provider = _fabric_provider(factory, cfg, request_id)
        if provider is None:
            return [None] * len(texts)
        operation = llm_auth.begin_operation(
            [provider], operation_id=request_id, context="translate-profiles")
        batch = max(1, int(cfg.get("batch_size", 20)))
        out: list[str | None] = []
        for i in range(0, len(texts), batch):
            chunk = texts[i:i + batch]
            filled = _fabric_fill(provider, cfg, chunk)
            if filled is None:
                # The operation stopped: no retry, no fallback, no invented result.
                out.extend([None] * (len(texts) - i))
                break
            out.extend(filled)
        return out
    finally:
        # EVERY exit closes the bound provider: success, unavailable and
        # exception alike. A local close invalidates the retained reference;
        # it never claims the upstream lease released.
        if operation is not None:
            operation.close()
        elif provider is not None:
            llm_auth.close_fabric_provider(provider)
