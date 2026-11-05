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

**Strikes endpoint disclosure.** OBSERVED at the baseline:
`collectors/thetadata.py` never calls `list/strikes`. Its only `list/*` calls
are `list/symbols` (`:279`) and `list/expirations` (`:296`), and no file under
`collectors/` or `engine/` names `list/strikes`. The lane called it on the same
local Terminal (127.0.0.1:25503), with no new provider and no paid call.

**Cohort derivation (CAT).** OBSERVED: the cohort is read from
`flow_meta_20261101T043626Z.json` (schema `live_flow.meta/v2`, as-of
2026-10-30T20:11:27Z), the D107 one-shot capture of `/api/flow/meta`. The
capture is committed here byte-exact from the incumbent session f77d3f70's
OPT-005 ruling scratch: sha256
`c03eab46584b0c5ddd9efee32834b61c2423bd1952002dfe536164e0d77dd9db`, 193,559 B.
It holds no credential, token or URL. Its
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

**Expiry selection (`per_root_selection_rule`).**
- Store: as-of 2026-10-29 for all 26 roots. This is the max date in each root's
  newest eod year file (`2026.parquet`), not a chosen trading date.
- Terminal strikes: per root, the first listed expiration on or after
  2026-11-01. That gives 2026-11-02 for 12 roots, 2026-11-04 for AAPL,
  2026-11-06 for 12 roots and 2026-11-20 for XLRE.
- The dates are OBSERVED in the request URLs. That each is the first listed
  one rests on the lane report, because the lane's saved `list/expirations`
  bodies were not retained in the repository.

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
lane's on-host copy was not re-fetched, so the declared-versus-received
difference is unreconciled.

**ORCH-1 annotations.** The committed file is the received block plus ORCH-1
annotation keys; no lane-written value was changed. It hashes to
`3c27e53553d4733fafaa6b807ba4b7deb9a74ae29f31651cf1a25e82308b9315`
(26,660 B). The added keys are:
- `cohort.source_capture_path`, `cohort.source_capture_sha256`,
  `cohort.source_capture_bytes` and `cohort.source_capture_origin`;
- `per_root_selection_rule`;
- `strikes_endpoint_disclosure`.

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
- The gate's grader counts sit under `grader_per_run`, labelled PER_RUN, and
  `grader.n_graded_ok = 0` is a per-run count, not a cumulative zero
  (INTERPRETED; see `arithmetic_check`). `gate.json` carries no run id, so
  `run_id` is null with a reason. The run is identified by the commit that
  wrote the blob, `6ef6fe67976bf0c66ac637e451d975c95acf57f7` (dashboard-bot,
  2026-10-18T07:09:10Z), gate blob `482412237b95`.
- The stage's cumulative fields sit under `cumulative`, from the grades table.
  The identity holds: 85,603 + 18,225 + 65 = 103,893 = `attempted`.

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
