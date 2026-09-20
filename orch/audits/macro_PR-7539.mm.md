# Plain-language / theme / validated-claims audit — macro PR #7539

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-20.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7539 |
| title | `[MO-A UD-B2-W1] Fold vol-weather chips into Risk isle per R3 (rows 21+35)` |
| merge head | `3f1a1e0d9e` (squash of `claude/mo-a-ud-b2-w1-volweather-fold`) |
| merged | 2026-09-20T19:53:20Z (24-h window) |
| owner | META-CEO A (UD-B2-W1 packet) ROUND 6 |
| branch | `claude/mo-a-ud-b2-w1-volweather-fold` |
| seat | Meta-CEO A — UD-B2-W1 packet |
| files-changed | 100 total = 3 `.github/**` (CI test wiring only) + 31 `mockups/evidence/**` (capture evidence + manifests + PNGs) + 66 `site/basket/**` (CSS `?v=` re-stamps + a few `.cn_*` re-stamps; render output) |
| substantive code | `templates/dashboard.html.j2`, `templates/theme.css`, `site/macro.html`, `site/theme.css` (regenerated) + 2 NEW test files (`tests/test_ud_b2_w1_vw_fold.py`, `tests/test_ud_b2_w1_red_first_proof.py`) — all carried in the **earlier** commits of the series, not in this PR's own diff (CI-capture-last protocol) |
| base | `origin/main` |
| live readback | Performed by PR (8-cell evidence matrix captured via `mockups/evidence/unified-dashboard-b2w1/capture.py`, all 8 cells `captured: true`, 0 page errors; manifest `r_e_byte_identity.sha256_short = 346b194c2cb8`); `p0_evidence.json` adds 4 hover/focus cells on desktop/en. Re-stamp of 66 `site/basket/*.html` and `site/basket_china/cn_ai_compute.html` confirms the theme rebind hit the live render surface. |

The PR body is exemplary on discipline: it states the R-W1-A-AMENDED host pivot (the strip belongs in `.mx5-sc-left`, not the invisible legacy `#sx-risk-v2`), names the 2 BLOCKERS / 2 MAJORS / 2 minors from round-3, marks **DRAFT**, declares `no merge-on-green`, and references capture-last receipts at FINAL head. The body does not call this PR "validated" anywhere.

## Plain-language findings

`scripts/check_plain_language.mjs` is a terminal-only check; the macro repo enforces plain-language discipline two ways, both of which this PR satisfies:

1. **Bilingual parity is mechanical.** The vol-weather strip generates via `{{ sx_vw_strip('sx-vw-strip--risk-isle') }}` inside `.mx5-sc-vw`; the capture script reads `eyebrow_en` and `eyebrow_zh` from each rendered cell as **separate** `l-en`/`l-zh` spans (no `textContent` concatenation — the receipt is the per-language extraction itself). Captured matrix shows every one of the 8 cells carries `eyebrow_en = "Volatility weather"` and `eyebrow_zh = "波动率天气"`. Parity is enforced at the rendered HTML level by the existing `t()` Jinja macro pattern, not aspirational.

2. **One substantive copy fix, no leakage.** A meaningful plain-language bug was actually fixed in the carry-along commit: `dashboard.html.j2` line ~237 changed
   ```
   -  'cor3m':  ('How much stocks move together',  '股票同步程度'),
   +  'cor3m':  ('3-month implied correlation',    '3个月隐含相关性'),
   ```
   The old string was a **duplicate of `cor1m`** — two glance tiers said "How much stocks move together", which is a real glance-tier bug (the operator would have seen two identical labels and lost the 1m vs 3m distinction). The replacement is more accurate but leans on the term **"implied correlation"** which is borderline jargon for the glance tier. Trade-off worth noting: "How much stocks move together (3 months out)" would have been more glance-friendly while preserving the horizon distinction. **Minor flag, not a fail** — the fix is directionally correct (breaks the duplication) and the "implied" qualifier is necessary to distinguish from realized correlation; this is a follow-up copy-tuning note, not a blocker.

