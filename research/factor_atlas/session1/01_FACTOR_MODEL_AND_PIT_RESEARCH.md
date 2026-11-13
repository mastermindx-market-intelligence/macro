# Factor Atlas — Factor Models, Cohorts and Historical Measurement

**Session 1 research and specialist implementation masterplan · 8 October 2026 (America/New_York)**  
**Proposed repository destination:** `macro/research/factor_atlas/01_FACTOR_MODEL_AND_PIT_RESEARCH.md`  
**Disposition:** research/contract proposal with an executable gated handoff; **not an accepted production contract or a completed native pilot**. This conversation package is **NOT_CANONICALLY_PERSISTED** in GitHub or Agent OS.

## 1. Executive decision

Build Factor Atlas as a **read-through catalog and measurement projection over incumbent owners**, not another factor, theme, security or portfolio authority. A catalog entry may be visible even when it has no admissible historical series. The interface must answer three different questions separately: **what does this mean; which cohort is being measured; which observations and methodology produced this line?**

The first eligible native slice is three existing US house baskets, tentatively `mag7`, `ai_infra` and `defense`, with monthly target weights, declared drift, source-qualified returns, breadth, concentration and coverage. These are candidate identifiers, **not a claim that their price inputs are rights-cleared**. Produce current-roster and strict-PIT requests side by side; a PIT result may legitimately be unavailable. An honest null is successful gate behavior, but it is not evidence that the requested PIT measurement capability has been completed.

The highest-value prerequisite is not a new ranking screen. It is correcting or explicitly versioning the calculation contract: current basket code describes monthly rebalancing but averages available constituent returns each day. The style portfolio engine also uses unchanged target weights across daily returns while describing buy-and-hold. Both affect the meaning of historical performance. Preserve their existing outputs and owners until an owner-approved migration exists. [M01], [M04]

**Native implementation is held.** Required procedure/custody reads received a platform safety-status refusal; affected-PR exact-head reconciliation remains incomplete. Purpose-specific price rights, action vintage and complete historical collection coverage were not established. The pinned Terminal gateway has no accepted Factor Atlas feed. No branch, PR, source modification, GMI state update, worker dispatch or deployment was performed. Independent mathematical conformance work in this package is deliberately separate from those missing proofs.

## 2. Evidence standard and pinned source

| Surface | Exact pinned commit | Meaning |
|---|---|---|
| Mastermind protected `master` | `732cf7be88e7159b4995a8885fbd381cd1484e3e` | INDEX/COLD_START and bounded ACTIVE_EXECUTION/SESSION_RELIABILITY reads; compatible bootstrap major 1. Required follow-on read completeness not established after refusal. |
| Macro `main` | `cdbcd143dcfa419ab0637bc11dd4c80368143e2e` | Source census baseline, commit timestamp 2026-10-09 02:19:39 UTC. Not a deployment assertion. |
| Terminal protected `master` | `bacda5dcc30682f9327e037a2d4425bd9714ac3a` | Consumer source baseline, timestamp 2026-10-09 02:04:13 UTC. Not a served-build assertion. |

The source register at the end supplies immutable file links; `evidence/source_register.json` supplies known blob identities and inspection bounds. Counts below distinguish direct current-document measurements from comments and historical reports. A repository file does not prove that a collector ran, an entitlement exists, a PR merged or production serves those bytes. Full-repository Macro recursive-tree output was truncated; non-results there are not absence proofs. Selected config, lib and tests subtree inventories were not truncated.

The source-custody assessment is intentionally **not complete**. Earlier open-PR searches identified overlapping baskets/sector/theme work. The later exact-head reconciliation batch was refused before usable results. Do not promote an earlier issue search, archived handoff, branch name or old head to present custody clearance.

## 3. Capability and implementation census

### 3.1 Required engines and related owners

| Exact incumbent path | Observed behavior at the pin | Reuse / missing proof |
|---|---|---|
| `engine/baskets.py` | Reads curated membership and broad/extras closes; `_ew_level` averages active available returns daily, then fills missing aggregate returns with zero after inception. `_ret` can advance a missing anchor to the first available observation. Comments say monthly rebalanced buy-and-hold. | Reuse membership references and owner price selection. Do not describe current algorithm as monthly drift. No whole-history corporate-action or missingness qualification established. |
| `engine/group_flow.py` | Display-only group fingerprint combining relative performance, breadth change, pair correlation and persistence. Shares basket helpers. Defaults include 20-session RS, 50-session breadth MA, 40-session correlation, 252-session z baseline, minimum history 150 and minimum members 8. | Reuse diagnostic concepts; do not call it measured fund flows. Its rolling-z convention is not identical to the style-series z convention. No new allocation signal. |
| `engine/subsector_rotation.py` | Consumes Finviz aggregate performance snapshots; relative values use a cross-sectional median; acceleration uses horizon return divided by approximate weeks. Insufficient/missing z values can become zero. | Aggregate vendor observations are not reconstructed house indexes. Preserve source, denominator, approximate pace and missingness. Do not convert zero fallback into a qualified neutral factor. |
| `engine/factor_series.py` | Month-end `compute_factors(asof=...)`; Q5 cap-weight long-only and Q5−Q1 equal-weight long-short. Long-only multiplies each day by unchanged target weights; long-short averages available names. Current factor list includes value, profitability, quality, investment, payout, low volatility, low beta and composite. | PIT fundamentals are useful but not a complete PIT universe/identity/weights proof. Constant-target daily weights are not buy-and-hold. Missing long-only contributions and missing long-short names are treated differently. |
| `engine/equity_factors.py` | Winsorized company cross-sections using EDGAR and prices. As-of path filters filings/prices; current short interest is deliberately omitted in PIT mode. Live shares reconciliation uses current reference shares. Existing ranking/firewall logic is distinct from display. | Reuse style definitions, released-as-of fundamentals and the incumbent identity bridge. Audit universe/classification histories and split/share basis before constructing qualified style portfolios. Do not modify rank eligibility or composite weighting. |
| `engine/factor_seasonality.py` | `factor_seasonality.v2`, academic monthly French series, full/30-year/10-year descriptive samples, explicit house-vs-academic distinction. | Reuse owner series; carry download vintage and availability cutoff. Full-sample seasonal patterns are descriptive, not evidence of forward forecasting skill. |
| `engine/price_ladder.py` | Adjusted-first selected source ladder; optional same-read byte/hash capture. Evidence leaves adjustment-as-of, session, venue and observation clock unknown where unproved. Legacy cache may be mixed-vintage, not simply raw. | Excellent starting evidence adapter, not a rights certificate. A hash binds bytes; it cannot fill unknown price semantics. |
| `engine/basket_membership_pit.py` | Existing append-only history and dated sidecars for US/CN suites; per-suite writer lanes; explicit current fallback; newer collection receipts and interval reader. | **The membership owner.** Strict Atlas PIT must reject `pit=False`, incomplete observation evidence and unknown intraday decision clocks. Never create another constituent store. |
| `lib/dataos/identity.py` | Existing listing/security/issuer identity, vendor aliases with effective intervals and `known_at`; alias resolution can use decision cutoff. | **The identity owner.** Resolve aliases through it; a ticker is not a stable global identity. Split, successor and multi-listing policies must come from owner evidence. |
| `lib/dataos/price.py` | `raw`, `sadj`, `tradj` basis vocabulary; session and venue identity; documented naming and migration rules. | Import existing enums and source policies. Do not mint incompatible basis strings or treat a display price as a total-return series. |
| `lib/closes_panel.py` | Existing shared whole-column price-source arbitration is referenced by baskets; selected source metadata was inventoried. | Preserve owner arbitration; never row-splice stores to cosmetically fill gaps. Full source behavior and tests were not independently executed here. |

