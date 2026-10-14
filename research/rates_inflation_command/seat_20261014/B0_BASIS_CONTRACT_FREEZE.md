# B0 — Basis-aware contract freeze (`rates_command_basis.v1`) — SEAT RULING, binding

Seat fc3dfe4b (Fable Meta-CEO), 2026-10-14. Implements MASTERPLAN §4–§5 and A06. Names, fields,
enums and refusal codes below are FROZEN: an implementer may add private helpers and extra
`limitations` text, but may not rename, drop, merge or re-mean a frozen item. A needed change is
returned to the seat as a spec delta, never improvised.

## 1. Files (ORCH-A is the single writer)

- `engine/rates_command_basis.py` — PURE module: stdlib + existing numeric conventions only; no
  network, file I/O, LLM, clock reads (`now()`), source acquisition or publication. Frozen
  dataclasses (`@dataclass(frozen=True)`), tuples not lists, JSON round-trip via `to_dict()` /
  `from_dict()`.
- `contracts/rates_command_basis.v1.schema.json` — JSON Schema (draft 2020-12) for the
  serialized `QualifiedObservation`, `ComparisonResult`, `PathIdentification`; `$id` ends in
  `rates_command_basis.v1.schema.json`; `additionalProperties: false` on each record.
- `tests/test_rates_command_basis.py` — new suite (enrolment in `.github/ci/legacy-jobs.yml`
  is a seat act; return the patch).
- `SCHEMA_VERSION = "rates_command_basis.v1"`.

## 2. Enums (string-valued; serialized as the value)

`EvidenceClass`: `official_measurement` | `house_estimate` | `market_implied_expectation` |
`survey_participant_projection` | `estimated_decomposition` | `hypothetical_scenario`.

`ValueState`: `present` | `missing` | `withheld` | `stale` | `refused`.
(`value` is a float only when `value_state == "present"`; otherwise `value is None`. Missing is
never 0, never "neutral", never "quiet".)

`Precision`: `minute` | `day` | `month` | `unknown`.

`ComparisonStatus`: `directly_comparable` | `comparable_after_transformation` |
`not_comparable` | `not_identified` | `unavailable`.

`PathStatus`: `identified_conditional` | `feasible_alternatives` | `inconsistent` |
`missing_inputs`.

`NA = "n/a"` — the explicit not-applicable marker for basis fields irrelevant to a target.
`None` on a basis field means UNKNOWN. Unknown is never defaulted.

## 3. `QualifiedObservation` (frozen; every field present on the wire)

| Field | Type | Meaning |
|---|---|---|
| `obs_id` | str | `sha256` (first 16 hex) of the canonical JSON of all other fields — exact operand reference. |
| `subject` | str | Series or contract identity (`CPIAUCSL`, `PCEPI`, `PAYEMS`, `ICSA`, `ZQX26`, `SR3Z26`, `DGS10`, `DFII10`, `THREEFYTP10`, `sep_median_2026`, …). |
| `evidence_class` | EvidenceClass | Class travels with the value; a transform never changes it. |
| `value` | float \| None | Present only when `value_state=="present"`. |
| `value_state` | ValueState | |
| `unit` | str | One of `pct_mom`, `pct_yoy`, `pct_ann_rate`, `pct_3m_ann`, `index_level`, `thousands_persons`, `persons`, `bp`. |
| `target` | str | Economic target, e.g. `cpi_u_all_items_mom_sa_first_print`, `cpi_u_core_mom_sa_first_print`, `pce_headline_mom_sa`, `nfp_change_first_print`, `icsa_level`, `effr_monthly_average`, `sofr_compounded_quarter`, `fed_funds_target_midpoint`, `sep_fed_funds_year_end_median`, `ust_par_yield`, `ust_zero_yield`, `ust_real_par_yield`, `inflation_compensation`, `term_premium_kw`, `term_premium_acm`. |
| `basket_or_index` | str \| None | `CPI-U` / `PCE` / `EFFR` / `SOFR` / `UST` / `TIPS` / NA. |
| `reference_start` / `reference_end` | ISO date \| None | Reference interval (month, IMM quarter, SEP year-end, observation date→maturity date for a yield). |
| `tenor` | str \| None | `10y`, `2y`, … or NA. |
| `observation_time` | ISO \| None | Quote/observation timestamp at its TRUE precision. |
| `observation_precision` | Precision | Day-level receipts stay `day`; never upgraded. |
| `seasonal_treatment` | `sa` \| `nsa` \| NA \| None | |
| `rate_index` | `EFFR` \| `SOFR` \| NA \| None | |
| `averaging_law` | `arithmetic_calendar_day` \| `compounded_business_day` \| `point` \| NA \| None | |
| `curve_convention` | `par` \| `zero` \| `forward` \| `real_par` \| NA \| None | |
| `source` | str \| None | Owner-qualified source id, e.g. `fred:CPIAUCSL`, `rate_futures:ZQ`, `release_forecast:v2`. None ⇒ source UNKNOWN (never a named default — A03). |
| `source_version` | str \| None | |
| `content_ref` | str \| None | Hash/blob of the input artefact the value was read from. |
| `first_public_evidence` | ISO \| None | Earliest evidence of public availability. |
| `first_public_precision` | Precision | ALFRED vintage ⇒ `day` (A09). |
| `admitted_at` | ISO \| None | House observation/admission time. |
| `cutoff` | ISO (required) | Publication cutoff the observation was qualified at. |
| `model_id` | str \| None | MRI model id or KW/ACM identity; NA for official data. |
| `target_epoch` | str \| None | MRI model/target epoch (legacy vs current kept distinct — A04/A11). |
| `vintage` | str \| None | Release vintage / settlement date / SEP release date. |
| `rights` | `public_official` \| `redistribution_limited` \| `display_only` \| `unknown` | `unknown` blocks export, not display of the refusal. |
| `quality` | tuple[str] | Flags from: `stale`, `carried`, `interpolated`, `fallback_strip`, `proxy_vintage`, `accuracy_withheld`, `benchmark_only`, `experimental`. |
| `authority` | str | Always `display_only` in this programme; never escalates. |
| `limitations` | tuple[str] | Free text. |

