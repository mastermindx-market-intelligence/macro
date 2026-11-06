# Earnings Wire Incremental Recovery Implementation Plan

> Execute in the locked worktree `/Users/chriswong/.mastermind/source-workspaces/earnings-wire-incremental-recovery-20260914-sol` on branch `sol/earnings-wire-incremental-recovery-20260914`.

**Goal:** Restore the public Earnings Wire beyond 2026-07-29 using bounded incremental hydration over the existing canonical story-packet and transcript planes.

**Architecture:** Migrate the existing redacted route catalog to v2 with a preserved forward-selection floor and bounded deferred packet identities. Compare its accepted immutable story generation to the current generation, then hydrate admitted routes, every correction, and only completed newly added calls on or after the preserved floor. Persist only canonical `TICKER/TRANSCRIPT_ID` identities for scheduled/future dates, recheck them on otherwise-no-change refreshes, refuse an all-held empty publication, and ship the dual-schema browser consumer behind a content-hash URL. Keep all existing evidence admission, rendering, private publication, and cleanup contracts.

**Tech:** Python 3.12, pytest, requests, immutable JSON manifests, GitHub Actions, static Jinja publication.

## Task 1: Pin the failing contract with tests

**Files:**
- Modify: `tests/test_earnings_public_wire.py`
- Modify: `tests/test_earnings_wire_freshness.py` only if the report contract changes

Add fixtures that can produce multiple packet entries, prior/current generations, a Terminal date index, and a recording fetcher. Add red tests for:

1. v1 route state migrates to v2 and derives `forward_selection_floor_date` from the newest published event.
2. v2 state preserves an existing floor even after newer events publish.
3. A current manifest over 10,000 entries does not trigger full hydration when prior state exists.
4. Selection fetches all admitted keys, all changed keys, and newly added keys on or after the floor.
5. Selection does not fetch newly backfilled keys before the floor.
6. Missing/invalid date for a newly added key fails before packet hydration.
7. A selected-count or selected-byte overflow fails before packet hydration.
8. Scheduled/future dates are deferred without blocking completed calls; non-canonical dates fail closed.
9. An all-held selected set retains the verified prior publication instead of wiping public/private output.
10. Route identity is canonicalized, strict state loading preserves its first validation cause, and injected fetchers remain compatible with both one- and two-argument seams.
11. A stale fallback error retains the causal fresh-source failure.

Run: `python3 -m pytest tests/test_earnings_public_wire.py -q`
Expected: new tests fail for missing v2/incremental behavior while the prior suite remains green.

## Task 2: Implement catalog migration and bounded selection

**Files:**
- Modify: `scripts/build_earnings_public_wire.py`

Implement:

- `ROUTE_CATALOG_SCHEMA_V1`, v2 current schema, and strict per-version key validation.
- `forward_selection_floor_date` parsing and v1 derivation from route events.
- Current/prior immutable manifest fetch helpers with byte, canonicalization, contract, generation, and SHA checks.
- A bounded Terminal index loader with explicit byte/count/date validation.
- A pure selection function returning admitted, corrected, forward-new, skipped historical, skipped future, and total selected keys.
- Structural limits of 64 MiB / 100,000 source entries plus separate 10,000-packet and 1-GiB selected-work ceilings.
- Selected-only packet hydration; standalone no-state builds retain the existing full path only below the selected ceiling.
- Causal fresh-source plus fallback error composition.

Keep packet validation and evidence admission unchanged. Do not add eligibility metadata to the story manifest and do not create a private checkpoint store.

Run the Task 1 tests until green. Make one implementation change at a time; do not bundle unrelated refactors.

## Task 3: Prove correction/removal and complete publication

**Files:**
- Modify: `tests/test_earnings_public_wire.py`
- Modify: `tests/test_company_intelligence_dossier_js.py`
- Modify: `tests/test_ticker_pages.py`
- Modify: `site/assets/js/company-intelligence-dossier.js`
- Modify: `templates/ticker.html.j2`
- Modify: committed `site/stocks/*.html` asset references
- Modify: `scripts/build_earnings_public_wire.py` only if tests expose a defect

Add integration tests where:

- a previously admitted packet changes and becomes ineligible;
- its old public article and private record payload are removed;
- unchanged admitted articles remain present;
- a new floor-date-or-later eligible event appears in HTML, route catalog, feed, sitemap, weekly intelligence, and private context;
- the v2 catalog advances the source receipt while preserving the floor;
- an all-held correction wave retains the last verified publication rather than deleting every record;
- the existing ticker-dossier consumer behaviorally accepts both v1 and v2 catalogs;
- the template and every committed ticker page reference the dossier asset by its actual eight-character SHA-256 prefix, preventing a one-year immutable-cache split brain.

Run: `python3 -m pytest tests/test_earnings_public_wire.py tests/test_earnings_wire_freshness.py -q`.

## Task 4: Measure the production-shaped recovery

**Files:**
- Add: a temporary off-repository diagnostic under the operation directory only
- Do not commit production packet bodies or private payloads

Against live current inputs, execute the selector without publishing. Record:

- prior/current generation receipts;
- admitted, changed, forward-new, historical-skipped, and selected counts;
- selected byte total and maximum object size;
- newest selected call date;
- absence of selected keys without valid dates.

Then run a full build into temporary public/private output directories using current live sources. Verify route count, newest date, deterministic second build, stale-page cleanup behavior, and no writes outside the temporary roots.

## Task 5: Adversarial review and repository verification

Commission one bounded persistent-state review after the implementation is green. Route `review` to an Opus-capable reviewer, cap repository calls, require the verdict file first, and ask it to attack duplicate-state creation, late events, corrections, source shrinkage, future dates, bounds, and private/public parity. Adjudicate under `REVIEW_RETURN`; repair blockers and majors with new red tests.

Run at minimum:

- `python3 -m pytest tests/test_earnings_public_wire.py tests/test_earnings_wire_freshness.py -q`
- `python3 -m pytest tests/test_earnings_api.py tests/test_earnings_evidence_graph_deps.py -q`
- the exact CI job/pack line selected by changed-path routing
- repository static and contract checks required by that pack
- `git diff --check`

Re-fetch `origin/main` before push. If owned paths changed on main, reconcile explicitly; never overwrite a sibling repair.

## Task 6: Deliver through production

Stage only task-owned files, commit, push, open one PR, and add `merge-on-green`. Wait for every binding check to conclude; repair genuine reds. Do not use GitHub native auto-merge and do not merge while checks are pending.

After concluded-green review, squash-merge the PR. The merge should trigger `earnings-public-wire.yml` because the builder path changed. Observe one covering workflow run without duplicate dispatch or cancellation.

Production proof:

1. `route-catalog.json` serves schema v2 with the preserved floor, new source receipt, and fresh `verified_at`.
2. Newest live event date is later than 2026-07-29.
3. A selected floor-date-or-later article returns HTTP 200 with the expected exact-evidence record.
4. The first index page displays a floor-date-or-later record.
5. `python -m scripts.audit_earnings_wire_freshness --strict` against live inputs no longer reports the 44-day/2,392-body outage.
6. The live VPS health SHA contains the merge or later covering publication commit.

Only after those receipts is the Wire `PROVEN_LIVE`. Update the existing Earnings Intelligence Agent OS records with the ruling, production proof, and exact next action; validate Agent OS before the final records commit if a second PR is required.

## Stop conditions

Stop only for a genuine external authorization/security gate, a destructive operation requiring Chairman action, an irreconcilable collision with a live owner, or a production failure whose safe repair needs new product authority. Otherwise continue from red tests through live proof in this session.
