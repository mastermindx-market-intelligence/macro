"""SNI-local DRAFT join-guard contract (A09 mismatched-join refusal).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
fact descriptors (identity, period, basis, currency, scale, segment scheme,
share denominator, counter, version). It does not re-implement Data OS identity,
Company Event/Earnings, FIF, Capital Structure, Stock Identity, Options,
Research Vault, or qledger/Evaluation. Identity ids are caller-supplied
opaque strings owned by Stock Identity / Data OS; this guard never
mints, derives, or guesses canonical HK/US issuer or security identifiers
from a ticker, name, code, or CIK. Unknown identity stays UNRESOLVED / null.

DRAFT, not wired into any owner or pipeline. It does not fetch, store,
normalise, convert, or repair anything. There is no FX table and no scale
arithmetic. A mismatch is refused, not fixed.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Every authority flag is literal false. A caller that tries to set any of
them true is refused (raise). Residuals and stress statistics stay
descriptive; this guard makes no causal or news-impact claim (A24). An
unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a signal
or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping

FACT_FIELDS: tuple[str, ...] = (
    "issuer_id",
    "counter_id",
    "level",
    "metric",
    "period_type",
    "period_start",
    "period_end",
    "basis",
    "currency",
    "source_reported_currency",
    "scale",
    "segment",
    "segment_scheme_version",
    "share_denominator",
    "ads_ratio",
    "version",
    "supersedes",
    "known_at",
    "source_owner",
    "value",
)

REASONS: tuple[str, ...] = (
    "SCHEMA_UNKNOWN_FIELD",
    "ISSUER_UNRESOLVED",
    "ISSUER_MISMATCH",
    "LEVEL_UNKNOWN",
    "LEVEL_MISMATCH",
    "COUNTER_UNRESOLVED",
    "COUNTER_MISMATCH",
    "METRIC_UNKNOWN",
    "METRIC_MISMATCH",
    "PERIOD_TYPE_UNKNOWN",
    "PERIOD_TYPE_MISMATCH",
    "PERIOD_END_MISSING",
    "PERIOD_MISMATCH",
    "BASIS_UNKNOWN",
    "BASIS_MISMATCH",
    "CURRENCY_UNKNOWN",
    "CURRENCY_MISMATCH",
    "CURRENCY_LABEL_CONFLICT",
    "SCALE_UNKNOWN",
    "SCALE_MISMATCH",
    "SEGMENT_MISMATCH",
    "SEGMENT_SCHEME_UNKNOWN",
    "SEGMENT_SCHEME_MISMATCH",
    "DENOMINATOR_UNCARRIED",
    "DENOMINATOR_MISMATCH",
    "ADS_RATIO_MISSING",
    "ADS_RATIO_MISMATCH",
    "VERSION_UNKNOWN",
    "VERSION_CONFLICT",
    "VALUE_CONFLICT",
    "TIMESTAMP_INCOHERENT",
    "KNOWN_AT_MISSING",
    "NOT_KNOWN_AS_OF",
    "JOIN_KIND_UNKNOWN",
)

JOIN_KINDS: tuple[str, ...] = (
    "same_fact",
    "ratio",
    "time_series",
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

_FACT_FIELD_SET = frozenset(FACT_FIELDS)
_JOIN_KIND_SET = frozenset(JOIN_KINDS)
_LEVELS = frozenset({"issuer", "security"})
_DIMENSION_MISMATCH = frozenset(
    {
        "ISSUER_MISMATCH",
        "LEVEL_MISMATCH",
        "COUNTER_MISMATCH",
        "METRIC_MISMATCH",
        "PERIOD_TYPE_MISMATCH",
        "PERIOD_MISMATCH",
        "BASIS_MISMATCH",
        "CURRENCY_MISMATCH",
        "SCALE_MISMATCH",
        "SEGMENT_MISMATCH",
        "SEGMENT_SCHEME_MISMATCH",
        "DENOMINATOR_MISMATCH",
        "ADS_RATIO_MISMATCH",
    }
)


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
class JoinVerdict:
    """Descriptive join refusal. Carries no value, converted number, or merge."""

    status: str
    reasons: tuple[str, ...]
    join_kind: str
    authority: Mapping[str, bool] = field(default_factory=lambda: AUTHORITY_FLAGS)

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(self.authority)
        for key in AUTHORITY_FLAGS:
            if self.authority.get(key) is not False:
                raise ValueError(
                    f"authority[{key!r}] is {self.authority.get(key)!r}; "
                    "every authority flag must be literal False"
                )
        object.__setattr__(self, "reasons", tuple(self.reasons))
        if self.status == "ALLOWED":
            if self.reasons:
                raise ValueError("ALLOWED verdict cannot carry reasons")
        elif self.status == "REFUSED":
            if not self.reasons:
                raise ValueError("REFUSED verdict must carry reasons")
        else:
            raise ValueError(
                f"status must be ALLOWED or REFUSED, got {self.status!r}"
            )


def _blank(value: object) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    return False


def _text_present(value: object) -> bool:
    """FAMILY TEXT RULE v2 (seat ruling, repair round 2): a field the
    module documents as an id, ref, code, label, owner reference, or other
    opaque text counts as present ONLY when it is a non-empty str whose
    first and last characters are not whitespace. Anything else -- None,
    empty, whitespace-only, padded (leading/trailing whitespace or
    newline), int, float, bool, bytes, list, dict, set, any other object
    -- is ABSENT and maps to the reason the module already emits for a
    blank value of that field. No new reason codes.

    ``str.isspace`` is the whole whitespace test and is behaviourally
    identical to an argument-free whitespace-removal check for every str:
    both cover exactly the Unicode whitespace characters (including the
    ideographic space U+3000, NBSP, em space, the C0 separators, NEL, and
    the line separator), and a whitespace-only string fails on its first
    character. The no-normalisation AST contract in
    ``tests/test_sni_join_guard.py`` forbids the five normalising
    attribute calls; ``isspace`` is not one of them, so the tight check is
    implemented without ever rewriting the value: a text-present id is
    compared and echoed byte-for-byte, never normalised, trimmed, or
    case-folded.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _text_absent(value: object) -> bool:
    return not _text_present(value)


