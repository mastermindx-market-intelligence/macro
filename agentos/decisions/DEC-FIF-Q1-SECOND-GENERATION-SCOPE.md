---
key: FIF-Q1-SECOND-GENERATION-SCOPE
question: >
  After the first Q1 held-out generation (reports/q1_held_out_20261031) showed
  two non-pack causes — issuer SIC unbound for every accession and the BAC FY2022
  10-K refused whole by the parser — may a second generation be run, and what may
  it change?
answer: >
  Yes, as a new reports directory (reports/q1_held_out_20261031_g2) produced by a
  new independent evaluator lane on a main revision that contains both kernel-side
  repairs (DEC:FIF-Q1-EVALUATOR-BINDS-SIC-FROM-HELD-OUT-CONTRACT-20261031 and
  DEC:FIF-PARSER-NIL-FACT-INERT-ATTRIBUTES-TOLERATED-20261031). It re-runs the
  unchanged evaluator over the SAME sealed labels under the SAME predeclared
  precision floor (0.80). It is the first honest measurement for PK04, PK11 and
  PK12 and for the 30 BAC trials; it does not reopen, relabel, drop or hand-score
  any generation-one failed family — each keeps its disposition
  (reopen_requires: fresh held-out labels under a new Q0 split decision) unless
  the unchanged evaluator itself reports differently on the repaired inputs. The
  first generation stays committed and unedited.
rationale: >
  Protocol §10 blocks only the failed pack and forbids relabelling, dropping cells
  or lowering N after a result; it does not forbid measuring packs whose first
  result was empty for a reason outside the pack. Binding SIC from the committed
  contract and parsing an EDGAR-accepted filing are kernel repairs with no pack
  knowledge, so a re-run on the same labels is not a second look at a bad result
  for the packs that already measured — their labels, floor and evaluator are
  identical and any change in their numbers comes only from the BAC trials
  entering the denominator. A separate directory keeps both measurements
  auditable side by side.
alternatives:
  - option: Edit the first generation's reports in place after the repairs
    why_not: Destroys the record of the first measurement and violates the rule that a Q1 report is never edited after it is written.
  - option: Wait for fresh held-out labels before any further measurement
    why_not: The empty cells were caused by the kernel, not by label exhaustion; fresh labels are the remedy for failed pack families, not for an unbound SIC or a refused filing.
  - option: Re-run only PK04/PK11/PK12 and the BAC accessions
    why_not: A partial generation would mix two evaluator runs in one aggregate; the A34 ledger and INDEX need one coherent twelve-pack generation.
evidence:
  - "reports/q1_held_out_20261031/INDEX.md: PK04/PK11/PK12 zero emissions with sic_source unbound; 30 exclusions package_admission_refused:primary_unparseable for 0000070858-23-000092 across PK01/06/07/08/09/11"
  - "Staged witnesses carry no sic key (keys: acceptanceDateTime, accessionNumber, filingDate, form, primaryDocument, reportDate, source_path, source_url); held_out_contract.json carries sic + sic_source for all five issuers"
  - "FIF_Q0_QUALITY_PROTOCOL.md §10 (failed-family disposition) and §11 (vocabulary)"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - research/financial_intelligence_fabric/reports/q1_held_out_20261031_g2/
  - tests/test_fundamental_forensics_q1_held_out_g2_reports.py
confidence: high
reversibility: easy
decided_by: "FIF Meta-CEO seat 96dc937a (Fable)"
decided_at: 2026-10-31
---

Second Q1 generation: same labels, same floor, unchanged evaluator, new directory, after the two kernel repairs; generation-one failed families keep their disposition.
