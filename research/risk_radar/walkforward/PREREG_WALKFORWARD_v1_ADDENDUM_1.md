# Addendum 1 to PREREG_WALKFORWARD_v1 — 2026-11-12

Kept in a separate file so the frozen prereg's pinned SHA-256 (01e66c59…ca7e7ca) stays verifiable.
**No frozen item changes.** The fitted quantities, fold design, fit objective (§3) and primary
endpoint (§4, the pivot read at ≥5%, post window 10) are unchanged.

Chairman's objective (2026-11-12): an insurer's profile — higher risk-adjusted return and smaller
drawdowns through regime awareness, not raw S&P 500 outperformance. Added as **declared secondary
reads** (they choose nothing):

1. **Insurer profile** (`engine/risk_radar_eval/insurer.py`) of a paper sleeve: alert at d's close
   means bills on d+1, otherwise SPY total return. Reported per series:
   - maximum drawdown;
   - longest time under water and share of sessions under water;
   - share of SPY's ≥10/≥7/≥5% drawdowns avoided (median and pooled);
   - share of gains kept outside declines and in rebounds;
   - Sharpe and Sortino in excess of bills;
   - CAGR, last.
   This **replaces excess return as the headline** of the secondary column. The return
   attribution in `scorecard.py` stays only as "retrospective arithmetic attribution".
2. **Comparators for that column:**
   - SPY;
   - RSP;
   - SPY + bills at a constant weight matching the sleeve's realized volatility (descriptive:
     the weight uses the full window);
   - fixed 60/40 SPY/IEF rebalanced daily;
   - SPY-or-bills on the 200-session rule.
3. **Read order.** Reports show recall on ≥10% turns, then ≥7%, then the ≥5% primary, each with
   false alarms and gains forgone beside it. Missing a large decline is the costlier error. This
   is presentation order only; the primary endpoint stays the ≥5% pivot read.

---
**Note 2026-11-12 (Chairman correction, via principal):** "we're not doing portfolio management… The
point is pivot identification". Items 1–2 above are demoted to a **descriptive appendix**: never a
bar, a headline or a comparator anything is judged against. Item 3's ≥10/≥7/≥5% order now applies
to the pivot read only. SPY < 200d stays as an identification baseline (when it calls each turn and
how late), as already listed in prereg §4. No frozen item changes; the primary endpoint was and
remains the pivot read.
