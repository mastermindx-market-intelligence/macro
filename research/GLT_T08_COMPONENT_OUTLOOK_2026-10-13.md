# GLT T08 Component Outlook — Measurement-Only Accounting Extension

**Date:** 2026-10-13

**Programme:** WS:GLOBAL-LIQUIDITY-TRANSMISSION, task T08 (macro)

**Module:** `engine/global_liquidity_outlook.py`

**Schema:** `glt_component_outlook_v1`

**Tier:** display-tier accounting, not promoted to any rank/size/gate authority

This note documents the T08 component-outlook accounting extension: the H.4.1
identity it reconciles (C16), its horizons, its estimate-type vocabulary, the
knowledge-time admissibility law it reuses from T05 (C15), the synthetic
fixture receipt, the live-snapshot status, and the test and refusal map. Line
names, constants, numbers and reason strings are quoted exactly from the
binding specification; nothing here is re-derived.

## Scope and authority

The module is measurement-only display-tier accounting. Its authority
constants are:

- `AUTHORITY = "measurement_only"`
- `CLAIM_LEVEL = "conditional_accounting_display_tier"`
- `SCHEMA = "glt_component_outlook_v1"`

- The module is not promoted to any rank/size/gate authority.
- It adds no collector, no calendar, no parquet, and no builder/render/nightly wiring.
- `engine/canon.py` remains the only owner of the net-liquidity series.
- `liquidity_plumbing.compute` and `treasury_supply.compute` are untouched.

these are conditional accounting paths and announced scenarios; no probability forecast exists until T09/T14

## Identity (C16)

The module reconciles the reserve identity R = A − N on the H.4.1 basis
below. The reserve line is printed and never absorbed:

- `reserves_implied = Total assets − (sum of the eleven non-reserve liability lines + Total capital)`
- `residual = reserves_reported − reserves_implied`
- A residual is always printed, never folded into any component.

| Role | Exact line name |
|---|---|
| Basis | H.4.1 Table 5 Consolidated Statement of Condition of All Federal Reserve Banks |
| Assets line | Total assets |
| Reserves line (the target; in no component) | Reserve balances with Federal Reserve Banks |
| Non-reserve liability 1 | Federal Reserve notes, net of F.R. Bank holdings |
| Non-reserve liability 2 | Reverse repurchase agreements: Foreign official and international accounts |
| Non-reserve liability 3 | Reverse repurchase agreements: Others |
| Non-reserve liability 4 | Deposits: Term deposits held by depository institutions |
| Non-reserve liability 5 | Deposits: U.S. Treasury, General Account |
| Non-reserve liability 6 | Deposits: Foreign official |
| Non-reserve liability 7 | Deposits: Other |
| Non-reserve liability 8 | Deferred availability cash items |
| Non-reserve liability 9 | Treasury contributions to credit facilities |
| Non-reserve liability 10 | Earnings remittances due to the U.S. Treasury |
| Non-reserve liability 11 | Other liabilities and accrued dividends |
| Capital line | Total capital |

The eleven non-reserve liability lines are `H41_NONRESERVE_LIABILITY_LINES`,
in the order printed above. The reconciliation is passed to the T04 identity
(`reserves_from_balance_sheet` / `assert_reserve_identity` in
`engine/global_liquidity_accounting.py`) in three buckets:

- `treasury_cash` = the TGA line ("Deposits: U.S. Treasury, General Account");
- `reverse_repo` = the two reverse-repo lines;
- `other` = every remaining non-reserve liability line plus Total capital.

Tolerances are T04's `DEFAULT_ABS_TOL` (1e-9) / `DEFAULT_REL_TOL` (1e-12) as
defined in `engine/global_liquidity_accounting.py`.

Component partition (`COMPONENT_LINES`, in order; sign = contribution to
reserves):

| Component | Line(s) | Sign |
|---|---|---:|
| `total_assets` | Total assets | +1 |
| `treasury_general_account` | Deposits: U.S. Treasury, General Account | -1 |
| `reverse_repo_others` | Reverse repurchase agreements: Others | -1 |
| `reverse_repo_foreign_official` | Reverse repurchase agreements: Foreign official and international accounts | -1 |
| `federal_reserve_notes` | Federal Reserve notes, net of F.R. Bank holdings | -1 |
| `other_nonreserve_and_capital` | Deposits: Term deposits held by depository institutions; Deposits: Foreign official; Deposits: Other; Deferred availability cash items; Treasury contributions to credit facilities; Earnings remittances due to the U.S. Treasury; Other liabilities and accrued dividends; Total capital | -1 |

