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
  - "Public GET /api/research/catalog on the VPS returned 200 with 2,959 items on 2026-10-19: the dedicated R2_RESEARCH_* family is configured there and its catalog object is readable. That does not show the bucket equals the publisher's secret or that FIF datasets are present; dataset presence is proven by the post-deploy pointer check below"
  - "Scheduled filing-forensics-sec run 39107312198 (2026-10-18, schedule-born) publish+verify step: verified=true for 5 issuers; ISS:US-XNAS-AAPL generation ffprods_3f6d0d51499690990ee14224604c7830c2c7d9cc024905676600c092be6e04d5 admitted and served (2/2 accessions). SNOW/CAT/BAC/GOOGL admitted 12/12 each, served 0 (statement reconstruction withheld), so in production mode they answer as they do in golden mode today: no served corpus for them"
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

## Post-deploy acceptance check and rollback trigger

After the deploy that installs this unit:

1. Public `GET /api/health` must show `"fif_financial_dataset_mode":"production"`.
   If it still shows `golden`, the host env file pins the mode: that is a host
   edit, not a repo change.
2. An authenticated `GET /api/forensics/health?entity_id=ISS:US-XNAS-AAPL` must
   return `X-FIF-Dataset-Pointer: admitted` with a generation id (the last
   schedule-verified one is `ffprods_3f6d0d51…`).
3. Rollback trigger: if step 2 reports `none` or `unavailable` for AAPL, or the
   AAPL statements and query routes answer 400 or 503 where golden answered 200,
   revert this line. The revert reinstalls the unit and restarts the API on the
   golden corpus.
