"""Production API and application binding owner for Shared AI Provider Control.

The application companion resolves a server-selected Fabric mode through the real
workload policy and capability broker before reading its proxy credential. It uses
the existing owner configuration, retains turn-scoped client lifetime, and owns no
account claims, queue, worker jobs or usage ledger. No application mode is enrolled
in the shipped configuration; the inspected Experiential implementation remains
unqualified and cannot be promoted by configuration alone.

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
* Credential DESTINATION is pinned in code, not in the config.  Every record in
  the config must agree with the closed :data:`_MODE_IDENTITY` table on
  provider, protocol, scheme, authority (host/port/userinfo), path, secret NAME,
  usage class, billing mode, cost identity, cap id and model.  A config edit
  that moves a credential anywhere else is refused before any transport exists,
  so a compromised or hand-edited JSON cannot redirect a metered key.
* Locked models.  ``default_model`` is not a reviewable default: the current
  MiniMax and GLM production identifiers are pinned in the same table (see
  :data:`MINIMAX_PINNED_MODEL` / :data:`GLM_PINNED_MODEL`).
* One credential boundary.  :func:`_resolve_credential` is the ONLY place a
  secret VALUE is read; :func:`resolve_mode` uses it for presence, and the
  transports receive the resolved value as an argument and never touch
  ``os.environ`` themselves.  :func:`call_mode` turns ``env=None`` into
  ``os.environ`` exactly once, at its own boundary.
* Bounded failure: :func:`call_mode` never raises on provider failure and
  always returns a receipt whose ``error_class`` is drawn from
  :data:`ERROR_CLASSES` — the INCUMBENT classes of
  :mod:`engine.provider_health` (``auth`` / ``usage_limit`` / ``timeout`` /
  ``transport`` / ``unsupported`` / residual ``error``), never a second
  HTTP-shaped taxonomy.  A config that disagrees with the pinned identity is not
  a provider failure: it raises :class:`ProductionModeConfigError` and no
  transport is reachable.
* Price truth is delegated.  ``price_state`` is ``known`` only when
  :func:`lib.ai_costs` can price the exact recorded call, and ``unknown``
  otherwise.  This module keeps no local rate table and makes no relative-cost
  claim of its own --- the ledger, not this module, is where any such claim
  would have to be earned.
* Request bodies are provider-owned.  The GLM body is
  :data:`GLM_REQUEST_PROFILE` merged over the shared
  ``earnings_qual._call_openai_compat_detailed`` payload; no caller kwarg
  reaches it.
* Receipts go through the existing writers unchanged —
  :func:`engine.provider_health.record_attempt` and
  :func:`lib.ai_costs.record_usage`.  Tests must redirect their state roots
  (``PROVIDER_HEALTH_PATH`` / ``AI_COSTS_STATE_ROOT``) or patch the writer
  functions; a sparse worktree must never be written into.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import time
from dataclasses import dataclass, field, replace
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

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

#: The INCUMBENT error taxonomy, read from :mod:`engine.provider_health`:
#: ``auth`` (``HTTPStatus.UNAUTHORIZED`` / ``FORBIDDEN``) / ``usage_limit``
#: (``TOO_MANY_REQUESTS``, quota, rate limit) / ``timeout`` /
#: ``transport`` (any 5xx, connection) / ``unsupported`` / residual ``error`` — plus
#: the local no-transport states ``disabled`` / ``unconfigured`` and ``none``
#: for success.  There is deliberately no ``http_4xx`` / ``http_5xx`` /
#: ``transport_error`` here: a second HTTP-shaped taxonomy would be a parallel
#: health vocabulary the fleet does not read.
ERROR_CLASSES = frozenset({
    "none",
    "disabled",
    "unconfigured",
    "auth",
    "usage_limit",
    "timeout",
    "transport",
    "unsupported",
    "error",
})

#: Closed set for :attr:`ProductionCallReceipt.price_state`.  Derived only from
#: what :mod:`lib.ai_costs` can price — never from a local rate table.
PRICE_STATES = frozenset({"known", "unknown"})

#: Locked production model identifiers.  These are the exact keys Sol's pricing
#: PR (#7289) adds to ``config/ai_pricing.yml``, so a receipt composes into
#: :func:`lib.ai_costs.estimate_cost_usd` without a translation table.
MINIMAX_PINNED_MODEL = "MiniMax-M3"
GLM_PINNED_MODEL = "glm-5.3-flash"


@dataclass(frozen=True)
class ModeIdentity:
    """The credential DESTINATION a mode is allowed to use, pinned in code.

    The config declares where a metered key is spent; this table decides
    whether that declaration is allowed.  Every field is compared exactly, so a
    config edit can never move a credential to another host, another path,
    another scheme, another secret NAME, another model, or another billing
    identity without failing closed.
    """

    provider_id: str
    protocol: str
    scheme: str
    authority: str
    path: str
    secret_ref: str
    usage_class: str
    billing_mode: str
    cost_identity: str
    cap_id: str
    model: str


#: Closed identity table.  A mode id absent from this table cannot be loaded at
#: all, so the set of credentialed production destinations is exactly this.
_MODE_IDENTITY = {
    "minimax_payg_api": ModeIdentity(
        provider_id="minimax",
        protocol=PROTOCOL_ANTHROPIC,
        scheme="https",
        authority="api.minimax.io",
        path="/anthropic",
        secret_ref="MINIMAX_API_KEY",
        usage_class=PRODUCTION_USAGE_CLASS,
        billing_mode=METERED_BILLING_MODE,
        cost_identity="minimax/metered",
        cap_id="prod_api:minimax",
        model=MINIMAX_PINNED_MODEL,
    ),
    "glm_general_api": ModeIdentity(
        provider_id="glm",
        protocol=PROTOCOL_OPENAI,
        scheme="https",
        authority="api.z.ai",
        path="/api/paas/v4",
        secret_ref="ZAI_API_KEY",
        usage_class=PRODUCTION_USAGE_CLASS,
        billing_mode=METERED_BILLING_MODE,
        cost_identity="glm/metered",
        cap_id="prod_api:glm",
        model=GLM_PINNED_MODEL,
    ),
}


PROFILE_UNQUALIFIED_PENDING_CANARY = "UNQUALIFIED_PENDING_CANARY"
PROFILE_QUALIFIED_CANARY = "QUALIFIED_CANARY"
REQUEST_PROFILE_QUALIFICATIONS = frozenset(
    {PROFILE_UNQUALIFIED_PENDING_CANARY, PROFILE_QUALIFIED_CANARY}
)


@dataclass(frozen=True)
class RequestProfile:
    """A provider-owned, closed request body overlay.

    ``qualification`` records how far the profile has been validated against
    the live model contract: a profile that has not been canaried against the
    pinned model is ``UNQUALIFIED_PENDING_CANARY`` and the code that owns it
    must not be treated as production-qualified.
    """

    model: str
    temperature: float
    max_tokens: int
    qualification: str

    def __post_init__(self) -> None:
        if self.qualification not in REQUEST_PROFILE_QUALIFICATIONS:
            raise ProductionModeConfigError(
                "request profile qualification is not in the closed accepted vocabulary"
            )

    def body(self, *, requested_max_tokens: int) -> dict[str, Any]:
        """The closed body overlay for one call.

        ``max_tokens`` is a CEILING: a caller may ask for fewer tokens but can
        never raise it, and no other key can be introduced by a caller.
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": min(int(requested_max_tokens), int(self.max_tokens)),
        }


#: GLM production body overlay.  The current ``glm-5.3-flash`` parameter
#: contract could not be verified offline, so this profile carries ONLY the
#: fields already implied by the shared helper (``model``, ``temperature``) plus
#: a conservative ``max_tokens`` ceiling -- no ``thinking``/reasoning control is
#: invented.  Until a canary against the pinned model says otherwise the
#: profile is UNQUALIFIED_PENDING_CANARY, and the module stays shadow-off.
GLM_REQUEST_PROFILE = RequestProfile(
    model=GLM_PINNED_MODEL,
    temperature=0.0,
    max_tokens=4096,
    qualification=PROFILE_UNQUALIFIED_PENDING_CANARY,
)

