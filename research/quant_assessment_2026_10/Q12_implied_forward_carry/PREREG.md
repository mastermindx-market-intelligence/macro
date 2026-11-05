# Q12 — Robust option-implied forward and carry-consistency estimates: pre-registration

Author: Claude Opus 5.5 (model ID claude-opus-5-5), Q12 AUTHOR, quant assessment 2026-10.
Status: research only. Nothing here is wired, scheduled, promoted or gating.
Reference implementation: `engine/options_parity_forward_interval.py` (RESEARCH_ONLY = True).

## 1. Estimand

For one contract family g = (underlying, expiry, deliverable, multiplier, settlement,
exercise, deliverable_standard) at one observation clock t, the **set of forwards consistent
with same-moment executable-quote bands under European put-call parity**:

    I_k(t) = [K_k + (C_bid - P_ask)/D,  K_k + (C_ask - P_bid)/D]   (widened over [D_lo, D_hi])
    F_hat_g(t) = intersection of I_k(t) over the qualified strikes k in g

Reported as an interval with status consistent, incompatible or unavailable. It is a
measurement of quote-implied carry consistency. It is **not** an executable arbitrage and
**not** a spot forecast. Carry (r - q - borrow) is identified only jointly.

## 2. Unit, clocks, cohort

* Unit: one (family g, clock t) expiry-snapshot.
* Clock: the quote observation timestamp. Both legs must sit within `max_async` = 1 second
  of each other, and within `max_quote_age` = 5 seconds of the snapshot clock.
* Cohort (preferred): European-exercise, cash-settled index options (e.g. SPX/XSP class),
  standard deliverable, 7–90 calendar days to expiry, strikes within ±10% of the forward.
  American equity/ETF options are eligible only for the explicit "unavailable / bounds-only"
  path (brief Q02 owns American adjustment).
* Discount basis: a dated risk-free curve (T-bill/SOFR) interpolated to expiry, with a
  band of ±5 bp in rate as D uncertainty.

## 3. Data vintages (macro-main data at cdab6268, read-only) with sha256

