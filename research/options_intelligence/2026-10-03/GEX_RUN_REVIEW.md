# Independent review: published GEX run arithmetic

**Verdict: PASS for the stated bounded artifact-level claims, with a raw-float precision qualification below.** No blocking arithmetic error identified. Review date: 2026-10-03. Reviewed carrier head: `626848e3bef0ab799b54380d204641256de94220`. This is a read-only arithmetic and evidence review, with an added review document and independent checker; it changes no production input, gate, ranking, model, or provider session.

The strongest supported conclusion is that `gex_confirm_verdict` contributes zero to the C1 score and rank of this exact published 69-row buy pool under the pinned source. The whole F5 family contributes through other admitted members. These claims must remain separate.

## Evidence identity

| Artifact | Verified identity |
|---|---|
| Original full published board, fetched independently by immutable GitHub blob | Git blob `bae9b8dac3b1cfefe9912e58c3d524f8c2007a1d`; 2,193,078 UTF-8 bytes |
| Incumbent fusion source copy | Git blob `210e070103b36f10bbbf19981420a17bb9fdc4fc`; SHA256 `7baf8f0bcc7b05bbc1c89031ddc052b00558daed4b887f791d19200505ce5baf` |
| Board-rank source, fetched and independently hashed | Git blob `26c29080c7d5cedd20d9a540aa11964128261ad7` |
| W3 sessions, fetched and independently hashed | Git blob `62632d8863122450e4ae169406f75b8c8cde202b` |
| Board input extract | SHA256 `af00367aeb4ba9fa64569eacfcac98926e5dcf46f863e1e99348d5d81938972e`; Git blob `378a5d4ee359790c8b1b980a5515c3750eadc001` |
| Archived coverage JSON extract | SHA256 `efc0e6965759a1f1c85061c9983f224cc5e8abac4cf8d2255a88c79ba4f67c32`; Git blob `01defb78fb159d9dbd50a42c6cfba983091954a5` |
| Audit script | SHA256 `774459bfc1a88296d9b643e9732392b8f91eccc91850bb1440a547589322312d`; Git blob `ad9430ef992bab30007cab29c5196bd94e182455` |
| Audit narrative | SHA256 `572121c6c56e39b37b6dded2c3d6f98eab12712d5d3ea0856b521be3a7867655`; Git blob `c0da39db0b53f058d03325a7c587885a91840b40` |
| Reference output and independent normal script reproduction | SHA256 `130e2f352889815047bf392cacec4ecfbc5e813e08dc627dcf4a404cc71122a3`; reference Git blob `6a5b15126fe75858466fd0d95e7d02c01554cbab` |

Repository: `mastermindx-market-intelligence/macro`. Pinned board snapshot: `3d9969c15bba0f57b64da7592c0731cc8a0f2eac`. The independently fetched board identifies `as_of=2026-10-01`, emitter `build_stock_library`, emitter time `2026-10-03T08:15:30+00:00`, and pair `f9f4108104c84918bacc5ff06805be40`.

## Checks that go beyond replaying the implementation

The normal supplied command was reproduced into `/tmp/gex-run-review-reproduced.json`, exited 0, and produced the exact reference-output SHA256 above.

A separate reviewer calculation did **not import the pinned module**. It is preserved as `gex-independent-replay.py`, a standard-library checker using hash-pinned adjacent evidence extracts. It extracted the eight registered members from the preserved raw fields, used the declared mappings/signs, and admitted a member on this single evaluable night only when at least half the rows were non-null and at least two non-null values differed. For a present member value `v`, it computed its percentile with rational arithmetic as `(2L + E + 1)/(2N)`, where `L` is the number of present values strictly below `v`, `E` is the number equal to `v`, and `N` is the number of present values. This pairwise-count derivation is independent of the producer's sorted tied-block loop. It then averaged surviving members within each family and present families within each row, multiplied by 100, and applied the producer's display rounding.

The independent calculation matched all 69 published one-decimal scores, all 69 ranks, all published six-decimal member percentiles, all two-decimal family contributions, family counts, admitted members, and the empty duplicate-collapse result. It also independently reproduced the rank-displacement and top-30 statistics for all three comparisons. The exact rational vectors found no within-family duplicates; the producer's nine-decimal vector comparison therefore does not change this pool.

Input projection was independently checked against the full fetched immutable board. All 69 projected rows matched exactly, including field presence/absence, the raw fields consumed by extraction, stage/rank, score, and member/family receipts. `as_of`, `emit`, `staleness`, and the retained ranking metadata matched exactly. Omitted display fields do not enter the inspected extractor. The optional signal-verdict fallback remains outside an upstream reconstruction, but every published replayed percentile and score agrees with the preserved raw-row route on this artifact.

The board-rank source independently confirms the stage/scored-first/descending-published-score/ticker sort and one-decimal score publication. All five stage buckets occur: 11 live, 41 setting_up, 3 ran, 5 basing, and 9 blocked. As a discriminating check, using unrounded raw scores in the independent calculation would change **four** published ranks. Matching the producer's rounding is therefore substantively tested, rather than an unexercised annotation.

## Floor, arithmetic, and comparison findings

| Member | Present rows | Distinct oriented values | Admission |
|---|---:|---:|---|
| alpha | 69 | 63 | Admitted |
| off_high | 69 | 60 | Admitted |
| tier_cascade | 48 | 4 | Admitted |
| sue_fresh | 69 | 2 | Admitted |
| smartmoney_add | 69 | 2 | Admitted |
| insider_cluster | 69 | 2 | Admitted |
| gex_confirm_verdict | 21 | 3 | Below presence |
| news_burst | 69 | 2 | Admitted |

