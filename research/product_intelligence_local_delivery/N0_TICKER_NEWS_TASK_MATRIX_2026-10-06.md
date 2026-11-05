# N0 — Ticker-news R1 task-to-source/test matrix (read-only census)

Pins: **MAIN_PIN** `892157418ec6b8664d3a0d4ead12011826fc82b4` (`git rev-parse origin/main` after `git fetch origin main`); **PR #8454 head** `66ff33ac507bb2eb7c18443a0cd27e79b20933ad`; **TERMINAL_PIN** `e17622b1a05fc8891e44bc3bac2d2a178c1820d7` (`/home/longr/lanes/tmp/mi-n0-terminal`).

## C0 — Task 4 comment head vs PR head

Comment `5987919846` names Task 4 source head `80dec0eeefaf02017506a11c6d1f91f473857626`; PR head is `66ff33ac507bb2eb7c18443a0cd27e79b20933ad`.

**Compare API** (`gh api repos/mastermindx-market-intelligence/macro/compare/66ff33ac507bb2eb7c18443a0cd27e79b20933ad...80dec0eeefaf02017506a11c6d1f91f473857626 --jq '{status,ahead_by,behind_by,merge_base:.merge_base_commit.sha,files:[.files[].filename]}'`):

```json
{"ahead_by":0,"behind_by":17,"files":[],"merge_base":"80dec0eeefaf02017506a11c6d1f91f473857626","status":"behind"}
```

**Local ancestry** (`git merge-base --is-ancestor 80dec0ee… 66ff33ac…`; exit 0): `80dec0ee` **is an ancestor** of PR head; PR head is **17 commits ahead** (`git log --oneline 80dec0ee..66ff33ac | wc -l` → 17); **zero** commits on `80dec0ee` not contained in PR head (`git log --oneline 66ff33ac..80dec0ee | wc -l` → 0).

**Named refs** (`git ls-remote origin | grep -c 80dec0ee`): `0` (no ref **name** contains that substring).

**Fetch by SHA** (`git fetch origin 80dec0eeefaf02017506a11c6d1f91f473857626`): succeeded (`-> FETCH_HEAD`).

**Decision for N1:** Task 4 store/migration source at `80dec0ee` is **published on the PR branch head** (strict subset). The comment head is **stale as “current tip”** but **not unpublished**. N1 must still treat Tasks 5–6 Macro API and all Terminal work as separate gates; nothing on `80dec0ee`-only that is missing from `66ff33ac`.

---

## Q1 — Task inventory (Tasks 1–12)

| Task | Name (short) | Stated state | Evidence |
| --- | --- | --- | --- |
| 1 | Provider-neutral revision normalization | SOURCE-BUILT-NOT-PROVEN | Plan Task 1 `66ff33ac:docs/superpowers/plans/2026-10-04-terminal-ticker-news-end-to-end.md:53`; frontier Tasks 1–2 BUILT_NOT_PROVEN `66ff33ac:research/ticker_news/IMPLEMENTATION_FRONTIER_2026-10-04.md:5` |
| 2 | Deterministic reduction / withdrawals | SOURCE-BUILT-NOT-PROVEN | Plan `:69`; frontier `:5`, `:44–56` |
| 3 | Exact universe + clustering | SOURCE-BUILT-NOT-PROVEN | Plan `:81`; frontier `:58–88` |
| 4 | qbus persistence / migration | SOURCE-BUILT-NOT-PROVEN | PR comment `5987919846` (“source-built / not production-proven”); plan `:98` |
| 5 | Benzinga + Massive adapters / runner | SOURCE-BUILT-NOT-PROVEN | Plan `:111`; PR head adds collectors + `scripts/run_qbus_news.py` (merge-base diff); comment `5987919846` “Next source wave: Task 5…” |
| 6 | Macro API read/stream | SOURCE-BUILT-NOT-PROVEN | Plan `:124`; head commit `66ff33ac` message “mount private ticker-news API” |
| 7 | Terminal server contract + proxy | NOT STARTED | Plan `:139`; Mastermind `03_WORK_PACKAGES.md` N1 paths; TERMINAL_PIN paths **FREE** |
| 8 | Ticker story panel + navigation | NOT STARTED | Plan `:152`; N2 paths **FREE** on TERMINAL_PIN |
| 9 | E2E fault, load, coverage, security | RELEASE-GATED | Plan `:163`; package N “Release: Tasks 9–12 remain under…” |
| 10 | Licensing / source-quality gate | RELEASE-GATED | Plan `:177`; package same |
| 11 | Release, canary, natural soak | RELEASE-GATED | Plan `:183` |
| 12 | Acceptance, expansion, deferred consumers | RELEASE-GATED | Plan `:191` |

