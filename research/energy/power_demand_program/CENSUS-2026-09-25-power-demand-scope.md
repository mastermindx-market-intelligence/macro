---
title: Power-Demand vertical scope census
date: 2026-09-25
lane: ene_pd_scope_census
main: daa6a2e1aae0a0e84d702c8824b35a58c49b750a
pr7870: 6cd958e92b259f7221690547e7076f4a0de4ed33
pr7791: 68e815d88fc8123a67167ae27b213078fe5339f7
status: census (read-only, not a design)
---

# Power-Demand vertical scope census

This record is a fact census. It selects nothing, changes no identity, proposes no vocabulary, and gives the Energy seat no product recommendation.

## Q1 — Identity

### Candidate: `data_center_power`

- Slug: `data_center_power`.
- `theme_node_id`: `theme:data_center_power`, defined at `config/theme_crosswalk.yml:102-113@daa6a2e1`.
- EN name: “Data Center Power & Cooling”; ZH name: “数据中心电力与冷却”, at `config/theme_crosswalk.yml:102-104@daa6a2e1`.
- Primary basket: `data_center_power` at `config/theme_crosswalk.yml:105-108@daa6a2e1`.
- Supplemental basket: `ai_neoclouds`. The machine-readable field is `basket_ids`, not `supplemental_basket_ids`; the stated relation is prose: “`ai_neoclouds` captures the hyperscaler demand driver” at `config/theme_crosswalk.yml:107-118@daa6a2e1`. This confirms supplemental/demand-driver intent but not an independently named typed relation, so the typed relation is `UNKNOWN`.
- Other definition sites: `config/theme_pathways.yml:246-273@daa6a2e1`; `config/theme_thesis_registry.yml:322-390@daa6a2e1`.

### Candidate: `grid_electrification`

- Slug: `grid_electrification`.
- `theme_node_id`: `theme:grid_electrification`, defined at `config/theme_crosswalk.yml:140-155@daa6a2e1`.
- EN name: “Grid & Electrification”; ZH name: “电网与电气化”, at `config/theme_crosswalk.yml:140-142@daa6a2e1`.
- Primary basket: `power_grid` at `config/theme_crosswalk.yml:143-146@daa6a2e1`.
- Supplemental basket: none in the crosswalk. `UNKNOWN — exact searches run: git grep -n data_center_power origin/main -- config engine contracts; git grep -n grid_electrification origin/main -- config engine contracts; git ls-tree -r --name-only origin/main | rg -i "(theme|basket).*(registry|pathway|crosswalk|thesis|membership)|((registry|membership).*(theme|basket))"`. The crosswalk's only basket id is `power_grid`.
- Other definition sites: `config/theme_pathways.yml:389-415@daa6a2e1`; `config/theme_thesis_registry.yml:702-775@daa6a2e1`.

### Lead ruled out as an anchor: `power_grid`

`power_grid` is a basket, not a canonical theme row. The canonical theme is `grid_electrification`, and the crosswalk names `power_grid` as that theme's primary basket at `config/theme_crosswalk.yml:140-146@daa6a2e1`. The same distinction is explicit in Energy: “`theme:grid_electrification` — primary basket `power_grid`” at #7791 R6 checkpoint line 176. No `theme:power_grid` row was found. Searches: `git grep -n power_grid origin/main -- config engine contracts`; `rg -n '^  - id: power_grid$' config/theme_crosswalk.yml`; filename census above.

### Main versus #7870 crosswalk

The crosswalk does not differ between `origin/main` and Semiconductor B #7870:

- Both tree entries are blob `782dbc519b7bb2d446af91c66c6fb9248722a8b9`.
- `git diff --stat origin/main refs/remotes/pr7870 -- config/theme_crosswalk.yml` is empty.
- SHA-256 of both rendered blobs is `43450b71f8663c4625d34940cdf15b5cab37eaa52061e118686f89c0d80ae909`.
- `git diff --stat origin/main refs/remotes/pr7870 -- data/baskets/membership.json` is also empty; both use blob `c5b838d59fad8115d40cd369410846e9aaf5ec11`.
- `engine/theme_graph/identity.py` is likewise identical on both refs, blob `c27fb161bf401ca05387c4f07ac8e0220b801b2a`.

The identity owner says `theme:<id>` is canonical and basket ids are suite-qualified: `engine/theme_graph/identity.py:141-161@daa6a2e1`.

