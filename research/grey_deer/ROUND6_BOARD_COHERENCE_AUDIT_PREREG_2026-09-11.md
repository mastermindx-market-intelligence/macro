# Prophet board coherence audit — preregistration R6

**Frozen before outcome-column access:** 2026-09-11 UTC  
**Parent operation:** `prophet-absolute-downside-research-20260910-sol-001`  
**Carrier:** existing Draft/HOLD Macro PR #7043  
**Authority:** research-only; no rank, entry, sizing, portfolio, model-promotion, source, UI, deployment, or production authority

## 1. Question and user job

The Chairman observed a visible Prophet board on which nearly every displayed name was down together. This audit asks a narrower, falsifiable historical question:

> When the existing US buy board loses, does it lose as a shared board; how often is that shared loss aligned with the market; and does the displayed top of the existing ordering separate better outcomes from the rest?

This is not a reconstruction of the motivating screenshot, a same-day intraday trade audit, a customer P&L statement, or a test of a new risk model. It uses the existing board grader and its declared conventions rather than creating another grader.

## 2. Frozen source identity and pre-read boundary

One committed artifact only:

- repository commit: `mastermindx-market-intelligence/macro@bbf6c1e65fc9cad1ba40efa26126cc60036713d0`
- path: `data/us_board_ledger/retro_grades.parquet`
- Git blob: `af8bdb5a0cedfcfe3c3ea0de37c86e79f7736462`
- bytes: `750653`
- SHA256: `fecaf0aa3e454ad93bd04cebd28b916f6bc71f50d71946ce5f03c5c50aa43399`
- Parquet metadata: 9,192 rows, 87 columns, one row group

Before this file was committed, Sol inspected only file existence, byte/hash identity, Parquet row/column counts, field names, and schema metadata. No numeric outcome column, date range, category frequency, board result, or fitted statistic from this artifact was read.

Abort rather than substitute a newer artifact if the bytes differ. The source is a retrospective committed ledger, not proof of the exact bytes served to the screenshot or of an as-known production decision.

## 3. Existing grader convention retained

The audit accepts the artifact's own declared measurement semantics as data, without silently upgrading them:

- board signal is published after its `as_of` session;
- entry is the next observed session's close;
- horizons are the ledger's existing 5, 10, 21, and 63 trading-session rows;
- `ret` is the name's fixed-horizon return under that convention;
- `spy_ret` and `excess_spy` are the existing benchmark legs;
- `mae_close_excess_spy` is a close-path excess excursion, not absolute intraday low or an executable stop fill;
- price-source and price-basis fields are reported as stamped.

A result about this ledger must not be restated as what a morning buyer, an intraday stop, or a live alert would have experienced.

## 4. Frozen population

1. Use `lane == "buy"` only.
2. Use product-era rows with `as_of >= 2026-06-25`, the existing grader's declared narrow-board era boundary.
3. Report every horizon present among `{5, 10, 21, 63}` separately. No horizon is primary and none may rescue another.
4. Grain is one `(as_of, horizon, ticker)` row. Exact duplicates abort the analysis and are reported; they are not averaged or keep-firsted after outcome access.
5. `issued_n` is the number of distinct ticker rows present at the grain. `resolved_n` is the number with finite `ret`.
6. A board date is eligible for headline board-distribution summaries only when `issued_n >= 5` and `resolved_n / issued_n >= 0.80`. Ineligible dates remain in a coverage table and denominator; they are not silently dropped from data-quality reporting.
7. Preserve every price-basis category found. Report the full eligible population and a separately labelled post-2026-08-06/adjusted-basis sensitivity only if that category is actually present; do not redefine an unfamiliar stamp after seeing results.
8. Missing outcomes remain missing. They are never coded as winners, losses, zero return, or removed from the issued denominator.

## 5. Frozen board-level measurements

For each eligible `(as_of, horizon)` board, compute on finite resolved rows:

- `loss_fraction = mean(ret < 0)`;
- `severe_loss_fraction = mean(ret <= -0.03)`;
- mean and median `ret`;
- mean and median `excess_spy`;
- minimum and 10th-percentile `ret`;
- sector Herfindahl concentration from the issued rows;
- the single `spy_ret`, after first requiring all finite values within the board to agree to 1e-12; disagreement aborts that board and is reported.

Predeclared co-loss events:

- `broad_loss_80`: at least 80% of resolved names lose;
- `near_total_loss_90`: at least 90% lose;
- `total_loss_100`: every resolved name loses;
- `severe_breadth_50`: at least half lose 3% or more.

Classify an 80% co-loss board as:

- `market_aligned` when `spy_ret < 0`;
- `selection_specific` when `spy_ret >= 0`;
- `market_unknown` when the benchmark is unavailable.

These names are descriptive categories, not causal proof.

## 6. Visible-top and ordering measurements

Define the visible top set as the twelve lowest numeric `position` values per eligible board, ties resolved only by `(position, ticker)` for reproducibility. If fewer than twelve resolved rows exist, use all and label the board `top12_is_all`.

For boards with at least 13 resolved rows, compute paired date-level differences:

- top-12 loss fraction minus remainder loss fraction;
- top-12 mean `ret` minus remainder mean `ret`;
- top-12 mean `excess_spy` minus remainder mean `excess_spy`.

For boards with at least five resolved distinct positions, compute Spearman correlation of `-position` with `ret` and separately with `excess_spy`. Summarize the distribution at the date level; do not pool stock rows as independent market episodes.

No score field, contextual lobe, sector slice, ticker example, or threshold may be added after the read to improve the story.

## 7. Uncertainty and dependence

For each horizon, report the number of eligible distinct board dates and raw rows. For the incidence of each co-loss event and the paired top-12 differences, use a circular moving-block bootstrap over ordered board dates:

- 2,000 draws;
- block length equal to `min(horizon, number_of_dates)`;
- seed `20260911`;
- 2.5%, 50%, and 97.5% percentiles.

This is an overlap-aware descriptive interval, not a distribution-free guarantee. When fewer than 20 eligible dates exist, report `UNDERPOWERED_DESCRIPTIVE` and do not print a directional conclusion for that horizon.

## 8. Fixed interpretation matrix

- Frequent market-aligned co-loss supports the need to evaluate shared market exposure/entry eligibility; it does not validate a proposed warning model.
- Frequent selection-specific co-loss is evidence against blaming only the broad market; it does not identify which ranking feature caused the loss.
- A top-12 difference whose interval excludes zero in the harmful direction is an investigation trigger for the existing ordering/feature surface, not automatic re-ranking.
- An interval spanning zero is `NO_CLEAR_SEPARATION`, not proof of equality.
- A favorable top-12 result does not establish absolute buyability.
- Any result remains retrospective and cannot promote a gate, ranker, entry policy, or public performance claim.

## 9. Implementation and stop contract

Create a small offline research harness in this same records carrier, with synthetic tests written and observed failing before implementation. Tests must cover duplicate-grain refusal, missing-outcome denominator preservation, benchmark disagreement refusal, exact threshold inclusivity, top-12 tie determinism, date-level rather than row-level inference, moving-block reproducibility, and an all-loss board.

Execute the frozen artifact once after tests pass. Preserve exact input/code/result hashes, exclusions, per-horizon board tables, aggregate summaries, and a dated interpretation. Do not tune thresholds, inspect alternate ledgers, add predictors, fit a model, retrieve current production data, access W3 comparative outcomes, or convert the result into source/product work.

Stop with one of:

- `AUDIT_EXECUTED_WITH_LIMITS`;
- `UNDERPOWERED_DESCRIPTIVE` for affected horizons;
- `ABORTED_CONTRACT_FAILURE` with the exact failed invariant.

The live closed-read repair, the independent pilot review, P0C horizon ownership, and B2/B3/B4 Entry Truth work remain separate existing-owner continuations.