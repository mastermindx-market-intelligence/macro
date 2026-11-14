# Catalogue part (a) placebo p90 — Rule A re-score

**CORRECTION LINE (not a new read); placebo p90 under repair; part (a) provisional.**

Rule: `PLACEBO_PLACEMENT_SPEC_v1` **Rule A**, cap `10 * n_draws`, co-signed Amendment 1; placement from `catalogue/placebo_rule_a.py`. Nothing else changes: same alerts, windows (all end ≤ 2023-12-29), turns, episodes, kind, post, seed 20261112, n_draws, tol 0.01, outcomes_through.

Step A reproduced each read's recorded p90 with the original carrier (`bm_ref.cluster_placebo_p90` for v2/pre; the read's own `parallel_p90`, which calls `bm_ref._placebo_draw_arrays`, for rev1/bt1). Step B swapped only the placement. Pairing is the k-th kept draw of every asset (spec §3), checked against `pair_kept_draws`.

## Per-set table

| read | set | kind | observed | old p90 | new p90 | (a) old → new | FLIP | alert share (pooled) | undefined assets |
|---|---|---|---:|---:|---:|---|---|---:|---:|
| v2 | rr-roff-incumbent-v2 | top | 0.333 | 0.378 | not defined | False → not defined | — | 0.2240 | 4 |
| v2 | rr-roff-confluence-k4-v2 | top | 0.511 | 0.400 | not defined | True → not defined | **FLIP** | 0.1383 | 5 |
| v2 | rr-ron-incumbent-v2 | bottom | 0.250 | 0.583 | 0.583 | False → False | — | 0.2240 | 0 |
| v2 | rr-ron-confluence-k4-v2 | bottom | 0.438 | 0.646 | 0.646 | False → False | — | 0.1383 | 0 |
| v2 | rr-ron-exit-v1-v2 | bottom | 0.271 | 0.458 | 0.438 | False → False | — | 0.2833 | 0 |
| pre | rr-roff-confluence-k3-followup | top | 0.449 | 0.370 | not defined | True → not defined | **FLIP** | 0.1837 | 14 |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | 0.449 | 0.370 | not defined | True → not defined | **FLIP** | 0.1837 | 14 |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | 0.795 | 0.378 | not defined | True → not defined | **FLIP** | 0.0973 | 14 |
| bt1 | dfii10 | top | 0.173 | 0.307 | not defined | False → not defined | — | 0.0150 | 4 |
| bt1 | dgs10 | top | 0.142 | 0.276 | not defined | False → not defined | — | 0.0076 | 2 |

(a) is read at the read's own printed precision: observed cluster share > cluster p90. `not defined` means at least one contributing asset hit the attempt cap or an empty eligible pool under Rule A.

**FLIP convention.** `FLIP` marks a set whose part (a) *pass* changed state: a former `True` that is no longer `True`. A set that was already `False` and is now `not defined` is **not** marked FLIP, but (a) is no longer evaluable — it is not a preserved `False`. Read the new column as: `False` where the set was defined and still fails, `not defined at this exposure` everywhere else. No top-exposure set is defined under Rule A, so every part (a) pass in this catalogue depended on the repaired placement.

## Alert share beside the p90 — per asset and pooled

Alert share is the fraction of that asset's windowed sessions the alert is ON (so it is the same for both p90 columns). The pooled figure is the session-weighted mean across the set's contributing assets, and is the one repeated in the per-set table above.