PR #8454 body (`/home/longr/lanes/tmp/pr8454.json`): mission **NOT COMPLETE** at plan publication; **DRAFT / DO NOT MERGE**; no paid feed or worker started. Comment `5985393200`: “Records published; product not implemented” at frontier `43bb3287` (superseded by later source on head). Package ceiling: “Tasks 1–6 contain source increments; hosted/integrated/release/Terminal/natural proof is not established” (Mastermind `03_WORK_PACKAGES.md` N section).

---

## Q2 — Task-to-source / test / CI matrix

Evidence commit for implementation files: **`66ff33ac`** unless noted. Entry points are **line numbers on that commit**.

| Task | Primary source (entry) | Tests (`path::test_name`) | CI enrollment |
| --- | --- | --- | --- |
| 1 | `engine/qbus_news_contract.py:274` (`normalize_news`) | `tests/test_qbus_news_contract.py::test_ws_created_normalizes_identity_clocks_and_metadata` (+ 13 more in file) | **NOT ENROLLED** — `git show 66ff33ac:.github/ci/legacy-jobs.yml \| rg 'test_qbus_news\|test_benzinga_news\|test_ticker_news'` → no match; scope `.github/ci/`, `scripts/ci_*`, `tests/ci_manifest*` |
| 2 | `engine/qbus_news_reducer.py:1` (module); `reduce_revision` per tests | `tests/test_qbus_news_reducer.py::test_explicit_delete_with_newer_direct_event_withdraws_and_removes_index_memberships` (+ 14) | **NOT ENROLLED** (same grep scope) |
| 3 | `engine/qbus_news_universe.py:1`; `engine/qbus_news_cluster.py:1` | `tests/test_qbus_news_universe.py::test_variable_constituent_count_is_preserved_not_capped_at_500`; `tests/test_qbus_news_cluster.py::test_same_upstream_item_across_routes_is_same_story_identity` | **NOT ENROLLED** |
| 4 | `engine/qbus_news_store.py:1044` (`commit`); `scripts/migrate_qbus_news.py:1` | `tests/test_qbus_news_store.py::test_first_commit_is_atomic_and_snapshot_is_security_indexed`; `tests/test_qbus_news_migration.py::test_migration_check_only_validates_without_creating_database` | **NOT ENROLLED**; frontier `:62` warns CI does not name new suites |
| 5 | `collectors/benzinga_news.py:93` (`BenzingaNewsClient`); `collectors/massive_benzinga_news.py:89`; `scripts/run_qbus_news.py:73` (`NewsIngestRunner`) | `tests/test_benzinga_news.py::test_delta_fetch_uses_updated_since_overlap_and_exhausts_news_and_removals`; `tests/test_massive_benzinga_news.py::test_fetch_pages_normalizes_results_and_marks_supplemental_not_correction_complete`; `tests/test_run_qbus_news.py::test_startup_catchup_precedes_connect_and_stream_commit_preserves_cursor`; `tests/test_qbus_news_task5_repairs.py::test_massive_repeated_next_url_stops_and_marks_explicit_gap` | **NOT ENROLLED** (plan names `tests/test_qbus_news_recovery.py` — **absent** on head; replaced by `test_qbus_news_task5_repairs.py`) |
| 6 | `app/ticker_news.py:345` (`ticker_news_snapshot`); `:445` (`ticker_news_stream`); `app/main.py:2287–2288` (router) | `tests/test_ticker_news_api.py::test_snapshot_is_authenticated_private_and_returns_cluster_rows`; `test_sse_cycle_rechecks_rights_and_emits_removal_before_stopping`; `test_production_app_mounts_all_private_ticker_news_routes` | **NOT ENROLLED** |
| 7 | (planned Terminal) `terminal/lib/newsContract.ts`, `terminal/lib/server/tickerNews.ts`, API routes — **no files** | (planned) `terminal/lib/__tests__/tickerNews*.test.ts` — **absent** | N/A — not on Macro PR |
| 8 | (planned) `terminal/components/news/*`, `terminal/e2e/ticker-news.spec.ts` — **absent** | N/A | N/A |
| 9–12 | `tests/test_ticker_news_end_to_end.py`, `scripts/verify_ticker_news.py`, evidence dirs — **absent** on `66ff33ac` (plan only) | N/A until Task 9 | N/A |

