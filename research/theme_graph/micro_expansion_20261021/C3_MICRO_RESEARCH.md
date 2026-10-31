# C3 micro-theme expansion research — materials & health group (2026-10-21)

Lane `gmi-micro-c3-20261021-r9` · base `ca7edbcf50df21bd321bffa3433e5f105d3335da` · commissioned by the GMI COMPLETION seat (Fable Meta-CEO, Chairman commission 2026-10-21).

PROPOSE rows only — this lane never ratifies. Research-only display vocabulary: no constituents, no tickers, no issuer names anywhere, no weights, no predictive claims. Sources are public, non-vendor references (industry associations, standards bodies, regulators, filings-style segment vocabulary, trade-press value-chain maps, academic venues). Chinese names follow A-share/HK disclosure and Chinese trade-press usage. Paired machine rows: `C3_PROPOSED_ROWS.yaml`.

Existing micro-themes under these six themes are untouched; every row below ADDS a mechanism-distinct position and names its nearest existing/proposed neighbour in `distinct_from`.

---

## theme:rare_earth_critical_min — Rare Earth & Critical Minerals

Existing rows stay as-is: `theme:critical_mineral_mining_development` (generic producer/developer layer), `theme:rare_earth_separation_refining` (oxide-stage midstream), `theme:ndfeb_permanent_magnets` (sintered NdFeB), `theme:gallium_germanium_supply_chain`, sub-theme `theme:rare_earth_processing_magnets`. The 16 rows below complete the chain: pre-production exploration, five extraction/conversion mechanisms beyond generic mining, a circularity pillar (by-product recovery, recycling, substitution), three non-magnetic functional-material families, and the oxide→metal step plus alternative magnet mechanisms inside the existing processing-to-magnets sub-theme.

**Sub-theme grouping.** Three new sub-themes organise the additions: `theme:critical_min_extraction_routes` (upstream) groups rows whose mechanism is the extraction/first-conversion process itself — ionic-clay leaching, placer sands, brine DLE, laterite HPAL and graphite beneficiation — all distinct from the generic mining-development row. `theme:critical_min_circularity` (enabler) groups the secondary pillar: by-product recovery from industrial waste streams, end-of-life magnet recycling, and demand-side substitution technology. `theme:ree_functional_materials` (downstream) groups non-magnetic rare-earth outputs by physical function — mechanical/chemical (polishing, glass, ceramics), optical (phosphors, scintillators) and catalytic. The two remaining midstream rows attach to the existing `theme:rare_earth_processing_magnets` because they are the metal step and an alternative-magnet mechanism inside the already-ratified processing-to-magnets grouping. `theme:ree_exploration_resource_definition`, `theme:tungsten_smelting_carbides` and `theme:titanium_sponge_pigment` stand directly under the theme: exploration precedes extraction, and the tungsten/titanium chains are single continuous chains best read without an intermediate layer.

**Theme-tier candidates (prose only).** If the seat ever wants a deeper cut, the battery-metal half of `critical_min` (lithium, nickel-cobalt, graphite) is now large enough to support a distinct `battery_raw_materials`-class theme, separating energy-transition metals from the rare-earth/magnet and export-control (gallium/germanium) narratives that currently share this theme.

### ree_exploration_resource_definition
- **id**: `theme:ree_exploration_resource_definition`
- **name_en**: Rare-earth & critical-mineral exploration · **name_zh**: 稀土及关键矿产勘查评价
- **value_chain_position**: upstream · **parent_sub_theme**: none
- **defining_activities**: acquiring and permitting early-stage mineral ground; conducting geological mapping, geophysics and drilling campaigns; defining and upgrading resources under public reporting codes; publishing scoping and preliminary economic assessments.
- **distinct_from**: `theme:critical_mineral_mining_development` — that row names the operating producer/developer layer; this row is the pre-production exploration and resource-definition work that feeds it.
- **exclusions**: operating mines, processing plants, exploration-equipment rental without project stewardship.
- **china_relevance**: high — 勘查登记与储量评审是自然资源部矿业权管理的入口环节，稀土资源评价直接受《稀土管理条例》框架约束。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* (Rare Earths and related chapters); (2) JORC Code (Australasian Joint Ore Reserves Committee) and CRIRSCO International Reporting Template; (3) 自然资源部《中国矿产资源报告》.

### ion_adsorption_ree_leaching
- **id**: `theme:ion_adsorption_ree_leaching`
- **name_en**: Ion-adsorption rare-earth extraction · **name_zh**: 离子型稀土矿浸出提取
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:critical_min_extraction_routes`
- **defining_activities**: extracting ion-adsorption clay deposits by in-situ leaching; managing lixiviant injection and collection; producing mixed rare-earth carbonate/oxide feed; reclaiming leached sites.
- **distinct_from**: `theme:critical_mineral_mining_development` (generic producer layer) and `theme:heavy_mineral_sands_monazite` (placer vs clay mechanism) — this row is the specific ionic-clay leach mechanism that supplies medium-and-heavy rare earths.
- **exclusions**: hard-rock bastnaesite mining, separation/refining of oxides.
- **china_relevance**: high — 南方离子型稀土是中重稀土核心资源，开采实行总量指标与回收工艺监管。
- **confidence**: high
- **sources**: (1) 国务院《稀土管理条例》(2024); (2) USGS, *Mineral Commodity Summaries* — Rare Earths; (3) 中国稀土行业协会行业运行资料.

### heavy_mineral_sands_monazite
- **id**: `theme:heavy_mineral_sands_monazite`
- **name_en**: Heavy mineral sands & monazite streams · **name_zh**: 重矿砂与独居石资源开采
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:critical_min_extraction_routes`
- **defining_activities**: dredge and dry-mining coastal placer deposits; gravity-separating ilmenite, rutile, zircon and monazite concentrates; managing naturally occurring radioactive material in monazite; selling rare-earth-bearing by-product streams.
- **distinct_from**: `theme:ion_adsorption_ree_leaching` — in-situ clay leaching versus mechanical placer mining with NORM handling; rare earths here are a by-product of a titanium/zircon suite.
- **exclusions**: TiO2 pigment and sponge smelting (see `theme:titanium_sponge_pigment`), REE separation.
- **china_relevance**: medium — 海滨砂矿主要分布于沿海省份与海外矿权，国内供给占比有限但选矿产能重要。
- **confidence**: medium
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Rare Earths; Zirconium and Hafnium; (2) IAEA safety reports on the management of naturally occurring radioactive material (NORM) in mineral-sand processing.

### lithium_brine_dle
- **id**: `theme:lithium_brine_dle`
- **name_en**: Lithium brine & direct lithium extraction · **name_zh**: 盐湖提锂与直接提锂
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:critical_min_extraction_routes`
- **defining_activities**: pumping and concentrating salar and salt-lake brines; applying adsorption/membrane/solvent extraction (direct lithium extraction) technologies; producing lithium chloride/carbonate base liquids; managing freshwater and tailings balance.
- **distinct_from**: `theme:ion_adsorption_ree_leaching` (different metal and mechanism) and `theme:critical_mineral_mining_development` — this row is the brine/DLE route, not hard-rock spodumene mining or the generic producer layer.
- **exclusions**: spodumene hard-rock mining, lithium chemical conversion plants downstream of brines.
- **china_relevance**: high — 盐湖提锂是青藏盐湖资源开发的主导工艺，吸附法直接提锂为国产化重点方向。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Lithium; (2) IEA, *Global Critical Minerals Outlook*; (3) 自然资源部《中国矿产资源报告》.

### nickel_cobalt_hpal
- **id**: `theme:nickel_cobalt_hpal`
- **name_en**: Laterite nickel-cobalt HPAL · **name_zh**: 红土镍钴高压酸浸
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:critical_min_extraction_routes`
- **defining_activities**: pressure-leaching laterite ores in autoclaves; producing mixed hydroxide precipitate and nickel-cobalt intermediates; managing acid plants and tailings; feeding battery-precursor and class-1 nickel chains.
- **distinct_from**: `theme:lithium_brine_dle` (brine vs laterite) and `theme:refined_copper` (pyrometallurgical copper chain, other metal) — this row is the acid-leach hydrometallurgical route for battery-grade nickel and cobalt.
- **exclusions**: sulphide smelting of nickel, stainless-steel mills.
- **china_relevance**: high — 湿法高压酸浸中间品是动力电池镍钴原料的主要增量来源，印尼与中国冶炼产能深度联动。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Nickel; Cobalt; (2) CSIRO hydrometallurgy research programmes on laterite processing; (3) IEA, *Global Critical Minerals Outlook*.

### natural_graphite_processing
- **id**: `theme:natural_graphite_processing`
- **name_en**: Natural graphite mining & purification · **name_zh**: 天然石墨采选与提纯
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:critical_min_extraction_routes`
- **defining_activities**: mining and flotation-beneficiating flake and vein graphite; purifying to battery- and refractory-grade purity; micronising and spheronising into spherical graphite; classifying for refractory, foundry and seal applications.
- **distinct_from**: `theme:gallium_germanium_supply_chain` (semiconductor metals) and `theme:nickel_cobalt_hpal` (metal hydrometallurgy) — this row is the natural-carbon mineral route that feeds anodes and refractories.
- **exclusions**: synthetic graphite furnaces, battery-cell manufacturing.
- **china_relevance**: high — 中国是天然鳞片石墨采选与球形石墨加工的主要产地，提纯与石墨化产能集中度高。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Graphite; (2) 中国非金属矿工业协会行业资料; (3) EU Critical Raw Materials Act (Regulation (EU) 2024/1252) raw-materials list.

### tungsten_smelting_carbides
- **id**: `theme:tungsten_smelting_carbides`
- **name_en**: Tungsten smelting & cemented carbides · **name_zh**: 钨冶炼与硬质合金
- **value_chain_position**: midstream · **parent_sub_theme**: none
- **defining_activities**: converting tungsten concentrates into APT and tungsten oxides; reducing to tungsten metal powder; carburising and sintering cemented-carbide grades; producing rods, inserts and wear parts.
- **distinct_from**: `theme:critical_mineral_mining_development` (mine stage) and `theme:ndfeb_permanent_magnets` (different function) — this row is the refractory-metal smelting-to-carbide conversion chain.
- **exclusions**: tungsten mine operation itself, downstream machining shops using purchased inserts.
- **china_relevance**: high — 中国钨精矿与 APT/硬质合金产能占全球主要份额，实行开采总量控制。
- **confidence**: high
- **sources**: (1) International Tungsten Industry Association (ITIA) tungsten data publications; (2) USGS, *Mineral Commodity Summaries* — Tungsten; (3) 中国钨业协会行业统计资料.

### titanium_sponge_pigment
- **id**: `theme:titanium_sponge_pigment`
- **name_en**: Titanium sponge & pigment chain · **name_zh**: 海绵钛与钛白粉产业链
- **value_chain_position**: midstream · **parent_sub_theme**: none
- **defining_activities**: chlorinating titanium minerals to TiCl4; reducing to sponge metal (Kroll route) and melting ingots; running chloride-process pigment plants; supplying aerospace-grade and pigment-grade output.
- **distinct_from**: `theme:heavy_mineral_sands_monazite` (upstream placer mining vs smelting/pigment conversion) and `theme:gallium_germanium_supply_chain` (different metal family) — this row is the mineral-to-sponge/pigment conversion stage.
- **exclusions**: upstream dredge mining, downstream aerospace forgings.
- **china_relevance**: high — 中国海绵钛与钛白粉产能全球占比高，氯化法钛白与航空级海绵钛是升级方向。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Titanium Mineral Concentrates; Titanium Sponge; (2) International Titanium Association industry publications.

### critical_min_byproduct_recovery
- **id**: `theme:critical_min_byproduct_recovery`
- **name_en**: By-product critical-mineral recovery · **name_zh**: 关键矿产伴生资源综合回收
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:critical_min_circularity`
- **defining_activities**: recovering rare earths, niobium, tantalum and scandium from beneficiation tailings; extracting criticals from phosphogypsum and coal ash; reprocessing historical mine waste; valorising smelter residues.
- **distinct_from**: `theme:magnet_scrap_recycling` (end-of-life product recycling vs industrial-process-waste recovery) and `theme:critical_mineral_mining_development` (primary ore mining) — this row is secondary recovery from other chains' waste streams.
- **exclusions**: municipal e-waste collection, primary mining of dedicated deposits.
- **china_relevance**: high — 磷石膏、尾矿与粉煤灰综合利用是政策重点支持的伴生资源回收方向。
- **confidence**: medium
- **sources**: (1) EU Critical Raw Materials Act (Regulation (EU) 2024/1252); (2) USGS, *Mineral Commodity Summaries* (by-product commodity chapters, e.g. Tellurium); (3) IEA, *The Role of Critical Minerals in Clean Energy Transitions*.

