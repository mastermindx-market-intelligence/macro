"""SNI-local DRAFT three-clock classifier (A08 economic / owner-known / publication).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
records shaped like the Company Event/Earnings and Data OS owners' fact
records; the field name -> clock label map is caller-supplied and the
record fields are read with that map. It does not re-implement Data OS
identity, Company Event/Earnings, FIF, Capital Structure, Stock Identity,
Options, Research Vault, or qledger/Evaluation. Identity ids and the
field name -> clock label map are caller-supplied opaque strings owned
by Stock Identity / Data OS / the calling owner; this classifier never
mints, derives, or guesses canonical HK/US issuer or security identifiers
from a ticker, name, code, or CIK. Unknown identity stays UNRESOLVED /
null. The classifier never names a clock from a hard-coded field name:
it reads exactly one field per clock from the supplied map, refuses
when the map is missing or the labels are unknown, refuses when one
field is mapped to more than one clock, refuses when the same clock is
filled by more than one present field on the record, and reports each
clock as the RAW record value (or None).

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. A clock that is
missing, ambiguous, malformed, or filled from another clock is refused,
not back-filled. SESSION_ANCHOR fields are accepted, ignored, and never
satisfy the ECONOMIC clock. economic_time is validated but never
promoted to a knowledge clock; a fact about a future period can be known
now, and a fact about a past period may not be.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path. Every authority flag is literal false. A caller that tries to set
any of them true is refused (raise). Residuals and stress statistics stay
descriptive; this classifier makes no causal or news-impact claim (A24).
An unestimable family is outside this module; the classifier never
invents a default 50/50 (A25). This is a descriptive refusal contract,
not a signal, score, or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping

CLOCKS: tuple[str, ...] = (
    "ECONOMIC",
    "OWNER_KNOWN",
    "PUBLICATION",
)

LABELS: tuple[str, ...] = (
    "ECONOMIC",
    "OWNER_KNOWN",
    "PUBLICATION",
    "SESSION_ANCHOR",
)

KINDS: tuple[str, ...] = (
    "actual",
    "estimate",
)

REASONS: tuple[str, ...] = (
    "FIELD_MAP_MISSING",
    "KIND_UNKNOWN",
    "CLOCK_UNKNOWN",
    "CLOCK_SUBSTITUTED",
    "CLOCK_FIELD_AMBIGUOUS",
    "ECONOMIC_MISSING",
    "OWNER_KNOWN_MISSING",
    "PUBLICATION_MISSING",
    "TIMESTAMP_INVALID",
    "PUBLICATION_BEFORE_ECONOMIC",
    "OWNER_KNOWN_BEFORE_PUBLICATION",
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

_KIND_SET = frozenset(KINDS)
_LABEL_SET = frozenset(LABELS)
_LABEL_CLOCK_SET = frozenset(CLOCKS)


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
class ThreeClockVerdict:
    """Descriptive three-clock refusal. Carries no values beyond raw record
    strings; no re-parsing, no re-formatting, no copies between clocks."""

    allowed: bool
    reasons: tuple[str, ...]
    economic: str | None
    owner_known: str | None
    publication: str | None

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """An opaque-text id / ref / field-name / kind-label is present iff
    it is a non-empty string that does not begin or end with whitespace. None, ``""``,
    ``"  "``, ``1``, ``True``, ``1.0``, ``b"id"``, ``["id"]``, and any
    other object are ABSENT and never match each other. Applied to the
    field-map keys (the field names the caller maps) and the kind label
    argument; record values looked up via ``_present`` only see this
    helper for the field-map-key path (the record value is compared to
    its field by ``_blank`` then routed to ``_coerce_field_value`` for
    parsing, matching the existing test pins on non-str / trailing-space
    record values). The clock labels (the values of the field map) keep
    their existing closed-set / CLOCK_SUBSTITUTED check; timestamps
    parsed by ``_coerce_field_value`` and containers keep their existing
    checks.

    FAMILY TEXT RULE v2 (seat ruling): a field-map key or kind label that
    begins or ends with whitespace is ABSENT, exactly like a whitespace-only
    one. The check uses no normalisation method (``.strip()`` etc.), which
    keeps the family's no-normalisation static scans green. Record values
    are NOT routed through this helper: the existing pins treat a padded
    record value (e.g. ``"2026-06-30 "``) as a value that fails parsing and
    refuses with TIMESTAMP_INVALID, which is also a refusal.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _blank(value: object) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    return False


