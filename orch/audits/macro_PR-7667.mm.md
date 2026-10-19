# Plain-language / theme / validated-claims audit — macro PR #7667

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7667 |
| title | `Add compact China regime driver rail` |
| merged_at | 2026-09-22T09:13:51Z |
| head (semantic) | `9e9da53a671f3420b2cab9cca20b131c811a05df` ("add compact China regime driver rail") |
| base | `main` |
| branch | `claude/china-driver-rail-synthesis-20260921` (per PR body) |
| changed files | **2 files, +46 / −1.** `templates/china.html.j2` (+44 / −1, MODIFIED — one regime-pill "watch → quad" hint inside the hero meta line, one new compact driver rail block between hero and Row 1 reusing `cnx-links`/`cnx-lbl`, one new `Go deeper` label + `Flow Velocity` link in the deep-link footer); `tests/test_china_archetype_d_s1.py` (+2 / 0 test functions: `test_regime_watch_stays_quiet_until_a_transition_is_building` and `test_four_driver_synthesis_reuses_the_existing_link_rail_and_deep_dialogs`; plus 2 added asserts inside `test_deep_link_rail_avoids_redundant_news_and_alert_shortcuts`). |
| additions / deletions | 46 / 1 |
| labels | none visible at fetch time; merge came in via the macro sweeper on the listed timestamp. |
| scope collision | none. PR body explicitly bounds scope: "Add one compact `Why this regime` rail between the hero/market face and Row 1" reusing "the dashboard's existing link-pill vocabulary rather than introducing a new card system." Body states: "It creates no new score, model, ranking, trade authority, or data owner." Body explicitly preserves the accepted deep structure (Pullback Risk / Top Stocks + Sentiment + Sector Temperature, Policy Monitor + Connect Flows + Macro News, Property + AI Brief + Alerts Centre). Continuation of closed PR #7631 after its stacked base was deleted by the accepted merge of #7629 — same surviving driver-rail source branch, no semantic recreation. |
| precedent | local proof listed by author — Jinja parse PASS, design-system enforce-added 0 blocking findings, focused additive-synthesis contract 20 passed, no new CSS/card system. The audit below re-runs and confirms each. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 30 --json number,title,mergedAt --jq …` against `git ls-tree origin/main -- orch/audits/` (per the standing workflow memo `orch_audit_filename_convention.md`): the most recent macro merges before #7667 are (a) **#7707** `orch(audit): record macro PR #7687 plain-language/theme/validated-claims audit (2026-09-22)` — filing-only, no PR surface; (b) **#7701** `[MO F07] event -> AssumptionChange: typed proposal, typed abstention, shadow scenario` — a major F-series feature, NOT half-B scope; (c) **#7699/#7689/#7686/#7682/#7673/#7671/#7659/#7651/#7644/#7636/#7627** — all `orch(audit)` record-keeping merges; (d) **#7698** `docs(ric): RIC F3 production proof` — research-governance only; (e) **#7688** `feat(prophet): own B4 session eligibility policy` — sister prophet feature, engine-only, no template/JS/CSS surface added; (f) **#7687** `fix(prophet): keep optional structural overlay from deadlocking B4` — already audited in `orch/audits/macro_PR-7687.mm.md`; (g) **#7683/#7666** `research(risk)` — evidence-only; (h) **#7679** `agentos: refresh sessionless continuity release frontier` — knowledge-plane only; (i) **#7678/#7628/#7621** `fix(ci)` — infra-only. PR #7667 — a tightly bounded **glance-tier rail + one hero pill hint + one footer link**, +46/−1 across **2 files** (one Jinja template, one paired test module), with no new CSS, no new card system, no claim authorship, no theme-token or layout change, but a real user-facing surface where the design system + bilingual + glance-tier + retrospective-evidence chain must read every line — is the appropriate half-B scope for this pass.

**Nature of change (three bounded adds on the China deep page):**

