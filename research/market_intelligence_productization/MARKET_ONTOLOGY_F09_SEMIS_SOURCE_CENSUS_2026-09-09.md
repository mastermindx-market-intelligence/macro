# MARKET ONTOLOGY F09 — Semis / critical-tech source census (2026-09-09)

- **Packet:** B-F09-B5-1 (Market Ontology Half B, family `F09-CAPITAL-MATERIALS`).
- **Class:** research record. This packet builds nothing and integrates nothing. Naming a source is not clearing it.
- **Ledger rows:** sequences from `MO-DELTA-029`; feeds `MO-PAID-040` and `MO-DELTA-027`.
- **Base commit read:** `74ef4e223cb2a22a2b57df23af0142f737f852dd` (`origin/main` on 2026-09-09; later than spec base `e75998821888`).
- **Date:** 2026-09-09.
- **Authority ceiling:** research record only. **No rights are claimed, granted or cleared by this packet.** Naming a source is not clearing it.

Quoted F00C cells from `MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` at the base commit above (CSV lines 77, 79, 84). The literal `UNVERIFIED` appears only inside these ledger citations.

**`MO-DELTA-029` (CSV line 79)**

- `next_bounded_child`: `DONE for the matrix itself; per-family gap children now sequence from the matrix (semis/critical-tech zero-coverage is the largest documented null)`
- `source_rights`: `exchange-traded commodity data unblocked; physical semiconductor supply data likely needs new source (UNVERIFIED)`

**`MO-PAID-040` (CSV line 84)**

- `next_bounded_child`: `DOCKETED_TERMINAL_HALF_B; DEFER — named cross-layer physical-flow source required first (rights docket adjacency)`
- `source_rights`: `EIA public covered for oil; metals/ag/semis supply-chain source UNVERIFIED`

**`MO-DELTA-027` (CSV line 77)**

- `next_bounded_child`: `DOCKETED_TERMINAL_HALF_B; DEFER — flow-source first`
- `source_rights`: `cross-commodity/cross-layer physical-flow source not identified (UNVERIFIED)`

---

## 1. Method and its limits

This census was built from files in this repository, from the coverage-matrix and F00C ledger cells quoted above, and from the builder's own knowledge of named vendors. The builder had no network. Every table row carries a `provenance` of `KNOWN-FROM-REPO` or `KNOWN-FROM-MODEL-KNOWLEDGE` and a `verification_method`. No row claims live verification. A later reader should treat the table as a candidate list that still needs a live confirmation pass, not as a verified inventory. Naming a source is not clearing it.

---

## 2. Scope

Seat ruling D1 (2026-09-09): four sub-domains IN, two ADJACENT-LISTED, everything else out. These are the repo's own `theme_id` values in `config/trade_flow_codes.yml:36-227`, not invented categories.

| sub_domain | HS6 codes already curated | config anchor | this packet |
|---|---|---|---|
| `ai_semiconductors` | 854231, 854232, 854233 | `config/trade_flow_codes.yml:126,137,148` | IN |
| `semicap_equipment` | 848620, 848630, 848640 | `config/trade_flow_codes.yml:159,170,179` | IN |
| `rare_earth_critical_min` | 280530, 284610, 284690, 850511 | `config/trade_flow_codes.yml:39,49,58,68` | IN |
| `nuclear_power` (uranium fuel cycle) | 284410, 284430 | `config/trade_flow_codes.yml:230,241` | IN |
| `solar` | 854142, 854143 | `config/trade_flow_codes.yml:90,102` | ADJACENT-LISTED |
| `grid_electrification` | four codes from line 189 | `config/trade_flow_codes.yml:192` | ADJACENT-LISTED |

Electronic-grade polysilicon (`280461`, `config/trade_flow_codes.yml:114`) sits in the config's `solar` block but is a semiconductor feedstock; it is IN, filed under `ai_semiconductors`.

The F09 coverage-matrix semis row (`MARKET_ONTOLOGY_F09_COMMODITY_COVERAGE_MATRIX_2026-09-02.csv` line 44) records `NO-COVERAGE` / `NONE` because its grep was scoped to `engine/commodity_*.py` and `engine/strategic_reserves.py`. Widening the scope by two directories finds a live, config-driven Census HS6 import apparatus (`collectors/census_trade.py`, `config/trade_flow_codes.yml`, `engine/theme_trade_flows.py`) whose artifact `data/trade_flows/` is absent. That is `PUBLIC-BUILDABLE-DARK`, not "no sources exist".