Partition law:

- Every line is named exactly once across the partition.
- The reserves line belongs to no component.
- A null line is unavailable, never zero.
- A duplicated or undeclared line is listed, never silently merged.

## Horizons

- `DEFAULT_HORIZONS_WEEKS = (4, 8, 13)`.
- Target date = anchor observed_on + 7*h days.
- Decision and publication time zone default America/New_York.

## Estimate-type vocabulary

Exactly three values (`ESTIMATE_TYPES`). There is no fourth type.

| Estimate type | Meaning |
|---|---|
| `announced_scenario` | The component has at least one admissible announcement; its level follows the announced schedule (a "level" change sets the level, a "delta" change adds; after the last change the level holds). Any assumption for that component is ignored and listed. |
| `conditional_accounting` | No admissible announcement; the level follows a stated assumption: `hold_level` (level = anchor) or `weekly_delta` (anchor + value * horizon_weeks). |
| `unavailable` | No number is produced; an `unavailable_reason` is printed. |

`unavailable_reason` strings on component paths:

- `anchor_published_after_as_of`
- `anchor_incomplete`
- `unsupported_assumption_kind:<kind>`
- `no_admissible_announcement_or_assumption`

`unavailable_reason` strings on the reserves block, in precedence order:

- `anchor_published_after_as_of`
- `anchor_incomplete`
- `anchor_identity_does_not_reconcile`
- `component_unavailable:<first unavailable component>`

Reserves block, when available, per horizon:

- `observed_anchor` = reported reserves at the anchor;
- `announced_change` = sum of sign * change_from_anchor over `announced_scenario` components;
- `assumed_change` = the same over `conditional_accounting` components;
- `level` = observed_anchor + announced_change + assumed_change;
- `statistical_residual` = None.

The reserves block's estimate type is `announced_scenario` only if every
component is `announced_scenario`, else `conditional_accounting`.

The top-level `statistical_residual` is always:

```json
{"estimate_type": "unavailable", "unavailable_reason": "no_statistical_model_until_T09"}
```

## Knowledge-time admissibility (C15)

An announcement or anchor is admissible iff

```
availability_start_utc(published_at, publication_tz) <= cutoff_utc(as_of, decision_tz)
```

using the T05 helpers in `engine/global_liquidity_knowledge_time.py`. A date
`as_of` means the START of that local day (`cutoff_utc` maps a plain date to
local midnight of that day in `decision_tz`).

Exclusion reasons, checked in this fixed order:

1. `missing_published_at`
2. `invalid_published_at`
3. `unknown_component`
4. `invalid_change`
5. `published_after_as_of`
6. `superseded_by:<id>` — applied only when the superseding announcement is itself admitted.

- A duplicate announcement id is an error.
- A post-as-of revision or financing-source change cannot alter any path.
- If the anchor itself is not admissible, every path and the reserves block
  are unavailable (`anchor_published_after_as_of`) and no anchor number
  appears anywhere in the output.

## Fixture: persistence vs announced-only

The fixture is synthetic, in $ millions. Anchor: observed_on 2026-09-02,
published 2026-09-03 16:30 America/New_York. as_of = 2026-09-04 with
decision_tz America/New_York, so the cutoff is 2026-09-04T04:00Z. Targets:
4w 2026-09-30, 8w 2026-10-28, 13w 2026-12-02.

Fixture row:

| H.4.1 line | Value ($ millions) |
|---|---:|
| Federal Reserve notes, net of F.R. Bank holdings | 2,300,000 |
| Reverse repurchase agreements: Foreign official and international accounts | 380,000 |
| Reverse repurchase agreements: Others | 150,000 |
| Deposits: Term deposits held by depository institutions | 0 |
| Deposits: U.S. Treasury, General Account | 800,000 |
| Deposits: Foreign official | 10,000 |
| Deposits: Other | 120,000 |
| Deferred availability cash items | 1,000 |
| Treasury contributions to credit facilities | 5,000 |
| Earnings remittances due to the U.S. Treasury | -230,000 |
| Other liabilities and accrued dividends | 40,000 |
| Total capital | 50,000 |
| Reserve balances with Federal Reserve Banks | 3,000,000 |
| Total assets | 6,626,000 |

