---
key: A-MOVED-LINE-READ-AS-AN-INSERTED-LINE-INVENTS-A-VIOLATION
claim: >
  Reading a construct at a line NUMBER in the head revision and inferring that it was added there
  manufactures phantom insertions, because unrelated additions above it shift every line below.
  Measured 2026-09-25 on Mastermind IAC-P1 C-B: the brief forbade widening the dispatcher's closed
  `REFUSAL_CODES` set, and at the returned head `"BODY_OVER_BUDGET"` appeared at line 92 inside that
  set. Read as an insertion, this was a direct instruction violation AND a contradiction of the
  worker's own `RUNTIME_RULES_OBSERVED` claim that the set was untouched - a serious finding about
  truthfulness, not just bookkeeping. It was false. The code sat at line 88 in both the parent and the
  previously published head; the C-B commits added four lines above it. AST extraction of the
  frozenset showed 12 codes on both sides, added NONE, removed NONE, and a diff of the whole region
  came back empty. The finding would have charged correct work with an instruction violation and
  impugned an accurate self-report.
falsifier: >
  Never compare a line number across revisions. Compare the semantic object: AST-extract the
  collection at both revisions and diff the SETS, printing added/removed explicitly, or diff the
  enclosing region directly. A membership claim that cites a line number and not a set difference is
  unverified. The same control catches the inverse error - a construct that genuinely moved out of a
  guarded block while its line number stayed put.
  Historical target: compare integrations/company_consultation_dispatch.py at parent 0e908422 and candidate 2f6bc1de using the source/AST comparison recorded in https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5829291253.
so_what: >
  This is the insertion-side twin of the absence-side traps: a partial or positionally-anchored read is
  indistinguishable from a complete one. It bites hardest when reviewing a peer's returned head against
  a brief, because the reviewer is looking for violations and a moved line supplies one for free - and
  publishing it both rejects sound work and accuses the worker of misreporting. Diff sets, not
  positions, before any claim that a closed set was widened, a field was added, or a guard was removed.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Historical author-recorded verification dated 2026-09-25; supporting receipt: https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5829291253.
  The C-B receipt retracts the alleged BODY_OVER_BUDGET insertion: line 88 moved to 92, both extracted REFUSAL_CODES sets contain the same 12 members, and the enclosing-region diff is empty.
scope:
  - "Mastermind historical IAC-P1 C-B donor evidence (2026-09-25)"
  - "integrations/company_consultation_dispatch.py"
  - "source comparison and closed-set review"
confidence: verified
---

## Historical provenance — 2026-09-25

The measurements, confidence and verification date above describe the original September 25 observation. The November 6 record repair validates document structure and preserves source references; it does not rerun the historical experiment or establish current runtime behavior. The supporting [original receipt](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5829291253) records the historical evidence.

The [later canonical lineage ruling](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5841164702) designated claude/iac1-p1-packet-carriage-20260925 as **DONOR_TEST_EVIDENCE / DO_NOT_PUBLISH_AS_P1**, with [Mastermind #986](https://github.com/mastermindx-market-intelligence/Mastermind/pull/986) the canonical P1 carrier. Its held C-D child remained STOP / DO_NOT_PUBLISH. These knowledge records grant no transplantation, installation, live-packet or replay authority; all original refused or uncertain effects retain their original target and reconciliation boundary.
