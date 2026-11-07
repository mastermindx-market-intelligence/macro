# Emergence matched study — 2026-10-06

## Verdict

**Build truthful B03 research-attention semantics and the frozen prospective evaluator. Do not describe H-EMERGENCE-CONVERSION as historically validated or as incremental predictive alpha.**

The parent result is reproducible as a **legacy raw-tier capture diagnostic**: in the original window, 3 of 13 horizon-mature first-ticker watch baselines later displayed a T1/T2 marker within 12 observed board sessions. One of those three, PWR, was explicitly provisional. Requiring an eligible, nonprovisional technical state leaves **2 of 13 observed confirmations**, with only **3 observed nonconverters** and **8 trajectories containing missing observations or unknown state**. Missing records cannot supply the other ten negative labels.

The source-vintage sensitivity is material. On extended latest-per-date snapshots, the same-date/sector/entry-status matched capture difference is **+11.3 percentage points**. Rebuilding both exposure and outcomes from the **first preserved snapshot for each date** produces **−1.5 percentage points**. Neither interval excludes zero. A stronger interpretation about independent point-in-time evidence is unavailable because the legacy flags are not an admissible independence graph.

There is also a concrete implementation correction: **the existing candidate pool does not contain most early watch candidates.** Only **3 of the 21** extended first-emergence baselines occur in the candidate_pool of their exposure snapshot. NVDA, FORM and PWR are absent at their early exposure cuts. B03 must compose the existing watch/candidate observations as well as the cascade-eligible pool; a pool-only projector would miss the golden early journey. This does **not** require new canonical anchors or any admission change.

All results here are historical discovery evidence inspected through 2026-10-06. No prospective confirmation, production effect, trading authority or threshold promotion is claimed.

## 1. Scope, source pins and reproduction

The frozen scientific question is conversion to incumbent valid T1/T2 within **12 observed board sessions**; the requested 3/5/10/20 horizons remain secondary. Exposure and endpoint thresholds were not optimized against outcomes.

| Source | Immutable identity | Use |
|---|---|---|
| Protected procedure source | Mastermind a6d40ff648671b03bd4d829d84dd066b58ea8c3f | Root admission/procedure pin |
| Main code/data source | macro 731a23fb64b9f6f1a321c77618f927f1a58d2d41 | Raw board history and B1/RP1 census |
| Parent research | PR #8495, head 770918cb266b5d884978e31d61670b4efd789eaf | Frozen definitions and original discovery |
| Raw board source | site/factordata/us_standouts.json | All archived exposure/control/outcome observations |
| Supplemental price source | Parent head 770918cb266b5d884978e31d61670b4efd789eaf | Final-vintage RS/liquidity sensitivity only |

Source census and every selected/alternative Git blob, commit timestamp and SHA256 are in [board_source_manifest.json](results/board_source_manifest.json). The extraction recovered **394 preserved variants across 36 board dates**, including **30 v3 dates from August 17 through October 5**. The original study window contains 26 of those v3 dates through September 25.

Both initially available source repositories were shallow. Older objects were obtained into an isolated research source repository; shared checkout, branches, refs and production files were not changed.

The full intermediate board arrays are deliberately not committed. Their SHA256 values are:

- Latest-per-date array: 599a96d4ba23e2aabe81caa9fb434fabd2652d700d0c48093ffee12c3478d889.
- First-per-date array: 060d56804c96601ac8f86f4f5c826105a2509c7e584673b5b0b4dbddc3240289.
- Complete variant manifest: 8aa9d2230bb6e8258fa2f68d77d0442496c4efdba2afc2a5290861cb1d42aa84.

The exact pool contract is [engine/us_candidate_lanes.py at the main pin](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/us_candidate_lanes.py). The exact B1 source relationship contract is [engine/us_candidate_episode_intake.py at the same pin](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/us_candidate_episode_intake.py).

## 2. What is, and is not, the exposure

