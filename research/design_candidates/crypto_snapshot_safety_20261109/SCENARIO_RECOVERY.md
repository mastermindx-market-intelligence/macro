# Crypto current-case recovery

## Outcome

A missing current scenario or named historical-review request now stays explicitly unavailable. It never borrows the generic Bitcoin review's cutoff or substitutes another scenario. **Browse scenarios / 浏览情景** returns to the existing Scenarios view while retaining the selected outlook horizon and other route parameters.

This is a candidate presentation/navigation correction against parent `ce97e52d0cd131de2a1ca7e750574fcdc9482adb`, assets `29d1c4abafba`. It adds no historical performance results, model output, storage operation or route owner.

## Route contract

| Request | Result |
|---|---|
| `panel=memory` | Existing intentionally unbound historical-review context. |
| `panel=memory:continuation` with a matching current case in the selected horizon | Existing review bound to that exact current case. |
| A named current review that cannot resolve | Scenario unavailable; no borrowed title, cutoff, review requirements or save control. |
| `panel=memory:` with an empty explicit target | The same unavailable state. It is distinct from bare `memory`. |
| A current `scenario:<id>` that cannot resolve | The same unavailable state and Browse scenarios recovery. |
| `saved-item:<revision>` / `memory-saved:<revision>` | Existing retained-record qualification and recovery remain unchanged. |

The unavailable screen explains: **This scenario is not in the current snapshot for this horizon. / 当前快照在此周期内没有这个情景。**

Keep the requested panel in the address until the user chooses recovery. The existing `update("scenarios", {panel:null}, true)` owner clears that panel and replaces the failed entry. It preserves horizon, history window, search, filter and sort. Existing drawer-close handling focuses the Scenarios heading when no usable opener exists. The user can then inspect a valid case and dismiss it without returning to the failed request.

The screen describes absence from this snapshot/horizon. It does not infer why the producer removed a case or confuse a current-case request with removal of a device-saved record.

## Implementation

Only `templates/crypto_intelligence_r4.js` changes product logic:

1. The existing missing-scenario branch selects current-versus-frozen wording.
2. Its nonfrozen path adds one primary recovery action using the existing drawer action group and route helper.
3. The existing current-review branch rejects an unresolved explicit target before its generic fallback. A bare `memory` still follows the existing generic behavior.

The frozen path retains its original message and two recovery actions. No saved-case lookup, storage intent, browser-history primitive, retry mechanism, focus-restoration registry, producer, projection, model, CSS or template changes.

The served JavaScript matches the template. Retained `crypto-r4.html` and `vector-r4.html` change only their two asset-version references. All data and visible server-rendered content remain exact.

## Native evidence

The parent was reproduced with the exact new tests before changing native runtime files.

| Run | Result | Native observation |
|---|---|---|
| Parent, PID 13476 | **6 failed / 11 passed**, 30.86s pytest, 31.255s subprocess | Missing current cases retained the old ambiguous message; four explicit review requests still opened generic review. |
| Candidate, PID 19457 | **17 passed**, 10.71s pytest, 11.059s subprocess | Complete targeted recovery and control paths pass. |

Each run used **17 contexts and 17 pages**, with zero page errors, external requests or WebSocket traffic. Native Chromium was 157.0.8103.39. These are local historical/synthetic fixtures, not live market observations.

The 17 cases cover:

- Six missing/malformed current-case requests across EN390 and ZH320, with no substituted date/title/results requirements or save action.
- Keyboard recovery, unchanged history length, preserved h/window/q/filter/sort, destination-heading focus, subsequent valid 30-day inspection and Escape return to its opener.
- Four intentionally generic and valid current-review controls.
- Six existing unusable-saved-version cases, which still cannot borrow current context.
- One existing missing-current/legacy-saved path, preserving optional evidence-digest behavior.

No storage writes occur in the new recovery journeys; an opaque retained record remains exact. Four native drawer captures—two request categories in each locale—were inspected; both categories intentionally render the same concise unavailable state.

The publication readback, PID 22466, verifies **five changed source/served/test paths and 16 unchanged inputs**. Reversing three product replacements and removing the appended tests recovers the exact parent. This is focused affected proof, not a complete browser-suite run.

## Reproduce and inspect

The existing browser test module contains the acceptance cases. The exact selectors, executable and result appear in [CANDIDATE_RUN.json](scenario-recovery/CANDIDATE_RUN.json). Tests serve the retained candidate on an isolated loopback origin and restrict browser traffic to that origin.

- [Exact source and proof receipt](scenario-recovery/PUBLICATION_RECEIPT.json)
- [Parent inputs](scenario-recovery/PARENT_INPUTS.json)
- [Owned transforms](scenario-recovery/TRANSFORMS.json)
- [Baseline results](scenario-recovery/BASELINE_RESULTS.xml)
- [Candidate results](scenario-recovery/CANDIDATE_RESULTS.xml)
- [Inspected native captures](scenario-recovery/captures)

The retained runner scripts record this isolated native directory and historical execution. They are evidence, not an instruction to replay an existing output directory or perform a release.

## Remaining work and boundaries

Next: make native route hrefs preserve the same selected context as ordinary clicks, and repair keyboard focus when a link inside a retiring view opens another view. Expired current-scenario card qualification and same-case return from valid current review are separate subsequent improvements.

Prior H5/model, alert, qualified historical-result, hosted/independent visual acceptance, public-route cutover and admission/release holds remain. Draft status and exact existing owners are preserved. The repair is not production acceptance.