### magnet_scrap_recycling
- **id**: `theme:magnet_scrap_recycling`
- **name_en**: Rare-earth magnet recycling · **name_zh**: 稀土磁材回收利用
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:critical_min_circularity`
- **defining_activities**: collecting swarf and end-of-life magnets from motors, wind turbines and electronics; demagnetising and sorting feed; recovering rare-earth oxides or metals via hydrometallurgy or short-magnet re-sintering; re-entering magnet supply.
- **distinct_from**: `theme:rare_earth_separation_refining` (primary ore feed vs recycled feed) and `theme:critical_min_byproduct_recovery` (process waste vs end-of-life products) — this row is the urban-mining loop specific to magnets.
- **exclusions**: battery recycling, general scrap trading.
- **china_relevance**: high — 退役磁材与加工废料回收是国家循环经济重点，回收氧化钕镨供给占比持续上升。
- **confidence**: high
- **sources**: (1) Rare Earth Industry Association (REIA) magnet-recycling studies; (2) EU Critical Raw Materials Act (Regulation (EU) 2024/1252) recycling benchmarks; (3) 国务院《稀土管理条例》(2024) 回收利用条款.

### critical_min_substitution
- **id**: `theme:critical_min_substitution`
- **name_en**: Critical-mineral substitution technologies · **name_zh**: 关键矿产减量替代技术
- **value_chain_position**: enabler · **parent_sub_theme**: `theme:critical_min_circularity`
- **defining_activities**: developing lower- or zero-heavy-REE magnet grades; qualifying substitution chemistries (ferrite, iron-nitride classes, reduced-dysprosium designs); thrifting critical content in catalysts and alloys; validating performance equivalence for OEMs.
- **distinct_from**: `theme:magnet_scrap_recycling` (supply-side recovery vs demand-side replacement) and `theme:ndfeb_permanent_magnets` (magnet manufacturing vs substitution R&D/products) — this row reduces or replaces critical-mineral demand.
- **exclusions**: recycling, mining, magnet production itself.
- **china_relevance**: medium — 少重稀土化与铁氮类永磁研究在国内高校院所活跃，产业化仍以海外先行。
- **confidence**: medium
- **sources**: (1) US Department of Energy, *Critical Materials Strategy*; (2) USGS, *Mineral Commodity Summaries* — "Substitutes" sections of commodity chapters.

### ree_polishing_glass_ceramic
- **id**: `theme:ree_polishing_glass_ceramic`
- **name_en**: Rare-earth polishing & glass-ceramic materials · **name_zh**: 稀土抛光粉与玻璃陶瓷材料
- **value_chain_position**: downstream · **parent_sub_theme**: `theme:ree_functional_materials`
- **defining_activities**: producing cerium-oxide polishing powders; supplying glass decolourising and UV-filtering additives; producing zirconia and rare-earth-stabilised ceramic powders; serving optics, displays and precision glass lines.
- **distinct_from**: `theme:ndfeb_permanent_magnets` (magnetic function vs mechanical/chemical function) and `theme:ree_phosphor_luminescent` (optical excitation vs polishing) — this row is the mechanical/chemical-function material family.
- **exclusions**: magnet-grade oxide supply, catalysts.
- **china_relevance**: high — 中国抛光粉产能全球占比高，光学玻璃与精密陶瓷用稀土材料以内需为主。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Rare Earths (end-use data); (2) 中国稀土行业协会功能材料运行数据; (3) *Journal of Rare Earths* (academic venue) on ceria polishing and glass applications.

### ree_phosphor_luminescent
- **id**: `theme:ree_phosphor_luminescent`
- **name_en**: Rare-earth phosphors & luminescent materials · **name_zh**: 稀土发光与荧光材料
- **value_chain_position**: downstream · **parent_sub_theme**: `theme:ree_functional_materials`
- **defining_activities**: synthesising REE-activated phosphor powders (Y, Eu, Tb, Ce systems); producing scintillator and laser-host crystals; qualifying luminescent grades for lighting, display and medical imaging screens; managing colour-point calibration.
- **distinct_from**: `theme:ree_polishing_glass_ceramic` and `theme:ree_catalyst_materials` — different physical function (optical excitation) of the same upstream oxides.
- **exclusions**: LED chip fabrication, display panel assembly.
- **china_relevance**: high — 照明显示产业链配套完整，稀土发光材料本土化程度高。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Rare Earths (lighting end-use); (2) 中国照明电器协会行业资料; (3) *Journal of Rare Earths* (academic venue) on REE luminescent materials.

### ree_catalyst_materials
- **id**: `theme:ree_catalyst_materials`
- **name_en**: Rare-earth catalyst materials · **name_zh**: 稀土催化材料
- **value_chain_position**: downstream · **parent_sub_theme**: `theme:ree_functional_materials`
- **defining_activities**: producing cerium-based fluid-cracking additives for refineries; supplying ceria-zirconia oxygen-storage components for automotive exhaust catalysts; formulating industrial and water-treatment catalysts; managing washcoat and support chemistry.
- **distinct_from**: `theme:ree_phosphor_luminescent` (catalytic vs luminescent function) — nearest non-magnetic downstream family with a distinct function.
- **exclusions**: precious-metal catalyst loading unrelated to REE, refinery operations.
- **china_relevance**: high — 尾气催化剂与炼油裂化助剂需求大，铈锆储氧材料国产化配套成熟。
- **confidence**: high
- **sources**: (1) International Zeolite Association (FCC zeolite/additive research community); (2) USGS, *Mineral Commodity Summaries* — Rare Earths (petroleum refining end-use); (3) 中国石油和化学工业联合会行业资料.

### ree_metals_master_alloys
- **id**: `theme:ree_metals_master_alloys`
- **name_en**: Rare-earth metals & master alloys · **name_zh**: 稀土金属与中间合金
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:rare_earth_processing_magnets`
- **defining_activities**: electrolytically reducing rare-earth oxides in molten-salt cells; producing NdPr, Dy and La/Ce metals and mischmetal; casting master alloys for magnet and battery-plate makers; controlling oxygen and impurity specs.
- **distinct_from**: `theme:rare_earth_separation_refining` (oxide output vs metal reduction) — this row is the metal step between separated oxides and magnet fabrication inside the existing processing-to-magnets grouping.
- **exclusions**: separation plants, magnet alloying/powder metallurgy downstream.
- **china_relevance**: high — 稀土金属电解产能集中于国内，金属品质直接影响磁材出口等级。
- **confidence**: high
- **sources**: (1) 全国稀土标准化技术委员会（SAC/TC 229）稀土金属产品国家标准; (2) 中国稀土行业协会行业运行资料; (3) USGS, *Mineral Commodity Summaries* — Rare Earths.

### smco_bonded_magnets
- **id**: `theme:smco_bonded_magnets`
- **name_en**: SmCo & bonded magnet manufacturing · **name_zh**: 钐钴与粘结磁体
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:rare_earth_processing_magnets`
- **defining_activities**: sintering samarium-cobalt magnet grades for high-temperature service; melt-spinning NdFeB ribbons and compounding bonded-magnet pellets; injection- and compression-moulding bonded parts; coating and magnetising finished magnets.
- **distinct_from**: `theme:ndfeb_permanent_magnets` (sintered NdFeB products vs SmCo high-temperature and polymer-bonded mechanisms) — alternative magnet mechanisms sharing the chain but with distinct metallurgy.
- **exclusions**: sintered NdFeB production, magnet assemblies for end devices.
- **china_relevance**: high — 钐钴与粘结磁体是国产磁材出口的重要品类， servo/车规高低温场景需求增长。
- **confidence**: high
- **sources**: (1) 中国电子元件行业协会磁性材料与器件分会行业资料; (2) USGS, *Mineral Commodity Summaries* — Rare Earths (magnet end-use data).

---

## theme:copper_steel_electrify — Copper, Steel & Electrification

Existing rows stay as-is: `theme:copper_mining`, `theme:refined_copper`, `theme:structural_steel_electrification`, `theme:copper_wire_cable`, sub-theme `theme:copper_supply_chain`. The 14 rows below add the conversion and fabrication stages the current set skips: hydrometallurgical and secondary copper routes, mill products, winding wire and smelter by-products on the copper side; the ore-to-aggregate stage and four ironmaking/steelmaking process routes on the steel side; plus the electrical-steel material chain and three enabler/downstream layers (mine electrification, service centres, plant equipment).

**Sub-theme grouping.** `theme:copper_extraction_fabrication` (midstream) groups everything between mine and cable: leach cathode, secondary smelting, mill products, winding wire and anode-slime recovery. `theme:iron_steel_process_routes` (midstream) groups conversion mechanisms — pellets feed, hydrogen DRI, scrap EAF and BF-BOF retrofit — as process families rather than demand rows. `theme:electrical_steel_materials` (midstream) isolates the magnetic-core material chain (GOES/NOES strip and laminated cores) from finished transformers, which already live under the grid theme. The three remaining rows (mine-fleet electrification, service centres, metallurgical equipment) attach directly to the theme as enabler/downstream layers.

**Theme-tier candidates (prose only).** The green-iron/hydrogen-DRI cluster is now mechanistically distinct enough that a seat-level `green_steel` theme-tier candidate could split decarbonisation routes away from the volume metal narrative; likewise `electrical_steel_materials` could graduate to a theme if the seat wants a dedicated transformer/motor material-chain view.

### copper_solvent_extraction_ew
- **id**: `theme:copper_solvent_extraction_ew`
- **name_en**: Copper SX-EW cathode · **name_zh**: 湿法炼铜（萃取电积）
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:copper_extraction_fabrication`
- **defining_activities**: heap- and dump-leaching oxide and secondary-sulphide ores; extracting copper from pregnant liquor in SX plants; electrowinning LME-grade cathode; managing raffinate and acid balance.
- **distinct_from**: `theme:refined_copper` (concentrate smelting/converting route) and `theme:copper_mining` (ore/concentrate stage) — this row is the hydrometallurgical leach-to-cathode route.
- **exclusions**: concentrate flash smelting, wire-rod mills.
- **china_relevance**: medium — 国内湿法铜以境外矿山与国内氧化矿浸出为主，占精炼铜供给比例低于火法。
- **confidence**: high
- **sources**: (1) International Copper Study Group (ICSG), *The World Copper Factbook*; (2) USGS, *Mineral Commodity Summaries* — Copper.

