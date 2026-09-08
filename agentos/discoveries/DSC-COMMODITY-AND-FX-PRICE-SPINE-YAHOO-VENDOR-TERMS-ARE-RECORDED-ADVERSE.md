---
key: COMMODITY-AND-FX-PRICE-SPINE-YAHOO-VENDOR-TERMS-ARE-RECORDED-ADVERSE
claim: >-
  Both the FX and the commodity price spines read the same `yahoo` store group, and
  the only written posture for that vendor is `config/dataset_registry.yml:63`
  `licensing: vendor_terms_personal_use` — a personal-use vendor-terms record that
  two paid surfaces republish; recorded and adverse, never cleared.
falsifier: >-
  grep -rn "Yahoo\|yfinance\|vendor_terms_personal_use" docs/QUAL_DATA_COMPLIANCE.md
  agentos/decisions/ agentos/discoveries/ config/ research/ no longer returns
  `config/dataset_registry.yml` `licensing: vendor_terms_personal_use` (or a later
  `DEC-*` that supersedes it); or engine/forex_inputs.py:66 and
  engine/commodity_inputs.py:49 no longer read store.read("yahoo", ...).
so_what: >-
  A future session must not treat FX or commodity prices as rights-cleared merely
  because they are on disk, and must not type the spine `unknown` or "unrecorded".
  The written posture is personal-use vendor terms under a paid SaaS. Any packet
  that widens, monetizes, redistributes, or exports those series needs a vendor
  ruling that supersedes `config/dataset_registry.yml:63` first; any rights table
  that lists them must type them `recorded-and-adverse (vendor_terms_personal_use)`,
  never "no restriction" and never "unrecorded".
kind: constraint
verified_at: 2026-09-07
verified_by: >-
  engine/forex_inputs.py:66-67,157; engine/commodity_inputs.py:49-53; scripts/collect.py:298;
  config/dataset_registry.yml:63 and :104 (`licensing: vendor_terms_personal_use` on
  `vendor: yahoo`); research/MASTERMIND_DATA_CONTRACTS.md:103 (yfinance-sourced stores
  republished to a paid product; exposure written at dataset_registry.yml:57
  `licensing: vendor_terms_personal_use`); research/IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md:189
  (CANONICAL_PRICE_TAPE (REUSE; yfinance exposure documented in-repo)); widened grep
  2026-09-07 over docs/, agentos/decisions/, agentos/discoveries/, config/, research/
scope: [macro, F01-MACRO-MARKETS, engine/forex_inputs.py, engine/commodity_inputs.py, scripts/collect.py, config/dataset_registry.yml]
confidence: verified
---

# Commodity and FX price spine Yahoo vendor terms are recorded and adverse

`engine/forex_inputs.py:66-67` (`ticker = meta["yahoo"]`; `df = store.read("yahoo", ticker)`) and
`engine/commodity_inputs.py:49-53` (`load_price(ticker)` → `store.read("yahoo", ticker)`) both bind
their price series through the same `yahoo` store group. That group is fed by
`collectors.intl_prices.IntlPriceAdapter`, registered at `scripts/collect.py:298` ("yfinance
indices + vol + FX").

| surface | consumer (file:line) | vendor path |
|---|---|---|
| FX spot / DXY | `engine/forex_inputs.py:66-67,157` → `templates/forex.html.j2:301` | `store.read("yahoo", …)` |
| commodity futures/spot | `engine/commodity_inputs.py:49-53` → `scripts/build_commodities.py:1199` | `store.read("yahoo", …)` |

The only written posture for that vendor is `config/dataset_registry.yml:63`
`licensing: vendor_terms_personal_use` (same value at `:104` on the second `vendor: yahoo`
block). `research/MASTERMIND_DATA_CONTRACTS.md:103` records that `data/yahoo` (with
`data/stocks` and `data/baskets/ohlcv`) is yfinance-sourced and republished to a paid
product, and that the registry row is the only place that exposure is written down.
`research/IMCE_ROUND3_ARCHITECTURE_FREEZE_BY_FABLE.md:189` lists `CANONICAL_PRICE_TAPE`
as `REUSE; yfinance exposure documented in-repo`. `docs/QUAL_DATA_COMPLIANCE.md` still
contains no Yahoo/yfinance clause, and no `DEC-*` clears the personal-use bar.

This is a durable, non-obvious fact: two paid-surface families (FX monitoring, commodity
monitoring) both sit on a **recorded and adverse** vendor-rights posture (personal-use
terms under a paid SaaS), not a blank one. Any future packet that widens exposure of
these series (new export, new paid tier, bulk API, redistribution) must treat the
posture as `recorded-and-adverse (vendor_terms_personal_use)`, not as cleared and not
as unrecorded, and should read
`research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md`
§4 V-1 before proceeding.
