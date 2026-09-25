# robotics_non_regression — frozen legacy decision outputs for `robotics_automation`

Operation `gmi-robotics-fable-ceo-e2e-20260923-chairman-001` (carrier Macro #7908), lane R3.
Test: `tests/test_robotics_theme_non_regression.py`. Baseline: `robotics_baseline.json`
(schema `robotics.theme_non_regression.v1`, `frozen_at_main` =
`3c93f8194f6c2cb19dad21c1347d8b3b8474aa31`, the carrier base, taken BEFORE any Robotics
research product code existed). Mirrors the accepted Energy pattern
(`tests/test_energy_economic_change_non_regression.py`, #7895).

## Why

The Robotics research vertical carries zero automatic decision authority. It must never change
the incumbent decision outputs — basket membership/weights, ThemeState, Theme Tracker
lane/stage/recommendation, entry fields, member ordering, Prophet presence — and must never leak
a full-fidelity research payload through public pages, public JSON or the tracked evidence
parquet (master packet §3 items 4-5; RBV-28, RBV-31). This freeze is the comparison set every
later Robotics lane is measured against.

## What is frozen vs shape

| section | frozen (exact value) | shape (type name only) |
|---|---|---|
| `basket_membership` | `robotics_automation` only: `weighting`, `weights`, members sorted by ticker projected to (ticker, added, removed, curated_added) | — |
| `theme_state` | `theme_id`, `name_en`, `name_zh`, `basket_ids`, `foresight_decision` (= foresight projected to stage, entry_ready, tier, bottleneck_band, source), `foresight_keys` (the sorted key set of the foresight object), `narrative` | `radar`, `basket_intel`, `subsector_rotation`, `divergence_board`, `subsector_keys`, `foresight_score` |
| `theme_tracker` (`scripts/build_state_of_themes.py::compose(REPO_ROOT)`) | `theme_id`, `name_en`, `name_zh` | the 19 tracker fields: lane, lane_rank, stance_en/zh, story_en/zh, fav_count, caut_count, present_count, stage_raw, stage_key, stage_label_en/zh, stage_sort, falsifier_any_fired, falsifier_label, filter_flags, leadership_context, entry_context |
| `basket_confluence` (`site/marketdata/basket_confluence.json` → `baskets[]` row with `basket_id == robotics_automation`) | `key`, `kind`, `label`, `label_zh`, `sector`, `sector_zh`, `basket_id`, `chart_key`, `member_tickers_sorted` | `entry`, `regime`, `class`, `price_level`, `n_members`, `n_priced`, `n_live`, `reliability`, `coverage_pct`, `has_signals`, `start`, `as_of`, `member_order` |
| `prophet_presence` (`site/prophet/index.json` → `plans[]` rows whose `asset` is a robotics member) | `member_tickers_present` (sorted set; name-pinned as `PROPHET_FROZEN`) | every row field of the matched rows as a type name (`row_fields`), plus `structure_checked` (the full sorted top-level key list, rows container, ticker field) |
| `public_pages` | the canary list itself and the scan roots | — (the test asserts no canary appears in `site/state_of_themes.html`, `site/basket/robotics_automation.html`, and no `gmirca_` / `curation_assertion` byte-string in any `*.json` under `site/marketdata`, `site/prophet`, top-level `site/*.json`, plus `site/basketdata/foresight_cascade.json`, the artifact `foresight.source` names) |
| `evidence_parquet` | the rule (`curation_assertion` column absent, or every cell null) | — |

Every section also carries a canonical sha256 (`section_sha256`) computed over
`json.dumps(section, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.

### Decisions recorded at the freeze

1. **`member_order` is shape, not frozen.** The confluence row emits members sorted by a nightly
   return column (`ret_20d` at the freeze: SYM, ISRG, TER, NOVT, … vs membership order ROK, ISRG,
   TER, CGNX, …), so the permutation changes every build. The member SET is the decision output
   and is frozen as `member_tickers_sorted`; the order's type is pinned.
2. **Prophet rows live under `plans[]`, keyed by `asset`.** At the freeze two robotics members had
   open plans (ISRG, NOVT). Numeric fields are shape only. This section is nightly-volatile by
   nature (plans open and close); a change here after a render-lane commit is expected and must be
   re-frozen with the recipe below, NOT silenced.
3. **Canaries are payload markers only.** A hidden mount element or an
   `/api/themes/v1/research` URL in the page shell is allowed and is not a canary.
4. **Theme Tracker context is deterministic** across two consecutive `compose()` runs at the
   freeze (byte-identical projection); no field had to be moved to shape for that reason.
5. **`foresight.score` is shape, not frozen** (independent review of R3, blocker 1). Over the
   month before the freeze the robotics `foresight` object changed 8 times across the 28 commits
   that rewrote `theme_state.json` (27 nightly `regime update` commits plus one `chore(immune)`,
   `69268b0650`), every time `score` only (45.0→38.8→37.1→38.8→39.4→45.0→40.0→45.0→39.4)
   while `(stage, tier, bottleneck_band, entry_ready)` never moved. The decision sub-fields are
   frozen as `foresight_decision`; the score's type is pinned as `foresight_score`. The foresight
   KEY SET is frozen as `foresight_keys` (re-review nit 1): it had zero transitions over the same
   28 checkpoints, and a new key written into the incumbent object is the leak this freeze exists
   to catch.
6. **Null counts as a type.** A shape field that is `null` at the freeze (`entry_context`,
   `leadership_context`, and five prophet row fields) reddens the shape assertion the first time
   the incumbent populates it. That is a real structural event; re-freeze with the recipe below
   and say why.
7. **The prophet section moves on presence events and on incumbent schema additions.** Across
   the prophet checkpoints before the freeze the member set changed once (NOVT's plan opened,
   2026-09-04) and the board's top-level key set changed once (`leader_observation_summary`,
   31→32 keys, `8b533225517d`, 2026-09-22). Both are legitimate causes of a red here: closed plans
   persist on the board, so the set is append-mostly, and `structure_checked.top_level_keys` is
   the full sorted key list on purpose (re-review nit 4). `row_fields` co-moves with the set (a new
   member adds its row's field types); all of it is one section sha on purpose.
8. **The membership section skips on a sparse checkout** (it reads `data/`), unlike the Energy
   pattern it mirrors, so the packet's "skips rather than fails" holds for every section.

## Regeneration recipe

Only regenerate when an incumbent owner changed the underlying artifact on `main` (never to make
a Robotics change pass). Run from a full checkout (`data/`, `site/` present):

```bash
TZ=UTC python3 tests/test_robotics_theme_non_regression.py --regenerate-baseline <main-sha>
```

Then run the test twice and confirm the baseline is byte-identical between two regenerations
(`shasum -a 256 tests/fixtures/robotics_non_regression/robotics_baseline.json`). Record the new
`frozen_at_main` sha and the reason in the PR body. Sparse checkouts skip the sections that need
`data/` or `site/` via the `needs_full_checkout` marker; they never fail.