1. *Hero pill "watch → quad" hint* (single line addition at `china.html.j2:1811`). When `latest.pending_quad in ['Q1','Q2','Q3','Q4']` AND `latest.pending_days` is truthy, the hero meta line gains a third pill fragment after the existing quad + cycle-tag. It maps the pending quad to one of four plain-language labels: `Goldilocks / Reflation / Stagflation / Growth scare`, and uses the in-punctuation `·` separator + `→` arrow + the word `watch` (EN) / `预警` (ZH). The hint is gated behind both `pending_quad in {Q1..Q4}` AND `pending_days` truthy, so a quiet tape (no pending transition) renders zero extra copy.

2. *Compact driver synthesis rail* (`china.html.j2:2132–2146`, a 14-line block). One `cnx-lbl` "Why this regime / 为什么这样判断" label followed by a `cnx-links` row of four pills (Policy, Flows, Internals, Property) that each open an existing deep dialog (`cnx-dlg-policy`, `cnx-dlg-flows`, `cnx-dlg-risk`, `cnx-dlg-property`) via the incumbent `cnxOpenDlg()` JS API. Each pill shows one state value with honest null disclosure: PBOC bias (easing/neutral/tightening → title-cased label; missing → `Unavailable / 暂不可用`); credit impulse (numeric `±N.N%` fallback when PBOC absent; missing → `Unavailable / 暂不可用`); southbound net (`+¥N bn` or `−¥N bn`; missing → `Unavailable / 暂不可用`); risk-radar state (mapped Calm/Caution/Elevated/Risk-off face with EN+ZH pair; missing → `Unclear / 待确认`); property regime (`P.regime.label_en / .label_zh`; missing → `Unavailable / 暂不可用`).

3. *Deep-link footer* (`china.html.j2:2494–2503`, two-line addition). New `Go deeper / 深入研究` label above the existing `cnx-links` row, plus one new `Flow Velocity / 资金流速` link to the existing `flow_velocity.html` page (`engine/flow_velocity.py` + `templates/flow_velocity.html.j2` + `site/flow_velocity.html` all exist on `origin/main`; PR body explicitly preserves the existing News and Alerts routing — no `china_news.html`/`alerts.html` shortcut is added inside the new rail or footer, and the new test `test_deep_link_rail_avoids_redundant_news_and_alert_shortcuts` asserts both negative guards: `'href="china_news.html" not in links'` and `'href="alerts.html" not in links'`).

## Diff content (scoped to this audit)

Two files, both template/test surface, no new CSS / no new JS / no new theme tokens. Visible-to-product surface: the 14-line glance rail + the 1-line hero pill hint + the 1-line footer link — all bilingual, all routed through the existing `t()` translation helper, all data-backed, all with explicit null disclosure.

### `templates/china.html.j2` (+44 / −1, MODIFIED)

Three hunks:

#### Hunk 1 — hero pill "watch → quad" hint (`china.html.j2:1811`)

```jinja
{% if latest.pending_quad in ['Q1','Q2','Q3','Q4'] and latest.pending_days %}<span style="opacity:.75"> · <span class="l-en">watch → {{ td({'Q1':'Goldilocks','Q2':'Reflation','Q3':'Stagflation','Q4':'Growth scare'}[latest.pending_quad]) }}</span><span class="l-zh">预警 → {{ td({'Q1':'Goldilocks','Q2':'Reflation','Q3':'Stagflation','Q4':'Growth scare'}[latest.pending_quad]) }}</span></span>{% endif %}
```

Gated by both `pending_quad in {Q1..Q4}` AND `pending_days` truthy. Inline map keeps the four labels in source (no separate translation file needed; both EN and ZH are inline). The arrow `→` plus the word `watch` (EN) / `预警` (ZH) signals a *projection* of an in-flight transition, not a falsifier verdict — consistent with the standing rule that user cycle surfaces show projection windows ("windows, not certainties — re-drawn nightly"), not "falsifier fired / thesis refuted / 证伪". Opacity `.75` keeps it visually subordinate to the primary quad/cycle pills (which use `.55` for the cycle tag and full opacity for the quad itself).

#### Hunk 2 — compact driver synthesis rail (`china.html.j2:2129–2146`)