### secondary_copper_smelting
- **id**: `theme:secondary_copper_smelting`
- **name_en**: Secondary copper & scrap smelting · **name_zh**: 再生铜冶炼
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:copper_extraction_fabrication`
- **defining_activities**: collecting and sorting copper scrap by grade; smelting and fire-refining scrap into alloys and cathode; operating anode-refining loops for recycled feed; certifying recycled content.
- **distinct_from**: `theme:refined_copper` (primary ore-based refining) and `theme:copper_solvent_extraction_ew` (leach feed vs scrap feed) — this row is the recycled-feed smelting route.
- **exclusions**: raw-scrap trading without smelting, primary concentrate smelters.
- **china_relevance**: high — 再生铜是国内铜供给的重要补充，废铜进口标准与再生铜杆产能集中。
- **confidence**: high
- **sources**: (1) Bureau of International Recycling (BIR) copper-recycling publications; (2) 中国有色金属工业协会再生金属分会行业资料; (3) ICSG, *The World Copper Factbook*.

### copper_mill_products
- **id**: `theme:copper_mill_products`
- **name_en**: Copper rod, tube & alloy mill products · **name_zh**: 铜杆管带与铜合金加工材
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:copper_extraction_fabrication`
- **defining_activities**: continuous-casting and rolling copper rod; extruding and drawing tube and pipe; rolling strip, sheet and foil stock; alloying and finishing brass and bronze mill shapes.
- **distinct_from**: `theme:copper_wire_cable` (insulated wire/cable fabrication) — this row is semi-finished bare mill products before insulation; and from `theme:magnet_winding_wire` (enamelled winding conductor).
- **exclusions**: insulated cable manufacture, finished busbar assembly.
- **china_relevance**: high — 铜加工材是国产化程度高的中间材料层，铜杆/铜管产能规模全球最大。
- **confidence**: high
- **sources**: (1) Copper Development Association (CDA) technical publications; (2) 中国有色金属加工工业协会行业资料.

### magnet_winding_wire
- **id**: `theme:magnet_winding_wire`
- **name_en**: Magnet & winding wire · **name_zh**: 电磁线与绕组线
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:copper_extraction_fabrication`
- **defining_activities**: drawing rod to fine and ultra-fine wire; applying enamel, film and paper insulation; producing rectangular and profiled winding conductors for motors and transformers; qualifying thermal-class performance.
- **distinct_from**: `theme:copper_wire_cable` (power cable products) and `theme:copper_mill_products` (bare shapes) — this row is the enamelled conductor conversion feeding motors, generators and transformer cores.
- **exclusions**: power transmission cable, bare busbar.
- **china_relevance**: high — 电磁线是电机与变压器核心配套材料，新能源车驱动电机用扁线是主要扩产方向。
- **confidence**: high
- **sources**: (1) IEC Technical Committee 55 (winding wires) standards family; (2) NEMA magnet-wire standards (MW series).

### copper_byproduct_refining
- **id**: `theme:copper_byproduct_refining`
- **name_en**: Copper smelter by-product recovery · **name_zh**: 铜阳极泥与冶炼副产品回收
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:copper_extraction_fabrication`
- **defining_activities**: processing anode slimes for selenium, tellurium and precious metals; capturing sulphur dioxide as sulphuric acid; recovering bismuth, nickel and platinum-group values; valorising smelter dusts.
- **distinct_from**: `theme:secondary_copper_smelting` (scrap feed vs minor-metal recovery from primary smelting residues) — distinct recovery mechanism at the same chain stage.
- **exclusions**: dedicated precious-metal refineries without copper-smelter linkage.
- **china_relevance**: high — 铜冶炼副产品（硫酸、硒碲、金银）是冶炼企业重要利润与战略材料来源。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Selenium; Tellurium; (2) ICSG, *The World Copper Factbook* (by-products coverage).

### iron_ore_beneficiation_pellets
- **id**: `theme:iron_ore_beneficiation_pellets`
- **name_en**: Iron ore beneficiation & pelletizing · **name_zh**: 铁矿石采选与球团
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:iron_steel_process_routes`
- **defining_activities**: mining and concentrating iron ore; grinding and beneficiating to grade; balling and indurating pellets for blast-furnace and direct-reduction feed; managing DR-grade pellet specifications.
- **distinct_from**: `theme:structural_steel_electrification` (downstream plate demand) — this row is the ore-to-aggregate feed stage upstream of every ironmaking route.
- **exclusions**: sinter plants inside integrated mills, scrap collection.
- **china_relevance**: high — 国内铁矿采选与球团保障能力建设是资源安全政策重点，DR级球团需求增长。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Iron Ore; (2) 中国钢铁工业协会行业统计资料; (3) World Steel Association, *World Steel in Figures*.

### hydrogen_dri_steelmaking
- **id**: `theme:hydrogen_dri_steelmaking`
- **name_en**: Hydrogen-based DRI & green ironmaking · **name_zh**: 氢冶金与直接还原铁
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:iron_steel_process_routes`
- **defining_activities**: running gas-based direct-reduction shaft furnaces; converting feed to hydrogen-based reduction; melting DRI in EAFs; certifying low-carbon hot metal and green-steel grades.
- **distinct_from**: `theme:eaf_scrap_steelmaking` (recycled feed vs virgin iron units) and `theme:bf_bof_low_carbon_retrofit` (route replacement vs retrofit) — this row is the new green-ironmaking route.
- **exclusions**: conventional BF-BOF operation, scrap-only EAF.
- **china_relevance**: high — 氢冶金示范工程与富氢碳循环高炉是国内钢铁低碳化的两条主线。
- **confidence**: high
- **sources**: (1) IEA, *Iron and Steel Technology Roadmap*; (2) IEA, *Global Hydrogen Review*; (3) World Steel Association climate-action publications.

### eaf_scrap_steelmaking
- **id**: `theme:eaf_scrap_steelmaking`
- **name_en**: Scrap-based EAF steelmaking · **name_zh**: 电炉短流程炼钢
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:iron_steel_process_routes`
- **defining_activities**: sourcing, grading and shredding ferrous scrap; melting in electric-arc furnaces; secondary metallurgy and continuous casting of EAF grades; operating short-route mini-mills.
- **distinct_from**: `theme:hydrogen_dri_steelmaking` (virgin feed) and `theme:bf_bof_low_carbon_retrofit` (integrated route) — this row is the recycled-feed short route.
- **exclusions**: scrap trading without melting, ironmaking from ore.
- **china_relevance**: high — 电炉短流程比例提升是国内钢铁结构调整目标，废钢加工配送体系配套发展。
- **confidence**: high
- **sources**: (1) World Steel Association, *Sustainability Indicators*; (2) 中国废钢铁应用协会行业资料.

### bf_bof_low_carbon_retrofit
- **id**: `theme:bf_bof_low_carbon_retrofit`
- **name_en**: Integrated BF-BOF decarbonization & CCUS · **name_zh**: 长流程低碳化与碳捕集改造
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:iron_steel_process_routes`
- **defining_activities**: recycling top gas and recovering waste heat; enriching blast furnaces with hydrogen-bearing injectants; retrofitting carbon capture on flue lines; upgrading process-control for abated integrated operation.
- **distinct_from**: `theme:hydrogen_dri_steelmaking` and `theme:eaf_scrap_steelmaking` (route replacement vs incremental retrofit of the existing integrated fleet).
- **exclusions**: greenfield DRI/EAF plants, carbon-capture in cement.
- **china_relevance**: high — 国内长流程产能占比高，超低排放改造与碳捕集示范决定行业减排路径。
- **confidence**: high
- **sources**: (1) IEA, *Iron and Steel Technology Roadmap*; (2) Global CCS Institute, *Global Status of CCS*.

### electrical_steel_goes_noes
- **id**: `theme:electrical_steel_goes_noes`
- **name_en**: Electrical steel (GOES/NOES) · **name_zh**: 电工钢（取向与无取向硅钢）
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:electrical_steel_materials`
- **defining_activities**: casting and rolling silicon-alloyed strip with grain-oriented or non-oriented textures; applying insulating coatings; qualifying core-loss and permeability grades; supplying transformer and motor laminators.
- **distinct_from**: `theme:structural_steel_electrification` (construction plate) and `theme:transformer_core_laminations` (strip supply vs core stamping) — this row is the magnetic-alloy steel product itself.
- **exclusions**: carbon steel plate, finished transformer manufacturing.
- **china_relevance**: high — 取向硅钢与高牌号无取向硅钢是特高压与新能源车电机的关键材料，国产产能扩张快。
- **confidence**: high
- **sources**: (1) IEC 60404 magnetic-materials standards family; (2) Association for Iron & Steel Technology (AIST) publications; (3) 中国钢铁工业协会行业统计资料.

### transformer_core_laminations
- **id**: `theme:transformer_core_laminations`
- **name_en**: Transformer core lamination processing · **name_zh**: 变压器铁芯叠片加工
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:electrical_steel_materials`
- **defining_activities**: slitting and cut-to-length electrical-steel strip; stamping or laser-cutting laminations; winding and annealing wound cores; stacking and clamping cores for transformer makers.
- **distinct_from**: `theme:hv_transformers_switchgear` (finished transformers under the grid/data-centre themes) — this row is the material-conversion step feeding them, distinct from OEM assembly.
- **exclusions**: transformer winding and assembly, coil insulation systems.
- **china_relevance**: high — 铁芯加工配套特高压变压器与配电变压器需求，自动化叠片产线扩张明显。
- **confidence**: high
- **sources**: (1) IEC 60404 magnetic-materials standards family; (2) 中国电器工业协会行业资料.

### mining_fleet_electrification
- **id**: `theme:mining_fleet_electrification`
- **name_en**: Mine fleet electrification · **name_zh**: 矿山运输装备电动化
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: supplying battery-electric haul trucks and loaders; installing trolley-assist lines on ramps; deploying mine charging and battery-swap infrastructure; integrating site microgrids for electric fleets.
- **distinct_from**: `theme:copper_mining` (ore output) — this row is the equipment/powertrain layer serving mines, an enabler of production rather than the mineral itself.
- **exclusions**: ore mining operations, general construction machinery.
- **china_relevance**: high — 矿卡电动化与换电重卡在露天煤矿和金属矿山加速渗透，国内厂商率先规模应用。
- **confidence**: high
- **sources**: (1) International Council on Mining and Metals (ICMM) innovation and decarbonisation publications; (2) 中国矿业联合会行业资料.

### steel_service_centers
- **id**: `theme:steel_service_centers`
- **name_en**: Steel processing & distribution service centers · **name_zh**: 钢材加工配送
- **value_chain_position**: downstream · **parent_sub_theme**: none
- **defining_activities**: slitting, blanking and cut-to-length processing mill coil; levelling plate and providing just-in-time supply; managing inventory risk for fabricators; tailoring grades and dimensions to OEM schedules.
- **distinct_from**: `theme:structural_steel_electrification` (steel products/demand) — this row is the processing-distribution layer between mills and fabricators.
- **exclusions**: steelmaking, fabrication of finished structures.
- **china_relevance**: high — 钢材加工配送中心连接钢厂与制造业终端，是钢材流通供应链的主要组织形式。
- **confidence**: high
- **sources**: (1) World Steel Association, *World Steel in Figures* (value-chain context); (2) 中国金属材料流通协会行业资料.

