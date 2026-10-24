# F01-1 — cross-consumer evidence journey (VIEW_ID `f01-journey-v1`)

## Scope

- Start commit (backend generation): `ed1497887c99101bd1b8bc5438e281f02466371b` (= origin/main at packet time).
- Lane branch `lane/dataos-f01-1`; verification only — no production code changed (P2: zero modified paths, four added).
- Subject-file blob pins (step 0.4, asserted at HEAD by `test_j8_backend_pins_match_the_frozen_generations`):
  `engine/price_ladder.py` `095fee9aafa128fae08bfaee07354bfee6c3f979` ·
  `tests/test_price_ladder.py` `da1f0bc19fb1e6c9828c1c055c85ebbd5b804a3b` ·
  `lib/dataos/read_contract.py` `460fc9403c28eefc771710cbd5b2ecd43bedfdd5` ·
  `lib/dataos/web_api.py` `fc35cdec14c1a83752c6c8f095ed0305218ebafc` ·
  `lib/dataos/web_workspace.py` `450c25fc363272cdff1a58889edbd14c29bffb18` ·
  `scripts/data_workspace.py` `f3763471beb4db2174215bdfc57d17c3692d6568` ·
  `engine/basket_membership_pit.py` `5c7ba201d505648365ba40ff88c6901b47aef713` ·
  `tests/test_basket_membership_pit.py` `6da5b38759ad945c5781fff213b9f8a6bcfc8d55`.
- Evidence class: synthetic fixtures through real consumer entrypoints (the C01 seam + the Data
  Workspace inspector in-process and as a CLI subprocess + basket membership/coverage). No market
  data, no credentials, no host secrets, no absolute host paths. Terminal UI cited from PR #996,
  not re-run.

The journey's world: three synthetic tickers — `PLAINCO` (60 sessions from 2026-01-02, no corporate
action), `SPLITCO` (60 sessions, 2-for-1 split effective 2026-02-13, an adjusted `close` column and
a printed `close_raw` column), `GONECO` (a basket member with no stored file) — in one synthetic
store, one US-suite basket (`f01-basket`, snapshot 2026-01-02, membership read 2026-01-15) and one
Data Workspace host binding (`store` → the synthetic store; `registry_path` → the repo's
`config/dataset_registry.yml`). All values are multiples of 1/4, so every comparison is exact
`Fraction` arithmetic. Every result record in the tests carries `VIEW_ID = "f01-journey-v1"`.

## Journey

