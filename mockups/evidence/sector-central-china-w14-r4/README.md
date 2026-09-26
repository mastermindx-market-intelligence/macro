# W14 r4 — sector_central_china evidence matrix

Provenance: `capture_sha` == `1ee4ada3a1571ee70206c639911040ddc1ab2b72`. Rig: S1 fixture-render + real `body.page-sector-central`; `__skyDeck`; overlay hide `.rvx-aurora` / `.mx5-aurora` / `.sky-fx` / `#mmb-root` / `#mmb-boot` / `.aurora`; overlay column populated; computed-style text on every cell. Light forced via `data-theme="light"` on `<html>` (and `setTheme`). Never opted into `site/` or `data/`.

Generated `2026-09-11T09:50:06Z`.

## DARK TREATMENT

Command center. Luminance tiles (`--panel` / `--panel2`) on a deep canvas, hairline `--line`, instrument-calm, no glow. `.si-links` is one family of tagged chips on `--panel2`; `.skel-slot` is a quiet `--panel2` shimmer; `.mx-error button` is a `--panel2` chip. The Act-Now board and Explore table sit as inset instruments, not cards with drop shadow.

## LIGHT TREATMENT

Research workspace. White `--panel` paper, hairline `--line`, short cool shadow instead of glow. `.si-links a` pick up the desk-tile shadow already used by `.rvx-hero`; `.skel-slot` shimmer mixes `--text` into `--panel` (paper, not a dark wash); `.mx-error button` is paper with a warn-tinted hairline. Light Overview / Explore read as a cool canvas with white material, not a paled command center.

## Which mechanisms intentionally differ

Fill (luminance tile vs paper), depth (none vs short shadow), skeleton mix target (`--panel2` vs `--panel`). Shared: information architecture, component semantics, spacing/type scales, state meanings, EN/ZH dual-emit, density law, interaction. Token substitution alone is not the light design.

Reference: templates/sector_central_china.html.j2 W14 r2 chrome comment (lines ~130–142) plus the live light rules under `html[data-theme="light"] body.page-sector-central`.

## §9.13 landing table (P2a + r2 band note)

