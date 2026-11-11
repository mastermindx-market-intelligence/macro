# Rotation Core — protocol header v2 (DRAFT, NOT FROZEN)

> **Power warning.** **H2 cannot detect a 2 pp/yr effect.** It is H-only (about 1,722 sessions). Its minimum detectable effect at 80 % power under Holm m = 2 is about **9.3 pp/yr**.
>
> H1's pooled L+H minimum detectable effect is about **1.4 pp/yr**, below 2 pp/yr. That projection assumes the long sample's per-session contrast variance equals D's. The 1929–1940s were more volatile, so treat 1.4 as optimistic.

**Status:** draft. The parent freezes it after folding in three inputs:
- the Sector Intelligence yardstick and shortlist;
- their Kimi review of v1;
- Pro run A.

No v2 outcome may be computed before the freeze commit. The `rotation_core_v2` trial-ledger declaration is written at freeze. Where this Markdown and `protocol_header_v2.DRAFT.json` differ, the JSON governs.

**Predecessor:** v1 (`af2a0988…`) closed at L0 by parent ruling 2026-11-11 09:50Z; its Stage H was never run.

## Question

When conditions turn bad, does rotating out of broad equity leadership into the defensive sectors (staples, utilities, health care) add timing skill over holding the same legs in a static mix? Cash is an option, not the default.

## Hypotheses (one Holm family, m = 2)

