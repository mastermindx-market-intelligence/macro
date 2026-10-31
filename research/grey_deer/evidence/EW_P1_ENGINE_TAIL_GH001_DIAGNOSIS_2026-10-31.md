# EW-P1 — engine and collect-tail GH001 diagnosis (2026-10-31)

Plain record of what was observed and what the repair changes. No forecast.

## Receipts

- `data/qledger/claims.jsonl` at origin/main `f2efb8baf983d3997abb000ecc29e523fbb1bba3` is blob
  `34a097d796237c2ecd8f5cbd82e005757d47e940`, 104,857,394 bytes — 206 bytes under GitHub's
  104,857,600-byte hard file limit — and it is appended nightly.
- Last commit touching it: `a050d2c71647` (2026-10-21T00:56:35-07:00, "engine: regime update 2026-10-21").
- Last commit on main from the daily engine job (subject `engine: regime update <date>`, written by
  `scripts/ci/daily_engine_commit_outputs.sh`): `ad6e5a824334` (2026-10-21T01:18:57-07:00); it is also
  the last commit to advance `data/risk_envelope/latest.json`. The asia-close workflow's separate
  `engine: asia dashboards <date>` commits kept landing (newest at `f8cb6f8abe26`: `a99473f26f4f`,
  2026-10-31T06:05:38-07:00).
- Run 40803269874 (2026-10-29): engine job 123688873047 `commit engine outputs` was rejected by the
  remote with GH001 at 2026-10-30T00:17:12Z; collect_tail job 123688869633 `commit tail data` was
  rejected for a 146.50 MB QLedger blob at 2026-10-29T20:20:23Z.
- `data/risk_envelope/latest.json` (durable mirror) last advanced 2026-10-21 while
  `site/riskdata/risk_envelope.json` kept advancing.
- The collect job is protected (#9556): daily.yml at `f2efb8ba` lines 763–815 carve, 895–920 park,
  1011–1050 restore. The engine and collect-tail paths were not.

## Natural run 41156792292

Created 2026-10-31T01:44:33Z, as observed 2026-10-31T06:59Z:

- collect job 124405276038: success, with the #9556 carve active (park + restore steps succeeded).
- collect_tail job 124447218246: FAILED at `commit tail data` — at 2026-10-31T05:26:10Z the remote
  answered `File data/qledger/claims.jsonl is 146.56 MB; this exceeds GitHub's file size limit of
  100.00 MB` / `GH001: Large files detected`, and the step logged `tail data: GH001 large-file
  rejection; automatic retry stopped`.
- engine job 124447591106 (observed 2026-10-31T16:1xZ): `bash scripts/ci/daily_engine_commit_outputs.sh`
  ran twice and both pushes were rejected with GH001 for `data/qledger/claims.jsonl` (09:08:06Z and
  09:27:35Z; the `commit engine outputs` step concluded failure), each logging
  `engine outputs: GH001 large-file rejection; automatic retry stopped`. The runner log masks the
  digit `1`, so the reported size reads `***00.00 MB`. The job concluded `cancelled` at
  2026-10-31T09:29:59Z.

## Unprotected paths at origin/main f2efb8ba

- `scripts/ci/daily_engine_commit_outputs.sh:64` (`git add data/ site/ reports/`) → `:209`
  (`options_signal_nightly.sh commit-broad-candidate`) → push loop
  (`git rebase --autostash -X theirs origin/main`).
- `.github/workflows/daily.yml:2156` (`git add data/ site/basketdata/` inside the
  `commit tail data` step at `:2124`) → `git commit` → `git pull --rebase --autostash -X theirs`
  push loop.

## Repair shape

(a) `scripts/ci/qledger_oversize_carve.sh` — a sourced bash library holding the collect job's
carve/park/restore semantics line for line: `qledger_carve_staged <lane>` measures every staged
`data/qledger`/`site/qledger` blob, and when any is within 1,048,576 B of the 104,857,600 B limit
it snapshots the staged index as an unreachable runner-local commit (`git commit-tree`), unstages
both planes and warns; if the snapshot cannot be written it fails closed (withholds the lane's
whole commit, index and worktree untouched). `qledger_park` puts both planes back at HEAD before
any push rebase and verifies that; `qledger_restore` (installed as an EXIT trap, fully guarded,
ends `return 0`) restores the carved bytes byte-identically from the snapshot afterwards, removing
paths the snapshot lacks. `QLEDGER_CARVE_LIMIT`/`QLEDGER_CARVE_MARGIN` are honored only under
`QLEDGER_CARVE_TEST_OVERRIDE=1`.

(b) `scripts/ci/daily_engine_commit_outputs.sh` — one 8-line insertion after the asia-close
`git reset` (line 145 at base): source the helper, carve with lane label `engine`, exit 0 on
withhold, and on a carve install the restore trap and park before continuing to the commit.

(c) The `commit tail data` step of job `collect_tail` extracted verbatim (sha256-pinned) to
`scripts/ci/daily_collect_tail_commit.sh`, with the same 7-line carve (lane label `collect-tail`)
inserted after `git add data/ site/basketdata/`; the YAML step now runs
`bash scripts/ci/daily_collect_tail_commit.sh`. daily.yml shrinks 481,236 → 478,476 bytes.

(d) `tests/test_qledger_oversize_carve.py` — 7 cases over temporary git repos: carve-with-snapshot,
within-limit no-op, park, restore byte-identity + idempotence + EXIT-trap exit-status pins and the
custody-LOST path, fail-closed snapshot failure via a `git commit-tree`-failing wrapper, call-site
text pins for both scripts and the helper, and daily.yml extraction pins (yaml step shape,
`resolve_run_source` sees the script, and the script minus headers minus insertion re-hashes to the
pre-extraction block).

## What this does NOT do

- No QLedger publication: `data/qledger` + `site/qledger` stay unpublished by these two paths until
  the QLedger publication program (#10079) cuts over.
- No change to the 104,857,600 limit or the 1,048,576 margin.
- No truncation, deletion, split, rewrite, gc or force-push of `data/qledger/claims.jsonl` or any
  QLedger history.

## Proof still owed

Two consecutive natural nightly sessions after merge in which `commit engine outputs` and
`commit tail data` both succeed, the carve warning is visible, and
`data/risk_envelope/latest.json` advances (EW-P1.T2 acceptance; owned by the seat).
