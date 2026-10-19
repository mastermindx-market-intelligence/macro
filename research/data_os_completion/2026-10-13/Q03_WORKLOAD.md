# Q03-1 — frozen matched workload: resource cost and preserved operational limits

Programme DATA-OS-COMPLETION, lane Q03-1. Verification only: no production code
was changed by this lane. Evidence class: **measured on `<lane-host>`, synthetic
frozen workload, paired commits; no market data.**

## 1. Scope

- Commit A (baseline): `5569baad64b8023e5cb1995c1ce7a30bc8254a7b` (measurement tree `<tree-A>`)
- Commit B (main): `ed1497887c99101bd1b8bc5438e281f02466371b` (measurement tree `<tree-B>`)
- Step 0.4 blob pins (all ten matched exactly):
  - `ed14978:lib/dataos/web_api.py` `fc35cdec14c1a83752c6c8f095ed0305218ebafc`
  - `ed14978:lib/dataos/web_workspace.py` `450c25fc363272cdff1a58889edbd14c29bffb18`
  - `ed14978:lib/dataos/web_readers.py` `753a1cdea027d47bce28eb55ad640acaf159f978`
  - `ed14978:scripts/data_workspace.py` `f3763471beb4db2174215bdfc57d17c3692d6568`
  - `ed14978:lib/dataos/registry.py` `65b0d69036da97760f20241468f2549b21d9c686`
  - `5569baa:lib/dataos/registry.py` `91c4a8eed34b118902dd2a80678b71472e328dca`
  - `ed14978:lib/dataos/read_contract.py` `460fc9403c28eefc771710cbd5b2ecd43bedfdd5`
  - `ed14978:engine/price_ladder.py` `095fee9aafa128fae08bfaee07354bfee6c3f979`
  - `ed14978:tests/test_price_ladder.py` `da1f0bc19fb1e6c9828c1c055c85ebbd5b804a3b`
  - `ed14978:engine/basket_membership_pit.py` `5c7ba201d505648365ba40ff88c6901b47aef713`
- Step 0.5 census re-verification (`git diff --stat 5569baa ed14978 -- <read-path files>`):

  ```
   config/dataset_registry.yml | 238 ++++++++++++++++++++
   lib/dataos/__init__.py      | 119 ++++++++++
   lib/dataos/registry.py      | 520 +++++++++++++++++++++++++++++++++++++++++++-
   3 files changed, 875 insertions(+), 2 deletions(-)
  ```

  The five byte-identical paths (`web_api.py`, `web_workspace.py`,
  `web_readers.py`, `scripts/data_workspace.py`, `engine/basket_membership_pit.py`)
  are absent from the output, exactly as the census predicted. New on main with
  no baseline: `lib/dataos/read_contract.py`, `lib/dataos/price_views.py`, the
  C01 seam `engine.price_ladder.resolve_close_canonical`.

## 2. Host

- `Linux <lane-host> 7.0.0-31-generic #31~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC ... x86_64 GNU/Linux`
- `os.cpu_count()` 24; `nproc` 24; Python 3.12.3; pandas 3.0.6; pyarrow 26.0.0.
- Load averages (`getloadavg`, 1/5/15-minute) around each arm: start
  `[4.29, 3.96, 2.92]`; after A_inproc `[4.63, 4.04, 2.96]`; after A_cli
  `[6.78, 4.58, 3.16]`; after C_basket `[6.58, 4.61, 3.19]`; after B_newpath
  `[6.53, 4.63, 3.21]`; after reg_as_shipped `[6.57, 4.67, 3.23]`; after limits
  `[6.57, 4.67, 3.23]`; end `[6.57, 4.67, 3.23]`. Peak 1-minute load 6.78 < 24
  CPUs at every boundary, so no arm was marked "noisy host" and no re-run was
  required by the frozen noise rule.
- The lane host is shared with other lanes (7 users, load 3–7 throughout); the
  paired/interleaved design (ABBA) is the control for that.

## 3. Freeze

