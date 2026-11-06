# B21 — Prophet US research-journey alert state-machine contract (2026-10-21)

ROUTE: research (design document; no code). Parent: BUILD_PROGRAM units[21]
(`research/prophet_v4/r6_fable_meta_ceo_handoff/effective/BUILD_PROGRAM.json`):
"Integrate meaningful alerts and durable user actions", depends_on B07/B20, release_limit
"No new retry/watch/queue/store system or click-feedback trading model." Work card:
`research/prophet_v4/r6_fable_meta_ceo_handoff/work_cards/B21.md`. Every design statement
below names the existing owner it extends; nothing here mints a store, queue, retry system
or watcher.

Premise check (packet rule: a contradicted premise is reported, not worked around): all
byte quotes were re-read at BASE `e5dd30c6344e` and agree with the packet, with two
refinements reported in place — (a) the packet's example `fire_event_id` literal cannot be
colon-joined as written, because the B1 `episode_id` is itself a 7-part colon literal
(`engine/us_candidate_episode.py:315-332`); (b) `<generation>` and `<definition_version>`
must not be identity segments at all (§2). Both are design-level corrections with quoted
incumbent rulings, not fact contradictions.

## 0. Incumbent lane inventory (the only carriers B21 may use)

- Preferences: `lib/user_prefs.py:1` — "the ONE reader/writer for a signed-in user's
  stored preferences" over Supabase Auth `user_metadata`. Closed
  `ALERT_CATEGORIES = ("holdings_material_change", "thesis_window", "fif_saved_issuer")`
  (`lib/user_prefs.py:68-72`); kind table adds `alert_email_optin` (bool),
  `alert_categories` (set), `tz`, `quiet_hours` (`lib/user_prefs.py:75-81`). Write surface
  `app/account_prefs.py:96-104` (PrefsRequest fields), route `app/account_prefs.py:131`
  (`POST /api/account/prefs`), loop at `:147-154`. Unsubscribe `app/unsubscribe.py:186-213`
  (suppression upsert `:186-193`, liftable-suppression lift `:196-208`, marketing opt-out
  `:211-215`); a resubscribe "deliberately refuses to lift a suppression whose reason is
  ``bounce`` or ``complaint``" (`app/unsubscribe.py:32-37`).
- Producers → `public.alert_outbox`: `engine/thesis_condition_monitor.py` (row shape per
  terminal migration 0013, `:46-51`; synthetic uuid5 `alert_id` `:323-328`; latched FIRED
  windows `:239-250`; dedupe = deterministic id + pre-insert SELECT + UNIQUE index
  `:74-77`; sha256-hash id `:301-320`) and `engine/fif_saved_research_notifications.py`
  (subscription = membership of the Supabase watchlist stored under the verbatim name
  "Filing Forensics", `:6-13`, `:71`; frozen literal id `fif:{kind}:{cik}:{event_ref}:{user_id}`
  `:24-29`, `:226-229`; pre-insert dedupe `:478-526`; payload = compose_alert fields +
  category `:436-454`). `holdings_material_change` has no producer — D05 open item D05-b
  (`research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-D05-01_2026-09-23.md:15`, `:24`).
- Drain: `engine/alert_delivery_drain.py`. Eligibility `decide_row` `:484-531` (opt-in
  `:493-494`, category closed-set `:500-501`, category filter `:507-508`, suppression
  `:509-512`, entitlement `:513-520`, quiet hours defer `:525-530`). Retry with fresh key
  `:23-29`, cap `ALERT_RETRY_ATTEMPTS_CAP = 3` `:71-74`, selection predicate `:711-718`.
  Effect-unknown rows are QUARANTINED — never resent, never marked delivered `:31-36`,
  `:88-100`, `:904-916`, write at `:594-623`. "Exactly-once is NOT available and is not
  claimed … at-most-once-per-logical-alert" `:38-43`. Dormant behind
  `ALERT_DRAIN_ENABLE=1` (`scripts/drain_alert_outbox.py:11`, `:51-54`), timer every 5
  minutes (`engine/alert_delivery_drain.py:4`).
- Dedupe ledger: `email_log` UNIQUE `idem_key = alert_fire:<fire_event_id>[:attempt]`
  (`app/mailer.py:1340-1353`; drain copy `engine/alert_delivery_drain.py:134-140`);
  `alert_outbox` UNIQUE(fire_event_id) (thesis monitor `:75-77`). No correction or
  revocation exists for delivered alerts anywhere in the estate (searches in §10).
- Prophet emits no user alert today: `engine/prophet_early_observations.py:30-31` —
  `AUTHORITY = {"buy": False, "alert": False, "entry_open": False, "rank": False,
  "size": False, "episode_write": False}`. B3 = `engine/prophet_candidate_state.py`,
  B4 = `engine/prophet_entry_availability.py`.

