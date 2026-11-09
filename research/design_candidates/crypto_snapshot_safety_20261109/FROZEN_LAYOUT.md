# Frozen saved-case hierarchy and evidence integrity

## Delivered behavior

The saved case now presents its complete original condition before either disclosure. The primary path is immediately available: Historical review. The saved review shows its case identity, original cutoff and absence of a qualified comparison; methodology stays available through a native disclosure.

This is the third implementation phase on dependent Draft PR #10901, following navigation commit `95ac76db194b8952aef0e63c4bcb30a220da78e0`. Asset version: `e38da6bba4dd`. It implements the accepted Paper hierarchy while retaining the existing drawer, history, focus and storage owners.

Paper file `01M6Y3F0NXNDPAKJMJGCAD759Z`, page `p-4-0` contains the accepted states 09–16 and two new concrete edge states:
- **17 / `3LJ-0`**: usable original case, present but unreadable evidence digest.
- **18 / `3MC-0`**: usable original case, original progress unavailable.

The new states clone the existing 7-day legacy and 30-day case frames, retain all mapped identities/parents/styles and alter only four text nodes. The source frames remain byte-identical in their JSX. They are historical/synthetic examples, not personal saved records or current-market claims.

## Reading order and field placement

| Visible surface | Original source / behavior |
|---|---|
| Header | Named parent, Saved snapshot eyebrow, original case title, Close |
| Identity | Saved asset, saved horizon, explicitly labeled original cutoff |
| Status | Retained original progress, or explicit missing progress; today's expiry remains separate |
| Original condition | Complete saved condition, unchanged and visible |
| Original case details | Original sequence, invalidation, counterpoint, next check recorded then, expiry, prior-close window/range and research qualification |
| Original evidence | Count of displayable captured readings; expanded original values, quality and explicitly labeled snapshot dates |
| Historical review | 48px primary action using the existing exact-revision route |
| Remove from this device | Separate 44px action using the existing explicit Remove intent |

No full technical revision ID is added to product copy. The revision remains the exact route/storage identity and is documented in the build evidence.

`savedScenario` is a rendering helper within the existing drawer owner. The current-scenario branch retains its original Next check, sequence, invalidation, Conditions and evidence, save/remove and demand-evidence composition. Optional parent arguments on the existing `button` and `definition` helpers place content in local groups without introducing another component state owner.

Saved presentation classes are cleared on every drawer render. The saved identity helper marks the scoped header. Shared styles, page template and data remain unchanged.

## Temporal integrity

The old `status(s)` combined original progress with expiry evaluated against today's date. It is therefore unsuitable as an undifferentiated “At cutoff” value.

The renderer now separates these concepts:

| Retained state | Product treatment |
|---|---|
| Not expired, nonempty localized progress string retained | At cutoff · original progress / 快照时 · 原始进展 |
| Not expired, localized progress missing or malformed | Original progress unavailable / 原始进展暂无 |
| Expired today | Existing Expired · historical context only warning |
| Expired, details expanded | Progress at cutoff shows the retained original string, or Not preserved |

The frozen renderer does not infer missing progress from current scenarios, original levels or a generic conditional fallback. It does not translate an absent saved locale by silently borrowing the other locale. The current-scenario status behavior remains unchanged.

Prior-close details require the original available flag, `prior_daily_closes` basis, positive integer count, valid ordered dates and an end before the saved cutoff. A range is shown only for finite positive low and a finite high at least as large. Missing windows remain unavailable. The 30-day fixture preserves 60 prior daily closes, 18 August–16 October, $64,681–$86,595. This is research context, not an official model invalidation.

## Optional evidence is a projection, not a mutation

A saved case can remain usable when optional `issue_evidence` is absent or damaged. The renderer must not erase the record, borrow current evidence, invent source clocks or convert malformed objects to apparent readings.

| Optional digest input | Result |
|---|---|
| No `issue_evidence` property | Existing supported legacy absence explanation; original case remains usable |
| Present digest with non-array/wholly unusable families | Incomplete/unreadable explanation; do not claim it was never preserved |
| Mixed displayable and unusable entries | Displayable saved readings remain; expanded note identifies unreadable entries |
| Object-valued/empty localized text | Not stringified into product copy |
| Impossible/malformed snapshot date | Explicit date unavailable |
| Unknown quality | Explicit quality unavailable |

