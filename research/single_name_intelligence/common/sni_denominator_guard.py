"""SNI-local DRAFT denominator-guard contract (A11 share-count binding).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
Capital Structure share-count observations (schema
capital_structure.share_count_observation.v1). It does not re-implement
Data OS identity, Company Event/Earnings, FIF, Capital Structure,
Stock Identity, Options, Research Vault, or qledger/Evaluation. Identity
ids are caller-supplied opaque strings owned by Stock Identity / Data OS;
this guard never mints, derives, or guesses canonical HK/US issuer or
security identifiers from a ticker, name, code, or CIK, and it never
mints, derives, guesses, fetches, selects, or estimates a share count or
ADS ratio. Unknown identity stays UNRESOLVED / null. Whether a counter is
ADS is a caller-supplied field (`counter_kind`); it is never inferred
from a ticker, code, exchange, or name.

DRAFT, not wired into any owner or pipeline. It does not fetch, store,
normalise, convert, or repair anything. A missing or unbound denominator
is refused, not filled in.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Every authority flag is literal false. A caller that tries to set any of
them true is refused (raise). Residuals and stress statistics stay
descriptive; this guard makes no causal or news-impact claim (A24). An
unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a signal
or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from types import MappingProxyType
from typing import Mapping

OWNER_SCHEMA = "capital_structure.share_count_observation.v1"

REASONS: tuple[str, ...] = (
    "SHARE_COUNT_MISSING",
    "OWNER_SCHEMA_MISMATCH",
    "OWNER_REF_MISSING",
    "CORRECTION_VERSION_MISSING",
    "CORRECTION_VERSION_MISMATCH",
    "NOT_AVAILABLE_AS_OF",
    "OWNER_AUTHORITY_NONFALSE",
    "OWNER_DISPOSITION_NOT_ACCEPTED",
    "ISSUER_MISMATCH",
    "ADS_RATIO_MISSING",
    "ADS_RATIO_UNSOURCED",
    "ADS_RATIO_NONPOSITIVE",
    "COUNTER_KIND_UNKNOWN",
)

COUNTER_KINDS: tuple[str, ...] = (
    "ordinary",
    "ads",
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

_COUNTER_KIND_SET = frozenset(COUNTER_KINDS)


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
class DenominatorVerdict:
    """Descriptive denominator refusal. Carries no share count or ratio value."""

    allowed: bool
    reasons: tuple[str, ...]
    owner_observation_id: str | None
    correction_version: int | None

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """A field documented as an id, ref, code, label, owner reference or
    other opaque text counts as present ONLY when ``_text_present`` is True.

    The seat's FAMILY TEXT RULE — rejects ``None``, empty string, whitespace-only,
    leading/trailing whitespace, and non-str (int, float, bool, bytes, list,
    dict, set, etc.). Equality between two caller-supplied ids is evaluated
    only after both sides pass ``_text_present``; a non-text side is ABSENT
    (its *_MISSING-style reason) and never equals anything.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _blank(value: object) -> bool:
    """Legacy blank-check used for the numeric ``ads_ratio`` slot only.

    Fields documented as ids / refs / codes / labels route through
    ``_text_present`` instead, per the seat's FAMILY TEXT RULE.
    """
    if value is None:
        return True
    if value == "":
        return True
    return False


def _present(fact: Mapping[str, object], key: str) -> bool:
    return _text_present(fact.get(key))


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


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


def _aware_datetime(text: object) -> datetime | None:
    """Timezone-aware parse. Naive values, including date-only, refuse."""
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


def _nested(body: object, *keys: str) -> object:
    current: object = body
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _correction_version_value(value: object) -> int | None:
    # bool is a subclass of int; a correction version must be a real int ≥ 1.
    if type(value) is not int:
        return None
    if value < 1:
        return None
    return value


