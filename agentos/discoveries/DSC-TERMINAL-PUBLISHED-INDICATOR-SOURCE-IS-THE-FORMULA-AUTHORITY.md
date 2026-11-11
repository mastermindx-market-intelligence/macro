---
key: TERMINAL-PUBLISHED-INDICATOR-SOURCE-IS-THE-FORMULA-AUTHORITY
claim: >
  In the Terminal PR 637 candidate, the user-visible Bollinger Pine definition
  and the Terminal interpreter provide a distinct internal implementation
  witness for the retained 500-bar fixture using ta.sma and the default
  two-argument ta.stdev, without certifying every built-in indicator or external
  TradingView behavior.
falsifier: >
  At the exact companion candidate and fixture, run
  terminal/lib/__tests__/bollingerRenderParity.test.ts. The claimed witness
  fails if runPine(IND_DEFS.bb.source, BARS).result.plots no longer matches
  bollingerBands(BARS, 20, 2) at 1e-12, or if the sample-sigma negative control
  no longer fails. The witness is inapplicable to a different definition,
  interpreter, fixture, argument mode or input history until requalified.
so_what: >
  Resolve a formula disagreement by naming the user-facing contract and checking
  its implementation with a separately traced witness, rather than selecting
  whichever side already has a passing test. For this candidate the published
  definition and internal interpreter distinguish the charted population-sigma
  bands from the Macro sample-sigma event-signal fixture. Keep that evidence
  scoped to its exact functions and inputs. EMA initialization, warmup, missing
  values and other deviation modes need their own version-specific bar-by-bar
  witnesses; agreement within one repository is not external conformance.
kind: architecture
verified_at: 2026-09-18
verified_by: >
  Historical companion report in mastermind-terminal PR 637 and its
  terminal/lib/__tests__/bollingerRenderParity.test.ts: published BB source
  run through lib/pine-engine matches the candidate owner within 1e-12 on the
  retained 500-bar fixture and rejects the ddof=1 bands by the recorded 0.1997%
  upper-band discrepancy. November 5 source/status qualification: PR 637 remains
  open at b9a3c2950492945300af463a9aff5d4c3d0ac298; no test rerun or protected
  or deployed adoption is claimed here.
scope:
  - mastermindx-market-intelligence/mastermind-terminal
  - terminal/lib/indicators.ts
  - terminal/lib/pine-engine/**
  - tests/fixtures/tech_parity/**
confidence: verified
---

## Qualified internal witness, with explicit limits

The September 18 companion record compares the charted Bollinger contract with
the Macro event-signal fixture. The published definition and its internal
interpreter are useful because they are separately traceable from the renderer
and the fixture generator. They still share a product context and assumptions;
they are not an independently certified external-platform oracle.

The retained test exercises the candidate's default two-argument
`ta.stdev(close, length)` and `ta.sma` on the specified finite fixture.
Its positive agreement and sample-sigma negative control support that bounded
decision: `DEC:TERMINAL-CHARTED-BOLLINGER-IS-POPULATION-SIGMA`.
They do not qualify missing-value behavior, warmup, other deviation modes,
every built-in source definition, or external runtime versions.

The companion source initializes `ta.ema` from its first valid source value.
The earlier statement that this necessarily differs from TradingView because
TradingView uses an SMA seed was not established by the Bollinger experiment and
is withdrawn. Do not replace it with an unverified opposite assertion. Before
using an EMA-family witness, bind the exact platform/version, definition,
history, initialization, warmup and missing-value treatment and compare the
series bar by bar. See the official
[Pine execution model](https://www.tradingview.com/pine-script-docs/language/execution-model/)
for why evaluation scope and historical buffers matter.

As of November 5, [Terminal PR 637](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/637)
is open at `b9a3c2950492945300af463a9aff5d4c3d0ac298`.
This Macro documentation does not itself adopt, deploy or validate that
Terminal candidate. The historical test date and measurements retain their
original scope.
