# China A-Share Heatmap Live Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the embedded and standalone China A-share heatmaps consume a coherent, two-second, Tushare-first current-session overlay while preserving the canonical daily-close heatmap and degrading honestly.

**Architecture:** The current daily payload remains the sole structure/history authority. A resource-capped VPS service publishes one normalized `china_heatmap_live.v1` overlay from Tushare `rt_k`, with bounded Tencent fallback. The shared heatmap client validates one live snapshot owner and routes every 1D computation through it; deployment, public serving, and health reuse the existing live plane.

**Tech Stack:** Python 3.11+, pandas, requests, systemd, Caddy, vanilla JavaScript, Node test runner, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-27-china-heatmap-live-stream-design.md`

## Global Constraints

- Protected procedure pin: `mastermindx-market-intelligence/Mastermind@dcc4829a811d3f6e4fe8c16a103f813c3501f48e`, INDEX blob `94d1af402598894372858793a5b1931019c5fa77`, Skillpack `1.0.1`, bootstrap major `1`.
- The daily `site/marketdata/china_heatmap.json` remains the canonical membership, structure, sizing, history, and settled-session owner.
- Live data changes only the `1D` presentation; no Prophet, ranking, signal, evaluation, portfolio, or trading inputs change.
- Tushare `rt_k` is primary; Tencent is a bounded fallback. Yahoo/yshares are not live truth sources.
- `usable=true` requires at least `0.95` coverage and phase-aware source freshness.
- Missing live values remain null; never convert missing to zero or silently retain a stale daily return under a live label.
- Browser credentials and direct vendor calls are forbidden.
- Public artifacts are atomically replaced and served `no-store`.
- `templates/heatmap.js` and `site/heatmap.js` remain byte-identical.
- No new lifecycle, queue, replay, credential, monitoring, publication-root, or browser-WebSocket authority.

## Review Focus

- Lunch, closing-auction, and post-close clocks must remain usable without wall-clock false-stale behavior; Task 1 and Task 2 test each phase.
- A missing/rejected Tushare token must enter bounded Tencent fallback without a two-second request storm; Task 2 pins the fallback interval and last-good semantics.
- Low coverage, duplicate/foreign symbols, and partial chunk failure must never produce a partially live UI; Task 1 and Task 3 reject them atomically.
- A newly advanced daily baseline must invalidate an old live overlay until the producer and browser agree on `baseline_asof`; Task 3 and Task 4 pin the mismatch.
- Embedded scorecard, standalone view, expanded overlay, hover, sectors, breadth, and movers must all read one accepted 1D snapshot; Task 4 proves the shared value path and rejects residual China `live.js` hooks.

---

### Task 1: Live Contract and Source Normalization

**Files:**
- Create: `engine/china_heatmap_live.py`
- Create: `tests/test_china_heatmap_live.py`
- Modify: `collectors/tushare_client.py`
- Modify: `tests/test_tushare.py`

**Interfaces:**
- Produces: `BaselineHeatmap(asof: str, tickers: tuple[str, ...])`.
- Produces: `validate_baseline(payload: Mapping[str, Any]) -> BaselineHeatmap`.
- Produces: `parse_market_time(value: Any) -> datetime | None`.
- Produces: `normalize_tushare_rows(frame: pd.DataFrame, baseline: BaselineHeatmap) -> dict[str, dict[str, Any]]`.
- Produces: `normalize_tencent_quotes(raw: Mapping[str, Mapping[str, Any]], baseline: BaselineHeatmap) -> dict[str, dict[str, Any]]`.
- Produces: `build_live_payload(baseline: BaselineHeatmap, quotes: Mapping[str, Mapping[str, Any]], *, source: str | None, fallback: bool, phase: str, now: datetime) -> dict[str, Any]`.
- Produces: `validate_live_payload(payload: Mapping[str, Any], baseline: BaselineHeatmap, *, now: datetime) -> dict[str, Any]`.
- Extends: `tushare_client.query(..., _timeout: float | None = None)` while preserving the existing default timeout and return contract.
- Consumed by Task 2 producer and Task 3 browser contract fixtures.

- [ ] **Step 1: Write failing baseline and Tushare-normalization tests**

Add tests that assert:

```python
baseline = validate_baseline(BASELINE_FIXTURE)
assert baseline.asof == "2026-09-24"
assert baseline.tickers == ("600519.SS", "000001.SZ")

