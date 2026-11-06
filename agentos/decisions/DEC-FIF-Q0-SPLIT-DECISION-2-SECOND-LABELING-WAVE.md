---
key: FIF-Q0-SPLIT-DECISION-2-SECOND-LABELING-WAVE
question: >
  Generation one of the Q1 held-out evaluation left every pack
  unavailable_research_only, and most positive cells were too small to clear the
  predeclared 0.80 Wilson floor even at perfect precision. Protocol §10 reopens a
  failed family only on fresh held-out labels under a new split decision. What is
  split decision 2: which filings, which rule admits them, who labels them, and
  how are they sealed and measured?
answer: >
  Split decision 2 adds a second, predeclared labeling wave on the SAME five
  held-out issuers (AAPL, SNOW, CAT, BAC, GOOGL) over fiscal years that no other
  FIF corpus uses: for CAT, BAC and GOOGL the FY2020 and FY2021 10-Ks plus every
  10-Q of calendar 2021 and 2022 and the Q1-2023 10-Q; for SNOW the FY2021 and
  FY2022 10-Ks (periods 2021-01-31, 2022-01-31) plus every 10-Q of FY2022 and
  FY2023 and the FY2024 Q1 10-Q (2023-04-30); for AAPL the FY2022 and FY2023 10-Ks
  plus every FY2022 and FY2023 10-Q and the FY2024 Q1 10-Q (2023-12-30). That is
  nine accessions per issuer, forty-five in all, each disjoint from the AAPL gold
  pair (FY2025 10-K, FY2026 Q3 10-Q), from wave one (fif-held-out-v1 rows), from
  the D0 five-issuer coverage contract and from g_src. The accession numbers are
  fixed in held_out_contract.json before any capture or label is written, each
  row carrying split_decision: 2. The capture script gains a contract-level
  admission_rule "predeclared_split_rows" (default stays the R5 two-latest rule)
  that admits exactly the rows whose split_decision equals a required
  --split-decision flag, only for a held-out contract and never for the g_src
  default output root; per-issuer capture_index.json and request_log.jsonl are
  merged, never truncated. Bytes stage on ubuntu2 under the existing
  ~/lanes/stage/fif-heldout/ root (new accession directories only); manifests enter
  git digest-only. Labels are written by new independent labeler lanes that never
  read pack source, one lane per pack over all forty-five filings so no two
  lanes touch the same seal, into the same packs/PKxx/labels/ directories as
  new files <ISSUER>_<accession>.json; the wave-one _SEALED block stays byte-identical and
  each labeler appends one wave-2 block (sealed_by, sealed_at, head_commit,
  split_decision: 2). Generation three of Q1 then runs the unchanged evaluator
  over the union of both waves under the unchanged 0.80 floor into a new reports
  directory. Families whose positive trials cannot reach sixteen even on sixty
  filings (10-K-only disclosures on five issuers) stay underpowered honestly;
  they reopen only through new issuers under the coverage program.
rationale: >
  The floor is frozen and N may not be lowered after a result, so the only lawful
  remedy for a perfect-but-small cell is more labelled trials. Sixteen positive
  trials is the smallest cell whose perfect-precision Wilson lower bound (0.806)
  clears 0.80, and forty-five additional filings roughly quadruple most
  10-Q-bearing families. Reusing the five issuers keeps the frozen contract, the
  sector classes, the SIC bindings and the witnesses, so labeling can start as
  soon as the bytes are staged; new issuers would need contract and capture work
  first and belong to the coverage program. Predeclaring the accession set in the
  contract and admitting it by rule keeps the anti-cherry-pick property of R5 for
  production while making the held-out split auditable: the rule, the rows and
  the decision are all in git before the first label exists.
alternatives:
  - option: Lower the precision floor or exempt small perfect cells
    why_not: Forbidden after a result (DEC:FIF-Q1-PRECISION-FLOOR-PREDECLARED-0-80; protocol §6, §10).
  - option: Run the existing R5 capture over an extended contract
    why_not: R5 admits only the two latest 10-Ks and 10-Qs per issuer, all already used by wave one or D0; the test suite forbids admitting capture-only rows, so no older filing could ever be admitted.
  - option: Add new held-out issuers now
    why_not: New issuers need contract, SIC witness, capture and applicability work before one label and would change the sector classes the packs claim; they remain the coverage program's instrument.
  - option: Second held-out root or per-wave contract files
    why_not: The protocol names one held-out root; the evaluator binds SIC from held_out_contract.json and the packages test joins one capture_index per issuer, so parallel roots or contracts would fork the record.
evidence:
  - "reports/q1_held_out_20261031: perfect cells below the floor by N alone — PK01 liquidity 10/10, maturity_schedule 5/5, PK06 lease_liability 12/12, PK07 goodwill_intangibles 8/8, PK09 icfr_opinion 6/6"
  - "Wilson 95% lower bound at k=n: n=12 0.758, n=14 0.785, n=16 0.806"
  - "Used-accession census 2026-10-31 (seat, offline over config/fundamental_forensics/coverage, g_src, gold root, held-out root): D0 holds FY2023–FY2026 for CAT/BAC/SNOW/GOOGL and FY2025–FY2026 for AAPL; wave one holds FY2022 10-K + 2023 10-Qs (CAT/BAC/GOOGL), SNOW FY2023 + 2023 10-Qs, AAPL FY2024 + 2024 10-Qs"
  - "Public EDGAR submissions (data.sec.gov, read-only, 1 req/s, declared UA) 2026-10-31: all forty-five wave-2 accessions are inline XBRL 10-K/10-Q filings filed 2021-01..2023-06 (AAPL from the committed five_issuer_submissions fixture)"
  - "scripts/capture_fif_issuer_packages.py r5_admission_candidates (two latest 10-K + two latest 10-Q); tests/test_fundamental_forensics_held_out_packages.py test_committed_capture_only_rows_are_never_admitted; IssuerRequestLog opens its log with mode w"
  - "FIF_Q0_QUALITY_PROTOCOL.md §1 split law, §3 per-issuer split, §6 minimum N, §10 reopen_requires"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - scripts/capture_fif_issuer_packages.py
  - tests/fixtures/fundamental_forensics_held_out/held_out_contract.json
  - tests/fixtures/fundamental_forensics_held_out/packages/
  - tests/fixtures/fundamental_forensics_held_out/packs/*/labels/
confidence: high
reversibility: costly
decided_by: "FIF Meta-CEO seat 96dc937a (Fable)"
decided_at: 2026-10-31
---

Split decision 2: forty-five predeclared older-FY filings of the same five issuers, admitted by a contract-level predeclared-rows rule, labelled by new independent lanes, sealed as an appended wave-2 block, measured by Q1 generation three under the unchanged floor.
