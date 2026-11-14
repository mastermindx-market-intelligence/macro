# Independent transition-repair pilot - preregistered exploratory screen

Current Chairman assignment: independently investigate and test contextual gates around existing dot/T1-T3 entry signals, reducing false bottoms and catastrophic buys while preserving useful entry coverage. This pilot is not the incumbent gate programme, not a new execution registry, and not authority to change live signals or trading.

Procedure pin: Mastermind protected master 199fd4f91ecc426b1d974eb3bf47f5162476cf24, skillpack 1.0.1. Principal retained for PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD. Existing context: macro issue #11014; preserve its active workers and reserved datasets.

## Scope and non-goals

Use public Kenneth French 49-industry daily value-weighted returns and daily Fama-French market/risk-free data. Filter dates <= 2002-12-31 before numerical parsing. No 2003-2019 industry confirmation outcomes, no 2020+ outcomes, no private stock/dot panel, no raw data committed, no PR, no production modification. Current-vintage historical data is not a point-in-time-vintage archive. Internet downloads may contain later rows, but the parser must discard them before constructing numerical arrays. Historical data through 2002 is exploratory, not claimed virgin or confirmatory.

Research objective: discriminate repair of a previously weak recipient from an exhausted recipient alone, and determine whether prior-leader rollover adds evidence beyond recipient repair. The public pilot tests sector mechanisms only; it cannot validate proprietary dots or stock-level confidence.

## Fixed design before outcome reads

Monthly decision dates: last available session per calendar month. Earliest eligible observation follows 252 valid daily returns. Entry at next-session close (one full session delay). Label horizon 63 sessions after that entry, with 21-session return secondary. Drop incomplete future windows rather than shorten them.

Candidate: industry's prior 126-session total return < market's and its total-return index is at least 10% below its trailing 126-session high. All required current/history inputs must be finite. No outcome-based event selection.

Primary gate R (recipient repair): prior 21-session industry return is positive AND exceeds market return. Compare R=1 against R=0 within candidate population.

Primary gate D (prior-leader rollover): identify top industry tercile using relative returns over t-252 through t-22, excluding focal industry. D=1 when those leaders' equal-weight average relative return over t-20 through t is negative. This is leadership rotation, not proof of fund flows.

Primary gate V (stress receding): market realized daily volatility over the latest 21 sessions is below its 63-session value. This is a transparent short-vs-medium volatility state, not a claim that a crisis has ended.

Primary comparisons: R; D incremental within R; V incremental within R. Show full R x D x V cells, not just selected winners. Hypothesized signs: R lowers downside and improves 63-session relative return; D may help only with R; V lowers downside among R. Either sign may be falsified.

Outcomes: positive 63-session net return (20 bp assumed round-trip cost); 63-session excess return versus market; maximum closing loss from entry; occurrence of >=10% closing loss within 63 sessions; terminal net return. Additionally a volatility-scaled competing-barrier outcome: hit +2*sigma63*sqrt(21) log-return barrier before its symmetric downside barrier within 63 sessions; downside-first and unresolved remain distinct. Sigma fixed at decision date. Industry indices are not directly tradable, so all economic results are mechanism screens, not implementable performance.

Inference: report events, distinct decision months, coverage, calendar-era partitions (1927-1962, 1963-1982, 1983-2002), and 95% moving-block bootstrap intervals using 12-month date blocks, 2000 replicates, fixed seed 20261114. Preserve all industries together per sampled month. Event means are not portfolio returns. Additional same-month control/matching must be labelled a robustness diagnostic, not replace the registered raw result.

## Required falsifiers and verification

- R's apparent safety must be checked against distance from trailing low, absolute drawdown and trailing volatility. Recovery-distance geometry alone is not durable-bottom discovery.
- Absolute and excess returns must both be printed: outperforming a falling market does not imply a profitable long.
- D must beat recipient-only conditioning; a weak source does not identify a destination.
- Repeat outcomes with one additional session execution delay as declared sensitivity, without selecting the better version.
- A prefix-invariance check must demonstrate features are unchanged when later data are omitted. Missing values must never become zero returns.
- Report nulls, sparse cells, dependence and contradictory eras. No calibrated stock win percentage can be inferred from this pilot.

## Deliverables and completion ruler

Reproducible code, input hashes and retrieval provenance, all planned result cells and diagnostics, source-based independent thesis, explicit next stock-level experiment, saved on this isolated research branch with readback and one result comment to existing #11014. Completion of this pilot is not completion of the broader Prophet programme. No new worker or watcher is commissioned.
