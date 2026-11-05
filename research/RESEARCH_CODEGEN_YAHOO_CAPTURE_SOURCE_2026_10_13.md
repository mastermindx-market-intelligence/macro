# Yahoo observation capture: dormant source acceptance

The current mutable Yahoo archive cannot establish when a historical value was first available. This change provides an explicit, default-off capture path for future observations from the incumbent Yahoo collector. It does not qualify the existing archive for point-in-time research.

`run_adapter(..., capture_yahoo_receipts=True)` requires the exact incumbent Yahoo adapter. Its current-call metadata qualifies only returned Adj Close total-return frames for XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV and XLY. Rebase attempts discard earlier lineage; fallback observations cannot inherit Yahoo lineage. The default caller and scheduled collection remain unchanged.

After a successful existing cache upsert, the helper preserves two bounded, normalized JSON images: the validated and session-filtered provider return, and the returned merged values. These are not vendor wire bytes or canonical parquet bytes. Separate clocks describe adapter return, capture and durable image publication. Images are published without replacement and the receipt follows them. A failed capture leaves the successful cache write intact and emits a fixed refusal note. It can leave unaccepted objects or an uncertain receipt: the future owner must reconcile those exact objects on the original attempt, never replay acquisition to manufacture success.

Unknown provider availability, source/operation identity, rights, actor and clock authentication remain null. Calendar qualification, original historical availability, revision completeness and canonical parquet transaction durability remain unqualified. A hash or declared lineage is not authentication. This is a trusted incumbent-caller helper, not an untrusted-object boundary or a new store, ledger, lease or scheduler.

## Verification

Four source/test files were independently reviewed against base `9d3fe8db76b4eac204a186d68b6cf85228b8fa74` and verified unchanged at integration base `00bf61fc699ca340f6000706f57a7c1ade78c479`:

- `collectors/yahoo.py`: `67d1f38327c4b65415b50309f83dd64c1bcfe5cec54616f25bd7851d5631c420`
- `collectors/base.py`: `2e17b5a2bd0b15d8c99d2bf73113e41429628230337b64e16d03e3a052b49965`
- `lib/store.py`: `7424b19d2a418d6611c6346b20764a89d6ffe34ad9e6f3a115ec78e6a45b826b`
- `tests/test_yahoo_availability_capture.py`: `40861a5a185d835cfba1f2f39983f47b8977b59a015ddcedfebfcb8e99665e83`

The 43 targeted tests passed using invented frames and temporary-directory publication. Network acquisition is mocked. Tests cover default-off behavior, lineage replacement/refusal, separate images and clocks, missing cells, bounds, no-clobber reuse, corruption/mode refusal, and interrupted publication. The combined capture/store-retention/collector-calendar regression produced 96 passes and one import failure because local Python lacks yfinance. The existing CI Yahoo job supplies that dependency. The 10 existing dual-basis store tests also passed and now have explicit coverage in the same Yahoo CI job. All 294 legacy CI jobs passed manifest validation. Independent review accepted dormant source integration with no blocking findings.

Evidence is retained under `/Volumes/Mastermind/evidence/research-factory-codegen-20261012-01a1333c/methods-review/t01-capture/`: `ROOT_CAPTURE_TESTS.log`, `INTEGRATED_CAPTURE_REGRESSION.log`, and `INDEPENDENT_CAPTURE_SOURCE_REVIEW.json`.

## Remaining programme obligations

No live capture, source-writer transfer, provider acquisition, Trial/Vault write, candidate execution, product acceptance or production activation occurred. Preserve the separate Yahoo basis-refresh DRAFT/HOLD PR #8066. Actual activation needs incumbent writer/basis-owner coordination, qualified rights/clocks/calendar/source identity, and a consumer that rejects missing or late evidence. The original typed-contracts Fabric operation retains its original assigning parent and recovery owner. Existing source PRs #9077 and #9096 remain on their normal protected release path; this source acceptance does not close the programme.
