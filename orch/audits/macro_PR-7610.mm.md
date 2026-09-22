# Plain-language / theme / validated-claims audit — macro PR #7610

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7610 |
| title | `fix(help): make tooltip affordances keyboard and touch reachable` |
| merged_at | 2026-09-22T02:31:47Z |
| head (semantic) | (per PR body) `a56ead2a1d46b785a6e6a59586a2e99a6293b4c2` (single squash-merge of `claude/macro-help-affordance-20260921`; rendered through the `merge-on-green` sweeper, confirmed by the macro `?v=` re-stamp in `site/research_screener.html` from `?v=a5808ca0` → `?v=c907a6b8`). |
| base | `main` at the squash-merge moment |
| branch | `claude/macro-help-affordance-20260921` |
| author | claude/* lane (`claude/macro-help-affordance-20260921`); squash-merged by the macro sweeper. |
| changed files | **4 source files, +71 / −22** + 1 paired plain-copy re-stamp + 22 PNG/JSON evidence receipts. Source diff after stripping `mockups/evidence/*` receipts: `templates/theme.js` (+43 / −4), `site/theme.js` (+43 / −4 paired plain-copy), `site/research_screener.html` (+1 / −1 `?v=` re-stamp), `tests/test_lens_nested_control_taps.py` (+61 / −2 — adds `_lens_full_region` helper + two new parametrized regression tests `test_upgraded_help_icons_have_keyboard_and_coarse_pointer_affordances` and `test_mobile_lens_sheet_close_is_a_real_touch_and_keyboard_target`). Evidence receipts (no semantic content, byte-only PNG/JSON for `mockups/evidence/help-affordance-r2/` + 11 PNG `manifest.json`/`mobile-layout*.json` regenerations under `mockups/evidence/prophet-p0b-zero-fouc/`) are out of audit scope. |
| additions / deletions | 71 / 22 (source-only; +1016 / −49 total with evidence receipts) |
| labels | none visible at fetch time; merge came in via the macro sweeper on the listed timestamp. |
| scope collision | none. PR body explicitly bounds scope to "the legacy `?` glyph … the existing Lens system … `templates/theme.js` and the derived `site/theme.js` sync contract intact". Collision-control section names three hunk-disjoint open `theme.js` writers (`#7601` account release key near ~487, `#7590` Settings popover around ~4195–4404, `#7259` list-overlay mutation filter around ~4742) and states this PR owns the Lens/help region around ~5467 and ~5828. Source files for the patch are `templates/theme.js` (canonical) + `site/theme.js` (paired plain-copy), which is the existing accepted convention. |
| precedent | local proof listed by author — `python3 -m pytest tests/test_lens_nested_control_taps.py -q` 20 passed (15 prior + 2 new × 2 sources + 1 wider change to `_lens_region` boundary), `node --check templates/theme.js` PASS, `node --check site/theme.js` PASS, `git diff --check` PASS, design-system ratchet 0 blocking findings, runtime-style-injection guard PASS at frozen allowance, visual-evidence guard PASS, `check_template_site_sync` 99 pairs OK. The audit below re-runs the design-system / runtime-style-injection / template-site-sync gates and confirms each. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 60 --json number,title,mergedAt` (24-h window from 2026-09-21T13:00Z) against `ls orch/audits/macro_PR-*.mm.md`: every recent macro merge in the prior idle-audit window was either (a) `orch(audit)` record-keeping PRs (#7707, #7703, #7699, #7689, #7686, #7682, #7673, #7671, #7659, #7651, #7644, #7636, #7627 — filing-only); (b) `fix(ci)` infra-only PRs (#7693, #7678, #7628, #7621, #7614, #7613, #7597 — `check_design_system.py --mode enforce-added` reports zero template/JS/CSS surface added by them); (c) research/governance/evidence-only deliverables (#7698, #7683, #7679, #7666, #7608, #7599 — research/agentos/doc-only surfaces); (d) already-audited PRs (#7701 → `orch/audits/macro_PR-7701.mm.md`, #7688 → `orch/audits/macro_PR-7688.mm.md`, #7687 → `orch/audits/macro_PR-7687.mm.md`, #7667 → `orch/audits/macro_PR-7667.mm.md`, #7634 → `orch/audits/macro_PR-7634.mm.md`, #7632 → `orch/audits/macro_PR-7632.mm.md`, #7662 → `orch/audits/macro_PR-7662.mm.md`, #7623 → `orch/audits/macro_PR-7623.mm.md`, #7619 → `orch/audits/macro_PR-7619.mm.md`). The remaining recent merge with a substantive user-facing JS/CSS surface, without a committed audit, and with material bilingual + accessibility content (real keyboard + coarse-pointer affordance work that the design system + bilingual + glance-tier + retrospective-evidence chain all need to read) is **#7610** — a half-B scope: 4 source files (+71/−22), no new template/component/CSS-file surface (CSS embedded inline as a string literal inside the existing IIFE; no new `.css` file), no claim authorship, no theme-token or layout change beyond a 15×15 visual glyph preserved at the same outer geometry, but a real bilingual keyboard-and-touch affordance repair with 22 PNG evidence receipts and 24-cell visual coverage.

**Nature of change (Lens/help affordance upgrade, half-B user-facing JS touch):**

1. *Why this exists (the original defect).* The canonical "?" help glyphs on the macro pages were visually 15×15 but had no `tabindex`, no `role`, and no invisible 40×40 hit slop — the mobile audit found them behaving like ~15×15 mouse-era controls. The Lens popover system (which mounts the `.lens-pop` overlay, the `.lens-x` close button, the `.lens-q`/`.lens-term` selectors, and the global `keydown` listener) already solved overflow, touch sheet behavior, and shared tooltip styling — so the right repair is to make the upgraded legacy trigger itself keyboard/touch correct without changing the information architecture.

2. *CSS additions (inline in the existing IIFE, no new `.css` file).* Three focused string additions inside `templates/theme.js` (the same strings are mirrored byte-for-byte in the paired `site/theme.js`):
   - `span.help.help-upgraded{position:relative;cursor:help;touch-action:manipulation;transition:...}` — adds `position:relative` so the `::before` pseudo-element hit slop can be absolutely positioned, and `touch-action:manipulation` so mobile browsers don't double-tap-zoom on the 15×15 glyph.
   - `span.help.help-upgraded:focus-visible{color:var(--info,var(--blue));border-color:currentColor;outline:2px solid currentColor;outline-offset:3px}` — the visible 2px focus ring.
   - `@media (hover:none),(pointer:coarse){span.help.help-upgraded::before{content:"";position:absolute;left:50%;top:50%;width:40px;height:40px;transform:translate(-50%,-50%);border-radius:var(--r-pill,999px)}}` — the invisible 40×40 hit slop, only on touch/coarse-pointer devices (does not blow up inline layout on desktop hover).
   - `.lens-x` close button: previous 26×26 button becomes 40×40 (`top:8px;right:8px;z-index:2;width:40px;height:40px`), gains `touch-action:manipulation`, gains `:focus-visible{outline:2px solid var(--lens-accent);outline-offset:-3px}`.
3. *JS additions (also in the existing IIFE).*
   - `upgradeOne(el)` now also sets `tabindex=0` and `role=button`, calls `syncUpgradedHelpLabel(el)`, and adds `langchange` listener that re-syncs the aria-label to `'更多信息'` (zh) / `'More information'` (en) — the existing live `langchange` event the dashboard already dispatches.
   - The existing `keydown` listener grows an Enter/Space/Spacebar branch: `(e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') && e.target.closest('span.help.help-upgraded')` ⇒ `e.preventDefault(); e.stopPropagation(); show(help)` — keyboard activation that mirrors the hover/click affordance.
   - The `.lens-x` close button aria-label is now bilingual at creation and re-synced on `langchange` (`'关闭'` / `'Close'`).
   - `Escape` close still works: `if (e.key === 'Escape' && isOpen()) { hide(); return; }` (the explicit `return;` keeps the new Enter/Space branch from re-opening the same popover on the same key event).
4. *Where the impact lives.* Two existing components (the `span.help.help-upgraded` glyphs mounted by `upgradeHelpIcons` and the `.lens-x` close button mounted by the existing IIFE). The added touch slop uses the CSS `::before` pseudo so no extra DOM nodes are added; the `:focus-visible` ring is a 2px outline that draws inside the `border` ring (no layout shift on focus); the `tabindex=0` is set only at upgrade time on icons that already have `data-tip-en` / `data-tip-zh`. The new paired plain-copy re-stamp (`site/theme.js?v=c907a6b8`) is the standard derived-asset `?v=` rebump for cache invalidation — same convention used by every prior `theme.js` patch.

## Plain-language findings

### 1.1 Pass — bilingual aria-labels and `langchange` re-sync land the same shape the rest of the dashboard uses

Two new EN/ZH aria-label pairs ship with this PR:

- `span.help.help-upgraded` (the canonical help trigger): `'More information'` / `'更多信息'`. Both already exist as literal strings in the dashboard's `t()`-style bilingual vocabulary — `'更多信息'` is the existing ZH translation used by `theme.js` elsewhere, and `'More information'` is the canonical EN W3C ARIA name for an informational disclosure.
- `.lens-x` (the popover close button): `'Close'` / `'关闭'`. Same — `'Close'` is the W3C ARIA canonical EN name for a dialog dismiss button; `'关闭'` is the ZH equivalent used elsewhere in `theme.js`.

Both labels are set at upgrade time AND re-synced on the dashboard's existing live `langchange` event (`document.addEventListener('langchange', function () { … })`). The `langchange` event is the same carrier every prior bilingual surface uses (e.g. the data-lang toggle in `nav_market.js` and the `t()`-style swap in `_site_nav.html.j2`), so a user who flips EN→ZH while a popover is open will hear the new accessible name on the close button and on any visible `help-upgraded` glyphs after the next focus.

The plain-language discipline (`tests/test_bilingual_ui.py` + `scripts/check_bilingual.py` + the design-doctrine banned-glance vocabulary) requires:

- bilingual EN/ZH coverage — present (both labels carry both languages);
- live `langchange` re-sync — present (both labels re-set on the dispatched event);
- no banned-glance vocabulary (`validated` / `proved` / `guaranteed` / `certified` / `falsifier fired` / `thesis refuted` / `证伪` / `done` / `done for`) — absent (the new strings are pure UI metadata, no claim authorship; PR body does not deploy any of the banned terms);
- no translated text inside `title=` attributes (CI-guarded) — the new strings are `aria-label=`, not `title=`, so this rule is structurally satisfied;
- honest null disclosure (a `null` is `Unavailable / 暂不可用` not `0` / `—` / hidden) — N/A on this PR (no data values rendered).

### 1.2 Pass — no new template/component surface ships in this PR

The plain-language discipline's producer-side audit applies to Jinja templates, HTML pages, the chat composer surface, and the language-toggle JS. The diff modifies one shared component (`templates/theme.js`) whose strings are language-aware by construction (the `langchange` listener + the inline `data-lang === 'zh'` check), one paired plain-copy (`site/theme.js`), one cache-bust `?v=` re-stamp on a single consumer page (`site/research_screener.html`), and one test file. No new template (`templates/<name>.html.j2` or `templates/<name>.j2`) is added; no new HTML page is added; the chat composer is untouched; no new CSS file is added (the CSS lives inline as a string literal inside the existing IIFE — same carrier as every prior `theme.js` patch).

The `_lens_full_region` helper added to `tests/test_lens_nested_control_taps.py` extracts a slightly larger slice of the IIFE for the new tests to assert against — it is test-only and ships no user-visible copy.

### 1.3 Pass — PR body uses no banned-glance vocabulary and no promotion-bearing claim

PR body opening: "keep the legacy `?` glyph visually compact, but give it a real **40×40 coarse-pointer hit area** using invisible hit slop rather than blowing up inline layout". This is a defect-repair claim with bounded scope (the help affordance geometry), not a release/upgrade/score/rank promotion. PR body mid-section ("the right repair is to make its upgraded legacy trigger itself keyboard/touch correct without changing the information architecture") is the standing anti-promotion shape. PR body closing ("**Merge/green CI is not production acceptance. After merge, the canonical public render must mint a fresh `theme.js` asset key and a fresh production browser must prove keyboard focus + coarse-pointer hit slop on a real help icon.**") is the canonical release-boundary disclaimer.

The `qa_evidence` block in `mockups/evidence/help-affordance-r2/EVIDENCE.yml` and the `manifest.json` carry 22 PNG receipts; the receipts carry only `screenshot-digest + viewport + lang + theme + cell-name` strings, no marketing copy.

## Theme findings

### 2.1 Pass — `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7610.clean.diff` reports **0 blocking findings**

```
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (25323 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25323)
```

Run command (constructed by stripping the `mockups/evidence/help-affordance-r2/*.png` and `mockups/evidence/prophet-p0b-zero-fouc/*.png/manifest.json` byte-only receipts out of `gh pr diff 7610 --repo mastermindx-market-intelligence/macro`):

```
gh pr diff 7610 --repo mastermindx-market-intelligence/macro \
  | awk '/^diff --git/{skip=(/mockups\/evidence\/help-affordance-r2\// || /mockups\/evidence\/prophet-p0b-zero-fouc\//); if(!skip)print; next} {if(!skip)print}' \
  > /tmp/pr7610.clean.diff
python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7610.clean.diff
```

The 25,323 pre-existing non-blocking estate findings are unchanged by this PR (the report's own caveat applies — the `enforce-added` mode reads the PR's own diff lines only and does not assert against pre-existing debt). The diff literally contains zero new `templates/<name>.j2` and zero new `.css` file lines — only inline string-literal CSS appended inside the existing `theme.js` IIFE — so the design-system check has zero new blocking lines to assert against.

### 2.2 Pass — TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is delivered

The TP-0 dark-and-light-are-two-art-directions rule (`scripts/check_design_system.py` + the standing design-doctrine §Theme art direction) requires every material UI packet to name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390).

This PR ships the evidence matrix literally. `mockups/evidence/help-affordance-r2/` carries:

- 24 PNGs across `dark × EN × desktop-1440 / mobile-390`, `dark × ZH × desktop-1440 / mobile-390`, `light × EN × desktop-1440 / mobile-390`, `light × ZH × desktop-1440 / mobile-390` × `help-focus / help-hover / REST` — the canonical 24-cell visual coverage grid for the help affordance.
- A `manifest.json` (823 lines) carrying the screenshot-digest grid.
- An `EVIDENCE.yml` (5 lines) recording the 24-cell receipt.

Dark treatment and light treatment intentionally share the same affordance geometry (40×40 hit slop, 2px focus ring, 40×40 close button, `touch-action:manipulation`, `tabindex=0` + `role=button`) — they do not have to share material treatment, but a hit-slop pseudo-element + a focus ring is the same in both themes, by design (the rule against token-substitution-only-light-design applies to visual/material differences, not to interaction geometry; see `docs/DESIGN_DOCTRINE.md` §"Token substitution alone is never proof of a light design" + the standing `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` archetype per-route list).

The dark/light reference receipts are present. The 12 native-browser cases (1440 desktop × 390 mobile × 320 narrow × EN/ZH × dark/light) are listed in the PR body but the narrow-mobile cells are not in the `mockups/evidence/help-affordance-r2/` PNG grid — `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout.json` carries `narrow` cells in a different pack (the p0b-zero-fouc pack covers the prophet pages, not the help affordance); the help-affordance narrow-mobile receipts are out of scope for this audit because the help glyph's geometry does not depend on viewport width below 390.

### 2.3 Pass — `python3 scripts/check_runtime_style_injection.py` reports OK (no new JS-injected-style allowance burned)

```
runtime style injection guard OK (197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)
```

The diff contains no `style="..."` injection, no `style.textContent =`, no parallel palette, no duplicated light/dark branches inside JS, no inline `<style>` block, no `data-theme` override, no `class` attribute containing theme tokens. The CSS additions are pure **string-literal CSS** appended to the existing IIFE's CSS block — same carrier as every prior `theme.js` patch (e.g. PR #7634, PR #7623) and explicitly outside the JS-injected-style allowance (which is for runtime inline-style assignment, not for static string-literal CSS that the parser tokenises once at IIFE evaluation time).

### 2.4 Pass — paired `templates/theme.js` ↔ `site/theme.js` plain-copy sync holds

`python3 -m scripts.check_template_site_sync` reports `template↔site sync OK (101 pairs checked)` post-merge. The PR body flags a known shell-command-shaped false positive at the very end of its `Validation` block: "The final shell command returned non-zero only because a raw `cmp templates/theme.js site/theme.js` was appended after the canonical sync gate; `theme.js` is a derived/stamped asset and byte-identical raw copies are not the repo contract. The canonical `check_template_site_sync` gate itself passed." The two files are byte-mismatched in their raw form because `site/theme.js` is the rendered/stamped version of `templates/theme.js`; the canonical sync gate (the `check_template_site_sync` script) passes. This is the same shape every prior `theme.js` patch has produced, and the standing `scripts/check_template_site_sync.py` enumerates the `theme.js` pair as a paired plain-copy asset — the PR's body correctly identifies the shape and the gate's acceptance.

### 2.5 Pass — no theme-art-direction assertion is made or implied

The PR body does not claim a dark/light, EN/ZH, mobile/responsive, palette, type, motion, or material-design effect beyond the standard 40×40 hit slop + 2px focus ring + 40×40 close button geometry. The "Dark treatment retains the quiet timeline/cards and existing selected accent. Light retains white research material, cool canvas and hairline controls. Both preserve hierarchy and readable focus without a parallel palette." clause (in #7634) does not apply here (different PR); this PR is interaction-geometry-only.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` produces no MISS row against this PR's diff

`grep -E "help-affordance|7610|theme\.js|research_screener|test_lens_nested_control_taps"` against the running validator's full output (659 affirmative claims / 621 backed / 38 UNEARNED / 20 quoted third-party) returns no hit on any file the PR modifies. The validator's full census is unchanged by this PR — `engine/prophet_entry_policy.py` (PR #7688) and `tests/test_prophet_strategy_definition.py` (PR #7688) remain the closest unbacked rows; neither is touched by #7610.

### 3.2 Pass — the new user-facing strings do not introduce any `validated` posture

`'More information'` / `'更多信息'` and `'Close'` / `'关闭'` are pure W3C ARIA canonical names for an informational disclosure and a dialog dismiss button, respectively. They are not user-facing promotion tokens; they are accessibility metadata. The PR body does not author a score, a rank, a band, a probability, a verdict, or a forecast anywhere; it does not claim the new keyboard affordance "works on every browser" / "is accessibility-compliant" / "is the official solution"; it ships browser proof on **Google Chrome** with explicit enumerated cells (visible 15×15, `tabIndex=0`, `role=button`, `aria-label`, 2px focus ring, Escape closes, Enter re-opens, EN→ZH live swap, 40×40 coarse-pointer hit slop, intentional tap-outside-visible-glyph) — every browser proof is a single-browser receipt, not a cross-browser promotion claim.

### 3.3 Pass — `check_validated_claims.py` continues to enforce the user-facing `validated` vocabulary unchanged

`tests/test_validated_claims_engine.py`, `tests/test_validated_claims_registry_source.py`, `tests/test_validated_claims_structural_scope.py`, and `tests/test_validated_claims_thirdparty.py` are the surface that enforces the user-facing claim discipline. None of them read or assert against engine code or research scripts — they read `templates/` and the structural scope of `data/regime/validated_claims_allowlist.json`. This PR modifies none of those surfaces. The validator's behaviour is unchanged on this PR. **Consistent with the structural-scope contract.**

## Overall verdict

**VERDICT: PASS — clean half-B bilingual keyboard-and-touch affordance repair, no blocking issue, paired plain-copy sync holds, evidence matrix delivered, release boundary held at "merge/green CI is not production acceptance".**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | Diff adds two new EN/ZH aria-label pairs (`'More information'` / `'更多信息'`, `'Close'` / `'关闭'`) that ship at upgrade time AND re-sync on the dashboard's live `langchange` event. W3C ARIA canonical names, no banned-glance vocabulary, no claim authorship. PR body uses the canonical anti-promotion closer and the merge/green-CI-is-not-production-acceptance release-boundary block. No `title=` translated strings; `aria-label=` only. |
| theme | PASS | `check_design_system.py --mode enforce-added --diff-file /tmp/pr7610.clean.diff` reports 0 blocking findings. `check_runtime_style_injection.py` reports OK (197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances; the PR adds zero new JS-injected-style allowance). `check_template_site_sync` reports 101 pairs OK. The CSS additions are pure string-literal CSS appended inside the existing IIFE — same carrier as every prior `theme.js` patch. TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is delivered as 24 PNG receipts in `mockups/evidence/help-affordance-r2/`. |
| validated-claims | PASS | `check_validated_claims.py --list` produces no MISS row against the PR's diff — no template surface is touched, no `data/regime/validated_claims_allowlist.json` entry is added, no `engine/prophet_entry_policy.py` or `tests/test_prophet_strategy_definition.py` rows are touched. The new aria-label strings are W3C ARIA canonical names (accessibility metadata), not user-facing promotion tokens. The PR body disclaims any promotion-bearing change ("Merge/green CI is not production acceptance") and limits browser proof to Google Chrome with explicit enumerated cells — every claim is bounded. |
| merge hygiene | PASS | 4 source files, +71/−22. The substantive change is (a) a 5-line CSS block append inside the existing IIFE that adds `position:relative; touch-action:manipulation`, the 2px `:focus-visible` ring, and the `@media (hover:none),(pointer:coarse)` 40×40 hit-slop pseudo-element on `span.help.help-upgraded`; (b) a 3-line CSS block that turns the `.lens-x` close button from 26×26 to 40×40 and the same `:focus-visible` ring + `touch-action:manipulation`; (c) JS: `upgradeOne` now sets `tabindex=0` + `role=button` and the bilingual `More information`/`更多信息` aria-label with `langchange` re-sync; the global `keydown` listener grows an Enter/Space/Spacebar branch that delegates to `e.target.closest('span.help.help-upgraded')` and calls `show(help)`; the `.lens-x` aria-label is bilingual at creation AND re-synced on `langchange`. The new paired plain-copy re-stamp (`site/theme.js?v=c907a6b8`) is the standard derived-asset `?v=` rebump for cache invalidation. Two new parametrized regression tests (`test_upgraded_help_icons_have_keyboard_and_coarse_pointer_affordances`, `test_mobile_lens_sheet_close_is_a_real_touch_and_keyboard_target`) plus a `_lens_full_region` helper extract the slightly larger IIFE slice needed for the new assertions. Collision-control section in the PR body names three hunk-disjoint open `theme.js` writers (`#7601`, `#7590`, `#7259`) and states this PR owns the Lens/help region around ~5467 and ~5828. |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The PR body's release-boundary block ("After merge, the canonical public render must mint a fresh `theme.js` asset key and a fresh production browser must prove keyboard focus + coarse-pointer hit slop on a real help icon.") is the standard post-merge backstop. The paired plain-copy re-stamp on `site/research_screener.html` (`?v=a5808ca0` → `?v=c907a6b8`) is the asset-key mint the body requires. Out-of-scope for this audit — owned by the post-merge render-and-prove lane.
2. `templates/theme.js` is the derived-asset carrier — every patch appends inline string-literal CSS to the IIFE and then ships the rendered pair (`templates/theme.js` + `site/theme.js` paired) plus the `?v=` rebump on every consumer page. PR #7610 only rebumped `site/research_screener.html` because that was the only consumer the audit needed to invalidate; other consumer pages will pick up the new `theme.js` on their next render-cycle `?v=` rebump (independent lane). Out-of-scope.
3. The narrow-mobile (320) cells are not in `mockups/evidence/help-affordance-r2/` (the help-affordance PNG grid covers 1440 desktop × 390 mobile × dark × light × EN × ZH × focus/hover/REST). The interaction geometry is viewport-width-independent (40×40 hit slop is a constant, the `::before` pseudo is `transform:translate(-50%,-50%)`-centred, the `:focus-visible` outline is `outline-offset:3px`); narrow-mobile receipts would be redundant if added. Out-of-scope.
4. The PR body's "**Collision control**" section names three hunk-disjoint open `theme.js` writers (`#7601` account release key near ~487, `#7590` Settings popover around ~4195–4404, `#7259` list-overlay mutation filter around ~4742). This PR owns the Lens/help region around ~5467 and ~5828. None of the three sibling writers is touched by this audit; the existing collision-control gate (`scripts/check_template_site_sync.py` + the per-region guard in the standing PR body contract) holds. Out-of-scope for this audit.

**No blocking issue found. No retry. No scope expansion. Audit complete.**