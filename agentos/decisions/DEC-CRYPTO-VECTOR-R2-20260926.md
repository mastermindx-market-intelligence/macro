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


The independent Crypto-deepening study has one additional reviewed screen: `crypto_deepening_asset-detail_r1.png`. It defines intended Paper board 15 Asset Detail / SOL after the write gate recovers. The screen synchronizes SOL/USD, SOL/BTC and spot-participation panes on the same dates but separate scales; treats liquidity as separate evidence; gives supporting and weakening evidence equal visual weight; links existing Event Intelligence without predicting direction; and separates Save dated review from optional follow behavior. The values are synthetic design fixtures and no user action or model authority was created.

The full intended native sequence after Paper write acceptance is now: 12 Market Pulse → 13 Asset Explorer → 14 Capital & Leverage → 15 Asset Detail / SOL. Do not mint new Paper IDs or claim these boards exist until the guarded adapter reports `accepted_for_write=true` and the native effects are screenshot-reviewed.


The supporting Crypto study now covers all four top-level Crypto research jobs plus one asset-detail workspace: Market Pulse, Asset Explorer, Capital & Leverage, Asset Detail / SOL, and Events. The reviewed Events preview explicitly separates before/during/after-event work, source/timing certainty and unknown price direction. It reuses Event Intelligence conceptually and creates no event/alert authority.

Supporting visual hashes are recorded in the research contract. The intended Paper sequence after write-pin acceptance is now boards 12 Market Pulse, 13 Asset Explorer, 14 Capital & Leverage, 15 Asset Detail / SOL, 16 Events. No such native board IDs exist yet from this continuation.


### Later CI status correction

A later GitHub read shows source-candidate commit `228f74d30b345dc60408e7be91a5c4a0027af5fa` CI run `36290595014` finished `cancelled`; fences `36290594814` remained successful. Therefore the newly enrolled R2/Vector suites still have no passing exact-source CI receipt from that run. Current records/design head `f85848e430331e1bd55ccd7d2257c2e647ba2de6` had CI `36294877873` pending and fences `36294877729` in progress when inspected; those docs-head runs do not substitute for source-candidate behavioral proof. Do not state CI green.


## Extra High source hardening — partial allocation gaps and real-template proof

Protected Mastermind law for this continuation is pinned to `fda6ed3911cdda24eb63b2ccbe1b174121cf404f` with INDEX blob `94d1af402598894372858793a5b1931019c5fa77`, Skillpack 1.0.1 / bootstrap major 1.

The previously unavailable local pytest action became available in this Extra High session and was used once per changed candidate rather than inferred from mode. Focused R2/Vector tests first passed 20/20 on the pre-gap-hardening head. A new TDD cycle then narrowed missing-allocation behavior: RED proved the old payload suppressed the whole replay; GREEN changed the contract so a historical allocation gap remains `null` in the chart while cumulative performance becomes unavailable only after that missing decision would govern a return interval. A second RED/GREEN cycle proved that a missing *latest* allocation does not erase performance already measurable through the latest close.

Current source candidate is immutable commit `e17c55ad81b01d076a6ab122130bc1c545347e5a`:
- `scripts/build_vector.py`: chart `valid` no longer requires complete allocation history; `performance_valid` is separate. Allocation gaps emit `ALLOCATION_GAPS`. Equity stays measurable through the missing-decision date, becomes unknown on the following return interval, and stays unknown cumulatively. Missing latest allocation can therefore coexist with valid historical performance.
- `site/vector_chart.js`: allocation and strategy-equity gaps render as whitespace; crosshair readout shows `—` for unavailable price/risk/allocation/performance rather than fabricating 0%, $0 or 1.00×.
- `templates/vector.html.j2`: chart remains usable with allocation gaps; explanatory copy states performance is visible only while governing allocation is known; full-history allocation simulation is hidden only when `performance_valid=false`.
- `tests/test_vector_r2_data_boundary.py`: covers valid zero versus null, no marker across missing decisions, gap timing, latest-decision edge, template gating and JS unknown readout.

