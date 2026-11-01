# Options Intelligence receipts — 2026-11-01 (ORCH-1, source/research half)

Records only. None of these files is a signal, a ranking, a sizing input or a
trade instruction, and none activates a producer, flag or release. Baseline for
every repository citation: `021af584204c9fb00ad516c2dbc9467503a84083`.

Claim classes used throughout: OBSERVED (read from a named path, query or
command), CALCULATED (arithmetic stated), INTERPRETED (labelled). `null` means
not observed, never zero. A read failure is not empty. Stale is not live.

## `theta_chain_terms_coverage_20261101.json` — D107 GAP 1–2 (L2)

Schema `oi.theta_chain_terms_coverage_receipt/v1`. Produced by Fabric lane
`oi1-l2-r1` (census, C1, m1/MiniMax-M3) at 2026-11-01T08:55:58Z against the
existing ThetaData path only (`engine/thetadata_store.py` resolver plus the
local Terminal `list/expirations` and `list/strikes` endpoints). No new
provider, no paid call, no QQQ request.

**Cohort derivation (CAT).** OBSERVED: the cohort is read from
`flow_meta_20261101T043626Z.json` (schema `live_flow.meta/v2`, as-of
2026-10-30T20:11:27Z), the D107 one-shot capture of `/api/flow/meta`. Its
`root_catalog` has 30 entries, 27 of tier `core`. The cohort is the core tier
minus QQQ (never requested), giving 26 roots led by SPY:
SPY NVDA TSLA AAPL META IWM SMH MSFT GLD SLV TLT XLE XLK DIA XLP HYG XLV XBI
ARKK XLU XLI KRE XLF XLY XLB XLRE.

**Result.** OBSERVED: `counts` = 26 roots, 26 observed, 0 empty, 0 unobserved,
0 read_failed. `unavailable_roots` is empty because no root was unavailable;
no reason was manufactured. Every `per_root` entry gives expirations and
strikes counts from the store chain at as-of 2026-10-29, the exact
`store.chain(...)` expression, and the two exact Terminal URLs with their
response counts.

**Terms source.** OBSERVED at the baseline:
- The multiplier is a POLICY_CONSTANT (`MULTIPLIER = 100`,
  `engine/options_alpha_exact_option_outcome.py:72`), not a vendor field.
- The standard-deliverable filter is a POLICY_CONSTANT (`:101`, `:195`,
  `:804-805`).
- Exercise style and settlement are NONE on the Theta path. The store has no
  such column. The only decoder is the non-Theta, non-admitted OCC FIXML module
  (`engine/options_occ_contract_terms.py:58,60`).

**Gaps.**
- The chain as-of is 2026-10-29, two sessions behind the receipt date.
- The Terminal list endpoints carry no per-contract rows, so they cannot close
  that gap.
- `store_columns.greeks` records the code-declared list. The live store schema
  is wider.
- `committed_artifacts` lists the committed manifests, all HISTORICAL_COMMITTED
  and not live.

**Transport integrity note.** The lane declared sha256 `62808251…` for the file.
The block received by the orchestrator is byte-count identical (24,245 B),
parses, and every cited baseline line was re-checked. It hashes to
`ea879b7d21888f747b8637dded766c8cb5894df722cd9d0366decdc65cce015f`. The
committed file is the block as received. The lane's on-host copy was not
re-fetched, so the declared-versus-received difference is unreconciled.

## `outcome_attrition_20261101.json` — AC24 COUNT-ONLY (L5)

Schema `oi.outcome_attrition_receipt/v1`. Produced principal-direct by ORCH-1
from the frozen spec of packet `oi1-l5-r1`. This is a recorded deviation: no
Fabric lane ran, to conserve lane budget. Inputs are the committed blobs
`data/flow_signals/{gate.json,ledger.parquet,grades.parquet}`, verified
byte-identical by sha256. Only row counts, column names, categorical status
counts and null counts were read. No return, score, hit rate, calibration or
monitor value was read into the receipt.

**Flow-signal snapshot (HISTORICAL_COMMITTED, as-of 2026-10-18).**
- CALCULATED: 103,893 attempted = 85,603 graded ok + 18,225 not_yet_matured
  (pending) + 65 no_price_data (unavailable).
- Among graded rows, each carries exactly one horizon: 51,838 at h5 and
  33,765 at h21.
- The h63 and h126 outcome columns are null on every row: unobserved, not zero.
- The gate's `grader.n_graded_ok = 0` is a per-run count, not a cumulative zero
  (INTERPRETED; see `arithmetic_check`).

**OA-3 exact-option path: GAP.**
- The evaluator can emit `pending`, `complete`, `unavailable`, `excluded` and
  `invalid`, with six unavailable reasons.
- No retained OA-3 outcome table is committed. The runbook's remaining
  real-path gate (an accepted active expression-selection contract plus a
  natural lifecycle) is still open.

**Candidate feed: GAP.**
- The store is R2-only (`options_alpha/candidate_feed.json`), and credentials
  are forbidden to this receipt.
- The feed is inactive: policy v2 is `preregistered_inactive_until_activation`
  and the activation receipt is absent.
- Candidate-level attrition is therefore unobserved.
