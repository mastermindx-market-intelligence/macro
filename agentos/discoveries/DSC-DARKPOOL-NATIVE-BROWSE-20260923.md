---
key: DARKPOOL-NATIVE-BROWSE-20260923
claim: Dark Pool Browse had non-native presets and sorting, unlabeled filters, narrow-screen
  clipping, and stock identity disappearing during horizontal scrolling.
falsifier: Run python3 -m pytest tests/test_darkpool_desk.py -q -k desk_ui against
  the paired original source; original native controls, labels, and sticky ticker
  should already pass to disprove the defects.
so_what: Use native controls, preserve data/filter/export logic, and test individual
  control bounds plus visible ticker identity at both horizontal scroll limits. Page-overflow
  checks alone miss lost identity.
kind: landmine
verified_at: '2026-09-23'
verified_by: python3 -m pytest tests/test_darkpool_desk.py tests/test_darkpool_signals.py
  -q
scope:
- mastermindx-market-intelligence/macro
- templates/darkpool.html.j2
- tests/test_darkpool_desk.py
confidence: verified
---

Built and locally verified, not production-accepted. Source, invariants, both art directions and real native interaction evidence are in research/evidence/uiux-darkpool-native-desk-20260923/README.md. No dataset, model or access change.
