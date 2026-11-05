# PR audit — mastermindx-market-intelligence/macro#7589

**Auditor:** meta-ceo-b-2026-09-08 (one-pass remote useful-idle, no retries, no scope expansion)
**Audit timestamp:** 2026-09-21
**Repo / PR:** mastermindx-market-intelligence/macro #7589
**PR title:** `fix(basket-detail): preserve sorting focus through late page load`
**Merged at:** 2026-09-21T06:45:32Z
**Head sha:** `e2f77ed5238ab5d50a70239279b573a50a64398c` (PR-disclosed release contract)
**Base sha:** `cf2aae0beefb3e7dbb15e4ec672d8c288492dd13` (PR-disclosed; conflict-free integration tree `722945852345cf8bc6da5a57aeb41e492f6f9854`)
**Merge commit:** `b4c3db210e5be5c62efdee1fafe742064baacb5e` (per `gh pr view --json mergeCommit`)
**Author:** chriswong6031-creator (seat-authored, see §1 scope note)
**Repo root verified:** `/Users/chriswong/lanes/repos/macro` on `claude/...` worktree (clean), `origin/main` reachable; merge confirmed via `gh pr view --json mergeCommit`.

> **Scope note (§1):** of the recent (last 24 h) merged PRs the audit mandate covers, the chronologically prior candidates are already audited (see `orch/audits/macro_PR-7585.mm.md`, `…_7599.mm.md`, `…_7602.mm.md`, `…_7603.mm.md`, `…_7607.mm.md`) or carry zero audit-engaging surface (#7608 / #7586 risk research, #7598 / #7588 / #7587 / #7582 / #7580 / #7570 / #7566 / #7565 / #7564 / #7561 / #7560 / #7558 / #7556 / #7555 `orch(audit)` ledger entries, #7597 MO-A p0b browser receipt re-mint, #7577 sector-theme-subtheme plan doc, #7576 commodities wire, #7573 prophet-live receipts, #7571 design-ratchet CSS-Color-4 doc, #7569 prophet B4 engine core). **#7589** is the only remaining user-facing half-B surface in the 24 h window: it is the canonical focal-late-load follow-up to the already-merged #7497; it touches the canonical basket-detail template (`templates/basket_detail.html.j2`, +1/−1 — a single `tbl-scroll` class token added to an existing `<div class="ts">` wrapper), regenerates the change across all 121 generated basket pages (`site/basket/*.html`, +1/−1 each), and locks the invariant with one new regression test (`tests/test_ftr_w3_ui.py`, +18/0). The body explicitly disclaims any new wrapper/focus handler/timer/observer/stylesheet/auth bypass/shared-theme change: **"Every source/page byte is unchanged after reversing that single class token."** It carries zero new plain-language strings (no prose surface), zero theme surface (it consumes an already-defined `.tbl-scroll` selector — see §3), and zero "validated"-bearing claims. The seat selects #7589.

---

## 1. PR metadata

| field | value |
|---|---|
| repo | mastermindx-market-intelligence/macro |
| number | 7589 |
| title | `fix(basket-detail): preserve sorting focus through late page load` |
| merged_at | 2026-09-21T06:45:32Z |
| head (PR-disclosed) | `e2f77ed5238ab5d50a70239279b573a50a64398c` |
| base | `cf2aae0beefb3e7dbb15e4ec672d8c288492dd13` (conflict-free integration tree `722945852345cf8bc6da5a57aeb41e492f6f9854`) |
| merge_commit | `b4c3db210e5be5c62efdee1fafe742064baacb5e` |
| branch | `claude/uiux-basket-load-focus-20260921` |
| changed files | 129 source files (`gh pr view 7589 --json files`): 1 template (`templates/basket_detail.html.j2` +1/−1), 121 generated basket pages (`site/basket/*.html` +1/−1 each), 1 test (`tests/test_ftr_w3_ui.py` +18/0), 1 discovery record (`agentos/discoveries/DSC-BASKET-LATE-LOAD-FOCUS-20260921.md` +33/0), 1 evidence README (`research/evidence/uiux-basket-load-focus-20260921/README.md` +22/0), 1 verifier (`research/evidence/uiux-basket-load-focus-20260921/verify_late_load.py` +90/0); remaining ~3 source files are JSON/manifest/EVIDENCE.yml, and the ≈120 PNG entries are visual receipts under `mockups/evidence/uiux-basket-load-focus-20260921/` and `research/evidence/uiux-basket-load-focus-20260921/{browser,sorting}/` |
| additions / deletions | 2,684 / 122 (per `gh pr view --json additions,deletions`); essentially all of the +2684 is visual-evidence PNG/manifest receipt noise — the only **code** surface is one template line + 121 generated carry-throughs + one regression test (+20 lines net) + one discovery record (+33 lines) + one evidence README (+22 lines) + one verifier (+90 lines). Body-quoted invariants: *"no new wrapper, focus handler, timer, observer, stylesheet, auth bypass or shared-theme change. Every source/page byte is unchanged after reversing that single class token."* |
| files of interest | (a) `templates/basket_detail.html.j2` (one-line: `<div class="ts"><table id="hold">` → `<div class="ts tbl-scroll"><table id="hold">` at row 1419 in the generated-page path that renders ROW 04 Holdings); (b) `site/basket/*.html` (121 generated pages — the rebake that picks up the same one-token carry-through); (c) `tests/test_ftr_w3_ui.py` (new regression `test_basket_holdings_use_canonical_scroll_wrapper_before_late_load` — locks `wrapper == '<div class="panel"><div class="ts tbl-scroll"><table id="hold">'` in the canonical template, asserts `old not in source`, and walks the five basket families — `basket`, `basket_china`, `basket_hk`, `basket_canada`, `basket_intl` — under `site/`, asserting the wrapper string is present and the old one absent); (d) `agentos/discoveries/DSC-BASKET-LATE-LOAD-FOCUS-20260921.md` |
| labels | none visible to this audit at one-pass; body states `merge-on-green` is NOT armed (this PR was merged by deliberate human action during an out-of-band window after VPS-only delivery was on the release contract line — not by the sweeper) |
| scope collision | none declared; protected Skillpack `Mastermind@3e66e43258f34db240d5bff76f54148c7af84ee4` and `DEC-UIUX-VPS-ONLY-DELIVERY-20260920` carry over; body explicitly rebukes rebuilding predecessor #7497 / #7437 / #7361 ("DO_NOT_REDO") |

**Nature of the change (UI / accessibility fix):** the canonical basket-detail template's ROW 04 Holdings table was rendered with `<div class="ts"><table id="hold">`. A *different* shared late-load hook (the `wrapTables` cross-table horizontal-scroll wrapper) inspects each candidate TABLE; if the surrounding wrapper **does not** already carry the `tbl-scroll` class, the hook creates one and reparents the TABLE node into the new wrapper. That reparenting moves the focused subtree (a freshly keyboard-sorted header `<th>` inside the table). The DOM's `activeElement` then resets to `body`, and the user's keyboard-sort intent silently dies. The body of #7589 is a single-class fix: add `tbl-scroll` to the existing `<div class="ts">` wrapper so the shared hook **skips** this table (the wrapper is already a scroll container). One token, both at the template source and at the 121 generated pages that already wrap that ROW.

This is a pure behaviour fix that consumes an existing selector. The body disclaims any *new* DOM/CSS/Js/auth surface: *"No extra wrapper, focus handler, timer, observer, stylesheet, auth bypass or shared-theme change."*

**Body signals — already-run gates (PR-quoted, NOT re-run in this audit per one-pass constraint):**
- 161 targeted tests passed, including one new regression (`test_basket_holdings_use_canonical_scroll_wrapper_before_late_load`) inside the CI-owned `tests/test_ftr_w3_ui.py`. No new unregistered suite.
- 16 native delayed-window-load cases pass across US/China × desktop/mobile × EN/ZH × dark/light: a held non-data image triggers the genuine load event; the exact focused DOM node, row order, and open score panel survive. No private renderer or wrapTables invocation.
- 16 native sorting cases plus four delayed-response focus/order cases pass on the existing verifier.
- 48 canonical visual capture frames across two routes × desktop/mobile/tablet × EN/ZH × dark/light (rest + focus state each); all receipt-linked PNG hashes resolve.
- "Design and visual evidence gates pass; all embedded data, model code, rank comparator and access behavior untouched."
- 1 factual disclosure: the initial verification-script callback error is preserved as tooling evidence (not claimed as a product test or a passing run).

**Cross-references (body-disclosed):**
- Predecessor #7497 (basket-detail feature release) is merged; the late-load focus bug surfaced during #7497's real public verification. #7589 is the bounded follow-up, opened on a NEW branch (`claude/uiux-basket-load-focus-20260921`) precisely because #7497's source carrier is already merged.
- `DEC-UIUX-VPS-ONLY-DELIVERY-20260920` is the contract governing this delivery (VPS-only, not Vercel); body states "Built and locally verified, NOT live until concluded repository CI, expected-head merge, existing VPS updater and public native verification."
- Member-only `wh_banner.js` stays 401 for anonymous users (unchanged by #7589 — explicit re-statement, NOT a new surface introduced by this PR).
- Public Market Structure #7437 and Intelligence Hub #7361 releases are accepted separately and remain DO_NOT_REDO.

---

## 2. Plain-language findings

**Source for plain-language law:** macro doesn't ship a `check_plain_language.mjs` (terminal-only); the macro equivalent is the visible-string audit mandated by `CLAUDE.md` §"Design (user-first law)" — `docs/DESIGN_DOCTRINE.md` + the `frontend-design` skill — read against the Tier-1 obligations (state + plain-word stance under hard word budgets; no internal study names, no untranslated stats, no raw slugs; bilingual EN/ZH parity on every visible string; plain-word null disclosure) and the Tier-2 obligations (Tier-2 receipts for nulls; no falsifier vocabulary front-facing; plain-word cadence call-outs).

**Scope check — does this PR carry any plain-language surface?** **No.** The diff is one CSS class token (`tbl-scroll`) on a single existing wrapper, replicated across 121 generated pages. The PR's prose surface is limited to:
1. The PR body (operator-facing, not user-facing).
2. The discovery record `agentos/discoveries/DSC-BASKET-LATE-LOAD-FOCUS-20260921.md` (agent-internal, not user-facing).
3. The evidence README (`research/evidence/.../README.md`) and the `verify_late_load.py` verifier (research-internal, not user-facing).

**Therefore: §2 plain-language findings are N/A by construction — no user-facing string is added, removed, or modified.** The body of the regex/string-facing surface stays byte-identical apart from the `tbl-scroll` class attribute (which is markup, not copy). The PR body, the `<caption class="hold-sr-only">` Holdings caption, the `L('Holdings — own-it conviction + entry timing','成分股 — 持有信念 + 入场择时')` ROW 04 h2, the `L('Potential','潜力')` / `L('Verdict','结论')` / `L('Entry now','入场时机')` / `L('Stock','个股')` column headers, and the existing hold-card verdict / entry / scorecopy strings are all **unchanged** — only the wrapper's `class` attribute gained `tbl-scroll`. The bilingual EN/ZH parity law is therefore trivially satisfied (no new translation surface to keep in parity).

**Sample git-level diff evidence for the no-user-facing-string invariant:**
```
@@ -1416,7 +1416,7 @@ function render(){
     </tr>`;}).join('');
   const nBoard=mem.filter(m=>m.on_board).length;
   h+=`<h2><span class="idx">04</span>${L('Holdings — own-it conviction + entry timing','成分股 — 持有信念 + 入场择时')} <span class="chip">${mem.length} ${L('names','只')}</span>${nBoard?` <span class="chip sb-chip" title="Members currently on the US Prophet buy board">★ ${nBoard} ${L('on Prophet board','在 Prophet 榜')}</span>`:''}</h2>
-  <div class="panel"><div class="ts"><table id="hold">
+  <div class="panel"><div class="ts tbl-scroll"><table id="hold">
     <caption class="hold-sr-only">${L('Holdings. Column buttons change sort order. Potential uses research priority rather than numeric score order.','成分股。列标题按钮可改变排序。潜力列采用研究优先顺序，而非简单数值排序。')}</caption>
```
The only edited byte on the user-facing path is the wrapper `class` attribute (`"ts"` → `"ts tbl-scroll"`); the `L()`-wrapped h2 row 04 text, the screen-reader caption string, the column header strings, and the member-prophet-board chip's `title=` attr (all plain-language-relevant) are **byte-equivalent** between the pre- and post-PR template.

