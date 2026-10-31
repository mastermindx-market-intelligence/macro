# Tech Volatility Shock — bounded visual evidence (PR #10229)

This is **real Chromium screenshot evidence of a synthetic, local presentation fixture**, not proof that the public Macro Dashboard is deployed or its raw vendor price data is fresh.

- Original source surface: `templates/_tech_volatility_shock.html.j2` at candidate `feda59ce1fda2d474685f75d8606fe6dacac2269`. The subsequent source-only calendar-integrity repair does not modify this template.
- Capture tool: unmodified canonical `scripts/capture_page_evidence.py` at Git blob `78ba651d2996a64231c738a133ed465d73dd8caf`, run on authorized M2 Chromium/Playwright. The authoritative manifest is `manifest.json` (schema `mastermind.p0_evidence.v2`); source file and capture tool digests are retained there.
- Fixture: local `/macro.html` assembled from the source partial, the existing Macro `templates/theme.css` tokens, a minimal `#regime-radar` + next-section wrapper, and **synthetic** SPY/QQQ numbers. The fixture explicitly forces the otherwise-collapsed `<details>` **open** to show the full cards; this is a *presentation-only display fixture*, not an assertion that production defaults to expanded or these are observed market prices.
- Exactly 8 rest screenshots: desktop 1440×900 and mobile 390×844 × EN/ZH × dark/light. Additional 8 captures set `summary_focus:focus(.tvs summary)` using actual browser focus and record `applied_force_state=summary_focus`, so the existing `:focus-visible` styling receives interaction evidence for both themes.
- Result: **16/16 actual browser captures**, each with a real PNG, file SHA256, dimensions, applied theme/locale, and tool identity. Console, overflow, asset failure, and lab timing observations remain available in `smells.json` and the manifest; neither file is production telemetry.
- Production follow-up remains mandatory after protected merge: raw Massive R2 bars → qualified source-bound market snapshot → final `site/macro.html` including late fresh-board rewrite → express re-render retention → authenticated browser date, accessibility, locale, and mobile checks. Passing this visual receipt or feature CI alone never closes those obligations.

## Reproduction

With a source-bound fixture HTML in a local directory, run the **existing** capture tool:

```bash
python3 scripts/capture_page_evidence.py \
  --site-dir /path/to/isolated-fixture \
  --routes /macro.html \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --max-pages 1 --delay-ms 0 --settle-ms 120 \
  --force-state 'summary_focus:focus(.tvs summary)' \
  --output-dir /path/to/evidence \
  --manifest /path/to/evidence/manifest.json \
  --smells /path/to/evidence/smells.json
```

No screenshots were copied from the reference image; all PNGs were captured by Chromium after the site fixture was rendered.
