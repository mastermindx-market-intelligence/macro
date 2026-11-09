---
key: RIC-EXPECTATION-READ-IS-NOT-MARKET-CONSENSUS
claim: >
  As of the 2026-09-24 rates-direction investigation, every historical
  release_forecast forward-ledger row carrying expectation_read used only the
  Cleveland Fed nowcast as its expectation source. The current expectation_read
  contract can accept Cleveland, Kalshi, or Polymarket, but the stored history
  examined here does not establish a multi-source market-consensus series.
  In addition, the legacy champion CPI/PPI/PCE/NFP target epochs are excluded
  from model-evaluation authority by the incumbent structured defect notices.
falsifier: >
  Run `grep -n '\"sources\".*kalshi\\|\"sources\".*polymarket' data/release_forecast/forward_ledger.jsonl`
  and produce an immutable pre-2026-09-24 expectation_read row with an admitted
  numeric market source, or point to an accepted historical consensus owner. For
  the target caveat, inspect `data/release_forecast/defect_notices.json:1` and
  show DN-004 no longer excludes the legacy cross-vintage target epochs through
  an accepted replacement target/model epoch.
so_what: >
  Rates research must not relabel expectation_read as market consensus. A
  catalyst study may consume the exact stored source as contemporaneous
  expectation context only, preserving source names. For CPI forecast math use
  the existing coherent_ridge_v1 / alfred_same_release_vintage_proxy_v1 shadow
  rather than the excluded legacy champion point. Headline and core belong to
  one announcement event, not two independent observations.
kind: data
scope:
  - macro
  - data/release_forecast/forward_ledger.jsonl
  - engine/release_market_context.py
  - research/rates_direction/
confidence: verified
verified_at: 2026-09-24
verified_by: >
  Direct read of compute_expectation_read source, defect_notices.json,
  release_forecast_model_registry.yml, and bounded enumeration of existing
  forward_ledger projection/shadow rows on the rates-direction carrier.
related:
  - "WS:RATES-INFLATION-COMMAND"
  - "DEC:RIC-SHOCK-DRIVERS-NO-PROMOTION"
---
