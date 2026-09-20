"""FIF-3A4: immutable cutoff-visible cross-filing fact lineage evidence.

Authority: ``DEC:FIF-3A4R-CROSS-FILING-LINEAGE-ACCEPTED-ON-MAIN`` and
``research/financial_intelligence_fabric/FIF_3A4R_CROSS_FILING_LINEAGE_PROTOCOL.md``.

This module is **not** a second fact ledger, a lineage database, a revision
store, or a metric registry.  It mints immutable receipts that assert one
narrow relation — ``xbrl_confirmation`` — between two already-accepted
``FILED`` ``RawFactOccurrence``s in two different SEC accessions, and it
re-proves that relation from live ledger facts at query time.

Frozen laws this module implements:

* A1/A2 occurrences remain ``event_type=FILED``.  Nothing here remints,
  appends, suppresses, or reclassifies an occurrence.
* ``xbrl_confirmation`` is a *lineage relation type* on a receipt.  It is
  deliberately **not** ``FactEventType.XBRL_CONFIRMATION``; that enum member
  stays a reserved conversion-time exclusive type in ``_REVISION_TYPES``.
* A confirmation is lineage evidence, never a reported revision.  It can only
  unify two ``FILED`` vintages into one effective root; it never mints
  ``revision_of``, never increments revision depth, and never reaches
  ``LATEST_RESTATED`` or FIF ``revisions[]``.
* v1 stays **exact**.  ``_duplicates_agree`` is the intra-instance diagnostic
  that separates ``precision_consistent_unconfirmed`` from ``changed_value``;
  it never widens cross-filing confirmation.
* The FIF-3A4R research census JSON is calibration evidence.  It is never
  imported, loaded, or consulted here.  Every receipt in this module is
  derived from source filings and re-proved against the live ledger.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence

from .raw_ledger import (
    FactEventType,
    RawFactOccurrence,
    _canonical_duplicate_representative,
    _duplicates_agree,
    canonical_json,
    decimal_text,
    stable_id,
    utc_text,
)

__all__ = [
    "APPROVED_TAXONOMY_PREFIXES",
    "COMPARISON_BASIS_EXACT",
    "CONFIRMATION_RULE_AVAILABLE_AT",
    "CONFIRMATION_RULE_ID",
    "CONFIRMATION_RULE_VERSION",
    "LINEAGE_EVIDENCE_SCHEMA",
    "LineageEvidenceError",
    "LineageEvidenceReceipt",
    "XBRL_CONFIRMATION_RELATION",
    "confirmation_refusal",
    "derive_confirmation_receipts",
    "evaluate_confirmation",
]


LINEAGE_EVIDENCE_SCHEMA = "fif3a4r.lineage_evidence_receipt/v1"

# The relation vocabulary is lineage, not occurrence event typing.  Sol
# amendment 4: ``xbrl_confirmation`` here is never FactEventType.XBRL_CONFIRMATION.
XBRL_CONFIRMATION_RELATION = "xbrl_confirmation"
NO_RELATION = "no_relation"

CONFIRMATION_RULE_ID = "mmx.fif.xbrl_confirmation"
CONFIRMATION_RULE_VERSION = 1

# Sol amendment 1: the only lawful v1 comparison basis.  Duplicate consistency
# and precision intervals are explicitly not a basis.
COMPARISON_BASIS_EXACT = "exact_parsed_value_and_accuracy_tokens"

# Guard 10: approved standard source taxonomy prefixes after Clark
# canonicalization (``TAXONOMY_NAMESPACE_POLICY`` -> ``us-gaap`` or ``dei``).
APPROVED_TAXONOMY_PREFIXES = frozenset({"us-gaap", "dei"})

# Clock law floor component: the accepted A4R lineage rule did not exist before
# Sol's 2026-08-25 bounded amendment (DEC:FIF-3A4R decided_at 2026-08-25).  The
# 2026-08-24 research freeze and the census timestamp do not authorize runtime
# lineage.
CONFIRMATION_RULE_AVAILABLE_AT = datetime(2026, 8, 25, tzinfo=timezone.utc)

# Bounded materialization: a lineage bundle is small by construction.  A bundle
# that exceeds this is a malformed provider, not a large legitimate answer.
MAX_LINEAGE_RECEIPTS = 20000


class LineageEvidenceError(ValueError):
    """Malformed, non-positive, or mis-bound lineage evidence.

    Deliberately *not* a ``QueryValidationError``: a bad evidence bundle is a
    provider fault, so the transport adapter fail-closes it as a private
    unavailable rather than a client-correctable 400.
    """


# ---------------------------------------------------------------------------
# Refusal vocabulary (mirrors the accepted A4R census classes)
# ---------------------------------------------------------------------------

REFUSAL_EVENT_TYPE_NOT_FILED = "event_type_not_filed"
REFUSAL_SAME_ACCESSION = "same_accession"
REFUSAL_SOURCE_FAMILY_MISMATCH = "source_family_mismatch"
REFUSAL_PARENT_NOT_BEFORE_CHILD = "parent_not_before_child"
REFUSAL_LOGICAL_KEY_MISMATCH = "logical_key_mismatch"
REFUSAL_INCOMPLETE_DIMENSIONAL_SCOPE = "incomplete_dimensional_scope"
REFUSAL_AMBIGUOUS_DUPLICATE_GROUP = "ambiguous_duplicate_group"
REFUSAL_MULTIPLE_POSSIBLE_PARENT = "multiple_possible_parent"
REFUSAL_NIL_CONFIRMATION_UNSPECIFIED = "nil_confirmation_unspecified"
REFUSAL_NIL_STATE_DIFFERENCE = "nil_state_difference"
REFUSAL_CHANGED_VALUE = "changed_value"
REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED = "precision_consistent_unconfirmed"
REFUSAL_CUSTOM_UNMAPPED_TAXONOMY = "custom_unmapped_taxonomy"
REFUSAL_TAXONOMY_NAMESPACE_VERSION_MISMATCH = "source_taxonomy_namespace_version_mismatch"
REFUSAL_UNIT_CONTEXT_CONCEPT_MISMATCH = "unit_context_concept_mismatch"
REFUSAL_MISSING_OCCURRENCE = "missing_occurrence"
REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE = "evidence_does_not_match_source"


def _taxonomy_prefix(concept_qname: str) -> str:
    if ":" not in concept_qname:
        return ""
    return concept_qname.split(":", 1)[0]


def _approved_taxonomy_uri(uri: Any, concept_qname: str) -> bool:
    """Whether an attested original taxonomy URI is a real approved namespace.

    Guard 11 asserts a fact about the *source*, and the canonical ledger does
    not retain the original Clark URI. Equality of two attested strings is
    therefore not enough on its own: two matching but invented URIs would
    satisfy it. Bind the attestation to the repository's own
    ``TAXONOMY_NAMESPACE_POLICY`` instead, and require the prefix that policy
    assigns to the URI to be the prefix the retained ``concept_qname`` already
    carries. An invented namespace is not in the policy, and a real namespace
    that disagrees with the concept is not this fact's taxonomy.
    """
    if not isinstance(uri, str) or not uri:
        return False
    from .filing_attestation import TAXONOMY_NAMESPACE_POLICY  # local: avoid import cycle

    prefix = TAXONOMY_NAMESPACE_POLICY.get(uri)
    if prefix is None or prefix not in APPROVED_TAXONOMY_PREFIXES:
        return False
    return prefix == _taxonomy_prefix(concept_qname)


def _accuracy_tokens(fact: RawFactOccurrence) -> tuple[str | None, str | None]:
    """The exact XBRL accuracy metadata v1 requires to match exactly."""
    return (fact.decimals, fact.precision)


def _exact_decimal(value: Any) -> Decimal | None:
    """Reconstruct a retained canonical parsed value, or refuse it."""
    if value is None or isinstance(value, bool) or isinstance(value, float):
        return None
    if isinstance(value, Decimal):
        return value if value.is_finite() else None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


# ---------------------------------------------------------------------------
# The v1 positive rule (FIF-3A4R protocol §5, Sol 2026-08-25)
# ---------------------------------------------------------------------------


def evaluate_confirmation(
    parent_events: Sequence[RawFactOccurrence],
    child_events: Sequence[RawFactOccurrence],
    *,
    parent_taxonomy_uri: str | None = None,
    child_taxonomy_uri: str | None = None,
    require_taxonomy_uri: bool = True,
) -> str | None:
    """Return ``None`` when the v1 positive rule holds, else a refusal reason.

    ``parent_events``/``child_events`` are all occurrences of one shared
    ``logical_key`` inside one accession each.  Every guard fails closed.

    ``require_taxonomy_uri`` distinguishes the two lawful call sites:

    * **Mint time** (``True``) has the parsed filing packages, so guard 11 —
      exact original source taxonomy namespace/version — is provable from the
      original Clark concept URIs.
    * **Query time** (``False``) sees only the canonical ledger, which retains
      ``us-gaap:Assets`` and not ``{http://fasb.org/us-gaap/2025}Assets``.
      Guard 11 is then carried by the immutable receipt that was minted with
      the URIs, and the caller separately re-proves that the receipt's asserted
      evidence still equals the live facts.  Guards 1-10 and 12 are re-proved
      from the ledger on every query either way.
    """
    if not parent_events or not child_events:
        return REFUSAL_MISSING_OCCURRENCE

    # Guard 1 — FILED -> FILED on every participating occurrence.
    for group in (parent_events, child_events):
        if any(item.event_type is not FactEventType.FILED for item in group):
            return REFUSAL_EVENT_TYPE_NOT_FILED
        # A FILED occurrence with a parent would already be a typed vintage.
        if any(item.revision_of is not None for item in group):
            return REFUSAL_EVENT_TYPE_NOT_FILED

    parent_accessions = {item.source.accession for item in parent_events}
    child_accessions = {item.source.accession for item in child_events}
    if len(parent_accessions) != 1 or len(child_accessions) != 1:
        return REFUSAL_MULTIPLE_POSSIBLE_PARENT

    # Guard 2 — distinct accessions.
    if parent_accessions == child_accessions:
        return REFUSAL_SAME_ACCESSION

    # Guard 3 — same filer/source family.
    families = {(item.source.source, item.source.entity_id) for item in (*parent_events, *child_events)}
    if len(families) != 1:
        return REFUSAL_SOURCE_FAMILY_MISMATCH

    # Guard 5 — same canonical economic logical key.  Also covers concept,
    # context and unit identity, which is why a bare concept match on a
    # different member QName can never reach this point.
    logical_keys = {item.logical_key for item in (*parent_events, *child_events)}
    if len(logical_keys) != 1:
        return REFUSAL_LOGICAL_KEY_MISMATCH

    # Guard 6 — dimensional scope must be known on every participating fact.
    if any(not item.dimensions_known for item in (*parent_events, *child_events)):
        return REFUSAL_INCOMPLETE_DIMENSIONAL_SCOPE

    # Guard 7 — duplicate groups are individually adjudicated with the existing
    # within-document collapse, and each filing must reduce to exactly one
    # representative.  Two irreconcilable groups on one side is not a parent.
    for group in (parent_events, child_events):
        if len({item.duplicate_group_key for item in group}) != 1:
            return REFUSAL_AMBIGUOUS_DUPLICATE_GROUP
        if not _duplicates_agree(group):
            return REFUSAL_AMBIGUOUS_DUPLICATE_GROUP

    parent = _canonical_duplicate_representative(parent_events)
    child = _canonical_duplicate_representative(child_events)

    # Guard 4 — parent accepted strictly before child.
    if parent.accepted_at is None or child.accepted_at is None:
        return REFUSAL_PARENT_NOT_BEFORE_CHILD
    if not parent.accepted_at < child.accepted_at:
        return REFUSAL_PARENT_NOT_BEFORE_CHILD

    # Guard 12 — nil is outside v1.  Sol amendment 3: no nil-confirmation
    # contract exists, so a nil/nil pair is refused rather than confirmed.
    if parent.is_nil != child.is_nil:
        return REFUSAL_NIL_STATE_DIFFERENCE
    if parent.is_nil:
        return REFUSAL_NIL_CONFIRMATION_UNSPECIFIED

    # Guard 10 — approved standard source taxonomy.
    if _taxonomy_prefix(parent.concept_qname) not in APPROVED_TAXONOMY_PREFIXES:
        return REFUSAL_CUSTOM_UNMAPPED_TAXONOMY
    if parent.concept_qname != child.concept_qname:
        return REFUSAL_UNIT_CONTEXT_CONCEPT_MISMATCH

    # Guard 8 — exact parsed numeric value.  Decimal equality, never an
    # overlapping rounding interval.  ``RawFactOccurrence`` retains
    # ``parsed_value`` as canonical non-exponent decimal *text*, so compare the
    # reconstructed Decimals rather than the strings: equality must be
    # numeric, and a value that will not reconstruct is not a proven equality.
    parent_value = _exact_decimal(parent.parsed_value)
    child_value = _exact_decimal(child.parsed_value)
    if parent_value is None or child_value is None:
        return REFUSAL_CHANGED_VALUE
    if parent_value != child_value:
        # Sol amendment 1: an intra-instance ``_duplicates_agree`` overlap does
        # not rescue a cross-filing inequality.  Classify it honestly so the
        # 90,678M/90,700M case stays visible as precision-consistent, and the
        # 83,727M/72,634M case stays a changed value.
        if _duplicates_agree((parent, child)):
            return REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED
        return REFUSAL_CHANGED_VALUE

    # Guard 9 — exact accuracy tokens.  Equal values reported at different
    # decimals are not the same assertion about accuracy.
    if _accuracy_tokens(parent) != _accuracy_tokens(child):
        return REFUSAL_PRECISION_CONSISTENT_UNCONFIRMED

    # Guard 11 — exact original source taxonomy namespace/version. Both sides
    # must carry the same URI, and that URI must be a policy-approved standard
    # namespace whose prefix is the one this concept actually uses.
    if require_taxonomy_uri:
        if not parent_taxonomy_uri or not child_taxonomy_uri:
            return REFUSAL_TAXONOMY_NAMESPACE_VERSION_MISMATCH
        if parent_taxonomy_uri != child_taxonomy_uri:
            return REFUSAL_TAXONOMY_NAMESPACE_VERSION_MISMATCH
        if not _approved_taxonomy_uri(parent_taxonomy_uri, parent.concept_qname):
            return REFUSAL_CUSTOM_UNMAPPED_TAXONOMY
        if not _approved_taxonomy_uri(child_taxonomy_uri, child.concept_qname):
            return REFUSAL_CUSTOM_UNMAPPED_TAXONOMY

    return None


def confirmation_refusal(
    parent_events: Sequence[RawFactOccurrence],
    child_events: Sequence[RawFactOccurrence],
    **kwargs: Any,
) -> str | None:
    """Readable alias for callers that want the refusal reason explicitly."""
    return evaluate_confirmation(parent_events, child_events, **kwargs)


# ---------------------------------------------------------------------------
# The immutable receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineageEvidenceReceipt:
    """One immutable cutoff-visible cross-filing lineage assertion.

    Exactly one of ``positive_evidence`` / ``refusal_reason`` is non-null, per
    protocol §7.  Only *positive* receipts are lawful in a runtime
    ``FinancialQueryDataset.lineage_evidence`` collection; the engine fail-closes
    anything else.
    """

    parent_occurrence_id: str
    child_occurrence_id: str
    logical_key: str
    source_known_at: datetime
    system_available_at: datetime
    positive_evidence: Mapping[str, Any] | None = None
    refusal_reason: str | None = None
    relation_type: str = XBRL_CONFIRMATION_RELATION
    evidence_rule_id: str = CONFIRMATION_RULE_ID
    evidence_rule_version: int = CONFIRMATION_RULE_VERSION
    comparison_basis: str = COMPARISON_BASIS_EXACT
    schema: str = LINEAGE_EVIDENCE_SCHEMA
    receipt_id: str = field(default="", compare=True)
    evidence_digest: str = field(default="", compare=True)

    def __post_init__(self) -> None:
        for name in ("parent_occurrence_id", "child_occurrence_id", "logical_key"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise LineageEvidenceError(f"{name} must be a non-empty string")
        if self.parent_occurrence_id == self.child_occurrence_id:
            raise LineageEvidenceError("a receipt cannot link an occurrence to itself")
        if self.schema != LINEAGE_EVIDENCE_SCHEMA:
            raise LineageEvidenceError("unknown lineage evidence schema")
        if self.relation_type not in (XBRL_CONFIRMATION_RELATION, NO_RELATION):
            raise LineageEvidenceError("unknown lineage relation type")
        if self.comparison_basis != COMPARISON_BASIS_EXACT:
            raise LineageEvidenceError("unknown comparison basis")
        if self.evidence_rule_id != CONFIRMATION_RULE_ID:
            raise LineageEvidenceError("unknown evidence rule id")
        if not isinstance(self.evidence_rule_version, int) or isinstance(
            self.evidence_rule_version, bool
        ):
            raise LineageEvidenceError("evidence_rule_version must be an integer")
        if self.evidence_rule_version < 1:
            raise LineageEvidenceError("evidence_rule_version must be positive")
        for name in ("source_known_at", "system_available_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise LineageEvidenceError(f"{name} must be a timezone-aware datetime")
            object.__setattr__(self, name, value.astimezone(timezone.utc))

        has_positive = self.positive_evidence is not None
        has_refusal = self.refusal_reason is not None
        if has_positive == has_refusal:
            raise LineageEvidenceError(
                "exactly one of positive_evidence or refusal_reason must be non-null"
            )
        if has_positive:
            if self.relation_type != XBRL_CONFIRMATION_RELATION:
                raise LineageEvidenceError("positive evidence requires xbrl_confirmation")
            if not isinstance(self.positive_evidence, Mapping):
                raise LineageEvidenceError("positive_evidence must be a mapping")
            missing = _REQUIRED_EVIDENCE_KEYS - set(self.positive_evidence)
            if missing:
                raise LineageEvidenceError("positive_evidence is missing required keys")
            extra = set(self.positive_evidence) - _REQUIRED_EVIDENCE_KEYS
            if extra:
                # Hostile extra keys are unavailable, matching FIF-3A3 delivery.
                raise LineageEvidenceError("positive_evidence carries unknown keys")
            object.__setattr__(
                self, "positive_evidence", _freeze_evidence(self.positive_evidence)
            )
        else:
            if self.relation_type == XBRL_CONFIRMATION_RELATION:
                raise LineageEvidenceError("a refusal cannot carry the confirmation relation")
            if not isinstance(self.refusal_reason, str) or not self.refusal_reason:
                raise LineageEvidenceError("refusal_reason must be a non-empty string")

        payload = self.canonical_payload()
        digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        expected_receipt_id = stable_id("lineage_receipt", payload)
        if self.evidence_digest and self.evidence_digest != digest:
            raise LineageEvidenceError("evidence_digest does not match the receipt payload")
        if self.receipt_id and self.receipt_id != expected_receipt_id:
            raise LineageEvidenceError("receipt_id does not match the receipt payload")
        object.__setattr__(self, "evidence_digest", digest)
        object.__setattr__(self, "receipt_id", expected_receipt_id)

    @property
    def is_positive_confirmation(self) -> bool:
        return (
            self.relation_type == XBRL_CONFIRMATION_RELATION
            and self.positive_evidence is not None
            and self.refusal_reason is None
        )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "relation_type": self.relation_type,
            "parent_occurrence_id": self.parent_occurrence_id,
            "child_occurrence_id": self.child_occurrence_id,
            "logical_key": self.logical_key,
            "evidence_rule_id": self.evidence_rule_id,
            "evidence_rule_version": self.evidence_rule_version,
            "comparison_basis": self.comparison_basis,
            "source_known_at": utc_text(self.source_known_at),
            "system_available_at": utc_text(self.system_available_at),
            "positive_evidence": (
                dict(sorted(self.positive_evidence.items()))
                if self.positive_evidence is not None
                else None
            ),
            "refusal_reason": self.refusal_reason,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.canonical_payload()
        payload["receipt_id"] = self.receipt_id
        payload["evidence_digest"] = self.evidence_digest
        return payload


_REQUIRED_EVIDENCE_KEYS = frozenset(
    {
        "concept_qname",
        "parent_accession",
        "child_accession",
        "parent_document_id",
        "child_document_id",
        "parent_taxonomy_uri",
        "child_taxonomy_uri",
        "parent_source_occurrence_keys",
        "child_source_occurrence_keys",
        "parsed_value",
        "decimals",
        "precision",
        "dimensions_known",
        "is_nil",
        "parent_accepted_at",
        "child_accepted_at",
        "parent_recorded_at",
        "child_recorded_at",
    }
)


def _freeze_evidence(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (list, tuple)):
            frozen[key] = tuple(value)
        else:
            frozen[key] = value
    from types import MappingProxyType

    return MappingProxyType(dict(sorted(frozen.items())))


# ---------------------------------------------------------------------------
# Minting
# ---------------------------------------------------------------------------


def _positive_evidence_payload(
    parent_group: Sequence[RawFactOccurrence],
    child_group: Sequence[RawFactOccurrence],
    *,
    parent_taxonomy_uri: str | None,
    child_taxonomy_uri: str | None,
) -> dict[str, Any]:
    parent = _canonical_duplicate_representative(parent_group)
    child = _canonical_duplicate_representative(child_group)
    return {
        "concept_qname": parent.concept_qname,
        "parent_accession": parent.source.accession,
        "child_accession": child.source.accession,
        "parent_document_id": parent.source.document_id,
        "child_document_id": child.source.document_id,
        "parent_taxonomy_uri": parent_taxonomy_uri,
        "child_taxonomy_uri": child_taxonomy_uri,
        "parent_source_occurrence_keys": tuple(
            sorted(item.source_occurrence_key or "" for item in parent_group)
        ),
        "child_source_occurrence_keys": tuple(
            sorted(item.source_occurrence_key or "" for item in child_group)
        ),
        "parsed_value": decimal_text(parent.parsed_value),
        "decimals": parent.decimals,
        "precision": parent.precision,
        "dimensions_known": parent.dimensions_known,
        "is_nil": parent.is_nil,
        "parent_accepted_at": utc_text(parent.accepted_at),
        "child_accepted_at": utc_text(child.accepted_at),
        "parent_recorded_at": utc_text(parent.clocks.recorded_at),
        "child_recorded_at": utc_text(child.clocks.recorded_at),
    }


def _system_available_floor(
    parent_group: Sequence[RawFactOccurrence],
    child_group: Sequence[RawFactOccurrence],
) -> datetime:
    """Protocol §8: no earlier than both recorded clocks and the rule clock."""
    clocks = [CONFIRMATION_RULE_AVAILABLE_AT]
    for item in (*parent_group, *child_group):
        clocks.append(item.clocks.recorded_at)
    return max(clocks)


def derive_confirmation_receipts(
    events: Iterable[RawFactOccurrence],
    *,
    system_available_at: datetime,
    original_taxonomy_uris: Mapping[tuple[str, str], str],
) -> tuple[LineageEvidenceReceipt, ...]:
    """Mint every lawful positive ``xbrl_confirmation`` receipt for a ledger.

    The rule is applied to source facts only.  No census, fixture table, or
    per-issuer special case participates.  Refusals are *not* returned: a
    runtime lineage bundle carries accepted positive immutable relations only
    (Sol amendment 6).  Callers that want the refusal taxonomy call
    :func:`evaluate_confirmation` directly.

    ``original_taxonomy_uris`` maps ``(accession, source_occurrence_key)`` to
    the original Clark concept namespace URI, which the canonical ledger does
    not retain.  Guard 11 is unprovable without it, so an absent entry refuses.
    """
    if not isinstance(system_available_at, datetime) or system_available_at.tzinfo is None:
        raise LineageEvidenceError("system_available_at must be a timezone-aware datetime")
    system_available_at = system_available_at.astimezone(timezone.utc)

    # Group every occurrence by (logical_key, accession).  A logical key seen in
    # exactly two accessions is the only shape v1 admits: a third filing would
    # make the parent ambiguous, and protocol §5 guard 7 fails closed there.
    by_key: dict[str, dict[str, list[RawFactOccurrence]]] = {}
    for event in events:
        by_key.setdefault(event.logical_key, {}).setdefault(
            event.source.accession, []
        ).append(event)

    receipts: list[LineageEvidenceReceipt] = []
    for logical_key, by_accession in sorted(by_key.items()):
        if len(by_accession) < 2:
            continue
        if len(by_accession) > 2:
            # More than two filings of one logical key cannot pick a unique
            # parent under v1.  Fail closed rather than chaining.
            continue
        (acc_a, group_a), (acc_b, group_b) = sorted(by_accession.items())
        ordered = _order_parent_child(group_a, group_b)
        if ordered is None:
            continue
        parent_group, child_group = ordered
        parent_rep = _canonical_duplicate_representative(parent_group)
        child_rep = _canonical_duplicate_representative(child_group)
        parent_uri = original_taxonomy_uris.get(
            (parent_rep.source.accession, parent_rep.source_occurrence_key or "")
        )
        child_uri = original_taxonomy_uris.get(
            (child_rep.source.accession, child_rep.source_occurrence_key or "")
        )
        refusal = evaluate_confirmation(
            parent_group,
            child_group,
            parent_taxonomy_uri=parent_uri,
            child_taxonomy_uri=child_uri,
            require_taxonomy_uri=True,
        )
        if refusal is not None:
            continue

        floor = _system_available_floor(parent_group, child_group)
        if system_available_at < floor:
            raise LineageEvidenceError(
                "system_available_at precedes the accepted lineage clock floor"
            )
        source_known_at = max(parent_rep.accepted_at, child_rep.accepted_at)
        receipts.append(
            LineageEvidenceReceipt(
                parent_occurrence_id=parent_rep.occurrence_id,
                child_occurrence_id=child_rep.occurrence_id,
                logical_key=logical_key,
                source_known_at=source_known_at,
                system_available_at=system_available_at,
                positive_evidence=_positive_evidence_payload(
                    parent_group,
                    child_group,
                    parent_taxonomy_uri=parent_uri,
                    child_taxonomy_uri=child_uri,
                ),
            )
        )
    return tuple(
        sorted(receipts, key=lambda item: (item.logical_key, item.receipt_id))
    )


def _order_parent_child(
    group_a: Sequence[RawFactOccurrence],
    group_b: Sequence[RawFactOccurrence],
) -> tuple[Sequence[RawFactOccurrence], Sequence[RawFactOccurrence]] | None:
    """Order two same-logical-key accession groups by acceptance time."""
    accepted_a = {item.accepted_at for item in group_a}
    accepted_b = {item.accepted_at for item in group_b}
    if len(accepted_a) != 1 or len(accepted_b) != 1:
        return None
    a = next(iter(accepted_a))
    b = next(iter(accepted_b))
    if a is None or b is None:
        return None
    if a < b:
        return group_a, group_b
    if b < a:
        return group_b, group_a
    return None
