"""Prophet research-journey notifications producer (B21 U2 — PURE half).

Enqueue-only projection over THREE existing owners — no new analysis
lifecycle, no scoring, no send, and in this half NO IO at all (A7: alerts
relay engine-emitted facts only; the IO/runner half is U3):

  - the subscription surface is the designated Supabase watchlist named
    "Prophet Research" (B21 contract §3(a)) on the exact fif pattern
    (engine/fif_saved_research_notifications.py:9-13, :71): the watchlists
    schema carries no kind/system/metadata column, so the list is identified
    by its verbatim stored name, and absence of the list or of a symbol on
    it IS "no subscription" — removing either is the unsubscribe.
  - the trigger inputs are typed reads supplied by the IO half: the B1
    episode ledger (engine/us_candidate_episode.py envelope shape), the
    previous and current B3 candidate-state projections
    (engine/prophet_candidate_state.py row shape), the session calendar and
    the existing alert_outbox rows. A missing/stale/unknown input is "no
    event" (the fif input law), never an exception.
  - the queue is the existing public.alert_outbox; delivery belongs to the
    drain (engine/alert_delivery_drain.py), never this module.

Identity (B21 contract §2, frozen): fire_event_id is the literal
concatenation "prophet|" kind "|" episode_id "|" from "->" to "|" b1_event_id
"|" user_id — no hashing, "|" major separator because the B1 episode_id is
itself a colon literal. Neither candidate_generation_id nor definition era
enters the id (thesis-monitor ruling: a definition change must not
re-notify); both ride the payload as provenance/display only.
UNIQUE(fire_event_id) makes replays no-ops; synthetic_alert_id mints one
uuid5 per user's Prophet watch on the fif pattern (:114-119, :232-238) under
a namespace DISTINCT from fif's. Every segment is a function of the B1
ledger alone (seat ruling F28 R1): for retracted/superseded the from side
is the B1 replay state immediately BEFORE the causing event, replayed in
B1's canonical order (known_at, source_system, source_event_id) with B1's
deferral of an event whose episode or relation is not yet placed — never
the previous B3 projection, which evolves between runs and would re-key
(and so re-send) the same notice. The replayed B1 state is shown through
the B3 lifecycle table below (contract §4: B3 is what the user was shown).
Routing identity (company_id, ticker) is the OPENED payload with every
CORRECTED patch of those two fields applied in replay order (F28 R10).

Eligibility (B21 contract §1, v1 closed set of kinds): episode_terminal,
emergence_triggered, corrected_material, retracted, superseded. Never:
OPENED (v1 seat ruling — episode_opened is not minted), OBSERVED,
EXPERT_EVENT_ATTACHED, REARM_SUPPRESSED, any quote/price/freshness change,
and any transition with UNESTIMABLE/UNAVAILABLE_DATA on either side —
absence of knowledge is not a journey change (typed `unknown_side`). A
STATE_TRANSITIONED is a cause only when B1 itself applies it — current
state ACTIVE, a terminal target, a non-empty terminal_reason; anything else
is `ineligible_event` (F28 R4). emergence_triggered also requires the
CURRENT lifecycle to be ACTIVE (F28 R4). Ratified contract deviation (F28
R8): for the emergence diff a prior emergence state that is absent or
UNESTIMABLE (B3's SOURCE_NOT_SUPPLIED default) counts as not triggered;
UNAVAILABLE_DATA on the prior side stays `unknown_side`. A projection_prev
READ_UNAVAILABLE derives nothing for the run (`prev_projection_unavailable`,
F28 R9).

Corrections (B21 contract §4 governs, F28 R5/R6): a correction kind
(corrected_material, retracted, superseded) corrects the ORIGINAL — the
latest prior notice of the same episode for the same user, of ANY kind
including emergence_triggered, "prior" meaning an earlier cause in B1
replay order. The original is resolved from this producer's own fire ids in
the alert_outbox READBACK and from the rows minted earlier in this run,
never from this run's derivation alone. Its fire id rides the payload as
`corrects_fire_event_id`. Branches on the original:
  - none -> `no_original`, nothing minted (a correction without an
    original is noise);
  - quarantined (failed, attempts >= 3, last_error ==
    "effect_unknown_after_smtp") -> `original_quarantined`, nothing minted:
    the original may already be in the reader's inbox, and the drain's
    at-most-once law forbids presuming either way;
  - producer-suppressed (suppressed, last_error ==
    "superseded_by_prophet_correction") -> `original_producer_suppressed`,
    nothing minted: an earlier correction already replaced it, and it is
    never re-read as a user opt-out;
  - sent -> the correction row only, in the copy that presumes receipt;
  - unsent (pending, deferred, failed under the drain retry cap of 3, and
    the residual failed-at-cap cell with any other last_error) -> ONE
    PlannedPatch suppressing the original AND the correction row in the
    same run, in the non-presuming copy; exactly one email can go out;
  - any other suppressed (user opt-out / category / address) -> the
    correction row anyway (the drain re-decides from live prefs; the
    producer holds no user state), in the non-presuming copy;
  - minted earlier in THIS run -> the original row is born suppressed
    (status "suppressed", last_error "superseded_by_prophet_correction",
    typed `original_superseded_in_run`) so its fire id still dedupes later
    runs, and the correction uses the non-presuming copy.
U3 must apply one plan's rows and patches in ONE transaction: a patch
without its correction row reads back as producer-suppressed, and that
correction would then never be minted. A retraction of an OBSERVED
relation leaves the episode tracked and says so (F28 R7).

not_after and recency (B21 contract §5 governs, F28 R2): not_after is the
end of the market session following the TRANSITION's own market_session —
the causing B1 event's known_at UTC date, B1's own session convention
(engine/us_candidate_episode.py opened_session = opened_at[:10]) — taken
from the session calendar; a Saturday or Sunday date (no session) resolves
through the latest earlier session's next-session end when that end lies
after it, while a weekday with no calendar row (holiday, calendar gap) is
unresolvable like any other miss. Unresolvable -> `not_after_unresolvable`; a not_after at or before
the run's now_utc (or no parsable now_utc) -> `stale_transition_at_mint`.
Neither mints a row: a six-month-old transition never mints.

The B3 source-state->lifecycle table is REPLICATED here (_LIFECYCLE_BY_SOURCE
mirrors engine/prophet_candidate_state.py:144-155 `_expected_lifecycle_state`
with no successor), never imported: this module imports NOTHING from engine/,
app/, lib/ or scripts/ — the pinned test asserts both the replication
equality against B3 and the import silence.

Determinism: identical inputs produce a byte-identical plan whatever their
input order — the ledger is replayed in B1's canonical order, rows are
sorted by (ticker, fired_at, kind, user_id, fire_event_id), patches by
fire_event_id, and every drop is counted under a typed SUPPRESSION_KEYS
bucket that fails closed rather than dropping silently.
"""
from __future__ import annotations