def _present(fact: Mapping[str, object], key: str) -> bool:
    return not _blank(fact.get(key))


def _freeze_reasons(items: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(items)))


def _as_date(text: object) -> date | None:
    if not isinstance(text, str) or len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _as_datetime(text: object) -> datetime | None:
    if not isinstance(text, str) or text == "":
        return None
    if len(text) == 10:
        parsed = _as_date(text)
        if parsed is None:
            return None
        return datetime(parsed.year, parsed.month, parsed.day)
    body = text
    if body.endswith("Z"):
        body = body[:-1]
    try:
        return datetime.fromisoformat(body)
    except ValueError:
        return None


def _known_at_later_than_as_of(known_at: object, as_of: object) -> bool:
    if not isinstance(known_at, str) or not isinstance(as_of, str):
        return False
    if len(as_of) == 10:
        kd = _as_date(known_at)
        ad = _as_date(as_of)
        if kd is None or ad is None:
            return False
        return kd > ad
    kt = _as_datetime(known_at)
    at = _as_datetime(as_of)
    if kt is None or at is None:
        return False
    return kt > at


def validate_fact(
    fact: Mapping[str, object],
    *,
    as_of: str | None = None,
) -> tuple[str, ...]:
    """Per-fact refusals, sorted and de-duplicated. Unknown is refused."""
    if not isinstance(fact, Mapping):
        raise TypeError("fact must be a Mapping")
    found: list[str] = []
    unknown_keys = [key for key in fact if key not in _FACT_FIELD_SET]
    for key in sorted(unknown_keys, key=str):
        found.append("SCHEMA_UNKNOWN_FIELD:" + str(key))
    level = fact.get("level")
    # isinstance before membership: a frozenset lookup hashes its operand,
    # so an unhashable level (list/dict/set) must refuse, never raise (JGP-01).
    if not isinstance(level, str) or level not in _LEVELS:
        found.append("LEVEL_UNKNOWN")
    if _text_absent(fact.get("issuer_id")):
        found.append("ISSUER_UNRESOLVED")
    if level == "security" and _text_absent(fact.get("counter_id")):
        found.append("COUNTER_UNRESOLVED")
    if _text_absent(fact.get("metric")):
        found.append("METRIC_UNKNOWN")
    if _text_absent(fact.get("period_type")):
        found.append("PERIOD_TYPE_UNKNOWN")
    if _text_absent(fact.get("basis")):
        found.append("BASIS_UNKNOWN")
    if _text_absent(fact.get("currency")):
        found.append("CURRENCY_UNKNOWN")
    if _blank(fact.get("scale")):
        found.append("SCALE_UNKNOWN")
    if _blank(fact.get("period_end")):
        found.append("PERIOD_END_MISSING")
    currency = fact.get("currency")
    reported = fact.get("source_reported_currency")
    if _text_present(currency) and _text_present(reported) and currency != reported:
        found.append("CURRENCY_LABEL_CONFLICT")
    denom = fact.get("share_denominator")
    if _text_absent(denom):
        found.append("DENOMINATOR_UNCARRIED")
    elif denom == "ADS" and _blank(fact.get("ads_ratio")):
        found.append("ADS_RATIO_MISSING")
    if _text_present(fact.get("segment")) and _text_absent(
        fact.get("segment_scheme_version")
    ):
        found.append("SEGMENT_SCHEME_UNKNOWN")
    if _text_absent(fact.get("version")):
        found.append("VERSION_UNKNOWN")
    known_at = fact.get("known_at")
    period_end = fact.get("period_end")
    if (not _blank(known_at)) and (not _blank(period_end)):
        known_day = _as_date(known_at)
        period_day = _as_date(period_end)
        if (
            known_day is not None
            and period_day is not None
            and known_day < period_day
        ):
            found.append("TIMESTAMP_INCOHERENT")
    if as_of is not None:
        if _blank(known_at):
            found.append("KNOWN_AT_MISSING")
        elif _known_at_later_than_as_of(known_at, as_of):
            found.append("NOT_KNOWN_AS_OF")
    return _freeze_reasons(found)