A counted family requires a nonempty localized label or retained ID and a nonempty localized state string. Displayed snapshot dates pass the existing calendar-day validator. The complete stored collection stays byte-for-byte unchanged throughout this projection.

Quality labels are localized: Snapshot only, Stale at capture, Observed at capture, Incomplete at capture, or Quality unavailable. These describe the captured quality flag. Dates are explicitly **snapshot dates**; the optional digest does not preserve independent observation dates, so the UI does not invent them.

## Review and recovery

Saved review uses the original asset rather than a hardcoded BTC label. Its visible result is “No qualified comparison yet” and a short statement that no performance result is available for this saved case.

“What would qualify a comparison” is a native disclosure retaining all four existing requirements: point-in-time history, independent episodes, counterexamples and forecast evaluation. No result, sample count, calibration or forecast authority is fabricated.

The new `review-requirements` and `remove` semantic keys join the existing reading-state owner. Disclosure, locale and focus restoration require no separate store. A language change retains focus on Remove. Parent return, native history, same-URL entries, original horizons and outer Close behavior remain covered by the full browser run.

Unavailable-version and unreadable-collection recovery actions use local flex groups with an 8px gap, a 48px primary target and a secondary target of at least 44px. Their existing routes/retry semantics remain intact.

## Layout and accessibility

The frozen header adds a modest saved-snapshot eyebrow and the existing 28px title token. The body uses the existing theme, font and spacing system. Native disclosure markers and keyboard semantics remain; focus-visible outlines are explicit.

Normal saved cases have two disclosures and a clear primary action. Legacy absence and unusable digests use a readable explanation in place of an empty evidence disclosure. No nested scroll owner, height animation, attention pulse or new feedback region is added. Existing reduced-motion rules remain in force.

Actual checks confirm the primary action fits the closed case at the tested 320, 390 and 1440 widths; all header/actions/disclosure targets meet their minimum sizes; no viewport/drawer horizontal overflow occurs. The 320/390 saved-review locale cases check focused-summary bounds against the sticky header. Native return captures show the Historical review action visible after restoring long evidence reading state.

## Verification

- Exact navigation-parent baseline, PID 45282: **19 failed / 2 passed / 61 deselected**, 39.56s pytest / 40.291s subprocess, 21 contexts/pages. The two retained-current-scenario cases pass; the new hierarchy, explicit expiry/progress, review, recovery and Remove-focus cases expose expected parent differences. These are shared defects/design requirements, not 19 independent bugs.
- Candidate PID 61590: **86 browser cases passed**, 80.36s pytest / 80.858s subprocess, **87 fresh contexts / 93 pages**, Chrome 157.0.8103.39; zero page errors, outside-origin requests or WebSockets.
- This includes all prior 61 browser cases and 25 additions. Four optional-digest cases were added after the baseline, before the candidate run. The existing saved-case assertion now checks the actual complete original condition, original date/horizon and the new evidence label instead of the removed repeated footer.
- Two current-scenario projections—320px EN and 1440px ZH—retain **exact DOM and element geometry** against the parent.
- Additional bounded light-theme capture run, PID 82354: **2 passed**, 6.25s pytest / 6.930s subprocess, two fresh contexts/pages. It only supplies 390px EN and 320px ZH visual captures; the verified runtime and primary test harness remain unchanged.
- **Twelve final native dialog captures inspected**: five closed saved cases across dark/light and languages, two expanded evidence views, compact Chinese review, legacy absence, two recovery states and long-reading native parent return.
- All 39 Python contract cases retain their previous passing evidence; the builder/data/projection inputs are unchanged and were not rerun unnecessarily.

Twenty-two JS transformations plus one CSS transformation invert to the exact parent. Template and served assets match. The two saved pages change only their asset-version references from `7d9cb01e7600` to `e38da6bba4dd`; fourteen other inputs are unchanged. Node syntax passes.

## Boundaries and continuation

This is a locally verified dependent Draft. H5/model authority, alert integration, hosted/independent visual acceptance, public-route cutover and release/admission remain held. No production replacement or model/data refresh occurred.

Retain the navigation phase's settled-scroll qualification and the storage phase's non-atomic Web Storage boundary. Native dialog crops do not establish full-viewport toast placement.

Next safe work is to compare the accepted relative-comparison design against the existing source's window, cohort and evidence-basis behavior and repair any concrete gaps within those existing owners. This does not authorize new model promotion or release.
