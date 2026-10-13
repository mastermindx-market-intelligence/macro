# R00 — dataset-registry declarations for the three D00.D6 consumers

**Lane:** `O2-R00` (run `dataos-o2-r00-1`) · **Programme:** DATA-OS-COMPLETION ·
**Base:** `origin/main` @ `f30746d115` (2026-10-13) · **Date:** 2026-10-13
**Binding semantics:** `D00_SEMANTIC_DECISIONS.md` (D00.D1–D00.D6, D00.01), frozen v1.

## What this is

The registry — not a directory name, not a licensing label — now answers, for the
three frozen consumers of D00.D6, which dataset each consumes, who produces it, on
which price basis, over which population, on which clocks, and under which
separately-stated rights. Five OPTIONAL fields were added to
`lib/dataos/registry.py::DatasetContract` (+ their validation), the consumer rows
were declared in `config/dataset_registry.yml` (47 → 51 rows), and
`tests/test_dataos_registry_consumers.py` pins both the real declarations and
every discriminating counterexample. No second registry, store, auth or publisher
was created (R00.03); every pre-existing row keeps its meaning and bytes (R00.04).

## The additive schema (frozen; validated ONLY when present)

| field | form | validation (violation classes) |
|---|---|---|
| `basis` | one of `raw \| sadj \| tradj \| not_applicable` | value outside the vocabulary; disagreement with ANY schema column carrying its own `basis:`; `not_applicable` while some column carries a basis |
| `population` | `{market: str, venues: [MIC…], universe: str}` | keys must be exactly the three (all required when present); `market`/`universe` non-empty strings; `venues` non-empty list of 4-letter uppercase MICs |
| `clocks` | non-empty list ⊆ `{published_at, ingested_at, derived}` | empty list; entry outside the vocabulary (`derived` = a DERIVED profile carries no clock of its own, D00.D1) |
| `rights` | exactly `purchase_access`, `internal_computation`, `redistribution` (+ optional `evidence:` right → pointer), each `granted \| not_granted \| unverified` | unknown/missing key; value outside the vocabulary; `granted` without evidence; evidence not of the form `DEC:<KEY>` / `DSC:<KEY>` / a `docs/` `research/` `agentos/` path (optional `#anchor`). A `data/` path, a directory, a URL or the row's own `licensing:` label is NOT evidence (R00.02). Rights never imply each other (K01.02) |
| `point_in_time_corporate_actions` | bool | `RegistryError` at load when present and not a bool — `bool("false")` is `True`, so a truthiness coercion would invert the author's meaning |

Error style follows the module's frozen contract: value-level violations are
REPORTED by `validate_registry` (report-not-raise, exactly like an unknown
`temporal_profile` — one bad row never takes the catalog down); `RegistryError`
is raised by `from_mapping` only for structures no honest contract can hold
(`rights`/`population` not a mapping, non-bool `point_in_time_corporate_actions`).
Absent field = "not declared" (no validation), never "false".

## The consumer matrix