| Module | Landing | Receipt |
|---|---|---|
| `#si-explore` desk header (h2 + basket search + count) | L1 KEEP | rest + explore crops |
| 01 Performance table (TABLE_LIMIT=8, counted see-more) | L1 KEEP | `table8-*` |
| 02 Performance chart | L1 KEEP | explore tab crop |
| 03 Baskets by category (+#cards/#details) | L1 KEEP | explore tab crop |
| `.si-links` band (tagged links + LENS `?`) | L1 KEEP; r4 recaptures light-ZH + 390 | `silinks-*` |
| `#reversal-sleeve-card` | DEMOTE → one link-band entry `Reversal Sleeve → cn_reversal_sleeve.html` (both lanes); stats in LENS tip | `silinks-*` |
| `#sleeve-chip` | DEMOTE → same Reversal Sleeve link-band entry; `hidden` on the chip | P2a test + explore crop |
| `#entry-radar` | DEMOTE → `<details id="entry-radar-more">` "Entry radar" / 「入场雷达」 at tail of Performance-table (JS mount unchanged) | r2 `details-open-*` |
| `#forming-narratives` | DEMOTE → `<details id="forming-narratives-more">` "Forming narratives" / 「酝酿中的叙事」 at tail of Baskets-by-category | explore crop |
| Theme Rotation Desk / concentration / 5-day rotation / impulse | DEMOTE → compact `<details class="si-more">` (`si_explore_compact`) | r2 `details-open-*` |
| r2 `.si-links-note` (42ch prose) | DEMOTE into LENS tip; band is tagged links + `?` only | `silinks-*` |


## 8 full-page baselines (rest cells)

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `rest-dark-en-1440` | full-page-overview | dark | en | 1440 | `bbdd4036515971ed.png` | clean | MASTERMINDX United States ▾ China ▾ Hong Kong ▾ Canada ▾ International ▾ Other A |
| `rest-light-en-1440` | full-page-overview | light | en | 1440 | `74307b625d3d415f.png` | clean | MASTERMINDX United States ▾ China ▾ Hong Kong ▾ Canada ▾ International ▾ Other A |
| `rest-dark-zh-1440` | full-page-overview | dark | zh | 1440 | `59ed197fe60f78a4.png` | clean | MASTERMINDX 美国 ▾ 中国 ▾ 香港 ▾ 加拿大 ▾ 国际 ▾ 其他资产 ▾ 研究 ▾ NVDA 终端 总览 全景图谱 正在轮动 深入探索 子行业汇 |
| `rest-light-zh-1440` | full-page-overview | light | zh | 1440 | `ccb533ee712189ae.png` | clean | MASTERMINDX 美国 ▾ 中国 ▾ 香港 ▾ 加拿大 ▾ 国际 ▾ 其他资产 ▾ 研究 ▾ NVDA 终端 总览 全景图谱 正在轮动 深入探索 子行业汇 |
| `rest-dark-en-390` | full-page-overview | dark | en | 390 | `4ad4c0627ebda606.png` | clean | NVDA Terminal Overview The Map What's Moving Explore Confluence CHINA SECTOR INT |
| `rest-light-en-390` | full-page-overview | light | en | 390 | `080819371f6ab33c.png` | clean | NVDA Terminal Overview The Map What's Moving Explore Confluence CHINA SECTOR INT |
| `rest-dark-zh-390` | full-page-overview | dark | zh | 390 | `0c9152eec055dc18.png` | clean | NVDA 终端 总览 全景图谱 正在轮动 深入探索 子行业汇聚 中国行业情报 · 12 个主题 · 3 个分类 截至 2026-09-11 领涨格局 稳定 中国 |
| `rest-light-zh-390` | full-page-overview | light | zh | 390 | `bdd4b3daf383a4fa.png` | clean | NVDA 终端 总览 全景图谱 正在轮动 深入探索 子行业汇聚 中国行业情报 · 12 个主题 · 3 个分类 截至 2026-09-11 领涨格局 稳定 中国 |

## Per-fix crops

### (a) P0 CSI 300 frame

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `p0-dark-en-1440` | p0-versus-csi300 | dark | en | 1440 | `6d6b3dda26b70743.png` | clean | vs CSI 300 Weekly movers ranked by 5-day return versus CSI 300, plus the change  |
| `p0-dark-zh-1440` | p0-versus-csi300 | dark | zh | 1440 | `e27d0d1f12364564.png` | clean | 相对 沪深300 按相对沪深300的 5 日回报排序，并显示 20 日相对强度排名变化。 |
| `p0-light-en-1440` | p0-versus-csi300 | light | en | 1440 | `c5eb850a4002e1a4.png` | clean | vs CSI 300 Weekly movers ranked by 5-day return versus CSI 300, plus the change  |
| `p0-light-zh-1440` | p0-versus-csi300 | light | zh | 1440 | `d0e8975e756d035f.png` | clean | 相对 沪深300 按相对沪深300的 5 日回报排序，并显示 20 日相对强度排名变化。 |

### (b) Bottoming Watch

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `bottoming-dark-en-1440` | bottoming-watch | dark | en | 1440 | `3f6612ceb6f5d639.png` | clean | BOTTOMING WATCH (1) Beaten down, first signs of turning up — watch only Electron |
| `bottoming-dark-zh-1440` | bottoming-watch | dark | zh | 1440 | `53de4088907800b5.png` | clean | 洗盘观察 (1) 超跌初现回升迹象 — 仅观察 电子 低谷 ↗ 转强 -5.2% 63日相对强度 · 位置 12% |
| `bottoming-light-en-1440` | bottoming-watch | light | en | 1440 | `c18b6ef705532bfe.png` | clean | BOTTOMING WATCH (1) Beaten down, first signs of turning up — watch only Electron |
| `bottoming-light-zh-1440` | bottoming-watch | light | zh | 1440 | `8290b6df88140dc7.png` | clean | 洗盘观察 (1) 超跌初现回升迹象 — 仅观察 电子 低谷 ↗ 转强 -5.2% 63日相对强度 · 位置 12% |

### (c) Act-Now Early sign

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `actnow-dark-en-1440` | act-now-chip | dark | en | 1440 | `346e133c12309e08.png` | clean | REDUCE / AVOID (1) Trend weakening — consider trimming Agriculture EARLY SIGN |
| `actnow-dark-zh-1440` | act-now-chip | dark | zh | 1440 | `b854b052d03261bf.png` | clean | 减仓 / 回避 (1) 趋势转弱 — 考虑减仓 农林牧渔 初步迹象 |
| `actnow-light-en-1440` | act-now-chip | light | en | 1440 | `ee1915db7ab82daa.png` | clean | REDUCE / AVOID (1) Trend weakening — consider trimming Agriculture EARLY SIGN |
| `actnow-light-zh-1440` | act-now-chip | light | zh | 1440 | `80b78a0d4a5dd16f.png` | clean | 减仓 / 回避 (1) 趋势转弱 — 考虑减仓 农林牧渔 初步迹象 |

### (d) Explore tab post-P2a

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `explore-dark-en-1440` | explore-tab | dark | en | 1440 | `088ad35c8607372f.png` | clean | 12 baskets — every member, every record. ? Explore — every basket in depth The p |
| `explore-dark-zh-1440` | explore-tab | dark | zh | 1440 | `b05337e11e6eba71.png` | clean | 12 个篮子 — 全部成分，全部记录。 ? 深入探索 — 每个篮子的深读 表现一览、叠加图表，以及按类别分组的篮子。 12 / 12 个主题 01 表现一览 所 |
| `explore-light-en-1440` | explore-tab | light | en | 1440 | `153b05fe064b07b1.png` | clean | 12 baskets — every member, every record. ? Explore — every basket in depth The p |
| `explore-light-zh-1440` | explore-tab | light | zh | 1440 | `d294befc971ead23.png` | clean | 12 个篮子 — 全部成分，全部记录。 ? 深入探索 — 每个篮子的深读 表现一览、叠加图表，以及按类别分组的篮子。 12 / 12 个主题 01 表现一览 所 |

### (e) TABLE_LIMIT=8 see-more

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `table8-dark-en-1440` | table-limit-8 | dark | en | 1440 | `92f925b4e88a0a5f.png` | clean | 01 Performance table Every basket, sortable. Switch between plain return, return |
| `table8-dark-zh-1440` | table-limit-8 | dark | zh | 1440 | `a051815ab62d7db8.png` | clean | 01 表现一览 所有篮子都在这里，可以排序。可以在原始涨跌、相对沪深300、以及这波对它自己来说算不算反常之间切换。可以按类别筛选，点开就能看成分股。 全部 科 |
| `table8-light-en-1440` | table-limit-8 | light | en | 1440 | `bc8978d6724ab138.png` | clean | 01 Performance table Every basket, sortable. Switch between plain return, return |
| `table8-light-zh-1440` | table-limit-8 | light | zh | 1440 | `2098d6b8964610e0.png` | clean | 01 表现一览 所有篮子都在这里，可以排序。可以在原始涨跌、相对沪深300、以及这波对它自己来说算不算反常之间切换。可以按类别筛选，点开就能看成分股。 全部 科 |

### (f) σ mode (no MTD/YTD dash wall)

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `sigma-dark-en-1440` | sigma-mode | dark | en | 1440 | `d2474a2ab87649eb.png` | clean | 01 Performance table Every basket, sortable. Switch between plain return, return |
| `sigma-dark-zh-1440` | sigma-mode | dark | zh | 1440 | `7520ae04ecf88eec.png` | clean | 01 表现一览 所有篮子都在这里，可以排序。可以在原始涨跌、相对沪深300、以及这波对它自己来说算不算反常之间切换。可以按类别筛选，点开就能看成分股。 全部 科 |
| `sigma-light-en-1440` | sigma-mode | light | en | 1440 | `b0e2878741112851.png` | clean | 01 Performance table Every basket, sortable. Switch between plain return, return |
| `sigma-light-zh-1440` | sigma-mode | light | zh | 1440 | `bf470c8a9a832935.png` | clean | 01 表现一览 所有篮子都在这里，可以排序。可以在原始涨跌、相对沪深300、以及这波对它自己来说算不算反常之间切换。可以按类别筛选，点开就能看成分股。 全部 科 |

### (g) Confluence one stamp

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `confluence-dark-en-1440` | confluence-one-stamp | dark | en | 1440 | `f3457b5da0527a75.png` | clean | Subsector Confluence · China 同花顺概念 as of 2026-09-11 |
| `confluence-dark-zh-1440` | confluence-one-stamp | dark | zh | 1440 | `0b1df3f1d986602e.png` | clean | 子行业汇聚 · 中国 同花顺概念 截至 2026-09-11 |
| `confluence-light-en-1440` | confluence-one-stamp | light | en | 1440 | `7d03545de6231565.png` | clean | Subsector Confluence · China 同花顺概念 as of 2026-09-11 |
| `confluence-light-zh-1440` | confluence-one-stamp | light | zh | 1440 | `caf0f98d53f120fd.png` | clean | 子行业汇聚 · 中国 同花顺概念 截至 2026-09-11 |

### (h) one-sentence footer + disclaimer

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `footer-dark-en-1440` | one-sentence-footer | dark | en | 1440 | `f558c80653beb005.png` | clean | The conviction read blends credit, volatility and margin conditions with the pat |
| `footer-dark-zh-1440` | one-sentence-footer | dark | zh | 1440 | `297a6ea96daf00c6.png` | clean | 信念读数由信用、波动率和融资环境，以及走势的条件概率共同决定——仅供参考，非投资建议。 |
| `footer-light-en-1440` | one-sentence-footer | light | en | 1440 | `103bb9a227bbe17c.png` | clean | The conviction read blends credit, volatility and margin conditions with the pat |
| `footer-light-zh-1440` | one-sentence-footer | light | zh | 1440 | `cc915f81ab4b20d5.png` | clean | 信念读数由信用、波动率和融资环境，以及走势的条件概率共同决定——仅供参考，非投资建议。 |

### (i) .si-links band (LENS ? + Reversal Sleeve)

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `silinks-dark-en-1440` | si-links-band | dark | en | 1440 | `b59410e6fa10e2fb.png` | clean | VALIDATED EDGE Reversal Sleeve → ? 同花顺 theme browser ↗ Live Sector Board ↗ Narra |
| `silinks-dark-en-390` | si-links-band | dark | en | 390 | `f2fff30f603829a6.png` | clean | VALIDATED EDGE Reversal Sleeve → ? 同花顺 theme browser ↗ Live Sector Board ↗ Narra |
| `silinks-dark-zh-1440` | si-links-band | dark | zh | 1440 | `43c5b319643907e7.png` | clean | 已验证优势 反转组合 → ? 同花顺主题浏览器 ↗ 实时行业看板 ↗ 叙事篮子雷达 ↗ 市场热力图 ↗ |
| `silinks-dark-zh-390` | si-links-band | dark | zh | 390 | `43db0059b2934680.png` | clean | 已验证优势 反转组合 → ? 同花顺主题浏览器 ↗ 实时行业看板 ↗ 叙事篮子雷达 ↗ 市场热力图 ↗ |
| `silinks-light-en-1440` | si-links-band | light | en | 1440 | `ace73153efc3311a.png` | clean | VALIDATED EDGE Reversal Sleeve → ? 同花顺 theme browser ↗ Live Sector Board ↗ Narra |
| `silinks-light-en-390` | si-links-band | light | en | 390 | `e24f91788c506b1c.png` | clean | VALIDATED EDGE Reversal Sleeve → ? 同花顺 theme browser ↗ Live Sector Board ↗ Narra |
| `silinks-light-zh-1440` | si-links-band | light | zh | 1440 | `ef6153c4e4da922c.png` | clean | 已验证优势 反转组合 → ? 同花顺主题浏览器 ↗ 实时行业看板 ↗ 叙事篮子雷达 ↗ 市场热力图 ↗ |
| `silinks-light-zh-390` | si-links-band | light | zh | 390 | `ac6084b102876749.png` | clean | 已验证优势 反转组合 → ? 同花顺主题浏览器 ↗ 实时行业看板 ↗ 叙事篮子雷达 ↗ 市场热力图 ↗ |

### r3 error-light reuse (n2)

r3 `error-light-en-1440` (`7431fc8347511fe5.png`) was the identical content-addressed file as r2's `mxerror-light-en-1440`. This round recaptured error in both locales; the light-EN abort path is still `7431fc8347511fe5.png` (deterministic rig, same bytes). ZH error is a new file.

## Theme-specific degraded states

### loading skeleton

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `skel-dark-en-1440` | degraded-skeleton | dark | en | 1440 | `ad7151294119cad0.png` | clean |  |
| `skel-dark-zh-1440` | degraded-skeleton | dark | zh | 1440 | `ad7151294119cad0.png` | clean |  |
| `skel-light-en-1440` | degraded-skeleton | light | en | 1440 | `7ada6e0ad4149a96.png` | clean |  |
| `skel-light-zh-1440` | degraded-skeleton | light | zh | 1440 | `7ada6e0ad4149a96.png` | clean |  |

### empty (quiet tape)

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `empty-dark-en-1440` | degraded-empty | dark | en | 1440 | `16edc5e644c7f51a.png` | clean | ⟲ China Rotation Events When one theme tops out as a peer turns up off a low — a |
| `empty-dark-zh-1440` | degraded-empty | dark | zh | 1440 | `a0615ab9bc0769cb.png` | clean | ⟲ 中国轮动事件 一个主题冲顶回落、同类主题自低位转强，且两者比值确认时记录。仅供参考，不是买入清单。 当前无活跃中国轮动事件——安静状态是有效状态。 南向资金 |
| `empty-light-en-1440` | degraded-empty | light | en | 1440 | `874f8c79d40971dd.png` | clean | ⟲ China Rotation Events When one theme tops out as a peer turns up off a low — a |
| `empty-light-zh-1440` | degraded-empty | light | zh | 1440 | `dc2783f8d1e51de5.png` | clean | ⟲ 中国轮动事件 一个主题冲顶回落、同类主题自低位转强，且两者比值确认时记录。仅供参考，不是买入清单。 当前无活跃中国轮动事件——安静状态是有效状态。 南向资金 |

### stale regime input

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `stale-dark-en-1440` | degraded-stale | dark | en | 1440 | `354b4f77379b5bca.png` | clean | • China equities are mixed right now. Stale regime input detected: credit(90d),  |
| `stale-dark-zh-1440` | degraded-stale | dark | zh | 1440 | `d2b5c3a573faac40.png` | clean | • 当前A股信号中性。 市况数据已经陈旧：credit(90d), vol(20d)。上游采集可能已经停更，导致判断被卡住。请检查采集日志。 |
| `stale-light-en-1440` | degraded-stale | light | en | 1440 | `58bd8ba522393fca.png` | clean | • China equities are mixed right now. Stale regime input detected: credit(90d),  |
| `stale-light-zh-1440` | degraded-stale | light | zh | 1440 | `d847875fdbea02b2.png` | clean | • 当前A股信号中性。 市况数据已经陈旧：credit(90d), vol(20d)。上游采集可能已经停更，导致判断被卡住。请检查采集日志。 |

### error-with-retry

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `error-dark-en-1440` | degraded-error | dark | en | 1440 | `ee3b02231cf70ff6.png` | clean | ! Basket data did not load. The rest of this page still works.Retry |
| `error-dark-zh-1440` | degraded-error | dark | zh | 1440 | `88351e69d8d1a696.png` | clean | ! 篮子数据未能加载。本页其余部分仍可用。重试 |
| `error-light-en-1440` | degraded-error | light | en | 1440 | `7431fc8347511fe5.png` | clean | ! Basket data did not load. The rest of this page still works.Retry |
| `error-light-zh-1440` | degraded-error | light | zh | 1440 | `38cd222443f0ffab.png` | clean | ! 篮子数据未能加载。本页其余部分仍可用。重试 |

## 390w no-page-h-scroll receipts (every si-view × both languages)

| si-view | locale | clientWidth | scrollWidth | page overflow |
|---|---|---|---|---|
| `overview` | en | 390 | 390 | false |
| `map` | en | 390 | 390 | false |
| `moving` | en | 390 | 390 | false |
| `explore` | en | 390 | 390 | false |
| `confluence` | en | 390 | 390 | false |
| `overview` | zh | 390 | 390 | false |
| `map` | zh | 390 | 390 | false |
| `moving` | zh | 390 | 390 | false |
| `explore` | zh | 390 | 390 | false |
| `confluence` | zh | 390 | 390 | false |

All ten receipts report no page-level horizontal overflow.

Container `overflow-x: auto` on `.si-side` (mobile rail) and `.ts` (table) is the §9.10 in-container scroll, not page scroll.

