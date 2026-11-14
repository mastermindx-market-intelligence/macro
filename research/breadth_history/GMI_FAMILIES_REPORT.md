# GMI theme-graph families and the group links table

Sector Intelligence quant lead, 2026-11-12, under COO rulings 31 §2, 32 §2 and 34 §§2–3.
Data only: nothing here relates any series or link to an outcome (no forward returns, hit
rates or backtests).

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
- Prices: the same single-vintage download as the tree families. All 201 graph member
  tickers are in it, so 0% are missing.
- The relationship hub families need four names that download lacks: ALGM, CRUS, MXL and
  SITM. A top-up fetched them under the COO's 09:39Z conditions: one call per ticker for the
  full history, same library and settings, 2026-11-12T09:39:20Z, scratch only. Each name's
  history comes from one download, and no ticker has history from two. The sidecar records
  this as `price_topup`. The #11107 series do not use these names.
- Start 2000-01-01, with the same sidecar sentences.

## Member floors (COO ruling 34 §2, for every family in the history build)

The floors of rulings 27, 31 and 32 no longer apply to these files.
- **Index:** built from 2 priced members (was 5).
- **Breadth:** built from 2 counted members (was 10). Every share is committed with
  `n_above_200` and `n_counted_200` beside it.
- **`size_class`:** set per group per date. A group is `small` when fewer than 10 members
  are counted that date, else `standard`.
- **Rank:** computed within the same family and size class on each date only.
- **Like-for-like change:** computed from 2 eligible members, with the count `n_fixed_*`
  beside it.
- **One-member group:** it gets no series. The links table marks it `single_name`; none
  exists in this build.
- In a group of n members the share moves in steps of 100/n. Read a small group's share as a
  count.
- The live engine's own floor is unchanged.

**Valid on the last week (2026-11-06) under the new floors:**

| Family | Groups | Breadth valid: standard | Breadth valid: small | Index valid |
|---|---|---|---|---|
| `gmi_theme` | 15 | 13 | 2 | 15 |
| `gmi_macro_category` | 7 | 7 | 0 | 7 |
| `rel_customers_of` | 4 | 1 | 3 | 4 |
| `rel_suppliers_of` | 3 | 0 | 3 | 3 |
| `basket` (index only) | 49 | – | – | 49 |
| `sector` (index only) | 11 | – | – | 11 |
| `subsector` (vendor, internal only) | 268 | 97 | 171 | 268 |
| `theme` (vendor, internal only) | 40 | 40 | 0 | 40 |

Under the old floors the counts were 13 for `gmi_theme`, 97 for `subsector` and 40 for
`theme`. Every group with members now has a series. The two small `gmi_theme` groups are
medical_devices (9) and memory_storage (4).

## Families (house file set, one `FAMILIES` entry each)

| Family | Groups in graph | With US members | Member tickers | Slots |
|---|---|---|---|---|
| `gmi_theme` | 18 | 15 | 201 | 235 |
| `gmi_macro_category` | 10 | 7 | 201 | 267 |

`gmi_theme` per theme (US members):

| Theme | Members | Theme | Members |
|---|---|---|---|
| ai_semiconductors | 26 | nuclear_power | 19 |
| grid_electrification | 24 | data_center_power | 18 |
| defense_aerospace | 21 | copper_steel_electrify | 16 |
| fintech_payments | 21 | semicap_equipment | 16 |
| space_satellite | 15 | glp1_obesity | 13 |
| robotics_automation | 12 | rare_earth_critical_min | 11 |
| cybersecurity | 10 | medical_devices | 9 (small) |
| memory_storage | 4 (small) | ag_fertilizer, diagnostics_lifesci, solar | 0 (no series) |

`gmi_macro_category`: industrials_defense 57, technology_software 51, energy_power 47,
semiconductors_hardware 42, materials_mining 27, healthcare_lifesciences 22,
financial_services 21. consumer_cyclical, consumer_defensive and crypto_digital_assets have
no US members and no series.

The first valid breadth date for each group is in the house sidecar. Under the floor of 2,
a group begins when its second member has 200 sessions, so most start in 2000.
One group starts 2013-08-09.

## Relationship hubs (COO ruling 32 §2)

`rel_customers_of` and `rel_suppliers_of` come from
`data/company_intelligence/relationships/relationship_edges.json` at the same pinned commit.
- **Edges used:** the 178 proposed edges of species supplier_customer,
  contract_manufacturing and component_dependency. All are US to US.
- **Roles:** normalised to supplier → customer, which gives 153 distinct pairs.
- **Hubs:** a hub is a company with 5 or more counterparties. Groups are named by the hub.
  - Customers of supplier hubs: TSM 19, UMC 7, AMKR 5, GFS 5.
  - Suppliers of customer hubs: AAPL 7, FTNT 7, INTC 5.
- All seven hubs are chips and hardware companies. Only TSM reaches the standard class.
- **Basis:** `proposed_relationships_unadmitted`. Today's proposed edges are applied to the
  past.
- **Measured quality:**
  - precision 0.6621, stratum-weighted, Wilson 95% [0.5596, 0.7646]
    (`research/theme_graph/GMI_O5_VERIFICATION_VERDICTS_2026-11-02.md:210`);
  - recall 0.3487 (83/238) (same file, line 201).
- About one member in three may be wrong, and about two in three true members are missing.
- This is as far as the relationship data reaches. No further relationship series will be
  built until the edge set grows.

