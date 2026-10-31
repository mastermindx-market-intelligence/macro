---
key: FABRIC-CANONICAL-SOURCE-UNREADABLE-IS-MINIMAX-POOL-SPECIFIC
claim: >
  The Subagent Fabric refusal `canonical_source_unreadable` (launcher rc=78) is
  produced only for MiniMax pools: `$K/ext/slot.py::_pool_refusal_reason` returns
  None unless `_is_minimax_pool`, and only then checks the MiniMax binding id,
  git-object commit, reviewed realm, binding row and receipt-owner readability.
  GLM, go-codex, qwen and the other pools never emit it, so the 2026-10-21 GMI
  audit's "Fabric readability failure" (two rc=78 MiniMax returns) does not
  block GLM-routed lanes.
falsifier: >
  Open the installed kit's ext/slot.py `_pool_refusal_reason` and find a
  `canonical_source_unreadable` return reachable for a non-MiniMax pool, or
  launch a GLM lane that returns rc=78 with reason canonical_source_unreadable.
so_what: >
  Route GMI (and any other) leaf labor through the GLM pool while the MiniMax
  canonical-source binding is repaired by the kit/platform owner; never replay
  the two retained rc=78 MiniMax returns, and never describe the fabric as
  globally unreadable. Separate host admission refusals (rc=75, e.g.
  host_temperature_at_or_above_limit on ubuntu1, disk stage floors on
  ubuntu0/2/3) are capacity facts, not pool readability facts.
kind: constraint
verified_at: 2026-10-21
verified_by: >
  Read ext/slot.py lines 355-380 and 590-630 in the installed meta-ceo-b kit
  this session; ran `python3 ext/pool_status.py` (GLM cap 24 / active 5 / rem
  19, MiniMax cap 7 / active 0); three GLM launches on 2026-10-21 10:27Z were
  refused by HOST admission (rc=75 host_temperature_at_or_above_limit), not by
  canonical-source readability.
scope:
  - macro
  - WS:GMI-THEME-GRAPH
  - research/theme_graph/gmi_completion_20261021
confidence: verified
---

The audit's F-02 "Fabric readability failure" is pool-scoped. The GMI
completion program runs its leaves on GLM; the MiniMax binding repair is a
platform-owner item and is not on the program's critical path.
