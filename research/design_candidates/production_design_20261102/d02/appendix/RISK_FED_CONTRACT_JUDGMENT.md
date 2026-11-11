> Integration note: original principal advisory retained as evidence, not RIG approval. The root D02 packet controls the candidate specification. Session-local cache paths below are provenance; durable source identities are in ../evidence/ and immutable GitHub links. The final root contract distinguishes reason-specific comparison refusal, evidence-cutoff admission from legitimate future targets, and source rights from user entitlement.

# D02 — Risk, regime, probability and Fed interpretation contract

**Read-only principal advice for the existing D02 Astra assignment.** This is a source-truth and UX judgment return to the D02 owner, not a new product session, reviewer admission, RIG approval, implementation, deployment or served-production proof.

Assignment package: Macro `6e1862867193ec6486a22001a0e4fb515da20448`. Protected procedure pin reused from root: Mastermind `b2326bbe30e9988d26199f5e774a482b9c09068a`, Skillpack 1.0.1. All current source/data observations below are at **Macro `fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9`**. Inspected files are cached at their original paths under `inputs/source/`; exact Git blob identities are in `advisor-risk/source-manifest.json`. The observation extract is `advisor-risk/observed-source-readings.json`.

Root retains browser, Paper, source publication and owner coordination. The historical Paper 13% specimen is not evidence of today's value. Root's initial browser read limitation also means none of the following source readings is represented as a confirmed served response.

**Evidence labels:** sections headed “observed” and statements tied to a source reference describe inspected committed code/data. Suggested wording, read-envelope fields, rendering behavior and acceptance cases are **proposals for the D02 specification**, not implemented behavior or released contracts. Source-cache verification recomputed Git blob identities: **23 of 23 cached producer/data files match their remote blobs exactly**. The current `engine/risk_radar.py` SHA-256 (`31668c7fe097cdf631edb6cca6e77990b40afdb3d4cb37d27596336689afe70d`) matches the latest prospective ledger's engine-source hash. That confirms this component's bytes only; it does not independently establish the served source bundle, calibration overlay, publication timing or model promotion.

## 1. Decision

D02 can specify the complete interpretation contract now. It should retain the analytical depth and the visible disagreement between trend, stress, positioning and policy pricing. It must not use one universal confidence meter, describe a normalized score as a probability, or make a withheld comparison reappear through a legacy display field.

The current source supports a **qualified risk-gradient presentation**, with the primary market state and its evidence visible together. It does **not** support a precision-qualified RiskRadar probability badge, an independently validated HMM transition forecast, or a blanket market-versus-Fed gap. This judgment does not change any model threshold, score, gate, calibration or authority. Final Paper composition remains with D02 after the joint F01/F02 shell-system v1 contract is verified.

### Observed source readings that must stay distinguishable

| Reading | Current committed observation | Required interpretation |
| --- | --- | --- |
| Canonical regime | Q2 / Reflation; growth +0.20, inflation +0.40; confirmed/raw both Q2; pending 0 of 7 | Two-axis classification with hysteresis. `TRANSITIONING` is also present but is not a pending label flip. |
| Regime confidence | Growth 0.12; inflation 0.32; aggregate 0.22 | Heuristic strength × agreement, averaged across axes. It is not a 22% probability that Q2 is correct. |
| HMM | Q2 membership 0.6774, Q3 0.3198; next-month hazard 0.4122; expected dwell 2.4 months | A separate fitted, display-only description. Historical posterior is full-sample smoothed; the hazard is an empirical monthly transition read. |
| RiskRadar | Caution; ungated state risk-off; growth scare 91.5; broad-tape gate false | The high raw scare and capped current state can coexist. Broad-tape confirmation is absent. This is not proof that risk has disappeared. |
| RiskRadar 21-observation estimate | 22%; baseline 17.8%; three hot Tier-A scares; state-only estimate 16% / lift 0.90 | The conjunction-adjusted estimate is distinct from the state-only rate. Do not claim that the caution state itself has above-baseline predictive edge. |
| Matching reconstructed evidence | 21-observation cell: n=66, 16 events, observed 24.24%, 90% interval 4.99%–45.45%, thin; `precision_grade=false` | Historical reconstruction, not contemporaneously issued forecasts. The interval describes the reconstructed observed rate, not a predictive interval around today's 22%. |
| Prospective scorecard | Latest exact-model cohort: 4 issued, 0 graded, 4 awaiting maturity; readiness `not_mature`; current model validated false | Evidence is accruing. A ledger issue receipt is not public-page publication proof. |
| Slow macro/credit risk | Score 20.81 / low; 10% band rate versus 19% base for ≥10% peak-to-trough decline over 63 trading days; full 4/4 composition | A different target and horizon from RiskRadar. Its low reading is not an all-clear for a near-term 5% loss. |
| Fed path | Current effective rate 3.88%; 12-month implied rate 4.46%; +58bp; legacy “~2 hikes” | The count is a rounded 25bp-equivalent level difference, not probabilities of two specific meetings. |
| Rates repricing | 12-month futures path fell 22.2bp over 20 trading sessions; easing pressure 4, hawkish pressure 0 | Direction of recent repricing, while the implied level remains above the current rate. “Cut expectations rising now” overstates what this necessarily means. |
| Rate/Fed comparison | Regime payload metadata: `not_comparable`, `basis_mismatch:reference_end`; rates-command stance withholds unmatched path, generation `d1_missing` | Render the withheld/comparison state consistently. Existing legacy numerical gap fields do not authorize a comparison. |

