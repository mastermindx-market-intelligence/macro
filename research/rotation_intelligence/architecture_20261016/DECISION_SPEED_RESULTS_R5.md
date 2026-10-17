# R5 results — react to new information, not just refresh more often

Date: 2026-10-17. Existing PR #9507 / `sector-rotation-intelligence`. The [design](DECISION_SPEED_DESIGN_R5.md) was published at `f7162ff8db6906375abb6a8f5b43845a18b976ec` before running the new simulation. All 64 declared cells, 512 synthetic paths per cell, are in [the full grid](decision_speed_grid_r5.csv). These are controlled invented price processes, **not market returns, a validated trading strategy, an optimal rebalance interval or evidence of anticipating actual crowding**.

## 1. What changed in the research capability

The price-only baseline can now be tested with **separate signal-memory, review-cadence, source-delay, confirmation and execution controls**. All policies share routine twenty-session maintenance, and daily review does not automatically force daily rebalancing of an unchanged target. New targets execute at the next close after the observed signal; the intervening return belongs to the old holdings. The bill proxy is a traded security, not cost-free settlement cash.

This distinguishes two different proposals: receiving useful evidence earlier, and acting more often on the same type of evidence. It also supplies specific falsifiers for a future implementation through existing source, evaluation and portfolio owners. No new event detector, production state machine, scheduler or signal service is created.

## 2. Exact timing: a fast screen can still carry a slow signal

For the prescribed deterministic relative-log-return reversal from -d to +d, a strict positive L-interval sum first flips after floor(L/2)+1 new intervals. Thus L=63 requires32 new intervals and L=20 requires11. The formula is specific to this witness; it is not a universal stock-market delay law.

Review cadence, source lag, confirmation and execution then determine a later actionable time. For example, measured from the last old-regime session0:

| Return intervals | Source lag | Review cadence | Confirmations | First source crossover | First eligible review | First execution close |
|---:|---:|---:|---:|---:|---:|---:|
|63|0|1|1|32|32|33|
|63|5|1|1|32|37|38|
|63|0|20|1|32|40|41|
|63|5|20|1|32|40|41|
|63|5|20|3|32|40|81|
|20|0|1|1|11|11|12|
|20|0|1|3|11|11|14|
|20|5|20|1|11|20|21|

The two twenty-session examples illustrate that source delay and review delay do not always add mechanically: a delay can fit inside existing review-grid slack. None of these integers is a real timestamp or a proven production latency.

Repeated reads of the same source version never count as multiple confirmations. Distinct observations are still not automatically statistically independent; the confirmation rule here is a policy heuristic, not a calibrated likelihood ratio.

## 3. Durable synthetic rotation: earlier exposure did not guarantee better net wealth

The following is the complete four-policy comparison for the fixed durable-switch world, no source lag, and an assumed5-basis-point cost per actually traded security dollar. Starting capital is1, investment length200 synthetic intervals. The response metric is the first post-onset accepted target allocating at least two slots to the three newly advantaged assets. It is an evaluation description, not a forecast or a hindsight input.

| Policy | Mean target-response delay among arrivals | No arrival by terminal | Mean target membership changes | Mean net terminal wealth |
|---|---:|---:|---:|---:|
|63-interval signal,20-session review|61.08|5.86%|7.46|1.124733|
|Same63-interval signal, daily review|44.20|0.20%|53.39|1.121195|
|20-interval signal, daily review|18.95|0.00%|95.36|1.083230|
|20-interval signal, three distinct-review confirmation|33.99|0.78%|20.06|1.110097|

The shorter signal responds much faster in this generator but repeatedly changes exposure. Waiting for three successive target confirmations cuts that churn substantially, but adds delay and still does not beat the slow control in this cell. The same-signal daily-review comparison has a mean log-wealth difference of -0.003510 with paired Monte Carlo standard error0.002141; this small difference is not presented as a universal statistically decisive financial result. The shorter-signal comparison is -0.038062 with Monte Carlo standard error0.003157 under this particular generator.

Some paths already hold the new group before onset because the noisy observed ranking selected it. Prepositioned fractions are reported in the full grid (about0.59%,0.39%,3.52%,2.54% for these four policies). First exposure can therefore reflect prepositioning, and it does not establish persistent or correctly predicted leadership. Delay means are never presented without non-arrival rates; main wealth results include all paths.

