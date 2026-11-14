"""Capacity Fabric consumer adapter — Anthropic-Messages-compatible router client.

The Capacity Fabric unified_router speaks the Anthropic Messages API, so an
Anthropic SDK client pointed at it just works. Two things differ from a direct
provider client, and both are load-bearing here:

  1. ``model`` is a LANE (``fabric/fast``, ``fabric/balanced``,
     ``fabric/frontier``, ``fabric/kimi-preferred``, ``auto``) or a bare provider
     slug. The router walks its own ladder of providers behind that lane.
  2. THE ROUTER OWNS FALLBACK. It does provider selection, per-provider
     cooldown and account pooling itself. THIS ADAPTER NEVER RETRIES A FAILOVER
     AND NEVER WALKS A SECOND PROVIDER: one logical call = one request. If the
     router's whole ladder is exhausted it returns the error; the caller degrades.
     Adding a retry or a local fallback ladder here would double-serve calls and
     bill a second provider for an outcome the router already resolved.

Configuration:
  FABRIC_ROUTER_TOKEN     the router's shared secret (required; sent as x-api-key;
                          the gateway accepts Bearer or x-api-key)
  FABRIC_ROUTER_BASE_URL  optional; defaults to http://127.0.0.1:8313.
                          The Anthropic SDK appends /v1/messages itself.
  The router only accepts loopback peers, which the nightly render host is.

Attribution (how fabric usage is attributed to this consumer):
  extra_headers {"x-fabric-client", "x-fabric-session-id", "x-fabric-agent-id",
                 "x-fabric-parent-agent-id", "x-fabric-project-id"}
  extra_body    {"metadata": {"fabric": {...same...}}}

Notes:
  * ``max_tokens`` is REQUIRED — the router uses it for admission.
  * ``betas`` go in a top-level body key (``betas``); an ``anthropic-beta``
    HEADER is NOT forwarded upstream by the gateway.
  * ``metadata.task_complexity`` is honoured only when the model is ``auto``;
    for a lane model the difficulty has already been resolved to a lane here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

DEFAULT_BASE_URL = "http://127.0.0.1:8313"
TOKEN_ENV = "FABRIC_ROUTER_TOKEN"
BASE_URL_ENV = "FABRIC_ROUTER_BASE_URL"

# The closed set the router's attribution census understands. Anything else is a
# caller bug, so it is rejected instead of silently landing as "Unknown client".
CLIENTS: frozenset[str] = frozenset({
    "T3",
    "Paperclip",
    "Hermes",
    "Subagent Fabric",
    "Claude SDK",
    "OpenAI SDK",
    "Python client",
    "Unknown client",
})
DEFAULT_CLIENT = "Python client"

# provider prefix -> concrete model slug. A bare slug also works (it switches the
# provider outright rather than walking a lane).
_PROVIDER_MODELS: dict[str, str] = {
    "deepseek": "deepseek-v4.1-flash",
    "glm": "glm-5.3",
    "kimi": "kimi-k3.1-pro",
    "qwen": "qwen3.8-max",
    "claude": "claude-opus-5-5",
    "gpt": "gpt-6.1-sol",
}

# difficulty bucket -> lane. Difficulty is resolved CLIENT-SIDE because the router
# only consults metadata.task_complexity for model == "auto".
_DIFFICULTY_LANES: dict[str, str] = {
    "flash": "fabric/fast",
    "easy": "fabric/fast",
    "fast": "fabric/fast",
    "balanced": "fabric/balanced",
    "medium": "fabric/balanced",
    "frontier": "fabric/frontier",
    "hard": "fabric/frontier",
}

# short lane name -> lane id as the router spells it.
_LANES: dict[str, str] = {
    "fast": "fabric/fast",
    "balanced": "fabric/balanced",
    "frontier": "fabric/frontier",
    "kimi": "fabric/kimi-preferred",
    "auto": "auto",
}
_LANE_IDS: frozenset[str] = frozenset(_LANES.values()) | frozenset({"fabric/kimi-preferred"})

# concrete slug -> provider. Used only as a fallback for `Completion.provider`
# when the router did not send its own provider header; an unknown slug stays
# None rather than being guessed.
_SLUG_PROVIDERS: dict[str, str] = {v: k for k, v in _PROVIDER_MODELS.items()}

# Response headers the router actually sets on a routed reply. Read from the
# RUNNING gateway (pid cwd release model-tier-20261111-peak-…-obs-d4ee4ad515d4,
# ops/native_fabric/unified_router/gateway.py ~L946-949, verified 2026-11-12):
#   response.headers["x-fabric-resolved-model"] = resolved
#   response.headers["x-fabric-route"]          = route.route_id
#   response.headers["x-fabric-routing-policy"] = VERSION
#   response.headers["x-fabric-request-id"]     = nonce
# The resolved-model header is "x-fabric-resolved-model" on EVERY release in the
# estate (no release emits "x-fabric-model"); the body's ``model`` field is the
# upstream provider's own name, which can differ from the gateway slug, so the
# header is the authoritative served-model source. The "-model"/"-id"/"-provider"
# spellings are kept as fallbacks for stub routers and any older gateway; the
# live ones come first so production attribution is never blank.
_ROUTE_HEADERS = ("x-fabric-route", "x-fabric-route-id")
_MODEL_HEADERS = ("x-fabric-resolved-model", "x-fabric-model")
_PROVIDER_HEADERS = ("x-fabric-provider",)


class FabricUnavailable(RuntimeError):
    """The router cannot be reached AT ALL — no token, or the SDK will not load.

    This is deliberately distinct from a served call that failed. A caller that
    has a working fallback should catch this and use the fallback; catching it
    as an ordinary failure would blank output that a healthy legacy path could
    still produce. It is NOT used for errors the router returns: those mean the
    router's own ladder was already walked, and a local retry is forbidden.
    """


@dataclass
class Completion:
    """One router completion.

    ``model_served`` is what the router actually ran (it may differ from the
    requested lane member); ``route_id``/``provider`` are best-effort and stay
    None when the gateway did not report them. ``provider`` falls back to the
    provider owning the served slug when no provider header was sent, so the
    cost ledger can still attribute the call.
    """

    text: str
    model_served: str | None
    route_id: str | None = None
    provider: str | None = None
    usage: dict = field(default_factory=dict)
    raw: Any = None


def is_configured() -> bool:
    """True iff a router token is present. Never raises."""
    return bool((os.environ.get(TOKEN_ENV) or "").strip())


def resolve_model(*, lane: str | None = None, difficulty: str | None = None,
                  provider: str | None = None, model: str | None = None) -> str:
    """Resolve the ``model`` request field.

    Precedence: explicit ``model`` > ``provider`` > ``difficulty`` > ``lane``
    (default lane ``fast``). Unknown provider/difficulty/lane raises ValueError
    so a typo fails loudly instead of silently landing on fast.
    """
    if model:
        return str(model)
    if provider:
        key = str(provider).strip().lower()
        if key not in _PROVIDER_MODELS:
            raise ValueError(
                f"unknown fabric provider {provider!r}; "
                f"expected one of {sorted(_PROVIDER_MODELS)}")
        return _PROVIDER_MODELS[key]
    if difficulty:
        key = str(difficulty).strip().lower()
        if key not in _DIFFICULTY_LANES:
            raise ValueError(
                f"unknown fabric difficulty {difficulty!r}; "
                f"expected one of {sorted(_DIFFICULTY_LANES)}")
        return _DIFFICULTY_LANES[key]
    key = str(lane or "fast").strip().lower()
    if key in _LANES:
        return _LANES[key]
    if key in _LANE_IDS:
        return key
    raise ValueError(
        f"unknown fabric lane {lane!r}; expected one of {sorted(_LANES)}")


def _make_client(base_url: str, timeout: float):
    """Build the SDK client. Imported lazily so this module is importable on a
    host without the anthropic package (the adapter is default-off)."""
    token = (os.environ.get(TOKEN_ENV) or "").strip()
    if not token:
        raise FabricUnavailable(f"{TOKEN_ENV} is not set; fabric router is not configured")
    try:
        import anthropic  # noqa: PLC0415 — lazy: optional dependency at import time
    except ImportError as e:
        raise FabricUnavailable(
            f"the anthropic SDK is not importable ({e}); the fabric router "
            f"cannot be reached from this host") from e

    return anthropic.Anthropic(base_url=base_url, api_key=token, timeout=timeout)


def _attribution(client: str, session_id: str | None, agent_id: str | None,
                 parent_agent_id: str | None, project_id: str | None,
                 ) -> tuple[dict[str, str], dict[str, Any]]:
    """Build the (extra_headers, metadata.fabric) pair for one call."""
    if client not in CLIENTS:
        raise ValueError(
            f"unknown fabric client {client!r}; expected one of {sorted(CLIENTS)}")
    fabric: dict[str, Any] = {"client": client}
    if session_id:
        fabric["session_id"] = str(session_id)
    if agent_id:
        fabric["agent_id"] = str(agent_id)
    if parent_agent_id:
        fabric["parent_agent_id"] = str(parent_agent_id)
    if project_id:
        fabric["project_id"] = str(project_id)
    headers = {
        "x-fabric-client": client,
        "x-fabric-session-id": str(session_id or ""),
        "x-fabric-agent-id": str(agent_id or ""),
        "x-fabric-parent-agent-id": str(parent_agent_id or ""),
        "x-fabric-project-id": str(project_id or ""),
    }
    return headers, fabric


def _request_kwargs(messages: Sequence[Mapping[str, Any]], *,
                    system: str | None, lane: str | None, difficulty: str | None,
                    provider: str | None, model: str | None, max_tokens: int,
                    client: str, session_id: str | None, agent_id: str | None,
                    parent_agent_id: str | None, project_id: str | None,
                    temperature: float | None, betas: Iterable[str] | None,
                    task_complexity: str | None) -> dict[str, Any]:
    resolved = resolve_model(lane=lane, difficulty=difficulty,
                             provider=provider, model=model)
    headers, fabric = _attribution(client, session_id, agent_id,
                                  parent_agent_id, project_id)
    extra_body: dict[str, Any] = {"metadata": {"fabric": fabric}}
    # task_complexity is only consulted by the router for model == "auto"; for a
    # lane model difficulty has already been resolved to the lane above.
    if resolved == "auto" and task_complexity:
        extra_body["metadata"]["task_complexity"] = str(task_complexity)
    if betas:
        # Top-level BODY key. The gateway does not forward the anthropic-beta
        # header upstream, so a header would be dropped silently.
        extra_body["betas"] = list(betas)
    kw: dict[str, Any] = {
        "model": resolved,
        "max_tokens": int(max_tokens),
        "messages": list(messages),
        "extra_headers": headers,
        "extra_body": extra_body,
    }
    if system is not None:
        kw["system"] = system
    if temperature is not None:
        kw["temperature"] = temperature
    return kw


def _single_request(sdk: Any, kw: dict) -> tuple[Any, Mapping[str, str] | None]:
    """Perform the adapter's ONE request and return (message, response headers).

    ``with_raw_response`` is preferred because the gateway reports its routing
    decision in headers (``x-fabric-route`` / ``x-fabric-resolved-model``, see
    ``_ROUTE_HEADERS``) and the parsed Message does NOT retain them. Measured
    against anthropic 2.8.0 (2026-11-12): a plain ``messages.create()`` leaves
    ``msg._response`` as None, so reading headers off the message silently
    yielded None for every call — the attribution we report was always blank.
    The raw-response wrapper exposes the real HTTP headers and ``.parse()``
    returns the same Message.

    Falls back to the plain call for any SDK/client that lacks the wrapper;
    attribution then degrades to None rather than failing a served call.
    """
    raw_api = getattr(getattr(sdk, "messages", None), "with_raw_response", None)
    create_raw = getattr(raw_api, "create", None)
    if callable(create_raw):
        response = create_raw(**kw)
        parse = getattr(response, "parse", None)
        if callable(parse):
            headers = getattr(response, "headers", None)
            return parse(), headers
    return sdk.messages.create(**kw), None


def complete(messages: Sequence[Mapping[str, Any]], *,
             system: str | None = None,
             lane: str | None = "fast",
             difficulty: str | None = None,
             provider: str | None = None,
             model: str | None = None,
             max_tokens: int = 2048,
             client: str = DEFAULT_CLIENT,
             session_id: str | None = None,
             agent_id: str | None = None,
             parent_agent_id: str | None = None,
             project_id: str | None = None,
             base_url: str | None = None,
             timeout: float = 120.0,
             temperature: float | None = None,
             betas: Iterable[str] | None = None,
             task_complexity: str | None = None) -> Completion:
    """ONE completion through the router. Never retries, never fails over.

    The router owns provider selection, cooldown and pooling; a raised SDK error
    is handed straight back to the caller (no second request).
    """
    kw = _request_kwargs(
        messages, system=system, lane=lane, difficulty=difficulty,
        provider=provider, model=model, max_tokens=max_tokens, client=client,
        session_id=session_id, agent_id=agent_id,
        parent_agent_id=parent_agent_id, project_id=project_id,
        temperature=temperature, betas=betas, task_complexity=task_complexity)
    sdk = _make_client(
        base_url or (os.environ.get(BASE_URL_ENV) or "").strip() or DEFAULT_BASE_URL,
        timeout)
    msg, headers = _single_request(sdk, kw)   # <- the single attempt
    return _completion_from(msg, headers)


def stream(messages: Sequence[Mapping[str, Any]], *,
           system: str | None = None,
           lane: str | None = "fast",
           difficulty: str | None = None,
           provider: str | None = None,
           model: str | None = None,
           max_tokens: int = 2048,
           client: str = DEFAULT_CLIENT,
           session_id: str | None = None,
           agent_id: str | None = None,
           parent_agent_id: str | None = None,
           project_id: str | None = None,
           base_url: str | None = None,
           timeout: float = 120.0,
           temperature: float | None = None,
           betas: Iterable[str] | None = None,
           task_complexity: str | None = None) -> Iterator[str]:
    """Yield text deltas from one SSE pass-through call. Never retries."""
    kw = _request_kwargs(
        messages, system=system, lane=lane, difficulty=difficulty,
        provider=provider, model=model, max_tokens=max_tokens, client=client,
        session_id=session_id, agent_id=agent_id,
        parent_agent_id=parent_agent_id, project_id=project_id,
        temperature=temperature, betas=betas, task_complexity=task_complexity)
    kw["stream"] = True
    sdk = _make_client(
        base_url or (os.environ.get(BASE_URL_ENV) or "").strip() or DEFAULT_BASE_URL,
        timeout)
    with sdk.messages.create(**kw) as events:
        for event in events:
            if getattr(event, "type", None) != "content_block_delta":
                continue
            delta = getattr(event, "delta", None)
            text = getattr(delta, "text", None)
            if text:
                yield text


def _header(msg: Any, name: str,
            headers: Mapping[str, str] | None = None) -> str | None:
    """Best-effort response-header read.

    ``headers`` is what ``_single_request`` captured from the raw response and is
    the reliable path; ``msg._response`` is kept for SDKs that attach the
    response to the parsed message. Returns None rather than raising — an
    attribution miss must never break a call that otherwise succeeded.
    """
    source = headers if headers is not None else getattr(
        getattr(msg, "_response", None), "headers", None)
    if source is None:
        return None
    try:
        value = source.get(name)
    except Exception:  # noqa: BLE001 — attribution must never break a served call
        return None
    return str(value) if value else None


def _first_header(msg: Any, names: Sequence[str],
                  headers: Mapping[str, str] | None = None) -> str | None:
    """First non-empty value among ``names``. None when none is present."""
    for name in names:
        value = _header(msg, name, headers)
        if value:
            return value
    return None


def _usage_dict(msg: Any) -> dict:
    usage = getattr(msg, "usage", None)
    if usage is None:
        return {}
    for method in ("model_dump", "dict"):
        fn = getattr(usage, method, None)
        if callable(fn):
            try:
                out = fn()
                if isinstance(out, dict):
                    return out
            except Exception:  # noqa: BLE001
                pass
    try:
        return dict(vars(usage))
    except Exception:  # noqa: BLE001
        return {}


def _completion_from(msg: Any,
                    headers: Mapping[str, str] | None = None) -> Completion:
    blocks = getattr(msg, "content", None) or []
    text = "".join(
        getattr(b, "text", "") for b in blocks
        if getattr(b, "type", "") == "text")
    model_served = (_first_header(msg, _MODEL_HEADERS, headers)
                    or getattr(msg, "model", None))
    route_id = _first_header(msg, _ROUTE_HEADERS, headers)
    provider = (_first_header(msg, _PROVIDER_HEADERS, headers)
                or _SLUG_PROVIDERS.get(model_served or ""))
    return Completion(
        text=text,
        model_served=model_served,
        route_id=route_id,
        provider=provider,
        usage=_usage_dict(msg),
        raw=msg,
    )
