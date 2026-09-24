---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/claude-fabric-auth-client-checkpoint-20260923
model: sol
ended_because: complete
mission: >
  Make Claude Code on the Mac Studio a fabric-first principal surface: default to Fable rather than
  Opus/Sonnet/Haiku, reserve native Opus children for bounded orchestration or read-only audit, route
  routine proof-bearing work into the existing Mastermind Executive/Subagent Fabric, and finish the
  first-class authenticated Claude-to-Executive carrier without creating another control plane.
state_before: >
  Claude Code was installed and authenticated, but global CLAUDE.md only carried SSD worktree law,
  settings did not pin the parent model, and no global hook enforced fabric-first child routing.
  Production Mastermind Executive MCP already existed, but Claude had no proven authenticated
  first-class carrier into that ingress; the legacy raw control socket was not a lawful substitute.
changed:
  - path: host:/Users/chriswong/.claude/settings.json
    what: "Pinned the global parent model to fable and registered fabric SessionStart plus Agent|Task PreToolUse hooks."
  - path: host:/Users/chriswong/.claude/CLAUDE.md
    what: "Added fabric-first law: Fable parent, canonical Executive child work for lifecycle-significant labor, no native Sonnet/Haiku defaults, no Fable child, Opus only for explicit orchestration/read-only audit."
  - path: host:/Users/chriswong/.claude/hooks/mastermind_fabric_routing_guard.py
    what: "Added fail-closed routing for inherited, Sonnet, Haiku, Fable-child and unqualified Opus Agent/Task calls."
  - path: host:/Users/chriswong/.claude/hooks/mastermind_fabric_context.py
    what: "Added startup owner/context guidance preserving Executive OS, Capacity/Model Router and Agent OS boundaries."
  - path: host:/Users/chriswong/.local/bin/mmx-executive-fabric
    what: "A temporary raw control.sock wrapper was prototyped, falsified against the installed runtime, and deleted; it is not accepted architecture."
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-23-CLAUDE-FABRIC-AUTH-CLIENT-CHECKPOINT.md
    what: "This cumulative continuation checkpoint."
verified:
  - claim: "Protected Mastermind Skillpack at checkpoint is a7d2b3049e5cdc523e91e61a6e9d70a1cb911157, schema mastermind.sol_skillpack.v1 v1.0.1 / bootstrap-major 1."
    command: "Read protected master branch identity and same-SHA docs/sol_skills/INDEX.md."
    result: "Protected master and same-SHA Skillpack pin verified."
  - claim: "Current Mac Studio Claude Code is installed and first-party claude.ai authenticated on Max."
    command: "claude --version; claude auth status"
    result: "Claude Code 2.1.275; loggedIn=true, authMethod=claude.ai, apiProvider=firstParty, subscriptionType=max."
  - claim: "Current global Claude configuration pins Fable and has both Mastermind fabric hooks installed."
    command: "Read ~/.claude/settings.json; validate JSON; inspect SessionStart and PreToolUse commands."
    result: "model=fable, fabric_context_hook=True, fabric_guard_hook=True; JSON and hook syntax validated."
  - claim: "Native-child guard enforces the intended exception boundary."
    command: "Feed representative Agent/Task hook payloads for inherited, sonnet, haiku, unsafe Opus audit, valid Opus read-only audit and valid Opus orchestration."
    result: "Inherited/Sonnet/Haiku/unsafe-Opus denied; valid Opus read-only audit and orchestration allowed."
  - claim: "A setup-time fresh Claude headless session actually selected Fable."
    command: "claude -p --output-format json --max-turns 1 'Return exactly the single word READY.'"
    result: "Under Claude Code 2.1.259 the run returned READY, modelUsage only claude-fable-5-1, subagent_stats.spawned=0."
  - claim: "Production Mastermind Executive MCP and dedicated CEO ingress are live on the Mac Studio."
    command: "Read installed executive-mcp.json, test /var/run/mastermind-executive/ceo-ingress.sock, inspect executive_mcp_entry.py process."
    result: "Installed release bf764f494b9cd0ecede6234bb472c3344c8e77cc; ceo-ingress.sock READY; production process running."
  - claim: "Legacy raw control.sock is not the accepted Claude carrier."
    command: "Invoke installed ceo_intent.py with Python 3.12 against /var/run/mastermind-executive/control.sock, then delete temporary wrapper."
    result: "Connection refused; wrapper removed; durable policy requires authenticated Executive ingress."
unverified:
  - claim: "A fresh Claude Code 2.1.275 headless run still resolves to claude-fable-5-1."
    what_would_verify: "One later allowed fresh claude -p JSON proof. The checkpoint-time attempt was blocked before dispatch and was not retried/rerouted."
  - claim: "Claude Code has a supported authenticated principal/client that can call production Mastermind Executive MCP directly."
    what_would_verify: "Use one supported Claude-facing authenticated client on the existing transport and read real Executive state with current resource/principal policy evidence and no copied secrets."
  - claim: "Protected Mastermind a7d2 already contains every source change needed for a Claude-facing carrier."
    what_would_verify: "Diff only Executive MCP/auth/Claude-client/admission seams from installed bf764 to current protected source before editing."
  - claim: "Claude can submit one real bounded fabric commission end to end."
    what_would_verify: "After authenticated read proof, use present Chairman authority for one harmless strict-v2 submit; require QUEUED, dispatched=false and same-carrier readback."
