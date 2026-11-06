# WP02 kernel corrective implementation v2

**The principal corrected the independently reproduced cutoff-precision defect. The updated author suite passes 117 tests, and both ordinary CLI examples remain byte-identical to v1. Independent corrective review and native integration remain separate gates.**

This package is a new author version of the existing structural research kernel. Its intended canonical module/helper directory remains `research/theme_graph/economic_network_execution_20261009/continuation_pro_004/source_diagnostic_kernel_v1/`: the public API and JSON schema are still v1. The canonical test path remains `tests/test_gmi_source_diagnostic_kernel.py`. A principal source map will distinguish authored version from runtime namespace. The original 16-file author v1 package remains byte-exact.

## Independently observed defect and ruling

The original `_instant` accepted timestamp strings using Python's datetime parser without a declared precision check. The independent reviewer demonstrated the defect through four actual `diagnose` calls on exact policy/adoption bytes, not a private-helper-only assertion. An anchor one microsecond after K was correctly held. An anchor 100 nanoseconds after K was silently truncated to K and incorrectly permitted all 120 artificial selections. For a same-fact correction, the corresponding one-microsecond case retained the 1.9 billion modeled cap, while the 100-nanosecond case wrongly replaced it with 2.1 billion.

The principal accepted this as a P2 temporal correctness defect and held the original implementation. The independent request/result bytes and `CUTOFF_PRECISION_EXECUTION.json` remain in `source_diagnostic_kernel_review_v1`; the receipt SHA-256 is `c6a1b192d7f5ad92349bbf522f668fa1ed617799008fdd9d9ab9fc8ce0b94ba0`. The actual original module is `80b12ec299e861d24c0c23f88805a475f44099af894fbea7d787296c72681d8f`. Neither the defect nor its repair grants any real source authority: the affected outputs were artificial models and all real authority flags remained held.

## Exact correction

The common timestamp parser now requires the complete ASCII shape `YYYY-MM-DDTHH:MM:SS[.fraction]Z`. Optional fractions must have one through six digits. More digits return `UTC_TIMESTAMP_PRECISION_UNSUPPORTED` **before** datetime conversion, including additional zero digits. This deliberately refuses representational precision the implementation cannot preserve. No supplied timestamp is rounded, truncated or normalized to make it usable.

Other shapes return the existing `EXPLICIT_UTC_BOUND_REQUIRED` refusal. Calendar and clock validity still pass through the datetime constructor. Week/basic dates, comma fractions, missing seconds, numeric offsets, non-ASCII digits and trailing text cannot expand the accepted language. This is an explicit input representation bound, not an eligibility filter or an assertion that finer-precision source evidence is false. A later owner can implement an exact finer-precision contract in a reviewed increment; this kernel does not improvise one.

The common parser is used for history anchors, membership events, shares/prices/FX assertions, correction relations and corporate actions. No arithmetic, pool, quota, source-admission, policy or adoption logic changed. The two exact normative input files retain their original SHA-256 bindings and the sole accepted numeric-rule override.

## Actual validation

| Execution | Result | What it establishes |
|---|---|---|
| Updated standard-library suite | 117 passed in 12.684 seconds; wrapper exit 0, child PID 4 | The original 90 author cases plus 27 public-API temporal regressions |
| Artificial standalone CLI | Expected NOT_READY exit 2, empty stderr; 652,327 output bytes | Complete 120-selection artificial result, byte-identical to the frozen v1 ordinary example |
| Real-mode forged-claims CLI | Expected NOT_READY exit 2, empty stderr; 8,662 output bytes | Null synthetic/real fields and unchanged unconditional real-source holds |
| Source preservation | All original 16 v1 files verified unchanged; v2 source unchanged through execution | Explicit old/new source custody within scratch |

The 27 new tests include exact K, just before K, one microsecond after K and unsupported 100-nanosecond precision; malformed/unsupported UTC representations; all six other public timestamp consumer positions; and the 1.9/2.1 billion correction boundary. The expected outcomes distinguish a supported post-K exclusion from an explicit unsupported-precision hold. A positive control at supported K is executed before each affected consumer's rejection, so an unrelated invalid fixture cannot masquerade as proof of the repair.

The normal CLI outputs have SHA-256 `e379fb2440b1c15bc7c6d9601b71c85ffaa0941d4ac72cc96b57e559d166b373` and `22ec54c7985e278954afddc666156924774167adb6dc8596b982150d1ac1494a`, respectively. Exact commands, child completion states, byte counts and before/after source hashes are retained in the execution receipts. The unit-test receipt SHA-256 is `c6d65dd3daeeec8c6977c9ee75fa8401207e71899a11f3542229ae0bd0a72e45`; the CLI receipt is `df0f9fb5f19378cd18acc98339ce5f9ec7e97bb85fe2194712f615aef7286b66`.

These are principal-authored scratch Linux executions, not independent corrective review or native Mastermind evidence. The original independent reviewer owns the subsequent exact failing-request replay and delta assessment. The original 41 wire controls, 18-flow Hall witness and v1 review remain separate historical evidence; this author return does not relabel them as corrected-source results.

## Integration and remaining obligations

The code remains `STRUCTURAL_ONLY`, `NOT_READY` and `NOT_ADMITTED`. Real population, pool denominators, capitalization, quantiles, cohort and F stay null. Source authority, historical coverage and entitlement remain separately unverified. The full implementation boundary and other deferred financial semantics remain those in the v1 implementation return and the corrected input contract.

The principal authored this correction because the available review and CI slots were occupied; the attempted builder followup did not start. There is one corrective author and one separate reviewer. No native source, Git ref, CI enrollment, provider API, source registry, acquisition job or real financial store was changed by this package's creation or execution. Test-created temporary files were confined to the assigned scratch directory and managed by the existing test harness.

Before runtime promotion: finish independent v1 findings, independently verify this exact v2 delta and failed inputs, preserve both versions and their reviews, map the corrected source into the canonical research kernel/test paths, complete native pytest and CI ownership verification, and release through normal exact-source CI. A passing artificial model still does not admit a historical frame or authorize predictions.