| read | set | kind | asset | alert share | old p90 | new p90 |
|---|---|---|---|---:|---:|---:|
| v2 | rr-roff-incumbent-v2 | top | BAA_10Y | 0.2247 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | CYC/DEF | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | DIA | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | EEM/SPY | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | HYG/IEF | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | HY_OAS | 0.2235 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | IGV/EWDEF | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | IWM | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | IWM/SPY | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | MDY | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | QQQ | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | QQQ/EWDEF | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | RSP | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | RSP/SPY | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | RSPT/EWDEF | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | SMH/EWDEF | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | SPHB/SPLV | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | SPY | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | SPY/GLD | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | SPY/TLT | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | XLK/EWDEF | 0.2240 | 0.378 | not defined |
| v2 | rr-roff-incumbent-v2 | top | **pooled** | **0.2240** | **0.378** | **not defined** |
| v2 | rr-roff-confluence-k4-v2 | top | BAA_10Y | 0.1394 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | CYC/DEF | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | DIA | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | EEM/SPY | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | HYG/IEF | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | HY_OAS | 0.1380 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | IGV/EWDEF | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | IWM | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | IWM/SPY | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | MDY | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | QQQ | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | QQQ/EWDEF | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | RSP | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | RSP/SPY | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | RSPT/EWDEF | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | SMH/EWDEF | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | SPHB/SPLV | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | SPY | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | SPY/GLD | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | SPY/TLT | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | XLK/EWDEF | 0.1383 | 0.400 | not defined |
| v2 | rr-roff-confluence-k4-v2 | top | **pooled** | **0.1383** | **0.400** | **not defined** |
| v2 | rr-ron-incumbent-v2 | bottom | BAA_10Y | 0.2247 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | CYC/DEF | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | DIA | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | EEM/SPY | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | HYG/IEF | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | HY_OAS | 0.2235 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | IGV/EWDEF | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | IWM | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | IWM/SPY | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | MDY | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | QQQ | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | QQQ/EWDEF | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | RSP | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | RSP/SPY | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | RSPT/EWDEF | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | SMH/EWDEF | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | SPHB/SPLV | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | SPY | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | SPY/GLD | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | SPY/TLT | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | XLK/EWDEF | 0.2240 | 0.583 | 0.583 |
| v2 | rr-ron-incumbent-v2 | bottom | **pooled** | **0.2240** | **0.583** | **0.583** |
| v2 | rr-ron-confluence-k4-v2 | bottom | BAA_10Y | 0.1394 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | CYC/DEF | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | DIA | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | EEM/SPY | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | HYG/IEF | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | HY_OAS | 0.1380 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | IGV/EWDEF | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | IWM | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | IWM/SPY | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | MDY | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | QQQ | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | QQQ/EWDEF | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | RSP | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | RSP/SPY | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | RSPT/EWDEF | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | SMH/EWDEF | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | SPHB/SPLV | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | SPY | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | SPY/GLD | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | SPY/TLT | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | XLK/EWDEF | 0.1383 | 0.646 | 0.646 |
| v2 | rr-ron-confluence-k4-v2 | bottom | **pooled** | **0.1383** | **0.646** | **0.646** |
| v2 | rr-ron-exit-v1-v2 | bottom | BAA_10Y | 0.2836 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | CYC/DEF | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | DIA | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | EEM/SPY | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | HYG/IEF | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | HY_OAS | 0.2826 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | IGV/EWDEF | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | IWM | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | IWM/SPY | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | MDY | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | QQQ | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | QQQ/EWDEF | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | RSP | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | RSP/SPY | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | RSPT/EWDEF | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | SMH/EWDEF | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | SPHB/SPLV | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | SPY | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | SPY/GLD | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | SPY/TLT | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | XLK/EWDEF | 0.2833 | 0.458 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | **pooled** | **0.2833** | **0.458** | **0.438** |
| pre | rr-roff-confluence-k3-followup | top | BAA_10Y | 0.1825 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | CYC/DEF | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | DIA | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | EEM/SPY | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | HYG/IEF | 0.1975 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | HY_OAS | 0.1821 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | IGV/EWDEF | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | IWM | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | IWM/SPY | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | MDY | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | QQQ | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | QQQ/EWDEF | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | RSP | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | RSP/SPY | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | RSPT/EWDEF | 0.1914 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | SMH/EWDEF | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | SPHB/SPLV | 0.1794 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | SPY | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | SPY/GLD | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | SPY/TLT | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | XLK/EWDEF | 0.1828 | 0.370 | not defined |
| pre | rr-roff-confluence-k3-followup | top | **pooled** | **0.1837** | **0.370** | **not defined** |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | BAA_10Y | 0.1825 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | CYC/DEF | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | DIA | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | EEM/SPY | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | HYG/IEF | 0.1975 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | HY_OAS | 0.1821 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | IGV/EWDEF | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | IWM | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | IWM/SPY | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | MDY | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | QQQ | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | QQQ/EWDEF | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | RSP | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | RSP/SPY | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | RSPT/EWDEF | 0.1914 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | SMH/EWDEF | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | SPHB/SPLV | 0.1794 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | SPY | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | SPY/GLD | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | SPY/TLT | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | XLK/EWDEF | 0.1828 | 0.370 | not defined |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | **pooled** | **0.1837** | **0.370** | **not defined** |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | BAA_10Y | 0.0965 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | CYC/DEF | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | DIA | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | EEM/SPY | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | HYG/IEF | 0.1014 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | HY_OAS | 0.0961 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | IGV/EWDEF | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | IWM | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | IWM/SPY | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | MDY | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | QQQ | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | QQQ/EWDEF | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | RSP | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | RSP/SPY | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | RSPT/EWDEF | 0.0998 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | SMH/EWDEF | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | SPHB/SPLV | 0.0886 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | SPY | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | SPY/GLD | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | SPY/TLT | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | XLK/EWDEF | 0.0973 | 0.378 | not defined |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | **pooled** | **0.0973** | **0.378** | **not defined** |
| bt1 | dfii10 | top | BAA_10Y | 0.0148 | 0.307 | not defined |
| bt1 | dfii10 | top | CYC/DEF | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | DIA | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | EEM/SPY | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | HYG/IEF | 0.0165 | 0.307 | not defined |
| bt1 | dfii10 | top | HY_OAS | 0.0144 | 0.307 | not defined |
| bt1 | dfii10 | top | IGV/EWDEF | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | IWM | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | IWM/SPY | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | MDY | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | QQQ | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | QQQ/EWDEF | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | RSP | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | RSP/SPY | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | RSPT/EWDEF | 0.0160 | 0.307 | not defined |
| bt1 | dfii10 | top | SMH/EWDEF | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | SPHB/SPLV | 0.0147 | 0.307 | not defined |
| bt1 | dfii10 | top | SPY | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | SPY/GLD | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | SPY/TLT | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | XLK/EWDEF | 0.0150 | 0.307 | not defined |
| bt1 | dfii10 | top | **pooled** | **0.0150** | **0.307** | **not defined** |
| bt1 | dgs10 | top | BAA_10Y | 0.0077 | 0.276 | not defined |
| bt1 | dgs10 | top | CYC/DEF | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | DIA | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | EEM/SPY | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | HYG/IEF | 0.0081 | 0.276 | not defined |
| bt1 | dgs10 | top | HY_OAS | 0.0073 | 0.276 | not defined |
| bt1 | dgs10 | top | IGV/EWDEF | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | IWM | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | IWM/SPY | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | MDY | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | QQQ | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | QQQ/EWDEF | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | RSP | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | RSP/SPY | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | RSPT/EWDEF | 0.0079 | 0.276 | not defined |
| bt1 | dgs10 | top | SMH/EWDEF | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | SPHB/SPLV | 0.0055 | 0.276 | not defined |
| bt1 | dgs10 | top | SPY | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | SPY/GLD | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | SPY/TLT | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | XLK/EWDEF | 0.0076 | 0.276 | not defined |
| bt1 | dgs10 | top | **pooled** | **0.0076** | **0.276** | **not defined** |

