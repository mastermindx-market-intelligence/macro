"""FIF saved-research notifications producer (X2-n, spec §5).

Enqueue-only projection over THREE existing owners — no new analysis lifecycle,
no scoring, no send (A7: notifications relay engine-emitted facts only):

  - the subscription surface is the designated Supabase watchlist named
    "Filing Forensics" (seat ruling R2 / OSD-2(A)) read SERVICE-SIDE exactly the
    way engine/recurring_briefs.py:666-671 reads brief_subscriptions and
    engine/thesis_condition_monitor.py reads theses — same env names, same
    REST client shape. The watchlists schema carries NO kind/system/metadata
    column (Terminal 0001_init.sql:29-36, census C2), so the list is identified
    by its verbatim stored name. Absence of the list, or of a symbol on it,
    IS "no subscription" — removing either is the unsubscribe.
  - the trigger inputs are LOCAL files on the nightly runner (census C6):
    the FIF private state data/fundamental_forensics/private/state.json.gz
    (written by scripts/build_fundamental_forensics earlier in the same engine
    job) and two documented local mirrors that DO NOT EXIST YET because their
    upstreams write only to the private R2 research vault — the broad-SEC run
    receipt and the production generation pointer. The producer NEVER reads
    R2: a missing input is "no event" (seat ruling R5), never an error.
  - the queue is the existing public.alert_outbox (Terminal 0013); delivery
    belongs to F08's drain (scripts/drain_alert_outbox.py), never this module.

Dedupe: alert_outbox's UNIQUE(fire_event_id) plus a pre-insert SELECT of the
ids this run would mint (the thesis monitor's belt-and-braces shape,
engine/thesis_condition_monitor.py:626-637). fire_event_id is the FROZEN
literal concatenation "fif:" kind ":" cik ":" event_ref ":" user_id (spec §5
dedupe key) — kind in {new_filing, generation, high_finding}; event_ref is
the accession / generation_id / engine finding id.

NO-LEAK (spec gate 3): a row is emitted for user U only for a ticker on U's
OWN designated list. derive_events() returns (user_id, event) pairs and the
per-user partition is built before any event is derived, so nothing from any
other user's list can ever enter U's rows.

Payload: exactly the compose_alert contract fields (app/mailer.py:1379-1430)
plus the category the drain filters on (engine/alert_delivery_drain.py:495,
:499, :506 — payload["category"]). No values, no scores, no slugs; glance-tier
strings obey the same banned-token discipline as the thesis monitor's
(engine/thesis_condition_monitor.py:121) and the mailer's _ALERT_BANNED_TOKENS
(app/mailer.py:1334-1337) — a relayed engine title carrying a banned token
falls back to a neutral sentence rather than being sent verbatim.

Fail-soft: missing credentials/tables/inputs produce a typed unavailable
state with ZERO rows; this module never raises for a deployment reason and
never writes a local file.
"""
from __future__ import annotations

import json
import os
import re
import uuid as _uuid_mod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://fsldfzlxyavsuwqbceod.supabase.co"
).rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
EVIDENCE_BASE = "https://www.mastermind-x.com"
SOURCE = "macro.fif_saved_research_notifications"
CATEGORY = "fif_saved_issuer"
CHANNEL = "email"

# R2 (seat ruling R2): ONE verbatim stored system name. The FIF UI shows a
# localized label; the stored row is identified by this exact, case-sensitive
# name against the schema's unique (user_id, name) index.
DESIGNATED_LIST_NAME = "Filing Forensics"

FIF_PAGE = "fundamental_forensics.html"

READ_OK, READ_OK_ZERO, READ_UNAVAILABLE = (
    "READ_OK",
    "READ_OK_ZERO",
    "READ_UNAVAILABLE",
)

KIND_NEW_FILING = "new_filing"
KIND_GENERATION = "generation"
KIND_HIGH_FINDING = "high_finding"
KINDS = (KIND_NEW_FILING, KIND_GENERATION, KIND_HIGH_FINDING)

