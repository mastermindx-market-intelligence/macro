---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/opencode-go-pool
model: local
ended_because: ci_handoff
mission: >
  Continue draft #7142 as the Executive Capacity Fabric's OpenCode Go composition
  checkpoint, on the current Macro main: carry the production-inert provider-account
  selector and its two hermetic suites onto the current manifest, compose the reviewed
  19-line code-gated CI job into the incumbent manifest, and correct this record's
  active evidence and caller contract while retaining the complete original bytes
  exactly once.
  This increment proves selector and synthetic-observation behavior only. It does not
  authorize runtime account switching, credential access, provider calls, enrollment or
  production activation, and it adds no lifecycle or state owner.
state_before: >
  The selector, its two suites and a 19-line code-gated CI job existed on draft #7142 at
  head 7b3da996324ae92c1bf65413acf7666914ae4a54, but that branch's CI manifest was
  composed on a September 2026 base, so its job ordering and neighbours no longer
  described the incumbent manifest. This record's active evidence was also wrong for
  the current source: it attributed 84 parser/selector/transport passes and three-turn
  A->B->C continuity to a two-file Macro command that runs neither the usage parser nor
  the Go transport, and it left the caller contract silent on the request clock, on the
  atomic claim the caller must take before selection, on what membership generation
  identifies, and on what owner-supplied effect metadata proves.
changed:
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-14-OPENCODE-GO-COMPOSITION.md
    what: >
      This record. The frontmatter and body now carry the current evidence, the current
      caller contract and the still-unresolved gates; the complete original 2026-09-14
      bytes are retained once, verbatim, in the dated historical appendix at the end of
      the record.
  - path: engine/provider_account_pool.py
    what: >
      Carried onto current main with unchanged bytes (git blob
      31c2025604f7d7b72bb78b8f7f73c557605e93a0). The secret-free, production-inert
      selector reads owner-supplied observations and selects one member; it neither
      observes, authenticates, routes nor reserves.
  - path: tests/test_provider_account_pool.py
    what: >
      Carried onto current main with unchanged bytes (git blob
      d28eb7586ccba2376d69840266d6da002bbd55b1). The selector suite.
  - path: tests/test_provider_account_pool_composition.py
    what: >
      Carried onto current main with unchanged bytes (git blob
      2b858a0509cc76a966f922cd62d31a1df87ea01f). The observation-composition suite.
  - path: .github/ci/legacy-jobs.yml
    what: >
      The incumbent current-main manifest plus exactly one added code-gated job,
      provider-account-pool, carrying the reviewed 19-line block verbatim. No incumbent
      job was reordered, removed or edited, no gate was migrated, and the two suites
      stay out of the data-only capability-broker job.
prs:
  - 7142
