# D05 — durable user-action owner census (Prophet US R6 wave-0)

Read-only census. No engine/, scripts/, tests/, templates/, .github/ or data file was
modified; this record is the lane's only write.

## SOURCE_SHA

- `SOURCE_SHA = fc6db6c1f9a76cadc180c44e386ae928c1a9ccbc` (`git rev-parse HEAD`, detached,
  byte-equal to `git rev-parse origin/main` — both printed the same sha).
- sha12 used in cites: `fc6db6c1f9a7`.
- **Cite convention.** Every cite is `path:line@fc6db6c1f9a7`. Inside the TABLE the
  `@fc6db6c1f9a7` suffix is written ONCE per cell (on its first cite) and applies to every
  other `path:line` in that same cell. Outside the table the suffix is written on the first
  cite of each block.
- Worktree is SPARSE (`data/`, `site/`, `mockups/`, `verify_shots/` not checked out —
  `python3 scripts/worktree_sparse.py status`). No `data/` artifact was read or is cited.
- Labels: **OBSERVED** = read/run in this lane. **INFERRED** = reasoned from observed code.
  **UNKNOWN** = could not be established; the missing artifact is named.

## TABLE — the seven requested actions

| action | owner module + function/endpoint | storage | account/list isolation | readback after save | episode/generation ref retained? | current UI entry point | verdict |
|---|---|---|---|---|---|---|---|
| **Watch** (add a name) | No macro-api route. Browser → Supabase REST directly: `templates/watchstore.js:486@fc6db6c1f9a7 symbolAdd()` → `:495 _symbolInsert()`; bulk path `:738 pushList()` → `:759 insert`. App-side only ever READS (`app/main.py:1871`) | signed-in: cloud `watchlist_symbols` (+ parent `watchlists`) `templates/watchstore.js:499`, `:756`. signed-out: `localStorage mdash.watchlist.v1` `templates/watchlist.js:25`; per-list render cache `mdash.wl.<listId>.v1` `templates/watchstore.js:191` | RLS owner + via-parent policies, Terminal-owned `supabase/migrations/0001_init.sql` (recorded `templates/uwp_supabase.sql:9`–`11`, `WATCHLIST.md:92`–`96`; not in this repo → the policies themselves are UNKNOWN here). Client side: every op list-scoped `.eq('watchlist_id', listId)` `templates/watchstore.js:500`, `:756`; signed-out calls inert `:1549`–`1550` | YES — server read of that one list `templates/watchstore.js:458 symbolsFetch()` → `:461`–`464`; server-side readback `app/main.py:1878`–`1880` inside `GET /api/portfolio/brief` `app/main.py:1892` | NO — insert payload is `{watchlist_id, symbol, section, position}` `templates/watchstore.js:500`, `:756`; read selects only `symbol, position, created_at` `:462` | `templates/watchlist.js:531`, `:1912` (`data-add` chips) → handlers `:2298`–`2299`, `:2433`–`2434` on `site/watchlist.html` (`templates/watchlist.html.j2:13`). NONE on any Prophet surface (`grep -rn "data-add\|WatchStore\|WLCloud" templates/plans.html.j2 templates/_prophet_card.html.j2 templates/_us_prophet_plan_cards.html.j2` → 0 hits) | **DURABLE_CLOUD** signed-in / **LOCAL_ONLY** signed-out |
| **Unwatch** (remove a name) | `templates/watchstore.js:508@fc6db6c1f9a7 symbolRemove()` → `:512`–`515 DELETE .eq('watchlist_id').in('symbol')`; delete half of the full-membership diff `:766`–`779`. Local side `templates/watchlist.js:258 remove()` | same table/blob as Watch: cloud `watchlist_symbols` `templates/watchstore.js:512`; local blob `templates/watchlist.js:259`–`260` → `localStorage` `:187` | same RLS; every delete carries `.eq('watchlist_id', listId)` `templates/watchstore.js:514`, `:770` — a localStorage cache is never a delete authority (`:689`–`696`), pinned `tests/test_watchstore_multilist_js.py:779` | YES — `symbolsFetch` `:458`. CAVEAT (OBSERVED in code): the next `pull()` merges cloud→local as a UNION `templates/watchstore.js:572`–`573` → `templates/watchlist.js:267`–`292`, so a symbol whose cloud delete never landed comes BACK | NO — `:512`–`515` names only `watchlist_id` + `symbol` | `templates/watchlist.js:403`, `:1109` (`data-rm` buttons) → `:2296`–`2297`, `:2431`–`2432`; list delete `:2055` | **DURABLE_CLOUD** signed-in / **LOCAL_ONLY** signed-out |
| **Pass + reason** (user declines a candidate and says why) | **NONE.** No route in `app/` accepts a user disposition: all 27 `@app.post`/`@router.post` routes in `app/*.py` are account, prefs, billing, brain, portfolio-read, forensics, biocatalyst, options, research, support, unsubscribe (`grep -rn "@router.post\|@app.post" app/*.py`). "Passed on tonight" is an ENGINE disposition rendered read-only (`templates/_prophet_receipts.html.j2:29`–`30`, `:123`–`135`) | **NONE** | **NONE** | **NONE** | **NONE.** `generation_id` exists only on read-only display surfaces (`templates/ticker.html.j2:1823`, `templates/_macro_suite_shell.html.j2:956`, `templates/time_machine.js:882`) | **NONE** — no button, no form, no store | **NONE** |
| **thesis / milestone note** | Three distinct sub-owners, none of them one thing. (a) note on a WATCHLIST symbol: blob field only `templates/watchlist.js:168@fc6db6c1f9a7`, `:240`, preserved across sync by `templates/watchstore.js:224`–`243`. (b) note on a POSITION: `templates/portfolio.js:1768` → `templates/watchstore.js:1431 portfolioUpsert()` `:1459`. (c) a durable user THESIS object: Supabase `public.theses` + `public.thesis_versions`, READ here at `engine/thesis_condition_monitor.py:599`–`604`, `:612`–`623` | (a) `localStorage` ONLY — `watchlist_symbols` has no note column BY RULING `WATCHLIST.md:34`–`35`, pinned `tests/test_watchstore_multilist_js.py:347`. (b) cloud `portfolio_positions.notes` `templates/watchstore.js:1289`, `:1459`. (c) cloud tables whose DDL lives in mastermind-terminal (`engine/thesis_condition_monitor.py:22`–`36`) | (a) per-browser, per-list key `templates/watchlist.js:37`. (b) 4 own-row RLS policies IN THIS REPO `templates/uwp_supabase.sql:36`–`56` + `.eq('user_id', uid)` `templates/watchstore.js:1467`. (c) `theses.user_id` (`engine/thesis_condition_monitor.py:601`, `:618`) — policies UNKNOWN here | (a) NO cloud readback (nothing to read back). (b) YES — the write returns the row `.select().single()` `templates/watchstore.js:1468`–`1469`, `:1477`–`1478`. (c) YES for the read path `engine/thesis_condition_monitor.py:604`, `:619` | (a) NO. (b) NO — column set is `id,user_id,ticker,shares,entry_price,entry_date,notes,status` `templates/watchstore.js:1289`. (c) NO episode/generation id — the join key is `subject_ref` `engine/thesis_condition_monitor.py:601`; `thesis_version` is DISPLAY only, never hashed `:32`–`34` | (a) NONE — no authoring input exists (`grep -rn "\.note *=\|setNote\|editNote" templates/*.js` → only `templates/watchlist.js:168`, `:278`). (b) `templates/portfolio.js:1518`, `:1546`, `:1768` (`#pfm_notes`) on `site/watchlist.html`. (c) NONE in this repo | (a) **LOCAL_ONLY** (and unreachable). (b) **DURABLE_CLOUD**. (c) cloud table, **no in-repo writer** → the write path is UNKNOWN |
| **existing-position review** | The review ACT has no owner; the reviewed OBJECT does. Client `templates/watchstore.js:1192@fc6db6c1f9a7 portfolioList()` → `:1228`–`1231`. Server `app/main.py:1824 _portfolio_load_holdings()` → `:1857`–`1859`; endpoints `GET /api/portfolio/brief` `app/main.py:1892`, `POST /api/portfolio/changes` `:1976` (computes a diff, writes nothing `:1995`–`2005`) | signed-in cloud `portfolio_positions` `templates/watchstore.js:1228`, writes `:1464`–`1482`; signed-out `localStorage mdash.pf.v1` `:901`, CRUD `:1053`–`1077` | A1A authority law `templates/watchstore.js:1150`–`1159`: signed-in is NEVER local mode `:1171`; `.eq('user_id', uid)` on every query `:1230`, `:1467`; per-user cache reset on every uid transition `:1595`–`1600`; RLS `templates/uwp_supabase.sql:36`–`56` | YES — the write returns the row `templates/watchstore.js:1468`–`1469`; read `:1228`–`1231`; server `app/main.py:1892` | NO — row build is `user_id,ticker,shares,entry_price,entry_date,notes,status,updated_at` `templates/watchstore.js:1453`–`1462` | `templates/portfolio.js` (cockpit) on `site/watchlist.html`; held-name marking `templates/research_screener.html.j2:170`–`175`; nav entry `templates/_navlinks.html.j2:229` | positions **DURABLE_CLOUD**; the review act itself **NONE** (nothing records that a review happened) |
| **alert subscription** | `app/account_prefs.py:131@fc6db6c1f9a7 POST /api/account/prefs` → `save_prefs` `:132` → `_write_user_metadata` `:194`. Fields `alert_email_optin`, `alert_categories`, `tz`, `quiet_hours` `:96`–`105`. Consumers: `engine/alert_delivery_drain.py:310`–`328 parse_alert_prefs`, gate `:495`–`507`; producer for `thesis_window` `engine/thesis_condition_monitor.py:107`, enqueue `:439` | cloud — Supabase auth `user_metadata` (`app/account_prefs.py:10`–`12`), mirrored to `email_prefs.lang` only for `lang` `:196`–`198`. No per-name/per-episode subscription row exists anywhere: `ALERT_CATEGORIES = ("holdings_material_change","thesis_window")` `lib/user_prefs.py:66` | identity from the Bearer token ONLY; a `user_id` in the body is not a field and is never read `app/account_prefs.py:17`–`19`, `:132`–`141` | YES — `app/account_prefs.py:205 GET /api/account/prefs` → `:214`, with honest `unset` null-disclosure `:218` and `categories_available` `:219` | NO — two coarse category strings `lib/user_prefs.py:66`. The fired-alert side does carry `thesis_id`/`thesis_version`/`tripwire_id` `engine/thesis_condition_monitor.py:442`–`445`, but that is the outbox row, not a user subscription | `templates/account.js:452`–`491` (alert group builder; `:479`–`480` the two category rows), GET `:271`, POST `:305`, `:314`; loaded by `templates/seo_base.html.j2` and `templates/neural_web.html.j2` | delivery preference **DURABLE_CLOUD**; a per-name or per-episode alert subscription **NONE** |
| **outcome-history view** | READ: `engine/neuralweb/brain_user_memory.py:718@fc6db6c1f9a7 get_trade_episodes()` → `_build_episodes()` `:753`–`760`; tool allowlisted `engine/neuralweb/brain_gateway.py:325`, `:376`, dispatched `:3730`–`3735`, reached over `POST /api/brain/chat` `app/main.py:1416`. WRITE: `admin/trade_memory.py:126 record()`, owner pinned to the OPERATOR uuid `:30`–`32`, insert `:145`–`158`; nightly store operator-pinned too `engine/neuralweb/trade_memory_store.py:71`, `:98`, `:140`, `:174` | cloud `public.trade_episodes`, DDL IN THIS REPO `scripts/deploy/0008_trade_memory.sql:11`–`52`; sibling `trade_memory_patterns` `:76`–`84`. No customer write path: `grep -rn "trade_episodes" app/*.py` → 0 hits. Self-documented: "Most accounts have NO rows (only the operator console writes episodes today)" `engine/neuralweb/brain_user_memory.py:727` | RLS own-row select/insert/update/delete `scripts/deploy/0008_trade_memory.sql:59`–`72`; read scoped `user_id=eq.<uid>` `engine/neuralweb/brain_user_memory.py:756`; guests get a sign-in note, never an error `:733`–`734` | YES for the read `engine/neuralweb/brain_user_memory.py:755`–`760`; NO write→readback loop for a customer, because there is no customer writer | PARTIAL — `prophet_pick_ref text` `scripts/deploy/0008_trade_memory.sql:26` (free text, ≤240 chars `engine/neuralweb/trade_memory.py:174`), plus `thesis_at_entry` `:24`, `observed_result` `:25`, `evidence_packet jsonb` `:27`, `autopsy jsonb` `:28`. There is NO keyed `episode_id`/`generation_id` column | the Brain chat only. NO dedicated page: `grep -rn "trade_episodes\|get_trade_episodes" templates/` → 0 hits | cloud table + per-user read exist; as a USER ACTION it is **NONE** (no customer writer) |