SECRET_REF_RE = re.compile(r"^[A-Z][A-Z0-9_]{3,63}$")
MODE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
CAP_ID_RE = re.compile(r"^prod_api:[a-z][a-z0-9_]{1,31}$")

_TOP_LEVEL_KEYS = frozenset({"schema", "producer_program", "modes"})
_OPTIONAL_TOP_LEVEL_KEYS = frozenset({"application_fabric_modes"})
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
    ``error_class`` is reserved for a transport that ALREADY knows the
    incumbent class (an SDK exception with no HTTP status, a missing SDK); it
    must be a member of :data:`ERROR_CLASSES` or it is normalised to the
    residual ``error``.
    """

    text: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    reason: str | None = None
    status_code: int | None = None
    error_class: str | None = None


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
    price_state: str = "unknown"


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


def _identity_mismatches(mode: ProductionMode, identity: ModeIdentity) -> list[str]:
    """Every way ``mode`` disagrees with the pinned credential destination.

    Compared exactly, field by field, including the three parts of the URL that
    decide WHERE the secret is sent: scheme, authority (host, port and userinfo
    all live in ``netloc``), and path.  A query or fragment is a mismatch on its
    own -- a credential is never sent under an unparsed URL tail.
    """
    problems: list[str] = []
    for field, actual, pinned in (
        ("provider_id", mode.provider_id, identity.provider_id),
        ("protocol", mode.protocol, identity.protocol),
        ("secret_ref", mode.secret_ref, identity.secret_ref),
        ("usage_class", mode.usage_class, identity.usage_class),
        ("billing_mode", mode.billing_mode, identity.billing_mode),
        ("cost_identity", mode.cost_identity, identity.cost_identity),
        ("cap_id", mode.cap_id, identity.cap_id),
        ("default_model", mode.default_model, identity.model),
    ):
        if actual != pinned:
            problems.append(f"{field} {actual!r} != pinned {pinned!r}")

    split = urlsplit(mode.base_url)
    if split.scheme != identity.scheme:
        problems.append(f"scheme {split.scheme!r} != pinned {identity.scheme!r}")
    if split.netloc != identity.authority:
        problems.append(
            f"authority {split.netloc!r} != pinned {identity.authority!r} "
            "(host, port and userinfo must be exact)"
        )
    if split.path != identity.path:
        problems.append(f"path {split.path!r} != pinned {identity.path!r}")
    if split.query:
        problems.append(f"base_url carries a query ({split.query!r})")
    if "#" in mode.base_url:
        # The raw string, not ``split.fragment``: ``urlsplit`` drops the
        # delimiter of an EMPTY trailing fragment, so a bare ``#`` is invisible
        # to the parsed parts -- and a credential is never sent under a URL tail.
        problems.append(f"base_url carries a fragment ({mode.base_url.split('#', 1)[1]!r})")
    return problems


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
    if (
        not base_url.startswith("https://")
        or "@" in base_url
        or "?" in base_url
        or "#" in base_url
    ):
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: base_url must be a plain https endpoint with no "
            "userinfo, query or fragment"
        )

    mode = ProductionMode(
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

    identity = _MODE_IDENTITY.get(mode_id)
    if identity is None:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: no pinned credential destination; a production "
            "mode may not be added by config alone"
        )
    mismatches = _identity_mismatches(mode, identity)
    if mismatches:
        raise ProductionModeConfigError(
            f"mode {mode_id!r}: config disagrees with the pinned credential "
            f"destination — {'; '.join(mismatches)}"
        )
    return mode


def _owner_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProductionModeConfigError("duplicate owner configuration key")
        result[key] = value
    return result


def _load_owner_document(path: str | Path | None = None) -> dict:
    """Read one fresh, credential-free snapshot of this owner's configuration."""
    cfg_path = Path(path) if path is not None else DEFAULT_PATH
    try:
        with cfg_path.open("rb") as handle:
            data = handle.read(262145)
        if len(data) > 262144:
            raise ProductionModeConfigError("owner configuration is too large")
        raw = json.loads(data.decode("utf-8"), object_pairs_hook=_owner_json_object)
    except FileNotFoundError as exc:
        raise ProductionModeConfigError(f"production modes config missing: {cfg_path}") from exc
    except json.JSONDecodeError as exc:
        raise ProductionModeConfigError(f"production modes config is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ProductionModeConfigError("production modes config must be a JSON object")
    unknown = sorted(set(raw) - _TOP_LEVEL_KEYS - _OPTIONAL_TOP_LEVEL_KEYS)
    if unknown:
        raise ProductionModeConfigError(f"unknown top-level key(s) {unknown} — closed set")
    missing = sorted(_TOP_LEVEL_KEYS - set(raw))
    if missing:
        raise ProductionModeConfigError(f"missing top-level key(s) {missing}")
    if raw["schema"] != SCHEMA:
        raise ProductionModeConfigError(f"schema must be {SCHEMA!r}, got {raw['schema']!r}")
    if raw["producer_program"] != PRODUCER_PROGRAM:
        raise ProductionModeConfigError(f"producer_program must be {PRODUCER_PROGRAM!r}")

    return raw


def load_modes(path: str | Path | None = None) -> dict[str, ProductionMode]:
    """Load the closed PAYG identities without opening application credentials."""
    raw = _load_owner_document(path)

    modes_raw = raw["modes"]
    if not isinstance(modes_raw, dict) or not modes_raw:
        raise ProductionModeConfigError("modes must be a non-empty object keyed by mode_id")
    unlisted = sorted(set(modes_raw) - set(_MODE_IDENTITY))
    if unlisted:
        raise ProductionModeConfigError(
            f"unknown mode id(s) {unlisted} — the credentialed set is exactly "
            f"{sorted(_MODE_IDENTITY)}"
        )
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


class ApplicationFabricBindingError(ValueError):
    """Bounded application refusal; never echo owner documents or credentials."""


@dataclass(frozen=True)
class _ApplicationFabricTransport:
    """Closed implementation identity, not a pool/account or routing registry.

    Application eligibility is independent of native worker registration. A
    configuration edit cannot qualify an implementation whose owner has not
    qualified it in source. Provider and billing attribution belong to this
    implementation, not to the word 'fabric'.
    """

    base_url: str
    secret_ref: str
    provider_id: str | None
    model: str | None
    cost_basis: str
    cap_id: str
    capability_id: str
    qualified: bool = False
    application_allowed: bool = False
    protocol: str = "openai_chat_v1"
    native_recipe_digest: str | None = None
    metadata_read: bool = False
    automatic: bool = False
    # Source-owned purpose classification. The wire protocol also carries
    # ordinary HTTP inference and cannot establish native-agent authority.
    execution_surface: str = "inference"


# Closed application implementations remain held until independently qualified
# and permitted by this owner. Neither native worker availability nor a config
# edit grants application permission. No mode is enrolled below or in shipped
# configuration, and no subscription/metered billing is inferred.
_APPLICATION_FABRIC_TRANSPORTS = {
    "experiential_proxy_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:8311/v1",
        secret_ref="FABRIC_PROXY_TOKEN",
        provider_id="experiential",
        model="glm-5.3-uncensored",
        cost_basis="unknown",
        cap_id="fabric:experiential_proxy",
        capability_id="fabric_application_proxy",
    ),
    "native_go_application_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1",
        secret_ref="MACRO_FABRIC_APPLICATION_TOKEN",
        provider_id="go",
        model="deepseek-v4.1-flash",
        cost_basis="unknown",
        cap_id="fabric:go_application",
        capability_id="fabric_application_go",
        protocol="native_application_v1",
        qualified=False,
        application_allowed=False,
        metadata_read=True,
    ),
    "native_go_mastermind_text_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1",
        secret_ref="MASTERMIND_FABRIC_APPLICATION_TOKEN",
        provider_id="go",
        model="deepseek-v4.1-flash",
        cost_basis="unknown",
        cap_id="fabric:go_mastermind_text",
        capability_id="fabric_application_go_mastermind_text",
        protocol="native_application_v1",
        qualified=False,
        application_allowed=False,
        metadata_read=False,
    ),
    "native_go_mastermind_chat_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1",
        secret_ref="MASTERMIND_FABRIC_CHAT_TOKEN",
        provider_id="go",
        model="deepseek-v4.1-flash",
        cost_basis="unknown",
        cap_id="fabric:go_mastermind_chat",
        capability_id="fabric_application_go_mastermind_chat",
        protocol="native_application_v1",
        qualified=False,
        application_allowed=False,
        metadata_read=False,
    ),
    "native_go_macro_brain_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1",
        secret_ref="MACRO_BRAIN_FABRIC_APPLICATION_TOKEN",
        provider_id="go",
        model="deepseek-v4.1-flash",
        cost_basis="unknown",
        cap_id="fabric:go_macro_brain",
        capability_id="fabric_application_go_macro_brain",
        protocol="native_application_v1",
        qualified=False,
        application_allowed=False,
        metadata_read=False,
    ),
    "native_go_macro_ask_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1",
        secret_ref="MACRO_ASK_FABRIC_APPLICATION_TOKEN",
        provider_id="go",
        model="deepseek-v4.1-flash",
        cost_basis="unknown",
        cap_id="fabric:go_macro_ask",
        capability_id="fabric_application_go_macro_ask",
        protocol="native_application_v1",
        qualified=False,
        application_allowed=False,
        metadata_read=False,
    ),

    # Source support does not enroll applications: current data qualification,
    # capability authority and native admission are still required for every call.
    "native_fabric_application_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="MACRO_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:go_application", capability_id="fabric_application_go",
        protocol="native_application_v1", metadata_read=True, automatic=True,
        qualified=True, application_allowed=True),
    "native_fabric_mastermind_text_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="MASTERMIND_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:go_mastermind_text", capability_id="fabric_application_go_mastermind_text",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
    "native_fabric_mastermind_chat_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="MASTERMIND_FABRIC_CHAT_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:go_mastermind_chat", capability_id="fabric_application_go_mastermind_chat",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
    "native_fabric_macro_brain_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="MACRO_BRAIN_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:go_macro_brain", capability_id="fabric_application_go_macro_brain",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
    "native_fabric_macro_ask_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="MACRO_ASK_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:go_macro_ask", capability_id="fabric_application_go_macro_ask",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
    "native_fabric_macro_batch_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="MACRO_BATCH_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:macro_batch", capability_id="fabric_application_macro_batch",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
    "native_fabric_macro_analysis_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="MACRO_ANALYSIS_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:macro_analysis", capability_id="fabric_application_macro_analysis",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
    "native_fabric_macro_portfolio_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="MACRO_PORTFOLIO_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:macro_portfolio", capability_id="fabric_application_macro_portfolio",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
    # Hermes primary turns use the same APPLICATION owner and exact native
    # protocol. These are distinct internal service identities, not provider
    # keys or enrollment. Current runtime data, capability and native admission
    # remain mandatory; source support alone authorizes no request.
    "native_go_hermes_attended_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1",
        secret_ref="HERMES_ATTENDED_FABRIC_APPLICATION_TOKEN",
        provider_id="go",
        model="glm-5.3-flash",
        cost_basis="unknown",
        cap_id="fabric:go_hermes_attended",
        capability_id="fabric_application_go_hermes_attended",
        protocol="native_application_v1",
        qualified=True,
        application_allowed=True,
        metadata_read=False,
    ),
    "native_go_hermes_secretary_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.2:50142/v1",
        secret_ref="HERMES_SECRETARY_FABRIC_APPLICATION_TOKEN",
        provider_id="go",
        model="deepseek-v4.1-flash",
        cost_basis="unknown",
        cap_id="fabric:go_hermes_secretary",
        capability_id="fabric_application_go_hermes_secretary",
        protocol="native_application_v1",
        qualified=True,
        application_allowed=True,
        metadata_read=False,
    ),
    "native_go_hermes_meta_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.3:50142/v1",
        secret_ref="HERMES_META_FABRIC_APPLICATION_TOKEN",
        provider_id="go",
        model="deepseek-v4.1-flash",
        cost_basis="unknown",
        cap_id="fabric:go_hermes_meta",
        capability_id="fabric_application_go_hermes_meta",
        protocol="native_application_v1",
        qualified=True,
        application_allowed=True,
        metadata_read=False,
    ),
    "native_fabric_hermes_secretary_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.2:50142/v1", secret_ref="HERMES_SECRETARY_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:go_hermes_secretary", capability_id="fabric_application_go_hermes_secretary",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
    "native_fabric_hermes_attended_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.1:50142/v1", secret_ref="HERMES_ATTENDED_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:go_hermes_attended", capability_id="fabric_application_go_hermes_attended",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True, metadata_read=False),
    "native_fabric_hermes_meta_auto_v1": _ApplicationFabricTransport(
        base_url="http://127.0.0.3:50142/v1", secret_ref="HERMES_META_FABRIC_APPLICATION_TOKEN",
        provider_id=None, model=None, cost_basis="unknown",
        cap_id="fabric:go_hermes_meta", capability_id="fabric_application_go_hermes_meta",
        protocol="native_application_v1", automatic=True,
        qualified=True, application_allowed=True),
}
_APPLICATION_MODE_IDS = frozenset({"shared_fabric"})
@dataclass(frozen=True)
class _ServiceFabricRelation:
    lane: str | None
    workload: str
    transport_id: str | None
    automatic_transport_id: str | None = None

