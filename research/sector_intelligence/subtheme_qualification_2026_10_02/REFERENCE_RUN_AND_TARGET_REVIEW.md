# Public reference execution and emergence-target adjudication

Date: October 2, 2026 Pacific (UTC observations extend into October 3).
Parent: Macro #7749 / #8299 / WS:PROPHET-US-V4-RECOVERY.
Operation: subtheme-takeover-replay-qualification-20261002-sol-001.
Protected procedure: Mastermind@bf1fa1db3147105e9ac3d4f7f4d20ef8efd59cba.

This is a research continuation and exact execution receipt, not a new scorer,
workstream, source store, production acceptance, or trading authorization.

## 1. What became true

The prior source head 6b51972e25919799dce986ce2d5c7104dacacbb6 passed hosted
CI 37087602005 and fences 37087601847. This closes the earlier test-registration
failure at THAT head, not independent scientific review or acceptance of later heads.

A new, separate public-industry reference implementation was committed in
6f1e1585db669ee6a152d61d66ee54c227fbaced and actually executed on the M2.
Its source is industry_reference.py in this directory. It reads only two explicitly
supplied public French-library ZIPs; it does not read any Mastermind price/member
store and does not resume the previously refused Mastermind-data inspection.

The direct public-data download returned process 78377 and exit 0. The source-pinned
computation returned process 87113 and exit 0. The command checked the script's
SHA-256 before executing it. A result file was produced and its SHA-256 was returned.
This establishes completed computation on actual provider data, NOT adjudicated
performance, independent review, or a qualified Mastermind microtheme backtest.

## 2. Immutable data/code/result references

Primary inputs:
- https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/49_Industry_Portfolios_daily_TXT.zip
- https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_TXT.zip

Provider methods and revision disclosure:
- https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html
- https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

The inspected headers say 202608 CRSP database; the files extend through 2026-08-31.
The source is a current provider-reconstructed vintage. The provider's library says
it reconstructs the full history and historical returns can change. Do not call the
2016-2025 evaluation an untouched institutional point-in-time holdout.

| Object | SHA-256 |
|---|---|
| Industry ZIP | 8382c46abe6f62363bf9956284c3933f6e6d49928c9b5e338545e87e39e27f87 |
| Factor ZIP | cde5caa44cfbe81d4367bf62dc3aaee6124c81b318987a2d78ebd7d3d46eba42 |
| Executed industry_reference.py | d95f7d7ee8d06ac296a776f8b17476730aeabdb594b2a78d32016a789fea2977 |
| Completed result.json | 7c3899d46eee0de2240d674427ac81c0f931810ca017bbf9baff25a7179020ba |

Retained executor directory: /private/tmp/mm-subtheme-public.K9YVUn.
Files: industries.zip, factors.zip, industry_reference.py, result.json, run.log.
These are retained process artifacts, not a new canonical market-data store. Temp
retention is not guaranteed. Raw third-party data is not copied into this public PR.

The original local pre-analysis text had transcript SHA-256
0d6a7c6d733078f49b24bf51067119fb5756a64f60bf2a734fd184c43f2d78ac before
reading the return files. A compact recovery record preserves the choices; it is
not claimed to be a formally registered, independently attested preregistration.

## 3. Frozen reference specification

Use 49 value-weighted industry return series, sorted by their source column names.
Daily market return is Mkt-RF plus RF, not Mkt-RF alone. Treat -99.99/-999 as missing.
Match the provider calendars; require complete feature and outcome cross-sections.
1988-1989 warmup; 1990-2009 development; 2010-2015 validation; 2016-2025 evaluation;
2026 observations excluded from performance. No post-result parameter selection.

Six fixed signals at close t:
1. trailing 20-session relative log return;
2. trailing 60-session relative log return, the baseline;
3. trailing 252-session relative log return skipping the latest 21 sessions;
4. mean last-five relative log returns minus mean preceding-fifteen;
5. fraction of positive relative-return days over 20 sessions;
6. signed relative-log-return sum divided by absolute-relative-log-return sum over 20.

Primary H=10, descriptive robustness H=5 and H=20. Outcomes use precisely t+1..t+H.
Top 10 of 49, NOT a top decile. Same eligible dates for all six models. Metrics:
date-level Spearman IC, HAC lag 2H intervals, paired IC delta versus the baseline,
Holm adjustment across five primary challengers, future top-10 overlap, top-10
market-excess returns, and frozen initial-weight daily-close adverse excursion.

The nested incremental check is an expanding annual ridge regression, training from
1990 and testing each year 2010-2025. The baseline uses mom60; the challenger uses
mom60, mom20, acceleration, persistence, efficiency. Rank-transform features;
normalized-Gram penalty fixed at 1; purge at least 20 provider sessions before each
test-year boundary and require all training labels to mature before it. No industry
identity feature, parameter search, probability calibration or production champion.

Separate hypothetical portfolios use equal-weight top 10, trade at the next CLOSE,
and first earn the new position's return on t+2. Include initial cash, drift,
post-cost self-financing target weights, final liquidation, and 0/5/10/25 bps on
purchases PLUS sales. Equal-49 and market comparisons use the same date ranges.
This is simulated industry-index exposure, not a traded ETF, stock execution,
capacity proof, or constituent-level transaction-cost estimate.

Twenty-five per-date label-shuffle trials use seed 20261002. The permitted process
tail reported shuffled mean IC 0.000528026993545022, range
[-0.007840231140379475, 0.006863019169329073]. This is a negative-control diagnostic,
not the signal's measured edge, a multiple-testing-adjusted p-value, or validation.

