# S2 conditional event-response study — P04 EVT-RESULTS, P05 EVT-CAPITAL, P06 EVT-REGULATORY

**HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution**

The graded cohort is the Alibaba issuer group on its US ADS leg (BABA `SEC:US-XNYS-BABA` vs SPY total return, MARKET_US). HK legs (9988 `SEC:HK-XHKG-09988`, 0700 `SEC:HK-XHKG-00700`) and the whole Tencent issuer group are CENSUS-ONLY: counted, listed, abstained, never graded (V0 row 14). Every window return is a conditional post-event co-movement description over a fixed window; the day-s move is excluded and disclosed; nothing here is a forecast, a signal, an attribution or authority of any kind.

- **P07: NOT SUPPORTED in S2 (not commissioned)**
- **P08: NOT SUPPORTED in S2 (not commissioned)**
- **P11: NOT SUPPORTED in S2 (not commissioned)**

## Abstention ladder (first match wins; never a 0.5 fill)

`ABSTAIN_NO_EPISODES` (honest-N 0) → `ABSTAIN_INSUFFICIENT_CLUSTERS` (cluster-N < 2: no test, no CI, per-episode rows printed descriptively) → `DESCRIPTIVE_ONLY` (< 153) → `TESTED`.

## INFO-LEAK (A23) and vintage disclosure

- **P04 TUNE RETIRED** — contamination class `information_leak`; detected_at 2026-10-11T21:59:47+00:00; successor: P04 v2 — not drafted; owner = seat/S0. a window return is invariant to a multiplicative adjustment constant across the window; the leak is the vintage, not necessarily the value. The split is still computed and printed below, labelled NON-CONFIRMATORY — TUNE RETIRED.
- P05: EMPTY — retirement not applicable
- P06: EMPTY — retirement not applicable
- HK series (9988, 0700): VINTAGE_UNVERIFIABLE (disclosed; not retired).
- TRAIN is never retired (SL §8 step 6).

## EVT-RESULTS (REG P04)

Ledger family `sni.s2_event_response.P04` (budget 6, FLOOR); REG canonical family `sni.s0.P04` is recorded for the later R1 step and is never written from S2.

### TRAIN · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TRAIN · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TRAIN · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TUNE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 1 / cluster-N 1; SENS-B honest-N 1 / cluster-N 1.
3. **honest-N (PRIMARY).** 1
4. **cluster-N (PRIMARY).** 1
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_INSUFFICIENT_CLUSTERS
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 1; distinct calendar clusters 1; honest-N 1 (SENS-A 1, SENS-B 1); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_INSUFFICIENT_CLUSTERS**.

**Baselines.**
- baseline (i) always-long (+1): episode fa48d372d67f s_us 2026-05-13 excess -0.0763444217 direction +1 → non-hit
- baseline (ii) sign of the trailing-63-session excess at D(s): episode fa48d372d67f s_us 2026-05-13 excess -0.0763444217 direction +1 → non-hit
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: episode fa48d372d67f s_us 2026-05-13 excess -0.0763444217 direction ABSTAIN → —
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=1)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

**NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK).** evidence: series=close/close_price; first_offending_date=2026-06-11,2026-06-18; steps_above_tolerance={'BABA': 1, 'SPY': 2}; max_abs_step={'BABA': 0.009183968381, 'SPY': 0.002576235571}; membership_sha256 `a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6`; successor P04 v2 — not drafted; owner = seat/S0.

### TUNE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 1 / cluster-N 1; SENS-B honest-N 1 / cluster-N 1.
3. **honest-N (PRIMARY).** 1
4. **cluster-N (PRIMARY).** 1
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_INSUFFICIENT_CLUSTERS
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 1; distinct calendar clusters 1; honest-N 1 (SENS-A 1, SENS-B 1); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_INSUFFICIENT_CLUSTERS**.

**Baselines.**
- baseline (i) always-long (+1): episode fa48d372d67f s_us 2026-05-13 excess -0.2183928942 direction +1 → non-hit
- baseline (ii) sign of the trailing-63-session excess at D(s): episode fa48d372d67f s_us 2026-05-13 excess -0.2183928942 direction +1 → non-hit
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: episode fa48d372d67f s_us 2026-05-13 excess -0.2183928942 direction ABSTAIN → —
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=1)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

**NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK).** evidence: series=close/close_price; first_offending_date=2026-06-11,2026-06-18; steps_above_tolerance={'BABA': 1, 'SPY': 2}; max_abs_step={'BABA': 0.009183968381, 'SPY': 0.002576235571}; membership_sha256 `a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6`; successor P04 v2 — not drafted; owner = seat/S0.

### TUNE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 1 / cluster-N 1; SENS-B honest-N 1 / cluster-N 1.
3. **honest-N (PRIMARY).** 1
4. **cluster-N (PRIMARY).** 1
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_INSUFFICIENT_CLUSTERS
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 1; distinct calendar clusters 1; honest-N 1 (SENS-A 1, SENS-B 1); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_INSUFFICIENT_CLUSTERS**.

**Baselines.**
- baseline (i) always-long (+1): episode fa48d372d67f s_us 2026-05-13 excess -0.2051207405 direction +1 → non-hit
- baseline (ii) sign of the trailing-63-session excess at D(s): episode fa48d372d67f s_us 2026-05-13 excess -0.2051207405 direction +1 → non-hit
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: episode fa48d372d67f s_us 2026-05-13 excess -0.2051207405 direction ABSTAIN → —
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=1)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

**NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK).** evidence: series=close/close_price; first_offending_date=2026-06-11,2026-06-18; steps_above_tolerance={'BABA': 1, 'SPY': 2}; max_abs_step={'BABA': 0.009183968381, 'SPY': 0.002576235571}; membership_sha256 `a3b15693e32d9d2f44e5e4a78f90bdfb3ac2afece84b5691be12e03685804ed6`; successor P04 v2 — not drafted; owner = seat/S0.

### QUARANTINE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): earnings.parquet#ticker=BABA; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 13; effective_n 13; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 13 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

## EVT-CAPITAL (REG P05)

Ledger family `sni.s2_event_response.P05` (budget 6, FLOOR); REG canonical family `sni.s0.P05` is recorded for the later R1 step and is never written from S2.

### TRAIN · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TRAIN · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TRAIN · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TUNE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TUNE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TUNE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (1): 12295308,12295380,12300619; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

## EVT-REGULATORY (REG P06)

Ledger family `sni.s2_event_response.P06` (budget 6, FLOOR); REG canonical family `sni.s0.P06` is recorded for the later R1 step and is never written from S2.

### TRAIN · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TRAIN · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TRAIN · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TUNE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TUNE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### TUNE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=5

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=21

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

### QUARANTINE · h=63

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

Across the counted episodes the post-event directional agreement with each frozen baseline cannot be distinguished from a coin flip at this sample size; the rows describe conditional post-event co-movement over fixed windows and are not forecasts, signals or attribution.

1. **Null.** see the plain-word statement above.
2. **Analysis set.** PRIMARY leads; SENS-A honest-N 0 / cluster-N 0; SENS-B honest-N 0 / cluster-N 0.
3. **honest-N (PRIMARY).** 0
4. **cluster-N (PRIMARY).** 0
5. **Literal row count.** 7 (pre step 0; transparency only, never a sample size)
6. **Visible exclusions.** excluded-and-listed (0): none; confounded 0; absorbed 0; purged 0; QUARANTINE 0.
7. **Test.** ABSTAIN_NO_EPISODES
8. **CI.** CI NOT ESTIMABLE (cluster-N < 2)
9. **Trial count.** literal_n 12; effective_n 12; declared_budget 6 — effective N (trials; TrialLedger.effective_n — never a sample N, IL §1).
10. **Receipt.** inputs pinned at 5ef7a7f39f99232bf9b574c7603da1011ee3af66 (see seal INPUT_MANIFEST blob ids; the branch head is never stamped so byte-compares stay stable); prereg digest `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`; seal row research/single_name_intelligence/runs/s2_event_response/SEAL_AND_BUDGET.json (REG §6 stays empty in S2; the seat integrates); ledger research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl; prior looks: none for v1.

**Commission family row.** event count 0; distinct calendar clusters 0; honest-N 0 (SENS-A 0, SENS-B 0); effective N 12 (trials; never a sample N); pooling weight NOT ESTIMABLE; uncertainty CI NOT ESTIMABLE (cluster-N < 2); abstention state **ABSTAIN_NO_EPISODES**.

**Baselines.**
- baseline (i) always-long (+1): no counted episodes in this block
- baseline (ii) sign of the trailing-63-session excess at D(s): no counted episodes in this block
- baseline (iii) direction of the all-events pooled TRAIN prior: NOT ESTIMABLE (TRAIN cluster-N < 2; TRAIN episodes=0)
- baseline (iii) direction of the all-events pooled TRAIN prior: no counted episodes in this block
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): NOT ESTIMABLE (hierarchy legs above own-name unregistered; own-name honest-N=0)
- challenger: frozen hierarchy (broad event prior → neighborhood → issuer/instrument → bounded own-name): no counted episodes in this block

**Proper score.** NOT SUPPORTED (REG P04: hit and excess are not a proper score)

## Census-only issuer group: tencent (00700)

Counted and listed, never graded (V0 row 14): the interim-results announcement (news_id 12280990, 2026-08-12 16:31 HKT) forms one census episode per horizon (TUNE; at h=63 its window reaches past 2026-10-01 and the line carries the purged flag). It never enters any graded honest-N, test, CI or family row above.

## Excluded-and-listed census (graded cohort)

- `earnings.parquet#ticker=BABA` — TIMESTAMP_QUALITY EVENT_DATE is not an admissible t_avail (IL §1); listed, never an anchor (P04 scope).
- `12295308,12295380,12300619` — one general-mandate placing programme (ONE event under REG P05), excluded and listed: E0 gap 10 (HK placement coverage misses general-mandate placings).
- `12291963` — census-level near-token refusal (token `40700` is not `00700`); tencent census scope.

## Reproduction

```
python3 research/single_name_intelligence/event_response/run_s2.py \
    --input-ref 5ef7a7f39f99232bf9b574c7603da1011ee3af66 \
    --out-dir research/single_name_intelligence/runs/s2_event_response \
    --trial-ledger-path research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl
```

`--check` reruns into a temp dir and byte-compares every output (ledger after dropping `ts`); the runner first recomputes every membership_sha256 and the prereg digest and exits non-zero on any mismatch with the seal.

