"""Technology economic-change dossier composer (GMI first vertical, F04 Task 5).

A PURE composer: ``compose_technology_economic_change`` folds one already-validated
``management_outlook_comparison.v1`` dict and already-accepted shared GMI curation
assertions into the closed ``technology_economic_change.v1`` display projection. It
fetches nothing, calls no model, reads no columnar or private storage, writes
nothing, and consults no clock — every date is injected. It never computes a
second financial answer: the comparison's decimal STRINGS are copied verbatim and
the arithmetic is never re-derived, re-parsed or re-rounded.

Laws restated from the saved plan:

* TR3 — the shared curation contract (``engine.theme_graph.curation_assertion``,
  ``theme_graph.curation_assertion.v1``, macro#7870@45eb37bb) is imported LAZILY
  inside the composer. Importable: every assertion MUST pass
  ``validate_assertion`` before use. Not importable (the carrier base): the
  assertion-dependent sections carry a typed
  ``shared_contract_unavailable`` refusal — never a local schema copy, never a
  re-implemented validator, never a permissive default.
* Closed allowlist — only ``product_workload_role``/``attributed``,
  ``buyer_paid_unit``/``attributed`` and
  ``workload_usage_direction``/``contrary_observation`` assertions inside the
  ``technology_ex_semis`` vertical are rendered as business facts. Everything
  else is RETAINED AS A COUNT in coverage (``unsupported_assertions``), never
  rendered. Narrative mention mints no membership, procurement, materiality,
  capacity or exposure claim; unnamed counterparties stay unnamed; no issuer is
  declared a pure-play (ECD-48: the classification section is a non-claim).
* Identity — native identity receipts are proof; ticker strings are display
  formatting, checked independently. A missing security binding removes the
  identity-joined view entirely (typed refusal, typed missingness) and NEVER
  performs a name-similarity join. The enrichment view itself stays out of the
  first unit either way.
* Freshness — assertion content dated after the selected cutoff is excluded and
  counted (``after_cutoff``): a later supplementary filing cannot appear in an
  earlier selected cutoff.
* Bounds (ECD-44 and first-unit scope) — at most 25 cards, 50 business rows,
  100 typed relationships, 2000 chars of free text per field and 262144 bytes of
  native input. Exceeding any bound REFUSES the compose; nothing is silently
  truncated. ``pagination_supported`` is false and any offset/cursor paging
  attempt is rejected; no partial page is ever labelled complete.
* Noninterference (ECD-48) — every emitted object carries the six authority
  flags literally false; ordering is by identifier, never by magnitude; there is
  no conviction-style aggregate, no vote, and no field a briefing/watchlist
  consumer could read as a directive.

Refusals at the input boundary raise :class:`EconomicChangeDossierError` (a
``ValueError`` subclass) whose message STARTS with a snake_case reason code;
section-level unavailability inside an otherwise valid compose is a TYPED
refusal object in the dossier. The composer self-validates its own emission
against the contract schema before returning.
"""
from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "SCHEMA_ID",
    "DEFINITION_VERSION",
    "ENGINE_VERSION",
    "AUTHORITY_CEILING",
    "MAX_CARDS",
    "MAX_BUSINESS_ROWS",
    "MAX_TYPED_RELATIONSHIPS",
    "MAX_FREE_TEXT_CHARS",
    "MAX_NATIVE_INPUT_BYTES",
    "SUPPORTED_ASSERTION_FORMS",
    "SUPPORTED_VERTICAL",
    "COMPARISON_SECTIONS",
    "EconomicChangeDossierError",
    "DossierScope",
    "NativeContext",
    "IdentityReceipt",
    "CoverageSpec",
    "compose_technology_economic_change",
    "identity_receipts_digest",
    "validate_dossier",
]

SCHEMA_ID = "technology_economic_change.v1"
#: Contract-definition revision of this dossier shape. The shared research shell
#: (#7870 hook 1) requires every registered vertical to carry it on the payload
#: and match it against the registration, so it is emitted on every dossier.
DEFINITION_VERSION = "2026-09-24.1"
ENGINE_VERSION = "market_ontology.technology_economic_change.v1"
AUTHORITY_CEILING = "research_display_only"

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts/market_ontology/technology_economic_change.v1.schema.json"
)

# --- first-unit bounds (ECD-44 + saved-plan scope); exceeding any REFUSES ------
MAX_CARDS = 25
MAX_BUSINESS_ROWS = 50
MAX_TYPED_RELATIONSHIPS = 100
MAX_FREE_TEXT_CHARS = 2000
MAX_NATIVE_INPUT_BYTES = 262144

# --- the sealed comparison contract (built concurrently; output only) ---------
COMPARISON_SCHEMA_ID = "management_outlook_comparison.v1"
COMPARISON_KIND = "MANAGEMENT_REVENUE_REMAINING_YEAR"
COMPARISON_SECTIONS: tuple[str, ...] = (
    "schema", "comparison_id", "kind", "subject", "fiscal_partition", "input_roles",
    "input_vector", "eligibility", "result", "limitations", "correction", "authority",
)
COMPARISON_RESULT_DECIMALS: tuple[str, ...] = (
    "annual_midpoint_change", "new_period_deviation", "prior_actual_revision",
    "earlier_remaining", "later_remaining", "remaining_change",
)
COMPARISON_RESULT_META: tuple[str, ...] = ("currency", "scale", "formula_revision")

# --- the shared curation contract (TR3; macro#7870@45eb37bb) ------------------
SHARED_CONTRACT_MODULE = "engine.theme_graph.curation_assertion"
SHARED_ASSERTION_SCHEMA_ID = "theme_graph.curation_assertion.v1"

#: Closed allowlist for this first unit: (predicate, statement_mode) pairs.
SUPPORTED_ASSERTION_FORMS: frozenset[tuple[str, str]] = frozenset({
    ("product_workload_role", "attributed"),
    ("buyer_paid_unit", "attributed"),
    ("workload_usage_direction", "contrary_observation"),
})
SUPPORTED_VERTICAL = "technology_ex_semis"

#: Where a datable field may live in an assertion's ``temporal`` section. The
#: shared contract owns the exact shape; the first key present wins, and an
#: assertion with no datable field is not cutoff-policed (admitted as-is).
TEMPORAL_DATE_KEYS: tuple[str, ...] = ("observed_on", "effective_from", "as_of")

