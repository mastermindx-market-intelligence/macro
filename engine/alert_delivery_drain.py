"""engine/alert_delivery_drain.py -- pure decision logic + isolated PostgREST IO for the
fired-alert delivery drain (packet B-F08-1b).

Trigger: ``app/deploy/macro-alert-drain.timer`` on the VPS app host (``OnCalendar=*:0/5``).
Cadence: every 5 minutes. User-visible latency budget: 15 minutes p95 from fire to send
(three ticks: one to pick it up, two of slack). This module is OFF the render path -- it
is never imported by any render or nightly builder and writes nothing under ``site/`` or
``data/``.

Layering (STANDING, do not re-litigate): ``engine/`` may not import ``app/`` --
``engine/portfolio_digest.py`` states this as construction law for exactly this lane.
Therefore the mail-sending function is INJECTED at the ``scripts/`` seam
(``scripts/drain_alert_outbox.py`` wires ``app.mailer.send_alert`` in as ``send_fn``);
this module has no import of ``app`` anywhere, which is what makes it possible for
``tests/test_alert_delivery_drain.py::test_engine_module_does_not_import_app`` to prove
no test of it and no build step that imports it can ever send mail.

``_pg`` below mirrors ``app/mailer.py``'s helper (same headers, same env resolution, same
``urllib`` idiom) but is local to this module for the layering reason above.

DELIVERY EFFECT, AND WHAT SMTP CANNOT PROVE
-------------------------------------------
This drain retries by minting a FRESH idempotency key (``_alert_idem_key(id, attempt)``),
which is the only lane in the estate that does so -- every other mailer caller derives a
stable key from its logical event, so a re-offer there collides with the ledger's unique
constraint and cannot resend. That per-attempt key was itself a fix (a terminally-'failed'
row could otherwise never be retried under the same key), and it is precisely what makes
an unresolved delivery dangerous here: a fresh key is a licence to hand the same logical
alert to the relay a second time.

So a durable ``email_log.status='queued'`` is never resolved by assumption. It is read as
three states via ``classify_ledger_queued`` -- provably pre-send, in flight, or effect
unknown -- and only the first is answered with a retry. An effect-unknown row is
QUARANTINED (``quarantine_effect_unknown``): never resent, never marked delivered,
retired past the selection predicate, and announced with a ``::warning`` because nothing
else will ever resolve it.

Exactly-once is NOT available and is not claimed. A connection that drops while the
client waits for the reply to the terminating '.' leaves the message either queued by the
server or discarded, with no way to tell -- so the guarantee this lane offers is
at-most-once-per-logical-alert under uncertainty, with the uncertainty preserved in the
record rather than resolved by guess. Adversarial reproduction of all six termination
points: ``tests/test_alert_delivery_effect_boundary.py``.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from lib import user_prefs

# --------------------------------------------------------------------------- #
# Typed reads (F08 freeze section 5 vocabulary)
# --------------------------------------------------------------------------- #
READ_OK = "READ_OK"
READ_OK_ZERO = "READ_OK_ZERO"
READ_NO_COVERAGE = "READ_NO_COVERAGE"
READ_UNAVAILABLE = "READ_UNAVAILABLE"

LANE = "macro_delivery_drain"
CADENCE_BUDGET_S = 300

# A 'failed' row is retried this many times (attempt 0 = the original send) before it
# leaves the drain's own selection predicate for good (review round 3 ruling). No new
# alert_outbox enum value is introduced -- the row stays 'failed', simply unselected.
ALERT_RETRY_ATTEMPTS_CAP = 3

# Mirrors app.mailer.ALERT_TEMPLATE / app.mailer.alert_idem_key -- duplicated locally
# for the same layering reason ``_pg`` is (module docstring): this module may not
# import ``app/``. Needed only to resolve what a mailer 'duplicate' result actually
# meant (review round 2 blocker, acceptance 1(d) -- see ``_resolve_duplicate`` below).
_ALERT_TEMPLATE = "alert_fire"

# --------------------------------------------------------------------------- #
# The post-SMTP effect boundary (mirrors app/mailer.py -- duplicated locally for the
# same layering reason ``_pg`` is; pinned across the seam by
# ``tests/test_alert_delivery_effect_boundary.py::
#   test_marker_constants_are_pinned_across_the_layering_seam``).
#
# A durable ``email_log.status='queued'`` used to be read as one thing -- "not sent
# yet" -- and answered with a fresh idempotency key on the next tick. It is actually
# three different things, and only the first may be answered that way:
#
#   no marker in `detail`        transport never entered      PROVABLY NOT SENT
#   marker younger than grace    a writer may still be live   IN FLIGHT
#   marker older than grace      the writer is gone           EFFECT UNKNOWN
#
# Minting a fresh key for the third case is a licence to deliver the same logical
# alert twice, which is the defect this boundary closes.
# --------------------------------------------------------------------------- #
SMTP_ATTEMPT_MARKER = "SMTP_ATTEMPTED"
EFFECT_UNKNOWN = "effect_unknown"

# The ``alert_outbox.last_error`` written when a row is quarantined. ``status`` must
# stay inside that table's own CHECK constraint (no new enum value -- review round 3
# MAJOR-3's ruling on unproven schema still binds), so 'failed' carries the row out of
# the retry predicate and THIS string carries the truth: not an ordinary failure, an
# unresolved uncertainty that wants an operator, not a retry.
EFFECT_UNKNOWN_LAST_ERROR = "effect_unknown_after_smtp"
SELECTOR_NO_MATCH = "selector_no_match"
SELECTOR_MULTIPLE_MATCH = "selector_multiple_match"
SELECTOR_MISMATCH = "selector_mismatch"

# How old a marker must be before its writer is presumed gone. DERIVED, not guessed:
# ``app/mailer.py`` can spend at most ``_SEND_ATTEMPTS`` (2) x six socket operations x
# ``_SMTP_TIMEOUT`` (10s) + ``_RETRY_BACKOFF_SEC`` (1.5s) ~= 121.5s inside the
# transport, so anything younger than that may belong to a LIVE writer from the
# previous tick rather than a dead one. Set to one full lane cadence (~2.5x the bound)
# for host clock skew and scheduler slack. The asymmetry is deliberate: too LONG only
# delays a quarantine by a tick, while too SHORT quarantines a send that is still in
# progress.
EFFECT_UNKNOWN_GRACE_S = 300

# How far in the FUTURE a marker may be stamped before we stop believing it is fresh.
# The mailer writes the marker from the app host and this drain reads it from its own,
# so a skewed clock can stamp a marker ahead of the drain's `now`. Without a bound,
# such a marker is younger than the grace window FOREVER: the row would sit 'pending',
# never resent (safe) but also never resolved and never surfaced -- re-evaluated every
# five minutes for as long as the skew lasts. That is exactly the silent livelock this
# module's round-6 ruling forbids. Past this bound the marker is not evidence of
# freshness, it is evidence of a broken clock, and the row fails closed to
# EFFECT_UNKNOWN -- quarantined and announced, which is a state a human can act on.
MAX_CLOCK_SKEW_S = 300


def _alert_idem_key(fire_event_id: str, attempt: int = 0) -> str:
    """Pinned identical to ``app.mailer.alert_idem_key`` (cross-module test in
    ``tests/test_alert_delivery_drain.py``) -- ``attempt=0`` is byte-identical to the
    original single-arg key; ``attempt>0`` mints a fresh key for a retry so a
    terminally-'failed' email_log row never blocks a later send under the same key
    (review round 3 BLOCKER)."""
    base = f"{_ALERT_TEMPLATE}:{fire_event_id}"
    return base if not attempt else f"{base}:{attempt}"


def _age_s(stamp, now_utc: datetime):
    """Seconds between ``stamp`` (ISO-8601, naive treated as UTC) and ``now_utc``.
    None when it cannot be read -- callers must decide the safe answer themselves."""
    if not stamp:
        return None
    try:
        t = datetime.fromisoformat(str(stamp).strip().replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (now_utc - t).total_seconds()


def classify_ledger_queued(detail, *, now_utc: datetime, created_at=None) -> str:
    """What a durable ``email_log.status='queued'`` actually means.

    Returns ``'pre_send'`` | ``'in_flight'`` | ``'effect_unknown'``.

    FAILS CLOSED. A marker with a missing or unparseable timestamp resolves to
    ``'effect_unknown'``, never to ``'pre_send'`` -- a garbled marker is still proof
    that the transport was entered, and the only unsafe answer is the one that
    licenses another send.

    ``'pre_send'`` covers both a bare claim (the process died between the INSERT and
    the marker write) and the marketing suppression park, which ``app/mailer.py``
    leaves at ``queued`` with ``detail='suppression_lookup_failed'``. Both are
    provably untouched by SMTP, so both keep their retry -- this is what keeps a
    suppression-lookup ``queued`` distinguishable from transport uncertainty.
    """
    text = str(detail or "")
    if SMTP_ATTEMPT_MARKER not in text:
        # No marker. Either the transport was never entered, or a writer is between
        # the ledger INSERT and the marker write RIGHT NOW -- that gap spans connect,
        # STARTTLS, AUTH and the marker's own round trip, so it is seconds wide, not
        # instantaneous. `created_at` is the claim time (app/mailer.py's _ledger_insert
        # writes the row before touching SMTP), so a claim younger than the grace
        # window is treated as a live writer and left alone. Without this, two
        # overlapping drain ticks resolve the same fresh claim as an abandoned
        # pre-send, bump `attempts`, and mint a fresh key for a send that is still
        # under way -- a duplicate that needs no crash at all.
        if _age_s(created_at, now_utc) is not None and _age_s(created_at, now_utc) < EFFECT_UNKNOWN_GRACE_S:
            return "in_flight"
        return "pre_send"
    _, _, stamp = text.partition(f"{SMTP_ATTEMPT_MARKER}@")
    stamp = stamp.strip()
    if not stamp:
        return EFFECT_UNKNOWN
    try:
        marked = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return EFFECT_UNKNOWN
    if marked.tzinfo is None:
        marked = marked.replace(tzinfo=timezone.utc)
    age_s = (now_utc - marked).total_seconds()
    if age_s < -MAX_CLOCK_SKEW_S:
        # Implausibly future-dated: a broken clock, not a fresh marker. Fail closed --
        # 'in_flight' here would never expire (see MAX_CLOCK_SKEW_S).
        return EFFECT_UNKNOWN
    if age_s < EFFECT_UNKNOWN_GRACE_S:
        # Includes a small negative age: modest skew is normal and the conservative
        # read is to touch nothing and look again next tick.
        return "in_flight"
    return EFFECT_UNKNOWN


@dataclass(frozen=True)
class TypedRead:
    state: str
    rows: list | None
    error_class: str | None = None


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _pg(method: str, path: str, body=None, prefer: str | None = None, timeout: int = 6):
    url_base = _env("SUPABASE_URL").rstrip("/")
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not key or not url_base:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY unset")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(
        f"{url_base}/rest/v1/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else None


def typed_get(path: str) -> TypedRead:
    """GET ``path`` and classify the result. ``READ_UNAVAILABLE`` never looks like
    ``READ_OK_ZERO`` -- a missing table is a typed failure, not an empty success."""
    try:
        rows = _pg("GET", path)
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            pass
        if exc.code == 404 or "42P01" in body or "PGRST205" in body:
            return TypedRead(READ_UNAVAILABLE, None, error_class="table_absent")
        return TypedRead(READ_UNAVAILABLE, None, error_class=f"HTTPError{exc.code}")
    except Exception as exc:  # noqa: BLE001
        return TypedRead(READ_UNAVAILABLE, None, error_class=type(exc).__name__)
    if rows is None:
        return TypedRead(READ_UNAVAILABLE, None, error_class="empty_response")
    if not rows:
        return TypedRead(READ_OK_ZERO, [])
    return TypedRead(READ_OK, rows)


# --------------------------------------------------------------------------- #
# Prefs (tolerant -- packet B-F08-1a may not have merged yet)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AlertPrefs:
    email_optin: bool
    categories: tuple | None
    tz: str
    tz_source: str
    quiet: tuple | None
    quiet_note: str | None
    lang: str
    categories_note: str | None = None


def _parse_quiet(value) -> tuple:
    """Returns (quiet_tuple_or_None, note_or_None)."""
    if value is None:
        return None, None
    try:
        if isinstance(value, dict):
            start_s, end_s = value.get("start"), value.get("end")
        elif isinstance(value, str) and "-" in value:
            start_s, end_s = value.split("-", 1)
        else:
            return None, "unparsed"

        def _to_min(s: str) -> int:
            text = str(s).strip()
            parts = text.split(":")
            if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
                raise ValueError("quiet-hour clock must be HH:MM")
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError("quiet-hour clock is outside 00:00-23:59")
            return h * 60 + m

        return (_to_min(start_s), _to_min(end_s)), None
    except Exception:  # noqa: BLE001
        return None, "unparsed"


def parse_alert_prefs(meta: dict | None) -> AlertPrefs | None:
    """None when metadata is unreadable -- 'we do not know', not 'nothing is set'."""
    if not isinstance(meta, dict):
        return None
    optin_raw = meta.get("alert_email_optin")
    email_optin = optin_raw is True or optin_raw in ("true", "1", "on")
    cats = meta.get("alert_categories")
    if cats is None:
        categories, categories_note = None, None
    elif isinstance(cats, (list, tuple)) and all(
            isinstance(category, str)
            and category.strip() in user_prefs.ALERT_CATEGORIES
            for category in cats):
        categories = tuple(category.strip() for category in cats)
        categories_note = None
    else:
        # A malformed stored value must not widen delivery to every category.  Keep
        # the parse typed so decide_row can count it as unevaluable.
        categories, categories_note = None, "unparsed"
    if "tz" in meta:
        # A present but falsey/invalid value is stored corruption, not permission to
        # reinterpret the user's wall clock as UTC. quiet_decision fails it closed.
        raw_tz = meta.get("tz")
        tz = raw_tz.strip() if isinstance(raw_tz, str) else ""
        tz_source = "user"
    else:
        tz, tz_source = "UTC", "default_utc"
    quiet, quiet_note = _parse_quiet(meta.get("quiet_hours"))
    lang = meta.get("lang") if meta.get("lang") in ("en", "zh") else "en"
    return AlertPrefs(email_optin=email_optin, categories=categories, tz=tz,
                      tz_source=tz_source, quiet=quiet, quiet_note=quiet_note, lang=lang,
                      categories_note=categories_note)


# --------------------------------------------------------------------------- #
# Recipient address (the gap the frozen contract leaves open)
# --------------------------------------------------------------------------- #
def fetch_user_record(user_id: str) -> tuple:
    """``(typed_state, {'email':..., 'user_metadata':...} | None)`` from GoTrue admin.
    ``READ_UNAVAILABLE`` on any failure -- an unknown recipient is never a send."""
    url_base = _env("SUPABASE_URL").rstrip("/")
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not key or not url_base:
        return READ_UNAVAILABLE, None
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    req = urllib.request.Request(
        f"{url_base}/auth/v1/admin/users/{urllib.parse.quote(str(user_id), safe='')}",
        method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = resp.read()
        rec = json.loads(raw) if raw else None
        if not rec:
            return READ_UNAVAILABLE, None
        return READ_OK, rec
    except Exception:  # noqa: BLE001
        return READ_UNAVAILABLE, None


# --------------------------------------------------------------------------- #
# Quiet hours -- user tz, never NY (F08 freeze section 3/8)
# --------------------------------------------------------------------------- #
def _wall_instant_utc(day, minute_of_day: int, tz, *, latest: bool) -> datetime | None:
    """Resolve a local wall-clock minute through DST folds and gaps.

    Ambiguous starts use the first fold and ambiguous ends use the second, keeping the
    whole repeated hour quiet. A nonexistent spring-forward minute advances to the
    first real local minute, so 02:30 opens at 03:00 rather than 03:30 or tomorrow.
    """
    wall = datetime.combine(day, datetime.min.time()) + timedelta(minutes=minute_of_day)
    # Normal cases return on the first iteration. The bounded two-day scan also covers
    # unusual whole-date IANA transitions without guessing an offset.
    for offset_m in range(0, 2 * 24 * 60 + 1):
        candidate_wall = wall + timedelta(minutes=offset_m)
        candidates: set[datetime] = set()
        for fold in (0, 1):
            candidate = candidate_wall.replace(tzinfo=tz, fold=fold)
            candidate_utc = candidate.astimezone(timezone.utc)
            round_trip = candidate_utc.astimezone(tz)
            if (round_trip.replace(tzinfo=None) == candidate_wall
                    and round_trip.fold == fold):
                candidates.add(candidate_utc)
        if candidates:
            return max(candidates) if latest else min(candidates)
    return None


def quiet_decision(now_utc: datetime, prefs: AlertPrefs) -> tuple:
    """('send', None), ('defer', <window-open instant, UTC>), or unevaluable.

    UTC is the explicit default only when the user has no stored timezone.  An invalid
    stored timezone paired with quiet hours is not silently reinterpreted as UTC.
    """
    if not prefs.quiet:
        return "send", None
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        tz = ZoneInfo(prefs.tz)
    except (ZoneInfoNotFoundError, ValueError, KeyError, TypeError):
        return "unevaluable", None
    start_m, end_m = prefs.quiet
    if start_m == end_m:
        return "send", None
    local_day = now_utc.astimezone(tz).date()
    for start_day in (local_day - timedelta(days=1), local_day):
        end_day = start_day if start_m < end_m else start_day + timedelta(days=1)
        start_utc = _wall_instant_utc(start_day, start_m, tz, latest=False)
        end_utc = _wall_instant_utc(end_day, end_m, tz, latest=True)
        if start_utc is None or end_utc is None:
            return "unevaluable", None
        if start_utc <= now_utc < end_utc:
            return "defer", end_utc
    return "send", None


# --------------------------------------------------------------------------- #
# Entitlement -- fail-closed (freeze section 5); NOT app.billing.read_entitlement,
# which fail-safes to free on any read error and would erase outage-vs-lapse.
# --------------------------------------------------------------------------- #
_LAPSED_STATUSES = {"canceled", "past_due", "unpaid", "incomplete_expired"}


_TIER_RANK = {"free": 0, "plus": 1, "pro": 2}


def entitlement_decision(read: TypedRead, now_utc: datetime, requires_tier: str | None = None) -> str:
    """'send' | 'suppress' | 'unavailable'. Fail-closed (freeze section 5): an
    unrecognised status, an unparsable period, or a tier below ``requires_tier``
    suppresses rather than sends -- this is the paid lane (MO-PAID-085/MO-PAID-027)."""
    if read.state == READ_UNAVAILABLE:
        return "unavailable"
    if read.state == READ_OK_ZERO:
        # No entitlement row at all: only a no-gate (free) alert may send.
        return "send" if not requires_tier else "suppress"
    row = (read.rows or [{}])[0]
    status = row.get("status")
    tier = row.get("tier")
    source = row.get("source")
    period_end = row.get("current_period_end")
    if not (source == "comp" and not period_end):
        if status in _LAPSED_STATUSES:
            return "suppress"
        if period_end:
            try:
                pe = datetime.fromisoformat(str(period_end).replace("Z", "+00:00"))
                if pe.tzinfo is None:
                    pe = pe.replace(tzinfo=timezone.utc)
                if pe < now_utc:
                    return "suppress"
            except Exception:  # noqa: BLE001
                return "suppress"  # unparsable period_end fails closed
    if requires_tier:
        have = _TIER_RANK.get(str(tier or "free"), -1)
        need = _TIER_RANK.get(str(requires_tier), 99)
        if have < need:
            return "suppress"
    if status in ("active", "trialing", "none") or source == "comp":
        return "send"
    return "suppress"  # fail-closed: an unrecognised status never sends


# --------------------------------------------------------------------------- #
# Decision (pure, the heart of the RED-first tests)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    deliver_after: datetime | None = None
    to_email: str | None = None
    lang: str = "en"


def decide_row(row: dict, *, user_state: str, record: dict | None,
              ent: TypedRead, suppression: TypedRead, now_utc: datetime) -> Decision:
    if user_state != READ_OK or record is None:
        return Decision(action="unevaluable", reason="prefs_unknown")
    meta = record.get("user_metadata") if isinstance(record, dict) else None
    prefs = parse_alert_prefs(meta)
    if prefs is None:
        return Decision(action="unevaluable", reason="prefs_unknown")
    to_email = str(record.get("email") or "")
    if not prefs.email_optin:
        return Decision(action="suppress", reason="not_opted_in", to_email=to_email, lang=prefs.lang)
    payload = row.get("payload") or {}
    category = payload.get("category") if isinstance(payload, dict) else None
    if not isinstance(category, str) or not category.strip():
        return Decision(action="unevaluable", reason="category_missing")
    category = category.strip()
    if category not in user_prefs.ALERT_CATEGORIES:
        return Decision(action="unevaluable", reason="category_unrecognized")
    if prefs.categories_note == "unparsed":
        return Decision(action="unevaluable", reason="alert_categories_unparsed")
    if not prefs.categories:
        return Decision(action="suppress", reason="no_alert_categories_selected",
                        to_email=to_email, lang=prefs.lang)
    if category not in prefs.categories:
        return Decision(action="suppress", reason="category_filtered", to_email=to_email, lang=prefs.lang)
    if suppression.state == READ_UNAVAILABLE:
        return Decision(action="unevaluable", reason="address_suppression_unavailable")
    if suppression.state == READ_OK and suppression.rows:
        return Decision(action="suppress", reason="address_suppressed", to_email=to_email, lang=prefs.lang)
    if ent.state == READ_UNAVAILABLE:
        return Decision(action="unevaluable", reason="entitlement_unavailable")
    requires_tier = payload.get("requires_tier")
    ent_decision = entitlement_decision(ent, now_utc, requires_tier=requires_tier)
    if ent_decision == "unavailable":
        return Decision(action="unevaluable", reason="entitlement_unavailable")
    if ent_decision == "suppress":
        return Decision(action="suppress", reason="entitlement_lapsed", to_email=to_email, lang=prefs.lang)
    if prefs.quiet_note == "unparsed":
        # An unrecognised quiet_hours shape must never fail OPEN to a silent send --
        # surface it as unevaluable (typed, counted, visible in the run receipt).
        return Decision(action="unevaluable", reason="quiet_hours_unparsed")
    action, deliver_after = quiet_decision(now_utc, prefs)
    if action == "unevaluable":
        return Decision(action="unevaluable", reason="quiet_hours_timezone_invalid")
    if action == "defer":
        return Decision(action="defer", reason="quiet_hours", deliver_after=deliver_after,
                        to_email=to_email, lang=prefs.lang)
    return Decision(action="send", reason="ok", to_email=to_email, lang=prefs.lang)


# --------------------------------------------------------------------------- #
# Two-phase run receipts
# --------------------------------------------------------------------------- #
def open_receipt(now_utc: datetime) -> tuple:
    """(run_uuid, run_id, wrote) -- POST the started row; wrote=False if unwritable."""
    run_uuid = uuid.uuid4()
    started_at_iso = now_utc.isoformat()
    run_id = f"{LANE}:{started_at_iso}:{run_uuid.hex[:8]}"
    try:
        _pg("POST", "alert_runs", body=[{
            "id": str(run_uuid), "lane": LANE, "run_id": run_id,
            "started_at": started_at_iso, "lane_cadence_budget_s": CADENCE_BUDGET_S,
        }], prefer="return=minimal")
        return str(run_uuid), run_id, True
    except Exception:  # noqa: BLE001
        return str(run_uuid), run_id, False


def close_receipt(run_uuid: str, *, outcome: str, evaluated_n: int, fired_n: int,
                  unevaluable_n: int, source_asof: str | None, error_class: str | None,
                  duplicate_n: int = 0) -> bool:
    """``duplicate_n`` is accepted (kept in the caller's ``DrainResult``/stdout summary)
    but deliberately NOT written here (review round 3 MAJOR-3): no schema file in this
    tree evidences an ``alert_runs.duplicate_n`` column, nor a jsonb ``detail``-style
    column on that table to fold it into, and the frozen table is external to this
    repo -- adding an unproven column made every ``close_receipt`` PATCH 400 (schema
    mismatch), swallowed by the except below, forcing ``outcome='partial'`` on every
    run regardless of whether a duplicate ever occurred. Ruling: no schema change;
    state the disposition in the PR body's nulls section (done)."""
    try:
        _pg("PATCH", f"alert_runs?id=eq.{urllib.parse.quote(run_uuid, safe='')}", body={
            "concluded_at": datetime.now(timezone.utc).isoformat(),
            "outcome": outcome, "evaluated_n": evaluated_n, "fired_n": fired_n,
            "unevaluable_n": unevaluable_n, "source_asof": source_asof,
            "error_class": error_class,
        }, prefer="return=minimal")
        return True
    except Exception:  # noqa: BLE001
        return False


def _patch_outbox(row_id, body: dict) -> bool:
    """PATCH one ``alert_outbox`` row; returns whether the write actually persisted.
    Review round 3 MINOR-3: a run receipt's counters must reflect writes that
    happened, not writes attempted -- every counter increment in the loop below is
    gated on this return value so a swallowed PATCH (network blip, CHECK rejection)
    can never inflate a receipt with a change that never landed.

    ``row_id`` is URL-quoted (review round 3 MINOR-2) for the same reason every
    other filter value in this module and ``close_receipt`` already is -- a
    DB-minted UUID never needs it, but an unquoted PostgREST filter value is an
    inconsistent contract with the rest of this module, not a proven-safe one."""
    try:
        _pg("PATCH", f"alert_outbox?id=eq.{urllib.parse.quote(str(row_id), safe='')}",
            body=body, prefer="return=minimal")
        return True
    except Exception:  # noqa: BLE001
        return False


def quarantine_effect_unknown(row_id, *, idem_key: str, attempts: int, cause: str) -> bool:
    """Retire ONE row whose delivery effect cannot be determined. Returns persistence.

    This is the whole point of the boundary, so be exact about what it does and does
    not claim:

      * it does NOT mark the row 'sent'   -- we cannot prove the reader got it;
      * it does NOT leave it retryable    -- we cannot prove they did not;
      * it DOES leave a durable, greppable record saying precisely that, and puts the
        row beyond ``drain()``'s own selection predicate so no later tick can quietly
        convert the uncertainty into a second delivery.

    ``attempts`` is forced to the cap rather than incremented: an increment would
    still re-select the row while it sat below the cap, and every re-selection mints a
    fresh idempotency key -- the exact licence being withheld. The ``::warning`` is
    how a human learns the row exists, because nothing else will ever resolve it.
    """
    ok = _patch_outbox(row_id, {
        "status": "failed",
        "attempts": max(int(attempts or 0), int(ALERT_RETRY_ATTEMPTS_CAP)),
        "last_error": EFFECT_UNKNOWN_LAST_ERROR,
    })
    print("::warning title=alert-drain-effect-unknown::"
          "idem_key %s entered SMTP and never recorded an outcome (%s) -- outbox row %s "
          "quarantined: NOT resent, NOT marked delivered. Confirm against the relay log "
          "before any manual replay.%s"
          % (idem_key, cause, row_id, "" if ok else " WARNING: the quarantine PATCH did "
             "not persist; the row may still be retryable."),
          flush=True)
    return ok


def derive_outcome(*, read_state: str, unevaluable_n: int,
                   failed_n: int, degraded_n: int) -> str:
    if read_state == READ_UNAVAILABLE:
        return "failure"
    if unevaluable_n > 0 or failed_n > 0 or degraded_n > 0:
        return "partial"
    return "success"


# --------------------------------------------------------------------------- #
# The one entry function
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DrainResult:
    outcome: str
    evaluated_n: int
    fired_n: int
    unevaluable_n: int
    deferred_n: int
    suppressed_n: int
    failed_n: int
    category_unfiltered_n: int
    duplicate_n: int
    # Rows whose delivery effect could not be determined and were therefore
    # quarantined rather than retried, and rows left untouched because a writer may
    # still be inside SMTP. Both are CODE-level only: no alert_runs column is written
    # for either (review round 3 MAJOR-3's ruling on unproven schema stands -- an
    # unverified column makes every close_receipt PATCH 400 and silently forces
    # outcome='partial' on every run). They reach an operator through the stdout
    # summary in scripts/drain_alert_outbox.py and the ::warning above.
    effect_unknown_n: int
    in_flight_n: int
    read_state: str
    error_class: str | None
    run_id: str | None
    receipt_written: bool
    selector_state: str | None = None


def _selector_failure(state: str, *, read_state: str) -> DrainResult:
    """A canary selector failed cardinality/identity checks before any effect."""
    return DrainResult(outcome="failure", evaluated_n=0, fired_n=0, unevaluable_n=0,
                       deferred_n=0, suppressed_n=0, failed_n=0,
                       category_unfiltered_n=0, duplicate_n=0, effect_unknown_n=0,
                       in_flight_n=0, read_state=read_state, error_class=state,
                       run_id=None, receipt_written=False, selector_state=state)


def drain(*, send_fn: Callable[..., str] | None, now_utc: datetime | None = None,
         limit: int = 200, dry_run: bool = False,
         fire_event_id: str | None = None) -> DrainResult:
    """Drain one batch. NEVER raises for a delivery reason.

    ``send_fn(fire_event_id=..., to_email=..., payload=..., lang=..., user_id=...,
    attempt=...) -> str`` returning a value in ``app.mailer.RESULTS`` -- i.e.
    ``STATUSES`` + ``'duplicate'`` + ``'effect_unknown'``. That last value is
    load-bearing, not decorative: a send_fn written to the older
    ``STATUSES + 'duplicate'`` contract sends an undetermined delivery down this
    function's failure branch, which increments ``attempts`` and so mints a fresh
    idempotency key -- reintroducing the exact duplicate this boundary prevents. Injected so this module never imports ``app/`` (see the module
    docstring's Layering note). ``send_fn=None`` or ``dry_run=True`` => decisions
    computed, ZERO sends, ZERO writes.

    A 'failed' row is re-selected only while ``attempts < ALERT_RETRY_ATTEMPTS_CAP`` --
    once capped it stays 'failed' but drops out of the ``or=(...)`` predicate below, so
    it is never retried again and never silently reappears as unaccounted-for.

    ``fire_event_id`` is the canary lane. It is applied server-side and forces a
    two-row read so cardinality can be proven. Before opening a run receipt or touching
    user state, preferences, SMTP, or an outbox row, the result must contain exactly
    one row whose returned identity exactly matches the requested value.
    """
    if fire_event_id is not None and not str(fire_event_id).strip():
        raise ValueError("fire_event_id selector must not be blank")

    now_utc = now_utc or datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()

    selector_filter = ""
    read_limit = int(limit)
    if fire_event_id is not None:
        selector_filter = ("&fire_event_id=eq."
                           + urllib.parse.quote(str(fire_event_id), safe=""))
        read_limit = 2

    outbox_read = typed_get(
        "alert_outbox?channel=eq.email"
        f"{selector_filter}"
        "&or=(status.eq.pending,"
        f"and(status.eq.failed,attempts.lt.{int(ALERT_RETRY_ATTEMPTS_CAP)}),"
        f"and(status.eq.deferred,deliver_after.lte.{urllib.parse.quote(now_iso)}))"
        "&select=id,user_id,alert_id,fire_event_id,status,payload,attempts,deliver_after"
        f"&order=created_at.asc&limit={read_limit}")

    # Canary validation happens before the receipt is opened. A selector that is
    # unreadable, ambiguous, absent, or contradicted by the returned identity has no
    # permitted effect beyond this one bounded read.
    if fire_event_id is not None:
        if outbox_read.state == READ_UNAVAILABLE:
            return DrainResult(outcome="failure", evaluated_n=0, fired_n=0,
                               unevaluable_n=0, deferred_n=0, suppressed_n=0,
                               failed_n=0, category_unfiltered_n=0, duplicate_n=0,
                               effect_unknown_n=0, in_flight_n=0,
                               read_state=READ_UNAVAILABLE,
                               error_class=outbox_read.error_class, run_id=None,
                               receipt_written=False)
        selector_rows = outbox_read.rows or []
        if not selector_rows:
            return _selector_failure(SELECTOR_NO_MATCH, read_state=outbox_read.state)
        if len(selector_rows) != 1:
            return _selector_failure(SELECTOR_MULTIPLE_MATCH, read_state=outbox_read.state)
        selector_row = selector_rows[0]
        if (not isinstance(selector_row, dict)
                or str(selector_row.get("fire_event_id")) != str(fire_event_id)):
            return _selector_failure(SELECTOR_MISMATCH, read_state=outbox_read.state)

    run_uuid, run_id, wrote = (None, None, False) if dry_run else open_receipt(now_utc)

    if outbox_read.state == READ_UNAVAILABLE:
        receipt_written = False
        if not dry_run and run_uuid is not None:
            receipt_written = close_receipt(
                run_uuid, outcome="failure", evaluated_n=0, fired_n=0, unevaluable_n=0,
                source_asof=None, error_class=outbox_read.error_class) and wrote
        return DrainResult(outcome="failure", evaluated_n=0, fired_n=0, unevaluable_n=0,
                           deferred_n=0, suppressed_n=0, failed_n=0, category_unfiltered_n=0,
                           duplicate_n=0, effect_unknown_n=0, in_flight_n=0,
                           read_state=READ_UNAVAILABLE, error_class=outbox_read.error_class,
                           run_id=run_id, receipt_written=receipt_written)

    rows = outbox_read.rows or []

    evaluated_n = fired_n = unevaluable_n = deferred_n = suppressed_n = failed_n = 0
    category_unfiltered_n = 0
    duplicate_n = 0
    degraded_n = 0
    effect_unknown_n = 0
    in_flight_n = 0
    fired_ats = []

    for row in rows:
        evaluated_n += 1
        raw_payload = row.get("payload")
        payload = raw_payload if isinstance(raw_payload, dict) else {}
        if payload.get("category") is None:
            category_unfiltered_n += 1
        user_id = row.get("user_id")

        user_state, record = fetch_user_record(str(user_id)) if user_id else (READ_UNAVAILABLE, None)
        suppression = TypedRead(READ_UNAVAILABLE, None)
        ent = TypedRead(READ_UNAVAILABLE, None)
        if user_state == READ_OK and record is not None:
            addr = str(record.get("email") or "").strip().lower()
            suppression = typed_get(f"email_suppression?email=eq.{urllib.parse.quote(addr, safe='')}&select=email,reason") if addr else TypedRead(READ_OK_ZERO, [])
            ent = typed_get(f"user_entitlements?user_id=eq.{urllib.parse.quote(str(user_id), safe='')}&select=tier,status,current_period_end,source")

        decision = decide_row(row, user_state=user_state, record=record, ent=ent,
                              suppression=suppression, now_utc=now_utc)

        if decision.action == "unevaluable":
            unevaluable_n += 1
            continue

        if dry_run or send_fn is None:
            if decision.action == "send":
                fired_n += 1
            elif decision.action == "defer":
                deferred_n += 1
            elif decision.action == "suppress":
                suppressed_n += 1
            continue

        if decision.action == "defer":
            ok = _patch_outbox(row["id"], {"status": "deferred",
                                            "deliver_after": decision.deliver_after.isoformat()})
            if ok:
                deferred_n += 1
            else:
                degraded_n += 1  # review round 5 MAJOR: a swallowed PATCH must still
                                 # count somewhere, or the run receipt reads clean.
            continue

        if decision.action == "suppress":
            ok = _patch_outbox(row["id"], {"status": "suppressed", "last_error": decision.reason})
            if ok:
                suppressed_n += 1
            else:
                degraded_n += 1
            continue

        # action == send
        fire_event_id = row.get("fire_event_id")
        attempt_n = int(row.get("attempts") or 0)
        try:
            status = send_fn(fire_event_id=fire_event_id, to_email=decision.to_email,
                             payload=payload, lang=decision.lang, user_id=user_id,
                             attempt=attempt_n)
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error_cls = type(exc).__name__
        else:
            error_cls = None

        if status == "duplicate":
            # A mailer 'duplicate' means email_log's UNIQUE idem_key was already claimed
            # -- it does NOT mean the earlier attempt actually sent (review round 2
            # blocker, acceptance 1(d)): the prior claim could equally be a failed,
            # suppressed, or still-queued send. Read that row rather than assume. The
            # key read back is the SAME one just attempted (same fire_event_id+attempt)
            # -- never the bare attempt=0 key -- so a retry's own claim is what gets
            # resolved, not the original attempt's.
            # select= carries `status,detail`. Review round 5 MINOR-1 had narrowed
            # this to `status` alone because nothing read `detail` -- that reasoning
            # was correct then and is superseded now, not reverted by accident:
            # `detail` is where the SMTP attempt marker lives, and it is the ONLY
            # thing that distinguishes a claim that never reached the transport from
            # one that did (see `classify_ledger_queued`). Reading it back is now
            # load-bearing, so the exposure that note weighed is worth paying.
            # Review round 6
            # MINOR-1: `created_at` was read as `delivered_at` below, but
            # `research/SUPPORT_EMAIL_ESTATE_MASTERPLAN_BY_FABLE.md`'s `email_log`
            # DDL stamps `created_at` at INSERT time -- `_ledger_insert`
            # (`app/mailer.py`) writes the row at `status='queued'` BEFORE SMTP is
            # touched, so `created_at` is the claim time, not the delivery time, and
            # was systematically early on every duplicate-resolved row. `email_log`
            # has no separate sent/updated timestamp column (no `updated_at`, no
            # `sent_at` -- confirmed against the DDL above and every migration under
            # `scripts/deploy/`), so there is nothing truthful to read back for "when
            # the prior attempt sent"; the drain's OWN resolution time is used
            # instead, which is never earlier than the real send and is honest about
            # what is actually known.
            idem_key = _alert_idem_key(str(fire_event_id), attempt=attempt_n)
            log_read = typed_get(
                f"email_log?idem_key=eq.{urllib.parse.quote(idem_key, safe='')}"
                "&select=status,detail,created_at")
            log_row = (log_read.rows or [None])[0] if log_read.state == READ_OK else None
            log_status = log_row.get("status") if log_row else None
            if log_status == "sent":
                # The earlier attempt genuinely sent -- mirror THAT fact, counted as a
                # duplicate resolution, never as a fresh fire. delivered_at is the
                # drain's own resolution time (see MINOR-1 note above), never
                # email_log's created_at.
                delivered_at = now_utc.isoformat()
                ok = _patch_outbox(row["id"], {"status": "sent", "delivered_at": delivered_at,
                                                "last_error": None})
                if ok:
                    duplicate_n += 1
                else:
                    degraded_n += 1
            elif log_status == "failed":
                # Review round 3 BLOCKER: this idem_key is now TERMINAL -- the real
                # mailer never revisits a claimed key's terminal status, so retrying
                # under the SAME key would read 'failed' forever (livelock). Bump
                # attempts here (this WAS the bug: the old code left attempts
                # unchanged on this exact path) so the next tick's send_fn call mints
                # a fresh key via ``attempt_n`` above, and the selection predicate's
                # cap eventually retires the row instead of looping forever.
                new_attempts = int(row.get("attempts") or 0) + 1
                ok = _patch_outbox(row["id"], {"status": "failed", "attempts": new_attempts,
                                                "last_error": "prior send failed"})
                if ok:
                    duplicate_n += 1
                    failed_n += 1
                else:
                    degraded_n += 1
            elif log_status == "suppressed":
                ok = _patch_outbox(row["id"], {"status": "suppressed",
                                                "last_error": "prior send suppressed"})
                if ok:
                    duplicate_n += 1
                    suppressed_n += 1
                else:
                    degraded_n += 1
            elif log_status == "queued":
                # The ambiguous one. A durable 'queued' is THREE states, and the old
                # code answered all three with "bump attempts" -- which mints a fresh
                # idempotency key next tick and so permits another SMTP delivery of
                # the same logical alert. That is safe for exactly one of them.
                kind = classify_ledger_queued(log_row.get("detail"), now_utc=now_utc,
                                              created_at=log_row.get("created_at"))
                if kind == EFFECT_UNKNOWN:
                    # The transport WAS entered and no outcome was ever recorded. The
                    # message may be in the reader's inbox. Never resend, never claim
                    # delivered -- quarantine and tell a human.
                    if quarantine_effect_unknown(row["id"], idem_key=idem_key,
                                                 attempts=attempt_n,
                                                 cause="ledger stayed queued past the "
                                                       "in-flight grace window"):
                        duplicate_n += 1
                    effect_unknown_n += 1
                    degraded_n += 1
                elif kind == "in_flight":
                    # A marker younger than the grace window may belong to a writer
                    # that is STILL inside SMTP (a slow relay, a previous tick that
                    # has not returned). Touch nothing: bumping `attempts` here would
                    # mint a fresh key next tick and race a live send, and marking the
                    # row would record an outcome nobody has yet. Counted so the run
                    # reads 'partial' rather than clean, and re-examined next tick.
                    degraded_n += 1
                    in_flight_n += 1
                else:
                    # PROVABLY pre-send: the transport was never entered (a bare claim
                    # whose process died, or the marketing suppression park at
                    # `detail='suppression_lookup_failed'`). Nothing was delivered, so
                    # the fresh-key retry below is exactly right -- this is the case
                    # the original code was written for, kept intact.
                    #
                    # Review round 6 MAJOR (amended ruling): `attempts` MUST still
                    # increment on every tick that touches this row, even though
                    # `status` stays 'pending' -- leaving it unchanged means
                    # `attempt_n` is byte-identical next tick, `_alert_idem_key` mints
                    # the SAME key, the mailer's unique constraint claims it as
                    # 'duplicate' again forever, and this branch re-fires every 5
                    # minutes with no way out. Once `attempts` reaches the cap the row
                    # is retired instead of looping.
                    new_attempts = int(row.get("attempts") or 0) + 1
                    if new_attempts >= ALERT_RETRY_ATTEMPTS_CAP:
                        ok = _patch_outbox(row["id"], {
                            "status": "failed", "attempts": new_attempts,
                            "last_error": "suppression_lookup_failed"})
                        if ok:
                            duplicate_n += 1
                            failed_n += 1
                        else:
                            degraded_n += 1
                    else:
                        ok = _patch_outbox(row["id"], {"status": "pending",
                                                        "attempts": new_attempts,
                                                        "last_error": "prior send queued"})
                        if ok:
                            duplicate_n += 1
                        degraded_n += 1
            elif log_status is not None:
                # 'skipped_no_smtp' (or any other readable, non-terminal mailer status
                # that is not 'queued' -- that one is handled above, because only it
                # can mean the transport was already entered): NOT a failure and NOT a
                # success, so it must not be
                # mirrored into alert_outbox's own CHECK-constrained status column --
                # neither value is a legal alert_outbox status (review round 3
                # MAJOR-2; the old code wrote it verbatim, which either violated the
                # CHECK constraint -- silently swallowed -- or, had it been accepted,
                # permanently orphaned the row outside this drain's own selection
                # predicate). The row stays 'pending' so the next tick re-selects it.
                #
                # Review round 6 MAJOR (amended ruling): `attempts` MUST still
                # increment on every tick that touches this row, even though
                # `status` stays 'pending' -- this is the exact bug the review
                # found: leaving `attempts` unchanged means `attempt_n` (read from
                # `attempts` at the top of the `action == send` branch) is
                # byte-identical next tick, so `_alert_idem_key` mints the SAME key,
                # the real mailer's unique constraint claims it as 'duplicate' again
                # forever, and this branch re-fires every 5 minutes with no way out.
                # Bumping `attempts` here mints a fresh `alert_fire:<id>:<n+1>` key
                # next tick (same mechanism as the terminal-'failed' branch above),
                # and once `attempts` reaches the cap the row is retired instead
                # of looping forever -- visible and out of the selection
                # predicate, never a silent livelock. Cause label follows the
                # mailer status: queued is a failed suppression lookup
                # (app/mailer.py:27-33, ``suppression_lookup_failed``), not SMTP.
                new_attempts = int(row.get("attempts") or 0) + 1
                if new_attempts >= ALERT_RETRY_ATTEMPTS_CAP:
                    ok = _patch_outbox(row["id"], {"status": "failed", "attempts": new_attempts,
                                                    "last_error": "smtp_unavailable"})
                    if ok:
                        duplicate_n += 1
                        failed_n += 1
                    else:
                        degraded_n += 1
                else:
                    ok = _patch_outbox(row["id"], {"status": "pending", "attempts": new_attempts,
                                                    "last_error": f"prior send {log_status}"})
                    if ok:
                        duplicate_n += 1
                        degraded_n += 1
                    else:
                        degraded_n += 1
            else:
                # Unreadable (READ_UNAVAILABLE) or a zero-row read that contradicts the
                # 'duplicate' claim -- either way we do not know what the prior send did,
                # so the row is left exactly as it was: pending, attempts unchanged, never
                # sent. Typed, printed, never silent.
                degraded_n += 1
                print("::warning title=alert-drain-duplicate-unreadable::"
                      "email_log row for idem_key %s state=READ_UNAVAILABLE (%s) -- outbox "
                      "row %s left pending, never marked sent"
                      % (idem_key, log_read.error_class or "no_matching_row", row["id"]),
                      flush=True)
        elif status == "sent":
            fired_at = payload.get("fired_at")
            ok = _patch_outbox(row["id"], {"status": "sent",
                                            "delivered_at": now_utc.isoformat(),
                                            "attempts": int(row.get("attempts") or 0) + 1,
                                            "last_error": None})
            if ok:
                fired_n += 1
                if fired_at:
                    fired_ats.append(str(fired_at))
            else:
                # Review round 5 MAJOR: send_fn actually sent the mail, but the
                # persisting PATCH failed -- if nothing is counted here the run
                # receipt reads outcome='success' with fired_n=0 (a false clean),
                # even though a real send happened with no durable record of it.
                # degraded_n makes derive_outcome report 'partial', matching every
                # other swallowed-PATCH path in this loop.
                degraded_n += 1
        elif status == EFFECT_UNKNOWN:
            # The mailer told us, in this very process, that it entered SMTP and never
            # learned the outcome. No grace window is needed -- we have its own word
            # for it. Same treatment as the durable case: never resend, never claim
            # delivered, retire the row and surface it.
            idem_key = _alert_idem_key(str(fire_event_id), attempt=attempt_n)
            quarantine_effect_unknown(row["id"], idem_key=idem_key, attempts=attempt_n,
                                      cause="mailer reported effect_unknown in-process")
            effect_unknown_n += 1
            degraded_n += 1
        elif status in ("skipped_no_smtp", "queued"):
            # Not a failure -- a config/transient gap (mail-off, or a marketing-only
            # ledger race that should never reach this transactional class in
            # practice). Leave the row 'pending' so the next tick tries again, rather
            # than mirroring a non-alert_outbox status (review round 3 MINOR-2;
            # mirrors the duplicate-branch treatment above).
            #
            # Review round 6 MAJOR (amended ruling): `attempts` MUST still
            # increment on every tick, even while `status` stays 'pending' --
            # otherwise `attempt_n` is byte-identical next tick, `_alert_idem_key`
            # mints the SAME key, the real mailer's unique constraint claims it as
            # 'duplicate' forever, and the row loops every 5 minutes with no way
            # out (this is the exact livelock the review found at this line). Once
            # `attempts` reaches the cap the row is retired to
            # retired -- visible and out of the selection predicate -- instead
            # of looping forever. queued names the mailer contract cause
            # (suppression_lookup_failed); skipped_no_smtp stays smtp_unavailable.
            new_attempts = int(row.get("attempts") or 0) + 1
            if new_attempts >= ALERT_RETRY_ATTEMPTS_CAP:
                cause = ("suppression_lookup_failed" if status == "queued"
                         else "smtp_unavailable")
                ok = _patch_outbox(row["id"], {"status": "failed", "attempts": new_attempts,
                                                "last_error": cause})
                if ok:
                    failed_n += 1
                else:
                    degraded_n += 1
            else:
                ok = _patch_outbox(row["id"], {"status": "pending", "attempts": new_attempts,
                                                "last_error": status})
                # Persisted or not, this decision is not-a-failure/not-a-success
                # either way -- degraded_n counts it unconditionally (no
                # false-clean risk here, unlike the ok-gated branches above/below).
                degraded_n += 1
        elif status == "suppressed":
            ok = _patch_outbox(row["id"], {"status": "suppressed", "last_error": status})
            if ok:
                suppressed_n += 1
            else:
                degraded_n += 1
        else:
            # "failed", or any status outside app.mailer.STATUSES -- fail-closed as a
            # real send failure: attempts increments (bounded by the retry cap above).
            new_attempts = int(row.get("attempts") or 0) + 1
            ok = _patch_outbox(row["id"], {"status": "failed", "attempts": new_attempts,
                                            "last_error": error_cls or status})
            if ok:
                failed_n += 1
            else:
                degraded_n += 1

    outcome = derive_outcome(read_state=outbox_read.state,
                             unevaluable_n=unevaluable_n, failed_n=failed_n, degraded_n=degraded_n)

    receipt_written = False
    if not dry_run and run_uuid is not None:
        source_asof = max(fired_ats) if fired_ats else None
        receipt_written = close_receipt(run_uuid, outcome=outcome, evaluated_n=evaluated_n,
                                        fired_n=fired_n, unevaluable_n=unevaluable_n,
                                        source_asof=source_asof, error_class=None,
                                        duplicate_n=duplicate_n) and wrote
        if not receipt_written and outcome == "success":
            # The run's own provenance failed to persist -- freeze section 4's
            # fallback => partial applies to the receipt path itself, not only to
            # the rows evaluated (2(ii)): a run nobody can audit is never "success".
            outcome = "partial"

    return DrainResult(outcome=outcome, evaluated_n=evaluated_n, fired_n=fired_n,
                       unevaluable_n=unevaluable_n, deferred_n=deferred_n,
                       suppressed_n=suppressed_n, failed_n=failed_n,
                       category_unfiltered_n=category_unfiltered_n,
                       duplicate_n=duplicate_n, effect_unknown_n=effect_unknown_n,
                       in_flight_n=in_flight_n,
                       read_state=outbox_read.state, error_class=None,
                       run_id=run_id, receipt_written=receipt_written)
