---
key: CRYPTO-VECTOR-R2-20260926
question: >
  After the Chairman rejected Crypto + Bitcoin R1, what design and production
  contract should govern the replacement experience without creating new
  decision, chart, snapshot or alert authority?
answer: >
  R2 is a chart-led research experience: preserve P0A BitcoinDecisionState as
  the final allocation authority, reuse the existing Lightweight Charts,
  snapshot and Alert Center owners, expose evidence and data-quality limits,
  distinguish valid zero from unavailable state, and progressively reshape the
  existing governed Vector shelves rather than building a parallel product.
rationale: >
  R1 simplified away too much analytical depth and remained card-heavy. The
  recovered Vector research and live audit support a quieter instrument with
  synchronized charts, explicit source semantics, point-in-time replay and
  progressive depth. Truth and authority boundaries must improve at the same
  time as visual quality so missing model state cannot become an apparent
  0% cash decision and design work cannot silently fork canonical engines.
alternatives:
  - option: >
      Implement the rejected R1 card layout directly.
    why_not: >
      Chairman explicitly rejected R1 and commissioned a deeper chart-led
      replacement.
  - option: >
      Create a new chart engine, decision model or alert system for R2.
    why_not: >
      Existing canonical owners already provide those capabilities; duplicating
      them would create competing control and truth planes.
evidence:
  - >
    Paper R2 page p-R-0 in file 01M2WGNCX9475G79JRKJTCM08P contains five
    native editable, screenshot-reviewed boards and the builder release contract.
  - >
    research/CRYPTO_VECTOR_R2_DESIGN_AND_RELEASE_CONTRACT_2026-09-26.md records
    the recovered research, live audit findings, prototype proof and release
    gates.
  - >
    Commit 52937b45eb61f1ebe360fca086fb6b324f6e51a4 adds the qualified replay
    contract, source inspector and fail-closed allocation-history gate.
  - >
    Commit a8c0c6a129f06ad79abb4555f14fb1fed9f9ac9f reshapes the governed
    Vector front door around R2 research navigation and plain-language hierarchy.
affects:
  - "WS:CRYPTO-INTELLIGENCE"
  - crypto-vector-r2-20260926-sol-001
  - templates/vector.html.j2
  - scripts/build_vector.py
  - site/vector_chart.js
  - tests/test_vector_r2_data_boundary.py
  - tests/test_vector_r2_frontdoor.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-26
---

# DEC-CRYPTO-VECTOR-R2-20260926

Recorded 2026-09-26 by Sol under the Chairman's current Crypto/Bitcoin redesign commission.
Existing owner/workstream: `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md`.
Operation: `crypto-vector-r2-20260926-sol-001`.
Projection/evidence: Macro Draft PR #8050, branch `sol/crypto-vector-r2-20260926`.

## Ruling

The Chairman rejected R1 for insufficient beauty, sophistication, understandability and production readiness. Do not implement R1 as an accepted reference. R2 is the new proposed visual direction; Chairman acceptance and production certification are not claimed.

The R2 design uses chart-led research rather than a card-wall: synchronized price/risk/exposure, relative price-ratio comparison, selected-date evidence, separate current versus historical model state, light/dark compositions and a purpose-designed mobile layout. Preserve useful existing analytical depth and the accepted P0A BitcoinDecisionState authority.

## Durable design/evidence anchors

Full source, feature and release contract: `research/CRYPTO_VECTOR_R2_DESIGN_AND_RELEASE_CONTRACT_2026-09-26.md`.
Paper file `01M2WGNCX9475G79JRKJTCM08P`, page `p-R-0`:
https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-R-0

Nodes: Bitcoin light `1EQ1-0`; Crypto light `1FL0-0`; Cycle Lab dark `1FRD-0`; Bitcoin mobile `1G0I-0`; builder blueprint `1GKA-0`. Five boards screenshot-inspected. Shared tokens `bba69475` unchanged.

Mastermind law pin `a31f49f4056943124cc0e7e42349e46feee444c7`; Macro audit pin `7150f29a765387f1c14fbae086314af6e0d6bddc`.

