# Two relative-strength gates: first historical comparison

## Decision

**Do not promote a blanket removal of the gates. Do not treat changing the 0.85
recommendation cutoff alone as a fix for the clean-entry path.** Keep the existing
recommendation/entry policy while the source explanation repair proceeds through
independent review and release. The 0.75-veto ablation, with original quality and
actual price-risk context retained, earns a stock-level investigation, not an
automatic production change.

This result does not establish that the incumbent gates are optimal. It identifies
a specific bottleneck and quantifies the first controlled alternatives. It does
not validate the complete Prophet system, justify missed CPU discovery, or settle
how current market-wide risk should be presented alongside concentrated leadership.

## What was built and measured

`compare_entry_gates.py` extends the existing calibration/entry/extension owners
with a frozen, research-only comparison. The CLI writes a complete event audit and
machine-readable results; no production consumer reads the alternative selections.
All five candidate configurations were logged through the existing canonical
`engine.trial_ledger.TrialLedger`. Exactly five native ledger records were appended;
no existing record was rewritten and no alternative trial registry was created.

Pre-outcome protocol: `ENTRY_GATE_COMPARISON_PREREG.md`, frozen and pushed at
`59bf08ca81632451165ac2423637181d536ab9e4` before historical forward outcomes were
computed. Initial freeze `c9acbb6bf98c7d9c5d76ae9808998724741be705` was clarified only
to allow native causal rolling arrays with prefix-invariance proof; no real
forward outcome had been read. No parameters were selected or retuned afterward.

Immutable input vintage: `macro@1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee`.
The nine original SPDR sector proxies and SPY use the native Yahoo close archive,
covering December 22, 1998 through September 18, 2026 at the common endpoints.
The analysis generated **8,937 decision-time asset rows** after warm-up and
completeness gates. It is not a study of 8,937 independent trades.

The same nine-slot decision population is used in every arm. Features are causal;
scalar functions receive decision-time prefixes. The hypothetical entry is the
NEXT session's close, not the signal close. Exits are 5, 21 and 63 sessions later.
The event outcomes deduct 10 basis points at entry and 10 at exit. This is an
assumed cost convention, not a measured execution-cost model.

The native calibration's cross-sector panel breadth and neutral macro setting are
explicit proxies. They are not historical intra-sector member breadth, actual
historical macro states, or the full Prophet ranking/entry stack. The source is a
current-vintage archive, not a logged-at historical data-vintage replay.

## Fixed candidate rules

- **Incumbent:** constructive native recommendation plus native clean entry.
- **Entry veto only:** retain the recommendation and original quality. Bypass
  only the relative-strength .75 veto when the ORIGINAL quality already meets
  .60 and the copied native counterfactual passes all other entry conditions.
- **Recommendation veto only:** bypass only the dominant-theme .85 veto; retain
  native clean entry, labels, scores, crowding and trend conditions.
- **Both vetoes:** combine the preceding ablations without a new price bound.
- **Both with price bound:** keep all incumbent selections; admit an additional
  both-veto candidate only below the native per-security close-based ATR stretch
  threshold of 3. Unknown extension does not admit an extra candidate.

The counterfactual entry call's extra .20 quality credit is NOT awarded to the
original row. This separates removal of a veto from changing the quality score.

## Results

Across all eligible decision dates, including rows whose longest forward outcome
has not yet matured, the incumbent selected 692 asset/date observations. The
entry-only and both-veto arms each selected 726; the recommendation-only arm still
selected 692; the price-bounded arm selected 705. These counts are not the
fully observed 21-session sample below.

The fixed assessment partition starts in 2018. Its primary 21-session comparison
contains **434 fully observed common decision dates**. Overlapping observations
are not independent; inference is computed on chronological date-level paired
nine-slot event-budget differences using the native Newey-West estimator.

| Alternative | Additional observations | Mean additional net return | Mean additional return vs SPY, net of cost | Negative net outcomes |
|---|---:|---:|---:|---:|
| Entry veto only | 14 | +1.73% | +1.14 percentage points | 6 of 14 |
| Recommendation veto only | 0 | Not applicable | Not applicable | Not applicable |
| Both vetoes | 14 | +1.73% | +1.14 percentage points | 6 of 14 |
| Both, with native price bound | 7 | +3.01% | +4.34 percentage points | 2 of 7 |

These are means of the ADDED observations, not returns for a portfolio, an account,
all the selected signals, or CPU stocks. Seven and fourteen observations are too
few to establish reliable conditional behavior. No added observation in this
assessment happened to breach the -8% entry-relative close-path reference, but
that small-sample zero is NOT a guarantee of safe entries.