def _add_eq_mismatch(
    reasons: list[str],
    left: Mapping[str, object],
    right: Mapping[str, object],
    key: str,
    code: str,
    *,
    type_strict: bool = False,
    text_strict: bool = False,
) -> None:
    left_value = left.get(key)
    right_value = right.get(key)
    if text_strict:
        if not (_text_present(left_value) and _text_present(right_value)):
            return
    elif not (_present(left, key) and _present(right, key)):
        return
    # X7-08: with type_strict, the type rides along with the value so a bool
    # never equals an int (True == 1 in Python); 0 vs "0" still refuses.
    if type_strict:
        if (type(left_value), left_value) != (type(right_value), right_value):
            reasons.append(code)
    elif left_value != right_value:
        reasons.append(code)


def _add_scheme_version_rule(
    reasons: list[str],
    left: Mapping[str, object],
    right: Mapping[str, object],
) -> None:
    """FAMJ2-02 (fail closed): scheme versions are compared whenever both
    sides carry a non-blank value, on the ratio path and the non-ratio
    path alike (X7-04). A carried side that is not text-present never
    compares equal -- a non-text side is never equal to anything, not even
    to an equal-looking int or bool -- so SEGMENT_SCHEME_MISMATCH is
    emitted instead of the silent pass round 1's text-only gate produced.
    Blank sides (None or empty) still carry no refusal, matching the
    one-sided carries the positive controls pin.
    """
    left_ver = left.get("segment_scheme_version")
    right_ver = right.get("segment_scheme_version")
    if _blank(left_ver) or _blank(right_ver):
        return
    if _text_absent(left_ver) or _text_absent(right_ver):
        reasons.append("SEGMENT_SCHEME_MISMATCH")
        return
    if left_ver != right_ver:
        reasons.append("SEGMENT_SCHEME_MISMATCH")


def _add_segment_rules(
    reasons: list[str],
    left: Mapping[str, object],
    right: Mapping[str, object],
    join_kind: str,
) -> None:
    left_seg = left.get("segment")
    right_seg = right.get("segment")
    left_set = _text_present(left_seg)
    right_set = _text_present(right_seg)
    if join_kind == "ratio":
        if left_set and right_set and left_seg != right_seg:
            reasons.append("SEGMENT_MISMATCH")
        # X7-04: scheme versions are compared whenever both sides carry one,
        # independent of segment presence (matches the non-ratio branch).
        _add_scheme_version_rule(reasons, left, right)
        return
    if left_set or right_set:
        if left_seg != right_seg:
            reasons.append("SEGMENT_MISMATCH")
    _add_scheme_version_rule(reasons, left, right)


