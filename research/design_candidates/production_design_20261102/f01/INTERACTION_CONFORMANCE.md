# F01 — executable interaction conformance

**Revision: F01-CONFORMANCE/1.0.0-candidate.3, 2026-11-04 UTC.** This makes the existing F01 candidate.4 requirements testable and records narrowly proposed directory improvements. It does not change the concurred joint geometry, route admission, company-search grammar, Brain lifecycle or domain ownership. Existing candidate.4 source approval and F02 concurrence remain bound to their exact inputs; this later revision carries its own source/self-QA evidence and does not inherit historical approval. All programme acceptance cases remain NOT_RUN unless their complete stated scope is actually qualified.

## 1. Exact sources and the implementation boundary

The original incumbent inspection used [Terminal master2ded360](https://github.com/mastermindx-market-intelligence/mastermind-terminal/tree/2ded360882b9c721e690907ff363b553781fb920/terminal) for the incumbent source, including [ShellDirectory](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/chrome/shared-shell/ShellDirectory.tsx), [sharedShellCopy](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/sharedShellCopy.ts), [SharedShellRuntime](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/chrome/shared-shell/SharedShellRuntime.tsx), and [scoped CSS](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/chrome/shared-shell/shared-shell.css). That inspection observed PR1244 at6fb8fd9 changing title mapping and query/category event resets. Its current consumed head is `624dbc0ac22ecdaa6d1bd580d5221da939c5e5a9`; preserve those independent changes during integration. PR1188 owns deferred mounting and search intent. The managed F01 implementation operation is `f01-directory-hardening-20261104-c4`; its actual acquisition receipt is in the [hardening evidence](evidence/hardening_20261104/).

The first implementation slice uses the existing categories **All, Workspaces, Markets, Research, Learn, Tools, About** and their existing classification. F03 subsequently concurred with the four-ID Options & futures grouping at `e1ac30e1405d5fed4fa1a79d623a066505d47c52`; the later bounded implementation and proof are recorded in §8. The complete 290-record presentation proposal remains unadopted. No new route, title taxonomy, active-symbol owner, API, telemetry stream or persistence key is introduced by this slice.

### Evidence classes

An observed source branch is not a served build. A browser fixture is not production data. A unit result does not establish native dialog behavior, screen-reader announcements or real IME behavior. Capture exact source, test command, fixture basis, browser/version, viewport, locale/theme, action, observed result and limitation. Report suite counts separately from the86 full qualification specifications.

## 2. Directory state and truthful counts

The existing mounted component owns raw query, selected category and rendered limit. Initial values remain empty query, All and48. The query is displayed exactly as typed; the incumbent NFKC/lowercase/trim/token logic is only its matching representation. A locale switch changes supported labels, not the query or chosen category. Closing a mounted directory retains query/category; new mounting follows the existing initial state. No cross-account or reload persistence is promised.

Distinguish three quantities for a single current input state:

| Quantity | Meaning | Required use |
| --- | --- | --- |
| Query-wide matches | Exact distinct destinations returned by the existing matcher with category=All | Scope of “Show all N matches”; includes other categories but no inferred URLs |
| Category matches | Destinations returned by that same incumbent matcher with the selected category | The visible result count; it is not a claim that other categories have no matches |
| Rendered matches | The prefix currently rendered under the batch limit | Show-more progress; never use this number as the total matching universe |

Retain the existing matcher and ordering, including bilingual names, existing aliases, exact href identity, finite `legacyPaths` fallback and category restrictions. Calculate both query-wide and category results through that same logic. Do **not** refactor to “classify once, filter after deduplication” without proving equivalence: the incumbent category-specific fallback can classify a path differently from a directory record with a public-nav/footer group. Preserve this behavior in the first slice; a category-taxonomy correction belongs to its own owner-reviewed change.

Distinct `/options`, `/options.html`, `/options_screener.html` and `/options/futures` survive. Same display titles never collapse distinct hrefs. Exact repeated hrefs do not inflate counts or duplicate a link. The290 proposal records are the historical design baseline, not a hard-coded live count; the later catalogue may legitimately contain more admitted records. The observed options12/facet4 values are evidence examples, never literals used to determine results.

### Transition requirements

| Action | State change | What stays and where focus goes |
| --- | --- | --- |
| Type/edit query | Query changes; limit becomes48 in the same input transition | Category remains; focus stays in search; no one-frame old-limit flash |
| Select category | Category changes; limit becomes48 | Query remains; selected category control retains focus |
| Show all N matches | Category becomes All; limit becomes48 | Query remains byte-for-byte. Move focus to the still-present All category control when the activated recovery button disappears; do not leave focus on BODY |
| Clear query | Query becomes empty; limit becomes48 | Category remains; search input receives/retains focus. It is not a reset-everything action |
| Show more | Increase limit by48, capped by the available rendered prefix | Keep query/category/order. If the button disappears at the final batch, focus the first newly revealed result; otherwise retain the button. No jump back to result1 |
| Dismiss and reopen while mounted | Close/open presentation only | Retain query/category and current rendered limit unless the actual owner remounts; reopen focuses the search input |
| Change locale/theme | Existing presentation owner updates labels/theme | Retain query/category/limit, results identity, scroll and valid focused control; no search rerun that changes ranking by language alone |
| Primary unmodified destination activation | Use the existing Link/router path and close directory for that navigation intent | Do not restore focus to the old opener. The destination owner handles loading/error and focus when ready; closing does not claim navigation completed |
| Modified click or middle-click | Preserve native new-tab/window semantics | Keep the current tab's directory and context. Do not mark its route committed or erase selection merely because an anchor click fired |
| Search companies | Transfer through the existing `onSearchCompanies`/AppShell owner | One modal; suppress directory return-focus. No second delayed callback, new event bus or company-search transport |

The retained48-step batch behavior means a rendered result is never silently replaced by a different result after Show more. A state change resets the batch deliberately, and a close alone does not. If lazy mounting has not resolved, show the loading/recovery owned by that existing path; zero matches must not appear before the catalogue exists.

### Empty and recovery states

| Condition | Message and action intent |
| --- | --- |
| Category matches>0, query-wide matches greater | Name the category-scoped count; offer Show all N matches. The action clears category only |
| Category matches=0, query-wide matches>0 | “No matches in this category” with the selected category still visible; offer Show all N matches. Do not say the page or company does not exist |
| Query-wide matches=0 and query nonempty | Existing no-pages guidance plus a clear-query action and the separate company-search path. Clearing preserves category |
| Empty query with a non-All category | Count the incumbent directory subset; use “destinations” rather than implying a query ran across every legacy path |
| More matches than rendered | Expose rendered/total progress beside Show more; the total is never48 merely because48 rows are displayed |

Use short EN/ZH copy through `sharedShellCopy` and the existing locale context. Counts require singular/plural correctness in English and complete sentences in Chinese. Status must be a concise polite, atomic live region associated with the input/result area; do not put the entire changing grid in an aria-live region. Announce scope/count once per committed input update without moving focus or reading every destination. The selected filter already exposes aria-pressed, so no repeated full category list is needed in the status.

## 3. Focus and input ownership

Candidate.4's conditional focus rule needs an observable predicate, not a call to `focus()` in every cleanup. Capture the actual opener before opening. At retirement, determine whether focus still belongs to this dialog **before** closing/removing it. A connected, visible, enabled target outside inert/hidden content is a valid return target. Connection alone is insufficient. Native dialog restoration is part of the browser behavior to verify, not evidence that a React effect already satisfies the rule.

For a user dismissal whose focus is still owned by the directory, return to its valid original opener. BODY and HTML are not meaningful return targets, including when the global shortcut opens from page background. Revalidate the saved control at dismissal; if focusing it is a no-op because it lost focusability, continue to a visible All tools/navigation opener and then the current page's existing visible heading/content fallback. Only named content fallbacks may acquire a programmatic tab stop. Preserve legitimate `tabindex=-1` invokers and preserve page scroll with `preventScroll` where supported. Do not manufacture an invisible sentinel, add a tab stop to BODY or an obsolete control, or focus a hidden desktop control on phone.

When category-only recovery moves focus to All, reveal that control inside the category strip as well as focusing it. Keep the current query and ordered eligible results. Scroll only the owned strip; do not scroll the document or primary task merely to expose the focus target. Test full button containment inside the strip, including the visible outline, rather than relying on DOM focus or `toBeVisible()` alone.

For a route activation or company-search transfer, let the destination/next-modal owner receive focus. For an intentional later focus movement outside the retiring surface, do not move it back. An old cleanup or scheduled callback must not affect a reopened directory, a newer route or another modal. Keep any cancellation/generation guard inside this mounted component or its existing parent owner; no new global layer store is justified.

Backdrop dismissal is an intentional pointer gesture: one primary pointer with the primary button must press and release outside the rendered dialog bounds, followed by its matching completed click. A drag from task to backdrop or backdrop to task, inside padding/border/edge activation, cancellation, interrupted capture, another pointer, secondary button or click without a completed pointer gesture keeps the directory open. Preserve a completed release through normal implicit touch-capture loss; discard incomplete capture and consume the gesture once. Reset it on close/reopen and cleanup. This local intent record does not gate Close or the established keyboard/native-cancel path, add a timer/global listener/storage owner, or change query/category/order/return ownership.

Input guards must respect defaultPrevented, repeat, modifier intent, editable/contenteditable targets and IME ownership wherever the relevant existing listener is changed. During composition, Escape belongs to text composition; it must not dismiss the directory or act as a chart/Brain shortcut. A child menu receives first refusal of Escape; only an unhandled Escape closes the directory. Do not let a capture-phase outer handler preempt a child merely because it ran first. A synthetic event test is useful but cannot qualify real operating-system Chinese IME behavior by itself.

The directory's capture phase may observe the native Escape and snapshot its composition/repetition protection, but must not dismiss or prevent the IME's keydown default. The bubble and native-cancel paths must use that same decision, including when composition ends between them. The [HTML close-request algorithm](https://html.spec.whatwg.org/multipage/interaction.html#close-requests) dispatches Escape keydown before processing close watchers; a prevented keydown has no corresponding native close request. A deliberately injected cancel after child prevention is therefore defensive synthetic coverage, not a claim about a native browser sequence.

Keep the association component-local and single-use: consume it on native cancel, clear on key release/cleanup, and expire it with a zero-delay task when neither arrives. An expiry must never close a surface, reopen it or clear a newer event's record. Native cancel exposes no originating keyboard identity. Until expiry, an unrelated non-keyboard cancel can conservatively consume an unconsumed protection once; timer task ordering is not a universal causal discriminator. Preserve this limit in review and qualify actual browser/operating-system IME behavior separately. Do not infer an IME pass from a synthetic `isComposing` flag.

Retain the native dialog's focus trap and one body-scroll lock. Record and restore the exact previous inline overflow value; repeated setup/cleanup and close/unmount must not leave a lock behind or unlock another active owner. Do not implement an alternative global scroll-lock service for this change. A dialog-to-search transfer must be exercised through actual AppShell, not inferred from independently passing dialog tests.

## 4. Responsive and accessible composition

Use the existing F02 roles and source-scoped CSS. Keep the neutral surface, clear title, stable input, named category controls, distinguishable destinations and quiet count/recovery area. The recovery action belongs next to the scope it changes. It must not push Close or company search off the usable viewport. At320px, wrap copy and use a single result column. Do not truncate the canonical identity needed to distinguish destinations.

The changed important buttons must provide the44px house target; result rows retain their existing greater-than48px target. Input/Close/status remain reachable with a reduced visual viewport and internal result scrolling. Test long Chinese copy, text enlargement, 400% reflow where practical, reduced motion and visible keyboard outlines. No authored maximum-scale or user-scalable=no change is silently folded into this slice; the observed application-wide magnification defect remains with its owning viewport declaration and separate conformance gate.

Viewport matrix:1440×900,820×1180,390×844;320px stress; live resize1440→320→1440 with directory open; short viewport/virtual-keyboard simulation. Use both EN/ZH and dark/light. Report representative state coverage, not a claim that a few screenshots cover all Cartesian combinations. Repeated layout effects must not reset query/category, steal focus or change the user's explicit compact-navigation preference.

## 5. Exact return and evidence identity remain domain contracts

The observed Company→Terminal→named-return journey preserved URL but lost the prior Financials period window, inner scroll and focus. Keep separate assertions for destination, entity/listing, local view, selected period/row, scroll and focus. Do not call the whole return journey passed because pathname/query match. A correction belongs to the existing Company/Terminal/history owners; F01 introduces no general return-state database.

On re-entry or evidence reopen, validate the existing source identity against the current owner revision. Preserve an exact period/field/statement identity only if still available and unambiguous; otherwise expose a named unavailable/changed context with the current view usable. Never reinterpret a missing FY2024 field as the same array index in FY2025. A prepared Brain attachment must be revalidated after source/context change, while an already-dispatched request keeps its original source identity. These requirements restate candidate.4 and CF04/N10/H01–H06, not a new source or save lifecycle.

### Unresolved dock-to-modal focus edge

The current shared contracts require modal inertness, no obscured focus and preservation of intentional outside focus. A passive resize from a dock to a modal can make these requirements conflict when the user has deliberately moved into the primary page. This is now an explicit **F01/F02 owner decision**, not an implicit implementation choice: either defer/suspend the evidence presentation until explicit reopen, preserving its identity, or qualify a focus-transfer rule with the affected owner. Do not auto-open a blocking modal over a later primary-task focus and call that “preserved.” The first directory slice does not implement this inspector transition. A chosen change to the joint transition rule requires the specified new candidate version and affected-consumer review.

[F01-RESIZE-FOCUS/0.1](RESIZE_FOCUS_DECISION_PROPOSAL.md) received F02's scoped proposal concurrence at013fdd72. [Joint candidate.5](JOINT_SHELL_SYSTEM_CONTRACT_CANDIDATE5.md) now specifies the transition, ownership snapshot order, adaptation versus dismissal, visible-focus/scroll precedence and exact remaining domain/host questions. Candidate.4 remains operative. Unknown-focus/other-modal arbitration and actual persistent recovery bindings remain unqualified; holding implementation is not permission to retain an invalid-width dock indefinitely.

## 6. Test facets mapped to the existing case ledger

These are discriminating subcases, not a replacement registry and not an increase to the86 programme cases. Each records baseline, changed outcome and exact evidence scope.

| Existing case | New concrete falsifier / required evidence |
| --- | --- |
| N03 | Same-labelled distinct hrefs; full-width and Chinese query; each incumbent category; legacy fallback that differs from a directory group. Compare ordered hrefs before/after; one changed category result without owner approval fails |
| N04 | Query with12 all-category matches and a narrower category; category=0/all>0; all=0;49/96/97+ matches. Recovery changes only category; clear-query changes only query; correct rendered/total counts; no lost focus when recovery/Show more disappears |
| N04/P02 | Close/reopen and locale/theme change after Show more. Query/category/limit/order remain; no rerender reset. Count announcements are scoped and grid is not an aria-live subtree |
| N05/N07 | Composition Escape, native isComposing/229 with composition ref false, composition ending before cancellation, repeat, and child prevention. Guard keyboard and native cancel consistently; consume protection once; expire it if no release/cancel arrives. Ordinary unhandled Escape closes once. Actual IME remains a distinct browser/manual qualification |
| N06/N07 | Shortcut from BODY; old invoker loses focusability; legitimate tabindex=-1 invoker; close after opener becomes hidden at320; removed/disabled opener; deliberate later focus; rapid close/reopen; directory→company search→cancel. No BODY/root tab stop or manufactured obsolete invoker; exactly one visible focus owner, no late reopening, valid fallback, original overflow restored |
| N06/N07 | Real input→backdrop and backdrop→input drags; cancelled/interrupted/mixed/secondary gestures; inside-edge activation; deliberate mouse/touch backdrop release; close once, retain query/category/URL, restore valid visible opener and reopen with context. Native capture ordering needs actual browser proof. |
| N04/N07/G08 | Category strip scrolled to About at320/390; All starts clipped; activate Show all. All becomes fully contained and focused, query/results preserved, document/primary scroll unchanged. Retain actual before/after geometry and inspect focus outline |
| N03/N06 | Ctrl/Meta-click and middle-click result, then ordinary activation; retain native new-tab semantics and current directory for modified activation; ordinary path invokes the existing navigation owner |
| N08/G07/G08 |1440/820/390/320, short height, EN/ZH dark/light, keyboard, resize and zoom. No document-wide overflow or unreachable changed control; query/selection persist;44px important targets |
| H01/H02/CF04 | URL result, selected period/identity, scroll and focus recorded independently; stale/missing source does not restore by array position or claim full context success |
| N10/N11/G07 | Record the unresolved passive dock→modal/outside-focus edge explicitly. A directory unit suite cannot close it or prove served Brain callbacks |

## 7. Release and review truth

Publish the source/spec delta and exact code/test evidence on the existing F01 carriers. Request affected-owner and independent qualification only against concrete immutable inputs. Record any PR1244/#1188 integration conflict and preserve their existing route/loading work. No merge, Ready, un-draft, enqueue, held-PR relabel or deployment follows automatically from tests. Paper, component tests, rendered fixture proof, served beta proof and acceptance are separate results.

## 8. Published four-ID facet qualification

The continued F01 implementation is [Terminal `b14436dd7b9c1296d17455c89f63960c774ab9be`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/commit/b14436dd7b9c1296d17455c89f63960c774ab9be) on Draft #1276, parent `1364256763ba505399399afe7a6b54021f141953`. The managed operation is `f01-directory-focus-correction-20261104-c4`; [exact evidence](https://github.com/mastermindx-market-intelligence/mastermind-terminal/tree/b14436dd7b9c1296d17455c89f63960c774ab9be/terminal/docs/pr-crops/f01-directory-options-facet-20261104) binds final sources, commands, raw reports and rendered screenshots. This is separate from the original §1 inspection and first-slice operation.

| Existing facet | Executed falsifier and result |
| --- | --- |
| N03 | Collect the incumbent ordered All corpus, then filter only terminal:options_futures, terminal:options, macro:options and macro:options_screener. Source entries are not mutated; a missing reviewed ID is not reconstructed from its fallback path. All seven original category fallback paths remain. |
| N04 | Added matching lessons change total counts without joining the facet; tools remain in All. Query/category reset preserves exact query and order. Component 100-result and real browser 104-result cases return from zero facet matches to the first 48-result batch after earlier expansion. |
| N04/N07 | Actual desktop keyboard Enter and tablet/mobile touch invoke Show all; touch pointer receipts, visible focused All, retained query/order and 44px control height are asserted. |
| N03/N04/P02 | Actual theme/language controls preserve the selected facet and English query across reopen. The incumbent Chinese query 期权 matches 2 source destinations; the facet filters that same result set without alias expansion. |
| N08/G07/G08 | Actual 1440/820/390 renders plus 320×420 light/ZH stress. The final phone list is one column; results scroll reaches the fourth destination while search, close/recovery and footer remain reachable. Actual screenshots were inspected. |

Before implementation, the five new component cases failed while the prior 24 passed. Final component/neighbor suites: **92 passed**. Full Chromium run: **34 passed / 2 intentional new-tab skips / 0 failed / 0 flaky**. After the phone-only visual refinement, **12 affected cases passed** on final source. Scoped lint and TypeScript pass. Adjacent #1244 single-file composition preserves its title mapping; this is not whole-PR integration. All **86 complete programme specifications remain NOT_RUN**.

The catalog is a synchronous bundled projection, unchanged at SHA-256 `2bfc0bf51e405abdd61032470d0b04cf1e1114370bd1c1f9b8e9e137d807f8cc`. This change creates no loading/error/stale-generation service. Existing source/access ownership, unknown tier, public-shell/premium-payload boundaries and production identity remain separately qualified. The local browser uses the incumbent development identity seam and controlled AAPL manifest; the known development chunk 404/ERR_ABORTED is recorded, with no new uncaught page exception. Candidate.5 inspector/IME/race conditions remain proposed and unexecuted, distinct from this directory evidence.

## Current deliberate-dismissal refinement — 2026-11-04 UTC

Terminal [e3bb0e683236d9882eedc09719de201a26dd9498](https://github.com/mastermindx-market-intelligence/mastermind-terminal/commit/e3bb0e683236d9882eedc09719de201a26dd9498) extends the earlier facet proof with the local pointer-intent correction. [Exact evidence](https://github.com/mastermindx-market-intelligence/mastermind-terminal/tree/e3bb0e683236d9882eedc09719de201a26dd9498/terminal/docs/pr-crops/f01-directory-gesture-20261104): three baseline real-browser failures; 95 final component/neighbor passes; full corrected browser matrix 37 passes / two existing intentional skips; three final affected passes after capture-loss handling; lint/type pass. The final captures bind the same source hashes. This is a refinement of existing N06/N07, with N04 retention checks; it adds no eighty-seventh programme obligation and does not qualify any complete programme case. The earlier section's b14436d/92-test results remain historical facet evidence. Candidate.4 and candidate.5 statuses are unchanged.
