"""A6 inter-labeler agreement and adjudication layer (news-impact program).

Implements masterplan section 3.5 (labeling protocol: two independent
labeler families per case, a third family resolving disagreements, residual
disagreement ruled by the seat or a human and recorded) and section 11
(coverage accounting: deferred and failed cases are counted, never silently
dropped), under freeze decision PHASE0_FREEZE_2026-10-11.md section 7 (the
labeling protocol and the value/unit/basis/period/negation grading
definition) and Gate 4 acceptance labels (freeze section 3).  The frozen
statistics, routing and minimum-agreement gate are pre-registered in
designs/A6_labeler/agreement_spec.md v1 (2026-10-12) sections 1-4; span
replay follows designs/A6_labeler/span_replay.md v1 (offline byte/offset
check over injected source bytes only — any network fetch is out of scope
and belongs to the Phase 1 document path, freeze section 10).

Standing kills respected: no confidence, probability, score, price_target,
fair_value, sentiment or contagion key is defined or passed through
(DNR:KILL-LLM-CONFIDENCE, W3-R3); such keys are stripped at ingest and
recorded in ``stripped_fields``.  Labelers are external: this module makes
no model calls.  Deterministic by construction: no clock reads, no
randomness, no network, no module-level I/O; iteration over sets/dicts is
sorted and two runs on permuted input order emit byte-identical canonical
JSON.

Reading of the spec (documented where the spec is silent, all INFERRED,
each also listed in the lane return packet):
- Abstentions (label_return ``abstentions``) are provenance metadata: the
  ``fields`` entry is authoritative for presence/absence (the schema forces
  all 12 field entries; guide section 6, "a field labelled as a typed
  absence is NOT an abstention").
- A ``quantity_absent`` value (``form: "absent"``) is the absence channel
  for quantity slots (guide section 6); the field-entry ``typed_absence``
  is the other.  Both reduce to an absence state keyed by ``reason``.
- ``span_only_divergence`` (spec section 1) is value agreement plus a
  different excerpt: it never counts as a value disagreement but routes
  the case to the third family for span confirmation (spec section 1 last
  bullet); because both drafting spans already replayed to enter the
  statistics at all, confirmation succeeds offline and the case resolves
  without adjudication.
- Replay step 5 (span_replay.md section 2.5): an injection-pattern hit
  does not fail replay; it is recorded with the closed reason
  ``injection_pattern_in_excerpt`` (vocabulary of section 3), the field is
  marked ``unevidenced`` in the case result, and the case is flagged.
- ``critical_numeric_correctness`` / ``material_routing_recall`` /
  ``unsupported_transfer_yes`` (spec section 2) are Gate 4 / section 11
  endpoints measured over adjudicator-assigned marks; this layer prints
  them as ``null`` (spec: "printed even when zero or null") because
  ``routing_label`` is adjudicator-only (freeze section 5) and is never
  taken from labeler output.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator

LABEL_RETURN_SCHEMA_NAME = "label_return.v1.schema.json"
ADJUDICATION_SCHEMA_NAME = "adjudication_record.v1.schema.json"
CONTRACT_NAME = "news_impact_event.v1.schema.json"

# Closed error-code vocabulary (W3-R5).  Every code has a test asserting the
# exact string.
LABEL_RETURN_INVALID = "LABEL_RETURN_INVALID"
FIELD_ENTRY_MALFORMED = "FIELD_ENTRY_MALFORMED"
CASE_PAIR_MISMATCH = "CASE_PAIR_MISMATCH"
DUPLICATE_LABELER_FAMILY = "DUPLICATE_LABELER_FAMILY"
THIRD_FAMILY_NOT_DISTINCT = "THIRD_FAMILY_NOT_DISTINCT"
SOURCE_BYTES_MISSING = "SOURCE_BYTES_MISSING"
RULING_INVALID = "RULING_INVALID"
ADJUDICATION_RECORD_INVALID = "ADJUDICATION_RECORD_INVALID"

CODES = frozenset(
    {
        LABEL_RETURN_INVALID,
        FIELD_ENTRY_MALFORMED,
        CASE_PAIR_MISMATCH,
        DUPLICATE_LABELER_FAMILY,
        THIRD_FAMILY_NOT_DISTINCT,
        SOURCE_BYTES_MISSING,
        RULING_INVALID,
        ADJUDICATION_RECORD_INVALID,
    }
)

# W3-R3: forbidden keys stripped at ingest, recorded per return.
FORBIDDEN_KEYS = frozenset(
    {
        "confidence",
        "probability",
        "score",
        "price_target",
        "fair_value",
        "sentiment",
        "contagion",
    }
)

# Closed replay-reason vocabulary (span_replay.md section 3).
REPLAY_SOURCE_SHA_MISMATCH = "source_sha_mismatch"
REPLAY_BYTE_RANGE_INVALID = "byte_range_invalid"
REPLAY_EXCERPT_MISMATCH = "excerpt_mismatch"
REPLAY_SEGMENT_VIOLATION = "segment_violation"
REPLAY_INJECTION_PATTERN = "injection_pattern_in_excerpt"
REPLAY_REASONS = frozenset(
    {
        REPLAY_SOURCE_SHA_MISMATCH,
        REPLAY_BYTE_RANGE_INVALID,
        REPLAY_EXCERPT_MISMATCH,
        REPLAY_SEGMENT_VIOLATION,
        REPLAY_INJECTION_PATTERN,
    }
)

T1 = "capital_allocation_event.v1"
T2 = "demand_guidance_contract_event.v1"
T3 = "strategic_product_partnership_event.v1"
TEMPLATES = (T1, T2, T3)

# The 12 critical fields per template (agreement_spec.md section 1; the
# label_return.v1 field discriminators).
TEMPLATE_FIELDS: dict[str, tuple[str, ...]] = {
    T1: (
        "company_id", "issuer_role", "novelty", "action_type",
        "commitment_status", "primary_amount_role", "incremental_amount",
        "remaining_authorization", "executed_amount", "horizon_period",
        "negated", "action_span",
    ),
    T2: (
        "company_id", "issuer_role", "demand_stage", "metric",
        "commitment_status", "stated_amount", "fiscal_period",
        "revision_direction", "negated", "novelty",
        "counterparty_company_id", "baseline",
    ),
    T3: (
        "company_id", "issuer_role", "event_kind", "object_name",
        "commitment_status", "novelty", "counterparty_company_id",
        "counterparty_role", "stated_quantity", "economic_claim_class",
        "negated", "action_span",
    ),
}

# Field comparison kinds (agreement_spec.md section 1 normalisation rules).
KIND_ENUM = "enum"
KIND_BOOLEAN = "boolean"
KIND_COMPANY_ID = "company_id"
KIND_QUANTITY = "quantity"
KIND_PERIOD = "period"
KIND_EVIDENCE = "evidence"
KIND_TEXT = "text"
KIND_BASELINE = "baseline"

FIELD_KINDS: dict[str, dict[str, str]] = {
    T1: {
        "company_id": KIND_COMPANY_ID,
        "issuer_role": KIND_ENUM,
        "novelty": KIND_ENUM,
        "action_type": KIND_ENUM,
        "commitment_status": KIND_ENUM,
        "primary_amount_role": KIND_ENUM,
        "incremental_amount": KIND_QUANTITY,
        "remaining_authorization": KIND_QUANTITY,
        "executed_amount": KIND_QUANTITY,
        "horizon_period": KIND_PERIOD,
        "negated": KIND_BOOLEAN,
        "action_span": KIND_EVIDENCE,
    },
    T2: {
        "company_id": KIND_COMPANY_ID,
        "issuer_role": KIND_ENUM,
        "demand_stage": KIND_ENUM,
        "metric": KIND_ENUM,
        "commitment_status": KIND_ENUM,
        "stated_amount": KIND_QUANTITY,
        "fiscal_period": KIND_PERIOD,
        "revision_direction": KIND_ENUM,
        "negated": KIND_BOOLEAN,
        "novelty": KIND_ENUM,
        "counterparty_company_id": KIND_COMPANY_ID,
        "baseline": KIND_BASELINE,
    },
    T3: {
        "company_id": KIND_COMPANY_ID,
        "issuer_role": KIND_ENUM,
        "event_kind": KIND_ENUM,
        "object_name": KIND_TEXT,
        "commitment_status": KIND_ENUM,
        "novelty": KIND_ENUM,
        "counterparty_company_id": KIND_COMPANY_ID,
        "counterparty_role": KIND_ENUM,
        "stated_quantity": KIND_QUANTITY,
        "economic_claim_class": KIND_ENUM,
        "negated": KIND_BOOLEAN,
        "action_span": KIND_EVIDENCE,
    },
}

# agreement_spec.md line ~56: the enum (kappa-eligible) critical fields.
KAPPA_ELIGIBLE_FIELDS: dict[str, frozenset[str]] = {
    T1: frozenset({"issuer_role", "novelty", "action_type", "commitment_status", "primary_amount_role"}),
    T2: frozenset({"issuer_role", "demand_stage", "metric", "commitment_status", "revision_direction", "novelty"}),
    T3: frozenset({"issuer_role", "event_kind", "novelty", "counterparty_role", "economic_claim_class"}),
}

# The $defs/quantity slots, for the section 4 absence-split floor.
QUANTITY_FIELDS: dict[str, frozenset[str]] = {
    T1: frozenset({"incremental_amount", "remaining_authorization", "executed_amount"}),
    T2: frozenset({"stated_amount"}),
    T3: frozenset({"stated_quantity"}),
}

ABSENCE_SCHEMA_CONSTS = frozenset({"field_absence.v1", "owner_typed_absence.v1"})

# Field-comparison outcomes (closed).
OUT_AGREE = "agree"
OUT_DISAGREE = "disagree"
OUT_ABSENT_VS_PRESENT = "absent_vs_present"

# Case statuses (closed).
ST_EXCLUDED_INVALID = "excluded_invalid_return"
ST_EXCLUDED_REPLAY = "excluded_replay_failure"
ST_ACCEPTED_FIRST_PASS = "accepted_first_pass"
ST_ROUTED_PENDING_THIRD = "routed_pending_third"
ST_RESOLVED_BY_THIRD = "resolved_by_third"
ST_ADJUDICATION_NEEDED = "adjudication_needed"

RULINGS = ("first", "second", "third", "none_of_the_above", "unresolvable_defer")

# Pre-registered section 4 thresholds.
EXACT_AGREEMENT_FLOOR = 0.90
KAPPA_FLOOR = 0.80
KAPPA_MIN_N_BOTH_PRESENT = 20
ABSENT_SPLIT_FRACTION_MAX = 0.10
EXACT_AGREEMENT_PAUSE = 0.75


class AgreementError(Exception):
    """Module error carrying a closed code from :data:`CODES`."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def canonical_json(obj: Any) -> str:
    """Canonical JSON encoding (W3-R2): sorted keys, tight separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _default_schema_path(name: str) -> Path:
    return Path(__file__).resolve().parents[2] / "contracts" / "news_impact" / name


def load_json_schema(name: str, path: str | Path | None = None) -> dict:
    """Lazily read one contracts_w3 schema (no module-level I/O)."""
    with open(path if path is not None else _default_schema_path(name), "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Ingest: strip forbidden keys, validate against label_return.v1
# ---------------------------------------------------------------------------


def strip_forbidden_keys(node: Any, trail: str = "") -> tuple[Any, tuple[str, ...]]:
    """Recursively remove forbidden keys; return (clean node, dotted paths)."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        stripped: list[str] = []
        for key in sorted(node):
            value = node[key]
            path = f"{trail}.{key}" if trail else key
            if key in FORBIDDEN_KEYS:
                stripped.append(path)
                continue
            clean, sub = strip_forbidden_keys(value, path)
            out[key] = clean
            stripped.extend(sub)
        return out, tuple(stripped)
    if isinstance(node, list):
        items: list[Any] = []
        stripped = []
        for index, value in enumerate(node):
            clean, sub = strip_forbidden_keys(value, f"{trail}[{index}]")
            items.append(clean)
            stripped.extend(sub)
        return items, tuple(stripped)
    return node, ()


