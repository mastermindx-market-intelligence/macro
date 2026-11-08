# Theme scoring + narrative allocation — explicit-input source contract

Date: 2026-11-06.
Mission: <https://github.com/mastermindx-market-intelligence/macro/issues/10779>
Base SHA (macro): `38f2441def30f02cf2accf9ddfbaee334d86e1b5` (`feat(sector): project coherent native brief with canonical tier previews`).
Protected law (Mastermind): `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.
Lane: `macro-always-on-20261106-c3-theme-allocation-01`.

This is the source contract for the two calculation seams the always-on Sector runtime
needs: the **theme scoring desk** (`engine/theme_scoring.py`) and the **narrative
allocation desk** (`engine/narrative_rotation.py`). It states what each seam consumes,
what it produces, what it guarantees, and — explicitly — what it still depends on.

It is a SOURCE contract. Nothing here is a runtime deployment, a publication, a history
effect or a live-writer change.

---

## 1. Why the seam exists

The always-on runtime must refresh the original Sector Brief from ONE accepted
historical snapshot. That requires both desks to be computable over **captured values**
instead of over the repository's ambient state, so that a corrected snapshot, a
different regime read, or a different Sector artifact produces a different — and
correctly dated — result, without either desk re-reading whatever happens to be on
disk at that moment.

The seam is therefore: **acquire once, calculate from the capture**.

---

## 2. The explicit interface

### 2.1 Theme scoring — `engine/theme_scoring.py`

```python
acquire_theme_score_inputs(region: str = "us") -> ThemeScoreInputs | None
compute_theme_intel_core(inputs: ThemeScoreInputs) -> ThemeScoreResult
prepare_theme_basket_rows(panel, *, region, group_flow_cfg, names_sectors) -> tuple
compute_theme_intel(region="us", *, inputs=None, deferred_effects=None) -> dict | None
```

`ThemeScoreInputs` (frozen dataclass — every field is a VALUE, never a loader
callback, never a mutable global):

| field | what it is | where it comes from |
|---|---|---|
| `region` | `"us" \| "china" \| "hk" \| "canada"` | caller |
| `panel` | `{closes, rets, idx, bench, mem, observation, price_resolution}` | `group_flow._setup` (US) / `narrative_rotation._setup` (regions) |
| `basket_rows` | the prepared per-basket rows, in basket order | `prepare_theme_basket_rows` |
| `group_flow_cfg` | the flow-fingerprint parameters | `group_flow._cfg()` (config.yml) |
| `names_sectors` | US GICS names ({} elsewhere) | `equity_factors._names_sectors()` |
| `macro_context` | `{state, sector_rs, display}` | `theme_scoring._macro_context(region)` |
| `signal_calibration` | the backtested signal-precision verdict | `data/strategies/baskets_calibration.json` |
| `regime_snapshot` | the published vol-regime snapshot | `site/vol/regime.json` \| `data/regime/latest.json` |
| `regime_sizing` | the computed vol-regime sizing overlay | `vol_regime.sizing_overlay(...)` |
| `regime_caution_scored` | whether the regime caution is gated on | `data/vol_regime/basket_overlay_gate.json` |
| `prior_sector_text` | **RAW JSON text of the PRIOR committed Sector artifact** (or `None`) | `site/sectordata/sector_central.json` |
| `evaluation_date` | **the EXPLICIT date the Sector freshness rule is measured against** | caller (`date.today()` in the legacy adapter) |
| `earnings_calendar` | ticker → next earnings date (freshness-filtered against the panel session) | `data/earnings/earnings.parquet` |
| `market_concentration` | the concentration panel | `basket_score.market_concentration(region)` |
| `basket_enrichments` | basket id → `{"signals": …, "textures": …}` | `_basket_signals` / `basket_score.theme_textures` |
| `bench_label`, `bench_label_zh` | the region's benchmark labels | `narrative_rotation._region_cfg(region)` |

`ThemeScoreResult` = `{payload: dict | None, deferred_effects: tuple}`.
`deferred_effects` carries the desk's ONE write (the breadth-divergence forward-log
stamp) as data; the core performs none of it.

### 2.2 Narrative allocation — `engine/narrative_rotation.py`

```python
acquire_narrative_allocation_inputs(region: str = "us") -> NarrativeAllocationInputs | None
compute_narrative_rotation_core(inputs: NarrativeAllocationInputs, *, diagnostics=None) -> dict | None
compute_narrative_rotation(region="us", *, inputs=None) -> dict | None
```

`NarrativeAllocationInputs` (frozen dataclass):

| field | what it is | where it comes from |
|---|---|---|
| `region` | the region id | caller |
| `panel` | `{mem, items, closes, rets, idx, bench, bench_ret, bench_close, resid}` (unused loader cfg omitted) | `narrative_rotation._setup(cfg)` |
| `region_meta` | `{id, market_en, market_zh, bench_label, bench_label_zh, phase0_file, phase0_fallback}` | `_region_cfg(region)` (the LOADER callables are deliberately NOT carried) |
| `radar` | the Divergence Radar document ({} when absent) | `site/basketdata/radar.json` |
| `short_interest` | the FINRA snapshot (context only) | `data/finra/short_interest.parquet` |
| `sizing_calibration` | the book-level vol-target sizing verdict | `data/strategies/baskets_calibration.json` |
| `phase0_meta` | the Phase-0 backtest document | `data/strategies/thematic_rotation_phase0*.json` |
| `phase0_fallback_meta` | the Phase-0 fallback document (HK cites the US 27y proxy) | same directory |

### 2.3 The setup seam — `engine/group_flow.py`

`group_flow._setup(region)` keeps its signature and its behaviour and is now exactly
`_build_setup(_acquire_setup(region))`. The acquisition half performs every read of the
group-flow data plane; the build half turns those captured values into the panel and
reads nothing. `narrative_rotation._setup(cfg)` has the same shape.

---

## 3. The purity contract

After `acquire_*` has run:

* the cores read **no file, no config and no provider**, and use **no clock**;
* the cores write **no ledger, no snapshot, no notification and no HTML**;
* the cores do **not mutate** the bundle they were handed;
* the cores do **not** return aliases of the inputs — every payload object is freshly
  built.

`tests/test_theme_allocation_explicit_inputs.py` enforces this with an instrumented
trap over `open` / `os.open` / `Path.read_*` / `Path.write_*` / `pandas.read_*` /
`DataFrame.to_*` / `os.mkdir*` / `os.remove` / `os.rename` / `os.replace` /
`shutil.copy*` / `time.time` / `time.monotonic` / `datetime.datetime.now` /
`datetime.date.today`, INCLUDING the `from datetime import date as _date` alias the
theme desk holds. The trap has its own self-test (`test_the_ambient_trap_actually_
detects_reads_writes_and_clocks`) so it cannot pass vacuously.

The explicit paths suppress legacy stdout/log diagnostics. Theme refusals remain in
`observation_refusals`; the narrative caller can collect extension-anchor and failure
records through its optional `diagnostics` list. Legacy calls keep their diagnostics.

---

## 4. The PRIOR-generation Sector dependency

The MLC-W2b sector-conflict demotion reads the last committed Sector artifact
(`site/sectordata/sector_central.json`) and demotes a buy item whose home sector rates
`Reduce`. In the explicit path this becomes two explicit values:

* `prior_sector_text` — the RAW JSON **text** of the PRIOR generation. It is captured as
  text (not parsed) so a corrupt artifact still raises exactly where it always did and
  the caller's fail-open path restores `buy` and leaves `conflicted` empty.
* `evaluation_date` — the date the 5-calendar-day freshness rule is measured against.
  The core never reads the wall clock.

The rule itself is unchanged: `as_of` older than 5 calendar days, or an absent or
unparseable artifact → fail open (`conflicted` stays empty). Only `Reduce` demotes;
`Cautious` does not; an SMH-proxied basket falls back to XLK.

**The in-progress current Sector output is never substituted.** The demotion reads the
captured prior generation only, so the desk cannot feed on the artifact it is helping
to produce — there is no calculation cycle. The site file is read ONCE, at acquisition,
by the legacy adapter; a runtime that owns its own generation can pass the prior
artifact text directly and never touch the site tree at all.

---

## 5. Unchanged legacy surface

| entry point | change |
|---|---|
| `theme_scoring.compute_theme_intel(region)` | signature, default behaviour and output bytes unchanged. Two optional keyword-only parameters were added (`inputs`, `deferred_effects`) so the same body can serve the explicit path; the incumbent call is untouched. |
| `theme_scoring._apply_sector_conflict_demotion(act_now, site_root)` | unchanged signature and behaviour; the arithmetic moved into `_apply_sector_conflict_demotion_doc`. |
| `theme_scoring._basket_signals(members, level, region, conv_map)` | unchanged signature and behaviour; an optional keyword-only `use_cache` was added. The ambient acquisition passes `False` to bypass this cache only; underlying member-candle and calibration caches remain. This is not snapshot isolation. Runtime callers must supply enrichments from accepted snapshot values. The default preserves incumbent caching. |
| `narrative_rotation.compute_narrative_rotation(region)` | signature, default behaviour and output bytes unchanged; one optional keyword-only `inputs` parameter was added. |
| `narrative_rotation.allocate(preps, ranks, crowd, rot, bench_close)` | unchanged; two optional keyword-only parameters (`crash`, `sizing_calibration`) let an explicit caller hand over the values it has already captured. |
| `narrative_rotation._crash_state(bench_close)` | unchanged signature and behaviour, including the SPY fallback; the arithmetic moved into `_crash_state_from_level`. |
| `narrative_rotation._vol_overlay(top, weights, byid)` | unchanged; an optional `cal` lets an explicit caller supply the captured calibration. |
| `group_flow._setup(region)` | unchanged signature and behaviour. |

No builder, publisher, history, ledger, snapshot, alert or HTML owner was touched, and
no new writer was added.

---

## 6. Transitive dependency audit

### 6.1 Captured at acquisition (the core sees only the captured value)

| dependency | read by | captured as |
|---|---|---|
| `data/baskets/membership.json` | `baskets._membership` | `panel.mem` |
| breadth / smallcap / midcap close caches | `equity_factors._closes` | `panel.closes` |
| `data/baskets/extras.parquet` | `baskets._basket_extras` | `panel.closes` (joined) |
| `store.read("yahoo", "SPY")` / region benchmark | `lib.store.read` | `panel.bench` |
| `config.yml` | `lib.config.load` | `group_flow_cfg`, `bench_label*` |
| `data/<tier>/constituents.parquet` | `equity_factors._names_sectors` | `names_sectors` |
| `data/regime\|bonds\|forex/latest.json` | `theme_scoring._read_json` | `macro_context` |
| `data/strategies/baskets_calibration.json` | `theme_scoring._signal_calibration` | `signal_calibration` |
| `site/vol/regime.json` \| `data/regime/latest.json` | `vol_regime.published_snapshot` | `regime_snapshot` |
| `data/vol_regime/basket_overlay_gate.json` | `vol_regime` | `regime_sizing`, `regime_caution_scored` |
| `site/sectordata/sector_central.json` | `theme_scoring` | `prior_sector_text` |
| `data/earnings/earnings.parquet` | `theme_scoring` | `earnings_calendar` |
| `data/<region>_breadth/breadth.parquet` | `basket_score.market_concentration` | `market_concentration` |
| member OHLCV stores | `basket_index` → `_basket_signals` | `basket_enrichments[bid]["signals"]` |
| `data/regime/cycle_bands_fit.json`, `ladder_risk_calibration.json` | `basket_mtf` → `_basket_signals` | `basket_enrichments[bid]["signals"]` |
| `data/strategies/baskets_calibration.json` (rollover weights + divergence grade) | `basket_score` / `basket_breadth_divergence` → `theme_textures` | `basket_enrichments[bid]["textures"]` |
| `site/basketdata/radar.json` | `theme_validation._read_radar` | `radar` |
| `data/finra/short_interest.parquet` | `narrative_rotation` | `short_interest` |
| `data/strategies/thematic_rotation_phase0*.json` | `narrative_rotation._validation_meta` | `phase0_meta`, `phase0_fallback_meta` |
| wall clock | `date.today()` | `evaluation_date` |

### 6.2 PURE helpers used by the cores (verified: no file, no clock, no write)

`lib.closes_panel.{align_latest_common_observation, population_observation,
resolve_thematic_close_panel}` · `engine.baskets.{_ew_level, _mtd_anchor, _perf}` ·
`engine.group_flow.{prep_group, fingerprint_at, _leadership}` ·
`engine.theme_crowding.basket_crowding` · `engine.extension.extension_signals` (explicit diagnostic mode) ·
`engine.cross_asset._absorption_ratio` · `engine.i18n.tr` ·
`engine.indicators.pct_rank_window` · `engine.basket_tape.basket_tape`.

---

## 7. Residual limitations — stated, not narrowed

1. **The consolidated-candle signals are not a function of the captured panel.**
   `_basket_signals` derives its candle calendar from the member OHLCV store
   (`data/baskets/ohlcv`, `data/stocks`, `data/china_stocks`, `data/yahoo`), not from
   the panel. `basket_mtf` additionally reads the cycle-band and ladder-risk
   calibrations and — for the US reference calendar — `engine.session_anchor`'s
   `date.today()`. All of this happens at ACQUISITION time and is captured, so the core
   is clean; but a refresh that must come from ONE accepted snapshot has to supply the
   signals from that snapshot's own member candles rather than from the live store.
   This is the parent's integration decision, not something this seam can decide.
2. **`basket_score.theme_textures` and `basket_breadth_divergence.breadth_divergence`
   read `data/strategies/baskets_calibration.json` internally.** Those modules are
   outside this lane's write scope. The seam captures their OUTPUT per basket, so the
   core reads nothing — but the capture still depends on that file. A runtime that
   supplies its own textures removes the dependency entirely.
3. **Acquisition-time side effects that are not calculation reads** (all pre-existing):
   `lib.config` imports and applies `<root>/.env` into `os.environ`;
   `lib.store.read` creates `data/<group>/` on a read path;
   `equity_factors._closes` prints `::warning` merge-disclosure lines and mutates a
   module global; `engine.extension.extension_signals` prints `::warning` lines.
4. **Runtime admission remains separate.** The captured predecessor must have an immutable
   generation/hash, must not be future-dated, and must stay fixed across retries. Prepared
   basket rows, benchmark observations and enrichments need the selected snapshot/session
   identity. The legacy narrative setup forward-fills its benchmark; that is not proof of
   an observed target-session benchmark. Legacy acquisition does not establish coherence.
5. **The new suite is not registered in any CI workflow.** Macro CI has no glob
   discovery — every invocation carries an explicit file list — and CI is outside this
   lane's write scope. The parent owns the registration.
6. **This is a source extraction, not a runtime deployment.** No process was started, no
   artifact published, no history advanced, no live writer fenced.

---

## 8. Test receipts

Suite: `tests/test_theme_allocation_explicit_inputs.py` (new, 19 tests) plus the
frozen base references `tests/fixtures/base_theme_scoring_38f2441.py` and
`tests/fixtures/base_narrative_rotation_38f2441.py`.

The frozen references are byte-exact copies of the base modules; the suite asserts their
git blob SHA-1 (`c835735ebf55d37e28506a99d6c4c8248522d579`,
`494a6f00dbbbdaf20e7fc76462170a31b93deae3`) against the base commit's own tree, so the
parity reference cannot drift.

What the suite proves:

* **PARITY** — the theme core and the allocation core produce output byte-identical to
  the ACTUAL base implementation over the same controlled acquired inputs, across: a
  current Sector artifact (the demotion fires), a stale artifact (it does not), the
  vol-regime kill switch, an absent calibration + an empty macro context, and a panel
  with missing members.
* **EXPLICITNESS** — the demotion follows the supplied `evaluation_date` and the
  supplied artifact text; the site file is never consulted by the demotion.
* **PURITY** — no reads, no writes and no clock reads inside either core, after
  acquisition.
* **DEFERRED WRITE** — the core performs no ledger stamp; the legacy adapter still does.
* **ISOLATION** — two bundles in one process cannot influence one another, and changing
  a supplied input (the macro context) changes the observable scores.
* **NO MUTATION** — the bundle is unchanged after a computation.
* **UNCHANGED LEGACY** — the incumbent adapters keep their bytes, their fail-open
  isolation (a corrupt Sector artifact leaves `buy` intact) and their allocation
  contract.

The frozen fixtures are the base implementation itself, so the parity claim does not
depend on the candidate's own code.


## 9. Parent integration and verification — 2026-11-06

The parent integrated immutable worker commit `45a4f141b53ba6069aea340f37cb6655828797cf`
(tree `1a482bb1922d6c75ec8f157b7ce30ba8f96299e8`) via its independently verified
base-to-candidate patch: 275,507 bytes, SHA256
`80d64d6a0594de9faad2f6a3be5b171804125a2983dfd89693a4db43d8c7f3fb`.
That direct diff is a different artifact from the worker's exported patch.

Parent source review repaired the direct explicit-call ledger replay, detached all
returned payload/deferred objects (including global weights), restored the all-refused
`None` return contract, removed loader callbacks from the explicit narrative panel,
normalized explicit absent sizing calibration to an empty value, and made diagnostics
explicit while preserving legacy output and ledger behavior. The shared extension
helper retains its default diagnostics and offers anchor receipts without stdout.

The focused suite passed **29 tests** on the integrated parent source. This includes
the original frozen-base parity cases and 10 parent regressions for direct calls,
all-refused data, returned-object mutation, no ambient calibration fallback, value-only
panels, and quiet extension provenance. Provider exclusion is now exercised separately
by socket/requests traps; the original file/clock trap alone did not prove it. Six
pre-existing pytest temporary-directory cleanup warnings remain. Exact local receipt:
`/tmp/mmx-theme-parent-repair-tests-20261106.log`.

This source foundation does not activate the runtime. The accepted-snapshot enrichment
path still needs explicit member OHLCV, session references, fitted cycle/risk bands and
one captured calibration document for texture/divergence weights and displayed grade.
Clearing process-global caches is not an allowed substitute. Source/basis/session and
predecessor admission, scoped CI registration, production publication and beta proof
remain open.

Final combined parent verification: **267 passed, 17 skipped, 6 warnings** across the
explicit-input suite and the relevant extension, theme, narrative, group-flow and
basket/context suites. The skipped cases retain their existing missing-data conditions.
One source-location assertion introduced by the earlier basket extraction was replaced
with a real output regression: a member leading the latest day must still rank behind
the twenty-session leader. Both displayed fast windows remain required.
Receipt: `/tmp/mmx-theme-parent-final-20261106.log`; `git diff --check` passed.
