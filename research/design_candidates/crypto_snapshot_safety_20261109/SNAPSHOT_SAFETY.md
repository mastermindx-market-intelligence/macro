# Saved-snapshot behavior and builder contract

## Source and ownership

Parent: `5e496c24c962e85a4f7f514dd43dc61443b95cab`, the open Draft Crypto R4 source in Macro PR #9580. This change uses the existing hash router, dialog, language observer, toast and `mmx.crypto.r4.scenarios.v1` local-storage key. It introduces no second storage owner, migration, queue, background retry or navigation stack.

The served `site/crypto_intelligence_r4.js` must stay identical to `templates/crypto_intelligence_r4.js`. The existing builder hashes the HTML template, CSS and JS together. Its saved `crypto-r4.html` and `vector-r4.html` pages therefore receive the new asset version without refreshing their source data or body markup. Public `crypto.html` and `vector.html` routes are unaffected.

## Read the collection before deciding what to show or change

`stored()` returns a ready or unavailable result. A missing key is a readable empty array. Invalid JSON, a non-array value, an empty string, a denied access or a parsed non-finite number is unavailable. Do not replace those states with an empty array.

A ready result retains the complete parsed `entries`, the original serialized value and a filtered display projection. Only the display projection is limited to 50 usable entries. The complete entries are the preservation input for every mutation.

A usable saved version has the original research authority, a nonempty exact revision, a supported numeric 7- or 30-day horizon, real ISO cutoff/expiry dates in order and the original bilingual case fields. Its `issue_evidence` digest is optional for legacy records. Missing digest does not permit reconstruction from current evidence.

`savedVersion(collection, revision)` requires exactly one usable match across the whole stored array. Missing, duplicate or malformed requested versions cannot borrow the current scenario horizon, cutoff or case fields. Both `saved-item:` and `memory-saved:` resolve through this rule.

## Act on the displayed intent

The button captures Save or Remove when rendered. It does not reinterpret a late click as the opposite action after another tab changes storage.

| Displayed intent and fresh state | Mutation | Result |
|---|---|---|
| Save; exact usable version already present | None | Already saved; preserve saved_at and issue_evidence byte-for-byte because storage is not written. |
| Save; same revision ambiguous or unusable | None | Explain that the stored version cannot be read reliably. |
| Save; absent and current case eligible | Append original case plus capture-time evidence | Apply capacity only to this actual new save. |
| Save; absent but case expired, insufficient or unavailable | None | Explain that available evidence cannot support saving. |
| Remove; exact revision absent | None | Explain that the snapshot is no longer saved. Never append. |
| Remove; one or more exact matches present | Remove every exact revision match | Preserve all unrelated parsed entries and their order. |
| Either intent; collection unavailable | None | Explain the read failure. |

For a genuinely new Save, retain the existing 50-snapshot capacity using recognized snapshot entries in array order. Opaque entries remain present and do not become cleanup targets. Do not apply retention trimming during Remove or an idempotent completion.

## Confirm the storage effect separately from view work

Prepare the serialized next array before writing. Attempt `setItem` once. Read through the same owner afterward and require both a readable collection and the exact serialized value just prepared.

A thrown write, a silently dropped write, a write followed by a throw, a failed readback or a mismatched readback is unconfirmed. The interface says:

> The change couldn’t be confirmed. Check Saved snapshots before trying again.

It does not report success, navigate to the saved list, replay the write or claim that no change occurred. The original action remains available. Readback is a confirmation observation, not atomic compare-and-swap: another tab can still race between synchronous storage operations. The tests prove stale displayed intent and preservation for the tested sequences; they do not prove simultaneous cross-tab linearizability.

A later list read can fail after a removal was already confirmed. Keep the confirmed outcome. The unavailable-list message is simply “Saved snapshots couldn’t be read.” The “No changes were made” clause belongs only to a pre-write failure, never the general list state.

## Respect the current interaction owner

Before acting, capture the URL, language, panel and original trigger/focus. Storage completion may update the current action only while that same trigger is connected in the same drawer, route and language.

A newer focus movement during readback takes precedence. A programmatic Save must not replace a different focused control. When a confirmed frozen-case Remove navigates to Saved snapshots, the existing `apply()` owns its displaced focus; return immediately afterward. Do not perform a late focus change that steals focus from a panel opened synchronously by the first focus callback.

For current-case completion, re-render with the just-confirmed per-render collection and restore the recreated action only while the original route/language still owns the result. This is not a global cache or a new render counter.

## Recovery and copy

- Unreadable collection: “Saved snapshots unavailable”; one explicit “Try reading again” action reuses the existing reader; “Open current outlook” is a separate deliberate destination.
- Readable array with only unsupported records: “No supported snapshots can be opened here.” Do not call it empty or claim the collection was unchanged after a successful removal.
- Requested version unavailable: preserve the unavailable-version state without current context. Its richer destination controls remain part of the next navigation/layout phase.
- Old usable version without a captured digest: keep its original conditions and cutoff visible and retain the existing honest missing-digest explanation.

## What was verified

The original-source baseline ran 35 new cases: 34 failed and one passed. One failure was an ambiguous test locator; its first correction exposed a nonexistent Python Locator method. Both harness failures are preserved as such. With the locator scoped to the drawer and focus inspected through the supported DOM evaluation API, the focused parent-source rerun demonstrated the actual unrelated-focus loss. The qualified baseline therefore demonstrates 34 failing behavior/copy cases across shared defects, not 34 independent bugs.

The final browser suite has 40 cases, including the five existing cases. It uses a fresh HTTP fixture origin and explicit installed Chrome, not personal storage. The final harness allows requests only to that exact ephemeral origin and blocks WebSockets. No external requests or sockets were attempted in this run.

The candidate run covered all 40 browser cases and 36 contract cases successfully. Three unchanged Python integration cases initially lacked imported source dependencies. Twenty exact-parent dependency files were restored in the owned verification root and those three cases passed separately, including the test that preserves legacy-route sentinels during a synthetic preview build. No current-data build, model execution, collection or deployment was performed.

The eight final PNGs are dialog-element crops. They show the rendered recovery and confirmation states at the tested English desktop and Chinese/mobile sizes. The current desktop toast is positioned against the viewport and can extend outside a dialog crop; these crops do not establish full-viewport toast placement. Hosted and independent visual acceptance remain outstanding.

## Next safe implementation phase

Keep this safety behavior and its tests intact. Continue in the existing drawer/history owner:

1. Pass the validated saved horizon when opening a list item.
2. Add an explicit same-revision parent return from historical review; use one browser Back only for a verified immediate parent.
3. For a truly detached review, replace the current entry with the exact saved case. Do not invent an ancestor.
4. Preserve disclosure state, semantic focus and reading position only for the same still-usable saved revision across locale and parent return.
5. Keep full Close as the complete drawer-journey exit. Restore a visible opener in the restored active view, otherwise that view’s heading.
6. Apply Paper’s original-condition-first saved-case hierarchy with concise evidence disclosures, clear recovery action spacing and readable feedback. Verify full-viewport feedback placement before judging it.

The accepted journey is a 30-day saved case opened from a 7-day view → review → parent → Close back to the original 7-day ancestor. Native Back/Forward, detached cases, disappearance/unreadable storage, locale changes, small widths and reentrant focus all require actual browser proof.