import re
import uuid as _uuid_mod
from dataclasses import dataclass, field, replace
from typing import Any

SCHEMA = "prophet.b21.journey_notifications/v1"
SOURCE = "macro.prophet_journey_notifications"
CATEGORY = "prophet_research_journey"
CHANNEL = "email"

# B21 contract §3(a): ONE verbatim stored system name, on the fif precedent
# (engine/fif_saved_research_notifications.py:68-71). The stored row is
# identified by this exact, case-sensitive name against the schema's unique
# (user_id, name) index.
DESIGNATED_LIST_NAME = "Prophet Research"

# The single place the tier literal appears (B21 U6): the payload carries it
# verbatim; the drain's entitlement decision consumes it
# (engine/alert_delivery_drain.py:513-520).
REQUIRES_TIER = "essential"

EVIDENCE_BASE = "https://www.mastermind-x.com"

# The Prophet surface anchor. A per-ticker deep link does not exist yet and
# is NOT invented here (recorded as a gap in the B21 return, not a guess).
EVIDENCE_PATH = "/us_stocks.html#us-standouts"

KIND_EPISODE_TERMINAL = "episode_terminal"
KIND_EMERGENCE_TRIGGERED = "emergence_triggered"
KIND_CORRECTED_MATERIAL = "corrected_material"
KIND_RETRACTED = "retracted"
KIND_SUPERSEDED = "superseded"
KINDS = (
    KIND_EPISODE_TERMINAL,
    KIND_EMERGENCE_TRIGGERED,
    KIND_CORRECTED_MATERIAL,
    KIND_RETRACTED,
    KIND_SUPERSEDED,
)

# The correction kinds (B21 contract §4): each references — and may patch —
# an ORIGINAL journey notice for the same user.
_CORRECTION_KINDS = frozenset(
    {KIND_CORRECTED_MATERIAL, KIND_RETRACTED, KIND_SUPERSEDED}
)

# A CORRECTED event is material only when its patch touches one of these B1
# PATCHABLE_FIELDS members (engine/us_candidate_episode.py:51-61); a patch
# on any other field alone is an ineligible_event.
MATERIAL_PATCH_FIELDS = ("terminal_reason", "ticker_at_observation")

# Typed suppression counts in a deterministic key order — fail closed, never
# a silent drop (the fif R3d pattern, :99-104). Plan-level keys count per
# (event, user) pair except no_subscriber, which counts once per event that
# reached zero subscribers; derive-level keys count per source occurrence.
SUPPRESSION_KEYS = (
    "read_unavailable",              # b1_events read READ_UNAVAILABLE -> zero events
    "prev_projection_unavailable",   # projection_prev READ_UNAVAILABLE -> zero events (F28 R9)
    "ineligible_event",              # B1 event seen but outside the v1 closed set
    "unknown_side",                  # unknown-state side, or no real TURN WATCH relation id
    "no_subscriber",                 # event's ticker on nobody's designated list
    "already_fired",                 # fid already in the outbox (typed mirror of duplicate_n)
    "banned_term",                   # glance text failed the persist-time guard
    "not_after_unresolvable",        # no calendar end for the transition's session (F28 R2)
    "stale_transition_at_mint",      # not_after already <= the run's now (F28 R2)
    "no_original",                   # correction kind with no original notice to correct
    "original_quarantined",          # original effect-unknown after SMTP; mint nothing
    "original_producer_suppressed",  # original already replaced by a correction (F28 R5)
    "original_superseded_in_run",    # original minted this run, born suppressed (F28 R5)
)

# The producer's own suppression reason (B21 contract §4): written on an
# original it supersedes, and read back as "already replaced", never as a
# user opt-out (F28 R5).
PRODUCER_SUPPRESSED_REASON = "superseded_by_prophet_correction"

# The drain's quarantine marker and retry cap
# (engine/alert_delivery_drain.py:107, :611-615).
_QUARANTINE_LAST_ERROR = "effect_unknown_after_smtp"
_DRAIN_RETRY_CAP = 3

# Glance-tier banned tokens — the thesis monitor's discipline
# (engine/thesis_condition_monitor.py:121) and fif's persist guard
# (engine/fif_saved_research_notifications.py:109-112). The mailer applies
# its own wider list at render time (app/mailer.py:1334-1337).
_BANNED_TERMS = ("falsif", "refut", "证伪")

# Machine tokens that must never enter glance text, checked
# case-insensitively at persist alongside _BANNED_TERMS.
_GLANCE_MACHINE_TOKENS = ("fire_event_id", "|")

# The B1 id shapes, matched on the id FORM, never as a lowercase substring
# of the composed glance (F28 R3: "HPE: ..." is a ticker, not an id): pee:
# event ids and peg: generation ids are a hex digest after the colon; pe:
# episode ids carry the "SEC:" security literal after it.
_MACHINE_ID_RE = re.compile(r"\b(?:pee?:[0-9a-f]|peg:[0-9a-f]|pe:SEC:)")

# A fixed, arbitrary namespace UUID for synthesizing alert_outbox.alert_id
# values (uuid5) from the conceptual "prophet_watch:<user_id>" identity —
# the fif pattern (:114-119). Distinct from fif's
# b1f0d2a4-7c39-5e81-9a2b-4d6e8f0a1c30 on purpose: one namespace per
# producer, so synthetic ids can never collide across categories. Never
# change this constant — doing so would re-mint every user's id.
_ALERT_ID_NAMESPACE = _uuid_mod.UUID("3f6b2d8e-9a41-5c07-b2e5-6d1f8a0c4b93")

READ_OK, READ_OK_ZERO, READ_UNAVAILABLE = (
    "READ_OK",
    "READ_OK_ZERO",
    "READ_UNAVAILABLE",
)

# ---------------------------------------------------------------------------
# Replicated B1/B3 vocabulary — read-model copies, never imports
# ---------------------------------------------------------------------------

