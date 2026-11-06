# Q09 VERDICT — INSUFFICIENT_DATA

**Overall: INSUFFICIENT_DATA** for publication-vintage and revision-stability claims, which
is what this brief asked for.

The exact missing input is FINRA weekly-summary initial-publication/update metadata per
(week, tier), plus retained multi-vintage snapshots. The licensed local store has neither:
- 0 of 21 weeks have a publisher release identity;
- 0 weeks have two or more vintages, because every week file was added once and never
  modified (git history).

The brief's falsifier binds. Output is limited to the currently released descriptive
concentration, and historical predictive and vintage claims are withheld. This rule was
fixed in PREREG §5 before any outcome was read (FREEZE.log
`7b256cb8…8a3a`, 2026-10-09T09:34:18Z).

## Pre-registered descriptive sub-result: KEEP (descriptive only; it cannot upgrade the overall verdict)

The single confirmatory comparison was run once and reproduced byte-identically on a
deterministic re-run (RUNS.log runs 1–2, results.json sha256 `263a00a1…980b`). After the
independent audit, a third run (RUNS.log run 3, results.json sha256 `772a63c8…2401`) made
only the PREREG_AMENDMENT.md changes, which are post-hoc and non-confirmatory. It
reproduced R, the CI, λ, the cohort and every holdout MSE to the last digit, and the
baseline output is byte-identical (`0c5f3e1b…f98d`).
- Target: per-symbol weekly ATS venue HHI over mpid. Tiers T1/T2; eligible when weekly
  shares ≥ 100k.
- Candidate: a multi-week shrunk per-symbol training mean. λ was chosen inside training
  only, by an inner chronological split, and came out at λ = 1.0. That is the edge of the
  grid, so in effect there is no shrinkage.
- Baseline: the incumbent-style single latest-observed-week snapshot.
- Chronological split: 14 training weeks, 7 holdout weeks. Every training week was in the
  store by the bulk commit, 2026-08-23T22:55:42Z. Every holdout week was first seen after
  it, between 2026-08-25 and 2026-10-06 (git upper bounds, not FINRA times).
- Relative holdout MSE reduction R = **0.335**. Moving-block bootstrap 95% CI
  **[0.258, 0.404]**, from block length 2 over weeks and 10,000 replicates. The bar was
  R ≥ 0.10 with a CI lower bound > 0, so the sub-result is **KEEP**.
- The candidate beat the baseline in all 7 holdout weeks. The pooled cross-section mean,
  reported but not tested, is worse than both.
- Honest N = **7 holdout weeks, about 4 blocks**. Rows (about 4.4–4.5k symbols per week)
  are not independent; resampling whole weeks keeps the cross-sectional dependence intact.
- **CI caveat.** The interval is a percentile CI built from about 4 effective blocks.
  Intervals from that few blocks are coarse, and their nominal 95% coverage cannot be
  relied on. Read [0.258, 0.404] as a rough spread, not a calibrated interval. The
  sub-result rests mainly on the sign holding in all 7 holdout weeks, not on the CI width.
- The split is clock-enforced: evaluate.py refuses to run if any training week is not in
  the store at the origin, or if any holdout week was already in it (PREREG_AMENDMENT A3).
- Support and attrition:
  - cohort of 4,812 tickers with ≥ 8 of 14 eligible training weeks;
  - 4,434–4,531 symbols evaluated per holdout week;
  - tier-ambiguous tickers dropped: 413 in week file 20260629 (T1↔T2 reclassification),
    1 in 20260413, 1 in 20260706, 0 elsewhere;
  - 20231106 excluded as a truncated remnant.

What this sub-result means: per-symbol ATS venue concentration is persistent enough that a
multi-week average describes the next weeks better than a single latest-week snapshot.
That is a measurement-stability statement about a venue/reporting category. It is not a
signal and makes no market or price claim. It also says nothing about who traded or why.
It is also close to an expected statistical property, because averaging reduces noise. It
is evidence that a multi-week descriptive projection is the steadier presentation, not an
alpha finding.

## Baseline reproduction (incumbent `scripts/build_darkpool_desk.py::_compute_ats_venue_table`)

- The logic was reproduced on the latest two ATS week files. Output is
  `baseline_incumbent_venue_table.json`, sha256 `0c5f3e1b…f98d`, with 20 venues.
- On complete ATS weeks the `mpid.str.len() > 0` filter drops 0% of mass.
- The same filter applied to the matching non-ATS week drops **100%** of mass, because
  non-ATS mpid is always empty. `engine/darkpool_signals.py::venue_split` already notes
  this hazard, and Q09 confirms it.
- The incumbent labels output by reporting week and has no availability clock.
- The collector's completeness gate {T1, T2} does not cover OTCE. A week stored before
  OTCE publishes would be silently incomplete. Every stored week does contain OTCE today.

## Descriptive concentration (latest stored week file 20260831; availability upper bound 2026-10-06T04:40:36Z)

**Universe: tiers T1+T2 only**, which is the PREREG §3 universe. The amendment
(PREREG_AMENDMENT A2) moved this from the all-tier aggregate the audit flagged. Per-tier
volumes go through `coverage_snapshot` (required tiers T1 and T2, on the store clock) and
then through `combine_tier_volumes`. All four week files (ATS and non-ATS, latest and
prior) are `complete`. OTCE is excluded and its share is printed alongside: 3.9% of ATS
reported shares and 28.5% of non-ATS reported shares.

- ATS T1+T2, over mpid:
  - HHI 0.0730, with no unknown mass;
  - effective venues 13.7 (1/HHI) and 17.9 (exp entropy);
  - the change against the prior week (−0.00005) is entirely within-venue, with 33 venues
    common and no entry or exit.
- Non-ATS T1+T2, over firm name (`venue_name`):
  - `De Minimis Firms` is 25.6% of mass and is unknown-composition mass;
  - HHI is bounded in [0.122, 0.188] if that mass is one separate venue, and up to 0.331
    if it could overlap known firms;
  - the HHI change on known firms only is −0.0094, almost entirely within-firm (1 entry
    and 1 exit, each with negligible weight).
- The unknown-mass bounds are wide. A point non-ATS HHI would overstate what is known.
- Erratum: PREREG §0 line 27 says 2,727 tickers sit in both T1 and T2 in 20260629. The
  correct count is **413**, which is the count the code drops and the count reported
  above (PREREG_AMENDMENT A1).

## Restrictions honoured

- ATS/non-ATS is a venue/reporting category, never owner intent.
- No accumulation, net-buying, live-print or short-interest reading.
  - The vocabulary guard normalises separators and hyphens and catches inflections.
  - It runs over the whole results.json dict and the baseline output before anything is
    written.
  - Prose documents (this file, PR_BODY) are not machine-guarded, because they must state
    restrictions as negations. They were reviewed by hand for affirmative use.
- The reporting week is never used as availability.
- Nothing is wired, gated or promoted (RESEARCH_ONLY), and no language model originated
  anything.
- Cited DNR keys: DNR:HOLD-PSS-AF1-FINRA, DNR:HOLD-PSS-CD1-CROWDING,
  DNR:KILL-FUSED-COMPOSITE, DNR:KILL-POSITIONING-FUSION and DNR:KILL-LLM-ORIGINATION.
