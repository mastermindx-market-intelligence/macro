# Brain output build

The runtime uses prebuilt, closed financial components. Model calls contain the template name, symbol and bounded view options; source arrays travel only through the existing private chart/history transport. Local controls never call the model.

Run `npm ci --ignore-scripts --no-audit --no-fund` in this directory, then `npm run build`. Commit the paired generated assets and `build-manifest.json`. The build verifies every canonical Terminal input against `terminal-sources.json` and fails if the pure statement bundle retains network or cache code. KaTeX is lazy-loaded and emits native MathML with trusted commands disabled and bounded expansion.

The statement normalizer is immutable: `terminal-statements-38723cef-v1` and `mm_brain_finance_math_v1.js` must continue to describe the pinned source revision. Future semantic changes need a new allowlisted version/filename while retained historical snapshots keep their original version. Do not hand-edit the vendored source or port its calculations to Python.

The standalone Markdown companion is generated from the existing shared widget's DOM-only Markdown functions. The manifest binds that exact source segment, preventing the standalone page from maintaining a second formatter.

Before release run the existing Brain code/browser gate, including the financial source, asset, browser, standalone and shared-widget suites. Browser fixtures prove deterministic behavior; live model selection, entitlement, saved history and actual Macro/Terminal delivery require separate production evidence.
