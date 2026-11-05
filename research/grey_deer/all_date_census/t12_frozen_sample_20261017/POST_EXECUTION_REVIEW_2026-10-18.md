# T13 metadata diagnostic — independent post-execution review, 18 October 2026

**Disposition: ACCEPT the emitted metadata artifact and its bounded support/refusal findings. No identity, coverage or arithmetic error found. Confirmatory model admission remains NOT_ADMITTED; FRED source purpose remains UNKNOWN / operational HOLD.** The result is a post-observation feasibility diagnostic and supplies no predictive validation.

## Evidence identity and execution custody

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `T13_SAMPLE_METADATA_ADMISSION_2026-10-18.json` | 1,248,719 | `91a45bc0f4ecb650db01bdeb5e9ec6834a09249ed4057d5a5d54a4d5cd6841e5` |
| `T13_SAMPLE_METADATA_ADMISSION_RECEIPT_2026-10-18.json` | 4,847 | `e6b5e1fd470acd4c260aa03cd089edeb5ae4751174def9663acb10d37b4c9a2b` |

The output, receipt and recorded stdout agree on output identity and all horizon summaries. The receipt records one invocation from **2026-10-18 02:07:24.626119 UTC** to **02:07:24.693074 UTC**, exit 0, empty stderr, zero fits/trials and no sample regeneration, label reconstruction, feature join or runtime mutation.

The adopted input files present locally match every receipt hash: contract `4c7a9d2225e9c27d6abd6a5f124b1f7fe6a70844c1adc4e8485b2c1f8c1ec8ce`, diagnostic source `0d1b6e55aafb58932c5b581ac406c96e242f199f7838c3e8abc723039b6498ff`, original sample `944e0054b724aef775a5073ee8a1537779b464454a304acf4a4b396cd818a583`, and original receipt `ad8a1f5fe92fb12690a25794f917619a2e113baaf9a07fc3f446207020340d4f`. Root reports separate verification that freeze commit `9102e6954db145b92dd3d1c32e113405104ce212` contains those exact inputs. This reviewer did not query Git or independently observe the invocation; the execution and commit-verification statements remain attributed to the root receipt. The diagnostic correctly describes its own commit field as declared provenance, not independent Git attestation.

## Verified output and support

The output retains **2,138 origin records across all 35 original windows**, with unique `(horizon, window_id, origin_idx)` identities and exact inclusive index coverage. All 21 original episode records and 14 original control pairs are present. Window order, identity, original lengths, warm-up and maturity predicates, exclusion reasons, within-window offsets, retained bands and aggregate counts reconcile with the frozen sample.

There are **2,004 index-eligible window records**. These are repeated horizon/window records, not a unique daily population, positive labels, admitted scoring rows or independent observations. Every origin's label and feature availability remain null, and scoring remains false.

| Horizon | Original episode records | Controls placed / requested | Role-supported pairs | Same-offset-supported pairs | Episodes with supported pairs | Episodes with three individually supported pairs |
|---|---:|---:|---:|---:|---:|---:|
| 5 sessions | 6 | 10 / 18 | 9 | 9 | 4 | 2 |
| 10 sessions | 7 | 3 / 21 | 2 | 2 | 2 | 0 |
| 21 sessions | 8 | 1 / 24 | 0 | 0 | 0 | 0 |

The original construction shortfalls of **8 / 18 / 23** are unchanged. Pair counts reconcile independently with retained origin records and each event's positive-support metadata. Role support and same-offset support happen to agree in this sample; they remain different definitions.

The 21-session lane correctly returns `REFUSE_NO_ESTABLISHED_MATCHED_SUPPORT`. Its sole matched episode, `h21-e000`, retains three padded-window origins after warm-up but **zero positive origins**: the four positives lie at indices 41–44, before index 63. Its control retains 26 mature candidate origins and 20 immature origins; the event and control have no common eligible offsets. Seven other 21-session episodes retain positive support, but none has an original control. The refusal therefore concerns this matched lane under the frozen use rules, not the absence of 21-session events generally.

The 5- and 10-session supported events remain confined to their original 2022 episode records. The counts establish a necessary structural condition only. Every horizon still has incomplete requested control allocation; neither representative temporal coverage nor adequate power has been established. “Three individually supported pairs” does not establish one offset set shared by all controls or three independent event replications.

## Calendar, dependence and acceptance limits

All **39 cross-horizon window intersections** are present with correct roles, parents and inclusive bounds: **19 episode/episode, 14 episode/control and 6 control/control**. These intersections support the explicit dependence warning. The 21 horizon-specific episode records cannot be reported as 21 independent events; `independent_episode_count` remains null throughout.

Every emitted date agrees with a permitted sample endpoint, window endpoint or inverted positive-boundary binding. **1,901 origin records correctly have null dates.** The complete daily calendar is unavailable for joining. No FRED missing-origin count has been translated into an index cutoff or synthetic calendar.

The result preserves `HOLD_SOURCE_PURPOSE_AND_EXACT_AVAILABILITY`, UNKNOWN source purpose, missing original label-vector admission, unfrozen chronological evaluation, and unresolved independence, power, model and utility gates. It admits no FRED feature join, probability publication, fit, warning promotion or action policy. The expected 21-session refusal confirms a disclosed prior limitation; it is not a new predictive discovery.

This review used local output/input reads, hashes and independent invariant/arithmetic checks only. **The diagnostic was not rerun or imported.** No labels were reconstructed; no prices, features, network, browser, Studio, Git or trial ledger were accessed. Only this review file was written. Root may retain these results in the existing programme and close the original 21-session matched lane at this bounded scope while preserving the frozen sample and all failures.
