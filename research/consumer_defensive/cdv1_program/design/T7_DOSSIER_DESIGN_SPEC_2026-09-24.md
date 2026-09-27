# CDV-1 Task 7 — Demand and Earnings Dossier Content + Contract Specification

STATUS: CONTENT+CONTRACT — awaiting foundation integration (repaired per R1/R1A/R2; §6 field map PROPOSED until Task 6 merges)

Operation: `gmi-consumer-defensive-research-20260923-sol-001`

Commissioned by: Fable Meta-CEO seat

**Addressed to:** the foundation host slot on PR #7870's lineage and `contracts/sector_intelligence/*.v1.schema.json`. The Earnings owner's clock remains authoritative. Clock-word mappings at that foundation are: fiscal period → `world_valid`; source published → `source_published`; source accepted/knowable time → `knowable`; source currentness observation → `observed`; workspace generation → `belief_or_build`; task-system recording → `system_recorded`; governance recording → `system_recorded`. No foundation class yet exists for review freshness, so that clock word remains “no foundation class yet” rather than an invented class.

This document owns the dossier content, copy, DOM contract, adapter behavior, privacy rules, and tests. It does not own a mount, host wiring, an asset path, or any CSS material treatment. Those are foundation-owner obligations. R1A supersedes the original mount, asset, and host-wiring rulings; the original R3-R6 and R8-R10 remain binding where they concern content, contract, copy, accessibility, and density.

## 1. Integration requirements (host slot)

### 1.1 Foundation host slot

The foundation owner supplies one bounded detail-panel slot per journey where the dossier can appear, one native issuer selector, and one currently selected symbol. The slot has no dossier-specific page, header, hero, navigation, scoring surface, or asset route of its own.

The host must provide:

- A bounded detail panel whose collapsed control consumes no more than 44 px of layout height and changes no page height while collapsed.
- A native issuer selector; its selected symbol is the only issuer value passed to the adapter.
- An authenticated read callback that uses the existing site session client and requests with `cache:'no-store'`.
- An auth-change subscription that follows `mdx-auth`, ignores `PREFS_SAVED`, and reports a change only when signed-in user identity changes.
- Focus and return handling for the host panel and evidence dialog: initial focus moves to the dialog close control, Escape and the non-content scrim close the dialog, Tab and Shift+Tab remain inside an open dialog, and focus returns to the invoking evidence control.
- A lifecycle owner that mounts on first disclosure expansion. Before that expansion there is no prefetch of private data. After the first expansion, the adapter keeps its DOM and the host merely hides it on collapse; re-expansion within the same signed-in session causes no teardown or refetch. The adapter destroys only on host teardown (a sign-out clears the private content to the sign-in state per §6.3 and keeps the adapter mounted), and `destroy()` is idempotent.
- If a host collapses on click, that host toggle ignores every click originating inside the dossier root.
- The expanded material area constrained to a maximum height of 390 px, with vertical scrolling inside the dossier content rather than the host page.

### 1.2 Adapter contract

```javascript
mountEarningsEconomicDossier(root, {issuer, fetchAuthenticated, onAuthChange}) → destroy()
```

- `root`: one element bound as `[data-economic-root]`. If it is missing, not an `Element`, or already mounted, return a no-op `destroy()` and change nothing. A successful mount writes exactly `data-economic-mounted="1"`; `destroy()` removes the attribute.
- `issuer`: `{ticker}`. The ticker is a display and route symbol, not native issuer identity. The adapter never resolves ticker identity, never supplies a native issuer ID, and never calls a GMI graph API.
- `fetchAuthenticated`: `(url, init={}) => Promise<Response>`. It must obtain the current session through `sb.auth.getSession()`, send the access token as `Authorization: Bearer <token>`, preserve `cache:'no-store'`, and return the browser `Response`. The adapter adds no second auth client and never stores a token.
- `onAuthChange`: `(listener) => unsubscribe`. The host subscribes to `mdx-auth`, ignores `PREFS_SAVED`, and invokes the listener only for a user-identity change.
- For source selection, the host's adapter call argument `issuer.ticker` is the only input. The adapter never selects a source from a dossier label, heading, URL fragment, issuer-name lookup, or any host attribute.
- On the first user expansion it renders the fixed loading state and requests `/api/earnings/v1/economic/{issuer.ticker}`. It performs no polling or automatic refresh.

