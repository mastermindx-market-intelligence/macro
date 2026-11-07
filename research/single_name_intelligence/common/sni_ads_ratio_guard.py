"""SNI-local DRAFT ADS-ratio interval-guard contract (A01 depositary ratio).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
Stock Identity / Capital Structure depositary-ratio interval records
(ratio_record_id, issuer_id, ordinary_per_ads, valid_from, valid_to,
source_ref, available_at). It does not re-implement Data OS identity,
Company Event/Earnings, FIF, Capital Structure, Stock Identity, Options,
Research Vault, or qledger/Evaluation. Identity ids are caller-supplied
opaque strings owned by Stock Identity / Data OS; this guard never
mints, derives, or guesses canonical HK/US issuer or security identifiers
from a ticker, name, code, or CIK, and it never mints, derives, guesses,
fetches, selects, or estimates an ADS-to-ordinary ratio. Unknown identity
stays UNRESOLVED / null.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. A missing, unsourced,
non-covering, not-yet-available, or unacknowledged-change ratio is
refused, not filled in.

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
from datetime import date, datetime
from math import isfinite
from types import MappingProxyType
from typing import Mapping

REASONS: tuple[str, ...] = (
    "RATIO_RECORDS_MISSING",
    "RATIO_RECORD_UNSOURCED",
    "RATIO_NONPOSITIVE",
    "INTERVAL_INVALID",
    "INTERVAL_OVERLAP",
    "ISSUER_MISMATCH",
    "DATE_INVALID",
    "NO_INTERVAL_COVERS_DATE",
    "RATIO_NOT_AVAILABLE_AS_OF",
    "RATIO_CHANGE_UNACKNOWLEDGED",
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
class AdsRatioVerdict:
    """Descriptive ADS-ratio refusal. Carries no converted share count."""

    allowed: bool
    reasons: tuple[str, ...]
    ratio_record_id: object | None
    ordinary_per_ads: object | None

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _blank(value: object) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    return False


def _text_present(value: object) -> bool:
    """FAMILY TEXT RULE presence: a non-blank, non-padded, exact str.

    A caller-supplied id, ref, code, label, or owner reference counts as
    present ONLY when this helper returns True. Anything else — None, "",
    whitespace-only, leading/trailing whitespace or a trailing newline, an
    int, a float, a bool, bytes, a list, a dict, a set, or any other
    object — is ABSENT and maps to the same refusal reason the module
    emits for a blank value of that field.
    """
    return isinstance(value, str) and value != "" and not value[0].isspace() and not value[-1].isspace()


def _present(fact: Mapping[str, object], key: str) -> bool:
    return _text_present(fact.get(key))


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _as_date(text: object) -> date | None:
    """Accept ONLY (a) an exact 10-char ``YYYY-MM-DD`` that
    ``date.fromisoformat`` parses, or (b) a string that
    ``datetime.fromisoformat`` parses IN FULL (returns its ``.date()``).
    Anything else — including "2026-08-20garbage", "2026-08-20 extra",
    and any non-str — returns None and flows to the module's existing
    DATE_INVALID / INTERVAL_INVALID handling.
    """
    if not isinstance(text, str) or text == "":
        return None
    if len(text) == 10:
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.date()


def _iso_date(text: object) -> date | None:
    """Exactly a 10-character ISO date (YYYY-MM-DD). Anything else is invalid.

    NOTE: the defect X8C-04 spec asked for ``_iso_date`` to mirror
    ``_as_date`` (accept (a) exact 10-char YYYY-MM-DD OR (b) a string that
    ``datetime.fromisoformat`` parses IN FULL). Pinning tests in
    ``tests/test_sni_ads_ratio_guard.py`` (``test_a01g_reason_date_invalid``)
    require ``on_date="2020-01-15T00:00:00"`` to be refused. To keep every
    existing test passing unedited, the broader (b) path is applied in
    ``_as_date`` only. ``_iso_date`` keeps its narrower 10-char strict
    behaviour; X8C-04 is recorded as a PARTIAL close in GAPS.
    """
    if not isinstance(text, str) or text == "":
        return None
    if len(text) != 10:
        return None
    try:
        return date.fromisoformat(text)
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


def _interval(
    rec: Mapping,
) -> tuple[date | None, date | None, bool]:
    """Return (start, end_or_none, dates_ok). end None means open-ended when ok."""
    start = _iso_date(rec.get("valid_from"))
    raw_to = rec.get("valid_to")
    if raw_to is None:
        return start, None, start is not None
    end = _iso_date(raw_to)
    return start, end, start is not None and end is not None


def _interval_usable(rec: Mapping) -> bool:
    start, end, ok = _interval(rec)
    if not ok or start is None:
        return False
    if end is not None and end <= start:
        return False
    return True


def _intervals_overlap(left: Mapping, right: Mapping) -> bool:
    a0, a1, aok = _interval(left)
    b0, b1, bok = _interval(right)
    if not aok or not bok or a0 is None or b0 is None:
        return False
    a_open = a1 is None
    b_open = b1 is None
    a_starts_before_b_ends = b_open or a0 < b1
    b_starts_before_a_ends = a_open or b0 < a1
    return a_starts_before_b_ends and b_starts_before_a_ends


def _covers_day(rec: Mapping, issuer_id: object, day: date) -> bool:
    if rec.get("issuer_id") != issuer_id:
        return False
    if not _interval_usable(rec):
        return False
    start, end, ok = _interval(rec)
    if not ok or start is None:
        return False
    if start > day:
        return False
    if end is not None and day >= end:
        return False
    return True


def _available_as_of(available_at: object, as_of: object) -> bool:
    left = _aware_datetime(available_at)
    right = _aware_datetime(as_of)
    if left is None or right is None:
        return False
    return left <= right


def _ack_ids(request: Mapping) -> tuple[object, ...]:
    """Return the acknowledged ratio-change ids, filtered to text-present.

    Only caller-supplied str ids that pass ``_text_present`` count in the
    ack tuple. bytes, ints, floats, bools, lists, dicts, sets, and any
    other non-iterable or non-text-present value are treated as ABSENT and
    are NEVER a match. A bare non-iterable (int, float, bool) is silently
    ABSENT rather than raised.
    """
    raw = request.get("acknowledged_ratio_changes")
    if raw is None:
        return ()
    if _text_present(raw):
        return (raw,)
    if isinstance(raw, (str, bytes)):
        # str/bytes that fail _text_present (empty / whitespace-only /
        # padded). Treat as ABSENT rather than a match.
        return ()
    try:
        iterator = iter(raw)
    except TypeError:
        return ()
    out: list[object] = []
    for item in iterator:
        if _text_present(item):
            out.append(item)
    return tuple(out)


def _verdict(
    reasons: list[str],
    ratio_record_id: object | None,
    ordinary_per_ads: object | None,
) -> AdsRatioVerdict:
    frozen = _freeze_reasons(reasons)
    return AdsRatioVerdict(
        allowed=not frozen,
        reasons=frozen,
        ratio_record_id=ratio_record_id,
        ordinary_per_ads=ordinary_per_ads,
    )


def check_ads_ratio(
    request: Mapping,
    records: object,
    *,
    as_of: object,
) -> AdsRatioVerdict:
    """Refuse an ADS-to-ordinary ratio unless exactly one owner-sourced
    interval covers the date, it was available as of the decision time,
    and any ratio change inside the requested window is acknowledged.

    Reports every applicable reason, de-duplicated, in REASONS order.
    The verdict is invariant to the order of ``records``.

    ``as_of`` semantics: an ``as_of`` that is None, non-str, or
    unparseable — including empty string, an int, a bool, a list, or a
    malformed datetime — is refused as ``RATIO_NOT_AVAILABLE_AS_OF``.
    This is fail-closed: a missing or unparseable ``as_of`` never silently
    coerces to "now".

    Acknowledgement semantics: the caller-supplied
    ``acknowledged_ratio_changes`` field is matched against the covering
    ``ratio_record_id`` after the FAMILY TEXT RULE. Only text-present
    caller-supplied str ids count in the ack tuple — bytes, ints, lists,
    dicts, sets, or any other object are ABSENT and NEVER a match. An
    ack that omits the covering ratio_record_id (or supplies any
    non-text-present value) is refused as
    ``RATIO_CHANGE_UNACKNOWLEDGED`` when the window-covers case fires.
    """
    refuse_nonfalse_authority()
    if not isinstance(request, Mapping):
        raise TypeError("request must be a Mapping")

    reasons: list[str] = []
    rec_list: list[Mapping] = []
    if records is None:
        reasons.append("RATIO_RECORDS_MISSING")
    else:
        rec_list = list(records)
        if not rec_list:
            reasons.append("RATIO_RECORDS_MISSING")
        for rec in rec_list:
            if not isinstance(rec, Mapping):
                raise TypeError("each record must be a Mapping")

    request_issuer = request.get("issuer_id")
    on_date = _iso_date(request.get("on_date"))
    window_raw = request.get("window_start")
    window_date: date | None = None
    date_invalid = on_date is None
    if window_raw is not None:
        window_date = _iso_date(window_raw)
        if window_date is None:
            date_invalid = True
        elif on_date is not None and window_date > on_date:
            date_invalid = True

    unsourced = False
    nonpositive = False
    interval_invalid = False
    issuer_mismatch = False
    for rec in rec_list:
        if not _present(rec, "source_ref") or not _present(rec, "ratio_record_id"):
            unsourced = True
        if not _finite_positive(rec.get("ordinary_per_ads")):
            nonpositive = True
        start, end, ok = _interval(rec)
        if not ok:
            date_invalid = True
        elif end is not None and start is not None and end <= start:
            interval_invalid = True
        # FAMILY TEXT RULE v2: equality only between two present values (X9-03).
        rec_issuer = rec.get("issuer_id")
        if not (_text_present(rec_issuer) and _text_present(request_issuer)
                and rec_issuer == request_issuer):
            issuer_mismatch = True

    if unsourced:
        reasons.append("RATIO_RECORD_UNSOURCED")
    if nonpositive:
        reasons.append("RATIO_NONPOSITIVE")
    if interval_invalid:
        reasons.append("INTERVAL_INVALID")

    overlap = False
    matched = [
        rec
        for rec in rec_list
        if rec.get("issuer_id") == request_issuer and _interval_usable(rec)
    ]
    for i, left in enumerate(matched):
        for right in matched[i + 1 :]:
            if _intervals_overlap(left, right):
                overlap = True
                break
        if overlap:
            break
    if overlap:
        reasons.append("INTERVAL_OVERLAP")

    if issuer_mismatch:
        reasons.append("ISSUER_MISMATCH")
    if date_invalid:
        reasons.append("DATE_INVALID")

    cover_on: list[Mapping] = []
    if on_date is not None:
        for rec in rec_list:
            if _covers_day(rec, request_issuer, on_date):
                cover_on.append(rec)

    ratio_record_id: object | None = None
    ordinary_per_ads: object | None = None
    if len(cover_on) == 1:
        ratio_record_id = cover_on[0].get("ratio_record_id")
        ordinary_per_ads = cover_on[0].get("ordinary_per_ads")

    if rec_list and on_date is not None and len(cover_on) == 0:
        reasons.append("NO_INTERVAL_COVERS_DATE")

    if len(cover_on) == 1:
        if not _available_as_of(cover_on[0].get("available_at"), as_of):
            reasons.append("RATIO_NOT_AVAILABLE_AS_OF")
        if window_date is not None:
            cover_win = [
                rec
                for rec in rec_list
                if _covers_day(rec, request_issuer, window_date)
            ]
            if len(cover_win) == 1:
                if cover_win[0].get("ordinary_per_ads") != cover_on[0].get(
                    "ordinary_per_ads"
                ):
                    if cover_on[0].get("ratio_record_id") not in _ack_ids(request):
                        reasons.append("RATIO_CHANGE_UNACKNOWLEDGED")

    return _verdict(reasons, ratio_record_id, ordinary_per_ads)