---

## 3. The census table

<!-- census-table:start -->

| candidate_source | sub_domain | what_it_would_cover | public_or_commercial | integrated_today | licence_required | verification_method | provenance | status | verified_negative_statement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| US Census Bureau International Trade API (HS6 monthly imports) | ai_semiconductors | Distribution layer: US monthly import value of processors, controllers, memory and analog ICs (HS 854231, 854232, 854233), including GPUs and HBM. | PUBLIC | collectors/census_trade.py:10 | US-Government-work / free-key-required | Read collectors/census_trade.py:10-13 (API key REQUIRED; keyless call returns 302) and config/trade_flow_codes.yml:126,137,148; git ls-tree HEAD data/trade_flows is empty, so the parquet artifact is missing and the required CENSUS_API_KEY is not claimed present. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE-DARK | n/a |
| US Census Bureau International Trade API (HS6 monthly imports) | semicap_equipment | Distribution layer: US monthly import value of lithography, deposition/etch/CMP, and assembly/test equipment (HS 848620, 848630, 848640). | PUBLIC | collectors/census_trade.py:117 | US-Government-work / free-key-required | Read collectors/census_trade.py:117 (loads config/trade_flow_codes.yml) and config/trade_flow_codes.yml:159,170,179; git ls-tree HEAD data/trade_flows is empty, so the parquet artifact is missing. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE-DARK | n/a |
| US Census Bureau International Trade API (HS6 monthly imports) | rare_earth_critical_min | Distribution layer: US monthly import value of rare-earth metals, cerium compounds, other rare-earth compounds, and NdFeB/SmCo magnets (HS 280530, 284610, 284690, 850511). | PUBLIC | collectors/census_trade.py:103 | US-Government-work / free-key-required | Read collectors/census_trade.py:103 (_CODES_PATH) and config/trade_flow_codes.yml:39,49,58,68; git ls-tree HEAD data/trade_flows is empty, so the parquet artifact is missing. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE-DARK | n/a |
| US Census Bureau International Trade API (HS6 monthly imports) | nuclear_power | Distribution layer: US monthly import value of natural uranium and uranium enriched in U-235 (HS 284410, 284430). | PUBLIC | collectors/census_trade.py:93 | US-Government-work / free-key-required | Read collectors/census_trade.py:93 (_COMM_LVL = HS6) and config/trade_flow_codes.yml:230,241; git ls-tree HEAD data/trade_flows is empty, so the parquet artifact is missing. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE-DARK | n/a |
| Electronic-grade polysilicon HS 280461 (filed under ai_semiconductors) | ai_semiconductors | Raw / refining feedstock: electronic-grade polysilicon used for semiconductor crystal growth. The config lists this code under solar; this census files it under ai_semiconductors as semiconductor feedstock. | PUBLIC | config/trade_flow_codes.yml:114 | US-Government-work / free-key-required | Read config/trade_flow_codes.yml:114-123; producer is collectors/census_trade.py:10; git ls-tree HEAD data/trade_flows is empty. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE-DARK | n/a |
| US Federal Register API (BIS Entity List and advanced-computing export controls) | ai_semiconductors | Chokepoint layer: Bureau of Industry and Security Entity List and advanced-computing export-control events that rewire who may receive advanced semiconductors. This is a policy chokepoint, not a physical quantity. | PUBLIC | collectors/federal_register.py:1 | US-Government-work / keyless | Read collectors/federal_register.py:1-2 (keyless, no auth required) and engine/policy_calendar.py:53 (title term advanced computing); git ls-tree HEAD lists data/federal_register/documents.parquet. This sparse checkout omits data/, so the parquet was not opened here. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE | n/a |
| US Federal Register API (BIS semiconductor-manufacturing export controls) | semicap_equipment | Chokepoint layer: export-control notices whose titles match semiconductor manufacturing, plus the Entity List sub-signal wired to semicap_equipment. This is a policy chokepoint, not a physical quantity. | PUBLIC | engine/policy_calendar.py:54 | US-Government-work / keyless | Read engine/policy_calendar.py:54 and engine/policy_calendar.py:59 (semicap_equipment is in _ENTITY_LIST_THEMES); git ls-tree HEAD lists data/federal_register/documents.parquet. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE | n/a |
| US Federal Register API (BIS Entity List sub-signal for rare earths) | rare_earth_critical_min | Chokepoint layer: Entity List events wired to rare_earth_critical_min. This is a policy chokepoint, not a physical quantity. | PUBLIC | engine/policy_calendar.py:59 | US-Government-work / keyless | Read engine/policy_calendar.py:59 (rare_earth_critical_min is in _ENTITY_LIST_THEMES); git ls-tree HEAD lists data/federal_register/documents.parquet. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE | n/a |
| China AI-semis confirmer (SMH, SOXX, TSM 4-week momentum) | ai_semiconductors | End-market layer as an equity-price proxy only: 4-week log-momentum of SMH, SOXX and TSM into China AI-supply baskets. This is not a physical quantity and does not fill the physical-flow gap. | PUBLIC | engine/cn_ai_semis_confirmer.py:9 | Delayed public-market price history (Yahoo) | Read engine/cn_ai_semis_confirmer.py:9-10 (DISPLAY + JSON CHIP ONLY); git ls-tree HEAD lists data/yahoo/SMH.parquet, SOXX.parquet and TSM.parquet. This sparse checkout omits data/, so the parquets were not opened here. | KNOWN-FROM-REPO | PUBLIC-BUILDABLE | n/a |
| USGS Mineral Commodity Summaries / National Minerals Information Center collector (absent from this repository) | rare_earth_critical_min | Raw layer: mine production and reserves for rare earths, lithium, cobalt and gallium. | PUBLIC | NO | US-Government-work | git ls-tree -r --name-only HEAD collectors with a case-insensitive match on usgs, mineral commodity, or nmic returned 0 paths; ls collectors with the same usgs match returned no file (245 files listed by ls; 250 collector paths in git ls-tree). | KNOWN-FROM-REPO | VERIFIED-NEGATIVE | git ls-tree -r --name-only HEAD collectors \| rg -i 'usgs\|mineral.?commodity\|nmic' returned 0 paths; ls collectors \| rg -i usgs returned no match (245 files listed by ls; 250 collector paths in git ls-tree). |
| EIA Uranium Marketing Annual Report collector (absent from this repository) | nuclear_power | Raw layer: US uranium purchases, inventories and origin of deliveries. | PUBLIC | NO | US-Government-work | Read collectors/eia.py:1-8 (petroleum Weekly Petroleum Status Report only); rg -n uranium collectors/eia.py returned 0 matches; git ls-tree -r --name-only HEAD collectors with a uranium filename match returned 0 collector filenames. | KNOWN-FROM-REPO | VERIFIED-NEGATIVE | Read collectors/eia.py:1-8 (EIA petroleum Weekly Petroleum Status Report only); rg -n uranium collectors/eia.py returned 0 matches; git ls-tree -r --name-only HEAD collectors \| rg -i uranium returned 0 collector filenames. |
| SEMI World Fab Forecast | semicap_equipment | Fabrication layer: planned fab equipment installations and capacity additions by region and process node. | COMMERCIAL | NO | SEMI paid-membership commercial data licence; redistribution restricted | NOT-VERIFIED-NO-NETWORK | KNOWN-FROM-MODEL-KNOWLEDGE | COMMERCIAL-GATE | n/a |
| TechInsights semiconductor manufacturing cost and process data | ai_semiconductors | Fabrication layer: process-node manufacturing cost and die-level production data. | COMMERCIAL | NO | TechInsights commercial subscription licence; no redistribution | NOT-VERIFIED-NO-NETWORK | KNOWN-FROM-MODEL-KNOWLEDGE | COMMERCIAL-GATE | n/a |
| Fastmarkets rare-earth oxide and magnet price assessments | rare_earth_critical_min | Refining layer: assessed prices for separated rare-earth oxides and magnet alloys. | COMMERCIAL | NO | Fastmarkets commercial price-assessment licence; redistribution restricted | NOT-VERIFIED-NO-NETWORK | KNOWN-FROM-MODEL-KNOWLEDGE | COMMERCIAL-GATE | n/a |
| UxC uranium price indicators (spot and term) | nuclear_power | Distribution / end-market layer: spot and term uranium price assessments, not physical volumes. | COMMERCIAL | NO | UxC commercial subscription licence; redistribution restricted | NOT-VERIFIED-NO-NETWORK | KNOWN-FROM-MODEL-KNOWLEDGE | COMMERCIAL-GATE | n/a |
| Solar photovoltaic cells and modules (adjacent listing) | solar | Out of scope of this packet: would be owned by a later F09 solar physical-flow census. config/trade_flow_codes.yml already curates HS 854142 and 854143. | PUBLIC | config/trade_flow_codes.yml:93 | US-Government-work / free-key-required (Census HS6 already curated; not further assessed) | Read config/trade_flow_codes.yml:93 (theme_id solar). | KNOWN-FROM-REPO | OUT-OF-SCOPE-THIS-PACKET | n/a |
| Grid electrification equipment (adjacent listing) | grid_electrification | Out of scope of this packet: would be owned by a later F09 grid-electrification physical-flow census. config/trade_flow_codes.yml curates four HS6 codes from line 189. | PUBLIC | config/trade_flow_codes.yml:192 | US-Government-work / free-key-required (Census HS6 already curated; not further assessed) | Read config/trade_flow_codes.yml:192 (theme_id grid_electrification). | KNOWN-FROM-REPO | OUT-OF-SCOPE-THIS-PACKET | n/a |

