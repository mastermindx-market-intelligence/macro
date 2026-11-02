# F1 claim / evidence / denominator matrix — News Intelligence Estate (2026-10-31)

BASE (HEAD): 19c31737672217939906b3861682e40de57d2395 (branch `lane/news-w3-f1-matrix-r3`, clean tree)
RUN_ID: NEWS-W3-F1-MATRIX (Fabric review-grade worker, glm-5.3, under seat 602cd180)
PACKAGE: MASTERPLAN §7.F F1 — "Maintain a claim/evidence/denominator matrix for all promised
capabilities; Source, merge, installation, authenticated path and acceptance remain separate
columns" (MASTERPLAN.md:386).

## Scope and method

Records only. Every cell below is a `path:line` at HEAD `19c31737672`, a `PR -> sha` as
recorded in a committed record named beside it, or the literal NONE. No cell is filled from
a plan, design or commission promise; no rung is inferred from a lower one.

Inputs read first (STEP 1):

- `research/news_intelligence_estate_20261021/MASTERPLAN.md` — §2.1 (capability/owner map,
  lines 72-93), §7 (work-package catalogue, 328-391), §9 (end-to-end acceptance, 465-523),
  §10 (incumbent carrier and hold register, 525-558), §12 (definition of complete, 589-608).
- `agentos/handoffs/NEWS-INTELLIGENCE-ESTATE-2026-10-31-FABLE-TAKEOVER.md` (all five writes;
  every PR -> sha, review verdict and unresolved item cited below by line).
- `agentos/workstreams/WS-NEWS-INTELLIGENCE-ESTATE-CONVERGENCE.md` (78 lines).
- The estate artifacts on main under `research/news_intelligence_estate_20261021/`:
  A1_SOURCE_DELIVERY_MATRIX.md, A5_TRANSPORT_OBSERVABILITY_GAPS.md, B1_SCHEMA_INVENTORY.md,
  D1_NEWS_INPUT_TRACE.md, B4_PROVENANCE_ADJUDICATION.md, B4_V3_NEW_CASE_ROUTING.md,
  B4_SAMPLER_STARTUP_NOTE.md, QUANT_CLAIM_MATRIX.md, C1_EXPOSURE_JOIN_CENSUS.md,
  C3_F05_CONSEQUENCE_DELIVERY_CENSUS.md — each quoted by its own verdict/summary line in
  §"What the 2026-10-31 estate artifacts prove and do not" below; no count was re-derived.
- `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`
  (cited as F00C) and `MARKET_ONTOLOGY_F04_EXACT_CAPABILITY_CLOSURE_MAP_2026-09-04.md`
  (cited as F04MAP) — committed MarketOntology programme records for the F02/F04 segments.

Greps run (STEP 2, receipt search; file lists and lines retained at
`~/lanes/tmp/news-w3-f1-matrix-r3/`):

- `grep -rln -E "PRODUCTION_PROOF|PROVEN_LIVE|authenticated|deploy(ed|ment) receipt|installed"
  research/news_intelligence_estate_20261021 agentos/handoffs/NEWS-INTELLIGENCE-ESTATE-2026-10-31-FABLE-TAKEOVER.md
  agentos/workstreams/WS-NEWS-INTELLIGENCE-ESTATE-CONVERGENCE.md research/market_intelligence_productization`
  → 40 hit files (capped at 40 by the frozen `head -40`).
- The same pattern with `-rn` over the three estate-scope targets → 36 candidate lines
  (`receipts.txt`). A hit is a candidate only; a cell is filled only where the cited line
  itself states a dated receipt with its carrier (PR, deployment, run id or review id).
- `grep -n -E "#[0-9]{4,5}"` over the handoff → 37 PR-statement lines (`prs.txt`);
  verdict-pattern grep → 19 verdict lines (`verdicts.txt`).

