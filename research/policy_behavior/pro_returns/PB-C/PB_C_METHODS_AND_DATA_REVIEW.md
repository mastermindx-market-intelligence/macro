# PB-C — Statistical design and source-access review

Advisory return to the sole integration owner. Research-only; no production collection, GitHub write, provider procurement, signal promotion, or event-return study was performed by this helper.

## 1. Decisive findings

The frozen 2025 study can support a source-verified event panel and exploratory timing diagnostics. It cannot estimate the population probability of a freely timed announcement after stress until source coverage makes both captured events and no-event issuer-days observable. A source search with no result is not such a denominator.

The exact prescribed Treasury sensitivity data are accessible from original U.S. Treasury XML feeds. The completed derivation uses **two-year nominal par yields** (`BC_2YEAR`) and **ten-year real par yields** (`TC_10YEAR`), separately. It does not substitute ten-year nominal yields, use FRED data, or inspect event-return outcomes. The source has 249 dated observations per instrument in 2025, while the separately reconstructed NYSE calendar has 250 sessions. The calendar includes the extraordinary January 9 closure, which was announced by ICE on December 30, 2024. [D01–D03, C01–C03]

With the protocol's increase of at least 25 basis points over five NYSE sessions, there are only **two new nominal two-year stress episodes** and **one new real ten-year stress episode** in 2025. The latter includes two consecutive qualifying closes. Those within-instrument onset counts, rather than thousands of issuer-day rows, describe the sparse stress variation available. The April nominal and real episodes overlap; two plus one must not be treated as three independent economic shocks.

The FRED and Cboe source terms require a narrower disposition than “publicly downloadable, therefore reusable.” FRED labels NASDAQCOM as pre-approval-required and VIXCLS as citation-required, but its current services terms also contain an AI/software-development restriction. Cboe's general terms separately restrict reuse and derivatives beyond its limited personal license, with a fair-use exception; its content-use page describes a signed-license process. No Nasdaq or VIX raw data was fetched for this analysis. These equity exposures remain **RIGHTS_UNRESOLVED / NOT_MEASURED** in this commission. This is a conservative source-admission decision, not a definitive legal opinion that every research use is unlawful. [D04–D08]

## 2. Executed Treasury derivation

### Exact operation and files

`derive_treasury_stress.py` fetched four bounded original-source files: nominal and real rates for 2024 and 2025. It retains the 2024 Q4 warmup for the calculations. XML bytes are kept only in the task-local `local_inputs/` cache and are not part of the proposed published return. Publication candidates are:

- `derive_treasury_stress.py`: reproducible derivation, original Treasury endpoints only.
- `rates_sensitivity_stress_calendar.json`: 365 date rows of derived exposure flags, prior observation dates, and source-age metadata.
- `nyse_calendar_2025.csv`: 250 official-calendar session dates and regular or early closing times.
- `treasury_stress_spec.json`: instrument, lag, calendar, episode, and parent-protocol identity.
- `treasury_stress_manifest.json`: response status, exact endpoints, byte counts, SHA-256 digests, and aggregate results.
- `treasury_derivation_checks.json`: selected independent XML arithmetic and temporal-integrity checks.

The two 2025 Treasury responses were HTTP 200. Nominal response: 345,104 bytes, SHA-256 `9de79baddd55ee58dd74a3bc1191d5c90f00b222bea40fa54c061f8cdeadfb62`. Real response: 226,335 bytes, SHA-256 `cdb3f71eae2d68cae936684385fcb0fb6f7a05ea3fc3cc227f28b18ba8b48ec3`. Both contain 249 dated entries. The manifest includes the 2024 warmup receipts.

### Definitions actually implemented

For a NYSE session `t`, take the most recent Treasury observation dated on or before `t`. Retain its actual source date. This carries the previously published rate across the two 2025 equity-open bank holidays, October 13 and November 11, rather than fabricating a quote or treating missingness as a zero. Then compute, separately for each instrument:

`change5_bp[t] = 100 × (yield_percent[t] − yield_percent[t−5 NYSE sessions])`

`shock[t] = 1(change5_bp[t] >= 25)`

For an event calendar date `d`, use NYSE sessions **strictly earlier than d**. The primary exposure is any qualifying shock within the latest five such sessions; the sensitivity uses ten. This deliberately does not exploit a same-day closing value, even for after-hours announcements. A new episode requires ten preceding non-shock sessions. Carryover from 2024 is retained but is not relabeled as a new 2025 episode.

