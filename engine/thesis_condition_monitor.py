"""Thesis condition monitor (F11 packet B-F11-1).

Pure projection over the EXISTING tripwire latch machine
(engine/falsifier_tripwires.py) -- no new analysis lifecycle, no scoring, no send.

Provenance of the two committed files this module reads (round-3 review MINOR-2:
the prior docstring wrongly claimed BOTH files are render-produced -- measured
against the actual code, only one is):
  - data/cycle_ontology/falsifiers.json is AUTHORED input -- "the compiled DSL
    registry" itself (engine/falsifier_tripwires.py:5). It is NOT produced by
    this repo's render lane; it is read by it.
  - data/cycle_ontology/tripwire_state.json IS produced by the render lane: it
    is the persisted latch state written by
    `falsifier_tripwires.evaluate_and_persist()`, called from
    `.github/workflows/render.yml:946` -> `scripts/build_cycle.py:311-321`.
This module joins both to active Supabase Thesis Objects BY SUBJECT, and enqueues one
public.alert_outbox row per not-yet-notified FIRED window. Delivery belongs to F08
(scripts/drain_alert_outbox.py). Notification latency is <= one nightly cycle after the
render that latched the fire. human_research_only: informational; no trading authority,
no sizing, no position advice.

Schema note (verified against the actual reviewed migration, `gh pr diff 502 -R
mastermindx-market-intelligence/mastermind-terminal -- supabase`, 2026-09-06): the
merged/reviewed schema defines exactly two tables, `public.theses` (the head/subscription
row -- an active thesis IS the user's standing "watch") and `public.thesis_versions`
(the immutable revision ledger, `transition`/`previous_version`, no `amended_from`
field). There is no separate `thesis_conditions` table anywhere in that migration or in
mastermind-terminal's merged `supabase/migrations/` (`gh api .../contents/supabase/migrations`
lists only 0001-0010; a code search for `thesis_conditions` in that repo returns zero
hits). A subscription's "condition version" IS `theses.current_version` /
`thesis_versions.version` -- there is no second, more-granular version to key off. This
module therefore keys `fire_event_id` off the tripwire's own identity ONLY
(META-CEO RULING B-F11-1 round-3 blocker 3) -- `thesis_version`/`current_version` is
carried on the payload for DISPLAY only and is never hashed. If a later migration adds
a genuine `thesis_conditions` table this module must be revisited; until then treating
one as existing would be inventing schema, not implementing spec.

condition_plain vs engine_window_plain (META-CEO RULING B-F11-1 round-3 blocker 1):
condition_plain is the USER's OWN falsifier text(s), read verbatim from
`thesis_versions.content.falsifiers` -- never the engine's tripwire `claim`. The
engine's own claim about the cycle is carried SEPARATELY as `engine_window_plain`
(Tier-2 detail only; may contain stats/abbreviations the glance-tier text may not).
Presenting the engine's claim as though it were the user's own condition puts words
in the user's mouth and was BLOCKER 1 of the round-2 review.

alert_outbox row shape (META-CEO RULING M1): the enqueued row's columns match
`public.alert_outbox` byte-for-byte per terminal PR #513's migration
`supabase/migrations/0013_alert_runs_outbox.sql` (id, user_id, alert_id,
fire_event_id, channel, status, payload, attempts, last_error, deliver_after,
delivered_at, created_at -- this module supplies user_id/alert_id/fire_event_id/
channel/status/payload/attempts and leaves the rest to column defaults). `alert_id`
is typed `uuid` in that migration and there is no real per-position Alerts-table row
backing a thesis-condition fire, so the conceptual synthetic identity
"thesis:<thesis_id>" (one alert_id per thesis, stable across every fire it produces)
is rendered through `uuid5` rather than stored as the literal string, which the
`uuid` column would reject -- see `synthetic_alert_id()`.

Glance-tier subject display (META-CEO RULING M3, round-3 review BLOCKER 1): the
committed falsifiers.json corpus carries no human `label` field on any entry
today. Title-casing the raw internal cycle slug (e.g. 'spx' -> 'Spx', 'pgms' ->
'Pgms', 'em-equities' -> 'Em Equities') is NOT a genuine plain-language label --
it is still the internal slug/abbreviation, merely reformatted, and is exactly
the class of untranslated engine jargon the plain-language law bans from the
glance tier. `_glance_subject()` therefore uses a window's `label` field only
when the corpus actually supplies one; a TICKER symbol (a real, universally-
shown market identifier) is always safe and is used directly; a CYCLE-scope
window with no `label` falls back to a fully-translated generic sentence that
never names the cycle at all, in both EN and ZH.

Disclosure (META-CEO RULING M1): terminal's alerts_engine.py guards its own
per-position fires with a "guarded one-shot disarm" PATCH against the fired alert
row (Freeze `research/MARKET_ONTOLOGY_F08_ARCHITECTURE_FREEZE_2026-09-05.md:60`).
That mechanism does NOT apply here. This module's fires are re-derived from the
committed tripwire latch state on every nightly run, and the ONLY dedup guard is
(a) the deterministic `fire_event_id`, (b) a pre-insert SELECT against
`alert_outbox` for ids already present, and (c) `alert_outbox`'s own unique index
on `fire_event_id` as the backstop enforcement point. There is no local disarm
state and none is added here (F11's `do_not_redo` forbids a second local
canonical-fact/idempotency store). Consequently, IF an operator or a future
migration ever purges/archives old `alert_outbox` rows, a tripwire whose latch
is still FIRED could be re-notified on the next run that no longer finds its old
row -- this is an F08-owned retention-policy question, not something this module
can close from its own owned files, and is deliberately disclosed here rather
than silently assumed away.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
import urllib.error
import uuid as _uuid_mod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from engine import falsifier_tripwires as ft
from lib import config

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://fsldfzlxyavsuwqbceod.supabase.co"
).rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
EVIDENCE_BASE = "https://www.mastermind-x.com"
SOURCE = "macro.thesis_condition_monitor"
CATEGORY = "thesis_window"
CHANNEL = "email"

READ_OK, READ_OK_ZERO, READ_NO_COVERAGE, READ_UNAVAILABLE = (
    "READ_OK",
    "READ_OK_ZERO",
    "READ_NO_COVERAGE",
    "READ_UNAVAILABLE",
)

# Words banned from every GLANCE-TIER user-facing string this module emits (house
# law, CLAUDE.md ruling #3821): falsifier/refutation language is never front-facing.
# Tier-2 fields (engine_window_plain*) are explicit raw-detail passthrough and are
# NOT subject to this ban -- see the module docstring.
_BANNED_TERMS = ("falsif", "refut", "证伪")

# A fixed, arbitrary namespace UUID for synthesizing alert_outbox.alert_id values
# (uuid5) from the conceptual "thesis:<thesis_id>" identity documented above. Never
# change this constant -- doing so would re-mint every thesis's synthetic alert_id.
_ALERT_ID_NAMESPACE = _uuid_mod.UUID("6f1e6cf4-6e9b-5f2a-9d0a-6d0f6a5b6c00")

# A ZH sentence must never leave the user-authored parts of a message untranslated
# without saying so (META-CEO RULING MINOR-2: "fallback to EN with a 'translation
# pending' marker rather than a ZH subject with an EN body"). The user's own
# falsifier text has no ZH counterpart in the thesis schema, so any ZH sentence
# that quotes it verbatim carries this marker.
TRANSLATION_PENDING_ZH_MARKER = "（翻译待补）"


@dataclass(frozen=True)
class TypedRead:
    state: str
    rows: list | None
    error_class: str | None = None


@dataclass(frozen=True)
class MonitorPlan:
    rows: list[dict]
    evaluated_n: int
    matched_n: int
    duplicate_n: int
    no_coverage_n: int
    unmappable_n: int
    stale_n: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MonitorResult:
    outcome: str
    read_state: str
    error_class: str | None
    evaluated_n: int
    matched_n: int
    enqueued_n: int
    duplicate_n: int
    no_coverage_n: int
    unmappable_n: int
    run_id: str
    planned_n: int = 0
    # A window that fired BEFORE the thesis existed is pre-existing history,
    # not a new transition (_not_stale), and is suppressed from enqueue --
    # but a run that suppressed N such windows must not be byte-identical in
    # its log line to a run that saw nothing at all (round-3 review MINOR-1:
    # MonitorPlan.stale_n was computed then silently discarded).
    stale_n: int = 0
    # Optional Government Revenue dry-planning block, present ONLY when the
    # the existing monitor consumes declared subscriptions; delivery stays dry.
    # every existing construction and test byte-compatible.
    govrev: dict | None = None


# ---------------------------------------------------------------------------
# Pure functions -- no IO
# ---------------------------------------------------------------------------

def subject_key(subject_ref: dict) -> tuple[str, str] | None:
    """Resolve a thesis subject_ref to a ('ticker'|'cycle', normalized) tuple.

    kind/owner vocabulary verified against the reviewed migration's
    `theses_set_subject_ref` guard: kind in ('issuer','theme'); owner in
    ('data_os.security_master','terminal.analysis_symbol','macro.theme_registry');
    owner='macro.theme_registry' <=> kind='theme'; the other two owners <=> kind='issuer'.
    """
    if not isinstance(subject_ref, dict):
        return None
    kind = subject_ref.get("kind")
    owner = subject_ref.get("owner")
    key = subject_ref.get("key")
    if kind == "issuer" and owner in ("data_os.security_master", "terminal.analysis_symbol"):
        listing = subject_ref.get("listing") or {}
        symbol = listing.get("symbol") if isinstance(listing, dict) else None
        raw = symbol or key
        if not raw or not isinstance(raw, str):
            return None
        return ("ticker", raw.strip().upper())
    if kind == "theme" and owner == "macro.theme_registry":
        if not key or not isinstance(key, str):
            return None
        return ("cycle", key.strip().lower())
    return None


def load_tripwire_view() -> tuple[list[dict], dict, str | None]:
    """Read the committed falsifiers + latch state. NEVER recomputes them.

    Returns (entries, state, error_class). error_class is None for the normal
    "file absent" state (nothing has rendered yet -- a legitimate READ_OK_ZERO,
    not an error) and is a typed string when a file EXISTS but cannot be parsed
    -- an unknown latch state must never render identically to an empty one.
    """
    root = config.ROOT
    f_path = root / ft._FALSIFIERS_JSON
    s_path = root / ft._STATE_JSON
    entries: list[dict] = []
    state: dict = {}
    if f_path.exists():
        try:
            data = json.loads(f_path.read_text())
            entries = data if isinstance(data, list) else data.get("falsifiers", [])
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return [], {}, "corrupt_falsifiers_json"
    if s_path.exists():
        try:
            state = json.loads(s_path.read_text())
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return [], {}, "corrupt_tripwire_state_json"
    return entries, state, None


def fired_windows(entries: list[dict], latch_state: dict) -> list[dict]:
    """Windows whose latch_state entry is a latched FIRED with a non-null fired_on."""
    out = []
    for e in entries:
        eid = e.get("id")
        st = latch_state.get(eid)
        if not isinstance(st, dict):
            continue
        if st.get("state") != "FIRED" or not st.get("latched"):
            continue
        fired_on = st.get("fired_on")
        if not fired_on:
            continue
        out.append(
            {
                "id": eid,
                "version": st.get("version", e.get("version")),
                "cycle": e.get("cycle"),
                "scope": e.get("scope", "cycle"),
                "tickers": e.get("tickers") or [],
                "claim": e.get("claim", ""),
                "claim_zh": e.get("claim_zh", ""),
                "direction": e.get("direction", "refutes"),
                "coverage": e.get("coverage", "full"),
                "fired_on": fired_on,
            }
        )
    return out


def match_windows(subject: tuple[str, str], windows: list[dict]) -> list[dict]:
    kind, norm = subject
    out = []
    for w in windows:
        scope = w.get("scope", "cycle")
        if kind == "ticker" and scope == "ticker":
            tickers = [t.upper() for t in (w.get("tickers") or [])]
            if norm in tickers:
                out.append(w)
        elif kind == "cycle" and scope != "ticker":
            if str(w.get("cycle", "")).lower() == norm:
                out.append(w)
    return out


def _not_stale(window: dict, thesis_created_at: str | None) -> bool:
    """A window fired before the thesis existed is not a transition 'since the
    last run' for that subscription -- it is pre-existing history. Enabling this
    monitor for the first time must not backfire every historically latched
    window at every currently-active thesis. Comparison is lexical ISO-8601,
    which sorts correctly for both date-only and full-timestamp strings. When
    the thesis has no recorded creation time (should not happen for a real row
    selected with `created_at` in the query, but defensive for callers that
    omit it) the window is not filtered -- an unknown recency is disclosed via
    the existing no_coverage/duplicate accounting, never silently dropped.
    """
    if not thesis_created_at:
        return True
    fired_on = window.get("fired_on") or ""
    return fired_on >= thesis_created_at[:10]


def fire_event_id(
    *,
    thesis_id: str,
    tripwire_id: str,
    tripwire_version: int,
    fired_on: str,
    thesis_version: int | None = None,
) -> str:
    """Deterministic id for one (thesis, tripwire-transition) fire.

    META-CEO RULING (B-F11-1 round-3 blocker 3): `thesis_version` is DISPLAY
    ONLY and is accepted here purely so callers can log/carry it alongside the
    id -- it is NEVER part of the digest. A thesis amendment (which bumps
    `current_version`) must not mint a new id for an already-notified
    (tripwire_id, tripwire_version, fired_on) transition, or a sticky/already-
    FIRED window would re-notify on every edit to the thesis.
    """
    parts = "|".join([thesis_id, tripwire_id, str(tripwire_version), fired_on])
    digest = hashlib.sha256(parts.encode("utf-8")).hexdigest()[:32]
    return f"thesis:{digest}"


def synthetic_alert_id(thesis_id: str) -> str:
    """Deterministic per-thesis synthetic `alert_outbox.alert_id` (uuid5 of the
    conceptual "thesis:<thesis_id>" identity -- META-CEO RULING M1). Stable
    across every fire produced for the same thesis; NOT a foreign key into any
    real Alerts-table row (none exists for a thesis-condition fire)."""
    return str(_uuid_mod.uuid5(_ALERT_ID_NAMESPACE, f"thesis:{thesis_id}"))


def user_condition_text(falsifiers: Any) -> str:
    """The user's OWN condition text(s), byte-verbatim from
    `thesis_versions.content.falsifiers` -- no rstrip/lstrip/normalization of
    any kind (META-CEO RULING MINOR-1). Multiple falsifiers are joined with
    '; ' BETWEEN the verbatim strings; a single falsifier is returned exactly
    as authored, with no separator applied. Never derived from the engine's
    tripwire `claim` -- see `engine_window_plain` and the module docstring."""
    if not falsifiers:
        return ""
    if isinstance(falsifiers, str):
        falsifiers = [falsifiers]
    return "; ".join(str(f) for f in falsifiers if f)


def _glance_subject(window: dict, subject: tuple[str, str]) -> str | None:
    """The safe glance-tier subject label, or None when no safe label exists.

    META-CEO RULING M3 else-branch (round-3 review BLOCKER 1): a humanized/
    title-cased form of the raw internal cycle slug ('long_bonds' ->
    'Long Bonds') is STILL the internal slug -- it is not a genuine plain-
    language label just because the underscores were swapped for spaces and
    the words capitalized. The real committed corpus carries no `label` field
    today, so every cycle-scope window falls through to None (caller uses the
    generic fallback sentence). A TICKER symbol is a real, universally-shown
    market identifier (not an internal abbreviation) and is always safe to
    use directly. A future corpus `label` field wins over both when present.
    """
    label = window.get("label")
    if label:
        return str(label).strip()
    kind, norm = subject
    if kind == "ticker":
        return norm
    return None


def _close_sentence(text: str) -> str:
    """Append a terminal period only when `text` doesn't already end with one
    (round-3 review MINOR-4): the user's byte-verbatim condition text may
    already end in '.'/'!'/'?', and blindly appending another produced a
    double period ('...decisively..') in the composed glance sentence. This
    never mutates the stored `condition_plain` field itself -- only the
    derived summary sentence's closing punctuation."""
    if text and text[-1] in ".!?":
        return text
    return f"{text}."