At the predeclared25-basis-point stress cost, the same four mean terminal wealth values are1.104622,1.037838,0.936759 and1.062506. These costs are assumptions, not estimates of sector-ETF execution. Risk exposure, bill occupancy, drawdown and turnover are reported alongside wealth; differences are not automatically risk-adjusted alpha.

## 4. No-edge, gradual and false-start worlds are retained

In the equal-drift/no-edge world, the shorter daily signal changes target membership about100.53 times over the200-interval investment period, versus7.79 for the slow control. At the25-basis-point stress cost, mean terminal wealth is0.851404 versus1.004669. The three-review policy reduces changes to19.72 and ends at0.976791. These are turnover consequences in a specified noise world, not proof that all real switches are false signals.

The gradual-change and twelve-interval headfake worlds are also retained in full. Across this finite chosen grid, all three faster variants have negative mean paired log-wealth differences relative to the slow control. **That does not establish twenty-session review as optimal**: the generator, selected signal types, change timing, candidate-confirmation construction, risk exposure and cost assumptions are fixed and narrow. Nothing was tuned after seeing these results to manufacture a successful fast strategy. No information-leading fundamental/macro/flow signal is included, so this cannot falsify its possible incremental value.

Source lag remains separately visible. In the durable world with5-basis-point costs, the short-signal mean response delay rises from18.95 to23.21 when the observation is delayed five sessions. Faster decision scheduling cannot recover unavailable evidence. This controlled use of lagged observations does not authorize accepting stale inputs in a production reader whose contract refuses them.

## 5. Exact economic hurdle for a switch

Starting fully invested in A with wealth1, switching completely to B at the same proportional cost c for purchases and sales leaves `(1-c)/(1+c)`. If B then has a constant relative log advantage delta for H intervals and both alternatives pay the same final sale rate, switching wins only when:

`H*delta > log((1+c)/(1-c))`.

The inequality is strict. At c=.0025 and a hypothetical delta=.001, the break-even horizon is slightly above5 intervals, not exactly5. The example concerns deterministic relative wealth and one switch; noisy forecasts, downside, overlap, market impact and mandate constraints require additional treatment. It is not a rule to size trades or a substitute for the existing portfolio owner.

The future research policy should ask whether the expected remaining opportunity compensates for actual changing exposure, rather than assume that any new top-three ordering deserves a complete rebalance. A buy/hold buffer or partial adjustment is a candidate to register and test separately, not an amendment inserted into this already-run grid. The primary literature motivations and their transfer limits are in the frozen design.

## 6. Concrete architecture requirements adopted for this supplement

- **Keep review and trading cadence separate.** The existing product can reassess on new information without asserting that every review should generate a transaction. Routine weight maintenance is a different decision from replacing holdings.
- **Expose the source of delay.** Distinguish economic observation, first permissible availability, estimator memory, review time, confirmation policy and first executable action. Do not call a signal early because the page refreshed recently.
- **Count evidence versions, not polls.** Confirmation must bind changed original observations and retain counterevidence. Repeated publication of one value is not independent support.
- **Qualify speed on economics as well as detection.** Report paired net wealth, downside, turnover, false-start costs and missed/late exposures together; never score only eventually successful rotations.
- **Faster technicals are a baseline, not the north star.** The advanced challenger needs earlier independent economic information or a demonstrably better inference/action rule. Macro labels, industry-capacity narratives and flows do not earn that status by being wired in.
- **No production timing recommendation yet.** The actual source rights/availability, empirical target, native study admission, costs/capacity and independent review remain prerequisites. Existing DNR constructions and native H1/H2/H3 are untouched.

These requirements belong in the existing input/measurement, evaluation and portfolio contracts. They introduce no new live detector, ranker, scheduler or risk veto.

## 7. Executed verification and test repairs

The initial three appropriately shaped placeholders failed three intended assertions: strict reversal timing, costed switch wealth, and equal-return cash behavior. The implemented subject then passed27 tests. Seven deliberate mutations each failed its intended assertion with zero unrelated errors: future prices, ignored source lag, wrong return interval count, same-version repeated confirmation, free bill trading, a new terminal-date trade, and invented investment authority.