Historical Treasury source dates are not an exact intraday publication log. The rate notes describe indicative quotations and curve estimates; they are not individual transaction prices. The nominal curve notes say input quotes are obtained at or near 3:30 p.m. The real series consists of interpolated TIPS par yields. Consequently these flags are **current-vintage, prior-date retrospective proxies**, not a certified replay of what a live observer had ingested at each historical timestamp. [D02, D03]

### Results

| Measure | Two-year nominal | Ten-year real |
|---|---:|---:|
| Qualifying 2025 NYSE shock sessions | 2 | 2 |
| New 2025 episodes | 2 | 1 |
| Episode-onset dates | April 11; May 14 | April 10 |
| Calendar days exposed in prior-five-session definition | 17 | 11 |
| NYSE event dates exposed in prior-five-session definition | 10 | 6 |
| Calendar days exposed in prior-ten-session definition | 32 | 24 |
| NYSE event dates exposed in prior-ten-session definition | 20 | 14 |

Five-session exposure ranges:

- Two-year nominal: April 12–21 and May 15–21, 2025.
- Ten-year real: April 11–21, 2025.

Ten-session sensitivity ranges:

- Two-year nominal: April 12–28 and May 15–29, 2025.
- Ten-year real: January 1–6 from inherited 2024 stress, and April 11–28, 2025.

For a chronologically selected source-frame audit, the earliest seven-calendar-day window beginning with primary rate exposure is **April 11–17, 2025**. A Monday-to-Sunday convention would instead select April 14–20; the integration owner must state that convention before looking at the relevant archives. A certified empty window would establish only that no eligible original item appeared in the specifically enumerated source frame, not that the company or all counterparties made no announcement anywhere.

Verification independently recomputed selected changes directly from XML: nominal two-year April 11 versus April 4 is +28 bp; May 14 versus May 7 is +27 bp. Real ten-year April 10 versus April 3 is +43 bp; April 11 versus April 4 is +45 bp. Checks also established 365 output days, 250 equity sessions, January 9 exclusion, strict prior-date joins, and inclusion of every five-session exposure in its ten-session counterpart. These checks do not validate announcement capture, economic interpretation, or causal effects.

## 3. A study population, an event panel, and a risk set are different objects

The parent protocol freezes 36 legal issuers for January 1–December 31, 2025, with 2024 Q4 warmup. The fixed strata are appropriate for transparent scope, but conventional firms have not yet earned a “matched” label. GOOG/GOOGL must remain one issuer; source-country date/time and US ADR mapping must remain explicit for TSM.

The full nominal grid contains 13,140 issuer-calendar-days, or 9,000 issuer-NYSE-sessions. Those counts are arithmetic, not a claim that every day has been observed. Each issuer-day needs coverage status such as:

| Coverage state | Meaning | Permitted use |
|---|---|---|
| Certified within stated source frame | Every eligible archive page/filing/source required by that frame was enumerated for the interval | Source-frame no-event counts and source-frame arrival rates |
| Partial | Some eligible sources/items are verified, completeness is not established | Positive event facts and selected-panel diagnostics |
| Missing | Required source route could not be inspected | Unknown; never zero |

The risk-set outcome must reflect the corresponding source-defined estimand. “No official newsroom release in a fully enumerated week” is narrower than “no economically material announcement.” Investor-relations archives, product blogs, filings, government award notices, partner releases, and live conference statements can each contain unique first disclosures.

The deterministic first-2025-earnings control is useful because its acquisition rule does not select favorable returns. It is still a selected one-event-per-issuer sample, not an annual earnings census. Preliminary results can precede full scheduled results. Preserve the preliminary record as the literal first results release, or log a pre-test amendment defining the control as the first full scheduled release. Do not silently choose the more regular date. Different answers to these two control definitions are informative calendar sensitivity, not an inconvenience to remove.

## 4. Identifiers and classifications that prevent false clusters

Keep separate identifiers for the source document, original source family, atomic root economic event, issuer involvement, and broader program. A joint contract released on both counterparties' sites remains one root event with two issuer involvements. A later actual financing close or commercial execution can be a distinct stage or event if it contains genuinely new economics; a syndication copy is never such an event.

Recommended clustering rules for this pilot:

