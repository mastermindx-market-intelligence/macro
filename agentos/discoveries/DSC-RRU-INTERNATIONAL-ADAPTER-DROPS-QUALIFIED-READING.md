---
key: RRU-INTERNATIONAL-ADAPTER-DROPS-QUALIFIED-READING
claim: >
  At Macro eb9e91961ddc4f3043d0dad358602525e66eccda, the real international
  _radar_display adapter returns None when state or h21 odds are missing. The RRU
  candidate intentionally withholds unreviewed odds, so this outer consumer discards
  its explicit qualified assessment even when direct shared-card tests pass.
falsifier: >
  Inspect git show eb9e91961ddc4f3043d0dad358602525e66eccda:scripts/build_international_macro.py
  and the matching templates/international_macro.html.j2. A later source-owner
  receipt showing the actual adapter retains corrected/unavailable readings through
  its wrapper and published page would close this candidate integration gap.
so_what: >
  Add the existing builder adapter and outer wrapper to the integrity slice's real
  consumer proof. Do not accept isolated card success as international-page delivery,
  or replace the missing qualified card with a separate unqualified forecast tile.
kind: landmine
verified_at: 2026-09-09
verified_by: >
  scripts/build_international_macro.py:47-74 and templates/international_macro.html.j2:260-276
  at eb9e919; source reads in the September 9 force-applicability continuation.
  RRU_INTL_JOURNEY_TESTS_2026_09_09.py and RRU_INTL_JOURNEY_FAILURE_SUMMARY_2026_09_09.json, native58689/75599.
scope: ["WS:GREY-DEER-RISK-INTELLIGENCE", "scripts/build_international_macro.py", "templates/international_macro.html.j2"]
confidence: verified
---

Source-mechanism finding only. No actual page build, market data or forecast outcome
was tested. Adapter tests remain an incomplete text draft after the final harness
append was platform-blocked; no candidate adapter patch or passing test is claimed.

## Later complete-page investigation

Thirty actual-adapter cases over ten profile definitions now reproduce the missing
qualified reading, within a51-test complete-page suite. The previous57-line partial
draft remains untouched. The new builder/VM patch append was separately blocked and
readback confirmed no append, so the adapter is still unpatched. Template-only display
improvements and160 fixture DOM checks do not close it; mobile capture was not settled.
See research/grey_deer/RRU_INTL_JOURNEY_REVIEW_2026_09_09.md for current limits.

## 2026-09-10 candidate resolution — supersedes the unpatched-candidate statement

The same-carrier adapter repair succeeded in the current continuation. Explicit
composition-bearing assessments now reach the existing mapper even without odds or
an evaluable state; old unmarked absent/no-odds behavior remains unchanged. This was
not a file-write fallback, source installation or retry of an unknown effect.

The unchanged51-case complete journey passes (native57680). A real build_all invocation
with the real page writer—not a direct mapper substitute—passes45 synthetic page/JSON
cases over the five actual routes. Historical original-consumer comparison failed35
cases with10 controls; candidate-v2 passes45. Current-main16b6c14cd479 also passes45
(native78238). The combined current-source module run passes286 (73652).

Proof lives in research/grey_deer/RRU_INTL_BUILD_PROOF_2026_09_10.py and the exact
rru_intl_build_20260910_current-16b6/receipt.json. The older blocked/draft receipts above
remain historical. Production source, independent review and installed-policy release
are separate gates; no deployed closure is claimed by this candidate evidence.