### 1.3 Open integration items for the foundation owner — DEFERRED

- Asset delivery and registration for the adapter.
- The include or module point at which the foundation loads the adapter.
- The host initialization call and final host-slot placement.

No Task 7 implementation, browser proof, or visible-journey claim is complete until the foundation owner resolves these items.

## 2. Information architecture

### 2.1 Glance tier

The collapsed row shows the section title, the issuer display name, and the expand toggle only. No status chip, stance line, or other data-derived text appears before the user first expands the section. After the first expansion, the state chip and stance sentence remain at the top of the expanded body and never migrate into the collapsed row.

### 2.2 Read tier: facts tables

Demand and earnings are separate groups. Each displayed fact row has a bilingual label, period, neutral basis chip, server-rendered value and unit, and an evidence action. Rows remain in server order. Reported, organic, and core are distinguished by their labels and words, not by semantic color.

The Demand group states: “Organic sales are a company-defined revenue measure, not household consumption.” / “有机销售额是公司定义的收入口径，不等于家庭消费。”

The Earnings group states: “Reported and core EPS use different definitions.” / “报告每股收益与核心每股收益采用不同定义。”

### 2.3 Findings

Findings are plain bilingual sentences selected only by the fixed rule-ID table in §5. They never display a rule ID and never add a trading direction.

### 2.4 Missing context

Missing optional context remains visible as a plain bilingual sentence. Absence never becomes “no data,” “unknown,” a zero value, or a market verdict.

### 2.5 Currentness and clock footer

The glance chip is selected only from `selection.currentness`. The footer prints the fiscal period, source acceptance time, and currentness sentence from server-owned localized values. It never calculates dates or manufacture time.

### 2.6 Evidence dialog

The evidence dialog is a bounded dialog, not a page. It identifies the source header, period, displayed generation, and permitted source excerpt. It does not expose object keys, credentials, full private documents, or machine paths.

## 3. Content structure and accessible DOM contract

The foundation may compose its canonical markup, but these data attributes and semantics are binding:

- Root: `data-economic-root`, `data-economic-state`, and `data-economic-mounted="1"` only after a successful adapter mount.
- Mounted issuer receipt: the adapter writes `issuer.ticker` to `data-economic-issuer` on the mount root; it never reads that attribute.
- State values: `data-economic-state` takes exactly `idle`, `loading`, `ready`, `sign_in`, `no_access`, `not_found`, `unavailable`, `unsupported`, or `error`.
- State chip: `data-economic-state-chip`.
- Stance sentence: `data-economic-stance`.
- Loading area: `data-economic-loading`.
- Content area: `data-economic-content`.
- Findings container: `data-economic-findings`.
- Demand rows container: `data-economic-demand`.
- Optional segment rows container: `data-economic-segments` and `data-economic-segment-rows`.
- Earnings rows container: `data-economic-earnings`.
- Finding rows: `data-economic-rule`.
- Missing-context rows: `data-economic-missing`.
- Clock footer: `data-economic-clock`.
- Links area: `data-economic-links`.
- State panel: `data-economic-state-panel`.
- Evidence dialog: `data-economic-evidence-drawer`.
- Evidence dialog text: `data-economic-evidence-text`; header, period, generation, manifest, record, digest, and precision placeholders each retain a dedicated `data-economic-evidence-*` attribute.

A fact row is a real table row:

```html
<tr data-economic-period="SERVER_PERIOD"
    data-economic-basis="reported|organic|core">
  <th scope="row">SERVER_BILINGUAL_OR_SELECTED_LABEL</th>
  <td>SERVER_PERIOD</td>
  <td><span data-economic-basis-label>SERVER_BASIS</span></td>
  <td>SERVER_VALUE_AND_UNIT</td>
  <td>
    <button type="button"
            data-economic-evidence
            data-economic-fact-id="SERVER_FACT_ID">
      <span class="l-en">Evidence</span><span class="l-zh">证据</span>
      <span data-economic-accessible-row-name>ACCESSIBLE_ROW_NAME</span>
    </button>
  </td>
</tr>
```