## Reproduction (step A)

| read | set | recorded p90 | reproduced p90 | diff | recorded observed | reproduced observed | recorded valid draws |
|---|---|---:|---:|---:|---:|---:|---:|
| v2 | rr-roff-incumbent-v2 | 0.378 | 0.378 | 0.0 | 0.333 | 0.333 | 2000 |
| v2 | rr-roff-confluence-k4-v2 | 0.400 | 0.400 | 0.0 | 0.511 | 0.511 | 2000 |
| v2 | rr-ron-incumbent-v2 | 0.583 | 0.583 | 0.0 | 0.250 | 0.250 | 2000 |
| v2 | rr-ron-confluence-k4-v2 | 0.646 | 0.646 | 0.0 | 0.438 | 0.438 | 2000 |
| v2 | rr-ron-exit-v1-v2 | 0.458 | 0.458 | 0.0 | 0.271 | 0.271 | 2000 |
| pre | rr-roff-confluence-k3-followup | 0.370 | 0.370 | 0.0 | 0.449 | 0.449 | 2000 |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | 0.370 | 0.370 | 0.0 | 0.449 | 0.449 | 2000 |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | 0.378 | 0.378 | 0.0 | 0.795 | 0.795 | 2000 |
| bt1 | dfii10 | 0.307 | 0.307 | 0.0 | 0.173 | 0.173 | 2000 |
| bt1 | dgs10 | 0.276 | 0.276 | 0.0 | 0.142 | 0.142 | 2000 |

## Unchanged inputs per set

| read | set | kind | near | post | contributing assets | observed cluster share |
|---|---|---|---|---:|---:|---:|
| v2 | rr-roff-incumbent-v2 | top | high | 5 | 21 | 0.333 |
| v2 | rr-roff-confluence-k4-v2 | top | high | 5 | 21 | 0.511 |
| v2 | rr-ron-incumbent-v2 | bottom | low | 10 | 21 | 0.250 |
| v2 | rr-ron-confluence-k4-v2 | bottom | low | 10 | 21 | 0.438 |
| v2 | rr-ron-exit-v1-v2 | bottom | low | 10 | 21 | 0.271 |
| pre | rr-roff-confluence-k3-followup | top | high | 5 | 21 | 0.449 |
| rev1 | rr-roff-confluence-k3-followup-rev1-repro | top | high | 5 | 21 | 0.449 |
| rev1 | rr-roff-leg-rates-realrate-pre-desc | top | high | 5 | 21 | 0.795 |
| bt1 | dfii10 | top | high | 5 | 21 | 0.173 |
| bt1 | dgs10 | top | high | 5 | 21 | 0.142 |

## Rule A placement, per asset and near

`placed` is the mean share of placed mass landing inside the eligible band; `alert` is the observed alert's own in-band mass share. `alert share` is the fraction of the asset's windowed sessions the alert is ON.

### v2 · rr-roff-incumbent-v2 (near high, post 5)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 20000 | 0 | 20000 | 0.000 | **no** | 26 | not defined | 0.066 | 0.2247 |
| CYC/DEF | 3637 | 2000 | 1637 | 0.550 | yes | 115 | 0.270 | 0.000 | 0.2240 |
| DIA | 2044 | 2000 | 44 | 0.978 | yes | 263 | 0.445 | 0.000 | 0.2240 |
| EEM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 49 | not defined | 0.000 | 0.2240 |
| HYG/IEF | 2001 | 2000 | 1 | 1.000 | yes | 357 | 0.486 | 0.143 | 0.2240 |
| HY_OAS | 20000 | 0 | 20000 | 0.000 | **no** | 17 | not defined | 0.046 | 0.2235 |
| IGV/EWDEF | 2655 | 2000 | 655 | 0.753 | yes | 104 | 0.244 | 0.009 | 0.2240 |
| IWM | 3592 | 2000 | 1592 | 0.557 | yes | 107 | 0.254 | 0.000 | 0.2240 |
| IWM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 57 | not defined | 0.000 | 0.2240 |
| MDY | 2657 | 2000 | 657 | 0.753 | yes | 166 | 0.348 | 0.000 | 0.2240 |
| QQQ | 2092 | 2000 | 92 | 0.956 | yes | 234 | 0.404 | 0.000 | 0.2240 |
| QQQ/EWDEF | 2143 | 2000 | 143 | 0.933 | yes | 166 | 0.320 | 0.013 | 0.2240 |
| RSP | 2251 | 2000 | 251 | 0.888 | yes | 239 | 0.457 | 0.000 | 0.2240 |
| RSP/SPY | 2345 | 2000 | 345 | 0.853 | yes | 169 | 0.338 | 0.270 | 0.2240 |
| RSPT/EWDEF | 2362 | 2000 | 362 | 0.847 | yes | 162 | 0.325 | 0.000 | 0.2240 |
| SMH/EWDEF | 2086 | 2000 | 86 | 0.959 | yes | 155 | 0.291 | 0.004 | 0.2240 |
| SPHB/SPLV | 3976 | 2000 | 1976 | 0.503 | yes | 78 | 0.191 | 0.000 | 0.2240 |
| SPY | 2143 | 2000 | 143 | 0.933 | yes | 288 | 0.498 | 0.000 | 0.2240 |
| SPY/GLD | 3218 | 2000 | 1218 | 0.622 | yes | 106 | 0.257 | 0.000 | 0.2240 |
| SPY/TLT | 2006 | 2000 | 6 | 0.997 | yes | 239 | 0.361 | 0.087 | 0.2240 |
| XLK/EWDEF | 2048 | 2000 | 48 | 0.977 | yes | 197 | 0.333 | 0.009 | 0.2240 |