## 1. Eligible change (Q1)

Enums, quoted:

- B1 event vocabulary — `engine/us_candidate_episode.py:35-44`:
  `EVENT_TYPES = {"OPENED", "OBSERVED", "EXPERT_EVENT_ATTACHED", "STATE_TRANSITIONED",
  "REARM_SUPPRESSED", "CORRECTED", "RETRACTED", "IDENTITY_SUPERSEDED"}`; terminal/source
  states `:45-47`: `TERMINAL_STATES = {"RESOLVED", "INVALIDATED", "EXPIRED", "RETRACTED"}`,
  `EPISODE_STATES = {ACTIVE} ∪ TERMINAL_STATES`. Correction patch surface `:51-61`
  `PATCHABLE_FIELDS = {company_id, ticker_at_observation, identity_epoch_state,
  identity_spec_schema, identity_spec_hash, opened_at, opened_session, intake_classes,
  terminal_reason}`.
- B3 projection — `engine/prophet_candidate_state.py:39-41` `_SOURCE_EPISODE_STATES =
  {"ACTIVE", "RESOLVED", "INVALIDATED", "EXPIRED", "RETRACTED"}`; `:42-51`
  `_LIFECYCLE_STATES = {"ACTIVE", "CLOSED", "INVALIDATED", "RETRACTED", "SUPERSEDED",
  "UNAVAILABLE_DATA"}`; `:52-54` `_EMERGENCE_STATES = {"FORMING", "ARMED", "TRIGGERED",
  "FAILED_TO_TRIGGER", "DECAYED", "UNESTIMABLE"}`; `:55-64` `_MATURITY_STATES =
  {"PRE_CONFIRMATION", "EARLY_CONFIRMATION", "CONFIRMED", "MATURE", "EXHAUSTION_RISK",
  "UNESTIMABLE"}`. B3 pins `entry_availability` to `{"state": "UNAVAILABLE_DATA",
  "reason": "B4_NOT_AVAILABLE"}` on every row `:347-350` and rejects anything else
  `:551-557`.
- B4 — `engine/prophet_entry_availability.py:35-45` `AVAILABILITY_STATES = {"NOT_READY",
  "APPROACHING_ENTRY", "ENTRY_OPEN", "WAIT_PULLBACK", "RAN_DONT_CHASE", "INVALIDATED",
  "UNAVAILABLE_DATA"}`; freshness axis `:65` `_FRESHNESS = {"FRESH", "STALE", "UNKNOWN"}`.

**Eligible kinds (v1 closed set):**

| kind | transition / cause | evidence |
|---|---|---|
| `episode_terminal` | lifecycle ACTIVE → any of {RESOLVED, INVALIDATED, EXPIRED, RETRACTED} (B3: ACTIVE → INVALIDATED / RETRACTED / CLOSED) | B1 STATE_TRANSITIONED is one-way and terminal-only: "terminal episode cannot reactivate in the same generation" / "state transition must leave ACTIVE for a terminal state" (`engine/us_candidate_episode.py:574-577`) |
| `emergence_triggered` | emergence none → TRIGGERED for a generation-local TURN WATCH relation | native read derives TRIGGERED only from a real relation id, else "UNESTIMABLE/SOURCE_NOT_SUPPLIED" (`engine/prophet_candidate_state.py:1224-1232`, coherence pinned `:1646-1668`) |
| `corrected_material` | B1 CORRECTED whose patch touches a field the user was shown: `terminal_reason` or `ticker_at_observation` | CORRECTED patches only `PATCHABLE_FIELDS` and stamps `correction_state: "corrected"` (`engine/us_candidate_episode.py:582-596`) |
| `retracted` | B1 RETRACTED of the OPENED relation (episode leaves the projection) or of a shown relation | RETRACTED targets OPENED/OBSERVED/EXPERT_EVENT_ATTACHED `:597-605`; an OPENED target removes the row `:626-629` |
| `superseded` | B1 IDENTITY_SUPERSEDED (B3 lifecycle SUPERSEDED whenever `superseded_by` is set) | `:606-616`; B3 forces SUPERSEDED over any source state when a successor exists (`engine/prophet_candidate_state.py:144-155`) |

`episode_opened` (a new ACTIVE episode on a watched name) is eligible **in principle** —
it is the journey start — but is v1-optional: it must ship recency-gated exactly like the
fif high-finding window (`engine/fif_saved_research_notifications.py:94`, `:285-299`) or
be left out of the first mint; dropping or adding it changes no other clause of this
contract.

**Never eligible:**

