# Settlement dependency — bounded static notes

**Date:** 2026-10-18 UTC
**Purpose:** Risk Radar / Mastermind #1567 release qualification; supporting notes for the parent dependency review.
**Disposition:** Preserve #1567 source acceptance. The source contains substantial settlement protections, but an existence-only deployment check is not proof of complete settlement, writer exclusion, or rollback of runtime data. No source, deployment, recovery, or live-state mutation was performed for this review.

## Scope and provenance

Read only the supplied local copies of `portfolio/paper_account.py`, `scripts/deploy_code_to_vps.sh`, necessary `portfolio/forward_evaluation.py` sections, and `source/dependency_source_manifest_20261018.json`. No first-party module was imported or executed. Shell work was limited to text inspection and hashing local bytes.

The manifest records `portfolio/paper_account.py` as identical at deployed-source baseline `732cf7be88e7159b4995a8885fbd381cd1484e3e`, accepted merge `b08223680180dcffdca7de10b03831dee3e1c287`, and protected source `e77631490e5bddca7d40c8cf039ae7763ce17b99`. The local file independently matches all three entries: 156,107 bytes; Git blob `d80b8cfc3397742e203e99ee8c15e5f44969cd50`; SHA256 `6c22b0609e867bf8160811487cb7bb942291cc9a336e6422dcb4d7628e6468d0`. Manifest SHA256: `ad1cb5288f3c2e18ad4a419c8ab463b58d55a2d10f2003b4dac8180a801cfeea`.

Other local files read:

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| `scripts/deploy_code_to_vps.sh` | 14,934 | `c158fc903121b8c4ad680049ded16000913393039944c6eec3a23d44ca376204` |
| `portfolio/forward_evaluation.py` | 75,128 | `19e053bbab9372bfd7c8dd075bfc9a6d3c7ce3450641982086400184a6e07a22` |

**Current applicability:** The parent reports a direct observation at 2026-10-18 02:46 UTC: the forward cohort is already active, starts on 2026-08-11, and retains deployment/health-verified SHA `3c4ef7f8b823baa4bb032c76add1960fa6d5a0c7`. This subreview did not repeat that live read. A missing/new/pending marker is therefore not the currently observed condition. Preserve the historical active cohort. This observation says nothing by itself about current WALs, settlement receipts, pending targets, or baseline completeness.

## Actual settlement path and accepted protections

| Boundary | Source-confirmed behavior | Source references |
| --- | --- | --- |
| Paths and serialization | Nonlegacy books resolve through `registry.data_dir(book)`. WAL and outbox live in that book directory. `_paper_transaction_lock` uses a persistent `.paper_transaction.lock`, exclusive `fcntl.flock`, and same-thread nesting keyed by its resolved path. | `paper_account.py` `_paths` 164–171; path helpers 390–402; lock 406–429 |
| Queue preflight | Under the paper lock, complete a prepared transaction first, then validate the executable target. Incompatible/malformed queues are quarantined; missing queues and valid regional legacy queues are accepted. US version/engine/book identity are explicitly checked. | `pending_target_contract_error` 2647–2703; `preflight_pending_target` 2823–2870 |
| Preparation | Canonical date required. Recover any prior WAL; refuse a new mutation while a validated receipt remains pending. Build a deterministic transaction identity and deterministic per-fill IDs; atomically persist the WAL before applying account/fill changes. Target settlements also place the transaction ID in the account, including zero-fill settlements. | `_commit_account_and_fills` 1270–1344 |
| Recovery | Require recognized WAL schema and matching portfolio, before/after digests, and an account matching the exact before or after state. Apply account if needed; repair an interrupted final JSONL fragment; append missing deterministic fill IDs. Publish the target-settlement receipt before applying the pending-queue follow-up and removing the WAL. | `_load_transaction` 460–470; `_recover_paper_transaction_unlocked` 1173–1261; `_repair_partial_jsonl_tail` 473–496 |
| Queue ownership | Clear or replace only the exact captured queue digest. A newer queued target/order list survives recovery of the older transition. | `_apply_transaction_followup` 1026–1063 |
| Receipt integrity | Reader requires `paper_settlement_receipt.v2`, matching book/filename/target digest, bound transaction preimage, consistent positive finite fill facts, deterministic IDs, bounded share/cash reconciliation, complete price coverage including the benchmark, and agreement between receipt and fill prices. Existing conflicting receipts are refused. | schemas 377–378; `_write_settlement_receipt` 537–623; validators 626–905; `pending_settlement_receipts` 953–992 |
| Durable fill proof | A separate validator compares receipt fills to durable ledger rows and refuses missing, changed, duplicate, malformed, or non-object rows. Zero-fill receipts return true without requiring a fill-ledger read. | `settlement_receipt_fills_are_durable` 908–950 |
| Deferred projection | Cash accrual waits when a receipt is pending. Ordinary marking is guarded against an already-visible pending receipt. Acknowledgement removes the named receipt durably after the caller's finalization path. | `accrue_cash_yield` 303–330; `mark` 3120–3153; `acknowledge_settlement_receipt` 995–1007 |