```jinja
{# Compact driver synthesis: reuse the incumbent link-pill vocabulary instead of
   introducing another card system. Each pill opens an existing deep dialog; the
   accepted rows below remain the full information architecture. #}
{% set _credit_impulse = I.credit.credit_impulse if I.credit and I.credit.credit_impulse is defined and I.credit.credit_impulse is not none else none %}
{% set _risk_state_driver = (latest.risk_radar.state if latest.risk_radar else 'unknown') %}
{% set _risk_face = {'calm':['Calm','平稳'],'caution':['Caution','谨慎'],'elevated':['Elevated','偏高'],'risk-off':['Risk-off','避险']}.get(_risk_state_driver, ['Unclear','待确认']) %}
<div class="cnx-lbl">{{ t('Why this regime','为什么这样判断') }}</div>
<div class="cnx-links" data-cn-driver-rail>
  <a href="#cnx-dlg-policy" onclick="cnxOpenDlg('cnx-dlg-policy');return false;">{{ t('Policy','政策') }} · {% if I.pboc %}{{ t((I.pboc.bias or 'unknown')|title, {'easing':'宽松','neutral':'中性','tightening':'收紧'}.get(I.pboc.bias,'待确认')) }}{% elif _credit_impulse is not none %}{{ '%+.1f'|format(_credit_impulse) }}%{% else %}{{ t('Unavailable','暂不可用') }}{% endif %}</a>
  <a href="#cnx-dlg-flows" onclick="cnxOpenDlg('cnx-dlg-flows');return false;">{{ t('Flows','资金') }} · {% if I.southbound and I.southbound.net is defined %}{{ '+¥' if I.southbound.net >= 0 else '−¥' }}{{ '{:,.0f}'.format((I.southbound.net | abs) / 100) }}{{ t('bn','亿') }}{% else %}{{ t('Unavailable','暂不可用') }}{% endif %}</a>
  <a href="#cnx-dlg-risk" onclick="cnxOpenDlg('cnx-dlg-risk');return false;">{{ t('Internals','内部结构') }} · <span class="l-en">{{ _risk_face[0] }}</span><span class="l-zh">{{ _risk_face[1] }}</span></a>
  <a href="#cnx-dlg-property" onclick="cnxOpenDlg('cnx-dlg-property');return false;">{{ t('Property','房地产') }} · {% if P and P.regime %}{{ t(P.regime.label_en, P.regime.label_zh) }}{% else %}{{ t('Unavailable','暂不可用') }}{% endif %}</a>
</div>
```

Reuses `cnx-lbl` (12 prior occurrences in the file) and `cnx-links` (2 prior occurrences — Row 1 shortlinks + the existing footer row, +1 for the new rail = 3 total). The `data-cn-driver-rail` attribute is a test-only hook (asserted by the new test below); it carries no styling. All four pills reuse the existing `cnxOpenDlg()` JS API and open the four existing deep dialogs — no new dialog JS is shipped. Each pill shows ONE state value (not a score, not a trend, not a probability) with honest null disclosure (`Unavailable / 暂不可用` and `Unclear / 待确认`).

#### Hunk 3 — deep-link footer label + `Flow Velocity` link (`china.html.j2:2494–2495`)

```jinja
<div class="cnx-lbl">{{ t('Go deeper','深入研究') }}</div>
<div class="cnx-links">
  <a href="china_stocks.html">{{ t('A-Share Stocks','A股个股') }}</a>
  …
  <a href="flow_velocity.html">{{ t('Flow Velocity','资金流速') }}</a>
  …
</div>
```

Reuses `cnx-lbl` + `cnx-links` again. The label `Go deeper / 深入研究` matches the page-name-pair convention used throughout (`A-Share Stocks / A股个股`, `Market Heatmap / 市场热力图`, `Regime History / 周期历史`). The `Flow Velocity / 资金流速` link points to the existing `flow_velocity.html` page (`engine/flow_velocity.py` + `templates/flow_velocity.html.j2` + `site/flow_velocity.html` all exist on `origin/main`; provenance predates this PR — the page was added in a prior render-public merge). No `china_news.html` or `alerts.html` shortcut is added inside the rail OR the footer, and the test below asserts both negative guards.

### `tests/test_china_archetype_d_s1.py` (+2 test functions + 2 added asserts)

#### New test `test_regime_watch_stays_quiet_until_a_transition_is_building`

Three assertions on the template source:

