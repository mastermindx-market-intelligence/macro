"""SNI-local DRAFT then-known view compiler (A07/A08 three-clock refusal).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied fact
records shaped like the Company Event/Earnings and Research Vault owners'
fact records, with their four clocks: economic_time (the period a fact is
about), owner_known_at (when the owning desk recorded it), published_at
(when the source published it), and retrieved_at (when SNI retrieved it).
It does not re-implement Data OS identity, Company Event/Earnings, FIF,
Capital Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation. Identity ids and fact ids are caller-supplied opaque
strings owned by Stock Identity / Data OS; this compiler never mints,
derives, or guesses canonical HK/US issuer or security identifiers from a
ticker, name, code, or CIK. Unknown identity stays UNRESOLVED / null.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. A fact that was not
knowable at the cutoff is excluded, not back-dated. economic_time is
validated but never compared to the cutoff: a fact about a future period
can be known now, and a fact about a past period may not be. A timestamp
exactly equal to the cutoff is then-known. Any validation refusal fails
closed: no partial view is emitted.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path. Every authority flag is literal false. A caller that tries to set
any of them true is refused (raise). Residuals and stress statistics stay
descriptive; this compiler makes no causal or news-impact claim (A24). An
unestimable family is outside this module; the compiler never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a
signal, score, or forecast.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping

REASONS: tuple[str, ...] = (
    "FACT_ID_MISSING",
    "DUPLICATE_FACT_ID",
    "ECONOMIC_TIME_INVALID",
    "OWNER_KNOWN_INVALID",
    "PUBLISHED_INVALID",
    "RETRIEVED_INVALID",
    "OWNER_KNOWN_BEFORE_PUBLISHED",
    "RETRIEVED_BEFORE_PUBLISHED",
    "SUPERSEDES_UNKNOWN",
    "SUPERSEDES_CYCLE",
)

EXCLUSION_REASONS: tuple[str, ...] = (
    "PUBLISHED_AFTER_CUTOFF",
    "OWNER_KNOWN_AFTER_CUTOFF",
    "RETRIEVED_AFTER_CUTOFF_UNVINTAGED",
    "SUPERSEDED_BY_THEN_KNOWN",
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
class ThenKnownView:
    """Descriptive then-known view. Carries no values, scores, or forecasts."""

    allowed: bool
    reasons: tuple[str, ...]
    included: tuple[str, ...]
    excluded: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)
        object.__setattr__(self, "included", tuple(self.included))
        object.__setattr__(self, "excluded", tuple(self.excluded))
        if frozen and (self.included or self.excluded):
            raise ValueError(
                "a validation refusal cannot carry a partial view; "
                "included and excluded must be empty when reasons are present"
            )

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
    """FAMILY TEXT RULE v2 (seat ruling): an opaque-text id / ref /
    label is PRESENT iff it is a non-empty ``str`` that does not begin
    or end with whitespace. None, ``""``, ``"  "``, ``"ID "``,
    ``" ID"``, ``"\tID"``, ``"ID　"``, ``1``, ``True``, ``1.0``,
    ``b"id"``, ``["id"]`` and any other object are ABSENT and never
    match each other.

    The helper calls NO normalisation method (no ``.strip`` /
    ``.lower`` / ``.upper`` / ``.casefold`` / ``.replace``), which
    keeps the family's no-normalisation static scans green.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _as_datetime(text: object) -> datetime | None:
    if not isinstance(text, str) or text == "":
        return None
    if len(text) == 10:
        try:
            parsed_day = date.fromisoformat(text)
        except ValueError:
            return None
        return datetime(parsed_day.year, parsed_day.month, parsed_day.day)
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


def _require_aware(item: Mapping[str, object], key: str) -> datetime:
    parsed = _aware_value(item.get(key))
    if parsed is None:
        raise ValueError(
            f"{key} must be an ISO-8601 datetime with offset; "
            "a missing, naive, or unparseable value refuses"
        )
    return parsed


