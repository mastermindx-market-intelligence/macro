# Plain-language / theme / validated-claims audit — macro PR #7710

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7710](https://github.com/mastermindx-market-intelligence/macro/pull/7710) |
| title | `fix: validate capital-need facts and repair issuer panel rendering` |
| mergedAt | 2026-09-22T22:45:18Z |
| merge commit | `9074ddb48e7f74f6f831e832427272b63cc670ba` (squash onto `main` from `claude/ssd-f09-capital-need-vertical-…`) |
| branch tip | `b124b8d8bf7ae94b52196684bc3c3bc62f4b0f41` (the CI wiring head cited in body) |
| audit head | `origin/main` (post-merge), audit-time `ac731aec23` |
| files | **10 changed, 1901 +, 78 −.** Engine: `engine/capital_need.py` (NEW, +368), `engine/cash_runway.py` (+233/−33). Builders: `scripts/build_debt_maturity.py` (+7/−3), `scripts/build_stock_library.py` (+61/−2), `scripts/build_ticker_pages.py` (+77/−1). UI template: `templates/_debt_maturity.html.j2` (+110/−28). Tests: `tests/test_capital_need.py` (NEW, +702), `tests/test_cash_runway.py` (+325/−11). Fixture: `tests/fixtures/cash_runway/synthetic_burn.json` (+2). CI: `.github/ci/legacy-jobs.yml` (+16). |
| half-B label | **half-B issuer-panel vertical** — first issuer capital-need vertical for F09, not the broader F09 program. By the operator's vertical plan the panel itself reads as "B half" not "A half" — no cross-issuer ranking, no rail, no composite, no signal colour; only one debt-maturity panel extended with three new evidence-gated sub-blocks (`cash reported`, `scenario runway`, `near-term cash cover / gap`). |
| program surface | The per-ticker `debt-maturity` section on issuer pages (`templates/_debt_maturity.html.j2`). Three new sub-blocks below the existing bucket ladder: (i) `dmw-runway` rebuilt from `capital_need.v1` reported facts + scenario; (ii) `dmw-capital-need` showing `value_pct` cash coverage of `y1` reported principal + the typed `not_applicable` state for zero-debt issuers; (iii) a stale-scenario disclosure under `dmw-nullwhy` when the underlying annual filing is stale. |
| scope (per body) | (a) A pure `capital_need.v1` adapter validates producer schema, canonical CIK, issuer scope, USD units, filing identity, annual cash-flow duration, filing/acquisition/evaluation clocks, freshness, bucket completeness, finite numeric inputs before deriving coverage, gap or runway. (b) Reported cash, operating cash flow, capex and debt remain distinct from free cash flow and the constant-cash-flow runway scenario. (c) Zero reported debt has a typed `not_applicable` ratio; missing data never becomes zero. (d) The page reassembles the view from debt/cash source blocks at render time, regenerates canonical debt bucket order, labels, amounts, totals, counts and percentages — cached coverage/runway or display strings cannot override validated facts. (e) The panel anchors maturity buckets to fiscal period end and discloses annual dates, accession, filing date, acquisition time and evaluation date. |
| durable owner | Engine adapter `engine/capital_need.py` (NEW). Reads `engine.cash_runway.read_cash_runway_view` and the debt-maturity block from the existing producer lane (`scripts/build_debt_maturity.py`); renders via `templates/_debt_maturity.html.j2` invoked from `scripts/build_ticker_pages.py` (+77/−1). No new data product, no new persistence path. |
| checks (body claims) | (1) Adapter+cash-producer suite: 245 passed. (2) Final page-context display/ordering/zero/missing-state controls: 5 passed. (3) Earlier combined adapter/cash/debt suite: 303 passed, 1 skipped. (4) Integrated head `1192d662e9`: 332 passed, 1 skipped (one page-run test could not read `data/universe/membership.parquet` in the sparse checkout). (5) Final CI wiring head `b124b8d8bf` adds `engine/capital_need.py` to two remaining curated scopes; the curated import closure test passed in 688.37s. (6) Final exact-head GitHub CI run [35790309771](https://github.com/mastermindx-market-intelligence/macro/actions/runs/35790309771): SUCCESS, all 12 packs. |
| gating scripts | `python3 scripts/check_validated_claims.py` → exit non-zero with **38 PRE-EXISTING UNEARNED claims — zero anchored to any PR-touched file** (`grep` for `capital_need|cash_runway|debt_maturity|build_ticker_pages|build_stock_library|build_debt_maturity` against the 38 hits returns no overlap; the 38 hits land on the macro-suite pages, `engine/market_os/macro_workspaces/consumer.py`, and `templates/_macro_suite_shell.html.j2` — all pre-existing on main before the squash). `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7710.diff` not re-run in this single pass (template-only delta with no CSS additions; the diff reuses existing `.dmw` / `.dmw-runway` panel classes — see §Theme findings). |

## Plain-language findings (tier-1 + tier-2 surface)

### Tier-1 (glance) — clean

The debt-maturity panel's user-facing copy is plain English/Chinese on every cell. No banned vocabulary (operator 2026-07-27, #3821: `falsifier` / `refute` / `thesis` / `disproven` / `证伪`) in any user-visible position. No machine slugs, no internal state names, no `debt_maturity.v1` literals bleed into copy. The PR replaces one ambiguous prior phrase ("next 12 months") with the explicit fiscal-period-end anchor ("12-month bucket following fiscal period end YYYY-MM-DD"), which is a deliberate plain-language upgrade, not a regression.

| cell | EN | ZH |
|---|---|---|
| lede (12-mo reported) | `In the 12-month bucket following fiscal period end YYYY-MM-DD, it reported $X due — about Z% of its disclosed principal.` | `在财年期末 YYYY-MM-DD 之后12个月的区间内，已披露到期本金为 $X，约占其披露本金的 Z%。` |
| lede (12-mo not reported) | `The 12-month bucket following fiscal period end YYYY-MM-DD is not reported. The years below are what the filing did report.` | `文件未披露财年期末 YYYY-MM-DD 之后12个月区间的到期金额；下方为其确实披露的年度。` |
| anchor disclosure | `All maturity buckets are measured from fiscal period end YYYY-MM-DD, not from today.` | `所有到期区间均从财年期末 YYYY-MM-DD 起算，而非从今天起算。` |
| y1 bucket label | `First 12 months after period end` | `报告期末之后首12个月` |
| unreported bucket | `not reported` | `未披露` |
| debt unavailable | `The debt figures are unavailable until issuer and filing inputs are verified.` | `发行人与报告数据核实前，债务金额暂不可用。` |
| runway — observed cash | `Cash reported at YYYY-MM-DD: $X.` | `截至 YYYY-MM-DD 披露的现金：$X。` |
| runway — self-funding | `Operating cash flow exceeded or equaled equipment spending over YYYY-MM-DD to YYYY-MM-DD; no cash burn to measure.` | `在 YYYY-MM-DD 至 YYYY-MM-DD 期间，经营现金流不低于设备支出，无可衡量的现金消耗。` |
| runway — months | `At the cash-burn pace reported over YYYY-MM-DD to YYYY-MM-DD, that cash represented about N months. This scenario excludes debt payments and future financing.` | `按 YYYY-MM-DD 至 YYYY-MM-DD 期间披露的现金消耗速度，该现金约对应 N 个月。此情景不包括债务偿还与未来融资。` |
| runway unavailable | `A cash-flow scenario is unavailable until the filing inputs are verified.` | `报告数据核实前，现金流情景暂不可用。` |
| coverage — derived | `Cash reported at YYYY-MM-DD covers Z% of issuer-reported principal in the 12-month bucket following that fiscal period end.` | `截至 YYYY-MM-DD 披露的现金可覆盖该财年期末之后12个月区间内发行人已披露到期本金的 Z%。` |
| coverage — gap | `Cash shortfall against that reported principal: $X` | `相对该已披露本金的现金缺口：$X。` |
| coverage — zero principal (typed NA) | `The filing reports zero principal in the 12-month bucket following YYYY-MM-DD; a cash coverage ratio does not apply.` | `文件披露 YYYY-MM-DD 之后12个月区间的到期本金为零，因此现金覆盖比率不适用。` |
| coverage — partial | `Capital-need coverage is partial; incomplete or incompatible filing inputs are not combined.` + `Any available cash-flow scenario is context only. Missing or incompatible inputs are not replaced with zero or a financing forecast.` | `资本需求覆盖信息不完整；不会合并不完整或不兼容的报告数据。` + `可用现金流情景仅供参考；缺失或不兼容的输入不以零值或融资预测替代。` |
| coverage — not available | `Capital-need coverage is not available for this issuer yet.` + `Reported facts remain separate from the cash-flow scenario until identity and filing provenance are confirmed.` | `该发行人的资本需求覆盖信息暂不可用。` + `在确认身份与报告来源之前，已披露事实与现金流情景保持分离。` |
| stale-scenario disclosure | `The runway scenario uses a stale annual filing and is not a current coverage assertion.` | `现金跑道情景使用已过时的年度文件，不代表当前覆盖能力。` |

The template reuses the existing `.dmw-lede` and `.dmw-null` / `.dmw-nullwhy` style classes (no new CSS class names in the diff). The disclosure line "This scenario excludes debt payments and future financing" is the operative plain-language design choice — it FORETELLS the scope of the runway number without leaking the `scenario` engine state name.

### Tier-2 (sources) — anchored

The existing `details.dmw-detail` block is preserved for the `complete` branch (it still renders the filing's accession / period end / unit / bucket reported count for `debt_maturity.status == 'reported'`). The capital-need branch adds a sibling `p` that names the annual period, accession and filing date directly: `Annual period YYYY-MM-DD — YYYY-MM-DD · USD · 10-K · <accn> · Filed YYYY-MM-DD.` That is a tier-2 receipt, not a glance-tier claim.

### State semantics — three typed outcomes

| state | copy |
|---|---|
| `complete`, pair-valid, y1>0, cover derived | `Cash reported at X covers Z% of issuer-reported principal in the 12-month bucket following that fiscal period end.` |
| `complete`, pair-valid, y1==0 | `The filing reports zero principal in the 12-month bucket following X; a cash coverage ratio does not apply.` (typed NA — not a 0% ratio, not a missing-data crash) |
| `partial` | `Capital-need coverage is partial; incomplete or incompatible filing inputs are not combined.` |
| `not_applicable` / not valid | `Capital-need coverage is not available for this issuer yet.` |
| scenario `stale` (post-state, all branches) | `The runway scenario uses a stale annual filing and is not a current coverage assertion.` |

The five rows are NOT semantic synonyms of "neutral / no signal / unknown / broken". Even the designed-null row carries an action verb ("not yet", "partial — not combined", "stale — not a current assertion") rather than a bare apology.

### Banned-vocabulary audit

`git diff 9074ddb48e^..9074ddb48e -- templates/_debt_maturity.html.j2 engine/capital_need.py engine/cash_runway.py | grep -iE 'falsif|refut|证伪|disproven|thesis'` → **0 hits**. The copy uses "verified", "not reported", "partial", "stale" — descriptive lifecycle words, never the operator-banned diagnostic vocabulary.

### No translated text in `title=` attributes (CI-guarded)

`grep -E 'title="[^"]+"' templates/_debt_maturity.html.j2` → **0 hits**. The previously-existing `<summary>` for the sources disclosure uses `{{ t(...) }}` bilingual strings, no `title=` tooltip carries translated text.

### Removed vs retained copy

The PR deletes the prior free-floating `near_term_cover_pct` paragraph ("cash on hand covers Z% of the debt coming due in the next 12 months") that lived inside the `cash_runway` branch and replaced it with the `capital_need`-gated block. This is a deliberate plain-language UPGRADE — the prior text conflated two different "near 12 months" windows (cash coverage period vs debt bucket period) when the periods could disagree; the new copy uses one anchored fiscal period end and exposes the gap (`_gap`) only when the pair is genuinely the same period. Body text "Reported cash, operating cash flow, capex and debt remain distinct from free cash flow and the constant-cash-flow runway scenario" is the design rationale.

## Theme findings

### Token discipline — no new token family introduced

The diff touches ONE template file (`templates/_debt_maturity.html.j2`) and adds no CSS files. New structural classes introduced: `.dmw-capital-need` (a panel wrapper reusing `.dmw-runway`'s grid/layout assumptions via the `data-panel="capital_need.v1"` attribute), plus inline `dmw-lede` / `dmw-null` / `dmw-nullwhy` paragraphs — all of which already exist in the estate. No new color, no new spacing scale, no new radius, no new font-size token. The `_cn_valid` boolean set at the top of the template is a Jinja namespace, not a CSS class.

### Token substitution alone is NOT what makes it pass — the new copy pre-existing

The panel uses existing `.dmw` (panel container), `.dmw-lede` (lead paragraph), `.dmw-null` / `.dmw-nullwhy` (designed-null copy) — all pre-existing tokens from the prior `_debt_maturity.html.j2`. The dark/light treatment of `.dmw` (panel + inset edge + chip background) was carried over verbatim — the PR does not change theme.css.

### Responsive composition

The new sub-blocks inherit `.dmw`'s existing responsive behaviour from the prior template (no `@media` blocks added or modified in this PR — `git diff 9074ddb48e^..9074ddb48e -- templates/theme.css scripts/theme.js` returns 0 lines). The PR's diffstat confirms this: 0 lines in `templates/theme.css`, 0 lines in `scripts/theme.js`. Mobile composition is therefore identical to the pre-existing panel — not regressed, not reworked.

### Visual verification matrix — body-claimed only (no re-render in single pass)

Body names no PNG evidence matrix for #7710 (it is a fix PR, not a UD-B2-W4B-style wave PR). Single-pass audit does not re-render — the body-claimed CI success (run [35790309771](https://github.com/mastermindx-market-intelligence/macro/actions/runs/35790309771), all 12 packs) is the receipt. Live AAPL/AMZN acceptance "remains pending actual source-bound stock-library and full dossier rebuild, publication, and browser readback" per the PR body — explicitly not claimed as done.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED

The 10 PR-touched files: `.github/ci/legacy-jobs.yml`, `engine/capital_need.py`, `engine/cash_runway.py`, `scripts/build_debt_maturity.py`, `scripts/build_stock_library.py`, `scripts/build_ticker_pages.py`, `templates/_debt_maturity.html.j2`, `tests/fixtures/cash_runway/synthetic_burn.json`, `tests/test_capital_need.py`, `tests/test_cash_runway.py`. `grep -E 'validated'` against each returns:

- `engine/capital_need.py`: 6 hits, ALL in internal Python helper names (`_validated_period`, `_validated_source`, `_validated_debt`) and the docstring `"""Expose only validated issuer facts and same-filing, fresh cash coverage."""` — internal naming, not user-facing copy.
- `engine/cash_runway.py`: 2 hits — `reader does not re-validate …` (internal comment) and the helper `"""Revalidate source blocks at render time; never trust cached arithmetic."""` (internal docstring).
- `templates/_debt_maturity.html.j2`: 4 hits — `{% set _validated_scenario = … %}` and `{% if _cash_inputs.valid and … and _validated_scenario is mapping … %}` Jinja namespace references. These are Python-side variable names, NOT rendered text. `grep -A2 'set _validated_scenario' templates/_debt_maturity.html.j2` shows the variable is only used as a boolean gate — never interpolated into user-visible HTML.
- The other 7 PR-touched files: 0 hits for `validated`.

`grep -rE 'validated' templates/_debt_maturity.html.j2 | grep -E 'title=|<p|<h[1-6]|<span|<div class'` (user-visible DOM only) → **0 hits**.

### Estate pre-existing: 38 UNEARNED (not PR-caused)

`python3 scripts/check_validated_claims.py` reports 38 unbacked claims; none anchor to PR-touched files. The 38 hits concentrate on `templates/_macro_suite_shell.html.j2` (1) + 15 `templates/macro_*.html.j2` macro-suite pages (16) + `templates/hk.html.j2` (3) + `templates/canada.html.j2` (1) + `templates/macro_suite.js` (1) + `templates/mm_brain.js` (1) + 16 mirrored `site/macro_*.html` (16) + `site/macro_suite.js` (1) + `site/mm_brain.js` (1) + `engine/market_os/macro_workspaces/consumer.py` (1) — **none** of which PR #7710 touched. This is consistent with the estate prior to the squash (the same 38 hits were already on main before the squash of #7710). Audit-time `ac731aec23` `git log --oneline 9074ddb48e^..ac731aec23 -- engine/capital_need.py engine/cash_runway.py templates/_debt_maturity.html.j2` shows the only changes after #7710 are the unrelated W2-2 (#7737) ThetaData skew accrual lane PR — none of which add a `validated` literal to the debt-maturity panel. The pattern matches the prior audit `orch/audits/macro_PR-7712.mm.md` exactly (zero PR-touched, all estate).

### Spirit: the PR REINFORCES the validated-claims law

Beyond the formal check, the PR's copy reads as a textbook "validated disclosure" surface:

- "The debt figures are unavailable until issuer and filing inputs are verified." — gates the data path; never claims it.
- "A cash-flow scenario is unavailable until the filing inputs are verified." — same gate.
- "Capital-need coverage is partial; incomplete or incompatible filing inputs are not combined." — actively refuses to claim what isn't there.
- "Any available cash-flow scenario is context only. Missing or incompatible inputs are not replaced with zero or a financing forecast." — explicit non-claim scope.
- "The runway scenario uses a stale annual filing and is not a current coverage assertion." — converts the old silent "stale" flag into a user-visible disclaimer.

These strings are the receipt that the PR delivers what the validated-claims law is for — the engine (capital_need.v1, `_validated_period`, `_validated_source`) does the validation, and the user-facing copy discloses the gate. The operator-curated `data/regime/validated_claims_allowlist.json` does not need a new entry for the debt-maturity panel because none of the user-visible copy says "validated".

## Diff content (scoped to this audit)

### `engine/capital_need.py` (NEW, +368)

`capital_need.v1` adapter. Public surface: `compose_capital_need(debt_block, cash_block, *, cutoff)`. Internal helpers: `_canonical_cik`, `_date`, `_number`, `_scope`, `_empty_result`, `_acquisition`, `_validated_period`, `_validated_source`, `_validated_debt`, `_compose_debt_view`, `_compose_cash_view`, `_compose_cover`. The schema dict keys are: `schema='capital_need.v1'`, `version=1`, `status ∈ {complete, partial, not_applicable}`, `issuer.cik/scope`, `as_of`, `coverage.{state, reasons}`, `reported.{debt_due, cash, operating_cash_flow, capex}`, `derived.{free_cash_flow, scenario_runway, near_term_cash_cover, near_term_cash_gap_usd}`, `authority.{class='context_only', display_only=True}`, `source_clock.{evaluation_as_of}`. The `_acquisition` helper extracts a timezone-bearing `fetched_at` separately from `evaluation_as_of` so the two clocks do not alias. Validation order: producer schema → canonical CIK → issuer scope → USD units → filing identity (form ∈ {10-K, 10-K/A, 20-F, 40-F}, fp=FY) → annual cash-flow duration → filing/acquisition/evaluation clocks → freshness → bucket completeness → finite numeric inputs.

### `engine/cash_runway.py` (+233 / −33)

Refactor: pulls the cash-runway producer a step closer to the `validated_source` contract. Adds `read_cash_runway_view(blocks, *, cutoff)` returning `{cash, operating_cash_flow, capex}` each with `{state, value, period, form, accn, fy, source}` typed values. Removes the prior `near_term_cover_pct` shortcut — coverage now flows through `capital_need.v1.near_term_cash_cover`, never the cash-runway adapter.

### `scripts/build_ticker_pages.py` (+77 / −1)

`render_ticker_pages()` now calls `compose_capital_need(debt_block, cash_block, cutoff=cutoff)` and passes the result through to the Jinja template as `capital_need`. The cash-runway block is no longer injected separately — the template reads `capital_need.derived.scenario_runway` and `capital_need.reported.cash`. Display-only flag is preserved (`display_only=True` on the authority block, never `True`).

### `scripts/build_debt_maturity.py` (+7 / −3)

Adds the canonical CIK ledger read fallback `{note, tickers: {...}}` plus legacy flat maps. Acquisition timestamps survive stock-library assembly separately from evaluation dates.

### `scripts/build_stock_library.py` (+61 / −2)

Pulls `fetched_at` (timezone-bearing) into the stock-library payload, distinct from the evaluation date.

### `templates/_debt_maturity.html.j2` (+110 / −28)

Three substantive template changes:

1. `_cn_valid` namespace set at the top — gates every `capital_need.*` reference. The boolean is true only when `capital_need.schema == 'capital_need.v1'`, `version == 1`, `authority.class == 'context_only'`, `authority.display_only is sameas true`, `derived` and `reported` are mappings.
2. The 12-month lede now anchors to fiscal period end: `In the 12-month bucket following fiscal period end YYYY-MM-DD, it reported $X due — about Z% of its disclosed principal.` (replaces the prior "next 12 months" phrasing). The new anchor-disclosure paragraph `All maturity buckets are measured from fiscal period end YYYY-MM-DD, not from today.` is the plain-language receipt for that anchor.
3. The `cash_runway` branch is replaced by a `capital_need` branch — the same dollar figures render with a stronger typed-state coverage (typed NA for zero y1 principal, partial-not-combined for incomplete inputs, not-available for unresolved identity).

The existing `details.dmw-detail` sources disclosure is preserved for the `reported` branch (filing accession, period end, unit, buckets-reported count).

### Tests (NEW: `test_capital_need.py` +702; `test_cash_runway.py` +325 / −11)

`tests/test_capital_need.py` covers: schema/version gating, CIK canonicalisation (zfill-10, ASCII digit-only, ≤10 chars, reject int 0), scope whitelist `{issuer, issuer_reported, consolidated}`, form whitelist `{10-K, 10-K/A, 20-F, 40-F}`, annual cash-flow duration requirement (`fp=FY`), filing/acquisition/evaluation clock validation, freshness cutoff, bucket completeness, finite numeric guard (rejects NaN, inf, ±1.7976931348623157e+308 boundary, bool), zero-y1 typed NA, partial-not-combined, stale disclosure, AAPL 290%/self-funding receipt, AMZN partial-no-cash-facts receipt, partial-period-mismatch fixture, controlled-synthetic 20-month/500% scenario. `tests/test_cash_runway.py` retains the prior scenario tests and adds the `fetched_at` clock separation tests.

### `tests/fixtures/cash_runway/synthetic_burn.json` (+2)

Synthetic same-period control fixture — the 20-month / 500% scenario cited in the body. The fixture keeps the controlled-synthetic flag in the JSON metadata; `compose_capital_need` is expected to refuse the fixture if the producer schema check fails (which it does by design).

### `.github/ci/legacy-jobs.yml` (+16)

Adds `engine/capital_need.py` to two remaining curated job scopes — closes the curated-import-closure gate.

## Overall verdict

**PASS** on plain-language, theme, and validated-claims.

- **Plain-language — PASS.** The 12-month anchor disclosure ("All maturity buckets are measured from fiscal period end YYYY-MM-DD, not from today") and the stale-scenario disclosure ("not a current coverage assertion") are exemplary plain-language upgrades. No banned vocabulary in user-visible positions. No `title=` attributes carrying translated text. Null/partial/stale states are typed, not blank.
- **Theme — PASS.** No new CSS files, no new token families, no `theme.css` / `theme.js` changes. Reuses existing `.dmw` / `.dmw-lede` / `.dmw-null` / `.dmw-nullwhy` classes. Dark/light treatment of `.dmw` is unchanged and inherits the panel treatments from the prior estate.
- **Validated-claims — PASS (formal) + REINFORCEMENT (spirit).** `python3 scripts/check_validated_claims.py` reports 38 PRE-EXISTING UNEARNED claims — zero anchored to PR-touched files. The 4 hits inside `templates/_debt_maturity.html.j2` are Jinja variable names (`_validated_scenario`) that are never interpolated into HTML; the 6 hits inside `engine/capital_need.py` are Python helper names (`_validated_period`, `_validated_source`, `_validated_debt`) — internal naming, not user-facing copy. The PR's user-facing copy ("until issuer and filing inputs are verified", "context only", "not a current coverage assertion") is the explicit non-claim shape the validated-claims law exists to enforce.

### Gaps / receipts to read

- Live AAPL/AMZN browser readback remains pending per body — the CI run [35790309771](https://github.com/mastermindx-market-intelligence/macro/actions/runs/35790309771) is the pre-publication receipt, but a 35794040579 render run is awaiting actual job admission (intended runner `pc-render-1` is online + idle but lacks `render-linux` eligibility — body says the fleet owner is reconciling). This is a fleet-lane, not a content, gap.
- The 38 PRE-EXISTING UNEARNED claims predate #7710; #7710 itself is clean. The estate carry-over is the same gap this audit pattern has flagged for every prior PR in the audit series.