### Frozen target exposure

The intended exposure is at least two **registered independent evidence families**, each with direction/semantics, known-at clock, source identity, staleness policy and duplicate-control relationship. That exposure is **not identifiable from these legacy board flags alone**. An unknown qualified-family count is not zero, and it is not the legacy flag count.

The independent evidence-family census in the companion report owns the source-readiness judgment. This study does not promote a synthetic SUE clock, stale holder information, or repeated news into an admitted family merely to obtain a sample.

### Historical proxy

For explicit compatibility with PR #8495, the diagnostic proxy counts:

1. A nonempty news_burst object.
2. A finite, nonzero sue_z.
3. smartmoney_chip.action equal to new or add.

There are **21 first-ticker unresolved proxy exposures** in the extended latest-snapshot reconstruction. Their patterns are 10 SUE-plus-ownership, 8 news-plus-SUE, 2 news-plus-ownership, and 1 with all three flags. Thus **19/21 depend on SUE**, whose legacy event timing is not the required true release/known-at clock. This is a substantial measurement limitation, not a minor missing column.

The news flag is not automatically bullish. At first exposure, HUBG's news lean is negative; TPR, NVDA and GOOG are neutral. All observed nonzero SUE values in this particular exposed cohort are positive, but the definition remains the frozen nonzero legacy proxy, not a newly tuned positive-only rule.

The proxy construction requires a watch[] row, no current T1/T2 marker, an observed Entry Signal status, and a status other than buy_now or partial. It does not make a watch lane synonymous with Entry Availability. The first qualifying observation per ticker is retained for the whole window, eliminating nightly exposed-row echoes.

This is a **conservative issuer-deduplicated historical index-observation sensitivity**, not a claim that a new canonical emergence episode ID exists. Exposure rows carry immutable source-observation references such as git:<blob>#watch/<row-index>. canonical_episode_id is left null unless an existing exact B1 relationship is separately proved. No ticker/date episode is minted.

## 3. Endpoints and missing-data rules

Three outcome layers are kept separate:

- **Raw technical marker:** later signal.tier_cascade is T1 or T2. This reproduces the parent marker census and may include provisional states.
- **Eligible, nonprovisional technical confirmation:** T1/T2 with explicit eligible=true and tier_observation_provisional=false, no contradictory provisional=true, and an observed signal clock. Explicit future observed/asof clocks are not accepted at an earlier board date. Missing eligibility or clock is unknown.
- **Entry status opening:** the incumbent entry_signal.status subsequently says buy_now or partial. The evaluator reads that supplied status; it does not derive availability from a tier, evidence count, rank, or price.

“Valid” in the result-file mode name denotes the second technical guard. It **does not certify independent-family PIT qualification, an entire source bundle, executable entry, or a provenance-clean formal plan**.

No naive signal.asof == board.as_of freshness rule is used. A premarket board can legitimately carry the prior completed session. Full freshness adjudication requires the incumbent expected-session/completed-session/basis rules and the actual source bundle. The companion operational census handles those receipts. The board-state endpoint here remains distinct from that clean-source/publication endpoint.

For each horizon:

- A preserved qualifying later state is an **observed conversion**, even if there were intervening gaps.
- A nonconverter is observed only when the candidate and necessary state are present on **every one of the horizon's observed board sessions**, without qualifying confirmation.
- Missing candidate rows or missing necessary state produce **OBSERVATION_GAP_OR_UNKNOWN_STATE**.
- Incomplete calendar follow-up produces **RIGHT_CENSORED**, unless a qualifying event has already been observed.
- A candidate absent from a displayed board has **not** thereby expired, failed, lost market eligibility, or stopped being a research candidate.

The session clock advances across observed board dates, not every exchange session and not calendar days. Missing whole-board dates therefore also limit what can be learned about intervening opportunities.

### Why there are two denominators