Fresh verification on this exact source candidate:
- `tests/test_vector_r2_data_boundary.py`: **7 passed, 0 failed**.
- Existing Vector CI pytest command after adding only the omitted sparse test dependencies (`/contracts/` and root `config.yml`) to this worktree: **87 passed, 5 skipped, 0 failed**. Before those two sparse paths were added, the same command produced 23 failures; all 23 were traced to missing `contracts/btc_decision.schema.json` or missing root `config.yml`, not behavior changes. No full checkout was used.
- Python compile, JavaScript `node --check`, Jinja parse and `git diff --check`: successful.
- The pytest output carries pre-existing Pandas deprecation and temporary Chromium cleanup warnings; do not call the run warning-free.

Controlled actual-template browser proof was also completed against the current R2 `templates/vector.html.j2` plus current repository chart/theme assets before the final allocation-gap source delta. Matrix: 1440/768/390 × dark/light × EN/ZH (12 combinations). Observed in every combination: HTTP 200, one canonical verdict, no page-wide overflow, synchronized chart mounted (15 canvases), source inspector opened from keyboard and exposed the expected source IDs, current model allocation remained distinct from historical strategy results, and no page JavaScript errors occurred. Representative 1440 dark EN, 768 light ZH and 390 dark EN screenshots were visually reviewed. Fixture-only request failures remained for shell extras/fonts not copied into the bounded fixture, so this is not a clean-network or production-route receipt.

The controlled fixture initially copied assets from the wrong source path, producing false non-mount/overflow evidence; the harness was corrected before the matrix above. A screenshot-like mobile Ask Mastermind overlap was investigated in DOM and could not be reproduced as a live element, so no CSS change was made from that artifact.

A later attempt to refresh the controlled fixture specifically for the new allocation-gap branch was refused before dispatch by the platform. It was not retried or routed around. Therefore the new gap semantics have automated source/unit/template proof but **no browser gap-state receipt yet**. Do not claim otherwise.

Paper remains independently blocked: server `paper-desktop 0.5.12`, observed catalog SHA `8cd27488a3adfc19c6c36d4349b75feebc71c159253c47f8a0f8d50c27043deb`, accepted adapter pin `ca90a537ee97f3e371ac945a8a3b9a928ba7fac9ffaeb67e31491075a0790570`, `accepted_for_write=false`. No native boards 12–16 were created. The supporting Crypto previews remain `NOT_APPLIED_TO_PAPER`.

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
DO_NOT_REDO: R1, accepted P0A, native R2 boards 01–11, reviewed supporting Crypto deepening screens, current CI enrollment, or the now-verified allocation-gap source logic. No production deployment, live alert, trade, save action or worker/watch cycle was created.

Exact next action after publishing this checkpoint: consume exact-head PR CI/fences for `e17c55ad8…` plus this records update; if source tests remain green, obtain production/generated-route browser evidence for the gap state when a permitted browser fixture/action exists, then continue H5 budget identity / qualified Crypto ranking integration without touching open #7645/#7849 custody. If the Paper adapter pin changes and `accepted_for_write=true`, apply reviewed boards 12–16 natively and screenshot-review them.


## Governance repair and gap-state browser proof — 2026-09-27

Exact-head `74f7a043a701bcf11a1ddfcac8982650db16b136` fences completed successfully, while CI run `36296186669` failed only in `ci-pack-10` / design-governance. Root cause was six forward-only design ratchet findings introduced by the R2 Vector front-door work: five literal radii and one inline `--vchart-h` custom-property literal in `templates/vector.html.j2`. All other CI packs succeeded. The failing design-governance unit/selftest/base-replay surfaces themselves were healthy.

The repair reused existing house tokens instead of creating a new style plane:
- wordmark control radius -> `var(--r-btn,10px)`;
- as-of dot and exposure rail -> `var(--r-pill,999px)`;
- tape and Overview card radii -> `var(--r-card,12px)`;
- removed the page-local `--vchart-h:470px` override and returned to the existing chart adapter default.

Fresh forward-only ratchet against the current working candidate: **0 blocking findings**.

The repository's canonical `scripts/capture_page_evidence.py` owner then captured the actual generated Vector fixture at desktop 1440x900 and mobile 390x844, both dark/light and EN/ZH: **8/8 required states captured**. Durable evidence owner:
`mockups/evidence/crypto-vector-r2-actual-20260927/EVIDENCE.yml`
with manifest `mockups/evidence/crypto-vector-r2-actual-20260927/manifest.json`. The owning receipt names `templates/vector.html.j2`. Local `check_ui_visual_evidence.py` passed against the full branch UI diff after that receipt was present.