## Q2 — Baskets and companies

All roles below mean membership in the named basket at the cited lines. `primary` means the basket is a Power-Demand candidate's primary basket; `supplemental` means the crosswalk/design says the basket supplements that candidate. The source membership document does not encode primary/supplemental itself.

### Primary basket `data_center_power`

Current members are defined in `data/baskets/membership.json:3443-3518@daa6a2e1`; basket metadata and thesis are at lines 3443-3460 and 3518-3526.

| Company id | Role | US-listed / SEC filing evidence |
|---|---|---|
| VRT / Vertiv | primary | `SEC:US-XNYS-VRT`, `RESOLVED`, CIK `0001674101`; CIK-map title “Vertiv Holdings Co” |
| ETN / Eaton | primary | `SEC:US-XNYS-ETN`, `RESOLVED`, CIK `0001551182`; “Eaton Corp plc” |
| POWL / Powell Industries | primary | `SEC:US-XNAS-POWL`, `RESOLVED`, CIK `0000080420`; “POWELL INDUSTRIES INC” |
| NXT / Nextpower | primary | `SEC:US-XNAS-NXT`, `RESOLVED`, CIK `0001852131`; “Nextpower Inc.”; membership rationale names CIK 1852131 |
| AEIS / Advanced Energy | primary | `SEC:US-XNAS-AEIS`, `RESOLVED`, CIK `0000927003`; “ADVANCED ENERGY INDUSTRIES INC” |
| NVT / nVent Electric | primary | `SEC:US-XNYS-NVT`, `RESOLVED`, CIK `0001720635`; “nVent Electric plc” |
| HUBB / Hubbell | primary | `SEC:US-XNYS-HUBB`, `RESOLVED`, CIK `0000048898`; “HUBBELL INC” |
| GEV / GE Vernova | primary | `SEC:US-XNYS-GEV`, `RESOLVED`, CIK `0001996810`; “GE Vernova Inc.” |

Membership file: `data/baskets/membership.json`. Identity evidence: `data/reference/security_master.parquet` blob `0a5cfdcb0b84f90049bcac9318012ef94df628c2` (security id, US MIC, `RESOLVED`, CIK) and `data/symbol_directory/cik_map/2026-09-21.parquet` blob `dd8763feefb7a2899a0d7294c6b254a823d3a49f` (ticker, CIK, registrant title). The symbol-directory metadata says it combines Nasdaq Trader listings with SEC `company_tickers.json`: `config/synapse.yml:8033-8041@daa6a2e1`. “CIK/RESOLVED” is repo evidence of an SEC registrant; no live SEC filing catalogue was queried.

### Supplemental basket `ai_neoclouds`

Current members (removed rows excluded) are defined at `data/baskets/membership.json:2700-2809@daa6a2e1`; removal dates are printed in the same table:

| Company id | Role | US-listed / SEC filing evidence |
|---|---|---|
| CRWV / CoreWeave | supplemental demand-driver | `SEC:US-XNAS-CRWV`, `RESOLVED`, CIK `0001769628`; “CoreWeave, Inc.” |
| NBIS / Nebius | supplemental demand-driver | `SEC:US-XNAS-NBIS`, `RESOLVED`, CIK `0001513845`; “Nebius Group N.V.” |
| CORZ / Core Scientific | supplemental demand-driver | `SEC:US-XNAS-CORZ`, `RESOLVED`, CIK `0001839341`; “Core Scientific, Inc./tx” |
| IREN / IREN | supplemental demand-driver | `SEC:US-XNAS-IREN`, `RESOLVED`, CIK `0001878848`; “IREN Ltd” |
| HUT / Hut 8 | supplemental demand-driver | `SEC:US-XNAS-HUT`, `RESOLVED`, CIK `0001964789`; “Hut 8 Corp.” |
| APLD / Applied Digital | supplemental demand-driver | `SEC:US-XNAS-APLD`, `RESOLVED`, CIK `0001144879`; “Applied Digital Corp.” |
| WULF / TeraWulf | supplemental demand-driver | `SEC:US-XNAS-WULF`, `RESOLVED`, CIK `0001083301`; “TERAWULF INC.” |
| CIFR / Cipher Mining | supplemental demand-driver | `SEC:US-XNAS-CIFR`, `RESOLVED`, CIK `0001819989`; “Cipher Digital Inc.” |
| BTDR / Bitdeer | supplemental demand-driver | `SEC:US-XNAS-BTDR`, `RESOLVED`, CIK `0001899123`; “Bitdeer Technologies Group” |
| RIOT / Riot Platforms | supplemental demand-driver | `SEC:US-XNAS-RIOT`, `RESOLVED`, CIK `0001167419`; “Riot Platforms, Inc.” |
| CLSK / CleanSpark | supplemental demand-driver, removed 2026-07-06 | `SEC:US-XNAS-CLSK`, `RESOLVED`, CIK `0000827876`; “CLEANSPARK, INC.” |
| MARA / MARA Holdings | supplemental demand-driver, removed 2026-07-04 | `SEC:US-XNAS-MARA`, `RESOLVED`, CIK `0001507605`; “MARA Holdings, Inc.” |
| GLXY / Galaxy Digital | supplemental demand-driver, removed 2026-07-08 | `SEC:US-XNAS-GLXY`, `RESOLVED`, CIK `0001859392`; “Galaxy Digital Inc.” |