Evidence: [S1], [S2], [S3], [S4], [S5], [S6], [S7], [S8], [S9], [S10]. All values are source snapshots, not current market advice.

## 2. The confidence taxonomy

The interface must always name what a quantity measures, how it was produced, its time window, and whether the claim is descriptive, model-based or supported by outcomes. “Confidence” alone is too ambiguous.

| Quantity / exact source field | Normalization and unit | Evidence class and permitted claim |
| --- | --- | --- |
| `growth_score`, `inflation_score` | Weighted average of available −1/0/+1 component signs, approximately −1 to +1 | Directional axis score; weights renormalize over available components. Report component coverage. |
| `confidence` | Mean of axis `abs(score) × agreement`; each axis becomes 0 below minimum component count | Heuristic agreement/strength. A displayed zero is not proof of a 0% regime probability. |
| `regime_hmm.regime_probs` | Fitted posterior membership; four values sum to one | Soft membership under this model, not calibrated accuracy of the canonical regime label. |
| `regime_hmm.hazard` | 1 − empirical monthly self-transition rate | Historical next-month transition frequency for the model's modal quad. No daily flip countdown; no causal claim. |
| `risk_radar.scares[].score` | Weighted mean of available input percentiles ×100; normalization uses a trailing 504-observation window with minimum history | Relative stress intensity. Use `display_score`, `reading_state` and coverage to determine whether it is an eligible current reading. |
| `risk_radar.drawdown_prob.h5/h10/h21` | State table plus conjunction increments; fractions 0–1, capped at 0.95 | Model estimate for a loss of at least 5% from the issue close within the next 5/10/21 native SPY closing observations. Qualification belongs beside it. |
| `conditions.drawdown_risk.score` and `dd10_prob_pct` | Composite score; separate empirically measured band frequency in percent | Slow macro/credit pressure; ≥10% maximum peak-to-trough decline over next 63 trading days. Withhold band odds if source composition differs. |
| Anticipation `anticipation_index` | Percentile of the current confluence value in its own history | Relative confluence, not a probability. The cone is an empirical conditional distribution at representative 5/42/189 trading-day windows. |
| Anticipation `horizons[].p_up` | Conditional or separately gated directional estimate | Scored direction only where the exact per-asset/per-horizon producer gate permits it. Short horizon is display-only; a missing gate cannot inherit “validated” styling. |
| Odds Lab `stats.win_rate`, `edge_pts` | Count of >0 outcomes / matched observations; difference from same-range/same-horizon unconditional rate | Historical conditional frequency. Its nominal Wilson interval is not multiple-search-adjusted evidence of an investable edge. |
| `fed_path.implied` | Annualized rate percent; market contracts have EFFR or SOFR basis | Futures-implied pricing, including risk premia. Not a house forecast or a count of survey respondents. |
| Prediction-market outcome price/probability | Provider event/outcome contract and settlement definition | Market-implied benchmark. It is not the percentage of traders holding a belief. |

The exact event definition matters. RiskRadar's replay takes the **minimum of the next H closing prices divided by the issue-day close**. It does not compute the same future peak-to-trough measure used by the slow macro/credit composite. A price path that rises 10% and then falls 10% but never crosses 5% below the issue close can satisfy one target and fail the other. These should never share an unlabeled “drawdown probability” heading. [S3], [S4], [S11], [S12], [S13], [S14]

## 3. Evidence-bound design rulings and conflict register

### R1 — Correct the existing regime-confidence explanation

`dashboard.html.j2:7634–7635` says confidence is “probability behind the label × how much the inputs agree.” The calculation is `abs(axis_score) × agreement` in `axes.py:77–87`, averaged in `regime.py:296`. Preserve the number only with its actual meaning; do not percent-format it or substitute the HMM membership.

Proposed copy: **“Signal agreement 0.22 / 1 — combines axis strength and agreement among inputs.”** ZH: **“信号一致程度 0.22 / 1——综合两轴强度与输入的一致程度。”** Detailed method must also disclose coverage, because insufficient components explicitly produces zero confidence. [S2], [S15]

### R2 — Preserve confirmed, raw and pending regime states

Hysteresis is the canonical label owner. A raw axis change is not an immediate confirmed label change. Missing axes produce no label for that day while internal hysteresis memory is retained. The current `flip_condition` names IWM/SPY as the weakest supporting component, with slope z=0.55, cutoff 0.45 and margin 0.10. That is a condition to inspect, not a forecast of a flip and not a sufficient condition by itself: aggregate axes and confirmation rules still apply.

