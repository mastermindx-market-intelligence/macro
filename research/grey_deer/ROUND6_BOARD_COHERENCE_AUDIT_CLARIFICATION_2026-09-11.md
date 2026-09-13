# Round 6 clarification — issued top set, missingness, and internal consistency

**Frozen before outcome-column access:** 2026-09-11 UTC  
**Parent preregistration:** `ROUND6_BOARD_COHERENCE_AUDIT_PREREG_2026-09-11.md` at commit `a30e94b1e7db63161a3a21664ad6cce525ce706f`  
**Source bytes unchanged:** Macro `bbf6c1e65fc9cad1ba40efa26126cc60036713d0`, blob `af8bdb5a0cedfcfe3c3ea0de37c86e79f7736462`, SHA256 `fecaf0aa3e454ad93bd04cebd28b916f6bc71f50d71946ce5f03c5c50aa43399`

This clarification resolves implementation ambiguities before any numeric outcome value, category frequency, date range, or board statistic is read. It changes no threshold, horizon, model, population, or authority.

## 1. Visible top twelve is fixed before outcome availability

The displayed top set is the twelve lowest `(numeric position, ticker)` rows among **all issued rows** on an eligible `(as_of, horizon)` board. It is never reconstituted after dropping unresolved outcomes. Otherwise a missing outcome in a highly ranked row would move a lower-ranked row into the evaluated top set using future data availability.

Top and remainder each retain:

- issued count;
- resolved count;
- resolved coverage;
- point metrics on finite outcomes;
- identification bounds over the issued denominator.

A paired top-versus-remainder point comparison is eligible only when the board has at least thirteen issued rows and both subsets have at least 80% resolved coverage. Ineligible comparisons remain in the coverage output.

## 2. Missingness bounds

For any issued set with `N` rows, `m` resolved rows, and `a` observed losses:

- lower loss fraction = `a / N`;
- upper loss fraction = `(a + N - m) / N`.

The reported resolved-only point fraction is `a / m` when `m > 0`. The same construction applies to severe losses. Co-loss event labels use the resolved-only point fraction only after the preregistered 80% board-coverage gate; the bounds are always reported and no unobserved row is called a winner or loss.

## 3. Benchmark and excess-return consistency

Within each board, all finite `spy_ret` values must agree to absolute tolerance `1e-12`. For rows where `ret`, `spy_ret`, and `excess_spy` are all finite, require `excess_spy == ret - spy_ret` to absolute tolerance `1e-10`. Violation aborts the audit rather than silently recomputing or keeping one field.

## 4. Stable inference unit

The statistical unit is one ordered `(as_of, horizon)` board date. Stock rows are used only to build that date's metrics. Bootstrap inputs are date-level metric vectors; no stock row receives an independent resampling weight.

## 5. Price-basis sensitivity

The full product-era analysis reports every stamped basis. A separately labelled cleaner sensitivity uses only board dates on or after `2026-08-06` whose resolved rows have one non-null basis category and do not use `unverified_pre_20260806`. If that leaves fewer than twenty eligible dates for a horizon, it remains `UNDERPOWERED_DESCRIPTIVE` and cannot replace the full result.

## 6. Stop law unchanged

The audit remains a one-time descriptive use of the frozen ledger. No alternative file, threshold, top-set width, loss definition, sector slice, score field, entry status, or horizon may be introduced after reading outcomes to improve the conclusion. The live closed-read repair and all Entry Truth implementation remain separate owner work.