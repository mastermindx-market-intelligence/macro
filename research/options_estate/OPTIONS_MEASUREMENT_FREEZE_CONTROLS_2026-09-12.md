# Options measurement-panel freeze controls and C1 linkage contract

**Date:** 2026-09-12  
**Carrier:** Macro draft PR `#7027`, branch `codex/nightglass-public-research-20260910-sol`  
**State:** prepared and commit-reviewable; **not frozen, not admitted, no proprietary rows acquired, no model fitted**.  
**Review gate:** PR review `5187571731` blocks freeze, acquisition, fitting and merge until the external rights/field receipt and an independent non-owner approval exist.

This record closes the locally resolvable parts of the independent methodological review. It does not replace the parent preregistration, authorize a purchase or vendor contact, open an OA wave, or turn T+1 labels into a live feature.

## 1. Freeze-gate ledger

| Gate | State after this record | Evidence / remaining boundary |
|---|---|---|
| Source and commercial rights | `OPEN_EXTERNAL` | Obtain the controlling Cboe/DataShop license or written source-owner answer for internal commercial research/modeling, retention, derived aggregates, publication and redistribution. |
| Execution-ID entitlement and field semantics | `OPEN_EXTERNAL` | Resolve the product/spec wording against SEC filing 34-104415's phrase “subscribing Member's execution IDs”; confirm nullability, corrections, breaks, provisional finality and mechanism coverage. |
| Observation units / no-double-counting law | `PREPARED_FOR_FREEZE` | Sections 3–4 define five ledgers and one-count-per-endpoint law. |
| C1 overlap / component matching | `PREPARED_FOR_FREEZE` | Section 5 fixes an exact-only primary join and explicit unmapped ledger. |
| Trade-type eligibility | `PREPARED_PENDING_SOURCE_RECEIPT` | Section 6 covers every TBT v1.0 type `1..57`. Conditional rows cannot be promoted by local inference. |
| Package heuristic thresholds | `PREPARED_FOR_FREEZE` | Section 7 fixes the transparent baseline and sensitivity arms before label inspection. |
| Missingness comparison | `PREPARED_FOR_FREEZE` | Section 8 fixes M0/M1/M2 populations, signatures and endpoints. |
| Censoring/dependence/economic ruler | `PREPARED_FOR_FREEZE` | Section 9 retains unresolved observations and separates long-premium from short/sold economics. |
| Current-source pin refresh | `CLOSED_FOR_THIS_HEAD` | Section 2 records current protected heads/blobs and reproduced semantics. |
| Independent approval | `OPEN_EXTERNAL_IDENTITY` | A GitHub identity other than the PR owner must approve the exact frozen head. |
| Natural OA-1T RTH proof | `OPEN_TEMPORAL_EXISTING_OWNER` | Existing owner only; historical replay is not proof and this carrier cannot manufacture it. |

## 2. Current protected source receipt

The research claims were rechecked against these protected identities on 2026-09-12:

- Macro `main`: `46751e12ccc3135b6ed3dff49c73335a25ab5347`.
- `engine/live_flow.py` blob: `323be029c88ef8ee03d97c2ae3a878fce95ba191`.
- `engine/flow_enrich.py` blob: `272e7f8e035e4bba085462fd4ae857e8a64ac3b3`.
- Terminal protected `master`: `a4be9a3f4b51246200cb1b7c4f1d44730066a9a9`.
- `terminal/lib/flowScore.ts` blob: `1f29d5626ebcd4bb2a9dc00a2941b51d5b70b23d`.

Reproduced behavior at those pins:

1. `live_flow` coalesces raw prints by `(expiration, strike, right)` into a single-contract event and retains the latest source sequence for event identity.
2. Its measured NBBO block is execution-location/coverage evidence and explicitly does not assert initiator identity.
3. `flow_enrich.detect_multi_leg` still maps the per-contract `swept` flag to `MULTI_LEG`.
4. The Macro q-score still grants `vol_gt_oi=None` a `0.60` factor and unknown moneyness a `0.60` factor.
5. Terminal still describes the fixed score as a flow “conviction” score and describes `vol > OI` as fresh/new positioning.

