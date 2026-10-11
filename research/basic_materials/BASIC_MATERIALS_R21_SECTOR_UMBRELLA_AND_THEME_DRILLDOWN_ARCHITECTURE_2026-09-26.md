# Basic Materials R21 — Sector Umbrella + Canonical Theme Drilldown Architecture

**Date:** 2026-09-26  
**Operation:** `gmi-basic-materials-research-20260923-sol-001`  
**Research carrier:** Macro #7796 / `sol/basic-materials-research-20260923`  
**Implementation carrier:** Macro #7984 / `claude/basic-materials-core-v0`  
**Current shared foundation:** Macro #7870 @ `6cd958e92b259f7221690547e7076f4a0de4ed33` (Draft/HOLD)  
**Current Macro main inspected:** `a03e6787000aa255ffa07c2bef1ffc5844fc5d63`  
**Protected procedure:** Mastermind `763ec8f920177fdf48b18df1b8e37b61ab482ef0`, Skillpack 1.0.1/bootstrap1.  
**Disposition:** architecture ruling for the continuing Materials program. This document does not grant source admission, private publication, shared-writer custody, merge authority or trading authority.

## 1. Ruling

Basic Materials is a **sector umbrella**, not one canonical GMI theme.

Do **not** mint `theme:basic_materials`, do not register `basic_materials` as a fake canonical theme merely to fit the shared theme-research shell, and do not collapse the sector research ontology into one theme/basket identity.

The product has two legitimate levels:

1. **Sector umbrella / Basic Materials Intelligence** — one sector-level research dossier that can span all Materials families, including families that have no accepted canonical GMI theme today.
2. **Canonical-theme drilldowns** — individual shared-shell research verticals only for accepted canonical themes and only after the #7870 foundation is accepted on the relevant base.

The pure economics core on #7984 remains below both surfaces. It is a deterministic calculation/explanation library, not a served dossier contract, identity owner, evidence owner, rights owner, publisher or route.

## 2. Evidence for the ruling

### 2.1 The canonical crosswalk does not contain a Basic Materials theme

Current `config/theme_crosswalk.yml` (blob `782dbc519b7bb2d446af91c66c6fb9248722a8b9`) defines the existing canonical theme vocabulary. Relevant Materials rows include:

- `theme:rare_earth_critical_min` — primary basket `critical_minerals`;
- `theme:copper_steel_electrify` — no primary basket; `reshoring` is only a broader demand proxy;
- `theme:ag_fertilizer` — no dedicated basket.

The same file explicitly leaves `gold_miners`, `silver_miners` and `pgm_miners` as unmapped baskets rather than canonical foresight themes. Construction materials, broad commodity/specialty chemicals, industrial gases and forest products/packaging likewise do not have a single accepted canonical Materials theme in this crosswalk.

Therefore the five-document/four-company proof set cannot truthfully be mounted under one existing theme identity. Nutrien, NOVONIX, Wheaton/Antamina and Weyerhaeuser deliberately exercise different economic families.

### 2.2 The shared shell is theme-exact, not sector-wildcard

#7870 now carries a closed generic shell:

- `VerticalRegistration` binds exactly one `anchor_theme_id`, a closed `slice_keys` set, exact response/evidence schemas, composer, evidence selector and owner-bundle loader.
- `MountFacts` binds exactly one accepted anchor plus bilingual mount copy.
- `registration_for()` is exact-key only; no wildcard, prefix, case normalization, environment/config fallback or default vertical.
- The current registry has only `ai_semiconductors`.

That closure is a feature, not a gap for Materials to bypass. A sector aggregate is not an admissible substitute theme.

### 2.3 Finance supplies a production-proven sector-umbrella precedent

Current main contains the Finance sector pattern:

- `templates/_finance_sector_deep_dive.html.j2` places a **Sector deep dive** card outside the canonical Theme Tracker lanes and says explicitly that it is not a theme, watchlist or call.
- `finance_intelligence.html` is a data-free dossier shell.
- `finance_intelligence_read_model.v1` is a sector-specific read model with `sector_ref: sector:financials`, coverage, material changes, domains, slices, company exposure, macro matrix, constraints, conflicts, source records, freshness, input receipts and authority caps.
- Finance keeps the private/evidence integration separate from the public shell and keeps scoring/ranking/entry authority out of the read model.

