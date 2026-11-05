# T13 sample-use and feasibility contract — adopted, 18 October 2026

**Status: ADOPTED FOR A POST-OBSERVATION METADATA DIAGNOSTIC ONLY. Root must commit these fixed bytes and the diagnostic source before its first execution. Model fitting remains unadmitted.**

This is a **post-observation admission contract** for the existing Grey Deer programme. The original sample, its control shortfalls, immature tails and warm-up losses have already been observed. Neither this contract nor its future output is an untouched predictive preregistration. It authorizes no feature join, fit, label reconstruction, trial entry, source acquisition, publication, or live policy change. Sol / Meta-CEO remains the method decision owner.

## 1. Purpose and immutable inputs

The useful output is a separate, reproducible inclusion/exclusion map of **metadata-derived candidate origins**, plus a determination of what structural support exists for an eventual study. A successful diagnostic does not admit that study.

Bind exactly these existing files:

| Input | Binding |
|---|---|
| T12 sample | `sample.json`, 6,359 bytes; SHA256 `944e0054b724aef775a5073ee8a1537779b464454a304acf4a4b396cd818a583` |
| Freeze receipt | `receipt.json`; SHA256 `ad8a1f5fe92fb12690a25794f917619a2e113baaf9a07fc3f446207020340d4f` |
| Sample identity | `grey_deer_episode_samples.v1`; SPY; 1,321 sessions; 2021-07-06 through 2026-10-07; seed 20261013; horizons 5, 10 and 21 |
| Close-input identity | `60f0d81c686fce6e03ace59c9549d9cd28713b10973b2d2711fc465740fd0bc8` |
| Separate normalized RAW OHLCV identity | `c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb` |
| Original builder / specification blobs | `0a0eecb98e743b780db1ee3b0382e268d592fa67` / `fe68838867982e845297aeb0daf518e0387120f9` |
| Original Stage1 helper blob | `76d231d6d12c8693cd07a2540b360c24f6c50b42` |

The diagnostic verifies the sample's canonical serialization and byte identity, receipt identity, source pins, indices, counts and identifiers. It does **not** call the builder, import Stage1, inspect prices, rebuild outcomes or change either input. It must create a new output file exclusively and refuse overwriting an existing result. The diagnostic source hash, adopted contract hash and root-supplied freeze commit are recorded. The commit value is a declared provenance pointer; the diagnostic does not independently query Git to attest it.

Source basis: original [T12 specification](../../EPISODE_SAMPLE_SPEC_2026-10-13.md), [builder](../../../../scripts/research/grey_deer_episode_samples.py), [Stage1 helper source](../../../../scripts/research/grey_deer_pullback_stage1.py), [freeze README](README.md), and [independent sample review](T12_FROZEN_SAMPLE_REVIEW_2026-10-17.md). The root-supplied T13 draft constraints are session index at least 63, mature forward horizon, original T12 membership, and strictly earlier release dates. This proposal does not replace the draft's hypotheses or consume its fit budget.

## 2. Distinguish three objects

1. **Window origin:** every integer session index in an emitted inclusive `window_idx = [lo, hi]`. Its role is `EPISODE_WINDOW` or `CONTROL_WINDOW`. An episode window includes 21 sessions of lead-in padding and `h` sessions after its last positive origin. Membership in that window does not mean `Y = 1`.
2. **Positive origin:** a session at which the original frozen label was `Y = 1`. T12 stores only `n_event_origins`, `first_event`, and `last_event`; it does not store the full positive-origin index vector. The diagnostic must not fill that vector or assign per-origin labels. In particular, all dates between first and last positive origins must not be labelled positive.
3. **Scored origin:** a row separately admitted for a specified hypothesis, with an exact calendar identity, entitled point-in-time features, original outcome identity and frozen evaluation rules. **There are no admitted scored origins in this diagnostic.** `score_admitted` and `fit_admitted` remain false, including for metadata-eligible rows.

The proposed candidate frame is every existing window origin that meets the index rules below. This settles the denominator for the admission map, not a scoring statistic or a choice of which positive labels to recover later. Keep one row per `(horizon, window_id, origin_idx)`; cross-horizon appearances remain separate, related records. Do not pool them into a pseudo-population.

## 3. Exact index eligibility and missing-date treatment

With zero-based index `i`, frozen length `N = 1321`, and horizon `h`:

```text
warm(i) = i >= 63
mature(i, h) = i + h < N
candidate(i, h) = warm(i) AND mature(i, h)
```

