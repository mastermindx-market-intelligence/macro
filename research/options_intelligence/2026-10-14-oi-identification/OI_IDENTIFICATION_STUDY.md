# Options opening/closing identification: bounds, source identity and the OIF18 consumer

**Research observation date:** October 14, 2026 UTC. This is a dated continuation of the original October 3 Options Intelligence commission, not a retrospective change to its original information cutoff. Mathematical results below are conditional identification results, not empirical predictive findings. Repository source was inspected at `macro@a3f3afa1e1268908a54263043f21048c1b5bc1b4`. No production source, data, collector, scored feature, candidate policy or empirical registration is modified by this research package.

## 1. Decision and connection to the original research

The original brief asks whether opening/closing activity can be inferred from yesterday's OI, today's volume, subsequent OI, signing and repeated activity, while keeping real-time inference separate from next-day evidence. The accepted 40-feature catalogue already places **OIF09**, actual non-market-maker buyer-opening put share, behind classified-source evidence. **OIF18**, next-available OI-change-to-volume context, is a separate aggregate feature. Neither definition is changed here. [R1]

**Decision:** retain exact observed contract-count changes as aggregate context; represent the opening/closing implications as an explicit feasible set when its input assumptions are actually supported. Do not attach an opening probability to a print from OI change or volume/OI alone. Do not convert the bounds into a new signal, seventh pilot, dealer inventory estimate, or substitute for OIF09. A later probabilistic estimator would need independently classified labels, a specified target and calibration study, not a midpoint of these intervals.

The practical advance is threefold: a sharp, executable count reference; a reproduced collision in an existing OI source-identity check; and a precise boundary between per-contract OIF18 and a legitimate but different net-by-strike display.

## 2. Observation model — what is assumed, not observed by the reference

Take one unchanged economic option series. Let `V` count every matched unit-contract transaction **once** over one specified interval. Let `I0` and `I1` be known nonnegative outstanding-contract counts at the interval boundaries. A unit trade has buyer/seller position effects:

| Symbol | Buyer | Seller | OI change from the trade |
|---|---|---|---:|
| `x` / OO | Opens long | Opens short | +1 |
| `y` / CC | Closes short | Closes long | -1 |
| `z` / OC | Opens long | Closes long | 0 |
| `w` / CO | Closes short | Opens short | 0 |

The mapping is consistent with OCC/OIC's description of opening/closing combinations. OCC also removes exercised/assigned contracts when calculating OI. [S1] The equations, bounds, constructions and code that follow are this research's derivation under the declared model; the vendor sources do not supply or validate this estimator.

Let `E` be the known number of non-trading removals. The reference allows their timing to be unconstrained; removals may all occur after trading. It does not model positive non-trading additions, corporate-action conversion, changed deliverables, corrections to an earlier state, or incomplete/one-venue volume paired with whole-market OI. Missing `E` is not silently zero. A justified interval for `E` can be examined separately.

Inventory must remain nonnegative. Closing and mixed transfers require at least one existing unit; from genuinely zero initial OI the first unit trade must be OO. This is an economic-count model, not a venue matching-engine simulator or reconstruction of individual investor accounts. Quotes, price, aggressor direction and participant capacity are not used to assign the latent effects.

## 3. Sharp joint feasible set

Define the trade-induced change

`d = I1 - I0 + E`.

Then

`x + y + z + w = V`, and `x - y = d`.

Set `m = z + w`. With exact integer counts, the complete feasible parameterization is:

```
x_min = max(0, d, 1 if I0 == 0 and V > 0 else 0)
x_max = floor((V + d) / 2)
x in [x_min, x_max], integer
y = x - d
m = V + d - 2*x
z in [0, m], integer
w = m - z
```

The counts are infeasible if `abs(d) > V` or `x_min > x_max`. Negative/fractional/boolean/nonfinite counts and unknown required counts are refused before calculation. Empty valid intervals with `V=0` remain permitted; their opening share has no denominator and stays null.

### Necessity