- A quote/price refresh. B4's own outputs are functions of the live quote:
  `current_price`, `quote_asof`, `quote_age_seconds`, all `*_pct` metrics
  (`engine/prophet_entry_availability.py:284-321`, `:471-478`), and `availability_id`
  hashes the whole material including `evaluated_at` `:484-487` — every refresh mints a
  new availability_id, so a B4-transition alert is by construction a quote-refresh alert.
- A freshness change: `FRESH/STALE/UNKNOWN` is a data-quality axis, not a journey axis;
  the B4 law is "Missing, stale, ambiguous or unknown required facts fail closed"
  (`engine/prophet_entry_availability.py:9-11`). STALE never becomes content.
- A re-read of the same generation (no new B1 event ⇒ no eligible change; §2 makes the
  id prove it), and a repeated unchanged event (same bytes ⇒ same content-addressed
  event_id, `engine/us_candidate_episode.py:309`).
- Any transition with `UNESTIMABLE` or `UNAVAILABLE_DATA` on either side: absence of
  knowledge is not a journey change. Maturity is pinned UNESTIMABLE by the native read
  (`engine/prophet_candidate_state.py:1433-1443` expects `"maturity_state":
  "UNESTIMABLE"`), so no maturity transition is producible today and none is eligible.
  Exception (ratified deviation, seat ruling F28 R8): for the `emergence_triggered` diff a
  prior emergence state that is absent or `UNESTIMABLE` (B3's `SOURCE_NOT_SUPPLIED`
  default) counts as not triggered, so a later `TRIGGERED` carrying a real relation id is
  eligible.
- B1 `REARM_SUPPRESSED` (replay no-op, `engine/us_candidate_episode.py:617-618`) and
  `OBSERVED`/`EXPERT_EVENT_ATTACHED` (engine-internal relations, no user-facing state
  change of record).

**Can B4 transitions be eligible today? No — confirmed.** B4 is evaluated on demand from
caller-supplied facts; `evaluate_entry_availability` has no caller outside tests and
`engine/prophet_entry_availability_sources.py` (search: `grep -rn
"evaluate_entry_availability|from engine.prophet_entry_availability" --include="*.py"`,
hits only `tests/test_ptse_new_entry_context.py:12,116`,
`tests/test_prophet_strategy_definition.py:120-122,220`,
`tests/test_prophet_daily_brief.py:9`, `engine/prophet_entry_availability_sources.py:33`).
Nothing persists a B4 series — `"pea:"` ids are minted in exactly one place
(`engine/prophet_entry_availability.py:485`, checked `:527`) with no writer anywhere in
`scripts/` or `engine/` — and B3 itself pins availability to UNAVAILABLE_DATA
(`:347-350`). A same-read caller would be a new store, which the B21 release limit
forbids. Therefore B4 availability transitions are **out of scope for B21**, not
blocked-pending; an alert on ENTRY_OPEN would additionally be a price alert in disguise.

## 2. Identity (Q2)

**Proposed literal (fif pattern: literal concatenation, no hashing —
`engine/fif_saved_research_notifications.py:226-229`):**

```
prophet|<kind>|<episode_id>|<from>-><to>|<b1_event_id>|<user_id>
```

- `<kind>`: one of the §1 closed set (`episode_terminal`, `emergence_triggered`,
  `corrected_material`, `retracted`, `superseded`, optional `episode_opened`).
- `<episode_id>`: the B1 episode id verbatim (`pe:SEC:…:sa:…:<n>`,
  `engine/us_candidate_episode.py:315-332`). Note its trailing integer is the identity
  anchor generation, fixed at episode creation — it is not the nightly
  `candidate_generation_id` and does not churn per read.
- `<from>-><to>`: B3 lifecycle pair for lifecycle kinds (`ACTIVE->INVALIDATED` etc.),
  `NONE->TRIGGERED` for `emergence_triggered`, `NONE-><kind>` for correction kinds.
  Enum tokens only; no colons.
- `<b1_event_id>`: the content-addressed id of the causing event (`pee:<64-hex>`,
  `engine/us_candidate_episode.py:309`): the STATE_TRANSITIONED / CORRECTED / RETRACTED /
  IDENTITY_SUPERSEDED event id, or the selected TURN WATCH `relation_event_id` for
  `emergence_triggered` (`engine/prophet_candidate_state.py:1231`, `:1268-1269`).
- `<user_id>`: the Supabase user uuid (fif terminal segment, `:229`).

**Delimiter deviation, reported:** the packet's example used `:` between segments, but
`<episode_id>` is itself a 7-part colon literal, so a colon join is unparseable. The
major separator is `|` — the same join character the thesis monitor uses internally
before hashing (`engine/thesis_condition_monitor.py:318`). The build lane pins the
format with a round-trip parse test.