@dataclass(frozen=True)
class ParsedReturn:
    """One validated, stripped labeler return (label_return.v1)."""

    record: dict
    case_id: str
    template: str
    labeler_family: str
    model_vintage: str
    prompt_version: str
    stripped_fields: tuple[str, ...] = ()

    def field_entry(self, name: str) -> dict:
        return self.record["fields"][name]

    def abstained_fields(self) -> tuple[str, ...]:
        return tuple(sorted(a["field"] for a in self.record.get("abstentions", [])))


def parse_label_return(record: Mapping[str, Any], schema_path: str | Path | None = None) -> ParsedReturn:
    """Strip forbidden keys, then validate against label_return.v1.

    Raises :class:`AgreementError` with code ``LABEL_RETURN_INVALID`` when the
    (stripped) record fails the schema, ``FIELD_ENTRY_MALFORMED`` when a field
    entry is structurally unusable (value null with no typed absence, or a
    fields object that is not exactly the template's 12 critical fields).
    """
    cleaned, stripped = strip_forbidden_keys(dict(record))
    schema = load_json_schema(LABEL_RETURN_SCHEMA_NAME, schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(cleaned), key=lambda e: "/".join(map(str, e.absolute_path)))
    if errors:
        raise AgreementError(
            LABEL_RETURN_INVALID,
            f"case {cleaned.get('case_id')!r}: {errors[0].json_path}: {errors[0].message}",
        )
    template = cleaned["template"]
    if template not in TEMPLATE_FIELDS:
        raise AgreementError(LABEL_RETURN_INVALID, f"unknown template {template!r}")
    fields = cleaned["fields"]
    expected = set(TEMPLATE_FIELDS[template])
    if set(fields) != expected:
        raise AgreementError(
            FIELD_ENTRY_MALFORMED,
            f"case {cleaned['case_id']!r}: fields object is not exactly the 12 critical fields "
            f"(missing={sorted(expected - set(fields))}, extra={sorted(set(fields) - expected)})",
        )
    for name in sorted(fields):
        entry = fields[name]
        if entry.get("typed_absence") is None and entry.get("value") is None:
            raise AgreementError(
                FIELD_ENTRY_MALFORMED,
                f"case {cleaned['case_id']!r} field {name}: value null without a typed_absence",
            )
    return ParsedReturn(
        record=cleaned,
        case_id=cleaned["case_id"],
        template=template,
        labeler_family=cleaned["labeler_family"],
        model_vintage=cleaned["model_vintage"],
        prompt_version=cleaned["prompt_version"],
        stripped_fields=stripped,
    )


