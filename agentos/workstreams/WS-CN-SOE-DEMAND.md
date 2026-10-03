---
key: CN-SOE-DEMAND
title: China Government / SOE Demand source map (Grid/Power first)
objective: >
  First-party source map for the Government/SOE Demand vertical, Grid/Power first.
  Done for C0 = the census and one bounded pilot recommendation exist; no collector,
  no score, no Prophet family.
status: active
program: china-system
repos: [macro]
owner: grok-cn-c
class: research
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - research/china_alpha/censuses/CN-C/
depends_on:
  - WS:DEFENSE-PROCUREMENT-V3
artifacts:
  - research/china_alpha/censuses/CN-C/CN-C_GOV_SOE_DEMAND_SOURCE_MAP.md
  - research/china_alpha/censuses/CN-C/CN-C_PROBE_RECEIPTS_2026-08-19.md
  - research/china_alpha/censuses/CN-C/CN-C_CIE11_C0_C1_GATE_2026-10-03.md
discoveries:
  - DSC:CN-CSG-HTML-VS-SGCC-ECP-SPA
landmines:
  - "Do not fork engine/government_revenue/ onto China. Adopt the event vocabulary only."
  - "Do not ingest dlnyzb / chinabidding / toobiao / other bid aggregators."
  - "Do not cron search.ccgp.gov.cn — it 频繁访问-blocks this egress on the second query."
  - "Do not log into CSG :9090/gmp or ECP /isc/ to fetch 中标通知书 or contracts."
  - "中标人 legal name resolution is CN-B, not a second matcher in this lane."
  - "江苏政府采购网 forbids republication without written permission."
do_not_redo:
  - "Do not rebuild the US GovRev store, SAM rail, or USAspending spine for this vertical."
  - "Do not treat 寻源公告 on bidding.csg.cn as 采购意向 — verified stale/non-intention."
  - "Do not treat national GGZY as a notice ledger — platform.js is a provincial directory."
waves:
  - id: C0
    title: First-party source map + bounded Grid/Power pilot recommendation
    status: done
    next_action: >
      ACCEPTED 2026-10-03 for technical pilot shape only: CSG-GD-货物-90d
      remains the bounded first rail. This does not clear C1 source use rights.
      Do not start an ECP scraper or ingest third-party bid aggregators.
  - id: C1
    title: Display-tier CSG Guangdong goods adapter (receipts only)
    status: todo
    depends_on: [C0]
    next_action: >
      RIGHTS_BLOCKED. Targeted 2026-10-03 verification confirms the public CSG
      notice rail remains readable, but the portal's 法律声明 / 服务条款 footer still
      resolves to a non-document placeholder. Existing rights/Data OS owner must
      adjudicate the exact C1 use classes before any automated collection or
      retained/customer-facing adapter. If cleared, use public HTML notices,
      CG… business keys, typed INTENTION_NOT_PUBLIC / CONTRACT_NOT_PUBLIC, no
      login and no score.
next_action: >
  Consume research/china_alpha/censuses/CN-C/CN-C_CIE11_C0_C1_GATE_2026-10-03.md.
  C0 is accepted. C1 remains RIGHTS_BLOCKED pending an explicit use-class ruling;
  do not collect, backfill, switch to ECP/aggregators, log in, or purchase a
  source as a workaround. Independent China Information-Edge lanes may proceed.
---

Research workstream for GROK-CN-C. Runtime authority is NONE. C1 does not start from this record.
