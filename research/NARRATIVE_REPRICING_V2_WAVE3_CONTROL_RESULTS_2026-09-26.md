# Narrative Repricing V2 — Wave 3 Control Results

Date: 2026-09-26
State: CONTROL_EVIDENCE / RESEARCH_ONLY / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Wave-3 source manifest: research/NARRATIVE_REPRICING_V2_CLOCK_CLEAN_SOURCE_WAVE3_2026-09-25.json
Wave-3 source manifest blob: 518adde086b64df0dc8de5c2f7aca2cb8a835a7c
Extraction head: f988de16a261bd708c6a2b9f8be321c4f964031d
Mastermind protected procedure pin: 58c842d5ab99e29785ec9b4d16ccee67e85e19c4
Skillpack index blob: 94d1af402598894372858793a5b1931019c5fa77
ACTIVE_EXECUTION blob: 9fed10f7cc7a2f4323d039b406f7c0715445e22e

## 1. Evidence boundary

Wave 3 was source-frozen before these outcomes were read. Its purpose is control coverage:
opposite-direction escalation, weak/unconfirmed rumors, and mixed/conflicted clusters.

The extraction used the existing Massive/Polygon U.S.-stocks minute entitlement with no
minute-data persistence and the same frozen V2 first-pass windows used in Waves 1-2.

For escalation rows:
- positive signed causal movement means USO moved higher as expected;
- negative raw SMH-minus-QQQ residual is directionally consistent with the expected
  semiconductor risk-off response.

For relief rows:
- positive signed causal movement means USO moved lower as expected;
- positive raw SMH-minus-QQQ residual is directionally consistent with the expected
  semiconductor risk-on response.

Mixed rows with no predeclared causal direction are not forced into a directional score.

## 2. Directional rows

| Event | Role | Signed USO 0→+5m | Raw SMH-QQQ +5→+35 | Expected-direction response |
|---|---|---:|---:|---:|
| 2026-07-14 CENTCOM additional strikes | mixed/conflict control | +32.48 bp | -9.93 bp | +9.93 bp |
| 2026-08-14 draft restrict hostile transit | weak rumor escalation | data gap | data gap | data gap |
| 2026-08-25 unconfirmed ceasefire/free navigation | weak rumor relief | **-10.96 bp** | +19.52 bp | +19.52 bp |
| 2026-08-31 Trump weighing limited strikes | weak rumor escalation | **-2.25 bp** | -14.00 bp | +14.00 bp |

Expected-direction response is a descriptive sign transform only:
- escalation: raw residual multiplied by -1;
- relief: raw residual unchanged.

It is not a score or trading signal.

## 3. July 14 — causal confirmation with source contamination

The CENTCOM strike announcement produced:
- pre-60m signed USO: +27.56 bp;
- pre-240m signed USO: +127.37 bp;
- first-five-minute signed USO: +32.48 bp;
- first-impulse raw SMH-QQQ residual: +21.03 bp, initially opposite the expected equity sign;
- +5→+20 raw residual: +3.30 bp;
- +5→+35 raw residual: -9.93 bp;
- +5→+65 raw residual: -5.30 bp.

The eventual 30/60-minute semiconductor direction is consistent with escalation, but the
source manifest already records a competing de-escalatory Iranian deputy-FM headline at
19:40Z, only ten minutes later.

Classification:
CAUSAL_PROXY_CONFIRMED / LATER_RESPONSE_DIRECTIONALLY_CONSISTENT / SOURCE_CONFOUNDED.

This event cannot be used as a clean primary proof of an escalation mechanism.

## 4. August 14 — honest data gap

The 09:07Z weak restriction-rhetoric event had insufficient admitted response observations
for the frozen first-pass window.

Classification:
DATA_GAP.

The clock is not moved to a later liquid interval.

## 5. August 25 — equity move without causal confirmation

The unconfirmed ceasefire/free-navigation report produced:
- pre-60m signed USO: +15.24 bp;
- pre-240m signed USO: +23.04 bp;
- first-five-minute signed USO: **-10.96 bp**, meaning oil moved opposite the expected
  relief direction;
- first-impulse SMH-QQQ residual: -4.70 bp;
- +5→+20 residual: +3.25 bp;
- +5→+35 residual: +19.52 bp.

The later semiconductor outperformance must not be counted as a validated relief event,
because the causal oil proxy did not confirm the narrative.

Classification:
RUMOR / NO_CAUSAL_CONFIRMATION / EQUITY_MOVE_NOT_ATTRIBUTED.

This is exactly the type of false-positive control the proposed product needs.

## 6. August 31 — later equity direction without causal confirmation

The report that Trump was weighing limited strikes produced:
- pre-60m signed USO: -19.49 bp;
- pre-240m signed USO: -2.25 bp;
- first-five-minute signed USO: **-2.25 bp**, effectively no expected escalation confirmation;
- first-impulse raw SMH-QQQ residual: +0.54 bp;
- +5→+20 residual: +5.13 bp;
- +5→+35 residual: -14.00 bp;
- +5→+65 residual: -22.18 bp.

Semiconductors eventually underperformed, but the causal oil proxy did not validate the
headline in the first impulse.

Classification:
RUMOR / NO_CAUSAL_CONFIRMATION / LATER_EQUITY_MOVE_NOT_ATTRIBUTED.

## 7. What Wave 3 adds

Wave 3 supports a stronger architecture rule even though it does not establish alpha:

> Never infer a geopolitical repricing state from headline polarity or downstream equity
> direction alone.

The research pipeline should distinguish:

1. source/narrative event;
2. causal-asset confirmation;
3. synchronized first impulse;
4. second-stage continuation;
5. contamination/conflict;
6. failure/no-confirmation.

This prevents two common retrospective errors:
- counting a later equity move as evidence for a rumor the causal market rejected;
- treating a contaminated multi-headline interval as a clean single-catalyst event.

## 8. Combined current evidence

Waves 1-2 already showed that:
- authoritative relief headlines frequently do not generate positive semiconductor continuation;
- oil confirmation is not sufficient for semiconductor continuation;
- source clocks materially alter apparent lead-lag.

Wave 3 now adds that:
- equity outcomes can line up with headline direction even when oil does not confirm;
- those cases must remain rejected/unattributed;
- a causally confirmed event can still be unusable as clean evidence when conflicting
  information arrives inside the measurement window.

Therefore the surviving product thesis is an **evidence-state classifier**, not a
headline-to-trade rule.

## 9. Product consequence

The read-only Narrative Repricing Radar should expose explicit state transitions:

1. NARRATIVE_DETECTED
2. SOURCE_QUALITY_RESOLVED
3. CAUSAL_ASSET_CONFIRMED or CAUSAL_REJECTED
4. FIRST_IMPULSE_OBSERVED
5. CONTINUATION_OBSERVED or NO_CONTINUATION
6. CONFLICTED / CONTAMINATED / DATA_GAP
7. HISTORICAL_ANALOGUE_CONTEXT

The product must never upgrade:
- rumor + later equity move
into
- validated event-driven repricing

without causal confirmation and source-clock integrity.

No alert, ranking, sizing, portfolio, or execution authority is granted.

## 10. Exact continuation

1. Keep the prospective holdout untouched.
2. Continue source-side feature measurement and clock-clean census work.
3. Use Wave-3 false positives to test future classifier precision.
4. Keep mixed/conflicted clusters out of clean directional primary samples.
5. Resolve the remaining cross-session regional data gates through existing Data OS owners.
6. Productize only as a read-only state/analogue surface after classifier behavior survives
   development and prospective evidence.
