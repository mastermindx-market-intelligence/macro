---
key: RIC-REACTION-REGIME-LOOKUP-MISMATCH
claim: >
  The frozen release-playbook contract publishes supplementary regime-conditioned
  cells as pooled era="all" rows, while engine.release_market_context previously
  searched for current-regime rows with era="2021plus". On the accepted playbook_v1
  this makes the documented regime preference unreachable and silently falls back
  to unconditioned 2021plus reaction means.
falsifier: >
  Run `python3 -c 'import json; p=json.load(open("research/release_playbook/results/playbook_v1.json")); print([r for r in p if r.get("era")=="2021plus" and r.get("regime") in {"Q1","Q2","Q3","Q4"} and r.get("horizon")=="h1" and (r.get("n") or 0)>=8][:5])'`.
  A non-empty accepted result for the same release/bucket/outcome contract, or an
  accepted supersession of PREREG_PLAYBOOK_V1.md that no longer defines pooled
  regime cells, falsifies this discovery.
so_what: >
  Release Radar reaction_sensitivity should read the actual pooled regime cell when
  current_regime matches and n>=8, then fall back field-by-field to the modern-era
  2021plus unconditioned cell. Because the preregistered regime labels use
  latest-revised regime history, any such read must expose revision_optimistic and
  remain descriptive/display-only. It is not rates-direction or trade authority.
kind: landmine
scope:
  - macro
  - engine/release_market_context.py
  - research/release_playbook/PREREG_PLAYBOOK_V1.md
  - research/release_playbook/results/playbook_v1.json
confidence: verified
verified_at: 2026-09-24
verified_by: >
  #7965; compare engine/release_market_context.py lookup against
  research/release_playbook/PREREG_PLAYBOOK_V1.md:88 and the accepted
  research/release_playbook/results/playbook_v1.json via the falsifier command.
related:
  - "WS:RATES-INFLATION-COMMAND"
  - "MRI-R17"
---
