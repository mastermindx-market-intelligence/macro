COMMISSION PRO-RUN V4-W1-2 - Regime and sector exhaustion

COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: research design for a multi-week quantitative programme; a wrong idea here costs weeks of data budget that cannot be recovered.
WHY_NON_PRO_INSUFFICIENT: needs a long, careful synthesis of literature, statistics and our data limits with adversarial self-checking.
PRO_MODE_TASK_CLASS: ADVERSARIAL_JUDGMENT
EXPECTED_DURATION_MINUTES: 60
STOP_CONDITION: one comment posted on GitHub mastermindx-market-intelligence/macro issue #11014 beginning "PRO-RUN V4-W1-2", or the full answer returned in this chat if posting is impossible.

Commissioned by the Prophet programme rotation research desk. Research only, read-only everywhere. Authorized: one comment on macro issue #11014. No pull request, push, edit or file change. Nothing here sizes or recommends a trade.

OUR QUESTION
Mastermind is a market-intelligence product. We want to know which observable combinations of market, sector, technical, macro and positioning factors give statistically defensible information about (a) an upcoming US sector or asset rotation and (b) a risk-on / risk-off pivot: its probability, its timing, its size, and whether acting on it beats SPY, RSP (equal-weight S&P 500) and cash after costs. We do not assume such a signal exists. A useful call needs early evidence of the turn; buying a falling group because it fell ("knife-catching") does not count. Our Chairman's rulings: the modern regime (2020 onward) is the test bed; change in breadth matters more than its level; history may be reconstructed from historical data (strict point-in-time vintages are welcome, not a precondition).

WHAT DATA WE HOLD (daily unless stated)
- 44 liquid ETFs with total-return closes from 1998-2012 starts: 11 SPDR sectors (XLC 2018, XLRE 2015), 16 industry groups (SMH IGV IBB XBI KRE KBE ITB XHB XOP OIH XME XRT ITA IYT TAN GDX), 17 cross-asset sleeves (QQQ IWM MDY EFA EEM EWJ FXI INDA TLT IEF SHY TIP LQD HYG GLD DBC VNQ), plus SPY, RSP, 3-month T-bill.
- S&P 1500 point-in-time membership (S&P 500 from 1996, 400 from 2012, 600 from Dec 2019) with member prices including delisted names (about 96% of measurable member-days priced 2020-2022, leavers about 90%). Members are assigned monthly to the 27 equity ETFs by trailing one-year return correlation (no GICS history exists). So we can build within-group breadth (share above own 200-day average, new highs/lows, etc.) and dispersion from 2020.
- Macro and liquidity: about 35 FRED series (Treasury curve, BAA-10y spread, NFCI, St Louis stress, claims, unemployment, CPI, etc.), ALFRED vintages for revised series; high-yield OAS only from late 2023. VIX, VIX term structure, equity put/call, CBOE skew, CFTC positioning for gold; Fama-French factors; Ken French industry portfolios up to 2019 only (later years sealed).
- Mastermind's own production signals (risk dashboard, cycle phase, production breadth thrust) exist but were all tuned on 2020+ data, so none is out of sample.

WHAT WE ALREADY TRIED, AND WHY IT FAILED
- v1 and v2: a two-key state machine (warn when a leadership group is near its 126-day high while its breadth drops; defend when its relative line crosses below its 50-day average; re-attack after a washout recovers) on 49 Ken French industries, 1928-2019. Offence/defence legs were beta-sorted thirds. No candidate cleared its pre-declared gates against an exposure-matched mix after costs. Lesson: 49 industries are roughly 2-2.5 independent bets; long-history selection did not transfer.
- v3: one pre-declared within-sector breadth test on 2020-2025, with the whole window sealed. Withdrawn before it ran: spending the only modern window on one test leaves nothing to discover with.
- Measured facts (signal against signal only, no returns): relative strength against one benchmark ranks exactly like momentum over the same lookback (rank corr 1.00); every price-only cross-sectional ranking we built is a recombination of return horizons (rank R-squared 0.67-0.91 on plain return windows); within-group breadth level has 4-week rank persistence 0.74 and about 40% of its variance is not explained by six public factors or the group's own price; the 13-week breadth change has persistence about 0.5; in a prior study the post-washout premium came 77% from 2020 alone (ex-COVID about zero); an earlier internal study found defensive-sector excess after SPY down months of -0.54% per month [-1.55, +0.46] on 2013-2025.

OUR DESIGN (for your reference)
Discovery block D = 2020-01-02 to 2023-12-29 (opened later by the principal). Sealed block S = 2024-01-02 onward, read once for at most five frozen candidates. Pre-2020 is used only to check a finding does not reverse, never to select. Every evaluated configuration is logged before its result is read; selection is corrected for that count (deflated Sharpe, probability of backtest overfitting, Holm on the final family). Decide at close t, trade at close t+1; costs 10 bp per one-way turnover (20 bp stress). Labels: forward relative return of each group vs the equal-weight panel at 3, 5, 10, 20, 63 sessions; dated rotation events (leadership changes among groups); dated risk pivots (drawdown and volatility regime turns).

YOUR TOPIC
How can a leading sector's or group's exhaustion be detected early on 2020+ US data, before its relative line breaks? Consider: breadth divergence inside the group (price near high while participation falls), deceleration of relative strength (second derivative across 21/63/126 sessions), dispersion and intra-group correlation, crowding proxies, volume and volatility of the relative line, and the interaction of exhaustion with the market's risk state. Separate what is just momentum crash / short-term reversal from what is new. Each card must say how it avoids knife-catching on the receiving side.

OUTPUT FORMAT (strict)
Return 6 to 10 HYPOTHESIS CARDS, ranked best first, then a short "do not try" list (ideas likely to fail or already tested, with why). Each card, in this exact shape:
CARD <n>: <short title>
- Mechanism: why the effect should exist and persist (2-4 sentences; cite papers by author and year).
- Features: exact formulas with lookbacks, smoothing and publication lags; which of our data each uses.
- Label: one of ours (forward relative return at h sessions; rotation event; risk pivot) and the horizon.
- Expected sign and rough size.
- Refuter: the observation on our data that would kill it.
- Data needed: what we hold vs what is missing.
- Cost to test: number of configurations (grid) and which model class.
- Prior post-2020 evidence: cite, or say none known.
- Closeness to a public factor (momentum, low beta, reversal, trend): high / medium / low.
Do not report any backtest result you did not compute from cited data. No trade sizing, no recommendations to buy or sell; this is research design only.
