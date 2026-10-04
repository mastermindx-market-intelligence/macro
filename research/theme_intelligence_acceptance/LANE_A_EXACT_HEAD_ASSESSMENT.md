# Lane A Exact-Head Independent Acceptance

**Lane F operation:** `theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001`
**Candidate operation:** `theme-intelligence-a-integration-and-semantic-repair-20260919-sol-001`
**Carrier reviewed:** Macro Draft/HOLD PR #7526
**Candidate head:** `23c6e6cccb42fa28fce09b8483802560f0b11998`
**Candidate tree:** `332c73d175704b859efc36f71e1bc1ef0323e8aa`
**Verdict:** `REQUEST_CHANGES`
**GitHub review:** `5260472945`

## Positive evidence independently reproduced

- Focused owner suites: **112 passed, 1 deselected**.
- Real producer → ThemeState/thesis → Theme Tracker build completed.
- Real AI Semiconductors input now produces `ai_semi_f2=ARMED` with `WATCH_WITHOUT_INDEPENDENT_DETERIORATION`.
- The real AI card renders lane `early` with `data-fired=0`.
- Medical Devices clean `PRECIPICE` renders `early`.
- rank/gate/size/escalate/trade authority remains false.

The two original incident repairs materially advance the product. They do not yet clear exact-head acceptance.

## BLOCKER — TI-A-CLOCK-001: observation clock is fabricated from build time

On the exact-head real build:

- Foresight owner observation: `asof=2026-09-18`.
- generated ThemeState/asymmetry snapshot: `as_of=2026-09-20`.
- `theme_intelligence.consumer.v1.clocks.observation=2026-09-20`.
- its snapshot watermark is also `2026-09-20`.

`_consumer_contract_row` assigns `snapshot_asof` directly to the observation clock. A weekend rebuild can therefore make a September 18 market observation appear newly observed on September 20.

**Required repair:** preserve the owner observation separately from snapshot/computation/publication clocks. Add a discriminator that rebuilds a 2026-09-18 owner observation on 2026-09-20 and requires observation to remain 2026-09-18.

## BLOCKER — TI-A-TRANSITION-002: ACCELERATING → GLUT-RISK false negative

The current registry accepts `RE-RATING`, `BROADENING`, `PRECIPICE`, and `WATCH` as prior stages for `GLUT-RISK`, but omits `ACCELERATING` even though Lane A's lifecycle places ACCELERATING immediately before GLUT-RISK.

Direct calls to the exact production evaluator show:

| Prior → current | Result |
|---|---|
| ACCELERATING → GLUT-RISK / LOOSE | `ARMED / REQUIRED_PREDECESSOR_NOT_PRESENT` |
| BROADENING → GLUT-RISK / LOOSE | `FIRED / STAGE_REGRESSION_WITH_ECONOMIC_DETERIORATION` |
| WATCH → GLUT-RISK / LOOSE | `FIRED / STAGE_REGRESSION_WITH_ECONOMIC_DETERIORATION` |
| RE-RATING → WATCH / NEUTRAL | `ARMED / WATCH_WITHOUT_INDEPENDENT_DETERIORATION` |
| RE-RATING → WATCH / LOOSE | `FIRED / STAGE_REGRESSION_WITH_ECONOMIC_DETERIORATION` |

The WATCH repair is correct, but the broader predecessor matrix is internally inconsistent and can miss the most natural mature-to-glut deterioration.

**Required repair:** adjudicate the full predecessor/target transition contract and add a matrix regression. If GLUT-RISK represents deterioration from the mature lifecycle, ACCELERATING must be accepted as a predecessor.

## BLOCKER — TI-A-CI-003: candidate-introduced contract-delta

Hosted CI run `35506191551` reports:

`unrun-subsector-themes` now reaches `site/basketdata/foresight_cascade.json`, but the existing job's declared `paths:` does not cover that artifact.

The contract gate reports **1 introduced, 1 inherited**. The separate `research-screener` fresh-bake failure in pack 8 is not attributed to Lane A.

**Required repair:** widen the existing owning job's scope through Lane A's single coordinated package CI edit. Do not create another CI job or test authority.

## Acceptance state

Lane A is **BUILT_NOT_PROVEN / REQUEST_CHANGES**.

Fences `35506191383` are green. Hosted CI `35506191551` is red. No formal product acceptance, merge, deployment, publication, or deployed-browser parity is claimed.

## Exact repair-and-return requirement

Repair only the three bounded blockers on the same PR #7526 carrier. Preserve:

- WATCH alone as non-deterioration;
- real WATCH+LOOSE and legitimate GLUT deterioration;
- clean PRECIPICE as early;
- distinct dated observations and same-date correction supersession;
- stable thesis identities;
- additive `theme_lanes.v1` compatibility;
- all-false rank/gate/size/escalate/trade authority.

Return the new immutable head. Lane F will rerun the real path, clock discriminator, transition matrix, CI ownership, and current-main integration without reopening unrelated architecture.
