# CI Latency + Autonomous Healing — masterplan

**Commissioned by the operator, 2026-08-17.** Status: active; W1 and substantial
planner/checkout infrastructure have landed, trusted-PC production routing is in
P3B-B on issue #6351, and the remaining latency/capacity waves are held behind that
route's exact-head proof and P4 natural-traffic acceptance.

This is a **dedicated wave, deliberately separate from PR #5823**. Standing constraint
for the whole program: *do not let a routing-feature PR rewrite CI infrastructure while
it is trying to become green.* A feature PR that also edits the planner, the packer, or
the gate cannot be reasoned about — its own red is then indistinguishable from the
infrastructure it is changing. Every wave below lands as its own PR against a green base.

**Explicit non-goal: do NOT replace the `ci-pack` system.** The 194→6 semantic scoping
already does real work (measured on #5823: `scoped to 16 changed file(s): 6/194 jobs
(2 unscoped always-on, 4 scoped matches); derived scopes for 177/194 jobs; 15 declared
exclusive`). This program is that system's next maturation step — fast front-door
validation, cheap checkouts, cached base proofs, empirical balancing, a closed-loop
healer — not a rewrite.

## 2026-08-26 current-state amendment

This amendment reconciles the original charter with the system that now exists. It does
not authorize a parallel CI plane and it does not make the private-repository cutover.

### What the repository is actually doing

- The code gate currently contains **132 logical jobs**, partitioned into twelve stable
  semantic check names. A full-suite validation at current main reports pack weights
  `274,272,172,172,172,171,170,170,170,170,173,171`; the first two partitions carry a
  materially heavier tail than the other ten.
- Ordinary PRs do **not** automatically execute all 132 jobs or all twelve packs. The
  hosted planner computes one exact changed-file set, conservatively infers ownership,
  and launches only the non-empty pack indices. Global-invalidating paths, unscoped jobs,
  opaque filesystem/subprocess traversals, and deliberately broad owners still widen a
  PR. That conservatism is why a small-looking change can legitimately select a long
  tail.
- A logical job is one serial sequence of checkout, tool setup, dependency installation,
  and one or more validation steps. The repository repeatedly folded unrelated suites
  into existing logical jobs to preserve the representative-diff scoping ratio. That kept
  coverage visible, but it also made one selected owner inherit every folded suite and
  made a slow step hold the whole pack open.
- P1/P2 proved three isolated Linux/x86 CI slots on the PC with a root-owned read-only
  object cache and an independent render reservation. P3B-A made the main-owned executor
  callable. P3B-B is the single live production-route carrier; no latency or slot-count
  edit may overlap it. P4 must then prove three natural ordinary PRs before the route is
  accepted as production behavior.
- The PC is a 24-core/24-thread Core Ultra 9 285K, but WSL is intentionally limited to
  16 CPUs, 44 GiB memory, and 8 GiB swap. Three CI candidates are proven. A fourth is the
  next admissible experiment only after an aggregate CI cgroup/slice budget and a
  render-aware resource receipt exist. Six or eight are not inferred from idle core
  count.
- The stationary M4 Pro MacBook is available for six months, but it is a macOS/ARM host,
  not a semantic substitute for Linux/x86 CI. Its first lawful role is a narrow,
  main-defined `macos-arm-validation` capability with no production route. The three
  current M4 minis are deferred because they will be replaced in roughly two weeks; the
  role must be device-independent so a replacement mini can assume it later.

### Why packs are numerous and why some are long

The answer is not simply "the codebase is huge." The repository spans product rendering,
data contracts, workflow authority, market engines, publication, Agent OS, deployment,
and security fences, so broad validation is real. But the current latency comes from four
separable mechanisms:

1. **Conservative ownership.** Static inference must widen when a test traverses the
   filesystem, launches opaque subprocesses, imports dynamically, or owns a global graph.
2. **Folded ownership.** Several independent suites share one logical owner because the
   manifest's scoping-ratio guard punished adding a broad job. Selecting that owner runs
   the whole bundle.
3. **Repeated environment startup.** Every selected pack repeats checkout, Python/Node
   setup, virtual-environment creation, and dependency installation before useful work.
4. **Stale balancing units.** Hand-maintained job weights do not reliably predict current
   checkout/install/test wall time, so one long owner can dominate the verdict after the
   other packs finish.

This is recognizable in large monorepos, but mature systems normally combine explicit
ownership graphs, hermetic task caching, immutable dependency caches, empirical weights,
and a small always-on trust core. Running every test for every PR is not the target here;
running every validation that the exact change can affect, plus the non-negotiable trust
fences, is.

### Revised execution order

The route and latency programs share authority files, so they are serialized:

1. Finish the existing P3B-B carrier and P4 natural-traffic proof without changing its
   planner, job selection, pack topology, or resource envelope.
2. Capture a current per-logical-job cost/selection corpus from those natural PRs. This is
   the baseline for every later latency claim.
3. Split false ownership coupling, beginning with suites folded into broad jobs. Preserve
   the actual security/merge fences and use coverage-audited `scope: exclusive` only where
   the closure checker proves the declaration complete.
4. Remove repeated startup cost with immutable dependency caches keyed by lock/input and
   execution profile. Candidate jobs may consume but never mutate shared cache state.
5. Add result reuse only for hermetic jobs keyed by exact tree/input/dependency/toolchain
   identity. Missing, stale, corrupt, or non-hermetic evidence must execute live.
6. Recalibrate job weights and, only from measured evidence, reconsider the fixed twelve
   partitions. Check names remain stable until merge-control consumers are migrated.
7. In a separate capacity carrier, prove a fourth PC slot under one aggregate CI resource
   slice and a naturally active render. Do not proceed to six until four has a clean
   pressure, cache, teardown, and render receipt.
8. In a separate host carrier, build the device-independent macOS/ARM validation role and
   keep production routing disabled until its isolation, reboot, contamination, cache,
   and thermal gates pass.
9. Recompute hosted-minute projection, ordinary-PR p50/p95, simultaneous-PR queueing, and
   render/native contention. Only then assemble the private-cutover packet.


## 2026-09-18 horizontal-agent scaling hardening amendment

This amendment is the capacity and queueing contract for the horizontal-agent era. It
does not replace GitHub Actions, the existing semantic planner/gate, runner policy,
merge controller, Agent OS, or any active repair carrier. It makes the scaling objective
explicit:

> Increasing the number of coding sessions must not require a near-linear increase in
> runner count, and waiting for CI must not consume principal reasoning turns.

The governing optimization order is **eliminate avoidable runner-minutes -> recover
leaked effective capacity -> preserve fair admission -> add measured capacity -> add
elastic burst capacity**. Hardware is never accepted as a substitute for a demand-slope
repair.

### Fresh evidence that changes the capacity model

The September 18 incident is not one failure mode:

- #7276 sampled 50 queued trusted-CI runs: **47 selected all twelve packs**, two
  selected two packs, and the bounded census contained **405 queued trusted-pack jobs**.
  A separate live census observed **73 queued runs / 4 in progress** while all three
  production PC listeners were doing real work. This proves saturation plus cross-run
  admission fragmentation, not simply dead runners.
- #7296 found 51 queued PR CI runs; 21 touched
  `.github/ci/legacy-jobs.yml`, and 17 touched that manifest without changing
  `ci.yml` or `run_ci_pack.py`. Exact base/head replay classified **17/17** of those
  manifest-only PRs as mechanically boundable instead of requiring the historical
  full-suite invalidation. This is direct evidence that avoidable demand amplification
  is a first-order capacity problem.
- #7315 proved a separate effective-capacity leak: GitHub had already terminalized three
  jobs while their local Runner.Worker/systemd trees continued executing for roughly
  another fifty minutes, consuming the entire three-slot pool. Registered listeners are
  therefore not equivalent to usable slots.
- #7222 measured the root-owned shared-cache updater consuming 70-120 seconds and
  peaking at **14.2 GiB** while scanning the whole ~93-GiB / ~7.4-million-object cache.
  The bounded incremental candidate reduced representative cycles to roughly 1-2
  seconds and about 120-247 MiB. Shared host maintenance can therefore erase nominal
  capacity even when every runner remains online.
- #7313 measured one repo-wide import guard at about **6.24 GiB peak RSS**; the bounded
  lifetime repair reduced it to about **189 MiB** without narrowing coverage.
- #7323 measured a repeated Agent OS validation subset improving from 165.68 seconds to
  37.08 seconds (**4.47x**) by replacing a parser hotspot without dropping tests.

These are different levers. Queue policy cannot repair wasteful execution, another
runner cannot repair a ghost-worker lifecycle, and test optimization cannot by itself
provide burst headroom.

### Capacity is runner-minutes, not runner names

Every capacity decision must use one common model. For a bounded observation window:

```text
lambda = admitted PR generations per hour
W      = runner-minutes consumed per admitted generation
C      = nominal admitted execution slots
A      = observed slot availability fraction after offline/ghost/refusal loss

usable_slots = C * A
rho = lambda * W / (60 * usable_slots)
```

A **PR generation** is an exact proof-producing head admitted to trusted execution. A
new synchronize event is another generation; counting only PR numbers materially
understates AI-driven load.

The same receipt plane must also derive:

```text
queued_runner_minutes = sum(predicted remaining runner-minutes for pending work)
estimated_drain_minutes = queued_runner_minutes / usable_slots
```

Do not size from queued-job count alone: a two-minute structural pack and a thirty-minute
tail pack are not equal demand.

Operating targets after the current repair wave:

| Capacity signal | Hardened target |
|---|---:|
| steady-state runner-minute utilization `rho` | <= 0.65 |
| rolling 15-minute burst utilization | <= 0.80 |
| ordinary PR queue pickup p95 | < 60 seconds |
| ordinary final-head push -> `ci-gate` p95 | < 10 minutes |
| heavy PR final-head push -> `ci-gate` p95 | < 15-20 minutes |
| stale/superseded generation runner-minutes | near zero |
| GitHub-terminal job retaining a local CI slot | zero tolerated |
| same-SHA green -> red nondeterminism | zero tolerated |

The 0.65 steady-state target is deliberate headroom for bursty agent completions. A
fleet that looks "efficient" only at 90-100% utilization is a queueing system optimized
for server occupancy rather than company throughput.

### Admission V1 is containment, not the end-state scheduler

#7276 remains the existing owner of the immediate cross-run starvation repair. Its
GitHub-native `queue: max` concurrency group is useful because it prevents hundreds of
pack jobs from many runs competing for three labels simultaneously. It does **not**
increase service rate.

The contract is narrower than the word "FIFO" can imply:

- GitHub owns the queue; no second scheduler/lease/priority database is created.
- `queue: max` admits at most **100 pending workflow/job instances per concurrency
  group**. The capacity plan must never depend on approaching that ceiling; overflow
  cancellation is an incident, not backpressure working as designed.
- GitHub documents ordering by the time an item begins waiting on the concurrency group,
  while also warning that actual start ordering is not guaranteed. Acceptance therefore
  measures **absence of material leapfrogging/starvation**, not a fictional total-order
  guarantee.
- A superseded PR head must vacate the pending queue and consume no later pack
  runner-minutes. A queued obsolete generation that survives its caller cancellation is
  a blocker.
- Direct diagnostics remain outside the production admission group.

Run-level serialization can become a head-of-line blocker after scoping improves. Once
the natural corpus contains mostly 1-4-pack ordinary PRs, measure **idle eligible slot
time while trusted work is pending**. If that exceeds 5% of queued intervals or pushes
ordinary pickup above the SLO, strict whole-run admission has become the bottleneck.

Only then may a separate carrier evaluate a GitHub-native **slot-lane admission** shape:
three lanes while production capacity is three, four after an accepted C3P promotion,
with each semantic pack deterministically mapped to one main-owned lane and
`queue: max` providing the queue. That experiment must preserve the existing runner
group, semantic plan, fragment law, stable check contexts, and GitHub as the sole
scheduler. No custom priority service is authorized by this amendment.

### Demand-slope law: full-suite execution is exceptional

#7296 is the incumbent carrier for the manifest-global-invalidator class. Do not create
another manifest classifier. Its post-merge natural proof must record, for every admitted
generation, one reason family:

- `GLOBAL_INVALIDATOR`
- `NO_TRUSTWORTHY_CHANGED_SET`
- `UNSCOPED_ALWAYS_ON`
- `OPAQUE_DEPENDENCY_FALLBACK`
- `BOUNDED_CHANGED_OWNER_SET`
- `NO_WORK`

A reason is diagnostic metadata, not another selection authority.

The existing latency-plan population definitions remain binding: **ordinary** means one
to four selected packs without a global invalidator; **heavy** means eight or more packs
or a declared full-suite path. After #7296 and the next ownership-splitting carriers,
the program is not considered demand-stable if more than 20% of natural product/maintenance
PR generations that do not intentionally change a global authority surface still widen
to eight or more packs.

Every narrowing must continue to pass closure/representative-diff/unrun-suite guards and
must name what it dropped. "Fewer tests" is never the optimization goal; **fewer
unaffected validations** is.

### Optimize the runner-minute tail, not the median command

Timing receipts must decompose each logical job into:

```text
queue_wait
checkout_materialization
runtime_tool_setup
dependency_preparation
useful_execution
base_replay_or_proof_reconciliation
artifact_publication
teardown
```

Performance work is selected by **runner-minute contribution and tail effect**. A job in
the top decile of aggregate runner-minutes or repeatedly on the critical p95 tail is a
candidate for profiling; a fast job that merely runs often is not automatically a
priority.

The current #7313 and #7323 repairs are examples of the intended method: retain the
semantic contract, profile the actual resource sink, remove the sink, and prove exact
behavioral parity.

Do not prematurely collapse multiple semantic packs into one physical job. Physical
multi-pack batching is eligible for experiment only if, after the checkout/environment
waves, repeated setup + teardown still consumes at least 20% of trusted runner-minutes
on the natural corpus. Otherwise preserve the current per-pack failure isolation and
parallel scheduling.

### Fleet tiers and failure domains

Treat execution profiles as capabilities, not interchangeable CPUs:

| Tier | Role | Initial authority |
|---|---|---|
| hosted control | planner, fences, anchors, merge control, forks/untrusted | preserve |
| local Linux/x86 | ordinary trusted pack execution | PC pool |
| elastic Linux/x86 | measured overflow / heavy-run capacity | future bounded wave |
| macOS/ARM | native compatibility/browser/tool validation | separate validation only |

The current fourth-slot sequence (#7269 -> #6732 -> #6733) remains the only authorized
PC capacity promotion path. Four-slot source/host/prod proof must complete before a fifth
local slot is discussed.

A future bare-metal Linux boot on the PC is a **new execution-profile qualification**,
not free capacity. It must A/B the accepted WSL profile on exact packs, re-prove runner
identity, cgroup/resource law, cache cleanliness, render coexistence, reboot/rollback,
and semantic parity. Full physical RAM/CPU visibility is a hypothesis to measure, not
permission to register extra listeners.

Incoming Apple-silicon Mac minis are not counted as `ci-linux` capacity. Their first CI
role, if used, is the existing device-independent `macos-arm-validation` contract or
other explicitly Mac-native proof. Emulated x86 success cannot silently satisfy the
Linux/x86 merge proof.

### Elastic capacity comes after four-slot proof, but before more permanent boxes

If natural traffic remains above the queue SLO after demand reduction and accepted
four-slot production, compare **one exact heavy-pack corpus** across:

1. the accepted local Linux/x86 profile;
2. a GitHub-hosted larger Linux/x64 runner pool with a prebuilt/custom image when
   available; and
3. only if the native hosted option is materially inferior, an ephemeral self-hosted
   GitHub scale-set/ARC-style profile.

Compare pickup p50/p95, wall p50/p95, semantic parity, setup time, failure rate,
runner-minutes and direct cost. The cheapest accepted result wins; do not assume
self-hosting is cheaper after operator/maintenance failure cost.

Prefer a deterministic first burst policy over a home-grown autoscaler: for example,
main-owned plan classes that are already known to be heavy/full-suite may be benchmarked
on an autoscaling hosted pool while ordinary narrow PRs remain local. If residual demand
later requires true elastic ordinary-PR capacity, use GitHub's existing runner/scale-set
control substrate; do not create a second scheduler or runner registry.

Permanent x86 hardware becomes justified only when a 14-day accepted corpus still shows
steady `rho > 0.65` or sustained paid-burst duty high enough that measured amortized
hardware + power + operator cost wins. A queue spike by itself is an elastic-capacity
signal, not a hardware-purchase proof.

### Agent waiting is a CI defect when it burns reasoning turns

After the final source push for an exact head, an agent may perform the required immediate
readback and then must not remain active merely to poll unchanged CI state.

- Merge-eligible work uses the existing merge-on-green path after its normal release
  gates; a green run does not need a principal watching it.
- A red return is routed by the existing/future W7 classification path to the exact
  producing owner with the failed logical job and evidence.
- HOLD-FOR-SOL / reviewer / worker dialogues use their existing durable watcher/return
  path. If no production-proven return path exists for a required decision, that missing
  bridge is the capability gap; repeated chat polling is not the substitute.
- No session may cancel/rerun another generation merely to improve its queue position.
- Fable and other scarce principals should spend waiting periods only on independent
  principal work. If none exists and durable execution is genuinely running, they yield.

Track **CI polls after final push** as avoidable work. The steady-state target is zero
principal polling loops.

### Incident matrix

| Failure class | Detection | Correct owner/action |
|---|---|---|
| full-suite amplification | plan reason + selected-pack distribution | existing scope/ownership program |
| cross-run starvation | queue wait / older eligible work bypassed | #7276 admission owner |
| `queue: max` occupancy pressure | concurrency-group pending count | demand reduction / approved capacity; never a second queue |
| GitHub-terminal + local worker live | job status joined to Listener PID/start identity | #7315 lifecycle owner |
| cache updater host blast | service CPU/RSS/elapsed + runner pressure | #7222 cache owner |
| one test/job dominates memory/time | logical-job timing/RSS receipt | bounded owning-job optimization |
| Windows/WSL reboot leaves fleet dark | host + GitHub live identity | existing boot-recovery owner |
| PC physical-host loss | live fleet failure-domain receipt | derate `A`; do not count registrations as slots |
| ARM/x86 mismatch | execution-profile identity | separate validation; no semantic substitution |
| stale/superseded head still executing | caller/head/run identity | cancellation contract; zero later runner-minutes |
| main/base red | existing semantic proof + contract-delta | main owner, never feature-author blame |

### Acceptance gauntlet for the horizontal-agent era

Do not declare the program scaled from one quiet successful PR. After the current repair
carriers merge, freeze a natural 14-day acceptance population with at least the existing
20 ordinary green final heads and five heavy heads, plus at least one real burst containing
multiple near-simultaneous PR generations.

The corpus must prove all of:

1. ordinary pickup and final-gate SLOs above;
2. no semantic/coverage regression and zero same-SHA nondeterminism;
3. obsolete generations consume near-zero post-supersession runner-minutes;
4. no terminal GitHub job retains a local slot;
5. no admission queue overflow/cancellation from the 100-pending ceiling;
6. no material starvation of older eligible work;
7. no sustained idle eligible slot while trusted work is pending unless the active
   execution profile intentionally cannot consume that slot;
8. accepted render/nightly coexistence remains intact;
9. exact per-generation runner-minutes and selected-pack distribution are published;
10. principal polling loops are absent from the accepted ship path.

A separate canary/chaos carrier may prove loss of one CI slot and host restart behavior;
do not manufacture destructive failure on production traffic merely to satisfy the
corpus.

### Revised critical path from 2026-09-18

Preserve every existing carrier and its custody. The order of **capabilities**, not a
license to absorb their source, is now:

1. release/prove the incumbent waste and leakage repairs (#7296 manifest bounding,
   #7222 cache updater, #7315 ghost-listener reclamation, and already-landed/local
   hot-tail repairs);
2. release/prove #7276 native admission containment without claiming it raises throughput;
3. complete #7269 -> C3R-B #6732 -> C3P #6733 and prove exactly four local production
   slots;
4. finish measured ownership splitting, immutable dependency/setup work, result reuse
   and empirical balancing under the existing W2-W6 owners;
5. measure whether run-level admission now causes idle-slot head-of-line blocking; only
   then evaluate native slot-lane admission;
6. if the four-slot + demand-reduced fleet still misses SLO, qualify elastic Linux/x86
   burst capacity;
7. qualify Mac minis only for explicit macOS/ARM or other device-native roles;
8. close the loop with event-driven red routing/return so no principal is paid to watch CI.

The parent outcome is not complete when the backlog happens to drain. It is complete when
additional coding sessions can be added without recreating a month-long CI traffic jam,
and the accepted natural corpus proves both low latency and bounded compute amplification.

---

## §0 ACCEPTANCE GATES

Hard SLOs. A wave is not done until its own gate holds **and** no earlier gate regressed.

| Metric | Target |
|---|---|
| structural/preflight failure surfaces | < 2 min |
| CI planner (`ci-plan`) | < 1 min |
| per-pack checkout | < 60 sec |
| ordinary green PR, final push → gate | < 10 min p95 |
| heavy PR | < 15–20 min p95 |
| PR-owned red routed back to producing agent | automatic |
| avoidable cancelled / micro-push runs | near zero |
| same-SHA green→red nondeterminism | **zero tolerated** |

Program-level gates, binding on every wave:

1. **No wave may weaken the semantic proof law.** Base evidence may be *cached* and
   *reused*; it may never be *assumed*. Fail-closed stays fail-closed: absent, expired,
   or contract-changed evidence forces a live replay. A wave that turns a missing proof
   into a pass is rejected outright.
2. **Every latency claim is measured, not asserted.** Before/after numbers from real runs,
   named run IDs, p50/p95 — never "should be faster". Reuse
   `scripts/capture_ci_canary_receipt.py` / `compare_ci_canary_receipts.py` /
   `monitor_ci_host_resources.py` rather than minting a second instrumentation path.
3. **No silent coverage loss.** Any wave that narrows what runs prints what it dropped
   (`::warning`, line-start, bare `print(..., flush=True)` — never through a logger, per
   the CI-guarded house rule). A pack that runs fewer jobs must say so by name.
4. **Designed-red contexts generate zero healing work.** `ci-authority/codex/merge-queue-pilot`
   is intentionally red on main-targeted PRs (#5815); `ci-authority/main` is the binding
   authority. Any classifier that files work against a designed-red is itself a defect.
5. **Each wave ships its own guard + test.** An SLO with no automated check is a wish;
   the next regression re-teaches it by hand.

---

## §1 The problem, as measured

Evidence from 2026-08-17 (two PRs, same afternoon):

- **Planner is a bottleneck, not a router.** `ci-plan` took **6m51s** on PR #5826 — to
  discover changed files and select six jobs. Operator-supplied profile: ~7 min wall,
  with a ~3m47 compute stage. The planner needs a broad repo checkout to answer a
  question that PR changed-file metadata already answers.
- **Checkout dominates execution.** Operator-supplied: pack 3 spent **3m03 materializing
  the repository to execute 53 seconds of work**. The repo is ~19 GB.
- **Pack balance is badly skewed.** Operator-supplied: one pack **13m36**, another
  **53 seconds**. Weights are hand-maintained and stale. Observed on #5823:
  `ci-pack-0` 16m55s vs `ci-pack-3` 4m11s.
- **Structural failures cost a full expensive cycle.** #5823's `ci-pack-0` red was
  `tests/test_agent_routing_control.py is a collecting pytest suite named by no run: step`
  — a *registration* fault, knowable in seconds, that instead surfaced after **16m55s**
  of pack execution.
- **Two-cycle discovery.** That PR's two root failures sat in different packs, so fixing
  one and waiting ~20 min to discover the other was the default path. (This wave's
  companion repair deliberately landed both in one push.)
- **Red is over-reported to humans and agents alike.** GitHub showed four reds on #5823;
  there were **two root causes**, one downstream aggregator (`ci-gate`), and one
  designed-red non-binding receipt. Nothing in the UI or the evidence packet says so.

Consequence: an agent session cannot close its own loop. It pushes, waits ~30 min, reads
an ambiguous red, and cannot tell "my bug" from "main was already broken" from "runner
flake" from "that one is red on purpose".

---

## §2 Waves

Ordered. Each is one PR. W1 is already discharged; W2 is the highest-leverage remaining.

### W1 — Repair #5823 in one push *(DONE, 2026-08-17)*
Wire the orphan suite into its owning job; reproduce and repair the HOUSE-U2 routing
matrix. Landed as `b1fbfd45bcf2` on `claude/fable-agent-routing-control`. Found in
passing, and worth carrying forward as method: the matrix failure split into a **genuine
guard bug** (an `^`-anchored `FABLE-WHY` regex that could never match the documented
`// FABLE-WHY:` JS-comment form, silently denying every fable workflow stage) and
**intended contract tightening** (three tests encoding the superseded contract). A red
pack is not one verdict — classify per assertion before touching either side.

### W2 — Fast Preflight gate (< 2 min), ahead of `ci-plan`
A cheap structural front door that runs **before** any expensive pack launches, and
short-circuits the run on registration/shape faults. Candidate contents, all already
existing as scripts: `audit_unrun_tests.py`, workflow-YAML validity
(`check_workflow_yaml.py`), trigger closure (`check_ci_trigger_closure.py`),
skip-only-suite detection, manifest validation, changed routing-contract checks,
template↔site pair sync, blocklist drift.

Gate: a fault of #5823's class surfaces in **30–120 s**, and the expensive packs
**never launch**. Guard: a test asserting preflight precedes `ci-pack` in the dependency
graph, so a later edit cannot reorder it back.

Watch: preflight must not become a second scoping authority. It answers *"is this diff
structurally well-formed"*, never *"which jobs run"*.

Implementation must specify and test the full dependency/aggregate matrix on the
post-P3B-B workflow: same-repository trusted execution, fork-hosted execution,
`workflow_dispatch` main proof, a no-work PR, malformed/absent planner evidence, and
preflight failure. Uncertainty widens to the existing full-suite path; it never suppresses
work. `ci-gate` must still publish one affirmative conclusion when downstream packs are
lawfully skipped. Checks that can be red on base use the existing differential
base-versus-head contract rather than becoming absolute always-on fleet blockers.

### W3 — Collapse the planner (< 60 s) *(CAPABILITY LANDED; residual work measured only)*
The sparse/tracked planner checkout and preserved selection law have landed. Do not reopen
or duplicate W3. Profile current natural traffic after P4; only a measured residual above
the gate may commission a new optimization carrier. That carrier may feed PR changed-file
metadata directly or further reduce the exact authority/config/scope materialization, but
checkout and compute remain separately receipted.

Gate: `ci-plan` < 60 s p95, with the **identical** job selection as today on a corpus of
replayed real PRs (selection equality is the correctness proof; a faster planner that
picks different jobs is a regression, not a win).

### W4 — Planner-produced per-pack sparse manifests (< 60 s checkout)
The planner already knows which logical jobs a pack owns; it should also emit the files
and dependency roots that pack needs, so a pack materializes a slice rather than 19 GB.
`scripts/ci_scope_dependencies.py` and the existing sparse-worktree machinery
(`config/sparse_worktree.json`, `scripts/worktree_sparse.py`) are the reuse surface.

Gate: per-pack checkout < 60 s; **zero** same-SHA green→red nondeterminism across a
replay corpus. Hard hazard, learned the expensive way in this repo (2026-08-13): a write
into an omitted tree **truncates** the committed artifact, and a guard whose baseline
lives under an omitted tree **over-reports**. Any pack manifest must therefore either
materialize what its jobs read or make the absence loud — never silently thin a tree a
job then writes into. Sparse-blind guards should read omitted bytes from HEAD (the
pattern already established for `check_template_site_sync.py`).

### W5 — Cached exact-base evidence; remove synchronous replay from the red path
Preserve the semantic law; stop paying for it synchronously on every ordinary red. Cache
base evidence keyed by **exact base SHA + job execution digest + proof ID**. Consume
trustworthy existing evidence immediately; live-replay only when evidence is absent or
the execution contract changed. `scripts/ci_semantic_proof.py` is the existing authority
and must remain the single one.

Gate: measured minutes removed from red feedback, with the fail-closed property proven by
mutation — corrupt/expire/contract-shift the cached evidence and confirm a replay is
forced. §0 gate 1 governs: cached, never assumed.

### W6 — Empirical pack balancing
Record checkout, dependency install, head execution, and base-replay time **separately**
for every logical job. Partition on rolling hosted-runner p50/p95 instead of stale
hand-maintained weights. Note `run_ci_pack.py` already rebalances when any job's weight
moves — so pack indices are not stable identifiers, and no report may hard-code one.

Gate: max/min pack wall-clock ratio ≤ 2× on a replay corpus (from the current ~15×:
13m36 vs 53 s).

### W7 — CI Failure Router / healer
Classify every concluded red as exactly one of:

| Class | Advisory disposition |
|---|---|
| `PR_OWNED` | evidence names the producing carrier and exact failed logical job, command, annotations, and changed files |
| `BASE_INHERITED` | evidence names the CI/main owner — **never** the feature author |
| `INFRA_TRANSIENT` | eligible for a later controller-owned bounded retry only after the separate retry gate |
| `NON_BINDING_DESIGNED_RED` | no work generated, ever |
| `UNKNOWN_UNATTRIBUTABLE` | advisory only; no blame, rerun, or work generated |

The classification inputs already exist and are load-bearing: `ship_loop_guard.py`
already distinguishes base-inherited from PR-owned reds (same check red on ≥2 independent
sibling heads, or a green run on a main descendant, with the proof required to *postdate*
the failing check). This wave should **consume** that logic, not fork a second copy.

Gate: on a labelled corpus of historical reds, ≥95% correct classification, **zero**
`BASE_INHERITED` misrouted to a feature author, and zero work items filed against a
designed-red. Hazards: a pack is ONE check, so two partial heals deadlock — the router
must route a pack's whole failure set to one owner; and "not red" is not "green" — a
pending check is not a pass.

The first W7 carrier is **advisory classification only** and writes no work item, message,
rerun, dispatch, scheduler state, or producer-agent assignment. An infra-transient retry
may be added only through the existing merge controller after it proves the exact same SHA
and tested merge tree, owns one bounded retry under the existing concurrency contract, and
cannot race a baseline refresh. No new queue, lease, registry, retry, or lifecycle plane is
authorized by this masterplan.

The implementation seam is one pure `scripts/ci_failure_classification.py` module
extracted under tests from the existing `ship_loop_guard.py` rules. It accepts explicit
immutable check/provenance/timing inputs and returns only the classification plus evidence;
it has no GitHub or filesystem mutation. Both the hook and the advisory reporter import
that module. A labelled fixture corpus must prove parity with the pre-extraction hook and
with every overlapping merge-controller classification before either consumer changes.

### W8 — Definition of done is "delivered", not "PR created"
Sessions (Claude / Codex / Cursor) run the fast local preflight **before** pushing, and
stay responsible through concluded binding CI, merge, and relevant live verification. The
only non-merge terminal states are those already allowed by repository law: a fully
ratified `HOLD-FOR-SOL` or the separately governed actual-external-blocker protocol with
exact evidence. This masterplan does not create a generic `BLOCKED` handoff escape. The
hook layer (`ship_loop_guard.py`) already encodes most of the accountability loop.

Gate: local preflight is one documented command, runs in the same budget as W2, and its
verdict matches CI's for the checks it covers — including **on a sparse worktree**, where
a naive local run is measurably misleading (2026-08-13: 1,281 failures + 419 errors purely
as sparseness artifacts).

### W9 — Runner experiments, *last*
Only after W2–W6. Benchmark larger hosted runners (8-core/32 GB and up) on genuinely
CPU-heavy packs. Rationale for the ordering: paying for 16 cores while spending three
minutes cloning 19 GB and synchronously replaying base failures treats the symptom, not
the architecture.

Keep the self-hosted fleet a **measured option, not an unbounded default**: benchmark the
same heavy pack hosted vs `ci-linux` with the persistent repo cache — the existing canary
is already instrumented for checkout/test/resource comparison. The original one-or-two
slot proposal is superseded by the accepted 2026-08-26 topology: three PC CI slots are
proven, and exactly one fourth slot is the next capacity experiment. All four must share
one enforced aggregate CI resource slice and preserve the independent render reservation.
Do not infer six or eight slots from nominal core count; each increase requires natural
traffic, cgroup pressure, teardown, cache, and concurrent-render receipts from the prior
level. The render budget remains law (~67 min, 4-core-bound), and the nightly/render lanes
retain priority over CI throughput.

The stationary M4 Pro MacBook is a separate native-validation experiment, not a fifth
Linux/x86 pack slot. Its role is one narrow `macos-arm-validation` capability, sealed so
that the same contract can be reconstructed on a replacement M4 mini. It does not acquire
`ci-linux`, `macstudio`, render, merge-control, or generic overflow authority.

---

## §3 Sequencing and ownership

W2 → residual planner measurement → W4 → W5 → W6 → advisory W7 → W8, then W9. The landed
W3 capability is not rerun; any measured residual planner optimization and W4 ship
separately so a planner regression is bisectable.

This document is the program's durable state. A session may take a single wave or carry
several end-to-end — the former one-wave-per-session boundary was repealed 2026-09-01
(`DEC:SESSION-LENGTH-IS-NOT-A-COST-CONTROL`). Per wave, however many a session takes:
read this file, read the latest `research/CI_LATENCY_*_HANDOFF_<date>.md` if present,
build the wave, ship it to merged + verified, then update the handoff before opening the
next one.

## §4 Reuse inventory (do not rebuild)

`ci_semantic_proof.py` (proof authority) · `ci_authority.py` / `ci_authority_paths.py` ·
`ci_scope_dependencies.py` (scope derivation) · `run_ci_pack.py` (partitioning,
`--validate-only`) · `audit_unrun_tests.py` · `check_workflow_yaml.py` ·
`check_ci_trigger_closure.py` · `capture_ci_canary_receipt.py` +
`compare_ci_canary_receipts.py` (hosted vs self-hosted) · `monitor_ci_host_resources.py` ·
`ship_loop_guard.py` (red attribution) · `merge-on-green.yml` (base-inherited-red refresh) ·
`worktree_sparse.py` + `config/sparse_worktree.json`.

## §5 Risks

- **Speed bought with coverage.** Every narrowing must print what it dropped (§0 gate 3).
- **A second scoping authority.** Preflight and the planner must not both decide what runs.
- **Cached proof drifting into assumed proof.** §0 gate 1 is the line; mutation tests hold it.
- **Sparse thinning corrupting artifacts.** W4's central hazard; see the 2026-08-13 receipts.
- **Router blaming authors for main's breakage.** A main break newer than main's last proof
  is *unattributable* for a window — the router must compare merge time to proof time and
  say "unknown" rather than guess. Fail-closed: unattributable is not PR_OWNED.
- **Livelock on the main-proof lever.** Main-ref `ci.yml` dispatches share one
  concurrency group with `cancel-in-progress`, so re-dispatching kills the in-flight proof
  every pinned session is waiting on. Any automation that dispatches a baseline must
  preflight for a live one first.
