---
key: CRYPTO-INTELLIGENCE
title: Governed crypto intelligence and decision presentation
objective: >
  Keep BTC Vector and adjacent crypto surfaces provenance-honest, with one
  declared authority for every decision-bearing output and advisory evidence
  unable to silently override it. Each wave is complete only at its separately
  authorized acceptance boundary.
status: active
program: crypto-intelligence
repos: [macro]
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: specified
waves:
  - id: P0A
    title: BTC Decision Authority Closure on Vector
    status: done
    pr: 6294
    note: >
      PROVEN_LIVE is durably closed. Sol accepted source head
      9ce6ce711602f6bb4986ed59ea84d70b704f3eac; release reconciliation head
      e573a341e406532748a9ba62e69e8c5444341630 passed exact-head CI, fence and
      authority workflows and PR #6294 merged at 2026-08-24T09:02:31Z as
      f039c86ae037cf75238cfdd1f3d732d9b643dbb7. PR #6395 then closed the stale
      organizational residue and separately commissioned P0B as merge
      0ee40fa28c64be0dc2a7d9f2e463bd68a70809ba. The accepted P0A live ruling is
      not reopened by P0B.
  - id: P0B
    title: Crypto H5 authority closure
    status: in_progress
    depends_on: [P0A]
    next_action: >
      Consume exact-head PR #8050 CI/fences for the H5 presentation/evidence head,
      then reconcile release ordering with open #7645 and regenerate site/crypto.html
      from the combined template source before any production acceptance. Prove the
      merged generated artifact on the real deployment path; do not alter canonical
      total-budget authority or the class split.
    note: >
      P0B remains BUILT_NOT_PROVEN at source head
      d079adb6d532b7af20a487bd0ebdeddc3a414ee0. It preserves the exact canonical
      cockpit receipt, now distinguishes a missing asset breakdown from an invalid
      total budget, and renders a valid zero without depending on class-model inputs.
      H5 uses source-specific bilingual failure explanations and a readable compact
      layout; shared styles and H1/H2 are unchanged. The existing source-claim gate
      caught an overstated Chinese validation sentence, which is corrected without
      changing the gate. Final proof and receipts are in the owning H5 decision.
next_action: >
  Keep PR #8050 as the H5 source/presentation carrier. Consume exact-head CI/fences,
  then coordinate merge ordering with #7645: its template patch auto-merges with H5,
  but site/crypto.html is a generated artifact with a pre-existing current-main
  conflict and must be regenerated after source reconciliation. After merge-order
  reconciliation, prove the combined production/deployed Crypto route and close P0B
  only if canonical happy/zero/unavailable behavior survives.
blocked_by:
  - >
    Exact-head PR #8050 CI/fences have not yet accepted the H5 presentation/evidence
    head. Local source, governance, generated-route and visual-evidence gates pass.
  - >
    Open #7645 remains an independent Crypto source carrier. Exact merge simulation
    shows templates/crypto.html.j2 auto-merges with H5 with zero conflict markers;
    site/crypto.html conflicts already between current main and #7645 and is a
    regenerated publication artifact. Release still needs source-order reconciliation,
    regeneration and real deployed-route proof.
owns_paths:
  - "engine/btc_decision.py"
  - "contracts/btc_decision.schema.json"
  - "scripts/build_vector.py"
  - "templates/vector.html.j2"
  - "tests/test_btc_decision.py"
  - "scripts/build_crypto.py"
  - "templates/crypto.html.j2"
  - "tests/test_crypto_wave2.py"
decisions:
  - "DEC:BTC-MIDTERM-BLACKOUT-AUTHORITY-RETIRED"
  - "DEC:CRYPTO-H5-BTC-BUDGET-AUTHORITY"
discoveries:
  - "DSC:CRYPTO-H5-BYPASSES-BTC-DECISION"
  - "DSC:PERSONAL-PRO-INGRESS-PRINCIPAL-GAP"
