# Market Memory real-corpus latency baseline

Eight sequential fresh Python processes read the existing 109-member registered corpus. The protocol was recorded before these eight trials, after a separately disclosed 12.174-second calibration. The source head was identical across all trials. No provider/model call, study transition, count, source refresh or subsequent price label access occurred. The OS filesystem cache was not cleared; these are not cold-cache measurements.

- Source: `9fd0cd7d2ca7737edcc86e58879c315a9ea0d508`
- Predeclared protocol SHA-256: `e1baa4ccded8761ade15d8684c5d76f7da76b5f6c096f59ff208c200cfe09651`
- Nearest-rank P50: 20.512 seconds; nearest-rank P95: 31.253 seconds (the maximum of only eight observations).
- Conventional sample median, averaging the central pair: 21.545 seconds.
- Peak process RSS: 33148928 bytes.

| Trial | Server seconds | Client seconds | Peak RSS bytes |
|---|---:|---:|---:|
| 1 | 22.578 | 23.973 | 32956416 |
| 2 | 20.512 | 21.480 | 33009664 |
| 3 | 25.166 | 26.563 | 32821248 |
| 4 | 31.253 | 32.377 | 33021952 |
| 5 | 26.610 | 27.691 | 32952320 |
| 6 | 17.094 | 17.944 | 33148928 |
| 7 | 14.838 | 15.648 | 33148928 |
| 8 | 18.918 | 19.802 | 33050624 |

All eight invocations returned eight retained citations, one attachment, zero registered candidates and zero transitions; the audit hook observed no attempted unrelated study opens. The existing 64 MiB owner read cap remained active. A separate profiled invocation found 8,022 policy checks, 16,047 registration loads and 40,118 protected-file opens. Profiling overhead makes that invocation unsuitable for the latency distribution.

This baseline identifies repeated authorization work as a performance concern; it does not authorize skipping rights, changing revocation semantics, or caching authority on a timer. A bounded Fabric review is assessing possible pure-validation reuse. No optimization or speedup is claimed.

B0 remains open for larger real/synthetic corpus distinctions, scale/concurrency, storage and refresh costs, review/model costs, and the dependent G0/G1 capabilities. No statistical independence or forecast usefulness follows from these repeated software invocations.

Evidence: `/Volumes/Mastermind/evidence/market-memory-20261012-01a1333c/integration/B0_REAL_CORPUS_LATENCY_PLAN.json`, `B0_REAL_CORPUS_LATENCY_TRIALS.json`, `B0_REAL_CORPUS_LATENCY_SUMMARY.json`, and `B0_REAL_CORPUS_PROFILE.txt`.

## Review disposition

The same-root Fabric cost review returned and was consumed. Its conditional validation-cache proposal is not adopted: the actual method disclosure includes the current descriptor and imported retrieval/cohort code identities, contrary to the proposal's prerequisite. All current authorization reads remain. Its repeated-read accounting informs the baseline; its projected speedup is unmeasured and the hypothetical 1024-row registry does not describe this one-row binding registry. No performance claim or immutable protocol pin changes follow from this review.