Offline preview artifact SHA-256 `80f95a5f241eb3f07f9e454168197059e16409848517e6888043e553dece5044`. Twelve core tests and 44 offline authored-DOM/browser checks passed. Local URL navigation was policy-blocked; no browser policy changed. Offline DOM proof is not real-route acceptance. Separate M2 audit successfully loaded both current public routes at desktop width; actual audit exceptions are documented in the research contract.

## DO_NOT_REDO / effect frontier

Do not rebuild accepted P0A authority, revive failed macro-allocation gating, recreate R1, rescan recovered research without a changed question, or duplicate existing chart/snapshot/alert owners. Resume verified R2 effects. At the original R2 design checkpoint, no production application files, model output, live alert, deployment, trade or durable worker had been changed/started; the later Extra High continuation below records the subsequent Bitcoin production commits. No modifying effect is known EFFECT_UNKNOWN. Denied action/target paths remain fenced as documented in the contract; one working action is not blanket capability evidence.

## Remaining release work

Bitcoin Slice 0 plus the narrow Slice 1 candidate is now published and awaiting exact-head CI/browser proof: qualified chart contract -> existing chart adapter -> exact source inspector -> invalid-state suppression, plus the R2 front-door hierarchy. The Crypto template lane remains held behind active #7645; shared theme changes remain held behind #7849. After Bitcoin proof, investigate and quarantine implausible ranked returns, distinguish altseason definitions, label source clocks, add Crypto budget/return-window consistency tests on a reconciled carrier, and close the recorded H5 budget bypass without replacing the canonical total-budget authority.

Full acceptance still requires real data integration, production-path screenshots/results, EN/ZH and both themes, accessibility/task completion, failure fixtures and cost/performance evaluation where relevant. No return series is fabricated to fill a performance card. No synthetic fixture is production strategy authority.

Classification: CHECKPOINTED_CONTINUATION at R2 design review / production integration boundary. This is not completion or custody transfer. Sol retains ownership. Next phase recommendation: Extra High for iterative implementation and real-route browser tests, after required capability/ownership verification. No mode self-switch, daemon or watcher is claimed.

## Extra High continuation — 2026-09-26

The Chairman enabled Extra High and continued the commission. Source collision review found the Bitcoin Vector production paths unchanged since the R2 audit pin; active PR #7645 still owns Crypto table/template work and #7849 still owns shared theme tokens, so this continuation deliberately advances Bitcoin only without touching those paths.

Two production commits now exist on PR #8050:

- 52937b45eb61f1ebe360fca086fb6b324f6e51a4 — creates mastermind.vector_risk_strategy.v2, preserves genuine 0% allocation separately from unavailable state, refuses to infer trade markers across missing decisions, exposes exact source/unit metadata without inventing availability timestamps, suppresses replay when required history is incomplete, and places the source contract in the real Vector study surface.
- a8c0c6a129f06ad79abb4555f14fb1fed9f9ac9f — keeps the exact governed S1–S6 roots but removes their decorative rail/card-wall treatment, adds Overview/Cycle/Strategy/On-chain/Derivatives research navigation, leads with a plain-language market read plus the canonical final model allocation, and keeps deeper evidence progressively available.

Local pytest execution for the new contract tests was explicitly refused before dispatch and was not rerouted or disguised. Earlier static Python/JavaScript/Jinja syntax verification succeeded on the first slice; a later combined front-door static verification call was separately refused before dispatch and was not retried. Canonical PR CI is therefore the test owner for these published candidates.

The first published slice exposed one fence failure unrelated to implementation logic: this decision record lacked the required YAML frontmatter. All other fence components in that run passed. This record has now been repaired in-place rather than creating a second decision owner. Production acceptance remains false until exact-head CI, generated-page/browser proof, and the remaining truth/data gates pass.


## Pro continuation — current cumulative frontier

