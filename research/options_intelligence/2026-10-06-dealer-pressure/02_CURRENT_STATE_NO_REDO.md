# Mastermind source census and integration boundaries

**Research date:** 2026-10-06. **Scope:** read-only source/contract and adjacent-owner census for the Intraday Dealer Pressure, LOD/HOD, EOD and Closing-Pressure commission. This report identifies reuse and missing seams. It is not a second masterplan, deployment report or empirical qualification.

**Frozen source:** Macro `c9631f8b2469587dec643bec94b16e77c09ef511`; Terminal `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`. The protected Mastermind procedure pin `a6d40ff648671b03bd4d829d84dd066b58ea8c3f` is handled by the parent commission. All 18 mandatory Macro corpus files were consumed. Additional exact source files and ten relevant current PR metadata records were inspected. Source IDs and local hashes are recorded in `evidence/sources_internal.json`.

## 1. Findings that change the implementation brief

Mastermind already owns the expensive foundations: option source adapters and canonical historical storage, live Flow coalescing and publication, vectorized Greeks, GEX/VEX/CEX, conditional Greek scenario fields, chain eligibility packets, existing exposure/structure views, shared quote authority, and evaluation/lifecycle owners. The frontier remains conditional inventory reconstruction, endpoint hedge repricing, eligible executable-liquidity comparison, auction measurement and prospective conditional-outcome evaluation.

Several criticisms in the October 3 source census are now stale. They must not become new work items:

| Subject | Current evidence | Consequence |
|---|---|---|
| Gamma regime versus flip | `gex_engine._gamma_flip` determines regime from repriced net gamma at actual spot; `_sampled_crossings` explicitly reports finite-grid roots and handles zero plateaus. [I11] | Reuse the correction. A nearest flip is not a universal sign boundary or certified exhaustive root set. |
| Future spot × time field | Macro #7306 merged October 4; `options_scenario_surface.build_scenario_surface` is present at the frozen pin. Mixed missing/known source clocks no longer bypass future-clock rejection. [I23] [IPR7306] | Do not rebuild the typed scenario field. Extend its economic scope only after qualification. |
| Terminal strike profile semantics | Current `marketStructure.hedgeProfile` reports snapshot strike sensitivity and known/missing/input row completeness. Its comments reject interpretation as a spot path or whole-book transaction sequence. [I50] | Do not repeat the old “fix profile to be a subtotal” task. Existing approximation/completeness gaps elsewhere remain. |
| Intraday chain storage | `chain_snapshot_poller` and `options_structure_intraday` already own per-root/session chain, prior-OI and bucket-receipt artifacts. [I27] [I28] [I29] | No second chain snapshot store or chain universe. |
| Impossible darkpool participation | Macro #7990 is the open carrier; #7901 is closed without merge. [IPR7990] [IPR7901] | Coordinate with #7990 rather than write a parallel quarantine. |
| Futures tape | Macro #8451 is an open ES-first Data OS proposal. Existing Massive futures re-probe #7326 is adjacent. [IPR8451] [IS01] | Existing ownership does not prove entitlement, executable collection or data acceptance. |
| Greek expiry/topology/UI | Macro #7327 already proposes expiry VEX/CEX; #7322 owns topology. Terminal #640/#661 own scenario contract/overlay preparation, #768 unknown-cell exposure lenses, #769 exact-expiry prototype. [IPR7327] [IS01] [IPR640] [IPR661] [IPR768] [IPR769] | Future slice should attach to these contracts and avoid duplicate carriers. |

A source file can be implemented while its runtime publication, current entitlement, capture continuity and consumer acceptance remain unproved. No live source or credential was accessed in this census. Repository fixtures, historical receipts, open PRs, deployed-owner statements and code are classified separately throughout.

## 2. Canonical sources and durable storage

### ThetaData: the option source seam

`collectors/thetadata.py` implements `trade_quote`, `bulk_trade_quote`, `bulk_trade_quote_day`, EOD, OI, Greeks and snapshot methods. Its trade-quote normalization carries contract identity, trade and quote timestamps, sequence, trade exchange, condition and extended-condition fields, BBO prices/sizes/exchanges/conditions. These fields are useful raw evidence; their meaning remains the vendor's documented clock/condition meaning. A field named trade timestamp is not automatically an exchange timestamp, SIP receipt or Mastermind known-at clock. [I14]

