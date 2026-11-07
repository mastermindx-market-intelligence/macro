# DI-V1 — financial input qualification and four-company economic bridge

**Date:** 2026-09-16 UTC. **Responsible principal:** Sol. **Existing workstream:** WS:DEFENSE-PROCUREMENT-V3. This extends the research/delivery amendment on #7175; it does not create a new lobe, Executive Job, financial store, signal, or worker assignment.

## 1. Mission and capability boundary

The investor journey remains sector participation -> explanatory mission/theme -> issuer exposure -> incremental profitable business -> expectations and valuation -> research condition -> measured outcomes. A working procurement publisher is necessary but insufficient. Comparing company economics requires correct concepts, reporting bases, scopes and periods, not merely populated numeric fields.

Sol's current Chairman-directed continuation authorizes this research and qualification. Procedure was loaded from protected Mastermind `11101d420179525678449820cbfd6228191c37ee`, Skillpack 1.0.1/bootstrap 1. INDEX, COLD_START, ACTIVE_EXECUTION, RECONCILE_STATE and CLOSEOUT matched their already-read content blobs. Macro owner-path observations were checked against `b6e22a884cd0afc5bb50e8d2ec4554da7a45a1ee` and the retained #7186 source workspace; relevant code reviewed here is not claimed deployed by this document.

The first four-company economic comparison is **NOT QUALIFIED for numeric ranking or a current entry signal**. That ruling is about this observed input contract, not a claim that financial intelligence is impossible or that all company data are unusable.

## 2. Current owner and consumer facts

The existing D4 bridge is not a general company-financial implementation. `templates/government-revenue-dossiers.js` defines an IRDM-only bridge and a fixed award/modification exemplar; `templates/government_revenue.html.j2` explicitly describes it as IRDM-only. `DEC:D4-COMPANY-RAIL-CONSUMES-CI-V1-CONTEXT` permits read-only owner consumption and excludes score-overlay fields. It leaves financial materiality `not_comparable` because the context contract carries no issuer-attributed compatible denominator. Preserve the accepted pilot rather than replacing it.

The current program dossier/ontology contains one Virginia-class program, one capability, one platform, one milestone, three role assertions and zero program-event links. It does not yet provide the missile-program map required by DI-V1. Existing curator `scripts/curate_government_program_ontology.py`, reviewed worksheet, identity graph and dossier composer remain the implementation route; no second graph or company identity is justified.

Actual GETs of `/api/company-intelligence/LMT`, `/RTX`, `/NOC` and `/LHX` all returned HTTP 200, `available:true`, `status:partial`, `company_intelligence_context.v1`. Each reported generation `2026-08-29T00:52:18Z`. Metrics carried `earnings_history` lineage, but their source precision was metadata-only; a present document-level transcript is not a span-level numeric validation. The overview summaries carried `score_overlay` lineage and must not enter the D4 financial bridge.

The owner projection's `_normalize_history_row` in `engine/company_intelligence/views.py` copies numeric history aliases through `finite_number`; `_event_from_history` assigns lineage and can overlay matching score fields. Those operations establish provenance of the supplied value, not verification of its economic meaning. Do not fix an upstream concept error by adding a misleading label in Government Revenue.

## 3. Four real-source qualification cases

These are observations made during this continuation. They are not backdated historical model inputs, exhaustive source coverage, or accepted financial facts in a production owner store. Original issuer datelines identify disclosures; today's successful read does not prove the system possessed that version on the original date.