def _finite_positive(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value > 0
    if isinstance(value, float):
        if not isfinite(value):
            return False
        return value > 0
    return False


def _owner_authority_nonfalse(observation: Mapping) -> bool:
    auth = observation.get("authority")
    if not isinstance(auth, Mapping):
        return True
    if auth.get("is_context_only") is not True:
        return True
    for key, value in auth.items():
        if key == "is_context_only":
            continue
        if value is not False:
            return True
    return False


def _available_as_of(observation: Mapping, as_of: object) -> bool:
    available_at = _nested(observation, "point_in_time", "available_at")
    left = _aware_datetime(available_at)
    right = _aware_datetime(as_of)
    if left is None or right is None:
        return False
    return left <= right


def _add_counter_and_ads(reasons: list[str], request: Mapping) -> None:
    counter_kind = request.get("counter_kind")
    ads_ratio = request.get("ads_ratio")
    ads_ratio_source = request.get("ads_ratio_source")
    if not isinstance(counter_kind, str) or counter_kind not in _COUNTER_KIND_SET:
        reasons.append("COUNTER_KIND_UNKNOWN")
        return
    if counter_kind == "ads":
        if _blank(ads_ratio):
            reasons.append("ADS_RATIO_MISSING")
        if not _text_present(ads_ratio_source):
            reasons.append("ADS_RATIO_UNSOURCED")
        if (not _blank(ads_ratio)) and (not _finite_positive(ads_ratio)):
            reasons.append("ADS_RATIO_NONPOSITIVE")
        return
    if ads_ratio is not None:
        if not _text_present(ads_ratio_source):
            reasons.append("ADS_RATIO_UNSOURCED")
        elif not _finite_positive(ads_ratio):
            reasons.append("ADS_RATIO_NONPOSITIVE")


def _verdict(
    reasons: list[str],
    owner_observation_id: str | None,
    correction_version: int | None,
) -> DenominatorVerdict:
    frozen = _freeze_reasons(reasons)
    return DenominatorVerdict(
        allowed=not frozen,
        reasons=frozen,
        owner_observation_id=owner_observation_id,
        correction_version=correction_version,
    )


def check_denominator(
    request: Mapping,
    observation: Mapping | None,
    *,
    as_of: str,
    expected_correction_version: int | None = None,
    accepted_dispositions: tuple[str, ...] = ("accepted",),
) -> DenominatorVerdict:
    """Refuse a per-share computation unless its share count is bound to an
    owner-issued Capital Structure observation (and, for ADS counters, a
    declared sourced ADS ratio).

    Reports every applicable reason, de-duplicated, in REASONS order.
    When observation is None only SHARE_COUNT_MISSING plus request-only
    reasons (blank issuer, unknown counter kind, ADS_*) are emitted.
    """
    refuse_nonfalse_authority()
    if not isinstance(request, Mapping):
        raise TypeError("request must be a Mapping")
    if observation is not None and not isinstance(observation, Mapping):
        raise TypeError("observation must be a Mapping or None")

    reasons: list[str] = []
    share_ref_present = _present(request, "share_count_ref")
    if observation is None or not share_ref_present:
        reasons.append("SHARE_COUNT_MISSING")

    if observation is None:
        if not _text_present(request.get("issuer_id")):
            reasons.append("ISSUER_MISMATCH")
        _add_counter_and_ads(reasons, request)
        return _verdict(reasons, None, None)

    if observation.get("schema") != OWNER_SCHEMA:
        reasons.append("OWNER_SCHEMA_MISMATCH")

    obs_id = observation.get("observation_id")
    share_count_ref = request.get("share_count_ref")
    if (
        not _text_present(obs_id)
        or not _text_present(share_count_ref)
        or obs_id != share_count_ref
    ):
        reasons.append("OWNER_REF_MISSING")

    cv = _correction_version_value(_nested(observation, "version", "correction_version"))
    if cv is None:
        reasons.append("CORRECTION_VERSION_MISSING")
    elif (
        expected_correction_version is not None
        and cv != expected_correction_version
    ):
        reasons.append("CORRECTION_VERSION_MISMATCH")

    if not _available_as_of(observation, as_of):
        reasons.append("NOT_AVAILABLE_AS_OF")

    if _owner_authority_nonfalse(observation):
        reasons.append("OWNER_AUTHORITY_NONFALSE")

    disposition = _nested(observation, "state", "disposition")
    if disposition not in accepted_dispositions:
        reasons.append("OWNER_DISPOSITION_NOT_ACCEPTED")

    issuer_id = request.get("issuer_id")
    obs_issuer = observation.get("issuer_id")
    if (
        not _text_present(issuer_id)
        or not _text_present(obs_issuer)
        or issuer_id != obs_issuer
    ):
        reasons.append("ISSUER_MISMATCH")

    _add_counter_and_ads(reasons, request)

    owner_id: str | None
    if _text_present(obs_id):
        owner_id = obs_id
    else:
        owner_id = None
    return _verdict(reasons, owner_id, cv)