# Neural Web Brain revival: source architecture and implementation plan

Operation: `brain-revival-20261112-c2`  
Source basis: Macro `1a9079a89d8ef934ceb84c449f37a98691d979f6`  
Procedure basis: Mastermind `0e1ca7a2d8aa95ac415191d64bd3a39212be39d0`

This document contains public-source analysis and proposed implementation only.
Production observations and private operational evidence are excluded.

## Outcome

Extend the original Neural Web into continuously available, evidence-backed product
and estate intelligence, using existing execution owners. A complete journey is:
changed evidence → bounded admitted interpretation → retained result → consumer
use → verified outcome or explicit unresolved failure. An animated graph, model
response, source merge or green test alone does not establish that journey.

This extends `research/NEURAL_WEB_MASTERPLAN_BY_FABLE.md` and existing Eval OS
contracts. It is an editorial task tree, not a new task store or runtime authority.

## Existing source to reuse

- `engine/neuralweb/cortex.py`: bounded tool loop, input-change gate, memo,
  attention and hypothesis surfaces.
- `engine/neuralweb/health.py`: Neural Web health publication and existing
  downstream dependency support.
- `engine/neuralweb/constitution.py`: observation/explanation, probation and
  stronger authority boundaries.
- `admin/intelligence_os.py`: pure T1/T4 evidence derivation, explicitly not a
  persisted estate-health database.
- `admin/intelligence_execution.py`: Linux process envelope, 45-second work
  deadline, two-second cleanup allowance and explicit failure codes.
- `admin/static/app.js`: existing admin navigation and consumer views. Its
  common GET deadline is 30 seconds; the evidence path must receive its bounded
  response rather than losing it to that shorter client deadline.
- `admin/CAPACITY_ROUTER.md`: existing router-observation ownership and the
  difference between configured routes, observed inference and task execution.
- Existing Executive/Fabric admission, Agent OS continuity and GitHub delivery.
  Reuse those owners; do not create a parallel agent queue or fleet.

## Architectural decision

One Brain experience, with distinct responsibilities behind it.

| Responsibility | Owner |
| --- | --- |
| Market evidence, domain interpretation, contradictions, hypotheses | Existing Macro data/Neural Web/Cortex owners |
| Engine identity, evidence quality and output health | Existing T1/T4/Eval OS |
| Durable work, admission, attempts, leases and capacity | Existing Executive OS and Capacity Fabric |
| Code repair, tests, PRs and release | Existing development team and GitHub workflow |
| Program continuity and accepted decisions | Agent OS |
| Human understanding and exploration | Existing admin/product shell |

The application host serves APIs, evidence readers and product consumers.
Model inference uses the incumbent provider transport. Specialist roles should
start as bounded task contracts; a permanent process per role is unnecessary.

Prefer the qualified economical Flash worker through the existing router for
bounded extraction, diagnosis and synthesis. Resolve actual model identity and
eligibility from its owner. A model preference does not widen a governance grant,
create credentials or authorize direct-provider fallback.

Self-improvement means evidence of a problem, a versioned intervention through its
owner, and a measured consumer outcome. Learned context does not grant trade,
permission, publication or release authority.

## Dependency graph and acceptance

### R1 — Truthful liveness and useful failure states

1. Align the evidence GET deadline with the existing bounded server envelope.
   Keep ordinary reads bounded and preserve write/caller-signal behavior.
2. Show a bounded typed error and manual retry on the existing Intelligence OS
   initial-error surface. Preserve available prior evidence with its timestamp;
   never label it current after a failed refresh.
3. Qualify Cortex memo freshness by content time and its declared cadence/SLA.
   Missing or malformed clocks/status cannot be healthy; deploy mtime cannot
   establish memo freshness.
4. Advance Cortex's existing input-change gate only after a structurally valid
   current-run memo is verified. Missing, corrupt, stale or malformed output
   must not suppress the next eligible recovery attempt.

Proof: focused executable regressions, existing relevant suites, exact-candidate
hosted checks, normal release and actual admin/next-run consumer verification.

### R2 — Bounded estate awareness (after R1)

Read one coherent canonical estate-evidence observation per deliberation and
reuse it within the run. Retain generation, source clock, blind/unavailable counts,
affected consumers and evidence references. Extend the existing change gate with
meaningful content changes, not observation time alone. Store the interpretation
in the incumbent memo/findings surface, never a persisted clone of the Eval OS panel.

Qualify the preferred Fabric-backed worker on structured read → diagnosis →
result, preserving tool/result identity and served-model attribution. Existing
production-mode and streaming/tool gateway contracts remain owners.

### R3 — Continuous execution (after R2 and runtime qualification)

Use the incumbent admission/scheduling/attempt/return mechanism. Reconcile the
existing nightly writer before altering cadence or placement. Require one writer,
bounded concurrency and budget, duplicate/restart reconciliation, unchanged-input
suppression and actual result consumption. Engineering work is a narrow admitted
handoff to the existing development team, not shell or deploy tools added to Cortex.

### R4 — Coherent admin Brain (after R2/R3 contracts)

Explain what changed, what is known, what is running, affected consumers, verified
improvements and unresolved decisions. Reuse Observatory, Intelligence OS, existing
Brain conversation and Capacity Router. Keep market relationships distinguishable
from execution dependencies. Preserve the accepted shell and shared design system.

## Compatibility and source custody

- Preserve Macro #11148's living-map renderer and visual evidence. This operation
  does not recreate that work; its app.js Synapse hunks are distinct from R1's
  evidence/read-deadline functions.
- Preserve #10171's engine-filter count repair; do not duplicate it.
- Preserve #10725/#10902's AI Brief recovery and #10727's provider composition,
  including their current release holds.
- Preserve the accepted T4 substrate; this is follow-on consumer hardening.
- No new scheduler, queue, watcher, credential owner or independent memory store.

## Delivery frontier

Source implementation, hosted CI, merge, installation and real-path acceptance
remain distinct. Save verified changes and exact proof here. The parent goal stays
open until the complete consumer journey is demonstrated. This plan grants no new
runtime authority and contains no production census or private diagnostics.
