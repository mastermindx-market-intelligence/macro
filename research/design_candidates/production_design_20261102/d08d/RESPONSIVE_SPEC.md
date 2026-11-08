# Responsive composition and Paper construction specification

## Reference status

The fourteen [source studies](studies/index.html) are static SVG/PNG design aids with adjacent annotations. They contain illustrative numbers and no network calls, product imports, replay logic or working controls. They are **not Paper compositions or an approved substitute for Paper**. They consume F01-F02-SHELL/1.0.0-candidate.4 and proposed F02 roles; final joint v1 remains unreleased. The source studies are useful now for critique and build-contract clarity while that native composition lane is held.

The exact future destination is proposed as **MM · Futures & Replay** under the programme's organization plan. File/page/artboard IDs remain null. The current published direct action's file-creation prohibition must be refreshed through P00's normal same-app approval path. Do not create the file through another carrier or use sibling D08/B/C boards to bypass the gate. The future writer rechecks live schemas, ownership and existing effects before dispatch, uses a stable operation ID and fresh exact snapshot, and reads back the returned file ID. A snapshot guard is not a document revision.

## Information hierarchy

1. **Return and identity.** One visible named return action, page title, exact instrument/contract, historical/source basis, venue and units. Global search context cannot silently replace route identity.
2. **Selection.** Absolute selected time and native ordinal/cutoff; requested-versus-effective time when they differ; actual retained/loaded scope. This survives scrolling as compact context when controls become sticky.
3. **Primary evidence.** One primary depth/footprint/execution visualization and a small set of clearly scoped totals. Unknown-side volume and coverage are adjacent to affected values.
4. **Inspection.** Evidence opens the selected observation, with source qualifications before exact technical fields. Long identifiers remain recoverable through wrap/copy, never only ellipsis.
5. **Advanced work.** Named Controls/Display & layers disclosure retains interval, row aggregation, expiry lens, mapping, GEX, CVD, zoom and price range. Weekly positioning is separately timed below the chart.

This organization preserves depth without making a new user read every source qualification before locating the observation. Essential limitations remain beside the affected data; detailed methodology stays in evidence. No warning stripe or colored container border carries hierarchy.

## Real shell geometry

Consume the shared shell once. The domain contributes content inside its measured useful width; it does not recreate or automatically compact navigation.

| Viewport | Expanded nav | Each gutter | Useful width | Evidence treatment |
| --- | ---: | ---: | ---: | --- |
| 320 | 0, closed drawer | 16 | 288 | Full-width modal, 16px internal padding |
| 390 | 0 | 16 | 358 | Full-width modal |
| 600 | 0 | 16 | 568 | Full-width modal |
| 768 | 0 | 20 | 728 | 440px modal; primary retains its width behind scrim |
| 860 | 0 | 20 | 820 | 440px modal |
| 861 | 196 | 20 | 625 | 440px modal; controls wrap; compact chart/table presentation |
| 1024 | 196 | 20 | 788 | 440px modal; a 320px dock would leave only 444px and is prohibited |
| 1200 | 224 | 24 | 928 | Modal |
| 1256 | 224 | 24 | 984 | 320px dock +24px gap leaves 640px, subject to domain plot minimum |
| 1280 | 224 | 24 | 1008 | Dock leaves 664px |
| 1440 | 224 | 24 | 1168 | Dock leaves 824px |
| 1600 | 224 | 24 | 1328 | Dock leaves 984px |

Header is 64px wide / 56px at ≤860; local navigation is at least 44px. A manually selected 72px compact nav is preserved by its owner; the first mathematical dock width there is 1096px, not an automatic domain breakpoint. The primary width minimum is subject to real plot/axis/control measurements. D06's separate focused-chart inspector dimensions must not be substituted into this shared-shell calculation.

At narrow widths, show the selected time above the chart, give Previous/Next/picker a full touch row, and place Evidence beside the view switch. Statistics use short but qualified labels and may wrap to two-plus-one rows. Do not hide “unknown side” or a gap just to force three columns. An opened controls sheet stages changes and exposes Apply/Cancel; switching language or opening evidence cannot silently commit it.

## Dark treatment

Use calm luminance depth: near-black canvas, slightly raised navigation, neutral panel surfaces and restrained selected fill. Primary text is bright but large empty areas remain quiet. Data colors distinguish buy/sell or price direction under their existing owners; focus is a complete outline. No decorative glow is necessary in this analytical workspace. Chart gaps use both a hatch/pattern and text. An unavailable GEX layer leaves valid futures observations readable.

The studies use F02 proposed roles: canvas `#080808`, navigation `#0c0c0c`, panel `#121212`, raised `#191919`, selected `#292929`, text `#f3f3f3/#b8b8b8/#949494`, neutral divider `#343434`, contrast-bearing boundary `#6f6f6f`. These are role references, not a newly shipped CSS namespace. Cyan/lilac side inks in these studies are proposed treatments requiring F02/domain review, not claimed incumbent invariants: actual IEX source uses green/red book-side inks, and the futures heatmap has quantity bands. The encodings stay distinct. Futures depth uses combined mean resting contracts; equity uses bid/ask resting shares with log intensity; footprint uses Sell | Buy classifications. Price up/down is a separate convention.

