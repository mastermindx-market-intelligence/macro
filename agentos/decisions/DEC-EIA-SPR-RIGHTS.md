---
key: EIA-SPR-RIGHTS
question: >
  May Mastermind redistribute and display the EIA-authored Weekly Petroleum Status
  Report petroleum series already consumed by collectors/eia.py and the strategic
  reserves / commodities display surfaces, and what attribution / exclusion
  boundary applies?
answer: >
  Yes for EIA-authored website information products and data, subject to explicit
  EIA acknowledgment. EIA's current Copyrights and Reuse policy states that U.S.
  government publications are public domain and that users may use and/or
  distribute EIA data, files, databases, reports, graphs, charts, and other
  information products on its website or email distribution service. Mastermind
  must identify EIA as the source and include the applicable publication/source
  date when reproducing the information. This ruling does NOT clear third-party
  material that merely appears on an EIA page, and it does not authorize use of
  the EIA logo or other protected marks. It applies only to direct EIA-authored
  petroleum data products used by the existing EIA collectors/readers.
  Translations must identify MastermindX as responsible and link back to the
  original EIA page. Missing publication timestamps must be disclosed rather
  than substituted with observation or ingestion dates.
rationale: >
  The prior F01 rights census correctly failed closed because it had not read an
  EIA reuse policy and explicitly named DEC-EIA-SPR-RIGHTS as the missing
  verification step. That missing evidence is now present. EIA's official
  Copyrights and Reuse page expressly permits use/distribution of its website
  data and other information products with acknowledgment, while separately
  warning that contributed or licensed third-party resources may remain
  protected. 17 U.S.C. §105 independently states the general federal-government
  works rule, but the EIA agency-specific policy is the operative product-use
  evidence for this ruling. Existing ingestion does not itself prove rights; this
  decision is what closes only that previously-unrecorded posture.
alternatives:
  - option: Keep all EIA petroleum data rights-unknown despite the agency policy
    why_not: >
      That would preserve a stale uncertainty after the exact verification path
      named by the prior census has been completed, and would unnecessarily block
      an already-shipped direct EIA display plane.
  - option: Treat every asset or document reachable from eia.gov as cleared
    why_not: >
      EIA itself distinguishes protected third-party contributed/licensed
      materials. Rights attach to the direct EIA-authored information product,
      not to the domain name alone.
  - option: Treat public-domain status as permission to reuse the EIA logo
    why_not: >
      The reuse page separately restricts protected marks/materials; this
      decision is about data/information products, not branding.
evidence:
  - "EIA Copyrights and Reuse (observed 2026-09-27): https://www.eia.gov/about/copyrights_reuse.php — permits use/distribution of EIA website data/files/databases/reports/graphs/charts/information products, requests acknowledgment including publication date, and excludes protected third-party contributed/licensed material."
  - "17 U.S.C. §105, U.S. House Office of the Law Revision Counsel (observed 2026-09-27): https://uscode.house.gov/view.xhtml?req=%28title%3A17+section%3A105+edition%3Aprelim%29 — copyright protection generally unavailable for U.S. Government works, subject to the statute's limited exceptions."
  - "collectors/eia.py — direct EIA Weekly Petroleum Status Report series collector under data/eia/."
  - "engine/commodity_supply_context.py — display-only EIA petroleum-balance read; never enters scoring/alerts."
  - "research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md V-4 — prior explicit unknown posture and named DEC-EIA-SPR-RIGHTS verification path."
affects:
  - WS:MARKET-OS
  - research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md
  - collectors/eia.py
  - engine/commodity_supply_context.py
  - engine/strategic_reserves.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-27
---

This decision supersedes only the prior EIA V-4 `rights-posture-unrecorded`
classification for **direct EIA-authored petroleum information products**. It does
not change Yahoo, FRED, CFTC, exchange, licensed-physical, or other source-rights
rulings, and it does not promote any EIA-derived display into ranking, sizing,
alert, portfolio, or trade authority.
