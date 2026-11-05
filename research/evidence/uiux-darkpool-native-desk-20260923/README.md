# Dark Pool — native browse controls and readable stock identity

MISSION_COMPLETE: false. CAPABILITY_STATE: BUILT_NOT_PROVEN. Current Chairman scope is the grouped Web Chat Macro frontend programme, VPS-only normal publication. No ChatGPT Work, worker, second source repository, runtime writer, new queue or publisher. Direct bounded completion is LOWER_TOTAL_OVERHEAD. Current compatible Skillpack is Mastermind@4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2 /1.0.1/bootstrap1.

## Source and continuity
Continue the already-started independent slice recorded at Macro#7781 issuecomment-5793072526. Original source base4815acf7fcd7ed5ad7bf7a5aacac00aff8c0bdac; current material-source comparison atfc6db6c1f9a76cadc180c44e386ae928c1a9ccbc found all owned source and dependency blobs unchanged. Planned sole source branch claude/uiux-darkpool-native-desk-20260923 was verified absent; no earlier publication or effect uncertainty exists. The fixture is immutable-source validation material, not a Git workspace or source owner. Current repository permission and post-checkpoint collision checks found no competing writer; wider PR file lists were expanded, not treated as empty.

## User journey and capability
Open Browse all stocks, select a quick filter, sort the same data, read its values without losing the ticker, switch language without resetting the view, and export the current selection. Empty results clearly explain how to recover.

Four non-native23.25px preset spans become native40px buttons with pressed state. Thirteen click-only sortable headings become native buttons, with one active aria-sort column and retained focus; optional definition tips stay outside the buttons and do not sort the table. Four filter fields have visible programmatic bilingual labels. Clear returns focus to Search; selecting or clearing a preset does not steal its focus. Native select labels and accessible names follow the shared language event without replacing controls. Current counts are announced; a genuinely empty snapshot is distinct from filters matching nothing.

The disclosure heading is shortened and structured rather than fragmenting into narrow text columns. Status text wraps at320px instead of being silently clipped. Screenshot review found that horizontal scrolling hid the stock identity; the ticker column is now sticky with an opaque existing panel surface, a hairline separator and the existing row-hover material. Header and row identities remain visible and hit-testable at both scroll limits. No new scrolling/focus script or duplicate wrapper is added.

## Preserved boundaries
The complete372-row embedded JSON is byte-identical to current source (SHA25649bbe0538d3fd31af08a641ca21062a62c26da951a65ce31c861da668ba97c2d). Sorting comparators, filter predicates/thresholds, exports, default sort and every producer/model/access rule are unchanged. Existing null-last behavior is preserved. No new network requests, authentication changes, paid payloads or shared CSS/JS edits. This is not a claim that FINRA short-volume data reveals individual investors or buying intent.

## Art direction
DARK preserves the existing quiet instrument shelf and measured selected/focus treatment. LIGHT preserves the white research panel, neutral form fields and hairline separators. Ticker identity uses each theme's actual opaque panel surface, not a hardcoded white or dark overlay. Chinese and English share the controls and data; labels alone switch. Controls remain usable at desktop1440, tablet820, mobile390 and narrow320. Wide-table horizontal scrolling stays native while the ticker remains legible.

## Verification
84 tests pass across the existing test_darkpool_desk and test_darkpool_signals suites, including14 added UI cases (13 recovered cases and the sticky-ticker regression). No new test suite or workflow. The paired original source failed all13 recovered interaction/layout discriminators; original capture/test failures caused by missing fixture dependencies were resolved by loading the actual dependencies, not by weakening tests.

16 native browser cases pass across four screen widths, both languages and themes. They test real Tab/Enter/Space and touch, all four original preset predicates,13 desktop sort columns (responsive columns on mobile), direction and null placement, unchanged372-row identity, label/state preservation after native Settings language switch, actual CSV downloads with original column values/order, empty-result recovery and focus. Ticker position and real hit-testing pass at both horizontal scroll limits. Actual focus outlines are solid2px; all tested controls are at least40px. No uncaught JS exception or page overflow. Local wh_banner.json and rr_banner.json404s are recorded fixture limitations, not production failure claims.

36 canonical rest/focus/hover captures cover desktop/tablet/mobile in both languages/themes; these govern outer disclosure presentation. All16 expanded-desk native screenshots and results supplement those outer-state captures. All image digests are checked. Design and visual-evidence guards run on the actual diff without allowances. Candidate page SHA256c054311fb192ccc777e1a4393f57a3fc97c4d9fce0526de0890a27ab8e7dfcb3; stylesheet170de2e0 is fingerprinted and exact-template parity is tested. No font file is committed.

Rerun:
```
python3 -m pytest tests/test_darkpool_desk.py tests/test_darkpool_signals.py -q
python3 research/evidence/uiux-darkpool-native-desk-20260923/verify_desk.py --site-dir site --output-dir /tmp/darkpool-native-proof
```
Public acceptance uses the same verifier with --base-url https://www.mastermind-x.com and no response interception. Local evidence is not public/authenticated production proof.

## Next action and stops
Publish the exact bounded source on its sole branch, consume concluded native repository CI/fences and current-base review, then normal VPS static publication and public verification. Do not retry the failed runtime updater or use Vercel. Transmission#7781 is separately with the existing merge owner; ETF/Crypto/Stage exact refusal families remain held. Prior Reports/AltData/Basket and accepted UI batches remain DO_NOT_REDO. No worker or autonomous Web wake is claimed. Intended continuation is the same Web Chat programme.