landmines:
  - >
    A direct H5 read of signals.alloc_optimal can produce the same happy-path
    number as btc.decision/v1 while still bypassing its integrity gates. P0B proof
    must include malformed and override cases, not only a 100% happy path.
  - >
    MAS-106 is the immutable failed original S0 experiment. The only authorized
    framed retry is MAS-112/S0-R1; do not reopen MAS-106 or create S0-R2.
  - >
    Historical bot U0BST4WG996 existed, but its then-active OAuth credential later
    crossed a model-visible app-settings boundary and is treated as compromised.
    Known bot identity is not current credential-safety proof.
  - >
    Private #sol-runtime C0BSGABKBFY now exists with Chris + ChatGPT1/2/3 only.
    Channel creation is topology preparation, not a Relay installation, C1 PASS,
    Executive admission or product execution claim.
  - >
    Executive G7 does not replace the Personal-Pro Slack admission sequence for Sol
    under the current protected Skillpack. Closed PR #6400 explored and rejected that
    bypass interpretation; do not revive it.
  - >
    Existing public #ceo-control-room C0BRDFZPLHK is not the frozen private B2/C2
    target. Do not use it for production modifying commands; reconcile that topology
    only after B2 is explicitly released.
  - >
    Economically meaningful raw/final allocation drift without an active named
    override is an integrity failure; only representation jitter is tolerated.
  - >
    The most-recent non-null prior allocation is continuity authority. Invalid,
    non-finite or out-of-range content fails closed instead of searching older rows.
  - >
    site/vector.html and site/crypto.html are regenerated publication artifacts.
    Reconcile their branch ownership against current main at release; never treat
    generated bytes as a second decision or organizational truth source.
  - >
    Slack tool availability, a merged autonomy-arm implementation or an Agent OS
    in_progress label is not Executive admission. A canonical Job receipt remains
    required before P0B can be called QUEUED or EXECUTING.
do_not_redo:
  - >
    Do not restore the retired midterm calendar veto or create a second
    allocation/override authority.
  - >
    Do not reopen P0A. PR #6294 and the accepted PROVEN_LIVE boundary are closed;
    P0B begins from that authority contract.
  - >
    Do not reopen Macro #6400. It was closed unmerged after rejecting a G7 bypass
    of Personal-Pro Slack admission. #6397 merged as the P0B runtime-gate
    reconcile; do not re-litigate that carrier.
  - >
    Do not reuse the exposed historical S0 bot credential or inspect Slack secret
    fields through model-visible browser/admin tooling.
  - >
    Do not use employee/ChatGPT Slack credentials as the C1 Relay, and do not bypass
    S0-R1/C1/B2/C2 through G7 local CLI, GitHub, Linear, MCP or another Slack action.
  - >
    Do not expand P0B into alerts, a new crypto optimizer, recommender removal,
    ETH/alt model promotion, navigation work or broader cockpit redesign.
  - >
    Do not bypass the Executive OS admission block by treating a Slack post,
    GitHub branch/issue, Linear assignment, merged G7 code or another carrier as a
    runtime Job.
artifacts:
  - agentos/handoffs/CRYPTO-INTELLIGENCE-2026-08-23-p0a-btc-decision.md
  - agentos/handoffs/CRYPTO-INTELLIGENCE-2026-08-24-p0a-close-p0b-commission.md
  - agentos/handoffs/CRYPTO-INTELLIGENCE-2026-08-24-p0b-runtime-gate.md
  - agentos/handoffs/CRYPTO-INTELLIGENCE-2026-08-25-personal-pro-ingress-unblock.md
  - agentos/decisions/DEC-CRYPTO-H5-BTC-BUDGET-AUTHORITY.md
  - agentos/discoveries/DSC-CRYPTO-H5-BYPASSES-BTC-DECISION.md
  - agentos/discoveries/DSC-PERSONAL-PRO-INGRESS-PRINCIPAL-GAP.md
  - research/CRYPTO_COCKPIT_MASTERPLAN.md
  - contracts/btc_decision.schema.json
  - verify_shots/p0a_btc_decision/
---

## P0A close

P0A is complete at its accepted production boundary. Its durable implementation
truth is PR #6294 plus merge commit
`f039c86ae037cf75238cfdd1f3d732d9b643dbb7`; PR #6395 separately reconciled the
Agent OS close and commissioned P0B. The accepted PROVEN_LIVE ruling is closed and
must not be re-litigated during P0B.

## P0B commission

P0B is separately commissioned and organizationally in progress. Its sole observable
mission is to make Crypto H5 honor the authority claim it already shows the user:
Bitcoin DecisionState sets the total crypto budget, while the existing class overlay
only splits that available budget among BTC, ETH and altcoins, with cash as the
residual.

