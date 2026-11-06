---
key: A-HIDDEN-TAB-VIEW-DEFEATS-A-FORCE-STATE-CAPTURE
claim: "On /sector_central.html the theme tape (#theme-tape) renders inside <section class=\"si-view\" data-view=\"explore\"> with .si-view{display:none} until the Explore tab is active, so capture_page_evidence.py --force-state hover(#theme-tape .help) reports captured: true on every cell together with a force_state_application gap ('did not take ... driver confirmed None'); --settle-ms retries cannot cure it."
falsifier: "`python3 scripts/capture_page_evidence.py --route '/sector_central.html#explore' --force-state 'hover(#theme-tape .help)'` reporting a force_state_application gap at desktop/en in either theme (the L5/L6 R2 run reported none)."
so_what: "When a guard-linked hover/focus target lives in a tab or view, the receipt route must carry the activating hash (the tool joins routes verbatim, capture_page_evidence.py:950-952); a 'captured: true' count is never proof \u2014 read the gap rows."
kind: landmine
verified_at: 2026-10-02
verified_by: "PR #8296 receipts: F01_LIVE_CHIP_L56_EVIDENCE_R1 (mini2 rs_20261002T221114Z_61126) BLOCKED 22:36Z with the gap on 24/24 cells; R2 (rs_20261002T223849Z_12743) at route #explore produced 24 PNG with the force applied (scripts/capture_page_evidence.py:950-952)"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "scripts/capture_page_evidence.py"
  - "templates/sector_central.html.j2"
  - "mockups/evidence/f01-live-chip-theme-tape/"
confidence: verified
---

The receipt manifest records both the success flag and the gap; only the gap tells the truth. Reviewers of hover/focus receipts open the gap rows first.
