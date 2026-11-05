---
key: CANON-RSI-MACD-IS-NOT-THE-SERVED-INDICATOR
claim: >
  The served Prophet US board path never imports engine.canon, and the served RSI-MACD
  (RSI14 -> MACD 14/60/5 with Pine RMA smoothing) agrees with engine.canon's RSI-MACD only
  after a warm-up of about 400 sessions: on SPY daily the maximum |MACD| difference is
  3.21e-05 after bar 400 and 0.593 inside the first 400 bars, because the two
  implementations seed their recursions differently; an independent Pine-RMA rewrite
  matches the served path to 8.5e-14.
falsifier: >
  Either (a) a grep of the served board modules (the import chain of the US board
  builder recorded in results/A1/served_definition.md) returning an `engine.canon`
  import, or (b) re-running results/A1/code/run.py and finding max |served - canon| MACD
  above 1e-4 after bar 400, or below 0.1 inside the first 400 bars, on the pinned SPY
  daily store.
so_what: >
  Any research lane that imports engine.canon to "reproduce the served signal" is
  reproducing a different first-400-session history for every name. B1 (and C2, E and
  every later lane on the B1 panel) must discard a 400-session warm-up measured from the
  name's first inner-joined session, or seed exactly as the served path does. A reviewer
  who sees served-vs-canon disagreement should check the bar index before calling it a
  bug. Temporal Grain and V4 owners should treat canon and served as two indicators at
  the start of every history and one indicator thereafter.
kind: landmine
verified_at: 2026-10-04
verified_by: >
  results/A1 round 1 (RESULT.md, result.json, code/run.py) and the independent Opus
  recomputation in the A1 review (3.21159730347631e-05 after bar 400;
  0.5931894460276439 first 400; Pine RMA rewrite 8.526512829121202e-14; 1,069 warm-up
  bars; 302 served rows), all matched.
scope: [macro, prophet]
confidence: verified
---

# Canon RSI-MACD is not the served indicator until bar ~400

Measured by lane A1 of the Astra -> Fable regime/indicator/timeframe program. The served
definition, its import chain and the buyable-tier receipt live in
research/prophet_v4/astra_regime_indicator_handoff_20261004/results/A1/served_definition.md.
