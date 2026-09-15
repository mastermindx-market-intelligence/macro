---
key: PROPHET-AUDIT-CONVERSION-SEMANTICS
claim: >
  The inspected Prophet miss audit credits ticker-ever plan existence as conversion,
  and its basket visibility rule does not establish fresh-entry actionability.
falsifier: >
  Read engine/prophet_miss_audit.py at the cited revision: explicit opportunity-episode
  and time-window matching inside conversion_join would refute the first clause;
  entry-readiness validation in the basket miss rule would refute the second.
so_what: >
  Preserve the legacy metrics but do not interpret 21/124 as on-time opportunity
  conversion or a leaders-only basket as an actionable entry. Add episode-linked,
  time-aware diagnostics through existing identities and the existing admin consumer,
  retaining unknown when linkage or publication proof is absent.
kind: landmine
verified_at: 2026-09-15
verified_by: >
  GitHub source read of macro@b3240cbb2e69bba5286f15ab27f6b785ede4ab0e,
  engine/prophet_miss_audit.py lines 300-650 and 1740-1920;
  data/prophet_miss_audit/latest.json lines 1-155, 220-280, 530-590.
scope:
  - macro
  - prophet-us
  - engine/prophet_miss_audit.py
confidence: verified
---

## Bounded finding

`load_plan_assets` gathers any plan asset; `conversion_join` matches sighted tickers
against that set. It does not match opportunity identity, direction, or publication
window. This is a scope limitation, not a claim that the documented statistic is
arithmetically wrong.

At the cited source, the energy complex is represented by DINO/VLO in leaders and
has zero buy/watch members. `miss=false` uses a narrow top-decile-ignition AND
zero-visible-members rule. It is not a general fresh-entry success metric.

## Reconciliation that must survive this chat

The earlier source d9a56888ee33f868eda2669b7c6ab75b159be168 had zero runner rows.
The cited newer source has 150 top63 and 50 top21 rows at the SAME price_through
2026-09-14. The newer artifact supersedes the current-status description, not the
historical observation. Do not commission a fix on the assumption it is still empty.
No production root cause or repair is proven by the change in output alone.

Prices are through September 14 while referenced board/rotation are September 11.
This is date misalignment, not proof of a particular service outage or three trading
days of lag. The source holds 12 Energy names among 150 historical runners; Energy
is absent from the stricter cascade-eligible sector histogram. That does not prove
absence from every current admission route or from the served product.

## Continuation

Research and bounded implementation contract:
`research/prophet_us_audit/ROTATION_PACKET0_CONTINUATION_2026-09-15.md`.
Existing home: `WS:PROPHET-US-ENTRY-TIMING`. Do not create a duplicate workstream,
change its status from this observation, or treat an owner note as runtime liveness.

First next useful vertical: native full-input receipts -> additive diagnostic block
in the existing producer -> existing Prophet admin machine/UI consumer -> production
proof with unchanged strategy outputs. The offline prototype is not production code;
no trading performance or model promotion is established. No worker was assigned.
