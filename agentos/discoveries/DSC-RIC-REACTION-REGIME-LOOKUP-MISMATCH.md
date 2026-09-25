---
key: RIC-REACTION-REGIME-LOOKUP-MISMATCH
claim: >
  The frozen release-playbook contract publishes supplementary regime-conditioned
  cells as pooled era="all" rows, while engine.release_market_context previously
  searched for current-regime rows with era="2021plus". On the accepted playbook_v1
  this makes the documented regime preference unreachable and silently falls back
  to unconditioned 2021plus reaction means.
falsifier: >
  Produce an accepted playbook_v1 row with era="2021plus", regime=Q1/Q2/Q3/Q4,
  horizon=h1 and n>=8 for the same release/bucket/outcome lookup, or supersede the
  preregistered playbook contract so regime cells are no longer pooled era="all".
so_what: >
  Release Radar reaction_sensitivity should read the actual pooled regime cell when
  current_regime matches and n>=8, then fall back field-by-field to the modern-era
  2021plus unconditioned cell. Because the preregistered regime labels use
  latest-revised regime history, any such read must expose revision_optimistic and
  remain descriptive/display-only. It is not rates-direction or trade authority.
kind: implementation
scope:
  - macro
  - engine/release_market_context.py
  - research/release_playbook/PREREG_PLAYBOOK_V1.md
  - research/release_playbook/results/playbook_v1.json
confidence: verified
verified_at: 2026-09-24
verified_by: >
  Exact main 25fb8fa805d611727078f65626f2c3b0388070b3 source/prereg/playbook
  comparison during the Chairman-authorized rates-direction program.
related:
  - "WS:RATES-INFLATION-COMMAND"
  - "MRI-R17"
---