Current Chairman intent is to continue toward immediately understandable, sophisticated, production-ready Crypto/Bitcoin experiences. Pro is user-reported; no served-model or mode telemetry is inferred. Protected Mastermind pin for this continuation: `4c6b206d3fb7fbc6d077faf61ae361bedf259925`, INDEX blob `94d1af402598894372858793a5b1931019c5fa77`, compatible Skillpack 1.0.1. Sol retains ownership under the existing operation and workstream. Direct native design work is principal judgment on the expressly authorized M2 Paper carrier; no worker was started.

### Verified native design delta

Paper file/page remain `01M2WGNCX9475G79JRKJTCM08P` / `p-R-0`. Shared token SHA `bba69475` is unchanged. The unrelated active document page was not edited.

- Corrected Crypto desktop `1FL0-0`: its former “Bitcoin leads” headline contradicted the SOL/BTC and ETH/BTC comparison. It now reads “SOL and ETH gain ground,” explicitly scoped to an eight-week illustrative comparison, not broad altcoin participation or expected upside.
- New `1NK0-0`, 1440 x 1120: refined dark Bitcoin Overview. One clear model stance, one synchronized price/risk/allocation instrument, explicit incomplete funding evidence, and inspect-decision first. Historical performance statistics are not part of the current-decision hierarchy. Marked design scenario, not live.
- New `1O0V-0`, 390 x 1260: Crypto mobile comparison. Direct series labels, an explicit 100 baseline, matching eight-week ratio changes, source/calculation entry, and a first-visit saved-baseline action.
- New `1O5O-0`, 1440 x 1270: comparison evidence sheet, unavailable Bitcoin decision and confirmed save-failure examples, plus the builder interaction/acceptance contract. Distinguishes valid 0% Bitcoin / 100% cash from missing decision; preserves unrelated qualified price/history; ambiguous save responses must reconcile before another write.

All three new boards and the corrected Crypto desktop were screenshot-inspected. The recovery board's dark text inheritance and height were repaired, then its screenshot was checked again. Proposed five-second comprehension/user-task acceptance is written on-board, but no participant study has been run and no award or production acceptance is claimed.

### Source/effect reconciliation and actual CI

The interrupted chart move applied to the existing local workspace, not a second branch: `templates/vector.html.j2` and `tests/test_vector_r2_frontdoor.py` were dirty atop `bfcdbaebd1032be6b96ed39532e1bab204e9d2f6`. One `vec-risk-chart` now appears in Overview; the Strategy instance was removed. Do not replay either mutation. Remaining local corrections are tracked in the same owned workspace. No modifying effect is known EFFECT_UNKNOWN.

Exact-head fences run `36279838458` passed; CI run `36279838608` failed. Contract-delta job `108516311639` reports the two newly added R2 tests are not enrolled in any workflow run step. Feature job `108516640073` reports six Bitcoin decision rendering failures and two Vector canonicalization failures. The decision trace identifies a real boundary regression: its fixture extracts from the first `set decision_ok`, which was moved above the hero; the isolated decision render then receives unrelated undefined hero variables. It is not evidence that six financial decisions were wrong. The two other failures concern the missing `id="timeline"` anchor and an ambiguous `#timeline` default; whether those are inherited versus introduced still requires an exact-base comparison.

The test path from that CI trace returned 404 at the supplied GitHub heads and ENOENT in this sparse workspace. No substitute test file or passing result is invented. Local pytest, the denied readout replacement, denied combined static checks and denied PR-body update remain fenced. Automatic existing PR CI is the evidence owner for published candidates; no dummy push or duplicate runner is authorized.

### Remaining production obligations

Finish the bounded source integration without disguising historical performance as a current model recommendation, preserve a directly renderable decision section, and keep unavailable hero state distinct from mixed evidence. Reconcile the existing CI test-registration owner before enrollment; keep Crypto #7645 and shared-theme #7849 paths untouched until current custody is established. The published replay gate currently suppresses all history on a missing required observation; narrow it to dependent claims in a separately verified repair. Existing JS null-readout repair remains blocked by its explicit denial.

