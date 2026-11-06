# SNI V0 — Evaluation extension decision

**Status:** V0 DECISION (one recommendation). Nothing in this document is implemented. Every change named here belongs to the existing evaluation owner and lands through that owner's normal PR path, after the gates in §9.
**Evidence base:** macro `origin/main` @ `e44069e306fd`. Property-by-property proof is in `SNI_V0_EVALUATION_SUPPORT_MATRIX.md` (cited below as "matrix row N").

## 1. Recommendation (exactly one)

**(a) A new declared claim family, `sni_belief.v1`, inside the existing qledger claim schema, owned by the evaluation owner `WS:EVAL-OS-MEASUREMENT-LAW` (`engine/qledger.py`).** Every SNI-specific field is validated **only** when `claim_family == "sni_belief.v1"`. No other family's validation, ids, grading, cohorts or publication change.

Why (a). Of the properties V0 must support:

- Eight are already enforced by qledger and pinned by tests: clock, maturity, refusal-not-short-grade, HK/US clock separation, backfill-not-prospective, count-once, market-from-provenance and control policy (matrix rows 3, 9, 11, 13, 15, 16, 22, 24).
- The rest need additive, family-gated fields on the same object.

`DEC:EVAL-OS-RECOVERY-ARCHITECTURE-FREEZE` names qledger and owner-native ledgers as "the canonical scored-record substrates" and existing gauntlet/qual-ladder owners as promotion authority. `DEC:MARKET-BELIEF-IS-COMPOSITION-NOT-TRUTH-STORE` rules that a belief product is a composition over owner records, not a truth store. A family inside qledger is the only option that satisfies both.

## 2. Fields and enums admitted (family-gated)

All fields below are validated in `_validate_claim` when `claim_family == "sni_belief.v1"`. **Any unknown top-level key on this family is refused.** This closes today's silent pass-through in `_prepare_claim` (matrix row 1) for this family only.

| Field | Type | Rule |
|---|---|---|
| `desk` | `"sni_belief"` | Required by the existing validator. **No `DESK_MARKET` entry** (the family is multi-market; matrix row 22). |
| `claim_family` | `"sni_belief.v1"` | Version in the family name. A v2 is a new family, never an in-place schema change. |
| `scope` | `{type:"entity", key:<listing symbol>}` | HK keys MUST carry `.HK` (`0700.HK`, `9988.HK`). Bare HK codes are refused. US keys are as listed (`BABA`). One listing per claim. An HKD/RMB counter is a different key and is never pooled (matrix row 23). |
| `bench` | string, **required** | Same market as `scope.key`. An omitted bench defaults to `SPY` (`_DEFAULT_BENCH` L1183), which makes every HK belief mixed-market and refused (matrix row 13). The *choice* of bench is S0/V1 design and is recorded in the prereg. |
| `direction` | `-1 / 0 / 1` | Still required by the existing validator. **Derived:** `sign(q50)`, or `0` inside `belief.dead_band`. The validator recomputes it and refuses a mismatch. It is never the headline score. |
| `horizon_d` / `horizon_unit` | `5 / 21 / 63`, `"trading"` | Limited to `GRADE_HORIZONS (5, 21, 63)` (L114). Anything longer is refused (no horizon above 63 is the do_not_redo of `WS:EVAL-OS-MEASUREMENT-LAW`). Multi-horizon = one claim per horizon sharing `belief.belief_id`. |
| `timestamp_quality` | `CRAWL_BOUNDED / PUBLISHER_STATED / DISCLOSURE_DATE` | Only the gradeable qualities (L1185). `EVENT_DATE`/`SNAPSHOT_DATE`/`CORRUPTED` are refused. |
| `target` | object | `target_kind ∈ {"price_return_distribution"}` (the only admitted kind at V0). `"kpi_reported_value"` is **reserved and refused** until the KPI outcome resolver is ratified (matrix rows 2 and 5). `return_basis ∈ {"close_to_close_price"}`: what `_leg_ret_in_window` actually computes, with no total-return claim. `relative_to_bench: bool`. `listing_currency ∈ {"HKD","USD"}` (informational). |
| `belief` | object | `belief_id` (sha256 of `model_spec_sha256 + target_spec_sha256 + scope.key + asof`). `representation ∈ {"quantiles","bins"}`. `levels[]` (quantile levels strictly increasing in (0,1), or bin edges strictly increasing). `values[]` (quantiles non-decreasing; bin probabilities ≥0 summing to 1±1e-9). `dead_band ≥ 0`. |
| `scoring_rule` | `"pinball_mean"` (quantiles) / `"log_loss_binned"` (bins) | Fixed by `representation`. Diagnostics (`reliability_curve`, `cone_coverage`, `brier_decomposition`) are reported, not used as the score. |
| `model_spec_sha256`, `target_spec_sha256` | 64-hex | Required. |
| `prereg_registration_id`, `prereg_digest_sha256` | string, 64-hex | Required. They point at the prereg instance (§7). |
| salt / `claim_id` | computed | The validator computes `salt = model_spec_sha256 + ":" + target_spec_sha256 + ":" + prereg_digest_sha256`. A caller-supplied `claim_id` or `salt` is **refused** for this family (matrix rows 7, 16, 17). |
| `supersedes_claim_id` | nullable string | Points at an earlier `sni_belief.v1` claim. The superseded claim is never altered. |
| `correction_kind` | `null / "design_change_supersede" / "data_convention_correction"` | Follows `DEC:PREREG-DESIGN-CHANGE-SUPERSEDES` and `DEC:PREREG-DATA-CONVENTION-CORRECTED-IN-PLACE`. The in-place kind applies to the prereg document only, never to a registered probability. |
| `provenance_kind` | `"prospective" / "reconstruction"` | A **label for readers only**. Cohort exclusion is enforced by the registration clock (`_cohort_prospective`, L1722), never by this field (no decorative backfilled flag). |
| `authority` | object, all `false` | `may_rank, may_gate, may_size, may_signal, may_escalate, may_trade`. The validator refuses any `true`. |
| grade-row `censoring_state` | `none / unpriceable_unclassified / delisted / halted / outcome_unpublished` | Written by the grader, not the registrant. `delisted` only from Data OS `security_master` evidence. `halted` only from a named halt source (none exists for HK today; matrix row 12). |

