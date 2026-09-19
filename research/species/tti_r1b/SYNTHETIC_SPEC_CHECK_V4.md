# TTI R1-B v4 synthetic specification check

**Evidence class:** synthetic/static-only pre-run validation. **No market data read, no outcome opened, no TrialLedger mutation.**

Bound freeze commit: `4db8d0edc63997f7f7944c3b35ac04709461b810`. Prereg SHA256 `a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3`; config SHA256 `24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19`.

Thirteen deterministic cases passed. They preserve the v3 thresholds/latency/population/grid and pin the v4 identity correction: there is no global first-event gate; an unqualified early anchor does not consume a later qualifying selector; one anchor may lawfully fire multiple independent selectors; a second event for the same selector is refused; the control census is first lawful BASE anchor per 30-minute bin and ignores future selector labels; candidate-anchor and pre-confirmation episode-low survival remain separate.

This check is not the authoritative market implementation, not a backtest, and not a promotion result. V1–v3 remain DO_NOT_RUN. Only v4 may be registered after R1-A's shared-source gate clears, and all 60 rows must reach the existing `entry_radar` TrialLedger before any R1-B outcome read.
