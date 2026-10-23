# W0/W1 vintage and entry laboratory

## Decision

**The disagreement can now be divided into actionable mechanisms. Replacing every stored entry with the latest open would combine several different accounting changes and remains unjustified.** The existing owners can implement a qualified migration with immutable original records, separate amendments and explicit unresolved states. A focused change to the existing benchmark extractor can stop discarding opening prices prospectively. The available benchmark history still cannot support a real aligned-opening counterfactual.

This laboratory extends the accepted October 9 census without modifying its calculations or any production source. The study pin remains `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. R0 #6871 remains a separate incumbent carrier. These results do not revive its rejected original-basis claims or certify actual execution.

## 1. Field-level decomposition of every relevant entry

The prior analytical CSVs were accepted only after their hashes matched the original manifest `80f38bdd75cff63d87190081c4edf027bdce5d564dc23740f9203750b70209c4`. The new collector re-applied the exact pinned pure `_t1_fill_detail` and compared it with the prior calculation. It examined all **1,948 unique stored latches**, representing **2,632 latch-bearing episode rows**. Every current derivation agrees with the accepted CSV within the existing float tolerance.

All **656 changed unique entries** use the **same entry session** in the original latch and current derivation. Missing or shifted session dates do not explain this particular discrepancy population. The original 933 count contains repeated use of an entry across definitions; it is not 933 independent trades.

| Current-field classification | All changed unique entries | Changed entries within the 289 matured V4 episodes | Meaning |
|---|---:|---:|---|
| Stored HL2 equals current HL2; current code now chooses open | **274** | **61** | Changing the preferred basis alone reproduces the entry difference on the current bar. |
| Stored value equals current raw-plane value on the stored basis | **206** | **35** | A numerical match to an existing different plane; it does not certify the original raw basis. |
| Neither comparison explains the stored value | **176** | **40** | Requires historical source evidence or remains unresolved. |
| **Total changed** | **656** | **136** | All current changed derivations use open. |

Of the full **289 matured V4 episodes**, **153** have unchanged derived entries and **136** differ. The original latches use **216 opens and 73 HL2 proxies**; all current derivations use open. All 73 HL2 latches carry the original corrupt-bar flag. The current corresponding bars do not trigger that flag. One stored HL2 happens to equal the current chosen open within tolerance, so 72 of the 73 HL2 rows fall in the changed population.

These are mutually exclusive *current-field* classifications in the order shown. They are not causal corporate-action labels. A name may have both a healed opening field and a price-scale change; the historical comparison below keeps that possibility visible.

**Evidence:** [vintage_results.json](vintage_results.json), [entry_comparison_rows.json](entry_comparison_rows.json), [collect_vintage_evidence.py](collect_vintage_evidence.py).

## 2. What historical price evidence was actually recovered

The repository is shallow. The bounded search found **82 reachable commits affecting the adjusted or raw stock-price paths**, beginning with `69268b06502cdbfb9cdf9ae24e6e64663b17c8ed`, committed **2026-08-23T22:55:42Z**. For each changed entry and each matured V4 entry, it inspected the nearest such commit on either side of the stored `latched_asof` timestamp.

Every witness commit was checked for ancestry to the study pin. Its `committed_at` is explicitly a **Git committer clock**. The compared `latched_asof` is explicitly the **producer field in `entry_latch.parquet`**. Their different meanings are retained in the output. A matching prior blob is useful recoverable source evidence; neither clock proves that those bytes were served to a user, known to a trading agent at entry, or executed.

| Witness qualification | 656 changed unique entries | 289 matured V4 episodes |
|---|---:|---:|
| Matching source bar in the nearest reachable commit before the latch clock | **385** | **239** |
| Only the nearest later witness matches the stored value | **186** | **33** |
| Neither of these two bounded witnesses matches | **85** | **17** |
| **Total** | **656** | **289** |

All 385 earlier changed-entry witnesses match both the stored-basis value and the current code's derivation on the historical bar. The same is true for all 239 earlier V4 witnesses. This removes substantial ambiguity about *what a historical source bar contained*. It does not fill the missing original publication or vendor-availability fields.

The following shape classification compares each exact entry bar with the pinned current adjusted bar. It prefers an earlier matching witness when one exists; otherwise it uses the matching later witness.

| Observable change shape | Matching witnesses for changed entries | Matching witnesses for matured V4 |
|---|---:|---:|
| Only open changes; high, low and close remain equal within tolerance | **317** | **75** |
| One positive scale factor fits all four OHLC fields | **179** | **28** |
| Multiple fields change without one common scale | **26** | **8** |
| OHLC already identical in the matching witness | **49** | **161** |
| **Total with either matching witness** | **571** | **272** |

The 49 unchanged bars in the first column are possible because a later witness can retain the original HL2 value even after its opening field has healed. A stored HL2 and the new preferred open can differ on an otherwise identical witnessed bar.

For prior-to-latch V4 witnesses alone, the corresponding counts are **75 open-only, 19 uniform-scale, 8 mixed, and 137 identical**. Eleven-session neighborhoods around the entry were also inspected where available. A monotone common scale across such a neighborhood is retained as arithmetic evidence, with exact ratios and bars. It is never renamed a verified split or dividend adjustment.

**Evidence:** [historical_witness_rows.json](historical_witness_rows.json), [historical_shape_cases.json](historical_shape_cases.json), [supporting_sources.json](supporting_sources.json), [vintage_inputs.json](vintage_inputs.json).

## 3. Why the nearly unchanged aggregate conceals meaningful differences

Holding the accepted current-at-pin exits and benchmark marks fixed, the V4 entry substitutions produce the following decomposition:

| Current-field group | Episodes | Mean change in excess return within group | Contribution to the overall 289-row mean change | Win/loss sign changes |
|---|---:|---:|---:|---:|
| Basis-only comparison | 61 | −0.1967 pp | −0.0415 pp | 7 |
| Raw-plane numerical match | 35 | +0.8788 pp | +0.1064 pp | 2 |
| Other unresolved current-field difference | 40 | −0.4038 pp | −0.0559 pp | 7 |
| Unchanged within tolerance | 153 | Approximately zero | Approximately zero | 0 |

The components largely cancel. Their sum is the previously reported approximately **+0.0090 pp** aggregate change, while **16** outcomes change sign. Ten original winners become current-entry losses and six original losses become current-entry winners.

This is an arithmetic decomposition of the earlier production reconciliation. It is **not** a correction to original economic P&L. Both variants still use current-at-pin exits, and the new historical witnesses do not supply an original complete entry-to-exit price vintage for every episode. It is also not evidence that choosing the later open improves selection.

## 4. Six inspectable cases that drive the engineering rules

Cases were selected for distinct source mechanisms, not for investment outcomes. The complete exact bars, input identities and relevant source-title leads are in [supporting_sources.json](supporting_sources.json).

**000962.SZ, September 3 board / September 4 entry:** the historical source before the latch clock has open **59.80**, outside high **55.80** and low **51.00**. The stored HL2 is **53.40**. Current high and low remain the same, while open is **55.30**. This is a direct example of a corrupt opening field leading to a latched proxy and a later valid opening field changing the preferred basis. Retain both records and label the original proxy honestly.

**600016.SS, September 1 board / September 2 entry:** the earlier matching bar has open **3.6300001**; the current adjusted open is approximately **3.5145447**. All four OHLC values fit a factor near **0.968194**, also consistent across the retained local neighborhood. Current raw open numerically matches the stored entry. This supports a scale-change diagnosis, while the owner still needs a certified adjustment bridge before labeling its economic cause.

**301489.SZ, August 28 board / August 31 entry:** the stored and earlier witnessed open is approximately **120.5100**. Current adjusted open is approximately **112.9565**, and current raw open is **113.00**. Other fields also have a small scale change. A single factor applied to all old OHLC does not explain the whole entry-bar change. This case rules out a migration that classifies every raw/adjusted difference as one harmless common-scale rebase.

**002290.SZ, August 20 board / August 21 entry:** the latch stores approximately **62.68**, while current adjusted and raw opens are approximately **67.89**. Neither of the bounded historical witnesses recovers a matching stored-basis bar. The honest state remains unresolved; a latest-raw substitution would conceal it.

**300803.SZ, July 21 board / July 22 entry:** the latch stores **83.00**. A later reachable August 23 source witness also contains **83.00**, while the current adjusted and raw opens are approximately **57.24138**. The observed common scale is near **0.689655**. A stored August 27 title concerns a half-year profit distribution and capitalization proposal. The title is a relevant lead, but contains no structured ex-date or transformation ratio. It does not certify this numerical transformation, execution economics, or the historical R0 claims.

**301000.SZ, August 18 board / August 19 entry:** the stored HL2 is approximately **24.505**, while the current open is approximately **25.610**. The first matching reachable witness occurs after the stored latch clock and already contains the same OHLC as current. It recovers the proxy value but cannot establish the original corrupt-open bytes. This is why a later numerical witness must not be upgraded to prior source custody.

The raw-plane blobs at those same historical witnesses were also inspected. They show **000962.SZ raw open changing 59.80→55.30**, **301489.SZ raw open changing approximately 120.51→113.00**, and **300803.SZ raw OHLC changing by the same approximately 0.689655 scale**. By contrast, 600016.SS raw OHLC remains identical while its adjusted values change. These observed differences directly refute treating the latest raw file as an immutable original price receipt. They do not identify which vendor or repair operation caused each change.

The existing filings table has **98,195 rows**, with **377 action-related title matches** across 303 issuers. Within the changed-entry issuers there are **58 title leads across 42 issuers**, including 13 issuers with changed matured V4 entries. No structured ex-date, distribution ratio, split factor or verified event-to-price bridge exists in this table's columns. The title leads are retained for a future bounded extraction by the existing company-intelligence owner; no causal labels were assigned here.

## 5. Benchmark opening data: exact blocker and tested candidate seam

All **38 reachable versions** of `data/china/510300.SS.parquet` contain only close and volume. None has a valid opening observation. The current wide China-search close matrix has **1,289 rows and 1,823 stock columns**, with no exact tested CSI300/510300 alias column. The current derived China-market-state object includes the benchmark symbol, but no opening fields. The filename inventory finds no alternative matching OHLC store. This is a bounded repository assessment, not a claim about every external database or untracked machine file.

The missing field is explained by a concrete source seam. In pinned `collectors/china_prices.py`, `_extract` at lines 90–98 explicitly projects the provider frame onto **`Close` and `Volume` only**. The download method already calls its existing provider; no new source owner is required merely to preserve optional fields present in that response.

[benchmark_retention_probe.py](benchmark_retention_probe.py) AST-extracts that exact pure method and feeds it synthetic provider frames. Its research-only candidate retains optional Open/High/Low while preserving required Close/Volume behavior. **Nine checks pass**, covering:

- Exact incumbent loss of OHLC that was present in the input.
- Unchanged values for every existing close/volume consumer.
- Equivalent single-instrument and provider MultiIndex layouts.
- Legacy close-only inputs remaining close-only and unavailable for opening marks.
- Corrupt-range, zero, infinite and NaN opens staying visible/refused without close substitution.
- Continued refusal when required Close is absent.

**Implementation decision:** extend the existing benchmark extractor contract; retain source observations and separate quality flags; attach source and basis/vintage identities; accrue valid openings through the existing collector. Any historical refresh is a distinct bounded acquisition task under that owner. Never fabricate historical openings from closes. Retaining a synthetic frame proves the extraction seam and backward compatibility; it does not prove present upstream field coverage. Existing adjustment guards, source rights, complete-session enforcement and storage behavior remain integration requirements.

The actual clock-only opening comparison remains `UNAVAILABLE_NO_VERIFIED_BENCHMARK_OPEN`. A missing comparator is an outcome of this laboratory, not a zero-effect estimate. [benchmark_versions.json](benchmark_versions.json) and [benchmark_retention_checks.json](benchmark_retention_checks.json) retain the receipts.

## 6. Minimal migration and fill contract

Use the existing decision, entry-latch and outcome owners. The research prototype in [fill_vintage_contract.py](fill_vintage_contract.py) is pure and has no database or side effects.

| Record or transition | Required implementation behavior |
|---|---|
| Existing original latch | Preserve all seven original fields and derive a stable identity. Missing source provenance becomes `LEGACY_SOURCE_VINTAGE_UNVERIFIED`, not a rewritten entry. |
| Recovered historical witness | Attach source commit/blob/row identities, the exact bar, Git clock and relation to the latch clock. Keep `HISTORICAL_SOURCE_WITNESS` distinct from source-availability or execution proof. |
| Basis-only heal | Add a separate later-open mark or entry-assumption correction, with the original HL2 proxy visible. Do not call the proxy an exact timed fill. |
| Uniform scale | Identify old/new price vintages and a supported transformation before producing normalized economic comparisons. Keep the originally published price intact. |
| Mixed revision | Require field-level review or remain unresolved. A one-factor normalization is insufficient. |
| Unknown original source | Keep the original value and explicit uncertainty; do not infer custody from numerical equality to current raw or from a Git timestamp. |
| Corrected record | Append a separately identified event referring to the original, with reason and recording time. Exact replay is idempotent; a second original with changed content is refused. |
| Comparable return label | Require aligned stock/benchmark entry and exit anchors, exact sessions, consistent within-instrument price basis/vintage, source availability at grading, and a publication clock preceding the assumed entry. |

The prototype's strict daily-snapshot comparator conservatively requires the same source blob for an instrument's two endpoints. A production owner using multiple immutable chunks should replace that with an equally strict shared version-manifest proof that covers both endpoint blobs; it must not relax to an unverified string label. Market marks remain `MARK_ONLY`. Actual execution, corporate-action accounting, legal fill feasibility and transaction costs require their separate receipts.

**Eighteen executable contract checks pass.** They reject close-as-open substitution, unmatched exit dates, HL2-as-exact-time, mixed basis or source vintages, source availability after grading, Git-clock substitution, missing/late publication clocks, original overwrite and tampered corrections. They also preserve all **1,948 actual legacy latch snapshots** without automatically upgrading the 206 raw-plane numerical matches. [vintage_contract_checks.json](vintage_contract_checks.json)

Two synthetic counterfactuals resolve a common design ambiguity. First, changing a corrupt open to a sane open can leave the old HL2 unchanged while changing the preferred entry assumption. Second, scaling **both** a 100→110 price path by 0.8 yields 80→88 and preserves its 10% return; combining old entry with new exit yields −12%, and combining new entry with old exit yields +37.5%. These are arithmetic demonstrations, not empirical returns. They explain why neither a healed field nor an apparent scale factor authorizes a silent original-latch overwrite.

## 7. Reproduction, limits and handoff status

Run against the fixed repository and the accepted earlier analytical outputs:

```bash
python3 collect_vintage_evidence.py --repo /Users/chriswong/Documents/Cluade/macro-main --prior /tmp/mmx-cn-prophet-historical-20261009/results --out /tmp/mmx-cn-prophet-vintage-lab-20261009/results
python3 probe_supporting_sources.py --repo /Users/chriswong/Documents/Cluade/macro-main --results /tmp/mmx-cn-prophet-vintage-lab-20261009/results
python3 benchmark_retention_probe.py --repo /Users/chriswong/Documents/Cluade/macro-main --out /tmp/mmx-cn-prophet-vintage-lab-20261009/results/benchmark_retention_checks.json
python3 verify_vintage_contract.py --evidence . --out vintage_contract_checks.json
```

The final census process exited 0 in **23.06 seconds**; the supporting-source probe is bounded to its named files and representative witnesses; the final nine-check retention probe exited 0 in **0.69 seconds**. The local contract probe passed all 18 checks. Inputs and outputs are hash-bound. The existing production functions were not imported with their runtime dependencies, and no collector, paid/vendor request, data cache mutation, production write or new owner was introduced.

**Research conclusion:** W0/W1 can now be handed an exact classification and migration policy, executable failure cases, recoverable source witnesses and a tested field-retention seam. Certification of original economic returns remains gated on original publication/source custody, consistent endpoint bases, required corporate-action evidence and real benchmark opening observations. The research does not need to keep speculating about those absent facts; implementation should encode their absence explicitly and begin accumulating the required forward receipts.
