---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/vps-site-fabric-20260915-sol
model: sol
ended_because: blocked
mission: >
  Integrate VPS/site AI with the existing local capacity fabric, protect Fable's
  developer capacity, and define safe account/model propagation without creating
  a second control plane. This handoff covers the first opt-in source guard,
  not a completed production migration.
state_before: >
  Macro build_providers automatically appended attached Codex and expanded Claude
  OAuth. No workload purpose separated product inference from native development.
  The key pool modeled seven Claude and three Codex slots; user-reported current
  inventory is four Claude and five Codex accounts, not independently verified.
changed:
  - path: engine/provider_workload_policy.py
    what: >
      Closed, size-bounded transport policy validation and host/caller intersection;
      typed refusals and non-secret content-identity receipts. No provider calls,
      quota claim, credential store, worker spawn or second router.
  - path: config/provider_workloads.v1.json
    what: >
      Four inference purposes and three native-agent purposes. Native subscription
      transports cannot be enabled in inference by broadening the manifest.
  - path: engine/llm_auth.py
    what: >
      Apply optional trusted server/caller profile before credential reads or Codex
      discovery; no implicit Codex or default nonempty list in profiled mode.
      Legacy behavior remains unchanged when neither selector is present.
  - path: tests/test_provider_workload_policy.py
    what: >
      Provider-free regression and adversarial coverage of purpose filtering,
      host-floor monotonicity, malformed policy, hot reload and closed receipts.
  - path: .github/ci/legacy-jobs.yml
    what: >
      Add the new tests to the existing LLM provider job and explicitly widen the
      five contract-delta-identified transitive consumer scopes; no new workflow.
  - path: docs/superpowers/specs/2026-09-15-vps-site-fabric-integration.md
    what: >
      Owning architecture, credential/runtime separation, synchronization contract,
      staged rollout, consumer coverage gaps and production acceptance matrix.
  - path: docs/superpowers/plans/2026-09-15-provider-workload-guard.md
    what: Executable bounded source plan and required independent-review hold.
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-15-VPS-SITE-INTEGRATION.md
    what: This source-only continuation; no workstream liveness or gate state altered.
verified:
  - claim: Existing gateway baseline is green before the change.
    command: MM_DATA_GUARD=1 python3 -m pytest tests/test_llm_auth.py -q
    result: 80 passed; inherited shared pytest cleanup permission warnings were not repaired.
  - claim: New integration tests reproduce the missing boundary before implementation.
    command: MM_DATA_GUARD=1 python3 -m pytest tests/test_provider_workload_policy.py -q --tb=short
    result: >
      11 failed and one legacy control passed. Failures showed forbidden OAuth/Codex
      rungs, automatic fallback insertion and invalid profiles being ignored.
  - claim: The complete existing LLM provider test group passes with the new guard.
    command: >
      MM_DATA_GUARD=1 python3 -m pytest tests/test_codex_provider.py
      tests/test_llm_auth.py tests/test_provider_workload_policy.py tests/test_key_pool.py
      tests/test_ollama_provider.py tests/test_ai_costs.py tests/test_provider_health.py
      tests/test_provider_capacity.py -q --tb=short
    result: >
      280 passed in 6.32 seconds. An operation-local temporary root was used;
      provider, native-account and telemetry boundaries in the new tests were inert.
  - claim: The source worktree begins at fresh Macro main and does not replace an active writer.
    command: git rev-parse HEAD; git status --short
    result: >
      Initial clean base e9d469383c68aec55cf4c2723112fdf204f667cf, created by the
      reviewed native sparse helper. Feature branch is claude/vps-site-fabric-20260915-sol.
  - claim: Hosted CI closure misses were reproduced and repaired without weakening gates.
    command: >
      MM_DATA_GUARD=1 python3 -m pytest tests/test_provider_workload_policy.py
      -q --tb=short -k existing_curated; then the complete provider group above.
    result: >
      Five failed before the manifest repair. After adding the shared module to
      five existing exclusive job scopes, the complete provider group passed
      285 tests in 12.12 seconds. No provider/runtime implementation changed.
  - claim: Full repository differential contract-delta passes after the scope repair.
    command: >
      CONTRACT_DELTA_TMP_ROOT=<operation-local-temp-root> MM_DATA_GUARD=1
      python3 scripts/check_contract_delta.py
      --base 52bd0cde0669cd8ea396dfbe692399261dd5cfe5
    result: >
      Exit 0; 0 introduced, 0 inherited. This is local full contract-delta proof,
      not a claim that the new hosted PR checks have completed.
  - claim: Independent review's missing PR-execution gate is reproduced and repaired.
    command: >
      tests/test_provider_workload_policy.py::test_workload_guard_executes_in_the_real_pull_request_code_packs;
      complete provider-group command above with an outside-repository operation temp root.
    result: >
      Regression RED: 1 failed, 52 deselected (zero code-pack executions). After the
      existing ruling-graph code-job step was added: 53 dedicated tests passed;
      286 total provider tests passed in 7.60 seconds. Real loader/partitioner
      selects the executable suite in a code pack; capability-broker stays data-gated.
      Initial in-repository temp-root run hit two existing ledger location guards;
      test isolation was corrected, never the product guard.