Nonnegative CC requires `x>=d`, and nonnegative mixed count requires `2*x<=V+d`. Nonnegative OO requires `x>=0`. If initial OI is zero but trading occurs, at least one OO is needed before any closing or mixed event can take place. The endpoint relation and nonnegative `I1,E` ensure `I0+d=I1+E>=0`.

### Constructive sufficiency

For any integers in the parameterization, execute all `x` OO units first, then all `z+w` mixed units, then all `y` CC units, then the `E` removals. A positive-volume zero-start sequence has at least one OO, so mixed trades have inventory. Immediately before closing there are `I0+x` units, and `y=x-d<=I0+x` because `I0+d>=0`. After trades there are exactly `I1+E` units, enough for the final removals. This produces the stipulated endpoint and every feasible marginal extremum.

This proof is conditional on freely ordering trades and removals. Known event positions can impose more information; the reference provides a separate bounded dynamic program for that case. Known actual removal times, participant constraints or other state changes require another explicitly specified model, not an undocumented extension of this construction.

## 4. Marginal bounds and a denominator distinction

The sharp marginal integer bounds are:

| Quantity | Lower | Upper |
|---|---:|---:|
| Both sides open | `x_min` | `x_max` |
| Both sides close | `x_min-d` | `x_max-d` |
| Mixed | `V+d-2*x_max` | `V+d-2*x_min` |
| Buyer-opening contracts | `x_min` | `V+d-x_min` |
| Seller-opening contracts | `x_min` | `V+d-x_min` |
| Opening participant sides | `V+d` | `V+d` |
| Closing participant sides | `V-d` | `V-d` |

**Marginal endpoints cannot be freely combined.** For example, the buyer-opening and seller-opening maxima may require different mixed-trade decompositions. The joint parameterization, not the rectangle formed by the marginal ranges, is authoritative for this mathematical model.

The fraction `(V+d)/(2*V)` concerns **opening participant sides among both sides of matched trades**, not the probability that a buyer opens and not the fraction of OO trades. Exact rational numerator/denominator values avoid large-integer float rounding. When `V=0`, this fraction is null.

### Examples that distinguish the interpretations

**Flat OI and 100 trades, starting from 10 outstanding:** buyer-opening quantity can be anywhere from 0 to 100, even though opening participant sides total exactly 100. One construction has all buyers close shorts while sellers open shorts; another has all buyers open longs while sellers close longs. Both keep OI at 10. Even additionally assuming that every buyer was the aggressor would not distinguish these two opening/closing constructions. A quoted at-ask observation is weaker than that extra assumption.

**OI increases by 90 on volume 100, with known zero removals:** buyer-opening quantity is 90–100, while OO quantity is 90–95. This is a useful count restriction, not an empirical confidence level. The opening-side fraction is 95%, but neither buyer-opening percentage nor the OO percentage is identified by that fraction.

**Volume exceeds initial OI:** the first example already has `100>10`, yet buyer-opening quantity can still be zero. Turnover/transfers can repeat; this threshold is not proof of opening buys.

**Zero start, zero finish:** two trades must be one OO and one CC. With three trades there is exactly one mixed trade; buyer-opening quantity is 1–2. A single trade returning zero to zero is impossible in this model. These boundaries falsify the naive formula that omits the zero-start restriction.

**Expiry/removal without trading:** `V=0, I0=100, I1=0, E=100` has zero closing trades. The observed OI decline is not a count of sell-to-close or buy-to-close transactions.

## 5. Selected flow, observed order and unknown removals

For an otherwise unpositioned selected subset containing `A` of the `V` unit transactions, let the global buyer-opening bounds be `[L,U]`. Its buyer-opening bounds are

`[max(0, L+A-V), min(A,U)]`.

This counts possible opening units **within that subset**; it does not establish that the subset is genuinely aggressor-classified, non-market-maker, directional or from one package. With volume 100, OI gain 90 and a selected quantity of 30, the selected buyer-opening count is 20–30. Selection identity and quote-signing confidence remain separate inputs.

