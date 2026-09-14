---
workstream: WS:CHAIRMAN-CONTROL-ROOM
session: sol/plugin-integration-handoffs-20260907
model: sol
ended_because: ci_handoff
prs: [6977]
operation_key: agentos-plugin-integration-handoffs-reconcile-20260907-sol-001
mission: >
  Make the plugin-integration continuation index a parseable, correction-safe Agent OS handoff
  that routes future sessions without granting external connectors canonical authority.
state_before: >
  Five useful records existed on Macro PR 6977, but every file lacked Agent OS YAML frontmatter
  and was therefore invisible to the canonical validator; volatile connector states were also
  written as current prose and two had already drifted.
changed:
  - path: agentos/handoffs/CHAIRMAN-CONTROL-ROOM-PLUGIN-INTEGRATION-INDEX-2026-09-07.md
    what: >
      Adds canonical handoff metadata, dated-observation semantics, and the current Remote
      Desktop Commander, Notion, and Mastermind Executive availability reconciliation.
verified:
  - claim: >
      The original five PR 6977 records were not valid Agent OS handoffs.
    command: >
      python3 scripts/agentos.py validate at PR head e9a4535f14275896222e7c6a3cc39484852395e5
    result: >
      The validator reported exactly five hard unparseable errors, one for each new handoff,
      because no YAML frontmatter existed.
  - claim: >
      Current host and Notion observations differ from the original assessment.
    command: >
      Remote Desktop Commander list_devices plus ping on cfd09f03-2e6e-4a24-843c-8401d4a7169d;
      Notion notion-get-users with user_id=self
    result: >
      The authorized Mac was online and pinged at 2026-09-07T16:00:38.051Z; Notion returned the
      current user Chris. No host or Notion write occurred.
  - claim: >
      Current protected Mastermind procedure was loaded atomically for this repair.
    command: >
      GitHub read protected Mastermind master and docs/sol_skills/INDEX.md, COLD_START.md,
      RECONCILE_STATE.md, REVIEW_RETURN.md at b30422efde0308beb7fa069ddefd0987ac0bf4f3
    result: >
      Skillpack mastermind.sol_skillpack.v1 version 1.0.1 is compatible with bootstrap major 1.
  - claim: >
      The repaired five-file packet is visible to canonical Agent OS validation and context
      compilation.
    command: >
      python3 scripts/agentos.py validate; python3 scripts/agentos.py compile-context
      --workstream CHAIRMAN-CONTROL-ROOM --budget 16000 --json
      --now 2026-09-07T16:07:21Z
    result: >
      Validation returned 1073 records, including 446 handoffs, with zero errors and 93 existing
      warnings. The context_bundle.v1 output contained all five exact handoff filenames.
  - claim: >
      The only focused Agent OS test failure is pre-existing baseline debt, not a handoff repair
      regression.
    command: >
      python3 -m pytest tests/test_agentos_schema.py tests/test_agentos_status.py
      tests/test_agentos_compile.py -q; repeat the failing test on detached exact PR base
      b5d23913256f9d070ac6f576c370c16bda0f10de
    result: >
      Repaired candidate: 185 passed, one failed in
      test_cross_repo_path_is_unchecked_when_that_checkout_is_absent because it rejects any
      unrelated repository phantom-artifact warning. The exact PR base fails the same assertion;
      the disposable base worktree was removed.
unverified:
  - claim: >
      All connector states not explicitly re-smoked in the current reconciliation remain callable
      now.
    what_would_verify: >
      Run the harmless read-only smoke test named by the connector-family handoff in the exact
      future session and record observed_at plus result.
unresolved:
  - >
    Mastermind Executive is installed and enabled, but its invokable namespace is absent from
    this session; current callability is not established.
  - >
    Independent review and terminal repository CI for PR 6977 remain outstanding.
next_actions:
  - >
    Run Agent OS validation and repository fences on the repaired exact head.
  - >
    Obtain independent review of the five-record packet.
  - >
    Future integration sessions re-smoke only their assigned connector lane and then implement
    one useful vertical slice.