verified:
  - claim: >
      The two composed suites pass on the actual candidate checkout, over the unchanged
      source and test blobs, with a direct exit code.
    command: >
      python -m pytest tests/test_provider_account_pool.py
      tests/test_provider_account_pool_composition.py -q
      (run from the candidate checkout with a unique private base temp, composed from
      parent 7b3da996324ae92c1bf65413acf7666914ae4a54 with frozen main
      69f902ecdf73b23c0cf939e446f99cff7c4a0e4e; the same command the composed CI job
      runs)
    result: >
      36 passed, TEST_EXIT=0, on Python 3.12.3 with pytest 9.1.1. This is the two-file
      suite run in the candidate checkout; it is not the 84-pass composition run and not
      an isolated-fixture result. The run's wall time and its private base-temp path are
      in the evidence log, not in this record, because neither is a reproducible fact.
  - claim: >
      The incumbent planner validates the composed manifest and selects the new job.
    command: >
      python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --gate code
      --validate-only
    result: >
      Exit 0. Validated 316 legacy jobs; 316 in scope; pack weights [5060, 5060]; the
      provider-account-pool job appears in the selected job list.
  - claim: >
      A diff carrying the selector and the two test files selects the new code-gated
      job, under the incumbent selector and scope inference.
    command: >
      python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --gate code
      --plan-only --changed-from 69f902ecdf73b23c0cf939e446f99cff7c4a0e4e
      --emit-plan-json <plan.json> --emit-changed-files <changed.txt>
    result: >
      Exit 0. 5 changed paths, 103 of 316 jobs in scope, plan sha256
      5b87cdbc7c7e55d5c89b8d85bbe97a75ce4b2bfdca17746f900f87119fcc8a95, and
      provider-account-pool is among the eligible jobs. Per-path selection through the
      incumbent select_jobs() also selects provider-account-pool for
      engine/provider_account_pool.py, tests/test_provider_account_pool.py and
      tests/test_provider_account_pool_composition.py.
  - claim: >
      The candidate differs from the frozen base in exactly the five owned paths, the
      three carried source and test blobs are byte-identical to the original head's, and
      the manifest carries exactly one added job with exactly one two-suite command.
    command: >
      git diff --name-status 69f902ecdf73b23c0cf939e446f99cff7c4a0e4e HEAD in the
      candidate checkout; git rev-parse <path> at each of the two heads; parsed
      job-definition comparison of the two manifests.
    result: >
      Exactly the five paths. Blobs 31c2025604f7d7b72bb78b8f7f73c557605e93a0,
      d28eb7586ccba2376d69840266d6da002bbd55b1 and
      2b858a0509cc76a966f922cd62d31a1df87ea01f are unchanged. The parsed comparison
      shows one added job, no removed job, no changed incumbent job, and exactly one
      command naming each suite once.
  - claim: >
      The paired packing-probe measurement against the frozen base is unchanged, so no
      packing ceiling moves and the conditional sixth path is not needed.
    command: >
      scripts/check_contract_delta.py --base 69f902ecdf73b23c0cf939e446f99cff7c4a0e4e,
      and the incumbent packing_probe_measurements() over the incumbent PACKING_PROBES
      on both the base tree and the candidate tree.
    result: >
      Exit 0; 0 introduced and 0 inherited findings. Both sides measure
      templates/index.html 137 jobs / 5912 s / 10 packs,
      scripts/build_free_content.py 137 jobs / 5927 s / 10 packs and
      engine/prophet/plan_book.py 131 jobs / 5668 s / 10 packs, against ceilings
      137/5912/10, 138/5927/10 and 131/5668/10. No breach on either side; the added
      job alone exceeds no probe bound.
  - claim: >
      The complete original bytes are retained once, verbatim, in the dated historical
      appendix, and the extracted archive hashes to the original blob.
    command: >
      extraction of the fenced archive block from this record, then git hash-object and
      sha256sum on the extracted bytes.
    result: >
      The extracted archive is byte-identical to git blob
      288f5b8094d29d2adfd72fcf0948b6ee8c9eb2ae, and the archive block occurs exactly
      once in this record.
unverified:
  - claim: >
      The 84 parser/selector/transport passes and the real three-turn A->B->C
      continuity claimed by the original 2026-09-14 record.
    what_would_verify: >
      Run the named suites on their own bytes in a controlled environment and compare the
      result and the published code/test blob identities to the tested bytes. These two
      Macro files do not import the real usage parser or the Go transport, so the
      two-file command cannot establish the claim.
  - claim: >
      Callback freezing, header forwarding, opaque-response replay protection and
      sensitive-trace suppression in the transport.
    what_would_verify: >
      Run the transport suites themselves on the transport bytes, in the transport
      owner's repository, and compare the published blob identities to the tested bytes.
  - claim: >
      Native MacBook workspace workflow readiness.
    what_would_verify: >
      Replay the native workspace check after resolving the recorded platform block; a
      device ping is not readiness.
  - claim: >
      Real model recall, native installation, account independence, entitlement or
      production canary behavior.
    what_would_verify: >
      Satisfy the applicable native, enrollment, policy and runtime gates, then run the
      bounded real coding-agent task and prove its visible workspace result.
  - claim: >
      Full repository CI, independent review, current-base integration truth and
      release.
    what_would_verify: >
      Run the hosted checks on the exact candidate head, obtain an independent
      non-author exact-head review, reconcile the current base, and have the parent
      accept the release evidence.