# B1 TERMINAL_STATES (engine/us_candidate_episode.py:45): a
# STATE_TRANSITIONED event is an episode_terminal cause only when its target
# is one of these.
_TERMINAL_SOURCE_STATES = frozenset(
    {"RESOLVED", "INVALIDATED", "EXPIRED", "RETRACTED"}
)

# The B3 source-state -> lifecycle table, replicated from
# engine/prophet_candidate_state.py:144-155 (`_expected_lifecycle_state`
# with no successor): RESOLVED/EXPIRED collapse to CLOSED, INVALIDATED and
# RETRACTED keep their names, ACTIVE stays ACTIVE. A successor overrides
# every entry with SUPERSEDED (engine/prophet_candidate_state.py:147-148) —
# the replay below applies that override once IDENTITY_SUPERSEDED is placed.
# The pinned test asserts this table equals B3's own constants over B3's
# source states.
_LIFECYCLE_BY_SOURCE = {
    "ACTIVE": "ACTIVE",
    "RESOLVED": "CLOSED",
    "EXPIRED": "CLOSED",
    "INVALIDATED": "INVALIDATED",
    "RETRACTED": "RETRACTED",
}
_SUPERSEDED_LIFECYCLE = "SUPERSEDED"

# Absence of knowledge on either side of a transition is not a journey
# change (B21 contract §1): UNESTIMABLE (emergence/maturity) and
# UNAVAILABLE_DATA (lifecycle) are the two unknown tokens in play.
_UNKNOWN_STATES = frozenset({"UNESTIMABLE", "UNAVAILABLE_DATA"})

# F28 R8 (ratified contract deviation): on the PRIOR side of the emergence
# diff an UNESTIMABLE state (B3's SOURCE_NOT_SUPPLIED default) counts as
# "not triggered"; only the remaining unknown token is still unknown_side.
_PRIOR_EMERGENCE_UNKNOWN = _UNKNOWN_STATES - {"UNESTIMABLE"}

# B1 event types whose RETRACTED target counts as shown to the reader: the
# OPENED relation (the episode leaves the projection) or an OBSERVED
# relation (the episode stays tracked, F28 R7). A RETRACTED of an
# EXPERT_EVENT_ATTACHED relation is engine-internal and never surfaces.
_SHOWN_RELATION_TYPES = frozenset({"OPENED", "OBSERVED"})

# B1 replay deferral (engine/us_candidate_episode.py
# _project_validated_events): these event types apply only once their
# episode is OPENED, these only once their correction_of relation is placed;
# REARM_SUPPRESSED is a replay no-op that registers no relation.
_NEEDS_EPISODE = frozenset(
    {"OBSERVED", "EXPERT_EVENT_ATTACHED", "STATE_TRANSITIONED", "IDENTITY_SUPERSEDED"}
)
_NEEDS_RELATION = frozenset({"CORRECTED", "RETRACTED"})
_UNREGISTERED_TYPES = frozenset({"REARM_SUPPRESSED"})

# A real TURN WATCH relation id is a B1 event id: "pee:" + 64 hex
# (engine/us_candidate_episode.py:309). Anything else at the emergence
# source_ref site is unknown_side, never an event.
_RELATION_EVENT_ID_RE = re.compile(r"^pee:[0-9a-f]{64}$")

# RFC3339 UTC with a Z suffix (the B1 _timestamp normal form and the B3
# _RFC3339_UTC_RE shape, engine/prophet_candidate_state.py:36-38); the two
# groups give an order key with the fraction padded to microseconds.
_RFC3339_UTC_RE = re.compile(
    r"^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?:\.([0-9]{1,6}))?Z$"
)

_LEADING_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypedRead:
    state: str
    rows: list | None
    error_class: str | None = None


@dataclass(frozen=True)
class JourneyInputs:
    """The typed reads the IO half (U3) supplies; every read fails soft.

    b1_events must carry each subscribed episode's full ledger slice: the
    replay order, the from side and the correction originals are all
    resolved from it. now_utc is the run's clock for the mint-time recency
    gate (F28 R2); market_session is run provenance only — not_after comes
    from each transition's own session."""

    b1_events: TypedRead
    projection_prev: TypedRead
    projection_curr: TypedRead
    session_calendar: TypedRead
    existing_outbox: TypedRead
    candidate_generation_id: str | None = None
    market_session: str | None = None
    now_utc: str | None = None


@dataclass(frozen=True)
class JourneyEvent:
    kind: str
    episode_id: str
    company_id: str
    ticker: str
    from_state: str
    to_state: str
    b1_event_id: str
    fact_receipt: str | None
    definition_era: str | None
    condition_plain: str
    subject: str
    fired_at: str | None
    # The causing B1 event's own session (known_at UTC date): the not_after
    # anchor (F28 R2) and the payload's market_session.
    market_session: str | None
    # Provenance for the payload only; never part of the fire id (B21 §2).
    candidate_generation_id: str | None = None
    # The copy for a correction whose original never reached the reader
    # (F28 R5): no "you were shown", no "the earlier notice is withdrawn".
    # Empty means the presuming copy presumes nothing and serves both.
    condition_plain_unsent: str = ""


@dataclass(frozen=True)
class PlannedPatch:
    """One producer-side update of an ORIGINAL row this run supersedes."""

    fire_event_id: str
    status: str
    last_error: str


@dataclass(frozen=True)
class ProducerPlan:
    rows: list[dict]
    patches: list[PlannedPatch]
    users_n: int
    symbols_n: int
    events_n: int
    duplicate_n: int
    suppressed: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Identity — literal concatenation, no hashing
# ---------------------------------------------------------------------------


def fire_event_id(
    *,
    kind: str,
    episode_id: str,
    from_state: str,
    to_state: str,
    b1_event_id: str,
    user_id: str,
) -> str:
    """The FROZEN dedupe key (B21 §2): "prophet" joined on "|", the state
    pair joined on "->". UNIQUE(fire_event_id) makes replays no-ops."""
    return (
        f"prophet|{kind}|{episode_id}|{from_state}->{to_state}"
        f"|{b1_event_id}|{user_id}"
    )


