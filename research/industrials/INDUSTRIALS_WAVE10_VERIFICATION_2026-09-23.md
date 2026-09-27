# Industrials Wave 10 — Verification and limitations

23 September 2026. Operation `gmi-industrials-sector-research-20260923-sol-001`. Macro Draft/HOLD PR #7789. Principal research and proposed design only. Final Fable handoff remains withheld.

## Executed checks

`python verify_wave10.py` completed before and after immutable GitHub readback: **34 passed, 0 failed**, exit 0. These are 24 selected financial-arithmetic checks and 10 document/reference checks. The same script was also executed in a temporary canonical repository layout, with the specification under `docs/superpowers/specs/` rather than the flat portable directory; all 34 checks passed there too. Those repeated runs overlap and are not added as independent coverage.

`python verify_wave10.py --native-schema <exact-local-schema>` completed before and after readback: **37 passed, 0 failed**, exit 0. The additional three checks use the actual GMI JSON Schema, whose local bytes match native blob `83dece15e98b9c8775a584afcd6ee09811dad220`. A hermetic baseline receipt shape passes; adding `curation_assertion` fails the closed schema; omitting its required publication day fails. The synthetic receipt is never written or admitted. This is actual local schema behavior, not native store round-trip, runtime admission, API or production proof.

The financial arithmetic covers paired compensation/other-income invariance, net versus gross revenue, six-month operating cash, cash after capital payments, working-capital contributions, the cash-balance roll-forward, segment/corporate reconciliation and preliminary-to-final arithmetic. Decimal and exact Fraction expressions are used. The values are manually selected public-source examples, not a licensed dataset or complete independent source audit.

Ten separate author self-review assertions passed for outcome, alternatives, native ownership, closed-content meaning, paired adjustments, time/corrections, private exposure and real-path proof. These are not an independent design review. The thirty IND-D requirements are proposed application cases, not thirty executed product tests.

No numerical assertion failure, expected-value correction or loosened tolerance occurred. Self-review added explicit source-date/midnight qualification and made document lookup support both canonical and archive layouts before publication. No product dependencies or native code were changed.

## Immutable file identities

Containing source/spec commit: `5d8ee4ded6178c5ac63dc131c5f95fed3a0d46ff`. The qualification note was first read at `ca4234d9a179193eff70731fb66b36fa3b805ec0`; the specification and verifier were read at the containing commit. Exact local Git blobs matched all readbacks:

| File | UTF-8 bytes | Git blob |
|---|---:|---|
| `research/industrials/INDUSTRIALS_WAVE10_INTERFACE_QUALIFICATION_2026-09-23.md` | 12,406 | `f980c9d7be051e4d12ef099b7352fde5ed4d9ab8` |
| `docs/superpowers/specs/2026-09-23-industrials-result-cash-dossier-design.md` | 28,638 | `40fd1e3783102c28fe748fe35b927484d4f3dddb` |
| `research/industrials/verify_wave10.py` | 8,249 | `70d49c1c5fa0f6b5aeb879bcb7baf57eb8b278e8` |

The specification contains 3,899 whitespace-delimited words and thirty proposed requirements. The 1,507-word qualification note covers twelve same-pin native code/contract paths and four primary sources. Counts describe the artifacts, not completeness, adoption or investment advantage. JSON verification outputs and self-review are derived portable receipts, not a second canonical evidence store.

## What remains unproved

No selected Exponent/Pentair object has been qualified as an admitted private native generation, a fully resolved company/security composition, or a served authenticated dossier. Existing code confirms reusable mechanisms, not present deployment health or case coverage. Current rights/source retention, native event and identity receipts, precise source clocks and the approved new private content role remain dependencies.

The inspected transcript context and public Company Intelligence paths are not compatible shortcuts for new private release/filing content. The GMI body extension and K1 cross-subject bridge remain explicit owner concerns, not implicitly working capabilities. No live record, source schema, renderer, signal, ranking, basket, trading policy, worker, Executive Attempt, watcher, merge or deployment was changed.

The standard-reader cross-check of Wave 9's recovered historical Parquet file remains outstanding. Local standard readers were unavailable; one pyarrow installation attempt failed at DNS. No decoder or alternate feed was created and no repeated installation loop was run. The raw historical snapshot was not recovered again. This failure did not block the independent case/specification work.

The Exponent filing's signature is not a verified acceptance timestamp. Management preliminaries are not external consensus, refunds lack a verified segment allocation, and source-specific cash formulas do not imply universal free-cash definitions. All research comparisons remain retrospective. No current fair value, calibrated financial prediction, held-out return result or independent factual-review receipt is claimed.

Portable packaging must exclude `private_inputs/`, native schema bytes, raw reports, the historical snapshot, complete feeds and credentials. Archive integrity and member hashes are verified after packaging. A user-visible Markdown attachment is not a production UI or browser acceptance receipt.
