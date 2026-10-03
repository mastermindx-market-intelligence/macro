---
key: TRANSMISSION-SCENARIO-DISCLOSURE-20260923
claim: >
  Transmission rendered a noninteractive more counter instead of the remaining scenario asset, and did not consume its existing bilingual asset-label map.
falsifier: >
  Run python3 -m pytest tests/test_transmission_publish.py -q -k scenario_ui against the paired original template; all rows, Chinese labels and native disclosures must already pass to disprove this defect.
so_what: >
  Keep four rows at glance, expose the remaining source rows through native details, and reuse canonical translations without adding a label or event-control plane. Verify computed focus styles rather than merely finding a CSS declaration.
kind: landmine
verified_at: 2026-09-23
verified_by: 'python3 -m pytest tests/test_transmission_publish.py -q -k scenario_ui'
scope:
  - mastermindx-market-intelligence/macro
  - templates/transmission.html.j2
  - tests/test_transmission_publish.py
confidence: verified
---

Built and source/browser verified, not production-accepted. Exact source, current snapshots, known limitations and return path are in research/evidence/uiux-transmission-scenarios-20260923/README.md. No historical beta, signed move, ordering, access rule or shared script changed.