## Q1 — is watchlist membership stored separately from portfolio holdings?

**YES — two tables, two owners, and a tested never-cross law.** OBSERVED.

- Different tables: `watchlists` + `watchlist_symbols` (membership) vs `portfolio_positions`
  (held positions) — `WATCHLIST.md:9`–`12`@fc6db6c1f9a7, `WATCHLIST.md:30`–`31`.
- Different schema owners: the watchlist pair has always lived in mastermind-terminal
  `supabase/migrations/0001_init.sql` and this repo "has never owned them, and must not
  re-declare them" (`templates/uwp_supabase.sql:9`–`11`); `portfolio_positions`' DDL is
  recorded there too (`:12`–`14`) while THIS repo owns only its four own-row RLS policies
  (`:16`–`18`, `:36`–`56`).
- Different client owners in one module: `WatchStore.symbols.*` (`templates/watchstore.js:1564`–`1569`)
  vs `WatchStore.portfolio.*` (`:1570`–`1583`), with separate local blobs
  (`mdash.watchlist.v1` `templates/watchlist.js:25` vs `mdash.pf.v1` `templates/watchstore.js:901`).
- Never write to each other — pinned by four named invariants `WATCHLIST.md:83`–`88` and
  `tests/test_watchstore_multilist_js.py:1072`, `:1092`, `:1111`, `:1129`, plus
  `:1145` (a full-membership push never reaches `portfolio_positions`).