The table below reports capture yield among **horizon-mature index observations** so treatment and same-date controls have comparable administrative follow-up. It separately retains events already observed in shorter follow-up. Those early events are not discarded from the evidence; they simply do not enter that mature-cohort rate.

Changing the horizon changes the mature cohort. Consequently 20-session mature capture need not exceed 12-session mature capture. It is not a monotone survival curve.

## 4. Conversion results

### Extended latest-snapshot cohort

| Horizon, observed board sessions | Mature baselines | Raw T1/T2 markers in mature cohort | Eligible nonprovisional confirmations | Fully observed nonconverters | Mature baselines with gaps/unknowns and no qualifying event | Immature baselines without observed conversion | Conversions already observed in shorter follow-up |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | 21 | 1 | 1 | 9 | 11 | 0 | 0 |
| 5 | 18 | 1 | 1 | 8 | 9 | 2 | 1 |
| 10 | 18 | 6 | 2 | 5 | 11 | 2 | 1 |
| **12** | **15** | **4** | **3** | **3** | **9** | **4** | **2** |
| 20 | 8 | 1 | 0 | 0 | 8 | 8 | 5 |

At the primary horizon the mature-cohort **observed capture fraction is 3/15 = 20.0%**. With 9 unknown trajectories, the corresponding true conversion risk is only partially identified: **20% to 80%** without an unproved assumption about what happened while candidates were unobserved. This bound is deliberately broad.

The 12-session events observed in shorter follow-up are COCO and URBN. There are therefore five observed within-12 confirmations across all 21 indexed candidates, but six of those 21 do not yet have 12 observed board sessions of administrative follow-up. A simple five-over-21 percentage is not a complete-case conversion probability.

### Parent-window reconciliation

The original August 17–September 25 window has 18 indexed candidates and 13 mature 12-session observations:

- Raw markers: **3/13**, reproducing the original 23.1% discovery numerator.
- Eligible, nonprovisional confirmations: **2/13**.
- Fully observed nonconverters: **3/13**.
- Missing/unknown mature trajectories: **8/13**.
- The corresponding true-risk identification interval is **15.4% to 76.9%**.

PWR's September 21/22/23 T1 is explicitly provisional. It is a raw technical progress observation, not a completed nonprovisional confirmation for the frozen primary outcome.

### Time to confirmation and Entry Availability

| Candidate | First proxy emergence, latest-snapshot reconstruction | First eligible nonprovisional confirmation | Observed-session lead | First observed Entry Signal opening | Interpretation |
|---|---|---|---:|---|---|
| FORM | Sep 3 | Sep 11, T2 | 5 | Sep 24, partial; 13 sessions | Technical confirmation precedes availability |
| NVDA | Sep 4 | Sep 23, T1 | 11 | Sep 23, buy_now | Preserved research lead time; clean-source/plan clocks remain separate |
| PWR | Sep 4 | Not observed through Oct 5 | Unknown | Not observed | Sep 21 T1 is provisional; later absence is unknown, not failure |
| WDC | Sep 10 | Sep 30, T1 | 11 | Not observed | Sep 25 T1 is provisional; confirmation does not itself open entry |
| COCO | Sep 16 | Sep 25, T2 | 7 | Not observed | Conversion observed before full 12-session maturity |
| URBN | Sep 30 | Oct 5, T2 | 3 | Oct 5, partial | A faster case exists; it does not redefine the horizon |

Among the three horizon-mature extended confirmations the conditional median is **11 observed sessions**. Including the two confirmations seen before their follow-up matures gives a conditional median of **7 sessions**. These medians describe observed converters only, not waiting time for all candidates.

Only **one of the 15 mature 12-session baselines** reaches an observed buy_now/partial state within the horizon. Raw tier confirmation, completed technical confirmation and Entry Availability are measurably different milestones.

The detailed baselines, all outcome states and source commits are in [extended_window_latest_exposed_baselines.csv](results/extended_window_latest_exposed_baselines.csv) and [extended_window_latest_outcomes.csv](results/extended_window_latest_outcomes.csv).

