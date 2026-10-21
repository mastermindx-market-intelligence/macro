# Monthly addition timing after a recovery signal

Controlled continuation of [Macro PR #9989](https://github.com/mastermindx-market-intelligence/macro/pull/9989).

The frozen protocol compares immediate, signal-triggered (month-end deadline), and blind month-end purchases with identical monthly contributions. SPY is primary. The ordinary 11 sector ETFs and two previously selected defensive baskets are declared secondary comparisons on the same signal calendar.

## Result

With 82 identical $1,000 monthly contributions, SPY terminal wealth was $146,743 for immediate purchases, $144,902 for signal waiting, and $145,271 for fixed month-end purchases. Signal waiting also trailed immediate purchases in all three secondary baskets. A favorable signal-funded subset did not pay for the waiting cost of deadline-funded months. See [REPORT.md](REPORT.md) for exact definitions, uncertainty, risk interpretation and limitations.

The separate [12-release guidance pilot](GUIDANCE_PILOT.md) preserves unresolved remaining-period operating revisions instead of forcing annual headlines into directional business labels. [Independent source review](guidance_review.md) checks four pivotal packets. [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) and [NEXT_HYPOTHESIS.md](NEXT_HYPOTHESIS.md) turn the findings into a research record and an explicitly untested funding-time watch hypothesis.

## Reproduce

Read [PROTOCOL.md](PROTOCOL.md), [config.json](config.json), [REGISTRATION.json](REGISTRATION.json), [AUDIT.md](AUDIT.md), and [DATA_DICTIONARY.md](DATA_DICTIONARY.md) first. This is exploratory research on already exposed history. No production feature or trading policy is changed.

The source signal roster and sanitized price provenance are in `inputs/`. Raw price parquets are retained privately in their original workspace and are not included here. Obtain the exact 31 archived ticker parquet files matching the published hashes; a new vendor download is a separately identified reconstruction, not byte-identical replication.

From this directory, with the verified archived prices named TICKER.parquet in a supplied directory:

```bash
python3 analyze.py --prices-dir /path/to/verified/prices
python3 verify.py --prices-dir /path/to/verified/prices
python3 build_figures.py
python3 build_pdf.py
```

`analyze.py` requires numpy, pandas, scipy and parquet support. Figure generation uses matplotlib; PDF generation uses reportlab and Pillow, with DejaVu fonts at the path stated in the script. The executed environment and source hashes are recorded in `results/`.

On the retained source host only, `prepare_inputs.py --prior-root /path/to/ownership_recovery_20261021` revalidates the accepted original manifest and creates ignored symlinks in `private/prices`. It does not download substitutes or publish raw inputs. The initial protocol was pushed at `b8036161bb84c2cab452d4d797081f7026f6b87d` before the new calculation.

All-scenario daily paths are retained in `results/daily_paths.csv.gz`. The portable review package includes all monthly ledgers and primary SPY figure paths; that larger daily file is available in this repository. The PDF contains the main assessment, research design and untested next-hypothesis contract.