def compose_payload(
    *, thesis: dict, window: dict, subject: tuple[str, str], evidence_base: str
) -> dict:
    """Compose the alert_outbox payload.

    condition_plain / condition_plain_zh are the USER's own falsifier text
    (verbatim, byte-for-byte). engine_window_plain / engine_window_plain_zh are
    the ENGINE's tripwire claim, carried as a SEPARATE Tier-2 detail field --
    never glued into the glance-tier summary/condition (META-CEO RULING
    B-F11-1 round-3 blocker 1).
    """
    title = (thesis.get("title") or "").strip() or "your thesis"
    condition = user_condition_text(thesis.get("falsifiers"))
    has_condition = bool(condition)
    display = _glance_subject(window, subject)
    kind, _norm = subject
    evidence_url = f"{evidence_base.rstrip('/')}/cycle.html"
    engine_window_plain = window.get("claim", "") or ""
    engine_window_plain_zh = window.get("claim_zh", "") or ""

    if display:
        subject_line = f"A window we watch for {display} has closed"
        subject_line_zh = f"你关注的“{display}”窗口已关闭"
        closed_prefix = f"A window we watch for {display} has closed."
        closed_prefix_zh = f"你关注的“{display}”窗口已关闭。"
    else:
        # META-CEO RULING M3 else-branch: no safe human label exists for this
        # window's subject (a cycle-scope window without a corpus `label`) --
        # fall back to a fully-translated generic sentence that never names
        # the raw/humanized internal slug, in either language.
        subject_line = "A market condition we watch for your thesis has changed"
        subject_line_zh = "你关注的一项市场条件已发生变化"
        closed_prefix = "A market condition we watch for your thesis has changed."
        closed_prefix_zh = "你关注的一项市场条件已发生变化。"

    if has_condition:
        summary_plain = (
            f'{closed_prefix} Your thesis "{title}" lists: {_close_sentence(condition)}'
        )
        summary_plain_zh = (
            f"{closed_prefix_zh}你的论点《{title}》列出的条件："
            f"{condition}{TRANSLATION_PENDING_ZH_MARKER}"
        )
        condition_plain_zh = f"{condition}{TRANSLATION_PENDING_ZH_MARKER}"
    else:
        summary_plain = f"{closed_prefix} Your thesis lists no conditions yet."
        summary_plain_zh = f"{closed_prefix_zh}你的论点尚未列出任何条件。"
        condition_plain_zh = ""

    return {
        "subject": subject_line,
        "subject_zh": subject_line_zh,
        "summary_plain": summary_plain,
        "summary_plain_zh": summary_plain_zh,
        # Only a ticker subject is a real ticker; a cycle subject's display
        # label is descriptive text, not a tradable symbol.
        "ticker": display if kind == "ticker" else None,
        "condition_plain": condition,
        "condition_plain_zh": condition_plain_zh,
        # Tier-2 detail only -- may contain the engine's own stats/abbreviations
        # (e.g. "SOX ~14,655"); never surfaced in the glance-tier fields above.
        "engine_window_plain": engine_window_plain,
        "engine_window_plain_zh": engine_window_plain_zh,
        "evidence_url": evidence_url,
        "fired_at": window.get("fired_on"),
        "category": CATEGORY,
        "requires_tier": None,
        "source": SOURCE,
        "thesis_id": thesis.get("id"),
        "thesis_version": thesis.get("version"),
        "tripwire_id": window.get("id"),
        "tripwire_version": window.get("version"),
        "coverage": window.get("coverage", "full"),
    }


