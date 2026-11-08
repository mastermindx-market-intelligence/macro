# R02 — Install / selection / consumption plan (P23-1)

PLAN ONLY — NOT EXECUTED. Every step below is a seat act or a read-back; this document performs none of them.

## 1. Inputs (pinned)

- Start commit (fresh main, carries heal #9234): `16e94177f063b27c7da6adeb709df2f8b8613996`.
- Blob pins at that commit:
  - `lib/dataos/read_contract.py` → `460fc9403c28eefc771710cbd5b2ecd43bedfdd5`
  - `lib/dataos/web_workspace.py` → `450c25fc363272cdff1a58889edbd14c29bffb18`
  - `scripts/data_workspace.py` → `f3763471beb4db2174215bdfc57d17c3692d6568`
  - `research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md` → `784b6c259815ccdc1324bd7345499699d3c6122c`
- C02 contract landed on main as squash `5a7d43b9ba04e867e831d4d7c349acb022bb4d5e` (PR #9210): `lib/dataos/read_contract.py`
  `account_coverage` (read_contract.py:1246), `CoverageResult` (read_contract.py:1062), `ReadResult.coverage`
  (read_contract.py:298), `Disposition` (read_contract.py:904), `SourceSegment` (read_contract.py:930),
  `MemberDisposition` (read_contract.py:946), refusal codes `DUPLICATE_MEMBER`, `COVERAGE_UNRECONCILED`,
  `BASIS_CHANGED`, `IDENTITY_CHANGED`, `FALLBACK_NOT_DECLARED` (read_contract.py:95-99).
- NOT landed (wave 3): C03, C04, M01, U03, U04. Every step that needs one of them is marked `BLOCKED-ON-<lane>` and is not
  written as if it already works.

## 2. Receipt tables

Four receipt kinds per consumer (R02.02: installed code, published data generation, selected setting, runtime execution are
separate receipts). `python` below means the repo's existing interpreter; every command is a bounded read-back.

### Consumer A — Terminal daily OHLC chart + data-origin readout (Terminal repo, default branch `master`)

| receipt kind | owner | exact command or path | expected observation | check id | state |
| --- | --- | --- | --- | --- | --- |
| installed code | Terminal `master`: `ingest/build_universe.py::build_ohlc_json` output feeding the daily OHLC chart and its data-origin readout in `ChartFrameBar.tsx` (D00_SEMANTIC_DECISIONS.md:113) | anonymous read-only inspection of Terminal `master` at the pinned head `4005275c` (D00_SEMANTIC_DECISIONS.md:121-122) | the OHLC JSON builder and the data-origin readout controls exist on `master` at the pinned head; no remote shell, no build, no deploy act is part of this plan (seat-only) | R02.02 | PLANNED |
| published data generation | the OHLC JSON the chart consumed (polygon/massive bars, D00_SEMANTIC_DECISIONS.md:113) | re-read the served OHLC JSON anonymously and read its origin fields alongside the rendered readout | the origin fields name the serving source and the bars' as-of span; no generation-ledger id is carried on this surface today (see C4 in the appendix) | R02.02, R02.04 | PLANNED |
| selected setting | the data-origin readout rendered with the chart (D00_SEMANTIC_DECISIONS.md:113) | read the readout text as served | the readout names the source actually served, not a preferred label | R02.02, R02.04 | PLANNED |
| runtime execution | Terminal PR #996 (anonymous reads only) | the recorded production proof of the daily OHLC chart + data-origin readout; a re-read would repeat the anonymous production read of the chart surface and compare the readout to the served JSON | PRODUCTION_PROOF rung (config/fable_mode_core.md:50) recorded via #996; no repo file at the pinned commit records #996 (searched), the citation is the programme record given to this lane | R02.01, R02.02 | ACCEPTED-RECEIPT: Terminal PR #996 |

No ssh, no deploy, no build command appears in this plan; consumer A re-reads are anonymous Terminal reads, seat-only.

### Consumer B — `scripts/data_workspace.py` CLI over `lib/dataos/web_workspace.py`

The CLI surface observed by `--help` at the pinned commit (appendix, §A6): flags are exactly `--config CONFIG` (required)
and `--capabilities`; there are no subcommands. Request actions are `search`, `browse`, `describe`, `read`, `lab_signals`,
`lab_plan`, `lab_run` (web_api.py:206-228).

| receipt kind | owner | exact command or path | expected observation | check id | state |
| --- | --- | --- | --- | --- | --- |
| installed code | `scripts/data_workspace.py` (blob `f3763471…`), `lib/dataos/web_workspace.py` (blob `450c25fc…`), `lib/dataos/web_api.py`, `lib/dataos/read_contract.py` (blob `460fc940…`) | `python scripts/data_workspace.py --help`, then `python scripts/data_workspace.py --config <host-binding.json> --capabilities` | `--help` shows exactly `--config` and `--capabilities`; `--capabilities` lists the seven actions (web_api.py:226-228) and the envelope carries `implementation_revision` (web_workspace.py:124), which `_revision()` fills with the 40-char commit or `RELEASE.json` `source_commit` (scripts/data_workspace.py:28-55) | R02.02 | PLANNED |
| published data generation | the CLI result envelope | run one `read` action; record sha256 of stdout; read the envelope fields | envelope carries `observed_at`, `implementation_revision` (web_workspace.py:123-124); the read carries `expected_version` (web_api.py:216-217), a stat-digest file version (`statv1:` prefix, web_workspace.py:74-77). The C02 generation id `GenerationRef.generation_id` + `supersedes` (read_contract.py:220-225) exists as contract only — no production constructor exists (appendix C4) — so the generation-ledger receipt is UNFINISHED until a producer lands | R02.02 | PLANNED (generation-ledger id: UNFINISHED: no producer of `GenerationRef` exists) |
| selected setting | the host-owned `--config` binding JSON (schema `mastermind.data_workspace_bindings/v1`, loader `load_workspace_config`, web_workspace.py:345-371; committed example `config/web_data_workspace.studio.json`) | record sha256 of the binding file and the list of root aliases with their `evidence_kind` values from one `describe`-style read of the binding | roots carry `evidence_kind` ∈ {unqualified_snapshot, historical_archive, research_sample, research_capture, raw_archive, proposed_source} (web_workspace.py:42-47); `registry_path` selects the dataset registry; `equity.bars.daily.stocks` is registered at config/dataset_registry.yml:44 | R02.02, R02.04 | PLANNED |
| runtime execution | the CLI's own output digest | `python scripts/data_workspace.py --config <host-binding.json>` with one stdin `read` request against `equity.bars.daily.stocks`; receipt = sha256(stdout) + envelope `implementation_revision` + `expected_version` | one JSON result, exit 0; envelope stamps `source_access: read_only` and `production_qualification: NOT_ESTABLISHED_BY_THIS_ADAPTER` (web_workspace.py:125-126) | R02.01, R02.03 | PLANNED |

### Consumer C — basket composition (`engine/basket_membership_pit.py` suites, D00_SEMANTIC_DECISIONS.md:115)

C2 census (appendix) found no production caller of `account_coverage` and no reader of `ReadResult.coverage`: the only
read_contract users are `engine/price_ladder.py` (types only: `ReadMode`, `ReadRequest`, `RefusalCode`, `ViewContract` at
price_ladder.py:94; seam functions `_c01_code` :676, `_c01_bind` :710, `resolve_close_canonical` :765 — none touches
coverage) and a schema-def name string in `engine/theme_graph/selection_cohort.py:223`. `engine/basket_membership_pit.py`
does not import read_contract at all. That is why every consumer C row is blocked.

| receipt kind | owner | exact command or path | expected observation | check id | state |
| --- | --- | --- | --- | --- | --- |
| installed code | basket composition suites wiring onto the C02 contract | blocked until a lane lands the composition read over `account_coverage` (read_contract.py:1246) | composition code imports read_contract and calls `account_coverage` | R02.01, R02.02 | BLOCKED-ON-C03 |
| published data generation | `CoverageResult` carried on `ReadResult.coverage` (read_contract.py:298, 1062) | blocked: no producer exists | per-member `MemberDisposition` rows (read_contract.py:946) under the cycle's view contract | R02.02 | BLOCKED-ON-C04 |
| selected setting | the composition population and basis declaration | blocked: no consumer exists | the contract declares a fixed population and adjustment basis; drift refuses `BASIS_CHANGED`/`IDENTITY_CHANGED` (read_contract.py:97-98) | R02.02, R02.04 | BLOCKED-ON-C03 |
| runtime execution | a composition read with its coverage account | blocked: `account_coverage` has zero callers today (C2) | refusal codes `DUPLICATE_MEMBER`, `COVERAGE_UNRECONCILED`, `FALLBACK_NOT_DECLARED` reachable (read_contract.py:95-99) | R02.01, R02.03 | BLOCKED-ON-C04 |

## 3. R02.01 — Enrolled-market matrix

D00.D6 declares the market populations (D00_SEMANTIC_DECISIONS.md:111-119):

| market (as D00 declares it) | consumer | evidence carrier | state |
| --- | --- | --- | --- |
| US (XNAS, XNYS, ARCX) | A | Terminal PR #996 production proof of the daily OHLC chart + data-origin readout | ACCEPTED-RECEIPT: Terminal PR #996; the planned re-read confirms the three venue codes are the ones served |
| US | B | the planned CLI runtime receipt over `equity.bars.daily.stocks` (config/dataset_registry.yml:44) | UNFINISHED: no executed production read exists; only PLANNED rows above |
| US suites | C | the C02 contract, landed (squash `5a7d43b9…`, PR #9210) with zero production callers (C2) | BLOCKED-ON-C03, BLOCKED-ON-C04 |
| HK | identity normalization only: `normalize_hk_symbol` (lib/dataos/identity.py:665) | none beyond the normalizer | UNFINISHED: enrolled for normalization only; no HK price-view positive witness is claimed in v1 and the gap is reported as coverage, not hidden (D00_SEMANTIC_DECISIONS.md:117-119) |
| CN | identity normalization only: `normalize_cn_symbol` (lib/dataos/identity.py:610) | none beyond the normalizer | UNFINISHED: same basis; CN limit arithmetic stays on RAW per the standing kill (D00_SEMANTIC_DECISIONS.md:119) |

## 4. R02.03 — Adoption statement

Consumer A's accepted receipt proves one production surface: the Terminal daily OHLC chart and its data-origin readout,
 anonymously read, as recorded under PR #996. Consumer B's planned receipts prove one host binding (the binding file passed
 via `--config`), the root set it declares, one dataset in the registry, and one stdin request served once — a single
 sample on a single host. Consumer C's receipts prove nothing yet because none can be executed. None of these proves
 all-account or all-universe adoption: every B envelope carries `production_qualification:
 NOT_ESTABLISHED_BY_THIS_ADAPTER` (web_workspace.py:126), and the adapter is a request-local observation service
 (web_workspace.py:99-100), so no receipt here generalizes beyond the exact root, dataset and request it recorded.

## 5. R02.04 — Coverage honesty

Where history is unqualified or missing, the consumer must show it as such:

- B: each root declares its `evidence_kind` (web_workspace.py:42-47) and every response envelope stamps
  `production_qualification: NOT_ESTABLISHED_BY_THIS_ADAPTER` (web_workspace.py:126); an `unqualified_snapshot` root is
  therefore always served as unqualified, never as current. `expected_version` (web_api.py:216-217) keeps the served file
  version explicit.
- C: the C02 carriers are `Disposition` values `STALE`, `MISSING`, `NEVER_INSPECTED`, `REFUSED` (read_contract.py:910-916)
  and the refusal codes `COVERAGE_UNRECONCILED`, `BASIS_CHANGED`, `IDENTITY_CHANGED`, `FALLBACK_NOT_DECLARED`
  (read_contract.py:96-99) — all blocked behind C03/C04 until a caller exists.
- A: the carrier is the data-origin readout itself (D00_SEMANTIC_DECISIONS.md:113); the planned re-read checks that the
  readout shows unqualified or missing history as such. UNFINISHED: no committed code in this repo declares consumer A's
  missing-history behavior, so the re-read criterion is the only carrier named here.
- Generation honesty on price reads: `MIXED_GENERATION` and `UNBOUND_GENERATION` refusals exist in
  lib/dataos/price_views.py:214-216.

## 6. Appendix — census outputs (trimmed)

### A1. Consumer B entrypoints (C1)

`scripts/data_workspace.py` (98 lines): `--config` (required, host-owned binding JSON), `--capabilities`, hidden
`--lab-worker` (scripts/data_workspace.py:72-74); `main()` at :70; `_revision()` at :28; `_input()` at :58. No
`add_parser`/`subparsers` exist — the CLI has no subcommands. `lib/dataos/web_workspace.py`: `MAX_RESPONSE_BYTES = 131072`
(:25), `class WorkspaceError` (:34), `class RootBinding` (:42), `class DataWorkspace` (:99, request-local observation
service), `load_workspace_config` (:345). Request actions live in `lib/dataos/web_api.py:206-228`: `search`, `browse`,
`describe`, `read`, `lab_signals`, `lab_plan`, `lab_run`; `capabilities` is served by the flag.

### A2. Consumer C seams (C2)

`git grep -n "read_contract|price_views|account_coverage|CoverageResult" -- engine scripts app ingest` returned:

- `engine/price_ladder.py:93-94` imports `RefusalReason` (price_views) and `ReadMode`, `ReadRequest`, `RefusalCode`,
  `ViewContract` (read_contract). Functions: `_c01_code` (:676), `_default_registry` (:688), `class CanonicalClose`
  (:694), `_c01_bind` (:710), `_c01_values` (:738), `resolve_close_canonical` (:765), `terminal_daily_ohlc_contract_v1`
  (:951). None calls `account_coverage`; none reads `ReadResult.coverage`. Its `coverage` mentions (:117-943) are price
  row-date spans inside the C01 seam, not the C02 coverage account.
- `engine/theme_graph/selection_cohort.py:223` — `_state_validator` (:221) reads a JSON-schema `$defs` entry named
  `owner_state_read_contract`; a name string only, not the read_contract module.
- `app/deploy/update.sh:1304, 1504, 2388` — service-restart fence regexes naming `lib/dataos/*.py` files; deploy plumbing,
  not callers.
- `engine/basket_membership_pit.py` — no read_contract/price_views/account_coverage/CoverageResult reference at all.

No production path calls `account_coverage` today; that is why consumer C is `BLOCKED-ON-C03`/`BLOCKED-ON-C04`.

### A3. Nightly owner (C3)

ORCHESTRATOR-CORRECTED (ORCH-4). The lane's census reported that `.github/workflows/` does not exist. That was a
false negative: the lane ran in a sparse worktree with no `.github/` on disk. At the pinned commit,
`git ls-tree --name-only 16e94177f063 .github/workflows/daily.yml` prints the path. The verified owner chain:

- `name: daily` (.github/workflows/daily.yml:1). It runs on `cron: "30 22 * * *"` and `"30 23 * * *"`, which is
  18:30 ET under EDT and under EST (daily.yml:36-37).
- Job `collect`, on `runs-on: [self-hosted, macstudio]` (daily.yml:125, :131).
- Step `run collectors`, `id: collectors` (daily.yml:311, :315). It calls `python -m scripts.collect --exclude-group asia …`
  (daily.yml:384).
  - That call reaches `scripts/collect.py:194` `("stock_prices", "collectors.sector_holdings", "StockPriceAdapter")`.
  - That adapter is the registered producer of `equity.bars.daily.stocks` (config/dataset_registry.yml:44-47).
- Step `security master — issuer axis nightly refresh (V4-D2B1)`. It runs `python3 scripts/build_security_master.py --nightly`
  (daily.yml:537-541).
- Step `commit market data` (daily.yml:567). It is gated `if: always() && steps.collectors.outcome == 'success'`
  (daily.yml:622) and commits `data: daily collection <UTC date>` (daily.yml:665).
- Step `push market data` (daily.yml:732) rebases onto and publishes to `origin main`.
- `.github/workflows/prophet-rescue.yml` with `scripts/prophet_rescue.py` is the existing bounded redispatcher of `daily`.

No step in this chain calls `account_coverage` or emits a `GenerationRef` (appendix A4).

The owner exists; Data OS generation identity does not yet ride on it. The cycle's return path is the concluded `daily` run
record plus the `data: daily collection <date>` commit on `origin/main`; R03 §1 gives the read commands.

The other recurring units are not the canonical-store owner. `app/deploy/*.timer` (e.g. `macro-live-bars.timer`,
OnCalendar Mon..Fri 13..21:37 UTC at app/deploy/macro-live-bars.timer:5) run live-dashboard lanes. Per
`scripts/vps_live_orchestrator.py:4-5`, those lanes own only short-lived `site/live` products.

`git grep "dataos|data_workspace|price_ladder|selection_cohort|build_baskets" -- app/deploy` hits only the update.sh
restart-fence regexes (:1304, :1504, :2388).

This plan invents no owner, schedule or publisher. It never dispatches, re-runs or cancels `daily`.

### A4. Generation identity (C4)

- `GenerationRef` — `generation_id`, `supersedes` (read_contract.py:220-225); `Dependency.generations` /
  `pinned_generation_id` (read_contract.py:236-237); `select_generation` binds by clock and cutoff (read_contract.py:545);
  `D00.D5` (:92-107) makes a receipt-only change a new generation and keeps superseded generations readable by id (:100).
- The published-data-generation identifier a receipt would carry is `GenerationRef.generation_id` (+ its `supersedes`
  chain). It exists today as contract code only: `git grep "GenerationRef(" -- lib engine scripts app ingest` finds no
  constructor. What exists and is served today: the envelope fields `observed_at`, `implementation_revision`
  (web_workspace.py:123-124) and the per-read `expected_version` stat digest (web_workspace.py:74-77, web_api.py:216-217).
- Price-view identity: `ActionRevisionSet` resolved at an `as_at` instant (lib/dataos/price_views.py:8-19).

### A5. Settings / selection (C5)

No `DATAOS*`, `DATA_OS*`, `MACRO_LIVE_DIR*` or `WORKSPACE_CONFIG*` setting exists in lib/dataos, the CLI, or
app/deploy/update.sh; the only hits are the `load_workspace_config` call sites (scripts/data_workspace.py:25, 77). The
setting that selects what a consumer reads is the host-owned `--config` binding JSON (scripts/data_workspace.py:72,
"host-owned, never a JSON request field", :6) with schema `mastermind.data_workspace_bindings/v1`, fields `registry_path`
and `roots` (web_workspace.py:352-368); a generation within a read is selected by `pinned_generation_id` /
`select_generation` (read_contract.py:237, 545), which no production path passes today.

### A6. §5.2 executed command

`python scripts/data_workspace.py --help` at the pinned commit printed:

```
usage: data_workspace.py [-h] --config CONFIG [--capabilities]
  -h, --help       show this help message and exit
  --config CONFIG  Explicit host-owned binding JSON
  --capabilities
```

Exit 0. No subcommands are listed, so no per-subcommand help exists to run.