**Not defined at this exposure:** BAA_10Y, EEM/SPY, HY_OAS, IWM/SPY.

### v2 · rr-roff-confluence-k4-v2 (near high, post 5)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 20000 | 0 | 20000 | 0.000 | **no** | 26 | not defined | 0.127 | 0.1394 |
| CYC/DEF | 5587 | 2000 | 3587 | 0.358 | yes | 115 | 0.493 | 0.000 | 0.1383 |
| DIA | 2002 | 2000 | 2 | 0.999 | yes | 263 | 0.677 | 0.007 | 0.1383 |
| EEM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 49 | not defined | 0.000 | 0.1383 |
| HYG/IEF | 2000 | 2000 | 0 | 1.000 | yes | 357 | 0.736 | 0.106 | 0.1383 |
| HY_OAS | 20000 | 0 | 20000 | 0.000 | **no** | 17 | not defined | 0.088 | 0.1380 |
| IGV/EWDEF | 3553 | 2000 | 1553 | 0.563 | yes | 104 | 0.440 | 0.021 | 0.1383 |
| IWM | 12471 | 2000 | 10471 | 0.160 | yes | 107 | 0.464 | 0.000 | 0.1383 |
| IWM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 57 | not defined | 0.000 | 0.1383 |
| MDY | 2246 | 2000 | 246 | 0.890 | yes | 166 | 0.583 | 0.000 | 0.1383 |
| QQQ | 2002 | 2000 | 2 | 0.999 | yes | 234 | 0.632 | 0.007 | 0.1383 |
| QQQ/EWDEF | 2040 | 2000 | 40 | 0.980 | yes | 166 | 0.549 | 0.021 | 0.1383 |
| RSP | 2035 | 2000 | 35 | 0.983 | yes | 239 | 0.677 | 0.000 | 0.1383 |
| RSP/SPY | 2369 | 2000 | 369 | 0.844 | yes | 169 | 0.611 | 0.183 | 0.1383 |
| RSPT/EWDEF | 2155 | 2000 | 155 | 0.928 | yes | 162 | 0.555 | 0.014 | 0.1383 |
| SMH/EWDEF | 2008 | 2000 | 8 | 0.996 | yes | 155 | 0.490 | 0.028 | 0.1383 |
| SPHB/SPLV | 20000 | 47 | 19953 | 0.002 | **no** | 78 | 0.374 | 0.000 | 0.1383 |
| SPY | 2017 | 2000 | 17 | 0.992 | yes | 288 | 0.728 | 0.014 | 0.1383 |
| SPY/GLD | 3691 | 2000 | 1691 | 0.542 | yes | 106 | 0.448 | 0.014 | 0.1383 |
| SPY/TLT | 2000 | 2000 | 0 | 1.000 | yes | 239 | 0.571 | 0.070 | 0.1383 |
| XLK/EWDEF | 2004 | 2000 | 4 | 0.998 | yes | 197 | 0.563 | 0.014 | 0.1383 |

**Not defined at this exposure:** BAA_10Y, EEM/SPY, HY_OAS, IWM/SPY, SPHB/SPLV.

### v2 · rr-ron-incumbent-v2 (near low, post 10)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 2161 | 2000 | 161 | 0.925 | yes | 219 | 0.399 | 0.148 | 0.2247 |
| CYC/DEF | 2003 | 2000 | 3 | 0.999 | yes | 265 | 0.430 | 0.230 | 0.2240 |
| DIA | 2008 | 2000 | 8 | 0.996 | yes | 338 | 0.515 | 0.161 | 0.2240 |
| EEM/SPY | 2005 | 2000 | 5 | 0.998 | yes | 300 | 0.416 | 0.191 | 0.2240 |
| HYG/IEF | 2004 | 2000 | 4 | 0.998 | yes | 471 | 0.587 | 0.404 | 0.2240 |
| HY_OAS | 2155 | 2000 | 155 | 0.928 | yes | 195 | 0.362 | 0.105 | 0.2235 |
| IGV/EWDEF | 2001 | 2000 | 1 | 1.000 | yes | 264 | 0.391 | 0.235 | 0.2240 |
| IWM | 2002 | 2000 | 2 | 0.999 | yes | 183 | 0.335 | 0.113 | 0.2240 |
| IWM/SPY | 2002 | 2000 | 2 | 0.999 | yes | 282 | 0.414 | 0.104 | 0.2240 |
| MDY | 2009 | 2000 | 9 | 0.996 | yes | 230 | 0.386 | 0.130 | 0.2240 |
| QQQ | 2001 | 2000 | 1 | 1.000 | yes | 362 | 0.502 | 0.183 | 0.2240 |
| QQQ/EWDEF | 2001 | 2000 | 1 | 1.000 | yes | 303 | 0.431 | 0.270 | 0.2240 |
| RSP | 2008 | 2000 | 8 | 0.996 | yes | 315 | 0.494 | 0.191 | 0.2240 |
| RSP/SPY | 2001 | 2000 | 1 | 1.000 | yes | 539 | 0.647 | 0.552 | 0.2240 |
| RSPT/EWDEF | 2001 | 2000 | 1 | 1.000 | yes | 280 | 0.426 | 0.157 | 0.2240 |
| SMH/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 294 | 0.410 | 0.165 | 0.2240 |
| SPHB/SPLV | 2002 | 2000 | 2 | 0.999 | yes | 196 | 0.326 | 0.117 | 0.2240 |
| SPY | 2008 | 2000 | 8 | 0.996 | yes | 385 | 0.549 | 0.200 | 0.2240 |
| SPY/GLD | 2045 | 2000 | 45 | 0.978 | yes | 214 | 0.407 | 0.070 | 0.2240 |
| SPY/TLT | 2001 | 2000 | 1 | 1.000 | yes | 365 | 0.466 | 0.265 | 0.2240 |
| XLK/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 368 | 0.448 | 0.196 | 0.2240 |

