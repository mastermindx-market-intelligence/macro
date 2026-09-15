# Prophet intelligence — executed pilot and recommendation-truth defect

**Research continuation:** September 10 US / September 11 UTC, 2026.  
**Existing operation:** `prophet-absolute-downside-research-20260910-sol-001`; same Draft PR #7043.  
**Disposition:** A specified historical-data experiment completed, a concrete presentation defect was reproduced, and a repair candidate passed its selector tests. No production forecast, entry rule, raw rank, portfolio or deployment changed.

## 1. What became known

This round moved beyond architecture prose. It recovered the previously interrupted read-only source inspection, qualified an actual dated archive, committed an experiment specification before reading its price columns, executed that experiment, and tested a concrete reason the intraday page could sound confident during a largely unreadable pass.

The principal scientific result is **not an earned protection rule**. Adding the six-feature sector-participation construction improved the point estimate versus a two-feature SPY baseline, but its uncertainty interval includes no improvement. On the primary endpoint both fitted models also lose to a constant historical-rate forecast over the complete held-out period. This does not establish that breadth has no predictive value; it rejects promotion of this particular construction under its frozen test.

## 2. An actual source-code explanation for the screenshot

The exact `_plvMode` function was recovered from `templates/dashboard.html.j2` at Macro `6e1fb2ab35f68bbaf3695ffee5fe5ba268e46bae`. Its extracted UTF-8 bytes have SHA256:

`98b7605cd1ee31ff5dd7061df0fc1c488e56a452a09d13379ceb6c953a9de62e`.

The full template has blob `7568730f680939587bb345e305dc1fe0024db441`, also independently returned by the GitHub connector at the newer audit pin `14dc3b38111081a0d559d27b9c36ab995c8aa441`. This proves that template's byte identity at those two pins, not the exact version serving the Chairman's screenshot.

The selector returns `closed` after 16:20 ET when an overall non-dark pass has a sufficiently recent time-of-day. The per-name unreadable-fraction check occurs LATER and is therefore skipped in that closed branch. A payload with `evaluated_n=175` and `dark_counts.no_quote=166` consequently returns `closed`, even though the same coverage during the session returns `dark`. The downstream empty closed-state copy can then say 'Nothing crossed today' while the footer discloses 166 unreadable names.

This is a control-flow defect, not evidence that the market had no setups. It is also not proof of the exact screenshot's upstream failure cause.

### Executable discriminator

The Node harness executes the exact extracted selector in an isolated context with its existing constants and a controlled clock adapter. It does not run the full template, browser, entitled feed or server.

- Original selector: **23 PASS / 5 FAIL** across 28 cases. All five failures are incomplete post-close observations incorrectly classified as ordinary closed results.
- Unapplied research candidate: **28 PASS / 0 FAIL**.
- Four deliberate bad variants are rejected: removing the closed-quality check; changing the half-unreadable boundary from inclusive to strict; moving all wall-clock ageing ahead of closure; and counting unknown/out-of-probed-band names as data-dark.

The proposed selector computes the existing unreadable fraction once, preserves the existing 50% threshold, and checks it in the closed branch. It retains the intentional rule that a healthy final observation does not become a data outage merely because the market closed. It also preserves the distinction between unknown and unreadable.

A dedicated closed-coverage explanation is required: 'The final intraday check was incomplete, so today’s crossing result cannot be confirmed.' The existing `PLV_DARK` copy consumer still needs that reason wired and verified by its source owner. The candidate is **not applied to the repository template**, is not a full browser repair, and does not complete B4 Availability. Historical crossings must not be erased from their event owner merely because the final read is incomplete.

**Owner placement:** existing Entry Truth #6805 and Cockpit #6817 source owners, with exact hunk/custody clearance. Do not open a competing template writer or reroute the separately refused dossier/copy repairs. Existing B2/B3/B4 prerequisites remain intact.

## 3. Data feasibility: three different facts, not one 'fresh' timestamp

The authorized host's current main checkout contains only the Massive store's two JSON sidecars, not the selected price parquets. Its local manifest reaches September 4. The current committed manifest at Macro `14dc3b...` is separately dated through September 8. An inspected older local mirror does contain all 14 selected parquet files, but those exact files reach **July 2** despite a nearby manifest saying August 18.

Each actual file has 1,254 unique dates, beginning July 6, 2021. The selected cutoff of June 30, 2026 leaves 1,252 rows per file. File hashes were frozen before numeric analysis and verified again by the runner. The source files were unchanged after execution. No mirror was promoted to live source truth, no collector or whole-store restore was run, and no manifest was rewritten.

The existing enterprise entitlement record, `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md` at `14dc3b...`, has blob `3969a9aae918141b51baffbb0e17d8a2ec2485a0`. The private agreement and credentials were not obtained or published. The ordinary R2 client was inspected through the existing helper; that selected process had no configured client. The investigation then explicitly qualified the already-existing dated local mirror rather than silently claiming current R2 access or inventing an authentication path.