## Subthemes and microthemes: no series

All 65 subthemes and 370 of the 371 microthemes have no member in the graph, by the frozen
V1 rule (`research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md:29-30`). We do not
invent members. Their full parent structure is in the links table with `has_series` false, so
it is ready when members arrive. The curation lead ratifies members through the existing
route (ruling 34 §1). The series are built from its crosswalk once that lands, under the
same floors.

## Links tables

The links are split by rights class, like the series:
- house rows go to `group_links_current.parquet` (1,383 rows);
- every row touching a vendor family (subsector, theme) goes to
  `vendor_internal_only_group_links_current.parquet` (13,982 rows), with the
  vendor rights fields in its sidecar. The repository is public, so this vendor file is kept
  off git, in scratch (the exporter's `--vendor-out`, default `/tmp/si_plan/quant/vendor_out/`),
  never committed or pushed (COO ruling 38 §2b).

One row per link between two groups. There is no ticker column and no prices. Columns:
- child family and id; parent family and id; link type;
- pathway node and node type; source file and source commit;
- `has_series` for each end (true when the weekly index has a valid level);
- `n_shared`; `child_n` and `parent_n` (registry members of each side);
- `single_name` for each end;
- `rights_class`.

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
| any house group ↔ any house group | `overlap` (COO ruling 34 §3) | 462 |
| any pair touching subsector or theme | `overlap` (vendor file) | 13,982 |

**Overlap.** There is one row for each unordered pair of groups in the history build that
share at least one member. It covers pairs within a family and across families. Each row
gives the shared count and each side's member count, with no tickers. The rows are computed
from the registries the series use.

**Vendor subsector → house theme: 0 of our 268 subsectors match.** The graph holds the 268
vendor subsectors as `ltheme:finviz:*` nodes, but only as company → local theme MEMBER_OF rows
(2,339). Every local theme → theme EXPRESSES row (671) comes from the China THS plane
(`ltheme:ths:*`). No basket → finviz local theme edge exists either. So the graph gives no
subsector-to-theme link today, and the table carries none. The exporter writes such rows
automatically if the graph gains them.

The cause was checked by an independent read at the pinned commit. The keys are not the
problem: each subsector key equals its node id suffix, `external_ids.subtheme_key` and
`source_meta.source_local_id`, 268 of 268. The graph withholds the edge by design.
`engine/theme_graph/materialize.py:1385-1390` says no concept-grain curation exists for the
vendor subthemes and a mechanical mapping would smear them onto the wrong themes. The
crosswalk's `subsector_keys` hold the 40 vendor theme names (14 of 14 match a theme key, 0 a
subsector key). So there is no exact documented key, no rows are added, and the vendor links
sidecar states the cause as `subsector_to_theme_cause`.

**Baskets.** Only 18 of the 49 US baskets express a house theme in the graph. The other 31
are the crosswalk's `unmapped_baskets`.

The exporter refuses to write a table whose ids do not all resolve to a graph node, a basket,
a subsector key or a pathway node. A test checks that `has_series` agrees with the index file.

## Not here

- No relationship series beyond the seven hubs (ruling 32 §2).
- No sideways curated links (feeds, competes_with, substitutes_for). They come from the
  curation lead once ratified (ruling 34 §3).
- No change to `data/theme_graph/`, the crosswalk, the pathways file or the relationship file.
- Child-against-parent and chain studies belong to the rotation desk.

## Rebuild

```
python scripts/export_gmi_history_registry.py --root <tree at the pinned commit> --commit <sha> \
  --registries-only
python scripts/build_tree_breadth_and_index.py --closes <scratch, first download + top-up> \
  --download-meta <scratch> --disagreement <yearly csv> --start 2000-01-01 --daily house
python scripts/export_gmi_history_registry.py --root <same> --commit <sha> --index \
  data/breadth/history/house_ew_index_weekly_current.parquet \
  /tmp/si_plan/quant/vendor_out/vendor_internal_only_ew_index_weekly_current.parquet
```

## Files and sizes

| File | Bytes |
|---|---|
| `house_breadth_weekly_current.parquet` | 465,314 |
| `house_ew_index_weekly_current.parquet` | 1,040,390 |
| `house_ew_index_daily_current.parquet` | 5,376,121 |
| `house_breadth_and_index_current.meta.json` | 19,855 |
| `group_links_current.parquet` + sidecar | 24,936 + 11,030 |
| `vendor_internal_only_breadth_weekly_current.parquet` (scratch, off git) | 3,824,814 |
| `vendor_internal_only_ew_index_weekly_current.parquet` (scratch, off git) | 3,780,804 |
| `vendor_internal_only_breadth_and_index_current.meta.json` (scratch, off git) | 39,923 |
| `vendor_internal_only_group_links_current.parquet` + sidecar (scratch, off git) | 41,145 + 9,663 |
| `registry/*.csv` (four files) | 15,144 |
| **Total** | **14.6 MB** |

No vendor file is committed: the repository is public, so the whole vendor set (breadth,
weekly index, sidecar and links) is kept off git, in scratch (COO ruling 38 §2b). The vendor
daily index is not built by default either; with size class and the small groups it measures
18.2 MB at the repository's compression, or 14.4 MB at maximum zstd. It rebuilds from the
scratch download with `--daily`. The house daily index is committed. #11107's committed house
files are unchanged at their checked head. This draft regenerates them on top of it.