### metallurgical_equipment_casters
- **id**: `theme:metallurgical_equipment_casters`
- **name_en**: Metallurgical plant equipment & continuous casting · **name_zh**: 冶金成套装备与连铸连轧
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: engineering and building continuous-casting machines; supplying rolling mills, reheating furnaces and electric furnaces; retrofitting plant automation and secondary-cooling systems; commissioning turnkey steel-plant lines.
- **distinct_from**: `theme:steel_service_centers` (distribution) and the steel-product rows — this row is the capital-equipment layer supplying steel plants.
- **exclusions**: mining equipment, finished steel trading.
- **china_relevance**: high — 冶金成套装备国产化程度高，连铸连轧产线出口与国内改造需求并存。
- **confidence**: high
- **sources**: (1) Association for Iron & Steel Technology (AIST) equipment publications; (2) 中国重型机械工业协会行业资料.

---

## theme:ag_fertilizer — Agriculture & Fertilizer

Existing rows stay as-is: `theme:nitrogen_fertilizer_production` (conventional Haber-Bosch nitrogen), `theme:potash_phosphate_nutrients` (finished potash/phosphate nutrient products), `theme:precision_agriculture_platforms` (agronomic data platforms). The 13 rows below complete the chain: the upstream ore/acid/ammonia feedstock stage, the formulated product layer (compound, controlled-release, water-soluble, biological, micronutrient, recovered-organic), and the downstream energy, industrial and services extensions (ammonia fuel, urea derivatives, soil testing, distribution).

**Sub-theme grouping.** `theme:fertilizer_upstream_feedstocks` (upstream) groups the feed stages upstream of finished nutrients — phosphate rock mining, sulphur/sulphuric acid, potash extraction and electrolytic ammonia — each mechanism-distinct from the nutrient-product rows. `theme:compound_specialty_fertilizers` (midstream) groups the formulation layer that turns single nutrients into differentiated products: NPK compounds, controlled-release, water-soluble, biological and micronutrient lines plus circular organic recovery. The remaining four rows (ammonia fuel logistics, urea derivatives, soil-testing services, and — under the upstream sub — green ammonia) attach where their chain position dictates; none re-describes an existing row.

**Theme-tier candidates (prose only).** `ammonia_energy` is a plausible future theme if the seat wants the energy-carrier chain (bunkering, cracking, co-firing) separated from fertilizer; `crop_protection` is an adjacent value chain deliberately not minted here to keep the fertilizer theme chemistry-scoped.

### phosphate_rock_mining
- **id**: `theme:phosphate_rock_mining`
- **name_en**: Phosphate rock mining & beneficiation · **name_zh**: 磷矿采选与选矿
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:fertilizer_upstream_feedstocks`
- **defining_activities**: mining sedimentary and igneous phosphate ore; washing, flotation-beneficiating and drying rock; upgrading P2O5 grades; supplying rock to phosphoric-acid and elemental-phosphorus plants.
- **distinct_from**: `theme:potash_phosphate_nutrients` (finished DAP/MAP/TSP nutrient products) — this row is the ore/beneficiation stage feeding them.
- **exclusions**: phosphoric-acid and granulation plants, potash mining.
- **china_relevance**: high — 磷矿是国家战略矿产资源，采选产能集中与磷石膏治理约束供给。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Phosphate Rock; (2) 中国磷复肥工业协会行业资料; (3) FAO, *Current world fertilizer trends and outlook*.

### sulphur_sulphuric_acid
- **id**: `theme:sulphur_sulphuric_acid`
- **name_en**: Sulphur & sulphuric acid intermediates · **name_zh**: 硫磺与硫酸中间体
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:fertilizer_upstream_feedstocks`
- **defining_activities**: handling and storing refinery-recovered sulphur; burning sulphur and treating smelter off-gas to acid; supplying acid to phosphoric-acid plants; balancing acid logistics between smelters and fertilizer producers.
- **distinct_from**: `theme:phosphate_rock_mining` (ore stage) — this row is the acid intermediate consumed to digest that ore into phosphoric acid.
- **exclusions**: downstream NPK granulation, copper smelting itself.
- **china_relevance**: high — 冶炼酸与硫磺制酸双轨供给磷肥体系，硫磺进口依存度高。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Sulfur; (2) International Fertilizer Association (IFA) sulphur/acid trade statistics.

### potash_mining_solutions
- **id**: `theme:potash_mining_solutions`
- **name_en**: Potash mining & solution extraction · **name_zh**: 钾盐开采与溶液采矿
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:fertilizer_upstream_feedstocks`
- **defining_activities**: underground-room mining of sylvinite; solution-mining salt bodies through injection wells; crystallising MOP/SOP from brines; operating solar-evaporation pond systems.
- **distinct_from**: `theme:potash_phosphate_nutrients` (finished nutrient products) — this row is the extraction/first-crystallisation stage with its distinct mining mechanisms.
- **exclusions**: granulation and blending of finished fertilizers.
- **china_relevance**: high — 钾盐对外依存度高，国内盐湖与深部钾盐勘查开发是保供重点。
- **confidence**: high
- **sources**: (1) USGS, *Mineral Commodity Summaries* — Potash; (2) 中国无机盐工业协会钾盐钾肥分会行业资料; (3) FAO fertilizer outlook reports.

### green_ammonia_synthesis
- **id**: `theme:green_ammonia_synthesis`
- **name_en**: Green ammonia & electrolytic nitrogen · **name_zh**: 绿氨与电解水制氮
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:fertilizer_upstream_feedstocks`
- **defining_activities**: electrolyzing water for hydrogen feed; synthesising ammonia on renewable or abated hydrogen; flexibly operating Haber-Bosch loops against variable power; certifying low-carbon ammonia molecules.
- **distinct_from**: `theme:nitrogen_fertilizer_production` (conventional gas/coal Haber-Bosch) — this row is the low-carbon production route of the same molecule.
- **exclusions**: fossil-based ammonia capacity, ammonia shipping/bunkering.
- **china_relevance**: high — 风光制氢合成绿氨示范项目与氮肥企业绿色转型并进，出口氨能基地规划多。
- **confidence**: high
- **sources**: (1) IEA, *Ammonia Technology Roadmap*; (2) 中国氮肥工业协会行业资料; (3) IRENA renewable-ammonia outlooks.

### ammonia_fuel_logistics
- **id**: `theme:ammonia_fuel_logistics`
- **name_en**: Ammonia fuel storage & marine bunkering · **name_zh**: 氨燃料储运与船用加注
- **value_chain_position**: downstream · **parent_sub_theme**: none
- **defining_activities**: siting refrigerated ammonia terminals; operating ammonia-carrier logistics and custody transfer; developing marine bunkering protocols and safety cases; supplying co-firing volumes to power and shipping.
- **distinct_from**: `theme:green_ammonia_synthesis` (synthesis stage) and `theme:nitrogen_fertilizer_production` (agricultural use) — this row is the downstream energy-carrier use of the ammonia chain.
- **exclusions**: fertilizer application, ammonia synthesis plants.
- **china_relevance**: medium — 国内港口绿色氨加注与航运脱碳路径仍在标准与试点阶段。
- **confidence**: medium
- **sources**: (1) IMO 2023 GHG Strategy (regulator classification); (2) DNV, *Maritime Forecast to 2050*; (3) IEA, *Ammonia Technology Roadmap*.

### urea_downstream_derivatives
- **id**: `theme:urea_downstream_derivatives`
- **name_en**: Urea downstream derivatives · **name_zh**: 尿素深加工（车用尿素与三聚氰胺）
- **value_chain_position**: downstream · **parent_sub_theme**: none
- **defining_activities**: blending diesel exhaust fluid to specification; producing melamine and urea-formaldehyde resins; converting urea to adhesives and industrial inputs; managing NOx-reagent distribution networks.
- **distinct_from**: `theme:nitrogen_fertilizer_production` (fertilizer-grade urea) — this row is the industrial-derivative chain off the same urea stream.
- **exclusions**: agricultural urea granulation, ammonia synthesis.
- **china_relevance**: high — 车用尿素与三聚氰胺是国内尿素深加工主要方向，国六排放标准带动DEF放量。
- **confidence**: high
- **sources**: (1) ISO 22241 (diesel-engine NOx-reduction agent AUS 32) standard series; (2) International Fertilizer Association (IFA) nitrogen-product statistics.

### npk_compound_blending
- **id**: `theme:npk_compound_blending`
- **name_en**: Compound NPK & bulk blending · **name_zh**: 复合肥与掺混肥
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:compound_specialty_fertilizers`
- **defining_activities**: granulating compound NPK grades (DAP/MAP/NPK towers); bulk-blending single-nutrient materials to prescription; tailoring formulas to soil-test recommendations; distributing regionally branded grades.
- **distinct_from**: `theme:potash_phosphate_nutrients` and `theme:nitrogen_fertilizer_production` (single-nutrient commodity products) — this row is the multi-nutrient formulation layer.
- **exclusions**: single-nutrient production, controlled-release coating (separate row).
- **china_relevance**: high — 复合肥率是行业结构升级指标，配方肥与测土配方施肥行动直接拉动。
- **confidence**: high
- **sources**: (1) 中国磷复肥工业协会行业资料; (2) The Fertilizer Institute (TFI) industry statistics; (3) IFA production and trade statistics.

### controlled_release_fertilizers
- **id**: `theme:controlled_release_fertilizers`
- **name_en**: Controlled-release & stabilised fertilizers · **name_zh**: 控释肥与稳定性肥料
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:compound_specialty_fertilizers`
- **defining_activities**: coating granules with polymer or sulphur membranes; blending urease and nitrification inhibitors into stabilised grades; matching release curves to crop uptake; qualifying enhanced-efficiency claims.
- **distinct_from**: `theme:npk_compound_blending` (conventional soluble grades vs release-metered mechanisms) — mechanism-level differentiation of the formulated layer.
- **exclusions**: conventional NPK, organic manure products.
- **china_relevance**: high — 控释肥与稳定性肥料是化肥减量增效政策的主推品类。
- **confidence**: high
- **sources**: (1) 农业农村部《肥料登记管理办法》及登记分类 (regulator classification); (2) The Fertilizer Institute (TFI) enhanced-efficiency fertilizer publications.

### water_soluble_fertigation
- **id**: `theme:water_soluble_fertigation`
- **name_en**: Water-soluble fertilizers & fertigation · **name_zh**: 水溶肥与水肥一体化
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:compound_specialty_fertilizers`
- **defining_activities**: producing fully water-soluble NPK and mono-ammonium/urea-phosphate grades; formulating chelated micronutrient liquids; deploying fertigation programs with drip systems; calibrating injection ratios by growth stage.
- **distinct_from**: `theme:npk_compound_blending` (field-applied granular vs irrigation-integrated soluble grades).
- **exclusions**: drip-hardware manufacturing, granular fertilizer.
- **china_relevance**: high — 水肥一体化在设施农业与高标准农田建设中快速普及，水溶肥是配套投入品。
- **confidence**: high
- **sources**: (1) 全国农业技术推广服务中心水肥一体化技术指导资料; (2) IFA specialty-fertilizer product statistics.

### biofertilizers_biostimulants
- **id**: `theme:biofertilizers_biostimulants`
- **name_en**: Biofertilizers & biostimulants · **name_zh**: 生物肥料与生物刺激素
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:compound_specialty_fertilizers`
- **defining_activities**: fermenting rhizobia, bacillus and mycorrhizal inoculants; formulating seaweed-, humic- and peptide-based biostimulants; registering products under fertilizer or biostimulant categories; running on-farm efficacy trials.
- **distinct_from**: `theme:npk_compound_blending` (mineral nutrient products vs biological-mechanism products) — nutrient supply or stress tolerance through biological action.
- **exclusions**: conventional mineral fertilizers, crop-protection pesticides.
- **china_relevance**: medium-high — 微生物菌剂登记品类增长快，生物刺激素监管归类仍在完善。
- **confidence**: medium
- **sources**: (1) European Biostimulants Industry Council (EBIC) definitions and industry data; (2) 农业农村部肥料登记品类 (regulator classification).