Official Massive documentation adds a material timing constraint: daily flat files are normally finalized around **11 a.m. ET the following day**. That does not prove an earlier pre-open decision had those finalized bytes. Raw flat-file prices are unadjusted; REST split adjustment is a different basis and is not dividend adjustment. This pilot mixes neither source nor basis.

The policy lesson is not 'our production feed necessarily has a one-day delay'. Other existing collectors or live routes may be earlier. The lesson is that every candidate feature must be bound to the ACTUAL route and available-at clock that supplies it; the final archive cannot silently stand in for earlier information.

## 4. Frozen experiment and result

Preregistration was committed as **`4d4b10116601adf241ec985556dc586abdcf3c8b`**, file `research/grey_deer/PROPHET_DOWNSIDE_PILOT_PREREG_2026-09-10.md`, blob `3e0d8b89c3c5ba7132ca84c09b47666a414e4377`, before price-column and outcome access. Its contents remain unchanged.

The input census is SPY, QQQ, IWM and 11 sector funds. IWM is census-only. Sector-fund participation is not individual-stock breadth. The experiment uses raw within-bar ratios and a two-observation feature lag. This conservative lag is an explicit study assumption motivated by archive availability, not proof of historical receipt times; it can be unnecessarily conservative across weekends and holidays. Daily-bar opening/closing fields are not independently certified here as regular-session auction fills.

Primary target: the SPY source bar closes at least 1% below its own open. Secondary target: its low is at least 1% below its own open. Neither is a full overnight-plus-intraday strategy return, a first-passage stop/target outcome, or the actual Prophet candidate universe.

Training ends in 2023; calibration is 2024; the locked test is January 2025 through June 2026. The motivating September incident is outside all evaluation periods. The eligible counts are **606 training / 252 calibration / 373 test**, after 21 warmup/lag rows. There are zero invalid OHLC rows in these selected files under the declared checks.

P0 is a smoothed constant historical event rate. P1 is a regularized logistic model using SPY body magnitude and range. P2 adds sector negative participation, sector mean body return, participation change and QQQ-versus-SPY body return. Training-only standardization, fixed penalties, calibration, chronological splits and the paired block bootstrap were all specified before the run.

### Primary endpoint: 30 events in 373 test dates

Lower Brier loss and lower log loss are better. These are probability-error scores, not win rates.

| Frozen model | Test Brier loss | Test log loss |
|---|---:|---:|
| P0 constant historical rate | 0.0747938093 | 0.2844811086 |
| P1 two-feature baseline, calibrated | 0.0771543314 | 0.3482544339 |
| P2 sector-enhanced model, calibrated | 0.0760191654 | 0.3313917529 |

P2 minus P1 paired Brier difference: **−0.001135166**. The 1,000-draw, 10-row paired circular-block 95% interval is **[−0.003203497, +0.000060908]**. The point difference is favorable in each reported test subperiod, but the interval crosses zero and the complete-test constant baseline is better. The frozen verdict is **NO_INCREMENTAL_SUPPORT**—meaning not established by this test, not a proof of zero predictive value.

### Secondary endpoint: 71 events in 373 test dates

P0 Brier = **0.154232913**; calibrated P1 = **0.152968340**; calibrated P2 = **0.151617298**. P2−P1 = **−0.001351042**, with 95% interval **[−0.003468132, +0.000109073]**. Its frozen verdict also remains NO_INCREMENTAL_SUPPORT. A secondary point improvement cannot rescue the primary result.

### Additional interpretation, not another fitted model

The frozen calibration step illustrates a real design vulnerability. The secondary event rate was 30/252 (**11.90%**) in calibration and 71/373 (**19.03%**) in the later test. P2's raw mean probability was **20.80%**; after the 2024-fitted calibration mapping it was **13.28%**. Its raw Brier loss was 0.145944043, versus 0.151617298 after calibration. The fitted mapping made this later-period prediction less useful under those metrics.

This supports investigating calibration drift and adaptation; it does not establish that a particular adaptive calibrator will solve the problem. The primary result is not rewritten to select raw probabilities, a different interval level, a different endpoint or a better-looking year. No threshold, feature, penalty or split was retuned after the result.

## 5. Numerical self-review caught a real harness boundary issue

Twelve synthetic specification tests passed before the market-data execution. Later adversarial self-review independently found that computing `close/open - 1 <= -0.01` with binary floats can exclude an exact decimal 1% loss. For example 100.02 to 99.0198 can compute as −0.009999999999999898.

Two new body/low boundary tests failed against the executed v1 harness. The corrected packaged harness compares the declared decimal prices at the exact 100×numerator <= 99×denominator boundary. It passes **14/14** tests. This is a numerical implementation correction to the unchanged endpoint, not a new threshold or favorable retuning.

