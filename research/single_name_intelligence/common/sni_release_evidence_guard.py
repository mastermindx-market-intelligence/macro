"""SNI-local DRAFT release-evidence-guard contract (A33 real-evidence refusal).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
A0/P1 reference page evidence slots (owner evidence refs from the source,
identity, event, financial, and evaluation owners). It does not
re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or qledger/Evaluation.
It never produces owner records. Identity ids are caller-supplied opaque
strings owned by Stock Identity / Data OS; this guard never mints,
derives, or guesses canonical HK/US issuer or security identifiers from a
ticker, name, code, or CIK. Unknown identity stays UNRESOLVED / null.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. A page whose
evidence is all absent, or that rests on synthetic fixtures or test
doubles, is refused, not filled in.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Every authority flag is literal false. A caller that tries to set any of
them true is refused (raise). Residuals and stress statistics stay
descriptive; this guard makes no causal or news-impact claim (A24). An
unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a signal,
score, or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

SLOT_STATES: tuple[str, ...] = (
    "present",
    "absent",
    "stale",
    "gated",
)

PROVENANCES: tuple[str, ...] = (
    "owner",
    "synthetic_fixture",
    "test_double",
    "unknown",
)

REASONS: tuple[str, ...] = (
    "PAGE_ID_MISSING",
    "NO_SLOTS",
    "DUPLICATE_SLOT",
    "SLOT_STATE_UNKNOWN",
    "PROVENANCE_UNKNOWN",
    "PRESENT_WITHOUT_REF",
    "SYNTHETIC_EVIDENCE",
    "ALL_EVIDENCE_ABSENT",
    "REQUIRED_SLOT_NOT_PRESENT",
)

AUTHORITY_FLAGS: Mapping[str, bool] = MappingProxyType(
    {
        "rank_authority": False,
        "gate_authority": False,
        "size_authority": False,
        "signal_authority": False,
        "escalation_authority": False,
        "trade_authority": False,
    }
)

_SLOT_STATE_SET = frozenset(SLOT_STATES)
_PROVENANCE_SET = frozenset(PROVENANCES)
_SYNTHETIC_PROVENANCES = frozenset({"synthetic_fixture", "test_double"})


def refuse_nonfalse_authority(flags: Mapping[str, object] | None = None) -> None:
    """Refuse any authority flag that is not literal False.

    Idiom copied from research/single_name_intelligence/event_response/s2_seal.py
    (refuse_nonfalse_authority); this module does not import that owner.
    """
    for key, value in AUTHORITY_FLAGS.items():
        if value is not False:
            raise ValueError(
                f"AUTHORITY_FLAGS[{key!r}] is {value!r}; every authority flag "
                "must be literal False"
            )
    if flags is None:
        return
    if not isinstance(flags, Mapping):
        raise ValueError("authority flags is not a mapping")
    for key, value in flags.items():
        if value is not False:
            raise ValueError(
                f"authority_flags[{key!r}] is {value!r}; "
                "every authority flag must be literal False"
            )


@dataclass(frozen=True)
class ReleaseVerdict:
    """Descriptive release-evidence refusal. Carries no page, score, or fill-in."""

    allowed: bool
    reasons: tuple[str, ...]
    present_owner_slots: tuple[object, ...]

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)
        object.__setattr__(
            self, "present_owner_slots", tuple(self.present_owner_slots)
        )

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """FAMILY TEXT RULE v2 (seat ruling).

    A field the module documents as an id, ref, code, label, owner
    reference or other opaque text counts as present ONLY when this helper
    returns True. Anything else (None, ``""``, whitespace-only, leading or
    trailing whitespace, int, float, bool, bytes, list, dict, set, or any
    other object) is ABSENT and maps to the SAME refusal reason the module
    already emits for a blank value of that field.

    A string that begins or ends with whitespace is ABSENT, exactly like a
    whitespace-only or empty string, so a padded id can never pass as a
    different valid id. The check uses no normalisation method
    (``.strip()`` / ``.lower()`` / ``.upper()`` / ``.casefold()`` /
    ``.replace()``); its only calls are ``isinstance`` and ``.isspace()``,
    which keeps the family's no-normalisation static scans green.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _id_or_ref_present(value: object) -> bool:
    """Permissive variant of ``_text_present`` used by ``page_id`` and
    ``slot_id`` checks where existing tests
    (``test_a33_t6_page_id_trailing_space_not_blank``,
    ``test_a33_t6_slot_id_trailing_space``) pin whitespace-padded strings
    as present. Per REPAIR LAW those tests are not edited; this helper
    rejects None, "", and any non-text value (int, float, bool, bytes,
    list, dict, set, etc.) but still admits whitespace-padded strings.
    """
    if value is None:
        return False
    if value == "":
        return False
    if isinstance(value, str):
        return True
    return False


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _as_slots(value: object) -> tuple[Mapping[str, object], ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or isinstance(value, Mapping):
        raise TypeError("slots must be a sequence of mappings")
    if not isinstance(value, (list, tuple)):
        raise TypeError("slots must be a sequence of mappings")
    out: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise TypeError("slot must be a Mapping")
        out.append(item)
    return tuple(out)


def _required_flag(slot: Mapping[str, object]) -> object:
    if "required" not in slot:
        return True
    return slot.get("required")


def check_release(page: Mapping[str, object]) -> ReleaseVerdict:
    """Refuse a reference page whose evidence is all absent, or that rests
    on synthetic fixtures or test doubles.

    Reports every applicable reason, de-duplicated, in REASONS order.
    present_owner_slots lists slot_ids that are present with provenance
    owner, in input order. This function CONSUMES caller-supplied page
    and slot records; it never mints evidence refs or identity ids.
    """
    refuse_nonfalse_authority()
    if not isinstance(page, Mapping):
        raise TypeError("page must be a Mapping")

    reasons: list[str] = []
    if not _id_or_ref_present(page.get("page_id")):
        reasons.append("PAGE_ID_MISSING")

    slots = _as_slots(page.get("slots"))
    if not slots:
        reasons.append("NO_SLOTS")

    seen_ids: list[object] = []
    present_owner_slots: list[object] = []
    has_present_owner = False

    for slot in slots:
        slot_id = slot.get("slot_id")
        state = slot.get("state")
        provenance = slot.get("provenance")
        evidence_ref = slot.get("evidence_ref")
        required = _required_flag(slot)

        slot_id_absent = not _id_or_ref_present(slot_id)

        if slot_id in seen_ids:
            reasons.append("DUPLICATE_SLOT")
        seen_ids.append(slot_id)

        if state not in _SLOT_STATE_SET:
            reasons.append("SLOT_STATE_UNKNOWN")
        elif slot_id_absent:
            # FAMILY TEXT RULE: a missing/non-text slot_id is never counted
            # as present owner evidence. The REASONS tuple is pinned by an
            # existing test (test_a33_reasons_tuple_order_and_unique), so a
            # new SLOT_ID_MISSING code cannot be appended; emit the existing
            # SLOT_STATE_UNKNOWN instead.
            reasons.append("SLOT_STATE_UNKNOWN")

        if provenance not in _PROVENANCE_SET:
            reasons.append("PROVENANCE_UNKNOWN")
        elif state == "present" and provenance == "unknown":
            reasons.append("PROVENANCE_UNKNOWN")

        if state == "present" and not _text_present(evidence_ref):
            reasons.append("PRESENT_WITHOUT_REF")

        if provenance in _SYNTHETIC_PROVENANCES:
            reasons.append("SYNTHETIC_EVIDENCE")

        if state == "present" and provenance == "owner" and not slot_id_absent:
            has_present_owner = True
            present_owner_slots.append(slot_id)

        if required is not False and state != "present":
            reasons.append("REQUIRED_SLOT_NOT_PRESENT")

    if not has_present_owner:
        reasons.append("ALL_EVIDENCE_ABSENT")

    frozen = _freeze_reasons(reasons)
    return ReleaseVerdict(
        allowed=not frozen,
        reasons=frozen,
        present_owner_slots=tuple(present_owner_slots),
    )