# Seat ruling R3 (X2-n r1): high findings are recency-gated so arming the
# flag — or a user's first watch — never sends the whole backlog. The anchor
# is the state document's `as_of` (the max latest_filed across the universe,
# scripts/build_fundamental_forensics.py:1209,1224 — a YYYY-MM-DD string),
# NEVER wall-clock time; the per-finding date is the filed date of the
# finding's current period (its first `evidence` entry whose basis ==
# "filing_index", :212-231,291), never the company's latest_filed.
# new_filing and generation events are NOT gated by this rule.
FIF_NEW_FINDING_WINDOW_DAYS = 14

# Typed suppression counts (R3d) in a deterministic key order: fail closed,
# never a silent drop. Counted per CANDIDATE high-finding event (user x
# finding), matching the pair accounting of events_n everywhere else.
SUPPRESSION_KEYS = (
    "high_finding_as_of_missing",      # as_of absent/unparseable -> every high finding
    "high_finding_date_missing",       # no parseable filing_index date
    "high_finding_date_after_as_of",   # finding_date > as_of
    "high_finding_outside_window",     # older than FIF_NEW_FINDING_WINDOW_DAYS
)

# Only a leading YYYY-MM-DD is honored; anything else counts as missing.
_LEADING_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

# Glance-tier banned tokens — the thesis monitor's discipline
# (engine/thesis_condition_monitor.py:121). The mailer applies its own wider
# list at render time (app/mailer.py:1334-1337); this guards what we PERSIST.
_BANNED_TERMS = ("falsif", "refut", "证伪")

# A fixed, arbitrary namespace UUID for synthesizing alert_outbox.alert_id
# values (uuid5) from the conceptual "fif_saved_issuer:<user_id>" identity —
# the pattern of the thesis monitor's _ALERT_ID_NAMESPACE (:126): one stable
# synthetic alert_id per user's FIF watch, across every event it produces.
# Never change this constant — doing so would re-mint every user's id.
_ALERT_ID_NAMESPACE = _uuid_mod.UUID("b1f0d2a4-7c39-5e81-9a2b-4d6e8f0a1c30")

# Local trigger-input mirrors (census C6). Upstream writes these artifacts to
# the private R2 research vault today (filing-forensics-broad-sec.yml /
# filing-forensics-sec.yml, permissions: contents: read, no store-dir), so
# neither path exists on the daily runner: both triggers read "no event" (R5)
# until a local mirror is wired. The producer never reads R2.
BROAD_SEC_RECEIPT_RELATIVE = Path("data/fundamental_forensics/broad_sec/latest-receipt.json")
PRODUCTION_POINTER_RELATIVE = Path("data/fundamental_forensics/production/latest.json")
# The broad-SEC receipt's change_summary carries COUNTERS ONLY
# (engine/fundamental_forensics/broad_sec_store.py:2621-2626); it cannot name
# an accession. new_filing events therefore derive exclusively from this
# optional per-CIK detail map a future mirror must carry:
#   {"run_id": ..., "change_summary": {...},
#    "new_relevant_accessions_by_cik": {"0000320193": ["0000320193-25-000073"]}}
RECEIPT_DETAIL_KEY = "new_relevant_accessions_by_cik"
# The production pointer mirror contract (one entry per issuer CIK):
#   {"generations": {"0000320193": {"generation_id": "ffprods_...", "admitted_at": "...Z"}}}
POINTER_GENERATIONS_KEY = "generations"


@dataclass(frozen=True)
class TypedRead:
    state: str
    rows: list | None
    error_class: str | None = None


@dataclass(frozen=True)
class TriggerInputs:
    """Local trigger artifacts, each independently absent-or-loaded."""

    state_doc: dict | None = None
    receipt: dict | None = None
    pointer: dict | None = None
    state_state: str = READ_UNAVAILABLE
    receipt_state: str = READ_UNAVAILABLE
    pointer_state: str = READ_UNAVAILABLE


@dataclass(frozen=True)
class FifEvent:
    kind: str
    cik: str
    ticker: str
    event_ref: str
    condition_plain: str
    subject: str
    fired_at: str | None
    # R3f: the date the payload records for this event — the finding's
    # filing_index date (YYYY-MM-DD) for high_finding, None for kinds
    # without one.
    event_date: str | None = None


