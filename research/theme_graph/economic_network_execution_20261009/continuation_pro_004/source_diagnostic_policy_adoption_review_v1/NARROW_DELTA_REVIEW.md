# Independent narrow adoption-sidecar review

**Verdict: PASS — R3 is resolved in the composite contract consisting of frozen v2 plus the exact principal sidecar.** No remaining P1 or P2 was found within this narrow delta. The frozen v2-only review and its then-open R3 finding remain unchanged; this later review closes that finding only for the bound composite.

## Exact objects reviewed

All five sidecar files were read; they total 19,510 bytes. Every manifest member and referenced policy/review binding matched its actual bytes.

| Object | Bytes | SHA-256 |
|---|---:|---|
| Base v2 policy | 60,312 | `d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522` |
| `POLICY_ADOPTION.json` | 9,593 | `645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016` |
| `PRINCIPAL_ADOPTION.md` | 7,155 | `1c2d9c72ad7ea969a5b41294845bb55d4fcb0158802b74e5ccff815e36264783` |
| Sidecar `MANIFEST.json` | 1,091 | `82839b3edfb68baf03ebbc8e435d9c9b63dd7bea50e0c8eb3b17bd52e9194e7e` |

The two remaining sidecar members are `ADOPTION_VALIDATION.json` and `NUMERIC_CLARIFICATION_CONTROL.json`; both were read and checked. The five-file inventory includes the manifest itself. Complete bindings are in `DELTA_CHECK.json`.

## Single normative delta

The sidecar has exactly one override: `/capitalization/numeric_rule`. Its `expected_original` matches the original v2 string exactly. Applying that replacement to an in-memory copy produces exactly one changed JSON pointer; all other policy values are equal. The base file was not changed.

The replacement separates the domains that conflicted in R3:

- Actual positive-class share-count measurements, raw prices, quote-unit scales, FX rates and multiplicative split/conversion/ADR factors must be strictly positive.
- Additive corporate-action share deltas may be negative, zero or positive. Their signs, class/share units, economic event identity, effective ordering and dependencies remain required.
- Zero delta requires an explicitly evidenced no-change assertion. It cannot fill a missing value. Supported zero/ceased-class assertions remain separately typed and cannot disappear into a partial cap sum.
- Resulting included-class shares and final issuer cap remain strictly positive. The signed-delta exception cannot admit a nonpositive price, rate or multiplicative factor.
- Cardinalities are nonnegative integers excluding booleans. Nonfinite values, booleans and binary floating-point inputs are invalid. Decimal strings are converted to exact rationals; absolute values, clipping, imputation, partial-class omission and display rounding cannot make invalid inputs pass.

These clauses resolve the reviewed numeric-domain ambiguity without changing the cap construct. A future parser must still implement and test them; this source review does not claim a parser already exists or that its runtime rejection behavior passed.

## Adoption and unchanged law

All three adopted meanings match their exact v2 `proposed` meanings: A01 relative count-band semantics with compulsory absolute tags, A02 company-primary activity/instrument perimeter, and A03 reported-share reference cap and D/K/F rules. The sidecar identifies the current commissioned principal's bounded research implementation decision. It explicitly leaves commissioning Sol CEO architectural adjudication `NOT_ASSERTED`.

The 120-issuer total, five strata of 24, six groups of 4, 2L/1M/1S, INT 8 UK/8 JP/8 EU, 42 reference pools, 30 difficult cases with 6 per stratum, D=2026-09-30, K=2026-10-09T00:00:00Z and seed `GMI-WP02-20261009-v1` remain equal to v2. F remains null pending the actual later freeze. The single-pointer comparison also verifies that the existing age limits, relative ties, absolute boundaries, source periods, replacement law and all other policy values were unchanged.

The sidecar governs this later bounded adoption. It does not rewrite the original recommendation's historical pending metadata or pre-approve a later source/runtime release. Implementers must bind both raw input objects, verify the expected original clause, and apply only the declared override. Arbitrary input-provided policies or override receipts cannot replace that binding.

## First-kernel boundary is preserved

The first scope is a `STRUCTURAL_ONLY` research kernel with explicit supplied-record diagnostics and synthetic 42-pool/120-slot checks. It has no selected real-source admission adapter. Real-source authority remains `SOURCE_AUTHORITY_UNVERIFIED`, rights remain `SOURCE_RIGHTS_UNVERIFIED`, and history remains `FRAME_HISTORY_UNPROVEN`. Real resolved cap, quantiles and selected cohort are null. Supplied-row counts cannot be relabelled as eligible-population counts.

The JSON and prose both make the hold unconditional. A caller-supplied boolean, owner name, path, hash, callback or synthetic label cannot authenticate source truth or enable real-source selection. Synthetic difficult cases cannot satisfy the real study's 30-case requirement. Unknown rights are unverified; they are not a proved absence of a license. All admission/production/graph/prediction/rank/size/trade/export/training authorities remain false or `NOT_ADMITTED`.

The external prerequisite remains an existing trusted owner-review/admission reader with actual provenance and applicability to exact source/derived evidence, D/K, coverage, derivation and permitted use. Even a later verified reader will not establish a complete lawful historical 42-pool frame by itself. No such reader, receipt, entitlement, identity or frame was invented or verified here. Parent-supplied native/procedure/source revisions in the sidecar remain attributed context; this lane did not independently inspect the current native estate.

## Observed narrow verification

One standard-library-only command completed with observed exit 0 and empty stderr:

```text
PYTHONDONTWRITEBYTECODE=1 python -B lanes/source_diagnostic_policy_adoption_review_v1/DELTA_CHECK.py > lanes/source_diagnostic_policy_adoption_review_v1/DELTA_CHECK.json 2> lanes/source_diagnostic_policy_adoption_review_v1/DELTA_CHECK.stderr
```

The check verified all exact bindings, unique parsed JSON keys, the single override, all three adopted meanings, unchanged parameters and unconditional real-source holds. Exact arithmetic reproduced 1.8b for the negative retirement, 2.2b for the incorrect absolute delta, and 2.0b for a zero delta. The zero calculation proves an arithmetic identity, not source evidence of no change.

For reproducibility, the in-memory base and effective objects were encoded as UTF-8 JSON with `ensure_ascii=False`, `sort_keys=True`, `separators=(',', ':')`, `allow_nan=False`, and no final newline:

| Canonical content | Bytes | SHA-256 |
|---|---:|---|
| Base policy | 52,590 | `6349f2b2c9f8d9257d3853d4906bdfcc9dd6fe706cf053e957f9a4098c133266` |
| Effective policy | 53,677 | `90bec6078348af6e41c9538e12e0443dd37d671c85a7089c64c547f5ce5e7714` |

These computed digests identify canonical policy content. They are not original-file byte hashes, source/owner authentication, adoption signatures or admission receipts. The exact raw-file bindings above remain required.

No 729-matrix rerun, issuer census, external source acquisition, application/native/store/Git operation or provider execution occurred. No actual parser, selector, owner trust interface, real source rights or history was tested. All reviewed source files and earlier reviews remain unchanged. New artifacts are confined to `lanes/source_diagnostic_policy_adoption_review_v1/`.

STOP.
