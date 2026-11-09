---
key: HOST-LOCAL-SPOOL-BESIDE-A-COMMITTED-LEDGER-IS-SPLIT-BRAIN
claim: >
  When one success branch writes two records — one to a git-tracked ledger that
  a workflow commits back, one to a gitignored host spool — the pair is a silent
  cross-host split-brain, because the fleet's publishing hosts do not share a
  checkout. `scripts/marketing_publisher` does exactly this on its
  `if receipt.ok:` branch: `_append_publication` writes
  `data/marketing/publications.jsonl` (committed back by marketing-publish.yml,
  so every host sees it) and `_record_persona_post` writes
  `data/marketing/personas_host/` (gitignored, so no host but the writer sees
  it). The publisher runs on runner label `macstudio-light`, the nightly
  consolidator on `macstudio`, the reply desk on the VPS at /opt/macro.
  Measured 2026-09-18: the receipt ledger held 1,138 live publications over 46
  days and 7 accounts while `data/marketing/personas/` did not exist at all.
falsifier: >
  Find a publishing host whose gitignored spool reaches the nightly consolidator
  without an explicit transport — e.g. a `git add` covering a gitignored path, a
  shared volume between the macstudio and macstudio-light runner workspaces, or
  a restore step that fetches personas_host/. Or show `runs-on` for
  marketing-publish.yml and daily.yml resolving to one workspace.
so_what: >
  A gitignored host spool drained by a "nightly consolidator" is only complete
  when the consolidator runs on every host that writes it — otherwise the
  undercount is SILENT, because an absent spool and an idle host leave identical
  evidence. Before trusting any host-spool counter, ask which host writes it and
  which host drains it. The repair pattern that needs no new transport: join the
  gitignored record against a tracked ledger that already crosses hosts, using
  an identity both writers reproduce (never approximate), and REPORT what the
  join cannot resolve. Applies to the sibling spools of the same posture —
  `data/marketing/outbox/items-host.jsonl` and `data/marketing/learning_host/`.
kind: constraint
verified_at: 2026-09-18
verified_by: >
  Read scripts/marketing_publisher.py:3206 (_append_publication) and :3252
  (_record_persona_post) inside one `if receipt.ok:` branch. Confirmed
  .gitignore:592 excludes data/marketing/personas_host/ and
  .github/workflows/marketing-publish.yml:421-423 commits outbox +
  publications.jsonl but no persona path. Confirmed runner labels:
  marketing-publish.yml:115 `runs-on: [self-hosted, macstudio-light]` vs
  daily.yml:5198 `runs-on: [self-hosted, macstudio]`; VPS reply desk via
  app/deploy/marketing-reply-desk.service ExecStart marketing_fastlane_daemon
  --lane reply, which reaches persona_memory.record_relation through
  engine/marketing/reply_export.py:506. Counted the live ledger with python:
  1,138 mode=live rows, 7 accounts, 2026-07-25..2026-09-18; `ls
  data/marketing/personas/` -> No such file or directory.
scope:
  - macro
  - engine/marketing/persona_memory.py
  - scripts/marketing_publisher.py
  - .github/workflows/daily.yml
  - .github/workflows/marketing-publish.yml
confidence: verified
---

The second half of the finding is the identity hazard that makes a naive repair
worse than the bug. `persona_memory._record_key("phrases", rec)` hashes
`date|text`, and `date` is the CONTENT PLAN's business day (`item["as_of"]`),
not the wall clock. 63 of those 1,138 live publications carry an `as_of` day
that differs from their `published_at` day. A reconciler reaching for the
receipt timestamp would therefore mint a second id for a post that shipped once
and double-count it — silently TIGHTENING the per-quirk frequency caps the
store exists to feed, which is a worse failure than the undercount it set out
to fix. Reproduce the identity through the same constructor the live writer
uses, or refuse the record and report it.

See `DSC:HOST-LOCAL-SPOOL-BESIDE-A-COMMITTED-LEDGER-IS-SPLIT-BRAIN` from
`engine/marketing/persona_memory.reconcile_publications`, and the two-host proof
harness in `tests/test_marketing_persona_cross_host.py`.