def plan_enqueue(
    *,
    theses: list[dict],
    versions: dict[str, dict],
    windows: list[dict],
    existing_fire_ids: set[str],
    evidence_base: str,
) -> MonitorPlan:
    rows: list[dict] = []
    evaluated_n = 0
    matched_n = 0
    duplicate_n = 0
    no_coverage_n = 0
    unmappable_n = 0
    stale_n = 0
    notes: list[str] = []

    for thesis in theses:
        evaluated_n += 1
        subject = subject_key(thesis.get("subject_ref") or {})
        if subject is None:
            unmappable_n += 1
            notes.append(f"unmappable subject_ref for thesis {thesis.get('id')}")
            continue
        all_matches = match_windows(subject, windows)
        created_at = thesis.get("created_at")
        matches = [w for w in all_matches if _not_stale(w, created_at)]
        if not all_matches:
            no_coverage_n += 1
            notes.append(f"no tripwire coverage for thesis {thesis.get('id')}")
            continue
        if not matches:
            stale_n += 1
            notes.append(
                f"tripwire fired before thesis {thesis.get('id')} was created — not a new transition"
            )
            continue
        thesis_id = thesis.get("id")
        current_version = thesis.get("current_version")
        version_row = versions.get(f"{thesis_id}:{current_version}")
        if version_row is None:
            unmappable_n += 1
            notes.append(f"no current version row for thesis {thesis_id}")
            continue
        content = version_row.get("content") or {}
        title = content.get("title", "")
        falsifiers = content.get("falsifiers") or []
        for window in matches:
            matched_n += 1
            fid = fire_event_id(
                thesis_id=thesis_id,
                tripwire_id=window.get("id"),
                tripwire_version=window.get("version"),
                fired_on=window.get("fired_on"),
                thesis_version=current_version,
            )
            if fid in existing_fire_ids:
                duplicate_n += 1
                continue
            thesis_for_payload = {
                "id": thesis_id,
                "version": current_version,
                "title": title,
                "falsifiers": falsifiers,
            }
            payload = compose_payload(
                thesis=thesis_for_payload,
                window=window,
                subject=subject,
                evidence_base=evidence_base,
            )
            rows.append(
                {
                    "user_id": thesis.get("user_id"),
                    "alert_id": synthetic_alert_id(thesis_id),
                    "fire_event_id": fid,
                    "channel": CHANNEL,
                    "status": "pending",
                    "attempts": 0,
                    "payload": payload,
                }
            )
            existing_fire_ids.add(fid)

    return MonitorPlan(
        rows=rows,
        evaluated_n=evaluated_n,
        matched_n=matched_n,
        duplicate_n=duplicate_n,
        no_coverage_n=no_coverage_n,
        unmappable_n=unmappable_n,
        stale_n=stale_n,
        notes=notes,
    )


