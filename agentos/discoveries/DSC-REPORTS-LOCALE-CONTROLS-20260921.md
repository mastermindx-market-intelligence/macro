---
key: REPORTS-LOCALE-CONTROLS-20260921
claim: >
  The public Reports archive leaves native labels and count in English when the shared language switch is activated with the keyboard; span-based topic controls also omit selected semantics.
falsifier: >
  Run the actual-client archive locale test against the original paired source f7539ad7e4e22cd889ff6d75190c2e1d686a0a53; all labels must already switch and native selected state must already be present to disprove the defect.
so_what: >
  Subscribe dynamic page labels to the existing document langchange event, not a pointer-click proxy. Native topic buttons own activation; preserve query, sort, URL and focus during recovery.
kind: landmine
verified_at: 2026-09-21
verified_by: 'python3 -m pytest tests/test_reports_timeline_ui.py -q -k archive_'
scope:
  - 'mastermindx-market-intelligence/macro'
  - 'templates/reports.html.j2'
  - 'tests/test_reports_timeline_ui.py'
confidence: verified
---

Candidate is locally source/browser verified, not production-accepted. The exact carrier and proof are in research/evidence/uiux-reports-controls-20260921/README.md. The source model, report titles and catalogue are unchanged.