The inspection was targeted, not an adversarial review of every line of each large module. The table identifies actual implementation behaviors and explicit unverified boundaries rather than claiming whole-module acceptance. [M01], [M02], [M03], [M04], [M05], [M06], [M07], [M08], [M09], [M10], [M11]

### 3.2 Current basket census and the two historical interpretations

The pinned `data/baskets/membership.json` contains **49 baskets, 1,038 member slots and 708 distinct ticker strings**. Slots are basket memberships, not distinct securities; ticker-string uniqueness is not a security-master identity census. `mag7` has 7 entries, `ai_infra` 24 and `ai_software` 17. The document version/curation stamp is 2026-08-07 and its seed date is 2023-05-09. [M12] (direct selected-field count)

Its own declarations are unusually useful: `added` is a back-projected index-inclusion mask, while `curated_added` records actual curation provenance. Its history note says **35 of the 49 baskets are back-projected** and expressly disclaims a prior investment track record. That 35 is the document's declaration, not an independently recomputed count. Neither the `added` mask nor the label “PIT” in an older engine comment overrides this disclosure.

The committed US cadence file reports `checked_at=2026-10-07T08:00:09Z`, `last_snapshot_date=2026-09-04` and membership SHA-256 `b968e9812f60494bd02bbc0d5ad4b8dc67dcb90a939426728e9db6befba9678a`. A content-deduplicating writer can legitimately have an older last-change date than its latest check. This stamp alone does not establish first coverage, every basket's collection completeness, current live cadence or genuine released-as-of history. The attempted parquet coverage inspection did not complete; those measurements remain unknown. [M13]

The existing reader uses stored observations when available but falls back to today's document with `pit=False` before coverage. Its newer path additionally returns `collection_state`, `collection_receipt`, `last_qualified_collection` and observation scope. A collection receipt validates exact basket/source/generation/membership hashes and `observed_at <= known_at`; its known date must match snapshot date. The date-only public reader still requires additional cutoff qualification before a same-day close can be used for a decision earlier that day. A prior collection of basket A is not deletion evidence for uncollected basket B. [M08]

### 3.3 Semantic graph and prior programme reconciliation

`config/theme_crosswalk.yml` remains the incumbent join into GMI/TIL. Its header declares 18 canonical themes, 13 primary basket mappings and 5 nulls. Crucially, only `primary_basket_id` denotes direct theme/basket identity; `basket_ids` also contains proxies and economic/supply-chain relationships. Reversing every forward basket reference would misclassify companies. Atlas must keep `direct`, `proxy`, `economic_exposure` and `unavailable` distinct. [M14]

The current-pinned Theme Fabric research/gap matrix is a research artifact, not a production graph snapshot. It describes 68 microthemes, macro categories and candidate parent/proxy relationships with important gaps. Do not restate its historical counts or draft mappings as current measured microtheme coverage. A semantic microtheme with no qualified cohort has no native measured series, even when a parent basket has returns. [M15], [M16]

The Fable Factor Intelligence masterplan owns a different use: per-company exposure/conditioning/de-escalation within the existing Neural Web path. Atlas's descriptive read model must not become a second selection engine, alter Fable's frozen research contracts, or write `research/factor_intelligence/`. GMI owns the graph, membership lifecycle and ThemeState; Atlas does not write `engine/theme_graph/`. [M17]

Open-work search surfaced Macro #7888 (cybersecurity membership), #7284/#7278/#7769 (Sector Intelligence), #8643 (PIT category shadow), #8665 (source receipts), and other GMI dependencies. These are **collision candidates, not independently reconciled current heads**. Avoid cybersecurity in the first pilot until that lane is qualified. An Oct-8 owner handoff records Terminal #847 Finviz discovery, an existing child/reviewer and a release hold. It explicitly rejects replacing Finviz with 49 house groups and says source/review/production gates remain. Its recorded test totals are historical owner claims, not tests run by this session. Preserve that carrier rather than dispatching another adapter. [M18]

### 3.4 Terminal and comparison consumers

At the Terminal pin, `terminal/app/api/sector-intelligence/route.ts` admits only:

| Feed | Incumbent upstream |
|---|---|
| sector | `/sectordata/sector_central.json` |
| confluence | `/marketdata/subsector_confluence.json` |
| themes | `/neuralwebdata/theme_state.json` |
| heatmap | `/marketdata/sp500_heatmap.json` |
| risk | `/riskdata/risk_envelope.json` |

The route is an authenticated, private/no-store, fixed-origin transport. It filters shared Supabase cookies, refuses arbitrary URLs/redirects, limits payload size to 4 MiB, qualifies exact envelopes and distinguishes source date from fetch receipt time. **There is no Factor Atlas feed in this map.** Adding one requires owner acceptance; it cannot be smuggled in as a ThemeState look-alike. [T01]

`terminal/lib/sectorIntelligence.ts` has typed receipts, null-preserving number parsing, explicit source cohorts, timeframe state, source-order tie handling and a top-five market-cap concentration view that refuses missing caps. Its `sourceDate` reduces an accepted source date to a day; it is not a sufficient intraday availability contract. Atlas must preserve exact timestamps in its own measurement envelope through an accepted additive interface, not overwrite that helper globally. [T02]

`tests/test_factordata_source.py` proves an existing Terminal test contract: a usable local owner directory is authoritative, and a missing per-symbol local file must not trigger a network substitution. This is a useful compatibility invariant, not proof that Factor Atlas already integrates with Sector Intelligence or the chart comparison stack. Exact chart-component binding and authenticated browser proof remain open acceptance gates. [T03]

### 3.5 Existing tests: what they do and do not prove

Located tests include `test_baskets.py`, `test_factor_series.py`, `test_equity_factors.py`, `test_factor_seasonality.py`, `test_group_flow.py`, `test_price_ladder.py`, `test_closes_panel_freshness.py`, `test_basket_membership_pit.py`, `test_us_basket_membership_pit.py`, `test_basket_membership_stamps.py`, `test_membership_snapshot_freshness.py`, and `test_dataos_security_master.py`. Their presence is not a passing test receipt.

The inspected style-series test explicitly **expects equal-weight fallback when a 5% cap is infeasible**. Therefore an Atlas contract must not “fix” this shared owner silently; expose the fallback as a different method or refuse the advertised capped request. Its “strict JSON” smoke calls ordinary `json.dumps(out)` without `allow_nan=False`; that assertion does not reject IEEE NaN. It also has a fixture expression using Python's `hash(f)`, so hash-seed independence should be tested rather than presumed. The PIT membership tests are fixture-only and cover writer lanes, sidecars and dedup stamps; they do not certify the current live store. [M19], [M20]

## 4. Complete factor-class model

### 4.1 One catalog, three separate identities

A read-through descriptor has `semantic_ref`, optional `cohort_ref`, and zero or more `series_specs`. A **descriptor key is a namespaced reference to an existing owner ID**, not a new global factor registry. A series fingerprint is a derived computation identity, not a security or membership identity.

`semantic_ref` answers meaning and provenance. `cohort_ref` answers who/what is measured and how membership is selected. `series_spec` answers return basis, portfolio construction, currency, calendar, sessions, correction view, costs and availability. Different series specs for the same semantic theme are not interchangeable. For example, AI capex as an economic theme, today's AI infrastructure basket and the basket's actual PIT history can share a navigation relationship while remaining different measured objects.

