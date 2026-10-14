# T08 — capitalization, participation, issuance, subscription

Census date 2026-10-12. Tree: candidate base `#8050` `fd8095012e91` on `origin/main`, plus the lane edit in `engine/crypto_market_state.py`. Template and `scripts/build_crypto.py` are unchanged in git; wording fixes are patches under `research/crypto_science/patches/`.

Classes: **capitalization** (price × supply, or a share of that), **participation** (breadth count or a named volume proxy), **issuance** (token or stablecoin supply), **subscription** (a source that publishes creations/redemptions). A null is unavailable, never zero. R15 (`research/CRYPTO_R15_DESK_INTEGRATION_RESULTS.md` on `fd8095012e91`, section 1) already keeps a known zero, an unavailable target, a stale decision, and a missing chart as different states. This census applies that split to class cap and the H3 shelf.

## Rendered copy (`templates/crypto.html.j2`)

| Line | EN / ZH | Computed from | Class | Verdict |
|---|---|---|---|---|
| 16 | seo "money flows" (EN only; no ZH string in the template) | prose, not a series | mixes three measurements | RELABEL(`measured subscriptions, stablecoin supply, spot participation` / gloss 已测量申购、稳定币供应与现货参与度) |
| 293 | nav `Capital` / `资金` → `#money-flows` | shelf title, not a series | mixes subscription, supply, and a volume proxy | RELABEL(`Subscriptions and supply` / `申购与供应`). Anchor id stays `money-flows` (`tests/test_crypto_wave2.py` navigation test). |
| 298–299 | `market.stance` / `summary` (+ ZH) | `_hero` in `engine/crypto_market_state.py:398` | capitalization, or issuance when supply is the leg that moved | SUPPORTED. The candidate-base hero called a falling share "wider participation" and "Capital is expanding". |
| 306 | `Derived total market capitalization` / `衍生总市值 · 描述性阶段历史` | `total_market_cap_history` `engine/crypto_market_state.py:184` | capitalization, but the tail may be a direct CoinGecko splice (`:75`) | RELABEL to name derived-or-direct splice and that regime bands skip the gap |
| 308 | `Total market cap` / `加密总市值` + `30-day change` | `total_market_cap`, `total_30d_pct` (`:619–620`) | capitalization | SUPPORTED |
| 309 | `Bitcoin market share` / `比特币市值占比` | `btc_dominance`, `dominance_30d` (`:623–626`) from `bgeo.btc_dominance` | capitalization share, not breadth | SUPPORTED |
| 333 | `Is participation broadening?` / `参与是否正在扩大？` and the next sentence separating share, returns, and breadth | question; the count is `breadth_read` | participation, and it says the three are different | SUPPORTED |
| 347 | `Positive 30-day returns` / `30日回报为正` | `engine/crypto_universe.py:158` `breadth_read`: count of positive reported 30d returns; missing returns excluded | participation (breadth/count) | SUPPORTED |
| 387 | `Money Flows` / `资金流`; `three class-level receipts` | shelf groups ETF, stablecoin supply, BTC volume | three classes under one flow name | RELABEL(`Subscriptions, supply, participation` / `申购、供应与参与`; `three separate measurements` / `三项分开的测量`) |
| 389 eyebrow | `US spot-BTC ETFs · 5D` / `美国现货比特币 ETF · 5日` | `flows.etf.value` = sum of last 5 Farside `total` prints (`:641`, `:511`) | subscription | SUPPORTED |
| 389 receipt | `Farside fund-level net flows… class liquidity` / `基金级净流量；仅作全市场流动性情况` | same Farside print, millions of dollars | subscription, over-read as class liquidity | RELABEL(`Farside fund-level net creations and redemptions, in millions of dollars. A bitcoin-ETF subscription measurement, not class capitalization.` / `Farside 基金级净申购与赎回，单位为百万美元。这是比特币 ETF 申购测量，不是全市场市值。`) |
| 390 eyebrow | `Stablecoin tide · 30D` / `稳定币潮汐 · 30日` | `flows.stablecoins.change_30d_usd` from DefiLlama `stablecoin_mcap_usd` (`:649–651`) | issuance/supply. "Tide" reads as flow | RELABEL(`Stablecoin supply · 30D` / `稳定币供应量 · 30日`) |
| 390 receipt | `Aggregate circulating supply from DefiLlama.` / `DefiLlama 汇总流通供应量。` | same stock | issuance | SUPPORTED as supply. Patch adds that it is not an ETF subscription. |
| 391 | `Spot participation proxy` / `现货参与度代理` and the BTC volume-percentile receipt | `flows.volume` (`:659–665`), percentile of coinbase BTC volume vs its own trailing year (`:530–532`) | participation, BTC-only proxy | SUPPORTED |
| 400 | `Perpetual funding` / `永续合约资金费率` | template hard-codes an unqualified interval; the number is not rendered | funding rate, not a capital flow | SUPPORTED (withheld) |
| 401 | `Open interest / BTC cap` / `未平仓量 / BTC 市值` | `heat.open_interest` from vector signals `oi_mcap_ratio` | leverage ratio vs BTC cap | SUPPORTED |
| 404 | `Altseason meter` / `山寨季仪表`; receipt `ETH/BTC relative trend plus BTC dominance` | `heat.altseason` (`:586–602`), kind `relative_price` | relative price + share, not a breadth count | SUPPORTED as that receipt. State words no longer say "participation" (`ETH leading on relative trend` / `BTC leading on relative trend` / `Mixed relative trend`). ZH for those three words is in the builder patch until `_state_zh` learns them. |
| 436 | `不推断各资产占比` / asset percentages | recorded model budget, not `btc_dominance` | budget split | SUPPORTED as allocation, not market share |

