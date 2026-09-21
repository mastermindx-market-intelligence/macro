# Brain composer notice removal

The Chairman requested removal of the complete purple research message. The row,
copy, cost subline, styles, and obsolete DOM updates are deleted, without replacing
them. Fast/Pro and the existing explicit `/research` command remain available.

## Verification

- `node --check templates/mm_brain.js`: passed.
- `python3 -m pytest tests/test_mm_brain_asset.py -q --no-header`: 13 passed.
- `python3 scripts/check_template_site_sync.py`: 99 pairs checked, passed.
- Runtime style injection guard: passed; no allowance expansion.
- Agent OS validation: zero errors; unrelated existing warnings remain.
- `python3 mockups/evidence/brain-composer-notice-removal-20260921/verify_behavior.py`:
  all eight dark/light x EN/ZH x 1440/390 browser states passed. Checks cover real
  research/fast request construction, retained Pro preference, denied research for
  a non-Pro entitlement, zero missing-element exceptions, and zero notice-row gap.
- `manifest.json`: eight real Chromium screenshots emitted by the existing
  `scripts/capture_page_evidence.py` owner. No screenshot is a generated mockup.

DARK: existing dark composer and blue Pro selection, with the violet notice gone.
LIGHT: existing light composer and blue Pro selection, with no notice or empty row.
No new palette, component, message, or substitute disclaimer is introduced.

The fixture uses synthetic auth/quotas and intercepts requests locally. It proves
component behavior, not production authentication, paid inference, or deployment.
The host language event is mirrored so Chinese evidence actually contains Chinese.
The PR and subsequent live verification separately establish release status.

## Reproduce screenshots

Run the existing capture CLI with `--site-dir .`, route
`/mockups/evidence/brain-composer-notice-removal-20260921/fixture.html`,
`--viewports desktop,mobile --locales en,zh --themes dark,light`, and the output,
manifest, and smell paths in this directory.

## Do not redo

Do not restore the old F11 composer notice to satisfy superseded snapshot tests.
Backend research authority, billing, and answer-level policy were not changed.
See `DEC:BRAIN-COMPOSER-NO-RESEARCH-NOTICE`.
