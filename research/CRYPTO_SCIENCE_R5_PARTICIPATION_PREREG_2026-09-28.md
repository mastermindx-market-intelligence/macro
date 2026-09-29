# Crypto science R5 — frozen incremental spot-participation experiment

Date2026-09-28; WS:CRYPTO-INTELLIGENCE / draft PR8050; existing operation crypto-vector-r2-20260926-sol-001. Research only: no production engine/config/gate/collector/UI change.

## Authority and frozen scope

Current Chairman Continue covers the next scientific question: distinguish continuing downside from stabilization/recovery, testing whether same-venue spot participation adds to price response on the SAME R4 parent episodes. Protected Mastermind7aa27814c65983932f466d7b79e293e24f5a69c7; INDEX94d1af402598894372858793a5b1931019c5fa77; compatible1.0.1/bootstrap1, ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT loaded. Same Sol/M2 Studio Direct carrier and clean existing sparse workspace; basebf879ff6a26d2369d970dc583d89ba2aadab5e62. Direct duty PRINCIPAL_JUDGMENT; no worker/independent reviewer/runtime created. Existing R4 CI/fences passed at recovery, not release acceptance.

Commit this protocol BEFORE new R5 outcomes. R4 results are already seen, so all periods are retrospective. Metadata-only inspection:94,063 Coinbase hourly OHLCV rows;2,957 OKX taker rows; Coinbase daily/hourly hashes equal R4. No R5 feature/outcome scan preceded this freeze. New R5 paths were absent. An optional gh read had a TLS timeout (no effect); this protocol's first oversized write returned Session terminated, and exact same-carrier readback showed ENOENT (no file effect). This is one smaller same-carrier technical recovery, not refusal bypass.

## Measurement

Primary source: existing Coinbase BTC-USD hourly OHLCV. Bucket timestamps are STARTS; use completed observations, then a later stored hourly open. Volume is unsigned participation, not aggressor identity, resting depth, replenishment or proven absorption. Preserve missing calendar bars/invalid OHLC; volume must be finite/nonnegative, reference median positive. Zero current volume is valid. Do not impute zero for absent volume.

OKX's actual collector requests instType=CONTRACTS, ccy=BTC, period=1H. Its aggressor flow is DERIVATIVES, not Coinbase spot. R5 records that boundary but does not combine or score it. Separate contract/venue/time qualification and a future frozen extension are required. No candle-signed flow, historical splice, provider call or raw-data publication.

Official Coinbase candle documentation checked: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles (start, open/close trades, bucket volume, possible gaps). Reference ratios within a source do not certify its historical revisions/publication clocks. All fills remain idealized price references, not achievable execution receipts.

## Parent/timing invariants

Reuse exact R4 D0 anchors(588) and daily washout parents(59). Assert source/anchor digests. Do not independently reselect D1 or optimize spacing. Reuse R4 account_path, complete_window, barrier_label, incumbent_targets, interval90 and the immutable r4/incumbent_replay_targets.csv after verifying its original input identities. This sidecar is research evidence, not a live target store.

Execution lag1h primary,6h sensitivity; costs0/10/25bp one-way turnover; cash yield0; positions drift until target changes. Both policies share initial state and endpoint. Existing R4 engine defaults and evidence remain untouched.

## Downside: six-hour landmark within original24h parent

Parent starts a, issue T=a+1h, original executable origin O=T+lag, endpoint E=O+24h. Observe SIX completed bars T..T+5h. Landmark issue L=T+6h, action F=L+lag; remaining horizon18h. Pre-F damage is not future prediction.

Broken level=min low of72 pre-parent bars a-72h..a-1h. All required prices must be valid.
- PERSISTENT: last follow-up close<broken level AND min low last3 follow-up bars<min low first3.
- RECLAIMED: last close>=broken level.
- STALLED_BELOW: below level without further low progression.
- UNKNOWN: required price evidence incomplete. These are descriptive price states, not a microstructure absorption verdict.

V=mean six follow-up volumes / median72 pre-parent volumes. Fixed threshold V>=1; no optimization. Required invalid/missing/negative volume or zero denominator=>unknown volume, not zero.

All paths start with incumbent allocation at O and restore incumbent target at E:
- INCUMBENT follows its delayed target throughout.
- DELAYED_CASH follows incumbent until F then cash to E (timing-only control).
- PRICE applies that cash action only for PERSISTENT; otherwise incumbent. Unknown price=>unavailable.
- PRICE_VOLUME applies it only for PERSISTENT and V>=1. Persistent but unknown V=>unavailable, not rescue or flat. Nonpersistent follows incumbent and does not require volume.

