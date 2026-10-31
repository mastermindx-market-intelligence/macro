---
key: FABRIC-CLI-COMPLETION-AND-WORKER-SCOPE
claim: >
  The OPT-007 incident combined distinct failure modes: a temporary host hold before
  launch, successful Claude CLI terminal records mislabeled as permission failures
  because their history included denied tools, and bounded repair workers in reused
  linked lanes inheriting principal PR/merge duties. New-minted Fabric lanes already
  have a completion exemption; reused linked claude branches need their own strictly
  bound completion scope without changing tool or source admission.
falsifier: >
  Run `python3 -m unittest discover -s tests -p test_fabric_existing_lane_completion.py`
  against the pre-repair hook and show all existing-lane completion tests pass.
  Parse the original SHA-bound captures and show that their final CLI records are not
  subtype success, is_error false and terminal_reason completed; or run the new
  permission-history regression against the original outcome parser and observe the
  explicit zero input exit preserved; or show the original existing-lane guard returns
  the synthetic bound child without entering the principal delivery fingerprint path.
so_what: >
  Distinguish admission, CLI completion, result delivery and parent acceptance. A
  historical denied tool is not by itself a terminal CLI failure. Bound repair workers
  return their evidence to their actual controller; they do not inherit forbidden PR,
  merge or deployment actions. Preserve real failures, permissions, source custody,
  host safety gates, original attempts and parent acceptance. Never retry an uncertain
  effect or infer installation from a merged source change.
confidence: verified
kind: runtime
verified_at: 2026-10-22
verified_by: >
  Original ubuntu0 lanes/ext/lanes/oi-opt007-20261022.provider.capture.jsonl SHA256
  8e26d8ec2c228aa6ce1a69408174317930ca713a8d45bc646cb2a2e2d6b3a5b2 and
  oi-opt007r1-20261022.provider.capture.jsonl SHA256
  8e21522bacf6e746a3d0a04f66ca3b6e09a063d563d34818b87e139c7acab936;
  Mastermind ops/native_fabric/quota_continuity/INCIDENT_OPT007_20261022.md;
  tests/test_fabric_existing_lane_completion.py; affected ship-loop, hold-wrapper
  and semantic pytest suite: 488 passed, 1 skipped, 17 subtests passed.
scope:
  - fabric
  - orchestration
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - .claude/hooks/ship_loop_guard.py
  - scripts/ship_loop_hold_wrapper.py
---

## Repair boundary

Source operation `fabric-worker-scope-20261022-c3` adds completion metadata only
for a previously admitted linked `~/lanes/wt/<workspace>` root, a bounded class
and complexity, and matching native run, usage, outcome path, root and lease.
The new attempt may reuse an older workspace name. The same scope is recorded at
SessionStart and revalidated at Stop. Missing or changed metadata, operator
capsules and principal sessions retain the ordinary delivery chain. The hold
adapter delegates valid children to that same guard before probing a stale
unmerged state. Existing PreToolUse/source admission is unchanged.

Worker return is not task acceptance, merge, production proof, permission to
retry or proof that a recipient woke. Historical captures remain private and
unchanged. The old outcome receipt overwrote the original process return code;
therefore successful terminal events are proven, but the old OS exit cannot be
retrospectively reconstructed from that receipt alone.

The companion Mastermind operation `fabric-launch-reliability-20261022-c3`
preserves successful terminal completion only for a complete unambiguous result
with explicit original CLI exit zero and no structured failure. It records
historical denial count separately, preserves original CLI exit diagnostics and
keeps the wrapper exit distinct. Its six isolated test suites passed 39 tests.

## Deployment ceiling

At this source commit the repair is BUILT_NOT_PROVEN: exact-head review, hosted
checks, merge and installed-source readback are separate remaining gates. The
native generation must be rebuilt from protected merged source and selected with
the existing expected-preimage compare-and-swap. Running controllers retain their
old immutable generation. A Macro merge does not rewrite an occupied worker's
checkout; do not overwrite that checkout or replay its run to manufacture proof.

No host thresholds, provider keys, lease owners, queues, watchers, accounts or
original OPT-007 attempts were changed by these repairs. Actual release and
consumer-proof receipts belong to the original PR and Agent OS continuation.