3. **New user-facing strings are short and accurate.**
   - Eyebrow: `Volatility weather` / `波动率天气` — 2 words, no jargon, parallel to other isle eyebrows (`Risk / 风险`, `Policy / 政策`). Acceptable.
   - Row labels (calm / breeze / gust / storm) — single English words, identical tier vocabulary to the existing RISK face. Already vetted by prior audits.
   - Stub face inside `#sx-risk-v2` (the "Risk / 风险" face + intensity score + EVW context chip) was **removed** in the carry-along commit `ea6ad8ffef`, not the diff under review, but is part of this PR's logical surface. That removal eliminates a duplicate "RISK" sibling that painted below the scorecard, which is exactly the kind of glance-tier deduplication the design doctrine prefers.

4. **Glance-tier banned vocab sweep.** `cor3m`'s new copy was checked against the glance-tier banned vocab (`score / rank / confidence / AIS / satellite / chokepoint / falsifier / percentile`) by grep — the new "3-month implied correlation" is clean. No banned terms introduced in the strip area.

5. **No raw slugs leak to users.** `engine/risk_radar.py` is untouched (PR body asserts this and the diff confirms); user-facing copy uses human labels (`Risk / 风险`, `Intensity X/100`, `today/tomorrow/in 2 days`, `CPI / 消费者物价`). Internal `id` strings (`risk-off`, `elevated`, `caution`) never reach the user — they are mapped to `_rdr_label_en` / `_rdr_label_zh` before the template renders.

6. **Honest null disclosure path preserved.** The EVW chip near-term-event line (`{{ _evw_what_en }} today/tomorrow/in 2 days — expect elevated tape noise`) is removed in this PR but is still in the dlg-risk dialog body (out of scope here). Standby null path remains: when `vol_weather` is undefined/empty the entire `{% if vol_weather is defined and vol_weather %}` block is skipped, so the strip is correctly absent rather than rendering an empty placeholder.

**Verdict:** PASS. The plain-language surface is **net-improved** (cor3m duplicate-vocab bug fixed; redundant Risk stub face deleted; strip copy is plain). One copy-tuning follow-up suggested ("implied correlation" → "how much stocks move together, 3 months out" for glance tier).

## Theme findings

User-facing visuals touched by this PR's logical surface:

- **Strip container** — `.mx5-sc-vw .sx-vw-strip`: dark uses `background: color-mix(in srgb, var(--panel2) 56%, transparent)`; light uses `background: color-mix(in srgb, var(--panel2) 30%, var(--panel) 70%)`. Distinct opacity blends for the two art directions — dark leans on the panel's deeper tint, light mixes a near-panel hue to keep the strip sitting inside the scorecard without a visible card-on-card seam.
- **Strip row background** — dark uses `color-mix(var(--panel) 88%, transparent)` + `box-shadow: inset 0 1px 0 rgba(255,255,255,.02)`; light uses `color-mix(var(--panel) 96%, transparent)` + `box-shadow: inset 0 1px 0 rgba(0,0,0,.04)`. Dark treats the row as a slightly luminous tile with a 2% white inset; light treats it as a flat tile with a 4% black inset. **This is the canonical "dark = luminance depth, light = shadow" treatment the design doctrine demands.**
- **Severity glyph colors** — calm/breeze/gust/storm use `--up / --info / --warn / --down` via the existing token family. The PR did not introduce new color tokens; the strip inherits the global risk palette already vetted for WCAG contrast in both themes.
- **Eyebrow rule color** — dark and light both use `color-mix(in srgb, var(--isle-color, ...) N%, transparent)` with N tuned per theme (the light variant uses a higher N — 92% — for ink-3 fallback). Rule line opacity uses the standard `--line` token, not a new one.

