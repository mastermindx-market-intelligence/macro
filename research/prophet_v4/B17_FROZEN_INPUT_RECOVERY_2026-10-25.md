# B-17 frozen-input recovery — 2026-10-25

Workstream: WS:PROPHET-US-V4-RECOVERY
Wave: b2
Disposition: **STILL_LIVE — input recovery and bounded replay; no acceptance or seq2**

## What this changes

B-17 needs the intersection of the early union and the actual admission gate over the original frozen study. The October 24 census found 33 later origination snapshots, all after the original price edge. This recovery locates the earlier immutable Git inputs, implements a research-only verifier and point replay, and leaves unavailable history explicitly unknown.

The implementation calls the existing `engine.prophet_bridge.select_candidates(n=None)` and `engine.us_early_turn.union_admission`. It introduces no runtime selector, episode store, producer, ranking authority, or production replay. B2-1's separate correction patch remains Draft #10176 at `228c25d37617a7217c8f65f1613ade701a2fe01a`.

## Frozen identity and recovered evidence

| Item | Bound identity or observed result |
|---|---|
| Original study run | 2026-08-11T12:36:43+00:00 |
| Frozen price edge | 2026-08-10 |
| Study code recorded by the original artifact | `ef43e77997659ace2534232c015e96179d0f3fba` |
| Original signal-store origin/main | `45dae5dba0a252ceaef05a8ab8c17decb73d99d8` |
| Frozen result and episode artifact read ref | `228c25d37617a7217c8f65f1613ade701a2fe01a` |
| Current rule source ref used by this run | `4e817e7a1b83ffed1ae8ec22a3911c92ac541198` |
| Signal files recovered | 241, with immutable Git blob identities and SHA-256 receipts |
| Primary priced panel | 240; SATS remains unpriced/excluded; HL and UEC remain separate add-ons |
| Frozen episode artifact | 39,877 rows; original C0 denominator 7,918 |
| Original C0 date span | 2014-12-04 through 2026-08-10 |
| Price candidates qualified against recorded anchors | 240 / 240 |
| Exact-path GitHub commit history | 579 revisions; first commit 2026-06-16T10:12:23Z |
| Daily archive sample | 57 complete original buy[] snapshots; 32 distinct source-as-of dates, 2026-06-15 through 2026-08-10 |
| C0 episodes with a complete 34-session admission-date window in this sample | 0 / 7,918 |
| Full shipped-roster coverage / lead | Unknown / unknown; both report fields are null |

The frozen results and episode files are read from their immutable Git objects. Each source receipt records ref, path, Git blob, byte length, SHA-256, and transport. Signal and price candidates come from the original signal-store source tree, not present-day caches.

Every price candidate matches the original artifact's row count, first and last session, every frozen episode's close, and every frozen episode's session position after the original normalization. These checks strongly qualify the recovered candidates. **The original study did not retain a digest of each complete price file.** This recovery therefore does not assert byte identity to the original working OHLC files or proof of unseen high/low or non-episode values. That limit matters because the union consumes more than the recorded episode closes.

The local clone is shallow. Its path history returned only 28 commits, and an unrelated `git log --all` encountered a missing object. Neither was treated as absence evidence. The archive index instead preserves all 579 commits returned by the GitHub commits endpoint for the exact source ref and `site/factordata/us_standouts.json` path, through the empty terminal page. For the bounded replay, the index chooses the last commit per UTC publication day. This samples 57 snapshots; it does not inspect every intraday revision or prove that other stores lack earlier material.

## Ruler replication and corrected label

The original R2i **C1-relaxed** row reproduces exactly:

- 4,800 of 7,918 C0 episodes covered: **60.62%**.
- Median lead: **12 sessions**.
- 19 same-session cases count as covered.

This is the C1-relaxed baseline. The frozen artifact does not contain a measured union or shipped-roster row. Older B2 narrative using “naked union” for this figure must not be inherited as measured union evidence.