Keep the existing `label_unsupported` handling. If raw and displayed labels diverge, say **“Confirmed label retained while new evidence awaits confirmation”** with pending progress; if the producer reports unsupported, say so visibly. The independent `transition_state` flag must not be presented as “7-day confirmation in progress” when `pending_quad` is null. [S1], [S16], [S15]

### R3 — Keep HMM membership, transition history and canonical classification separate

`regime_hmm.py:24–27` explicitly states that historical probabilities use future data through full-sample smoothing. This is usable as a retrospective description, but cannot substantiate “the model predicted this turn then.” `hazard` uses a monthly empirical transition matrix; expected dwell is `1/(1−p_stay)`, not remaining life after the current five-month spell.

Label HMM history **“Retrospective model description”** and expose its fit cutoff. Any replay that claims knowledge available at an earlier date needs the causal expanding-window refit and validation the producer itself requires. Current-month resampling uses the last available value in an incomplete month; the producer should explicitly declare the partial month if the UI displays monthly transitions. A quad missing from fitted states gets zero membership; it must be described as unrepresented in the fit, not impossible. [S7]

### R4 — Preserve RiskRadar's state resolution; do not recalculate it in the UI

`_resolve_state_row` is the single semantic owner of Tier-A origin, confirmed/eligible conjunction, Tier-B escalation and broad-tape cap. Current `state=caution`, `state_ungated=risk-off` and `context_gate.met=false` are a coherent model result. “Caution: several stress inputs are high, but broad market confirmation is absent” connects the answer to its evidence without pretending that low stress and high stress disagree.

Threshold confirmation and empirical evaluation are different. The current credit HYG/TLT leg crosses its threshold but carries historical lift 0.5; the current vol-term leg crosses its threshold but carries lift 0.44. Neither should become a “validated leading signal” simply because `confirmed=true`. Do not independently change the display-only exclusion or renormalization rules: the source documents a reverted cosmetic reweighting that changed authority. D02 should expose the qualification, not repair model math inside a redesign. [S3]

### R5 — Preserve unavailable/partial semantics through every view model

Current source has an internals scare with raw score 100, `reading_state=UNAVAILABLE`, zero eligible resolved legs and `display_score=null`. The dashboard ladder correctly guards this at `13617–13621`. The Macro Context builder instead copies raw `score` and `band` at `538–546` and drops reading state, display score and coverage; it can therefore revive an unavailable raw reading. This is a concrete cross-route contract defect.

Carry `reading_state`, `display_score`, `display_band`, `weight_coverage`, registered/resolved counts and `partial_composition` intact. UNAVAILABLE wins over all numerical fallbacks. PARTIAL remains a reading with disclosed coverage, not an ordinary fully qualified score. Valid 0 remains 0. In the current source, volatility is PARTIAL with 50% registered weight coverage; it should not look equivalently supported to a fully observed scare. [S1], [S3], [S17], [S18]

### R6 — Use current reconstructed evidence; do not over-correct to “no calibration exists”

The current payload includes a matching accepted historical evidence surface. The 21-observation 22% cell has n=66 and 16 events, marked thin and non-precision-grade. A different historical Paper screen displaying 13% cannot establish the current estimate or its validation state.

Retain the RiskRadar probability feature, but make **Caution** the leading answer. Put the numerical estimate in the evidence layer or give it adjacent qualification on any glance card. Proposed copy: **“Historical model estimate: 22% over 21 trading observations. Evidence is limited.”** The evidence layer shows target, base rate, state-only rate, conjunction contribution, n/events, interval, period, reconstruction class and current validation status.

The 90% interval must be called **“Interval for the reconstructed observed rate.”** It is not a calibrated range for today's future probability. `precision_grade=false` must not become a green pass badge. If evidence matching fails because the probability surface or conjunction parameters changed, do not borrow cells from the old surface; show **“Evidence not matched to this model version.”** [S4], [S5], [S19]

### R7 — Separate three kinds of track record

The source distinguishes reconstructed calibration, historical issued-odds audit and prospective same-model receipts. Historical audit has 59 graded observations per horizon and zero target events; lower Brier error in such a one-class sample is not sufficient validation. The latest prospective exact-model cohort has 4 issued and 0 graded observations, with `public_publication_timing_verified=false` and `current_model_validated=false`.

Use explicit section labels and never add these counts into one “validated N.” Producer readiness requires 252 issued sessions, 300 calendar days, 200 graded observations per horizon, event/non-event support, event clusters, complete baselines and integrity, plus supportive block-bootstrap results. Even then, the code says promotion review eligibility is not automatic validation. D02 must consume those states; it cannot award promotion. [S5], [S6]

### R8 — Resolve the audit's Fed phrase conflict as level versus change

`rates_inflation_command.py:659–685` creates `repricing_dovish` when the 20-session 12-month ZQ path change is at most −15bp and easing-minus-hawkish score is at least 2. The label map says “Cut expectations rising now.” Current input is −22.2bp with easing 4 and hawkish 0. At the same time, the level is 4.46% against 3.88% current, or +58bp.

