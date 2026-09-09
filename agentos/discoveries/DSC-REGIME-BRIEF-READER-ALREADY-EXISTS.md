---
key: REGIME-BRIEF-READER-ALREADY-EXISTS
claim: >
  At macro a4d33f32, master_brain._build_regime_path already consumes quad_vector
  directly but drops its date and reconstruction basis while prescribing future-direction wording.
falsifier: >
  git show a4d33f32dad140acdfa081b21f55ad6d8dcb94d4:engine/master_brain.py
  would disprove the claim if that reader preserved the date/basis and forbade forecast interpretation.
so_what: >
  Repair this existing direct briefing reader and shared server-rendered body;
  do not add another probability route through world_state/brief_context for the same consumer.
kind: architecture
verified_at: 2026-09-09
verified_by: >
  engine/master_brain.py:633 and the read-only falsifier in the W1 intake receipt;
  date changed to2000 and reconstruction disclosure added without changing prior consumer output.
scope: [macro, WS:REGIME-BRIEFING-CONTEXT]
confidence: verified
---

This supersedes only the earlier W1 proposal's extra probability route for this briefing consumer.
Other Neural Web consumers still need their own owner-routed integration and evidence.
The actual visible body is templates/_aibrief_body.html.j2, shared by server-rendered brief surfaces.
The original predictor, ledger, clocks, signal policy and W0 PR7015 remain separate and unchanged.
