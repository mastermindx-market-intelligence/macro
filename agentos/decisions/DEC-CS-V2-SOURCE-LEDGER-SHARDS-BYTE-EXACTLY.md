---
key: CS-V2-SOURCE-LEDGER-SHARDS-BYTE-EXACTLY
question: >
  data/capital_structure/source_manifest.jsonl is an append-only, prefix-hashed
  evidence ledger that crossed GitHub's 100 MB hard file limit (101.47 MB on
  2026-10-09), so every Capital Structure generation push since 2026-09-27 was
  rejected with GH001 while the nightly job still concluded success. How does the
  ledger keep publishing through Git — the accepted compiled-generation selector —
  without rewriting published bytes, without Git LFS, and without a second
  publication plane?
answer: >
  Shard the ledger into byte-exact continuation parts. source_manifest.jsonl
  stays part 1 and is frozen byte-identical. New rows land in
  source_manifest.part-NNNN.jsonl (NNNN from 0002, contiguous, zero-padded);
  a part is sealed once it reaches SOURCE_LEDGER_PART_ROLL_BYTES = 48 MiB, the
  cut is made at the next line end, and a sealed part is never rewritten — the
  writer refuses (ManifestIdentityError) any body that does not extend the
  sealed bytes at their offset. The logical ledger is the ordered concatenation
  of every part; every reader (engine/capital_structure/source_ledger_io.py,
  collectors/sec_capital_structure.py through it, and the Company Facts anchor
  reader in collectors/sec_capital_structure_companyfacts.py) reads parts in
  index order and rejects a gap, an orphan continuation part, or a staging
  *.tmp.jsonl file beside the ledger. The collect→capital_structure handoff
  receipt (rows = newline count, sha256 over the concatenation) is computed by
  ONE script, scripts/capital_structure_ledger_receipt.py, on both daily.yml
  sides, so the two jobs cannot drift. The append-only push fence member for
  the ledger declares siblings_pattern and compares the LOGICAL base stream
  against the LOGICAL head stream, so a rewritten or dropped continuation part
  withholds the whole CS generation exactly as a rewritten part 1 does.
  Staging writes (*.tmp.jsonl) are gitignored and excluded from the workspace
  artifact; the rejected-ledger capture includes every part.
rationale: >
  GH001 is a hard remote limit, so no future generation could publish through
  the existing path even after the runner outage clears. The jsonl_prefix
  evidence law (DEC:CS-V2-WHOLE-GENERATION-APPEND-ONLY-FENCE,
  DEC:APPEND-ONLY-BASE-FRESHNESS-IS-A-PUSH-PATH-FENCE) forbids rewriting or
  compacting published bytes, and manifest ids, source_ledger_prefix_hash and
  PIT receipts all depend on the exact ordered lines. A line-aligned part roll
  keeps every published byte at its existing offset, so nothing historical is
  re-hashed. 48 MiB keeps every part under GitHub's 50 MiB large-file warning
  with the hard limit twice as far away; one nightly appends far less than the
  gap. A single receipt implementation on both sides of the handoff is what
  makes the verify step reject a tree where part 1 matches but a continuation
  part was dropped — the exact stale tree the handoff exists to catch.
alternatives:
  - option: Git LFS for the ledger
    why_not: Forbidden by house law; it moves the selector's bytes out of the
      Git tree that every clone, the VPS pull and the fence read, which is a
      second publication plane in disguise.
  - option: Compact or rewrite part 1 (dedupe, re-encode, drop old rows)
    why_not: Violates the jsonl_prefix evidence law; prefix hashes, historical
      manifest_id strings and PIT receipts would no longer verify.
  - option: Move the ledger to R2 and commit a pointer
    why_not: Git is the accepted compiled-generation selector and R2 the
      evidence store (DEC:CS-V2-WHOLE-GENERATION-APPEND-ONLY-FENCE); a pointer
      makes R2 the selector for one member of a coherent generation.
  - option: Roll at ~95 MB to minimise part count
    why_not: Every push would carry GitHub's large-file warning and one bad
      night could cross the hard limit before the roll; 48 MiB costs nothing
      but a slightly longer part listing.
  - option: Date- or quarter-keyed files instead of numbered parts
    why_not: Existing bytes would have to move between files, which breaks the
      byte-at-offset invariant the fence and the prefix hash rely on.
