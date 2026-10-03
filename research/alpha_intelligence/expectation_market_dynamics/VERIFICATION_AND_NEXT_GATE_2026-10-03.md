# Information→Price R0 verification and next gate — 2026-10-03

Status: **RESEARCH_ONLY / candidate; MISSION_COMPLETE: false**

Assignment: [Macro #8309](https://github.com/mastermindx-market-intelligence/macro/issues/8309)

Existing owner: `WS:ALPHA-INTELLIGENCE-INTEGRATION`, K3E Expectation Market Dynamics / SRC-A1.

## Decision and scope

The stateless source-qualification diagnostic is implemented and independently reviewed. It was executed on the two exact existing SRC-A1 Git blobs. It detects known historical defects, preserves unknowns and excludes unsupported comparisons without rewriting source truth. This is implementation and source evidence; it is not financial evaluation, SRC-A1 promotion, live installation or EXP-1 acceptance.

The proposed source change adds no data collector, store, source schema, residual computation, model, ranker, event identity, production consumer, schedule or capital action. The full architecture/research synthesis is in `INFORMATION_TO_PRICE_PROGRAM_2026-10-03.md`.

## Immutable inputs and executed code

Input revision: `ff420e6841a2468e4b718340cff240abbef114f1`.

Frozen audit cutoff: `2026-10-03T06:31:51Z`.

| Artifact | Git blob / bytes | SHA-256 |
|---|---|---|
| `data/revisions/expectation_observations.parquet` | `164919cf4c33e53ca7fcb8dad6e83bd4771b2ad1`; 37,020,102 B | `3db55f485c01bd307f1419ff04f392ae5f1994d2e7d8071b977abe9bbb562b93` |
| `data/revisions/expectation_attempts.parquet` | `46d143323994c6750bedbd98cc602b8a09486813`; 1,169,700 B | `05507a186772eb0de0cfcc2e21714091dca4247cbf0957aaf0c51a3324db691e` |
| `information_to_price_audit.py` | Executed and independently reviewed source | `ec89a53116081627881dcfc082d4bd9e06de0c2264c315d013ee1136c480bc8e` |
| Final `test_information_to_price_audit.py` | 23 tests; class name aligned to repository discovery | `f46f3a77f92f0f20be38a8520e16de47fad9cf9637e7efd2ef92ef9c678d5d52` |
| `INFORMATION_TO_PRICE_AUDIT_2026-10-03.json` | 41,276 B; complete stdout report | `9191e344d4d10b211a66ccb22f5b5a0a07aa2180aaa2b0ddb08503239a704e36` |

The final test-class rename from `AuditTests` to `TestAudit` changes repository test discovery, not audit behavior. The complete 23-test suite passed again after that rename. The previously reviewed test digest was `b1df6ad58ed60b5a8fb4b522e386fe96bd426f0d530fd82491dfe7616c10b6d6`; the implementation and report did not change.

## Reproduce

From this source checkout, substituting an existing checkout with the pinned objects for `$PWD` if needed:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  research/alpha_intelligence/expectation_market_dynamics/test_information_to_price_audit.py -q

PYTHONDONTWRITEBYTECODE=1 python3 \
  research/alpha_intelligence/expectation_market_dynamics/information_to_price_audit.py \
  --as-of 2026-10-03T06:31:51Z \
  --repo "$PWD" \
  --revision ff420e6841a2468e4b718340cff240abbef114f1 \
  --git-observations-path data/revisions/expectation_observations.parquet \
  --git-attempts-path data/revisions/expectation_attempts.parquet
```

The CLI emits JSON to stdout. It disables lazy Git fetching, requires both inputs at the same full commit, hashes their actual bytes and refuses an LFS pointer. The pure audit uses the standard library; parquet decoding uses pandas/PyArrow. Arrow nullable decoding is necessary because ordinary float conversion can erase the distinction between true NULL and IEEE NaN. A caller may also supply two explicit stable local parquet files; that mode declines to claim a common historical origin.

## Actual results

| Population | Result |
|---|---:|
| Observation rows / unique observation IDs | 473,200 / 473,200 |
| Attempt rows / unique attempt IDs | 8,583 / 8,583 |
| Observation tickers / attempted tickers | 1,506 / 1,510 |
| Observation sessions / attempt sessions | 44 / 46 |
| Finite measurements / genuine NULL / malformed numeric measurements | 400,509 / 72,691 / 0 |
| All linked observation rows / sum of attempt-declared counts | 473,200 / 473,200 |
| Declared-capture structurally eligible / excluded rows | 400,482 / 72,718 |
| Central average/median rows with declared capture support | 66,860 |
| Success / partial / null attempts | 8,373 / 77 / 133 |
| Present native period anchors / absent anchors | 448,588 / 24,612 |
| Retained adjacent present pairs / declared-anchor rollovers | 329,092 / 2,561 |

Every observation lacks canonical issuer/security references, units, currency, accounting basis and source-effective/publication clocks, and has rights `UNKNOWN`. Those are separate semantic and use dependencies. The collector deliberately retains them as unknown. The diagnostic neither fabricates them nor treats a rights label as authorization.

The only integrity reason in the full retained snapshot is **27 present non-count measurements in non-estimable groups**. Independent cohort inspection placed all 27 in the August 26 C2 session `d9fa989a6c9e3b82a1d2ab92f90c16976ad3c1fa9df75ffcca814c1141649c9d`, for BRK-B, COKE and CRVL, from 04:02:56.529421Z through 04:04:21.394304Z. No later cohort violates that criterion. This reproduces the documented pre-repair defect, not a new collector regression. The nine zero-valued coverage counts remain valid count facts. Historical observations stay immutable.

There are **2,016 nonexclusive source-consistency flags** for unavailable covering-count companions. They are already within the missing-measurement population and must not be added to the excluded-row total. There are no detected duplicate-ID, receipt-binding, supersession-consistency or knowledge-clock-order failures in this snapshot. A retained snapshot cannot prove complete history or the absence of an earlier overwrite.

All financial authority fields, historical availability verification and predictive validation are false. No event, actual-result, price, future-return, residual or held-outcome data was read by the diagnostic.

## Independent review and test evidence

The builder's initial candidate was not accepted on a green test result alone. Independent review reproduced and required repairs for:

1. Present estimates qualifying without valid positive analyst coverage.
2. Future economic effective dates incorrectly treated as future knowledge.
3. Supersession skipping a newer retained predecessor and contradictory unchanged labels.
4. Corrupted or late coverage companions supplying apparent support to sibling observations.

The revised implementation was independently reread and passed ten targeted reviewer tests. Parent execution then passed all **23 tests** and the full pinned native run (exit 0; approximately 34 seconds). The tests include genuine zeros, typed NULL, Boolean/NaN/infinity rejection, malformed rows, orphan and duplicate references, source hash bindings, future/naive/reversed clocks, economic effective-time separation, period rollover, latest predecessor, tied-clock ambiguity, finite bounded diagnostic samples, exact paired input provenance and absence of permission escalation.

## CI execution ownership

The suite is enrolled as one additional named step in the existing `gate: code` logical job `unrun-factor-research` in `.github/ci/legacy-jobs.yml`. Existing dependencies already include pandas and PyArrow. Existing workflow triggers and checkouts include the research paths.

The step invokes the audit CLI with `--help` and explicitly runs the test path with pytest. The CLI invocation names the implementation for static dependency inference without reading inputs. Both paths independently select the existing owner.

A first actual-source scope assertion failed despite 23 passing tests: the repository's `audit_unrun_tests.defines_tests()` recognizes test classes beginning with `Test`, while pytest also collects the original `AuditTests(unittest.TestCase)`. Renaming the class to `TestAudit` repaired discovery without changing the shared classifier. Final actual-source proof, with no mocked inventory:

```text
23 passed in 0.63s
EXACT_CI_OWNERSHIP information_to_price_audit.py => unrun-factor-research
EXACT_CI_OWNERSHIP test_information_to_price_audit.py => unrun-factor-research
derived scopes for 1/1 jobs
```

`python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --gate code --validate-only` exited 0 and validated 168 legacy job definitions. It did **not** execute 168 jobs. Hosted PR CI and source merge remain separate publication evidence; this local receipt does not claim them.

## Current native behavior witnesses

The August capability ledger's claim that five behaviors have never fired is no longer an adequate description of the retained source. Bounded independent body checks found:

| Behavior | Witness and source version | What is directly established |
|---|---|---|
| Unchanged values | UVV, EPS, +1q, average; `ec66cc3fa210c489fd104a41c4e2cf070293421d` → `cc9fdabd6204bc89ab0eb7d2d9e26075cfb90f3a` | Same value/unit/currency/basis/anchor, later clock, unchanged state, no supersession; prior selected fields retained. |
| Changed value supersedes | V, EPS, +1q, average; same pair | Same anchor, changed value, newest prior ID cited, later clock; prior selected fields retained. |
| Partial response preserves prior good state | JBGS, revenue, 0q; September 25 and October 1 | Two partial attempts append twelve typed-missing non-count fields; prior coverage-positive measurements remain intact across all 31 observation columns. |
| Fiscal rollover | KBH, revenue, 0q, average; `e52b46d36ea570eac5ae7df81cd6903da6b61694` → `969883bc9733eaa81af6dbdcd6841fd363b6aeda` | Scheduled September 25 source; native anchor changes 2026-08-31 → 2026-11-30, new original, no supersession, later clock, positive coverage and full prior-row retention. |
| Repeated horizon shape | UVV and V repeated sessions | The raw set remains {0q, +1q, 0y, +1y}; this is observed preservation, not a universal four-horizon vendor contract. |

The full attempt search found fifteen partial attempts after prior structurally good name state, of which **two** contained new missing non-count fields after prior good same-grain observations. There were zero null attempts after prior structurally good name state. No 401/403/429/malformed/error attempts appear. The partial branch has source evidence; untriggered failure variants retain their separate hermetic evidence and natural-trigger limitations.

### Exact partial-after-good recovery witnesses

September 25:
- Introducing commit `969883bc9733eaa81af6dbdcd6841fd363b6aeda`; parent `e52b46d36ea570eac5ae7df81cd6903da6b61694`.
- Attempt `4824256eed666a3de9c84c52c0943d43fbd051e253c25b332b7d80a7de240c35`.
- New missing low observation `0cb2901aa2bd4c2b4252fa7ce4f567bf6b09520423929e1aeb12f7500c5ee135`; prior good `e60711b5a87398e76a813bf8578ed0eb86815ddd6766f93f17018d243380875b`.
- Attempt 2026-09-25T06:10:44.029721Z → 06:10:56.592352Z; appended observation clock 06:10:44.160930Z.

October 1:
- Introducing commit `99f440526ca112999404829290d017374c31f893`; parent `f735a497b78862d6cf718acaae490a4c78eff342`.
- Attempt `16a7d8ddfa2479875b91a75b3ded02f372595842e1cd1c0d818af4764a07e175`.
- New missing high observation `357788399d669dbc900d1d7839369ff06137d087b3ae8dcba83051df4d5fd70f`; prior good `d41b173567b26c851df5b7de140e1b3fecf472a074e61a40043b93227e3b705e`.
- Attempt 2026-10-01T04:22:37.365376Z → 04:22:50.984751Z; appended observation clock 04:22:37.411996Z.

Both prior full rows are equal in introducing-parent, introducing-commit and current-base snapshots. Both new missing rows and all thirteen attempt columns are equal from introduction to current. The new missing rows have no period anchor and no supersession; this proves preservation without asserting same-fiscal-period continuity.

### Scheduled rollover replacement

The strongest rollover witness is KBH revenue 0q average in the same scheduled September 25 session as JBGS. New observation `81070408146974ab4003c09fcc08a862ecccb2c87059fd3a54843b5a8a2054ba` is absent from parent `e52b46d36ea570eac5ae7df81cd6903da6b61694` and present in introducing commit `969883bc9733eaa81af6dbdcd6841fd363b6aeda`. Prior observation `75a1f0b16a9f133e001a51e7bc6b73ec77bb5d6f561ce87a1a431f144a3e789d` remains equal across all 31 columns in parent, introducing commit and current base. The new full row also remains equal to current.

Attempt `750903502ea83e6ab4a942f776de520c685cf3ae51fbb622da540c23b8ea31e8` is success with 56 observations, 2026-09-25T06:15:01.560426Z–06:15:17.085699Z. The new observation clock is 06:15:01.694832Z. Both old and new covering counts are positive and interpretable. The period moves from 2026-08-31 to 2026-11-30; the new row is original with no supersession. This scheduled, fully traced witness replaces the earlier dispatched MKC example for acceptance purposes.

A bounded match against 150 existing daily runs identified 40 of 44 observation sessions: 29 scheduled and 11 dispatched. Twenty scheduled sessions contain anchored rollover candidates. Three additional job reads confirmed successful source/commit steps with an unrelated OIP tail failure. Their introducing Git commits were outside the shallow local history, so the fully traced September 25 KBH witness is preferred. No additional historical source or outcome was synthesized.

## Actual producer bindings and limits

Root recomputed the collector's deterministic session preimages and independently inspected GitHub job receipts:

| Witness session | Bound run / event | Engine receipt | Source step / commit step |
|---|---|---|---|
| UVV / V `bc4cedfe5e97…` | [36952547249](https://github.com/mastermindx-market-intelligence/macro/actions/runs/36952547249), schedule | Job 110720426260, cancelled; 2026-10-02 11:27:28Z–16:32:30Z | Regime/source step success 11:32:05Z–12:54:03Z; final engine-commit step pending in returned receipt; source commit exists at 16:30:03Z. |
| JBGS / KBH September 25 `c74d5a8ba6c0…` | [36078806272](https://github.com/mastermindx-market-intelligence/macro/actions/runs/36078806272), schedule | Job 107948023991, failure; 05:04:41Z–09:25:09Z | Source step success 05:15:30Z–07:04:35Z; engine-commit step success 09:16:14Z–09:22:25Z. |
| JBGS October 1 `879840460de2…` | [36801122853](https://github.com/mastermindx-market-intelligence/macro/actions/runs/36801122853), schedule | Job 110201628354, cancelled; 03:23:37Z–05:22:10Z | Source step cancelled 03:31:35Z–04:58:59Z; engine-commit step success 05:18:10Z–05:20:22Z. |
| MKC `18eea38eda5a…` | [36832376691](https://github.com/mastermindx-market-intelligence/macro/actions/runs/36832376691), workflow_dispatch | Job 110354097909, failure; 16:04:01Z–20:35:16Z | Source and engine-commit steps success; event is not a scheduled source witness. |

Run-level success is insufficient attribution. Conversely, an unrelated later job or engine-tail failure does not logically erase successfully committed source observations. The frozen SRC-A1 contract requires actual scheduled production and the specified source behaviors; it does not require every unrelated engine step to succeed. Source-owner acceptance must examine the exact component evidence and complete the required post-repair cohort audit. A deterministic session hash is a consistency binding, not an unforgeable attestation on its own.

The generic GitHub fetch adapter did not expose Actions run listing. Supported read-only GitHub CLI listing supplied known run IDs; dedicated job reads and filtered CLI job metadata supplied these receipts. No workflow was dispatched, rerun, cancelled or modified for evidence.

## Remaining acceptance and continuation

1. Complete the existing SRC-A1 owner acceptance assessment using the qualified post-repair scheduled cohorts, complete source/attempt reconciliation and the ten existing mutation gates. Scheduled KBH now supplies the anchored rollover witness; scheduled JBGS supplies partial-after-good preservation. A complete native acceptance record remains required.
2. Record native SRC-A1 acceptance only when that evidence warrants it; until then the accepted ledger remains `BUILT_NOT_PROVEN`. Do not preserve the obsolete assertion that no re-observations have occurred.
3. Preserve historical defects and explicit downstream exclusion; do not rewrite old raw rows or infer missing metadata.
4. After SRC-A1 acceptance, perform a fresh path/authority collision census and commission the existing EXP-1 as a separate bounded change with a real consumer.
5. Keep EVAL-0 and its activation/digests unchanged. No new target, trial, held-outcome inspection, residual engine or prediction has been admitted by this receipt.

Source custody remains the installed-launcher workspace `/Volumes/Mastermind/agent-workspaces/claude/4f623a88e8fe5eac/information-to-price-20261003-cace05a127eed148`, branch `claude/ssd-information-to-price-20261003-cace05a127eed148`. Native helpers are completed bounded contributions, not an Executive Job, installed runtime or persistent background worker.