<!-- census-table:end -->

---

## 4. Per-row reasoning

1. **US Census Bureau International Trade API — `ai_semiconductors`.** `collectors/census_trade.py:10-13` records that the International Trade API requires a key (a keyless call returns 302 to missing_key.html). `_COMM_LVL = "HS6"` is pinned at `:93`. `config/trade_flow_codes.yml:126,137,148` already curates 854231 / 854232 / 854233. The consumer `engine/theme_trade_flows.py:3-6` is display/confluence context only (`may_rank=false`) and reads `data/trade_flows/imports_monthly.parquet` at `:29`. That directory is not in this checkout and is not in `git ls-tree HEAD`. Status is therefore `PUBLIC-BUILDABLE-DARK`: the producer and the config exist; the artifact and the required key do not.

2. **US Census Bureau International Trade API — `semicap_equipment`.** Same producer. Config anchors `:159,:170,:179` (848620 lithography, 848630 deposition/etch/CMP, 848640 assembly/test). Same missing artifact. Same dark status.

3. **US Census Bureau International Trade API — `rare_earth_critical_min`.** Same producer. Config anchors `:39,:49,:58,:68` (280530 metals, 284610 cerium compounds, 284690 other rare-earth compounds, 850511 NdFeB/SmCo magnets). Same missing artifact. Same dark status.