The broad adapter does not prove all downstream artifacts retain all source fields. Its EOD normalization reduces some last-trade/created information to a date; OI is effectively a vintage date. Greek normalization does not preserve all upstream model/underlying-clock provenance. A historical file reconstructed today cannot acquire an original publication receipt by renaming its build time. The per-expiry bulk fallback can return a partially covered root, so an inventory study needs a source completion denominator independent of the rows that survived parsing. [I14]

`engine/thetadata_store.py` is the canonical reader/resolver. `resolve_thetadata_store`/`store_root` choose the authorized existing store; `_classify_store` performs a bounded three-valued probe. A probe that times out is uncertainty, not an empty or healthy store. `oi_for_date` uses narrow date projection; `chain` preserves the prior-session OI law; `doi_series` and EOD date/history readers provide existing reconstruction seams. The tier layout is:

- `{THETADATA_STORE}/eod/{ROOT}/{YYYY}.parquet`
- `{THETADATA_STORE}/oi/{ROOT}/{YYYY}.parquet`
- `{THETADATA_STORE}/greeks/{ROOT}/{YYYY}.parquet`

The default configured data root is `data/thetadata_eod`, with existing fallback/resolver policy. This is not an instruction to connect to any path. [I19]

Commission 15 records historical coverage acceptance and a later drained-store/false-healthy-manifest incident. Neither the historical favorable ratio nor a committed stub/current JSON is a fresh inventory of the private canonical store. The correct next qualification is through its incumbent owner, not a replacement archive. [I08] [I09] [I19]

### Intraday chain and contract eligibility

`scripts/chain_snapshot_poller.py` already owns private `data/chain_snapshots/{ROOT}/{SESSION}.parquet`, `{SESSION}_oi.parquet` and `_bucket_receipts/{SESSION}.jsonl`. `scripts/build_options_structure_intraday.py` consumes the incumbent source/completion seam. `engine/options_structure_intraday.py::build_packet` emits descriptive U-CHAIN eligibility with exact root, expiry/right/strike identity, quote state, source clocks, fixed prior-session OI law and all-false authority. `packet_key`, `current_key`, `index_key`, `build_current_pointer` and `build_index` own discovery. The shared index is `options_structure/msc_intraday/index.json`. The live hook treats bucket receipts as authority; standalone compatibility metadata is a distinct mode. [I27] [I28] [I29] [I30]

The focused quote runbook defines its dependent qualification and receipts; it is not a reason to seed another contract universe. Before a dealer-state consumer trusts a bucket, it must qualify the existing receipt/completeness contract and its natural publication. Source implementation alone does not establish that every expected root/bucket is currently present. [I30] [I56]

## 3. Live Flow: exact strengths and remaining epistemic gap

### Source sample and event grain

`engine/live_flow.py::process_batch` uses explicit session/batch clocks, session/root/contract sequence deduplication and the existing day-state schema. It measures source evidence before soft sign filtering. `_coalesce_batch` and `_coalesce_nbbo_microstructure` aggregate a poll batch by contract; the emitted event is not an atomic print, parent order or complete package. Notable-event thresholds and display/feed truncation are distinct from all-source accumulators. [I13]

The measured block `options.trade_nbbo_microstructure/v1` retains source versus valid counts and premium denominators, bid/ask/inside/outside quote location, spread, quote age and displayed-size summaries. Current eligibility requires finite positive trade price/size and bid, ask strictly above bid, and finite nonnegative quote age. It does **not** itself require a bounded maximum quote age, strictly positive displayed sizes or condition-code qualification. That is an exact current-law observation, not a claim that the implementation is broken for its declared descriptive purpose. [I13]

Quote-location shares are premium-weighted within covered retained prints. `aggression_share` is ask share plus bid share; balance is their difference. These are execution-location measurements. They cannot establish the beneficial participant, customer/dealer classification, open versus close, parent order, hedge motive or inventory ownership. Coverage is conditional on the retained source sample, not proof of capture continuity or national market completeness. [I13] [I08]

`_sign_batch` delegates soft signing to `engine/flow_signing.py::quote_rule_sign`. Signing and microstructure coverage are separate laws; the sign helper is not automatically governed by all clock/condition constraints needed for a new inventory experiment. The standard premium arithmetic currently uses price × size × 100. A futures/adjusted-option expansion must supply actual contract economics or exclude ineligible contracts. [I13] [I31]

### Existing single publisher and what it does not retain

