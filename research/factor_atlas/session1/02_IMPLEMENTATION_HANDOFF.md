# Factor Atlas Session 1 — Executable Native Implementation Handoff

**Disposition:** owner-facing, ready for qualification; **not an admitted work order, accepted schema, native implementation or publication receipt**. 8 October 2026, America/New_York.

**Goal:** give Macro, Terminal and validated research consumers reproducible, source-bound descriptive histories for existing house baskets without replacing the incumbent semantic, membership, identity, price, state or access owners.

**Architecture:** a pure additive read adapter consumes immutable projections from the existing owners and emits one explicitly versioned measurement envelope. Source collection, membership changes, correction admission, access decisions and publication remain with their present owners. Consumer integration uses the existing Terminal Sector Intelligence gateway and chart ownership, not a second service or router.

**Specification:** `01_FACTOR_MODEL_AND_PIT_RESEARCH.md`. Proposed contract and policy: `contracts/factor_read_model.v0.schema.json` and `contracts/metrics_policy.v0.json`. They are research candidates; the accepted native contract must receive its own reviewed version.

**Execution method:** after the gates below are satisfied, use a single admitted native workspace and separate PR. Follow current protected procedure and its execution/review path. Do not treat this document, optional skills, a tool's technical write capability or the Chairman's broad commission as an exemption from custody, rights or interface acceptance.

## 1. Exact starting state

| Surface | Last source pin | Boundary |
|---|---|---|
| Protected Mastermind | `732cf7be88e7159b4995a8885fbd381cd1484e3e` | Required follow-on procedure reads were refused; modification clearance was not established. |
| Macro | `cdbcd143dcfa419ab0637bc11dd4c80368143e2e` | Targeted source census, not deployed-source proof or complete custody reconciliation. |
| Terminal | `bacda5dcc30682f9327e037a2d4425bd9714ac3a` | Existing gateway/library inspected; no Atlas feed or accepted Atlas chart adapter. |

No remote branch, PR, source write, worker dispatch, installation, deployment or owner acceptance occurred in this commission. No modifying effect is unknown. Local package checks prove only the behaviors identified in `evidence/verification.json`.

### Gates that must change before a native slice starts

1. **Procedure/custody:** complete the missing required protected reads on a lawfully restored surface; qualify the applicable runtime, workspace, source and publication rules. Do not rephrase or switch carriers to replay a refused effect. Recover current GMI/basket/price/identity/Terminal owner records and pending effects. Search hits and old PR heads are not current custody.
2. **Source collision:** reconcile the current heads and exact touched paths of basket/sector/theme/receipt work identified in the report. Preserve existing GMI and Finviz workers/reviewers; no duplicate adapter or watcher. `research/factor_intelligence/` and `engine/theme_graph/` remain outside this PR.
3. **Input admission:** bind complete membership/identity/price/corporate-action/rights receipts for the selected baskets, windows and intended research/display/export purposes. A house-curation allowance is not a price license. A file hash is not an adjustment vintage or an observation clock.
4. **Interface acceptance:** obtain the owning integration decision for the v1 envelope, upstream path, request dimensions, caching/access behavior and exact chart component. A proposed schema does not authorize a new feed.

An unresolved gate produces a documented withheld result, not a fabricated receipt. While gate 3 or 4 remains open, permitted fixture-only/native shadow work depends on the owner's explicit accepted scope; this handoff does not assume that scope.

## 2. Global constraints

Use existing owner-qualified basket and security identifiers. No alias registry, constituent store, canonical catalog authority, ThemeState, portfolio writer, entitlement service, collector, queue or retry service.

US daily pilot only; USD; completed regular-session observation convention explicitly bound by the price owner. Return units are fractions. Base level is 100 before the first admitted return. The initial method uses monthly target weights with drift in constituent-total-return units between effective rebalances. The owner must attest dividend-reinvestment semantics and source compatibility.

Require 100% valued held weight for a qualified portfolio return; never renormalize missing holdings or fill missing return with zero. Permit advance breadth only with at least 3 eligible securities, 80% valid count and 80% valid weight, with PARTIAL status below full coverage. Concentration requires the complete weight vector.

CURRENT_ROSTER and PIT_AS_KNOWN must be separate requests and results. Strict PIT rejects current-roster fallback, unqualified same-day knowledge, partial/unknown collection completeness and ambiguous identity. PIT_LATEST_CORRECTED is a separate revision view, not a silent upgrade of an old backtest.

Actual outcome prices are qualified at measurement cutoff, not at the earlier portfolio-selection cutoff. Selection inputs are qualified at selection cutoff. Preserve calendar version, UTC intervals, basis, source hashes and all correction identities.

