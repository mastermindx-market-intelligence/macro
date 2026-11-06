STATUS: SOURCE-AMENDED / RUN HELD

## 2026-11-06 SCIENTIFIC SOURCE REPAIR

This amendment repairs [review 5328510830](https://github.com/mastermindx-market-intelligence/macro/pull/7868#pullrequestreview-5328510830) on the original PR #7868 carrier. The prior v3 is preserved at `3ad50f9d92d560a8375fd56a350243ee3aa99a93`. Current records-repair authority is Mastermind #2028 under compatible protected pin `49c2e1d93e5e080b1671c98087a845e5beb09dd5`; it does not authorize a diagnostic run.

**RUN MAY START: NO.** Source publication is separate from independent scientific acceptance of the amended registration and the existing commissioning/data-store/start gates. The original review is not dismissed or described as an approval. No macro source, financial outcome or trial artifact was read to prepare this repair.

| Review issue | Operative repair |
|---|---|
| B1 / prior N11 | N counts anchors; effective independent N and dependent-process inferential calibration remain UNESTABLISHED. The unchanged binomial threshold is an explicitly IID reference calculation within a descriptive screen. |
| B2 | Fixed, series-specific H1/H2/H3 row groups below govern availability before event evaluation. Only H1 support determines primary membership, chaining and the null; H3 can require follow-through through t+24. |
| ORDER-input clarification | All five ORDER target/prior pairs are required, with no recursive transformation of their input rows. |
| Trough-tie clarification | Preserve the N2 inequality and use the earliest center that actually satisfies it. Keep the conservative same-vintage prior-row admissibility checks; do not relabel an earlier equal level as the trough. |

The operative rules below supersede the prior N11 independence assertion and resolve the prior universal-support wording. The numeric thresholds, separation, random seed/draw count, trough inequality, full-vintage source pins, era, rights restrictions and no-return/no-promotion boundary are unchanged. The earlier amendment tables are updated only where those source-review repairs apply.

## AMENDMENT RECORD

| Finding | What changed | Section |
|---|---|---|
| B1 | Every used row must have an admissible publication clock. Missing H1-required rows censor primary membership; missing H2/H3-only rows censor only that secondary description. Earliest/latest primary anchors use H1 support. | Per-hypothesis required support; window and era handling |
| B2 | Every three-month change is now a same-vintage difference, `Δ3_v(t) = value_v(t) - value_v(t-3)`, with the t−3 row selected at the t vintage; the query no longer keeps only initial rows. | Frozen publication-clock transformation; run contract |
| B3 | Anchors are ORDER events only, every anchor remains in the H1 denominator, and H2 and H3 describe the identical anchor set without allocating or rescuing anchors. | Hypotheses; primary endpoint |
| M1 | The sole event is the ORDER downturn crossing with the frozen sequence `+,+,≤0,−,−`; the unused opposite-direction event is removed. | Hypotheses |
| M2 | Period-month offsets are explicit; H1 inventory uses `Δ3_v ≥ 0` in at least one required month, and the first qualifying ISRATIO level trough is used. | Hypotheses |
| M3 | Counted anchors are chained at 16 period months; N below 12 makes the primary endpoint NOT EVALUABLE rather than failed. | Primary endpoint |
| M4 | The registered null remains 2,000 draws of H1-availability-admissible random months under the same separation rule and seed 20260924. The descriptive screen retains the IID-reference binomial threshold and 95th-percentile comparison. | Primary endpoint |
| M5 | The result remains DESCRIPTIVE_ONLY: about 269 months with 16-month separation cannot meet the 50-matured-anchor floor. N is counted; N_eff and dependent-process calibration are UNESTABLISHED, not inferred from spacing. The effective-cluster floors remain unsatisfied/unproven. | Primary endpoint; disclosures |
| M6 | The pass/fail path to return inspection is replaced by the exact prohibition on returns, trial work, public surfaces, and B18. | Disclosures |
| M7 | AWHMAN is excluded from availability. Null values or missing same-vintage prior rows block their series/group; the explicit H1/H2/H3 support sets determine which description is censored. | Frozen publication-availability rule; per-hypothesis required support |
| M8 | The run contract pins the exact vintages blob and v2 merge SHA, reads the blob rather than the moving path, and verifies every governing record at that SHA. | Status + authority; run contract |
| m1 | The three-month availability deadline remains frozen and discloses that it was fitted to the observed maximum lags and therefore blocks nothing today. | Frozen publication-availability rule |
| m2 | The file records that v1 merged before R6-B16-01 and the D03 matrix reached main, and that the run verifies both at the recorded merge SHA. | Status + authority; run contract |
| m3 | Process narrative about authoring history is removed from this pre-registration. | Run contract |
| m4 | The earliest possible anchor period is derived and stated as 2003-02 alongside the latest possible anchor period 2024-02. | Window and era handling |

## v3 AMENDMENT RECORD

| Ruling | Binding repair | Section |
|---|---|---|
| N1 | Same-vintage values, availability/era guards and full-vintage object pins stand. The 2026-11-06 repair qualifies the former independence claim and makes censoring hypothesis-specific without relaxing those guards. | Data precondition; per-hypothesis required support; run contract |
| N2 | The first ISRATIO level trough at `u` reads the five levels at one vintage `v*`, the first realtime_start for period `u+2`; the required order is `L(u−2) > L(u−1) ≥ L(u) < L(u+1) ≤ L(u+2)`. | ISRATIO level trough |
| N3 | The earliest anchor is 2003-05, derived once from its Δ3 inputs at 2003-03 and the `+,+` ORDER sequence at 2003-03 and 2003-04. | Window and era handling |
| N4 | The a priori null universe contains months whose explicit H1-required row groups are admissible (envelope `t−5..t+14`). Preserve `numpy.random.default_rng(20260924)`, 2,000 ordered permutations, 16-month spacing and actual N′ on exhaustion. The descriptive screen retains observed ≥ 0.60, IID-reference lower 95% bound > 0.50 and observed > null 95th percentile. | Primary endpoint |
| N5 | Apply primary H1 right-censoring first, then chain. A primary-censored anchor consumes no window; keep the next uncensored anchor at least 16 period months from the last counted anchor and skip one at less than 16. | Primary endpoint |
| N6 | Latest primary anchor eligibility uses only the explicit H1-required groups, whose envelope is `t−5..t+14`. H2/H3 support may censor their own descriptions but never moves that primary boundary. | Window and era handling |
| N7 | The three exact parquet blobs are written with `git cat-file -p <blob> > "$RUN_TMP/<SERIES>_all_vintages.parquet"`, verified against the manifest SHA-256 values, and loaded as table `vintages`. The run pins `<prereg_merge_sha>`, the squash commit of this PR, never main HEAD, and verifies governing records at that SHA. | Data precondition; run contract |
| N8 | The run opens no return, price, outcome, ledger or trial artifact at any time; the result closes the diagnostic; this pre-registration authorizes nothing after either outcome. | Disclosures; run contract |
| N9 | An H2 event is the OUTPUT Δ3 sequence `+,≤0,−` at `s−1,s,s+1` for the first `s ∈ [t,t+6]`. With the relevant secondary support complete, no event makes H2 NOT EVALUABLE; H3 is likewise NOT EVALUABLE when no `r` exists. Neither result rescues H1. | H2; H3; primary endpoint |
| N10 | The SQL computes ROW_NUMBER over all vintages before applying the admissibility filter. | Run contract |
| N11 | Superseded by scientific review B1: 16-month spacing does not establish independence. Report counted N and `N_eff = UNESTABLISHED`; the binomial quantity is an IID reference, not calibrated inference for unspecified dependence. | Primary endpoint |

## STATUS + AUTHORITY

- Operation: `prophet-us-fable-meta-ceo-20260923-001`; lane `pu_w3_prereg_v2`; commissioner: the Fable Meta-CEO seat.
- Authority: `DEC:PROPHET-US-B16-CYCLE-INTERNAL-DIAGNOSTIC-ERA`, R6-B16-01a, R6-B16-01, R6-D03-01, and the R6-PREREG-01 seat ruling. This amendment is made under `DEC:PROPHET-US-FABLE-META-CEO-DELEGATION` after an independent cross-family Opus review rejected v1 with `RUN MAY START: NO`.
- The blockers were: B1 allowed publication clocks outside the ratified era; B2 subtracted levels from different vintages and admitted a level splice; and B3 allowed an H1-failing anchor to leave the H1 denominator while OUTPUT or INVENTORY turns consumed the separation window.
- v1 merged as `0c9e30ad4da0325b135bbf621b4498174dcc875b` before R6-B16-01 and the D03 matrix commit `89a1a5798aa4694101a87691c7871607422e9bba` were on main. The run must verify this v3 file and every governing record at `<prereg_merge_sha>`.
- This file computes no empirical endpoint, rate, anchor count, or return. It specifies one proposed amended procedure. Independent scientific acceptance and existing run authority are still required before any formal read; merge plus file availability is not sufficient.

## DATA PRECONDITION

The run does not read `data/fred_vintage/vintages.parquet` (the initial-release-only, `output_type=4` store). It reads the full-vintage store at `data/fred_vintage/cycle_vintages/{NEWORDER,ISRATIO,INDPRO}_all_vintages.parquet`, produced by ALFRED `output_type=2` through `collectors/fred.py::fetch_all_vintages` in nightly lane `pu_w3_cycle_vintages_producer`. Each table has `period`, `realtime_start`, `realtime_end`, `value`, `series`, and `source_output_type`; `realtime_end` is inferred as the next vintage minus one day and is `9999-12-31` for the latest row.

The run may start only when all three files and `data/fred_vintage/cycle_vintages/manifest.json` exist on `origin/main` at one recorded `<store_main_sha>` no earlier than the first nightly that produced them. Before analysis, the run records `<store_main_sha>`, computes the three blob identifiers with `git rev-parse <store_main_sha>:data/fred_vintage/cycle_vintages/<SERIES>_all_vintages.parquet`, and verifies each file against that manifest's SHA-256 value:

```text
<blob_NEWORDER>
<blob_ISRATIO>
<blob_INDPRO>
```

No moving path, working-tree file, latest main HEAD, or unpinned manifest may supply the source.

## HYPOTHESES

### Frozen publication-clock transformation

For each period `t` and series `s ∈ {NEWORDER, ISRATIO, INDPRO}`, select the source row `value_v(t)` for period `t` with the smallest `realtime_start` `v`; then select the row for period `t−3` whose closed interval `[realtime_start, realtime_end]` contains `v` (exactly one row by construction; none blocks the month). The same-vintage change is exactly:

`Δ3_v(t) = value_v(t) - value_v(t-3)`

If the store cannot supply either row, either `realtime_start` is outside `[2002-12-01, 2025-05-15]`, or either `value` is null, period `t` is blocked for that series. Do not use a later revised `value_v(t)`, a different-vintage `value_v(t−3)`, zero, interpolation, normalization, a lagged value, or a latest-revised fallback. This rule prevents a level splice: benchmark, re-reference, index-base, and NAICS-versus-SIC changes cannot enter as fake three-month changes.

- `ORDER(t) = Δ3_v(NEWORDER,t)`.
- `INVENTORY(t) = Δ3_v(ISRATIO,t)`.
- `OUTPUT(t) = Δ3_v(INDPRO,t)`.
- `HOURS(t)` is report-only and is defined only when AWHMAN supplies both same-vintage levels; it never anchors, blocks, alters eligibility, or rehabilitates a result.
- `Δ3_v` is defined for period `t` only when both period months are within the ratified target era: t−3 is never imported from 2002-09 through 2002-11.

### Frozen publication-availability rule

A required row is available only when every row used for that row's transformation has `realtime_start ∈ [2002-12-01, 2025-05-15]`, a non-null `value`, and, for t−3, an interval containing `v`. In addition, the first publication for target month `t` must be on or before the end of the third period month after `t`. The deadline remains frozen from v1 and applies to every series and every required target month before event construction.

The deadline was fitted to the maximum observed lags across all vintage rows — 86 days for NEWORDER, 116 for ISRATIO, 93 for INDPRO, and 80 for AWHMAN — so the third month-end was the first common whole-month boundary after every maximum. That fit means it blocks no source currently known to the receipts and is retained only as a frozen publication guard, not as a claim that every future source is late. AWHMAN excluded: the availability rule never uses it because it anchors nothing. A null `value` or missing same-vintage t−3 row blocks that month for that series. Apply that absence to the explicit per-hypothesis required groups below: a missing primary group censors H1 eligibility, while a secondary-only absence censors only that secondary description.

An ORDER downturn crossing is the sole anchor event. It is a period `t` at which the ORDER sequence, in consecutive period months, is exactly `+,+,≤0,−,−` for offsets `t−2,t−1,t,t+1,t+2`. This definition is exhaustive; no opposite-direction event, other crossing, reconstructed neighbour, or runner-selected substitute exists. All FIVE target/prior pairs must be availability-admissible: for each q in `t−2..t+2`, require the first-vintage NEWORDER row at q and the uniquely selected same-vintage row at q−3. Input rows are not transformed recursively.

### ISRATIO level trough

For period `u`, set `v*` to the first `realtime_start` of period `u+2`. An ISRATIO level trough exists when one-vintage levels `L(u−2..u+2)` read from that `v*` satisfy:

`L(u−2) > L(u−1) ≥ L(u) < L(u+1) ≤ L(u+2)`

The query returns these five levels. A candidate's qualifying month is its CENTER u only when the displayed inequality holds; select the earliest qualifying center in `[t,t+12]`. Do not shift that center to an earlier equal minimum. For example, levels `[3,2,2,3,4]` qualify the center at index 2; index 1 is not the qualifying center. The inequality allows equality on the left and requires a strict rise on the right.

Preserve the existing conservative prior-row admissibility guard: for EACH q in `u−2..u+2`, require both L(q) and the row for q−3 at the SAME v*, with a unique interval containing v*, non-null values, ratified periods/publication clocks and the existing target-month first-publication deadline. These prior rows qualify support only; they do not enter the level inequality and are not transformed recursively. The complete fixed H1 support is checked before searching centers, so a blocked earlier candidate cannot be bypassed by choosing a later trough. A level trough is never an anchor.

### H1 — Order flow leads inventory turns while output contracts

At an ORDER downturn crossing `t`, H1 holds when both conditions hold:

1. INVENTORY has `Δ3_v ≥ 0` in at least one of period months `t,t+1,t+2,t+3`.
2. The first qualifying ISRATIO level trough in period months `[t,t+12]` exists, and OUTPUT has `Δ3_v < 0` in at least one period month from `t` through that trough's period month.

Every offset in this section is a period-month offset, not a publication-date or trading-time offset. Availability applies to every H1-required group below before any H1 event/outcome test. An anchor lacking an H1-required reading is RIGHT-CENSORED and excluded from N, never an H1 failure. Missing H2/H3-only groups cannot cause that exclusion.

### H2 — Output follows order flow with delayed inventory pressure

On the identical ORDER-anchor set used by H1, find the first period month `s ∈ [t,t+6]` whose OUTPUT Δ3 signs at `s−1,s,s+1` are exactly `+,≤0,−`; that is the OUTPUT event. H2 holds when INVENTORY has `Δ3_v > 0` in at least one period month from `t` through that crossing. If no `s` exists, H2 is NOT EVALUABLE for that anchor and is reported as such, not as a fail. H2 is a secondary, non-rescue description. An unavailable required reading makes its H2 description RIGHT-CENSORED, without changing anchor membership, H1, N, or the primary endpoint.

### H3 — Recovery restores output before inventory pressure clears

On the identical ORDER-anchor set used by H1, find the first period month `r ∈ [t,t+6]` with `ORDER Δ3_v > 0`. If no `r` exists, H3 is NOT EVALUABLE for that anchor and is reported as such, not as a fail. When `r` exists, H3 holds when OUTPUT has `Δ3_v > 0` in `[r,r+9]` and INVENTORY has `Δ3_v < 0` in a period month from the first qualifying positive OUTPUT month through nine period months after that month. H3 is a secondary, non-rescue description. An unavailable required reading makes its H3 description RIGHT-CENSORED, without changing anchor membership, H1, N, or the primary endpoint.

## PER-HYPOTHESIS REQUIRED SUPPORT

All ranges below are inclusive period-month ranges. A required group is a set of exact series/period/vintage row references, not permission to fill a rectangular all-series panel. Repeated requests selecting the same exact source row are the same operand, not independent observations. In particular, T(t+4) already includes D(ISRATIO,t+6); it cannot be treated as an H2-only missingness case.

- D(series,q): the two rows for the same-vintage change at target q, selected exactly by the transformation rule (first-vintage target q and unique interval-containing prior q−3). Check the existing values, target/input periods, publication-clock window and target deadline. Do not apply another three-month transform to q−3.
- T(u): the five ISRATIO levels at the single v* first published for u+2, PLUS each level's conservative q−3 admissibility row at that same v*, as specified above. Prior rows do not change the trough inequality.

| Description | Fixed required groups, before inspecting signs or events | Support envelope |
|---|---|---|
| H1 / primary eligibility / null availability | D(NEWORDER,q), q=t−2..t+2; D(ISRATIO,q), q=t..t+3; D(INDPRO,q), q=t..t+12; T(u), u=t..t+12 | t−5..t+14 |
| H2 on the counted H1 anchors | D(INDPRO,q), q=t−1..t+7; D(ISRATIO,q), q=t..t+6 | t−4..t+7, in addition to already-qualified H1 support |
| H3 on the counted H1 anchors | D(NEWORDER,q), q=t..t+6; D(INDPRO,q), q=t..t+15; D(ISRATIO,q), q=t..t+24 | t−3..t+24, in addition to already-qualified H1 support |

The envelopes describe extreme periods, not a requirement to read every series at every enclosed month. The fixed groups determine availability without inspecting signs. Report periods with missing ORDER-definition operands as UNCLASSIFIABLE_ORDER periods, not observed ORDER events or H1 failures. Among observable ORDER crossings, missing remaining H1 support causes primary RIGHT-CENSORING before chaining; complete support permits entry into the counted primary population. The null universe uses that SAME H1 availability mask without requiring an observed ORDER crossing. Neither H2/H3 event values nor their additional availability enter H1 eligibility, N, chain order or the null.

For each counted anchor, apply each secondary's complete fixed group mask BEFORE looking for its event. If any required secondary group is absent, report that secondary RIGHT-CENSORED with the exact group and reason. If all groups qualify but no s/r exists, report that secondary NOT EVALUABLE under N9. Otherwise evaluate the specified secondary condition. The conservative full group mask does not shrink after seeing an early event or a favorable result.

H3's maximum support follows directly from its frozen horizons: r may equal t+6; the first positive OUTPUT may be r+9=t+15; INVENTORY follow-through may then extend through t+24. Beyond-era rows are unavailable, not zero, a false event or permission to extend the era. Missing this tail leaves an otherwise qualified H1 anchor in N. H2/H3 statuses and evaluable/censored counts are reported separately on the identical counted primary population; they never allocate new anchors, consume another chain window or rescue H1.

### Deterministic source-only boundary fixtures

These are invented availability masks and integers, not observations from ALFRED or a diagnostic run.

| Constructed case | Required result |
|---|---|
| Every H1-required group is admissible through t+14; an abstract qualifying ORDER anchor is at t. H3's constructed r=t+6 and first positive OUTPUT=t+15 require INVENTORY through t+24, but rows after t+14 are unavailable. | Retain the anchor in H1/N and its original chain/null availability. Mark H3 RIGHT-CENSORED; do not mark a false H3 event or drop the H1 anchor. |
| Add the missing H3-only groups through t+24, leaving all H1 rows and values unchanged. | H3 availability may change; H1 membership, N, chain and null universe remain exactly unchanged. |
| Remove a follow-through row required by H1 from a known ORDER anchor. | Censor the primary anchor BEFORE chaining; it consumes no 16-month window. Secondary completeness cannot restore it. Missing ORDER-definition inputs are separately UNCLASSIFIABLE_ORDER. |
| An H1-admissible anchor lacks the INDPRO prior row at t−4 selected at the first publication vintage of t−1, required only by D(INDPRO,t−1) for H2. | H2 is RIGHT-CENSORED; primary membership, N, chain and null remain unchanged. |
| ISRATIO one-vintage levels are 3,2,2,3,4 at five successive periods. | The qualifying center is the middle period (index 2), not the first equal minimum (index 1); preserve the exact N2 inequality. |

## PRIMARY ENDPOINT

- **Primary hypothesis:** H1. The endpoint is the H1 concordance rate among counted, availability-admissible ORDER downturn-crossing anchors. Anchors are ORDER events only; every admissible anchor enters the H1 denominator exactly once.
- **Estimator:** H1 concordant anchors divided by `N`, where `N` is the number of counted anchors. An H1 RIGHT-CENSORED anchor is excluded from N and reported separately as neither concordant nor failed. Secondary-only censoring never excludes it.
- **Censoring order and chain rule:** Apply H1 RIGHT-CENSORING first. Then walk uncensored ORDER anchors forward in period time. Keep the first anchor, skip every later anchor within 16 period months of the last COUNTED anchor, and keep the first at least 16 months after it; repeat. A primary-censored anchor consumes no window. H2/H3 describe this identical counted set with their own statuses. Null draws use the same H1 availability rule and spacing, not the same realized ORDER-anchor identities.
- **Null:** The a priori universe is every period month whose explicit H1 groups are all admissible (envelope `t−5..t+14`), fixed before inspecting signs/outcomes. Secondary groups do not enter it. Instantiate `numpy.random.default_rng(20260924)` once. For each of 2,000 draws, in order, obtain one random permutation of that universe, accept a month only if it is at least 16 period months from EVERY already accepted month (permutation order is not chronological), until N months are accepted. Compute H1 concordance/N′ using the actual accepted count on exhaustion; a zero N′ is NOT EVALUABLE and never becomes a rate or a passed comparison. Record N′ for every draw. The exact N2 inequality, including its permitted ties, is identical in observed and null computations. This registered reference distribution does not itself establish serial independence or calibrated Type-I error.
- **Threshold:** Preserve all three registered numeric comparisons: observed rate ≥ 0.60; one-sided 95% IID-binomial lower reference bound > 0.50; observed rate > null-draw 95th percentile. All three are required for DESCRIPTIVE_SCREEN_PASS. This is a descriptive registered screen, not acceptance of H1 as a calibrated predictive, causal or inferential claim. For k concordant anchors out of N, the IID reference is 0 when k=0, otherwise the 0.05 quantile of Beta(k,N−k+1), the Clopper–Pearson calculation under an independent Bernoulli model. Its exactness is conditional on that model, which this macro design has not established.
- **Evaluability:** If `N < 12`, the primary endpoint is NOT EVALUABLE. That is a registered result, not a failure or a pass.
- **Honest N and reporting:** Report counted N, primary RIGHT-CENSORED count, chain/skipped anchors, secondary statuses, IID-reference binomial bound and null 95th percentile. Report `N_eff = UNESTABLISHED` and `DEPENDENCE_CALIBRATION = UNESTABLISHED`. Even disjoint follow-through does not prove independent macro episodes; H1's full support at t−5..t+14 overlaps an anchor 16 months later at offsets 11..14. Do not estimate effective N from spacing or mechanically substitute an estimated N_eff into a binomial formula. H2/H3 cannot rescue H1.
- **Dependence counterexample (source-only):** Twelve disjoint observations driven by one common Bernoulli(0.5) shock have counted N=12 but perfectly dependent outcomes. On their all-success outcome the IID lower reference is `0.05**(1/12)≈0.77908`, exceeding 0.5 with probability 0.5, not 0.05. This disproves a guarantee from disjoint windows; it does not estimate actual macro dependence or any empirical endpoint.
- **Descriptive status:** The result is unconditionally `DESCRIPTIVE_ONLY` under this registration. The governing 50-matured-anchor and effective-cluster floors are not waived: about 269 months with 16-month separation cannot meet the 50-anchor floor, and no effective independent-N floor or dependent-process calibration has been established. Report counted N and the explicit UNESTABLISHED fields. The window ends 2025-05-15; later periods remain OUT of window. Any proposed inferential method or promotion study needs a separately accepted forward-only registration before its outcomes are examined; no post-result retuning is allowed here.

## WINDOW AND ERA HANDLING

- Ratified publication-clock window: every row used for any purpose must have `realtime_start ∈ [2002-12-01, 2025-05-15]`. This binds target rows, input rows, t−3 neighbours, level-trough neighbours, and every follow-through month.
- Excluded era `1997-04-15 → 2002-11`: pre-NAICS and reconstruction regimes are mixed. In particular, INDPRO first published for 2002-09 and 2002-10 before the December-2002 G.17 NAICS conversion is inadmissible, so importing it as a 2002-12 transform input is forbidden.
- Excluded era `2025-05-16 → latest`: the post-2025 M3 benchmark, INDPRO's 2025-11-24 conversion, and UNKNOWN ISRATIO benchmark applicability make a new era that is too short and partly unknown. In particular, NEWORDER and ISRATIO publications for 2025-04 and 2025-05 may occur after 2025-05-16 and cannot be used.
- RIGHT-CENSORING: missing, null, ambiguous or out-of-era H1-required rows censor the primary anchor and exclude it from N BEFORE chaining. Missing H2/H3-only groups censor only that secondary description. Report the hypothesis, series, period/vintage group and reason. A censored description is neither a success nor a failure. Fixed per-hypothesis availability masks are evaluated before signs/events.
- Earliest possible primary anchor: **2003-05**, subject to actual H1-group availability. Its earliest ORDER target is t−2=2003-03 and that target's prior is 2002-12; this fixes the earliest possible period without importing pre-era inputs. The required `+,+` signs are at 2003-03/04. This source-calendar bound is not an observed anchor count or event claim.
- Latest primary-eligible month: the run computes and reports the last t whose explicit H1 groups (envelope `t−5..t+14`) are all admissible. Secondary completeness never moves that boundary. H3 may require rows through t+24, all within the SAME ratified era; if unavailable, report H3 RIGHT-CENSORED while retaining an eligible primary anchor. No values/signs/outcomes enter availability.
- The approximately 269-month span is source-clock information, not an outcome observation. No row outside the era may be selected, transformed, classified, or used to repair a blocked row.

## DISCLOSURES

- This is a macro-only, internal-only, retrospective diagnostic. It has no issuer, issuer mapping, sector population, or trade. Aggregate macro series cannot represent failed or delisted firms, and survivorship is disclosed as a limitation rather than claimed away by macro-only construction.
- Every FRED/ALFRED leg remains internal-only. Neither the diagnostic nor its result may appear on a public or user-facing surface.
- `AWHMAN` is diagnostic-only. It may be reported beside anchors when available but never blocks an anchor, defines eligibility, or changes H1, H2, H3, or the null.
- The diagnostic can describe publication-clock timing among order flow, inventories, and output. It cannot prove causation, select a sector, admit exploratory work or a trade, support a position or sizing rule, establish capacity, or make a market-direction or profitability claim.
- Neither a pass nor a fail authorizes return inspection, exploratory work, a public surface, or B18 work; the diagnostic is machinery evidence only (DEC:PROPHET-US-B16-CYCLE-INTERNAL-DIAGNOSTIC-ERA). The run opens no return, price, outcome, ledger or trial artifact at any time; the result closes the diagnostic; this pre-registration authorizes nothing after either outcome.

## RUN CONTRACT

The run remains held: **RUN MAY START: NO** on this source amendment. Before any formal read, the amended registration requires independent external scientific acceptance under R6-PREREG-01 and the recorded review, an actual scoped commissioning/start decision from the existing owner, this PR's accepted merge, and the DATA PRECONDITION. Merge, green CI, a source self-check or file presence alone satisfies none of the other gates. No named old author is made a permanent approver, and no current independent acceptance or active runner is claimed.

Once all gates are actually satisfied, the diagnostic is read-only with respect to every source. It records `<prereg_merge_sha>`, the actual squash commit of this PR supplied in its args, never main HEAD, and verifies this amended file and every governing record at that SHA. Placeholder source/blob/merge pins below remain unfilled until those canonical facts exist; this repair does not invent them.

For each SERIES in `NEWORDER,ISRATIO,INDPRO`, it records the pinned blob, reads exactly that object, verifies the manifest SHA-256, and loads the result into table `vintages`:

```text
git rev-parse <store_main_sha>:data/fred_vintage/cycle_vintages/<SERIES>_all_vintages.parquet
git cat-file -p <blob_NEWORDER> > "$RUN_TMP/NEWORDER_all_vintages.parquet"
git cat-file -p <blob_ISRATIO> > "$RUN_TMP/ISRATIO_all_vintages.parquet"
git cat-file -p <blob_INDPRO> > "$RUN_TMP/INDPRO_all_vintages.parquet"
```

Required source query, where `target_vintages` is the first-vintage relation:

```text
WITH target_vintages AS (
  SELECT series, period, value, realtime_start, realtime_end
  FROM (
    SELECT
      series,
      period,
      value,
      realtime_start,
      realtime_end,
      ROW_NUMBER() OVER (
        PARTITION BY series, period
        ORDER BY realtime_start ASC, realtime_end ASC
      ) AS vintage_rank
    FROM vintages
    WHERE series IN ('NEWORDER', 'ISRATIO', 'INDPRO')
  ) AS ranked_first_release
  WHERE vintage_rank = 1
    AND realtime_start >= DATE '2002-12-01'
    AND realtime_start <= DATE '2025-05-15'
)
SELECT
  target.series,
  target.period AS target_period,
  target.value AS target_value,
  target.realtime_start AS vintage,
  prior.period AS prior_period,
  prior.value AS prior_value
FROM target_vintages AS target
LEFT JOIN vintages AS prior
  ON prior.series = target.series
 AND prior.period = target.period - INTERVAL '3 MONTHS'
 AND prior.realtime_start <= target.realtime_start
 AND prior.realtime_end >= target.realtime_start
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY target.series, target.period
  ORDER BY prior.realtime_start DESC, prior.realtime_end ASC
) = 1
```

The inner ROW_NUMBER runs first over all vintages; only then does the outer predicate retain rank 1 and apply `[2002-12-01, 2025-05-15]`. No minimum-`realtime_start` filter or row-number qualifier may be applied to `prior`. A missing LEFT-JOIN result, null `value`, out-of-era publication clock or non-unique eligible interval blocks the corresponding series-month/group. The integrity phase must reject duplicate interval matches BEFORE using the query's final row selection; its tie ordering is not permission to select silently among ambiguous source rows. Per-hypothesis support determines which description is censored.

Required integrity checks report only counts, dates, series and completeness for each exact group; no endpoint is computed before the start gates are satisfied and every relevant group is classified available or blocked. Resolve the H1 eligibility mask independently; a censored H2/H3 mask does not block H1 computation on its qualified anchors. The future authorized run writes primary anchors/censoring/chaining, separate H2/H3 statuses, counted N, `N_eff=UNESTABLISHED`, `DEPENDENCE_CALIBRATION=UNESTABLISHED`, IID-reference and null/threshold diagnostics to `research/prophet_v4/r6_program/wave2/CYCLE_A_MACRO_DIAGNOSTIC_RESULT_v3_2026-09-24.md`. No result artifact is created by this amendment. The run opens no return, price, outcome, ledger or trial artifact at any time.

## EVIDENCE

- Independent review basis: v1 was rejected with `RUN MAY START: NO`; B1, B2, and B3 were blockers, and M1–M8 plus m1–m4 are folded above without softening.
- v1 is the registered first version at merge `0c9e30ad4da0325b135bbf621b4498174dcc875b` and remains unchanged. That merge preceded R6-B16-01 and D03 matrix commit `89a1a5798aa4694101a87691c7871607422e9bba` on main. The closed v2 lane never supplied a merge SHA; this run verifies v3 at `<prereg_merge_sha>`.
- R6-B16-01a §2 supplies the era `2002-12 → 2025-05-15`, the excluded eras, and INDPRO substitution. R6-B16-01 §1 records that AWHMAN anchors nothing.
- The v1 lag receipts are maximum publication lags only: NEWORDER 86 days, ISRATIO 116, INDPRO 93, and AWHMAN 80. They establish the frozen deadline and do not override era admission or establish anchor availability.
- `collectors/fred.py::fetch_all_vintages` at the base implements ALFRED `output_type=2`, melts the vintage matrix to long form, adds `series` and `source_output_type`, and infers `realtime_end` as the next vintage minus one day with `9999-12-31` for the latest row. This source-contract check opened no parquet file.
- At authoring time, the nightly producer and the three committed files are a run precondition rather than an existing source read. No `data/fred_vintage/`, `data/prophet/`, `data/prophet_arena/`, `data/prophet_stage_shadow/`, return, outcome, ledger, scoreboard, or trial artifact was opened in this amendment lane. No endpoint, rate, count of anchors, or return was computed or estimated.

## GAPS + MUST-NOTS REFUSED

- The exact calendar day of the December-2002 G.17 NAICS conversion is not established by the governing records; no day-level conversion inference is made. The source era boundary remains 2002-12-01 through 2025-05-15 as ratified.
- No fallback, interpolation, revised row, different-vintage subtraction, moving-path source read, initial-release store, latest-revised level, or runner choice is admitted. The three full-vintage files and manifest must first be present on `origin/main` at the recorded `<store_main_sha>`.
- No endpoint result is claimed, no current-regime claim is made, no issuer or sector is selected, no exploratory work or public surface is admitted, B18 remains blocked, and no production DDL is applied.

## SUPERSESSION

This source-amended v3 is the proposed replacement for prior v3, v2 and v1, subject to the independent scientific-acceptance and actual start gates above. No earlier version authorizes bypassing the outstanding review. v1 remains the registered first version; v2 was never merged (PR #7857 closed unmerged); no endpoint was computed under v1 or v2. This amendment computes no empirical endpoint.