**Suggested local verification** (not executed on N0 lane — no `pytest` module on host; see Gaps):

```bash
python -m pytest -q tests/test_qbus_news_contract.py tests/test_qbus_news_reducer.py \
  tests/test_qbus_news_universe.py tests/test_qbus_news_cluster.py tests/test_qbus_news_store.py \
  tests/test_qbus_news_migration.py tests/test_qbus_news_store_api_reads.py \
  tests/test_qbus_news_store_clusters.py tests/test_qbus_news_task5_repairs.py \
  tests/test_benzinga_news.py tests/test_massive_benzinga_news.py tests/test_run_qbus_news.py \
  tests/test_ticker_news_api.py
```

Comment `5987919846` reported **93/93** at `80dec0ee` (Tasks 1–4 + incumbent qbus); head adds Task 5–6 suites — count not re-run here.

---

## Q3 — Provider modules, credentials, DO-NOT-CALL

**Env var names (values never read):**

- `scripts/run_qbus_news.py:230` — CLI `--token-env` default **`BENZINGA_API_KEY`**; read at `:237` via `os.environ.get(args.token_env, "")`.
- Collectors take **injected** `token` / `api_key` parameters (`collectors/benzinga_news.py:99`, `collectors/massive_benzinga_news.py:89`) — no direct `getenv` in collector modules on head.

**Client-served paths (PR head tree):**

- `git grep -n 'BENZINGA|MASSIVE|benzinga_api|API_KEY' 66ff33ac -- app templates` → **no matches** (558 paths under `app/` + `templates/` listed).
- `git ls-tree -r origin/main --name-only site/` — no provider key tokens; incidental `massive` in unrelated research HTML filenames only.

**DO-NOT-CALL (paid / upstream network) paths:**

| Path | Line | Why |
| --- | --- | --- |
| `collectors/benzinga_news.py` | HTTP methods on `BenzingaNewsClient` (e.g. delta fetch ~`:164`) | Live Benzinga REST |
| `collectors/benzinga_news.py` | `catch_up_once` `:392` | REST catch-up |
| `collectors/massive_benzinga_news.py` | page fetch using `apiKey` `:110` | Live Massive partner API |
| `scripts/run_qbus_news.py` | `NewsIngestRunner.run` `:156`, `_default_connect` `:60–62`, `stream_url` `:54` | WebSocket + orchestrated ingest |
| `scripts/run_qbus_news.py` | `main`/CLI run path (~`:230+`) | Starts foreground ingest service |

**Not DO-NOT-CALL:** `app/ticker_news.py` — read-only `NewsStore.open_readonly` (`:150`); no provider HTTP.

---