| Class | Customer definition and semantic owner | Cohort / observable series / limits |
|---|---|---|
| Economic theme | A causal economic proposition or exposure, using the incumbent GMI/TIL node. | May have no constituents. Link separate direct baskets and proxy instruments; never average “economics” into a made-up price. Economic indicators carry their native units, not equity returns. |
| Tradable thematic house basket | An explicitly curated investable-or-descriptive group under the existing basket ID and thesis. | Membership document or PIT owner observation; declared weighting, listing/currency, actions and costs. “Tradable” requires execution/liquidity/borrow evidence beyond a gross index. |
| GMI microtheme with qualified constituents | Existing microtheme node with an owner-admitted membership relationship. | Measure only its admitted exact cohort and effective interval; retain cross-membership. Do not infer all parent constituents or use semantic parent count as a measured denominator. |
| GMI microtheme without constituents | Existing semantic node, useful for navigation/research. | `SEMANTIC_ONLY`; optional visibly named parent/proxy comparison, not a microtheme return. No zero line, guessed breadth or inferred company roster. |
| GICS sector/industry | Licensed classification, provider/version/effective history. GICS has sector/industry-group/industry/sub-industry levels. [P06] | Declare universe (e.g. a specific index population versus all eligible US equities). A sector ETF is a proxy, not the entire classification. Do not substitute Finviz taxonomy for GICS. |
| Quantitative momentum | A published screening rule, e.g. a named 12–1 price/total-return momentum definition. | Rank eligible PIT universe using lagged data, explicit breakpoints, ties and liquidity rules. Keep long-only high-momentum cohort and high-minus-low spread separate. |
| Quantitative value | Cheapness relative to declared fundamental denominator. | Reuse company metric owner; select earnings/book/sales/CFO yields separately or a versioned composite. Negative earnings need their own missing/eligibility policy, not zero P/E. |
| Quantitative quality / profitability | A named accounting-quality/profitability construction. | Quality and profitability need not be one factor. Carry filings/restatements, denominator validity, winsorization and universe. House z scores are not academic RMW. |
| Quantitative volatility / beta | A low/high realized-volatility or beta screen. | Specify estimator, return basis, lagged window, trading days and leverage. Inverse-vol weighting is not the same object as a low-volatility selected cohort or covariance risk parity. |
| Quantitative growth | A rule based on realized revenue/earnings expansion, investment or admitted estimates. | Not synonymous with high valuation, QQQ or minus-HML. Forecast growth requires estimate vintages and rights; otherwise use a separately named realized-growth style. |
| ETF benchmark / proxy | Actual fund/share class and benchmark reference via security owner. | Market-price total return and NAV total return are distinct. Actual fund returns already include operating effects reflected in price/NAV; avoid subtracting stated fees a second time. Underlying-index comparison needs its own series/rights. |
| Dynamic short-interest cohort | A screen on reported outstanding short positions, denominator and release availability. | Publication, not settlement date, starts eligibility. Short sale volume is not short interest. FINRA describes their different meanings; its API documents publication availability. [P04], [P05] |
| Dynamic earnings cohort | Companies with a defined reported surprise, event or scheduled-report criterion. | Use actual release instant and contemporaneous consensus when applicable. Same-day after-hours events cannot enter that day's pre-close cohort. Current calendar or revised surprise history is not a PIT screen. |
| Long-short relative-value spread | Explicit two legs or signed portfolio, plus hedge/capital/financing convention. | A percentage-point return difference, price ratio and financed long-short NAV are three different observables. Negative weights do not define a financing model by themselves. |
| Leveraged/inverse product | Actual security with a prospectus-defined objective, reset frequency and costs. | Prefer observed instrument return. Synthetic daily-reset comparator is explicitly synthetic; never multiply a multi-month underlying return by leverage. [P07] |
| User portfolio/custom snapshot | User-owned immutable selection or the incumbent portfolio owner's accepted snapshot. | Reference that owner's ID/ACL. Current snapshot backprojection is hypothetical; actual deposits/withdrawals require time-weighted versus money-weighted performance distinction. No new user portfolio writer in Atlas. |
| Academic factors | Published research series with original construction, universe and vintage. | French HML/RMW/CMA/SMB/MOM/Rm−Rf stay in a distinct family. Their long-short/excess-return construction is not interchangeable with a house company cohort. [P02], [P03] |

### 4.2 Owner-reference rules

Preserve every source-local ID verbatim behind an owner-qualified reference. Reject ambiguous ticker-only joins rather than creating a new mapping. A catalog may index references for search; any materialization must be disposable and reconstructible from those references. It must not become the source of truth for constituents, taxonomy, permission, retries, lifecycle or ThemeState.

A displayed proxy needs `relationship=proxy`, a named measured instrument/cohort and a reason. A semantic-only descriptor can have descriptions, parent/related links and missing reasons, but no fabricated performance cells. Do not let an ML model infer membership, weighting or economic causality into the qualified data plane.

## 5. Return mathematics and time conventions

The equations below are the **proposed house measurement contract**, not claims that every incumbent engine implements them. Internally use simple returns as fractions; UI percent multiplies by 100. Price units are quote currency per share, index levels arbitrary positive units, volume shares/contracts with scope, weights fractions of declared capital. Persist calculation precision; round only presentation.

### 5.1 Single-security returns and corporate actions

For a split-adjusted price series of a single compatible vintage, price return is

\[r^{P}_{i,t}=P^{sadj}_{i,t}/P^{sadj}_{i,t-1}-1.\]

For a source-qualified total-return series,

\[r^{TR}_{i,t}=P^{tradj}_{i,t}/P^{tradj}_{i,t-1}-1.\]

**Do not add dividends again** to a total-return-adjusted series. For raw-price reconstruction, value all surviving claims from one beginning share, including split conversion, successor shares, cash and distributed shares:

\[r^{TR}_{i,t}=\frac{\text{end value of all claims from one beginning share}+\text{cash distributions}}{P^{raw}_{i,t-1}}-1.\]

Corporate-action mappings, quantities, event clocks and correction versions must be owner-supplied. They cannot be guessed from a suspicious price jump. Splits adjust share count and price inversely; a pure split creates no economic return. Cash mergers convert to proceeds on the declared effective convention. Stock mergers transfer into successor claims under the historical mapping, not today's ticker. Spin-offs require both parent and distributed-child value, including the chosen when-issued/first-regular-mark treatment. Delisting is neither automatic zero return nor automatic −100%: use verified terminal proceeds/return, or make the unresolved valuation explicit. A missing security must not quietly disappear and improve the basket.

Choose and label dividend reinvestment: `constituent_total_return` reinvests in each constituent's total-return unit; `index_level_reinvestment` reinvests distributions across the index. These can diverge. S&P DJI's methodology explicitly describes index-level dividend reinvestment and distinguishes price, total and net total return. This proposal does not claim its hypothetical house baskets reproduce an official S&P index. [P01]

Gross versus net dividends require tax jurisdiction/rate/version. No tax rate is inferred from user residence. Unsupported net-return requests return unavailable. Fractional-share allowance, cash-in-lieu, corporate-action costs and withholding are explicit construction parameters.

### 5.2 Equal, cap, float, volatility and fixed weights

At rebalance reference instant \(\tau\), use only eligible information available to the decision. For eligible set \(C_\tau\):

\[w_i^{EW}=1/|C_\tau|,\quad w_i^{cap}=M_i/\sum_j M_j,\quad w_i^{float}=M_i f_i/\sum_j M_j f_j.\]

\(M_i\) uses contemporaneous raw price times compatible outstanding shares, including FX where needed; do not multiply a total-return-adjusted historical price by today's shares. \(f_i\) is a qualified float fraction. Absence of historical shares/float is not permission to backfill today's value.

An inverse-volatility target is

\[w_i^{ivol}=\sigma_{i,\tau^-}^{-1}/\sum_j\sigma_{j,\tau^-}^{-1}.\]