Primary contrast PRICE_VOLUME minus PRICE at1h/10bp on common full-history parents. Secondary versus incumbent/delayed cash. First passage starts F, ends E:5%down before3%up over18h. Retain neither/ambiguous/censored labels and all state/volume groups. Common-parent means include no-action cases.

## Recovery: earlier reclaim, volume evaluated at the SAME first entry

Use R4 washout parents. Daily issue T=a+24h; original O=T+lag; common E=O+336h. Search buckets t=T+6h..T+47h in order, for FIRST:
1. close(t)>max high of previous6 bars(excluding current);
2. min low t-2h..t >= min low t-5h..t-3h.
All seven price bars must be present/valid. Unknown intervening window stops with UNKNOWN; do not skip a gap to a favorable later observation. No condition by T+48h=>NO_ENTRY. Execute t+1h+lag, not the close. Earliest issue is T+7h.

P buys full BTC at that first price entry and holds to E; starts/ends cash. PV uses EXACTLY that date only if mean volume t-2h..t / median72 volumes t-74h..t-3h >=1. A failed volume gate means cash for entire parent, not a later search. Unknown V=>unavailable PV; P retained. No-entry parents remain cash without spurious fees.

Compare P/PV with immediate U0, R4 daily U1, corrected incumbent and cash at SAME O/E. Conditional labels:5%up before3%down over168h after each actual entry. Keep no-entry/unknown parents. Primary contrast PV-P full-history1h/10bp. P-immediate and P-daily-U1 are secondary. An ex-post exposure-duration control may be reported only as non-executable diagnostic, not risk-matched policy.

## Reporting and scientific gate

Full history,2016–2019,2020–2023,reused2024+; retain period-crossing parents but censor endpoints beyond each slice. Every lag/cost reported. No fit/parameter sweep. Retain each condition/status, price entry, landmark, volume ratio, lineage, barrier category and paired account return/drawdown/turnover. Compare policies only on shared nonmissing parents; disclose total versus usable counts. Never select a sample using future outcomes. Ambiguous first-passage order receives no favorable credit.

Use R4's90-calendar-day block bootstrap(seed20260928,1000draws) on signed paired event differences; report descriptive95% intervals, yearly counts and leave-one-year-out means. These do not adjust for all sequential research choices or provide current probabilities. Two volume contrasts are co-primary, not best-of-selected. Compare volume gate to price-only at identical candidate time. Changes in the number of actions must not be sold as increased forecast recall without evaluating missed events.

No candidate earns live promotion from this reused history. Positive primary mean with uncertainty/period/lag/cost robustness can earn only independent-review and forward-test priority. Negative/fragile results persist unchanged. All proposed definitions are research hypotheses, not risk-on/off instructions. Do not infer that high volume is buying or that candle stabilization proves limit-order absorption.

## Implementation plan

Architecture: research/crypto_science/r5_participation_study.py imports existing R4 helpers and immutable targets/events. Artifacts r5/. Tests appended to already-invoked tests/test_btc_impulse_falsifier.py; no new CI job/production model. Stack existing Python/Pandas/NumPy/pytest. Existing Agent OS workstream/decision carries continuity.

- Commit this protocol before outcomes.
- RED tests: prefix invariance; pre-parent volume reference excludes trigger/follow-up; zero versus missing/negative volume; broken calendars; first reclaim never shifted by volume gate; valid no-entry versus unknown; original common endpoints and explicit later action.
- Implement research helpers; pass tests; commit before the outcome scan.
- Hash inputs, R4 receipts, engine/config and existing gates; run once; retain all conditions/results and do not publish raw price data.
- Independently verify classification, timestamps, first-passage and cash/coin arithmetic without simply calling the generator. Same-session arithmetic is not an independent reviewer.
- Run current combined Vector/Crypto/science pack, source-claim checker, compile/diff checks. Preserve real failures and technical amendments with initial outputs.
- Publish full result and cumulative existing-owner checkpoint with readback. No automatic future work.

Review focus: no hindsight anchor; no volume-induced re-entry search; no missing-flow zero; no pre-action damage credited; no scenario-row independence claim. Short actual CONTRACTS flow remains separate from long Coinbase unsigned spot participation. Publication qualification, legacy funding semantics, independent review and all parent release gates remain open.
