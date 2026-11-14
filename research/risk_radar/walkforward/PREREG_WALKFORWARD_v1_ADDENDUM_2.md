# Addendum 2 to PREREG_WALKFORWARD_v1: 2026-11-12, before any fit

This addendum is a separate file, so the pinned SHA-256 of the prereg (01e66c59…ca7e7ca) still
verifies. It applies findings H19 and H20 from the research desk's attack seat. No fit had run
when it was written.

1. **Availability lag. This touches §1 ("Features are the shipped causal transforms").**
   - **Affected legs.** FRED-sourced legs are stamped with their observation date but are
     published the next morning. The legs are credit_oas_roc (ICE BofA HY OAS), rates_realrate
     (DFII10) and jpy_carry (DEXJPUS).
   - **Correction.** All three are shifted one session (`inputs.incumbent_signals()`,
     `inputs.AVAILABILITY_LAG`). The shift applies to the walk-forward, the shipped-v2
     comparator, the HY OAS baseline and any challenger alike.
   - **What is unchanged.** The transforms themselves, the fitted quantities, the folds, the
     objective and the primary endpoint.
   - **DEXJPUS caveat.** It is published weekly (H.10), so one session is a floor; it was not
     verified.
2. **Execution lag (secondary reads only).** Paper economics and the insurer sleeve assume a
   signal seen at d's close is executed at d+1's close, so the sleeve is out of SPY for session
   d+2 (`exec_lag=1`). The pivot read is not affected: it scores when a call is made, not when it
   is executed.
3. **Mechanical references (H20), added as baselines.** Both are causal and use convention
   levels, never fitted. Every signal is read against them:
   - `mech_near_high_1pct`: SPY within 1% of its running total-return peak. It fires where onsets
     occur by construction.
   - `mech_dd_ge_5pct`: SPY already at least 5% below its peak. It confirms by construction.