| VIEW_ID | consumer | exact call | identity seen | value relation | labels seen |
| --- | --- | --- | --- | --- | --- |
| f01-journey-v1 | (a) Terminal seam | `engine.price_ladder.resolve_close_canonical("PLAINCO", view=ReadRequest(CURRENT, ViewContract(purpose="terminal_daily_ohlc", identity={"security_id": "SEC:US-XNYS-PLAINCO", "listing_id": "US-XNYS-PLAINCO", "mic": "XNYS"}, adjustment_reference={"basis": "tradj"})), data_dir=<store>, registry=load_registry(<repo config/dataset_registry.yml>))` | `vendor_symbol="PLAINCO"`, `listing_id="US-XNYS-PLAINCO"` (code `PLAINCO`), `mic="XNYS"`, `registry_row="equity.bars.daily.stocks"`, `vendor="yahoo"` | 60 exact `Fraction` pairs `2026-01-02..2026-03-26`, first `Fraction(100)` | `evidence_mode.basis="tradj"`, readout `vendor-adjusted — not a printed price`, `field_units.share_basis="tradj"`, clock `ingested_at` |
| f01-journey-v1 | (a) Terminal seam (SPLITCO) | same with `"SPLITCO"` | same forms, code `SPLITCO` | 60 exact `Fraction` pairs; adjusted view | same labels; `legacy_defects=()` (no S10 on stocks/close/tradj) |
| f01-journey-v1 | (a) Terminal seam (GONECO) | same with `"GONECO"` | `vendor_symbol="GONECO"`, no registry row | `values is None`, refusal `read_contract.UNBOUND_DEPENDENCY`, coverage `none` | typed refusal, never another ticker's values |
| f01-journey-v1 | (b) inspector in-process | `lib.dataos.web_api.dispatch(ws, {"action": "describe" \| "read", "ref": "store:" + evidence_mode.source_path, "columns": ["__index_level_0__", column], "limit": 200}, config_path=<bindings>)` | `source.relative_path="stocks/PLAINCO.parquet"` → stem `PLAINCO` | EQUALITY as `Fraction` per date — the inspector returns the same float64 the parquet holds; the ladder reads the column unchanged and `_c01_values` converts exactly that float | column names `close` / `close_raw`; `price_basis="PRESERVED_AS_STORED_NOT_REBASED"`; `file_version` statv1 identity |
| f01-journey-v1 | (b) inspector CLI | `scripts/data_workspace.py --config <bindings>` with the same JSON on stdin | identical `relative_path` and `file_version` as in-process | identical rows (FRESH cross-transport agreement) | same envelope, plus `implementation_revision` from git |
| f01-journey-v1 | (c) basket | `engine.basket_membership_pit.members_asof("f01-basket", "2026-01-15", suite="baskets")` and `.coverage("baskets")` | member strings `GONECO`, `PLAINCO`, `SPLITCO` (bare symbols) | `pit=True`, `basis="pit_snapshot"`, snapshot 2026-01-02, 3 rows | membership basis flags ride with the answer |
| f01-journey-v1 | (c) coverage account | `lib.dataos.read_contract.account_coverage(<ViewContract from terminal_daily_ohlc_contract_v1()>, ["PLAINCO","SPLITCO","GONECO"], dispositions)` | members as bare symbols; segments carry `source="data_stocks"`, `basis="tradj"`, `listing_id=<member>` | `requested=3`, `qualified=("PLAINCO","SPLITCO")`, `qualified_fraction=Fraction(2, 3)` | GONECO `MISSING`/`NO_COVERAGE` — kept IN, never dropped, never filled |

## Identity join

The three consumers join on the bare store symbol, and the namespaced Terminal form maps to it
through the code's own identity module — no undeclared mapping is needed:

- the seam's `identity.vendor_symbol` is the bare ticker the store is keyed by;
- `identity.listing_id` (`US-XNYS-<CODE>`) reduces to the same symbol via
  `lib.dataos.identity.parse_listing_key(...).code` (namespace documented by
  `engine.price_ladder.IDENTITY_NAMESPACE_US_LISTING = "US-<MIC>-<CODE>[.N]"`);
- the inspector's file stem and the basket member string are that same bare symbol;
- the registry row itself declares `id_column: ticker`, `id_type: symbol` — "NOT an identity (§D2)".

Verdict: **join succeeds; no FINDING.** Direction note, recorded not scored: the mapping the code
provides is listing→code (parser). The reverse direction (bare symbol → namespaced listing id),
which the C04-era Terminal emitter will need, has no in-repo alias table on main; the seam request
supplies the namespaced id and the seam checks its internal consistency (mic vs listing key) but
does not derive it. That reverse join is part of the U03/U04/C04 dependency-bound legs below.

## Distinct views