## 5. Matched controls, uncertainty and sensitivity

Controls are unresolved same-date watch observations with fewer than two legacy flags. Missing flags are not proof of absent upstream evidence; that limits the comparison to the legacy board representation.

The primary diagnostic sequence uses same date, then sector, then exact incumbent entry status. Additional fixed three-nearest matching uses same-date, baseline-only covariates: residual alpha, setup, extension, off-high distance, sector rank fraction, alignment quality and realized-volatility context. Cross-sectional scaling is calculated on the same board date, not from future covariate values. No C1 score is fabricated for off-buy observations.

| Reconstruction / matching | Matched exposed baselines | Exposed observed capture | Control observed capture | Difference | Date-cluster bootstrap 95% interval |
|---|---:|---:|---:|---:|---|
| Parent window; same date | 13 | 15.4% | 4.8% | +10.6 pp | −4.9 to +32.4 pp |
| Parent window; date + sector | 13 | 15.4% | 5.2% | +10.1 pp | −4.7 to +30.7 pp |
| Parent window; date + sector + entry status | 11 | 18.2% | 10.4% | +7.8 pp | −3.2 to +33.3 pp |
| Extended latest; date + sector + entry status | 12 | 25.0% | 13.7% | +11.3 pp | −2.2 to +37.3 pp |
| Extended first; date + sector + entry status | 13 | 15.4% | 16.9% | **−1.5 pp** | −10.9 to +8.0 pp |

These are **capture-yield comparisons**, not estimates that fill missing actual conversions with zero. For the extended latest date/sector/status comparison, allowing the unresolved trajectories to take either outcome yields conversion-difference bounds of **−42.9 to +69.6 percentage points**.

The extended latest matched capture relative risk is **1.83**, and its capture odds ratio is **2.10**. Neither is a calibrated probability nor a causal effect. Both are subject to missing follow-up, proxy exposure, selected historical discovery and source-version instability.

### Effective sample size and concentration

The extended latest date/sector/status analysis has 12 exposed issuers, 8 exposure-date clusters, 29 distinct control tickers, and a control-weight Kish effective N of **18.94**. Date concentration gives only **6.55 effective date clusters**; the largest date contributes 25% of exposed observations. Information Technology supplies **6/12** matched exposures. Industry and market-cap identity are not consistently available as point-in-time baseline fields.

Removing FORM from the original date/sector/status sample changes the capture difference from +7.8 pp to **−1.4 pp**. That original result is not robust to the influence of every individual name. The two temporal slices also fail the intended replication test: in the extended latest reconstruction, only **one** after-September-10 exposure has mature H12 follow-up, and it has an unknown trajectory. Two same-direction, adequately observed temporal replications have not been established.

### Issuer deduplication

The primary exposed construction retains only one baseline per ticker. Same-date controls can recur across different exposure dates, so effective weights and repeated issuer use are disclosed.

A stricter sensitivity assigns each issuer only one study role in chronological order. A ticker already enrolled as a control cannot later be counted as a treated issuer in that sensitivity, and controls are not reused. This avoids counting an issuer in both arms without excluding controls based on future outcomes. It changes the sampled population, so it is not a replacement for canonical episode accrual.

- Original window: 9 treated issuers and 19 unique controls; **zero observed capture contrast**.
- Extended latest: 10 treated issuers and 20 controls; **+10.0 pp** observed contrast.
- Extended first-version reconstruction: 10 treated issuers and 21 controls; **zero observed contrast**.

Several tiny matched samples contain identical observed treatment-control outcomes in every date block. Their empirical bootstrap can collapse to [0,0]. The result JSON explicitly labels this **DEGENERATE_OBSERVED_CONTRAST_NOT_PRECISE_NULL**. It is not proof of a precisely estimated zero effect; missing-outcome identification bounds remain very wide.