- The ONE place they meet is a labelled server-side population fallback, not a shared store:
  `app/main.py:1824`–`1889`@fc6db6c1f9a7 returns `"positions"` (`:1868`) or
  `"watchlist_union"` (`:1889`), and a FAILED query is `"unspecified"`, never
  `"watchlist_union"` (`:1839`, `:1860`–`1862`).

Consequence for R6: a Watch action can never satisfy an "existing holdings" question, and an
existing-holdings review can never be answered from watchlist membership without saying which
population it used (`app/main.py:1827`, `:1837`).

## Q2 — which actions would today advertise cloud persistence while persisting only locally?

Explicit list. Items 1–3 are the R6 forbidden case; item 4 is the same honesty class on the
alert side; item 5 records what is NOT in the list.

1. **Watch, signed-in, when the push fails or the device is offline — YES, forbidden case.**
   `pushList()` swallows the failure: `setPill('offline')`, one `warnOnce`, `return null`
   (`templates/watchstore.js:787`–`791`@fc6db6c1f9a7). There is NO retry queue and NO outbox
   for the watchlist scope — the only retries in the module are the fold marker
   (`:670`, `:675`) and the portfolio import path (`:1359`–`1378`). The `online` handler calls
   `pull()` (`:1807`), and `pull()` flushes only pushes that were QUEUED because their list had
   never been read (`:594`, `:721`, `:729`–`736`) — a push that already fired and failed is
   never re-enqueued. Meanwhile the chip copy promises the write-through:
   "Your changes are kept on this device and written through when it comes back"
   (`templates/watchlist.js:863`–`865`). The change does reach the cloud, but only if the user
   happens to edit the list again (the next `pushCloud()` full-membership diff,
   `templates/watchlist.js:2112`–`2117`). OBSERVED in code; the browser sequence was not run here.