_SERVICE_FABRIC_RELATIONS = {
    "mastermind_text_fabric": _ServiceFabricRelation(
        "mastermind-text", "site_batch", "native_go_mastermind_text_v1", "native_fabric_mastermind_text_auto_v1"),
    "mastermind_chat_fabric": _ServiceFabricRelation(
        "mastermind-chat", "site_interactive", "native_go_mastermind_chat_v1", "native_fabric_mastermind_chat_auto_v1"),
    "macro_brain_fabric": _ServiceFabricRelation(
        "brain", "site_interactive", "native_go_macro_brain_v1", "native_fabric_macro_brain_auto_v1"),
    "macro_ask_fabric": _ServiceFabricRelation(
        "ask-brain", "site_interactive", "native_go_macro_ask_v1", "native_fabric_macro_ask_auto_v1"),
    "macro_batch_fabric": _ServiceFabricRelation(
        None, "site_batch", None, "native_fabric_macro_batch_auto_v1"),
    "macro_analysis_fabric": _ServiceFabricRelation(
        None, "lobe_analysis", None, "native_fabric_macro_analysis_auto_v1"),
    "macro_portfolio_fabric": _ServiceFabricRelation(
        None, "portfolio_analysis", None, "native_fabric_macro_portfolio_auto_v1"),
    "hermes_secretary_fabric": _ServiceFabricRelation(
        "hermes-secretary", "site_interactive", "native_go_hermes_secretary_v1",
        "native_fabric_hermes_secretary_auto_v1"),
    "hermes_meta_fabric": _ServiceFabricRelation(
        "hermes-meta-ceo", "site_interactive", "native_go_hermes_meta_v1",
        "native_fabric_hermes_meta_auto_v1"),
    "hermes_attended_fabric": _ServiceFabricRelation(
        "hermes-attended", "hermes_attended", "native_go_hermes_attended_v1",
        "native_fabric_hermes_attended_auto_v1"),
}
_APPLICATION_RECORD_KEYS = _APPLICATION_MODE_IDS | frozenset(_SERVICE_FABRIC_RELATIONS)
_APPLICATION_ID = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_APPLICATION_IDENTITY_FIELDS = (
    "base_url", "secret_ref", "provider_id", "model", "cost_basis",
    "cap_id", "capability_id",
)
_APPLICATION_RECORD_FIELDS = frozenset(_APPLICATION_IDENTITY_FIELDS) | {
    "transport_id", "enabled", "application_allowed", "qualification",
    "qualification_ref", "qualified_until",
}