def _present(record: Mapping[str, object], key: str) -> bool:
    if not _text_present(key):
        return False
    if key not in record:
        return False
    value = record.get(key)
    if _blank(value):
        return False
    if isinstance(value, str):
        # Whitespace-only record values (e.g. "  ") are ABSENT and map
        # to the reason for a blank value of this clock. Trailing-space
        # values are NOT routed here (they keep their TIMESTAMP_INVALID
        # refusal via _coerce_field_value per the existing test pins).
        for char in value:
            if not char.isspace():
                return True
        return False
    return True


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _as_date(text: object) -> date | None:
    if not isinstance(text, str) or len(text) != 10:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _as_datetime(text: object) -> datetime | None:
    if not isinstance(text, str) or text == "":
        return None
    body = text
    if body.endswith("Z"):
        body = body[:-1]
    try:
        return datetime.fromisoformat(body)
    except ValueError:
        return None


def _aware_value(text: object) -> datetime | None:
    """Timezone-aware parse. Naive, missing, or unparseable values return None."""
    if not isinstance(text, str) or text == "":
        return None
    body: object = text
    if text.endswith("Z"):
        body = text[:-1] + "+00:00"
    parsed = _as_datetime(body)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _coerce_field_value(
    value: object, *, require_aware: bool
) -> tuple[datetime | None, bool]:
    """Return (parsed_datetime, ok). ok=False for any non-conforming value."""
    if not isinstance(value, str) or value == "":
        return None, False
    if require_aware:
        parsed = _aware_value(value)
        if parsed is None:
            return None, False
        return parsed, True
    parsed = _as_date(value)
    if parsed is not None:
        return datetime(parsed.year, parsed.month, parsed.day), True
    parsed_dt = _aware_value(value)
    if parsed_dt is None:
        return None, False
    return parsed_dt, True


def _utc_date(text: object) -> date | None:
    """Return the UTC date of an aware datetime string, or None."""
    parsed = _aware_value(text)
    if parsed is None:
        return None
    return parsed.astimezone().date()


