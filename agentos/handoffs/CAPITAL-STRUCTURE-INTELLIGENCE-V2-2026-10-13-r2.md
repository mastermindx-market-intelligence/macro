---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-r2-ledger-sharding
model: fable
ended_because: ci_handoff
mission: >
  Masterplan R0–R2 (research/capital_structure/e2e_20261013/MASTERPLAN.md at
  93c82c9058ee): reconcile the retained estate, read the natural receipts
  without dispatching a run, and repair only the demonstrated source/generation
  failure so the Capital Structure nightly can publish a generation again.
state_before: >
  Last landed generation 24ab0b613f89 (2026-09-26; health degraded_discovery;
  filing-discovery horizon 2026-09-17). Eight nightlies 2026-09-27..10-08
  concluded success with no generation commit on origin/main; the 2026-10-09
  run 37874656026 failed at push with GH001 because
  data/capital_structure/source_manifest.jsonl reached 101.47 MB (97.6 MiB on
  main). Since 2026-10-10 the collect job is cancelled by the runner-listener
  outage (operator-owned), so the capital_structure job is skipped. W2C/W2D
  remain BUILT_NOT_PROVEN; the UI repair PR #8673 remains held.
changed:
  - path: engine/capital_structure/source_ledger_io.py
    what: >
      Byte-exact continuation parts source_manifest.part-NNNN.jsonl (NNNN from
      0002, contiguous), 48 MiB line-aligned roll, sealed parts never rewritten
      (ManifestIdentityError), ordered-concatenation reader,
      source_ledger_receipt, atomic *.tmp.jsonl staging.
  - path: collectors/sec_capital_structure_companyfacts.py
    what: >
      Company Facts anchor reader reads the ledger parts in index order and
      refuses gaps, orphan continuation parts and byte-cap overruns.
  - path: scripts/capital_structure_ledger_receipt.py
    what: >
      New. One stamp/verify implementation of the collect -> capital_structure
      handoff receipt (rows + sha256 over the logical ledger); bare line-start
      GitHub annotations.
  - path: .github/workflows/daily.yml
    what: >
      collect stamps and capital_structure verifies through the receipt script;
      the workspace artifact excludes *.tmp.jsonl; the rejected-ledger capture
      includes every continuation part.
  - path: scripts/ci/append_only_base_fence.py
    what: >
      Member.siblings_pattern and logical_blob_at so the jsonl_prefix verdict
      compares the logical base stream with the logical head stream across
      parts; a rewritten or dropped part withholds the whole family.
  - path: config/append_only_artifacts.json
    what: The capital-structure ledger member declares the continuation-part siblings pattern.
  - path: config/synapse.yml
    what: Notes the sharded ledger layout on the source-manifest artifact.
  - path: .gitignore
    what: data/capital_structure/*.tmp.jsonl staging files are never committed.
  - path: .github/ci/legacy-jobs.yml
    what: >
      capital-structure-intelligence pack also runs
      tests/test_capital_structure_ledger_receipt.py and
      tests/test_capital_structure_source_ledger_io.py.
  - path: config/unrun_test_baseline.json
    what: tests/test_capital_structure_source_ledger_io.py leaves the grandfather list (now CI-owned).
  - path: tests/
    what: >
      test_capital_structure_source_ledger_io.py (sharding block),
      test_capital_structure_ledger_receipt.py (new),
      test_append_only_base_fence.py (sharded CS lane),
      test_daily_capital_structure_job.py (receipt steps),
      test_sec_capital_structure_companyfacts.py (parts reader).
  - path: agentos/decisions/DEC-CS-V2-SOURCE-LEDGER-SHARDS-BYTE-EXACTLY.md
    what: Records the sharding law and the rejected alternatives.
  - path: agentos/discoveries/DSC-CS-GENERATION-PUSH-LOST-TO-GH001-WHILE-JOB-SUCCEEDED.md
    what: Records that a green capital_structure job is not a publication receipt.
verified:
  - claim: The sharded ledger module rolls line-aligned at the byte cap, extends only the active part, and refuses to rewrite a sealed part.
    command: /opt/homebrew/bin/python3.12 -m pytest tests/test_capital_structure_source_ledger_io.py -q
    result: 19 passed, 2 skipped (2026-10-13, local).
  - claim: The receipt script stamps and verifies the logical ledger across parts and rejects dropped, rewritten, extra and orphan parts and a missing receipt.
    command: /opt/homebrew/bin/python3.12 -m pytest tests/test_capital_structure_ledger_receipt.py -q
    result: 11 passed.
  - claim: The append-only fence withholds the whole CS generation when a continuation part is rewritten or dropped and admits a new part that extends the logical stream.
    command: /opt/homebrew/bin/python3.12 -m pytest tests/test_append_only_base_fence.py -q
    result: all passed, including the appended sharded-lane block.
  - claim: daily.yml stamps and verifies through the single receipt script with no second hash implementation in either step.
    command: /opt/homebrew/bin/python3.12 -m pytest tests/test_daily_capital_structure_job.py -q
    result: 31 passed.
  - claim: The Company Facts anchor reader reads parts in order and refuses gaps, orphans and byte-cap overruns.
    command: /opt/homebrew/bin/python3.12 -m pytest tests/test_sec_capital_structure_companyfacts.py -q
    result: the four appended sharded-ledger tests pass; the pre-existing external head-witness test is listed under unresolved.
  - claim: Every new test file is named by a run step and the unrun-test gate passes.
    command: python3 scripts/audit_unrun_tests.py
    result: exit 0 after removing the source_ledger_io row from config/unrun_test_baseline.json.
  - claim: The document-terms authority closure is unchanged by this branch.
    command: /opt/homebrew/bin/python3.12 scratchpad import check printing engine.capital_structure.document_terms._AUTHORITY_POLICY_DEPENDENCY_COUNT
    result: 432, identical to origin/main.
  - claim: The two registration-lifecycle failures (event immutable identity digest mismatch) pre-exist this branch.
    command: >
      Swap engine/capital_structure/source_ledger_io.py and
      collectors/sec_capital_structure_companyfacts.py to origin/main bytes,
      rerun tests/test_compile_capital_structure_registration_lifecycles.py,
      restore (md5 identical before/after).
    result: >
      Still 2 failed with origin/main bytes (local pandas 3.0.5, pyarrow 25.0.0).
      Main's newest completed ci.yml proof 38385627689 reports FAILED only for
      tests/test_ci_pack.py in ci-pack-0, so the capital-structure pack is green on main.
unverified:
  - claim: Hosted ci.yml, fences and the ci-authority checks conclude green on the exact PR head.
    what_would_verify: The PR's checks concluding; then a hand merge with --match-head-commit.
  - claim: The first natural nightly after the merge publishes a generation carrying source_manifest.part-0002.jsonl.
    what_would_verify: >
      A commit on origin/main after the merge that changes
      data/capital_structure/health.json and adds
      data/capital_structure/source_manifest.part-0002.jsonl, with the
      capital_structure job's verify step logging 'capital-structure handoff
      verified'. Requires the runner-listener outage to clear; never dispatch
      daily.yml to prove it.
unresolved:
  - "Runner-listener fuse has cancelled every collect job since 2026-10-10; Chairman blocker with operator-only levers."
  - "Filing-discovery horizon stuck at 2026-09-17 on the last landed generation is a second R2 bucket not resolved by sharding."
  - "tests/test_compile_capital_structure_registration_lifecycles.py has 2 pre-existing local failures (event identity digest mismatch under pandas 3.0.5); green on main CI."
  - "tests/test_capital_structure_document_terms.py [cpython-3.12.2-python-org] params fail locally because that interpreter is actually 3.12.10; an environment pin, not code."
  - "RESOLVED 2026-10-14: the Company Facts external head-witness test failed locally on 2026-10-13; the whole file passes 98/98 at af5cf079 (pytest tests/test_sec_capital_structure_companyfacts.py), so no repair was owed."
next_actions:
  - Merge the R2 PR by hand on concluded green with --match-head-commit, then prove main under the changed scripts/workflows authority with one ci.yml baseline after the in-flight preflight.
  - Observe the first natural nightly for a generation commit carrying part-0002; do not dispatch daily.yml.
  - Start C0 (state/scenario type freeze) and E0 (reference docs); adopt #8673 (P0) only through the held owner path after a hosted gate:data receipt and browser proof.
do_not_redo:
  - Rewrite, compact, re-encode or Git-LFS data/capital_structure/source_manifest.jsonl.
  - Add a second receipt implementation (wc/shasum) in daily.yml beside scripts/capital_structure_ledger_receipt.py.
  - Dispatch or rerun daily.yml to prove the sharded ledger.
  - Fix the registration-lifecycle digest mismatch or the document_terms interpreter pin inside this workstream without a demonstrated CI red.
danger_areas:
  - A sealed part is never rewritten; a writer whose body does not extend the active part raises ManifestIdentityError by design.
  - A *.tmp.jsonl beside the ledger is staging and must never be treated as a part or committed.
  - A tree with continuation parts and no part 1, or a numbering gap, is refused whole; never repair it by renaming parts.
  - source_manifest.jsonl on main is 97.6 MiB; any append path that bypasses write_source_ledger crosses GH001 again.
prs: [9146]
decisions:
  - DEC:CS-V2-SOURCE-LEDGER-SHARDS-BYTE-EXACTLY
discoveries:
  - DSC:CS-GENERATION-PUSH-LOST-TO-GH001-WHILE-JOB-SUCCEEDED
---

R2 closed the publication path, not the compilers. The handoff receipt is now one
script on both daily.yml sides; the fence judges the logical ledger; readers
refuse corrupt part listings. Production proof is still owed by the first
natural nightly after the merge and cannot be manufactured.