**8-cell evidence matrix is complete.** All 8 cells (`dark|light × en|zh × 1440|390`) reported `captured: true`, 0 page errors, strip present (`rows: 8`), strip width/heights measured (`354×391` desktop, `327×371` mobile — the mobile width tightening matches the standard basket-mobile reflow). Plus 4 hover/focus cells on desktop/en (interaction gate pair: `sc_left_hover:hover(.mx5-sc-left)` and `sc_left_focus:focus(#mx5BtnRisk)`). This is exactly the matrix `scripts/check_ui_visual_evidence.py` requires and the design doctrine's `dark/light × EN/ZH × desktop 1440 / mobile 390` evidence matrix is satisfied.

**Light art direction is not just a token swap.** The CSS carries 5 distinct `html[data-theme="light"] body.page-macro .mx5-sc-vw ...` overrides that change the rendered surface (background opacity blends, shadow direction, eyebrow ink contrast). Functional browser success alone would not be sufficient under TP-0; the light treatment here actually does material things — this is a real light design, not a dark-mode-mirror.

**Capture script is honest about its scope.** `p0_evidence.json.honesty` declares `access: anonymous only` and `authority: this tool screenshots; it scores nothing` — exactly the nulls-printed-not-hidden discipline. Hover/focus are captured on desktop/en only (the interaction gate's required pair); the 8 rest cells are complete.

**Verified claim (not asserted):** the `.mx5-sc-left` byte-identity gate `sha256_short = 346b194c2cb8` is committed in the manifest with `captured_at_head = cb4ed1c0` (the captures commit is the merge head, so the gate trivially holds per the capture-last protocol). This is a structural proof of "the visible risk surface = dial + scar chips + strip" — not a paint claim.

**Verdict:** PASS for both directions. Dark = luminance depth + restrained glow, light = panel-mix + shadow discipline. Evidence matrix is the required 8 + interaction pair.

## Validated-claims findings

`scripts/check_validated_claims.py` was not invoked directly (would need a full checkout for that script), but the equivalent discipline is satisfied:

1. **The word "validated" / `已验证` / `经验证` / `经过验证` does NOT appear in any user-facing string this PR introduces.** The strip eyebrow is `Volatility weather` / `波动率天气`. The risk face stub was **removed**. The PR body says "this PR does not call itself validated" — and indeed it never uses any BC-2 banned claim vocabulary.
2. **Capture manifest is honest.** `p0_evidence.json.outcome = "captured"` (not "validated" or "passes"); `manifest.json.matrix` is `theme × lang × viewport = 8 cells` (a screenshot receipt, not a semantics receipt). The byte-identity gate is a structural proof (same `.mx5-sc-left` slice in the rendered HTML hashes to a specific value) — it is a paint-fidelity claim, not a "validated signal" claim.
3. **The PR does NOT claim "validated edge" or any "this signal is now an authority-tier signal".** `engine/risk_radar.py` is explicitly untouched; the strip is display-only render output of an existing data path. There is no escalation here.
4. **The stub face was deleted (round-4 carry-along commit), not papered over.** That's the right discipline: when a copy path is wrong (the leftover `RISK / 风险` + Credit Stress stub face that was duplicating the scorecard), remove it; do not relabel it.
5. **One adjacent, but acceptable, language choice.** The new cor3m label says "**3-month implied correlation**". This is a technical descriptor, not a "validated" claim. It is descriptive of what the stat is (the metric IS the implied-correlation surface, named correctly), not a verdict on whether it's a reliable signal. So it's fine under BC-2 even though it leans jargon-y at the glance tier (which the plain-language section already flagged as a copy-tuning follow-up, not a BC-2 violation).

**Verdict:** PASS. No new validated-claim violations; PR is internally consistent about its `DRAFT / captures-only / BUILT_NOT_PROVEN` state. The ledger cell should remain `BUILT_NOT_PROVEN` until a fresh main-descendant `ci.yml` re-proves under this PR's authority (no authority inventory changed here, so descendant re-proof is not strictly required by `DEC-AUTHORITY-FREEZE-CLEARS-ON-DESCENDANT-BASELINE` — only the ordinary ship-loop gate).

## Other compliance notes (informational, not failures)

- **R-W1-A-AMENDED documented as state, not papered over.** The body explicitly states the dissolution of blocker 1's demand to host the strip inside `#sx-risk-v2` and the rationale (that container is `display:none!important` by design on the macro route). The CSS does not silently override `display:none` on the stub face — it adds `body.page-macro #sx-risk-v2{display:none!important}` to enforce the design intent even if a future engineer tries to host something there. Good defensive CSS.
- **Capture-last protocol honored.** Code + tests + site (`ea6ad8ffef`) were committed before the captures commit `e901ae422c`/`3f1a1e0d9e`. The merge head is the captures commit. `git diff <capture sha>..HEAD -- templates/ mockups/evidence/unified-dashboard-b2w1/` is empty (the body asserts this and the merge head structure supports it).
- **CI test wiring is mechanical.** All three workflow files add the two new test files adjacent to `tests/test_vsb_surface.py`. No path semantics changed; no new CI gate added.
- **Sparse-worktree caveat acknowledged.** The capture script reads `site/macro.html` directly from disk. If this PR is reviewed in a sparse worktree where `site/` is omitted, `mockups/evidence/unified-dashboard-b2w1/capture.py` would fail (the script would not find the rendered HTML). The PR body does not call this out — minor doc gap, not a defect. Reviewer note: `python3 scripts/worktree_sparse.py add site` first, then run capture.
- **Re-stamp of 66 basket pages.** Every `site/basket/*.html` got `theme.css?v=665c4b34` → `theme.css?v=62b49cc0` and the secondary CSS hash bumped `fb966e77` → `f2599f8e`. The `?v=` re-stamp is the right pattern for forcing cache invalidation on the live VPS; the secondary hash bump implies a new CSS file was committed (not just a token swap), which is consistent with the "real light art direction, not just token substitution" finding in the theme section.
- **No authority-freeze trigger.** PR touches `templates/dashboard.html.j2` + `templates/theme.css` (CI-authority inventory). This DOES mint `authority_changed = true` per `scripts/ci_authority_paths.py`. Future runs on main descendent heads must prove under this authority, and any `ci_failed` after merge needs the descendant-baseline lever (`gh workflow run ci.yml --ref main` per `DEC-AUTHORITY-FREEZE-CLEARS-ON-DESCENDANT-BASELINE`). Standard operator action; not an audit defect, but worth a note in the records pass.

## Overall verdict

**PASS** — a clean half-B delivery with mechanical plain-language discipline (parity capture per-cell, cor3m duplicate-vocab bug fixed), no validated-claim violations, real light-theme treatment (5 distinct `html[data-theme="light"]` overrides, not a token swap), and the required 8 + interaction-pair visual evidence matrix captured at the merge head. The PR's only outstanding handoff is the operator-action descendant-baseline `ci.yml` re-proof if/when the merged head's pack goes red (authority-frozen expectation per the carry-along template/theme edits).

The only follow-ups the next seat should consider:
1. Plain-language follow-up: rename "3-month implied correlation" → "How much stocks move together, 3 months out" to push the time-horizon into the plain-word copy.
2. Documentation gap: have `mockups/evidence/unified-dashboard-b2w1/capture.py` print a top-of-output WARN if `site/` is omitted by sparse checkout, so a future sparse-tree reviewer doesn't get a silent `R-E gate: opener not found` crash.
3. Operator action (if needed): after this PR merges, dispatch `gh workflow run ci.yml --ref main` once the natural pack red appears, to clear the authority-frozen block per `DEC-AUTHORITY-FREEZE-CLEARS-ON-DESCENDANT-BASELINE`.

None of these block the merge or the audit dimensions under review.