# ---------------------------------------------------------------------------
# Span replay (span_replay.md, offline over injected bytes)
# ---------------------------------------------------------------------------

_text_safe_patterns: list[re.Pattern[str]] | None = None


def _injection_patterns(contract_path: str | Path | None = None) -> list[re.Pattern[str]]:
    """Compile the frozen $defs/text_safe not-patterns (lazy, cached)."""
    global _text_safe_patterns
    if _text_safe_patterns is None:
        contract = load_json_schema(CONTRACT_NAME, contract_path)
        node = contract["$defs"]["text_safe"]
        pats = [branch["pattern"] for branch in node.get("not", {}).get("anyOf", []) if "pattern" in branch]
        _text_safe_patterns = [re.compile(p) for p in pats]
    return _text_safe_patterns


@dataclass(frozen=True)
class ReplayFailure:
    """One span replay failure or injection flag (closed reason vocabulary)."""

    field: str
    reason: str
    detail: str

    def to_dict(self) -> dict:
        return {"field": self.field, "reason": self.reason, "detail": self.detail}


def replay_return_spans(
    parsed: ParsedReturn,
    source_bytes: bytes,
    source_sha256: str,
    segments: Sequence[Mapping[str, int]] | None = None,
    contract_path: str | Path | None = None,
) -> dict:
    """Replay every field-level span of one return (span_replay.md section 2).

    Steps 1-4 produce hard failures (counted in ``n_failed``); step 5 records
    ``injection_pattern_in_excerpt`` without failing the replay
    (span_replay.md section 2.5).  Returns the section 4 report row plus
    ``injection_flagged``.
    """
    failures: list[ReplayFailure] = []
    n_checked = 0
    injection_flagged = False
    digest = sha256(source_bytes).hexdigest()
    for name in sorted(parsed.record["fields"]):
        span = parsed.record["fields"][name].get("source_span")
        if span is None:
            continue
        n_checked += 1
        if digest != source_sha256 or span.get("text_sha256") != source_sha256:
            failures.append(ReplayFailure(name, REPLAY_SOURCE_SHA_MISMATCH, "case or span sha does not tie"))
            continue
        start, end = span.get("byte_start", -1), span.get("byte_end", -1)
        seg_index = span.get("segment_index", -1)
        if not (start >= 0 and end >= 1 and end > start and end <= len(source_bytes) and seg_index >= 0):
            failures.append(ReplayFailure(name, REPLAY_BYTE_RANGE_INVALID, f"byte range [{start},{end}) invalid"))
            continue
        try:
            slice_text = source_bytes[start:end].decode("utf-8")
        except UnicodeDecodeError:
            slice_text = None
        if slice_text != span.get("excerpt"):
            failures.append(ReplayFailure(name, REPLAY_EXCERPT_MISMATCH, "slice does not reproduce excerpt byte-for-byte"))
            continue
        if segments is not None:
            seg = next((s for s in segments if s.get("segment_index") == seg_index), None)
            if seg is None or start < seg["byte_start"] or end > seg["byte_end"]:
                failures.append(ReplayFailure(name, REPLAY_SEGMENT_VIOLATION, f"span crosses segment {seg_index} boundary"))
                continue
        if any(p.search(span.get("excerpt", "")) for p in _injection_patterns(contract_path)):
            # span_replay.md section 2.5: the bytes reproduce, so this is NOT
            # a replay failure; the field is marked unevidenced and the case
            # recorded as an injection finding.
            failures.append(ReplayFailure(name, REPLAY_INJECTION_PATTERN, "excerpt carries an injection not-pattern; field marked unevidenced"))
            injection_flagged = True
    hard = [f for f in failures if f.reason != REPLAY_INJECTION_PATTERN]
    return {
        "case_id": parsed.case_id,
        "template": parsed.template,
        "labeler_family": parsed.labeler_family,
        "n_spans_checked": n_checked,
        "n_replayed": n_checked - len(hard),
        "n_failed": len(hard),
        "failures": [f.to_dict() for f in failures],
        "injection_flagged": injection_flagged,
    }


