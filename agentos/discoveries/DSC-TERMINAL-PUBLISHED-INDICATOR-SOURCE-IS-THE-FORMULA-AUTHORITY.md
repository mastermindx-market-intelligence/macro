---
key: TERMINAL-PUBLISHED-INDICATOR-SOURCE-IS-THE-FORMULA-AUTHORITY
claim: >
  Every Terminal built-in indicator ships a user-visible Pine definition in
  IND_DEFS.<key>.source (the chart's "Source code..." button), and that published
  text — executed by the Terminal's own lib/pine-engine — is an executable oracle
  for the indicator's formula that is independent of both ChartPanel and the Macro
  Python parity fixtures.
falsifier: >
  In mastermind-terminal, `grep -n 'source:' terminal/lib/indicators.ts` no longer
  shows a Pine body per indicator, or lib/indicators.ts:39 stops describing it as
  shown by "Source code...", or running that source through runPine() no longer
  reproduces the rendered series — e.g.
  `runPine(IND_DEFS.bb.source, BARS).result.plots` ceasing to match
  bollingerBands(BARS, 20, 2) at 1e-12, as asserted by
  terminal/lib/__tests__/bollingerRenderParity.test.ts.
so_what: >
  When a Terminal indicator's TypeScript disagrees with a Macro Python fixture, do
  NOT settle it by asking which side has a passing test, and do NOT edit the fixture
  to whatever the chart currently does. Run the published source through the Pine
  engine: it yields the expected series from the contract the product states to its
  users, giving a non-circular third implementation to adjudicate against. This is
  how the Bollinger ddof dispute was decided (DEC:TERMINAL-CHARTED-BOLLINGER-IS-POPULATION-SIGMA).
  Caveat before reusing it: some sources are labelled "DISPLAY-TIER DESCRIPTIVE"
  (e.g. IND_DEFS.ribbon.source) and are weaker evidence than a plain definitional
  one like IND_DEFS.bb.source, and the engine is not uniformly TradingView-faithful —
  its ta.ema is FIRST-VALUE seeded (lib/pine-engine/runtime.ts:466) where
  TradingView's is SMA-seeded, so the oracle is sound for ta.stdev/ta.sma but must be
  spot-checked per function before being trusted for EMA-family indicators.
kind: architecture
verified_at: 2026-09-18
verified_by: >
  mastermind-terminal PR #637; terminal/lib/__tests__/bollingerRenderParity.test.ts
  (published BB source run through lib/pine-engine matches indicatorMath.bollingerBands
  within 1e-12 across 500 fixture bars, and rejects the ddof=1 bands by 0.1997%);
  terminal/lib/indicators.ts:39,127; terminal/lib/pine-engine/runtime.ts:466,481
scope:
  - mastermindx-market-intelligence/mastermind-terminal
  - terminal/lib/indicators.ts
  - terminal/lib/pine-engine/**
  - tests/fixtures/tech_parity/**
confidence: verified
---

The Terminal publishes each built-in indicator's formula to its own users as Pine, and it
also ships an interpreter for that Pine. Those two facts together are more useful than
either alone: the published text is a contract the product has already made, and the
interpreter turns it into numbers that were produced by neither the renderer nor the
fixture generator.

That is what made the Bollinger adjudication decidable rather than a matter of taste. Both
candidate formulas had a defender — ChartPanel drew one, a green parity test certified the
other — and the tie was broken by a third implementation deriving the expectation from
`ta.stdev(close, length)`, the definition the chart itself offers under "Source code…".

The technique generalizes to any indicator with a definitional source, and the same run
that validated it also exposed its limit: the engine's `ta.ema` does not seed the way
TradingView's does, so an EMA-family oracle would currently vouch for a third answer rather
than the right one. Check the function you are about to lean on before you lean on it.