unverified:
  - claim: The guard is merged, installed or enabled on the VPS.
    what_would_verify: >
      Exact-head independent approval, concluded CI, explicit Sol release and
      approved deployment/canary receipt. This slice changes no production config.
  - claim: Provider account inventory matches the Chairman's four Claude plus five Codex accounts.
    what_would_verify: >
      Native Provider Control enrollment and quota-domain evidence for exact active
      and retired identities; presence or subscription totals are insufficient.
  - claim: Global claims and real service-principal Executive admission are ready.
    what_would_verify: >
      Incumbent H0/P0 acceptance, CF2-I atomic reservation and a real authenticated
      service job with normalized result consumed by its parent. This connector
      reported fixture mode, so no live admission was attempted through it.
  - claim: Mastermind's paper-portfolio native waterfall is covered by this guard.
    what_would_verify: >
      Separate consumer adaptation and end-to-end tests: brain/provider_waterfall.py
      directly calls _oauth_pool_candidates, bypassing Macro build_providers.
unresolved:
  - Source transport eligibility does not prove API entitlement, spending approval or quality.
  - Policy hot reload/content hashes do not implement authenticated fleet propagation or quota claims.
  - The live safe health read reported Codex unavailable while the legacy waterfall policy remained green.
  - Independent review and current runtime owner gates remain mandatory before rollout.
next_actions:
  - >
    Recover this exact source PR with gh pr list -R mastermindx-market-intelligence/macro
    --state all --head claude/vps-site-fabric-20260915-sol. Review its current exact head,
    test results and Draft/HOLD-FOR-SOL status; do not arm or merge on an assumed green.
  - >
    Incumbent Fable principal coordinates independent source review on parent operation
    agent-fabric-end-to-end-fable-integration-20260913-sol-001. This slice does not
    grant write custody on any other active branch or replace the existing principal.
  - >
    Resolve existing H0/P0/CF2-I and service admission proofs. Reconcile actual account
    identities and approved production providers/budgets through incumbent owners.
  - >
    Sol owns the consumer rollout: first a read-only AI Brief shadow and one bounded
    native lobe job, then chat and paper-portfolio analysis after quality and rollback
    evidence. Adapt the direct Mastermind waterfall before claiming fleet coverage.
do_not_redo:
  - Do not create a second router, lifecycle, account/quota store, scheduler or refresh daemon.
  - Do not copy OAuth caches or quota ledgers bidirectionally as ongoing fleet synchronization.
  - Do not infer native quota domains or retire numbered accounts from the reported totals.
  - Do not use Chairman credentials as a shortcut for production service admission.
  - Do not rewrite active Fable, provider-economics, OpenCode or native-realm carriers.
  - Do not replace explicit denied/empty profiled routes with legacy Claude/Codex fallback.
