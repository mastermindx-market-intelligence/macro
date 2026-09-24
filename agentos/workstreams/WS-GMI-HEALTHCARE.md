---
key: GMI-HEALTHCARE
title: "GMI Healthcare — theme-intelligence vertical (GLP-1 first slice, twelve-family roadmap)"
objective: >
  Deliver the maintained GMI Themes Healthcare vertical, beginning with a truthful GLP-1
  slice and its visible FDA supply consumer while preserving the twelve-family roadmap.
  Completion is observable when the admitted releases reach their declared user journeys
  and per-release adjudication without adding ranking, sizing, or trade effects.
status: active
program: gmi-theme-graph
repos: [macro]
owner: ceo-fable
class: research
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - research/healthcare/hc_program/
  - collectors/fda_shortages.py
  - engine/fda_scarcity.py
  - tests/test_fda_shortages_generation.py
  - tests/test_fda_supply_probes.py
depends_on:
  - WS:GMI-THEME-GRAPH
decisions:
  - DEC:GMI-THEME-GRAPH-END-TO-END-COMPLETION-OWNERSHIP-SEQUENCING
do_not_redo:
  - >-
    Do not rebuild the shared base (theme-graph assertion/evidence/rights/route/mount);
    consume #7870's accepted contract — Chairman/Astra directive 2026-09-24.
  - Do not implement on the research branch #7788 or on #7870.
  - Do not re-ACK; PICKUP_ACK is #7788/5811997064.
  - >-
    Do not treat `probe_r7_fda.py` as a test of desired behavior — it characterizes
    the pre-D1 defects.
  - >-
    Do not add rank/entry/sizing/trade/stage effects from the FDA chip — display-only
    by plan.
  - No target price / expected return / underpricing claims in the first descriptive release.
artifacts:
  - research/healthcare/hc_program/
waves:
  - id: D1
    title: >
      T01 supply meaning in the visible FDA consumer; T02 sweep qualification and
      forward history; relevant T08 per-release adjudication.
    status: in_progress
    next_action: >
      Adjudicate the independent D1 review on #7788, post START naming carrier
      claude/healthcare-d1-fda-supply, run lanes hc_t02_fda_sweep then
      hc_t01_supply_meaning, run Opus red-team, merge, then verify the nightly drip and
      foresight chip live.
  - id: D2
    title: >
      T03 v1.1 shared-branch consumption; T04 private Research Vault binding; T05
      Healthcare profile on the common POST research routes; relevant T08 per-release
      adjudication.
    status: todo
    next_action: >
      Hold until #7870 lands on main, then consume its accepted shared branch and
      private-profile contracts without rebuilding the base.
  - id: D3
    title: >
      T06 complete GLP-1 five-part explanation and relevant T08 per-release
      adjudication.
    status: todo
  - id: D4
    title: >
      T07 correction and distinct non-metabolic mechanism with relevant T08 per-release
      adjudication.
    status: todo
next_action: >
  Adjudicate the independent D1 review on #7788, post START naming carrier
  claude/healthcare-d1-fda-supply, run lanes hc_t02_fda_sweep then
  hc_t01_supply_meaning, run Opus red-team, merge, and verify the nightly drip and
  foresight chip live.
landmines:
  - >-
    `data/fda/shortages.parquet` is a committed artifact re-written by the nightly drip — tests must never write it; sparse worktrees truncate it.
  - >-
    `tests/test_foresight_cascade.py` was unrun on CI before D1 (no legacy-jobs.yml job named it).
  - >-
    Protected current Healthcare assertions never enter public Git/HTML/JSON/mirrors (R4 §2).
---

## Operation and custody

- Operation: `gmi-healthcare-fable-ceo-e2e-20260924-chairman-001`.
- Commissioned by: Healthcare Fable CEO seat, session `1172846f`, under Chairman delegation `2026-09-24`.
- Research carrier: PR `#7788`, branch `claude/healthcare-theme-research-20260923`, frozen input commit `e5789583de2428b6dbdaa26266e8fc8e0655789a`.
- Master handoff: `agentos/handoffs/GMI-HEALTHCARE-MASTER-FABLE-CEO-HANDOFF-2026-09-24.md`, immutable at `81b67a83ad23d3b02685ea89135ea40c21a21d86`.
- Pickup acknowledgment: PR `#7788`, issue comment `5811997064`, `2026-09-24`, receiver session `1172846f`.
- Seat records directory: `research/healthcare/hc_program/`, carried by PR `#7928`.

The required workstream fields are exactly: `key`, `title`, `objective`, `status`, `program`, `repos`, `owner`, `class`, `blast_radius`, `ambiguity`, `waves`, and `next_action`.

## Handoff release facts

| Release | Plan tasks | Required useful result | Ownership boundary |
|---|---|---|---|
| D1 | T01–T02, relevant T08 checks | Truthful existing FDA supply observation and visible consumer, including incomplete/stale/mixed states | New Healthcare CEO coordinates the bounded existing collector/consumer repair after its own review and custody; does not wait for v1.1/private-profile readiness |
| D2 | T03–T05, relevant T08 checks | One real admitted Healthcare assertion reaches the existing protected page | Existing shared owner supplies/accepts common extension and private/transport interfaces; Healthcare integrates its explicit profile |
| D3 | T06, relevant T08 checks | Complete GLP-1 change/mechanism/participant/counterevidence/next-observation explanation | Healthcare domain composition and source-qualified synthesis; D1 required where misleading legacy output remains in the journey |
| D4 | T07–T08 | Real correction, distinct non-metabolic mechanism, honest broad navigation | Same existing correction/evidence/publication owners; no copied second stack |

The Healthcare workstream consumes, but does not own, `engine/theme_graph/`, `contracts/theme_graph/`, and `config/theme_sources.yml` under `WS:GMI-THEME-GRAPH` and PR `#7870`; it also consumes `engine/foresight_cascade.py` and `scripts/build_foresight.py` only at the FDA chip/drip seam.

## External rulings

R4 is recorded at PR `#7780`, comment `5808854275`; R12 is recorded at PR `#7870`, comment `5809358801`; the SEC rights basis is recorded at PR `#7870`, comment `5809660585`.

Regulator status, manufacturer availability, and any economic capacity thesis remain three separate observations. Discontinuation is not resolution; absence from a later complete snapshot is not resolution; partial acquisition is never promoted. Source generation (`meta.last_updated`), acquisition time, and render time remain distinct. Complete-empty, failed acquisition, stale cache, and unrecognized status remain distinct states. Cache history before an acquired snapshot is unknown, never backfilled.