### v2 · rr-ron-confluence-k4-v2 (near low, post 10)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 2001 | 2000 | 1 | 1.000 | yes | 219 | 0.628 | 0.204 | 0.1394 |
| CYC/DEF | 2000 | 2000 | 0 | 1.000 | yes | 265 | 0.656 | 0.310 | 0.1383 |
| DIA | 2000 | 2000 | 0 | 1.000 | yes | 338 | 0.739 | 0.239 | 0.1383 |
| EEM/SPY | 2000 | 2000 | 0 | 1.000 | yes | 300 | 0.645 | 0.106 | 0.1383 |
| HYG/IEF | 2000 | 2000 | 0 | 1.000 | yes | 471 | 0.794 | 0.542 | 0.1383 |
| HY_OAS | 2000 | 2000 | 0 | 1.000 | yes | 195 | 0.552 | 0.170 | 0.1380 |
| IGV/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 264 | 0.589 | 0.373 | 0.1383 |
| IWM | 2000 | 2000 | 0 | 1.000 | yes | 183 | 0.572 | 0.225 | 0.1383 |
| IWM/SPY | 2000 | 2000 | 0 | 1.000 | yes | 282 | 0.636 | 0.275 | 0.1383 |
| MDY | 2001 | 2000 | 1 | 1.000 | yes | 230 | 0.619 | 0.239 | 0.1383 |
| QQQ | 2000 | 2000 | 0 | 1.000 | yes | 362 | 0.695 | 0.289 | 0.1383 |
| QQQ/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 303 | 0.628 | 0.380 | 0.1383 |
| RSP | 2000 | 2000 | 0 | 1.000 | yes | 315 | 0.710 | 0.296 | 0.1383 |
| RSP/SPY | 2000 | 2000 | 0 | 1.000 | yes | 539 | 0.829 | 0.465 | 0.1383 |
| RSPT/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 280 | 0.633 | 0.232 | 0.1383 |
| SMH/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 294 | 0.612 | 0.232 | 0.1383 |
| SPHB/SPLV | 2000 | 2000 | 0 | 1.000 | yes | 196 | 0.538 | 0.211 | 0.1383 |
| SPY | 2000 | 2000 | 0 | 1.000 | yes | 385 | 0.753 | 0.317 | 0.1383 |
| SPY/GLD | 2007 | 2000 | 7 | 0.997 | yes | 214 | 0.627 | 0.127 | 0.1383 |
| SPY/TLT | 2000 | 2000 | 0 | 1.000 | yes | 365 | 0.654 | 0.345 | 0.1383 |
| XLK/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 368 | 0.631 | 0.268 | 0.1383 |

### v2 · rr-ron-exit-v1-v2 (near low, post 10)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 2130 | 2000 | 130 | 0.939 | yes | 219 | 0.368 | 0.156 | 0.2836 |
| CYC/DEF | 2001 | 2000 | 1 | 1.000 | yes | 265 | 0.380 | 0.192 | 0.2833 |
| DIA | 2001 | 2000 | 1 | 1.000 | yes | 338 | 0.460 | 0.134 | 0.2833 |
| EEM/SPY | 2002 | 2000 | 2 | 0.999 | yes | 300 | 0.352 | 0.189 | 0.2833 |
| HYG/IEF | 2001 | 2000 | 1 | 1.000 | yes | 471 | 0.538 | 0.430 | 0.2833 |
| HY_OAS | 2041 | 2000 | 41 | 0.980 | yes | 195 | 0.313 | 0.100 | 0.2826 |
| IGV/EWDEF | 2002 | 2000 | 2 | 0.999 | yes | 264 | 0.347 | 0.230 | 0.2833 |
| IWM | 2000 | 2000 | 0 | 1.000 | yes | 183 | 0.297 | 0.096 | 0.2833 |
| IWM/SPY | 2001 | 2000 | 1 | 1.000 | yes | 282 | 0.358 | 0.127 | 0.2833 |
| MDY | 2002 | 2000 | 2 | 0.999 | yes | 230 | 0.349 | 0.110 | 0.2833 |
| QQQ | 2000 | 2000 | 0 | 1.000 | yes | 362 | 0.475 | 0.151 | 0.2833 |
| QQQ/EWDEF | 2004 | 2000 | 4 | 0.998 | yes | 303 | 0.392 | 0.261 | 0.2833 |
| RSP | 2002 | 2000 | 2 | 0.999 | yes | 315 | 0.445 | 0.155 | 0.2833 |
| RSP/SPY | 2001 | 2000 | 1 | 1.000 | yes | 539 | 0.608 | 0.540 | 0.2833 |
| RSPT/EWDEF | 2001 | 2000 | 1 | 1.000 | yes | 280 | 0.389 | 0.141 | 0.2833 |
| SMH/EWDEF | 2002 | 2000 | 2 | 0.999 | yes | 294 | 0.358 | 0.162 | 0.2833 |
| SPHB/SPLV | 2000 | 2000 | 0 | 1.000 | yes | 196 | 0.288 | 0.100 | 0.2833 |
| SPY | 2002 | 2000 | 2 | 0.999 | yes | 385 | 0.518 | 0.162 | 0.2833 |
| SPY/GLD | 2005 | 2000 | 5 | 0.998 | yes | 214 | 0.358 | 0.072 | 0.2833 |
| SPY/TLT | 2000 | 2000 | 0 | 1.000 | yes | 365 | 0.406 | 0.241 | 0.2833 |
| XLK/EWDEF | 2001 | 2000 | 1 | 1.000 | yes | 368 | 0.404 | 0.179 | 0.2833 |