def _classify_outcome(plan: MonitorPlan) -> tuple[str, str]:
    """(outcome, read_state) for a plan whose reads all succeeded. READ_NO_COVERAGE
    (META-CEO RULING MINOR-4) is used, not left dead, exactly when EVERY evaluated
    thesis had zero tripwire coverage at all -- a real, disclosed state distinct
    from a normal empty-but-covered run."""
    if plan.evaluated_n > 0 and plan.no_coverage_n == plan.evaluated_n:
        return "no_coverage", READ_NO_COVERAGE
    return "ok", READ_OK


# ---------------------------------------------------------------------------
# Government Revenue monitor declarations -- pure, bounded, DRY planning only.
#
# These hooks evaluate EXPLICITLY DECLARED government_revenue monitor
# declarations carried by the EXISTING immutable thesis content
# (thesis_versions.content.government_revenue_monitor, wire shape). They read
# only what the caller passes in: no network, no scheduler, no public write,
# no notification side effect, and no alert_outbox row of any new category is
# ever enqueued from here. Returned intents are DRY PLANNING ONLY until the
# root independently qualifies payload/privacy/category/installation; no
# activation flag bypass and no drain enable exists on this path.
# ---------------------------------------------------------------------------

GOVREV_DECLARATION_SCHEMA = "government_revenue.monitor_declaration.v1"
GOVREV_INTENT_CATEGORY = "government_revenue"
GOVREV_STATUS_BASELINE = "baseline"
GOVREV_STATUS_NEW_EVENT = "new_event"
GOVREV_STATUS_CORRECTION = "correction"
GOVREV_STATUS_NO_CHANGE = "no_change"
GOVREV_STATUS_OUTAGE = "outage"
GOVREV_STATUS_INVALID = "invalid_declaration"
GOVREV_STATUSES = (
    GOVREV_STATUS_BASELINE, GOVREV_STATUS_NEW_EVENT, GOVREV_STATUS_CORRECTION,
    GOVREV_STATUS_NO_CHANGE, GOVREV_STATUS_OUTAGE, GOVREV_STATUS_INVALID,
)
GOVREV_MAX_INPUT_REFS = 16
GOVREV_MAX_BASELINE_EVENTS = 100
GOVREV_MAX_DECLARATION_BYTES = 24 * 1024
_GOVREV_INPUT_REF_RE = re.compile(r"^(workspace-sha256:[0-9a-f]{64}|grw2-[0-9a-f]{24})$")
_GOVREV_CANONICAL_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
_GOVREV_TICKER_RE = re.compile(r"^[A-Z0-9]+([.-][A-Z0-9]+)*$")
# Only these two statuses mint a notification intent; the intent identity is
# deterministic (thesis + declaring immutable revision + event record/version/
# knownAt) so replanning the same evidence never duplicates.
_GOVREV_NOTIFIED_STATUSES = (GOVREV_STATUS_NEW_EVENT, GOVREV_STATUS_CORRECTION)
_GOVREV_VERSION_MAX = 999_999_999


def _govrev_canonical_utc(value: Any) -> str | None:
    """Canonical UTC wall clock (millisecond precision, Z only), calendar-validated."""
    if not isinstance(value, str) or not _GOVREV_CANONICAL_UTC_RE.fullmatch(value):
        return None
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return None
    return value


def _govrev_bounded_line(value: Any, max_len: int) -> str | None:
    """PostgreSQL btrim(text, ' ') semantics, bounded, control-character free."""
    if not isinstance(value, str):
        return None
    trimmed = value.strip(" ")
    if not trimmed or len(trimmed) > max_len:
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in trimmed):
        return None
    return trimmed


def _govrev_nullable_line(value: Any, max_len: int) -> str | None:
    return None if value is None else _govrev_bounded_line(value, max_len)


