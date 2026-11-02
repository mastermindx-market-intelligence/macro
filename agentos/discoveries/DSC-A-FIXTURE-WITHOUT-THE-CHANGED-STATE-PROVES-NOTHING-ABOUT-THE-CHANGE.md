---
key: A-FIXTURE-WITHOUT-THE-CHANGED-STATE-PROVES-NOTHING-ABOUT-THE-CHANGE
claim: "An evidence packet captured against a fixture that does not exercise the changed state is not a receipt for the change: #8289 R1 captured 8 am_edition cells against a page-test fixture whose only research-watch row carries condition_zh_disclosed_why: None, so no zh cell could show the .mx-rw-zh-note that #8283 added."
falsifier: "A zh cell captured from the tests/test_am_edition_page.py:411-413 fixture (condition_zh_disclosed_why None) whose probe.json records at least one visible .mx-rw-zh-note."
so_what: "An evidence packet for a change must assert the changed state is PRESENT in the DOM (probe.json) before the screenshot; a receipt that would look identical with the change reverted is not a receipt."
kind: constraint
verified_at: 2026-10-02
verified_by: "Opus RO review of #8289 R1 (BLOCKED D1); R2 fixture carries a disclosed row and the probe asserts the note; tests/test_am_edition_page.py:411-413"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "mockups/evidence/am_edition/"
  - "tests/test_am_edition_page.py"
  - "scripts/build_am_edition.py"
confidence: verified
---

Production rows are uniformly disclosed (build_am_edition.py:1095-1109 _safe_zh_mirror has no translation branch), so the 'mixed' state exists only in the test fixture; the receipt had to synthesize it to prove the fix.