evidence:
  - "daily.yml run 37874656026 job 113680083720 (2026-10-09): compile steps passed, push rejected 'GH001: File data/capital_structure/source_manifest.jsonl is 101.47 MB; exceeds GitHub's file size limit of 100.00 MB'"
  - "R1 census 2026-10-13: capital_structure job concluded success on 09-27, 09-28, 10-02, 10-03, 10-05, 10-06, 10-07, 10-08 with no generation commit on origin/main after 24ab0b613f89 (2026-09-26); part 1 on main is 97.6 MiB"
  - "DSC:CS-GENERATION-PUSH-LOST-TO-GH001-WHILE-JOB-SUCCEEDED"
  - "engine/capital_structure/source_ledger_io.py: SOURCE_LEDGER_PART_PATTERN, SOURCE_LEDGER_PART_ROLL_BYTES, write_source_ledger sealed-part refusal, source_ledger_receipt"
  - "scripts/capital_structure_ledger_receipt.py stamp|verify; .github/workflows/daily.yml collect stamp + capital_structure verify steps"
  - "scripts/ci/append_only_base_fence.py Member.siblings_pattern + logical_blob_at; config/append_only_artifacts.json capital-structure member"
  - "/opt/homebrew/bin/python3.12 -m pytest tests/test_capital_structure_source_ledger_io.py tests/test_capital_structure_ledger_receipt.py tests/test_append_only_base_fence.py tests/test_daily_capital_structure_job.py tests/test_sec_capital_structure_companyfacts.py (2026-10-13, all green locally)"
affects:
  - "WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2"
  - "capital-structure-intelligence"
  - "data/capital_structure/source_manifest.jsonl"
  - "data/capital_structure/source_manifest.part-*.jsonl"
  - "engine/capital_structure/source_ledger_io.py"
  - "collectors/sec_capital_structure_companyfacts.py"
  - "scripts/ci/append_only_base_fence.py"
  - "config/append_only_artifacts.json"
  - ".github/workflows/daily.yml"
confidence: high
reversibility: costly
decided_by: "coo-fable seat a9559a4c (Fable Meta-CEO, Chairman commission 2026-10-13, masterplan task R2)"
decided_at: 2026-10-13
review_by: 2026-10-27
---

R2 of research/capital_structure/e2e_20261013/MASTERPLAN.md: repair only the
demonstrated source/generation failure. The failure is the publication path,
not the compilers — every compile step passed on 2026-10-09 and the push died.

## Invariants readers and writers must keep

- Part 1 is `source_manifest.jsonl`; continuation parts are
  `source_manifest.part-NNNN.jsonl` with NNNN ≥ 0002 and no gaps. A tree with
  continuation parts and no part 1, or with a gap, is a corrupt ledger and is
  refused, never partially read.
- The logical ledger is the ordered byte concatenation. `source_ledger_prefix_hash`,
  `validate_manifest_ledger` and `manifest_id_for` are unchanged and operate on
  the logical stream.
- A sealed part (any non-last part, or a last part at or above 48 MiB) is
  never rewritten. The writer may only extend the active part or open the next
  one. Staging goes to `<part>.tmp.jsonl` then `os.replace`.
- The handoff receipt is `rows` (newline count) and `sha256` over the logical
  stream, produced on both sides by `scripts/capital_structure_ledger_receipt.py`.
  While the ledger is unsharded it is byte-for-byte the old `wc -l` / `shasum`
  receipt.
- The fence's `jsonl_prefix` verdict compares logical base vs logical head; the
  member's `siblings_pattern` is what makes continuation parts part of the
  member rather than untracked new files.

## Not decided here

- Offloading sealed parts to R2 with a verified pointer remains a possible later
  follow-up once the ledger approaches many parts; it needs its own record and
  must not change the Git-selector boundary.
- Whether the stuck discovery horizon (2026-09-17) is a second source defect is
  a separate R2 bucket, not resolved by sharding.