def parse_govrev_declaration(value: Any) -> tuple[dict | None, str | None]:
    """Strictly validate the optional declaration carried by immutable thesis
    content (wire shape, exactly as the owning SQL function stores it).

    Returns (declaration, None) for a valid declaration, (None, "absent") when
    the member is missing or explicitly null, and (None, <error_class>) for
    anything malformed: unknown/private keys, free URLs or bodies, malformed
    clocks, non-finite versions and over-limit payloads are all refused here.
    """
    if value is None:
        return None, "absent"
    if not isinstance(value, dict):
        return None, "declaration_not_object"
    if sorted(value.keys()) != sorted([
        "schema", "enabled", "subject", "selection", "window", "knowledge_cutoff", "input_refs", "baseline_events",
    ]):
        return None, "declaration_keys"
    if value["schema"] != GOVREV_DECLARATION_SCHEMA or not isinstance(value["enabled"], bool):
        return None, "declaration_header"
    subject = value["subject"]
    if not isinstance(subject, dict) or subject.get("schema") != "mastermind.thesis-subject-ref/v1":
        return None, "declaration_subject"
    required_subject = {"schema", "kind", "owner", "key", "identity_state", "company_id", "display"}
    if not required_subject.issubset(subject) or set(subject) - required_subject - {"listing"}:
        return None, "declaration_subject"
    kind, owner = subject.get("kind"), subject.get("owner")
    if kind not in ("issuer", "theme") or owner not in ("data_os.security_master", "terminal.analysis_symbol", "macro.theme_registry"):
        return None, "declaration_subject"
    if (owner == "macro.theme_registry") != (kind == "theme"):
        return None, "declaration_subject"
    if _govrev_bounded_line(subject.get("key"), 256) != subject.get("key") or _govrev_bounded_line(subject.get("display"), 256) != subject.get("display"):
        return None, "declaration_subject"
    if subject.get("identity_state") not in ("resolved", "listing_scoped"):
        return None, "declaration_subject"
    if subject.get("company_id") is not None and _govrev_bounded_line(subject["company_id"],256) != subject["company_id"]:
        return None, "declaration_subject"
    listing = subject.get("listing")
    if listing is not None:
        if not isinstance(listing,dict) or set(listing) != {"symbol","mic","security_id"}:
            return None,"declaration_subject"
        if _govrev_bounded_line(listing.get("symbol"),24) != listing.get("symbol"):
            return None,"declaration_subject"
        for field,cap in (("mic",32),("security_id",256)):
            if listing[field] is not None and _govrev_bounded_line(listing[field],cap) != listing[field]:
                return None,"declaration_subject"
    if owner == "terminal.analysis_symbol":
        if subject["identity_state"] != "listing_scoped" or not listing or listing["symbol"] != subject["key"] or subject["key"] != subject["key"].upper():
            return None,"declaration_subject"
    elif subject["identity_state"] != "resolved":
        return None,"declaration_subject"
    if kind == "theme" and listing is not None:
        return None,"declaration_subject"

    selection = value["selection"]
    if not isinstance(selection, dict) or sorted(selection.keys()) != sorted(
        ["mode", "truth", "q", "agency", "ticker", "issuer"]
    ):
        return None, "selection_keys"
    if selection["mode"] not in ("changes", "awards", "opportunities", "recompetes"):
        return None, "selection_mode"
    if selection["truth"] not in ("all", "official", "linked", "defense"):
        return None, "selection_truth"
    q = _govrev_nullable_line(selection["q"], 120)
    agency = _govrev_nullable_line(selection["agency"], 100)
    ticker = _govrev_nullable_line(selection["ticker"], 10)
    if q is None and selection["q"] is not None:
        return None, "selection_text"
    if agency is None and selection["agency"] is not None:
        return None, "selection_text"
    if ticker is None and selection["ticker"] is not None:
        return None, "selection_text"
    if ticker is not None and not _GOVREV_TICKER_RE.match(ticker):
        return None, "selection_ticker"
    if selection["issuer"] not in (None, "LMT", "RTX", "NOC", "LHX"):
        return None, "selection_issuer"

    window = value["window"]
    if not isinstance(window, dict) or sorted(window.keys()) != ["end", "start"]:
        return None, "window_keys"
    start = _govrev_canonical_utc(window.get("start"))
    end = _govrev_canonical_utc(window.get("end"))
    cutoff = _govrev_canonical_utc(value["knowledge_cutoff"])
    if not start or not end or not cutoff or start > end:
        return None, "window_clock"

    refs = value["input_refs"]
    if not isinstance(refs, list) or not 1 <= len(refs) <= GOVREV_MAX_INPUT_REFS:
        return None, "input_refs"
    if any(not isinstance(ref, str) or not _GOVREV_INPUT_REF_RE.fullmatch(ref) for ref in refs):
        return None, "input_ref_shape"
    if len(set(refs)) != len(refs):
        return None, "input_ref_duplicate"

    raw_events = value["baseline_events"]
    if not isinstance(raw_events, list) or len(raw_events) > GOVREV_MAX_BASELINE_EVENTS:
        return None, "baseline_events"
    baseline: list[dict] = []
    for item in raw_events:
        if not isinstance(item, dict) or sorted(item.keys()) != sorted(
            ["record_id", "event_id", "version", "known_at"]
        ):
            return None, "baseline_event_keys"
        record_id = _govrev_bounded_line(item["record_id"], 128)
        event_id = _govrev_bounded_line(item["event_id"], 128)
        known_at = _govrev_canonical_utc(item["known_at"])
        version = item["version"]
        if not record_id or not event_id or not known_at or known_at > cutoff:
            return None, "baseline_event_fields"
        # Finite positive versions only: bools, floats, zero and oversized
        # counters are all refused before any planning happens.
        if isinstance(version, bool) or not isinstance(version, int) or not 1 <= version <= _GOVREV_VERSION_MAX:
            return None, "baseline_event_version"
        baseline.append({"recordId": record_id, "eventId": event_id, "version": version, "knownAt": known_at})
    if len({(b["recordId"], b["eventId"]) for b in baseline}) != len(baseline):
        return None, "baseline_event_duplicate"

    if len(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")) > GOVREV_MAX_DECLARATION_BYTES:
        return None, "declaration_too_large"

    return {
        "schema": value["schema"],
        "enabled": value["enabled"],
        "subject": subject,
        "selection": {
            "mode": selection["mode"], "truth": selection["truth"],
            "q": q, "agency": agency, "ticker": ticker, "issuer": selection["issuer"],
        },
        "window": {"start": start, "end": end},
        "knowledgeCutoff": cutoff,
        "inputRefs": list(refs),
        "baselineEvents": baseline,
    }, None


GOVREV_MAX_OBSERVATIONS = 500
GOVREV_MAX_WORKSPACE_BYTES = 8 * 1024 * 1024


def _govrev_instant(value: Any) -> Any:
    if not isinstance(value,str) or value.endswith("-00:00"): return None
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError,OverflowError): return None


def _govrev_clock(value: Any) -> str | None:
    """Canonical display clock; comparisons retain the source's full precision."""
    instant=_govrev_instant(value)
    return instant.isoformat(timespec="milliseconds").replace("+00:00","Z") if instant is not None else None


def _govrev_content_ref(workspace: dict) -> str:
    # Same content basis as scripts.build_government_revenue._workspace_bundle_id:
    # assembly time is excluded; original producer bundle must match these bytes.
    basis={k:v for k,v in workspace.items() if k not in {"bundle_id","generated_at"}}
    digest=hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    return "grw2-"+digest[:24]


def govrev_workspace_readiness(workspace: Any) -> tuple[bool, str | None, str | None]:
    if not isinstance(workspace,dict): return False,"workspace_unavailable",None
    events=workspace.get("events")
    if not isinstance(events,list) or len(events)>GOVREV_MAX_OBSERVATIONS:
        return False,"workspace_population_unbounded",None
    if any(not isinstance(event,dict) for event in events) or len({event.get("event_id") for event in events}) != len(events):
        return False,"workspace_event_identity_conflict",None
    try:
        from engine.government_revenue.workspace import is_valid_procurement_workspace
        if not is_valid_procurement_workspace(workspace): return False,"invalid_governed_workspace",None
        if workspace.get("bundle_id") != _govrev_content_ref(workspace): return False,"workspace_identity_mismatch",None
    except (ImportError,TypeError,ValueError,OverflowError): return False,"workspace_validation_unavailable",None
    knowledge=_govrev_clock(workspace.get("known_at"))
    if knowledge is None: return False,"workspace_knowledge_clock_missing",None
    coverage=workspace.get("coverage") or {}
    if workspace.get("next_cursor") or coverage.get("events_truncated") or len(events)<coverage.get("events_visible",len(events)):
        return False,"incomplete_monitor_population",None
    freshness=workspace.get("freshness") or {}
    if freshness.get("status") != "ok": return False,"workspace_not_current",None
    return True,None,knowledge


def load_govrev_workspace() -> Any:
    """Bounded read of the incumbent published artifact; no network or user fields."""
    path=config.ROOT/"data/government_revenue/workspace.json"
    try:
        with path.open("rb") as handle: raw=handle.read(GOVREV_MAX_WORKSPACE_BYTES+1)
        if len(raw)>GOVREV_MAX_WORKSPACE_BYTES: return None
        return json.loads(raw)
    except (OSError,ValueError,UnicodeError): return None


