---
key: FIF-PARSER-NIL-FACT-INERT-ATTRIBUTES-TOLERATED
question: >
  When an EDGAR-accepted Inline XBRL document carries decimals, precision, scale,
  format or sign on a numeric fact that is xsi:nil="true", does the shared SEC
  filing parser refuse the whole document or tolerate the attributes?
answer: >
  Tolerate, visibly, as a strict widening. A nil fact has no value, so those
  attributes are inert: the parser drops them at parse time (the recorded fact
  keeps nil=true and carries no accuracy or transform) and appends one per-fact
  diagnostic {code: nil_fact_inert_attributes_dropped, fact_start, attributes}
  only on the path that used to raise. No always-written counter is added, so
  every previously accepted input stays byte-identical, the 14 accepted-corpus
  pins do not move and the parser fingerprint is unchanged
  (DEC:FIF-PARSER-FINGERPRINT-BINDS-ACCEPTED-OUTPUT). The source-free validator
  admits that diagnostic only when it points at a recorded nil numeric fact and
  keeps asserting the record invariant. Structural refusals are unchanged: a
  native (non-Inline) fact carrying Inline-only attributes still fails before
  the nil tolerance, non-nil numeric facts still need decimals or precision, and
  non-numeric facts still may not carry numeric attributes. The first build lane
  (fif-bacnil-20261031-r1) proved that always-written coverage counters move all
  14 pins; that surface is rejected.
rationale: >
  The Bank of America FY2022 10-K (accession 0000070858-23-000092) was refused
  whole with "nil fact cannot carry accuracy, transform, sign, or scale", which
  excluded 30 held-out trials across six packs from the first Q1 generation
  (research/financial_intelligence_fabric/reports/q1_held_out_20261031/). The
  refusal protected nothing: no number can be changed by an attribute on a fact
  with no value. EDGAR accepted the filing; a kernel stricter than EDGAR on an
  inert attribute measures the parser, not the issuer. Counting the deviation
  keeps the tolerance auditable per document.
alternatives:
  - option: Keep the fail-closed refusal and exclude such filings from every pack
    why_not: Excludes real issuers for a non-semantic attribute; the held-out denominator loses whole filings and the product cannot serve them.
  - option: Tolerate only decimals/precision and keep refusing scale/format/sign on nil facts
    why_not: Equally inert on a nil value; a partial tolerance would still refuse EDGAR-accepted documents for no semantic gain and would need a second ruling later.
  - option: Repair the filing bytes before parsing
    why_not: Rewriting source bytes breaks the byte-faithful provenance the parser fingerprint binds (DEC:FIF-PARSER-FINGERPRINT-BINDS-ACCEPTED-OUTPUT).
evidence:
  - "Q1 run q1_held_out_20261031: PK01/PK06/PK07/PK08/PK09/PK11 trials for 0000070858-23-000092 excluded as package_admission_refused:primary_unparseable (INDEX.md rows); engine/fundamental_forensics/admitted_filing_package.py:518 maps SecFilingParseError to primary_unparseable"
  - "collectors/sec_filing_parser.py::_fact_accuracy raised on nil + any of decimals/precision/sign/scale/format (line ~1286 at main 594a7429)"
  - "Build lane fif-bacnil-20261031-r1 (ubuntu0, base 594a7429): diagnosis on the real document — 17 nil ix:nonFraction facts, 10 carry scale only, 7 carry none; coverage-counter surface moved all 14 _BYTE_IDENTITY_PINS → BLOCKED, surface redesigned to per-fact diagnostics in lane fif-bacnil2-20261031-r1; independent fabric review follows before merge"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - collectors/sec_filing_parser.py
  - tests/test_sec_filing_parser.py
  - engine/fundamental_forensics/admitted_filing_package.py
confidence: high
reversibility: easy
decided_by: FIF Meta-CEO seat 96dc937a (Fable)
decided_at: 2026-10-31
---

The evaluator re-run that measures the effect is a new Q1 generation under a new
reports directory; the first generation's reports are never edited.