The current defect is structural rather than visual. `scripts/build_crypto.py`
currently rereads `signals.alloc_optimal` for H5 total exposure. That bypasses the
P0A integrity projection, so an integrity-invalid state can make Vector unavailable
while H5 remains actionable. `DEC:CRYPTO-H5-BTC-BUDGET-AUTHORITY` freezes the repair
boundary; `DSC:CRYPTO-H5-BYPASSES-BTC-DECISION` records the falsifiable current-state
finding. Integrity-invalid or unavailable DecisionState must make H5 non-actionable.

## P0B runtime admission gate

Sol repeated the runtime gate against current protected Mastermind
`51f9942733b86e550bb9169d2a43462bd28e774f`. The compatible v1.0.0 Skillpack still
requires a production-proven Personal-Pro write path, a fresh `MMX/SOL_STATE_V1`,
exact grounding, expected Slack workspace/private CEO channel/sender, Relay READY +
reconciliation COMPLETE, Executive admission readiness and one-carrier binding. It
also states that `EXECOS/CEO_REQUEST_V1` may be used only after B2/C2 have proven it.

The connected Slack read recovered no fresh `MMX/SOL_STATE_V1`; `#ceo-control-room`
contains only the older Aug-20 operating/setup messages and no `#sol-runtime` channel
was discoverable from the current principal. Mastermind PR #146/G7 is now merged,
but its own proof contract explicitly leaves production host install/readiness/arm/
real-intent/disarm-rearm proof outstanding. Therefore G7 merge does not satisfy the
current P0B admission handshake.

No modifying CEO request was submitted. There is still no P0B `operation_key`,
`intent_id`, `job_id`, canonical Job status or dispatch receipt. This is a clean
refusal-before-submit, not an ambiguous modification.

## Current Executive admission predecessor

Current protected Personal-Pro law remains PR-A -> R0 -> B1 -> C1 plus independent
S0-R1 -> B2 -> C2. B1 is now implementation truth: Mastermind #106 merged as
`607a4e13cd78261ba60e4f6ffae2a8212c9074fa` and current-base B1 wrapper-hash repair
#114 merged as `00d15138eeea715fd833ba772518b06ce274a9b7`.

S0 V1/MAS-106 is an immutable `REJECTED_BY_DESIGN` experiment. MAS-112 owns the one
framed S0-R1 retry and is still `NOT_BUILT`. C1/MAS-109 owns production private
SOL_STATE read proof and has no implementation/proof PR. Sol has created its required
private four-seat `#sol-runtime` channel `C0BSGABKBFY`, but the dedicated Relay bot and
least-privilege host principal remain unproven.

Therefore P0B is blocked upstream before B2. No current Executive operation identity or
Job exists for P0B, and no Slack/Linear/GitHub projection may imply otherwise.


## 2026-09-27 P0B source execution supersession

Current protected Mastermind law `c01d890f6536539496f2d6744f3143ff49da296d` plus the Chairman's live continuation permitted this already-assigned, custody-clear source repair directly in the active Sol session. This supersedes only the historical claim above that P0B source implementation itself had to wait for a new Personal-Pro Executive/Slack runtime Job. It does not retroactively create such a Job, change Executive OS lifecycle truth, or waive any runtime/transport gate for work that actually requires those systems.

P0B source authority is now **BUILT_NOT_PROVEN** at `fc93f8e7eeec8c70b285191aa2374e88f71332c3`:
- the existing `btc.decision/v1` owner projects the only downstream total-budget value;
- `crypto.cockpit/v1` exposes that decision status/final exposure as an existing display receipt;
- `build_crypto` derives H5 total exposure only from the canonical projection;
- the existing BTC/ETH/alt class grid remains split-only;
- valid zero is distinct from unavailable; integrity-invalid state fails closed before Crypto page publication.

Local verification on the candidate: Crypto CI-owner tests **34 passed**; Vector CI-owner tests **95 passed**; Python compile and diff checks passed. These are local receipts, not exact-head GitHub acceptance.

Open #7645 owns the current Crypto template/publication bytes, so H5 unavailable-state UI integration and real browser acceptance remain fenced there. Do not touch #7645's template from this carrier and do not call P0B complete until that ownership is reconciled, exact-head checks pass, and the real generated H5 path proves valid-zero, unavailable/integrity-failure and happy-path states.


## 2026-09-27 current continuation

