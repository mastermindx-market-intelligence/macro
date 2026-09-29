# NYSE Breadth & Participation Command Center — Implementation Plan

> Execute in the dedicated worktree `claude/nyse-breadth-command-center-20260929-sol` from Macro base `942956ea69f6cd118a153ff3eceb58bfe4813f60`. Follow strict red-green-refactor. Keep `live.breadth.v1` frozen.

## Task 1 — Pin source law and approved design

**Files**

- Create: `docs/superpowers/specs/2026-09-29-nyse-breadth-command-center-design.md`
- Create: `docs/superpowers/plans/2026-09-29-nyse-breadth-command-center.md`

**Verification**

- Scan both files for `TBD`, `TODO`, `FIXME`, contradictory authority, duplicate planes, and unstated price/session basis.
- Confirm the Macro base SHA, Mastermind law SHA, and skill-index blob.
- Commit an atomic documentation checkpoint.

## Task 2 — Pure XNYS universe and breadth engine

**Files**

- Create: `engine/exchange_breadth.py`
- Create: `tests/test_exchange_breadth.py`

**Red tests first**

1. Massive roster normalization accepts XNYS rows and splits exactly `CS|ADRC` from all issues.
2. Identity resolution precedence is canonical security ID, share-class FIGI, composite FIGI, then unresolved.
3. Membership interval update compresses consecutive sessions, opens/closes changes, and never bridges a missing session.
4. Entity-history assembly keeps a ticker rename continuous and separates ticker reuse.
5. Forward, reverse, and stock-dividend split events restate only pre-event raw bars and never use events after the observation session.
6. An unmatched split-like seam excludes the affected entity instead of manufacturing a new low.
7. NH/NL uses the prior 252 split-normalized closes and excludes the current session from thresholds.
8. Young issues are excluded from seasoned denominators.
9. Both-extremes, missing prices, unchanged names, moving-average percentages, normalized values, and zero denominators are correct.
10. Descriptive state derivation is causal and carries visible reasons.

**Implementation**

- Add typed constants and pure normalization, identity, interval, history, aggregate, context, and state helpers.
- Keep the core free of filesystem and network I/O.
- Return finite JSON-compatible primitives at the view boundary.

**Verification**

```bash
python -m pytest tests/test_exchange_breadth.py -q
```

**Commit**

`feat(breadth): add identity-safe XNYS breadth core`

## Task 3 — Massive point-in-time roster source and nightly collector

**Files**

- Create: `collectors/exchange_breadth.py`
- Create: `tests/test_exchange_breadth_collector.py`
- Modify: `scripts/collect.py`
- Modify: `config.yml`
- Modify: `config/dataset_registry.yml`
- Modify: `.gitignore` only if a transient artifact needs an explicit boundary.

**Red tests first**

1. Reference request uses `market=stocks`, `exchange=XNYS`, requested `date`, `active=true`, and `limit=1000`.
2. Split request uses `/stocks/v1/splits`, an execution-date bound, all adjustment types, and a bounded page cap.
3. Roster and split pagination propagate the API key without logging it.
4. Non-OK, duplicate, wrong-exchange, invalid-ratio, empty, truncated, and low-row-floor responses refuse.
5. Existing accepted membership, split, and summary files remain byte-identical after failure.
6. The latest completed XNYS session comes from the Massive manifest plus canonical calendar, not a wall-clock guess.
7. A partial or stale local Massive store refuses before writes.
8. An accepted fetch updates roster intervals and split observations, computes both frames, and writes a receipt with rules, basis, counts, unresolved examples, and source clock.
9. Registry order places `exchange_breadth` after `massive_stock_day` in the nightly owner lane.

**Implementation**

- Build mockable paginated roster and split fetchers using the existing key/config conventions and secret-redaction law.
- Load incumbent alias data through `VendorAliasTable`.
- Resolve the Massive store through the established config/R2 pattern.
- Write interval, state, receipt, and aggregate artifacts atomically only after full validation.
- Return `nyse_operating` and `nyse_all_issues` frames through the adapter runner.

**Verification**

```bash
python -m pytest tests/test_exchange_breadth_collector.py tests/test_collect.py -q
```

**Commit**

`feat(breadth): collect point-in-time NYSE participation`

## Task 4 — Resumable recent/full historical backfill

**Files**

- Create: `scripts/backfill_exchange_breadth.py`
- Create: `tests/test_exchange_breadth_backfill.py`
- Modify: `.github/workflows/backfill.yml`

**Red tests first**

1. Session enumeration uses the reviewed XNYS calendar.
2. Default recent seed targets at least 270 completed sessions.
3. Completed sessions are skipped; failed or partial sessions remain pending.
4. Checkpoint writes only after roster and price evidence reconcile.
5. Bounded runs stop cleanly and report remaining sessions.
6. Re-run is idempotent.
7. Older-than-R2 dates use a mockable grouped-daily REST fetch with `adjusted=false`, then apply the same dated split algorithm.
8. Recent R2 and grouped-daily paths produce identical metrics on a split fixture.

**Implementation**

- Add `--start`, `--end`, `--recent-sessions`, `--max-sessions`, `--resume`, and `--dry-run`.
- Reuse collector/core functions rather than duplicating calculation.
- Add a manually dispatchable workflow lane with R2 restore, credentials, bounded execution, artifact audit, and existing-owner publication behavior.

**Verification**

```bash
python -m pytest tests/test_exchange_breadth_backfill.py -q
```

**Commit**

`feat(breadth): add resumable NYSE breadth backfill`

## Task 5 — Pure command-center composer

**Files**

- Create: `engine/breadth_command_center.py`
- Create: `tests/test_breadth_command_center.py`

**Red tests first**

