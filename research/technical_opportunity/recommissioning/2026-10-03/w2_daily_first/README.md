# W2 Daily-first qualification — October 6, 2026

This packet narrows the first TOI study's data dependency without changing #7094's broad-panel HOLD.

Start with [the source/clock ruling](W2_DAILY_FIRST_SOURCE_RULING_2026-10-06.md). Supporting receipts:
- [raw W-FRI behavior](WEEKLY_SOURCE_CONTRACT_VALIDATION.json)
- [label vs known-date mapping](WEEKLY_KNOWN_DATE_MAPPING_VALIDATION.json)
- [session-calendar completion](WEEKLY_CALENDAR_COMPLETION_VALIDATION.json)
- [S&P1500 PIT membership census](SP1500_PIT_MEMBERSHIP_CENSUS.json)
- [current-source compatibility](CURRENT_SOURCE_COMPATIBILITY.json)
- [exact source/admission snapshot](SOURCE_AND_ADMISSION_SNAPSHOT.json)

The first 22-slot candidate no longer waits on 4H. Broad Daily/Weekly/4H W2 remains held. The proposed population is PIT S&P1500 from 2021-07-06 with missingness retained; historical source knowledge is capped at RETROSPECTIVE unless stronger receipts exist. No outcome or data admission is conferred.

## Live price/date coverage return

The October 6 live R2 coverage return reads only parquet date indexes against the literal PIT membership denominator. Corrected availability is 1,957,003 / 1,990,911 cells (98.2969%). This is not an admission rate: 84.83% of missing cells are before first R2 price under floor-seeded SP400/SP600 membership intervals, exposing identity/membership-start uncertainty rather than proving random price loss. Two keys remain source/identity unresolved. No outcome was read.

## Corporate-action / economic basis

The October 6 corporate-action basis ruling freezes the first-wave transform semantics without building another data plane. Raw massive_stock_day remains the source of record; analytical geometry and primary price-return outcomes require authoritative split events from the existing Data OS reference.corporate_actions owner. Ten synthetic transform tests pass. The house price-jump splitter remains diagnostic only; total-return is secondary/HOLD until dividends and its convention are receipted. Current host access to the Massive corporate-action REST source is owner/credential-gated, so W3 remains HOLD.
## Observational unit and manifest draft

The source-only spell census defines a proposed membership-bounded vendor-ticker spell that never crosses missing expected source sessions or S&P1500 non-membership hiatuses. Its ruling and compact receipt are in this directory. The companion w3_manifest directory binds the 22 Daily planning objects to content-hashed source/population/detector/label/model/evaluation blocks while leaving every unresolved owner setting null. Neither artifact is W3 admission.

