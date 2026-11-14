# Risk Radar BT1-RATE-RESPONSE on PRE — description only

Window 2006-01-03..2019-12-31, pre 21, post 5, seed 20261112, 2000 draws, tol 0.01, min_off 10; control seed 20261113, 2000 accepted draws. bm_ref rev1 pin.

**Nothing is tuned.** The rule is frozen as written in BREAKTHROUGH_1_ANSWER.md and repeated in ledger rows `rr-bt1-rate-response-pre-desc` / `rr-bt1-rate-response-pre-dgs10-desc`. Both are DESCRIPTION only, never a nomination.

## Pins and rows

- `bm_ref.py` `f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76` (end `f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76`)
- `adapter.py` `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1` (end `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1`)
- `rr-bt1-rate-response-pre-desc` spec `d80306439c57cdc945d27055551647b329bce5e1987ea6e623d7b1effc4f276a`
- `rr-bt1-rate-response-pre-dgs10-desc` spec `63a0ce44d5df9fa85ea83d88c3d4468e7fbc5c94be0090f3120f624daa876235`
- scorer `<desk>/pivot/radar_eval/engine/risk_radar_eval/pivots.py`

## Date guard

Every turn, alert, level, episode and `outcomes_through` date is ≤ 2019-12-31; every scored turn is ≥ 2006-01-03 (asserted).

| surface | max date |
|---|---|
| turns | 2019-12-31 |
| levels | 2019-12-31 |
| outcomes_through | 2019-12-31 |
| engine_calendar_used | 2019-12-31 |
| episodes | 2019-12-31 |

Min scored turn: 2006-01-11.

## DFII10 (the frozen rule)

| metric | value |
|---|---|
| cluster share | 0.173 |
| 90% CI | [0.120, 0.238] |
| false/asset-yr | 0.826 |
| median delay | -12.0 |
| alert share (pooled) | 0.015 |
| ON days / ON starts (window) | 53 / 31 |
| turns scored / flagged | 471 / 51 |
| clusters / flagged | 127 / 22 |
| placebo p90 (cluster) | 0.307 |
| ref dd share / false | 0.047 / 0.153 |
| ref near **(better)** share / false | 0.323 / 2.954 |

Alert share by year: 2006 0.0000, 2007 0.0080, 2008 0.0553, 2009 0.0198, 2010 0.0000, 2011 0.0159, 2012 0.0120, 2013 0.0159, 2014 0.0119, 2015 0.0198, 2016 0.0079, 2017 0.0000, 2018 0.0359, 2019 0.0079

### Rule 2b — parts at the candidate's realised share

| part | threshold | achieved (finite) | achieved (all) | non-finite | cluster share | false/asset-yr |
|---|---|---|---|---|---|---|
| Rplus | 0.998016 | 0.015080 | 0.015001 | 0/72593 | 0.102 | 0.326 |
| B20_SPY | 0.016563 | 0.014969 | 0.014891 | 0/72593 | 0.276 | 0.844 |
| B20_QQQ | 0.019512 | 0.014941 | 0.014864 | 0/72593 | 0.228 | 0.764 |
| response_only | 0.013731 | 0.015052 | 0.014974 | 0/72593 | 0.244 | 0.823 |
| Q5 | 0.998016 | 0.015080 | 0.015001 | 0/72593 | 0.102 | 0.326 |
| D5 | 0.330000 | 0.014900 | 0.014822 | 0/72593 | 0.055 | 0.278 |

**a/b/c:** a=False, b=False, c=False; criteria_met=[]; parts_checked=4. **DESCRIPTION — nomination False (forced).**

### Principal's diagnosis (equal alert share)

| comparison | candidate share / false | other share / false | false lower? | catch higher? |
|---|---|---|---|---|
| sign gate: Rplus vs Q5 | 0.102 / 0.326 | 0.102 / 0.326 | False | False |
| response: A_R vs Rplus | 0.173 / 0.826 | 0.102 / 0.326 | False | True |
| A_R vs response-only | 0.173 / 0.826 | 0.244 / 0.823 | False | False |

### Native comparator (rates_realrate at .90) — recorded aggregate only

Recorded aggregate `.795 / 4.97` (not re-read). Cluster ids on this window are used only for the paired table.

