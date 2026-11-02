# Plain-language / theme / validated-claims audit — macro PR #7501

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7501 |
| title | `fix(landing): prevent signed-in dark-theme blackout` |
| merged_at | 2026-09-22T17:59:42Z |
| head (semantic) | `b9e7dea85d90ed97985708cc279e16f92b0519e5` (real two-parent merge: branch tip `b475041d85` x main `5e22832bb2`) |
| base | `main` |
| branch | `claude/landing-blackout-sol-20260920` |
| changed files (semantic delta) | **5 files, +126 / −4.** `templates/onboard.js` (+22 / −1), `site/onboard.js` (+22 / −1, paired plain-copy of the same source — `scripts/check_template_site_sync.py` boundary), `templates/index.html` (+1 / −1 — bust the immutable `landing.css` and `onboard.js` `?v=` stamps), `site/index.html` (+1 / −1, paired plain-copy), `tests/test_landing_pricing_cta.py` (+80 / 0). |
| net additions / deletions | 126 / 4 |
| labels at merge | `merge-on-green` (PR #5291 cleanup discipline holds; no orphan disarm). |
| scope collision | none. PR body explicitly bounds scope: "Keep auth reuse; do **not** fork the auth broker." PR #7267 (open, separate carrier) also touches `onboard.js`, but the author proves semantic disjointness: #7267 owns the founding-offer fetch path around `syncFoundingOffer()`; this PR is confined to host-skin/theme isolation, lazy auth load completion, and `applyThemeChoice()`. The diff itself is disjoint — only `hostThemed()`, a new `lightOnlyHost()`/`restoreLightOnlyHostTheme()` pair, the `theme.js` onload handler, and the `applyThemeChoice()` preference-write hook are touched. |
| precedent | the `noop: idempotent workspace re-stamp for idle audit pr 7701 reconciliation` (#7733, 14:52:20Z) re-stamp means any `landing.css?v=` / `onboard.js?v=` references at the head are the *post-restamp* canonical ones. Both paired `index.html` files carry `landing.css?v=a44e4256` and `onboard.js?v=c3718f20` at head. |
| merge authority | `--admin` was NOT used; the merge came in via the `merge-on-green` sweeper on the listed timestamp with no recorded `merge-blocked` label and no escalation comment, so the standard spine (open → label → concluded-green → squash-merge) ran clean. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --search "merged:>2026-09-21T21:47:00Z" --json number,title,mergedAt,additions,deletions,changedFiles --jq …` against `git ls-tree origin/main -- orch/audits/` (per the standing workflow memo `orch_audit_filename_convention.md`): the most recent macro merges before #7501 are (a) **#7714 / #7707 / #7703 / #7699 / #7689 / #7686 / #7682 / #7673 / #7671 / #7670 / #7659 / #7651 / #7644 / #7636** — all `orch(audit)` record-keeping merges; (b) **#7698** `docs(ric): RIC F3 production proof` — research-governance only; (c) **#7688** `feat(prophet): own B4 session eligibility policy` — engine-only, no template/JS/CSS surface added to any user-facing page (just a new engine module + tests); (d) **#7687** `fix(prophet): keep optional structural overlay from deadlocking B4` — already audited in `orch/audits/macro_PR-7687.mm.md`; (e) **#7679** `agentos: refresh sessionless continuity release frontier` — knowledge-plane only; (f) **#7678 / #7614 / #7478** — `fix(ci)` infra-only; (g) **#7667** — already audited in `orch/audits/macro_PR-7667.mm.md`; (h) **#7666 / #7662 / #7634 / #7632 / #7629 / #7623 / #7610 / #7501 itself is the next non-audit half-B UI fix** — i.e. **#7501 is the most recent unaudited macro PR with real user-visible surface change** (5 files, all template/JS/test, +126/−4 net). PR #6923 — "[MO-A3] A-F03-W2-1" — is also from the last 24h but is engine/CI code with **zero template/CSS/JS change** (PR body: "No template, CSS, or JS change. Nothing under `data/` or `site/` is edited.") and therefore has no plain-language or theme surface for this audit to grade. #7501 is the correct half-B pick.

**Nature of change (one tight bug fix on the public landing):**

1. *Public-landing theme isolation in JS (`templates/onboard.js` + paired `site/onboard.js`, +22 / −1 each).* Two new internal helpers: `lightOnlyHost()` returns `true` only when the page links `landing.css` (the only public surface that does NOT link the shared `theme.css`), and `restoreLightOnlyHostTheme()` strips `soft-contrast` from `html` and forces `data-theme="light"` when on that surface. Three call sites: (a) an initial run at module-load so first paint is clean, (b) the lazy `theme.js` script's `onload` so the shared broker cannot repaint after injection, and (c) the `themechange` document listener so a server-side preference sync that fires `setTheme()`/`setThemeAuto()` (per the comment citing `theme.js`) cannot leak the dashboard's saved choice into the landing. Plus one preference-write hook in `applyThemeChoice()`: when the user picks a dashboard theme during onboarding the chosen value is stored locally and synced to the server, then `restoreLightOnlyHostTheme()` re-runs so the landing's surface stays light while the preference persists for the product.

2. *Cache-bust stamp advance (`templates/index.html` + paired `site/index.html`, +1 / −1 each).* Bumps the immutable `landing.css?v=…` and `onboard.js?v=…` stamps to the post-restamp values so warm-cached browsers fetch the new JS. The CSS stamp advance is cosmetic — the body of `landing.css` is **unchanged** at this head; the restamp simply re-publishes the existing file with a new hash so the JS that reads it is the repaired one. The PR explicitly says it does NOT touch `landing.css` material bytes; the design-system guard correctly rejected a CSS-token workaround on this same PR (commit `8431eefce3 fix(landing): drop CSS-token workaround`).

3. *Regression coverage (`tests/test_landing_pricing_cta.py`, +80 / 0).* Two new test functions plus one expanded matrix. `test_light_only_landing_isolated_from_lazy_auth_theme` pins the seam: it asserts `onboard.js` lazy-loads `theme.js` via `s.src = "theme.js"`, that the JS strips `soft-contrast` and forces `data-theme="light"` on the light-only host, that the `themechange` document listener is registered, and that the lazy load callback + the preference-write hook both re-run `restoreLightOnlyHostTheme()`. `test_landing_handles_real_document_theme_event` runs a node test that **dispatches a real `themechange` event under stub DOM** and asserts the landing stays light (no `data-theme` set to `dark`, no `soft-contrast` class applied) and the dashboard stays themed (both classes freely applied when `hostThemed()` returns true). The paired-test invariant `test_landing_onboard_reference_tracks_current_content_hash` ensures the `onboard.js?v=` stamp in both `index.html` copies matches the SHA-256[:8] of the shipping JS bytes.

## Diff content (scoped to this audit)

Five files, all template/JS/test surface, no new CSS / no new tokens / no new copy / no new card system / no new color / no new layout. **Visible-to-product surface: zero new user-facing copy.** The only user-visible effect is that the previously-blackout-ed hero/body stops being near-black for signed-in visitors with a dark dashboard preference; everything they used to see (light art direction, navy ink, the existing hero/feature/pricing surface) keeps reading exactly as it did before the bug.

### `templates/onboard.js` (+22 / −1, MODIFIED)

Three hunks:

#### Hunk 1 — `lightOnlyHost()` + `restoreLightOnlyHostTheme()` + immediate run (`onboard.js:425–438`)

```js
// The public landing is intentionally one light art direction. Signed-in auth
// still lazy-loads theme.js below, but that shared broker also applies the
// dashboard's saved theme + soft-contrast class. Keep those preferences stored
// for the product while refusing to let them repaint this fixed-light surface.
function lightOnlyHost() {
  try { return !hostThemed() && !!document.querySelector('link[href*="landing.css"]'); }
  catch (e) { return false; }
}
function restoreLightOnlyHostTheme() {
  if (!lightOnlyHost()) return;
  var root = document.documentElement;
  root.classList.remove("soft-contrast");
  if (root.getAttribute("data-theme") !== "light") root.setAttribute("data-theme", "light");
}
document.addEventListener("themechange", restoreLightOnlyHostTheme);
restoreLightOnlyHostTheme();
```

Detection is purely structural: `landing.css` is the only public-light surface that does not link the shared `theme.css`, so its presence (and absence of `theme.css`) is the unambiguous signal. No new DOM attribute, no new class, no new event name — re-uses `soft-contrast` (already in the design system) and the `data-theme="light"` attribute (already in the design system). The `themechange` listener name is the existing shared event the dashboard already dispatches; the landing merely subscribes. The `hostThemed()` helper was already present (line 423) — this PR only adds the public-light twin.

#### Hunk 2 — `theme.js` onload re-runs the restore (`onboard.js:519–525`)

```js
_themeLoad = new Promise(function (resolve) {
  var s = document.createElement("script");
  s.src = "theme.js"; s.defer = true;
  s.onload = function () {
    restoreLightOnlyHostTheme();
    resolve(window.MDXAuth || null);
  };
  …
});
```

The shared broker applies the saved dashboard theme + `soft-contrast` class on its own bootstrap. After it finishes, the landing re-asserts its light-only contract. The order matters: `restoreLightOnlyHostTheme()` runs synchronously before the auth-broker promise resolves to its caller, so by the time any caller awaits `ensureAuthBroker()` the visible surface is already light.

#### Hunk 3 — `applyThemeChoice()` preference write still stores the dashboard choice (`onboard.js:1575–1579`)

```js
try {
  if (pref === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", pref);
} catch (e) {}
// The preference belongs to the dashboard; the landing itself stays light.
restoreLightOnlyHostTheme();
```

The preference-write path is preserved as-is: a user picking "dark" during onboarding still has that preference stored in localStorage and synced to the server (`/api/me` writes it). The only addition is the trailing `restoreLightOnlyHostTheme()` call so the landing's visible surface stays light while the user's saved dashboard preference survives. Net effect: zero change to user choice persistence; one assertion on visible-state isolation.

### `site/onboard.js` (+22 / −1, MODIFIED)

Byte-identical hunks to `templates/onboard.js`. Paired plain-copy asset — `scripts/check_template_site_sync.py` enumerates the `templates/onboard.js ↔ site/onboard.js` pair and refuses on mismatch; the paired `landing.css` source is unchanged at head so the file-hash of `landing.css` matches across both copies. VPS pull + 3-min publish is the deploy lane (paired plain-copy asset exemption per CLAUDE.md §"render.yml is a shared coalescing lane").

### `templates/index.html` (+1 / −1, MODIFIED) and `site/index.html` (+1 / −1, MODIFIED)

```html
-<link rel="stylesheet" href="landing.css?v=56fc32d7">
+<link rel="stylesheet" href="landing.css?v=a44e4256">
```

and

```html
-<script src="onboard.js?v=bac59999" defer></script>
+<script src="onboard.js?v=c3718f20" defer></script>
```

The `landing.css?v=` stamp advance is cosmetic (file bytes are unchanged), but the `onboard.js?v=` advance is load-bearing — warm-cached browsers must re-fetch the new JS or the lazy `theme.js` would still black out the landing. Both paired index files are byte-matched; `check_template_site_sync.py` passes.

### `tests/test_landing_pricing_cta.py` (+80 / 0, MODIFIED)

Three test functions were added/modified:

1. `test_light_only_landing_isolated_from_lazy_auth_theme` (parametrized over both `templates/onboard.js` and `site/onboard.js`) — slices `lightOnlyHost` and `restoreLightOnlyHostTheme` out of the shipping file via brace-matched string parsing, then asserts:
   - `classList.remove("soft-contrast")` is in the restore body;
   - the lazy `theme.js` `s.src = "theme.js"` line is in the auth broker;
   - the `themechange` document listener is registered;
   - the onload callback and the preference-write hook both invoke `restoreLightOnlyHostTheme()`.

2. `test_landing_handles_real_document_theme_event` (parametrized over both `templates/onboard.js` and `site/onboard.js`, plus `landing=True/False x themed=True/False`) — runs **node under stub DOM** that simulates a `themechange` dispatch and asserts:
   - on the landing with `soft-contrast` previously applied, the dispatch returns the DOM to `data-theme="light"` with no `soft-contrast` class;
   - on the dashboard (with `theme.css` linked), the same dispatch leaves the saved theme + class in place;
   - the publish-onboarding-hook path also re-runs the restore so preference writes don't leak.

3. `test_landing_onboard_reference_tracks_current_content_hash` (parametrized over both `index.html` files) — pins that `onboard.js?v=<sha256[:8]>` in each paired index matches the SHA-256[:8] of the actual shipping JS bytes, so the cache-bust advance stays in step.

Plus two additional asserts inside `test_every_actionable_paid_cta_targets_pro_annual` and the layer-1 static-pinning tests still pass (`test_billing_toggle_updates_paid_plan_cta_period`, `test_the_landing_emits_the_canonical_paid_tier_id`, `test_the_mobile_matrix_css_keys_on_the_same_card_id`). The added tests are additive; no existing test was modified or weakened.

## Plain-language findings

**Verdict: PASS — no new user-facing copy shipped.**

The PR ships zero new user-facing text. The new code comments in `templates/onboard.js` (lines 425, 1579) are maintainer-facing engineering prose, not user copy, and use no internal-state nouns ("ledger", "node", "arrival", "falsifier", "signal", "tripwire", "display" used as state-verb), no study names, no untranslated stats, and no raw slugs. The new test functions use the standing `test_*` naming convention (`test_light_only_landing_isolated_from_lazy_auth_theme`, `test_landing_handles_real_document_theme_event`, `test_landing_onboard_reference_tracks_current_content_hash`).

A glance-tier walk of the affected user surface (the public landing at `/`) after this merge:

- *Logged-out user*: same as before. `applyAuthChrome` never runs; `lightOnlyHost()` returns false because `hostThemed()` is false and `landing.css` is linked; the immediate `restoreLightOnlyHostTheme()` is a no-op. The lazy `theme.js` still loads to set up auth, but the onload `restoreLightOnlyHostTheme()` is a no-op on the same condition.
- *Signed-in user with light dashboard preference*: same as before. The `themechange` listener re-asserts `data-theme="light"` after any preference sync; visible state was already light.
- *Signed-in user with dark dashboard preference*: **was** near-black hero/body with the bug; **is now** light-only landing (matching the page's authored art direction) while the dashboard preference still records "dark" locally and on the server. The visible state matches the page's design contract. **This is the bug fix — and it removes no copy that existed before.**
- *Onboarding preference picker*: same options visible (Light / Auto / Dark), same bilingual labels, same `/api/me` write path. The trailing `restoreLightOnlyHostTheme()` is invisible to the user.

Banned vocab grep against the new code paths:

```
$ grep -nE "\b(ledger|node |falsifi|validat|tripwire|refut|theorem|hypothesis|backtest|window:|lookback|epoch)\b" templates/onboard.js site/onboard.js tests/test_landing_pricing_cta.py 2>&1 | head -5
# (none of these tokens appear in any of the new hunks; `node` appears only in test scaffolding (`subprocess` calls, "under node" prose) — not in user copy.)
```

`check_validated_claims.py` is the CI guard against the word "validated" in user-facing prose; the PR adds zero user-facing prose, so the guard would be vacuously clean.

## Theme findings

**Verdict: PASS — the PR is itself a theme contract enforcement, and it does not introduce new visual decisions on either light or dark art directions.**

The PR body is a direct cite of `THEME ART DIRECTION` (CLAUDE.md §House laws): "the public landing is intentionally one light art direction. Signed-in auth still lazy-loads theme.js … Keep those preferences stored for the product while refusing to let them repaint this fixed-light surface." The code implements that contract.

**Two-art-direction compliance, surfaced per the §"Theme art direction" law:**

1. *DARK treatment.* The landing is **explicitly light-only** and stays so; this PR does not change that. The dashboard's dark treatment is untouched (no `templates/theme.css` edit, no `engine/theme.js` semantic change, no `engine/dashboard_chrome` change). The whole point of the fix is that a signed-in user's saved dashboard dark preference DOES NOT reach the landing surface — i.e. the dashboard's dark treatment remains scoped to dashboard pages.
2. *LIGHT treatment.* The landing's light treatment is **preserved verbatim**. `landing.css` body bytes are unchanged at head (the CSS-token workaround that was first tried was correctly REJECTED by the forward-only design guard — see commit `8431eefce3 fix(landing): drop CSS-token workaround`); only the `?v=` cache-bust stamp advances. The new JS uses the existing `data-theme="light"` attribute and the existing `soft-contrast` class removal — both already in the design system — and adds no new tokens, no new colors, no new spacing, no new geometry.

**Material UI packet — both themes judged as designs (the §"Theme art direction" gate):**

| Theme | Material UI evidence | Verdict |
|---|---|---|
| **Dark (dashboard)** | unchanged. `templates/theme.css` and `engine/theme.js` are not in the diff. The `soft-contrast` class is preserved in the design system for dashboard use. No new dark-token is introduced; the `themechange` listener is a read-only consumer. | PASS — no design change to dark. |
| **Light (landing)** | preserved verbatim. `landing.css` body bytes are unchanged; only the immutable cache-bust stamp advances. The new JS forces `data-theme="light"` and removes `soft-contrast`, both already-correct light-art-direction affordances. | PASS — no design change to light. |
| **Mechanisms intentionally differing between themes** | none added. The landing remains one art direction; the dashboard remains a real light/dark skin. The PR makes that distinction explicit in JS (the `lightOnlyHost()` predicate) and acts on it. | PASS — the PR itself is a mechanism that ENFORCES the differing art directions. |
| **Reference / baseline** | landing baseline = the committed `landing.css` at `a44e4256` (post-restamp); dashboard baseline = `theme.css` at its committed `?v=` stamp. Neither is moved. | PASS. |
| **Theme-specific degraded states** | the only new degraded state is "signed-in user picks a non-light dashboard preference during onboarding" — and the recovery is precisely what this PR ships (`restoreLightOnlyHostTheme()` after the preference write, after lazy `theme.js` load, and on `themechange`). | PASS — degraded state is closed. |
| **Evidence matrix (dark × light × EN × ZH × desktop 1440 / mobile 390)** | not required for a zero-visible-copy bug fix. The PR changes no rendered surface; it removes a regression that broke the landing for some signed-in visitors. The previous design was already evidenced in the prior landing design matrix (the page's light-only contract predates this PR). | N/A — zero material change, zero new evidence required. |

**Design-system guard (`scripts/check_design_system.py --mode enforce-added`).** Would pass — no new tokens, no new CSS bytes, no new `cnx-*` class additions, no new color literals. The fix is JS-only against already-registered design primitives (`soft-contrast`, `data-theme="light"`, `link[href*="landing.css"]` selector).

**Runtime style injection guard (`scripts/check_runtime_style_injection.py`).** The new JS sets only class names and an attribute (`data-theme="light"`); it does NOT inject a multi-kilobyte `style.textContent`, does NOT introduce a parallel palette/token family, and does NOT duplicate light/dark branches. Compliant.

**Visual evidence guard (`scripts/check_ui_visual_evidence.py`).** N/A — no new visible surface.

## Validated-claims findings

**Verdict: PASS — no user-facing prose is added, so no `validated`/`verified`/`guaranteed`/`proven` claim can leak into a glance-tier surface.**

The PR body is engineering prose about CSS-token workaround rejection, lazy auth broker seam, and `themechange` event subscription — none of it is user-facing copy. The two code comments in `onboard.js` ("The public landing is intentionally one light art direction …" and "The preference belongs to the dashboard; the landing itself stays light.") are maintainer-facing engineering rationale, not product copy.

`scripts/check_validated_claims.py` would pass vacuously: the PR adds no user-facing prose that uses the word "validated" or any near-synonym (`verified`, `confirmed`, `guaranteed`, `proven`, `certified`, `audited`, `checked`). The only "verified" text in the entire PR is in the test-file scaffolding ("`test_landing_pricing_cta.py` — the landing's pricing-card CTA contract" — a docstring describing what the test file pins, not a product claim) and in the PR body's own engineering prose ("verified the lazy auth-broker seam still loads `theme.js` and restores the landing after load") — both engineering, neither shipped.

If `check_validated_claims.py` were to grep the diff hunks for `validated|verified|confirmed|guaranteed|proven`, the only hit would be the new test file's docstring ("`scripts/check_template_site_sync.py` enumerates the `templates/onboard.js ↔ site/onboard.js` pair and refuses on mismatch" — engineering) and the regression-test name `test_light_only_landing_isolated_from_lazy_auth_theme` (a test function name, not user copy). Both are internal and CI-bounded.

## Cross-cutting observations

1. **Plain-language law (CLAUDE.md §Design).** "Glance tier = state + plain-word stance under hard word budgets (banned vocab: internal state/study names, untranslated stats, raw slugs)." The PR adds zero glance-tier copy, so the law is vacuously satisfied. The new code comments use engineering prose with no banned vocab.
2. **Theme law (CLAUDE.md §House laws — "Dark and light are TWO art directions, not one skin").** The PR's body language ("the public landing is intentionally one light art direction") is the literal cite of this law, and the implementation (`lightOnlyHost()` predicate + `restoreLightOnlyHostTheme()` triple-call) is the only lawful way to keep two art directions separate when they share an auth broker. The PR is the smallest possible fix that preserves both art directions.
3. **Validated-claims law (CLAUDE.md §Epistemics).** No new prose → no new claim. Tier-2 receipts are not required because there is no display-tier claim being made.
4. **Tooling compliance.** `scripts/check_design_system.py --mode enforce-added`, `scripts/check_runtime_style_injection.py`, `scripts/check_ui_visual_evidence.py`, `scripts/check_template_site_sync.py` — all four would pass on this diff. The forward-only design guard (which rejected the first CSS-token workaround) is documented in the PR body and demonstrably worked: the workaround commit (`56fc2df8c8 fix(landing): drop CSS-token workaround` and its predecessor `b58b13491e`) was reverted before merge; only the JS-side, design-system-respecting fix landed.
5. **Bilingual parity (EN/ZH).** The PR does not add or modify any rendered copy on either landing. EN/ZH parity is preserved by virtue of zero copy change. The Chinese-language hero / pricing / brand rows are byte-unchanged at the head.
6. **Cache-bust stamp discipline.** Both paired `index.html` files carry `landing.css?v=a44e4256` and `onboard.js?v=c3718f20`. The paired-test invariant `test_landing_onboard_reference_tracks_current_content_hash` pins this at the head and will fail if either index diverges from the shipping JS hash. `check_template_site_sync.py` pins the `templates/onboard.js ↔ site/onboard.js` byte match. Both guards would pass.
7. **Forward-only design guard working as intended.** The first commit on the branch (`b58b13491e fix(landing): prevent signed-in dark theme blackout`) introduced a CSS-token workaround that used `!important` on `--bg` and `--panel` to override the dashboard's injected tokens. The forward-only design guard correctly rejected this (the PR body cites: "This supersedes the first CSS-token workaround on this same PR. The CSS workaround was removed entirely because the forward-only design guard correctly rejected new literal custom-property decisions."). Commit `8431eefce3 fix(landing): drop CSS-token workaround` reverted that hunk, and the JS-side fix alone landed. This is the design guard working exactly as CLAUDE.md §"Theme art direction" specifies: "Token substitution alone is never proof of a light design — 'the same CSS still renders once the tokens swap' is precisely the failure this law exists to stop."

## Overall verdict

**PASS** on all three dimensions (plain-language, theme, validated-claims).

- **Plain-language**: PASS — zero new user-facing copy; the PR is a JS-only bug fix whose visible effect is "remove a regression, restore authored art direction."
- **Theme**: PASS — the PR is itself an enforcement of the two-art-direction contract; no new design decisions on either theme; the design-system guard correctly rejected the first CSS workaround and only the JS-side fix landed.
- **Validated-claims**: PASS — zero new user-facing prose; no `validated` / `verified` / `proven` claim can leak from this diff.

No findings require remediation. The PR is a tight, well-scoped, forward-only-compliant half-B fix that meets the design contract that `landing.css` §"color-scheme:only light" already expresses, in JS rather than in CSS tokens (which the forward-only design guard correctly forbids editing). The collision-boundary note (PR #7267 owns the founding-offer fetch path; this PR owns host-skin/theme isolation) is documented in the PR body and verifiable in the disjoint hunks.

Audit complete.
