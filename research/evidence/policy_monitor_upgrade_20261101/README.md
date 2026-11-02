# Policy Monitor — current visual proof

Feature source: `df0680156a3a75dbe97a3eca2aaadb8823f90242` (R6). The source remained clean during capture.

## Current verification

- Focused suite: **318 passed, no skips**, 60.29 seconds. Includes twelve new regression cases that reproduced and closed the independent review's two provenance-label blockers.
- `receipt.json`: **14 shapes / 34 PNGs**, all interaction and overflow assertions passed in 52.90 seconds. Populated English/Chinese × light/dark × desktop/mobile, plus partial, missing and malformed inputs. Real dashboard template, actual committed input payloads, shared dialog controller and keyboard trap. This test supplies a signed-in preview fixture; it does not prove live authentication or deployment.
- Canonical UI evidence: [24-state manifest](../../../mockups/evidence/policy-monitor-upgrade-20261101/manifest.json) and [owning receipt](../../../mockups/evidence/policy-monitor-upgrade-20261101/EVIDENCE.yml). Eight actual theme/language/viewport cells and sixteen real hover/focus cells. All reported state applications and PNG bytes passed the existing receipt validator. The component preview is anonymous and is explicitly scoped in its README and fixture.json.

## Suggested views

- [Desktop light](policy-populated-en-light-1440-dialog.png)
- [Desktop dark](policy-populated-en-dark-1440-dialog.png)
- [Mobile dark](policy-populated-en-dark-390-dialog.png)
- [Chinese mobile light](policy-populated-zh-light-390-dialog.png)
- [Mobile chart](policy-populated-en-dark-390-chart.png)
- [Missing input](policy-missing-en-dark-1440-dialog.png)

## Historical evidence retained with its source identity

`produced-sections.json` and the six `policy-produced-*` images remain bound to `afc33cb328f354a95923957928432f9ed64b86b0`. They verify real producer output for the activity, transmission and calendar sections; they are **not current R6-head screenshots**. Earlier R1 success claims and screenshots are superseded.

Independent final-head review, current hosted CI, normal release and served-page proof remain separate gates. This evidence package does not claim any of those gates passed.
