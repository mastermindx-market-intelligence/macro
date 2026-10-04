# Defense Intelligence — first-cohort economic exposure map

Date: 2026-09-19. Parent: `WS:DEFENSE-PROCUREMENT-V3`. Principal: Sol.

This is a source-backed research bridge for the first LMT/RTX/NOC/LHX Defense Intelligence
cohort. It is **not** a D5 human-admitted program map, a valuation conclusion, a current trade
recommendation, or a replacement financial truth store. Percentages below are transparent
calculations from the cited issuer/SEC figures and must retain their named denominators.

## Investor question

When missiles, interceptors, air-defense systems, replenishment and propulsion demand strengthen,
which listed company is actually converting the theme into incremental revenue, operating profit and
cash — and which company merely has thematic association, development exposure, or future optionality?

The answer requires at least four different measurements:

1. **company sensitivity** — how material the relevant business is to consolidated economics;
2. **incremental capture** — how much current company growth is actually explained by the theme;
3. **profit conversion** — whether higher volume improves or damages operating profit/margin;
4. **recognition** — whether the improvement is already reflected in guidance, backlog, bookings and price.

A program or contract relationship alone establishes none of those four.

## Q2 2026 observed economic bridge

| Issuer | Relevant disclosed business | Q2 sales / total sales | Theme evidence in Q2 | Profit evidence | Research implication |
|---|---|---:|---|---|---|
| **LMT** | Missiles and Fire Control (MFC) | $4.101B / $20.063B = **20.4%** | MFC sales +$668M YoY; $560M from PAC-3/THAAD ramps and $100M from PrSM ramps | MFC operating profit $594M, +24%; margin 14.5% vs 14.0% | Current missile/air-defense production is already a material, profitable growth driver. The open question is remaining expectation gap, not whether the theme reaches earnings. |
| **RTX** | Raytheon segment | $8.269B / $24.708B = **33.5%** | Raytheon organic sales growth included about $0.5B land/air defense (Patriot), $0.4B naval power (Standard Missile), and $0.2B air/space defense (AMRAAM) | Raytheon operating profit $1.042B, +29%; margin 12.6% vs 11.5% | The defense/missile transmission is large and broad, but RTX is still a diversified aerospace company; commercial and propulsion economics must remain separate. |
| **NOC** | Defense Systems is the nearest disclosed segment proxy, not a pure missile segment | $2.093B / $10.876B = **19.2%** | Sales +5%, with Sentinel/IBCS ramps and continued tactical-missile investment; company describes SiAW/AARGM-ER as future multi-billion-dollar opportunities | Defense Systems operating income $156M, **-38%**; margin 7.5% vs 12.7%, including a $68M unfavorable SiAW EAC adjustment | Current demand and backlog do not equal current profit capture. NOC has meaningful future missile/propulsion optionality, but near-term qualification/execution costs are a first-order variable. |
| **LHX** | Missile Solutions | $1.054B / $5.881B = **17.9%** | Missile Solutions revenue +14%; Propulsion Systems +$85M and Advanced Effects +$44M from higher volumes/ramps | Missile Solutions operating profit $130M vs $116M; margin 12.3% vs 12.5% | The segment is a clear propulsion/munitions expression but remains a minority of consolidated economics; supplier capacity, allocation and contract pricing matter as much as end-demand growth. |

### Incremental growth attribution

The same issuer disclosures allow a more discriminating comparison than static segment share.

**LMT.** Total sales increased by about $1.908B year over year. MFC contributed $668M of that
increase, about **35.0%** of consolidated sales growth. PAC-3/THAAD plus PrSM volume contributed
about $660M, approximately **34.6%** of consolidated sales growth and almost all of MFC's disclosed
sales increase. This is direct evidence that current missile/air-defense ramps are moving
consolidated results.

**RTX.** Total net sales increased by about $3.127B. Raytheon contributed $1.268B, about **40.6%**
of consolidated sales growth. The three explicitly quantified Raytheon drivers — Patriot/land-air
defense (~$0.5B), Standard Missile/naval power (~$0.4B), and AMRAAM/air-space defense (~$0.2B) —
sum to roughly $1.1B, approximately **35.2%** of total company sales growth and **86.8%** of
Raytheon's segment sales increase. These figures are driver attributions, not program revenue
shares.

**NOC.** Defense Systems contributed $102M of a roughly $525M company sales increase, about **19.4%**.
But the segment's operating income fell $97M while sales rose. This is exactly the adverse case a
procurement-only signal misses: stronger strategic demand can coexist with lower current economics
when qualification, EAC and production-maturity costs rise.

