"""The theme-research foundation every registered vertical shares.

Sol's decomposition ruling on carrier PR #7870 (issuecomment-5895067178,
refreshed in 5923155205) names this leaf as the canonical shared owner and
bounds what may live here: the shared refusal/unavailability protocol,
canonical anchor-versus-``theme:<slug>`` scope matching, canonical JSON,
cutoff/time comparison and unreadable-owner withholding primitives, and
shared query-format validation and generation/fingerprint mechanics "where
all vertical inputs are explicit arguments rather than semiconductor
defaults".

What is deliberately NOT here
-----------------------------
Slice and view vocabularies, labels, registration membership, schema ids,
evidence schema ids, definition versions, vertical query literals, economic
interpretation, financial logic, row construction, vertical limitation
tokens, evidence-selection policy, rights/source mappings, navigation, and
every ranking/gating/entry/sizing/trading authority. Those stay with their
vertical. Semiconductor's five view literals and its ``ResearchQuery``
literals are NOT promoted into universal law merely because other lanes
mirrored them, and nothing here is a framework, plugin system, dynamic
registry, schema, store, route, queue, publisher, rights plane, identity
plane or lifecycle plane.

Why a leaf
----------
The registry, every vertical's loader and the shell all share these names, so
they must live below all three without an import cycle. The module's own
imports are the standard library only; the one identity-owner call is bound
lazily inside the function that needs it so importing this foundation never
drags a data stack into the mount producers (the same law
``test_registry_import_closure_stays_light`` enforces next door).

No authority: nothing here ranks, gates, sizes, times or originates
anything, and no figure, token, credential or URL passes through.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "BundleUnavailable",
    "ResearchRefusal",
    "canonical_text",
    "generation_fingerprint",
    "in_anchor_scope",
    "is_instant",
    "le",
    "parse_clock",
    "parse_day",
    "readable",
    "validate_cutoff_format",
    "validate_pagination",
    "validate_replay_cutoffs",
    "within",
]


# ---------------------------------------------------------------------------
# The shared refusal / unavailability protocol
# ---------------------------------------------------------------------------

class BundleUnavailable(Exception):
    """The registered loader cannot serve a bundle for this request.

    Raised for: unbound private store, unreachable or refusing owner reader,
    a reader envelope that breaks its own contract, a rights snapshot that
    carries no revision. Never raised for coverage absence — that is a typed
    omission on the bundle, so the response says what is missing.
    """


class ResearchRefusal(ValueError):
    """A query/generation contract violation. ``str(exc)`` is exactly ``.code``.

    Shared because the shell catches it at the transport boundary: the
    ``except`` clause must resolve without loading any vertical's composer,
    which is precisely what the eager import removed here was doing. The
    shell maps refusal codes to the existing private error family; a vertical
    raises this with its OWN code and never invents a status code or an error
    string family.
    """

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ---------------------------------------------------------------------------
# Canonical JSON
# ---------------------------------------------------------------------------

def canonical_text(payload: Mapping[str, Any]) -> str:
    """The one canonical serialization: sorted keys, no spurious whitespace,
    non-ASCII preserved, NaN refused.

    Measured on this build: the only production caller is
    :func:`generation_fingerprint`, and it serializes query dimensions that
    are ASCII by construction — so ``ensure_ascii=False`` changes no digest
    this build emits. It is stated and pinned here (not in a caller) because
    the first caller to serialize bilingual copy inherits it, and a digest
    that escapes a zh label is a different digest for the same content.
    """
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


# ---------------------------------------------------------------------------
# Cutoff / time comparison, and unreadable-owner withholding
# ---------------------------------------------------------------------------

def is_instant(value: str) -> bool:
    return "T" in value


def parse_clock(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def parse_day(value: str):
    return parse_clock(value).date() if is_instant(value) else datetime.strptime(value, "%Y-%m-%d").date()


def le(value: str, cutoff: str) -> bool:
    """``value <= cutoff`` for date-or-datetime strings, WITHOUT synthesizing a
    time: when either side is date-only the comparison is on calendar days
    (inclusive). Two instants compare as instants.

    CONTRACT, for consumers reading a date-only cutoff (asked by the Energy
    seat on #7870): the calendar day taken from an instant is the day in the
    instant's OWN offset, so a date-only cutoff means "the source's local day",
    not "the UTC day". Measured on this build::

        le("2026-12-31T23:00:00-05:00", "2026-12-31")  # True  (04:00Z on Jan 1)
        le("2027-01-01T01:00:00+08:00", "2026-12-31")  # False (17:00Z on Dec 31)

    This is deliberate and follows from the no-synthesis rule above: converting
    to UTC first and then taking the date would pick UTC midnight as the cutoff
    instant -- a time the caller never supplied, in a zone the cutoff never
    named. A caller that wants instant semantics states an instant cutoff, and
    then no day is inferred on either side::

        le("2026-12-31T23:00:00-05:00", "2026-12-31T23:59:59+00:00")  # False

    Grain mismatch in the other direction is not silently resolved either: a
    date-only publication landing ON the cutoff instant's own day cannot be
    placed before or after it, so a replay gate drops that row with its own
    same-day-ambiguity limitation rather than guessing a side.
    """
    if not is_instant(value) and not is_instant(cutoff):
        return parse_day(value) <= parse_day(cutoff)
    if not is_instant(value):          # date vs instant: compare days
        return parse_day(value) <= parse_clock(cutoff).date()
    if not is_instant(cutoff):         # instant vs date: compare days
        return parse_clock(value).date() <= parse_day(cutoff)
    return parse_clock(value) <= parse_clock(cutoff)


def within(value: Any, cutoff: Any) -> bool:
    """:func:`le` for an OWNER-SUPPLIED timestamp: a value this transport
    cannot read is ``False`` — the row is WITHHELD, never fatal.

    ``le`` raises ``ValueError`` on a string it cannot parse and ``TypeError``
    on a non-string. Reached from a time gate, that bare exception left the
    route's catch-all to answer 503, so ONE unreadable timestamp from the owner
    denied the caller every row it was entitled to. That is the same defect
    ``app/theme_research.py`` already fixed for an unreadable ROW ("a row this
    transport cannot read is WITHHELD, never fatal; withholding is the
    fail-closed answer, 503 is not") — this is that law applied to the
    timestamps inside the row. Reported by the Energy seat as base item 5
    (#7870 issuecomment-5866433049), whose probe used an empty ``reviewed_at``.

    Every caller reads this as "in range", so ``False`` withholds in both
    polarities: an inclusion test does not include, an exclusion test excludes.
    The parse is unchanged for every value ``le`` could already read."""
    try:
        return le(value, cutoff)
    except (ValueError, TypeError):
        return False


def readable(value: Any) -> bool:
    """Whether :func:`le` could compare this owner timestamp at all — the
    distinction between "not datable" and "datable, and outside the cutoff",
    which the caller needs to pick the right limitation."""
    try:
        parse_day(value)
    except (ValueError, TypeError):
        return False
    return True


# ---------------------------------------------------------------------------
# Shared query-format validation — every vertical input an explicit argument
# ---------------------------------------------------------------------------

def validate_pagination(*, limit: Any, offset: Any, expected_generation: Any,
                        min_limit: int, max_limit: int) -> None:
    """Page bounds and the deep-page generation pin.

    ``min_limit``/``max_limit`` are the VERTICAL's declared bounds, passed in
    rather than defaulted here: this helper carries no page policy of its own.
    ``bool`` is rejected explicitly because it is an ``int`` subclass and
    ``True`` would otherwise pass as a limit of 1.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) \
            or not min_limit <= limit <= max_limit:
        raise ResearchRefusal("limit_out_of_range")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ResearchRefusal("offset_negative")
    if offset > 0 and expected_generation is None:
        raise ResearchRefusal("expected_generation_required")


def validate_replay_cutoffs(*, time_mode: Any, source_cutoff: Any,
                            recorded_cutoff: Any,
                            replay_mode: str = "system_replay") -> None:
    """Replay needs both cutoffs. The mode TOKEN is an argument because the
    mode vocabulary is the vertical's, not this foundation's."""
    if time_mode == replay_mode and (source_cutoff is None or recorded_cutoff is None):
        raise ResearchRefusal("replay_cutoffs_required")


def validate_cutoff_format(*cutoffs: Any) -> None:
    """A SUPPLIED cutoff must be readable, in EVERY mode.

    Until this ran, the first parse happened inside a time gate: ``le`` raised
    a bare ValueError and the route's catch-all answered 503 ``retry_later``
    (a transient code for a permanently malformed request), and where no gate
    read the cutoff the request answered a silent 200 that echoed the
    unreadable value back in ``request.recorded_cutoff`` with no limitation
    marking it. Both halves measured by the Energy seat over nuclear's route
    (#7870 issuecomment-5868018569, corrected in 5869344590 and 5870740225).

    :func:`parse_day` is the parser deliberately: it accepts EXACTLY the values
    :func:`le` can go on to compare. ``parse_clock``/``fromisoformat`` would
    admit ``20261231`` and ``2026-W53-4``, which ``le`` then raises on — the
    validator would hand those straight back to the 503 it exists to remove.

    FORMAT only. A well-formed cutoff is never refused for arriving in a mode
    a module does not read it in: a registered vertical may read one there on
    purpose (nuclear judges target windows from ``source_cutoff`` in
    ``latest``), and refusing it would fail that vertical's existing pins.
    """
    for raw in cutoffs:
        if raw is None:
            continue
        try:
            parse_day(raw)
        except (ValueError, TypeError):
            raise ResearchRefusal("cutoff_unreadable") from None


# ---------------------------------------------------------------------------
# Canonical anchor scope matching
# ---------------------------------------------------------------------------

def in_anchor_scope(assertion: Mapping[str, Any], anchor_theme_id: str) -> bool:
    """Whether an assertion belongs to the anchor the query names.

    TWO VOCABULARIES MEET HERE, and they are deliberately different. The
    mount/API ``anchor_theme_id`` is the crosswalk SLUG (``ai_semiconductors``,
    ``^[a-z0-9_]+$`` at the route). The assertion's ``scope.canonical_theme_id``
    is the identity owner's NODE id, ``theme:<slug>`` — the canonical-id law
    this carrier published at #7870 issuecomment-5812295091, which every later
    vertical was told to mint through
    :func:`engine.theme_graph.identity.theme_node_id`, and which the
    semiconductor contract's own schema gives as its example
    ("e.g. theme:semiconductors").

    Comparing the two as raw strings — which is what this gate did until now —
    admits ONLY the slug form. The semiconductor corpus happens to carry the
    slug, so the shipping vertical worked and the defect stayed invisible; a
    vertical that followed the published law instead matched nothing, and
    because an out-of-scope row is deliberately silent it got zero rows and NO
    limitation naming why. Accepting both forms is what makes the foundation's
    own law executable, which is why it is shared rather than copied.

    Resolution goes through the identity owner rather than a literal
    ``"theme:" + anchor`` so the prefix has ONE definition, and there is no
    resolver parameter: a vertical that could pass its own would be able to
    reintroduce exactly the defect this closes. It also refuses ``ltheme:``
    structurally, with no blocklist: the owner declares that prefix
    deliberately non-canonical, and ``theme_node_id`` can never produce it.

    The identity import is bound lazily so this foundation stays importable
    without a data stack."""
    scope_id = assertion.get("scope", {}).get("canonical_theme_id")
    if not isinstance(scope_id, str) or not scope_id:
        return False
    if scope_id == anchor_theme_id:
        return True
    from engine.theme_graph.identity import theme_node_id  # noqa: PLC0415 — lazy by design
    try:
        return scope_id == theme_node_id(anchor_theme_id)
    except ValueError:
        return False  # an anchor the identity owner cannot form a node id for


# ---------------------------------------------------------------------------
# Generation / fingerprint mechanics
# ---------------------------------------------------------------------------

def generation_fingerprint(*, definition_version: str, rights_revision: str,
                           revision_tuple: Any, fields: Mapping[str, Any],
                           prefix: str = "gen_", width: int = 32) -> str:
    """The shared fingerprint: ``prefix`` + sha256 of the canonical payload.

    Every vertical input is an explicit argument. ``fields`` carries the
    vertical's OWN query dimensions (semiconductor passes slice/view/time
    mode/cutoffs/anchor); this helper adds no dimension of its own and
    defaults none. Mining's different generation semantics and Technology's
    temporal-key defect are NOT forced into this shape — a vertical that
    needs other mechanics keeps its own and simply does not call this.

    ``revision_tuple`` is sorted into lists so an owner revision set
    fingerprints independently of the order it arrived in. Key insertion
    order is irrelevant: :func:`canonical_text` sorts.
    """
    payload = {
        "definition_version": definition_version,
        "rights_revision": rights_revision,
        "revision_tuple": sorted(list(pair) for pair in revision_tuple),
        **dict(fields),
    }
    digest = hashlib.sha256(canonical_text(payload).encode("utf-8")).hexdigest()[:width]
    return prefix + digest