SOURCE_REF_FIELDS: tuple[str, ...] = (
    "owner", "object_id", "schema", "generation", "sha256", "selector",
)
# The single place the six authority flags are pinned: all literally false
# (ECD-48). AUTHORITY_FLAGS is derived from it so the flag-name list can never
# drift from the emitted authority objects. VOCABULARY NOTE: these six bare
# names are Technology's OWN emitted-object vocabulary (dossier rows, cards,
# relationships, the root ceiling, and the sealed comparison packet this
# composer checks). They are NOT the shared curation assertion contract's
# authority vocabulary — that block is the five `can_*` flags owned and
# enforced by theme_graph.curation_assertion.v1; the two sets are disjoint
# and must never be merged or substituted for each other.
_FALSE_AUTHORITY: dict[str, bool] = {
    "rank": False, "gate": False, "size": False,
    "veto": False, "originate": False, "open_entry": False,
}
AUTHORITY_FLAGS: tuple[str, ...] = tuple(_FALSE_AUTHORITY)

_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CURATION_REVISION_RE = re.compile(r"^gmirca_[0-9a-f]{32}$")
_REL_PATH_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*\.html$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_THEME_REF_RE = re.compile(r"^(?:theme|ltheme):[A-Za-z0-9_.\-]+$")
_COMPANY_REF_RE = re.compile(r"^co:(?:us|cn|hk|ca|intl):[A-Za-z0-9.\-]+$")
_PRODUCT_REF_RE = re.compile(r"^prod:[A-Za-z0-9][A-Za-z0-9._\-]*$")
_GENERATION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_MODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,11}$")
_OWNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")

_COVERAGE_COUNT_KEYS: tuple[str, ...] = (
    "included", "missing", "stale", "rights_blocked", "unresolved",
)


class EconomicChangeDossierError(ValueError):
    """Composer refusal. The message STARTS with a snake_case reason code."""


# --- public input dataclasses (frozen; plain mappings of the same shape are
# --- accepted and coerced, so sealed fixture providers can stay dict-based) ----


@dataclasses.dataclass(frozen=True, slots=True)
class DossierScope:
    """The accepted scope of one compose. ``offset``/``cursor`` exist only so a
    pagination attempt is a typed, closable input (ECD-44): any non-null value
    REFUSES the compose — this contract has no pages."""

    scope_mode: str
    theme_ref: str
    company_ref: str
    offset: int | None = None
    cursor: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class NativeContext:
    """Mode/freshness and owner context, all injected (no ambient clock)."""

    mode: str
    as_of: str
    cutoff: str
    generation: str
    owner_program: str
    owner_operation: str | None = None
    owner_lane: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class IdentityReceipt:
    """A native identity receipt (NativeRef-like) plus what it binds.

    The six trailing fields are the ONLY source-reference shape this contract
    emits; ``display_ticker`` is display formatting, never proof."""

    entity_id: str
    binding_kind: str
    display_ticker: str | None
    owner: str
    object_id: str
    schema: str
    generation: str
    sha256: str
    selector: str


@dataclasses.dataclass(frozen=True, slots=True)
class CoverageSpec:
    """Known population or explicitly unknown scope, with caller-side counts."""

    population_mode: str
    known_population_total: int | None
    counts: Mapping[str, int | None]
    complete_attested: bool
    family_labels_treated_as_baskets: bool


# --- small helpers ---------------------------------------------------------------


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest_hex(value: Any, width: int) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()[:width]


def _false_authority() -> dict[str, bool]:
    return dict(_FALSE_AUTHORITY)


def _refusal(code: str, explanation: str) -> dict[str, Any]:
    return {"refused": True, "reason_code": code, "explanation": explanation}


def _parse_iso_date(value: str, code: str) -> datetime.date:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise EconomicChangeDossierError(f"{code}: {value!r} is not an ISO date string")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise EconomicChangeDossierError(f"{code}: {value!r} is not a valid date") from exc


def _check_all_false_authority(authority: Any, code: str) -> None:
    if not isinstance(authority, Mapping):
        raise EconomicChangeDossierError(f"{code}: authority section is not a mapping")
    for flag in AUTHORITY_FLAGS:
        if authority.get(flag) is not False:
            raise EconomicChangeDossierError(
                f"{code}: authority flag {flag!r} is not literally false"
            )


def _require_str(value: Any, code: str, *, pattern: re.Pattern[str] | None = None,
                 max_length: int = 200) -> str:
    if not isinstance(value, str) or not value:
        raise EconomicChangeDossierError(f"{code}: expected a non-empty string, got {value!r}")
    if len(value) > max_length:
        raise EconomicChangeDossierError(f"{code}: string exceeds {max_length} chars")
    if pattern is not None and not pattern.match(value):
        raise EconomicChangeDossierError(f"{code}: {value!r} does not match the required grammar")
    return value


def _free_text(value: Any, code: str) -> str:
    """Free text bound: overlong input REFUSES; nothing is silently trimmed."""
    text = value if isinstance(value, str) else ""
    if len(text) > MAX_FREE_TEXT_CHARS:
        raise EconomicChangeDossierError(
            f"free_text_bounds_exceeded: {code} is {len(text)} chars > {MAX_FREE_TEXT_CHARS}"
        )
    return text