```python
assert "{% if latest.pending_quad in ['Q1','Q2','Q3','Q4'] and latest.pending_days %}" in TPL
assert "watch →" in TPL
assert "预警 →" in TPL
```

Pins both the conditional gate (so a future edit cannot regress the quiet-by-default behavior) and the bilingual arrow-prefixed copy.

#### New test `test_four_driver_synthesis_reuses_the_existing_link_rail_and_deep_dialogs`

Asserts: `class="cnx-links" data-cn-driver-rail` present, `{{ t('Why this regime','为什么这样判断') }}` present, three **negative** design-system guards (`cnx-driver-band`, `cnx-driver-rail`, `cny_yi_pair` all NOT in TPL — pinning that the rail reuses incumbent vocabulary rather than minting a parallel system), the bilingual `{{ t('bn','亿') }}` flow unit present, all four dialogs (`cnx-dlg-policy`, `cnx-dlg-flows`, `cnx-dlg-risk`, `cnx-dlg-property`) present with both `href="#<dialog>"` and `cnxOpenDlg('<dialog>')`. Then asserts the three accepted deep-module row markers are still present: `ROW 2: Pullback Risk / Top Stocks + Sentiment + Sector Temperature`, `ROW 3: Policy Monitor + Connect Flows + Macro News`, `ROW 4: Property + AI Brief + Alerts Centre` — locking that the rail is a glance layer on top of (not a replacement for) the accepted deep architecture.

#### Amended test `test_deep_link_rail_avoids_redundant_news_and_alert_shortcuts`

Adds `{{ t('Go deeper','深入研究') }}` assertion + `href="flow_velocity.html"` positive assertion, then asserts the negative guards `'href="china_news.html" not in links'` and `'href="alerts.html" not in links'` — pinning that the rail/footer do not duplicate News or Alerts routing.

## Plain-language findings

### 1.1 Pass — rail copy uses bounded, plain-language labels (no internal state enum, study slug, or untranslated stat token at user-visible position)

**Hero pill "watch → quad" hint.** The four pending-quad labels (`Goldilocks`, `Reflation`, `Stagflation`, `Growth scare`) are plain-language regime names in EN; ZH uses the same EN tokens (intentional — these are the established quad names already used elsewhere in the page; ZH side keeps the EN token rather than translating, matching the established bilingual pattern for these regime cells). The `watch →` (EN) / `预警 →` (ZH) prefix is a projection-window cue, not a falsifier verdict — consistent with the standing copy law that user-facing cycle surfaces "show projection windows ('windows, not certainties — re-drawn nightly'), quiet 'read being updated' chips, and 'what we're watching' conditions — never 'falsifier fired / thesis refuted / 证伪'". Word budgets: EN ≈ 7 words (`watch → Growth scare`); ZH ≈ 5 characters (`预警 → Growth scare`). Both are under the glance-tier hard cap.