`scripts/live_flow_poller.py` owns fetching, processing, staging and publication. Its `_stage_raw_events` name does not make the staged object an atomic raw market tape: the source passed through Flow event coalescing. Its WAL, learning-stage drains and source-generation receipts are incumbent mechanisms. The documented historical quarantine of a previous WAL must not be cleared or used as a pretext to recollect unchanged proof. [I25] [I09]

The current private output root is `data/live_flow_out`; existing public objects include `live_flow/feed_current.json`, `heat_current.json`, `tide_current.json`, `dte_tide_current.json` and `tickers/{ROOT}.json`. `scripts/build_flow_surface.py` stages observed strike × session-time snapshots under `live_flow/surface/{ROOT}/{SESSION}/{STAMP}.json` with indexes and date discovery. Its ephemeral quote taps are not serialized as complete historical day-state source tape. [I25] [I26]

Consequently a dynamic dealer inventory study cannot reconstruct an atomic, full-population signed trade ledger from the capped notable feed or aggregate tide. It must request a bounded, causal projection from the current source/capture owner, preserving corrections and completeness. That is a seam to qualify, not permission for a new publisher or collection daemon.

## 4. Greek, exposure and scenario reuse

| Existing owner | Implemented capability at the pin | Qualification boundary |
|---|---|---|
| `engine/intraday_greeks.py::bs_greeks_vec`, `bs_price`, `implied_vol_vec`, `parity_spot`, `compute_greek_grids` | Vectorized pricing/IV/Greek primitives and chain-grid calculation. [I22] | Declared pricing convention; not universal American exercise or heterogeneous futures valuation. |
| `engine/exposure_math.py::dealer_exposures` | Central dollar exposure conversion. [I21] | Retain units, sign, multiplier and time/vol scaling. |
| `engine/gex_engine.py::compute_gex`, `gamma_profile`, `_gamma_flip`, `_repriced_net` | GEX/VEX/CEX, spot sweep, flip/regime, gross gamma magnets, charm anchor and related summary diagnostics. [I11] | Call-positive/put-negative is an inventory assumption. Gross strike masses do not identify executable support/resistance. |
| `engine/options_hub.py::compute_gex`, `_flip_and_profile` | Existing hub distribution and delegation to the canonical flip/profile machinery. [I20] | By-strike/by-delta Greek fields already exist; by-expiry VEX/CEX is the existing #7327 carrier. |
| `engine/options_scenario_surface.py::build_scenario_surface` | Typed `options.scenario_surface/v1`, spot × future horizon GEX/VEX/CEX grids, optional IV from mids, fixed OI, sticky-strike IV, source clocks and explicit assumptions. [I23] | Modeled conditional field; not observed history, forecast path, dynamically inferred inventory or endpoint hedge-transaction measure. |
| `scripts/build_options_scenario_surface.py` | Pure CLI artifact builder. [I24] | No inspected scheduler, API or current Terminal `flowSource` scenario key. |
| `engine/options_surface.py` | Whole-market snapshot exposure summaries. [I55] | Does not establish intraday signed ownership. |

The scenario builder validates positive numeric inputs, OI dates strictly before observation ET date, known IV/source timestamps not after observation, declared supported volatility convention and horizon eligibility. It reuses `bs_greeks_vec`, and can solve a frozen IV from provided mids with `implied_vol_vec`. These are implemented safeguards, not future work. [I23]

Remaining economic gaps are substantive:

1. Inventory is a fixed unsigned OI snapshot with assumed call/put sign. There is no inspected customer/dealer/open-close posterior update.
2. The output grids are local Greek sensitivities at a future state. They are not the change in fully repriced book delta between states. Full endpoint hedge flow must be calculated from two inventory/book states and a declared hedge instrument.
3. Expired contracts drop from active Greek sums. Cash, share or futures delivery, surviving hedges, assignment and unwind policy are not represented.
4. One scalar multiplier, rate and dividend convention serve the root. It is not a native SPX/SPY/ES or NDX/QQQ/NQ joint valuation model.
5. The numerical sum uses a joint finite gamma/vanna/charm mask. Source input counts and active fractions exist, but per-cell lost-contract counts, Greek-specific coverage and exposure denominator are not fully carried. A partial sum can look like a total unless a consumer reads the limits.
6. Zero crossings are sampled-grid estimates. Interpolation does not certify all continuous roots, topology stability, or a probability of touch/hold/break.
7. Natural publication, current consumer acceptance and out-of-sample forecast utility remain separate from merged source.