One initial future-data mutation survived because the first test shifted all future assets and the bill proxy together, preserving the relevant comparison. The fixture was strengthened to change only a different sector subset. A separate first cost mutation changed array slices too broadly and caused a broadcasting error; it was scoped to the cost function before being counted as a valid falsifier. No simulation parameter or empirical rule was adjusted to make an investment result look better.

The vectorized self-financing calculation uses a contraction bounded by c<=.01 and checks its budget residual. It was compared against the **unchanged, published R2 scalar rebalance function** on384 invented portfolios/cost cases. Maximum relative discrepancy was4.285928635281368e-16. This is mathematical equivalence under the stated model, not a product-portfolio test.

The actual published subject, tests, counterfactual script and grid were fetched at `822c046a934d9e6a6d8c259da878d724d49a7d27` and run on M2 Python3.14.7/NumPy2.5.2. Local environment was Python3.13.5/NumPy2.3.5. All27 tests and seven intended counterfactuals reproduced. The full nine-decimal CSV matched after **line-ending normalization only** (CRLF-to-LF); no numerical rounding or field exclusion was added to obtain that match.

| Artifact | SHA-256 |
|---|---|
| decision_speed_r5.py | `50cf240a59400c73c1a90d2acebf43ebae0b154b24d561eec584ef12dbdfa637` |
| test_decision_speed_r5.py | `222e73224907cf40f0ebfb1d04d3f7517b69d394569c13cd4f4ee0d0d254930b` |
| check_speed_mutations_r5.py | `3226efab2bba8575c9cc63b71d82d22c35bda9efa57127d1bdbb3099e28dd55b` |
| Published grid, LF | `328553cf278ed164164ae134713dd28b893bd66c00f406ae1a87a977c01755b6` |
| Local raw generated grid, CRLF | `d9fbed37ed7579f07eaa8c7895c817c557ddf022a929e78e1e85df349cf885e6` |
| Local/M2 mutation output | `9fb844bbb9a66c3939936d87219c4100c451bc9b5ece309e9585a4bc1a7fcf37` |

M2 evidence: `/Volumes/Mastermind/research/rotation-intelligence-census-20261016-sol-c1/r5-speed/`, including source and numeric verification, test log and reproduced output. The final package readback is recorded after this document's commit rather than claimed in advance. Author verification is not independent release approval, native size/power qualification, or financial validation.

## 8. The new child is not reconciled; do not invent completion

A separate economical arithmetic-fixture child was submitted once: `rotation-r5-20261017-c1-cadence-fixtures`, original Web root/parent `rotation-intelligence-census-20261016-sol-c1`. Its packet permitted supplied arithmetic only, not sources, archives, network, product edits or delegation. It is distinct from the older refused source and final-review actions.

Its response remains unavailable. Same-ID status returned `ACTIVE_OR_WAITING` with unverified controller lineage, null reported root/parent, worker_state UNKNOWN and retry_authorized=false. The original process-output session could not be found. A bounded original-owner diagnosis returned `original_run_observation_unconfirmed`; the exposed `check-terminal` path returned unsupported operation/root and was found to route to an a04-specific handler, not a demonstrated generic reconciliation capability for this Web run.

No result was consumed or accepted; no cancel, duplicate submission, account/provider change or replacement child occurred. No STARTED/RUNNING or terminal-completion claim is made. Preserve this exact unreconciled dispatch/return and the [carrier record](https://github.com/mastermindx-market-intelligence/macro/pull/9507#issuecomment-6234112703). The parent-owned research evidence above does not close or impersonate that child. Do not claim all children are terminal, and do not claim a background Web session.

## 9. Mission frontier

The R5 timing diagnostic is published and verified. The broader allocation programme is still incomplete. The original source-qualification operation is blocked and unretried; no new source-owner disposition was received. The existing thirteen-input archive, BIL coverage mismatch and missing actual source/consumer qualification remain as last verified in R3. The original final independent-package review still lacks a verdict after its provider403.

Next material steps require the corresponding real boundary to resolve: supported same-run child reconciliation; an actually permitted source/consumer qualification path; and independent final review with exact-head CI. R5 does not reopen native P1/P2/P3, write Trial/Vault state, acquire data, activate a collector or produce a live score, trade or deployment. Do not add another synthetic grid merely to avoid those real dependencies or confuse file count with capability.