The inclusive eligible bands are therefore `[63, 1315]`, `[63, 1310]`, and `[63, 1299]` for horizons 5, 10, and 21. Emit both predicates and every applicable exclusion reason. Do not reinterpret an immature origin as a negative label. A row excluded for warm-up is still retained in the map.

Each row carries its original window bounds, parent `episode_id`, optional `control_id`, role and within-window offset. Interior dates are **null** unless the sample metadata itself binds that exact index to a date. Date bindings may come only from sample first/last dates, window endpoints, and exactly recovered first/last positive boundaries under the pinned padding rule. Conflicting bindings refuse the diagnostic. No weekday calendar, exchange calendar, holiday interpolation, price file or auxiliary feature file is substituted.

The current sample contains no full daily calendar vector. Its close-input hash establishes which calendar belongs to it but cannot reconstruct that calendar. **Do not infer that FRED's reported 348 missing origins line up with indices 0–347, or that a particular feature begins at index 348.** Aggregate coverage counts and date ranges do not establish an exact row join.

## 4. Positive-support counts without reconstructing labels

For an episode whose window is not clipped at either series boundary, the original source gives:

```text
first_positive_idx = lo + 21
last_positive_idx = hi - h
```

This is inversion of already frozen padding metadata, not a new label computation. The diagnostic binds these two indices to the recorded first/last event dates. It validates that the recorded positive count is possible within that span. For a clipped window, use no such inverse; return unknown support unless exact boundary indices are already present in the permitted metadata.

For any retained index band `B`, let the frozen positive span be `S = [first_positive_idx, last_positive_idx]` and recorded count be `K`:

- If `S` lies entirely in `B`, retained positive count is exactly `K`.
- If `S` misses `B`, retained positive count is exactly zero.
- Otherwise report a lower and upper bound using the number of available positions and the known positive first/last boundaries. An exact count may be reported only when those bounds coincide. Leave interior membership unknown in all cases.
- If the boundary indices cannot be identified from metadata, report conservative unknown bounds. Unknown support cannot pass a gate requiring established positive support.

Never count all eligible padded-window rows as positive origins. The existing review already identifies the counterexample: `h21-e000` has an event window at indices 20–65, while its four positive origins occur at indices 41–44. The three padded-window rows that survive the index-63 rule provide **zero** retained positive origins. These are prior observations, not new results of this proposed diagnostic.

## 5. Controls, pair support and denominators

Keep every original episode and control in its original order. Preserve `month_matched`, original lengths, requested count of three, placed count and shortfall. Do not replace a pre-warm-up control, refill a missing slot, change the seed, shorten a window, draw a new control, borrow another episode's control or promote a control to another horizon. A control's original role means the builder found no positive origin at that horizon; it does not establish a generic benign market or independently reverify every label.

Report these distinct quantities per episode and horizon:

| Quantity | Exact definition |
|---|---|
| Placed controls | Number of original control records attached to this episode |
| Controls with any candidate origins | Original controls containing at least one warm and mature window origin |
| Fully eligible control windows | Original controls for which every window origin is warm and mature |
| Episode positive support | Bounds and, when identifiable, exact count of original positive origins surviving eligibility |
| Role-supported pairs | Event has established retained positive support and its own control has at least one candidate origin |
| Same-offset pair support | Offsets `q` for which both `episode.lo + q` and `control.lo + q` meet eligibility; retained positive support is counted or bounded on the event side of this common-offset band |
| Episodes with three usable controls | All three originally requested controls each form an individually supported pair at their own common offsets; this does not establish one offset intersection shared across all three controls, complete retained event coverage, or independent replication |

Same-offset support measures whether the original equal-length pairing still has comparable temporal positions after exclusions. It is a diagnostic mask; it does not alter window bounds, define a model weight, or authorize averaging over shortened windows. Report role support and common-offset support separately rather than choosing whichever makes the study look stronger. Control observations remain separate records even when associated with the same event.

The frozen three-control request is a target supplied by T12, not a guarantee or a documented inferential threshold. Report completeness honestly. Do not silently import Stage1's ten-episode floor, invent a power threshold, balance classes, reweight incomplete matches, or turn case/control proportions into a daily base rate. Such study choices remain a separate, explicitly post-observation method decision.

## 6. Dependence and chronology

Emit every cross-horizon intersection of original windows, distinguishing episode/episode, control/control and episode/control. Preserve both horizons and IDs and the intersection bounds. Also validate the original within-horizon control separation and episode buffer as structural metadata checks. Overlap counts, union windows, episode records and repeated origins are not independent episode counts; **`independent_episode_count = null`** throughout.