A separate read-only audit checked ALL 1,252 actual SPY rows through the cutoff: **zero body-label differences and zero low-label differences** between v1 and the corrected decimal comparison. The audit retained the original SPY hash and occurred at 2026-09-11T01:58:26.830935Z. Therefore the original run's labels and reported results are unaffected; no corrected empirical rerun is claimed.

The exact executed v1 harness is retained separately from the corrected reusable harness. Four deliberately bad harness variants are rejected by the synthetic suite: one-row look-ahead, invalid data converted to zero, test observations included in standardization, and misaligned dates admitted.

## 6. Execution and evidence identities

The first and only empirical model run completed with **exit 0**, runtime **1.40 seconds**, on the authorized host. Result time: **2026-09-11T01:40:01.915505Z**. All model/calibration optimizations returned success.

- Executed v1 script SHA256: `9e337917e9f26a3b84c7a629e051c4fe5cbeb06277408b066b626f2c9cb9734b`.
- Exact original result JSON SHA256: `2cde9ca7aa7166b952028e394ded55fed5ca9a7df690c4cd2e3453b0b464ebb9`.
- Corrected reusable script SHA256: `350d93ffc13002feef22fdd155c43894f17c68bed0c3b97c9261e832d7b77bb5`.
- Original selector SHA256: `98b7605cd1ee31ff5dd7061df0fc1c488e56a452a09d13379ceb6c953a9de62e`.

The result was transferred as derived statistics only and its sandbox bytes independently matched the host result hash. Raw quote history, credentials, private contract and host paths are absent from the public research result. A Git preregistration is recorded; integration into any separate owner-maintained trial/promotion registry is not claimed.

## 7. Revised priorities: useful decisions, not a bigger score

**First, fix unsupported certainty.** The closed-state regression is a finite maintenance case for the existing owner. Preserve current source ownership and the B2/B3/B4 sequence; do not wait for a successful predictive model to make an incomplete read sound incomplete. Exact consumer copy and real browser proof remain required.

**Second, qualify decision-time data.** The next market study needs actual source-available observations at its proposed decision checkpoints. Preserve separate archived-history, actual-capture and live-production evidence. Extend the existing data/quote/episode owners rather than create a new collector or event store. The dated local mirror does not satisfy live freshness.

**Third, study conditional entry value and repair.** This small market-bar pilot does not settle stock-specific opportunity quality, overnight gaps, useful entry deferral, or recovery. The next experiment should compare enter-now, wait-for-a-specified-confirmation, and retain-as-research-only using existing candidate/plan identities and executable paths. It must charge the waiting policy for missed moves and late entry. No new model-derived permission is active.

**Fourth, make calibration an observed capability.** A model's probability mapping should carry its data window, sample maturity, current reliability and limitations. The next adaptation method must be compared prospectively or on a new untouched evaluation, not selected by reusing this holdout until something passes. Signal Lab should show this complete policy evidence, not inherit confidence from individually studied ingredients.

The existing #6840 return was rechecked this turn: it remains unchanged and unmerged with its requested repair. It was not duplicated or taken over. Existing #7005 source recovery, #7035 participation, #6817/#6832 Cockpit and #6805 Entry Truth retain their owners. No new worker was assigned; no runtime Job or watcher was created.

## 8. Completion boundary and next action

Completed: the specified archive diagnostic, exact-source defect reproduction, discriminating tests, numerical-boundary correction and durable research disposition. Not completed: a live presentation repair, market forecasting capability, stock-path policy, independent review, full Agent OS/CI validation, authenticated browser proof or improved customer returns.

**Primary product next action:** the current Entry Truth/Cockpit source owner consumes the exact closed-read regression and clears its isolated maintenance hunk/consumer copy, without treating it as a new B4 authority or repeating the held #6840 work. **Independent scientific next action:** qualify the earlier decision-time source and freeze a path/deferral plus calibration-drift study on an untouched evaluation. Do not launch another tuned version of this failed promotion candidate on the same test period.

### Primary source references

- Protected procedure: Mastermind `964bd8e7b30c91e5e83caee0ba37513ba7d07e70`, compatible Skillpack 1.0.1/bootstrap 1; re-read during this continuation.
- Macro audit: `14dc3b38111081a0d559d27b9c36ab995c8aa441`; source selector also pinned to `6e1fb2ab35f68bbaf3695ffee5fe5ba268e46bae` with identical full-template blob.
- Preregistration: Macro `4d4b10116601adf241ec985556dc586abdcf3c8b`, `research/grey_deer/PROPHET_DOWNSIDE_PILOT_PREREG_2026-09-10.md`.
- Source documentation: https://massive.com/docs/flat-files/stocks/day-aggregates ; https://massive.com/docs/flat-files/stocks/overview ; https://massive.com/docs/rest/stocks/aggregates/custom-bars .