**Two segments of the packet's example are deliberately excluded, with incumbent
rulings:**

- `<generation>` — excluded. The producer is a stateless nightly re-derivation over the
  cumulative append-only B1 ledger (full replay each run,
  `engine/us_candidate_episode.py:540-670`); the B1 event envelope's closed field set
  (`:347-351`) carries no generation stamp, and the same logical transition read in a
  later cumulative generation would mint `…|G2|…` ≠ `…|G1|…` — two outbox rows for one
  journey change. Keying on the causing event's own content-addressed id is the only
  stateless collapse. `candidate_generation_id` and `market_session` ride the payload as
  provenance/display only.
- `<definition_version>` — excluded by direct ruling: the thesis monitor's id "keys
  `fire_event_id` off the tripwire's own identity ONLY … `thesis_version`/`current_version`
  is carried on the payload for DISPLAY only and is never hashed. … A thesis amendment
  (which bumps `current_version`) must not mint a new id for an already-notified …
  transition" (`engine/thesis_condition_monitor.py:30-36`, `:311-316`). A B21 definition
  change re-notifying every subscriber is the same defect. B3's `DEFINITION_ERA`
  (`engine/prophet_candidate_state.py:32`) rides the payload.

**Collapse proof (one outbox row per logical event per user):**

| scenario | mechanism | bytes |
|---|---|---|
| repeated unchanged event, nightly re-run | identical literal → pre-insert SELECT skips + UNIQUE(fire_event_id) backstop | fif `plan_enqueue` skips `fid in existing_fire_ids or fid in seen` (`engine/fif_saved_research_notifications.py:503-509`); thesis dedupe guards `engine/thesis_condition_monitor.py:74-77` |
| retry (drain) | a retry never inserts an outbox row: the drain reuses the SAME row and only the email_log idem key gains `:attempt` | `app/mailer.py:1340-1353`, drain copy `engine/alert_delivery_drain.py:134-140`; producers are the only inserters (`enqueue`, fif `:631`) |
| re-read of the same generation (or a later cumulative generation containing the same event) | the causing event's id is content-addressed and immutable → same literal → duplicate skip | `engine/us_candidate_episode.py:309` (`"pee:" + sha256(…)`), `:343-351` (closed envelope re-checked on every read) |

Synthetic `alert_id`: one uuid5 per user's Prophet watch on the fif pattern
(`engine/fif_saved_research_notifications.py:114-119`, `:232-238`) — a frozen namespace
constant plus the conceptual `prophet_watch:<user_id>` identity; never a foreign key into
any Alerts-table row (none exists; thesis ruling `engine/thesis_condition_monitor.py:52-56`).

## 3. Subscription (Q3)

**(a) — chosen.** One new `ALERT_CATEGORIES` member plus membership of a designated
named Supabase watchlist, exactly the fif pattern. What (a) needs:

1. `lib/user_prefs.py:68-72` — append exactly one member (proposed literal:
   `prophet_research_journey`) with one comment line naming B21. The drain needs no
   change: `decide_row` checks `category not in user_prefs.ALERT_CATEGORIES`
   (`engine/alert_delivery_drain.py:500-501`), so an enum append is drain-recognized
   unedited. The route needs no change: `PrefsRequest.alert_categories` is a
   `list[str]` "subset of user_prefs.ALERT_CATEGORIES" (`app/account_prefs.py:97-98`)
   checked through the lib's set normalizer (`lib/user_prefs.py:163-174`).
2. Enum acceptance gate in `tests/test_alert_prefs.py` (5 category tests at BASE; the
   open cs-v2 lane adds its own there — custody below).
3. Designated list constant in the new producer module:
   `DESIGNATED_LIST_NAME = "Prophet Research"` on the fif precedent — one verbatim
   stored name, because "The watchlists schema carries NO kind/system/metadata column
   (Terminal 0001_init.sql:29-36, census C2), so the list is identified by its verbatim
   stored name. Absence of the list, or of a symbol on it, IS 'no subscription'"
   (`engine/fif_saved_research_notifications.py:9-13`, `:71`). Service-side read shape:
   `watchlists?name=eq.<name>&select=id,user_id,name` then per-list symbols (`:584-586`,
   `:596-606`); per-user partition before any event is derived (no-leak,
   `build_subscriptions` `:457-475`).
4. User-facing opt-in surface is a **separate, deferrable** unit: `templates/account.js:655-656`
   hardcodes exactly two category rows (`holdings_material_change`, `thesis_window`) and
   already does not list `fif_saved_issuer` — the incumbent precedent is enum-member +
   producer with no account-UI row (API-selectable), consistent with the D05 honest-
   absence ruling ("no user-facing promise until one lands",
   `research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-D05-01_2026-09-23.md:15`).