quotes = normalize_tushare_rows(TUSHARE_FRAME, baseline)
assert quotes["600519.SS"]["price"] == 1412.8
assert quotes["600519.SS"]["prevClose"] == 1398.0
assert quotes["600519.SS"]["changePct"] == pytest.approx((1412.8 / 1398.0 - 1) * 100)
assert quotes["600519.SS"]["ts"] == EXPECTED_UTC_MS
assert "600000.SS" not in quotes  # not in baseline
```

Also pin `.SH -> .SS`, malformed timestamps, non-finite prices, duplicate normalized tickers, and no-trade placeholders.

- [ ] **Step 2: Run the new tests and verify RED**

Run: `python3 -m pytest -q tests/test_china_heatmap_live.py`
Expected: import failure because `engine.china_heatmap_live` does not exist.

- [ ] **Step 3: Implement the baseline and source-normalization contract**

Create the exact interfaces above. Use `engine.prophet_live.cn_clock.expected_latest_quote_time` for freshness, `MIN_COVERAGE = 0.95`, `MAX_SOURCE_LAG_SECONDS = 45.0`, and `SCHEMA = "china_heatmap_live.v1"`. Recompute percentage from price/previous close. Keep only canonical baseline symbols.

- [ ] **Step 4: Write failing payload-coherence and phase tests**

Test morning, lunch, afternoon, closing auction, post-close, holiday/weekend, low coverage, count mismatch, breadth mismatch, future source clock, wrong baseline, foreign quote key, and heartbeat advancement without source-clock advancement.

- [ ] **Step 5: Run the phase tests and verify RED**

Run: `python3 -m pytest -q tests/test_china_heatmap_live.py`
Expected: failures in the not-yet-implemented payload builder/validator.

- [ ] **Step 6: Implement payload building and validation**

`build_live_payload` must produce the spec's allowlisted contract, compute breadth over accepted quotes, and set `usable` only from coverage + phase-aware source clock. `validate_live_payload` must independently recompute all accounting.

- [ ] **Step 7: Write and run the Tushare timeout test RED**

Add a test that monkeypatches `requests.post` and calls `query("rt_k", _timeout=5.0, _retries=0, ...)`; assert the request receives `timeout=5.0`. Run:

`python3 -m pytest -q tests/test_tushare.py -k timeout`

Expected: failure because `_timeout` is not accepted.

- [ ] **Step 8: Add the optional timeout and run Task 1 tests GREEN**

Run:

`python3 -m pytest -q tests/test_china_heatmap_live.py tests/test_tushare.py`

Expected: all selected tests pass.

- [ ] **Step 9: Commit Task 1**

```bash
git add engine/china_heatmap_live.py collectors/tushare_client.py tests/test_china_heatmap_live.py tests/test_tushare.py
git commit -m "feat(china): define live heatmap contract"
```

---

### Task 2: Tushare-First Producer, Tencent Fallback, and Atomic Loop

**Files:**
- Create: `scripts/build_china_heatmap_live.py`
- Create: `tests/test_china_heatmap_live_producer.py`
- Modify: `engine/live_quotes.py`
- Modify: `tests/test_live_quotes.py`

**Interfaces:**
- Consumes Task 1 `BaselineHeatmap`, normalizers, builder, and validator.
- Produces: `fetch_tushare_snapshot(baseline: BaselineHeatmap) -> dict[str, dict[str, Any]] | None`.
- Extends: `fetch_tencent_cn(symbols, *, batch_size=_TENCENT_BATCH, max_workers=1, timeout=12, retries=2)` with defaults preserving current callers.
- Produces: `ChinaHeatmapLiveProducer.step(now: datetime | None = None) -> dict[str, Any]`.
- Produces: `ChinaHeatmapLiveProducer.run_forever() -> None`.
- Produces CLI: `python -m scripts.build_china_heatmap_live [--once|--loop] --base PATH --out PATH --interval 2 --fallback-interval 15 --heartbeat-interval 30`.
- Consumed by Task 5 systemd service.

- [ ] **Step 1: Write failing Tushare request and provider tests**

Pin one `rt_k` call using `ts_code="6*.SH,3*.SZ,0*.SZ"`, an explicit field list including `trade_time`, `_timeout=5.0`, `_retries=0`, and `_return_empty=True`. Assert absent token/None response is a miss, not an empty current market.

- [ ] **Step 2: Run producer tests and verify RED**

Run: `python3 -m pytest -q tests/test_china_heatmap_live_producer.py`
Expected: import failure because the script does not exist.

- [ ] **Step 3: Implement one-shot Tushare production**

Implement baseline reload, Tushare fetch, Task 1 normalization, payload build/validate, and atomic temp-file + fsync + rename with mode `0644`. A one-shot failure returns non-zero and never replaces an accepted output.

- [ ] **Step 4: Write failing bounded Tencent fallback tests**

Test configurable batch size/concurrency while preserving default serial behavior. Pin that a Tushare miss runs Tencent no more often than once per `fallback_interval`, and that a failed fallback keeps the original `source_observed_at`.

- [ ] **Step 5: Run fallback tests and verify RED**

Run:

`python3 -m pytest -q tests/test_live_quotes.py -k tencent tests/test_china_heatmap_live_producer.py -k fallback`

Expected: failures because optional concurrency and producer fallback state do not exist.

- [ ] **Step 6: Implement bounded Tencent fallback and last-good state**

Use parallel batches only when `max_workers > 1`; default behavior remains unchanged. The producer may call fallback at most every 15 seconds, may retain a previous source only while Task 1 freshness accepts it, and may never restamp a stale source as fresh.

- [ ] **Step 7: Write failing session-loop tests**

Use injected clock, sleep, and fetchers to prove:

- two-second fetch cadence in `morning`/`afternoon`;
- no vendor calls during `session_break`, `pre_open`, `weekend`, or `holiday`;
- 30-second phase heartbeats;
- graceful SIGTERM/KeyboardInterrupt exit;
- baseline reload when the base file changes;
- output remains valid during a transient source exception.

- [ ] **Step 8: Implement the loop and run Task 2 tests GREEN**

Run:

`python3 -m pytest -q tests/test_china_heatmap_live.py tests/test_china_heatmap_live_producer.py tests/test_live_quotes.py`

Expected: all selected tests pass.

- [ ] **Step 9: Commit Task 2**

```bash
git add scripts/build_china_heatmap_live.py engine/live_quotes.py tests/test_china_heatmap_live_producer.py tests/test_live_quotes.py
git commit -m "feat(china): publish live heatmap overlay"
```

---

### Task 3: Browser Live Contract and Shared Refresh Owner

**Files:**
- Modify: `templates/heatmap.js`
- Modify: `site/heatmap.js`
- Create: `tests/china_heatmap_live_refresh_harness.cjs`
- Create: `tests/test_china_heatmap_live_refresh.cjs`

**Interfaces:**
- Consumes `china_heatmap_live.v1` from Tasks 1–2.
- Produces internal functions `validateChinaLiveSnapshot(payload, base, nowMs)`, `commitChinaLiveSnapshot(baseUrl, payload)`, `startChinaLiveRefresh(base)`, `chinaLiveValue(data, tile, tf)`, and `chinaLiveMeta(data)`.
- Produces event `hm-live-refresh` with `{url}` only after an accepted atomic revision.
- Consumed by Task 4 rendering.

- [ ] **Step 1: Write failing browser contract tests**

Pin valid adoption, wrong schema/market/baseline, malformed date, future heartbeat, stale heartbeat, low coverage, count/breadth mismatch, foreign/duplicate quote identity, inconsistent percentage, and source-clock regression.

- [ ] **Step 2: Run and verify RED**

Run: `node --test tests/test_china_heatmap_live_refresh.cjs`
Expected: harness boundary/functions missing.

- [ ] **Step 3: Implement validation and atomic state replacement**

Store accepted live state outside the canonical baseline object, keyed by base URL. Preserve the accepted object through transient failures. Never attach server-controlled private keys to baseline data.

- [ ] **Step 4: Write failing refresher ownership tests**

Pin one owner per URL, two-second running cadence, 30-second break/closed cadence, visible-tab gating, overlap prevention, fetch+JSON timeout, late-response refusal, retry after failure, and shared state across overlapping mounts.

- [ ] **Step 5: Run and verify RED**

Run: `node --test tests/test_china_heatmap_live_refresh.cjs`
Expected: refresher tests fail before implementation.

- [ ] **Step 6: Implement the refresher and value helper**

Use recursive `setTimeout`, not fixed overlapping intervals. Add cache-busting query data only to the live overlay request. `chinaLiveValue` returns live 1D, null for uncovered names while live is active, and baseline values otherwise; non-1D is always baseline.

- [ ] **Step 7: Copy the template and run Task 3 tests GREEN**

Run:

```bash
cp templates/heatmap.js site/heatmap.js
node --test tests/test_china_heatmap_live_refresh.cjs tests/test_china_heatmap_refresh.cjs
cmp -s templates/heatmap.js site/heatmap.js
```

Expected: all tests pass and `cmp` exits zero.

- [ ] **Step 8: Commit Task 3**

```bash
git add templates/heatmap.js site/heatmap.js tests/china_heatmap_live_refresh_harness.cjs tests/test_china_heatmap_live_refresh.cjs
git commit -m "feat(china): consume shared live heatmap overlay"
```

---

### Task 4: Complete Renderer Coherence and Honest Session Labels

**Files:**
- Modify: `templates/heatmap.js`
- Modify: `site/heatmap.js`
- Create: `tests/test_china_heatmap_live_render.cjs`
- Modify: `tests/test_china_heatmap_observations_ui.cjs`
- Modify: `tests/test_heatmap_label_ink.py`

**Interfaces:**
- Consumes Task 3 `chinaLiveValue` and `chinaLiveMeta`.
- Produces one coherent live 1D read across full view, embedded scorecard, expanded overlay, hover card, sector aggregates, breadth, median, movers, and market pulse.
- Removes China from the legacy `live.js` hidden-`.nb-chg` overlay while preserving HK/Canada behavior.

- [ ] **Step 1: Write failing renderer tests**

Assert a single accepted live fixture changes:

- full-map tile colour and visible percent;
- scorecard tile colour and visible percent;
- sector aggregate;
- breadth/median;
- gainers/losers;
- hover return;
- source/status label.

Assert `1W` remains the baseline and a missing live ticker is null/neutral.

- [ ] **Step 2: Add source-level guard tests and verify RED**

Pin that China is absent from `_LIVE_MKT`, that critical renderer functions call `chinaLiveValue`, and that no China-specific MutationObserver dependency remains. Run:

`node --test tests/test_china_heatmap_live_render.cjs`

Expected: failures because direct `tile.perf` reads and the legacy China hook remain.

- [ ] **Step 3: Route every live-sensitive 1D read through the shared helper**

Update central aggregators first (`medianPc`, `sectorAgg`, `breadth`), then tile labels, lists, dashboard summary, mover rows, hover/detail, scorecard, and source labels. Prefer the live payload's breadth accounting while active; never use stale daily `board_breadth` under a live label.

- [ ] **Step 4: Implement bilingual phase/fallback copy**

Distinct copy/dot states are required for live morning/afternoon, lunch break, closing auction, closed, degraded, and daily fallback. Include source time in Asia/Shanghai and `resolved/requested` coverage.

- [ ] **Step 5: Copy paired JS and run Task 4 tests GREEN**

Run:

```bash
cp templates/heatmap.js site/heatmap.js
node --test \
  tests/test_china_heatmap_live_render.cjs \
  tests/test_china_heatmap_live_refresh.cjs \
  tests/test_china_heatmap_refresh.cjs \
  tests/test_china_heatmap_observation_refresh.cjs \
  tests/test_china_heatmap_observations_ui.cjs