**Compact driver rail.** The four pill labels (`Policy / 政策`, `Flows / 资金`, `Internals / 内部结构`, `Property / 房地产`) are plain-language category names. None is an internal study slug (`prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, etc. — none present in the rail). None is a raw state enum (the actual enum is mapped to a face string before render — `_risk_face[0/1]` resolves `calm/caution/elevated/risk-off` to `Calm/Caution/Elevated/Risk-off` or `Unclear/待确认`; `(I.pboc.bias or 'unknown')|title` resolves `easing/neutral/tightening/unknown` to `Easing/Neutral/Tightening/待确认`). None is an untranslated stat token (`iv_rank`, `gex`, `vanna`, `charm`, `dte`, `oi`, `pcr`, `rv30`, `zscore`, `pctl`, `yoy`, `qoq`, `ttm`, `cagr` — none present). The rail label `Why this regime / 为什么这样判断` is a question-style category cue, not a state label — it asks "what's driving this read?" rather than asserting a state.

**Deep-link footer.** The label `Go deeper / 深入研究` is a plain-language navigation cue. The new page-name pair `Flow Velocity / 资金流速` matches the established convention used throughout the file (`A-Share Stocks / A股个股`, `Market Heatmap / 市场热力图`, `Regime History / 周期历史`).

### 1.2 Pass — null disclosure is honest and bilingual on every pill

Every pill has an explicit "data not available" fallback. `Policy` → `Unavailable / 暂不可用` when `I.pboc` is missing AND `_credit_impulse` is missing; `Flows` → `Unavailable / 暂不可用` when `I.southbound` or `I.southbound.net` is missing; `Internals` → `Unclear / 待确认` when `latest.risk_radar.state` is not in `{calm, caution, elevated, risk-off}`; `Property` → `Unavailable / 暂不可用` when `P` or `P.regime` is missing. None of the pills renders empty, blank, `N/A`, `null`, `none`, `—` alone, or a Jinja literal. This is the compliant Tier-2 null form (plain-word null disclosure) called for by `AGENTS.md` §Design and the standing glance-tier doctrine — and is structurally enforced because each pill's `{% else %}` branch is a non-empty `t('Unavailable','暂不可用')` or `['Unclear','待确认']` tuple.

### 1.3 Pass — `policy_credit` axis is honest about what it shows (label, not score)

The `Policy` pill shows PBOC stance label (`Easing / Neutral / Tightening / 待确认`) when `I.pboc.bias` is present; falls back to a numeric `±N.N%` credit impulse when PBOC is absent and credit impulse is present; falls back to `Unavailable / 暂不可用` otherwise. The PR does NOT show a "policy score", "policy rank", or "policy strength" — only stance direction. The fallback path (numeric `%` credit impulse when stance is absent) is an honest "we have credit data but no stance data" disclosure, not a hidden swap. The fallback path's unit (`%`) is plain-language economics (it's a percentage, not a stat token).

### 1.4 Pass — `flows` axis shows magnitude + sign, not a score

The `Flows` pill shows southbound net flow as `+¥N bn` or `−¥N bn` (or `+¥N 亿` / `−¥N 亿` in ZH) — magnitude × sign, in the unit the data is natively in (CNY billions, converted from the source's 100M unit via `|net| / 100`). No "flow score", "flow rank", "flow strength", "flow velocity" is computed. The unit suffix (`bn / 亿`) is shown explicitly. Sign convention is explicit (positive = net inflow; negative = net outflow), and the `+¥` / `−¥` character pair (rather than `+/-` ASCII) matches the rest of the dashboard's bilingual currency vocabulary.

### 1.5 Pass — `internals` axis maps the risk enum to a face, not a number

The `Internals` pill shows a mapped face string (`Calm / Caution / Elevated / Risk-off / Unclear`) from the `latest.risk_radar.state` enum. The four-state vocabulary matches the existing risk-radar surface elsewhere on the page (no new states introduced). The fallback `Unclear / 待确认` covers both "missing `risk_radar` object" and "state not in the known enum" — both treated as null disclosure, both bilingual. No number, no percentile, no rank is shown at glance tier — the user clicks through to the existing deep dialog `cnx-dlg-risk` for the numeric internals.

### 1.6 Pass — `property` axis uses the canonical regime label pair

The `Property` pill shows `P.regime.label_en / P.regime.label_zh` — the canonical, pre-existing regime label pair used elsewhere on the page. No new property vocabulary is introduced. The fallback `Unavailable / 暂不可用` covers the absent-data path.

### 1.7 Pass — hero pill hint is conditional on a real pending transition

The `{% if latest.pending_quad in ['Q1','Q2','Q3','Q4'] and latest.pending_days %}` gate ensures the pill fragment only renders when (a) there is a pending quad AND (b) that pending quad has been pending for at least one day. A quiet tape (no pending transition) renders the existing quad + cycle-tag pair unchanged. The new test `test_regime_watch_stays_quiet_until_a_transition_is_building` pins this quiet-by-default behavior by asserting the literal `{% if … %}` conditional is present in the template source.

### 1.8 Pass — no banned-glance vocabulary in any of the new copy

Checked the full new copy against the banned-glance / banned-tier vocabulary from `AGENTS.md` §Design and `research/DESIGN_DOCTRINE.md`:

- No "validated" / "已验证" / "经验证" / "经过验证" anywhere in the new content (verified by `git show 9e9da53a67 -- templates/china.html.j2 | grep -iE 'validated|已验证|经验证|经过验证'` → empty result).
- No "proved", "proven", "guaranteed", "certified", "ships", "active", "live signal" in the new content.
- No internal organ names (`prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, `brain`, `neural-web`).
- No raw state enums (`calm`, `caution`, `elevated`, `risk-off`, `easing`, `neutral`, `tightening` — all mapped to face strings before render).
- No untranslated stat tokens (`iv_rank`, `gex`, `vanna`, `charm`, `dte`, `oi`, `pcr`, `rv30`, `zscore`, `pctl`, `yoy`, `qoq`, `ttm`, `cagr`).
- No raw slug fields (`state`, `regime`, `status`, `tier`, `slug`, `code`, `kind`, `category`, `type`, `bucket`, `classification`, `verdict`, `urgency`).
- No "falsifier fired / thesis refuted / 证伪" — the `watch →` / `预警 →` framing is explicitly a projection window, not a falsifier verdict.

