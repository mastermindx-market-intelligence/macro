# Independent review: six-pilot study specification v1

**Verdict: PASS for principal engineering-design acceptance, with empirical gates held.** No blocking design correction remains in the reviewed versions. This is not acceptance of a fitted model, a qualified dataset, an accepted empirical preregistration, a power result, a completed hypothesis test, or production authority.

Review date: 2026-10-03. Operation: `options-intelligence-deep-research-20261003-astra-001`. Scope: finite read-only mathematical, causal, and statistical execution review. The writer's specification files were not modified by this reviewer. No empirical fit, provider call, order, production effect, or second parquet decode was performed.

## Exact reviewed artifacts

| Artifact | SHA256 | Git blob |
|---|---|---|
| `PILOT_STUDY_SPEC_V1.md` | `f439d6df16f5437ce6bf996fefe1df891927f5539ece368d44cbe9098bf971f8` | `db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0` |
| `pilot-study-spec.v1.json` | `e30796c158da18cffe1b581463ba6820ff33e9acbe8a4248b3fc068e67f70317` | `fc00aa33b11c26be9fa0ca6a4b7c0280f73dab81` |

These are the writer's frozen versions after the final P6 quote-size-side clarification. The JSON parsed successfully. Its long substantive contract strings are preserved literally in the Markdown; the separate JSON claim-ceiling string expresses the same narrower authority boundary. All seven declared input-manifest SHA256 values matched the local reviewed input files. This consistency check does not independently attest those inputs' external source or deployment claims.

The review applies the latest principal decisions, rather than the earlier fixed-six-stock/native-target-forecast draft. Principal decisions communicated during review include the dynamic causally admitted incumbent panel, explicit incumbent-information research adapter, actual-fill P6 primary, minimum-20-block validation duration, and the final centered score formula. The centered formula is a deliberate fixed design choice distinct from the previously suggested `score/100` under a no-intercept ridge adapter; no outcome-driven selection is inferred.

## 1. Population and incumbent comparison

**Accepted:** P1–P4 use a frozen *rule* for a dynamic PIT population: the latest causally consumer-admitted incumbent US-common-stock buy-pool revision at formation, followed by declared identity, price, liquidity, option-volume, contract, source, and history gates. The rule does not substitute the inspected 69-name board for historical population membership. Failed rows remain in the census, with source and eligible-population digests, selection lineage, and ordered exclusion reasons. A revision above the proposed 200-row bound is refused rather than silently truncated.

The study binds immutable board/row/run/pair identity, source age, publication, and actual consumer receipt. Date-only identity and unknown/all-missing incumbent covariates are refused. The 62-versus-69 GEX case is appropriately used as a lineage warning, not as training data or proof of historical availability.

P5 remains a fixed ETF inventory-scenario population. P6 remains an independently authorized existing-order population. Their empirical adapters require honest incumbent covariate receipts; an absent stock-board row is unavailable, not a zero score. Numerical/scenario or observation work may remain possible when empirical incrementality is blocked. The broader fixed-root feasibility lane is expressly separate from the primary incumbent-cohort comparison.

**Accepted claim limit:** options-free B0 inputs do not make an incumbent-selected or options-selected cohort options-free. The proposed result is conditional on the declared population/qualification rule. No broad-market, upstream-options-independence, or production-policy conclusion follows.

Appendix A supplies an actual algorithm for B1-RI rather than treating a generic C1 score as a range, return, variance, or cost forecast. Its eight fixed receipt-derived covariates and ordering are specified, including `score_center=(published prophet.score-50)/50`, stage indicators, explicit field missingness, and publication age. Confirmed null fields and an absent/unknown board are distinct states. The adapter's ridge, constraints, target link, solver, and receipts are fixed.

**Accepted estimand:** B2-RI versus the fixed target-trained summary-information B1-RI adapter. This is not improvement over every raw incumbent feature, an existing native forecast, the production ranker, or its live decision policy. Catalogue quality/borrow/package controls remain eligibility rules and diagnostics unless a separately accepted common-nuisance adapter is bound. A positive result cannot be relabelled as fully confounder-adjusted private information.

## 2. Causal clocks, target versions, and maturity

The decision contract fixes actual consumer admission `t` within the nominal ten-second window, source cutoff `c<=t`, maximum cutoff lag, feature windows ending at `c`, and outcome windows beginning at `t`. Feature, B0, B1, contract/reference, and input bytes must actually be available by `t`; event timestamps alone do not establish this. Later corrections cannot backfill past decisions. Captured-PIT and reconstructed development history are explicitly distinguished.

