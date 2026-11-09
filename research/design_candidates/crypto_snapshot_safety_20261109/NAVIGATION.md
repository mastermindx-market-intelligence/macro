# Saved-case navigation and reading continuity

## Delivered boundary

This phase extends the existing R4 drawer, hash router and browser history entry. It follows storage-safety commit `2c04fc37d239f4bf27b6efaed98b229256ea337e` on dependent Draft PR #10901. Asset version: `7d9cb01e7600`.

The accepted Paper flow is: **7-day ancestor → Saved snapshots → original 30-day saved case → Historical review → same saved case → Close to the original 7-day ancestor**. The saved version supplies its own horizon, cutoff and original fields. A return never substitutes the current scenario.

The frozen-case typography/content hierarchy remains the next phase. This phase introduces the named parent control and its 44px target but deliberately retains the existing body composition. Paper file `01M6Y3F0NXNDPAKJMJGCAD759Z`, states 09–16, remains the design contract.

## Ownership and architecture

| Concern | Existing owner and extension |
|---|---|
| Route | `state`, `open`, `update`, `apply`; no second router |
| Journey ancestry | Existing `history.state` fields: `r4`, `drawer`, `previous`, `depth`, `detachedOrigin` |
| Reading state | One optional `history.state.reading` object attached to that entry |
| Saved data | Existing `stored` / `savedVersion` exact-revision reader; no new storage key |
| Parent activation | `returnToSavedCase`, with a single bounded pending return intent |
| Render/focus | Existing drawer owner; semantic focus keys, never persisted DOM references |
| Language | Existing locale observer rebuilds from the same saved record and entry |

Reading metadata has `panel`, `revision`, `horizon`, `cutoff`, `disclosures`, `focus`, and `scroll`. It is accepted only for a readable saved-list scope or the exact usable saved case/review scope. The case must match panel, revision, original horizon and cutoff. Scroll must be finite and nonnegative.

The renderer remembers the rendered URL **and the complete serialized history metadata**. URL alone is insufficient: two native history entries may share the same URL and have different disclosure/scroll state. No secondary history stack or render-generation counter is added.

## Route and parent behavior

Opening a saved list item passes its validated original horizon. Opening a saved-item/review also re-reads the requested revision. A usable saved route with the wrong `h` is repaired through `replaceState` on the existing entry; unrelated parameters, prior address, journey depth and detached origin remain intact.

A named parent is supported by managed drawer metadata, an integer depth of at least one, a recognized matching view, and the exact expected previous panel. A detached saved-item can still be the real parent of a review that was subsequently opened from it. Its `detachedOrigin` flag must not erase that immediate relationship. A legacy parent's incorrect horizon is repaired in place.

| Destination context | Visible action | Effect |
|---|---|---|
| Review with proven saved-case parent | ← Saved case / ← 已存情景 | One native Back |
| Truly detached review | Open saved case / 打开已存情景 | Replace with that exact saved case |
| Saved case with proven list parent | ← Saved snapshots / ← 已存快照 | One native Back |
| Detached saved case | Open saved snapshots / 查看已存快照 | Replace with the saved list |
| Close, managed nondetached journey | Close / 关闭 | Existing `history.go(-depth)` to the outer origin |
| Close, detached journey | Close / 关闭 | Existing same-entry removal of the panel |

Parent activation re-reads storage **before** history movement. Missing/duplicate/unusable requested versions stay on the review entry and show the unavailable requested-version state. Unreadable collections show the distinct unavailable-collection state. These failures never run Back and never borrow current context.

The one pending intent records revision, child address and parent address. It suppresses a duplicate parent activation while native Back is pending and is consumed only by its exact expected arrival. Other owned open/update/close actions clear it. Arrival re-reads storage again before any old reading state is restored. This handles removal between activation validation and the destination render.

## Reading and focus behavior

Capture happens before owned open/update/close and locale rerenders, plus native disclosure toggle, focus changes and `scrollend`. The pending incoming entry is never overwritten with outgoing DOM during `popstate`. Every popstate is processed; only an obsolete/already-rendered hashchange is skipped.

Disclosure and focus identities are semantic: `case-details`, `saved-evidence`, `review`, `parent`, `saved:<revision>`, `close`, and `heading`. Resolution uses known controls and exact dataset equality, not caller-supplied selectors. Native details remain native; restoration sets their open state, then restores scroll and focus with `preventScroll`.

