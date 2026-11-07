---
key: A-CAPTURE-TOOL-THAT-CALLS-SETTHEME-BAKES-THE-TOGGLE-FLOURISH-INTO-EVIDENCE
claim: "theme.js skyToggleFx mounts a .sky-fx orb for 1100 ms on every setTheme call (theme.js:547-551); an evidence capture that switches theme post-load and waits less than 1100 ms records a glow on the LIGHT theme that is not page design (a TP-0 violation in the receipt, not the page)."
falsifier: "A cell captured under prefers-reduced-motion: reduce (templates/theme.js:543 guard) or after `document.querySelectorAll('.sky-fx').length == 0`, still showing the orb."
so_what: "Every evidence tool that switches theme after load must emulate reduced motion or assert the orb is gone before the screenshot, and receipts should record sky_fx_count 0 per cell."
kind: landmine
verified_at: 2026-10-02
verified_by: "#8289 R1 cells (am_edition receipt) all carried the orb after a 150 ms post-setTheme wait; R2 (head 0e456adcc39c) captured under reduced motion with sky_fx_count 0; same defect fixed earlier in #8278 R2"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "templates/theme.js"
  - "scripts/capture_*_evidence.py"
  - "mockups/evidence/**"
confidence: verified
---

Two independent capture tools (#8278 and #8289) reproduced it before the rule was written down; the cost each time was a full re-capture round.