### pre · rr-roff-confluence-k3-followup (near high, post 5)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 20000 | 0 | 20000 | 0.000 | **no** | 128 | not defined | 0.157 | 0.1825 |
| CYC/DEF | 20000 | 0 | 20000 | 0.000 | **no** | 60 | not defined | 0.000 | 0.1828 |
| DIA | 2000 | 2000 | 0 | 1.000 | yes | 1156 | 0.655 | 0.080 | 0.1828 |
| EEM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 208 | not defined | 0.022 | 0.1828 |
| HYG/IEF | 20000 | 0 | 20000 | 0.000 | **no** | 313 | not defined | 0.014 | 0.1975 |
| HY_OAS | 20000 | 0 | 20000 | 0.000 | **no** | 119 | not defined | 0.143 | 0.1821 |
| IGV/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 208 | not defined | 0.006 | 0.1828 |
| IWM | 2013 | 2000 | 13 | 0.994 | yes | 626 | 0.478 | 0.026 | 0.1828 |
| IWM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 118 | not defined | 0.005 | 0.1828 |
| MDY | 2004 | 2000 | 4 | 0.998 | yes | 893 | 0.575 | 0.057 | 0.1828 |
| QQQ | 2000 | 2000 | 0 | 1.000 | yes | 1027 | 0.602 | 0.080 | 0.1828 |
| QQQ/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 332 | not defined | 0.025 | 0.1828 |
| RSP | 2000 | 2000 | 0 | 1.000 | yes | 1057 | 0.622 | 0.057 | 0.1828 |
| RSP/SPY | 2436 | 2000 | 436 | 0.821 | yes | 885 | 0.696 | 0.094 | 0.1828 |
| RSPT/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 58 | not defined | 0.002 | 0.1914 |
| SMH/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 20 | not defined | 0.000 | 0.1828 |
| SPHB/SPLV | 20000 | 0 | 20000 | 0.000 | **no** | 4 | not defined | 0.000 | 0.1794 |
| SPY | 2000 | 2000 | 0 | 1.000 | yes | 1196 | 0.668 | 0.082 | 0.1828 |
| SPY/GLD | 20000 | 0 | 20000 | 0.000 | **no** | 158 | not defined | 0.017 | 0.1828 |
| SPY/TLT | 20000 | 0 | 20000 | 0.000 | **no** | 235 | not defined | 0.002 | 0.1828 |
| XLK/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 173 | not defined | 0.009 | 0.1828 |

**Not defined at this exposure:** BAA_10Y, CYC/DEF, EEM/SPY, HYG/IEF, HY_OAS, IGV/EWDEF, IWM/SPY, QQQ/EWDEF, RSPT/EWDEF, SMH/EWDEF, SPHB/SPLV, SPY/GLD, SPY/TLT, XLK/EWDEF.

### rev1 · rr-roff-confluence-k3-followup-rev1-repro (near high, post 5)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 20000 | 0 | 20000 | 0.000 | **no** | 128 | not defined | 0.157 | 0.1825 |
| CYC/DEF | 20000 | 0 | 20000 | 0.000 | **no** | 60 | not defined | 0.000 | 0.1828 |
| DIA | 2000 | 2000 | 0 | 1.000 | yes | 1156 | 0.655 | 0.080 | 0.1828 |
| EEM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 208 | not defined | 0.022 | 0.1828 |
| HYG/IEF | 20000 | 0 | 20000 | 0.000 | **no** | 313 | not defined | 0.014 | 0.1975 |
| HY_OAS | 20000 | 0 | 20000 | 0.000 | **no** | 119 | not defined | 0.143 | 0.1821 |
| IGV/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 208 | not defined | 0.006 | 0.1828 |
| IWM | 2013 | 2000 | 13 | 0.994 | yes | 626 | 0.478 | 0.026 | 0.1828 |
| IWM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 118 | not defined | 0.005 | 0.1828 |
| MDY | 2004 | 2000 | 4 | 0.998 | yes | 893 | 0.575 | 0.057 | 0.1828 |
| QQQ | 2000 | 2000 | 0 | 1.000 | yes | 1027 | 0.602 | 0.080 | 0.1828 |
| QQQ/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 332 | not defined | 0.025 | 0.1828 |
| RSP | 2000 | 2000 | 0 | 1.000 | yes | 1057 | 0.622 | 0.057 | 0.1828 |
| RSP/SPY | 2436 | 2000 | 436 | 0.821 | yes | 885 | 0.696 | 0.094 | 0.1828 |
| RSPT/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 58 | not defined | 0.002 | 0.1914 |
| SMH/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 20 | not defined | 0.000 | 0.1828 |
| SPHB/SPLV | 20000 | 0 | 20000 | 0.000 | **no** | 4 | not defined | 0.000 | 0.1794 |
| SPY | 2000 | 2000 | 0 | 1.000 | yes | 1196 | 0.668 | 0.082 | 0.1828 |
| SPY/GLD | 20000 | 0 | 20000 | 0.000 | **no** | 158 | not defined | 0.017 | 0.1828 |
| SPY/TLT | 20000 | 0 | 20000 | 0.000 | **no** | 235 | not defined | 0.002 | 0.1828 |
| XLK/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 173 | not defined | 0.009 | 0.1828 |

