# US Prophet track-record forensics: frozen-price replay

## Status and decision boundary

Research checkpoint under the Chairman's continuing historical-track-record investigation. Parent remains PARTIAL. No production change, trade authority, accepted replacement strategy, certified-forward performance claim, or completed funded-portfolio backtest.

HOLD-FOR-SOL: this records-only candidate is not strategy acceptance. Release requires exact research-evidence review and canonical Agent OS validation. Do not arm merge-on-green, auto-merge, or widen into production changes from this document.

## Frozen evidence

- Exact screenshot ledger, board snapshots and price generation: macro `cf28b6bcb8e77b7143ab618e5780f90221b25001`.
- Current implementation/record base: `27ec910d04fc81692cf9640347ac31fd3de40170`.
- Protected Mastermind procedure revalidated at unchanged `4537f066775c73d305f82acf0643701f01f5e53c`, skillpack 1.0.1 / bootstrap 1; retained same-pin COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT.
- Snapshot path `data/us_board_ledger/snapshots.jsonl`, SHA256 `0b58bb38d292ec34737d2886134b1d32177493912171e35889ee4931c0b5fed4`.
- Research protocol SHA256 `9da112e1879f9db58662c405246ed608d2048d45aa681f00b659db71690657be`, frozen before population outcomes.
- Source prices: exact-commit `data/baskets/ohlcv/<TICKER>.parquet`, read through Git objects with `GIT_NO_LAZY_FETCH=1` and `GIT_OPTIONAL_LOCKS=0`; occupied working files were not advanced or edited.

Existing local evidence carrier on Mac-Studio:
`/Volumes/Mastermind/Mastermind/research/us-prophet-track-audit-20260916/phase3/`.
Full local archive: sibling `US_Prophet_Phase3_Research_20260916.zip`, 1399999 bytes, SHA256 `287a923df1d0bcc875b4c01cb074acc31afa4ab26626dbe37ce86062b9d147ce`.

Core receipts:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| paired_policy_summary.json | 6141 | bcaa10b1525fdcd07a88c4a991e78f3cc63880b5224c57af27fccdbcad1d1f99 |
| paired_policy_rows.json | 927088 | 993ffef5697782dec74ac317aa76feb85c58c74f37d314b4bf41cffad4fb3718 |
| frozen_price_slice.parquet | 1262331 | 351387d5326b9c08235b84d401e89fc4d3579f9b304f79e71e86523185fa82cd |
| entry_geometry_diagnostics.json | 167509 | 89ca6fcdfacbf3461166713d3b2d0703c0f49db457cfb4bed99b80f28248de4d |

The archive contains tested research functions, all reconciliation rows, individual paired outcomes, source manifests, entry reach diagnostics, and an explicitly UNTESTED capital function. It is evidence, not another runtime, price or identity authority.

## Coverage and method

All 843 mature screenshot episodes matched checked original admission rank, spot, stop, chase ceiling, entry status and stage against 38 frozen boards: zero disagreements. This is a same-generation join check, NOT proof of publication before the decision. The known August 14 reconstruction remains distinguishable; other records are not automatically certified-forward.

The 843 episodes comprise 642 tickers. The selected OHLC family contains 503 of those tickers and covers 659 episodes. Only 413 episodes, 324 tickers and 29 admission dates passed strict price/basis reconciliation. Another 246 failed a quote-basis or return check; 184 lacked this OHLC family. Do not call those 184 globally unpriceable or classify all 246 as dividends without evidence.

Primary rules required exact signal/entry bars, positive complete OHLC, valid OHLC geometry, and a source exit after the recorded number of observed sessions. Signal spot, entry and exit had to agree with recorded prices within max($0.011, 1bp of price); reconstructed return had to agree with published one-decimal P&L within 0.055 percentage point. No rescaling, splicing, missing-open invention or performance-selected source fallback entered the primary arm.

The primary cohort is 49.0% of the original sample and is not asserted representative. Its reference mean is not the full screenshot headline.

The protective overlay uses the original `entry_stop` only AFTER the close-fill bar. On a later bar: open at/below stop means modeled exit at OPEN; otherwise low at/below stop means modeled exit at STOP; otherwise keep the incumbent exit. Six missing/invalid/above-entry stops were flagged and left unchanged. No fitted threshold, trailing rule or optimized profit target was introduced.

Costs are sensitivities at 0/5/10bps per side, not measured security-specific costs. Daily bars do not prove queue priority, liquidity, spreads, halts or actual fills. Incumbent close-based exit conventions remain unchanged: this isolates protection rather than certifying an entire execution policy.

## Main result: tail protection, not rescued selection

| Metric | Reference | Original-stop overlay |
|---|---:|---:|
| Episodes | 413 | 413 |
| Win rate | 45.0363% | 41.6465% |
| Mean gross return | -0.511903% | -0.309956% |
| Median gross return | -0.671392% | -1.013940% |
| Mean net, 5bps/side | -0.611342% | -0.409596% |
| Profit factor | 0.841246 | 0.893251 |
| Losses at least 10% | 44 | 30 |
| Winners at least 10% | 25 | 25 |
| Worst outcome | -27.7233% | -24.1422% |

