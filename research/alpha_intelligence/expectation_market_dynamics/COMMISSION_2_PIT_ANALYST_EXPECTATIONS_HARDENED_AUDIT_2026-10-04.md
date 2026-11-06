# Commission 2 — Point-in-Time Analyst Expectations & Revisions Warehouse

## Hardened audit and recommendation

**Research date:** 2026-10-04  
**Status:** RESEARCH ONLY / PROCUREMENT-NEUTRAL  
**Disposition:** Proceed only to point-in-time (PIT) sample, rights, and empirical validation. No production deployment, vendor selection, portfolio authority, or procurement is authorized by this report.

### Source pins used for this hardening

- Protected Mastermind master: 84df29801d4078724c2b603a136de5aa1532cdfe
- Protected Sol Skillpack: mastermind.sol_skillpack.v1 / 1.0.1 / bootstrap 1
- Macro main observed for the current adjacent estate: f9ed175800257b228166dabe8b3ac9a55e74e237
- This report extends and hardens the existing Expectation Market Dynamics / K3E research. It does not supersede frozen K3E ownership, clock, or evaluation law.

---

# A. Executive conclusion

## Decision

**Proceed, but only to a procurement-neutral PIT bakeoff and schema/temporal validation. Do not yet authorize a production build or vendor contract.**

The target capability is worth pursuing. Analyst revisions are an established institutional information family, and the research literature supports revision innovation, analyst responsiveness, forecast timeliness, dispersion, and contributor heterogeneity as potentially useful information. That does **not** establish incremental alpha for Mastermind after its existing price, SUE/PEAD, fundamentals, news, options, theme, and event information.

The architecture should **not** be a new independent analyst warehouse or control plane. Macro already has the K3E Expectation Market Dynamics architecture, OWNER_AND_REUSE_MATRIX.md, DATA_CLOCK_RIGHTS_MATRIX.md, VEND_0_INSTITUTIONAL_ESTIMATES_BAKEOFF_2026-08-23.md, and frozen K3E-EVAL-0-V1. The accepted owner for prospective EPS/revenue expectation observations is already collectors/equity_revisions.py. K3E is explicitly a derived read model, not another truth store.

The eventual preferred source architecture is:

**commercial PIT consensus + analyst-level detail where rights and empirical value justify it + public issuer/SEC guidance receipts.**

That is the C+D strategy in the source-strategy decision tree below. Analyst detail should remain a separable entitlement: if it does not materially outperform cheaper PIT consensus after controls, Mastermind should not buy or retain it.

For vendor evaluation:

- LSEG I/B/E/S and S&P Capital IQ deserve the first analyst-detail/PIT probes.
- FactSet deserves the first consensus-PIT probe.
- Bloomberg deserves a PIT-consensus/guidance probe.
- Visible Alpha should be evaluated as a later KPI/segment-depth add-on rather than assumed to be the broad-history core.
- Zacks/Intrinio is a credible lower-cost challenger worth including in the bakeoff.

No winner is justified before actual record-level samples and contract-specific rights review.

## The most important hardening finding

The real problem is not simply "Mastermind lacks revisions."

Mastermind already has a **prospective, short-history revision plane** and downstream code consuming revision fields. What it lacks is:

1. mature historical institutional PIT expectations;
2. proven analyst-level contributor history;
3. rights-cleared institutional estimates;
4. enough temporal resolution to distinguish true value revisions from composition, staleness, fiscal roll, and methodology changes;
5. empirical proof that analyst detail adds information beyond Mastermind's existing evidence;
6. a production-proven Decision Snapshot / reliability-independence layer capable of consuming the family without double-counting it.

That distinction changes the implementation recommendation materially.

---

# B. Current-state census

## B1. Protected Mastermind

Protected master was pinned at:

84df29801d4078724c2b603a136de5aa1532cdfe

The protected INDEX, ACTIVE_EXECUTION, and SESSION_RELIABILITY procedures resolve under compatible mastermind.sol_skillpack.v1 / 1.0.1 / bootstrap 1.

### What actually exists