After correcting all four primary comparisons together, **none passes the
predeclared statistical screen**: entry-only / both-veto q=0.6437, price-bounded
q=0.5348, recommendation-only q=1.0. The raw paired p-values are 0.4828, 0.1337 and
1.0 respectively. These are not probabilities that the strategies work.

The earlier development partition also does not establish a stable improvement.
Its entry-only added cohort has 19 observations, mean net return +1.02% and mean
net relative return approximately -0.01 percentage points. The price-bounded
cohort has six observations, mean net return -0.49% and net relative return +0.37
percentage points. The seemingly stronger later-period price-bounded result must
not be selected while ignoring that history.

The baseline proxy itself is not a demonstrated investment edge: its 340
fully observed assessment selections average +0.15% net absolute and -0.52
percentage points relative to SPY. This is a limitation of the proxy experiment,
not a claim about the realized performance of the complete deployed Prophet.

## What this rules in and out

The .85-only change produces no extra clean-entry observations. The stricter .75
condition remains upstream of the final combined entry permission. A regression
also proves that inclusion relationship across a dense synthetic RS boundary grid.
The .85 condition can still alter THEME recommendation copy and visibility; it is
not globally redundant in every product or model path.

The .75 restriction can suppress otherwise-qualified entries. Some additional
observations are profitable in the later sample, and the native price-bound
candidate retains a narrower subset. That is an investigable direction, not
sufficient evidence to turn every high-relative-strength name green.

The proper next modeling question is stock-level: preserve complete candidate
visibility, distinguish subtheme leadership from a broad-sector cap, and evaluate
current-price entry/protection evidence. Use the existing Prophet candidate and
entry owners, not a CPU whitelist or a new ranker. Keep the same decision-time
population and preserve adverse as well as favorable outcomes.

## Missingness, time boundaries and interpretation limits

Six dates are present in the current calendar's expected grid but absent from
all the archived input series: 2001-09-11 through 2001-09-14, 2004-06-11 and
2007-01-02. They are recorded as **archive/calendar mismatches**, not invented
prices. The study does not adjudicate their historical calendar meaning.
The complete-504-session rule excluded 2,727 potential asset/date decisions.
This conservative exclusion materially limits the available historical periods;
calendar-owner reconciliation is a named independent follow-up, not a reason
to fill holes or tune the sample after seeing results.

Across all horizons there are 26,145 observed asset/date/horizon outcomes, 504
future-path missingness dispositions and 162 immature-tail dispositions. Another
162 outcome records crossing the fixed development/assessment boundary are
excluded from those partition comparisons. Horizon records are repeated outcomes
on the same decision, not additional independent signals.

Maximum adverse excursion is measured from entry, not from a later peak. The
fixed nine-slot event-budget score leaves unselected slots in zero-return cash
and does not compound overlapping bets. It is not capital-feasible portfolio
P&L, CAGR, Sharpe, execution simulation or a claim of better live recommendations.

## Verification and reproduction

- **36 new tests** discriminate native vetoes, retained original quality,
  unchanged trend/label conditions, missing/unknown extension, dated source
  completeness, prefix invariance, delayed entry, forward-path gaps, outcome
  maturity, boundary purging, event identities and date-level denominators.
- **205 Python 3.14 owner/consumer/detail tests passed.**
- **197 overlapping Python 3.12 tests passed.**
- Existing **10,584-case native recommendation parity** remains unchanged.
- Both new source and test paths are registered in the existing hosted CI owner.
- Existing 48-cell browser evidence is not rerun or upgraded to production proof:
  the present comparison makes no changes to those UI/engine source paths.

```sh
python3 research/sector_pulse/recommendation_reasons_20260921/compare_entry_gates.py \
  --source-ref 1e767a2f5b43f302b0e1068c9a7e60b12aeb98ee \
  --prereg-commit 59bf08ca81632451165ac2423637181d536ab9e4 \
  --output /tmp/theme-entry-gate-comparison
```

Use the existing native trial ledger, not an empty replacement. An identical
rerun deduplicates the same five configs; any genuine new config must count as
new research. Inputs, native owners, frozen protocol, study module and compressed
event rows are SHA-256-bound in `comparison.json`. `events.csv.gz` preserves the
complete auditable event population; `summary.json` and this report are views.

**MISSION_COMPLETE: false. PRODUCTION_POLICY_CHANGED: false.** The bounded
historical comparison is complete. Independent review, current-head release
checks and actual producer-to-consumer production evidence remain separate gates.