This is a semantic-drift receipt, not a production-prevalence measurement. No current R2 market rows were loaded.

## 3. Frozen observation units

The study keeps five non-interchangeable ledgers:

1. **`execution_side_record`** — one final source row for one side/capacity/open-close observation. Stable identity is the immutable source-file version plus row ordinal or source-supplied row identity; a derived content hash is only an integrity checksum.
2. **`simple_execution`** — one C1 execution keyed by `(exchange, trading_dt, exec_id)` only after the source receipt confirms entitlement, completeness and uniqueness.
3. **`complex_execution`** — one exchange-defined complex execution keyed by `(exchange, trading_dt, complex_exec_id)` only where that field is documented and populated. `exec_id` may be used for a complex mechanism only when the receipt gives that exact meaning.
4. **`component_leg`** — one OSI contract/side/quantity component attached to a supported complex execution. Legs are not independent package observations.
5. **`live_component_print` / `live_event`** — the canonical pre-aggregation raw ThetaData print and existing coalesced `live_flow` event. Matching happens at component-print level before event roll-up.

### One-count-per-endpoint law

- A source side row contributes at most once to a side/open-close endpoint.
- A paired buy/sell execution contributes at most once to a transaction endpoint.
- A complex execution contributes at most once to a package endpoint, regardless of sides or legs.
- Quantity- and premium-weighted summaries are reported separately and never replace observation counts.
- Repeated alerts/revisions from one canonical campaign remain clustered under that campaign.
- No row, side, leg or revision may be duplicated to increase evidence or sample size.

“Single-leg supported” below means only that the **exchange-defined execution represented by that type** is documented as single-leg. It is not proof that the beneficial owner had no staged, cross-exchange or separately entered package.

## 4. Endpoint ownership

| Endpoint | Unit | Positive/negative meaning | Forbidden inference |
|---|---|---|---|
| Side/open-close field recovery | `execution_side_record` | Agreement with final entitled source field on supported mechanisms | Aggressor, initiator, motive, informed trader |
| Simple execution reconstruction | `simple_execution` | Complete paired execution under confirmed `exec_id` semantics | Beneficial-owner strategy |
| Exchange-defined package association | `complex_execution` | Complete supported exchange link across all represented legs/sides | Cross-exchange or staged package absent from source linkage |
| Transparent package candidate | linked `live_component_print` set | Heuristic candidate under Section 7 | Ground-truth package or profitable structure |
| Event interpretation | existing `live_event` | Roll-up of component coverage and supported labels | Backfilled T+1 evidence at decision time |
| Attention missingness comparison | fixed daily eligible population | Rank behavior under M0/M1/M2 | Probability, conviction, expected return |
| Later economics, if separately admitted | existing exact-instrument lifecycle/campaign owner | Executable policy outcome with all terminal states | Best print, midpoint substitution, underlying return |

## 5. C1 overlap and exact component matching

### Eligible primary universe

- Exchange: `C1` only.
- Session: `RTH`; the daytime `trading_segment` associated with that RTH row.
- Source product: exact licensed TBT version and immutable file hash recorded at acquisition.
- Live source: existing canonical raw `bulk_trade_quote` component rows that formed eligible `live_flow` events.
- Instrument: exact OSI identity `(root, expiration, call_put, strike)` after deterministic normalization.
- No non-C1, GTH, Curb, routed-away or unmapped row is a negative example.

### Primary exact join

A component pair is a primary match only when all agree:

1. C1 exchange and trading date;
2. exact normalized OSI identity;
3. exact contract quantity;
4. exact trade price in integer minimum-tick units, not floating tolerance;
5. exact normalized `transact_time`/`trade_timestamp` at the coarser documented source precision, with no nearest-neighbor search;
6. final/non-provisional source state under the source receipt.

