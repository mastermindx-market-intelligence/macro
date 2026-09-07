---
key: CCR-HARNESS-PACKAGE-HISTORICAL-TREE
claim: >
  Historical Operator grants cannot validate revised skill bytes from a moving
  checkout. Their tests need the declared immutable package separately from
  current executable code; local-only Git readers must disable lazy fetching.
falsifier: >
  Reproduce the baseline, closeout overlay, and explicit historical-source
  comparisons in Mastermind PR 512 comment 5563474463. A corrected current
  consumer must accept its declared historical package, reject changed bytes
  under the old grant, and independently test the revised package. Re-run the
  missing-blob/tree controls in comment 5562747472 to test local-only reading.
so_what: >
  Preserve historical hashes and grants. Complete the existing owner's explicit
  test-source binding across F0, registry, adapter and canary consumers instead
  of weakening production verification or treating an older green subset as
  current integration proof. Keep this separate from runtime activation.
kind: landmine
verified_at: 2026-09-07
verified_by: >
  Mastermind PR 512 comments 5562747472 and 5563474463; executed pytest,
  independently parsed JUnit/exit files, and local file-only Git Trace2 controls.
scope:
  - WS:CHAIRMAN-CONTROL-ROOM
  - mastermind:plugins/mastermind-operator/**
  - mastermind:tests/test_sol_capability_fabric_package_generation_f0.py
confidence: verified
---

# Preserve old package identity without freezing the working instructions

The original package tree is `783ae81b44e9606baf13e2402a75a2130df9758a`
at commit `12c2cb8993f78e81c6cb9e9a75a9829f9b194dab`. A shared dialogue-reference
change affects all four skill closures, not only the edited finish entrypoint.
The earlier thirteen-path copied-fixture proposal was withdrawn in favor of
reading immutable Git objects. This is a recorded implementation choice, not
permission to change a runtime grant or replay a provider attempt.

The initial local-only reader still fetched missing promisor objects. In two
actual disposable file-only partial clones, the missing blob/tree became local
and Git Trace2 recorded a fetch child. `--no-lazy-fetch` fixed both cases while
the complete-history control passed; removing that flag reproduced both failures.
No company remote, external network or deployed incident was involved.

The hardened F0/package subset passed 101 checks. After CAP-S1 merged at
`ef02058ba9356808e41937dab054f00043f89c1e`, new consumers exposed a material gap:
V4 baseline 49 passed; closeout overlay 21 passed/28 failed; explicit historical
fixture binding plus two adapter/projection controls 51 passed. The wider six
modules remained 480 passed/31 failed. Twenty failures concerned remaining
canary-source binding; eleven reflected test-environment prerequisites.
A blocked edit and rerun were not executed. No full repair is claimed.

Evidence and retained source ownership:
https://github.com/mastermindx-market-intelligence/Mastermind/pull/512#issuecomment-5562747472
https://github.com/mastermindx-market-intelligence/Mastermind/pull/512#issuecomment-5563474463

These are dated source/test observations. They establish neither installation,
Fable-equivalent performance, nor the real parent-worker continuation journey.
