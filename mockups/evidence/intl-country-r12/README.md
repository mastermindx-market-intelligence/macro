# International R12 — canonical browser evidence

This captures the implemented International country cockpit through the repository's existing `scripts/capture_page_evidence.py` owner. The small runner at `research/paper_international_wave1_wave2/capture_country_cockpit.py` supplies fresh anonymous Chrome contexts and serves the already-rendered integration specimen plus local template assets at the isolated `http://intl.test/intl.html` route. It preserves the canonical state application, measurement, screenshot, hashing and manifest lifecycle.

## Observed result

All 24 states were captured: eight rest states for desktop (1440×900) and phone (390×844), English/Chinese and dark/light, plus hover and focus for the open country summary in each combination. The manifest records the actual applied locale, theme and interaction. Every PNG is present beside the manifest, with matching bytes, dimensions and SHA-256. `EVIDENCE.yml` binds the three material UI paths in the complete International change. The repository visual-evidence guard passes on the original-base-to-candidate template diff.

The separately recorded country browser acceptance covers 12 viewport/theme/locale states, including 320px, and ten country/navigation/degradation journeys. Its evidence remains under `research/paper_international_wave1_wave2/country_cockpit_preview/`.

## Meaning and limits

This is an isolated integration specimen, not a capture of the deployed service or a signed-in session. Official forecast and national-policy evidence is bound in the R12 research receipt; specimen market inputs are not live-market acquisition proof. Canonical census gaps for signed-in access and asynchronous loading/empty/stale/error states remain explicit in the manifest. Separate focused degradation tests must be assessed on their own recorded scope.

The capture observed two expected fixture failures: local `live_config.js` is not generated in the template-only specimen, and the external analytics script is deliberately aborted. No request was made to a signed-in endpoint. Neither failure is silently removed from the manifest. The static country analysis, country selection and native disclosure content are present without that generated deployment configuration.

The census reports zero document horizontal overflow, two H1 nodes and wider elements on mobile. Those raw measurements are preserved; the census alone does not determine whether the counted nodes are visible in the active view. This receipt demonstrates captured source behavior and integrity, not a blanket accessibility claim, formal product approval, production delivery, market freshness or an award-winning design verdict.

## Token migration check

The six page-local color blends were moved unchanged to canonical shared-theme variables. A real Chrome comparison against published commit `88b6f192c3e2a7a94f5cf7ff4d9d06bc225324a4` found identical computed color, background, border, outline, shadow and background-image values for all 3,168 International elements in both themes at rest, hover and focus (six checks). The raw before/after screenshot comparison is also retained; full PNGs are not asserted byte-identical because shared chrome varied between captures.

## Reproduction

Run the existing R12 preview builder first, then the following command with the installed Chrome and Python Playwright used by this specimen. The canonical tool module hash and actual request/state observations are in `manifest.json`; do not hand-edit screenshot cells to replace a new capture.

```sh
python research/paper_international_wave1_wave2/capture_country_cockpit.py \
  --base-url http://intl.test --routes /intl.html --max-pages 1 \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --output-dir mockups/evidence/intl-country-r12/screens \
  --manifest mockups/evidence/intl-country-r12/manifest.json \
  --smells mockups/evidence/intl-country-r12/smells.json \
  --settle-ms 1300 --delay-ms 0 --timeout-s 10 \
  --force-state 'country-hover:hover(.imc-country[open] > summary)' \
  --force-state 'country-focus:focus(.imc-country[open] > summary)'
```

The exact diff supplied to the local design/visual gates is preserved losslessly as `research/paper_international_wave1_wave2/country_cockpit_preview/ci_ui_delta.diff.gz`. Decompress it to reproduce those recorded commands. The compressed form avoids committing whitespace-bearing diff context as source lines.