For positive initial inventory, the global unidentified width simplifies to `U-L=V-abs(d)`. This is an algebraic size of a feasible set, not a statistical confidence score. A selected subset can remain completely unidentified even when the global range is narrow: with volume100, OI gain90 and a selected five-unit print, the selected buyer-opening quantity remains 0–5. In the positive-change case, a strictly positive lower bound for the subset requires `d > V-A`: the OI gain must exceed all volume outside that subset. The [nine-case sensitivity table](ambiguity-sensitivity.json) checks these statements under its explicitly idealized complete-volume/known-removal assumptions.

Knowing exact unit-event positions can tighten this range. With true zero initial/final OI and three trades, the first selected unit is certainly buyer-opening, the last certainly not buyer-opening, and the middle can be either. `ordered_subset_bounds` solves the finite state problem with `interest -> minimum/maximum selected buyer-open count`. Its 256-unit cap is a research-computation limit, not a license to truncate a larger tape. Source ordering must be independently qualified; timestamp ties or merely sorting a file do not prove clearing/execution order.

For removals known only to lie in `[E_low,E_high]`, the reference returns the **union** of feasible count sets. It does not pick the most convenient value. For `V=100, I0=100, I1=20`, assuming `E=0` gives buyer-opening bounds 0–20; allowing justified removals from 0 through 80 broadens them to 0–100. The output identifies any declared interval endpoints incompatible with the count model. Unknown positive adjustments or unmatched volume still invalidate this model; they do not disappear into `E`.

The interval implementation computes marginal extrema from endpoints, parity neighbours and the small number of piecewise breakpoints rather than iterating over a possibly enormous removal range. Exhaustive finite-state tests check this optimization independently of its formulas.

## 6. Reproduced source finding: equal aggregates are not equal contract content

At the pinned source cut, `engine/positioning_persistence.py` has blob `917bbd225ab2ed3ad5668b38dcbb4f4c4d0c988f`. Its `vintage_fingerprints` / `same_vintage_mask` functions (lines310–342) compare per-root contract count, total OI and one underlying spot. The loader's lines1208–1216 suppress all OI-change clusters when that comparison is true. [R2]

The exact producer functions were loaded after verifying their Git blob. The [source witness](source_vintage_witness.py) and [results](source-vintage-results.json) use only fabricated contracts:

| Case | Producer calls it same vintage | Exact sum of absolute contract OI changes | Net-by-strike absolute change |
|---|---:|---:|---:|
| Two strikes: OI 50/150 becomes 150/50, same total/count/spot | true | 200 | 200 |
| Same strike/right, different expiries: identical offsetting changes | true | 200 | 0 |
| Identical OI, only spot changes | false | 0 | 0 |
| Identical control | true | 0 | 0 |
| Total rises by one contract | false | 1 | 1 |
| Only input row order changes | true | 0 | 0 |

The first case is a **real source-level collision**: distinct per-contract contents are treated as the same vintage, so the loader branch would suppress a +100 and a -100 change. No production impact frequency or affected real ticker is claimed; the store loader and live data were not executed by this witness.

Even a collision-resistant full-content fingerprint would not establish economic vintage. Two independently reported effective sessions may have equal OI, while the same OI report can be accompanied by a different underlying price. Correct source semantics require separate contract-content identity, effective OI session, report/receipt/revision identity, and consumer availability. Do not replace one unsupported timestamp inference with a stronger hash and call the provenance issue solved.

### OIF18 must take absolute values before inappropriate aggregation

The existing `matched_oi_delta` joins exact contract identifiers, then nets by root/strike/right across expirations. This is legitimate for a **net-by-strike display**. It is not the catalogue's OIF18 numerator `sum_i abs(delta_OI_i)`. With +100 at one expiry and -100 at another on the same strike, the exact numerator is 200; absolute value after netting is zero. The triangle inequality explains the general difference. No unchanged product view is automatically wrong just because it answers a different question. [R1][R2]

## 7. Current vendor conventions and source qualification

