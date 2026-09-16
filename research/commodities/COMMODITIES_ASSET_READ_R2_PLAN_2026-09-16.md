# Commodity asset-read R2 — implementation and acceptance

## Current candidate qualification — supersedes earlier blocker notes below

Semantic source 306834682e15121c636db1091a1de8f242c3608e completes the scoped malformed-input qualification:
invalid identities/enums/timeframe containers and records, cross-asset identity,
overflowing numeric inputs, and invalid price observations fail closed. Finite
prices alone advance price_asof; valid finite zero/negative prices are preserved.
No allocation model, indicator aggregation, score weight or source data is changed.

101 focused tests pass, including the 110-invalid-input matrix, 1,458 nominal
combinations, clock controls and capture wiring. The exact combination with R1
0b249399 passes 450 tests with two existing NumPy warnings. Counts overlap.
24 canonical whole-page fixture captures and 96 card/detail interactions pass in
both themes/locales at requested desktop/mobile widths with overlay checks.
The full-page mode is reproducible through the existing R2 capture script.

The previous 403-test interruption was recovered. A later 416-test output was
rejected because its setup failed; it is not acceptance evidence. The corrected
448-test source pair passed, then the two capture-mode tests brought the final
exact-source total to 450. No duplicate in-flight test or CI run was started.

The initial tool-refused input guard refinements are no longer the active code
frontier: the scoped changes were completed through the same source carrier and
verified. Shared-markup refactoring remains omitted; shared data and user selection
are already tested, so no second renderer is required to call that connection built.

State: BUILT_NOT_PROVEN / DRAFT-HOLD. Independent review, applicable concluded CI,
R1/#7215/#7163 release dependencies and actual served page/data verification remain.
No numerical trading-edge improvement or current market recommendation is claimed.
Evidence: COMMODITIES_QUALIFIED_R1_R2_RELEASE_PROOF_2026-09-16.json and
mockups/evidence/commodities-qualified-r1-r2/. After this bounded release, advance
the approved family-specific macro/read model and coherent publication work using
existing owners; chart parity still requires the exact chart recipe.

## Earlier implementation history

Operation: `commodities-asset-read-r2-20260916-sol-001`. Parent: commodities-asset-first-safety-r1-20260916-sol-001 / #7198.
Source pickup: `784bc6aec7c32e8f651c280978d5b5ab0aa366f4`. Protected procedure: Mastermind `bf843961c0e1b5bd45fa481f0138c71f2a87d4e2`, Skillpack 1.0.1.
Current live Chairman direction authorizes advancing the next useful capability while CI is held.
Direct-execution reason: PRINCIPAL_JUDGMENT — reconcile existing model labels, exposure targets,
timeframe evidence and date semantics without originating another trading policy.

## User outcome

An investor can compare gold, silver, copper and oil on their own evidence instead of inferring
permission from commodity-index breadth. Each card displays its existing instrument key, model
exposure target, model label, risk, long trend, daily/three-session/weekly evidence, signal date,
and a reason when those inputs disagree. One semantic click opens that same asset's detailed read.

The machine job is one display-only projection shared by detail and the existing latest.json
payload. It does not compute a new exposure, conviction score, forecast, rank or entry gate.
`new_entry_permission` remains null; no numerical policy is admitted or changed.

## Source and no-rebuild boundaries

- Preserve R1's frozen source/evidence. R2 is a separate bounded capability and must not release
  ahead of the R1 headline/MTF safety prerequisite. Do not copy R1 source changes into this PR.
- Extend scripts/build_commodities.py and its existing view model/latest.json writer. No database,
  publication service, ledger, lifecycle, identity registry, evaluator or calendar is introduced.
- The new scripts/commodity_asset_read.py is a pure projection of existing outputs, not a model.
- templates/_commodity_asset_read.html.j2 and the existing commodities template render the same
  projection; existing detail-tab controls are reused, not replaced with another navigation system.
