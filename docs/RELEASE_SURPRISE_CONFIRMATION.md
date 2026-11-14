# Macro Surprise and Confirmation Intelligence

**Owner:** MRI / `WS:RATES-INFLATION-COMMAND`, particularly F1 release truth and F6 evaluation. **Authority:** descriptive/shadow only. No output in this extension can score, rank, gate, size, trade, or self-promote a model.

## What is implemented

The extension joins canonical official first-print receipts to separately typed economist-consensus snapshots, preserving when each fact became available. It computes continuous surprises, lagged normalization, and explicitly named CPI/PPI comparisons. Its research adapter evaluates exact-session forward returns, matched event-date baselines, tails, a fixed chronological challenger, and separately captured forward forecasts. It reuses the original MRI publisher, receipt appender, shared statistical primitives, and TrialLedger; there is no new data service, scheduler, queue, execution plane, or promotion authority.

The source entrypoints are `engine/release_surprise_confirmation.py`, `engine/release_surprise_study.py`, `scripts/ingest_release_consensus.py`, and `scripts/research_release_surprise.py`. The prospective append/observation boundary belongs to the existing `scripts/build_release_forecast.py` writer and its existing `data/release_forecast/forward_ledger.jsonl`.

### Actual consumers

| Consumer | Integration | Preserved boundary |
| --- | --- | --- |
| MRI | `release_forecast.v2.surprise_confirmation`; original latest/site copies remain byte-identical | Existing model points, grading and legacy forecasts remain separate |
| Release Radar | Bilingual `Inflation agreement` section, using the existing fetch | Missing/stale/corrupt/rights-limited states are explicit; no trade recommendation |
| Event Windows | Additive `macro_surprise_context` in its existing snapshot | No change to event selection, windows or live risk authority |
| Sector Central | Additive `macro_surprise_context` in its existing publication | No changes to sector scores, order, gating or sizing |
| Prophet native read | Optional `include_macro_context=True` | Default closed response shape and exact candidate bytes/order are unchanged |
| Prophet authenticated HTTP route | Optional `include_macro_context=true` or `false` on `/api/prophet/daily-brief/v1` | Existing authentication and source/pair/selection-receipt pins remain required; unknown grammar is rejected |

The UI is a projection of qualified evidence, not the source of the evidence. It adds no independent fetcher, timer, storage, or action plane. Native disclosure preserves focus and open state during refresh. It uses the canonical `mx-disc` anatomy and existing theme/language tokens.

## Inputs and qualification

Official facts remain `release_actual.v1` under the existing actual owner. This extension does not turn revised history, priors, model estimates, prediction-market prices, or a vendor infographic into first-print consensus evidence. Native official targets currently include CPI, headline final-demand PPI, PCE, NFP and Claims; **core PPI is not a supported canonical target** and is not synthesized.

Economist snapshots live at `data/release_forecast/consensus_snapshots.jsonl`. Each `release_consensus.v1` record contains:

- `baseline_kind=economist_consensus`, exact `release`, reference `period`, `exact_target_id`, `unit`, and finite numerical `value`;
- `source_id`, an HTTPS source URL without credentials/query secrets, source SHA-256, and a rights reference;
- explicit offset-aware `forecast_at`, `observed_at`, `recorded_at`, and `release_at` timestamps;
- qualified `rights`, explicit `use_scopes`, and optional immutable correction lineage.

The capture CLI owns observation/record timestamps. An imported record cannot supply an earlier possession time. A snapshot captured at or after the release is retained honestly but cannot support a reconstructed pre-release signal. A backfilled vendor archive needs a separately qualified vintage-verification route before it can be used as historical knowledge; none is silently assumed here.

A rights string is not a license grant. The data owner must qualify the referenced rights and source. Unknown rights permit no research/display use, and `display_only` cannot authorize `internal_research`. Research rights do not imply display rights. Derived normalization is redacted when any contributing history lacks derived-display permission. Raw actual/consensus values require separate raw-display scope. Do not place credentials or private license text in the output artifact.

Exact target, unit, period and release timestamp must match. Multiple poll providers require an explicit source selection; the engine does not average incomparable baselines. Conflicting first prints, conflicting poll snapshots, unknown clocks, future information and overly late actual captures are excluded with named reasons. Malformed input is not converted to an empty successful history.

## Temporal and statistical protocol v1

The hypothesis family is explicit: headline CPI + headline PPI and core CPI + headline PPI; SPY, QQQ and IWM; 1, 5, 10 and 20 exchange sessions; four quadrants, agreement, disagreement and the agreement-minus-disagreement comparison. The default family therefore contains **168 cells**, including unavailable cells. Separate individual-release outcomes are descriptive and keep their original individual clocks; they are not opportunistically added to that inferential family.

A paired event exists only when both same-reference-month reports are known. Its clock is the later component clock. Equal-to-forecast prints remain neutral and are not forced into agreement/disagreement. Previous complete months become historical context when a newer incomplete period exists.

