# Final integrated-claim review

Operation: `MMX-CN-PROPHET-CENSUS-REVIEW-FINAL-20261009`  
Date: 2026-10-09  
Verdict: **PASS — the two material document findings below are resolved.** The initial review requested changes; the author corrected them and this reviewer verified the final wording. No new historical experiment, public search or implementation was required.

## Scope and reviewed identity

Reviewed `REPORT.md`, `EXPERIMENTS_AND_ACCEPTANCE.md` and `IMPLEMENTATION_HANDOFF.md` against the accepted historical evidence, historical evaluation/review and China market/research memo. The concurrently edited mechanism census was deliberately not reviewed. Pipeline, ordering and publication observations were checked for consistency and appropriately limited claims, not independently re-executed. PR states and source-custody observations remain the originating workers' observations.

| Reviewed file | SHA-256 after verified corrections |
|---|---|
| `REPORT.md` | `31eb6ab4cd37f427f62df216502ac96186c209e51a2b10402be364877c4458c7` |
| `EXPERIMENTS_AND_ACCEPTANCE.md` | `4f2fb3def10272bd0877a615579c692358371b3e20fc087a83c2338d2cdfd1c7` |
| `IMPLEMENTATION_HANDOFF.md` | `db14abc3b8c84e9982f6e0d652f1f0d223b613f1374cc37b069e358a650ea34b` |

The supporting public memo's refreshed introduction, T+1 proof wording and cap-versus-quota language were also checked at SHA-256 `884a1a52aabcd54881ee56e52eae93c7fdaaadb03f3f8d4f4b973e42cee65780`. Its official-source rule distinctions and research-transfer limits remain consistent with the accepted research.

The accepted historical numerical evidence remains SHA-256 `8b651cf4df19736f66a3cf184c5a47478ffe0bf2fc62a24bb5452c01b836e54d`; its reviewed claim memo remains `49096c1197adb12bc29e526497700aa87073852ab3aee73d6e9efdc4fec668c0`. This review does not alter that acceptance. The separately requested rank-metrics addendum and any subsequent report insert were not yet part of this reviewed snapshot and are not pre-approved here.

## Resolved findings

### F1 — Inconclusive comparison summarized as a superiority verdict — RESOLVED

**Location:** `EXPERIMENTS_AND_ACCEPTANCE.md`, §1 table, line 17, “Common-cohort baseline race.”  
**Severity:** P1, statistical/experiment-identity claim.  
**Initial wording:** “Every paired 95% interval crosses zero; intended intelligence is not superior.”

The first clause does not establish the second. The accepted historical evaluation §3 says no stable advantage is demonstrated and explicitly rejects proof of no alpha. The integrated report correctly preserves that distinction at §C, lines 98–108. The experiment summary should not contradict it.

The historical arm is also a stored-intelligence-score ranking diagnostic within a restricted common-feature pool. It must not be presented as validation of the full intended V4 policy, which includes its eligibility/coverage contract and intelligence→V3-score→ticker ordering. The reviewed historical `top6` baseline orders the selected feature then ticker; it is not the same complete policy described at `REPORT.md` §B, line 58.

**Smallest repair:** replace the observed-result cell with:

> Every descriptive paired date-cluster interval includes zero; the stored-intelligence ranking baseline did not demonstrate stable superiority on this common cohort. This does not establish equivalence or the performance of the full intended V4 policy.

The existing “do not promote from this sample” decision remains justified. No data or numerical table needs changing.

**Verified resolution:** `EXPERIMENTS_AND_ACCEPTANCE.md` line 17 now says no stable superiority is demonstrated for the stored-intelligence-score baseline. Line 20 explicitly distinguishes its ticker tie-break from the exact intended intelligence→V3-score→ticker policy. `REPORT.md` lines 103 and 108 make the same distinction. The final documents no longer turn an inconclusive result into a superiority/equivalence verdict.

### F2 — Precision denominator ambiguous for unresolved frozen picks — RESOLVED

**Location:** `EXPERIMENTS_AND_ACCEPTANCE.md`, §2 “Metrics and uncertainty,” line 44.  
**Severity:** P1, acceptance/selection-missingness contract.  
**Initial wording:** “Precision@K: proportion of the frozen K picks with positive excess return … Report unresolved outcomes separately from the denominator.”

