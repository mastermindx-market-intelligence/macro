# Reflex evidence integrity — R8 source-root isolation

**BUILT_NOT_PROVEN / PARTIAL. MISSION_COMPLETE:false. Same PR #8154 remains DRAFT / HOLD-FOR-SOL.**

Operation `prophet-risk-reflex-record-integrity-20260928-sol-001`; branch
`claude/prophet-reflex-record-integrity-20260928`. R8 begins at exact head
`98b2fa535551eecd407aa7ea54afc0070d94d179`. The primary lead retains source
responsibility under the current Chairman continuation and software self-audit
exception. This is not independent review or financial-policy promotion.

## Why this belongs to the policy critical path

Future Grey Deer rules must name which registered rule and observation produced
an assessment. R7 fixed the native firing writer's reserved metadata. While
binding the first-policy source contract, R8 found a second defect in that SAME
existing module: `load_registry(root)` returned its one global cached mapping
without checking which root had supplied it.

An actual-module witness used two fictional fixture roots. Root A contained only
`policy_a`; root B contained only `policy_b`. Loading A then B returned `policy_a`
for BOTH. A missing or invalid second source could likewise be hidden by the
first source's successful cache. This is a reproduced source-selection defect,
not a demonstrated production policy, bad trade, or authorization exploit.

## Small native repair, not a new control plane

The existing single cache entry now associates the resolved registry path and
mapping in ONE tuple. A read takes one local cache snapshot. Selecting a different
root loads and validates that source; selecting a canonical alias of the same
root reuses the cache. One assignment keeps path and contents paired when root
reads overlap. `invalidate_cache()` clears the entry.

The prior same-root contract remains: changed contents at the same path require
`force=True` or explicit invalidation. No mtime watcher, digest service, reload
loop, new registry or policy state machine is added. Return mappings remain the
same API species. This repair is not an immutable-snapshot/grant verifier and
does not certify every historical record or external dynamic caller.

The R7 firing repair is retained: caller payload cannot replace `claim_id`,
`reflex`, `claim_family`, `desk`, or mandatory `is_context_only=True`. Original
key ordering, normal serialized bytes, claim-ID algorithm, nonreserved fields,
append behavior and fail-soft write handling are unchanged. No existing firing
or registry file is rewritten. Context-only evidence never confers gate, size,
execution or earned-policy authority.

## Discriminating executed tests

The exact native module and existing writer/load suites run with eleven added
root-isolation tests. Final selected inventory: **31 tests**.

* Original R7 module against the final suite: **8 failed / 23 passed**.
* Repaired module: **31 passed**, no failures.
* The original-code test replaced only the isolated fixture module; fixed bytes
  were restored and hash-verified afterward. No live application was patched.

Cases cover alternating roots, absent/invalid second registry, forced refresh,
explicit invalidation, relative paths after cwd change, default/explicit roots,
symlink retargeting, canonical alias reuse, and 160 concurrent reads across four
fixed fixture roots. Those concurrent reads are not 160 statistical samples.
The earlier 20 writer/load cases retain their original metadata and byte-parity
proof. No native producer, query adapter or market-outcome proof is claimed.

Command:

```
python3.12 -m pytest tests/test_reflexes.py::TestRecordFiring \
 tests/test_reflexes.py::TestLoadFirings \
 tests/test_reflexes.py::TestRegistryRootIsolation \
 --basetemp <owned-test-directory> -q
```

Red log SHA256 `ab073a356cf0ca8a37417d8006c6c2a87edc0f374986928532f70a6091ab04da`.
Green log SHA256 `61f0d6ff93d29e24d178e1c17bc116ace18799f56554829040a2426d15136468`.
Fixed module SHA256 `e7f7e160e3db5d72d58d0c2369df6a2687b80cb6193977e575d50dcc1af72f63`.
Test file SHA256 `8221b9c10aacb4370f9cee927ca3fb0adf681b389fd705238ed575cd265b694f`.

Existing `neural-web-core` now selects the additional root-isolation class.
Exactly one existing command is appended; all other YAML/job/path content is
preserved. This registers 31 cases, not every class in `tests/test_reflexes.py`.

## Current release evidence and limits

R7 head98b2fa5's hosted CI run36430924429 and fences completed successfully.
That proof remains historical for its exact source; R8 changes executable
semantics and needs the new head's CI and self-audit before source acceptance.
No Ready, merge, auto-merge, deployment or background worker is requested by
this source update.

The separate GD6A PR#8141 stays frozen at54cf589ffdc43538e80996ffac3831830e7f188a.
Its CI run36411935277 passed, but latest-base integration remains incomplete.
A fresh bounded tree census for the Reflex lane compared source roots between
704d6b8ae9953ed8949264d73b5b6f9a4d65dd36 and
4e30aa69d89ac444dd3344ffc7c3d1e212c71107: seven changed paths, no engine/lib
source changes, and no root-file changes in that census. It is not a complete
runtime-data proof. Further CI-owner source/artifact/manifest-comparison requests
were refused before dispatch and were not repeated or proxied. Therefore no
unqualified current-base release is inferred from either successful older run.

## First-policy decision boundary

The existing Grey Deer freeze separates measured state, hazard and per-rule
capital authority. Do not invent a permanent rule or a temporary grant from this
loader repair. Before nonzero policy consumption, the original owner must bind:
registered policy/rule/version; authority basis and actual grant; market/asset/
candidate/lifecycle/exposure scope; start/expiry/revocation; evidence/episode
receipts; policy-specific lift conditions; and lossless counterfactuals.

R8 confirms why source-root identity is part of that binding. A cached map or
`is_context_only` flag is not proof of any of the above. Seat A's earlier
16:30-versus-native-17:00 settled-source question stays open; no decision clock,
threshold, trial or dataset has been silently changed. Missing evidence must
not remove an independently active policy before its own expiry, and one rule's
repair must not lift another rule. Those are next-policy requirements, not
capabilities this PR claims to have shipped.

## Continuation

Consume exact new-head CI, including the selected registry test class. Resolve
actual findings under this same source operation. After complete release
qualification, prove a normal native writer/reader use without rewriting history.
Preserve the separately held #8141, H1/Cycle, original Prophet CEO and Seats A-D.
No new event store, portfolio action, user alert, policy threshold or automatic
wake has been introduced.

Protected procedure pin: Mastermind
`bf709270f29f5445288e8f453fe82f6c4dd389b4`, compatible Skillpack1.0.1/bootstrap1.
Current source and all effects remain on the same native GitHub carrier. Prior
refusals remain scoped and are not converted into blanket service outages.
