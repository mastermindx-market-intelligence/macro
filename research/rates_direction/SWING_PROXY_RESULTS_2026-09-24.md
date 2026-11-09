# First observed-session indicator comparison: no accepted winner

## Result and scope

The predeclared all-three MPR comparison did not improve the trend/volatility benchmark in this small ^TNX proxy pilot. No combination meets the preregistered50 resolved, non-overlapping active-episode adequacy gate. This is an insufficient-evidence result, not a general rejection of the waveform hypothesis or a claim that the best-looking secondary is a winner.

Before outcomes: exact code, reference, spec and tests frozen at18841b8f37af5a0257b1c08df78e5ab3eb53a8bb, receipt2026-09-24T14:15:23.690573+00:00. All9 generated configurations appended to the existing TrialLedger family ric_swing_proxy_v1 before the first feature/outcome evaluation. Original Studio process35332 completed the run. 56 synthetic/related tests passed before the freeze. RD1 remains unchanged; no optimizer, new indicator owner, collector or live risk mutation.

Data = original captured Yahoo ^TNX hourly sample, NOT TVC:US10Y and NOT native Pine-certified.448 closed hourly rows form256 provider-session-anchored bars:192 full2h and64 scheduled40-minute closing stubs. Closing stubs are not two hours. Overnight excursions are unobserved. Current incomplete rows and one irregular snapshot excluded; no filled or reconstructed extrema. Supplied-default research formulas are tested, not verified current chart overrides.

Targets = first observed upper/lower barrier touch during12 closed chart bars AFTER a full1-bar delay. Barriers set at signal time from trailing24-bar volatility with5bp floor. Same-hour dual touches would be ambiguous; unfinished full horizons are censored. This is not an executable stop-loss strategy or continuous24h Treasury path. USD/equity returns, trading costs, leverage and portfolio performance were not tested.

## All results retained

123 reconstructed forecast origins,110 matured/scored origins across28 source dates. Every origin has9 model distributions:1107 total model/date forecasts, not1107 independent observations. Scored origins run2026-08-11T16:20Z through2026-09-18T18:20Z. Outcomes on that common panel:46 up-first,24 down-first,40 neither;13 later origins are censored. The last reconstructed forecast is September23 at19:00Z; these were generated afterward, never issued then.

Brier is the sum of three squared probability errors (range0..2); lower is better. Relative improvement is measured versus the trend/volatility benchmark on the SAME110 origins. Non-overlapping episodes below are deliberately sparse and are NOT claimed statistically independent.

| Model | Brier | Relative improvement | Resolved non-overlapping active episodes | Directional successes |
|---|---:|---:|---:|---:|
| Unconditional frequencies |0.694859| - | - | - |
| Trend + volatility |0.685173| reference | - | - |
| M: MACD-RSI |0.686003|-0.12%|6|3 |
| P: price Stochastic, native strict zone rule |0.686026|-0.12%|6|2 |
| R: Stochastic RSI, proposed K/D cross |0.679106|+0.89%|7|4 |
| M+P |0.685173|0.00%|2|1 |
| M+R |0.685537|-0.05%|4|1 |
| P+R |0.673438|+1.71%|6|2 |
| M+P+R (primary) |0.685173|0.00%|2|1 |

The best-looking secondary P+R has only6 resolved episodes. Date-averaged diagnostic HAC gives t1.368,p0.1713 on28 dates; neither statistical strength nor the preregistered adequacy gate supports a winner. No raw-event percentage is presented as a reliable win rate. Predicted probabilities use past conditional frequencies; an oscillator can carry contextual information even when following its directional cross does not work. These are different statistics, explaining why P+R's probability score and2/6 directional successes need not rank alike.

The primary/all-three state was active at only5 of123 reconstructed origins and produced only2 resolved non-overlapping episodes. Its forecast probabilities were identical to the baseline. Under the frozen shrinkage rule, absence of eligible matched training observations means falling back to the baseline, not inventing an edge. This does not prove that confluence never works: it demonstrates that this definition is too sparsely supported in this capture to earn stronger conclusions. Do not widen recency, drop the native P zone, select another barrier or retime the origin to rescue this run.

## Reproduction and integrity

Private evidence: /Volumes/Mastermind/evidence/rates-direction-20260924-sol-001/swing-proxy-v1/frozen-18841b8/.
Raw-source SHA256:687b93d52beeb141dbfc3ea3eff787b67da7b36daa8effedc19568cbe544d070.
Prediction SHA256:527abd41223aca3982effc53a5ce66e35cc2d8b7441ec99693ac262e5c821c8f.
Summary SHA256:7fd91b889b2510a042e4c3d293738452d7396447eed5c9b9c8625b9196f0931b.
Published aggregates: swing_proxy_results_v1.json; registration:swing_proxy_registration_v1.json; arithmetic:swing_proxy_integrity_v1.json.

Same-author saved-row audit checked every origin/probability, strict training target-end cutoff, all9 recomputed Brier scores, unchanged frozen code/source identity, and exact append-only9-row TrialLedger suffix. PASS;0 new fits and0 new configurations. This is not independent review. Re-running the production CLI on this now-registered family is refused; preserve the original result and source freeze.

## Next discriminating step

Keep default formulas and this result. Obtain greater historical coverage from the existing source owner and bind native Pine exports to close remaining replication uncertainty. Freeze an expanded-sample replication with unchanged rules BEFORE inspecting its strategy outcomes; separate previously seen overlap from earlier dates and eventual prospective data. Do not call a longer corrected-history download an as-observed archive. A real equity-transmission comparison remains separate from rates-direction success. No promotion, merge, deployment, live forecast or autonomous worker is claimed here.