GEX has 11 caution, 3 confirm, 7 neutral, and 48 missing readings. Coverage is exactly `21/69 = 0.30434782608695654`, below 0.50. At least 35 present rows are required on this population. Its three observed categories satisfy the variation requirement; presence is the failing gate. No absent reading becomes a neutral reading in the baseline. This missingness claim concerns GEX: the incumbent deliberately derives several other flag members with Boolean defaults, as the narrative/source disclose.

| Fixed-pool comparison | Literal producer float scores changed | Published scores changed | Rank moves | Maximum move | Mean absolute move | Top-30 replacements |
|---|---:|---:|---:|---:|---:|---:|
| Remove GEX from frozen admitted members | 0 | 0 | 0 | 0 | 0 | 0 |
| Remove entire F5 family | 69 | 68 | 42 | 11 | 1.536231884057971 | 2 |
| Synthetic missing-to-neutral replacement | 69 | 69 | 40 | 10 | 1.5072463768115942 | 3 |

**Precision qualification:** the whole-F5 count of 69 uses the incumbent's literal floating-point `!=` operation. Independent exact rational arithmetic changes 68 scores. MMSI's rational score is identical before and after F5 deletion; the two producer float paths give `45.652173913043484` and `45.65217391304348`, a difference of approximately `7.105427357601002e-15`. The 69th raw inequality is numerical rounding noise, not a mathematical change in the vote. This does not alter the 68 published-score changes, 42 rank moves, or zero GEX-specific result. When citing the raw count, label it as literal producer float inequality, or use the rational count of 68 with its stated method.

Removing a member that was not admitted is structurally an identity operation. Its zero-change assertion is not, by itself, discriminating proof. Here it is supported by independent presence counts, source-floor inspection, immutable-board projection, producer admission receipts, and exact replay of all published member/family contributions. Whole-F5 deletion and the synthetic mutation provide distinct nonzero checks; the whole-F5 diagnostic also matches the artifact's stored producer diagnostic.

The synthetic mutation changes 48 unknown observations into measured zero-category readings, increases apparent GEX coverage to 100%, and admits it into F5. A zero oriented category does not generally produce a zero cross-sectional percentile. With 11 caution, 55 neutral, and 3 confirm readings after this mutation, the rational neutral percentile is `39/69`, approximately `0.5652173913`. The F5 member average and subsequent family average therefore change. This explains the nonzero result without claiming any market benefit, actual observation, or lawful repair. All three comparisons hold the population and published stages fixed; none establishes a changed selection/cohort outcome.

## Archived 62-row observation

The independently fetched immutable W3 sessions blob contains the exact preserved session with observation fingerprint `cf0059c8da553ea5ad07bdf8cc4ce8252ca504e78dcea17b164b39f37fe3627b`, 62 buy rows, and pending H10 outcomes. The preserved coverage extract names parquet Git blob `d9ddf422dd104eaab798190fab273cac17261508` and GEX coverage `0.370968`, status `below_presence`. The independently verified 69-row published board has different population size and coverage despite sharing `as_of=2026-10-01`.

This reviewer checked the coverage extract and its hash, but did not independently perform a second binary parquet decode. The parquet decode/identity verification remains the preserved producer receipt described in the audit. The differing population identity is independently supported by the source session and full published board. Rounded archived coverage is not an independently reconstructed exact count here. No eventual outcome values were read or inferred.

Rejecting a date-only join between these observations is justified. The evidence does not show that the archived store is erroneous or authorize replacing its frozen record with the later board. Revision/population identity and consumer-availability lineage remain necessary for later causal work.

## Acceptance boundary and follow-on use

**PASS:** artifact-specific GEX presence exclusion and zero direct C1 vote; exact published score/rank reconstruction; whole-F5 distinction; synthetic missingness witness; incompatible same-date population identity; appropriately qualified fit-free arithmetic evidence.

**Not accepted by this review:** an options-free incumbent claim; upstream options-independence claim; proof of original market-data provenance or freshness; independent stage/cohort reconstruction; signed binary/container execution attestation; real consumer receipt time; browser deployment; predictive value, profitability, or causality; permission to enable GEX, relax floors, substitute missingness, delete F5, or change production.

The primary script executes the incumbent source for the arithmetic, so its statements that it recomputes the producer's operations should be understood as exact source replay, not a second independently authored implementation. The separate reviewer derivation above supplies the independent arithmetic check on this artifact. Published receipts are external fixed expectations, and the full-board projection check addresses the possibility of a self-consistent but invented extract. The inspector's assertions are research validation under the documented normal Python command; they are not security or production enforcement gates.

No blocking finding requires changes. B4 may close its initial run-level arithmetic uncertainty for this exact immutable artifact while retaining the broader lineage, availability, and predictive-evaluation questions already identified in the audit. Preserve the precision qualification when reporting raw changes.

## Reproduce the separate checker

```bash
python gex-independent-replay.py --output /tmp/gex-independent-replay.json
```

Checker SHA256: `74ef9329d96f1292aa4c2af19ed9654034b53230939da80504ffcf8c53bbc345`. Output SHA256 under the documented normal Python command: `acfa38c2bb2551e25ea7e69965b209b65f02e28b3fd60a26d1e0bc4c9c54db1b`. The checker asserts the four-rank unrounded-sort witness and the exact rational change counts (68 whole-F5, 69 synthetic mutation). It compares published scores, ranks, and displacement/churn fields to the immutable published receipts and reference output. It validates archived-extract identity, date, count, and coverage; independently fetched full-board projection and source-session checks remain the review evidence recorded above, rather than being claimed as online checks repeated by this local command.