**Custody (read at BASE, plus the one open-lane object available on this host):**
`lib/user_prefs.py` history at BASE is merged work (B-F08-1a `#6907`, FIF X2-n `#9069`).
An **open lane edits the same tuple**: head `9807f9067f80` on
`origin/claude/cs-v2-v0b-lane` (on host, NOT an ancestor of BASE) adds exactly one
member plus one comment line — bytes at that head:

```
ALERT_CATEGORIES: tuple[str, ...] = (
    "holdings_material_change",
    "thesis_window",
    "fif_saved_issuer",
    "cs_saved_scenario",
)
```

with `tests/test_alert_prefs.py` +29 lines (`git diff --stat e5dd30c6344e 9807f9067f80 --
lib/user_prefs.py tests/test_alert_prefs.py`). Consequence: the B21 append lands as an
adjacent line in one tuple — merge-order coordination is required and both lanes' enum
gates must accept the union. **Gap:** whether that lane has an open PR (number, labels,
review state) is not readable from this offline lane (no `gh`/network); the rule-bound
alternative (head-commit read via `git show`) is what the bytes above are.

**(b) — forbidden, and why.** Any new subscription surface (a `prophet_subscriptions`
table, a per-user state file, a preference outside `user_metadata`) violates the B21
release limit "No new retry/watch/queue/store system" and duplicates two live owners
(Supabase `user_metadata` prefs; `watchlists`/`watchlist_symbols` via WatchStore). It
would also collide with the F11 do-not-redo bar on "a second local
canonical-fact/idempotency store" (`engine/thesis_condition_monitor.py:77-79`).
D05 additionally rules that watchlists/portfolio scopes already "have a real cloud
owner" and only Pass/thesis/milestone actions lack one
(`SEAT_RULING_R6-D05-01_2026-09-23.md:11`) — a Prophet-specific second watch store would
contradict that finding. D09 context: Watch is the only live user action and flows
through `templates/watchstore.js` (Supabase relational sync, owner-scoped multi-list,
`watchlist_symbols`; header docstring `:1-38`); B21 subscribes off that same store and
adds no action.

## 4. Correction and revocation (Q4)

A correction is a **NEW `alert_outbox` row** referencing the original fire id; a
delivered row is never edited (`email_log`'s UNIQUE idem ledger and the outbox's own
UNIQUE(fire_event_id) make post-hoc edits both racy and unprovable — and the drain's
at-most-once law forbids treating a sent row as unsent,
`engine/alert_delivery_drain.py:38-43`).

- New-row kinds: `corrected_material`, `retracted`, `superseded` (§1). Their own
  `fire_event_id` is the §2 literal keyed on the **causing** CORRECTED/RETRACTED/
  IDENTITY_SUPERSEDED event id, so a repeated correction event cannot double-send.
- The reference to the original rides the payload as `corrects_fire_event_id` — a
  machine field both incumbent consumers ignore (the drain reads only
  `payload["category"]`/`payload["requires_tier"]`, `engine/alert_delivery_drain.py:495-515`;
  `compose_alert` reads display keys by name, `app/mailer.py:1379-1430`). Its VALUE must
  never enter glance-tier text: `"fire_event_id"` is a banned token at render
  (`app/mailer.py:1334-1337`) and the producer-side persist guard bans machine tokens
  (`engine/fif_saved_research_notifications.py:109-112`).
- **Original-status readback.** The producer extends its existing dedupe read
  (`read_existing_fire_ids`, fif `:615-623`) to `select=fire_event_id,status,attempts,last_error`
  and branches on the ORIGINAL row's delivery state before minting:

| original state (read from `alert_outbox`) | behaviour |
|---|---|
| unsent: `pending`, `deferred`, or `failed` with `attempts < 3` | PATCH the original to `status='suppressed'`, `last_error='superseded_by_prophet_correction'` (a status and free-text error the table already admits — the drain itself writes `'suppressed'` + reason at `engine/alert_delivery_drain.py:808-810`), then insert the correction row. Exactly one email is ever sent. A producer PATCH against its own row has an incumbent analogue: terminal's "guarded one-shot disarm" PATCH (`engine/thesis_condition_monitor.py:70-72`, citing the F08 freeze). The PATCH is scoped to fire ids this producer minted. |
| sent: `status='sent'` | never touch the original; insert the correction row only. The original's `delivered_at` is the drain's resolution time and stays immutable (`engine/alert_delivery_drain.py:845-870`). |
| quarantined (effect-unknown): `status='failed'` AND `attempts >= 3` AND `last_error='effect_unknown_after_smtp'` (`engine/alert_delivery_drain.py:107`, write `:611-615`) | **no correction row.** The original "may be in the reader's inbox" and the drain's law is "never resend, never claim delivered" (`:904-916`); minting a correction that presumes receipt converts an unknown into an assertion. The correction is counted with a typed producer suppression key (`correction_original_effect_unknown`, fif R3d pattern `engine/fif_saved_research_notifications.py:99-104`) and surfaces in the run receipt; the corrected fact is corrected in the product surface; the quarantined original stays with its `::warning` operator path (`:616-621`). A self-contained "as of <date> we no longer track X" notice that presumes nothing is a copy/product ruling for Sol, recorded here as open — not silently chosen. |
| suppressed (user opt-out / category / address) | mint the correction row anyway and let the drain re-decide from live prefs — the producer holds no user state (`engine/fif_saved_research_notifications.py:31-34` no-leak partition; `decide_row` `:493-512`). |