Atomic replacement flushes/fsyncs the file, replaces it, and attempts directory fsync. Appends flush/fsync the ledger; unlink attempts directory fsync. Directory-fsync `OSError` is tolerated, so process-interruption recovery is better supported by this source than a universal filesystem/power-loss durability claim. (`paper_account.py` 235–275, 333–349.)

## Concrete limits and defects

### 1. The two lock files are different; the outer writer contract is essential

The helper locks `$LIVE_DATA_PATH/locks/book:autonomous.lock` only around the post-health hash comparison, `finalize`, and `status` (`deploy_code_to_vps.sh` 309–334). The low-level paper-account lock is `registry.data_dir(book)/.paper_transaction.lock` (`paper_account.py` 164–171, 406–429). The latter does not itself acquire the former. The helper's comment that it excludes a service writer is therefore conditional on the actual caller using the outer book lock and both paths resolving to the intended live filesystem.

The parent separately identified `control_plane.locks.acquire_or_log("book:autonomous")` around scheduled build/evaluation, marking, and settlement, with analogous China/HK coverage. That is positive caller evidence, not an unresolved claim that no writer is locked. The next small dependency is the exact `control_plane/locks.py` path/flock/root implementation and effective runtime path mapping. Nonservice writers and low-level calls remain outside the guarantee until identified. The pre-restart gate and initial hashes are not themselves enclosed by either displayed lock; stopping one service is sufficient only if it owns all relevant writers (`deploy_code_to_vps.sh` 225–290).

### 2. The settlement gate is conservative for normal files, with a narrower predicate than the reader

The helper refuses any existing WAL and any ordinary top-level `*.json` receipt in autonomous, China, or HK, then requires the exact output `clean` (`deploy_code_to_vps.sh` 232–258). It does not parse a receipt or automatically recover/finalize it. This is a useful fail-closed release barrier for the ordinary files created by the supplied writer. Do not replace it with automatic recovery merely to make deployment pass.

The checked `paper_account.py` already uses receipt v2 at all three pins. The helper's historical schema-upgrade comment does **not** establish a new receipt-version change in #1567's examined baseline-to-merge delta.

Two qualifications matter:

- The helper uses `find ... -type f`, whereas the reader iterates every `root.glob("*.json")` entry and attempts `read_text`. A symlink named as a receipt, or a directory ending in `.json`, can be missed by the helper but followed/read/refused by the runtime reader. This is a static abnormal-filesystem counterexample, not a claim that the canonical writer produces such entries or that any exist live (`paper_account.py` 953–972).
- Absence of a WAL/receipt proves only absence of those checked blockers at that instant. It does not establish account/fill semantic consistency, successful NAV/decision/public-position finalization, or uninterrupted writer quiescence. US baseline hashes prove byte identity of two readable files across the checked interval, not those broader properties (`deploy_code_to_vps.sh` 260–279, 322–331).

### 3. Startup preflight intentionally mutates pending queues; code rollback does not reverse that mutation

`preflight_pending_target` is not a read-only health check: it may recover a WAL and may quarantine an incompatible target (`paper_account.py` 2835–2869). `quarantine_pending_target` atomically renames the original within the same book directory, preserves its bytes, records its digest and reason, and attempts both a local audit row and a shared event. If the rename fails, it returns a failed quarantine and consumers must stop. Failures of either audit sink are recorded separately and do not re-enable the target (`paper_account.py` 2712–2820).