The correct distinction is **“12-month implied rate fell 22.2bp over 20 sessions; it remains above the current rate.”** The original two phrases are not necessarily numerical contradictions. A level can remain positive while falling. Avoid “now” unless it refers to the observed session. Current rates-command asof is October 30; built time is November 2 at 10:35Z. [S8], [S9]

This copy is conditional on permitted basis/comparison. The current producer actually withholds its stance because matching is incomplete, so the interim production spec must honor the withheld state rather than simply replacing one sentence while keeping the unqualified chart.

### R9 — Honor comparability metadata across all legacy consumers

Current `fed_path.implied_source_meta.gap` says `not_comparable` / `basis_mismatch:reference_end`. Yet legacy gap values survive by design. `fed_stance` repeats the legacy comparison, and the dashboard Policy and Fed dialogs render legacy gaps without checking metadata. The current `rates_command` artifact also carries `board_generation.complete=false`, reason `d1_missing`, and the stance: “The futures rate path isn't shown until it can be matched to the policy rate.”

This is the stronger conflict: a qualified producer declines an interpretation while its consumers still make it. All summary, chart, tooltip, accessibility text and detail consumers need the same comparability verdict. Display independently valid observations separately, with their own targets, but withhold the difference and “more dovish than the Fed” takeaway. Do not hide the entire rates panel because one comparison is unavailable. [S8], [S9], [S10], [S20]

The legacy gap is −14bp in the October 30 rates-command row and −22bp in the November 2 regime row. `fed_path.py:177–180` calculates months to year-end from the asof month, so merely moving the artifact date across October/November changes the chosen horizon from two months to one. This is an identifiable source of drift, not proof of actual repricing. The authoritative repair belongs to the rates producer/D15 consultation, with D02 owning consistent consumption.

### R10 — Put SEP projections at their actual target dates

Policy dialog code puts the current-year SEP dot at the m6 slot (`dashboard:14099` onward). Fed dialog code puts it at the m12 slot (`14742–14769`). The same year-end projection cannot consistently mean both six and twelve months from today. The proposed detailed chart must have a calendar or duration-correct x-axis, or show a separate explicitly dated SEP table. Outer-year dots must not be visually joined into a compatible futures curve unless basis and horizon transformations are qualified.

The current dots metadata also lacks the SEP release date/vintage; say **“Release date unavailable”**, not “Latest Fed projection.” The median SEP participant projection is not a policy commitment. ZQ monthly EFFR averaging and SR3 SOFR averaging are distinct rate bases; a SOFR fallback must not silently inherit an EFFR chart title. [S10], [S20]

### R11 — Replace inferred causality and survey language

The rates composition currently contains phrases such as an easing leg “is driving the move.” These are deterministic contextual joins, not causal identification. Prefer **“Inputs consistent with easing pressure”** and let the user inspect the observed legs and their dates. A hawkish market path plus easing statement guidance is a conflict to expose, not proof of policy being “on hold”; the legacy `fed_stance` fallback calls this neutral.

The dashboard's prediction-market sentence says “about N in 10 traders expect” (`12797–12798`). Outcome price is not a survey headcount. Use **“The market price implies approximately X% for [exact outcome]”**, with provider, contract, cutoff and settlement wording. Preserve the existing benchmark-only boundary; do not fuse it into the rate or risk score. [S9], [S21], [S22]

### R12 — Give source clocks truthful names

`conditions._input_vintages` identifies the last **changed-or-first** value in a forward-filled series. It cannot distinguish an unchanged new release from no new release. Its `asof` is therefore a last-distinct-value proxy, not automatically a verified publication timestamp. Cadence thresholds are explicit (e.g. weekly NFCI 14 calendar days, monthly EBP 70); age alone should not become a universal staleness rule.

`build_macro_context.py:628–631` substitutes `today` for an international-risk source date and calls it an “honest null.” This is not null and must not provide freshness certification. Preserve unknown source time until the real artifact `built`/observation field is joined. Separate `observed_at`, `published_at`, `built_at` and served-generation identity. A fresh build must never refresh an old observation. [S12], [S18]

### R13 — Preserve true zeros and missing states

`build_macro_context.py:948,955` uses truthiness fallback for policy rate and near-term forward spread; real zero can be replaced by a different source. Its hero class maps missing score to zero/down (`489`). Anticipation uses `p_up || 0.5` (`243`), and missing median return becomes zero in sorting (`323`). These are exact acceptance cases: null/undefined/NaN, zero and negative values must be tested separately; unavailable items sort after available items in both sort directions.

No-data is not calm, neutral, 50%, zero return or safe. Zero events with n>0 is an observed zero; zero observations is an unavailable rate. A source false boolean is not an absent boolean. [S18], [S23]

### R14 — Qualify historical analog and cone evidence