## Q4a — Server contract (N1 consumption)

On **`66ff33ac`**:

| Concern | Location |
| --- | --- |
| Revision normalization | `engine/qbus_news_contract.py:274` (`normalize_news`), schema `qbus.news_revision.v1` `:19` |
| Reduction / withdrawal | `engine/qbus_news_reducer.py` (consumed by store commit) |
| Read rights / redaction | `engine/qbus_news_store.py:93` (`NewsReadRights`); `_redact_story` ~`:490` |
| Snapshot shape | `NewsSnapshot` `:137`; API `ticker_news.snapshot.v1` `app/ticker_news.py:259` |
| Change / stream cursor | `ChangePage` `:161`; routes `app/ticker_news.py:310`, `:445` (SSE `text/event-stream`) |
| Story detail | `StoryDetail` `:169`; `app/ticker_news.py:286` |
| Correction / withdrawal semantics | Store commit + change rows `:1044`; reducer tests; SSE removal `tests/test_ticker_news_api.py::test_sse_cycle_rechecks_rights_and_emits_removal_before_stopping` |

**qbus writers / Parquet — UI must NOT switch:**

- Production `qbus.append_items` callers on head: `collectors/china_official_corpora.py:391`, `engine/china_news_intel.py:806`, `engine/communique_diff.py:408`, `engine/europe_news_intel.py:617`, `engine/financial_news.py:242`, `engine/news_vector.py:588`, `scripts/recrawl_official_tape.py:215`, definition `engine/qbus.py:246`.
- Comment `5987919846`: legacy **`data/qbus/items.parquet`** untouched; no production writer switch; migration defaults check-only.

---

## Q4b — Terminal readiness (TERMINAL_PIN)

**Incumbent route conventions:** `terminal/app/api/company-theme-context/[symbol]/route.ts:14–15` (`runtime = "nodejs"`, `dynamic = "force-dynamic"`); auth `:23–34` (Supabase `getUser`, E2E fixture bypass); rate limit `:45`; errors `:36–42`, `:58–70`; cache `:17` (`Cache-Control: no-store`); schema wrapper `:19–20`.

**Existing news surfaces:** `rg -l '(?i)(ticker.?news|/news/|newsContract)' terminal/app terminal/components terminal/lib terminal/e2e` on TERMINAL_PIN → **empty** (no dedicated ticker-news implementation).

**N1/N2 owned paths:** all **FREE** (no collision) at TERMINAL_PIN.

**Open Terminal PRs (`gh pr list -R mastermindx-market-intelligence/mastermind-terminal --state open --search news`):** `[]`.

---

## Q5 — Required N test-list coverage

Side: **SERVER** = Macro/qbus/API tests on `66ff33ac`; **UI** = Terminal component/e2e (not present).