def parse_fire_event_id(value: str) -> dict[str, str]:
    """Inverse of fire_event_id: exactly six "|"-separated parts with the
    literal "prophet" prefix token, the pair splits once on "->", enum
    tokens only, and from/to carry no colons. Malformed input raises
    ValueError, never guesses."""
    parts = str(value or "").split("|")
    if len(parts) != 6 or parts[0] != "prophet":
        raise ValueError(f"malformed prophet fire_event_id: {value!r}")
    kind, episode_id, pair, b1_event_id, user_id = parts[1:]
    if kind not in KINDS:
        raise ValueError(f"unknown prophet journey kind: {kind!r}")
    states = pair.split("->")
    if len(states) != 2 or not states[0] or not states[1]:
        raise ValueError(f"malformed state pair: {pair!r}")
    from_state, to_state = states
    if ":" in from_state or ":" in to_state:
        raise ValueError(f"state pair carries a colon: {pair!r}")
    if not episode_id or not b1_event_id or not user_id:
        raise ValueError(f"empty identity segment: {value!r}")
    return {
        "kind": kind,
        "episode_id": episode_id,
        "from_state": from_state,
        "to_state": to_state,
        "b1_event_id": b1_event_id,
        "user_id": user_id,
    }


def synthetic_alert_id(user_id: str) -> str:
    """Deterministic per-user synthetic alert_outbox.alert_id (uuid5 of the
    conceptual "prophet_watch:<user_id>" identity — the fif/thesis-monitor
    pattern). Stable across every event produced for the same user's watch;
    NOT a foreign key into any real Alerts-table row."""
    return str(
        _uuid_mod.uuid5(_ALERT_ID_NAMESPACE, f"prophet_watch:{user_id}")
    )


# ---------------------------------------------------------------------------
# Glance text — fixed templates, plain language only
# ---------------------------------------------------------------------------

# episode_terminal closing phrase by lifecycle token. The B1 terminal_reason
# free text never enters glance text; the lifecycle token picks the phrase.
_TERMINAL_PHRASES = {
    "CLOSED": "it ran its course",
    "INVALIDATED": "the setup no longer holds",
    "RETRACTED": "it was withdrawn",
}

_PATCH_PHRASES = {
    "terminal_reason": "the closing reason changed",
    "ticker_at_observation": "the ticker on record changed",
}

_SUBJECT_SHORT = {
    KIND_EPISODE_TERMINAL: "closed",
    KIND_EMERGENCE_TRIGGERED: "turn triggered",
    KIND_CORRECTED_MATERIAL: "correction",
    KIND_RETRACTED: "withdrawn",
    KIND_SUPERSEDED: "successor",
}


def _glance(
    kind: str,
    ticker: str,
    *,
    to_state: str = "",
    material_fields: tuple[str, ...] = (),
    relation_level: bool = False,
    presumes_receipt: bool = True,
) -> tuple[str, str]:
    """(condition_plain, subject) from the fixed templates. No values,
    scores, prices, percentages, slugs, episode ids or machine tokens by
    construction; the persist-time guard re-checks every string.
    presumes_receipt=False is the copy for a correction whose original the
    reader never received (F28 R5); relation_level marks a retraction of an
    OBSERVED relation, after which the name is still tracked (F28 R7)."""
    subject_short = _SUBJECT_SHORT[kind] if kind in _SUBJECT_SHORT else ""
    if kind == KIND_EPISODE_TERMINAL:
        phrase = _TERMINAL_PHRASES.get(to_state, _TERMINAL_PHRASES["CLOSED"])
        condition = (
            f"{ticker}: the Prophet research journey you follow has closed "
            f"— {phrase}."
        )
    elif kind == KIND_EMERGENCE_TRIGGERED:
        condition = f"{ticker}: the turn you were watching has triggered."
    elif kind == KIND_CORRECTED_MATERIAL:
        whats = [
            _PATCH_PHRASES[field]
            for field in MATERIAL_PATCH_FIELDS
            if field in material_fields
        ]
        what = " and ".join(whats) if whats else _PATCH_PHRASES["terminal_reason"]
        if presumes_receipt:
            condition = (
                f"{ticker}: a correction to the journey you were shown — {what}."
            )
        else:
            condition = (
                f"{ticker}: a correction to this research journey — {what}."
            )
    elif kind == KIND_RETRACTED:
        if relation_level:
            condition = (
                f"{ticker}: an earlier observation was withdrawn; the name "
                f"remains tracked."
            )
            subject_short = "observation withdrawn"
        elif presumes_receipt:
            condition = (
                f"{ticker}: this name is no longer tracked; the earlier notice "
                f"is withdrawn."
            )
        else:
            condition = f"{ticker}: this name is no longer tracked."
    elif kind == KIND_SUPERSEDED:
        # The successor's raw episode id is a machine string and never
        # enters glance text (fif payload law: no slugs, no ids).
        condition = (
            f"{ticker}: this opportunity continues under a successor identity."
        )
    else:
        raise ValueError(f"unknown prophet journey kind: {kind!r}")
    subject = f"{ticker} Prophet journey: {subject_short}"
    return condition, subject


def _glance_is_clean(text: Any) -> bool:
    """Persist-time guard for every glance-tier string: banned terms and
    machine tokens (case-insensitive) and the B1 id shapes (on the id form,
    F28 R3) fail closed to a typed suppression, never a silent send of
    engine vocabulary."""
    value = str(text or "")
    if not value:
        return False
    lowered = value.lower()
    if any(term in lowered for term in _BANNED_TERMS):
        return False
    if any(token in lowered for token in _GLANCE_MACHINE_TOKENS):
        return False
    return _MACHINE_ID_RE.search(value) is None


# ---------------------------------------------------------------------------
# Payload — the compose contract fields plus the B21 provenance set
# ---------------------------------------------------------------------------


def evidence_url(evidence_base: str = EVIDENCE_BASE) -> str:
    """The Prophet surface anchor; a per-ticker deep link does not exist and
    is not invented here."""
    return f"{str(evidence_base).rstrip('/')}{EVIDENCE_PATH}"


def _event_date(fired_at: str | None) -> str | None:
    """The causing event's YYYY-MM-DD; a fired_at without a leading real
    date records None, never a guessed prefix."""
    text = str(fired_at or "")
    match = _LEADING_DATE_RE.match(text[:10])
    if not match:
        return None
    return text[:10]