The evidence control uses a visible text label, not an icon-only label. Its accessible name is bilingual and includes the row label, for example “Open source evidence — Reported diluted EPS” / “打开源证据——报告稀释每股收益”.

The host must render the basis label as a neutral chip and the row name as visually hidden text while keeping both readable to assistive technology; the spec owns the `data-economic-*` attributes and ARIA, not host class names. Other accessibility requirements are fixed: real table semantics; heading levels nest correctly inside the host panel; the dialog uses `role="dialog"` and `aria-modal="true"`; initial focus is the close button; Escape and the toggle control close the dialog; focus returns to the invoking evidence button; all disclosure `hidden` and `aria-expanded` states stay synchronized; every interactive target has an effective target of at least 40×40 px. Bilingual accessible names are provided for the root, links navigation, evidence dialog, evidence controls, close control, sign-in control, and disclosure controls.

The unentitled state must contain a real sign-in control:

```html
<button type="button" data-economic-sign-in>
  <span class="l-en">Sign in to read this research</span><span class="l-zh">登录以阅读此研究</span>
</button>
```

Activation follows the foundation's existing sign-in action and returns focus to the sign-in control after failure or cancellation if the host remains open. It never deep-links to a production billing route or exposes entitlement details.

## 4. Material requirements for the host

This dossier owns no stylesheet, selector, token, or CSS declaration. The foundation must satisfy both art directions with its shared material system.

### 4.1 Intentional theme differences

The reference baseline is `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` §12 (light component table). The mechanisms that intentionally differ between the two art directions are:

- Separation: dark uses luminance layering; light uses hairline structure.
- Emphasis: dark uses restrained glow; light uses a tight shadow.
- Canvas: dark uses a deep neutral; light uses a cool light canvas.
- Dialog scrim: dark has one; light has none.

### 4.2 Dark art direction

Dark is a command-center treatment. It uses luminance depth, restrained glow, and a dark scrim behind the evidence dialog. Dossier surfaces must separate through layered panel luminance, not a new color family. Interactive evidence and close controls may use a controlled light response or glow consistent with shared dark controls.

Degraded states are concrete: loading geometry uses a panel-luminance step without source text; unavailable and no-access states have no glow or bloom; unsupported and error states use state ink on the existing panel scale; missing context stays legible without a second palette; reduced motion requires no movement.

### 4.3 Light art direction

Light is a research-workspace treatment. It uses a cool canvas, white or near-white material, hairline structure, and shadow rather than glow. The evidence dialog has no dark scrim; it uses an existing light overlay or transparent separation with the host. Raised controls use a crisp hairline and tight shadow, not glow or glass sheen.

Degraded states are concrete: loading geometry remains visible on the cool canvas; unavailable and no-access states retain a structural step or hairline on white; unsupported and error text remains legible without relying on dark-only glow; missing context stays legible without a second palette; reduced motion requires no movement.

Light mode has no scrim, so click-to-close binds to the toggle control itself and to `Escape`; dark mode also provides its non-content scrim. The toggle is the only other close affordance in both themes.

### 4.4 Neutral and semantic color requirements

- Reported, organic, and core basis chips use the same neutral chip family; only their visible words differ.
- State color may distinguish up to date, warning, and unavailable semantics, but never labels a basis chip better, suspect, linked, or actionable.
- Links use the host's link semantic; non-link controls must not use the link color.
- Color is never the only means of distinguishing a basis, state, language, or action.
- The two art directions must be separately adjudicated in dark and light; token substitution alone is not acceptance evidence.

### 4.5 Density requirement

The collapsed control is at most 44 px tall. The expanded dossier area is at most 390 px tall and uses inner vertical scrolling. The dossier adds no header, hero, second page, or always-expanded full-sector report.

## 5. Copy, stance lookup, and definitions

