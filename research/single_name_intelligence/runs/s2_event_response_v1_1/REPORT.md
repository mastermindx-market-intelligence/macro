# S2 conditional event-response study — P04 EVT-RESULTS, P05 EVT-CAPITAL, P06 EVT-REGULATORY

**HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution**

## Version record

This is S2 **v1.1**, a defect-repair reprint. It supersedes v1 at commit `b75a3c27083e1e1dec820e4d545e3a3948b3244b`. Reason = defect repair (X2-01..08, A7-F1/F2/F5) with one line per defect:

- **X2-01.** INFO-LEAK scan and retirement run before any window return; retired cells print RETIRED-CONTAMINATED and do not resolve excesses
- **X2-02.** trailing63_direction uses the frozen prereg sign (BABA(D)/BABA(D63)-1)-(SPY(D)/SPY(D63)-1); v1 printed the inverse and is void
- **X2-03.** v1.1 seal carries top-level authority_flags (all false) and outcome_free true; builder and verifier refuse any non-False flag
- **X2-04.** per-cell graded_membership_count / graded_membership_sha256 / census_only_count added; membership_sha256 unchanged
- **X2-05.** REG §3 RETIRED-CONTAMINATED fold for P01/P03/P04 v1 TUNE; §7 successor = — (none registered); owner = seat/S0
- **X2-06.** REPORT states once that 27 cells plus 3 REG §6 TEST-rule rows all abstained and multiplicity adjustment is not estimable
- **X2-07.** each TUNE block prints baseline (iii) once; proper-score line cites the block's own protocol
- **X2-08.** REPORT opens with a 27-row honest-N lead table; trial counts live in a receipt footnote
- **A7-F1.** purge_flag(split, None) returns True (unknown coverage purged); v1 rows with coverage None = 0 so membership_sha256 unchanged
- **A7-F2.** split_tokens drops empty-after-strip tokens; None stays []
- **A7-F5.** run_collapse exclusions are sorted by (step, issuer_key, id)

- Prereg digest v1 `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; v1.1 `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; unchanged = True.
- membership_sha256 per cell: identical to v1.
- No configuration added, removed, or changed.
- All cells still abstain.
- v1 baseline-(ii) directions printed in v1 were sign-inverted relative to the prereg and are void.
- v1 P04 TUNE excesses were computed before the leak scan and are void.
- Authority flags all false; descriptive_only = True.

This reprint examined 27 cells plus the 3 REG §6 TEST-rule rows; every cell abstained (27 of 27); no p-value family exists; multiplicity adjustment is therefore not estimable.

The graded cohort is the Alibaba issuer group on its US ADS leg (BABA `SEC:US-XNYS-BABA` vs SPY total return, MARKET_US). HK legs (9988 `SEC:HK-XHKG-09988`, 0700 `SEC:HK-XHKG-00700`) and the whole Tencent issuer group are CENSUS-ONLY: counted, listed, abstained, never graded (V0 row 14). Every window return is a conditional post-event co-movement description over a fixed window; the day-s move is excluded and disclosed; nothing here is a forecast, a signal, an attribution or authority of any kind.

- **P07: NOT SUPPORTED in S2 (not commissioned)**
- **P08: NOT SUPPORTED in S2 (not commissioned)**
- **P11: NOT SUPPORTED in S2 (not commissioned)**

## Lead table (honest-N / cluster-N / state per cell)

| protocol | split | horizon | honest-N | cluster-N | state |
|---|---|---|---|---|---|
| P04 | TRAIN | 5 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P04 | TRAIN | 21 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P04 | TRAIN | 63 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P04 | TUNE | 5 | 1 | 1 | ABSTAIN_INSUFFICIENT_CLUSTERS |
| P04 | TUNE | 21 | 1 | 1 | ABSTAIN_INSUFFICIENT_CLUSTERS |
| P04 | TUNE | 63 | 1 | 1 | ABSTAIN_INSUFFICIENT_CLUSTERS |
| P04 | QUARANTINE | 5 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P04 | QUARANTINE | 21 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P04 | QUARANTINE | 63 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | TRAIN | 5 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | TRAIN | 21 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | TRAIN | 63 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | TUNE | 5 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | TUNE | 21 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | TUNE | 63 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | QUARANTINE | 5 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | QUARANTINE | 21 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P05 | QUARANTINE | 63 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | TRAIN | 5 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | TRAIN | 21 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | TRAIN | 63 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | TUNE | 5 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | TUNE | 21 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | TUNE | 63 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | QUARANTINE | 5 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | QUARANTINE | 21 | 0 | 0 | ABSTAIN_NO_EPISODES |
| P06 | QUARANTINE | 63 | 0 | 0 | ABSTAIN_NO_EPISODES |