def clock_triplet(item: Mapping[str, object]) -> tuple[datetime, datetime, datetime]:
    """Return (published_at, owner_known_at, retrieved_at) as aware datetimes.

    Raises ValueError when any of the three knowledge clocks is missing,
    naive, or unparseable. economic_time is deliberately not part of the
    triplet: it is the economic clock, never a knowledge clock.
    """
    if not isinstance(item, Mapping):
        raise TypeError("item must be a Mapping")
    return (
        _require_aware(item, "published_at"),
        _require_aware(item, "owner_known_at"),
        _require_aware(item, "retrieved_at"),
    )


def _has_supersedes_cycle(edges: Mapping[str, str]) -> bool:
    """True when following supersedes from any item returns to a visited item."""
    safe: set[str] = set()
    for start in edges:
        if start in safe:
            continue
        on_path: set[str] = set()
        path: list[str] = []
        node: str = start
        while node in edges and node not in safe:
            if node in on_path:
                return True
            on_path.add(node)
            path.append(node)
            node = edges[node]
        safe.update(path)
    return False


def _fact_id_absent(value: object) -> bool:
    """True for ABSENT fact_id per FAMILY TEXT RULE v2 (seat ruling):
    None, a non-``str`` (int, float, bool, bytes, list, dict, set, or
    any other object), an empty ``str``, a whitespace-only ``str``, or
    a ``str`` that begins or ends with whitespace.

    Whitespace-only is detected via ``str.isspace()`` so the rejection
    covers every Unicode whitespace character -- including ``"　"``
    ideographic space, ``" "`` no-break space, ``" "`` em
    space, ``"\x1c"`` file separator, ``"\u0085"`` NEL, and ``" "``
    line separator -- not just the ASCII subset.

    Padded ``str`` values (e.g. ``"SYN-FACT-1 "``, ``" SYN-FACT-1"``)
    are CLOSED here under FAMILY TEXT RULE v2: a padded fact_id is
    ABSENT, never a different valid id. X8B-02's padded half is CLOSED.

    The implementation never calls ``.strip`` / ``.lower`` / ``.upper`` /
    ``.casefold`` / ``.replace`` on the value: those attribute names are
    forbidden by ``test_a07g_static_scan_no_normalisation_ast``. Calling
    ``.isspace()`` on a single character is allowed by the same scan.
    """
    return not _text_present(value)


