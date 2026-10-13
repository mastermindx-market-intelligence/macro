# Mastermind AI China Freshness Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep China prices advancing through transient membership-source outages and prevent Mastermind AI from presenting a component date as China's last trading day.

**Architecture:** Reuse the committed China-search membership table as the collector's last-known-good universe, extend the existing China freshness module with one required-store postcondition at the end of `scripts.collect --group asia`, and make the existing market packet carry separate exchange/state/component clocks. No workflow edit or duplicate freshness plane is introduced.

**Tech Stack:** Python 3.12, pandas/parquet, pytest, existing `lib.cn_calendar`, existing Macro brain gateway.

**Spec:** `docs/superpowers/specs/2026-09-14-mastermind-ai-china-freshness-repair-design.md`

**Status:** `PROVEN_LIVE` — production accepted 2026-09-15. Delivered by Macro PR `#7156` (accepted head `81a01a8c681aeb4f81e16c65e1736bb86437e49b`; squash merge `4ec24e0f474522f5398b813ed14ae738a4361b77`). Canonical production receipt: PR comment `5689018917`.

## Global Constraints

- Work only in the isolated Warp worktree on a fresh `origin/main` base.
- Reuse `members.parquet`, `scripts/check_tushare_freshness.py`, and `lib.cn_calendar`.
- Write tests before implementation and preserve the intended failing evidence.
- Run every Asia adapter before enforcing the required core-store postcondition.
- Stage explicit paths only; never `git add -A`.

---

### Task 1: Recover the price collector through a Sina outage

**Files:**
- Modify: `collectors/china_universe.py`
- Test: `tests/test_china_universe_extras.py`

- [x] Add an incident replay that writes prior membership, makes Sina raise, returns fresh Yahoo closes through 2026-09-11, and proves the close store advances with a warning.
- [x] Prove the pre-fix path propagates the Sina exception.
- [x] Implement live-first, strict cached-second membership resolution.
- [x] Require at least 75% of configured universe width and preserve no-cache failure.

### Task 2: Enforce the existing Asia freshness contract

**Files:**
- Modify: `scripts/check_tushare_freshness.py`
- Modify: `scripts/collect.py`
- Test: `tests/test_tushare_freshness_tripwire.py`

- [x] Add red tests for the exact 2026-09-09 versus 2026-09-11 freeze, current data, ahead data, and a timezone-aware wide index.
- [x] Extend `_latest_date` to read wide index-based stores without shifting local dates through UTC.
- [x] Add `check_china_search_core()` using the canonical mainland calendar.
- [x] Add `_required_group_health("asia")` at the end of collection; leave every other group unchanged and preserve explicit `--skip-quality` / partial-run maintenance escapes.
- [x] Prove a stale core store returns exit 3 after all collection work, preventing the existing workflow's commit/build steps.

### Task 3: Separate exchange, state, and component clocks in chatbot grounding

**Files:**
- Modify: `engine/neuralweb/market_packet.py`
- Modify: `engine/neuralweb/brain_gateway.py`
- Test: `tests/test_market_packet.py`
- Test: `tests/test_brain_gateway.py`

- [x] Add the 9/9 component + 9/11 state incident replay with a pinned 2026-09-14 clock.
- [x] Normalize injected naive clocks to UTC.
- [x] Add typed `as_of_kind`, validated state/component dates, exchange-session date, and component-session relation.
- [x] Keep missing China artifacts explicit rather than minting a calendar-only regional row.
- [x] Make calendar failure render `exchange session unavailable` rather than a bare component stamp, and disclose `content vintage unknown` when content has no dated source.
- [x] Label non-China component dates instead of printing ambiguous bare dates.
- [x] Add the narrow gateway epistemic rule and exercise the actual `_grounding_digest` seam.

### Task 4: Verify, deliver, and prove production

**Files:**
- Modify only if required by an exact repository gate: CI ownership/wiring.
- Update durable company records only if the implementation reveals a reusable ruling beyond this incident.

- [x] Run red-then-green incident batteries.
- [x] Run complete affected pytest suites, `py_compile`, annotation, unrun-test, and contract-delta gates.
- [x] Obtain two independent reviews on the frozen diff and close all critical/important findings, including workflow propagation, Shanghai-midnight, undated-content, strict-cache, and raw-date-alias proofs.
- [x] Fetch/reconcile latest `origin/main`; rerun affected tests.
- [x] Commit explicit paths, push, open PR, arm `merge-on-green`, and own CI through conclusion.
- [x] Squash-merge only after binding checks conclude green.
- [x] Verify the VPS checkout/process has the merged code and `macro-api` restarted through the normal deploy gate.
- [x] Run/observe the next Asia close path and prove `china_search` reaches the expected mainland session.
- [x] Probe the live gateway and confirm a 9/9 component can no longer be described as the last trading day.

## Production acceptance — 2026-09-15

Closeout was adjudicated under Sol Skillpack `1.0.1` from protected Mastermind
`master` SHA `8e25bb32601ef5f40a689da6d6f24149e79e31fa`.

- Exact-head required workflows passed: `ci` run `34924268885` and `fences` run
  `34924268555`. PR `#7156` merged at `2026-09-15T20:24:45Z` as
  `4ec24e0f474522f5398b813ed14ae738a4361b77`.
- Production `/api/health` reports `commit=4ec24e0f47`; the running API therefore
  imported the accepted merge. The checkout later advanced to
  `142c8f6123b2a5da50e1ec95b6d0f7cb2167a009`; comparison from the merge through
  that checkout shows zero changes to the six material collector/calendar/packet/gateway paths.
- Canonical `asia-close` run `35021696056` completed successfully. Its binding
  freshness receipt placed `data/china_search/closes.parquet` at the expected
  mainland session `2026-09-15`; canonical collection commit
  `bbc5b9c9377fb1925afbc4a6bcc06702700981d4` contains that recovery.
- Fresh production inspection reports 1,277 close rows, latest session
  `2026-09-15`, both incident-era sessions `2026-09-10` and `2026-09-11` present,
  and `check_china_search_core()` return code `0`.
- Public Brain replays `204ceaad3b7d43e38e5ce1847603f40b` and
  `701ec273818340c4a55f482bde8b6cb7` were non-degraded. Both identified
  `2026-09-15` as the latest completed mainland session and explicitly treated
  `2026-09-09` only as a lagged component vintage, never as the market session.
- The repair extends the existing membership cache, close store, mainland
  calendar, freshness module, Asia collection path, market packet, and Brain
  gateway. It creates no second calendar, store, freshness/control/retry plane,
  deployment path, signal, rank, sizing, portfolio, or trading authority.

### Do not redo

Do not reopen or replace PR `#7156`, repeat the incident archaeology, fabricate
backfill rows, or create another freshness/calendar/store path. Resume repair work
only if a later canonical Asia run, production core-freshness check, or real Brain
replay falsifies this acceptance. Otherwise this capability remains `PROVEN_LIVE`
and returns to normal scheduled monitoring.