Source/evidence commit: `155348673c2266f55e8fb1f5cf4ea7135e3a475e`.

Fresh consolidated verification on the final source/evidence bytes completed with exit 0:
- forward-only design ratchet: 0 blocking;
- visual evidence gate: PASS;
- exact existing Vector pytest pack: **88 passed, 5 skipped, 0 failed**;
- Python compile, JavaScript syntax, Jinja parse and `git diff --check`: PASS.
Warnings remain from the existing `Timestamp.utcnow` deprecation and temporary Chromium cleanup; no warning-free claim is made.

The controlled partial-allocation-gap browser route is now also proven on the source semantics:
- gap payload: `valid=true`, `performance_valid=false`, issue `ALLOCATION_GAPS`;
- 1440/390 × dark/light × EN/ZH: all eight combinations HTTP 200, no horizontal overflow, 15 chart canvases mounted, gap disclosure visible, simulation-unavailable state present, no `#vrc-score` simulation metrics, no page JS errors;
- crosshair at missing-decision date `2026-09-20`: Price $83,640; Risk 45; **Allocation —**; **vs HODL 1.02×** because the prior known allocation still governed that close;
- next date `2026-09-21`: Price $83,521; Risk 45; Allocation 20%; **vs HODL —** because the missing 20-Sep decision governs the next return interval and cumulative strategy performance is no longer knowable.

These are controlled generated-fixture receipts, not production-route acceptance. Shell-only fixture request failures for some fonts/account/terminal overlay assets remain recorded in the evidence manifest.

### Visual blocker discovered during evidence review

The committed canonical screenshots visibly include the shared theme.js Brain boot launcher. On the desktop Vector capture it sits over the right-side evidence area; the mobile capture also places the launcher/orb over high-value Vector content. A raw crop of the committed desktop PNG confirmed the launcher is in the screenshot bytes, not merely the ChatGPT image viewer. Repository tracing identifies the owner as the existing `theme.js` `#mmb-boot` / `mm_brain.js` launcher, not Vector markup.

No launcher behavior or shared Brain code was changed in this continuation. Existing production patterns show that Macro Command reserves a gutter on desktop and suppresses the global FAB on mobile when an in-page analyst entry exists, while `mm_brain.js` supports host-provided `anchor:'top'`. Changing Vector's chat entry is a bounded UX design decision and remains pending Chairman approval under the active brainstorming gate; do not silently hide or fork Brain.

Paper write remains independently blocked at `paper-desktop 0.5.12`, observed catalog `8cd27488a3adfc19c6c36d4349b75feebc71c159253c47f8a0f8d50c27043deb`, accepted write pin `ca90a537ee97f3e371ac945a8a3b9a928ba7fac9ffaeb67e31491075a0790570`, `accepted_for_write=false`. No native boards 12–16 exist.

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
Next implementation action requiring design approval: replace the floating Brain launcher on Vector with one explicit in-page Ask Mastermind entry that reuses the existing boot/open owner, suppressing the floating stub/launcher on Vector only. After approval, implement TDD-first, recapture the 8-state evidence matrix, rerun design/visual gates and exact Vector pack, then consume exact-head PR CI/fences.


## Approved Vector Brain-entry implementation — 2026-09-27

Chairman explicitly approved the bounded launcher design in the outer live message and instructed continuation. Current protected Mastermind law pin for this modifying continuation is `c01d890f6536539496f2d6744f3143ff49da296d`, INDEX blob `94d1af402598894372858793a5b1931019c5fa77`, Skillpack 1.0.1 / bootstrap major 1.

Implementation commit: `e0b8f075618e268f393a98b0e649b36c09e3e0e7`.

Capability delta:
- before: shared `theme.js` mounted the bottom-right Brain boot FAB on Vector and canonical screenshots showed it covering evidence/chart content;
- after: Vector exposes one explicit in-page **Ask Mastermind / 询问操盘大脑** control in the research section bar, suppresses the redundant `#mmb-boot` and `#mmb-launch` on `body.page-vector` only, and reuses the existing Brain owner for activation.

