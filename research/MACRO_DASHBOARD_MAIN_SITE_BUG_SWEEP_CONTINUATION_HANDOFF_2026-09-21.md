# Macro Dashboard main-site bug sweep — continuation handoff — 2026-09-21

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION  
MISSION_COMPLETE: false  
Operation: `macro-dashboard-main-site-bug-sweep-checkpoint-20260921-sol-001`  
Protected procedure: `mastermindx-market-intelligence/Mastermind@4ca1b97e65de9d4ba8c868b9d708fb7620a8a76f` / `mastermind.sol_skillpack.v1` 1.0.1 / bootstrap major 1  
Checkpoint carrier: `sol/macro-dashboard-main-site-bug-sweep-checkpoint-20260921`  
Checkpoint base: Macro `main@7c6e35163c9f67087ffe174a7ab3810f47ce6a45`

## Mission

Continue the Chairman-directed audit and repair of the Terminal-integrated primary Macro dashboard and its immediate supporting surfaces. Fix real bugs, UI inconsistencies, stale projections, and truth-boundary defects without creating a second dashboard, CI plane, publisher, identity system, or replacement carrier.

This checkpoint is organizational continuity only. It does not transfer source custody from the existing product PRs and does not make any open implementation accepted, merged, deployed, or production-proven.

## Capability delta at this boundary

Before this audit, the primary Macro route could stack a second UD-B1 decision surface above the established US dashboard, report missing/blocked health evidence as healthy, describe concentrated Risk-on without participation qualification, expose a stale Terminal Macro preview link, and compress tablet decision content behind ellipses / a fixed Brain launcher.

At this boundary:

- Primary-route composition + health truth are **PROVEN_LIVE** through merged Macro PR #7503.
- Terminal's Macro preview symlink is repaired on current Terminal `master`.
- Participation-aware Risk-on exists on PR #7505 but is **NOT ACCEPTED**: exact-head CI is green, while a later Sol review found two semantic/runtime blockers and requested changes.
- Tablet readability is implemented on PR #7626 with local browser proof, but remains **BUILT_NOT_PROVEN** because hosted CI is red on one candidate-introduced asset-fingerprint mismatch; the other two reds reproduce on its tested base and were repaired separately on newer main.

## Exact carriers and current truth

### Macro PR #7503 — primary composition + health truth

- State: **MERGED / PROVEN_LIVE / DO_NOT_REDO**.
- Final PR head: `d1586a7f49a77519ceb40f27842499ff989816fd`.
- Merge commit: `c125178ed4e146e4cc15a4caa5586c790df0a13d`.
- Accepted user-facing contract:
  - no `#ud-hero` on primary `macro.html`;
  - one established `#regime-radar` as first primary decision surface;
  - zero observed health entries => unavailable/unknown, never green;
  - all observed entries OK => observed healthy / green;
  - actionable unhealthy => warning;
  - blocked-only or OK+blocked => neutral / no active failures, not "all observed sources OK".
- Public acceptance receipt: PR #7503 comment `5762130416` records VPS checkout at the merge commit, atomically served `macro.html` byte-identical to checkout (SHA-256 `f4c743bdd0ba1a21c1c4935825f19ec66f18e47276f049eda6719be3693b242d`), public HTTP 200, Chromium-visible single `#regime-radar`, and `#ud-hero=0`.
- The later Market Memory W2C canary failure happened after atomic publication and is separate; #7503 is not effect-unknown.

### Macro PR #7505 — participation-aware Risk-on

- State: **OPEN / BUILT_NOT_PROVEN / REQUEST_CHANGES**.
- Exact head: `81f6a7f76afdc757dc84997f486f4739ce50ae6b`.
- Exact-head hosted proof currently green:
  - fences run `35658489371`: success;
  - CI run `35658489660`: success.
- Current-main direct-path overlap from the original base remains only `.github/ci/legacy-jobs.yml`; do not manufacture an ancestry-only merge merely to make `behind=0`.
- Binding later review: PR review `5272185887` is **REQUEST_CHANGES / FULL_REREVIEW_REQUIRED**.
- BLOCKER 1: `engine.market_state._participation_scope()` can promote stale / wrong-session / degraded breadth into "Broad risk-on". Repair must use one engine-owned presentation projector bound to verdict + market + settled `asof` + canonical input vintages + exactly one numeric 0-100 breadth component; require non-stale, non-degraded, same-session evidence or emit participation unverified.
- BLOCKER 2: live/nightly display currently passes reduced verdict blocks that strip `components`, `asof`, `input_vintages`, and `market`; participation therefore degrades to unverified rather than reflecting valid measured breadth. Repair from the actual selected `live_ms` / `nightly_ms` snapshot and the debounced displayed verdict. Browser code must consume the engine-owned presentation object, not duplicate thresholds.
- Coherence requirement: formal score-band word remains exactly Risk-on / Mixed / Risk-off. Participation is descriptive scope, not a fourth verdict. Extend `scripts/check_ms_board_coherence.py` to parse qualified/styled Risk-on thesis copy without widening score-band vocabulary.
- Required discriminators include stale=true, input-vintage mismatch, degraded breadth, duplicate/missing breadth, valid 0/50/75 cases, weak/supportive nightly and live display, pending/debounced mismatch, and legacy-payload fallback.
- Frozen boundary: no score weights/thresholds, Risk Radar authority, Prophet ranking, sizing, trade gate, or non-US authority changes. Do not merge #7515 or #7528 as parallel implementations.