110 stops triggered; 16 filled at the gap-open assumption. Fourteen eventual reference winners stopped out. The SAME 25 large-winner identities survived. Mean improvement was +0.201948 percentage point, but both methods remained negative.

Time slices remain important. Through August 7, 206 paired episodes averaged +2.095800% versus +2.171816%. From August 12, 207 averaged -3.107009% versus -2.779739%. The 137 V3 episodes averaged -2.506563% versus -2.040962%. No pristine holdout or statistical-significance claim is made.

## Most mean improvement is one issuer

PCG contributes 75.2519% of the net paired-improvement numerator. Without PCG, 409 episodes improve by only +0.050467pp. Without PCG/EIX, 408 improve by +0.044817pp; both means remain negative. Tail protection persists outside those issuers (40 large losses become 29), but the small residual mean effect does not establish a robust edge.

Repeated issuer appearances and shared event exposure must not count as independent confirmation. The one-issuer funded-portfolio test was PLATFORM-BLOCKED before tests or results returned. Its function exists but is UNTESTED. Never infer portfolio returns from summed episode percentages.

## Case evidence

| Admission | Reference | Overlay | Interpretation |
|---|---:|---:|---|
| PCG August 24 | -27.7233% | -7.4074% | $17 reached intraday August 28, before the next-session gap |
| PCG August 18 | -24.8159% | -3.6827% | Same stop, different reference entry |
| EIX August 18 | -26.4978% | -24.1422% | Gap through $67.23; an ideal fill at the stop would be false |
| ONTO August 14 | -23.9065% | -23.9065% | $218.30 stop never reached; approximately 37.8% below entry |
| MRNA August 7 | +132.2187% | +132.2187% | $53.86 stop never reached after entry |
| TEM August 12 | +26.5979% | +26.5979% | $41.55 entry stop never reached |

TEM's entry stop $41.55 is NOT the separate hold invalidation $40.30. Field identity is part of the trade-policy contract.

MRNA frozen closes $59.81 on August 10 and $138.89 on August 24 reproduce +132.22%. Yahoo's public historical display corroborates those prices and the daily path, but may share the underlying vendor; it is not independent-feed or publication-time certification. Never backdate the later clinical result into the August 7 candidate features.

## Entry-band reachability changes the interpretation

MRNA's original zone was $56.01-$58.80, chase ceiling $59.17. August 10 opened at $59.75, reached a low around $58.41 and closed at $59.81. A close-only rejection would discard it, although a predeclared $58.80 upper-limit order was reached by the daily range and the same day's low stayed above its stop. This is reachability, NOT guaranteed execution.

Across 402 known primary-cohort bands, 288 closed above the upper band; 95 had nevertheless touched the limit during the session, including six double-digit reference winners. Ten reachable-limit cases also crossed their stop in the same bar and need explicit ordering treatment. No alternate-entry P&L is claimed.

The known-chase/close-within subset (224 episodes) remained negative: -0.814206% reference versus -0.693728% overlay. A blanket close-price filter is not a demonstrated recovery.

## Verification, failures and continuation

Seven synthetic protective-stop/cost checks passed. Seven actual-replay invariants passed: all 843 accounted for, 413 primary pairs, no policy exit after reference, no stop before/at close-fill, reference rounded-P&L agreement, identical 25 large-winner identities, invalid-stop cases unchanged. These are research checks, not production-suite results or independent review.

The compound additional-source/composition inspection and capital-tests/replay call were platform-refused; no results are claimed. Do not route these denied actions through another actor/tool. Own analysis process 89745 exited with code 0. No background worker, watcher, Job or Attempt is running for this work.

Exact next action: use the saved slice and reconciliation exceptions to resolve raw/adjusted quote and risk geometry through existing price owners; obtain allowed opening-price coverage for the other episodes. Then complete actual limit-entry/stop ordering and the frozen 20-slot, no-leverage, one-position-per-issuer capital comparison through a permitted execution path. Only afterward assess matched-universe selection challengers in the existing Conditional Fusion/shadow mechanism.

Preserve the intended journey: discovery -> explicit current permission/interval/expiry -> feasible fill and same-basis risk -> issuer/event-aware position -> outcome under the same policy. Rejected/unfilled candidates remain measurable. Null evidence stays unknown. No duplicate grader, ranker, price/event store or control plane.

Do not redo headline joins, phase-two score comparisons, the frozen retrieval, primary paired replay or entry-reach scan. Do not promote this overlay, hard sector exclusions or optimized stop widths from these examples. Independent review and real source-to-UI-to-outcome proof remain required for production acceptance.

External corroboration: Yahoo MRNA history https://uk.finance.yahoo.com/quote/MRNA/history/ ; execution-risk qualification: FINRA https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets . Neither source proves our modeled fills.