- Freeze commit: `1eddd478d855eff69bab564d3e084e0dfc99d77d`, files:
  `tests/verification/__init__.py` (0 bytes), `tests/verification/bench_q03.py`,
  `tests/verification/test_bench_q03_contract.py`,
  `research/data_os_completion/2026-10-13/q03_baseline.json`.
- `git diff 1eddd478d855eff69bab564d3e084e0dfc99d77d HEAD -- tests/verification/bench_q03.py research/data_os_completion/2026-10-13/q03_baseline.json`
  → **empty** (the bench and the spec are byte-identical to the freeze; no
  post-freeze change, no re-run obligation).
- The fixture (2,040 digested files incl. 200 nested CSVs) and the frozen
  requests R1–R12, arms, interleave, accepted `MAX_*` limits and the
  pre-registered detection rule all live in the spec. The fixture is regenerated
  and digest-verified by every bench run; it is never committed.

## 4. Registry arm decision

- **Matched arm (used for A_inproc and A_cli):** both commits load
  `registry_base.yml` = `config/dataset_registry.yml` @ `5569baa`
  (content sha256 frozen in the spec). Proof that main's `load_registry`
  accepts it:

  ```
  main load_registry(base yaml): n=47 first=equity.bars.daily.stocks duplicates=()
  base load_registry(main yaml): n=51 first=equity.bars.daily.stocks
  ```

  Both directions load, so no GAP and no fallback was needed; the baseline YAML
  was chosen per the lane's preference. R3's id `equity.bars.daily.stocks` is
  the first dataset id present in both registries.
- **as-shipped arm:** each commit with its own `config/dataset_registry.yml`
  (construction + R2/R3 only; reported, never compared under the rule).

## 5. Paired results

All latencies in milliseconds; `p90` is nearest-rank. Full sample sets:
`q03_results.json`. Latency is measured with `tracemalloc` active (the
specified memory instrument) in-process — symmetric across arms.

### 5.1 A_inproc — construction and import (n=6 drivers per commit)

| metric | A (baseline) | B (main) | verdict |
| --- | --- | --- | --- |
| construction `load_workspace_config` | med 262.92, p90 280.61, min 257.93, max 280.61 | med 260.54, p90 262.50, min 257.18, max 262.50 | ok |
| import of `lib.dataos.web_api`+`web_workspace` (informational, one-time per process) | med 22.8, max 24.3 | med 49.2, max 54.3 | not judged |

The per-process import cost is the one clear construction-side change on this
path: `lib/dataos/__init__.py` (+119 lines) now imports `price_views` and
`read_contract` on every `lib.dataos.*` import.

### 5.2 A_inproc — per-request latency (cold n=6, warm n=12 per commit)

| rid | A cold med/p90/min/max | B cold med/p90/min/max | A warm med (2 passes) | B warm med | verdict cold/warm |
| --- | --- | --- | --- | --- | --- |
| R1 capabilities | 0.12/0.12/0.11/0.12 | 0.12/0.12/0.12/0.12 | 0.12/0.12 | 0.12/0.12 | ok/ok |
| R2 search | 12.25/12.34/12.14/12.34 | 12.66/12.91/12.59/12.91 | 12.98/12.95 | 13.29/13.27 | ok/ok |
| R3 describe registry | 0.17/0.18/0.17/0.18 | 0.18/0.19/0.18/0.19 | 0.19/0.18 | 0.21/0.20 | ok/ok |
| R4 browse fixture | 0.39/0.41/0.38/0.41 | 0.39/0.39/0.39/0.39 | 0.41/0.41 | 0.40/0.40 | ok/ok |
| R5 browse nested | 9.13/9.23/8.99/9.23 | 8.97/9.12/8.93/9.12 | 9.51/9.60 | 9.30/9.32 | ok/ok |
| R6 describe parquet | 115.59/145.00/112.65/145.00 | 115.30/133.98/111.46/133.98 | 0.68/0.68 | 0.67/0.67 | ok/ok |
| R7 read csv | 8.31/8.53/8.24/8.53 | 8.24/8.40/8.15/8.40 | 7.94/7.96 | 7.73/7.76 | ok/ok |
| R8 read parquet | 23.36/23.57/23.14/23.57 | 23.09/23.38/23.00/23.38 | 22.04/21.97 | 21.55/21.75 | ok/ok |
| R9 read jsonl | 29.33/29.61/28.89/29.61 | 29.14/29.42/28.98/29.42 | 29.16/29.56 | 28.89/29.03 | ok/ok |
| R10 wrong version | 0.13/0.14/0.12/0.14 | 0.13/0.14/0.13/0.14 | 0.12/0.12 | 0.12/0.12 | ok/ok |
| R11 missing file | 0.07/0.08/0.07/0.08 | 0.08/0.08/0.07/0.08 | 0.07/0.07 | 0.07/0.07 | ok/ok |
| R12 oversized read | 42.06/42.56/40.99/42.56 | 41.34/42.20/41.16/42.20 | 39.73/38.77 | 38.56/37.87 | ok/ok |