python3 -m pytest -q tests/test_heatmap_label_ink.py tests/test_china_heatmap_gate.py
cmp -s templates/heatmap.js site/heatmap.js
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit Task 4**

```bash
git add templates/heatmap.js site/heatmap.js tests/test_china_heatmap_live_render.cjs tests/test_china_heatmap_observations_ui.cjs tests/test_heatmap_label_ink.py
git commit -m "fix(china): make live heatmap views coherent"
```

---

### Task 5: Public Serving, Systemd Ownership, and Secret Delivery

**Files:**
- Create: `app/deploy/macro-live-china-heatmap.service`
- Create: `.github/workflows/deploy-china-heatmap-live.yml`
- Create: `tests/test_china_heatmap_live_deploy.py`
- Modify: `app/deploy/live-setup.sh`
- Modify: `app/deploy/update.sh`
- Modify: `app/deploy/Caddyfile`
- Modify: `config/site_access.yml`
- Modify: `docs/ops/site-access.md`
- Modify public-inventory tests discovered by the focused boundary suite, including `tests/test_unsubscribe_page.py` when required.

**Interfaces:**
- Consumes Task 2 CLI.
- Produces systemd unit `macro-live-china-heatmap.service`.
- Produces public route `/live/china_heatmap.json` with `Cache-Control: no-store`.
- Produces operator-triggered secret delivery using only `VPS_DEPLOY_KEY` and `TUSHARE_TOKEN`.

