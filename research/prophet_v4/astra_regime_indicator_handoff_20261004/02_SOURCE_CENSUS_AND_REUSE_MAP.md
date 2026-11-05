# Source census v2: verified dependencies and existing execution plans

**Audit date:** 2026-10-04. **Purpose:** repair the published handoff's incomplete source navigation, missing dependencies and stale-state assumptions. This is a census of existing implementation and existing plans, not a replacement for the blocked, unpublished chapter 03 or a new execution authority.

The [original census](https://github.com/mastermindx-market-intelligence/macro/blob/b598819bcecc2ef98e5848f473df9b21bd045118/research/prophet_v4/astra_regime_indicator_handoff_20261004/02_SOURCE_CENSUS_AND_REUSE_MAP.md) remains immutable. Its research shelves remain useful; the corrections below take precedence as evidence about what was checked in this audit.

## 1. Exact observations, not assumed current deployment

| Surface | Observation | What it proves |
|---|---|---|
| Protected procedure | Mastermind `d1594f3c7ae750db3f14b4eebf0de3460f84267a`; INDEX blob `4b0189a75d559d963365097485e8509a49c70e23` | Protected master source, compatible bootstrap major 1 / skillpack 1.0.1; not installed runtime parity |
| Product/research source | Macro `02fb67891222f9710c2a16b1fa6feb917996cab7` | Immutable source used for the new document/code reads below |
| Original handoff | Macro `b598819bcecc2ef98e5848f473df9b21bd045118`, PR #8363 | Five published Markdown files; draft and unmerged when audited |
| Terminal | Previously observed master `863f678658e2211b5a48daa99404686dfaa117f2` | Historical navigation only; Terminal was not re-audited in this revision |
| Executive read | Server 1.3.1, generated `2026-10-03T20:45:33Z` | This installed runtime reported read-only mode; not a fleet-wide availability verdict |
| Fabric read | Generated `2026-10-03T20:45:43Z`; observation digest `eb54d17d7ac2147f187325da3a74902f2d9204db7176a90cd1fb0411471660f3` | This arm reported `ceo_submit_armed: false`; root provenance partial/unjoined; no dispatch performed |

Local names are aliases: `/mastermind` is GitHub `mastermindx-market-intelligence/Mastermind` (master); `/macro-main` is `mastermindx-market-intelligence/macro` (main); `/charting-app` is `mastermindx-market-intelligence/mastermind-terminal` (master). Resolve the actual managed workspace and remote before edits. Do not open or reset a historical folder merely because its name resembles an alias.

A read of an old document at new main proves the document exists at new main; it does not update the dates, empirical population or live status described inside it.

## 2. Newly recovered dependencies the first handoff omitted

### 2.1 Temporal Grain Intelligence already owns the central clock-mechanism question

[WS:TEMPORAL-GRAIN-INTELLIGENCE][temporal] separates:

- **G: grain**, the sampling/bar interval;
- **A: anchor/session**, the boundary and included trading sessions;
- **K: kernel memory**, smoothing and effective historical memory;
- **D: data/instrument plane**, feed, instrument, adjustment, venue and futures-roll identity.

This is directly relevant to the claim that 1D, 2D and 3D usefulness changed. A comparison which changes all four cannot attribute its result to timeframe alone.

**Verified stale projection:** the workstream still describes W0 as `awaiting_ci`, but [PR #6790][pr6790] is merged, with merge SHA `db5d20c45db123a2e133d9c1a28387ec9f23a545` and merge time `2026-09-03T09:51:05Z`. The merge is architecture/records proof, not empirical proof, not evidence of W1A execution and not automatic closure of any separately required acceptance.

The existing sequence is W1A exact recipe/parity/mechanical attack -> separately preregistered W1B localization/risk utility -> outcome-blind W2 structure-to-kernel derivation -> W3 instrument-disjoint confirmation -> adjudication. W1A may conclude only ARTIFACT, UNRESOLVED_DATA or MECHANICALLY_SURVIVES. Fewer crosses or smoother lines cannot establish usefulness.

Existing detailed plans, not new proposed files:

- `research/signal_engine/temporal_scale/CHARACTERISTIC_MARKET_TIME_SIGNAL_GRAIN_ARCHITECTURE_FREEZE_2026-09-03.md`
- `docs/superpowers/specs/2026-09-03-characteristic-market-time-signal-grain-design.md`
- `docs/superpowers/plans/2026-09-03-temporal-grain-gakd-artifact-attack-r1.md`
- `research/signal_engine/temporal_scale/CHARACTERISTIC_MARKET_TIME_W0_ADVERSARIAL_REVIEW_AMENDMENT_2026-09-03.md`

WMT and silver remain selected discovery examples. Their outcomes cannot establish generalization. This sibling does not replace the broad TOI data/clock admission audit.

### 2.2 Technical Opportunity Intelligence already has explicit research/build boundaries

[WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE][toi] defines the first complete vertical as Compression Release on completed Weekly/Daily/4H inputs, real anticipation/actionability occurrences, product plus Terminal rendering, prospective evidence and species-specific adjudication. W0 records are merged; the source records W1 and W2-0 as undispatched. That last statement must be reconciled against current runtime/carriers before creating children.

| Existing wave | Assigned output in existing source | Entry dependency | Evidence needed to move on |
|---|---|---|---|
| W1 | Method/formula/alias/dependency-family census | W0 and current custody | Source receipts, method passports, local implementation coverage, rights and equivalence validators |
| W2-0 | Broad US data, clocks, corrections, coverage, rights and Terminal parity | W0 and current custody | Store contracts, clock fixtures, coverage and parity receipts; explicit ADMIT/HOLD/REJECT |
| W2 | Bounded existing-owner substrate repair, only when needed | Accepted W2-0 | Required input contract actually works; not another generic data platform |
| W3 | Compression Release preregistration and family tournament | Accepted W1 AND W2-0 | Frozen population, methods and outcome ruler; accountable result rather than a picked winner |
| W4 | Current per-security occurrence and two-queue snapshot | W3 adjudication | Source-backed state transitions, invalidation, correction and missing-data behavior |
| W5 | Product, detail view and Terminal consumption | W4 contract | Same occurrence identity/state on real consumer surfaces |
| W6 | Production shadow accrual | W5 | Real producer-to-ledger-to-product evidence, not fixtures only |
| W7 | Species-level disposition | Qualified W6 evidence | Kill/version/accrue/display/bounded-consumer ruling |
| W8 | Bottom/top reversal vertical | W7 and Durable Bottom/Species law | A separately tested construction, not a renamed killed washout seed |

Monthly, true intraday and sector/theme/basket objects remain in the long-term scope. Weekly/Daily/4H is the first proving slice, not the user's final scope and not a reason to ignore 12H/2D/3D research. Wider clocks need their own admitted data/definition, not synthetic daily-to-intraday reconstruction.

### 2.3 Prophet V4 has an incumbent programme and reserved source custody

[Current V4 workstream][v4ws] names the Fable Meta-CEO operation `prophet-us-fable-meta-ceo-20260923-001`, carrier #6805, and incumbent carriers #7581/#7180/#7572. These are retrieval targets, not a claim that those operators are alive or that their leases have expired. The Chairman requests Astra as the new principal, but that does not transfer a started writer or clear an uncertain effect.

Astra's first custody read must distinguish accountable leadership, live worker assignment, exclusive source lease and unresolved effect. Preserve path-disjoint progress while reconciling the exact incumbent carrier. Do not demand an acknowledgement from a historical title as a substitute for checking the current owner.

## 3. Where the real product goals and contracts already live

The [V4 master plan, sections 0-2][v4plan] provides explicit user outcomes: early evidence before slow confirmation; server-authoritative current entry availability; no green entry after a valid zone is consumed; full searchable candidates; missing-aware intelligence; cohort-honest grading; same-tape legacy control. These are existing product requirements, not proof they are shipped.

The [contract/owner map][owners] is detailed but contains dated capability snapshots. Use its interface ownership, then inspect current implementations and latest amendments before accepting its historical statuses.

| Question | Existing producer/owner | Consumer boundary and important distinction |
|---|---|---|
| Which security is this? | Data OS `lib/dataos/identity.py`, `VendorAliasTable`, security/issuer master | Exact issuer/security/listing identity is NOT Stock Identity's behavioral fingerprint |
| Which expert event occurred? | Live Entry Radar `mastermind.entry_event.v1` and its immutable experts | Do not collapse C2/C4, create a second event bus, or treat a display snapshot as a firing expert |
| Which durable opportunity episode? | V4 B1, `prophet.candidate_episode/v1` | Radar's `mastermind.live_entry_episode.v1` is not an alias or surrogate |
| What technical maturity? | B3/current occurrence owners | Confirmation is independent of buyability and intelligence quality |
| Is a trade available at this price/time? | B4/current entry-availability owner | Reconcile `engine/entry_signal.py`; do not mint a competing zone/stop/chase calculation |
| What evidence was known then? | D5 adapters and upstream owners | Earnings admission requires both source availability AND system observation at/before cut; a current workspace read is not a historical revision read |
| Which theme/subtheme and state? | GMI/theme graph, identity-resolution bridge and lawful memberships | Do not substitute legacy context-vector theme fields for canonical ThemeState |
| How are candidates ranked? | Conditional Fusion, accepted members/version and current board definition | D5 evidence-family presence is not a vote; a new challenger must earn authority |
| Who owns outcomes? | Evaluation OS, QLedger and established board/episode/plan graders | Do not confuse the execution-policy arena with the rank/fusion arena; preserve distinct denominators |
| Is the product actually fresh? | Existing settlement/publication/freshness owners | Wall-clock `asof`, GitHub success and artifact creation are not served economic-session proof |
| Who sizes exposure? | Portfolio/Risk | Prophet research context, an LLM narrative and a classifier are not sizing authority |

The source also records prior concerns about unpopulated control legs and plan-benchmark columns. Treat those as audit questions until current schemas and actual rows are checked; do not present August counts as current October measurements.

## 4. Exact existing research artifact contracts to reuse

### TOI W1: method passports, not thousands of independent indicator names

The [W1 evidence-census commission][w1] already specifies:

- `research/technical_opportunity/W1_EVIDENCE_CENSUS.md`
- `research/technical_opportunity/w1_method_passports.jsonl`
- `research/technical_opportunity/w1_alias_equivalence.json`
- `research/technical_opportunity/w1_source_receipts.json`
- `research/technical_opportunity/w1_local_coverage.json`
- `research/technical_opportunity/W1_REPORT.md`
- validators `validate_toi_w1_passports.py`, `validate_toi_w1_equivalence.py`, `validate_toi_w1_sources.py` under `scripts/research/`, and `tests/test_toi_w1_census.py`.

These are **specified deliverables**, not files proven implemented by this audit. The passport includes formula, parameters, source/rights, causal family, dependency family, role, required columns, actionable lag, repaint behavior, implementation coverage, equivalence, owner disposition, failure modes and baseline. This directly addresses the Chairman's request to go beyond MACD/RSI without counting aliases as independent confirmation.

[Current `engine/tech_catalog.py`][catalog] already separates legacy and Technical Lab modules. Inspected families include directional trend, recency/price pressure, compression/release, efficiency, breakout channels, volume money flow/participation, adaptive/ATR trends, rank momentum, path risk, relative strength, bar/fractal structure and challenger cycle/gap transforms. Its `role`, `dependency_family`, `actionable_lag`, `challenger_only` and `entry_stack_blocked` metadata are central to reuse. Display availability is not validated predictive authority.

### TOI W2-0: data and clocks

The [W2 data/clock commission][w2] specifies store contracts, clock matrix, coverage receipts, Terminal parity receipts, rights matrix, architecture freeze, report, validators and `tests/test_toi_w2_data_clock.py` under the same existing research owner.

Its requirements include distinct `4H-CLOCK` and `195M-RTH` definitions. The 390-minute US regular session is not two uniform four-hour bars. Explicitly handle the 9:30-13:30 and 13:30-16:00 alternative, two 195-minute bars, early closes, DST, holidays, missing intervals, corrections and completed-bar known time. No pooling across constructions. No synthetic 12H/4H series derived from daily bars.

Its store contract requires price basis, timestamp/session basis, availability support, corporate-action policy, PIT status, delisted coverage, ticker-reuse guard and separate research/storage/subscriber/public rights. A successful API call proves none of those independently.

### Existing clock repair, not a missing invention

The incumbent cascade uses `engine/session_anchor.py`, the absolute-session era `abs-session-2026-08-06`, and RSI-MACD 14/14/60/5 plus StochRSI 14/3/3. Preserve that baseline. Existing tests include `tests/test_confluence_resample_runtime.py` and `tests/test_confluence_warmup_floor.py`; the inspected runtime test covers W-FRI/ME parity, not every 2D/3D property. Audit actual call sites and seed/warmup semantics before claiming residual defects.

## 5. Existing empirical work that changes the research direction

| Source | Newly recovered implication | Interpretation ceiling |
|---|---|---|
| [2013-July 2026 regime/rotation atlas][atlas] | Existing historical sector analysis and a weekly price-MACD study; regime spans deliberately chosen ex post | Not a decision-time state reconstruction; QQQ is Nasdaq-100, not the Composite; not Prophet RSI-MACD |
| [RS-threshold study][rs] | The .75-.85 band does not validate the .75 gate as protection; hotter >=.85 comparison has more continuation failure in its specified test | Sector-ETF proxy, not point-in-time AI subthemes or production gate promotion |
| [Direct extension study][extension] | Existing 1.5-ATR boundary was NO-GO as an entry gate | Keep the measured null; do not revive it just because 'remaining opportunity' is an attractive phrase |
| [Phase-22 preregistration][phase22] | Exact future C2/same-cut C4 test and availability floors already specified | No new MACD-age threshold; no premature outcome read; no claim accrual started from the prereg alone |
| Regime-reliability adjudication | Broad family-by-regime forward-drawdown construction had a scoped null and poor rich-state coverage | Neither proof of universal conditional alpha nor a ban on every distinct conditional experiment |

The research audit contains the numerical tables and external-primary-source interpretation limits. None was re-run on raw internal data in this handoff revision.

## 6. Data inventory: questions which must receive measured answers

Existing candidate paths include `data/stocks/`, `data/yahoo/`, `data/baskets/ohlcv/`, `data/fred/`, `data/regime/regime_v2_pit.parquet`, `data/signal_archive/track_record.parquet`, `data/us_board_ledger/retro_grades.parquet`, `data/prophet/ledger.jsonl`, monthly US context-vector candidates, canonical episodes, Radar forward data, QLedger, TrialLedger and theme histories.

Astra needs one owner-backed inventory, not a claim that the count of parquet files equals usable history. For every dataset measure: first/last date; eligible universe by date; native security identity; delistings; adjustment convention; timezone and session; observation, publication, ingestion and decision clocks; vintage/correction support; coverage by regime and horizon; stale gaps; license/retention; immutable digest; and prior outcome exposure.

Separate final-vintage historical reconstructions, source-vintage as-observed reconstructions and genuinely live-forward evidence. They answer different questions. Today's theme membership cannot be used to claim a historical theme return. An old macro observation date cannot substitute for historical first-known time. Never read a no-peek experiment's outcomes to fill this inventory; operational counts and missingness suffice.

## 7. Fabric takeover facts, not imaginary dispatch instructions

The current connector exposes read-only `executive_state`, `executive_fabric`, `executive_job` and intent-status reads, plus `submit_ceo_intent`. The submission contract creates a QUEUED job and explicitly does not dispatch. The observed arm was disarmed; no dummy submission was made.

This is an exact arm-level observation, not evidence that every fabric avenue is unusable. On takeover discover the current approved dispatch/admission path, source custody, budget and eligible model/harness separately. Do not invent raw provider commands, endpoint names or aliases to compensate. No worker was started by this audit.

The Chairman permits Astra principal orchestration with fabric-only labor and multi-level suborchestration, including eligible Grok, Cursor, GLM 5.3 and Sol 6.1 routes. Model names are preferences, not readiness receipts. Suborchestrators receive bounded scopes, input/output contracts, budget and independent review requirements; they use the same fabric and never ChatGPT-native subagent spawning. Easy/medium work should not consume Astra when an eligible worker can meet its bar. Astra retains scientific disputes, cross-owner decisions and acceptance.

## 8. What remains unverified

Current production champion/version; latest actual plan/candidate/episode performance; historical data and theme availability; complete consumer parity; live W1A/W1/W2-0 execution; Phase-22 start receipt and qualified accrual; current Fable/carrier custody; full fleet route eligibility; and production release proof remain open. The first package's missing chapters remain missing. This repair provides verified navigation to existing plans and corrects evidence, without claiming to publish the previously blocked new master plan.

[temporal]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/agentos/workstreams/WS-TEMPORAL-GRAIN-INTELLIGENCE.md
[pr6790]: https://github.com/mastermindx-market-intelligence/macro/pull/6790
[toi]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/agentos/workstreams/WS-TECHNICAL-OPPORTUNITY-INTELLIGENCE.md
[v4ws]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md
[v4plan]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/prophet_v4/PROPHET_US_V4_RECOVERY_AND_INTELLIGENCE_GRAPH_OS_MASTERPLAN_BY_SOL_2026-08-17.md
[owners]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/prophet_v4/CONTRACT_AND_OWNER_MAP.md
[w1]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W1_EVIDENCE_CENSUS_HANDOFF_2026-08-27.md
[w2]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W2_DATA_CLOCK_HANDOFF_2026-08-27.md
[catalog]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/engine/tech_catalog.py
[atlas]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/SP500_NASDAQ_REGIME_ROTATION_ATLAS_2013_2026.md
[rs]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/prophet/cpu_leadership/ENTRY_RS_THRESHOLD_FINDINGS_2026-09-21.md
[extension]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/prophet/cpu_leadership/ENTRY_DIRECT_EXTENSION_CHALLENGER_FINDINGS_2026-09-21.md
[phase22]: https://github.com/mastermindx-market-intelligence/macro/blob/02fb67891222f9710c2a16b1fa6feb917996cab7/research/prophet_v4/US_PROPHET_PHASE22_FAST_CYCLE_REGIME_PROSPECTIVE_PREREG_2026-09-19.md