R6's cold pass carries the lazy `import pyarrow.parquet` inside the first
parquet request (both commits, ~115 ms); warm R6 is 0.68 ms.

### 5.3 A_cli — real host transport (n=7 reps per request per commit, AB/BA alternating)

| rid | A med/p90/min/max | B med/p90/min/max | verdict | exits A/B |
| --- | --- | --- | --- | --- |
| R1 | 140.3/142.1/138.7/142.1 | 166.1/169.1/162.7/169.1 | REGRESSION | 0/0 |
| R2 | 142.9/155.2/142.0/155.2 | 169.2/175.5/168.7/175.5 | REGRESSION | 0/0 |
| R3 | 139.7/145.0/138.3/145.0 | 168.3/173.7/166.8/173.7 | REGRESSION | 0/0 |
| R4 | 141.1/144.3/138.3/144.3 | 168.2/171.6/167.8/171.6 | REGRESSION | 0/0 |
| R5 | 142.8/147.6/139.8/147.6 | 169.3/171.0/167.8/171.0 | REGRESSION | 0/0 |
| R6 | 223.9/226.6/219.9/226.6 | 250.8/254.9/247.8/254.9 | REGRESSION | 0/0 |
| R7 | 143.1/147.1/139.9/147.1 | 169.8/172.1/168.0/172.1 | REGRESSION | 0/0 |
| R8 | 227.0/247.7/187.2/247.7 | 256.7/279.2/250.3/279.2 | REGRESSION | 0/0 |
| R9 | 147.0/148.9/143.5/148.9 | 174.7/178.9/172.8/178.9 | REGRESSION | 0/0 |
| R10 | 140.4/141.6/138.0/141.6 | 167.3/171.5/166.0/171.5 | REGRESSION | 2/2 |
| R11 | 141.7/144.0/140.1/144.0 | 167.2/170.7/165.3/170.7 | REGRESSION | 2/2 |
| R12 | 155.0/157.4/153.7/157.4 | 184.2/187.4/183.2/187.4 | REGRESSION | 2/2 |

Every CLI call is one fresh process, so each pays the import delta measured in
§5.1 (~+26 ms median per call, uniform across requests including refusals).
Zero timeouts, zero errors; the +26 ms is a per-process constant, not a
per-request cost. `_revision()` spawns two `git` subprocesses per CLI call at
BOTH commits — pre-existing `scripts/data_workspace.py` behaviour, reported,
not called a regression.

### 5.4 C_basket — unchanged PIT membership reader (n=25 samples per commit, 5 interleaved drivers)

| call | A med/p90/min/max | B med/p90/min/max | rows A/B | verdict |
| --- | --- | --- | --- | --- |
| members_asof 2026-07-20 (pit snapshot) | 93.95/95.13/91.97/100.48 | 93.64/94.95/92.42/95.23 | 295/295 | ok |
| members_asof 2026-01-01 (before coverage, pit=false fallback) | 6.57/11.43/5.79/17.51 | 6.29/6.93/5.67/7.38 | 300/300 | ok |
| coverage | 5.85/6.72/4.90/7.01 | 5.86/6.20/4.93/6.52 | 900/900 | ok |

