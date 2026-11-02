# Plain-language / theme / validated-claims audit — macro PR #7577

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7577 |
| title | `sector-theme-subtheme architecture + STSI-1 plan` |
| merged_at | 2026-09-21T06:31:07Z |
| head (integration) | `536e99caf6a5171de1433de45049733756270b37` |
| base | `main` at `e0dc4946cd53234e1a3479d872adabd81680f744` (per body "Plan compatibility was checked against Macro `main@e0dc4946cd53234e1a3479d872adabd81680f744`") |
| branch | `claude/sol-001/sector-theme-subtheme-intelligence-architecture-20260920` (architecture carrier — body says implementation MUST begin on a fresh worktree/branch from `origin/main`, NOT on this branch) |
| changed files | **2 markdown files, +3,557 / −0.** `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md` (+816 NEW), `docs/superpowers/plans/2026-09-21-stsi1-sector-federation-technology-dossier.md` (+2,741 NEW). Zero template / CSS / JS / data / product-runtime / render / workflow / governance / agentos surface touched in this PR. |
| additions / deletions | 3,557 / 0 |
| labels | (DRAFT / HOLD — body explicit: "**Do not mark Ready, add `merge-on-green`, enable auto-merge, merge, deploy or infer product acceptance.**" Release condition: "Chairman reviews and approves both the architecture and the STSI-1 implementation plan.") |
| capability state | `SPEC_AND_PLAN_COMPLETE / REVIEW_HELD` (per body). Parent product mission remains incomplete. |
| scope collision | none — body is explicit that #7526 / #7455 / #7508 / #7252 / #7283 / #7211 are preserved as the existing implementation carriers; "STSI-1 does not duplicate or edit active implementation carriers"; no product source, generated site, runtime, workflow, data, authority or deployment path is changed. |