Outcome construction is sufficiently specified for a finite implementation: exact P1 extrema rather than boundary-crossing bars; fixed midpoint eligibility; ten one-minute P5 increments; P3 five-minute/session-boundary marks, partial sessions, and one inclusion of each overnight return; corporate-action-aware total-return increments; explicit half-day/holiday and skipped-entry P4 rules. Unavailable marks, incomplete paths, unsupported actions, and missing benchmark intervals remain missing rather than zero or rescaled paths.

The immutable label cutoff is 20:00 ET on the first NYSE session strictly after the horizon/deadline date. Training and planning must use actual `label_mature_at`, not nominal horizon completion. Missing-at-cutoff labels cannot be silently replaced by later reconstruction. Purging uses exact label intervals at every fit stage, including the H20 validation tail before test sealing.

The amended historical construction is important: P3 B0 offsets used *inside* RI calibration are themselves earlier as-of/held-out HAR forecasts; the next level uses held-out B1-RI forecasts for B2 training. Final HAR predictions do not retroactively replace RI training offsets. P2/P4 historical target residualization uses the row's earlier monthly beta artifact, while validation/test use a frozen evaluation beta version. The target identity therefore includes the residualization rule and row version, rather than claiming one fitted beta vector existed throughout history. The final B2 scaler is correctly described as a training transformation of historical raw features, not as a scaler historically published at every row.

The 99% label-completion threshold is a declared quality gate, not proof that remaining missingness is random. Even if it passes, conclusions should retain the specification's missingness diagnostics and conditional population identity. The proxy-loss claim is narrower than latent variance accuracy or trading utility; QLIKE does not fix biased, sparse, or selected price marks.

## 3. Mathematical algorithms and units

**P3/P5 positive nesting passes.** For positive matched-unit `v1` and finite eligible `z`, `v2=v1*exp(beta*z)` is strictly positive when its declared finite-domain checks pass, and beta zero exactly recovers B1. A negative OIF19 feature is valid; it is never used as a variance argument. OIF19 is in volatility units, while B0/B1/B2 forecasts and realized labels are in matched variance units. OIF20 remains a separate queued feature.

With nonnegative `y`, scalar QLIKE fitting has derivative `sum w*z*(1-(y/v1)*exp(-beta*z))` and nonnegative Hessian `sum w*z^2*(y/v1)*exp(-beta*z)`. The boundary-sign/bisection rule on the fixed `[-1,1]` domain is correct. The analytic flat case is distinguished from a small numerically rounded Hessian; an inability to certify finite derivatives/brackets is a refusal, not an arbitrary coefficient. A boundary optimum is retained and disclosed. Zero realized labels are valid because `log(v)+y/v` remains defined; no `log(y)` is introduced.

The RI variance objective adds positive ridge, giving a strictly convex objective on its box. Its cyclic coordinate order, coordinate derivative, boundary KKT signs, stopping checks, and nonconvergence refusal are specified. The P3 direct-H HAR candidate keeps training-only retransformation and does not add a second smear to directly QLIKE-trained B2. Its positive log-domain/full-rank requirements are real gates, including refusal of genuine zero training targets rather than epsilon replacement.

The declared 252-based-to-ACT/365F conversion is dimensionally correct when the external input uses the stated same-interval `(252/n)*sum(r^2)` convention. Missing interval, `n`, or unit convention blocks conversion. A common positive unit change adds a common QLIKE log constant and leaves the mathematical paired loss difference unchanged.

P1 is explicitly unconstrained through-origin WLS followed by nonnegative prediction projection. It is not asserted to be the optimum of the projected-loss fitting problem. P2/P4 retain the linear offset. P4 now fixes call-minus-put sign, OI weights, borrow units, `Tbar`, dividend indicator, pair-spread formula, forward/spot term, and nuisance-design order.

P5 fixes the selected book at 09:35, one primary inventory-sign scenario, shock, model/surface convention, full selected-book coverage, exact time decrement, and endpoint-spot notional. This is a scenario feature, not dealer inventory or observed hedge transactions. Genuine zero P5 persistence variance now consistently blocks its multiplicative positive comparison while preserving the scenario/outcome census.

P6 uses independently observed full-fill cost by 60 seconds, with actual fees and explicit partial/unfilled/missing-record categories. Buy quantity is checked against displayed ask size, sell quantity against bid size. Its weighted-median nonnegative one-dimensional L1 offset and tie disposition are mathematically appropriate for positive spread regressors. The RI cost mean's evaluation by MAE is a frozen algorithm choice, not a claim of an optimal median predictor. Simulated hedged markouts are diagnostics and cannot become actual-fill calibration labels. Full-fill conditioning cannot establish routing or unconditional execution-policy value.

No implementation or numerical fixture is certified by this algebraic inspection. Finite-domain, pricing/Greek, clock, deliverable, and optimizer witnesses remain required under G4/G6.

## 4. Dependence, multiplicity, and power planning