- New tests are enrolled in the existing commodity panel step in .github/ci/legacy-jobs.yml;
  no workflow/job, budget, or release permission is added.
- A small capture wrapper borrows the existing commodity fixture renderer, theme/locale helpers,
  Chromium context and content-addressed PNG producer; it is not a second chart implementation.
- No Yahoo-derived export or paid redistribution is widened. Archived data stays on the host.

## Data and failure semantics

Unknown model exposure must stay unavailable, not become 0%. A genuine zero target stays 0%.
A BUY label alongside zero exposure is an explicit policy disagreement, not a vote to average away.
Weak daily/three-session evidence or the existing WAIT/CAUTION/AVOID/pullback assessment cannot be
promoted to positive alignment by this summary. A real positive control remains descriptive.

Dates come from the existing frame observations, not live quote hydration. Signal and price-date
mismatch, missing dates, unsorted/duplicate source indexes and missing core evidence are incomplete.
Lag is explicitly relative to the newest declared page input, in calendar days; no live freshness
SLA or completed-bar claim is invented. The existing NYSE-reference three-session aggregation may
include a partial bar and is not represented as exact TradingView/CME parity. Temporal Grain remains
the owner of that independent chart-contract work.

## Implemented and observed in this candidate

- One asset read shared by the per-asset detail and vm.asset_reads; existing latest.json receives
  that same field. No new durable decision file.
- Core cards expose conflicting/defensive/positive/incomplete/lagging states independently.
- A reproduced new bug in the initial draft let a positive summary outrank the existing WAIT
  verdict. A distinct consumer fix now preserves the existing timing assessment. Its regressions pass.
- 56 focused projection, source-wiring, fixture and template tests pass.
- Ten relevant suites on the isolated source candidate: 324 passed, 0 failed, 2 pre-existing
  NumPy warnings. This count is against the main-based R2 candidate, not the unmerged R1 test tree.
- 24 Chromium component fixture cells (3 scenarios x EN/ZH x dark/light x 1440/390) pass;
  all 96 summary-to-detail clicks preserve asset identity and headline. Component bounds fit.
  Full-page overflow and served/hydrated production behavior are NOT certified by these crops.

## Archived-input consumer replay

The normal input/signal/asset_vm/build_sector_vm/template path produced all 17 asset reads from
archived inputs through September 15, with exact calibration-file hashes recorded. Gold and silver
both retained 0% targets and elevated risk. This exposed another distinction: oil carried a SELL
model label with a 100% allocation-model target. R2 now names both directions of label/target
disagreement; it never changes either underlying value. Three discriminating regressions pass.

The replay did not run collectors or production publication. An optional index-cache persistence
attempt hit the deliberately read-only fixture and was not retried or enabled; the computed
projection and HTML were returned normally. This is not a successful production persistence test.

## Explicit held refinements and acceptance limits

A requested strict-input refinement for the pure projection was tool-refused and was not applied.
Readback confirmed the retained original guards; the later timing-verdict consumer change is distinct
and does not include that refused refinement. A separate attempt to factor the card/detail markup
into one shared rendering macro was also refused and not applied. Current card and detail read the
same dictionary but retain their separate markup. Do not bypass a refused action through another
actor or carrier, and do not treat the passing nominal cases as proof of every malformed input.

R2 remains PARTIAL / DRAFT / NOT_PRODUCTION_PROVEN until strict input-edge qualification,
independent exact-head review, current integration/CI and the source publication gates are closed.
The known R1 CI attempt 2 is terminal cancelled; no third rerun was sent. #7215 pack 6 has a genuine
failed result, but its exact underlying unit has not yet been established; blocked log/fragment
retrievals were not bypassed. Reviewer placement remains under the existing owner, not Chairman labor.

## Next implementation and proof steps

1. Preserve the archived-input replay and verify any subsequent semantic correction against it;
   optional missing fixtures and the refused cache-write remain explicit.