| consumer | dataset_id | producer | storage | basis + evidence | population | clocks | rights + evidence | PIT actions | status | gaps |
|---|---|---|---|---|---|---|---|---|---|---|
| B | `equity.bars.daily.stocks` | `collectors/sector_holdings.py::StockPriceAdapter` (unchanged) | `data/stocks/{ticker}.parquet` (unchanged) | `tradj` — agrees with schema `close basis: tradj` (the §D4 measurement) | **not declared** — market US per D00.D6 stated in `notes`; venues unmeasurable in-repo (yfinance exposes no per-row venue; no `data/` read permitted) → do not guess | `[ingested_at]` — no per-row `published_at` is captured; first system observation is the nightly collect (D00.D1) | purchase `unverified` / computation `unverified` / redistribution `not_granted`; no evidence pointers (none lawful exists) | `false` | PRODUCED (unchanged) | G1, G3 |
| B | `reference.security_master` | `scripts/build_security_master.py` (unchanged) | `data/reference/security_master.parquet` (unchanged) | `not_applicable` — no schema column carries a basis | not declared (US per D00.D6; venues unmeasurable) | not declared | unverified / unverified / not_granted | not declared | PRODUCED (unchanged) | G1 |
| B | `reference.vendor_aliases` | `scripts/build_security_master.py` (unchanged) | `data/reference/vendor_aliases.parquet` (unchanged) | `not_applicable` | not declared (US per D00.D6) | not declared | unverified / unverified / not_granted | not declared | PRODUCED (unchanged) | G1 |
| B | `reference.security_migrations` | `scripts/build_security_master.py` (unchanged) | `data/reference/security_migrations.parquet` (unchanged) | `not_applicable` | not declared (US per D00.D6) | not declared | unverified / unverified / not_granted | not declared | PRODUCED (unchanged) | G1 |
| A | `terminal.bars.daily.ohlc_json` (NEW) | `mastermind-terminal@06a49a6104f6:ingest/build_universe.py::build_ohlc_json` (cross-repo, cited in notes at :54-58, :89-91, :142-156, :211, :376-384, :415-429, :450; sibling producers `ingest/refresh_ohlc.py:40-41` adjusted=true, `ingest/refresh_ohlc_intl.py:86` auto_adjust) | `mastermind-terminal:terminal/public/data/{ticker}.json` + `manifest.json` (`OUT = $TERMINAL_DATA_DIR` override) | `tradj` — ruling: one row label may never claim LESS adjustment than a constituent may carry; mixed per-ticker vendor-adjusted `src` selection; **vendor-adjusted, not house SADJ (D00.D3), not executable** | market US; venues `[XNYS, XNAS, XASE, ARCX]` (Polygon `primary_exchange` MIC map, :89-91/:211); universe = US tickers of the Macro deep store (`equity.bars.daily.stocks`), last `MAX_BARS=3900` (~15y) | `[derived]` (DERIVED has no clock, D00.D1) | unverified / unverified / not_granted | `false` | **PROPOSED** (R00.01: cross-repo producer is not in-repo evidence) | G2, G4, G5 |
| C | `basket.membership.history.baskets` (NEW) | `engine/basket_membership_pit.py::append_all` (driven by `scripts/build_baskets.py`, lane `nightly` per `SUITE_LANE`) | `data/baskets/membership_history.parquet` — append-only, keep-FIRST on `(snapshot_date, basket_id, ticker)` | `not_applicable` — membership, no price column | **not declared** — market US (D00.D6 positive witness) in `notes`; venues not a measurable property of index membership | `[ingested_at]` — snapshot stamped at lane observation; collection receipts carry the collection clock | unverified / unverified / not_granted | `false` | PRODUCED — committed blob at HEAD (last advanced `297b3e6f16` 2026-09-04); `config/dag.yml` wires `scripts.build_baskets --snapshot` | G1, G6 |
| C | `basket.membership.history.baskets_china` (NEW) | `engine/basket_membership_pit.py::append_all` (`scripts/build_baskets_china_ths.py`, lane `asia`) | `data/baskets_china/membership_history.parquet` | `not_applicable` | not declared — market CN, **identity-only** (D00.D6) in `notes` | `[ingested_at]` | unverified / unverified / not_granted | `false` | PRODUCED — committed blob (last advanced `8e8ce5ec7b` 2026-08-06) | G1, G6 |
| C | `basket.membership.history.baskets_china_ths` (NEW) | `engine/basket_membership_pit.py::append_all` (lane `asia`) | `data/baskets_china_ths/membership_history.parquet` | `not_applicable` | not declared — market CN, **identity-only** (D00.D6) | `[ingested_at]` | unverified / unverified / not_granted | `false` | PRODUCED — committed blob (last advanced `63df61aa9a` 2026-10-04) | G1, G6 |

Code consumers added: the DataWorkspace modules (`lib/dataos/web_workspace.py`,
`web_api.py`, `web_readers.py`) on the four B rows; the PIT read seams
(`engine/basket_membership_pit.py::members_asof` / `::read_history`) plus the
measured external readers (`scripts/build_theme_graph.py`,
`engine/theme_graph/materialize.py`,
`scripts/research/freeze_mi_s2_theme_relative_intraday_registration.py`) on the C
rows. `basket_membership_pit.py` itself reads no price store, so no C entry was
added to `equity.bars.daily.stocks` — consumer C's price view IS that row, already
declared. Consumer A's row declares NO `inputs:` edge: the in-repo DAG is in-repo
lineage, a cross-repo build is named in `notes`/`producer`, never graphed as an
in-repo pipeline (the seed fence `consumers_of("equity.bars.daily.stocks") == ()`
stays true and is pinned by test).

## Rule compliance (each rule has a named test)

