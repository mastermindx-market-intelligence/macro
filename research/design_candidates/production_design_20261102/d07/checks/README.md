# Reproduce the D07 source checks

These are offline design-research diagnostics. Run from this directory with Node 24.22.1. No package installation, privileged session, or live data credential is needed.

## Analysis route matrix

Use a checkout of mastermind-terminal at `3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9`. Invoke `node verify-routes.mjs /path/to/mastermind-terminal`. The harness verifies four actual source blob identities recorded in [sources.json](sources.json), imports the real TypeScript modules and resolves their existing aliases. It applies [45 cases](matrix.json) to the server parser, the URLSearchParams adapter and the ambient panel mapper. This exercises duplicate-key behavior without running a Next server or reading any account data. A successful run produces [this output](route-results.txt).

## Estimate observations and the explorer readout

Provide the two frozen summary files, the AAPL ticker document at the later revision, and the later revision's actual Jinja template:

```sh
node verify-expectations.mjs /path/to/older/summary.json /path/to/later/summary.json /path/to/later/AAPL.json /path/to/later/expectation_surface.html.j2
```

| Input | Immutable file | Git blob |
| --- | --- | --- |
| Earlier summary | [site/expectation_surface/summary.json](https://github.com/mastermindx-market-intelligence/macro/blob/143bdfe08ac2444fde9fcb2263aa0c1d3d03dcc0/site/expectation_surface/summary.json) | d8a377c2ac42a8c56e42798146db6ed5be31d24a |
| Later summary | [site/expectation_surface/summary.json](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/expectation_surface/summary.json) | ddf20f7a1023cded3930715425713969ea324c1d |
| AAPL series | [site/expectation_surface/tickers/AAPL.json](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/expectation_surface/tickers/AAPL.json) | 15d5e943cb490176db663e59ad4dcf63acca9980 |
| Explorer | [templates/expectation_surface.html.j2](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/expectation_surface.html.j2#L1687-L1720) | 51d99c9ac76557e2dce356a53231416f5fe84a44 |

Five checks establish source invariants. The sixth reproduces the current discrepancy by running the pinned explorer's prior-average selector and readout arithmetic. A null fiscal end is paired with a dated period and gives a numeric zero where the required UI should withhold comparison. Reproducing the defect is the expected result for this baseline. This check establishes the calculation from source, without asserting the same input was selected in a served browser. [Observed output](expectation-results.txt)