No `theme.js`, `mm_brain.js`, API, thread store, routing, assistant identity or Brain lifecycle code changed. Vector does not set `MM_BRAIN_CFG`, import `mm_brain.js`, call `/api/brain`, or create a second chat owner. The Vector action first opens an already-mounted `window.MMBrain`; otherwise it programmatically activates the existing hidden `mmb-boot` stub. It carries `aria-haspopup=dialog` / `aria-controls=mmb-panel`, a busy state while the existing owner mounts, and a bilingual unavailable label after a bounded failed mount attempt. Closing Brain leaves the in-page Vector action as the re-entry point; the floating launcher remains hidden on Vector.

TDD receipt:
- RED: the new source tests failed because no `data-vector-brain` entry existed.
- GREEN: `test_vector_uses_in_page_brain_entry_and_suppresses_floating_launcher` and `test_vector_brain_entry_is_not_a_second_chat_owner` passed after implementation.

Controlled real-template interaction proof:
- matrix: 1440x1000 and 390x844 × dark/light × EN/ZH = 8 combinations;
- before click in every cell: in-page Vector Brain button visible, `#mmb-boot` exists but is not visible, no `#mmb-launch`, no page-wide overflow;
- after click in every cell: existing `window.MMBrain.mounted=true`, `#mmb-panel.open` visible, real `#mmb-launch` may exist under the shared owner but remains invisible due Vector-local suppression, no button error/busy residue, no page JS errors.

Canonical visual evidence was recaptured after implementation with the repo's existing `capture_page_evidence.py` owner. Receipt remains:
`mockups/evidence/crypto-vector-r2-actual-20260927/EVIDENCE.yml`.
Manifest now proves 24/24 states: the required 8 REST cells plus real browser `brain-hover:hover(.vector-brain-entry)` and `brain-focus:focus(.vector-brain-entry)` force states across the full state matrix. The visual-evidence guard initially refused REST-only evidence for the new hover/focus CSS; after those interaction captures were added, the gate passed. Representative desktop/mobile EN/ZH and focus/hover captures were visually reviewed. The previous floating overlap is absent in the recaptured rest states.

Fresh final local verification on the implementation/evidence bytes:
- forward-only design ratchet: **0 blocking findings**;
- canonical visual-evidence guard: PASS;
- exact existing Vector pytest pack: **90 passed, 5 skipped, 0 failed**;
- Python compile, JS syntax, Jinja parse and `git diff --check`: PASS.
Existing Pandas deprecation and temporary Chromium cleanup warnings remain; no warning-free claim.

This slice supersedes only the earlier pending Brain-launcher UX decision. The shared Brain owner and all prior authority/effect boundaries remain controlling.

Paper remains blocked independently by the unreviewed upstream Paper schema pin; no native boards 12–16 were created in this slice. Crypto #7645 and shared-theme #7849 custody were not touched.

MISSION_COMPLETE: false
Current child capability: BUILT_NOT_PROVEN on production route; controlled generated-route proof is strong, but exact-head PR CI/fences and deployment/live-route proof remain before production acceptance.
Exact next action: publish this commit plus durable record, consume exact-head #8050 CI/fences, then continue the independent H5 canonical Crypto-budget authority/data-qualification lane while Paper remains blocked.

## Current continuation frontier — 2026-09-28 Pro / H5 partial-data readiness

MISSION_COMPLETE: false
FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
Capability state: BUILT_NOT_PROVEN on the production route.

Mission remains the Chairman's Crypto/Bitcoin redesign and production-readiness commission: sophisticated chart-led research with an immediately understandable first read, clear evidence and dependable failure states. This turn continued the already-authorized H5 source/presentation lane; it did not recreate approved design work or add a second model, publication or lifecycle owner.

Current protected law: Mastermind `dcc4829a811d3f6e4fe8c16a103f813c3501f48e`; INDEX `94d1af402598894372858793a5b1931019c5fa77`; Skillpack 1.0.1/bootstrap 1. Same source/carrier: Macro PR #8050, `sol/crypto-vector-r2-20260926`, M2 Studio Direct, owned sparse workspace. Requested working profile is Pro; no mode switch or hidden health telemetry is asserted. Direct duty: PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD for the tightly coupled failure-semantics/source/browser repair.