| Input | sha256 |
|---|---|
| data/polygon_gex/chains/*.parquet (28 files, 2026-06-15..2026-08-13; aggregate = sha256 of sorted "sha name" lines) | c0753653e831af9df9464b1766b055988194a046b388ab8bb283bf2e3aa10830 |
| data/flow_signals/ledger.parquet | c14b99cf92c29467d40a823a42e1b8974f018233c76b70d917b403f7a3898b62 |
| data/massive/capability_manifest.json | a47340db753e5a44566590ca714c3cb2524ab4dd686a676e5d1592b5c4f29051 |
| data/thetadata_eod/_manifest.json | c13b9d3af019c1cb7605fd435f2b739e39fa5c572bf09a6492018f232a0444a1 |
| data/thetadata_eod/_backfill_state.json | 913b6737af0a732a4fc4e586b327b7216b9568f9f1062676ad7baf3d89690354 |
| data/options_ivspread/snapshots.parquet | e4e5fa9d701f1727a7894affb85aa49052978218b114780b07d3a77775056ed9 |
| data/options_dislocation/snapshots.parquet | ed5d7876e46539f8617319fcde47789b41c6d0d4639d02e3db9287a27c6f4c94 |
| _base/engine/options_dislocation.py (absence record) | 1364858165bfa298a5b57ba42a67f0ffebf2faefb873ed42a7a2cea499ed6ca9 |
| _base/engine/intraday_greeks.py (incumbent baseline) | 3592b1981bbe851a2d55cc1b711eb1eede7f21697918a290ba0a5950d03a6f90 |
| _base/engine/options_focused_quote.py (W0b quote probe, nothing retained) | 5848368c82d19d49da425576611d5d3eb11e8023500b3217c0013a07b054aa15 |
| pre-freeze schema census _fabric/Q12-scratch/scan_quotes.json | 9835ccf8150beb63396dbed59d0a69ec036b2833b4a0a62b9c705ef3cc0aa32e |

Disclosure: before this freeze, the author read data SCHEMAS (column names and types) and
the incumbent code only. The pre-freeze census walked 25,246 parquet schemas and 39,175
json/jsonl/csv heads for bid/ask keys and found no file carrying two-sided option quotes.
No outcome (no forward, interval, coverage or comparison value) was computed before freeze.

## 4. Eligibility rule E (decides whether the empirical comparison can run)

A store is eligible only if, per row or per leg, it carries ALL of: option right; strike;
expiry; quote timestamp; bid AND ask for the option (two-sided quote, not trade prints and not
bid/ask-SIDE flow premia); deliverable or multiplier identity; settlement or exercise style
(or an exchange/root mapping that determines them unambiguously); plus a dated discount basis.
Vendor IVs, greeks, OI, trade-print averages and aggregates do not satisfy E: inverting a
vendor IV with an unknown r/q to a price would manufacture the very precision under test.

## 5. Hypotheses (evaluated only if E is met)

* H1 (consistency): on eligible European snapshots with ≥3 qualified pairs, the fraction of
  snapshots whose pair intervals are mutually compatible is ≥ 0.80.
* H2 (comparison, the single dependence-aware test): leave-one-strike-out. For each eligible
  snapshot, estimate from all pairs but one and score against the held-out pair interval.
  Q12 "miss" = intersection disjoint from the held-out interval (or Q12 incompatible/
  unavailable, counted as a miss). Baseline "miss" = incumbent point outside the held-out
  interval. Q12 must be non-inferior on miss rate (difference ≤ +0.02) AND its median
  intersection width must be ≤ the median single-pair width (informativeness).
* H3 (falsifier guard): under injected crossed/stale/asynchronous quotes, Q12 never returns a
  narrower consistent interval than it returns on the clean snapshot.

## 6. Baselines

* B1 incumbent `engine/intraday_greeks.parity_spot` (mid-based point: nearest expiry, tightest
  |C - P| strike, fixed r = 0.043, q = 0; no bands, no identity, no consistency check),
  converted to a forward point as parity_spot / D with r chosen so e^{-rT} = D.
* B2 incumbent price-space parity in `engine/options_dislocation.py`: recorded
  "structurally_absent" (no option price column in the chain store). Its absence is
  reproduced by schema read.
* Baseline reproduction is run on synthetic controls (witness pair, crossed leg, stale leg,
  incompatible strikes) and logged in RUNS.log whether or not E is met.

## 7. Effect bar, trial family, windows, split

* Effect bar: H2 non-inferiority margin 0.02 on miss rate, upper 95% CI bound ≤ 0.02;
  informativeness ratio (median Q12 width / median pair width) ≤ 1.0.
* Trial family: exactly one primary comparison (H2) with the fixed parameters above
  (max_async 1 s, max_quote_age 5 s, D band ±5 bp, min_pairs 3). No parameter search.
  H1 and H3 are reported, not traded off.
* Windows: all eligible snapshots, sampled at most once per 5 minutes per family.
* Chronological split: first 60% of trading days = development (parameters already frozen,
  used for diagnostics only); last 40% = evaluation; verdict reads evaluation only.

## 8. Dependence-aware uncertainty

Moving-block bootstrap over trading days (block = 5 days, 2,000 resamples, fixed seed 12012).
Snapshots within one day are dependent; strikes within one snapshot are dependent. Inference
is never per-strike or per-snapshot i.i.d.

## 9. Falsifier and stop rule

* Falsifier: if qualified pairs cannot identify a stable forward within quote/carry
  uncertainty (H1 fails, or H2 fails non-inferiority), the method returns bounds or
  unavailable and the verdict is REJECT for point use.
* Stop rule: if eligibility rule E finds no eligible store, stop. The verdict is
  INSUFFICIENT_DATA naming the exact missing input; no proxy (vendor IV inversion, trade
  prints, aggregates) is substituted. If E finds a candidate store, evaluation stops after the
  census and a PREREG_AMENDMENT.md must fix the column mapping before any outcome is read.
* Descriptive diagnostic D1 (never a verdict input): in data/flow_signals/ledger.parquet
  (one-sided trade-print events, no bid/ask levels), count call/put events sharing
  (session_date, root, exp, strike) and report the distribution of their timestamp gaps, to
  document asynchrony of the closest retained store.

## 10. Non-duplication (incumbent refresh + collision grep of _base)

Collision grep of `_base` for `put.call parity|implied_forward|parity_forward` hit
`engine/signal_frontier_docket.py`, `engine/intraday_greeks.py`, `engine/options_ivspread.py`,
`engine/options_dislocation.py` and research docs (`OPTIONS_ALPHA_MASTERPLAN.md`,
`options_intelligence/2026-10-03/*`). No `_base/engine` or `_base/tests` file is named like
`*parity_forward*` or `*forward_interval*`.

* `intraday_greeks.parity_spot`: a mid-based **point spot** for greek grids. Q12 is a
  band-based **forward interval** with pair identity, quote-quality rejection, compatibility
  diagnostics and American refusal. Q12 does not replace or edit it.
* `options_ivspread` (Cremers-Weinbaum IV spread): an IV-space return predictor. Q12 forms no
  predictor and no IV.
* `options_dislocation`: records price-space parity as `structurally_absent`. Q12 agrees and
  uses that record as baseline B2's absence proof.
* `options_skew`, `greeks`: not touched; no second writer against options_skew/greeks.
* `options_focused_quote` (W0b): fail-closed vendor snapshot probe, not NBBO; no retained output.
* EXCLUSIONS: relative options pricing maps #8577/#8578 (Q01/Q12/Q13 are distinct derived
  measurements); options matrix #7861/#7293/#7327 (no session repair, snapshot retention or
  expiry projection here). Q01 may consume this forward later; Q02 owns American adjustment;
  Q13 follows. None of those is read or duplicated.
* DNR respected: DNR:KILL-FUSED-COMPOSITE, DNR:KILL-POSITIONING-FUSION,
  DNR:KILL-LLM-ORIGINATION, DNR:KILL-OUTCOME-AUDITION — no composite, no fusion, no language
  model originates anything, no outcome audition.