Seeding uses the `config.data_dir` redirect idiom from
`tests/test_basket_membership_pit.py`; two snapshots (2026-07-08 full, 2026-07-15
with five dated removals). The store's keep-first law means a re-run into an
existing scratch dir reports `written: false` — the measured reads are
unaffected.

## 6. Deterministic counters (A vs B, matched registry)

Warm-phase counters are constant within each commit; every request shows A == B
except R3. Cold == warm except R6 (cold carries the pyarrow lazy import:
open 101→3 after first touch — identical pattern at both commits).

| rid | open | scandir/listdir | syscr | rchar | response bytes A→B | digest A==B | refusal A/B | rows A/B | columns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | 0 | 0/0 | 2 | 196 | 960 = 960 | yes | –/– | – | – |
| R2 | 2 | 2/0 | 2 | 196 | 8006 = 8006 | yes | –/– | 25 = 25 | – |
| R3 | 0 | 0/0 | 2 | 196 | **1920 → 2012** | **NO** | –/– | 26 → 31 | same schema keys |
| R4 | 1 | 1/0 | 2 | 196 | 1616 = 1616 | yes | –/– | 5 = 5 | – |
| R5 | 1 | 1/0 | 2 | 196 | 40943 = 40943 | yes | –/– | 200 = 200 | – |
| R6 | 3 | 0/0 | 5 | 69836 | 1453 = 1453 | yes | –/– | 50000 = 50000 | 7 = 7 |
| R7 | 3 | 0/0 | 5 | 30123 | 10248 = 10248 | yes | –/– | 200 = 200, scanned 200 = 200 | [date, close] |
| R8 | 3 | 0/0 | 12 | 438476 | 13179 = 13179 | yes | –/– | 200 = 200, scanned 3700 = 3700 | [date, ticker, close] |
| R9 | 3 | 0/0 | 5 | 136492 | 15663 = 15663 | yes | –/– | 200 = 200, scanned 200 = 200 | [date, kind, ticker, value] |
| R10 | 2 | 0/0 | 2 | 196 | – | – | SOURCE_VERSION_MISMATCH = same | – | – |
| R11 | 2 | 0/0 | 2 | 196 | – | – | SOURCE_NOT_FOUND = same | – | – |
| R12 | 3 | 0/0 | 5 | 738496 | – | – | RESULT_TOO_LARGE_REDUCE_COLUMNS_OR_LIMIT = same | – | – |

A_cli mirrors this: identical bytes/digests/refusals on every request except
R3 (bytes 1951 → 2043, digest differs). pyarrow reads files in C++ and is not
visible to the audit hook — that is why `syscr`/`rchar` deltas from
`/proc/self/io` are reported alongside (R8: 438,476 bytes read via the OS
counter while the audit hook sees only 3 `open`s).

## 7. New-path cost (main only)

**Label: new path; no baseline; observed cost, not a regression comparison.**
The code under test does not exist at commit A.

- `resolve_close_canonical`, CURRENT mode over 50 synthetic tickers
  (n=250, 5 driver processes): med 2.246 ms, p90 2.904, min 1.794, max 3.213;
  250/250 ok (30 values each), 0 errors, 0 refusals.
- First call per process (n=5): 300.58, 305.38, 300.35, 300.84, 301.99 ms —
  includes `_default_registry`, an `lru_cache` that loads the dataset registry
  once per process.
- REPLAY mode (n=100): med 0.023 ms; 100/100 typed refusals
  `read_contract.NO_RETAINED_OUTPUT` (no read attempted).
- `account_coverage` over a 500-member synthetic population (n=25): med
  4.865 ms, p90 4.954; 25/25 ok, 500/500 qualified members, 0 errors.
- Driver import of `pandas` + `engine.price_ladder` + `read_contract`:
  med 197.2 ms one-time per process.

## 8. Q03.03 limits

Module-level `MAX_*` extracted with `ast` from `git show <sha>:<path>` output
at BOTH commits (never by importing). A == B == frozen spec for all four files;
`scripts/data_workspace.py` has none.

