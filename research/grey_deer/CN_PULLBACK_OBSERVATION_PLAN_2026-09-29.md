# China pullback observation — implementation plan

## 0. Acceptance and scope
Chairman commission: assess, design and implement the pullback-risk → actual-pullback experience end to end, with advanced, beautiful illustrations. This slice completes the motivating China dashboard path; it does not retune US/HK/CA models or authorize trades.
Operation: `cn-pullback-lifecycle-20260929-sol-001`. Source carrier: Studio Direct, isolated registered SSD workspace, branch `claude/ssd-cn-pullback-lifecycle-20260929-68e848e41de4db74`.
Protected law: Mastermind `9b01b708551196b1f144aa2f98b48bf37f513e26`; INDEX blob `94d1af402598894372858793a5b1931019c5fa77`; skillpack 1.0.1/bootstrap 1. Macro base: `650e2ebbe08046bedf10e7eec39def3f62073103`.
Done requires exact-candidate tests, bilingual dual-theme desktop/mobile browser evidence, independent review, normal concluded-check merge, landed-byte reconciliation, and real served-page proof. Built/merged/rendered/live remain separate facts.

## 1. Assessment and preserved work
- The China rack and hero hard-code Pullback Risk. The rack disappears when the forecast is quiet, even if prices are declining. Its 98/100 is not proof that an event has begun.
- `china_inputs.build_features()` forward-fills price and breadth inputs. The observation must instead read actual `store.read("china", ticker)` closes without filling missing sessions.
- Stored September 29 closes at the source pin: Shanghai 3817.145 vs recent 63-close high 4043.643; CSI 300 ETF proxy 4.405 vs 4.916; Shenzhen 12883.514 vs 15597.510. These are stored observations, not a production verification receipt.
- The international audit grades future minimum close relative to the forecast-reference close. Existing odds are NOT an estimate of remaining loss from an episode peak. Do not rename them continuation/retest probability.
- Preserve accepted replay parity, missing-evidence safety, risk scores, ceilings, forecast horizons, capital policy, Prophet ranking and all forward ledgers.
- PR #7875 is a separate held semantics carrier with dirty local work; #7592 owns breadth/null repairs. Do not edit their workspaces, merge their holds, or claim their work. New observation/presentation code is separate; integration must preserve their independent semantics and receive conflict review.

## 2. Observation contract, frozen before implementation
The producer is a deterministic display projection inside the existing China Market State artifact, not a new forecast, policy, ledger or event database. Primary basis: Shanghai closing index; other CN_PROFILE indices provide explicitly labelled index confirmation, not stock-market breadth. The CSI 300 ETF is labelled as a proxy.
Use the exchange's expected settled session and raw source dates. Reject invalid/nonpositive/nonfinite closes, conflicting duplicate dates and incomplete current observations; exclude future/intraday rows. Missing sessions reset persistence counters, never manufacture stability.
A new decline uses the latest closing high in the preceding 63 actual closes. Onset requires two consecutive settled closes at least 2% below the same reference, or one close at least 5% below it. These are versioned descriptive rules, not statistically promoted thresholds. The risk score cannot start or end an observed decline.
Freeze the peak reference within the down-leg. Stabilizing requires at least three observed sessions without a new low plus a close above its five-close average. Recovering requires five consecutive closes above the 20-close average, a rising 20-close average, and ten observed sessions without a new low. Both remain observations, not policy recovery confirmation or entry permission.
Resolve the down-leg only by two consecutive closes reclaiming its peak, or a separately named trend repair: twenty consecutive closes above the 20-close average, a new 20-close high, and at least 21 observed sessions since the low. The latter does not claim the old high was recovered. A rolling peak aging out is never resolution. A failed repair remains the same down-leg.
Publish price phase, source/expected dates, frozen peak/low, actual drawdown, observed-close count, measured loss recovered, source digest, index-confirmation coverage and a bounded reconstructed price timeline. Never invent a prior issued warning or first-known timestamp from reconstructed history. Chronicle/Reflex/QLedger remain the durable history owners.

## 3. User experience and illustrations
One view model drives hero entry, rack tile and existing Risk Radar dialog. Active declines remain visible even with a quiet forecast. Delayed observations cannot appear current or safe. Keep settled-price and intraday Market State clocks visibly separate.
Active headline: Pullback underway / Stabilizing / Recovering. The primary number becomes actual drawdown, with its benchmark and peak basis. Forecast score/odds retain their original meaning below the observation or in detail.
Use shared Signal Ink (`lib.illus`) for the real underwater close path; add a measured trough-to-peak recovery ruler and a compact, dated price-event rail. No fabricated forecast cone, fake data, probability-as-progress, new chart library or looping live pulse. Reconstructed dates are labelled as such.
DARK TREATMENT: graphite material, restrained directional ink and a quiet underwater veil. LIGHT TREATMENT: white research card, crisp hairlines, softer fill, shadow instead of glow. Both use the existing theme tokens and direction/language convention.
Glance tier stays compact: one dominant read, one plain meaning, one action/observation limit. Mechanics and rule thresholds live in the existing detail journey. EN/ZH parity, keyboard operation, visible focus and reduced-motion behavior are required.