Recovery reconciled clean local/remote `e6cb197c087e9783ddbefbabf51ff2bb88125acf`, which already included H5 current-page unavailable handling. That accepted work was preserved. Its fences `36358298342` passed, but CI `36358298580` failed validated-claims-source on a single unsupported Chinese validation claim in H5 recovery text. This claim is corrected with an actual scanner regression, not an allowlist or weaker check.

Material source effects:
- `2bfa46242f782c11376733d8795fd90b16bc84ca`: a valid total budget remains known when only the asset breakdown is missing; invalid/stale targets remain suppressed; valid zero remains all-cash without requiring class inputs. Malformed numeric representations and invalid split weights do not turn into displayed authority. The UI distinguishes available, breakdown-unavailable and unavailable, explains the specific reason, and preserves other research.
- `f9e5506a8aef5fdf3fe14bcb404d20cd77a09ebb`: fixes genuine 320px inner-card overflow and improves H5 explanatory typography/stacked mobile hierarchy.
- `d079adb6d532b7af20a487bd0ebdeddc3a414ee0`: final source identity, also moves the H5 CSS insertion away from #7645's Market Board insertion point. Exact three-way simulation has zero conflict markers and retains both H5 and accessible H2. No shared theme or H1/H2 change.

Proof: 167 combined existing Vector/Crypto tests pass; the source validation-claim gate passes; design ratchet has zero new blockers; visual-evidence gate passes; Python/Jinja/diff checks pass. The first browser run found two real compact-card failures despite zero page-wide scrolling. After repair and final-source regeneration, all 112 semantic/geometry cells pass (seven scenarios × four widths × two themes × two languages), with H5/H6 preserved, correct state semantics, no page JS error, no H5/document overflow and measured explanatory text >=14px. The existing capture owner produced forty state screenshots; their hashes are verified. Warnings and fixture-only network/resource gaps remain explicitly recorded.

Evidence and detailed semantics are under the existing `mockups/evidence/crypto-h5-authority-20260927/` owner and `agentos/decisions/DEC-CRYPTO-H5-BTC-BUDGET-AUTHORITY.md`; use `proof_summary.json` for exact source hashes and reproduction limits. These are controlled generated-route tests, not deployed-route/font-parity or participant-usability acceptance. No live alert, saved review, trade, deployment, worker or watcher was started. The two pre-existing loopback fixture servers are not a claimed autonomous continuation.

DO_NOT_REDO: rejected R1; accepted P0A model authority; R2 native boards 01–11; approved Vector in-page Brain entry; current CI enrollment; H5 canonical-budget seam and now-reviewed failure-state layout. Supporting Crypto boards 12–16 remain NOT_APPLIED_TO_PAPER from earlier work. Paper's last known schema hold was not re-probed or bypassed during this source turn; no new Paper effect is claimed. Earlier action-specific denials remain scoped and are not cleared by the user naming Pro.

Unresolved scope: exact-new-head CI/fences; independent release acceptance/order and combined-source regeneration with #7645; deployed-route/font-resource proof; broader Market Board/data-qualification and Crypto shell polish; actual saved-review/alert integration; participant comprehension testing; lawful Paper write qualification. No pending modifying effect is known EFFECT_UNKNOWN. The previous whole-file #7645 hold is superseded only by exact H5 source coexistence; no claim of peer merge or deployment.

Natural continuation boundary: the current H5 partial-data/compact-layout batch is implemented, regression-tested, generated-route tested and visually evidenced. The next substantive unit crosses into candidate acceptance and combined release/integration proof rather than another redraw of the same H5 states. Exact next action: read this frontier and current PR #8050 head, consume its exact CI/fence return, repair only evidence-backed failures on the incumbent branch, and then follow the existing release owner to reconcile #7645/source generation and verify the deployed Crypto route. Pro remains suitable for that adjudication; choose an execution profile only when a concrete build task materially benefits. No autonomous wake or custody transfer is implied.

## Working continuation — 2026-09-28 / Market Board snapshot integrity

Current Chairman instruction continues the same production-readiness commission. Protected Mastermind pin `17fc8c67142ca865c5d34360c1dbbdb73bb5e993`, INDEX `94d1af402598894372858793a5b1931019c5fa77`, compatible 1.0.1/bootstrap 1; ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT loaded from the same pin. Same incumbent M2 Studio Direct workspace and operation; no new worker or carrier. Direct ownership is PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD for the coupled snapshot, explanation and release-integrity question.