Five-column rule (MASTERPLAN.md:386): source, merge, installation, authenticated path and
acceptance remain **separate columns**; MASTERPLAN.md:56 — "Source presence, unit tests, CI,
merge, installation, authenticated delivery and accepted product capability remain different
facts." Nine-rung ladder (CLAUDE.md, §Execution continuation law): `ACK -> QUEUED -> START ->
RUNNING -> DELIVERED -> CI -> MERGED -> PRODUCTION_PROOF -> ACCEPTANCE` — nine distinct
facts and none implies the next. A review verdict is not acceptance; a merge is not an
installation; a design is not a source.

The terminal and Mastermind repositories are not in this worktree. Their facts appear only
as committed records state them (path:line of the handoff, the workstream, the masterplan or
D1), labelled "as recorded"; no terminal/mastermind-side receipt was read for this matrix.

Strict case separation (binding, restated from the lane law and every B4 artifact): 600
registration cases / gated_v2 99 drawn of which 74 routed MATCH (scorable) / gated_v3 135
drawn / 40 NEW cases routing-pending / 0 prospective. The 135 drawn are not 135 scored or
gold cases. A shared group id does not transfer a label, a verdict or independence across
versions, assets, clocks or horizons.

## Capability matrix

18 rows in MASTERPLAN §2.1 order (MASTERPLAN.md:74-91). Column contents: SOURCE = committed
code/doc on main (path, or PR -> sha); MERGE = PR -> merge sha recorded in a committed
record (named beside it); INSTALLATION / AUTHENTICATED PATH / ACCEPTANCE = a committed
dated receipt with its carrier, else NONE. Path shorthand: artifacts by short name under
`research/news_intelligence_estate_20261021/`; HANDOFF =
`agentos/handoffs/NEWS-INTELLIGENCE-ESTATE-2026-10-31-FABLE-TAKEOVER.md`; WS =
`agentos/workstreams/WS-NEWS-INTELLIGENCE-ESTATE-CONVERGENCE.md`.

| # | Segment (§2.1) | SOURCE | MERGE | INSTALLATION | AUTHENTICATED PATH | ACCEPTANCE | Highest proven rung | Open obligation (§2.1 "Remaining obligation") |
|---|---|---|---|---|---|---|---|---|
| 1 | Shared ticker-news evidence (:74) | qbus news store on main; A1:17-18 (family A sole-writer rows, file:line at BASE 64ef5131); store read path C1:113 (J02, engine/qbus_news_store.py:1751-1830); deploy unit app/deploy/macro-ticker-news.service (A1:18) | Macro #9846 -> 1298ed4281362329c682a1f7c038b932e4ccbb64, #9942 -> 526ce826f0898d8724e79acf3a884f9cec6f3096 (MASTERPLAN:531-532); A1 refresh #10046 -> 603d98a5bbe2 (HANDOFF:63) | RETAINED production readback, dated, with carrier: "RETAINED 2026-10-20 #9846: one writer PID 3227108, zero disconnects/failed catch-ups"; delivering per "RETAINED 2026-10-21 #9942" (A1:18; retained-receipt rule A1:5, MASTERPLAN:56) | NONE | NONE | MERGED (+ retained 2026-10-20/21 live-ingest receipts; no PRODUCTION_PROOF claimed anywhere — HANDOFF:114) | "Current source health and coverage census; prove corrections and rights changes through every intended consumer" (:74) |
| 2 | Authenticated ticker delivery (:75) | /api/ticker-news read path on main with NewsReadRights gate (app/ticker_news.py:583, D1:37); consumers incl. Terminal BFF and Macro panels (A1:139, :165); BFF itself in terminal repo (not in worktree) | Terminal #1094 -> d9ec4d2b86e9e9e0129d7fcd4c646f25f7670c49 (MASTERPLAN:533, as recorded); R2 rail #1111 -> 58c44ed9d6c1, #1110 -> ca8347f8230c, #1128 -> c78b705d56e8 (D1:241, as recorded) | #1094 09:20 deployment receipt (MASTERPLAN:533, as recorded; terminal repo not in worktree) | #1094 09:42 authenticated source-filter/reload proof (MASTERPLAN:533; §2.1:75 "now receipted", as recorded) | NONE | MERGED, plus retained installation + one authenticated journey for the source-filter/reload slice; "partially live-proven" (MASTERPLAN:78); no committed record claims PRODUCTION_PROOF | "Retain accepted frontend proof; close article-class quality follow-up #9963, natural grouped-detail/correction proof and generated Macro page proof" (:75) |
| 3 | Editorial quality (:76) | curated-predicate backend on main (#9942 backend curation merged, MASTERPLAN:531; editorial-eligibility split MASTERPLAN:101-104) | #9942 -> 526ce826f0898d8724e79acf3a884f9cec6f3096 (MASTERPLAN:531); repair #9963 open Ready at d19374c3dc8d599d92ec7c42259ec5ed22ec00e6, NOT merged (MASTERPLAN:534) | "delivering (RETAINED 2026-10-21 #9942: Benzinga 7,015 raw / 6,922 editorially admitted)" (A1:18; 08:40 observation MASTERPLAN:101, as recorded) | NONE — §2.1:76 references an "authenticated acceptance" exposing Benzinga article-class gaps, but that line carries no dated receipt; the dated 09:42 proof is #1094's (MASTERPLAN:533) | NONE | MERGED | "Finish original #9963 CI/release/fresh live acceptance; measure factual recall, false exclusion and concentration" (:76) |
| 4 | Macro News cockpit (:77) | NONE — source on open PR #9612 head 3a663ae70ecbd8a4130de9c95dbb6d940d181e04, source/fixture proof only (MASTERPLAN:536, §2.1:77); Sol CEO writes live on it, read-only here (WS:31) | NONE (#9612 open, MASTERPLAN:536) | NONE | NONE | NONE | none proven on main (open PR; nothing of this segment is at HEAD) | "Recover same reviewer through #1661 dependency, reconcile original branch, qualify exact CI/review/release and installed signed-in journey" (:77) |
| 5 | Terminal News sidebar (:78) | NONE in this worktree — sidebar rail lives on terminal Draft #1081 head a10657ee8eaa0aa12c98e2ba5563a8680bfb9c9b (MASTERPLAN:535; terminal repo not in worktree) | NONE for the sidebar (#1081 Draft, MASTERPLAN:535); shared-file #1094 -> d9ec4d2b merged (MASTERPLAN:533/:78, as recorded) | as recorded: #1094 deployed 09:20 (MASTERPLAN:533) — covers shared curation/details files, not the sidebar rail; the rail itself is uninstalled | NONE | NONE | none for the sidebar itself (its carrier is a Draft) | "Preserve #1094 proof and reconcile #1081 shared files, then qualify the new sidebar independently of Brief" (:78) |
| 6 | Shared Brief mode (:79) | NONE — design only (§2.1:79; E4 build forbidden before bindings, MASTERPLAN:379) | NONE | NONE | NONE | NONE | none (no source exists) | "Bind existing runtime/artifact/budget owners, run evaluation, build endpoint before UI, prove zero-demand and correction behaviour" (:79) |
| 7 | Legacy News Delta Desk (:80) | on main: engine/news_events.py + engine/news_event_ledger.py (B1 F3, B1:17); J07 enrich_with_qbus C1:118; J24 keep-FIRST event log C1:175 | NONE — predates the estate waves; no PR -> sha recorded in HANDOFF | NONE | NONE | NONE | MERGED by presence on main at HEAD (no PR -> sha recorded) | "Reconcile semantic and correction limits with qbus revisions; inspect current forward dataset and promotion state" (:80) |
| 8 | Macro release interpretation (:81) | engine/macro_surprise.py on main (B1:20 F6; §2.1:81 post-print cards, latest-revised FRED, explicitly not first-print/consensus truth) | NONE recorded | NONE | NONE | NONE | MERGED by presence on main | "Keep labels honest and link to accepted release/expectation owners" (:81) |
| 9 | Macro Release Intelligence (:82) | separate programme on main; MRI named as incumbent expectation/value owner (MASTERPLAN:82; B2 row MASTERPLAN:347) | NONE recorded in HANDOFF | NONE | NONE | NONE | source exists (separate programme); no estate-wave merge receipt | "Reuse; qualify exact current artifacts, benchmark clocks, target definitions and news-consumer joins" (:82) |
| 10 | Prophet News Impact (:83) | engine/news_impact/ on main; owned by WS:PROPHET-NEWS-IMPACT, consumed never redrawn (WS:33); B4 artifacts committed at HEAD (below) | #10338 -> cde8601b443 (WS:43; commit cde8601b443 on main at HEAD) — adjudication records only; benchmark PR #10063 head 01f9e0a50f17 stays open/untouched (HANDOFF:79, :96) | NONE | NONE | NONE | MERGED (adjudication records); QUANT CLAIM VERDICT: DEFENSIBLE_NEGATIVE (QUANT_CLAIM_MATRIX.md:140) — no engine influence claimable | "Complete measured corpus/adjudication and native consumer integration; honour B4 and existing scientific holds" (:83) |
| 11 | Sector/theme news context (:84) | engine/news_flow.py + engine/foresight_earliness.py on main (D1:31-38 T1.x hops, AUTHORITY class per hop; C1:139 J14, J15) | NONE recorded | NONE | NONE | NONE | MERGED by presence on main | "Trace actual influence and accepted semantics; improve event specificity and independent-source accounting through current owners" (:84) |
| 12 | GMI and company exposures (:85) | engine/company_theme_exposure/ + theme_graph + market_ontology on main (C1:141 J16, C1:142 J17, J18-J23); none reads a news object (C1:268 GAP-8) | NONE recorded | NONE | NONE | NONE | MERGED by presence on main | "Bind event evidence to dated entity/product/theme relationships; no second graph or expectation store" (:85) |
| 13 | MarketOntology F02 (:86) | engine/policy_intent_desk.py, engine/sanctions_map.py, engine/uk_policy_brain.py, engine/intl_risk.py et al. on main (F00C:14-19 real_producer column; MASTERPLAN:86) | F02 slices recorded in the committed F00C ledger: #6899 base+OFAC (F00C:14), #8300 -> 3565430d3cb6 (F00C:16), #8267 -> ed6a86133288 (F00C:19), #8307 -> 05bd9aac513a (F00C:18) | dated served receipts (historical): sanctions_map.html LIVE 2026-09-19T00:58Z (F00C:14, "anonymous /usr/bin/curl, page served unlocked"); policy_watch.html GET 200 live-proven 2026-09-19 (F00C:17); covering render 37105009906 SUCCESS 2026-10-03 09:57:28Z + served reads 10:09:16Z by served_proof_8300.sh (F00C:16, :18) | NONE — every F00C receipt is an anonymous public read (F00C:14) | historical, narrow-slice acceptance-closure statements by the programme owner: "Acceptance closed for base+OFAC" (F00C:14), "Lifecycle acceptance closed" (F00C:15, :17), "Acceptance met" (F00C:17); freshness not established (MASTERPLAN:62) | PRODUCTION_PROOF historical for one row: MO-PAID-008, "PRODUCTION_PROOF 2026-10-03 (CEO A D77)" (F00C:18); seven of ten rows PROVEN_LIVE (F00C:14-20), three NOT_BUILT rights-held (F00C:21-23) | "Extend actual coverage only after source rights/identity checks; preserve unbuilt rights-held military/AIS/satellite exclusions" (:86) |
| 14 | MarketOntology F04 (:87) | theme graph / TXI / exposure composer on main (C1:142 J17, J18); compose_exposure_map has zero production callers (C1:262 GAP-2) | NONE for the integration candidate #9639 (open at 3f7db3f22f4e7fea40dd49a2981b264072f82c8b, MASTERPLAN:543); historical "MO-PAID-016 PARTIAL — WTI/TXI vertical PROVEN_LIVE" (F04MAP:181) | NONE | NONE | NONE | source on main; the nine-capability denominator remains open (F04MAP:9, :11); X1 held pending repair (F04MAP:22-24) | "Current native admission, history/purpose qualification, actual installation and authenticated journey; calibrated opportunity remains separately gated" (:87) |
| 15 | MarketOntology F05 (:88) | engine/chronicle/ chain on main: spine.py:85/:202 -> impact.py:464/:1012 -> build_site.py:7676-7680 -> news.html.j2:1061 (C3:32-40 "Delivery chain at HEAD") | #8775 per-family source merged at 9ebe0fe08812 with impact.py/templates/tests/receipt (C3:323, as recorded in the committed census) | NONE as a receipt — the rendered page itself is committed (site/news.html tracked at HEAD carrying #nxConsequence, window "Events from 23 Oct to 30 Oct 2026", C3:325), but no committed receipt checks it (GAP-RECEIPT, C3:326; HANDOFF:200-202) | NONE | NONE — "Glance accepted" is asserted at MASTERPLAN:88 without a dated receipt; "covering-render proof still owed" reconciled as a real debt (C3:324) | MERGED (#8775 -> 9ebe0fe08812; nightly render path C3:39) | "Reconcile actual served state, preserve family counts and correction history; causal/ranked implications remain gated" (:88) |
| 16 | Mastermind tools and assessments (:89) | brain/bot_mcp.py get_news/get_intelligence + portfolio/lenses.py at Mastermind master bb85b429 (D1:231-239 pointers, as recorded; mastermind repo not in worktree); macro engine/intelligence.py on main (B1:21 F7) | Mastermind #1897 (D2 consumer-freshness half) MERGED via merge queue -> master 3b7e002a (WS:53, as recorded in the workstream) | NONE (no deployed-Mastermind-runtime receipt in scope) | NONE | NONE | MERGED (consumer half) | "Introduce richer source-qualified research context through existing consumer seams; preserve provenance, corrections and authority" (:89); MMREV-03 producer follow-on open (HANDOFF:81) |
| 17 | Integrated answer / Brain (:90) | app/integrated_answer.py + engine/intelligence.py on main (B1:21 F7; MASTERPLAN:90) | #8596 and #8811 recorded merged at MASTERPLAN:90, but no merge sha is recorded in HANDOFF — counted NONE under the PR -> sha rule | NONE | NONE | NONE | MERGED by presence on main | "Reconcile current live and per-leg acceptance; attach qualified news by reference; do not create another answer warehouse" (:90) |
| 18 | Editorial/media intelligence (:91) | NONE — Intelligence Desk/Suite + Press read adapter named at MASTERPLAN:91 without macro-main paths; separate derived editorial workflow | NONE | NONE | NONE | NONE | none proven | "Share admissible evidence; editorial ranking and draft eligibility must not become market-signal authority" (:91) |

Reading notes. (a) "MERGED by presence on main" is the merge fact proven by the file being
at HEAD; it is weaker than a recorded PR -> sha and claims nothing higher. (b) Every F00C
(F02) receipt is historical (2026-09-19 / 2026-10-03) and anonymous; MASTERPLAN:62 — "An old
'PROVEN_LIVE' receipt cannot establish today's freshness." (c) The retained #9846/#9942
receipts are owner receipts read from merged PR bodies, "never a claim about the present"
(A1:5).

## Closure-criteria matrix

MASTERPLAN §12 (lines 595-604), one row per numbered criterion. Status vocabulary: MET /
PARTIAL / NOT MET / NOT MEASURABLE AT HEAD.

| # | Criterion (§12) | Evidence at HEAD | Status | One-line reason |
|---|---|---|---|---|
| 1 | Declared source/event/market coverage measured and honestly displayed (:595) | A1:5 (honesty rule), A1:17-21 (matrix rows); #10046 -> 603d98a5bbe2 (HANDOFF:63); live health census owed (MASTERPLAN:58) | PARTIAL | A1 committed with explicit no-live-probe honesty; the live source-by-source health census is still execution work (MASTERPLAN:58). |
| 2 | Source observations, independent evidence, revisions and current views reconcile (:596) | A3 propagation tests #10044 -> 87d7158af405 (HANDOFF:63); B1 join ruling DEC:NEWS-ESTATE-B1-JOINS (HANDOFF:27-31); natural grouping unproven (MASTERPLAN:99) | PARTIAL | Propagation tests merged and joins ruled, but "no natural fuzzy cross-publisher join was observed" (MASTERPLAN:99). |
| 3 | Macro, Terminal and Mastermind consume the same qualified facts through existing owners (:597) | D2 producer #10280 -> 5b3c2e05498c (HANDOFF:66); Mastermind #1897 -> master 3b7e002a (WS:53); "A source merge ... is not installed or production proof" (D1:241) | PARTIAL | Producer and consumer halves are merged; installed/production equality across the three repos is unproven. |
| 4 | Ticker, theme and MarketOntology implications source-backed, time-valid and appropriately conditional (:598) | C1:261 (GAP-1), C1:221-222 | NOT MET | The committed census proves no existing join takes a news object to a dated company/theme exposure (C1:261; "Of the YES joins, NONE takes a news object as input", C1:222). |
| 5 | Quantitative comparisons use admitted actuals, expectations, units, periods and vintages (:599) | B1 vocabulary #10049 -> 8ecd470152ee (HANDOFF:63); B2 adapter is a bounded outcome not built (MASTERPLAN:347) | NOT MET | The schema vocabulary is committed, but no admitted quantitative comparison exists in use; the B2 adapter is unbuilt. |
| 6 | Existing releases and authenticated user/machine journeys are proven (:600) | #1094 09:20 deployment + 09:42 authenticated proof (MASTERPLAN:533, as recorded); Journey 6 terminal #1196 -> master 7f1fdafe MERGED, "PRODUCTION_PROOF not claimed (real sign-in = human gate)" (HANDOFF:154-156); #9963 fresh signed-in acceptance owed (MASTERPLAN:534) | PARTIAL | One retained authenticated journey (#1094 slice) and one merged rail; real sign-in and the #9963 fresh acceptance remain unproven. |
| 7 | Briefs and other AI work have real admission, reuse, correction-safe publication and measured cost (:601) | MASTERPLAN:79 (design only), MASTERPLAN:379 (E4) | NOT MET | Brief is design only; E4 build is forbidden before concrete job/artifact/budget bindings. |
| 8 | Quantitative research reaches a justified accepted result; engine influence has its own scoped permission and evidence (:602) | QUANT_CLAIM_MATRIX.md:140 (VERDICT), :142 (0 committed system scores); accepted by artifact (HANDOFF:95) | PARTIAL | The claim adjudication is committed and accepted by artifact as DEFENSIBLE_NEGATIVE, but the section-11 evaluation itself has 0 committed system scores; no engine influence is claimed or permitted. |
| 9 | Degraded states, revocations, corrections and recovery leave no stale claims or duplicate effects (:603) | A3 tests #10044 -> 87d7158af405 (HANDOFF:63); A5:24 (all six modes partial, 9 gaps); controlled fault recovery (F4, MASTERPLAN:389) not run | PARTIAL | Propagation tests merged and the observability gap inventory committed; no controlled fault-recovery observation exists. |
| 10 | Fable's independent audit accepts the actual capability matrix and existing durable records reflect it (:604) | this file (the F1 matrix) at this HEAD; F2 review package (MASTERPLAN:387) not run | NOT MET | The capability matrix is written by this commit; the independent F2 adversarial review and Fable's acceptance of the matrix have not happened. |

## Denominator

Segments (n of 18, reconciling to the capability matrix row numbers):

- With SOURCE evidence: **14 of 18** (rows 1, 2, 3, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
  17). Without: rows 4, 5, 6, 18 (open PR, terminal Draft, design only, no macro-main path).
- With MERGE (a PR -> merge sha recorded in a committed record): **7 of 18** (rows 1, 2, 3,
  10, 13, 15, 16). Row 17's #8596/#8811 are recorded merged without shas (MASTERPLAN:90) and
  are counted NONE under the PR -> sha rule; rows 7-9, 11-12, 14 carry sources on main with
  no estate-wave PR -> sha.
- With INSTALLATION (a committed dated deployment/production receipt): **5 of 18** (rows 1,
  2, 3, 5, 13). Row 5's receipt covers #1094's shared files only, not the sidebar rail; row
  15's rendered page is a committed artifact, not a receipt (GAP-RECEIPT, C3:326).
- With AUTHENTICATED PATH (a committed receipt of a real signed-in user/machine journey):
  **1 of 18** (row 2: the #1094 09:42 source-filter/reload proof, MASTERPLAN:533, as
  recorded). Row 13's receipts are explicitly anonymous (F00C:14).
- With ACCEPTANCE (a committed independent non-author acceptance): **1 of 18** (row 13 —
  historical, narrow-slice programme-owner acceptance closures, F00C:14-17; freshness not
  established, MASTERPLAN:62). For the 2026-10-31 estate waves themselves: "Nothing is
  PRODUCTION_PROOF or ACCEPTED yet" (HANDOFF:114).

Closure criteria (n of 10, reconciling to the closure-criteria matrix): MET **0** / PARTIAL
**6** (criteria 1, 2, 3, 6, 8, 9) / NOT MET **4** (criteria 4, 5, 7, 10) / NOT MEASURABLE AT
HEAD **0**.

## What the 2026-10-31 estate artifacts prove and do not

- **A1_SOURCE_DELIVERY_MATRIX.md** — its own reading rule: "From the source tree alone this
  census can usually prove only `configured` / `admitted` / `intentionally excluded`;
  `delivering` or `degraded` is written **only** with a RETAINED receipt and its date"
  (A1:5). It proves the configured/admitted/excluded source matrix plus two dated retained
  production readbacks (A1:18); it does not prove present-tense delivery — "no provider,
  VPS, R2 or service was probed for this file" (A1:5).
- **A5_TRANSPORT_OBSERVABILITY_GAPS.md** — its own summary line: "Eight of nine gaps are
  single-file-or-two S-sized changes ...; Gap count: **9**. Bounded build proposals: **6**"
  (A5:24); all six failure-mode rows are "partial" (A5:15-24 table). It proves the
  observability gap inventory; it does not prove any gap closed.
- **B1_SCHEMA_INVENTORY.md** — "VERDICT: PASS" (B1:5), seven families F1-F7 inventoried
  (B1:14-21). It proves the schema vocabulary exists on main; it does not prove any join or
  comparison built on it.
- **D1_NEWS_INPUT_TRACE.md** — "VERDICT: PASS" (D1:6), every news input path traced hop by
  hop with one AUTHORITY class per hop (D1:9-12, :14-20). Its own boundary statements: the first
  real consumer is the Mastermind boundary (D1:231), and "A source merge of #1110/#1111/#1128
  is not installed or production proof" (D1:241). It proves input paths and their authority
  classes; it does not prove any installed or production journey.
- **B4_PROVENANCE_ADJUDICATION.md** — "PROVENANCE LABEL: RECONSTRUCTION" (B4_PROVENANCE:12);
  the original calendar is "**NOT FOUND.**" after hashing 2,272,098 local blobs
  (B4_PROVENANCE:56, :64); boundary counts "(a) 7, (b) 43, (c) 0, (d) 4, (e) 5"
  (B4_PROVENANCE:240). It proves the registered draw's provenance state; it draws no
  conclusion and changes nothing (B4_PROVENANCE:156-158).
- **B4_V3_NEW_CASE_ROUTING.md** — its own reconciliation: "40 = 31 MATCH + 4 NO_EVENT +
  3 OTHER_EVENT + 2 WRONG_ISSUER + 0 UNREADABLE_CARD" (B4_V3:34), "not gold labels ...
  `authority: context_only`" (B4_V3:103). It proves census routing verdicts for the 40 NEW
  cases; it does not score, label or make any case scorable.
- **B4_SAMPLER_STARTUP_NOTE.md** — strict-separation line at B4_SAMPLER:11; the pinned
  behaviour "56 passed in 1.01s (12 + 44)" (B4_SAMPLER:161-164) with a discrimination proof
  that fails against an admit-first mutant (B4_SAMPLER:166-178). It proves the sampler
  share-cap semantics as registered; it touches no engine file (the pinned commit law).
- **QUANT_CLAIM_MATRIX.md** — "QUANT CLAIM VERDICT: DEFENSIBLE_NEGATIVE" (QUANT:140),
  because "`P/section11/` at HEAD contains exactly `README.md` + `registration.json`: 0
  committed system scores against v2_match under the registered gate" (QUANT:142). **The
  quantitative outcome is DEFENSIBLE_NEGATIVE and no engine influence is claimable**; the
  74 MATCH scorable population has nothing scored on it (QUANT:146), and any promotion
  reading waits for the owner's threshold reconciliation (QUANT:130-134).
- **C1_EXPOSURE_JOIN_CENSUS.md** — its own counts: "28 table rows — 21 functioning joins"
  (C1:186) and "**DATED counts: YES = 11 rows ...; NO = 7 ...; PARTIAL = 6 ...; n/a = 1**"
  (C1:221), with "Of the YES joins, NONE takes a news object as input" (C1:222) and GAP-1:
  "no dated news→theme join exists" (C1:261). **C1's dated YES/NO/PARTIAL counts are 11 / 7 /
  6 (+1 n/a)**; it proves the exposure-join inventory and the absence, not any new join.
- **C3_F05_CONSEQUENCE_DELIVERY_CENSUS.md** — its own counts line: "Counts: 10 RECONCILED
  (one as RECONCILED-ARTIFACT), 2 GAP (GAP-RECEIPT, GAP-COVERAGE), 0 CONTRADICTED"
  (C3:335-336). **C3's open gaps are GAP-RECEIPT** — "No committed receipt or proof document
  checks that served section's counts ... against the corpus" (C3:326; gap restated
  C3:343-349) — **and GAP-COVERAGE** — no committed receipt measures a retracted event's
  delivery on the served section (C3:331). The 127-citations-re-derived figure is the
  handoff's own summary of this census (HANDOFF:174-175 "127 citations re-derived"), not a
  line inside it; the census's own evidence line is "Every `path:line` citation re-derived
  by `sed -n` at HEAD" (C3:429).

## Open obligations by owner

Owner names are exactly as the masterplan/handoff/workstream state them.

| Obligation | Owner (as named) | Carrier | Evidence that would close it |
|---|---|---|---|
| F05 GAP-RECEIPT: a committed receipt checking the rendered #nxConsequence section against the Chronicle corpus of the same render (C3:326, HANDOFF:200-202) | the C3/F05 (Chronicle) owner; "this seat records the gap, mints nothing" (HANDOFF:201-202) | a committed receipt (none minted) | a dated receipt checking the served/rendered section's counts, six disclosures and empties against the current corpus (C3:343-349) |
| F05 GAP-COVERAGE: correction-history receipt (C3:331) | the C3/F05 (Chronicle) owner (HANDOFF:200-202) | a committed receipt | a committed receipt measuring a retracted event's delivery or omission on the served section (C3:331) |
| C2 — complete the selected #9639 F04 vertical through native source and authenticated consumer (MASTERPLAN:357); W3 rows C2/C4/C5 deliberately not launched (HANDOFF:203-204) | their incumbent owners (HANDOFF:204); #9639 incumbent carrier per MASTERPLAN:543 | macro PR #9639 (open at 3f7db3f22f4e7fea40dd49a2981b264072f82c8b) | exact company/date/rights proof, installed source-at-import, protected release, authenticated F04 journey (MASTERPLAN:357, :543) |
| C4 — extend policy/geographic lifecycle coverage through F02 owners (MASTERPLAN:359) | F02 owners (MASTERPLAN:359; HANDOFF:203-204) | F02 owner records/PRs | primary legal/business stage + effective dates through existing owners; rights-held military/AIS/satellite exclusions preserved (MASTERPLAN:86, :359) |
| C5 — integrate sourced peer/sector consequences with Catalyst and rotation owners (MASTERPLAN:360) | Catalyst and rotation owners under #9616/#9507 holds (MASTERPLAN:360) | owner PRs (held) | source-backed consequence integration respecting the holds; no calibrated-impact claim (MASTERPLAN:360) |
| E4 — Brief bindings before build (MASTERPLAN:379; §2.1:79) | this seat, W4 (WS:60-63; HANDOFF:161-163) | W4 package | concrete job/artifact/budget bindings, extractive baseline, frozen 60-100 bundle evaluation, permission-aware reuse, correction-safe publication (MASTERPLAN:379) |
| #9612 Macro News cockpit (MASTERPLAN:77, :536) | Sol CEO writes live on it (WS:31, read-only here); recovery comment 6310693622 (MASTERPLAN:536) | macro PR #9612 (open) + Mastermind #1661 dependency | same reviewer recovered through #1661, original branch reconciled, exact CI/review/release, installed signed-in journey (MASTERPLAN:77, :536) |
| #1081 Terminal sidebar (MASTERPLAN:78, :535) | Sol's carrier (E1 pointer posted once, HANDOFF:155) | terminal PR #1081 (Draft at a10657ee) | #1081/#1094 shared files reconciled, then the new sidebar qualified independently of Brief (MASTERPLAN:78) |
| #9963 editorial quality repair (MASTERPLAN:76, :534) | original carrier ticker-news-editorial-live-gap-20261021-c3 (MASTERPLAN:534) | macro PR #9963 (Ready at d19374c3) | exact required checks, ordinary backend rollout, fresh signed-in acceptance (MASTERPLAN:534) |
| Mastermind #1661 — E2 dependency (MASTERPLAN:537) | incumbent (MASTERPLAN:537) | Mastermind PR #1661 (Ready at 9188c6ab) | exact source/security qualification, protected release, immutable runtime rollout, original reviewer reconciliation (MASTERPLAN:537) |
| MMREV-03 + CI registration of tests/test_news_llm.py (HANDOFF:81-82) | the next Macro producer lane (HANDOFF:82) | producer PR | bundled intelligence file news-leg source_asof; the P1D test registered in a CI run line (HANDOFF:81) |
| §9.1 seven vertical proofs (MASTERPLAN:469-477, correction-after-save at :481) | this seat, W4 (WS:60-63) | W4 proof packages | **none of the seven verticals has a committed proof at HEAD** — each needs a committed observed-behaviour proof on an ordinary authenticated path, incl. the correction arriving after a saved assessment (MASTERPLAN:481) |
| Production proof — a real signed-in session | human gate: "real sign-in = human gate" (HANDOFF:156); UNPROVEN by design in proof-r1: "real Supabase sign-in, production SSE delivery, cross-device persistence" (HANDOFF:151-153) | ORCH-4 rail (terminal #1196 merged) + a human-only control | a real production sign-in journey receipt — a human-only control this lane cannot perform |
| Terminal classic-pair-tag follow-up + mobile-ZH overlaps (HANDOFF:163-164) | open terminal follow-ups, "not this program's" (HANDOFF:164) | terminal carriers | out of this estate program; recorded here only so the matrix does not lose them |

## What this matrix is not

This matrix is **not an acceptance** of any segment, artifact or criterion — no cell
confers a rung, and a review verdict recorded in a cell is evidence of a review, never an
acceptance. It is **not a percentage-complete estimate** — MASTERPLAN.md:606: "Do not
substitute a percentage-complete estimate for this denominator." It is **not a release
decision** and not a HOLD/label action. It is **not a ranking or sizing authority**: no
signal, sizing, promotion or trading authority is created, widened or implied by anything
recorded here (QUANT:140 keeps the quantitative outcome DEFENSIBLE_NEGATIVE; no engine
influence is claimable). It records what committed evidence at HEAD proves, at HEAD
`19c31737672217939906b3861682e40de57d2395` only.

## Evidence

Commands run for this matrix (all at HEAD 19c31737672217939906b3861682e40de57d2395, clean
tree; scratch kept under `~/lanes/tmp/news-w3-f1-matrix-r3/`):

1. `git rev-parse HEAD` → 19c31737672217939906b3861682e40de57d2395;
   `git status --porcelain` → empty; `git branch --show-current` → lane/news-w3-f1-matrix-r3;
   `mkdir -p ~/lanes/tmp/news-w3-f1-matrix-r3`.
2. Reads (Read tool): MASTERPLAN.md offset 60-104 (§2.1 + §2.2 head), 326-393 (§7),
   463-560 (§9-§10), 588-611 (§12-§13 head); HANDOFF (all 204 lines); WS (all 78 lines);
   C1 head 1-60 + regions 186-232 + 258-270; C3 head 1-40 + 322-366 + 424-435; B1 head
   1-24; D1 head 1-23 + hop rows 31-38 + tail 230-243; A1 head 1-21 + section greps;
   A5 13-27; B4_PROVENANCE 1-30 + 136-166 + 238-240; B4_V3 1-24 + counts; B4_SAMPLER
   1-40 + 160-180; QUANT 1-20 + 130-150; F04MAP head 1-40 + greps.
3. `grep -n -E "#[0-9]{4,5}" agentos/handoffs/NEWS-INTELLIGENCE-ESTATE-2026-10-31-FABLE-TAKEOVER.md`
   → 37 lines (`~/lanes/tmp/news-w3-f1-matrix-r3/prs.txt`).
4. `grep -n -E "PASS_WITH_NOTES|PASS-WITH-GAPS|PASS_WITH_GAPS|DEFENSIBLE_NEGATIVE|PASS|FAIL|ACCEPT_WITH_NOTES|ACCEPT|REVISE|BLOCK" agentos/handoffs/NEWS-INTELLIGENCE-ESTATE-2026-10-31-FABLE-TAKEOVER.md`
   → 19 lines (`verdicts.txt`).
5. Receipt search (frozen): `grep -rln -E "PRODUCTION_PROOF|PROVEN_LIVE|authenticated|deploy(ed|ment) receipt|installed" research/news_intelligence_estate_20261021 agentos/handoffs/NEWS-INTELLIGENCE-ESTATE-2026-10-31-FABLE-TAKEOVER.md agentos/workstreams/WS-NEWS-INTELLIGENCE-ESTATE-CONVERGENCE.md research/market_intelligence_productization`
   → 40 files; same pattern `-rn` over the three estate targets → 36 lines
   (`receipts.txt`, each capped at 200 chars).
6. Targeted greps/`sed -n` for verdict and counts lines quoted above: C1:186/221/222/261-270;
   C3:32-40/322-336/338-354/424-435; QUANT:55/140/142-147; B4_PROVENANCE:12/31/51-56/64/136-158/240;
   B4_V3:3/7-12/18-24/34/103; B4_SAMPLER:11/13-40/161-176; A1:5/17-21/122/135/139/172-185;
   A5:13-24; B1:5/14-21; D1:6/31-38/231-243; MASTERPLAN:18-20/54-62/74-91/99-104/336-391/
   454/469-481/531-546/555/579-581/595-606; F00C:14-23 (+ header); F04MAP:7-11/22-24/181;
   WS:31-38/43/48/53/58/60-64; HANDOFF:27-46/63-102/111-164/167-204.
7. `git log --oneline -8` (confirm cde8601b443 [#10338] and 81f64c2ca15 [#10344] on main
   at HEAD; 19c31737672 = the #10347 records commit).
8. STEP 4 commit/push of this one file (see the return packet).
