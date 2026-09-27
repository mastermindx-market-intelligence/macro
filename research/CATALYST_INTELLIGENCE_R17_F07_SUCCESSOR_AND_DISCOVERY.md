# Catalyst R17 — F07 successor contract and options-led discovery

**State: executable research-contract candidate. Not production valuation, source admission, calibrated forecasting, recommendation policy, native Paper, or whole-programme completion.**

## Source and responsibility

Current Chairman continuation retains the central Catalyst Meta-CEO assignment. The job remains one recommendation-first cross-sector workspace with separate specialist causal models, not another financial or event stack. This unit directly resolves the previously named successor-interface question through a concrete, testable contract. It does not wait on an historical Fable title as though that established a running implementer.

Protected procedure: Mastermind `d9585ed814d758d26120592a68916b17c81f54fc`; INDEX blob `94d1af402598894372858793a5b1931019c5fa77`, Skillpack 1.0.1/bootstrap 1. Main source inspected: Macro `39c84a1a35836fcde5cf170b3237ebc118a6af4b`. Existing source carrier at entry: #8061 / `claude/sector-catalyst-recommendation-north-star-20260926`, head `dc66dba9316b1e249146bb4b9fa8bf4ac8360a14`.

The real F07 handoff at this main has blob `446886fdc0bb6d5e7a8a9c9474a30ad0190646bf` and maps to MAS-148. A fresh MAS-148 read still reports Todo/unstarted with no named assignee or attached implementation. Existing `engine/valuation_scenario.py`, blob `e632f019bb42d1dc200650535f5d1ba217f43d43`, remains fixed B-F07-1. No product file, old schema or existing branch is modified by this research reference.

## 1. Placement decision: extend F07, preserve fixed V1

**Programme design disposition:** F07 owns a successor conditional-equity assessment, not FIF's reported facts and not a sector's new local valuation service. The research reference is in `research/catalyst_intelligence_reference/f07_conditional_equity/`. Its `evaluate(packet, expected_version=...)` is an executable specification, not a registered production endpoint or trusted receipt validator.

Production placement is an extension of the existing F07 valuation/model family and its current publisher. Preserve `engine/valuation_scenario.py:compute` and `valuation_scenario.v1` byte/behavior compatibility unless their actual owner explicitly adopts a successor. The eventual owner may add a distinct versioned callable in that family after exact-source review; the reference file must not be imported as an alternative production kernel. No new API route, financial store, forecast registry, identity allocator, job queue or cross-sector ranker is created here.

The accepted production shape must bind native subject, financial inputs, economic rights, specialist forecast, model family/version, source generations, known-at cutoff, quote and validity, horizon, currency, costs, publication and policy. These are existing-owner objects. A nonempty string or a caller's `calibrated=true` is not any such proof. This reference deliberately accepts only `synthetic_reference` mode and always returns `can_rank=false`, `production_admission=false`, no recommendation and no calibrated probability.

That reference-only restriction is a verification boundary, not the product's ultimate ambition. Actual qualified probabilities and recommendations remain required by the Chairman's north star; their adoption belongs to their existing evidence, evaluation and release owners.

## 2. The financial distinction is executable

The reference provides two expressly different model families:

### Common-earnings multiple

`gross profit = annual revenue * annual gross margin`

`operating income = gross profit - operating expense`

`net common income = operating income - interest expense - income-tax expense - other income claims`

`common equity = net common income * declared common-earnings multiple`

The multiple applies to common equity earnings; it is not an enterprise multiple. It does not subtract debt or add cash again. This is a narrow declared convention, not a universal claim that every valuation model should ignore excess cash. Nonpositive common earnings require a different qualified model family, not a made-up P/E target. A missing operating expense, tax or interest amount does not become zero. An explicitly supplied tax benefit remains a model input; the code never invents one from a loss.

The earnings period is explicitly the twelve months after the valuation horizon. A next-quarter revenue/margin pair cannot be relabelled or automatically annualized. The specialist must supply the actual modeled periods under its own method. The reference's synthetic test is not a forecast of Micron or any other real issuer.

### Operating-enterprise value

`common equity residual = operating EV at horizon + horizon cash - horizon debt - other senior claims`

`common equity value = max(0, common equity residual)` under the reference's explicit limited-liability common-equity rule.

`common price at horizon = common equity value / common shares at horizon`

The EV input excludes the cash and claims being bridged, and belongs to that same horizon. A negative residual remains visible alongside the explicit floor; it is not silently relabelled a healthy zero. The reference does not estimate EV from filings or calibrate a multiple. Production requires an eligible operating model or properly scoped asset model and rights.