Lead-table rows: 27.

## Abstention ladder (first match wins; never a 0.5 fill)

`ABSTAIN_NO_EPISODES` (honest-N 0) → `ABSTAIN_INSUFFICIENT_CLUSTERS` (cluster-N < 2: no test, no CI, per-episode rows printed descriptively) → `DESCRIPTIVE_ONLY` (< 153) → `TESTED`.

## INFO-LEAK (A23) and vintage disclosure

- **P04 TUNE RETIRED** — contamination class `information_leak`; detected_at 2026-10-11T21:59:47+00:00; successor: — (none registered); owner = seat/S0. a window return is invariant to a multiplicative adjustment constant across the window; the leak is the vintage, not necessarily the value. Retired cells print `RETIRED-CONTAMINATED (information_leak) — outcome not computed` and do not resolve a window return.
- P05: EMPTY — retirement not applicable
- P06: EMPTY — retirement not applicable
- HK series (9988, 0700): VINTAGE_UNVERIFIABLE (disclosed; not retired).
- TRAIN is never retired (SL §8 step 6).

## EVT-RESULTS (REG P04)

Ledger family `sni.s2_event_response.P04` (budget 6, FLOOR); REG canonical family `sni.s0.P04` is recorded for the later R1 step and is never written from S2.

### TRAIN · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TRAIN · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TRAIN · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TUNE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: fewer than two independent clusters, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 1 / cluster-N 1; SENS-B honest-N 1 / cluster-N 1.
3. **honest-N (PRIMARY).** 1
4. **cluster-N (PRIMARY).** 1
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_INSUFFICIENT_CLUSTERS
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 1; distinct calendar clusters 1; honest-N 1 (SENS-A 1, SENS-B 1); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_INSUFFICIENT_CLUSTERS**.

**Baselines.**
- baseline (i) always-long (+1): RETIRED-CONTAMINATED (information_leak) — outcome not computed
- baseline (ii) sign of the trailing-63-session excess at D(s): RETIRED-CONTAMINATED (information_leak) — outcome not computed
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=1)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

**NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK).** evidence: series=close/close_price; first_offending_date=2026-06-11,2026-06-18; steps_above_tolerance={'BABA': 1, 'SPY': 2}; max_abs_step={'BABA': 0.009183968381, 'SPY': 0.002576235571}; membership_sha256 `a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6`; successor — (none registered); owner = seat/S0.

### TUNE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: fewer than two independent clusters, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 1 / cluster-N 1; SENS-B honest-N 1 / cluster-N 1.
3. **honest-N (PRIMARY).** 1
4. **cluster-N (PRIMARY).** 1
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_INSUFFICIENT_CLUSTERS
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 1; distinct calendar clusters 1; honest-N 1 (SENS-A 1, SENS-B 1); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_INSUFFICIENT_CLUSTERS**.

**Baselines.**
- baseline (i) always-long (+1): RETIRED-CONTAMINATED (information_leak) — outcome not computed
- baseline (ii) sign of the trailing-63-session excess at D(s): RETIRED-CONTAMINATED (information_leak) — outcome not computed
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=1)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

**NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK).** evidence: series=close/close_price; first_offending_date=2026-06-11,2026-06-18; steps_above_tolerance={'BABA': 1, 'SPY': 2}; max_abs_step={'BABA': 0.009183968381, 'SPY': 0.002576235571}; membership_sha256 `a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6`; successor — (none registered); owner = seat/S0.