4. **US Census Bureau International Trade API — `nuclear_power`.** Same producer. Config anchors `:230,:241` (284410 natural uranium, 284430 enriched U-235). Same missing artifact. Same dark status.

5. **Electronic-grade polysilicon HS 280461.** `config/trade_flow_codes.yml:114-123` labels this code silicon / polysilicon (electronic grade) and sets `theme_id: solar`, while the rationale says it is the upstream material for both solar wafers and semiconductor crystal growth. Seat ruling D1 files it under `ai_semiconductors`. It is still Census HS6, still dark.

6. **US Federal Register API — `ai_semiconductors` chokepoint.** `collectors/federal_register.py:1-2` is keyless. `engine/policy_calendar.py:53` is the title term "advanced computing" (commented as semiconductor-specific). `_compute_entity_list_events` is defined at `:299` and called at `:192`. `git ls-tree HEAD` lists `data/federal_register/documents.parquet`, so the artifact is tracked even though this sparse checkout omits `data/`. This names a policy chokepoint, not tonnes or units.

7. **US Federal Register API — `semicap_equipment` chokepoint.** `engine/policy_calendar.py:54` is the title term "semiconductor manufacturing". `:59` includes `semicap_equipment` in `_ENTITY_LIST_THEMES`. Same tracked Federal Register artifact.

8. **US Federal Register API — `rare_earth_critical_min` chokepoint.** `engine/policy_calendar.py:59` includes `rare_earth_critical_min` in `_ENTITY_LIST_THEMES`. Same tracked artifact. Same policy-not-quantity limit.

