# Current Save/Remove: retain the reader

## User outcome

Saving or removing a current case keeps the open Conditions and evidence disclosure and its reading position. The confirmed action becomes the opposite action, with keyboard focus on that usable control. If removal leaves a disabled Save control—for example, after expiry—focus goes to the case heading. The case stays on the same route and history entry.

This extends the existing storage and per-entry reading owners in `templates/crypto_intelligence_r4.js`. It adds no second history store, router, retry policy, storage mutation path or timing loop. Read this alongside [storage safety](SNAPSHOT_SAFETY.md), [current review and return](CURRENT_CASE_RETURN.md) and [saved navigation](NAVIGATION.md).

## Problem and exact scope

At parent `0ec213ab7bb570a0cebc28f2e4112cde14ff59c2` / assets `2698fd4fd4ed`, the confirmed storage path called `renderDrawer()` directly. Replacing the body closed an expanded disclosure, clamped scroll, and sometimes left focus targeting a disabled action. The automatic reading listener could then record that reset state.

The new baseline reproduced **19 failures with 72 passing controls**. All 91 selected cases now pass on assets `a8bf00034c30`. This is an affected native fixture run, not an entire application-suite or production-acceptance claim. [Exact inputs, outcomes and cases](current-save-reading/PUBLICATION_RECEIPT.json).

## Behavior by outcome

| Situation | Storage behavior | Visible reader and focus |
|---|---|---|
| New Save confirmed by exact serialized readback | Existing one write; preserve the source fields, recorded time and issue evidence | Keep fresh disclosure/scroll; show and focus Remove |
| Remove confirmed | Existing one write removes every exact revision match; unrelated parsed entries and order survive | Keep fresh disclosure/scroll; focus enabled Save, otherwise heading |
| Stale Save is already present | Zero writes; retain the saved version, time and evidence | Reconcile to Remove and preserve the reader |
| Stale Remove is already absent | Zero writes; never recreate the record | Reconcile to Save and preserve the reader |
| Collection cannot be read | No write | Retain the original body, action, focus and scroll; existing unreadable message |
| Write/readback cannot confirm the postcondition | No automatic replay, redirect or success assumption | Retain the original reader; existing unconfirmed message |
| Reading metadata cannot be persisted, with ownership otherwise unchanged | Do not replay the already confirmed storage action | Keep the freshly captured visible reader; do not claim history persistence |
| A newer route, language, history entry/metadata or focus choice intervenes | Preserve the real, already completed storage outcome | Yield the older UI continuation |
| Current identity cannot qualify a reading, but this DOM/entry is still owned | Existing storage rules still govern the requested action | Reconcile confirmed controls without borrowing old reading metadata |
| Remove from a frozen saved-item panel | Existing confirmed removal path | Existing replace into Saved snapshots; `apply()` owns the resulting focus |

A programmatic activation with unrelated focus still does not rebuild that other focused UI. The old control can remain visible when a newer history choice owns the entry; the next legitimate render reconciles it. That is not a reason to replay the storage action.

## Continue these owners

| Owner | Responsibility |
|---|---|
| `save()` | Explicit displayed intent; full collection; one existing write/readback; confirmed outcome; owned UI completion |
| `readingScope()` | Existing qualified panel/revision/horizon/cutoff tuple |
| `captureDrawerReading()` | Fresh DOM capture with separate ownership and reading-eligibility outcomes |
| `ownsDrawerCapture()` | Address, language, body subtree, history length and exact history-state signature |
| `persistDrawerReading()` | Merge only `reading` into this entry; qualify the observed result before adopting it |
| `rememberDrawer()` | Automatic focus/toggle/scroll capture, gated by the existing suspension flag |
| `matchingDrawerReading()` / `restoreDrawerReading()` | Shared tuple qualification and disclosure/scroll projection for ordinary navigation and confirmed mutation |
| `usableDrawerFocus()` | Shared reachable, connected, enabled and visible focus qualification |
| `apply()` | Existing navigation/locale rendering and parent-return behavior |

The capture returns `owned: false` for an obsolete DOM/history context. An owned capture can instead have `reading: null` when the case identity cannot qualify. These outcomes are different: obsolete continuations yield; an owned unqualified case may still reconcile confirmed controls.

## Completion sequence