unresolved:
  - >
    Rotation-safe enrollment identity, canonical refusal/cooling feedback, reservations
    and accepted pool binding remain pending.
  - >
    The usage endpoint does not supply an identity witness.
  - >
    The MacBook native workspace check was platform-blocked and was not replayed via
    another device.
  - >
    OpenCode's current Terms explicitly restrict multiple-account circumvention; no
    exception was verified, and this composition resolved neither those terms nor any
    provider access, entitlement or policy eligibility.
  - >
    Training-enabled models remain excluded from proprietary workloads; paid overflow
    stays outside this approval.
  - >
    The real usage-parser and Go-transport binding, the shared claim, the streaming and
    cancellation behavior and the application canary remain unproven.
  - >
    The release hold on #7142 stands: current exact-head hosted checks, an independent
    non-author exact-head review and resolved current-base integration truth are still
    outstanding, and this preparation supplies none of them.
next_actions:
  - >
    The parent of this preparation retains source acceptance, publication and release.
    Sol must accept current exact-head hosted checks, an independent non-author
    exact-head review and resolved current-base integration truth before the hold on
    #7142 is released.
  - >
    A live owner that calls the selector must take the existing owner's atomic claim
    and supply its own trusted current request clock before selecting; selection is not
    a concurrency reservation.
  - >
    Use existing provider-home enrollment, transcript custody and broker boundaries,
    and preserve the existing carriers.
  - >
    Only with the applicable native, enrollment, policy and runtime gates satisfied may
    a bounded real coding-agent task run, and its visible workspace result must be
    proved first.
do_not_redo:
  - >
    Do not treat device ping as native workflow readiness, or retry a refused effect
    through a worker or another carrier.
  - >
    Do not make the kernel a worker-private streaming proxy; it remains buffered and
    injected source.
  - >
    Do not treat the selector as an atomic concurrency allocator.
  - >
    Do not overwrite #583's concurrently owned credential/ACL fixes or substitute older
    source.
  - >
    Do not merge or arm #583/#7103/#622/#7142/#7143 through this work.
  - >
    Do not mark `usage_policy_satisfied` true from registration or acceptance of ban
    risk.
  - >
    Do not call these synthetic tests production proof or restore generic AuthError
    switching.
  - >
    Do not read the archived 2026-09-14 bytes as this candidate's evidence; they are the
    dated historical record.
  - >
    Do not read the 36-test result as the 84-test composition result, and do not read a
    planner estimate as runtime execution evidence.
danger_areas:
  - >
    Registration is not credential enrollment or independent entitlement proof.
  - >
    Membership hashing and this record do not grant a post-START pool carrier.
  - >
    No keys were read, enrolled or copied, no provider requests were made, no services
    were installed and no workers were launched.
  - >
    OpenCode's current Terms explicitly restrict multiple-account circumvention; no
    exception was verified.
  - >
    Keep strict provider_capacity.v1, placement and the existing credential owners
    unchanged.
  - >
    The selector is production-inert: it reads owner-supplied observations and selects
    one member. It neither observes nor routes, and it grants no account entitlement.
  - >
    The composed CI job's pip line is retained manifest source. This preparation
    installed no package and triggered no workflow.
---

# Executive Capacity Fabric - OpenCode Go composition checkpoint

## H6 source integration continuation, 2026-11-07

**MISSION_COMPLETE: false. Capability: SOURCE_CONTRIBUTION_VERIFIED / INSTALL_UNPROVEN.**
This is the latest bounded integration addition to the H3 source record below,
under the Chairman's [H6 assignment](https://github.com/mastermindx-market-intelligence/Mastermind/pull/2175#issuecomment-6705879262).

[Full H6 brief](../../research/h6_account_publication/README.md),
[exact composition patch](../../research/h6_account_publication/native.patch),
[19-input / five-output manifest](../../research/h6_account_publication/manifest.json),
[qualification receipt](../../research/h6_account_publication/qualification.json) and
[reproducer](../../scripts/qualify_h6_account_publication.py) are retained on this
original #7142 contribution carrier. No new final branch or control plane was created.

