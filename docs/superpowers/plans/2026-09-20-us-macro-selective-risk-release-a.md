# US Macro Selective Risk-On Release A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the US Macro hero participation-aware without changing Market State scoring or authority.

**Architecture:** Add one pure presentation projection to engine/market_state.py. Static and live consumers use that projection; JavaScript retains only safe legacy fallback copy and never recomputes participation.

**Tech Stack:** Python, Jinja2, plain JavaScript, pytest/Node harnesses.

**Spec:** docs/superpowers/specs/2026-09-20-us-macro-selective-risk-design.md

## Global Constraints

- Preserve score, raw_score, verdict thresholds, caps, Risk Radar authority, history, and Prophet authority.
- US-only participation qualification; do not change CN/HK/CA semantics.
- Reuse pct_above_200 vintage; never invent a session date.
- Preserve template/site byte parity for risk_state_live.js.
- Keep #7060, #7384, #6685, and #7040 ownership boundaries intact.

## Review Focus

- Numeric breadth zero must remain valid weak breadth, not null.
- Stale or wrong-session breadth must produce unverified participation.
- Debounced live verdict must receive copy for the displayed verdict, not the pre-debounce verdict.
- Legacy live payload must never restore the old universal breadth-agreement claim.
- Non-US market snapshots must preserve existing copy.

---

### Task 1: Market State presentation projection

**Files:** Modify engine/market_state.py; Test tests/test_market_score_authority_2026_08_12.py.

**Produces:** _market_presentation(verdict, components, *, asof, input_vintages, market) -> dict | None.

- [ ] Add failing tests for weak/uneven/supportive/unverified breadth, zero handling, MIXED/RISK_OFF precedence, and non-US invariance.
- [ ] Run the focused tests and confirm the new cases fail for the missing projection.
- [ ] Implement the minimal pure projection and attach it to US snapshots.
- [ ] Make US headline_en/headline_zh use the presentation; preserve underlying label/verdict/score.
- [ ] Run focused Market State tests green.

### Task 2: Live transport and browser consumption

**Files:** Modify scripts/build_risk_state.py, templates/risk_state_live.js, site/risk_state_live.js; Test tests/test_risk_state_live_session_floor.py and tests/test_risk_state_live_copy_sync.py.

**Consumes:** _market_presentation from Task 1.

- [ ] Add failing Node-harness tests proving transported Selective risk-on copy paints on a same-session feed and legacy payload uses safe generic copy.
- [ ] Add failing pure-Python assertion that the display projection follows the debounced verdict.
- [ ] Transport presentation in _verdict_block and rebuild display.presentation from the debounced verdict.
- [ ] Patch live JS to prefer display.presentation stance/headline/subline/action and use safe verdict fallback otherwise.
- [ ] Mirror the JS source to site and run the two live suites green.

### Task 3: Static first paint

**Files:** Modify templates/dashboard.html.j2; Test tests/test_risk_state_live_copy_sync.py plus existing dashboard coherence tests.

**Consumes:** market_state.presentation from Task 1.

- [ ] Add failing presence/semantic assertions for presentation-first verdict word, subline, thesis, and action.
- [ ] Render presentation fields when available and safe fallback copy otherwise.
- [ ] Run copy-sync, board-coherence, Market State, and authority suites.
- [ ] Run template/site sync guard for risk_state_live.js.

### Task 4: Integration proof

- [ ] Run the full targeted Release A suite from the clean branch.
- [ ] Run current collision check against open incumbent PR paths and fresh origin/main.
- [ ] Inspect diff for accidental score/authority/other-market changes.
- [ ] Commit exact source, push branch, open PR, and follow repository CI/merge/live rules if the branch is admissible.