Pre-revenue biotechnology, mine projects and distressed claims must not be forced through the profitable-company P/E family. Sum-of-parts, risk-adjusted asset economics, legal recoveries and other families need their own accepted applicability and no-double-counting rules. The two examples do not certify every sector's model.

## 3. Financing, cash and shares change together

At the horizon:

- cash includes separately supplied operating cash after interest/tax, capital expenditure, gross equity-issue proceeds, issuance fees, new debt, repayment and distributions;
- issue proceeds equal declared issue price times newly issued common shares;
- terminal common shares equal opening common shares plus that issuance;
- ending debt equals opening debt plus new borrowing minus cash repayment;
- negative ending cash or debt is rejected rather than repaired by invented funding;
- a scenario's issue-price change updates both retained cash and operating-EV equity value.

Cash flows through the valuation horizon are a different period from earnings forecast for the following twelve months. Net income is not substituted for operating cash flow. The endpoint sums do **not** prove that the company can fund every intervening date. The output explicitly says `liquidity_path_assessed=false`; a positive final cash balance cannot be advertised as path-survival proof.

This initial reference excludes buybacks, debt conversions, preferred conversions, share exchanges, restricted/country-specific cash, contingent funding, tranche eligibility, shareholder taxes, dividend reinvestment and interim financing dates. Unknown extra fields are refused instead of being ignored. Production must model applicable events through the existing Capital Structure, rights and path-survival owners. Merely adding null fields is not implementation.

The dividend received by the entry shareholder is explicit and separate from total company distributions. It is not the final cash balance or an automatically computed average over terminal diluted shares. The reference checks that the claimed per-opening-share payment does not exceed the total distributions; this arithmetic check is not a legal entitlement receipt.

## 4. Joint outcomes, not independent averages

Each state contains its own revenue, gross margin, common-income bridge, financing, shares, valuation family and payoff. Expected payoff is calculated after evaluating each complete state. Do not multiply mean revenue by mean margin and call it expected profit.

The test uses joint states with 60% weight on revenue 1,200/margin 50% and 40% on revenue 800/margin 30%. Expected gross profit is **456**; multiplying the separate means gives **436.8**. These are authored monetary-unit examples illustrating dependence, not market predictions.

Probability handling is equally explicit. With a complete illustrative partition, weights must be nonnegative and sum to one. Duplicate state IDs and partial probabilities fail. When probabilities are entirely absent, conditional prices/payoffs remain but expected return and positive-return probability are null. No renormalization makes an incomplete scenario set appear exhaustive. A zero probability is a number, not missingness.

The output's return is `(horizon price + entry-share dividend)/reference price - 1 - stated cost fraction`. Gross and net values are separate. It is an arithmetic reference with fixed cost assumptions, not proof of executable fills, fees, capacity or risk-adjusted alpha. All examples carry synthetic identity and scenario labels.

## 5. Options can discover the case before the story exists

Consumed specialist R6: `research/semiconductors/CATALYST_R6_OPTIONS_FIRST_CONFLUENCE_2026-09-27.md` at `10c36bc3bf09c4df20085e0bc55fe3d77d1aa4c6`, blob `3919ed1246a0ba573773ec2d39829685efcb96f4`; central return #8061/5855280560. Its underlying literature, tape and full 69-test package were not independently reverified in this unit. The disposition below is central product/method design, not empirical approval of the specialist's coefficients or examples.

**Accepted for programme design:** options-led, fundamental-led and joint discovery are origins of the same security-level case. A later identified catalyst enriches the case rather than creating another exposure. Unknown dealer or institution identity prevents those actor claims; it does not make observable activity, skew or concentration useless as candidate predictors.

This refines R14's fundamental-first ablation wording. Test at least price/context-only, options-plus-context, fundamentals-plus-context, combined additive and combined-interaction models on declared eligible origins and properly separated targets. Options-only is a substantive challenger, not an ornamental layer forced to wait for every fundamental model. Combined models must earn value over the stronger standalone baseline. Preserve source-origin dependence; several displays of the same option prints are not independent confirmations.

Two distinct accepted investment-output paths may eventually reach the existing recommendation owner:

1. Specialist causal/economic states translated through qualified F07 conditional equity.
2. A separately qualified empirical equity-return distribution for an explicit horizon, source universe, executable entry, costs and benchmark.

