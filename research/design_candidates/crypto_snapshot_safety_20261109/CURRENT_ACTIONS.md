# Current actions and unobstructed mutation feedback

## User outcome

Current-case Historical review and Save/Remove have 12px separation, readable wrapping and 48px targets. Inspect demand sits on its own row, 12px below, with a target of at least 44px. Save uses the existing primary treatment; Remove remains neutral. Native disabled Save is visually distinct and has no enabled hover treatment. Review and inspection keep their independent availability.

The existing confirmation/status node now follows the drawer content in normal flow, so it cannot cover these controls. Its existing text, polite status semantics and five-second timer remain. Hiding a nonempty message retains its occupied box, preventing timeout-induced scroll clamping.

Failures receive an additional visibility rule: an unreadable or unconfirmed action has no changed button to signal its outcome. If the initiating action still owns focus and the URL/language/history context, scroll only the existing drawer just far enough to expose the full message below the sticky header. Do not rebuild the body, move focus, retry storage or change the route. When the message already fits, do not scroll.

This intentionally refines the failure-visibility promise of [the preceding reading phase](CURRENT_SAVE_READING.md). Confirmed and idempotent outcomes still retain the reading position; a failure can make the minimum scroll needed to reveal its actionable explanation. It does not silently substitute a reset reader.

## Why this is needed

The native parent captures showed Review and Save/Remove touching edge to edge, despite the 12px gap in Paper G5. The fixed toast covered Inspect demand and could also obscure Save/Remove. Disabled expired Save looked much like an enabled neutral button.

A normal-flow message alone would remove the obstruction but could hide a failure below the fold. A changed button gives sighted users an immediate success cue; unchanged controls give no equivalent failure cue. This phase therefore verifies the failure message and the original focused action together in the visible drawer.

The parent baseline has **21 failures / 54 passes** across 75 affected cases. The source is rooted at `f2cb62ef2e19abbef7ebe218030c110276953912` / assets `a8bf00034c30`. The final runtime receipt and candidate identity are recorded below after verification.

## Existing owners and implementation

| Concern | Continue here | Decision |
|---|---|---|
| Current actions | `scenario()` and `.cri-drawer-actions` | Reuse the wrapping group; 12px gap; Review then Save/Remove or storage Retry |
| Storage unavailable | Existing ready/unavailable collection result | Existing warning appears before the action group; Review and Inspect remain usable |
| Primary action | Existing `.cri-btn-primary` | Save only; Remove stays neutral |
| Disabled state | Native `disabled` and current-action CSS | Existing panel2/muted/line tokens; distinct cursor; no hover brightness/background change |
| Demand evidence | Existing `open("evidence:liquidity_flows")` and semantic focus key | Separate action row; no destination or evidence change |
| Status | Existing `#cri-toast` sibling after `#cri-dialog-body` | One DOM node, one `role=status`, one polite live region, existing timer |
| Feedback visibility | Existing failure `report()` inside `save()` | Exact action ownership first; move only the existing drawer if the message falls outside its visible reading area |
| Confirmation and reading | Existing `save()`, capture/projection/persistence helpers | No storage mutation or confirmed-reading policy replacement |

There is no new status node, queue, timer, scroll container, state registry, router or model owner. The HTML template is unchanged.

### Action layout

The primary row inherits the shared wrapping behavior, then applies current-case 12px spacing and 48px targets. Controls retain their semantic focus and snapshot-intent markers. The current-action minimum-height rule follows the shared recovery rule so the CSS cascade does not reduce Review to 44px.

The second action row reuses the same group with a 12px top gap. The 244px Paper specimen widths are not forced onto phones. English and Chinese labels wrap through the group according to available space; keyboard order remains Review → enabled Save/Remove/Retry → Inspect. Disabled Save is skipped naturally.

### One stable feedback node

The status already lives after the body inside the existing native dialog. Its fixed-position rules are replaced by normal-flow spacing aligned to the drawer's 26px desktop / 20px narrow inset. It retains readable wrapping and existing surface, border, type and radius tokens.

When the timer sets `hidden`, a nonempty status retains its box with `visibility:hidden`. It is not visibly rendered, while the space remains. An initially empty hidden status still takes no layout space. This is a guarantee about **timeout-induced** layout stability, not an assertion that differently sized later messages have identical geometry.

Markup semantics remain unchanged; this native browser proof is not a new screen-reader announcement certification. The implementation adds no height animation or nested scrolling behavior.

### Failure is visible and focus stays owned

At action start, capture the history-state signature alongside the existing length, URL/language/control witnesses. The additional signature guards failure-visibility scrolling. Truthful confirmed status still appears when another control gained focus; the existing reading capture separately yields an obsolete rebuild.

For a failed action:

1. If the original action no longer owns the context, yield presentation.
2. Show the existing status message.
3. Reveal it only when the original action still owns focus and the same context.
4. Measure the visible dialog area below the sticky header. If the message ends below the viewport, move the existing scroll position by that excess; if it starts above the reading area, move by that deficit.
5. Return. There is no later focus, render, route or storage effect.

The original control and case DOM remain connected. A programmatic activation with unrelated focus does not pull the reader to a message. Storage read/serialization/write/readback failures remain distinct and keep the existing no-replay semantics. Frozen saved-item Remove failure uses the same visibility rule; successful frozen Remove retains its existing list destination.

