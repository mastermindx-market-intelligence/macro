# SI Rotation Read

**Description only; not a forecast.**

The rotation read is one descriptive weekly panel for the Sector Intelligence
page: which house baskets are seeing their breadth improve or deteriorate, and
for how long, on **today's roster**. It is a pure projection of the committed
weekly fixed-set breadth history — it computes no new measure and tunes nothing.

- Builder: `scripts/build_rotation_read.py` (step in `build_sector_intelligence.default_steps()`, immediately before the freshness gate).
- Output: `site/sectordata/rotation_read.json`, schema `si.rotation_read/v1`.
- Inputs (read-only): `data/breadth/history/basket_breadth_weekly_current.parquet` and `data/baskets/membership.json`.
- Freshness: `check_sector_intelligence_freshness.check_rotation_read(root)` binds the written `as_of` to the history's last completed weekly close.

## Fields

Top level, in order: `schema`, `as_of`, `built_at`, `status`, `basis`, `copy`, `groups`, `companies`.

- `as_of` — the last completed weekly close in the input history (strict `YYYY-MM-DD`).
- `built_at` — UTC ISO timestamp with `Z`.
- `status` — `ok`, `stale` (two or more completed weekly closes behind the latest session), or `unavailable` (every row unavailable for a reason other than stale).
- `basis` — always `current_roster`.
- `copy` — the fixed consumer line: "Breadth change inside the group on today's roster. Description only; not a forecast."

Each `groups[]` row, in order: `group_id`, `family`, `name`, `parent`, `as_of`,
`status`, `unavailable_reason`, `n_members`, `n_counted`, `pct_above_200`,
`chg_13w`, `chg_26w`, `direction`, `run_weeks`, `rank_13w`, `n_ranked`.

- `family` — `sector` for `us_sector_*` ids (listed first), else `theme`; within a family rows sort by `group_id`.
- `n_members` — today's active roster size (`engine.us_basket_turn.active_members`), always an int.
- `n_counted` — members with a defined 200-session average (`n_has_200`).
- `pct_above_200` — share above the 200-session average, percent, rounded to 4 decimals.
- `chg_13w` / `chg_26w` — fixed-set (like-for-like) change of that share over 13 / 26 weeks, rounded to 4 decimals; `chg_26w` may be null.
- `direction` — `improving` / `flat` / `deteriorating` from the sign of `chg_13w`.
- `run_weeks` — consecutive weekly closes holding that direction.
- `rank_13w` / `n_ranked` — rank of `chg_13w` **inside the family only** (1 = largest increase, ties share the lower rank), over the family's OK rows.

`companies` maps every active ticker to `{"sector": <us_sector_* id or null>, "themes": [sorted non-sector basket ids]}`, keys sorted.

## Rules

1. **Completed weekly close (calendar only).** A date is a completed weekly close iff no NYSE session exists on any day after it through the Sunday of its Mon–Sun week. The panel pins to the latest such date in the history; a trailing partial week never becomes `as_of`. No wall clock is consulted for the vintage.
2. **Stale.** "label stale at two or more completed weekly closes behind the latest session" (the `stale_rule` recorded in `data/breadth/history/group_breadth_weekly_current_live.meta.json`). Weeks are counted by each week's last NYSE session; a week whose last session is after the latest expected session does not count. A stale panel keeps top `status="stale"` and every row is unavailable with reason `stale` and null measures.
3. **Unavailable ladder (first match wins).** No history row for the basket → `no_history`; top stale → `stale`; `pct_above_200` or the 13-week change missing → `too_few_members`. The missing-measure case encodes the upstream `engine.group_breadth_history.MIN_MEMBERS = 10` rule: a share or change built on fewer than 10 qualifying members is missing, never zero. Unavailable rows carry null measures; `n_counted` survives only for `too_few_members`.
4. **No history, no file.** Missing/unreadable inputs or no completed weekly close → the builder logs and writes nothing (rc 0). The freshness gate errors if the JSON exists without a completed close, is missing although its history exists, carries the wrong schema, or its `as_of` differs from the history's last completed weekly close (`ROTATION READ VINTAGE SPLIT`).
5. **Roster honesty.** Measures describe the historical fixed set; the roster fields (`n_members`, `companies`) describe today's active membership. Removed members never appear.

Description only; not a forecast.