### micronutrients_soil_conditioners
- **id**: `theme:micronutrients_soil_conditioners`
- **name_en**: Crop micronutrients & soil conditioners · **name_zh**: 中微量元素肥料与土壤调理剂
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:compound_specialty_fertilizers`
- **defining_activities**: producing zinc, boron, manganese and iron fertilizer grades; chelating trace elements for availability; supplying gypsum, lime and silicate conditioners; remediating acidic, saline and sodic soils.
- **distinct_from**: `theme:npk_compound_blending` (macronutrient vs secondary/micronutrient and amendment function).
- **exclusions**: NPK macronutrients, biological inoculants.
- **china_relevance**: high — 中微量元素缺乏与土壤酸化调理是耕地质量提升行动的重点。
- **confidence**: high
- **sources**: (1) 全国农业技术推广服务中心耕地质量与施肥指导资料; (2) FAO soil and fertilizer publications.

### organic_nutrient_recovery
- **id**: `theme:organic_nutrient_recovery`
- **name_en**: Organic waste nutrient recovery · **name_zh**: 有机废弃物养分回收
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:compound_specialty_fertilizers`
- **defining_activities**: processing manure, sludge and digestate; precipitating struvite and recovering phosphorus streams; composting and blending organic-mineral products; certifying recovered-nutrient content for fertilizer use.
- **distinct_from**: `theme:biofertilizers_biostimulants` (cultured biological products vs recovered nutrient products from waste streams) and from mineral synthesis rows — circular feedstock mechanism.
- **exclusions**: municipal solid-waste incineration, conventional manure spreading services.
- **china_relevance**: high — 畜禽粪污资源化利用与磷回收是农业面源治理政策重点。
- **confidence**: medium
- **sources**: (1) European Sustainable Phosphorus Platform (ESPP) nutrient-recovery publications; (2) FAO livestock-waste and nutrient-cycling reports.

### soil_testing_agronomy_services
- **id**: `theme:soil_testing_agronomy_services`
- **name_en**: Soil testing & agronomy advisory services · **name_zh**: 土壤检测与农化服务
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: operating soil and tissue laboratories; profiling nutrients, pH and salinity; prescribing fertilization programs from test results; running field agronomy advisory and training.
- **distinct_from**: `theme:precision_agriculture_platforms` (software/data platforms) — this row is lab analytics plus human advisory, the service layer those platforms consume.
- **exclusions**: fertilizer products, remote-sensing software.
- **china_relevance**: high — 测土配方施肥实现县域全覆盖，农化服务网络是化肥企业标配能力。
- **confidence**: high
- **sources**: (1) American Society of Agronomy / Soil Science Society of America, North American Proficiency Testing (NAPT) program; (2) 全国农业技术推广服务中心测土配方施肥资料.

---

## theme:glp1_obesity — GLP-1 & Obesity

Existing rows stay as-is: `theme:glp1_incretin_therapies` (single-incretin injectable class), `theme:oral_glp1_formulations`, `theme:glp1_api_manufacturing` (GMP drug-substance capacity), `theme:cardiorenal_metabolic_indications`, `theme:fill_finish_delivery_devices`, sub-themes `theme:glp1_therapy_products` and `theme:glp1_supply_chain`. The 12 rows below widen the mechanism map: synthesis-chemistry and fermentation routes upstream of API capacity; multi-receptor, amylin and small-molecule mechanisms beyond the single-agonist class; and the care/ops ring — cold chain, clinics, surgery, nutrition, compounding, digital tools and sharps.

**Sub-theme grouping.** No new sub-themes are minted: the two existing sub-themes already cover products (`theme:glp1_therapy_products`) and supply chain (`theme:glp1_supply_chain`), and the six new midstream/upstream rows slot under them by mechanism; the six downstream/enabler rows (care programs, surgery, nutrition, compounding, digital titration, sharps) stand directly under the theme because they form the care-and-operations ring rather than either existing grouping.

**Theme-tier candidates (prose only).** If the seat later splits this theme, a `obesity_care_ecosystem`-class theme (clinics, surgery, nutrition, digital, waste services) would separate care delivery from the drug chain, and a `peptide_manufacturing_services`-class theme could carry the CDMO/reagent/fermentation supply stack across GLP-1 and wider peptide markets.

### peptide_sps_reagents
- **id**: `theme:peptide_sps_reagents`
- **name_en**: Peptide solid-phase synthesis reagents · **name_zh**: 多肽固相合成试剂
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:glp1_supply_chain`
- **defining_activities**: manufacturing protected amino-acid building blocks; producing resins, linkers and coupling reagents; supplying side-chain chemistry for ligation; qualifying GMP-usable synthesis inputs.
- **distinct_from**: `theme:glp1_api_manufacturing` (GMP drug-substance capacity) — this row is the synthesis-input chemistry layer upstream of that capacity.
- **exclusions**: finished API production, fill-finish.
- **china_relevance**: high — 国内多肽合成试剂与保护氨基酸供应链完备，固相合成耗材全球供给占比高。
- **confidence**: high
- **sources**: (1) American Peptide Society (symposium proceedings and industry resources); (2) 中国生化制药工业协会多肽药物行业资料.

### recombinant_peptide_fermentation
- **id**: `theme:recombinant_peptide_fermentation`
- **name_en**: Recombinant & fermentation peptide API · **name_zh**: 重组发酵法多肽原料药
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:glp1_supply_chain`
- **defining_activities**: engineering yeast and fungal expression strains; running fed-batch fermentation of peptide actives; purifying refolded secreted peptides; supplying biosynthetic-route drug substance at scale.
- **distinct_from**: `theme:peptide_sps_reagents` (chemical synthesis inputs) and `theme:glp1_api_manufacturing` (capacity framing) — this row is the biological production route itself.
- **exclusions**: synthetic-route API, mammalian-cell biologics outside incretins.
- **china_relevance**: medium — 发酵法GLP-1原料路径在国内产能布局加速，菌种与纯化是门槛。
- **confidence**: medium
- **sources**: (1) 中国医药生物技术协会行业资料; (2) *Journal of Pharmaceutical Sciences* (academic venue) on recombinant peptide manufacturing.

### multi_receptor_incretin_agonists
- **id**: `theme:multi_receptor_incretin_agonists`
- **name_en**: Multi-receptor incretin co-agonists · **name_zh**: 多重受体激动剂
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:glp1_therapy_products`
- **defining_activities**: developing GIP/GLP-1 and glucagon co-agonist molecules; running weight-efficacy and tolerability trials; manufacturing multi-agonist peptides; seeking label expansion across metabolic indications.
- **distinct_from**: `theme:glp1_incretin_therapies` (single GLP-1-receptor class) — this row is multi-receptor polypharmacology.
- **exclusions**: single-agonist incretins, non-incretin mechanisms.
- **china_relevance**: medium — 国内多靶点减重管线以跟随开发为主，临床推进速度快。
- **confidence**: high
- **sources**: (1) American Diabetes Association, *Standards of Care in Diabetes*; (2) Endocrine Society clinical practice guidance on obesity pharmacotherapy.

### amylin_cagri_analogues
- **id**: `theme:amylin_cagri_analogues`
- **name_en**: Amylin & CAGR receptor analogues · **name_zh**: 胰淀素类似物
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:glp1_therapy_products`
- **defining_activities**: developing amylin and calcitonin-receptor agonist analogues; characterising appetite and gastric-empting effects; combination dosing with incretins; establishing subcutaneous and alternative delivery.
- **distinct_from**: `theme:multi_receptor_incretin_agonists` (incretin polypharmacology vs non-incretin amylin pathway) — different receptor biology on the same therapy map.
- **exclusions**: incretin-based molecules, insulin therapy.
- **china_relevance**: medium — 胰淀素通路为国内减重管线新方向，多处于早期临床。
- **confidence**: medium
- **sources**: (1) Obesity Medicine Association clinical practice statements; (2) American Diabetes Association, *Standards of Care in Diabetes*.