This is the correct *sector-umbrella* precedent for Basic Materials. Reuse the architecture law, not Finance-specific domains or schema fields mechanically.

### 2.4 Energy and Robotics supply the theme-level precedent — and a sequencing warning

Energy #8002 is a vertical-specific `nuclear_theme_research.v1` module stacked on #7870. It does not invent a second shared shell.

Robotics #7908 demonstrates the failure mode to avoid: it merged before #7870, imported shared modules absent on main, broke `tests/test_first_party_import_names.py`, and was reverted by #8013 / commit `e5512ef66a74b538b165c5a600354c7a8eb35c92`. The revert explicitly calls this a sequencing defect and says to re-land with #7870.

Materials therefore MUST NOT add #7870-only imports to a mergeable main-based carrier before the shared base lands.

## 3. V0 product topology

### 3.1 Basic Materials sector entry

Add one **Basic Materials Intelligence / 原材料情报** sector-deep-dive card to the existing Theme Tracker sector-deep-dive area, outside canonical theme lanes.

The card:
- links to the Basic Materials sector dossier;
- carries no ThemeState stage, lane, rank, score, watchlist or recommendation;
- uses the existing Finance sector-deep-dive visual/accessible idiom and shared design system;
- is one navigation entry, not a new canonical theme.

The card should communicate:
> What changed in Materials economics, which businesses capture it, what reaches retained cash/value, and what evidence matters next.

### 3.2 Data-free sector dossier shell

Proposed later UI surface: `materials_intelligence.html` (final naming may follow current shared naming review).

Like Finance:
- static HTML/CSS/JS contains no private Materials payload;
- not-connected/degraded state is a legitimate shipped shell state;
- private data hydrates only through an accepted authenticated reader;
- EN/ZH, dark/light, desktop/mobile, keyboard and evidence-drawer behavior remain acceptance requirements;
- no public static brief receives full private assertions.

The shell's information architecture should preserve the researched Materials jobs rather than copy Finance section labels blindly. Proposed semantic sections:

1. **What changed** — source-backed economic changes, with exact scope/horizon.
2. **Material / subtheme map** — sector families and current coverage, clearly distinguishing canonical themes from research-only slices.
3. **Profit-pool / value-chain map** — who gains/loses economics and why.
4. **Company exposure** — role, basis, materiality/measurement type and identity state; no universal exposure score.
5. **Cycle / scarcity / capacity view** — only where the industry's model supports it.
6. **Cash & valuation bridge** — reported values, calculations and assumptions kept distinct.
7. **Macro / geography matrix** — mechanisms and lags, never stock verdicts.
8. **Evidence / counterevidence / change conditions** — exact clocks, disagreements, missingness and next evidence.

Progressive disclosure remains mandatory. The first screen answers the investor job; detailed accounting/process evidence opens on demand.

### 3.3 Sector read model

Proposed contract family (subject to current Sector Intelligence owner acceptance):

- `contracts/sector_intelligence/basic_materials_intelligence_read_model.v1.schema.json`
- pure sector projection under `engine/sector_intelligence/` consuming already-read owner outputs.

The read model is a **sector projection**, not another evidence truth plane. It should carry:
- `sector_ref: sector:materials` (or the exact incumbent sector-id form returned by the owner; do not invent a second alias if another canonical value exists);
- generated/knowledge/common-as-of clocks;
- snapshot identity and source/curation generations;
- coverage across Materials domains/slices;
- material changes;
- domain/slice catalog;
- company exposure rows;
- economic mechanisms / profit-capture bridges;
- cash/valuation context;
- macro/geographic context;
- conflicts/counterevidence;
- freshness and degraded sections;
- pointer-only source/evidence receipts;
- authority caps fixed to research/display only.

Do not clone Finance's 52-slice vocabulary or financial-system views. Materials uses the ten researched families and eight common economic lenses, with family-specific fields below the common shell.

### 3.4 Pure T4 core stays reusable and lower-level

#7984 `engine/market_ontology/materials_economics.py` remains the bounded deterministic core.