2. **Unwatch under the same failure — YES, and it silently reverses.** The local blob drops the
   symbol (`templates/watchlist.js:258`–`262`) while the cloud row survives (`:512`–`515` never
   ran). The next successful `pull()` merges cloud→local as a UNION (`templates/watchstore.js:572`–`573`
   → `templates/watchlist.js:267`–`280`), so the removed name REAPPEARS in the UI, and that same
   `pull()` success dispatches `setPill('synced')` (`templates/watchstore.js:592`) which maps to
   chip state `saved` (`:122`) whose copy is "Saved to your Mastermind account."
   (`templates/watchlist.js:851`–`853`). INFERRED from the observed merge + chip code paths.
3. **The Watchlists chip paints a WRITE claim after a plain READ — YES.**
   `CHIP_STATE = { synced: 'saved', ... }` (`templates/watchstore.js:122`@fc6db6c1f9a7) and
   `synced` is set by BOTH `pushList()` success (`:785`) and `pull()` success (`:592`). The
   page's own documented vocabulary says `saved` = "a WRITE just landed in the account" and
   `clean` = "a READ succeeded from the account; nothing has been written this session"
   (`templates/watchlist.js:819`–`821`), and the Portfolio scope honours that split
   (`templates/portfolio.js:1658`, `:1711`, `:1792`). Nothing dispatches `clean` for the
   Watchlists scope: `grep -rn "'clean'" templates/*.js` returns portfolio-side hits only.
   So a signed-in page load can say "Saved to your Mastermind account" with no write at all.
4. **`holdings_material_change` alert category — advertised, no producer.** It is offered in the
   UI (`templates/account.js:479`), stored durably (`app/account_prefs.py:96`, `:194`), gated on
   delivery (`engine/alert_delivery_drain.py:499`–`507`) — and repo-wide the string appears only
   in the enum, the UI and tests (`lib/user_prefs.py:66`; `templates/account.js:479`;
   `tests/test_account_prefs.py:209`, `:220`, `:301`; `tests/test_alert_delivery_drain.py:862`).
   `thesis_window` DOES have a producer (`engine/thesis_condition_monitor.py:107`, `:439`).
   A subscription that can never fire is the alert-side twin of the forbidden case: disable it
   honestly in EN+ZH, or name the producer that lives outside this repo (UNKNOWN — see
   NOT_ESTABLISHED).