1. Count atomic root events once in aggregate timing. Use event–issuer rows only for issuer-specific outcomes and never pretend those rows are independent.
2. Merge source copies and cross-publisher manifestations before measuring proximity.
3. Preserve known joint programs/conferences as a separate cluster field. Report raw root-event proximity and the sensitivity that coarsens a common program to one cluster.
4. A directed sequence requires actual ordering. Same-day date-only disclosures support proximity, not a direction of influence. Unknown timezone or merely republished time must not become an exact first-public timestamp.
5. For the strict cross-firm statistic, require disjoint issuer sets for the two roots. Report shared-issuer pairs separately; otherwise a single issuer's serial communications can masquerade as a many-firm sequence.

Classify economic direction and materiality without reference to subsequent returns. An authorization to repurchase shares is not proof of execution; a conditional commitment is not the same as cash received; an offtake or price floor has contractual contingencies. Scheduled earnings containing a buyback, capex, partnership, or guidance decision remain calendar-timed disclosures for the timing analysis. Unknown scheduling is not evidence of freedom to choose the publication date.

A direct-documentation claim of coordination requires a separate evidentiary record: actor, decision/instruction, contemporaneous date, document/source, intended scope, and connection between that instruction and the observed announcement. A pre-existing government contract establishes a relationship of its particular kind. It does not establish an instruction to support equity prices. Timing and return persistence alone cannot fill that gap. Credible convergent observational evidence could support a graded inference without a private instruction document, provided selection, calendar and common-cause alternatives are adequately tested; this pilot does not meet that standard.

## 5. Estimation and null models

### Complete-risk-set model: proposed, not fitted

After coverage certification, estimate species-specific counts or a binary arrival outcome, with issuer and calendar controls, on the same admitted source frame. A conditional Poisson formulation is a reasonable first method for repeated counts; use a log exposure offset only where the duration or number of eligible risk units actually varies. An example mean specification is:

`log E[Y(i,d,s)] = issuer/species effect + month×weekday effect + known calendar covariates + beta(s)×lagged_stress(d)`

Report absolute rate differences as well as rate ratios. Relevant calendar covariates include quarter-end and fiscal calendars, earnings dates, pre-announced product conferences, investor days, regulatory deadlines, major macro releases, holiday/early-close status, and documented launch windows. Their existence is not proven by writing their names into a regression plan.

The methods literature shows how time-stratified conditional Poisson models connect to case-crossover analysis and can accommodate overdispersion, autocorrelation, and differing denominators. Its evidence is methodological; it does not validate transplanting a model to a sparse, strategically selected corporate event panel. [M01, M02]

A full calendar-day fixed effect absorbs any stress variable shared by all issuers, so a common market-stress coefficient is not identified in that model. A stress-by-preexisting-linkage interaction may vary across issuers, but that does not solve confounding in linkage. With one or two new rate episodes, conventional large-sample standard errors and issuer-only clustering are particularly misleading. The present return should display counts and episode structure and decline population inference.

### Frozen pilot permutation: conditional diagnostic only

Use the parent's seed `20261007` and 10,000 replications. For each freely timed root event, eligible placebo dates are the predeclared trading dates within its original month and weekday. Move the root once, together with every attached issuer/source/species field. Preserve scheduled roots on their actual dates. Preserve program bundles in the declared coarsening sensitivity. Unknown scheduling belongs outside the strict freely timed subset.

The primary stress-alignment statistic can be the fraction of eligible captured positive roots landing in the frozen stress window. Its permutation reference asks how unusual that alignment is **conditional on the selected panel and its month/weekday constraints**. It does not estimate a population hazard ratio. Incomplete capture can favor unusually salient stress-linked releases even when the searcher never uses returns as a filter.

The three-session proximity statistic should count unordered pairs of distinct roots involving different issuers, with a five-session sensitivity. Report same-session pairs separately. Events on non-trading dates cannot be moved among trading dates while preserving their original weekday. Retain them descriptively and exclude them from this strict permutation, unless a separately documented amendment supplies a calendar-day null. Do not silently shift weekend releases to Monday.

When testing stress-arrival, **do not fix the observed total number of events on each day**: that would condition away the aggregate timing pattern under study. When testing a more demanding cross-firm-sequencing hypothesis, a distinct future null can preserve daily total intensity while shuffling issuer labels subject to issuer/month/species counts and documented exclusions. That second design asks a different question—who announces near whom, given common daily activity—not whether announcements aggregate after stress.

The calendar-control diagnostic also has a distinct null: move each selected first-quarterly-results date within month and weekday to examine how much ordinary earnings scheduling alone can produce apparent clustering. Moving those scheduled controls is appropriate for this particular diagnostic; it is different from keeping scheduled announcements fixed in the discretionary-arrival null. State the analysis mode in every output.

