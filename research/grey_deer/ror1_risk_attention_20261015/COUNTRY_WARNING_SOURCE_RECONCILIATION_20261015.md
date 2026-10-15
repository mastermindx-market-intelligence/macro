# ROR-1 — Country warning source contract reconciliation (October 15, 2026)

**Status:** bounded read-only source audit. **This is not a released cross-country warning** or a source-writer transfer.

**Evidence:** [machine-readable pinned receipt](COUNTRY_WARNING_INPUT_RECEIPT_20261015.json). Macro source pin `9b255a5377385a6b0dab23850e6a6ff67714a5f1`; held Grey Deer publisher/adapter #8132 head `639aaed06ce7754110d3bd6e94a0b704bb6c7760`. #8132's exact adapter is `scripts/risk_warning_source_adapter.py`, Git blob `de4f1b7b2427da1c3e7543cc787b1a45cd8228db`.

## What actually fails before any customer presentation

The existing held source adapter `augment_banner_payload` declares country inputs at `data/{regime,china_regime,hk_regime,canada_regime}/latest.json:risk_radar`. It refuses nonfinite JSON via `parse_constant=_nonfinite_json`, rejects absent `risk_radar` as `missing_radar`, and independently compares each native Radar snapshot's `asof` with the market owner-supplied expected session. Those are valid authority and quality protections. The supplied producer/file assumptions are not aligned with the October 15 committed outputs:

| Market | Declared Radar source | Pinned input | Candidate source result |
|---|---|---|---|
| US | `regime/latest.json:risk_radar` | Strict JSON, native Caution dated Oct14, parent Oct14 | Available for independent calendar qualification |
| CN | `china_regime/latest.json:risk_radar` | Strict JSON dated Oct15, **no Radar key** | `missing_radar` |
| HK | `hk_regime/latest.json:risk_radar` | **Bare NaN** in a non-Radar field and no root Radar key | `invalid_json` |
| CA | `canada_regime/latest.json:risk_radar` | **Bare NaN** and no root Radar key | `invalid_json` |
| International 7 profiles | `intl/latest.json:records[cc].risk_radar` | Strict JSON with 7 Radar records, individual observations Oct08–09 | Availability requires independent local expected-session checks |

A non-JSON `NaN` is accepted by Python's *default* JSON parser but explicitly rejected by #8132's strict decoder and by JavaScript JSON.parse. **Do not solve this by weakening strict JSON validation** or by counting missing Radar as calm.

## Canonical country Market State is real but not the native Radar schema

These two separate persistent artifacts are valid:

- `data/china_market_state/latest.json`, Git blob `faf675be75424ed14c29e2a0815002e885abbcb6`: **China Oct15, 24/RISK_OFF**, presentation Radar **risk-off / intensity 97**.
- `data/hk_market_state/latest.json`, Git blob `b0d139c6d0021a9b5e721243bae45619af062519`: **Hong Kong Oct15, 32/RISK_OFF**, presentation Radar **caution / intensity 81**.
- U.S. `data/market_state/latest.json` separately indicated **44/MIXED through Oct14** at the preceding accepted pin.

These nested `market_state.radar` blocks are *reduced display projections*, **not `risk_radar_intl.v1`**: neither includes its native `schema` and `asof`. Therefore merely aliasing `market_state.radar` into the held adapter would fabricate source identity/session qualification. The China/HK Market State verdicts must also remain distinct from their Radar states: HK Risk-off does **not** mean HK Radar issued native Risk-off.

## The existing producer already documents the likely boundary

`scripts/build_china.py` and `scripts/build_hk.py` call `engine.risk_radar_intl.snapshot(CN_PROFILE/HK_PROFILE)` *inside page rendering*, then persist a transformed Market State. `scripts/build_feeds.py` explicitly says those country radars were **render-inline and never persisted** and creates a `site/feeds/intl_spillover.json` multi-country snapshot by recomputing from committed stores. That feed artifact was **not found in the inspected Git tree**. This does not prove a deployed/R2 copy is absent or entitled; origin, generation order and publication clocks need their actual owner.

Therefore this is a **schema/source-location mismatch**, not evidence the underlying regional Radar model failed to calculate risk. The country pipeline must supply an authorized *native* session-dated Radar artifact at an existing accepted publication boundary before #8132 can qualify CN/HK/CA warnings. Options are existing feed-plane integration after verifying serving and independent expected-market sessions, or an additive owner-persisted source-native Radar read. Neither option is accepted until the source/transport owner provides the real path, identity, clock, input-health and normal release proof. Avoid creating a second risk engine, ledger, scheduler or publication plane.

## Proposed first-glance user truth (copy prototype, not deployed)

**EN:** *Asia: Risk-off — China 24 and Hong Kong 32 (Oct 15 market reads). U.S.: Mixed 44 (Oct 14 close). U.S. AI leadership damage was separately observed; data coverage remains partial. These are distinct regional conditions, not proof of cross-market contagion.*

**ZH:** *亚洲市场：风险规避——中国 24、香港 32（10月15日市场读数）。美国：混合 44（10月14日收盘）。美国 AI 领涨股群体另有已观测的受损迹象；部分数据覆盖仍不完整。不同市场的风险状态不等于已证实跨市场传染。*

Do not use a forced composite, numerical cash/sizing advice, crisis probability, or universal red band to substitute for source-native warnings. The public copy is conditional on authentic qualified current source dates and the existing risk-projection owner.

## Source-owner acceptance

1. Identify the **original native CN/HK/CA Radar producer** and one authoritative session-stamped artifact per market, with explicit UTC/market calendar rules and source hashes. Do not infer freshness from wrapper build time.
2. Feed the unchanged source-native schemas to the existing `project_warning_set` on a test root; missing/invalid data remains unavailable; use a dated unverified prior only under accepted retention rules.
3. Test country-clock mismatch, holiday, malformed/NaN, no native Radar, HK caution vs HK measured risk-off, and same-day regional contradictions; count no contextual support as a forecast vote.
4. Prove the **real** publisher emits one qualified record for each eligible market; one permitted consumer displays each at glance tier with clear market/observation date, then verify authenticated origin/edge/browser and notification/episode semantics.
5. Preserve current #8132 REQUEST_CHANGES/HOLD, #9428 source/CI authority and the independent #894 Terminal production-data incident. Passing a source test cannot clear these gates.

**Conclusion:** Current source adapter produces CN `missing_radar`, HK/CA `invalid_json` for its declared input paths. Real CN/HK market-state risk-off evidence exists elsewhere. The next fix is an owner-qualified *source-binding and publication* repair, not a new detector.