## Light treatment

Use a research workspace with a cool neutral page, white analytical surfaces and hairline separation. The inspector gains definition from white material, boundary/shadow and spacing rather than dark-mode glow. Selected controls have a quiet neutral fill; text and data inks are explicitly dark enough for the light material. Hover/pressed layers, gap hatching and degraded-source notices are adjudicated separately from dark.

Proposed role values: canvas `#f6f6f3`, navigation `#efefec`, panel `#ffffff`, raised `#f0f0ed`, selected `#e2e2dc`, text `#1a1c20/#51555b/#5f6368`, divider `#cbccc7`, control boundary `#85877f`. Link, warning, buy/sell and focus use their light text-grade roles. Light evidence surfaces keep generous line separation for native timestamps; they are not an inverted screenshot. The native designer must qualify real text, focus, controls and chart marks on both treatments.

## Typography, spacing and motion

Use the released F02 UI stack with tabular financial numerals. Native identifiers may use the code face; financial values are not globally switched to monospace. Paper's inspected file provides Inter and PingFang SC. The local PNG studies use DejaVu Sans as an available fallback; this is a disclosed study-render limitation, not a new production font decision. Final CJK glyph and wrapping review is outstanding.

Target 28px desktop /24px mobile page titles, 17px section headings, 14px analytical body, 13px tables and 12px supporting metadata. Essential caveats are readable body text near affected content, not sole microtext. Long exact values wrap safely. Use 4/8/12/16/20/24/32/44 spacing roles; do not alias `--sp-8` across repositories because existing source meanings differ. Primary mobile controls are at least 44px; table rows target 48px on touch. Desktop density can use 40px rows with keyboard access.

Routine transitions target 120ms; reduced motion is static. No automatic numeric tween, continuous-time interpolation, animated gap fill or autoplay is introduced. Focus is visible on buttons, tabs, sliders, tables and modal close. Screen-reader live status announces a committed selection, not every pixel of pointer movement.

## Studies and annotations

| Study | User task and annotation focus | Status |
| --- | --- | --- |
| [Futures 1440 dark](studies/futures-1440-dark-en.png) | Orient to ESZ6, select a historical cutoff, inspect evidence and return | Supporting EN static study |
| [Footprint 1440 light](studies/futures-footprint-1440-light-en.png) | Dense execution comparison with CVD, layer context and evidence | Supporting EN static study |
| [Equity 1440 dark](studies/equity-1440-dark-en.png) | Select retained IEX sample and distinguish acquisition time | Supporting EN static study |
| [Equity evidence 1024 light](studies/equity-evidence-1024-light-en.png) | Preserve useful primary width; use 440px modal inspector | Supporting EN static study |
| [Futures 390 dark](studies/futures-390-dark-en.png) | Identity/time before chart, touch selection and advanced controls | Supporting EN static study |
| [Futures 320 dark](studies/futures-320-dark-en.png) | Minimum-width control and number legibility | Supporting EN static study |
| [Equity 390 light](studies/equity-390-light-en.png) | Partial archive, snapshot selection and scoped totals | Supporting EN static study |
| [Equity evidence 390 light](studies/equity-evidence-390-light-en.png) | Full-width evidence with exact native fields and named return | Supporting EN static study |
| [State atlas](studies/state-atlas-1440-light-en.png) | Guest/plan/access/source/window/loading/gap/return/unsupported/error/stale states | Supporting EN static study |
| [Opened advanced views](studies/advanced-replay-1440-dark-en.png) | Futures query/layers, available GEX and levels, separately timed COT, equity price range/executions | Supporting EN static study |
| [Futures controls 390](studies/futures-controls-390-dark-en.png) | Full scrollable controls sheet, Apply/Cancel, chart table and weekly report access | Supporting tall content capture |
| [Futures evidence 390](studies/futures-evidence-390-dark-en.png) | Request/cutoff, available/loaded window, publication/freshness, unknown-side and GEX qualification | Supporting tall content capture |
| [Exact equity source 1024](studies/equity-source-1024-light-en.png) | Full example artifact/source digests, native identity, correction scope and acquisition limitation | Illustrative identity; no market receipt |
| [Journey, chooser and return](studies/journey-chooser-return-1440-light-en.png) | Matched origin/expected return, direct retained-array picker and changed observation with withheld book | Proposed state sequence; not browser proof |

These do not cover all native theme/locale combinations or prove focus behavior. The [first-pass input freeze](review-input/first-pass-artifacts.json) retains unannotated reviewer inputs. Later study amendments are separate from that frozen set. Reviewer findings and remediations are recorded in [REVIEW_RETURN.md](REVIEW_RETURN.md).