The composition preserves H3 `ef95049fa2e1f8c981497c8a21b643fcbe59f25b`, consumes
H2 `69ead1bdc1b7f6e1b62ef186d955d07cbd718dce`, and targets the exact native inputs
of #2175 `cd557dc05e26b70f2d8f56ad0da2df76a15d74ca`.
Patch SHA256: `06d4bb2d027c7807685c6c5a38a7526777fd0114d9cac02b3dbf6437dc375ffd`.
This combined patch includes H3 already; do not apply both contributions separately.

**Verified delta:** new native claims hold the original native admission lock
through SQLite commit/rollback, sharing the actual compatible policy and quota
publisher's lock. H2 pending/failure/refusal state fences H3's old capacity envelope.
Exact refresh completion identity, canonical cache aliases and file/directory
durability are retained. Original recovery/settlement/release stay available during
publication contention. Four earlier-composition negative controls failed as
expected; composed proof passed **104 native + 43 H2 = 147 tests** with all nineteen
input blobs and five output hashes verified under the incumbent offline boundary.
No provider, credential, selected runtime, native install or useful live turn was
executed. This is SELF_REVIEWED source evidence, not mandatory hosted CI or approval.

**Preserved holds:** the live #2175 final writer's builder/CI effects, the original
J95731 UNKNOWN, #7116 unpublished-source denial and the refused #7142 review remain
on their original owners. The bounded reasoning advisor is ACCEPTED/STOP, and no
worker, watcher or unattended continuation is claimed. Source proof does not
advance programme or runtime acceptance.

**Remaining evidence:** installed caller lock order and every mutable configuration
publisher's participation; actual integer account/window observations, entitlement,
whole-operation no-overage enforcement and settlement coverage; mixed-window and
retention qualification; original final manifests/required CI/release/install;
the ten original H6 primary/worker/physical-account/OS acceptance rows.

**Next action:** the currently assigned #2175 integrator reconciles the active
builder/CI effects, consumes this exact combined source after input verification,
regenerates its original native manifests and runs required exact-head CI. It then
qualifies the installed original owners and one lawful account/budget for the first
useful primary vertical. This checkpoint does not transfer live or unknown effects
and does not require the Chairman to relay routine implementation work.

## Current continuation: H3, 2026-11-07

