# China Prophet historical-method review

Operation: `MMX-CN-PROPHET-CENSUS-REVIEW-HISTORY-20261009`  
Review date: 2026-10-09  
Existing canonical R0 owner: #6871. This review creates no new owner or execution authority.

## Verdict

**PASS for the corrected, explicitly retrospective diagnostic and the verified V4 summaries.** The initial selection and risk-metric findings were corrected by the historical worker and independently checked. This is not approval of executable alpha, a trading strategy, calibrated predictive probabilities, or production changes.

The comparable result is: **no stable ranking advantage is demonstrated on this small common cohort.** Intervals spanning zero do not establish that an effect is absent. The first output must not be used in place of the corrected artifacts below.

Final claim memo reviewed: `historical_autopsy/HISTORICAL_EVALUATION.md`, including its outcome tables, comparison claims, caveats and source index. Three wording requests were resolved: extreme cases are labeled as selected extremes; the four-winner net difference explicitly favors the latch convention; portfolio accounting must handle overlapping recommendations rather than prohibit overlapping positions. The restrictions in §4 are retained in the reviewed memo and remain required for the integrated claim table.

## 1. Bound inputs and proof scope

Read-only review covered `/workspace/scratch/cb265ed3ed34/historical_autopsy/autopsy.py`, its authorized companion `extend_audit.py`, and their locally delivered results. The declared immutable data/source revision is `3d90aad6d83152dfeeaf8345bc995826ac9d3139` in both scripts/evidence. No remote host was invoked, author script/result edited, production changed, public research expanded, or child worker launched by this reviewer. Only this separate review memo was written.

The following SHA-256 values were recomputed locally and match the historical worker's final handoff:

| File in `/workspace/scratch/cb265ed3ed34/historical_autopsy/` | SHA-256 |
|---|---|
| `autopsy.py` | `5a09a5112b3920201001d7fceefefcd336716154c696269fa6d680043a05e6a6` |
| `extend_audit.py` | `3838a50f85067e6a1a3ff990ec70c7f7a0f997699fb123a1406a3efc28f11408` |
| `historical_evidence.json` | `8b651cf4df19736f66a3cf184c5a47478ffe0bf2fc62a24bb5452c01b836e54d` |
| `v4_review_rows.json` | `626aacda09bdef9ba6cd8bb01a3688e445228b48ce63d5496defb07ce0482830` |
| `HISTORICAL_EVALUATION.md` | `49096c1197adb12bc29e526497700aa87073852ab3aee73d6e9efdc4fec668c0` |

I independently recomputed counts, means, positive counts, rank correlation, paired differences, date-cluster intervals and common-cohort membership from the exported row matrices. I checked subtraction and latch-return algebra. All eight delivered outputs match the final `SOURCE_MANIFEST.json` byte counts and hashes. I did not independently fetch the underlying remote Git objects or reconstruct raw price histories, original publication receipts, complete historical constituents or actual trades. Metadata/source-census assertions outside the row export (including the first reachable Git date and stale-name membership) remain author/source-census evidence, not a second remote extraction.

## 2. Material findings resolved

### R1 — Selection conditioned on future outcome availability: resolved

The first script ranked the `observed` subset and could replace an unresolved candidate. Current `autopsy.py` lines 224, 226, 233 and 234 freeze membership from issuance fields first, retain unresolved selections, and omit a portfolio outcome rather than substitute a ticker. Lines 246–247 enforce the common-date intersection for all five feature-complete rankers. `extend_audit.py` lines 49–51 retain the rejected-method comparison and examples.

A real example confirms the relevance: on 2026-08-31 the common-feature score selection includes `601059.SS`, whose exact-session outcome is unresolved. Selecting observed outcomes first substitutes `601360.SS`. The corrected common comparison excludes that date rather than crediting the substitute. The broader cap-qualified H10 top-six selections themselves did not change, but the equal-pool comparator has 15 complete dates rather than 17. Do not describe all older aggregate changes as a ranking-order effect.

The independent synthetic counterexample also passed: an unavailable highest-scoring A remains in frozen `ABCDEF`; the rejected method would return `BCDEFG`.

### R2 — Different feature/date cohorts: resolved for the comparable experiment

Current `autopsy.py` line 219 restricts the common experiment to the same non-null score, intelligence, momentum and quality cohort; lines 246–247 impose the five-arm date intersection. All five H10 arms have the same 11 dates, six selections per date and underlying feature-qualified pool per date. The broader 14/15/17-date tables remain conditional diagnostics with different coverage. They are not a fair aggregate league table.

The feature-complete experiment compares alternative rankers against score ranking within that restricted pool. It does not reconstruct the actual 24-name featured board. Sector capping is not full sector/liquidity matching; the matching extension explicitly reports slot availability, not a matched-portfolio return.

### R3 — Entire missing-price names omitted from denominators: resolved

`autopsy.py` line 181 and following lines add `no_price_file` outcomes; `extend_audit.py` line 52 quantifies scope. Four absent-price tickers account for 168 recorded candidate rows, nine raw-eligible rows and **zero cap-qualified rows**. Thus this particular missing-file issue does not change the qualified comparison, while raw-pool missingness remains visible. `raw_eligible_nulls` is zero at this pin, so the inspected Boolean conversion does not admit actual null flags here.