This does not specify whether the denominator stays at issued K or shrinks to the observed subset. The latter can reward a policy whose difficult outcomes disappear, undoing the intent of the frozen-selection rule at line 28. Retaining the selected ticker in a ledger is necessary but does not by itself define an honest performance denominator.

For example, three observed winners, two observed losers and one unresolved pick yield 3/5 conditional precision, but not an identified precision for all six issued picks. Treating 60% as the full fixed-six result would conceal the missing outcome. The known-positive lower bound is 3/6 and the upper bound is 4/6; neither assigns the unresolved outcome a realized loss or win.

**Smallest repair:** require issued K, observed count, unresolved count and coverage beside the result. Grade full-K precision only for complete outcomes, or explicitly label `wins / observed` as conditional and show fixed-K bounds `wins / K` through `(wins + unresolved) / K`. Preserve unresolved selections without replacement or silent zero-filling. State the complete-date/paired-coverage rule used for comparisons, and return inconclusive when material unresolved outcomes could change the promotion conclusion.

This clarifies the future acceptance contract; it does not invalidate the accepted 11-date historical comparison, whose selected outcomes are complete for all five compared arms.

**Verified resolution:** line 44 now requires frozen K, observed count and unresolved count; primary comparisons use complete-K dates. Observed-only precision is explicitly conditional and must show the fixed-K lower/upper bounds. Unresolved names cannot be silently dropped or replaced. This restores an unambiguous performance denominator while preserving honest missingness.

## Controls and conclusions preserved correctly

- **Historical arithmetic:** the integrated report matches accepted 133/289 latched versus 129/289 current-entry wins, 16 sign changes, the separate 288-row matched-close result, and the 11-date/66-selection common-feature table. It does not infer that the difference between the two H10 measures is benchmark-clock bias.
- **Causal limits:** `REPORT.md` §D explicitly separates observed mechanism/measurement effects from an allocation of investment losses. The 4/24 current ordering overlap is used as selection sensitivity, not return evidence. No correction is promoted as proven alpha.
- **Statistical limits:** numerical board-rank direction is correct. Date-cluster intervals remain descriptive; serial overlap, repeated issuers, multiple testing, cohort maturity and narrow regime coverage remain explicit. The +0.25 pp hurdle and extraction thresholds are proposals for ratification, not measured results or already accepted release gates.
- **Execution limits:** signal marks, current reconstructed entries, stored latches and executable outcomes remain distinct. The benchmark-open counterfactual is unavailable; HL2 lacks an identified intraday clock. T+1 prohibits selling newly bought ordinary A shares in the purchase session, without implying that intraday buying is forbidden. Flat adjusted bars are not treated as authoritative legal limits.
- **China/source facts:** the current July 6, 2026 main-board ST change, different domestic/Connect access, quarterly Northbound holdings, Beijing exclusion and public-source coverage caveats are consistent with the accepted market memo. The report acknowledges existing calendar/ST implementations instead of inventing their absence as a root cause.
- **Governance and ownership:** #6871 retains R0 custody and disputed historical claims stay disputed; #8714 stays a research Draft/HOLD. Existing CIE restrictions, settled private TuShare compliance and killed constructions remain intact. The handoff proposes existing-owner work rather than activating a new pipeline, vendor, runtime, trade or sizing authority.
- **Completeness boundary:** the A–G structure and eight-question closure are present. Unavailable H60 V4, certified PIT valuation, full matched-random portfolio, net execution, portfolio risk and broad regime comparisons are identified rather than fabricated. The separate rank-metrics addendum still needs its assigned review.

## Closeout

No remaining material factual, causal, statistical, governance, execution or scope contradiction was found within the corrected three-document snapshot. F1 and F2 are closed. Preserve the accepted evidence and regenerate the applicable document manifest after integration. Later numerical addenda require their own bounded check; the accepted historical files need not be rewritten.

Only this `FINAL_REVIEW.md` was written. No author file, accepted historical result or canonical repository item was modified by this reviewer; no new search, host call or data experiment was performed. Parent retains final adjudication and integration. This bounded operation is terminal.