- [ ] **Step 1: Write failing deployment contract tests**

Pin service type/command/restart/resource/security settings, setup install+enable, update restart path allowlist, Caddy public route/no-store behavior, site-access classification, and exact public-inventory parity.

- [ ] **Step 2: Run and verify RED**

Run:

`python3 -m pytest -q tests/test_china_heatmap_live_deploy.py tests/test_site_access_boundary.py tests/test_unsubscribe_page.py`

Expected: missing unit/workflow/route failures.

- [ ] **Step 3: Implement systemd, setup, update, and public route**

The update block restarts the persistent service only when the unit, producer, engine contract, Tushare client, Tencent adapter, or heatmap JS changes. Do not restart unrelated live services.

- [ ] **Step 4: Write failing workflow hygiene tests**

Assert `workflow_dispatch`, minimal read permission, non-bare self-hosted runner label, no secret echo/argument, stdin delivery, mode `0600`, replacement of only `TUSHARE_TOKEN`, restart of only the China heatmap service, and post-restart artifact/public-header checks.

- [ ] **Step 5: Implement the dedicated workflow**

Do not modify the broad OAuth/API secret workflow. The new workflow fails loudly when either required secret is absent.

- [ ] **Step 6: Run Task 5 tests GREEN**

Run:

```bash
python3 -m pytest -q \
  tests/test_china_heatmap_live_deploy.py \
  tests/test_site_access_boundary.py \
  tests/test_unsubscribe_page.py \
  tests/test_close_pass_lane.py \
  tests/test_entry_radar_w4_lane.py
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 5**

```bash
git add app/deploy/macro-live-china-heatmap.service app/deploy/live-setup.sh app/deploy/update.sh app/deploy/Caddyfile config/site_access.yml docs/ops/site-access.md .github/workflows/deploy-china-heatmap-live.yml tests/test_china_heatmap_live_deploy.py tests/test_site_access_boundary.py tests/test_unsubscribe_page.py tests/test_close_pass_lane.py tests/test_entry_radar_w4_lane.py
git commit -m "ops(china): own live heatmap publication"
```

---

### Task 6: Existing Health Plane and CI Enrollment

**Files:**
- Modify: `scripts/check_vps_live_health.py`
- Modify: `.github/workflows/vps-live-heartbeat.yml`
- Modify: `.github/ci/legacy-jobs.yml`
- Modify: `config/dag.yml` only if the repository's conformance checker requires the new invoked module.
- Create or modify: `tests/test_china_heatmap_live_health.py`
- Modify: `tests/test_vps_live_orchestration.py`
- Modify: `tests/test_ci_pack.py` only when required by CI enrollment.

**Interfaces:**
- Consumes public `china_heatmap_live.v1` and the served baseline.
- Produces phase-aware health findings through the existing VPS heartbeat/checker; no second watcher or status owner.
- Produces CI execution of the new Python/JS/deploy suites.

- [ ] **Step 1: Write failing phase-aware health tests**

Pin active-session stale heartbeat, low coverage, unusable state, source-clock lag, wrong baseline, lunch acceptance, closed acceptance, missing artifact outside session, and malformed payload.

- [ ] **Step 2: Run and verify RED**

Run: `python3 -m pytest -q tests/test_china_heatmap_live_health.py tests/test_vps_live_orchestration.py`
Expected: missing health clause/finding failures.

- [ ] **Step 3: Extend the existing health owner**

Use the same HTTP/artifact inventory and evaluation result. During active phases, missing/unusable is a failure; during break/closed, apply the phase rules from the spec. Add no new scheduler.

- [ ] **Step 4: Write and run failing CI-enrollment tests**

Pin that Python contract/producer/deploy/health and Node refresh/render suites are executed in an existing relevant CI job with an exclusive changed-path scope.

- [ ] **Step 5: Enroll the suites and run Task 6 tests GREEN**

Run:

```bash
python3 -m pytest -q tests/test_china_heatmap_live_health.py tests/test_vps_live_orchestration.py tests/test_ci_pack.py
python3 scripts/check_dag_conformance.py
```

Expected: all selected tests pass and DAG conformance reports no introduced drift.

- [ ] **Step 6: Commit Task 6**

```bash
git add scripts/check_vps_live_health.py .github/workflows/vps-live-heartbeat.yml .github/ci/legacy-jobs.yml config/dag.yml tests/test_china_heatmap_live_health.py tests/test_vps_live_orchestration.py tests/test_ci_pack.py
git commit -m "test(china): monitor live heatmap freshness"
```

---

### Task 7: Integrated Qualification, PR, Deployment, and Natural RTH Proof

**Files:**
- Modify only files required by discriminating failures found during qualification.
- Create evidence under the repository's existing evidence owner/path only when current source law requires it; do not create a new evidence registry.

**Interfaces:**
- Consumes all prior tasks.
- Produces one exact branch head, one PR, hosted CI, review disposition, merged deployment, secret workflow run, and natural-session production receipts.

- [ ] **Step 1: Run the full focused local matrix**

```bash
python3 -m pytest -q \
  tests/test_china_heatmap_live.py \
  tests/test_china_heatmap_live_producer.py \
  tests/test_china_heatmap_live_deploy.py \
  tests/test_china_heatmap_live_health.py \
  tests/test_tushare.py \
  tests/test_live_quotes.py \
  tests/test_market_heatmap.py \
  tests/test_china_heatmap_gate.py \
  tests/test_china_heatmap_observations.py \
  tests/test_vps_live_orchestration.py \
  tests/test_site_access_boundary.py \
  tests/test_unsubscribe_page.py \
  tests/test_ci_pack.py
