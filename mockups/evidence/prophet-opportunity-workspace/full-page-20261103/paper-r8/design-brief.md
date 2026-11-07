# Prophet R8 full-page design source — 3 November 2026

## Reviewed editable designs

The new R8 boards live in the existing PROPHET Paper file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, page `p-C-0`. Earlier boards remain intact.

| Variant | Paper board | Current disposition |
| --- | --- | --- |
| Desktop 1440, English, light | YW1-0 | Complete; native screenshot reviewed; clean JSX exported |
| Mobile 390, English, light | ZRL-0 | Complete; native screenshot and card crop reviewed; clean JSX exported |
| Mobile 390, Chinese, dark | 1092-0 | Complete; native screenshot and card crop reviewed; clean JSX exported |
| Desktop 1440, English, dark | ZE5-0 | Incomplete; held after an original palette operation returned no definitive effect receipt |

The desktop dark operation `prophet-r8-20261103-desktop-dark-colors-200` timed out. A same-carrier read showed the requested 81-node update had not appeared at that observation. That read does not establish that the original request cannot later apply. The board has not been replayed, overwritten, or accepted. Other boards were edited only outside the held subtree.

## Design decisions

A compact market brief leads to visible section navigation and the Today / Screener / Plans workspace. Four rich cards give price structure, entry conditions, comparison, provenance, and a clear next action. Regime, breadth, themes, sector timing, and research follow in a consistent hierarchy. The assistant belongs in the page header.

Entry, stale quote, unavailable quote, and maturity are distinct states. Quote time, signal time, and terms time remain separate; unavailable clocks say so. A stale quote does not automatically revoke an entry. The Turn Setups example explicitly distinguishes unavailable data from no qualifying stocks.

The existing Mastermind tokens and Inter typography are retained. Chinese mobile text uses PingFang SC, with red for gains and green for declines across charts and supporting data. The mobile status bar is from Paper's official mobile-status-bar guide.

All numbers, symbols, charts, entry conditions, and sector observations here are illustrative design fixtures. They are not a fresh market-data report. The illustration label is visible in the footer.

## Artifacts and reproducibility

The three JSX files are clean native Paper exports, not re-created HTML exports. The five `paper-*.jpg` images are unmodified native Paper screenshots. `native-screenshot-receipt.json` records board IDs, dimensions, byte sizes, and SHA-256 hashes.

The four HTML and JSON variants are the editable composition source and offline design preflight. The dark desktop HTML is a proposed finished composition; it does not prove that the held Paper board reached that state. Offline preflight metrics do not establish native product improvement.

From a repository checkout with the existing dependencies installed:

```bash
python3 tools/generate_paper_r8.py --output paper-r8
python3 tools/capture_paper_preflight.py --workspace /path/to/repo --source paper-r8 --output paper-r8/preflight-final
```

These commands are relative to this evidence directory. They create illustrative local artifacts and perform no Paper mutation. Use a new output directory for each capture. Production implementation must preserve the native Jinja/data/authentication paths and pass separate native-browser and release checks.