**Not defined at this exposure:** BAA_10Y, CYC/DEF, EEM/SPY, HYG/IEF, HY_OAS, IGV/EWDEF, IWM/SPY, QQQ/EWDEF, RSPT/EWDEF, SMH/EWDEF, SPHB/SPLV, SPY/GLD, SPY/TLT, XLK/EWDEF.

### rev1 · rr-roff-leg-rates-realrate-pre-desc (near high, post 5)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 20000 | 0 | 20000 | 0.000 | **no** | 128 | not defined | 0.085 | 0.0965 |
| CYC/DEF | 20000 | 0 | 20000 | 0.000 | **no** | 60 | not defined | 0.020 | 0.0973 |
| DIA | 2000 | 2000 | 0 | 1.000 | yes | 1156 | 0.889 | 0.359 | 0.0973 |
| EEM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 208 | not defined | 0.041 | 0.0973 |
| HYG/IEF | 20000 | 0 | 20000 | 0.000 | **no** | 313 | not defined | 0.095 | 0.1014 |
| HY_OAS | 20000 | 0 | 20000 | 0.000 | **no** | 119 | not defined | 0.062 | 0.0961 |
| IGV/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 208 | not defined | 0.041 | 0.0973 |
| IWM | 2000 | 2000 | 0 | 1.000 | yes | 626 | 0.772 | 0.180 | 0.0973 |
| IWM/SPY | 20000 | 0 | 20000 | 0.000 | **no** | 118 | not defined | 0.032 | 0.0973 |
| MDY | 2000 | 2000 | 0 | 1.000 | yes | 893 | 0.846 | 0.238 | 0.0973 |
| QQQ | 2000 | 2000 | 0 | 1.000 | yes | 1027 | 0.865 | 0.293 | 0.0973 |
| QQQ/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 332 | not defined | 0.078 | 0.0973 |
| RSP | 2000 | 2000 | 0 | 1.000 | yes | 1057 | 0.865 | 0.301 | 0.0973 |
| RSP/SPY | 2000 | 2000 | 0 | 1.000 | yes | 885 | 0.931 | 0.168 | 0.0973 |
| RSPT/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 58 | not defined | 0.009 | 0.0998 |
| SMH/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 20 | not defined | 0.000 | 0.0973 |
| SPHB/SPLV | 20000 | 0 | 20000 | 0.000 | **no** | 4 | not defined | 0.000 | 0.0886 |
| SPY | 2000 | 2000 | 0 | 1.000 | yes | 1196 | 0.890 | 0.351 | 0.0973 |
| SPY/GLD | 20000 | 0 | 20000 | 0.000 | **no** | 158 | not defined | 0.026 | 0.0973 |
| SPY/TLT | 20000 | 0 | 20000 | 0.000 | **no** | 235 | not defined | 0.064 | 0.0973 |
| XLK/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 173 | not defined | 0.041 | 0.0973 |

**Not defined at this exposure:** BAA_10Y, CYC/DEF, EEM/SPY, HYG/IEF, HY_OAS, IGV/EWDEF, IWM/SPY, QQQ/EWDEF, RSPT/EWDEF, SMH/EWDEF, SPHB/SPLV, SPY/GLD, SPY/TLT, XLK/EWDEF.

### bt1 · dfii10 (near high, post 5)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 2000 | 2000 | 0 | 1.000 | yes | 128 | 0.863 | 0.192 | 0.0148 |
| CYC/DEF | 20000 | 0 | 20000 | 0.000 | **no** | 60 | not defined | 0.000 | 0.0150 |
| DIA | 2000 | 2000 | 0 | 1.000 | yes | 1156 | 0.942 | 0.000 | 0.0150 |
| EEM/SPY | 2000 | 2000 | 0 | 1.000 | yes | 208 | 0.866 | 0.000 | 0.0150 |
| HYG/IEF | 2000 | 2000 | 0 | 1.000 | yes | 313 | 0.933 | 0.019 | 0.0165 |
| HY_OAS | 2000 | 2000 | 0 | 1.000 | yes | 119 | 0.860 | 0.264 | 0.0144 |
| IGV/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 208 | 0.878 | 0.019 | 0.0150 |
| IWM | 2000 | 2000 | 0 | 1.000 | yes | 626 | 0.887 | 0.000 | 0.0150 |
| IWM/SPY | 2000 | 2000 | 0 | 1.000 | yes | 118 | 0.867 | 0.000 | 0.0150 |
| MDY | 2000 | 2000 | 0 | 1.000 | yes | 893 | 0.920 | 0.019 | 0.0150 |
| QQQ | 2000 | 2000 | 0 | 1.000 | yes | 1027 | 0.929 | 0.000 | 0.0150 |
| QQQ/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 332 | 0.884 | 0.019 | 0.0150 |
| RSP | 2000 | 2000 | 0 | 1.000 | yes | 1057 | 0.928 | 0.000 | 0.0150 |
| RSP/SPY | 2000 | 2000 | 0 | 1.000 | yes | 885 | 0.970 | 0.019 | 0.0150 |
| RSPT/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 58 | not defined | 0.019 | 0.0160 |
| SMH/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 20 | not defined | 0.000 | 0.0150 |
| SPHB/SPLV | 20000 | 0 | 20000 | 0.000 | **no** | 4 | not defined | 0.000 | 0.0147 |
| SPY | 2000 | 2000 | 0 | 1.000 | yes | 1196 | 0.940 | 0.000 | 0.0150 |
| SPY/GLD | 2000 | 2000 | 0 | 1.000 | yes | 158 | 0.885 | 0.000 | 0.0150 |
| SPY/TLT | 2000 | 2000 | 0 | 1.000 | yes | 235 | 0.898 | 0.000 | 0.0150 |
| XLK/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 173 | 0.872 | 0.019 | 0.0150 |

