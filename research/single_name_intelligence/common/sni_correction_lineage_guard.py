"""SNI-local DRAFT correction-lineage guard (A16 append-only history refusal).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
correction/version-record values shaped like the source owners'
correction and vintage records and the qledger/Evaluation owner's
append-only ledgers. It does not re-implement Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options,
Research Vault, or qledger/Evaluation. Identity ids are caller-supplied
opaque strings owned by Stock Identity / Data OS; this guard never
mints, derives, or guesses canonical HK/US issuer or security
identifiers from a ticker, name, code, or CIK. Unknown identity stays
UNRESOLVED / null.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. A proposed record
history that is not a strict append-only extension of the prior history
— one strictly increasing version chain, correct supersedes links, a
real content change, and monotone record times — is refused, not
repaired, merged, or rewritten.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path. Every authority flag is literal false. A caller that tries to set
any of them true is refused (raise). Residuals and stress statistics
stay descriptive; this guard makes no causal or news-impact claim (A24).
An unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a
signal, score, or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

RECORD_FIELDS: tuple[str, ...] = (
    "record_id",
    "version_id",
    "version",
    "supersedes_version_id",
    "content_sha256",
    "recorded_at",
)

REASONS: tuple[str, ...] = (
    "RECORD_FIELD_INVALID",
    "MIXED_RECORD_IDS",
    "HISTORY_TRUNCATED",
    "HISTORY_REWRITTEN",
    "DUPLICATE_VERSION_ID",
    "FORK",
    "VERSION_GAP",
    "VERSION_NOT_INCREASING",
    "SUPERSEDES_MISMATCH",
    "CONTENT_UNCHANGED",
    "RECORDED_AT_NOT_MONOTONE",
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

_RECORD_FIELD_SET = frozenset(RECORD_FIELDS)
_HEX_DIGITS = frozenset("0123456789abcdef")


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
class LineageVerdict:
    """Descriptive lineage refusal. Carries no record content or ledger write."""

    allowed: bool
    reasons: tuple[str, ...]
    appended: tuple[str, ...]

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)
        object.__setattr__(self, "appended", tuple(self.appended))

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """An opaque-text id / ref is present iff it is a non-empty string
    that does not begin or end with whitespace. None, ``""``, ``"  "``, ``1``, ``True``,
    ``1.0``, ``b"id"``, ``["id"]``, and any other object are ABSENT and
    never match each other. Applied to ``record_id``, ``version_id`` and
    ``supersedes_version_id``; numbers (the ``version`` int), timestamps
    parsed by ``_aware_datetime``, the SHA-256 hex string checked by
    ``_is_sha256_hex``, and the record container itself keep their
    existing checks and are NOT routed through this helper.

    FAMILY TEXT RULE v2 (seat ruling): a string that begins or ends with
    whitespace is ABSENT, exactly like a whitespace-only string, so a
    padded id can never pass as a different valid id. The check uses no
    normalisation method (``.strip()`` / ``.lower()`` / ``.upper()`` /
    ``.casefold()`` / ``.replace()``), which keeps the family's
    no-normalisation static scans green.
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


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _aware_datetime(text: object) -> datetime | None:
    """Timezone-aware ISO-8601 parse. Naive values, including date-only, refuse."""
    if not isinstance(text, str) or text == "":
        return None
    body = text
    if body.endswith("Z"):
        body = body[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(body)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _nonblank_str(value: object) -> bool:
    return _text_present(value)


def _version_number(value: object) -> int | None:
    # bool is a subclass of int; a version must be a real int >= 1.
    if type(value) is not int:
        return None
    if value < 1:
        return None
    return value


def _is_sha256_hex(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    for char in value:
        if char not in _HEX_DIGITS:
            return False
    return True


def _as_mapping(record: object) -> Mapping[str, object]:
    if not isinstance(record, Mapping):
        raise TypeError("version record must be a Mapping")
    return record


def _valid_record(record: object) -> bool:
    body = _as_mapping(record)
    if set(body) != _RECORD_FIELD_SET:
        return False
    if not _text_present(body.get("record_id")):
        return False
    if not _text_present(body.get("version_id")):
        return False
    if _version_number(body.get("version")) is None:
        return False
    supersedes = body.get("supersedes_version_id")
    if supersedes is not None and not _text_present(supersedes):
        return False
    if not _is_sha256_hex(body.get("content_sha256")):
        return False
    if _aware_datetime(body.get("recorded_at")) is None:
        return False
    return True


def _readable_field(records: tuple[Mapping[str, object], ...], key: str) -> list[str]:
    out: list[str] = []
    for record in records:
        value = record.get(key)
        if _text_present(value):
            out.append(value)
    return out


def check_lineage(
    prior: tuple[Mapping[str, object], ...],
    proposed: tuple[Mapping[str, object], ...],
) -> LineageVerdict:
    """Refuse a proposed record history unless it extends the prior history
    append-only.

    prior and proposed are tuples of version records for ONE record_id.
    The verdict's appended is the tuple of version_ids present in proposed
    but not prior, in proposed order. Reasons are reported de-duplicated,
    in REASONS order; allowed is True iff reasons is empty. proposed
    equal to prior is allowed (appended is empty); prior may be empty
    (first write). Chain rules (fork, gap, ordering, supersedes, content
    change, record-time monotonicity) run on the proposed history.
    """
    refuse_nonfalse_authority()
    if not isinstance(prior, (tuple, list)):
        raise TypeError("prior must be a tuple of version records")
    if not isinstance(proposed, (tuple, list)):
        raise TypeError("proposed must be a tuple of version records")
    prior_records = tuple(_as_mapping(record) for record in prior)
    proposed_records = tuple(_as_mapping(record) for record in proposed)

    prior_valid = all(_valid_record(record) for record in prior_records)
    proposed_valid = len(proposed_records) > 0 and all(
        _valid_record(record) for record in proposed_records
    )

    reasons: list[str] = []
    if not proposed_valid or not prior_valid:
        reasons.append("RECORD_FIELD_INVALID")

    prior_vids = _readable_field(prior_records, "version_id")
    proposed_vids = _readable_field(proposed_records, "version_id")
    prior_vid_set = frozenset(prior_vids)
    appended = tuple(vid for vid in proposed_vids if vid not in prior_vid_set)

    record_ids = _readable_field(prior_records, "record_id")
    record_ids.extend(_readable_field(proposed_records, "record_id"))
    if len(set(record_ids)) > 1:
        reasons.append("MIXED_RECORD_IDS")

    if prior_valid and proposed_valid:
        if len(proposed_records) < len(prior_records):
            reasons.append("HISTORY_TRUNCATED")
        if any(vid not in frozenset(proposed_vids) for vid in prior_vids):
            reasons.append("HISTORY_TRUNCATED")

        prior_by_vid: dict[str, Mapping[str, object]] = {}
        for record in prior_records:
            prior_by_vid.setdefault(record["version_id"], record)
        for record in proposed_records:
            earlier = prior_by_vid.get(record["version_id"])
            if earlier is not None and record != earlier:
                reasons.append("HISTORY_REWRITTEN")

        if len(set(proposed_vids)) != len(proposed_vids):
            reasons.append("DUPLICATE_VERSION_ID")

        versions = [record["version"] for record in proposed_records]
        if len(set(versions)) != len(versions):
            reasons.append("FORK")
        if sorted(versions) != list(range(1, len(versions) + 1)):
            reasons.append("VERSION_GAP")
        if any(
            versions[index] >= versions[index + 1]
            for index in range(len(versions) - 1)
        ):
            reasons.append("VERSION_NOT_INCREASING")

        by_version: dict[int, Mapping[str, object]] = {}
        for record in proposed_records:
            by_version.setdefault(record["version"], record)
        for record in proposed_records:
            number = record["version"]
            if number == 1:
                if record["supersedes_version_id"] is not None:
                    reasons.append("SUPERSEDES_MISMATCH")
                continue
            previous = by_version.get(number - 1)
            if previous is None:
                continue
            if record["supersedes_version_id"] != previous["version_id"]:
                reasons.append("SUPERSEDES_MISMATCH")
            if record["content_sha256"] == previous["content_sha256"]:
                reasons.append("CONTENT_UNCHANGED")
            if _aware_datetime(record["recorded_at"]) <= _aware_datetime(
                previous["recorded_at"]
            ):
                reasons.append("RECORDED_AT_NOT_MONOTONE")

    frozen = _freeze_reasons(reasons)
    return LineageVerdict(
        allowed=not frozen,
        reasons=frozen,
        appended=appended,
    )