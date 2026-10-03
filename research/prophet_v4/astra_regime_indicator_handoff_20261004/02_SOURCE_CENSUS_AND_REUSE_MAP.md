# Source census and reuse map

## 1. Source identity and what the pin proves

This package was authored against Macro `f5c2e829fef0a9891df0527a4bf74f280aaa0813` (tree `7199758d2388d2af6e96f159d7c055de4df9ad2d`), Mastermind `d1594f3c7ae750db3f14b4eebf0de3460f84267a`, and the observed Terminal master ref `863f678658e2211b5a48daa99404686dfaa117f2`. Default branches and repository names were retrieved through the live GitHub connector. Macro permits source writes for this connection; this does not waive review or deployment gates.

A pin fixes an observation, not the receiver's future execution base. Re-pin protected procedure once on pickup; inspect relevant deltas rather than repeating the entire census after unrelated commits. Terminal's ref was checked, but no fresh terminal-wide functional audit was performed during handoff preparation.

Protected INDEX is compatible with bootstrap major 1, schema `mastermind.sol_skillpack.v1`, skillpack 1.0.1. ACTIVE_EXECUTION's blob `9fed10f7cc7a2f4323d039b406f7c0715445e22e` matched the version already read during continuation. SESSION_RELIABILITY was not enrolled in this pinned INDEX; do not guess a file or treat its earlier missing path as a global work blocker. Load it from the same commit if the receiver's current accepted INDEX enrolls it.

## 2. Decisive sources

### S1 - incumbent indicator and temporal semantics: checked at handoff source pin

