# Homepage mobile reflow — evidence and limits

Scope: footer responsiveness and the Special Situations score/timing row. No changes to prices, entitlements, data values, animation logic, destination links or brand assets.

The original browser audit measured a 406px-wide document at a 320px viewport. The footer did not inherit the shared public chrome's two-column layout. The remaining narrow-screen defect was the intrinsic no-wrap width of the Special Situations meter: its gauge, score and timing badge could not all fit on one line.

Changes use the existing 900px and 680px responsive blocks. Footer destinations reflow into the same two-column grid used by shared public chrome. Score and timing can wrap; the timing label is never hidden. No global overflow suppression was introduced.

## Verification
- Regression tests were run before the fix: 4 failed, 1 passed, with missing reflow rules as the cause.
- Targeted regression/public chrome/navigation/pricing suite: 56 passed after the fix and sparse dependency materialization.
- Template/site synchronization: 98 pairs checked, no drift.
- Canonical capture: `scripts/capture_page_evidence.py --site-dir site --routes '/index.html?still' --viewports desktop,mobile --locales en,zh --themes dark,light --max-pages 1 --settle-ms 1200`.
- `manifest.json` is the existing `mastermind.p0_evidence.v2` schema. It records eight real captures with requested theme and locale applied. Both standard viewports report no document overflow.
- Supplemental local-file Chromium captures at 320/360/390/430/768/1440 pixels retained the requested full-page width. EN/ZH and both color preferences were also checked at 320/390/1440. These additional captures are diagnostics, not a second canonical manifest format.

## Art direction and inspection
The public landing intentionally retains its light acquisition header/canvas in both preference settings and its dark terminal/closing/footer bands. This patch changes geometry only. At narrow widths the two footer columns remain legible, every destination is preserved, and the situation score stays beside its gauge while the timing badge uses the next line when necessary. No color meaning or typography scale changed.

## Limitations
This is local built-site evidence, not production acceptance. The static server cannot serve `/api/billing/offers/founding_pro`, so the canonical capture truthfully records its 404; the fallback offer display must not be described as a live billing response. Authenticated, loading, stale, empty and error states remain explicit capture gaps.
The manifest's resolved Git SHA is the baseline at capture time, not a claim that an uncommitted patch was already deployed. This PR carries the exact source diff and paired asset stamp. Independent review, current-base CI, merge and a deployed mobile click-through are separate remaining gates.