## 4. Execution and proof
1. Build pure raw-close observation and tests: high risk/flat tape; low risk/crash; missing/stale/future/conflicting data; gap reset; failed rebound; frozen anchor; peak-age trap; partial repair; exact resolution; replay-prefix causality and input immutability.
2. Build the canonical token-based card/detail partial and synthetic visual preview before integration. Preview data is explicitly illustrative, never live evidence.
3. Attach the JSON projection before existing Market State persistence; render the same object on all China entry points. Do not change the existing forecast producer or publish a second data feed.
4. Test actual template integration, real stored-input render, generated asset parity, dark/light × EN/ZH × 1440/390 browser matrix, dialog/keyboard/reduced-motion/degraded cases and payload/DOM consistency. Record any integration conflict instead of replacing held work.
5. Freeze candidate; obtain independent review; finish normal CI/merge/render/VPS publication and exact real-route verification. Never bypass checks or use Vercel.

## Frontier
CURRENT_CRITICAL_DEPENDENCY: implement and verify the raw-close observation contract.
ACTIVE_PHASE: observation and visual build. MISSION_COMPLETE: false.
LAST_DURABLE_EFFECT: registered isolated workspace; plan source written. No runtime dispatch, forecast change, policy change or production change.

## Observation checkpoint — implementation evidence
- `python3 -m pytest tests/test_pullback_observation.py -q --tb=short`: 29 passed (2.80 s; process 91694, exit 0). The 43 warnings were pre-existing pytest temporary-browser cleanup warnings, not feature failures; subsequent tests use an operation-owned temporary root.
- A first real-input probe found eight archival calendar disagreements for Shanghai/Shenzhen and one for the ETF, most recently 2014-01-30. The house calendar describes itself as approximate. The implementation therefore preserves raw history and reports all disagreements; any disagreement inside the selected chart/reference evidence window blocks the state. It does not silently remove a real source price or let an old conflicted peak escape by aging off the chart. Both directions are tested.
- After explicit trend repair, the next reference starts at the repair close. Otherwise the un-reclaimed old peak would immediately mint a false second pullback during a continuing rally. This is a resolution/re-arm invariant, not a probability or threshold retune.
- Full stored-input replay at the frozen source: Shanghai UNDERWAY, -10.0276% from the frozen 2026-05-13 episode high, versus -5.6013% from the recent 63-close high. CSI 300 ETF proxy -12.1985% from its frozen high; Shenzhen -20.0733%. These distinct references must not be mixed in UI labels. Source processing for all three, including Git reads, took 1.761 s. This remains build evidence, not served-production proof.
- Completed batch: pure observer and 29 contract cases. Next bounded phase: canonical China adapter, measured illustrations and template/real-page proof. Forecast/score/policy producers and all ledgers remain untouched. MISSION_COMPLETE: false.

## Canonical integration + component milestone
- Implemented `lib/china_pullback_view.py`: raw CN_PROFILE stores, explicit Shanghai primary, labelled CSI 300 ETF proxy, per-index source coverage, exchange-owned settlement/expiry clocks, immutable JSON projection. No collector, new data feed, ledger, forecast, score or policy change.
- Connected the same view to the China hero trigger, compact popover, rack tile and existing shared CN Risk Radar dialog. Attached JSON before the single existing CN Market State persist; tests prove exact serialization and no US-path write. Other-country dialog composition remains unchanged.
- Added `templates/_pullback_observation.{html,css,js}.j2`. Real Signal Ink underwater close path, measured trough-to-peak loss-recovery ruler, index-confirmation strip, reconstructed dated price rail and explicit reference-basis table. Forecast intensity/21-session odds remain separate. Missing/stale prices cannot become calm or current; page expiry uses one producer-deadline timer and existing visibility/langchange events, no polling or second state owner.
- Component browser evidence: 8 variants (1440/390 × dark/light × EN/ZH), keyboard method disclosure, 44px targets, source-expiry demotion, no overflow/nonfinite paths/duplicate IDs/runtime exceptions. Captures live at `/Volumes/Mastermind/tmp/cn-pullback-lifecycle-20260929-sol-001/components-v2/`; these are explicitly COMPONENT evidence, not complete-page or deployment proof. Visually inspected dark/light English desktop and dark Chinese mobile.
- The first visual inspection caught absent page-local spacing/radius tokens; fixed with scoped fallbacks matching the existing ramp and China 18px radius. Added computed-padding/radius assertions so a visually collapsed card cannot pass on overflow checks alone. Kept the shared palette unchanged.
- After canonical sparse opt-in for `site` and `data`, the 11-suite integration/regression batch passed: **276 passed in 10.51 s** (Studio process 86469, exit 0). The preceding four failures were only absent sparse site files; no test was suppressed. New three suites are bound to the existing render-guard job, not a new CI plane.
- Executive read-only probe: mode `readonly`, no queued/running jobs; no reviewer child was created or dispatched. Installed Macro identity differs from this implementation base and is not an acceptance receipt.
- MISSION_COMPLETE: false. Next: full stored-input China page render, actual page/modal browser proof, bounded independent review and normal CI/merge/publication. `engine.china_run.run` writes re-derived local regime artifacts even in fast render; any dev-render data effects must be inspected and excluded from the source candidate rather than claimed as no-effect. No production action yet; EFFECT_UNKNOWN: none.