## 3. Owning module and test file for each change

| ID | Change | Owning module | Test file (existing module) |
|---|---|---|---|
| X1 | Family-gated validation of §2 (incl. unknown-key refusal, suffix rule, explicit bench, derived direction, authority all-false) | `engine/qledger.py::_validate_claim` (L1754) | `tests/test_qledger.py`, `tests/test_qledger_horizon_clock.py` |
| X2 | Computed salt; refuse caller `claim_id`/`salt` for the family | `engine/qledger.py::_prepare_claim` (L1899) / `_claim_id` (L1250) | `tests/test_qledger.py` |
| X3 | Family-dispatched scoring behind the existing `_matured_window` gate. Hoist `pinball`/`mean_pinball` (from `engine/pick_forward_dist.py` L578/L586) and binned log-loss (from `engine/k3e_eval1_forward.py::row_log_losses`) into `engine/grading_stats.py`, leaving re-exports at the old sites | `engine/qledger.py::grade_claim` (L2698); `engine/grading_stats.py` | `tests/test_qledger.py`; `tests/test_grading_stats.py`; `tests/test_grading_stats_calibration.py` |
| X4 | `censoring_state` on grade rows. Mapped from the existing refusal (`primary_leg_refused`) plus Data OS delisting evidence. A censored row counts in the coverage denominator | `engine/qledger.py::grade_claim`, `_cohort_rowless_class` (L2876) | `tests/test_qledger_horizon_clock.py` |
| X5 | Pin the family at `DISPLAY`; exclude it from `emit_ladder_states` enumeration and from the per-family block that `compute_track_record` (docstring L3436: "per desk and per claim-family") publishes to public `site/qledger/track_record.json`, until the §5 bridge is accepted | `engine/qledger.py::FAMILY_CONTROL_POLICY` (L1387), `emit_ladder_states` (L4738), `promotion_check_dispatch` (L4695), `compute_track_record` / `emit_track_record` (L3514) | `tests/test_qledger_control_policy.py` |
| X6 | Belief/target blocks outside the `backfill_regime_stamps` write set | `engine/qledger.py::backfill_regime_stamps` (L2145) | `tests/test_qledger.py` |
| X7 | HK prices reachable by the grader: an additive `data/hk_stocks/` fallback, in the existing china-fallback idiom | `engine/ai_desk.py::_close_series_uncached` (L236) | `tests/test_ai_desk.py` |
| X8 | Closed-period chunk `sha256` + `previous_manifest_sha256` for the belief *projection* (§6). This is C-series work, not V0 | the projection builder, reusing the `engine/oracle/timemachine.py` chunk/manifest pattern and `engine/qledger_store_protocol.py::verify_snapshot` (L595) | `tests/test_qledger_store_protocol.py` |