### R4 — Unsourced legal-limit/chase and adverse-excursion labels: resolved

The unsourced prefix-based chase classification was removed from the new diagnostic. `autopsy.py` line 140 now calls a flat adjusted bar `flat_bar_indeterminate`, and the methodology disclaims legal-limit/fill inference. This respects the existing prohibition on inferring legal price limits from adjusted prices.

The original `mae_close` could be positive when every future close exceeded entry. I reproduced entry 100→next close 101 yielding +1%; line 145 now clamps the value at zero. The revised pure function passed independent tests for positive and adverse paths. This remains an episode-level measure from closes, not intraday MAE, portfolio drawdown or volatility.

### R5 — Version/horizon/clock attribution and vintage labels: constrained correctly

`extend_audit.py` line 27 adds the same 158 mature episodes across H1/H3/H5/H10/H20, with 11 issuance dates. Older v3 and later v4 aggregate samples must not be used as a version treatment comparison. The directly comparable recorded v4/v3-shadow rows are identical on all 683 date/ticker/rank/score observations.

`autopsy.py` lines 87–89 identify selected-set/score disagreements. I verified that the five identified v4 discordant dates are absent from qualified exported comparisons. Cases now join definition/date/ticker and use `candidate_snapshot_features` at line 259, avoiding an unsupported original-publication claim.

## 3. Numerical controls independently verified

The export has 431 v4 episodes and 2,155 episode/horizon rows for H1/H3/H5/H10/H20, with no duplicate date/ticker/horizon keys. Every observed entry follows its recorded issuance date, every observed exit follows entry, and no exported entry/exit uses a weekend, the October 1–7 closure or September 25. Excess equals stock minus matched benchmark return; all close-based adverse excursions are nonpositive.

| Instrument | Recomputed result | Interpretation |
|---|---|---|
| Production-style H10, latched entry | 133/289 positive = 46.02%; mean −0.222129 pp; 21 dates | Reproduces the reported telemetry convention. |
| Production-style H10, current reconstructed entry | 129/289 positive = 44.64%; mean −0.213099 pp | Same 289 rows; 16 win-sign changes versus latch. Latch algebra reconciles. |
| Matched next-session-close to ten-elapsed-session close | 142/288 positive = 49.31%; mean +0.163738 pp; 21 dates | A separate analytical return convention. Date-cluster interval [−0.461174, +0.843003] pp. |
| H10 board-rank correlation | +0.077810 on 21 dates | Lower board rank is better, so **negative** correlation would be favorable. This is not a higher-is-better score IC. |
| H10 close-based adverse excursion | Median −3.976397% | Not intraday risk or portfolio drawdown. |

On the common feature/date/eligibility cohort, each ranker has 66 selections across 11 dates:

| Ranker | Mean excess, pp | Mean versus score, pp | Descriptive paired date-cluster interval, pp |
|---|---:|---:|---:|
| Score | −0.316215 | 0 | Reference |
| Intelligence | −0.563122 | −0.246907 | [−2.931617, +2.547798] |
| Momentum | −0.003037 | +0.313178 | [−2.303893, +2.963367] |
| Reversal | +0.517691 | +0.833906 | [−1.193039, +2.614613] |
| Quality | −0.585147 | −0.268933 | [−3.132921, +2.467333] |

These means and intervals match independent recomputation. One common-pool date has an unresolved unselected name; its denominator remains visible, and every selected name for all five compared arms has an observed outcome. An equal-pool benchmark therefore has a different complete-date coverage and should not be compared by unpaired aggregate means.

## 4. Required claim limits and remaining uncertainty

- **Clocks:** production H10 uses open/HL2 entry, a tenth stock close that includes the fill session, and a fill-session-close benchmark. The matched-close diagnostic changes entry, endpoint convention and one unresolved cohort row. Their difference does not identify the effect of benchmark-clock repair. The benchmark snapshot exposes only close and volume; `extend_audit.py` line 26 correctly labels the isolated clock counterfactual unidentifiable.
- **T+1 and execution:** the diagnostic's earliest H1 exit is after its entry session; synthetic and real-row timing checks passed. This does not prove broker settlement, fill queues, halt exits, price limits or intraday stop execution. Current adjusted closes, open/HL2 proxies and hypothetical cost drags are analytical evidence.
- **Uncertainty:** `describe` at `autopsy.py` line 29 samples whole issuance dates independently. This keeps same-date names together but does not handle serial overlap, repeated issuers or full multiplicity. The reproduced 95% quantiles are descriptive date-cluster intervals, not serial-overlap-robust significance. With 11 common dates, do not claim an effect is absent or a ranker has validated alpha.
- **Estimands:** episode summaries weight episode rows; baseline summaries average portfolio dates. Fixed-six comparisons are not the full 24-name board. Pool/feature restrictions, complete-selection exclusions and changing horizon maturity must accompany comparisons.
- **History:** stored board/candidate dates and current-at-pin prices do not certify first-publication UTC, point-in-time adjustment vintages or historical universe completeness. Current member coverage does not resolve survivorship. The 60-session v4 result is immature and must remain unreported as performance. Imported old research is explicitly not reexecuted here.

No remaining observed numeric/code blocker applies to this bounded retrospective diagnostic. Parent retains final adjudication, source-custody and integrated claim wording on #6871. Further execution or new evidence collection requires its existing authorized owner path.
