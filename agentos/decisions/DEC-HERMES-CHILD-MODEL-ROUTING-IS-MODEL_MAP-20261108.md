---
key: HERMES-CHILD-MODEL-ROUTING-IS-MODEL_MAP-20261108
question: How should a Hermes parent pin the model that each delegated child runs on, and does OMH intelligent routing apply to those children?
answer: >-
  The advanced-delegation model_map backend is the owner of child model routing.
  The parent selects a child model by passing one `option` field per task --
  frontier, mechanical or sensitive -- and omitting it resolves to the backend
  default `sensitive`. Global `delegation.model` and `delegation.provider` stay
  in configuration but are inert behind `delegation.backend: model_map`.
  OMH keeps its category-chain routing brain for its own workflows and does not
  route Hermes children; its own dag tool tells the parent to pass tasks
  unchanged, each with its `option`.
rationale: >-
  One field per task is the surface Hermes already dispatches on, so eight
  children on different models run concurrently without a shared mutable
  setting. OMH routing of children would need a config write per dispatch,
  which serialises the fan-out and strands a route when the writer crashes.
  A single global pin cannot hold both cheap mechanical work and frontier
  reasoning at the same time, and it silently re-weights every existing child.
  Keeping the inert global pin means reverting the backend restores the prior
  route verbatim instead of leaving a half-migrated configuration.
alternatives:
  - option: Route each child through OMH omh_delegate_route
    why_not: Serialised config write per child, so concurrent children on different models are impossible; a crash mid-dispatch strands the route with no receipt.
  - option: Pin every child with one global delegation.model
    why_not: Forces one tier on all work, burns frontier tokens on mechanical sweeps, and silently changes the model behind every existing child.
  - option: Name provider-specific model ids per task
    why_not: Leaks vendor model strings into every call site and bypasses the backend that owns the provider and fallback map.
evidence:
  - "Chairman commission 2026-11-07: pinning the children's model must be fixed and ready, working alongside the Engineering bot where needed."
  - "Live config read of ~/.hermes/profiles/marketing/config.yaml: plugins.enabled includes advanced-delegation; delegation.backend model_map; default sensitive; options frontier/mechanical/sensitive; max_concurrent_children 8; max_spawn_depth 3; six fallback_providers untouched; delegation.model and delegation.provider present but inert."
  - "Option map as configured: frontier -> zai glm-5.3; mechanical -> byteplus-coding deepseek-v4-1-flash-261017; sensitive -> experientiallabs deepseek-v4.1-flash-uncensored."
  - "Provider-side check, not self-report: three children dispatched from fresh marketing sessions landed on experientiallabs, zai and byteplus-coding respectively, read back from the Hermes state database rather than from the children's summaries."
  - "OMH routing inventory: 18 category chains, all resolving to glm53, deepseek-v41-uc or deepseek-flash after ten dead heads were removed; pre-change backups retained as *.pre-modelmap.20261108T044712Z."
  - "~/.hermes/plugins/omh/tools/dag_tool.py::_backend_say states the child-routing owner explicitly: do not call omh_delegate_route; pass the tasks unchanged, each with its option."
  - "Open caveat, not accepted as clean: omh doctor still reports missing_heads=10, which is a catalog-versus-discovery-scan mismatch -- heads it flags as missing were serving children in the same window. Treated as cosmetic until the discovery path is inspected."
affects:
  - WS:AGENT-OS
  - WS:MARKETING-X-CATALYST-LOOP
  - hermes:profiles/marketing/config.yaml
confidence: high
reversibility: easy
decided_by: "marketing profile principal, child-model-routing-20261108"
decided_at: '2026-11-08'
---

# Hermes child model routing is the model_map backend

Two questions were asked together and they have different answers. Pinning a
child's model is a supported per-task field. Intelligent routing of children is
not OMH's job, and wiring it that way would have been a regression dressed as
capability.

## Pinning a child

A parent passes one `option` field in the task. `frontier` sends architecture,
hard debugging and adversarial review to `glm-5.3`. `mechanical` sends bulk
inventories, extraction and formatting to BytePlus `deepseek-v4-1-flash-261017`.
`sensitive` sends adversarial and TOS-adjacent design work to
experientiallabs `deepseek-v4.1-flash-uncensored`, and is also the backend
default, so a child that omits `option` gets exactly what every child got before
the change. One-shot `-z` sessions cap at two children regardless of the
configured limit of eight; attended sessions get the full eight, and children
may themselves delegate to a depth of three.

`delegation.model` and `delegation.provider` remain in the file on purpose.
They are inert while `delegation.backend` is `model_map`, and they are what a
revert to the previous backend would fall back to — keeping them makes that
revert a one-line change instead of an archaeology exercise.

## Why OMH does not route children

OMH carries the routing brain: 18 category chains mapping work categories to
live heads, repaired in this same window so that every chain resolves to one of
three providers rather than to ten heads that no longer exist. That brain serves
OMH's own workflows. Child routing belongs to the backend Hermes dispatches on,
and OMH's dag tool says so in its own words.

The rejected design was routing each child through `omh_delegate_route`. It is
rejected on mechanism, not taste: each dispatch rewrites shared configuration,
so eight concurrent children on different models cannot be in flight at once,
and a writer crash leaves a route with no receipt. The selected design keeps the
fan-out parallel and the route recoverable.

## What is proven and what is not

Proven: the configuration is live and read directly from disk, the option map
resolves to three distinct providers, and three real children landed on three
different providers as recorded in the Hermes state database.

Not proven: `omh doctor` still prints `missing_heads=10`. Heads it reports as
missing were serving children in the same time window, so the report is a
catalog-versus-discovery mismatch, but the discovery path was not inspected and
this is not claimed as clean.