unresolved:
  - "Installed Executive release bf764f494b9cd0ecede6234bb472c3344c8e77cc lags protected Mastermind a7d2b3049e5cdc523e91e61a6e9d70a1cb911157; relevant source movement must be reconciled first."
  - "Production Executive transport/auth is real, but Claude-specific authenticated client enrollment is not proven."
  - "Direct Claude-to-fabric admission remains NOT_PROVEN even though local Claude routing is configured and ingress is live."
  - "Older scheduled-task SKILL.md files still contain legacy Opus/Sonnet/Haiku prose; do not bulk-rewrite blindly."
  - "No watcher, background executor or successor session was started by this handoff."
next_actions:
  - "Fresh successor re-pins current Mastermind Skillpack, reads WS:EXECUTIVE-CAPACITY-FABRIC and this handoff, then reconciles only Executive MCP/auth/Claude-client/admission deltas from installed bf764 to current protected source."
  - "Reuse the existing production Executive HTTP MCP / dedicated CeoIngress carrier. Determine the smallest supported Claude Code authentication/enrollment path; if source work is required, use one bounded carrier/PR."
  - "Prove read-only connectivity first from the actual Claude surface with exact principal/resource-policy evidence; fixture/local-error responses are not production proof."
  - "Only after read proof and current Chairman authority, submit one harmless strict-v2 intent on the same carrier; require QUEUED, dispatched=false and same-carrier status reconciliation."
  - "After carrier acceptance, expose it through supported Claude MCP/client configuration and prove one fabric-first commission with Fable parent and canonical Executive child work."
do_not_redo:
  - "Do not switch the Claude parent default back to Opus, Sonnet or Haiku absent a material invalidator."
  - "Do not remove the global fabric routing hooks merely to make a native child spawn succeed."
  - "Do not spawn native Fable children or use Sonnet/Haiku as automatic native worker lanes."
  - "Do not recreate the deleted raw control.sock wrapper or another authentication bypass."
  - "Do not create a second Executive app, queue, ingress, broker, lifecycle, auth store, credential, retry, capacity or scheduler plane."
  - "Do not treat Claude-native ephemeral subagents as canonical Executive child work when output is proof-bearing or lifecycle-significant."
  - "Do not copy provider tokens, JWTs, cookies, auth files, API keys or ChatGPT tunnel credentials into Claude config, Agent OS, GitHub, Slack or prompts."
  - "Do not claim QUEUED, MCP delivery, CI green or a local model run means a Worker STARTed or end-to-end fabric is accepted."
  - "Do not retry the blocked post-update claude -p proof through alternate accounts/tools merely to evade the refusal."
danger_areas:
  - "Executive auth is resource/principal bound. Reachable localhost MCP does not authorize Claude to impersonate an allowed ChatGPT principal."
  - "Installed release and protected source diverged; editing from bf764 without current-source reconciliation risks duplicate or stale implementation."
  - "Any ambiguous modifying admission after send is EFFECT_UNKNOWN on that carrier; reconcile, never resubmit elsewhere."
  - "Macro primary checkout is dirty; keep this records carrier isolated from unrelated primary-checkout debris."
  - "Local pre-change Claude backups are recovery evidence, not a second policy plane."
---

## Continuation classification

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false

The local Claude principal/routing layer is configured and guarded, and the existing production
Executive ingress is live. The first-class authenticated Claude-to-Executive carrier is not yet proven.

## Capability delta

Before: Claude could run on the Mac Studio but was not globally Fable-first/fabric-first and had no
truthful authenticated admission route into Executive OS.

After: Fable is the configured global parent; native Agent/Task fan-out is fail-closed except explicit
bounded Opus orchestration/read-only audit; lifecycle-significant labor is directed to canonical
Executive child work; raw-socket bypass is rejected. The remaining critical dependency is narrow:
authenticate Claude to the existing production Executive transport and prove one real read plus one
harmless strict-v2 admission on that same carrier.

## Exact identities at boundary

- Protected Mastermind/Skillpack pin: a7d2b3049e5cdc523e91e61a6e9d70a1cb911157.
- Installed Executive release: bf764f494b9cd0ecede6234bb472c3344c8e77cc.
- Macro handoff worktree base: 33c73dd9f5e65936f0052cb28f4ece4880b51a43.
- Workstream owner: WS:EXECUTIVE-CAPACITY-FABRIC.
- Intended resume surface: fresh Sol/CEO session with Mac Studio plus current GitHub/Executive inspection.

## Primary next action

Reconcile current protected Executive MCP/auth/Claude-client source against installed bf764, then use
or build the smallest supported Claude-authenticated client on the EXISTING Executive transport.
Read-only production proof comes first; only then may one harmless Chairman-authorized strict-v2 submit
prove QUEUED / dispatched=false plus same-carrier readback.

## What must not be redone

Do not redo the Fable default, global routing hooks, fabric-first CLAUDE.md policy, raw-control-socket
falsification, or the ruling that proof-bearing/lifecycle-significant work belongs to canonical Executive
child work rather than hidden Claude-native subagents, absent a material invalidator.