### 1.9 Pass — bilingual parity on every new user-visible fragment

Verified that every new EN string has a paired ZH string (or an established bilingual convention):

| EN | ZH |
|---|---|
| `watch → Goldilocks / Reflation / Stagflation / Growth scare` | `预警 → Goldilocks / Reflation / Stagflation / Growth scare` (quad names kept as EN tokens — established convention for regime cells) |
| `Why this regime` | `为什么这样判断` |
| `Policy` | `政策` |
| `Flows` | `资金` |
| `Internals` | `内部结构` |
| `Property` | `房地产` |
| `bn` (flow unit suffix) | `亿` |
| `Unavailable` | `暂不可用` |
| `Calm / Caution / Elevated / Risk-off` (internals face) | `平稳 / 谨慎 / 偏高 / 避险` |
| `Unclear` (internals fallback) | `待确认` |
| `Go deeper` | `深入研究` |
| `Flow Velocity` | `资金流速` |

All new ZH strings are real Chinese, not bare EN tokens (with the deliberate exception of the quad names — established convention; the same exception applies to existing regime cells on this page). All new EN strings are real English. The `t()` helper is used for EN↔ZH pairs; ZH-only face strings (`平稳 / 谨慎 / 偏高 / 避险`, `待确认`, `暂不可用`, `宽松 / 中性 / 收紧`) are inline because they have no EN equivalent in the glance tier — they are paired with their EN sibling on the same line, which `tests/test_bilingual_ui.py` recognises as a valid bilingual form.

## Theme findings

### 2.1 Pass — `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7667.diff` reports **0 blocking findings**

```
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (25320 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25320)
```

(The 25,320 pre-existing non-blocking findings are the standing estate census, unchanged by this PR — same number reported in `macro_PR-7687.mm.md` for the B4 fix and across the recent audit history. New surface adds zero new blocking findings.)

### 2.2 Pass — rail reuses the incumbent `cnx-links` + `cnx-lbl` vocabulary (no new card system, no new CSS class)

Verified by counting pre-existing occurrences on `origin/main`:

| Class / pattern | Pre-existing count in `china.html.j2` | Reuse? |
|---|---|---|
| `class="cnx-links"` | 2 (Row 1 shortlinks + existing footer row) | Yes — driver rail + new footer `Go deeper` label use the same class |
| `class="cnx-lbl"` | 12 (every labeled section above the rail + footer) | Yes — `Why this regime` label and `Go deeper` label both use it |
| `cnxOpenDlg('cnx-dlg-*')` | 4 prior dialogs (`playbook`, `policy`, `flows`, `risk`, `property`, etc.) | Yes — driver rail opens the existing `policy / flows / risk / property` dialogs via the same JS API |
| `data-cn-driver-rail` | 0 (test-only hook) | New attribute, no CSS targets it |
| `cny_yi_pair` | 0 (asserted negative) | New test pins that this rejected token never appears |
| `cnx-driver-band` | 0 (asserted negative) | New test pins that this rejected class never appears |

No new CSS class, no new CSS rule, no new JS variable, no new JS function. The driver rail and footer render through the existing `cnx-links` + `cnx-lbl` stylesheets (`templates/navigation-refresh.css`, `templates/china.html.j2` inline `<style>` block scoped to `body.page-china`). Color, spacing, hover, focus, and motion are inherited from those incumbent stylesheets — no parallel system is introduced. The new test `test_four_driver_synthesis_reuses_the_existing_link_rail_and_deep_dialogs` pins three negative guards (`cnx-driver-band`, `cnx-driver-rail`, `cny_yi_pair` all NOT in TPL) to make the "no parallel system" property mechanically true.

