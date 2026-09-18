"""Metered production API usage modes for the Shared AI Provider Control program.

WHY THIS EXISTS
---------------
``mastermind.provider_capacity.v1`` describes the twelve SUBSCRIPTION slots the
fleet already runs on (``engine/provider_capacity.py``), and ``#7103`` describes
subscription PLANS whose backgrounds are explicitly forbidden from production
(``production_backend_allowed=false``).  Neither is a metered, per-token
production lane: MiniMax's Anthropic-compatible PAYG API and Z.ai's GLM PaaS v4
OpenAI-compatible API are separate products with separate keys, separate
billing, and separate cost identity.

This module is that seam and nothing more.  It is a closed, reviewable config
plus a loader, a resolution step and a call step.  It deliberately does NOT
touch the OAuth/Codex subscription waterfall, ``build_providers``, the twelve
capacity slots, or the ``#7103`` plan catalog.

CONTRACT
--------
* Closed set: an unknown key, an unknown protocol, a non-``production_api``
  ``usage_class``, a non-``metered`` ``billing_mode``, a truthy
  ``subscription_fallback_allowed``, an ``enabled`` that is not a bool, or a
  ``secret_ref`` that is not an env-var NAME is a hard config error.
* Secret NAMES only.  ``secret_ref`` is resolved against the environment at
  call time; the VALUE is never stored, logged, returned, or receipted.  A
  config string that looks like a secret value is a hard config error.
* Shadow/off by default.  Every mode ships ``enabled=false``; a disabled or
  unconfigured mode makes NO transport call, and the receipt says why.
* No subscription fallback, ever.  A production mode that cannot run returns
  ``fallback="none"`` rather than borrowing an OAuth or Codex rung.  This
  module never imports :mod:`engine.llm_auth`.
* Bounded failure: :func:`call_mode` never raises on provider failure and
  always returns a receipt whose ``error_class`` is drawn from
  :data:`ERROR_CLASSES`.
* Receipts go through the existing writers unchanged —
  :func:`engine.provider_health.record_attempt` and
  :func:`lib.ai_costs.record_usage`.  Tests must redirect their state roots
  (``PROVIDER_HEALTH_PATH`` / ``AI_COSTS_STATE_ROOT``) or patch the writer
  functions; a sparse worktree must never be written into.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from engine import provider_health
from lib import ai_costs

log = logging.getLogger(__name__)

SCHEMA = "mastermind.provider_production_modes.v1"
PRODUCER_PROGRAM = "shared-ai-provider-control"

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "provider_production_modes.v1.json"

#: Ledger lane for every row this module emits.
LANE = "provider_production_modes"

#: Matches ``earnings_qual._call_openai_compat``'s own default (120 s).
DEFAULT_TIMEOUT_S = 120.0

PROTOCOL_ANTHROPIC = "anthropic_compat"
PROTOCOL_OPENAI = "openai_compat"
PROTOCOLS = (PROTOCOL_ANTHROPIC, PROTOCOL_OPENAI)

PRODUCTION_USAGE_CLASS = "production_api"
METERED_BILLING_MODE = "metered"
CAP_ID_PREFIX = "prod_api:"

ERROR_CLASSES = frozenset({
    "none",
    "disabled",
    "unconfigured",
    "http_4xx",
    "http_5xx",
    "timeout",
    "empty",
    "transport_error",
})

SECRET_REF_RE = re.compile(r"^[A-Z][A-Z0-9_]{3,63}$")
MODE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
CAP_ID_RE = re.compile(r"^prod_api:[a-z][a-z0-9_]{1,31}$")

_TOP_LEVEL_KEYS = frozenset({"schema", "producer_program", "modes"})
_REQUIRED_RECORD_KEYS = frozenset({
    "provider_id",
    "protocol",
    "base_url",
    "default_model",
    "secret_ref",
    "usage_class",
    "billing_mode",
    "cost_identity",
    "cap_id",
    "enabled",
    "subscription_fallback_allowed",
})
_OPTIONAL_RECORD_KEYS = frozenset({"docs_ref", "pricing_ref", "notes"})

#: Provider ids that name a SUBSCRIPTION rung.  A metered production mode may
#: never masquerade as one of these — that is the fallback this module exists
#: to make impossible.
_FORBIDDEN_PROVIDER_IDS = frozenset({
    "oauth",
    "codex",
    "claude",
    "claude_code_oauth",
    "claude_oauth",
    "anthropic_oauth",
})

#: A config value that matches one of these is a secret VALUE, not a NAME.
_SECRET_VALUE_PATTERNS = (
    re.compile(r"^(sk|pk|rk|hf|ghp|gho|ghs|xox[baprs]|glpat|AKIA)[-_A-Za-z0-9]{6,}$"),
    re.compile(r"^eyJ[A-Za-z0-9_\-]{8,}\."),
    re.compile(r"^[A-Fa-f0-9]{32,}$"),
    re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$"),
)


class ProductionModeConfigError(ValueError):
    """The production-mode config is not the closed set this module accepts."""


@dataclass(frozen=True)
class ProductionMode:
    """One metered production API usage mode, as declared in the config."""

    mode_id: str
    provider_id: str
    protocol: str
    base_url: str
    default_model: str
    secret_ref: str
    usage_class: str
    billing_mode: str
    cost_identity: str
    cap_id: str
    enabled: bool
    subscription_fallback_allowed: bool
    docs_ref: str = ""
    pricing_ref: str = ""
    notes: str = ""

    @property
    def ledger_provider(self) -> str:
        """Provider label for :func:`lib.ai_costs.record_usage`."""
        return self.cost_identity.split("/", 1)[0]

    @property
    def ledger_cost_basis(self) -> str:
        """Cost basis for :func:`lib.ai_costs.record_usage`."""
        return self.cost_identity.split("/", 1)[1]


@dataclass(frozen=True)
class ModeStatus:
    """Resolved configuration state.  Carries the secret NAME, never a value."""

    mode_id: str
    provider_id: str
    protocol: str
    model: str
    secret_ref: str
    usage_class: str
    billing_mode: str
    cost_identity: str
    cap_id: str
    enabled: bool
    state: str


@dataclass(frozen=True)
class TransportOutcome:
    """What a transport hands back, before classification.

    ``reason`` is the provider's own free-form failure string; it is mapped by
    :func:`_classify_reason` and is never surfaced to a caller verbatim.
    """

    text: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    reason: str | None = None
    status_code: int | None = None


#: Injectable transport.  Called keyword-only; may return a
#: :class:`TransportOutcome`, a raw provider payload dict, a ``(text, reason)``
#: or ``(text, usage, reason)`` tuple, a plain string, or ``None``.
Transport = Callable[..., Any]


@dataclass(frozen=True)
class ProductionCallReceipt:
    """The single outcome record of one :func:`call_mode` attempt."""

    provider_id: str
    mode_id: str
    model: str
    protocol: str
    ok: bool
    text: str | None
    input_tokens: int | None
    output_tokens: int | None
    error_class: str
    latency_ms: int
    cost_identity: str
    fallback: str
    cap_id: str
    state: str


def _looks_like_secret_value(value: str) -> bool:
    return any(pattern.match(value) for pattern in _SECRET_VALUE_PATTERNS)


def _require_str(raw: Mapping[str, Any], key: str, mode_id: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: {key!r} must be a non-empty string"
        )
    value = value.strip()
    if key != "notes" and _looks_like_secret_value(value):
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: {key!r} looks like a secret VALUE; only env-var NAMES are allowed"
        )
    return value


def _require_bool(raw: Mapping[str, Any], key: str, mode_id: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: {key!r} must be a JSON boolean, got {type(value).__name__}"
        )
    return value


def _validate_record(mode_id: str, raw: Any) -> ProductionMode:
    if not isinstance(raw, dict):
        raise ProductionModeConfigError(f"mode {mode_id!r}: record must be an object")

    unknown = sorted(set(raw) - _REQUIRED_RECORD_KEYS - _OPTIONAL_RECORD_KEYS)
    if unknown:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: unknown key(s) {unknown} — closed set"
        )
    missing = sorted(_REQUIRED_RECORD_KEYS - set(raw))
    if missing:
        raise ProductionModeConfigError(f"mode {mode_id!r}: missing key(s) {missing}")

    provider_id = _require_str(raw, "provider_id", mode_id)
    protocol = _require_str(raw, "protocol", mode_id)
    base_url = _require_str(raw, "base_url", mode_id)
    default_model = _require_str(raw, "default_model", mode_id)
    secret_ref = _require_str(raw, "secret_ref", mode_id)
    usage_class = _require_str(raw, "usage_class", mode_id)
    billing_mode = _require_str(raw, "billing_mode", mode_id)
    cost_identity = _require_str(raw, "cost_identity", mode_id)
    cap_id = _require_str(raw, "cap_id", mode_id)
    enabled = _require_bool(raw, "enabled", mode_id)
    fallback_allowed = _require_bool(raw, "subscription_fallback_allowed", mode_id)
    docs_ref = raw.get("docs_ref", "") or ""
    pricing_ref = raw.get("pricing_ref", "") or ""
    notes = raw.get("notes", "") or ""
    for key, value in (("docs_ref", docs_ref), ("pricing_ref", pricing_ref), ("notes", notes)):
        if not isinstance(value, str):
            raise ProductionModeConfigError(
                f"mode {mode_id!r}: {key!r} must be a string when present"
            )

    if not PROVIDER_ID_RE.match(provider_id):
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: provider_id must match {PROVIDER_ID_RE.pattern}"
        )
    if provider_id in _FORBIDDEN_PROVIDER_IDS:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: provider_id {provider_id!r} names a subscription rung; "
            "production modes are metered providers only"
        )
    if protocol not in PROTOCOLS:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: protocol must be one of {PROTOCOLS}, got {protocol!r}"
        )
    if usage_class != PRODUCTION_USAGE_CLASS:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: usage_class must be {PRODUCTION_USAGE_CLASS!r}"
        )
    if billing_mode != METERED_BILLING_MODE:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: billing_mode must be {METERED_BILLING_MODE!r}"
        )
    if fallback_allowed:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: subscription_fallback_allowed must be false; "
            "a production mode never borrows a subscription rung"
        )
    if not SECRET_REF_RE.match(secret_ref):
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: secret_ref must be an env-var NAME matching "
            f"{SECRET_REF_RE.pattern}"
        )
    if cost_identity != f"{provider_id}/{METERED_BILLING_MODE}":
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: cost_identity must be {provider_id!r} + '/metered'"
        )
    if not CAP_ID_RE.match(cap_id) or cap_id != f"{CAP_ID_PREFIX}{provider_id}":
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: cap_id must be {CAP_ID_PREFIX}{provider_id}"
        )
    if not base_url.startswith("https://") or "@" in base_url or "?" in base_url:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: base_url must be a plain https endpoint with no userinfo or query"
        )

    return ProductionMode(
        mode_id=mode_id,
        provider_id=provider_id,
        protocol=protocol,
        base_url=base_url,
        default_model=default_model,
        secret_ref=secret_ref,
        usage_class=usage_class,
        billing_mode=billing_mode,
        cost_identity=cost_identity,
        cap_id=cap_id,
        enabled=enabled,
        subscription_fallback_allowed=fallback_allowed,
        docs_ref=docs_ref,
        pricing_ref=pricing_ref,
        notes=notes,
    )


def load_modes(path: str | Path | None = None) -> dict[str, ProductionMode]:
    """Load and validate the closed production-mode config.

    Raises :class:`ProductionModeConfigError` on any deviation.  Returns a
    dict keyed by ``mode_id``.
    """
    cfg_path = Path(path) if path is not None else DEFAULT_PATH
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProductionModeConfigError(f"production modes config missing: {cfg_path}") from exc
    except json.JSONDecodeError as exc:
        raise ProductionModeConfigError(f"production modes config is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ProductionModeConfigError("production modes config must be a JSON object")
    unknown = sorted(set(raw) - _TOP_LEVEL_KEYS)
    if unknown:
        raise ProductionModeConfigError(f"unknown top-level key(s) {unknown} — closed set")
    missing = sorted(_TOP_LEVEL_KEYS - set(raw))
    if missing:
        raise ProductionModeConfigError(f"missing top-level key(s) {missing}")
    if raw["schema"] != SCHEMA:
        raise ProductionModeConfigError(f"schema must be {SCHEMA!r}, got {raw['schema']!r}")
    if raw["producer_program"] != PRODUCER_PROGRAM:
        raise ProductionModeConfigError(f"producer_program must be {PRODUCER_PROGRAM!r}")

    modes_raw = raw["modes"]
    if not isinstance(modes_raw, dict) or not modes_raw:
        raise ProductionModeConfigError("modes must be a non-empty object keyed by mode_id")
    out: dict[str, ProductionMode] = {}
    for mode_id, record in modes_raw.items():
        if not isinstance(mode_id, str) or not MODE_ID_RE.match(mode_id):
            raise ProductionModeConfigError(f"mode_id {mode_id!r} is not a valid id")
        out[mode_id] = _validate_record(mode_id, record)
    return out


def _mode(mode_id: str, path: str | Path | None = None) -> ProductionMode:
    modes = load_modes(path)
    try:
        return modes[mode_id]
    except KeyError as exc:
        raise ProductionModeConfigError(
            f"unknown production mode {mode_id!r}; known: {sorted(modes)}"
        ) from exc


def _env_name_present(env: Mapping[str, str], name: str) -> bool:
    value = env.get(name)
    return isinstance(value, str) and value.strip() != ""


def resolve_mode(mode_id: str, env: Mapping[str, str] | None = None) -> ModeStatus:
    """Resolve ``mode_id`` to ``disabled`` / ``unconfigured`` / ``configured``.

    Reads only PRESENCE of the secret env var.  The value is never read into
    this module's state and never returned.
    """
    mode = _mode(mode_id)
    source: Mapping[str, str] = os.environ if env is None else env
    if not mode.enabled:
        state = "disabled"
    elif not _env_name_present(source, mode.secret_ref):
        state = "unconfigured"
    else:
        state = "configured"
    return ModeStatus(
        mode_id=mode.mode_id,
        provider_id=mode.provider_id,
        protocol=mode.protocol,
        model=mode.default_model,
        secret_ref=mode.secret_ref,
        usage_class=mode.usage_class,
        billing_mode=mode.billing_mode,
        cost_identity=mode.cost_identity,
        cap_id=mode.cap_id,
        enabled=mode.enabled,
        state=state,
    )


def normalize_openai_response(payload: Any) -> TransportOutcome:
    """Normalize an OpenAI-compatible payload to a :class:`TransportOutcome`."""
    if not isinstance(payload, dict):
        return TransportOutcome(reason="empty")
    text: str | None = None
    try:
        choices = payload.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if content:
                text = str(content)
    except (AttributeError, IndexError, TypeError, KeyError):
        return TransportOutcome(reason="bad_shape")
    if not text:
        return TransportOutcome(reason="empty")
    usage = payload.get("usage") or {}
    return TransportOutcome(
        text=text,
        input_tokens=_int_or_none(_usage_field(usage, "prompt_tokens")),
        output_tokens=_int_or_none(_usage_field(usage, "completion_tokens")),
    )


def normalize_anthropic_response(payload: Any) -> TransportOutcome:
    """Normalize an Anthropic-shaped payload to a :class:`TransportOutcome`."""
    if not isinstance(payload, dict):
        return TransportOutcome(reason="empty")
    blocks = payload.get("content") or []
    parts: list[str] = []
    try:
        for block in blocks:
            if isinstance(block, dict):
                part = block.get("text")
            else:
                part = getattr(block, "text", None)
            if part:
                parts.append(str(part))
    except (AttributeError, TypeError):
        return TransportOutcome(reason="bad_shape")
    if not parts:
        return TransportOutcome(reason="empty")
    usage = payload.get("usage") or {}
    return TransportOutcome(
        text="".join(parts),
        input_tokens=_int_or_none(_usage_field(usage, "input_tokens")),
        output_tokens=_int_or_none(_usage_field(usage, "output_tokens")),
    )


def _usage_field(usage: Any, key: str) -> Any:
    if isinstance(usage, dict):
        return usage.get(key)
    return getattr(usage, key, None)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_outcome(value: Any) -> TransportOutcome:
    """Accept the documented transport return shapes and normalize them."""
    if isinstance(value, TransportOutcome):
        return value
    if value is None:
        return TransportOutcome(reason="empty")
    if isinstance(value, str):
        return TransportOutcome(text=value) if value else TransportOutcome(reason="empty")
    if isinstance(value, dict):
        if "error" in value and "choices" not in value and "content" not in value:
            return TransportOutcome(reason=str(value.get("error") or "transport_error"))
        if "choices" in value:
            return normalize_openai_response(value)
        if "content" in value:
            return normalize_anthropic_response(value)
        text = value.get("text")
        if text or value.get("reason") or value.get("status_code"):
            return TransportOutcome(
                text=str(text) if text else None,
                input_tokens=_int_or_none(value.get("input_tokens")),
                output_tokens=_int_or_none(value.get("output_tokens")),
                reason=str(value["reason"]) if value.get("reason") else None,
                status_code=_int_or_none(value.get("status_code")),
            )
        return TransportOutcome(reason="empty")
    if isinstance(value, tuple):
        if len(value) == 2:
            text, reason = value
            return TransportOutcome(
                text=str(text) if text else None,
                reason=str(reason) if reason else None,
            )
        if len(value) == 3:
            text, usage, reason = value
            tokens = usage if isinstance(usage, dict) else {}
            return TransportOutcome(
                text=str(text) if text else None,
                input_tokens=_int_or_none(tokens.get("prompt_tokens", tokens.get("input_tokens"))),
                output_tokens=_int_or_none(tokens.get("completion_tokens", tokens.get("output_tokens"))),
                reason=str(reason) if reason else None,
            )
    return TransportOutcome(reason="transport_error")


def _status_to_error_class(status: int) -> str:
    if 400 <= status < 500:
        return "http_4xx"
    if 500 <= status < 600:
        return "http_5xx"
    return "transport_error"


def _classify_reason(reason: str) -> str:
    """Map a provider reason string to a bounded error class, conservatively."""
    text = (reason or "").strip().lower()
    if not text:
        return "transport_error"
    if "timeout" in text or "timed_out" in text:
        return "timeout"
    match = re.search(r"http[_ -]?(\d{3})", text)
    if match:
        return _status_to_error_class(int(match.group(1)))
    if "empty" in text or "no_content" in text:
        return "empty"
    return "transport_error"


def _reason_from_exception(exc: BaseException) -> str:
    """Map an SDK/client exception to the same free-form reason vocabulary."""
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if isinstance(status, bool):
        return "transport_error"
    if isinstance(status, int):
        return f"http_{status}"
    if "ratelimit" in name:
        return "http_429"
    return "transport_error"


def _glm_transport(
    mode: ProductionMode,
    system: str,
    user: str,
    *,
    max_tokens: int,
    timeout_s: float,
) -> TransportOutcome:
    """GLM through the EXISTING ``earnings_qual._call_openai_compat`` (unchanged)."""
    from engine import earnings_qual  # noqa: PLC0415 — one-time import, kept lazy

    oc_cfg = {
        "base_url": mode.base_url,
        "api_key_env": mode.secret_ref,
        "model": mode.default_model,
        "timeout_s": timeout_s,
    }
    call = getattr(earnings_qual, "_call_openai_compat")
    outcome = _coerce_outcome(call(system, user, oc_cfg, max_tokens=max_tokens))
    # The helper returns no usage block, so token counts stay UNKNOWN here
    # rather than being invented from a character ratio.
    return TransportOutcome(text=outcome.text, reason=outcome.reason)


def _message_to_payload(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        return message
    content = []
    for block in getattr(message, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            content.append({"text": text})
    usage = getattr(message, "usage", None)
    return {
        "content": content,
        "usage": {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        },
    }


def _minimax_transport(
    mode: ProductionMode,
    system: str,
    user: str,
    *,
    max_tokens: int,
    timeout_s: float,
) -> TransportOutcome:
    """MiniMax PAYG through the Anthropic SDK at the mode's own ``base_url``."""
    try:
        import anthropic  # noqa: PLC0415
    except ImportError:
        return TransportOutcome(reason="sdk_unavailable")

    api_key = os.environ.get(mode.secret_ref, "")
    if not api_key:
        # Defensive: ``resolve_mode`` gates this, so reaching here means the
        # environment changed underneath the call.
        return TransportOutcome(reason="unconfigured")
    try:
        client = anthropic.Anthropic(api_key=api_key, base_url=mode.base_url)
        message = client.messages.create(
            model=mode.default_model,
            max_tokens=int(max_tokens),
            system=system,
            messages=[{"role": "user", "content": user}],
            timeout=timeout_s,
        )
    except BaseException as exc:  # noqa: BLE001 — classified below, never re-raised
        return TransportOutcome(reason=_reason_from_exception(exc))
    return normalize_anthropic_response(_message_to_payload(message))


