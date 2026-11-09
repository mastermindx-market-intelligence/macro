# Shared Tools mobile category chooser

**Implemented source candidate; release held.** This follows the accepted [Paper mobile chooser and Build sheet](https://app.paper.design/file/01M6Y32A3E4XC51FQVJN98YRPH/p-2-0) using the existing All Tools owner. The source base is Macro **071ed19f5ce87927f078f94f3e126c24d8a0307e**; this isolated carrier is `design/paper-tools-mobile-chooser-20261109`.

## What changes for the reader

On screens at or below 600px, a single category button replaces the horizontal category rail. Opening it reveals the **same source-driven category buttons** in an inline vertical list. The existing dialog is the only mobile scrollport, so the list and destination rows share the available height. Desktop retains its existing category controls and body scroll.

The current category remains obvious: **Start here** means the existing contextual starting subset; a selected category uses its source label; a meaningful global query says **All categories**; the deliberate full-directory action says **All destinations**. These labels represent different existing result sets.

| Reader action | Result |
| --- | --- |
| Search from Research | Search all source categories, retaining Research underneath. |
| Clear the search | Return to Research and keep focus in search. |
| Choose a category while searching | Clear the query, show that category, collapse the chooser and focus its button. |
| Show available tools after no results | Use the existing full-directory reset and focus search. |
| All destinations from the mobile footer | Show the full directory, reset its scroll and focus the visible chooser button. |
| Escape while expanded | Close the chooser and restore its button; a fresh later Escape closes All Tools. |
| Hold Escape | Repeated events remain owned by that physical press and cannot consume both levels. |
| Change language | Preserve the open chooser, stable category identity and eligible focus; defer incomplete IME queries. |
| Change the responsive breakpoint | Normalize outgoing scroll, repair only focus in a newly hidden control, and retain other focused content with nearest visibility. |
| Close and reopen | Start collapsed and refresh through the original source snapshot owner. |

The explicit closing toggle repairs focus even when a pointer activation did not first focus it. The IME-origin Escape reservation survives composition-end/input/cancel order and repeats until keyup or the next distinct key. It does not suppress the IME's native cancellation. These event sequences are source-tested; actual OS IME remains a browser qualification requirement.

## Existing architecture and exact scope

All behavior remains inside the marked controller in `templates/nav_market.js`, copied identically to `site/nav_market.js`. The documentary `src/all-tools.js` remains exactly the production marker block. Only the existing All Tools CSS marker block changes in the paired navigation stylesheet; all surrounding JS/CSS bytes are unchanged.

Mount enhances the existing category region rather than requiring new generated host markup. It adds one category button and one media-query listener to the same mounted instance. One disclosure boolean and one short-lived Escape-press owner remain local to that controller. There is no second catalogue, router, native dialog, focus trap, saved preference, data request or retry owner.

The source anchor snapshot, group/search selection and per-opening withdrawal map remain authoritative. Every render and native activation boundary still qualifies the original href, target and enabled source node. Category or locale redraw cannot revive a withdrawn destination. Valid ordinary, modified, auxiliary and context-menu navigation remain native.

The mobile category button and choices use existing design tokens and a 44px minimum. Labels can wrap. The existing hidden rule removes collapsed choices from keyboard traversal. The small chevron turns over 120ms and stops transitioning under reduced motion; existing source blueprint illustrations remain untouched. Actual layout, target measurement and font proof are still owed.

Only Macro overview, Sector Central and Reports index remain admitted. Their generated HTML was processed with the existing `scripts.optimize_assets.make_optimizer` helper. Original assets first reproduced all three pages byte-for-byte. Candidate outputs then changed only the paired stylesheet/preload references from `edfd821b` to `f7206632`. No model/data builder ran, and no generated page was independently hand-edited.

## Executed qualification

The final source passes **138 Node checks** and **11 existing All Tools integration contracts**, with the latter extracting and executing the actual production controller. These are overlapping evidence layers, not 149 browser cases. The original 107 behavior checks passed before changes; the missing-chooser falsifier then failed on the exact original controller and passes in the final suite. Full-asset JavaScript syntax also passes.

The existing tests cover category/query/Clear, direct and native-cancel Escape paths, repeated keys, IME event ordering, locale redraw, breakpoint focus/scroll intent, footer recovery, one-instance mounting, current source inventory, withdrawal persistence and native destination boundaries. The recording DOM does not provide geometry, actual browser event synthesis, OS IME or assistive-technology evidence.

[VALIDATION.json](VALIDATION.json) binds the ten implementation/test/generated paths to their Git blobs and SHA-256 hashes. Supporting artifacts are [the final Node results](controller-tests.tap), [the pytest result](all-tools-pytest.txt), [the original-source falsifier](baseline-chooser-falsifier.tap), [the optimizer qualification](asset-reference-qualification.json) and [the source-scope check](scope-verification.json).

The first pytest collection lacked Jinja2 in the primary runtime. Reusing the already installed system Jinja package through the test process's PYTHONPATH resolved that dependency; the final exact suite passes. No package installation, browser substitution or approval change occurred.

## Concrete release blockers

**Keep this source candidate Draft and disarmed.** No Ready, auto-merge, merge or deployment is established by the passing source checks.

1. **Shared loader integration.** The existing payload-key test passes on the base and fails on this candidate: old expected digest `472f1b07`, new actual digest `1b594114`, unchanged key `20261101-expectation-surface-nav`. This means returning browsers can retain the old nav at its immutable URL. PR7601 and PR10261 already own overlapping outer navigation/loader changes. Their heads and effects were read and preserved. Reconcile through those incumbent owners, advance both loader hops and the existing digest, and emit served theme through `lib.site_assets.emit_theme_js()`; HTML CSS stamping cannot close this JavaScript chain. The [recorded gate result](loader-owner-qualification.json) executes the exact named function and dependency/constants from the unchanged test by AST, with the real nav/account inputs; it is not a full navigation-module test run.
2. **Required measured receipts.** The unchanged [P0B closure gate output](p0b-receipt-closure.txt) returns exit1 with four findings: both original receipts pin changed `site/nav_market.js` and `site/navigation-refresh.css`. [The existing hold](https://github.com/mastermindx-market-intelligence/macro/pull/7601#issuecomment-6689771047) explicitly preserves the denied pinned capture family. No capture, alternate browser/host/worker, digest-only receipt rewrite, gate weakening or CI replay was attempted. Closure needs an actually authorized measured route or a separately authorized canonical gate-owner change.

When those boundaries are legitimately resolved, integration must prove actual 320px EN/ZH enlarged-text reachability with one scrollport; desktop/mobile and dark/light behavior; native dialog/IME/keyboard focus; old generated hosts; source withdrawal; and returning-browser cache delivery. The earlier R41 horizontal rail addressed a real double-typography scroll trap, so its historical proof cannot be relabelled as proof of this replacement layout.

## Historical documentation corrected

PR7949 actually merged on **21 October 2026** at **ccc3242ef52966877e24b5290a5883628664e707**. The parent README now labels its R41/R23 records as historical, retains their findings and separates the current candidate from old installation and native-session status. This does not claim that the newer chooser is deployed.
