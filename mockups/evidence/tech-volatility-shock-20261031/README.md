# Tech Volatility Shock - exact-source visual evidence (PR #10229)

**SYNTHETIC_LOCAL_NOT_PRODUCTION.** These are actual Chromium captures of a local
presentation fixture. All displayed prices and statistics are invented display
values; this bundle proves presentation, not mathematical correctness, real market
observations, deployment, or natural nightly/express behavior.

## Frozen source and capture identity

- Reviewed feature head: `8b389ffcbfc03d4b5a0dfb08773586bc38334b79`.
- Template: `templates/_tech_volatility_shock.html.j2`, Git blob
  `ada3a38b08aec39c33c538232b31714201e9789b`, SHA256
  `06bb7d53ade98140cf8f793557e263ed4196dedfefe35b24a4b187c7c9041f71`.
- Estate theme: Git blob `619436f58d37a222d1db7021ba9d52bb3a05a7fa`.
- Unmodified canonical capture tool: `scripts/capture_page_evidence.py`, Git blob
  `78ba651d2996a64231c738a133ed465d73dd8caf`, SHA256
  `9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`.
- Captured on ubuntu0 at 2026-11-02T23:26:38Z using Chromium 156.0.8078.4,
  Playwright 1.64.0. `manifest.json` preserves the actual tool/target/axis records.
- Fabric result `VOLSHOCK_VISUAL_REFRESH_8B389_20261102_01`, response SHA256
  `1ef766323380269b09ff561c85e9f942975d2c98990098d7c0f9240013d01c66`.

These files replace the pre-fix feda59ce screenshots, which still showed removed
colored left borders and must not be cited as the current template's evidence.
The template, calculator, rendering hooks and tests are unchanged by this refresh.

## Captured coverage and limitations

Exactly 8 rest cells plus 8 genuine `summary_focus` cells: desktop 1440x900 and
mobile 390x844, EN/ZH, dark/light. All 16 PNG bytes match their manifest SHA256;
force-state cells record the browser-applied focus. No failed asset responses,
console errors or horizontal overflow were reported by the final capture.

The fixture uses the exact partial and theme, a minimal regime-radar/next-section
scaffold and an explicit synthetic-data banner. The fixture layer forces details
open to show the complete cards; the production template remains collapsed by
default. Estate theme.js was not included, so the capture tool used its documented
HTML-attribute theme/locale fallback. This is component-level evidence, NOT the
complete deployed page or user preference/theme-toggle path.

Separate actual browser assertions checked FOUR representative corners (desktop
EN-dark and ZH-light; mobile ZH-dark and EN-light), not all eight combinations:
neutral symmetric 1px card/relative borders, no inset/pseudo-element colored rail,
mount after regime-radar, collapsed default, Tab focus with visible outline, and
Enter/Space expand/collapse. Assertions and reproducible fixture source remain in
the original bounded bundle below; no unperformed assertions are inferred.

The first, superseded fixture capture had six missing-font/style 404s. Those exact
head assets were supplied before this final capture. Old failed captures are not
included here. Authenticated/loading/empty/stale/error states not captured are
explicit gaps in the manifest. The synthetic values are never live data proof.

## Reproduction and retained original

The canonical invocation is:

```bash
python3 scripts/capture_page_evidence.py \
  --site-dir /path/to/isolated-source-bound-fixture --routes /macro.html \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --max-pages 1 --delay-ms 0 --settle-ms 120 \
  --force-state 'summary_focus:focus(.tvs summary)' \
  --output-dir /path/to/evidence --manifest /path/to/evidence/manifest.json \
  --smells /path/to/evidence/smells.json
```

Original bundle on ubuntu0:
`/home/ubuntu0/lanes/returns/volshock-resume-10229-20261102/`.
Its `SHA256SUMS` digest is
`16a63b9730c09cb7c59d6c303c225d0c6423df9092ae3019f33c373f259987f2`.
Parent verified all 26 listed hashes and visually inspected desktop EN-dark and
mobile ZH-light. Verified M2 copy:
`/tmp/volshock-release-preflight.3bwVBv/visual-proof/`.

## Remaining acceptance

Protected release and actual raw Massive R2 -> qualified derived snapshot -> final
Macro HTML -> raw-less express preservation -> served EN/ZH desktop/mobile/theme
and keyboard behavior remain mandatory. No production acceptance is claimed.
The private derived JSON does not require an anonymous-access allowlist change.
