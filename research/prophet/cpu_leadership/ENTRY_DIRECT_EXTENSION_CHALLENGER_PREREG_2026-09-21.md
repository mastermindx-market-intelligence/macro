# CPU leadership recovery — direct extension challenger preregistration

Status: PRE-OUTCOME / ZERO PRODUCTION AUTHORITY
Carrier: macro PR #7572
Parent result: ENTRY_RS_THRESHOLD_FINDINGS_2026-09-21.md

## Why this stage exists

The frozen RS-threshold study found no measured protective advantage for the incumbent .75 clean-entry
cutoff and evidence of a materially hotter zone at >=.85. But the September-18 motivating themes also
show why simply replacing .75 with .85 is insufficient:

- AI Semiconductors RS=.845 and median-member close-ATR extension=1.77 (extended);
- Memory/HBM/Storage RS=.845 and extension=1.83 (extended);
- AI Infrastructure RS=.833 and extension=.87 (normal).

Mastermind already owns the separate display-only direct-extension geometry in
`engine/theme_extension.py`; this stage tests that existing chase-risk concept without inventing
another score or tuning on those examples.
## Frozen geometry

Historical substrate: the same committed/store-backed ~27-year US SPDR sector panel + SPY used by
the parent study.

Direct extension uses the incumbent `theme_extension` formula on each sector ETF level:

`ATR_EXT = (close - SMA50) / WilderEMA14(|Δclose|)`

with the incumbent band boundary:

`BAND_EXTENDED = 1.5 ATR`

No threshold search. The 3.0 stretched and 5.0 parabolic bands are not alternative optimization
candidates in this study.

Important ceiling: the long-history proxy applies this formula to the sector ETF level. The live
Theme Extension surface headlines the median constituent extension. Therefore this study can validate
the direct-own-price concept and 1.5 boundary only as a shadow challenger; it cannot by itself promote
the exact live median-member metric to gate authority.
## Frozen population and cohorts

Reuse the parent study's **otherwise-clean** construction, preserving acceleration, RSI room,
breadth, 200d trend, shallow-pullback and breaking-tape conditions.

Restrict the primary population to `rs_pctile < .85`.

Primary cohorts, counted as distinct contiguous episode onsets:

1. `rs085_atr_normal`: otherwise-clean, RS<.85, ATR_EXT<1.5.
2. `rs085_atr_extended`: otherwise-clean, RS<.85, ATR_EXT>=1.5.

Also report descriptive coverage inside the recovered middle band:
- `.75<=RS<.85 and ATR_EXT<1.5`;
- `.75<=RS<.85 and ATR_EXT>=1.5`.

Those middle-band coverage rows are not a second threshold search.
## Frozen outcomes

At episode onset report:
- episode count, sectors and decade coverage;
- 5d / 10d / 21d absolute return;
- 5d / 10d / 21d relative return versus SPY;
- forward 21d maximum adverse excursion;
- probability of 21d drawdown worse than -8%;
- continuation-failure rate (21d relative return <=0).

Primary inference compares `rs085_atr_extended - rs085_atr_normal`.
Collapse to one mean observation per cohort/calendar month, pair only overlapping months, then report:
- overlapping-month count;
- mean and median difference;
- Newey-West mean/t/p with 3 monthly lags;
- moving-block bootstrap 95% CI for the mean difference, 3-month blocks, 5,000 draws,
  deterministic seed 20260921.
## Frozen interpretation

Direct extension adds useful anti-chase protection if the ATR-extended cohort shows materially worse
adverse excursion / >8% drawdown risk and/or materially higher continuation failure than ATR-normal
under dependence-aware inference.

If direct extension does not separate risk or continuation, do not promote it merely because the
September-18 Semis/Memory examples look extended.

A successful result advances only this **shadow policy hypothesis**:

`otherwise-clean AND RS<.85 AND direct-extension<1.5`

versus the incumbent `otherwise-clean AND RS<.75`.

No result here changes production clean-entry, recommendation, Prophet rank, availability, sizing,
or trade authority. Any eventual promotion still requires exact live-theme geometry, independent
review and prospective shadow evidence.
## Guardrails

- No CPU/semiconductor/ticker whitelist.
- No current or premarket prices in historical features.
- No third RS threshold and no alternative ATR threshold after outcomes.
- Episode onset is the inferential unit; no daily-row pseudo-N.
- Missing RS/extension/price remains unavailable.
- The current September-18 examples are acceptance exemplars only.
- Existing leadership detection and entry permission remain separate.
- No new store, ledger, ranker, queue, retry, publication or authority plane.