Recovered clean local/remote candidate `9e30dd81504da62b228fffd2cbf6306c57040da3`. Its exact CI `36383857728` and fences `36383857383` both concluded success. This is candidate-check acceptance only, not merge/deployment. Preserve the completed H5 and Vector Brain work.

### Investigative result and implemented delta

The old loader reproduced 50 displayed rows spanning 2026-09-01/05/22/26, while the source store held exactly 50 current 26-Sep observations plus 17 older assets. DARK/POLYDOGE's extreme displayed returns were older CoinPaprika observations at stale ranks, displacing current observations on truncation. Missing 30-day returns also counted as nonpositive via `or 0`; deeper price histories extended beyond dated snapshots and were sometimes mislabeled 90D. Those are display/data-integrity failures, not evidence of market direction or fraud.

Source commit `31a60448e058f09b5cea4795cb4bdcfc3f7cfcba` repairs the existing universe owner and its real Crypto consumer:
- `load_universe_snapshot` selects one latest recorded cross-section and retains exclusions; the existing `load_universe` is only a compatibility projection of that owner. Older, future-dated, unreadable, invalid-rank or invalid-latest-price records cannot be rescued into current ranked rows. No parquet or collector was modified.
- Missing return values are excluded from breadth rather than treated as losses. The original ten-asset minimum and history-coverage requirement remain. A real zero remains measurable and different from unavailable.
- Histories restart on unqualified source/asset-ID changes rather than stitching a reused ticker. Deep BTC/ETH/SOL price histories stop at the row cutoff and label their actual recorded length.
- The page adds a dated Market Board coverage disclosure with source/date/reason per exclusion and explicit return-count semantics. It is not a Bitcoin-relative or altseason score. Empty and insufficient-coverage states preserve the rest of the page. Live quote cells are explicitly separate from ranked snapshot context.
- Existing `crypto.class_state/v1` carries the additive coverage receipt; no parallel store, strategy score, allocation model, watcher or notification owner exists.

Actual recorded-data result: all 50 ranks now belong to 2026-09-26, ordered 1–50; 17 older observations remain inspectable but do not fill ranks. All 67 input parquet hashes were unchanged before/after real builds. After honest source-identity continuity checks, only three assets meet the existing breadth-history requirement, so breadth is unavailable rather than an invented bullish/bearish percentage. No arbitrary maximum-return clamp or backfilled history was introduced.

### Integration and verification

TDD reproduced the stale-rank displacement, null-as-loss denominator, invalid-latest-price rescue, date leakage, identity stitching and future-date poisoning before repair. The full real builder test also caught a Jinja/CSS `{#` collision during implementation; it was corrected, not bypassed. Combined existing Vector and Crypto suites: **182 passed**, with the same 25 pre-existing warnings. Source-claim checker, Python compile, design-system ratchet and diff check pass; no validation allowlist was changed.

Exact three-way source simulation with #7645 `74298e32bbbbc7f00884ece259455b9bbe46fd6f`, common base `2b62f49603e731daf68877516d3f6f748497b160`, auto-merges with zero markers. The snapshot disclosure was moved outside the peer's header/table hunk after the first simulation exposed that insertion conflict. Peer row accessibility/CSS and our H5 state projection remain intact. This is combined-source proof, not permission to deploy peer generated bytes.

The actual builder produced four controlled routes: stored snapshot, no snapshot, missing returns, and the exact three-way combined template. Browser matrix **64/64** passes at 320/390/768/1440 × EN/ZH × dark/light: all governed shelves retained, exact date/count membership, no stale outliers in ranked rows, visible exclusions, correct unavailable semantics, native Enter-open disclosure, open state preserved on language change, no document/disclosure overflow, minimum 14px reading text and a 44px summary target. Existing `crypto.class_state/v1` schema validates all four actual builder outputs. The verifier now waits for the existing theme flourish to finish rather than capturing its transient sun/moon overlay or hiding it.