def compose_payload(
    event: JourneyEvent,
    *,
    user_id: str,
    not_after: str | None,
    evidence_base: str = EVIDENCE_BASE,
    corrects_fire_event_id: str | None = None,
) -> dict:
    """Exactly the frozen key set: the compose_alert contract fields
    (app/mailer.py:1379-1430), the category the drain filters on
    (engine/alert_delivery_drain.py:495-507), and the B21 provenance set
    (not_after, fact_receipt, corrects_fire_event_id,
    candidate_generation_id, market_session, definition_era, kind, source,
    schema). requires_tier is REQUIRES_TIER on every row — the single
    constant site. corrects_fire_event_id is the ORIGINAL's fire id for
    THIS user (resolved by plan_enqueue from the readback, F28 R6), or None
    for non-correction kinds. user_id is the row's subscriber; it enters no
    payload key."""
    del user_id  # the subscriber is the row's user_id, never a payload key
    return {
        "ticker": event.ticker,
        "condition_plain": event.condition_plain,
        "evidence_url": evidence_url(evidence_base),
        "subject": event.subject,
        "fired_at": event.fired_at,
        "category": CATEGORY,
        "event_date": _event_date(event.fired_at),
        "requires_tier": REQUIRES_TIER,
        "not_after": not_after,
        "fact_receipt": event.fact_receipt,
        "corrects_fire_event_id": corrects_fire_event_id,
        "candidate_generation_id": event.candidate_generation_id,
        "market_session": event.market_session,
        "definition_era": event.definition_era,
        "kind": event.kind,
        "source": SOURCE,
        "schema": SCHEMA,
    }


# ---------------------------------------------------------------------------
# Subscriptions — the designated-list per-user partition (no-leak)
# ---------------------------------------------------------------------------


def build_subscriptions(
    list_rows: list, symbol_rows: list
) -> dict[str, frozenset[str]]:
    """{user_id: frozenset(symbols on THAT user's designated list)} — the
    fif per-user partition (:457-475) with the designated-name filter inside
    the pure function so a mixed list_rows read can never leak another
    list's symbols. Only rows whose watchlist_id names a designated list
    enter; a symbol row keyed to anything else is ignored."""
    user_by_list: dict[str, str] = {}
    for row in list_rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("name") or "") != DESIGNATED_LIST_NAME:
            continue
        list_id = str(row.get("id") or "")
        user_id = str(row.get("user_id") or "")
        if not list_id or not user_id:
            continue
        user_by_list[list_id] = user_id
    buckets: dict[str, set[str]] = {}
    for row in symbol_rows or []:
        if not isinstance(row, dict):
            continue
        user_id = user_by_list.get(str(row.get("watchlist_id") or ""))
        symbol = str(row.get("symbol") or "").strip().upper()
        if not user_id or not symbol:
            continue
        buckets.setdefault(user_id, set()).add(symbol)
    return {user_id: frozenset(symbols) for user_id, symbols in buckets.items()}


# ---------------------------------------------------------------------------
# B1 replay — canonical order, deferral, identity
# ---------------------------------------------------------------------------


def _rows(read: TypedRead) -> list:
    """A read's rows as a list; an unavailable read has none. The caller's
    counts keep the drop typed (the read states themselves are the IO
    half's to report)."""
    if not isinstance(read, TypedRead):
        return []
    rows = read.rows
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _utc_key(value: Any) -> tuple[str, str] | None:
    """An order key for an RFC3339 UTC "Z" instant (the fraction padded to
    microseconds), or None when the value is not one."""
    match = _RFC3339_UTC_RE.fullmatch(str(value or "").strip())
    if not match:
        return None
    return match.group(1), (match.group(2) or "").ljust(6, "0")


def _replay_order(envelopes: list[dict]) -> tuple[list[dict], int]:
    """(applied envelopes in B1 replay order, unplaced count). B1's canonical
    order is (known_at, source_system, source_event_id)
    (engine/us_candidate_episode.py `_event_order`), event_id breaking any
    residual tie; an event whose episode is not yet OPENED, or whose
    correction_of relation is not yet placed, waits for a later pass exactly
    as B1's `_project_validated_events` defers it. An envelope with no
    event_id or no RFC3339 known_at, and any event still waiting when a pass
    places nothing, is unplaced (counted ineligible by the caller). A
    repeated identical event (same content-addressed event_id) is placed
    once and costs no count."""
    unique: dict[str, dict] = {}
    unplaced = 0
    for envelope in envelopes:
        event_id = str(envelope.get("event_id") or "")
        if not event_id or _utc_key(envelope.get("known_at")) is None:
            unplaced += 1
            continue
        unique.setdefault(event_id, envelope)
    pending = sorted(
        unique.values(),
        key=lambda row: (
            _utc_key(row.get("known_at")),
            str(row.get("source_system") or ""),
            str(row.get("source_event_id") or ""),
            str(row.get("event_id") or ""),
        ),
    )
    applied: list[dict] = []
    opened: set[str] = set()
    registered: set[str] = set()
    while pending:
        waiting: list[dict] = []
        for envelope in pending:
            event_type = str(envelope.get("event_type") or "")
            episode_id = str(envelope.get("episode_id") or "")
            if event_type in _NEEDS_EPISODE and episode_id not in opened:
                waiting.append(envelope)
                continue
            if (
                event_type in _NEEDS_RELATION
                and str(envelope.get("correction_of") or "") not in registered
            ):
                waiting.append(envelope)
                continue
            applied.append(envelope)
            if event_type == "OPENED" and episode_id:
                opened.add(episode_id)
            if event_type not in _UNREGISTERED_TYPES:
                registered.add(str(envelope.get("event_id") or ""))
        if len(waiting) == len(pending):
            unplaced += len(waiting)
            break
        pending = waiting
    return applied, unplaced


def _episode_identity(applied: list[dict]) -> dict[str, tuple[str, str]]:
    """{episode_id: (company_id, ticker)} from the episodes' OPENED payloads
    (engine/us_candidate_episode.py:394-452 — ticker_at_observation and
    company_id are required there), with every CORRECTED patch of either
    field applied in replay order (F28 R10), so a corrected ticker routes to
    its own subscribers. An event whose episode OPENED is absent from the
    read cannot be routed and is counted ineligible at derivation, never
    silently dropped."""
    identity: dict[str, tuple[str, str]] = {}
    for envelope in applied:
        event_type = str(envelope.get("event_type") or "")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            continue
        episode_id = str(envelope.get("episode_id") or "")
        if event_type == "OPENED":
            company_id = str(payload.get("company_id") or "").strip()
            ticker = str(payload.get("ticker_at_observation") or "").strip()
            if episode_id and company_id and ticker:
                identity[episode_id] = (company_id, ticker)
        elif event_type == "CORRECTED" and episode_id in identity:
            patch = payload.get("patch")
            if not isinstance(patch, dict):
                continue
            company_id, ticker = identity[episode_id]
            patched_company = patch.get("company_id")
            if isinstance(patched_company, str) and patched_company.strip():
                company_id = patched_company.strip()
            patched_ticker = patch.get("ticker_at_observation")
            if isinstance(patched_ticker, str) and patched_ticker.strip():
                ticker = patched_ticker.strip()
            identity[episode_id] = (company_id, ticker)
    return identity


