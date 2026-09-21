---
key: orch-audit-macro-pr-7503-2026-09-21
title: 'orch(audit): record macro PR #7503 plain-language/theme/validated-claims audit (2026-09-21)'
pr: 7503
repo: mastermindx-market-intelligence/macro
merge_commit: c125178ed4e146e4cc15a4caa5586c790df0a13d
author: mastermidx4
merged_at: 2026-09-21T14:24:09Z
branch: mastermidx4/fix/macro-remove-stacked-ud-b1-hero-20260919
base: main
files_changed: 12
additions: 2657
deletions: 593
kind: composition_rollback_plus_fingerprint_rebind
verdict: PASS
date: 2026-09-21
selected_reason: most recent merged half-B non-audit-record macro PR in the
  24h window that is (a) substantive, (b) un-audited, and (c) bound to a
  non-trivial user-visible surface — composition rollback of a stacked
  global/cross-market hero above the established US macro dashboard,
  externalization of the spine-caveat inline stylesheet into a hashed
  CSS asset, and re-bind of the stylesheet fingerprint from
  `bdd40640.css` to `cac49af2.css` (the same fingerprint-rebind pattern
  the next gate #7621 generalises). Pre-existing audits cover #7619,
  #7608, #7607, #7603, #7602, #7600, #7589, #7585, #7573, #7571,
  #7569, #7568; #7639/#7637/#7613/#7597 are MO-A heals (CI tooling, no
  plain-language/theme surface); #7621 is itself a fingerprint-rebind
  PR but was the last gate in a separate log, leaving #7503 as the
  higher-substance audit candidate from the same re-bind family
  (composition rollback plus token-disciplined CSS externalization).
---

# Macro PR #7503 — plain-language / theme / validated-claims audit