Production release remains held for exact-head tests, generated real-route visual/interaction proof, EN/ZH and both themes, valid-zero and missing-input cases, point-in-time source semantics, qualified asset rankings, and canonical H5 total-budget identity. Design boards and prior prototype test receipts do not satisfy these obligations. No deployment, live alert, trade, autonomous watcher or accepted release exists from this continuation.


### Source candidate and continuation boundary

This revision preserves the reconciled Overview chart move and returns CAGR/Sharpe/drawdown/time-invested statistics to Strategy, labeled full-history simulation excluding trading costs. It restores the standalone canonical decision fragment while keeping Overview as a read-only projection of the same decision, corrects the navigation's markup-in-ARIA error, gives missing market analysis its own unavailable headline, and corrects the 0% Bitcoin / 100% cash language. Four regressions were authored in the existing `tests/test_vector_wave1.py`; the R2 data-boundary wording assertion was strengthened. No new passing test receipt is claimed.

The five changed Paper boards were visually reviewed. The builder board now links all eight R2 boards and the real failed-CI frontier. Own working indicators were released successfully after one DOCUMENT_CHANGED pre-dispatch refusal and a fresh same-carrier snapshot. No shared token or unrelated active-page design was changed.

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
Boundary: the requested Pro design/refinement chunk has produced reviewed native screens and a bounded source-repair candidate. The next stage needs exact-candidate CI/test-enrollment adjudication and real-route integration proof; the heavy design/CI context should not be replayed. This is not release acceptance, cancellation, source-custody transfer or a claim all lanes are unavailable.

Exact next action: read this cumulative record and the current PR #8050 head, reconcile the current existing CI registration owner against the two unenrolled R2 tests, then consume exact-head CI and repair remaining failures in the same owned branch. After required capability/permission checks, prove the generated Vector route and chart-to-evidence interaction at 390/768/1440, EN/ZH and both themes. The denied local tests/static/readout/PR-body actions remain fenced; a new turn or mode is not retry permission. The source/feature contract lists remaining native-design mismatches explicitly.

Resume surface: Pro for CI/source adjudication and product review, as currently requested. Reassess a concrete permitted execution surface only when the next build/browser action requires it; do not infer capabilities from the mode name. No worker, watcher or automatic future session was started. Sol remains accountable; accepted P0A and existing snapshot/chart/alert owners must not be rebuilt.

## Expansion and hardening — current continuation

The Chairman praised the reviewed R2 pass and explicitly continued expansion/hardening. This endorses continuing the visual direction; it does not waive source, usability or production gates. Protected Mastermind remains `4c6b206d3fb7fbc6d077faf61ae361bedf259925`, INDEX `94d1af402598894372858793a5b1931019c5fa77`, Skillpack 1.0.1/bootstrap 1. Same Sol operation, M2 Studio Direct carrier, owned sparse branch and Paper p-R-0; no worker or watcher started. Direct source repair is CRITICAL_PATH_SHORTCUT; native interaction design remains PRINCIPAL_JUDGMENT.

Reconciled PR #8050 at `5a381634787610eaf99ea2f8ff12729f65df021d` against the clean same-carrier workspace. Fences run `36289883594` completed successfully. CI `36289883729` was still running, with contract-delta job `108537811923` failed. GitHub CLI refused log display while the parent run was in progress; no new error details or passing result were inferred.

CI registration custody is now resolved at the changed-region level: #8041 head `39618e255cbd9d434651091c493ccf80d4b3864f` changes only the design-governance invocation around line 6660. Our repair changes only the existing unrun-vector-dsr pytest invocation around line 11230, whose bytes match observed main `de82839b9bea319b2ca4112808b1d6bacdc0ff4a`. No #8041 job region, dependency, job identity, timeout, gate or runner was changed.

The same existing Vector invocation now names both R2 suites and previously unenrolled `tests/test_vector_wave1.py`. A regression in the R2 frontdoor suite checks that the actual existing pytest step invokes all three without a conditional or ignored failure. Local tests remain denied and were not attempted; this is source-enrollment candidate evidence, not test success. Existing automatic PR CI remains the execution owner.

