"""Capital-structure V2 task B1: select one comparable share basis, or refuse.

``select_share_basis`` is the only owner-declared interface of this module
(``issuer_state_contracts.INTERFACE_OWNERSHIP``).  It reads share-count
observations admitted under ``config/capital_structure_share_source_admission.v1.json``
(task B0) and evidenced corporate actions, and returns a frozen
``ShareBasisResult``.  It is deterministic: no HTTP, collector, LLM or SEC
request, and the receipt's ``computed_at`` is the caller's ``as_of``.

Selection law (gates A16/A17/A18/A19/A48 of the 2026-10-13 masterplan):

* Only an *observed* ``common_shares_outstanding`` fact on the shares unit
  can be selected, and only as ``issued_and_outstanding``.  Public float
  (USD), weighted-average EPS shares and non-affiliate shares never stand in
  for it — they are rejected with a named reason, never converted.
* The latest clean instant wins only when nothing at that instant disagrees.
  Two values, an ambiguous fact or a unit mismatch at the same instant is a
  ``conflict``; the largest or newest-looking figure is never chosen.
* An unconfirmed fact after the selected instant, or a basis older than
  ``MAX_BASIS_AGE_DAYS``, is ``refused`` ("old or unconfirmed share basis",
  review class 3).
* A split is applied only when authorization, vote, effective split and
  exchange adjustment are each separately observed, agree on kind, ratio,
  date and security, and the split took effect strictly after the count's
  instant (pre-split, security-matched items only).  A non-integral result
  refuses rather than guessing fractional-share treatment.  An event-spine
  charter amendment after the count refuses; a vote or authorization alone is
  only a note.
* No probability, score or sizing is produced; every authority flag on an
  input must already be false.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from fractions import Fraction
from typing import Any, Mapping, Sequence

from engine.capital_structure.issuer_state_contracts import (
    COMPATIBLE_INPUT_SCHEMAS,
    CalculationReceipt,
    CorporateActionBasis,
    CorporateActionInputs,
    EvidenceRef,
    FamilyProvenance,
    Provenance,
    Quantity,
    ShareBasisResult,
    ShareInputs,
    ShareObservationRef,
    sha256_of,
    stable_id,
)

IMPLEMENTATION = "engine.capital_structure.share_basis.select_share_basis/1"
COMPILER_VERSION = "capital_structure.share_basis/1"
ADMISSION_CONFIG = "config/capital_structure_share_source_admission.v1.json"

#: Review class 3 ("old or unconfirmed share basis"): a quarterly cover/balance
#: count plus the longest ordinary filing lag.  Older than this is refused.
MAX_BASIS_AGE_DAYS = 150

#: Authorized-capital facts are state quantities, never a comparable share
#: basis: they can never be a candidate and never change a selection.
AUTHORIZED_CAPITAL_KINDS = ("common_shares_authorized", "common_shares_issued", "common_shares_reserved_for_future_issuance")

#: The B0 admission's support limits, carried verbatim on every partial result
#: (cross-checked against the config by the test suite).
SUPPORT_LIMITS: tuple[str, ...] = (
    "publication_not_activated",
    "provider_conformance_unproven",
    "concurrent_writer_unproven",
    "retention_disabled",
    "no_committed_share_ledger",
    "collector_production_unverified",
    "security_class_concept_level_only",
    "weighted_average_eps_not_admitted",
    "non_affiliate_shares_not_admitted",
)

SPLIT_STAGES = ("authorization", "vote", "effective", "exchange_adjustment")
SPLIT_KINDS = ("reverse_split", "forward_split")
_EVENT_EFFECTIVE_SUBTYPES = ("charter_amendment_candidate",)
_EVENT_NOTE_SUBTYPES = ("shareholder_vote_candidate", "authorization_or_vote_candidate")
_RATIO_PLACES = Decimal("0.000000000001")

RULES: dict[str, Any] = {
    "implementation": IMPLEMENTATION,
    "admission_config": ADMISSION_CONFIG,
    "selectable_metric": "common_shares_outstanding",
    "selectable_unit": "shares",
    "selectable_disposition": "observed",
    "selected_basis": "issued_and_outstanding",
    "never_substitutes": ["public_float", "weighted_average_eps", "non_affiliate_public_float"],
    "max_basis_age_days": MAX_BASIS_AGE_DAYS,
    "same_instant_disagreement": "conflict",
    "unconfirmed_after_selected_instant": "refused",
    "security_class_id": "<issuer_id>:security:common_stock",
    "split_stages": list(SPLIT_STAGES),
    "split_applies_to": "pre-split issued_and_outstanding count of the matched security, effective strictly after the count instant and on or before as_of",
    "split_on_count_date": "refused",
    "split_fractional_result": "refused",
    "event_charter_amendment_after_count": "refused",
    "event_vote_or_authorization": "note_only",
    "support_cap": "partial",
    "support_limits": list(SUPPORT_LIMITS),
    "authority": "context_only",
}
RULE_DIGEST = sha256_of(RULES)


class ShareBasisInputError(ValueError):
    """The inputs cannot be judged at all (mixed issuers, authority claims, wrong family)."""


@dataclass(frozen=True)
class _Fact:
    record: Mapping[str, Any]
    observation_id: str
    instant: date
    available_at: datetime
    clean: bool
    value: Decimal | None
    reason: str


@dataclass(frozen=True)
class SplitDecision:
    """Outcome of evaluating evidenced corporate-action records against one count."""

    applied: CorporateActionBasis
    action_id: str | None = None
    numerator: int | None = None
    denominator: int | None = None
    refusals: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    available_at: str | None = None


# ---------------------------------------------------------------------------
# Small parsers (inputs are already contract-checked for schema and keys)
# ---------------------------------------------------------------------------


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(record: Mapping[str, Any], *path: str) -> Any:
    node: Any = record
    for key in path:
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def _nonneg_decimal(value: Any) -> Decimal | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite() or parsed < 0:
        return None
    return parsed


def _positive_fraction(value: Any) -> Fraction | None:
    parsed = _nonneg_decimal(value)
    if parsed is None or parsed == 0:
        return None
    return Fraction(parsed)


def _decimal_text(value: Decimal | Fraction) -> str:
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        with localcontext() as ctx:
            ctx.prec = 50
            exact = Decimal(value.numerator) / Decimal(value.denominator)
            if Fraction(exact) != value:
                exact = exact.quantize(_RATIO_PLACES, rounding=ROUND_HALF_EVEN)
        value = exact
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def security_class_id_for(issuer_id: str) -> str:
    """The common-stock security id this module selects for (published in ``RULES``)."""

    return f"{issuer_id}:security:common_stock"


def _available_instant(record: Mapping[str, Any]) -> datetime | None:
    pit = record.get("point_in_time") if isinstance(record.get("point_in_time"), Mapping) else {}
    for key in ("available_at", "public_available_at"):
        parsed = _parse_ts(pit.get(key))
        if parsed is not None:
            return parsed
    parsed = _parse_ts(_get(record, "filing", "accepted_at"))
    if parsed is not None:
        return parsed
    filed = _parse_date(_get(record, "filing", "filed")) or _parse_date(_get(record, "filing", "filing_date"))
    if filed is not None:
        return datetime(filed.year, filed.month, filed.day, 23, 59, 59, tzinfo=timezone.utc)
    return None


def _assert_context_only(record: Mapping[str, Any], label: str) -> None:
    authority = record.get("authority")
    if not isinstance(authority, Mapping):
        raise ShareBasisInputError(f"{label}: authority block required (context-only inputs)")
    if authority.get("is_context_only") is not True:
        raise ShareBasisInputError(f"{label}: input is not context-only")
    for flag, granted in sorted(authority.items()):
        if flag != "is_context_only" and granted not in (None, False):
            # A17: an observed ledger (or any other input) never selects the denominator.
            raise ShareBasisInputError(f"{label}: {flag} must be false — no input selects, ranks or sizes")


def _issuer_of(record: Mapping[str, Any]) -> str | None:
    issuer = record.get("issuer_id")
    if isinstance(issuer, str) and issuer:
        return issuer
    nested = _get(record, "issuer", "issuer_id")
    return nested if isinstance(nested, str) and nested else None


def _resolve_issuer(observations: Sequence[Mapping[str, Any]], actions: Sequence[Mapping[str, Any]]) -> str:
    issuers = {_issuer_of(item) for item in (*observations, *actions)}
    issuers.discard(None)
    if not issuers:
        raise ShareBasisInputError("no issuer identity: ShareInputs carries none and no record names one")
    if len(issuers) > 1:
        raise ShareBasisInputError(f"mixed issuers in one share-basis call: {sorted(str(item) for item in issuers)}")
    return str(next(iter(issuers)))


# ---------------------------------------------------------------------------
# Corporate actions
# ---------------------------------------------------------------------------


def _evidence_refs(record: Mapping[str, Any]) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = []
    for item in record.get("evidence") or ():
        if isinstance(item, Mapping):
            refs.append(EvidenceRef(str(item.get("manifest_id")), str(item.get("span_id")), str(item.get("text_sha256"))))
    return tuple(refs)


def evaluate_split_actions(
    actions: Sequence[Mapping[str, Any]],
    *,
    issuer_id: str,
    security_class_id: str,
    count_instant: date,
    as_of: datetime,
) -> SplitDecision:
    """Judge ``capital_structure.corporate_action_observation.v1`` records against one count.

    Pure over records: no binding is required, so the stage handling is
    testable before the corporate-actions family is admitted to the contract.
    """

    as_of_day = as_of.date()
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    notes: list[str] = []
    for index, record in enumerate(actions):
        _assert_context_only(record, f"corporate_actions[{index}]")
        if _issuer_of(record) != issuer_id:
            raise ShareBasisInputError(f"corporate_actions[{index}]: issuer {_issuer_of(record)!r} differs from {issuer_id!r}")
        available = _available_instant(record)
        if available is None or available > as_of:
            notes.append(f"not_yet_available:{record.get('observation_id')}")
            continue
        action_id = record.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise ShareBasisInputError(f"corporate_actions[{index}]: action_id required")
        grouped.setdefault(action_id, []).append(record)

    applicable: list[tuple[str, list[Mapping[str, Any]], date]] = []
    refusals: list[str] = []
    for action_id in sorted(grouped):
        records = grouped[action_id]
        by_stage: dict[str, list[Mapping[str, Any]]] = {}
        for record in records:
            by_stage.setdefault(str(record.get("stage")), []).append(record)
        dates = {_parse_date(record.get("effective_date")) for record in records}
        dates.discard(None)
        if not dates:
            notes.append(f"pending:{action_id}:no_effective_date")
            continue
        if len(dates) > 1:
            if any(count_instant < day <= as_of_day for day in dates):
                refusals.append(f"unconfirmed:split_effective_date_disagrees:{action_id}")
            else:
                notes.append(f"rejected:{action_id}:effective_date_disagrees_outside_window")
            continue
        effective = next(iter(dates))
        if effective > as_of_day:
            notes.append(f"rejected:{action_id}:effective_after_as_of:{effective.isoformat()}")
            continue
        if effective < count_instant:
            notes.append(f"already_reflected:{action_id}:effective_before_count:{effective.isoformat()}")
            continue
        if effective == count_instant:
            refusals.append(f"unconfirmed:split_effective_on_count_date:{action_id}")
            continue
        applicable.append((action_id, records, effective))

    if len(applicable) > 1:
        refusals.append("unconfirmed:multiple_corporate_actions_after_count:" + ",".join(item[0] for item in applicable))
        return SplitDecision(applied=CorporateActionBasis(), refusals=tuple(refusals), notes=tuple(notes))
    if not applicable or refusals:
        return SplitDecision(applied=CorporateActionBasis(), refusals=tuple(refusals), notes=tuple(notes))

    action_id, records, effective = applicable[0]
    by_stage = {}
    for record in records:
        by_stage.setdefault(str(record.get("stage")), []).append(record)
    observed: dict[str, Mapping[str, Any]] = {}
    for stage in SPLIT_STAGES:
        stage_records = [item for item in by_stage.get(stage, ()) if _get(item, "state", "disposition") == "observed"]
        if len(stage_records) > 1:
            refusals.append(f"unconfirmed:split_stage_duplicated:{action_id}:{stage}")
        elif stage_records:
            observed[stage] = stage_records[0]
    missing = [stage for stage in SPLIT_STAGES if stage not in observed]
    if missing:
        label = "split_pending" if "effective" in missing else "split_stage_unevidenced"
        refusals.append(f"unconfirmed:{label}:{action_id}:missing:{'+'.join(missing)}")
    if refusals:
        return SplitDecision(applied=CorporateActionBasis(), refusals=tuple(refusals), notes=tuple(notes))

    kinds = {str(item.get("action_kind")) for item in observed.values()}
    ratios = {(str(_get(item, "ratio", "new_shares")), str(_get(item, "ratio", "old_shares"))) for item in observed.values()}
    securities = {str(item.get("security_class_id")) for item in observed.values()}
    if len(kinds) > 1:
        refusals.append(f"unconfirmed:split_kind_disagrees:{action_id}")
    if len(ratios) > 1:
        refusals.append(f"unconfirmed:split_ratio_disagrees:{action_id}")
    if len(securities) > 1 or securities != {security_class_id}:
        refusals.append(f"unconfirmed:split_security_unmatched:{action_id}")
    if refusals:
        return SplitDecision(applied=CorporateActionBasis(), refusals=tuple(refusals), notes=tuple(notes))

    kind = next(iter(kinds))
    if kind not in SPLIT_KINDS:
        refusals.append(f"unconfirmed:corporate_action_not_modeled:{action_id}:{kind}")
        return SplitDecision(applied=CorporateActionBasis(), refusals=tuple(refusals), notes=tuple(notes))
    new_raw, old_raw = next(iter(ratios))
    new_shares, old_shares = _positive_fraction(new_raw), _positive_fraction(old_raw)
    if new_shares is None or old_shares is None:
        refusals.append(f"unconfirmed:split_ratio_invalid:{action_id}")
        return SplitDecision(applied=CorporateActionBasis(), refusals=tuple(refusals), notes=tuple(notes))
    factor = new_shares / old_shares
    if (kind == "reverse_split" and not factor < 1) or (kind == "forward_split" and not factor > 1):
        refusals.append(f"unconfirmed:split_ratio_inconsistent_with_kind:{action_id}")
        return SplitDecision(applied=CorporateActionBasis(), refusals=tuple(refusals), notes=tuple(notes))

    evidence: list[EvidenceRef] = []
    for stage in SPLIT_STAGES:
        for ref in _evidence_refs(observed[stage]):
            if ref not in evidence:
                evidence.append(ref)
    if not evidence:
        refusals.append(f"unconfirmed:split_without_evidence:{action_id}")
        return SplitDecision(applied=CorporateActionBasis(), refusals=tuple(refusals), notes=tuple(notes))
    ratio_text = _decimal_text(factor)
    if Fraction(Decimal(ratio_text)) != factor:
        notes.append(f"split_ratio:{_decimal_text(Decimal(new_raw))}-for-{_decimal_text(Decimal(old_raw))}")
    latest = max(_available_instant(item) for item in observed.values())  # type: ignore[type-var]
    return SplitDecision(
        applied=CorporateActionBasis(
            kind=kind,
            ratio=ratio_text,
            effective_date=effective.isoformat(),
            contract_adjustment_evidence=tuple(evidence),
        ),
        action_id=action_id,
        numerator=factor.numerator,
        denominator=factor.denominator,
        notes=tuple(notes),
        evidence=tuple(evidence),
        available_at=_iso(latest),
    )


def _event_notes(
    events: Sequence[Mapping[str, Any]], *, issuer_id: str, count_instant: date, as_of: datetime,
) -> tuple[list[str], list[str]]:
    refusals: list[str] = []
    notes: list[str] = []
    for index, record in enumerate(events):
        if _get(record, "event", "family") != "corporate_action":
            continue
        _assert_context_only(record, f"events[{index}]")
        if _issuer_of(record) != issuer_id:
            raise ShareBasisInputError(f"events[{index}]: issuer {_issuer_of(record)!r} differs from {issuer_id!r}")
        available = _available_instant(record)
        filed = _parse_date(_get(record, "filing", "filing_date"))
        if available is None or available > as_of or filed is None or filed <= count_instant:
            continue
        subtype = _get(record, "event", "subtype")
        event_id = str(record.get("event_id"))
        if subtype in _EVENT_EFFECTIVE_SUBTYPES:
            refusals.append(f"unconfirmed:{subtype}:{event_id}:{filed.isoformat()}")
        elif subtype in _EVENT_NOTE_SUBTYPES:
            notes.append(f"rejected:{event_id}:vote_or_authorization_is_not_an_effective_split")
    return refusals, notes


# ---------------------------------------------------------------------------
# Share-count facts
# ---------------------------------------------------------------------------


def _classify(record: Mapping[str, Any], as_of: datetime) -> tuple[_Fact | None, str | None]:
    """Return a timeline fact, or a rejection note for a record that can never be a candidate."""

    observation_id = str(record.get("observation_id"))
    metric = _get(record, "metric", "kind")
    if metric == "public_float":
        return None, f"rejected:{observation_id}:public_float_usd_is_not_a_share_basis"
    if metric in AUTHORIZED_CAPITAL_KINDS:
        return None, f"not_a_share_basis_kind:{metric}"
    if metric != "common_shares_outstanding":
        return None, f"rejected:{observation_id}:metric_not_admitted:{metric}"
    if _get(record, "security_class", "classification") != "common_stock":
        return None, f"rejected:{observation_id}:security_not_common_stock"
    instant = _parse_date(_get(record, "period", "period_end"))
    if instant is None:
        return None, f"rejected:{observation_id}:no_instant"
    if instant > as_of.date():
        return None, f"rejected:{observation_id}:instant_after_as_of"
    available = _available_instant(record)
    assert available is not None  # eligibility was checked by the caller
    disposition = _get(record, "state", "disposition")
    normalized = record.get("normalized") if isinstance(record.get("normalized"), Mapping) else {}
    value = _nonneg_decimal(normalized.get("value"))
    if disposition != "observed":
        return _Fact(record, observation_id, instant, available, False, None, f"{disposition}:{_get(record, 'state', 'reason')}"), None
    if normalized.get("unit") != "shares" or str(_get(record, "fact", "unit")) != "shares":
        return _Fact(record, observation_id, instant, available, False, None, f"unit_mismatch:{normalized.get('unit')}"), None
    if normalized.get("scale") not in ("1", None):
        return _Fact(record, observation_id, instant, available, False, None, f"scale_mismatch:{normalized.get('scale')}"), None
    if value is None:
        return _Fact(record, observation_id, instant, available, False, None, "value_not_a_nonnegative_decimal"), None
    return _Fact(record, observation_id, instant, available, True, value, "observed"), None


def _superseded_ids(records: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    superseded: dict[str, str] = {}
    for record in records:
        by = str(record.get("observation_id"))
        for old in _get(record, "relationships", "supersedes") or ():
            superseded[str(old)] = by
        prior = _get(record, "version", "correction_of")
        if isinstance(prior, str) and prior:
            superseded[prior] = by
    return superseded


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


def select_share_basis(observations: ShareInputs, actions: CorporateActionInputs, as_of: str) -> ShareBasisResult:
    """Select the comparable issued-and-outstanding share basis as of ``as_of``, or refuse."""

    if not isinstance(observations, ShareInputs):
        raise ShareBasisInputError("observations: ShareInputs required")
    if not isinstance(actions, CorporateActionInputs):
        raise ShareBasisInputError("actions: CorporateActionInputs required")
    as_of_at = _parse_ts(as_of)
    if as_of_at is None:
        raise ShareBasisInputError("as_of: timezone-aware ISO timestamp required")
    action_family = actions.binding.input_family
    if actions.actions and action_family not in ("events", "corporate_actions"):
        raise ShareBasisInputError(f"actions: corporate actions come from events or corporate_actions, not {action_family!r}")

    for index, record in enumerate(observations.observations):
        _assert_context_only(record, f"share_count_observations[{index}]")
    issuer_id = _resolve_issuer(observations.observations, actions.actions)
    security_id = security_class_id_for(issuer_id)
    binding = observations.binding
    generation_id = binding.generation_id

    conflicts: list[str] = []
    refusals: list[str] = []
    notes: list[str] = []
    if not actions.actions:
        notes.append("corporate_actions_unobserved")

    eligible: list[Mapping[str, Any]] = []
    for record in observations.observations:
        available = _available_instant(record)
        filed = _parse_date(_get(record, "filing", "filed"))
        if available is None or available > as_of_at or (filed is not None and filed > as_of_at.date()):
            notes.append(f"not_yet_available:{record.get('observation_id')}")
            continue
        eligible.append(record)
    superseded = _superseded_ids(eligible)
    facts: list[_Fact] = []
    for record in eligible:
        observation_id = str(record.get("observation_id"))
        if observation_id in superseded:
            notes.append(f"superseded:{observation_id}:by:{superseded[observation_id]}")
            continue
        fact, rejection = _classify(record, as_of_at)
        if rejection:
            notes.append(rejection)
        if fact is not None:
            facts.append(fact)

    def _ref(fact: _Fact) -> ShareObservationRef:
        return ShareObservationRef(
            observation_id=fact.observation_id,
            basis="issued_and_outstanding",
            as_of_date=fact.instant.isoformat(),
            security_class_id=security_id,
            value=_decimal_text(fact.value) if fact.value is not None else None,
            source=Provenance("share_count_observations", generation_id, (), _iso(fact.available_at)),
        )

    def _provenance(support: str, available: datetime | None) -> FamilyProvenance:
        capped = "partial" if support in ("supported", "partial") else support
        return FamilyProvenance(
            family="share_basis",
            input_family="share_count_observations",
            input_schema=binding.schema,
            support=capped,
            compiler_version=COMPILER_VERSION if capped in ("supported", "partial") else None,
            generation_id=generation_id,
            artifact_sha256=binding.artifact_sha256,
            support_limits=SUPPORT_LIMITS if capped in ("supported", "partial") else (),
            as_of=_iso(as_of_at),
            available_at=_iso(available) if available is not None else None,
        )

    receipt = CalculationReceipt.build(
        inputs={"observations": observations.as_record(), "actions": actions.as_record(), "as_of": as_of},
        rule_digest=RULE_DIGEST,
        implementation=IMPLEMENTATION,
        computed_at=_iso(as_of_at),
    )

    def _result(status: str, *, candidates: Sequence[ShareObservationRef] = (), selected: Quantity | None = None,
                corporate_action: CorporateActionBasis | None = None, support: str | None = None,
                available: datetime | None = None) -> ShareBasisResult:
        ordered = sorted({item.observation_id: item for item in candidates}.values(), key=lambda item: (item.as_of_date, item.observation_id))
        reasons = tuple(conflicts + refusals + sorted(set(notes)))
        return ShareBasisResult(
            issuer_id=issuer_id,
            security_class_id=security_id,
            as_of=_iso(as_of_at),
            status=status,
            provenance=_provenance(support or binding.support, available),
            receipt=receipt,
            selected=selected,
            candidates=tuple(ordered),
            conflicts=reasons,
            corporate_action=corporate_action or CorporateActionBasis(),
        )

    if not observations.observations:
        notes.append("share_count_observations_absent")
        return _result("unavailable", support="unavailable")
    if not eligible:
        return _result("unavailable", support="unavailable")

    clean = [fact for fact in facts if fact.clean]
    latest_available = max((fact.available_at for fact in facts), default=None)
    if not clean:
        if not facts:
            refusals.append("refused:no_admissible_common_shares_outstanding_fact")
            return _result("refused", available=latest_available)
        top = max(fact.instant for fact in facts)
        blocked = [fact for fact in facts if fact.instant == top]
        refusals.extend(f"unconfirmed:{fact.observation_id}:{fact.reason}" for fact in blocked)
        return _result("refused", candidates=[_ref(fact) for fact in blocked], available=latest_available)

    instant = max(fact.instant for fact in clean)
    at_instant = [fact for fact in facts if fact.instant == instant]
    candidates = [_ref(fact) for fact in at_instant]
    clean_values = sorted({fact.value for fact in at_instant if fact.clean})  # type: ignore[type-var]
    if len(clean_values) > 1:
        conflicts.append(f"contradicted:{instant.isoformat()}:" + "|".join(_decimal_text(value) for value in clean_values))
    for fact in at_instant:
        if not fact.clean:
            conflicts.append(f"contradicted:{instant.isoformat()}:{fact.observation_id}:{fact.reason}")
    for fact in facts:
        if not fact.clean and fact.instant > instant:
            refusals.append(f"unconfirmed:{fact.observation_id}:{fact.reason}")
            candidates.append(_ref(fact))
        elif not fact.clean and fact.instant < instant:
            notes.append(f"ignored_before_selected_instant:{fact.observation_id}:{fact.reason}")
    age = (as_of_at.date() - instant).days
    if age > MAX_BASIS_AGE_DAYS:
        refusals.append(f"stale:{instant.isoformat()}:{age}d")

    decision = SplitDecision(applied=CorporateActionBasis())
    if action_family == "corporate_actions" and "corporate_actions" in COMPATIBLE_INPUT_SCHEMAS and actions.actions:
        decision = evaluate_split_actions(actions.actions, issuer_id=issuer_id, security_class_id=security_id, count_instant=instant, as_of=as_of_at)
        refusals.extend(decision.refusals)
        notes.extend(decision.notes)
    elif action_family == "events" and actions.actions:
        event_refusals, event_notes = _event_notes(actions.actions, issuer_id=issuer_id, count_instant=instant, as_of=as_of_at)
        refusals.extend(event_refusals)
        notes.extend(event_notes)

    if conflicts:
        if len(candidates) < 2:
            # A single unclean fact cannot make a two-sided conflict; it is a refusal.
            refusals.extend(conflicts)
            conflicts.clear()
            return _result("refused", candidates=candidates, available=latest_available)
        return _result("conflict", candidates=candidates, available=latest_available)
    if refusals:
        return _result("refused", candidates=candidates, available=latest_available)

    chosen = sorted((fact for fact in at_instant if fact.clean), key=lambda fact: fact.observation_id)[0]
    assert chosen.value is not None
    value = chosen.value
    quantity_note = f"selected:{instant.isoformat()}:{chosen.observation_id}"
    if decision.applied.kind != "none":
        assert decision.numerator is not None and decision.denominator is not None and decision.action_id is not None
        scaled = Fraction(chosen.value) * Fraction(decision.numerator, decision.denominator)
        if scaled.denominator != 1:
            refusals.append(f"unconfirmed:fractional_share_treatment_unknown:{decision.action_id}")
            return _result("refused", candidates=candidates, available=latest_available)
        value = Decimal(scaled.numerator)
        derived = ShareObservationRef(
            observation_id=stable_id("split_adjusted", {"observation_id": chosen.observation_id, "action_id": decision.action_id}),
            basis="issued_and_outstanding",
            as_of_date=str(decision.applied.effective_date),
            security_class_id=security_id,
            value=_decimal_text(value),
            source=Provenance("corporate_actions", actions.binding.generation_id, decision.evidence, decision.available_at),
        )
        candidates.append(derived)
        notes.append(f"split_scaled:{decision.action_id}:fractional_share_treatment_not_modeled")
        quantity_note = f"split_adjusted:{decision.action_id}:{chosen.observation_id}"
    known_at = chosen.available_at
    if decision.available_at is not None:
        known_at = max(known_at, _parse_ts(decision.available_at) or known_at)
    selected = Quantity.known(
        _decimal_text(value),
        "shares",
        share_basis="issued_and_outstanding",
        security_class_id=security_id,
        provenance=Provenance("share_count_observations", generation_id, (), _iso(known_at)),
        note=quantity_note,
    )
    return _result("selected", candidates=candidates, selected=selected, corporate_action=decision.applied, available=latest_available)


__all__ = [
    "ADMISSION_CONFIG",
    "COMPILER_VERSION",
    "IMPLEMENTATION",
    "MAX_BASIS_AGE_DAYS",
    "RULES",
    "RULE_DIGEST",
    "SPLIT_STAGES",
    "SUPPORT_LIMITS",
    "ShareBasisInputError",
    "SplitDecision",
    "evaluate_split_actions",
    "security_class_id_for",
    "select_share_basis",
]
