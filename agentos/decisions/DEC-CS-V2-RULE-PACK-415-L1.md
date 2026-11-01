---
key: CS-V2-RULE-PACK-415-L1
question: >
  Masterplan task L1 (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  acceptance rows A12, A13, A14 and A20, depending on L0) owes the L0 pack two
  debts: the binding text of Rule 415 and Securities Act Section 10(a)(3), and
  the pre-2016 Form S-3/F-3 editions. Which exact text of 17 CFR
  230.415(a)(1)(x), (a)(4), (a)(5) and (a)(6), 17 CFR 230.462(e) and 15 U.S.C.
  77j(a)(3) governs on a given day, on which days is it verified rather than
  bracketed, and does either L0 gap close on retrieved evidence?
answer: >
  The L0 pack is reissued as capital-structure-rule-applicability/1.1.0 with
  six new binding rules and no reader change beyond the version constant.
  Twenty-three paced research-seat requests retrieved 16 new sources: the eCFR
  title index (title 17 up_to_date_as_of 2026-10-09, the current edition D),
  the 230.415 and 230.462 edition indices, the current edition plus every
  point-in-time edition each index lists (seven for 230.415: 2016-11-21,
  2020-06-01, 2020-08-01, 2021-12-09, 2022-01-31, 2024-07-24, 2024-09-23;
  three for 230.462: 2016-11-21, 2020-06-01, 2020-08-01), Release 33-8591
  (SECURITIES OFFERING REFORM, FILE NO. S7-38-04, RIN 3235-AI11, final, printed
  EFFECTIVE DATE: December 1, 2005) and the govinfo USCODE-2024-title15 granule
  for 15 U.S.C. 77j. Forty-eight new spans (17 stored texts, 31 same_as edition
  aliases) carry the exact paragraph text: 415(a)(1)(x), (a)(4), (a)(5) with
  (i), (ii) and (ii)(A)-(B), (a)(6), 462(e), 77j(a)(3), the release's adopted
  text for each, its amendatory instructions, its release-number block and its
  effective date, and the two eCFR source notes. Each paragraph was compared
  edition by edition rather than assumed identical, and two do change:
  415(a)(1)(x) at the 2020-08-01 edition (350 to 458 chars) and 415(a)(6) at
  the 2022-01-31 edition (1203 to 1277 chars, inserting "unless expressly
  required in another part of the registration statement"), so their
  version_index windows split there; 415(a)(4), 415(a)(5) and 462(e) are
  byte-identical across every served edition, so theirs do not. Each of the five
  CFR rules carries a point at 2005-12-01 and a bracket 2005-12-01..2016-11-21
  on the release span, earned because the release's adopted text and the
  earliest served edition share one normalized_sha256 in all five cases. There
  is no point at today: full/2026-10-14/title-17.xml was refused with HTTP 404
  for both sections, so the last verified CFR day is 2026-10-09 and later days
  answer beyond_window. Release 33-8591 ADDS (a)(5), (a)(6) and 462(e), which
  are therefore not_in_force before 2005-12-01, and REVISES (a)(1)(x) and
  (a)(4), which pre-existed and are therefore withheld, never not_in_force.
  77j(a)(3) is a single point at the 2026-10-14 qualification date because the
  granule prints "United States Code, 2024 Edition" and no edition date, with
  everything before it withheld. The rule_415_and_section_10_a_3_text gap closes
  with closed_by L1; pre_2016_form_editions stays open because sec.gov serves
  only the current (02-25) editions. Release 33-11418 remains excluded.
rationale: >
  L1a's shelf-window and automatic-effectiveness predicates only become
  conditional when the pack carries Rule 415(a)(5) and Rule 462(e) as verified
  or bracketed text on the day in question, so a guessed or mis-dated paragraph
  would make every downstream capacity answer a fabrication. Retrieving every
  served edition and comparing paragraph digests is what separates "the text did
  not change" (a measured fact) from "the text is the same" (an assumption);
  two of the five provisions really did change, and a single current-edition
  retrieval would have dated the new text back to 2016. Earning the bracket only
  on a shared normalized_sha256 keeps the release-to-eCFR interval honest: where
  the adopted text and the earliest edition agree typographically-blind, the day
  between them lies between two qualified editions; where they did not agree, no
  bracket would be emitted and the days would answer withheld. Separating
  not_in_force from withheld by what the release itself says (ADD versus REVISE)
  is the same discipline: the packet expected (a)(1)(x) to be added, the release
  says it was revised, and the release wins. Refusing to invent a point at today
  after a 404, and refusing to invent an edition date for a statute granule that
  prints none, keeps A20's rule that unknown never becomes a convenient value.
alternatives:
  - option: Retrieve only the current eCFR edition and date each paragraph back
      to the adopting release
    why_not: Measured false. 415(a)(1)(x) changes at the 2020-08-01 edition and
      415(a)(6) at 2022-01-31; one window per provision would have asserted
      today's text for days that carried different text.
  - option: Mark 415(a)(1)(x) not_in_force before 2005-12-01 as the packet
      expected
    why_not: Release 33-8591 item 30.b reads "Revise paragraph (a)(1)(x)", so
      the paragraph existed before the release; not_in_force would assert a
      repeal-and-readoption that never happened. Withheld is the true answer.
  - option: Emit a point window at today for the CFR provisions
    why_not: full/2026-10-14/title-17.xml returned HTTP 404 for both sections.
      Without served bytes there is no verified day at today; the honest state
      after 2026-10-09 is beyond_window with a requalify condition.
  - option: Record 70 FR 44722 as the release's Federal Register citation
    why_not: The retrieved release PDF prints no Federal Register citation at
      all. The only retrieved FR citations are the eCFR source notes - 70 FR
      44812 for 230.415 and 70 FR 44818 for 230.462 - and only those were
      encoded.
  - option: Close pre_2016_form_editions with the sec.gov /about/forms/ aliases
    why_not: Both return the CURRENT editions, byte-identical to the already
      qualified form_s3_pdf and form_f3_pdf sources, labelled SEC 1379 (02-25)
      and SEC 1983 (02-25). "(02-25)" is not older than "(02-25)"; directory
      browsing is refused, so no archived edition is reachable and the gap stays
      open with all four attempts recorded.
  - option: Change the reader to express the split-edition windows
    why_not: Not needed. parse_rule_applicability_pack already accepts ordered
      windows of mixed kinds with equal starts, per-window span pins and
      before_first_window of withheld or not_in_force; only the version constant
      changed.
evidence:
  - config/capital_structure_rule_applicability_pack.v1.json (sha256 2be52749456bddcd54bdfe973268b933313e11763f23d227688875efba2417e3; 38 sources, 78 spans, 24 rules, 18 findings, request_policy.l1_requests)
  - engine/capital_structure/rule_applicability.py (RULE_APPLICABILITY_PACK_VERSION is the only line changed)
  - tests/test_capital_structure_rule_applicability.py (88 tests; the 35 appended ones cover per-rule as-of ladders, span digest recomputation, window ordering and pins, the release revision-versus-addition split, the request log, both gaps, and the disclosed page folio inside the release's (a)(5) span)
  - Review repair (O2): the release PDF breaks the (a)(5) paragraph across a page, and the derived text prints the folio "370" and a form feed there. The span omits that page furniture, and the span now records the omission in a page_furniture_removed note; its normalized digest equals the 2016-11-21 eCFR (a)(5) span
  - Release 33-8591 retrieved from https://www.sec.gov/rules/final/33-8591.pdf (sha256 449cb5a5b533d72b4cf56e9b3647efe2f86c306983378b435424726c42281a6b, 2287419 bytes), derived with pdftotext -layout 24.02.0 to sha256 88ea8e973d3c5383648279c5d1b08f7735bda3641cdcf9dce4a5069568311ac8
  - 15 U.S.C. 77j retrieved from https://www.govinfo.gov/content/pkg/USCODE-2024-title15/html/USCODE-2024-title15-chap2A-subchapI-sec77j.htm (sha256 dd1637e9def25ad6736ce2c810dd05f5d19cbeab51b3447adec60695d9222fc9, 8732 bytes)
  - 23 paced requests in request_policy.l1_requests, including the three refusals (two HTTP 404 on full/2026-10-14, one HTTP 301 on sec.gov/about/forms)
affects:
  - engine/capital_structure/rule_applicability.py
  - config/capital_structure_rule_applicability_pack.v1.json
  - tests/test_capital_structure_rule_applicability.py
  - WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
  - masterplan tasks L1a, C1 and G0 (consume the 415/462(e) windows and the as-of states; never re-derive rule text by prose)
confidence: high
reversibility: easy
decided_by: opus-suborchestrator-l1b-under-fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
review_by: 2026-11-14
---

# Rule 415, Rule 462(e) and Section 10(a)(3) text (L1)

A paragraph is verified on a day only when a retrieved edition covers that day.
Every served eCFR edition of 230.415 and 230.462 was retrieved and compared
paragraph by paragraph; where the text changed, the window split, and where the
release's adopted text and the earliest edition share a normalized digest, the
interval between them is bracketed rather than guessed. What the release ADDS is
not_in_force before 2005-12-01; what it REVISES is withheld, because the earlier
text was never retrieved. A refused request produces no window, and a statute
granule that prints no edition date produces a single point at the qualification
date. One L0 gap closed; the pre-2016 form editions remain open with their four
attempts on the record.