No new module, store, grader, registry, queue or scheduler appears in this table.

## 4. Masterplan-required tests → existing test or named new test (in an existing module)

| Masterplan §7 V0 test | Existing test(s) that already pin the mechanism | Named new test (existing module) |
|---|---|---|
| Identical registration counts once | `tests/test_qledger.py::test_register_persists_and_is_idempotent` (L111), `::test_register_batch_dedupe_keep_first` (L674), `::test_register_batch_error_isolation` (L662); `tests/test_qledger_control_policy.py::test_t10_a_deduped_batch_starts_nothing` (L779) | `tests/test_qledger.py::test_sni_belief_identical_registration_counts_once` (computed salt is deterministic; second register is a no-op) |
| Changed model/spec or target is a new belief/version | none family-specific (salt is caller-chosen today) | `tests/test_qledger.py::test_sni_belief_changed_spec_or_target_is_a_new_claim`; `::test_sni_belief_refuses_caller_supplied_claim_id_or_salt` |
| Outcome arrival cannot alter published probabilities | keep-first registration (L111, L674); `::test_backfill_regime_stamps_null_only` (L787) shows the one post-registration writer | `tests/test_qledger.py::test_sni_belief_block_is_byte_identical_after_grading_and_regime_backfill`; C-series: `tests/test_qledger_store_protocol.py::test_sni_belief_closed_chunk_hash_chain_verifies` |
| An interval is not scored before maturity | `tests/test_qledger.py::test_grade_not_matured_returns_empty` (L222); `tests/test_qledger_control_policy.py::test_f5_a_replay_judges_maturity_on_the_replay_date_not_the_wall_clock` (L2041) | `tests/test_qledger.py::test_sni_belief_interval_is_not_scored_before_maturity` |
| Unpriceable / delisted / halted produce a declared censoring state | `tests/test_qledger_horizon_clock.py::test_a_leg_missing_the_windows_exit_bar_is_refused_not_graded_short` (L561) | `tests/test_qledger_horizon_clock.py::test_sni_belief_censoring_state_is_declared_never_dropped` (parametrized: `unpriceable_unclassified`, `delisted`, `halted`, `outcome_unpublished`) |
| HK and US clocks stay separate | `tests/test_qledger_horizon_clock.py::test_an_hk_claim_resolves_on_the_hk_calendar` (L914), `::test_require_single_clock_refuses_a_mixed_set` (L290), `::test_an_unknown_market_is_never_answered_with_another_markets_sessions` (L1020) | `tests/test_qledger_horizon_clock.py::test_sni_belief_hk_claim_with_default_spy_bench_is_refused_as_mixed`; `::test_sni_belief_requires_suffixed_hk_scope_keys`; `tests/test_ai_desk.py::test_close_series_reads_hk_stocks_fallback` (X7) |
| Backfills never count as prospective | `tests/test_qledger_control_policy.py::test_t5_retrospectively_registered_controlled_rows_never_join_the_cohort` (L396), `::test_t5_registering_an_old_asof_claim_starts_no_clock` (L428); `tests/test_qledger_desk_adapter.py::test_anchor_at_registration_claim_joins_prospective_cohort_both_reference_dates` (L364) | `tests/test_qledger_control_policy.py::test_sni_belief_reconstruction_label_never_enters_prospective_cohort` (the label is not the gate; the clock is) |
| (added by V0) Authority stays false / never promoted | `LADDER_RUNGS` (L3531) | `tests/test_qledger_control_policy.py::test_sni_belief_family_is_pinned_display_and_never_promoted` |

## 5. The bridge rule: return/hit grading is not probabilistic support

Until X3 is merged **and** the evaluation owner accepts it, any SNI surface that shows a qledger grade must label it as a directional summary ("direction right/wrong over N matured beliefs"). It must never be labelled forecast skill, calibration or probability accuracy.

"Accepted bridge" means:

1. X3 merged, with the §4 tests green.
2. A reliability diagnostic (`grading_stats.reliability_curve` for bins, `cone_coverage` for quantiles) computed on **matured, prospective** beliefs only.
3. The `WS:EVAL-OS-MEASUREMENT-LAW` owner records acceptance.