`scripts/build_crypto.py:540–554` aria still says "Derived total crypto market cap…". That is the same splice series. RELABEL in the builder patch.

## `build_market_state` fields

| Field | From | Class | Verdict |
|---|---|---|---|
| `stance`, `summary` (+ ZH) | `_hero` `:398`. Issuance if BTC supply (`mcap/close`) moved ≥1pp and price did not (`_cap_attribution` `:337`). | capitalization or issuance | SUPPORTED |
| `total_market_cap`, `total_30d_pct`, `total_state` | spliced cap `:619–621`; direction thresholds ±3% `:491` | capitalization | SUPPORTED |
| `btc_dominance`, `dominance_*` | bgeo share, ±1pp `:492` | capitalization share | SUPPORTED. A share change is not breadth. |
| `cap_basis.segments/splices` | `:635`, assembly `:75`. `date`, `from_basis`, `to_basis`, `support_before`, `support_after`, `level_ratio` | basis of the cap series | SUPPORTED |
| `regimes` | `class_regimes` on the continuity-adjusted path `:634` | capitalization bands | SUPPORTED. A raw splice still looks like a bull band if the adjustment is stripped; the shipped path does not. |
| `cap_attribution.kind` | `valuation` / `issuance` / `mixed` / `share_or_flat` / `unavailable` | cause of the 30d cap move | SUPPORTED. Not a score. |
| `flows.etf` | Farside `total`, kind `subscription`, cadence `us_business_day` | subscription | SUPPORTED |
| `flows.etf.observation` | `observation_status` `:286` | pending (weekend gap with Friday on file) / stale (missed weekday) / zero (expected day printed 0) / current / unavailable | SUPPORTED. Weekend pending is not a zero fill. |
| `flows.stablecoins` | DefiLlama stock, kind `issuance`, cadence `calendar_day` | issuance | SUPPORTED as supply. Not a mint/redeem ledger and not an ETF subscription. |
| `flows.stablecoins.observation` | same clock, calendar cadence. A Friday print on Sunday is stale. Direction word becomes `Unavailable` while the last level stays (`:508–509`) | issuance freshness | SUPPORTED |
| `flows.volume` | BTC spot volume percentile. Missing history is `Unavailable`, not `Normal` (`:533–534`) | participation proxy | SUPPORTED |
| `heat.altseason` | withheld (`Unavailable`, value null) when `dominance_30d` is missing (`:587–589`). No `(dom_30d or 0)`. | relative price | SUPPORTED |
| `heat.funding`, `open_interest`, `volatility` | vector signal row | leverage / vol, not flow | SUPPORTED where the input exists; funding's page number stays withheld by the template |
| breadth | not a `build_market_state` field. `breadth_read` → template line 347 and `class_state.market.breadth_state` (`scripts/build_crypto.py:512`) | participation | SUPPORTED |

