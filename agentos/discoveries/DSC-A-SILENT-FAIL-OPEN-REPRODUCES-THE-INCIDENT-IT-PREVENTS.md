---
key: A-SILENT-FAIL-OPEN-REPRODUCES-THE-INCIDENT-IT-PREVENTS
claim: >
  A guard that correctly fails OPEN on an unverifiable input, and says nothing when it does,
  reproduces the exact incident it was built to prevent — on precisely the host and precisely the
  conditions it was written for. The ThetaData resolver's emptiness check must fail open, because
  the three tier dirs are SYMLINKS onto an external volume whose listing hangs or is denied under
  launchd; `_RESOLVABLE = (_HAS_ROOT, _UNKNOWN)` encodes that. But `_UNKNOWN` resolves a real
  `Path`, and the consumer's own alarm —
  `scripts/build_options_intel_brief.py:166-171` — prints its `::warning` only when
  `store is None`. So on the M1, under launchd, with the tier listing denied, the drained store
  resolves, the `None` branch never runs, the producer exits 0, and the blank board publishes with
  no diagnostic anywhere. The guard is not bypassed by a bug; it is bypassed by its own correct
  behaviour, and the only reason it looked safe in review is that the fail-open branch is
  unreachable from a shell (an ssh session lists those symlinks fine — the divergence
  `scripts/build_options_hub_nightly.py:170-172` already documents).
falsifier: >
  `python3 -m pytest tests/test_thetadata_resolver.py::TestFailingOpenIsNeverSilent -q` (3 tests).
  Mutation-tested two ways on PR #8203: routing the annotation through `log.warning` instead of a
  bare `print` -> 1 failed (the house-law violation that makes GitHub silently drop the line), and
  firing it unconditionally rather than only on `_UNKNOWN` -> 1 failed. If a future change makes
  the resolver take the `_UNKNOWN` branch without emitting
  `::warning title=thetadata-store-unverified::` at line start, this claim's fix is refuted.
  NOTE a deleted-`print` mutant is NOT a valid test of this: it leaves a dangling `if` and the
  suite reports a collection ERROR, not a failure — that mutant never runs and proves nothing.
so_what: >
  Three things. (1) Do not "simplify" the `thetadata-store-unverified` annotation away or route it
  through a logger — it is the ONLY evidence that separates "built from a verified store" from
  "built from a store we could not read", and a logger prefix makes GitHub drop it silently
  (tests/test_gh_annotation_line_start.py). (2) When an options/ThetaData artifact is blank or
  stale, grep the lane's CI log for `thetadata-store-unverified` BEFORE diagnosing placement or
  data: if it fired, the store was never verified and the artifact is not evidence about the
  store's contents. (3) Generally — when adding a fail-open branch to any guard, ask where the
  alarm for that branch lives. An alarm attached to the fail-CLOSED path (here, `store is None`)
  does not cover the fail-open path, and the fail-open path is the one that runs in production.
kind: landmine
verified_at: 2026-09-29
verified_by: "PR #8203, merge 54f62e4d4b25c4e475ece482aff856d052e42e67; tests/test_thetadata_resolver.py::TestFailingOpenIsNeverSilent; engine/thetadata_store.py:320-332"
scope:
  - macro
  - engine/thetadata_store.py
  - scripts/build_options_intel_brief.py
  - WS:ADVANCED-DATA-OPTIONS
confidence: verified
---

## The shape

```
store drained + tier listing readable    -> _NO_ROOT  -> refused, ::error fires      (the fix works)
store drained + tier listing DENIED      -> _UNKNOWN  -> RESOLVED, silence           (the incident)
store healthy + tier listing DENIED      -> _UNKNOWN  -> RESOLVED, silence           (why it must fail open)
```

Rows 2 and 3 are indistinguishable to the resolver — that is not a defect, it is the honest
state of knowledge, and refusing row 3 would disable a production data path across several
nightly lanes (mutation-tested: narrowing `_RESOLVABLE` to `(_HAS_ROOT,)` fails 4 tests).

The defect was that rows 2 and 3 were also indistinguishable to the *operator*. The annotation
makes the resolver say which row it is on, which converts a question nobody could measure from
this host into one the M1's own next run answers in its log.

## Why this was not visible in review

The fail-open branch cannot be reached from an interactive shell on the store host: ssh lists the
tier symlinks without complaint. It is reachable only under launchd, where TCC/removable-volume
policy denies the listing — the same divergence `build_options_hub_nightly.preflight_store`
already bounds in a daemon thread. So "I checked on the host and it was fine" is not evidence
about this branch, and a reviewer who checks that way will conclude the branch is dead.