These public documentation observations were checked October 14, 2026 UTC. They are not proof of Mastermind's installed version, entitlement, captured historical availability or permission to redistribute data. They supplement, rather than rewrite, the original October 3 audit.

**Theta history OI:** documentation describes a normally daily OPRA report around 06:30 ET for the previous trading close, with some zero-interest contracts receiving no new message. [S2]

**Theta snapshot OI:** documented behaviour is latest per-contract messages from a seven-calendar-day lookback, removal after expiry, with `current_day_only=true` restricting today's messages. Consequently, one response need not itself prove a uniform economic OI vintage. [S3]

**Cboe Open-Close:** the current public conventions distinguish participant-side counts, venue-specific activity and third-party industry OI/volume. C1 exchange volume used `(B+S)/2` through October4,2019 and now uses `B+S`; historical OI date conventions also differ by exchange. Intraday files do not contain the EOD OI/total-volume fields. Apply the exact product/exchange/schema/date convention, not a universal divide-by-two or shift-by-one rule. A November8,2026 intraday-format/correction update is announced but not yet effective at this lookup. [S4]

**Cboe TBT:** current documentation describes C1 execution-level side, open/close, capacity and execution identifiers delivered T+1, not a live nationwide feed. External redistribution is prohibited by the product page. [S5]

The existing sample qualification carrier #8658 already separates account-side cleared quantity from nationwide unique contracts and keeps its EOD and TBT demonstration samples as different partial populations. We inspected its source/runbook at `1609b14088e53a754835f471e521ab138ae91572`, not its private sample bytes. Do not rebuild that acquisition lane, combine sample totals as one complete population, or publish proprietary rows. [R3]

### Required qualification before any real count calculation

Bind the exact economic contract identity (expiry, right, strike, deliverable and adjustment lineage), matched market/venue/session coverage, volume-side convention, two OI effective boundaries, their actual report/receipt times, source revisions, non-trading adjustments and the intended consumer time. A missing contract row is not an observed zero. A filename, a new build time or equal aggregate totals is not sufficient.

For OIF18, join the matched contract set explicitly, expose excluded/unmatched mass, calculate absolute changes per contract before the declared aggregation, and bind volume to the same interval/population. This descriptive ratio remains distinct from the stricter count-conservation model, which additionally needs complete relevant activity and adjustment accounting. Preserve the original catalogue definition; do not silently rename a covered-subset diagnostic as the full feature.

For OIF09, aggregate OI cannot provide the missing participant/open-close labels. Qualified classified-source observations can support a subsequent study only for their actual available venue, participant, period and release delay. Neither this theorem nor a demo sample establishes predictive value or source qualification for the six pilots.

## 8. Fable / incumbent integration brief

**Consumer outcome:** a researcher inspecting OI migration can see genuine per-contract redistribution and its uncertainty without mistaking total OI changes for identified opening buyers, specific closing trades, or dealer pressure.

The next bounded source repair belongs in the existing `positioning_persistence` producer and its tests, after current writer/effect reconciliation. Keep the current legitimate net-by-strike view. Separate effective-report identity from exact contract-content equality; preserve source-session/capture uncertainty as unavailable rather than inventing freshness. The existing OI-change display should describe a net outstanding-contract increase/decrease, not proven opening purchases or closing transactions. A separately computed OIF18 diagnostic must retain expiry-level contract changes until after absolute value.

Discriminating acceptance must include constant-total redistribution, same OI on a new proven effective session, a repeated effective report with changed spot, mismatched series populations, expiry/removal without trading, future consumer receipt, missing versus explicit zero OI, and offsetting expiries. A repair that merely makes the six synthetic examples green is not full source qualification. No new collector, store, source clock, publisher, identity service or fusion authority is authorized here.

The [machine-readable integration brief](integration-contract.json) is a passive specification and test-case catalogue. It is not a job queue, a source-admission substitute, a new schema installed into production or a permission grant.

## 9. Verification boundary