The implementation preserves the original inclusive zero-to-30-session ruler, same-ticker session positions, and latest qualifying candidate when several precede one C0 anchor. Its deduplication helper preserves the original keep-first, ten-session gap rule. The tested first-eligible-surface helper uses the date the union and gate are jointly observed eligible, rather than backdating admission to the union's earlier signature. Missing or unknown gate observations cannot prove first visibility. No first-visibility result is asserted for this archive sample.

## Original-cutoff point intersection

The exact cutoff snapshot was committed at **2026-08-11T12:24:47Z**, before the study run, and carries source-as-of **2026-08-10**:

- Ref: `cac3c23880f869bb3d63708e8814841c5811593b`.
- Git blob: `aad158ef8f945b7af637bfb7c680a10d4e62900d`.
- SHA-256: `6f02ac0fbba70640eb3f7e13949ea55af13283b193627f513151dae77bd6addb`.
- Original buy[] population: **69 rows**.
- Current pinned canonical selector, without its downstream count cap: **42 admitted names**.
- Intersection with the original 240-name priced panel: **6 names**.

| Panel name admitted by the selector | Most recent union signature | Age in sessions | Live under the existing three-session window |
|---|---|---:|---|
| DHR | 2026-05-20 | 55 | No |
| META | 2026-06-30 | 28 | No |
| ORCL | 2026-07-30 | 7 | No |
| STLD | 2026-07-14 | 19 | No |
| TKO | 2026-07-30 | 7 | No |
| WBD | 2026-08-04 | 4 | No |

All six union evaluations returned known results; none is live at the cutoff. This is a **single source-date intersection under the current pinned rules**. It is not zero historical coverage, a trading result, historical served membership, or evidence that users saw these inputs on August 10. The commit is known on August 11; source-as-of and availability time remain separate clocks. The report retains both and leaves coverage and lead null.

## Why the full measurement remains open

The recovered admission sample begins in June 2026, while the original frozen population spans years. The 34-session check is a necessary input-availability screen for the 30-session candidate lookback, three-session union liveness, and current session. It is not sufficient proof of complete publication history, deduplication context, or first visibility. Even under this source-date screen, no original C0 episode has all dates supplied.

Recovering the 240 study names' historical OHLC alone cannot reconstruct the producer's full buy universe. The upstream board uses full-universe composite ordering, per-sector and overall caps, dual-class deduplication, earnings blackout, and non-price/event inputs including surprise, insider/revision evidence, regime and themes. Downstream `n=None` removes only the selector cap. A reconstruction restricted to study names would silently change the gate population. Missing or unbuilt non-price evidence must not be filled with neutral values.

Do not invoke `build_stock_library.main(now=T)` as a historical replay: its current reads, host-clock uses, collectors and writes are not a point-in-time input contract. The observed `name_score/us_calls` archive has a pre-August-14 host-clock shift and lacks persisted bar-as-of; `conviction_us` is a basket aggregate. Neither presently supplies the missing per-name, full-population admission history.

The next bounded implementation step is to recover a historically bound full-population source for the missing dates, or build a pure producer-input adapter only after every required historical dependency and availability clock is qualified. Keep the original denominator, rulers, unknown states and upstream population rules. A changed window or population would require an explicit measurement-scope decision; it cannot silently close B-17. Full-population measurement and independent scientific adjudication still precede seq2.

## Validation and reproduction

The focused suite completed **28 passed in 1.10 seconds**. It checks canonical selector behavior, unknown versus known refusal, incomplete reconstruction, legacy defaults, source/availability clocks, future input poisoning, immutable object identity, exact ruler boundaries and deduplication, delayed gates, missing liveness evidence, unavailable union results, and refusal propagation. Explicit source-access denial stops the read operation rather than falling through to another client. The recovery also refuses a reader pointed at a different checkout: canonical imports and the recorded rule ref must bind the same implementation checkout. The focused suite includes that provenance regression.

