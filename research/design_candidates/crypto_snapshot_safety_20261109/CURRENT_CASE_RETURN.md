# Current-case review: exact return and readable entry

## Outcome and source boundary

A valid current scenario now has a complete inspection journey: open its details, read Historical review, and return to that same case and horizon with its disclosure, scroll and review-button focus restored. Close still dismisses the entire managed drawer journey. A detached review has a deterministic “Open scenario details” destination.

This increment is relative to source parent `bcf8e84957017181dc323ff3c3a9f4b32b218799`, tree `2ce718df8579f6cb4e01ac6128c0d4e281c168ac`, assets `7fc541a886d1`. Final verified assets are `2698fd4fd4ed`. The retained data snapshot is unchanged; the test clocks and older case dates are explicit fixtures, not new observations.

The [publication receipt](current-return/PUBLICATION_RECEIPT.json) identifies every input, changed file, retained file, browser case and selected capture. This is dependent work in [PR #10901](https://github.com/mastermindx-market-intelligence/Macro/pull/10901), against incumbent PR #9580. Draft status and the separate integration/release gates continue to apply.

## User-visible behavior

| Situation | Visible destination and result |
|---|---|
| Review opened from the same current case and normalized horizon | **← Scenario details / ← 情景详情** returns one browser-history entry. |
| Detached review or predecessor at another horizon | **Open scenario details / 打开情景详情** replaces the current entry with the resolved case; unrelated URL parameters survive. |
| Case details on return | Reopen the matching Conditions and evidence disclosure, restore its reading position, and focus Historical review. |
| Native Back/Forward through the case | Consume that entry’s own qualified reading state. A repeated URL does not make two history entries interchangeable. |
| New valid named current-review entry | Start the dialog at the top so the case identity and **No qualified comparison yet** are visible immediately. |
| Same-entry current-review locale refresh | Keep the deliberate scroll position; the verified path retains focus on the persistent Close control. |
| Current case is expired | It remains inspectable and can be returned to. Existing Save eligibility continues to apply independently. |
| Saved storage cannot be read | Return to current details still works. The existing storage warning and reading retry remain available; navigation writes no saved collection. |
| Current identity does not resolve | Keep the existing unavailable-case recovery. Do not create a case parent for generic `memory` or missing named cases. |
| Close or Escape | Dismiss the complete managed journey and restore the original outer context and usable opener. |

The current-review header uses **Scenario / 情景**. Saved review retains **Saved snapshot / 已存快照**. No wording asserts that an inspectable case is fresh.

## One existing navigation and reading owner

The implementation remains in the existing [R4 script](../../../templates/crypto_intelligence_r4.js). There is no additional router, persisted reading registry or timer.

| Owner | Change and builder rule |
|---|---|
| `readingScope()` | Derive current-case identity from the rendered `scenario:<id>` panel and existing `activeScenario()` resolver. Require the rendered panel to equal the route panel, a nonblank string revision, a valid supplied cutoff date, and the supplied numeric horizon to equal the normalized route horizon. Preserve the exact supplied revision. |
| `history.state.reading` | Continue storing the existing panel/revision/horizon/cutoff tuple plus keyed disclosures, semantic focus and scroll. A mismatched tuple is ignored. Expiry does not disqualify an otherwise inspectable reader. |
| `rememberDrawer()` | Retain the rendered-address/history-signature guards so outgoing DOM cannot be captured into an incoming entry. Existing focus, disclosure and scroll listeners remain the capture owners. |
| `drawerReading()` | The existing saved-reading helper is renamed to reflect its expanded case scope. Saved/list qualification remains intact. |
| `hasDrawerParent()` | Add an optional expected-horizon check for current cases. Route normalization remains `"30"` → 30D, otherwise 7D; an omitted `h` is a valid 7D parent. Saved callers retain their previous behavior. |
| `pendingCaseReturn` | Generalize the existing single pending saved-return intent. It carries the exact expected tuple and child/parent addresses. A second activation while its traversal is pending does not add another Back. |
| `returnToCurrentCase()` | Resolve the case through the existing active scenario source at the bound horizon. It does not require readable saved storage. Use one native Back for a recognized immediate parent; otherwise use the existing replacement update. |
| `apply()` | Retain the matched pending intent locally before clearing the global on arrival. After rendering, compare the full tuple before forcing the review-button focus. |
| First current-review reading | Only a resolved `memory:<id>` qualifies. A closed dialog, changed rendered address/history signature, or incoming `popstate` means a new reading entry. Reset the dialog scroll before focus handoff. Same-entry locale refresh does not reset it. |
| Focus restoration | Reject disconnected, disabled, hidden, inert or unrendered targets and use the heading fallback. Focus remains the final effect: a focus callback owns any newer navigation or reading position. |

Current scenario controls use the existing semantic marker mechanism:

- `scenario-conditions` for the disclosure and summary;
- `review` for Historical review and its explicit return-focus intent;
- `snapshot-save` and `snapshot-remove` for distinct mutation meanings;
- `storage-retry` for reading recovery;
- `demand-evidence` for the existing evidence action and native Back.

Intent-specific mutation keys prevent old Remove focus from silently becoming Save after another actor changes the collection. A now-disabled Save cannot receive restored focus. A successful mutation’s own direct-render behavior is a separate presentation path; this increment does not claim to preserve reading through that path.

Current scenario details receive persisted reading state. Current-review entries use the default-entry policy above, without introducing another persisted review store. Generic Historical review and saved-case review keep their existing contracts.

## Implementation and design match

The source increment changes five paths:

1. Script template and its byte-identical served copy.
2. The affected browser test module.
3. The two retained HTML outputs, with exactly two asset-reference substitutions in each.

Sixteen other recorded inputs remain byte-identical, including the view JSON, projection, builder, CSS, template and shared assets. The script’s 20 recorded transformation steps reverse exactly to the published parent. Removing the appended browser cases also recovers the original test file.

Paper uses the existing R4.06 scenario/save reference (`G5-0`) and the existing review behavior row on the R4.08 scorecard (`QI-0`). The workflow must expose Historical review before Save and Inspect demand, then describe the intermediate parent return separately from whole-journey Close. The audit receipt records the actual node edits, geometry, source binding and complete readback; the source contract alone is not Paper mutation evidence.

## Native verification and why the intermediate runs are retained

The final run is **61 passed** in Chrome **157.0.8103.39**, with **61 contexts, 61 pages, zero page errors, zero external requests and zero WebSockets**. Pytest elapsed time was **35.64 s**; captured subprocess time was **35.989 s** and the process wrapper reported **36.24 s**. These are fixture verification timings, not product performance claims.

| Run | Evidence and interpretation |
|---|---|
| Published-parent baseline, PID 12376 | 22 failed / 35 passed. It exposed the absent current parent, lost current reading state and unusable focus restoration. |
| Initial candidate, PID 17024 | 55 passed / 2 failed. Both failures were the incoming-state fault harness. |
| Timing diagnostic, PID 25251 | A late-installed window listener saw already-rendered scenario DOM. Installing before the app saw the outgoing review and injected the mismatched identity before rendering. This two-page diagnostic is not additional product acceptance. |
| Corrected fault checks, PID 30048 | 2 passed with unchanged runtime assets `54f56205be7e`; the corrected test asserts that injection happens while review DOM still owns the old render. |
| First-view correction, PID 44832 | 59 passed at assets `35617892939a`. Visual inspection had shown the new review inheriting the case’s bottom scroll and hiding its identity/status. |
| New-entry baseline, PID 54712 | 2 failed: a different horizon at the same case ID, and two real entries with identical URL/serialized metadata, both retained the prior scroll. |
| Final complete affected set, PID 58382 | 61 passed at assets `2698fd4fd4ed`. The final set is exactly the prior 59 plus those two new-entry cases. |

The metadata receipts verify exact case-set relationships, source inverses and asset parity. The baseline and intermediate failures remain available with their stdout, stderr, JUnit, command, observations, scripts and input receipts; they have not been relabeled as successful runs.

Coverage includes EN/ZH, 7D/30D, expired and unexpired cases, 320/390/1440 widths, short 600px viewports, detached replacement, default-7D normalization, wrong-horizon ancestry, stale revision/cutoff metadata, native traversal, double activation, readable/unreadable storage, locale refresh, disabled/changed action targets, newer focus callbacks, evidence Back, saved-case return and recovery, current unavailable-case recovery, and the earlier mutation ownership guards.

[Capture references](current-return/CAPTURE_REFERENCES.json) identify six final dialog crops and two initial review crops retained to show the first-reading defect. Full content below a crop is exercised by the tests; the crops do not certify offscreen presentation. The corresponding final command is in [VERIFIED_RESULT.json](current-return/VERIFIED_RESULT.json).

## Build and acceptance sequence

Start from the [build map](README.md) and retain the existing producer/data boundary. Reproduce in an isolated checkout with the recorded view JSON and served shared dependencies. Use the actual selected-test command in the final result and an available supported Chromium executable.

The runners retain the actual native absolute paths and unique-output guards as execution evidence. A future reproduction needs its own isolated root and output directories; do not replay them into the recorded workspace or the primary checkout.

Keep the routing, saved collection and reading ownership together when changing this flow. A replacement implementation must prove the same-case/horizon return, first-review reading, same-entry locale preservation, whole-journey Close, safe focus fallback and newer-choice precedence, not merely render a parent button.

H5/model authority, alerts and delivery, paired source receipts, qualified historical results, hosted/independent acceptance, public-route cutover and admission/release remain separate holds. The unavailable-results state remains truthful throughout this UI improvement.