### oral_small_molecule_obesity
- **id**: `theme:oral_small_molecule_obesity`
- **name_en**: Oral small-molecule obesity drugs · **name_zh**: 口服小分子减重药物
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:glp1_therapy_products`
- **defining_activities**: discovering small-molecule agonists of appetite-regulatory receptors; running dose-ranging obesity trials; scaling chemical manufacturing for oral candidates; pursuing convenience-driven prescribing.
- **distinct_from**: `theme:oral_glp1_formulations` (oral dosage forms of peptide GLP-1) — this row is small-molecule chemistry, a different modality.
- **exclusions**: peptide orals, injectables.
- **china_relevance**: medium — 国内口服小分子减重项目多为引进或跟随开发，商业化尚早。
- **confidence**: medium
- **sources**: (1) US FDA, CDER Novel Drug Approvals (regulator classification); (2) Endocrine Society obesity-treatment guidance.

### pharma_cold_chain_logistics
- **id**: `theme:pharma_cold_chain_logistics`
- **name_en**: Pharma cold-chain logistics · **name_zh**: 医药冷链物流
- **value_chain_position**: downstream · **parent_sub_theme**: `theme:glp1_supply_chain`
- **defining_activities**: operating 2–8°C storage and distribution networks; validating thermal packaging and lane qualifications; tracking temperature excursions end-to-end; running GDP-compliant last-mile for injectables.
- **distinct_from**: `theme:fill_finish_delivery_devices` (manufacturing) — this row is the distribution layer moving finished cold-chain product.
- **exclusions**: fill-finish plants, pharmacy retail.
- **china_relevance**: high — 医药冷链是疫苗与生物药流通的基础设施，GLP-1放量直接拉长冷链需求。
- **confidence**: high
- **sources**: (1) WHO, *Good distribution practices for pharmaceutical products* (Technical Report Series); (2) IATA CEIV Pharma certification program.

### obesity_care_programs
- **id**: `theme:obesity_care_programs`
- **name_en**: Obesity care & telehealth weight management · **name_zh**: 减重门诊与互联网体重管理
- **value_chain_position**: downstream · **parent_sub_theme**: none
- **defining_activities**: staffing obesity-medicine clinics; delivering telehealth prescribing and coaching; structuring multidisciplinary diet and exercise programs; measuring long-term outcomes for payers.
- **distinct_from**: `theme:glp1_incretin_therapies` (drug products) — this row is the care-delivery layer wrapping pharmacotherapy.
- **exclusions**: bariatric surgery, drug manufacturing.
- **china_relevance**: high — 《肥胖症诊疗指南（2024年版）》推动规范化减重门诊与多学科管理建设。
- **confidence**: high
- **sources**: (1) 国家卫生健康委《肥胖症诊疗指南（2024年版）》; (2) World Obesity Federation, *World Obesity Atlas*; (3) Obesity Medicine Association clinical practice statements.

### metabolic_bariatric_surgery
- **id**: `theme:metabolic_bariatric_surgery`
- **name_en**: Metabolic & bariatric surgery · **name_zh**: 减重代谢外科
- **value_chain_position**: downstream · **parent_sub_theme**: none
- **defining_activities**: performing sleeve gastrectomy and gastric bypass; running revision and conversion procedures; supplying stapling and energy platforms for bariatric teams; managing long-term nutritional follow-up.
- **distinct_from**: `theme:obesity_care_programs` (medical/behavioral care) — this row is procedural intervention with its device and perioperative chain.
- **exclusions**: pharmacotherapy, endoscopic obesity devices not yet in scope.
- **china_relevance**: medium-high — 减重代谢手术量随指南推广快速增长，腔镜耗材国产配套完善。
- **confidence**: high
- **sources**: (1) International Federation for the Surgery of Obesity and Metabolic Disorders (IFSO) guidelines; (2) American Society for Metabolic and Bariatric Surgery (ASMBS) standards.

### weight_management_nutrition
- **id**: `theme:weight_management_nutrition`
- **name_en**: Weight-management nutrition & meal replacement · **name_zh**: 体重管理营养与代餐食品
- **value_chain_position**: downstream · **parent_sub_theme**: none
- **defining_activities**: formulating meal-replacement and very-low-calorie products; producing high-protein and fortified diet foods; supporting pharmacotherapy-era nutrition protocols; distributing through supervised and retail channels.
- **distinct_from**: `theme:obesity_care_programs` (care services) — this row is the product layer consumed within those programs.
- **exclusions**: drugs, devices, general functional food without weight-management positioning.
- **china_relevance**: high — 体重管理营养与代餐是国内增速领先的食品品类，标准体系逐步完善。
- **confidence**: high
- **sources**: (1) 中国营养保健食品协会行业资料; (2) EU foods for special medical purposes / total diet replacement framework (regulator classification).

### compounded_peptide_supply
- **id**: `theme:compounded_peptide_supply`
- **name_en**: Compounded & alternate peptide supply · **name_zh**: 药房配制与替代供给
- **value_chain_position**: downstream · **parent_sub_theme**: none
- **defining_activities**: operating registered outsourcing facilities for sterile compounding; preparing shortage-listed GLP-1 preparations; sourcing compounded-grade actives; navigating policy transitions back to authorized supply.
- **distinct_from**: `theme:glp1_api_manufacturing` (innovator GMP supply) — this row is the regulated compounding channel that substitutes during shortages.
- **exclusions**: authorized generics, counterfeit supply.
- **china_relevance**: low — 配制供给是美国监管框架下的现象，国内无对应规模化业态。
- **confidence**: medium
- **sources**: (1) US FDA 503B outsourcing-facility framework (regulator classification); (2) Alliance for Pharmacy Compounding industry publications.

### digital_titration_adherence
- **id**: `theme:digital_titration_adherence`
- **name_en**: Digital titration & adherence programs · **name_zh**: 数字化滴定与依从管理
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: building dose-escalation guidance apps; tracking side effects and persistence; connecting patients to coaches and refill logistics; generating real-world adherence datasets.
- **distinct_from**: `theme:obesity_care_programs` (human care delivery) — this row is the software/digital layer enabling it.
- **exclusions**: clinical decision software for diagnosis, pharmacy dispensing.
- **china_relevance**: medium — 互联网医院随访问药与依从管理工具在减重领域起步。
- **confidence**: medium
- **sources**: (1) *Journal of Medical Internet Research* (academic venue) on digital adherence programs; (2) Obesity Medicine Association practice resources.

### sharps_waste_services
- **id**: `theme:sharps_waste_services`
- **name_en**: Sharps & injectable waste services · **name_zh**: 注射锐器与医疗废物服务
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: supplying puncture-resistant sharps containers; running mail-back and curbside collection for home injectors; autoclaving and incinerating biomedical waste; training patients on safe disposal.
- **distinct_from**: `theme:pharma_cold_chain_logistics` (inbound distribution vs post-use waste stream) — the after-use end of the injectable lifecycle.
- **exclusions**: hospital regulated-medical-waste contracts, recycling of non-medical waste.
- **china_relevance**: medium — 居家注射废物分类回收体系仍在建设中，一次性注射笔放量带来新需求。
- **confidence**: medium
- **sources**: (1) WHO, *Safe management of wastes from health-care activities*; (2) US OSHA Bloodborne Pathogens Standard (regulator classification).

---

## theme:medical_devices — Medical Devices

Existing rows stay as-is: `theme:medical_imaging`, `theme:remote_patient_monitoring`, `theme:surgical_implants_instruments`, `theme:surgical_robotics_systems` (shared with robotics), sub-theme `theme:ai_clinical_data_devices`. The 15 rows below map the therapy-side device tree: four interventional/active-implant classes, four hospital therapy-equipment classes, and the supply ring (biomaterials, contract manufacturing, sterilisation, home devices, dental, wound consumables, evidence services) that the existing implant/instrument and monitoring rows do not cover.

**Sub-theme grouping.** `theme:interventional_therapy_devices` (midstream) groups catheter-based and active implantable therapy systems — cardiovascular, neuro/peripheral, neuromodulation and ophthalmic — each modality-distinct from the open-surgical implants row. `theme:clinical_care_equipment` (midstream) groups hospital therapy-delivery equipment — respiratory/anesthesia, blood purification, infusion/oncology delivery and surgical energy — distinct from the existing monitoring and imaging modalities. The seven remaining rows attach directly to the theme: dental, wound consumables and home devices are device classes without a natural grouping above; biomaterials (upstream), contract manufacturing, sterilisation and evidence services are the supply ring (upstream/enabler).

**Theme-tier candidates (prose only).** A `minimally_invasive_therapy` theme-tier candidate could unite interventional devices with surgical energy and robotics; an `active_implantables` candidate could separate electroceutical systems from passive implants if the seat wants deeper granularity later.

### cardiovascular_interventional_devices
- **id**: `theme:cardiovascular_interventional_devices`
- **name_en**: Cardiovascular interventional devices · **name_zh**: 心血管介入器械
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:interventional_therapy_devices`
- **defining_activities**: designing coronary stents and drug-eluting systems; developing transcatheter structural-heart valves; producing balloons, guide catheters and delivery systems; supporting cath-lab procedural training.
- **distinct_from**: `theme:surgical_implants_instruments` (open-surgical implants) — this row is catheter-based interventional therapy devices.
- **exclusions**: imaging systems, open-heart surgical instrumentation.
- **china_relevance**: high — 心血管介入是国内高值耗材集采与国产替代的主战场，创新器械审批通道活跃。
- **confidence**: high
- **sources**: (1) US FDA CDRH product classification database (regulator classification); (2) 国家药品监督管理局《医疗器械分类目录》; (3) European Society of Cardiology clinical guidelines.

### neurovascular_peripheral_intervention
- **id**: `theme:neurovascular_peripheral_intervention`
- **name_en**: Neurovascular & peripheral intervention · **name_zh**: 神经与外周介入器械
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:interventional_therapy_devices`
- **defining_activities**: producing stroke thrombectomy devices; manufacturing aneurysm coils and flow diverters; developing peripheral stents and atherectomy systems; delivering stroke-network device programs.
- **distinct_from**: `theme:cardiovascular_interventional_devices` (coronary/structural-heart beds) — this row is the neuro and peripheral vascular subspecialty.
- **exclusions**: coronary devices, neurosurgical open instruments.
- **china_relevance**: high — 卒中中心建设带动取栓与动脉瘤介入器械放量，国产取栓支架品类快速获批。
- **confidence**: high
- **sources**: (1) US FDA CDRH product classification database; (2) Society for Vascular Surgery clinical practice guidelines.

### neuromodulation_implants
- **id**: `theme:neuromodulation_implants`
- **name_en**: Neuromodulation & active implants · **name_zh**: 神经调控与有源植入
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:interventional_therapy_devices`
- **defining_activities**: manufacturing implantable pulse generators; producing leads for spinal-cord, deep-brain, sacral and vagal stimulation; programming and remote-managing implanted systems; expanding into closed-loop sensing.
- **distinct_from**: `theme:surgical_implants_instruments` (passive implants) — this row is active electroceutical systems with electronics and therapy software.
- **exclusions**: cardiac pacemakers, passive orthopedic hardware.
- **china_relevance**: medium — 脊髓刺激与DBS国产获批品类增多，渗透率仍低于海外。
- **confidence**: high
- **sources**: (1) International Neuromodulation Society (INS) resources; (2) US FDA CDRH product classification database.

### ophthalmic_devices_iol
- **id**: `theme:ophthalmic_devices_iol`
- **name_en**: Ophthalmic devices & IOLs · **name_zh**: 眼科器械与人工晶状体
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:interventional_therapy_devices`
- **defining_activities**: manufacturing intraocular lenses including premium toric/multifocal optics; producing phaco handpieces and vitrectomy systems; supplying glaucoma drainage implants; running refractive-surgery device lines.
- **distinct_from**: `theme:surgical_implants_instruments` — this row is the ocular device class with optical implant design at its core.
- **exclusions**: vision-care contact lenses, ophthalmic drugs.
- **china_relevance**: high — 白内障手术量与人工晶体集采带动国产替代，高端晶体仍以进口为主。
- **confidence**: high
- **sources**: (1) ISO 11979 ophthalmic-implant standards series (Intraocular lenses); (2) US FDA CDRH ophthalmic product classification.

### respiratory_anesthesia_equipment
- **id**: `theme:respiratory_anesthesia_equipment`
- **name_en**: Respiratory & anesthesia equipment · **name_zh**: 呼吸与麻醉设备
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:clinical_care_equipment`
- **defining_activities**: manufacturing ICU and transport ventilators; producing anaesthesia machines and vaporiser systems; supplying humidification and airway-management products; servicing breathing-circuit consumables.
- **distinct_from**: `theme:remote_patient_monitoring` (monitoring) — this row is life-support therapy delivery equipment.
- **exclusions**: home sleep-apnea therapy (covered by home devices row), monitoring sensors.
- **china_relevance**: high — 国产呼吸机与麻醉机体系完整，出口与国内ICU建设共同拉动。
- **confidence**: high
- **sources**: (1) ISO 80601 respiratory-equipment standards series; (2) American Association for Respiratory Care (AARC) clinical resources.

### renal_dialysis_devices
- **id**: `theme:renal_dialysis_devices`
- **name_en**: Renal dialysis & blood purification devices · **name_zh**: 血液净化与透析设备
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:clinical_care_equipment`
- **defining_activities**: manufacturing haemodialysis machines and dialysers; producing peritoneal-dialysis cyclers and solutions; building water-treatment trains for dialysis units; operating CRRT blood-purification lines.
- **distinct_from**: `theme:remote_patient_monitoring` (monitoring) — this row is blood-purification therapy equipment.
- **exclusions**: renal drugs, dialysis clinic operations.
- **china_relevance**: high — 血液净化国产化率高，县域透析中心建设持续扩容。
- **confidence**: high
- **sources**: (1) European Renal Association clinical guidelines; (2) US FDA CDRH renal product classification.

### infusion_chemo_delivery_devices
- **id**: `theme:infusion_chemo_delivery_devices`
- **name_en**: Infusion & oncology delivery devices · **name_zh**: 静脉输注与化疗给药设备
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:clinical_care_equipment`
- **defining_activities**: manufacturing volumetric and syringe infusion pumps; producing elastomeric pumps and PCA sets; supplying closed-system drug-transfer devices for oncology; integrating smart-pump safety libraries.
- **distinct_from**: `theme:fill_finish_delivery_devices` (GLP-1 fill-finish and pen devices under the GLP-1 theme) — this row is hospital infusion/oncology delivery hardware.
- **exclusions**: pen injectors, IV fluid manufacture.
- **china_relevance**: high — 输注泵与化疗给药装置国产份额高，智慧输液管理升级带来更新需求。
- **confidence**: high
- **sources**: (1) US FDA infusion-pump guidance (regulator classification); (2) Institute for Safe Medication Practices (ISMP) safe-practice guidance.

