---
key: CFTC-COT-RIGHTS
question: >
  Can the COT positioning project retain and display CFTC-published aggregate
  government position data and Mastermind's original calculations without
  extending that permission to third-party market prices or the CFTC seal?
answer: >
  Use official public CFTC Legacy, TFF and Disaggregated aggregate reports for
  the scoped positioning feature, with visible CFTC acknowledgement and source
  provenance. The inspected CFTC Web Policy identifies its government
  information as public domain and permits copying and distribution. This
  record resolves the earlier unrecorded-rights finding for these COT government
  facts only. It clears no third-party content, price feed, seal, trademark,
  proprietary commentary, trading authority or production-release gate.
rationale: >
  The earlier F01 record correctly distinguished existing ingestion from a
  documented rights basis. That missing reading has now been performed on the
  primary source. The policy expressly separates government information from
  private contributed/licensed material, requires permission beyond applicable
  exceptions for the latter, and excludes outside use of the CFTC seal.
  Accordingly the board uses original Mastermind code/design, aggregate public
  position facts, textual attribution and a source link, with no CFTC seal and
  no third-party price series. This is a bounded product-source decision under
  the Chairman's current implementation commission, not legal advice or a
  worldwide clearance of every resource hosted by CFTC.
alternatives:
  - option: Treat all publicly reachable material as unrestricted
    why_not: CFTC explicitly distinguishes private copyrighted resources and seal use.
  - option: Leave the public COT facts indefinitely unknown despite the policy reading
    why_not: The missing primary-source reading is now available and supports this narrow use.
evidence:
  - https://www.cftc.gov/sites/default/files/cftc/cftcprivacy.htm
  - "CFTC Web Policy, Copyright and Use of CFTC Seal sections, inspected 2026-10-09."
  - https://portal.cftc.gov/TermsOfUseAgreement
  - "Portal Terms, Reproduction of CFTC Content, corroborating government-information distinction."
  - research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md
  - lib/cot_contracts.py
  - templates/cot_positioning.html.j2
affects:
  - WS:MARKET-OS
  - WS:ALPHA-INTELLIGENCE-INTEGRATION
  - cot-positioning-20261009-sol-001
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-10-09
---

This branch record is proposed source until accepted through the normal review
and merge path. A changed source policy, third-party dataset, non-public access
requirement, or new use class reopens its scope. Yahoo, FRED, exchange price
licensing and the standing source-specific gates remain unchanged.
