# US Macro Participation-Aware Market State — Implementation Plan

**Outcome:** Keep the existing US Market State score/band intact while making the user-facing interpretation truthful when breadth does not confirm the index/cross-asset backdrop. A 61 / RISK_ON snapshot with breadth=0 must read as **Selective risk-on**, not as a broad-rally all-clear.

**Non-goals:** No score reweighting, no new trading authority, no changes to China/HK/Canada semantics, no new sector ranking engine, and no overlap with held Grey Deer PR #6685 or Sector Central/Confluence PRs #7060/#7384/#7455.

## Task 1 — Static Market State interpretation

**Files**
- Add: `tests/test_market_state_participation_scope.py`
- Modify: `engine/market_state.py`

**RED:** Add pure tests covering US RISK_ON with breadth scores 0 / 50 / 75 / missing, plus MIXED/RISK_OFF and non-US invariance. Assert score/verdict are not changed by the interpretation helper and no selective copy claims broad breadth confirmation.

**GREEN:** Add one display-only participation classifier using the existing breadth leg and its existing 42/60 tone cutoffs. Generate the US RISK_ON headline from that classifier:
- >=60: broad participation;
- 42–59: selective / uneven participation;
- <42: selective / weak participation;
- missing/non-numeric: participation unverified.
All other verdicts/markets retain current headline semantics. Persist an additive `participation_scope` block in the snapshot for consumers.

## Task 2 — Intraday parity without duplicating signal logic

**Files**
- Modify: `scripts/build_risk_state.py`
- Modify: `templates/risk_state_live.js`
- Modify: paired `site/risk_state_live.js`
- Modify: `tests/test_risk_state_live_copy_sync.py`
- Modify: `tests/test_risk_state_live_session_floor.py`

**RED:** Extend tests so the live feed carries the same participation-aware headline as the canonical engine. Node harness must prove that a current RISK_ON feed with weak breadth paints “Selective risk-on”, while missing data fails closed to “participation unverified”; existing session-floor behavior must remain intact.

**GREEN:** Have the live builder derive `display.headline_en/zh` and `display.participation_scope` from the canonical Market State helper for the displayed verdict. The JS consumes these fields when present and falls back to its legacy verdict map for backward compatibility. Do not invent a second breadth calculation in JavaScript.

## Task 3 — Verification and delivery

Run the new tests first, then the risk-state live/session-floor suites and the existing market-state/radar regression subset. Run `git diff --check` and paired-template sync. Inspect the diff for path overlap with currently open PRs.

Then commit, push, open one PR, wait for all binding checks to conclude, merge only when lawful/green, and verify the served `macro.html` on the production path. Production acceptance requires the page to preserve the score/band while the headline truthfully distinguishes selective from broad participation.