| rule | test |
|---|---|
| R00.01 PROPOSED ≠ PRODUCED; never claim PRODUCED you cannot evidence | `test_r0001_the_terminal_row_is_proposed_with_a_cross_repo_producer`; C rows cite their git-blob/`config/dag.yml` evidence in `notes` |
| R00.02 no right from a readable directory or a licensing label; granted requires lawful evidence | `test_r0002_redistribution_granted_without_evidence_is_refused`, `…_the_licensing_label_is_not_evidence`, `…_a_data_directory_is_not_evidence`, `…_a_url_is_not_evidence`, `…_a_bare_directory_or_root_only_path_is_not_evidence`, `…_lawful_evidence_forms_are_accepted`, `…_rights_never_imply_each_other`, `…_a_fourth_rights_key_is_refused`, `…_a_missing_rights_key_is_refused`, `…_yes_is_not_a_rights_value`, `…_evidence_must_be_a_mapping_when_present` |
| R00.03 never a second registry/store/auth/publisher | `test_r0003_there_is_still_exactly_one_registry` — the declarations extended the one registry and its one contract class |
| R00.04 the Tiingo contracts stay as measured, byte-unchanged | `test_r0004_the_tiingo_rows_are_exactly_the_measured_twenty_four` (exactly the 24 ids, 20 PROPOSED / 4 PRODUCED, none carries an R00 field); byte-discipline of the diff is checked by the operator |

## Evidence

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dataos_registry.py tests/test_dataos_registry_consumers.py -q -p no:cacheprovider` → **72 passed**.
- §6: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dataos_*.py tests/test_price_ladder.py -q -p no:cacheprovider` → **965 passed, 4 failed**; all four proven failing identically at pristine base (`git checkout --` of this lane's two modified files, same worktree): two `test_price_ladder.py` real-store controls `[JPM]/[KO]` (pinned last-close literals vs the advanced store) and two `test_dataos_security_master.py` gates (`company_intelligence.issuer_disclosure_generations` `private:` storage path; rename-map reachability) — pre-existing, not touched by this lane. Before `data/` was materialized (sparse worktree) the same command showed 855 passed / 38 failed / 72 errors, all `data/`-missing artifacts; `scripts/worktree_sparse.py add data` (the repo's sanctioned per-worktree opt-in) resolved them.
- `git diff origin/main..HEAD -- config/dataset_registry.yml` touches only: `equity.bars.daily.stocks` (new keys + one appended `notes` sentence — the spec's "say so in notes" for unmeasurable venues), the three `reference.*` rows (new keys only), and four NEW rows (`terminal.bars.daily.ohlc_json`, `basket.membership.history.{baskets,baskets_china,baskets_china_ths}`). No existing value changed; `updated:` header left untouched per ownership bounds; the 24 `vendor.tiingo.*` rows byte-unchanged.

## Gaps (honest list)

- **G1** — `population` blocks are omitted wherever venues are not measurable in-repo without reading `data/` (all rows except consumer A's): the additive schema honestly requires all three keys when present, so a partial stays in `notes` rather than guessing a MIC list. P01+ may measure venues from the identity seams and add the blocks.
- **G2** — consumer A: per-ticker basis is not declared in the Terminal output (mixed `src` selection deep/polygon/yahoo); the row carries the honest single label `tradj` + the ruling's "vendor-adjusted, not house SADJ (D00.D3), not executable" note.
- **G3** — consumer B: the fetch universe of `data/stocks` includes occasional foreign shares (producer's own session-routing comment); market US is declared per D00.D6, coverage is not asserted per name.
- **G4** — consumer A: venues measured `[XNYS, XNAS, XASE, ARCX]` from the Terminal MIC map; D00.D6 names XNAS/XNYS/ARCX — the XASE difference is recorded here, not silently reconciled.
- **G5** — consumer A facts are the ORCH-2 measured packet cited at `mastermind-terminal@06a49a6104f6:<file>:<line>`; the pinned Terminal commit is absent from the local read-only clone (predates it) and no network fetch is permitted, so the citations were not re-verified locally (file existence of `ingest/build_universe.py` sanity-checked at the local older HEAD).
- **G6** — C rows: advance recency is a cadence-stamp question (content-dedup), not asserted by the rows; `baskets_china` last advanced 2026-08-06 by git history.
- Pre-existing base failures listed under Evidence (not this lane's gaps to fix).

## DEVIATIONS from the packet

- Worktree inherited the shared clone's sparse profile (`research/`, `data/` not materialized); D00 was read via `git show HEAD:…` and this doc added by explicit path; `data/` was later materialized in-worktree via the repo's own `scripts/worktree_sparse.py add data` to obtain the true §6 baseline.
- The packet's counterexample arrow "→ RegistryError" is realized as the module's frozen report-not-raise contract (see "The additive schema" above); `RegistryError` is reserved for unrepresentable structures, matching the existing `identity:`/`schema:` handling and the `temporal_profile` precedent.