`qualify_observation(value: object, metadata: dict, cutoff: str) -> QualifiedObservation`
- Missing metadata keys become `None` (UNKNOWN), never guessed. `value` that is None/NaN/"" ⇒
  `value_state="missing"`, `value=None` unless metadata supplies `withheld`/`stale`/`refused`.
- If `first_public_evidence` or `observation_time` is later than `cutoff` (compared at the
  coarser of the two precisions), the observation is returned with `value_state="refused"`,
  `value=None`, limitation `after_cutoff` — the number never leaks past its cutoff.
- A cutoff or evidence stamp that cannot be parsed refuses the value (`cutoff_unparsable` /
  `evidence_time_unparsable`). The value is never admitted unproven.
- **FQ2, as merged in #9233.** An unknown evidence time stays ADMITTED, with a visible tag in
  `limitations`:
  - no `first_public_evidence` and no `observation_time` → `evidence_time_unknown`;
  - an `observation_time` but no `first_public_evidence` → `first_public_evidence_unknown`;
  - both stamped → no tag.

  A refused record gets neither tag. The tag survives `to_dict`/`from_dict`. Cutoff-strict
  consumers refuse an `evidence_time_unknown` operand fail-closed; the D0 point-in-time cutoff
  is the first of these. B0 does not refuse it, because display of a dated official value
  must not depend on a stamp the source never carried.

## 4. `ComparisonRule` and `ComparisonResult`

`ComparisonRule(rule_id, version, purpose, left_constraints: dict, right_constraints: dict,
match_fields: tuple[str], transform: str | None, output_unit: str)` — constraints map a field to
the tuple of allowed values; `match_fields` must be equal on both sides and KNOWN (not None).

`ComparisonResult(status, difference, range, unit, rule_id, rule_version, transform,
assumptions: tuple[str], limitations: tuple[str], reason: str, left_ref, right_ref,
left_cutoff, right_cutoff)` — `difference`/`range` are None unless status is
`directly_comparable` or `comparable_after_transformation`.

`compare_qualified(left, right, rule)` evaluation order (first hit wins; `reason` codes FROZEN):
1. either operand `value_state != "present"` → `unavailable`, `reason="operand_<state>:<side>"`.
2. either `rights == "unknown"` and rule purpose is `export` → `not_comparable`, `rights_unknown`.
3. operand violates the rule's constraints → `not_comparable`, `constraint:<field>:<side>`.
4. any `match_fields` entry is None on either side → `not_comparable`, `unknown_basis:<field>`.
5. any `match_fields` entry differs and the rule has no transform bridging it →
   `not_comparable`, `basis_mismatch:<field>`.