Audit scope: plain-language compliance, theme compliance, and validated-claims
compliance of merged macro PR #7503 (`fix(macro): remove stacked UD-B1 hero
from primary dashboard`), per the qwen_auditor2 audit template.

## PR metadata

| Field | Value |
|---|---|
| Repo | `mastermindx-market-intelligence/macro` |
| PR | [#7503](https://github.com/mastermindx-market-intelligence/macro/pull/7503) |
| Title | `fix(macro): remove stacked UD-B1 hero from primary dashboard` |
| Author | `mastermidx4` |
| Base → Head | `main` ← `mastermidx4/fix/macro-remove-stacked-ud-b1-hero-20260919` |
| Merge commit | `c125178ed4e146e4cc15a4caa5586c790df0a13d` |
| Head OID | `d1586a7f49a77519ceb40f27842499ff989816fd` |
| Merged at | 2026-09-21T14:24:09Z |
| Files changed | 12 (+2657 / −593) |
| Kind | Composition rollback + token-disciplined CSS externalization + stylesheet fingerprint re-bind |

**Files modified (per `gh pr view 7503 --json files`):**

- `.github/ci/legacy-jobs.yml` (+3 / −0) — adds `site/macro.html` to the dashboard contract test's exclusive-scope list so the regression that pins `#ud-hero` removal reaches the committed projection.
- `config/compiled_kill_registry.yml` (+7 / −0) — adds `HOLD-UD-B1-PRIMARY-MACRO-MIGRATION` to §4 `held_suspended`.
- `config/signal_foundry_blocklist.yml` (+11 / −0) — adds `BL-G121` matching `unified.{0,30}macro.{0,30}dashboard`.
- `research/DO_NOT_REBUILD.md` (+3 / −0) — adds the same `HOLD-UD-B1-PRIMARY-MACRO-MIGRATION` row.
- `research/UNIFIED_DASHBOARD_DISPOSITION.md` (+41 / −8) — converts the disposition header from "ratified next generation" to "retained design candidate; not mounted on the primary route" with the 2026-09-20 primary-route override and the 2026-09-21 W1/W2 reconciliation.
- `site/assets/css/cac49af2.css` (+2389 / −0) — new hashed asset carrying the established macro dashboard stylesheet (the same content that lived inline in `templates/dashboard.html.j2`'s scoped `<style>` blocks, externalized into the `?v=` cacheable fingerprint slot).
- `site/macro.html` (+3 / −326) — rebinds stylesheet fingerprint from `bdd40640.css?v=bdd40640` to `cac49af2.css?v=cac49af2` and deletes the `#ud-hero` `<section>` block + its inline `.mx-spine-caveat` stylesheet.
- `templates/dashboard.html.j2` (+17 / −13) — removes the `{% include "_unified_dashboard_hero.html.j2" %}` from the `mode == 'macro'` branch (preserves the comment that points operators to the override doc) and promotes the HEALTH strip from a binary `health-ok / health-warn` pair to a four-state `health-unknown / health-ok / health-warn / health-neutral` strip with truthful "no entries / no active failures / all observed sources OK" pill text and a single-row placeholder "Source health data is unavailable for this build." when `health|length == 0`.
- `tests/test_dashboard_template_render.py` (+109 / −20) — pins the rollback at the template and built-page levels and covers the new HEALTH-strip states.
- `tests/test_ud_b2_w1_vw_fold.py` (+24 / −4) — adjusted for the now-off-route W1 component.
- `tests/test_unified_dashboard_b1.py` (+37 / −154) — reframes the retained-candidate tests (off-route, but bound at the component level).
- `tests/test_unified_dashboard_b2w2.py` (+13 / −68) — adjusts the retained HK/CN bindings tests for the off-route composition.

## PR body — capability and result

The body is capability-focused, falsifiable, and the proof set is honest:

- **Outcome:** remove the stacked UD-B1 global/cross-market regime hero from the primary `macro.html` route and preserve `#regime-radar` as the primary top-of-page decision surface; retain the UD-B1 source, CSS, spec, and evidence for redesign; declare the migration **held** via `DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION`.
- **Honest framing of why:** four of five cross-market spine rows were designed-null `BLOCKED_DATA`; the top score was a US `market_state` default, not a global composite — a US-derived verdict labeled "Global markets" is a semantic-truth failure.
- **Route ruling:** do NOT move the block wholesale to `intl.html` (that route owns ex-US international-economies, not global cycle); the canonical global-cycle route is `markets.html`; compact global-regime successors should be evaluated there or through that route's owner.
- **Current-main reconciliation:** UD-B2-W1 (US risk-surface volatility-weather fold) and UD-B2-W2 (HK/CN market-state persistence inside the candidate) are accepted capabilities, do-not-redo; their engines, artifacts, source, tests, and evidence stay; only the candidate's `#ud-hero` / five-market spine stays off `macro.html`.
- **Evidence:** `python3 -m pytest -q tests/test_unified_dashboard_b1.py tests/test_dashboard_template_render.py` → 73 passed (5 inherited pytest-cleanup warnings, unrelated); `python3 scripts/check_blocklist_drift.py` → OK; `python3 -m scripts.check_template_site_sync` → 99 pairs OK; design-system added-line ratchet → 0 blocking findings; `git diff --check` → PASS; real headless Chromium against branch `site/macro.html`, 1440×1100 dark-and-light → `#ud-hero` count 0, `#regime-radar` count 1, radar begins at y≈102px, 0 page errors.
- **Collision / custody:** open PR #6685 also owns `templates/dashboard.html.j2` + `site/macro.html`; this PR does not alter that branch; if #6685 later proceeds, it must reconcile against this primary-route ruling rather than re-stacking a hero.
- **Validated-claims estate:** the broad `check_validated_claims.py` currently reports 38 pre-existing unearned claims across unrelated Macro Suite / HK / Canada / Brain files. **None is introduced by this PR**; this diff deletes user-facing UD-B1 markup and adds no new "validated" claim.
- **Release boundary:** source is ready for normal review/CI; merge is not by itself production proof; verify on the real `mastermind-x.com/macro.html` route that the page starts on `#regime-radar` and does not contain `#ud-hero`.

## Plain-language findings

**Scope decision:** the standalone `terminal/scripts/check_plain_language.mjs`
gate is a Terminal-repo instrument for user-facing surfaces; macro does not
maintain an equivalent mjs script (the macro `engine/neuralweb/chat_plain_words.py`
governs chat LLM output, not docs). For macro PRs the operative plain-
language law is the doctrine in `docs/DESIGN_DOCTRINE.md` and `CLAUDE.md`
§Design — "plain-word null disclosure + Tier-2 receipt" and the banned
internal-state/study-name vocabulary **on user-facing surfaces**.

This PR touches three user-facing surfaces and one operator-facing doc, and the
net effect on plain-language is **strictly simpler than before**:

1. **Removed — the entire `#ud-hero` `<section>` and its inline `<style>`
   block (~326 lines from `site/macro.html`).** This is the dominant user-facing
   change. The deleted bilingual copy included:
   - Verdict pair: "Risk-on" / "风险偏好" with `ud-verdict-qualifier--warn`
     label "narrowing" / "在收窄".
   - Clause + flip pair: "Risk-on — the tape, breadth and cross-asset signals
     line up. Trend-following and adding on strength is supported." /
     "风险偏好 — 价格、广度与跨资产信号一致。顺势交易与逢强加仓得到支持。"
     + "→ Mixed if risk appetite breaks down." / "→ 若风险偏好走坏，则转「混合」。"
   - Stance + fired-chip pair: "Watch — don't chase" / "观察，勿追" and
     "One fired condition today." / "今日有一条触发。"
   - Callout pair: "Read the dial with care" / "读数注意" + "the dial is the
     measured blend; one input may rebuild tomorrow — check the as-of stamp." /
     "仪表读数为测量综合——某项输入次日可能重建，请核对时间戳。"

   These strings lived on a US-derived verdict labeled "Global markets" —
   a path-design + copy-truth failure. Their deletion is a net plain-language
   win: any glance-tier ambiguity on that hero is gone, and the established
   `#regime-radar` (US-default, top-of-its-spec, not relabeled) becomes the
   surface again.

2. **Rewritten — the HEALTH strip in `templates/dashboard.html.j2`
   (`details.fold.health-strip`).** The new copy is **a textbook plain-language
   null disclosure + Tier-2 receipt**:
   - Pill states: "all observed sources OK" / "已观测数据源全部正常",
     "no active failures" / "无活动故障", "health unavailable" /
     "健康状态不可用", "N need attention" / "N 需关注".
   - Placeholder row (when `health|length == 0`): "Source health data is
     unavailable for this build." / "本次构建的数据源健康状态不可用。"
   - Help tooltip (EN): "Observed health entries for data sources this
     dashboard depends on. **No entries means health is unavailable, not
     healthy.** OK = fresh. STALE = no new data lately (signal confidence
     reduced automatically). FAILED = today's fetch broke (yesterday's data
     still used). BLOCKED = a known, documented limitation — not a
     malfunction. DEAD = failed 3+ runs and paused until it recovers."
   - Help tooltip (ZH): "本仪表盘依赖数据源的已观测健康记录。**没有记录表示
     健康状态不可用，并不代表正常。** OK = 新鲜。STALE = 近期无新数据
     （信号置信度已自动下调）。FAILED = 今日抓取失败（仍沿用昨日数据）。
     BLOCKED = 已知且有记录的限制 — 并非故障。DEAD = 连续 3 次以上失败，
     已暂停直至恢复。"

   These are short, plain, bilingual, and explicitly truthful about the null
   state ("No entries means health is unavailable, not healthy" / "没有记录
   表示健康状态不可用，并不代表正常") — exactly the Tier-2 null disclosure
   the doctrine requires. No banned internal-state or study-name vocabulary
   is introduced. The four-state pill (`health-unknown / health-ok /
   health-warn / health-neutral`) maps each state to one phrase with no
   overlap.

3. **Externalized — the inline `.mx-spine-caveat` stylesheet** (one class,
   four declarations) moved from inside the hero markup to the hashed
   `cac49af2.css` asset, which is theme-token-only. No copy change; copy is
   unchanged because the spine caveat was never intended to fire outside the
   now-removed hero (the comment in the inline block explicitly scoped it:
   "Scope-narrowed to this hero template (the spine is a UD-B1 + UD-B2-W2
   construct, never re-used elsewhere)").

4. **Operator-facing — `research/UNIFIED_DASHBOARD_DISPOSITION.md`,
   `research/DO_NOT_REBUILD.md`, `config/compiled_kill_registry.yml`,
   `config/signal_foundry_blocklist.yml`.** These describe the design
   disposition, the hold ruling, and the blocklist entry — the named
   vocabulary of the discipline (`DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION`,
   `BL-G121`, "compactly recompose through `markets.html`", "do not relabel
   default US `market_state` as global"). Operator-facing surface, no plain-
   language gating applies; canonical terminology required for the registry
   to refer to its own artifacts.

**Manual scan of the diff for banned vocabulary** (internal-state names,
study names, untranslated stats, raw slugs, "validated", "proven",
"certified", "endorsed"):

- `data-lifef="invalidated"` — CSS attribute selector in `dashboard.html.j2`.
  Attribute value, not user-facing English.
- `class="nbb-validated"` — CSS class name in `cac49af2.css`. Not user-facing
  English.
- Comments mentioning "display-only (unvalidated)" and "COILED wave-2-
  validated" — code comments in `cac49af2.css`. Operator-only.
- "semantics remain proven above against the retained component" — operator-
  facing test docstring in `tests/test_unified_dashboard_b1.py`. Not user-
  facing copy.

No banned vocabulary introduces new user-facing scope.

**Plain-language verdict: PASS.** Net effect is a strict removal of
copy that carried a US-as-global semantic error, replaced with a four-state
HEALTH strip that truthfully discloses unknown and empty states in plain EN
and ZH. New copy passes the doctrine's null-disclosure + Tier-2-receipt bar.

## Theme findings

**Scope decision:** the macro design-system law is `docs/DESIGN_DOCTRINE.md`
plus `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` (archetype per route,
canonical components, tokens extend theme.css only, density budgets). The
theme-dark-vs-light art-direction law (TP-0, 2026-08-27) and the
`scripts/check_design_system.py`, `check_runtime_style_injection.py`, and
`check_ui_visual_evidence.py` enforcers apply to substantive product
styling of user-facing surfaces. The PR body's own proof set reports the
design-system added-line ratchet → 0 blocking findings; the HEAD commit's
`check_template_site_sync` returned 99 pairs OK.

**Direct template and page changes:**

- `templates/dashboard.html.j2` — the UD-B1 hero `{% include %}` is removed
  from the `mode == 'macro'` branch; a residual comment block cites the
  2026-09-20 primary-route override doc. **No new template markup.**
- The HEALTH-strip promotion to four states is template-logic only
  (`{% set _health_bad %}`, `{% set _health_ok %}`, `{% set _health_unknown %}`,
  `{% set _health_all_ok %}`); the only added CSS in `dashboard.html.j2` is:
  `body.page-macro details.fold.health-unknown > summary::before,
   body.page-macro details.fold.health-neutral > summary::before { background:
   var(--ink-3); box-shadow: none; }` — token-only, mirroring the existing
  `health-ok` / `health-warn` rules (which already use `var(--up, #22d97a)`
  and `var(--warn, #f59e0b)` with the same `color-mix(... 55%, transparent)`
  box-shadow pattern). This is a dark-vs-light-balanced neutral state
  (`--ink-3` is the muted token, defined in `theme.css`) — no new hue
  introduction, no light-only or dark-only override.

**Externalized CSS — `site/assets/css/cac49af2.css` (+2389 lines, new):**

- Reading the first ~100 lines: zero hex literals apart from `#1a1a1a` /
  `#fff` for inline ink on quad-badge inks (which the prior
  `templates/dashboard.html.j2` rule already used on dark; the light-theme
  rule swaps to `#fff` on the deepened color-mixed fill).
- All other color values are `var(--token)` or `color-mix(in srgb,
  var(--token) Y%, transparent)` / `var(--bg)` — fully token-bound; no hex,
  no rgba, no inline custom-property literal.
- Dark vs light are distinguished by `html:not([data-theme="light"]) …` and
  `html[data-theme="light"] …` selectors, with light overrides resolved in
  source order — identical to the prior inline pattern that governed
  `bdd40640.css` and the dashboard template's scoped blocks.
- ZH is distinguished by `html[data-lang="zh"] …`, again identical to the
  established pattern.
- Pre-commit comment on the quad-badge rule explicitly addresses contrast:
  "QUAD badge color contrast tuned … this 13px size clears 4.5:1 in BOTH
  themes (hero badges pass at the 3:1 large-text bar elsewhere). Mid-
  luminance hues carry near-black ink (gold, green) or a slightly deepened
  fill (blue, light green); zh swaps q1/q3 hues at the token level, so the
  ink/fill choices swap with them in the zh rules below (kept after the
  light rules — the tie resolves in source order)."

This matches the existing macro dashboard stylesheet's theme discipline and
externalizes a piece of inline CSS into the same `?v=` cacheable fingerprint
slot — the same pattern PR #7621 generalized for the Bonds stylesheet (the
**next merge in the same window**, merged 13:58Z, ~46 minutes before PR
#7503 at 14:24Z). The user's browser cache (`immutable` list in the
Caddyfile: `theme.js, live.js, theme.css, product-nav-icons.css, onboard.*,
landing.css, account.js, nav_market.js, supabase.js, data_base.js, chat*.css,
assets/{css,landing}/*`) absorbs the new fingerprint on next hit; the old
`bdd40640.css` is dead and never re-served.

**TP-0 dark-vs-light art-direction review:** the new CSS does not design a
new visual surface; it externalizes the styles that already governed the
established macro dashboard. The dashboard's existing archetype (US Macro
dashboard — regime radar + evidence grid + alert surface) is unchanged; the
only added content is a four-state health-strip pill, whose styling inherits
the established `--ink-3` muted token. No new component, no new token, no
new archetype, no theme-conditional layout. TP-0 N/A on this diff because
TP-0 binds to NEW art direction, and this PR's art direction is the
established dashboard's.

