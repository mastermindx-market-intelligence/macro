# Preserved intermediate integration repair evidence

This directory preserves the exact intermediate contract SHA-256 `d633f0baeb8d506053387c15f5712ebd49c4b6b9b392a43e8e143e3c3226ee4f`, its independent checks, and the subsequent normal-path timestamp precision counterexample. It is development evidence and is **not the final accepted candidate**.

The intermediate independent core run passed 59 checks. The corresponding native Parquet run passed four writes and four pre-write refusals; all 11 retained Parquet files remain here. These results remain valid for their tested scenarios. They did not yet cover a fractional evaluation instant.

`precision_regression.py` subsequently supplied `2026-10-12T02:00:00.250000+00:00` through the native evaluator. The unchanged emitted events and envelope truncated that instant to seconds. The source receipt retained microseconds, so normal ingestion refused with `future_quote_source_receipt`. No event or envelope timestamp was altered by the probe. `PRECISION_EVIDENCE.json` retains the exact envelope, clocks, source identities and typed refusal. Quotes and their source/basis contract are explicitly synthetic. This proves a reachable offline code path, not a natural production occurrence.

The final candidate `3518cc9f408534cccbe60419b8de8d7143ad42f406c7d9ee262068ef1c5fe2e0` preserves the supplied evaluation instant and is reviewed in the parent directory. Its positive +250 ms and negative 50 ms backdate cases distinguish precision preservation from weakened source-availability checks.

## Reproducibility

From the original repository layout:

```bash
python -B deliverable/research/cn_prophet_audit/census_20261009/deepening_20261009/reviews/integration_repair_review/development/d633f0ba/precision_regression.py
```

The precision probe uses the exact local intermediate contract, the fixed parent `review_support.py`, the original independently retained native source bundle, and the original lab fixture. Those dependencies are bound by this directory's manifest. It writes its evidence beside itself; use a disposable copy of the relative study tree to preserve the seal during replay.

The other copied scripts are preserved exactly as executed before relocation. In particular, copied `accept_repair.py` retains its original root-layout assumptions. Its archived result and input identities are inspectable, but direct invocation from this relocated directory is not claimed to be standalone replay. The native helper takes explicit input/output paths; its exact original command and exit-zero receipt are retained in `HOST_EXECUTION_RECEIPT.json`.

No original lab, original review or final producer file was modified to preserve this snapshot. The exact intermediate contract was recovered read-only from the review's earlier isolated host copy after the producer advanced to the final candidate.
