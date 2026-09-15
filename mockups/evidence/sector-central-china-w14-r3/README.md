# W14 r3 — sector_central_china evidence matrix

Provenance: `capture_sha` == `891c32e46f9d7c87c68f3e26c9721592019e8410`. Rig: S1 fixture-render + real `body.page-sector-central`; `__skyDeck`; overlay hide `.rvx-aurora` / `.mx5-aurora` / `.sky-fx` / `#mmb-root` / `#mmb-boot` / `.aurora`; overlay column populated; computed-style text on every cell. Light forced via `data-theme="light"` on `<html>` (and `setTheme`). Never opted into `site/` or `data/`.

Generated `2026-09-11T09:12:19Z`.

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
| `.si-links` band (tagged links + LENS `?`) | L1 KEEP; r2 simplified to one idiom | r2 cells `silinks-*` (referenced, not recaptured) |
| `#reversal-sleeve-card` | DEMOTE → one link-band entry `Reversal Sleeve → cn_reversal_sleeve.html` (both lanes); stats in LENS tip | r2 `silinks-*` |
| `#sleeve-chip` | DEMOTE → same Reversal Sleeve link-band entry; `hidden` on the chip | P2a test + explore crop |
| `#entry-radar` | DEMOTE → `<details id="entry-radar-more">` "Entry radar" / 「入场雷达」 at tail of Performance-table (JS mount unchanged) | r2 `details-open-*` |
| `#forming-narratives` | DEMOTE → `<details id="forming-narratives-more">` "Forming narratives" / 「酝酿中的叙事」 at tail of Baskets-by-category | explore crop |
| Theme Rotation Desk / concentration / 5-day rotation / impulse | DEMOTE → compact `<details class="si-more">` (`si_explore_compact`) | r2 `details-open-*` |
| r2 `.si-links-note` (42ch prose) | DEMOTE into LENS tip; band is tagged links + `?` only | r2 `silinks-*` (band unchanged this round) |


## 8 full-page baselines (rest cells)

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `rest-dark-en-1440` | full-page-overview | dark | en | 1440 | `b03f9f9c8244fbec.png` | clean | MASTERMINDX United States ▾ China ▾ Hong Kong ▾ Canada ▾ International ▾ Other A |
| `rest-light-en-1440` | full-page-overview | light | en | 1440 | `f61e3b4e073e47d7.png` | clean | MASTERMINDX United States ▾ China ▾ Hong Kong ▾ Canada ▾ International ▾ Other A |
| `rest-dark-zh-1440` | full-page-overview | dark | zh | 1440 | `935eb5e97e688d93.png` | clean | MASTERMINDX 美国 ▾ 中国 ▾ 香港 ▾ 加拿大 ▾ 国际 ▾ 其他资产 ▾ 研究 ▾ NVDA 终端 总览 全景图谱 正在轮动 深入探索 子行业汇 |
| `rest-light-zh-1440` | full-page-overview | light | zh | 1440 | `04f2d7056b6393e7.png` | clean | MASTERMINDX 美国 ▾ 中国 ▾ 香港 ▾ 加拿大 ▾ 国际 ▾ 其他资产 ▾ 研究 ▾ NVDA 终端 总览 全景图谱 正在轮动 深入探索 子行业汇 |
| `rest-dark-en-390` | full-page-overview | dark | en | 390 | `b3b346c032856218.png` | clean | NVDA Terminal Overview The Map What's Moving Explore Confluence CHINA SECTOR INT |
| `rest-light-en-390` | full-page-overview | light | en | 390 | `fd1281bc73c42741.png` | clean | NVDA Terminal Overview The Map What's Moving Explore Confluence CHINA SECTOR INT |
| `rest-dark-zh-390` | full-page-overview | dark | zh | 390 | `7f782195ca498c49.png` | clean | NVDA 终端 总览 全景图谱 正在轮动 深入探索 子行业汇聚 中国行业情报 · 12 个主题 · 3 个分类 截至 2026-09-11 领涨格局 稳定 中国 |
| `rest-light-zh-390` | full-page-overview | light | zh | 390 | `9fc508a47ad53cdd.png` | clean | NVDA 终端 总览 全景图谱 正在轮动 深入探索 子行业汇聚 中国行业情报 · 12 个主题 · 3 个分类 截至 2026-09-11 领涨格局 稳定 中国 |

## Per-fix crops

### (a) P0 CSI 300 frame

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `p0-dark-en-1440` | p0-versus-csi300 | dark | en | 1440 | `6d6b3dda26b70743.png` | clean | vs CSI 300 Weekly movers ranked by 5-day return versus CSI 300, plus the change  |
| `p0-dark-zh-1440` | p0-versus-csi300 | dark | zh | 1440 | `e27d0d1f12364564.png` | clean | 相对 沪深300 按相对沪深300的 5 日回报排序，并显示 20 日相对强度排名变化。 |
| `p0-light-en-1440` | p0-versus-csi300 | light | en | 1440 | `91deac53b6c25ef8.png` | clean | vs CSI 300 Weekly movers ranked by 5-day return versus CSI 300, plus the change  |
| `p0-light-zh-1440` | p0-versus-csi300 | light | zh | 1440 | `71b81b0f5258bc87.png` | clean | 相对 沪深300 按相对沪深300的 5 日回报排序，并显示 20 日相对强度排名变化。 |

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
| `explore-light-en-1440` | explore-tab | light | en | 1440 | `153e17c7e7f1282c.png` | clean | 12 baskets — every member, every record. ? Explore — every basket in depth The p |
| `explore-light-zh-1440` | explore-tab | light | zh | 1440 | `e8e3e95885b0a74b.png` | clean | 12 个篮子 — 全部成分，全部记录。 ? 深入探索 — 每个篮子的深读 表现一览、叠加图表，以及按类别分组的篮子。 12 / 12 个主题 01 表现一览 所 |