Identity receipt on this row: N (non-reserve liabilities + capital) =
3,626,000; reserves_implied = 3,000,000; residual = 0; the row reconciles.
The `other_nonreserve_and_capital` anchor level = -4,000.

Announcements at as_of 2026-09-04:

| # | id | Kind | Component | Published | Change | Effective | Outcome | Reason |
|---|---|---|---|---|---|---|---|---|
| A1 | `tga-qra-2026q3` | schedule | TGA | 2026-08-04 08:30 America/New_York | level 850,000 | 2026-09-30 | ADMITTED | — |
| A2 | `tga-qra-2026q3-rev` | schedule | TGA (supersedes A1) | 2026-09-10 | level 900,000 | 2026-09-30 | EXCLUDED | published_after_as_of; A1 stays in force |
| A3 | `financing-shift-2026-09-15` | financing_source | TGA | 2026-09-15 | delta -200,000 | 2026-09-16 | EXCLUDED | published_after_as_of |
| A4 | `same-day-after-cutoff` | schedule | TGA | 2026-09-04 08:30 America/New_York | level 700,000 | 2026-09-30 | EXCLUDED | published_after_as_of (a date as_of means the start of that local day) |

Assumptions:

| Assumption | Component | Kind | Value | Disposition |
|---|---|---|---|---|
| `qt-runoff-assumption` | `total_assets` | `weekly_delta` | -5,000 | applied (`conditional_accounting`) |
| `hold-tga` | `treasury_general_account` | `hold_level` | — | ignored because A1 is admitted; listed, not used |
| (hold_level) | `reverse_repo_others`, `reverse_repo_foreign_official`, `federal_reserve_notes`, `other_nonreserve_and_capital` | `hold_level` | — | applied (`conditional_accounting`) |

Comparison:

| horizon_weeks | target_date | persistence_level | announced_only_level | difference | reserves level (conditional) | announced_change | assumed_change | TGA path level |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 4 | 2026-09-30 | 3,000,000 | 2,950,000 | -50,000 | 2,930,000 | -50,000 | -20,000 | 850,000 |
| 8 | 2026-10-28 | 3,000,000 | 2,950,000 | -50,000 | 2,910,000 | -50,000 | -40,000 | 850,000 |
| 13 | 2026-12-02 | 3,000,000 | 2,950,000 | -50,000 | 2,885,000 | -50,000 | -65,000 | 850,000 |

Plain-digit forms of the same five levels (no thousands separators):
persistence_level 3000000; announced_only_level 2950000; reserves level
2930000 (4w), 2910000 (8w), 2885000 (13w).

Realized mapping {2026-09-30: 2,960,000} and the realized-miss row:

| horizon_weeks | target_date | realized_level | persistence_miss | announced_only_miss |
|---:|---|---:|---:|---:|
| 4 | 2026-09-30 | 2,960,000 | -40,000 | +10,000 |
| 8 | 2026-10-28 | None | None | None |
| 13 | 2026-12-02 | None | None | None |

In plain words: the announced-only path differs from persistence at every
horizon ONLY because exactly one admissible announcement exists — A1, the TGA
schedule — which raises the TGA path from its anchor 800,000 to 850,000; on a
sign -1 component that is the -50,000 `announced_change`, so
announced_only_level = reported reserves 3,000,000 − 50,000 = 2,950,000 while
persistence_level stays 3,000,000. The conditional reserves level additionally
carries the stated assumptions: `total_assets` at `weekly_delta` -5,000 gives
assumed_change -20,000 / -40,000 / -65,000, and the other four components are
held at their anchor levels, so level = observed_anchor 3,000,000 +
announced_change + assumed_change = 2,930,000 / 2,910,000 / 2,885,000. Because
`total_assets` is `conditional_accounting`, the reserves block's estimate type
is `conditional_accounting`. `baseline_comparison` is pure and never changes
any path; `announced_only_miss` is None when realized is absent.