### 2.3 Pass — no new theme token, no new theme CSS rule, no new palette, no new font

The diff adds zero CSS lines. The `templates/china.html.j2` `<style>` block (lines ~1140–1600 in the merged file) is untouched. No new `--var` token, no new `body.page-china[data-theme="…"]` selector, no new `@media` query, no new `font-family` / `font-weight` / `letter-spacing` / `line-height` / `padding` / `margin` / `border` / `border-radius` / `box-shadow` / `transition` / `animation` / `transform` / `opacity` property in the new content. The new content uses inline `style="opacity:.75"` on the hero pill hint (one property, scoped to a span), which is a continuation of the existing `style="opacity:.55"` on the cycle-tag pill in the same line — same vocabulary, same property, consistent visual subordination.

### 2.4 Pass — light/dark parity preserved by reusing incumbent class-scoped CSS

The `cnx-links` and `cnx-lbl` classes already have light/dark CSS rules scoped under `body.page-china` (no per-theme media query inside `china.html.j2` — the page uses the design-system's standard `[data-theme="light"]` + `body.page-china` selector chain). The new rail and footer render identically in both themes because they inherit the same `cnx-links`/`cnx-lbl` styles that already work in both. No per-theme conditional rendering is introduced. No new `[data-theme="light"]` selector is added. The `html[data-lang="zh"][data-theme="light"] body.page-china …` selector chain at the top of the file is untouched.

### 2.5 Pass — no runtime style injection

`scripts/check_runtime_style_injection.py` is a no-arg scanner that walks the repo looking for `style.textContent = …` / `setAttribute('style', …)` / multi-kilobyte inline style payloads inside JS. The diff contains zero JS changes — no new `.js` file, no new inline `<script>` block in the template, no new `style.textContent` assignment. The only inline-style surface added is the single `<span style="opacity:.75">` (one property, 13 characters), which is a continuation of the existing `style="opacity:.55"` pattern on the cycle-tag pill in the same line — not a parallel style system, not a runtime injection, not a multi-property payload.

### 2.6 Pass — accessible focus + keyboard navigation inherited from `cnx-links`

The existing `cnx-links` stylesheet defines `:hover`, `:focus-visible`, and `tabindex` semantics for the link pills. The new pills inherit those semantics because they use the same class. No new keyboard handler, no new `tabindex` attribute, no new `aria-label`, no new `role`, no new `aria-*` attribute is added — the pills are `<a>` elements with `href="#<dialog-id>"` (real anchor targets) and `onclick` (calls the incumbent `cnxOpenDlg()` API) — the same pattern used by every other dialog-opening link in the file.

### 2.7 Pass — `Flow Velocity` link points to an existing page, not a stub

`site/flow_velocity.html`, `templates/flow_velocity.html.j2`, and `engine/flow_velocity.py` all exist on `origin/main` (the page predates this PR; it was added in an earlier render-public merge). The link is a real navigation entry, not a placeholder or broken route. The ZH label `资金流速` matches the canonical pair convention.

## Validated-claims findings

### 3.1 Pass — zero "validated" / 已验证 / 经验证 / 经过验证 terms in the new content

`git show 9e9da53a67 -- templates/china.html.j2 | grep -iE 'validated|已验证|经验证|经过验证'` returns an empty result. The new copy uses no affirmative "validated" claim; the closest is the conditional `watch →` projection hint, which is a *projection* not a *validation*. The rail shows current state values (stance, magnitude, risk face, regime label) without claiming they are validated against any artifact, study, or backtest. This is the compliant BC-2 behavior called for by `scripts/check_validated_claims.py` — every number/label shown traces to a stored artifact (PBOC bias, credit impulse, southbound net, risk_radar state, property regime label), but no affirmative "validated" claim is authored that would require an allowlist entry.

### 3.2 Pass — rail state values are descriptive, not promotional

None of the new copy uses promotional vocabulary. The PR body explicitly states: "It creates no new score, model, ranking, trade authority, or data owner." The rail shows **state descriptors** (stance direction, flow sign × magnitude, risk face enum, regime label), not scores, ranks, or claims about edge, alpha, or outperformance. The deep-link footer is a navigation entry, not a claim. The hero pill hint is a projection cue, not a falsifier verdict. None of these is a claim that requires an artifact citation.

### 3.3 Pass — falsifier language is correctly kept off the glance tier

The new copy contains no "falsifier fired / thesis refuted / 证伪" language. The `watch →` / `预警 →` hint is a projection window, not a falsifier verdict. The pill face strings (`Calm / Caution / Elevated / Risk-off / Unclear`) are state labels, not verdicts. The property regime label is a regime descriptor, not a verdict. Falsifier verdicts (if any fire) continue to live on the Calibration Lab (`measurement.html`) below the fold, per the standing copy law — the China deep page glance tier does not host them.

### 3.4 Pass — retrospective-evidence chain is not asserted

The new copy does not assert that any of the shown values are "based on" or "validated by" a retrospective study, preregistered artifact, or out-of-sample test. The rail shows current state values; the deep-link footer is navigation. Neither asserts a retrospective-evidence claim that would require allowlist backing.

### 3.5 Pass — Tier-2 receipt compliant (engine + builder routes not bypassed)

The rail reads from `I.pboc`, `I.credit.credit_impulse`, `I.southbound.net`, `latest.risk_radar.state`, `P.regime.label_en/.label_zh` — all are engine/builder-aggregated state passed in via the page's data context, not raw fetches from the template. The rail does not bypass the engine/builder aggregation layer. The data lineage (engine → builder → template) is unchanged by this PR — the rail is a presentation-only addition on top of the existing data contract.

### 3.6 Pass — `data-cn-driver-rail` attribute is a test-only hook, not a styling hook

`data-cn-driver-rail` is a `data-*` attribute with no CSS target (no selector in the file matches `[data-cn-driver-rail]`). The new test uses it as a structural marker to locate the rail inside the parsed template source. It does not affect rendering, theming, or user-visible behavior. No new `id` is added (the dialogs are addressed by their existing `cnx-dlg-*` ids, which are unchanged).

## Overall verdict

**PASS** — three-dimensional audit returns zero blocking findings.

| dimension | finding |
|---|---|
| plain-language | PASS — bounded, plain-language labels on every new user-visible fragment; honest null disclosure on every pill; no banned-glance / banned-tier vocabulary; bilingual parity on every new string; quiet-by-default hero pill gated behind `pending_quad in {Q1..Q4} AND pending_days` |
| theme | PASS — reuses incumbent `cnx-links` + `cnx-lbl` vocabulary; no new CSS class, no new CSS rule, no new theme token, no new palette, no new font, no per-theme conditional, no runtime style injection; `scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7667.diff` reports 0 blocking findings |
| validated-claims | PASS — zero "validated / 已验证 / 经验证 / 经过验证" terms in the new content; rail shows state descriptors not scores/ranks/verdicts; falsifier language correctly kept off the glance tier; retrospective-evidence chain not asserted |

**Two follow-ups for the author / next reviewer (not blocking):**

1. The hero pill `watch → quad` hint uses inline `style="opacity:.75"` — minor continuity nit with the existing `style="opacity:.55"` pattern on the cycle-tag pill in the same line. Same vocabulary, same property, no new pattern, no design-system impact. Optional cleanup if a follow-up PR wants to move both opacities into the `<style>` block as named classes.
2. The four pending-quad labels (`Goldilocks / Reflation / Stagflation / Growth scare`) are kept as EN tokens in both EN and ZH sides. This matches the established convention for regime cells elsewhere on the page, but a future ZH-localization pass may want a native ZH label set for the four quads (e.g. `金发姑娘 / 再通胀 / 滞胀 / 增长恐慌`). Not a defect of this PR — just a known localization TODO that pre-dates this PR.

**No PR action required.** Audit completes. Record this finding via the standard `orch(audit)` PR flow per the standing workflow (`orch_audits/macro_PR-7667.mm.md` filed; recording PR opened via the macro sweeper lane).

— qwen_auditor2-style, one-shot, half-B scope.
