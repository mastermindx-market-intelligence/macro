# Macro workspace experience — implementation packet

## Authority and outcome

The Chairman explicitly renewed and expanded the Macro Dashboard upgrade on 2026-11-09 after the initial search/dialog pass was insufficient. The desired outcome is a coherent, responsive, polished daily intelligence workspace, implemented in the existing Jinja + live JavaScript product and verified through the normal release path. Source/PR/CI alone do not prove production acceptance.

Protected procedure pin: `494d095813dad415938800fa0e4d2719497738fa`.
Macro acquired base: `9a13c64bf69f782332afa29efb09fe48ee30b857`.
Operation: `macro-experience-redesign-20261109-astra-02`.
Workspace acquisition returned PARTIAL; the original native mmx-workspace status reconciled a clean, owned branch at the exact base, path `/Volumes/Mastermind/agent-workspaces/macro/web/macro-experience-redesign-20261109-astra-02`. No acquisition replay.

## Primary question and composition

Archetype D: What is the US market outlook, and what would change it?
The existing #regime-radar remains the primary US decision surface. The page gains one compact h1 with US scope and a local anchor index. Reading order is outlook/history, market tape, priorities and events, market drivers, briefing and monitoring, existing research destinations. Six L1 groups maximum. DOM, visual and keyboard order must agree.

The earlier search/dialog source PR #10896 remains on its original carrier. Its same-carrier CI repair was published at `88577573e30d73291381bbe3f9f50c9a0ee0bea8` and merge-on-green rearmed after exact-head readback; runtime remains identical to `5b4317c83934c8b82387fbad2d7afa3f5c57c6bb`. That repair has separate source-linked evidence at `research/ux_polish/macro-20261109/CI_REPAIR.md`. This new owned branch changes the main page composition and history interaction, and does not duplicate the search/dialog controller work. The current shared-nav, policy producer, sector adapter and risk dialog lifecycle carriers remain owners of their existing scopes.

## Frozen design decisions

- Compact page identity and page-local section links, within the existing canonical product navigation. No new global header or shared-nav override.
- Existing scorecard receives a deliberate title, stronger verdict hierarchy, quieter gauge treatment and better proportions. Keep measured-versus-capped semantics and all live IDs/data bindings.
- History is visible on mobile, with readable chart labels and a native keyboard/touch range control. Extend the incumbent path enhancement; retain mx5pathlive updates and selected historical date. No new fetcher, polling or chart runtime.
- Move Markets to its visible position in the actual DOM. Group the existing cards with semantic section headings and a common material/spacing rhythm.
- Replace the cut-off five-event timeline with a readable dated agenda using exactly the same producer rows, complete EN/ZH names and explicit impact labels. Preserve None versus empty versus populated states and the existing live release overlay/dialog.
- Use explicit native detail buttons, consistent placement and at least 44px targets. Preserve existing dialogs and independently interactive links/copilot controls. Avoid nested interactive card semantics.
- On phones, market drivers become a deliberate swipe strip with visible affordance and native focus/scroll behavior; primary outlook, priorities and agenda stay in normal vertical flow. No hidden capability or page-level horizontal overflow.
- Existing shared theme typography, ink, panel, line, spacing and radius tokens; approved fallbacks where the pending shared scale is absent. No independent font/palette root, colored container edge stripe or opaque runtime stylesheet.

## Art direction

DARK: calm command surface, neutral luminance depth, fine even borders, clear semantic ink. Remove ambient aurora/glass blur from this page composition; no decorative pulsing or replayed card entrance. Focus and actual live-state signals remain distinct.

LIGHT: cool canvas with opaque white panels, disciplined hairlines and restrained soft shadows. No dark glass formula or colored glow translated onto white. Verdict/status ink uses the existing accessible light theme rungs. Hierarchy, content, order and behavior stay identical across themes.

Motion: short existing-token state transitions only; native control feedback, no whole-card wandering. Reduced motion explicitly covers new surfaces and pseudo-elements. No scroll hijacking.

Chart line item: retain the existing server-rendered SVG path and exact live patch geometry contract; this is interaction/responsive improvement to the incumbent chart, not a replacement chart engine or new forecast. Other charts retain their established owners.

## Boundaries

Preserve DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION (no #ud-hero/global composite), DNR:HOLD-IGNITION-SURFACES, and the W1 hidden legacy #sx-risk-v2 ruling. No data scoring/ranking, access, auth, licensing or trade execution changes. Source release via the existing controller, never self-merge.

## Verification

Full Jinja render with representative rich data and honest degraded states; desktop1440, tablet, mobile390; dark/light × EN/ZH. Inspect actual captures. Check headings, card reachability, complete event labels, DOM/focus order, history keyboard/touch/live update behavior, reduced motion and overflow. Stock mode remains unchanged. Run affected existing render/history/risk/events tests and source/visual guards. Recapture the existing EW-P4 source-bound receipt where required; never change hashes without a real capture. Reuse canonical capture_page_evidence.py.

Direct implementation decision: LOWER_TOTAL_OVERHEAD. This work tightly couples page composition, existing live DOM contracts and visual iteration. Native children supplied bounded source/ownership/product reasoning only; no routine implementation labor was dispatched. One principal owns the source diff and validation.

## Current status

Implementation and focused self-check are complete for the main workspace. Thirty-one browser cases pass against populated and unavailable fixtures; 200 affected existing checks passed on the first run, and the two stale card-slicing assertions were repaired to use real element boundaries (five targeted checks then passed). Canonical CI ownership/closure checks passed. Commit-bound recapture is complete at fca9114d922d21a3b88e6406b02e2368da66db9c: 16 workspace states, 74 W9 states and 68 EW states; the final 31 browser cases and both source-binding guards pass. Source/visual guards pass. The next phase is ready PR, normal merge/render, then actual served-page acceptance. Production acceptance is not yet proven.

Known dependencies: the canonical shared navigation produces a large cold-load layout shift in both the acquired baseline and candidate; local diagnosis measured roughly 0.723 baseline and 0.702 candidate CLS. The existing held prehydration carrier #10261 owns that issue; this page does not create a second nav controller or claim Web Vitals readiness. The frozen rate-card semantic contradiction remains owned by #10493. These observations do not authorize bypassing either hold.
