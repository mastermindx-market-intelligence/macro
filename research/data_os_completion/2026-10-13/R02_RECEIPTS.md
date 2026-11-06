# R02 — installed / selected / consumed receipts (seat 972d2923, 2026-10-17 13:3xZ–13:4xZ)

Three consumers, three separate receipt sets. Each receipt names its host, interpreter,
digests and envelope fields only — never stored data values, never secrets.
`production_qualification: NOT_ESTABLISHED_BY_THIS_ADAPTER` is the adapter's own
declaration and is reproduced, not upgraded, here. One host binding + one interpreter +
one sample file is one runtime receipt, not all-account adoption (R02.03).

## Consumer B — DataWorkspace canonical read (`scripts/data_workspace.py`)

Host `ubuntu-s-mastermindx` (VPS 146.190.142.17), repo `/opt/macro` HEAD
`83daf2b783ba218c4beed3850b2fc34cc5d139e7` = `origin/main` at 13:23Z (shallow clone;
liveness proven by blob digests, never by ancestry).

### R02.01 INSTALLED (code bytes = origin/main @83daf2b7)

| path | sha256 (VPS) | equals origin/main blob |
|---|---|---|
| `scripts/data_workspace.py` | `8d8bab56c2e74ca6…` | yes |
| `lib/dataos/web_workspace.py` | `4107d80a4daa5d31…` | yes |
| `lib/dataos/web_api.py` | `a59db1f8e1f3bbdd…` | yes |
| `lib/dataos/__init__.py` | `9df67c87bd7f92cc…` | yes |

`python3 scripts/data_workspace.py --help` rc=0; flags exactly `--config CONFIG` + `--capabilities`.
`git status --porcelain -- lib/dataos scripts/data_workspace.py` = 0 lines.
Interpreters: system `/usr/bin/python3` 3.12.3 (PyYAML 6.0.1, **no pyarrow**); production
service venv `/opt/macro/.venv/bin/python` (systemd `ExecStart=/opt/macro/.venv/bin/python
-m scripts.am_edition_live`, `WorkingDirectory=/opt/macro`; pyarrow 24.0.0, pandas 3.0.3).

### R02.02 SELECTED (setting actually present on the host)

- `config/dataset_registry.yml` sha256 `a9ef1c840ba9bb8b…` (96023 B).
- `config/web_data_workspace.studio.json` sha256 `ef90da044c829fb6…` — the committed
  Mac-path example; **no VPS-specific host binding exists on the host**.