P0B source authority remains `BUILT_NOT_PROVEN` at local candidate `26fd88c7dad5448f69e6096037cf099d96d0c01e`. Additional adversarial tests now cover exact-budget conservation, named override final-vs-raw authority, stale decision dates and the fail-closed `project_budget()` projection. Combined Vector/Crypto authority regression pack: 147 passed locally.

The only user-facing P0B blocker is still template custody plus real-route proof: #7645 remains open and owns `templates/crypto.html.j2` / `site/crypto.html`. Do not edit those paths from PR #8050 while that carrier remains unreconciled. After custody clears, add the explicit H5 unavailable state and prove valid-zero, canonical-unavailable/integrity-failure and happy-path allocations in EN/ZH and both themes before accepting P0B.

## 2026-09-28 Market Board snapshot-integrity return

PR #8050's earlier `9e30dd81504da62b228fffd2cbf6306c57040da3` completed CI/fences successfully; no merge/live acceptance followed. New source `31a60448e058f09b5cea4795cb4bdcfc3f7cfcba` removes mixed-date ranking, retains older observations as exclusions, preserves unknown return coverage, and stops price-history leakage across snapshot dates or unqualified asset/source identities. It changes neither P0A/P0B allocation authority nor the provider store. Local proof: 182 regression tests, 64 semantic/browser cells, 32 canonical captures. The same-source combined fixture includes #7645's accessible table with zero source merge conflicts. See the current R2 decision and `mockups/evidence/crypto-universe-snapshot-20260928/` for exact input hashes and proof limits.

Parent remains in progress / BUILT_NOT_PROVEN on the deployed route. Next: consume the newly published exact-head CI/fences, follow source/release-order ownership with #7645 and regenerate/verify the actual deployed site. Do not redo the reviewed H5 or snapshot states; broader Crypto chart-led integration, floating Brain obstruction, native Paper qualification, review/alert integrations and participant comprehension remain unfinished.

## 2026-09-28 Chairman science commission and R1 result

The live Chairman instruction adds extensive scientific research on Crypto drivers, immediate risk transitions and multi-horizon pivots as a primary moat requirement within this same workstream. Sol completed a first source/data/temporal audit, with preregistration `47d4eacf6abd98055a085a779e9df75fee567d18`. See `research/CRYPTO_SCIENCE_R1_FINDINGS_AND_PROGRAMME_2026-09-28.md` and the current science frontier in `DEC-CRYPTO-VECTOR-R2-20260926.md`.

The incumbent bottom-pressure history fails prefix invariance on 3/366 declared dates; raw-allocation sensitivity is up to 5.3156 percentage points on one date per variant. A separate exploratory probe finds immature future-label tails counted as False. These are documented timing/evaluation defects, not new profitable strategies or live-trade verdicts. Original/amended diagnostic outputs and all cutoffs are preserved; input/source hashes remained unchanged. No production engine/config/data changed, and no new final-allocation authority was created.

Next scientific phase: reviewed temporal/label correction through existing owners, availability-qualified baseline replay, then preregistered fast-downside and washout/recovery experiments followed by trend/cycle work. Prior failed hypotheses and already-used historical holdouts remain explicit. Model promotion needs calibrated net utility, independent event evidence, realistic source/execution delays and fresh forward records—not decorative certainty or CI alone. Parent mission remains incomplete; no autonomous worker/watch cycle was started.

## 2026-09-28 science R2 correction/replay return

Source candidate a5a2d98cbb192f02113fc957fba28f40f37deff2 repairs higher-timeframe completion labels and immature impulse outcomes within existing engines. The original three-day grouping and all strategy/evaluator thresholds remain unchanged. Full stored-vintage paired replay completed:4393daily prefixes,54original bottom-pressure mismatches versus0corrected; only9of197columns changed. Original baseline matches stored principal columns exactly. Latest snapshot target unchanged; no live publication/gate/trade occurred.

Final local pack235passed with25existing warnings; source-claim/static/diff/replay checks pass. All55inputfiles,18existing data gates/ledgers and9source/config hashes remain unchanged. Evidence is in research/crypto_science/r2; interpretation and complete limitations in CRYPTO_SCIENCE_R2_TIMING_REPAIR_RESULTS_2026-09-28.md and current R2 decision frontier. No independent review or live-release acceptance is claimed.