### (e) TABLE_LIMIT=8 see-more

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `table8-dark-en-1440` | table-limit-8 | dark | en | 1440 | `bd336e99a8736cf8.png` | clean | 01 Performance table Every basket, sortable. Switch between plain return, return |
| `table8-light-en-1440` | table-limit-8 | light | en | 1440 | `9309e076f3250d55.png` | clean | 01 Performance table Every basket, sortable. Switch between plain return, return |

### (f) σ mode (no MTD/YTD dash wall)

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `sigma-dark-en-1440` | sigma-mode | dark | en | 1440 | `57e5d528da5be77a.png` | clean | 01 Performance table Every basket, sortable. Switch between plain return, return |
| `sigma-light-en-1440` | sigma-mode | light | en | 1440 | `bf622397c9d6050b.png` | clean | 01 Performance table Every basket, sortable. Switch between plain return, return |

### (g) Confluence one stamp

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `confluence-dark-en-1440` | confluence-one-stamp | dark | en | 1440 | `f3457b5da0527a75.png` | clean | Subsector Confluence · China 同花顺概念 as of 2026-09-11 |
| `confluence-light-en-1440` | confluence-one-stamp | light | en | 1440 | `7d03545de6231565.png` | clean | Subsector Confluence · China 同花顺概念 as of 2026-09-11 |

### (h) one-sentence footer + disclaimer

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `footer-dark-en-1440` | one-sentence-footer | dark | en | 1440 | `f558c80653beb005.png` | clean | The conviction read blends credit, volatility and margin conditions with the pat |
| `footer-dark-zh-1440` | one-sentence-footer | dark | zh | 1440 | `297a6ea96daf00c6.png` | clean | 信念读数由信用、波动率和融资环境，以及走势的条件概率共同决定——仅供参考，非投资建议。 |
| `footer-light-en-1440` | one-sentence-footer | light | en | 1440 | `103bb9a227bbe17c.png` | clean | The conviction read blends credit, volatility and margin conditions with the pat |
| `footer-light-zh-1440` | one-sentence-footer | light | zh | 1440 | `cc915f81ab4b20d5.png` | clean | 信念读数由信用、波动率和融资环境，以及走势的条件概率共同决定——仅供参考，非投资建议。 |

### (h continued) simplified `.si-links` band — referenced from r2, not recaptured

The band is unchanged this round (r1 landing table + r2 one-idiom simplification). r2 capture_sha `21546c85ed8af3e286abfdd4214a8c99b607efe9`. Directory `mockups/evidence/sector-central-china-w14-r2`.

| id | file | theme | locale |
|---|---|---|---|
| `silinks-dark-en-1440` (r2) | `4341b686af527d45.png` | dark | en |
| `silinks-light-en-1440` (r2) | `035bcd140a1f09ec.png` | light | en |
| `silinks-dark-zh-1440` (r2) | `aef810cbf40c9fd2.png` | dark | zh |

## Theme-specific degraded states

### loading skeleton

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `skel-dark-en-1440` | degraded-skeleton | dark | en | 1440 | `ad7151294119cad0.png` | clean |  |
| `skel-light-en-1440` | degraded-skeleton | light | en | 1440 | `7ada6e0ad4149a96.png` | clean |  |

### empty (quiet tape)

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `empty-dark-en-1440` | degraded-empty | dark | en | 1440 | `16edc5e644c7f51a.png` | clean | ⟲ China Rotation Events When one theme tops out as a peer turns up off a low — a |
| `empty-light-en-1440` | degraded-empty | light | en | 1440 | `874f8c79d40971dd.png` | clean | ⟲ China Rotation Events When one theme tops out as a peer turns up off a low — a |

### stale regime input

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `stale-dark-en-1440` | degraded-stale | dark | en | 1440 | `354b4f77379b5bca.png` | clean | • China equities are mixed right now. Stale regime input detected: credit(90d),  |
| `stale-light-en-1440` | degraded-stale | light | en | 1440 | `58bd8ba522393fca.png` | clean | • China equities are mixed right now. Stale regime input detected: credit(90d),  |

### error-with-retry

| id | subject | theme | locale | vw | file | overlay | computed text |
|---|---|---|---|---|---|---|---|
| `error-dark-en-1440` | degraded-error | dark | en | 1440 | `ee3b02231cf70ff6.png` | clean | ! Basket data did not load. The rest of this page still works.Retry |
| `error-light-en-1440` | degraded-error | light | en | 1440 | `7431fc8347511fe5.png` | clean | ! Basket data did not load. The rest of this page still works.Retry |

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