## 4. Results boundary: completed run, detailed results NOT reviewed

After the successful run, a separate command to read result.json, produce a compact
summary and print the detailed metrics was blocked by OpenAI before any process
receipt: 'we could not determine the safety status of the request.' The intended
summary write has no confirmed effect. Do not assume summary.json exists.

That action is stopped, EFFECT_NONE, and was not retried through different wording,
tools, hosts, workers or another route. The older Mastermind raw-data refusal also
remains stopped. No detailed performance table is invented from the short log tail.

Thus the correct state is: PUBLIC REFERENCE COMPUTATION COMPLETED / RESULTS
ADJUDICATION BLOCKED; MASTERMIND PIT REPLAY NOT RUN. No hypothesis is endorsed or
rejected by the unreviewed full result. The stored output still needs provenance,
coverage, sensitivity and independent scientific assessment after permitted recovery.

## 5. Two substantive corrections to the Deep Research target proposal

These are mathematical/source-contract findings, not new empirical market results.
They critique the report's proposed target, not a proven live production defect.

### 5.1 A rolling-rank transition can occur with zero new information or return

Consider four trailing daily returns:

| Group | Returns in the current four-session window | Current window return |
|---|---|---:|
| A | -20%, +5%, +5%, +5% | -7.39% |
| B | +1%, +1%, +1%, +1% | +4.060401% |
| C | 0%, 0%, 0%, 0% | 0% |

Tomorrow every group returns exactly zero. A's old -20% observation expires; its
new trailing return becomes +15.7625%. B's trailing return becomes +3.0301%.
A becomes the rolling-return leader although every group's new absolute and
relative return is zero. Predicting this transition does not anticipate new inflows.

For relative log returns x and h <= L:

    S_L(t+h) - S_L(t)
        = sum(new x from t+1 through t+h)
          - sum(expiring x from t-L+1 through t-L+h)

The expiring term is already known at t. A carry-forward placebo should forecast
future rolling scores by removing those known expiring observations while setting
new relative returns to zero. A model must be compared against that placebo before
its rolling-rank transition skill is called early intelligence.

Proposed owner decision: keep descriptive transition, persistence and NEW forward
relative payoff as separate labels. Report carry-driven crossings explicitly. An
entry into a trailing-return percentile is not sufficient evidence of positive
future return, profitable execution, independent accumulation, or improved economics.
Do not silently redefine or promote the current canonical target.

### 5.2 Confirmation extends label maturity beyond the stated emergence horizon

The report proposes entering leadership within ten sessions and then remaining in
a band for at least three of the following five sessions. A crossing on session
10 can depend on observations through session 15. A ten-session embargo or nominal
label end would therefore permit future confirmation information into training.

Keep decision time, crossing time, confirmation end, actual label-known time and
execution time separate. A conservative fixed label maturity is H+P sessions plus
input availability latency; any earlier stopping rule must be explicit and tested.
Purging and censoring must use actual outcome availability, not just the title
'10-session emergence'. The existing qualification.purged_training_ids already
supports the correct clock when supplied truthfully.

## 6. Verification and exact scope

Thirty new local synthetic checks passed, including the 28 reference-engine cases
and the two target discriminators above. They cover parser/date refusal, true
session horizons, future-data mutation, missing-loser exclusion, execution delay,
self-financing entry/exit costs, cost monotonicity, tie handling, HAC, Holm and
training-label chronology. Thirty exact relocated cases also passed locally.

All 30 are physically appended to the existing CI-owned
 tests/test_subsector_track_record.py
in commit 669005897870b755cdaa02de6fbb51621f552a07. Its entire previously accepted
31,717-byte prefix is unchanged, including the original ten owner tests and all
107 earlier qualification/seam cases. No new pytest file, waiver, workflow,
skip or shared CI-manifest modification was introduced.

New owner-test file: 37,681 bytes; Git blob
303ee5b362736a68b7998ee9b433b29edfb33900; SHA-256
defb472244a65ab05d69884f13161bbda012b6b96ffe15159a7c75a716866650.

The local proof executes the exact added block, not the full production-engine
import chain. New-head hosted CI and independent review remain required. Tests
prove software cases, not historical investment profitability.

## 7. Fabric and continuation

The current canonical executive_fabric roots preflight at 2026-10-03T02:37:40Z
returned mode=readonly and ceo_submit_armed=false. It enumerated seven terminal roots,
none queued/running, with no truncation. This establishes a disabled submission arm,
not absence of every provider or every possible worker elsewhere in the fleet.
No worker, dispatch, watcher or autonomous wake is claimed. No direct-provider
spawn or alternative queue was used.

Preferred division once positive admission exists: routine source inventory and
fixed replay execution to the least-scarce qualified worker; statistical review to
an independent capable reviewer; principal retains target decisions and integration.
Provider preference (MiniMax/GLM/frontier) is not an admission or budget receipt.
Do not send a refused data action to another actor to evade its gate.

Next: consume exact-head CI; independent review of the code and target correction;
permitted recovery of the original result-inspection action; then review the retained
public result without changing parameters. Separately recover and qualify actual
Mastermind PIT inputs before claiming subtheme, Prophet, or production value.

MISSION_COMPLETE: false. All ranking/gating/sizing/trading/promotion flags remain
false. No live collector, model, candidate population, publisher or deployment changed.
