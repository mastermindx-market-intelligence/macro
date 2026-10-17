# Independent auction math and capture review

Scope: bounded offline engineering review of the supplied W2 math leaf and root capture script, extended by root instruction to W1 receipt causality, lifecycle phase, alias and freshness. Candidate code was not edited by this reviewer. No network, repositories, market data, model outcomes, or backtests were used.

## Verdict

W2 supplied arithmetic slice passes the observed acceptance checks. No confirmed finance arithmetic, accounting sign, cohort/date/currency, unknown-versus-zero, decision-clock, or same-cohort percentile defect was found. This is acceptance of supplied-duration context math and asserted-complete private cash accounting only, not source qualification or live integration.

The initial capture had the two defects below. Root corrected both in capture SHA256 `0b3fed438d863f1f5380182d95386ffa25660b04e121673aaac8dfc409017524`; targeted independent revalidation passed. Parse completion now conservatively bounds own-system knowledge while exact body receipt remains separately exposed.

The initial stable W1 at `3db6b0d390c488134ae466a8a929f6c02e73a44e508436b4d7ab77ae28351781` had an additional **medium-severity phase-retention defect**: a fully elapsed auction without an observed result was calculated as AWAITING_RESULT and then omitted by the episode window. The original Bill fixture with a synthetic missing deadline, receipt Oct8 22:00Z and cutoff Oct14 12:00Z returned available context, zero episodes and awaiting_result_count=0 although the issue date was Oct15. Root corrected this by retaining AWAITING_RESULT within the bounded recent auction-date horizon. Independent checks for both known and missing deadlines pass at root-confirmed final W1 hash `3faead6ed3aa7cb5c2cc6b86a3657ad578b71723feb858599fe8280cd70f23fb`.

No remaining confirmed substantive blocker was found in the reviewed candidates. Acceptance is limited to these frozen offline context-math, source-normalization and capture boundaries. Final unified-repository feed serialization and owner-consumer integration remain root's separate verification task.

## Confirmed initial capture defects

1. **Medium: official-source provenance is not enforced after redirects.** `_fetch` returns `response.url` as `final_url` without checking scheme or hostname. `capture` then unconditionally records `rights_status=OFFICIAL_PUBLIC_SOURCE` and retains the fixed requested official URL as `source_url`. An offline fake `urlopen` response with `url=https://untrusted.example/auction-data`, status 200 and valid `[]` body exercises the actual `_fetch` code and is accepted. A capture supplied that transport metadata remains `available` and labeled official. Bounded correction: require HTTPS and a reviewed exact official hostname for each source before following redirects and for the final response URL; preserve a visible failure receipt when the provenance check fails.

2. **Medium: malformed content is reported as successful capture.** Exact `b'{broken'` response bytes produce `status=available`, `payload=None`, no explicit error, and actual `main()` exit code 0. W1 intentionally retains exact bytes and later quarantines the malformed payload, so this is a capture/CLI semantic validation defect rather than a proven downstream feature leak. Bounded correction: preserve the immutable exact body receipt, expose separate semantic validation status/error, and return nonzero on malformed, unsupported or degraded content.

## Observed positive evidence