| Issuer | Observed live context | Primary-source check | Qualification result |
|---|---|---|---|
| LMT | FY2026 Q2; `gross_margin_pct=10.8` | July 23 release labels 10.8% **total business segment operating margin** and separately gives consolidated operating margin 12.4%. [LMT] | **CONCEPT_MISLABELLED.** Do not use 10.8 as gross margin. Preserve the actual segment-operating concept through the financial owner; do not infer a replacement gross-margin value. |
| RTX | FY2026 Q2; generic revenue growth 16%, EPS growth 21% | July 23 release distinguishes reported sales growth 14% from organic 16%, and GAAP EPS growth 29% from adjusted 21%. [RTX] | **BASIS_MISSING.** The values can be valid on their respective bases but are not interchangeable with reported growth. Preserve both bases and their definitions. |
| NOC | FY2026 Q2; generic EPS growth 8% | July 21 release reports diluted EPS 7.68 versus 8.15, down 6%; the prior period includes a 1.04/share divestiture benefit. [NOC] | **COMPARISON_BASIS_AMBIGUOUS.** Approximately +8% can be reproduced by excluding that prior benefit, but this is a possible explanation, not proof of the upstream calculation. Do not label the field reported EPS growth or silently overwrite it with -6. |
| LHX | `latest_event` is FY2026 Q1, call date April 30 | The issuer published Q2 results on July 29. [LHX] | **LATEST_PERIOD_NOT_CURRENT.** A refreshed outer generation cannot make the Q1 event the latest reported quarter. Repair the existing owner selection/acquisition/publication chain before using a cross-company current-quarter comparison. |

For NOC the explanatory arithmetic is `100 * (7.68 / (8.15 - 1.04) - 1) = approximately 8.02%`. This is Sol's explicit inference using disclosed inputs, not an issuer-admitted non-GAAP metric or a license to choose the more favorable growth rate.

## 4. Economically relevant company scope — research reference, not a purity score

The following reported segment figures demonstrate why procurement themes must connect to segment economics. Values are USD millions for the respective FY2026 second quarters; fiscal quarter endings differ and must remain explicit in any owner ingestion. These are not program-specific revenues or a ranking of missile exposure.

| Issuer / disclosed segment | Quarterly sales | Segment operating measure | What must remain separate |
|---|---:|---|---|
| LMT — Missiles and Fire Control | 4,101 | Operating profit 594; margin 14.5%, prior 14.0% [LMT] | The segment is broader than any one missile program. Production demand still needs program, contract and cash-conversion attribution. |
| RTX — Raytheon | 8,269 | Reported operating profit 1,042; reported ROS 12.6%; adjusted profit is separately 1,043 [RTX] | Do not combine Raytheon with commercial aerospace or call all segment sales missile sales. Keep reported and adjusted measures distinct. |
| NOC — Defense Systems | 2,093 | Operating income 156; margin 7.5%, prior 12.7%; sales +5% while operating income -38% [NOC] | Increased demand and declining profitability can coexist. Other NOC segments also participate in relevant capabilities. |
| LHX — Missile Solutions | 1,054 | Margin 12.3%, prior 12.5%; sales +14% [LHX] | Growth in a relevant supplier segment is not proof of margin expansion, stock mispricing, or immediate cash realization. |

A next-generation dossier must join these concepts to specific products and contracts without double counting prime/supplier values or manufacturing missing program margins. No segment-to-company ratio is admitted here as a missile-purity estimate. No valuation, consensus surprise, expected return, or current entry is established by these quarterly figures.

## 5. Real canonical-extractor probe and its limitations

The existing `engine.fundamental_forensics.disclosure_diff.normalize_filing` and `engine.earnings_release.figures.extract_release_figures` were executed, unmodified, against captured raw issuer-page HTML for LMT, RTX and LHX. Each yielded zero bound figures and explicit absences (including missing basis, units, currency or period). Thus the existing strict extractor cannot simply be assumed to consume those raw web layouts successfully. This is a bounded input-compatibility result, not a claim that all earnings extraction is broken: the probe did not exercise the full SEC filing/exhibit acquisition path or every supported document format.

Native NOC HTML acquisition returned 403. No proxy, alternate-header loop or source bypass was used. Its financial facts above were verified in the official SEC document through the browser research tool; no native raw-body or span-replay proof is claimed for it.

Captured raw-body SHA-256 values:

- LMT: `727c9c73b15aaa5a706361d1be5193afc17e942485cc1fd664bcc84cea72e36e` (412,469 bytes).
- RTX: `76bbd7c56e5e089c3255983a45b3ec3e5e3d92d10ea46c93675291b33a64f706` (280,122 bytes).
- LHX: `ad8fb2daf23d9c6e4499c5317255a2681f7049d9a36d769db034911fc16132fa` (449,575 bytes).