Full repricing should therefore use the existing math owner while adding an explicit book-state and endpoint-difference contract. Diagnostics may decompose the result into gamma/vanna/charm approximations, but the approximation residual should be shown near 0DTE. The mathematical cross-product contract is developed separately in `08_CROSS_PRODUCT_EXPOSURE_SPEC.md`.

### Overstrong legacy naming that must not propagate

`engine/options_flow.py::sign_volume` signs option minute bars using that option's own close change and carry-forward tick direction. `measured_dealer` then assumes the dealer is opposite signed customer flow. Its current “MEASURED dealer” documentation overstates what the input establishes. `vol_oi_newpos` uses volume relative to prior OI; repeated turnover makes this insufficient to identify new opening inventory. `oi_positioning` can measure unsigned contract-count changes, while bullish/defensive interpretations remain assumptions. `signing_gate` is an explicit reliability gate; passing a sign gate would not confer participant identity. [I12]

The proper reuse is primitive and provenance reuse, with corrected downstream claim types. It is not adopting the old method name as ground truth or discarding the existing source because an older bar-sign experiment was weak.

## 5. Current Terminal surfaces and precise routing

`terminal/app/(shell)/options/page.tsx` delegates to `terminal/components/workspaces/OptionsWorkspace.tsx`, with the existing access gate. `terminal/lib/optionsIa.ts` defines seven categories. The workspace's legacy URL aliases and redirects remain part of its contract. `terminal/components/OptionsHubView.tsx` owns the current views and lazy component integration. [I45] [I46] [I47] [I59]

| Category | Existing views / URL keys | Placement for future research-qualified information |
|---|---|---|
| Command | desk | Compact state/uncertainty summary after a qualified shared payload exists; no independently computed score. |
| Flow | tape, tide, 0dte, largest, surface, vol/screener, tickers | Source coverage, quote location and conditional position-effect summaries; preserve observed session history versus hypothetical future field. |
| Exposure | gex, positioning, levels | Signed-inventory scenarios, native/common-unit exposures, full endpoint hedge requirements and decomposition. |
| Structure | structure | Conditional interaction nodes and eligible liquidity comparison, tied to the selected root/session. |
| Volatility | volatility | IV assumptions, dynamics and scenario sensitivity. |
| Statistics | current gate with no child view | Prospective touch/hold/break/close calibration only through the existing Statistics owner; #799 is open. |
| Prophet | prophet | Existing independent authority boundary. This research grants no modification. |

This placement is an architectural recommendation, not a new tab taxonomy. The existing Flow surface is observed strike × time history; a future scenario field needs its own typed product kind and visible scenario controls. It cannot silently replace history. [I45] [I46] [I47]

The current source registry `terminal/lib/flowSource.ts::backendPath`/`r2Key` provides these exact routes/objects. “Route” here is the registry's upstream API target, not a claim that every runtime endpoint was called or healthy. [I52]

| Source key | Upstream API target | Existing R2 object |
|---|---|---|
| `tide` | `/api/flow/tide` | `live_flow/tide_current.json` |
| `dte` | `/api/flow/dte` | `live_flow/dte_tide_current.json` |
| `ticker:R` | `/api/flow/ticker/R` | `live_flow/tickers/R.json` |
| `gex:R` | `/api/hub/gex/R` | `options_hub/gex/R.json` |
| `gex_dates:R` | `/api/hub/gex_history/R/dates` | `options_hub/gex_history/R/dates.json` |
| `gex_at:R:D` | `/api/hub/gex_history/R/D` | `options_hub/gex_history/R/D.json` |
| `vol:R` | `/api/hub/vol/R` | `options_hub/vol/R.json` |
| `gexstate:R` | `/api/hub/gexstate/R` | `options_structure/gex_state/R.json` |
| `matrix:R` | `/api/hub/matrix/R` | `options_structure/matrix/R.json` |
| `levels:R` | `/api/hub/levels/R` | `levels/R.json` |
| `surface_at:R:D:T` | `/api/flow/surface/R/D/T` | `live_flow/surface/R/D/T.json` |
| `darkpool` | `/api/hub/darkpool` | `darkpool/eod.json` |
| `options_alpha_candidate_feed` | R2-only source policy | `options_alpha/candidate_feed.json`, coupled receipt `options_alpha/candidate_feed.receipt.json` |