| Id | Rule (one, no variants) | Primary contrast | Confirmation samples |
|---|---|---|---|
| **H1** | ^GSPC < 200-day SMA → equal-weight defensive leg (XLP/XLU/XLV; on L: NoDur/Utils/Hlth). Otherwise → equal-weight all eligible sectors (on L: all 12 French industries). Always fully invested; month-end rebalance within the leg. | H1 minus an exposure-matched static mix of the two legs (weight = H1's share of sessions in the risk-on leg, rebuilt per window) | **L + H pooled** |
| **H2** | v1 J1-E unchanged: SPY → cash only when T and real-time Sahm ≥ 0.50 agree | H2 minus a static SPY/cash mix at H2's mean weight | **H only** |
| (third) | **Not included.** J3-C's primary contrast was weak on D (+3.3 %, raw p 0.13); its only strong number was the secondary contrast versus GTAA. It has no long sample, and adding it would raise Holm m to 3 for an H-only minimum detectable effect of about 11 pp/yr. | — | — |

## Why H1 is built this way (D evidence only)

- **Risk-on leg = equal-weight sectors.**
  - No D sector-selection rule beat equal weight (J2* = B5), and equal weight is the unselected, neutral choice.
  - SPY would add a cap-weight bet the defensive leg doesn't share.
  - A declared "high-beta set" would have to be picked using D outcomes, which is a forking path.
- **Defensive leg = XLP/XLU/XLV.** From peak to trough the trio beat SPY in every D episode, by +9.6 to +31.5 pp.
- **Switch on the risk state, not on sector momentum.** On D the RS rules held cyclicals or tech at the 2000 and 2007 peaks.
- **T rather than crisis-only (J1-E).** J1-E exited before the trough in only 2 of 6 D episodes. It stayed invested through 1998, 2011, 2015–16 and 2018Q4, exactly where the trio still won by 10–13 pp.
- **Why a defensive fallback allows a faster trigger.** With a cash fallback, T's false risk-off calls cost 3.7 %/calm-yr on D. With a defensive fallback, a false call costs only the spread between equal-weight sectors and the trio (beta about 0.6), not the equity premium. That makes a faster trigger affordable, which is the argument for T.
- **T rather than trend-and-credit (J1-B).** Two reasons:
  - J1-B exited on the same dates as T in all six D episodes. Its smaller false-pivot count matters less when false pivots are cheap.
  - Credit data starts only in 1986, which would make H1 H-only.
- **Variants, not confirmatory.** The trend-and-credit and J1-E-trigger variants of H1 are reported on H as descriptive only.

## Samples, and what is clean

- **D (1998–2019):** seen; used for design and context only.
- **L, Ken French `12_Industry_Portfolios_Daily.csv`, value-weighted, returns 1928-10-17 → 1997-12-31 (18,424 sessions):**
  - **Why 12 industries:** the defensive trio maps one-to-one (NoDur, Utils, Hlth), there are no missing cells up to 1997, and it is the closest analogue to 9–11 SPDR sectors. The 30-industry file splits staples into four groups; the 49-industry file has missing early series.
  - **Mechanics:** 10 bp per side, cash = French RF, signal on ^GSPC.
- **What is already computed on L:**
  - **Market level:** the v1 Stage D long tier computed timing against cash on the French *market* return. That covered the 200-day rule (B3), J1-D and B4 for 1928–1997, J1-E for 1960–1997, and the credit rules for 1987–1997.
  - **Industry panels:** **no strategy output of any kind exists on the French industry panels.** J2_L was deferred and never run, no worker computed industry returns, and Macro main has no consumer of these files. Only the raw CSVs exist in scratch.
- **Clean on L:**
  - **H1: partly.** The industry-level contrast is unseen. The trigger T and its market-level timing against cash were seen.
  - **H2: no.** J1-E was run on 1960–1997, and real-time Sahm has no long real-time substitute. H2 is H-only.
- **H (returns 2020-01-02 → 2026-11-06, the v1 pin):** unseen by any Rotation Core statistic. v1's burned-date exclusion applied only to J4 member-persistence formations, so no H dates are excluded for H1 or H2. That is the same treatment as v1's J1–J3.
- **Signal availability across L:**
  - H1 uses only ^GSPC, which is available from 1927.
  - H2's Sahm leg is declared H-only, with no substitute.
  - Credit appears only in a descriptive H-only variant.

## Declared comparators (reported for every book; no test)

- SPY.
- RSP (from 2003-05).
- The risk-on leg alone.
- The defensive leg alone.
- X1 and X2, the static mixes used in the primary contrasts.

For every book: full-period monthly up/down capture, plus stress-episode capture against SPY and RSP, both pooled and per episode. Stress episodes:
- L: 1929–32, 1937, 1962, 1966, 1969–70, 1973–74, 1980–82, 1987, 1990.
- H: 2020, 2022, 2025, and 2026 under its v1 rule.
- All closing drawdowns ≥ 15 % are also listed.

## Decision rule (declared now)

- **H1 primary test.** A sample-stratified stationary bootstrap that resamples L and H separately (block 21, sensitivity 63, B = 10,000), using the session-weighted mean of the two annualised contrasts.
- **Why pooled plus sign.** H alone cannot see less than about 4.7 pp/yr, so a separate H significance test would be a formality. Requiring L > 0 and H > 0 stops either sample from carrying the result alone.
- **H2 test.** The same bootstrap on H only. Holm at 0.05 over {H1, H2}.

| Level | H1 | H2 |
|---|---|---|
| **L1 accepted historical** | All of: Holm p < 0.05 pooled; pooled effect ≥ +1.0 pp/yr; L > 0 and H > 0; still holds at 2× costs; pooled stress capture vs SPY ≤ 0.80; CAGR ≥ risk-on leg − 1.0 pp/yr on both L and H | All of: Holm p < 0.05 on H; effect ≥ +1.0 pp/yr; holds at 2× costs; max drawdown ≤ 0.70 × SPY's; CAGR ≥ SPY − 2.0 pp/yr |
| **L0** | Anything else. A null is reported with its power line as "not detectable". | Same |
| **L2 prospective shadow** | L1, then ≥ 252 forward sessions under the unchanged hash, written nightly with no backfill, containing a ≥ 10 % SPY drawdown, with forward contrast ≥ 0. **Owner: QLedger**, one claim per decision (family, decided_at, exec_at, weights, header sha, commit, X, horizons 21/63, falsifier). Nothing is written to QLedger, Reflex Registry or Chronicle unless L1 is earned. | Same |

## Power (from D-sample contrast variance only)

| | D SE (ann.) | MDE80, Holm m = 2 |
|---|---|---|
| H1 pooled L+H | 0.99 % (TE 5.2 %, 5,031 D sessions) | **1.37 pp** (L only 1.43, H only 4.75) |
| H2 H-only | 1.85 % (v1 J1-E:P1) | **9.28 pp** |

**H1's standard error:** I simulated H1 on D and printed **only** the bootstrap standard error (`/home/ubuntu2/tmp/rotation-core/v2/power_h1_D.py`). Its point estimate was never printed or seen.

**Scaling:** the projections scale the D standard error by √(n_D / n).

## Unchanged from v1, and dropped

**Unchanged:** the same harness, costs (5 bp ETF, 10 bp French industry), t+1 execution, metrics, bootstrap conventions and data pin.

**Trial ledger:** `rotation_core_v2` is declared at freeze (budget 9). The deflated-Sharpe trial count carries v1's 36.

**Dropped:** sector RS velocity, graded MTF, and J4.