## Defects this lane closed in the engine

Before the edit, a cap rise with a falling share produced "Capital is expanding beyond Bitcoin" / "Advancing with wider participation" (`engine/crypto_market_state.py` at candidate base, the block that is now `_hero`). A missing cap fell through to "Range-bound, waiting for participation". A missing volume percentile became "Normal". Altseason treated a missing share change as zero. `class_regimes` had no splice record, so a derived-to-direct level gap was a momentum event. ETF and stablecoin freshness shared no source cadence, so a weekend gap and a missed daily print were the same shape, and a missing frame was not distinguished from a printed zero by an observation field.

## Patches (not applied here)

- `research/crypto_science/patches/cx-t08-20261012__crypto.html.j2.patch` — the RELABEL strings above, plus a splice line (`date`, bases, support) and the observation label when the engine sent one. `id="money-flows"` unchanged.
- `research/crypto_science/patches/cx-t08-20261012__build_crypto.py.patch` — aria EN+ZH, `_state_zh` for the three relative-trend states, and additive `cap_move`, `cap_splices`, `flow_kinds` on `crypto.class_state/v1`. The existing `flows` map stays a state word.

SEO has no ZH slot. Gloss only: `每日加密市场状态：头部资产、已测量申购、稳定币供应、现货参与度、杠杆、波动、配置、比特币、以太坊与上市加密股票。`

## Repair r2

Display tier unchanged. No score, size, or authority.

NYSE full-closure dates are `lib.nyse_calendar.holidays` (`lib/nyse_calendar.py:85`), read through `is_session` (`:121`) by `_expected_us_session` (`engine/crypto_market_state.py:281`). A full-day closure, and the weekend after it when the prior session print is on file, is `pending`. The 5-day direction word stays (`Rising` / `Falling` / `Steady`). A missed session weekday stays `stale`, and that state word becomes `Unavailable`. The calendar is rule arithmetic for any year (MLK from 1998, Juneteenth from 2022, plus `ONE_OFF_CLOSURES`). It has no year table. A date it cannot resolve is not marked `stale`. This replaces the weekends-only claim in the `flows.etf.observation` row above.

An issuance or valuation sentence is emitted only when that bitcoin leg and `total_30d_pct` share a sign. An opposed leg sets `cap_attribution.kind` to `unattributed`. The hero then uses the existing direction headline (`Market cap is higher` / `Market cap is lower` / `Market cap is little changed`) and does not attach the issuance note or the price-change summary. `note_en` and `note_zh` are empty for that kind. No new user-facing sentence. Same-sign issuance and valuation still use the sentences already in `_hero`.

`cap_attribution.material_pct` is `1.0` and `cap_attribution.hero_band_pct` is `3.0`. Notes are not rewritten to name those numbers.

The altseason rail `else 0` at `templates/crypto.html.j2:404` is already omitted when the value is null by `origin/claude/cx-t19p-20261012` patch `research/crypto_science/patches/cx-t19p-20261012__crypto.html.j2.patch` (`141eb25c`). No r2 template patch.