The parent reports that scheduler startup invokes this preflight for all three active books before resuming, and accepts successful quarantine as a safe state. This is an intended protective effect. It should not be described as demonstrated corruption or as a reason to restore incompatible executable intent automatically.

The release consequence is concrete: the helper excludes runtime `data` from source synchronization and restores only listed code paths, so a completed quarantine and its audit artifacts survive code rollback. The US account/fill hash comparison does not detect a queue-only quarantine (`deploy_code_to_vps.sh` 89–103, 152–190, 260–279, 309–334). Any release proof must account for this permitted effect; no bad live target or observed quarantine is inferred here.

### 4. `mark` checks receipts before recovery can create one

**Source-confirmed guard-ordering counterexample, not an executed test or observed incident:** suppose a legitimate target-settlement WAL remains after interruption, but its receipt has not yet been written. An ordinary `mark` acquires the paper lock, finds no pending receipt at lines 3141–3152, and then calls `_load_account` at line 3153. `_load_account` recovers the WAL at 189–192; recovery publishes a receipt at 1250. `mark` does not repeat its receipt check and continues to persist benchmark/position metadata and NAV at 3158–3247 using the ordinary caller's prices/date.

Thus the function can write a mark while a newly recovered receipt awaits finalization, despite its guard against already-visible receipts. The parent separately reports that current `daily_mark` can recover during its union pre-read (`scheduler.py` 1266), checks receipts under the outer book lock at 1309, and calls cash accrual at 1322 before another account load at 1323. Cash accrual itself loads/recovers before checking receipts (`paper_account.py` 312–318). These caller protections matter: ordinary scheduler reachability of the direct `mark` counterexample is not established from this export alone. The narrow repair candidate is to recover and then recheck receipt ownership under the same inner transaction lock before ordinary mark writes, retaining legitimate receipt-driven marks. No repair was made in this review.

### 5. WAL removal and receipt acknowledgement are not standalone finalization proofs

Recovery's duplicate suppression uses a set of existing `fill_id` values. It does not compare a present row with the expected WAL row, and `_load_jsonl` skips malformed lines (`paper_account.py` 352–365, 1220–1248). A same-ID conflicting row can therefore be skipped, followed by WAL removal; target settlement still leaves the strict outbox proof available. The separate durable-fill validator detects such conflicts when actually called (`908–950`). This distinction prevents overstating the `committed` recovery result as complete ledger validation.

`acknowledge_settlement_receipt` validates the ID's shape and removes that path; it does not itself acquire the paper/book lock, validate receipt contents, prove durable fills, or prove downstream projections (`995–1007`). Likewise, `mark`'s receipt ID/source guard does not itself establish that its supplied prices equal the receipt's saved prices (`3141–3153`). These are lower-level primitives whose safety depends on the actual canonical finalization caller. The allowed files do not expose that complete caller sequence. Treat it as the next bounded read, not as evidence of a currently incorrect acknowledgement.

## Already-active cohort and release meaning

`initialize_start` preserves a valid existing active marker, and `finalize_start` returns without resetting its SHA or cohort start (`forward_evaluation.py` 530–535, 560–577). An existing active marker also permits `evaluate` to build/persist when a caller runs it (`1554–1590`). Therefore the helper's description of pending evaluation being inert is applicable to newly pending cohorts; it does not provide a write barrier for the active August cohort observed by the parent. Actual scheduled caller serialization and restart behavior govern that case. This review does not authorize changing the historical marker to fit a new release.

## Smallest next dependencies and acceptance evidence

1. Read the already-requested exact `control_plane/locks.py` implementation and bind its generated book-lock path to the helper and effective service filesystem. Preserve the parent's positively identified scheduled callers.
2. Locate only the actual callers of `acknowledge_settlement_receipt`, `settlement_receipt_fills_are_durable`, and `mark(..., _settlement_receipt_id=...)`; inspect their lock extent and the order of account-anchor check, durable-fill proof, receipt-price use, NAV/decision/public-position publication, and acknowledgement. Include their retry behavior after a projection failure. Do not invoke them.
3. Use the actual release owner and existing source/release process to qualify the permitted startup-quarantine and active-cohort effects alongside the already recorded rollback defects. A successful health probe or `clean` settlement gate alone does not complete that proof.

No provider, model, market-data, strategy, allocation, or general Bot refactor work was added. These notes are a separate dependency review input and do not alter earlier accepted reports or imply current live damage.