Canonical capture owner produced **32/32** REST states and every PNG digest was checked. Expanded desktop and Chinese-mobile disclosure crops were visually reviewed. Evidence: `mockups/evidence/crypto-universe-snapshot-20260928/` includes the EVIDENCE.yml receipt, source/combined/input hashes, semantic matrix, canonical manifest, merge review and exact reproduction scripts. Nine canonical repository font assets were used locally (not included as shared evidence); semantic tests have zero failed font requests. The bounded fixture still lacks favicon/live quote/overlay and one navigation-script request, and retains those errors; no complete live-shell/network acceptance is claimed. The shared floating Crypto Brain control remains visible and was not changed in this data slice.

### Current continuation

MISSION_COMPLETE: false
FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
Capability: BUILT_NOT_PROVEN on the production route.
The coherent snapshot-integrity batch is implemented, unit-tested, generated-route tested and proven to coexist with #7645. The next substantive phase is exact-new-candidate acceptance and release/integration adjudication, not another redraw or rerun of this unchanged snapshot workflow. The earlier 9e30dd8 checks are green; they do not assert the new candidate's CI status.

DO_NOT_REDO: accepted P0A; H5 current/zero/partial-state handling; approved Vector Brain entry; R2 native boards 01–11; old recovered research; newly verified snapshot/coverage logic. Paper's last-known schema qualification hold was not retried this turn; supporting boards 12–16 remain NOT_APPLIED_TO_PAPER. All material source/evidence effects are reconciled. No new server, worker, review save, alert, trade, merge or deployment was started; existing loopback servers are fixture infrastructure, not an autonomous continuation. Earlier action-specific denials remain scoped and effective.

Exact next action: recover this record and PR #8050's current head, consume matching CI/fences, then follow the existing release owner to reconcile source ordering with #7645, regenerate the combined site and verify the deployed route. Independent remaining product gaps include floating Crypto Brain obstruction, broader chart-led Crypto front-door integration, source/venue qualification beyond this snapshot fix, actual saved-review/Alert Center integration, and participant comprehension tests. Do not treat a code merge or these controlled screenshots as the whole production outcome. Same incumbent carrier/custody; Pro working profile retained without any asserted model or UI-mode switch.

## Current frontier — 2026-09-28 / Chairman commissions Crypto science

This section supersedes the previous next-action priority only: the Chairman explicitly adds deep scientific research on Crypto drivers, short/medium/long pivots, washouts, tops/bottoms, rapid de-risk/re-entry and the incumbent Bitcoin models. Existing design/source results and all release/authority gates remain intact. This is a research track within WS:CRYPTO-INTELLIGENCE, not a new strategy, runtime or portfolio owner.

Protected Mastermind pin: `5c6b010a6157895d4f697548c75263cdff641ea6`; INDEX `94d1af402598894372858793a5b1931019c5fa77`; compatible Skillpack 1.0.1/bootstrap 1. COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT loaded at that same pin. Same M2 Studio Direct carrier and existing branch/workspace; direct duty is PRINCIPAL_JUDGMENT for causal validity and the research loss function. No delegated worker, provider credential/action, new paid source or watcher was started.

Recovered head `0c252f0befaa0891a9666949835cab8e9d27f3ba`; observed main `03e8961d22b48cc65666f6318ee8c8bd610f3caa`; principal BTC signals/inputs/overrides/radar/config paths agree across those refs. Preregistration was committed at `47d4eacf6abd98055a085a779e9df75fee567d18` BEFORE the new temporal tests. Exact specification: `research/CRYPTO_SCIENCE_R1_AUDIT_PREREG_2026-09-28.md`.

### Material scientific results