One explicit date/root/slot-or-order hierarchy governs fitting and evaluation; the later precise weights rule expressly replaces earlier shorthand. Daily aggregation avoids counting prints, contract legs, and repeated alerts as independent observations. Within-date cross-root/slot records remain together in calendar resampling. P4 structural non-formation dates remain missing positions rather than artificial zero benefits.

The final inference rule is implementable: 9,999 circular calendar-block draws; fixed L and exactly one 2L sensitivity; exact concatenation/truncation; null centering; one-sided tail with ties and the plus-one convention; empty/nonfinite resample invalidation; deterministic SHA256 counter-mode uniform index sampling; and a fixed percentile-interval convention. The boundary statistic is correct for each margin. In particular, `E[.98*L1-L2]>0` tests more than a 2% reduction on the declared weighted loss population; ordinary benefit and relative reduction remain separate reported quantities.

Holm retains all six primary hypotheses, including p=1 for blocked/unrun/invalid pilots, fixed tie ordering, one final test, and no alpha recycling. Registered sensitivity outputs are not a second chance to select a favorable primary result. Marginal descriptive intervals are explicitly distinguished from simultaneous familywise intervals. Block-bootstrap p-values remain approximate model-based inference, so nominal alpha is not a demonstrated finite-sample FWER guarantee merely because the algorithm and Holm rule are fixed.

The earlier 63-session validation versus 20-session-block concern was resolved by the principal's conservative design constraint: validation `max(63,20L)`, hence 400 sessions for P3/P4 and 100 for the other pilots. Usable primary/2L block counts, positive finite variance, and the fixed stability ratio are now explicit screens. They do not establish stationarity or future support. Source failures and missing blocks cannot be replenished after observing favorable losses.

Power planning now fixes the shifted validation residual grid, finite Monte Carlo counts, Bonferroni planning threshold, Wilson lower endpoint, N grid, first-qualifying-N rule, and infeasibility/refusal states. This is executable conditional planning under the declared shift. The simulated fixed critical value derived from validation is a planning approximation; it does not rerun the eventual test's entire data-dependent centered-bootstrap and Holm procedure inside each simulated alternative. The specification appropriately does not claim actual future effect, realized power, latent variance truth, or policy utility. This limitation should remain in the implementation report rather than being compressed into an unqualified “80% powered” claim.

No variance, block-stability, completion, source, or power gate was empirically passed by this review. An unresolved or infeasible plan must retain its typed state.

## 5. Disposition and remaining required bindings

**No source-document change is required for principal engineering-design acceptance at the exact hashes above.** The writer addressed the review's concrete definition/consistency issues before these versions froze: dynamic panel and RI scope, score centering, nested causal offsets, historical target beta versions, P1 projection characterization, common weights, B0 receipt ordering, exact P4 quantities, P5 zero-offset consistency, P6 actual-fill disposition and size side, and exact inference/power rules.

The work needed before an empirical trial is accepted remains concrete and mandatory:

1. Record principal adjudication of the numerical choices, fixed C schema, RI estimand, dynamic population rule, useful margins, P6 catalogue disposition, and planning constraint. Reconcile older catalogue/protocol wording when it still implies native-policy or stronger fully controlled incrementality; preserve that as an explicit scope change rather than silently inheriting a stronger claim.
2. Obtain existing-owner acceptance and causal source/snapshot/input/reference receipts. Bind the allowed contract/quote-condition, surface/pricing, event-calendar, corporate-action, and benchmark-classification versions. Implementers must not invent those unbound identities or historical receipt times.
3. Bind exact data/split manifests, per-root history eligibility, scaler/nuisance and held-out offset artifacts, actual label maturity, immutable trial identity, and power-planned N after qualified validation. Existing #8286 outcomes remain development evidence.
4. Execute the finite numerical and causal fixtures, source/coverage/domain checks, and conditional power procedure without test-outcome inspection. Preserve unavailable, invalid, unresolved, infeasible, and failed states; no epsilon, clipping, fallback, cohort replacement, or tuned alternate model may repair them silently.
5. For P6, bind the separate actual order/fill/fee read authorization and catalogue-primary disposition. Absence leaves observation/simulation work only and p=1, with no new orders or authority escalation.

These are held gates already represented by null binding fields and G0–G6, not corrections that this reviewer filled with assumed data. The accepted next step is a bounded implementation packet under existing owners that validates and executes the declared contract, while keeping production candidate/score/rank/gate/order/deployment authority unchanged.

## 6. Later integration disposition — 2026-10-03

**Disposition: ACCEPTED / STOP for this finite consistency review.** The four later integration documents reconcile the accepted engineering design consistently. No correction is requested. This append does not reopen the immutable study specification, rerun an empirical test, attest a numerical implementation, or fill an empirical/owner/source/power gate. Publication and remaining integration belong to the root principal.