def then_known_view(
    items: Iterable[Mapping[str, object]],
    *,
    cutoff: str,
) -> ThenKnownView:
    """Compile the then-known view of items at a cutoff instant.

    Fact ids and supersedes links are compared as exact strings; they are
    never folded, stripped, or normalised. Validation failures fail closed
    (allowed False, empty included/excluded). Otherwise each item carries
    the FIRST applicable exclusion, or is included.
    """
    refuse_nonfalse_authority()
    if isinstance(items, (str, bytes)) or not isinstance(items, Iterable):
        raise TypeError("items must be an iterable of Mappings")
    item_list = list(items)
    for item in item_list:
        if not isinstance(item, Mapping):
            raise TypeError("item must be a Mapping")
    cutoff_dt = _aware_value(cutoff)
    if cutoff_dt is None:
        raise ValueError(
            "cutoff must be an ISO-8601 datetime with offset; "
            "a missing, naive, or unparseable value refuses"
        )

    reasons: list[str] = []

    # Pass 1: fact ids (exact strings; a variant spelling is a different id).
    # _fact_id_absent catches the unpinned cases (None, non-str, empty,
    # whitespace-only -- via str.isspace so Unicode whitespace counts)
    # and leaves padded strings as PRESENT (X8B-02 padded half stays
    # open per the pinning test_a07g_duplicate_exact_only_no_folding).
    known_ids: set[str] = set()
    for item in item_list:
        fact_id = item.get("fact_id")
        if _fact_id_absent(fact_id):
            reasons.append("FACT_ID_MISSING")
            continue
        # _fact_id_absent returned False: the value is a non-empty,
        # non-whitespace-only str (possibly padded). The padded form is
        # a distinct, PRESENT id; the unpadded form is also PRESENT.
        # Both flow into the duplicate check below as opaque strings.
        if not isinstance(fact_id, str):  # defensive; the helper already gated
            reasons.append("FACT_ID_MISSING")
            continue
        if fact_id in known_ids:
            reasons.append("DUPLICATE_FACT_ID")
        else:
            known_ids.add(fact_id)

    # Pass 2: clock validation, clock ordering, supersedes targets.
    rows: list[tuple[str | None, datetime | None, datetime | None, datetime | None, object, object]] = []
    edges: dict[str, str] = {}
    for item in item_list:
        fact_id = item.get("fact_id")
        economic = _aware_value(item.get("economic_time"))
        if economic is None:
            reasons.append("ECONOMIC_TIME_INVALID")
        owner_known = _aware_value(item.get("owner_known_at"))
        if owner_known is None:
            reasons.append("OWNER_KNOWN_INVALID")
        published = _aware_value(item.get("published_at"))
        if published is None:
            reasons.append("PUBLISHED_INVALID")
        retrieved = _aware_value(item.get("retrieved_at"))
        if retrieved is None:
            reasons.append("RETRIEVED_INVALID")
        if published is not None and owner_known is not None:
            if owner_known < published:
                reasons.append("OWNER_KNOWN_BEFORE_PUBLISHED")
        if published is not None and retrieved is not None:
            if retrieved < published:
                reasons.append("RETRIEVED_BEFORE_PUBLISHED")
        supersedes = item.get("supersedes")
        # FAMILY TEXT RULE v2: None and "" are the "no link" short-circuit
        # (pinned by test_a07g_blank_supersedes_treated_as_absent). Any
        # OTHER value that is not text-present (whitespace-only, padded,
        # non-str, unhashable) is ABSENT and emits SUPERSEDES_UNKNOWN. A
        # text-present value that is not in known_ids also emits
        # SUPERSEDES_UNKNOWN. ``superseded.add(...)`` and edge creation
        # happen only for text-present values, so nothing here ever
        # raises on junk input.
        if supersedes is None or supersedes == "":
            pass
        elif not _text_present(supersedes):
            reasons.append("SUPERSEDES_UNKNOWN")
        elif supersedes not in known_ids:
            reasons.append("SUPERSEDES_UNKNOWN")
        elif _text_present(fact_id):
            edges[fact_id] = supersedes
        rows.append(
            (fact_id, published, owner_known, retrieved, supersedes, item.get("vintaged"))
        )

    # Pass 3: cycle detection over known supersedes links.
    if _has_supersedes_cycle(edges):
        reasons.append("SUPERSEDES_CYCLE")

    frozen = _freeze_reasons(reasons)
    if frozen:
        # Fail closed: a validation refusal emits no partial view.
        return ThenKnownView(False, frozen, (), ())

    # Exclusion pass: the three knowledge clocks gate, economic_time never does.
    clock_reasons: dict[str, str | None] = {}
    passing: list[tuple[str, object]] = []
    for fact_id, published, owner_known, retrieved, supersedes, vintaged in rows:
        clock_reason: str | None = None
        if published is not None and published > cutoff_dt:
            clock_reason = "PUBLISHED_AFTER_CUTOFF"
        elif owner_known is not None and owner_known > cutoff_dt:
            clock_reason = "OWNER_KNOWN_AFTER_CUTOFF"
        elif retrieved is not None and retrieved > cutoff_dt and vintaged is not True:
            clock_reason = "RETRIEVED_AFTER_CUTOFF_UNVINTAGED"
        clock_reasons[fact_id] = clock_reason
        if clock_reason is None:
            passing.append((fact_id, supersedes))

    superseded: set[str] = set()
    for fact_id, supersedes in passing:
        # FAMILY TEXT RULE v2: only text-present supersedes reach
        # superseded; the rest were already emitted as SUPERSEDES_UNKNOWN
        # in Pass 2 and the view would have failed closed before this
        # loop ran. This guard keeps that invariant explicit and ensures
        # no junk input can raise from ``set.add``.
        if _text_present(supersedes):
            superseded.add(supersedes)

    included: list[str] = []
    excluded: list[tuple[str, str]] = []
    for fact_id, _published, _owner, _retrieved, _supersedes, _vintaged in rows:
        clock_reason = clock_reasons[fact_id]
        if clock_reason is not None:
            excluded.append((fact_id, clock_reason))
        elif fact_id in superseded:
            excluded.append((fact_id, "SUPERSEDED_BY_THEN_KNOWN"))
        else:
            included.append(fact_id)
    return ThenKnownView(True, (), tuple(included), tuple(excluded))