It:
- consumes explicit typed measures/conditions;
- performs Decimal calculations and deterministic explanation selection;
- produces no source admission, permissions, identity, route or publication state;
- can later be called by the sector read model and by accepted canonical-theme vertical composers;
- imports no #7870-only module while #7870 is off main.

Do not move the core into the sector read model merely because V0 is sector-level. The reusable economics belong below the presentation/transport projection.

R20's repair order remains binding before the core can become a green candidate:
1. current cash-reconciliation RED;
2. canonical decimal grammar;
3. duplicate-role refusal;
4. strict chronology;
5. remaining commercial-progression and contractual-participation mechanisms;
6. output-schema freeze and wider T4 tests.

## 4. Canonical-theme drilldowns after the shared foundation

When #7870 is accepted/available on the appropriate base, existing canonical Materials themes may add their own shared-shell verticals.

### 4.1 Existing eligible anchors

First candidates are the accepted themes already in the crosswalk:

- `rare_earth_critical_min`;
- `copper_steel_electrify`;
- `ag_fertilizer`.

Each vertical gets:
- one exact anchor;
- a closed, reviewed slice set;
- its own vertical-specific `*_theme_research.v1` served contract following the Semiconductor/Energy shared-shell shape;
- owner-bundle adapter;
- shared registry/mount entry through the incumbent shared writer;
- no duplicate API/client/auth/rights system.

Examples of possible slice boundaries from completed Materials research (final acceptance belongs to the theme/ontology owner):
- rare-earth/strategic materials: mining/concentrate, separation/refining, precursors/magnets, recycling/secondary, qualification/commercial readiness;
- copper/steel/electrification: resource production, processing/refining, fabrication/conversion, recycling, development/capacity;
- agriculture/fertilizer: nitrogen, potash, phosphate, crop-input/commercial channel, farmer-affordability/application context.

These are implementation candidates, not authority to mutate canonical ontology.

### 4.2 Families that must remain sector/research slices until ontology admission

Do not register a shared-shell theme for:
- gold / silver / PGM producer sleeves;
- broad construction materials;
- commodity chemicals;
- specialty/functional materials;
- industrial gases;
- forest products / pulp / packaging;
- any other Materials family without a canonical anchor.

They remain legitimate Basic Materials sector slices and research cohorts in the sector dossier. If a future GMI D2D ontology decision admits a canonical theme, that theme can then receive its own shared-shell drilldown.

**No Materials session mints that identity unilaterally.**

## 5. V0 proof mapping

The existing proof set remains valid under the sector architecture:

### Nutrien
Sector slice: phosphate / fertilizer economics.  
Core job: realized price vs COGS and retained unit margin.  
Canonical-theme relationship: may later drill into `ag_fertilizer`; V0 sector dossier does not wait for that mount.

### NOVONIX
Sector slice: battery/strategic materials → synthetic graphite/anode qualification.  
Core job: technical/customer/commercial progression.  
Canonical-theme relationship: adjacent to strategic-materials research; do not force into a current canonical theme if the accepted crosswalk does not say so.

### Wheaton / Antamina
Sector slice: precious metals financial claims / streaming.  
Core job: contractual participation and threshold economics.  
Canonical-theme relationship: gold/silver producer baskets are currently unmapped; V0 sector dossier is therefore the truthful home.

### Weyerhaeuser
Sector slice: forest products / timber / biological assets.  
Core job: actual investment cash vs adjusted distribution measure.  
Canonical-theme relationship: none accepted today; sector dossier is the truthful home.

This confirms why the sector V0 must precede an all-theme-only implementation.

## 6. Shared evidence/private integration

The sector read model does not supersede #7870's shared evidence/rights/private owners.

For original source/economic assertions:
- consume the accepted curation/evidence owner;
- current rights remain an independent veto;
- use the accepted Research Vault/private-publication owner rather than inventing a Materials store;
- source collection/retention, review, identity and publication receipts stay distinct;
- a sector projection may reference evidence but does not become its canonical store.

Where Finance/other sector read models mirror curation field names for display-tier projections, Materials may follow the same owner-preserving idiom only after the current source owners accept the exact mapping.

No sector-level architecture grants a corporate-hosted source `sec_edgar` rights. Source family is determined by actual provenance.

## 7. Route and page sequencing

