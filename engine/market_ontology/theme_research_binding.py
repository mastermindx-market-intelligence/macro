"""The theme-research foundation every registered vertical shares.

Sol's decomposition ruling on carrier PR #7870 (issuecomment-5895067178,
refreshed in 5923155205) names this leaf as the canonical shared owner and
bounds what may live here: the shared refusal/unavailability protocol,
canonical anchor-versus-``theme:<slug>`` scope matching, canonical JSON,
cutoff/time comparison and unreadable-owner withholding primitives, and
shared query-format validation and generation/fingerprint mechanics "where
all vertical inputs are explicit arguments rather than semiconductor
defaults".

The str-typed ``ResearchQuery`` / ``OwnerBundle`` carriers and the five
gates ``passes_time_mode``, ``review_excluded``,
``filter_interpretation_blocks``, ``correction_lineage`` and
``collapse_syndicated`` live here too, but they did not all arrive from the
same place. ``passes_time_mode`` and ``filter_interpretation_blocks`` moved
out of the semiconductor composer. ``passes_time_mode`` still compares the
three mode tokens that composer compared (``latest``, ``source_history``,
``system_replay``), so the move does not change a semiconductor response
byte. ``filter_interpretation_blocks`` is that composer's replay filter on
interpretation blocks, same rule. ``review_excluded`` and
``correction_lineage`` were never on that composer: they are vertical-neutral
forms of gates the Robotics and Nuclear verticals carried on their own
branches, and neither branch is on this tree — each vertical module is
absent at this commit and on ``origin/main``, Robotics' first carrier
merged then was reverted the same day
(``agentos/workstreams/WS-GMI-ROBOTICS.md``, ROB-W1) and nuclear never
landed. ``_correction_lineage`` is the R3-7 family pattern of
research/energy/nuclear_program/rulings/R-ENE-2026-09-25-w2-module-r3.md;
``_review_excluded`` is recorded in the Robotics known-revisions decision
and the nuclear implementation handoff. ``collapse_syndicated`` has no
provenance this tree can show: the token occurs in no ``research/`` or
``agentos/`` artifact at this commit — only in this shell, the composer's
re-export and alias block, and the two shared-shell suites — so it is
documented here as an unwired proposed form, not as another vertical's
carried gate. They land here unwired: nothing in this tree calls them
except the shared-shell equality suite, which exercises them directly.
The semiconductor module binds them in its alias block and never invokes
them, so no semiconductor response byte depends on them.

What is deliberately NOT here
-----------------------------
Slice and view vocabularies, labels, registration membership, schema ids,
evidence schema ids, definition versions, economic interpretation, financial
logic, row construction, rights/source mappings, navigation, and every
ranking/gating/entry/sizing/trading authority. Those stay with their
vertical. ``ResearchQuery`` carries ``str`` fields, not a vertical
``Literal`` vocabulary, and semiconductor's five view literals are not
promoted into universal law. Nothing here is a framework, plugin system,
dynamic registry, schema, store, route, queue, publisher, rights plane,
identity plane or lifecycle plane.

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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "SHARED_CONTRACT_MODULE",
    "SHARED_SHELL_MODULE",
    "BundleUnavailable",
    "OwnerBundle",
    "ResearchQuery",
    "ResearchRefusal",
    "canonical_text",
    "collapse_syndicated",
    "correction_lineage",
    "filter_interpretation_blocks",
    "generation_fingerprint",
    "in_anchor_scope",
    "is_instant",
    "le",
    "parse_clock",
    "parse_day",
    "passes_time_mode",
    "readable",
    "review_excluded",
    "validate_cutoff_format",
    "validate_pagination",
    "validate_replay_cutoffs",
    "within",
]

#: The shared assertion contract. The string stays this module; callers
#: import it lazily. The shell module constant sits next to it so a vertical
#: can load both owners without naming a sibling vertical.
SHARED_CONTRACT_MODULE = "engine.theme_graph.curation_assertion"
SHARED_SHELL_MODULE = "engine.market_ontology.theme_research_binding"


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
# Str-typed carriers. Field order is the semiconductor order: frozen
# dataclasses bind positionally, and a reorder would misbind every caller.
# The closed literal vocabularies stayed behind; these fields are ``str``.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResearchQuery:
    anchor_theme_id: str
    slice_key: str
    view: str
    time_mode: str
    source_cutoff: str | None
    recorded_cutoff: str | None
    offset: int = 0
    limit: int = 50
    expected_generation: str | None = None


@dataclass(frozen=True)
class OwnerBundle:
    revision_tuple: tuple[tuple[str, str], ...]
    rights_revision: str
    assertions: tuple[Mapping[str, Any], ...]
    identity_results: tuple[Mapping[str, Any], ...]
    event_workspaces: tuple[Mapping[str, Any], ...]
    financial_packets: tuple[Mapping[str, Any], ...]
    interpretation_blocks: tuple[Mapping[str, Any], ...]
    native_refs: tuple[Mapping[str, Any], ...]
    omissions: tuple[str, ...]


def _curation_source_ref(assertion: Mapping[str, Any]) -> str:
    """``gmi-curation://<theme>/<revision>`` from fields already on the row.

    Same text ``source_ref_for`` emits for a fixture assertion that already
    validates. This leaf does not import the assertion validator: importing
    it would pull the schema stack into every mount producer.
    """
    scope = assertion.get("scope") or {}
    theme = scope.get("canonical_theme_id") if isinstance(scope, Mapping) else None
    return f"gmi-curation://{theme}/{assertion.get('curation_revision')}"


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


def passes_time_mode(assertion: Mapping[str, Any], query: ResearchQuery,
                     limitations: set[str]) -> bool:
    """The semiconductor time gate, moved unchanged.

    ``latest`` keeps the row. ``source_history`` keeps a row whose
    publication or availability is inside ``source_cutoff`` (no cutoff keeps
    the whole selection). ``system_replay`` keeps a row whose availability
    and recording are both inside the two cutoffs, and refuses to invent a
    midnight for a date-only publication on the cutoff day. An unreadable
    owner timestamp is withheld and named; it is not a 503.
    """
    source = assertion["source"]

    if query.time_mode == "latest":
        return True

    if query.time_mode == "source_history":
        if query.source_cutoff is None:
            return True  # no cutoff given: history is the whole selection
        # ``comparable`` tracks whether a date was actually READ, not whether a
        # field was present: an unreadable timestamp is undatable in the only
        # sense this gate can act on, so it reuses the existing
        # ``undatable_excluded`` token rather than vanishing silently.
        comparable = False
        published = source.get("published_at")
        if published is not None and readable(published):
            comparable = True
            if within(published, query.source_cutoff):
                return True
        available = source.get("available_at")
        if isinstance(available, str) and available != "unknown" and readable(available):
            comparable = True
            if within(available, query.source_cutoff):
                return True
        if not comparable:
            limitations.add("undatable_excluded")
        return False

    # system_replay: known availability AND system recording, both inside cutoffs
    available = source.get("available_at")
    # An availability this transport cannot READ is availability it does not
    # know, so it joins the unknown case rather than raising out of the gate.
    if not isinstance(available, str) or available == "unknown" or not readable(available):
        limitations.add("availability_unknown_excluded")
        return False
    if not within(available, query.source_cutoff):
        return False
    # Split "cannot be dated" from "dated, and outside the cutoff". Only the
    # first is a LIMITATION: being outside the cutoff is the answer the caller
    # asked for, while an undatable row is a row the caller never learns about
    # unless it is named. This is the same token the source_history branch
    # already emits, for the same reason.
    retained = source.get("retained_at")
    if not readable(retained):
        limitations.add("undatable_excluded")
        return False
    if not within(retained, query.recorded_cutoff):
        return False
    published = source.get("published_at")
    if published is not None:
        grain = source.get("published_at_grain")
        if grain == "date":
            # never synthesize midnight: a date-only publication on the cutoff
            # day cannot be placed before or after the cutoff instant
            if is_instant(query.source_cutoff) and readable(published) \
                    and parse_day(published) == parse_clock(query.source_cutoff).date():
                limitations.add("same_day_grain_ambiguous")
                return False
        if not readable(published):
            limitations.add("undatable_excluded")
            return False
        if not within(published, query.source_cutoff):
            return False
    return True


def review_excluded(assertion: Mapping[str, Any], *, now: str | None,
                    limitations: set[str]) -> bool:
    """Whether a review disposition or a due date removes this assertion.

    ``now`` is the caller's clock (a replay cutoff, or the newest review
    stamp the caller chose). This function does not read the wall clock.
    ``held`` and ``rejected`` are excluded. A due date ``le`` ``now`` is
    excluded. Anything else, including a due date with no ``now``, stays.
    """
    review = assertion.get("review") or {}
    disposition = review.get("disposition") if isinstance(review, Mapping) else None
    if disposition in ("held", "rejected"):
        limitations.add(
            "held_present" if disposition == "held" else "rejected_present")
        return True
    due = review.get("review_due_at") if isinstance(review, Mapping) else None
    if isinstance(due, str) and due and now is not None and le(due, now):
        limitations.add("review_expired_present")
        return True
    return False


def filter_interpretation_blocks(
    blocks: Sequence[Mapping[str, Any]],
    *,
    time_mode: str,
    recorded_cutoff: Any,
    limitations: set[str],
    replay_mode: str = "system_replay",
) -> list[dict[str, Any]]:
    """The semiconductor replay filter for interpretation blocks.

    Outside ``replay_mode`` every block is kept. Inside it, a block whose
    ``reviewed_at`` cannot be read is withheld (``undatable_excluded``) and
    a block reviewed after ``recorded_cutoff`` is withheld without a
    limitation — being outside the cutoff is the answer the caller asked
    for. Order is ``interpretation_id``.
    """
    chosen = []
    for block in blocks:
        if time_mode == replay_mode:
            reviewed = block.get("reviewed_at")
            if not readable(reviewed):
                limitations.add("undatable_excluded")
                continue
            if not within(reviewed, recorded_cutoff):
                continue
        chosen.append(dict(block))
    chosen.sort(key=lambda item: item.get("interpretation_id", ""))
    return chosen


def correction_lineage(assertion: Mapping[str, Any],
                       visible: Sequence[Mapping[str, Any]]) -> list[str]:
    """Walk ``correction.predecessor_revision`` over ``visible`` only.

    A predecessor that is not in ``visible`` is emitted as a pointer built
    from the last served row's theme and that revision, and the walk stops.
    A cycle stops. Nothing outside ``visible`` is read.
    """
    by_revision = {
        item.get("curation_revision"): item
        for item in visible if isinstance(item, Mapping)
    }
    lineage: list[str] = []
    seen = {assertion.get("curation_revision")}
    current: Mapping[str, Any] = assertion
    while True:
        correction = current.get("correction") or {}
        prior = correction.get("predecessor_revision") if isinstance(correction, Mapping) else None
        if not isinstance(prior, str) or not prior or prior in seen:
            break
        predecessor = by_revision.get(prior)
        if predecessor is None:
            prefix = _curation_source_ref(current).rsplit("/", 1)[0]
            lineage.append(f"{prefix}/{prior}")
            break
        seen.add(prior)
        lineage.append(_curation_source_ref(predecessor))
        current = predecessor
    return lineage


def collapse_syndicated(
    assertions: Sequence[Mapping[str, Any]],
    limitations: set[str],
) -> tuple[list[Mapping[str, Any]], dict[str, list[str]]]:
    """Drop an unambiguous syndicated copy and record it under its original.

    A row whose ``limitations.source_dependence`` is
    ``syndicated_copy_of:<publisher>`` collapses onto the single original
    with that publisher and the same predicate. Zero or several originals
    and the copy stays. The returned corroboration maps the original's
    ``curation_revision`` to the copy's source ref. ``syndicated_collapsed``
    is added once per collapsed copy.
    """
    def _dependence(item: Mapping[str, Any]) -> str:
        raw_limits = item.get("limitations") or {}
        if not isinstance(raw_limits, Mapping):
            return ""
        dependence = raw_limits.get("source_dependence") or ""
        return dependence if isinstance(dependence, str) else ""

    corroboration: dict[str, list[str]] = {}
    survivors: list[Mapping[str, Any]] = []
    for assertion in assertions:
        dependence = _dependence(assertion)
        if not dependence.startswith("syndicated_copy_of:"):
            survivors.append(assertion)
            continue
        upstream = dependence[len("syndicated_copy_of:"):]
        originals = [
            candidate for candidate in assertions
            if ((candidate.get("source") or {}).get("publisher") == upstream
                if isinstance(candidate.get("source"), Mapping) else False)
            and not _dependence(candidate).startswith("syndicated_copy_of:")
            and candidate.get("predicate") == assertion.get("predicate")
        ]
        if len(originals) == 1:
            original = originals[0]
            corroboration.setdefault(original["curation_revision"], []).append(
                _curation_source_ref(assertion))
            limitations.add("syndicated_collapsed")
        else:
            survivors.append(assertion)
    return survivors, corroboration


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