Post-critique mobile main views reserve a 310px chart card with a 194px plot, compared with the original 100px plot. Whole-number futures ticks omit redundant `.00`; real fractional ticks retain their required precision and axis width. Exact historical year, quantity scope, unknown side, the named origin, a full-array picker and 44px controls remain. The annotation band is outside the 844px product viewport. The two tall sheet captures illustrate scrollable content, not content magically fitting one viewport.

Procedural illustrative chart marks are not source evidence. Futures heat cells use illustrative quantities in the displayed bands; equity opacity uses the declared logarithmic ratio over the illustrated displayed prefix. Neither calibrates against a real admitted feed. Both final source-derived encoding and native palette/contrast still require acceptance. Current IEX's up-to-60 selected-prefix drawing is retained; the first-pass 40-column depiction remains in the review freeze as historical review input only.

## Bilingual composition copy

Use the existing language provider. Keep source symbols, contract identifiers, hashes, decimal nanoseconds and SI units stable. Language is separate from market-direction color convention. Do not silently switch to Chinese market data when switching language.

| English | 简体中文 | Layout rule |
| --- | --- | --- |
| Futures replay / Equity replay | 期货回放 / 股票回放 | Same title hierarchy |
| Historical / Latest retained observation | 历史 / 最新保留观测 | Remains adjacent to cursor; “实时” prohibited for archive selection |
| Return to NVDA chart | 返回 NVDA 图表 | 44px target; named fallback only if exact return unavailable |
| Selected published frame | 所选已发布帧 | Two lines permitted on mobile |
| Requested / Selected | 请求时刻 / 已选观测 | Show both when values differ |
| Available in this publication / Loaded | 本次发布可用范围 / 已加载范围 | Do not abbreviate them into one range |
| Observed snapshot / Choose observation | 观测快照 / 选择观测 | Accessible ordinal and exact time |
| Depth / Footprint / Executed volume | 深度 / 足迹 / 成交量 | Native tabs, no compressed icon-only meanings |
| Observed bid shares / Observed ask shares | 观测买方挂单股数 / 观测卖方挂单股数 | Wrap labels to two lines; values retain width |
| Captured contracts / Known-side delta | 捕获合约数 / 已知方向净量 | Do not translate delta as return/P&L |
| Unknown-side contracts | 方向未知合约数 | Keep unknown quantity visible |
| Display & layers / Evidence | 显示与图层 / 证据 | Reachable on every width |
| Archive acquired / Artifact served | 档案获取于 / 数据响应时间 | Separate clocks; exact values remain available |
| Source session / Native sequence | 来源交易时段 / 原生序列 | Long values wrap; no fabricated exchange session |
| Partial captured window | 仅部分捕获时段 | Adjacent to totals and evidence |
| Book withheld / No captured executions | 暂不显示订单簿 / 未捕获成交 | Neither phrase means a market zero |
| Weekly positioning — outside replay | 每周持仓 — 不属于回放 | Independent report/retrieval clocks |
| Source-session 0DTE | 来源交易日内到期 | No intraday tradability guarantee |

Full bilingual exception and save-copy contracts are in [WORKFLOW_INTERACTION.md](WORKFLOW_INTERACTION.md). A future Paper matrix must include dark/light × EN/ZH at desktop1440 and mobile390, plus 320 stress and 768/1024 modal transitions. EN raster studies here are not misreported as ZH visual proof.

## Native Paper construction packet after admission

First create a focused file through the qualified original app action, verify its exact ID and empty/expected contents, then add **00 · Read me & Build contract** and **01 · Replay candidates** pages. Proposed labels below are construction intent, not claimed existing board IDs:

- Read me / Build contract: persona, complete journey, owner map, source/interface/foundation pins, current candidates, illustrative-data notice, actual limitations, RIG state and exact source package link.
- Futures desktop dark EN, futures desktop light ZH footprint, equity desktop light EN, equity desktop dark ZH evidence.
- Futures mobile dark EN and light ZH controls; equity mobile light EN and dark ZH full-width evidence.
- 320 dense/long-value state, 768 modal state, 1024 light/ZH evidence state.
- Access/failure atlas in both themes with EN/ZH copy, including selected book gap, latest-source stale and exact-return fallback.
- Adjacent annotations for every materially changed selection, evidence, refresh and return control. Link full contracts while leaving useful explanations in Paper itself.

Use current catalog schemas, tokens/components and source-backed chart semantics. Each bounded edit has one stable operation ID/carrier and a fresh exact snapshot. No sibling board is a writable target. After each meaningful state, capture the actual artboard, inspect hierarchy/clipping/density/contrast and iterate. If an edit result is unknown, reconcile that same target/carrier before any further write. On acceptance, export supported JSX only as a visual construction aid; future builders integrate it into the owned route/providers/readers rather than shipping a second app.

Freeze exact native IDs/time, screenshots, supported source exports and annotations with SHA-256 into the existing RIG manifest/receipt process. A successful schema response, token hash or hero screenshot is insufficient. Later canvas edits invalidate affected captures/review. P00/F01/QA01 gates remain visible until their exact evidence is read back.