The complete recovery run exited **0** in 107.86 seconds, qualified all 240 price candidates, read all 57 snapshots, reproduced the C1 baseline, and emitted the bounded cutoff replay.

Run from an isolated checkout with the original Git objects available:

```bash
python3 -m pytest tests/test_prophet_b17_frozen_input_recovery.py -q
python3 -m research.prophet_v4.b17_frozen_input_recovery \
  --archive-index research/prophet_v4/B17_ADMISSION_ARCHIVE_INDEX_2026-10-25.json \
  --report /tmp/prophet-b17-recovery.json
```

The optional `--github-fallback` reads absent immutable objects through the already authorized GitHub client and validates the returned bytes against their Git identity. It does not bypass an explicit access denial. The recorded run used that option. A checkout lacking historical objects may need it.

The report binds the checkout HEAD as `rule_ref` and receipts for the five canonical engine dependencies. A later research-only commit therefore changes that provenance field even when the five rule blobs are identical; do not confuse that expected metadata difference with changed input results. The recorded module SHA-256 must match the implementation bytes used to produce the report.

| Artifact | SHA-256 of committed file bytes |
|---|---|
| `b17_frozen_input_recovery.py` | `3d423e7cc8b1823a5a184b21b16b79741219bbb269e1e5efae87d70ff75c8d58` |
| `test_prophet_b17_frozen_input_recovery.py` | `3309c9064a7b647b789bc65d408a8ed7cbf5fc7326292b81a72ba77aa42a5d48` |
| `B17_ADMISSION_ARCHIVE_INDEX_2026-10-25.json` | `cbccb07847f70b854692db594c84ba5b8c251de25d6e38ae2ca67c6406179584` |
| `B17_FROZEN_INPUT_RECOVERY_2026-10-25.json` | `7bd9c2c081b9c5f0c2223cfc12915bc4514fb91b5e410a5a63dbfb4020d981e0` |

The report's `history_index_sha256` separately hashes the parsed index serialized with sorted JSON keys; it is a semantic-input digest, not the pretty-printed index file digest in this table.

## Review and custody boundary

The current recovery session owns this B2 continuation under Chris's no-owner-wait directive. Original source review `prophet-v4-b2-withdrawal-review-20261025-01` remains terminal rc1/HTTP429 and STOP WITHOUT ACCEPTANCE. The single newly authorized non-Qwen retry was run `prophet-v4-b2-withdrawal-review-20261025-04`, pinned to the GLM pool, model auto within that pool, excluding the MiniMax author pool, for exact source head `228c25d37617a7217c8f65f1613ade701a2fe01a`.

Fabric returned `MANUAL_ROUTE_UNAVAILABLE`, `error_code=INVALID_ARGUMENT`, `execution_absence_proven=false`, and `retry_allowed=false`. No controller or reviewer verdict was returned. That refusal is recorded on Draft #10176; no extra attempt, acceptance, self-approval, merge, or production change follows from it. This implementation is separately reviewable and does not substitute for the independent B2 review gate.

## Source references

- [Frozen result artifact](../prophet_us_audit/early_admission_bakeoff_results.json)
- [Frozen episodes](../prophet_us_audit/early_admission_bakeoff_episodes.parquet)
- [Original study program](../prophet_us_audit/early_admission_bakeoff.py)
- [B2 disposition and mutation contract](B2_0_DISPOSITION_AND_MUTATION_PACKET_2026-09-04.md)
- [Complete archive index](B17_ADMISSION_ARCHIVE_INDEX_2026-10-25.json)
- [Recovered-input and point-replay report](B17_FROZEN_INPUT_RECOVERY_2026-10-25.json)
- [Research implementation](b17_frozen_input_recovery.py)
- [Focused tests](../../tests/test_prophet_b17_frozen_input_recovery.py)