danger_areas:
  - Legacy callers remain unchanged until deliberate adoption; this is not a live reserve guarantee.
  - Internal provider descriptors contain credentials; only workload_policy is a safe projection.
  - Host/caller profile selectors are trusted server configuration, never browser request parameters.
  - Site use does not authorize production OAuth relaying or unbounded API spending.
  - No autonomous deployment, real-money execution, self-granted permissions or governor edits.
decisions:
  - DEC:EXECUTIVE-CAPACITY-FABRIC-OWNERSHIP-AND-CONTRACT
---

## Capability delta and release hold

Before: the generic builder did not distinguish product inference from developer
subscription use. After, in this source candidate: an explicitly profiled caller
or server can filter forbidden transports before credentials or native accounts
are accessed, with a reproducible policy identity. Unprofiled legacy behavior is
intentionally preserved for staged migration.

**BUILT_NOT_PROVEN.** Local source tests are green; no merge, production install,
account enrollment, API call, live Executive Job or global capacity claim is implied.

HOLD-FOR-SOL: keep the implementation PR Draft, with no merge-on-green label and
no native auto-merge. Sol release requires independent exact-head review, concluded
binding checks, and composition with the incumbent fabric owners. Source release
alone does not authorize production activation. Fable's existing core-runtime
program continues; this handoff does not STOP it or seize an active writer.

The architecture and rollout details are in the committed spec and plan named in
changed[]. The canonical source PR is unambiguously recoverable from the exact
feature branch command in next_actions; its GitHub head/CI is the live evidence.


## R7179-R1 continuation — same writer, source-only repair

Recovered compatible Skillpack 1.0.1 from protected Mastermind
7642aea155d2817219135b24246b55c1d7611c66. Current GitHub review is comment
5690266059: REQUEST_CHANGES, B1 only. The previous 85a9d127 source checks did
NOT execute this suite in the PR code gate. A gate-free inventory was insufficient.

Repair adds an executable provider-free step to existing ruling-graph, after
minimal deps; the adjacent final agent-routing step owned by #7114 is untouched.
A real-loader/code-partitioner regression distinguishes this from nightly-only
coverage. The existing capability-broker data job is not moved. Empty host-profile
rollback semantics are explicit in the spec; no empty-to-legacy bypass was added.

The original parent/carrier, consumer coordination and source writer are retained.
No new principal, provider worker, credential ceremony or runtime effect is claimed.
Fresh independent exact-head review and concluded hosted checks remain owed after
publication of this repair. Runtime integration still depends on the incumbent
Family-B/H0/P0/atomic-claim owners and explicitly qualified service admission.


R2 integration evidence: full differential contract-delta against observed main
7c3b2e19c0bffe8aca9a7bfa91e610c1ca3b7149 exited 0 with zero introduced and zero
inherited findings. Actual scope inference selects the code job for changes to
the policy module, llm_auth, manifest, or own test. Isolated data-gate / removed-step /
commented-command mutants all remove code execution. No active manifest mutation
was retained. Compile and diff checks passed; Agent OS validation: 0 errors,
97 warnings. Native source/check publication and external review remain separate.

Consumer coverage findings for the NEXT bounded adoption wave (not fixed here):
- engine/master_brain.py:1698-1727 uses the shared builder for the DeepSeek lane,
  but its pinned-custom-endpoint branch calls _client and constructs a descriptor
  directly. This must not be advertised as covered by a builder-only floor.
- engine/marketing/copy_auditor.py:142-174 and copy_critic.py:339-382 return cached
  provider descriptors before calling the builder. Their cache identity does not
  include the new workload policy. Policy-file reload at build time is therefore
  NOT proof of immediate policy adoption by already-built long-lived consumers.
- Mastermind brain/provider_waterfall.py still directly enumerates OAuth/native
  candidates; the prior do-not-redo entry remains. Consumer rollout must prove
  typed refusal, custom-path eligibility and cache retirement/adoption at the
  real execution boundary, with no fallback to an unprofiled native path.
- Active AI Brief scheduling repair Macro #7178 and Portfolio V3 Mastermind #673
  retain their existing owners. Do not duplicate those producers or widen their
  branches. Shared policy adoption must be a separately bounded coordinated wave.
