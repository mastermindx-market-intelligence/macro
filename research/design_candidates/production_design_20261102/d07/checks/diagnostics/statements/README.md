# D07 statement-helper source diagnostic

This bounded diagnostic supports the existing D07 Phase 2A semantic content study. It directly imports the pinned, unmodified TypeScript helpers through Node 24's native type stripping. It uses no installed packages. The only import adaptation resolves the two exact extensionless local runtime imports. All fixture values are synthetic.

The recorded run is `BASELINE_REPRODUCED` with **22 cases, 69 helper assertions and 12 source-integrity checks across four files**. Twenty-one cases reproduce ordinary helper behavior. ST22 deliberately reproduces an undesirable legacy result. The run contains **zero UI assertions**.

## Reproduce

From this directory, run with Node 24.22.1 or another qualified Node 24 runtime that supports native TypeScript stripping and `registerHooks()`.

```sh
node probe-statements.mjs > results.json
```

The bundled `sources/` tree is the default input. To use an existing checkout at the same immutable pin, pass its root.

```sh
node probe-statements.mjs /path/to/pinned/mastermind-terminal > results.json
```

The harness validates each file's Git blob, SHA-256 and byte length before executing any tested source. A changed source refuses this baseline. The recorded artifact is deterministic. No network, database, browser, app installation or production write is required.

A zero exit means the baseline expectations were reproduced. It includes the undesirable ST22 result. A later implementation acceptance test must assert the corrected source-owner outcome and exercise the owning entry point before it can establish that the gap is fixed.

## Exact source identity

Repository `mastermindx-market-intelligence/mastermind-terminal`, commit `3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9`. The manifest records full SHA-256 values, byte lengths and clickable pinned URLs. The source copies match the upstream Git blobs.

| Source | Git blob | Role |
| --- | --- | --- |
| [finStatementMath.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/finStatementMath.ts) | `9bf1e3077a66d65f2546261cb9efa7b27140fda5` | Runtime helper under test |
| [finStatements.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/finStatements.ts) | `d6b0cff78c94f6c4cead423122cf4fcd6a5f19d5` | Runtime history/gap consumer |
| [markets.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/markets.ts) | `6168662381b7d0a32af90eb262ae2c8862883a1b` | Actual market-classification dependency |
| [fund.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/fund.ts) | `7d60914b44d123bc30e63dc7a0652b9ea24aa9a1` | Verified source contract, type-only imports stripped by Node |

## Observed helper behavior

| Cases | Study tasks | Executed observation |
| --- | --- | --- |
| ST01 | S01 | Unique annual fiscal identity yields 20% growth. The real Revenue-history consumer produces the same value and delta. |
| ST02–ST03 | S03 | True zero is retained and counted as coverage. A zero current value after a positive prior yields −100%. A zero prior withholds the percentage. Null retains its history slot. A real flat comparison remains numeric 0. |
| ST04–ST09 | S02 | Duration mismatch, different/unknown basis, incompatible period kind, duplicate prior/current identity and partially supplied qualifying metadata all return null comparators. |
| ST10 | S02 | A canonical mixed YTD/discrete transport remains labeled Interim. Its values are retained and the mismatched comparison is null. |
| ST11–ST12 | S04 | Canonical HK H1/H2 values are never differenced again. Producer-null EPS remains null. Chart and normalized revenue share the same array reference. Revenue history matches. Same-half-year YoY follows fiscal identity across a calendar-year boundary. |
| ST13–ST14 | S04 | Legacy HK/CN cumulative normalization differences additive flows, preserves negative discrete net income and withholds non-Q1 EPS. Missing initial or cross-year bases yield null. |
| ST15–ST16 | S02/S04 | Fully absent legacy fiscal metadata retains annual and four-quarter positional comparisons. The actual US market gate prevents cumulative differencing even for cumulative-shaped growing values. |
| ST17 | S01/S04 | Statement basis fallback selects the available transport. With neither basis available it retains the requested basis for deterministic empty handling. |
| ST18–ST20 | S06 | Bank, mixed and ambiguous source families receive the actual helper labels and industrial-geometry eligibility. Mixed expenses preserve each period's appropriate definition. |
| ST21 | S03 | Vendor gap labels are scoped to the selected statement block. |
| ST22 | S02/S04 | A synthetic missing-Q2 legacy history emits a six-month subtraction under the Q3 label. This case has `EXPECTED_UNDESIRABLE_BASELINE` expectation metadata. |

### ST22 requires a later owner-qualified disposition

The synthetic source has Q1 2025 cumulative revenue 120 and Q3 2025 cumulative revenue 390, with Q2 absent. The trailing four-value chunks satisfy the legacy cumulative-shape heuristic, including one chunk that crosses a fiscal-year boundary. Actual `incomeView("0700.HK", set, "quarterly")` returns 270 for the retained label `Q3 2025`.

The subtraction spans April through September. The helper's legacy path checks same-fiscal-year adjacency in the stored array, which does not establish adjacent fiscal quarters. The source owner must qualify the missing base or emitted duration before this result can be represented as a discrete quarter. Keep the independently sourced cumulative observations available. This diagnostic establishes a synthetic path and makes no claim about its live frequency. [Legacy subtraction](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/finStatementMath.ts#L142-L163) · [Market and normalization gates](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/finStatementMath.ts#L536-L601)

## Deliberately unexecuted scope

- S05 CN annual-only forecast rendering, null `eps_q` handling and the optional third annual target belong to `gen_fund_cn.py` and `ForecastPage.tsx`. These helpers cannot establish those outcomes.
- Proposed UI reasons remain untested. `priorComparableIndex()` and `comparablePeriodChanges()` return number-or-null without a typed reason. A later presentation must bind any specific explanation to the corresponding source condition.
- ST11 proves that canonical producer-null EPS is retained. It does not run the HK producer that decides whether the source EPS is safely available. ST13 separately executes the legacy helper's actual EPS-withholding behavior.
- Financial-family eligibility flags and labels are executed. Actual row/chart omission in a component requires its separate test.
- Source access, filing/restatement clocks, real issuer payload coverage, privacy workflows, browser/Paper interactions, F01/F02 adoption and visual acceptance retain their existing owners and acceptance gates.

This diagnostic is retained as source evidence in the existing D07 design/research carrier.
