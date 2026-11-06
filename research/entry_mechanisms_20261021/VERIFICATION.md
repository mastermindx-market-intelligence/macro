# Verification record

## Frozen design and inputs

The protocol, initial executable analysis and mechanical checks were committed at `636fb729f9e0bf5dc81847da7a5195eca895c149`, before the outcome run began at 2026-10-21 11:26:22 UTC. The main run completed at 11:28:02 UTC. The original study code hash remained `278792fb1c40ea2dd916c9959a458dc95453f2808d88e15f79e3c0f7c647fd75`; selection lock remained `6744d7b85f78dac077bfddfe75537f263d80ee5c070f6d81b23dc7eb89d3b075`.

The input loader verifies each retained price parquet against its original manifest hash. No new prices were fetched and no original input was changed. Finalist counts for the recent 63-session primary pool agree with the original study, including 842 price-turn, 539 weekly-deep, 73 weekly-crossover and 53 two-week-crossover events.

## Mechanical checks

Eight checks passed locally and on the execution host:

1. Decision close is not substituted for the next executable open.
2. An entry-session stop can trigger, using ATR available at the prior close.
3. A gap through a stop fills at the opening price.
4. Adjustment factors use the correct entry/exit dates; incomplete horizons stay unknown.
5. Peak, trough and reset definitions preserve chronology and prefix invariance.
6. A trough before a later peak cannot be reused as a post-peak reset.
7. Ordinary-entry comparisons exclude the focal observation.
8. Nonoverlap uses the frozen holding endpoint without consulting stop outcomes.

These verify mechanics, not strategy profitability. The baseline's prior completed-bar, calendar and indicator verification remains recorded in its own directory.

## Independent methodological review

A separate reviewer inspected the protocol and implementation for temporal leakage, reset chronology, executable fills, adjustment factors, benchmark construction and event identity. The reviewer found no consequential lookahead or execution-order fault in the core original-roster results.

The review identified three reporting issues, addressed without changing any rule or original CSV result:

- Top comparator calculations were absent from the initial bottom-focused summary path. `review_supplement.py` adds consistently transformed top cash-exit comparisons.
- The first nonoverlap diagnostics selected separately after filtering. The supplement first selects a shared price-event roster, then partitions the gates. Existing per-arm rows remain explicitly labeled policy sensitivities.
- The top event ledger retains counterfactual long return/MAE fields; the dictionary now explicitly distinguishes those from top avoided-return summaries.

Accepted-minus-rejected contrasts resample both arms with the same calendar blocks and record the usable-bootstrap fraction (1.0 in the executed contrasts). The favorable weekly state-matched contrast is explicitly limited to 36/51 recent accepted events. No causal or universally negative oscillator claim is made.

A first supplemental rerun's integrity assertion mistakenly included its own newly extended output among the original files. The check was corrected to compare against the original run's recorded eight CSV hashes. The final supplement completed successfully, with all original CSV hashes unchanged. No signal or outcome was repaired to improve a result.

## Publication verification

The three figures are rendered from saved tables, except the clearly labeled synthetic MACD illustration. All figures are visually inspected. The report cites pinned internal sources and original external papers; previous study claims remain attributed and distinct from the newly executed results. GitHub CI status is a separate publication gate and is reported through the pull request, not treated as investment validation.