### May advance independently
- Pure #7984 core, once the previously blocked product-write action is genuinely available.
- Sector read-model contract/projection using synthetic fixtures, if path/custody preflight says those Sector Intelligence paths are free.
- Data-free sector dossier design/shell and Theme Tracker sector-deep-dive card, using the existing Finance pattern and design-system laws, if current template/page custody is reconciled.
- Non-regression freeze proving no theme lane/rank/entry/Prophet/basket decision changes.

### Must wait for owner/foundation
- Any import of #7870-only modules on a main-based merge candidate until #7870 lands or an accepted stacked-base strategy is used.
- Shared registration/mount edits.
- Native source/private publication.
- Real source-to-company browser rehearsal.
- New canonical theme identities.

### Sequencing invariant from Robotics #8013
Never validate against a synthetic/throwaway tree containing #7870 and then merge the dependent vertical into a main that lacks #7870. CI/proof must match the actual merge topology.

## 8. Revised implementation task mapping

The existing eight task identities remain; mechanics change as follows:

- **T1–T3 shared evidence/private/K1:** consume #7870 / existing owners; unchanged.
- **T4 pure economics core:** continue #7984; no shared-only imports; reusable by sector + theme adapters.
- **T4b sector projection (inside existing T4 program, not a ninth lifecycle task):** owner-preserving Basic Materials sector read model that calls the pure core where applicable.
- **T5 transport:** sector V0 may use the incumbent Sector Intelligence authenticated route pattern or, if the accepted owner later standardizes one shared sector route, that owner. Do not force a non-theme sector dossier through #7870's exact-theme route merely for reuse.
- **T6 UI:** Finance-style Theme Tracker sector-deep-dive entry plus data-free Materials dossier shell. Canonical theme mounts remain #7870 shared-shell integrations later.
- **T7 real proof:** all five originals/four companies through the sector dossier, with company/source navigation and private evidence.
- **T8 acceptance:** independent review, deployed/browser proof, private negative-path proof and frozen decision outputs.

This architecture does not remove any of the existing 44 acceptance requirements. Requirements referring to the old standalone Materials theme route/client must be interpreted through the R11/R21 owner-preserving replacements.

## 9. Alternatives rejected

### A. Mint `theme:basic_materials`
Rejected. It duplicates/overrides canonical ontology and falsely implies one theme identity covers heterogeneous sector economics.

### B. Force all Materials into `us_sector_materials` as a canonical GMI theme
Rejected. A sector basket/ETF is a market measurement context, not a canonical semantic theme.

### C. Build only three canonical-theme verticals and omit unmapped families
Rejected. It would drop precious-metals financial claims, forest products and other first-release jobs and would fail the Chairman's sector-level mission.

### D. One giant Materials vertical registered to #7870 under a synthetic anchor
Rejected. Violates exact-anchor closure and repeats vocabulary-N+1.

### E. New standalone Materials evidence/private/API/client stack
Rejected. Duplicates existing owners and directly violates program law.

## 10. Capability statement and next actions

**Before R21:** the Materials program had a strong economic core design and a real T4 implementation carrier, but its served-product identity was still implicitly theme-shaped even though the first proof set spans unrelated/unmapped Materials families.

**After R21:** the product architecture is explicit and owner-preserving:
- V0 is a Basic Materials **sector dossier**;
- #7984 supplies reusable economics below it;
- accepted canonical Materials themes later receive exact shared-shell drilldowns;
- missing canonical themes stay sector/research slices until GMI ontology admission;
- no fake `theme:basic_materials`.

Exact next actions:
1. preserve #7984 RED until the blocked product-write class is genuinely available; then resume its frozen TDD order;
2. reconcile current Sector Intelligence path ownership for a Basic Materials sector read-model carrier;
3. freeze the sector V0 read-model fields and first-release slice catalog using R1–R20 research—without duplicating source records;
4. reconcile Theme Tracker/template custody for one Finance-style sector-deep-dive entry and data-free shell;
5. keep #7870 theme registrations/native private proof dependency-held;
6. update the current Fable integration packet and Agent OS checkpoint to this architecture before any new implementation assignment.

**MISSION_COMPLETE:** false.  
**FINALIZATION_CLASSIFICATION:** CHECKPOINTED_CONTINUATION once the updated packet/checkpoint are read back.