| set | clusters caught |
|---|---|
| native rate leg | 101 |
| candidate A_R | 22 |
| retained by A_R | 22 |
| lost by A_R | 79 |
| newly caught by A_R | 0 |

### Displaced-clock control (description line)

Status **ESTIMABLE**; seed 20261113, 43125 offset vectors generated (max 200000), 2000 accepted (required 2000).

- observed ON days / starts: 53 / 31
- catch difference p10 / p50: -0.032 / -0.008
- false-rate difference p50 / p90: 0.170 / 0.271
- displaced catch median 0.181, false median 0.656
- observed run lengths: 31 runs, median 1.0, max 6; displaced starts median 31.0, max 32
- count-matching (observed 53 ON days / 31 starts, tolerance ±1): accepted ON-day range [52, 54], start range [30, 32]; acceptance 2000/43125 = 0.0464
- accepted run-length histogram (length: runs across accepted draws): 1: 37445, 2: 14360, 3: 5690, 4: 2720, 5: 1438, 6: 743

### Fragmentation diagnostic (first start per shock episode)

- parent shock episodes (J = qR≥.90 AND dy5>0): 163 (147 in window)
- candidate decision starts 31; retained 24; removed as later repeats 7; unassigned 0
- retained event-list catch share 0.165; false/asset-yr 0.663
- pre-shock equity break already true before the episode: either 38/147 (SPY 31, QQQ 33)

Runtime this block: 44.5s.

## DGS10 substitute line (description)

| metric | value |
|---|---|
| cluster share | 0.142 |
| 90% CI | [0.094, 0.203] |
| false/asset-yr | 0.684 |
| median delay | -17.0 |
| alert share (pooled) | 0.008 |
| ON days / ON starts (window) | 27 / 21 |
| turns scored / flagged | 471 / 45 |
| clusters / flagged | 127 / 18 |
| placebo p90 (cluster) | 0.276 |
| ref dd share / false | 0.039 / 0.153 |
| ref near **(better)** share / false | 0.299 / 2.951 |

Alert share by year: 2006 0.0040, 2007 0.0040, 2008 0.0277, 2009 0.0238, 2010 0.0000, 2011 0.0040, 2012 0.0000, 2013 0.0159, 2014 0.0079, 2015 0.0000, 2016 0.0040, 2017 0.0000, 2018 0.0159, 2019 0.0000

### Rule 2b — parts at the candidate's realised share

| part | threshold | achieved (finite) | achieved (all) | non-finite | cluster share | false/asset-yr |
|---|---|---|---|---|---|---|
| Rplus | 0.998016 | 0.013017 | 0.012949 | 0/72593 | 0.102 | 0.188 |
| B20_SPY | 0.024554 | 0.007644 | 0.007604 | 0/72593 | 0.150 | 0.371 |
| B20_QQQ | 0.026292 | 0.007630 | 0.007590 | 0/72593 | 0.110 | 0.312 |
| response_only | 0.021545 | 0.007644 | 0.007604 | 0/72593 | 0.158 | 0.399 |
| Q5 | 0.998016 | 0.013017 | 0.012949 | 0/72593 | 0.102 | 0.188 |
| D5 | 0.420000 | 0.006245 | 0.006213 | 0/72593 | 0.063 | 0.076 |

**a/b/c:** a=False, b=False, c=False; criteria_met=[]; parts_checked=4. **DESCRIPTION — nomination False (forced).**

### Principal's diagnosis (equal alert share)

| comparison | candidate share / false | other share / false | false lower? | catch higher? |
|---|---|---|---|---|
| sign gate: Rplus vs Q5 | 0.102 / 0.188 | 0.102 / 0.188 | False | False |
| response: A_R vs Rplus | 0.142 / 0.684 | 0.102 / 0.188 | False | True |
| A_R vs response-only | 0.142 / 0.684 | 0.158 / 0.399 | False | False |

### Displaced-clock control (description line)

Status **NOT_ESTIMABLE**; seed 20261113, 200000 offset vectors generated (max 200000), 730 accepted (required 2000).

