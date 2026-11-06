# ROR-1 — reconcile the accepted September gate-latency study

**Research-only source reconciliation, 2026-10-15.** The new ROR-1 suppression
census and the June tuning-report labeling concern must not obscure a newer
**already corrected and evidence-backed study** in Grey Deer. No model, gate,
probability, capital policy, live deployment or customer notification is changed here.

## Authoritative preexisting study (do not rerun by default)

- Registered protocol: `research/grey_deer/RISK_RADAR_GATE_LATENCY_PREREG_2026-09-21.md`
  (blob `d5d65f64fcfb99a2b0a64e2e6fc48d47e4045fbc`).
- Corrected result: `research/grey_deer/evidence/gate-latency-20260921/result.json`
  (Git blob `1e9761bf3046ce61a1a2694af82fab31ecd4b569`; declared result SHA256
  `927a7784ad1e248079b698ddfe1d452464fe7f422db7b364c8f648a12f9b991b`).
- Accepted verification: `research/grey_deer/evidence/gate-latency-20260921/verification.json`
  (blob `949f86a02d493d6cd00f13f788d35dc7d45c1df6`), status
  `corrected_post_replay_parity`; first pre-parity analysis is superseded by #7632.
- Study target is a **future 5% SPY decline over 21 native closing observations**.
  Source observables stop September 18, 2026; mature outcome windows stop August 19.
  This is **current-code historical reconstruction**, not genuinely issued alerts,
  independent crisis episodes or the unobserved October 14 delivery state.

## True denominators from committed confusion counts

| History / signal | TP | FP | TN | FN | Precision | Recall | Fire rate | FPR = FP/(FP+TN) | FDR = FP/(TP+FP) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full raw (8,195 days) | 985 | 3698 | 3051 | 461 | 21.03% | 68.12% | 57.14% | **54.79%** | 78.97% |
| Full gated (8,195) | 409 | 566 | 6183 | 1037 | 41.95% | 28.28% | 11.90% | **8.39%** | 58.05% |
| 2020+ raw (1,666) | 259 | 797 | 575 | 35 | 24.53% | 88.10% | 63.39% | **58.09%** | 75.47% |
| 2020+ gated (1,666) | 108 | 149 | 1223 | 186 | 42.02% | 36.73% | 15.43% | **10.86%** | 57.98% |

Full sample: gate removed 3,132 false-positive **days** and lost 576 true-positive
**days** (5.44 false-positive days removed for every true-positive day lost).
2020+: 648 removed / 151 lost (4.29). Overlapping 21-session windows are not
independent incidents. The gate buys selectivity at a substantial cost in recall.

## Event-clock latency is the customer-attention argument

- The deterministic event atlas had 110 complete 5% / 21-session event anchors.
- 103/110 (93.6%) showed ungated loud risk by their anchor T0.
- Only 41/110 (37.3%) showed gated loud risk by T0.
- Among 103 raw-pre-T0 events: 41 gated by T0; another 9 after T0 but before
  5% breach; 12 after the breach; **41 never through T+21**.
- Where both readings exist, gate detection lag median 3 sessions, p75 23.
- A missing gated alert is **not proof** that the earlier ungated read had a
  deployable positive predictive value or should have controlled trades.

## Reconciliation with ROR-1

1. **Do not rerun or silently replace the accepted September study.** It already
   supplies the confusion counts missing from the older June prose for its own
   **different** 5%/21d target, model vintage and sample.
2. The June report's 0.915 / 0.751 / 0.901 / 0.741 `fp_rate` entries still
   equal 1 − precision (false-discovery rate), despite a definition of FPR.
   Preserve this historical documentation inconsistency; never substitute
   September's confusion matrix into June's differing event definitions.
3. The independent October 15 ROR-1 first-writer ledger shows 13 consecutive
   *recorded* prospective severe ungated readings clamped to Caution, all
   ungraded. It is distinct from September's reconstructed event study.
4. User-facing work should reuse **qualified source-native observational
   warnings**, Grey Deer's existing warning projection and data-health
   contract, while retaining the model gate for predictive probabilities
   and all trading/capital permissions pending separate promotion.
5. The next valuable test is an **issued-time, source-vintage, entitlement
   and actual delivery** replay, with a separate false-interruption budget.
   Do not create another independent risk authority, copy a stage across
   incompatible market sessions, or claim 2026-10-14 prediction success.

## Research limitations and execution boundary

This note is a readback/derivation from the already committed September
result and verification, not a newly executed market-data backtest or a
current-source parity revalidation. The latest Risk Radar source blob is
`94222d44ec102e728da5443e2082da73ad29f17f`, whereas the September
receipt binds an older source hash. The relevant source/data drift must be
evaluated before applying its numeric skill claims to October.

A separate attempted compound M2 evidence-download/validation command was
platform-refused pre-dispatch on this turn. It created no observed new
evidence files and was not retried or proxied; this document relies on
the previously successful direct GitHub reads of the committed study.

**Release state:** source research only; #8132/#9428 incumbent writers and
holds are unaffected. ROR-1 root: https://github.com/mastermindx-market-intelligence/Mastermind/issues/1478.
