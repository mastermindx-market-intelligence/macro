# Brain output build

The runtime uses prebuilt, closed financial components. Model calls contain the template name, symbol and bounded view options; source arrays travel only through the existing private chart/history transport. Local controls never call the model.

Run `npm ci --ignore-scripts --no-audit --no-fund` in this directory, then `npm run build`. Commit the paired generated assets and `build-manifest.json`. The build verifies every canonical Terminal input against `terminal-sources.json` and fails if the pure statement bundle retains network or cache code. KaTeX is lazy-loaded and emits native MathML with trusted commands disabled and bounded expansion.

The statement normalizer is immutable: `terminal-statements-38723cef-v1` and `mm_brain_finance_math_v1.js` must continue to describe the pinned source revision. Future semantic changes need a new allowlisted version/filename while retained historical snapshots keep their original version. Do not hand-edit the vendored source or port its calculations to Python.

The standalone Markdown companion is generated from the existing shared widget's DOM-only Markdown functions. The manifest binds that exact source segment, preventing the standalone page from maintaining a second formatter.

Before release run the existing Brain code/browser gate, including the financial source, asset, browser, standalone and shared-widget suites. Browser fixtures prove deterministic behavior; live model selection, entitlement, saved history and actual Macro/Terminal delivery require separate production evidence.

## Presentation contract and local controls

The existing Brain gateway is the sole tool-admission and source-entitlement owner. `render_financial_widget` accepts one of `price`, `financial_statement`, `company`, or `transcript`, a validated symbol (or completed same-turn source reference), and closed view options. Statement options select income/balance/cashflow, annual/interim, at most eight displayed periods, and a compatible metric. Price options select 1M/3M/6M/YTD/1Y/MAX. These descriptors never contain markup, arbitrary styles, executable code or data URLs.

The gateway sends a compact model receipt while the private chart/history channel retains a bounded immutable source snapshot. The browser applies the pinned statement normalizer to full retained history before choosing display periods. Local range, statement, period, metric, table/compact and CSV controls use that snapshot without another model call. Current transcript entitlement is checked on replay; withheld valid quote evidence returns only a static localized membership-required notice, without source facts or receipt data.

Legacy technical charts retain the existing chart transport and ChartBus boundary. Strict daily OHLC intake rejects missing/coerced fields and inconsistent bars, preserves unknown volume, sorts/deduplicates dates, and bounds the feed. Cached requests expire after 60 seconds and failed requests are evicted. Weekly/monthly candles aggregate measured daily bars, with missing aggregate volume retained as missing. Date ranges do not change on resize; dense histories use measured-close paths rather than fabricated candles. The displayed start/end and daily-derived basis are visible.

Math supports explicit `\\( … \\)`, `\\[ … \\]` and `$$ … $$` delimiters. Single-dollar currency and code remain literal. Rendering is display only, not a calculator. KaTeX's unused error-color default is adapted at build time to `currentColor`; strict errors still preserve readable formula text. This avoids a vendor palette while keeping the package version pinned and does not change the immutable Terminal math inputs.

## Visual evidence recipe

After building, run `MM_REQUIRE_BROWSER=1 python3 tools/brain-output/capture_evidence.py` with the same Python/Chromium runtime used by the Brain browser tests. It feeds actual widget and standalone fixtures into `scripts/capture_page_evidence.py`'s existing observer/manifest owner. It writes PNGs and the canonical evidence receipt under `mockups/evidence/brain-intelligent-output/`.

`statement-public-AAPL.json` is the fixed public financial snapshot used for statement layout review, as of 2026-10-21; its digest is retained in the wire and evidence target. Other price, company and transcript values are explicitly synthetic fixtures. Captures disclose this boundary and cannot substitute for live model, membership or deployment acceptance. The recipe records asset and recipe digests, actual applied theme/language, viewport dimensions, real hover/focus states, and browser errors. Timing remains unmeasured; bootstrap fixture traffic is not a performance benchmark.