def _govrev_matches(event: dict, selection: dict) -> bool:
    kind=event.get("kind")
    modes={"awards":"award_change","opportunities":"opportunity","recompetes":"recompete"}
    if selection["mode"] in modes and kind!=modes[selection["mode"]]: return False
    impacts=event.get("listed_company_impacts") or []
    agency=event.get("agency") or {}
    agency_name=agency.get("department_name") or agency.get("name") or ""
    source_class=(event.get("evidence") or {}).get("source_class")
    if selection["truth"]=="official" and (kind=="recompete" or source_class=="observed_source_revision"): return False
    if selection["truth"]=="linked" and not any(i.get("ticker") for i in impacts if isinstance(i,dict)): return False
    if selection["truth"]=="defense" and not re.search(r"defen[cs]e|military|air force|army|navy|space force", " ".join(str(agency.get(k) or "") for k in ("name","department_name","subagency_name")),re.I): return False
    if selection["agency"] and agency_name!=selection["agency"]: return False
    tickers={event.get("primary_ticker")} | {i.get("ticker") for i in impacts if isinstance(i,dict)}
    for key in ("ticker","issuer"):
        if selection[key] and selection[key] not in tickers: return False
    if selection["q"]:
        award=event.get("award_change") or {};opportunity=event.get("opportunity") or {};change=event.get("change") or {}
        terms=[event.get(k) for k in ("event_id","record_id","title_original","title_zh","primary_ticker")]
        terms += [agency_name,agency.get("subagency_name"),opportunity.get("notice_id"),opportunity.get("solicitation_number"),award.get("award_key"),award.get("generated_award_id"),award.get("piid"),award.get("recipient_name"),change.get("what_changed_en"),change.get("what_changed_zh")]
        if selection["q"].casefold() not in " ".join(str(x or "") for x in terms).casefold(): return False
    return True


def _govrev_collect_events(declaration: dict, workspace: dict) -> tuple[list[dict], str | None]:
    events=[];current_clock=_govrev_instant(workspace.get("known_at"));current_ref=workspace["bundle_id"]
    for raw in workspace["events"]:
        if not _govrev_matches(raw,declaration["selection"]): continue
        change=raw.get("change") or {};known=_govrev_clock(change.get("known_at"))
        instant=_govrev_instant(change.get("known_at"))
        if instant is None or instant>current_clock: return [],"event_knowledge_clock_invalid"
        if not _govrev_instant(declaration["window"]["start"])<=instant<=_govrev_instant(declaration["window"]["end"]): continue
        events.append({"record_id":raw["record_id"],"event_id":raw["event_id"],"version":raw["version"],"known_at":known,"source_known_at":change["known_at"],"is_correction":change.get("is_correction") is True,"input_ref":current_ref})
    return events,None


def govrev_intent_identity(*, thesis_id: Any, thesis_version: Any, event: dict) -> str:
    """Deterministic dedup identity for one planned intent: the thesis, the
    immutable revision that declared the monitor, and the event's record/
    version/knownAt. Never derived from the serving source bundle."""
    parts = "|".join([
        str(thesis_id), str(thesis_version), event["record_id"], event["event_id"],
        str(event["version"]), _govrev_instant(event.get("source_known_at",event["known_at"])).isoformat(timespec="microseconds"),
    ])
    return "govrev:" + hashlib.sha256(parts.encode("utf-8")).hexdigest()[:32]