The paired evaluator keeps D2/D3 demoted and U1 insufficient_n, consistent with the pre-existing stored gate; historical positive claims are not current predictive certification. Funding input selection is also identified:80recent first-column observations versus1089older observations in another field, with semantics not yet reconciled. Next: independent existing-owner timing review before release, then funding/source-time qualification and mature source-available cohorts before new fast-downside/recovery experiments. Parent scientific advantage and production mission remain incomplete.

## 2026-09-28 / R3 source identity and episode evidence

Within the same Chairman science commission, candidate cc5f0a2d16311db7639aba5f8f54ef6772a30374 protects the funding input against physical column-order changes and adds an opt-in nullable source-observed view to the existing radar. Current funding values and all default fire booleans remain unchanged; no live gate or allocation policy was switched. Legacy funding equivalence, settlement period and publication timing remain unresolved; old history was not spliced.

The plan was committed before new cohort outcomes at953eedfa53a5a201efebc03b74853316cad6a2cf. The complete diagnostic now retains48cohort scenarios and2090scenario-episode rows, not independent events. In reused2024+, zero-delay separated onsets yield D2:8/35, D3:2/18 andU1:1/8 hits under the unchanged +/-5% next-three-close target. Assumed delays and seven-day episode spacing are retained as sensitivities. A stronger comparison lift after removing unavailable source periods does not represent additional correct forecasts, and sparse bounce episodes do not support choosing the most favorable delay.

See research/CRYPTO_SCIENCE_R3_INPUT_COHORT_RESULTS_2026-09-28.md and research/crypto_science/r3/ for results, source/data/gate hashes, complete outcomes and actual test/evidence receipts. The fresh combined local pack passed247tests; independent review, source-time qualification and deployment remain owed. Next primary science unit is a frozen fast-downside and stabilization/reclaim experiment against the corrected incumbent with explicit latency/cost and episode rules. Current model authority, accepted UI work, reused-holdout designation and failed hypotheses remain intact. MISSION_COMPLETE:false; no worker, watcher, paid source or automatic continuation was started.

## 2026-09-28 R4: first frozen execution-aware sequence comparison

The existing science track completed hourly breakdown/shock and daily washout/reclaim hypotheses under protocol c458e016b094bbf28f6e4d89f5e622a56e92e697, research source f83e37e95d788f449ef3aa05d7f4e3b3e452671b. Report: research/CRYPTO_SCIENCE_R4_SEQUENCE_RESULTS_2026-09-28.md; complete initial/amended outputs and independent arithmetic under research/crypto_science/r4/. Production engine/config/data/gate/UI paths were not modified.

Neither rule earns promotion. Shock filtering increases the descriptive downside-first fraction, but the fixed24h cash overlay has negative mean marginal return after the declared costs versus the corrected incumbent. The specified daily reclaim sequence waits a median5days among confirmed complete parents and loses on average versus immediate entry and the incumbent over common14-day endpoints, including no-entry cash. This does not establish immediate entry as safe or reject all confirmation/risk reduction; it rejects these particular candidate policies as sufficient evidence of a new edge.

R4 retains2,378 scenario-event and6,738 account rows, not that many independent trades. Every summary and2,308 mature first-passage/6,738 account paths were independently arithmetically checked by the same session; no external-review claim. Combined regression pack256passed,25warnings; source/static/hash checks pass. All initial CSVs remain byte-identical after the disclosed terminal-open qualification repair. Result SHA256 b93f7b0408f59f2e688ccf043ce2c1600d9b02321b080e8af80e6ef6443ed636.

Next science dependency is a separately frozen incremental absorption/spot-participation or properly qualified genuine-flow test with unchanged comparable action/endpoints/cost accounting, not a retuning of R4 until it wins. Independent review, historical publication qualification, source funding semantics, PR conflict reconciliation and live/forward proof remain open. Parent mission incomplete; no live policy, trade, subscription, worker or automatic continuation was started.

## 2026-09-28 R5 participation experiment

R5 completes the frozen same-parent participation comparison under PR8050. Protocol3cc4e46d2b7827ba5fce746d5b4bcd1875fb80c6; research implementation065f29376d82db77342a634496ccd2f4d97d0ab0; all647R4 parent episodes retained across1,294 event and3,882account scenarios. No engine/config/live-policy change.

Downside volume filters only7of171persistent candidates and retains the same30downside-first outcomes; incremental mean -0.00178pp versus price-only at1h/10bp. Recovery volume increment+0.72003pp on53paired parents has wide uncertainty, period dependence and becomes nearly zero when2020 is removed. It leaves31parents in cash; zero all-parent median drawdown is not precise bottom timing. No candidate is promoted.