# ---------------------------------------------------------------------------
# Normalisation (agreement_spec.md section 1) and field comparison
# ---------------------------------------------------------------------------


def _fold_number(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _is_absence(value: Any) -> bool:
    return isinstance(value, dict) and value.get("schema") in ABSENCE_SCHEMA_CONSTS


def _absence_reason(value: Mapping[str, Any]) -> str:
    reason = value.get("reason")
    if reason is None and "owner_reason" in value:
        reason = value["owner_reason"]
    return f"absent:{reason}"


def _normalise_period(value: Mapping[str, Any]) -> dict:
    # Component-wise over the full fiscal_period key set (calendar_end
    # differences count even when year+kind match — spec section 1).
    return {
        "year": value.get("year"),
        "quarter": value.get("quarter"),
        "calendar_end": value.get("calendar_end"),
        "period_kind": value.get("period_kind"),
        "end_year": value.get("end_year"),
    }


def _normalise_quantity(value: Mapping[str, Any]) -> dict:
    form = value.get("form")
    if form == "point":
        return {
            "form": "point",
            "value": _fold_number(value.get("value")),
            "bound": value.get("bound"),  # a hedge difference is a disagreement
            "unit": str(value.get("unit", "")).strip().lower(),
            "currency": value.get("currency"),  # compared exactly (ISO upper)
            "period": _normalise_period_or_absence(value.get("period")),
            "negated": value.get("negated"),
        }
    if form == "range":
        return {
            "form": "range",
            "low": _fold_number(value.get("low")),
            "high": _fold_number(value.get("high")),
            "unit": str(value.get("unit", "")).strip().lower(),
            "currency": value.get("currency"),
            "period": _normalise_period_or_absence(value.get("period")),
            "negated": value.get("negated"),
        }
    # basis never compares (spec section 1: slot-fixed by schema const); any
    # other form is kept verbatim so the pair still compares deterministically.
    return {"form": form}


def _normalise_period_or_absence(value: Any) -> Any:
    if value is None:
        return None
    if _is_absence(value):
        return _absence_reason(value)
    if isinstance(value, dict) and "period_kind" in value:
        return _normalise_period(value)
    return value


def _normalise_deep(value: Any) -> Any:
    if isinstance(value, dict):
        if _is_absence(value):
            return _absence_reason(value)
        if "period_kind" in value:
            return _normalise_period(value)
        if "form" in value and ("value" in value or "low" in value):
            return _normalise_quantity(value)
        return {k: _normalise_deep(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [_normalise_deep(v) for v in value]
    return value


def normalise_value(template: str, field_name: str, value: Any) -> Any:
    """Normalise one critical-field value per agreement_spec.md section 1."""
    kind = FIELD_KINDS[template][field_name]
    if _is_absence(value):
        return _absence_reason(value)
    if kind == KIND_ENUM or kind == KIND_BOOLEAN or kind == KIND_TEXT:
        return value
    if kind == KIND_COMPANY_ID:
        if isinstance(value, list):
            return {"ids": sorted(value)}
        return {"ids": [value]}
    if kind == KIND_QUANTITY:
        if isinstance(value, dict) and value.get("form") == "absent":
            return _absence_reason(value["absence"])
        return _normalise_quantity(value)
    if kind == KIND_PERIOD:
        return _normalise_period_or_absence(value)
    if kind == KIND_EVIDENCE:
        if isinstance(value, dict) and "evidence_absence" in value:
            return {"kind": "absence", "reason": _absence_reason(value["evidence_absence"].get("absence", value["evidence_absence"]))}
        # evidence_span: the value agrees on form; the quote is span-choice,
        # compared as an excerpt (span_only_divergence), never as a value.
        return {"kind": "span"}
    if kind == KIND_BASELINE:
        return _normalise_deep(value)
    raise AgreementError(FIELD_ENTRY_MALFORMED, f"unknown field kind {kind!r} for {field_name}")


@dataclass(frozen=True)
class FieldState:
    """Presence state of one field entry after section 1 normalisation."""

    present: bool
    token: Any  # normalised value, or "absent:<reason>"

    def to_dict(self) -> dict:
        return {"present": self.present, "token": self.token}


def field_state(template: str, field_name: str, entry: Mapping[str, Any]) -> FieldState:
    """Reduce one label_return field entry to a presence state."""
    if entry.get("typed_absence") is not None:
        return FieldState(False, _absence_reason(entry["typed_absence"]))
    value = entry.get("value")
    if isinstance(value, dict) and value.get("form") == "absent" and "absence" in value:
        return FieldState(False, _absence_reason(value["absence"]))
    return FieldState(True, normalise_value(template, field_name, value))


@dataclass(frozen=True)
class FieldComparison:
    """Outcome of comparing one field across two returns (closed outcomes)."""

    outcome: str  # OUT_AGREE | OUT_DISAGREE | OUT_ABSENT_VS_PRESENT
    both_present: bool
    both_absent: bool
    span_only_divergence: bool
    excerpt_a: str | None = None
    excerpt_b: str | None = None

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "both_present": self.both_present,
            "both_absent": self.both_absent,
            "span_only_divergence": self.span_only_divergence,
        }


def compare_field(template: str, field_name: str, entry_a: Mapping[str, Any], entry_b: Mapping[str, Any]) -> FieldComparison:
    """Compare one critical field between two returns (agreement_spec section 1)."""
    state_a = field_state(template, field_name, entry_a)
    state_b = field_state(template, field_name, entry_b)
    excerpt_a = (entry_a.get("source_span") or {}).get("excerpt")
    excerpt_b = (entry_b.get("source_span") or {}).get("excerpt")
    if state_a.present != state_b.present:
        return FieldComparison(OUT_ABSENT_VS_PRESENT, state_a.present and state_b.present, False, False, excerpt_a, excerpt_b)
    agree = canonical_json(state_a.token) == canonical_json(state_b.token)
    span_only = bool(
        agree
        and state_a.present
        and excerpt_a is not None
        and excerpt_b is not None
        and excerpt_a != excerpt_b
    )
    return FieldComparison(
        OUT_AGREE if agree else OUT_DISAGREE,
        state_a.present and state_b.present,
        not state_a.present and not state_b.present,
        span_only,
        excerpt_a,
        excerpt_b,
    )


# ---------------------------------------------------------------------------
# Cohen's kappa (agreement_spec.md section 2, line ~53)
# ---------------------------------------------------------------------------


def cohen_kappa(pairs: Sequence[tuple[str, str]], enum_universe: Sequence[str]) -> tuple[float | None, str, int]:
    """Cohen's kappa over both-present pairs; null per spec line ~53.

    Returns ``(kappa, kappa_note, n)``.  ``kappa`` is ``None`` when fewer than
    2 categories are observed or ``n = 0`` — printed as null, never omitted.
    ``kappa_note`` names the closed-enum categories unobserved in the
    both-present confusion matrix ("" when none).  Categories outside the
    closed enum are carried in the matrix but never enter the note.
    """
    n = len(pairs)
    if n == 0:
        return None, ",".join(sorted(enum_universe)), 0
    observed = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    if len(observed) < 2:
        unobserved = sorted(c for c in enum_universe if c not in observed)
        return None, ",".join(unobserved), n
    categories = sorted(set(observed) | set(enum_universe))
    row = {c: 0 for c in categories}
    col = {c: 0 for c in categories}
    diag = {c: 0 for c in categories}
    for a, b in pairs:
        row[a] += 1
        col[b] += 1
        if a == b:
            diag[a] += 1
    p_o = sum(diag.values()) / n
    p_e = sum((row[c] / n) * (col[c] / n) for c in categories)
    if p_e >= 1.0:
        # Unreachable when categories are the union of observed values
        # (Cauchy-Schwarz); kept as a defensive null, printed never omitted.
        unobserved = sorted(c for c in enum_universe if c not in observed)
        return None, ",".join(unobserved), n
    kappa = (p_o - p_e) / (1.0 - p_e)
    unobserved = sorted(c for c in enum_universe if c not in observed)
    return round(kappa, 6), ",".join(unobserved), n


def field_enum_universe(template: str, field_name: str, contract_path: str | Path | None = None) -> tuple[str, ...]:
    """Closed enum universe of a kappa-eligible field, from the frozen contract."""
    contract = load_json_schema(CONTRACT_NAME, contract_path)
    defs = contract["$defs"]
    if field_name in ("issuer_role", "novelty", "commitment_status"):
        return tuple(defs[field_name]["enum"])
    props = defs[template]["properties"]
    return tuple(props[field_name]["enum"])


# ---------------------------------------------------------------------------
# Routing: acceptance, third family, adjudication (agreement_spec section 3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldRouting:
    """Per-field routing decision for one case."""

    field: str
    comparison: FieldComparison
    status: str  # "agreed" | "disputed" | "span_only_divergence"
    resolved_by: str | None = None  # "first" | "second" when the third family formed a majority

    def to_dict(self) -> dict:
        out = {"field": self.field, "status": self.status}
        out.update(self.comparison.to_dict())
        if self.resolved_by is not None:
            out["resolved_by"] = self.resolved_by
        return out


@dataclass(frozen=True)
class CaseRouting:
    """Full routing outcome for one case (spec section 3)."""

    case_id: str
    template: str
    status: str
    fields: tuple[FieldRouting, ...]
    replay_a: dict
    replay_b: dict
    replay_c: dict | None = None
    stripped_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "template": self.template,
            "status": self.status,
            "fields": [f.to_dict() for f in self.fields],
            "replay_failed": self.replay_a.get("n_failed", 0) > 0 or self.replay_b.get("n_failed", 0) > 0
            or (self.replay_c is not None and self.replay_c.get("n_failed", 0) > 0),
            "injection_flagged": bool(
                self.replay_a.get("injection_flagged") or self.replay_b.get("injection_flagged")
                or (self.replay_c is not None and self.replay_c.get("injection_flagged"))
            ),
            "adjudication_needed_fields": [f.field for f in self.fields if f.status == "disputed" and f.resolved_by is None],
            "disputed_fields": [f.field for f in self.fields if f.status != "agreed"],
            "stripped_fields": list(self.stripped_fields),
        }


def route_case(
    first: ParsedReturn,
    second: ParsedReturn,
    source_bytes: bytes,
    source_sha256: str,
    third: ParsedReturn | None = None,
    segments: Sequence[Mapping[str, int]] | None = None,
    contract_path: str | Path | None = None,
) -> CaseRouting:
    """Route one case: acceptance, third-family majority, adjudication need.

    Raises :class:`AgreementError` (``CASE_PAIR_MISMATCH``,
    ``DUPLICATE_LABELER_FAMILY``, ``THIRD_FAMILY_NOT_DISTINCT``) on pairing
    violations; replay failures do not raise — they yield status
    ``excluded_replay_failure`` (a replay failure is a span defect, not a
    disagreement; agreement_spec section 1).
    """
    if first.case_id != second.case_id or first.template != second.template:
        raise AgreementError(CASE_PAIR_MISMATCH, f"{first.case_id}/{first.template} vs {second.case_id}/{second.template}")
    if first.labeler_family == second.labeler_family:
        raise AgreementError(DUPLICATE_LABELER_FAMILY, f"case {first.case_id}: {first.labeler_family}")
    if third is not None:
        if third.case_id != first.case_id or third.template != first.template:
            raise AgreementError(CASE_PAIR_MISMATCH, f"third return {third.case_id}/{third.template} is not this case")
        if third.labeler_family in (first.labeler_family, second.labeler_family):
            raise AgreementError(
                THIRD_FAMILY_NOT_DISTINCT,
                f"case {first.case_id}: {third.labeler_family} in ({first.labeler_family}, {second.labeler_family})",
            )
    replay_a = replay_return_spans(first, source_bytes, source_sha256, segments, contract_path)
    replay_b = replay_return_spans(second, source_bytes, source_sha256, segments, contract_path)
    replay_c = (
        replay_return_spans(third, source_bytes, source_sha256, segments, contract_path)
        if third is not None
        else None
    )
    if replay_a["n_failed"] or replay_b["n_failed"] or (replay_c is not None and replay_c["n_failed"]):
        return CaseRouting(first.case_id, first.template, ST_EXCLUDED_REPLAY, (), replay_a, replay_b, replay_c,
                           tuple(sorted(set(first.stripped_fields) | set(second.stripped_fields))))

    routings: list[FieldRouting] = []
    for name in TEMPLATE_FIELDS[first.template]:
        entry_a = first.field_entry(name)
        entry_b = second.field_entry(name)
        entry_c = third.field_entry(name) if third is not None else None
        comparison = compare_field(first.template, name, entry_a, entry_b)
        if comparison.outcome == OUT_AGREE and not comparison.span_only_divergence:
            routings.append(FieldRouting(name, comparison, "agreed"))
            continue
        status = "span_only_divergence" if comparison.outcome == OUT_AGREE else "disputed"
        resolved_by: str | None = None
        if entry_c is not None:
            if status == "span_only_divergence":
                # Span confirmation (spec section 1 last bullet): both
                # drafting spans replayed to reach this layer, so the
                # divergence is confirmed-reproducible and the value stands.
                resolved_by = "span_confirmed"
            else:
                token_c = field_state(first.template, name, entry_c).token
                token_a = field_state(first.template, name, entry_a).token
                token_b = field_state(first.template, name, entry_b).token
                if canonical_json(token_c) == canonical_json(token_a):
                    resolved_by = "first"
                elif canonical_json(token_c) == canonical_json(token_b):
                    resolved_by = "second"
        routings.append(FieldRouting(name, comparison, status, resolved_by))

    any_dispute = any(r.status != "agreed" for r in routings)
    if not any_dispute:
        status = ST_ACCEPTED_FIRST_PASS
    elif third is None:
        status = ST_ROUTED_PENDING_THIRD
    elif all(r.resolved_by is not None for r in routings if r.status != "agreed"):
        status = ST_RESOLVED_BY_THIRD
    else:
        status = ST_ADJUDICATION_NEEDED
    return CaseRouting(
        first.case_id,
        first.template,
        status,
        tuple(routings),
        replay_a,
        replay_b,
        replay_c,
        tuple(sorted(set(first.stripped_fields) | set(second.stripped_fields))),
    )


def build_adjudication_record(
    case_id: str,
    template: str,
    field_name: str,
    values: Sequence[Mapping[str, Any]],
    ruling: str,
    reason: str,
    adjudicator: str,
    resolved_value: Mapping[str, Any] | None = None,
    schema_path: str | Path | None = None,
) -> dict:
    """Build and schema-validate one adjudication_record.v1 (spec section 3).

    ``values`` are the three labelers' entries in draft order, each
    ``{labeler_family, value, source_span, typed_absence}`` kept verbatim.
    For ruling ``first``/``second``/``third`` the resolved value repeats that
    labeler's entry verbatim; ``none_of_the_above`` requires an explicit
    ``resolved_value``; ``unresolvable_defer`` resolves to nulls and defers
    the case (counted, never dropped).
    """
    if ruling not in RULINGS:
        raise AgreementError(RULING_INVALID, f"ruling {ruling!r} not in {RULINGS}")
    if len(values) != 3:
        raise AgreementError(ADJUDICATION_RECORD_INVALID, f"values must carry 3 labeler entries, got {len(values)}")
    if ruling in ("first", "second", "third"):
        idx = RULINGS.index(ruling)
        chosen = values[idx]
        resolved = {"value": chosen.get("value"), "source_span": chosen.get("source_span"), "typed_absence": chosen.get("typed_absence")}
    elif ruling == "none_of_the_above":
        if resolved_value is None:
            raise AgreementError(ADJUDICATION_RECORD_INVALID, "none_of_the_above requires an explicit resolved_value")
        resolved = dict(resolved_value)
    else:  # unresolvable_defer
        resolved = {"value": None, "source_span": None, "typed_absence": None}
    record = {
        "schema": "adjudication_record.v1",
        "case_id": case_id,
        "template": template,
        "field": field_name,
        "values": [dict(v) for v in values],
        "ruling": ruling,
        "resolved_value": resolved,
        "reason": reason,
        "adjudicator": adjudicator,
    }
    schema = load_json_schema(ADJUDICATION_SCHEMA_NAME, schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(record), key=lambda e: list(e.absolute_path))
    if errors:
        raise AgreementError(ADJUDICATION_RECORD_INVALID, f"case {case_id} field {field_name}: {errors[0].message}")
    return record


# ---------------------------------------------------------------------------
# Agreement statistics and the section 4 gate
# ---------------------------------------------------------------------------


def _empty_field_row() -> dict:
    return {
        "n_compared": 0,
        "n_both_present": 0,
        "n_both_absent": 0,
        "n_absent_vs_present": 0,
        "exact_agreement": None,
        "kappa": None,
        "kappa_note": "",
        "absent_vs_present_rate": None,
        "example_disagreement_case_ids": [],
        "example_absent_split_case_ids": [],
        "example_span_only_case_ids": [],
    }


def compute_agreement(
    first_returns: Iterable[Mapping[str, Any]],
    second_returns: Iterable[Mapping[str, Any]],
    source_texts: Mapping[str, tuple[bytes, str]],
    third_returns: Iterable[Mapping[str, Any]] | None = None,
    segments: Mapping[str, Sequence[Mapping[str, int]]] | None = None,
    label_return_schema_path: str | Path | None = None,
    contract_path: str | Path | None = None,
) -> dict:
    """Compute the full agreement summary (spec sections 1-3).

    ``source_texts`` maps case_id to ``(source_bytes, source_sha256)`` and is
    the only source of case bytes (W3-R4: injected, never fetched).  Returns
    the summary as plain JSON-compatible dicts: per template the 12 field rows
    (all seven statistics, each with its n) and the template-level counters,
    plus per-case routing results.  Deterministic: cases processed in sorted
    case_id order, sets and dicts iterated sorted.
    """
    parsed_first: dict[str, ParsedReturn] = {}
    parsed_second: dict[str, ParsedReturn] = {}
    parsed_third: dict[str, ParsedReturn] = {}
    invalid: list[dict] = []
    for bucket, iterable in (("first", first_returns), ("second", second_returns), ("third", third_returns or [])):
        for raw in iterable:
            try:
                parsed = parse_label_return(raw, label_return_schema_path)
            except AgreementError as exc:
                invalid.append({"bucket": bucket, "code": exc.code, "message": exc.message})
                continue
            target = {0: parsed_first, 1: parsed_second, 2: parsed_third}[("first", "second", "third").index(bucket)]
            if parsed.case_id in target:
                invalid.append({"bucket": bucket, "code": LABEL_RETURN_INVALID, "message": f"duplicate case {parsed.case_id} in {bucket} returns"})
                continue
            target[parsed.case_id] = parsed

    case_ids = sorted(set(parsed_first) & set(parsed_second))
    cases: dict[str, dict] = {}
    field_rows: dict[str, dict[str, dict]] = {t: {f: _empty_field_row() for f in TEMPLATE_FIELDS[t]} for t in TEMPLATES}
    template_rows = {
        t: {
            "n_cases": 0,
            "n_accepted_first_pass": 0,
            "n_routed_third_family": 0,
            "n_resolved_by_third": 0,
            "n_adjudicated": 0,
            "n_replays_failed": 0,
            "n_span_only_divergence": 0,
            "n_injection_flagged": 0,
            "critical_numeric_correctness": None,
            "material_routing_recall": None,
            "unsupported_transfer_yes": None,
        }
        for t in TEMPLATES
    }
    kappa_pairs: dict[str, dict[str, list[tuple[str, str]]]] = {t: {f: [] for f in KAPPA_ELIGIBLE_FIELDS[t]} for t in TEMPLATES}
    n_returns_failed_replay = 0
    unpaired = sorted((set(parsed_first) ^ set(parsed_second)) | set(parsed_third) - set(parsed_first))

    for case_id in case_ids:
        first, second = parsed_first[case_id], parsed_second[case_id]
        template = first.template
        source = source_texts.get(case_id)
        if source is None:
            raise AgreementError(SOURCE_BYTES_MISSING, f"case {case_id}: no injected source bytes")
        source_bytes, source_sha256 = source
        third = parsed_third.get(case_id)
        try:
            routing = route_case(first, second, source_bytes, source_sha256, third, (segments or {}).get(case_id), contract_path)
        except AgreementError as exc:
            invalid.append({"bucket": "pair", "code": exc.code, "message": exc.message})
            continue
        trow = template_rows[template]
        trow["n_cases"] += 1
        case_dict = routing.to_dict()
        case_dict["abstentions"] = {
            "first": list(first.abstained_fields()),
            "second": list(second.abstained_fields()),
            **({"third": list(third.abstained_fields())} if third is not None else {}),
        }
        cases[case_id] = case_dict

        if routing.status == ST_EXCLUDED_REPLAY:
            # A return whose spans fail replay is excluded whole (spec section 1).
            n_returns_failed_replay += sum(
                r["n_failed"] > 0 for r in (routing.replay_a, routing.replay_b, routing.replay_c) if r is not None
            )
            trow["n_replays_failed"] += 1
            continue
        if routing.replay_a.get("injection_flagged") or routing.replay_b.get("injection_flagged"):
            trow["n_injection_flagged"] += 1

        # First-pass two-family statistics (the gate population, section 4).
        for name in TEMPLATE_FIELDS[template]:
            row = field_rows[template][name]
            fr = next(f for f in routing.fields if f.field == name)
            comp = fr.comparison
            row["n_compared"] += 1
            if comp.both_present:
                row["n_both_present"] += 1
            elif comp.both_absent:
                row["n_both_absent"] += 1
            else:
                row["n_absent_vs_present"] += 1
                row["example_absent_split_case_ids"].append(case_id)
            if comp.outcome == OUT_AGREE:
                if comp.span_only_divergence:
                    row["example_span_only_case_ids"].append(case_id)
                    trow["n_span_only_divergence"] += 1
            else:
                row["example_disagreement_case_ids"].append(case_id)
            if comp.both_present and name in KAPPA_ELIGIBLE_FIELDS[template]:
                token_a = field_state(template, name, first.field_entry(name)).token
                token_b = field_state(template, name, second.field_entry(name)).token
                kappa_pairs[template][name].append((str(token_a), str(token_b)))

        if routing.status == ST_ACCEPTED_FIRST_PASS:
            trow["n_accepted_first_pass"] += 1
        elif routing.status != ST_EXCLUDED_REPLAY:
            trow["n_routed_third_family"] += 1
            if routing.status == ST_RESOLVED_BY_THIRD:
                trow["n_resolved_by_third"] += 1
            elif routing.status == ST_ADJUDICATION_NEEDED:
                trow["n_adjudicated"] += 1

    for template in TEMPLATES:
        for name in TEMPLATE_FIELDS[template]:
            row = field_rows[template][name]
            n = row["n_compared"]
            if n > 0:
                # example_disagreement_case_ids carries every non-agree
                # outcome (value disagreements, reason mismatches and
                # absent-vs-present splits alike).
                agreeing = n - len(row["example_disagreement_case_ids"])
                row["exact_agreement"] = round(agreeing / n, 6)
                row["absent_vs_present_rate"] = round(row["n_absent_vs_present"] / n, 6)
            for key in ("example_disagreement_case_ids", "example_absent_split_case_ids", "example_span_only_case_ids"):
                row[key] = sorted(row[key])[:5]
            if name in KAPPA_ELIGIBLE_FIELDS[template]:
                kappa, note, n_pairs = cohen_kappa(
                    kappa_pairs[template][name], field_enum_universe(template, name, contract_path)
                )
                row["kappa"], row["kappa_note"] = kappa, note

    return {
        "schema": "agreement_summary.v1",
        "templates": {
            t: {**template_rows[t], "fields": field_rows[t]} for t in TEMPLATES
        },
        "n_returns_failed_replay": n_returns_failed_replay,
        "n_returns_invalid": len(invalid),
        "invalid_returns": invalid,
        "n_unpaired_returns": len(unpaired),
        "unpaired_case_ids": unpaired,
        "cases": {cid: cases[cid] for cid in sorted(cases)},
    }


def evaluate_minimum_agreement(summary: Mapping[str, Any]) -> dict:
    """Evaluate the pre-registered section 4 minimum-agreement gate.

    The gate applies, per template, on the first-pass two-family round:
    ``exact_agreement >= 0.90`` on every critical field, ``kappa >= 0.80`` on
    every kappa-eligible field with ``n_both_present >= 20`` (fields below 20
    both-present pairs are exempt from the kappa test — spec line ~98), and
    ``n_absent_vs_present <= 10%`` of ``n_compared`` on every quantity field.

    The gate is fail-closed (DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS, amendment
    L6): a critical field with ``n_compared == 0`` is listed in
    ``not_evaluable_fields`` AND is a ``not_evaluable`` failure, so an
    unmeasured template is never usable; a kappa-eligible field with
    ``n_both_present >= 20`` whose kappa is null (only one category observed)
    is a ``kappa_undefined_single_category`` failure. Neither sets
    ``pause_labeling`` — that stays tied to measured exact agreement.
    """
    results: dict[str, dict] = {}
    for template in sorted(summary.get("templates", {})):
        trow = summary["templates"][template]
        failures: list[dict] = []
        not_evaluable: list[str] = []
        pause = False
        kappa_fields = KAPPA_ELIGIBLE_FIELDS[template]
        for name in sorted(trow["fields"]):
            row = trow["fields"][name]
            if row["n_compared"] == 0:
                not_evaluable.append(name)
                failures.append({
                    "field": name,
                    "criterion": "not_evaluable",
                    "value": None,
                    "threshold": EXACT_AGREEMENT_FLOOR,
                    "n": 0,
                    "example_case_ids": [],
                })
                continue
            if row["exact_agreement"] is not None and row["exact_agreement"] < EXACT_AGREEMENT_FLOOR:
                failures.append({
                    "field": name,
                    "criterion": "exact_agreement",
                    "value": row["exact_agreement"],
                    "threshold": EXACT_AGREEMENT_FLOOR,
                    "n": row["n_compared"],
                    "example_case_ids": row["example_disagreement_case_ids"],
                })
                if row["exact_agreement"] < EXACT_AGREEMENT_PAUSE:
                    pause = True
            if name in kappa_fields and row["n_both_present"] >= KAPPA_MIN_N_BOTH_PRESENT:
                if row["kappa"] is None or row["kappa"] < KAPPA_FLOOR:
                    failures.append({
                        "field": name,
                        "criterion": "kappa" if row["kappa"] is not None else "kappa_undefined_single_category",
                        "value": row["kappa"],
                        "threshold": KAPPA_FLOOR,
                        "n": row["n_both_present"],
                        "example_case_ids": row["example_disagreement_case_ids"],
                    })
            if name in QUANTITY_FIELDS[template] and row["absent_vs_present_rate"] is not None:
                if row["absent_vs_present_rate"] > ABSENT_SPLIT_FRACTION_MAX:
                    failures.append({
                        "field": name,
                        "criterion": "absent_vs_present_rate",
                        "value": row["absent_vs_present_rate"],
                        "threshold": ABSENT_SPLIT_FRACTION_MAX,
                        "n": row["n_compared"],
                        "example_case_ids": row["example_absent_split_case_ids"],
                    })
        results[template] = {
            "usable": not failures,
            "pause_labeling": pause,
            "failures": failures,
            "not_evaluable_fields": not_evaluable,
        }
    return {"schema": "minimum_agreement_gate.v1", "templates": results}