**LHX.** Missile Solutions contributed $129M of roughly $455M consolidated sales growth, about
**28.4%**. Its operating-income increase was only $14M of the company's roughly $83M consolidated
operating-income increase, about **16.9%**, while segment margin declined 20 bps. Communications &
Spectrum Dominance contributed much more absolute operating income ($522M in Q2) than Missile
Solutions ($130M). This prevents a missile headline from being treated as the whole-company earnings
story.

## Backlog and demand context

### RTX

At June 30, RTX reported $289B total backlog: $170B commercial and $119B defense. Raytheon alone
reported $86B of backlog and about $20B of Q2 defense bookings. Disclosed bookings included Patriot
GEM-T, AMRAAM, AIM-9X, ESSM, LTAMDS, NASAMS, StormBreaker and SM-3.

This is a strong evidence set for **future defense activity**, but backlog is not current-period profit
and company-wide RTX remains nearly half commercial by Q2 sales customer mix.

### NOC

Northrop reported $104.692B total backlog at June 30, including $34.678B in Defense Systems.
Defense Systems backlog increased 25% from year-end. Funded backlog was $9.392B and unfunded backlog
$25.286B in that segment.

The distinction is important: future opportunity is large, but current margin evidence says the
tactical-missile maturation path can consume profit before production scales.

### LHX

L3Harris reported $42B of record company backlog and 1.2x Q2 book-to-bill. Missile Solutions
guidance was about $4.1B of 2026 revenue. The segment's Q2 revenue growth was driven by Propulsion
Systems and Advanced Effects, but the observed Q2 margin did not expand.

### LMT

Lockheed's MFC Q2 outlook and results already embed material PAC-3, THAAD and PrSM production ramps.
The July outlook showed 2026 MFC sales around $16.5B-$16.9B and operating profit around
$2.30B-$2.35B. A later contract headline therefore cannot automatically be treated as an
unanticipated earnings reset; the expectations layer must ask what was incremental to that outlook.

## Exposure architecture for the product

The product should not emit one `missile_exposure_score`. For each issuer/theme relationship,
retain these independent fields:

- relationship stage: development / qualification / production / sustainment;
- role: prime / subsystem / propulsion / sensor / integrator / supplier;
- disclosed relevant segment and segment share of consolidated revenue;
- segment operating margin and current direction;
- explicitly attributed current-period revenue/profit change;
- funded backlog versus unfunded/framework/ceiling amount;
- capacity expansion and second-source qualification state;
- capital expenditure / working-capital / EAC or execution burden where disclosed;
- management guidance already reflecting the demand;
- market-recognition state from the existing price/theme owner.

An unknown program revenue share remains unknown. Segment share is a **denominator/context**, not a
claim that the whole segment is the named theme.

## First-cohort research interpretation

The four names currently represent different economic expressions of the same broad defense demand:

- **LMT:** direct production-ramp conversion is already visible in MFC sales and profit.
- **RTX:** the largest disclosed relevant segment share in this cohort and broad missile/air-defense
  bookings, but diluted by substantial commercial aerospace exposure.
- **NOC:** strategically meaningful missile/rocket-motor and modernization optionality with current
  evidence that qualification/execution costs can work against near-term margins.
- **LHX:** comparatively focused missile/propulsion segment and supplier leverage, but that segment is
  a minority of consolidated profit and its economics depend on capacity/allocation/contract terms.

These are structural descriptors, not an investment ranking. The asymmetric opportunity depends on
**what changes next relative to expectations and price**.

## Sources

Primary / issuer or SEC sources read 2026-09-19:

1. Lockheed Martin Q2 2026 results:
   https://investors.lockheedmartin.com/news-releases/news-release-details/lockheed-martin-reports-second-quarter-2026-financial-results
2. Lockheed Martin Q2 2026 Form 10-Q:
   https://www.sec.gov/Archives/edgar/data/936468/000162828026049411/lmt-20260628.htm
3. RTX Q2 2026 Form 10-Q:
   https://www.sec.gov/Archives/edgar/data/101829/000010182926000027/rtx-20260630.htm
4. RTX Q2 2026 results:
   https://www.rtx.com/news/news-center/2026/07/23/rtx-reports-q2-2026-results
5. Northrop Grumman Q2 2026 results:
   https://www.sec.gov/Archives/edgar/data/1133421/000113342126000033/noc-06302026xearningsrelea.htm
6. L3Harris Q2 2026 results / 10-Q:
   https://investors.l3harris.com/news/news-details/2026/L3Harris-Technologies-Reports-Robust-Second-Quarter-2026-Results/default.aspx
   https://www.sec.gov/Archives/edgar/data/202058/000020205826000058/hrs-20260703.htm

Dates above are source publication/event dates. This September 19 reconstruction does not by itself
prove Mastermind had these exact bytes at those historical dates. Point-in-time model training must
use retained first-seen/version receipts.