6. rule is a decomposition/attribution rule whose answer is not identified by the operands →
   `not_identified`, `underidentified:<what>` (with the feasible alternatives in `limitations`).
7. otherwise compute: `directly_comparable` (no transform) or `comparable_after_transformation`
   (named transform recorded in `transform` and its assumptions in `assumptions`).
Difference unit conversions are explicit (`pct`→`bp` ×100 only when `output_unit=="bp"`).

## 5. Frozen first-slice rule registry (`RULES: dict[str, ComparisonRule]`)

| rule_id | Purpose | Outcome law |
|---|---|---|
| `forecast_vs_first_print.v1` | house forecast vs official first print | match `target`, `basket_or_index`, `reference_start`, `reference_end`, `unit`, `seasonal_treatment`, `target_epoch`; left `house_estimate`, right `official_measurement` with target ending `_first_print`. Revised value as right operand ⇒ `constraint:target:right`. |
| `same_basis_level_change.v1` | same series, two dates | match everything except dates/vintage; direct difference. |
| `zq_month_vs_policy_midpoint.v1` | ZQ monthly-average EFFR vs current target midpoint | `comparable_after_transformation` with transform `monthly_average_vs_level` and assumption `effr_minus_midpoint_bp=<explicit>`. The gap is APPLIED in the rule's output unit (bp): `difference = (ZQ − midpoint)×100 − effr_minus_midpoint_bp` for pct operands, `(ZQ − midpoint) − effr_minus_midpoint_bp` for bp operands; a pct output subtracts the gap/100 (midpoint-equivalent; amendment B0-FIX6 — the raw ZQ−midpoint spread is the EFFR–midpoint basis, never an implied policy change). No gap is ever defaulted. An explicit basis that is missing, None, a bool, non-numeric or non-finite, or operands in mixed units ⇒ `not_identified`, `underidentified:effr_target_basis`. Assumptions record `effr_minus_midpoint_bp=<gap>` and `effr_gap_applied_in=<unit>`. |
| `sr3_vs_zq.v1` | SR3 quarter vs ZQ month | `not_comparable`, `basis_mismatch:rate_index` (no automatic SOFR–EFFR basis, no fallback equivalence — A15/A18). |
| `sep_vs_market_year_end.v1` | SEP year-end median vs market-implied | comparable only when the market operand's reference interval contains the SEP year-end month (transform `year_end_interval_match`, limitation "participant appropriate-policy projection, not a committee promise or probability"); otherwise `basis_mismatch:reference_end` (A19). |
| `par_vs_zero.v1` | par vs zero yield | `not_comparable`, `basis_mismatch:curve_convention` (A20). |
| `inflation_compensation.v1` | nominal par − real par, same tenor/date | `comparable_after_transformation`, transform `nominal_minus_real`, limitations: liquidity/indexation-lag/basis; output `inflation_compensation` (A23). |
| `term_premium_kw_vs_acm.v1` | KW vs ACM | `comparable_after_transformation` only at matched tenor+date; limitation "model disagreement, not a forecast or signal"; never renames one to the other (A22). |
| `cpi_vs_pce.v1` | CPI vs PCE | `not_comparable`, `basis_mismatch:basket_or_index` (A12/A13). |
| `cpi_month_vs_breakeven_10y.v1` | next-month CPI vs 10y breakeven | `not_comparable`, `basis_mismatch:reference_end` (A13). |
| `yield_move_attribution.v1` | attribute a nominal move to expected-short vs premium, or real vs compensation | `not_identified`, `underidentified:decomposition` with the alternatives (e.g. +10/+20 and −10/+40 for +30); never sums across the two accounting views (A23/A24). |

## 6. `PathAssumptions` / `solve_reference_average`

`PathAssumptions(month_start, month_end, effective_dates: tuple[str], realised_through: str |
None, realised_average: float | None, pre_change_rate: float | None, rate_step_bp: float | None,
effr_minus_midpoint_bp: float | None, tolerance_bp: float)` — effective dates are SUPPLIED by
the canonical calendar owner (a policy change takes effect on its supplied effective date); the
pure module never derives them.

`PathIdentification(status, identified: dict | None, alternatives: tuple[dict], end_rate_range:
tuple[float, float] | None, assumptions_used: tuple[str], missing: tuple[str], residual_bp:
float | None)`. Each path dict = `{"segments": [[start, end, rate], …], "end_rate": float}`.