The research entry is the first authoritative exchange-session close **strictly after** the event is known. The horizon counts subsequent exchange sessions from that entry. Missing prices never shorten the horizon. Calendar coverage, price adjustment basis, source references and availability times are mandatory. A closing-price model does not pretend to test next-open execution or intraday drawdown.

Surprises are continuous in percentage points or the official target unit. Standardization uses only prior available observations of the same target and poll provider, with a 12-observation minimum and 60-observation trailing maximum. Current/future prints do not fit their own scale.

Matrix baselines use all paired event months on the same entry convention, not zero return. Outputs include conditional and baseline means, gap, median, win rate, worst observation, lower-decile mean and closing-price drawdown. Wilson win-rate intervals are explicitly descriptive and not adjusted for temporal dependence. The bootstrap intervals describe uncertainty in a **mean gap**, not the return distribution of the next trade.

The implementation uses the incumbent stationary bootstrap with one complete reference-month calendar shared across assets/variants; missing months remain missing. Defaults are 800 draws, mean block length three months, seed seven and at least 30 observations in both relevant groups. Centered-null bootstrap p-values are approximate exploratory diagnostics. Holm adjustment covers the declared within-run family, including missing cells. The existing TrialLedger records the declared configuration before return evaluation; its observed configuration count also appears as a conservative cross-run multiplier. **Neither adjustment is a guarantee against unlogged research, data-universe selection, repeated sequential looks, nonstationarity, or unqualified source data.** Block-length/regime sensitivity must be tested and logged before promotion.

The challenger uses a fixed ridge model with alpha 10, a minimum 60 mature training observations and a 24-hour calendar embargo after labels become known. It compares against same-training-set unconditional and shrunk-quadrant baselines. Scaling is fitted on training data only. Current target outcomes are not inputs to prediction. Optional regime features must come from existing owners with observed/known clocks and source references; unavailable or conflicting features cause abstention, not zero imputation.

Cost assumptions are explicit basis-point scenarios. Forecast grading requires the same cost basis. These event studies are **not** an investable portfolio backtest: overlapping positions, capital utilization, cash yield, spread, slippage and execution feasibility require separate qualification. Three correlated ETFs do not create three independent histories of inflation releases.

## Forward capture is separate from reconstruction

`prepare_shadow_proposals` can compute a current-event forecast without an outcome label. It returns `prepared_not_captured`, never prospective proof. Capture is explicit opt-in through the original MRI writer, not a new schedule or automatic activation.

The writer uses its actual UTC clock, an inode-bound nonblocking file lock, immutable identities, flush/fsync and readback. It first stores the forecast, then stores a distinct observation receipt showing when durable possession was observed. Capture must begin more than 60 seconds before the proposed entry, and the durability observation must still precede entry. A late capture cannot move entry to a later close or backdate possession. Synthetic datasets cannot activate capture through the CLI.

An existing forecast is keep-first even when a later model run changes its value. A missing observation receipt stays unqualified; retry does not manufacture historical evidence. An interrupted append reports uncertainty and requires reconciliation against the **original** ledger before any replay or reroute. Read-only evaluation grades only linked, intact, qualified pre-entry captures with available labels and matching entry/cost basis.

This is local publisher capture evidence, **not independent third-party timestamp attestation**, accepted model validation, or permission to trade. Future performance cannot be manufactured by running synthetic tests today.

## Operator entrypoints

Validate an already authorized poll export without mutation:

```sh
python scripts/ingest_release_consensus.py --source /path/to/authorized-consensus.jsonl --root /path/to/macro
```

Append only after source/rights qualification by the existing owner:

```sh
python scripts/ingest_release_consensus.py --source /path/to/authorized-consensus.jsonl --root /path/to/macro --commit
```

Run reproducible research using a source-bound dataset and the existing research owner's trial ledger:

```sh
python scripts/research_release_surprise.py --root /path/to/macro \
  --dataset /path/to/qualified-dataset.json --asof 2026-11-13T20:00:00Z \
  --trial-ledger /path/to/existing-owner-trials.jsonl \
  --output /path/to/new-immutable-study.json --cost-bps 5
```

The date above is an example, not a command to backdate a current run. The dataset schema is `release_surprise_dataset.v1`: qualified calendar/price/rights references, explicit evidence class and research scope, authoritative `session_closes`, adjusted `bars`, and optional source-bound `regime_observations`. Each bar has `symbol`, `close_at`, `known_at`, positive `close`, `basis=total_return_adjusted_close`, and `source_ref`.

Add `--capture-shadow` only for an authorized current capture using qualified non-synthetic inputs. It writes to the original MRI forward ledger. It cannot qualify a historical entry that has already passed. Without that flag the study never writes forward forecasts. Output files are exclusive-create; rerunning a trial does not silently overwrite an earlier report.

## Honest acceptance and remaining data boundary

Engineering tests demonstrate contracts and consumer behavior, not historical alpha. Full independent reproduction of Alphatica requires its actual event universe, forecast vintages, target definitions, exclusions and prices; those were not supplied. The motivating graphic's QQQ value is **+0.62%**, making the inferred missing cell approximately **+1.05%**, not the earlier misread +3.60%. That inference from rounded source figures is not a replicated return series.