This is not equal-risk-contribution portfolio optimization. Specify estimator, lookback, lag, min history, cap and zero-volatility handling. A zero or missing estimate is ineligible, not infinite weight. Explicit fixed weights must be nonnegative for the long-only class and sum to one within the numeric tolerance; signed portfolios use a different contract. Do not normalize erroneous client inputs silently.

Capped weights solve an explicitly documented redistribution rule. Feasibility requires \(n c\ge1\) for an all-invested long-only single-name cap \(c\). If infeasible, return `INFEASIBLE_WEIGHT_CONSTRAINT`, or choose an explicitly requested alternative series spec. Do not advertise “5% cap” while returning 20% equal weights.

### 5.3 Rebalance, drift and index level

Let \(w_{i,t-1}\) be beginning-of-period weights, after any effective rebalance. For a fully priced long-only, constituent-TR-unit portfolio with no costs or external flows:

\[r_{B,t}=\sum_i w_{i,t-1}r_{i,t};\qquad I_t=I_{t-1}(1+r_{B,t}).\]

Between rebalances:

\[w_{i,t}=\frac{w_{i,t-1}(1+r_{i,t})}{1+r_{B,t}}.\]

At rebalance, reset target weights without creating a return jump; record turnover and costs separately. Monthly means the last eligible exchange session under a versioned calendar—not every 20 rows and not the last observed row of a truncated month. Record reference instant, decision cutoff, execution/effective instant and next effective holdings. A close-known selection cannot claim a fill at an already-passed closing auction. The pilot uses predeclared basket membership/targets eligible before its reference/effective boundary; close-derived signals need a lagged execution convention.