Hindsight facts (what 0700.HK or 9988.HK actually did) are outcomes, never historical forecasts. No SNI belief exists before X1 lands, so there is no SNI track record to show.

## 6. Immutable publication via the oracle timemachine manifest pattern (not a new store)

- **Where rows live:** qledger (append-only, keep-first). That is the only record store.
- **What is published:** the masterplan §5.1 belief/forecast projection, a *reader* over accepted `sni_belief.v1` rows and grades. It is published with the existing `engine/oracle/timemachine.py` + `scripts/build_oracle_timemachine.py` shape:
  - one manifest (versioned `schema_version`) listing period chunks `<tier>_<period>.json`
  - a reader loads the manifest, then only the chunks it needs
- **What V0 adds to the pattern:** the timemachine has no content hashes today (matrix row 20). Each closed-period chunk gains `sha256`, and the manifest gains `previous_manifest_sha256`. This is the hash-chain idiom already used by the Terminal `event_workspace` manifest (`previous_generation_id`, `previous_manifest_sha256`) and verified with `engine/qledger_store_protocol.py::verify_snapshot`.
  - A closed chunk is never rewritten. A correction is a new claim (§2 `supersedes_claim_id`) and appears in a later chunk.
  - The open period is the only mutable chunk.
  - Time Machine views read retained chunks and never recompute (masterplan §7 P0).
  - The manifest is the immutable record. It is not a compact pointer (`DSC:FF-1-IMMUTABLE-MANIFEST-IS-NOT-A-COMPACT-POINTER`).
- **What is not built:** a forecast store, a queue, a scheduler, or a second ledger.

## 7. Prereg-schema family versus qledger

| Holds | Prereg schema family (`contracts/research/*_prereg.v1.schema.json`; pattern instances: `k3e_expectation_market_dynamics_evaluation_prereg.v1`, `momoedge_oracle_completion_benchmark_prereg.v1`; runtime idiom `engine/entry_radar/replay/prereg.py`) | qledger (`engine/qledger.py`) |
|---|---|---|
| What | The **design**: target definitions, model spec (whose sha256 is `model_spec_sha256`), horizon set, bench per market, scoring rule and diagnostics, metric constants, held-out windows, evidence budget, cohort definition, amendment law | The **registrations** (one row per belief × horizon), maturity, grades, `censoring_state`, cohort/coverage accounting |
| Mutability | Design change ⇒ new version that supersedes the old one (`DEC:PREREG-DESIGN-CHANGE-SUPERSEDES`); data-convention fix ⇒ in place (`DEC:PREREG-DATA-CONVENTION-CORRECTED-IN-PLACE`) | Append-only, keep-first. Grades written separately. A correction is a new claim |
| Identity | `prereg_registration_id` + `prereg_digest_sha256` | `claim_id` (computed salt includes the prereg digest) |
| New artifact SNI adds | one prereg **instance** in the existing schema family (S0/V1 authors it, not V0) | one family (`sni_belief.v1`) |

Neither side is a new scientific registry. `DEC:EVAL-OS-RECOVERY-ARCHITECTURE-FREEZE` keeps T1 as the only engine registry.

## 8. Rejected alternatives

1. **(b) Additive extension to an existing family.** Rejected.
   - The natural host, `stock_desk`, is a live matched-control family. Its claims, cohort statistics, ladder state and public track record would change meaning if distribution fields and a different scoring rule entered it. `FAMILY_CONTROL_POLICY` and the cohort machinery partition by `claim_family`, so a family boundary is exactly what isolates SNI from a promotion-bearing population.
   - The do_not_redo "do not re-mint stock_desk's clock" is a second reason to keep out.
   - K3E EVAL-1 is not a general family. It is a pre-registered study with its own trial identity, and borrowing it would spend or contaminate that trial.
