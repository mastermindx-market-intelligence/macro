# Parent focus restoration: separate integration follow-up

Recorded: 2026-10-22 04:35 UTC. This records a known baseline limitation and an independent principal ruling; it is not a product patch, approval, or production acceptance.

## Retained observation

The unmodified Macro source `ae6de4e56e2f826beab78f4de29fcaa89f27dbeb` and actual Terminal parent `e45bde2cac07ac3b29285ff70c40d68900fad62c` produced the retained baseline in `baseline_parent_restoration_v7/`. The saved view and the fresh frame's INIT.restore both contained `{x:0,y:3299,focusId:"im-catalogue-library-search"}`. Forward restored y=3299 at both later samples, while child focus remained BODY. There were no page or console errors. See `PARENT_FOCUS_BASELINE.md` and the raw archived driver/result/runtime/shutdown records.

The search input is static and is enabled synchronously before iframe onLoad/INIT. An earlier dynamic-mount hypothesis was corrected. Parent frame exposure/inert timing is a source-backed explanation, not an instrumented observation of the exact inert state at the focus call.

## Independent principal boundary

Reviewer: native `/root/intl_shell_acceptance_review`. The bridge's existing wheel/pointerdown/keydown cancellation observes only the child. Existing VISIBILITY expresses browser-tab visibility, not frame exposure or focus authority. A delayed child focus retry could override newer parent interaction that the child has not observed; a longer timer, animation frame, preventScroll or document.hasFocus alone does not establish the required ordering.

A separate LegacyPageHost–bridge integration change must define one-shot focus-restoration authorization for the current generation and history entry after exposure. Parent and child activity must invalidate pending restoration, newer user intent must win, and asynchronously queued grant/cancel messages must not be assumed to make that race safe. The design needs an explicit compatibility/version decision. This states the semantic requirement, not a chosen implementation.

Relevant pinned sources:
- https://github.com/mastermindx-market-intelligence/macro/blob/ae6de4e56e2f826beab78f4de29fcaa89f27dbeb/templates/shared_shell_bridge.js
- https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/e45bde2cac07ac3b29285ff70c40d68900fad62c/terminal/components/chrome/shared-shell/LegacyPageHost.tsx

## Acceptance treatment

Do not add a child timer-based focus retry to R3. Current driver v8 separates scroll restoration, saved-focus restoration and controller focus stealing. Only the exact already-observed BODY failure can be labeled known_baseline_failure; it still contributes to the overall failed count and nonzero exit. Other focus results are new failures.

A proven Tools/nested-link repair may be published to the existing Draft PR with this limitation explicit. Complete actual-parent acceptance cannot be claimed while the focus-restoration assertion fails. This follow-up has not been commissioned or implemented, and no Terminal or bridge focus code has been changed.