Base level is 100 immediately **before the first admitted return**. Rebasing a comparison to time \(a\) gives \(I'_t=100I_t/I_a\) with \(I_a>0\); it changes neither returns nor history qualification. Preserve null gaps. A return chain cannot reconnect across an unresolved missing return; a later separate segment needs a disclosed new base, not a hidden flat bridge.

**Counterexample:** three equal positions start at 100. One goes 100→200→100; two stay flat. Buy-and-hold ends at its initial value, a 0% return. Daily re-equal-weighting gives \((1+1/3)(1-1/6)-1=1/9\), or **11.111111%**. The package's synthetic oracle verifies this difference. It is not an estimate of the error in any live basket history.

### 5.4 Missing observations and coverage

A qualified portfolio return needs all economically held weight to be valued, or an explicit owner-approved valuation for the missing holding. Missingness is not zero. Do not renormalize the remaining 80% and claim a return on the full basket.

For known beginning weights, available-weight coverage is

\[q_t=\sum_i w_{i,t-1}\mathbf1(\text{valid end-to-end return for }i).\]

For signed portfolios use absolute gross weights in the denominator. If target weights themselves cannot be established, available-weight coverage is null, not guessed from available market caps. Count coverage is separately \(n_{valid}/n_{eligible}\). A listing that did not yet exist is structural ineligibility, a halted name is a held but potentially unvalued claim, and a corrupt row is a data error; keep those reasons distinct.

A separately named `covered_subset_descriptive` aggregate may renormalize valid weights above a declared threshold, but it must not appear as the complete basket's investable history. The first pilot excludes this convenience to avoid conflating claims. Raw endpoint ratios across a multi-session gap may be valid **interval** returns, but cannot be assigned to one daily bar or used to fill daily volatility.

### 5.5 Aggregate versus investable definitions

An equal-weight daily average of current company returns is a valid cross-sectional aggregate when precisely named. It is not necessarily a monthly-rebalanced, implementable portfolio. A vendor's average month-to-date change across its present members is also not necessarily a daily-linked month-to-date index return. Store `measurement_kind=aggregate_snapshot`, `portfolio_index`, `instrument_return`, `academic_spread` or `economic_observation` and make incompatible comparisons opt-in and explicit.

Investability additionally needs contemporaneous listing universe, liquidity, execution, fractional shares, turnover, capacity, short availability and costs. A reproducible gross index is not a trading recommendation or realized portfolio performance. Atlas emits no position size or entry permission.

### 5.6 Long-short, hedging and financing

A simple return comparison is \(\Delta_{A,B}=R_A-R_B\), in percentage points after display conversion. Geometric relative performance is \((1+R_A)/(1+R_B)-1\). A price-level ratio is scale/basis-dependent. None is automatically a funded strategy.

For a declared capitalized portfolio, signed beginning exposures \(w_i\), net cash/collateral accounts \(c_k\), and NAV \(V\):

\[r^{NAV}_t=\sum_i w_{i,t-1}r^{TR}_{i,t}+\sum_k c_{k,t-1}r^{cash}_{k,t}-b_t-f_t-TC_t.\]

Here \(b\) is borrow cost on short notional, \(f\) contains financing adjustments not already represented in cash accounts, and \(TC\) is trading cost divided by beginning NAV. Balance assets, short liabilities, segregated short proceeds and financing explicitly; do not earn unrestricted cash interest on locked collateral or charge the same borrowing twice. Long-short dividends are already in signed total-return P&L; do not deduct them twice.

Gross leverage is \(\sum|w_i|\), net exposure \(\sum w_i\). “100/100” means 200% gross, zero net, not zero capital and not a 100% gross strategy. Hedge ratio \(h\) may be fixed or estimated on a prior window; declare rebalance, estimation lag and whether weights are re-scaled to gross notional or NAV. `r_A-h r_B` without these terms is an unfunded diagnostic spread. If NAV reaches zero or a synthetic day implies return below −100%, terminate/flag insolvency rather than drawing an ordinary rebased wealth line.

Cost model: turnover \(TO=\tfrac12\sum_i|w_i^{target}-w_i^{drift}|\) is one-way portfolio turnover for balanced long-only rebalancing. Execution costs charged per traded dollar use the **full** absolute traded notional, not half by accident. Store commissions, spread, impact, borrow availability and financing scenario separately. Unknown borrow cannot be zero by default; unfunded gross spreads remain a permitted descriptive alternative.

### 5.7 Frequency, currency and non-synchronous sessions

US pilot: daily regular-session completed bars, one declared venue/session convention and USD. Intraday is a later capability, not inferred from daily prices. Session close and official auction are distinct observations. An after-hours mark compares against the last regular close in a separately labeled extended-session view; it does not rewrite that day's finalized RTH return or intraday historical denominator.

Cross-market comparisons carry local trading date **and UTC interval endpoints**, calendar/version, quote/base currencies and FX fix. Use common information cutoffs and intersection of comparable completed intervals for correlations/betas. Never forward-fill a foreign holiday into a zero observation for covariance. Weekly common-window analyses can reduce, not eliminate, non-synchronous trading effects; disclose rather than manufacture synchronization.

FX conversion for unhedged returns is \((1+r_{local})(1+r_{FX})-1\), where the FX quote is base currency per unit local currency. Currency-hedged series require a separate forward/roll/cost contract. Mixed quote directions are invalid inputs.

### 5.8 Beta and residual return

Market beta uses aligned excess returns over a declared estimation window:

\[\beta_m=\mathrm{Cov}(r_B-r_f,r_m-r_f)/\mathrm{Var}(r_m-r_f).\]

For joint market and sector exposures use an intercept and full-rank regression of basket excess return on market and sector excess returns. A sector ETF overlaps the market; independent univariate betas cannot simply be subtracted twice. Use a declared joint model or a pre-specified residualized sector regressor; reject singular/poorly conditioned designs.

Fitted residual \(\epsilon_t=y_t-\hat\alpha-\hat\beta'x_t\) is a descriptive decomposition of that fitting window. An out-of-sample residual uses coefficients fitted strictly before \(t\). Neither is automatically a tradable “alpha factor.” Persist coefficients, estimator/window, sample size, regressor series refs, residual units and lag. Proposed beta policy uses a 252-session default window, at least 126 common observations and at least 80% coverage of the requested window; for a full 252-session request the coverage floor therefore requires at least 202 common observations. These are descriptive admission choices, not calibrated accuracy guarantees. Future factor-neutral return construction is a distinct long-short/cost problem and outside the pilot.

## 6. Point-in-time, availability and correction science

### 6.1 The necessary clocks

| Clock / identity | Meaning and required behavior |
|---|---|
| `effective_from`, `effective_to` | Real-world validity of membership/classification/alias/holding interval, half-open `[from,to)`. |
| `source_published_at` | First documented public/vendor availability for the fact; null when not evidenced. A filing period end or short-interest settlement date is not this clock. |
| `observed_at` | Collection observation of source content; use owner's meaning, not fetch time of a downstream page. |
| `known_at` | Earliest recorded system knowledge/admission of that exact revision. Never backdate a newly received correction. |
| `selection_cutoff` | Information available to each membership/weight decision. Must precede applicable execution/effective holding instant. |
| `measurement_cutoff` | Information and revisions available to a requested historical measurement. Outcome prices after selection are lawful outcomes, not selection inputs. |
| `materialized_at` | Computation completion/serialization timestamp; cannot substitute for source observation or decision availability. |
| `membership_revision_ref` | Existing owner's membership/generation/collection identity, including complete/partial/retired status. |
| `calculation_version` / `revision_ref` | Algorithm and input lineage. Method changes are not silently data corrections. |

These clocks are not assumed identical. For a selected fact, require relevant effective validity and `source_published_at <= selection_cutoff` when public availability matters, plus `known_at <= selection_cutoff` for an as-known system replay. For measurement outcomes, use the measurement cutoff, not the earlier selection cutoff. That distinction prevents both look-ahead selection and the opposite mistake of rejecting all realized returns that happened after a portfolio was formed.

### 6.2 Explicit historical modes

**CURRENT_ROSTER:** freeze the incumbent roster at a disclosed snapshot/revision, measure that selected set backward over its own listing history. Mark hindsight/survivorship limitation, pre-curation region and listing coverage. Selection before those dates is not claimed. Default strict all-member comparability begins only when the complete requested roster can be measured; show partial listing coverage without silently changing the portfolio universe.

**PIT_AS_KNOWN:** at each decision, resolve the actual eligible membership and aliases from the incumbent owner with effective and knowledge/availability gates. A date-only historical snapshot without intraday qualification can support a carefully delayed daily convention, but not any arbitrary instant. No fallback to current. A basket observed as empty is different from an unobserved basket; a collection's partial absence is not removal evidence.

**PIT_LATEST_CORRECTED:** reconstruct historical effective cohorts using currently admitted corrections while preserving historical decision eligibility. Distinguish corrections to historical facts from information that would not have been knowable then. Report it as revised historical measurement, not what the system originally knew. A correction cannot retroactively create a trading decision that did not exist.

The UI's two primary tabs remain **Today's roster backtest** and **Point-in-time history**; the PIT revision selector shows as-known versus revised. Current and PIT comparisons must share calendar, start/end, return basis and construction to isolate roster effects. When PIT starts later, offer both full current-roster history and a matched-overlap comparison; never imply that their unequal windows measure the same opportunity.

### 6.3 Correction lineage and deterministic recomputation

Do not overwrite existing owner ledgers. Reference the original input manifest and the owner's correction record; materialize a new calculation revision. Record `supersedes`, reason, affected intervals, source/corporate-action/identity/membership revisions and an original-versus-corrected numeric delta. Old and new calculations must remain separately addressable through existing evidence/publication facilities. An owner with keep-FIRST history needs its own accepted correction extension; Atlas must not create a shadow mutable history to compensate.

A deterministic semantic input fingerprint includes source byte hashes, price/identity/membership revisions, code commit, dependency lock/version, calendar/timezone, method, clocks, parameters and rights-purpose references. Canonical JSON is finite, sorted and explicitly encoded. A generation timestamp is outside the deterministic result core; recomputing the same inputs should preserve result hash even if the computation ran later. Changing source bytes or membership revision must change the input identity, even if the final number happens to be equal.

Pure multiplicative backward adjustments can leave same-vintage interval returns unchanged while changing historical levels. Do not claim every new corporate action necessarily changes every past return. The dangerous cases are mixed vintages, corrected events, incompatible share counts, source stitching and unknown lineage. Preserve one consistent source generation per computed interval, or use raw-plus-actions through the existing price owner.

## 7. Descriptive analytics catalog and minimum evidence

These are **proposed conservative admission defaults**, not empirically optimized thresholds or guarantees of statistical accuracy. Version them in `contracts/metrics_policy.v0.json`. A policy change is visible. All metric envelopes carry value/unit, requested and actual window, status/reason, sample count, count/weight coverage, basis and source refs.

### 7.1 Horizon returns and term structures

| Metric | Definition | Minimum and unavailable behavior |
|---|---|---|
| Intraday | Mark/previous RTH close−1, or interval mark/start−1, explicitly distinguished. | Qualified intraday endpoints, timestamp/venue/age and all held weight. Daily-only pilot returns `UNSUPPORTED_FREQUENCY`. |
| 1D | Completed session close/previous completed-session close−1. | Two adjacent eligible endpoints; no fill across missing sessions. |
| 1W/1M/3M/6M/1Y | Geometric return between calendar-anchored endpoints using declared preceding-session rule. | Both exact resolved anchors and all intervening portfolio returns. Store actual dates. Do not equate 1M with 20 sessions. |
| MTD/YTD | End/prior month-end or prior year-end−1. | Correct prior-close anchor; insufficient inception is null, with separate inception return. |
| Custom window | Explicit boundary/anchor convention and geometric chain. | Never slide requested start forward because data is missing. |
| 5/10/20/60-session | Product of exactly h adjacent session gross returns−1. | Exactly h valid returns is sufficient; h+1 prices. Missing rows do not compress the window. |
| Relative strength | Geometric relative return and percentage-point difference as distinct cells. | Same endpoints, basis, currencies and comparable calendars. |
| Momentum pace / acceleration | Log-return-per-session over disjoint short and prior windows; acceleration is difference in pace. | Positive levels and full windows. Display units `log_return_per_session`, not a probability. |

A useful term structure is the vector of 5/10/20/60-session geometric relative returns plus disjoint recent-versus-prior pace. Do not interpret overlapping 1W and 1M changes as independent observations. House momentum ranking remains a separate owner-controlled use.

### 7.2 Distribution, volatility, downside and tails

For h-session rolling return distributions use exact calendar windows; show sample period, valid-origin count, overlapping status and excluded origins. Report mean, median, standard deviation, 10/25/75/90th percentiles, positive/zero/negative counts and extrema. Use a predeclared quantile interpolation convention. A histogram with 252 overlapping 60-session returns is not 252 independent observations.

Realized volatility: sample standard deviation (`ddof=1`) of daily simple returns times \(\sqrt A\), with \(A\) the declared annualization convention (252 for this US daily policy). Default published stable estimate requires 60 valid adjacent daily returns; 20-session volatility can appear as explicitly short-window descriptive data, never silently substitute for 60. Compare like estimators.

Downside deviation relative to target \(m=0\): \(\sqrt{A\,n^{-1}\sum\min(r_t-m,0)^2}\). Denominator is all valid returns, not just negative days. Zero downside is a possible sample outcome, not evidence of no risk. A downside standard deviation using only negative observations is a separately named metric.

Drawdown \(DD_t=I_t/\max_{s\le t}I_s-1\); maximum drawdown is the minimum. Record peak, trough, recovery timestamp, sessions and calendar days. Unrecovered episodes are right-censored, not zero-duration. A missing segment breaks the continuous drawdown claim; compute disclosed covered-segment diagnostics or null.

Empirical tail loss at level \(p\): \(VaR_p=-Q_p(r)\); expected shortfall is average loss in the specified lower tail with deterministic boundary-weight handling. Descriptive 5% tails require at least 252 daily observations and at least 12 lower-tail observations; 1% tails require 1,260 observations under this policy. Negative VaR is permitted under that signed definition or separately shown as signed return quantile—never silently clipped. These thresholds do not make tail forecasts reliable; no forward probability claim is admitted.

### 7.3 Abnormality and volume

Return z-score: current observation minus mean of a **prior-only** baseline, divided by its sample standard deviation. Default 252 valid prior observations, minimum 60; constant baseline gives `ZERO_BASELINE_VARIANCE`, not z=0. Historical percentile uses a deterministic midrank convention and exposes ties. Current-inclusive variants must have a different method label. Winsorized ranking z scores are not time-series surprise z scores.

For volume, define share versus dollar volume, exchange/off-exchange scope, split compatibility and same-time-of-day baseline. Dollar volume is aggregated as compatible price×volume, not a sum of unlike share counts interpreted as liquidity. Intraday relative volume compares cumulative volume at the same elapsed session point, excluding the present day; default 20 prior comparable sessions, half-days separated. Daily pilot volume requires qualified source scope; price-only evidence does not manufacture volume coverage. Abnormal dollar volume can be a descriptive activity measure, not proof of inflows.

### 7.4 Breadth, concentration and overlap

Daily advance breadth = number of eligible constituents with positive same-interval return / number with valid same-interval return. Publish unchanged and declining counts and the missing denominator separately. MA breadth = fraction of eligible names whose compatible current price is above a specified 20/50/200-session MA, with each member's full required history. For the pilot, define breadth as advance breadth; later MA breadth has separate history gates.

Minimum for multi-name breadth: 3 eligible securities, at least 80% count coverage and 80% known-weight coverage; otherwise metric null. These thresholds permit a **disclosed partial breadth statistic**, not a qualified partial portfolio return. Flag small-N cohorts below 10; an ETF instrument has N=1 and does not manufacture constituent breadth without a holdings owner.

Portfolio concentration uses beginning/drifted weights: \(HHI=\sum_iw_i^2\), effective number \(N_{eff}=1/HHI\), and top-1/top-5/top-10 weights. Require the complete weight vector. Give both security-level and issuer-aggregated concentration where the issuer mapping is complete. Missing issuer links invalidate issuer concentration, not security concentration. Market-cap concentration and return-contribution concentration are different measures and should have different keys.

Membership overlap: Jaccard \(|A\cap B|/|A\cup B|\) on qualified security IDs at the same clock. Weighted overlap for long-only unit-weight portfolios: \(\sum_i\min(w_i^A,w_i^B)\). Empty/unknown cohorts are not zero overlap; two known empty cohorts need an explicitly defined convention, and Atlas defaults to unavailable. Signed overlap uses separately reported long-long, short-short and opposing exposures; do not reuse the long-only formula blindly. Overlap creates dependence between factor comparisons and must remain visible.

### 7.5 Correlations, pairs and attribution

Pearson correlation uses the same aligned return intervals; rank correlation is a separate named estimator with average-rank tie handling. Default minimum 60 common intervals, at least 80% of the requested reference-calendar intervals, nonzero variance. Return the pair's common start/end/count. For a matrix, one common complete-case sample is the default; pairwise deletion requires per-cell sample metadata and cannot promise a positive-semidefinite covariance matrix.

Pair displays show both common-window lines rebased to 100, individual and geometric relative returns, percentage-point difference, overlap, rolling beta/correlation and source/basis differences. A “spread” must explicitly say whether it is a return difference, normalized ratio or capitalized strategy. No valuation convergence claim follows from correlation.

Single-period attribution is \(c_{i,t}=w_{i,t-1}r_{i,t}\); cash, action residual and costs must reconcile to total return. Multi-period exact linked contribution under one explicit convention is

\[C_i=\sum_t c_{i,t}\prod_{u=t+1}^{T}(1+r_{B,u}),\]

with identical linking for cost/cash terms. This sums to compounded return when daily contributions reconcile; simply summing daily contributions does not. Preserve identity changes at the security/issuer owner boundary. Provide entrants/exits and rebalance changes separately from price contributions. An unexplained attribution residual above tolerance fails the result.

### 7.6 Seasonality and event studies

Monthly heatmap cells are geometric calendar-month returns; distinguish unfinished month, uncovered month and zero return. Summary by calendar month shows count, arithmetic mean, median, hit rate, quantiles and coverage. Three complete comparable years allow an exploratory cell; ten observations per month allow a more stable descriptive label, not predictive qualification. Full history, trailing 10 years and trailing 30 years use explicit end cutoffs.

Weekday seasonality uses local session weekday and completed sessions; minimum 30 observations for each displayed weekday, zero-return proportion separate. Holidays/half-days are not silently pooled into a standard weekday sample. Event studies anchor actual release time into tradable sessions; pre/post windows, overlapping events, repeated issuers and selection universe are declared. Default at least 30 distinct events and 10 issuers before pooled statistics, with clustered or block uncertainty appropriate to dependence. Small samples remain individual examples, not confident probabilities.

French series are reconstructed and can change as source data is revised; their 2025 FIZ→CIZ transition changes monthly construction and dividend timing. Pin the download vintage and provider format. Do not join legacy and current files without declaring and testing that transition. [P02] Existing house-basket seasonality and French factor seasonality remain different products within one interface.

### 7.7 Valuation and participation coverage

Any aggregate valuation needs the denominator population and an aggregation rule. A weighted arithmetic mean of P/E is not equivalent to aggregate market cap divided by aggregate earnings. Prefer a declared aggregate earnings yield where negative earnings are economically meaningful; explicitly separate nonpositive-denominator ratios. Proposed minimum valid valuation weight is 80%, with positive/negative/unavailable weights reported. Require PIT filings and compatible shares/price where a historical valuation is requested. No valuation data are needed to admit an equal-weight return series; do not confuse a missing valuation metric with missing price returns.

## 8. Proposed read-model contract

`contracts/factor_read_model.v0.schema.json` is an executable **candidate**, not the incumbent integration contract. It defines an envelope with:

- `schema`, `contract_status=PROPOSED`, owner-referenced descriptor and semantic/cohort/series specs;
- `history_mode`, selection and measurement cutoffs, basis/currency/calendar/session/venue, construction version;
- source/identity/membership/action/rights receipts as **references**, not mirrored authoritative stores;
- calculation inputs/result digests, code source commit and correction lineage;
- statused observations/metrics with finite numbers or explicit nulls, intervals and coverage;
- non-authority flags, including no ranking, gating, sizing, escalation, portfolio or ThemeState effects.

Series specs are immutable semantic inputs. Fields with unknown evidence are null plus a reason; they cannot be synthesized from file mtime or a downstream fetch. Every successful strict-PIT result must have a qualified cohort and input manifest. A top-level failed gate may produce a status-only envelope without measured observations. Omitted metrics mean “not requested”; a requested unsupported metric is explicit unavailable.

**Compatibility decision:** accept an additive `factor_atlas` feed only through the existing Terminal route owner, with the existing auth/origin/size/error policy. Add a dedicated parser in `terminal/lib/factorAtlas.ts` only after owner approval; do not weaken `readableOwnerEnvelope` for the existing five feeds. Preserve existing URL/history ownership and make new query state namespace collision-free. Macro can consume the same published read model through its current rendering path; validated research consumes the source-qualified artifact directly under its existing admission rules. One publication owner, no parallel collector/API/auth/cache service.

The exact production publication path is an **owner acceptance gate**, not a guessed endpoint. The implementation handoff names a proposed owner output at `site/marketdata/factor_atlas.json`, but it must not be created, exposed or added to an allowlist until its rights and transport are accepted. Public Terminal fixtures must remain synthetic.

## 9. Data coverage and rights matrix

| Input / owner | Observed evidence | Internal measurement | Customer display / redistribution | Next qualification |
|---|---|---|---|---|
| House curated definitions / membership | `config/theme_sources.yml` marks `mastermind_curated` direct-display/house; 49 US baskets in pinned document. | Definition use supported within owner scope. | Definition permission is not price permission. | Bind exact curation revision, existing ACL/purpose; do not broaden the GMI registry's jurisdiction. |
| GMI semantic nodes / crosswalk | Existing owner references and direct/proxy distinction. | Use admitted read references. | Follow owner rights and public-emission decision. | Verify actual admitted graph/version; no new microtheme constituents. |
| Finviz theme structure/performance | Current theme source registry says internal-only, including Oct-6 Chairman no-public-display disposition; specific legacy paths are grandfathered, not arbitrary descendants. | Only within the recorded purpose and owner gate. | **Not admitted for new Atlas public display.** | No scraping another copy or extending path exemptions. Procurement is an owner/human rights decision. |
| THS concepts | Same registry: internal-only, receipted collection. | Within existing scope only. | **Not admitted for new public Atlas display.** | Owner evidence, not inferred access rights. |
| Yahoo/basket adjusted prices | Existing collectors and price-ladder basis selection. | Exact intended-purpose authorization not established here. | Not qualified. A software license/accessibility is not a market-data license. | Owner entitlement receipt: source, fields, derived use, display, export, retention, territory, user class and expiry. |
| Legacy broad close caches | Mixed/rebuilt/raw-ish history warning; adjusted vintage may be unknown. | Unqualified for verified total-return claims. | Entitlement separately unresolved. | Owner raw/actions or consistent admitted vintage; no silent fallback. |
| Reference shares / float | Current share reference used by live factor code; historical float not certified. | Live coverage not PIT coverage. | No new rights inferred. | Historical dated share/float owner, correction and publication clocks. |
| EDGAR fundamental filings | Existing as-of factor path. | Reuse native filing/identity selection, not today's restatement backfill. | Under incumbent data admission; not independently licensed/cleared by this study. | Filing availability, period, unit, entity, restatement and universe receipts. |
| FINRA short interest | Existing current snapshot omitted by PIT factor code; public methodology distinguishes positions from volume. | A released-as-of cohort needs publication history, not snapshot backfill. | Dataset/API entitlement and redistribution purpose not established here. | Exact release records, float/shares denominator basis and retention/display rights. |
| French academic data | Existing seasonality owner; public construction and revision notes. | Refer to source-defined research series with vintage. | Do not assume bulk rehosting/commercial rights. | Owner use/attribution policy and source file hash/version. |
| ETF and GICS data | Referenced/proposed classes, not a certified exhaustive owner-data census. | Use existing instrument and classification owners. | No permission inferred from a freely visible website. | Fund/security identities, holdings/classification versions and licenses. |
| Custom user portfolios | No new snapshot store created. | Requires incumbent account/portfolio owner and user ACL. | Account-private; no public fixtures with real holdings. | Existing snapshot/flow contract and isolation tests. |

The public yfinance project itself points users to Yahoo's data terms and cautions about intended personal use. That is a reason to require actual entitlement evidence, not a legal opinion that every existing Mastermind use is forbidden. [P08] No new price fetch, vendor account, paid subscription or acceptance of terms was performed.

## 10. LIQN comparison study

A live public landing read confirmed LIQN's first-party metadata claim of **150+ thematic factors across 3,000+ US equities**. The rendered public surface offered sign-in; it exposed no methodology links. No authentication was attempted. The public evidence available here did **not** establish exact weighting, rebalances, composition effective dates, dividend/corporate-action basis, ranking tie rules, monthly-return construction or synthetic-spread financing. [P09]

Accordingly, no numeric “Mastermind minus LIQN” return-method error is claimed. LIQN's stated scope is not comparable to 49 house baskets: its factor and equity population definitions are unverified. Monthly heatmap/multi-factor/spread features discussed in secondary discovery material remain **feature hypotheses**, not confirmed internals. The detailed evidence matrix and deterministic black-box test design are in `03_LIQN_EVIDENCE_AND_COMPARISON.md`.

A legitimate future comparison uses lawfully available displays/exports with timestamps and composition revisions. Test unchanged-roster windows, constituent round trips, dividend/split dates, composition-change boundaries, incomplete coverage, rebasing and leg swaps. Record expected results for daily constant-weight, periodic drift, endpoint-average and financed-spread models. Mark each model supported, contradicted or still underdetermined. Never infer financing from a line labeled “spread,” or PIT from a dated composition list alone.

## 11. Implementation waves and dependency order

### W0 — Qualify custody and contracts, not a new project queue

Resolve the refused required reads only after an actual permitted-access change; do not rephrase or switch carriers to obtain the refused effect. Re-read current protected procedures, recover the existing GMI/price/identity/basket/Terminal owners and pending effects, reconcile the specific collision PRs and accepted interface. Register one operation/workspace through existing runtime/workspace law. Record exact source heads and path custody. Publication and schema approval are different from permission to draft research.

**Exit:** accepted source/data/consumer contract and an owner-native carrier; or a precise gate with no source writes. This session exits through the latter.

### W1 — Pure read-only pilot, three existing house baskets

Proposed new paths after owner acceptance: `engine/factor_atlas_read.py`, `tests/test_factor_atlas_read.py`, `tests/fixtures/factor_atlas/`, `contracts/factor_atlas_read.v1.schema.json`. No changes to existing `data/` owners or graph/ranking/portfolio state. The module composes immutable owner-returned inputs; it must not own a new constituent or price database.

Use `mag7`, `ai_infra`, `defense` only if each membership and every required price field is admitted for the pilot's exact purpose. Produce source-bound daily histories in CURRENT_ROSTER and PIT_AS_KNOWN, advance breadth, security concentration and historical coverage. Withhold strict history when source/corporate-action/collection gates fail. The owner must accept whether pure mathematics belongs in this additive read module or an incumbent shared helper before code is placed; avoid creating a second parallel financial calculation engine.

**Exit tests:** deterministic byte/result hashes; changed source revision changes identity; current/PIT disagree on a deliberate membership change; pre-PIT dates unavailable; split and dividend neutrality; retained delisting proceeds; no missing-as-zero; rebalance drift; breadth denominator; weight conservation; concentration and attribution; zero source writes; no network fallback; no unintended effects. A strict-PIT path returning only nulls is safe behavior but does not satisfy real PIT capability acceptance.

### W2 — Owner correction and legacy-method compatibility

Through incumbent owners, add any missing collection/availability/action/identity correction contract, and version legacy method changes. Maintain old and new results side by side with exact intervals and deltas. Do not mutate the existing `baskets._ew_level` or shared style engine in the pilot PR. Add owner-native tests before any subsequent repair, including the documented daily-versus-monthly counterexample and strict JSON rejection. Preserve old scientific reports and no-promotion history.

**Exit:** original and corrected histories independently reproduce; source owner signs the semantics; downstream existing tests unchanged or explicitly migrated with reviewed evidence.

### W3 — Accepted native consumer integration

Proposed additive files: `terminal/lib/factorAtlas.ts`, `terminal/lib/__tests__/factorAtlas.test.ts`; owner-reviewed edits only to `terminal/app/api/sector-intelligence/route.ts` and existing Sector Intelligence presentation components. The exact chart-component path must be bound by the owning implementation; it was not qualified here. Do not create a replacement shell/router/auth boundary.

Reuse one existing chart/comparison consumer with an adapter from the accepted schema. Test null gaps, unit conversions, same-vintage common-window rebasing, source-inspector provenance, current/PIT switch, view URL restoration, duplicate IDs, access loss, stale source and oversized/invalid payloads. Respect existing feed ordering and prior consumer behavior.

**Exit:** exact Macro and Terminal heads plus accepted owner payload, unit/type/CI proof and authenticated browser journeys at desktop/tablet/mobile; served-build/source markers match the accepted revisions. Creation, merge and deployment are separately recorded.

### W4 — Complete descriptive analytics

Extend the same read model with policy-versioned horizon, rolling distribution, volatility/downside/drawdown/tails, overlap/correlation/attribution and seasonality. Use incumbent French/volume/fundamental owners; no new collector or ranking engine. Admission tests cover every metric's minimum and insufficient evidence. Derived statistics share the same underlying admitted returns rather than quietly rebuilding their own cohorts.

### W5 — Styles, dynamic cohorts and sophisticated spreads

Only after PIT universe and released-as-of features are qualified: styles with deterministic ties and breakpoints, short-interest/earnings cohorts, costed long-short, beta-neutral residuals, leveraged comparators and user snapshots. Each class adds its own explicit methodology version. Do not reuse a live factor rank table as proof of historical portfolio selection. Investment/forecast claims require a separate validated research consumer, not Atlas UI acceptance.

## 12. The 10/10 end-user and machine-consumer acceptance ruler

Each dimension is binary and evidence-bound. **10/10 requires all ten; 9/10 is not release permission when the missing dimension is a gate.** This session does not award a production score.

| # | User promise | Machine / acceptance evidence |
|---|---|---|
| 1 | I know what the selected factor means. | Correct owner-qualified semantic ID, class, direct/proxy distinction and source definition. |
| 2 | I know exactly whose returns I see. | Complete cohort revision, listing/security identity, weights and denominator; current versus PIT label survives every view/export. |
| 3 | The line means what its method says. | Hand-verified rebalance/drift, price/TR, splits/dividends/mergers/delistings and financing fixtures reconcile. |
| 4 | I can reproduce the historical claim. | Same immutable inputs produce identical calculation core and digest; dependencies/calendars/units recorded. |
| 5 | History never borrows knowledge from the future. | Adversarial availability/knowledge/alias/classification tests; strict PIT rejects fallback and incomplete clocks. |
| 6 | Missing data are visible, not reassuring fake zeros. | Null states and coverage appear in values, ranks, charts, heatmaps, aggregates and exports. |
| 7 | Comparisons use comparable periods and meanings. | Matched endpoints/basis/currency, explicit spread type, overlap and pair sample counts; no scale-dependent fake alpha. |
| 8 | Corrections are explainable without rewriting history. | Original/superseding source and calculation revisions, quantified deltas and recoverable prior result. |
| 9 | Data are used and shown lawfully within access bounds. | Accepted purpose-specific rights/ACL receipts; authenticated transport; no copied vendor/portfolio data in public fixtures. |
| 10 | This works in the actual product and research path. | Exact-head tests and independent review, accepted interface, required CI, served version and authenticated consumer/browser proof; no GMI/rank/portfolio effects. |

## 13. Refused and deferred ideas

Refuse a second canonical theme graph, constituent/identity/ThemeState store, source-rights registry, collector, publication/auth service or execution lifecycle. Refuse backward application of today's roster labeled PIT; missing values as zero; undocumented available-name renormalization; mixed price vintages; current market caps/float/classifications as historical facts; automatic “delisted = zero”; academic factors relabeled house baskets; price ratio relabeled funded long-short; leveraged multi-period multiplication; inherited microtheme membership; Finviz/THS rights by grandfathered-path analogy; production scores from fixture-only tests.

Defer covariance/risk-parity optimization, forecasting probabilities, portfolio trade sizing, automated factor discovery, causal theme attribution, live intraday global synchronization, borrow execution, custom-account writes and comprehensive options-derived cohorts. They are not required for the first trustworthy read model. Retain exploratory charts only with explicit descriptive status and no ranking/decision authority.

## 14. Exact result, limitations and continuation frontier

**What this session produced:** this specialist architecture/research report, source/capability evidence register, LIQN evidence-limit comparison, candidate schema/metric policy, an executable native handoff, and a synthetic mathematical conformance oracle with separately recorded test results.

**First native implementation result: `NOT_STARTED_GATED`.** No implementation PR/head exists for this commission. No real house-basket history was qualified or published. No native engine test suite, independent exact-head review, CI, deploy or authenticated browser proof was completed here. The local conformance suite proves only the mathematics and rejection cases it executes; it does not prove owner adapter or consumer compatibility.

**Specific missing inputs:** completion of required protected/custody reads under lawful access; current affected-head/custody agreement; exact price-purpose rights; corporate-action basis/vintage and actual interval coverage; complete PIT collection/knowledge evidence; accepted additive Terminal feed/consumer binding. The first native action after those gates is W1 under the existing owner operation, not another ontology study or a new worker queue.

**Persistence:** conversation files and their SHA-256 manifest are real artifacts, but they are not canonical GitHub/Agent OS publication. Keep `NOT_CANONICALLY_PERSISTED` until the owner-approved destination is written and read back with a commit/digest receipt. Do not release or replace another owner's active workspace.

## Source register

All Macro links below use `cdbcd143dcfa419ab0637bc11dd4c80368143e2e`; Terminal links use `bacda5dcc30682f9327e037a2d4425bd9714ac3a`. Findings refer to inspected ranges/functions, not automatic whole-file review.

[M01]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/engine/baskets.py
[M02]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/engine/group_flow.py
[M03]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/engine/subsector_rotation.py
[M04]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/engine/factor_series.py
[M05]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/engine/equity_factors.py
[M06]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/engine/factor_seasonality.py
[M07]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/engine/price_ladder.py
[M08]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/engine/basket_membership_pit.py
[M09]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/lib/dataos/identity.py
[M10]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/lib/dataos/price.py
[M11]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/lib/closes_panel.py
[M12]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/data/baskets/membership.json
[M13]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/data/baskets/snapshots/_cadence.json
[M14]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/config/theme_crosswalk.yml
[M15]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/research/theme_graph/THEME_FABRIC_COMPLETION_RESEARCH_2026-10-07.md
[M16]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/research/theme_graph/theme_fabric_gap_matrix.json
[M17]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/research/FACTOR_INTELLIGENCE_MASTERPLAN_BY_FABLE.md
[M18]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/agentos/handoffs/GMI-THEME-GRAPH-2026-10-08-finviz-discover.md
[M19]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/tests/test_factor_series.py
[M20]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/tests/test_us_basket_membership_pit.py
[M21]: https://github.com/mastermindx-market-intelligence/macro/blob/cdbcd143dcfa419ab0637bc11dd4c80368143e2e/config/theme_sources.yml
[T01]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/bacda5dcc30682f9327e037a2d4425bd9714ac3a/terminal/app/api/sector-intelligence/route.ts
[T02]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/bacda5dcc30682f9327e037a2d4425bd9714ac3a/terminal/lib/sectorIntelligence.ts
[T03]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/bacda5dcc30682f9327e037a2d4425bd9714ac3a/tests/test_factordata_source.py
[P01]: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-index-math.pdf
[P02]: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
[P03]: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html
[P04]: https://syndication.finra.org/content/short-interest-what-it-what-it-not
[P05]: https://developer.finra.org/docs
[P06]: https://www.spglobal.com/spdji/en/landing/topic/gics/
[P07]: https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec
[P08]: https://github.com/ranaroussi/yfinance/blob/main/README.md
[P09]: https://liqn.ai/landing