### RS and liquidity sensitivity

The companion ignition extraction supplied immutable, final-vintage adjusted-price covariates. **16/21** exposed baselines join, and 9 mature exposures can be compared under the exact date/sector/status restrictions. LFUS, FIX, AMG, AMAT and MPWR have no admissible join in that supplemental input and remain missing.

Adding prior RS21 and log 21-session dollar volume changes **none of the 20 matched control pairs**. Scarce exact strata leave little room for an actual adjustment. The apparent +16.7 pp capture contrast is therefore unchanged mechanically; it is not evidence that convergence survives a successful liquidity adjustment. Residual standardized imbalance is approximately **0.97 for log liquidity** and **−0.67 for extension**. The true conversion-difference bounds remain **−38.9 to +72.2 pp**.

RS21 and momentum21 differ by the same-date SPY constant, so only RS21 enters matching distance; the same information is not counted twice. These are final adjustment vintages from the parent pin and are not promoted into a historical PIT qualification. Details: [emergence_price_control_sensitivity.json](results/emergence_price_control_sensitivity.json).

**Incremental information beyond technical proximity, RS and rank is not established.** Exact bars-to-cross is absent for the matched exposed observations; alignment/setup are imperfect proximity proxies. No threshold or new champion was selected to compensate for those limitations.

## 6. False attention, disappearance and expiry

Three extended latest baselines have complete 12-session observation with no completed confirmation: **LFUS, AMAT and TPR**. Each contributes 12 observed follow-up candidate sessions. These are valid examples of bounded research attention that did not convert within the frozen horizon.

LFUS and AMAT later confirm after **24** and **22** observed sessions respectively. Their later progress must not retroactively turn the 12-session outcome into success. TPR has no observed valid confirmation through the available window.

By contrast, HUBG, SNDK, BAC, PWR, INDV and other sparse trajectories cannot safely be branded false positives. For example, BAC is present in only 2 of its 12 follow-up board sessions; FIX in 1. The missing states contain no reliable negative technical result.

The 21 exposed candidates contribute **131 observed candidate follow-up sessions** within the available 12-session windows. This measures observation burden, not analyst time or attention actually spent. An exact cost of research attention requires prospective interaction/attention events under the existing owner.

Candidate disappearance is reported as first absence and last later visible date in the baseline CSV. **Expiry is unavailable** without an exact canonical terminal-state relation. No finite “gone for N days means failed” rule was invented.

## 7. B03/B1 coverage: a required implementation correction

### Lossless does not mean all watched candidates

build_candidate_pool consumes the existing **cascade-eligible pre-cap blend order**. Its lossless invariant applies to that input population. Ordinary watch[] observations can be outside it.

Measured from exact preserved board objects:

| Board date | Candidate-pool rows | watch[] rows | Watch rows actually in candidate_pool |
|---|---:|---:|---:|
| Aug 18 | 66 | 48 | 0 |
| Sep 3 | 93 | 48 | 5 |
| Sep 4 | 98 | 48 | 8 |
| Sep 25 | 148 | 48 | 31 |
| Sep 30 | 100 | 48 | 11 |
| Oct 2 | 154 | 48 | 36 |
| Oct 5 | 125 | 48 | 16 |

Only HUBG, BAC and URBN—**3/21** first proxy emergence observations—are present in the pool at their corresponding exposure cut. The other 18 were nevertheless real preserved watch observations. The original pool-only additive contract cannot show them at that cut.

**Required amendment:** compose the existing watch/candidate observations with candidate-pool visibility in B03, explicitly retaining source collection, board definition, source digest, observation time and exact row reference. Preserve original collection membership and ordering. Do not extend cascade eligibility, rewrite pool_rank, synthesize Prophet score, or treat a watch observation as an admitted trade.

This is a presentation/continuity coverage correction within B03 and the existing candidate observation plane. It supplies no evidence for a new B1 anchor species.