All current and removed member rows above resolve to `issuer_state=RESOLVED` and a ten-digit issuer CIK in the committed security master.

### Primary basket `power_grid`

Current members (all rows have `removed: null`) are defined at `data/baskets/membership.json:662-843@daa6a2e1`; basket metadata/changelog is at lines 662-885.

| Company id | Role | US-listed / SEC filing evidence |
|---|---|---|
| GEV / GE Vernova | primary for `grid_electrification` | `SEC:US-XNYS-GEV`, `RESOLVED`, CIK `0001996810` |
| ETN / Eaton | primary | `SEC:US-XNYS-ETN`, `RESOLVED`, CIK `0001551182` |
| VRT / Vertiv | primary | `SEC:US-XNYS-VRT`, `RESOLVED`, CIK `0001674101` |
| PWR / Quanta Services | primary | `SEC:US-XNYS-PWR`, `RESOLVED`, CIK `0001050915` |
| NEE / NextEra Energy | primary | `SEC:US-XNYS-NEE`, `RESOLVED`, CIK `0000753308` |
| CEG / Constellation Energy | primary | `SEC:US-XNAS-CEG`, `RESOLVED`, CIK `0001868275` |
| VST / Vistra | primary | `SEC:US-XNYS-VST`, `RESOLVED`, CIK `0001692819` |
| NRG / NRG Energy | primary | `SEC:US-XNYS-NRG`, `RESOLVED`, CIK `0001013871` |
| PCG / PG&E | primary | `SEC:US-XNYS-PCG`, `RESOLVED`, CIK `0001004980` |
| D / Dominion Energy | primary | `SEC:US-XNYS-D`, `RESOLVED`, CIK `0000715957` |
| EME / EMCOR | primary | `SEC:US-XNYS-EME`, `RESOLVED`, CIK `0000105634` |
| FIX / Comfort Systems | primary | `SEC:US-XNYS-FIX`, `RESOLVED`, CIK `0001035983` |
| TLN / Talen Energy | primary | `SEC:US-XNAS-TLN`, `RESOLVED`, CIK `0001622536` |
| OKLO / Oklo | primary | `SEC:US-XNYS-OKLO`, `RESOLVED`, CIK `0001849056` |
| SMR / NuScale Power | primary | `SEC:US-XNYS-SMR`, `RESOLVED`, CIK `0001822966` |
| LEU / Centrus Energy | primary | `SEC:US-XNYS-LEU`, `RESOLVED`, CIK `0001065059` |
| DUK / Duke Energy | primary | `SEC:US-XNYS-DUK`, `RESOLVED`, CIK `0001326160` |
| SO / Southern Company | primary | `SEC:US-XNYS-SO`, `RESOLVED`, CIK `0000092122` |
| AEP / American Electric Power | primary | `SEC:US-XNAS-AEP`, `RESOLVED`, CIK `0000004904` |
| SRE / Sempra | primary | `SEC:US-XNYS-SRE`, `RESOLVED`, CIK `0001032208` |
| HUBB / Hubbell | primary | `SEC:US-XNYS-HUBB`, `RESOLVED`, CIK `0000048898` |
| GNRC / Generac | primary | `SEC:US-XNYS-GNRC`, `RESOLVED`, CIK `0001474735` |
| BWXT / BWX Technologies | primary | `SEC:US-XNYS-BWXT`, `RESOLVED`, CIK `0001486957` |
| POWL / Powell Industries | primary | `SEC:US-XNAS-POWL`, `RESOLVED`, CIK `0000080420` |