node --test \
  tests/test_china_heatmap_live_refresh.cjs \
  tests/test_china_heatmap_live_render.cjs \
  tests/test_china_heatmap_refresh.cjs \
  tests/test_china_heatmap_observation_refresh.cjs \
  tests/test_china_heatmap_observations_ui.cjs
cmp -s templates/heatmap.js site/heatmap.js
git diff --check
```

Expected: all selected tests pass.

- [ ] **Step 2: Run contract/fence checks required by changed paths**

Run the repository's CI planner/fence commands for the exact diff. Any discovered command must be recorded with its actual output; do not substitute a guessed full-suite claim.

- [ ] **Step 3: Perform whole-branch review**

Use the executing-plans review package from merge base `808432ecfb2824b55ec37dcbf6b448e5fd31411a` to the candidate head. Grade findings by user effect. Critical/Important findings receive one TDD fix pass; minors are recorded without opportunistic scope expansion.

- [ ] **Step 4: Push one branch and open one PR**

The PR body must state the exact baseline/live authority split, contract, source hierarchy, safety behavior, tests, deployment gate, and capability state `BUILT_NOT_PROVEN`. Reconcile and supersede the stale overlapping intent in PR #7193 without discarding its settled-close protection.

- [ ] **Step 5: Consume hosted CI and independent review**

Do not merge on local proof. Preserve exact head identity and wait for the binding hosted checks/review. Repair only evidenced failures, update the head once per coherent repair, and invalidate only affected proof.

- [ ] **Step 6: Merge through the protected repository path**

Only after required CI/review passes. Green CI is not production acceptance.

- [ ] **Step 7: Dispatch the dedicated secret/install workflow**

Verify the workflow run itself succeeded, the service is active, and the artifact passes its schema/coverage/header checks. An absent secret is an exact operator gate, not permission to paste a token into chat or a command.

- [ ] **Step 8: Capture natural mainland-session proof**

During `morning` or `afternoon`, verify two successive source ticks and both real browser journeys. Confirm one live 1D value against the public artifact, coherent breadth/sector/mover updates, unchanged 1W, no console error, and honest fallback after a controlled service/source interruption only when the production runbook permits it.

- [ ] **Step 9: Record final capability state**

`PROVEN_LIVE` requires the real-path receipts above. Otherwise leave `BUILT_NOT_PROVEN` with the exact remaining natural-session or human gate. Close/supersede PR #7193 only after the new carrier preserves its settled-close guarantees and the repository state is reconciled.