The second is not automatically a clinical/award-outcome forecast, and it need not manufacture a fundamental price target to exist. Direction accuracy alone is insufficient: payoff/tails, uncertainty, calibration, coverage and net utility are still required. Both paths remain structured governed families behind existing Alpha/evaluation/recommendation gates. No new model or ranker is started by this decision.

The UI should reveal what is building, where and over what period, our evidence-bound interpretation, and what would invalidate it. Discovery origin and target type remain visible in the existing sector/methodology panel. Do not create a separate winning-picks application or an options-only shell.

## 6. Mining's new return narrows a different dependency

Consumed #8061/5855342109 as a specialist return, not a fresh execution here. It identifies an existing GMI identity consumer and a dated diagnostic showing missing Canadian master coverage. Therefore the central open requirement is permitted master/alias plus original/successor claim coverage through that existing consumer—not writing another Canadian allocator or widening a US-only request port by string substitution.

The report's extracted-reader execution and code publication were explicitly refused in that other lane. They are not delegated here, retried or proxied. The local R5 archive and its tests are not imported or accepted by this disposition. The R4 core already consumed remains the last exact central byte intake for Resources. Settlement rounding, record versus delivery date, and stream-payment thresholds are material economic semantics, not automatic current equity forecasts.

## 7. Tests and actual boundaries

Final local suite: **61 passed, zero failures**. Initial run failed because the reference module did not exist. A review-expanded suite then had one failing liquidity-disclosure check; it was repaired and rerun. A final export review added two failing cases for accepted Decimal/integer probability inputs: state outputs previously retained raw input types, so Decimal weights could not be JSON-exported. The reference now emits canonical decimal strings; all 61 tests and all eight mutations were rerun. Other added positive tests are not retroactively described as repaired defects.

Eight syntax-valid harmful mutations were detected by assertion failures, with zero execution errors: double balance-sheet adjustment, gross-margin substitution for common earnings, ignoring new shares, omitting issuance fees, treating company distributions as entry-share cash, missing probabilities becoming zero, rank authority becoming true, and permitting future-known inputs. Mutation failures are not eight trained-model validation results.

The tests cover both valuation families, annual-period boundaries, explicit cash/debt/share reconciliation, source/version/time/currency structural mismatches, no input mutation, missing estimates, joint weighting, finite inputs and reference-only authority. Test numbers and identities are synthetic. Production packet/rights verification, interim liquidity, real data, entire Macro/Agent OS/hosted CI, human visual acceptance and investment performance are not proved.

No R17 primary screen or Paper effect was made. R13 remains the current mockup. The unchanged Special Situations module still has blob `4e79fc0b22045917bcb1110092ad402187cddef0`; the bounded #8087 return read was empty. The R16 snapshot gap remains unresolved. This phase did not repeat its already completed diagnosis or silently take its implementation branch.

## 8. Exact next delivery

Central owns the F07 successor design/compatibility decision; this executable candidate replaces the vague instruction to find a financial bridge. The next code-integration step is exact-source independent review and an accepted F07 binding to native financial/rights/model objects, followed by a one-case consumer/export witness. Preserve fixed V1 and its readers. A synthetic envelope must never be relabelled as a native FIP.

The current Executive V2 read on the established Primary connection returned HTTP 502. No job was submitted, no receiver START is claimed, and no alternate account was used to manufacture dispatch. This does not prove the entire fabric is absent. Work here is direct principal financial-interface judgment under the active project assignment; no source lease, deployment or denied operation is transferred.

Specialists continue domain research. Central must consume their replies and advance the accepted consumer; it should not generate indefinite documents or repeat unchanged dependency requests. After an admitted real pair is bound, prospective frozen forecasts/evaluation remain distinct from successful composition. The entire Catalyst programme is still incomplete.


## 9. Reproduction and source-to-runtime boundary

From an authorized local copy of the three reference files, use the existing Python environment with pytest:

```sh
python -m pytest -q test_f07_scenario_reference.py
python check_mutations.py --report /permitted/output/f07_mutations.json
```

The first command must report 61 passing tests. The second must report eight syntax-valid mutations detected through assertion failures with zero execution errors and exit 0. The mutation runner makes temporary isolated copies and writes only its specified local report. It neither edits the accepted engine nor sends a source/model request. It is a diagnostic script, not an always-running service.

The package includes synthetic `fixtures.json` and worked outputs, plus the actual initial absence, review-failure and final verification reports. The declared future input bindings still need a real F07/FIF/identity/rights source receipt; a reference field name is not that receipt. No actual trading opportunity or calibrated win rate is generated by this unit.
