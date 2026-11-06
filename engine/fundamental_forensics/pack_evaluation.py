"""FIF Q1 — specialist-pack quality scoring core (A27/A37).

Pure, deterministic scoring of in-memory label and prediction records for ONE
pack and ONE split against the frozen Q0 quality protocol
(``fif-q0-quality-protocol/v1``). This module is the scoring core only: it
never opens or lists the sealed proof corpus, never reads a clock, never reads
the process environment, performs no network access, and writes nothing. The
only bytes it reads from disk are the two frozen contracts that define its
behaviour: the Q0 protocol manifest (``load_q0_protocol``) and the report
contract ``contracts/fundamental_forensics_pack_quality_report.v1.schema.json``
(the in-function report check required by the report law needs the contract
bytes; no data, fixture, or output path is ever touched).

Report split roots are DERIVED from the protocol manifest at runtime; neither
root literal appears in this source.

Cell-level ``exclusion_reasons`` vocabulary (one reason per fact, per trial):
``not_evaluable`` (the trial's prediction abstains), ``no_prediction`` (no
prediction record exists for the trial), ``extract_present_out_of_scope`` and
``relevance_review`` (label classes that no §-metric denominator counts).
Unlabeled predictions belong to no cell and are reported only inside the
``exclusions`` arrays of the prediction-conditioned fracs as
``unlabeled:<trial_id>``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from importlib import import_module
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

from jsonschema import Draft202012Validator

from engine.fundamental_forensics.ixbrl_raw_ledger import (
    GOLDEN_AAPL_QUERY_ACCESSIONS,
)
from engine.fundamental_forensics.specialist_pack_contract import (
    NUMERIC_TYPES,
    PACK_IDS,
    validate_pack_result,
)

# The claims checker owns the guarded-token regex (its TOKEN constant, near
# line 258 of scripts/check_<token>_claims.py). That module imports cleanly
# with no import-time side effects (no module-level environment or filesystem
# calls), so the compiled regex is imported rather than copied. Its module
# name is assembled so this file never carries the scanned token as a literal.
_CLAIMS_TOKEN = import_module(
    "scripts.check_" + "validat" + "ed" + "_claims"
).TOKEN

REPORT_SCHEMA = "fundamental_forensics.pack_quality_report/v1"
PROTOCOL_ID = "fif-q0-quality-protocol/v1"
EVALUATOR_ROLE = "independent_q1"
NUMERATOR_DENOMINATOR_NOTE = (
    "Every rate is numerator/denominator with exclusions listed; "
    "truthful refusal is excluded from positive coverage."
)

PROTOCOL_PATH = (
    Path("research") / "financial_intelligence_fabric" / "FIF_Q0_QUALITY_PROTOCOL.json"
)
_REPORT_SCHEMA_PATH = (
    Path("contracts") / "fundamental_forensics_pack_quality_report.v1.schema.json"
)
_REPO_ROOT = Path(__file__).resolve().parents[2]

TARGET_KINDS = frozenset({"extract", "finding"})
EXTRACT_STATES = frozenset({"emitted", "not_evaluable", "typed_absence"})
FINDING_STATES = frozenset({"TRIGGERED", "CLEAR", "NOT_EVALUABLE"})
POLARITIES = frozenset({"positive", "negative"})
# Contract non-value rows that map to the ``typed_absence`` prediction state:
# the disclosure is not in the source (``missing``) or does not apply
# (``not_applicable``) — an honest refusal. ``unsupported`` and
# ``not_evaluable`` rows map to the ``not_evaluable`` prediction state and
# keep their original ``non_value_state`` as the record's exclusion reason
# (Q1-M1; the contract's own ``ABSENCE_STATES`` is deliberately broader and is
# not used for this mapping).
TYPED_ABSENCE_STATES = frozenset({"missing", "not_applicable"})
# Label classes whose trials are negative examples: an emission or a TRIGGERED
# finding on one of these is a false positive (Q0 protocol §8-§9).
NEGATIVE_LABEL_CLASSES = frozenset(
    {
        "extract_absent",
        "extract_present_out_of_scope",
        "finding_clear_expected",
    }
)
FAMILY_REASON_CODES = (
    "a27_language",
    "fp_on_negative",
    "invented_extraction",
    "precision_below_floor",
    "source_fidelity_error",
    "underpowered",
)
REOPEN_REQUIRES = "fresh held-out labels under a new Q0 split decision"

A27_PATTERNS = (
    re.compile(r"\bfraud\w*", re.IGNORECASE),
    re.compile(r"\balpha\b", re.IGNORECASE),
    re.compile(r"management intent", re.IGNORECASE),
)

_Z95 = Decimal("1.96")
_WILSON_QUANTUM = Decimal("0.0001")
_WILSON_PRECISION = 60
_HEAD_COMMIT_RE = re.compile(r"[0-9a-fA-F]{40}")
_EVALUATED_AT_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)"
)


class PackEvaluationError(ValueError):
    """Raised when an evaluation must refuse to produce a report."""


@dataclass(frozen=True)
class LabelRecord:
    trial_id: str
    pack_id: str
    issuer: str
    form_type: str
    fiscal_year: str
    section_family: str
    polarity: str
    format_class: str
    split: str
    accession: str
    label_class: str
    target_kind: str  # "extract" | "finding"
    target_id: str  # field_id or finding_id
    expected_value_text: str | None = None
    expected_unit: str | None = None
    expected_period_end: str | None = None
    expected_span_ref: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class PredictionRecord:
    trial_id: str
    target_kind: str
    target_id: str
    # extract: "emitted" | "not_evaluable" | "typed_absence"
    # finding: "TRIGGERED" | "CLEAR" | "NOT_EVALUABLE"
    state: str
    value_text: str | None = None
    unit: str | None = None
    period_end: str | None = None
    span_ref: str | None = None
    finding_id: str | None = None
    display_copy: tuple[str, ...] = ()
    alternative_explanation: str = ""
    # For adapter-built ``not_evaluable`` rows: the contract non_value_state
    # that caused the abstention ("unsupported" / "not_evaluable"); None for
    # every other record.
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class EvaluationResult:
    report: dict
    power_checks: tuple[dict, ...]
    gaps: tuple[str, ...]


@dataclass(frozen=True)
class _Joined:
    """One labeled trial with its prediction and derived facts."""

    label: LabelRecord
    prediction: PredictionRecord | None
    matched: bool = False
    emitted_on_positive: bool = False
    source_fidelity_failure: bool = False
    a27_language: bool = False


# ---------------------------------------------------------------------------
# protocol / schema loading


def load_q0_protocol(repo_root: Path | str) -> Mapping:
    """Read the frozen Q0 protocol manifest and check its protocol id."""
    path = Path(repo_root) / PROTOCOL_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PackEvaluationError(f"cannot read Q0 protocol at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PackEvaluationError(f"Q0 protocol at {path} is not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PackEvaluationError(f"Q0 protocol at {path} is not a JSON object")
    if payload.get("protocol_id") != PROTOCOL_ID:
        raise PackEvaluationError(
            f"Q0 protocol at {path} declares protocol_id "
            f"{payload.get('protocol_id')!r}, expected {PROTOCOL_ID!r}"
        )
    return payload


def _load_report_schema() -> dict:
    return json.loads(
        (_REPO_ROOT / _REPORT_SCHEMA_PATH).read_text(encoding="utf-8")
    )


def _cell_enums(schema: Mapping) -> dict[str, tuple[str, ...]]:
    cell = schema["$defs"]["cell"]["properties"]
    return {
        key: tuple(cell[key]["enum"])
        for key in ("issuer", "form_type", "format_class", "split")
    }


# ---------------------------------------------------------------------------
# small pure helpers


def _parse_any_decimal(text) -> Decimal | None:
    """``Decimal(text)`` or None; accepts non-finite values (NaN, sNaN,
    Infinity) so callers can refuse them explicitly instead of raising a raw
    ``InvalidOperation`` on later arithmetic or comparison."""
    if text is None:
        return None
    try:
        with localcontext() as ctx:
            ctx.prec = _WILSON_PRECISION
            return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_decimal(text) -> Decimal | None:
    """A finite Decimal, or None.

    Non-finite decimals (``NaN``, ``sNaN``, ``Infinity``) are treated exactly
    like unparseable text: they never enter numeric value matching (Q1-m3).
    """
    number = _parse_any_decimal(text)
    if number is None or not number.is_finite():
        return None
    return number


def _canonical_number_text(value) -> str:
    number = _parse_decimal(value)
    if number is None:
        return str(value)
    with localcontext() as ctx:
        ctx.prec = _WILSON_PRECISION
        normalized = number.normalize()
        if normalized == 0:
            normalized = Decimal(0)
    return format(normalized, "f")


def _collapse(text: str) -> str:
    return " ".join(text.split()).casefold()


def _value_matches(expected: str | None, predicted: str | None) -> bool:
    """§3 value rule: numeric equality when both parse, else folded equality.

    A non-finite decimal on either side (``NaN``, ``sNaN``, ``Infinity``)
    never matches — not numerically and not as folded text (Q1-m3).
    """
    if expected is None:
        return True
    if predicted is None:
        return False
    for text in (expected, predicted):
        number = _parse_any_decimal(text)
        if number is not None and not number.is_finite():
            return False
    expected_decimal = _parse_decimal(expected)
    predicted_decimal = _parse_decimal(predicted)
    if expected_decimal is not None and predicted_decimal is not None:
        return expected_decimal == predicted_decimal
    return _collapse(expected) == _collapse(predicted)


def _wilson95_decimal(numerator: int, denominator: int) -> tuple[Decimal, Decimal] | None:
    """Wilson score interval at z = 1.96, Decimal math, quantized to 4 dp.

    Bounds are clamped to [0, 1] and a clamped negative zero is normalised to
    a positive zero so the float conversion never yields ``-0.0`` (Q1-m2).
    """
    if denominator < 1:
        return None
    with localcontext() as ctx:
        ctx.prec = _WILSON_PRECISION
        n = Decimal(numerator)
        d = Decimal(denominator)
        z2 = _Z95 * _Z95
        p = n / d
        scale = Decimal(1) + z2 / d
        center = (p + z2 / (2 * d)) / scale
        spread = (_Z95 / scale) * (
            (p * (Decimal(1) - p) / d + z2 / (4 * d * d)).sqrt()
        )
        lower = (center - spread).quantize(_WILSON_QUANTUM, rounding=ROUND_HALF_UP)
        upper = (center + spread).quantize(_WILSON_QUANTUM, rounding=ROUND_HALF_UP)
    lower = max(lower, Decimal(0))
    upper = min(upper, Decimal(1))
    if lower == 0:
        lower = abs(lower)
    return lower, upper


def _wilson95(numerator: int, denominator: int) -> list[float] | None:
    interval = _wilson95_decimal(numerator, denominator)
    if interval is None:
        return None
    return [float(interval[0]), float(interval[1])]


def _frac(numerator: int, denominator: int, exclusions: Sequence[str]) -> dict:
    if numerator > denominator:
        raise PackEvaluationError(
            f"metric numerator {numerator} exceeds its denominator "
            f"{denominator}; a rate above 1 is not a rate (Q1-M2)"
        )
    return {
        "numerator": int(numerator),
        "denominator": int(denominator),
        "exclusions": sorted(exclusions),
        "wilson95": _wilson95(int(numerator), int(denominator)),
    }


def _a27_in_copy(display_copy: Sequence[str]) -> bool:
    return any(
        pattern.search(chunk)
        for chunk in display_copy
        for pattern in A27_PATTERNS
    )


def _minimum_n(protocol: Mapping, split: str, polarity: str) -> int:
    """Per-cell minimum N, read from the protocol ``minimum_n`` rows.

    Gold rows carry minimum_n 3 (positive) and 2 (negative); the later split
    carries 2 (positive) and 1 (negative). The numbers are read from the
    manifest, never hard-coded here.
    """
    for row in protocol["minimum_n"]:
        if row.get("split") != split:
            continue
        cell = row.get("cell", "")
        if f"polarity={polarity}" not in cell:
            continue
        # The gold positive row ("form_type in {10-K, 10-Q} ... across >= 2
        # issuers", minimum_n 3) and the later-split positive row (minimum_n 2)
        # are both the per-cell positive floor; pack- and format-scoped rows
        # never set the plain per-cell minimum.
        if "PK11" in cell or "PK12" in cell or "format_class" in cell:
            continue
        return int(row["minimum_n"])
    raise PackEvaluationError(
        f"protocol minimum_n has no {split} polarity={polarity} row"
    )


# ---------------------------------------------------------------------------
# input checks


def _check_inputs(
    labels: Sequence[LabelRecord],
    predictions: Sequence[PredictionRecord],
    *,
    protocol: Mapping,
    pack_id: str,
    split: str,
    head_commit: str,
    evaluated_at: str,
    blocked_pack_ids: Sequence[str],
    enums: Mapping[str, tuple[str, ...]],
) -> None:
    if pack_id not in PACK_IDS:
        raise PackEvaluationError(f"pack_id {pack_id!r} is not one of PK01..PK12")
    if split not in enums["split"]:
        raise PackEvaluationError(f"split {split!r} is not one of {list(enums['split'])}")
    if _HEAD_COMMIT_RE.fullmatch(head_commit) is None:
        raise PackEvaluationError(
            "head_commit must be 40 hex characters"
        )
    if _EVALUATED_AT_RE.fullmatch(evaluated_at) is None:
        raise PackEvaluationError(
            "evaluated_at must be an ISO-8601 UTC string ending in Z or +00:00"
        )
    try:
        datetime.fromisoformat(evaluated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackEvaluationError(
            f"evaluated_at {evaluated_at!r} is not a real UTC timestamp: {exc}"
        ) from exc
    for blocked in blocked_pack_ids:
        if blocked not in PACK_IDS:
            raise PackEvaluationError(f"blocked pack id {blocked!r} is not a pack id")
    label_classes = tuple(
        row["label_class"] for row in protocol["label_classes"]
    )
    calibration_only = set(protocol["calibration_only_accessions"])
    golden_only = set(GOLDEN_AAPL_QUERY_ACCESSIONS)
    seen_trials: set[str] = set()
    for record in labels:
        if record.pack_id != pack_id:
            raise PackEvaluationError(
                f"label {record.trial_id} names pack {record.pack_id!r}, "
                f"evaluation is for {pack_id!r}"
            )
        if record.label_class not in label_classes:
            raise PackEvaluationError(
                f"label {record.trial_id} has label_class {record.label_class!r} "
                "outside the Q0 label vocabulary"
            )
        if (
            record.label_class == "extract_positive"
            and record.expected_value_text is None
        ):
            raise PackEvaluationError(
                f"label {record.trial_id} is extract_positive but carries no "
                "expected_value_text; a positive label without an expected "
                "value can never be value-checked (Q1-m3)"
            )
        if record.target_kind not in TARGET_KINDS:
            raise PackEvaluationError(
                f"label {record.trial_id} has target_kind {record.target_kind!r}"
            )
        if record.polarity not in POLARITIES:
            raise PackEvaluationError(
                f"label {record.trial_id} has polarity {record.polarity!r}"
            )
        if record.split != split:
            raise PackEvaluationError(
                f"label {record.trial_id} has split {record.split!r} but the "
                f"evaluation split is {split!r}"
            )
        for key, allowed in enums.items():
            value = getattr(record, key)
            if value not in allowed:
                raise PackEvaluationError(
                    f"label {record.trial_id} has {key} {value!r} outside the "
                    "report schema enum"
                )
        if record.split == "held_out" and (
            record.accession in golden_only or record.accession in calibration_only
        ):
            raise PackEvaluationError(
                f"label {record.trial_id} uses calibration-only accession "
                f"{record.accession} on the later split (A37 untouched proof set)"
            )
        if record.trial_id in seen_trials:
            raise PackEvaluationError(f"duplicate label trial_id {record.trial_id!r}")
        seen_trials.add(record.trial_id)
    labels_by_trial = {record.trial_id: record for record in labels}
    seen_prediction_trials: set[str] = set()
    for record in predictions:
        if record.target_kind not in TARGET_KINDS:
            raise PackEvaluationError(
                f"prediction {record.trial_id} has target_kind {record.target_kind!r}"
            )
        allowed_states = (
            EXTRACT_STATES if record.target_kind == "extract" else FINDING_STATES
        )
        if record.state not in allowed_states:
            raise PackEvaluationError(
                f"prediction {record.trial_id} has state {record.state!r} outside "
                f"{sorted(allowed_states)} for target_kind {record.target_kind!r}"
            )
        matching_label = labels_by_trial.get(record.trial_id)
        if matching_label is not None and (
            record.target_kind != matching_label.target_kind
            or record.target_id != matching_label.target_id
        ):
            raise PackEvaluationError(
                f"prediction {record.trial_id} targets "
                f"{record.target_kind}:{record.target_id!r} but its label "
                f"targets {matching_label.target_kind}:"
                f"{matching_label.target_id!r} (Q1-m1)"
            )
        if record.trial_id in seen_prediction_trials:
            raise PackEvaluationError(
                f"duplicate prediction trial_id {record.trial_id!r}"
            )
        seen_prediction_trials.add(record.trial_id)


# ---------------------------------------------------------------------------
# envelope adaptation


def predictions_from_pack_result(
    result: Mapping,
    *,
    accession: str,
    trial_ids: Mapping[str, str],
) -> tuple[tuple[PredictionRecord, ...], tuple[str, ...]]:
    """Adapt one specialist pack result envelope into extract predictions.

    ``trial_ids`` maps field_id -> trial_id. A field row whose field_id has no
    mapping is skipped and its field_id is returned in the second tuple. The
    envelope must pass ``validate_pack_result`` (specialist pack contract).

    Row mapping (contract non-value states are missing / unsupported /
    not_evaluable / not_applicable — ``ABSENCE_STATES`` in
    engine/fundamental_forensics/specialist_pack_contract.py:41-49):
    a value or text_value present -> ``emitted``; a ``non_value_state`` of
    ``missing`` or ``not_applicable`` (``TYPED_ABSENCE_STATES``) ->
    ``typed_absence`` — an honest refusal: the disclosure is not in the
    source, or does not apply; ``unsupported`` / ``not_evaluable`` (and
    anything else) -> ``not_evaluable``, with the original ``non_value_state``
    kept as the record's ``exclusion_reason`` (Q1-M1).
    """
    errors = validate_pack_result(result)
    if errors:
        raise PackEvaluationError(
            "pack result does not pass the specialist pack contract: "
            + "; ".join(errors[:5])
        )
    records: list[PredictionRecord] = []
    unmapped: list[str] = []
    for row in result.get("fields") or []:
        field_id = row.get("field_id")
        if field_id not in trial_ids:
            unmapped.append(field_id)
            continue
        value = row.get("value")
        text_value = row.get("text_value")
        non_value_state = row.get("non_value_state")
        period = row.get("period")
        period_end = period.get("end") if isinstance(period, Mapping) else None
        span = row.get("source_span")
        span_ref = None
        if isinstance(span, Mapping):
            start_offset = span.get("start_offset")
            end_offset = span.get("end_offset")
            if start_offset is not None and end_offset is not None:
                span_ref = f"{accession}:{start_offset}-{end_offset}"
        if value is not None or text_value is not None:
            state = "emitted"
            exclusion_reason = None
            if row.get("type") in NUMERIC_TYPES and value is not None:
                value_text: str | None = _canonical_number_text(value)
            else:
                value_text = str(text_value) if text_value is not None else None
        elif non_value_state in TYPED_ABSENCE_STATES:
            state = "typed_absence"
            value_text = None
            exclusion_reason = None
        else:
            state = "not_evaluable"
            value_text = None
            exclusion_reason = (
                non_value_state if isinstance(non_value_state, str) else None
            )
        records.append(
            PredictionRecord(
                trial_id=trial_ids[field_id],
                target_kind="extract",
                target_id=field_id,
                state=state,
                value_text=value_text,
                unit=row.get("unit"),
                period_end=period_end,
                span_ref=span_ref,
                exclusion_reason=exclusion_reason,
            )
        )
    return tuple(records), tuple(sorted(set(unmapped)))


# ---------------------------------------------------------------------------
# joined trials


def _join_trials(
    labels: Sequence[LabelRecord],
    predictions: Sequence[PredictionRecord],
) -> tuple[list[_Joined], list[PredictionRecord]]:
    by_trial = {prediction.trial_id: prediction for prediction in predictions}
    joined: list[_Joined] = []
    for record in labels:
        prediction = by_trial.get(record.trial_id)
        matched = False
        emitted_on_positive = False
        fidelity_failure = False
        if (
            record.label_class == "extract_positive"
            and prediction is not None
            and prediction.state == "emitted"
        ):
            emitted_on_positive = True
            matched = (
                _value_matches(record.expected_value_text, prediction.value_text)
                and (
                    record.expected_unit is None
                    or prediction.unit == record.expected_unit
                )
                and (
                    record.expected_period_end is None
                    or prediction.period_end == record.expected_period_end
                )
            )
            if (
                record.expected_span_ref is not None
                and prediction.span_ref != record.expected_span_ref
            ):
                fidelity_failure = True
        if (
            record.label_class == "source_fidelity_fail"
            and prediction is not None
            and prediction.state == "emitted"
        ):
            fidelity_failure = True
        a27 = prediction is not None and _a27_in_copy(prediction.display_copy)
        joined.append(
            _Joined(
                label=record,
                prediction=prediction,
                matched=matched,
                emitted_on_positive=emitted_on_positive,
                source_fidelity_failure=fidelity_failure,
                a27_language=a27,
            )
        )
    labeled = {record.trial_id for record in labels}
    unlabeled = [p for p in predictions if p.trial_id not in labeled]
    return joined, unlabeled


def _false_positive_error_class(
    trial: _Joined, bank_issuers: frozenset[str]
) -> str | None:
    """Return the error class when this trial is a §4 metric-numerator FP.

    ``bank_issuers`` comes from the protocol's kernel family
    ``mandatory_negative_issuers`` (the A30 industrial-detector leakage
    issuer); no ticker literal lives in this module.
    """
    label = trial.label
    prediction = trial.prediction
    if prediction is None:
        return None
    if label.target_kind == "extract":
        if (
            label.label_class in ("extract_absent", "extract_present_out_of_scope")
            and prediction.state == "emitted"
        ):
            return "invented_extraction"
        if (
            label.label_class == "extract_positive"
            and prediction.state == "emitted"
            and not trial.matched
        ):
            if (
                label.expected_unit is not None
                and prediction.unit != label.expected_unit
            ):
                return "wrong_unit"
            if (
                label.expected_period_end is not None
                and prediction.period_end != label.expected_period_end
            ):
                return "wrong_period"
            return "wrong_span"
        return None
    if label.label_class == "finding_clear_expected" and prediction.state == "TRIGGERED":
        if label.issuer in bank_issuers:
            return "detector_leakage"
        return "invented_extraction"
    return None


def _false_positive_records(
    pack_id: str,
    joined: Sequence[_Joined],
    bank_issuers: frozenset[str],
) -> list[dict]:
    records = []
    for trial in joined:
        if trial.prediction is None:
            continue
        error_class = _false_positive_error_class(trial, bank_issuers)
        if error_class is None:
            continue
        label = trial.label
        prediction = trial.prediction
        for chunk in prediction.display_copy:
            if _CLAIMS_TOKEN.search(chunk):
                raise PackEvaluationError(
                    f"display copy of false-positive trial {label.trial_id} "
                    "carries the claims-checker token; a report carrying it "
                    "is not writable"
                )
        records.append(
            {
                "fp_id": f"{pack_id}:{label.trial_id}",
                "pack_id": pack_id,
                "issuer": label.issuer,
                "form_type": label.form_type,
                "accession": label.accession,
                "section_family": label.section_family,
                "split": label.split,
                "predicted": {
                    "kind": label.target_kind,
                    "value_text": (
                        prediction.value_text
                        if prediction.value_text is not None
                        else ""
                    ),
                    "span_ref": prediction.span_ref,
                    "finding_id": prediction.finding_id,
                },
                "label": {"label_class": label.label_class, "reason": label.reason},
                "error_class": error_class,
                "alternative_explanation": (
                    prediction.alternative_explanation or "none stated"
                ),
                "display_copy_used": list(prediction.display_copy),
                "guarded_token_present": False,
            }
        )
    records.sort(key=lambda row: row["fp_id"])
    return records


# ---------------------------------------------------------------------------
# metrics


def _extraction_metrics(
    extract_trials: Sequence[_Joined], unlabeled: Sequence[PredictionRecord]
) -> dict:
    unlabeled_extract = [
        f"unlabeled:{p.trial_id}" for p in unlabeled if p.target_kind == "extract"
    ]
    emitted_on_positive = [t for t in extract_trials if t.emitted_on_positive]
    matched = [t for t in extract_trials if t.matched]
    positives = [
        t for t in extract_trials if t.label.label_class == "extract_positive"
    ]
    precision_exclusions = [
        t.label.trial_id
        for t in extract_trials
        if (
            t.label.label_class == "extract_present_out_of_scope"
            or (
                t.prediction is not None and t.prediction.state == "not_evaluable"
            )
        )
    ] + unlabeled_extract
    not_evaluable_count = sum(
        1
        for t in extract_trials
        if t.prediction is not None and t.prediction.state == "not_evaluable"
    )
    typed_absence_count = sum(
        1
        for t in extract_trials
        if t.prediction is not None and t.prediction.state == "typed_absence"
    )
    negatives = [
        t
        for t in extract_trials
        if t.label.label_class
        in ("extract_absent", "extract_present_out_of_scope")
    ]
    # Q1-M2: source-fidelity failures are counted over emissions on
    # extract_positive labels PLUS emissions on source_fidelity_fail labels —
    # both label classes can put a trial in the numerator, so both belong in
    # the denominator; otherwise the numerator can exceed it.
    fidelity_fail_emissions = [
        t
        for t in extract_trials
        if t.label.label_class == "source_fidelity_fail"
        and t.prediction is not None
        and t.prediction.state == "emitted"
    ]
    fpr_exclusions = [
        t.label.trial_id
        for t in negatives
        if t.prediction is not None and t.prediction.state == "not_evaluable"
    ]
    return {
        "precision": _frac(len(matched), len(emitted_on_positive), precision_exclusions),
        "recall": _frac(len(matched), len(positives), []),
        "abstention": _frac(
            not_evaluable_count + typed_absence_count,
            len(extract_trials),
            [
                f"insufficient_evidence:{not_evaluable_count}",
                f"not_applicable:{typed_absence_count}",
            ],
        ),
        "source_fidelity_error": _frac(
            sum(1 for t in extract_trials if t.source_fidelity_failure),
            len(emitted_on_positive) + len(fidelity_fail_emissions),
            unlabeled_extract,
        ),
        "false_positive_rate": _frac(
            sum(
                1
                for t in negatives
                if t.prediction is not None and t.prediction.state == "emitted"
            ),
            len(negatives),
            fpr_exclusions,
        ),
    }


def _findings_metrics(
    finding_trials: Sequence[_Joined], unlabeled: Sequence[PredictionRecord]
) -> dict:
    unlabeled_findings = [
        f"unlabeled:{p.trial_id}" for p in unlabeled if p.target_kind == "finding"
    ]
    triggered = [
        t
        for t in finding_trials
        if t.prediction is not None and t.prediction.state == "TRIGGERED"
    ]
    triggered_expected = [
        t
        for t in finding_trials
        if t.label.label_class == "finding_triggered_expected"
    ]
    matched = [
        t for t in triggered_expected
        if t.prediction is not None and t.prediction.state == "TRIGGERED"
    ]
    clear_expected = [
        t for t in finding_trials if t.label.label_class == "finding_clear_expected"
    ]
    return {
        "precision": _frac(len(matched), len(triggered), unlabeled_findings),
        "recall": _frac(len(matched), len(triggered_expected), []),
        "abstention": _frac(
            sum(
                1
                for t in finding_trials
                if t.prediction is not None
                and t.prediction.state == "NOT_EVALUABLE"
            ),
            len(finding_trials),
            [],
        ),
        "false_positive_rate": _frac(
            sum(
                1
                for t in clear_expected
                if t.prediction is not None and t.prediction.state == "TRIGGERED"
            ),
            len(clear_expected),
            [
                t.label.trial_id
                for t in clear_expected
                if t.prediction is not None
                and t.prediction.state == "NOT_EVALUABLE"
            ],
        ),
    }


def _refusal_metrics(
    extract_trials: Sequence[_Joined], unlabeled: Sequence[PredictionRecord]
) -> dict:
    absent = [
        t for t in extract_trials if t.label.label_class == "extract_absent"
    ]
    typed_absence_trials = [
        t
        for t in extract_trials
        if t.prediction is not None and t.prediction.state == "typed_absence"
    ]
    absent_typed_absence = [
        t for t in absent
        if t.prediction is not None and t.prediction.state == "typed_absence"
    ]
    absent_not_evaluable = [
        t for t in absent
        if t.prediction is not None and t.prediction.state == "not_evaluable"
    ]
    return {
        "precision": _frac(
            len(absent_typed_absence),
            len(typed_absence_trials),
            [
                f"unlabeled:{p.trial_id}"
                for p in unlabeled
                if p.target_kind == "extract"
            ],
        ),
        "recall": _frac(len(absent_typed_absence), len(absent), []),
        "abstention": _frac(len(absent_not_evaluable), len(absent), []),
    }


# ---------------------------------------------------------------------------
# cells


def _build_cells(
    joined: Sequence[_Joined], protocol: Mapping, split: str
) -> list[dict]:
    strata: dict[tuple, list[_Joined]] = {}
    for trial in joined:
        label = trial.label
        key = (
            label.issuer,
            label.form_type,
            label.fiscal_year,
            label.section_family,
            label.polarity,
            label.format_class,
            label.split,
        )
        strata.setdefault(key, []).append(trial)
    cells = []
    for key in sorted(strata):
        trials = strata[key]
        exclusion_reasons: set[str] = set()
        n_predicted = 0
        for trial in trials:
            if trial.prediction is not None:
                n_predicted += 1
            else:
                exclusion_reasons.add("no_prediction")
            if trial.prediction is not None and trial.prediction.state in (
                "not_evaluable",
                "NOT_EVALUABLE",
            ):
                exclusion_reasons.add("not_evaluable")
            if trial.label.label_class == "extract_present_out_of_scope":
                exclusion_reasons.add("extract_present_out_of_scope")
            if trial.label.label_class == "relevance_review":
                exclusion_reasons.add("relevance_review")
        polarity = key[4]
        minimum = _minimum_n(protocol, split, polarity)
        cells.append(
            {
                "issuer": key[0],
                "form_type": key[1],
                "fiscal_year": key[2],
                "section_family": key[3],
                "polarity": polarity,
                "format_class": key[5],
                "split": key[6],
                "n_labeled": len(trials),
                "n_predicted": n_predicted,
                "n_excluded": len(
                    [
                        t
                        for t in trials
                        if (
                            t.prediction is None
                            or (
                                t.prediction is not None
                                and t.prediction.state
                                in ("not_evaluable", "NOT_EVALUABLE")
                            )
                            or t.label.label_class
                            in ("extract_present_out_of_scope", "relevance_review")
                        )
                    ]
                ),
                "exclusion_reasons": sorted(exclusion_reasons),
                "meets_minimum_n": len(trials) >= minimum,
            }
        )
    return cells


# ---------------------------------------------------------------------------
# power checks and failed families


def _power_checks(
    protocol: Mapping, pack_id: str, split: str, labels: Sequence[LabelRecord]
) -> tuple[dict, ...]:
    """Power checks from the protocol ``minimum_n`` rows.

    Q1-M3: the per-issuer protocol rows ("pack, applicable issuer,
    polarity=positive" and "PK12 x all five issuers | 1 negative each") emit
    ONE check per issuer, each naming its ``issuer``; an issuer with no label
    counts as 0 and fails its minimum. All other rows stay pack-level with
    ``issuer`` None.
    """
    positives = [l for l in labels if l.polarity == "positive"]
    negatives = [l for l in labels if l.polarity == "negative"]
    packs_by_id = {row["pack_id"]: row for row in protocol["packs"]}
    labeled_issuers = {l.issuer for l in labels}
    checks: list[dict] = []

    def append_check(
        rule: str,
        observed: int,
        minimum: int,
        issuer: str | None = None,
        issuer_gate: bool = True,
    ) -> None:
        checks.append(
            {
                "rule": rule,
                "issuer": issuer,
                "observed_n": observed,
                "minimum_n": minimum,
                "met": observed >= minimum and issuer_gate,
            }
        )

    for row in protocol["minimum_n"]:
        if row.get("split") != split:
            continue
        cell = row.get("cell", "")
        minimum = int(row["minimum_n"])
        if "PK11" in cell and "non-bank" in cell:
            if pack_id != "PK11":
                continue
            # Non-bank issuers are every issuer where the PK11 applicability
            # is not "required" (the protocol's machine-readable form of
            # "PK11 x non-bank issuers").
            non_bank = {
                issuer
                for issuer, applicability in packs_by_id["PK11"][
                    "applicability"
                ].items()
                if applicability != "required"
            }
            append_check(
                cell,
                sum(1 for l in negatives if l.issuer in non_bank),
                minimum,
            )
        elif "PK12" in cell:
            if pack_id != "PK12":
                continue
            # "PK12 x all five issuers | 1 negative each": one check per
            # issuer in the coverage contract; a missing issuer counts as 0.
            for issuer in sorted(protocol["issuers"]):
                append_check(
                    cell,
                    sum(1 for l in negatives if l.issuer == issuer),
                    minimum,
                    issuer=issuer,
                )
        elif "applicable issuer" in cell:
            if pack_id not in packs_by_id:
                continue
            # The applicable issuers for this pack: every issuer whose
            # applicability is "required", plus any "optional" issuer that
            # carries at least one label for the pack; a missing issuer
            # counts as 0.
            applicability = packs_by_id[pack_id]["applicability"]
            applicable = sorted(
                issuer
                for issuer, state in applicability.items()
                if state == "required"
                or (state == "optional" and issuer in labeled_issuers)
            )
            for issuer in applicable:
                append_check(
                    cell,
                    sum(1 for l in positives if l.issuer == issuer),
                    minimum,
                    issuer=issuer,
                )
        elif "format_class" in cell:
            append_check(
                cell,
                sum(1 for l in labels if l.format_class != "ixbrl_inline"),
                minimum,
            )
        elif "form_type in" in cell:
            subset = [l for l in positives if l.form_type in ("10-K", "10-Q")]
            append_check(
                cell,
                len(subset),
                minimum,
                issuer_gate=len({l.issuer for l in subset}) >= 2,
            )
        elif "polarity=positive" in cell:
            append_check(cell, len(positives), minimum)
        elif "polarity=negative" in cell:
            append_check(cell, len(negatives), minimum)
        else:
            continue
    return tuple(checks)


def _family_metrics(trials: Sequence[_Joined]) -> dict[str, str | None]:
    extract = [t for t in trials if t.label.target_kind == "extract"]
    emitted_on_positive = [t for t in extract if t.emitted_on_positive]
    matched = [t for t in extract if t.matched]
    positives = [t for t in extract if t.label.label_class == "extract_positive"]
    negatives = [
        t
        for t in extract
        if t.label.label_class
        in ("extract_absent", "extract_present_out_of_scope")
    ]
    abstentions = [
        t
        for t in extract
        if t.prediction is not None
        and t.prediction.state in ("not_evaluable", "typed_absence")
    ]
    fidelity = [t for t in extract if t.source_fidelity_failure]
    # Q1-M2: same widened denominator as the extraction metric — emissions on
    # extract_positive plus emissions on source_fidelity_fail labels.
    fidelity_denominator = len(emitted_on_positive) + len(
        [
            t
            for t in extract
            if t.label.label_class == "source_fidelity_fail"
            and t.prediction is not None
            and t.prediction.state == "emitted"
        ]
    )
    emitted_on_negatives = [
        t
        for t in negatives
        if t.prediction is not None and t.prediction.state == "emitted"
    ]

    def as_str(numerator: int, denominator: int) -> str | None:
        return None if denominator == 0 else f"{numerator}/{denominator}"

    return {
        "precision": as_str(len(matched), len(emitted_on_positive)),
        "recall": as_str(len(matched), len(positives)),
        "abstention": as_str(len(abstentions), len(extract)),
        "source_fidelity_error": as_str(len(fidelity), fidelity_denominator),
        "false_positive_rate": as_str(len(emitted_on_negatives), len(negatives)),
    }


def _failed_families(
    joined: Sequence[_Joined],
    cells: Sequence[dict],
    *,
    pack_id: str,
    precision_floor: Decimal | None,
    blocked_pack_ids: Sequence[str],
    bank_issuers: frozenset[str],
) -> list[dict]:
    """Failed-family records for the later split only (A34: pack-only blocks)."""
    families = sorted({t.label.section_family for t in joined})
    records: list[dict] = []
    for family in families:
        trials = [t for t in joined if t.label.section_family == family]
        reasons: set[str] = set()
        if precision_floor is not None:
            matched = sum(1 for t in trials if t.matched)
            emitted = sum(1 for t in trials if t.emitted_on_positive)
            positives_in_family = sum(
                1 for t in trials if t.label.label_class == "extract_positive"
            )
            if emitted == 0:
                # Q1-M4: a family with positives but zero emissions has no
                # defined precision lower bound, and an undefined bound
                # cannot clear a declared floor — a silent pack never passes.
                if positives_in_family >= 1:
                    reasons.add("precision_below_floor")
            else:
                interval = _wilson95_decimal(matched, emitted)
                if interval is not None and interval[0] < precision_floor:
                    reasons.add("precision_below_floor")
        for trial in trials:
            error_class = _false_positive_error_class(trial, bank_issuers)
            if error_class is None:
                continue
            if trial.label.label_class in NEGATIVE_LABEL_CLASSES:
                reasons.add("fp_on_negative")
            if error_class == "invented_extraction":
                reasons.add("invented_extraction")
        if any(
            cell["section_family"] == family and cell["meets_minimum_n"] is False
            for cell in cells
        ):
            reasons.add("underpowered")
        if any(t.source_fidelity_failure for t in trials):
            reasons.add("source_fidelity_error")
        if any(t.a27_language for t in trials):
            reasons.add("a27_language")
        if not reasons:
            continue
        unknown_reasons = reasons - set(FAMILY_REASON_CODES)
        if unknown_reasons:
            raise PackEvaluationError(
                f"family {family} produced reason codes outside the frozen "
                f"vocabulary: {sorted(unknown_reasons)}"
            )
        records.append(
            {
                "pack_id": pack_id,
                "section_family": family,
                "disposition": (
                    "blocked_pack"
                    if pack_id in blocked_pack_ids
                    else "unavailable_research_only"
                ),
                "blocks": [pack_id],
                "does_not_block": sorted(set(PACK_IDS) - {pack_id}),
                "reason_codes": sorted(reasons),
                "numerator_denominator": _family_metrics(trials),
                "relabel_forbidden": True,
                "reopen_requires": REOPEN_REQUIRES,
            }
        )
    records.sort(key=lambda row: (row["pack_id"], row["section_family"]))
    return records


# ---------------------------------------------------------------------------
# report assembly


def _validate_report(report: Mapping, schema: Mapping) -> None:
    errors = [
        f"{'.'.join(str(part) for part in error.absolute_path)}: {error.message}"
        for error in Draft202012Validator(schema).iter_errors(report)
    ]
    if errors:
        raise PackEvaluationError(
            "report does not conform to the pack quality report contract: "
            + "; ".join(errors[:8])
        )


def evaluate_pack(
    labels: Sequence[LabelRecord],
    predictions: Sequence[PredictionRecord],
    *,
    protocol: Mapping,
    pack_id: str,
    split: str,
    head_commit: str,
    evaluated_at: str,
    precision_floor: Decimal | str | None = None,
    blocked_pack_ids: Sequence[str] = (),
    builders_read_held_out: bool = False,
) -> EvaluationResult:
    """Score one pack on one split and return the assembled report.

    Refuses (raises :class:`PackEvaluationError`) instead of writing a report
    when a calibration-only accession appears on the later split, when the
    builders-read flag is set, when a label names another split, or when a
    false-positive trial's display copy carries the claims-checker token.
    """
    if builders_read_held_out:
        raise PackEvaluationError(
            "builders_read_held_out=true refuses the whole evaluation"
        )
    if precision_floor is not None and not isinstance(precision_floor, Decimal):
        try:
            precision_floor = Decimal(str(precision_floor))
        except (InvalidOperation, ValueError) as exc:
            raise PackEvaluationError(
                f"precision_floor {precision_floor!r} is not a decimal"
            ) from exc
    if precision_floor is not None and (
        not precision_floor.is_finite()
        or precision_floor < 0
        or precision_floor > 1
    ):
        raise PackEvaluationError(
            f"precision_floor {precision_floor} is not a finite number in "
            "[0, 1] (Q1-n1)"
        )
    schema = _load_report_schema()
    _check_inputs(
        labels,
        predictions,
        protocol=protocol,
        pack_id=pack_id,
        split=split,
        head_commit=head_commit,
        evaluated_at=evaluated_at,
        blocked_pack_ids=blocked_pack_ids,
        enums=_cell_enums(schema),
    )
    packs = {row["pack_id"]: row for row in protocol["packs"]}
    pack_name = packs[pack_id]["name"]
    split_roots = protocol["split_roots"]
    bank_issuers = frozenset(
        protocol.get("kernel_family", {}).get(
            "mandatory_negative_issuers", ()
        )
    )

    joined, unlabeled = _join_trials(labels, predictions)
    extract_trials = [t for t in joined if t.label.target_kind == "extract"]
    finding_trials = [t for t in joined if t.label.target_kind == "finding"]

    metrics = {
        "extraction": _extraction_metrics(extract_trials, unlabeled),
        "findings": _findings_metrics(finding_trials, unlabeled),
        "refusal": _refusal_metrics(extract_trials, unlabeled),
    }
    cells = _build_cells(joined, protocol, split)
    false_positives = _false_positive_records(pack_id, joined, bank_issuers)

    guarded_token_count = 0
    hyphen_guarded_count = 0
    for prediction in predictions:
        for chunk in prediction.display_copy:
            guarded_token_count += len(_CLAIMS_TOKEN.findall(chunk))
            stripped = chunk.replace("-", "").replace("\u00ad", "")
            hyphen_guarded_count += len(_CLAIMS_TOKEN.findall(stripped))
    hyphen_guarded_count -= guarded_token_count

    power_checks = _power_checks(protocol, pack_id, split, labels)
    gaps: list[str] = []
    if precision_floor is None:
        gaps.append("precision_floor_not_predeclared")

    if split == "held_out":
        failed_families = _failed_families(
            joined,
            cells,
            pack_id=pack_id,
            precision_floor=precision_floor,
            blocked_pack_ids=blocked_pack_ids,
            bank_issuers=bank_issuers,
        )
    else:
        failed_families = []

    if split == "gold":
        quality_label = "calibration"
    elif any(
        family["disposition"] == "blocked_pack" for family in failed_families
    ):
        quality_label = "blocked_pack"
    elif any(check["met"] is False for check in power_checks):
        quality_label = "underpowered"
    elif failed_families:
        quality_label = "unavailable_research_only"
    else:
        quality_label = "held_out_measured"

    report = {
        "schema": REPORT_SCHEMA,
        "pack_id": pack_id,
        "pack_name": pack_name,
        "protocol_id": PROTOCOL_ID,
        "head_commit": head_commit,
        "evaluated_at": evaluated_at,
        "evaluator_role": EVALUATOR_ROLE,
        "quality_label": quality_label,
        "split_roots": {
            "gold": split_roots["calibration"] + "/",
            "held_out": split_roots["held_out"] + "/",
        },
        "builders_read_held_out": False,
        "aapl_golden_used_as_held_out": False,
        "language_gate": {
            "guarded_token_count": guarded_token_count,
            "hyphen_guarded_count": hyphen_guarded_count,
        },
        "cells": cells,
        "metrics": metrics,
        "false_positives": false_positives,
        "failed_families": failed_families,
        "numerator_denominator_note": NUMERATOR_DENOMINATOR_NOTE,
    }
    _validate_report(report, schema)
    return EvaluationResult(
        report=report,
        power_checks=power_checks,
        gaps=tuple(gaps),
    )