| Capability | Audit state | Evidence | Interpretation |
|---|---|---|---|
| Earnings-expectation risk lane | PARTIAL | portfolio/held_risk.py around lines 737-805 at the protected pin | Reads SUE/PEAD plus revisions.est_chg_30d, net_up_30d, and breadth. Consumption logic exists, but this is not a historical institutional estimates warehouse. |
| PIT SEC fundamentals research | BUILT_NOT_PROVEN / research | loop/fundamentals.py at the protected pin | Enforces as-of discipline such as asof_date <= t; useful leakage discipline to reuse. |
| Mature historical analyst-revision series | NOT FOUND | research/TREND_PERSISTENCE_PROTOCOL.md around lines 91-100 and 137-139 | Existing research defers revision persistence until canonical PIT history exists. |
| V3 Decision Snapshot | NOT_BUILT | Portfolio V3 specification | Important because this family should eventually enter a correction-safe decision snapshot rather than gain direct authority. |
| V3 claim ledger | NOT_BUILT | Portfolio V3 specification | Same implication. |
| Reliability/independence fusion | NOT_BUILT | Portfolio V3 specification | Analyst revisions must not be treated as independent of earnings/news/price by assumption. |
| V3 overall | SPEC_ONLY | Portfolio V3 specification | Do not represent the desired evidence-independence architecture as production-proven. |
| Static system census | STALE for present negative proof | data/census/CENSUS.md generated 2026-07-16 | Negative findings from this census alone are weak evidence in October. |

The V3 architecture already identifies the deeper conceptual problem: Mastermind's issue is not simply lack of signals. Incomplete consumption and correlated evidence can create false confidence. Its Decision Snapshot design also distinguishes observed_at from known_at and preserves correction generations. Commission 2 should conform to that architecture rather than inventing a parallel temporal model.

## B2. Macro estate — direct overlap already exists

Current Macro main was observed at:

f9ed175800257b228166dabe8b3ac9a55e74e237

This estate contains materially more relevant work than the old static Mastermind census exposes.

### Existing revision source

collectors/equity_revisions.py already owns a Yahoo/yfinance prospective revisions lane. The current program records or contracts for:

- EPS revision breadth;
- 30/90-day EPS consensus drift;
- reviser counts;
- covering-analyst counts;
- EPS dispersion;
- revenue consensus fields;
- explicit absence of revenue revision history where the provider does not supply it;
- prospective append-only expectation observations;
- attempt receipts;
- period-end anchors;
- correction lineage;
- an explicit rights_class rather than pretending rights are known.

The adjacent census records data/revisions/history.parquet as beginning only around 2026-06-16. It is therefore honest prospective PIT accrual, **not historical analyst-estimate history**.

The stronger SRC-A1 contract already separates:

- source_effective_at
- source_published_at
- provider_observed_at
- system_observed_at
- market_session

and explicitly forbids copying collector timestamps into unavailable source timestamps.

That is the correct architectural direction.

### Existing K3E program

There is already a directly overlapping program under:

research/alpha_intelligence/expectation_market_dynamics/

including:

- MASTERPLAN.md
- BUILD_SEQUENCE.md
- OWNER_AND_REUSE_MATRIX.md
- DATA_CLOCK_RIGHTS_MATRIX.md
- VEND_0_INSTITUTIONAL_ESTIMATES_BAKEOFF_2026-08-23.md
- EVALUATION_PREREG.md
- eval0_preregistration.v1.json
- CURRENT_CAPABILITY_LEDGER.md

The prior VEND-0 research reached a sound preliminary answer: LSEG, FactSet, S&P Capital IQ, and Visible Alpha are credible evaluation candidates, but no vendor has been sampled and rights remain unverified.

**Commission 2 should harden and extend K3E/VEND-0, not supersede it.**

### Frozen evaluation law

K3E-EVAL-0-V1 is already frozen. Its canonical digest is recorded in the existing program and its own amendment law requires a new version, new digest, explicit reason/diff, and new forward boundary for changes after outcome access.

This report therefore does **not** rewrite EVAL-0. The incremental-value study recommended below should be a new preregistration with its own forward boundary.

### Terminal adjacency

mastermind-terminal separately collects yfinance statements/estimates/analyst fields through ingest/collect_us_fund.py. That is an adjacent current-state surface, not evidence of institutional historical PIT estimates.

---

# C. State-of-the-art research

## C1. Literature supports the family, not automatic promotion

The literature supports four design lessons.

### Revision magnitude alone is too crude

Gleason and Lee study analyst forecast revisions and distinguish revisions that contain more innovative information from revisions that merely move toward consensus. The implication for Mastermind is that raw consensus delta should not be the only feature.

Source: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=370425

### Analyst timing matters

Research on analyst responsiveness after earnings links prompt analyst revisions with faster price discovery and less subsequent post-earnings drift. That supports explicit post-earnings reset and revision-latency features rather than treating every revision identically.

Source: https://www.sciencedirect.com/science/article/pii/S0165410108000220

### Analyst identity may matter, but creates a harder data requirement

The analyst literature finds persistent differences associated with experience, employer resources, portfolio complexity, boldness/herding, and timeliness. Analyst weighting is therefore a legitimate research challenger, but only after contributor identity, rights, and PIT historical accuracy are proven.

Representative sources:

- https://www.sciencedirect.com/science/article/pii/S0165410199000130
- https://www.sciencedirect.com/science/article/pii/S0304405X01000678

### Historical vendor databases themselves can change