### surgical_energy_endoscopy
- **id**: `theme:surgical_energy_endoscopy`
- **name_en**: Surgical energy & endoscopic instruments · **name_zh**: 外科能量与腔镜器械
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:clinical_care_equipment`
- **defining_activities**: producing electrosurgical and ultrasonic energy platforms; manufacturing staplers and endomechanical sets; supplying laparoscopic instruments and video endoscopes; advancing energy-adjunct vessel sealing.
- **distinct_from**: `theme:surgical_robotics_systems` (robotic platforms) — this row is handheld energy and mechanical instrumentation.
- **exclusions**: robot systems, open general instruments without energy/endoscopic scope.
- **china_relevance**: high — 微创手术量增长带动能量平台与吻合器需求，国产 stapler 竞争充分。
- **confidence**: high
- **sources**: (1) US FDA CDRH electrosurgical product classification; (2) Society of American Gastrointestinal and Endoscopic Surgeons (SAGES) guidelines.

### wound_care_advanced_dressings
- **id**: `theme:wound_care_advanced_dressings`
- **name_en**: Advanced wound care & surgical consumables · **name_zh**: 伤口护理与高端敷料
- **value_chain_position**: midstream · **parent_sub_theme**: none
- **defining_activities**: producing foam, alginate and hydrocolloid dressings; manufacturing negative-pressure-wound-therapy systems; supplying haemostats and sealants; running single-use sutures and trocar lines.
- **distinct_from**: `theme:surgical_implants_instruments` (implants/instruments) — this row is single-use consumable products for wound management.
- **exclusions**: implantable devices, pharmaceutical wound treatments.
- **china_relevance**: high — 高端敷料与NPWT国产替代推进，造口伤口护理市场扩容。
- **confidence**: high
- **sources**: (1) European Wound Management Association (EWMA) position documents; (2) US FDA CDRH wound-care product classification.

### dental_implant_equipment
- **id**: `theme:dental_implant_equipment`
- **name_en**: Dental implants & dental equipment · **name_zh**: 口腔种植与齿科设备
- **value_chain_position**: midstream · **parent_sub_theme**: none
- **defining_activities**: manufacturing dental implant systems and abutments; producing bone-graft and membrane materials; supplying CAD/CAM scanners and chairside milling; supporting clear-aligner and orthodontic device lines.
- **distinct_from**: `theme:surgical_implants_instruments` (body surgical implants) — this row is the oral restoration device class.
- **exclusions**: dental consumables retail, orthodontic services.
- **china_relevance**: high — 种植牙集采后放量，国产种植体与数字化齿科设备加速渗透。
- **confidence**: high
- **sources**: (1) FDI World Dental Federation industry resources; (2) US FDA CDRH dental product classification.

### medical_biomaterials_polymers
- **id**: `theme:medical_biomaterials_polymers`
- **name_en**: Medical-grade polymers & biomaterials · **name_zh**: 医用高分子与生物材料
- **value_chain_position**: upstream · **parent_sub_theme**: none
- **defining_activities**: producing medical-grade polymers (PEEK, UHMWPE, silicone, PVC/TPE); manufacturing nitinol and titanium-alloy stock for implants; developing resorbable polymers and hydrogels; qualifying materials under biocompatibility programs.
- **distinct_from**: all finished-device rows — this row is the input-material layer that device makers consume.
- **exclusions**: finished implants, packaging conversion.
- **china_relevance**: medium-high — 医用高分子原料长期依赖进口，国产聚醚醚酮与硅橡胶正在突破。
- **confidence**: high
- **sources**: (1) ISO 10993 biological-evaluation standards series; (2) ASTM Committee F04 on medical devices materials standards.

### device_contract_manufacturing
- **id**: `theme:device_contract_manufacturing`
- **name_en**: Device precision manufacturing & CMO · **name_zh**: 医疗器械精密加工与代工
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: precision-machining implant and instrument components; injection-moulding and extruding device polymers; assembling electronics modules under design transfer; running quality systems for OEM outsourcing.
- **distinct_from**: all OEM product-category rows — this row is the contract-manufacturing services layer behind them.
- **exclusions**: OEM brand products, component distribution only.
- **china_relevance**: high — 国内精密加工与注塑产能承接全球器械代工，质量体系认证完善。
- **confidence**: high
- **sources**: (1) ISO 13485 medical-device quality-management standard; (2) AdvaMed industry resources.

### sterilization_reprocessing
- **id**: `theme:sterilization_reprocessing`
- **name_en**: Sterilization & device reprocessing services · **name_zh**: 灭菌与器械再处理服务
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: operating ethylene-oxide and irradiation sterilisation plants; validating steam cycles for device makers; reprocessing eligible single-use devices; tracking instrument sterility with digital systems.
- **distinct_from**: `theme:device_contract_manufacturing` (production vs post-production services) — this row is the sterilisation/reprocessing service layer.
- **exclusions**: hospital central-sterile departments run by hospitals themselves, packaging manufacture.
- **china_relevance**: medium — 国内环氧乙烷灭菌产能集中，辐射灭菌与新监管下的再处理仍在发展。
- **confidence**: medium
- **sources**: (1) ISO 11135 / ISO 11137 sterilisation standards families; (2) Association for the Advancement of Medical Instrumentation (AAMI) sterilisation guidance; (3) US FDA reprocessing guidance.

### home_therapy_devices
- **id**: `theme:home_therapy_devices`
- **name_en**: Home therapy & self-care devices · **name_zh**: 家用治疗与居家护理设备
- **value_chain_position**: downstream · **parent_sub_theme**: none
- **defining_activities**: manufacturing CPAP and ventilator-support devices for home use; producing stationary and portable oxygen concentrators; supplying hearing aids and personal mobility devices; enabling home-infusion setups.
- **distinct_from**: `theme:remote_patient_monitoring` (connected monitoring) — this row is therapy hardware used at home; and from hospital equipment rows — different care setting and channel.
- **exclusions**: hospital therapy equipment, diagnostics self-tests.
- **china_relevance**: high — 居家呼吸治疗与助听器市场随老龄化扩容，家用无创通气国产份额提升。
- **confidence**: high
- **sources**: (1) US FDA home-use device guidance (regulator classification); (2) WHO, *Global Atlas of Medical Devices*.

### device_evidence_pm_services
- **id**: `theme:device_evidence_pm_services`
- **name_en**: Device clinical evidence & post-market services · **name_zh**: 器械临床证据与上市后监测服务
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: running device clinical investigations and registries; compiling clinical-evaluation reports under regulator rules; operating post-market surveillance and complaint analytics; supporting regulatory submissions across markets.
- **distinct_from**: `theme:device_contract_manufacturing` (physical supply vs evidence/quality services) — this row is the regulatory-evidence service layer.
- **exclusions**: drug CRO work, device manufacturing itself.
- **china_relevance**: medium — 创新器械临床评价与真实世界研究服务需求随审批升级增长。
- **confidence**: medium
- **sources**: (1) International Medical Device Regulators Forum (IMDRF) post-market guidance; (2) EU Medical Device Regulation (EU) 2017/745 clinical-evaluation requirements.

---

## theme:diagnostics_lifesci — Diagnostics & Life-Science Tools

Existing rows stay as-is: `theme:liquid_biopsy_assays`, `theme:genomic_sequencing` (NGS), `theme:proteomics_discovery_platforms`, `theme:life_science_lab_instruments`, `theme:diagnostic_reagents_kits`, sub-theme `theme:multi_omics_platforms`. The 15 rows below fill the routine and upstream layers the multi-omics view skips: five core-lab detection modalities (molecular, immuno/chemistry, clinical mass spec, POCT, flow cytometry), four upstream tool inputs (raw reagents, media/cell lines, gene synthesis, automation), two informatics/enabler rows, and four downstream service layers (ICL/central labs, companion diagnostics, newborn/population screening, trial biomarker services) plus digital pathology.

**Sub-theme grouping.** `theme:molecular_immuno_core_lab` (midstream) groups the routine detection modalities by chemistry and platform — beneath the discovery-omics layer. `theme:lifesci_upstream_tools` (upstream) groups the raw inputs and workflow infrastructure labs consume before any assay runs. `theme:diagnostics_services_icl` (downstream) groups the service operators who run tests, distinct from the assay and kit products that existing rows describe. `theme:lims_lab_informatics` and `theme:digital_pathology_ai` attach directly to the theme as informatics/enabler layers that serve all three groupings.

**Theme-tier candidates (prose only).** A `research_and_bioproduction_tools` theme-tier candidate could separate the life-science research-tools economy (upstream reagents, media, synthesis, automation) from clinical diagnostics; a `lab_services` candidate could do the same on the service side if ICL and CRO-adjacent testing keep expanding.

### pcr_molecular_diagnostics
- **id**: `theme:pcr_molecular_diagnostics`
- **name_en**: PCR & nucleic-acid molecular diagnostics · **name_zh**: 分子诊断与核酸检测
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:molecular_immuno_core_lab`
- **defining_activities**: developing real-time PCR and isothermal-amplification assays; manufacturing nucleic-acid extraction and amplification reagents; running infectious-disease and genetic panels; validating assays under laboratory standards.
- **distinct_from**: `theme:genomic_sequencing` (NGS platforms) — this row is targeted amplification testing, not sequencing.
- **exclusions**: sequencers, mass-spec panels.
- **china_relevance**: high — 分子诊断国产化率高，呼吸道多联检与肿瘤伴随场景扩容。
- **confidence**: high
- **sources**: (1) WHO, *Model List of Essential In Vitro Diagnostics*; (2) Clinical and Laboratory Standards Institute (CLSI) molecular-diagnostics standards.

### immunoassay_clinical_chemistry
- **id**: `theme:immunoassay_clinical_chemistry`
- **name_en**: Immunoassay & clinical chemistry systems · **name_zh**: 免疫诊断与生化检测
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:molecular_immuno_core_lab`
- **defining_activities**: manufacturing chemiluminescent immunoassay analysers; building clinical-chemistry reagent menus; operating high-throughput routine testing lines; managing assay traceability and calibration.
- **distinct_from**: `theme:diagnostic_reagents_kits` (kit trade line) — this row is the installed-system modality (analysers plus menus) behind routine testing.
- **exclusions**: molecular and mass-spec modalities, research-only instruments.
- **china_relevance**: high — 化学发光是国产替代主战场，传染病与激素检测量全球领先。
- **confidence**: high
- **sources**: (1) International Federation of Clinical Chemistry and Laboratory Medicine (IFCC) standards activities; (2) WHO, *Model List of Essential In Vitro Diagnostics*.

### clinical_mass_spectrometry
- **id**: `theme:clinical_mass_spectrometry`
- **name_en**: Clinical mass spectrometry · **name_zh**: 临床质谱检测
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:molecular_immuno_core_lab`
- **defining_activities**: deploying LC-MS/MS platforms for routine quantitation; validating clinical analyte panels (vitamin D, steroids, toxicology); producing kit-based sample preparation; standardising reference measurement procedures.
- **distinct_from**: `theme:proteomics_discovery_platforms` (research discovery) — this row is routine clinical quantitation by mass spec.
- **exclusions**: research proteomics, sequencing modalities.
- **china_relevance**: high — 临床质谱在国内第三方与医院实验室快速铺开，国产仪器注册加速。
- **confidence**: high
- **sources**: (1) CLSI clinical mass-spectrometry guidance; (2) Association for Diagnostics & Laboratory Medicine (ADLM, formerly AACC) resources.