261combined tests passed with27warnings; independent arithmetic checks647observations,1,279barrier paths,3,843accounts and all48summary cells/intervals. Prior inputs/gates/artifacts unchanged. Complete source/results and scope limits: research/CRYPTO_SCIENCE_R5_PARTICIPATION_RESULTS_2026-09-28.md and the current R5 frontier in DEC-CRYPTO-VECTOR-R2-20260926.md.

Next: qualified signed-flow/venue/time information and a frozen continuous-probability/utility experiment versus R4/R5, with chronological selection and eventual issued-forward evidence. Coinbase unsigned spot and OKX CONTRACTS flow remain different measurements. Independent review, publication-time qualification, funding equivalence and production acceptance remain open. Mission incomplete; no worker, alert, trade, collector, automatic wake or deployment was started.

## Current R6 scientific result — chronological probability versus action utility

The same commissioned Crypto science track now includes a frozen quarterly continuous-model study, protocol067f0fb76f7fc20239aa4cdeae03b6cf5b279b85 and implementation7b63e8ab2608a4c280e410d5dfaab7df04042127. No production model/config/collector/gate/UI change or new forecast owner. See CRYPTO_SCIENCE_R6_PROBABILITY_RESULTS_2026-09-28.md and the cumulative current frontier in DEC-CRYPTO-VECTOR-R2-20260926.md.

Primary404scored post-break episodes: continuous price/state Brier improves0.103774→0.098027 versus expanding past rate, but its paired block interval includeszero and mean forecast15.85% exceeds actual11.14%. Adding unsignedvolume worsens primary proper scores slightly. Chronological training-only class-payoff mapping still trails incumbent wealth: primary10bp mean−0.04916pp(price)/−0.03503pp(+volume). No accepted crash probability or exit rule. Recovery cannot satisfy the precommitted80row/15perclass fit gate; actual derivatives signed-flow remains unqualified for unit/time/availability and excluded, not relabeled spot.

268combined tests passed,27warnings retained. Independent numeric expression by the same session verifies features,trainingdates,scalers,likelihoodgradients,allpredictions/actions and72utilitysummary cells; not independent researcher review. Allrecorded input/gate/prior-source/evidence hashes unchanged. Resultsb24832969f5758d0884dcbd85e75931f9fa5aaf20a23cab9182a760607cf3f54;manifest071d1475b40ec7214ec2af4a2b2d1da03045d09877dae8562bba200a889608c2. Complete derived evidence under research/crypto_science/r6/.

Next: independent review and a separately frozen training-only calibration/recent-rate comparator plus explicit risk-budget,tail-protection and turnover utility; do not optimize prior thresholds/delay from observed results or rerun completed audits. Parent mission remains incomplete, no livepolicy promotion,background worker or wake created.

## 2026-09-29 scientific continuation — recovered R6 and completed R7

Network recovery found R6 already published at b445029abd6c84a66cadc572929e0beb702be4b7 with successful exact-head CI/fences; it was not replayed. R7 calibration/protection protocol2e8709464b643a33a5bca53b53999f53ad4756f5 and implementation01a2b9c1ad89bfaae9200f581c5ef3ffa6cf29e1 preceded one result run. Same operation/branch/M2 carrier; research/test/continuity only.

Training-only recalibration lowers risk overstatement but recent-period Brier is essentially tied with a simple recency-weighted event-rate estimate. The primary calibrated-price protective rule loses mean return and declared drawdown-penalized utility. One calibrated-volume positive full-cohort cell has wide uncertainty, recent-period loss and cost/delay instability; no method earns promotion. Primary cohort289episodes,21target events; repeated37,611policy scenarios are not independent shocks.

Fresh combined suite276passed,27warnings. Independent numerical expression checked7,038cash/coin paths,70quarter training fits,1,012predictions and37,611policies plus504utility summaries; this is same-session arithmetic, not independent review. All55input identities,18gates and87prior evidence artifacts remain unchanged. Full result/report at research/crypto_science/r7/ and research/CRYPTO_SCIENCE_R7_CALIBRATION_RESULTS_2026-09-29.md; exact cumulative frontier in existing DEC-CRYPTO-VECTOR-R2-20260926.md.