Both clocks must be converted to integer exchange-local epoch units using documented precision. One row may not be rounded toward another. If the products do not document a common resolution, the primary match is unavailable until the source owner resolves it.

### Ambiguity and roll-up

- Multiple candidate rows, split prints, subset-sum quantity matches, timestamp-nearest matches and price-only matches are `unresolved`, not forced.
- Electronic matching uses `transact_time`. `floor_action_ts` remains a separate floor-agreement clock and never substitutes for electronic booking time.
- Matched raw rows roll up to the immutable `live_event_id` with `supported`, `partial`, `unresolved`, `unmapped` and `corrected` counts.
- Event coverage is supported matched premium/print count divided by the full eligible component denominator and cannot exceed 1.
- T+1 labels append an evaluation revision; they never rewrite `event_at`, `decision_at`, original soft side or measured NBBO block.

For coverage diagnosis only, report exact-price/size/OSI candidate pairs at timestamp offsets `±1 ms`, `±10 ms`, `±100 ms` and `±1 s`. They remain unmatched in the primary endpoint. No diagnostic tolerance may be promoted after label inspection without a new preregistration.

## 6. TBT v1.0 trade-type eligibility matrix

Every specification ID `1..57` is covered exactly once. `conditional_package_positive` means public prose indicates a complex execution, but a positive package comparator is admitted only after the source receipt confirms linkage and completeness. `unresolved` is not negative.