### Verified return-visit design expansion

The native R2 page now has eleven artboards, confirmed by a bounded tree read of `root_node_p-R-0`. New boards are: `1OQ7-0` (09, Past Decision, dark desktop 1440); `1PIG-0` (10, Since your review, light desktop 1440); and `1Q1E-0` (11, Saved review plus optional alert confirmation, light Chinese mobile 390). All three are populated, editable and screenshot-inspected after correcting text contrast, chart coordinates or content fit. Shared token hash remains `bba69475`. The unrelated active Prophet page was not edited.

Board 09 makes the historical date explicit, aligns price/risk/allocation to that date and distinguishes a recorded model target from an explanation of its cause. The inspector withholds an unsupported rule-level explanation and says publication timing is unverified; a dated record is not proof of what was knowable then. Its synthetic 100% to 60% Bitcoin change on 12 September leaves 40% cash, not a personal-account assertion. A dated review can be saved without activating an alert.

Board 10 adds the second-visit question: "Same allocation. Different evidence." The illustrative 12-to-26 September comparison preserves both 60% model targets while risk falls from 61 to 43. Synthetic Bitcoin prices 87,600 to 94,400 give a rounded +7.8% price change, explicitly not strategy or account performance. Funding unavailable at the baseline is not compared with zero. Source corrections are distinct from new market observations; saving a new review does not overwrite the original.

Board 11 shows a synthetic confirmed save separately from an alert awaiting confirmation. Chinese copy explains the original review is preserved, model allocation is not the user's account, and saving does not enable notifications. Its illustrative threshold is a target change of at least ten percentage points from the preceding valid published target. Exact trigger/channel support, entitlement and activation receipts still need the existing Alert Center owner; no real review or subscription was created.

The existing research/release contract now specifies historical/revised evidence, field-level comparability, immutable review references, separate save/activation effects and fourteen adversarial acceptance cases. Those cases are requirements, not newly executed tests. It also specifies authorization on reopen, safe handling of notes/source text, non-hover chart inspection, date-race handling, focus return and long EN/ZH layouts without inventing latency or accessibility certification.

### Source and verification receipts

CI enrollment repair was committed and pushed on the same branch as `228f74d30b345dc60408e7be91a5c4a0027af5fa`; origin readback matched. Exact-head fences `36290594814` completed successfully. Exact-head CI `36290595014` was pending when inspected. Prior-head CI `36289883729` was still in progress. The three suites are now invoked in source by the existing Vector pytest command; their execution and passing status remain unverified. The later records-only commit containing this cumulative checkpoint does not inherit an exact-head CI success claim from that source receipt.

### Deferred native housekeeping and effects

Attempts to refresh builder board 05 (`1GKA-0`, text nodes `1GKE-0`, `1GKX-0`, `1GL0-0`) were refused before dispatch with DOCUMENT_CHANGED while the unrelated active page was being edited. They did not apply. The builder still contains the previous eight-board/current-CI references; use this record and the updated release contract for the eleven-board handoff. A subsequent attempt to release working indicators on roots 09–11 was also refused before dispatch, so indicator release is not confirmed. Do not replay the three completed boards or change the active page to bypass the guard. Revisit only after evidenced document stabilization or a relevant adapter/environment change, with fresh same-carrier inspection and original-target reconciliation. No further unchanged inspect/retry loop is authorized.

All successful Paper and source effects above are reconciled. No modifying effect is known EFFECT_UNKNOWN. The pre-dispatch document-drift refusals are neither unknown execution nor a blanket policy denial. Existing explicit denials on local pytest, combined static checks, the JavaScript readout replacement and PR-body update remain fenced. Crypto #7645 and shared-theme #7849 paths remain untouched.

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
Boundary: the requested return-visit expansion has produced three visually reviewed native screens, a source CI-enrollment repair and a detailed integration contract. The next bounded phase is exact-current-candidate CI/source adjudication and real-route proof; the pending existing CI and document-drift housekeeping are recorded without launching another runner or replaying this heavy design context. This is not release acceptance, cancellation, transfer of custody or a claim that all useful lanes are blocked.

