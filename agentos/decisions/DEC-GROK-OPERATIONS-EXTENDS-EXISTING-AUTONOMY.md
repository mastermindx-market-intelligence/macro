---
key: GROK-OPERATIONS-EXTENDS-EXISTING-AUTONOMY
question: >
  How should the ready Grok Bot product be integrated with Mastermind autonomy,
  Workspace Agents and economical helpers without duplicating company control planes?
answer: >
  Build one Grok Operations Bot as an optional operational foreman/sentinel. Inbound
  obligations use the existing Executive Wake and exact RuntimeBinding owners; outbound
  answers and helper requests use the existing four-tool Company Consultation fabric.
  Start production-inert, qualify one exact return journey, then add one economical peer,
  one event-driven responsibility and only explicitly delegated operational decision
  classes. Never make Grok another CEO, queue, router, memory store or acceptance owner.
rationale: >
  Chris approved the Grok operations direction and requested the complete infrastructure,
  integration model and implementation plan. Protected source now includes W6-C1's
  versioned consultation contract and Company MCP facet, so a new Grok callback/result
  system would be both unnecessary and architecturally wrong. The highest-value use is
  reducing manual continuation and evidence reconstruction while deterministic services
  retain liveness, deduplication, effects and recovery. Current protected source also
  confirms Grok Secretary is an approved team principal and that read-only security must
  be proportional rather than blocked by exact roster ceremony.
alternatives:
  - option: Make Grok a second Meta-CEO or mandatory supervisor over every worker.
    why_not: >
      Duplicates Sol and Executive owners, adds premium reasoning hops, creates competing
      decisions and makes provider availability an organizational dependency.
  - option: Give Grok direct credentials to GLM, MiniMax, Codex, Studio and other helpers.
    why_not: >
      Bypasses current Router/Capacity/provider eligibility, exposes credentials on a
      shared cloud computer and makes prompt text an account/placement authority.
  - option: Use a Grok-specific callback database or widen the five-tool Executive app.
    why_not: >
      W6-C already owns consultation/result lineage. A callback database would duplicate
      result state, while a sixth Executive tool would collapse CEO intent and peer
      consultation into one unsafe surface.
  - option: Depend on Slack listeners, schedules or continuous model polling for liveness.
    why_not: >
      Burns scarce usage, can pause, confuses transport with lifecycle and recreates a
      scheduler. Deterministic Wake should activate Grok only for a material obligation.
  - option: Keep Grok read-only forever.
    why_not: >
      Leaves the key autonomy benefit unrealized. After identity/effect proof, #612 permits
      a qualified operational principal to own closed repair/continue/park decisions
      inside its current grant without a fresh Web Sol turn.
evidence:
  - "Chairman live Grok Bot conversation: approved the operations-foreman direction and then requested hardening, infrastructure/system integration and the full implementation plan; stated Grok Bot is ready for setup after research."
  - "Protected Mastermind d07689b7737f324c16b142d03bffc89cdcf7a27d; Sol Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap-major 1 loaded from that exact commit."
  - "Protected W6-C1 at parent f4730cc65436d86500ef827c24493f83a7e41def: versioned peer-consultation contract and distinct four-tool Company Consultation MCP facet."
  - "Protected PR #617 / merge d07689b7737f324c16b142d03bffc89cdcf7a27d: Grok Secretary is an approved team principal; exact roster count is not a read-only C1 blocker; hard stops remain concrete secret, identity, duplicate-publication, stale-truth, effect-unknown, second-plane and destructive-authority failures."
  - "Mastermind draft PR #624 at 34b2e25b946e9e7dade78fb7cead7a9f19ea2aca: five documentation paths including the controlling infrastructure amendment, full implementation plan, reconciled canary plan and owner setup runbook."
  - "Mastermind draft PR #615: W6-C2 runtime/receipt half remains unmerged/production-disarmed and is the first implementation dependency; downstream Grok code must bind to its protected interface, not draft symbols."
  - "Mastermind control_plane/wake_transport.py at f4730cc... names grok-computer with transport_implemented=false; control_plane/session_targets.py has no grok-bot reasoning surface; checked-in targets are disabled and production is false."
  - "Mastermind integrations/mastermind_company_mcp/consultation.py and server.py at f4730cc... expose exactly company.peers, company.consult, company.reply and company.consultation with one-answer/four-evidence/zero-forward-hop limits and no provider I/O."
  - "Mastermind integrations/executive_wake/codex_app_server.py at f4730cc... provides the existing one-call, typed acceptance/delivery and EFFECT_UNKNOWN adapter pattern the Grok transport must extend."
  - "Official contracts read 2026-09-14: https://cursor.com/help/grok-bot/plans ; https://cursor.com/help/grok-bot/routines ; https://docs.x.ai/grok-bot/overview ; https://docs.x.ai/grok-bot/bots ; https://docs.x.ai/grok-bot/security-faq ; https://docs.x.ai/grok/connectors/custom-mcp-tunneling ; https://docs.x.ai/grok/connectors ."
  - "Macro agentos/README.md read at e0e3fda2fa2a44d8d64c3f0a52b9d56c1de3653b; later main movement to 4b0d6a553b6a970688ccd2f7ac112bf30e56edf2 changes only data/research_vault/catalog.json and is path-disjoint."
