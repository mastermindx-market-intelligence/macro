# Theme Price-Basis Integrity W0 — Exact-Head Proof

**Operation:** `theme-price-basis-integrity-w0-20260912-sol-001`  
**Semantic source head:** `46ce0969c298facebad66ac92bfd33e0be3b7995`  
**Pickup/data epoch:** `acb0d75e49596a62230542cf297a84391694f765`  
**Procedure:** Mastermind `57a2672af5b9dcea282e4bae01d1a0b9d10bb1cd`, Skillpack 1.0.1 / bootstrap 1  
**Authority:** measurement integrity only; no rank, size, entry, Prophet, portfolio, or trade authority.

## Capability proved

Baskets, Group Flow thematic baskets, and Theme Scoring now use one shared whole-column primary-vs-supplemental close resolver on the already-frozen US market calendar. The existing Group Flow/PIT-sector price plane remains byte-equivalent to its prior add-only construction.

The resolver never advances the desk calendar from supplemental tape and never row-splices divergent adjustment vintages. A losing source can donate older history only through the incumbent `_stitch_ok` identity gate. Price adjustment vintage remains explicitly `unrecorded`.

## TDD and focused verification

The resolver was first observed RED in six cases because the capability did not exist. Consumer routing was then observed RED across Group Flow, Baskets, and Theme Scoring. A later real-input replay exposed an additional false-green: Group Flow did not itself apply the W0 60% population floor. A dedicated test reproduced that defect before the repair and then passed after it.
Focused verification on the final source:

```text
204 passed, 11 skipped
```

The set covers close-panel freshness/basis guards, Group Flow US/regional behavior, Theme Scoring including conflict/leadership rules, Baskets/calibration/member context, price-basis grader guards, and GitHub annotation law. `git diff --check` and Python compilation of all four production modules passed.

## Real committed-input replay

Required tracked input blobs were extracted from the pinned data epoch into a separate read-only receipt root. No omitted sparse-worktree `data/` or `site/` path was materialized or written. The proof ran the real `group_flow._setup('us')`, `baskets.compute_baskets()`, `group_flow.compute_group_flows()`, and `theme_scoring.compute_theme_intel('us')` code paths.

```json
{
  "effective_as_of": "2026-09-11",
  "configured_baskets": 49,
  "population_admitted": 45,
  "population_refused": 4,
  "baskets_admitted": 45,
  "baskets_refused": 4,
  "group_flow_basket_rows": 45,
  "theme_scoring_admitted": 45,
  "theme_scoring_refused": 4
}
```
The exact refused set is `regional_banks`, `semicap_equipment`, `data_center_power`, and `industrial_distribution`; each remains below the established three-member / 60% configured-live observation floor.

Resolution receipt:

```json
{
  "chosen_counts": {"baskets_extras": 620, "primary_breadth": 86},
  "unresolved_n": 2,
  "unresolved_tickers": ["MAG", "GATO"],
  "stitch_count": 4,
  "adjustment_vintage": "unrecorded",
  "authority": "measurement_only"
}
```

The external proof-root hash was identical before and after execution: `c14a14b46a92660fe4a5833f5bfbeb3a6296ef66a9299017380e4e7861383351`. The proof also reconstructed the incumbent Group Flow add-only primary plane and asserted byte-equivalence against the new `setup["closes"]` output.

## Current-main compatibility

Before delivery, `origin/main` advanced to `c518b8787a72f62e8ee18f172ec5e96136890748`. The six intervening commits did not touch `lib/closes_panel.py`, `engine/group_flow.py`, `engine/baskets.py`, `engine/theme_scoring.py`, either modified test file, or the new W0 spec/plan paths. No ancestry-only merge or rebase was introduced merely to make the branch appear current.

## Next dependency

After merge and merged-byte proof, resume the original Theme Strength Buying program with the separately preregistered research-only temporal-grain/MACD wave. Reuse the existing 4H/session-anchor infrastructure; do not create entry, rank, sizing, Prophet, Action Board, or trade authority from W0.
