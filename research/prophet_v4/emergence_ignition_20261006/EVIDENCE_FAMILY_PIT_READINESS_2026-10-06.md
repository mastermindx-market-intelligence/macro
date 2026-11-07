# Prophet Emergence + Ignition: evidence-family point-in-time readiness

**Research date:** 2026-10-06. **Authority:** research and source audit only. **Production effects:** none.

**Macro source pin:** `731a23fb64b9f6f1a321c77618f927f1a58d2d41`. **Parent discovery carrier:** [#8495](https://github.com/mastermindx-market-intelligence/macro/pull/8495), head `770918cb266b5d884978e31d61670b4efd789eaf`. Protected Mastermind procedure pin supplied by the commissioning owner: `a6d40ff648671b03bd4d829d84dd066b58ea8c3f`.

## Decision

**Build the existing B03/B04 research-attention semantics and preserve qualified source evidence now. Do not call the current historical three-flag count an independent, point-in-time-qualified convergence measure.** The estate contains useful collection and identity primitives, including real SEC filing clocks, observed news records, source-hashed Q2 holdings, and a substantial prospective expectations tape. The complete chain from those records to a frozen, source-qualified Prophet exposure has not been demonstrated by this census.

The main distinction is **row admissibility versus family readiness**. A particular filing or news row can have a valid source clock and be usable under a named evidence class. That does not establish complete source coverage, correct historical security binding, a valid pre-event expectation, an admissible signal age, or independence from another counted family. Conversely, incomplete family coverage must not cause a demonstrably valid individual source row to be discarded from descriptive research.

Four findings materially sharpen the inherited report:

1. **The current EPS panel is mixed, not uniformly synthetic.** Of 113,469 rows, 82,481 have an exactly 60-day period-end-to-as-of interval, and 30,988 have other intervals. The collector has a real earliest-filing-date overlay, but the output drops the clock-basis and filing identity. The exact-60 group is consistent with the fallback; equality alone does not prove that every such row is synthetic. The panel remains unsuitable for strict event-arrival qualification because neither the clock basis nor the actual EPS value's accession/revision survives. [S01–S03]
2. **A true filing clock exists elsewhere at useful breadth:** 173,495 Item 2.02 filings for 2,765 tickers, with CIK, accession, filing date, and parseable acceptance timestamp. This is an earnings-filing clock, not an automatically linked earnings-surprise value or necessarily the earliest issuer release. [S04; census]
3. **The board's `news_burst` is a capped recent-headline count.** It is sourced from `site/news/by_ticker.json`, not directly from the Polygon sentiment snapshot parquet. The board discards upstream article identities, event clusters, timestamp quality, and capture clocks. Three items are not three independent catalysts, and neutral lean can mean no classified sentiment rather than affirmative neutral evidence. [S05–S08]
4. **The five original ignition issuers' selected ownership evidence reduces to three Q2 filings.** TSLA/ISRG use D1, ADM/PRIM use Soros, and INTC uses Coatue. All three filings were accepted August 14 and captured August 18. NVDA uses that same Soros report. Issuer deduplication therefore does not create five independent ownership information shocks. [S09–S11; selected-case results]

All observations through 2026-10-06 remain discovery or historical diagnostic evidence under this commission. This report does not promote any row to prospective confirmation, amend the exposure after observing returns, or change Entry Availability, ranking, alerts, plans, sizing, or trading authority.

## 1. Audit boundary and reproduction

The census reads exact Git objects with `git show <sha>:<path>`. It does not execute collection, earnings, news, options, ranking, or publication producers. It does not fetch a vendor, edit the source checkout, or build a new store. The research inventory script is `scripts/census_evidence_sources.py`; its output is `results/evidence_source_census.json`. Each inspected file records its immutable Git blob, byte count, SHA-256, and source URL. No copied source Parquet is included in the deliverable.

Inventory counts describe the committed source vintage at the pin. They are **not** a historical delivery census. A historical event in a current file may have been collected much later; a later corrected value can retain an old event date. The separate emergence/ignition studies own the first-versus-later board reconstruction and the episode outcomes. This census supplies source admissibility, not a replacement population or candidate identity.

Relevant newer work was reconciled through actual GitHub PR state. The exact observed states and heads are saved in `results/evidence_relevant_carriers.json`:

| Existing carrier | Reconciled state | Consequence for this study |
|---|---|---|
| #8189, earnings evidence semantics | Merged 2026-10-05 | Reuse factual earnings/dossier semantics. The legacy C1 default was deliberately retained. |
| #8069, Q06 comparable revenue | Merged 2026-10-05 | One exact source-bound AAPL comparison is an important construction proof, not broad earnings-surprise coverage. |
| #8312, Information→Price/SRC-A1 | Merged 2026-10-06 07:31:46Z | Native physical expectations collection proof exists. It does not supply missing identity, fiscal comparability, contributor identity, source-issued clocks, or downstream rights. |
| #8192, prospective capture/integrity | Open, non-draft; reported CI integration failures | Do not claim full prospective capture has landed. Preserve the existing repair/carrier. |
| #7869, B04 A7–A12 amendment | Open draft | Consume as a proposal; it is not adopted source law. |
| #8004, identity-bound D5 repair | Open draft | The current pinned D5 still has the known security-to-issuer binding gap described below. |
| #7264, private Lab research view | Open draft | A source/API drawer proposal is not production evidence availability. |
| #8454, ticker-news correctness/store | Open draft; `BUILT_NOT_PROVEN` | Reuse its deterministic clustering/correction work; live rights, activation, deployment, and natural-session proof remain unproven. |

## 2. Which clock answers which question?

The following must remain distinct in every family adapter and study row:

| Clock or identity | Meaning | What it cannot prove |
|---|---|---|
| `event_at` / fiscal `period_end` | When an economic event happened or which accounting interval a number describes | When it was public, observed, computed, or served |
| Source publication / acceptance | When this exact source disclosure became available on its own channel | That Mastermind captured it then; that an earlier press release had the same numbers |
| System observation / capture | When Mastermind received this exact source revision | That every downstream reader had already seen it |
| Derived `computed_at` / generation | When the feature/dossier was assembled from those exact inputs | Source arrival time or UI visibility |
| Product publication / reader visibility | When the qualified bundle reached a user or machine consumer | That the exposure existed at the earlier event or board label date |
| Source/body/version identity | Which actual bytes, filing, or provider revision support the observation | Timing without corresponding clock receipts |

For an **observed-as-run** result, all required source, capture, computation, and publication conditions must hold at the recorded decision cut. In a public-information replay, source-time admissibility may be reconstructed under a registered replay class, but it must use the version of the fact that was public then. A current value with an old filing date is not that reconstruction. Public replay and observed-as-run samples cannot be pooled silently.

The current D5 owner already implements a useful subset of this discipline. It selects a workspace revision only if `source_available_at`, `observed_at`, and workspace `generated_at` are all no later than the B1 decision cut; it separates later correction receipts. It calls the source clock `source_published_at`, maps `known_at` to owner `observed_at`, and explicitly marks per-source capture time unasserted when the revision receipt does not expose it. It discovers the current manifest's event, not the complete historical event set. [S12]

R6-D07 has been adopted at the vocabulary level. Its categories are `OBSERVED_AS_RUN`, `PUBLIC_INFO_REPLAY`, `RETROSPECTIVE`, and explicit null. The adoption explicitly did not cure blocked source rows: capture clock plus pinned store generation are required for observed-as-run. The merged ruling's original B04-D S1 rows remain blocked until their named row remedies carry qualifying receipts. This audit is evidence for those remedies, not an owner-authorized class upgrade. [S13]

## 3. Readiness matrix

The detailed machine-readable matrix is `results/evidence_family_matrix.csv` and `.json`. “Conditional” means the stated row gates must be proven; it is not an assertion that the end-to-end serving family is currently qualified.

| Family / source | Direction | Knowability and staleness | Independence unit | Current coverage / prospective readiness | Emergence | Ignition |
|---|---|---|---|---|---|---|
| A: current board news chip | Direction-neutral attention; polarity separate | Daily artifact date and reduced counts; required item/cluster clocks omitted | Not retained in chip | Useful historical proxy; not a complete qualified exposure | Context/proxy only today | Context/proxy only today |
| A: native news ledger / qbus | Typed event direction or neutral attention | `first_seen_utc` / `_crawled_at` plus provider-dependent source-time meaning; retain exact revision and no future rows | Native item ID, qbus event key, then explicit upstream-origin link | Individual rows can support timed attention; cross-family origin joins, coverage and correction history remain necessary | Conditional A row | Conditional A row |
| B: legacy EPS/SUE | Cross-sectional relative seasonal EPS momentum; not analyst beat | Mixed unlabeled as-of basis; final-vintage values; no accession/value lineage | `(issuer, metric, fiscal interval, value revision)` is missing from board proxy | Strict arrival ineligible; contextual historical covariate only | No primary leg | No primary leg |
| B: SEC Item 2.02 clock + qualified release/dossier | Actual sign only after comparable facts or pre-release expectations | True filing acceptance exists; exact release/value/capture/generation must be bound | Native CIK/accession/body revision and earnings event | Strong clock infrastructure; broad surprise/value join not shown; D5 identity repair pending | Conditional B row | Conditional B row |
| B: analyst expectations/revisions | Aggregate expectation level/change; no contributor-specific upgrade proof | SRC-A1 has prospective system/provider observation; source-issued time absent; same fiscal target and value basis required | Collection/observation IDs, supersession chain; same-event linkage needed | Physical source is live; identity/basis/rights and contributor comparability incomplete | Internal source accrual; not primary-ready | Same |
| B: guidance / KPI | Raise/cut/improvement only on comparable typed facts | Owner release/version clocks; historical phrase hits are insufficient | Same earnings/guidance origin; revised KPI is not a new independent family | Narrow factual/dossier primitives exist; broad typed source population not proven | Conditional B subtype | Conditional B subtype |
| C: 13F new/add | Increase/newly disclosed long common-equity holding; not current flow | Filing acceptance, first capture, period age and disclosure age; both quarter snapshots and PIT fund grade needed | One ownership family; filing/control-group origin, security/CUSIP, two qualified holdings versions | Recent Q2 source rows often well stamped; older vintages uneven; chip omits clocks/grade receipt | Conditional C row; age policy required | Same |
| D: peer/customer/supplier read-through | Direction requires explicit relationship role plus event effect | Both relationship and source event must be effective and known at cut | Typed relation + issuer event origin | Current inspected graph lacks economic edge types; material 8-K counterparty census below; no broad qualified path demonstrated | Conditional prereg category; not ready | Secondary only; excluded from initial exposure |
| E: sector/industry/theme rerating | Group observation; often overlaps price/RS context | D0 `PIT_PARTIAL`; exact membership version, state date, belief/capture time and coverage required | Common group/source shock, not count of constituent tickers | Restricted 2026 window only; membership is not a rerating event | Conditional prereg category; not ready as broad primary evidence | Secondary only |
| F: policy/contract/external catalyst | Positive effect requires typed issuer exposure and economic direction | Exact source release/capture/version plus contract or policy effective interval | Underlying policy/contract origin, linked to its news and read-through | Material-filing/news leads exist; no broad qualified directional population proven by this bounded census | Conditional prereg category; row gates remain | Secondary only |
| Options/GEX/flow | Estimated positioning; confirmer or fragility/hazard | EOD/delayed source, contract/spot/Greek/quote alignment; calibrated sign and source clock required | Native trade/contract/positioning origin; not equity cash flow | Incumbent sign gate remains direction-unreliable; named hazard/confirmer contracts already exist | Secondary context | Secondary context; excluded |

Ignition's frozen primary families are A/B/C. Emergence's preregistration also enumerates D/E/F conditionally after typed direction/provenance/point-in-time qualification; that is not permission to insert a convenient retrospective relationship or theme. New options/insider/alternative-data families remain separate secondary accrual unless the existing owner explicitly registers them before evaluation.

## 4. Family findings

### 4.1 News: source-rich records become a source-poor chip

`engine/financial_news.py` builds the actual per-ticker feed. Its `mastermind_by_ticker` reducer sets `n_recent=len(items)`, aggregates available sentiment, and retains only the first four headlines in `top`. Upstream `_dedup_rank` removes duplicate item IDs and caps the chosen feed. The board then retains only `n_recent`, `sentiment_lean`, `n_pos`, and `n_neg` when the count is at least three. The label is not a standardized burst against a ticker's historical arrival rate, and the top-headline truncation is not an exhaustive input manifest. [S05–S06]

At this pin the compact index has **691 ticker keys**, **50** with `n_recent>=3`, and **821 retained top-article references**. Its lean distribution is 605 neutral, 63 positive, and 23 negative. These are one current artifact's counts, not the study's historical prevalence. The stale source comment saying 17 ticker coverage must not be treated as the current census.

There are two useful upstream record sets:

* `data/news/event_log.parquet`: 1,122 events, zero duplicate event IDs, capture range July 11–October 5, and publisher/crawl `seendate` beginning June 17. Two rows have source time later than capture; they require row-specific clock disposition, not silent family-wide acceptance.
* `data/qbus/items.parquet`: 49,116 unique item IDs and 46,539 event keys. All capture clocks parse, spanning June 19–October 6. Its current vintage includes old source dates; that range must not be mistaken for an equally long observation history. Its caller-stamped `_crawled_at` is the relevant system observation field. Only **565** rows have a nonblank `body_sha256`; **48,551** do not. Retained item/title identity must not be described as exact-body replay for those missing-hash rows.

The separate Polygon sentiment store has 31,757 daily snapshots for 527 tickers from June 21 to October 6. It contains counts and `_first_seen`, but no article or event identities. Its same-ticker/snapshot-date write is keep-last, so `_first_seen` is the capture time of the retained daily aggregate, not necessarily the first capture of that day's information. This source cannot independently reconstruct the chip's exact item set. [S07–S08]

Timestamp quality is heterogeneous by design. Financial News labels GDELT as crawl-bounded and RSS/provider dates as publisher-stated. A generic field called `published` in the compact index must not erase that distinction. Neutral attention is allowed in A; it must remain separate from positive fundamental evidence in B. A news article restating a guidance raise does not create an independent A+B pair solely because it arrived through a different feed.

The new ticker-news PR #8454 directly addresses immutable provider revision IDs, correction/removal, cross-source clustering, and qbus-owned history. It is still an open draft with unproven live activation and natural-session delivery. The next integration should consume that owner when qualified, not create another news event service.

### 4.2 Earnings: real clocks exist, but the value version is the decisive join

`collectors/edgar_eps.py` fetches SEC frames for EPS values. It initializes a synthetic `period_end + 60d`, then overlays the earliest qualifying 10-Q/10-K `filed` date returned by the companyconcept API. The overlay output explicitly drops `filed_date`; the final panel only carries `ticker`, `period_end`, `eps_q`, and `asof_date`. The separate filing-date sidecar is absent at the pinned commit. This is a mixed-clock panel with no retained clock-quality flag. [S01]

The SEC describes the frames endpoint as choosing the last-filed fact fitting the requested calendar interval; companyconcept contains disclosures from multiple filings. Therefore attaching an earliest date to a value drawn from a later frame **can backdate a later fact version**. This is a data-construction risk established by the source semantics, not a claim that every EPS observation was actually restated. Merely replacing the 60-day offset with a real date does not repair value lineage. [P01]

The existing `legacy_sue_evidence` correction accurately calls the board value a cross-sectional z-score of seasonal EPS momentum. Positive `sue_z` means above peers on that transformed metric; it does not establish a positive raw EPS change or an analyst-consensus beat. The legacy fusion boolean also accepts any nonzero SUE value and uses an `or 999` freshness fallback, which can mishandle a genuine zero-day age. The opt-in corrected earnings semantics from #8189 do not silently change the default historical feature. [S02–S03]

The Item 2.02 store supplies the missing **filing chronology**, with 173,495 unique CIK/accession rows and parseable acceptance timestamps. It contains neither actual EPS nor expectation, and it has no per-row collector capture timestamp. `report_date` must not be joined to EPS fiscal `period_end` as if those meant the same thing. Selecting the nearest filing before a board date is a diagnostic, not a validated surprise join. The selected-case JSON explicitly labels the recent filings as **not linked to the EPS value**. [S04]

The correct existing route is already available in pieces: CIK/accession filing keys; `ReleaseRevision` source/body hash and supersession; exact byte/span replay receipts; source-bound comparable facts; and the D5 vector's three-clock selection. #8069 supplies one exact AAPL comparable-revenue proof. It establishes a factual reported comparison, not an analyst surprise or broad market coverage. #8189 preserves explicit unavailable consensus, guidance history, matched contributors, and comparable financial bases. These should be expanded through their source owners and B04 rather than bypassed with a ticker/date lookup. [S12, S14–S16]

**Row admission for a positive B earnings leg requires:** the same issuer/security binding; actual and expected/comparison fiscal target; compatible units, currency, accounting/share basis; pre-release expectation observed and available before the release when a surprise is claimed; the exact actual source revision available by the decision; retained raw direction; and an explicit active-age rule. Source acceptance alone is insufficient.

### 4.3 Revisions, guidance and KPIs: collection readiness is not semantic readiness

The legacy revision history contains 22,951 ticker/date records for 1,545 tickers, spanning June 16–October 5. It preserves daily snapshots of aggregate breadth and estimate changes, but does not expose an individual analyst revision history. Same-date replacement means historical intraday variants need an external generation receipt.

The newer SRC-A1 tape contains **495,320 observations for 1,506 tickers** from August 25 through October 5, accompanied by **8,991 attempts** over 1,510 tickers: 8,766 success, 79 partial and 146 null results. It records collection/attempt IDs, payload hashes, provider/system observation clocks, typed missingness, correction state, and supersession. **470,624** rows have `period_end`; **419,250** have a nonmissing value; **400,060** have both. All source-effective and source-published clocks are absent, all issuer/security references are absent, contributor coverage is zero, and all rows have `rights_class=UNKNOWN`. These are specific missing semantics, not a failure to acquire data.

The collector correctly treats a known fiscal rollover as a new observation rather than a same-target revision. If either period end is missing, its value-comparison lineage can still run; a consumer must therefore refuse to interpret an unbound relative horizon such as `0q` as a known same-quarter revision. Aggregate consensus change can reflect contributor turnover. It is not a contributor-matched upgrade, and it does not show that a forecast was issued at its later fetch time. [S17]

#8312 now proves the native physical source's prospective collection/lineage behavior. The current source-rights register still records Yahoo/yfinance expectations as internal-only acquisition with unqualified model/redistribution posture. This report does not reinterpret that register or treat physical source acceptance as downstream use approval. Preserve the tape and its typed uncertainty; qualify an owner-backed identity, period, basis and permitted use before it becomes a counted B exposure. [S18]

The simple `guidance_hits.parquet` is much narrower: 18 records/12 tickers, file dates April 22–August 6 and fetch dates June 28–August 8; its `polarity` field is null on every row. Phrase-direction tags are not comparable guidance values. The annual RPO store has 381 rows/75 tickers and no source-specific capture or revision identity. These may direct research but do not constitute timed guidance/KPI revision families. The typed factual earnings owner is the appropriate source of such observations, preserving same-origin grouping with the earnings event.

### 4.4 Ownership: usable recent filings, old information, and a shared-origin sample

The 13F collector now captures acceptance, availability date, accession, source hash, parser version and `fetched_at` on new snapshots. It preserves older snapshots and has an accession-keyed receipt log. Acceptance at or after 16:00 Eastern rolls the earliest eligible close-based trade date forward; calendar-to-session snapping is separate. Legacy rows can be joined to filing receipts, but a receipt must not falsely backdate the later capture of previously missing holdings bytes. [S09]

The original-snapshot inventory has **709 dated files**, **51 funds**, and **28,912 position rows**, spanning period ends September 2022–June 2026. Files in which every row has all five required filing/acceptance/accession/source-hash/fetch fields account for **1,889 rows**; legacy or incomplete files account for **27,023**. This whole-file completeness classifier does not count every individually complete row inside an otherwise incomplete file. The current Q2 inventory has **49 files**, of which **46** pass that completeness check. That is promising recent source coverage; it is not proof that every old quarter or every security mapping is qualified. The result JSON excludes amendments and non-date summary files from this original-snapshot denominator.

The selected-case records prove the following source clocks and disclose their concentration:

| Selected cases | Fund / accession | Accepted, UTC | Holdings captured, UTC | Implication |
|---|---|---|---|---|
| TSLA, ISRG | D1 / `0001172661-26-003662` | 2026-08-14 15:17:28 | 2026-08-18 03:00:56.979769 | One selected filing origin for two ticker episodes |
| ADM, PRIM; also NVDA | Soros / `0000902664-26-003507` | 2026-08-14 20:10:21 | 2026-08-18 03:01:33.698100 | One origin shared by three named examples |
| INTC | Coatue / `0000919574-26-005478` | 2026-08-14 20:03:06 | 2026-08-18 03:00:55.428214 | Separate selected filing origin |

All describe the period ending **2026-06-30**. The selected raw CUSIP records show new disclosed holdings for the five ignition cases and an increase in Soros's NVDA shares from 1,073,206 to 1,464,635. These are retained disclosed positions and changes between reporting snapshots, not observations of transaction time. Small prior positions can be omitted from 13F, and confidential treatment/amendments can change what was publicly visible; “new” must mean new in the qualified comparable disclosed book. SEC 13F instructions confirm quarterly holdings reporting, the filing lag, and exclusion of short positions. [P02]

At the dated cases, the June 30 holdings are approximately 52 days old for TSLA, 65 for ADM/PRIM, 72 for INTC, 76 for ISRG, and 87 for NVDA's September 25 cut. Public filing age and system capture age are smaller and must be reported separately. Do not use only whichever age makes the source look freshest. The chip's literal `Q1-2026 13F` warning is stale even though its actual `period_end` is Q2. [S06]

Fund A/B grades add another point-in-time condition. The incumbent manager-quality function derives grades from realized forward returns in the available close panel and has no explicit decision-cut argument. Recomputing the current grade for an old case can introduce outcomes not available then. Use the grade already captured in that exact historical source generation or recompute only from a pre-cut, versioned input set. An old board chip showing A/B is evidence of what it displayed, not a receipt of the grade's underlying model/input vintage. [S10–S11]

The fusion registry mentions a 63-session staleness allowance for the legacy chip. That number does not settle the new preregistration's required definition of which clock is aged, whether disclosure/position/capture age all matter, or how stale contextual ownership can qualify. The prospective owner must pin the existing intended policy explicitly before accrual; this study must not choose a favorable cutoff after reading returns.

### 4.5 Peer/customer/supplier and group rerating

The current theme graph has **25,100 edges**: 22,431 `MEMBER_OF`, 2,592 `EXPRESSES`, and 77 `TRACKS`. It contains no emitted `SUPPLIES`, `CUSTOMER_OF`, `ENABLES`, or comparable typed economic relationship in this audited store. Reserved schema vocabulary does not establish a populated relationship graph.

The incumbent Group Reads linked-outsider adapter intentionally refuses customer/supplier/partner/competitor labels: a material-agreement filing alone does not establish who supplies whom. It requires a nonempty source counterparty and resolves names through the existing issuer owner, not fuzzy ticker matching. It describes current tape relative to a basket, not a causal read-through forecast. The current material 8-K store has **51,566 rows** for **665 tickers**, including **2,056 nonblank counterparties**. Its source comment describing zero counterparties is stale. This provides a concrete extraction substrate; it does not establish a typed, time-qualified customer/supplier family. The current extracted counterparty must not be backdated solely from its filing date or the row's initial capture field. [S19; census]

The existing D0 membership study remains **PIT_PARTIAL**, with its reported honest window **2026-07-05–2026-10-01**, minimum per-date in-force coverage **660/2,595 = 25.43%**, and a leading-theme membership join beginning **2026-08-13**. Those are that study's fixed source/result boundaries. Current source artifacts include dates through October 3, but this audit does not extend D0's honest-window verdict without rerunning its write-time and coverage rules. It also does not imply a PIT membership tape for 2014–2025. [S20]

Point-in-time membership is a prerequisite for a group observation; it is not itself an independent rerating event. Group RS, breadth, price trend and constituent leadership may repeat information already used in the technical leg and matching controls. Source-backed pricing, capacity, inventory, or capex changes need their own event identity and direction. Several company news items all reacting to one sector release remain one shared shock for uncertainty/concentration analysis.

### 4.6 Policy, contract and external catalysts

Emergence's preregistration also names family F, conditional on explicit event identity and availability. The inspected material-filing and news stores provide existing owner paths. They do not constitute a complete typed policy/contract family: only 1,931 of the 51,566 material-filing rows have a nonmissing amount, and an amount does not establish contract economic direction, affected-issuer exposure or an admissible revision clock. This bounded audit did not conduct a separate exhaustive policy-document census.

Admit an individual catalyst only with its exact source and revision, publication/capture clocks, grounded issuer exposure, explicit economic direction and age/effective interval. Its news articles, a counterparty read-through and an issuer filing can all derive from one underlying contract or policy origin. F remains conditional for Emergence and secondary for Ignition; neither the category's presence in a preregistration nor the number of extracted filing rows is proof of primary readiness. [S07, S19; census; parent Emergence preregistration §3.1F]

### 4.7 Options: preserve the incumbent confirmer and hazard jobs

The incumbent GEX confirmer explicitly assumes dealer sign and consumes delayed EOD data. It provides confirm/neutral/caution context for an existing price thesis. The separate options-flow path signs minute aggregates with a tick-rule approximation and carries a calibration gate; at the pin, `data/options_flow/signing_gate.json` says **`direction_reliable=false`**, `magnitude_reliable=true`, with as-of June 21. A current GEX gate is still `building_history`. The ticker- and method-specific admissibility of any newer options source must be supplied by its own owner, not inferred from availability of another tape. [S21–S22; census]

The theme options witness has an explicit all-false, crowding-hazard/context contract and a September 30 artifact. Its receipt says **`store_present=false`**, **0 of 18 themes with any coverage**, and **3 themes suppressed**. The existence of its contract therefore must not be described as populated theme-positioning coverage. It forbids treating its positioning measures as a positive signal or fused positioning score. Its OI lag convention and coverage suppression belong to that owner and must be retained. This census does not revalidate the claimed empirical sign accuracy in legacy source comments. [S23; census]

For Emergence/Ignition, options can be typed **confirming context or fragility/caution**, outside the frozen primary convergence count. Premium, delta flow, dealer-GEX estimates and OI changes are different quantities; none is net common-equity inflow. A later separately registered hypothesis may test them with quote/trade timing, classification confidence, instrument identity, expiry/Greek/spot alignment and proper coverage.

## 5. Independence: reuse B04 and native source identity

The existing D5 vector already has `source_refs`, `evidence_roots`, `economic_dependence_groups`, and a content-addressed `COMMON_INFORMATION_ORIGIN` contract. Its v1 is deliberately one earnings family, at most one dependence group, and no `evidence_count`/score field. B04's adopted dossier wrapper is the owner for expanding the explanation without changing the closed vector by accident. #7869 is a draft contract extension and #8004 a draft identity repair; neither may be treated as already merged. [S12, S24]

Native news primitives also exist. `qkernel.event_id` hashes normalized title plus source discriminator, so identical titles on different hosts intentionally have different item IDs. `qbus.assign_event_keys` uses shared entity/theme, a three-day window and shingled-title Jaccard >=0.6, then deterministic connected components/representative selection. This is reproducible duplicate clustering, not an economic causal-independence test. In current `append_items`, new rows are clustered within the incoming batch before keep-first append; historical cross-batch identity and corrections therefore need explicit qualification. Re-clustering the entire current store can let later items bridge or rename an earlier component. [S25–S26]

The practical contract is:

1. **Bind exact source revisions first.** Use native filing CIK/accession/body hash, provider stable article/revision IDs, or source-owner observation IDs. Never invent candidate episodes from ticker/date.
2. **Record document lineage and common origins.** A press release, its transcript/repost, articles quoting it, and estimate changes explicitly responding to it share an origin when the source relationship is grounded. A correction updates a version; it is not automatically new independent information.
3. **Apply deterministic duplicate rules within what was known at the cut.** Preserve the rule version, cluster membership, and member capture times. Use explicit native IDs/citations before approximate title matching. LLM suggestions can identify a relationship for review but cannot be the sole admission proof.
4. **Retain each active family's complete activation proof.** Its proof must name every origin needed to satisfy that family's frozen rule. Do not select one convenient article from a mixed burst to conceal overlap with the earnings family.
5. **Count distinct permitted families with disjoint necessary origin sets.** Multiple funds, articles, metrics or KPIs can strengthen a family's explanation; they do not create more families. Shared-origin A+B is one information bundle for this purpose. Unknown origin identity means unresolved independence, not an assumed extra vote.
6. **Preserve cross-episode dependence in evaluation.** Common filings, earnings dates, sector releases and market-wide news can correlate observations across issuers. Report those clusters alongside ticker/date/sector concentration. Operational deduplication does not prove economic or statistical independence.

This is an implementation contract for the existing B04/evidence owners. It is not a new evidence graph, research database, lifecycle or ranking architecture.

### Missing evidence is not a control group

The evaluator needs **EXPOSED / UNEXPOSED / UNKNOWN**, plus reasoned family states. If two allowed active families are qualified and demonstrably independent, exposure can be known even if a third family is unavailable. A 0/1 count is a valid control only when source coverage and absence evidence establish that the second qualifying family is not merely missing. One active, one inactive, one unavailable A/B/C family is **UNKNOWN**, not a clean one-family control.

Equivalently, maintain a lower and upper bound on qualified independent count. Lower bound >=2 establishes exposure. Upper bound <2 establishes unexposed. An interval crossing two remains unknown. Do not impute uncovered names to zero or condition the primary sample on later source completeness. The same contemporaneous coverage rules must apply to exposure and control names.

## 6. Exact next work through incumbent owners

| Priority | Existing owner | Required concrete outcome | Acceptance evidence |
|---|---|---|---|
| 1 | B04/D5 identity + dossier owners | Complete the existing #8004 security/issuer gate and reconcile #7869 against the adopted wrapper | Conflicting/unbound security reads no issuer evidence; decision/current views preserve separate clocks and all-false authority |
| 2 | News/qbus, #8454 | Preserve an exact item/revision/cluster manifest with source-time quality and system capture for every A activation | As-of replay excludes later stories/corrections and common-origin earnings echoes; coverage failures become UNKNOWN |
| 3 | SEC/Earnings/Q06 + B04 | Bind actual fact and comparison/expectation to the exact filing/release version; preserve real clock basis | Synthetic-clock rejection, future-version mutant rejection, pre-release expectation test, actual/current correction view separation |
| 4 | Smart-money + B04 | Carry both position versions, acceptance/capture, security mapping, period/disclosure age and historical grade receipt | Q2 receipt linked to source bytes; no same-day-close use after close; old grade replay excludes later outcomes; no multiple-family credit for multiple funds |
| 5 | SRC-A1/K3E expectations | Consume #8312 physical source proof; qualify the permitted identity/period/basis/use joins | No fiscal-rollover-as-revision, no contributor-turnover-as-upgrade, and explicit unknown source-issued times/rights |
| 6 | Conditional Fusion/B4 + B03 | Freeze a complete source-qualified exposure definition and preserve lossless candidate references, including unanchored observations | Both first-cut exposure and controls carry same coverage policy; source versions/independence reproducible; no new B1 anchor species |
| Later | GMI/Group Reads/options owners | Separately register qualified group, relationship and options secondary evidence | Native data/clock/identity/rights receipts, source-origin controls, and hypotheses frozen before outcome inspection |

The remaining empirical blocker is precise: **the historical proxy cohort lacks complete decision-time source-version and independence proof, and some historical source families lack a defined observable-negative state.** More return combinations cannot cure it. The exact prospective remedy is to accrue the frozen A/B/C exposure with source-qualified origin sets, exact cut/version clocks, cohort coverage/missingness, a preserved historical grade if used, and the incumbent T2 episode identity; accrue the same information for controls. Report source-qualified cohort size separately from total candidates and legacy proxy exposures. Retain B03 early attention without trading authority while this evidence matures.

## Source anchors

All internal source anchors below use Macro `731a23fb64b9f6f1a321c77618f927f1a58d2d41`; exact blobs and SHA-256 digests are in the census JSON. They are code/source evidence, not proof of current runtime deployment.

* **S01** [EPS producer](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/collectors/edgar_eps.py#L10-L19), real-date overlay at lines 171–187, value construction and fallback at 220–245.
* **S02** [SUE construction and legacy semantics](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/sue.py#L63-L94), versioned semantics at 140–190; factual/expectation clocks at 240–321 and 414–451.
* **S03** [Fusion feature extraction](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/us_prophet_fusion.py#L431-L465), registered source descriptions at 229–279, opt-in semantics at 1053–1100.
* **S04** [Item 2.02 filing clock collector](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/collectors/edgar_earnings_8k.py#L1-L45).
* **S05** [Financial News reducer](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/financial_news.py#L877-L922), source-time classes at 139–150 and dedup/cap at 611–633.
* **S06** [Board source propagation](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/scripts/build_stock_library.py#L4466-L4525), actual news source read at 3335–3346.
* **S07** [News event ledger](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/news_event_ledger.py#L75-L88), keep-first and capture at 110–169.
* **S08** [Polygon aggregate snapshots](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/collectors/polygon_news.py#L108-L135), keep-last at 238–246.
* **S09** [13F source metadata](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/collectors/edgar_13f.py#L374-L430), availability policy at 52–81.
* **S10** [13F action/grade owner](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/smart_money.py#L398-L430), receipt bridge at 676–718 and grade call at 798–810.
* **S11** [Manager quality source](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/manager_quality.py#L51-L68), current-panel grade construction at 151–203.
* **S12** [D5 intelligence vector](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/prophet_lab/intelligence_vector.py#L1-L12), clocks at 400–442, current identity gap at 1064–1075, three-clock filter at 1192–1237, origins at 1339–1355, closed group contract at 2193–2222.
* **S13** [Adopted D07 evidence-class ruling](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/research/prophet_v4/r6_program/rulings/R6-D07-01_EVIDENCE_CLASS_REGISTER_ADOPTION_2026-09-27.md#L12-L38).
* **S14** [Release-version binding](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/earnings_release/binding.py#L58-L132).
* **S15** [Exact span replay](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/earnings_release/receipts.py#L160-L202).
* **S16** [Q06 dossier projection](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/prophet_lab/earnings_dossier.py#L1-L24), source/clock binding at 64–115.
* **S17** [SRC-A1 observation and lineage](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/collectors/equity_revisions.py#L324-L369), fiscal rollover/correction at 385–425, legacy daily retention at 783–790.
* **S18** [Existing source-rights register](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md#L113-L143).
* **S19** [Group Reads relation admission](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/group_linked_outsiders.py#L1-L79).
* **S20** [D0 fixed result](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/RESULT.md#L1-L18) and sibling result JSON.
* **S21** [GEX confirmer contract](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/gex_confirm.py#L1-L59).
* **S22** [Options-flow method and gate](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/options_flow.py#L1-L76).
* **S23** [Theme options hazard owner](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/theme_options_witness.py#L1-L79).
* **S24** [Adopted B04 wrapper ruling](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/research/prophet_v4/r6_program/rulings/R6-B04-01_DOSSIER_CONTRACT_2026-09-24.md#L1-L25).
* **S25** [qkernel item identity](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/qkernel.py#L193-L211), shingle/Jaccard at 254–274.
* **S26** [qbus deterministic clustering and append](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/engine/qbus.py#L176-L267).
* **P01** [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), companyconcept and frames sections; accessed 2026-10-06. Primary source for last-filed frame semantics and API update/capture distinction.
* **P02** [SEC Form 13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f), questions 8, 25, 39, 41–43; accessed 2026-10-06. Primary source for quarterly holdings, deadline, omission and short-position limitations.
