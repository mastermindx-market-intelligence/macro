# Independent pre-execution review — T13 metadata admission, 18 October 2026

**Disposition: APPROVE THE BOUNDED METHOD AND SOURCE for root adoption and a first execution only after the contract and diagnostic source are committed. No blocking defect found.** This approves a post-observation metadata diagnostic, not a predictive preregistration, feature join, study, fit, probability, or policy. FRED source purpose remains **UNKNOWN / operational HOLD** for the retained-series fitting/evaluation and probability-publication purposes.

## Reviewed identity and scope

| Reviewed file | Bytes | SHA256 |
|---|---:|---|
| `T13_SAMPLE_USE_CONTRACT_PROPOSAL_2026-10-18.md` | 15,404 | `8438120c615218d0b80d675b97759f1f8df2bb60b14f1ee7ec33584ff45afaa1` |
| `t13_sample_metadata_admission_proposal.py` | 18,761 | `a76d3b37e5cd365a33245143e1f28b68aac935225c8bf8ad4e433daa59b86db4` |
| Frozen `sample.json` | 6,359 | `944e0054b724aef775a5073ee8a1537779b464454a304acf4a4b396cd818a583` |
| Frozen `receipt.json` | 10,563 | `ad8a1f5fe92fb12690a25794f917619a2e113baaf9a07fc3f446207020340d4f` |
| Original T12 specification | 7,904 | `2eded5ca933da1eefd689b4e7985986f2bce79d3f9834592224a5b83a1fe0c29` |
| Original T12 builder | 17,212 | `b03462ae9e058939774cb10d4cd6b1782b826ac2cde5f79c5d33d5ef6259307e` |
| Original Stage1 source | 133,159 | `47ec425821c7a075dc4667171d9e75e8af213e0f088154c5fdb1cad419413714` |

The three original sources agree with the receipt's respective blobs `fe68838867982e845297aeb0daf518e0387120f9`, `0a0eecb98e743b780db1ee3b0382e268d592fa67`, and `76d231d6d12c8693cd07a2540b360c24f6c50b42`. Review used local reads, SHA256 calculation, AST syntax parsing and arithmetic inspection. **The diagnostic and its functions were not executed or imported.** No builder, label helper, price read, feature join, fit, trial ledger, Git operation, Studio operation, browser or network was used. Only this review file was written.

## Findings

1. **Positive-bound inversion is correct for the fixed sample.** Stage1 `cluster_window` gives `[first − 21, last + h]`; `merge_episodes` retains the earliest first and latest last. The builder clips only at the series ends. Therefore `lo + 21` and `hi − h` recover the first/last positive indices when the window touches neither end. All frozen episode windows satisfy that condition. The source conservatively refuses the inversion for boundary-touching windows. It checks positive count feasibility and never fills interior labels.

2. **Retained-positive bounds are valid.** With `I` positions inside the retained part of the positive span, `O` outside, `K` total positives, and known positive boundary counts `r` inside and `s` outside, the implemented lower bound `max(r, K − O, 0)` and upper bound `min(I, K − s, K)` follow from capacity and the known endpoints. Exact counts appear only when the bounds coincide. A nonzero padded-window count alone cannot pass positive support.

3. **Warm-up and maturity are correctly bounded.** For `N = 1321`, the eligible bands are `[63, 1315]`, `[63, 1310]`, and `[63, 1299]` for horizons 5, 10 and 21. These agree with Stage1's index rule. Original windows and excluded origins remain in the output; immature rows remain unlabelled. The known counterexample is preserved: `h21-e000` has positives at indices 41–44 and zero warm positive support. Its warm window offsets 43–45 do not intersect the sole control's mature offsets 0–25. This is arithmetic from already observed metadata, not an executed result or new predictive discovery.

4. **Pair support is separated appropriately.** Equal lengths, episode identity, seed, month flag, three-control cap, shortfall, within-horizon non-overlap and the 63-session control/episode buffer match the original source. The common-offset interval correctly intersects each original pair's warm/mature portions. Support requires an established positive lower bound; unknown support cannot pass. The role-supported and common-offset-supported counts remain distinct. No controls are replaced, reweighted, moved or regenerated.

5. **Calendar and dependence handling are honest.** Only explicitly bound sample/window dates and inverted positive-boundary dates populate the index/date map, with consistency and order checks. Other dates remain null. No FRED availability row is inferred from the aggregate count of 348 missing origins. Every cross-horizon window intersection is retained with both roles and IDs; independent episode count stays null. Chronological folds, labels, source rights, feature admission, power and utility gates remain unresolved.

6. **Execution boundaries prevent false admission.** Exact sample/receipt hashes, canonical sample bytes and receipt source pins are checked before a result is emitted. The CLI checks contract bytes, records its own source hash and a transparently root-declared commit, and opens the output exclusively. It has only standard-library imports and no external data or model calls. All per-origin labels remain null, scoring/fit admission remains false, and a zero process exit indicates artifact creation only. The source parses successfully; runtime behavior remains untested pending the root freeze and first run.

## Non-blocking clarification

`all_three_common_offset_supported` counts **three individually supported event/control pairs**. It does not compute one offset intersection shared by the event and all three controls, prove complete retained positive coverage, or establish independent replications. The contract's per-pair definition supports the implementation. Root should preserve that interpretation in the adopted wording and result commentary. No code change is required for the declared bounded scope.

Root remains responsible for committing the actual adopted bytes before execution, verifying that the recorded commit contains them, reviewing the emitted result, and binding its hash in the existing programme. This review does not supply or attest a freeze commit and does not waive the current source-purpose hold.