All source-derived labels and date strings are server-owned bilingual strings. Fixed UI strings are paired EN/ZH and must not be paraphrased. ZH is native-shaped; EPS, FX, and established company segment names may remain intact. No translated text is placed in `title=` attributes.

### 5.1 Fixed shell and actions

| Token | EN | ZH |
|---|---|---|
| title | Demand and earnings evidence | 需求与盈利证据 |
| compact toggle | Open {issuer.name} demand and earnings evidence | 打开{issuer.name}需求与盈利证据 |
| compact expanded suffix | Close {issuer.name} demand and earnings evidence | 关闭{issuer.name}需求与盈利证据 |
| action: watch | watch — don't chase | 先观察，不追入 |
| action: source | check the source before acting | 先核对来源再行动 |
| action: none | nothing to act on yet | 暂无可执行事项 |
| action: receipt | read the receipt first | 先阅读凭证 |
| loading | Loading the latest accepted evidence. | 正在加载最新已采纳证据。 |
| demand | Demand | 需求 |
| earnings | Earnings | 盈利 |
| item | Item | 项目 |
| period | Period | 期间 |
| basis | Basis | 口径 |
| value | Value | 数值 |
| evidence | Evidence | 证据 |
| evidence action | Open source evidence | 打开源证据 |
| segments | Segment detail | 分部明细 |
| findings | What the numbers say | 数字说明了什么 |
| missing title | Context not available | 缺失的背景 |
| drawer title | Source evidence | 来源证据 |
| header | Header | 表头 |
| generation | Generation | 生成版本 |
| manifest | Manifest | 清单 |
| record | Record | 记录 |
| digest | Digest | 解读 |
| precision | Precision note | 精度说明 |
| close | Close | 关闭 |
| source accepted | Source accepted | 来源采纳时间 |
| currentness | Currentness | 时效性 |
| company link | Open the company page | 打开公司页面 |
| GMI link | Open the related research | 打开相关研究 |
| unresolved links | Related company and research links are unavailable. | 相关公司与研究链接不可用。 |

### 5.2 Basis chips

| Machine value | EN | ZH |
|---|---|---|
| reported | Reported | 报告口径 |
| organic | Organic | 有机口径 |
| core | Core | 核心口径 |

### 5.3 Fact labels

| Owner metric family | EN | ZH |
|---|---|---|
| reported sales growth | Reported sales growth | 报告销售额增长 |
| organic sales growth | Organic sales growth | 有机销售额增长 |
| total volume growth | Total volume growth | 总销量增长 |
| organic volume growth | Organic volume growth | 有机销量增长 |
| combined volume/mix | Volume and mix combined | 销量与结构合计 |
| price contribution | Price contribution | 价格贡献 |
| mix contribution | Mix contribution | 结构贡献 |
| FX contribution | FX contribution | 汇率贡献 |
| other contribution | Other contribution | 其他贡献 |
| reported diluted EPS | Reported diluted EPS | 报告稀释每股收益 |
| prior reported diluted EPS | Prior reported diluted EPS | 上期报告稀释每股收益 |
| reported EPS growth | Reported EPS growth | 报告每股收益增长 |
| core EPS | Core EPS | 核心每股收益 |
| prior core EPS | Prior core EPS | 上期核心每股收益 |
| core EPS growth | Core EPS growth | 核心每股收益增长 |
| core reconciliation context | Core EPS reconciliation | 核心每股收益调节说明 |
| admitted segment | Use the owner-supplied segment display name in both languages | 使用所有者提供的双语分部名称 |

### 5.4 Plain-word state chips

| `selection.currentness` | EN | ZH |
|---|---|---|
| `up_to_date` | Up to date | 已是最新 |
| `newer_source_pending` | Newer filing not yet read | 新文件尚未读取 |
| `currentness_unverified` | Freshness not confirmed | 时效未确认 |
| absent or unsupported | Not available | 不可用 |

State-panel copy:

| State | EN | ZH |
|---|---|---|
| unavailable | This evidence is unavailable. | 此证据暂不可用。 |
| unavailable why | The accepted private record is not available to this page. | 本页无法读取已采纳的私有记录。 |
| unentitled | Full membership is required. | 需要完整会员权限。 |
| unentitled why | Sign in with an account that includes this research. | 请使用包含此研究的账户登录。 |
| unsupported schema | This evidence needs a newer page version. | 此证据需要更新版本页面。 |
| error | This evidence could not be loaded. | 此证据未能加载。 |
| error why | The request failed before any evidence was shown. | 请求在显示任何证据前失败。 |

### 5.5 Pinned stance table

Evaluate the ordered set of `interpretation.findings[].rule_id` from first to last and use the first matching row. Matching is rendering only; the browser never computes, scores, or ranks findings.

| Ordered rule-ID set | EN sentence | ZH sentence |
|---|---|---|
| contains `reported_vs_organic_difference` | Reported and organic growth differ — check the source before acting. | 报告与有机增长不同——先核对来源再行动。 |
| otherwise contains `positive_organic_nonpositive_pure_volume` | Organic rose but pure volume did not — watch — don't chase. | 有机增长而纯销量未增——先观察，不追入。 |
| otherwise contains `reported_vs_core_earnings_disagreement` | Reported and core EPS differed — read the receipt first. | 报告与核心每股收益不同——先阅读凭证。 |
| otherwise contains `incomplete_margin_to_cash_bridge` | Margin does not show profit or cash improvement — nothing to act on yet. | 利润率未显示利润或现金改善——暂无可执行事项。 |
| otherwise contains `segment_scope_limitation` | Segments cover only those segments — check the source before acting. | 分部仅覆盖这些分部——先核对来源再行动。 |
| otherwise contains `missing_consensus` | Consensus is unavailable — nothing to act on yet. | 缺少一致预期——暂无可执行事项。 |
| default | Fresh evidence is ready — read the receipt first. | 新证据已就绪——先阅读凭证。 |

### 5.6 Findings by rule ID

The machine rule ID is never shown.

| Rule ID | EN | ZH |
|---|---|---|
| reported_vs_organic_difference | Reported and organic growth differ — check the source before acting. | 报告与有机增长不同——先核对来源再行动。 |
| positive_organic_nonpositive_pure_volume | Organic rose but pure volume did not — watch — don't chase. | 有机增长而纯销量未增——先观察，不追入。 |
| reported_vs_core_earnings_disagreement | Reported and core EPS differed — read the receipt first. | 报告与核心每股收益不同——先阅读凭证。 |
| incomplete_margin_to_cash_bridge | Margin does not show profit or cash improvement — nothing to act on yet. | 利润率未显示利润或现金改善——暂无可执行事项。 |
| segment_scope_limitation | Segments cover only those segments — check the source before acting. | 分部仅覆盖这些分部——先核对来源再行动。 |
| missing_consensus | Consensus is unavailable — nothing to act on yet. | 缺少一致预期——暂无可执行事项。 |

### 5.7 Missing context

| Owner value | EN | ZH |
|---|---|---|
| consensus | Consensus is unavailable. | 缺少一致预期数据。 |
| segments | Segment detail is unavailable. | 分部明细不可用。 |
| reconciliation | The company’s core EPS reconciliation is unavailable. | 公司核心每股收益调节说明不可用。 |
| margin_to_cash | The margin-to-cash bridge is unavailable. | 利润率与现金流之间的衔接信息不可用。 |
| empty list | Nothing required is missing. | 必需信息没有缺失。 |

### 5.8 Mandatory definition lines

- “Organic sales are a company-defined revenue measure, not household consumption.” / “有机销售额是公司定义的收入口径，不等于家庭消费。”
- “Reported and core EPS use different definitions.” / “报告每股收益与核心每股收益采用不同定义。”
- “Volume and mix combined is not pure volume.” / “销量与结构合计不等于纯销量。”
- “Read the evidence in its source context.” / “请结合来源语境阅读证据。”

### 5.9 Clock templates

