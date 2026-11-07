---
audit_id: macro_PR-8030
audit_date: 2026-09-26
pr: 8030
pr_title: "[MO-A] RIC F3 W2: trailing publication-lag tolerance — yield momentum measured at the last captured row (fixed_grid_origin.v4)"
repo: mastermindx-market-intelligence/macro
merged_at: 2026-09-25T17:32:05Z
head_sha: 15b0ce517ec1da22b8ab1c647a2fb28e2deaada7
merge_commit: 3f4b572f9ff6d67cc5974cc107e2da34a8a43b30
half_b_class: engine-half-B (data-wire + display-tier; `display_only: True`, `authority: False`; no template/CSS surface in this PR — W3 consumer wiring explicitly OUT of scope)
auditor: qwen_auditor2-equivalent (idle audit pass)
audit_mode: REMOTE USEFUL-IDLE (one pass, no retries, recorded disk-only)
---

## PR metadata

- **Number / title:** #8030 — `[MO-A] RIC F3 W2: trailing publication-lag tolerance — yield momentum measured at the last captured row (fixed_grid_origin.v4)`
- **Branch:** `claude/ric-f3-w2-trailing-lag-20260925`
- **Author:** `chriswong6031-creator` (Meta-CEO A seat, Claude5 session `2bb0da13`, per body)
- **Head SHA:** `15b0ce517ec1da22b8ab1c647a2fb28e2deaada7`
- **Merge commit:** `3f4b572f9ff6d67cc5974cc107e2da34a8a43b30`
- **Merged at:** 2026-09-25T17:32:05Z (≈24h+ before audit time 2026-09-26 — within the operator's "last 24 h" tolerance for an idle sweep, treating the audit-pass cutoff at 17:32Z on the merge day)
- **Capability:** Engine-side calculation. Treats a bounded trailing publication lag (1–3 weekday grid rows carried forward because FRED DGS* prints T+1) as an expected absence rather than withholding the whole path — momentum is measured at the **last captured source row** (`as_of`), not at the frame date. Wire-contract change: 4 new fields + version bump `fixed_grid_origin.v3 → v4`.
- **Owned files (3):**
  - `engine/yield_momentum.py` (+54 / −5) — adds `TRAILING_PUBLICATION_LAG_ROWS=3`, `LAG_BASIS='fred_next_business_day_publication_v1'`, 4 new wire fields (`trailing_publication_lag_rows`, `trailing_expected_absent_rows`, `lag_tolerance_rows`, `lag_basis`), a `measurement_origin` field, a trailing-lag qualification branch in `_series_read`, and one new caveat string. `display_only/authority/can_*` flags unchanged at `True/False/False/False/False`.
  - `tests/test_yield_momentum.py` (+132 / −7) — three pins moved deliberately (flat-frame carry, real-builder carry, 3-row carried tail → measured at the captured row); 9 new W2 tests (lag 1/2/3 measured at captured row, lag 4 stale + tolerance suffix, interior absence + lag withholds, holiday inside the run skipped, frame ending on holiday keeps W1 state (a), nonfinite trailing print, determinism + wire-key superset + v4 caveat).
  - `research/RIC_F3_W2_TRAILING_PUBLICATION_LAG_2026-09-25.md` (+41) — six-bake measurements table + W3 consumer-wiring notes.
- **Per-PR-body local test gate (run on the install set `pytest jinja2 pyyaml jsonschema==4.26.0 pillow`):**
  - `tests/test_yield_momentum.py` → 48 passed.
  - consumer suites (`test_rate_inflation_transmission`, `test_transmission_context`, `test_transmission_publish`, `test_credit_momentum`, `test_transmission_chains`) → 265 passed, 3 skipped.
  - `scripts/check_contract_delta.py --base origin/main` → 0 introduced, 2 inherited (base `d9d83b11`).
- **What is explicitly NOT in this PR (per body):** W3 consumer wiring (`engine/credit_momentum.py` interim T-bond block at ~:1125 / ~:1805), percentile denominator, holiday calendar, templates. **Templates = the actual user-facing display surface — out of scope by design.** Liveness proof = first nightly after merge showing non-null `velocity_bp.22d` on tenors whose lag is ≤ 3 (sentinel to be armed by the seat).
- **Scope signal:** RIC F3 W2 is half-B content for the rate-inflation-confirmation lane; this PR is its engine-side data plumbing. The audit-able user-facing surface is therefore zero in this PR — but the wire payload does carry **two display-bound strings** (a `null_reason` suffix and a new `caveats` entry) that W3 may surface in operator-tier `<details>` panels. That surface is what this audit grades.

## Plain-language findings

The PR introduces **two display-bound string mutations** (an appended `lag_suffix` to two existing `null_reason` lines and one new `caveats` entry). All other changes are wire keys, calculation logic, and constants — not user-facing.

### Display-bound string diffs

| # | Where | New/Modified | Operator-tier copy |
|---|---|---|---|
| 1 | `null_reason` (stale / nonfinite-latest path) | appended suffix | `; trailing publication lag N rows exceeds tolerance 3` (literal `f"; trailing publication lag {lag_rows} rows exceeds tolerance {TRAILING_PUBLICATION_LAG_ROWS}"`) |
| 2 | `null_reason` (interior unexpected absence path) | appended suffix | `; interior unexpected absence withholds the path` |
| 3 | `caveats` (wire payload) | new entry | `A trailing publication lag of at most 3 weekday rows is an expected absence: momentum is then measured and dated at the last captured source row (as_of), never at the frame date.` |

The pre-existing pinned prefixes (`'latest grid value is missing, nonfinite or carried; no new measured momentum'` and `'endpoint comparisons only; complete observed path not qualified'`) are preserved verbatim, so any downstream display wiring that greps the pinned prefix keeps working.

### Findings

- **Plain-language — "publication lag" (EN) is technical jargon, borderline for an operator-tier panel.** *"publication lag"* names a timing relationship between data source and baking clock — a plain-language paraphrase is *"the data hasn't been published yet"*. For an operator audience this is acceptable jargon (operators know FRED publication timing) but it is not the glance-tier word the design doctrine calls for. Severity: **MINOR** — only because this string is operator-tier and only appears in the withheld / stale branch, not in the happy-path `available` payload.
- **Plain-language — "tolerance" is technical but operational.** The string names a numeric threshold ("tolerance 3") so the operator can compare against the lag. Reasonable in an operator-tier context; not great as customer copy (would be — but this string is not customer copy, and W3 is out of scope). Severity: **MINOR** — same reasoning.
- **Plain-language — ZH parity:** the PR does NOT introduce ZH copies of the two `null_reason` suffixes. The existing `null_reason` literals in this code path are English-only (`'latest grid value is missing...'`, `'endpoint comparisons only...'`, `'requires 64 grid points for 63-interval velocity'`); this PR keeps them English-only. **Consistent with the surrounding engine convention** — `engine/yield_momentum.py` does not localise `null_reason` in W1 either, and ZH surfaces are produced downstream by the consumer / template layer. Severity: **PASS** — not a regression.
- **Plain-language — caveat leaks wire-key into prose.** The new caveat reads `... dated at the last captured source row (as_of), never at the frame date.` The parenthetical `(as_of)` is a wire-key name (`out['as_of']` in the same function). For an operator audience this is acceptable (operators read wire payloads), but it is a soft leak — the cleaner operator-tier phrasing is *"dated at the last captured source row (the `as_of` field)"* or simply *"dated at the last captured source row"*. Severity: **MINOR** — only because the W3 instructions explicitly tell the consumer to print `as_of` (not `frame_as_of`), so the parenthetical reinforces the correct consumer-side print name.
- **Plain-language — `measurement_origin` field is a wire-key name that may surface.** The wire adds `measurement_origin = 'last_captured_source_row' | 'latest_grid_row'`. The PR body's W3 instructions say consumer wiring should "treat `measurement_origin == 'latest_grid_row'` with `status 'stale'` as the honest empty state" — which is plain-language-correct, but the **key name itself** (`measurement_origin`) is internal jargon. Whether it surfaces as a label is a W3 template choice. **PASS at PR scope** — flag for W3 audit.
- **Plain-language — `lag_basis = 'fred_next_business_day_publication_v1'`** is a wire constant string with versioned naming. **Internal-only** — `lag_basis` is added to the wire payload, but only consumers that key off it will read it; the engine itself never displays it. PASS.
- **Plain-language — no banned vocabulary** (no "axis" coordinate metaphor, no "accepted print", no internal study names like `nh_contraction`, no raw slugs). The PR uses domain-natural terms ("publication lag", "carried-forward fill", "last captured source row") that are appropriate for the rate/CMT lane. PASS.
- **Plain-language — no falsifier / refutation language.** No "thesis refuted", no "falsifier fired", no `证伪`. The new caveat is descriptive, not verdict-shaped. PASS.
- **Plain-language — no call-to-action.** The display-bound strings describe data state; they do not tell the user to act. The existing caveat `Endpoint changes do not prove continuous deceleration or a market turn.` is preserved verbatim. PASS.
- **Glance-tier posture (out-of-PR but worth flagging):** this PR does NOT touch the glance tier — the rate-inflation transmission glance tier is wired by consumers. Once W3 lands, the rate-momentum tile will go from "null on every nightly" to "showing the captured-as_of value" — a real upgrade in information density. The change preserves the explicit disclaimer that the lane is `display_only: True`, `authority: False`, `can_score: False`, `can_size: False`, `can_trade: False`. PASS.

**Plain-language verdict: PASS with 3 MINOR (operator-tier jargon in `null_reason` suffix + caveat parenthetical)** — 0 blocking findings. The MINORs are operator-tier-only (never reach glance / customer surface) and the existing pinned-prefix convention preserves any downstream regex wiring. The `lag_basis` / `measurement_origin` wire-key surfaces are flagged for the W3 audit, not this one.

## Theme findings

The PR touches **zero CSS, zero design tokens, zero template chrome, and zero theme-aware structure**. The diff is pure Python engine code + tests + a research note.

- **No CSS rules added or modified.** ✓
- **No color, fill, stroke, shadow, glow, or any visual treatment added.** ✓
- **No `color-mix(...)`, no rgba, no opacity tricks, no inline `style.textContent` injection.** ✓
- **No design-token reference changes** (no `--panel2`, `--ink-3`, `--muted`, `--line`, `--band`, `--tone-*` references added or removed). ✓
- **No `data-band`, `data-reading-state`, `data-tone`, `data-frame`, or other theme-aware attribute hooks added.** ✓
- **No template family change.** The PR does not modify `templates/*.html.j2`, `templates/_site_nav.html.j2`, `templates/_public_nav.html.j2`, or any chrome / chrome-css / chrome-js file. ✓
- **No SVG, icon, or glyph asset change.** ✓
- **Dark/light parity:** no theme-conditional branching introduced; no `prefers-color-scheme` or `[data-theme]` query added. The wire payload is theme-agnostic by design. ✓
- **No theme-debt introduction** — and none can regress, because the PR does not touch any rendered surface.

**Theme verdict: PASS** — 0 blocking, 0 major, 0 minor findings. The PR is **theme-inert by construction** (engine + tests + a research note; the only rendered surface is what W3 builds downstream, which is out of scope). `scripts/check_design_system.py --mode enforce-added` is expected to report this PR as theme-silent.

## Validated-claims findings

- **No `validated` keyword in user-facing strings.** Grep over the new/modified literals in the diff:
  - `null_reason` suffixes: `trailing publication lag`, `exceeds tolerance`, `interior unexpected absence withholds the path` — no `validated` / `验证` / `已验证` / `经验证` / `经过验证` / `confirmed` / `verified` / `live` / `real-time` hits. ✓
  - new `caveats` entry: `A trailing publication lag of at most 3 weekday rows is an expected absence: momentum is then measured and dated at the last captured source row (as_of), never at the frame date.` — no banned phrase hits. ✓
  - other diff lines: code comments, type annotations, docstrings, test assertions — no user-facing surface. ✓
- **No `VALIDATED` prefix / stamp / banner / chip / badge introduced** anywhere. The PR adds no chip, no badge, no stamp. ✓
- **No instrument verdict surfaced as a market verdict.** The PR's display-bound strings describe **data state** (`null_reason` = "why this is withheld", `caveats` = "what this measure does not prove"). They are not verdicts; they are receipts. The pre-existing `Endpoint changes do not prove continuous deceleration or a market turn.` caveat is preserved verbatim. ✓
- **Authority flags unchanged.** The wire payload still reads `'display_only': True, 'authority': False, 'can_score': False, 'can_size': False, 'can_trade': False`. The PR is structurally barred from becoming a promotion-bearing surface; the new fields (`trailing_publication_lag_rows`, `trailing_expected_absent_rows`, `lag_tolerance_rows`, `lag_basis`, `measurement_origin`) are receipts about HOW the display value was measured, not claims about WHAT the value means. ✓
- **A7 (LLM never originates signals) — preserved.** The PR is pure data plumbing; no new scoring, no new ranking, no new escalation. The `turn_watch` field's thresholds, the `extreme_high_watch` enum, and the percentile denominator are **unchanged** (the test surface confirms `turn_watch == 'extreme_high_watch'` passes the same way it did pre-merge for matching inputs). ✓
- **Display-tier posture preserved.** The PR body explicitly: *"Display-tier only: no authority, sizing or trading semantics change."* Verified at the wire level (`display_only True`, `can_* False` for all four). ✓
- **No `validated_claims_allowlist.json` regression risk.** No new affirmative "validated" claim is introduced; the allowlist does not need to grow. The PR is in the validator's safe zone. ✓
- **Test surface — `check_validated_claims.py --selftest`:** no synthetic pattern from the selftest set is touched by this PR. ✓
- **W3 liveness risk flagged (out-of-PR but worth recording):** once W3 wires the consumer, downstream pages will start showing `velocity_bp.22d` numbers where they previously showed null. The wire payload's `caveats` correctly disclaims these values ("Endpoint changes do not prove continuous deceleration or a market turn" + the new lag caveat), and `display_only: True` keeps the value out of any authority lane. **A W3 audit should re-check that the consumer-tier template does NOT add a `Validated` chip / `Verified` badge / `已验证` stamp onto the new value** — that would be a promotion-bearing surface and would require either an `allowlist` entry or a `display_only` chip-shaped disclaimer. The PR does not introduce that risk; the W3 implementation could. Flag only.
- **Epistemics gauntlet.** Per house law, the gauntlet applies only at promotion to authority — and this PR is structurally barred from promotion (`display_only: True`, `can_score: False`). Display-tier builds ship display-tier freely; the gauntlet does not apply at this rung. PASS by design.

**Validated-claims verdict: PASS** — 0 blocking, 0 major, 0 minor findings. The PR adds zero new claim surface. The new `null_reason` suffix and the new `caveats` entry are receipts about data state, not claims about market state. Authority flags are unchanged and remain fail-closed against any future promotion.

## Overall verdict

**PASS** on all three dimensions (plain-language, theme, validated-claims).

This is an **engine-side data-wiring change** for the rate-inflation-confirmation lane. It treats FRED DGS*'s T+1 publication timing as a bounded expected absence (≤ 3 weekday grid rows) and measures momentum at the last captured source row rather than withholding the entire path. The change is structurally **display-tier only** — every authority flag remains `False` and the wire payload carries the proper `caveats` disclaimers.

- **Plain-language:** PASS with 3 operator-tier MINORs (jargon in `null_reason` suffix + caveat parenthetical `(as_of)`). All MINORs are scoped to operator-tier display surfaces that never reach the glance / customer tier. None are blocking.
- **Theme:** PASS — 0 findings. The PR is theme-inert by construction; no CSS / tokens / template chrome touched.
- **Validated-claims:** PASS — 0 findings. No `validated` keyword, no chip / badge / stamp, no authority flag changes, no promotion-bearing surface. A7 / display-tier / epistemics gauntlet all preserved.

**W3 carry-forward flag (out-of-PR scope, recorded for the W3 audit):** the consumer wiring in `engine/credit_momentum.py` should be checked for three things — (1) the operator-tier panel must not promote the new `velocity_bp.22d` value to a `Validated` / `Verified` chip or `已验证` stamp; (2) the printed `as_of` line should not echo the wire-key parenthetical from the new caveat (operator-readable "as of [date]" is cleaner than "as of [date] (as_of)"); (3) the consumer must print `as_of`, NOT `frame_as_of`, per the PR body's explicit instruction. None of these is this PR's fault — this PR does the engine-side work correctly.

**Heal durability:** the change is a calculated data path, not a byte-identify render. Drift cannot re-accumulate the way #8035's did — the engine logic itself either produces the new wire shape or it does not. No nightly-rebake risk.

**Not done because:** display-tier engine change; zero user-facing strings added on the customer's tier; no CSS / theme surface; no `validated` / chip / badge introduction. A PASS with three operator-tier MINORs and one W3 carry-forward flag is the right adjudication.
