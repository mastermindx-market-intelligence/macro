# Brain composer notice removal

The Chairman requested removal of the complete purple research message. The row,
copy, cost subline, styles, and obsolete DOM updates are deleted, without replacing
them. Fast/Pro and the existing explicit `/research` command remain available.

## Verification

- `node --check templates/mm_brain.js`: passed.
- `python3 -m pytest tests/test_mm_brain_asset.py -q --no-header`: 13 passed.
- `python3 scripts/check_template_site_sync.py`: 99 pairs checked with the full
  `lib.site_assets` bake available. The derived `site/theme.js` Brain content stamp
  is updated in the same PR; unversioned bytes alone are not the release proof.
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

The Brain content hash changed from `cc2fa93e` to `2a93db87`. The existing bake
owner derives the new stamp; only that literal changes in the minified theme asset.
Live acceptance must confirm the real page loader and its immutable-version URL,
including the normal generated-page re-stamp after merge.

## Expanded checks and inherited gap

The dedicated asset suite now covers `test_mm_brain_asset.py`, `test_site_assets.py`,
and `test_template_site_sync_tokens.py`: **29 passed**. Full bake parity passes.

The wider `test_chat_launcher_stub.py` adds 15 passes and one existing failure:
`test_no_dynamic_child_asset_is_document_relative` flags `stock.html#` in the
unchanged theme source. Its two complete inputs are identical at this candidate
and origin/main 57ccf27b67a861459330647e034a308ef9148360:

- templates/theme.js blob fb1bb2faf09cfb171f7adf5a33a0a74849658f8b
- tests/test_chat_launcher_stub.py blob e82a3c993f19506a256128e051990b2bece3c04b

No guard was weakened and that unrelated source/test was not edited.

A real, unmocked production browser baseline on `/macro.html` returned HTTP 200,
mounted the widget, and found one notice row. Its actual loader request was
`/mm_brain.js?v=cc2fa93e`, serving SHA-256
`cc2fa93e3c24e393f4f4d96cb6ca7c757b8ce8a20377e471694592ac45d3aac7`.
This is explicitly pre-release evidence: the fix was not live at that check.
