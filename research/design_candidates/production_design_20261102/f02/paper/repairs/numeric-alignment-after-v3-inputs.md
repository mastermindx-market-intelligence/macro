# Numeric alignment after v3 — planned precondition rebase

**Prepared only; no live validation or native effect.** This patch is intended after the final cumulative v3 text, chart and Energy-order corrections. It preserves the original numeric-frame style operation and changes only the expected visible Text guards explicitly targeted by the prerequisite candidate.

## Exact inputs

- Original patch: `numeric-alignment-native-patch.json`; SHA-256 `1a597788640380f0bf439c768c33b4a62381c565d80413e1ee89affe6b1836f3`.
- Final cumulative candidate: `observation-identity-clocks-v1/native-patch-candidates.cumulative.v2.json`; SHA-256 `dc3fd2f6b09d8867848f8e6e4b48f347f39837abd79003585e9b9f8b71bcd2c8`.
- Prepared output: [numeric-alignment-after-v3-inputs.json](numeric-alignment-after-v3-inputs.json); SHA-256 `77a0a202fe4c1d37e7771224554d99779be9adc6e79d46f82e1ba92298d4efd8`.
- [Validation record](numeric-alignment-after-v3-inputs.validation.json); SHA-256 `0a0d438e620dc9e82df3a4af68c7e4180f35c4e74e3307dba04d6a798b7f9d8e`.

## Included scope

| Board pair | Frames per theme | Included |
| --- | ---: | --- |
| Macro dark / light | 33 | Three numeric headers and 30 body frames per theme |
| Options dark / light | 52 | Four numeric headers and 48 body frames per theme |
| Company dark / light | 6 | Numeric headers only |

Total: **182 frames: 26 headers and 156 body frames**, across 50 source steps. All **108 Company body frames are excluded** from both bindings and executable batches; their separate row replacements own their alignment.

Twenty Macro text guards change: each theme's active sort header and nine coverage cells, including Energy `0 / 82`. The other 162 guards remain unchanged. Options bindings and Company header bindings remain identical as parsed objects. Every retained frame ID, row/column role, width, current-style guard and desired style payload is preserved exactly. No row-position inference is used.

## Safe sequencing

Reconcile the prerequisite cumulative candidate against the sole writer's actual operation ledger first. Fresh-read the exact retained frame and Text node before alignment; the planned guard is not evidence that a prior text update has applied. Verify identity, expected text, width and style state. Any mismatch remains a reconciliation task; do not silently change the target or widen the style repair. If a frame already has the desired alignment, record it satisfied instead of replaying an old operation.

The original patch's source/export hashes and current-style fields remain historical provenance. This preparation does not refresh them into live observations. Company body replacement IDs, chart replacement IDs and all Paper effects remain with the sole writer.

Validation found **zero source-binding mismatches**. This is an authoring/precondition check, not rendered proof, an independent product/taste review or formal RIG approval.