| IDs | Trade-type family | Class | Package endpoint | Linkage before source receipt | Side/open-close |
|---|---|---|---|---|---|
| 1–4 | AIM Simple: Agency, Contra, Responder, other participant | `simple_electronic` | `single_leg_supported` | `exec_id` | `eligible_if_final` |
| 5–8 | AIM Complex: Agency, Contra, Responder, other participant | `complex_electronic` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_receipt` | `eligible_if_final` |
| 9–11 | AIM FLEX Simple | `simple_electronic` | `single_leg_supported` | `exec_id` | `eligible_if_final` |
| 12–14 | AIM FLEX Complex | `complex_electronic` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_receipt` | `eligible_if_final` |
| 15–17 | SAM Simple | `simple_electronic` | `single_leg_supported` | `exec_id` | `eligible_if_final` |
| 18–20 | SAM Complex | `complex_electronic` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_receipt` | `eligible_if_final` |
| 21–23 | SAM FLEX Simple | `simple_electronic` | `single_leg_supported` | `exec_id` | `eligible_if_final` |
| 24–26 | SAM FLEX Complex | `complex_electronic` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_receipt` | `eligible_if_final` |
| 27 | Floor PAR Simple | `simple_floor` | `single_leg_supported` | `exec_id_pending_floor_receipt` | `conditional_floor_clock` |
| 28 | Floor PAR FLEX Simple | `simple_floor` | `single_leg_supported` | `exec_id_pending_floor_receipt` | `conditional_floor_clock` |
| 29 | Floor PAR Complex | `complex_floor` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_floor_receipt` | `conditional_floor_clock` |
| 30 | Floor PAR FLEX Complex | `complex_floor` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_floor_receipt` | `conditional_floor_clock` |
| 31–32 | Floor Legged In, standard/FLEX | `complex_floor_legged` | `partial_or_unresolved` | `none_until_linkage_receipt` | `conditional_floor_clock` |
| 33–34 | MM In-crowd Simple, standard/FLEX | `simple_floor` | `single_leg_supported` | `exec_id_pending_floor_receipt` | `conditional_floor_clock` |
| 35–36 | MM In-crowd Complex, standard/FLEX | `complex_floor` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_floor_receipt` | `conditional_floor_clock` |
| 37 | QCC | `ambiguous_contingent` | `unresolved` | `none_until_mechanism_receipt` | `conditional` |
| 38 | Compression | `ambiguous_strategy` | `unresolved` | `none_until_mechanism_receipt` | `conditional` |
| 39 | Routed | `routed_external_execution` | `excluded_from_primary` | `none` | `excluded` |
| 40 | FLEX Auction Simple | `simple_electronic` | `single_leg_supported` | `exec_id` | `eligible_if_final` |
| 41 | FLEX Auction Complex | `complex_electronic` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_receipt` | `eligible_if_final` |
| 42–43 | COA Initiator / Responder | `complex_electronic` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_receipt` | `eligible_if_final` |
| 44 | COA Unrelated | `ambiguous_electronic` | `unresolved` | `none_until_mechanism_receipt` | `conditional` |
| 45–46 | SUM Displayed / Response | `simple_electronic` | `single_leg_supported` | `exec_id` | `eligible_if_final` |
| 47–48 | Complex Remove / Add | `complex_book_side` | `conditional_package_positive` | `complex_exec_id_or_exec_id_pending_receipt` | `eligible_if_final` |
| 49 | Resting Complex Legged In | `complex_legged` | `partial_or_unresolved` | `none_until_linkage_receipt` | `conditional` |
| 50 | Incoming Complex with Simple Legs | `complex_with_simple_legs` | `partial_or_unresolved` | `none_until_linkage_receipt` | `conditional` |
| 51–52 | Legged In to Resting Complex / Contra | `complex_legged` | `partial_or_unresolved` | `none_until_linkage_receipt` | `conditional` |
| 53–54 | Simple Remove / Add | `simple_book_side` | `unresolved` | `exec_id_pending_mechanism_receipt` | `conditional` |
| 55 | Opening Cross | `simple_or_complex_unknown` | `unresolved` | `none_until_mechanism_receipt` | `conditional` |
| 56 | RFC | `simple_or_complex_unknown` | `unresolved` | `none_until_mechanism_receipt` | `conditional` |
| 57 | Provisional | `provisional` | `excluded_until_final` | `none` | `excluded` |

Additional law:

- Simple rows support only the exchange-defined single-leg execution after paired-side completeness/finality is confirmed.
- Complex rows cannot become confirmed packages merely because their names contain “Complex”; all represented legs and sides require confirmed linkage.
- Legged-in, complex-with-simple-legs, QCC, compression, RFC, opening-cross and ambiguous book-side rows remain mechanism-specific/unknown until confirmed.
- Routed rows are outside the C1 executed-overlap primary endpoint.
- Type 57 stays excluded until a later final classification is versioned and remains preserved in the unmapped ledger.
- No trade type supplies beneficial-owner identity or aggressor truth by itself.

## 7. Transparent package-candidate baseline E

This is a transparent heuristic comparator, not ground truth and not a production feature.

### Immutable thresholds

- Primary maximum component timestamp span: `500 ms`.
- Predeclared sensitivities, never selected by achieved accuracy: `100 ms` and `2,000 ms`.
- Same root; 2–4 distinct OSI contracts; no duplicate contract after exact source-sequence deduplication.
- Aggregate leg-size ratios reduce within 10% to `1:1`, `1:2`, `2:1`, `1:3` or `3:1`.
- Same-expiry templates: vertical, straddle, strangle, risk reversal, butterfly and condor only when rights/strikes form one unambiguous template.
- Calendar/diagonal templates: exactly two expiries and same right; either same strike or one strike per expiry. Multiple feasible templates are `unresolved`.
- Inputs are cutoff-time fields only. T+1 linkage is comparator truth, not an input.
- A component in multiple feasible candidates makes all affected candidates `conflicting`; retain them in coverage but exclude them from resolved-template accuracy.
- Payoff orientation is stated only when all component-side records are supported and the template is unique.

Baselines: **D** current `swept -> MULTI_LEG`; **E** fixed heuristic above; **F** entitled linkage after approval. Report supported-domain precision, recall, F1, single-contract false-package rate, missed unswept linked-package rate, component coverage, unmatched/multiply matched quantity, template accuracy and correction stability. Cluster uncertainty by complex execution and session.

## 8. Missingness policies M0/M1/M2

Use the same frozen daily C1-overlap event population for all arms.

- **M0 current fallback:** exact pinned behavior; unknown OI and moneyness retain current positive factors.
- **M1 evidence-only:** unavailable components contribute zero, remain in an availability vector and are not renormalized.
- **M2 availability-stratified:** rank only within the exact signature `premium_z_present`, `prior_oi_present`, `moneyness_present`, `nbbo_coverage_bin` (`missing`, `[0,0.80)`, `[0.80,1.00]`) and `package_state` (`single_leg_supported`, `resolved`, `partial`, `unresolved`, `conflicting`).

No arm is probability, conviction or expected return. Predeclared outputs are Kendall tau-b agreement, top-2% and top-10% Jaccard overlap, score/rank shift due only to missingness, missing-field concentration by percentile, population/premium coverage by signature, and one-field-removal stability. Ties use immutable event ID. `premium_z=null` never earns unusualness or an outlier badge under M1/M2.

## 9. Censoring, dependence and later economics

The public `3968 / 6389` result remains descriptive conditional arithmetic under its stated idealized +30/-50 model. The 954 open observations are administrative censoring, not disposable failures or successes.

Any separately authorized internal economic study must:

- enroll every candidate at original decision/availability time;
- retain `target`, `stop`, `expiry/deadline`, `no_entry`, `data_unavailable`, `open_at_cutoff` and correction states;
- use a common-age locked cohort or competing-risk cumulative incidence with frozen administrative cutoff;
- cluster by existing campaign/session and keep package legs together;
- report unresolved-outcome bounds;
- separate long-premium, short/sold-option, debit-package and credit-package economics, including capital, margin and tail denominators;
- use exact executable quotes, latency, fees and quantity; never best print, midpoint, intrinsic or underlying return;
- version admission, entry, quote, management and outcome rulers.

This record authorizes none of those arms.

## 10. External source-owner question packet

Preserve the controlling answer verbatim with responder/date and contract/version reference:

1. May a non-TPH commercial subscriber use TBT internally to evaluate and develop proprietary analytical/modeling methods?
2. What storage, retention, backup and internal-user limits apply?
3. Which derived aggregates may be published, shown to customers or used commercially without redistributing rows?
4. Does a non-TPH subscriber receive `exec_id`/`complex_exec_id` for the full C1 report or only executions associated with a subscribing Member?
5. For each type, when are IDs populated, unique and stable? Which field links paired sides, all package legs, legged-in and complex-with-simple-leg executions?
6. Are `side`, `open_close` and `capacity` side-specific on every row, and do meanings vary by mechanism?
7. How are cancels, breaks, corrections, late floor reports, duplicate rows and type-57 updates delivered/versioned?
8. What constitutes a final row, and can historical files be restated?
9. What timestamp precision/time zone applies to `transact_time` and `floor_action_ts`?
10. Are routed rows executions on C1 or reports of execution elsewhere?
11. Are there unstated mechanism-specific linkage/open-close limitations?
12. Which license controls where product page, specification and SEC filing wording differs?

No purchase, download or contact is authorized by this packet alone.

## 11. Exact next actions

1. Existing source/rights owner obtains and records Section 10 answers under the controlling license.
2. Update only conditional cells explicitly resolved by that receipt; preserve unresolved cells.
3. Freeze the parent preregistration plus this record at exact hashes before acquiring rows.
4. Obtain approval from a GitHub identity other than the PR owner on that exact head.
5. Independently, the existing OA-1T owner captures one natural untouched RTH source-to-existing-consumer receipt. No historical replay or this branch may substitute.

Until steps 1–4 complete, #7027 stays draft and no proprietary TBT rows or model fitting may begin.