Dated and current surface index/date mappings also exist. There is no explicit scenario-surface key in the inspected registry. Macro `app/hub.py::hub_gex`, `hub_vol`, `_hub_fetch` are existing hub API owners; their cache/stale fallback must not erase payload source age. The candidate feed is deliberately R2-only and must not borrow a different feed as fallback. [I52] [I54]

### Exact Terminal mathematics

`terminal/lib/marketStructure.ts` owns `aggregate`, `hedgeProfile`, `scenarioGrid`, `signSensitivity` and `dailyHedging`; `terminal/components/msc/HedgingCards.tsx` displays them. `GexDeskView.tsx` distinguishes nightly exposure from the selected structure matrix. `StructureView.tsx` is the incumbent structure host. [I48] [I49] [I50] [I51]

The current `hedgeProfile` correction should be retained. Other boundaries remain: `aggregate` sums finite observations without a full per-Greek completeness denominator; `scenarioGrid` uses a local negative gamma/vol/time sensitivity combination and defaults absent vanna/charm to zero while flagging their absence. Those flags are useful but do not make an incomplete zero a measured value. `signSensitivity` varies convention weights; its absolute-tilt “confidence” is a heuristic, not a posterior probability. `dailyHedging` combines a positive spot-sigma, positive IV and time scenario; it is not the expected aggregate trading flow of the day. [I50]

## 6. Darkpool and liquidity-memory ownership

`engine/darkpool_signals.py` is a deterministic **EOD** panel engine. `trailing_z` uses a trailing window with the current point excluded, median/MAD and fallback; `share_break_index`/`usable_history` detect share-unit discontinuities and reset comparison history. `compute_name_metrics`, `venue_split`, `firm_roles`, `market_gauge` and unusualness/streak logic already exist. These are source participation and context features, not per-print absorption measurements. A share discontinuity reset is not a substitute for economically validated corporate-action adjustment. [I32]

`engine/darkpool_context.py` provides the v2 `classify`, `build_snapshot`, `build_context_feed`, `compact_state`, `diff_changes` and `append_ledger` flow. Its classifications are deliberately price-conditioned “heavy into weakness/strength/flat,” avoiding accumulation/distribution certainty. Existing paths include `data/darkpool/context/latest.json` and `data/darkpool/ledger/forward.jsonl`. This append-only context ledger is not a new outcome evaluator. [I33]

`scripts/build_darkpool_desk.py::_load_panel` unions the existing panel and deep panel with collector overlap precedence, and joins consolidated volume/price context. Weekly ATS and non-ATS comparisons use actual matched week. `_emit_pane_json` writes `site/darkpool_eod.json` with `darkpool_eod.v2`, mirrored as `darkpool/eod.json`. Preserve the sealed PSS-AF1 panel and incumbent source rules. [I16] [I34]

`collectors/finra_short_volume.py` and `collectors/finra_ats_transparency.py` are the source owners for distinct FINRA daily short-volume and delayed weekly ATS/non-ATS data. Short volume is not short interest. Weekly delayed venue/firm activity cannot be used as contemporaneously known signed institutional inventory. “Unclassified” firm roles stay unclassified; role heuristics do not identify a print's beneficial owner or motivation. [I35] [I36]

The impossible >100% participation case has its existing #7990 quarantine carrier. It is a priority data-validity boundary, but not an independently unowned task. [IPR7990]

`research/MASSIVE_ADVANCED_INTEGRATION_MASTERPLAN_BY_FABLE.md` already proposes richer tick/off-exchange shelf work. The current `engine` directory census did not expose a corresponding `engine/tick_plane`; the plan is not executable evidence. Existing #8451 creates another specific futures-owner dependency. `engine/options_market_memory_context.py` reads exact external MarketMemory references with zero authority and no nearest-neighbor fallback. It neither owns an episode/campaign lifecycle nor supplies a ready continuous absorption map. [I37] [I44] [IPR8451] [IS03]

Accordingly a new liquidity-memory feature should be a versioned derived observation under existing capture/context owners: price/time location, observed volume, quote response and persistence with source qualification. Calling such a shelf “institutional accumulation,” or treating late-reported/off-exchange volume as causal current resting liquidity, remains unsupported.

## 7. Existing empirical priors and evaluation ownership

### Options Intelligence and near expiry