No `power_grid` row is removed. The basket itself is generated/electrical equipment/power sellers tied to AI/electrification load growth: `data/baskets/membership.json:845-885@daa6a2e1`.

## Q3 — What the Energy design already decided for Power-Demand

### Packet `f628167227613175cc3ede088f40423add7252fb`

> “Second expansion foundation: **Power-Demand Value Capture**.” — packet lines 130-134.

> “Reuse the same architecture in this order according to leverage/current source readiness: - Power-Demand Value Capture from R3; - hydrocarbon/contract economics from R2; - solar/wind manufacturer/developer/asset-owner economics; - storage integrator versus storage owner; - hydrogen/fuel cell/geothermal/renewable fuels/CCUS/waste-to-energy; - global expectation/valuation overlays from R5; - sector-level Energy projection through accepted sector-dossier owner.” — packet lines 625-636.

> “Energy demand growth does not identify the profit pool.” — packet line 642.

> “R3 power-demand business-model research” and “current decision that Nuclear is first Energy proof and Power Demand is the next expansion foundation” must not be redone. — packet lines 722-734.

### Design `d6dac80bead5a028da8d757b419c896b1b8437ed`

> “The next expansion is **Power-Demand Value Capture** across `data_center_power`, `grid_electrification`, the Energy sector and connected Utilities/Industrials businesses. It reuses the same dossier grammar rather than launching a separate product.” — design lines 38-40.

> “The standard Energy bridge is: `demand/market change → commercial exposure → unit economics → operating contribution → required capital/financing → ownership/claims → attributable cash per continuing share`.” — design lines 164-170.

> “regulated utility: approved eligible capital, recovery timing, allowed/earned returns, financing and share count” and “merchant generator: regional power/fuel exposure, hedge vintage, availability, capacity/retail/customer obligations” are owner-bound mechanisms. — design lines 172-181.

> Counterevidence must include “demand forecast revised lower”, “backlog is contingent/unfunded”, “contracted MW are existing output, not new supply”, “technical milestone belongs to a test asset, not commercial operation”, and “improved contract duration requires materially more capital”. — design lines 208-222.

> “Power-demand value capture: Vistra/Duke/GE Vernova/Quanta/Clearway/Talen/Eaton and connected gas/infrastructure cases.” — design lines 512-518.

### Plan `f7dc93621532b06e2478f90ef3876d6c31236242`

> “After Nuclear first vertical acceptance: - Hydrocarbon Value Capture from R2; - Power-Demand Value Capture from R3; - Solar/wind manufacturer/developer/asset-owner cases from R4; - Storage integrator/asset owner; - Hydrogen/geothermal/renewable fuels/CCUS; - global expectations/valuation from R5.” — plan lines 437-445.

> “Sector-level Energy projection may consume #7777's accepted sector-dossier interface once live. The theme/company economic-change dossier remains the detail engine. Do not fork the architecture by subtheme.” — plan line 447.

> Task 11 starts only after the first vertical is accepted. — plan lines 491-504.

### Checkpoint `a710755c126fe23a0bad8d57f36f272dfd6f5d9b`

> R3 “Preserve: - demand level versus forecast revision versus actual load; - merchant hedge vintage and customer obligations; - regulated recovery/financing/dilution; - contracted resource/asset ownership; - orders/reservations/RPO/backlog/delivery/cash/service clocks; - capacity price × quantity × calendar; - demand credibility versus business capture versus market expectations.” — checkpoint lines 73-83.

> “Accepted crosswalk identities: - `theme:grid_electrification`: primary basket `power_grid` - `theme:data_center_power`: primary basket `data_center_power`; supplemental demand-driver `ai_neoclouds`.” — checkpoint lines 172-183.

> “Second expansion after first vertical: **Power-Demand Value Capture** across accepted `data_center_power`, `grid_electrification` and connected company roles.” — checkpoint lines 216-218.

The checkpoint's `power_grid` relation is explicitly primary-basket mapping, not an independently verified typed edge. No `power_grid` supplemental relation appears in the four pinned blobs. Exact search run across all four blobs: `power|grid|electrif|utilit|PPA|purchase|interconnect|queue|capac|data.center|capex|turbine|transformer|backlog|demand|milestone|unknown|funded|announc|delivered`.