| file | MAX_* (identical at A and B) |
| --- | --- |
| `lib/dataos/web_api.py` | MAX_REQUEST_BYTES 16384, MAX_LAB_WALL_SECONDS 60 |
| `lib/dataos/web_workspace.py` | MAX_RESPONSE_BYTES 131072, MAX_DIRECTORY_ENTRIES 30000, MAX_SEARCH_ENTRIES 5000 |
| `lib/dataos/web_readers.py` | MAX_TEXT_BYTES 33554432, MAX_FOOTER_BYTES 8388608, MAX_ROW_GROUP_BYTES 268435456, MAX_COLUMNS 128, MAX_SOURCE_COLUMNS 4096, MAX_ROWS 200, MAX_SCAN_ROWS 100000, MAX_CELL_BYTES 1048576, MAX_NESTING 32, MAX_CONTAINER_ITEMS 4096 |
| `scripts/data_workspace.py` | (none) |

Verbatim greps:

```
$ git show 5569baad64b8023e5cb1995c1ce7a30bc8254a7b:lib/dataos/web_workspace.py | grep -n MAX_RESPONSE_BYTES
25:MAX_RESPONSE_BYTES = 131072
134:        if len(encoded.encode("utf-8")) > MAX_RESPONSE_BYTES:

$ git show ed1497887c99101bd1b8bc5438e281f02466371b:lib/dataos/web_workspace.py | grep -n MAX_RESPONSE_BYTES
25:MAX_RESPONSE_BYTES = 131072
134:        if len(encoded.encode("utf-8")) > MAX_RESPONSE_BYTES:
```

The value is `131072` at both commits. The contract test additionally pins
every frozen `MAX_*` to the CURRENT working tree, so a future widening must
update the spec in the same PR — that is the "not silently widened" guarantee
(demonstrated killed by mutation BM4).

## 9. Q03.04 background work

Across every request sample of A_inproc (432 samples), C_basket (150) and
B_newpath (375): zero `subprocess.Popen`, zero `socket.connect`, zero
`socket.getaddrinfo`; `threading.active_count()` identical before/after every
request and equal to 1 at every driver end; `ru_maxrss` 231,136 KB at both
commits' driver ends (inproc). Listing discipline: R2 issued exactly 2
scandirs for 2 PRESENT roots, R4/R5 exactly 1 scandir for 1 returned directory
— no request over-listed. The A_cli `git` subprocesses from `_revision()` are
pre-existing at both commits and excluded by the rule. No arm hid latency or
cost behind background work.

## 10. Findings (every GAP, with reproducer)

Total under the frozen rule: 14 REGRESSION, 2 CHANGE, 0 Q03.02, 0 Q03.04,
0 LIMITS, 0 errors, 0 timeouts. Both findings are explained from the step-0.5
diff; neither is waived, and no speed-up, quota or savings number is claimed.

1. **GAP — A_cli wall latency, all 12 requests (12 REGRESSION entries).**
   median(B) > max(A) and > 1.10 x median(A) on every request, ~+26 ms median
   per CLI call (e.g. R7: 143.1 → 169.8 ms). Cause, from the step-0.5 diff:
   `lib/dataos/__init__.py` (+119) now imports `price_views` (+2078 lines) and
   `read_contract` (+1291 lines) into every `lib.dataos.*` import; the
   one-time in-process import cost rose 22.8 → 49.2 ms (§5.1), and each CLI
   call is a fresh process. Per-request in-process cost is unchanged (§5.2 all
   ok). Reproducer:
   `PY -B tests/verification/bench_q03.py --spec research/data_os_completion/2026-10-13/q03_baseline.json --repo-a <tree-A> --repo-b <tree-B> --fixture-dir <scratch>/fixture --out <scratch>/repro.json --arms A_cli`
