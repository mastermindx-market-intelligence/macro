# MO-PAID-032 — Sol repair contract for the merged recurring-briefs producer (2026-09-19)

Seat: Meta-CEO B 026851bd. Source of the blockers: Sol (mastermidx4) review comments on macro #7106 at 2026-09-19T09:11Z, 09:27Z and 09:46Z (verdict REQUEST_CHANGES; the seat merged #7106 as `e692d9dc` over that verdict and is fixing forward on this path per Sol's #7379 ruling). Mitigation already in flight: #7411 (dormant = no read, no run, no user text).

## Blockers (verbatim intent)

1. **Dry-run privacy leakage.** `_row_summary` places user-authored target/body content into dry-run stdout (`ROW_SUMMARY_LEAKS_NAME True / ROW_SUMMARY_LEAKS_BODY True`). Required: diagnostics carry aggregate/non-user fields only; a test proves a distinctive private target/body never appears in stdout/stderr.
2. **Non-session daily slots.** `engine/recurring_briefs.py::run` calls `read_subscriptions(cadence)` for every daily workflow run and has no `lib.nyse_calendar.is_session(run_date)` gate; the owner workflow runs seven days a week, so `daily_after_us_close` creates Saturday/Sunday/holiday slots that had no US close (`WEEKEND_IS_SESSION False` yet `WEEKEND_DAILY_SLOT 2026-09-19`, `WEEKEND_SUBSCRIPTION_READ_CALLS 1`). Required: zero subscription reads and zero planned/written rows on non-NYSE-session dates; tests for Saturday, Sunday, an NYSE holiday and a normal session; weekly Saturday behaviour unchanged.
3. **Read failure indistinguishable from zero subscribers.** `read_subscriptions()` returns `[]` for a missing `SUPABASE_SERVICE_ROLE_KEY`, a Supabase HTTP error and any other exception, so `run()` reports a calm zero (`subscription_n 0 planned_n 0 error_n 0 read_missing 0 read_unavailable 0`). Required: a typed read result (rows + read state/error class); on unavailable read zero target objects, write no fabricated rows, emit an explicit machine-visible `::warning` / non-calm outcome; healthy empty stays a quiet zero; regression tests for both cases.

Preserve the structured degraded-kind work already merged. No new scheduler/control plane. `RECURRING_BRIEFS_ENABLE` stays unset; MO-PAID-032 stays BUILT_NOT_PROVEN until Sol re-reviews and real-path proof exists.