### #7791 R3 research artifact

The seat asked only the four pinned #7791 blobs for Q3. The R3 artifact is nevertheless the cited source for “Power-Demand from R3”; #7791 carries `research/energy/ENERGY_R3_POWER_DEMAND_EQUITY_DOSSIERS_2026-09-23.md`. It names these Power-Demand business cases at lines 7-19: Vistra merchant generation/retail, Duke regulated investment, Clearway contracted generation, GE Vernova equipment/service, Quanta construction, plus Eaton, Talen, and AEP Ohio focused comparators. It is cited here as source identity, not treated as a fifth pinned blob.

## Q4 — Collisions and ownership

| Owner / surface | Record or PR | Exact overlap | State |
|---|---|---|---|
| Energy Fable CEO / `WS:GMI-THEME-GRAPH` ENE-1 | #7791 and working checkpoint | Owns Energy sequencing and the accepted `data_center_power`, `grid_electrification`, `power_grid`, `ai_neoclouds` scope | #7791 OPEN/DRAFT at head `68e815d8`; ENE-1 in progress; first vertical remains Nuclear, Power-Demand follows |
| Semiconductor B / shared theme-research shell | PR #7870 | Owns the shared assertion, registry, mount, private route family and #7870 snapshot; does not change the candidate crosswalk or basket membership | OPEN/DRAFT, head `6cd958e9`; crosswalk and membership blobs identical to main |
| GMI Theme Graph D2D ontology/membership evidence | PR #7462 | Includes `research/prophet_v4/d2/curation/lithium-storage-2026-09-21/exports/theme_grid_electrification.json` and Theme Graph readers | OPEN/DRAFT, head `31706d73`; exact owner is the incumbent Theme Graph workstream |
| US sector membership reconciliation | PR #7284 | Touches `data/baskets/membership.json`; fetched diff has no `power_grid`, `data_center_power`, or `ai_neoclouds` hunk | OPEN/not draft, head `6ea0763e` |
| GMI Industrials first vertical | WS `GMI-INDUSTRIALS-FIRST-VERTICAL`; #7789 research; #7924 T01 | Shared shell/result-to-cash economics and some connected companies, but no candidate basket membership file and no Power-Demand theme ownership | Workstream active; #7789 OPEN/DRAFT; #7924 OPEN/DRAFT |
| Robotics precedent | #7908 | Owns the five-view Robotics shell pattern used by later verticals, not these identities/memberships | MERGED at head `d259ec08`; #7791-era shell dependency now reflected in current main |
| Prophet flagship fan-out research | #6264 | Search result mentions `data_center_power`/Eaton; its GitHub files list has no matching energy/power/grid file | OPEN/DRAFT, head `5d6fd20e` |
| Theme Intelligence convergence / Lane E | #7453, #7664 | Search surfaced crosswalk/thesis files, but current GitHub files lists show no candidate identity or membership overlap | #7453 OPEN/DRAFT; #7664 OPEN/DRAFT |

No Utilities workstream was found. Searches run: `git ls-tree -r --name-only origin/main agentos/workstreams | rg -i 'utilit|energy|industrial|theme-graph'`; `git grep -n -i -E '\butilit(y|ies)|utilities' origin/main -- agentos/workstreams`. The only Energy workstream hit is ENE-1; Industrials is separate.

`docs/PROJECT_ACTIVE_BUILD_MAP.md` is stale/generated on 2026-08-11 and contains no Power-Demand/grid/electrification/Utilities row; its only “power” hit is unrelated #5340. `docs/ACTIVE_BUILD_MAP.md:40-64@daa6a2e1` lists #7924, #7908, #7870 and other active carriers. `research/DO_NOT_REBUILD.md` returns no row for Power-Demand, data-center power, grid/electrification, Utilities, Energy or the candidate themes; therefore there is no `DNR:<KEY>` to quote.

Open-PR searches were run with GitHub CLI for: `data center power`, `power demand`, `grid`, `utilities`, `electrification`, `GMI Industrials`, `Semiconductors`, the four identity/membership paths, the three slugs, and company terms GE Vernova, Vertiv, Eaton, Duke Energy, Vistra, Quanta Services, Talen Energy. Path searches also surfaced #7870/#7453/#7664 and #7284; company-term searches after Eaton/Vertiv returned no exact company-owner PR.

