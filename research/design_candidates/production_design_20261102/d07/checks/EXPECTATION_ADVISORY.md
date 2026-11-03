# D07 Expectation Surface advisory diagnostics

This continuation reviews the Phase 2A source contract. It does not run a server, fetch private data, write a ledger or qualify a design. Python imports selected function definitions from the pinned publisher with its original source unchanged. Node runs the original client request/index functions in an isolated VM with controlled responses and a minimal DOM adapter. It substitutes an `afterLoad` recorder to observe callback delivery. The original `afterLoad` source assigns `cur.doc` and calls `updateCard`, `renderView` and `fillNumbers`. That rendering path was inspected in source, and browser verification remains pending. The tests assert the inspected baseline behavior. [Original rendering callback](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/expectation_surface.html.j2#L1908-L1928)

## Reproduction

Use Python 3 with pandas 2.2.3 and Node 24.22.1. Supply the exact source files below.

```sh
python probe-expectation-producer.py /path/to/build_expectation_surface.py
node probe-expectation-client.mjs /path/to/expectation_surface.html.j2
```

Both scripts verify the Git blob identity before executing. A changed source blob refuses the old baseline probe. A successful exit means **BASELINE_REPRODUCED**. Several assertions deliberately require the undesirable current result. A future implementation test must replace those baseline expectations with the required user outcome and run the actual owning entry point.

| Input | Immutable source | Required Git blob |
| --- | --- | --- |
| Producer | [build_expectation_surface.py](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_expectation_surface.py) | `1b39e3a519a548d2187130498dd05b58a256ccdd` |
| Client | [expectation_surface.html.j2](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/expectation_surface.html.j2) | `51d99c9ac76557e2dce356a53231416f5fe84a44` |

## Observed cases and interpretation

| Probe | Reproduced baseline | Required builder result |
| --- | --- | --- |
| Numeric observation with typed missingness | Average rejected by pair computation is still emitted in explorer with high/count | Reject or null ineligible values consistently, retaining reasons and eligible fields |
| Known currency mismatch, schema boundary | USD→EUR is paired as a numeric revision | Resolve compatible unit/currency/basis or show noncomparable |
| Partial attempt clocks | Newest observed session disappears without a reason | Per-session fallback or explicitly omitted session |
| Same-session changed payload | 10→11→12 makes two positive breadth changes while chart has one latest value | Source-owner revision selection and one admitted observation per comparison point |
| Same-session period change | New values can inherit the first payload's period end | Values, range and analyst count bind to the same selected source revision and fiscal end |
| Offset-qualified clocks | Raw string minimum is later than chronological minimum | Validate UTC-only inputs or normalize before ordering |
| Reversed changed-payload rows | One up/one down replaces two ups, latest value follows file order | Selection independent of physical row order |
| Analyst count census | One issuer with two horizon counts yields the median across two keys | Label metric/horizon denominator and mixed vintages |
| Render interruption | New summary/index, old HTML and retained old ticker file | Existing publisher promotes or serves a coherent generation, with typed mismatch on failure |
| A→B request race | B remains in query and URL while delayed A reaches the substituted `afterLoad` callback after B | Verify request identity and discard older completions |
| Wrong payload identity/flags | A 200 payload for another ticker with a true reserved flag reaches the substituted `afterLoad` callback | Validate object and explicit false authority flags |
| Failed search-index fetch | Error is cached as an empty list and suppresses subsequent reads | Separate failed from empty state and expose retry |
| Existing route behavior | `?t=<symbol>#es-explorer`, selective replaceState, 12-character UI limit | Preserve meaningful query keys, define restoration and reconcile with 15-character producer |

The raw source contract deliberately permits distinct payload hashes within a session and carries observation IDs/correction links. The changed-payload cases therefore represent a supported source pattern. The invalid numeric-plus-missingness and mixed-offset rows are defensive synthetic inputs. The known-currency mismatch is a schema-boundary fixture. Current SRC-A1 emits null `unit`, `currency` and `basis`. No live frequency is claimed. The render test injects a deterministic exception at the render dependency boundary after the function has written JSON into a temporary directory, then inspects those exact files and removes that temporary directory. It requires no Jinja installation. [Raw owner and schema](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/research/alpha_intelligence/expectation_market_dynamics/DATA_CLOCK_RIGHTS_MATRIX.md) · [Collector behavior](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/collectors/equity_revisions.py)

Results record **9 producer probes and 4 client probes**. Original six AAPL/clock diagnostics remain unchanged. [Producer output](expectation-producer-advisory.json) · [Client output](expectation-client-advisory.json)