- `data/stocks/` = 251 parquet files; `data/stocks/_view_contract.json` ABSENT (expected until
  C04 #9226 lands and the next nightly emits it — that is R03).
- Seat runtime binding = scratch `/tmp/dataos_r02_972d2923/binding.json`, sha256
  `526c118e15c0d606e58da469424bc31196ebf3583fb8a200563aa2f84ea29ca5`, schema
  `mastermind.data_workspace_bindings/v1`, one root `macro_vps_snapshot` → `/opt/macro/data`
  (`evidence_kind: unqualified_snapshot`), `registry_path: /opt/macro/config/dataset_registry.yml`.
  Removed after each run (`scratch_removed: true`, re-verified absent). Nothing written under `/opt/macro`.

### R02.03 CONSUMED (runtime execution; receipts `R02_B_RUNTIME_RECEIPT_venv.json` / `_sys.json`)

Service venv run, started 13:38:55Z, finished 13:38:58Z, every envelope
`schema_version=mastermind.data_workspace/v1`, `implementation_revision=83daf2b783ba218c4beed3850b2fc34cc5d139e7`,
`source_access=read_only`, `production_qualification=NOT_ESTABLISHED_BY_THIS_ADAPTER`:

| run | request | rc | stdout sha256 | key fields |
|---|---|---|---|---|
| capabilities | `--capabilities` | 0 | `e90ece4ebb872372…` | actions = search, browse, describe, read, lab_signals, lab_plan, lab_run, history_dossier, history_transcript, tiingo_compare_statements |
| describe_contract | `registry:equity.bars.daily.stocks` | 0 | `e6aac64d33291ed2…` | L1 PRODUCED, `data/stocks/{ticker}.parquet`, parquet, grain [ticker,date], BARS, total_return, America/New_York, 1d; availability `NOT_ESTABLISHED_BY_DECLARATION` |
| read | `macro_vps_snapshot:stocks/AAPL.parquet` limit 1 | 0 | `41b6588ed103939b…` | file_bytes 457100; file_version `statv1:b29c3bdb770a6a7e…`; result dict rows=1, columns `Date, close, high, low, volume` (no `open`); `price_basis=PRESERVED_AS_STORED_NOT_REBASED`; temporal_caution present; query_receipt_sha256 `6e8c2e6b7fb901e6…` |
| read_expected_version | same + `expected_version` = observed file_version | 0 | `fe18788268cf5919…` | `source_file_version_rechecked: true` (a mismatch would have refused `SOURCE_VERSION_MISMATCH`; the query echo omits `expected_version` by design) |

System-python run (`_sys.json`): capabilities rc=0 (`090183b9…`), describe rc=0 (`399a7419…`),
read rc=2 typed refusal **`DEPENDENCY_UNAVAILABLE`** (`ddfc2df9…`) — pyarrow absent on that
interpreter; the refusal is typed, not a traceback. Both interpreters recorded.

Finding carried to the closeout: the stored AAPL parquet exposes no `open` column through the
read path (columns observed `Date, close, high, low, volume`). Recorded as an observation of
the selected setting, not adjudicated here.

### R02.04 NOT CLAIMED

Unqualified history is never advertised complete; one sample file, one binding, one host.

## Consumer A — Terminal daily OHLC + data-origin readout (Terminal #996, PRODUCTION_PROOF)

- Installed: Terminal build log (`$S/orch/o1/seat/terminal_release/build.log:395,399`, 2026-10-13):
  `new build OK: BUILD_ID=build-TfctsWXpff2fKS sha=fdc7c7f96f56a7b882525de11104acdffe411cd4` and
  `identity verified: intended=fdc7c7f9… marker=fdc7c7f9… BUILD_ID=build-TfctsWXpff2fKS`. The
  identity check is the build script's own SERVER-SIDE marker comparison, not an HTML embed.
- Consumed: the 10-13 anonymous page receipt (`page_20261013.html`, `chunks_20261013.txt`) is preserved.
- 13:4xZ re-read of https://app.mastermind-x.com/ anonymously: `page bytes=98822 html_hits=0`,
  `chunk_hits_total=0 chunks=32` for the sha/BUILD_ID regex — the page never embedded that
  string (0 hits on the preserved 10-13 copy too), so this is NOT a regression signal. The
  JS chunk list differs from 10-13 (32 vs 32 files, 66 diff lines): the Terminal has been
  rebuilt since the #996 release by another lane. Host read 13:5xZ (read-only):
  `/opt/terminal/terminal/.next/BUILD_ID` = `build-TfctsWXpff2fKS` (unchanged), file mtime
  `2026-10-17 12:56:23Z` — a swap performed today by a lane that is not this seat; the
  build id is deterministic and unchanged. The live deployment marker
  `/opt/terminal/terminal/.deployment-id` = `3e6e9591d21b849227de3633b4322d7d3b0d3b37`
  (mtime 12:56:25Z) — a LATER Terminal commit than #996's `fdc7c7f9…`. Ancestry PROVEN on
  the host's full (non-shallow) canonical clone `/opt/terminal/.gitsrc`
  (`mastermindx-market-intelligence/mastermind-terminal`): `git merge-base --is-ancestor
  fdc7c7f9… 3e6e9591…` rc=0, 33 commits ahead; live commit = master
  `3e6e9591 2026-10-17T12:47:33Z test(chart-engine): C01-A03 census follow-ups …`.
  So the production Terminal still carries the #996 consumer-A change.
  #996 stays ACCEPTED-RECEIPT; the seat never redeploys it.
- U01/U02 FILL = `BUILD_ID=build-TfctsWXpff2fKS`, sha `fdc7c7f96f56a7b882525de11104acdffe411cd4`.

## Consumer C — basket membership / price composition

Runtime receipt = R03: the first nightly `daily.yml` (~02:30Z) that commits
`data/stocks/_view_contract.json` after C04 #9226 lands; the seat never dispatches `daily.yml`.
Code side already LANDED: U04 #9241 (`37df30ea4366`) + wire-5 #9555 (in CI).
