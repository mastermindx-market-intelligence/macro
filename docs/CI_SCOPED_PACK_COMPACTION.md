# Scoped CI pack compaction

Existing owner: `WS:CI-MERGE-CONTROL-PLANE` / Macro #6351, with the
Fast-ship implementation retained under Mastermind #1607. Operation:
`fastship-ci-20261104-ryan`. This is an extension of `build_plan`, not a second
planner, scheduler, evidence store, release controller, or review gate.

## Behavior

The incumbent planner still chooses every logical job and publishes the one
hashed authoritative plan. After selection, a genuinely narrowed active PR may
use fewer nonempty execution packs, provided the legacy modeled maximum pack
weight does not increase. Every selected job object appears exactly once;
within-pack ordinal order, logical execution digests, the twelve-slot plan shape,
semantic evidence and exact candidate identities remain intact.

The helper first obtains the unchanged greedy `partition_jobs` baseline, then
tries smaller greedy bin counts beginning at `ceil(total_weight / baseline_peak)`.
It chooses the smallest tested count whose maximum modeled load is no greater
than that baseline. It does not assume greedy feasibility is monotonic. Empty
and all-zero workloads are explicit, negative weights are rejected, and input
generators are consumed once. This is a guarantee about the planner's weights,
not a guarantee about elapsed seconds, billing, or production throughput.

Compaction requires ALL of:

- role `pr_head`, a known changed-file inventory and a nonempty base reference;
- scope mode `active`, no unresolved global invalidation;
- fewer selected jobs than the manifest's eligible universe.

The original `partition_jobs` API remains unchanged. Main baselines, full-suite
selection, `shadow`/`off` overrides and global-invalidating plans preserve their
original named pack partition. This is load-bearing: incumbent inherited-red
comparison still needs main's pack check names. A blanket all-plan compactor
would remove baseline checks and is deliberately not implemented.

The execution consumer does not replan. It consumes the same plan JSON and
validates the existing plan digest, selected semantic jobs and exact tree/head/base.
No dynamic matrix or workflow schema change is required: existing code already
emits only the plan's nonempty pack indices.

## Actual retained workload replay

Source: Macro Actions run **41975922719**, attempt **1**, PR **#8045**.
Artifacts read as data only: `ci-semantic-plan-41975922719-1` (ID13391417887)
and `ci-changed-files` (ID13392341097).

- Tested tree: `f1c5a053595d3f68921209554a4b697075cff8f2`.
- Source head: `b096b9dbeec5237f35382cdf02e52987affad404`.
- Base: `34b4dd3e4dddd36c75348e3298624153cbab9c24`.
- Original manifest blob: `f4bd46e6bc4c8bb72aba8eeb7cf38c631ad7822e`.
- Original plan SHA-256: `4bd4237e1eabeb1ac2768fba73ce02632d66facc335c560e8d47ee1529d0884a`.
- Changed inventory: `.github/ci/legacy-jobs.yml`; bounded manifest delta selected
  **21 of 314** jobs, rather than assuming every manifest edit is safely narrow.

The exact original manifest bytes were retrieved from GitHub's blob endpoint and
verified against the blob object ID. The old partition was reproduced exactly,
including every pack's ordered job IDs and weights. All **21 logical execution
digests** matched the retained authoritative semantic plan before compaction.

| Replay output | Before | After |
| --- | --- | --- |
| Selected logical jobs | 21 | 21, identical IDs and execution digests |
| Active packs | 12 | 2 |
| Modeled maximum pack weight | 1400 | 1400 |
| Modeled total weight | 1786 | 1786 |
| Pack weights | 1400,106,63,56,28,28,27,24,14,14,14,12 | 1400,386,0,0,0,0,0,0,0,0,0,0 |

This replay removes ten pack launches for that retained workload without reducing
selected work. It is **not** a newly executed production CI run or an observed
wall-time/cost saving. Natural post-adoption CI must establish the actual effect.
The replay receipt remains in the operation's temporary evidence directory and
these immutable source/artifact identities make it reconstructible independently.

## Regression requirements

The new tests were RED before implementation (11 failing, seven passing); focused
qualification now passes **22 cases**, including **300 fixed-seed randomized
workloads** checked for exact object coverage, stable permutations, shape, ordinal
order and non-increasing modeled peak. Main/full/shadow/off/global-invalidator
negative controls preserve all baseline check names. A compacted plan round-trips
through the real authoritative consumer with all selection/partition functions
forced to fail if called, proving the consumer never re-derives the plan.

Run the existing pack, semantic and fragment suites before publication; their
actual results belong in the PR/parent source receipt. Keep any broader failures
explicit rather than removing tests or disguising local environment gaps.

## Adoption and interaction with existing work

Current related candidates retain ownership: #10735 splits the heavy control-plane
logical job; #10658 preserves a fresh interpreter for each FIF file with two
concurrent processes; #10745 repairs replay configuration inheritance. #10738's
four shared xdist workers changed the isolation model and remain unqualified;
its failing replay is not the next accepted concurrency step. This compactor
changes disjoint algorithm/planner blocks, not those weight entries, suite
definitions or replay environment helpers.
Reconcile exact current heads before integrating those PRs; do not overwrite an
incumbent or create replacement carriers.

Source merge, installed workflow use, a natural scoped-plan observation, and actual
latency improvement are separate receipts. Observe selection equivalence, stable
main baselines and real runner/startup demand after release. A report or green PR
alone is not completion of the Fast-ship program.

## Current composition — 2026-11-07

The original operation and branch compose protected main
8f83fc39187565eb0e16f9ebf66b9be2d3a8df2a without changing the authored compactor.
Only this document, the original planner blocks and appended planner tests differ
from that main revision. Accepted source, semantic classification, inherited-red
handling and import-guard repairs remain current. Fresh exact-candidate native
qualification is still required; the older failed run41985635410 is not relabeled.

The original Fabric scratch run fastship-pack-compact-20261104-01, under root
fastship-ci-20261104-ryan, has a verified TERMINAL/rc0 recorded return. It made no
repository or GitHub changes and its blanket-compaction prototype was not
accepted. Its result does not authorize a new run or acceptance; the existing
scoped implementation remains the sole source carrier. The old process number
70837 was not a durable runtime identity or a live-writer receipt.

Adoption still needs a natural genuinely narrowed PR, identical selected logical
jobs and execution digests, preserved main check names, and observed end-to-end
queue/setup/execution/aggregate costs. Twelve-to-two modeled packing is not a
five-minute full-CI result. Preserve #10674's original uncertain operation26751
and the #10745-to-#10735 delivery chain independently.