Month and weekday preservation removes only those specific regularities. It does not preserve fiscal earnings-week conventions, conference schedules, product readiness, merger negotiations, regulatory clocks, attention competition, or demand shifts. Calendar-aware is therefore a fair description; fully calendar-adjusted is not. Time-stratified referent selection is preferable to constructing opportunistic event-centered control windows after seeing where interesting cases land. [M01]

### Numerical reporting

For an upper-tail statistic use `(1 + number of simulated statistics >= observed) / (10000 + 1)`, with the tie rule stated. Do not print a zero p-value. At a tail probability near 0.05, 10,000 simulations have Monte Carlo standard error about 0.0022; this numerical uncertainty is much smaller than potential capture or exchangeability bias and does not account for those biases. The plus-one calculation is a valid conservative convention under the relevant randomization assumptions. [M03]

Display the observed statistic, simulated median and central range, number of movable events, number of fixed scheduled events, root/program counts, and candidate-set sizes. Mark a null as uninformative if too few events can move or the statistic is nearly constant. A conditional p-value is not a probability of coordination. Prospective inference should predefine a limited test family and multiplicity correction; this pilot should not select the smallest p-value across instruments, lags, species, or exclusions.

## 6. Required sensitivities and strongest failure modes

The parent menu—exclude NVDA; exclude NVDA+AMD+ORCL; leave each species out; exact-time subset; strict versus uncertain scheduling; program coarsening; alternate stress horizons—is appropriate. Every sensitivity should show the denominator and number of independent episodes left. A vanishing statistic after dropping a species may show that the claim was driven by an event mechanism; it is not automatically a reason to exclude that species from the main analysis.

| Failure mode | What would reveal it | Consequence |
|---|---|---|
| Capture depends on salience, stress, or company prominence | Coverage certification differs by date/issuer; archive census adds less memorable events | C1 not estimable from the search panel |
| Calendar explains apparent cooperation | Comparable clustering among ordinary earnings; conference/program coarsening removes result | Prefer calendar explanation; preserve residual uncertainty |
| A single stress episode creates many rows | One real or two nominal episodes despite thousands of issuer-days | Do not use row count as independent sample size |
| Recycled stories create a sequence | Same root economics, original source, or program appears repeatedly | Deduplicate; report source propagation separately |
| Announcement itself changes the stress measure | Same-day closing stress or later revised timestamp used | Enforce strict pre-announcement information cutoff |
| Sign or economic quality is assigned from returns | Classifications change when subsequent price chart is hidden | Recode blinded to returns; C4 otherwise circular |
| “Connected” firms selected after their contracts become famous | Government/linkage records first appear after stress or announcement | C2 comparison invalid until dated pre-exposure linkage exists |
| Controls lack common support | Mega-cap platforms compared with much smaller miners or consumer firms without balance | Describe strata; do not call them matched causal controls |
| Endogenous launch timing is misread as a central instruction | Shared commercial incentives or product readiness suffice to explain clustering | Central-intent inference remains unestablished unless evidence distinguishes it from these alternatives |
| Estimated self-excitation reflects omitted baseline shifts | Flexible calendar/time baseline removes Hawkes effect; timestamp repair changes it | Avoid Hawkes-based coordination scores in this pilot |
| Missing prices are silently replaced by vendor defaults | Adjusted-close definition, corporate actions, timezone, or benchmarks differ | C4 not measured; do not fabricate neutral returns |

Filimonov and Sornette's methodological work reports spurious Hawkes endogeneity from regime mixtures and sensitivity to timestamp quality. Its abstract was inspected, not its complete empirical analysis. The narrow implication here is to require baseline and timestamp challenges before using self-excitation as evidence; no numerical result from that market-microstructure paper is transferred to corporate announcements. [M04]

## 7. Source register and inspection limits

Access/retrieval date for this review: October 7, 2026 UTC. Exact historical publication dates are stated where material. Sources are primary documents, official data documentation, or original research papers.