- Supplied W2 test suite: 16 tests passed.
- Independent reviewer suite: 7 tests passed. There are 120 generated DV01 cases and 120 private-cash cases, each checked against exact `Fraction` arithmetic across Decimal context precisions 2, 7, 28 and 80.
- Independent percentile oracle: 7/23 x 100 = `30.43478260869565217391304347826086956522`, with reversal of history and contamination by other class, tenor, measure basis, funding axis, future event, late receipt, result role and unknown value preserving the same score and 23-row baseline.
- Every security class (Bill, CMB, Note, Bond, TIPS, FRN) excludes each of the other five classes. All-tie histories return 50; current auction-result role is not scored.
- One microsecond beyond the decision clock blocks market-value eligibility. Exact equality is eligible.
- Missing/empty cash categories and uncertified completeness leave net cash unknown; explicit zero buyback remains eligible. Gross face and separate SOMA context do not enter net cash. Mismatched cohort raises. Exact negative net cash is valid. Reserve pressure is always null in examined outcomes.
- Revised capture receipt is stamped at parse completion, after the complete body returns, and is not backdated by HTTP dates. Independent test clocks have request T, body T+3 and eligibility T+4. Identical receipt replay preserves the inode; existing conflicting bytes cause a collision exception and are not overwritten; temporary files are cleaned up. Invalid UTF-8 is preserved as bounded base64 failure content.
- Supplied W1 tests: 35 passed. Supplied capture tests: 6 passed using an in-memory split-tree fixture-location harness; no test source edits.
- Independent W1 suite: 6 passed, covering one-microsecond receipt cutoffs, updates that cannot backdate knowledge, late invalid results that cannot become valid merely through a later build, reopening alias evidence and distinct auction dates, failure/malformed responses that cannot refresh valid age, order-independent equal-clock conflicts, and bounded next-day AWAITING_RESULT retention.
- Independent revised capture probes exercise the real `_fetch` function through a fake opener. An untrusted final URL raises before its body is read; a supplied untrusted final URL becomes unavailable without the official-source rights label. Malformed exact JSON is retained while validation status is unavailable and actual CLI exit is 1.

## Commands

```bash
cd /workspace/scratch/f3c3644d80e2/w2_patch
python -m unittest discover -s tests -v
cd /workspace/scratch/f3c3644d80e2
python review_math_capture/adversarial_review.py
python review_math_capture/run_candidate_suites.py
python review_math_capture/lifecycle_review.py
```

The reviewer scripts use injected/fake transport only and do not perform network IO. `run_candidate_suites.py` loads the supplied test modules unchanged and redirects the capture test's single fixture constant to the W1 fixture folder in memory, because root_patch is a split patch directory rather than the final unified repository.

## Reviewed hashes

| Artifact | SHA256 |
|---|---|
| W2 engine | `0a8e5a6c12af0127186d693f0a87164709f28e339e505a3b7ba4b4a32cfc0b43` |
| W2 tests | `3a2a7e0fc1a1894e68d7b1f2efa2ee0afc77c1e0da85071e4e08cbcc08c70d27` |
| W2 README | `271b24fee271fa32528abf55239584f19f26319a8a6a7a5538adb5630f0377c5` |
| Root capture, initial | `8ac2b7486faab653cd6a107c111f92523b04b1b4384adc53e4c2ad9926788051` |
| Root capture, revised | `0b3fed438d863f1f5380182d95386ffa25660b04e121673aaac8dfc409017524` |
| W1 source after root phase fix, final | `3faead6ed3aa7cb5c2cc6b86a3657ad578b71723feb858599fe8280cd70f23fb` |

Final review logs: `adversarial_revised.log`, `lifecycle_revised.log`, and `supplied_suites_revised.log`. The supplied-suite log contains 35 W1 tests and 6 capture tests; the independent logs contain 7 math/capture tests plus active capture probes and 6 lifecycle tests. All final commands exited 0.

## Remaining limits

The math leaf cannot prove the owner completeness assertion, discover omitted operations, source real settlement cash, qualify receipts or duration/market-value inputs, or identify whether two distinct IDs represent one economic component. Indexed TIPS market value and real-yield duration must be supplied; FRN effective-rate duration has no maturity fallback. Percentile thresholds are versioned product choices, not validated forecasts. W1 is a bounded local receipt view, not a historical first-release archive, a complete future CMB universe, or a TAAPS/announcement-result XML migration adapter. Reopening/date joins rely on retained explicit source fields, not inferred identity. Persistence proves atomic no-overwrite by this publisher, not WORM filesystem permissions or crash recovery durability. No live official-endpoint connectivity was exercised.

Existing SLF006 NO-GO, D2 FAIL and Terminal KILL remain unchanged. This review creates no risk, exit, deploy or probability authority.
