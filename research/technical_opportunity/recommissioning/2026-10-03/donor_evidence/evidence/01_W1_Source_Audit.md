# TOI existing-W1 recovery and bounded audit

**As of:** 2026-10-03. **Scope:** existing W0/W1 artifacts, review/effect history, S16 and first-family crosswalk. Read-only source investigation; this memo is an intermediate contribution to the parent's renewed research packet. It does not acquire the existing W1 writer, accept W1, register a trial, or authorize W3. No market-data panel or outcome tape was opened and no empirical study or native review suite was rerun.

**Procedure pin supplied and verified by principal:** Mastermind@20adcaf65c2dd1bb734ab06e215feb1a0eb65659, INDEX 1.0.1 / bootstrap major 1. **Research-source pins inspected here:** Macro current baseline 5fc7af4a1aa2510966a7b566f97e5b894f2632f8; W1 candidate 15e4dfb0c9ddc788127d0954fd7d92414eefdcbf. The exact source checks below are distinct from historical test claims.

## 1. Recovery ruling

The commission's “W1/W2-0 undispatched; artifacts absent” premise is stale **at the program level**, although the two W1 report paths are still absent from the current main baseline (exact pinned fetches returned 404). The reports, normalized method records, source receipts and validators exist on the original draft W1 carrier. Correct status is **PARTIAL / REQUEST_CHANGES / SOURCE_CUSTODY_AND_ACCEPTANCE_HOLD**, not NOT_BUILT and not accepted.