affects:
  - "mastermind:docs/superpowers/specs/2026-09-14-grok-bot-autonomy-foreman-design.md"
  - "mastermind:docs/superpowers/specs/2026-09-14-grok-bot-autonomy-infrastructure-amendment.md"
  - "mastermind:docs/superpowers/plans/2026-09-14-grok-bot-autonomy-full-implementation.md"
  - "mastermind:docs/superpowers/plans/2026-09-14-grok-bot-first-supervised-return.md"
  - "mastermind:docs/runbooks/grok-bot-operations-setup.md"
  - "mastermind:common/agent_dialogue_consultation_contract.py"
  - "mastermind:control_plane/session_targets.py"
  - "mastermind:control_plane/wake_transport.py"
  - "mastermind:integrations/executive_wake/*"
  - "mastermind:integrations/mastermind_company_mcp/*"
  - "agentos/*"
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-14
review_by: 2026-09-21
---

## Architecture ruling

The final system has two independent seams:

```text
Executive Wake + exact RuntimeBinding
-> one Grok webhook-routine submission
-> Grok Operations
-> authenticated Company Consultation MCP
-> W6-C consultation/runtime carrier
-> current requester consumption and lawful next action
```

Inbound provider acceptance and outbound company evidence are separate. A webhook
HTTP 200 proves accepted/start only. It cannot prove recipient consumption, answer
availability, requester consumption, work acceptance or completion.

Use one Bot with SENTINEL and FOREMAN task modes. These are not separate identities.
A Bot's company identity is the admitted Worker/Attempt plus RuntimeBinding. A dedicated
Cursor user is required only when the connected credentials or data need isolation from
other Bots; it is not an exact-roster or read-only observability prerequisite. Multiple
Bots under one user still share the cloud computer/files/browser sessions/logins.

The Bot never receives provider/helper credentials. It asks `company.consult` for an
opaque peer; existing Resolver/Router/Capacity/provider owners determine a lawful route.
Independent effectful/source-modifying work remains an Executive child Job.

## Capability state

- W6-C1 peer contract/Company MCP: `BUILT_NOT_PROVEN / PRODUCTION_INERT` on protected source.
- W6-C2 consultation runtime: `BUILT_NOT_PROVEN / UNMERGED / PRODUCTION_DISARMED`.
- Grok `grok-bot` reasoning surface: `NOT_BUILT`.
- `grok-computer` Wake adapter: `NOT_BUILT`; descriptor false.
- authenticated remote Company Consultation app: `NOT_BUILT`.
- Grok product/account: Chairman reports ready, but Mastermind connection is
  `DARK_OR_DISCONNECTED` until exact account/profile/MCP/routine attestation and proof.
- overall Grok operations integration: `SPEC_ONLY`.

Mastermind PR #624 remains documentation-only. No runtime/config/service/account/credential/
Bot/routine/tunnel/provider/billing/production effect follows from this decision or PR.

## Proportional security and economics laws

Read-only observation should be protected by identity, least-privilege access, stale/unknown
honesty and no duplicate state—not blocked by exact team roster count or repeated ceremony.
Stronger gates begin when the lane adds secrets, provider submissions, result mutation,
source writes, production effects or delegated operational authority.