Odds Lab returns are next-open to horizon-close, not issue-close-to-close. Matching excludes today and compares with an unconditional rate over the same range/horizon. Preserve those definitions. Nominal Wilson intervals assume a sampling structure that does not account for overlapping 5/20-session outcomes or repeated filter searches; the UI must not equate a band above 50% with a proven edge over the actual historical baseline.

Anticipation uses representative windows 5/42/189 trading days while showing range labels 1–10, 21–63 and 126–252. Say which representative window produced a quantile. `cell_n` is not independent effective N. Preserve `thin`, long-history `underpowered`, direction-scored gate and model provenance. The committed gate contains GO for the confluence composite even though some constituent driver labels are NEUTRAL: do not claim every displayed constituent was independently validated. When the gate is absent, blanket “validated core” copy needs to degrade even if numerical cones remain available as display context. [S13], [S14], [S23]

## 4. Reuse strong existing work

| Existing source behavior | Disposition | Reason / required refinement |
| --- | --- | --- |
| Regime flip strip's unsupported/raw/pending handling | RETAIN + IMPROVE copy | Retain guards and nearest-support detail; remove probability misdefinition. |
| Dashboard scare unavailable guard | RETAIN and propagate | Correctly prevents raw 100 from becoming a current reading without eligible observations. |
| Macro Context reconstructed n/events/thin disclosures and qualification at 783–820 | RETAIN | Strong existing evidence disclosure; add full interval and exact trading-observation target, and keep it adjacent to the number. |
| RiskRadar state, broad-tape cap, counterread, trajectory and de-escalation | RETAIN | These explain why trend, stress and positioning may differ. No UI recomputation. |
| Separate slow macro/credit risk, nowcasts and source vintages | RETAIN + IMPROVE | Distinct horizons and composition matter. Rename inferred clocks honestly. |
| HMM history and transition matrix | RETAIN as retrospective method detail | Not a live-trading or historical-prediction proof. |
| Fed path, recent repricing and SEP details | RETAIN + IMPROVE | Preserve independently valid observations; block incompatible comparisons and align target dates. |
| Legacy unmatched market/Fed gap takeaway | BLOCKED_DATA for the claim | Owner must provide qualified basis/horizon comparison; retain accessible explanation of why it is withheld. |
| Prominent unqualified historical Paper 13% | IMPROVE | Historical specimen only; no cosmetic validation. Qualified numerical feature remains available where source exists. |
| Probability precision badge / promoted model claim | BLOCKED_DATA | Current producer validation false; not a designer approval decision. |
| Condition save | RETAIN seam to D23 | D02 supplies reading/predicate context; D23 owns save identity, mutation and acknowledgment. No silent save on navigation. |

No removal of an analytical feature is authorized by this advice. “Blocked” applies to a specific unsupported interpretation, not the surrounding inspection journey. Current access restrictions on `/macro_signals.html` and `/crossasset.html` remain intact; no essential successor may be moved behind them without the existing access decision.

## 5. Proposed read contract and exact existing carriers

This is a **proposed consumer contract**, not an invented API or released shared schema. Prefer a source-backed adapter over duplicating model logic in templates. Preserve current schemas and paths while introducing explicit optional metadata through the responsible owner.

| Consumer need | Real current carrier | Required preservation / producer addition |
| --- | --- | --- |
| Canonical regime, axes, pending and support | `data/regime/latest.json`; `engine/axes.py`, `engine/regime.py`, `engine/run.py` | Preserve raw/confirmed distinction, exact method version and component availability; expose the actual thresholds/config revision. |
| Regime history | `data/regime/regime_history.parquet` → `build_site.py` timeline export | Declare reconstructed versus contemporaneous history; price timeline and regime series need a common cutoff or visible clock mismatch. |
| HMM | `regime_hmm` in regime payload; nightly `data/regime/hmm_latest.json` producer named by source | Preserve fit cutoff, retrospective class, states present, monthly frequency; no render-time refit. |
| RiskRadar | `risk_radar.v2` in regime payload | Preserve state/ungated/gate/authority/reading-state fields and source version. Consumption cannot change math or authority. |
| Reconstructed calibration | `data/risk_radar/probability_evidence.json`, attached as `drawdown_prob.calibration_evidence` | Match exact probability surface/conjunction parameters; preserve class, n/events/interval, date bounds, target, digest, precision false. |
| Forward evidence | `data/risk_radar/scorecard.json` and producer's forward logs | Preserve issue timing versus publication timing and exact-model identity; no mixing prior model cohorts. |
| Slow conditions risk | `conditions.drawdown_risk` plus `vintages` | Preserve expected/resolved/missing/undefined legs, stat passport and withheld probability. Add actual raw-source release receipts where the clock is currently inferred. |
| Fed path | `fed_path.implied` and `implied_source_meta` in regime payload | Distinguish exact field from rates-command's `board.rate_path_row.implied_path`; preserve selected strip, basis, rate index, averaging law, contract reference interval and comparability. |
| Rates interpretation | `data/rates_command/latest.json`, built by `scripts/build_rates_command.py` using `engine/rates_inflation_command.py` | Consume state change and level separately; honor `board_generation`/stance basis refusal across every rendering branch. |
| Analog/cone outcomes | `engine/odds_lab.py`, `engine/anticipation.py`; existing route builders/JS | Preserve return definition, query factors, horizon, matched/base counts, gate and evidence status. |