Next scientific unit is action-aligned severity and timing: separate already-incurred loss from post-landmark avoidable risk and missed rebounds, then preregister the earlier observable cohort comparison. Independent review, signed-flow/publication qualification and fresh forward-issued evidence remain promotion gates. Current final allocation and all production/design/review/alert effects are unchanged. Parent scientific/product mission remains incomplete.

## 2026-09-29 R8 — earlier action and direct protection-value research

Same current Chairman continuation, operation crypto-vector-r2-20260926-sol-001, M2 Studio Direct and draft PR8050. R7 exactCI/fences succeeded. R8protocol89b6876ba0937691270b7b042427ea6fc4c2e042 and tested sourceede102e5eb9d83b4d13ef0f22b12148d72d433d5 preceded one new study. Research/tests/continuity only; no production model/collector/gate/UI/liveaction change.

Same588breakdown parents compare earliest completed observation with six-hour follow-up on a common24h endpoint. Of43large marked-loss cases across586complete primary accounts, seven had already occurred byk6; most remaining tailrisk was hypothetically avoidable, but indiscriminate cash loses mean return. Direct ridge models predict cash-minus-incumbent return/excess-drawdown value rather than binary event probability. Earlymodel is modestly better than later on average, with uncertainty crossingzero and negative reused2024+return/utility. No model earns promotion; restrictedhindsight envelopes are not executable edge.

Final combinedpack284passed,48warnings. Independently expressed SAME-session arithmetic checks1,998feature observations,14,076inventorypaths,420training snapshots,6,072predictions/30,204policyrows,288utilitysummaries and144paired method contrasts.55input identities/18gates/100prior artifacts remain unchanged. Fullreport andevidence: research/CRYPTO_SCIENCE_R8_ACTION_VALUE_RESULTS_2026-09-29.md and research/crypto_science/r8/; currentfrontier inexistingDEC-CRYPTO-VECTOR-R2-20260926.md.

Nextscientificunit requires a preregistered pre-breakwatch population withquiet/non-event periods, true warningleadtime, episode-clustered falsealarms and actioneconomics. Conditioning every earlierstudy on an alreadyobserved72hbreak cannot prove anticipatory warning. Independentreview, sourcepublication/rights, actualsignedflow qualification, forwardissued evidence and productionacceptance remain gates. Oneoptional post-verification diagnosticprint was explicitlyrefused pre-dispatch andnotretried; independentpermitted evidencepersistence continued. Parentmission incomplete; no automaticwake or liveeffect asserted.

## 2026-09-29 R9 pre-break research completion

R9 changes the scientific population from observed breakdowns to a fixed six-hour UTC watch clock including quiet/non-event periods. Protocol3821bcdade52648ea1c18667b538a032c4c1808c and tested implementation6d23d1b5f9fbd1034c44523fd03c74ec66b8f9e0 preceded one empirical execution. Same operation/branch/M2 Studio Direct carrier; research/tests/continuity only. No live warning, sizing, collector or new forecast owner.

Price features improve retrospective full-period Brier/ranking over a matched recent-rate baseline, but the proper-score gain is absent in the reused recent period. Fixed10%threshold emits1,114primary warnings with156own-window hits/953completed non-events/5unknown. Recent228warnings have20own hits and208non-events; only one strict anticipatory match among15damaging D0events, with5events actually supported. Hypothetical cash at those recent warning times loses−0.2222ppmean event return versus incumbent at10bp costs. Distinguish own-window precision, all-event versus supported recall, equivalent observed-watch-month burden and actual protection economics. No model or policy earns promotion.

Combined existing pack293tests passed,48warnings; compile, source-claim and diff checks pass. Same-session independent numerical expression verifies31,372clock scenarios,26,508finite features,70fits,25,526predictions,4,665warning scenarios,1,176catalogue event/lag rows,65strict matches and27,840inventory paths plus all summary arithmetic. These scenario counts are not independent shocks, and arithmetic verification is not independent researcher review.55input identities,18gates,114prior artifacts and inherited source hashes unchanged.

Full report/evidence: research/CRYPTO_SCIENCE_R9_PREBREAK_RESULTS_2026-09-29.md and research/crypto_science/r9/. Current cumulative exact frontier is DEC-CRYPTO-VECTOR-R2-20260926.md. Next dependency is independent review and exact existing flow/funding source semantics before a separately frozen coverage-matched incremental-information trial. Do not retune the completed price experiment, infer signed-flow units, splice unqualified history or weaken recovery minimums. Parent product/scientific mission remains incomplete; no automatic background continuation or release acceptance.