- Grok Secretary is an approved team principal; do not create a removal/predecessor gate.
- Cursor/SuperGrok grants do not stack; on-demand is a separate account-level path.
- A monthly on-demand limit is not a strict stop in the middle of a running turn.
- Do not enable/raise on-demand or purchased-credit overflow from this program without
  separate authority and an enforceable accounting boundary.
- Bot role prompts, account login and Auto Review do not grant organizational authority.
- Webhook URL/key and Company MCP OAuth material remain in existing secret custody and
  never enter RuntimeBinding, webhook JSON, GitHub, Slack, Agent OS, Bot memory or files.
- Company Consultation is a distinct authenticated four-tool app; the Executive five-tool
  app is not widened.
- Custom MCP public reachability/tunnel is transport only; OAuth and backend grants remain
  mandatory.
- Grok routines may pause and cannot own company liveness or the canonical event queue.
- #188/OpenClaw remains optional later local actuation and is not a cloud-loop dependency.

## What the finished experience looks like

Chris sees one Grok Operations responsibility in Control Room showing the current logical
target, sanitized binding generation, source/capability generation, Wake state, consultation
state, routine/budget state, exact blocker/owner and evidence links. It never exposes secrets,
raw prompts/answers or inferred liveness.

An admitted returned-work obligation wakes Grok once. Grok resolves the exact current
consultation and evidence, optionally consults one Router-selected peer, produces one answer,
and stops. W6-C records recipient and requester consumption. The current parent continues,
repairs, parks or escalates. Grok can disappear afterward without losing company state.

After the read/return and exact Wake journeys are production-proven, Grok may receive a
current delegation envelope for closed operational decision classes such as bounded repair,
continue-inside-frozen-plan or park-affected-dependency. Product thesis, architecture,
acceptance waiver, provider admission, major budget/release/live-capital and Chairman-reserved
decisions remain outside its authority.

## Exact implementation sequence

1. C0 — reconcile/review/protect W6-C2 and its exact receipt interfaces.
2. C1 — version Company Consultation for the honest `grok-bot` reasoning surface while
   preserving every v1 fingerprint/result.
3. G1 — build provider-free Grok Wake dispatcher and bounded webhook client; keep
   `transport_implemented=false` and target disabled.
4. G2 — build/install the authenticated four-tool Company Consultation HTTP app through
   existing OAuth/audit/service/tunnel owners.
5. G3 — add unarmed capability/profile, redacted Bot attestation, setup/rollback runbook
   and truthful Control Room projection.
6. G4 — configure one Bot and inactive routine; prove one manual read/return canary.
7. G5 — prove one finite webhook Wake/return journey and negative effect semantics while
   canonical transport is still false.
8. G6 — guarded promotion of one exact Grok target only.
9. G7 — prove one Router-selected economical helper and bounded correction.
10. G8 — enable one narrow event-driven responsibility and closed operational decisions.
11. G9 — evaluate ROI/security and accept, restrict or reject each route independently.

The implementation details, exact files/interfaces/tests/commands and stop conditions are
in Mastermind PR #624's full implementation plan.

## Exact next action

**Reconcile and protect W6-C2 / Mastermind PR #615.** This is the current critical-path
interface dependency. After it is accepted, create two path-bounded source waves:

- versioned `grok-bot` consultation identity;
- provider-free Grok Wake adapter/client with descriptor still false.

The remote Company Consultation app may be implemented in parallel only when its owner
binds to the protected W6-C runtime. Owner-side Grok account/Bot setup waits for the
reviewed installed service, capability profile and attestation source. Do not ask Chris
to select worker accounts or transfer routine messages manually.

## Revalidation / falsifier

Before each operational wave, re-read current protected source, W6-C2 state, provider
contracts, actual intended account configuration, usage/overflow, installed service,
RuntimeBinding and tool inventory. A newer protected return contract, supported exact
provider ACK, enforceable budget cap or accepted production proof supersedes only the
corresponding observation; it does not create broader authority.

No merge, provider launch, Bot setup, helper invocation, account/billing change, routine
activation, host install or production deployment is authorized by this decision record.
