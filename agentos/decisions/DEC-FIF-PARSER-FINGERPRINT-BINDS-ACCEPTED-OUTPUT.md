---
key: FIF-PARSER-FINGERPRINT-BINDS-ACCEPTED-OUTPUT
question: >
  When the SEC filing parser (collectors/sec_filing_parser.py) widens what it
  accepts — a new href shape, a raised resource cap — must VERSION or
  SEC_FILING_PARSER_ALGORITHM_FINGERPRINT bump?
answer: >
  The fingerprint is the compatibility authority for ACCEPTED OUTPUT only. A
  change that strictly widens the acceptance set while every previously
  accepted input produces byte-identical output — proved over the full
  retained corpus plus the AAPL golden — is compatible and does NOT bump. Any
  change that alters the output bytes of any previously accepted input DOES
  bump, and needs its own seat ruling because it moves pins. Refusal verdicts
  are not fingerprint-bound; they are bound by the committed G-SRC
  `_VERDICT_PIN` (tests/test_fif_gsrc_capture.py), regenerated in the same PR
  only through the readmit path over staged bytes.
rationale: >
  Downstream identities (ffxbrl ids, golden hashes, admitted package
  manifests) are derived from parser OUTPUT. A bump invalidates every
  downstream pin even when no accepted byte changed, which would force a
  golden re-capture for a pure widening. Binding the fingerprint to accepted
  output keeps widening cheap and keeps output drift impossible to hide,
  because the byte-identity census is the proof obligation.
alternatives:
  - option: Bump the fingerprint on every parser change.
    why_not: Moves AAPL golden and ffxbrl pins for changes that alter no accepted byte; forces re-capture with no information gain.
  - option: Never bump; rely on tests.
    why_not: An output-changing edit would silently change identities that downstream stores treat as content addresses.
evidence:
  - "Seat ruling D1X-3 (2026-10-13 ~00:5xZ) for the D1-ext C (fragment-only href) and B'2 (BAC cap co-raise) PRs."
  - "#9042 (squash 9f43a86ef48c): max_nodes 100k->200k with VERSION and fingerprint unchanged; admitted G-SRC primaries 6/16 -> 10/16; independent opus review PASS at b614cc43."
  - "D1-ext C census (ORCH-B2): 132/132 previously accepted primaries byte-identical, 0 mismatched, 0 lost; the 3 CAT 10-Qs extract at current caps."
  - "collectors/sec_filing_parser.py:28 carries the compatibility-authority comment; the D1-ext C PR rewords it to state this rule."
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - collectors/sec_filing_parser.py
  - tests/test_sec_filing_parser.py
  - tests/test_fif_gsrc_capture.py
confidence: high
reversibility: easy
decided_by: "seat 96dc937a (FIF Meta-CEO, Chairman commission 2026-10-11)"
decided_at: 2026-10-13
---

# The parser fingerprint binds accepted output, not the acceptance set

Proof required for a non-bumping widening:
- full-corpus byte identity for every previously accepted input;
- AAPL golden untouched;
- every newly accepted primary passes its oracle and validator replay;
- negative tests for each shape still refused;
- `_VERDICT_PIN` regenerated with `mkpin`-style tooling from the readmitted table, never by hand.

STOP conditions:
- any byte change on a previously accepted input;
- any AAPL, golden or ffxbrl id move;
- any VERSION or fingerprint edit without a separate ruling.