**Not defined at this exposure:** CYC/DEF, RSPT/EWDEF, SMH/EWDEF, SPHB/SPLV.

### bt1 · dgs10 (near high, post 5)

| asset | attempts | kept | discarded | acceptance | defined | E sessions | placed mass in E | alert mass in E | alert share |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| BAA_10Y | 2000 | 2000 | 0 | 1.000 | yes | 128 | 0.940 | 0.185 | 0.0077 |
| CYC/DEF | 2005 | 2000 | 5 | 0.998 | yes | 60 | 0.953 | 0.000 | 0.0076 |
| DIA | 2000 | 2000 | 0 | 1.000 | yes | 1156 | 0.975 | 0.000 | 0.0076 |
| EEM/SPY | 2000 | 2000 | 0 | 1.000 | yes | 208 | 0.944 | 0.000 | 0.0076 |
| HYG/IEF | 2000 | 2000 | 0 | 1.000 | yes | 313 | 0.970 | 0.038 | 0.0081 |
| HY_OAS | 2000 | 2000 | 0 | 1.000 | yes | 119 | 0.944 | 0.222 | 0.0073 |
| IGV/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 208 | 0.948 | 0.037 | 0.0076 |
| IWM | 2000 | 2000 | 0 | 1.000 | yes | 626 | 0.949 | 0.000 | 0.0076 |
| IWM/SPY | 2000 | 2000 | 0 | 1.000 | yes | 118 | 0.955 | 0.000 | 0.0076 |
| MDY | 2000 | 2000 | 0 | 1.000 | yes | 893 | 0.965 | 0.000 | 0.0076 |
| QQQ | 2000 | 2000 | 0 | 1.000 | yes | 1027 | 0.968 | 0.000 | 0.0076 |
| QQQ/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 332 | 0.949 | 0.037 | 0.0076 |
| RSP | 2000 | 2000 | 0 | 1.000 | yes | 1057 | 0.967 | 0.000 | 0.0076 |
| RSP/SPY | 2000 | 2000 | 0 | 1.000 | yes | 885 | 0.987 | 0.074 | 0.0076 |
| RSPT/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 58 | 0.938 | 0.038 | 0.0079 |
| SMH/EWDEF | 20000 | 0 | 20000 | 0.000 | **no** | 20 | not defined | 0.000 | 0.0076 |
| SPHB/SPLV | 20000 | 0 | 20000 | 0.000 | **no** | 4 | not defined | 0.000 | 0.0055 |
| SPY | 2000 | 2000 | 0 | 1.000 | yes | 1196 | 0.971 | 0.000 | 0.0076 |
| SPY/GLD | 2000 | 2000 | 0 | 1.000 | yes | 158 | 0.950 | 0.000 | 0.0076 |
| SPY/TLT | 2000 | 2000 | 0 | 1.000 | yes | 235 | 0.958 | 0.000 | 0.0076 |
| XLK/EWDEF | 2000 | 2000 | 0 | 1.000 | yes | 173 | 0.947 | 0.037 | 0.0076 |

**Not defined at this exposure:** SMH/EWDEF, SPHB/SPLV.

## Provenance

| read | runner | window | ledger rows | sets |
|---|---|---|---|---:|
| v2 | `v2_bmref/run_bmref.py` | 2020-01-02..2023-12-29 | 479 rr-roff-incumbent-v2; 480 rr-ron-incumbent-v2; 481 rr-roff-confluence-k4-v2; 482 rr-ron-confluence-k4-v2; 483 rr-ron-exit-v1-v2 | 5 |
| pre | `followup_pre/run_pre.py` | 2006-01-03..2019-12-31 | 484 rr-roff-confluence-k3-followup | 1 |
| rev1 | `followup_rev1/run_rev1.py` | 2006-01-03..2019-12-31 | 512 rr-roff-confluence-k3-followup-rev1-repro; 514 rr-roff-leg-rates-realrate-pre-desc | 2 |
| bt1 | `bt1_pre/run_bt1.py` | 2006-01-03..2019-12-31 | 535 rr-bt1-rate-response-pre-desc; 537 rr-bt1-rate-response-pre-desc (DGS10 substitute) | 2 |

Desk modules pinned: `bm_ref.py` `f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76`; `placebo_rule_a.py` `5270e64e4041331095c1d93ae5addec4c87b91f613c3d4c61853c3eea7cc774c`; `adapter.py` `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1`. The v2/pre reads recorded `bm_ref.py` `c5130e9e2f80c9da3ff85d66a9f3070367f02e71c10d3e411205a97f12a9f066`; `cluster_placebo_p90` and `_placebo_draw_arrays` are byte-identical between those revisions.

No output file names a local absolute path. The desk was read only and `trials.jsonl` was never written.