def _default_transport(
    *,
    mode: ProductionMode,
    system: str,
    user: str,
    max_tokens: int,
    timeout_s: float,
) -> TransportOutcome:
    if mode.protocol == PROTOCOL_OPENAI:
        return _glm_transport(mode, system, user, max_tokens=max_tokens, timeout_s=timeout_s)
    if mode.protocol == PROTOCOL_ANTHROPIC:
        return _minimax_transport(mode, system, user, max_tokens=max_tokens, timeout_s=timeout_s)
    return TransportOutcome(reason="unknown_protocol")


def _emit_attempt(
    status: ModeStatus,
    *,
    ok: bool,
    latency_ms: int,
    error_class: str,
    model: str | None = None,
) -> None:
    """One health row per attempt, skips included.  Telemetry never raises."""
    try:
        provider_health.record_attempt(
            lane=LANE,
            context=status.mode_id,
            rung=status.provider_id,
            ok=ok,
            latency_ms=latency_ms,
            cap_id=status.cap_id,
            model=model or status.model,
            error_class="" if ok else error_class,
        )
    except Exception as exc:  # noqa: BLE001 — telemetry must not cost a call
        log.warning("provider_production_modes: health receipt failed (%s)", exc)


def _emit_usage(
    status: ModeStatus,
    *,
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> None:
    """One cost row, only when BOTH token counts are known.  Never raises."""
    try:
        provider, cost_basis = status.cost_identity.split("/", 1)
        ai_costs.record_usage(
            lane=LANE,
            provider=provider,
            model=model,
            key_id=status.cap_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_basis=cost_basis,
            note="provider_production_modes",
        )
    except Exception as exc:  # noqa: BLE001 — telemetry must not cost a call
        log.warning("provider_production_modes: cost receipt failed (%s)", exc)


def _receipt(
    status: ModeStatus,
    *,
    ok: bool,
    text: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    error_class: str,
    latency_ms: int,
) -> ProductionCallReceipt:
    return ProductionCallReceipt(
        provider_id=status.provider_id,
        mode_id=status.mode_id,
        model=status.model,
        protocol=status.protocol,
        ok=ok,
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        error_class=error_class,
        latency_ms=max(0, int(latency_ms)),
        cost_identity=status.cost_identity,
        fallback="none",
        cap_id=status.cap_id,
        state=status.state,
    )


def call_mode(
    mode_id: str,
    system: str,
    user: str,
    *,
    max_tokens: int,
    env: Mapping[str, str] | None = None,
    transport: Transport | None = None,
) -> ProductionCallReceipt:
    """Call one production mode, or refuse to, and return a receipt.

    ``transport`` is injected for tests; when omitted the real client path runs
    (``earnings_qual._call_openai_compat`` for GLM, the Anthropic SDK for
    MiniMax).  A disabled or unconfigured mode never invokes the transport at
    all, and no path in this module falls back to a subscription rung.
    """
    status = resolve_mode(mode_id, env)
    if status.state != "configured":
        _emit_attempt(status, ok=False, latency_ms=0, error_class=status.state)
        return _receipt(
            status,
            ok=False,
            text=None,
            input_tokens=None,
            output_tokens=None,
            error_class=status.state,
            latency_ms=0,
        )

    mode = _mode(mode_id)
    call = transport if transport is not None else _default_transport
    started = time.perf_counter()
    try:
        outcome = _coerce_outcome(
            call(
                mode=mode,
                system=system,
                user=user,
                max_tokens=int(max_tokens),
                timeout_s=DEFAULT_TIMEOUT_S,
            )
        )
    except Exception as exc:  # noqa: BLE001 — a provider failure is a receipt, not a raise
        outcome = TransportOutcome(reason=_reason_from_exception(exc))
    latency_ms = int((time.perf_counter() - started) * 1000)

    error_class = "none"
    if outcome.status_code is not None:
        error_class = _status_to_error_class(outcome.status_code)
    elif outcome.reason:
        error_class = _classify_reason(outcome.reason)
    elif not outcome.text:
        error_class = "empty"
    if error_class not in ERROR_CLASSES:
        error_class = "transport_error"

    ok = error_class == "none"
    input_tokens = _int_or_none(outcome.input_tokens)
    output_tokens = _int_or_none(outcome.output_tokens)
    if not ok or input_tokens is None or output_tokens is None:
        # Both counts or neither: a half-known token pair cannot be priced.
        input_tokens = None
        output_tokens = None

    _emit_attempt(status, ok=ok, latency_ms=latency_ms, error_class=error_class)
    if ok and input_tokens is not None and output_tokens is not None:
        _emit_usage(
            status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=status.model,
        )

    return _receipt(
        status,
        ok=ok,
        text=outcome.text if ok else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        error_class=error_class,
        latency_ms=latency_ms,
    )