- **Retraction behaviour.** `retracted` (B1 RETRACTED of the OPENED relation — the
  episode is removed from the projection, `engine/us_candidate_episode.py:626-629` — or
  of a shown relation): plain-language notice that the name is no longer tracked, plus
  `evidence_url`; minted only when the original was sent, else the original is
  PATCH-suppressed per the table above. `superseded` (B1 IDENTITY_SUPERSEDED → B3
  SUPERSEDED, `engine/prophet_candidate_state.py:144-155`): notice that the opportunity
  continues under a successor identity; the successor's raw episode id is a machine
  string and must not appear in glance text (fif payload law: "No values, no scores, no
  slugs", `engine/fif_saved_research_notifications.py:37-39`) — the ticker and the
  surface link carry it. `from->to` for both uses the B3 lifecycle pair, because B3 —
  not B1 — is the state the user was shown.

## 5. Stale mandatory fact guard (Q5)

The mandatory fact of a B21 row is the B1 event it relays; a row can sit in the outbox
for hours (quiet-hours defer `engine/alert_delivery_drain.py:525-530`; deferred rows are
re-selected only when due, `:716`). Two guards, both typed, neither sending an older
value:

1. **At mint (producer, fail closed):** the B1 snapshot is re-checked against its own
   generation bytes before any id is minted (the native owner read already re-checks
   disk content against the snapshot; `engine/prophet_candidate_state.py:1098-1105`).
   A missing/stale/unknown input is "no event", never an error — the fif input law
   (`engine/fif_saved_research_notifications.py:19-20`) — and unknown-at-derivation is
   suppressed with a typed count before minting (fif R3 gate shape `:285-299`). This
   mirrors B4's own law: "Missing, stale, ambiguous or unknown required facts fail
   closed" (`engine/prophet_entry_availability.py:9-11`).
2. **At drain (the named extension):** the payload carries `not_after` — one RFC3339
   UTC instant fixed by this contract as the end of the market session following the
   transition's `market_session` — plus `fact_receipt` (the receipted sha256 already on
   the B3/B1 material, display-inert). `decide_row` (existing owner:
   `engine/alert_delivery_drain.py:484-531`) gains one closed check before the
   quiet-hours branch: `payload.not_after` present and `now_utc > not_after` ⇒
   `Decision(action="suppress", reason="mandatory_fact_stale")`. That reuses the
   incumbent typed-suppress path verbatim — status `'suppressed'` + `last_error` reason
   (`:808-810`), counted in `suppressed_n`, permanently out of the selection predicate —
   so a stale row is never sent with an older value and never retried. No new enum
   value, table, or marker is introduced; the reason string is the only new vocabulary,
   as `EFFECT_UNKNOWN_LAST_ERROR` was (`:102-107`).

## 6. Entitlement and premium leakage (Q6)

The preventing check, quoted — `engine/alert_delivery_drain.py:513-520`:

```
    if ent.state == READ_UNAVAILABLE:
        return Decision(action="unevaluable", reason="entitlement_unavailable")
    requires_tier = payload.get("requires_tier")
    ent_decision = entitlement_decision(ent, now_utc, requires_tier=requires_tier)
    if ent_decision == "unavailable":
        return Decision(action="unevaluable", reason="entitlement_unavailable")
    if ent_decision == "suppress":
        return Decision(action="suppress", reason="entitlement_lapsed", to_email=to_email, lang=prefs.lang)
```

`entitlement_decision` fails closed end to end: no entitlement row + a `requires_tier`
⇒ suppress; lapsed statuses (`canceled/past_due/unpaid/incomplete_expired`) ⇒ suppress;
an unparsable `current_period_end` ⇒ suppress; "an unrecognised status … suppresses
rather than sends -- this is the paid lane" (`engine/alert_delivery_drain.py:432-469`;
entitlement row read `:780`). Premium Prophet content therefore sets
`payload["requires_tier"]` to the canonical tier string that gates the Prophet surface
(resolved through `lib/tiers.py::tier_rank()` from `config/plans.yml`,
`lib/tiers.py:179-200`; the exact literal is bound by the B07 entitlement-surface
decision — B21 fixes the mechanism, not the catalog value). B21 adds no new check; it
consumes this one.

