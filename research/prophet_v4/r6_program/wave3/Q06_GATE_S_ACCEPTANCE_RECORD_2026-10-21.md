# Q06 Gate S acceptance record (2026-10-21)

Companion record to `q06_sec_comparable_revenue_capture_manifest.v0_1.json` and
`q06_sec_comparable_revenue_source_contract.v0_2.json`. It records an acceptance that
already exists; it accepts nothing new and changes no contract bytes.

## The acceptance

`research/prophet_v4/earnings_semantics_v1/README.md:81-84` records that parent Sol
independently reproduced the repaired Gate S contract on Macro PR #8069 head
`ae9409bca5d81dbf7438ff0037a976b324853bdd` and accepted the factual source field only,
in #8069 comment `5894923827`:

- author `mastermidx4` (Sol), 2026-09-29T17:05:28Z
- marker `SOL_Q06_GATE_S_ACCEPTANCE_20260929`
- title "SOL ACCEPTED / CONTINUE — Gate S factual field accepted; Gate E remains closed"

Accepted scope: the factual source field only (Apple FY2026 Q3 8-K EX-99.1 comparable
quarterly GAAP revenue growth, `16.356501765281383%`).

## Pinned identities

- Contract sha256 `a0790967ad56740fe740e7026e53eda34f3c2529ca75d6dfca64d28b293a177d`,
  byte-identical in both copies:
  `research/prophet_v4/r6_program/wave3/q06_sec_comparable_revenue_source_contract.v0_2.json`
  and `tests/fixtures/prophet/q06_source_contract.v0_2.json`.
- SEC EX-99.1 fixture `tests/fixtures/company_intelligence/aapl_fy2026_q3_ex99_1.htm`,
  sha256 `070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb`.

## Why the contract still carries pending text

The contract's `.state` (`GATE_S_REPAIRED_PENDING_PARENT_ACCEPTANCE`) and
`.gate_s.state` (`REPAIRED_PENDING_PARENT_ACCEPTANCE`) are intentionally unchanged:
the source-qualified D5 consumer pins the contract SHA-256 above
(`earnings_semantics_v1/D5_CONSUMER_2026-09-30.md`), and the verifier asserts that
pending state at `verify_q06_sec_comparable_revenue_source_contract.py:100`
(`assert contract["gate_s"]["state"] == "REPAIRED_PENDING_PARENT_ACCEPTANCE"`).
A byte edit of either state field would break both pins. This record carries the
acceptance; the contract bytes stay frozen.

## Standing limits

- Gate E remains closed (`NOT_REGISTERED_PREPARATORY_ONLY`); Evaluation owns it.
- D07 register row deferred.
- No live, ranked or qualified claim.
