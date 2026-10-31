# Tech Volatility Shock — Macro Market Internals

**Parent:** WS:MARKET-OS (product context only; this branch does not mutate the incumbent workstream/waves). **Status:** source candidate, not released. **Current user assignment:** integrate the attached SPY/QQQ shock panel into the US Macro Dashboard.

## Outcome and provenance

Users can tell whether tech is experiencing an unusually severe selloff relative to the broader market, how extreme the day is against a causal historical reference, and whether damage came before or after the opening auction. This is an EOD **descriptive** instrument, not a new trade signal, risk classifier, or forecast. It must extend the existing market-state/risk surfaces rather than stack a second regime hero or originate a new shock taxonomy (see `research/UNIFIED_DASHBOARD_DISPOSITION.md` and `research/TECH_INTERNALS_CODEX_ADJUDICATION_BY_FABLE.md`).

**Input:** `data/massive_stock_day/{SPY,QQQ}.parquet` through `lib.store`; qualified unadjusted raw OHLC and whole-market-day volume (not regular-session-only volume). Do NOT combine Yahoo total-return-adjusted close with raw opening prices. Missing R2 restore/volume/history or mismatched dates must display disclosed unavailability; never synthesize values. Display as-of session date and source basis. No new collector, narrative classifier, or dependency on an LLM.

**Math (same paired market date):** net return = C[t]/C[t-1] - 1; overnight = O[t]/C[t-1] - 1; intraday = C[t]/O[t] - 1; `(1+overnight)*(1+intraday)-1 = net`. Relative daily performance is `(QQQ return-SPY return)*100` percentage points (not the QQQ/SPY price ratio return). Each 60-session z-score uses the **prior** 60 return observations (exclude t) with sample standard deviation; no insufficient-sample claims. Relative z-score applies the same causal window to the paired daily difference series. Volume multiple = current full-day aggregate volume divided by the prior 20-session mean, clearly labeled. Yearly worst-day rank counts observed YTD eligible sessions; disclose eligible N. Recency/extreme labels must be derived from observations, not screenshot figures. Missing, nonpositive or nonfinite bars invalidate the affected metric, not a fabricated zero.

**Session caveat:** Massive's daily OHLC rungs are XNYS regular-session prices and the corresponding daily activity counters include broader sessions (DSC-SPY-DAILY-AGG-IS-RTH-PRICE-FULLDAY-ACTIVITY). 'Overnight' means previous regular close to next regular open; it does not separately isolate after-hours versus premarket. Display additive split via rounded legs only with a compounding note. No unverified "1-in-192" probability claim.

## Task tree and acceptance

| ID | Node | Depends | Status | Done when / proof |
|---|---|---|---|---|
| TVS.P1 | Measurement and contracts | — | in_progress | Exact source/basis/date/causal formulas and null coverage tested with synthetic bars |
| TVS.P1.T1 | Pure snapshot calculator | — | ready | Supports aligned SPY/QQQ; basis/no-open guards; 60-session z and paired relative z; YTD ranking and volume baseline; opposite-sign sessions |
| TVS.P1.T2 | Deterministic unit tests | P1.T1 | ready | Formula equality, leaks, mismatch, missing, stale, partial and yearly rank pass |
| TVS.P2 | EOD Macro user experience | P1 | ready | Compact summary after existing regime section with opt-in detailed comparison, responsive 2-up/stacked cards, status/source labels; no duplicate regime verdict |
| TVS.P2.T1 | Renderer partial and safe mount | P1.T1 | ready | Build-site route only (not stocks mode); Jinja escaping; no runtime external requests; dev re-render parity |
| TVS.P3 | Release/quality | P1,P2 | blocked | Exact-head CI + non-author review; production date, source restore, numeric fixture and responsive browser interaction verified; protected merge/deploy through normal owner only |

**Negative acceptance:** no public screenshot numbers hard-coded as current market quotes; no silently adjusted/unadjusted mix; no claim of intraday live data; no standalone "tech shock" trading decision engine; no user-position sizing or signals; no overwriting concurrent Macro source work. Current modified surface restricted to the additive engine, focused tests, a self-contained presentation partial, source-bound build hooks and this plan.

**Next action:** implement P1.T1 and T2 on isolated `sol/tech-volatility-shock-20261030` branch, then wire the compact component to `scripts/build_site.py` and `scripts/render_macro_fast.py`. Publish one reviewable PR. Do not mark production live from CI alone.