A reading envelope should carry stable reading/series/instrument identity; source path + JSON pointer; schema and model/config identity; value plus unit and transform; target plus horizon/calendar; observation/publication/admission/computation clocks with precision and null reasons; source revision and input-bundle digest; coverage; reading state; evidence class; authority; and comparability state. These names are proposals for integration discussion, not fields asserted to exist everywhere.

The smallest safe migration is to project existing fields intact, then add missing provenance through the producer owner. It is unsafe to create a “clean” UI object that discards a withheld state and supplies defaults. A verified display contract needs one concrete fixture per producer and an explicit mapping for every numerical field.

## 6. Interaction and invalidation states

At the first reading, show the regime/state, observation date and the most consequential limitation. The next layer answers “why,” and the evidence layer answers “what exactly was measured?” A mobile card must not hide the limitation behind hover. Keyboard and screen-reader summaries must use the same target, date and qualification as visible copy.

| State | User-facing behavior and example | Re-evaluation / invalidation rule |
| --- | --- | --- |
| Available | Show value, unit and observation date | Re-evaluate when the producer publishes a new observation/model generation. |
| Partial | “Partial reading — 1 of 3 eligible inputs available.” Use actual counts/weight coverage; do not imply equal weights. | Return to full only when source coverage and basis match, not when a page reload succeeds. |
| Unavailable | “Reading unavailable — eligible inputs are missing.” Keep evidence access. | A real zero or old raw score cannot clear this state. |
| Unknown source time | “Observation time unavailable.” | Requires producer source timestamp; build time cannot substitute. |
| Last known / stale | “Last observed [date]; update is overdue under this source's schedule.” | Cadence and market calendar decide lateness. Weekends alone do not invalidate a daily close. |
| Model evidence unmatched | “Evidence not matched to this model version.” | Requires a matched model surface/config/source fingerprint; old cell N does not qualify it. |
| Thin reconstructed evidence | “Historical reconstruction · limited evidence.” | Stronger wording requires the model owner's evidence and promotion state, not a larger chart. |
| Incomparable operands | “Comparison unavailable — reference periods do not match.” Keep independently valid rows. | Requires exact permitted transformation and basis match. |
| Raw regime pending | “New axis reading awaiting confirmation: [n] of [required] sessions.” | Canonical hysteresis or explicit shock rule resolves it. No browser timer. |
| Confirmed label unsupported | “Current axes no longer support the displayed label.” | Producer recomputation determines new label; do not infer from one component crossing. |
| Risk capped by context gate | “Stress inputs are high; broad market confirmation is absent.” | Recheck the actual SPY/breadth gate, eligible legs and state resolver. |
| Conflicting evidence | Show both readings with target/horizon/date and reason for disagreement | Do not silently average; a change in question/basis may explain rather than resolve the disagreement. |
| Changed model or revision | Show revision/model-version marker and retained prior context where available | A historical revision cannot be described as an event known on the old date. |

Proposed concise EN/ZH copies include **“Comparison unavailable / 暂无法比较”**, **“Limited historical evidence / 历史证据有限”**, **“Observation time unavailable / 观测时间未知”**, and **“Last known reading / 最近一次已知读数”**. Use words and icons as well as color, and keep them in table/export/accessibility text. F02 should govern the shared visual treatment; D02 owns the exact financial interpretation.

The save-condition seam should carry a stable producer condition, observed value/unit, target/horizon, model version, evaluation cadence and source snapshot. D23 must decide writable identity, validation, pending/success/failure/readback and notification semantics. A regime component margin is not automatically a supported alert predicate; mark the proposed condition unresolved until D23 and the source owner agree.

## 7. Discriminating acceptance cases for the later implementation

These are specification tests, **not claims that production tests were executed**. Source extraction arithmetic was checked separately: (0.12+0.32)/2=0.22, 0.16+2×0.03=0.22, (4.46−3.88)×100=58, and current HMM membership sums to 1.