## Verification contract

New cases verify:

- Action separation, minimum target sizes, wrapping, no horizontal overflow and keyboard order at EN/320, ZH/320, EN/390, ZH/390 and EN/1440.
- Expired Save's visual distinction, unchanged disabled hover and native inertness, while Review and Inspect stay usable.
- Confirmed Save, Remove, expired Remove, unreadable storage and unconfirmed writes in both mobile locales: the same single status node, no control overlap, correct storage count and reader/focus behavior.
- Both timeout cases: hidden feedback retains its box, scroll and action rectangles remain exact, and focus stays on Inspect.
- Four already-fitting failure cases: no unnecessary scroll.
- Frozen Remove failure: the same body/control/focus/storage and a fully visible message.

The preceding failure-reading test is deliberately updated for the new visible-feedback requirement. It still requires exact body HTML, the original connected focused control, open conditions and unchanged storage outcome. It permits only the required scroll and checks both action and message in view. Its previous form is retained in the reversible transformation manifest.

The other affected tests retain confirmed/idempotent reading, history/locale/focus ownership, saved navigation and cross-tab displayed intent. Do not combine overlapping phase counts into another full-suite claim.

## Proof and conservation

### Final affected run

**75 passed** in one final native run on assets `62cf3bb534f8`: 61.75s pytest time / 62.121s subprocess time / 62.38s wrapper time. Chrome `157.0.8103.39` recorded **75 contexts / 81 pages**, zero page errors, zero external requests and zero WebSockets. Six new functions contribute 25 cases; the other 50 are affected regressions. This is not a whole application-suite run.

All 75 case IDs are shared by the baseline, initial candidate and final candidate. Their assertions are not all identical: two existing functions have explicit, reversible changes described below. The baseline recorded 21 failures / 54 passes. The initial candidate recorded 72 passes / three failures. Two failures exposed an overly broad history-signature guard that suppressed truthful confirmed feedback after newer focus; the final implementation applies that guard only to failure-reveal scrolling. The third exposed a test that compared the outgoing locale's scroll position with the new locale's post-feedback scroll range. The corrected assertion records the actual nested action's starting position after locale layout has already clamped it.

The failed-mutation test was deliberately refined to require visible failure feedback while retaining the exact body, control, focus, disclosure and storage result. It allows only the necessary reveal scroll. It is not represented as an unchanged historical assertion.

A separate launcher typo exited 127 before the candidate wrapper ran. The retained error receipt records PID 61321 and the incorrect executable path. Its known no-run outcome was reconciled before dispatching the corrected path. The subsequent initial candidate and final run are separate recorded executions; no ambiguous mutation was replayed.

### Visual proof

All **25 final PNGs** are retained. The **13 new-scope captures** were visually inspected: five action layouts (EN/320, EN/390, EN/1440, ZH/320, ZH/390), two disabled states, and six Save/expired Remove/unconfirmed outcome views across the mobile locales. The remaining 12 captures are retained navigation, reading and intent regressions, not claimed as a new visual review. The new views show separate actions, the existing primary Save treatment, distinct disabled Save and in-flow feedback without covering controls. Complete focus-ring clearance at the viewport edge is a separate follow-up, not part of this phase's rectangle-visibility claim.

### Recorded execution

| Stage | PID | Recorded outcome |
|---|---:|---|
| Parent snapshot | 23285 | 21 exact inputs; no runtime changes |
| Parent baseline | 46508 | 21 failed / 54 passed; 47.92s pytest / 48.311s subprocess / 48.41s wrapper |
| Launcher error | 61321 | Exit 127 before wrapper execution; 0.05s wrapper |
| Initial candidate | 62604 | 72 passed / three failed; 58.78s pytest / 59.135s subprocess / 59.39s wrapper |
| Final verified candidate | 76049 | 75 passed; 61.75s pytest / 62.121s subprocess / 62.38s wrapper |
| Publication metadata | 82775 | 28 native evidence/script files, 25 captures; exit 0 / 0.11s wrapper |


[Exact native receipt](current-action-layout/PUBLICATION_RECEIPT.json) and [capture references](current-action-layout/CAPTURE_REFERENCES.json) record input identities, individual cases, runtime observations and image hashes.

The source changes the current action grouping, existing failure presentation and their CSS. Seven recorded source/generated/test paths change; fourteen recorded inputs remain exact. The two HTML pages change only their two asset references. Template/served CSS and JS match; source JSON, projection, HTML template, builder, server tests and shared assets remain unchanged.

All seven source transformations reverse exactly. Reversing the two existing test-function changes and removing the appended tests recovers the complete parent module and the baseline test hash.

## Editable reference and limits

Paper G5 already gives the action pair a 12px gap and separates demand inspection. Preserve that specimen layout. QI and Build 3IP should explain the implemented action/status policy and distinguish confirmed reading continuity from the minimum visibility scroll for failure. Do not place builder mechanics or additional explanatory footnotes into the product action area.

Native fixture proof does not establish current-market freshness, personal saved activity, hosted/independent acceptance, public-route replacement or release. Existing H5/model, alert, paired-receipt, qualified-result and admission/release boundaries remain. The storage sequence is still not atomic cross-tab compare-and-swap.