- Fiscal period: `Fiscal period: {period}` / `财务期间：{period}`
- Source accepted: `Source accepted: {date}` / `来源采纳时间：{date}`
- Up to date: `Currentness: up to date as of {source clock}` / `时效性：截至{source clock}已是最新`
- Pending: `Currentness: a newer filing has not been read since {source clock}` / `时效性：自{source clock}起新文件尚未读取`
- Unverified: `Currentness: latest accepted, freshness not confirmed` / `时效性：最新已采纳，时效未确认`

### 5.10 Copy bans

No visible string uses internal state names, machine slugs, generation labels except inside the evidence dialog, study names, or falsifier/refutation language. “Validated” is forbidden. No front-facing string says demand is proven, core is cleaner or recurring, combined volume/mix is pure volume, or consensus was beaten. The UI never says “buy,” “sell,” “size,” “rank,” “originate,” “entry,” or “Prophet.”

## 6. Data and behavior contract

### 6.1 Response wrapper and closed interpretation

The current view is the Task 6 wrapper:

```text
{slug, generation_id, manifest_sha256, record_sha256, interpretation, …}
```

Require all five named wrapper fields. Apply the closed 14-key interpretation check to `interpretation`, not to the wrapper:

```text
schema, interpretation_id, issuer, event_id, build, selection, observations,
comparisons, findings, missing_context, next_evidence, quality, clocks, authority
```

Reject an unsupported `interpretation.schema`, any missing or extra interpretation key, or an `authority` object whose six authority booleans are not all present and literal `false`. Unknown optional fields elsewhere in the wrapper follow the wrapper contract; unknown fields inside a closed interpretation section render unavailable rather than being interpreted.

### 6.2 JSON-to-DOM field map

#### Binding contract on Tasks 3, 4 and 6 (contract-first; `PROPOSED` until Task 6 merges)

Task 3's interpretation output, Task 4's v2 private publication, and Task 6's API responses MUST expose the exact paths below, or the task that cannot must amend this spec in its own PR before it merges. The map is `PROPOSED` until Task 6 merges. `source_text` carries original-language source text only and is shaped `source_text: {text, lang}`, where `lang` is an ISO 639-1 code (P&G filings are `en`); no ZH translation of private SEC text is produced or displayed. ZH applies only to labels, chips, stance rows, and definitions owned by this spec's copy tables. `header`, `period`, and `precision_note` remain EN/ZH pairs because they are spec-owned copy composed from typed fields, never quoted source text.

Every source-derived placeholder maps exactly as follows:

| DOM placeholder | Payload path |
|---|---|
| `data-economic-issuer` | Adapter-written receipt of `issuer.ticker`; never read |
| Current-view URL `{ticker}` | Host-supplied `issuer.ticker`, the sole source input |
| `data-economic-state` | `idle`; `loading`; `ready`; 401 → `sign_in`; 403 → `no_access`; 404 → `not_found`; 5xx, timeout, or network failure → `unavailable`; unknown response schema version → `unsupported`; any other failure → `error` |
| `[data-economic-state-chip]` | `interpretation.selection.currentness` through §5.4 |
| `[data-economic-stance]` | Ordered `interpretation.findings[].rule_id` through §5.5 |
| `[data-economic-demand]` rows | `interpretation.observations` with a demand owner metric family |
| `[data-economic-segment-rows]` rows | `interpretation.observations` with an admitted segment family |
| `[data-economic-earnings]` rows | `interpretation.observations` with an earnings family |
| Row `th` | `interpretation.observations[].label.{en,zh}` |
| Row period cell and `data-economic-period` | `interpretation.observations[].period` |
| Row basis cell and `data-economic-basis` | `interpretation.observations[].basis` |
| Row value cell | `interpretation.observations[].value_and_unit.{en,zh}` |
| `data-economic-fact-id` | `interpretation.observations[].fact_id` |
| Evidence button accessible row name | The same row `label.{en,zh}` |
| `[data-economic-findings]` items | `interpretation.findings` in server order |
| Finding text | Fixed §5.6 sentence selected by `findings[].rule_id` and page language |
| Finding `data-economic-rule` | `findings[].rule_id` |
| `[data-economic-missing]` items | `interpretation.missing_context` in server order |
| Missing-context text | Fixed §5.7 sentence selected by owner value and page language |
| Fiscal-period footer item | `interpretation.clocks.fiscal_period.{en,zh}` |
| Source-accepted footer item | `interpretation.clocks.source_accepted.{en,zh}` |
| Currentness footer item | `interpretation.selection.currentness` and `interpretation.clocks.source_currentness` |
| Evidence route `{slug}` | wrapper `slug` from the displayed response |
| Evidence route `{fact_id}` | displayed row `fact_id` |
| Evidence query `generation` | displayed wrapper `generation_id` |
| Evidence query `manifest_sha256` | displayed wrapper `manifest_sha256` |
| Evidence query `record_sha256` | displayed wrapper `record_sha256` |
| `[data-economic-evidence-header]` | evidence response `header.{en,zh}` |
| `[data-economic-evidence-period]` | evidence response `period.{en,zh}` |
| `[data-economic-evidence-generation]` | displayed wrapper `generation_id` |
| `[data-economic-evidence-manifest]` | displayed wrapper `manifest_sha256` |
| `[data-economic-evidence-record]` | displayed wrapper `record_sha256` |
| `[data-economic-evidence-text]` | evidence response `source_text.text`; `source_text.lang` identifies the original language |
| `[data-economic-evidence-digest]` | evidence response `source_sha256` |
| `[data-economic-evidence-precision]` | evidence response `precision_note.{en,zh}` |
| Company and GMI links | `interpretation.next_evidence.company_link` and `.gmi_link` when valid owner bindings exist |

