---
key: CHINA-ECONOMY-RECEIPT-BOUND-SOURCE-INTEGRATION
claim: >
  The China economy candidate can traverse the existing ChinaMacroAdapter and
  run_adapter into the owned local parquet store, then the existing China
  builder into both China pages. This is local integration proof, not live
  production acceptance. Source values must match their per-column receipt;
  dataframe column-wise merges must not lend old metadata to changed values.
falsifier: >
  Run python3 -m pytest -q tests/test_china_economy_acquisition.py
  tests/test_china_economy_parser.py tests/test_china_economy_store.py:
  an altered value admitted under an old receipt, a mixed seasonal revision,
  or a missing source silently populated from review data refutes the contract.
  A failed real build or JSON/UI mismatch refutes the corresponding integration
  claim; browser and production claims are explicitly not made.
so_what: >
  Continue issue #8185 in the same owned source lane. Preserve the original
  four dialogs and the 128-series catalog, but do not report all catalog series
  as acquired. The current source-detail qualification admits 84 series but
  still covers only two of six growth-domain directions; withhold the overall
  direction. Keep legacy monthly FAI amounts separate from official comparable
  cumulative growth, even when both observations refer to the same month.
kind: landmine
verified_at: 2026-09-30
verified_by: >
  Sol attended integration: python3 -m scripts.build_china completed with
  RENDER_NO_DRIP=1 and CHINA_VM_DUMP=1; installed ChinaMacroAdapter qualified
  through collectors.base.run_adapter; source-final.xml records 358 passed
  with zero failures/errors/skips. Evidence manifest and exact
  local receipt paths are in research/CHINA_ECONOMY_SOURCE_INTEGRATION_20260929.md.
  Machine/client chart-value, unit and definition parity was checked on the
  actual builder output, not the separately transcribed research preview.
  The subsequent focused suite records 482 passed in focused-final-v2.xml;
  read research/CHINA_ECONOMY_DETAIL_AND_FAI_BASIS_20260929.md and its r3
  source/ingestion/build receipts for the new 31 readings and same-owner FAI
  correction. Original evidence hashes are not rewritten.
scope: [macro, collectors/china_macro.py, collectors/china_economy_adapter.py, engine/china_economy_store.py, scripts/build_china.py]
confidence: verified
---

The source-access denial from the prior turn was resolved by an observed
allowlist change and a successful read of the exact existing worktree. The
worktree was not recreated, relocated, reset or accessed through another carrier.
Its five earlier changed/untracked files were backed up and reconciled by exact
preimage hashes before the source package was applied once and read back.

A separate browser administrator refusal remains unresolved. Collector success,
static HTML parsing, a passing focused test suite and a GitHub PR do not prove
browser behavior, authentication, installed production identity or acceptance.

The raw-source acquisition configuration remains disabled in the shipped example.
Qualification used an instance-local configuration, not a production enrollment.
The observed FAI discrepancy is resolved at the new evidence binding: the
legacy BASE_SAME matches single-month amount arithmetic, not comparable YTD
growth. The NBS value occupies a separate column in the same table and both
new views share its receipt admission. Every original legacy date/value and
index name is preserved; no strategy computation was changed. Export basis,
fiscal acquisition, wider histories and commercial redistribution review remain open.

The original browser refusal and an additional unclear OpenAI refusal of a
compound UI/CI/palette/browser-source read remain action-scoped gates. Neither
was retried through another route. No visual, authenticated gateway or release
acceptance follows from this independent data-unit completion.
