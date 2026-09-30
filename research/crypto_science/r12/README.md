# R12 host integration and physical storage evidence

Parent: WS:CRYPTO-INTELLIGENCE / operation crypto-vector-r2-20260926-sol-001 / Macro draft8050. Initial source commit372cdf9f443a9b53e32df01feef718a00d07783f. Original reviewed source baseline6fff72caec8c6cf044c1be40015a580223f9d528.

The formerly sandbox-only boolean-reference-price patch now exists in the actual repository with host regression/compatibility proof. Retention envelope implementation is NOT complete. No live collector, model-policy or release acceptance is claimed.

## Evidence

- red_price_host.txt: host reproduction before patch, one failure and one numeric control passing.
- green_price_host.txt:52collector/CVDtests pass after the exact prepared patch.
- verification_final.txt:431tests pass,49warnings, compilation/source-claim/difference checks pass after61additional host compatibility cases.
- reference_cvd_before_price_guard.py.txt: immutable original engine bytes, noncollecting snapshot, SHA25612117869d18239cdffd4d70b0c6906ba8a51bf140894c860e07321db2a8420a9.
- pipeline_proof.json/pipeline_host_log.txt: unchanged R11 verifier loaded with output redirected to THIS directory. Prior proof not overwritten. Actual source runtime matches current patch; later test-only append is separately covered by full suite.
- parquet_probe.py/parquet_baseline.json:0/100/1000synthetic retained captures on physical PyArrow Parquet, temporary files only. One append and duplicate per size, no percentile, cold-cache or production-capacity claim.
- verify_receipts.py: read-only identity/compatibility/arithmetic checks; does not run providers or rewrite historical scientific experiments.

```bash
python3 research/crypto_science/r12/verify_receipts.py
```

The Parquet generator refuses to overwrite saved measurements. Do not replay it merely because a chat disconnects. Times describe the observed host/runtime and workload, not a SLA. Source/data/gate hashes and deterministic account shapes are stronger reproducibility claims than exact wall-time reproduction.

All57recorded inputs,18gates and137prior research artifacts remain unchanged. The collector/capture/store runtime modules are unchanged; production change in this batch is the narrow CVD price guard. Expanded tests remain in the enrolled CVD suite; the prior source is .py.txt so it cannot become an accidentally collecting new suite.

Open release questions: explicit capacity envelope and admitted operational limits, independent review bound to the eventual source, current exact-headCI and real prospective capture. The later retention-plan append was refused before dispatch and not retried; no retention code/configuration effect occurred. Keep prior runtime/typed-publication refusals action-scoped and do not bypass them. Full findings are in research/CRYPTO_SCIENCE_R12_RELEASE_HARDENING_RESULTS.md.
