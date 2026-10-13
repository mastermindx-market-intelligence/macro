---
workstream: "WS:CI-MERGE-CONTROL-PLANE"
session: claude/ci-pack-checkout-unfiltered-fetch-20260923
model: fable
ended_because: complete
mission: >
  Explain and remove the fleet-wide 2026-09-23 pack-checkout failure "could not
  fetch 20ced73508fe… from promisor remote" (runs 35876013221 / 35885173966 /
  35886408213) without changing CI authority semantics, and record the finding
  as DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION.
state_before: >
  Hosted ci-pack jobs checked out with `filter: blob:none` + `fetch-depth: 1`
  and then materialised the whole ~5 GiB / 105k-blob tree, so every blob was
  lazily fetched by `git checkout` in one unretried promisor request. Three
  such requests were cut at 65–67 minutes; each rerun went green. The named
  OID is .agents/skills/macro-sparse-worktree/SKILL.md — merely the first index
  entry — and is intact on GitHub and locally.
changed:
  - path: .github/workflows/ci.yml
    what: >
      ci-pack checkout drops `filter: blob:none` (keeps `fetch-depth: 1`, no
      sparse checkout) so blob transfer rides actions/checkout's retried
      `git fetch` as a single-commit want; comment carries the receipts.
  - path: tests/test_ci_pack.py
    what: pins `filter` ABSENT on the pack checkout (was pinned to blob:none).
  - path: tests/test_ci_pack_semantic.py
    what: fixture docstring no longer claims every hosted pack is blobless.
  - path: scripts/run_ci_pack.py
    what: >
      `_hydrate_exact_base_objects` docstring notes the hosted packs are now
      full clones (hydration is the pinned no-op there); no code change.
  - path: agentos/discoveries/DSC-CI-PROMISOR-OBJECT-FETCH-TRUNCATION.md
    what: new discovery with mechanism, falsifier and so_what.
  - path: agentos/workstreams/WS-CI-MERGE-CONTROL-PLANE.md
    what: cites the new discovery.
verified:
  - claim: the named object is the first blob of the tested tree and is intact
    command: git ls-tree -r origin/main | head -1; git cat-file -t/-s 20ced73508fe1863f41e6a2cfc1a75d98a4fed6e
    result: .agents/skills/macro-sparse-worktree/SKILL.md; blob; 2349
  - claim: all three failures are ~66-minute checkout-step transfers cut mid-chunk, not a code red
    command: gh api repos/mastermindx-market-intelligence/macro/actions/jobs/{107238846125,107264966712,107267933408}/logs
    result: git checkout started 14:57:37/16:00:16/16:07:28Z, died 16:03:58/17:07:39/17:12:59Z with 25719/35379/27331 bytes still expected
  - claim: git names the first still-missing promisor OID after a failed batch, and actions/checkout retries fetch() but not checkout()
    command: read git/git promisor-remote.c promisor_remote_get_direct; actions/checkout v4 src/git-command-manager.ts + src/retry-helper.ts
    result: die() in the remaining-OID loop; RetryHelper(3, 10, 20) wraps fetch only
  - claim: the discovery validates
    command: python3 scripts/agentos.py validate
    result: rc 0, 0 error(s)
  - claim: workflow-shape and base-replay tests pass with the new shape
    command: python3 -m pytest tests/test_ci_pack.py tests/test_ci_plan_workflow.py tests/test_fence_checkout_contract.py -q; python3 -m pytest tests/test_ci_pack_semantic.py -k "replay or hydration or partial" -q
    result: see PR body (the one pre-existing red in test_ci_pack.py is attributed there)
unverified:
  - claim: an unfiltered depth-1 fetch is not slower than the blobless fetch plus lazy checkout on hosted runners
    what_would_verify: compare "Checking out the ref" + "Fetching the repository" durations on this PR's ci.yml run against a healthy pre-change run (ci-pack-0 rerun of 35876013221 took 9m10s in checkout)
unresolved:
  - GitHub's ~66-minute cap on a single upload-pack response is inferred from three receipts, not documented; a fetch that is genuinely slower than that would still fail (three times, retried) rather than resume.
next_actions:
  - Watch the first ci.yml run on this PR head for pack checkout durations; if the unfiltered fetch is materially slower, the next lever is `fetch-depth: 1` plus `git config http.lowSpeedLimit/http.lowSpeedTime` in the pre-checkout step, never a return to `blob:none` on a full-tree job.
do_not_redo:
  - Do not reinstate `filter: blob:none` on the hosted ci-pack checkout; it saves no bytes on a job that materialises the whole tree and removes the fetch retry.
  - Do not sparse-checkout the packs (test_ci_pack_partial_clone_keeps_history_without_historical_site_blobs; legacy suites read committed site/).
  - Do not investigate 20ced73508fe as a corrupt object; see DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION falsifier.
danger_areas:
  - ci.yml is CI authority; the merged head carries `authority_changed=true` and clears only through a green ci.yml run on a main descendant.
  - ci-plan, fence-pack and the semantic-law checkout keep `blob:none` on purpose (paired with sparse checkouts); do not "harmonise" them.
discoveries:
  - "DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION"
---

One PR, one behavioural change (the pack checkout's fetch shape), receipts in the
DSC. The ship-loop guard's `missing_pack_fragment` classification of such heads
was correct and is untouched.