def _session_of(envelope: dict | None) -> str | None:
    """The causing B1 event's market session: its known_at UTC date (B1's
    own convention, opened_session = opened_at[:10]); None when absent."""
    if envelope is None:
        return None
    known_at = str(envelope.get("known_at") or "").strip()
    if _utc_key(known_at) is None:
        return None
    return known_at[:10]


def _emergence_by_episode(rows: list[dict]) -> dict[str, str]:
    """{episode_id: emergence state token} from B3 projection rows (the
    nested emergence_state.state site, engine/prophet_candidate_state.py:345)."""
    out: dict[str, str] = {}
    for row in rows:
        episode_id = str(row.get("episode_id") or "")
        if not episode_id:
            continue
        emergence = row.get("emergence_state")
        state = (
            str(emergence.get("state") or "")
            if isinstance(emergence, dict)
            else ""
        )
        if state:
            out[episode_id] = state
    return out


# ---------------------------------------------------------------------------
# Derivation — eligibility over the typed reads
# ---------------------------------------------------------------------------


def derive_events(inputs: JourneyInputs) -> tuple[list[JourneyEvent], dict[str, int]]:
    """The eligible journey events plus typed counts. A READ_UNAVAILABLE on
    b1_events or on projection_prev yields ZERO events and its typed count —
    never an exception (input law, F28 R9). The B1 ledger is replayed in
    canonical order and each event's from side is the replayed state just
    before it (F28 R1); events come back in replay order."""
    counts = {key: 0 for key in SUPPRESSION_KEYS}
    if inputs.b1_events.state == READ_UNAVAILABLE:
        counts["read_unavailable"] = 1
        return [], counts
    if inputs.projection_prev.state == READ_UNAVAILABLE:
        counts["prev_projection_unavailable"] = 1
        return [], counts

    applied, unplaced = _replay_order(_rows(inputs.b1_events))
    counts["ineligible_event"] += unplaced
    rank = {str(envelope["event_id"]): index for index, envelope in enumerate(applied)}
    by_event_id = {str(envelope["event_id"]): envelope for envelope in applied}
    identity = _episode_identity(applied)
    prev_emergence = _emergence_by_episode(_rows(inputs.projection_prev))

    events: list[JourneyEvent] = []

    def _stamp(
        *,
        kind: str,
        episode_id: str,
        from_state: str,
        to_state: str,
        cause_id: str,
        envelope: dict | None,
        material_fields: tuple[str, ...] = (),
        relation_level: bool = False,
    ) -> JourneyEvent:
        company_id, ticker = identity[episode_id]
        condition_plain, subject = _glance(
            kind,
            ticker,
            to_state=to_state,
            material_fields=material_fields,
            relation_level=relation_level,
        )
        condition_plain_unsent, _ = _glance(
            kind,
            ticker,
            to_state=to_state,
            material_fields=material_fields,
            relation_level=relation_level,
            presumes_receipt=False,
        )
        return JourneyEvent(
            kind=kind,
            episode_id=episode_id,
            company_id=company_id,
            ticker=ticker,
            from_state=from_state,
            to_state=to_state,
            b1_event_id=cause_id,
            fact_receipt=(
                str(envelope.get("content_sha256") or "") or None
                if envelope is not None
                else None
            ),
            definition_era=(
                str(envelope.get("definition_era") or "") or None
                if envelope is not None
                else None
            ),
            condition_plain=condition_plain,
            subject=subject,
            fired_at=(
                str(envelope.get("recorded_at") or "") or None
                if envelope is not None
                else None
            ),
            market_session=_session_of(envelope),
            candidate_generation_id=inputs.candidate_generation_id,
            condition_plain_unsent=condition_plain_unsent,
        )

    # -- B1 command events, in replay order -------------------------------
    # Per-episode replayed state: [B1 source state, superseded?]. The from
    # side of a retracted/superseded notice is this state immediately
    # BEFORE its causing event, never the previous projection (F28 R1).
    replayed: dict[str, list] = {}
    for envelope in applied:
        event_id = str(envelope["event_id"])
        event_type = str(envelope.get("event_type") or "")
        episode_id = str(envelope.get("episode_id") or "")
        payload = envelope.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        if event_type == "OPENED":
            replayed.setdefault(episode_id, ["ACTIVE", False])
            # v1 seat ruling: episode_opened is never minted.
            counts["ineligible_event"] += 1
            continue
        if episode_id not in identity or episode_id not in replayed:
            counts["ineligible_event"] += 1
            continue
        state = replayed[episode_id]
        before = (
            _SUPERSEDED_LIFECYCLE
            if state[1]
            else _LIFECYCLE_BY_SOURCE.get(state[0], state[0])
        )

        if event_type == "STATE_TRANSITIONED":
            target = str(payload.get("episode_state") or "")
            if target not in _TERMINAL_SOURCE_STATES:
                # A non-terminal target (ACTIVE included) or a missing or
                # unknown episode_state is not a journey notice (F28 R4).
                counts["ineligible_event"] += 1
                continue
            reason = payload.get("terminal_reason")
            if state[0] != "ACTIVE" or not (
                isinstance(reason, str) and reason.strip()
            ):
                # B1 applies a transition only from ACTIVE with a reason; a
                # second terminal or a reasonless one changes nothing.
                counts["ineligible_event"] += 1
                continue
            state[0] = target
            events.append(
                _stamp(
                    kind=KIND_EPISODE_TERMINAL,
                    episode_id=episode_id,
                    from_state=_LIFECYCLE_BY_SOURCE["ACTIVE"],
                    to_state=_LIFECYCLE_BY_SOURCE[target],
                    cause_id=event_id,
                    envelope=envelope,
                )
            )
        elif event_type == "CORRECTED":
            patch = payload.get("patch")
            patch = patch if isinstance(patch, dict) else {}
            material = tuple(
                field for field in MATERIAL_PATCH_FIELDS if field in patch
            )
            if not material:
                counts["ineligible_event"] += 1
                continue
            events.append(
                _stamp(
                    kind=KIND_CORRECTED_MATERIAL,
                    episode_id=episode_id,
                    from_state="NONE",
                    to_state="corrected_material",
                    cause_id=event_id,
                    envelope=envelope,
                    material_fields=material,
                )
            )
        elif event_type == "RETRACTED":
            target_envelope = by_event_id.get(
                str(envelope.get("correction_of") or "")
            )
            target_type = (
                str(target_envelope.get("event_type") or "")
                if target_envelope is not None
                else ""
            )
            if target_type not in _SHOWN_RELATION_TYPES:
                counts["ineligible_event"] += 1
                continue
            from_state = before
            events.append(
                _stamp(
                    kind=KIND_RETRACTED,
                    episode_id=episode_id,
                    from_state=from_state,
                    to_state="RETRACTED",
                    cause_id=event_id,
                    envelope=envelope,
                    relation_level=target_type == "OBSERVED",
                )
            )
        elif event_type == "IDENTITY_SUPERSEDED":
            successor = payload.get("successor_episode_id")
            if not (
                isinstance(successor, str)
                and successor.strip()
                and successor != episode_id
            ):
                counts["ineligible_event"] += 1
                continue
            from_state = before
            state[1] = True
            events.append(
                _stamp(
                    kind=KIND_SUPERSEDED,
                    episode_id=episode_id,
                    from_state=from_state,
                    to_state=_SUPERSEDED_LIFECYCLE,
                    cause_id=event_id,
                    envelope=envelope,
                )
            )
        else:
            # OBSERVED, EXPERT_EVENT_ATTACHED, REARM_SUPPRESSED and anything
            # unknown: seen, counted, never minted.
            counts["ineligible_event"] += 1

    # -- emergence diff across projection generations ----------------------
    for row in _rows(inputs.projection_curr):
        episode_id = str(row.get("episode_id") or "")
        emergence = row.get("emergence_state")
        state_token = (
            str(emergence.get("state") or "")
            if isinstance(emergence, dict)
            else ""
        )
        if state_token != "TRIGGERED":
            continue
        # A TRIGGERED-to-TRIGGERED repeat is no journey change and costs no
        # count. F28 R8: an absent or UNESTIMABLE prior counts as not
        # triggered; an UNAVAILABLE_DATA prior is still an unknown side.
        prior_state = prev_emergence.get(episode_id)
        if prior_state == "TRIGGERED":
            continue
        if prior_state in _PRIOR_EMERGENCE_UNKNOWN:
            counts["unknown_side"] += 1
            continue
        source = emergence if isinstance(emergence, dict) else {}
        relation_id = str(source.get("source_ref") or "")
        if not _RELATION_EVENT_ID_RE.fullmatch(relation_id):
            # No real TURN WATCH relation id at the site B3 fills
            # (engine/prophet_candidate_state.py:1231): unknown side.
            counts["unknown_side"] += 1
            continue
        lifecycle = row.get("episode_lifecycle")
        lifecycle_state = (
            str(lifecycle.get("state") or "")
            if isinstance(lifecycle, dict)
            else ""
        )
        if lifecycle_state in _UNKNOWN_STATES:
            counts["unknown_side"] += 1
            continue
        if lifecycle_state != "ACTIVE":
            # F28 R4: a turn on a closed, withdrawn or superseded journey is
            # not a notice.
            counts["ineligible_event"] += 1
            continue
        if episode_id not in identity:
            counts["ineligible_event"] += 1
            continue
        events.append(
            _stamp(
                kind=KIND_EMERGENCE_TRIGGERED,
                episode_id=episode_id,
                from_state="NONE",
                to_state="TRIGGERED",
                cause_id=relation_id,
                envelope=by_event_id.get(relation_id),
            )
        )

    unranked = len(rank)
    events.sort(
        key=lambda event: (
            rank.get(event.b1_event_id, unranked),
            event.kind,
            event.episode_id,
            event.b1_event_id,
        )
    )
    return events, counts