### 6.3 Current-view fetch

```javascript
fetchAuthenticated('/api/earnings/v1/economic/' + issuer.ticker, {
  credentials: 'same-origin',
  cache: 'no-store',
  headers: {Accept: 'application/json'}
})
```

Capture an internal request epoch before the call. Keep exactly one current-view controller in `pending`; a new mount load aborts the prior request. Discard a late response whenever its captured epoch differs from the current epoch.

On an `mdx-auth` identity transition to signed-in while the adapter is in `sign_in`, re-run the load in place: no page reload, no re-mount, and no change to `data-economic-mounted`. On a transition to signed-out, increment the epoch, abort the current and evidence requests, close the dialog, clear private DOM text and private-bearing `data-economic-*` attributes and rows, render the fixed `sign_in` state, and keep `data-economic-mounted`. The attribute is never removed while the adapter is alive; only `destroy()` removes it. `destroy()` performs the same private-data clearing and final teardown. A load under a newly signed-in identity is the new identity's one load, not a retry.

### 6.4 Evidence fetch and dialog lifetime

An evidence click immediately opens the dialog in a loading state and performs exactly one evidence fetch for that open:

```text
GET /api/earnings/v1/records/{slug}/economic-evidence/{fact_id}?generation={generation_id}&manifest_sha256={manifest_sha256}&record_sha256={record_sha256}
```

All four pinned values come from the displayed current-view response. The request uses `fetchAuthenticated`, `credentials:'same-origin'`, `cache:'no-store'`, and `Accept:'application/json'`. It owns exactly one `AbortController`. Closing the dialog, an auth-identity change, and `destroy()` abort it; a second open starts a new single request. A failed or aborted evidence fetch leaves the dialog in its fixed unavailable/error state unless the dialog closes, in which case focus returns to the invoking evidence control. The adapter never constructs an evidence URL from mutable current state or a source URL.

### 6.5 Rendering, privacy, and links

- Render source-derived text exclusively with DOM text APIs. Never use `innerHTML`, `insertAdjacentHTML`, `eval`, `Function`, `srcdoc`, or `outerHTML` with source data.
- Perform no browser arithmetic, rounding, aggregation, sorting beyond server order, inference, modeling, scoring, or trading-label creation.
- Write no source-derived value, response, token, digest, URL, or user state to local/session storage, IndexedDB, cookies, service-worker caches, console, screenshots initiated by code, analytics, or telemetry.
- Expose no private value in a DOM attribute beyond the fixed `data-economic-*` contract.
- Language follows the existing page `data-lang` and `langchange` mechanism; dynamic text re-renders on language change without another private fetch.
- Render company and GMI links only from valid same-site owner bindings; otherwise show the fixed unresolved-links sentence. Never infer either URL from ticker or company name.