def _optional_name(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if 0 < len(text) <= 200 else None


# --- contract validation ---------------------------------------------------------

_VALIDATOR: Any = None


def _contract_validator() -> Any:
    global _VALIDATOR
    if _VALIDATOR is None:
        import jsonschema  # lazy: the contract check is a compose-time concern only

        schema = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        _VALIDATOR = jsonschema.Draft202012Validator(schema)
    return _VALIDATOR


def validate_dossier(payload: Mapping[str, Any]) -> None:
    """Validate a ``technology_economic_change.v1`` payload against the contract.

    Raises :class:`EconomicChangeDossierError` (code ``dossier_schema_violation``)
    naming the first violating path. Pure; reads the contract file only.
    """
    try:
        errors = sorted(
            _contract_validator().iter_errors(payload),
            key=lambda err: [str(p) for p in err.absolute_path],
        )
    except ImportError as exc:  # pragma: no cover - venv always carries jsonschema
        raise EconomicChangeDossierError(
            "contract_validator_unavailable: jsonschema is required to validate a dossier"
        ) from exc
    if errors:
        first = errors[0]
        path = "/".join(str(p) for p in first.absolute_path) or "<root>"
        raise EconomicChangeDossierError(
            f"dossier_schema_violation: {path}: {first.message}"
        )


# --- TR3: the shared curation contract, imported lazily -------------------------


def _load_shared_curation_contract() -> Any | None:
    """Import the shared ``engine.theme_graph.curation_assertion`` lazily (TR3).

    Returns the module, or ``None`` when it is absent (the carrier base) or does
    not expose BOTH callables the composer relies on (``validate_assertion`` and
    ``curation_revision``) — either way the composer must refuse the
    assertion-dependent sections rather than guess at payloads.
    """
    try:
        from engine.theme_graph import curation_assertion as shared
    except ImportError:
        return None
    if not callable(getattr(shared, "validate_assertion", None)) \
            or not callable(getattr(shared, "curation_revision", None)):
        return None  # a partially-present contract is typed unavailable, never a silent zero-row render
    return shared


# --- input coercion --------------------------------------------------------------


def _coerce_scope(value: Any) -> DossierScope:
    if isinstance(value, DossierScope):
        scope = value
    elif isinstance(value, Mapping):
        try:
            scope = DossierScope(
                scope_mode=value.get("scope_mode"),
                theme_ref=value.get("theme_ref"),
                company_ref=value.get("company_ref"),
                offset=value.get("offset"),
                cursor=value.get("cursor"),
            )
        except TypeError as exc:
            raise EconomicChangeDossierError(f"scope_shape_invalid: {exc}") from exc
    else:
        raise EconomicChangeDossierError("scope_shape_invalid: scope is neither DossierScope nor mapping")
    if scope.scope_mode not in ("theme_first", "company_first"):
        raise EconomicChangeDossierError(
            f"scope_shape_invalid: scope_mode {scope.scope_mode!r} is not theme_first/company_first"
        )
    if not isinstance(scope.theme_ref, str) or not _THEME_REF_RE.match(scope.theme_ref):
        raise EconomicChangeDossierError(f"scope_shape_invalid: theme_ref {scope.theme_ref!r}")
    if not isinstance(scope.company_ref, str) or not _COMPANY_REF_RE.match(scope.company_ref):
        raise EconomicChangeDossierError(f"scope_shape_invalid: company_ref {scope.company_ref!r}")
    if scope.offset is not None and (isinstance(scope.offset, bool) or not isinstance(scope.offset, int)):
        raise EconomicChangeDossierError("scope_shape_invalid: offset must be an integer or null")
    if scope.cursor is not None and not isinstance(scope.cursor, str):
        raise EconomicChangeDossierError("scope_shape_invalid: cursor must be a string or null")
    return scope


def _coerce_native_context(value: Any) -> NativeContext:
    if isinstance(value, NativeContext):
        native = value
    elif isinstance(value, Mapping):
        try:
            native = NativeContext(
                mode=value.get("mode"),
                as_of=value.get("as_of"),
                cutoff=value.get("cutoff"),
                generation=value.get("generation"),
                owner_program=value.get("owner_program"),
                owner_operation=value.get("owner_operation"),
                owner_lane=value.get("owner_lane"),
            )
        except TypeError as exc:
            raise EconomicChangeDossierError(f"native_context_shape_invalid: {exc}") from exc
    else:
        raise EconomicChangeDossierError(
            "native_context_shape_invalid: native_context is neither NativeContext nor mapping"
        )
    if not isinstance(native.mode, str) or not _MODE_RE.match(native.mode):
        raise EconomicChangeDossierError(f"native_context_shape_invalid: mode {native.mode!r}")
    if not isinstance(native.generation, str) or not _GENERATION_RE.match(native.generation):
        raise EconomicChangeDossierError(
            f"native_context_shape_invalid: generation {native.generation!r}"
        )
    if not isinstance(native.owner_program, str) or not native.owner_program:
        raise EconomicChangeDossierError("native_context_shape_invalid: owner_program is required")
    _parse_iso_date(native.as_of, "native_context_shape_invalid")
    _parse_iso_date(native.cutoff, "native_context_shape_invalid")
    return native


def _coerce_receipt(value: Any) -> IdentityReceipt:
    if isinstance(value, IdentityReceipt):
        receipt = value
    elif isinstance(value, Mapping):
        try:
            receipt = IdentityReceipt(
                entity_id=value.get("entity_id"),
                binding_kind=value.get("binding_kind"),
                display_ticker=value.get("display_ticker"),
                owner=value.get("owner"),
                object_id=value.get("object_id"),
                schema=value.get("schema"),
                generation=value.get("generation"),
                sha256=value.get("sha256"),
                selector=value.get("selector"),
            )
        except TypeError as exc:
            raise EconomicChangeDossierError(f"identity_receipt_shape_invalid: {exc}") from exc
    else:
        raise EconomicChangeDossierError(
            "identity_receipt_shape_invalid: receipt is neither IdentityReceipt nor mapping"
        )
    code = "identity_receipt_shape_invalid"
    _require_str(receipt.entity_id, code, pattern=re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_.\-]{0,95}$"))
    if receipt.binding_kind not in ("security", "listing", "issuer"):
        raise EconomicChangeDossierError(f"{code}: binding_kind {receipt.binding_kind!r}")
    if receipt.display_ticker is not None and not isinstance(receipt.display_ticker, str):
        raise EconomicChangeDossierError(f"{code}: display_ticker must be a string or null")
    _require_str(receipt.owner, code, pattern=_OWNER_RE)
    _require_str(receipt.object_id, code, max_length=128)
    _require_str(receipt.schema, code, max_length=128)
    _require_str(receipt.generation, code, pattern=_GENERATION_RE)
    _require_str(receipt.sha256, code, pattern=_SHA256_RE)
    _require_str(receipt.selector, code, max_length=256)
    return receipt


def _coerce_coverage(value: Any) -> CoverageSpec:
    if isinstance(value, CoverageSpec):
        cov = value
    elif isinstance(value, Mapping):
        try:
            cov = CoverageSpec(
                population_mode=value.get("population_mode"),
                known_population_total=value.get("known_population_total"),
                counts=value.get("counts") or {},
                complete_attested=value.get("complete_attested"),
                family_labels_treated_as_baskets=value.get("family_labels_treated_as_baskets"),
            )
        except TypeError as exc:
            raise EconomicChangeDossierError(f"coverage_shape_invalid: {exc}") from exc
    else:
        raise EconomicChangeDossierError(
            "coverage_shape_invalid: coverage is neither CoverageSpec nor mapping"
        )
    code = "coverage_shape_invalid"
    if cov.population_mode not in ("known_population", "unknown_scope"):
        raise EconomicChangeDossierError(f"{code}: population_mode {cov.population_mode!r}")
    if cov.known_population_total is not None and (
        isinstance(cov.known_population_total, bool)
        or not isinstance(cov.known_population_total, int)
        or cov.known_population_total < 0
    ):
        raise EconomicChangeDossierError(f"{code}: known_population_total must be a non-negative int or null")
    if cov.population_mode == "known_population" and cov.known_population_total is None:
        raise EconomicChangeDossierError(f"{code}: known_population requires known_population_total")
    if not isinstance(cov.complete_attested, bool):
        raise EconomicChangeDossierError(f"{code}: complete_attested must be a boolean")
    if cov.family_labels_treated_as_baskets is not True and cov.family_labels_treated_as_baskets is not False:
        raise EconomicChangeDossierError(f"{code}: family_labels_treated_as_baskets must be a boolean")
    if cov.family_labels_treated_as_baskets:
        # Research family labels are labels, never approved baskets.
        raise EconomicChangeDossierError(
            "coverage_basket_equivalence_forbidden: research family labels must not be "
            "treated as approved baskets in this contract"
        )
    if not isinstance(cov.counts, Mapping):
        raise EconomicChangeDossierError(f"{code}: counts must be a mapping")
    for key in _COVERAGE_COUNT_KEYS:
        value = cov.counts.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise EconomicChangeDossierError(f"{code}: counts[{key!r}] must be a non-negative int or null")
    return cov


def _coerce_input_vector(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EconomicChangeDossierError("input_vector_shape_invalid: input_vector is not a mapping")
    code = "input_vector_shape_invalid"
    if set(value) != {"engine_version", "native_context_generation", "identity_receipts_digest", "comparison_id"}:
        raise EconomicChangeDossierError(
            f"{code}: closed keys are engine_version/native_context_generation/"
            "identity_receipts_digest/comparison_id"
        )
    if value.get("engine_version") != ENGINE_VERSION:
        raise EconomicChangeDossierError(f"{code}: engine_version must be {ENGINE_VERSION!r}")
    generation = _require_str(value.get("native_context_generation"), code, pattern=_GENERATION_RE)
    digest = _require_str(value.get("identity_receipts_digest"), code, pattern=_SHA256_RE)
    comparison_id = _require_str(value.get("comparison_id"), code, max_length=128)
    return {
        "engine_version": ENGINE_VERSION,
        "native_context_generation": generation,
        "identity_receipts_digest": digest,
        "comparison_id": comparison_id,
    }


def identity_receipts_digest(receipts: Iterable[Any]) -> str:
    """The binding digest of a receipt sequence (canonical JSON, in given order)."""
    payload = [dataclasses.asdict(_coerce_receipt(r)) for r in receipts]
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


# --- sealed comparison handling ---------------------------------------------------


def _check_comparison(comparison: Any) -> dict[str, Any]:
    if not isinstance(comparison, Mapping):
        raise EconomicChangeDossierError("comparison_shape_invalid: comparison is not a mapping")
    if comparison.get("schema") != COMPARISON_SCHEMA_ID:
        raise EconomicChangeDossierError(
            f"comparison_schema_mismatch: expected {COMPARISON_SCHEMA_ID!r}, "
            f"got {comparison.get('schema')!r}"
        )
    if comparison.get("kind") != COMPARISON_KIND:
        raise EconomicChangeDossierError(
            f"comparison_kind_unsupported: expected {COMPARISON_KIND!r}, "
            f"got {comparison.get('kind')!r}"
        )
    if set(comparison) != set(COMPARISON_SECTIONS):
        missing = sorted(set(COMPARISON_SECTIONS) - set(comparison))
        extra = sorted(set(comparison) - set(COMPARISON_SECTIONS))
        raise EconomicChangeDossierError(
            f"comparison_section_mismatch: missing={missing} extra={extra}"
        )
    _require_str(comparison.get("comparison_id"), "comparison_shape_invalid", max_length=128)
    if not isinstance(comparison.get("input_vector"), Mapping):
        raise EconomicChangeDossierError("comparison_shape_invalid: input_vector must be a mapping")
    _check_all_false_authority(comparison.get("authority"), "comparison_authority_violation")
    eligibility = comparison.get("eligibility")
    if not isinstance(eligibility, Mapping) or not isinstance(eligibility.get("eligible"), bool):
        raise EconomicChangeDossierError("comparison_shape_invalid: eligibility.eligible must be a boolean")
    explanation = eligibility.get("explanation")
    if not isinstance(explanation, str):
        raise EconomicChangeDossierError("comparison_shape_invalid: eligibility.explanation must be a string")
    result = comparison.get("result")
    if result is None:
        # Refusal: eligibility must then carry a nonempty explanation.
        if eligibility["eligible"] or not explanation:
            raise EconomicChangeDossierError(
                "comparison_inconsistent: a null result requires an ineligible eligibility "
                "with a nonempty explanation"
            )
    elif isinstance(result, Mapping):
        if not eligibility["eligible"]:
            raise EconomicChangeDossierError(
                "comparison_inconsistent: a present result requires an eligible eligibility"
            )
        missing = [
            key for key in COMPARISON_RESULT_DECIMALS + COMPARISON_RESULT_META
            if not isinstance(result.get(key), str) or not result[key]
        ]
        if missing:
            raise EconomicChangeDossierError(f"comparison_result_incomplete: missing {sorted(missing)}")
    else:
        raise EconomicChangeDossierError("comparison_shape_invalid: result must be null or an object")
    if not isinstance(comparison.get("limitations"), list):
        raise EconomicChangeDossierError("comparison_shape_invalid: limitations must be a list")
    return dict(comparison)


def _comparison_section(comparison: Mapping[str, Any]) -> dict[str, Any]:
    limitations = comparison.get("limitations") or []
    first = limitations[0] if limitations else None
    text = None
    if isinstance(first, Mapping):
        candidate = first.get("text")
        if isinstance(candidate, str) and candidate:
            text = candidate
    elif isinstance(first, str) and first:
        text = first
    if text is None:
        return _refusal(
            "comparison_limitations_absent",
            "The sealed comparison carries no usable first limitation; primary-limitation "
            "text is required minimum content, so the comparison section is refused.",
        )
    result = comparison.get("result")
    eligibility = comparison.get("eligibility") or {}
    explanation = _free_text(eligibility.get("explanation") or "", "comparison eligibility_explanation")
    if isinstance(result, Mapping):
        echoed = {key: result[key] for key in COMPARISON_RESULT_DECIMALS + COMPARISON_RESULT_META}
        admission = "admitted"
    else:
        echoed = None
        admission = "refused"
    correction = comparison.get("correction")
    correction_digest = (
        _digest_hex(correction, 64) if correction is not None else None
    )
    return {
        "comparison_id": comparison["comparison_id"],
        "admission": admission,
        "eligibility_explanation": explanation,
        "result": echoed,
        "primary_limitation": {"text": _free_text(text, "comparison primary_limitation")},
        "correction_digest": correction_digest,
    }


# --- navigation -------------------------------------------------------------------


def _slug_from_ref(ref: str) -> str:
    tail = ref.rsplit(":", 1)[-1].lower()
    if not _SLUG_RE.match(tail):
        raise EconomicChangeDossierError(
            f"navigation_target_invalid: cannot derive a slug from {ref!r}"
        )
    return tail


def _navigation(scope: DossierScope) -> dict[str, str]:
    theme_slug = _slug_from_ref(scope.theme_ref)
    company_slug = _slug_from_ref(scope.company_ref)
    targets = {
        "theme_first": f"technology/economic-change/{theme_slug}/index.html",
        "company_first": f"technology/economic-change/{theme_slug}/{company_slug}.html",
    }
    for key, target in targets.items():
        if not _REL_PATH_RE.match(target):
            raise EconomicChangeDossierError(
                f"navigation_target_invalid: {key} target {target!r} is not a validated relative path"
            )
    return targets


# --- assertion processing -----------------------------------------------------------


@dataclasses.dataclass
class _AssertionOutcome:
    rows: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    counters: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    # (observation_id, subject entity, revision, source object_id): the real
    # curation revision behind each counter edge — provenance is never minted
    # from a digest that is not a curation revision.
    counter_rels: list[tuple[str, str, str, str]] = dataclasses.field(default_factory=list)
    revisions: list[str] = dataclasses.field(default_factory=list)
    unsupported: int = 0
    invalid: int = 0
    after_cutoff: int = 0
    source_unavailable: int = 0
    entity_meta: dict[str, list[tuple[str, str | None, str | None]]] = dataclasses.field(
        default_factory=dict
    )


def _assertion_source_ref(source: Any) -> dict[str, Any] | None:
    """The closed six-field reference, or None when the source is unavailable.

    An assertion renders ONLY after its own source is available — a payload
    whose source section does not yield the closed reference shape is counted
    (``source_unavailable``), never rendered."""
    if not isinstance(source, Mapping):
        return None
    ref: dict[str, Any] = {}
    for field in SOURCE_REF_FIELDS:
        value = source.get(field)
        if not isinstance(value, str) or not value or len(value) > 256:
            return None
        ref[field] = value
    if not _SHA256_RE.match(ref["sha256"]) or not _GENERATION_RE.match(ref["generation"]):
        return None
    if not _OWNER_RE.match(ref["owner"]) or len(ref["object_id"]) > 128 or len(ref["schema"]) > 128:
        return None
    return ref


def _assertion_observed_date(validated: Mapping[str, Any]) -> datetime.date | None:
    temporal = validated.get("temporal")
    if not isinstance(temporal, Mapping):
        return None
    for key in TEMPORAL_DATE_KEYS:
        value = temporal.get(key)
        if isinstance(value, str) and _DATE_RE.match(value):
            try:
                return datetime.date.fromisoformat(value)
            except ValueError:
                continue
    return None


def _observation_text(validated: Mapping[str, Any]) -> str:
    observation = validated.get("observation")
    if isinstance(observation, Mapping) and isinstance(observation.get("text"), str):
        return observation["text"]
    return ""


def _entity_side(value: Any) -> tuple[str | None, str | None, str | None]:
    """(entity_id, display_name, paid_unit) from a subject/object section."""
    if not isinstance(value, Mapping):
        return None, None, None
    entity_id = value.get("entity_id")
    entity_id = entity_id if isinstance(entity_id, str) and entity_id else None
    paid_unit = value.get("paid_unit")
    paid_unit = paid_unit if isinstance(paid_unit, str) and paid_unit else None
    return entity_id, _optional_name(value.get("display_name")), paid_unit


def _record_entity_meta(out: _AssertionOutcome, entity_id: str | None,
                        validated: Mapping[str, Any], display_name: str | None) -> None:
    if entity_id is None or not entity_id.startswith("co:"):
        return
    industrial = validated.get("industrial_context")
    family = None
    if isinstance(industrial, Mapping):
        family = _optional_name(industrial.get("family_label"))
    out.entity_meta.setdefault(entity_id, []).append(
        (validated.get("curation_revision") or "", display_name, family)
    )


def _process_assertions(payloads: Iterable[Any], shared: Any,
                        cutoff: datetime.date) -> _AssertionOutcome:
    out = _AssertionOutcome()
    seen_row_ids: set[str] = set()
    for payload in payloads:
        try:
            validated = shared.validate_assertion(payload)
        except Exception:
            # The shared contract owns its refusal type (CurationAssertionError);
            # any refusal means the payload is not a valid assertion. Counted,
            # never rendered, never raised through.
            out.invalid += 1
            continue
        if not isinstance(validated, Mapping):
            out.invalid += 1
            continue
        try:
            revision = shared.curation_revision(validated)
        except Exception:
            out.invalid += 1
            continue
        if not isinstance(revision, str) or not _CURATION_REVISION_RE.match(revision):
            out.invalid += 1
            continue
        predicate = validated.get("predicate")
        statement_mode = validated.get("statement_mode")
        scope_section = validated.get("scope")
        if not isinstance(scope_section, Mapping) or scope_section.get("vertical") != SUPPORTED_VERTICAL:
            out.unsupported += 1
            continue
        if (predicate, statement_mode) not in SUPPORTED_ASSERTION_FORMS:
            out.unsupported += 1
            continue
        observed = _assertion_observed_date(validated)
        if observed is not None and observed > cutoff:
            # A later supplementary filing cannot appear in an earlier cutoff.
            out.after_cutoff += 1
            continue
        source_ref = _assertion_source_ref(validated.get("source"))
        if source_ref is None:
            out.source_unavailable += 1
            continue
        subject_id, subject_name, _ = _entity_side(validated.get("subject"))
        object_id, object_name, paid_unit = _entity_side(validated.get("object"))
        if subject_id is None:
            out.invalid += 1
            continue
        _record_entity_meta(out, subject_id, validated, subject_name)
        _record_entity_meta(out, object_id, validated, object_name)
        statement = _free_text(
            _observation_text(validated),
            f"assertion statement (curation_revision {revision})",
        )
        if statement_mode == "contrary_observation":
            if not (statement or "").strip():
                # A counter-observation with no statement text cannot be
                # attributed content; counted, never rendered.
                out.invalid += 1
                continue
            observation_id = "tecobs_" + _digest_hex(
                {"revision": revision, "subject": subject_id, "source": source_ref["object_id"]}, 12
            )
            out.counters.append({
                "observation_id": observation_id,
                "statement": statement,
                "attributed_to": {"entity_id": subject_id, "display_name": subject_name},
                "source_ref": source_ref,
                "observed_on": observed.isoformat() if observed is not None else None,
                "effect_on_comparison": "none_display_only",
                "authority": _false_authority(),
            })
            out.counter_rels.append(
                (observation_id, subject_id, revision, source_ref["object_id"])
            )
        else:
            if not (statement or "").strip():
                # An attributed business fact with no statement text is not a fact.
                out.invalid += 1
                continue
            row_id = "tecrow_" + _digest_hex(
                {
                    "predicate": predicate,
                    "subject": subject_id,
                    "object": object_id,
                    "revision": revision,
                    "source": source_ref["object_id"],
                },
                12,
            )
            if row_id in seen_row_ids:
                continue
            seen_row_ids.add(row_id)
            out.rows.append({
                "row_id": row_id,
                "curation_revision": revision,
                "predicate": predicate,
                "statement_mode": statement_mode,
                "subject": {"entity_id": subject_id, "display_name": subject_name},
                "object": {"entity_id": object_id, "display_name": object_name, "paid_unit": paid_unit},
                "statement": statement,
                "source_ref": source_ref,
                "observed_on": observed.isoformat() if observed is not None else None,
                "authority": _false_authority(),
            })
        out.revisions.append(revision)
    out.rows.sort(key=lambda row: row["row_id"])
    out.counters.sort(key=lambda obs: obs["observation_id"])
    out.revisions.sort()
    return out


# --- business projection assembly ----------------------------------------------------


def _cards_and_relationships(out: _AssertionOutcome,
                             comparison_section: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cards: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    def _rel(rel_type: str, from_id: str, to_id: str, revision: str) -> None:
        relationships.append({
            "relationship_id": "tecrel_" + _digest_hex(
                {"rel_type": rel_type, "from": from_id, "to": to_id, "via": revision}, 12
            ),
            "rel_type": rel_type,
            "from_id": from_id,
            "to_id": to_id,
            "via_curation_revision": revision,
            "authority": _false_authority(),
        })

    # Typed fact + provenance + aggregation edges per row; ordering by identifier.
    for row in out.rows:
        revision = row["curation_revision"]
        subject_id = row["subject"]["entity_id"]
        object_id = row["object"]["entity_id"]
        # An unnamed counterparty side yields NO role/procurement edge: the row
        # stays visible, the edge is never invented (no self-edge, no empty endpoint).
        if row["predicate"] == "product_workload_role":
            if object_id:
                _rel("product_has_workload_role", subject_id, object_id, revision)
        elif object_id:
            _rel("product_has_buyer", object_id, subject_id, revision)
        _rel("row_backed_by_source", row["row_id"], row["source_ref"]["object_id"], revision)

    # Cards: one per product/kind, aggregating row ids — never a magnitude.
    # The card key separates a named object from an unnamed one structurally, so an
    # unnamed side can never share a card with a real entity whatever its id spells.
    # Display names are recorded per (kind, id): a buyer card never borrows the
    # display name an identically-spelled entity carries as a product, and vice versa.
    by_product: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    object_names: dict[tuple[str, str], str] = {}
    for row in out.rows:
        object_id = row["object"]["entity_id"]
        named = "named" if object_id else "unnamed"
        key_id = object_id if object_id else ""
        kind = "product_workload_role" if row["predicate"] == "product_workload_role" else "buyer_paid_unit"
        by_product.setdefault((kind, named, key_id), []).append(row)
        name = row["object"]["display_name"]
        if object_id and name:
            object_names.setdefault((kind, object_id), name)
    for (kind, named, product_id), rows in sorted(by_product.items()):
        row_ids = sorted(row["row_id"] for row in rows)
        if named == "named":
            label = object_names.get((kind, product_id), product_id)
        else:  # the null side is the product for a workload role, the counterparty for a paid unit
            label = "Unnamed product" if kind == "product_workload_role" else "Unnamed counterparty"
        title = (
            f"{label} — "
            + ("workload role (attributed)" if kind == "product_workload_role" else "buyer / paid unit (attributed)")
        )
        if len(title) > 200:
            raise EconomicChangeDossierError(
                f"free_text_bounds_exceeded: card title for {product_id!r} exceeds 200 chars"
            )
        body = _free_text(
            f"{len(row_ids)} attributed row(s): " + ", ".join(row_ids),
            f"card body ({kind}, {product_id or 'unnamed'})",
        )
        card_id = "tecard_" + _digest_hex(
            {"kind": kind, "product": product_id if named == "named" else None, "rows": row_ids}, 12
        )
        cards.append({
            "card_id": card_id,
            "card_kind": kind,
            "title": title,
            "body": body,
            "source_refs": [dict(row["source_ref"]) for row in sorted(rows, key=lambda r: r["row_id"])],
            "authority": _false_authority(),
        })
        via_revision = min(row["curation_revision"] for row in rows)
        for row_id in row_ids:
            _rel("row_aggregated_into_card", row_id, card_id, via_revision)

    # Comparison card: the admitted/refused stance plus the primary limitation.
    if isinstance(comparison_section, Mapping) and comparison_section.get("refused") is True:
        admission, limitation = "section refused", ""
    else:
        admission = comparison_section.get("admission")
        limitation = (
            comparison_section.get("primary_limitation", {}).get("text") or ""
        )
    cards.append({
        "card_id": "tecard_" + _digest_hex({"kind": "comparison", "id": "comparison"}, 12),
        "card_kind": "comparison",
        "title": f"Management revenue remaining-year comparison — {admission}",
        "body": _free_text(limitation, "comparison card body"),
        "source_refs": [],
        "authority": _false_authority(),
    })

    # Coverage card: population accounting, explicitly not a completeness claim.
    cards.append({
        "card_id": "tecard_" + _digest_hex({"kind": "coverage", "id": "coverage"}, 12),
        "card_kind": "coverage",
        "title": "Coverage of the accepted scope",
        "body": "Population accounting for the accepted scope only; no sector completeness is claimed.",
        "source_refs": [],
        "authority": _false_authority(),
    })

    for obs in out.counters:
        cards.append({
            "card_id": "tecard_" + _digest_hex({"kind": "counter_observation", "id": obs["observation_id"]}, 12),
            "card_kind": "counter_observation",
            "title": "Counter-observation (attributed, display only)",
            "body": obs["statement"],
            "source_refs": [dict(obs["source_ref"])],
            "authority": _false_authority(),
        })
    for observation_id, subject_id, revision, source_object_id in sorted(out.counter_rels):
        _rel("counter_observation_attributed_to", subject_id, observation_id, revision)
        _rel("row_backed_by_source", observation_id, source_object_id, revision)

    cards.sort(key=lambda card: card["card_id"])
    relationships.sort(key=lambda rel: rel["relationship_id"])
    return cards, relationships


# --- identity / entities ---------------------------------------------------------------


def _format_display_ticker(raw: str | None) -> str | None:
    """Display formatting of a receipt ticker; never proof of anything."""
    if raw is None:
        return None
    formatted = raw.strip().upper()
    return formatted if _TICKER_RE.match(formatted) else None


def _entities(scope: DossierScope, out: _AssertionOutcome,
              receipts_by_entity: Mapping[str, IdentityReceipt]) -> list[dict[str, Any]]:
    entity_ids: set[str] = {scope.company_ref}
    for row in out.rows:
        if row["subject"]["entity_id"].startswith("co:"):
            entity_ids.add(row["subject"]["entity_id"])
    # Only issuer-kind ids become entity rows; a receipt bound to some other id
    # plane still counts toward the digest but mints no entity here.
    entity_ids.update(
        entity_id for entity_id in receipts_by_entity if _COMPANY_REF_RE.match(entity_id)
    )
    entities: list[dict[str, Any]] = []
    for entity_id in sorted(entity_ids):
        display_name: str | None = None
        family_label: str | None = None
        for revision, name, family in sorted(out.entity_meta.get(entity_id, [])):
            if display_name is None and name is not None:
                display_name = name
            if family_label is None and family is not None:
                family_label = family
        receipt = receipts_by_entity.get(entity_id)
        binding = None
        ticker = None
        if receipt is not None:
            binding = {
                "owner": receipt.owner,
                "object_id": receipt.object_id,
                "schema": receipt.schema,
                "generation": receipt.generation,
                "sha256": receipt.sha256,
                "selector": receipt.selector,
            }
            ticker = _format_display_ticker(receipt.display_ticker)
        entities.append({
            "entity_id": entity_id,
            "display_name": display_name,
            "family_label": family_label,
            "binding_state": "bound" if binding is not None else "unbound",
            "security_binding": binding,
            "display_ticker": ticker,
        })
    return entities


# --- the composer ----------------------------------------------------------------------


def compose_technology_economic_change(
    *,
    scope: DossierScope | Mapping[str, Any],
    business_assertions: Iterable[Any],
    comparison: Mapping[str, Any],
    native_context: NativeContext | Mapping[str, Any],
    identity_receipts: Iterable[IdentityReceipt | Mapping[str, Any]],
    input_vector: Mapping[str, Any],
    coverage: CoverageSpec | Mapping[str, Any],
) -> dict[str, Any]:
    """Compose the closed ``technology_economic_change.v1`` projection. Pure.

    Every input is sealed: the comparison dict is consumed exactly as the
    producer validated it (structural checks only, arithmetic never re-derived),
    and curation assertions are usable only through the shared contract. No
    fetch, no model call, no clock, no write. Input-boundary refusals raise
    :class:`EconomicChangeDossierError` (snake_case code first); section-level
    unavailability is a typed refusal object inside the returned dossier.
    """
    scope_o = _coerce_scope(scope)
    native = _coerce_native_context(native_context)
    cov = _coerce_coverage(coverage)
    receipts = [_coerce_receipt(r) for r in identity_receipts]
    iv = _coerce_input_vector(input_vector)
    comparison_o = _check_comparison(comparison)

    # ECD-44: this contract has no pages; a paging attempt refuses the compose.
    if scope_o.offset is not None:
        raise EconomicChangeDossierError(
            f"pagination_not_supported: offset={scope_o.offset!r} was rejected; "
            "narrow the accepted scope instead of paging (pagination_supported=false)"
        )
    if scope_o.cursor is not None:
        raise EconomicChangeDossierError(
            f"pagination_not_supported: cursor={scope_o.cursor!r} was rejected; "
            "narrow the accepted scope instead of paging (pagination_supported=false)"
        )

    # Native input byte bound: refuse oversized native inputs, never trim them.
    native_blob = _canonical_json({
        "native_context": dataclasses.asdict(native),
        "identity_receipts": [dataclasses.asdict(r) for r in receipts],
    })
    native_bytes = len(native_blob.encode("utf-8"))
    if native_bytes > MAX_NATIVE_INPUT_BYTES:
        raise EconomicChangeDossierError(
            f"native_input_bounds_exceeded: native inputs are {native_bytes} bytes "
            f"> {MAX_NATIVE_INPUT_BYTES}"
        )

    # The input vector binds the native inputs it describes.
    if iv["native_context_generation"] != native.generation:
        raise EconomicChangeDossierError(
            "input_vector_binding_mismatch: native_context_generation does not match native_context.generation"
        )
    if iv["comparison_id"] != comparison_o["comparison_id"]:
        raise EconomicChangeDossierError(
            "input_vector_binding_mismatch: comparison_id does not match the comparison"
        )
    if iv["identity_receipts_digest"] != identity_receipts_digest(receipts):
        raise EconomicChangeDossierError(
            "input_vector_binding_mismatch: identity_receipts_digest does not match the receipts"
        )

    _parse_iso_date(native.as_of, "native_context_shape_invalid")
    cutoff = _parse_iso_date(native.cutoff, "native_context_shape_invalid")

    navigation = _navigation(scope_o)
    comparison_section = _comparison_section(comparison_o)

    shared = _load_shared_curation_contract()
    if shared is None:
        # TR3: the iterable is deliberately NOT consumed here — without the
        # shared validator nothing in it can be classified, so it is counted as
        # unknown rather than guessed at.
        business = _refusal(
            "shared_contract_unavailable",
            "The shared theme_graph.curation_assertion.v1 contract module is not "
            "importable on this base, so assertion-dependent content is refused "
            "rather than rendered from unvalidated payloads "
            f"(pinned to macro#7870@45eb37bb, module {SHARED_CONTRACT_MODULE}).",
        )
        out = _AssertionOutcome()
        assertion_counts_available = False
    else:
        out = _process_assertions(business_assertions, shared, cutoff)
        assertion_counts_available = True

    cards, relationships = _cards_and_relationships(out, comparison_section)
    business_projection = {
        "rows": out.rows,
        "cards": cards,
        "relationships": relationships,
        "ordering": "identifier_lexicographic",
    }
    business_section: dict[str, Any] = business if shared is None else business_projection

    # First-unit bounds: refuse, never silently truncate.
    if len(out.rows) > MAX_BUSINESS_ROWS:
        raise EconomicChangeDossierError(
            f"first_unit_bounds_exceeded: business rows {len(out.rows)} > {MAX_BUSINESS_ROWS}; "
            "refuse or require a narrower accepted scope"
        )
    if len(cards) > MAX_CARDS:
        raise EconomicChangeDossierError(
            f"first_unit_bounds_exceeded: cards {len(cards)} > {MAX_CARDS}; "
            "refuse or require a narrower accepted scope"
        )
    if len(relationships) > MAX_TYPED_RELATIONSHIPS:
        raise EconomicChangeDossierError(
            f"first_unit_bounds_exceeded: relationships {len(relationships)} > {MAX_TYPED_RELATIONSHIPS}; "
            "refuse or require a narrower accepted scope"
        )

    receipts_by_entity: dict[str, IdentityReceipt] = {}
    for receipt in sorted(receipts, key=lambda r: (r.owner, r.object_id, r.generation, r.sha256)):
        receipts_by_entity.setdefault(receipt.entity_id, receipt)
    entities = _entities(scope_o, out, receipts_by_entity)
    focus_receipt = receipts_by_entity.get(scope_o.company_ref)
    if focus_receipt is None:
        security_view = _refusal(
            "security_binding_missing",
            "The focus entity has no native identity receipt, so the identity-joined "
            "view is refused; no name-similarity join is attempted.",
        )
    else:
        security_view = _refusal(
            "enrichment_out_of_first_unit_scope",
            "An identity receipt is bound, but market-data enrichment is outside the "
            "first-unit scope, so this view renders nothing.",
        )

    product_ids = sorted({
        row["object"]["entity_id"]
        for row in out.rows
        if row["predicate"] == "product_workload_role" and row["object"]["entity_id"]
        and _PRODUCT_REF_RE.match(row["object"]["entity_id"])
    } | {
        row["object"]["entity_id"]
        for row in out.rows
        if row["predicate"] == "buyer_paid_unit" and row["object"]["entity_id"]
        and _PRODUCT_REF_RE.match(row["object"]["entity_id"])
    })
    business_entity_ids = sorted(
        {scope_o.company_ref}
        | {row["subject"]["entity_id"] for row in out.rows
           if row["subject"]["entity_id"].startswith("co:")}
    )

    coverage_section = {
        "population_mode": cov.population_mode,
        "known_population_total": cov.known_population_total,
        "counts": {
            **{key: cov.counts.get(key) for key in _COVERAGE_COUNT_KEYS},
            "unsupported_assertions": out.unsupported if assertion_counts_available else None,
            "invalid_assertions": out.invalid if assertion_counts_available else None,
            "after_cutoff": out.after_cutoff if assertion_counts_available else None,
            "source_unavailable": out.source_unavailable if assertion_counts_available else None,
        },
        "assertion_counts_available": assertion_counts_available,
        "family_labels": {
            "are_baskets": False,
            "denominator": "known" if cov.population_mode == "known_population" else "unknown",
        },
        "completeness": {
            "complete_within_accepted_scope": cov.complete_attested,
            "sector_completeness_claimed": False,
            "basis": "accepted_scope_only",
        },
    }

    # The digest mapping is the dossier identity contract for exactly the
    # inputs it names: schema, definition_version, the scope identity
    # (scope_mode/theme_ref/company_ref), comparison_id, cutoff, the curation
    # revisions and the bound input vector. Its key set is explicit and its
    # order deliberate (identity -> scope -> sealed inputs -> bindings);
    # canonical JSON sorts keys at serialization time, so order does not feed
    # the digest — but a key enters or leaves this mapping only by deliberate
    # revision, never incidentally. definition_version binds the id to the
    # contract revision that defines this shape, so a definition bump re-ids
    # every dossier on purpose.
    # KNOWN LIMITATION (pre-dating this mapping's definition_version binding):
    # mode, as_of, owner_program (and the other owner fields) and the
    # coverage/omissions input do NOT enter the digest, so a `latest` and a
    # `system_replay` dossier over the same cutoff and generation share ONE
    # dossier_id, and complete vs incomplete coverage likewise. Binding any of
    # those four is a separate identity-design decision, deliberately not
    # taken here.
    dossier_id = "tecd_" + _digest_hex(
        {
            "schema": SCHEMA_ID,
            "definition_version": DEFINITION_VERSION,
            "scope_mode": scope_o.scope_mode,
            "theme_ref": scope_o.theme_ref,
            "company_ref": scope_o.company_ref,
            "comparison_id": comparison_o["comparison_id"],
            "cutoff": native.cutoff,
            "curation_revisions": out.revisions,
            "input_vector": iv,
        },
        32,
    )

    dossier = {
        "schema": SCHEMA_ID,
        "definition_version": DEFINITION_VERSION,
        "dossier_id": dossier_id,
        "kind": "TECHNOLOGY_ECONOMIC_CHANGE",
        "engine_version": ENGINE_VERSION,
        "authority": _false_authority(),
        "authority_ceiling": AUTHORITY_CEILING,
        "display_only": True,
        "owner": {
            "program": native.owner_program,
            "operation": native.owner_operation,
            "lane": native.owner_lane,
        },
        "mode": native.mode,
        "freshness": {"as_of": native.as_of, "cutoff": native.cutoff},
        "scope": {
            "scope_mode": scope_o.scope_mode,
            "theme_ref": scope_o.theme_ref,
            "company_ref": scope_o.company_ref,
        },
        "navigation": navigation,
        "classification": {
            "issuer_pure_play_claimed": False,
            "basis": "issuer_level_classification_out_of_first_unit_scope",
        },
        "selected": {
            "business_entity_ids": business_entity_ids,
            "product_ids": product_ids,
            "input_vector": dict(iv),
        },
        "source_version_vector": {
            "comparison_input_vector": dict(comparison_o["input_vector"]),
            "curation_revisions": list(out.revisions),
        },
        "business": business_section,
        "comparison": comparison_section,
        "counter_observations": out.counters,
        "identity": {
            "entities": entities,
            "views": {"security_enrichment_view": security_view},
        },
        "coverage": coverage_section,
        "bounds": {
            "pagination_supported": False,
            "max_cards": MAX_CARDS,
            "max_business_rows": MAX_BUSINESS_ROWS,
            "max_relationships": MAX_TYPED_RELATIONSHIPS,
            "max_free_text_chars": MAX_FREE_TEXT_CHARS,
            "max_native_input_bytes": MAX_NATIVE_INPUT_BYTES,
            "truncation": "none_refuse_instead",
        },
    }
    validate_dossier(dossier)
    return dossier