## 2026-09-29 — R10 source qualification completed

R10 moves the scientific frontier from another price-only forecasting variation to the exact meaning and availability of existing derivatives-flow/funding inputs. Same operation and M2 Studio Direct carrier; protocol38b8f6d2f2580730993e81de95ef1b7fa34e2a14 preceded the numeric audit. Initial implementation342cb1454d0aee29028f53df9019fbc7a568c5b3 and disclosed synthetic-receipt correction90adead20f7797b10446c54d0ca0bf0779bacd19 are retained with original and amended evidence.

The actual flow store has2,957hourly observations and nine missing hours in one gap. One historical24-row window spans33hours; one72-row window spans81hours. The latest windows remain complete. Existing count-based CVD and its720-hour gap threshold cannot certify shorter elapsed windows. The exact endpoint identifies aggregate BTC CONTRACTS but leaves required units/timestamp/finality semantics unresolved; descriptive same-unit ratios and dollar-capital/predictive claims remain different.

Secondary OKX funding capture retains predicted rates but drops actual settled rates and intraday settlement identity in a daily mean. This is not the active BGeometrics funding path. The latter has1,089legacy versus80current rate observations with one equal overlap, insufficient to authorize a splice. Generic publication schedules are not historical first-availability records. No new provider data or account was requested.

Only364R9forecast-qualified clocks overlap mechanically complete flow windows under both tested label conventions; no clock has the full documented availability/contract evidence, and even the hypothetical overlap is below R9's unchanged1,000training-example floor. No forecast, PnL or outcome association was fitted. Research-only source/clock helpers now make the requirements executable; production owners are unchanged.

Final combined suite306passed,49warnings. Same-session independent arithmetic verified five source frames,5,914window rows and125,488clock masks. All57input identities,18gates,137prior artifacts and inherited source hashes remained unchanged. The initial helper receipt-edge defect and verifier timestamp-unit mistake are disclosed and preserved. Report and exact evidence are under research/CRYPTO_SCIENCE_R10_SOURCE_QUALIFICATION_RESULTS_2026-09-29.md and research/crypto_science/r10/; cumulative frontier remains in DEC-CRYPTO-VECTOR-R2-20260926.md.

Next: inspect current collector/storage custody, implement an additive existing-owner retention/elapsed-window repair, and obtain exact provider contract evidence before a coverage-matched incremental study. No new data/control plane, speculative history, live model promotion or deployment. Parent mission remains incomplete.

## 2026-09-29 R11 producer/consumer repair

Recovered the interrupted local implementation instead of repeating it. Final source candidateb53636f05b6374dafabcbc9c5d8085773d88fdf0 adds response-occurrence evidence through the existing collector/keep-first owner, preserves predicted/actual funding and as-of revision/reversion, and leaves legacy numerical series/request signatures unchanged in controlled tests. Display-only CVD now uses contiguous elapsed label windows, explicit native units/unknown causal qualification, no price forward-fill, and wall-clock freshness distinct from price-feed synchrony. Existing builder warnings match the repaired semantics. No primary allocation or forecasting policy change.

The old R10 collecting archive filename and dynamically bound legacy diagnostic are repaired with exact original bytes preserved and manifest amendments, not waived tests or changed research outcomes. Final broad Crypto/Vector/storage/science368passed49warnings;50targeted collector/CVD tests; compile, source-claim and original enrollment checker pass with existing warnings retained. Normal run_adapter fake-HTTP/temporary-store proof checks9receipts,4as-of states,54elapsed-window cases, failure degradation and unchanged source-data/gate identities. These are same-session source/integration results, not independent review or live data accrual.

Evidence: research/CRYPTO_SCIENCE_R11_COLLECTION_REPAIR_RESULTS_2026-09-29.md and research/crypto_science/r11/. Exact cumulative frontier is DEC-CRYPTO-VECTOR-R2-20260926.md. BUILT_NOT_PROVEN: no actual provider source_observations file created, new scheduler, alert, trade, design effect, merge or deployment. Next is exact-head CI/integration and independent source-boundary review before an admitted prospective existing-collector proof. Unknown units/timestamps/finality/daily completeness, sufficient scientific sample history and fresh forward evidence remain gates; no speculative splice or lowered model minimums. Mission incomplete.
