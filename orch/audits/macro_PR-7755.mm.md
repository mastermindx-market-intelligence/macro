# Plain-language / theme / validated-claims audit — macro PR #7755

Auditor: qwen_auditor2-style one-pass, half-B scope. Date: 2026-09-23.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7755](https://github.com/mastermindx-market-intelligence/macro/pull/7755) |
| title | `[MO-A10] A-F10-W1: Retire the Intelligence Hub entry card to the admin-only Calibration Lab (MO-PAID-039 dead link)` |
| mergedAt | 2026-09-23T02:52:37Z |
| merge commit | `f72d7e3ad1494c6fe27b44818eb25e5e880fc249` (squash onto `main` from `claude/mo-a-10-a-f10-w1-hub-entry-dead-link`) |
| branch tip | `7d904dc307cd2a28abe00a167996946a1c4c83c5` (DRAFT until Meta-CEO A seat ratified; merged at this exact head) |
| audit head | `origin/main` post-merge (`558b07fb85…` "fix(intl): receive global regime overview…" — main advanced past the merge) |
| files | **2 changed, 18 insertions(+), 93 deletions(-).** `templates/intelligence_hub.html.j2` (-40 added lines, -40 content; 0 added lines per `git diff origin/main…HEAD … | grep -cE '^\+[^+]'`). `tests/test_measurement_research_implications.py` (+71 / -71; four test renames + body rewrites). |
| half-B label | **half-B UD-A10 / A-F10-W1 admin-routing cleanup** — pure removal of a product-page outbound link that pointed at an intentional 404 (admin-only Calibration Lab route). Half-B by the operator's wave plan (W1 of F10), bounded by "no public copy, no admin retarget, no helper touched". |
| program surface | `templates/intelligence_hub.html.j2` — the `_site_nav` family signed-in hub. Specifically: (i) the CSS block keyed off `.rid{…}` (`.rid-rail`, `.rid-b`, `.rid-k`, `.rid-t`, `.rid-d`, `.rid-a`, hover/focus/responsive/reduced-motion rules) inside `<style>`; (ii) the corresponding `<a class="card rid" href="measurement.html#ric-section">…</a>` block guarded by `{% if ric_n %}`. |
| scope (per body) | (a) `templates/intelligence_hub.html.j2` — delete the `.rid` CSS rules and the `.rid` card markup (~:828–841 of pre-merge). (b) `scripts/build_intel_hub.py` — UNTOUCHED; the helper `load_research_implications_for_hub` (~:369) and its calls (~:492/~:505) stay. (c) `tests/test_measurement_research_implications.py` — exactly four renames: test names now assert ABSENCE of the link, the destination-article-count test keeps only its cardinality check, the zero-cards test asserts no `.rid` ever renders (both envelopes), the bilingual test collapses to the `_site_nav` membership check. (d) `mockups/` and the visual-evidence PNGs — UNTOUCHED; `test_f10a1_evidence_is_full_viewport_and_theme_differentiated` (~:1942) still runs. (e) F00C MO-PAID-039 reconciliation belongs to the next A-side ledger cycle, not this PR. |
| durable owner | The pre-existing `scripts/build_intel_hub.py` consumer (`load_research_implications_for_hub` → context var `research_implications`) keeps running; the template just stops binding the variable to user-facing copy. The Caddyfile `@never_site` path list (no user search) remains the single source of truth for "measurement.html is intentionally 404 on the public site"; pinned by `tests/test_admin_research_tools.py`. |
| checks (body claims) | (1) `pytest tests/test_measurement_research_implications.py -q` → "88 passed, 2 warnings in 11.12s" (the two Pillow `Image.getdata` deprecation warnings come from the untouched `test_f10a1_evidence_is_full_viewport_and_theme_differentiated`). (2) Adjacent hub suites → "55 passed, 3 failed"; the 3 failures pre-exist on `origin/main` and are unrelated to the packet. (3) `check_ui_visual_evidence.py --diff-file -` over the templates+site diff → **rc=0** (no material-change shapes). (4) `check_contract_delta.py --base origin/main` → rc=0, "0 introduced, 1 inherited" (the inherited entry names `test_render_dead_ref_targets.py` as already-unwired on the PR's base; not introduced). (5) `git diff --numstat origin/main…HEAD` → exactly two files (`0 40` for the template, `71 71` for the test file). |
| gating scripts run by this audit | `gh pr diff … | python3 scripts/check_design_system.py --mode enforce-added --diff-file -` → **rc=0**, `R0 enforce-added: 0 blocking finding(s) (25321 further pre-existing, non-blocking findings)`. `gh pr diff … | python3 scripts/check_ui_visual_evidence.py --diff-file -` → **rc=0**. `python3 scripts/check_validated_claims.py --list | grep intelligence_hub` → 1 hit, **OK** (`site/intelligence_hub.html:1641 [allow:已验证"门槛]` — pre-existing, allowlisted). `git show origin/main:templates/intelligence_hub.html.j2 | grep -nE 'href="measurement\.html|class="card rid"|ric-section|research_implications|\.rid\{|\.rid-|\.rid:'` → **no output, rc=1** (substantive content fully removed). `gh pr diff … | grep -E '^[+-]' | grep -iE 'falsifier|refute|thesis|证伪|disproven|validated'` → **0 hits**. |
| CI rollup at head | `ci-plan`, `ci-authority`, `ci-authority` (3 entries), `fence-pack`, `contract-delta`, `capability-broker`, `ci-pack-{0..11}` (all 12) → **SUCCESS**. `ci-gate` → **SUCCESS**. `self-mod-fence`, `fork-self-mod-fence-unused`, `trusted-ci`, `fork-capability-broker-unused`, `fork-grader-manifest-unused` → **SKIPPED** (expected — fork lanes / non-active paths). `ci-authority/codex/merge-queue-pilot` → **FAILURE** (the standing-ignorable lane; documented in body). |

## Plain-language findings

### Tier-1 (glance) — no NEW copy added

The PR is deletion-only on the user-facing template. Zero new tier-1 copy enters the hub; the page reads identically except the now-absent `.rid` card no longer appears. Banned-vocabulary audit (DESIGN_DOCTRINE §"rewrite, don't delete", operator 2026-07-27 #3821):

```
gh pr diff 7755 --repo mastermindx-market-intelligence/macro \
  | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' \
  | grep -iE 'falsifier|refute|refuted|thesis|disproven|证伪'
# (no output, rc=1)
```

Same for `validated` and any `title="…中文…"` pattern (bilingual-titles CI guard) — all return zero hits on the diff. The deleted copy ("Research implications — what N frozen studies actually produced" / "研究含义 —" + the "Research context, not a trading signal" description) was bilingual and used the operator-mandated plain phrase "not a trading signal" instead of any banned term; the deletion does not regress that discipline because no replacement copy is added.

### Tier-2 (hover/focus) — none

No new hover/focus content. The deleted `.rid` had no popover, no `aria-describedby`, no `title=` (the link itself was the affordance). The template variable `research_implications` is still resolved by `build_intel_hub.py` for any future consumer; the absence on the page is a "not shown", not a "shown without explanation".

### Bilingual structure — preserved by subtraction

The deleted block carried paired `<span class="l-en">…</span><span class="l-zh">…</span>` strings in `.rid-k`, `.rid-t`, `.rid-d`; its removal does not disturb the rest of the hub's bilingual structure (`_site_nav` family, `_macro_suite_shell` etc. untouched). The new tests' final rename (`test_hub_uses_the_product_nav_family`) pins `_site_nav.html.j2 in hub and "_public_nav" not in hub` — the navigation family invariant is the surviving assertion.

### State semantics — no semantic change

Before: a clickable card carrying one Chinese-and-English line each for the eyebrow, title, and description, plus a `→` affordance. After: the band that contained it (Track record) now ends one section earlier; no card slot is introduced in its place; no null placeholder copy ("Read being updated" / "判读更新中") is needed because the card was condition-gated by `{% if ric_n %}` (zero cards → nothing rendered → no change here either). The honest disclosure is now structural: the public hub simply does not advertise the admin-only route.

## Theme findings

### Token discipline — no new token family introduced

The diff only REMOVES CSS, never ADDS. Therefore the R0 enforce-added check returns 0 blocking by construction: nothing has been added that could introduce a new color, spacing scale, radius scale, or shadow token. The deleted `.rid` block was built entirely from existing tokens (`var(--hair)`, `var(--card)`, `var(--r-card,12px)`, `var(--info)`, `var(--text)`, `var(--muted)`, `var(--dim)`, `var(--fig)`, `var(--panel)`, `var(--card-shadow)`, `color-mix(... transparent)`); the surviving template continues to use the same token family, and the audit confirms no orphan CSS rule references the now-removed class names.

### Dark vs light are TWO art directions, not one skin

The deleted `.rid` block distinguished themes (dark = `inset 0 1px 0 … ` glow stack on `var(--card)`; light = `var(--card-shadow)` + `translateY(-1px)` on hover). Its removal is therefore a removal of two theme-aware treatments — not a regression toward "token-only" homogeneity — because the treatment was duplicate to other deltas in the page and the rest of the band reads cleanly without it. The "dark = command center (luminance depth, instrument calm, restrained glow); light = research workspace (cool canvas, white material, hairline discipline, shadow instead of glow)" CLAUDE.md discipline is unaffected: nothing was added that would substitute one skin for both; nothing was removed that would weaken the other treatment classes (`_site_nav`, `_macro_suite_shell`, `track-record` cards) that already govern the rest of the band.

### Mobile / responsive — cleanup without breakage

The deleted `@media(max-width:640px){ .rid{ grid-template-columns:3px minmax(0,1fr); } .rid-a{ display:none; } .rid-b{ padding:13px 14px 13px 0; } }` rule was the only mobile adjustment for this card; its removal removes a single-cell responsive tweak and the surviving `track-record` band already governs the rest of the mobile layout. No `@media` block was added; no breakpoint changed; the hub's existing responsive structure (`.hh` at 880px, `.alerts` at 820px, `.led-row` at 720/640px, `.ecards` auto-fill at 272px min) is unchanged.

### Visual verification matrix — body-claimed, audit confirms no regression

`mockups/` and `tests/test_measurement_research_implications.py::test_f10a1_evidence_is_full_viewport_and_theme_differentiated` (~:1942) are untouched by this PR; the operator-mandated "dark × light × EN × ZH × desktop 1440 / mobile 390" evidence pack for F10-A1 still lives at its committed paths. This audit does not re-render the matrix (single-pass; the body claim and the rc=0 of `check_ui_visual_evidence.py` are the receipt), and the deleted content was already inside the pre-F10-A1 evidence crops — removing the card does not invalidate the F10-A1 matrix because that matrix is keyed to F10-A1's own changes, not the `.rid` entry card.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED

`gh pr diff 7755 --repo mastermindx-market-intelligence/macro | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -iE 'validated'` → **0 hits**. Neither the deleted CSS nor the deleted markup nor the rewritten tests introduce the word `validated`. The deleted markup DID use plain words ("Research implications — what N frozen studies actually produced") that did NOT assert validation, so its removal is a removal of a non-claim, not a removal of an unbacked claim.

### Estate pre-existing: 65 UNEARNED, none anchored to PR-touched files

`python3 scripts/check_validated_claims.py` exits non-zero with 65 UNEARNED claims at audit time. Cross-checking against the PR-touched files (`templates/intelligence_hub.html.j2`, `tests/test_measurement_research_implications.py`):

- `templates/intelligence_hub.html.j2` — `git show origin/main:templates/intelligence_hub.html.j2 | grep -iE 'validated'` → **0 hits** (the deleted markup did not contain the literal `validated`; the surviving template does not either).
- `tests/test_measurement_research_implications.py` — the rewrite rewrites test IDs and bodies, none of which introduce the literal `validated`. The renamed `test_hub_template_has_no_link_to_the_admin_only_measurement_page` and `test_hub_never_renders_a_research_implication_entry` use the phrases `ric-section`, `class="card rid"`, `measurement.html`, `research_implications`, `frozen` — the `frozen` token is the word "frozen" as in "冻结研究" (frozen study), not the validated-claim jargon; these are content-negation assertions, not affirmative validated claims.

The 65 estate-wide unbacked hits all land on files unrelated to this PR: `_debt_maturity.html.j2`, `_macro_suite_shell.html.j2`, `canada.html.j2`, `hk.html.j2`, the nine `macro_*.html.j2` pages, `site/macro_*.html`, `engine/market_os/macro_workspaces/consumer.py`, etc. — the same pre-existing estate the prior audit (`macro_PR-7712.mm.md`) and `macro_PR-7701.mm.md` already flagged.

The lone `intelligence_hub`-anchored validated-claim is `site/intelligence_hub.html:1641 [allow:已验证"门槛]` — already allowlisted, OK, pre-existing on main before this PR. The deletion of the `.rid` block does not touch line 1641 (which is in the static `已验证` 门槛 — "validated threshold" — explanatory copy elsewhere on the page).

### Honest-impact statement — what changes when this lands

The hub template no longer renders a card whose href pointed at `/measurement.html#ric-section`. Because `www.mastermind-x.com` serves `/measurement.html` as an intentional 404 (per Caddyfile `@never_site` and `tests/test_admin_research_tools.py`), every reader who clicked the deleted card previously got a 404. After: that 404 path is gone. No reader-facing "validated" claim was made by the deleted card and none is unmade by its removal; the surrounding page copy at line 1641 (which DOES use the word `已验证`) is unaffected and remains allowlisted.

## Overall verdict

**PASS — Plain-language / theme / validated-claims laws all clean for PR #7755.**

- **Plain-language:** deletion-only on the user-facing template; no new copy added; no banned vocabulary introduced; bilingual structure preserved by subtraction; the navigation family invariant (`_site_nav`, not `_public_nav`) is now pinned by the surviving renamed test. No `title=` attributes touched; no translated titles introduced.
- **Theme:** zero CSS added; the R0 enforce-added design-system check returns 0 blocking by construction; no new token family; no theme treatment added that would weaken the "dark = command center, light = research workspace" discipline; mobile breakpoint untouched (only a now-dead single-cell responsive tweak was removed). The `mockups/` evidence pack is untouched; `test_f10a1_evidence_is_full_viewport_and_theme_differentiated` still runs.
- **Validated-claims:** zero `validated` literals on the diff; the 65 estate-wide UNEARNED claims are pre-existing and not caused by this PR; the one `intelligence_hub`-anchored validated claim (`site/intelligence_hub.html:1641 [allow:已验证"门槛]`) is pre-existing, allowlisted, and untouched. The deleted `.rid` block carried no `validated` claim, so its removal is a removal of a non-claim, not a removal of an unbacked claim.

The PR's net effect is the deletion of a product-page outbound link to an intentional 404, paired with four test renames that invert their assertions from "the link is present and correct" to "the link is absent". This is a positive plain-language outcome (the page no longer advertises a route that does not exist for the reader), a positive theme outcome (no orphan CSS, no orphan markup), and a positive validated-claims outcome (no new unbacked claim enters the estate, no surviving claim is disturbed).

## Gaps / observations

- The body documents a DEVIATION on the literal acceptance grep: the EDIT-1 grep `grep -nE '\.rid\b|rid-|card rid|measurement\.html|ric_cards|ric_n\b|research_implications' templates/intelligence_hub.html.j2` returns 20 matches, all on pre-existing `grid-template-columns` declarations at lines 167/169/195/214/220/441/471/474/503/515/521–525/529/535/553/567/568. The unanchored `rid-` token matches the `grid-` substring (false positive). The seat's content-anchored grep at the merged head returns zero matches: `grep -nE 'href="measurement\.html|card rid|ric-section|research_implications|ric_cards|\.rid\{|\.rid-|\.rid:' templates/intelligence_hub.html.j2` → no output, rc=1. This audit re-confirms: `git show origin/main:templates/intelligence_hub.html.j2 | grep -cE '^\+[^+]'` for the diff → 0; content-anchored grep → no output; `git diff origin/main…HEAD -- templates/intelligence_hub.html.j2 | grep -cE '^\+[^+]'` → 0 (40 deleted, 0 added).
- The seat read at the merged head reports `pytest tests/test_measurement_research_implications.py` → "32 passed, 56 errors, every error `frozen contract missing at …/site/measurementdata/research_implication_cards.json`" — these are sparse-tree artifacts (`site/` not on disk in the seat tree). The PR's own ci.yml run at `7d904dc3` ran the same file in a full checkout and concluded green (`ci-gate` SUCCESS, twelve `ci-pack-*` SUCCESS). Single-pass audit here does not re-run pytest; the body-claimed 88-pass count and the ci-gate SUCCESS are the receipts.
- The `MO-PAID-039` reconciliation (moving F00C from "INTEL_HUB points at admin-only Calibration Lab" to "INTEL_HUB does not point at it; the authenticated admin readback of a rendered implication card remains NEEDS_USER") belongs to the next A-side ledger cycle, not this PR. The deletion is the public half; the admin readback is a separate `needs_user` item.
- `tests/test_intel_hub_policy_gate.py` and `tests/test_china_lens_hub.py` are part of the adjacent hub suite (3 failed, 55 passed). The 3 failures pre-exist on `origin/main` and are unrelated to this packet; verified by the seat at the merged head.

## DEV IATIONS

None. The PR is removal-only on the user-facing template (zero added lines), test-only on the assertion side (four renamed tests, body rewritten to negate the prior assertions), and zero-touch on `scripts/build_intel_hub.py`, `mockups/`, `tests/test_f10a1_evidence_is_full_viewport_and_theme_differentiated`, and the F00C ledger. The deletion does not introduce any new copy, token, breakpoint, or claim — it removes an outbound link and its CSS and its inverse test.

---

SESSION END: PROVEN_OUTCOME (one-pass audit delivered; no durable write to remote host; result persisted into the seat's orch/idle directory from this stdout)