### Macro PR #7626 — tablet dashboard readability

- Carrier: `claude/macro-dashboard-main-bug-sweep-20260921`.
- Exact head: `64e4f946cc235d9703aecd1ce84b4b058f81b08c`.
- State: **OPEN / BUILT_NOT_PROVEN**.
- Local exact-head proof:
  - template/site asset syntax checks pass;
  - template↔site sync: 99 pairs OK;
  - integrated dashboard/navigation subset: 226 passed, 1 skipped, 1 deselected;
  - Chromium: 1440 full labelled Brain launcher; 820px 56px accessible orb + all eight volatility-weather labels readable + no document overflow; 390px 56px orb + no document overflow; no page errors / duplicate IDs / broken fragment targets.
- Hosted:
  - fences run `35598768447`: success;
  - CI run `35598769064`: failure;
  - `contract-delta`: success.
- Candidate-introduced hosted red:
  - `research-screener` / `tests/test_research_screener.py::test_fresh_bake_matches_committed_site_html`;
  - changing `theme.css` changed its asset fingerprint while committed `site/research_screener.html` retained the old fingerprint;
  - base replay on `57ccf27b67a861459330647e034a308ef9148360` passed this suite.
- Inherited-at-that-base reds:
  - Glossary alert-banner committed page test;
  - Bonds stylesheet fingerprint test;
  - both reproduced on the tested base. Later current-main repair #7613 fixed the inherited Glossary/Bonds contract failures; do not patch those into #7626 unless a fresh current-base run proves they remain.
- Do not blindly rerun the old CI. Reconcile the same carrier onto current source first, then regenerate affected committed assets through the incumbent builder/asset-optimizer path.

### Terminal preview integration

- Current Terminal `master@5fee4ab7517095c04a1fbab17c6b273826fd6446`.
- `macro-site-link` now points to `/Users/chriswong/Documents/Cluade/macro-main/site`.
- Repair commit: `749576c537284df43772d3cfd3fdd75ad7194a2d` — `fix(dev): repair macro dashboard preview link (#700)`.
- This repair is merged/current and **DO_NOT_REDO**.

## DO_NOT_REDO / preserved ownership

- Do not remount UD-B1 on the primary US Macro route or call the default US `market_state` a global score.
- Do not weaken the #7503 health partition.
- Do not recreate the Terminal preview-link repair.
- Keep #7505 as the sole participation implementation carrier; do not replace it with #7515/#7528 or another PR.
- Keep #7626 on its existing tablet carrier; do not create a replacement tablet-readability PR.
- Do not create another CI job/control plane for either repair; use existing owners.
- Do not treat green CI as acceptance when a later semantic review is red.
- Do not blind-rerun #7626's obsolete red before reconciling source/base and regenerating the stale committed fingerprint.
- Separate global-regime relocation carriers (#7594 / #7635) are outside this bug-sweep continuation; do not absorb or overwrite them.

## EFFECT_UNKNOWN

None at this checkpoint. The records-only checkpoint branch was created successfully from the exact Macro main listed above. No ambiguous product mutation, merge, deployment, or production write is carried into the next session.

## Exact next actions

1. **Primary next action — repair #7505 on its existing carrier.**
   - Re-pin protected procedure and current Macro `main`.
   - Reconcile the one intersecting CI-manifest path plus governing dependencies without ancestry-only churn.
   - Implement the two review blockers and coherence-guard change on the same #7505 branch.
   - Add the discriminating RED→GREEN cases named above.
   - Obtain full rereview on the new exact head and fresh exact-head hosted fences/CI.
   - Only after review PASS + current integration proof may the existing release path merge, publish, and browser-prove static + live selective/broad participation behavior.

2. **Then repair #7626 on its existing carrier.**
   - Re-pin current main and reconcile the branch, preserving its tablet CSS/Brain behavior.
   - Bring in the current-main inherited Glossary/Bonds repairs rather than duplicating them.
   - Regenerate the affected committed static assets through the incumbent builder/optimizer so `site/research_screener.html` carries the current `theme.css` fingerprint.
   - Run the focused research-screener + tablet/readability + template/site-sync checks, push the same branch, and require fresh hosted CI.
   - After lawful merge/publication, prove the real public Macro route at 820px: eight readable weather labels, 56px accessible Brain orb, no horizontal overflow, no page errors; retain 1440 and 390 behavior.

3. Resume the broader dashboard bug sweep only after these two existing carriers are reconciled/released or explicitly held, so new shared-dashboard work does not collide with unfinished source truth.

## Resume instruction

> Continue the Macro-dashboard main-site bug sweep from `research/MACRO_DASHBOARD_MAIN_SITE_BUG_SWEEP_CONTINUATION_HANDOFF_2026-09-21.md`. Re-pin protected procedure and current sources first. Start with the existing #7505 carrier and its REQUEST_CHANGES blockers; do not redo #7503 or the Terminal preview-link repair.