1. Prefix invariance failed in the incumbent `btc_signals.bottom_pressure`: all 366 daily cutoffs from 2025-09-26 to 2026-09-26 were checked, with 3 changed dates (2026-05-20, 05-21 and 07-01), max absolute 0.0930232558 on its 0–1 scale. The three-day resampling labels can assign later closes to earlier timestamps. A research-only completed-date counterfactual and price-only momentum/risk controls each had 0 changed dates. Controls do not certify non-price vintages.
2. With all other stored allocation inputs fixed, the prefix-only bottom-pressure altered one day's raw allocation in each variant by at most 5.3156146 percentage points. This is sensitivity, not a live-trade error, PnL loss, entire-engine replay or proof that historical profit is inflated. No production function or config was changed.
3. A later, explicitly exploratory synthetic probe found the current impulse evaluator counts immature future outcomes as boolean False. Eight rows provide five mature three-day windows, but the label helper returns eight non-null booleans; the last three unavailable outcomes are not masked. The old forward-window formula in the research prose is stale and already corrected in current code; only the maturity-mask defect is attributed to current implementation. No falsifier gate was written.
4. The source audit distinguishes the daily momentum/stress/valuation/conviction/brake/bottom-overlay path from short-lived impulse context and final DecisionState. Current midterm blackout is disabled/retired, not a live cycle-timing authority. MVRV and derived NUPL are not independent votes. Prior six re-entry candidates failed their report's preregistered acceptance bar; earlier premium/candle-flow and macro-gating failures remain constraints, not new measured results.
5. Actual data are heterogeneous: 4,393 daily signal rows/197 fields, 94,063 hourly BTC candles, 2,957 actual OKX taker-flow hours, 89 options-structure snapshots, ETF history only from 2024. Timestamp gaps and missing publication-vintage clocks must precede any immediate-timing claim. The initially guessed `taker_volume_1h` filename was absent; the actual owner path `taker_volume_hourly` exists. Do not claim real order-flow data are absent.

### Evidence and verification

`research/crypto_science/` contains the executable audit, all 366 cutoff records, metadata/source/input digests and the exploratory label reproduction. Current audit JSON SHA256 `f521c10e927f174d9dc215458da59340e5b84e9f02a7f35d1ed910e757903836`. Eleven input and seven principal source hashes were unchanged. Both the initial and technical-amendment variants are retained: pandas 3.0.5 ignored `origin` for the counterfactual's `3D`; replacing it with fixed-origin `72h` reproduced exactly the same result without the warning. This was a disclosed post-run harness correction, not a new economic test or retuned strategy. Full cutoff CSVs are byte-identical.

The label probe was rerun and reproduced 5 mature versus 8 non-null labels. Python compile, result consistency, source/input hash checks and git diff checks passed. These are diagnostic reproduction checks, not a passing scientific forecasting model or a complete repository test suite. No new PnL, accuracy percentage or strategy backtest was claimed.

The research synthesis `research/CRYPTO_SCIENCE_R1_FINDINGS_AND_PROGRAMME_2026-09-28.md` records actual results, incumbent mechanics, prior rejected hypotheses, primary-source mechanism evidence, four forecast jobs, data availability requirements, event-level/latency/cost calibration and promotion gates. Public primary sources were reviewed via their author abstracts/summaries and official docs; not claimed replicated. The distinction between causal mechanism, predictive association and profitable decision is load-bearing.

### Research ruling and continuation

Affected historical-alpha claims cannot support stronger policy promotion until the temporal/label defects are repaired and the baseline replayed. This does not order a live liquidation, alter current model allocation or globally reject unrelated data. Research, alert eligibility and final sizing remain distinct. P0A/P0B, prior H5/snapshot/Brain results and implementation paths remain unchanged.

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
R1 bounded outcome: substantive source/data audit, preregistered temporal experiment, sensitivity check, exploratory label probe, mechanism synthesis and staged scientific programme complete. Scientific forecasting improvement and parent production mission remain unproven/incomplete.

Natural boundary: the next unit is a separately reviewed production-source correction plus full availability-qualified baseline replay, not another audit summary or unrestricted feature search. Preserve all initial evidence before that heavier unit. Exact next action: recover this record and the current #8050 branch; review/fix higher-timeframe aggregation and immature-label masking through existing engine/test owners, extend temporal and publication-time checks, then reproduce incumbent and previously qualified impulse baselines before preregistering one fast downside and one recovery experiment. Pro remains the requested working profile; no mode self-switch, served-identity inference or future daemon is implied.

DO_NOT_REDO: the existing accepted UI/failure-state work, retired calendar veto, already recorded research failures, or the now-reproduced R1 diagnostics without a source/input/definition change. Prior 2024+ holdouts are already used and cannot be renamed untouched. Do not promote the research-only 72h counterfactual or add a new allocation/gate/ledger owner. No pending effect is known EFFECT_UNKNOWN; all current changes are research and existing Agent OS continuity only.