| ID | Fixture / intervention | Required result |
| --- | --- | --- |
| RC-01 | Axis confidence 0.22, HMM Q2 0.6774 | Two clearly named quantities; neither is labeled the other's probability. |
| RC-02 | Raw quad changes for 1 of 7 required sessions | Confirmed label retained; pending progress shown; history not rewritten as a confirmed flip. |
| RC-03 | One axis absent, last known quad in memory | Current classification unavailable; historic label may be shown only as last known. |
| RC-04 | `transition_state=TRANSITIONING`, `pending_quad=null` | No invented pending-label countdown. |
| RC-05 | IWM/SPY z moves below 0.45 but aggregate axes stay same | Weak support changes; no frontend-forced regime flip or automatic save trigger. |
| RC-06 | Raw scare score100, display_score null, reading_state UNAVAILABLE | Dash and explanation on macro overview, context page, popup, export and accessible summary; never a high-risk or calm fallback. |
| RC-07 | Vol scare PARTIAL, 0.5 weight coverage, one of three resolved | Partial qualification retained; no reweighting or independent band change. |
| RC-08 | Current state caution, ungated risk-off, gate false | Coherent capped-state explanation; no “all-clear” and no frontend upgrade to risk-off. |
| RC-09 | Confirmed threshold with lift below eligibility floor | Threshold state retained, but no historically qualified leading-signal badge. |
| RC-10 | State h21=.16, conjunction_n3, displayed h21=.22 | State-only rate16%, final estimate22% and base17.8% are distinguished; caution itself not credited with joint lift. |
| RC-11 | Probability surface changes but old evidence cells remain | Evidence attachment fails closed; no inherited n/interval/precision label. |
| RC-12 | Reconstructed n66/events16 with CI90[.049919,.454545] | Label interval for historical observed rate; not “today's risk range5–45%.” |
| RC-13 | Prospective four issued, zero graded; historical59 all no-event | “Accruing / not mature,” no accuracy boast or model validation. |
| RC-14 | Macro/credit loses NFCI; score remains finite | Partial composition retained and dd10 probability withheld; slow-risk score not confused with a current five-percent-loss estimate. |
| RC-15 | HMM historical plot is recomputed on a later fit | Explicit retrospective series; no claim that historical posterior was issued then. |
| RC-16 | HMM one quad unrepresented | Zero labeled unrepresented under fit; not impossible regime. |
| RC-17 | Rate path drops22.2bp over20 sessions but m12 remains58bp above current | Distinct recent direction and forward level; no claim that cuts are the priced net outcome. |
| RC-18 | Metadata comparison not_comparable, legacy numeric gap populated | No gap chip or equivalent tooltip/takeaway leaks; independent rates still accessible. |
| RC-19 | Rates-command stance withheld and generation d1_missing, legacy path values populated | Every route honors the producer's basis qualification; no “path withheld” beside an unqualified path. |
| RC-20 | Oct30 strip reused on Nov2; end-year legacy horizon changes2→1 | Display generation/source drift, not fabricated market repricing; compare only matched target dates. |
| RC-21 | December31 SEP dot inspected in February, June and November | Correct calendar position each time or a dated separate row; never fixed6m/12m slot. |
| RC-22 | ZQ absent, only SR3 available | SOFR basis named; no silent EFFR/target-midpoint subtraction. |
| RC-23 | Hawkish market path and easing statement guidance | Explicit mixed evidence; no semantic assertion that the Fed is on hold. |
| RC-24 | Prediction-market probability72% | “Price-implied benchmark72%”; no “7 in10 traders.” Exact outcome/settlement retained. |
| RC-25 | policy rate0, spread0, return median0, p_up0 versus null | Zeros survive; null unavailable. Sort unavailable last in both directions. |
| RC-26 | A new release repeats exactly the prior value | Last-change clock is not represented as release timestamp; source receipt can independently refresh publication time. |
| RC-27 | Monday build includes Friday market close and monthly EBP observation | Appropriate clocks/cadence visible; no universal stale badge caused solely by calendar age. |
| RC-28 | Odds5/20-session matched days overlap; user tries many factor sets | Historical baseline retained; nominal CI identified; no automatic validated-edge styling. |
| RC-29 | Anticipation gate absent or horizon not scored | No validated directional badge; thin/underpowered and representative window still visible. |
| RC-30 | 320px, touch, keyboard, zoom and ZH versions of any qualified reading | Target, time and limitation remain available without hover; modal close restores trigger focus and source scroll. |

## 8. Strongest counterarguments and the evidence that would settle them

**“The probability evidence is present, so 22% can be the hero.”** Presence is a useful improvement over the older audit. It does not override `precision_grade=false`, thin cells, overlapping samples or current-model validation false. The strongest defensible compromise retains the numeric feature with adjacent qualification and makes the state/evidence primary. A matched, sufficiently mature prospective cohort and the real promotion decision would settle stronger presentation; D02 cannot manufacture them.

**“Dovish repricing and net hikes are contradictory; choose one.”** They measure change and level, respectively. Inspect the same instrument, reference horizon and source session. The current source demonstrates both can be true. The needed correction is precise wording and clock/basis consistency, not deletion of one series.

**“Legacy gap values are still generated, so they are approved for display.”** The newer metadata expressly preserves legacy numeric keys while declining comparability. Numeric presence is therefore not the gate. A comparable status with an explicit permitted transformation would settle the comparison.

**“Removing an unqualified leg from the mean is only a visual cleanup.”** The documented reweighting changed state and authority because available-weight normalization changed. This requires model-owner intervention and validation, not a design-only edit. Preserve arithmetic and display its limitations.

**“A low long-horizon macro-risk rate contradicts a near-term risk alert.”** The target, measurement definition, horizon and leading/lagging information differ. A paired target definition and same-source test path settles whether there is a numerical inconsistency; differing scores alone do not.