## Q5 — Shell fit (facts only)

### Shared assertion vocabulary on #7870

From `contracts/theme_graph/curation_assertion.v1.schema.json` blob `ff3928f0c54aa164ef8283d9da45af67e6a0d971`:

- Predicates at lines 118-129: `PRODUCT_CAPABILITY`, `DOCUMENTED_PRODUCT_INCLUSION`, `ANNOUNCED_DEVELOPMENT_AGREEMENT`, `DEPLOYMENT_TARGET`, `REPORTED_DEPLOYMENT`, `OWNERSHIP_EVENT`, `REPORTED_FINANCIAL_MEASURE`, `REPORTED_OPERATING_MEASURE`.
- Statement modes at lines 131-134: `REPORTED_FACT`, `CATALOG_DESCRIPTION`, `ANNOUNCED_ARRANGEMENT`, `FORWARD_TARGET`, `ATTRIBUTED_INTERPRETATION`.

### Five Robotics views and predicate map

From `engine/market_ontology/robotics_theme_research.py:72-73,90-112@daa6a2e1`:

- `composition`: `DOCUMENTED_PRODUCT_INCLUSION`, `PRODUCT_CAPABILITY`
- `manufacturing`: empty set
- `commercial`: `ANNOUNCED_DEVELOPMENT_AGREEMENT`, `DEPLOYMENT_TARGET`, `REPORTED_DEPLOYMENT`, `OWNERSHIP_EVENT`
- `capacity`: `REPORTED_OPERATING_MEASURE`
- `economics`: `REPORTED_FINANCIAL_MEASURE`

The module also states that attributed interpretations never become rows in any view: lines 102-104.

### Existing-predicate fit for Power-Demand evidence named by Q3

This is carriage feasibility only, not a recommendation:

| Evidence kind | Existing predicate | Existing view | Fact / limitation |
|---|---|---|---|
| Power purchase agreement | `ANNOUNCED_DEVELOPMENT_AGREEMENT` | commercial | Announced/commercial grammar exists; no PPA-specific predicate |
| Interconnection queue position | `NO_PREDICATE` | none | Queue position has no exact shared predicate |
| Capacity addition / target | `DEPLOYMENT_TARGET` when a deployment target; `REPORTED_DEPLOYMENT` when already reported deployed | commercial | Forward versus reported modes remain distinct; no generic “capacity addition” predicate |
| Data-center load target | `DEPLOYMENT_TARGET` | commercial | Existing predicate can carry a target, not a realized-load fact |
| Actual load / energization | `REPORTED_DEPLOYMENT` | commercial | Exact observation semantics must remain source-scoped |
| Utility capex plan | `REPORTED_FINANCIAL_MEASURE` | economics | Existing financial predicate can carry a reported measure; approved/recovered/earned distinctions are not predicate-specific |
| Turbine or transformer backlog | `REPORTED_FINANCIAL_MEASURE` for RPO/backlog financial measures, or `REPORTED_OPERATING_MEASURE` for an operating quantity | economics or capacity | No backlog-specific predicate; funded/contingent and reservation/order distinctions must remain in limitations/observation semantics |
| Merchant power/fuel exposure, hedge vintage | `NO_PREDICATE` | none | No hedge-vintage predicate |
| Capacity price × quantity × calendar | `REPORTED_FINANCIAL_MEASURE` or `REPORTED_OPERATING_MEASURE` according to the cited measure | economics or capacity | Existing predicates do not encode the arithmetic; Robotics rows explicitly do not compute totals |
| Orders / reservations / delivery / cash / service clocks | `NO_PREDICATE` | none | One shared predicate cannot carry all clocks; a given reported financial or operating measure may carry one source-scoped observation |
| Demand forecast revision | `NO_PREDICATE` | none | No forecast-revision predicate |
| Regulated recovery / financing / dilution | `REPORTED_FINANCIAL_MEASURE` for an admitted reported measure | economics | No recovery/financing/dilution-specific predicate |
| Contracted resource/asset ownership | `OWNERSHIP_EVENT` | commercial | Existing ownership grammar exists |
| Milestone | `NO_PREDICATE` | none | Current main's nuclear wave explicitly carries `milestone_predicate_unavailable` |

## Q6 — Truth laws

### Ordering and scope

From the #7791 packet:

> “Nuclear is first Energy proof and Power Demand is the next expansion foundation.” — packet line 734.

