# Crypto route context and focus continuity

## Outcome

Copying a route link, opening it in a new tab and ordinary activation now retain the same research context. When an owned in-section activation would retire the focused view, focus moves to the existing destination tab before that view is hidden. A newer choice made during that focus handoff takes precedence.

This candidate builds on `059b9a6acd6d84726e20781b52a66e0c2a5ec651`. Runtime assets are `f15feec04ead`. It extends the existing R4 navigation owner; no router, state store, history primitive or focus registry is added.

## Link contract

The existing `apply()` route loop copies its normalized URL parameters, removes only `panel`, and serializes each supported anchor with the existing `address()` helper. It never mutates the current parameter object while deriving destinations.

| Context | Behavior |
|---|---|
| Outlook horizon | Preserve `h`; opening a native link from the 30-day view must not silently become 7-day context. |
| Chart, Markets and extra parameters | Preserve `window`, `q`, `filter`, `sort` and unrelated parameters, matching ordinary route activation. |
| Open drawer | Remove `panel` from route destinations without dismissing the current drawer merely to update links. |
| Current pathname/query | Keep the existing entry page and query; assign a fragment destination. |
| Navigation state | Existing `apply()` remains the sole owner of `aria-current` and visible sections. |

The href is correct before interaction. Copying it or using a browser-native new-tab action therefore receives the same destination as the application route handler.

## Focus and action ownership

The root route-click branch handles only an unconsumed, unmodified primary activation. A previously prevented event or Meta/Control/Shift/Alt/nonprimary activation is left to the existing browser/caller behavior.

Before the owned action writes history, it checks whether the active control belongs to a view that the destination will retire. If so, it focuses the existing persistent destination tab. This allows the old section to remain visible throughout the handoff; it avoids revealing an incoming hidden heading or creating a second visible view.

After focus, the branch requires its URL, locale, serialized history state and history length to remain unchanged. Focus must still belong to the intended connected, visible destination control. Otherwise it yields before calling `update()`. A removed target also aborts continuation. The branch captures the requested view before focus, so later work does not reread a mutable route destination.

A persistent navigation control already survives the view change and needs no handoff. Once `update()` runs, there is no late focus write that could overwrite a newer action.

This is the contract for owned route-link activation when the retiring view owns focus. It is not a new general focus-restoration policy for every arbitrary hash assignment or Back/Forward event. Existing saved-case, dialog Close, horizon, chart-window, language and shock owners retain their behavior.

## Implementation and conservation

Only two sections of `templates/crypto_intelligence_r4.js` change:

1. The existing route loop now projects hrefs alongside its current-state labels.
2. The existing root route-click branch honors consumed/native-modified actions and performs the guarded precommit focus handoff.

The served JavaScript matches the template. The two retained candidate HTML pages change only their two asset-version references. Their static content, data, template, CSS, projection, model and shared-shell files remain exact.

Five source/served/test paths change; 16 other runtime inputs remain unchanged. Reversing the two product replacements and removing the appended test block recovers the exact parent.

## Native evidence

| Run | Result | Meaning |
|---|---|---|
| Main parent baseline, PID 56462 | **10 failed / 11 passed**, 13.44s pytest / 13.830s subprocess | Reproduces bare native destinations, missing focus handoff and handling of consumed/Alt clicks. |
| Additional parent history cases, PID 65188 | **2 failed**, 3.44s pytest / 3.782s subprocess | Two added same-URL history choices cannot receive the missing handoff on the parent. |
| Candidate, PID 69813 | **23 passed**, 13.15s pytest / 13.408s subprocess | The complete affected case set passes in one run. |

The baseline union exactly matches the candidate's 23 case identities. The main baseline has 21 contexts/pages; the added baseline has two. The candidate has **23 contexts and 25 pages** because the English and Chinese native Meta-click paths each open a real second page. All three runs report zero page errors, external requests and WebSocket traffic.

The passing cases establish:

- Native hrefs retain the same path/query and complete route parameters, with the drawer panel omitted.
- Real native Meta-click opens the same context in a second page, while the originating URL/history stays unchanged; ordinary activation then reaches the identical copied destination.
- Keyboard in-section navigation focuses the destination tab while the outgoing view is still visible and before history changes. Only one view is visible afterward; persistent navigation retains focus.
- Newer view, locale, focus, removed-target, same-URL replaceState and same-URL pushState choices survive without a stale continuation.
- Six bounded synthetic consumed/modifier probes produce no extra application navigation. Native default behavior is canceled after the application listener in these probes; only Meta-click is claimed as a complete native second-page gesture.
- The existing horizon/drawer/chart path and six missing-case recovery paths still pass.

The EN390 dark and ZH320 light viewport captures were inspected. Four recovery captures generated by the affected regression cases are byte-identical to their previously inspected files; they are referenced in place, not duplicated.

Publication readback, PID 74938, exit 0, verifies source/test inverses, exact input hashes, run identities and capture metadata. These are local historical/synthetic fixtures. This is a focused affected run, not a complete browser-suite or production-acceptance claim.

## Builder entry points

- [Complete proof and input conservation](route-context/PUBLICATION_RECEIPT.json)
- [Exact candidate command](route-context/CANDIDATE_RUN.json)
- [Candidate results](route-context/CANDIDATE_RESULTS.xml)
- [Baseline results](route-context/BASELINE_RESULTS.xml)
- [Additional history baseline](route-context/HISTORY_BASELINE_RESULTS.xml)
- [Source/test transforms, including the main baseline test block](route-context/TRANSFORMS.json)
- [Capture locations and exact identities](route-context/CAPTURE_REFERENCES.json)
- [New viewport captures](route-context/captures)

The retained runner scripts record an isolated native verification directory and its completed execution. They are evidence, not an instruction to replay existing output directories or release the candidate.

## Next work and existing gates

Next: qualify expired current-scenario cards before inspection, using the existing expiry/progress owner and preserving original conditions. Then add a same-case return from valid current historical review without altering whole-drawer Close.

H5/model, alerts, qualified historical results, hosted/independent visual acceptance, public-route cutover and admission/release holds remain. All denied/unknown-effect boundaries retain their scope.