**What the email body may contain:** exactly the `compose_alert` contract fields —
`ticker`, `condition_plain`, `evidence_url`, `subject`, `fired_at` (+ category for the
drain; fif precedent `engine/fif_saved_research_notifications.py:436-454`). Plain
language only; no values, no scores, no slugs, no prices, no zone levels, no B4 metrics
(`distance_to_zone_pct` & co. are "values"); banned-token discipline twice — at persist
(producer `_BANNED_TERMS`, `:109-112`) and at render (`_ALERT_BANNED_TOKENS`,
`app/mailer.py:1334-1337`, fallback not verbatim). The subject line is the incumbent
`<ticker> alert · <ticker> 提醒` form (`app/mailer.py:1426-1429`).

## 7. Delivery versus read (Q7)

`email_log.status='sent'` means the relay accepted responsibility:
"Returning normally from ``send_message`` means ``sendmail`` read a 2xx reply to the
terminating '.', i.e. the relay took responsibility. That is the strongest claim SMTP
permits and it is what this ledger means by 'sent'." (`app/mailer.py:445-449`.) The
outbox's `delivered_at` is the drain's own resolution time — "never earlier than the
real send and … honest about what is actually known" (`engine/alert_delivery_drain.py:845-856`).
No open, pixel, or click signal exists anywhere in the lane, and building one is
forbidden by the B21 release limit ("no … click-feedback trading model"). **B21 may
claim:** "an SMTP-accepted message to `<address>`, resolved at `<time>`" — nothing about
reading, opening, or acting. Read-state language ("you saw", "as you read") must not
appear in copy or receipts.

## 8. Proof shape (Q8)

Real source change → existing transport → receipt readback:

1. **Real source change.** A genuine B1 ledger event for a security on a real
   subscription: an operator/test account creates the designated watchlist
   "Prophet Research" through the existing WatchStore surface and adds a name
   (`templates/watchstore.js` — no code); the nightly engine then lands a real
   STATE_TRANSITIONED / TURN WATCH / RETRACTED event in the episode store the producer
   reads (local snapshot on the runner, fif input law). No synthetic outbox insert is a
   proof.
2. **Existing transport.** Nightly producer step (dormant-until-flagged runner
   registered as a `config/dag.yml` step, fif precedent `:1829-1830`; thesis precedent
   `:1409-1413`) → `public.alert_outbox` → the drain timer (every 5 min,
   `engine/alert_delivery_drain.py:4`) with **`ALERT_DRAIN_ENABLE` left as the operator
   gate** — the runner is "Dormant by default: without ``ALERT_DRAIN_ENABLE=1`` … this
   script" stays decision-only (`scripts/drain_alert_outbox.py:11`, `:51-54`). The
   build/proof lane never latches the flag on; enabling it on the VPS app host is an
   operator act.
3. **Receipt readback.** The drain's existing canary lane selects exactly one row by
   `fire_event_id` with cardinality + identity proof before any effect
   (`engine/alert_delivery_drain.py:693-696`, `:706-740`); readback is the outbox row at
   `status='sent'` plus the `email_log` row under
   `alert_fire:<fire_event_id>[:attempt]` (`:857-861` read shape) at `status='sent'`,
   received in the **authorized test recipient's** actual inbox — an operator-held
   address that is signed in, `alert_email_optin` on, `prophet_research_journey`
   selected, absent from `email_suppression`, and holding an entitled
   `user_entitlements` row (all four drain gates exercised: `:493-530`).
4. **Human-only list.** (i) enabling/keeping `ALERT_DRAIN_ENABLE=1` on the VPS host and
   deciding when it stays on; (ii) providing the authorized test recipient, its
   credentials/inbox, and its entitlement row; (iii) reading the human inbox; (iv)
   ratifying the designated watchlist display name and any correction copy (the §4
   effect-unknown wording); (v) relay/credential access if a quarantined row must be
   investigated. Everything else in this contract is buildable and provable by a
   bounded worker.

## 9. Smallest build units (Q9)