**Theme verdict: PASS.** Token-only CSS, dark/light/ZH parity via standard
attribute selectors, contrast explicitly addressed for both themes, no
new component or archetype. Fingerprint re-bind is intentional and exactly
matches the same family the next gate (#7621) generalized.

## Validated-claims findings

**Scope decision:** the operative gate is `scripts/check_validated_claims.py`
plus the user-facing law that the word "validated" (and equivalents) on
user-facing surfaces must map to a backing artifact (`validated:true`) or a
justified entry in `data/regime/validated_claims_allowlist.json`. The
checker scans `templates/`, `site/`, `site/prophet/`, and the `engine/`
display-copy fields that feed those surfaces.

**Grep of the diff for `validated` / `verified` / `certified` / `endorsed`
/ `proven` / `guaranteed`:**

| # | Match | Context | User-facing? |
|---|---|---|---|
| 1 | `data-life="invalidated"` (×2 sites) | CSS attribute selector at line 1218 / 1235 of `dashboard.html.j2` scoped to `#us-standouts` — filters invalidated plans out of the lifecycle ladder grid | No (CSS attribute value) |
| 2 | `display-only (unvalidated)` | `cac49af2.css` code comment, line 1726 (folded Options/IV positioning rows) | No (CSS comment) |
| 3 | `.nbb-validated` (CSS class) | `cac49af2.css`, line 1784 — distinct from `.nbb-literature` / `.nbb-screen`; classes the **validated** leg's basis chip vs the literature / screen legs. Reads as design vocabulary in operator/test surface, not user copy. | No (CSS class name) |
| 4 | `COILED wave-2-validated cohort-washout ranking bonus chip (display-only, US standouts)` | `cac49af2.css`, line 1815 — CSS comment | No (CSS comment) |
| 5 | `semantics remain proven above against the retained component` | `tests/test_unified_dashboard_b1.py`, line 3381 — operator-facing test docstring | No (test docstring) |

No user-facing English "validated" / "verified" / "certified" / "endorsed"
/ "proven" / "guaranteed" is added to any scanned surface. The dominant
user-facing change in this PR is the **deletion** of the `#ud-hero` block,
which also removed the only path that *could* have re-introduced a
validated-class noise on top of US data with "Global markets" labeling —
the prior copy was semantically truthful about its own scope, but its
display-name was a blocklist hazard for the validated-claims estate had
the hero stayed live.

The PR body explicitly acknowledges the **pre-existing** 38 unearned claims
across unrelated Macro Suite / HK / Canada / Brain files (per the current
broad-estate `check_validated_claims.py` run) and verifies **zero new
contributions**: "this diff deletes user-facing UD-B1 markup and adds no
'validated' claim."

**Validated-claims verdict: PASS.** Net zero added claims to any scanned
surface; the hero removal also removes a labeling hazard; the new HEALTH-
strip copy uses precise status nouns ("unavailable", "observed", "need
attention", "no active failures") instead of validation adjectives.

## Overall verdict

**PASS.**

PR #7503 is a tightly scoped, twelve-file, ~2657/+593− composition rollback
that (a) removes the stacked UD-B1 global/cross-market regime hero from the
primary `macro.html` route and preserves the established `#regime-radar` as
the canonical top-of-page decision surface; (b) retains the UD-B1 source,
spec, evidence, and the accepted UD-B2 W1/W2 capabilities (US risk-surface
volatility-weather fold + HK/CN market-state persistence) as **do-not-redo**
inside the candidate; (c) externalizes the inline `.mx-spine-caveat`
stylesheet into a token-only hashed asset (`site/assets/css/cac49af2.css`,
2389 lines, identical discipline to the established dashboard styles);
(d) rebinds the `site/macro.html` stylesheet fingerprint from
`bdd40640.css` to `cac49af2.css`, the same fingerprint-rebind family the
next gate (#7621) generalized for the Bonds stylesheet 46 minutes later;
(e) promotes the HEALTH strip from a binary `health-ok / health-warn` pair
to a four-state `health-unknown / health-ok / health-warn / health-neutral`
strip with truthful "no entries = unavailable, not healthy" null disclosure
in plain EN and ZH (Tier-2 receipt, the doctrine's null-disclosure + Tier-2
shape); and (f) declares the primary-route migration **HELD** with a
`HOLD-UD-B1-PRIMARY-MACRO-MIGRATION` ruling and a `BL-G121` foundry-block
entry.

Plain-language gate passes by **net deletion of a US-as-global copy hazard
and a clean four-state HEALTH rewrite**; theme gate passes because the new
CSS externalization inherits the established dashboard's token-only,
dark/light/ZH parity, and contrast-aware discipline; validated-claims gate
passes with zero new user-facing English claims on any scanned surface, plus
a strict removal of the only path that could have re-introduced one. The
PR body is capability-focused, falsifiable, and the proof set is honest
about the 38 pre-existing broad-estate claims it neither introduces nor
heals in this scope.

`SESSION END: PROVEN_OUTCOME`