| ID | Source and exact URL | What was inspected; limit |
|---|---|---|
| D01 | Treasury XML documentation — https://home.treasury.gov/treasury-daily-interest-rate-xml-feed | Endpoint syntax, yearly/monthly filters, XML format, availability dates. Four actual source files parsed separately. |
| D02 | Treasury 2025 nominal rates — https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2025 | Series methodology/units and table structure inspected. Actual calculation uses original XML `BC_2YEAR`, not a visually inferred table column. |
| D03 | Treasury 2025 real rates — https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_real_yield_curve&field_tdr_date_value=2025 | TIPS par-curve method and maturity descriptions inspected. Actual calculation uses original XML `TC_10YEAR`. |
| D04 | FRED Nasdaq metadata — https://fred.stlouisfed.org/series/NASDAQCOM | Daily close, Nasdaq source, copyright label. No Nasdaq historical raw dataset fetched. |
| D05 | FRED VIX metadata — https://fred.stlouisfed.org/series/VIXCLS | Daily close, Cboe source, copyright label. No VIX raw dataset fetched. |
| D06 | FRED legal terms — https://fred.stlouisfed.org/legal/ | Series licensing labels, prohibited uses, general/API AI-software-development clauses, inspected as current terms. No legal ruling inferred. |
| D07 | Cboe historical-data page — https://www.cboe.com/tradable_products/vix/vix_historical_data | Actual historical-file link inspected: https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv . File was not fetched. |
| D08 | Cboe terms and content permissions — https://www.cboe.com/terms ; https://www.cboe.com/use-of-content | General terms section 2 and content-approval conditions inspected. Do not infer product reuse permission from a public link. |
| D09 | Microsoft official stock lookup — https://www.microsoft.com/en-us/investor/stock-lookup ; official linked endpoint https://microsoft.gcs-web.com/ | Historical lookup controls and visible current-week table inspected, including split/dividend adjustment note. No 2025 full-period export, redistribution license, or point-in-time adjustment series established. |
| D10 | Apple official stock-price page — https://investor.apple.com/stock-price/default.aspx | Page and historical-lookup controls inspected. Search-index extract states third-party Tickertech supply; this lineage text was not present in the limited direct HTML extract. No full historical adjusted-price coverage established. |
| D11 | Federal Reserve Board disclaimer — https://www.federalreserve.gov/disclaimer.htm | Public-domain default for Board material, exceptions for non-Board content, attribution requested. This is not a blanket license for all FRED content. |
| C01 | ICE November 8, 2024 calendar release — https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx | 2025 ten regular holidays and July 3, November 28, December 24 early closes. |
| C02 | ICE December 30, 2024 extraordinary closure — https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx | January 9, 2025 NYSE equity/options closure explicitly inspected. |
| C03 | ICE November 10, 2023 calendar release — https://ir.theice.com/press/news-details/2023/NYSE-Group-Announces-2024-2025-and-2026-Holiday-and-Early-Closings-Calendar/default.aspx | 2024 Q4 holidays/early closes for warmup calendar. |
| M01 | Janes, Sheppard & Lumley, Statistics in Medicine, 2005 — https://onlinelibrary.wiley.com/doi/abs/10.1002/sim.1889 | Publisher abstract and reference list inspected; not full methods. Establishes referent-selection and overlap-bias concern, not a validated PB-C estimator. |
| M02 | Armstrong, Gasparrini & Tobias, 2014 — https://link.springer.com/article/10.1186/1471-2288-14-122 | Full HTML methods, equations, overdispersion/autocorrelation/offset discussion inspected; original authors' code is linked by the article. No implementation copied/executed. |
| M03 | Phipson & Smyth, 2010; author-posted manuscript — https://arxiv.org/pdf/1603.05766 | Full PDF extracted; sections 5–6 including plus-one and with-replacement conservativeness inspected. arXiv upload is 2016; journal article is 2010. |
| M04 | Filimonov & Sornette, author manuscript v3, 2014 — https://arxiv.org/abs/1308.6756 | Full abstract and version metadata inspected; no full-paper empirical reproduction. |

## 8. Disposition and next action

Completed: original Treasury source inspection, bounded data derivation, exact-instrument and calendar reconciliation, independent selected arithmetic/lag checks, and this implementable methods review. The integration owner can now consume the derived calendar in the selected-panel diagnostic and use the predeclared earliest stress window for a source-frame coverage audit.

Not completed by this helper: event panel acquisition, full issuer-day risk-set certification, Nasdaq/VIX measurement, issuer or benchmark returns, C1/C2 population/causal estimation, or production validation. No claim of validated coordination, return persistence, ranking value, or trade authority follows from this return.

The highest-value next scientific step is a complete source-frame denominator and prospective capture under the existing event/evaluation owners. A longer regression table or more flexible point-process fit cannot repair selective event acquisition or create independent stress episodes.
