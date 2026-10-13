---
key: F3-YIELD-MOMENTUM-HAS-NO-CONSUMER
claim: >
  The RIC F3 deterministic yield-momentum capability (macro PR #6721, squash
  7a2a84df4d14, plus the origin-preserving follow-up #7291 / 1ec47315d963) is BUILT
  and CORRECT but INERT: nothing downstream reads it. Full census at macro
  ea194c5d, 2026-09-22 — `yield_momentum` is PRODUCED once
  (engine/rate_inflation_transmission.py:595 -> data/transmission/latest.json) and
  COPIED once (engine/rates_inflation_command.py:1234 reads it back out of that
  artifact, :1422 writes it into data/rates_command/latest.json). That is the whole
  chain. It is NOT copied by engine/neuralweb/world_state.py `_compose_rates_command`
  (which forwards only asof/net_state/state_label/hawk_score/ease_score/stance/
  implied_m12/policy_rate/path_plain/futures_plain), so it never enters
  data/neuralweb/world_state.json or the RCB lobe. It is NOT read by
  engine/neuralweb/market_packet.py `_rates_block` (the live per-turn chat grounding
  packet), which takes only `board.rate_path_row` / `inflation_row` / `risk_row` /
  `curve_regime_key`. No template references it; `grep -rl yield_momentum site/`
  returns nothing. The provenance fields #7291 added — `observation_origin`,
  `path_qualified`, `carried_level`, `frame_as_of` — are WRITE-ONLY: nothing outside
  engine/yield_momentum.py reads any of them. The live Fed Path — Forward Board on
  https://www.mastermind-x.com/macro.html renders (hawk 3 / ease 3, "Two-sided — watch
  the tape", asof 2026-09-18) with ZERO F3 fields. The user's actual live 20Y read
  comes from a DIFFERENT owner — engine/market_os/macro_workspaces/rates_curves.py
  (`SERIES_US20Y, COL_US20Y = "DGS20", "us20y"`, `us20y_level`) ->
  macro_rates_curves.html — which is independent of F3 and carries no momentum state.
falsifier: >
  Any new reader of the `yield_momentum` key outside
  engine/rate_inflation_transmission.py and engine/rates_inflation_command.py — a
  template, a site/ artifact, a world_state lobe field, a market_packet block, or a
  scored leg — refutes this. Re-run: `grep -rn yield_momentum --include='*.py'
  --include='*.j2' --include='*.js' engine/ scripts/ templates/ app/ admin/` and
  `grep -rl yield_momentum site/`.
so_what: >
  Correct the capability state: F3 is not BUILT_NOT_PROVEN, it is BUILT_AND_PROVEN_
  INERT. The deterministic logic, the canonical DGS20->us20y mapping, the degradation
  contract and the display-only authority flags (authority/can_score/can_size/
  can_trade all false) are all verified correct on the real current path — but the
  object terminates as an unread field in data/rates_command/latest.json. Do NOT
  commission further F3 *source* work to "prove" it; the source is proven. The only
  work that changes anything is a CONSUMER. Do not build a new rates dashboard for
  it either — the live owner of the user-facing 20Y surface is rates_curves.py /
  macro_rates_curves.html, and engine/credit_momentum.py:1125,1805 already carries an
  interim TLT/IEF block explicitly marked "R6: no yield_momentum.v1 yet", i.e. a
  consumer that was designed for F3 and is still running on a placeholder. That is the
  natural first consumer. Before wiring ANY consumer, settle
  [[DSC:F3-TURN-WATCH-IS-STRUCTURALLY-UNREACHABLE-IN-PRODUCTION]] — a consumer wired
  today would render a permanently-null turn_watch.
confidence: verified
kind: constraint
verified_at: 2026-09-22
verified_by: >
  macro ea194c5d215c64158a828abdc676f47bb7723374; origin/main c538c78eef57 at
  re-check. Census: `grep -rn yield_momentum --include='*.py' --include='*.j2'
  --include='*.js' --include='*.html' engine/ scripts/ templates/ app/ admin/` -> only
  rate_inflation_transmission.py:29,595, rates_inflation_command.py:1234,1235,1422,
  inputs.py:175, yield_momentum.py:208,219, and two credit_momentum.py comments;
  `grep -rl yield_momentum site/` -> empty. engine/neuralweb/world_state.py:1883-1938
  (_compose_rates_command field list); engine/neuralweb/market_packet.py:878-908
  (_rates_block field list). Live: curl https://www.mastermind-x.com/macro.html ->
  HTTP 200, 606738 bytes, 'Fed Path|Forward Path|rate path' x5, 'yield_momentum' x0,
  'turn_watch|rolldown_forming|velocity_bp|acceleration_bp' x0; rendered board text
  "Fed Path — Forward Board / 联储路径 — 前瞻看板 ... 2026-09-18 ... 3 Hawkish / Easing
  3" with legs Rate futures, Breakevens, Oil, Inflation path, Yield curve,
  Expectations, Equity risk-off, Growth cooling, Strong dollar — no momentum leg.
  curl https://www.mastermind-x.com/transmission.html -> HTTP 200, 138822 bytes,
  yield_momentum x0, 20Y refs x0. curl
  https://www.mastermind-x.com/macro_rates_curves.html -> HTTP 200, 376269 bytes,
  '20-year|20Y|us20y_level' x6, yield_momentum x0.
scope:
  - mastermindx-market-intelligence/macro
---

The whole chain, verified hop by hop on the real current path:

    data/fred/DGS20.parquet (us20y)
      -> engine/inputs.py build_features()   [ffill_limit=5, f.attrs['rate_observations']]
      -> engine/rate_inflation_transmission.py:595 build_yield_momentum(f)
      -> data/transmission/latest.json ['yield_momentum']
      -> engine/rates_inflation_command.py:1234 read / :1422 write
      -> data/rates_command/latest.json ['yield_momentum']
      -> (nothing)

At the last hop `_compose_rates_command` and `_rates_block` each pick a fixed field
list that omits it, and no template or site/ artifact mentions it. `yield_momentum`
sits as a top-level sibling of `board` / `expectations_pressure` and never feeds
`hawk_score`, `ease_score` or `net_state` — so the display-only authority contract is
intact, and there is no current-state-as-forecast confusion. It is simply unread.

Related: [[DSC-F3-TURN-WATCH-IS-STRUCTURALLY-UNREACHABLE-IN-PRODUCTION]] — settle that
before wiring the first consumer.