2. Freeze exact source and committed fixture evidence. Run design/evidence/CI contract gates;
   retain negative findings, never suppress tests or manufacture a green status.
3. Integrate against R1 through an exact merged/source combination after its release prerequisites;
   verify headline, asset cards, detail and latest.json identity together.
4. Finish strict input-edge qualification only when the editing route lawfully admits it, obtain
   independent review and drive the existing release path through actual served/browser proof.
5. Continue the approved coherent publication and per-family macro/model upgrades; no new numerical
   challenger gains authority without point-in-time and forward validation.

Stop condition is real source/review/release/permission closure, not a CI wait alone. Records and
component screenshots are continuity evidence, not delivery acceptance of the wider commodities program.

## Completed consumer and null-target follow-through

The existing asset_vm producer was still coercing None to 0% and crashing on NaN
before the new read could render. Its two-case RED proof plus three valid controls
now pass by reusing exposure_percent and preserving valid legacy rounding.

The existing hub loader discarded asset_reads and the hub card still derived a
Favored list from the commodity quadrant. The loader now forwards the canonical
asset read and its card renders those dated asset descriptions, with explicit
unavailable states and escaped text. It does not calculate another sector verdict.
Mobile retains the established compact navigation layout; asset details are read
on the commodity page rather than forced into a 52px navigation tile.

Open #7048 owns adjacent BTC/bond/IPO hub copy. R2's helper was positioned beside
the commodity loader, and its renderer edit was scoped to the commodity expression.
A three-way source merge with #7048 head 8f33915a0e33ce9fe02ed6dc3de17a5b44dd7e24
and common 909dc4edfd99b916b9b2a9f79630dee5af984d81 is conflict-free. This is not
acceptance of #7048, and its future movement still requires reconciliation.

The isolated normal build now runs build_commodities.main, the existing write_page
and latest.json writers, and the real hub loader/chip consumer. It writes 17 reads;
the core page states match the JSON and hub. External vendor collection and the
optional hazard artifact are absent; no network connection was attempted. All
outputs are in a new fixture, not site production. A first fixture setup failed
because it copied a read-only commodity-input symlink; that symlink was not made
writable. A new output namespace completed the replay successfully.

There are now 67 focused cases, including a 1,458-combination nominal policy grid.
The last ten-suite run before that additional grid case passed 334 tests with two
existing warnings; the full integrated-source run is a separate receipt. No nominal
matrix result settles the separately held malformed-input qualification.

## Recovered integration and committed R2 component proof

Protected procedure was re-pinned at Mastermind
`5ee11ab1e993616f3568cfca4069cb21fa61fd8f` (compatible Skillpack 1.0.1).
The interrupted exact R1/R2 source projection completed **403 tests**, zero
failures and two existing NumPy warnings in 408.85 seconds. The original log and
all six merged-file digests were recovered; no replacement test was launched.
The precise pair remains R1 `9f6b536f` plus R2 `bf8d7256`, not current main.

The original R2 component corpus is now preserved under
`mockups/evidence/commodities-asset-read-r2/`. All 24 PNG hashes and 6895
materialized source blobs matched the exact R2 source before binding the manifest.
The existing evidence validator accepted the receipt and its full state matrix.
The recorded 96 interactions are component-fixture proof, not full-page or hub
browser proof. Pixel crops do not establish global viewport geometry.

No semantic code was changed to preserve these results. Strict malformed-input
qualification and the separately refused refinements remain held. A new combined
full-builder fixture setup was tool-refused; the target was confirmed absent and
that setup was not retried or moved to another carrier. Prior successful R2
normal-builder/page/JSON/hub replay remains valid only within its stated limits.

Next: finish allowed browser inspection and source qualification, obtain independent
reviews and current-head checks, and then use the existing production publication
path. Do not redo completed implementation, source-merging, tests or captures.
No production acceptance, current market update or numerical-model admission follows
from these evidence-only changes.