Research scratch, not a canonical runtime store: retained #7186 workspace `.pytest-local/defense-financial-qualification/`, containing raw captures, strict-extractor outputs, acquisition receipts, and actual company-wire read receipts. Raw release bodies were not copied into GitHub. Do not mistake scratch availability for an accepted source adapter or production rights/admission.

## 6. Required owner contract and implementation order

**Authority precedence:** Executive for runtime/admission; Agent OS for workstream continuity; each financial/event/market/theme owner for its truth; GitHub for source/proof; Linear projection; Slack transport. This research provides evidence, not a worker assignment. Sol retains Defense integration and acceptance responsibility.

**Non-goals:** no replacement Company Intelligence, earnings/transcript/SEC store, program graph, market feed, tenant system, scorer, queue or Prophet; no arbitrary confidence score; no display-to-trade permission flip; no rewriting past forecasts; no broad rerun or host/CI intervention.

**First owner action:** trace the exact four live event IDs back to the canonical history inputs and current generation manifest. Distinguish bad extraction, lost basis metadata, stale event selection and stale publication. Correct the owner at the proven boundary and preserve original evidence/correction history; never patch Government Revenue with a ticker-specific financial number.

**Second action:** use the existing release/document/span and company-event owners to carry a typed economic measure. Required meaning includes concept, issuer/segment/program scope, reporting/adjustment basis, period and comparison-period basis, units/currency, point-in-time source availability and correction lineage. A generic `earnings_history` label is not sufficient. Missing dimensions remain unknown and non-comparable, never inferred from a favorable percentage. Quarterly and year-to-date figures must not collide merely because their period end matches.

**Third action:** extend the existing D4 bridge to the admitted Defense cohort only after this owner contract is sound. Show company context beside procurement facts, the exact program/role, what changes cash economics, and what is still missing. Keep comparison closed when the denominator, accounting meaning or information time is incompatible. The viewer should see an explanation of uncertainty, not silent disappearance or a fabricated ratio.

**Fourth action:** link the reviewed munitions program/role expansion through the existing D5 curator and dossier consumer, and compose the existing thematic/market owner context. Determine recognition and valuation separately from factual company growth. A market leader is not automatically an unpriced opportunity; a laggard is not automatically a catch-up trade.

### Acceptance and failure behavior

The regression set must include the four live cases, same-period GAAP-versus-adjusted pairs, organic versus reported revenue, gross versus segment/consolidated operating margin, fiscal-quarter versus year-to-date collisions, a newer report with an older generated wrapper, absent values, contradictory values, source corrections, and zero/no-program-coverage controls.

Deterministic code owns identifiers, units, basis, period joins, arithmetic and refusals. Models may explain evidence and propose hypotheses but may not select a basis or invent a number to make a thesis work. The owner must produce an exact source/span replay and correction-safe packet; the real entitled Defense consumer and bounded machine tool must render the same generation and caveats. UI negative/stale/corrected states are part of proof. Source tests or a fixtures-only browser are not production acceptance.

Stop an implementation lane on unresolved ownership, unsupported source rights, ambiguous prior effects, missing runtime admission, or incompatible financial meaning. Do not let a blocked optional source hold unrelated accepted-source research hostage. The exact next financial action is the four-event owner-boundary trace, not another broad Defense audit.

## 7. Relationship to current publication repair

#7186 remains the separate DI-R0 repair at `f1682c0e72ed6b7bfbb240831d93019f59174cbc`; its local full-builder/API proof is preserved. This financial qualification does not widen that PR. Its release currently awaits actual CI: the three organization ci-linux runners were observed offline and twelve packs queued. The Windows device read could not execute; a bounded SSH read timed out. These observations were routed as source intake to the existing Runner Fleet incident #6351, not used to create a second healer or modify labels, services, admission, memory envelopes or workflow routes. Vercel's separate failure and entitled production proof remain unresolved.

## Primary sources

