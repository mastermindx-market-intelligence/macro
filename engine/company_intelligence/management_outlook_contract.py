"""Company Intelligence — management-outlook comparison contract, v1.

Pure contract layer for the first comparison kind,
``MANAGEMENT_REVENUE_REMAINING_YEAR``.  It seals a caller payload into a
frozen :class:`ComparableRevenueInput` only when an owner-created
:class:`VerifiedContext` supplies the accepted definition / binding /
clock / rights compatibility receipts; a caller cannot pass booleans that
mean "verified", and a request URL or ticker can never self-certify the
issuer or rights.  Output envelopes are closed objects validated against
``contracts/company_intelligence/management_outlook_comparison.v1.schema.json``.

Boundary notes (Task 2 of the saved plan):

* Every refusal raises :class:`ManagementOutlookContractError` whose message
  STARTS with a snake_case reason code, matching the repo convention for
  contract modules.
* Amount ranges are source guidance ranges; actual rows must be point
  values (low == high).  Midpoints are conventions, not expectations.
* Native refs are caller-transported strings here; only the Task 4
  owner-reader adapter can establish their bytes, identity and eligibility.
  This module checks shape, consistency (one generation per native object)
  and grounding (the perimeter receipt must be one of the cited objects).
* Authority is materially all-false (rank / gate / size / veto / originate /
  open_entry).  No promotion or surprise field of any kind exists in the
  contract; the forbidden-key scan below rejects any attempt to add one.
  The E1 ``basis_match`` behavior elsewhere in Company/Earnings is
  untouched, and no scoring of the new period against its guide was added
  here.
* First-unit bounds: one issuer, one additive metric (revenue), at most four
  atomic fiscal periods, six role families, sixteen role rows, sixty-four
  native refs, sixteen role-generation pairs.  Complex fiscal calendars
  outside the admitted profile refuse rather than compress.  A larger native
  use case requires a separately reviewed bound, not an unbounded default.
* Normalized input decimal strings match
  ``-?(?:0|[1-9][0-9]{0,11})(?:\\.[0-9]{1,6})?`` (absolute value below 10^12,
  at most six fractional digits, no exponent form, no NaN, no signed
  non-finite spellings, no booleans).  Derived result strings may carry a
  seventh fractional digit from the midpoint division and stay below 10^15
  (16 admitted role rows at the input ceiling sum to ~1.6e13; the bound
  keeps headroom while staying far inside Decimal precision 34).
  Intermediate values are never rounded and Decimal never passes through a
  binary floating step.
* Content identity (``comparison_id``) is a sha256 over the canonical
  envelope minus the correction lineage, so a corrected re-issue with
  identical values keeps value identity while carrying a different
  predecessor link.  There is no wall-clock field anywhere in the envelope,
  so a render timestamp can never leak into identity; a changed source
  generation, definition, perimeter decision or formula revision changes
  identity even when every number coincides.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
import re
from typing import Literal, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonschemaValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACT_PATH = REPO_ROOT / "contracts" / "company_intelligence" / "management_outlook_comparison.v1.schema.json"

SCHEMA_ID = "management_outlook_comparison.v1"
REQUEST_SCHEMA_ID = "management_outlook_comparison_request.v1"
KIND = "MANAGEMENT_REVENUE_REMAINING_YEAR"
FORMULA_REVISION = "management_outlook_remaining_year/v1"
CONTRACT_SCALE = "millions"
DECIMAL_CONTEXT_PREC = 34
COMPARISON_ID_PREFIX = "moc_"

ROLE_FAMILIES = ("FY_A", "FY_B", "ACTUAL_C_A", "ACTUAL_C_B", "GUIDE_N_A", "ACTUAL_N_B")
ROLE_FAMILY_SET = frozenset(ROLE_FAMILIES)
ANNUAL_ROLES = ("FY_A", "FY_B")
ACTUAL_ROLES = ("ACTUAL_C_A", "ACTUAL_C_B", "ACTUAL_N_B")
GUIDE_ROLES = ("FY_A", "FY_B", "GUIDE_N_A")
ROLE_PARTITION_EXPECTATION = {
    "FY_A": "annual",
    "FY_B": "annual",
    "ACTUAL_C_A": "completed",
    "ACTUAL_C_B": "completed",
    "GUIDE_N_A": "newly_completed",
    "ACTUAL_N_B": "newly_completed",
}

ADDITIVE_METRICS = frozenset({"revenue"})
NON_ADDITIVE_METRICS = frozenset({
    "gross_margin", "operating_margin", "net_margin", "gross_margin_pct",
    "operating_margin_pct", "eps", "eps_diluted", "margin",
})
CURRENCIES = frozenset({
    "USD", "EUR", "GBP", "JPY", "CNY", "HKD", "CAD", "AUD", "CHF",
    "SEK", "KRW", "TWD", "INR", "SGD", "MXN", "BRL",
})
ACCOUNTING_BASES = frozenset({"GAAP", "IFRS", "NON_GAAP"})

MAX_ATOMIC_PERIODS = 4
MAX_ROLE_ROWS = 16
MAX_NATIVE_REFS = 64
MAX_ROLE_GENERATIONS = 16
MAX_REFS_PER_ROLE_ROW = 8  # request-layer twin of the contract's input_roles[].refs_sha256 maxItems
MIN_FISCAL_YEAR = 2000
MAX_FISCAL_YEAR = 2100

INPUT_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?$")
RESULT_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]{0,14})(?:\.[0-9]{1,7})?$")
INPUT_CEILING = Decimal(10) ** 12
RESULT_CEILING = Decimal(10) ** 15

ISSUER_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.-]{0,63}$")
PERIOD_KEY_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z_.-]{0,31}$")
OWNER_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
OBJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
NATIVE_SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_.]{2,127}\.v[0-9]{1,3}$")
GENERATION_RE = re.compile(r"^[0-9a-f]{16,64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Accepted owner field/span selector only: a whitelisted dotted field path
# with an optional [start:end] span.  Eval-style and dunder selectors can
# never match, so they are refused before any consumer sees them.
SELECTOR_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}(?:\.[a-z][a-z0-9_]{0,63})*(?:\[[0-9]+:[0-9]+\])?$")

AUTHORITY_FLAGS = ("rank", "gate", "size", "veto", "originate", "open_entry")
# Rejection-scan list: any of these keys appearing in a result envelope is a
# forbidden promotion/surprise field and the envelope is refused.  These
# literals exist ONLY to be rejected; the contract emits none of them.
FORBIDDEN_PROMOTION_KEYS = frozenset({
    "rank", "ranking", "gate", "gated", "gating", "size", "sizing",
    "position_size", "veto", "originate", "open_entry", "score",
    "confidence", "probability", "consensus", "beat", "miss", "forecast",
    "expected_value", "expected_impact", "surprise", "target_price",
    "valuation", "trade", "recommendation", "signal", "alpha", "weight",
    "distribution", "upside", "downside",
})

ELIGIBILITY_REASONS = (
    "missing_role", "source_unverified", "identity_unresolved",
    "source_not_eligible_at_cut", "fiscal_partition_mismatch",
    "definition_accounting_fx_mismatch", "perimeter_not_comparable",
    "rights_blocked", "unsupported_metric", "non_additive_metric",
    "invalid_range", "request_bound_exceeded", "no_remaining_horizon",
)
CHECKED_DIMENSIONS = (
    "issuer_identity", "source_verification", "cut_eligibility",
    "fiscal_partition", "definition_accounting_fx",
    "perimeter_comparability", "rights", "metric_support",
    "range_validity", "request_bounds", "remaining_horizon",
)
LIMITATIONS = (
    "midpoints are conventions, not expectations",
    "guidance endpoints are source ranges, not expectations",
    "values are normalized to the contract scale; native precision and units remain in source receipts",
    "actuals are point values; guidance rows carry source ranges",
    "a null result retains input references for explanation only",
)
ELIGIBLE_EXPLANATION = "every admitted dimension was checked for this comparison kind"

RESULT_SECTIONS = (
    "schema", "comparison_id", "kind", "subject", "fiscal_partition",
    "input_roles", "input_vector", "eligibility", "result", "limitations",
    "correction", "authority",
)
REQUEST_TOP_KEYS = frozenset({
    "schema", "kind", "subject", "fiscal_partition", "input_roles",
    "perimeter_receipt", "input_vector_sha256",
})
SUBJECT_KEYS = frozenset({"issuer_id", "fiscal_year", "metric_id", "currency", "accounting_basis", "scale"})
PARTITION_KEYS = frozenset({"periods", "completed", "newly_completed", "remaining"})
PERIOD_FIELDS = frozenset({"key", "start", "end_exclusive"})
ROLE_ROW_KEYS = frozenset({"role", "low", "high", "refs", "definition_ref", "period_keys"})
NATIVE_REF_KEYS = frozenset({"owner", "object_id", "schema", "generation", "sha256", "selector"})
SERIALIZE_KEYS = frozenset({
    "subject", "fiscal_partition", "input_roles", "input_vector",
    "eligible", "reasons", "explanation", "values", "limitations",
    "correction",
})
RESULT_VALUE_KEYS = (
    "annual_midpoint_change", "new_period_deviation",
    "prior_actual_revision", "earlier_remaining", "later_remaining",
    "remaining_change",
)


class ManagementOutlookContractError(ValueError):
    """Refusal whose message starts with a snake_case reason code."""


def _fail(code: str, detail: str) -> None:
    raise ManagementOutlookContractError(f"{code}: {detail}")


def _require_closed(raw, allowed: frozenset, where: str) -> None:
    if not isinstance(raw, Mapping):
        _fail("invalid_request_shape", f"{where} must be an object, got {type(raw).__name__}")
    extra = sorted(set(raw) - allowed)
    if extra:
        _fail("unknown_key", f"{where} carries unknown key(s) {extra}; a request URL or ticker cannot self-certify issuer or rights")
    absent = sorted(allowed - set(raw))
    if absent:
        _fail("invalid_request_shape", f"{where} is missing key(s) {absent}")


# ---------------------------------------------------------------- dataclasses

@dataclass(frozen=True)
class Period:
    key: str
    start: date
    end_exclusive: date


@dataclass(frozen=True)
class NativeRef:
    owner: str
    object_id: str
    schema: str
    generation: str
    sha256: str
    selector: str


@dataclass(frozen=True)
class Amount:
    low: Decimal
    high: Decimal
    refs: tuple[NativeRef, ...]
    definition_ref: NativeRef
    period_keys: tuple[str, ...]


@dataclass(frozen=True)
class RoleAmount:
    role: Literal["FY_A", "FY_B", "ACTUAL_C_A", "ACTUAL_C_B", "GUIDE_N_A", "ACTUAL_N_B"]
    amount: Amount


@dataclass(frozen=True)
class ComparableRevenueInput:
    issuer_id: str
    fiscal_year: int
    metric_id: str
    currency: str
    accounting_basis: str
    perimeter_receipt: NativeRef
    fiscal_periods: tuple[Period, ...]
    completed: tuple[str, ...]
    newly_completed: tuple[str, ...]
    remaining: tuple[str, ...]
    role_amounts: tuple[RoleAmount, ...]
    input_vector_sha256: str


@dataclass(frozen=True)
class VerifiedContext:
    """Owner-created binding of accepted compatibility receipts.

    There is deliberately no boolean field anywhere: acceptance is the
    presence of the four accepted native receipts plus the accepted
    issuer, and every one of them is checked against the payload.
    """
    definition_receipt: NativeRef
    binding_receipt: NativeRef
    clock_receipt: NativeRef
    rights_receipt: NativeRef
    issuer_id: str


# ---------------------------------------------------------------- schema load

@lru_cache(maxsize=1)
def load_contract_schema() -> dict:
    with CONTRACT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _contract_validator() -> Draft202012Validator:
    schema = load_contract_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


# ---------------------------------------------------------------- parsing

def _parse_native_ref(raw, where: str) -> NativeRef:
    _require_closed(raw, NATIVE_REF_KEYS, where)
    parts = {}
    for field in ("owner", "object_id", "schema", "generation", "sha256", "selector"):
        value = raw[field]
        if not isinstance(value, str) or not value:
            _fail("invalid_source_ref", f"{where}.{field} must be a nonempty string")
        parts[field] = value
    checks = (
        ("owner", OWNER_RE, "invalid_source_ref"),
        ("object_id", OBJECT_ID_RE, "invalid_source_ref"),
        ("schema", NATIVE_SCHEMA_RE, "invalid_source_ref"),
        ("generation", GENERATION_RE, "invalid_source_ref"),
        ("sha256", SHA256_RE, "invalid_source_ref"),
        ("selector", SELECTOR_RE, "invalid_source_selector"),
    )
    for field, pattern, code in checks:
        if not pattern.fullmatch(parts[field]):
            _fail(code, f"{where}.{field}={parts[field]!r} is not an accepted owner selector value")
    return NativeRef(**parts)


def _validate_context_receipt(receipt, field: str, code: str) -> NativeRef:
    if receipt is None:
        _fail(code, f"verified context has no accepted {field} receipt")
    if isinstance(receipt, NativeRef):
        raw = {"owner": receipt.owner, "object_id": receipt.object_id, "schema": receipt.schema,
               "generation": receipt.generation, "sha256": receipt.sha256, "selector": receipt.selector}
    elif isinstance(receipt, Mapping):
        raw = receipt
    else:
        _fail("source_unverified", f"verified context {field} receipt is not a native ref")
    return _parse_native_ref(raw, f"verified_context.{field}")


def _decimal_from_string(raw, where: str) -> Decimal:
    if isinstance(raw, bool) or not isinstance(raw, str):
        _fail("amount_not_string", f"{where} must be a decimal string, got {type(raw).__name__}")
    if not INPUT_DECIMAL_RE.fullmatch(raw):
        _fail("invalid_amount",
              f"{where}={raw!r} is outside the normalized decimal envelope "
              "(absolute value below 10^12, at most six fractional digits, no exponent form)")
    return Decimal(raw)


def _format_decimal(value: Decimal, pattern: re.Pattern, ceiling: Decimal, code: str, where: str) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        _fail(code, f"{where} is not a finite Decimal")
    if value == 0:
        text = "0"
    else:
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
    if abs(value) >= ceiling or not pattern.fullmatch(text):
        _fail(code, f"{where}={text!r} is outside the serializable decimal envelope")
    return text


# ---------------------------------------------------------------- digest

def _canonical_amount_text(raw):
    """Digest amounts by value, not spelling: "1006.4260" and "1006.426" are one quantity.

    Only strings inside the accepted decimal envelope are canonicalized; anything
    else is digested verbatim and refused later by the validator.
    """
    if isinstance(raw, str) and INPUT_DECIMAL_RE.fullmatch(raw):
        return _format_decimal(Decimal(raw), INPUT_DECIMAL_RE, INPUT_CEILING, "invalid_amount", "digest")
    return raw


def _canonical_role_row(row: Mapping) -> dict:
    # A citation repeated verbatim is one citation: the digest is over the distinct set.
    refs = [list(ref) for ref in sorted(
        {(r["owner"], r["object_id"], r["schema"], r["generation"], r["sha256"], r["selector"])
         for r in row["refs"]},
    )]
    return {
        "role": row["role"],
        "low": _canonical_amount_text(row["low"]), "high": _canonical_amount_text(row["high"]),
        "period_keys": list(row["period_keys"]),
        "refs": refs,
        "definition_ref": sorted(
            [row["definition_ref"]["owner"], row["definition_ref"]["object_id"],
             row["definition_ref"]["schema"], row["definition_ref"]["generation"],
             row["definition_ref"]["sha256"], row["definition_ref"]["selector"]]),
    }


def compute_input_vector_sha256(payload: Mapping) -> str:
    """Order-insensitive digest of the semantic input vector.

    Reordering role rows or the refs inside a row leaves the digest
    unchanged; changing any amount, period fact, perimeter decision,
    definition or native generation changes it.
    """
    if not isinstance(payload, Mapping):
        _fail("invalid_request_shape", "payload must be an object")
    subject = payload.get("subject")
    partition = payload.get("fiscal_partition")
    roles = payload.get("input_roles")
    if not isinstance(subject, Mapping) or not isinstance(partition, Mapping) or not isinstance(roles, list):
        _fail("invalid_request_shape", "payload misses subject/fiscal_partition/input_roles")
    core_subject = {key: subject[key] for key in
                    ("issuer_id", "fiscal_year", "metric_id", "currency", "accounting_basis", "scale")
                    if key in subject}
    periods = sorted(partition.get("periods", []), key=lambda p: (p["start"], p["end_exclusive"], p["key"]))
    canonical = {
        "subject": core_subject,
        "fiscal_partition": {
            "periods": [dict(p) for p in periods],
            "completed": list(partition.get("completed", [])),
            "newly_completed": list(partition.get("newly_completed", [])),
            "remaining": list(partition.get("remaining", [])),
        },
        "input_roles": sorted((_canonical_role_row(row) for row in roles),
                              key=lambda r: (r["role"], r["period_keys"], r["low"], r["high"],
                                             r["definition_ref"], r["refs"])),
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compute_comparison_id(payload: Mapping) -> str:
    """Content identity: everything except the correction lineage."""
    if not isinstance(payload, Mapping):
        _fail("invalid_request_shape", "payload must be an object")
    canonical = {key: value for key, value in payload.items()
                 if key not in ("comparison_id", "correction")}
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return COMPARISON_ID_PREFIX + hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- request validation

def validate_comparison_request(payload, *, verified_context) -> ComparableRevenueInput:
    if not isinstance(payload, Mapping):
        _fail("invalid_request_shape", "payload must be an object")
    extra = sorted(set(payload) - REQUEST_TOP_KEYS)
    if extra:
        _fail("unknown_key", f"payload carries unknown key(s) {extra}; a request URL or ticker cannot self-certify issuer or rights")

    if payload.get("schema") != REQUEST_SCHEMA_ID:
        _fail("schema_mismatch", f"expected {REQUEST_SCHEMA_ID!r}, got {payload.get('schema')!r}")
    if payload.get("kind") != KIND:
        _fail("unsupported_kind", f"only {KIND} is admitted in this first unit, got {payload.get('kind')!r}")

    subject = payload.get("subject")
    _require_closed(subject, SUBJECT_KEYS, "subject")
    issuer_id = subject["issuer_id"]
    if not isinstance(issuer_id, str) or not ISSUER_ID_RE.fullmatch(issuer_id):
        _fail("invalid_issuer_id", f"subject.issuer_id={issuer_id!r} is not an accepted issuer slug")
    fiscal_year = subject["fiscal_year"]
    if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int):
        _fail("invalid_request_shape", "subject.fiscal_year must be an integer, not a boolean")
    if not (MIN_FISCAL_YEAR <= fiscal_year <= MAX_FISCAL_YEAR):
        _fail("fiscal_year_out_of_profile", f"subject.fiscal_year={fiscal_year} outside {MIN_FISCAL_YEAR}..{MAX_FISCAL_YEAR}")
    metric_id = subject["metric_id"]
    if metric_id in NON_ADDITIVE_METRICS:
        _fail("non_additive_metric", f"metric {metric_id!r} is not additive over fiscal periods")
    if metric_id not in ADDITIVE_METRICS:
        _fail("unsupported_metric", f"metric {metric_id!r} is not admitted for {KIND}")
    currency = subject["currency"]
    if currency not in CURRENCIES:
        _fail("unknown_currency", f"subject.currency={currency!r} is not an admitted currency code")
    basis = subject["accounting_basis"]
    if basis not in ACCOUNTING_BASES:
        _fail("unknown_accounting_basis", f"subject.accounting_basis={basis!r} is not admitted")
    if subject["scale"] != CONTRACT_SCALE:
        _fail("unsupported_scale", f"source normalization must be an exact accepted unit transformation into {CONTRACT_SCALE!r}, got {subject['scale']!r}")

    if verified_context is None or not isinstance(verified_context, VerifiedContext):
        _fail("source_unverified", "an owner-created VerifiedContext binding is required; caller claims prove nothing")
    context_definition = _validate_context_receipt(verified_context.definition_receipt, "definition", "definition_accounting_fx_mismatch")
    _validate_context_receipt(verified_context.binding_receipt, "binding", "identity_unresolved")
    _validate_context_receipt(verified_context.clock_receipt, "clock", "source_not_eligible_at_cut")
    _validate_context_receipt(verified_context.rights_receipt, "rights", "rights_blocked")
    if verified_context.issuer_id != issuer_id:
        _fail("identity_unresolved", f"context issuer {verified_context.issuer_id!r} disagrees with payload issuer {issuer_id!r}")

    partition = payload.get("fiscal_partition")
    _require_closed(partition, PARTITION_KEYS, "fiscal_partition")
    raw_periods = partition["periods"]
    if not isinstance(raw_periods, list):
        _fail("invalid_request_shape", "fiscal_partition.periods must be a list")
    if len(raw_periods) > MAX_ATOMIC_PERIODS:
        _fail("request_bound_exceeded", f"{len(raw_periods)} atomic periods exceed the first-unit maximum of {MAX_ATOMIC_PERIODS}; complex fiscal calendars refuse rather than compress")
    if not raw_periods:
        _fail("fiscal_partition_mismatch", "the selected fiscal year has no atomic periods")
    periods_by_key: dict[str, Period] = {}
    for index, raw_period in enumerate(raw_periods):
        _require_closed(raw_period, PERIOD_FIELDS, f"periods[{index}]")
        key = raw_period["key"]
        if not isinstance(key, str) or not PERIOD_KEY_RE.fullmatch(key):
            _fail("invalid_period_key", f"periods[{index}].key={key!r} is not an accepted period key")
        if key in periods_by_key:
            _fail("duplicate_period_key", f"period key {key!r} appears more than once")
        try:
            start = date.fromisoformat(raw_period["start"])
            end_exclusive = date.fromisoformat(raw_period["end_exclusive"])
        except (TypeError, ValueError):
            _fail("invalid_period_date", f"periods[{index}] dates must be ISO YYYY-MM-DD strings")
        if start >= end_exclusive:
            _fail("reversed_period_dates", f"periods[{index}] ({key!r}) has start not before end_exclusive")
        periods_by_key[key] = Period(key=key, start=start, end_exclusive=end_exclusive)
    ordered_keys = [p.key for p in sorted(periods_by_key.values(), key=lambda p: (p.start, p.end_exclusive))]
    sorted_periods = sorted(periods_by_key.values(), key=lambda p: (p.start, p.end_exclusive))
    for previous, following in zip(sorted_periods, sorted_periods[1:]):
        if previous.end_exclusive > following.start:
            _fail("period_overlap", f"periods {previous.key!r} and {following.key!r} overlap; a cumulative fact may not sit beside the atomic periods it aggregates")
        if previous.end_exclusive != following.start:
            _fail("partition_gap", f"periods {previous.key!r} and {following.key!r} leave an interior date gap")
    position = {key: index for index, key in enumerate(ordered_keys)}

    cells: dict[str, list[str]] = {}
    for cell in ("completed", "newly_completed", "remaining"):
        keys = partition[cell]
        if not isinstance(keys, list) or any(not isinstance(k, str) for k in keys):
            _fail("invalid_request_shape", f"fiscal_partition.{cell} must be a list of period keys")
        for key in keys:
            if key not in periods_by_key:
                _fail("unknown_period_key", f"fiscal_partition.{cell} cites unknown period key {key!r}")
        cells[cell] = keys
    membership: dict[str, list[str]] = {}
    for cell, keys in cells.items():
        for key in keys:
            membership.setdefault(key, []).append(cell)
    for key, owners in membership.items():
        if len(owners) > 1:
            _fail("partition_overlap", f"period {key!r} belongs to {owners}; C/N/R must be nonoverlapping")
    if set(membership) != set(ordered_keys):
        left_out = sorted(set(ordered_keys) - set(membership))
        _fail("partition_gap", f"period(s) {left_out} sit in no C/N/R cell; the partition must be complete")
    sequence = [position[key] for cell in ("completed", "newly_completed", "remaining") for key in cells[cell]]
    if sequence != sorted(sequence):
        _fail("partition_not_chronological", "C then N then R must follow the chronological period order")

    raw_roles = payload.get("input_roles")
    if not isinstance(raw_roles, list):
        _fail("invalid_request_shape", "input_roles must be a list")
    if len(raw_roles) > MAX_ROLE_ROWS:
        _fail("request_bound_exceeded", f"{len(raw_roles)} role rows exceed the first-unit maximum of {MAX_ROLE_ROWS}")

    role_amounts: list[RoleAmount] = []
    all_refs: list[NativeRef] = []
    generation_by_object: dict[tuple[str, str, str], str] = {}
    sha_by_object_generation: dict[tuple[str, str, str, str], str] = {}
    for index, raw_row in enumerate(raw_roles):
        where = f"input_roles[{index}]"
        _require_closed(raw_row, ROLE_ROW_KEYS, where)
        role = raw_row["role"]
        if role not in ROLE_FAMILY_SET:
            _fail("unknown_role", f"{where}.role={role!r} is not one of {sorted(ROLE_FAMILY_SET)}")
        low = _decimal_from_string(raw_row["low"], f"{where}.low")
        high = _decimal_from_string(raw_row["high"], f"{where}.high")
        if low > high:
            _fail("invalid_range", f"{where} has low {low} above high {high}; guidance ranges may not be reversed")
        raw_refs = raw_row["refs"]
        if not isinstance(raw_refs, list) or not raw_refs:
            _fail("missing_source_ref", f"{where}.refs must cite at least one native source object")
        # A citation repeated verbatim carries no further information: the sealed
        # request (and therefore comparison_id / input_vector_sha256) is over the
        # distinct citations, so the identity agrees with the deduplicated echo.
        refs = tuple(_unique_in_order(_parse_native_ref(ref, f"{where}.refs[]") for ref in raw_refs))
        distinct_row_refs = {ref.sha256 for ref in refs}
        if len(distinct_row_refs) > MAX_REFS_PER_ROLE_ROW:
            _fail("request_bound_exceeded", f"{where} cites {len(distinct_row_refs)} distinct native refs; the first-unit maximum per role row is {MAX_REFS_PER_ROLE_ROW}")
        definition_ref = _parse_native_ref(raw_row["definition_ref"], f"{where}.definition_ref")
        if definition_ref != context_definition:
            _fail("definition_accounting_fx_mismatch", f"{where} definition disagrees with the accepted definition receipt")
        raw_keys = raw_row["period_keys"]
        if not isinstance(raw_keys, list) or any(not isinstance(k, str) for k in raw_keys):
            _fail("invalid_request_shape", f"{where}.period_keys must be a list of period keys")
        for key in raw_keys:
            if key not in periods_by_key:
                _fail("unknown_period_key", f"{where} cites unknown period key {key!r}")
        for ref in refs + (definition_ref,):
            all_refs.append(ref)
            object_key = (ref.owner, ref.object_id, ref.selector)
            seen_generation = generation_by_object.get(object_key)
            if seen_generation is None:
                generation_by_object[object_key] = ref.generation
            elif seen_generation != ref.generation:
                _fail("mixed_generation", f"native object {object_key} is cited at generations {seen_generation} and {ref.generation}; half of one generation and half of another is an error")
            version_key = object_key + (ref.generation,)
            seen_sha = sha_by_object_generation.get(version_key)
            if seen_sha is None:
                sha_by_object_generation[version_key] = ref.sha256
            elif seen_sha != ref.sha256:
                _fail("ref_inconsistency", f"native object {object_key} at generation {ref.generation} is cited with two different digests")
        role_amounts.append(RoleAmount(role=role, amount=Amount(
            low=low, high=high, refs=refs, definition_ref=definition_ref,
            period_keys=tuple(raw_keys))))
    if len(all_refs) > MAX_NATIVE_REFS:
        _fail("request_bound_exceeded", f"{len(all_refs)} native refs exceed the first-unit maximum of {MAX_NATIVE_REFS}")
    role_generations = {(row.role, ref.owner, ref.object_id, ref.selector, ref.generation)
                        for row in role_amounts for ref in row.amount.refs}
    if len(role_generations) > MAX_ROLE_GENERATIONS:
        _fail("request_bound_exceeded", f"{len(role_generations)} role-generation pairs exceed the first-unit maximum of {MAX_ROLE_GENERATIONS}")

    rows_by_role: dict[str, list[RoleAmount]] = {}
    for row in role_amounts:
        rows_by_role.setdefault(row.role, []).append(row)
    for role in ANNUAL_ROLES:
        rows = rows_by_role.get(role, [])
        if not rows:
            _fail("missing_role", f"no {role} row; both annual vintages are required")
        if len(rows) > 1:
            _fail("duplicate_role_row", f"{len(rows)} {role} rows; exactly one annual row per vintage is admitted")
        if rows[0].amount.period_keys != tuple(ordered_keys):
            _fail("fiscal_year_mismatch", f"{role} must span exactly the selected fiscal year {tuple(ordered_keys)}, got {rows[0].amount.period_keys}")
    for role in ("ACTUAL_C_A", "ACTUAL_C_B"):
        _check_cell_coverage(rows_by_role.get(role, []), cells["completed"], role)
    for role in ("GUIDE_N_A", "ACTUAL_N_B"):
        _check_cell_coverage(rows_by_role.get(role, []), cells["newly_completed"], role)
    for role in ACTUAL_ROLES:
        for row in rows_by_role.get(role, []):
            if row.amount.low != row.amount.high:
                _fail("actual_not_point", f"{role} rows must be point values (low == high), got {row.amount.low}..{row.amount.high}")

    perimeter_receipt = _parse_native_ref(payload.get("perimeter_receipt"), "perimeter_receipt")
    if perimeter_receipt not in all_refs:
        _fail("perimeter_not_comparable", "the declared perimeter receipt is not among the cited native objects, so the perimeter is not comparable with the evidence read")

    declared_digest = payload.get("input_vector_sha256")
    recomputed = compute_input_vector_sha256(payload)
    if declared_digest is not None:
        if not isinstance(declared_digest, str) or declared_digest != recomputed:
            _fail("input_vector_mismatch", "declared input_vector_sha256 disagrees with the recomputed digest of the semantic input vector")

    return ComparableRevenueInput(
        issuer_id=issuer_id,
        fiscal_year=fiscal_year,
        metric_id=metric_id,
        currency=currency,
        accounting_basis=basis,
        perimeter_receipt=perimeter_receipt,
        fiscal_periods=tuple(sorted_periods),
        completed=tuple(cells["completed"]),
        newly_completed=tuple(cells["newly_completed"]),
        remaining=tuple(cells["remaining"]),
        role_amounts=tuple(role_amounts),
        input_vector_sha256=recomputed,
    )


def _check_cell_coverage(rows: list, expected_keys: list, role: str) -> None:
    expected = list(expected_keys)
    seen: dict[str, int] = {}
    foreign = []
    for row in rows:
        if len(row.amount.period_keys) != 1:
            _fail("fiscal_partition_mismatch", f"{role} rows cover exactly one atomic period each, got {row.amount.period_keys}")
        key = row.amount.period_keys[0]
        seen[key] = seen.get(key, 0) + 1
        if key not in expected:
            foreign.append(key)
    if foreign:
        _fail("fiscal_partition_mismatch", f"{role} rows cite period(s) {sorted(set(foreign))} outside the partition cell this role covers")
    for key in expected:
        if key not in seen:
            _fail("missing_role_row", f"{role} has no row for period {key!r}; an absent row in a nonempty partition is an error, never a silent zero")
    for key, count in seen.items():
        if count > 1:
            _fail("duplicate_role_row", f"{role} has {count} rows for period {key!r}")


# ---------------------------------------------------------------- echo + serialization

def _unique_in_order(values):
    """First-seen order, duplicates dropped — the echo never repeats a digest."""
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def serialize_input_echo(inputs: ComparableRevenueInput) -> dict:
    """Permitted input references echoed into the result envelope."""
    order = {role: index for index, role in enumerate(ROLE_FAMILIES)}
    rows = []
    generations = []
    seen_generations: set[tuple[str, str]] = set()
    for row in sorted(inputs.role_amounts, key=lambda r: (order[r.role], r.amount.period_keys)):
        amount = row.amount
        rows.append({
            "role": row.role,
            "low": _format_decimal(amount.low, INPUT_DECIMAL_RE, INPUT_CEILING, "invalid_amount", f"{row.role}.low"),
            "high": _format_decimal(amount.high, INPUT_DECIMAL_RE, INPUT_CEILING, "invalid_amount", f"{row.role}.high"),
            "period_keys": list(amount.period_keys),
            "refs_sha256": _unique_in_order(
                ref.sha256 for ref in
                sorted(amount.refs, key=lambda r: (r.owner, r.object_id, r.schema, r.generation, r.sha256, r.selector))
            ),
            "definition_sha256": amount.definition_ref.sha256,
        })
        for ref in sorted(amount.refs, key=lambda r: (r.owner, r.object_id, r.selector, r.generation)):
            pair = (row.role, ref.generation)
            if pair in seen_generations:
                continue  # one echo per (role, generation); the request-layer bound counts the same set
            seen_generations.add(pair)
            generations.append({"role": row.role, "generation": ref.generation})
    return {
        "subject": {
            "issuer_id": inputs.issuer_id,
            "fiscal_year": inputs.fiscal_year,
            "metric_id": inputs.metric_id,
            "currency": inputs.currency,
            "accounting_basis": inputs.accounting_basis,
            "scale": CONTRACT_SCALE,
        },
        "fiscal_partition": {
            "periods": [{"key": p.key, "start": p.start.isoformat(), "end_exclusive": p.end_exclusive.isoformat()}
                        for p in inputs.fiscal_periods],
            "completed": list(inputs.completed),
            "newly_completed": list(inputs.newly_completed),
            "remaining": list(inputs.remaining),
        },
        "input_roles": rows,
        "input_vector": {
            "input_vector_sha256": inputs.input_vector_sha256,
            "definition_receipt_sha256": inputs.role_amounts[0].amount.definition_ref.sha256,
            "perimeter_receipt_sha256": inputs.perimeter_receipt.sha256,
            "role_generations": generations,
        },
    }


def serialize_comparison(result: Mapping) -> dict:
    """Assemble the closed result envelope and self-validate it."""
    if not isinstance(result, Mapping):
        _fail("invalid_request_shape", "result must be an object")
    extra = sorted(set(result) - SERIALIZE_KEYS)
    if extra:
        _fail("unknown_key", f"result carries unknown key(s) {extra}")
    absent = sorted(SERIALIZE_KEYS - set(result))
    if absent:
        _fail("invalid_request_shape", f"result is missing key(s) {absent}")

    eligible = result["eligible"]
    if not isinstance(eligible, bool):
        _fail("invalid_request_shape", "eligible must be a boolean")
    reasons = list(result["reasons"])
    explanation = result["explanation"]
    values = result["values"]
    if eligible:
        if reasons:
            _fail("refusal_shape_invalid", "an eligible comparison carries no refusal reasons")
        if not isinstance(values, Mapping):
            _fail("invalid_request_shape", "an eligible comparison must carry the six result values")
        formatted = {}
        for key in RESULT_VALUE_KEYS:
            if key not in values:
                _fail("invalid_request_shape", f"values misses {key}")
            formatted[key] = _format_decimal(values[key], RESULT_DECIMAL_RE, RESULT_CEILING,
                                             "result_out_of_envelope", f"result.{key}")
        if not isinstance(explanation, str) or not explanation:
            _fail("refusal_shape_invalid", "an eligible comparison still carries a nonempty eligibility explanation")
        subject = result["subject"]
        result_section = {
            **formatted,
            "currency": subject["currency"],
            "scale": CONTRACT_SCALE,
            "formula_revision": FORMULA_REVISION,
        }
    else:
        if not reasons or any(reason not in ELIGIBILITY_REASONS for reason in reasons):
            _fail("refusal_shape_invalid", "a refused comparison carries at least one admitted refusal reason")
        if not isinstance(explanation, str) or not explanation:
            _fail("refusal_shape_invalid", "a refused comparison carries a nonempty explanation")
        if values is not None:
            _fail("result_present_when_refused", "a refused comparison retains input references for explanation only, never a hidden best-effort result")
        result_section = None

    correction = result["correction"]
    _require_closed(correction, frozenset({"corrected", "predecessor_id", "reason"}), "correction")
    corrected = correction["corrected"]
    if not isinstance(corrected, bool):
        _fail("invalid_request_shape", "correction.corrected must be a boolean")
    predecessor_id = correction["predecessor_id"]
    correction_reason = correction["reason"]
    if corrected:
        if not isinstance(predecessor_id, str) or not predecessor_id.startswith(COMPARISON_ID_PREFIX):
            _fail("correction_shape_invalid", "a corrected result names its predecessor comparison id")
        if not isinstance(correction_reason, str) or not correction_reason:
            _fail("correction_shape_invalid", "a corrected result carries a correction reason")
    elif predecessor_id is not None or correction_reason is not None:
        _fail("correction_shape_invalid", "an uncorrected result carries a null predecessor and reason")

    role_order = {role: index for index, role in enumerate(ROLE_FAMILIES)}
    canonical_roles = sorted(result["input_roles"],
                             key=lambda row: (role_order.get(row["role"], len(role_order)),
                                              list(row["period_keys"]), row["low"], row["high"]))
    input_vector = dict(result["input_vector"])
    input_vector["role_generations"] = sorted(
        input_vector["role_generations"],
        key=lambda entry: (role_order.get(entry["role"], len(role_order)), entry["generation"]))

    envelope = {
        "schema": SCHEMA_ID,
        "comparison_id": "",
        "kind": KIND,
        "subject": dict(result["subject"]),
        "fiscal_partition": result["fiscal_partition"],
        "input_roles": canonical_roles,
        "input_vector": input_vector,
        "eligibility": {
            "eligible": eligible,
            "reasons": reasons,
            "explanation": explanation,
            "checked": list(CHECKED_DIMENSIONS),
        },
        "result": result_section,
        "limitations": list(result["limitations"]),
        "correction": {"corrected": corrected, "predecessor_id": predecessor_id, "reason": correction_reason},
        "authority": {flag: False for flag in AUTHORITY_FLAGS},
    }
    envelope["comparison_id"] = compute_comparison_id(envelope)
    validate_comparison_result(envelope)
    return envelope


# ---------------------------------------------------------------- result validation

def _scan_forbidden_keys(node, path: str) -> None:
    if isinstance(node, Mapping):
        for key, value in node.items():
            if key in FORBIDDEN_PROMOTION_KEYS:
                _fail("forbidden_promotion_field", f"{path}.{key} is a forbidden promotion or surprise field")
            _scan_forbidden_keys(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _scan_forbidden_keys(item, f"{path}[{index}]")


def validate_comparison_result(payload) -> None:
    if not isinstance(payload, Mapping):
        _fail("invalid_request_shape", "result payload must be an object")
    sections = set(payload)
    if sections - set(RESULT_SECTIONS):
        _fail("unknown_section", f"unknown section(s) {sorted(sections - set(RESULT_SECTIONS))}; the envelope is closed and carries no render timestamp")
    if set(RESULT_SECTIONS) - sections:
        _fail("missing_section", f"missing section(s) {sorted(set(RESULT_SECTIONS) - sections)}")

    authority = payload["authority"]
    if not isinstance(authority, Mapping) or set(authority) != set(AUTHORITY_FLAGS):
        _fail("authority_not_sealed", "authority must carry exactly the six authority flags")
    for flag in AUTHORITY_FLAGS:
        if authority[flag] is not False:
            _fail("authority_not_sealed", f"authority.{flag} must be literally false")

    for section, content in payload.items():
        # The authority section itself carries the six literal-false flags by
        # design; every other section is scanned for promotion fields.
        if section != "authority":
            _scan_forbidden_keys(content, f"$.{section}")

    correction = payload["correction"]
    if isinstance(correction, Mapping) and correction.get("corrected") is True \
            and correction.get("predecessor_id") == payload.get("comparison_id"):
        _fail("correction_shape_invalid",
              "a corrected result cannot name itself as predecessor; a re-issue with identical content is not a correction")

    eligibility = payload["eligibility"]
    if not isinstance(eligibility, Mapping):
        _fail("invalid_request_shape", "eligibility must be an object")
    eligible = eligibility.get("eligible")
    if not isinstance(eligible, bool):
        _fail("invalid_request_shape", "eligibility.eligible must be a boolean")
    result_section = payload["result"]
    if eligible and result_section is None:
        _fail("result_missing_when_eligible", "an eligible comparison carries a result object")
    if not eligible and result_section is not None:
        _fail("result_present_when_refused", "a refused comparison has result null and retains input references for explanation only")
    if result_section is not None:
        for key in RESULT_VALUE_KEYS:
            value = result_section.get(key)
            if not isinstance(value, str) or not RESULT_DECIMAL_RE.fullmatch(value):
                _fail("result_out_of_envelope", f"result.{key}={value!r} is outside the serializable decimal envelope")
        if result_section.get("currency") not in CURRENCIES:
            _fail("unknown_currency", "result.currency is not an admitted currency code")

    expected_id = compute_comparison_id(payload)
    if payload.get("comparison_id") != expected_id:
        _fail("comparison_id_mismatch", f"comparison_id does not match the content identity (expected {expected_id})")

    try:
        _contract_validator().validate(payload)
    except JsonschemaValidationError as error:
        _fail("schema_violation", f"{error.json_path}: {error.message}")
