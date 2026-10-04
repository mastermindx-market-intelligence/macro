# Cross-Session Daily Handoff — Hong Kong Advisory Result

Date: 2026-09-26  
State: DEVELOPMENT_EVIDENCE / EXPLORATORY_ADVISORY / PRODUCTION_INERT / NO TRADING AUTHORITY  
Operation: geopolitical-relief-event-study-20260924-sol-001  
Carrier: Macro PR #8012 / `sol/geopolitical-relief-event-study-20260924`  
Source manifest: `research/CROSS_SESSION_DAILY_HANDOFF_SOURCE_MANIFEST_2026-09-26.json`  
Manifest blob: `af5bccef35212fe32462e79a7ade8bc9caea1ca4`  
Protected Mastermind pin: `763ec8f920177fdf48b18df1b8e37b61ab482ef0`  
Skillpack INDEX blob: `94d1af402598894372858793a5b1931019c5fa77`

## Evidence boundary

The 22-event Hong Kong advisory set was frozen from source metadata before HSI outcomes were read.
The parent source census remains `retrieval_incomplete`, so this is development evidence only and
cannot support a population timing-frequency claim.

The outcome read used the incumbent Hong Kong Yahoo transport family through the existing
`HkPriceAdapter._download(["^HSI"], "max")` semantics with `auto_adjust=true`.
The dedicated existing `/Users/chriswong/cnhk-venv` supplied the already-installed yfinance
runtime. No HSI bytes were persisted, no new collector/store/data plane was created, and the
canonical `data/hk` namespace was not mutated.

Observed HSI coverage from that read: 1986-12-31 through 2026-09-25, 9,807 daily rows.

The recovery process had already exposed mainland Shanghai daily bars while reconciling local
data availability. Mainland daily handoff therefore remains explicitly contaminated for this
continuation and is not treated as a blind slice. The prospective V2 holdout remains untouched.

## Frozen advisory geometry

For each source-selected post-Asia-close event:

- previous observed HSI cash close -> next observed HSI session open;
- previous observed close -> next observed session close;
- next observed open -> next observed close.

The event clock is preserved. No event is moved to the next market open. Observed HSI bar dates
are used only for this advisory diagnostic and do not claim an authoritative HK holiday/half-day
calendar.

Directional transform was frozen before outcome access:

- relief / implementation relief: positive HSI gap is directionally consistent;
- escalation / implementation escalation: negative HSI gap is directionally consistent;
- mixed/conflicted and denial/breakdown rows remain descriptive.

## Primary advisory result

Among the 18 directional event rows:

- direction-adjusted next-open gap mean: **-27.66 bp**
- median: **-8.66 bp**
- positive rate: **5/18 = 27.8%**

After de-duplicating events that map to the same target HSI open and keeping only unmixed
directional target opens:

- independent unmixed target opens: **17**
- direction-adjusted mean: **-29.20 bp**
- median: **-9.13 bp**
- positive rate: **5/17 = 29.4%**

This development slice does **not** support the generic rule:

> post-Asia-close geopolitical headline -> next Hong Kong open follows headline direction.

The point estimate is opposite that simple rule.

## Previously classified causal-confirmed subset

To avoid post-HSI threshold tuning, the narrow subset below is not selected from Hong Kong
outcomes. It is the four Wave-1 rows that the pre-existing
`NARRATIVE_REPRICING_V2_CLOCK_CLEAN_WAVE1_RESULTS_2026-09-25.md` receipt had already
identified as fully measured primary rows with USO moving in the expected relief direction
over the first five minutes:

| Event | Frozen prior causal state | HSI next-open direction-adjusted gap |
|---|---|---:|
| 2026-08-04 Bessent / possible Hormuz deal | expected-direction oil confirmation | +14.73 bp |
| 2026-08-06 19:53Z Oman/Iran agreement | expected-direction oil confirmation | -1.42 bp |
| 2026-08-07 U.S. official expects deal soon | expected-direction oil confirmation | +53.43 bp |
| 2026-08-21 navigation talks | expected-direction oil confirmation | -88.18 bp |

Descriptive result:

- n = **4**
- positive = **2/4**
- mean = **-5.36 bp**
- median = **+6.65 bp**

This tiny subset is mixed. Causal oil confirmation alone does not establish a positive
next-Hong-Kong-open handoff.

The July 14 escalation event is not added to a clean confirmed subset even though its prior
receipt classified the causal proxy as confirmed, because that same pre-existing receipt
also classified it `SOURCE_CONFOUNDED` by a competing de-escalatory headline ten minutes
later. The Aug 25 and Aug 31 rumor controls remain causal-rejected under their pre-existing
Wave-3 classifications.

## Interpretation

The recovered evidence now falsifies three progressively simpler stories:

1. **Oil leads semiconductors by a clean one-minute lag.** Falsified at the earliest Sep 24
   public distribution clock; the first cross-asset impulse was effectively synchronized.
2. **Credible relief + oil confirmation is sufficient for positive semiconductor continuation.**
   Not supported across Waves 1-3.
3. **A post-Asia-close geopolitical headline is generally carried in the same direction into
   the next Hong Kong open.** Not supported in this frozen advisory slice.

The surviving research thesis is therefore an **evidence-state and analogue problem**, not a
headline-polarity rule:

`NARRATIVE_DETECTED -> SOURCE_QUALITY -> CAUSAL_CONFIRMED/REJECTED -> FIRST_IMPULSE ->
CONTINUATION/NO_CONTINUATION -> CROSS_SESSION_ASSIMILATION -> CONFLICT/DATA_GAP ->
HISTORICAL_ANALOGUE`

The cross-session question that remains legitimate is interaction-based: whether specific
source novelty, physical-channel implementation, pre-event risk-premium state, synchronized
global repricing, and contamination state jointly explain how much information remains for
the next regional cash session.

## Source gates still open

- HK first-5-minute primary endpoint: **SOURCE_GATE** — no admitted historical HK minute
  plane was established by this work.
- Mainland first-5-minute endpoint: **MATERIALIZATION_GATE** — reviewed TuShare minute-plane
  implementation exists, but the current M2 canonical data root does not contain the minute
  store; this research PR will not launch a bulk backfill.
- Parent timing-frequency population inference: **COVERAGE_GATE** — source census remains
  retrieval-incomplete.
- V2 prospective holdout: **UNTOUCHED**.

## Disposition

No alpha, alert, ranking, trade, sizing, portfolio, or execution authority is granted.

Do not rescue the original story by tuning a post-hoc clock bucket, oil threshold, or HSI-gap
threshold. The next useful build is a read-only evidence-state / analogue layer backed by the
already-frozen research states, while regional intraday source gates are resolved through the
existing Data OS owners.