**“A wide confidence interval is too much detail for mobile.”** The full interval can be progressive disclosure, but “limited historical evidence” and exact horizon must be on the primary surface. Hiding the limitation while retaining a large precise percentage creates the false confidence the assignment asks D02 to remove.

**“Last value change is a sufficient freshness clock.”** It is a useful proxy and existing thresholds prevent obvious ffill certification. It fails on unchanged new releases and revisions. Raw-source observation/release receipts would settle the ambiguity; until then label the proxy honestly.

## 9. Producer obligations and bounded handoff

The assignment verifies D02, F01/F02 and collaborator D15 responsibilities. It does **not** verify a current individual writer for each model. Do not promote the historical `research/grey_deer` path into a live writer identity or transfer custody. Root should consult the incumbent source owner before implementation.

| Accountable boundary | Exact source carrier | Minimum next evidence / action |
| --- | --- | --- |
| D02 existing owner | `dashboard.html.j2` `body.page-macro`, Macro Context and assigned route consumers | Carry reading states and qualifications end to end; correct copy; preserve D03 `body.page-stocks`; document exact mappings. |
| F01 / F02 existing foundation owners | Joint shell-system v1 | Verify released contract identity and semantic styles before final composed Paper freeze. Data/spec work need not wait. |
| D15 consultation + incumbent rates producer owner | `engine/fed_path.py`, `engine/rates_inflation_command.py`, `engine/rates_command_basis.py`; `data/rates_command/latest.json` | Resolve D1 generation/basis hold, year-end mapping and source-clock contract; reconcile legacy gap consumption. Existing owners keep writer custody. |
| Incumbent RiskRadar/model source owner; live person unverified | `engine/risk_radar.py`, `probability_evidence.json`, `risk_radar_scorecard.py`; historical evidence path `research/grey_deer/...` | Provide exact live model/source/calibration fingerprint, evidence linkage and promotion state. Reconcile current source versus served generation; no new calibration “approval” from D02. |
| Incumbent regime/HMM source owner | `axes.py`, `regime.py`, `regime_hmm.py`, calibration harness named in source | Confirm display-only HMM scope; declare fit cutoff/incomplete month; no predictive-history claim without causal refit. |
| Incumbent conditions/source ingestion owner | `conditions.py` / upstream raw observations | Add verified observation/release timestamps where currently inferred from changes; preserve composition qualification. |
| D02 with incumbent Anticipation/Odds model source owners | `anticipation.py`, gate artifact, `odds_lab.py`, route builders | Ensure gate identity, effective-sample limitations and nominal interval disclosure; preserve exact outcome definitions. |
| D23 existing save owner | Existing condition-save carrier, not invented here | Confirm stable predicate identity, supported evaluation cadence, write/readback and save states. |
| D10 / D19 existing domain owners | Event/news reading; China-specific risk semantics | Preserve exact market and jurisdiction boundaries; US calibration must not qualify China or other market models. |

**Advisory completion state:** sufficient source evidence to specify the principal risk/confidence contract and the material unresolved producer obligations. No code, Paper, approval state, production configuration, PR state or deployment was changed. Exact individual producer writers, served artifact identity and final composed layout remain with root's existing coordination work.

## Source references at the single current source pin

[S1]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/data/regime/latest.json
[S2]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/axes.py#L65-L97
[S3]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/risk_radar.py#L813-L1050
[S4]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/risk_radar.py#L1306-L1349
[S5]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/data/risk_radar/scorecard.json#L69-L446
[S6]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/risk_radar_scorecard.py#L705-L1010
[S7]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/regime_hmm.py#L1-L150
[S8]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/data/rates_command/latest.json
[S9]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/rates_inflation_command.py
[S10]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/fed_path.py#L112-L247
[S11]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/risk_radar_backtest.py#L173-L226
[S12]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/conditions.py#L540-L604
[S13]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/anticipation.py#L243-L382
[S14]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/odds_lab.py#L333-L490
[S15]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/dashboard.html.j2#L7574-L7644
[S16]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/regime.py#L270-L386
[S17]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/dashboard.html.j2#L13608-L13648
[S18]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_macro_context.py
[S19]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/risk_radar.py#L367-L426
[S20]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/dashboard.html.j2#L14071-L14814
[S21]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/fed_stance.py#L37-L78
[S22]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/dashboard.html.j2#L12788-L12799
[S23]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/anticipation.html.j2#L233-L326

Additional exact data anchors: regime top-level facts lines1–60; conditions353 onward; HMM4741 onward; Fed9465 onward; Fed stance11363 onward; RiskRadar22274 onward, probability22512, attached evidence22533, context gate22608. Rates-command asof/built3–4, rate row8 onward, pressure218, market check359, stance1185, generation1640. Probability evidence target/source/precision at `data/risk_radar/probability_evidence.json:694–713`. Strong reusable reconstructed evidence UI at `templates/macro_context.html.j2:783–820`; current prospective scorecard at `data/risk_radar/scorecard.json:264–446`.