## 7. Evidence matrix

These are tests to run inside whatever host the foundation provides. A synthetic test host may prove adapter behavior, but it is not production host proof.

### 7.1 Required combinations

Run dark and light, EN and ZH, at desktop 1440 px, tablet 820 px, and mobile 390 px. Capture the expanded dossier and evidence dialog for all twelve combinations. Verify no horizontal overflow at 390 px, inner vertical scrolling at the 390 px expanded budget, collapsed height no greater than 44 px, focus visibility, and reduced-motion behavior.

### 7.2 Behavioral and adversarial checks

| ID | Required proof |
|---|---|
| B01 | Keyboard opens/closes evidence; Escape closes; focus returns exactly to the invoking control |
| B02 | Dialog focus trap and non-content scrim close |
| B03 | Synthetic hostile span/header remains inert text |
| B04 | Logout during fetch aborts and discards the private sentinel |
| B05 | Late earlier response cannot replace a newer response |
| B06 | Missing consensus/segments render fixed absence sentences and no beat/miss verdict |
| B07 | Newer filing state leaves accepted rows visible and warning copy plain |
| B08 | Freshness-unconfirmed state never says up to date |
| B09 | Unsupported interpretation schema renders unavailable and no private fields |
| B10 | Unentitled state has a real sign-in control and no teaser, blur, or private text |
| B11 | Error copy reveals no object path or credential |
| B12 | Loading geometry contains no stale private values |
| B13 | Reported, organic, and core remain distinguishable by text in both languages under grayscale |
| B14 | Evidence URL uses the displayed slug, fact, generation, manifest digest, and record digest |
| B15 | Evidence dialog aborts on close and auth change; one open makes one request |
| B16 | Company/GMI links appear only for valid owner bindings |
| B17 | Mount, destroy, remount, auth event filtering, and `data-economic-mounted="1"` lifecycle are exact |
| B18 | Private sentinel reaches no storage, console, analytics, service worker, or unintended route |
| B19 | Reduced motion introduces no mandatory movement |
| B20 | Dark and light materials are separately adjudicated from evidence artifacts |
| B21 | The foundation host's final include, init, and asset delivery are present in production-path proof |

### 7.3 Command and evidence receipt

The future build lane runs the foundation-provided browser project, scoped to these cases, for example:

```bash
python3 -m pytest tests/test_earnings_economic_browser.py -q
```

The receipt names the actual host, head, browser commands, twelve visual artifacts, and B01-B21 outcomes. It never claims production integration from a synthetic-only host or claims checks green while pending.

## 8. Resolved questions

- **Theme Tracker and XLP mounts, assets, and host wiring.** Resolved by R1A: no mount, host anchor, or asset path belongs to this document; integration requirements and deferred foundation items are in §1.
- **Two art directions and density.** Resolved by R1A with R4 and R8: the foundation owns material treatment, while §4 states binding dark, light, neutral-color, and 390 px requirements.
- **Stance.** Resolved by R3: ordered rule-ID lookup in §5.5; no response field is added.
- **Response wrapper and evidence fetch.** Resolved by R6: wrapper validation, field map, query parameters, click fetch, abort behavior, and cache behavior are in §6.
- **Copy and accessibility.** Resolved by R9: §3 supplies the sign-in control and per-row bilingual accessible names; §5 fixes all ruled EN/ZH wording, including “已是最新,” “一致预期,” and “报告每股收益与核心每股收益.”
- **Basis chips.** Resolved by R5: §4.3 requires one neutral family distinguished only by words.
- **Fallback tokens.** Resolved by R10 and superseded in ownership by R1A: this document creates no CSS tokens; the foundation's shared token system owns any token decision.
- **Actual release proof.** The foundation integration and visible-journey proof wait for the host slot, per R1A A4; API and reader proofs proceed independently.