@dataclass(frozen=True)
class ProducerPlan:
    rows: list[dict]
    users_n: int
    symbols_n: int
    events_n: int
    duplicate_n: int
    # R3e: typed suppression counts (SUPPRESSION_KEYS order, deterministic).
    suppressed: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ProducerResult:
    outcome: str
    read_state: str
    error_class: str | None
    users_n: int
    symbols_n: int
    events_n: int
    enqueued_n: int
    duplicate_n: int
    planned_n: int
    state_state: str
    receipt_state: str
    pointer_state: str
    notes: list[str] = field(default_factory=list)
    # R3e: carried from the final plan so the runner can print the counts.
    suppressed: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pure functions — no IO
# ---------------------------------------------------------------------------

def cik10(value: Any) -> str | None:
    """Normalize a CIK to the canonical zero-padded 10-digit string (the
    `_cik10` form scripts/build_fundamental_forensics.py:1164-1169 joins the
    issuer master by). None when the value is not a CIK."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        n = int(text)
    except ValueError:
        return None
    if n < 0:
        return None
    return f"{n:010d}"


def fire_event_id(*, kind: str, cik: str, event_ref: str, user_id: str) -> str:
    """The FROZEN dedupe key (spec §5): literal concatenation, no hashing.
    UNIQUE(fire_event_id) makes replays no-ops."""
    return f"fif:{kind}:{cik}:{event_ref}:{user_id}"


def synthetic_alert_id(user_id: str) -> str:
    """Deterministic per-user synthetic `alert_outbox.alert_id` (uuid5 of the
    conceptual "fif_saved_issuer:<user_id>" identity — the thesis monitor's
    synthetic_alert_id pattern, :318-323). Stable across every event produced
    for the same user's watch; NOT a foreign key into any real Alerts-table
    row."""
    return str(_uuid_mod.uuid5(_ALERT_ID_NAMESPACE, f"fif_saved_issuer:{user_id}"))


def _plain(text: Any, fallback: str) -> str:
    """Banned-token guard for every glance-tier string this module persists —
    mirrors app/mailer.py's _alert_plain fallback semantics (:1356-1361)."""
    value = str(text or "")
    if not value or any(term in value for term in _BANNED_TERMS):
        return fallback
    return value


def evidence_url(ticker: str, evidence_base: str = EVIDENCE_BASE) -> str:
    return f"{evidence_base.rstrip('/')}/{FIF_PAGE}?symbol={ticker}"


# ---------------------------------------------------------------------------
# R3 recency gate — pure date parsing, no wall-clock anywhere
# ---------------------------------------------------------------------------
def _parse_leading_date(value: Any) -> date | None:
    """A leading YYYY-MM-DD only (R3c). Anything else — including a date-like
    string with a bad month/day — counts as missing, never an error."""
    text = str(value or "").strip()
    match = _LEADING_DATE_RE.match(text)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _finding_filed_date(finding: Any) -> date | None:
    """The filed date of the finding's current period: the `date` of its FIRST
    `evidence` entry whose `basis` == "filing_index"
    (scripts/build_fundamental_forensics.py:212-231,291 — _source_links emits
    the filing_index link first, carrying the current period's `filed`). The
    company's own latest_filed is NEVER substituted (R3c)."""
    evidence = finding.get("evidence") if isinstance(finding, dict) else None
    if not isinstance(evidence, (list, tuple)):
        return None
    for entry in evidence:
        if isinstance(entry, dict) and entry.get("basis") == "filing_index":
            return _parse_leading_date(entry.get("date"))
    return None


def _high_finding_gate(event: FifEvent, as_of: date | None) -> str | None:
    """None = emit. Otherwise the typed suppression key (R3d): a high finding
    row is emitted only when 0 <= (as_of - finding_date).days <=
    FIF_NEW_FINDING_WINDOW_DAYS, checked fail-closed in SUPPRESSION_KEYS
    order. new_filing and generation events never reach this gate."""
    if as_of is None:
        return "high_finding_as_of_missing"
    filed = _parse_leading_date(event.event_date)
    if filed is None:
        return "high_finding_date_missing"
    if filed > as_of:
        return "high_finding_date_after_as_of"
    if (as_of - filed).days > FIF_NEW_FINDING_WINDOW_DAYS:
        return "high_finding_outside_window"
    return None