### TUNE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: fewer than two independent clusters, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 1 / cluster-N 1; SENS-B honest-N 1 / cluster-N 1.
3. **honest-N (PRIMARY).** 1
4. **cluster-N (PRIMARY).** 1
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_INSUFFICIENT_CLUSTERS
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 1; distinct calendar clusters 1; honest-N 1 (SENS-A 1, SENS-B 1); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_INSUFFICIENT_CLUSTERS**.

**Baselines.**
- baseline (i) always-long (+1): RETIRED-CONTAMINATED (information_leak) — outcome not computed
- baseline (ii) sign of the trailing-63-session excess at D(s): RETIRED-CONTAMINATED (information_leak) — outcome not computed
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=1)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

**NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK).** evidence: series=close/close_price; first_offending_date=2026-06-11,2026-06-18; steps_above_tolerance={'BABA': 1, 'SPY': 2}; max_abs_step={'BABA': 0.009183968381, 'SPY': 0.002576235571}; membership_sha256 `a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6`; successor — (none registered); owner = seat/S0.

### QUARANTINE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

## EVT-CAPITAL (REG P05)

Ledger family `sni.s2_event_response.P05` (budget 6, FLOOR); REG canonical family `sni.s0.P05` is recorded for the later R1 step and is never written from S2.

### TRAIN · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

### TRAIN · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

### TRAIN · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

### TUNE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

### TUNE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

### TUNE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

### QUARANTINE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

### QUARANTINE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

### QUARANTINE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P05: hit and excess are not a proper score)

## EVT-REGULATORY (REG P06)

Ledger family `sni.s2_event_response.P06` (budget 6, FLOOR); REG canonical family `sni.s0.P06` is recorded for the later R1 step and is never written from S2.

### TRAIN · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

### TRAIN · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

### TRAIN · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

### TUNE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

### TUNE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

### TUNE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

### QUARANTINE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

### QUARANTINE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

### QUARANTINE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

This family abstains: no episode was counted in this block, so no agreement rate, no interval and no test against the frozen baselines is estimable. The rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** see receipt footnote (trial counts are never printed beside honest-N).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl; prior looks: none for v1.1 (v1 P04 TUNE excesses and v1 baseline-(ii) directions are void; see VERSION_RECORD.json).

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)

**Proper score.** NOT SUPPORTED (REG P06: hit and excess are not a proper score)

## Census-only issuer group: tencent (00700)

Counted and listed, never graded (V0 row 14): the interim-results announcement (news_id 12280990, 2026-08-12 16:31 HKT) forms one census episode per horizon (TUNE; at h=63 its window reaches past 2026-10-01 and the line carries the purged flag). It never enters any graded honest-N, test, CI or family row above.

## Excluded-and-listed census (graded cohort)

- `earnings.parquet#ticker=BABA` — TIMESTAMP_QUALITY EVENT_DATE is not an admissible t_avail (IL §1); listed, never an anchor (P04 scope).
- `12295308,12295380,12300619` — one general-mandate placing programme (ONE event under REG P05), excluded and listed: E0 gap 10 (HK placement coverage misses general-mandate placings).
- `12291963` — census-level near-token refusal (token `40700` is not `00700`); tencent census scope.

## Receipt footnote: trial counts

Trial counts (literal_n / effective_n / declared_budget) are the multiple-testing quantity and are never a sample N (IL §1). They are printed here once per family, never inside a cell block beside honest-N.

| protocol | literal_n | effective_n | declared_budget |
|---|---|---|---|
| P04 | 13 | 13 | 6 |
| P05 | 12 | 12 | 6 |
| P06 | 12 | 12 | 6 |

## Reproduction

```
python3 research/single_name_intelligence/event_response/run_s2.py \
    --input-ref 5ef7a7f39f99232bf9b574c7603da1011ee3af66 \
    --out-dir research/single_name_intelligence/runs/s2_event_response_v1_1 \
    --trial-ledger-path research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl \
    --seal-dir research/single_name_intelligence/runs/s2_event_response_v1_1
```

`--check` reruns into a temp dir and byte-compares every output (ledger after dropping `ts`); the runner first recomputes every membership_sha256 and the prereg digest and exits non-zero on any mismatch with the seal.