The original independent review before this append had SHA256 `f91dbf930f05387a938f06fb430fe6fc817cf9996ea6472d94ef0e9fd5fa9976` and Git blob `3665208e227f2f0b3847d2b73f0cf4caa23af167`. Its acceptance remains bound to the original specification hashes at the start of this document. Both specification files were rehashed in this integration read and remained byte-identical.

| Later integration artifact | Reviewed SHA256 | Git blob |
|---|---|---|
| `MASTER_PLAN.md` | `8b981e922f01e4e165992bde7d7ffc0d5ddf014321903b7e2527e5dfea879f57` | `0b0d60291d0377b1c9be4857281abcb34a87efdd` |
| `RESEARCH_PROTOCOL.md` | `44181deee4bc02b0ef8702599b1f89e3076d51e3bbf0f86608fc195e36626cb8` | `aa4be7b8c80d872e8b5838dacfceda2feea92a5d` |
| `options-signal-catalog.md` | `88d696b36ccefe41bd0609881a6eebe93fb81284d38873bd3ede086f39579319` | `93a3838ca124790eb867ddcdc3da5f782f7d03e9` |
| `options-signal-catalog.json` | `490616b43576b51ed3cabc1c88e9959f673a271f26539aa112617631958ddd35` | `66b3bf08df1e77bfb0befdf41eea8d30f54ac543` |

Focused findings:

- All four documents now identify P1–P4's dynamic causally consumer-admitted incumbent US-common-stock panel and preserve failed-row census, revision/population identity, source age, and selection lineage. They do not substitute the present board or the broader fixed-root feasibility lane for historical incumbent membership. P5/P6 retain their distinct scenario/order populations and genuine-covariate gates.
- B2-RI versus B1-RI is the fixed first research estimand. The actual-production-policy/all-information objective remains explicitly separate and unsatisfied. An options-free-input B0 on the selected population is not called an options-free cohort. The protocol binds the actual source/date/dataset/owner/power evidence still needed after design adoption.
- P3's positive multiplicative B2-RI mapping is recorded as a resolved design decision. It is no longer presented as an unspecified primary mapping. Negative OIF19 remains a volatility residual; matched positive variance forecasts are scored by QLIKE against nonnegative realized variance. OIF20 and the other queued P3 variants explicitly retain their own newly versioned mapping/baseline/multiplicity requirements and do not inherit the primary's acceptance.
- P6's actual 60-second full-fill implementation-shortfall MAE is the sole empirical primary, conditional on independently observed complete fills and fees. Quote coverage and simulated hedged markouts remain diagnostics. The JSON preserves the exact previous catalogue endpoint and prior catalogue SHA256 `03f6e951dd838cc348472159d96a9eefe1c328879e720b09a2f4021aa57f7a82` in the endpoint disposition. No previous diagnostic or simulation is reclassified as successful actual-fill calibration.
- The catalogue still has 40 unique feature IDs and exactly six primary assignments: P1/OIF01, P2/OIF04, P3/OIF19, P4/OIF22, P5/OIF13, and P6/OIF35. The primary raw formulas inspected during this review remain consistent with the frozen specification. The author separately reports preservation of all raw formulas, units, input fields, clocks, aggregation, normalization, controls, source/owner records, and historical evidence. This focused review is an evaluation-metadata consistency check, not a second full audit of every unchanged catalogue field.
- The catalogue's adoption record explicitly gives the finite specification priority for pilot formation, population, normalization, modeling, and evaluation without activating the broader queued definitions. The original #8286 retrospective statistics, identities, null-preservation rule, and distinct multiplicity family remain in the protocol; no new empirical result or source/power pass is supplied by this integration.

**Historical input identity is preserved.** The frozen specification intentionally still names its original inputs. In the current cumulative scratch package, its `RESEARCH_PROTOCOL.md` and catalogue JSON inputs now have the later hashes above. `CONTRACTS.md` also has a root-owned later revision, current SHA256 `f5a512528b728fdadb5adbd0c7de43e71fe2a3cc7067a016149c8d2deef873f5`, versus the original frozen input SHA256 `e2a8ced5a769996a8b46a737db07d33ce6a9571b8838d763447d5c2e19514db5`. That contract revision is outside the four-file review scope. The root reports it adds only a reviewed-reference index with synthetic/source-certification/strict-schema limits. The root's final cumulative manifest must bind the current bytes separately; none of these later revisions rewrites what the original study author and reviewer actually read.

No other file was changed by this integration reviewer. The finite consistency review is complete; further source qualification, owner acceptance, implementation validation, empirical sealing, release, and publication remain with the principal and existing owners.