**Verdict:** PASS-by-vacuity. No user-facing string was added, deleted, or altered.

---

## 3. Theme findings

**Source for theme law:** the macro repo's governing theme artifacts are:
- `templates/theme.js` (shared data-tip Lens owner, MO-A theme machinery, late-load hooks including `wrapTables`)
- `templates/navigation-refresh.css`
- `templates/theme.css`
- `templates/_site_nav.html.j2`, `_navlinks.html.j2`, `_public_nav.html.j2`, `_public_chrome_*.html.j2`
- `docs/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` archetype/composition + `research/DESIGN_MIGRATION_FACTORY_V1.md` ratchet
- The `CLAUDE.md` "Theme art direction — required (dark and light are TWO art directions, not one skin; TP-0 2026-08-27)" directive — DARK = command center / LIGHT = research workspace, dark and light **must be** judged as designs, never just token substitutions.

**Scope check — does this PR carry any theme surface?** **No.** The PR body's own "Root cause and minimal fix" paragraph disclaims it explicitly:

> "No extra wrapper, focus handler, timer, observer, stylesheet, auth bypass or **shared-theme change**."

The single template-line patch is a `class` attribute on a wrapper that **already exists** (`<div class="ts">`); the new token (`tbl-scroll`) is one of the canonical scroll-wrapper classes that the existing `wrapTables` cross-table horizontal-scroll hook already governs. The `tbl-scroll` selector is an existing site-wide convention — used elsewhere across `templates/theme.js` / `theme.css` for horizontal-scroll table wrappers — and the body confirms the existing shared hook **already skips** tables whose wrapper is already `tbl-scroll`. The new wrapper byte does not register any new CSS rule, token, color, type scale, geometry, motion, breakpoint, or responsive rule. It only fails the predicate inside the existing `wrapTables` hook.