do_not_redo:
  - >
    Do not recreate a plugin registry, lifecycle, queue, auth, identity, transcript, retry, or
    state plane.
  - >
    Do not treat a dated successful connector read as permanent current availability.
danger_areas:
  - >
    Connector installation, account connection, tool invocation, end-to-end integration, and
    production acceptance are separate states.
  - >
    A stale handoff can route work incorrectly even when its source PR is green.
---
# Chairman Control Room — Plugin Integration Index

Date: 2026-09-07
Owner: Sol (CEO)
Workstream: `WS:CHAIRMAN-CONTROL-ROOM`
Chairman: Chris
Status: integration readiness ruling + continuation index

## Canonical procedure pin for this assessment

This assessment loaded the protected Mastermind Sol skillpack from:

- repository: `mastermindx-market-intelligence/Mastermind`
- protected master commit: `aefafc6dd12bebc0d8849f05e29d2dc11eced011`
- skillpack version: `1.0.1`
- bootstrap major: `1`
- required reads used from the same commit: `docs/sol_skills/INDEX.md`, `docs/sol_skills/COLD_START.md`, `docs/sol_skills/CLOSEOUT.md`

A future session MUST recover protected master again and load the then-current compatible skillpack. This SHA is evidence of the procedure used for this assessment, not permission to treat it as permanently current law.

## Executive ruling

Do **not** create a second plugin registry, startup plane, queue, lifecycle system, identity system, auth system, state store, transcript system, memory system, or orchestration control plane.

The existing Mastermind direction is a thin **skill -> installed-plugin bridge**. Extend that architecture. Each connector gets a bounded role, explicit authority boundary, read-only smoke test, one useful producer/consumer path, and real production proof before it is called integrated.

Authority remains:

- Executive OS: Job / Attempt / Worker / Event lifecycle and CEO admission.
- Agent OS (`macro/agentos/`): durable organizational continuity, decisions, discoveries, and handoffs.
- GitHub: canonical implementation and evidence for the current Mastermind estate.
- Linear: projection.
- Slack: transport / hot state.

External plugins are capabilities at the edge. Installation or authentication does not grant them organizational authority.

## Dated connector smoke-test estate

The table is a dated assessment snapshot, not a permanent connection guarantee. `PROVEN_LIVE` means a connector completed a real bounded read at its recorded observation; it does **not** mean every session can invoke it or that an end-to-end product workflow is integrated. Every future session must re-smoke its assigned connector and record `observed_at`, account/workspace/device scope, and the exact harmless read before relying on current availability.

### Current reconciliation overlay — 2026-09-07T16:07:21Z

- **Remote Desktop Commander:** current session `PROVEN_LIVE` for the authorized device `Mac-Studio.ts.net lan` (`cfd09f03-2e6e-4a24-843c-8401d4a7169d`); `list_devices` returned online/valid auth and exact-device `ping` returned pong at `2026-09-07T16:00:38.051Z`. Host capability does not expand organizational permission.
- **Notion:** current session `PROVEN_LIVE`; `notion-get-users(user_id=self)` returned the current user Chris. This proves account-scoped read access only, not a canonical organizational store or completed workflow.
- **Mastermind Executive:** Plugin Management reports the app installed and enabled, but its invokable namespace is absent from this session. Preserve the prior successful read as last-proven evidence; current-session callability is `UNVERIFIED`, not silently live or broken.

### Canonical Agent OS repair proof

The original PR head carried five Markdown files under `agentos/handoffs/` with no YAML frontmatter. The canonical validator therefore reported five hard `agentos-unparseable` errors and did not admit them as durable handoffs. This repair adds the required handoff contract to those same five paths.

At the repaired working tree:

- `python3 scripts/agentos.py validate` returned **1073 records / 446 handoffs / 0 errors / 93 pre-existing warnings**;
- the bounded `compile-context` read for `WS:CHAIRMAN-CONTROL-ROOM` returned `context_bundle.v1` and included all five exact records;
- the three focused Agent OS test modules returned **185 passed / 1 failed**; the sole failing test also fails on detached exact PR base `b5d23913256f9d070ac6f576c370c16bda0f10de` because it searches the whole repository warning stream for any `phantom-artifact`, rather than isolating the injected cross-repository artifact;
- no connector, account, service, runtime, provider, Agent OS code, test code, or external system was modified.

This is repository evidence for a records repair, not protection, installation, end-to-end plugin integration, or production acceptance.

| Connector | Verified connector state | Intended Mastermind role | Readiness / ruling |
|---|---|---|---|
| Mastermind Executive | PROVEN_LIVE (last-proven); current session UNVERIFIED | canonical CEO runtime / lifecycle authority | Installed/enabled, but current tool namespace is absent. Re-smoke before use; never wrap with a competing lifecycle plane. |
| GitHub | PROVEN_LIVE | canonical implementation + evidence | Primary source-control integration. |
| Linear | PROVEN_LIVE | work projection | Projection only; do not make it lifecycle authority. |
| Slack | PROVEN_LIVE | transport / hot state | Transport only; durable truth stays with owning system. |
| Gmail | PROVEN_LIVE | Chairman / company mail edge | Ready for bounded read/write workflows. Do not use as durable task state. |
| Google Calendar | PROVEN_LIVE | scheduling / availability | Ready for bounded scheduling workflows. |
| Google Contacts | PROVEN_LIVE | people / recipient resolution | Ready; use to resolve contacts before Gmail/Calendar writes. |
| Google Drive | PROVEN_LIVE | collaborative file/doc edge | Ready; repository/Agent OS remain canonical for engineering/org truth. |
| Trello | PROVEN_LIVE | optional capture / human task projection | One workspace is reachable. Trello is **not** a replacement for Executive OS or Linear. |
| AgentMail | PARTIAL | dedicated agent mailbox edge | API works but zero inboxes exist. Create inboxes only for a named agent-mail use case. |
| Airbyte Agent Engine | PARTIAL | data-source bridge for apps without a better direct connector | Enrollment completed during assessment; default workspace has zero connectors; payment setup still required. |
| Make | PROVEN_LIVE | bounded external automation edge | Authenticated. Must not become Mastermind's queue/orchestration/lifecycle plane. |
| PostHog | PROVEN_LIVE | product analytics, experiments, feature flags, error/log telemetry | `MastermindX` org is reachable. Analytics authority only; not market/business truth. |
| Firecrawl | PROVEN_LIVE | deep web retrieval/crawl/map/monitor for research | Connector works; no monitors configured. Rights/provenance rules still apply. |
| Context7 | PROVEN_LIVE | current software/library documentation | Ready; use for API/docs freshness, never as repository-state authority. |
| Canva | PARTIAL | brand/design production and review | Connected; `Mastermind-X` folder exists; no Brand Kit is exposed. |
| Figma | PARTIAL | product/UI design and code-to-design workflow | Authenticated but current seat is **View** on Starter. Reads may work; writes must not be assumed. |
| Opera Browser Connector | DARK_OR_DISCONNECTED | logged-in browser inspection/navigation | Plugin is present but browser reports not connected; enable browser-side AI connection and sign in. |
| Remote Desktop Commander | PROVEN_LIVE (reverified) | authorized Mac filesystem/terminal bridge | Current exact-device list/ping succeeded; repeat schema/device/ping startup fence in every session. |
| Vercel | PROVEN_LIVE | web/frontend deployment lane where existing estate uses Vercel | Workspace/team read succeeded. Do estate archaeology before writes; never dual-own the same service with Render/BasicDeploy. |
| Render | PROVEN_LIVE | service/data deployment lane where existing estate uses Render | Workspace read succeeded. Treat per-service ownership as explicit. |
| BasicDeploy | PROVEN_LIVE | disposable sandbox/prototype deployment lane | Container listing succeeded. Default role is sandbox, not production authority. |
| GitLab | PROVEN_LIVE | optional external SCM/interoperability edge | Two newly created private projects with the same name were found. **Rejected by design as canonical Mastermind SCM** unless Chairman explicitly changes source-control authority. |
| Notion | PROVEN_LIVE (reverified) | optional collaborative knowledge/document edge | Current self-user read succeeded. Use only for a named workflow; Agent OS/repository truth remain canonical. |