# ---------------------------------------------------------------------------
# not_after — the stale-mandatory-fact bound (B21 contract §5, F28 R2)
# ---------------------------------------------------------------------------


def _session_end(calendar_rows: list[dict], market_session: str | None) -> str | None:
    """The end of the session following `market_session`, VERBATIM from the
    calendar: the row for that session when its value is one RFC3339 UTC
    instant. Anything else — no row for that session (weekend, holiday or a
    calendar gap), conflicting or unparsable values — is None (fail closed,
    `not_after_unresolvable`; seat ruling F28 R2 — no neighbouring-session
    fallback)."""
    session = str(market_session or "")
    if not _LEADING_DATE_RE.fullmatch(session):
        return None
    by_session: dict[str, set[str]] = {}
    for row in calendar_rows:
        row_session = str(row.get("market_session") or "")
        if not _LEADING_DATE_RE.fullmatch(row_session):
            continue
        value = str(row.get("next_session_end_utc") or "").strip()
        by_session.setdefault(row_session, set()).add(value)

    def _single(values: set[str]) -> str | None:
        if len(values) != 1:
            return None
        (value,) = values
        return value if _utc_key(value) is not None else None

    if session in by_session:
        return _single(by_session[session])
    return None


# ---------------------------------------------------------------------------
# The enqueue plan
# ---------------------------------------------------------------------------