| Case | Verdict | Side | Evidence |
| --- | --- | --- | --- |
| Late response (prior symbol) | NOT COVERED | UI | No `terminal/e2e/ticker-news.spec.ts`; no component tests |
| Snapshot / stream race | PARTIAL → **NOT COVERED** (no dedicated race test) | SERVER partial | SSE + snapshot tests exist separately; no explicit race test name on head |
| Duplicate delivery | COVERED | SERVER | `tests/test_qbus_news_reducer.py::test_exact_current_revision_is_duplicate_and_keeps_state`; `tests/test_qbus_news_store.py::test_exact_replay_advances_cursor_but_does_not_emit_duplicate_change` |
| Correction / withdrawal | COVERED | SERVER | Reducer + store withdrawal tests; `tests/test_ticker_news_api.py::test_sse_cycle_rechecks_rights_and_emits_removal_before_stopping` |
| Expired cursor / reconnect gap | NOT COVERED | SERVER/UI | Gap/catch-up in `tests/test_benzinga_news.py::test_full_page_at_page_budget_holds_cursor_and_marks_gap`; no “expired cursor” UI/API test by name |
| Aborted client | NOT COVERED | UI | Plan Task 7 requires; no Terminal tests |
| Source vs account rights | COVERED | SERVER | `tests/test_ticker_news_api.py::test_unknown_source_rights_fail_closed_before_store_open`; store `test_read_rights_filter_source_and_fields_without_changing_canonical_state` |
| Cache isolation | NOT COVERED | SERVER/UI | Private cache headers tested (`cache-control: private, no-store`); no multi-user cache isolation test |
| Unavailable store | COVERED | SERVER | `tests/test_ticker_news_api.py::test_store_unavailable_is_503_not_empty_200` |
| Quiet vs disconnected | PARTIAL | SERVER | `tests/test_ticker_news_api.py::test_live_source_with_no_ticker_rows_reports_quiet`; no explicit “disconnected market” test |
| Oversize payload | COVERED | SERVER | `tests/test_qbus_news_contract.py::test_oversized_title_and_body_are_rejected_with_stable_codes`; runner malformed frame tests |
| a11y (keyboard/focus/reduced motion) | NOT COVERED | UI | Plan Task 8; no Terminal surface |
| EN/ZH × dark/light | NOT COVERED | UI | Plan Task 8; Terminal shell dark-only evidence law applies to Terminal |

Adversarial **N-A…N-F** (Mastermind `05_ACCEPTANCE_AND_RED_TEAM.md`): partially reflected in reducer/cluster/store tests (N-A/B/C/D/F themes); **not** closed as full journey proofs without Tasks 7–9.

---

## Q6 — Release holds and prohibitions (verbatim sources)

From PR #8454 body (`pr8454.json`):

- “**DRAFT / DO NOT MERGE** until the exact candidate is reviewed and its applicable source/CI gates pass.”
- “Do not arm merge-on-green or auto-merge during implementation.”
- “Provider acquisition/redistribution rights, storage migration/activation, deployment and natural market proof remain separate.”
- “No paid feed, new subscription, production service or background worker has been started.”
- “The parent mission is **NOT COMPLETE** at plan publication.”

From comment `5985393200`:

- “**DRAFT / DO NOT MERGE remains.** No merge-on-green, auto-merge, production or predictive authority is added.”

From comment `5987919846`:

- “Migration utility defaults to check-only; `--write` … does not alter a production selector, rename/delete the Parquet, start a daemon, contact a provider, or grant rights.”
- “Remaining Task 4 acceptance: independent review, explicit CI enrollment/integration, real backup/restore/cutover proof and single-writer migration remain owed before production selection.”

From Mastermind package N / plan Tasks 9–12:

- “**Release:** Tasks 9–12 remain under source rights, single-writer migration/backup/restore, exact reviewed CI, incumbent deploy and natural-canary gates. Existing qbus writers and Parquet **cannot be switched** by the UI worker.”
- Task 10–12 checklist items (licensing, canary, acceptance) — all **RELEASE-GATED** on plan `:177–191`.

From frontier `IMPLEMENTATION_FRONTIER_2026-10-04.md`:

- “Keep Task 5 paid-provider activation rights-gated”
- “do not execute migration on production data during source qualification”

---

## Gaps and refusals

- **pytest not executed** on N0 lane host: `/usr/bin/python3: No module named pytest` (worktree at MAIN_PIN lacks PR-head test files).
- **CI enrollment:** none of the thirteen `tests/test_*qbus*news*` / `test_ticker_news_api.py` files appear in `.github/ci/legacy-jobs.yml` on `66ff33ac` (grep scope above).
- **Plan drift:** `tests/test_qbus_news_recovery.py` named in plan Task 5 — **missing** on head; use `tests/test_qbus_news_task5_repairs.py` instead.
- **Terminal news UI:** zero implementation at TERMINAL_PIN; no open Terminal PRs for news.
- **C0 named refs:** `git ls-remote origin | grep -c 80dec0ee` → 0; object still fetchable by SHA.