No edits to incumbent ranking, entry, sizing, policy, GMI state or portfolio decisions. Existing outputs are unchanged in the pilot PR. No real vendor/member payloads in a public Terminal repository; use synthetic fixtures and appropriately protected evidence references.

## 3. Proposed file boundaries and interfaces

All proposed new paths require approval before placement. Reuse an incumbent helper instead when the owning implementation identifies an already accepted equivalent.

| Task | Candidate paths | Responsibility |
|---|---|---|
| Pure native read adapter | `macro/engine/factor_atlas_read.py` | Compose owner-returned immutable inputs; compute qualified measurements; no disk/network writes or source fallback. |
| Contract | `macro/contracts/factor_atlas_read.v1.schema.json` | Accepted envelope, units, status/null rules and reference requirements; not an owner registry. |
| Native tests | `macro/tests/test_factor_atlas_read.py`, `macro/tests/fixtures/factor_atlas/` | Hermetic cases; no live data or writer-lane environment changes. |
| Native invocation seam | Incumbent Macro builder path, selected by source owner | Bind admitted input manifests and publish through the existing owner. No new collector or daemon. |
| Terminal adapter | `terminal/lib/factorAtlas.ts`, `terminal/lib/__tests__/factorAtlas.test.ts` | Validate accepted envelope and adapt to the existing comparison/chart consumer. |
| Gateway addition | `terminal/app/api/sector-intelligence/route.ts` | Optional owner-approved fixed source; preserve authentication, origin, redirect and size guards. |
| Presentation | Existing Sector Intelligence/chart component, exact path to be recorded by consumer owner | Current/PIT toggle, same-window comparison, provenance and null-safe plotting. No competing shell. |

**Candidate pure interface:**

```python
def build_factor_read(request: Mapping[str, object], *,
                      owner_inputs: Mapping[str, object]) -> dict[str, object]:
    """Read-only composition; no I/O, collection, identity creation or admission."""
```

`owner_inputs` is an invocation-scoped validated projection, not a persisted mirror. It contains references plus precisely selected prices, membership decisions, weights, calendars and receipt fields. The owning implementation should replace this broad prototype signature with the repository's established typed contracts before accepting v1. The proposed JSON envelope fixes observable outputs; it does not prescribe a second owner API.

**Candidate consumer interface:**

```typescript
function qualifyFactorRead(input: unknown): QualifiedFactorRead | RejectedFactorRead;
function toComparisonSeries(read: QualifiedFactorRead): ExistingComparisonInput;
```

`ExistingComparisonInput` means the actual incumbent chart input type, not a new type with that literal name. Qualification must bind that exact type/path in the PR before implementing the adapter; no discovery-time guess is treated as compatibility. A rejected envelope produces unavailable data and reasons, never a plausible empty/zero series.

## 4. Ordered implementation tasks

### Task 0 — Owner contract and immutable input qualification

**Consumes:** fresh governing sources, existing owners/collision records, selected basket IDs and purpose-specific rights decisions. **Produces:** one admitted carrier, accepted v1 contract, exact source manifests and allowed paths.

Record per basket: semantic relationship, current snapshot, PIT collection birth/intervals/completeness, identity mapping, selected price source/field/basis/action vintage, session/venue/currency, reference/execution instants, entitlement purpose and expiry. Candidate IDs are `mag7`, `ai_infra`, `defense`; replace a candidate only through the existing membership owner and record why. Do not claim all three are currently qualified.

**Verification:** validate every required source reference and distinguish unavailable from complete-empty. Confirm only the intended paths are in scope. Preserve the source head and original target of any uncertain effect before proceeding. No fabricated “approval” document generated by the implementer is a substitute for owner acceptance.

### Task 1 — Failing tests for independent current/PIT and missingness behavior

**Files:** the proposed native test file and synthetic fixtures only, in the admitted workspace.

Write and run tests for these exact invariants before product code:

- `test_current_roster_and_pit_return_different_results`: deliberate constituent substitution yields different cohort digests and returns while all other inputs agree.
- `test_pit_false_is_unavailable`: owner fallback cannot produce a strict-PIT point.
- `test_future_known_at_cannot_select_same_day`: known-after-cutoff member or alias is excluded/refused; the publication period alone cannot qualify it.
- `test_late_outcome_price_is_allowed_at_measurement_cutoff`: valid realized outcome after selection is not incorrectly excluded.
- `test_partial_collection_is_not_deletion`: basket-scoped incomplete observation cannot retire a missing member or an unrelated basket.
- `test_missing_held_price_withholds_return_and_breaks_chain`: one missing nonzero position creates null, not a zero or renormalized full-basket return.
- `test_empty_complete_is_not_unknown`: known empty, retired, unobserved and missing-price states remain distinct.