Ljungqvist, Malloy, and Marston document material changes across historical I/B/E/S recommendation downloads. Payne and Thomas show that split adjustment and rounding in I/B/E/S per-share data can alter empirical classifications.

These findings strongly support immutable Mastermind receipts and correction generations instead of assuming today's historical vendor download equals what was knowable historically.

Sources:

- https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2009.01484.x
- https://scholars.uky.edu/en/publications/the-implications-of-using-stock-split-adjusted-ibes-data-in-empir/

Dispersion also should not be treated as a universal bullish/bearish scalar. Classic evidence links forecast dispersion with subsequent returns in some samples, but disagreement, optimism, coverage, and constraints complicate the mechanism.

Source: https://afajof.org/issue/volume-57-issue-5/

## C2. Institutional practice

MSCI's Analyst Sentiment methodology uses revision ratios and changes in analyst-predicted EPS, sales, cash flow, targets, and recommendations, with recency weighting. This supports testing breadth, magnitude, velocity, and recency as separate dimensions rather than collapsing them into one opaque score.

Source: https://www.msci.com/documents/10199/a925c038-cf5e-9701-fe7a-e4414a06b1ca

LSEG's SmartEstimate weights analyst accuracy and recency and exposes revision-cluster analytics. FactSet offers Sharp Consensus-style revision clustering. S&P applies contributor-basis and stale-estimate rules. These are useful **benchmarks/challengers**, not canonical Mastermind truth.

Source: https://www.lseg.com/en/data-analytics/financial-data/analytics/quantitative-analytics/starmine-smartestimates

---

# D. Source landscape

| Source | Coverage / history | Latency | PIT quality | Corrections / methodology | Rights | Cost class | Best use |
|---|---|---|---|---|---|---|---|
| LSEG I/B/E/S | Deep global analyst history; LSEG markets analyst detail, consensus, guidance, measures/KPIs, and historical products. | Product/delivery specific. | Promising; sample required. | Actuals/guidance expose multiple temporal concepts, but exact analyst-detail correction lineage must be proven on delivered records. | Contract-specific; internal storage, redistribution, and AI rights remain UNKNOWN until product terms are reviewed. | Enterprise quote | Deep-history analyst-detail candidate. |
| FactSet Estimates + PIT Consensus | General estimates history is deeper than PIT consensus; PIT consensus history begins in Dec-2009 in FactSet's published methodology. | PIT consensus uses local-market-midnight daily snapshots. | Very strong documented consensus PIT. | Particularly useful because FactSet documents differences between standard historical reconstruction and PIT states caused by later QA corrections, deletions, currency/class changes, and dilution treatment. | Contract-specific; broker entitlements and AI/model rights must be verified. | Enterprise quote | Best consensus-PIT benchmark. |
| S&P Capital IQ Estimates + Snapshot | Broad estimates history; Snapshot captures PIT updates since Aug-2016 according to S&P's product materials. | Snapshot cadence is described as every two hours. | Very strong candidate; public materials expose effective/to-date concepts. | Contributor inclusion/exclusion, majority-basis, and stale-estimate policies make consensus-move decomposition mandatory. | Contributor entitlements and contract-specific AI/data rights matter. | Enterprise quote | Strong combined PIT + detail candidate. |
| Visible Alpha | Highly granular model, segment, and KPI line items. Public S&P pages are not perfectly consistent on historical-start descriptions. | Intraday/broker-timestamp claims. | PIT claimed; exact history and correction lineage require sample proof. | Excellent model granularity; correction semantics need delivered evidence. | Separately entitled and contract-specific. | Enterprise/high | P2 KPI/segment-depth add-on after broad core proves value. |
| Bloomberg Company Financials/Estimates PIT | Bloomberg markets historical PIT company financials/estimates and enterprise delivery. | Daily PIT snapshots for the PIT product family. | Strong documented consensus/guidance candidate. | Corporate-action-adjusted PIT is attractive; analyst-detail lineage still requires product-specific evidence. | Agreement-specific. | Enterprise quote | Consensus/guidance/PIT challenger. |
| Zacks / Intrinio | Long historical estimates offerings and API/bulk delivery. | Package-specific. | Unproven against Commission 2's immutable PIT standard. | Needs the same correction/backfill bakeoff as enterprise incumbents. | Licensed; display/storage terms require review. | Mid/enterprise challenger | Lower-cost benchmark. |
| SEC EDGAR + issuer IR | US issuer filings, XBRL, 8-Ks, earnings releases, and guidance artifacts. | Public filing/API chronology. | Excellent for issuer publication/acceptance chronology; not sell-side consensus. | Filing amendments/corrections need explicit lineage. | Public/government, subject to normal source terms. | Free/public | Management guidance, actuals, event anchors. Never substitute for analyst consensus. |
| Current Yahoo/yfinance Mastermind source | Current EPS/revenue snapshots plus prospective accrual since 2026. | Collection-time resolution. | Honest prospective PIT from Mastermind observation time; no historical backfill. | Source publication clocks are often absent and rights are not sufficiently established for institutional historical use. | Unverified for target use. | Low/free | Prospective research baseline and continuity source. |
| FMP / similar retail APIs | Current and historical-looking estimate fields. | API. | Insufficient evidence of immutable historical PIT/correction semantics for this commission. | Unknown until sampled. | Plan-specific. | Low | Screening/current-state challenger only until PIT semantics are proven. |