def evaluate_govrev_monitors(
    *, heads: list[dict], versions: dict[str, dict], workspace: Any, now_utc: Any = None
) -> list[dict]:
    """Evaluate every explicitly declared Government Revenue monitor for the
    supplied active heads, strictly over their EXISTING immutable content.

    Pure: no IO, no scheduler, no public write, no notification side effect,
    and baselines are never mutated here. Returns one typed row per evaluated
    monitor with exact inputRef/event/version evidence; intents are DRY
    PLANNING ONLY (dry_run_only=True) and are never enqueued."""
    ready, gate_reason, as_of = govrev_workspace_readiness(workspace)
    current_clock=_govrev_clock(now_utc or _now_utc_iso())
    if ready and (current_clock is None or _govrev_instant(workspace.get("known_at"))>_govrev_instant(now_utc or _now_utc_iso())):
        ready=False;gate_reason="future_workspace_knowledge"
    rows: list[dict] = []
    for head in heads:
        thesis_id = head.get("id")
        user_id = head.get("user_id")
        thesis_version = head.get("current_version")
        row: dict = {
            "thesis_id": thesis_id, "user_id": user_id, "thesis_version": thesis_version,
            "status": None, "reason": None, "events": [], "planned_intents": [],
        }
        # Active owner/version agreement is validated BEFORE any planning: a
        # head/version disagreement is an outage, never a plan.
        version_row = versions.get(f"{thesis_id}:{thesis_version}")
        if (head.get("lifecycle_state") != "active" or not isinstance(version_row, dict)
            or version_row.get("thesis_id") != thesis_id or version_row.get("user_id") != user_id
            or version_row.get("version") != thesis_version):
            row["status"] = GOVREV_STATUS_OUTAGE
            row["reason"] = "owner_or_version_mismatch"
            rows.append(row)
            continue
        content = version_row.get("content")
        declaration, error = parse_govrev_declaration(
            content.get("government_revenue_monitor") if isinstance(content, dict) else None)
        if error == "absent":
            continue  # not a Government Revenue subscriber: not evaluated at all
        if error is not None:
            row["status"] = GOVREV_STATUS_INVALID
            row["reason"] = error
            rows.append(row)
            continue
        if declaration["enabled"] is not True:
            continue  # explicitly disabled declaration: inert, not evaluated
        if not ready:
            row["status"] = GOVREV_STATUS_OUTAGE
            row["reason"] = gate_reason
            rows.append(row)
            continue
        if as_of < declaration["knowledgeCutoff"]:
            row["status"] = GOVREV_STATUS_OUTAGE
            row["reason"] = "stale_workspace"
            rows.append(row)
            continue
        if head.get("subject_ref") != declaration["subject"]:
            row["status"] = GOVREV_STATUS_INVALID; row["reason"]="subject_mismatch"; rows.append(row); continue
        needed={"awards":"award_events","opportunities":"opportunities","recompetes":"recompetes"}.get(declaration["selection"]["mode"])
        if needed and (workspace.get("freshness",{}).get(needed) or {}).get("status") != "ok":
            row["status"]=GOVREV_STATUS_OUTAGE;row["reason"]="required_rail_unavailable";rows.append(row);continue
        required=[needed] if needed else ["award_events","opportunities","recompetes"]
        age_error=None
        for rail in required:
            health=(workspace.get("freshness") or {}).get(rail) or {}
            if health.get("status") != "ok" or health.get("failure_state") is not None: age_error="required_rail_unavailable";break
            sla=health.get("freshness_sla_minutes")
            if sla is None and health.get("freshness_sla_days") is not None:
                days=health["freshness_sla_days"]
                if isinstance(days,bool) or not isinstance(days,(int,float)) or not 0<days<float("inf"):
                    age_error="required_rail_freshness_unqualified";break
                sla=days*1440
            if sla is not None:
                observed=_govrev_clock(health.get("observed_at") or health.get("last_successful_observed_at") or health.get("known_at"))
                if isinstance(sla,bool) or not isinstance(sla,(int,float)) or not 0<sla<float("inf") or observed is None:
                    age_error="required_rail_freshness_unqualified";break
                age=(datetime.fromisoformat(current_clock.replace("Z","+00:00"))-datetime.fromisoformat(observed.replace("Z","+00:00"))).total_seconds()/60
                if age<0 or age>sla: age_error="required_rail_stale";break
        if age_error:
            row["status"]=GOVREV_STATUS_OUTAGE;row["reason"]=age_error;rows.append(row);continue
        events, collect_error = _govrev_collect_events(declaration, workspace)
        if collect_error is not None:
            row["status"] = GOVREV_STATUS_OUTAGE
            row["reason"] = collect_error
            rows.append(row)
            continue

        # First observation with an empty declared baseline establishes the
        # baseline and emits NOTHING; later runs classify against it.
        # The immutable cutoff identifies the subscribed baseline even when its
        # matching population was empty. Later observations can still be new.
        first_baseline = len(declaration["baselineEvents"]) == 0
        baseline_index = {b["recordId"]: b for b in sorted(declaration["baselineEvents"],key=lambda x:(x["version"],x["knownAt"]))}
        statuses: list[str] = []
        for event in events:
            prior = baseline_index.get(event["record_id"])
            if prior is not None and event["version"] == prior["version"] and _govrev_instant(event["source_known_at"]) == _govrev_instant(prior["knownAt"]):
                event_status, baseline_version = GOVREV_STATUS_NO_CHANGE, prior["version"]
            elif _govrev_instant(event["source_known_at"]) <= _govrev_instant(declaration["knowledgeCutoff"]):
                # Historical rows absent from a bounded baseline are not new since subscription.
                event_status, baseline_version = (GOVREV_STATUS_BASELINE if first_baseline else GOVREV_STATUS_NO_CHANGE), None
            elif prior is None:
                event_status = GOVREV_STATUS_CORRECTION if event["is_correction"] else GOVREV_STATUS_NEW_EVENT
                baseline_version=None
            else:
                # Correction is decided by the declared baseline record+version
                # together with the event's own is_correction flag -- never by
                # which source bundle happened to serve the observation.
                baseline_version = prior["version"]
                event_status = GOVREV_STATUS_CORRECTION if event["is_correction"] else GOVREV_STATUS_NEW_EVENT
            statuses.append(event_status)
            evidence = {
                "record_id": event["record_id"], "event_id": event["event_id"],
                "version": event["version"], "known_at": event["known_at"], "source_known_at":event["source_known_at"],
                "input_ref": event["input_ref"], "is_correction": event["is_correction"],
                "status": event_status, "baseline_version": baseline_version,
                "intent_identity": None,
            }
            if event_status in _GOVREV_NOTIFIED_STATUSES:
                evidence["intent_identity"] = govrev_intent_identity(
                    thesis_id=thesis_id, thesis_version=thesis_version, event=event)
                row["planned_intents"].append({
                    "identity": evidence["intent_identity"],
                    "category": GOVREV_INTENT_CATEGORY,
                    "status": event_status,
                    "thesis_id": thesis_id, "thesis_version": thesis_version,
                    "record_id": event["record_id"], "event_id": event["event_id"],
                    "version": event["version"], "known_at": event["known_at"], "source_known_at":event["source_known_at"],
                    "input_ref": event["input_ref"], "is_correction": event["is_correction"],
                    "dry_run_only": True,
                })
            row["events"].append(evidence)
        if GOVREV_STATUS_CORRECTION in statuses:
            row["status"] = GOVREV_STATUS_CORRECTION
        elif GOVREV_STATUS_NEW_EVENT in statuses:
            row["status"] = GOVREV_STATUS_NEW_EVENT
        elif GOVREV_STATUS_BASELINE in statuses:
            row["status"] = GOVREV_STATUS_BASELINE
        else:
            row["status"] = GOVREV_STATUS_BASELINE if first_baseline else GOVREV_STATUS_NO_CHANGE
        rows.append(row)
    return rows


def govrev_planning_summary(rows: list[dict]) -> dict:
    """Aggregate a dry-planning evaluation. enqueued_n is ALWAYS 0: nothing on
    this path is written anywhere."""
    counts = {status: 0 for status in GOVREV_STATUSES}
    planned = 0
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        planned += len(row["planned_intents"])
    return {
        "evaluated_n": len(rows),
        "planned_n": planned,
        "enqueued_n": 0,
        **counts,
        "note": "dry planning only; no alert_outbox write and no new category enqueued",
    }


# ---------------------------------------------------------------------------
# IO functions -- isolated, monkeypatched in tests
# ---------------------------------------------------------------------------