Exact next action: recover this cumulative record and the current PR #8050 head; consume the existing exact-head CI return, resolve actual failures in the same owned branch and prove the generated Vector chart-to-evidence path at 390/768/1440, EN/ZH and both themes through permitted actions. Then bind the reviewed historical/comparison/save views to the existing decision, snapshot/case and Alert Center owners. Independently refresh builder references and release only our working indicators after the native guard is stable. No new boards are needed to repeat the now-reviewed return journey.

DO_NOT_REDO: accepted P0A, rejected R1, recovered research, the reconciled Overview chart move, completed R2 boards or CI enrollment. Outstanding production work includes dependent-series/date-specific missing-data handling, the fenced null-readout repair, qualified rankings and source clocks, H5 budget identity, real review/alert owner integration and user-task proof. The fourteen new hardening cases, comprehensive browser matrix and participant comprehension study have not run.

Resume surface: Pro for exact-source/CI adjudication and product review, as requested. Reassess a concrete permitted build/browser surface only when its required action makes that necessary; no mode self-switch or telemetry is asserted. Sol remains accountable. No worker, watcher, automatic future session, deployment, trade or live user action was created.


## Extra High Crypto-design continuation — Paper write pin blocked, design lane advanced

Current Chairman scope continues Crypto design. Protected Mastermind is pinned to `fda6ed3911cdda24eb63b2ccbe1b174121cf404f` (INDEX blob `94d1af402598894372858793a5b1931019c5fa77`). Paper's first requested board-12 mutation was refused before dispatch as `UPSTREAM_SCHEMA_UNREVIEWED`; the new observed catalog hash is `8cd27488a3adfc19c6c36d4349b75feebc71c159253c47f8a0f8d50c27043deb`, while the guarded adapter expects `ca90a537ee97f3e371ac945a8a3b9a928ba7fac9ffaeb67e31491075a0790570`. `accepted_for_write=false`. Therefore no new Paper node/artboard effect exists from this turn and the Paper mutation lane is frozen pending an accepted exact write pin. Do not use another carrier to bypass it.

Open #7645 still owns Crypto production table/template work and #7849 still owns shared theme primitives. No collision path was edited. The independent design lane advanced through a local M2 visual study, explicitly `NOT_APPLIED_TO_PAPER`, at `/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/crypto_deepening_preview.html`. Reviewed screenshots are `crypto_deepening_market-pulse_r3.png`, `crypto_deepening_asset-explorer_r2.png`, and `crypto_deepening_capital-leverage_r3.png`.

The Market Pulse first prototype revealed a truth defect during visual review: breadth, relative leadership and Bitcoin market share were drawn on a shared-looking axis despite different meanings/scales. It was corrected to three aligned independent panes before checkpointing. Capital flows were likewise split into separate ETF and stablecoin panes instead of suggesting a common value scale. This correction is design evidence only, not production code.

The canonical research contract now records exact jobs, semantics and hardening gates for intended Paper boards 12 Market Pulse, 13 Asset Explorer and 14 Capital & Leverage. The next Paper effect is to recreate those reviewed states natively only after the guarded catalog pin is accepted. The next product-depth board after that is an Asset Detail / SOL workspace, not another generic dashboard.

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
DO_NOT_REDO: reviewed R2 boards 01–11; the corrected supporting previews; accepted P0A; current CI enrollment; existing chart/snapshot/alert owners. The Paper refusal is EFFECT_NONE, not unknown execution. No deployment, alert, review save, trade, worker or watcher started.
Exact next action: after a relevant adapter/schema change is evidenced, re-read the current Paper catalog/inspect receipt and, if `accepted_for_write=true`, build intended boards 12–14 natively from the reviewed preview on p-R-0, screenshot-review them, update builder references, and release only our indicators. If Paper remains blocked, continue the independent Asset Detail design and source/test integration without claiming canvas completion.