Primary vendor references:

- LSEG I/B/E/S: https://www.lseg.com/en/data-analytics/financial-data/company-data/ibes-estimates
- LSEG I/B/E/S Broker Estimates: https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/broker-estimates
- FactSet Estimates API: https://developer.factset.com/api-catalog/factset-estimates-api
- FactSet PIT methodology: https://insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf
- S&P Capital IQ Estimates: https://www.spglobal.com/market-intelligence/en/solutions/capital-iq-estimates
- S&P Estimates / Visible Alpha: https://www.spglobal.com/market-intelligence/en/solutions/products/estimates
- Bloomberg enterprise catalog: https://professional.bloomberg.com/products/data/enterprise-catalog/cofi/
- Zacks historical data: https://www.zackspro.com/historical.asp
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

## Vendor conclusion

There is **no basis yet for selecting a winner**.

The initial bakeoff should include LSEG, S&P Capital IQ, FactSet, Bloomberg, and one lower-cost Zacks/Intrinio challenger. Visible Alpha should be a separate KPI-depth evaluation because its economic question is different.

---

# E. Canonical data model

The current K3E owner law should remain intact. Do **not** create a second generic estimates database.

The minimum useful model is an extension of the existing revisions owner with provider-native raw observations plus derived read models.

## E1. expectation_observation

Grain:

provider × issuer/security × contributor × metric × immutable fiscal period × observation

Minimum fields:

- observation_id
- provider_record_id
- provider
- issuer_ref
- security_ref
- provider_company_id
- metric_native
- metric_canonical
- fiscal_period_end
- periodicity
- fiscal_year
- horizon_label_raw
- contributor_id
- broker_id
- analyst_id
- value
- currency
- unit
- scale
- basis
- normalization_class
- source_published_at
- vendor_received_at
- vendor_activated_at
- provider_snapshot_at
- mastermind_observed_at
- known_at
- ingested_at
- effective_from
- effective_to
- correction_generation
- supersedes_observation_id
- withdrawal_state
- rights_class
- source_receipt

Unavailable clocks stay NULL/UNKNOWN. They are never synthesized from a later clock.

## E2. consensus_snapshot

Do not force Mastermind to reconstruct every vendor consensus.

Store the vendor's PIT consensus **and** separately calculate a transparent Mastermind consensus when analyst detail permits.

Useful statistics include:

- mean
- median
- high
- low
- standard deviation
- eligible contributor count
- raw contributor count
- stale/excluded count where supplied
- consensus window/class
- basis
- currency
- snapshot time
- correction/methodology lineage

Vendor consensus and Mastermind consensus are separate evidence objects.

## E3. collection_attempt / source receipt

This already exists conceptually in SRC-A1 and should survive vendor adoption.

It must distinguish:

- success
- partial
- null
- rights_blocked
- entitlement_blocked
- rate_limited
- malformed
- transport_error

A failed fetch is never "no revision."

## E4. contributor identity history

Only if licensed:

provider_contributor_id × analyst × broker × valid_from × valid_to

Analyst moves between brokers must not create false analyst identities. Team forecasts and anonymized IDs remain explicit rather than guessed.

## E5. Reuse, do not duplicate

Company guidance, SEC filings, actuals, corporate actions, issuer/security identity, and market-response data remain with their existing canonical owners. The expectation system stores references/receipts, not competing copies of truth.

---

# F. Derived intelligence

Everything below should be deterministic before an LLM sees it.