Current Chairman assignment: complete [H3 — expiration-aware physical-account admission](https://github.com/mastermindx-market-intelligence/macro/pull/7142#issuecomment-6705878444).
The original carrier remains `sol/opencode-go-pool`, with source parent `126c32af2f335ca25201dfc53f51745fc8c38613`.
Governing compatible protected pin: `Mastermind@779fc3be9d07c366bf5b47c650b64e59fc6f3903`.
The remainder of this record preserves the November6 selector-composition checkpoint and dated archive; its prior-head evidence is not relabeled as current H3 or installed proof.

**Current source result:** [H3 contribution and integration contract](../../../research/h3_expiration_account_admission/README.md), an exact native Broker/cache-consumer/test patch against `Mastermind@39bd39aaa8c5fa1f6112fc34c593815323428b2f` for the existing #2175 composer.
[Manifest](../../../research/h3_expiration_account_admission/manifest.json) and [machine receipt](../../../research/h3_expiration_account_admission/qualification.json) retain exact inputs and outputs. The [reproducer](../../../scripts/qualify_h3_expiry_admission.py) reads a supplied native source tree without modifying it and runs disposable fixtures.

Executed exact-patch proof: 16 original input blobs verified; original Broker expected-red discriminator selects `alpha-far`; composed source **91 passed** (32 H3, 24 existing admission, 30 existing effects/recovery and 5 existing fairness). The real Broker lease and Gateway terminal receipt retain `zeta-near` in synthetic observations. Independent windows, strict pins, shared aliases/consumers, reserves, stale/revoked inputs, immutable original recovery, cross-reset liabilities and replayed observations are exercised. The original 36 selector/composition tests and source bytes remain unchanged; they were not rerun or counted in 91.

**State: SOURCE_CONTRIBUTION_VERIFIED / INSTALL_UNPROVEN. H3 user outcome remains incomplete.** H2 owns the actual paired observation producer and account/entitlement qualification. This patch's adapter contract is proposed, not a live producer receipt. Existing execution owners must certify enforceable whole-operation ceilings in upstream units. Terminal/legacy/reset coverage and normal retention are not yet production-qualified. The digest recheck is not a publication mutex: existing Broker and native publisher locks must be composed by the original owner before activation. #2175 retains generation composition, required CI/release, installation and a legitimate useful account-bound canary.

Next source-linked action: reconcile H2's exact successor with the adapter, preserve all outstanding liabilities and the actual shared-scope mapping, compose the existing publication/admission boundary and native manifests on #2175, then prove installed selected=leased=dispatched=settled account and useful accepted result. Return source/CI/install/live evidence separately to Mastermind#983/H6. No replacement branch, provider call, credential operation, installed generation change or daemon was created here. #7116's unpublished-source denial and the refused #7142 review effect were not replayed. Actual release/security holds remain; the current Web waiver is not self-approval or merge authority.

## Retained November6 checkpoint

Record identity: `HND/EXECUTIVE-CAPACITY-FABRIC-2026-09-14-OPENCODE-GO-COMPOSITION`,
filed under `WS:EXECUTIVE-CAPACITY-FABRIC`, created 2026-09-14 - the git add date of
this path and the date carried in the record key. The 2026-09-14 revision of this
record was authored under `model: sol`; this 2026-11-06 revision was composed by a
host-run local agent under the Chairman's oldest-first completion assignment
`macro-backlog-oldest-first-20261105-c3` (Mastermind#2028), preparation identity
`macro-pr7142-selector-record-composition-20261106-c3-a1`, a normal paid
`fix_build / C1_ROUTINE_BOUNDED` local preparation of draft #7142. The parent retains
source acceptance, publication and release.

The complete original bytes of this record - frontmatter, body and final newline - are
retained once, verbatim, in the dated historical appendix at the end of this record.
They are the dated historical evidence. They are not this candidate's evidence.

## What this increment proves, and what it does not

This increment proves selector and synthetic-observation behavior only. It composes the
production-inert selector and its two hermetic suites onto the current Macro main
manifest, composes the reviewed 19-line code-gated CI job into the incumbent manifest,
and corrects this record's active evidence and caller contract. It does not authorize
runtime account switching, credential access, provider calls, enrollment or production
activation, and it introduces no lifecycle or state owner.

## Active current interpretation

1. **Scope of the two suites.** `tests/test_provider_account_pool.py` and
   `tests/test_provider_account_pool_composition.py` demonstrate selector and synthetic
   observation behavior. They are not the 84 parser/selector/transport passes the
   original record attributed to the two-file command. They do not import the real
   usage parser or the Go transport, and they do not prove three-turn A->B->C
   continuity, callback freezing, header forwarding, opaque-response replay protection
   or sensitive-trace suppression.
2. **The request clock.** `now=None` evaluates at `snapshot.generated_at`. A live owner
   must supply its own trusted current request clock; the selector never infers one.
3. **The claim.** The caller must acquire the existing owner's atomic claim before
   selection. Selection is not a concurrency reservation.
4. **Membership generation.** The generation identifies membership only. It is not an
   observation version, a reservation token, or a post-START carrier.
5. **Unknown quota.** Unknown quota stays unknown, and an elapsed reset time does not
   manufacture a fresh observation.
6. **Effect metadata.** `effect_state='proven_no_effect'` is owner-supplied metadata. It
   is not, by itself, proof of no effect.
7. **Rollover.** Only an actually proven pre-effect usage-limit refusal supports the
   intended in-pool rollover. Auth errors, ambiguous failures, timeouts, partial streams
   and uncertain cancellation do not authorize account replay.

## Historical evidence, attributed as historical

- **2026-09-14, the original record**, archived verbatim in the appendix: the
  composition checkpoint, the cross-repository receipts, the recorded 84-pass synthetic
  Linux sandbox run, and the gates left open.
- **2026-11-04, review 5766694663 by MastermindX1** on head
  `7b3da996324ae92c1bf65413acf7666914ae4a54`: fresh qualification on Python 3.14 with
  pytest in a new isolated temporary fixture, over the three source and test blobs
  above plus the empty `engine/__init__.py`, with
  `python -m pytest -q --confcutdir <isolated-root> tests/test_provider_account_pool.py
  tests/test_provider_account_pool_composition.py`; 36 passed in 2.01s, `TEST_EXIT=0`.
  That review explicitly supersedes the original record's attribution of 84 tests and
  of three-turn continuity to the two-file command. It is a historical result on the
  original head, not this candidate's run.
- **Hosted CI 35957117275 and fences 35957117136** bind the original head
  `7b3da996324ae92c1bf65413acf7666914ae4a54` only. Their historical tested merge tree
  used a September 2026 base and is not current-base integrated CI.
- **2026-11-06, this candidate**: the current-source composition and the focused proof
  recorded in the frontmatter's `verified` list. The two suites ran on the actual
  candidate checkout, not in an isolated fixture.

## Current gates and non-goals, still unresolved

Rotation-safe enrollment identity, canonical refusal/cooling feedback, reservations and
accepted pool binding remain pending. The usage endpoint does not supply an identity
witness. Registration is not credential enrollment or independent entitlement proof.
The MacBook native workspace check was platform-blocked and was not replayed via
another device. OpenCode's current Terms explicitly restrict multiple-account
circumvention; no exception was verified, and this composition resolved neither those
terms nor any provider access, entitlement or policy eligibility. Training-enabled
models remain excluded from proprietary workloads, and paid overflow stays outside this
approval. The parser and transport binding, the shared claim, the streaming and
cancellation behavior and the application canary remain unproven.

The kernel remains buffered and injected source, NOT a worker-private streaming proxy.
The selector is not an atomic concurrency allocator. Keep strict `provider_capacity.v1`,
placement and the existing credential owners unchanged. Membership hashing and this
record do not grant a post-START pool carrier. #583 is concurrently owned and has
advanced; do not overwrite its credential and ACL fixes, and do not substitute older
source.

## Exact next action

The parent of this preparation retains source acceptance, publication and release.
Before #7142 can leave its release hold, that parent needs Sol's acceptance of current
exact-head hosted checks, an independent non-author exact-head review, and resolved
current-base integration truth. This preparation supplies none of those three, and it
arms, marks ready and merges nothing.

A live owner that calls the selector must, before selecting, acquire the existing
owner's atomic claim and supply its own trusted current request clock. A rollover is
authorized only by an actually proven pre-effect usage-limit refusal.

## Historical appendix - the original 2026-09-14 record, archived once

The bytes between the fences are the complete original file - frontmatter, body and
final newline - exactly as they were on the original head, with no edit of any kind.
They are retained for the dated evidence only.

<!-- BEGIN ARCHIVED ORIGINAL BYTES: created 2026-09-14; git blob 288f5b8094d29d2adfd72fcf0948b6ee8c9eb2ae -->
```text
---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/opencode-go-pool
model: sol
ended_because: ci_handoff
mission: >
  Continue draft #7142 as the Executive Capacity Fabric's OpenCode Go composition checkpoint:
  compose the already-tested parser, selector and transport pieces, preserve account-shared usage
  semantics, request-time freshness and exclusion identity, document the exact implementation and
  test receipts, and keep every runtime, enrollment and policy gate explicitly unresolved.
state_before: >
  Three separately tested source pieces had no proven composition. Parser floating-point output was
  rejected by the selector, exclusions had no stable-membership input, freshness was checked only at
  snapshot time, and AuthError triggered account switching.
changed:
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-14-OPENCODE-GO-COMPOSITION.md
    what: >
      This continuation record: the composition checkpoint, the exact Macro and Mastermind
      implementation receipts, the synthetic Linux test result, the unproven native and production
      gates, the policy boundaries, and the exact next action.
  - path: engine/provider_account_pool.py
    what: >
      Compose existing Macro usage rows into account-shared observations; support fractional
      percentages, request-time freshness, exclusions without changing membership identity, reset
      re-observation and exhausted-status precedence; and add transport behavior that freezes request
      state before callbacks, limits forwarded headers, rejects opaque account-scoped replay context,
      suppresses sensitive ordinary repr/tracebacks, and stops on AuthError.
  - path: tests/test_provider_account_pool.py
    what: >
      Add the provider account pool suite exercised in the record's Linux sandbox result.
  - path: tests/test_provider_account_pool_composition.py
    what: >
      Add the combined parser/selector/transport composition suite exercised in the record's Linux
      sandbox result, including the three-turn continuity test.
  - path: .github/ci/legacy-jobs.yml
    what: >
      Wire the two provider account pool suites into a new hermetic `gate: code` job rather than
      appending them to the `gate: data` capability-broker job.
prs: []
verified:
  - claim: "The recorded Linux sandbox run passed 84 synthetic pool, transport and combined parser/selector/transport tests."
    command: >
      In the record's Linux sandbox with Python 3.13.5 / pytest 9.0.2: `python -m pytest
      tests/test_provider_account_pool.py tests/test_provider_account_pool_composition.py -q`
    result: "36 pool tests, 41 transport tests and 7 combined parser/selector/transport tests; 84 passed."
unverified:
  - claim: "The three-turn test preserves one process, temporary workspace marker, model, local tool-result transcript and session across simulated A/B/C successes."
    what_would_verify: >
      Run the named suite on the exact implementation bytes in a controlled environment and compare
      its result and published code/test blob identities to the tested bytes.
  - claim: "Native MacBook workspace workflow readiness."
    what_would_verify: >
      Replay the native workspace check after resolving the recorded platform block; a device ping is
      not readiness.
  - claim: "Real model recall, native installation, account independence or production canary behavior."
    what_would_verify: >
      Satisfy the applicable native, enrollment, policy and runtime gates, then run the bounded real
      coding-agent task and prove its visible workspace result.
  - claim: "Full repository CI, independent review or Agent OS store validation."
    what_would_verify: >
      Run full repository CI, independent source review and current-parent reconciliation, then run
      Agent OS store validation.
unresolved:
  - "The MacBook native workspace check was platform-blocked and was not replayed via another device."
  - "Rotation-safe enrollment identity, canonical refusal/cooling feedback, reservations and accepted pool binding remain pending."
  - "The usage endpoint does not supply an identity witness."
  - "No exception to OpenCode's current Terms restricting multiple-account circumvention was verified."
  - "Training-enabled models remain excluded from proprietary workloads; paid overflow stays outside this approval."
  - "Full repository CI, independent review and Agent OS store validation were not established by the recorded synthetic run."
next_actions:
  - "Sol should complete the reviewed single-account streaming harness binding on the existing #622 carrier after independent source review and current-parent reconciliation."
  - "Use existing provider-home enrollment, transcript custody and broker boundaries."
  - "Only with the applicable native, enrollment, policy and runtime gates satisfied may a bounded real coding-agent task run."
  - "Prove its visible workspace result first; an approved pooled rollout additionally needs real identity, A/B/C continuity, cancellation/partial-stream safety and simultaneous-claim proof."
  - "Preserve existing carriers and retrieve the full checkpoint before continuing."
do_not_redo:
  - "Do not treat device ping as native workflow readiness, or retry a refused effect through a worker or another carrier."
  - "Do not make the kernel a worker-private streaming proxy; it remains buffered/injected source."
  - "Do not treat the selector as an atomic concurrency allocator."
  - "Do not overwrite #583's concurrently owned credential/ACL fixes or substitute older source."
  - "Do not merge or arm #583/#7103/#622/#7142/#7143 through this work."
  - "Do not mark `usage_policy_satisfied` true from registration or acceptance of ban risk."
  - "Do not call these synthetic tests production proof or restore generic AuthError switching."
danger_areas:
  - "Registration is not credential enrollment or independent entitlement proof."
  - "Membership hashing and this record do not grant a post-START pool carrier."
  - "No keys were read/enrolled/copied, provider requests made, services installed or workers launched."
  - "OpenCode's current Terms explicitly restrict multiple-account circumvention; no exception was verified."
  - "Keep strict provider_capacity.v1, placement and existing credential owners unchanged."
---

## Executive Capacity Fabric - OpenCode Go composition checkpoint

Parent: `WS:EXECUTIVE-CAPACITY-FABRIC`; owner Sol; capability state PARTIAL / BUILT_NOT_PROVEN. This is a continuation record on draft #7142, not a new workstream, runtime assignment or final acceptance.

Procedure pin: protected Mastermind `51b815ab9527e15c9218b049f622dc4d3e0bfbc4`, Skillpack 1.0.1 / bootstrap 1. Current Chairman explicitly continued the existing program and reported all three Go registrations ready. Registration is not credential enrollment or independent entitlement proof.

## Source change and evidence

Before: three separately tested source pieces did not have a proven composition; parser floating-point output was rejected by the selector, exclusions had no stable-membership input, freshness was checked only at snapshot time, and AuthError triggered account switching.

After: existing Macro usage rows compose into account-shared observations; selector supports fractional percentages, explicit request-time freshness, exclusions without changing membership identity, reset re-observation and exhausted-status precedence. Existing transport freezes request/model/context before callbacks, limits forwarded headers, rejects opaque account-scoped context for replay, suppresses sensitive ordinary repr/tracebacks, and stops on auth errors. Neither membership hashing nor this record grants a post-START pool carrier.

Exact implementation receipts:
- Macro #7142: `814e6d4e6aaa13d27f9302febf954a780923db6c`.
- Macro #7143: unchanged `d8127bded3a9a35bc501e786d27fa32f0ecdd923`, still stacked on #7103.
- Mastermind #622 implementation: `f68fc0c62552bfd4a4994792698e7064899d008f`.
- Mastermind #622 cross-repo proof: `a2a529e6d633b2e6aa522b294d531fa4db525de0`.
- Full checkpoint: Mastermind `097e1bac090be8f254013a2729e0f7ef69c94054`, `docs/OPENCODE_GO_COMPOSITION_CHECKPOINT_2026-09-14.md`.

Linux sandbox, Python 3.13.5 / pytest 9.0.2: 36 pool tests, 41 transport tests, 7 combined parser/selector/transport tests; **84 passed**. Published code/test blob identities matched tested bytes. The three-turn test preserves one process, temporary workspace marker, model, local tool-result transcript and session across simulated A/B/C successes. All credentials, provider usage and inference outputs are synthetic. No real model recall, native installation, account independence or production canary was proven. Full repository CI, independent review and Agent OS store validation were not established by this run.

## Current gates and non-goals

The MacBook native workspace check was platform-blocked and was not replayed via another device. No keys were read/enrolled/copied, provider requests made, services installed or workers launched. Do not treat device ping as native workflow readiness, and do not retry a refused effect through a worker or another carrier.

The kernel remains buffered/injected source, NOT a worker-private streaming proxy. The selector is not an atomic concurrency allocator. Rotation-safe enrollment identity, canonical refusal/cooling feedback, reservations and accepted pool binding remain pending. The usage endpoint does not supply an identity witness. Keep strict provider_capacity.v1, placement and existing credential owners unchanged.

#583 is concurrently owned and has advanced; do not overwrite its credential/ACL fixes or substitute older source. This work does not merge or arm #583/#7103/#622/#7142/#7143. Older PR body statements about automatic auth rollover are superseded by the narrower implementation and checkpoint, not evidence of live behavior.

OpenCode's current Terms explicitly restrict multiple-account circumvention. Do not mark `usage_policy_satisfied` true from registration or acceptance of ban risk. No exception was verified. Training-enabled models remain excluded from proprietary workloads; paid overflow stays outside this approval.

## Exact next action

Sol should complete the reviewed single-account streaming harness binding on the existing #622 carrier after independent source review/current-parent reconciliation. Use existing provider-home enrollment, transcript custody and broker boundaries. Only with the applicable native, enrollment, policy and runtime gates satisfied may a bounded real coding-agent task run. Prove its visible workspace result first; an approved pooled rollout additionally needs real identity, A/B/C continuity, cancellation/partial-stream safety and simultaneous-claim proof.

No Fable or other worker was commissioned; no watcher is waiting. Preserve existing carriers and retrieve the full checkpoint before continuing. Never call these synthetic tests production proof or restore generic AuthError switching.
```
<!-- END ARCHIVED ORIGINAL BYTES -->
