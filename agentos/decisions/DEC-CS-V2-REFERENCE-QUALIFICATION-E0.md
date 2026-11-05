---
key: CS-V2-REFERENCE-QUALIFICATION-E0
question: >
  Masterplan task E0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A07 and A09) must qualify the exact reference
  documents, source policy, rights, issuer identities and labelled gold that
  every later Capital Structure V2 wave (L0 rule applicability, T0 extraction,
  B0 share basis, F0 funding, G0 gold, U0 product) may bind to, without a new
  collector and without guessed facts. Which documents, editions, spans,
  identities and fixtures are qualified, where does that binding live, and
  what may a later wave not do with it?
answer: >
  One machine-readable pack, config/capital_structure_reference_pack.v1.json
  (schema capital_structure.reference_pack.v1, version
  capital-structure-reference-qualification/1.0.0), read and validated by
  engine/capital_structure/reference_qualification.py, is the binding. It
  holds thirteen qualified sources, each with url, retrieved_at, http status,
  byte count and sha256 of the raw body: the SEC Securities Act Forms C&DI page
  (edition 2026-09-25) with the six exact question spans 116.21 to 116.26 and
  their interpretation dates (2008-11-26, 2010-08-11, 2010-08-11, 2013-05-16,
  2016-11-02, 2026-03-19), the March 19, 2026 C&DI update page, the Nasdaq
  5600 Series rulebook (browser-qualified after an HTTP 403 to a plain client,
  five excerpt-limited spans of at most 500 characters covering 5635(a)-(d)
  and IM-5635-3 with their amendment trails), Release 33-11418 Registered
  Offering Reform recorded as proposed_reform with status proposed and no
  final-rule evidence, the 2026 rulemaking index that still lists it as a
  Proposed Rule, the SEC developer fair-access page (10 requests per second,
  declared user agent), company_tickers.json and the six submissions indices
  for the archetype CIKs. Eight rule examples (three negative) preserve the
  official staff and exchange examples as rule tests, including the 116.23
  arithmetic ($10 million limit, $2.5 million sold, $7.5 million remaining,
  $5 million cap on the June 14 supplement), the 116.26 continuing-ATM staff
  position, the S-3 versus F-3 instruction-numbering difference, the Nasdaq
  approval context (transaction, price, quantity, voting power) and the
  IM-5635-3 public-offering determination. Six identity bindings re-qualify
  the archetypes against the live registry: AIR, CLNN, QNCX, LPTH and EDBL
  keep their labels and supply their cases; WHK is label drift (registry name
  WhiteHawk Minerals Corp., former name WhiteHawk Income Corp to 2026-06-09)
  with no S-3-family registration, so its case is unsupplied, the old witness
  is preserved and a replacement is owed, never guessed. Eleven gold fixtures
  under tests/fixtures/capital_structure/ are bound by path and sha256 with
  their consuming suites and reviewed expectations. The source policy mirrors
  docs/CAPITAL_STRUCTURE_INTELLIGENCE_CONTRACT.md (in-policy and out-of-policy
  forms, 500-character excerpt cap, HTTP 403 is never missing-index evidence,
  reserves 500/20/20 under a 540 ceiling) and records that E0 changed no
  reserve and added no collector. Fact origins are typed: canonical_extraction
  and adjudicated_gold may mint facts; llm_proposed_span, llm_interpretation,
  issuer_assertion and model_prose may not. Four gaps are named with owners:
  the binding Form S-3/F-3 General Instruction text (L0), the WHK replacement
  issuer, the foreign-issuer F-3 witness and the held-out pattern witness. A
  requalification procedure records how to re-derive every hash.
rationale: >
  The original waves bound rules and cases to prose citations and to ticker
  labels from 2026-08-18; one of the six anchors has since been renamed and
  no longer files on the forms the program covers, and the staff positions the
  program relies on have an edition date and a per-question interpretation
  date that no code recorded. A07 forbids silently reusing old labels and A09
  forbids an LLM span minting a fact, so the binding has to be byte-exact
  (sha256 per source and per span), dated, rights-aware and typed by fact
  origin before L0 encodes a single applicability rule or T0 extracts a single
  term. Keeping the pack outside the nightly collector and the SEC request
  budget (thirteen paced research-seat requests, reserves untouched) honours
  §7 S05/E04. Recording Release 33-11418 as proposed_reform that the module
  can never mark enforceable closes E03 structurally rather than by review.