1. Compose XNYS, S&P 500/400/600/1500, Russell 2000, and available sector evidence.
2. Preserve absent/partial universes without manufacturing zeros.
3. Compute transparent confirmation numerator/denominator and reasons.
4. Distinguish broadening, narrowing, washout, recovery, fragmentation, and mixed.
5. Never emit buy, sell, de-risk, probability, or forecast language.
6. Carry basis, roster version, source clock, coverage, and authority disclosure.

**Implementation**

- Keep the composer pure: dictionaries/series in, JSON-safe view model out.
- Avoid an opaque score; expose component evidence and counts.

**Verification**

```bash
python -m pytest tests/test_breadth_command_center.py -q
```

**Commit**

`feat(breadth): compose cross-universe breadth command center`

## Task 6 — Build-site integration and shared surface

**Files**

- Create: `templates/_breadth_command_center.html.j2`
- Modify: `scripts/build_site.py`
- Modify: `templates/dashboard.html.j2`
- Create: `tests/test_breadth_command_center_render.py`
- Modify exact render fixtures only when required by the intended surface.

**Red tests first**

1. VM loader reads accepted exchange frames and degrades to unavailable.
2. Macro Markets face contains the compact XNYS/S&P/diffusion/state strip.
3. `#dlg-markets` starts with Breadth & Participation before Index Health.
4. US Stocks preserves the incumbent S&P 1500 board and exposes the shared command-center link/summary.
5. English/Chinese, coverage, basis, source clock, and context-only copy are present.
6. No `official NYSE`, forecast, buy/sell, or Hindenburg language appears.
7. Missing data renders an honest accruing state.

**Implementation**

- Add one `breadth_command` VM key.
- Include one shared partial in Macro compact/detail contexts and the US Stocks context.
- Add only scoped CSS; preserve existing dialog/focus infrastructure.

**Verification**

```bash
python -m pytest tests/test_breadth_command_center_render.py tests/test_build_site.py -q
python -m scripts.render_macro_fast
```

**Commit**

`feat(dashboard): surface NYSE breadth command center`

## Task 7 — Separate live XNYS sidecar on the existing snapshot

**Files**

- Create: `engine/live_exchange_breadth.py`
- Create: `tests/test_live_exchange_breadth.py`
- Modify: `scripts/live_breadth_poller.py`
- Modify: `templates/live.js`
- Modify: `site/live.js`
- Modify: `docs/live_breadth_runbook.md`
- Modify deployment/health contracts only where required by the additive sidecar.

**Red tests first**

1. Exact `live.exchange_breadth.v1` schema.
2. Existing `live.breadth.v1` exact-shape tests remain unchanged and green.
3. One `fetch_full_market` invocation feeds both builders.
4. Threshold store is identity and roster-version bound.
5. Missing source clock, stale roster, incomplete universes, low price coverage, low seasoned coverage, and closed session fail closed.
6. Sidecar write is atomic and independent of the v1 write.
7. Browser patches only when `usable === true`; otherwise the baked VM remains.
8. Payload is finite JSON and carries source/coverage disclosure.

**Implementation**

- Add an exchange threshold store backed by accepted interval/history artifacts.
- Refactor the one-cycle shell to share the snapshot result without changing the incumbent v1 payload.
- Add the public path and semantic health disclosure.

**Verification**

```bash
python -m pytest tests/test_live_breadth.py tests/test_live_breadth_js_contract.py tests/test_live_exchange_breadth.py -q
```

**Commit**

`feat(breadth): add live NYSE breadth sidecar`

## Task 8 — Research study harness

**Files**

- Create: `scripts/research/nyse_breadth_study.py`
- Create: `tests/test_nyse_breadth_study.py`
- Create: `research/NYSE_BREADTH_STUDY_PROTOCOL_2026-09-29.md`

**Red tests first**

1. Event features use only data available through the observation session.
2. Cooldown clusters adjacent fires.
3. Forward outcomes use future bars only after the event date and report censoring.
4. Conditional baselines match trend, volatility, and regime without leakage.
5. Output includes sample size and refuses unsupported inference.
6. Hindenburg/Titanic names and authority remain blocked.

**Implementation**

- Produce reproducible JSON/Markdown research artifacts.
- Do not wire results into production scoring.

**Verification**

```bash
python -m pytest tests/test_nyse_breadth_study.py -q
```

**Commit**

`research(breadth): add PIT NYSE breadth study harness`

## Task 9 — Verification, visual proof, review, and integration

**Targeted verification**

```bash
python -m pytest \
  tests/test_exchange_breadth.py \
  tests/test_exchange_breadth_collector.py \
  tests/test_exchange_breadth_backfill.py \
  tests/test_breadth_command_center.py \
  tests/test_breadth_command_center_render.py \
  tests/test_live_exchange_breadth.py \
  tests/test_live_breadth.py \
  tests/test_live_breadth_js_contract.py \
  tests/test_nyse_breadth_study.py -q
python -m pytest tests/test_ci_pack.py -q
python -m compileall engine collectors scripts
```

Run the relevant CI pack, build Macro and US Stocks, and perform browser verification at desktop/mobile in English/Chinese and dark/light, for healthy and unavailable fixtures. Confirm no console errors and correct keyboard/focus behavior.

Run a bounded real-path data probe when credentials and the canonical R2 store are present. The receipt must show XNYS-only membership, both cohorts, nonzero seasoned/coverage counts, prior-252 semantics, at least one reconciled real split case, and the same source session as the rendered page. If a production control is absent, persist the exact gate and do not claim live proof.

Read and apply `verification-before-completion`, request independent code review, address findings with tests, push the branch, create a PR, observe CI, and merge only after required checks and real-path evidence. Read back `origin/main` and the production/public artifacts after merge and deployment.