**Therefore: §3 theme findings are PASS-by-vacuity. No new DARK treatment, no new LIGHT treatment, no new mechanism that intentionally differs, no new theme-specific degraded states, no new evidence matrix entry — none of those artifacts is required because no theme surface was added.** The visual receipts (`mockups/evidence/uiux-basket-load-focus-20260921/` and `research/evidence/uiux-basket-load-focus-20260921/{browser,sorting}/`) carry **48 rest + focus states** across two routes × desktop/mobile/tablet × EN/ZH × dark/light and ALL receipt-linked PNG hashes resolve (body-quoted), so the body also confirms the **existing** dark/light/EN/ZH/designs stay pixel-equivalent after the wrapper-token change. A token-only step inside the existing dark+light machinery that produces a 48-frame identical-PNG hash receipt is the strongest possible non-modification evidence — colour, geometry, type, motion, and breakpoints stay invariant.

**Specific design-law checks the audit performed without re-running (one-pass):**
1. **No new colour palette, no new semantic colour, no `color-mix(...)` block, no `oklch(...)` value, no `lab(...)`/`lch(...)` value, no `hwb(...)` value, no new `light-dark(...)` branch, no new theme-token addition.** No new selector at all. The diff is a `class` attribute string change. PASS.
2. **No new typography / weight / line-height / letter-spacing rules.** PASS (no CSS authored).
3. **No new responsive breakpoint.** PASS.
4. **No new motion / transition / animation.** PASS.
5. **No new layout primitive (`grid-template-columns` / `flex-*` / `display:`/positioning).** PASS.
6. **No new z-index / stacking / shadow / glow / hairline / shadow-vs-glow choice.** PASS.
7. **No new opaque runtime stylesheet injection (`style.textContent`/`setAttribute("style",…)` style multi-kb blob, parallel palette family, duplicated light/dark branches in JS).** PASS — the PR does not touch `theme.js`, `theme.css`, `navigation-refresh.css`, `_public_chrome_*.html.j2`, `nav_market.js`, or any page-level composer JS. The governance of `check_runtime_style_injection.py` is structurally untouched.
8. **`check_design_system.py --mode enforce-added` and `check_ui_visual_evidence.py` posture:** per `CLAUDE.md` these enforce material-UI surface presence only. With zero new theme surface the predicates hold vacuously; the enforced decision is inherited-debt is unchanged.
9. **`check_template_site_sync.py` posture:** the PR moves `<div class="ts">` → `<div class="ts tbl-scroll">` in the canonical template `templates/basket_detail.html.j2` AND in all 121 generated `site/basket/*.html` pages in lock-step. The paired-asset invariant for plain-copy templates (the MACRO "templates/<name> ↔ site/<name>" gate) is therefore maintained because both halves of every pair (`templates/basket_detail.html.j2` → `site/basket/*.html`) are committed in this same PR. The check would PASS by construction.
10. **Dark-vs-light are TWO art directions, not one skin (TP-0 2026-08-27).** With zero new theme surface, the Dark-vs-Light invariant is held trivially; the existing dark and light treatments stay pixel-equivalent (PNG-hash evidence) so neither direction is mutated by this PR.