### point_of_care_testing
- **id**: `theme:point_of_care_testing`
- **name_en**: Point-of-care testing · **name_zh**: 即时检测（POCT）
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:molecular_immuno_core_lab`
- **defining_activities**: manufacturing handheld and benchtop near-patient devices; producing single-use cartridges and strips; connecting POC results into hospital informatics; deploying testing in pharmacies and clinics.
- **distinct_from**: `theme:immunoassay_clinical_chemistry` (central-lab analysers) — this row is the decentralised site-of-care modality.
- **exclusions**: home self-test kits retail, central lab systems.
- **china_relevance**: high — POCT在急诊、基层与家庭场景扩张，国产快检平台成熟。
- **confidence**: high
- **sources**: (1) ISO 22870 point-of-care testing quality-competence standard; (2) WHO, *Model List of Essential In Vitro Diagnostics*.

### flow_cytometry_analysis
- **id**: `theme:flow_cytometry_analysis`
- **name_en**: Flow cytometry & cellular analysis · **name_zh**: 流式细胞分析
- **value_chain_position**: midstream · **parent_sub_theme**: `theme:molecular_immuno_core_lab`
- **defining_activities**: manufacturing analyzers and sorters; producing antibody panels for immunophenotyping; supporting cell-therapy potency QC; running minimal-residual-disease monitoring programs.
- **distinct_from**: `theme:life_science_lab_instruments` (general instruments) — this row is the cellular-analysis modality with its reagent ecosystem.
- **exclusions**: imaging cytometry, sequencing.
- **china_relevance**: high — 流式在临床免疫与细胞治疗质控中用量增长，国产仪器进入医院采购。
- **confidence**: high
- **sources**: (1) International Society for the Advancement of Cytometry (ISAC) standards and shared resources; (2) CLSI flow-cytometry guidelines.

### lifesci_raw_reagents
- **id**: `theme:lifesci_raw_reagents`
- **name_en**: Life-science raw reagents (enzymes & antibodies) · **name_zh**: 生命科学上游原料试剂
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:lifesci_upstream_tools`
- **defining_activities**: manufacturing recombinant enzymes and polymerases; producing primary and secondary antibodies; supplying probes, buffers and assay building blocks; qualifying raw materials for IVD production.
- **distinct_from**: `theme:diagnostic_reagents_kits` (finished kits) — this row is the upstream raw-material layer kit makers consume.
- **exclusions**: finished diagnostic kits, laboratory consumable plastics.
- **china_relevance**: high — 生命科学上游原料国产替代是产业链安全重点，酶与抗体品类扩张快。
- **confidence**: high
- **sources**: (1) NIST reference-material programs; (2) ATCC (American Type Culture Collection) biological-materials resources.

### cell_culture_media_celllines
- **id**: `theme:cell_culture_media_celllines`
- **name_en**: Cell-culture media & cell lines · **name_zh**: 细胞培养基与细胞系
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:lifesci_upstream_tools`
- **defining_activities**: formulating serum-free and chemically-defined media; producing sera and supplements; banking and authenticating cell lines; supplying bioproduction and research growth systems.
- **distinct_from**: `theme:lifesci_raw_reagents` (assay building blocks) — this row is the growth-system layer for living-cell work.
- **exclusions**: bioreactor hardware, finished biologics.
- **china_relevance**: medium-high — 无血清培养基与国产细胞库建设推进，生物药产能扩张拉动需求。
- **confidence**: medium
- **sources**: (1) ATCC cell-line and media resources; (2) 中国细胞生物学学会细胞培养行业标准活动.

### oligo_gene_synthesis
- **id**: `theme:oligo_gene_synthesis`
- **name_en**: Oligonucleotide & gene synthesis · **name_zh**: 寡核苷酸与基因合成
- **value_chain_position**: upstream · **parent_sub_theme**: `theme:lifesci_upstream_tools`
- **defining_activities**: synthesising custom primers, probes and oligos; assembling synthetic genes and pathways; scaling long-fragment DNA writing; screening orders under biosafety protocols.
- **distinct_from**: `theme:genomic_sequencing` (reading DNA vs writing DNA) — complementary but mechanistically opposite modality.
- **exclusions**: sequencing services, therapeutic oligo drug manufacture.
- **china_relevance**: high — 基因合成与引物探针产能集中国内，合成生物学应用拉动需求。
- **confidence**: high
- **sources**: (1) International Gene Synthesis Consortium (IGSC) harmonized screening protocol; (2) NIST reference materials and genome-reference programs.

### lab_automation_sample_prep
- **id**: `theme:lab_automation_sample_prep`
- **name_en**: Laboratory automation & sample preparation · **name_zh**: 实验室自动化与样本前处理
- **value_chain_position**: enabler · **parent_sub_theme**: `theme:lifesci_upstream_tools`
- **defining_activities**: building liquid-handling workstations; integrating robotic sample-prep lines; producing automation-optimised consumables; connecting instruments into walk-away workflows.
- **distinct_from**: `theme:life_science_lab_instruments` (individual instruments) — this row is integrated workflow automation across them.
- **exclusions**: informatics software (separate row), single analysers.
- **china_relevance**: medium-high — 检验科与药企实验室自动化改造需求上升，国产机械臂平台起步。
- **confidence**: medium
- **sources**: (1) Society for Laboratory Automation and Screening (SLAS) resources; (2) ISO 15189 medical-laboratory quality standard (workflow context).

### lims_lab_informatics
- **id**: `theme:lims_lab_informatics`
- **name_en**: LIMS & laboratory informatics · **name_zh**: 实验室信息化（LIMS）
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: deploying LIMS/ELN platforms; managing sample chain-of-custody data; integrating instruments via standards-based interfaces; supporting accreditation workflows and audit trails.
- **distinct_from**: `theme:lab_automation_sample_prep` (physical automation) — this row is the data/records informatics layer.
- **exclusions**: hospital HIS systems, physical robotic hardware.
- **china_relevance**: medium — 实验室信息国产化替代推进，医学实验室认可带动 LIMS 需求。
- **confidence**: medium
- **sources**: (1) ISO/IEC 17025 testing-laboratory competence standard; (2) SLAS informatics resources.

### icl_central_labs
- **id**: `theme:icl_central_labs`
- **name_en**: Independent clinical labs & central labs · **name_zh**: 独立医学实验室与中心实验室
- **value_chain_position**: downstream · **parent_sub_theme**: `theme:diagnostics_services_icl`
- **defining_activities**: operating regional testing networks under laboratory accreditation; running referred and specialty assays; servicing hospital outsourcing volume; supporting trial central-lab logistics.
- **distinct_from**: `theme:diagnostic_reagents_kits` (products) — this row is the service operators who run the tests.
- **exclusions**: hospital in-house labs, reagent manufacturing.
- **china_relevance**: high — 独立医学实验室网络覆盖广，区域检验与分级诊疗拉动外包。
- **confidence**: high
- **sources**: (1) US CMS Clinical Laboratory Improvement Amendments (CLIA) program; (2) CNAS-CL02 medical-laboratory accreditation (ISO 15189) in China.

### companion_diagnostics
- **id**: `theme:companion_diagnostics`
- **name_en**: Companion diagnostics · **name_zh**: 伴随诊断
- **value_chain_position**: downstream · **parent_sub_theme**: `theme:diagnostics_services_icl`
- **defining_activities**: co-developing assays with drug programs; seeking paired regulatory approvals; bridging assays across platforms; running therapy-selection testing programs.
- **distinct_from**: `theme:pcr_molecular_diagnostics` (general molecular testing) — this row is the therapy-coupled, co-approved assay class.
- **exclusions**: infectious-disease panels, standalone genetic tests.
- **china_relevance**: medium-high — 伴随诊断审评通道明确，肿瘤精准治疗放量带动检测。
- **confidence**: high
- **sources**: (1) US FDA–CDER/CBER/CDRH co-development of an in vitro companion diagnostic with a therapeutic product guidance; (2) Association for Molecular Pathology (AMP) practice resources.

### newborn_screening_programs
- **id**: `theme:newborn_screening_programs`
- **name_en**: Newborn screening & population programs · **name_zh**: 新生儿筛查与出生缺陷防控
- **value_chain_position**: downstream · **parent_sub_theme**: `theme:diagnostics_services_icl`
- **defining_activities**: running dried-blood-spot screening panels; operating program laboratories and follow-up; supplying screening reagents and MS/MS kits; expanding carrier and prenatal population programs.
- **distinct_from**: `theme:icl_central_labs` (general service network) — this row is public-health screening program content and delivery.
- **exclusions**: routine pediatric testing, therapeutic interventions.
- **china_relevance**: high — 新生儿疾病筛查纳入国家出生缺陷防控体系，覆盖率持续提升。
- **confidence**: high
- **sources**: (1) US Advisory Committee on Heritable Disorders in Newborns and Children, Recommended Uniform Screening Panel; (2) 国家卫生健康委《新生儿疾病筛查技术规范》.

### trial_biomarker_services
- **id**: `theme:trial_biomarker_services`
- **name_en**: Trial biomarker & bioanalytical services · **name_zh**: 临床试验生物标志物与生物分析服务
- **value_chain_position**: downstream · **parent_sub_theme**: `theme:diagnostics_services_icl`
- **defining_activities**: running sponsor bioanalytical assays under regulated method validation; managing trial biomarker endpoints and kits; performing pharmacogenomic and safety lab testing; supporting global specimen logistics.
- **distinct_from**: `theme:icl_central_labs` (routine patient testing) — this row is sponsor-facing trial-endpoint services.
- **exclusions**: routine clinical labs, preclinical discovery research.
- **china_relevance**: high — 国内创新药临床试验量全球领先，中心实验室与生物分析服务配套成熟。
- **confidence**: high
- **sources**: (1) ICH E15/E16 biomarker and genomic-sampling guidance; (2) Association for Diagnostics & Laboratory Medicine (ADLM) trial-lab resources.

### digital_pathology_ai
- **id**: `theme:digital_pathology_ai`
- **name_en**: Digital pathology & AI-assisted reads · **name_zh**: 数字病理与AI辅助判读
- **value_chain_position**: enabler · **parent_sub_theme**: none
- **defining_activities**: scanning glass slides to whole-slide images; building image-management and viewing systems; validating AI triage and quantification algorithms; enabling remote pathology consultation.
- **distinct_from**: `theme:medical_imaging` (radiology modalities) — this row is the pathology slide workflow and its informatics.
- **exclusions**: radiology PACS, conventional microscope hardware.
- **china_relevance**: medium — 数字病理远程会诊与AI辅助筛查在基层病理资源缺口下推进。
- **confidence**: medium
- **sources**: (1) College of American Pathologists (CAP) digital-pathology accreditation; (2) US FDA AI-enabled medical-device list (regulator classification).

---

## Method note

Sources are cited at organization/document level (industry associations, standards bodies, regulators, intergovernmental reports, academic venues) per the lane source standard; no long passages are reproduced. All rows are display vocabulary only — no weights, scores, ranks, or exposure figures; no issuer names, tickers, or membership claims of any kind. Value-chain positions are display attributes (`upstream|midstream|downstream|enabler`), not edges.