def _add_version_rule(
    reasons: list[str],
    left: Mapping[str, object],
    right: Mapping[str, object],
) -> None:
    if any(code in _DIMENSION_MISMATCH for code in reasons):
        return
    left_ver = left.get("version")
    right_ver = right.get("version")
    if _text_absent(left_ver) or _text_absent(right_ver):
        return
    if left_ver == right_ver:
        if left.get("value") != right.get("value"):
            reasons.append("VALUE_CONFLICT")
        return
    left_sup = left.get("supersedes")
    right_sup = right.get("supersedes")
    left_link_ok = _text_present(left_sup) and _text_present(right_ver)
    right_link_ok = _text_present(right_sup) and _text_present(left_ver)
    linked = (left_link_ok and left_sup == right_ver) or (
        right_link_ok and right_sup == left_ver
    )
    if not linked:
        reasons.append("VERSION_CONFLICT")


def check_join(
    left: Mapping[str, object],
    right: Mapping[str, object],
    *,
    join_kind: str,
    as_of: str | None = None,
) -> JoinVerdict:
    """Refuse a join whose identity, period, basis, currency, scale, segment
    scheme, share denominator, counter, or version do not match.

    Reports every reason, sorted and de-duplicated. check_join(a, b) and
    check_join(b, a) yield the same bare reason set after LEFT:/RIGHT: prefixes
    swap.
    """
    reasons: list[str] = []
    for code in validate_fact(left, as_of=as_of):
        reasons.append("LEFT:" + code)
    for code in validate_fact(right, as_of=as_of):
        reasons.append("RIGHT:" + code)
    if not isinstance(join_kind, str) or join_kind not in _JOIN_KIND_SET:
        reasons.append("JOIN_KIND_UNKNOWN")
        frozen = _freeze_reasons(reasons)
        return JoinVerdict(
            status="REFUSED",
            reasons=frozen,
            join_kind=join_kind,
            authority=AUTHORITY_FLAGS,
        )
    _add_eq_mismatch(
        reasons, left, right, "issuer_id", "ISSUER_MISMATCH", text_strict=True
    )
    _add_eq_mismatch(reasons, left, right, "level", "LEVEL_MISMATCH")
    if left.get("level") == "security" and right.get("level") == "security":
        _add_eq_mismatch(
            reasons,
            left,
            right,
            "counter_id",
            "COUNTER_MISMATCH",
            text_strict=True,
        )
    if join_kind != "ratio":
        _add_eq_mismatch(
            reasons, left, right, "metric", "METRIC_MISMATCH", text_strict=True
        )
    _add_eq_mismatch(
        reasons,
        left,
        right,
        "period_type",
        "PERIOD_TYPE_MISMATCH",
        text_strict=True,
    )
    if join_kind != "time_series":
        period_hit = False
        # X7-03: a one-sided period_start (present here, blank there) is a
        # mismatch, not a silent pass; two blank sides stay allowed.
        if _present(left, "period_start") != _present(right, "period_start"):
            period_hit = True
        if (
            _present(left, "period_start")
            and _present(right, "period_start")
            and left.get("period_start") != right.get("period_start")
        ):
            period_hit = True
        if (
            _present(left, "period_end")
            and _present(right, "period_end")
            and left.get("period_end") != right.get("period_end")
        ):
            period_hit = True
        if period_hit:
            reasons.append("PERIOD_MISMATCH")
    _add_eq_mismatch(
        reasons, left, right, "basis", "BASIS_MISMATCH", text_strict=True
    )
    # currency-mismatch rule (mutation proof (a) deletes this block)
    if (
        _text_present(left.get("currency"))
        and _text_present(right.get("currency"))
        and left.get("currency") != right.get("currency")
    ):
        reasons.append("CURRENCY_MISMATCH")
    _add_eq_mismatch(
        reasons, left, right, "scale", "SCALE_MISMATCH", type_strict=True
    )
    _add_segment_rules(reasons, left, right, join_kind)
    _add_eq_mismatch(
        reasons,
        left,
        right,
        "share_denominator",
        "DENOMINATOR_MISMATCH",
        text_strict=True,
    )
    if left.get("share_denominator") == "ADS" and right.get("share_denominator") == "ADS":
        _add_eq_mismatch(reasons, left, right, "ads_ratio", "ADS_RATIO_MISMATCH")
    if join_kind == "same_fact":
        _add_version_rule(reasons, left, right)
    frozen = _freeze_reasons(reasons)
    status = "REFUSED" if frozen else "ALLOWED"
    return JoinVerdict(
        status=status,
        reasons=frozen,
        join_kind=join_kind,
        authority=AUTHORITY_FLAGS,
    )