> “Energy demand growth does not identify the profit pool.” — packet line 642.

> “A backlog can grow while comparable business deteriorates.” — packet line 648.

> “A technical milestone can reduce future uncertainty without creating current revenue.” — packet line 652.

From the #7791 design:

> “Missing steps remain unavailable rather than being guessed.” — design line 170.

> “A large application may identify an opportunity but not establish financing, siting or energization. A security deposit may reduce one counterparty risk without proving the full construction schedule. Actual energization still does not establish that the mature ramp has been achieved.” — #7791 R3 lines 37-43.

> “A peak load estimate should never silently turn into full-time energy consumption. Nor should a procurement commitment automatically become evidence that a building is operating at that level.” — #7791 R3 lines 29-35.

> “Paying an operating plant under a new contract is not the same as adding all of the contracted MW to the grid. Uprates require their own spending, milestones and operational evidence. A signed future contract can have present valuation relevance without being current revenue.” — #7791 R3 lines 99-102.

> “Announced spending immediately treated as approved rate base” is the stated error to prevent. — #7791 R3 lines 53-67.

> “A minimum **billing demand** does not establish that the customer must physically consume that fraction of annual electricity.” — #7791 R3 lines 141-147.

> “A contract can stabilize a unit selling price while leaving production, availability, curtailment or replacement obligations exposed.” — #7791 R3 lines 165-171.

> “A new PPA is not evidence that the old economic burden disappeared without cost.” — #7791 R3 lines 181-185.

> “A customer may reserve a production slot without all terms matching a firm order.” — #7791 R3 lines 209-213.

> “An output run-rate expressed in GW per year is also not the same object as a stock of operating generation measured in GW.” — #7791 R3 lines 209-215.

> “Backlog and RPO do not establish margin.” — #7791 R3 lines 326-337.

> “Distinguish estimated MSA work from obligations and recognized revenue from cash.” — #7791 R3 lines 326-337.

> “MW-day capacity revenue is not energy revenue per MWh.” — #7791 R3 lines 271-285.

> “Rising corporate capacity revenue does not necessarily imply a higher market capacity price.” — #7791 R3 lines 271-281.

> “The requirement is to state the conditions and the comparison baseline, not pretend that no value exists until the first invoice is paid.” — #7791 R3 lines 287-302.

### Explicit null/degraded truth laws

From the packet:

> “Unknown never becomes zero. Unavailable never becomes false.” — packet lines 525-549.

From the design:

> The dossier must distinguish “unknown versus zero”, “present operations versus future target”, “contingent versus funded”, and related states. — design lines 349-366.

> “A conflict never disappears because an LLM prefers one narrative.” — design line 366.

> **ENE-05**: “Unknown exposure percentage remains unknown.” — design line 437.

> **ENE-06**: “Supplemental basket relation does not become reverse primary-theme membership.” — design line 438.

> **ENE-08**: “Contract index, formula, option holder, start/expiry and volume scope remain explicit.” — design line 440.

> **ENE-09**: “Future contract/capacity does not become current delivery/revenue.” — design line 441.

> **ENE-10**: “Orders, reservations, RPO/backlog, delivery, revenue, cash and service are separate clocks.” — design line 442.

> **ENE-16**: “Customer advances/contract liabilities are not profit.” — design line 448.

> **ENE-22**: “Technical/design/test milestone does not become commercial operation.” — design line 454.

> **ENE-46**: “Missing/partial/restricted/degraded states are explicit and visually distinct.” — design line 478.

> **ENE-53**: “Existing basket membership/weights remain unchanged.” — design line 485.

> **ENE-76**: “Fable and workers must not redo R1–R5 foundational research.” — design line 508.

### Operation directive on current main

From `agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md@daa6a2e1`:

> “Contingent backlog is never summed and never labelled funded. An equity-method investee is never consolidated. A target whose window has passed stays a retrospective target. Rights fail closed through B's shared resolver. Every authority flag is false.” — line 240.

> “The five views and the predicate-to-view map are identical to Robotics' (the manufacturing view stays structurally empty).” — line 238.

> “A milestone exists only inside the limitations of the assertion it qualifies … Every response carries `milestone_predicate_unavailable`; the request for a truthful additive milestone predicate on #7870 stays open and is not re-asked.” — line 239.

> “Slices are declared limited witness cohorts, never membership or rank.” — lines 234-237.

