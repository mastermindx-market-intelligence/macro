# Commodity asset-read R2 — implementation and acceptance

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
