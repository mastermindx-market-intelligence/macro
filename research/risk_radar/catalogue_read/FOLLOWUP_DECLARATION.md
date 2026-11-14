# Risk Radar follow-up set (Principal ruling 3, 2026-11-12 10:25Z): declared before any new read

**Selected after seeing D.** The D-block reads (out/, out_r1b/, both superseded scorers) showed
k=2, k=3 and the real-rate-jump leg doing well. This set was picked knowing those numbers.

## The one frozen set: `rr-roff-confluence-k3-followup`
- **Rule.** Equal-vote count of the same 12 legs, each at the engine's own thr_pct (the same table as
  rr-roff-confluence-k4). The alert is ON when 3 or more legs are on. A leg with no value counts as off.
- **Family and direction.** R-off (tops), primary post 5. Major tier, pre 21, min_off 10, one-session
  shift, seed 20261112, 2000 draws, tol 0.01. Desk adapter with `episode_rule="swing"`, sha pinned in the
  ledger row.
- **Why k=3 and not k=2 or the real-rate leg.**
  - k=2 is on about 46% of sessions; that is a background state, not a call.
  - The real-rate-jump leg is one channel. On D its catch rests on the 2022 rate shock, and PRE turns
    (2008, 2011, 2015–16, 2018) are mostly credit and growth shocks, so a single rate leg is the
    likeliest to be regime-specific.
  - k=3 keeps the multi-channel premise of the Radar at an alert share of about 26%.
  - Bottoms are not followed up, because the confluence bottom read was weak at every k.
- **Decisive read: PRE.** All catalogue PRE-block major-tier risk_off turns, starting at
  2006-01-03, the first date with at least 11 of the 12 legs present, through the end of the PRE
  block (2019-12-31).
  - Leg history: vol_term from 2011-12-30 and credit_hyg_tlt from 2008-05-07. Each counts as off
    before its first date; coverage is reported.
  - FRED legs are point-in-time from 2006 on: `availability.pit_signals(sigs, start="2006-01-03")`,
    with ALFRED dates where present and the release rules elsewhere.
- **Nomination rule (Principal ruling 2):**
  - (a) Cluster catch share is above the near-high placebo p90.
  - (b) Cluster catch share is above the budget-matched mechanical reference, with false calls per
    asset-year at or below that reference's. Budget-matched means each asset's drawdown and near-high
    references take the threshold whose ON share equals this set's ON share on the same block.
    The threshold is computed from price levels only. The fixed-threshold references are reported
    beside it.
  - (c) It beats its best single leg at the same or lower false-call rate.
- **After PRE.** The RD's attack seat. No hold-out, because the Radar family touched 2024+. If it
  passes, it is a forward candidate only.

## RD conditions, accepted 2026-11-12 (frozen at 10:22Z)
1. **Scorer and timing.** Same desk adapter: swing episodes, one-session shift, adapter_sha256 in the row.
   The row is written when the R1g sha arrives. PRE is not read until the budget-matched reference
   (BM-REF) sha arrives.
2. **Causal percentiles.** Leg percentiles on PRE are the engine's own trailing 504-session causal
   percentiles (`leading_signals`). Each date uses only data before it. There is no full-sample
   percentile and no threshold fit.
3. **Missing legs.** A missing leg counts as off, so the effective rule is 3 of the legs available on
   that date: 10 before 2008-05-07, 11 until vol_term starts on 2011-12-30, then 12. The alert share by
   year on PRE is reported beside the result, as description.
