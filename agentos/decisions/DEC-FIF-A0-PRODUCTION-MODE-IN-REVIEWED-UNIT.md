---
key: FIF-A0-PRODUCTION-MODE-IN-REVIEWED-UNIT
question: >
  Where should the FIF A0 flip (FIF_FINANCIAL_DATASET_MODE=production on the
  serving API) be declared, so that it is reviewable, reversible and never
  touches a host secret file?
answer: >
  In the repo-managed unit fragment `app/deploy/macro-api.service`, as one
  `Environment=FIF_FINANCIAL_DATASET_MODE=production` line. update.sh installs a
  changed reviewed unit (systemd-analyze verify, install, daemon-reload) and
  restarts the API through its existing verified-restart path. Rollback is a
  revert of that line: unset is the golden corpus byte for byte.
  `/etc/macro-api.env` is never read or edited for this flip.
rationale: >
  The A0 packet's original held act edited `/etc/macro-api.env` on the VPS. That
  file holds credentials, so editing it means opening it, and it leaves no
  reviewed record of which corpus the API serves. The unit fragment already
  carries non-secret flags (MACRO_INTEGRATED_ANSWER_ENABLED=1), is pinned by
  tests, deploys through the same reviewed path, and makes the served corpus
  auditable from git. The Chairman's 2026-10-18 instruction gave the FIF seat
  the owner role for project blockers, so the seat takes the flip through
  this path instead of waiting for a host-side edit.
alternatives:
  - option: edit /etc/macro-api.env on the VPS (the A0 packet's original §2 act)
    why_not: >
      Requires opening a secret-bearing file, leaves no reviewed record, and
      its rollback is another manual host edit.
  - option: default the selector to production in app/forensics.py
    why_not: >
      DEC:FIF-D3-DATASET-MODE-SELECTOR rejects default-production: it would
      swap the corpus of every host by omission, test hosts included.
evidence:
  - "app/deploy/macro-api.service — Environment=FIF_FINANCIAL_DATASET_MODE=production inside [Service], with its rollback note"
  - "tests/test_fif_a0_production_mode_unit.py — pins the line exactly once inside [Service], checks the API selector accepts its value, and forbids a local store path in the unit"
  - "app/deploy/update.sh — reviewed-unit install (mm_reviewed_unit_file_ready, systemd-analyze verify, install, daemon-reload, API_UNIT_UPDATED=1) and the verified restart in MACRO_API_RESTART_TRIGGER"
  - "Public GET /api/research/catalog on the VPS returned 200 with 2,959 items on 2026-10-19, so the private research-store family the reader resolves (the same family the scheduled publisher writes) is configured there; names only, no secret read"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - app/deploy/macro-api.service
  - app/forensics.py
confidence: high
reversibility: easy
decided_by: FIF Meta-CEO seat 96dc937a (owner-role delegation, Chairman 2026-10-18)
decided_at: 2026-10-18
---

# FIF A0 — the production flip is a reviewed unit line

A0 needs the serving API in production dataset mode. The flip is one
non-secret `Environment=` line in the reviewed unit, so it ships, reviews and
reverts like code. Systemd gives `EnvironmentFile=` precedence over
`Environment=`. If the host env file ever pins the mode, the live
`/api/health` readout (`fif_financial_dataset_mode`) shows it, and that host
value has to be removed on the host. The A45 receipts and the
natural-cycle witness still decide A0 acceptance. This record only moves
the switch.