- [W0 PR #6570](https://github.com/mastermindx-market-intelligence/macro/pull/6570) is merged, 2026-08-30 04:31:03Z, merge 6e3126c5106d5d240961088a866bf0e45f940538. Its architecture is a specification with W1/W2 commissions, no empirical or runtime proof.
- [W1 PR #7107](https://github.com/mastermindx-market-intelligence/macro/pull/7107) remains open/draft/unmerged at 15e4dfb0c9ddc788127d0954fd7d92414eefdcbf, branch sol/toi-w1-evidence-census-20260913. Its current PR body accurately records the grouped repair; the committed documents do not yet reflect that recovery.
- [Parent adjudication #6817/5865326642](https://github.com/mastermindx-market-intelligence/macro/issues/6817#issuecomment-5865326642) explicitly accepted the recovery correction and conservative semantic downgrades while requesting repair and withholding overall W1 acceptance.
- [Original-carrier repair ruling #7107/5865508898](https://github.com/mastermindx-market-intelligence/macro/pull/7107#issuecomment-5865508898) is the operative recorded repair frontier, subject to actual custody/admission.
- [W2-0 #7094](https://github.com/mastermindx-market-intelligence/macro/pull/7094) remains a separate carrier; the W1 records retain head 5bb1bc68c99146fab040aade04bbf1903c51e5b7 and combined data/clock HOLD. This memo has not independently audited W2 contents; use the W2 agent's fresh return.

### Exact stale records

| Record | Current text / defect | Recovered meaning |
|---|---|---|
| [Current Agent OS workstream](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/agentos/workstreams/WS-TECHNICAL-OPPORTUNITY-INTELLIGENCE.md) lines 46–61, 117–122 | W1 and W2-0 “Undispatched”; no delivery/pickup/START effect in that reconciliation | Projection predates existing #7107/#7094. Correct carrier state without manufacturing current runtime START or writer release. |
| [W1_REPORT.md](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/research/technical_opportunity/W1_REPORT.md) | PARTIAL / REPAIR_APPLIED_AWAITING_REREVIEW; asks to repeat Connors/RVOL bounded rereview | That review is terminal and accepted for its precise scope. Remaining acceptance work is the four grouped findings, handoff and release gates. |
| [W1_EVIDENCE_CENSUS.md](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/research/technical_opportunity/W1_EVIDENCE_CENSUS.md) | Same old rereview requirement; 26/1/5 coverage | Preserve original review history; mark corrected 24/3/5 coverage only when actually applied. |
| [w1_local_coverage.json](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/research/technical_opportunity/w1_local_coverage.json) | gaps_for_full_w1 still requests accepted rereview; false exact bindings remain | Update synchronously with passports and reports on original source carrier. |
| [w1_reproduction_sample.json](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/research/technical_opportunity/w1_reproduction_sample.json) | AWAITING_INDEPENDENT_REVIEWER, independent_review_complete=false | Deterministic sample was actually reviewed. Record completed review plus scoped outcomes, while retaining W1-acceptance=false and W3-authority=false. |
| Required W1 continuation handoff | No dated Agent OS W1 handoff appears among the 14 changed paths of #7107 | Closing handoff is still owed; do not infer it exists from narrative comments. |

The corrected PR body is useful current metadata, but does not by itself correct committed files, integration state or source custody.

## 2. What the original W1 actually contains

Pinned artifact set under research/technical_opportunity:
W1_EVIDENCE_CENSUS.md, W1_REPORT.md, w1_method_passports.jsonl, w1_alias_equivalence.json, w1_local_coverage.json, w1_source_receipts.json, w1_reproduction_sample.json, w1_residual_family_dispositions.json; four validators under scripts/research; tests/test_toi_w1_census.py; records-only waiver change. [Exact changed paths](https://github.com/mastermindx-market-intelligence/macro/pull/7107/files).

Descriptive parsing of those immutable JSON records gives:

- **32 passports** = 12 P0 + 10 P1 + 8 P2 + 2 archive.
- **29 equivalence classes, 65 aliases, 21 dependency clusters**.
- **20 W3-candidate owner dispositions, 8 later-context, 3 Terminal-display, 1 existing-species**. These are research routing classifications, not admitted trials.
- Committed local assertions: **26 exact / 1 partial / 5 missing**; conservative repair direction accepted by parent: **24 exact / 3 partial / 5 missing**, with P0 **9 exact / 3 partial**. The latter is **not applied** to the candidate.
- **29 source receipts**: 13 official platform formula documentation; 2 creator documents; 1 official open-source documentation; 11 academic/official academic sources; 1 practitioner source; 1 internal entitlement record. This is not 29 independent empirical validations.
- **10 residual-family dispositions**; their declared first-W3 trial effect is zero.
- **20-method reproduction sample**, selected deterministically by SHA256("TOI-W1-REPRO-V1:" + method_id), taking the 20 smallest digests; not selected using outcomes.

### Full active inventory

“Exact” below reproduces the **committed assertion**, not blanket acceptance by this audit.

| Method ID | Priority | Lifecycle/evidence role | Dependency family | Committed local state / repair | Routed owner |
|---|---|---|---|---|---|
| toi.bb_bandwidth | P0 | setup | volatility_channel | exact → partial (repair accepted, unapplied) | toi_w3_candidate |
| toi.bb_kc_squeeze | P0 | setup | compression_release | exact | toi_w3_candidate |
| toi.natr_percentile | P0 | setup | volatility_regime | exact | toi_w3_candidate |
| toi.hvr | P0 | context | volatility_regime | exact | toi_w3_candidate |
| toi.nr7 | P0 | setup | volatility_range | exact | toi_w3_candidate |
| toi.range_expansion | P0 | trigger | volatility_range | exact | toi_w3_candidate |
| toi.donchian_breakout | P0 | trigger | breakout_channel | exact | toi_w3_candidate |
| toi.donchian_fakeout | P0 | risk | breakout_channel | exact → partial (repair accepted, unapplied) | toi_w3_candidate |
| toi.fractal_swing_structure | P0 | setup | pattern_structure | exact | toi_w3_candidate |
| toi.benchmark_rs | P0 | participation | benchmark_relative_strength | exact | toi_w3_candidate |
| toi.cmf | P0 | participation | volume_money_flow | exact | toi_w3_candidate |
| toi.rvol | P0 | participation | volume_participation | partial | toi_w3_candidate |
| toi.support_resistance | P1 | setup | pattern_structure | missing | toi_w3_candidate |
| toi.adx_dmi | P1 | context | directional_trend | exact | toi_w3_candidate |
| toi.choppiness | P1 | context | trend_efficiency | exact | toi_w3_candidate |
| toi.momentum_12_1 | P1 | context | multi_horizon_momentum | exact | toi_w3_candidate |
| toi.momentum_acceleration | P1 | participation | multi_horizon_momentum | exact | toi_w3_candidate |
| toi.high52 | P1 | context | multi_horizon_momentum | exact | toi_w3_candidate |
| toi.obv | P1 | participation | volume_money_flow | exact | toi_w3_candidate |
| toi.inside_bar | P2 | setup | pattern_structure | exact | toi_later_context |
| toi.ulcer | P1 | risk | downside_path_risk | exact | toi_w3_candidate |
| toi.round_levels | P1 | context | pattern_structure | missing | toi_later_context |
| toi.short_reversal | P1 | context | short_horizon_reversal | missing | toi_later_context |
| toi.ma_trend | P2 | context | moving_average_trend | exact | toi_later_context |
| toi.rsi_oscillator | P2 | context | rsi_mean_reversion | exact | toi_later_context |
| toi.macd_stoch_incumbent | archive | trigger | incumbent_oscillator_confluence | exact | existing_species |
| toi.kama_er | P2 | context | adaptive_trend | exact | terminal_display |
| toi.supertrend | P2 | context | atr_adaptive_trend | exact | terminal_display |
| toi.connors_rsi | P2 | context | rsi_mean_reversion | exact | terminal_display |
| toi.geometric_double_pattern | P2 | setup | pattern_structure | exact | toi_later_context |
| toi.fibonacci_retracement | archive | context | fibonacci_geometry | missing | toi_later_context |
| toi.ordered_path_elliott | P2 | context | ordered_path_geometry | missing | toi_later_context |

[Inventory source](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/research/technical_opportunity/w1_method_passports.jsonl); [derived coverage](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/research/technical_opportunity/w1_local_coverage.json).

### Equivalence cautions

The three reductions from 32 methods to 29 classes are Donchian breakout/fakeout, support-resistance/round-level control, and 12–1 momentum/acceleration. They use **subtype** relationships. These do not prove identical formulas, interchangeable estimands or statistical independence of the remaining 29. RSI and Connors RSI share dependency while remaining distinct methods. Multiplicity accounting must include all chosen constructions and decisions, not use 29 as a free-standing effective-test count. [Equivalence artifact](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/research/technical_opportunity/w1_alias_equivalence.json).

### Residual and DNR routing to preserve

| Residual | Current disposition | Boundary |
|---|---|---|
| Generic FVG / gap imbalance | P2; local challenger; later | DNR:KILL-PM3-GAP-MAP stays killed; generic geometry is not that construction. |
| Divergence | P2; partial existing | Causal pivot confirmation/known-at unresolved; no backdating. |
| Named candlestick enumeration | Archive / Terminal display | Deterministic bar grammar already represented; enumeration is not distinct evidence. |
| Cycle phase / transforms / Monthly oscillator context | Existing CPI owner | DNR:KILL-ROTATION-CYCLE-CONFLUENCE; no new phase/turn/hazard owner. |
| Breadth and peers | P2 / existing substrate | Reuse PIT universe and denominator; no survivor-defined breadth store. |
| Regime conditioning | P2 / existing regime plane | DNR:KILL-REGIME-SCORECARD and DNR:KILL-FUSED-COMPOSITE. |
| Learned path / sequence representations | P2 / not built | After causal baselines, leakage controls and trial budget; no per-name outcome audition. |
| Exhaustion / extension | P2 / partial descriptors | Existing path/location features; later model follows proven occurrence semantics. |
| Opaque fused vendor composites | Blocked | Undisclosed formula and duplicated evidence family; no inferred vendor weights. |
| Opaque proprietary pivots | Blocked | Do not invent a formula from a name. |

[Residual source](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/research/technical_opportunity/w1_residual_family_dispositions.json). These dispositions are useful no-rebuild work, but mostly narrative interfaces, not completed Monthly/breadth/tactical scientific contracts.

## 3. Four outstanding defects: independently checked against exact source

The bounded checks below read the specific defining code. They confirm the substance of [review 5334507113](https://github.com/mastermindx-market-intelligence/macro/pull/7107#pullrequestreview-5334507113); they do not rerun or replace the completed independent review.

### D1. Valid generated catalog IDs fail the committed identity validator

[validate_toi_w1_passports.py](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/scripts/research/validate_toi_w1_passports.py) lines 75–97 performs literal substring membership across named source files. [ma_crosses.py](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/engine/ma_crosses.py) defines CROSS_PAIRS [(7,35),(21,100),(50,200)] and generates SIGNALS keys with an f-string in a loop at lines 189 onward. The concrete key golden_cross_7_35 therefore exists by deterministic registration, without appearing as literal source text.

Historical executed result: committed validator raises ValueError for toi.ma_trend / golden_cross_7_35. A prior dirty AST repair and two tests exist in the original review workspace. **Repair:** recover and preserve those exact pending edits; qualify their registration recognition. Do not loosen validation to accept arbitrary interpolations or treat a dirty-worktree PASS as committed-head proof.

### D2. The duplicate-membership hostile fixture reaches the wrong guard

[test_toi_w1_census.py](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/tests/test_toi_w1_census.py) lines 110–117 clones a first_class member from class 0 into class 1, which already has its own first_class. [validate_toi_w1_equivalence.py](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/scripts/research/validate_toi_w1_equivalence.py) lines 66–71 rejects “exactly one first_class” before reaching the cross-class membership-mismatch guard. The test expects the later error.

**Repair:** set only the inserted fixture member's relationship to subtype, so the cross-class duplicate guard is tested. Keep a separate two-first-class test. Do not broaden regex to conceal wrong-guard coverage.

### D3. BandWidth is falsely bound to band-walk Booleans

toi.bb_bandwidth claims exact local implementation using bb_band_walk_up/down. Those functions in [bollinger_event_signals.py](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/engine/bollinger_event_signals.py) lines 104–143 produce 0/1 states for price beyond a band on at least three of five bars. They are not numeric bandwidth.

The existing [stock_technicals.py::bb_bandwidth](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/engine/stock_technicals.py#L102-L106) computes 2*k*rolling_sd(ddof=0)/rolling_mean with n=20,k=2, ratio units. The band-walk module's own bands use ddof=1, which reinforces the need to bind the precise primitive.

**Repair:** reference the existing numeric helper and keep its unqualified catalog/consumer binding **partial**. The raw helper also does not by itself specify the percentile window, rank tie treatment, valid-history threshold or W3 cutoff required by W0's “Bollinger bandwidth percentile” design. Those must be frozen in a research construction, not supplied post-outcome.

### D4. Fakeout tracks the latest break, while the passport claims the original occurrence

The passport says freeze boundary on the breakout bar and emit once on recross within its fixed window. [compression_signals.py](https://github.com/mastermindx-market-intelligence/macro/blob/15e4dfb0c9ddc788127d0954fd7d92414eefdcbf/engine/compression_signals.py#L226-L308) sets last_break_idx and last_break_upper/lower every time the rolling breakout predicate is true. A second qualifying break resets both age and boundary. The same code's donch_break_up/down emits every qualifying close outside the trailing prior channel; it does not itself deduplicate a frozen TOI occurrence.

**Repair:** retain the original-occurrence scientific meaning and classify the existing binding **partial** with explicit latest-break mismatch. Do not rewrite the method to fit current implementation, and do not change production math in the records repair.

**Current-source relevance verified:** compression_signals.py, stock_technicals.py and bollinger_event_signals.py have identical Git blob hashes between W1 candidate and current Macro baseline:
31b22d5b864cd1da2c6517b93f9f379db82b209c;
ca33b18252eb5f08feb5646e0fb904039d80629b;
8a23cadad538e25fb45398def287fc47c89a3d85.
These findings are not invalidated merely because main advanced.

## 4. S16 is an incumbent with its own history, not the new TOI identity

[Current species registry](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/data/species/registry.json) records **S16 v1.0 “Squeeze Release”**, validation_status accruing, deployment_status unshipped, trial_count **12**. It binds engine/vol_squeeze.assess_series and the existing RUL-9 grader. Its rejection rules ban FIRED_DOWN in the long study and ban entering during COILED/COMPRESSED (“arming”) in this family.

The registry prose calls S16 volume-confirmed. Exact implementation and population establish a narrower truth:

- [vol_squeeze.py](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/engine/vol_squeeze.py) defaults: percentile threshold25, min-duration5, rank-window252, release-window3, volume threshold1.3, min-bars160. It computes BBWP and HVP, and additionally requires BB/KC squeeze where H/L is available. It constructs the box from the compression run.
- In lines 140–158, volume_confirmed is computed separately; FIRED_UP/FIRED_DOWN follows price versus the box regardless of that flag.
- [run_w2_ssq.py](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/scripts/research/run_w2_ssq.py) lines 484–509 collects **all FIRED_UP onsets**, deduplicating consecutive states, while retaining volume_confirmed as a tri-state field.
- The runner's own report-generation source at lines 1162–1168 explicitly says the historical species bar uses **all FIRED_UP events** and the volume-faithful fraction is diagnostic.

This is a verified source/registry-description mismatch, consistent with Seat B's retained finding. **Do not alter the historical event population to “repair” its prose, and do not silently turn the old 12 trials into volume-gated evidence.** A future volume-confirmation challenger is a separately accounted policy/variant.

Similarly, W1's BB/KC squeeze method is not synonymous with the full S16 run/percentile/box/onset construction. W0's proposed compression_release_up/down are not automatically new names for S16. Scientific owner must classify each proposed construction as an incumbent reproduction, version/variant or distinct species and carry forward the appropriate trial history.

### Arming and downside resolution

W0 explicitly studies FORMING/ARMED detection and separate upside/downside opportunity states. This can coexist with S16's arming-entry ban if pre-trigger observations are **non-actionable research/context** and never become early entries or recolored S16 historical events. Downside detection likewise has no directional-short authority. The renewed architecture should state those distinctions directly. Any conflicting consumer request requires a scientific-owner ruling, not name substitution.

### Def-4 remains a separate historical preregistration lineage

[SSQ_DEF4_VARIANT_PREREG.md](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/research/entry_stack/SSQ_DEF4_VARIANT_PREREG.md) defines esx_sq_def4_phase0, **10 declared trials / 46 planned BH-eligible hypothesis cells**, as a conditioning study on the same FIRED_UP tape, with no arming, no FIRED_DOWN, no retest/false-break state extension. Its proposed runner is scripts/research/run_ssq_def4.py. This memo read the preregistration, not that study's outcomes or execution proof. Seat B's retained execution classification is **NOT_ESTABLISHED**. Do not count a preregistration file as registration receipt plus completed execution; do not reset family-sequential accounting.

## 5. Seat B R2, Turn7 and Turn8: useful recovered decisions, missing complete artifacts

[W1 cumulative return 5863266019](https://github.com/mastermindx-market-intelligence/macro/pull/7107#issuecomment-5863266019) and [parent-side Seat B return 5864160892](https://github.com/mastermindx-market-intelligence/macro/issues/6817#issuecomment-5864160892) preserve these decisions:

- R2 status **DRAFT_SOURCE_BOUND_NOT_ADMITTED**. JSON SHA256 134e0d8d2c6a09260f150002d9b165c4da82a1d9cb61db17090dde492ceedba5; package SHA256 2ec03107b5aa874d926788964e245340c1c6502eb1da9fa48210f8c72db516e7.
- **Four proposed families / 32 constructions / zero registrations.** The 32 constructions are not 32 fully enumerated inferential hypotheses. Endpoint/comparator/model-selection accounting remains owed.
- Original-trigger cohort, full roster, common terminal and coverage/value attribution must be preserved. Existing native grading uses a fill-relative H, while R2's claimed policy comparison uses the original-trigger +21-session terminal; unequal fills with equal H are a different estimand.
- Parent's **single proposed 0.01 upside confirmation claim** within the broader Prophet amendment is not multiplied into secondary rescue claims or silently adopted as TOI's independent global budget.
- Additional baseline fits, endpoints, selection choices and looks require predeclared accounting and existing scientific/evaluation-owner adoption.
- S16 trial_count12, historical population and arming ban persist; R2 is not an identity reset.
- D5 requires a native technical-family extension. Technical evidence cannot masquerade as earnings evidence or an extra tenth B4 gate.

Turn7 and Turn8 contain analytical mathematics/synthetic proofs. The useful durable distinction is **same-time information/representation value versus original-cohort timing-policy value**. A confirmation Boolean deterministic in the full available feature set cannot add independent raw information; waiting can still alter economic value through price, risk, costs and time. Higher target-hit probability can merely reflect nearer target geometry. These are design/falsifier considerations, not empirical evidence that a technical method works.

**NOT_REACQUIRED:** the complete R2 JSON/ZIP, Turn7 package and Turn8 package are not attached in this session and no branch source file was recovered. One bounded SEAT_B_TOI default-branch search returned no match; that is not proof of global absence. Hashes and narrative returns establish their recorded identity and scope, not their full bytes. The principal confirmed no mounted Seat B artifact exists. Therefore the new packet must not present an invented 32-construction table as a recovered document. It may propose a clearly labeled new draft design that preserves these decisions, with zero registrations and no adoption claim.

## 6. Where old W1 falls short of the renewed research-complete commission

These are **scope/contract gaps**, not an instruction to reopen accepted unchanged formula review:

1. **Breadth of target objects:** every active passport is single_security. Active timeframes are D/W/candidate_4H (plus 2W incumbent); no explicit Monthly or tactical-intraday active passport. The residual notes mention these owners, but don't freeze usable-time, aggregation identity, endpoint or consumer contracts.
2. **Lifecycle measurements:** the records identify setup/trigger/participation/context/risk roles, but have no full activation-risk sets, failure competing events, confirmation-cost objective, remaining-opportunity denominator, censoring or path-consumed rules.
3. **Construction precision:** e.g. raw bandwidth lacks its percentile constructor; NR7 parameter object is empty while its steps permit optional retention; methods lack full permissible parameter domains. Current schema is not a preregistration.
4. **Scientific crosswalk:** 31/32 candidate_species arrays are empty; only incumbent MACD/Stoch names T1–T4. Twenty owner_disposition=toi_w3_candidate rows are not 20 admitted species. S16 and related prior history require explicit bindings.
5. **Failure evidence:** 15/32 known_failure_modes lists are empty. A receipt to a formula catalog establishes a definition, not evidence of predictive/economic incremental value, nonstationarity or failure conditions.
6. **Mechanism versus observable:** CMF/RVOL and OBV are transformations of price/volume, not direct measurements of order ownership or informed buying. Benchmark-relative momentum and peer-relative leadership are different comparators. The renewed evidence matrix must state proxies and available information rather than treat these as independent latent causes.
7. **Statistical and economic budgets:** method/equivalence counts do not enumerate direction × clock × threshold × phase × endpoint × comparator × fitted selection. Full prior lineage, selection law, strong baseline, costs and untouched/prospective cuts are still missing.
8. **Data/rights admission:** internal entitlement receipt in W1 is an evidence reference, not permission to mark the W2 data panel ADMIT. Formula rights also do not grant vendor-data research/display/redistribution rights.
9. **Closing deliverable:** the original W1 commission requires complete candidate-family size, compute estimate, exact preregistration action, horizon/owner counts and do-not-redo handoff. The committed report and hash-only R2 do not meet that complete handoff.
10. **Current product claims:** W1 is records-only. No current occurrence engine, Radar queues, production path, Prophet integration, prospective validation or live acceptance can be inferred from these artifacts.

[Original W1 commission](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W1_EVIDENCE_CENSUS_HANDOFF_2026-08-27.md); [W0 scientific and product requirements](https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_ARCHITECTURE_FREEZE_2026-08-27.md).

## 7. Recommended repair and recommission sequence

1. **Preserve original #7107 identity and pending work.** Source custodian must inspect current worktree/effects under current admission, match or reconcile dirty preimages, and explicitly establish the single permitted writer. A new research narrative is not that receipt.
2. **One grouped records repair:** preserve/qualify AST generated-ID change; fix hostile membership fixture with separate first_class coverage; change BandWidth and original-occurrence fakeout to partial; update 24/3/5 counts and all stale reports/reproduction/handoff metadata together. Do not modify production indicator formulas in W1.
3. **Complete research packet on the parent's authorized documentation carrier:** integrate new mechanism/lifecycle/context/Temporal-Grain/statistical evidence with the recovered inventory, not a replacement registry. Clearly label proposed architecture and unavailable R2 bytes. Keep research additions separate from source-repair acceptance.
4. **Scientific owner adopts an exact W1→W3 crosswalk:** include S16 full formula/population lineage and12 historical trials, def4 lineage, independent new upside/downside definitions if appropriate, original-trigger risk sets, full endpoints/comparators/selection budget and compute estimate. Reuse species/trial/evaluation owners.
5. **Qualify repaired immutable W1 head:** native passport/source/equivalence/residual validators, corrected hostile suite, Agent OS/diff hygiene; bounded independent review only of changed findings; latest-base integration and required hosted checks; final parent acceptance.
6. **Require separate W2 data/clock verdict.** A clean W1 head does not admit a panel or 4H construction.
7. **Only after both research/admission gates:** freeze and register W3 through existing owners. No market outcome run in this recovery pass.

**First-family recommendation (design judgment):** retain Compression Release as first proving family pending scientific-owner amendment. It exercises formation, trigger proximity, first trigger, confirmation, failure and extension; existing primitives and S16 provide strong reuse and hostile comparators. This is a cost/information-design rationale, not a prediction of positive returns. Start with strongest causal baselines and the smallest genuinely distinct construction budget. Do not treat lack of lawful4H as permission to silently pool clocks or change W0; carry a precise proposed Daily/Weekly staged admission ruling to the owner if W2 holds4H.

## 8. Custody, historical evidence and DO_NOT_REDO

Original pending workspace:
 /Volumes/Mastermind/Mastermind/worktrees/sol-review-pr7107-15e4df-20260913
branch sol-review/toi-w1-validator-repair-20260913.

Retained dirty preimages:
- validator SHA256 7a1804af0bd8a1c7fc19c5366883da92d210db6c12b2654396572241d47f60f2
- tests SHA256 5a84cd21521e01ac8d4931e23722cd11a5aba95719848b2aef886e235418dcbd

These are **historically retained hashes**, not freshly reread by this agent. AUTH_UNAVAILABLE and subsequent explicit credential-mapping refusal remain recorded; no source lease has been proven here. Do not route around that refusal, overwrite pending work, create a replacement W1 branch/PR, or replay an operation whose effect is uncertain.

Accepted completed review scope:
- original20-passport review on accd7c6a296fd038ae863d071fa44244c4796e0a:18 PASS/2 FAIL; terminal;
- subsequent two-finding Connors/RVOL review on15e4dfb0…: Slack root C0BSBM78V1N/1789328715.664659, RESULT1789363727.143149, SOL ACCEPTED/STOP1789367962.694559; terminal;
- keep Connors3/2/100 source binding, P2/Terminal routing and RSI-family block; retain RVOL prior20 completed-bar definition with current inclusive formula partial.

Historical native evidence, **not rerun here**: dirty metadata validators PASS; dirty suite27 PASS/1 FAIL; committed passport validator FAIL; Agent OS1108 records/0errors/61warnings; diff-check PASS. Seat B synthetic and exact-function counts are separate source-limited evidence, not market performance or hosted acceptance.

**DO_NOT_REDO:** unchanged20-passport review; unchanged accepted Connors/RVOL rereview; generic source list as a substitute for renewed estimands; S16 historical outcome run; def4 outcome run; per-name best-indicator/timeframe audition; killed arming/timer/gap-map/composite constructions under new names; alternative indicator/species/trial/evidence/lifecycle/identity/data/Radar/renderer stores. No source mutation, credential access, worker launch, Slack send, CI run, outcome computation, trial registration, model fit, Prophet authority or production effect occurred in this agent's task.

## 9. Evidence identity notes

Key immutable W1 blobs:
- passports77a88239cb542dea1f2dd461a5bb580281f64246
- alias/equivalence6bf4984a77f3bb64ac1ca35c387ebb2dac278f3c
- local coveragef643223a7a5191179a482e468810c907d84979c9
- source receipts7ad48dd30e6816ca89bfa53c2d21a44a67aacec6
- residualse2874ed5a7ba0455efdf7f8888301a51ddd1d50a
- reproduction samplec63cd8115a37e2581b8612c2ab402c6488b649a5
- W1 reporta8c60960c72c5501773c08f7dcacfcd5bdaa2fc4
- W1 censusf1c6756f7e0f0e060d1aa3abe062675273c40190
- passport validatorf409d2dee7789770ad398f87b6683c84aa5d6fbd
- tests c6a42cfaab0be7ddb9525691f8628c404953cedb

Current-main evidence:
- workstream90b14f7f575c3db2edbfb8bb037bbc99549a7079
- W0 architectureb9d79f6aff568d1f670b297e81ea381ae2c7dbcd
- original W1 commissiond433d4a0a2a2cd731411aab61c0c5c43ae902796
- S16 registry3478c4b731400f304c1baf360b7f0fa2a746942d
- vol_squeezeae0d7f53219440530ecb174644c86b02f3a384ba
- S16 runnerf5ecf998208bae97948b87c73248b776ffcb67f0
- def4 prereg7e9d671410e2ec67b390125016bb7e62f91fddc2

Bounded copies of inspected W1 sources and original commissions are under work/w1-sources for principal integration. These scratch copies are intermediate evidence, not adopted repository changes.