| Feature | Hardened definition |
|---|---|
| Revision magnitude | Same metric, same immutable period, same basis. Prefer scale-safe change; avoid percentage EPS change around zero/negative EPS. |
| Revision velocity | Change per trading/calendar time from eligible observations, with observation density printed. |
| Acceleration | Change in velocity using fixed windows; require stable denominator and period identity. |
| Value-revision breadth | (distinct continuing analysts up - distinct continuing analysts down) / eligible continuing analysts. |
| Entry/exit breadth | Analyst coverage additions/removals reported separately. |
| Staleness effect | Consensus change caused solely by aging/expiry of estimates. |
| Dispersion | Preserve vendor-native SD/IQR/range separately. Never substitute high-low range for standard deviation. |
| Clustered revisions | Count distinct contributors and time span; distinguish same-information herding from independent innovation where testable. |
| Estimate-age weighting | Deterministic, transparent recency kernel; benchmark against unweighted consensus. |
| Analyst-skill weighting | Research challenger only after contributor identity and PIT historical accuracy are rights-cleared. |
| Post-earnings reset | Separate pre-event estimates, first post-event revisions, and later stabilization. |
| Persistence | Same-period directional revision persistence, not fiscal-roll persistence. |
| Consensus momentum | Change in comparable consensus after decomposing constituent/composition effects. |
| Nowcast gap | Mastermind deterministic/ML nowcast minus same-basis PIT consensus, with independent evidence accounting. |
| Consensus-move decomposition | value revisions + additions/removals + stale expiry + withdrawals + methodology/class/currency change + period roll. |

This decomposition is essential. Vendor consensus can move even when no continuing analyst changes a value. A raw consensus delta therefore cannot safely be labeled "analyst revision."

---

# G. Mastermind integration map