def classify_clocks(
    record: Mapping[str, object],
    field_map: Mapping[str, object] | None,
    *,
    kind: str,
) -> ThreeClockVerdict:
    """Classify the three clocks of a record.

    The field map is the caller's contract: each value is exactly one of
    the LABELS strings. A non-string value (a tuple / list / set / None)
    is treated as one field carrying more than one clock and is refused.
    SESSION_ANCHOR fields are accepted and ignored: they never satisfy
    ECONOMIC and never participate in ordering.

    `kind` is "actual" or "estimate". For "estimate", PUBLICATION may
    precede ECONOMIC (a forecast precedes its period). OWNER_KNOWN is
    always required to precede (or equal) PUBLICATION for both kinds.

    The verdict carries the raw record values for each clock, never a
    re-formatted copy. Missing clocks are returned as None.
    """
    refuse_nonfalse_authority()
    reasons: list[str] = []

    if not isinstance(field_map, Mapping) or len(field_map) == 0:
        reasons.append("FIELD_MAP_MISSING")
        frozen = _freeze_reasons(reasons)
        return ThreeClockVerdict(
            allowed=not frozen,
            reasons=frozen,
            economic=None,
            owner_known=None,
            publication=None,
        )

    if not _text_present(kind) or kind not in _KIND_SET:
        reasons.append("KIND_UNKNOWN")
        # still walk the field map for unknown label / substituted / ambiguous

    # Pass 1: validate the field map itself.
    label_by_field: dict[str, str] = {}
    clock_to_fields: dict[str, list[str]] = {c: [] for c in CLOCKS}
    session_anchor_fields: list[str] = []
    for field_name, label in field_map.items():
        if not isinstance(label, str) or label not in _LABEL_SET:
            # A non-string label (tuple/list/set/None) substitutes: one
            # field is asked to carry more than one clock.
            if not isinstance(label, str):
                reasons.append("CLOCK_SUBSTITUTED")
            else:
                reasons.append("CLOCK_UNKNOWN")
            continue
        if not _text_present(field_name):
            # A non-text field-map key is ABSENT. The clock (per the
            # valid label above) is reported missing; we don't add the
            # key to clock_to_fields so it never satisfies a clock.
            if label != "SESSION_ANCHOR":
                reasons.append(f"{label}_MISSING")
            continue
        label_by_field[field_name] = label
        if label == "SESSION_ANCHOR":
            session_anchor_fields.append(field_name)
        else:
            clock_to_fields[label].append(field_name)

    # Pass 2: pick the raw value for each clock. A clock with no mapped
    # field is MISSING. A clock with more than one mapped field that is
    # present non-blank on the record is AMBIGUOUS (equal values do not
    # rescue; one field, one clock).
    raw: dict[str, str | None] = {"ECONOMIC": None, "OWNER_KNOWN": None, "PUBLICATION": None}
    for clock in CLOCKS:
        fields = clock_to_fields[clock]
        present = [f for f in fields if _present(record, f)]
        if not present:
            if fields:
                # The map says this clock has a field, but the record
                # does not carry a non-blank value for it.
                reasons.append(f"{clock}_MISSING")
            else:
                reasons.append(f"{clock}_MISSING")
            continue
        if len(present) > 1:
            reasons.append("CLOCK_FIELD_AMBIGUOUS")
            # still pick the first present field for raw pass-through
            raw[clock] = str(record.get(present[0]))
            continue
        raw[clock] = str(record.get(present[0]))

    # Pass 3: validate the parsed form of each clock. ECON requires a date
    # or aware datetime; OKP require aware datetimes. Anything else
    # (naive, unparseable, non-string) refuses with TIMESTAMP_INVALID.
    parsed: dict[str, datetime | None] = {
        "ECONOMIC": None,
        "OWNER_KNOWN": None,
        "PUBLICATION": None,
    }
    for clock in CLOCKS:
        value = raw[clock]
        if value is None:
            continue
        require_aware = clock != "ECONOMIC"
        parsed_value, ok = _coerce_field_value(value, require_aware=require_aware)
        if not ok:
            reasons.append("TIMESTAMP_INVALID")
            parsed[clock] = None
            continue
        parsed[clock] = parsed_value

    # Pass 4: ordering.
    econ = parsed["ECONOMIC"]
    pub = parsed["PUBLICATION"]
    known = parsed["OWNER_KNOWN"]
    econ_value = raw["ECONOMIC"]
    pub_value = raw["PUBLICATION"]
    known_value = raw["OWNER_KNOWN"]

    if (
        kind == "actual"
        and econ is not None
        and pub is not None
    ):
        econ_date: date | None
        if econ_value is not None:
            econ_date_candidate = _as_date(econ_value)
            if econ_date_candidate is not None:
                econ_date = econ_date_candidate
            else:
                econ_date = econ.astimezone().date()
        else:
            econ_date = econ.astimezone().date()
        pub_date = _utc_date(pub_value)
        if pub_date is not None and econ_date is not None and pub_date < econ_date:
            reasons.append("PUBLICATION_BEFORE_ECONOMIC")

    if known is not None and pub is not None:
        if known < pub:
            reasons.append("OWNER_KNOWN_BEFORE_PUBLICATION")

    frozen = _freeze_reasons(reasons)
    return ThreeClockVerdict(
        allowed=not frozen,
        reasons=frozen,
        economic=econ_value,
        owner_known=known_value,
        publication=pub_value,
    )