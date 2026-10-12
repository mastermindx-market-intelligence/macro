# R11 existing-collector source repair and evidence

Parent: WS:CRYPTO-INTELLIGENCE / Macro draft PR8050. Operation: crypto-vector-r2-20260926-sol-001. This package proves a source candidate on a controlled collector/storage path. It is not a live collector, new data store engine, model promotion, alert or trading strategy.

## Implementation ordering

- Published baseline:4577adc349ef68f86f6c6200369e49b86e7c453f (R10).
- Plan: research/CRYPTO_SCIENCE_R11_COLLECTION_REPAIR_PLAN_2026-09-29.md, committed before implementation.
- Interrupted implementation recovered intact:e489b12bc0bbf7c3be37a04c23bb358d42bf0ecd.
- Recovery/reference/integrity hardening:d3368828db32a4dbb08e57f8edaa6cc28f4de192.
- Final observed-status/settlement-type source:b53636f05b6374dafabcbc9c5d8085773d88fdf0.
- Findings: research/CRYPTO_SCIENCE_R11_COLLECTION_REPAIR_RESULTS_2026-09-29.md.

## Verification

```bash
python3 research/crypto_science/r11/verify_receipts.py
```

This command only reads saved proof and exact source/data identities. It does not replay a provider fetch or write data. The pipeline producer `verify_pipeline.py` is an executable synthetic integration that uses fake HTTP and temporary stores, plus read-only arithmetic over the recorded stored snapshot. It refuses to overwrite an existing proof. Do not delete results and replay after an interruption; reconcile the existing evidence first.

The final synthetic check executes the ordinary `run_adapter()` entry and real house storage helper. It proves response revisions and reversion, exact repeated capture idempotence, as-of funding views, unchanged original numerical fields/request signatures and degraded status when evidence recording fails. Direct membership and scalar arithmetic verify54elapsed-window cases and2stored-snapshot cases. This is separate numerical expression by the same session, not independent reviewer approval.

The earlier passing pipeline before the final two type guards is retained in `pipeline_before_type_hardening.json` and its log. The same synthetic scenarios on the changed source have identical semantic results; no financial experiment was rerun or tuned. Raw test failures, a log-only whitespace-normalization receipt and the archive/reference fixes remain visible.

Final broad suite:368passed,49warnings. Collector/CVD targeted suite:50passed,43warnings. Compilation, existing source claim checker and diff checks passed. The original suite-enrollment checker exits0 with preexisting repository-wide warnings; no waiver or new CI job. The real scientific test file is unchanged. R10's archived test bytes are retained under a noncollecting .py.txt name, and the original historical CVD is pinned by hash for its legacy diagnostic.

## Evidence boundary

- `pipeline_proof.json`: exact8candidate source identities,57input identities,18gates and137prior artifacts;9capture identities,4as-of views,54elapsed cases and2stored arithmetic checks.
- `pipeline_log.txt`: successful end-to-end run.
- `verification_final.txt`: full existing regression command/output and syntax/claim checks.
- `suite_enrollment_final.txt`: current native enrollment checker output.
- `verification_receipts.txt`: saved evidence and before/after compatibility checks.
- `MANIFEST.json`: exact derived proof/report/source digests; no raw market data or fonts.

The real provider observation files are absent both before and after tests. Only temporary fixture stores were created. No paid subscription, market API, source backfill, live collection, gate, model allocation, UI, saved review, alert, trade, merge or deployment happened here. Official provider documentation was read without requesting market/account data.

The additive source preserves what the system receives from future ordinary runs. It does not reconstruct historical availability or certify units, finality, timestamp roles, settlement interval, daily completeness or predictive efficacy. Independent review, exact-head CI, release admission, retention capacity and a prospective existing-process capture proof remain before production acceptance.