The inspected incumbent MRI producer reports street consensus unavailable, and the bounded collector/source search did not establish a qualified macro-consensus feed. Missing sparse-checkout files are not proof that all production data is absent. The first production data gate is a qualified existing provider/archive, rights evidence, exact target mapping, original capture/vintage proof, and replayable coverage. No purchase, credential change or new provider enrollment is authorized by this document.

A live-data backtest, unseen chronological assessment and a genuine forward record remain separate scientific acceptance stages. Promotion requires the existing research/strategy owner to approve predeclared incremental-value/risk criteria using actual evidence. This component never flips that authority itself. Until then the safe consumer output is descriptive context or an explicit unavailability state.

## Evidence and references

The implementation plan and evolving proof are in `research/release_forecast/MACRO_SURPRISE_CONFIRMATION_MASTERPLAN_2026-11-13.md`. Focused tests are `tests/test_release_surprise_*.py`, plus affected MRI, Prophet and Sector Central suites. Component browser evidence is under `research/release_forecast/msc_evidence_20261113/`; it is explicitly synthetic UI proof, not production-page or trading validation.

Statistical interpretation reference: ASA President's Task Force, *Statement on Statistical Significance and Replicability* (2021), paragraphs on uncertainty, selection, multiplicity and practical significance: https://magazine.amstat.org/blog/2021/08/01/task-force-statement-p-value/ (HTML inspected 2026-11-13). The reference supports careful interpretation, not this signal's profitability.

Resampling provenance: Politis and Romano, *The Stationary Bootstrap*, JASA 89(428), 1994, 1303-1313, DOI 10.1080/01621459.1994.10476870. Bibliographic/abstract-level provenance only in this session; full text was not inspected. The implemented primitive is reused from `engine/challenger_spa_comparison.py`, not independently re-derived from an inaccessible article. Financial nonstationarity remains a limitation, not something bootstrap resampling removes.


## Publication and private evidence

`data/release_forecast/consensus_snapshots.jsonl` is the existing MRI private-input
archive, now explicitly gitignored and registered as `gitignored-local`. The ingest
owner keeps its file mode at 0600, including an already-existing archive. Keep
provider input files outside publishable source/data trees; do not force-add the
archive. Source admission, pre-release vintage proof and commercial rights remain
separate from this storage registration.

Research datasets must declare a typed `use_scopes` list. `internal_research` does
not imply `display_derived`. The research report is an internal diagnostic, not a
public export. The existing MRI forward ledger is Git-published, so new forecast
capture requires explicit dataset derived-publication rights and derived rights
for every macro observation actually used by the fit and target. The dataset
rights declaration covers its price/calendar/regime inputs; the incumbent data
owner must qualify that declaration and its `rights_ref`. Missing rights default
to nonpublication. Forecast preparation can still run internally; capture refuses
before writing. No new private/public ledger or publication authority is created.

The original capture writer preflights the complete proposal batch before its
first append. Malformed or unqualified later proposals cannot leave an unreported
partial batch. Actual append/readback interruptions retain the original uncertain
effect and reconciliation rules; caller clocks never replace writer time.


## Historical-source qualification boundary

The live v1 ingestion clock is deliberately the actual local receipt time. A
historical vendor download is not permission to backdate `recorded_at`, and
post-release `LastUpdate` must not be copied into `forecast_at` as though it were
an economist's original estimate timestamp. Archived market availability and our
system's later possession are distinct facts. The live producer remains strict;
qualified retrospective reconstruction must preserve both clocks and remain
separately labeled from actual forward captures.

A concrete candidate for the source-admission lane is Trading Economics' documented
calendar point-in-time method. Its documentation describes original release-time
values; its schema distinguishes economist `Forecast` from provider-model
`TEForecast`. This identifies a possible source, not an admitted dataset, a license,
an authenticated connection, or proof that the desired 2008-2026 target definitions
and original consensus vintages are covered.

Primary documentation inspected 2026-11-13:
- https://docs.tradingeconomics.com/economic_calendar/point-in-time/
- https://docs.tradingeconomics.com/economic_calendar/schema/
- https://docs.tradingeconomics.com/mcp/tools/#get_calendar_point_in_time

Before using an archive, the existing MRI/RIC source owner must resolve access and
internal/derived/raw rights, exact CPI/PPI target and definition-era mapping,
original-forecast versus later revision semantics, release/calendar timezone,
market-availability evidence, current acquisition timestamps and immutable input
receipts. The historic endpoint's date-range parameters alone do not prove an
arbitrary pre-release forecast snapshot. Do not relabel ordinary calendar history
as certified point-in-time history. No provider was activated or purchased by this
change; no historical archive has been admitted, normalized or used for validation.
The current connector catalog search returned no Trading Economics plugin; that
is a bounded catalog result, not proof that no account or integration exists.

This dependency is independent of release of honest unavailable/shadow context.
Do not claim the Alphatica result was reproduced while it remains unresolved.