1. Keep the existing storage action and postcondition checks. At action start, witness history length as well as the existing URL/language/control.
2. After confirmation and focus ownership, capture the current DOM. Use its actual expanded disclosures and scroll; do not substitute a possibly older `history.state.reading`.
3. Suspend automatic reading capture while rebuilding with the already confirmed collection. This adds no extra storage read.
4. Recheck the route, language, history signature/length and focus. Project only a fresh reading whose full tuple still matches.
5. Choose the actual resulting enabled action, or the heading. Capture the completed projection with that intended semantic focus key.
6. Persist this projection before final focus, including when Save was activated inside an enclosing render's focus callback. Merge unrelated metadata unchanged. Adopt `renderedHistory` only if the readback signature exactly matches the requested metadata and the original URL/language/subtree/history length still belong to this continuation.
7. Restore the previous suspension value and focus once. There are no later projection or persistence effects in the mutation completion. A focus callback owns its newer destination.

A failed optional history write with unchanged history may leave the visible projection usable. A changed history signature is a newer choice, even if URL and focus happen to be unchanged. A same-URL, same-metadata `pushState()` during storage is detected by history length. A callback that writes and then throws is reconciled against the observed history without replaying the write.

The existing review-parent, Close, current-review initial scroll and detached-entry rules remain in [their contract](CURRENT_CASE_RETURN.md). The same helper policy is reused; no parallel restoration policy is introduced.

## Browser proof

| Run | Exact result | Meaning |
|---|---|---|
| Parent baseline | 19 failed / 72 passed; pytest 58.32 s, subprocess 58.703 s, wrapper 58.80 s | Existing runtime with the appended affected tests |
| Initial candidate runner | Exit 4; zero cases executed | The runner duplicated the module prefix in its selectors; this is a harness selection error |
| Corrected runner | **91 passed**; pytest 55.72 s, subprocess 55.978 s, wrapper 56.07 s | Same candidate source and tests, corrected selector list |

The corrected run used Chrome **157.0.8103.39**, **91 contexts / 97 pages**, with **zero page errors, blocked external requests or WebSockets**. The 97 pages include existing cross-tab intent checks. The selection-error run launched no tested browser cases and is not counted as passing proof.

The 24 new cases cover confirmed Save/Remove and expired Remove in EN/390 and ZH/320; both idempotent intents; unreadable and unconfirmed storage; fresh reading when optional persistence fails; newer focus/navigation/history during persistence; heading-focus navigation; Save inside a locale render callback; same-address metadata/entry changes during storage; and an owned case with unqualified reading identity. The remaining 67 cases retain current/saved review, parent/Close, locale, recovery, focus and cross-tab intent behavior. Counts from older phases overlap and must not be added into another complete-suite claim.

Six new mutation dialog crops were inspected, at 390px English and 320px Chinese with 600px viewport height. They show the open disclosure and resulting action at the retained reading position. The run also generated 15 retained workflow captures; those are recorded separately from the six new visual inspections. [Capture identities and hashes](current-save-reading/CAPTURE_REFERENCES.json).

## Source conservation and reproduction

Five recorded paths change: template JS, served JS, browser tests, and the two generated page asset references. Sixteen recorded inputs remain exact, including the HTML template, CSS, projection, server tests, builder, source JSON and shared assets. Template and served JS match. Each HTML page differs only in its two asset-version references.

All six source transformations invert exactly to the parent. Removing the appended tests recovers the parent's complete browser module. The original baseline, selector failure, corrected runner, JUnit, process outputs and native observations remain in `current-save-reading/`; [the receipt](current-save-reading/PUBLICATION_RECEIPT.json) binds their hashes to the candidate assets.

The runner scripts record the isolated native verification paths and exact commands as historical evidence. Reproduce in a fresh authorized checkout using the same source inputs and local fixture browser configuration. Do not overwrite their original evidence directories or infer authorization to deploy from these scripts.

## Paper and remaining interface work

[Paper interaction page](https://app.paper.design/file/01M6Y3F0NXNDPAKJMJGCAD759Z/p-1-0) uses G5 for current-case interactions and QI for the implementation scorecard. [Saved-case Build 3IP](https://app.paper.design/file/01M6Y3F0NXNDPAKJMJGCAD759Z/p-4-0) retains the storage, frozen identity and navigation contracts. The confirmed mutation's reader continuity belongs with these existing contracts rather than another feature/state registry.

The native captures expose a separate visual follow-up: current Historical review and Save/Remove controls lack the spacing shown in Paper, and the existing confirmation toast overlaps Inspect demand. Address those through the current action layout and status owner; preserve this confirmed-action behavior.

## Acceptance limits

This is isolated historical/synthetic browser proof. It does not establish hosted or independent visual acceptance, current-market freshness, personal saved activity, public-route cutover, merge/deployment or production replacement. Existing H5/model, alert integration, paired-receipt, qualified historical-result and admission/release holds remain.

Web Storage's read/write/readback sequence is not atomic cross-tab compare-and-swap. Optional reading persistence does not become a storage-confirmation guarantee, and the UI never automatically retries an unconfirmed mutation.