## Priority setup queue

### P0 — unblock connectors whose installation is not enough

1. Opera Browser Connector — enable **Allow AI connection** in Opera Browser Connector and sign into Opera; prove with `list-tabs`.
2. Airbyte — complete payment setup only if a named Airbyte use case is accepted; list workspaces/connectors before adding anything.
3. Figma — upgrade the current seat or grant edit rights for the intended Mastermind file/team before any write workflow is accepted.
4. Canva — decide whether Mastermind needs a formal Brand Kit. Current account exposes a `Mastermind-X` folder but no Brand Kit.
5. Mastermind Executive — re-smoke current-session tool availability before any runtime read or CEO admission; installed/enabled status alone is not invocation proof.
6. Remote Desktop Commander and Notion no longer have setup blockers in this session. Preserve their startup smoke tests and move them to P1 only when a named workflow exists.

### P1 — convert connected surfaces into one useful vertical slice each

- Google Workspace: one real Chairman workflow using Contacts -> Gmail/Calendar/Drive as appropriate.
- PostHog: one real production event / insight path tied to a product question.
- Firecrawl + Context7: one research/developer workflow with provenance and a consumer.
- Canva/Figma: one real design handoff tied to a product/brand output, after write permissions are settled.
- Vercel/Render: map actual service ownership, then prove a real deployment read/diagnostic path without changing ownership.

### P2 — optional edges only after a named need exists

- AgentMail, Make, Trello, Airbyte, GitLab, BasicDeploy.

These tools are useful but particularly prone to creating duplicate task, automation, integration, repository, or deployment planes. Integrate only against a named user/machine job.

## Future-session startup contract

Every plugin-integration session must:

1. Recover current protected Mastermind skillpack from protected master; record its exact commit SHA and use one commit for all required reads.
2. Read this index and the connector-family handoff for its assigned scope.
3. Verify the connector is actually present in the current tool surface. If missing, use Plugin Management rather than assuming it still exists.
4. Perform a harmless read-only smoke test before any modifying operation.
5. Reconcile authority: identify what system owns truth and what the connector is only transporting/projecting/observing.
6. Search existing repository/Agent OS implementation before adding a bridge. Extend the existing skill-to-plugin pattern rather than introducing a registry/control plane.
7. For writes, preserve explicit Chairman intent, platform permission gates, same-carrier effect reconciliation, and no blind retry after unknown effects.
8. Implement one independently useful vertical slice: real producer -> connector -> real consumer / UI or machine projection -> tests / validation.
9. Require production proof. Authentication, schema creation, CI green, merge, deploy, ACK, START, QUEUED, and execution are not equivalent to acceptance.
10. Update Agent OS with verified state, proof, failure semantics, and exact next action.

## Continuation handoffs

- `agentos/handoffs/PLUGIN-HANDOFF-COLLAB-COMMS-2026-09-07.md`
- `agentos/handoffs/PLUGIN-HANDOFF-RESEARCH-DESIGN-HOST-2026-09-07.md`
- `agentos/handoffs/PLUGIN-HANDOFF-DATA-AUTOMATION-OBSERVABILITY-2026-09-07.md`
- `agentos/handoffs/PLUGIN-HANDOFF-CODE-DELIVERY-2026-09-07.md`

## Stop condition

Stop and escalate rather than improvising when a proposed integration would:

- replace Executive OS lifecycle authority,
- make Slack/Trello/Make/Linear a new canonical queue or task system,
- create a second identity/auth/state/transcript/memory plane,
- duplicate a production deployment owner for the same service,
- migrate GitHub authority to GitLab without explicit Chairman direction,
- grant model-generated summaries/sentiment decision authority,
- or require credentials to be pasted into chat.