### Exact B1 relationships

The pinned B1 generation is peg:2303e8ef44ffb17b8b2411e6daffacd20bf228797e6b5b524fe8c274843b8042, containing **1,060 canonical episodes**. Existing candidate source-event IDs are parsed from the registry; the audit does not create them.

For the 21 exact historical exposure observations:

| Relationship state | Count | Meaning |
|---|---:|---|
| PRESENT in the pinned canonical archive | 6 | Exact existing source-event relationship resolves to one accepted canonical episode |
| Explicit NOT_YET_ANCHORED | 0 | No exposed baseline has the exact MISSING_STRUCTURAL_ANCHOR refusal required for this classification |
| UNAVAILABLE — identity unresolved | 2 | INDV and ACMR have exact identity refusals |
| UNAVAILABLE — no exact source relationship | 13 | Archived input/relationship not established at that observation; cannot be relabeled unanchored |

The six retrospectively associated names are HUBG, SNDK, TPR, BAC, NVDA and PWR. Their earliest relation recorded_at fields are:

| Ticker | Source observation date | Existing B1 relation recorded_at |
|---|---|---|
| HUBG | Aug 27 | 2026-08-28T14:28:48Z |
| SNDK | Aug 28 | 2026-08-29T15:41:20Z |
| TPR | Aug 28 | 2026-08-29T15:41:20Z |
| BAC | Sep 4 | 2026-09-06T11:16:58Z |
| NVDA | Sep 4 | 2026-09-06T11:16:58Z |
| PWR | Sep 4 | 2026-09-06T11:16:58Z |

These are **current retrospective exact associations**. The recorded clocks precede the selected latest board versions' commit times, but that does not prove the IDs were available at the original research decision. Production publication/availability of the original relation was not independently witnessed here.

Restricting evaluation to those six exact relations would drop **15/21** baseline observations, including FORM and WDC, two of the three mature H12 observed converters. That is a material selection change, not a scientifically harmless cleanup. Exact B1 identity should enrich a preserved observation when available; missing identity must not silently delete the observation or manufacture a replacement episode.

For comparison, the October 2 cascade-eligible pool has 154 rows: **62 PRESENT, 5 explicitly NOT_YET_ANCHORED, and 87 IDENTITY_UNRESOLVED**. The latest October 5 pool has no exact same-date relation in the October 4 generation; it is unavailable, not 125 newly proved unanchored candidates.

All association IDs, recorded clocks and source hashes are in [b1_emergence_relations.csv](results/b1_emergence_relations.csv), [b1_rp1_source_manifest.csv](results/b1_rp1_source_manifest.csv), [b03_selected_pool_b1_relations.csv](results/b03_selected_pool_b1_relations.csv), and [b1_rp1_coverage_summary.json](results/b1_rp1_coverage_summary.json).

## 8. RP1 and downstream plan joins

No exact mastermind.research_priority.v1 object is present in the selected board snapshots. A pinned search of committed data/, site/ and research/entry_radar returns no such schema. The committed Entry Radar ledger says WAITING_FOR_LIVE_SOURCE, live_forward_rows=0, and the B1 receipt has entry_radar input=0 with MISSING_SOURCE_FILE.

Therefore empirical correlation, overlap and orthogonality between **actual RP1** and evidence convergence are **not estimable from these artifacts**. Correlation remains null; it is not zero. This is a committed-source coverage conclusion, not a claim that every runtime or account lacks RP1. No substitute RP1 was calculated.

An eventual formal plan is also a separate relation. Same ticker plus a later date is insufficient to bind an emergence observation to a plan, and a pre-emergence plan is not a later conversion. In particular, the existing FORM and PWR August plans cannot count as September emergence-to-plan conversions. Exact provenance-clean plan/publication/reader/execution results are owned by the companion operational census. Cohort-level formal-plan conversion and expiry remain null where the exact relationship is missing.

## 9. Precise implementation and prospective handoff

