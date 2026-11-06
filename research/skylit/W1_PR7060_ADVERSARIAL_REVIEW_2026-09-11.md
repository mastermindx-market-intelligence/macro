# W1 PR7060 adversarial review and repair boundary

Recorded: 2026-09-11 UTC. Accountable seat: ceo-sol.
Product child: `us-sector-participation-w1-20260910-sol-001`.
Exact Slack carrier: Mastermind X / `C0BSBM78V1N / 1789063697.492969`.
Records carrier: Macro PR7035 / `sol/skylit-sector-integration-20260910`.
Source implementation carrier: Macro PR7060 / `claude/ssd-sector-central-w1-source-impl-1c350aeb6815a110`.
Exact reviewed source head: `16d0cc47368705cdb4ad7c7dc2ba588f5f327fef`.
Procedure basis for the review: protected Mastermind `797cfd0b1001d9dfe6fe9030af80ecdab0e1220d`, Skillpack1.0.1/bootstrap1.

## 1. Verdict and capability delta

**Verdict: REQUEST_CHANGES / CONTINUE. Capability state: PARTIAL.**

Before PR7060, W1 existed as research, source law and an operator contract, with no product source implementation.
At the reviewed head, the branch contains a licensed-history request helper, part of the deterministic 20-session calculation, a metadata-only Sector Central reader, one explicit CI-manifest registration and twenty tests. This is meaningful scaffolding but not the commissioned product.

The primary persona still cannot scan a real calendar, select a dated cell, verify its denominator/exclusions and matching constituents, or follow the existing research destination. The licensed helper is not called by an owning producer; no derived artifact is published; the builder returns only hard-coded metadata; the Money & Breadth UI is absent. The promised producer -> derived product -> real consumer journey is disconnected.

No merge, Ready, deployment, live full-roster acquisition, production proof, trading authority, W2 or worker release follows from this review.

## 2. Worker chronology and exact dialogue edge

The same Claude8 desktop conversation remains the source writer. Its source RESULT is Slack `1789095669.355329`. The worker truthfully reported that it wrote code before emitting a separate source-writing START; the chronology defect is preserved, not backdated or replayed.

Sol consumed that return in `1789096018.269229` and required repair in the same PR. The repair must include the UI rather than creating a follow-up UI PR. The Secretary's attempted native continuation later returned a specific-user-approval hold. The current Chairman then explicitly directed this Sol session to continue the original goal; Sol transmitted that specific approval to the existing capacity/continuation owner with a reconcile-before-send, same-exact-destination, send-once instruction. Until a later exact-carrier receipt is consumed, delivery and worker repair START remain distinct and uncertain.

The builder remains sticky to PR7060. Do not place a replacement, copy the work into another branch/session or infer completion from a delivery attempt.

## 3. Exact-head source findings

The reviewed diff changes four paths:

- `.github/ci/legacy-jobs.yml`
- `collectors/breadth.py`
- `scripts/build_sector_central.py`
- `tests/test_sector_central_participation.py`

Useful preserved decisions include bearer-token header use rather than a query parameter, no direct call from inherited breadth `fetch()` at this head, calendar reindexing, explicit five-name/90%-coverage intent, local pandas import in the builder to preserve its light-import gate, and explicit naming of the new test suite in a dependency-compatible legacy job.

However, independent exact-source execution with fake HTTP and in-memory prices found all twelve targeted adversarial obligations unmet:

1. A whole missing reference symbol disappears from the expected denominator.
2. A Boolean inside an object column is admitted as numeric.
3. A sector with zero covered symbols disappears instead of remaining visibly unavailable.
4. A response for the wrong ticker is accepted.
5. A response declaring `adjusted=false` is accepted and restamped as adjusted.
6. A body-level `NOT_AUTHORIZED` response containing rows is accepted.
7. An unexpected `next_url` is accepted despite possible truncation.
8. Conflicting duplicate sessions are silently last-write-wins.
9. Rows outside the requested window are accepted.
10. Non-finite closes are accepted.
11. Boolean closes are accepted.
12. Non-positive closes are accepted.

The probe imported only the exact method AST with fakes, made no provider request and wrote no source or market store. It is discriminating review evidence, not product execution or production proof.

## 4. Required repair

### R1 — complete one real vertical in the same PR

Add one explicit S&P-reference-only owning invocation. Preserve inherited midcap, small-cap, Russell, China, Hong Kong and Canada acquisition. Publish the derived participation and dated member evidence through the existing schedule/publication system. Sector Central consumes actual numbers after the grader boundary. Finish the Money & Breadth calendar, dated constituent inspection and existing research links in PR7060. Do not split producer, UI or evidence into a nominal future capability.

Live full-roster acquisition and deployment remain held pending qualification. Implementation tests use fake/injected source responses and isolated roots.

### R2 — expected population and input identity

`expected_count` comes from the complete validated reference roster for the sector, not the available price columns. Missing whole symbols remain expected and receive typed exclusions. Preserve zero-covered sectors. Validate duplicate symbols, duplicate provider identities, conflicting sector membership, malformed sector/symbol values, duplicate price columns and duplicate normalized session dates.

