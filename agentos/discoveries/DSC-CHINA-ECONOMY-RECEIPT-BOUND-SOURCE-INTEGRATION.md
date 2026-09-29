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
  tests/test_china_economy_adapter.py tests/test_china_economy_store.py:
  an altered value admitted under an old receipt, a mixed seasonal revision,
  or a missing source silently populated from review data refutes the contract.
  A failed real build or JSON/UI mismatch refutes the corresponding integration
  claim; browser and production claims are explicitly not made.
so_what: >
  Continue issue #8185 in the same owned source lane. Preserve the original
  four dialogs and the 128-series catalog, but do not report all catalog series
  as acquired. A successful local collector with 53 admitted series covers
  only two of six growth domains; the overall direction must remain withheld.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Sol attended integration: python3 -m scripts.build_china completed with
  RENDER_NO_DRIP=1 and CHINA_VM_DUMP=1; installed ChinaMacroAdapter qualified
  through collectors.base.run_adapter; source-final.xml records 358 passed
  and one explicitly deselected baseline test. Evidence manifest and exact
  local receipt paths are in research/CHINA_ECONOMY_SOURCE_INTEGRATION_20260929.md.
  Machine/client chart-value, unit and definition parity was checked on the
  actual builder output, not the separately transcribed research preview.
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
Existing FAI/export source-basis differences, fiscal acquisition failure, wider
catalog acquisition and commercial redistribution review remain open.
