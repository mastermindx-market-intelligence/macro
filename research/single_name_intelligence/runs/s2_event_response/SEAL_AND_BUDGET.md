# S2 SEAL_AND_BUDGET — P04–P06 frozen before any outcome

Lane `s2_event_response` vv1; BASE `5ef7a7f39f99232bf9b574c7603da1011ee3af66`; branch `claude/sni-s2-event-response-20261011`; input_ref `5ef7a7f39f99232bf9b574c7603da1011ee3af66`.

**Label.** HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1); identity = RETROSPECTIVE_JOIN (A07), identity_resolved_as_of = security_master ingested_at; conditional post-event co-movement description, not an attribution

**Authority flags.** {"escalation_authority": false, "gate_authority": false, "rank_authority": false, "signal_authority": false, "size_authority": false, "trade_authority": false} — all false.

## Families, budgets, itemized grids, REG mapping

| protocol | family | ledger family (S2) | REG canonical family (R1 step) | declared budget | itemized |
|---|---|---|---|---|---|
| P04 | results | sni.s2_event_response.P04 | sni.s0.P04 | 6 (FLOOR) | 12 |
| P05 | capital_action | sni.s2_event_response.P05 | sni.s0.P05 | 6 (FLOOR) | 12 |
| P06 | regulatory_material | sni.s2_event_response.P06 | sni.s0.P06 | 6 (FLOOR) | 12 |

Itemized grid per family: 3 frozen baselines x 3 horizons = 9 configs, plus the challenger column x 3 horizons = 3 (logged even when NOT ESTIMABLE) = 12. Budgets are floors, never caps (REG §8 L205). No `sni.s0.*` ledger row is ever written from S2; the mapping is recorded here for the later R1 step only.

## Not supported in S2

- P07: NOT SUPPORTED in S2 (not commissioned)
- P08: NOT SUPPORTED in S2 (not commissioned)
- P11: NOT SUPPORTED in S2 (not commissioned)

## Graded cohort

- Graded issuer group: **alibaba** on adr_baba (SEC:US-XNYS-BABA, MARKET_US).
- CENSUS-ONLY: tencent issuer group (00700) — counted, listed, abstained, never graded.
- CENSUS-ONLY: HK legs (9988, 0700) — never graded (V0 row 14).

## Membership table (protocol, h, split, count, membership_sha256)

| protocol | h | split | count | membership_sha256 |
|---|---|---|---|---|
| P04 | 5 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P04 | 5 | TUNE | 2 | 3987f51b24bc47ce9961206ffef580f810ea634964864f2f9659f5705dd24a0b |
| P04 | 5 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P04 | 21 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P04 | 21 | TUNE | 2 | f392d0c6efe30cc44af8406d72542a70ac4a559fc989ccdf287cbd71cdfbf298 |
| P04 | 21 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P04 | 63 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P04 | 63 | TUNE | 2 | 7fbe134bb1e72f6a5635a547cb6d562b1b5364f59168e67b12321ee64bf805c7 |
| P04 | 63 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 5 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 5 | TUNE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 5 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 21 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 21 | TUNE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 21 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 63 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 63 | TUNE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P05 | 63 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 5 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 5 | TUNE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 5 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 21 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 21 | TUNE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 21 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 63 | TRAIN | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 63 | TUNE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| P06 | 63 | QUARANTINE | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

## Collapse receipts (metadata only)

- literal row count pre step 0: 7
- kept after step 0: 5
- events after step 2: 3
- events of record after step 3: 2
- excluded-and-listed [step0_admission] 12291963 (tencent): exact-token selection refused: token '40700' is not '00700'
- excluded-and-listed [step0_admission] earnings.parquet#ticker=BABA (alibaba): TIMESTAMP_QUALITY EVENT_DATE is not an admissible t_avail (IL §1); the row is listed, never an anchor
- excluded-and-listed [post_step2_coverage_exclusion] 12295308,12295380,12300619 (alibaba): E0 gap 10: HK placement coverage misses general-mandate placings; the one programme (one event under REG P05) is excluded and listed, never silently dropped

## DEVIATIONS and S0-difference log

- Tencent counter local_code: the packet's prose examples say `0700`; the profile's `hkd_0700.local_code` is `00700` (tencent.yml). The exact-token rule is applied against the profile local_code; the packet's own anchors (news_id 12280990; false positive 12291963, token `40700`) reproduce exactly under it.
- Line drift: S0 cites trial_ledger L48/L126/L159/L210/L214/L242/L296 and grading_stats L56/L121; at BASE these sit at DEFAULT_PATH L49, log_trial L146, log_declared_budget L202, literal_n L253, effective_n L257, declared_budget L287, register_trials L296, wilson_ci L56, block_bootstrap_ci L121. The APIs are identical; only line numbers drifted. S0 was not edited.
- The receipt's commit identity is carried by `input_ref` + the pinned INPUT_MANIFEST blob ids (content-derived, byte-stable); the branch head at run time is never stamped, so `--check` byte-compares stay stable. The seal commit itself is named by the seat when it integrates the REG §6 row, which stays empty in S2.
- Census-only episodes (tencent) carry split labels and appear in the membership manifests with graded_leg NONE — census only (V0 row 14); they never enter any graded honest-N.
- The near-token probe also matches a counter code's unpadded key form (e.g. `0700` for `00700`) so the packet's false-positive class (token `40700`) stays visibly listed.

## Receipts

- prereg_digest_sha256: `38b564eadc8f55d8511aa69d5894d224024383f6cd714e071a7a478709f06943`
- S0 blob ids: REG `1b891b3c60a54bc5eba94cb7fafa8fec6ffb6ea6`, IL `6ec4b097ce3fd24261da12061b3418fde945efaf`, SL `c06a91beee22626eab1912aaa8a3baa6856913a2`
- trial ledger path: `research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl` (written at evidence time, never by this builder)