9. **China AI-semis confirmer.** `engine/cn_ai_semis_confirmer.py:9-10` is display and JSON chip only. It reads SMH / SOXX / TSM 4-week momentum. `git ls-tree HEAD` lists the three Yahoo parquets. This is an equity-price proxy. A reviewer who treats it as physical-flow coverage will understate the gap.

10. **USGS Mineral Commodity Summaries collector (absent).** USGS is the usual public production and reserves series for rare earths, lithium, cobalt and gallium. This repository has no collector for it. The searches that established the absence are in column 10. This is a collector gap, not a claim that USGS as a public body does not exist.

11. **EIA Uranium Marketing Annual Report collector (absent).** `collectors/eia.py:1-8` is the Weekly Petroleum Status Report only. A line search for `uranium` in that file returned 0 matches. No collector filename under `collectors/` matches uranium. The oil physical-balance precedent in `engine/commodity_supply_context.py` does not extend to the uranium fuel cycle.

12. **SEMI World Fab Forecast.** Named from model knowledge as the usual commercial fab-capacity and equipment-install series. Not verified live. Cannot be `PUBLIC-BUILDABLE`. A Chairman rights review is required before any store write (`docs/QUAL_DATA_COMPLIANCE.md:87-100`).

13. **TechInsights semiconductor manufacturing cost and process data.** Named from model knowledge as a commercial fabrication-layer source. Not verified live. Same Chairman-act ceiling.

14. **Fastmarkets rare-earth oxide and magnet price assessments.** Named from model knowledge as a commercial refining-layer price source. Not verified live. Same Chairman-act ceiling. This is a price assessment, not a tonnes-produced series.

15. **UxC uranium price indicators.** Named from model knowledge as a commercial uranium price source. Not verified live. Same Chairman-act ceiling. This is a price assessment, not a physical-volume series.

16. **Solar (adjacent).** `config/trade_flow_codes.yml:93` already curates photovoltaic-cell HS6. This packet does not census it. The owning row would be a later F09 solar physical-flow census.

17. **Grid electrification (adjacent).** `config/trade_flow_codes.yml:192` already curates the first of four grid HS6 codes. This packet does not census it. The owning row would be a later F09 grid-electrification physical-flow census.

---

## 5. What this changes for `MO-PAID-040` and `MO-DELTA-027`

`MO-PAID-040`'s acceptance test is "one commodity documents a >=3-layer sourced chain" on the vocabulary raw → chokepoint → refining → fabrication → distribution → end-market. The census does not build that chain. It names what would make the chain buildable.

For **`MO-PAID-040`**: a public physical chain of three or more layers is **not nameable**. What is nameable, by layer:

- **raw** — no in-repo public collector. USGS (rare earths) and EIA uranium marketing are `VERIFIED-NEGATIVE` as collectors in this repository.
- **chokepoint** — Federal Register / BIS Entity List and export-control title terms are `PUBLIC-BUILDABLE` (policy events, not physical quantities).
- **refining** — no public in-repo source; Fastmarkets is `COMMERCIAL-GATE`.
- **fabrication** — no public in-repo capacity series; SEMI World Fab Forecast and TechInsights are `COMMERCIAL-GATE`. Census HS6 equipment imports are the distribution of tools, not fab output.
- **distribution** — US Census HS6 monthly imports are `PUBLIC-BUILDABLE-DARK` (producer and config live; `data/trade_flows/` and `CENSUS_API_KEY` missing).
- **end-market** — the China AI-semis confirmer is `PUBLIC-BUILDABLE` as an equity-price proxy only.

The gate therefore stays a named DEFER: the distribution layer is now a named public-dark source, the chokepoint layer is a named public policy source, and the raw / refining / fabrication physical layers are either collector-absent or commercial. Two public layers plus commercial remainder is not "one commodity documents a >=3-layer sourced chain" under a public-source reading.

