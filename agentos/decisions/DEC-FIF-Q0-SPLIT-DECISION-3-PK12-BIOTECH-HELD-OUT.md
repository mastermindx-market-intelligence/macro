---
key: FIF-Q0-SPLIT-DECISION-3-PK12-BIOTECH-HELD-OUT
question: >
  PK12 (biotech cash runway, R&D expense, going concern or financing) cannot earn a positive
  held-out cell. None of the five reference issuers is a biotech, so Q0 §5 gives PK12 one
  negative per issuer and nothing else. §6 says PK12 positives "need an explicit later issuer
  or stay blocked". §15 forbids a stealth biotech among the five. How does PK12 get a lawful,
  predeclared held-out wave, without lowering the floor and without touching any other pack's
  held-out claim?
answer: >
  Declare split decision 3. It is a PK12-scoped biotech held-out cohort, fixed now, before any
  label exists.

  Selection rule: SEC SIC code 2834, 2835 or 2836. The cohort mixes commercial-stage and
  clinical-stage issuers. Each issuer contributes its three 10-K filings (no 10-K/A) for
  fiscal years 2021, 2022 and 2023, as listed in EDGAR's public submissions index. That gives
  30 filings in total:
    GILD (0000882095) 0000882095-22-000007, 0000882095-23-000007, 0000882095-24-000007.
    AMGN (0000318154) 0000318154-22-000010, 0000318154-23-000017, 0000318154-24-000011.
    EXEL (0000939767) 0000939767-22-000026, 0000939767-23-000019, 0000939767-24-000028.
    IONS (0000874015) 0000874015-22-000079, 0000874015-23-000105, 0000874015-24-000116.
    NBIX (0000914475) 0000914475-22-000013, 0000914475-23-000011, 0000914475-24-000054.
    NTLA (0001652130) 0000950170-22-001981, 0000950170-23-004097, 0000950170-24-018736.
    EDIT (0001650664) 0001558370-22-001950, 0001558370-23-001764, 0001650664-24-000008.
    FATE (0001434316) 0000950170-22-002293, 0000950170-23-005067, 0000950170-24-020158.
    CRSP (0001674416) 0000950170-22-001282, 0000950170-23-003441, 0000950170-24-017571.
    ARWR (0000879407, fiscal year ends 09-30) 0001564590-21-057888, 0001628280-22-030869, 0001628280-23-040219.
  INCY is excluded because its EDGAR SIC is 8731, not a pharmaceutical code.

  Where the cohort lives: it enters the one held-out root through
  tests/fixtures/fundamental_forensics_held_out/held_out_contract.json. That file gets one new
  issuer row per issuer and one accession row per filing, each with "split_decision": 3 and
  pack scope PK12. It also gets a split_decisions entry with id 3 that names this decision.

  What each issuer row carries:
    - The contract sic.
    - A sic_source witness. This is a compact per-issuer extract of the public submissions
      JSON (cik, name, sic, sicDescription, tickers, source_url, retrieved_at, response sha256
      and the three 10-K rows), stored under
      tests/fixtures/fundamental_forensics_held_out/split3_submissions/. sic_source.sha256 is
      the sha256 of that committed file.
    - legal_name, ticker, fiscal_year_end, issuer_class, identity_binding_state
      "generic_path_only", and a security_master_binding.

  The evaluator refuses an issuer row without a security_master_binding
  (contract_identity_missing). So each binding is read from data/reference/security_master.parquet
  at the build's base commit, in the same shape as the five reference issuers' bindings.
  An issuer with no security-master row is dropped before capture, and the drop is recorded.
  No replacement issuer is chosen afterwards. The cohort can only shrink, before any label,
  and never after a result.

  Capture: the existing predeclared_split_rows rule with --split-decision 3, writing only new
  accession dirs onto the ubuntu1 held-out stage. Manifests enter git digest-only, and filing
  bytes stay staged, not committed.

  Labelling: an independent PK12 labeler labels the captured filings and appends one wave-3
  block to the PK12 _SEALED record. The wave-one and wave-two blocks stay byte-identical.

  Scoring: a new Q1 generation runs the unchanged evaluator, under the unchanged 0.80 Wilson
  precision floor, over the union, into a new reports directory. The existing PK12 g3 report
  stands as written.