Run `python -m pytest tests/test_factor_atlas_read.py -q` from Macro's admitted root. Record the exact native head and expected failing assertions. Import errors, missing dependencies or a malformed fixture do not count as the intended red test.

### Task 2 — Minimal pure measurement adapter

Implement the accepted interface without changing shared basket/style helpers. Use the incumbent price and membership readers only at the invocation binding seam; pass the frozen result into pure computation. Preserve owner selection rather than independently rebuilding the same data.

Tests must additionally cover:

- Three equal names with one 100→200→100 round trip: monthly drift gives 0%; daily equal reset gives 1/9. Method labels distinguish the outputs.
- 2:1 split: value-neutral; cash dividend: TR includes it once; spin-off/merger/delisting: all verified claims retained or output explicitly unavailable.
- Rebalance target/decision/effective ordering; month-end from an accepted exchange calendar rather than last present row; no selection at a passed auction.
- `n*cap<1` request rejected, or an explicitly different requested method—not a silent 20% weight under a 5% label.
- Exactly 5 valid daily returns suffice for a 5-session result; one missing session is not dropped to manufacture a shorter interval.
- Full weight conservation, breadth count/weight denominators, HHI/effective number, security-to-issuer concentration qualification, linked attribution reconciliation.
- Same semantic inputs produce the same core bytes/hash across separate processes/hash seeds; a source revision changes input identity even if values are equal.

Run the new tests and the relevant incumbent regression suites identified in the report, using the repository's dependency and test configuration. Record exact commands, head, environment and result, not an unsupported “all tests green.”

### Task 3 — Retained owner-data pilot and correction proof

Run the pure adapter against admitted retained inputs for each selected basket. Produce current-roster and PIT results for a common window, plus a disclosed longer current-roster window where valid. At least one real covered PIT interval and a real/owner-qualified membership revision must be exercised for PIT capability acceptance; an all-null PIT panel is not enough.

Recompute the same manifest twice in fresh processes. Verify result-core digests and all numeric cells. Introduce a **synthetic mutation copy** of the input manifest for a controlled source correction test; never edit the incumbent source object. Link original/corrected results and compare only affected intervals. A controlled fixture correction is not evidence of a real upstream correction event.

Hash source files before and after the invocation. Trap filesystem writes and network calls in native tests. No membership snapshot writer, collection lane, cache rebuild or grading ledger is invoked. Preserve private inputs under existing evidence custody; publish only allowed aggregates/references.

### Task 4 — Accepted Terminal consumer proof

Add the accepted source only after contract/interface approval. Retain filtered shared authentication, fixed upstream origin, no redirects, private/no-store caching, 4-MiB maximum and existing error semantics. The qualified data path must not substitute an anonymous source after access denial.

Test schema rejection; missing/revised data; source-date versus fetched-time; fraction-to-percent conversion; gap preservation; matched-window rebasing; current/PIT label persistence; stale source; unknown proxy; duplicate IDs; back/forward URL state; access loss; and unchanged existing feeds.

Run the repository's current typecheck and relevant unit/browser scripts. Record actual commands from its package/configuration rather than assuming a script name. Exercise desktop/tablet/mobile and keyboard/source inspector on the real accepted owner payload. Mocked auth/transport tests are useful but do not establish authenticated served production compatibility.

### Task 5 — Separate exact-head review, publication and acceptance

Publish the separate branch/PR through the admitted carrier. Preserve exact reviewed head, tests, allowed-path diff and source manifests. Independent review under current owner law is not replaced by this research author's self-review.

Merge, deployment and acceptance are separate receipts. Verify the served Macro generation and Terminal build marker, authenticated access and actual current/PIT chart behavior. Do not amend or rewrite incumbent GMI/Fable source to satisfy an Atlas release check. Roll back only the Atlas consumer addition through the owning deployment path if its accepted release fails.

## 5. Highest-value next dependency

Once the first bounded result is verified, continue with the smallest safe prerequisite: owner-provided corporate-action/adjustment and PIT collection evidence, or the accepted consumer adapter. Do not broaden into a new theme ontology, a ranking overhaul or a new collector. Preserve the original source-method mismatch as an owner-native correction task with old/new results retained, not an opportunistic shared-engine edit in the pilot PR.

## 6. Result required from the implementer

Return the admitted operation/carrier, exact Macro/Terminal heads, accepted contract and input manifest IDs, qualified basket/window count, actual current/PIT output and deterministic digest, unavailable intervals with reasons, correction replay result, native regression results, independent review and publication/served-browser receipts. Separate “not built,” “built but not proven,” and “accepted/live” for every dependency. Return the next useful in-scope action or the concrete remaining gate.

**Current handoff frontier:** all native tasks remain unstarted pending the four gates. The local mathematical oracle and schema checks accompany the handoff; they do not close those gates.