2. **(c) ESCALATE.** Rejected as unnecessary. Every required property maps onto an existing owner plus an additive, family-gated change. The three UNSUPPORTED rows are *owner-ratification* gaps (the KPI resolver from the Company Event owner, the HK price fallback, a halt source), not architectural forks a Chairman/Sol ruling must settle.
3. **A dedicated SNI forecast store.** Forbidden by the commission. It contradicts `DEC:MARKET-BELIEF-IS-COMPOSITION-NOT-TRUTH-STORE` and `DEC:EVAL-OS-RECOVERY-ARCHITECTURE-FREEZE`.
4. **A bespoke SNI grader.** Forbidden. Scoring stays in `engine/grading_stats.py`, dispatched by `grade_claim`.
5. **Untyped pass-through** (just put SNI fields in a claim today). Rejected. `_prepare_claim` stores unknown fields unvalidated, so a malformed distribution would register silently, and its `claim_id` would ignore the spec (matrix rows 1, 7).

## 9. Sequencing gates (binding on implementers)

- **No `engine/qledger.py` registration, batch or backfill edits while PR #8042 is open.** This covers X1, X2 and X6. See `SNI_V0_8042_COLLISION_CHECK.md`.
- X7 (`engine/ai_desk.py`) is disjoint from #8042 and may land independently.
- X3's `grading_stats` hoist is disjoint and may land first, as a pure refactor.
- X5 must land **in the same PR** as X1, or before it. A family that can register before it is pinned to DISPLAY would be auto-published by `emit_ladder_states`.
- KPI beliefs stay refused until the Company Event / Earnings owner ratifies an as-first-reported outcome resolver.

## Adversarial review

1. **"A family-dispatched scorer inside `grade_claim` is a bespoke grader with extra steps."**
   Disposition: rejected, with a guard. The scoring functions live in `engine/grading_stats.py` (shared, tested) and are hoisted, not rewritten. Dispatch sits behind the same `_matured_window` gate and the same refusal paths every family uses. The guard: X3's PR must contain no SNI-specific arithmetic outside `grading_stats`. A reviewer checks this by grepping the diff for numeric code in `qledger.py` under the family branch.
2. **"This is K3E's job; SNI should register through K3E's study."**
   Disposition: rejected. K3E EVAL-1 is a pre-registered trial with its own identity and budget, and SNI beliefs registered under it would spend or contaminate that trial. SNI *reuses K3E's metric constants and log-loss primitive*, which is the reusable part, without joining its trial.
3. **"`emit_ladder_states` enumerates every `claim_family` found in claims.jsonl (L4738 docstring) and `compute_track_record` publishes per-family stats to the public `site/qledger/track_record.json`, so SNI results go public the moment the first row registers."**
   Disposition: accepted as a real defect of naive (a). This is why X5 is mandatory and must land with or before X1. Named test: `test_sni_belief_family_is_pinned_display_and_never_promoted`.
4. **"`_claim_id` ignores the model spec; two specs with the same direction collide and the second is silently dropped."**
   Disposition: accepted. That is today's behaviour, because the salt is caller-chosen. X2 computes the salt from the spec, target and prereg digest, and refuses caller ids. Named tests in §4 row 2.
5. **"`backfill_regime_stamps` rewrites stored claim rows, so the ledger is not immutable."**
   Disposition: partially accepted. It fills null regime stamps only (L787 test) and already skips `.HK` (L832 test). It does not touch belief fields today. X6 makes that a pinned invariant (byte-identity test) rather than an accident of the current write set.
6. **"The timemachine has no hashes, so 'immutable publication' is aspirational."**
   Disposition: accepted. §6 adds chunk `sha256` + `previous_manifest_sha256`, verified by the existing `qledger_store_protocol.verify_snapshot`. The claim of immutability is made only for chunks that carry the hash, and only after X8 (C-series).
7. **"An HK belief inherits `SPY` as bench and gets refused, or is silently graded against US sessions."**
   Disposition: accepted as found. It is refused, not graded on US sessions, because `resolve_claim_market` fails closed on mixed legs (L975; test L290). §2 makes `bench` mandatory and same-market, so the refusal becomes a registration-time error with a reason instead of a surprise.
8. **"Even with every field right, HK beliefs cannot be scored."**
   Disposition: accepted. The grader's price loader does not read `data/hk_stocks/` (matrix row 14). X7 is a precondition for any HK score. Until it lands, an HK belief grades to `primary_leg_refused` and is counted, not hidden.
9. **"Market will be inferred from the ticker after all."**
   Disposition: rejected. `sni_belief.v1` has no `DESK_MARKET` entry. HK requires an explicit `.HK` suffix, a leg-level fact that `_ticker_market` honours outright. Bare HK codes are refused for the family. A bare US ticker resolves through the existing rule-6 path, which the do_not_redo already governs.
