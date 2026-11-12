# GMI theme-graph families and the group links table

Sector Intelligence quant lead, 2026-11-12, under COO ruling 31 §2. Data only: nothing here
relates any series or link to an outcome (no forward returns, hit rates or backtests).

**Read first.** Today's members are applied to the past (`reconstructed_current_membership`).
This is not point-in-time, and it covers survivors only. The graph's dated membership is not
used: most of its dates are a seed constant or a reconstruction, not an observed change.

## Source

- `data/theme_graph/` at main `e907472c31478649d0827b128da577dd05ee39c2`. The sidecar
  `group_links_current.meta.json` records this as `source_commit`.
- Exported by `scripts/export_gmi_history_registry.py` with the store's own read views:
  - latest belief per edge, then open edges only;
  - company → basket (MEMBER_OF) → house theme (EXPRESSES); macro category → theme (PARENT_OF);
  - US-listed resolved identities only (listing key `US-…`);
  - the three nodes that `node_lifecycle.parquet` marks retired or merged are dropped
    (`co:us:GOLD`, `co:us:IBIT`, `co:us:VMRK`);
  - no vendor local-theme rows.
- Prices: the same single-vintage download as the tree families (no second download).
  All 201 member tickers are priced, so 0% are missing.
- Start 2000-01-01, with the same floors, sidecar sentences and rank-within-family rule.

## Families (committed in the existing tree files, one `FAMILIES` entry each)

| Family | Groups in graph | With US members | Member tickers | Slots | Valid for breadth, last week (≥10) |
|---|---|---|---|---|---|
| `gmi_theme` | 18 | 15 | 201 | 235 | 13 |
| `gmi_macro_category` | 10 | 7 | 201 | 267 | 7 |

`gmi_theme` per theme (US members):

| Theme | Members | Theme | Members |
|---|---|---|---|
| ai_semiconductors | 26 | nuclear_power | 19 |
| grid_electrification | 24 | data_center_power | 18 |
| defense_aerospace | 21 | copper_steel_electrify | 16 |
| fintech_payments | 21 | semicap_equipment | 16 |
| space_satellite | 15 | glp1_obesity | 13 |
| robotics_automation | 12 | rare_earth_critical_min | 11 |
| cybersecurity | 10 | medical_devices | 9 (counts and index only) |
| memory_storage | 4 (counts only) | ag_fertilizer, diagnostics_lifesci, solar | 0 (no series) |

`gmi_macro_category`: industrials_defense 57, technology_software 51, energy_power 47,
semiconductors_hardware 42, materials_mining 27, healthcare_lifesciences 22,
financial_services 21. consumer_cyclical, consumer_defensive and crypto_digital_assets have
no US members and no series.

The first valid breadth date for each group is in the tree sidecar. Most start in 2000. The
younger themes begin when their tenth member has 200 sessions: cybersecurity 2025-05-16,
rare earths 2024-08-02, space 2022-12-02, data-center power 2021-11-05.

## Subthemes and microthemes: no series

All 65 subthemes and 370 of the 371 microthemes have no member in the graph, by the frozen
V1 rule (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:29-30`). The research
side's candidate roles average about 2 per microtheme, which is under both floors. We do not
invent members. Their full parent structure is in the links table with `has_series` false, so
it is ready when members arrive.

## Links table `group_links_current.parquet`

One row per link between two groups. It has no ticker column and no prices. Columns:
child family and id, parent family and id, link type, pathway node, node type, source file,
source commit, and `has_series` for each end (true when the weekly index has a valid level).

| Child → parent | Link type | Rows |
|---|---|---|
| basket → gmi_theme | EXPRESSES | 18 |
| gmi_theme → gmi_macro_category | PARENT_OF | 21 |
| gmi_sub_theme → gmi_theme | PARENT_OF | 65 |
| gmi_micro_theme → gmi_theme | PARENT_OF | 375 |
| gmi_micro_theme → gmi_sub_theme | PARENT_OF | 283 |
| basket → gmi_theme | PATHWAY_ROLE (`config/theme_pathways.yml`) | 68 |
| pathway_node → gmi_theme | PATHWAY_ROLE (nodes with no basket) | 25 |
| pathway_node → pathway_node | PATHWAY_WINNER / PATHWAY_LOSER (curated chain steps) | 48 / 18 |

**Vendor subsector → house theme: 0 of our 268 subsectors match.** The graph holds the 268
vendor subsectors as `ltheme:finviz:*` nodes, but only as company → local theme MEMBER_OF rows
(2,339). Every local theme → theme EXPRESSES row (671) comes from the China THS plane
(`ltheme:ths:*`). No basket → finviz local theme edge exists either. So the graph gives no
subsector-to-theme link today, and the table carries none. The exporter writes such rows
automatically if the graph gains them.

**Baskets.** Only 18 of the 49 US baskets express a house theme in the graph. The other 31
are the crosswalk's `unmapped_baskets`.

The exporter refuses to write a table whose ids do not all resolve to a graph node, a basket,
a subsector key or a pathway node. A test checks that `has_series` agrees with the index file.

## Not here

- No series from the 248 proposed company relationships (ruling 31 §4).
- No change to `data/theme_graph/`, the crosswalk, the pathways file or the relationship file.
- Child-against-parent and chain studies belong to the rotation desk.

## Rebuild

```
python scripts/export_gmi_history_registry.py --root <tree at the pinned commit> --commit <sha>
python scripts/build_tree_breadth_and_index.py --closes <scratch> --download-meta <scratch> \
  --disagreement <yearly csv> --start 2000-01-01 --daily
python scripts/export_gmi_history_registry.py --root <same> --commit <sha> \
  --index data/breadth/history/group_ew_index_weekly_current.parquet
```