`SPLITCO` carries both views in one file: `close` (vendor-adjusted, the seam's declared view) and
`close_raw` (the printed close; a synthetic addition — the committed `data/stocks` layout declares
only `close`).

- Before the split (2026-01-02 .. 2026-02-12, 30 sessions): printed ≠ adjusted on every session.
- Pre-split printed ÷ adjusted = exactly `Fraction(2, 1)` — the 2-for-1 factor and nothing else;
  post-split the ratio is exactly `Fraction(1, 1)` (30 sessions each side).
- Labels present and DIFFERENT per view: seam `evidence_mode.basis="tradj"`; contract readout
  `"vendor-adjusted — not a printed price"` (`CANONICAL_READOUT`, also on
  `field_units.share_basis="tradj"` and in `terminal_daily_ohlc_contract_v1()`); inspector column
  names `close` vs `close_raw`. Raw and total-return numbers are not forced equal (F01.02).
- On the REAL committed store the raw-vs-adjusted comparison is `UNFINISHED`: lack of a raw column
  (`equity.bars.daily.stocks` schema = `{close}` only). The seam's not-a-printed-price label is
  asserted regardless.

## Fresh/stale/partial/denied

Codes per transport (in-process `dispatch` code == CLI envelope `error`):

| leg | request | in-process | CLI |
| --- | --- | --- | --- |
| FRESH | `read store:stocks/PLAINCO.parquet` columns+limit 200 | ok, 60 rows, `next_offset=null` | rc 0, identical rows/`file_version` |
| STALE | same + `expected_version="statv1:000…0"` (64 zeros) | `SOURCE_VERSION_MISMATCH` | `SOURCE_VERSION_MISMATCH` (rc 2, no rows) |
| PARTIAL | coverage account over the basket | `qualified_fraction == Fraction(2, 3) < 1` | n/a (in-process contract) |
| DENIED | `read nosuchroot:x.parquet` | `ROOT_NOT_BOUND` | `ROOT_NOT_BOUND` |

## Census

`journey_f01_census.py` (audit hook installed before any project import; J1–J6 consumer calls
in-process; CLI leg excluded — `scripts/data_workspace.py` spawns `git` for its revision,
pre-existing and disclosed). Paths reduced to classes (store files are store-relative; outside
writes are counted by class only):

```json
{"cli_leg": "excluded: scripts/data_workspace.py spawns git for its implementation revision (pre-existing, disclosed)",
 "journey_calls": {"basket_calls": 2, "describe": 2, "inspector_refusals": 6, "read": 3, "seam_refused": 3, "seam_served": 2},
 "network_modules_imported": [],
 "os_mutations": {"os.mkdir": 0, "os.remove": 0, "os.rename": 0, "os.replace": 0, "os.rmdir": 0, "os.truncate": 0},
 "shutil_events": 0,
 "socket_events": 0,
 "store_changes": [],
 "store_files_after": {"baskets/membership.json": ["ce2a96f9…c51ff0", 1791953738558183374],
                       "baskets/membership_history.parquet": ["bdfa4e95…9d868b", 1791953738565948332],
                       "stocks/PLAINCO.parquet": ["3dae3126…4d9e9e", 1791953738546262759],
                       "stocks/SPLITCO.parquet": ["b2dcf2d8…aa0f42", 1791953738547083822]},
 "store_files_before": {"baskets/membership.json": ["ce2a96f9…c51ff0", 1791953738558183374],
                        "baskets/membership_history.parquet": ["bdfa4e95…9d868b", 1791953738565948332],
                        "stocks/PLAINCO.parquet": ["3dae3126…4d9e9e", 1791953738546262759],
                        "stocks/SPLITCO.parquet": ["b2dcf2d8…aa0f42", 1791953738547083822]},
 "store_unchanged": true,
 "subprocess_popen": 0,
 "view_id": "f01-journey-v1",
 "write_opens_inside_store": 0,
 "write_opens_outside_by_class": {"cache": 0, "other": 0, "tmp": 0}}
```

Zero sockets, zero subprocesses, zero network-module imports, zero filesystem mutations, zero
write-mode opens anywhere (tmp/cache/other all 0), every store file byte-identical with unchanged
`st_mtime_ns`. The fixture's in-root symlink is a link, not a file, and is skipped by the snapshot
walk (its target sits outside the store and never enters any digest).

## Broken links

J6 codes (both transports agree; the leak sweep over every serialized refusal — in-process codes,
CLI envelopes, seam contracts, the read-contract exception — found none of: the absolute `tmp_path`
string, the string `outside`, the sentinel `F01-SECRET-SENTINEL`, any `/`-rooted path):

| broken/unauthorized link | code |
| --- | --- |
| `store:../outside.txt` (sentinel file next to the store) | `PATH_REFUSED` |
| `store:stocks/leak.parquet` (symlink inside the root → the sentinel) | `PATH_OR_SOURCE_REFUSED` |
| `store:missing.parquet` | `SOURCE_NOT_FOUND` |
| `registry:no.such.dataset` | `DATASET_NOT_REGISTERED` |
| seam asked for `GONECO` | `read_contract.UNBOUND_DEPENDENCY`, `values is None`, no legacy series |
| seam REPLAY `output_id="f01-no-such-output"` | `read_contract.NO_RETAINED_OUTPUT`, `legacy is None` (no read at all) |
| `read_contract.replay(request, None)` | `ReadRefusal NO_RETAINED_OUTPUT` (raised, typed) |

The `GONECO` seam refusal names no other ticker and no path; a replay request never returns current
values.

## Generations

- backend = start commit `ed1497887c99101bd1b8bc5438e281f02466371b` + the eight step-0.4 blob pins
  (asserted at HEAD by J8 via `hashlib.sha1(b"blob %d\0" % len(data) + data)`; no git in tests).
- source = the fixture's own digests: `stocks/PLAINCO.parquet`
  `3dae31263e68101151940dc070aae6e132edfebaaa4150d6b8cc04b6504d9e9e`, `stocks/SPLITCO.parquet`
  `b2dcf2d8bae083ccb3a312d4bf2779e003108f6c2382e22fbff0b91ed6aa0f42`, plus the basket
  membership/history files (census `store_files_before`, above). Synthetic only.
- frontend = **Terminal PR #996, deploy `fdc7c7f9`** — the Terminal UI evidence chip's accepted
  production proof, CITED and not re-verified. EN/ZH, themes and widths coverage of the Terminal UI
  is that PR's evidence; this record adds nothing to it. The Terminal JSON producer lives in another
  repository (registry row `terminal.bars.daily.ohlc_json`, producer
  `mastermind-terminal@06a49a6104f6:ingest/build_universe.py::build_ohlc_json`); this lane never
  imports, runs or reimplements it (J8 pins that the producer path is absent from this repo).

## Not covered

- Terminal JSON leg: `UNFINISHED: awaiting C04 LANDED` (the sidecar emitter that carries evidence
  into the Terminal JSON does not exist on main; the Macro-side seam and view contract are what this
  journey proves).
- U03/U04 consumer UI wiring: `UNFINISHED: awaiting U03/U04 LANDED` (no consumer UI exists on main
  to carry the chip; likewise C03, M01 — declared dependencies, absent).
- The browser journey EN/ZH/themes/widths: covered by Terminal PR #996's own evidence, cited above,
  not re-run here.
- A rights-allowed real corpus: not used; synthetic fixtures only. C01/C02-era reads on main.

## Mutation sensitivity

Each mutation was applied alone (≤ 6 changed lines) in a detached worktree at HEAD, the suite run
there, then restored with `git checkout -- lib/ engine/` (all four mutations live under `lib/` or
`engine/`). Killed **4/4**; no survivor.

| id | mutation (file, ≤6 lines) | failing tests |
| --- | --- | --- |
| FM1 | substitution: for a ticker with no stored file, `resolve_close` returns another ticker's `stocks/PLAINCO.parquet` series (`engine/price_ladder.py`, +4) | `test_j6_the_seam_refuses_goneco_without_substitution`, `test_j4_no_member_is_filled_or_substituted`, `test_j8_backend_pins_match_the_frozen_generations` |
| FM2 | path leak: a missing file's refusal code embeds the resolved absolute path (`lib/dataos/web_workspace.py`, +3) | `test_j6_no_refusal_leaks_paths_or_sentinels`, `test_j6_missing_file_and_unknown_dataset_refuse`, `test_j8_backend_pins_match_the_frozen_generations` |
| FM3 | inspection side effect: `DataWorkspace.read` writes a marker next to the source it read (`lib/dataos/web_workspace.py`, +2) | `test_j7_inspection_triggers_nothing`, `test_j8_backend_pins_match_the_frozen_generations` |
| FM4 | coverage drop: `account_coverage` omits MISSING members (`lib/dataos/read_contract.py`, +1; the constructor's never-drop law then refuses the account) | `test_j4_coverage_keeps_goneco_in_the_account`, `test_j4_qualified_members_keep_the_seams_provenance`, `test_j5_partial_coverage_is_exactly_two_thirds`, `test_j7_inspection_triggers_nothing`, `test_j8_backend_pins_match_the_frozen_generations` |

`test_j8_backend_pins_match_the_frozen_generations` failing in every mutated run is bonus
sensitivity: it hashes the subject files, so any mutation under them is itself detected.

## Findings

none

(No strict-xfail items: every acceptance behaviour asserted in J1–J8 holds on the pinned head, so
no FINDING reproducer is owed. The raw-column absence on the real `data/stocks` store is recorded
under Distinct views / Not covered as UNFINISHED, not as a defect — the seam's label discloses it.)

## Commands

Run from `~/lanes/wt/dataos-f01-1` with `PY=~/lanes/venv/bin/python`; every pytest invocation
prefixed `PYTHONDONTWRITEBYTECODE=1` and suffixed `-q -p no:cacheprovider`. Last lines at the final
HEAD:

- **P1** `PY -m pytest tests/verification/test_journey_f01.py -q -p no:cacheprovider -rs` — run
  twice, identical both times: `28 passed in 5.8s` (28 items ≥ 24, 0 skipped, 0 xfail — no FINDING).
- **P2** `git diff --name-only <start> HEAD` → exactly the four owned paths
  (`research/data_os_completion/2026-10-13/F01_JOURNEY.md`, `tests/verification/__init__.py`,
  `tests/verification/journey_f01_census.py`, `tests/verification/test_journey_f01.py`);
  `git diff --diff-filter=M --name-only <start> HEAD` → empty.
- **P3** `PY -m py_compile tests/verification/test_journey_f01.py tests/verification/journey_f01_census.py`
  → `compile-ok`.
- **P4** `grep -n "datetime.now\|time\.time\|requests\|urllib\|socket\|subprocess\|open(" <the two
  files>` — every hit explained: `subprocess` is the CLI transport leg plus the census launcher;
  `socket`/`subprocess.Popen`/`requests` appear only as audit-hook counter names and the watched
  network-module name list; no `open(`, no `datetime.now`, no `time.time`, no `urllib` in either
  file; all writes go to `tmp_path` only.
- **P5** `PY scripts/check_contract_delta.py --base ed1497887c99101bd1b8bc5438e281f02466371b` —
  `::error title=contract-delta::tests/verification/test_journey_f01.py is a new pytest suite named
  by no run: step in any workflow — wire it into the job that owns its subject in
  .github/ci/legacy-jobs.yml, or add a reasoned row to config/unrun_test_waivers.yml` /
  `contract-delta: 1 introduced, 0 inherited (base ed1497887c99)`. The introduced finding naming
  the unwired suite is EXPECTED (the orchestrator applies the CI wiring patch); running it needed a
  full worktree checkout (`scripts/worktree_sparse.py full`, this worktree only, fully offline —
  all 118,145 HEAD blobs already local).
- **P6** mutation sensitivity, above: killed 4/4
  (`git worktree add --detach ~/lanes/wt/dataos-f01-1-mut HEAD`, one mutation at a time, suite run,
  `git checkout -- lib/ engine/`, `git worktree remove --force ~/lanes/wt/dataos-f01-1-mut`).
