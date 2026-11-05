# B03 component evidence — independent approval pending

These are real browser captures of **synthetic fixtures**, not a live user journey.
The fixture uses the current dashboard's body/panel base CSS, shared theme.css,
the actual B03 template and client. The browser test sends requests through the
real API router and read model over the real producer's fixture output. Its
MDXAuth session and user entitlement are test doubles; no real credential is used.

For capture, the rendered component DOM is exported after successful source reads,
scripts are removed, and an explicit fixture notice is added. The canonical
scripts/capture_page_evidence.py loads those static fixture pages anonymously.
observations.html shows page one of 61 synthetic observations; search.html shows
an exact AMZN search over that full population, although AMZN is outside page one.
The counts verify 40 featured / 21 beyond-preview fixture names against the exact producer receipt. Search captures open the source-evidence disclosure, preserving the MACD counterevidence and missing correction-history/first-available limits. Exact local shared font assets accompany the capture fixture. No paid production data is contained in these files.

## Art direction and scope

Dark uses the dashboard's existing dark canvas and instrument panel, neutral
hairlines, restrained blue identity links and shared glass controls.
Light uses its existing white panel, cool canvas, dark ink and hairlines; the
shared button material and shadows follow the light theme. The component creates
no palette or runtime stylesheet. Mobile uses the existing stacked DecisionRow;
desktop keeps identity, trigger and episode relation on one row. English and
Chinese retain the same order, counts and actions. Eight rows are visible per page;
search runs on the full source before paging.

The complete mechanical matrix is desktop/tablet/mobile × EN/ZH × dark/light,
for both browse and exact search (24 captures). The browser suite additionally
exercises 401/403/503, clearing private rows on sign-out, retry and query behavior.
These captures cover only the new disclosure. Full dashboard integration,
independent visual judgment, authenticated deployed journeys and source-publication
freshness remain release gates. A passed evidence checker is not their acceptance.

## Reproduce and inspect

Run tests/test_prophet_observations_browser.py with Playwright Chromium. Its
desk fixture is the source of the exported DOM. Capture uses the repository's
capture_page_evidence.py with --routes /observations.html,/search.html,
--viewports desktop,tablet,mobile --locales en,zh --themes dark,light.
The manifest records its exact tool hash, observed state, screenshot hashes and
target directory. The original exported fixture DOM remains in the parent
evidence root under b03-visual-fixture-r3-20261011.

No B1/B3/B4 engines, episode history, entry decisions, rankings, Plans or scientific
promotion rules were changed by this component.
