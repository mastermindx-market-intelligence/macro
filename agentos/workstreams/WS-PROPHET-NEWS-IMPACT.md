---
key: PROPHET-NEWS-IMPACT
title: Prophet news-to-business-impact — measured event packets, baselines and a graded benchmark
objective: >
  Turn company news into a measured, span-cited, typed business-impact packet that
  Prophet can consume as context_only evidence. Done means: three frozen event
  templates with acceptance labels and closed schemas live under
  contracts/news_impact/; a validator in engine/news_impact/ rejects unknown fields
  and unsolicited instructions; a 600-case graded benchmark (200/200/200) reports
  critical-numeric correctness, material-event routing recall and zero unsupported
  ticker-to-supplier assertions against the masterplan §11 thresholds; and the
  Prophet evidence owner reads the packets without any change to master procedures,
  live portfolios, B4 gates, source licenses or provider authentication.
status: active
program: prophet-us
repos: [macro]
owner: fable-ceo
class: research
blast_radius: reversible
ambiguity: scoped
depends_on:
  - WS:PROPHET-US-V4-RECOVERY
owns_paths:
  - research/prophet_v4/news_to_business_impact_20261006/
  - research/PROPHET_NEWS_IMPACT_CONTINUATION_HANDOFF_2026-10-11.md
  - engine/news_impact/
  - contracts/news_impact/
  - tests/test_news_impact_*.py
  - agentos/handoffs/PROPHET-NEWS-IMPACT-*.md
landmines:
  - "Sol's DRAFT PR #8533 carries the masterplan packet on research/prophet-news-impact-masterplan-20261006; it is superseded by this workstream's branch (cherry-pick -x of cde0219b1040) and closes with one comment once the Phase 0 PR merges — never merge or rebase #8533 itself."
  - "Adjacent Sol lanes never touched by this workstream: #8697 (tiingo news quality, DRAFT/HOLD), #8698, #6514 (K3-D, HOLD-FOR-SOL). Masterplan §12 commission C never repairs or merges #6514."
  - "Masterplan §13: no changes to master procedures, live portfolios, B4 gates, source licenses, provider authentication or existing active workers. New code lives only in the LEAF namespace engine/news_impact/ + contracts/news_impact/ and consumes existing owners (engine/news_events.py, engine/news_event_ledger.py, engine/company_intelligence/*)."
  - "DNR:KILL-LLM-CONFIDENCE and DNR:KILL-CAUSAL-DAG-ALPHA bind: no model confidence field, no price target, no 0-100 rerating score, no multi-hop theme prediction in any packet schema."
do_not_redo:
  - "Phase 0 recovery census (2026-10-11): nothing of this program is in origin/main; no sibling session owns it; engine/news_impact/ and contracts/news_impact/ are free. Do not re-census."
  - "Orchestration shape: Fable seat → one native Opus orchestrator → read-only fabric lanes on local m2 pools (glm-5.3-flash census, glm-5.3 candidates + attack reviews) → orchestrator synthesis → seat adjudication. The Workflow tool is platform-blocked in the seat session (hook dispatch timeout, verified twice); do not try it a third time."
waves:
  - id: p0
    title: Phase 0 — recovery census, three-candidate commission A, seat freeze of event templates + closed schemas
    status: in_progress
    next_action: Adjudicate $S/design/SYNTHESIS_RECOMMENDATION.md by artifact, write PHASE0_FREEZE_2026-10-11.md + contracts/news_impact/*.schema.json, open the Phase 0 PR and carry it to merged.
  - id: w1
    title: Wave 1 — benchmark candidate sampler (L3) + schema validator with hostile fixtures (L4)
    status: todo
    depends_on: [p0]
  - id: w2
    title: Wave 2 — commission D 600-case graded benchmark (200 capital allocation / 200 demand-guidance / 200 strategic-partnership)
    status: todo
    depends_on: [w1]
  - id: w3
    title: Wave 3 — Phase 1 measured packet producer wired to the existing event ledger, context_only, behind the benchmark gate
    status: todo
    depends_on: [w2]
next_action: Adjudicate the ORCH-W1 synthesis by artifact and freeze commission A (three templates, acceptance labels, shared $defs), then open the Phase 0 PR.
---

# Prophet news-to-business-impact

Masterplan: `research/prophet_v4/news_to_business_impact_20261006/package/MASTERPLAN.md`
(cherry-picked from Sol's DRAFT PR #8533, commit `cde0219b1040`). Chairman assignment
2026-10-10/11: the Fable Meta-CEO seat owns delivery end to end, autonomously, with
labor on the Mastermind Executive/Subagent Fabric and judgment in the seat.

Program state at resumption grain lives in
`research/PROPHET_NEWS_IMPACT_CONTINUATION_HANDOFF_2026-10-11.md` (DECIDED / FACTS /
OPEN / NEXT + lane matrix). Phase 0's freeze is
`research/prophet_v4/news_to_business_impact_20261006/PHASE0_FREEZE_2026-10-11.md`.