> Energy expands “Power-Demand, hydrocarbons, renewables/storage, transition families, expectations overlays, sector projection through the same accepted architecture.” — lines 6-13.

No exact phrase “demand ≠ profit”, “an announced PPA ≠ delivered energy”, “a queue position ≠ capacity”, or “unknown stays unknown” was found in the four blobs or directive. Equivalent binding laws are quoted above; the seat should use those exact wordings rather than infer unstated slogans.

## UNKNOWNS

1. `UNKNOWN`: a machine-named relation for `ai_neoclouds`. Searches: `rg -n 'supplemental|demand.driver|relation' config/theme_crosswalk.yml config/theme_pathways.yml config/theme_thesis_registry.yml`; `git grep -n data_center_power origin/main -- config engine contracts`; the crosswalk supplies `basket_ids` and prose “captures the hyperscaler demand driver”.
2. `UNKNOWN`: `grid_electrification` supplemental basket/relation in current registries. Searches: `git grep -n grid_electrification origin/main -- config engine contracts`; the crosswalk lists only `power_grid`; no supplemental field exists.
3. `UNKNOWN`: live SEC filing counts/filing history. Repo evidence establishes a US listing and SEC CIK, but no filing catalogue was queried. Searches were intentionally repo-only over `data/reference/security_master.parquet`, `data/symbol_directory/cik_map/2026-09-21.parquet`, and `data/edgar/ticker_cik_ledger.json`.
4. `UNKNOWN`: owner of a future Power-Demand implementation carrier. #7791 and ENE-1 own the frozen sequencing/research facts, but the mission explicitly makes this census read-only and no Power-Demand implementation carrier was found.

## SOURCES

- `origin/main` = `daa6a2e1aae0a0e84d702c8824b35a58c49b750a` (`git rev-parse origin/main`).
- #7870 / `refs/remotes/pr7870` = `6cd958e92b259f7221690547e7076f4a0de4ed33`.
- #7791 / `refs/remotes/pr7791` = `68e815d88fc8123a67167ae27b213078fe5339f7`.
- #7870 assertion schema: `contracts/theme_graph/curation_assertion.v1.schema.json`, blob `ff3928f0c54aa164ef8283d9da45af67e6a0d971`.
- #7791 pinned packet: blob `f628167227613175cc3ede088f40423add7252fb`.
- #7791 pinned design: blob `d6dac80bead5a028da8d757b419c896b1b8437ed`.
- #7791 pinned plan: blob `f7dc93621532b06e2478f90ef3876d6c31236242`.
- #7791 pinned checkpoint: blob `a710755c126fe23a0bad8d57f36f272dfd6f5d9b`.
- #7791 R3 artifact: `refs/remotes/pr7791:research/energy/ENERGY_R3_POWER_DEMAND_EQUITY_DOSSIERS_2026-09-23.md`.
- Identity and membership files at the pinned refs: `engine/theme_graph/identity.py`, `config/theme_crosswalk.yml`, `config/theme_pathways.yml`, `config/theme_thesis_registry.yml`, `data/baskets/membership.json`.
- SEC/listing identity artifacts: `data/reference/security_master.parquet` blob `0a5cfdcb0b84f90049bcac9318012ef94df628c2`; `data/symbol_directory/cik_map/2026-09-21.parquet` blob `dd8763feefb7a2899a0d7294c6b254a823d3a49f`; `data/edgar/ticker_cik_ledger.json` blob `f172fc8f0afd80bb78891607241b3d4f2620061a`; metadata at `config/synapse.yml:8033-8041@daa6a2e1`; master CIK semantics at `tests/test_dataos_security_master.py:397-423,500-524@daa6a2e1`. These three narrowly targeted identity artifacts were the only `data/` reads used for Q2; no bulk artifact scan was run.
- Collision records: `docs/PROJECT_ACTIVE_BUILD_MAP.md`, `docs/ACTIVE_BUILD_MAP.md`, `research/DO_NOT_REBUILD.md`, `agentos/workstreams/WS-GMI-THEME-GRAPH.md`, `agentos/workstreams/WS-GMI-INDUSTRIALS-FIRST-VERTICAL.md`, `agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md`.
- GitHub PR records queried read-only with `gh pr list` / `gh pr view`: #6264, #7284, #7453, #7462, #7664, #7789, #7791, #7870, #7908, #7924.