[LMT] https://news.lockheedmartin.com/2026-07-23-Lockheed-Martin-Reports-Second-Quarter-2026-Financial-Results

[RTX] https://www.rtx.com/news/news-center/2026/07/23/rtx-reports-q2-2026-results

[NOC] https://www.sec.gov/Archives/edgar/data/1133421/000113342126000033/noc-06302026xearningsrelea.htm

[LHX] https://investors.l3harris.com/news/news-details/2026/L3Harris-Technologies-Reports-Robust-Second-Quarter-2026-Results/default.aspx

## September 19 owner-boundary resolution

The four qualification defects above are still present in the live
`/api/company-intelligence/{ticker}` responses. The intervening producer is not dead:
the scheduled Company Intelligence lane continues to complete and promote immutable R2
generations. The defect is upstream and structural.

### Exact source chain

The live Company Intelligence root marker currently points at generation
`ffd6797aef39d75064a35ab0`, whose source manifest names an earnings generation and
50,982 history rows. The current earnings root marker has continued advancing score
generations, but its immutable `history.parquet` remains:

- 50,982 rows / 3,529 tickers;
- latest call date **2026-07-31**;
- MD5 `440447335f37a51419937dba493b3168`;
- source `equitydesk_backfill/delta_2026-07-31/earnings_call_data.json`;
- source update max **2026-08-01 08:08:38.565289+00:00**.

By contrast, the same manifest's score plane has continued through September 2026. The
Windows/Terminal earnings worker confirms this is intentional current architecture: it hydrates the
existing R2 generation, scores new transcript bodies, upserts `scores.parquet`, and republishes.
It does **not** append quantitative rows to `history.parquet`.

Reading the exact immutable history object reproduces the four Defense problems at the source:

| Ticker | Last relevant legacy history row | What the row means for Defense |
|---|---|---|
| LMT | FY2026 Q2: revenue_growth 11; gross_margin 10.8 | 10.8 is already mislabeled upstream relative to the issuer's segment operating-margin disclosure |
| RTX | FY2026 Q2: revenue_growth 16; eps_growth 21 | basis is generic in the legacy row; issuer basis is organic/adjusted |
| NOC | FY2026 Q2: revenue_growth 5; eps_growth 8 | comparison basis needed to reconcile reported GAAP EPS is absent |
| LHX | FY2026 Q1 is latest | FY2026 Q2 is absent from the immutable history entirely |

This means `engine/company_intelligence/views.py` is not inventing the bad values; it is faithfully
projecting generic legacy columns. A downstream rename or hard-coded override would conceal the
source defect and create a second financial truth.

### Existing owner capability is insufficient for a direct swap

The accepted Earnings `event_workspace.v1` route is not a general four-company escape hatch:
production requests for LMT, RTX, NOC and LHX all return
`event_workspace_not_covered`.

The Financial Intelligence Fabric is the correct long-term filing-semantic owner, but its Agent OS
record still says production attested issuer service is **NOT_BUILT**. FIF-3 remains in progress,
with golden AAPL statement/query slices proven; it explicitly forbids calling those fixtures
production issuer coverage.

The older committed SEC quarterly table is useful as a research cross-check but is also not a
current product solution: its current extraction for these names stops at FY2026 Q1, while the
separate EPS quarterly artifact has Q2 availability rows. Defense must not compose those stores
into a new canonical financial service.

### Defense V1 ruling

For the first investor-loop dossier:

1. use official issuer/SEC facts with explicit period, accounting basis, units, source and
   publication/known-at clock as a bounded **research bridge**;
2. preserve missing current-quarter facts instead of falling back to generic legacy labels;
3. keep procurement economics as scenarios/ranges until company attribution and margin evidence
   exist;
4. consume Earnings/FIF production facts when those owners generalize—never fork their semantic
   models;
5. no valuation/asymmetry conclusion may be labeled supported when the financial denominator came
   from the stale generic history fields.

The cross-session landmine is recorded as
`DSC:EARNINGS-HISTORY-FROZEN-WHILE-SCORES-ADVANCE`.