The next step is **instrumented implementation and prospective accrual under existing owners**, not another broad historical search.

1. **B03:** repair the pool-only premise by preserving already-existing watch/candidate source observations alongside the cascade-eligible projection. Expose research state separately from tier, Entry Availability, score and canonical episode relationship.
2. **B04/D5:** produce typed family observations with direction, true known_at, source/capture clocks, staleness, source identity and inspectable upstream fact/duplicate relationships. A flag does not meet this contract.
3. **B1:** consume exact existing associations when available; render PRESENT, explicitly proved NOT_YET_ANCHORED, or UNAVAILABLE honestly. Preserve unresolved observations through existing source references. No new anchor species is required by this study.
4. **Conditional Fusion / existing evaluator:** freeze exposure at the decision cut; preserve candidates through the full 12 observed-session horizon; record missingness and terminal state explicitly. Keep 3/5/10/20 results as secondary endpoints. Select same-date comparable controls at enrollment, and retain the original exposed and control populations through disappearance from the visible board.
5. **B4:** supply exact Entry Availability objects. Technical progress never creates availability locally.
6. **A2:** bind first clean source, plan publication, reader visibility and executable-price witnesses independently. No provenance relaxation is justified.
7. **RP1:** consume an existing lawful object only. Accrue exact RP1-to-observation joins before claiming overlap or orthogonality; do not create another priority score.

The empirical blocker is specific: **there is no sufficiently complete cohort of frozen, independent, truly timed family exposures with continuous candidate follow-up, comparable controls and exact downstream relations.** Prospective accrual must resolve that block, obtain at least two temporal evaluation slices, and show that the conclusion survives issuer/date/sector concentration and baseline technical differences. This study sets no new numeric shipping threshold.

B03 semantics are justified because preserving and explaining known research observations is useful without predictive alpha. H-EMERGENCE-CONVERSION is a reasonable frozen accrual question, but its historical predictive support is fragile. Nothing here grants buy ranking, sizing, plans, alerts, execution or promotion authority.

## 10. Reproduction and artifact verification

Run against a read-only object repository containing the pinned ancestry and blobs:

```bash
python3 scripts/extract_boards.py --repo /path/to/source-object-repo --pin 731a23fb64b9f6f1a321c77618f927f1a58d2d41 --out /tmp/emergence-repro/boards

python3 scripts/analyse_emergence.py --self-test

python3 scripts/analyse_emergence.py --latest /tmp/emergence-repro/boards/boards_latest.json --first /tmp/emergence-repro/boards/boards_first.json --out /tmp/emergence-repro/full

python3 scripts/audit_b1_rp1_coverage.py --repo /path/to/source-object-repo --pin 731a23fb64b9f6f1a321c77618f927f1a58d2d41 --boards /tmp/emergence-repro/boards/boards_latest.json --baselines /tmp/emergence-repro/full/extended_window_latest_exposed_baselines.csv --out /tmp/emergence-repro/full
```

The optional price sensitivity consumes the companion ignition reproduction's price_controls_2026-10-06.csv, then compact_emergence_outputs.py emits the publication subset. The full intermediate match/control tables are regenerated by analyse_emergence.py; the committed tables retain every exposed baseline/outcome and the primary H12 control/pair evidence.

The focused self-test passes absence-is-unknown, horizon censoring, provisional exclusion and missing-eligibility refusal. The final deterministic run uses seed **20261006** and **10,000 date-cluster bootstrap draws** per comparison; same-horizon comparisons use a fixed corresponding seed. [reproduction_environment.json](results/reproduction_environment.json) records exact input and script digests. [EMERGENCE_ARTIFACT_DIGESTS.json](results/EMERGENCE_ARTIFACT_DIGESTS.json) verifies the compact result files.

No production source, live data, score, gate, plan, alert, sizing policy, lifecycle identity, shared checkout or shared ref was modified by this contribution.

