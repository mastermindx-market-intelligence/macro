# robotics_non_regression

Test: `tests/test_robotics_theme_non_regression.py`.

The suite does not compare live `site/` or `data/` bytes to a frozen snapshot.
Prophet presence drifted after the freeze at `3c93f819` (`member_tickers_present`
was `[ISRG, NOVT]`; on the re-land head it is `[CGNX, ISRG, NOVT, ROK, TRMB]`,
and `site/prophet/index.json` gained `source_board_sha256`,
`source_board_snapshot_encoding`, and `source_board_snapshot_path`). That drift
is the daily prophet board. Re-blessing the snapshot would fail again the next
day. The `prophet_presence` block was removed from `robotics_baseline.json`
because no assertion reads it.

## What the suite holds

1. **Write-set disjointness.** `reland_write_set.json` is
   `git diff --name-only 2cd51ad3db37bc51383380a6fa3f29f397253060 efe72f1292d17f9defb38d0a452fbfaf918cacef`.
   None of those paths may sit under `site/`, `data/`, or `templates/`, and none
   may be a builder or publisher the prophet board, membership, or theme tracker
   read. Every `engine/**` module whose path contains `robotics` is AST-scanned
   for file writes (`open` with a write mode, `Path.write_*`, `json.dump` to a
   file, `shutil`, `os.replace`).
2. **Import isolation.** The AST import closure of those builders does not
   include a robotics engine module, so their outputs do not depend on the
   re-land.

Builders the check names:

| surface | module | why it is the builder |
|---|---|---|
| prophet board | `scripts/build_prophet.py` | publishes `site/prophet/index.json` |
| membership | `engine/baskets.py` | reads curated `data/baskets/membership.json` (`_membership`) and computes the basket payload |
| membership | `scripts/build_baskets.py` | publishes the baskets page from that payload |
| theme tracker | `scripts/build_state_of_themes.py` | `compose()` is the Theme Tracker read |
| theme tracker | `scripts/build_thematic_state.py` | publishes `theme_state.json`, which `compose()` reads |

US membership is human-curated. `scripts/reconcile_membership.py` does not
auto-mutate `data/baskets/membership.json`.

The builder paths are parse-only subjects of assertions 1 and 2. The suite
opens them and walks their AST; it does not import them. Both the path table
and the pin asserts carry `# ci-trigger-closure: data`, so the exclusive
`robotics-theme-research` job does not adopt the publishers' import closures.
Widening that job onto `collectors/` and the basket/prophet publishers would
select it for ordinary collector edits and push packing probes through their
ceilings.

## Structural pins that do not read live trees

`robotics_baseline.json` still records the pre-robotics freeze
(`frozen_at_main` `3c93f8194f6c2cb19dad21c1347d8b3b8474aa31`) for schema,
frozen-vs-shape field lists, the public-page canary vocabulary, the evidence
parquet rule, and the historical membership / theme_state / theme_tracker /
basket_confluence sections. Each remaining section's `section_sha256` must
match the section. Those sections are not compared to today's checkout.

Do not regenerate this baseline from `site/` or `data/`. A sparse checkout
runs the whole module; it does not skip for missing `data/` or `site/`.

## Live comparisons this replaced

| removed assertion | intent now covered by |
|---|---|
| membership vs the frozen basket | (1) the artifact is under `data/` and the membership builder/publisher is not in the write set; (2) those modules do not import robotics |
| theme_state vs the freeze | (1) the artifact is under `data/` and `site/`, and `scripts/build_thematic_state.py` is not in the write set; (2) that publisher does not import robotics |
| theme tracker `compose()` vs the freeze | (1) `scripts/build_state_of_themes.py` is not in the write set and the artifacts it reads are under `site/` and `data/`; (2) its closure does not import robotics |
| basket confluence vs the freeze | (1) the artifact is under `site/` and robotics modules perform no writes, so they cannot rewrite it |
| prophet presence vs the freeze | (1) `site/prophet/index.json` is under `site/` and `scripts/build_prophet.py` is not in the write set; (2) that publisher's closure does not import robotics |
| live public-page / public-JSON canary scan | (1) the write set has no `site/` path and robotics modules perform no writes. The canary vocabulary stays pinned and does not open `site/` |
| live evidence-parquet cell scan | (1) the parquet is under `data/` and robotics modules perform no writes. The column rule stays pinned and does not open the parquet |