The October 3 accepted pilot and feature ontology are prior source specifications. Relevant families already include OIF-11/12 gross/scenario gamma, OIF-13 full spot-vol-time hedge stress, OIF-14 vanna, OIF-15 charm, OIF-16 concentration, OIF-17 gamma-node distance, OIF-18 next-OI churn and OIF-29 through 34 near-expiry diagnostics. Extend these identities rather than minting a replacement opaque options score. Accepted engineering specifications do not mean empirical qualification. [I01] [I02] [I03] [I04] [I05]

The accepted P5 v1 population names SPY/QQQ/IWM. SPX/SPXW are an additive contract/population decision requiring registration, not an invisible edit to an already registered hypothesis. The broader near-expiry specification separately calls for product/cohort separation; exact session/expiry clocks and source vintage need to survive this expansion. [I01] [I05]

The OPEX/vanna/charm adjudication is existing internal evidence, not an experiment rerun for this commission. It reports that front-week charm/gamma concentration retained incremental volatility information after controls, with much raw effect explained by size/volatility. Signed charm pressure was refuted under those controls; charm intensity reversed sign. Vanna-relief strengthened as a volatility-compression state, with convention and opposite-sign suppression caveats. Pin-like suppression also occurred in non-OPEX placebo states, and the modern air-pocket narrative failed. Root/era distinctions are material. These priors justify controlled extension/falsification and forbid reviving directional charm or special OPEX narratives by mechanical intuition alone. [I15]

### Shared underlying quote evidence

Commission 15 already identifies Terminal's Quote Plane as underlying market-data authority and Macro `app/dossier_quote.py` as a bounded projection, not a store/socket/scheduler. It also distinguishes source timestamps from synthetic fallback/build clocks in existing latest-only live-quote paths. This census did not independently reopen every Quote Plane component; these findings are carried as the accepted, cited Commission 15 owner record, not newly observed complete BBO-history capability. [I08] [I09]

A continuous quote-event/OFI or executable-liquidity denominator needs qualified quote-event evidence from that owner. Trade-sampled option BBO, candle volume, latest-only snapshots and OHLCV CVD cannot supply the missing continuous queue changes.

### Evaluator and lifecycle reuse

`engine/trial_ledger.py::TrialLedger.log_trial`/`log_declared_budget` are existing multiplicity/inspection-budget primitives. Commission 15's three evidence modes—ACTUAL_AS_SEEN, HISTORICAL_RECEIVABILITY and FINAL_VINTAGE—must not be pooled as equivalent. A future study uses matched candidates, explicit feature availability, purged forward outcomes and declared claim families through the incumbent Evaluation OS. [I10] [I42]

`engine/entry_radar/replay` is the existing replay seam. PR0 fixes noninterference, candidate identity, event spool versus single nightly durable writer, source/basis/freshness and outcomes. Its primary research horizon and qledger's registration/grading horizons are separate; do not silently apply a new intraday horizon to an old registered claim. `engine/qledger.py` and `engine/ledger_lane.py::nightly_advance_enabled` are named owners in that contract, not inspected runtime gates in this lane. [I18] [I43]

The OA recovery workstream records merged exact-option evaluator source, episode/campaign work and candidate-engine/publisher work with distinct remaining natural-runtime/integrity/deployment gates. `engine/options_alpha_exact_option_outcome.py` is a pure evaluator; it does not prove executable quote lifecycle capture. `engine/options_nbbo_cohort.py` belongs to a separate MomoEdge benchmark. Generic validated parser/quote/math helpers may be reused; its cohort identity, registries and fixed capture fence should not be imported as the OA lifecycle. `options_alpha_candidate_feed.py` likewise must not become a competing dealer-pressure publication lane. [I38] [I39] [I40] [I41]

Daytrade already owns session VWAP, opening range, session levels, RVOL and a labeled approximate OHLCV CVD with its established opt-in boundary. `terminal/lib/intradayMath.ts` is a current implementation seam. These are appropriate low-cost baselines and contextual controls, not evidence of quote-depth absorption. [I17] [I53]

## 8. Adjacent PR collision register

Statuses were read through GitHub metadata during this census; open heads are evidence snapshots, not merge or deployment claims. Full records and exact heads are in `evidence/sources_internal.json`.