A named review return focuses Historical review in the saved case, including legacy entries with no reading metadata. If a recovery retires the focused parent control, the unavailable heading receives focus. Initial deep-link autofocus is a separate contract and may legitimately remain on the native dialog's initial control.

Close retains a legitimate native focus destination when visible. Otherwise it restores a connected visible opener within the active view, then falls back to that restored view's heading. A hidden/removed opener cannot strand focus.

Reading capture/restoration is suspended with prior-value restoration during nested rendering. A focus callback may open a different panel; no late restoration step may overwrite that newer destination.

**Scroll limit:** native Back/Forward restores the last settled scroll position captured by `scrollend`. Explicit parent/open/close/language actions capture current position synchronously. This does not claim every interrupted, unfinished scroll is persisted.

## Reentrancy and storage preflight

All storage-bearing panels—saved list, current scenario, saved case and saved review—read before replacing the drawer subtree. The preflight checks URL, language, prior subtree and active element. If a storage callback creates a newer navigation or focused control, the older render yields. Confirmed-save rerenders can use their already confirmed collection.

Opening a modal can itself cause focus callbacks. Opening focus-event observation and route/subtree/focus guards protect the newer owner. No later focus effect runs after restoration triggers newer navigation. Optional history metadata replacement failure must not prevent basic navigation.

The storage phase's limits still apply: read/write/readback is not atomic cross-tab compare-and-swap. There is no new background storage observer. An unrelated change after a completed render is resolved at the next owned read.

## Verification and failure classification

- Exact parent baseline: **16 failed / 40 deselected**, 18.61s pytest / 19.470s subprocess. These demonstrate shared horizon, parent-control, locale/disclosure and outer-focus defects; they are not 16 independent bugs.
- Initial candidate: **93 passed / 7 failed** out of 100, 64.19s pytest / 64.777s subprocess. All 39 contract checks passed. Browser: 62 contexts / 68 pages, Chrome 157.0.8103.39, zero page errors or outside-origin/WebSocket requests.
- Six failures came from a heading-focus assertion accidentally inserted into the old initial-unavailable-deep-link test. The assertion belongs to recovery after a focused parent control is retired; it was moved there.
- The seventh test installed a late popstate listener that removed the record **after** the app had read and rendered the arriving case. A diagnostic preserved the observed sequence. The corrected test removes via the captured native storage setter immediately before delegating one real native `history.back`, and asserts one invocation.
- Corrected affected run: **10 passed / 51 deselected**, 14.45s pytest / 15.405s subprocess, 10 contexts / 10 pages, zero page errors or outside-origin/WebSocket requests. Product JS/CSS and saved pages were unchanged between runs.
- JUnit identity comparison confirms **100 unique cases with passing coverage: 39 contract + 61 browser**. Three previously passing parent-recheck cases overlap. This is not a single-run 100-pass claim.
- Native navigation captures at 1440px EN, 390px ZH and 320px EN were inspected. They show restored reading state, so some body content is intentionally scrolled under the fixed header. Header actions pass ≥44px target and viewport/drawer overflow assertions.

The 21 added browser cases cover managed and detached journeys, native Back/Forward, same-URL distinct entries, original-horizon repair, missing/duplicate/unreadable return, disappearance before arrival, locale disclosure/scroll/focus continuity, hidden/removed outer opener fallback, and storage/focus callbacks opening newer destinations.

## Source proof and next phase

Twenty-nine recorded JS transformations and one CSS transformation invert exactly to parent `2c04fc3`. Template and served assets match. Fourteen remaining source inputs are unchanged; the two saved pages change only their two asset version references from `3786626cb4d5` to `7d9cb01e7600`. Node syntax check passes. No builder, data, model projection or shared asset change.

Next: apply the accepted original-condition-first frozen layout, compact review qualifications, original evidence disclosure and spaced recovery actions. Preserve temporal truth: `status(s)` computes expiry against today; do not relabel today's expired status as original-cutoff progress. Keep source fields, captured dates/quality and legacy digest absence honest.

Hosted/independent visual acceptance, H5/model authority, alerts, public-route cutover, release and admission remain held. No production replacement, personal storage, current-market freshness or forecast-performance claim is made.