**Why this PR is the half-B pick.** The 24-h unaudited merge set excludes audit-record PRs (#7651, #7644, #7636, #7627, #7612, #7606, #7598, #7588, #7587, #7582, #7580), pure CI fixes with already-filed audits (#7614, #7639), and previously audited substantive PRs (#7619, #7608, #7607, #7603, #7602, #7600, #7589, #7585). Of the remaining 24-h unaudited merges — #7628 (CI canary), #7637 (CI design-governance fetch fallback), #7621 (CI test repair), #7613 (MO-A heal), #7597 (MO-A heal), #7599 (research risk), #7586 (research risk), #7577 (architecture/plan), #7576 (commodities pacing) — #7577 is the largest substantive content carrier (3,557 lines) and the only one whose plain-language surface is reviewer-relevant: a frozen architecture plus a test-first implementation plan that already names the dark/light × EN/ZH × 1440/390 evidence matrix, the bilingual glance copy budgets, the typed-null disclosure rules, and the JS-renders-only / owner-produces-classification separation. It is the half-B pick with the most reviewer-relevant prose surface and no theme/JS/CSS/data surface change to enforce against.

**Nature of change (half-B plan-freezing + architecture-frozen type).** (i) A 816-line architecture doc that names eight named carriers, the conflict class set (`ALIGNED`, `TIMEFRAME_SPLIT`, `SCOPE_SPLIT`, `FRESHNESS_SPLIT`, `COVERAGE_SPLIT`, `AUTHORITY_SPLIT`, `GENUINE_CONTRADICTION`, `UNAVAILABLE`), the page-role upgrades for Sector Central / sector / subsector / Theme Tracker / theme-detail / source-local subtheme / Atlas, the named-dimensions-not-fused-score ruling, and the rights-aware / latest-belief / correction-safe / typed-null behavior contract. (ii) A 2,741-line test-first implementation plan with eight numbered tasks, exact file lists, exact discriminating tests, exact commands, exact commit boundaries, exact failure behavior, and exact production proof — including the TP-0 visual evidence matrix (dark/light × EN/ZH × 1440/390) and the controlled-degraded-fixture matrix (404 / stale / optional-unavailable / hash-mismatch-rejected-before-publication). Both files freeze capability state at `SPEC_AND_PLAN_COMPLETE / REVIEW_HELD` and explicitly defer implementation to a fresh `origin/main` worktree.

## Diff content (scoped to this audit)

The diff is two markdown documents inside `docs/superpowers/`. There is **zero** template / HTML / JS / CSS / data / workflow / render / runtime / agentos surface. The plain-language / theme / validated-claims laws therefore have only the prose surfaces to read, but those surfaces are reviewer-relevant: the plan names the canonical headline budgets, the typed-disagreement vocabulary, the page-role copy, and the bilingual EN/ZH exemplar strings that the implementation must adopt.

### `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md` (+816, NEW)

Architecture scope: "an owner-preserving intelligence federation with page-specific projections". Distinguishes sector, subsector/group, canonical theme, source-local subtheme, basket and company/security identities. Preserves direct/primary versus supplemental/proxy basket relationships. Defines the conflict class set listed above. Defines page roles for Sector Central, sector dossiers, Subsector Confluence, subsector dossiers, Theme Tracker, theme details, source-local subtheme dossiers and Theme Atlas/heatmaps. Preserves named dimensions rather than fused scores. Makes participation, concentration, persistence, material change, evidence sufficiency and parent-relative decomposition first-class. Requires rights-aware, latest-belief, correction-safe and typed-null behavior. Keeps rank/gate/size/escalate/trade/Prophet-modification permissions **false**. Decomposes delivery into STSI-1 through STSI-6 (this PR freezes only STSI-1).

The closing paragraph of the spec body is explicit and load-bearing:

> *This document creates no implementation, deployment, prediction, ranking, gating, sizing, portfolio, or trading authority.*

That sentence is the validated-claims / theme-art-direction disclaimer line; it bounds every reviewer question about what this PR is and is not allowed to claim.

### `docs/superpowers/plans/2026-09-21-stsi1-sector-federation-technology-dossier.md` (+2,741, NEW)

Eight numbered tasks (test-first), each with `Files:`, `Step 1: Complete required design preflight` (which reads `docs/DESIGN_DOCTRINE.md`, `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`, and the canonical specimen, and uses the repository's approved frontend-design skill/tool in the implementation environment), explicit preflight for current `sectors/XLK.html` baseline capture in dark/light × EN/ZH × 1440/390, explicit art directions (Dark: "command-center instrument panel; restrained depth; no glowing dashboard clutter." / Light: "research sheet; cool canvas; white material cards; hairline boundaries; shadow rather than glow."), and the existing-global-navigation-family rule ("Keep the existing global navigation family and `theme.css`; no third header or parallel token system."). Each subsequent step names the exact files, the exact discriminating tests, the exact commands, and the exact commit boundary. Task 5 contains the EN/ZH exemplar strings:

| EN | ZH |
|---|---|
| `Sector intelligence` | `板块情报` |
| `What is happening inside Technology` | `科技板块内部正在发生什么` |
| `Loading governed read…` | `正在加载治理研判…` |
| `Detailed read unavailable` | `详细研判暂不可用` |
| `Detailed read unavailable without JavaScript. The existing sector analysis below remains available.` | `未启用 JavaScript，详细研判暂不可用；下方现有板块分析仍可使用。` |

These strings appear inside an HTML mock block and are explicitly the design-time exemplar the implementation must adopt; they are not yet live. Glance-tier word budgets are named in the plan: headline ≤ 34 English words / ≤ 44 Chinese characters where natural; posture ≤ 18 English words; conflict summary ≤ 18 English words. Technical / internal states are confined to details / tooltips / evidence drawer. The plan enforces: "**Light art direction:** functional token swapping is not acceptance."

The plan's CSS example block (lines 2092–2115 of the diff) is the only color-bearing surface in either file:

```css
/* Dark — illustrative mechanics */
html[data-theme="dark"] .sd-shell {
  background: linear-gradient(180deg,
    color-mix(in srgb,var(--panel) 92%,var(--info) 8%),
    var(--panel));
  border-color: color-mix(in srgb,var(--line) 72%,var(--info) 28%);
}

/* Light — illustrative mechanics */
html[data-theme="light"] .sd-shell {
  background: #fff;
  border-color: color-mix(in srgb,var(--line) 82%,#8792a8 18%);
  box-shadow: 0 10px 28px rgba(35,48,78,.08);
}
html[data-theme="light"] .sd-card {
  background: color-mix(in srgb,#fff 96%,var(--panel2) 4%);
  border-color: color-mix(in srgb,var(--line) 88%,#a5afc1 12%);
}
```

Every literal in that block is wrapped by an `html[data-theme="…"]` selector and uses `color-mix()` against the canonical token set (`--panel`, `--info`, `--line`, `--panel2`); the only bare literals are `#fff` (allowed: the spec's "research sheet; cool canvas; white material" requires the literal white), `#8792a8`, `#a5afc1` (border mix partners, not surface colors), and `rgba(35,48,78,.08)` (the shadow color for the hairline-disciplined light card). The plan is explicit on the authority of these values: *"These are illustrative mechanics; the implementation designer owns final values within canonical tokens."* That sentence is load-bearing — without it the plan would be in tension with `scripts/check_design_system.py` (which reads `templates/` not `docs/superpowers/`, so it does not gate here, but the principle binds the implementation phase). The light tokens-vs.-literal pattern is internally consistent with `docs/DESIGN_DOCTRINE.md` (light = "white material, hairline discipline, shadow instead of glow"; the literal `#fff` is the white material).

The PR introduces **zero** JS payload, **zero** template change, **zero** CSS rule in committed code, **zero** data write, **zero** workflow file. The CSS block above is prose inside a markdown doc, not committed CSS — it cannot run, render, or fail any CSS check at this PR's head. The CI guards (`check_design_system.py`, `check_runtime_style_injection.py`, `check_template_site_sync.py`) are all template-/site-/runtime-scoped and structurally inapplicable to `docs/superpowers/`.

## Plain-language findings

### 1.1 Pass — the architecture's plain-language stance is the "what is happening inside Technology?" exemplar, not a forbidden token surface

The spec's "First viewport" copy block (lines 3080–3110 of the diff) names the dossier's glance-tier answer as the plain-language question rather than only "how is XLK trading?". The copy hierarchy is *state → what changed → principal driver → participation/concentration → strongest child group + largest drag → current posture + freshness* — exactly the design-doctrine §Glance-tier order. The plan's headline word budget (≤ 34 EN words / ≤ 44 ZH chars) and posture/conflict budgets (≤ 18 EN words) are concrete, named, and match the doctrine's "ban internal state names, raw slugs, untranslated stats" rule. The five exemplar strings (EN + ZH table above) read as plain language: a non-operator can answer "what does this page say?" from them. No banned-glance vocabulary appears in any exemplar (`proves`, `proven`, `validated`, `guaranteed`, `certified` — see §3.1). No raw slugs, no internal-state names, no study identifiers leak into the user-visible strings. **Pass.**

### 1.2 Pass — the typed-disagreement vocabulary is the load-bearing plain-language move

The eight conflict classes (`ALIGNED`, `TIMEFRAME_SPLIT`, `SCOPE_SPLIT`, `FRESHNESS_SPLIT`, `COVERAGE_SPLIT`, `AUTHORITY_SPLIT`, `GENUINE_CONTRADICTION`, `UNAVAILABLE`) are the plan's named replacement for one fused "is X over/under Y" claim. They are: (a) explicit about WHAT disagrees, (b) typed so two reads are never collapsed, (c) all-caps to surface in glance tier without jargon, (d) `UNAVAILABLE` is first-class (typed-null behavior the design-doctrine requires). This is the design-doctrine "banned vocab: internal state/study names, untranslated stats, raw slugs" rule applied constructively — the architecture refuses to invent a magic score and instead names the disagreement shape. **Pass.**

### 1.3 Pass — the page-role and depth-section lists keep prose discipline

The "First viewport" list (seven items) and "Depth sections" list (seven numbered items: Internal leadership tree, Breadth and structure, Connected themes/subthemes, Macro transmission context, Execution context, Conflicts and watch conditions, Evidence and outcomes) are parallel in shape, plain-language, and avoid internal jargon in the user-visible labels. The "subsector overview" descriptor copy ("current entry context; parent-relative leadership; acceleration and persistence; participation, dispersion and concentration; reliability and source coverage; parent-sector agreement/conflict; material change since the last observation; direct links to group and connected-theme dossiers") is plain-language and matches the "so what do I do" design-doctrine rule. The architecture's `SPDR sector base rates are never presented as subsector proof. Current-membership synthetic history remains explicitly non-PIT where applicable.` is a load-bearing plain-language disclaimer (it forbids presenting proxy base rates as if they were sector truth). **Pass.**

### 1.4 Observation (non-blocking) — the §Glance-tier word budget "where natural" hedge

The headline budget reads "≤ 34 English words / ≤ 44 Chinese characters **where natural**". The hedge "where natural" is a real softener: it permits the implementation designer to exceed the budget when the language requires it. This is intentional — the design-doctrine's word budgets are non-binding; a designer may exceed them when the alternative is worse copy — and it matches the standing convention used elsewhere in the repo (e.g. `docs/DESIGN_DOCTRINE.md` §Glance tier "under hard word budgets" phrasing). **Not blocking** — flagged so a future audit pass on a STSI-1 implementation PR does not mistake the budget hedge for an unenforceable target.

### 1.5 Observation (non-blocking) — the architecture's named-dimension list is dense; an "answer in one breath" reviewer may push back

The spec names seven "first-class" dimensions in one paragraph (participation, concentration, persistence, material change, evidence sufficiency, parent-relative decomposition, plus the typed-disagreement vocabulary). A reviewer who believes the user should be able to answer the page in one breath might push back on density; the spec's argument is that "named dimensions" beat "fused score" precisely because fused scores collapse the disagreement the typed vocabulary names. The disagreement is intentional and matches the design-doctrine "banned vocab: fused scores". **Not blocking** — flagged so a future STSI-1 implementation audit pass can re-read the named-dimension contract against the actual rendered page, not against this plan.

## Theme findings

### 2.1 Pass — the plan's TP-0 evidence matrix is named, complete, and frozen as a prerequisite

The plan's Task 5 Step 1 (#5 of the numbered list) is explicit: "Capture the current `sectors/XLK.html` baseline in dark/light × EN/ZH × 1440/390." The matrix itself (lines 2353–2368 of the diff) is a complete 8-row grid (dark × {EN, ZH} × {1440, 390} + light × {EN, ZH} × {1440, 390}). Each row is labelled "real current dossier" — every screenshot is required to come from real current source data, not hand-authored fixtures. The degraded-states addendum (dossier 404/unavailable; dossier stale/degraded; optional leadership unavailable; optional entry context unavailable; required-source hash mismatch is rejected before publication) names five controlled-fixture variants and explicitly requires every receipt JSON to be labelled `real_current_source` or `controlled_degraded_fixture`. **Pass** — the evidence matrix is what TP-0 demands ("Evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390)") and the controlled-degraded addendum is exactly the "theme-specific degraded states" clause TP-0 requires.

### 2.2 Pass — the dark/light art directions are named as TWO treatments, not one skin

TP-0 demands "dark and light are TWO art directions, not one skin" — and the plan's Task 5 Step 1 (lines 1934–1936 of the diff) names both:

> **Dark:** command-center instrument panel; restrained depth; no glowing dashboard clutter.
> **Light:** research sheet; cool canvas; white material cards; hairline boundaries; shadow rather than glow.

Both treatments are explicit, both name material + geometry + signature, neither is "token-swap the dark and call it light". The light treatment explicitly bans the failure mode ("**Light art direction:** functional token swapping is not acceptance.", line 2731). **Pass** — this is the TP-0 dark/light requirement satisfied at the plan level. The reviewer's `PASS` for the implementation will require both themes judged as designs, hierarchy + material depth + semantic color + responsive composition + EN/ZH parity, against the produced screenshots — that judgement is not in scope for this plan-only PR.

### 2.3 Pass — the plan enforces "no third header, no parallel token system"

Task 5 Step 1 (#6) reads "Keep the existing global navigation family and `theme.css`; no third header or parallel token system." This is the standing macro navigation law (`templates/_site_nav.html.j2` + `theme.css`; `templates/_public_nav.html.j2` for anonymous/corporate; never a third header; `nav_prefix` may vary only by directory depth). The plan inherits that law and forbids both a third header AND a parallel token system, which is the right anti-pattern pair (third header breaks the navigation family, parallel token system breaks `theme.css`). The plan also forbids substantive product styling as a runtime stylesheet inside JS — Task 5's "JS renders only; all classification, freshness, relationships and authority are producer-owned" (re-par body of the PR) + the explicit test `assert "style.textContent" not in JS.read_text()` at line 1979 of the diff enforce that rule at the test layer. **Pass** — `check_runtime_style_injection.py` will gate the implementation phase automatically; this plan cannot drift into a JS-injected stylesheet system because the test forbids `style.textContent` in the JS file.

### 2.4 Pass — the plan's CSS exemplar block stays inside the canonical token set

The illustrative CSS block (§Diff content above) uses `color-mix()` against the canonical tokens (`--panel`, `--info`, `--line`, `--panel2`), with three exceptions that the plan owns explicitly: `#fff` (the light surface, mandated by the "research sheet; cool canvas; white material" art direction), `#8792a8` and `#a5afc1` (border mix partners, not surface colors), and `rgba(35,48,78,.08)` (the light card's hairline-discipline shadow). The plan's "These are illustrative mechanics; the implementation designer owns final values within canonical tokens" line binds the final values to the canonical token family — the implementation designer may adjust the mix percentages but cannot substitute a parallel palette. **Pass** — the illustrative mechanics stay inside the canonical token set; the only literal-hex exceptions are mandated by the light art direction itself.

### 2.5 Observation (non-blocking) — the illustrative hex literals in the light CSS example are not yet tokens

`#8792a8`, `#a5afc1`, and `rgba(35,48,78,.08)` are illustrative literals in the plan's CSS example. If the implementation lands with the same hexes in `templates/sector.html.j2` page-scoped CSS, `check_design_system.py` will report them as literals outside the canonical token set (R1 of the design-system ratchet, governed by the page registry). The implementation designer's job is to either (a) extend `theme.css` to mint these as new tokens (`--shadow-light-hairline`, `--border-mix-warm`, `--border-mix-cool`), or (b) defend them as page-scoped literals that match the light art direction. Either resolution is consistent with the plan's "implementation designer owns final values within canonical tokens" line. **Not blocking** — flagged so the implementation audit pass does not flag the literals without reading the designer's resolution.

### 2.6 N/A — no theme-art-direction assertion is made or implied in this PR

The PR is a plan + spec. No CSS file is changed. No JS file is changed. No template is changed. No page is rendered. The CSS example in the plan is prose inside a markdown doc, not committed CSS; the example explicitly defers final values to the implementation designer. The TP-0 dark/light × EN/ZH × 1440/390 matrix is named as the implementation's evidence requirement, not as this PR's evidence. The PR body closes with the explicit disclaimer: "Capability state: `SPEC_AND_PLAN_COMPLETE / REVIEW_HELD`. Parent product mission remains incomplete." No theme assertion exists to fail; the theme evaluation is structural (does the plan name TP-0's requirements?) and the answer is yes on every row.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` does not enumerate `docs/superpowers/`, so the gate is structurally out-of-scope

`scripts/check_validated_claims.py --list` reads the `data/regime/validated_claims_allowlist.json` allow list plus every `templates/*.j2` file; both paths miss `docs/superpowers/` entirely. Verified manually: `python3 scripts/check_validated_claims.py` enumerates hundreds of template entries; none of `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md` or `docs/superpowers/plans/2026-09-21-stsi1-sector-federation-technology-dossier.md` appear. **Pass** — the gate does not see the PR's files.

### 3.2 Pass — no use of the word `validated` or any promotion-bearing synonym in either PR-added file

`grep -inE "validated|guaranteed|certified|proved"` against the two PR-added files returns ZERO matches in any promotion-bearing sense. The word `proves`/`proved` does NOT appear; the agentos governance vocabulary used here is `PROVEN_LIVE` / `BUILT_NOT_PROVEN` / `PARTIAL` / `CAPABLE_PROMOTED` (line 2792 etc. of the diff) — these are the **standing agentos capability-state labels**, not user-facing validated authority claims. Each row in the plan's carriers table is paired with a concrete dependency cite (#7211, #7526, #7455, #7508, #7252, #7283) and an exact capability label, so the labels are descriptive state-of-the-world markers, not authority claims. `certified` / `guaranteed` / `compliant` — zero matches. **Pass.**

### 3.3 Pass — the spec body closes with an explicit production-promotion disclaimer

Spec closing paragraph (line 2757 of the diff): "This document creates no implementation, deployment, prediction, ranking, gating, sizing, portfolio, or trading authority." The eight forbidden activities map exactly to the standing `LLM may only de-escalate calibrated keys — never originate signals, scores, or escalations.` rule (operator 2026-08-09, calibrated to PR #3821). The PR body mirrors: "This PR does **not** duplicate or edit active implementation carriers" + "**No product source, generated site, runtime, workflow, data, authority or deployment path changed.**" The plan's release condition clause: "Only after STSI-1's written plan is approved should source implementation begin." Three independent disclaimers, all consistent, all closing. **Pass** — the PR explicitly disclaims every promotion-bearing outcome.

### 3.4 Pass — the conflict-class vocabulary is the lawful alternative to a "validated" fused score

The eight conflict classes (§1.2) are the plan's named replacement for "we proved sector X is strong / weak". Instead of a fused score, the architecture names disagreement shape: `ALIGNED` (everything agrees), `TIMEFRAME_SPLIT` (different windows disagree), `SCOPE_SPLIT` (different slices disagree), `FRESHNESS_SPLIT` (different ages disagree), `COVERAGE_SPLIT` (different completeness disagree), `AUTHORITY_SPLIT` (different sources disagree), `GENUINE_CONTRADICTION` (sources genuinely disagree on the same window/scope/freshness/coverage/authority), `UNAVAILABLE` (no evidence). This is the standing `preserves named dimensions instead of creating a fused magic score` ruling applied as policy, and it is the lawful antithesis of an unbacked `validated` claim. **Pass** — the architecture's central design choice is to refuse a fused score, which is the validated-claims discipline expressed structurally rather than lexically.

### 3.5 Pass — the EN/ZH exemplar strings are typed-null and typed-disagreement, not authority-bearing

The five EN/ZH exemplar strings (§Diff content) all use the typed-null vocabulary: `Loading governed read…` / `正在加载治理研判…` (explicit pending state), `Detailed read unavailable` / `详细研判暂不可用` (explicit typed-null). None of them claim a validated rank, score, signal, gate, size, escalation, trade or portfolio action. None of them name a specific stock, sector return, or timing call. None of them use the word `validated` or any promotion-bearing synonym. The plan's test at line 1987 of the diff is the load-bearing guarantee: `for forbidden in ("rank_security", "select_security", "size_position", "execute_trade"): assert forbidden not in combined` — every page-level artifact is forbidden from carrying those four tokens, period. **Pass** — the EN/ZH exemplars are typed-null, and the test forbids the four authority-bearing tokens at the implementation layer.

### 3.6 Pass — no `promotion: PROMOTED`, no `authority_changed: true`, no signal / rank / score / threshold / context-gate / policy / ledger change

The PR body is explicit: "No product source, generated site, runtime, workflow, data, authority or deployment path changed." The diff is two markdown files; the diff does not modify any of: a signal model, a rank, a score, a threshold, a context-gate rule, a policy, a ledger, a capability sidecar, a rights registry, a freshness contract, or a launch/land/escalation path. The plan's "Hard dependency heads remain #7211 `9b01c9bcae2b12f23ab0a2ab3a5054f81dcade02` and #7526 `cdad0d3ec3f09f53425906ed2b532fed4507ed12`, both open/unmerged at plan freeze" line is the load-bearing guarantee: implementation cannot begin until those carriers merge, so this PR carries zero implementation authority regardless of whether the plan reads well. **Pass** — promotion-bearing surface is zero, by construction.

## Overall verdict

**VERDICT: PASS — clean half-B architecture + plan freeze, merge is correct.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | The spec/plan prose is plain-language throughout: the "what is happening inside Technology?" exemplar, the seven first-viewport items, the seven depth-section items, the five EN/ZH exemplar strings (all typed-null or plain-prose, zero jargon), the typed-disagreement vocabulary, the explicit word budgets. Banned-glance vocabulary scan is clean. Bilingual pair is named in concrete strings with word budgets. No raw slugs, no internal-state names, no study identifiers leak into user-visible copy. |
| theme | PASS | The plan names the TP-0 dark/light × EN/ZH × 1440/390 evidence matrix as a hard prerequisite; the dark and light art directions are two distinct treatments (command center vs. research sheet), explicitly forbidding token-swapped skin; the existing global navigation family and `theme.css` are preserved; a parallel token system is forbidden; a runtime-injected stylesheet system is forbidden by test (`style.textContent` not in JS). The CSS exemplar block uses `color-mix()` against the canonical token set; the three illustrative hex literals (`#fff`, `#8792a8`, `#a5afc1`) plus one `rgba()` shadow are owned by the light art direction and explicitly deferred to the implementation designer. The controlled-degraded-fixture matrix (5 variants) is named. `check_design_system.py` and `check_runtime_style_injection.py` are structurally out-of-scope for this docs-only PR; both will gate the implementation phase. |
| validated-claims | PASS | `check_validated_claims.py --list` does not enumerate `docs/superpowers/`. The word `validated` and promotion-bearing synonyms (`guaranteed`, `certified`, `proves`, `proved`, `compliant`) appear zero times in either PR-added file. The agentos governance vocabulary (`PROVEN_LIVE` / `BUILT_NOT_PROVEN` / `PARTIAL`) is the standing capability-state labels, paired with concrete dependency cites — not user-facing validated authority claims. The spec body, PR body, and plan release-condition clause each close with an explicit production-promotion disclaimer. The eight conflict classes are the lawful alternative to a fused validated score. The EN/ZH exemplar strings are typed-null. The implementation is forbidden by test from containing `rank_security` / `select_security` / `size_position` / `execute_trade`. Promotion-bearing surface is zero, by construction. |
| merge hygiene | PASS | DRAFT / HOLD state preserved in body; release condition named (Chairman approval + #7211/#7526-or-successor merged + fresh worktree from `origin/main`). Capability state `SPEC_AND_PLAN_COMPLETE / REVIEW_HELD`. Plan compatibility census: 0 introduced contract deltas, only inherited pre-existing test (`tests/test_render_dead_ref_targets.py`) carried. `git diff --cached --check`: PASS. No TBD/TODO/duplicate headings/unbalanced fenced blocks per body's verification list. No duplication of active lanes (named carriers preserved verbatim). No second publisher, no second ledger, no second authority surface. |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The illustrative hex literals in the plan's CSS example block (`#8792a8`, `#a5afc1`, `rgba(35,48,78,.08)`) are owned by the light art direction but are not canonical tokens at the time of the plan's authoring. The implementation PR's design packet should either extend `theme.css` to mint `--shadow-light-hairline` / `--border-mix-warm` / `--border-mix-cool` (or the implementation designer's chosen names) or defend the literals as page-scoped, art-direction-mandated. The plan defers this choice correctly; the implementation must resolve it before its `templates/` change gates green.
2. The headline word budget hedge ("≤ 34 EN words / ≤ 44 ZH characters **where natural**") is intentional soft language; the implementation's glance-tier copy should be reviewed against both the budget AND a plain-language readability check. If the implementation exceeds the budget for a real reason, that reason should be in the implementation PR's body.
3. The "no third header, no parallel token system" rule is correctly stated in Task 5 Step 1. The implementation should also avoid minting a new global CSS file (e.g. `sector.css`); the plan's CSS example is page-scoped (`.sd-shell`, `.sd-card`), which is the correct scoping. Implementation review should verify the scoped-CSS pattern is preserved.
4. The `style.textContent` test at line 1979 of the diff is the load-bearing JS-renders-only gate; the implementation reviewer should confirm this test exists in the implementation's `tests/test_sector_dossier_page.py` and that the implementation's `templates/sector_dossier.js` does not introduce any new `style.textContent =` or `style.cssText =` or `element.style.<prop> =` lines that violate the spirit of the rule (token-substitution aside).
5. The PR is DRAFT / HOLD with explicit release condition. The next merge step requires Chairman approval of both the architecture and the plan; no fresh `claude/sol-001/*` branch may continue implementing on top of this branch.

**No blocking issue found. No retry. No scope expansion. Audit complete.**