2. **GAP — R3 `describe registry:equity.bars.daily.stocks` response grows and
   its digest changes (REGRESSION bytes + CHANGE digest, in-proc and CLI).**
   In-proc bytes 1920 → 2012 (+92); CLI 1951 → 2043. Cause, from the step-0.5
   diff: `DatasetContract` gained five optional consumer-declaration fields
   (`basis`, `population`, `clocks`, `rights`,
   `point_in_time_corporate_actions`), all serialized by
   `describe`/`dataclasses.asdict` even when defaulted (contract dict 26 → 31
   keys). Members/series fields of every other request are byte-identical.
   Reproducer: same command with `--arms A_inproc`.

Q03.01: unchanged-path requests meet the frozen workload with every timeout
included (0 timeouts, 0 errors) — the regression that exists is the CLI
process-start cost above, reported, not waived. Q03.02: no member, row, column
or field was removed (all rows/columns identical; R8 scanned 3700 = 3700).
Q03.03: no bound widened (§8). Q03.04: no hidden work (§9).

## 11. Not measured

- The U03/U04 consumer paths — not landed on main:
  `UNFINISHED: awaiting U03/U04 LANDED`. Close by re-running this bench with a
  request set covering those consumers once they land.
- The C04 sidecar emitter — not landed. Close the same way once it exists on
  main.
- The Terminal production route (`terminal_daily_ohlc_contract_v1` is measured
  only as pure mapping inside B_newpath's import; the actual Terminal daily
  OHLC production path is out of scope here). Close with a Terminal-route lane.
- Concurrency above one in-flight request. The audit-hook design is
  per-process single-threaded; closing this needs a multi-client harness with
  per-request attribution, which this frozen workload deliberately does not
  add (no new collector or service).

## 12. Commands (P1–P7)

Run from the lane worktree unless stated; `PY` = the lane venv python; pytest
runs carry `PYTHONDONTWRITEBYTECODE=1 -q -p no:cacheprovider`.

- P2 (full measurement, after the freeze):
  `PY -B tests/verification/bench_q03.py --spec research/data_os_completion/2026-10-13/q03_baseline.json --repo-a <tree-A> --repo-b <tree-B> --fixture-dir <scratch>/fixture --out research/data_os_completion/2026-10-13/q03_results.json`
  → last line: `arms=A_inproc,A_cli,C_basket,B_newpath,reg_as_shipped,limits samples=1150 errors=0 timeouts=0 regression_gaps=14+0q02+0q04+0lim change_gaps=2`
- P1: `PY -m pytest tests/verification/test_bench_q03_contract.py -q -p no:cacheprovider -rs`
  → run 1 last line: `16 passed in 4.17s`; run 2 last line: `16 passed in 3.11s`
  (both summaries 16 passed, 0 skipped).
  `PY -m pytest tests/verification --collect-only -q -p no:cacheprovider | grep bench_q03`
  → every line names `tests/verification/test_bench_q03_contract.py::...` (16
  lines); no line names `tests/verification/bench_q03.py::` — the bench is
  never collected.
- P3: `git diff --name-only ed1497887c99101bd1b8bc5438e281f02466371b HEAD`
  → exactly the six owned paths (4 pre-record + `q03_results.json` +
  `Q03_WORKLOAD.md`). `git diff --diff-filter=M --name-only ed14978... HEAD`
  → empty.
- P4: `PY -m py_compile tests/verification/bench_q03.py tests/verification/test_bench_q03_contract.py && echo compile-ok`
  → `compile-ok`