Positive control: at as_of 2026-09-11, A2 (published 2026-09-10) is admitted
and A1 is excluded with reason `superseded_by:tga-qra-2026q3-rev` —
supersession applies only because the superseder is itself admitted — and the
TGA 4w level is 900,000.

C16 refusal cases on the fixture:

- Dropping "Deposits: Other" from the non-reserve lines → residual -120,000;
  does not reconcile.
- Listing the TGA line twice → residual +800,000; duplicate_lines =
  ["Deposits: U.S. Treasury, General Account"]; does not reconcile.
- "Deferred availability cash items" = None → missing = ["Deferred
  availability cash items"]; reserves_implied None; residual None; does not
  reconcile; and the reserves block and `other_nonreserve_and_capital` are
  unavailable (`anchor_incomplete`).

## Live snapshot status

`snapshot()` is a fail-open availability probe; it never reads file contents
and never computes paths. It probes four owner inputs:

- `data/fred/WALCL.parquet`
- `data/fred/RRPONTSYD.parquet`
- `data/treasury/tga.parquet`
- `data/fred/WRESBAL.parquet`

Today it reports state `data_degraded` with the summary "component outlook
needs a full H.4.1 Table 5 owner loader (routed to T22); no paths computed",
because no full H.4.1 Table 5 owner loader exists — that loader is routed to
T22. Its gaps also list "no owner loader for H.4.1 line: <name>" for every
non-reserve liability line except the TGA line, and for Total capital.

## Tests and refusal map

18 tests, grouped:

C16:

- `test_c16_identity_reconciles_on_fixture_row`
- `test_c16_dropped_liability_prints_nonzero_residual`
- `test_c16_double_counted_liability_prints_nonzero_residual`
- `test_c16_component_partition_names_each_line_once`
- `test_c16_missing_line_is_unavailable_never_zero`

C15:

- `test_c15_future_published_announcement_excluded_and_recorded`
- `test_c15_announcement_published_on_as_of_date_after_cutoff_excluded`
- `test_c15_future_revision_cannot_replace_admitted_schedule`
- `test_c15_post_as_of_financing_source_change_cannot_alter_any_path`
- `test_c15_anchor_published_after_as_of_makes_paths_unavailable`

Text and shape law:

- `test_estimate_types_are_three_allowed_values_never_statistical_forecast`
- `test_no_forbidden_output_keys`
- `test_module_text_has_no_forbidden_fragments`
- `test_persistence_and_announced_only_differ_only_where_admissible_announcement_exists`
- `test_baseline_comparison_plain_numbers_on_fixture`
- `test_snapshot_empty_root_names_missing_inputs`
- `test_module_constants_measurement_only`
- `test_bool_rejected`

Mutants — each turns at least one named test red:

- M1 — admit every announcement regardless of published_at: the C15 exclusion
  law collapses; `test_c15_future_published_announcement_excluded_and_recorded`,
  `test_c15_announcement_published_on_as_of_date_after_cutoff_excluded`,
  `test_c15_future_revision_cannot_replace_admitted_schedule`, and
  `test_c15_post_as_of_financing_source_change_cannot_alter_any_path` go red.
- M2 — omit Total capital from the reconciled lines: the fixture row no longer
  reconciles and a nonzero residual appears, turning
  `test_c16_identity_reconciles_on_fixture_row` red.
- M3 — treat a null line as 0: a missing line would print a number instead of
  unavailable, turning `test_c16_missing_line_is_unavailable_never_zero` red.
- M4 — apply supersession even when the superseder is excluded: the excluded
  A2 would wrongly displace the admitted A1, turning
  `test_c15_future_revision_cannot_replace_admitted_schedule` red.

## What this is not

- No probability, no confidence, no ranking, no sizing, no score.
- It owns no statistical content: the `statistical_residual` is always
  `{"estimate_type": "unavailable", "unavailable_reason":
  "no_statistical_model_until_T09"}`.
- Downstream T09 (statistical residual model), T10 and T14 own anything
  probabilistic; T22 owns the full H.4.1 Table 5 owner loader.
- `baseline_comparison` is a pure display and never changes any path;
  `snapshot()` never computes paths.
- The module is not promoted to any rank/size/gate authority; it is
  display-tier accounting only.