`solve_reference_average(observations, assumptions)` — calendar-day arithmetic identity
`avg × N = Σ rate_i × days_i`:
- non-meeting month (no effective date inside) ⇒ `identified_conditional`, end rate = monthly
  level, assumption "no intra-month change".
- one effective date with known `pre_change_rate` (or realised average over elapsed days) ⇒
  `identified_conditional`: `r_post = (avg·N − r_pre·d_pre)/d_post`, plus `end_rate_range` from
  `tolerance_bp`. Missing pre-change rate ⇒ `missing_inputs`.
- ≥2 unknown segments, or a discrete grid admitting >1 path within tolerance ⇒
  `feasible_alternatives` (all grid paths listed, capped at 50 with a limitation if capped).
- no feasible path within tolerance ⇒ `inconsistent`.
- **F3, as merged in #9233.** No grid step is ever defaulted. `rate_step_bp` that is None, 0,
  negative, NaN, infinite, a bool or non-numeric counts as unsupplied. Without a supplied step:
  - one effective date and no usable pre-change rate ⇒ `missing_inputs`, `missing=("pre_change_rate",)`;
  - no effective date supplied at all ⇒ `missing_inputs`, `missing=("rate_step_bp",)`;
  - two or more inside dates ⇒ `missing_inputs`, `missing=("rate_step_bp",)`.

  A supplied step enumerates the grid at half the step, and its tags name the step
  (`rate_step_bp=<g>`). Witnesses: a single date with step 50 lists 37 alternatives; two
  dates with step 25 list 18; a single date with a known pre-rate is `identified_conditional`
  4.2. A realised average counts as a pre-rate only when its window is a strict prefix of the
  pre-change segment. Without a window it carries `realised_through_unknown`.
- Path rates are in the operand's own rate-index space (EFFR for ZQ). The solver does not
  apply `effr_minus_midpoint_bp`, which is carried for consumers. A midpoint-space reading
  goes through `zq_month_vs_policy_midpoint.v1`, never by relabelling a path rate.
- Canonical witness (A16/A17): 30-day month, 15 d @ 4.50 + 15 d @ 4.00 ⇒ average 4.25; the
  month-average change vs 4.50 is −25 bp while the second-half level change is −50 bp; with
  pre-rate unknown and 25 bp grid the same 4.25 average admits multiple paths ⇒ nonunique.
- Never outputs a probability, cut count or terminal rate without the supplied assumptions.

## 7. Board wire compatibility (T0/C0 apply it; B0 freezes it)

- `build_board(root=None, *, cutoff: str | None = None)` and
  `fed_path.compute(..., *, metadata: dict | None = None, cutoff: str | None = None)` — keyword
  additions only; existing positional/keyword callers unchanged.
- Board top level adds `basis_contract_version: "rates_command_basis.v1"` and
  `qualified_comparisons: [ComparisonResult.to_dict(), …]`. Existing rows keep every existing
  field; each row MAY add `basis: QualifiedObservation.to_dict()` (or a list for multi-operand
  rows). No existing key changes meaning; `regime_outlook` (GRI) is untouched byte-for-byte.
- A row whose source is unknown carries `source_en`/`source_zh` = None plus
  `basis.source == None` — never a named provider default (A03).
- Countdown: board carries `countdown.source_cutoff` (the evidence time the day count was
  computed at) and `countdown.display_cutoff` (explicit); a stale count is either recomputed
  through the canonical calendar at `display_cutoff` or rendered as historical — never as
  current (A05).

## 8. Minimum B0 tests (red first, then green)

`test_unknown_basis_refuses_numeric_comparison`, `test_missing_is_not_zero`,
`test_after_cutoff_value_never_leaks`, `test_sr3_vs_zq_refused_without_basis`,
`test_par_vs_zero_refused`, `test_cpi_vs_pce_not_comparable`,
`test_forecast_vs_revised_value_rejected_for_first_print_rule`,
`test_monthly_average_two_paths_same_average_nonunique` (the 4.50/4.00 witness),
`test_one_meeting_identified_conditional_with_pre_rate`,
`test_yield_move_attribution_not_identified_lists_alternatives`,
`test_obs_id_is_stable_content_hash`, `test_schema_round_trip_validates` (jsonschema against
the new contract), `test_module_is_pure` (no `requests`/`urllib`/`open(`/`datetime.now` in the
module source).