- P5: `grep -n "datetime.now\|time\.time\|requests\|urllib\|socket\|subprocess\|random" tests/verification/bench_q03.py tests/verification/test_bench_q03_contract.py`
  → hit accounting: bench `random` 15 (the seeded `random.Random(seed)`
  fixture generator), `subprocess` 11 (A_cli arm, driver spawning, `git show`
  for the limits arm), `socket` 7 (audit-event NAMES only), `requests` 7 (the
  word "requests" as the frozen request table `spec["requests"]`, never the
  HTTP library), `datetime.now` 1 (the docstring sentence declaring its
  absence), `time.time` 0, `urllib` 0; test file `subprocess` 6 and `socket` 4
  (the smoke launcher and the audit-event names it asserts), `requests` 2 (the
  spec's request table), `random`/`urllib`/`time.time`/`datetime.now` 0.
- P6 (each: mutate `<mut-tree>/lib/dataos/web_workspace.py` only, then
  `PY -B tests/verification/bench_q03.py --spec ... --repo-a <tree-B> --repo-b <mut-tree> --fixture-dir <scratch>/fixture --out <scratch>/<id>.json --arms A_inproc --rounds 2`,
  then `git checkout -- lib/` there):
  - BM1 sleep 50 ms in `DataWorkspace.read` → last line
    `... regression_gaps=19+0q02+0q04+0lim change_gaps=0`; **killed**: latency
    REGRESSION on R7–R12 (also one sub-millisecond noise trip on R1 warm2,
    median difference 0.01 ms — the rule's known sensitivity on ~0.1 ms
    requests; reported, not hidden).
  - BM2 `subprocess.run(["true"])` in `read` → last line
    `... regression_gaps=38+0q02+12q04+0lim change_gaps=0`; **killed**: Q03.04
    `subprocess.Popen` flagged on R7–R12 (plus rchar increases).
  - BM3 clamp `limit` to 10 → last line
    `... regression_gaps=0+3q02+0q04+0lim change_gaps=4`; **killed**: Q03.02
    rows 200 → 10 on R7/R8/R9, digest changes, and R12 stops refusing (10
    clamped rows fit the bound) — refusal-code CHANGE.
  - BM4 `MAX_RESPONSE_BYTES = 262144` → bench last line
    `... regression_gaps=1+0q02+0q04+0lim change_gaps=1` with R1 digest CHANGE
    (`capabilities` echoes `max_response_bytes=262144`); contract test run
    inside the mutation tree (two owned test files + spec copied there):
    `2 failed, 14 passed in 3.12s`
    (`test_max_response_bytes_is_131072`,
    `test_frozen_max_literals_match_source[lib/dataos/web_workspace.py]`);
    **killed**. Deviation from the lane's expectation: R12 did NOT stop
    refusing at 262144 — the R12 response is ≈590 KB (200 rows x 60 columns x
    40-char strings), far above 256 KiB, so it still refuses with
    RESULT_TOO_LARGE. The widening is caught instead by the contract test and
    the R1 digest. The bench LIMITS arm reads committed blobs via `git show`
    (right for two frozen commits), so an uncommitted working-tree widening is
    invisible to it — the working-tree guard is the contract test, by design.
  - **Kills: 4/4. No surviving mutation.**
  - `git worktree remove --force ~/lanes/wt/dataos-q03-1-mut` → done.
- P7: `PY scripts/check_contract_delta.py --base ed1497887c99101bd1b8bc5438e281f02466371b 2>&1 | tail -8`
  → last lines:

  ```
  ::error title=contract-delta::tests/verification/test_bench_q03_contract.py is a new pytest suite named by no run: step in any workflow — wire it into the job that owns its subject in .github/ci/legacy-jobs.yml, or add a reasoned row to config/unrun_test_waivers.yml
  contract-delta: 1 introduced, 0 inherited (base ed1497887c9)
  contract-delta: wall 255.9 s
  ```

  The single introduced finding names the unwired test file — EXPECTED, lanes
  do not wire CI (the orchestrator applies the `.github/ci/legacy-jobs.yml`
  patch). Nothing else introduced.

## Deviations (measurement-honesty notes)

- Registry arm: matched registry possible on the first choice (proof in §4);
  no fallback needed.
- BM4's "R12 stops refusing" expectation did not materialize (§12 P6 BM4);
  the kill is carried by the contract test and the R1 digest.
- The lane worktree initially had a sparse profile excluding
  `research/data_os_completion/` (the owned path was added) and `.github/`;
  P7 needed the planner's full profile, applied to THIS worktree only via
  `scripts/worktree_sparse.py full`.
- The bench LIMITS arm measures committed source; the working-tree guard is
  `test_bench_q03_contract.py` (both are part of the frozen design).
- Commit trailer reads `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  per the programme's attribution rule for this lane.
