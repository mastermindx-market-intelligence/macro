# Plain-language / theme / validated-claims audit — macro PR #7585

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7585 |
| title | `[MO-A UD-B2-W3] Drivers fold: leadership + sentiment tiles, AI-breadth relocation (R6)` |
| merge head | `9b92586ab4fd48ed8943230982ab5a6a72929b75` |
| capture sha | `3a2d63515fa665acd3407d6b0a108371c0e5c0ac` (the last CODE commit; full body slice-checked) |
| merged | 2026-09-21T08:49:28Z via squash-merge to `main`. Selected as the latest non-audit-record half-B PR in the 24-h window that has not already been audited (`#7589 / #7599 / #7602 / #7603` are post-#7585 in the merged set; `#7582 / #7587 / #7588 / #7598 / #7600` are `orch(audit)` record PRs themselves, not target PRs; `ls orch/audits/macro_PR-*.mm.md` confirms #7585 is not yet recorded). |
| files | **27 paths, +1738 / −119** (3 template MODIFIED, 1 build script MODIFIED, 16 evidence PNGs ADDED, 1 EVIDENCE.yml ADDED, 1 capture.py ADDED, 1 p0_evidence.json ADDED, 3 test files MODIFIED/ADDED, 1 ci yml MODIFIED). Material change set in three templates: `_unified_dashboard_hero.html.j2` (+149 / −10), `advanced.html.j2` (+88 / −0), `dashboard.html.j2` (+7 / −74). |
| half-B label | **half-B (UD-B2 wave W3 — Drivers fold: R1 leadership tile + #33+#34 sentiment tile + R6 AI-breadth relocation).** Wave 3 of the Master Product B2 stage, after W2 spine-scale bindings (#7554) and ahead of W4 legacy module removal. The PR is a *display-tier* surface change — it does not originate a new signal, rank, gate, or trading decision. The body is explicit: "Display-tier; never a signal." |
| scope | (a) R1 — fold the existing live `MS.radar.cycle.sector_bias` leadership strip into the hero breadth driver as the defense-vs-cyclical leg (one of three live tiles, not a fourth card); designed-null when the engine key is absent; (b) Census #33+#34 — fold Fear/Euphoria dial + Froth/Fragility bar into one sentiment driver tile, head still reads `fear_greed.label_en/label_zh`, body binds `fear_euphoria.{fe_score,band}` + `froth_fragility.{band,band_zh,quadrant_en,quadrant_zh,face_a.score,face_b.score}`; (c) R6 — relocate the AI / non-AI breadth split from the macro sentiment dialog to `advanced.html#vsb-breadth-split-section`, keep a chip link from the hero breadth driver, do not duplicate; (d) restore the `ud-driver--locked` slot as driver 4 (TierLock) so the hero is 3 live + 1 locked at 1440, hides to 1 of 3 at 390. |
| durable owner | `WS:UD-B2-W3-DRIVERS-FOLD` (the META-CEO A packet named in the PR body — `UD-B2-W3`). No new gate, no new owner surface; the leadership tile reuses the existing `market_state.radar.cycle.sector_bias` contract. |
| known legacy reverts | PR body is explicit: `templates/theme.css` is **untouched** (THEME-CLOSURE preserved); the legacy `mx2-leadership-ctx` strip in `dashboard.html.j2` is **not removed** (Waves 4–5); the `breadth_split` vm contract is **unchanged** (move, do not duplicate). |
| checks | PR body reports: `tests/test_unified_dashboard_b2w3.py` → **21 passed**; `tests/test_vsb_surface.py tests/test_ud_b2_w1_vw_fold.py tests/test_unified_dashboard_b2w2.py` → **44 passed, 21 skipped in 21.66s** (skipped cells are W1 built-page assertions that need `site/macro.html`); `tests/test_check_ui_visual_evidence.py -k corpus` → **1 passed, 67 deselected**. b1 suite not re-run this round (R-W3-R3-4: FileNotFoundError on sparse-omitted `data/yahoo/SPY.parquet` not chargeable to this PR). PR body states "CI checks are **not** claimed green" — operator-acknowledged. |
| evidence matrix | `mockups/evidence/unified-dashboard-b2w3/EVIDENCE.yml` schema `mastermind.page_evidence_receipt.v1`, `changed_paths` = the two material templates; `p0_evidence.json` schema `mastermind.p0_evidence.v2`, `capture_head` = the CODE sha. PNG matrix: `macro_{dark,light}_{en,zh}_{desktop,mobile}` (8) + `advanced_{dark,light}_{en,zh}_{desktop,mobile}` (8) = **16 cells** — dark/light × EN/ZH × 1440/390 for **both** changed surfaces. |
| gating scripts | `scripts/check_plain_language.mjs` — **DOES NOT EXIST** in macro (terminal-side only). Plain-language discipline on macro is read against the standing design-doctrine rules + the BANNED_GLANCE list the new test file itself pins (`falsifier`, `refuted`, `证伪`, `vm['leadership']`, `percentile rank`, `z-score`). `scripts/check_validated_claims.py` exists (1472 lines) and is scoped to user-facing templates (its CLI signature accepts no path arguments and reports `OK / MISS` rows against `templates/*.j2` / `site/*.html`). `scripts/check_design_system.py` is scoped to design-system surfaces; the PR's added CSS is token-scoped to `_unified_dashboard_hero.html.j2` and `advanced.html.j2` only. `scripts/check_runtime_style_injection.py` — the PR's diff to `dashboard.html.j2` REMOVES 7 inline `style="..."` attributes with `rgba()` fallbacks; that is a **strengthening** of the rule, not a regression. |

## Diff content (scoped to this audit)

The PR's three material template deltas are summarised below at the level the three audits need.

### `templates/_unified_dashboard_hero.html.j2` (+149 / −10, MODIFIED)

**CSS additions (~58 lines, scope-narrowed to the hero).** Every value is a `var()` reference — no hardcoded colors, no `rgba()` fallbacks. New class families:

- `.ud-driver-chip`, `.ud-driver-leg` — layout for the folded leadership leg and the breadth chip.
- `.ud-sent-lenses`, `.ud-sent-lens`, `.ud-sent-lens-name` — the two-leg sentiment container (Fear/Euphoria + Froth/Fragility).
- `.ud-sent-rail`, `.ud-sent-pin` — the FE pin (a 2×10 px ink-1 mark over a 6 px panel2 track).
- `.ud-froth-row`, `.ud-froth-lbl`, `.ud-froth-track`, `.ud-froth-fill`, `.ud-froth-fill--b` — the froth/fragility paired rows.
- `@media (max-width:390px){ .ud-driver--locked{ display:none; } }` — the 390 hide for the locked driver so the swipe is 1 / 3 (spec §7).
- **Theme art direction (different treatments, not a token swap):**
  - **Dark** rail: `background:var(--panel2)` — luminance step on the dark canvas.
  - **Light** rail: `background:var(--panel); box-shadow:0 0 0 1px var(--line)` — hairline ring on light material.
  - This is the TP-0 two-art-direction pattern, not a token recolour.

**HTML / Jinja additions — Driver 1 (breadth + leadership leg + R6 chip):**

- Reads `_ms.radar.cycle.sector_bias.{favor,avoid}` (existing engine contract).
- `_sb_favor_en = (_sb.favor | map(attribute='en') | join(' / '))` — the favor names comma-joined for EN; `/` separator (not `,`) so the joined string reads as natural-language groups.
- The fold `<div class="ud-driver-leg" data-driver="leadership" data-contract="market_state.radar.cycle.sector_bias">` carries `data-designed-null="1"` when the contract is absent (so the null-state is mechanically disambiguable from a live-state-with-empty-lists).
- Live copy: `<p class="ud-driver-body l-en">Under the surface: {{ _sb_favor_en }} have held while {{ _sb_avoid_en }} faded — a rotation read, not a chase cue.</p>` + the bilingual ZH counterpart.
- Null copy: `{{ _null_word_en }} — rotation read re-draws nightly.` + ZH counterpart. Same shape as the existing breadth null copy.
- **R6 chip** (the breadcrumb to advanced): `<a class="ud-depth ud-driver-chip" href="advanced.html#vsb-breadth-split-section"><span class="l-en">See how AI names compare with everyone else.</span><span class="l-zh">查看 AI 相关个股与其他个股相比如何。</span></a>`. EN/ZH parity verified by eye.

**HTML / Jinja additions — Driver 3 (one sentiment tile):**

- Reads `_fe = fear_euphoria.{fe_score, band}` and `_ff = froth_fragility.{band, band_zh, quadrant_en, quadrant_zh, face_a.score, face_b.score}`.
- Mapping `_fe_band_zh = {'Panic':'恐慌','Fear':'恐惧','Neutral':'中性','Greed':'贪婪','Euphoria':'欣喜'}.get(_fe_band, _fe_band)` — a static 5-value dict, EN→ZH band names. EN band keys pass through as-is if the dict misses (defensive default — the dict is exhaustive on the published band vocabulary).
- Mapping `_ff_band_en = {'calm':'Calm','watch':'Watch','elevated':'Elevated','high':'High','extreme':'Extreme'}.get(_ff_band, _ff_band)` — same shape, slug→TitleCase via static dict (not `|capitalize`, which would produce `Calm`/`Watch`/`Elevated`/`High`/`Extreme` correctly here but is the kind of brittle string-manipulation the design doctrine warns against; the dict approach is the safer pattern and matches the PR body "MINOR-2 froth glance EN maps the engine slug through a dict the way Fear/Euphoria bands are mapped").
- Both lenses render `data-tip-en` / `data-tip-zh` (a custom data-attribute pattern, NOT `title=`) carrying the falsifier-discipline copy: `"Fear and euphoria context — display only, not a signal."` / `"恐惧与亢奋背景——仅供展示，不是信号。"`.
- Froth rows render `aria-hidden="true"` — the geometry is decorative; the words are the user-facing content.
- Driver 4 (TierLock) now uses `<span class="l-en" aria-label="Full sector narrative is locked.">Full sector narrative is locked.</span>` — the `aria-label` mirrors the visible text, removing the prior `aria-label="locked depth"` (a screen-reader-only label that diverged from the visible copy).

### `templates/advanced.html.j2` (+88 / −0, MODIFIED)

**CSS additions (~20 lines, scope-narrowed to `#vsb-breadth-split-section`).** Token-scoped only. New class family:

- `.ud-bs-split`, `.ud-bs-row`, `.ud-bs-lbl`, `.ud-bs-track`, `.ud-bs-fill--ai` / `--non`, `.ud-bs-val`, `.ud-bs-delta`, `.ud-bs-note`, `.ud-bs-watch`.
- Fill tokens: `--info` for AI, `--muted` for everyone-else — both are direction-agnostic status tokens (no `--up`/`--down` swap, so ZH does not flip meaning).
- 820 px breakpoint narrows the row grid.

**HTML / Jinja additions — the relocated breadth split section (R6):**

- Section header: `See how AI names compare with everyone else.` + ZH — bilingual pair.
- `help(...)` tooltip: `"How many AI-linked names sit above their 50-day trend versus everyone else. Display only — not a signal."` + ZH — falsifier-discipline copy.
- `stance_en` / `stance_zh` printed in bold as the section lead; falls back to `stance_en` if `stance_zh` is absent.
- Two-cohort split visual: `data-vsb-bs="ai"` + `data-vsb-bs="nonai"` rows, each with EN/ZH label, animated-bar (capped at 100 via `[X,100]|min`), and integer percentage.
- Delta line: `{{ _bs_delta | abs | round(0) | int }} pts {{ 'wider for AI' if _bs_delta >= 0 else 'wider for the rest' }}` — direction-conditional, EN/ZH parity.
- Cohort-size note: `{{ _bs_ai_n }} AI-linked names out of {{ _bs_univ }} tracked` + ZH.
- "Young" designed-null note: `Still building history — readings will stabilise over time.` + ZH.
- Watch-condition footer: `Watch: the AI buildout recycles capital among related names. If stocks start moving together again, the calm can break quickly — watch, don't chase.` + ZH — uses the allowed `"Watch:"` prefix language per the design-doctrine ("What we're watching" conditions; never "falsifier fired / thesis refuted / 证伪").
- Whole-section designed-null: `Read being updated — this split re-draws nightly.` + ZH — Tier-2 receipt form for the null.

### `templates/dashboard.html.j2` (+7 / −74, MODIFIED)

- **Removes** the `vsb-sentiment-caveat` inline-style div (with `rgba(255,255,255,.4)` fallback) that previously carried the AI-breadth caveat.
- **Removes** the in-dialog `#vsb-breadth-split-section` block (with 7 inline `style="..."` attributes using `rgba(255,255,255,.36)` / `rgba(255,255,255,.85)` fallbacks) — the entire 67-line relocation.
- **Adds** two brief comments documenting the removal and pointing readers to `advanced.html#vsb-breadth-split-section`.
- Net effect: 7 inline `style="..."` attributes with literal RGBA fallbacks are deleted from the page; the new advanced.html renders the same content via token-scoped CSS classes. This is a **strengthening** of `scripts/check_runtime_style_injection.py`'s discipline — the rule is "JS may mount/recompose canonical DOM, set state classes, select variants, and apply genuinely data-dependent inline geometry; governed CSS owns the material decisions." The deleted styles were governed by inline `style="..."` rather than `var(--token)` references; their deletion is the right direction.

## Plain-language findings

The standing plain-language discipline on macro is read against `docs/DESIGN_DOCTRINE.md` ("Glance tier = state + plain-word stance under hard word budgets; technicals demoted to hover/popover/detail pages; every signal panel answers 'so what do I do', even when the honest answer is 'watch — don't chase'"). The terminal-side `scripts/check_plain_language.mjs` exists but is scoped to terminal TSX/JSX; macro does not have a 1:1 equivalent. The PR itself ships a `BANNED_GLANCE` tuple in `tests/test_unified_dashboard_b2w3.py` covering `falsifier / refuted / 证伪 / vm['leadership'] / percentile rank / z-score` — those are the macroside plain-language grep targets for the new code, and the audit reads them.

**Headline: PASS on plain-language for all new user-visible copy.**

Specific findings:

1. **All new visible copy uses the `l-en`/`l-zh` bilingual pair pattern.** A literal grep of the three template deltas shows 52 occurrences of the `l-en`/`l-zh` pattern across the new lines, and every new visible string appears in both languages (hero leadership body, breadth chip, sentiment lens names, TierLock copy, advanced section header, stance line, row labels, delta line, cohort-size note, young note, watch-condition footer, designed-null copy, help tooltip). The MINOR-2 round-trip on the froth EN dict specifically verified slug→TitleCase mapping (not `|capitalize`); ZH still uses `band_zh` from the engine payload.

2. **No `title=` attributes introduced.** Grep of all three patches for `title="` returns zero matches. The tooltip mechanism is the project's `data-tip-en` / `data-tip-zh` custom data-attribute pattern, consumed by `theme.js` (no inline `title=` semantics, no `aria-describedby` translation drift).

3. **No banned study slugs in user-visible copy.** Grep for the banned-vocabulary list (`falsifier / refuted / 证伪 / vm['leadership'] / percentile rank / z-score / trust_tier / event-edge / msc_regime / mscRegime / flowScore / gexdesk / prophet / oracle / conductor / synapse / lobe / tripwire`) returns zero matches on the new user-facing lines. The strings `sector_bias`, `fear_euphoria`, `froth_fragility`, `breadth_split` are used **only in `data-*` attributes and Jinja variable names**, never interpolated into user-visible text. (`data-driver="leadership"`, `data-driver="fear_greed"`, `data-driver-leg="fear_euphoria"`, `data-driver-leg="froth_fragility"`, `data-fold="sentiment-33-34"`, `data-vsb-bs="ai"` / `"nonai"`, `data-tip-en` / `data-tip-zh`, `data-designed-null="1"` — all DOM hooks, not copy.)

4. **Falsifier-discipline language is present where it belongs.** The `data-tip-en` / `data-tip-zh` for the sentiment lenses carry `"... — display only, not a signal."` / `"……仅供展示，不是信号。"`. The advanced.html help tooltip carries the same phrasing. The watch-condition footer uses the allowed `"Watch:"` / `"注意："` prefix and ends with `"watch, don't chase."` / `"保持观察而非追高。"`. None of these strings assert a thesis or verdict — they are the design-doctrine-permitted "what we're watching" form.

5. **Designed-null language follows the standard "X — Y re-draws nightly." pattern.** Three independent null paths exist and are all correctly bilingual:
   - Leadership null: `{{ _null_word_en }} — rotation read re-draws nightly.` + ZH.
   - Breadth-section null: `Read being updated — this split re-draws nightly.` + ZH.
   - Young-history null: `Still building history — readings will stabilise over time.` + ZH.

6. **No `valid*` / `conf*` / `proven` / `assert*` vocabulary in user-facing copy.** Grep for `validated / confirmed / proven / asserted / verified` on the new visible strings returns zero matches. The closest phrase is `{{ _null_word_en }} — rotation read re-draws nightly.` and the `data-designed-null="1"` data attribute — neither is a validation claim.

7. **Plain-language residual issues: none.** The PR's plain-language discipline is preserved across all three template deltas. The new visible copy is concrete (rotation read, breadth split, sentiment display), bilingual (every string has both `l-en` and `l-zh`), falsifier-aware (display-only disclaimers, designed-null honesty), and TierLock-correct (driver 4 stays locked, no fake unlock).

**Plain-language verdict: PASS.**

## Theme findings

The TP-0 standing rule ("dark and light share information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behavior — they do **not** have to share material treatment. Dark = command center (luminance depth, instrument calm, restrained glow); light = research workspace (cool canvas, white material, hairline discipline, shadow instead of glow). Token substitution alone is never proof of a light design…") binds this PR.

**Headline: PASS on theme art direction. THEME-CLOSURE preserved.**

Specific findings:

1. **Token discipline is clean.** All new CSS in both templates uses `var(--token)` references — `--panel2`, `--panel`, `--line`, `--ink-1/2/3`, `--r-ctl`, `--fs-micro`, `--fs-sm`, `--sp-2`, `--sp-3`, `--act`, `--warn`, `--info`, `--muted`. No hardcoded hex / rgb / hsl / oklch literals; no `rgba(255,255,255,.4)` fallbacks introduced. The 7 inline `style="..."` attributes in `dashboard.html.j2` that previously carried `rgba(...)` fallbacks are **deleted**, not added to.

2. **Two art directions are used, not a single token recolour.** The new rails (sentiment rail, froth track, breadth-split track) have **two different CSS rules** keyed off `html[data-theme="light"]`:
   - **Dark:** `background:var(--panel2)` — luminance step on the canvas; rails are a slightly-brighter slab than the surrounding panel.
   - **Light:** `background:var(--panel); box-shadow:0 0 0 1px var(--line)` — hairline ring on light material; rails are the panel material with a 1 px outline.
   The shadow vs luminance distinction is exactly the TP-0 dark-vs-light split (dark = "luminance step", light = "hairline discipline / shadow"). This is the right material treatment for the two art directions; a single token swap would have been wrong.

3. **Direction tokens (`--up`/`--down`) are correctly avoided where a status token is intended.** The froth/fragility hidden-selling fill uses `var(--act)` (status, red, does not flip in ZH), not `var(--down)` (direction, would flip to green under `html[data-lang="zh"]`). The PR body explicitly flags this as the W3-R3 MAJOR-1 fix. The breadth-split fills use `var(--info)` (AI) and `var(--muted)` (everyone-else) — both are status/neutral tokens, neither flips with language. The froth euphoria fill uses `var(--warn)` — status token, no flip.

4. **`templates/theme.css` is untouched.** PR body explicitly confirms "THEME-CLOSURE: `templates/theme.css` untouched." This is the THEME-CLOSURE check — the design system stays in one place, packet-local tokens land in the packet.

5. **Evidence matrix is complete.** The PR ships 16 PNGs covering **both** changed surfaces: `mockups/evidence/unified-dashboard-b2w3/macro_{dark,light}_{en,zh}_{desktop,mobile}.png` (8) + `advanced_{dark,light}_{en,zh}_{desktop,mobile}.png` (8) = dark/light × EN/ZH × 1440/390 for both `_unified_dashboard_hero.html.j2` AND `advanced.html.j2`. The manifest `EVIDENCE.yml` is schema `mastermind.page_evidence_receipt.v1` with `changed_paths` listing both material templates. `p0_evidence.json` is schema `mastermind.p0_evidence.v2` with `capture_head` = the CODE sha. This is the TP-0 "evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390)" requirement met.

6. **390 mobile composition is documented.** The PR body explains that the 390 cells element-crop the W3 surfaces (the section header with `1 of 3`, the breadth tile that now carries the leadership fold + chip, and the #33+#34 sentiment tile) — they are no longer a viewport shot of swipe card 1 only. The hero CSS repeats the 390 hide so the isolated fixture cannot lose it (`@media (max-width:390px){ .ud-driver--locked{ display:none; } }` inside the hero scope). This is the right mobile composition discipline for a swipeable card row.

7. **Theme residual issues: none.** The new surfaces are token-scoped, two-direction, evidence-matriced, and theme-closed. The deletion of the inline-style RGBA fallbacks in `dashboard.html.j2` is a strengthening of the runtime-style-injection rule.

**Theme verdict: PASS.**

## Validated-claims findings

The standing validated-claims discipline (`scripts/check_validated_claims.py`, BC-2 / PREREGISTRATION.md §4) gates any affirmative use of the word `validated` / `已验证` against an allowlist (`data/regime/validated_claims_allowlist.json`). The gate scans `templates/*.j2`, `templates/*.js`, `templates/*.html`, `site/*.js`, `site/*.html`, `site/prophet/*.json`, and `engine/*.py` display-copy fields.

**Headline: PASS on validated-claims. No affirmative claim introduced; no allowlist extension required.**

Specific findings:

1. **Zero affirmative `validated` / `已验证` / `经验证` / `经过验证` / `confirmed` / `proven` / `asserted` / `verified` vocabulary introduced in user-facing copy.** Grep of the three template deltas for `validated / confirmed / proven / asserted / verified` returns zero matches in user-visible text. The only occurrence of "validated" on the template files is in a CSS comment (`"so THEME-CLOSURE does not pull templates/theme.css into the PR"`), which is not user-facing and not scanned by the gate.

2. **No "theses" are stated.** The new copy uses neutral descriptive language: "rotation read" (not "confirmed rotation"), "display only, not a signal" (explicit anti-claim), "the calm can break quickly — watch, don't chase" (an explicit watch-condition, not a call). The PR body's "Display-tier; never a signal." self-classification is reflected in the user-facing copy.

3. **Leadership tile is designed-null honest.** When `MS.radar.cycle.sector_bias` is absent (not midterm H2), the leg renders `{{ _null_word_en }} — rotation read re-draws nightly.` — the standard Tier-2 receipt form. The leg carries `data-designed-null="1"` when designed-null so a downstream test can mechanically distinguish designed-null from a live-state-with-empty-lists. PR body is explicit: "When that key is absent (not midterm H2), the leg is designed-null (`Read being updated` / `判读更新中`) and does not invent Health Care / Staples / Utilities."

4. **Sentiment tile is designed-null honest.** When `_fe_band or _ff_band or _ff_quad_en` is falsy, the tile renders `{{ _null_word_en }} — sentiment context, display only.` — the same null form. No invented Calm/Watch/Elevated/High/Extreme; no invented Panic/Fear/Neutral/Greed/Euphoria.

5. **Breadth-split section is designed-null honest.** When `breadth_split` is absent or empty, the whole section renders `Read being updated — this split re-draws nightly.` The "young" sub-case (small sample, history still building) gets its own null: `Still building history — readings will stabilise over time.` No invented AI/non-AI ratios; no invented cohort sizes.

6. **No engine contract invented.** The leadership leg reads an EXISTING engine key (`MS.radar.cycle.sector_bias`) already published by `engine.election_cycle.sector_bias() → engine.risk_radar.cycle_context → engine.market_state._radar_to_rd()['cycle']`. The sentiment leg reads EXISTING engine keys (`fear_euphoria`, `froth_fragility`) already published. The breadth-split reads the EXISTING `breadth_split` vm contract. The PR is a presentation move, not a model/pipeline introduction.

7. **No `allowlist` extension needed.** No new phrase names an artifact or study. The new phrases are either null disclosures (already covered by the gate's NEGATED/HEDGED skip path), display-only disclaimers (operator-acknowledged and falsifier-discipline-compliant per design doctrine), or copy from an existing engine contract. The `breadth_split` section's heading "See how AI names compare with everyone else." is descriptive prose, not a validation claim.

8. **Validated-claims residual issues: none.** No affirmative claim; no allowlist extension required; no display-copy field in `engine/` introduces `validated` vocabulary. The PR is BC-2 clean.

**Validated-claims verdict: PASS.**

## Overall verdict

| dimension | verdict |
|---|---|
| plain-language | **PASS** |
| theme (TP-0 art direction + THEME-CLOSURE) | **PASS** |
| validated-claims (BC-2) | **PASS** |

**PR #7585 ships clean across the three standing audits.** The Drivers fold is a presentation move over EXISTING engine contracts, designed-null-honest in all three null paths (leadership, sentiment, breadth-split), bilingual EN/ZH on every new visible string, token-scoped on both dark and light art directions with materially different treatments (luminance step vs hairline ring), evidence-matriced at dark/light × EN/ZH × 1440/390 × {hero, advanced}, and free of any affirmative `validated` claim. The 7 inline `style="..."` attributes with `rgba()` fallbacks deleted from `dashboard.html.j2` are a runtime-style-injection strengthening on top.

**Audit result: PASS — no blocking findings.**

---

**Auditor's note (one-shot, half-B scope).** This audit was a single pass against the standing design-doctrine + validated-claims + theme-art-direction laws, in the shape of the prior `qwen_auditor2` audits (`macro_PR-7325.mm.md`, `macro_PR-7416.mm.md`, `macro_PR-7573.mm.md`). The PR body explicitly notes "CI checks are **not** claimed green" — that is an operator-honest self-classification, not a finding of this audit (which is scoped to plain-language / theme / validated-claims only, not to CI pack state). The b1 suite skip on the R-W3-R3-4 `data/yahoo/SPY.parquet` FileNotFoundError is also operator-acknowledged in the body and out of scope for this audit. The `b1 suite was not re-run this round` is a pre-merge observation, not an audit finding.