```
PROPOSED — not applied by this packet (see D5)
MO-PAID-040 next_bounded_child:
DEFER — distribution layer named as US Census HS6 imports (PUBLIC-BUILDABLE-DARK: collectors/census_trade.py; data/trade_flows absent; CENSUS_API_KEY required); chokepoint layer named as Federal Register / BIS Entity List (PUBLIC-BUILDABLE: collectors/federal_register.py); raw production collector VERIFIED-NEGATIVE (no USGS collector; collectors/eia.py is petroleum-only); refining and fabrication remain COMMERCIAL-GATE (Fastmarkets, SEMI World Fab Forecast, TechInsights) pending a Chairman rights review. A >=3-layer public physical chain is not nameable. See research/market_intelligence_productization/MARKET_ONTOLOGY_F09_SEMIS_SOURCE_CENSUS_2026-09-09.md.
```

For **`MO-DELTA-027`**: the row's gate is "DEFER — flow-source first" and its `source_rights` cell said the cross-layer physical-flow source was not identified. The flow source for the distribution layer is now identified (Census HS6, dark). A cross-layer public chain is still not nameable, so the row stays DEFER, with the named source pointed at this census.

```
PROPOSED — not applied by this packet (see D5)
MO-DELTA-027 next_bounded_child:
DEFER — flow-source now named for the distribution layer: US Census HS6 imports (PUBLIC-BUILDABLE-DARK; collectors/census_trade.py + config/trade_flow_codes.yml + engine/theme_trade_flows.py; data/trade_flows absent). A cross-layer public physical chain is still not nameable. See research/market_intelligence_productization/MARKET_ONTOLOGY_F09_SEMIS_SOURCE_CENSUS_2026-09-09.md and MO-PAID-040.
```

This packet does not edit the F00C ledger CSV. A records packet that owns that file may apply the two replacement cells above.

---

## 6. What is still absent

- There is no USGS Mineral Commodity Summaries / National Minerals Information Center collector in this repository (`git ls-tree` over `collectors/` for usgs / mineral commodity / nmic returned 0 paths). The raw production and reserves layer for rare earths, lithium, cobalt and gallium has no in-repo public producer.
- There is no EIA Uranium Marketing Annual Report collector. `collectors/eia.py` is the petroleum Weekly Petroleum Status Report only (`rg -n uranium collectors/eia.py` returned 0 matches). The raw uranium layer has no in-repo public producer.
- `data/trade_flows/` is absent from git and from this checkout, and `CENSUS_API_KEY` is required, so the Census HS6 distribution layer is code-live and artifact-dark.
- No public in-repo series names fab capacity, process-node output, or rare-earth oxide separation volumes. Those layers are commercial-gate candidates, not public-buildable ones.
- No row in this census was verified live. Every `KNOWN-FROM-MODEL-KNOWLEDGE` URL or vendor name is an unverified assertion.

---

## 7. Rights posture

This packet has no Chairman grant. The F01 census shape is copied; its authority is not. Each `COMMERCIAL-GATE` row is a request for a Chairman act, not a clearance. `docs/QUAL_DATA_COMPLIANCE.md:87-100` requires a written compliance review recorded as a dated Change Log entry before any new source enters the store. None of the rows below is an expert network (`§2.1`, `§2.2`), a card/transaction panel (`§2.3`), or a ToS-adverse scrape (`§2.4`). Each would still have to clear `§3`.

**SEMI World Fab Forecast.** Vendor: SEMI. Licence class: paid-membership commercial data licence; redistribution restricted. Clause to clear: `docs/QUAL_DATA_COMPLIANCE.md:87-100` (standing rule: written §5 Change Log review before any store write). This census names it; it does not clear it.

**TechInsights semiconductor manufacturing cost and process data.** Vendor: TechInsights. Licence class: commercial subscription licence; no redistribution. Clause to clear: `docs/QUAL_DATA_COMPLIANCE.md:87-100`. This census names it; it does not clear it.

**Fastmarkets rare-earth oxide and magnet price assessments.** Vendor: Fastmarkets. Licence class: commercial price-assessment licence; redistribution restricted. Clause to clear: `docs/QUAL_DATA_COMPLIANCE.md:87-100`. This census names it; it does not clear it.

**UxC uranium price indicators (spot and term).** Vendor: UxC. Licence class: commercial subscription licence; redistribution restricted. Clause to clear: `docs/QUAL_DATA_COMPLIANCE.md:87-100`. This census names it; it does not clear it.

No sentence in this document is a ruling that a source is cleared, approved, or may be used.
