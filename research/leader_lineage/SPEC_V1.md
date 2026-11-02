# Leader lineage descriptor — SPEC V1 (frozen 2026-10-11)

**Status:** Chairman-requested requirement (PR #8750 comment, 2026-10-11T01:20Z: "differentiate failed
leadership vs deep corrective continuation (PLTR case, 2026-10-10)"). Built as a SEPARATE additive
source slice. It is NOT #8750 functionality, not live, and carries no authority. Phase 1 = this
module + tests + these two documents. Phase 2 (Leader Radar / Terminal / Prophet integration) is
specified in `CONSUMER_SPEC.md` and starts only after #8750 is on `origin/main` and the Leader Pivot
owner (#8649) has admitted the read path.

Era `leader-lineage-descriptive-2026-10-11`, schema `leader_lineage.v1`,
evidence mode `RECONSTRUCTED_CURRENT_VINTAGE`, authority `may_rank/may_gate/may_size/may_trade/may_alert`
all `false`. Nothing here ranks, gates, sizes, trades or alerts, and nothing here may be promoted to
any of those without prospective (post-freeze) evidence and a separate authority decision.

## 0. Collision-free slice (one writer per surface)

| Owned by this slice (NEW files only) | Never touched by this slice |
|---|---|
| `engine/leader_lineage.py` | `engine/leader_recovery*.py`, `engine/rs_leader_highs.py`, `scripts/build_leader_radar.py`, `templates/leader_radar.html.j2` — PR #8750 (RS LEADER deep recovery) |
| `tests/test_leader_lineage.py` | `engine/entry_radar/replay/*` — PR #8649 (Leader Pivot, P0B-30M owner) |
| `research/leader_lineage/SPEC_V1.md`, `research/leader_lineage/CONSUMER_SPEC.md` | `engine/leadership_lab/*` — PR #8586 (leadership lab) |

Event ownership stays with `engine/leader_recovery_observations.py` (append-only, default-off). This
module keeps NO ledger, writes NO file, and replays from the caller's price history every call. If a
future phase feeds it observed first-seen events, the evidence mode changes to an observed one; until
then every output is a current-vintage reconstruction and is labelled so.

## 1. Inputs (all caller-supplied, all read-only)

| Input | Type | Rule |
|---|---|---|
| `close`, `benchmark` | `pd.Series` indexed by naive session dates | Values after `as_of` are cut. Duplicate dates and boolean prices raise. A non-numeric value is a gap (`nan`), never carried forward. |
| `as_of` | `datetime.date` | The read date. The row for `as_of` is the "current" row. |
| `sessions` | iterable of naive session dates | The caller's COMPLETED-session calendar. See §2. |
| `ticker` | str | Episode identity seed only (`episode_id = sha256(ticker|leadership_qualified_at)[:16]`). |
| `peers` | mapping ticker → close `pd.Series` | Leave-one-out peer basket (the subject ticker is excluded by key). Absent → rung R4b stalls, see §5. |
| `fundamentals` | rows `{as_of, state, source_ref}` | Owner-dated. `state ∈ {PRESENT, NONE, STABILIZED, UNKNOWN}`. `STABILIZED` dated on/after the trough fills R5. |
| `volume_demand` | rows `{as_of, state, source_ref}` | Owner-dated. `state ∈ {DISTRIBUTION, ACCUMULATION, …}`. `ACCUMULATION` dated on/after the trough fills R6. |
| `pivot` | `{confirmed_on}` | READ ONLY from the intraday pivot owner's published descriptor (#8649). This module never computes 15m/30m state. |

Owner rows are projected by `as_of` on each session: the newest owner row dated on or before the
session is used; an undated row is ignored; nothing is ever back-dated into the history. Absent owner
input → the corresponding field is `UNKNOWN` and no timestamp is fabricated.

## 2. Calendar law — strict, deliberately stricter than the incumbent

The `sessions` calendar must be strictly increasing, non-empty, and END exactly at `as_of`. A session
dated after `as_of` is a contradiction and the whole read fails closed with
`state: UNAVAILABLE, reason: invalid_or_incomplete_calendar` — it is never silently dropped.

This differs on purpose from `engine/leader_recovery.py` (which filters its calendar to `<= as_of`).
Rationale: the price SOURCES may legitimately extend past `as_of` (a store refreshed after the read
date) and are cut; the CALENDAR is the caller's assertion of what was complete at `as_of`, and an
assertion that includes the future is a caller bug the descriptor must surface, not repair. Point-in-
time replay (§8) depends on this.

Sessions before the first date both sources cover are dropped (nothing can be said there). If either
source is empty the read is `UNAVAILABLE / missing_source`.

## 3. Leadership qualification and episode lifecycle

Qualification is the same transparent price/RS proxy as the incumbent (`PRICE_RS_PROXY`): on a session
with more than `high_window` completed sessions behind it, a strict new RS high versus the previous
`high_window` sessions AND a positive `high_window` absolute return AND a close above the slow
average. The first qualification opens an `ACTIVE` episode; a qualification while the current episode
is not `ACTIVE` CLOSES it (`close_reason: re_admitted_new_episode`) and opens a NEW episode whose
`prior_episode_id` links back. A failure is therefore never a lifetime delisting.

Phases: `ACTIVE → DAMAGED → REPAIRED | FAILED`. `DAMAGED` opens on the first close whose drawdown from
the episode price ATH reaches `deep_fraction`; the correction peak (price + RS at the peak) is frozen
then, and the trough is tracked downward until R2 (reclaim of the fast average) lands.

### Episode fields (every one dated or explicitly `null`)

`episode_id`, `prior_episode_id`, `leadership_qualified_at`, `phase`, `break_class`, `revised_from`,
`revised_on`, `history_complete`, `closed_on`, `close_reason`,
`price_ath` / `price_ath_on` and `rs_ath` / `rs_ath_on` (SEPARATE — a price ATH reclaim never implies an
RS ATH reclaim, Chairman point 4), `correction_peak_price` / `correction_peak_on` /
`rs_at_correction_peak`, `correction_trough_price` / `correction_trough_on` / `rs_trough`,
`max_close_drawdown`, `rs_peak_to_trough`, `sessions_below_50` and `sessions_below_200`
(`{consecutive_max, total, current}`), `repair_floor_price`, `failed_on`, `structural_on`,
`structural_watch`, `revisable`, `revision_requires`, `ladder` (§5), `ladder_order_violations`,
`ladder_stalled`, `distribution_evidence`, `accumulation_evidence`, `fundamental_deterioration`,
`rs_vs_peer_basket`.

## 4. Two independent axes (Chairman point 2) — never collapsed into one label

**Thesis** `thesis_state ∈ {INTACT, DAMAGED, CONTRADICTED, UNKNOWN}`:

1. `CONTRADICTED` iff `contradiction_evidence` is non-empty. The only two admissible items are
   `fundamental_deterioration_present` (owner-dated) and `structural_break_no_slow_reclaim_by_horizon`.
2. else, phase `DAMAGED` or `FAILED` → `DAMAGED`, EXCEPT when `ladder_stalled` is non-empty → `UNKNOWN`.
   Settled semantic: *every price rung cleared but an owner input is missing means the thesis is
   unproven, never manufactured* — neither "damaged" nor "repaired" is asserted without the evidence.
3. else (phase `ACTIVE` or `REPAIRED`), `INTACT` only when `fundamental_deterioration.state == NONE`
   from an owner row; otherwise `UNKNOWN`. An `UNKNOWN` thesis is never rendered as healthy.

**Setup** `setup_state ∈ {WATCH, RESET, REBUILDING, RE_IGNITION, EXTENDED, INVALIDATED}`:

- phase `FAILED` → `INVALIDATED`
- phase `ACTIVE` / `REPAIRED` → `EXTENDED` when close > fast average × (1 + `extension_fraction`),
  else `RE_IGNITION` (REPAIRED) or `WATCH` (ACTIVE)
- phase `DAMAGED` → `REBUILDING` once R1 or R2 has landed, else `RESET`

A `FAILED_BREAK` row carries `revisable: true` and
`revision_requires: [new_leadership_qualification, ordered_ladder_R1_R4, owner_dated_R5_R6]`.

## 5. Re-admission = chronological evidence ladder (Chairman point 3)

| Rung | Key | Rule |
|---|---|---|
| R1 | `higher_low_confirmed_on` | the last `higher_low_sessions` closes all hold above the frozen trough, at least that many sessions after it; a new lower close before R2 resets the trough and clears R1 |
| R2 | `reclaim_50d_on` | `confirm_sessions` consecutive closes above the fast average, only after R1; sets `repair_floor_price` = the trough |
| R3 | `reclaim_200d_on` | `confirm_sessions` consecutive closes above the slow average, strictly AFTER R2 |
| R4a | `rs_vs_spy_rising_on` | `rs_window`-session relative return vs the benchmark > 0 on `confirm_sessions` consecutive closes, after R3 |
| R4b | `rs_vs_peer_basket_rising_on` | the same versus the leave-one-out basket; absent basket → rung STALLS |
| R5 | `revisions_news_stabilized_on` | owner-dated only (`fundamentals` `STABILIZED` on/after the trough) |
| R6 | `volume_demand_confirmed_on` | owner-dated only (`volume_demand` `ACCUMULATION` on/after the trough) |
| R7 | `pivot_confirmed_on` | read-only from the pivot owner's descriptor; must be on/after the trough and not after the session |

A rung reached out of order is NOT counted: it is appended to `ladder_order_violations`
(`{rung, on, missing}`) and the rung stays `null`.

**Break classes** (`break_class ∈ {UNRESOLVED, STRUCTURAL_BREAK, REPAIRED_TREND, FAILED_BREAK}`):

- `REPAIRED_TREND` (phase `REPAIRED`) iff R1–R4a AND R4b are all present in order. A prior
  `STRUCTURAL_BREAK` is then recorded in `revised_from` / `revised_on`, never erased.
- `STRUCTURAL_BREAK` iff the longest consecutive stay below the slow average reaches
  `structural_below_slow` AND no R3 by `horizon_sessions` after the trough. `structural_watch` is true
  while the stay condition holds before the horizon.
- `FAILED_BREAK` (phase `FAILED`) iff a close falls below `repair_floor_price` after R2.
- Stall: price rungs R1–R4a complete but no peer basket was supplied → `ladder_stalled =
  [rs_vs_peer_basket_rising_on]`, class returns to `UNRESOLVED` (a prior structural call is recorded as
  revised), thesis `UNKNOWN` (§4). No verdict either way.

The long deep-recovery lane COMPLEMENTS `us_leader_pullback`; the shallow lane's thresholds, population
and files are untouched (`test_shallow_reset_never_opens_the_deep_phase`).

## 6. Frozen thresholds (fixed BEFORE any outcome evaluation; never fitted)

`LineageSpec(high_window=252, fast_window=50, slow_window=200, rs_window=21, confirm_sessions=3,
deep_fraction=0.20, extension_fraction=0.10, higher_low_sessions=10, structural_below_slow=40,
horizon_sessions=126)`. The dataclass is frozen and validates itself (`invalid_window`,
`invalid_window_order` — `rs < fast < slow <= high`, `invalid_horizon_order` — `structural < horizon`,
`invalid_fraction` — open interval (0, 1)).

`definition_sha256` = sha256 of the sorted JSON of the spec, stored on every `describe_lineage` read.
**Default digest (pinned by test):**
`cf43eb5deb69ca7b3c14aa5d96f72a1c8b829b0c015e364293f04763bfc1c5cf`.
Any threshold change mints a new digest and a new era; results across digests are never pooled.

## 7. Tests (Chairman: "below-200 long duration and failed vs repair transitions")

`tests/test_leader_lineage.py`, 15 tests, synthetic fixtures only (no licensed data in the repo):

| Req | Test |
|---|---|
| T1 PLTR-shaped 43-session below-200 stay → structural until the ordered ladder repairs it | `test_pltr_shaped_deep_stay_is_structural_until_the_ordered_ladder_repairs_it`, `test_owner_dated_stabilisation_makes_the_repaired_thesis_intact_and_fills_r5` |
| T2 failed path, CONTRADICTED only with evidence, revisable | `test_failed_break_after_reclaim_is_invalidated_but_revisable_and_only_contradicted_with_evidence` |
| T3 shallow reset never opens the deep phase | `test_shallow_reset_never_opens_the_deep_phase` |
| T4 price ATH vs RS ATH persist separately | `test_price_ath_reclaim_does_not_imply_rs_ath_reclaim` |
| T5 out-of-order evidence never counts | `test_out_of_order_rungs_are_recorded_as_violations_and_never_counted`, `test_reclaim_before_a_higher_low_is_a_violation_not_a_rung` |
| T6 missing owners → UNKNOWN, ladder stalls, no fabricated dates | `test_missing_owner_inputs_are_unknown_and_stall_the_ladder_without_a_verdict`, `test_owner_dated_volume_and_pivot_rows_are_projected_read_only` |
| T7 PIT: a later close never alters an earlier row | `test_a_later_close_never_alters_an_earlier_row`, `test_missing_session_is_a_gap_not_a_carried_value`, `test_calendar_and_source_guards_fail_closed` |
| T8 digest stability + authority all false + no incumbent import | `test_spec_is_frozen_checked_and_digested`, `test_module_imports_no_incumbent_lane_and_carries_no_authority`, `test_describe_lineage_reports_descriptive_authority_and_linked_episodes` |

## 8. Epistemic boundaries

- **Point in time.** One row per completed session; a row is a function of sessions at or before its
  date only. Sources are cut at `as_of`; the calendar is asserted by the caller (§2).
- **No forward fill.** A missing or invalid session clears the rolling evidence, marks
  `history_complete: false`, and emits an `UNAVAILABLE / missing_or_invalid_completed_session` row.
- **Reconstructed, not observed.** `evidence_mode = RECONSTRUCTED_CURRENT_VINTAGE`: dates are when the
  rule would have fired on today's history, not first-seen timestamps. Never call these snapshots
  prospective.
- **PLTR is illustrative only** (Chairman point 5). The 2026 case (June 1 → June 25 close −33.2 %,
  43 sessions below the 200d, RS 0.213 → 0.146, Oct 8 close $198.78 with RS 0.2568 still below the prior
  252-session RS high 0.3065) motivates the shape of T1 and is never a positive label on any row.
  Shallow-reset winners (AVGO/NVDA-type) and true-failure controls are evaluation cohorts, not labels.
- **Negative headline preserved.** The incumbent repair-vs-immediate research (−5.18 pp paired,
  −1.22 pp vs ma50; re-ignition −6.95 / −2.71) stands; this descriptor adds lineage context and asserts
  no incremental edge.
- **No authority promotion** until prospective post-freeze evidence exists AND a separate authority
  decision is recorded; the module's `AUTHORITY` block is tested to be all-false.

## 9. Delivery plan

1. Phase 1 (this slice): module + tests + docs, CI step naming the test file, `git diff --check`,
   the 9-file RS LEADER recipe unchanged (401 passed), ship loop to merge.
2. Phase 2 (after #8750 on `origin/main` and #8649 admission): `CONSUMER_SPEC.md` §2 payload
   attached by the Leader Radar builder under its own PR, additive to `rows[i].display_chips` and a
   top-level `lineage_roster`; Terminal reads the same payload; Prophet receives descriptive context
   only.
3. Evaluation (separate research PR, never a row label): PIT membership, matched controls, rejection
   evidence, forward net-of-cost outcomes, episode-level honest N, in-sample disclosure.