def _pg(method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def typed_get(path: str) -> TypedRead:
    if not SUPABASE_SERVICE_ROLE_KEY:
        return TypedRead(READ_UNAVAILABLE, None, "no_credentials")
    try:
        rows = _pg("GET", path)
        rows = rows if rows is not None else []
        if not rows:
            return TypedRead(READ_OK_ZERO, [])
        return TypedRead(READ_OK, rows)
    except urllib.error.HTTPError as exc:
        code = getattr(exc, "code", None)
        body = ""
        try:
            body = exc.read().decode("utf-8", "ignore")
        except Exception:
            pass
        if code == 404 or "42P01" in body or "PGRST205" in body:
            return TypedRead(READ_UNAVAILABLE, None, "table_absent")
        return TypedRead(READ_UNAVAILABLE, None, f"http_{code}")
    except Exception:
        return TypedRead(READ_UNAVAILABLE, None, "unknown")


def read_active_theses(limit: int) -> TypedRead:
    path = (
        "theses?lifecycle_state=eq.active&select=id,user_id,current_version,subject_ref,created_at"
        f"&order=updated_at.desc&limit={limit}"
    )
    return typed_get(path)


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def read_current_versions(pairs: list[tuple[str, int]]) -> TypedRead:
    if not pairs:
        return TypedRead(READ_OK_ZERO, [])
    all_rows: list[dict] = []
    for chunk in _chunks(pairs, 50):
        ors = ",".join(f"and(thesis_id.eq.{tid},version.eq.{v})" for tid, v in chunk)
        path = f"thesis_versions?or=({ors})&select=thesis_id,user_id,version,content"
        result = typed_get(path)
        if result.state == READ_UNAVAILABLE:
            return result
        all_rows.extend(result.rows or [])
    return TypedRead(READ_OK if all_rows else READ_OK_ZERO, all_rows)


def read_existing_fire_ids(ids: list[str]) -> TypedRead:
    if not ids:
        return TypedRead(READ_OK_ZERO, [])
    all_rows: list[dict] = []
    for chunk in _chunks(ids, 100):
        in_list = ",".join(chunk)
        path = f"alert_outbox?fire_event_id=in.({in_list})&select=fire_event_id"
        result = typed_get(path)
        if result.state == READ_UNAVAILABLE:
            return result
        all_rows.extend(result.rows or [])
    return TypedRead(READ_OK if all_rows else READ_OK_ZERO, all_rows)


def enqueue(rows: list[dict], *, dry_run: bool) -> tuple[int, int, str | None]:
    enqueued = 0
    duplicates = 0
    if dry_run:
        return (0, 0, None)
    for row in rows:
        try:
            _pg("POST", "alert_outbox", body=row, prefer="return=minimal")
            enqueued += 1
        except urllib.error.HTTPError as exc:
            code = getattr(exc, "code", None)
            body = ""
            try:
                body = exc.read().decode("utf-8", "ignore")
            except Exception:
                pass
            if code == 409 or "23505" in body:
                duplicates += 1
                continue
            if code == 400 or "23502" in body:
                return (enqueued, duplicates, "schema_mismatch")
            return (enqueued, duplicates, f"http_{code}")
    return (enqueued, duplicates, None)


def _now_utc_iso() -> str:
    """Real wall-clock UTC timestamp. A thin, monkeypatchable seam so run_id can
    be tested deterministically without ever defaulting to a constant across
    nightly runs (META-CEO RULING MINOR-5)."""
    return datetime.now(timezone.utc).isoformat()


def run(
    *, now_utc=None, limit: int = 500, dry_run: bool = True, evidence_base: str = EVIDENCE_BASE,
    govrev_workspace: Any = None,
) -> MonitorResult:
    if now_utc is None:
        now_utc = _now_utc_iso()
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=500:
        raise ValueError("monitor limit must be an integer from 1 to 500")
    run_id = hashlib.sha256(f"{now_utc}|{limit}".encode("utf-8")).hexdigest()[:12]

    entries, latch_state, tripwire_error = load_tripwire_view()
    if tripwire_error is not None:
        return MonitorResult(
            outcome="unavailable",
            read_state=READ_UNAVAILABLE,
            error_class=tripwire_error,
            evaluated_n=0,
            matched_n=0,
            enqueued_n=0,
            duplicate_n=0,
            no_coverage_n=0,
            unmappable_n=0,
            run_id=run_id,
        )
    windows = fired_windows(entries, latch_state)

    theses_read = read_active_theses(limit)
    if theses_read.state == READ_UNAVAILABLE:
        return MonitorResult(
            outcome="unavailable",
            read_state=theses_read.state,
            error_class=theses_read.error_class,
            evaluated_n=0,
            matched_n=0,
            enqueued_n=0,
            duplicate_n=0,
            no_coverage_n=0,
            unmappable_n=0,
            run_id=run_id,
        )
    theses = theses_read.rows or []

    pairs = [(t.get("id"), t.get("current_version")) for t in theses]
    versions_read = read_current_versions(pairs)
    if versions_read.state == READ_UNAVAILABLE:
        return MonitorResult(
            outcome="unavailable",
            read_state=versions_read.state,
            error_class=versions_read.error_class,
            evaluated_n=len(theses),
            matched_n=0,
            enqueued_n=0,
            duplicate_n=0,
            no_coverage_n=0,
            unmappable_n=0,
            run_id=run_id,
        )
    versions = {
        f"{v.get('thesis_id')}:{v.get('version')}": v for v in (versions_read.rows or [])
    }

    # The existing nightly entry point consumes the incumbent published workspace
    # for explicit immutable declarations. Private names/filters are never published.
    # This contribution plans only; notification payload/privacy admission remains owed.
    govrev: dict | None = None
    if govrev_workspace is not None or any(isinstance(v.get("content"),dict) and v["content"].get("government_revenue_monitor") is not None for v in versions.values()):
        if govrev_workspace is None: govrev_workspace=load_govrev_workspace()
        govrev_rows = evaluate_govrev_monitors(
            heads=[
                {"id": t.get("id"), "user_id": t.get("user_id"),
                 "current_version": t.get("current_version"), "lifecycle_state": "active", "subject_ref":t.get("subject_ref")}
                for t in theses
            ],
            versions=versions,
            workspace=govrev_workspace,
            now_utc=now_utc,
        )
        govrev = govrev_planning_summary(govrev_rows)
        govrev["monitors"] = govrev_rows

    plan = plan_enqueue(
        theses=theses,
        versions=versions,
        windows=windows,
        existing_fire_ids=set(),
        evidence_base=evidence_base,
    )

    candidate_ids = [r["fire_event_id"] for r in plan.rows]
    existing_read = read_existing_fire_ids(candidate_ids)
    if existing_read.state == READ_UNAVAILABLE:
        return MonitorResult(
            outcome="unavailable",
            read_state=existing_read.state,
            error_class=existing_read.error_class,
            evaluated_n=plan.evaluated_n,
            matched_n=plan.matched_n,
            enqueued_n=0,
            duplicate_n=0,
            no_coverage_n=plan.no_coverage_n,
            unmappable_n=plan.unmappable_n,
            stale_n=plan.stale_n,
            govrev=govrev,
            run_id=run_id,
        )
    existing_ids = {r["fire_event_id"] for r in (existing_read.rows or [])}
    to_send = [r for r in plan.rows if r["fire_event_id"] not in existing_ids]
    duplicate_n = plan.duplicate_n + (len(plan.rows) - len(to_send))

    if dry_run:
        # Dormant/preview path: no write is attempted. enqueued_n reports what
        # ACTUALLY got written (always 0 here); planned_n reports what a live
        # run would attempt, so callers can log the two without conflating them.
        outcome, read_state = _classify_outcome(plan)
        return MonitorResult(
            outcome=outcome,
            read_state=read_state,
            error_class=None,
            evaluated_n=plan.evaluated_n,
            matched_n=plan.matched_n,
            enqueued_n=0,
            duplicate_n=duplicate_n,
            no_coverage_n=plan.no_coverage_n,
            unmappable_n=plan.unmappable_n,
            stale_n=plan.stale_n,
            govrev=govrev,
            run_id=run_id,
            planned_n=len(to_send),
        )

    enqueued_n, more_dupes, error_class = enqueue(to_send, dry_run=dry_run)
    duplicate_n += more_dupes

    if error_class is not None:
        return MonitorResult(
            outcome="unavailable",
            read_state=READ_UNAVAILABLE,
            error_class=error_class,
            evaluated_n=plan.evaluated_n,
            matched_n=plan.matched_n,
            enqueued_n=enqueued_n,
            duplicate_n=duplicate_n,
            no_coverage_n=plan.no_coverage_n,
            unmappable_n=plan.unmappable_n,
            stale_n=plan.stale_n,
            govrev=govrev,
            run_id=run_id,
        )

    outcome, read_state = _classify_outcome(plan)
    return MonitorResult(
        outcome=outcome,
        read_state=read_state,
        error_class=None,
        evaluated_n=plan.evaluated_n,
        matched_n=plan.matched_n,
        enqueued_n=enqueued_n,
        duplicate_n=duplicate_n,
        no_coverage_n=plan.no_coverage_n,
        unmappable_n=plan.unmappable_n,
        stale_n=plan.stale_n,
        govrev=govrev,
        run_id=run_id,
        planned_n=len(to_send),
    )