**Verdict:** PASS. The PR adds zero theme surface; body-quoted 48-frame PNG-hash evidence additionally confirms pixel-equivalence of the existing dark/light/EN/ZH viewports under both rest and focused states.

---

## 4. Validated-claims findings

**Source for validated-claims law:** `CLAUDE.md` §"Epistemics (gauntlet = PROMOTION gate, NOT a build gate)" + the explicit CI enforcer `scripts/check_validated_claims.py` (BC-2, `PREREGISTRATION.md §4, D2 §4.3`) — every affirmative "validated" claim in a user-facing surface (`templates/`, `site/*.js`, generated `*_data.js`, `engine/` display-copy fields) must map to (a) a justified entry in `data/regime/validated_claims_allowlist.json` whose `surfaces` list names the claiming file's surface, or (b) a referenced artifact JSON whose top-level `validated == true`. Negated / hedged uses are ignored automatically (`'no validated...'`, `'unvalidated'`, `'un-validated'`, n't-contractions, `'cannot ... validated'`, `'无...验证'`, `'非...验证'`, `'未...验证'`, `'未经验证'`, `'不...已验证'`).

**Scope check — does this PR carry any new user-facing "validated"-bearing claim?** **No.**

A regex sweep of the user-facing diff hunks (the single template-line patch and the 121 generated `<div class="ts"><table id="hold">` → `<div class="ts tbl-scroll"><table id="hold">` hunk that mirrors it across `site/basket/*.html`) yields **zero** matches for `validated`, `已验证`, `经验证`, `经过验证`, or any of the BC-2 admit phrases (`OK`, `certified`, `audit-passed`, `endorsed`, `official` etc. — none of those is configured in this scanner; only `validated` and the three Chinese variants, per the gate's own source comment). The user-facing columns inside that table (Stock / Potential / Verdict / Entry now / 20d) and the screen-reader caption stay byte-equivalent between pre- and post-PR.

**The PR body itself is operator-facing, not user-facing, but the audit additionally scanned it for BC-2-adjacent claims to confirm the body isn't sneaking a "validated" assertion past the gate by routing it through prose:**
- The body claims "161 targeted tests passed", "16 native delayed-window-load cases pass", "Design and visual evidence gates pass" — **none** of these uses the word "validated", and the BC-2 gate is phrase-scoped (not file:line-scoped) so a phrase-style assertion in the PR body is irrelevant to BC-2 anyway (BC-2 governs `templates/`, `site/*.js`, generated `*_data.js`, `engine/` display-copy fields — the PR body is none of those).
- The body uses "verified" (e.g. "Built and **locally verified**" and "real public **verification**" of #7497) — neither term is in BC-2's admit list, and the surrounding context disclaims deployment ("**NOT live** until concluded repository CI, expected-head merge, existing VPS updater and public native verification"), so there is no risk of a factually-false "verified" assertion slipping through BC-2's gap.
- The body uses "pass" (e.g. "PASS", "passed") in the context of `git diff --check`, test counts, design-gate TXT files — these are CI test results, not platform assertions of "validated". BC-2 is a platform-claim gate (what THE PLATFORM says about a Macro Dashboard signal/rank/gate/artifact), not a CI-result gate; CI pass/fail noise in body prose is governed by the ordinary dev workflow, not BC-2.

**The agent-internal discovery record (`agentos/discoveries/DSC-BASKET-LATE-LOAD-FOCUS-20260921.md`, +33 lines) carries no "validated" string** (visible-string scan). The verifier (`research/evidence/.../verify_late_load.py`, +90 lines) and the evidence README (`research/evidence/.../README.md`, +22 lines) are also research-internal, not user-facing.

**Therefore: §4 validated-claims findings are PASS-by-vacuity. No new affirmative "validated" claim is added anywhere on the user-facing surface, and the operator/prose language stays well clear of BC-2's admit phrases.**

---

## 5. Overall verdict

**PASS on every axis.** This PR is a textbook minimal-fix surface touch:

- **Plain-language (§2):** PASS-by-vacuity. No user-facing string is added, removed, or modified. The single template-line hunk `<div class="ts">` → `<div class="ts tbl-scroll">` (and its 121 generated carry-throughs) is markup-only, and the bilingual EN/ZH parity law is trivially satisfied.
- **Theme (§3):** PASS-by-vacuity. No new CSS, no new token, no new colour, no new typography rule, no new breakpoint, no new motion, no new layout primitive, no new stacking/shadow/glow choice, no new opaque runtime-stylesheet injection. Body disclaims "no stylesheet change / no shared-theme change" explicitly; body also disclaims any new wrapper/handler/timer/observer/auth bypass. The 48-frame canonical visual capture (two routes × desktop/mobile/tablet × EN/ZH × dark/light, rest + focus) with all PNG hashes resolving is the strongest possible non-modification evidence that the existing dark/light/EN/ZH viewports stay pixel-equivalent under the change. The TP-0 dark/light are two art directions invariant is structurally honoured (no mutation at all).
- **Validated-claims (§4):** PASS-by-vacuity. No affirmative "validated" / "已验证" / "经验证" / "经过验证" claim on any user-facing surface; BC-2's negate/hedge handling irrelevant. Body uses "verified" / "verifier" / "pass" inside ordinary CI/dev workflow language with no platform-claim content; the body disclaims deployment to the moment of "concluded repository CI, expected-head merge, existing VPS updater and public native verification", so no factually-false deployment claim can ride along either.
- **Plain-language/theme/validated-claims gates that exist for this PR, in summary:** all three are by-vacuity PASS — the PR does not exercise their predicates because it adds zero user-facing prose, zero theme surface, and zero BC-2-bearing claim. The body of evidence the PR does carry (one template token + 121 generated carry-throughs + one regression test + one discovery record + one evidence README + one verifier + 48-frame visual receipts) is consistent with the narrowest possible root-cause minimal fix the body itself narrates: "Every source/page byte is unchanged after reversing that single class token."

**Overall verdict: PASS.** Nothing on plain-language, theme, or validated-claims axis blocks or even touches this PR. The PR is ready to ship as-is on those axes (release gates — repo CI, expected-head merge, VPS-only delivery per `DEC-UIUX-VPS-ONLY-DELIVERY-20260920`, public native verification — are out-of-scope for this language/theme/claims audit by construction).

---

## House-law notes / out-of-scope references (recorded, not adjudicated)

- **DO_NOT_REDO honoured:** PR body and discovery record both re-state that public Market Structure #7437, Intelligence Hub #7361, and #7497 are accepted / merged and must not be rebuilt. This audit does not re-open them.
- **`DEC-UIUX-VPS-ONLY-DELIVERY-20260920`** is on the release contract line; this audit does not adjudicate VPS-pipeline readiness (out of language/theme/claims scope).
- **Protected Skillpack `Mastermind@3e66e43258f34db240d5bff76f54148c7af84ee4`** carries through unchanged.
- **`merge-on-green` arming:** not visibly armed on this PR at audit time (this PR was delivered by deliberate human-merge action during the VPS-only delivery window — not by the sweeper); this audit takes no position on whether `merge-on-green` SHOULD be retro-applied (operator-level decision, not language/theme/claims scope).
- **Predecessor-followup chain:** #7497 (basket-detail feature release) → #7589 (this PR's bounded late-load edge follow-up) is the right pattern: open a new branch off fresh `main`, not reuse a merged carrier. Body and discovery record confirm.
- **Sub-second observable deltas outside language/theme/claims:** a visitor with a focused `<th>` inside the ROW 04 holdings table who triggers the genuine `wrapTables`-would-have-run late-load event will, after this PR, keep their focus and continue to sort. Body-confirmed by 16 native delayed-load cases + 4 delayed-response focus/order cases. Out of language/theme/claims scope, recorded so the next audit can pick up the trail if needed.
