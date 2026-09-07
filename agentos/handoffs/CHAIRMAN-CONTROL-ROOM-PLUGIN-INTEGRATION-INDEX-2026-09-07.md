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

## Verified connector estate

Capability states use the Mastermind vocabulary. `PROVEN_LIVE` below means the connector itself was proven callable with a real read; it does **not** mean an end-to-end product workflow is fully integrated.

| Connector | Verified connector state | Intended Mastermind role | Readiness / ruling |
|---|---|---|---|
| Mastermind Executive | PROVEN_LIVE | canonical CEO runtime / lifecycle authority | Preserve as authority; never wrap with a competing lifecycle plane. |
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
| Remote Desktop Commander | DARK_OR_DISCONNECTED | authorized Mac filesystem/terminal bridge | Connector returned HTTP 401 Authentication failed. Reconnect/authenticate before any host work. |
| Vercel | PROVEN_LIVE | web/frontend deployment lane where existing estate uses Vercel | Workspace/team read succeeded. Do estate archaeology before writes; never dual-own the same service with Render/BasicDeploy. |
| Render | PROVEN_LIVE | service/data deployment lane where existing estate uses Render | Workspace read succeeded. Treat per-service ownership as explicit. |
| BasicDeploy | PROVEN_LIVE | disposable sandbox/prototype deployment lane | Container listing succeeded. Default role is sandbox, not production authority. |
| GitLab | PROVEN_LIVE | optional external SCM/interoperability edge | Two newly created private projects with the same name were found. **Rejected by design as canonical Mastermind SCM** unless Chairman explicitly changes source-control authority. |
| Notion | NOT_BUILT | potential collaborative knowledge/document edge | Plugin directory currently reports Notion as **not installed** in this session. Do not claim it is connected until reinstalled/reverified. |

## Priority setup queue

### P0 — unblock connectors whose installation is not enough

1. Remote Desktop Commander — reconnect/authenticate, then `list_devices`, select intended authorized Mac, and `ping` it before any file/shell use.
2. Opera Browser Connector — enable **Allow AI connection** in Opera Browser Connector and sign into Opera; prove with `list-tabs`.
3. Airbyte — complete payment setup if Airbyte will be used; list workspaces/connectors before adding anything; default workspace currently has no created connectors.
4. Figma — upgrade the current seat or grant edit rights for the intended Mastermind file/team before any write workflow is accepted.
5. Canva — decide whether Mastermind needs a formal Brand Kit. Current account exposes a `Mastermind-X` folder but no Brand Kit.
6. Notion — reinstall/reconnect if Chairman still intends to use it, then smoke-test before assigning a role.

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
