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
