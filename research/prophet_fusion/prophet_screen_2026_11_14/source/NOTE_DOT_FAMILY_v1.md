# Note: which grey dot the trough programme tests (RD, 2026-11-14)

**Why.** The Prophet lead's product census (Terminal c67a68ee, Macro 5c122cae, read-only) shows the Terminal and Macro dots are different families. This note names ours. It changes no test, no threshold and no m.

1. **Family tested: the Terminal twin, locked spec, completed buckets.**
   - Source: `_terminal_dot_mask` in `engine/stock_identity/replay/grey_dot.py` (sha256 0419d7c0…), read-only, already named in PLAN_TROUGH_v1 §1 and TROUGH_BREADTH_DEF_v1.
   - Legs: 3D StochRSI K×D bullish cross; D < 20 within 8 bars; ONE strictly rising 2B RSI-MACD histogram step, PIT-joined; canon RSI (SMA-seeded RMA); no RSI ceiling.
   - It is NOT the Macro replay dot (bare-ewm RSI, rsi14 < 65, two rising steps on the prior closed 2D bar).
   - Label in every output: "Terminal-twin dot, completed buckets".
2. **Known gap to the live chart.** The live Terminal allows a developing edge bucket; ours uses completed buckets only. Our dot can therefore appear up to one bucket later than the live chart shows it (cf. W2_G0_PARITY_RECEIPTS, four materialisations one session late). This is conservative for earliness: any lag measured here is an upper bound on the live lag. HINDSIGHT_GUARD prints the known_ts minus 3D-bar-label lag distribution as description.
3. **Amber (washout-promoted) dots.** On the live chart a dot with washout context leaves the grey set and shows as an amber EARLY / BOTTOM_WATCH mark. Our G3 set keeps both, with `in_washout_context` as a feature (plan §1), unchanged.
   - Description only, not screened, not in m: COUNTS.md prints grey-only vs amber counts per year, and the breadth file carries `dot_share_10_grey` (amber excluded) next to `dot_share_10`. GRP-DOT's event rule stays on `dot_share_10`.