alternatives:
  - option: Retrieve the binding Form S-3 and Form F-3 General Instruction text (17 CFR 239.13 / 239.33) in E0 and encode applicability rules now
    why_not: E0 is qualification of existing references, not rule encoding;
      the eCFR edition and effective date belong to L0's rule-applicability
      pack, so the gap is named and owned instead of half-filled.
  - option: Store the full Nasdaq rule text and full C&DI page text in the repository
    why_not: The Nasdaq rulebook is copyrighted and the contract caps excerpts
      at 500 characters; the SEC page is public domain but the pack needs exact
      question spans with dates, not a page mirror that drifts on every edit.
  - option: Keep the 2026-08-18 ticker labels and section references as the identity binding
    why_not: WHK is now WhiteHawk Minerals Corp. with no S-3-family filings;
      reusing the label would be exactly the silent reuse A07 forbids, and a
      guessed replacement issuer would be a fact without a source.
  - option: Treat Release 33-11418 as near-final and model the reformed shelf rules
    why_not: REJECTED_BY_DESIGN. The release is a proposed rule with comments
      due 2026-07-27 and no adopting release; the masterplan forbids
      implementing it as effective law.
  - option: Let the nightly collector fetch and re-hash these references each run
    why_not: It would spend the 500/20/20 class reserves on non-filing pages
      and add a second collector, both forbidden by §7; requalification is a
      manual, paced, receipted procedure.
evidence:
  - config/capital_structure_reference_pack.v1.json (sources[], rule_examples[], identities[], gold_cases[], gaps[], requalification_procedure)
  - engine/capital_structure/reference_qualification.py (parse_reference_pack, verify_gold_fixtures, enforceable_sources, rule_sources, qualification_report)
  - tests/test_capital_structure_reference_qualification.py (32 tests; tampering with a span, a gold hash, a drift flag, the reform class or the collector flag each fails)
  - SEC C&DI Securities Act Forms page sha256 9a6b1c41263425319f9ebb10a8e62b0734333c8544aa9288a3a301d6f5e9c906 retrieved 2026-10-13T13:32:50Z
  - Nasdaq 5600 Series rendered page text sha256 25b336964180ff319bfc0f211a92951e81e0bf7ecc599cd9e7169b967938ee05 (plain GET returned HTTP 403)
  - Release 33-11418 page sha256 193732ea63aec2149fb4e194c2082aa3e4e441583355b126e16e19c8f5583bae (Proposed, file S7-2026-17)
  - SEC submissions index CIK0001921603 sha256 6583025489b4ce956b5c262e9206f93eaea51ea3a3b9efaa99546a35e69c9cdc (WhiteHawk Minerals Corp., former name WhiteHawk Income Corp)
  - research/CAPITAL_STRUCTURE_INTELLIGENCE_V2_MASTERPLAN_2026-08-18.md §16.1-§16.6 (the prior labels being requalified)
affects:
  - engine/capital_structure/reference_qualification.py
  - config/capital_structure_reference_pack.v1.json
  - tests/test_capital_structure_reference_qualification.py
  - masterplan tasks L0, T0, B0, F0, G0, U0 (consume the pack; never re-qualify by prose)
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-13
review_by: 2026-11-13
---

# Reference qualification for Capital Structure V2 (E0)

The pack is the only place a later wave may read a reference document, a
staff example, an issuer identity or a gold expectation from. A changed span
hash is a new edition and gets a new interpretation-date witness; a changed
gold hash is a gold change that needs its own reviewed expectation update; a
registrant rename is label drift with the former name kept as a historical
witness. `proposed_reform` sources can never be enforceable and never back a
rule example. Non-canonical fact origins can never mint a fact.
