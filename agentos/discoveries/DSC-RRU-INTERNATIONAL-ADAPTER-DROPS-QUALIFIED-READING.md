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
scope: ["WS:GREY-DEER-RISK-INTELLIGENCE", "scripts/build_international_macro.py", "templates/international_macro.html.j2"]
confidence: verified
---

Source-mechanism finding only. No actual page build, market data or forecast outcome
was tested. Adapter tests remain an incomplete text draft after the final harness
append was platform-blocked; no candidate adapter patch or passing test is claimed.
