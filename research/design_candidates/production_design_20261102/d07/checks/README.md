# Reproduce the D07 source checks

These are offline design-research diagnostics. Node checks ran on 24.22.1. The additional producer suite uses Python 3.12.14 and pandas 2.2.3. The geometry check uses the Python standard library. Supply the exact pinned source inputs and installed runtime dependencies. The checks operate on controlled local fixtures.

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

## Additional producer and client diagnostics

Run `python probe-expectation-producer.py /path/to/build_expectation_surface.py` and `node probe-expectation-client.mjs /path/to/expectation_surface.html.j2`. Both verify their source blob before executing. The 9 producer cases exercise original source functions with controlled frames and a temporary publication target. The 4 client cases execute the original request/index functions with a minimal DOM and a presentation-callback recorder. The original `afterLoad` rendering path is source-inspected separately. [Exact dependencies, cases and interpretation](EXPECTATION_ADVISORY.md)

The results say `BASELINE_REPRODUCED`. Several assertions require the current undesirable result. A passing baseline probe therefore preserves evidence of an open product issue. Later implementation acceptance must run through the owning normal entry point and require the specified corrected outcome. [Producer results](expectation-producer-advisory.json) · [Client results](expectation-client-advisory.json)

## Earnings member lifecycle

From the D07 directory run `node checks/diagnostics/earnings-hydration/probe-hydration.cjs`. The included source copy is the exact public Macro loader blob `12216b31e5a747d959051ca2295bc690270335ac` at `fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9`. The script validates it before execution and checks controlled DOM/auth/HTTP seams. All six witnesses reproduce the current loader's behavior. [Probe](diagnostics/earnings-hydration/probe-hydration.cjs) · [Results](diagnostics/earnings-hydration/probe-results.txt)

## Joint candidate geometry

From the D07 directory run `python checks/verify-geometry.py`. The 42 assertions transcribe F01-F02-SHELL/1.0.0-candidate.2 at `245a7d2c` and F02's concurrence at `f7c25c4b`. They verify available-width arithmetic, dock thresholds, fractional widths, extra local chrome and basic control/table budgets. Actual rendered text, focus, contrast and responsive behavior require their own evidence. [Results](geometry-results.txt) · [Responsive requirements](../RESPONSIVE.md)

## Evidence categories

| Suite | Recorded result | What it establishes |
| --- | --- | --- |
| Native Analysis routes | 45 cases, 180 assertions and 4 blob checks passed | Pinned real parser/helper behavior in an offline module harness |
| Original estimate fixtures | Six checks, including one reproduced false-zero comparison | Exact source artifacts, distinct clocks and current prior-selector behavior |
| Added estimates | 9 producer + 4 client diagnostics reproduced | Controlled source behavior and typed repair requirements |
| Earnings hydration | Six witnesses reproduced | Current loader behavior under controlled auth, data and response timing |
| Joint geometry | 42 assertions passed | Candidate specification arithmetic |

The source and specification results remain distinct from served browser observations, final Paper visual review, RIG acceptance and production proof.