- observed ON days / starts: 27 / 21
- catch difference p10 / p50: -0.008 / 0.016
- false-rate difference p50 / p90: 0.201 / 0.299
- displaced catch median 0.126, false median 0.482
- observed run lengths: 21 runs, median 1.0, max 3; displaced starts median 21.0, max 22
- count-matching (observed 27 ON days / 21 starts, tolerance ±1): accepted ON-day range [26, 28], start range [20, 22]; acceptance 730/200000 = 0.0037
- accepted run-length histogram (length: runs across accepted draws): 1: 11660, 2: 2735, 3: 640, 4: 166, 5: 25, 6: 14

### Fragmentation diagnostic (first start per shock episode)

- parent shock episodes (J = qR≥.90 AND dy5>0): 173 (158 in window)
- candidate decision starts 21; retained 18; removed as later repeats 3; unassigned 0
- retained event-list catch share 0.134; false/asset-yr 0.607
- pre-shock equity break already true before the episode: either 33/158 (SPY 28, QQQ 23)

Runtime this block: 53.1s.

## Candidate cluster-id overlap, DFII10 vs DGS10

| set | clusters |
|---|---|
| DFII10 candidate | 22 |
| DGS10 candidate | 18 |
| caught by both | 13 |
| only DFII10 | 9 |
| only DGS10 | 5 |

## Deviations

- The two rate legs: DFII10 qR is the engine's own pit_signals('rates_realrate') series; dy5 is the same PIT replay's DFII10.diff(5) (released observations only, ffilled onto the engine sessions), verified to reproduce qR to 1e-12 on 2004+ replay vs the engine leg.
- The PIT helper has no DGS10 rule: availability.release_dates accepts DEXJPUS / DFII10 / BAMLH0A0HYM2 only, and FRED_FIRST_RELEASE_DATES_v1.csv contains no DGS10 rows. The DGS10 line therefore uses the DFII10 branch's documented rule verbatim: observation t is usable from the next business day (US federal holiday calendar), with the same trailing-504 pct_rank_window of diff(5) applied to released observations only.
- Price predicates: B20 is computed on the desk level series (bm_ref.level_series of the catalogue specs SPY and QQQ, adjusted closes truncated at 2019-12-31), reindexed onto the engine SPY-session calendar with ffill so the three operands share one clock.
- Market-level alert broadcast: A_R is one series built on the engine calendar, shifted t+1 on the full series, then reindexed onto every panel series with ffill (the k3 follow-up convention).
- Rplus validity: an observation is valid when qR and dy5 are both present at s; Rplus is 0 when all five are valid and none has dy5>0, and undefined (NaN, not alerting) otherwise.
- Parts at matched share follow the rev1 shift order: the t+1 shift is applied to the full part score series and the window taken afterwards; part_at_matched_share then takes one pooled threshold per part. For scoring, each part's alert is rebuilt on the full windowed index with a non-finite session counting as not alerting (asserted equal to the function's own alert where both are defined).
- Criterion (c) uses the four mandatory parts (Rplus, B20_SPY, B20_QQQ, response-only min(B20_SPY,B20_QQQ)); Q5 and D5 are reported as adversaries in the diagnosis table and are not part of the pass call.
- Displaced-clock control: one market-level Rplus exists, so each year's single drawn shift is trivially the same for every target asset; the price predicates are unchanged.
- Displaced-clock control: the ON-day/start-count match is evaluated on the engine-calendar windowed candidate alert (the fixed scored support), not on the pooled 21-series panel support; the two differ only by ffill edge sessions. Rplus outside PRE years 2006-2019 is left genuine (only PRE calendar years are circularly shifted), so the first sessions of 2006 can read unshifted 2005 values; declared, not smoothed.
- Displaced-clock control: a draw is scored only after the within-one count filter; catch differences are observed cluster share minus displaced, false differences observed false/asset-yr minus displaced. Fewer than 2,000 qualifying draws = NOT_ESTIMABLE.
- Fragmentation: starts are taken from the unshifted decision series A_R inside the scored support, assigned to the parent J episode containing the most recent qualifying session in t-5..t-1, first start per episode retained at its original published (t+1) date, unassigned starts retained. The retained list is evaluated against the same top windows and episode exemptions; no daily alert array is rebuilt.
- Native comparator cluster ids come from a scoring call on the same window; its aggregate is reported only as the recorded .795 / 4.97 and is NOT re-read or re-verdict.
- Both blocks are DESCRIPTION only: nomination is forced False regardless of any figure.