rationale: >
  Q0 §6 already anticipates this route and names its only lawful form: an explicit later
  issuer, declared before labelling.

  The evaluator builds cells from labels, and the only labels this wave adds are PK12 labels.
  The new issuers therefore add PK12 cells and nothing else. No other pack's sector claim,
  denominator or report changes.

  Three FY2021–2023 10-Ks across ten issuers give PK12 room to reach n >= 16 per family. That
  matters because the Wilson lower bound at k = n reaches 0.806 only at n = 16, so smaller
  perfect cells still fail the fixed floor.

  The cohort is disjoint from everything that could have shaped the PK12 pack:
    - the five reference issuers;
    - gold, D0 and g_src;
    - wave one and wave two;
    - the PK12 dev-corpus biotech issuers (VRTX, REGN, MRNA, BEAM, BIIB; alternates ALNY, SRPT);
    - the FY2024–25 filings used in the candidate census.
  So no repair decision was made by looking at these filings.

  Mixing commercial-stage and clinical-stage issuers means both cash-runway and going-concern
  language get exercised, and the funded-commercial negatives get exercised too.
alternatives:
  - option: "Lower the 0.80 precision floor or exempt small perfect PK12 cells"
    why_not: "Forbidden by DEC:FIF-Q1-PRECISION-FLOOR-PREDECLARED-0-80 and Q0 §6/§10; Q1 may not lower N after seeing a result"
  - option: "Treat one of the five reference issuers as a biotech"
    why_not: "Q0 §15: PK12 will not gain a stealth biotech among the five reference issuers"
  - option: "Wait for the 250/1,000 coverage program to bring biotech issuers in"
    why_not: "That leaves PK12 permanently blocked inside this masterplan; coverage admission is not a held-out split and carries no predeclared label wave"
  - option: "Reuse the PK12 dev-corpus biotech issuers as held-out"
    why_not: "Those filings shaped the dev repair; held-out must be disjoint from anything a repair lane read"
  - option: "Second held-out root or a per-wave contract file"
    why_not: "The protocol names one held-out root and the evaluator binds SIC and identity from held_out_contract.json; split 2 rejected the same alternative"
evidence:
  - "FIF_Q0_QUALITY_PROTOCOL.md §5 (PK12 families cash_runway_disclosure, rd_expense, going_concern_or_financing; 10-K only), §6 PK12 row, §10 failed-family law, §15 no stealth biotech"
  - "Wilson 95% lower bound at k=n: n=12 0.758, n=14 0.785, n=16 0.806"
  - "EDGAR public submissions census 2026-11-01 (data.sec.gov, read-only, 1 req/s, declared UA): SIC, fiscal-year end and the 10-K accession list for all ten issuers; INCY SIC 8731"
  - "Disjointness: zero padded-CIK hits for the ten issuers across config/, tests/fixtures/fundamental_forensics and tests/fixtures/fundamental_forensics_held_out; the one 1434316 hit is a substring of file number 251434316 in an existing submissions file, not an issuer"
  - "scripts/fif_held_out_evaluate.py: an issuer row without security_master_binding raises contract_identity_missing; the packet entity reads legal_name and identity_binding_state from the contract row"
  - "tests/test_fif_held_out_capture_predeclared.py test_contract_rows_all_carry_a_known_split_decision pins split_decision in (1, 2); this decision widens it to (1, 2, 3)"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - scripts/capture_fif_issuer_packages.py
  - tests/fixtures/fundamental_forensics_held_out/held_out_contract.json
  - tests/fixtures/fundamental_forensics_held_out/split3_submissions/
  - tests/fixtures/fundamental_forensics_held_out/packages/
  - tests/fixtures/fundamental_forensics_held_out/packs/PK12/labels/
  - tests/test_fif_held_out_capture_predeclared.py
confidence: high
reversibility: costly
decided_by: "FIF Meta-CEO seat 96dc937a (Fable)"
decided_at: 2026-11-01
---

Split decision 3 is a predeclared, PK12-only biotech held-out cohort: 30 FY2021–2023 10-Ks
across ten issuers with SIC 2834–2836. It is labelled by an independent PK12 labeler and
scored under the unchanged 0.80 floor.