def _application_refuse(code: str):
    raise ApplicationFabricBindingError(code)


@dataclass(frozen=True)
class _ApplicationFabricMode:
    transport: _ApplicationFabricTransport
    enabled: bool
    application_allowed: bool
    qualification: str
    qualification_ref: str | None
    qualified_until: float | None
    admin_pool_view: bool = False
    route_scope_json: str | None = None

    @property
    def route_scope(self):
        return json.loads(self.route_scope_json) if self.route_scope_json is not None else None

    @property
    def secret_ref(self) -> str:
        return self.transport.secret_ref


def _application_fabric_mode(mode_id: str, root: Path) -> _ApplicationFabricMode:
    """Read the incumbent owner document; no secret, client, ledger or claim."""
    if mode_id not in _APPLICATION_RECORD_KEYS:
        _application_refuse("fabric_application_mode_unknown")
    try:
        document = _load_owner_document(root / "config/provider_production_modes.v1.json")
    except Exception:
        raise ApplicationFabricBindingError("fabric_owner_config_invalid") from None
    records = document.get("application_fabric_modes", {})
    if not isinstance(records, dict) or set(records) - _APPLICATION_RECORD_KEYS:
        _application_refuse("fabric_application_modes_invalid")
    raw = records.get(mode_id)
    if raw is None:
        _application_refuse("fabric_application_binding_missing")
    if not isinstance(raw, dict) or set(raw) not in (
            _APPLICATION_RECORD_FIELDS, _APPLICATION_RECORD_FIELDS | {"admin_pool_view"},
            _APPLICATION_RECORD_FIELDS | {"route_scope"},
            _APPLICATION_RECORD_FIELDS | {"admin_pool_view", "route_scope"}):
        _application_refuse("fabric_application_binding_invalid")
    if type(raw.get("admin_pool_view", False)) is not bool:
        _application_refuse("fabric_application_metadata_permission_invalid")
    transport_id = raw["transport_id"]
    if not isinstance(transport_id, str):
        _application_refuse("fabric_application_transport_invalid")
    relation = _SERVICE_FABRIC_RELATIONS.get(mode_id)
    if relation is not None and transport_id not in (relation.transport_id, relation.automatic_transport_id):
        _application_refuse("fabric_application_transport_invalid")
    if relation is None and mode_id in _APPLICATION_MODE_IDS and transport_id in {
            value for rel in _SERVICE_FABRIC_RELATIONS.values()
            for value in (rel.transport_id, rel.automatic_transport_id)}:
        _application_refuse("fabric_application_transport_invalid")
    transport = _APPLICATION_FABRIC_TRANSPORTS.get(transport_id)
    if type(transport) is not _ApplicationFabricTransport:
        _application_refuse("fabric_application_transport_unregistered")
    if ("route_scope" in raw) != transport.automatic:
        _application_refuse("fabric_application_route_variant_invalid")
    route_scope_json = None
    if transport.automatic:
        from engine.fabric_inference_client import validate_auto_route_scope
        try:
            scope, _ = validate_auto_route_scope(raw["route_scope"])
            route_scope_json = json.dumps(scope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            _application_refuse("fabric_application_route_scope_invalid")
    if any(raw[k] != getattr(transport, k) for k in _APPLICATION_IDENTITY_FIELDS):
        _application_refuse("fabric_application_identity_mismatch")
    if type(raw["enabled"]) is not bool or type(raw["application_allowed"]) is not bool:
        _application_refuse("fabric_application_flags_invalid")
    qualification = raw["qualification"]
    if not isinstance(qualification, str) or qualification not in REQUEST_PROFILE_QUALIFICATIONS:
        _application_refuse("fabric_application_qualification_invalid")
    ref, until = raw["qualification_ref"], raw["qualified_until"]
    if ref is not None and (not isinstance(ref, str) or not _APPLICATION_ID.fullmatch(ref)):
        _application_refuse("fabric_application_qualification_invalid")
    if until is not None and (type(until) not in (float, int)
                              or not 0 < until <= 253402300799 or not math.isfinite(until)):
        _application_refuse("fabric_application_qualification_invalid")
    return _ApplicationFabricMode(
        transport, raw["enabled"], raw["application_allowed"], qualification, ref, until,
        raw.get("admin_pool_view", False), route_scope_json,
    )


def _application_timeout_cap(value):
    """Validate a request budget before credentials; None keeps the protocol default."""
    if value is None:
        return None
    if type(value) not in (int, float) or not 0 < value <= 900 or not math.isfinite(value):
        _application_refuse("fabric_application_timeout_invalid")
    return float(value)


def _validate_service_fabric_relation(
    mode_id: str, lane: str, service_mode_id: str | None,
    profile_present: bool, profile: Any,
) -> None:
    """Host mode stays shared_fabric; child service IDs are record keys only."""
    if mode_id not in _APPLICATION_MODE_IDS:
        _application_refuse("fabric_application_selection_invalid")
    if service_mode_id is None:
        return
    relation = _SERVICE_FABRIC_RELATIONS.get(service_mode_id)
    if type(relation) is not _ServiceFabricRelation:
        _application_refuse("fabric_application_selection_invalid")
    if ((relation.lane is not None and lane != relation.lane)
            or not profile_present or profile != relation.workload):
        _application_refuse("fabric_application_selection_invalid")


@dataclass(frozen=True)
class ApplicationFabricFactory:
    """Trusted startup composition; fresh configuration, workload and capability checks.

    The native admission/gateway owner retains the account claim and operation
    fence. This object adds neither a worker job nor a lease/usage/retry ledger.
    Callers cannot pass a qualification dictionary, URL, token or model override.
    """

    mode_id: str
    lane: str
    root: Path
    _profile_present: bool
    _profile: Any
    _provider_order: tuple[str, ...]
    service_mode_id: str | None = None
    _inspection_commitment: str | None = None
    _timeout_cap: float | None = None
    _requested_model: str | None = None

    def __post_init__(self):
        _validate_service_fabric_relation(
            self.mode_id, self.lane, self.service_mode_id,
            self._profile_present, self._profile)

    def with_requested_model(self, model: str) -> "ApplicationFabricFactory":
        """Pure immutable narrowing; fresh inspection proves the existing scope."""
        if type(model) is not str or _APPLICATION_ID.fullmatch(model) is None:
            _application_refuse("fabric_application_requested_model_invalid")
        if self._requested_model is not None and self._requested_model != model:
            _application_refuse("fabric_application_identity_changed")
        if self._inspection_commitment is not None:
            frozen = json.loads(self._inspection_commitment)
            if (frozen.get("schema") != "mastermind.fabric_application_inspection.v3"
                    or frozen.get("requested_model") != model):
                _application_refuse("fabric_application_identity_changed")
        return replace(self, _requested_model=model)

    def _effective_record_id(self) -> str:
        _validate_service_fabric_relation(
            self.mode_id, self.lane, self.service_mode_id,
            self._profile_present, self._profile)
        if self.service_mode_id is not None:
            return self.service_mode_id
        # Fixed historical transports keep their original identity. AUTO generic
        # consumers have explicit native authorities for each workload; a local
        # policy intersection cannot turn Admin into a batch/analysis principal.
        mode = _application_fabric_mode(self.mode_id, self.root)
        if not mode.transport.automatic:
            return self.mode_id
        if self._profile_present and self._profile == "site_interactive":
            return self.mode_id
        for record_id, relation in _SERVICE_FABRIC_RELATIONS.items():
            if (relation.lane is None and self._profile_present
                    and self._profile == relation.workload):
                return record_id
        _application_refuse("fabric_application_workload_authority_missing")

    def _request_timeout(self, caller_cfg: Mapping[str, Any] | None = None):
        """A caller may narrow the immutable startup budget, never widen it.

        The existing client owns the absolute request deadline. This does not
        add a timer or a whole-operation deadline; close and deliberate later
        steps retain their separate bounds and uncertain effects stay held.
        """
        startup = _application_timeout_cap(self._timeout_cap)
        if caller_cfg is not None and not isinstance(caller_cfg, Mapping):
            _application_refuse("fabric_application_workload_invalid")
        caller = _application_timeout_cap(
            caller_cfg.get("client_timeout_s") if caller_cfg is not None else None)
        if startup is None:
            return caller
        return startup if caller is None else min(startup, caller)

    def workload_configuration(self) -> dict:
        cfg = {"provider_order": list(self._provider_order)}
        if self._profile_present:
            cfg["workload_profile"] = self._profile
        return cfg

    def _decide_workload(self, transport, cfg):
        from engine.provider_workload_policy import (
            HOST_PROFILE_ENV, decide_native_workload, decide_workload,
        )

        options = {"host_profile": os.environ.get(HOST_PROFILE_ENV),
                   "policy_path": self.root / "config/provider_workloads.v1.json"}
        if transport.execution_surface == "native_agent":
            # The existing fixed native recipe remains mandatory. No native
            # AUTO service authority or production qualification is invented.
            if (transport.automatic or transport.protocol != "native_application_v1"
                    or type(transport.native_recipe_digest) is not str
                    or re.fullmatch(r"[0-9a-f]{64}", transport.native_recipe_digest) is None):
                _application_refuse("fabric_application_native_purpose_contract_invalid")
            return decide_native_workload(cfg, **options)
        if transport.execution_surface != "inference":
            _application_refuse("fabric_application_execution_surface_invalid")
        decision = decide_workload(cfg, **options)
        # None is legacy migration, never permission to construct Fabric.
        if decision is None or decision.allowed_order != ("fabric",) or decision.denied_order:
            _application_refuse("fabric_application_workload_denied")
        return decision

    def workload_decision(self):
        mode = _application_fabric_mode(self._effective_record_id(), self.root)
        return self._decide_workload(mode.transport, self.workload_configuration())

    def _eligibility(self, caller_cfg: Mapping[str, Any] | None = None):
        """The ONE owner/workload/capability/qualification check set.

        It resolves NO credential and constructs NO client, so the
        credential-free inspection and the real binder reuse the same rules.
        Configuration can change between calls; with_inspection() narrows a
        later binding to the exact earlier identity. Every refusal
        below happens BEFORE any secret is read, so an ineligible host never
        touches a credential at all.

        Returns (mode, transport, decision). The caller decides what to do
        with a credential-free result: inspect() publishes the identity,
        _bind_with_workload() spends it.
        """
        self._request_timeout(caller_cfg)
        mode = _application_fabric_mode(self._effective_record_id(), self.root)
        transport = mode.transport
        decision = self._decide_workload(transport, self.workload_configuration())
        if caller_cfg is not None:
            if not isinstance(caller_cfg, Mapping):
                _application_refuse("fabric_application_workload_invalid")
            if "workload_profile" in caller_cfg:
                # The explicit Fabric branch has already selected one transport.
                # Preserve the actual caller's selector, including null/empty;
                # its legacy waterfall cannot add another selected transport.
                caller = self._decide_workload(transport,
                    {"workload_profile": caller_cfg["workload_profile"],
                     "provider_order": ["fabric"]},
                )
                if (caller.policy_hash, caller.policy_revision) != (decision.policy_hash, decision.policy_revision):
                    _application_refuse("fabric_application_policy_changed")
                decision = replace(decision,
                    profiles=tuple(dict.fromkeys((*decision.profiles, *caller.profiles))))
        if self._requested_model is not None and (not transport.automatic
                or type(self._requested_model) is not str
                or _APPLICATION_ID.fullmatch(self._requested_model) is None):
            _application_refuse("fabric_application_requested_model_invalid")
        if (transport.automatic and caller_cfg is not None
                and "workload_profile" in caller_cfg
                and (not self._profile_present or caller_cfg["workload_profile"] != self._profile)):
            _application_refuse("fabric_application_workload_authority_mismatch")
        if transport.automatic and (transport.protocol != "native_application_v1"
                or transport.model is not None or transport.provider_id is not None
                or transport.cost_basis != "unknown" or transport.native_recipe_digest is not None
                or mode.route_scope is None):
            _application_refuse("fabric_application_auto_contract_invalid")
        if transport.protocol not in {"openai_chat_v1", "native_application_v1"}:
            _application_refuse("fabric_application_protocol_invalid")
        if transport.native_recipe_digest is not None and (
                transport.protocol != "native_application_v1"
                or not isinstance(transport.native_recipe_digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", transport.native_recipe_digest) is None):
            _application_refuse("fabric_application_recipe_invalid")
        if not mode.enabled:
            _application_refuse("fabric_application_disabled")
        if transport.qualified is not True or mode.qualification != PROFILE_QUALIFIED_CANARY:
            _application_refuse("fabric_application_unqualified")
        if transport.application_allowed is not True or mode.application_allowed is not True:
            _application_refuse("fabric_application_not_permitted")
        if not mode.qualification_ref or mode.qualified_until is None or mode.qualified_until <= time.time():
            _application_refuse("fabric_application_qualification_expired")

        self._capability(transport)
        return mode, transport, decision

    def _capability(self, transport):
        from engine.neuralweb import capability_broker

        # Explicit root bypasses the incumbent broker's process manifest cache.
        grant = capability_broker.resolve(transport.capability_id, self.lane, root=self.root)
        if not isinstance(grant, dict) or grant.get("allowed") is not True:
            _application_refuse("fabric_application_capability_denied")
        if grant.get("ref_name") != transport.secret_ref:
            _application_refuse("fabric_application_credential_ref_mismatch")

    def _metadata_identity(self):
        """Separate explicit read permission; it cannot relax inference gates."""
        mode = _application_fabric_mode(self._effective_record_id(), self.root)
        transport = mode.transport
        if (self.lane != "admin-orchestrator" or mode.enabled is not True
                or mode.admin_pool_view is not True or transport.metadata_read is not True
                or transport.protocol != "native_application_v1"):
            _application_refuse("fabric_application_metadata_not_permitted")
        decision = self._decide_workload(transport, self.workload_configuration())
        self._capability(transport)
        return mode, transport, self._commit_inspection(self._inspection_identity(transport, decision, mode.route_scope, self._requested_model))

    def prepare_admin_pool_reader(self):
        """Trusted startup only: resolve through the incumbent secret boundary once."""
        from engine.fabric_inference_client import FabricPoolViewReader

        mode, transport, identity = self._metadata_identity()
        credential = _resolve_credential(mode, None)
        if credential is None:
            _application_refuse("fabric_application_unconfigured")
        return _PreparedApplicationPoolReader(self, identity,
            FabricPoolViewReader(base_url=transport.base_url, proxy_token=credential))

    @staticmethod
    def _inspection_identity(transport, decision, route_scope=None, requested_model=None) -> dict:
        if transport.automatic:
            from engine.fabric_inference_client import (
                AUTO_INSPECTION_SCHEMA, EXACT_INSPECTION_SCHEMA, validate_auto_route_scope,
            )
            scope, digest = validate_auto_route_scope(route_scope)
            private = {**{key: getattr(transport, key) for key in _APPLICATION_IDENTITY_FIELDS},
                "protocol": transport.protocol, "requested_model": requested_model,
                "route_scope": scope, "output_limit_mode": "hard_maximum"}
            return {"schema": (AUTO_INSPECTION_SCHEMA if requested_model is None else EXACT_INSPECTION_SCHEMA),
                "requested_model": requested_model,
                "route_scope": scope, "route_scope_digest": digest, "output_limit_mode": "hard_maximum",
                "cap_id": transport.cap_id, "capability_id": transport.capability_id,
                "workload_policy": decision.receipt(),
                "transport_identity": hashlib.sha256(json.dumps(private, sort_keys=True,
                    separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()}
        return {
            "provider": transport.provider_id,
            "model": transport.model,
            "cap_id": transport.cap_id,
            "capability_id": transport.capability_id,
            "cost_basis": transport.cost_basis,
            "workload_policy": decision.receipt(),
            # Commit the private source recipe without publishing its endpoint
            # or secret-reference name. This contains no credential value.
            "transport_identity": hashlib.sha256(json.dumps({
                **{key: getattr(transport, key) for key in _APPLICATION_IDENTITY_FIELDS},
                "protocol": transport.protocol,
                **({"native_recipe_digest": transport.native_recipe_digest}
                   if transport.native_recipe_digest is not None else {}),
                **({"execution_surface": transport.execution_surface}
                   if transport.execution_surface != "inference" else {}),
            }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
        }

    @staticmethod
    def _commit_inspection(identity: Mapping[str, Any]) -> str:
        # A snapshot only narrows an already eligible owner. It grants nothing.
        fields = {"provider", "model", "cap_id", "capability_id", "cost_basis",
                  "workload_policy", "transport_identity"}
        if type(identity) is dict and identity.get("schema") in {
                "mastermind.fabric_application_inspection.v2", "mastermind.fabric_application_inspection.v3"}:
            from engine.fabric_inference_client import validate_auto_inspection
            try:
                identity = validate_auto_inspection(identity)
            except Exception:
                _application_refuse("fabric_application_inspection_invalid")
        elif type(identity) is not dict or set(identity) != fields:
            _application_refuse("fabric_application_inspection_invalid")
        try:
            return json.dumps(identity, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            _application_refuse("fabric_application_inspection_invalid")

    def with_inspection(self, identity: Mapping[str, Any]) -> "ApplicationFabricFactory":
        """Return the same immutable owner type, narrowed to an observed identity.

        The commitment contains only inspection metadata and is copied by value.
        Binding still runs every current eligibility check before comparing it
        and before resolving any credential or constructing a transport client.
        """
        commitment = self._commit_inspection(identity)
        if self._inspection_commitment is not None and self._inspection_commitment != commitment:
            _application_refuse("fabric_application_identity_changed")
        return replace(self, _inspection_commitment=commitment)

    def inspect(self, caller_cfg: Mapping[str, Any] | None = None) -> dict:
        """Inspect current eligible identity without credentials, clients or admission.

        A cache may use this current identity without opening a credential. A
        later cold fill must bind with with_inspection(snapshot) so a valid
        reconfiguration cannot store another model's output under this key.
        Missing credentials may still prevent that later fill.
        """
        mode, transport, decision = self._eligibility(caller_cfg)
        identity = self._inspection_identity(transport, decision, mode.route_scope, self._requested_model)
        if (self._inspection_commitment is not None
                and self._inspection_commitment != self._commit_inspection(identity)):
            _application_refuse("fabric_application_identity_changed")
        return identity

    def _bind_with_workload(self, caller_cfg: Mapping[str, Any] | None = None,
                            *, operation_id: str | None = None,
                            prior_admission_possible: bool = False):
        """Internal composition returns the exact policy receipt with the client."""
        mode, transport, decision = self._eligibility(caller_cfg)
        if (self._inspection_commitment is not None
                and self._inspection_commitment != self._commit_inspection(
                    self._inspection_identity(transport, decision, mode.route_scope, self._requested_model))):
            _application_refuse("fabric_application_identity_changed")
        from engine.fabric_inference_client import (
            FabricInferenceClient, NATIVE_PROTOCOL, validate_native_operation_id,
        )

        native = transport.protocol == NATIVE_PROTOCOL
        if type(prior_admission_possible) is not bool or prior_admission_possible and not native:
            _application_refuse("fabric_application_restoration_invalid")
        if native:
            # Original identity is part of the trusted owner join. A caller
            # cannot omit/rewrite it and still touch the service credential.
            validate_native_operation_id(operation_id)
        timeout = self._request_timeout(caller_cfg)
        credential = _resolve_credential(mode, None)
        if credential is None:
            _application_refuse("fabric_application_unconfigured")

        client = FabricInferenceClient(
            base_url=transport.base_url, proxy_token=credential,
            model=self._requested_model if transport.automatic else transport.model,
            **({"auto_inspection": self._inspection_identity(transport, decision, mode.route_scope, self._requested_model)}
               if transport.automatic else {}),
            **({"timeout_s": timeout} if timeout is not None else {}),
            **({"protocol": NATIVE_PROTOCOL, "operation_id": operation_id,
                "prior_admission_possible": prior_admission_possible,
                **({"native_recipe_digest": transport.native_recipe_digest}
                   if transport.native_recipe_digest is not None else {})} if native else {}),
        )
        if transport.automatic:
            return ({"schema": ("mastermind.fabric_application_binding.v2" if self._requested_model is None
                                else "mastermind.fabric_application_binding.v3"), "client": client,
                     "inspection": self._inspection_identity(transport, decision, mode.route_scope, self._requested_model)}, decision)
        return ({"client": client, "model": transport.model,
                 "provider": transport.provider_id, "cost_basis": transport.cost_basis,
                 "cap_id": transport.cap_id}, decision)

    def __call__(self) -> dict:
        return self._bind_with_workload()[0]


@dataclass(frozen=True)
class _PreparedApplicationPoolReader:
    factory: ApplicationFabricFactory = field(repr=False)
    identity: str = field(repr=False)
    reader: Any = field(repr=False)

    def read(self):
        # Revocation/config drift is checked without re-opening credentials.
        _, _, current = self.factory._metadata_identity()
        if current != self.identity:
            _application_refuse("fabric_application_identity_changed")
        return self.reader.read()


def describe_application_fabric_selection(mode_id, *, root):
    """Local configuration evidence only; never readiness or admission proof."""
    if mode_id is None:
        return {"selected": False, "state": "legacy", "provider": None, "model": None, "blocker": None}
    # The environment/config selector is a HOST, never a child record key.
    # Keep a present child/invalid value selected+held before any record lookup,
    # credential boundary or client/network construction can be approached.
    if not isinstance(mode_id, str) or mode_id not in _APPLICATION_MODE_IDS:
        return {"selected": True, "state": "held", "provider": None, "model": None,
            "blocker": "fabric_application_selection_invalid"}
    try:
        mode = _application_fabric_mode(mode_id, Path(root))
        transport = mode.transport
        blocker = ("fabric_application_disabled" if not mode.enabled else
            "fabric_application_unqualified" if not transport.qualified or mode.qualification != PROFILE_QUALIFIED_CANARY else
            "fabric_application_not_permitted" if not transport.application_allowed or not mode.application_allowed else
            "fabric_application_qualification_expired" if not mode.qualification_ref or mode.qualified_until is None
                or mode.qualified_until <= time.time() else None)
        return {"selected": True, "state": "held" if blocker else "configured",
            "provider": transport.provider_id, "model": transport.model, "blocker": blocker}
    except ApplicationFabricBindingError:
        return {"selected": True, "state": "held", "provider": None, "model": None,
            "blocker": "fabric_application_binding_unavailable"}


def make_application_fabric_factory(
    *, mode_id: str, lane: str, workload_cfg: Mapping[str, Any], root: Path,
    service_mode_id: str | None = None,
) -> ApplicationFabricFactory:
    """Select by trusted owner mode; keep absent/invalid workload selectors distinct."""
    if (not isinstance(mode_id, str) or mode_id not in _APPLICATION_MODE_IDS
            or not isinstance(lane, str) or not _APPLICATION_ID.fullmatch(lane)
            or not isinstance(root, Path) or not root.is_absolute()
            or not isinstance(workload_cfg, Mapping)
            or not (service_mode_id is None or isinstance(service_mode_id, str))):
        _application_refuse("fabric_application_selection_invalid")
    order = workload_cfg.get("provider_order")
    if not isinstance(order, list) or order != ["fabric"]:
        _application_refuse("fabric_application_provider_order_invalid")
    profile_present = "workload_profile" in workload_cfg
    profile = workload_cfg.get("workload_profile")
    _validate_service_fabric_relation(mode_id, lane, service_mode_id, profile_present, profile)
    return ApplicationFabricFactory(
        mode_id, lane, root, profile_present, profile, tuple(order),
        service_mode_id=service_mode_id,
        _timeout_cap=_application_timeout_cap(workload_cfg.get("client_timeout_s")),
    )


def configured_application_fabric(
    *, lane: str, workload_profile: str, root: Path, service_mode_id: str | None = None,
):
    """Compose a service's trusted startup selection without opening credentials.

    Absence preserves legacy startup. Any present invalid selection remains
    selected with no factory, so the AI path refuses while other service paths
    remain available. Browser input and injected callbacks cannot weaken it.
    """
    if "MM_PROVIDER_APPLICATION_MODE" not in os.environ:
        return False, None
    try:
        factory = make_application_fabric_factory(
            mode_id=os.environ["MM_PROVIDER_APPLICATION_MODE"], lane=lane, root=root,
            workload_cfg={"workload_profile": workload_profile, "provider_order": ["fabric"]},
            service_mode_id=service_mode_id,
        )
    except ApplicationFabricBindingError:
        return True, None
    return True, factory


def _resolve_credential(
    mode: ProductionMode | _ApplicationFabricMode, env: Mapping[str, str] | None,
) -> str | None:
    """The ONE credential boundary: env-var NAME in, value (or ``None``) out.

    ``env=None`` means ``os.environ`` — the only place in this module that
    default is taken.  Everything else (``resolve_mode`` for presence,
    ``call_mode`` for the transports) goes through this function, so a
    transport never needs to read the environment and the call path reads it
    exactly once.  The value is never persisted, logged or receipted.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    value = source.get(mode.secret_ref)
    return value if isinstance(value, str) and value.strip() else None


def _request_profile_for_mode(mode: ProductionMode) -> RequestProfile | None:
    """Return and revalidate the provider-owned profile that gates ``mode``."""

    if mode.mode_id != "glm_general_api":
        return None
    profile = GLM_REQUEST_PROFILE
    if type(profile) is not RequestProfile:
        raise ProductionModeConfigError("GLM request profile has invalid type")
    if profile.qualification not in REQUEST_PROFILE_QUALIFICATIONS:
        raise ProductionModeConfigError(
            "GLM request profile qualification is not in the closed accepted vocabulary"
        )
    if profile.model != mode.default_model:
        raise ProductionModeConfigError(
            "GLM request profile model does not match the pinned production mode"
        )
    return profile


def _resolve_status_and_credential(
    mode: ProductionMode,
    env: Mapping[str, str] | None,
) -> tuple[ModeStatus, str | None]:
    """Resolve admission before touching a credential value."""

    if not mode.enabled:
        return _status(mode, None), None
    profile = _request_profile_for_mode(mode)
    if profile is not None and profile.qualification != PROFILE_QUALIFIED_CANARY:
        return _status(mode, None, qualified=False), None
    credential = _resolve_credential(mode, env)
    return _status(mode, credential), credential


def resolve_mode(mode_id: str, env: Mapping[str, str] | None = None) -> ModeStatus:
    """Resolve one mode without treating an unqualified profile as callable."""

    mode = _mode(mode_id)
    status, _credential = _resolve_status_and_credential(mode, env)
    return status


def _status(
    mode: ProductionMode,
    credential: str | None,
    *,
    qualified: bool = True,
) -> ModeStatus:
    """Build the resolved status from already-admitted credential evidence."""
    if not mode.enabled:
        state = "disabled"
    elif not qualified:
        state = "unqualified"
    elif credential is None:
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


def _usable_text(text: Any) -> str | None:
    """The transport's text, or ``None`` when it carries nothing usable.

    A blank string is not text: a 2xx whose body is whitespace is the same
    failed call as one whose body is empty, and neither may be receipted as a
    success with ``text=None``.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    return text


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
            return TransportOutcome(reason=str(value.get("error") or "provider_error"))
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
    return TransportOutcome(reason="unrecognised_transport_shape")


def _incumbent_error_class(*, message: str = "", exc: BaseException | None = None) -> str:
    """The INCUMBENT taxonomy, from :func:`engine.provider_health.classify_error`.

    That function is the fleet's single error decision tree; this module reuses
    it rather than growing a second one.  It classifies from an exception's
    message and type name, so a free-form provider string is wrapped in a
    neutral exception to run exactly that logic.  A class this module does not
    carry (``not_installed`` is host-local and needs a class of its own) lands
    on the residual ``error``.
    """
    probe: BaseException = exc if exc is not None else RuntimeError(message or "")
    cls = provider_health.classify_error(probe) or "error"
    return cls if cls in ERROR_CLASSES else "error"


def _status_to_error_class(status: int) -> str:
    """Map an HTTP status to the incumbent class.

    ``HTTPStatus.UNAUTHORIZED`` / ``FORBIDDEN`` are ``auth`` and
    ``TOO_MANY_REQUESTS`` is ``usage_limit``: the credential is dead, or the
    window is spent.  Every other 5xx is ``transport``; any other 4xx is the
    residual ``error`` — exactly the operator's decision tree, with no
    HTTP-shaped class of our own.  The three threshold statuses are named
    constants, so no bare HTTP number appears on a changed line.
    """
    if HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES:
        # A metered transport hands back the status of a SUCCESSFUL response too,
        # so a 2xx must classify as success rather than as an error class.  This
        # maps the STATUS alone; ``call_mode`` still requires the body to carry
        # usable text before it receipts a success.
        return "none"
    if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        return "auth"
    if status == HTTPStatus.TOO_MANY_REQUESTS:
        return "usage_limit"
    http_class = status // 100
    if http_class == 5:
        return "transport"
    if http_class == 4:
        return "error"
    return "transport"


def _classify_reason(reason: str) -> str:
    """Map a provider reason string to a bounded incumbent error class."""
    text = (reason or "").strip().lower()
    if not text:
        return "error"
    match = re.search(r"http[_ -]?(\d{3})", text)
    if match:
        return _status_to_error_class(int(match.group(1)))
    return _incumbent_error_class(message=text)


def _exception_status_code(exc: BaseException) -> int | None:
    """The HTTP status an SDK exception carries, when it carries one."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, bool) or not isinstance(status, int):
        return None
    return status


def _error_class_from_kind(kind: str | None) -> str:
    """Transport-neutral failure kind -> incumbent class.

    The kinds are transport detail (``timeout`` / ``connection`` / ``http`` /
    ``empty`` / ``bad_shape`` / ``unsupported`` / ``unconfigured``), NOT a
    second health taxonomy: they never leave this module as an ``error_class``.
    """
    if kind == "timeout":
        return "timeout"
    if kind in {"connection", "http"}:
        return "transport"
    if kind == "unsupported":
        return "unsupported"
    return "error"


def _glm_transport(
    mode: ProductionMode,
    system: str,
    user: str,
    *,
    max_tokens: int,
    timeout_s: float,
    credential: str,
) -> TransportOutcome:
    """GLM through ``earnings_qual._call_openai_compat_detailed`` (additive).

    The legacy two-tuple helper is untouched and still used by every other
    caller; this lane asks for the DETAILED result so a real usage block
    reaches the receipt, and hands the helper the resolved credential instead
    of letting it read the environment a second time.  The body overlay is the
    provider-owned :data:`GLM_REQUEST_PROFILE`; no caller payload is merged.
    """
    from engine import earnings_qual  # noqa: PLC0415 — one-time import, kept lazy

    oc_cfg = {
        "base_url": mode.base_url,
        "api_key_env": mode.secret_ref,
        "model": mode.default_model,
        "timeout_s": timeout_s,
    }
    call = getattr(earnings_qual, "_call_openai_compat_detailed")
    result = call(
        system,
        user,
        oc_cfg,
        max_tokens=int(max_tokens),
        request_profile=GLM_REQUEST_PROFILE.body(requested_max_tokens=int(max_tokens)),
        api_key=credential,
    )
    usage = getattr(result, "usage", None) or {}
    return TransportOutcome(
        text=result.text,
        input_tokens=_int_or_none(_usage_field(usage, "prompt_tokens")),
        output_tokens=_int_or_none(_usage_field(usage, "completion_tokens")),
        reason=result.reason,
        status_code=_int_or_none(result.status_code),
        error_class=(
            None if result.error_kind is None else _error_class_from_kind(result.error_kind)
        ),
    )


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
    credential: str,
) -> TransportOutcome:
    """MiniMax PAYG through the Anthropic SDK at the mode's own ``base_url``.

    The credential is an ARGUMENT: this transport never reads ``os.environ``,
    so the value the caller resolved is exactly the value that is sent.
    """
    try:
        import anthropic  # noqa: PLC0415
    except ImportError:
        return TransportOutcome(reason="sdk_unavailable", error_class="unsupported")

    if not credential:
        # Defensive: the credential boundary gates this, so reaching here means
        # the caller handed the transport an empty value.
        return TransportOutcome(reason="unconfigured", error_class="unconfigured")
    try:
        # This owner issues one production attempt. A timeout/connection error
        # can follow provider dispatch, so SDK retries must not replay it.
        client = anthropic.Anthropic(
            api_key=credential, base_url=mode.base_url, max_retries=0,
        )
        message = client.messages.create(
            model=mode.default_model,
            max_tokens=int(max_tokens),
            system=system,
            messages=[{"role": "user", "content": user}],
            timeout=timeout_s,
        )
    except BaseException as exc:  # noqa: BLE001 — classified below, never re-raised
        status_code = _exception_status_code(exc)
        return TransportOutcome(
            reason=type(exc).__name__,
            status_code=status_code,
            error_class=(
                None if status_code is not None else _incumbent_error_class(exc=exc)
            ),
        )
    return normalize_anthropic_response(_message_to_payload(message))


def _default_transport(
    *,
    mode: ProductionMode,
    system: str,
    user: str,
    max_tokens: int,
    timeout_s: float,
    credential: str,
) -> TransportOutcome:
    if mode.protocol == PROTOCOL_OPENAI:
        return _glm_transport(
            mode, system, user, max_tokens=max_tokens, timeout_s=timeout_s,
            credential=credential,
        )
    if mode.protocol == PROTOCOL_ANTHROPIC:
        return _minimax_transport(
            mode, system, user, max_tokens=max_tokens, timeout_s=timeout_s,
            credential=credential,
        )
    return TransportOutcome(reason="unknown_protocol", error_class="unsupported")


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
) -> str:
    """One cost row, only when BOTH token counts are known.  Never raises.

    Returns the receipt's ``price_state``: ``known`` only when
    :func:`lib.ai_costs` can price this exact call, ``unknown`` otherwise.
    The estimate comes FROM that library (this module keeps no rate table), and
    the same value is handed to the writer, so the row the ledger holds and the
    state the receipt reports can never disagree.
    """
    try:
        estimate = ai_costs.estimate_cost_usd(model, input_tokens, output_tokens)
    except Exception as exc:  # noqa: BLE001 — pricing telemetry must not cost a call
        log.warning("provider_production_modes: cost estimate failed (%s)", exc)
        estimate = None
    price_state = (
        "known"
        if isinstance(estimate, (int, float)) and not isinstance(estimate, bool)
        else "unknown"
    )
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
            est_cost_usd=estimate,
        )
    except Exception as exc:  # noqa: BLE001 — telemetry must not cost a call
        log.warning("provider_production_modes: cost receipt failed (%s)", exc)
    return price_state


def _receipt(
    status: ModeStatus,
    *,
    ok: bool,
    text: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    error_class: str,
    latency_ms: int,
    price_state: str = "unknown",
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
        price_state=price_state if price_state in PRICE_STATES else "unknown",
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
    (``earnings_qual._call_openai_compat_detailed`` for GLM, the Anthropic SDK
    for MiniMax).  A disabled or unconfigured mode never invokes the transport
    at all, and no path in this module falls back to a subscription rung.

    ``env=None`` becomes ``os.environ`` exactly here, ONCE; the resolved
    credential is then an argument to the transport, which never reads the
    environment itself.  A config that disagrees with the pinned credential
    destination raises :class:`ProductionModeConfigError` before any transport
    exists — that is a refusal, not a provider failure.
    """
    mode = _mode(mode_id)
    source: Mapping[str, str] = os.environ if env is None else env
    status, credential = _resolve_status_and_credential(mode, source)
    if status.state != "configured":
        error_class = "unsupported" if status.state == "unqualified" else status.state
        _emit_attempt(status, ok=False, latency_ms=0, error_class=error_class)
        return _receipt(
            status,
            ok=False,
            text=None,
            input_tokens=None,
            output_tokens=None,
            error_class=error_class,
            latency_ms=0,
        )

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
                credential=credential or "",
            )
        )
    except Exception as exc:  # noqa: BLE001 — a provider failure is a receipt, not a raise
        status_code = _exception_status_code(exc)
        outcome = TransportOutcome(
            reason=type(exc).__name__,
            status_code=status_code,
            error_class=(
                None if status_code is not None else _incumbent_error_class(exc=exc)
            ),
        )
    latency_ms = int((time.perf_counter() - started) * 1000)

    error_class = "none"
    status_code = _int_or_none(outcome.status_code)
    text = _usable_text(outcome.text)
    if status_code is not None:
        error_class = _status_to_error_class(status_code)
    elif outcome.error_class is not None:
        error_class = outcome.error_class
    elif outcome.reason:
        error_class = _classify_reason(outcome.reason)
    elif text is None:
        error_class = "error"
    if error_class not in ERROR_CLASSES:
        error_class = "error"
    if error_class == "none" and text is None:
        # A metered transport reports the status of a SUCCESSFUL response too,
        # so ``_status_to_error_class`` maps a 2xx to "none" -- but the status
        # alone is not a success.  A 2xx whose body carries no usable text
        # (empty ``choices``, ``content == ""``, an unparseable shape) is a
        # FAILED call, never a silent "none" with ``text=None``.
        error_class = "error"

    ok = error_class == "none"
    input_tokens = _int_or_none(outcome.input_tokens)
    output_tokens = _int_or_none(outcome.output_tokens)
    if not ok or input_tokens is None or output_tokens is None:
        # Both counts or neither: a half-known token pair cannot be priced.
        input_tokens = None
        output_tokens = None

    _emit_attempt(status, ok=ok, latency_ms=latency_ms, error_class=error_class)
    price_state = "unknown"
    if ok and input_tokens is not None and output_tokens is not None:
        price_state = _emit_usage(
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
        price_state=price_state,
    )
