---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/quota-economics-20260913
model: sol
ended_because: blocked
mission: >
  Implement subscription-aware useful-work allocation so the Chairman no longer manually
  instructs orchestrators which prepaid provider/model allowance to consume before reset.
state_before: >
  Macro PR 7103 supplied plan metadata and usage parsers at
  2d3538a3d115adeee281dc961007d65f892cc17c, but no complete quota-economics allocator.
  The recovered capacity workstream still held CF2-I behind installed CF2-H0/P0 proof.
  Executive state read failed with a 404 transport response; live quota/account bindings
  and multi-account claim readiness were not established in this session.
changed:
  - path: engine/provider_quota_economics.py
    what: >
      Added a read-only deterministic preview over native resource intersections, model
      reserves, freshness, suitability tiers, independent review, provider preference,
      bounded short-window forecasts and an existing usage-parser row bridge.
  - path: scripts/preview_provider_quota_economics.py
    what: Added a bounded offline JSON CLI consumer; no credentials, network or dispatch.
  - path: tests/test_provider_quota_economics.py
    what: Added 28 executable intent cases, including CLI and parser integration.
  - path: tests/fixtures/provider_quota_economics/grok_cursor_synthetic.json
    what: Added an explicitly synthetic runnable Grok-first/Cursor-fallback scenario.
  - path: research/SUBSCRIPTION_QUOTA_ECONOMICS_ROUTING_2026-09-13.md
    what: >
      Recorded outcome, current source scope, architecture/no-rebuild boundary,
      current official plan corrections, integration sequence, acceptance and stop condition.
verified:
  - claim: The 28 quota-economics intent cases pass under native Python 3.9.6.
    command: /usr/bin/python3 -m unittest discover -s tests -p test_provider_quota_economics.py -v
    result: PASS; 28 tests, including the actual local CLI subprocess.
  - claim: The same 28 cases pass under native Python 3.14.7.
    command: /opt/homebrew/bin/python3 -m unittest discover -s tests -p test_provider_quota_economics.py -q
    result: PASS; 28 tests. Neither run consumed a provider subscription.
  - claim: All 41 targeted new and dependency tests pass together.
    command: .venv-quota/bin/python -m pytest --noconftest -q tests/test_provider_quota_economics.py tests/test_provider_subscription_plans.py tests/test_provider_subscription_usage.py
    result: PASS; 41 tests in 0.13 seconds. This is not full repository CI.
  - claim: The new handoff passes the canonical record-local schema validator.
    command: scripts.agentos.check_handoff(parsed_frontmatter_with_body, handoff_path)
    result: PASS; zero record-local problems. Full-store validation was not run in the sparse source tree.
  - claim: This carrier builds on the existing provider plan/usage implementation.
    command: git rev-parse HEAD before the first source commit
    result: 2d3538a3d115adeee281dc961007d65f892cc17c; Macro PR 7103 base carrier.
  - claim: Current plan semantics must not all be flattened into fixed token limits.
    command: >
      Read official Anthropic Fable plan, xAI usage FAQ, Cursor usage limits,
      Alibaba Personal Token Plan, Z.AI Coding Plan and OpenAI Work/Codex limits
      on 2026-09-13; exact source URLs and implications are in the research artifact section 5.
    result: >
      Shared/subset pools, distinct Cursor monthly pools, native credits, different
      reset anchors and provider-permitted harness modes require versioned bindings.
unverified:
  - claim: Economics-based routing is live in Executive OS or any provider harness.
    what_would_verify: >
      Current installed CF2-P0 acceptance, reviewed shared-resource capacity contract,
      existing atomic claim integration, actual authorized provider worker result,
      quota reconciliation and visible machine/Control Room proof.
  - claim: The source candidate passed independent review or the full repository CI.
    what_would_verify: Exact-head independent review and concluded required checks on its PR.
  - claim: The screenshot represents fresh usable quota for an enrolled provider account.
    what_would_verify: Supported authorized source observation with reviewed account/generation binding.
unresolved:
  - CF2-H0/P0 installed acquisition evidence and its current release state must be recovered.
  - The Executive plugin read returned 404; no modifying Executive command was submitted.
  - Macro 7103 needs source-owner reconciliation of current Alibaba Personal and GLM credit-generation semantics.
  - Actual account products, shared pool identities and cost calibration are not established by the preview.
  - Automatic reserve release, closed-loop learning, live telemetry polling and runtime claim integration are not built here.
next_actions:
  - >
    Resume this exact branch/source carrier for independent review and repairs. Compare against
    Macro 7103 parent 2d3538a3d115adeee281dc961007d65f892cc17c; retain all unrelated owner files.
  - >
    In the existing 7103 source-owner lane, reconcile current official Alibaba Personal
    seven-day Credits and GLM five-hour/weekly Credits generations. Preserve historical
    plans and provider terms; do not silently amend existing enrolled accounts.
  - >
    Recover current canonical control-host CF2-H0/P0 receipts through the existing
    capacity carrier. Obtain the actual missing authorization/transport/installed proof;
    do not route around it using a different Mac or shared provider-home credentials.
  - >
    After the gates release, implement reviewed native resource bindings and economics
    in existing Capacity Fabric claim composition, then shadow and prove one real accepted
    worker result with atomic quota evidence and the existing visible projection.
do_not_redo:
  - Do not build a second provider scheduler, queue, quota ledger, account registry or polling service.
  - Do not modify provider_capacity.v1 or placement_snapshot_json for this source preview.
  - Do not count Fable's subset allowance as additive to the shared Claude parent.
  - Do not infer absolute tokens from a percentage or promise advertised agent concurrency as a hard entitlement.
  - Do not restart or migrate an already-started or EFFECT_UNKNOWN Attempt to consume another subscription.
  - Do not create busywork, repeat reviews or inflate context to hit a quota-consumption target.
danger_areas:
  - All preview flags and bindings are caller declarations; the result explicitly grants no admission authority.
  - Alternative option forecasts share resources and must not be summed.
  - Missing historical rolling releases produce conservative scenario estimates, not proven unavoidable waste.
  - Provider personal-plan interactive permissions are not automatic permission for a background executor.
  - Shared quota state is not safely keyed by a session, host, ordinal home or displayed account label.
  - Parent provider metadata is a moving source dependency; a draft PR is not deployed account truth.
prs: [7103]
---

# Quota economics source checkpoint

The strategic outcome remains uncompleted. This is a useful executable source slice,
not a live intelligent router, and the parent workstream must remain active.

Source workspace on the authorized MacBook:
`/Users/chriswong/sol-worktrees/quota-economics-20260913-sol-001`.
Branch: `sol/quota-economics-20260913`. Protected Skillpack basis:
`9ed16bf0fcc5b47e870350ff2413ff5c8c73b447` (version 1.0.1, bootstrap 1).
GitHub is the implementation/evidence carrier; this workspace is not a runtime host.

Read `research/SUBSCRIPTION_QUOTA_ECONOMICS_ROUTING_2026-09-13.md` for the complete
operator handoff: mission, why, authority, verified state, scope/non-goals, user journey,
time/null/correction behavior, deterministic versus learned method, failure modes,
ordered integration waves, production acceptance and stop conditions.

Hold authority is Sol. Release this source candidate only after independent review,
parent reconciliation and concluded binding checks. Runtime release additionally needs
the existing installed-host gates and accepted shared-pool/claim contract. No auto-merge,
merge-on-green or unattended watcher is authorized or claimed by this handoff.