| Repository / PR | Observed state | Relevance |
|---|---|---|
| Macro #7306 | Merged 2026-10-04; merge `98c67b7d2c5b89670b5e915c34dbc17d899e6df7` | Typed conditional Greek field; no-redo source. |
| Macro #7327 | Open draft; `d656e189265d908e34a7299ebbbccc13a031e69b` | Expiry VEX/CEX projection. |
| Macro #8451 | Open; `7cc4dcb78b99a5c3861e25f8ecaf8d380af6bcc0` | ES-first futures Data OS; sources/rights acceptance remain separate. |
| Macro #7990 | Open; `f7bcd3854d8d2d22990282e417941a638e3a7f60` | Darkpool invalid-share quarantine. |
| Macro #7901 | Closed unmerged; `8bfb3410e1a8e75a1dfa061b71abf3d63787caca` | Superseded quarantine carrier. |
| Terminal #640 | Open draft; `df440cac848ffbb973ed6100579f0603ca3c5e19` | Typed scenario surface consumer contract. |
| Terminal #661 | Open draft; `edea69ef044c2581bf38a463d1956cf72295e2ab` | Future scenario overlay primitives. |
| Terminal #768 | Open draft; `bd8c258f89f625a90be687a7df000eeb8e3f67a6` | Unknown-cell source-session exposure lenses. |
| Terminal #769 | Open draft; `5ea5811d0f6279cf8e0d9138df0c7fdda91d62e6` | Exact decimal expiry/reference prototype. |
| Terminal #799 | Open draft; `8b39aa25a88a71ad437a673c87d460b0eed0e027` | Statistics workspace from existing sources. |

Search also surfaced Macro #7322 topology, #7326 entitlement re-probe and #7272 OPEX phase honesty, plus Terminal #723 heatmap companion, #780 volatility truthfulness and #781 payoff planning. Those titles establish nearby ownership leads only; their full latest source/acceptance was not qualified here. Recheck the bounded relevant carrier before implementation, not every unrelated recent commit. [IS01] [IS02]

## 9. What this census establishes, and what it leaves unproved

**Established:** the exact source owners and publication contracts above; the listed current code semantics; the 18-file starting corpus; the meaningful merged-source advances; relevant existing PR collisions; official cross-product specification differences in the companion report.

**Not established:** current account entitlements, completeness or freshness of private historical files, full atomic/corrected tape retention, continuous national NBBO history, current futures/auction feeds, production deployment or natural consumer receipts, dealer inventory truth, a calibrated probability forecast, or incremental trading performance.

The source-grounded next integration can therefore be concrete without granting new authority: an additive, research-only book-state and endpoint-hedge contract reusing the Greek/source owners; source-qualified liquidity/auction inputs through incumbent owners; explicit existing feature/claim identities and lifecycle/evaluation; and existing Exposure/Structure/Statistics surfaces consuming one published derived contract. Root synthesis determines the phased implementation and acceptance sequence.



## Source links

## Final bounded census addendum: existing Exposure Outlook

Native Linear MAS-260, updated September 24 with a September 21 current-frontier section, reports that its **tested GEX predictive hypothesis is closed for promotion** after frozen cross-instrument tests. Exposure remains structural/context information; the current forecasting candidate is a causal price/volatility baseline. This is consequential prior negative evidence. Its summary does not disclose the negative test's exact population, dates, target, score, uncertainty or artifact hash. The nearby 45-session source-quality study and 35 effective SPY donor sessions describe different exercises and must not be assigned to the negative test. This commission did not independently reproduce that result. [M01]

The original remote source carrier is open Macro #7328, branch `claude/mas260-exposure-baseline-20260918`, head `9515f2558a006c913a7c0eb30d966c47fa1a143b`. It already supplies source/price audit and observed-outcome CLI owners, including `engine/exposure_outlook_data.py`, `engine/exposure_outlook_prices.py`, `engine/exposure_outlook_outcomes.py` and `engine/exposure_outlook_research.py`. Local/unpushed later work is separately recorded: a price/volatility shadow generator/writer, strict Terminal consumer and incumbent flow-transport seam. The exact local artifact family is `options_hub/outlook/{ROOT}.json`. The record keeps `can_publish=false` and `r2_published=false`; the shared main-chart overlay and prospective qualification remain pending. These are source-custody and evidence boundaries, not missing modules to rebuild. [M01] [IPR7328]

Any later implementation must first reconcile this existing source operation, local calibration lane and exact consumer contract through their owners. Do not overwrite, repush, recreate or claim acceptance of the unpushed work. Preserve the prior GEX promotion refusal. The new signed-inventory/full-reprice hypotheses differ from that tested static/conditioning claim and require an additive registration, the active price/volatility comparator and their own falsifiable evidence.