| Producer | Canonical owner/artifact | Evidence family | Consumer |
|---|---|---|---|
| Yahoo prospective estimates | existing collectors/equity_revisions.py / data/revisions/* | expectations/revisions | K3E research surface; current held-risk context |
| Future licensed estimates vendor | same revisions owner, provider-native observations | expectations/revisions | K3E EXP-1 -> later Decision Snapshot |
| SEC/issuer guidance | Earnings/Event/FIF owners | management expectations | K3E comparison/reference |
| SEC/financial actuals | existing financial/earnings owners | realized fundamentals | surprise/reset calculations |
| Price/residual owners | existing market/DRL owners | market response | K3E MKT-1 |
| Options owners | existing options plane | implied uncertainty | K3E MKT-1/context |
| Identity owner | existing issuer/security identity | mapping | every join |
| K3E derived read model | EXP-1/CPL-1/PHASE-1 when accepted | descriptive expectation dynamics | V3 Decision Snapshot / research consumers |
| V3 Decision Snapshot | Portfolio V3 owner | immutable decision information set | future PM/portfolio experiments only after separate acceptance |

No new lifecycle, identity, risk, publication, evaluation, or portfolio-control plane is needed.

---

# H. Empirical validation program

## H1. Do not rewrite EVAL-0

K3E-EVAL-0-V1 is already frozen and explicitly immutable.

Commission 2 should add a **new preregistered incremental-value study with a new forward boundary** rather than editing the old registration after outcomes have begun accruing.

## H2. Core experiment

Use rolling-origin/walk-forward evaluation only.

| Model | Information |
|---|---|
| A | price momentum/reversal, volatility, liquidity, size, beta, sector |
| B | A + PIT fundamentals + SUE/PEAD + earnings-event state |
| C | B + existing news/options/theme/macro evidence where PIT-safe |
| D | C + PIT consensus revisions |
| E | D + analyst-level decomposition |
| F | E + KPI/segment/guidance features where available |

The economically decisive tests are **D versus C** and **E versus D**.

If analyst detail cannot beat consensus-only after costs and complexity, do not buy the analyst-detail entitlement.

## H3. Horizons

Use mechanism-aligned horizons:

- immediate/event reaction;
- 1-5 trading days;
- about 20/21 days;
- about 60/63 days;
- next earnings event;
- longer only with an explicit mechanism.

Separate ordinary revisions from pre-earnings, post-earnings, and guidance-event regimes.

## H4. Metrics

Primary research diagnostics should include:

- cross-sectional IC / rank IC;
- incremental predictive loss or R-squared where appropriate;
- quantile monotonicity;
- coverage and missingness;
- calibration;
- turnover;
- net-of-cost economics;
- sector/beta/style exposures;
- stability across eras;
- issuer/revision-episode clustered uncertainty;
- block/date sensitivity;
- multiple-hypothesis control.

## H5. Negative controls

The study should deliberately attempt to catch itself cheating:

- future-data sentinel fields;
- current reconstructed history versus true PIT snapshots;
- conservative timestamp delays;
- shuffled contributor identity within appropriate groups;
- stale-removal-only consensus changes;
- coverage-entry/exit-only changes;
- fiscal-period-roll "revisions";
- deliberately delayed availability timestamps;
- vendor correction cases;
- corporate-action cases;
- pre/post event timestamp boundary cases.

A signal that disappears when known_at is delayed to realistic Mastermind availability should be treated as non-actionable.

## H6. Independence

The revision family must prove incremental information beyond:

- price momentum;
- PEAD/SUE;
- earnings-event proximity;
- news sentiment;
- options;
- fundamental growth/value/quality;
- sector/theme momentum.

This is especially important because analysts react to public information and recent price performance. Analyst revisions may otherwise be a slower repackaging of evidence Mastermind already owns.

---

# I. Risks and failure modes

## Temporal leakage

The biggest risk is not a bad model. It is a dataset that appears historical but has been retrospectively corrected.

FactSet's own PIT methodology is a useful warning: standard history and PIT history can differ because of currency changes, QA corrections, deleted observations, consensus-class changes, and dilution treatment.

Source: https://insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf

## Basis mismatch

EPS, revenue, EBITDA, and even "revenue" can be on incompatible bases. S&P documents contributor-basis and inclusion/exclusion methodology. Basis must be preserved rather than silently normalized.

Source: https://www.spglobal.com/market-intelligence/en/solutions/capital-iq-estimates

## Fiscal-roll leakage

FY1 today and FY1 six months ago can refer to different immutable periods. Relative horizon labels cannot be the primary historical key.

## Contributor composition masquerading as revision

Consensus can move with zero continuing-analyst value revisions because analysts enter, leave, expire, withdraw, or are excluded.

## Vendor methodology drift

Vendor methodology itself can change. Methodology version therefore belongs in lineage where obtainable.

## Corporate actions

Per-share history is particularly dangerous. Split adjustment and rounding can change empirical classifications.

Source: https://scholars.uky.edu/en/publications/the-implications-of-using-stock-split-adjusted-ibes-data-in-empir/

## Vendor-history mutability

Historical vendor databases can change between downloads. Immutable Mastermind receipts/generations are mandatory.

Source: https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2009.01484.x

## Rights

The fact that a vendor supports APIs or LLM integrations does **not** automatically grant storage, redistribution, model-training, or prompt-exposure rights.

Rights must be resolved from the product-specific agreement and entitlement schedule. Public product pages are not enough.

Representative sources:

- https://www.spglobal.com/en/terms-of-use
- https://developers.lseg.com/en/api-catalog/eikon/eikon-data-api/documentation

---

# J. Build priority

| Priority | Recommendation |
|---|---|
| P0 | Preserve existing K3E/revisions ownership. Do not create a new warehouse/control plane. |
| P0 | Run record-level vendor PIT/rights bakeoff before procurement. |
| P0 | Freeze canonical temporal invariants and vendor-neutral receipt contract. |
| P0 | Extend data-quality observability: ingestion lag, late arrivals, corrections, missingness, coverage churn, mapping failures. |
| P1 | Evaluate broad PIT consensus from LSEG/S&P/FactSet/Bloomberg plus a lower-cost challenger. |
| P1 | Evaluate analyst detail as a separately priced and separately tested entitlement. |
| P1 | Preregister incremental OOS testing against Mastermind's existing evidence. |
| P2 | Visible Alpha or equivalent KPI/segment-depth add-on after broad core proves value. |
| P2 | Analyst-skill/accuracy weighting after contributor identity and rights pass. |
| DEFER | Frontier-LLM explanation of consensus moves until deterministic decomposition is proven. |
| REJECT | Backfilling Yahoo/current snapshots into historical dates. |
| REJECT | Calling every consensus change an analyst revision. |
| REJECT | One opaque "expectations score." |
| REJECT | Treating SmartEstimate/Sharp/vendor proprietary analytics as canonical Mastermind truth. |
| REJECT | Long vendor contract before PIT sample bakeoff. |
| REJECT | Production/portfolio authority based only on retrospective alpha. |

---

# K. Proposed phases

## Phase 0 — source-law reconciliation

Treat existing K3E/VEND-0/EVAL-0/SRC-A1 as the baseline. Re-census current code immediately before any implementation wave.

## Phase 1 — procurement-neutral bakeoff

Obtain time-limited or vendor-supplied rights-permitted samples.

Use the existing VEND-0 sample design as the base and harden it to include approximately 30 issuers across regions, non-calendar fiscal years, ADR/share-class cases, mergers/spinoffs, inactive companies, and difficult metric/basis cases.

Test the same fixed issuer/metric/period/as-of requests across vendors.

## Phase 2 — PIT conformance harness

For each vendor prove:

- immutable as-of reconstruction;
- source/provider/Mastermind clocks;
- corrections;
- withdrawals;
- fiscal period identity;
- corporate actions;
- missing versus zero;
- analyst/broker persistence;
- entitlement failures;
- reproducibility on a later extraction date.

## Phase 3 — consensus-only research

Load only rights-cleared sample/research history through the existing owner and evaluate PIT consensus revisions.

No product authority.

## Phase 4 — analyst-detail incremental test

Only if Phase 3 establishes useful information, test whether analyst-level detail improves on consensus-only.

This is the main economic gate for paying for detail.

## Phase 5 — KPI/segment depth

Evaluate Visible Alpha or comparable granular models only where company-specific drivers plausibly add value beyond standard financial metrics.

## Phase 6 — prospective shadow

Only surviving features enter an isolated forward shadow evidence family.

## Phase 7 — separate promotion decision

Portfolio/Prophet/ranking/sizing authority requires a new explicit decision and forward evidence. Research success does not grant it automatically.

---

# Temporal invariants

The implementation owner should treat these as acceptance tests.

**T1 — Knowledge cutoff:** replay at time T may consume only records with known_at <= T.

**T2 — No retroactive correction:** a correction learned at T+1 cannot change what replay at T sees.

**T3 — No timestamp invention:** absent source publication or vendor activation clocks remain absent.

**T4 — Fiscal identity:** a rolling FY1 change with a different period end is not a revision.

**T5 — Composition decomposition:** removal/addition/staleness alone cannot increment value-revision breadth.

**T6 — Rights:** rights-blocked analyst detail cannot silently degrade into inferred identities.

**T7 — Intraday honesty:** daily/local-midnight data cannot support an earlier intraday signal.

**T8 — Receipt separation:** vendor availability and Mastermind ingestion are different clocks.

**T9 — Corporate action lineage:** splits/ADR changes cannot silently rewrite historical per-share observations.

**T10 — Reproducibility:** every derived feature is reproducible from cutoff-eligible immutable observations.

---

# Source-strategy decision matrix

| Strategy | Information | PIT confidence potential | Complexity | Cost/lock-in | Verdict |
|---|---:|---:|---:|---:|---|
| A. PIT consensus only | Medium | High | Low | Medium | Good P1 baseline |
| B. Analyst detail only | High | Variable | High | High | Reject as sole architecture |
| C. PIT consensus + analyst detail | Very high | High if sampled | High | High | Preferred institutional core if detail proves incremental value |
| D. Commercial core + SEC/issuer guidance | Very high | High | Medium-high | Medium-high | Required complement |
| E. Visible Alpha/KPI add-on | Extremely deep, narrower universe/history | Medium/high if proven | High | High | P2, not core |

**Recommended target: C + D, staged so A + D can survive permanently if analyst detail fails its incremental-value test.**

---

# Procurement bakeoff

Before any long contract, ask every candidate for:

1. exact table/product history by metric and geography;
2. sample schemas/data dictionaries;
3. analyst and broker identifier semantics/history;
4. fiscal-period mapping;
5. source publication, receipt, activation, effective, and snapshot timestamp definitions;
6. timezone/DST conventions;
7. corrections, deletions, withdrawals, and restatements;
8. consensus constituent/staleness methodology;
9. corporate-action and currency treatment;
10. API/feed/cloud delivery and SLAs;
11. historical snapshot reproducibility;
12. internal raw-data retention rights;
13. derived-feature retention rights;
14. internal display rights;
15. external display/redistribution restrictions;
16. analyst/broker attribution rights;
17. LLM prompt/retrieval rights;
18. model-training/fine-tuning rights;
19. post-termination raw and derived-data retention;
20. an evaluation sample covering the frozen issuer/event panel.

A refusal or inability to explain PIT correction semantics is itself a material result.

---

# Red-team findings

The preferred C+D architecture can still fail.

## 1. Revisions may be redundant

The strongest attack is that analyst revisions may mostly be a slower repackaging of information Mastermind already sees earlier through prices, earnings, filings, news, and options. If realistic availability delays erase incremental performance, the warehouse is expensive redundancy rather than edge.

## 2. Consensus may capture nearly all useful information

Analyst detail could dramatically increase data volume, licensing complexity, identity work, and legal restrictions while adding little incremental OOS value. This is why E versus D is a required economic gate.

## 3. "PIT" can still hide product-specific transformations

A vendor history can look point-in-time while still applying transformations or correction rules that differ from what an actual historical subscriber could have observed. Record-level replay is mandatory.

## 4. Coverage selection can manufacture apparent alpha

The richest analyst detail exists where institutional coverage is highest. Apparent performance may therefore be a large-cap/liquidity/quality exposure.

## 5. Signal decay is a real prior

Revision effects are old and institutionally known. Current institutional factor products operationalize them. Mastermind should assume competition has arbitraged away easy constructions and require contemporary holdout plus prospective evidence.

---

# What we still do not know

| Unknown | Evidence required |
|---|---|
| Best vendor | Identical rights-permitted bakeoff samples |
| Exact LSEG analyst-detail PIT semantics | Delivered schema + repeated historical replay |
| FactSet analyst-detail correction behavior versus PIT consensus | Detail entitlement sample |
| S&P correction/withdrawal behavior at analyst level | Snapshot/detail sample across known corrections |
| Exact Visible Alpha historical start across products | Contract/data dictionary; public product descriptions must not be treated as enough |
| Bloomberg analyst-level export/PIT availability for this use | Enterprise sample/data dictionary |
| Analyst identity persistence across broker moves | Vendor identity-history sample |
| LLM/model-training rights | Executed product-specific agreement |
| Whether analyst detail adds Mastermind alpha | New preregistered incremental OOS experiment |
| Whether consensus itself adds Mastermind alpha | Same |
| Whether KPI depth pays for itself | Separate KPI/segment ablation |
| True total cost | Comparable sales quotes for the frozen entitlement requirements |

---

# Claim-confidence ledger

| Claim | Status | Confidence |
|---|---|---:|
| Mastermind has an earnings-expectation consumer lane | OBSERVED CODE | High |
| Existing Mastermind lacks mature historical institutional revision history | OBSERVED across current code/research | High |
| Macro already owns prospective expectation observations | OBSERVED CODE/DECISION | High |
| Existing Yahoo history can support pre-2026 backtests | FALSE / prohibited | High |
| K3E/VEND-0/EVAL-0 already overlap Commission 2 | OBSERVED | High |
| FactSet PIT consensus preserves historical states against later QA/currency/deletion changes | PRIMARY VENDOR CLAIM | High |
| S&P Snapshot provides frequent PIT snapshots with effective intervals | PRIMARY VENDOR CLAIM | High |
| LSEG offers deep analyst history and PIT products | PRIMARY VENDOR CLAIM | High |
| Visible Alpha exact history/PIT semantics for the contemplated entitlement | SAMPLE REQUIRED | Unknown |
| Bloomberg offers enterprise PIT consensus/guidance history | PRIMARY VENDOR CLAIM | High |
| Any vendor permits Mastermind's desired AI/storage uses | UNKNOWN pending contract | Low |
| Analyst detail has incremental Mastermind alpha | UNKNOWN | Low until tested |

---

# L. Exact follow-on handoff

## Recommended next commission: institutional estimates PIT bakeoff & rights validation

**Mission:** Determine whether one or more commercial analyst-estimates sources can lawfully and reproducibly supply the historical point-in-time expectation information required by Mastermind's existing K3E/revisions architecture, and whether analyst-level detail is sufficiently better than consensus-only data to justify further engineering/procurement.

**Scope:** Research/evaluation only. No production deployment, no portfolio authority, no vendor selection, no long-term contract, no raw licensed data committed to Git, no modification of K3E ownership, and no rewriting of frozen K3E-EVAL-0-V1.

**Candidates:** LSEG I/B/E/S; FactSet Estimates/PIT Consensus; S&P Capital IQ Estimates/Snapshot; Bloomberg Company Financials/Estimates PIT; one Zacks/Intrinio lower-cost challenger; Visible Alpha as a separately scored KPI-depth add-on.

**Required work:** Freeze one common issuer/metric/event panel; obtain rights-permitted samples and data dictionaries; replay identical historical cutoffs; test publication/activation/snapshot/system clocks; test corrections, deletions, withdrawals, fiscal rolls, corporate actions, stale-estimate rules, and contributor composition; document storage/derived/display/LLM/training/post-termination rights; measure coverage and operational limits; map each candidate into the existing revisions-owner temporal contract without building an adapter.

**Acceptance evidence:** For every candidate, deliver a field-presence matrix, temporal-semantics matrix, correction replay, identifier/fiscal-period audit, rights matrix, coverage report, reproducibility receipt, cost class, lock-in assessment, and PASS/PARTIAL/FAIL decision. Every unsupported property remains UNKNOWN.

**Decision gate:** Advance a candidate only if historical PIT state is reproducible without hindsight, corrections preserve as-known history, missingness is distinguishable from zero, required rights are contractually available, coverage meets the target universe, and the source can support the subsequent preregistered incremental-value experiment.

**Stop condition:** Return a procurement recommendation only after the bakeoff. If no source passes, return NO_BUILD / RIGHTS_BLOCKED / PIT_UNPROVEN and preserve the existing prospective Yahoo accrual rather than fabricating history.

**Explicitly not authorized:** signing contracts, paying vendors, deploying adapters, changing production ingestion, modifying trading behavior, granting Prophet/portfolio/ranking/sizing authority, or exposing licensed data to LLMs beyond explicitly granted evaluation rights.

---

# Final recommendation

The hardened sequence is:

1. **prove PIT semantics and rights;**
2. **prove consensus incremental value;**
3. **prove analyst-detail incremental value;**
4. **only then decide what to buy and build.**

This is deliberately stricter than a normal vendor-selection exercise. It protects Mastermind from spending heavily on a sophisticated dataset whose information is either temporally contaminated, legally unusable, or already captured by existing evidence families.