def _receipt_detail(receipt: Any) -> dict[str, list[str]]:
    if not isinstance(receipt, dict):
        return {}
    detail = receipt.get(RECEIPT_DETAIL_KEY)
    if not isinstance(detail, dict):
        return {}
    out: dict[str, list[str]] = {}
    for raw_cik, raw_list in detail.items():
        cik = cik10(raw_cik)
        if cik is None or not isinstance(raw_list, (list, tuple)):
            continue
        out[cik] = [str(a) for a in raw_list if str(a or "").strip()]
    return out


def _pointer_generations(pointer: Any) -> dict[str, dict]:
    if not isinstance(pointer, dict):
        return {}
    generations = pointer.get(POINTER_GENERATIONS_KEY)
    if not isinstance(generations, dict):
        return {}
    out: dict[str, dict] = {}
    for raw_cik, entry in generations.items():
        cik = cik10(raw_cik)
        if cik is not None and isinstance(entry, dict):
            out[cik] = entry
    return out


def derive_events(
    *,
    subscriptions: dict[str, set[str]],
    inputs: TriggerInputs,
) -> list[tuple[str, FifEvent]]:
    """(user_id, event) pairs — one event per (kind, watched ticker, event_ref)
    derived STRICTLY inside each user's own subscription partition (no-leak,
    gate 3). The company universe comes from the private state; a watched
    symbol with no company row is simply outside the FIF universe (no event,
    never an error)."""
    state_doc = inputs.state_doc if isinstance(inputs.state_doc, dict) else None
    companies = (state_doc or {}).get("companies")
    companies = companies if isinstance(companies, dict) else {}
    generated_at = (state_doc or {}).get("generated_at")
    receipt_detail = _receipt_detail(inputs.receipt)
    receipt_clock = (
        inputs.receipt.get("poll_completed_at")
        if isinstance(inputs.receipt, dict)
        else None
    )
    generations = _pointer_generations(inputs.pointer)

    pairs: list[tuple[str, FifEvent]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def _emit(user_id: str, key: tuple[str, str, str, str], event: FifEvent) -> None:
        if key in seen:
            return
        seen.add(key)
        pairs.append((user_id, event))

    for user_id in sorted(subscriptions):
        for ticker in sorted(subscriptions[user_id]):
            company = companies.get(ticker)
            if not isinstance(company, dict):
                continue
            cik = cik10(company.get("cik"))
            if cik is None:
                continue
            # high_finding — relay the engine's plain title only (A7).
            for finding in company.get("findings") or []:
                if not isinstance(finding, dict):
                    continue
                if str(finding.get("priority") or "") != "high":
                    continue
                ref = str(finding.get("id") or "").strip()
                if not ref:
                    continue
                filed = _finding_filed_date(finding)
                _emit(
                    user_id,
                    (KIND_HIGH_FINDING, cik, ref, user_id),
                    FifEvent(
                        kind=KIND_HIGH_FINDING,
                        cik=cik,
                        ticker=ticker,
                        event_ref=ref,
                        condition_plain=_plain(
                            finding.get("title_en"),
                            "A new review item needs attention for this company",
                        ),
                        subject=f"A new review item needs attention on {ticker}",
                        fired_at=generated_at,
                        event_date=filed.isoformat() if filed else None,
                    ),
                )
            # new_filing — only from the receipt mirror's per-CIK detail map.
            for accession in receipt_detail.get(cik) or []:
                ref = str(accession).strip()
                if not ref:
                    continue
                _emit(
                    user_id,
                    (KIND_NEW_FILING, cik, ref, user_id),
                    FifEvent(
                        kind=KIND_NEW_FILING,
                        cik=cik,
                        ticker=ticker,
                        event_ref=ref,
                        condition_plain="A new filing was admitted for this company",
                        subject=f"A new filing was admitted for {ticker}",
                        fired_at=receipt_clock,
                    ),
                )
            # generation — a missing pointer is "no event" (R5), never an error.
            entry = generations.get(cik)
            if isinstance(entry, dict):
                ref = str(entry.get("generation_id") or "").strip()
                if ref:
                    _emit(
                        user_id,
                        (KIND_GENERATION, cik, ref, user_id),
                        FifEvent(
                            kind=KIND_GENERATION,
                            cik=cik,
                            ticker=ticker,
                            event_ref=ref,
                            condition_plain="A newer filing dataset now covers this company",
                            subject=f"A newer filing dataset now covers {ticker}",
                            fired_at=str(entry.get("admitted_at") or "") or None,
                        ),
                    )
    return pairs


def compose_payload(event: FifEvent, *, evidence_base: str = EVIDENCE_BASE) -> dict:
    """The compose_alert contract fields (app/mailer.py:1379-1430) plus the
    category the drain filters on (engine/alert_delivery_drain.py:495-507),
    and event_date (R3f) — the date the payload records for the event (None
    for kinds without one). Both consumers read named keys only and ignore
    extras (drain: payload.get("category")/:514 requires_tier and the
    isinstance dict pass-through :767-768,:820; mailer compose_alert reads
    ticker/condition_plain/evidence_url/fired_at/subject by name and never
    rejects unknown keys), so the extra field is harmless. Nothing else —
    no values, no scores, no slugs."""
    return {
        "ticker": event.ticker,
        "condition_plain": event.condition_plain,
        "evidence_url": evidence_url(event.ticker, evidence_base),
        "subject": event.subject,
        "fired_at": event.fired_at,
        "category": CATEGORY,
        "event_date": event.event_date,
    }


def build_subscriptions(list_rows: list, symbol_rows: list) -> dict[str, set[str]]:
    """The per-user partition: {user_id: {symbols on THAT user's designated
    list}}. Only the designated list's own rows enter; a symbol row whose
    watchlist_id matches no designated list is ignored."""
    list_by_id = {
        str(row.get("id")): str(row.get("user_id"))
        for row in list_rows
        if isinstance(row, dict) and row.get("id") and row.get("user_id")
    }
    subscriptions: dict[str, set[str]] = {}
    for row in symbol_rows or []:
        if not isinstance(row, dict):
            continue
        user_id = list_by_id.get(str(row.get("watchlist_id")))
        symbol = str(row.get("symbol") or "").strip().upper()
        if not user_id or not symbol:
            continue
        subscriptions.setdefault(user_id, set()).add(symbol)
    return subscriptions


def plan_enqueue(
    *,
    subscriptions: dict[str, set[str]],
    inputs: TriggerInputs,
    existing_fire_ids: set[str],
    evidence_base: str = EVIDENCE_BASE,
) -> ProducerPlan:
    """One row per (user, event); ids already present in alert_outbox (or
    already minted this run) are counted as duplicates and skipped. A high
    finding outside the R3 recency window is suppressed BEFORE its id is
    minted — a suppressed candidate never enters the probe either, so it
    consumes no dedupe lookup and never becomes a row."""
    pairs = derive_events(subscriptions=subscriptions, inputs=inputs)
    rows: list[dict] = []
    duplicate_n = 0
    suppressed: dict[str, int] = {key: 0 for key in SUPPRESSION_KEYS}
    seen: set[str] = set()
    state_doc = inputs.state_doc if isinstance(inputs.state_doc, dict) else None
    as_of = _parse_leading_date((state_doc or {}).get("as_of"))
    for user_id, event in pairs:
        if event.kind == KIND_HIGH_FINDING:
            gate = _high_finding_gate(event, as_of)
            if gate is not None:
                suppressed[gate] += 1
                continue
        fid = fire_event_id(
            kind=event.kind, cik=event.cik, event_ref=event.event_ref, user_id=user_id
        )
        if fid in existing_fire_ids or fid in seen:
            duplicate_n += 1
            continue
        seen.add(fid)
        rows.append({
            "user_id": user_id,
            "alert_id": synthetic_alert_id(user_id),
            "fire_event_id": fid,
            "channel": CHANNEL,
            "status": "pending",
            "attempts": 0,
            "payload": compose_payload(event, evidence_base=evidence_base),
        })
    return ProducerPlan(
        rows=rows,
        users_n=len(subscriptions),
        symbols_n=sum(len(s) for s in subscriptions.values()),
        events_n=len(pairs),
        duplicate_n=duplicate_n,
        suppressed=suppressed,
    )


# ---------------------------------------------------------------------------
# IO functions — isolated, monkeypatched in tests. urllib is imported LAZILY
# so importing this module never loads an HTTP client (P1).
# ---------------------------------------------------------------------------

def _pg(method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6):
    import urllib.request  # noqa: PLC0415 — lazy by design (P1)

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
    import urllib.error  # noqa: PLC0415 — lazy by design (P1)

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
        except Exception:  # noqa: BLE001
            pass
        if code == 404 or "42P01" in body or "PGRST205" in body:
            return TypedRead(READ_UNAVAILABLE, None, "table_absent")
        return TypedRead(READ_UNAVAILABLE, None, f"http_{code}")
    except Exception:  # noqa: BLE001
        return TypedRead(READ_UNAVAILABLE, None, "unknown")


def read_designated_lists() -> TypedRead:
    """Every user's designated list, service-side (RLS owner policies do not
    bind the service role; the no-leak partition is enforced by THIS module,
    never by the read)."""
    import urllib.parse  # noqa: PLC0415 — lazy by design (P1)

    path = (
        "watchlists?name=eq."
        + urllib.parse.quote(DESIGNATED_LIST_NAME, safe="")
        + "&select=id,user_id,name"
    )
    return typed_get(path)


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def read_list_symbols(list_ids: list[str]) -> TypedRead:
    if not list_ids:
        return TypedRead(READ_OK_ZERO, [])
    import urllib.parse  # noqa: PLC0415 — lazy by design (P1)

    all_rows: list[dict] = []
    for chunk in _chunks([str(i) for i in list_ids], 100):
        in_list = ",".join(urllib.parse.quote(c, safe="") for c in chunk)
        path = (
            f"watchlist_symbols?watchlist_id=in.({in_list})"
            "&select=watchlist_id,symbol"
        )
        result = typed_get(path)
        if result.state == READ_UNAVAILABLE:
            return result
        all_rows.extend(result.rows or [])
    return TypedRead(READ_OK if all_rows else READ_OK_ZERO, all_rows)


def read_existing_fire_ids(ids: list[str]) -> TypedRead:
    if not ids:
        return TypedRead(READ_OK_ZERO, [])
    import urllib.parse  # noqa: PLC0415 — lazy by design (P1)

    all_rows: list[dict] = []
    for chunk in _chunks([str(i) for i in ids], 100):
        in_list = ",".join(urllib.parse.quote(c, safe="") for c in chunk)
        path = f"alert_outbox?fire_event_id=in.({in_list})&select=fire_event_id"
        result = typed_get(path)
        if result.state == READ_UNAVAILABLE:
            return result
        all_rows.extend(result.rows or [])
    return TypedRead(READ_OK if all_rows else READ_OK_ZERO, all_rows)


def enqueue(rows: list[dict], *, dry_run: bool) -> tuple[int, int, str | None]:
    """Insert-or-ignore on fire_event_id: a 409/23505 replay is a no-op
    (UNIQUE backstop), never an error."""
    import urllib.error  # noqa: PLC0415 — lazy by design (P1)

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
            except Exception:  # noqa: BLE001
                pass
            if code == 409 or "23505" in body:
                duplicates += 1
                continue
            if code == 400 or "23502" in body:
                return (enqueued, duplicates, "schema_mismatch")
            return (enqueued, duplicates, f"http_{code}")
    return (enqueued, duplicates, None)


def _read_json(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def load_trigger_inputs(root: str | Path) -> TriggerInputs:
    """Local-only trigger reads — NEVER R2 (census C6). Each artifact is
    independently absent-or-loaded; absence is a typed state, not an error."""
    from engine.fundamental_forensics import private_state  # noqa: PLC0415 — lazy

    root_path = Path(root)
    state_doc: dict | None = None
    state_state = READ_UNAVAILABLE
    try:
        blob = private_state.local_state_path(root_path).read_bytes()
        state_doc = private_state.decode_state_blob(blob)
        state_state = READ_OK
    except Exception:  # noqa: BLE001
        state_doc = None
        state_state = READ_UNAVAILABLE
    receipt = _read_json(root_path / BROAD_SEC_RECEIPT_RELATIVE)
    pointer = _read_json(root_path / PRODUCTION_POINTER_RELATIVE)
    return TriggerInputs(
        state_doc=state_doc,
        receipt=receipt,
        pointer=pointer,
        state_state=state_state,
        receipt_state=READ_OK if receipt is not None else READ_UNAVAILABLE,
        pointer_state=READ_OK if pointer is not None else READ_UNAVAILABLE,
    )


def run(
    *,
    root: str | Path = ".",
    dry_run: bool = True,
    evidence_base: str = EVIDENCE_BASE,
) -> ProducerResult:
    lists_read = read_designated_lists()
    if lists_read.state == READ_UNAVAILABLE:
        return ProducerResult(
            outcome="unavailable", read_state=lists_read.state,
            error_class=lists_read.error_class, users_n=0, symbols_n=0,
            events_n=0, enqueued_n=0, duplicate_n=0, planned_n=0,
            state_state=READ_UNAVAILABLE, receipt_state=READ_UNAVAILABLE,
            pointer_state=READ_UNAVAILABLE,
        )
    list_ids = [str(row.get("id")) for row in lists_read.rows or [] if row.get("id")]
    symbols_read = read_list_symbols(list_ids)
    if symbols_read.state == READ_UNAVAILABLE:
        return ProducerResult(
            outcome="unavailable", read_state=symbols_read.state,
            error_class=symbols_read.error_class, users_n=0, symbols_n=0,
            events_n=0, enqueued_n=0, duplicate_n=0, planned_n=0,
            state_state=READ_UNAVAILABLE, receipt_state=READ_UNAVAILABLE,
            pointer_state=READ_UNAVAILABLE,
        )
    subscriptions = build_subscriptions(lists_read.rows or [], symbols_read.rows or [])
    inputs = load_trigger_inputs(root)
    # Pre-insert SELECT of the ids this run WOULD mint (dedupe belt), then the
    # real plan against whatever it found. An unreadable probe degrades to the
    # UNIQUE-index backstop alone — noted, never fatal.
    probe = plan_enqueue(
        subscriptions=subscriptions, inputs=inputs,
        existing_fire_ids=set(), evidence_base=evidence_base,
    )
    existing_read = read_existing_fire_ids([r["fire_event_id"] for r in probe.rows])
    existing_ids = (
        {str(r.get("fire_event_id")) for r in existing_read.rows or []}
        if existing_read.state != READ_UNAVAILABLE
        else set()
    )
    notes: list[str] = []
    if existing_read.state == READ_UNAVAILABLE:
        notes.append(
            f"existing_fire_ids unreadable ({existing_read.error_class}) — "
            "enqueue relies on UNIQUE alone"
        )
    plan = plan_enqueue(
        subscriptions=subscriptions, inputs=inputs,
        existing_fire_ids=existing_ids, evidence_base=evidence_base,
    )
    enqueued_n, duplicate_n, error_class = enqueue(plan.rows, dry_run=dry_run)
    return ProducerResult(
        outcome="ok" if error_class is None else "partial",
        read_state=READ_OK,
        error_class=error_class,
        users_n=plan.users_n,
        symbols_n=plan.symbols_n,
        events_n=plan.events_n,
        enqueued_n=enqueued_n,
        duplicate_n=plan.duplicate_n + duplicate_n,
        planned_n=len(plan.rows),
        state_state=inputs.state_state,
        receipt_state=inputs.receipt_state,
        pointer_state=inputs.pointer_state,
        notes=notes,
        suppressed=plan.suppressed,
    )
