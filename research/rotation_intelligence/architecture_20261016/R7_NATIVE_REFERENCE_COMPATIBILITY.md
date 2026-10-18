# R7 — Native receipt-reference compatibility and truthful consumer summaries

Observed 2026-10-18 UTC; same Chairman sector-rotation assignment, Macro PR #9507 and original branch. This is a source/consumer repair, not a new strategy, collector, source authority, or evaluation service. Original source base: `aadf630c45f22232218669bb2d874e472d1f1825`.

## Reproduced defects and minimal repair

**The latest fixture suite no longer represented a valid raw-selected history.** Rows used source SHA `a…a`, but their history declared `b…b`. The newest raw-hash-only guard failed at the first XLB row, masking negative cases intended to exercise BIL, dates, price validity and other checks. The actual pinned native modules on M2 reproduced a pytest summary of `27 failed, 10 passed, 5 subtests passed`; this count includes failing subtests, not 27 distinct methods out of the 25-method suite. No passing result is claimed for that source.

**There was also a real native-interface mismatch.** The incumbent `lib/dataos/tiingo_reader.py` accepts either a raw-content SHA or an exact receipt identity. `read_research_history` preserves the caller's selector in `source_partitions`, while rows retain both identifiers. The new adapter incorrectly required raw-content SHA membership only. Thus authentic native receipt-ID histories failed even after fixing the unrelated fixtures. The repaired default fixtures are explicitly raw-selected, and dedicated receipt-ID tests establish the second supported path.

The consumer now matches either row identifier to the original declared reference, then requires the original capture day for that matched identifier. Unknown references, unrelated capture days, future market dates, incompatible prices, incomplete sessions and mixed adjustment vintages remain rejected. This is not permission to manufacture native dataclasses: original source bytes and rights remain the incumbent reader's responsibility.

**A public summary could echo fabricated authority.** A caller could construct or replace a `ResearchProjection` to assert PIT eligibility, admitted source use or another elevated flag. `public_summary` previously checked only the Python type. It now refuses any evidence-mode/source-use mismatch or non-false historical/rank/gate/size/trade flag with `PROJECTION_AUTHORITY_CONFLICT`. The output still contains no vendor price values.

## Executed verification — real native modules, invented inputs

A disposable source snapshot was built from immutable public GitHub files, with original Git blob verification. It includes the actual Data OS package, NYSE calendar, Tiingo archive, materializer, history reader and original tests. No stand-in class or calendar was substituted. Missing snapshot imports were resolved by fetching their exact pinned public source, not by weakening tests. The working snapshot is not a second publication carrier.

Test-first evidence:

- With corrected default fixtures and new receipt-ID cases, the unmodified adapter failed four intended tests, including the actual thirteen-instrument native producer-to-consumer case: `4 failed, 25 passed, 17 subtests passed`.
- The summary-authority test produced eight failing subtests before repair.
- Final command: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_sector_allocation_tiingo.py tests/test_tiingo_reader.py tests/test_tiingo_history.py -q --tb=short --junitxml=../native-regression.xml`.
- Final result on M2 Python **3.14.7**, pytest **9.1.1**, pyarrow **25.0.1**: **138 passed, 50 subtests passed**, exit 0. There are **30 distinct adapter test methods**; the combined count also includes collection through the existing reader-suite alias and other original Data OS tests. It is not 138 independent investment experiments.
- The native end-to-end case creates thirteen invented raw responses in a temporary archive, materializes them through the original producer, reads each by raw hash AND receipt identity, and verifies equal projected values but different provenance digests. No vendor calls, private retained market data or strategy outcomes were used.
- Five isolated mutations were caught by their intended assertion: removing receipt-ID compatibility, original capture-day matching, future-market-day rejection, mixed-adjustment rejection, and summary-authority rejection. No mutation is accepted merely for producing an unrelated import error.

Exact tested bytes:

| File | Git blob | SHA-256 |
|---|---|---|
| `lib/dataos/sector_allocation_tiingo.py` | `4402592b92249ad48924db328de783805c329daf` | `22f800c8d377dd6b5c4d8dd62ed4ae73d94c1819ac9f66b2a86652e93a740aeb` |
| `tests/test_sector_allocation_tiingo.py` | `50f8622cd57b0e9cae575efcdd1ef427b3cb2643` | `03e9592ba0f3b1e95196ca0aba27751e21cf96fa5a2f39862904f7a85231ca83` |

M2 evidence remains under `/Volumes/Mastermind/research/rotation-intelligence-census-20261016-sol-c1/r7-native-review/`: original/source manifests, red logs, final log, JUnit result and `mutation-verification.json`. Original R1–R6 historical receipts remain intact; this evidence supersedes their untested claims only where the source changed. Full hosted CI and exact-head independent review remain separate requirements.

## Requested independent Fabric review — no false execution claim

The current user requested Fabric review while the principal advances independent work. One bounded `session_summon` request used stable key `rotation-r6-review-aadf630c-pro-20261017-c1`, research-only, one attempt, exact public source and no writes or outcome reads. The existing Executive ingress returned `backend_unavailable`; original-key reply recovery returned `reply_unavailable`. The canonical Fabric projection explicitly reports `ceo_submit_armed=false`. No Job, STARTED/RUNNING or reviewer verdict is established. The request was not duplicated through another carrier or replaced by a native Sol worker. Existing GitHub reviewer request to `mastermindx-3` is also not a completed review.

The earlier shell child `rotation-r5-20261017-c1-cadence-fixtures` was read once through its original status command: still `ACTIVE_OR_WAITING`, worker unknown, no terminal result and retry unauthorized. Preserve that original uncertain effect; this repair does not depend on it or clear it.

## Remaining delivery boundary

Current Sol is responsible for advancing the source and research integration, not waiting for an imaginary human source-owner ACK. However, the earlier explicitly refused private archive action, actual data-use/point-in-time evidence, real thirteen-series revision/coverage/BIL-tail qualification and scientific outcome gates cannot be fabricated. No private archive read was repeated, no licence grant created, and no model, trade, production or held native Track A outcome was activated. Track B remains distinct from native LR-W6.

Next: verify atomic same-branch publication of these tested bytes, consume its actual hosted CI, obtain a genuinely admitted independent Fabric review, and execute only an authorized original-source qualification. Do not repeatedly rebase or manufacture another synthetic grid while the concrete source/review gates are unresolved. Draft/HOLD; broader allocation mission incomplete.