| # | unit | owner file(s) extended | state | blocking fact |
|---|---|---|---|---|
| U1 | `ALERT_CATEGORIES` member + comment line + enum gate | `lib/user_prefs.py:68-72`, `tests/test_alert_prefs.py` | **READY** | none technical; coordination fact = open cs-v2 lane `9807f9067f80` edits the same tuple (§3 bytes) — merge-order coordination, both gates must accept the union |
| U2 | pure producer core: §1 eligibility, §2 id + synthetic alert_id, payload compose, `not_after`, requires_tier | new `engine/prophet_journey_notifications.py` (fif shape; pure half) | **READY** | none |
| U3 | IO + dormant runner + `config/dag.yml` step row | fif IO shape (`read_designated_lists`/`read_list_symbols`/`read_existing_fire_ids`/`enqueue`, `:577-657`) | **READY** | none (nightly engine job config owner) |
| U4 | correction/retraction rows: original-status readback (`status,attempts,last_error` select), unsent-supersede PATCH, typed `original_quarantined` count (the readback + typed counts landed in U2 under seat ruling F28 R5/R6; key name as implemented) | extends U3's read; PATCH analogue = terminal one-shot disarm | **READY** | none legal; the effect-unknown copy variant is a Sol ruling (open, §4) |
| U5 | drain stale-fact guard: `not_after` check in `decide_row`, reason `mandatory_fact_stale` | `engine/alert_delivery_drain.py:484-531` | **READY** | none (drain lane; pin suite `tests/test_alert_delivery_drain.py` at BASE) |
| U6 | premium payload `requires_tier` | U2 payload | **READY** | exact tier literal pends the B07 entitlement-surface decision (mechanism fixed, §6) |
| U7 | account-UI category row + i18n strings | `templates/account.js:655-656` | **READY, deferrable** | honest-absence ruling permits shipping after the producer (§3.4); no blocker |
| U8 | end-to-end proof (§8) | drain canary + timer | **BLOCKED** | human-only gate set (§8.4): `ALERT_DRAIN_ENABLE` on the host, authorized recipient + entitlement + inbox, copy ratifications |
| U9 | B4 availability alerts | — | **BLOCKED (out of scope by law)** | no same-read caller exists (§1 searches); making one requires a new series store, forbidden by the B21 release limit |
| U10 | user-facing journey completeness | B07/B20 | **BLOCKED** | BUILD_PROGRAM units B07 and B20 are `SPECIFIED_NOT_DISPATCHED` at BASE (`…/effective/BUILD_PROGRAM.json`); B21 `depends_on: ["B07","B20"]` — Fable Meta-CEO sequencing decision, does not block U1–U7 |

## 10. Absent / not found

- `supabase/migrations/*` — not in this repo at BASE (`git ls-tree HEAD` has no
  `supabase/` path; `ls supabase/migrations/` → No such file). The `alert_outbox`
  column set is quoted from the thesis monitor's citation of terminal PR #513's
  `0013_alert_runs_outbox.sql` (`engine/thesis_condition_monitor.py:46-51`); the
  watchlists no-metadata-column fact likewise arrives via the fif citation of Terminal
  `0001_init.sql:29-36` (`engine/fif_saved_research_notifications.py:9-13`). Searches
  run: `git ls-tree HEAD --name-only | grep -i supa` (empty), `grep -rn
  "supabase/migrations" engine/ app/` (citations only).
- Open-PR metadata (number/labels/review state) for the cs-v2 enum edit — not
  available on host without network; only the branch head `9807f9067f80` is readable
  (§3). No `gh` calls were made (packet no-network rule).
- Any correction/revocation mechanism for delivered alerts — not found. Searches:
  `grep -rn "corrects_\|supersedes_\|retraction" engine/ app/ scripts/` (only B1
  episode-ledger vocabulary hits), `grep -n "correction" engine/alert_delivery_drain.py
  app/mailer.py` (none).
- A same-read B4 caller / persisted B4 series — not found (searches quoted in §1).
- A producer for `holdings_material_change` — not found (D05-b, ruling `:15`, `:24`);
  B21 does not touch it.
- `email_log` DDL — not re-read here; its semantics are quoted from the drain's pinned
  citation of `research/SUPPORT_EMAIL_ESTATE_MASTERPLAN_BY_FABLE.md`
  (`engine/alert_delivery_drain.py:846-856`).
- Live value of `ALERT_DRAIN_ENABLE` on any host — not inspected (host environment
  fact; the gate's existence and dormancy law are quoted from
  `scripts/drain_alert_outbox.py:11,:51-54`).

## 11. Outcome files avoided

None opened. The whole `data/` tree (ledger, scoreboard, track-record and outcome
classes) is excluded from this sparse worktree by the standing profile
(`config/sparse_worktree.json` `exclude_dirs: ["data","site","mockups","verify_shots"]`),
so no outcome-class file was reachable, and no `*scoreboard*`/`*track_record*`/
`*outcome*`/`*returns*` path was read. The B1/B3/B4 contract modules read for this
contract contain no realized-outcome data.