Reject an isolated Boolean inside an object column. A member is eligible only with twenty finite, positive, non-Boolean prices on the twenty consecutive expected sessions. Use exact integer coverage comparison (`eligible * 10 >= expected * 9`) plus the five-name floor. A zero eligible denominator is unavailable; a valid denominator with zero above is a genuine zero percent.

Resolve class-share and other provider symbols through the existing identity owner. Retain reference and provider symbols separately and validate the response against the provider identity; do not add another ad-hoc identity plane.

### R3 — qualify the returned source data

Validate the HTTP/body envelope, returned ticker, explicit adjusted flag, results shape, request range, daily-session timestamps, pagination/truncation markers, duplicate dates and every close before stamping the result qualified. A source-level 401/403/`NOT_AUTHORIZED` stops the bounded generation promptly rather than repeating the same doomed request across the roster. Never send the bearer token to an unapproved/non-HTTPS base.

A complete sparse response may legitimately omit an expected session. Preserve that hole so only rolling windows containing it become ineligible; do not call every market-data absence transport truncation or discard all later usable history. Fetch nineteen precursor sessions before the first displayed cell. Record calculation bounds separately from display bounds.

The computation's production input must mechanically carry the qualified source/basis/vintage contract; a docstring saying a DataFrame is expected to be split-adjusted is not a gate.

### R4 — exact numerical behavior

The reviewed `rolling_max == rolling_min` guard covers constant windows but not all nonconstant windows whose exact arithmetic mean equals the final price while binary summation rounds below it. Preserve exact-oracle equality and genuine one-ULP crossing tests. Do not apply a broad arbitrary epsilon. The implementation may use an efficient fixed-point/exact-input method; the acceptance rule is semantic, not a mandated algorithm.

### R5 — one bounded atomic generation

Cells, member states, reference identity, method/schema, source/basis/vintage, calculation/display bounds, expected/source sessions, acquisition/computation clocks, exclusions, quality and availability must share one generation identity. A partial roster, mixed vintage, deadline expiry, interrupted write or malformed result never becomes a current-looking generation.

Publish through a temporary/versioned derived generation and move the canonical pointer only after validation. A previous valid generation may remain visible only with its original identity/source clock and a stale status derived against the current expected session. A fresh page-build timestamp never rejuvenates it. Do not use default `combine_first` snapshot publication that carries stale values into new unavailable cells.

Keep the public projection bounded: compact summary cells may load with the view, while dated member evidence is lazy-loaded or equivalently bounded. Never embed the full roster×history matrix or existing gated action rows into the legacy `window.SECTOR_CENTRAL` payload. The selected detail must verify the summary generation ID before display.

### R6 — bound and isolate the whole acquisition

A per-request timeout is not an overall bound. Declare a finite request budget and wall-clock deadline. Stop promptly on global auth/entitlement refusal. Individual symbols may resolve to typed terminal exclusions; a global deadline or interrupted roster is not a publishable complete generation.

Old 50/200 breadth must remain numerically and operationally publishable when W1 auth is refused, one symbol fails, or the W1 deadline expires. Prefer an existing-schedule post-old-publication seam or prove an equivalent fail-soft ordering. This remains one breadth-owned product extension, not a new collector, scheduler, queue, retry service or control plane.

### R7 — complete the user experience and proof

Inside the existing `money` / Money & Breadth view, preserve view hashing and mount only after visibility. Add 3M/6M/1Y controls bounded by actual covered completed sessions, accessible sector×session cells, keyboard/touch selection, a detail panel with exact counts/exclusions/method/basis/generation and separate clocks, matching dated constituent states and existing research destinations. Preserve selection on return without replacing the shared SI view hash.

Cover English/Chinese, dark/light and 1440/768/390 widths. A failed W1 panel must not blank or corrupt the existing product. Public/entitled outputs must not leak withheld old board rows.

Tests must prove R1–R7 plus original A01–A26, old50/200/grader/access invariance, sibling real-fetch zero calls/writes, auth abort, global budget, atomic failure, stale-generation retention and cell/detail generation match. The suite must appear in an actual selected `gate: code` CI plan and hosted execution, not only a legacy definition or plan-position claim.

Remove the two unrelated `Timestamp.utcnow` replacements unless an in-scope failure and regression require them. Replace blanket legal/provenance language such as “every adjusted store is un-entitled” with the narrower inspected-provenance finding already ruled.

## 5. Return and acceptance boundary

Before further source edits after the return, the same writer must state a truthful repair START, exact owned worktree/head/base/path facts and obtain the current Source Continuity `CHECKPOINT_VERIFIED` receipt. No chronology rewrite.

Return one immutable repaired head with changed-file census, RED then GREEN commands/results, mutation/adversarial proof, exact selected CI step/run, real-input qualification state, browser/publication evidence state and one proposed Sol action. Remain Draft/HOLD.

W1 reaches BUILT_NOT_PROVEN only after the complete source-to-user journey exists and required non-production proofs pass. It reaches PROVEN_LIVE only after qualified real inputs flow through the actual publication route to served browser proof under the accepted access states. A PR, tests, green CI, deploy attempt or screenshot alone is not final acceptance.