For publication of this independently commissioned research package, the principal selected a **supporting research contribution** to the observed native pair `WS:MARKET-OS` / `MAS-260`, with refs-only, research authority and records-only completion. This does not create an implementation successor wave, alter the issue/workstream, replace #7328, release its CI-deferral/hold or authorize any local custody transfer. The research files are isolated under a new descendant of the existing options research directory. [M01] [M02]

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[I01]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/MASTER_PLAN.md
[I02]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/CURRENT_STATE.md
[I03]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/CONTRACTS.md
[I04]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-signal-catalog.md
[I05]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-near-expiry-spec.md
[I08]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/COMMISSION_15_HARDENED_REPORT.md
[I09]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/CURRENT_STATE_AND_HARDENING_LOG.md
[I10]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/VALIDATION_PROTOCOL.md
[I11]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/gex_engine.py
[I12]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_flow.py
[I13]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/live_flow.py
[I14]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/thetadata.py
[I15]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/OPTIONS_OPEX_VANNA_CHARM_ADJUDICATION.md
[I16]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/DARKPOOL_DESK_AUDIT_AND_UPGRADE_2026-08-05.md
[I17]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/DAYTRADE_SUITE_MASTERPLAN_BY_FABLE.md
[I18]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/LIVE_ENTRY_RADAR_PR0_RESEARCH_CONTRACT.md
[I19]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/thetadata_store.py
[I20]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_hub.py
[I21]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/exposure_math.py
[I22]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/intraday_greeks.py
[I23]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_scenario_surface.py
[I24]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_options_scenario_surface.py
[I25]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/live_flow_poller.py
[I26]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_flow_surface.py
[I27]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/chain_snapshot_poller.py
[I28]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_structure_intraday.py
[I29]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_options_structure_intraday.py
[I30]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_estate/OPTIONS_STRUCTURE_INTRADAY_R2_RUNBOOK.md
[I31]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/flow_signing.py
[I32]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/darkpool_signals.py
[I33]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/darkpool_context.py
[I34]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_darkpool_desk.py
[I35]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/finra_short_volume.py
[I36]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/finra_ats_transparency.py
[I37]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/MASSIVE_ADVANCED_INTEGRATION_MASTERPLAN_BY_FABLE.md
[I38]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md
[I39]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_alpha_candidate_feed.py
[I40]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_alpha_exact_option_outcome.py
[I41]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_nbbo_cohort.py
[I42]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/trial_ledger.py
[I43]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/entry_radar/replay/__init__.py
[I44]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_market_memory_context.py
[I45]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/optionsIa.ts
[I46]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/workspaces/OptionsWorkspace.tsx
[I47]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/OptionsHubView.tsx
[I48]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/gexdesk/GexDeskView.tsx
[I49]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/structure/StructureView.tsx
[I50]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/marketStructure.ts
[I51]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/components/msc/HedgingCards.tsx
[I52]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/flowSource.ts
[I53]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/lib/intradayMath.ts
[I54]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/app/hub.py
[I55]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_surface.py
[I56]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_estate/OPTIONS_FOCUSED_QUOTE_R2_RUNBOOK.md
[I59]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ad36a332cd4b53af1d917a94f6fb3a10e27dad84/terminal/app/(shell)/options/page.tsx
[IPR640]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/640
[IPR661]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/661
[IPR7306]: https://github.com/mastermindx-market-intelligence/macro/pull/7306
[IPR7327]: https://github.com/mastermindx-market-intelligence/macro/pull/7327
[IPR7328]: https://github.com/mastermindx-market-intelligence/macro/pull/7328
[IPR768]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/768
[IPR769]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/769
[IPR7901]: https://github.com/mastermindx-market-intelligence/macro/pull/7901
[IPR7990]: https://github.com/mastermindx-market-intelligence/macro/pull/7990
[IPR8451]: https://github.com/mastermindx-market-intelligence/macro/pull/8451
[IS01]: https://github.com/mastermindx-market-intelligence/macro/pulls
[IS02]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/pulls
[IS03]: https://github.com/mastermindx-market-intelligence/macro/tree/c9631f8b2469587dec643bec94b16e77c09ef511/engine
[M01]: https://linear.app/mastermindx/issue/MAS-260/options-exposure-outlook-research-calibrated-forecasts-and-terminal
[M02]: https://github.com/mastermindx-market-intelligence/macro/blob/aafb9e25b0c12390ef99a9b9c4937fa1198b4bf0/agentos/workstreams/WS-MARKET-OS.md