5. **NOT in the list (verified honest, so R6 must not "fix" them).** Signed-out Watch / Unwatch /
   positions say so in plain words — chip `local`, "This list lives in this browser only."
   (`templates/watchlist.js:860`–`862`), and an anonymous write failure gets its own
   device-scoped word `failed_local` (`:869`–`871`, law at `:842`–`849`). A signed-in cloud
   failure NEVER substitutes the local book and never asserts zero: it answers last-good
   (degraded) or `null` (`templates/watchstore.js:1251`–`1262`), pinned by
   `tests/test_portfolio_truth_a1a_js.py:354`, `:380`, `:403` and
   `tests/test_portfolio_auth_transition_js.py:404`, `:458`, `:520`. Watchlist notes are local by
   an explicit recorded ruling (`WATCHLIST.md:34`–`35`), not by an accidental claim.

## Q3 — behaviour-by-behaviour test coverage

Test files named per behaviour. All are OBSERVED by `grep -n "^def test_"` on the file; the two
files marked ✓ were also executed in this lane (see EVIDENCE).

| behaviour | status | files + lines |
|---|---|---|
| duplicate-retry | TESTED | ✓`tests/test_watchstore_multilist_js.py:280` (a racing create adopts the existing row), `:676` (fold twice → identical state), `:712` (empty local book never consumes the one-shot), `:732` (a failed insert never marks the fold, so it retries), `:994` (add reads an unread list first instead of blind-inserting); ✓`tests/test_portfolio_import_a1b_js.py:429` (lost response, all exact → no second insert), `:437` (lost response, proven zero → one retry with identical ids), `:504` (a second lost response after proven zero stops at effect_unknown), `:535` (uuid fold keeps two exact duplicate lots and is idempotent) |
| changed-list | TESTED | ✓`tests/test_watchstore_multilist_js.py:298` (symbol ops isolated between lists), `:321` (per-list caches do not bleed), `:779` (a stale cache of one list can never delete another list's rows), `:831` (a never-read list is never diffed), `:853` (a push issued during the setActive window never lands on the new list), `:904` (two unread lists each keep their own queued push), `:938` (a push with no bound list is refused, not queued for whatever binds later), `:1022` (a push carries its target through the debounce) |
| different-account | TESTED | `tests/test_portfolio_truth_a1a_js.py:566` (anonymous and authenticated reads never share one answer), `:611` (cross-user last-good cloud never survives an auth transition), `:647` (sign-out also resets last-good); `tests/test_portfolio_import_a1b_js.py:470` (a wrong-owner receipt never claims saved even if the owner read is exact), `:528` (an auth generation change suppresses success and never changes owner); `tests/test_portfolio_auth_transition_js.py:1662`, `:1707` (a second user's first healthy read never inherits the prior user's failed chip); ✓`tests/test_watchstore_multilist_js.py:1170` (signed-out multi-list calls are inert and write nothing); server side `tests/test_account_actions.py:548` (files the token owner's row, not a body claim) |
| offline / partial-response | TESTED for the PORTFOLIO scope; **NONE for the WATCHLIST scope** | Portfolio: `tests/test_portfolio_import_a1b_js.py:446` (partial existing batch stops before the insert mutation check), `:462` (a partial receipt never claims saved or blind-retries), `:478` (lost-response partial reconcile stops without retry), `:485` (unavailable reconcile is effect_unknown, no retry), `:492` (unavailable preflight is known zero-effect and retryable); `tests/test_portfolio_auth_transition_js.py:458` (degraded read-only banner on last-good), `:520` (client init failure never serves the local anon book), `:578`, `:617` (write-failure chip history never says offline or saved), `:1260`, `:1323` (never-settling client/read resolves terminal within the deadline); `tests/test_portfolio_truth_a1a_js.py:354`, `:380`. Watchlist: **NONE** — no test asserts what happens after `pushList()` fails (`templates/watchstore.js:787`–`791`); the only offline assertion found is chip vocabulary, `tests/test_watchlist_workspace_js.py:571` |
| corrected-episode | **NONE on any user-action owner** | No user-action store holds an episode reference at all (see the episode-ref column: `templates/watchstore.js:462`, `:500`, `:1289`, `:1453`–`1462`), so there is nothing to correct and no test. The behaviour exists ONLY on the SYSTEM episode store: `tests/test_us_candidate_episode_reconciler.py:655` (`test_explicit_correction_appends_without_mutating_the_original_line` — last-write-wins would erase the immutable event being corrected, `:656`), `:341` (a suppression retry at a later recorded_at retains the original immutable row) |
| deletion | TESTED | ✓`tests/test_watchstore_multilist_js.py:252` (list create/rename/delete round trip), `:554` (binding never deletes the bound list's existing rows), `:779` (delete scoping), `:1111` (removing from a watchlist keeps the portfolio position); `tests/test_portfolio_import_a1b_js.py:174` (remove is explicit and a foreign owner is forbidden); policy side `templates/uwp_supabase.sql:54`–`56` and `scripts/deploy/0008_trade_memory.sql:70`–`72`; account-deletion intake `tests/test_account_actions.py:496`, `:522`, `:579`, `:606`. **NONE**: no test deletes a user thesis/milestone note or a passed-candidate reason, because no such store exists (Q2 item 4, TABLE row 3) |

## Q4 — smallest owner-compatible extension for a durable "saved episode thesis"

**Reuse `public.trade_episodes`. Do not create a second position ledger, and do not touch
`watchlist_symbols`.** INFERRED from the observed DDL, RLS and read path.

Why this is the compatible owner (all OBSERVED):
- The columns the feature needs already exist: `thesis_at_entry text` (`scripts/deploy/0008_trade_memory.sql:24`@fc6db6c1f9a7),
  `prophet_pick_ref text` (`:26`), `evidence_packet jsonb` (`:27`), `observed_result` (`:25`),
  `outcome`/`autopsy_state` (`:23`, `:29`), owner + timestamps (`:13`, `:34`–`35`).
- Own-row RLS for all four verbs is already committed in this repo (`:59`–`72`), so a customer
  row is isolated by the same mechanism the watchlist and portfolio already rely on.
- A per-user reader already exists and is already wired to a user-facing surface
  (`engine/neuralweb/brain_user_memory.py:718`, `:753`–`760`; allowlist
  `engine/neuralweb/brain_gateway.py:325`, `:376`; route `app/main.py:1416`) — and it already
  emits the user's own entry thesis and observed result "AS THEIR WORDS" (`:721`–`723`).
- The privacy contract is already written for exactly this shape: no position size, no account
  value, no dollar P&L column (`scripts/deploy/0008_trade_memory.sql:7`,
  `engine/neuralweb/brain_user_memory.py:724`–`725`).

The three changes, smallest first (only #3 is optional):
1. **One new `source` enum value.** `scripts/deploy/0008_trade_memory.sql:15` currently allows
   only `('operator','prophet','historical_replay')`; the same set is `SOURCES` in
   `engine/neuralweb/trade_memory.py:34`. A customer-entered episode needs one more value.
   This is production DDL applied through the Supabase SQL editor / Management API
   (`scripts/deploy/0008_trade_memory.sql:2`) — NOT by this lane and not by a builder without
   an operator ratification act.
2. **One caller-scoped writer route.** Both existing writers are operator-pinned
   (`admin/trade_memory.py:30`–`32` + `:126`; `engine/neuralweb/trade_memory_store.py:42`, `:71`,
   `:174`). Add one `app/` route that inserts with `user_id = require_user(...)` and nothing
   else, copying the authed-route shape already in the tree (`app/account_prefs.py:132`,
   `app/main.py:1893`) and letting RLS (`scripts/deploy/0008_trade_memory.sql:64`–`66`) be the
   isolation. Normalize through the existing `normalize_episode`
   (`engine/neuralweb/trade_memory.py`, exercised by `tests/test_trade_memory.py:67`, `:74`, `:81`)
   so the no-size/no-P&L contract is enforced by the owner, not by the route.
3. **Episode identity in the EXISTING pointer, not a new table.** `prophet_pick_ref` is already
   free text ≤240 chars (`engine/neuralweb/trade_memory.py:174`) — carry
   `<episode_id>@<generation_id>`, the two ids the read side already pins and renders
   (`app/prophet_lab.py:281`–`306`; `templates/ticker.html.j2:1823`). ONLY if the seat needs a
   joinable key rather than a display pointer: add two nullable text columns `episode_id` /
   `generation_id` to the SAME table in the same additive idempotent file. That is the ceiling of
   this proposal.

Alternatives rejected, with the reason:
- A note column on `watchlist_symbols` — forbidden by an existing ruling
  (`WATCHLIST.md:34`–`35`: "this program does not add one").
- `portfolio_positions.notes` — a position is not an episode; the column is free text with no
  episode key (`templates/watchstore.js:1289`), and reusing it would fuse the two stores Q1 keeps
  apart (`tests/test_watchstore_multilist_js.py:1092`, `:1145`).
- A new `user_theses` / `saved_episode_theses` table — would be a second owner for something
  `public.theses` + `public.trade_episodes` already own
  (`engine/thesis_condition_monitor.py:24`–`25`).
- **NONE-NEEDED is not the answer**: today a customer cannot persist an episode thesis at all
  (TABLE rows 3, 4a, 7).

Route choice for the seat, if it prefers the thesis object over the journal: `public.theses` /
`thesis_versions` already mean "the user's standing watch" and already hold the user's OWN
falsifier text (`engine/thesis_condition_monitor.py:24`–`25`, `:38`–`40`), and a thesis already
drives a real alert (`:107`, `:439`). Their writer is not in this repo → UNKNOWN; the missing
artifacts are mastermind-terminal `supabase/migrations/` and the Terminal route that writes
`theses`. Choosing that route makes this a two-repo change; choosing `trade_episodes` keeps it
in one.

## EVIDENCE — commands and captured tails

All commands ran in `/Users/chriswong/lanes/wt/mo-ext-fix-pu_d05_persistence` (a linked sparse
worktree; `.git` is a gitfile → `lanes/repos/macro/.git/worktrees/mo-ext-fix-pu_d05_persistence`).

```
$ git rev-parse HEAD && git rev-parse origin/main
fc6db6c1f9a76cadc180c44e386ae928c1a9ccbc
fc6db6c1f9a76cadc180c44e386ae928c1a9ccbc          rc=0

$ git status --porcelain=v1 -b | head -3
## HEAD (no branch)                                rc=0   (clean detached HEAD == origin/main)

$ python3 scripts/worktree_sparse.py status | head -3
worktree-sparse: SPARSE checkout — omitting data, mockups, site, verify_shots
worktree-sparse: sparse worktree — data, mockups, site, verify_shots not checked out; ...
                                                          rc=0

$ grep -rn "watch" app/*.py | head -40            rc=0   → 25 lines; no watch WRITE route.
  app/main.py:1871:    lists = _sb_get(f"watchlists?user_id=eq.{quid}&select=id&order=position")
  app/main.py:1879:        f"watchlist_symbols?watchlist_id=in.({id_filter})"

$ grep -rn "@router.post\|@app.post" app/*.py | head -60   rc=0 → POST_ROUTE_COUNT=27, none a
  user disposition / pass / thesis / alert-subscription-by-name writer.

$ grep -rln "create table\|supabase" app engine config scripts | head -20   rc=0
  → scripts/deploy/0005..0008*.sql, templates/uwp_supabase.sql are the in-repo schema files.

$ grep -n "premiumdata" scripts/build_site.py app/*.py | head   rc=0
  scripts/build_site.py:3095:ETF_PAYLOAD_DIR = "premiumdata"
  scripts/build_site.py:3179:    """Render the paid remainder of the ETF desk into site/premiumdata/etfs.json.
  scripts/build_site.py:3243:    /premiumdata/etfs.json instead. The shell literally does not contain them, so
  scripts/build_site.py:4889:US_PAYLOAD_DIR = "premiumdata"
  app/regwall.py:67:# a separate payload (/premiumdata/*, plus /allocationdata/special_situations.json
  → the premium/private split is a BUILD-time payload split enforced by app/paywall.py
    (app/regwall.py:63–71). No user-action store writes into it, so no action row above can
    leak a paid payload; conversely a saved thesis must never embed premium payload bytes.

$ grep -rn "holdings_material_change" . | grep -v node_modules   rc=0 → 7 hits only:
  lib/user_prefs.py:66 · templates/account.js:479 · tests/test_account_prefs.py:209,220,301
  · tests/test_alert_delivery_drain.py:862.  No producer.

$ grep -rn "trade_episodes" app/*.py   rc=0 → no output (0 hits): no customer HTTP writer.

$ python3 -m pytest tests/test_watchstore_multilist_js.py -q -p no:cacheprovider
.................................                                        [100%]
33 passed in 8.61s                                                       rc=0

$ python3 -m pytest tests/test_portfolio_import_a1b_js.py -q -p no:cacheprovider
FAILED tests/test_portfolio_import_a1b_js.py::test_import_assets_have_shipping_site_pairs
FAILED tests/test_portfolio_import_a1b_js.py::test_a1b_badge_refresh_follows_authoritative_rows_and_keeps_shipping_pairs
2 failed, 29 passed in 1.76s                                             rc=1
  Both failures are SPARSE-Worktree artifacts: pytest itself printed
  "This checkout omits data, mockups, site, verify_shots ... sparse worktree — site not
  checked out". Both assert `templates/`↔`site/` byte-pairs, and `site/` is not materialized
  here. Not a code defect and not fixed by this read-only lane. The 29 passing tests include
  every duplicate-retry / partial-response / wrong-owner case cited in Q3.
```

Line-ranged reads (no whole-file dumps): `WATCHLIST.md:1`–`144`;
`templates/watchstore.js:118`–`182`, `:458`–`530`, `:678`–`830`, `:890`–`1000`, `:1000`–`1140`,
`:1140`–`1300`, `:1431`–`1500`, `:1544`–`1600`, `:1795`–`1840`;
`templates/watchlist.js:258`–`292`, `:750`–`800`, `:810`–`935`, `:2100`–`2140`, `:2340`–`2365`;
`app/account_prefs.py:1`–`60`, `:85`–`230`; `app/main.py:1855`–`1900`, `:1976`–`2005`;
`app/prophet_lab.py:1`–`92`, `:281`–`373`; `engine/thesis_condition_monitor.py:1`–`40`,
`:425`–`460`, `:595`–`630`; `engine/neuralweb/brain_user_memory.py:718`–`760`;
`engine/neuralweb/trade_memory_store.py:60`–`115`; `engine/alert_delivery_drain.py:300`–`330`,
`:495`–`515`; `scripts/deploy/0008_trade_memory.sql:1`–`90`; `templates/uwp_supabase.sql:1`–`58`;
`admin/trade_memory.py:25`–`40`, `:120`–`160`; `lib/user_prefs.py:66`–`76`;
`tests/test_watchstore_multilist_js.py:347`–`400`.

## BLOCKED

- **Conflicting PR instruction inside this commission.** The MISSION block says "open the PR
  yourself as DRAFT" (`gh pr create --draft ...`); the ROLE/DELIVERY block for the same operation
  (`operation prophet-us-fable-meta-ceo-20260923-001`) says "The lane opens the DRAFT PR itself —
  you do not." Resolution taken: push the branch (both blocks require it), then check once
  whether a PR for that head already exists; create the DRAFT only if none does, and report which
  happened. No `gh pr ready|merge|edit|review|comment` was or will be used.
- **Sparse worktree.** `site/`, `data/`, `mockups/`, `verify_shots/` are not checked out and were
  not opted into (lane instruction). Two consequences, both handled above: the `site/`-pair tests
  cannot pass here, and no `data/` artifact is cited.
- **Terminal-repo schema is not readable from this lane.** `watchlists` / `watchlist_symbols` /
  `portfolio_positions` / `theses` / `thesis_versions` / `alert_outbox` / `alert_runs` DDL and RLS
  live in `mastermindx-market-intelligence/mastermind-terminal` `supabase/migrations/`
  (`templates/uwp_supabase.sql:6`–`14`; `engine/thesis_condition_monitor.py:22`–`23`, `:46`–`50`).
  This lane stayed inside its own worktree, so those policies are cited from the in-repo records
  that name them, not read directly.
- No step of the census itself was blocked: every requested READ target existed on `origin/main`.

## NOT_ESTABLISHED

Each UNKNOWN names the artifact that would settle it.

1. **The live RLS text on `watchlists` / `watchlist_symbols`.** Isolation is cited from
   `templates/uwp_supabase.sql:9`–`11` and `WATCHLIST.md:92`–`96`, which both point at
   mastermind-terminal `supabase/migrations/0001_init.sql`. Missing artifact: that file (or a
   Supabase introspection of the two policies). `WATCHLIST.md:140`–`144` still lists the two-account
   RLS verification as a to-do, so it has not been receipted in-repo.
2. **Who writes `public.theses` / `thesis_versions`, and whether a milestone is a first-class
   field there.** This repo only reads them (`engine/thesis_condition_monitor.py:599`–`623`) and
   records that the merged migration has exactly those two tables and no `thesis_conditions`
   (`:24`–`31`). Missing artifacts: mastermind-terminal `supabase/migrations/` + the Terminal
   route/UI that creates and revises a thesis.
3. **Whether `holdings_material_change` has a producer outside this repo.** In-repo there is none
   (Q2 item 4). Missing artifact: a Terminal or nightly producer that enqueues an
   `alert_outbox` row with `category='holdings_material_change'`.
4. **The runtime behaviour of the chip sequence in Q2 items 1–3.** Established by reading the code
   paths, not by a browser run — this lane is read-only and ran no Playwright/browser evidence.
   Missing artifact: a `browser/` proof script exercising add-while-offline → reconnect → pull,
   and a `verify_shots/` receipt of the chip copy in dark+light × EN/ZH.
5. **The exact live column set of `portfolio_positions` and `trade_episodes`.** Cited from the
   in-repo records (`templates/watchstore.js:1289`; `scripts/deploy/0008_trade_memory.sql:11`–`52`)
   and from `templates/uwp_supabase.sql:12`–`14`, which states the `portfolio_positions` table was
   created by hand against prod and its recorded migration merely "matches the introspected live
   shape". Missing artifact: a fresh introspection of the live Supabase project
   `fsldfzlxyavsuwqbceod`.
6. **Whether any Prophet surface will even offer these seven actions.** No Watch / Pass / note /
   alert entry point exists on `templates/plans.html.j2`, `templates/_prophet_card.html.j2` or
   `templates/_us_prophet_plan_cards.html.j2` today (TABLE, UI-entry column). Missing artifact: the
   R6 wave-1 UI packet that names the surfaces — until then rows 3, 4a and 7 have no entry point to
   attach an owner to.
