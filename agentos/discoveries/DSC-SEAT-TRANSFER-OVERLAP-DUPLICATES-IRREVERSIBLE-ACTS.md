---
key: SEAT-TRANSFER-OVERLAP-DUPLICATES-IRREVERSIBLE-ACTS
claim: >
  when a Meta-CEO seat is handed to a successor session while the predecessor session is still
  alive, both seats act on the same carriers from the same handoff kit and against the same
  watcher endpoints. On 2026-09-08 the successor bound at 21:0xZ (the seat-transfer note on
  macro#6819) while predecessor session 7cd4fae1 kept running until 22:55Z; inside that window
  the predecessor repeated three acts the successor had already taken — a second application of
  migrations 0014 and 0015 to the production database (harmless only because both files are
  written IF NOT EXISTS / CREATE OR REPLACE), a second round-4 ratification comment on
  macro#6981 (issuecomment-5592757852), and a second review lane on terminal#527 that had to be
  killed — and it ran a second watcher per endpoint against the quota law until the successor
  killed them. The predecessor disclosed the duplicates on the carriers
  (terminal#514 issuecomment-5592751149) and stood down; the receipts of record are the
  successor's.
falsifier: >
  a handover in which the predecessor's stand-down comment precedes the successor's bind
  comment and no carrier shows two same-act comments from two session ids — check with
  `gh api repos/{owner}/{repo}/issues/6819/comments --jq '.[].body'` over the transfer window.
so_what: >
  the seat-transfer protocol is ordered and the order is the whole protection: (1) the
  predecessor kills its watchers and review lanes, (2) the predecessor posts a stand-down on the
  seat issue naming its session id, its last act and the words "no further acts", (3) only then
  does the successor bind and re-arm. The successor's first act after reading the record is to
  verify (1) and (2) — `ps` for the predecessor's watcher loops on the shared build host, and
  the stand-down comment on macro#6819 — before any migration, merge or ratification. Any act
  that is not idempotent (a migration written without IF NOT EXISTS, a merge, a label flip) must
  be preceded by a re-read of the carrier looking for a same-act comment from another session
  id.
kind: landmine
verified_at: 2026-09-08
verified_by: >
  Meta-CEO B successor seat, harness session d640f3ef, 2026-09-08 22:2xZ to 23:09Z; predecessor
  session 7cd4fae1; carriers macro#6819 (seat transfer), macro#6981 (issuecomment-5592757852),
  terminal#514 (issuecomment-5592751149), terminal#527.
scope:
  - macro
  - terminal
  - "fleet operations (seat transfer)"
  - WS:MARKET-OS
confidence: verified
related:
  - "DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06"
  - "DSC:TERMINAL-MASTER-REQUIRES-RESOLVED-THREADS-SO-AN-ADVISORY-CODEQL-THREAD-BLOCKS-A-GREEN-HEAD"
  - "WS:MARKET-OS"
---

Two live sessions holding one seat will do the same work twice. On 2026-09-08 the
overlap produced a duplicate migration application, a duplicate ratification comment and
a duplicate review lane before the predecessor stood down. Nothing broke, because the
migrations happened to be idempotent — that was luck, not design. Hand the seat over in
order: watchers and lanes dead first, stand-down posted second, successor binds third,
and the successor checks the first two before it does anything that cannot be undone.