Before implementation, the 23 initially written tests failed because the reference module was absent; this is a test-first scaffold result, **not** a claim that 23 numerical bugs existed. The implemented reference passed those tests. A further denominator-specific test brings the final complete package suite to **24 tests**, zero errors/failures. The three independently authored state-enumeration comparisons exercise **1,650 exact-count geometries, 1,470 removal-interval geometries and 3,456 fixed-order/subset geometries: 6,576 total**. These are count configurations, not observed market days or independent statistical samples.

Eight deliberate prohibited mutations were detected, including dropping the empty-inventory condition, ignoring removals, missing-to-zero, using the wrong side denominator, collapsing an unknown-removal interval, erasing the subset lower bound, ignoring known order and inventing a probability. Some mutants cause valid typed-refusal failures as well as wrong-result failures; none is accepted merely for a syntax/import error. [verification-results.json](verification-results.json) retains the exact source/test hashes and outcomes.

The source-vintage witness separately covers six fabricated cases against pinned existing source. The new research tests have no production import or live data dependency. The whole Macro repository test suite has not been run for this research-only package. Independent Fabric derivation and its exact acceptance are recorded separately when actually returned and consumed; worker execution alone is not validation.

## 10. Scope, earlier accepted evidence and continuation

The 59-artifact October3 package and its published GEX arithmetic study remain accepted evidence. The gamma/proxy repairs already landed and are not redone. Q03 chronology PR #9178 remains draft at `1ed8e59ebf62945bc1493ad1d1833391ed7ff2cd`; its hosted workflows now report success, but the earlier refused independent review remains absent. The workflow reconciliation is recorded in comment6158419299. This independent OI research task is not a retry of that denied review. [R4]

No P1–P6 registration, OIF definition, empirical G0–G6 binding, #8385 methods decision, held #8555/#7328 proposal, Fable task, broker order, runtime/service configuration, trade sizing, production publication or proprietary sample was changed. A conditional count identification result is not alpha, a forecast or an installed Terminal capability.

**Next useful acceptance step:** the existing producer owner reviews the reproduced vintage collision and the source/effective-session evidence needed for its narrow repair; the research principal consumes the independently returned OI derivation and preserves its verified result. Actual data qualification precedes any application to OIF18/OIF09 studies. The research mission remains incomplete.

## References

[R1] `macro@a3f3afa1e1268908a54263043f21048c1b5bc1b4`, `research/options_intelligence/2026-10-03/options-signal-catalog.md`, blob `93a3838ca124790eb867ddcdc3da5f782f7d03e9`, especially OIF09 and OIF18.

[R2] Same source cut, `engine/positioning_persistence.py`, blob `917bbd225ab2ed3ad5668b38dcbb4f4c4d0c988f`; lines310–342,347–385,1208–1216. Source witness and results are adjacent files.

[R3] Macro #8658 at `1609b14088e53a754835f471e521ab138ae91572`: `collectors/options_free_samples.py`, `collectors/options_free_tbt.py`, `docs/runbooks/OPTIONS_FREE_SOURCE_EVALUATION.md`. Source-only inspection; private samples not accessed.

[R4] Macro #9178, exact head above, comment `https://github.com/mastermindx-market-intelligence/macro/pull/9178#issuecomment-6158419299`.

[S1] OCC/OIC, October2025, “Open Interest: Why It Matters”: https://www.optionseducation.org/news/open-interest-why-it-matters

[S2] ThetaData V3, history/open_interest, observed October14,2026: https://thetadata.net/docs/operations/option_history_open_interest.html

[S3] ThetaData V3, snapshot/open_interest, observed October14,2026: https://www.thetadata.net/docs/operations/option_snapshot_open_interest.html

[S4] Cboe DataShop, Open-Close Volume Summary, observed October14,2026: https://datashop.cboe.com/cboe-options-open-close-volume-summary

[S5] Cboe DataShop, Enhanced US Options Trade-by-Trade Execution Detail, observed October14,2026: https://datashop.cboe.com/enhanced-us-options-trade-by-trade-execution-detail