[engine/confluence_tiers.py](https://github.com/mastermindx-market-intelligence/macro/blob/f5c2e829fef0a9891df0527a4bf74f280aaa0813/engine/confluence_tiers.py)

Read lines 1-64 during preparation. Blob: `004eda921766922e146d35acc6ee2bc646e96854`. Confirms RSI-MACD rather than ordinary price MACD, 14/14/60/5 constants, StochRSI 14/3/3, the absolute-session era and distinct event/observation/provisional dates. It does not prove every downstream caller or deployed release uses the expected path. Read the calculation and callers for reproduction.

### S2 - existing absolute anchor: inspected in preceding continuation

[engine/session_anchor.py](https://github.com/mastermindx-market-intelligence/macro/blob/b4f95f98ef80b8cbb4636afbd723b5091658e1f1/engine/session_anchor.py)

Earlier source blob: `0cfc9857cd240788542f1dc6d94eb55d4a68a513`. This is an existing implementation, not a missing proposed module. Read its current revision, `lib/nyse_calendar.py`, the associated absolute-calendar adjudication and its actual consumers. Audit unsupported-market fallback, reference coverage and late vendor corrections. Do not replace it with pandas `3B`, series-start counting or a new calendar registry.

Related existing paths: `research/SESSION_ANCHOR_ABSOLUTE_CALENDAR_ADJUDICATION_BY_FABLE.md`, `engine/canon.py`, `engine/technicals.py`, `tests/test_confluence_resample_runtime.py`, `tests/test_confluence_warmup_floor.py`. The inspected runtime test only covers W-FRI/ME and exact accepted known-date behavior; it is not by itself a full 2D/3D invariance proof.

### S3 - exact frozen fast-cycle experiment: checked at handoff source pin

[Phase-22 preregistration](https://github.com/mastermindx-market-intelligence/macro/blob/f5c2e829fef0a9891df0527a4bf74f280aaa0813/research/prophet_v4/US_PROPHET_PHASE22_FAST_CYCLE_REGIME_PROSPECTIVE_PREREG_2026-09-19.md)

Blob: `8eeeef8c3f61e474383815ba6ff26b92e5d1795e`. Read lines 1-220. This is the authority for the experiment's population, start boundary, primary/secondary tests, availability rules and no-peek floors; recover any later amendment before execution. Companion configuration: `research/prophet_v4/us_prophet_phase22_fast_cycle_regime_prereg_v1.json`.

Related discovery: `agentos/discoveries/DSC-PROPHET-PHASE21-TWO-DEFECT-MECHANISM-AND-PHASE22-PROSPECTIVE-TEST.md`. The Phase-21 synthesis digest is retained in the research intake. Its local location must be resolved; no raw file recovery is claimed here.

### S4 - one Prophet platform, multiple strategies: checked at handoff source pin

[Multi-strategy and cycle-capture decision](https://github.com/mastermindx-market-intelligence/macro/blob/f5c2e829fef0a9891df0527a4bf74f280aaa0813/agentos/decisions/DEC-PROPHET-ONE-PLATFORM-MULTI-STRATEGY-AND-CYCLE-CAPTURE.md)

Blob: `08d1676fb1007334043c7e737196d0192360b232`. Read lines 1-75. Preserves one platform, canonical candidate/evidence/availability/outcome owners, distinct strategy sleeves and separately governed risk. Rejects a single universal all-weather rank, a duplicate Prophet per strategy and a fused macro scorecard.

Companions for full pickup: `research/prophet_v4/PROPHET_STRATEGY_PLATFORM_AND_CYCLE_CAPTURE_ARCHITECTURE_FREEZE_2026-08-30.md` and `agentos/decisions/DEC-PROPHET-CYCLE-CAPTURE-REUSES-LONG-HOLD-AND-MARKET-NATIVE-OWNERS.md`.

### S5 - conditional information can earn authority: checked at handoff source pin

[Earned conditional authority decision](https://github.com/mastermindx-market-intelligence/macro/blob/f5c2e829fef0a9891df0527a4bf74f280aaa0813/agentos/decisions/DEC-PROPHET-ZERO-AUTHORITY-SUPERSEDED-BY-EARNED-CONDITIONAL-AUTHORITY.md)

Blob: `d26131a2c2396dc5dc69279745377d05b6765aea`. Read lines 1-65. The permanent blanket ban on information families was superseded. A versioned model can be a promotion unit, but an unconditional composite or confirming-desk count is not restored. The old champion name inside this historical decision is not a current deployment receipt; census current champion/version separately.

Companions: `research/PROPHET_CONDITIONAL_FUSION_MASTERPLAN_BY_FABLE.md`, `agentos/workstreams/WS-PROPHET-CONDITIONAL-FUSION.md`, `agentos/decisions/DEC-PROPHET-FUSION-IS-THE-CANONICAL-US-RANKER.md`, `engine/us_prophet_fusion.py`, `engine/prophet_arena.py`, `research/prophet_fusion/families.yml`.

### S6 - technical catalog, species and two product queues: inspected in preceding continuation

[TOI owner decision](https://github.com/mastermindx-market-intelligence/macro/blob/b4f95f98ef80b8cbb4636afbd723b5091658e1f1/agentos/decisions/DEC-TECHNICAL-OPPORTUNITY-INTELLIGENCE-CANONICAL-OWNERSHIP-AND-TWO-QUEUE-LAW.md)

Canonical primitives remain in `engine/tech_catalog.py`; scientific species in `engine/species_registry.py` and `data/species/registry.json`; trial/grading/promotion in existing evaluation systems. FORMING/ARMED anticipation is separate from TRIGGERED/CONFIRMED actionability. Occurrence states also include extension, exhaustion, invalidation and fakeout. Terminal is a consumer, not a second semantic owner. Re-read current source before editing.

### S7 - contrary empirical result and estimability: checked at handoff source pin

[Regime-reliability adjudication](https://github.com/mastermindx-market-intelligence/macro/blob/f5c2e829fef0a9891df0527a4bf74f280aaa0813/research/REGIME_RELIABILITY_FACTOR_CROWDING_ADJUDICATION.md)

Blob: `8d189014d01dd61268cdcd55907a7df2eef86afe`. Read lines 78-151. The reported null is construction- and outcome-specific; do not promote it into a permanent information-family ban. Do not ignore it either. Related existing code/report: `engine/regime_conditioning_coverage.py`, `tests/test_regime_conditioning_coverage.py`, `scripts/regime_reliability_phase0.py`, `reports/regime-reliability-phase0.md`.

### S8 - existing theme-state dependency and ownership: historical recommendation, not a fresh ruling

[D1/D3/W3B merge-order recommendation](https://github.com/mastermindx-market-intelligence/macro/blob/85932a1b7ce0e597ad73e713f7528101e4ef58d9/research/prophet_v4/D1_D3_W3B_MERGE_ORDER_RECOMMENDATION.md)

This earlier recommendation identified GMI as ThemeState owner and identity/membership/PIT readiness as predecessors to a Prophet consumer. It is expressly a recommendation. Resolve the actual accepted decision and latest GMI checkpoint, including `agentos/decisions/DEC-GMI-THEME-GRAPH-END-TO-END-COMPLETION-OWNERSHIP-SEQUENCING.md` and `agentos/workstreams/WS-GMI-THEME-GRAPH.md`. Do not mistake its old coverage percentages for current data readiness.

## 3. Existing program owners to recover, not recreate

| Concern | Existing owner/surface to inspect | What this project should add, if absent |
|---|---|---|
| Runtime, budgets, provider placement, fleet execution | Mastermind Executive OS / Model Router / Capacity / workspace custody | Bounded admitted research/build jobs, not a second executor or queue |
| Organizational continuity | Macro `agentos/` | Current handoff and decisions through existing protocols |
| Regime facts | `risk_radar` -> `market_state` -> `regime_vector`, plus `regime_one`, `regime_coherence`, rates/liquidity owners | Qualified historical reconstruction and conditional evaluation, not a competing fused verdict |
| Primitive indicators | `engine/tech_catalog.py`, `engine/technicals.py`, technical lab / Terminal implementations | Definition/provenance audit, missing reusable adapters and parity tests |
| Setup identity and scientific lifecycle | `engine/species_registry.py`, `data/species/registry.json` | Registered distinct challenger species and evidence, not another species database |
| Current structural occurrence | Technical Opportunity Intelligence | Sequence, confirmation cost and remaining-opportunity descriptors within its contract |
| Tactical event production | Live Entry Radar | Same-cut evidence durability, not alternate C2/C4 identities |
| Theme identity and state | GMI / `engine/theme_graph/` | Historical membership/coverage and leader-persistence consumer evidence |
| Prophet episodes and planes | V4 B1 identity; B3 maturity; B4 availability; D5 evidence | Contract-compatible adapters and strategy views; verify actual build status first |
| Ranking and model comparison | Existing Conditional Fusion / arena / current champion | Measured incremental challengers, no unconditional replacement score |
| Outcomes and promotion | Evaluation OS / QLedger / TrialLedger | Required experiments and evidence envelopes under existing ownership |
| Portfolio exposure and sizing | Existing Portfolio/Risk owner | Separate risk-aware validation after strategy evidence; no LLM sizing |
| User consumption | Macro dashboard and mastermind-terminal | One coherent explanation and lifecycle across both real surfaces |

## 4. Research and plan shelves already discovered

These paths are navigation from preceding source census, not claims that every plan is shipped or was freshly reread during packaging. Resolve status, amendments and current artifact paths before building.

**Prophet architecture and evaluation:**
`research/PROPHET_MASTERPLAN_BY_FABLE.md`; `research/PROPHET_US_TREND_INTELLIGENCE_MASTERPLAN_BY_FABLE.md`; `research/PROPHET_US_SUPERINTELLIGENCE_ROADMAP_BY_FABLE.md`; `research/PROPHET_CN_SUPERINTELLIGENCE_ROADMAP_BY_FABLE.md`; `research/MASTERMIND_PROPHET_EVAL_SPEC.md`; `research/PROPHET_PIT_REPLAY_HARNESS_V1.md`; `research/PROPHET_LEARNING_LOOP_MASTERPLAN_BY_FABLE.md`; `research/prophet_v4/PROPHET_US_V4_RECOVERY_AND_INTELLIGENCE_GRAPH_OS_MASTERPLAN_BY_SOL_2026-08-17.md`.

**Timing, availability and failure analysis:**
`research/prophet_us_audit/ENTRY_LATENESS_FORENSIC_2026-08-07.md`; `research/prophet_us_audit/EARLY_ADMISSION_BAKEOFF_2026-08-11.md`; `research/PROPHET_US_MISSED_IGNITIONS_MASTERPLAN_BY_FABLE.md`; `research/PROPHET_US_IGNITION_LAYER_W8_BY_FABLE.md`; `research/prophet/cpu_leadership/CONVERGENCE_AND_DELIVERY_2026-09-21.md`; `research/prophet/cpu_leadership/ENTRY_DIRECT_EXTENSION_CHALLENGER_FINDINGS_2026-09-21.md`; `research/prophet/cpu_leadership/ENTRY_RS_THRESHOLD_FINDINGS_2026-09-21.md`; `research/prophet/cpu_leadership/PREMARKET_ENTRY_FINDINGS_2026-09-21.md`.

**Regime, breadth, participation and historical atlas:**
`research/SP500_NASDAQ_REGIME_ROTATION_ATLAS_2013_2026.md`; `research/artifacts/sp500_nasdaq_regime_rotation_2013_2026/methodology.json`; `research/REGIME_V2_PIT_DIVERGENCE_AUDIT.md`; `research/FACTOR_INTELLIGENCE_MASTERPLAN_BY_FABLE.md`; `research/REGIME_DISLOCATION_RECAL_PROPOSAL.md`; `research/MEGACAP_SUCTION_FIELD_GUIDE.md`; `research/MEGACAP_LEADERSHIP_COHERENCE_MASTERPLAN_BY_FABLE.md`; `research/POSTMORTEM_20260716_DEFENSIVE_ROTATION_MISS_BY_FABLE.md`; `research/ROTATION_EVENTS_V2_MASTERPLAN_BY_FABLE.md`; `research/ROTATION_COMMAND_MASTERPLAN_BY_FABLE.md`; `research/participation_flow_intelligence/`.

The prior Library search found `PFI_WEB_CEO_MASTER_PACKET.md`. Its useful point was to separate opportunity-universe width from aggregate market risk and keep participation/flow context owner-backed. It was an authoring packet, not evidence its children ran. Do not import its suggested time budgets or deployment status as current law.

**Technical and long-hold prior art:**
`research/STOCKINVEST_TECH_INDICATOR_SUITE_PROGRAM.md`; `research/long_hold/WASHOUT_TIMEFRAME_HYPOTHESIS.md`; `reports/mwr_timeframe_personality.md`; `scripts/research/mwr_timeframe_personality_scan.py`; `engine/advanced_indicators.py`; `engine/indicators.py`; `engine/indicators_m2.py`; `engine/tech_confluence.py`; Signal Foundry and technical-catalog sources found through their registries.

**Cross-market and theme work:**
`research/cn_prophet_audit/SEMICON_LEADERSHIP_AUDIT_2026-09-21.md`; `research/cn_prophet_audit/CHINA_LEADERSHIP_CONTINUATION_2026-09-22.md`; CN flow, chase, exit, precursor and persistence audits in that directory; `research/PROPHET_HK_CANADA_REVAMP_EXECUTION_PACKET_2026_08_18.md`; `research/theme_graph/THEME_GRAPH_END_TO_END_COMPLETION_FREEZE_2026-08-27.md`.

Do not transplant a CN result to US without testing session structure, shorting/limit rules, liquidity, instrument universe and point-in-time feature differences.

## 5. Data surfaces to census before promising coverage

Existing paths identified earlier include:

- `data/stocks/`, `data/yahoo/`, `data/baskets/ohlcv/`, country stores and `data/fred/`;
- `data/us_board_ledger/retro_grades.parquet`, board outcome/track artifacts, `data/prophet/ledger.jsonl`;
- `data/us_prophet_rank/candidates.parquet`, context-vector and candidate/episode records;
- `data/signal_archive/track_record.parquet`, `data/regime/regime_v2_pit.parquet`;
- existing Entry Radar forward evidence, QLedger and `data/trial_ledger.jsonl`;
- `data/species/registry.json`, theme-graph and Neural Web theme histories, research-vault catalogs.

For each surface record owner, immutable revision/digest, observation range, markets, instruments, adjustment convention, sessions, first-known/vintage support, eligibility universe, delistings, gaps, revisions, rights, intended use and known contamination. File count is not usable history. A deep OHLC history does not imply historical subtheme membership or first-known macro releases. A current stock universe can be survivorship-biased even if its price series are long.

## 6. No-redo and source-collision register

Recover current `research/DO_NOT_REBUILD.md` and its compiled registry before proposing any rule. Known relevant identifiers include `DNR:KILL-WASHOUT-TURN`, `DNR:KILL-ROTATION-CYCLE-CONFLUENCE`, `DNR:KILL-REGIME-SCORECARD`, `DNR:KILL-FUSED-COMPOSITE`, `DNR:KILL-PROPHET-POP-MERGE`, `DNR:KILL-OUTCOME-AUDITION`, `DNR:KILL-LLM-ORIGINATION`, `DNR:KILL-OFFHORIZON-VERDICTS` and positioning-fusion amendments. A different hypothesis must explain exactly how it differs from the killed construction.

Known existing workstreams: `WS:PROPHET-US-V4-RECOVERY`, `WS:PROPHET-US-ENTRY-TIMING`, `WS:PROPHET-CONDITIONAL-FUSION`, `WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE`, `WS:LIVE-ENTRY-RADAR`, `WS:GMI-THEME-GRAPH`, `WS:PROPHET-US-AVAILABILITY`, `WS:PROPHET-HK-CA-REVAMP`, plus Evaluation/identity/earnings owners. Their files may lag actual code; recover current checkpoints and active source leases rather than following an old next_action blindly. The entry-timing workstream read in the preceding continuation still pointed at an August bake verification, which is evidence to reconcile, not proof it remains the next action.

Historical PRs named inside Phase 22 are collision leads only. Inspect live state before touching their files. This handoff does not assign or overwrite an active sibling branch, TrialLedger prefix, deployment or runtime operation.

## 7. Confidence boundary

The source pins and decisive excerpts above are independently recoverable. The broader census is a substantial navigation map, not an assertion of a completed repository-wide or production audit. The highest-value next step is targeted verification of current champion, clocks, full decision populations, PIT feature availability and active owners, then concrete implementation through those owners.
