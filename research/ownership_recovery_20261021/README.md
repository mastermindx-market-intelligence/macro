# Ownership and recovery research

Start with [REPORT.md](REPORT.md). This executed continuation separates selected businesses, recovery timing, reference-low survival, stop geometry and usable capital. It reconstructs the original defensive V11 study and follows the earlier sector-RSI finding without another indicator grid.

## What became clearer

- Core defensive joint signals retain 67/74 positive endpoint outcomes, but only 39/74 frozen lows survive 126 sessions.
- On matched support, core signals add 1.10 percentage points of mean return over ordinary dates; peers add 1.91 points. The core's higher absolute hit rate partly reflects its stronger ordinary-entry base rate.
- Core joint capital grows 6.94% annually with a 19.17% maximum drawdown despite 39.4% average exposure.
- Same-date sector baskets capture much of the recovery result; selected-minus-basket paired uncertainty spans zero.
- Stopouts of eventual winners usually occur with the earlier low touched or undercut on or before the stop date. An untouched-reference explanation accounts for only 4/23 core and 2/51 peer converted winners.
- The worst core drawdown carried older positions into a new shock; the sector drawdown concentrated many fresh rebound entries together. These imply different next research questions.

See the report for denominators, costs, open positions, comparison limits and the qualitative information-mechanism assessment. Historical positive returns are not a qualified future win probability.

## Contents

- [PROTOCOL.md](PROTOCOL.md): committed definitions before new outcomes; exposed-history status preserved.
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md): units, estimator meanings and maturity conventions.
- [VERIFICATION.md](VERIFICATION.md): independent review, 13 focused mechanical checks and review-driven repairs.
- [INFORMATION_AUDIT.md](INFORMATION_AUDIT.md): retained data clocks and issuer-guidance feature design.
- [HANDOFF.md](HANDOFF.md): recoverable research conclusions, unresolveds and next discriminator.
- `results/`: full derived ledgers, all declared policies/scenarios, uncertainty, reconstruction and correction receipts.
- `figures/`: reproducible SVG charts; `build_figures.py` also renders PNGs.

## Reproduction

Requirements: Python, numpy, pandas, pyarrow; curl_cffi only for explicitly requested missing public inputs. Matplotlib renders figures; reportlab, Pillow and system DejaVu fonts render the optional PDF. No production service or credentials are needed.

To reuse the registered retained inputs, supply the prior price manifest, original pre-outcome sector catalogue and V11 archive to `prepare_inputs.py`:

```bash
python prepare_inputs.py --base-data /path/to/prior/data --base-events /path/to/base_events.parquet --archive /path/to/Defensive_Nested_V11_Full_Reproduction_2026-10-12.zip --out ./data
python verify.py
python analyze.py
python supplement.py
python build_figures.py
python build_pdf.py
```

The optional `--acquire-missing-public` flag acquires absent public histories and receipts them. A new download is a new vintage and must not be described as byte-identical reproduction. `analyze.py` verifies the manifest's price and sector-catalogue hashes. Registered protocol, code and input hashes are in `results/registration.json`; the correction receipt preserves the initial run's identity and proves unchanged account outputs.

Raw public price bytes, private ordinary panels, local input paths and private earnings/transcript bodies are excluded from Git. The original archived source and result ledgers remain in the repository's `research/defensive_v11` archive. Figures and tables can be reproduced from the published derived results without acquiring prices. Research only: selected survivors, current-vintage prices, exposed history and dividend-return proxies are not point-in-time investment qualification.