def plan_enqueue(
    events: list[JourneyEvent],
    subscriptions: dict[str, frozenset[str]],
    *,
    inputs: JourneyInputs,
    existing_outbox_rows: list,
    evidence_base: str = EVIDENCE_BASE,
) -> ProducerPlan:
    """One row per (event, user) whose ticker is on the user's own
    designated list; ids already present in alert_outbox (or already minted
    this run) count as duplicates. A row needs a resolvable not_after that
    is still ahead of the run's now_utc (F28 R2). Correction kinds resolve
    their ORIGINAL from the readback and this run's rows (F28 R6) and branch
    on its state (contract §4, F28 R5); a user never sees another user's
    row — row["user_id"] is always the subscriber, and both the fire id and
    the original lookup embed the user."""
    rows: list[dict] = []
    patches: dict[str, PlannedPatch] = {}
    duplicate_n = 0
    suppressed = {key: 0 for key in SUPPRESSION_KEYS}

    # B1 replay rank: "prior" for the corrects chain means an earlier cause.
    rank: dict[str, int] = {}
    if inputs.b1_events.state != READ_UNAVAILABLE:
        applied, _ = _replay_order(_rows(inputs.b1_events))
        rank = {str(envelope["event_id"]): index for index, envelope in enumerate(applied)}

    existing_by_fid: dict[str, dict] = {}
    for row in existing_outbox_rows or []:
        if not isinstance(row, dict):
            continue
        fid = str(row.get("fire_event_id") or "")
        if fid:
            existing_by_fid.setdefault(fid, row)

    # This producer's own notices per (episode, user), from the readback.
    notices: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for fid in sorted(existing_by_fid):
        try:
            parts = parse_fire_event_id(fid)
        except ValueError:
            continue
        position = rank.get(parts["b1_event_id"])
        if position is None:
            continue
        notices.setdefault((parts["episode_id"], parts["user_id"]), []).append(
            (position, fid)
        )

    now_key = _utc_key(inputs.now_utc)
    calendar_rows = _rows(inputs.session_calendar)
    in_run: dict[str, dict] = {}

    unranked = len(rank)
    ordered = sorted(
        events,
        key=lambda event: (
            rank.get(event.b1_event_id, unranked),
            event.ticker,
            str(event.fired_at or ""),
            event.kind,
            event.episode_id,
            event.b1_event_id,
        ),
    )
    user_ids = sorted(subscriptions)

    candidates: list[tuple[JourneyEvent, str]] = []
    for event in ordered:
        ticker = str(event.ticker or "").strip().upper()
        watchers = [
            user_id
            for user_id in user_ids
            if ticker in subscriptions.get(user_id, frozenset())
        ]
        if not watchers:
            suppressed["no_subscriber"] += 1
            continue
        for user_id in watchers:
            candidates.append((event, user_id))

    for event, user_id in candidates:
        fid = fire_event_id(
            kind=event.kind,
            episode_id=event.episode_id,
            from_state=event.from_state,
            to_state=event.to_state,
            b1_event_id=event.b1_event_id,
            user_id=user_id,
        )
        if fid in existing_by_fid or fid in in_run:
            duplicate_n += 1
            suppressed["already_fired"] += 1
            continue
        unsent_copy = event.condition_plain_unsent or event.condition_plain
        if (
            not _glance_is_clean(event.condition_plain)
            or not _glance_is_clean(unsent_copy)
            or not _glance_is_clean(event.subject)
        ):
            suppressed["banned_term"] += 1
            continue
        not_after = _session_end(calendar_rows, event.market_session)
        if not_after is None:
            suppressed["not_after_unresolvable"] += 1
            continue
        if now_key is None or _utc_key(not_after) <= now_key:
            # The transition's staleness bound has passed (or the run has
            # no clock to prove it has not): never mint an old fact.
            suppressed["stale_transition_at_mint"] += 1
            continue

        condition_plain = event.condition_plain
        original_fid = None
        if event.kind in _CORRECTION_KINDS:
            position = rank.get(event.b1_event_id)
            prior = [
                notice
                for notice in notices.get((event.episode_id, user_id), [])
                if position is not None and notice[0] < position
            ]
            if not prior:
                suppressed["no_original"] += 1
                continue
            original_fid = max(prior)[1]
            if original_fid in in_run:
                # The original was minted earlier in this run and never left
                # the outbox: it is born suppressed, and the correction says
                # nothing about a notice the reader never received.
                in_run[original_fid]["status"] = "suppressed"
                in_run[original_fid]["last_error"] = PRODUCER_SUPPRESSED_REASON
                suppressed["original_superseded_in_run"] += 1
                condition_plain = unsent_copy
            else:
                original = existing_by_fid[original_fid]
                status = str(original.get("status") or "")
                attempts = original.get("attempts")
                attempts = attempts if isinstance(attempts, int) else 0
                last_error = str(original.get("last_error") or "")
                if status == "suppressed" and last_error == PRODUCER_SUPPRESSED_REASON:
                    # Producer-suppressed: an earlier correction already
                    # replaced this original. Never the opt-out branch.
                    suppressed["original_producer_suppressed"] += 1
                    continue
                if (
                    status == "failed"
                    and attempts >= _DRAIN_RETRY_CAP
                    and last_error == _QUARANTINE_LAST_ERROR
                ):
                    # Quarantined original: the effect is unknown, so minting
                    # a correction that presumes receipt converts an unknown
                    # into an assertion. Nothing is minted for this pair.
                    suppressed["original_quarantined"] += 1
                    continue
                if status == "sent":
                    # Never touch the original; the correction row only.
                    pass
                elif status == "suppressed":
                    # User opt-out / category / address: mint anyway, the
                    # drain re-decides from live prefs; nothing was received.
                    condition_plain = unsent_copy
                else:
                    # pending / deferred / failed under the retry cap — and
                    # the residual failed-at-cap cell with a definitive
                    # error: suppress the original AND insert the correction
                    # in the same run, so exactly one email can go out.
                    patches[original_fid] = PlannedPatch(
                        fire_event_id=original_fid,
                        status="suppressed",
                        last_error=PRODUCER_SUPPRESSED_REASON,
                    )
                    condition_plain = unsent_copy

        row = {
            "user_id": user_id,
            "alert_id": synthetic_alert_id(user_id),
            "fire_event_id": fid,
            "channel": CHANNEL,
            "status": "pending",
            "attempts": 0,
            "last_error": None,
            "payload": compose_payload(
                replace(event, condition_plain=condition_plain),
                user_id=user_id,
                not_after=not_after,
                evidence_base=evidence_base,
                corrects_fire_event_id=original_fid,
            ),
        }
        rows.append(row)
        in_run[fid] = row
        position = rank.get(event.b1_event_id)
        if position is not None:
            notices.setdefault((event.episode_id, user_id), []).append(
                (position, fid)
            )

    rows.sort(
        key=lambda row: (
            str(row["payload"].get("ticker") or ""),
            str(row["payload"].get("fired_at") or ""),
            str(row["payload"].get("kind") or ""),
            str(row["user_id"]),
            str(row["fire_event_id"]),
        )
    )
    return ProducerPlan(
        rows=rows,
        patches=[patches[fid] for fid in sorted(patches)],
        users_n=len(subscriptions),
        symbols_n=sum(len(symbols) for symbols in subscriptions.values()),
        events_n=len(candidates),
        duplicate_n=duplicate_n,
        suppressed=suppressed,
    )