The map does not select folds. A later evaluation contract must bind exact calendar indices, the prediction clock, available training labels and chronological train/validation/test intervals before any feature/outcome scoring. A training origin's outcome must be fully known before the test decision time; related overlapping event windows cannot straddle training and test as independent samples. Leave-one-episode-out with later training history is not a prospective test. Purging, embargo, clustering/uncertainty, same-support baseline comparisons, counted fits and power/utility gates remain unadmitted until frozen together. No field is automatically populated from an observed outcome or from whichever fold choice happens to retain more controls.

## 7. Deterministic dispositions

The diagnostic produces several explicit dispositions rather than one misleading green flag:

| Check | Accept condition | Refusal or limitation |
|---|---|---|
| Metadata diagnostic | Exact byte/source bindings and structural invariants pass | `REFUSE_METADATA_IDENTITY_OR_STRUCTURE` on any failure; no partial result presented as accepted |
| Minimal pair support at a horizon | At least one original same-episode pair has established positive support and candidate control origins, reported separately from same-offset support | `REFUSE_NO_ESTABLISHED_MATCHED_SUPPORT` if absent; this is a logical necessity, not evidence of adequate power when present |
| Original requested allocation | Original placed count equals three for every episode | Otherwise `INCOMPLETE_REQUESTED_ALLOCATION`; this reports a construction limitation without inventing a statistical threshold |
| Feature admission | Not evaluated here | `HOLD_SOURCE_PURPOSE_AND_EXACT_AVAILABILITY` |
| Confirmatory model admission | Not evaluated here | `NOT_ADMITTED`; independent N, adequate chronological support, power, labels and model/evaluation contract remain unestablished |

Based on the already published review, the 21-session matched lane is expected to refuse after warm-up: its sole matched event has no eligible positive origin. This expectation is disclosed before executing the new diagnostic; do not present its confirmation as a new predictive discovery. The 5- and 10-session lanes may retain some structural pairs, but that cannot establish representative temporal support, inferential adequacy or forecasting skill.

The current FRED-purpose disposition remains **UNKNOWN / operational HOLD** for the retained-FRED fitting/evaluation and probability-publication purposes. Do not perform a feature availability join during this diagnostic, even if a calendar is later made available. Source-purpose qualification, exact initial-release identity and a separately authorized join must precede that next phase. The strict date-only feature rule, when that phase is admitted, is `release_date < origin_date`; same-day releases cannot be assumed available. Missing, revised, stale or ambiguous inputs remain typed unknowns. This contract neither rules on all prior acquisition nor authorizes new collection, source substitution, deletion or publication.

## 8. Adopted implementation and execution boundary

The companion `t13_sample_metadata_admission.py` uses the Python standard library. Its only data inputs are the two exact metadata files. The adopted contract and its hash are provenance inputs. It emits one JSON containing origin records, per-window and per-episode attrition, same-episode pair support, cross-horizon overlap and explicit admission holds. Every per-origin `label` is null and every `score_admitted` is false. No model or feature module is imported.

Before executing it, root must:

1. Review and adopt or amend this proposal in the existing repository and programme record, preserving its post-observation status.
2. Commit the fixed contract and diagnostic source; record that exact commit and the adopted contract SHA256.
3. Execute once against the frozen metadata into a new result path. The CLI requires `--contract`, `--contract-sha256`, and `--freeze-commit`; those arguments record custody and do not independently prove it.
4. Review the emitted result, bind its hash, and record the resulting accept/refuse dispositions in the same programme evidence. A successful process exit means the diagnostic emitted valid evidence, not that fitting was admitted.

At adoption, neither the author, independent reviewer nor root has **executed the diagnostic**. No new sample, daily labels, feature join, scored hypothesis, fit or trial has been created. If the diagnostic confirms an unsupported lane, retain that failure and close that lane at the appropriate scope. Any revised sampler, expanded history, feature set or evaluation design needs its own declared development revision; it cannot be passed off as the original untouched freeze.

## 9. Root adoption and independent review

Sol / Meta-CEO accepts this bounded method after the [independent pre-execution review](T13_SAMPLE_USE_CONTRACT_REVIEW_2026-10-18.md). The reviewed proposal was SHA256 `8438120c615218d0b80d675b97759f1f8df2bb60b14f1ee7ec33584ff45afaa1`; its diagnostic source was `a76d3b37e5cd365a33245143e1f28b68aac935225c8bf8ad4e433daa59b86db4`. Adoption changes document status and repository links, clarifies that three-control support is per pair, and changes only the source module docstring. The diagnostic logic is unchanged. The review does not certify runtime behavior, predictive competence or the enclosing commit. Root will independently verify the committed contract/source bytes before the first execution and retain a separate result and process receipt.
