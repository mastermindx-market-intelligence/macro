# Plain-language / theme / validated-claims audit — macro PR #7574

Auditor: qwen_auditor2-style pass (one-shot, half-B scope, focused on the user-facing surface). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7574 |
| title | `China heatmap: exact observation truth and coherent refresh` |
| merged_at | 2026-09-22T02:54:26Z |
| head (semantic) | `33fd208dbd8b8f6bc49da7cf316a1547646db86b` (per PR body "Exact source identity" — verified locally via `git fetch origin pull/7574/head:pr-7574-head && git rev-parse pr-7574-head` → `cd96e21bb0a82fc7949ee5d758736e3c917a848f` is the **merge-commit head**; `33fd208dbd8b8f6bc49da7cf316a1547646db86b` is the **branch head**; both reachable on `origin/main` after fast-forward) |
| base | `main` |
| branch | `sol/china-heatmap-observation-refresh-20260921` |
| changed files | **14 files, +2264 / −42.** Surface relevant to this audit: `templates/market_heatmap.html.j2` (+12 / 0, MODIFIED — adds the per-card observation-coverage block), `templates/heatmap.js` (+293 / −14, MODIFIED), `site/heatmap.js` (+293 / −14, MODIFIED — paired plain-copy asset, byte-matched to template via `scripts/check_template_site_sync.py` per PR body *"ship the byte-identical `site/heatmap.js` mirror"*). Non-surface files: `engine/china_heatmap_observations.py` (+209 / 0, ADDED — pure observation contract), `engine/market_heatmap.py` (+30 / −9, MODIFIED — China-only integration), `.github/ci/legacy-jobs.yml` (+19 / −2), plus 9 test / fixture / harness files. |
| additions / deletions | 2264 / 42 (overall) — 598 / 28 (user-facing surface: 12 on the template + 293+293 on `templates/heatmap.js` and `site/heatmap.js`) |
| labels | none visible at fetch time; merge came in via the macro sweeper on the listed timestamp |
| scope collision | none. PR body explicitly bounds scope: *"The restored/canonical China dashboard design is preserved; this does not replace or redesign that surface."* The change is a data-correctness repair to the China heatmap observation contract + a coherence repair to the existing shared refresh owner — no new product surface, no new score, no new model/data authority, no new ranking, no new trade / promotional element, no redesigned UX. |
| precedent | local proof listed by author — `147 passed` (Python heatmap / mainland-calendar / page-gate / label / market-cap / observation suite), `24 passed` (contract-delta unit suite), `89 passed` (Node observation UI / coherent refresh / mutation / timeout / retry / downgrade tests against `templates/heatmap.js`), `89 passed` (the same suite against `site/heatmap.js`), `node --check`, `py_compile`, `git diff --check`, YAML parsing, template↔site sync (`99 pairs checked`). Real-input build: `1,702` tiles, `12` sectors, `1D coverage 1702/1702`, `3M coverage 1687/1702 (15 correctly unavailable)`, `1Y coverage 1656/1702 (46 correctly unavailable)`. Real-browser proof on `site/china_heatmap.html`: `1,702` desktop tiles + `1,702` mobile rows, dark/light theme transition, no horizontal overflow, zero page/heatmap console errors. The audit below re-runs and confirms against the standing plain-language / theme / validated-claims laws. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 100 --json number,title,mergedAt --jq …` against `git ls-tree origin/main -- orch/audits/` and the working-tree-untracked audit files (4 files: `macro_PR-7667`, `macro_PR-7687`, `macro_PR-7688`, `macro_PR-7701`), the most recent non-audit-recording merges before #7574 are: (a) **#7667** `Add compact China regime driver rail` — already audited via `orch/audits/macro_PR-7667.mm.md` (worktree-local untracked file); (b) **#7687** `fix(prophet): keep optional structural overlay from deadlocking B4` — engine-only, audited via `macro_PR-7687.mm.md`; (c) **#7688** `feat(prophet): own B4 session eligibility policy` — engine-only, audited via `macro_PR-7688.mm.md`; (d) **#7698** `docs(ric): RIC F3 production proof` — docs only, no user-facing surface; (e) **#7683 / #7666** `research(risk):` — evidence-only; (f) **#7679** `agentos:` — knowledge-plane only; (g) **#7678 / #7628 / #7621** `fix(ci):` — infra only; (h) **#7639 / #7637** `[MO-A heal]` design-governance deepen — infra only; (i) **#7662 / #7632 / #7623 / #7629 / #7610 / #7607 / #7603 / #7602 / #7600 / #7614 / #7619 / #7613 / #7618 / #7569 / #7571 / #7573 / #7577 / #7585 / #7589 / #7599** — already audited on `origin/main`. **#7574 is the only un-audited half-B PR in the last 24 h that has a real user-facing surface (the China heatmap and its companion observation-coverage chip)**. The engine / agentos / tests / fixture / harness dimensions are not user-facing copy and are out of scope for plain-language / theme / validated-claims law; the template + paired site copy + paired stylesheet are, and that is what this audit covers.

**Nature of change (one template, +12; two paired JS, +293 each):**

1. *Observation-coverage chip* (template lines ~134–144, paired site identical). A new `<div class="hx-bscope hm-observation-coverage" role="status">` block renders **only when** `summary.observation_coverage` is present (i.e., the China heatmap, which is the only payload that ships the new `china_heatmap_observations.v1` contract). Inside the block:
   - When interval coverage accounting is valid: `<span class="l-en">N / M names have observed endpoint pairs · K unavailable.</span><span class="l-zh">N / M 个标的具备有效区间行情 · K 个不可用。</span>`. The numbers are concrete (`interval.valid_count`, `interval.denominator`, `interval.missing_count`) — they describe the on-screen state, not an aspirational or aggregated claim.
   - When the accounting is missing or doesn't add up: `t('Observation coverage unavailable.', '观测覆盖率不可用。')` — the canonical Tier-2 receipt form: null disclosure in plain language, not a silent fall-through to "0 unavailable" or to a stale prior value.

2. *Coherence guard in `templates/heatmap.js` and `site/heatmap.js`* (`+293 / −14` each, byte-matched per PR body). The diff introduces `isChinaHeatmapUrl()`, `chinaDay()`, `chinaGeneration()`, `chinaRecord()`, `chinaNumber()`, `chinaCount()`, `validateChinaObservations()`, `validateChinaSnapshot()`. The validation guards are pure (no I/O, no DOM mutation, no global state writes) — they throw on contract mismatch and the surrounding refresh owner catches and discards the bad snapshot. No new user-facing copy; the failure path is silent (the existing `discardSnapshot()` returns the previous-snapshot fallback or an "Observation coverage unavailable." chip in the absence of any prior valid snapshot).

3. *Refresh owner hardening* (lens / `templates/heatmap.js` lines around the existing `_dataPromises[url]` owner). One in-flight request per URL, bounded fetch/JSON timeout, abort, retry, hidden-tab suppression. US / HK / Canada refresh semantics unchanged. No new user-facing copy.

4. *No new palette, no new font, no new CSS token, no new template file.* The `hm-observation-coverage` block reuses the existing `.hx-bscope` typography (the same class the broader-scope summary chip uses) and inherits `role="status"` (a pre-existing pattern across the site for live-updating bits that screen readers should announce on change).

## Diff content (scoped to this audit)

Three files, all user-facing template / paired site / paired JS surface. No new CSS, no new font, no new palette, no new global token, no new template file.

### `templates/market_heatmap.html.j2` (+12 / 0, MODIFIED)

#### Hunk 1 — observation-coverage chip (lines ~134–144)

```jinja
{%- if summary.observation_coverage %}
{%- set oc = summary.observation_coverage %}
{%- set interval = oc.timeframes.get(summary.tf) if oc.timeframes is mapping else none %}
<div class="hx-bscope hm-observation-coverage" role="status">
  {%- if interval and oc.basis == 'current_membership' and oc.membership_count is integer and interval.denominator is integer and interval.denominator > 0 and interval.valid_count is integer and interval.valid_count >= 0 and interval.missing_count is integer and interval.missing_count >= 0 and interval.denominator == oc.membership_count and interval.valid_count + interval.missing_count == interval.denominator %}
  <span class="l-en">{{ interval.valid_count }} / {{ interval.denominator }} names have observed endpoint pairs · {{ interval.missing_count }} unavailable.</span>
  <span class="l-zh">{{ interval.valid_count }} / {{ interval.denominator }} 个标的具备有效区间行情 · {{ interval.missing_count }} 个不可用。</span>
  {%- else %}
  {{ t('Observation coverage unavailable.', '观测覆盖率不可用。') }}
  {%- endif %}
</div>
{%- endif %}
```

Three structural facts to pin:

- **Visible only when `summary.observation_coverage` is present** (the new `china_heatmap_observations.v1` payload). The chip does not render on US / HK / Canada heatmaps (their payloads don't carry `observation_coverage`), so the new copy is scoped to the surface it describes.
- **Bilingual-by-construction** (`<span class="l-en">…</span><span class="l-zh">…</span>`). The pre-existing site-wide `l-en / l-zh` span convention is reused — no new bilingual mechanism, no inline ZH translation, no language switch required for the chip to display in both locales (CSS / `langchange` event hides the wrong-language half).
- **Concrete numbers, no aggregation language.** The visible text is `N / M names have observed endpoint pairs · K unavailable.` — `N`, `M`, `K` are payload-derived counts (`interval.valid_count`, `interval.denominator`, `interval.missing_count`), not a derived signal, not a synthesised score, not a normalised index.

The fallback branch renders `Observation coverage unavailable.` / `观测覆盖率不可用。` only when the accounting predicates fail. The predicates mirror `validateChinaObservations()` in `templates/heatmap.js` exactly: `valid_count + missing_count == denominator` and `denominator == oc.membership_count`. If the payload fails the JS-side guard, the JS-side `discardSnapshot()` discards the snapshot and the template never renders the chip in the first place — so the fallback branch is the second-tier receipt for payloads that pass the JS guard but still don't satisfy the template's render predicates (a contract-version skew, e.g.). This is the canonical "nulls printed, not hidden" shape.

### `templates/heatmap.js` (+293 / −14, MODIFIED)

The diff has three structural parts:

- **New `validateChinaObservations()` function** (~120 lines). Pure function: takes the payload, throws on contract mismatch, returns nothing. Checks every per-tile observation against the schema `china_heatmap_observations.v1`, the per-timeframe reference session endpoints, the `VALID / CURRENT_MISSING / CURRENT_INVALID / REFERENCE_MISSING / REFERENCE_INVALID / RETURN_INVALID` status enum, the membership denominator, and the `valid + missing == denominator` accounting invariant. The body is mathematical / regulatory: `Math.abs(c.fraction - counts[tf] / data.n_tiles) > 1e-12` rejects a coverage fraction that doesn't add up.
- **New `validateChinaSnapshot()` function** (~80 lines). Pure function: validates the top-level snapshot identity (`market == 'china'`, `map_type == 'stocks'`, `source == 'daily-close'`), date labels (`chinaDay(asof)`, `isFinite(chinaGeneration(generated_utc))`, `generated_utc.slice(0, 10) >= asof`), absence of client-state keys (`Object.keys(data).some(k => k.charAt(0) === '_')` — the existing snapshot contract reserves `_`-prefixed keys for client-injected state), tile accounting (`n_tiles == tiles.length`, all tickers unique and well-formed), timeframe / sector catalog uniqueness, default-tf presence in the catalog.
- **Coherence guard on the existing refresh owner** (~40 lines net). One in-flight request per URL (`_dataPromises[url]` reuse, already present), bounded fetch timeout (60 s default), JSON parse timeout, abort on URL change, retry-on-network-error with backoff, hidden-tab suppression (`document.visibilityState === 'hidden'` short-circuits). The US / HK / Canada branches are byte-for-byte unchanged per the diff hunks.

Net code added: ~240 lines of validation + ~50 lines of refresh-hardening. Net code removed: ~14 lines of the old "trust the payload" branch. All new code is **scoped to the China-only path** (guarded by `isChinaHeatmapUrl(url)`); US / HK / Canada refresh semantics are unchanged and the existing test suite continues to gate them.

### `site/heatmap.js` (+293 / −14, MODIFIED — paired plain-copy asset)

Identical diff to `templates/heatmap.js`. The standing `scripts/check_template_site_sync.py` guard refuses a PR if the paired plain-copy diverges (PR body: *"ship the byte-identical `site/heatmap.js` mirror"*). This audit does not re-run the byte-match (CI-guarded), only confirms the two diffs are parallel.

### `engine/china_heatmap_observations.py` (+209 / 0, ADDED)

A pure observation contract module. No I/O, no publication, no monitoring, no scheduling, no trade authority (per the module-level comment in the diff: *"Pure computation. No I/O, publication, monitoring, scheduling or trade authority."*). Reads the canonical mainland calendar + the canonical mainland tickers list, produces the `china_heatmap_observations.v1` payload that the JS-side `validateChinaObservations()` then validates. No user-facing copy in this file (no Jinja, no HTML, no template strings, no aria-labels, no t() calls).

### `engine/market_heatmap.py` (+30 / −9, MODIFIED)

Wires `china_heatmap_observations.v1` into the existing China heatmap payload. Removes the previous "substitute a prior valid interval" branch and the "fabricated zero on missing data" branch (per PR body's "Capability delta"). No new user-facing copy.

### Test files

`tests/china_heatmap_refresh_harness.cjs` (+44), `tests/test_china_heatmap_gate.py` (+41 / −3), `tests/test_china_heatmap_observation_refresh.cjs` (+47), `tests/test_china_heatmap_observations.py` (+184), `tests/test_china_heatmap_observations_ui.cjs` (+35), `tests/test_china_heatmap_refresh.cjs` (+149). 9 fixtures under `tests/fixtures/china_heatmap_refresh/`. Per PR body: `147 passed` Python, `24 passed` contract-delta unit suite, `89 passed` Node observation/refresh/mutation/timeout/retry/downgrade against `templates/heatmap.js`, `89 passed` against `site/heatmap.js`. None of the test files introduce user-facing copy.

## Plain-language findings

### 1.1 Pass — minimal, concrete, bilingual user-facing copy

The diff adds **four** new user-facing strings, all scoped to the China heatmap:

| Where | EN | ZH |
|---|---|---|
| Coverage chip (numbers) | `{{ N }} / {{ M }} names have observed endpoint pairs · {{ K }} unavailable.` | `{{ N }} / {{ M }} 个标的具备有效区间行情 · {{ K }} 个不可用。` |
| Coverage chip (null) | `Observation coverage unavailable.` | `观测覆盖率不可用。` |

Two observations:

- **Numbers are concrete and payload-derived.** `N`, `M`, `K` are `interval.valid_count`, `interval.denominator`, `interval.missing_count` respectively — they describe the on-screen state, not a normalised score, not a synthesised index, not a derivative. The format `N / M names … · K unavailable` is the canonical plain-language accounting form (valid count out of total, with the unavailable remainder named).
- **Null disclosure is plain-worded.** `Observation coverage unavailable.` / `观测覆盖率不可用。` is the standing Tier-2 receipt shape — not "0 unavailable", not "n/a", not a silent fall-through, not a stale prior value. This is the canonical "nulls printed, not hidden" form per the standing plain-language law.

No banned-glance / banned-tier vocabulary anywhere in the diff:

- 0 hits for "validated | 已验证 | 经验证 | 经过验证" in any user-facing position (`grep -ciE "validated|已验证|经验证|经过验证" /tmp/pr7574.diff | grep -v test | grep -v mockup | grep -v fixture` → 0; the two hits `test_ssr_observation_coverage_is_validated_and_bilingual` and `'query-string China URL is still identity-validated'` are test names, not UI strings).
- 0 hits for banned internal-organ slug (`prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, `brain`, `neural-web`, `state`, `regime`, `status`, `tier`, `verdict`, `classification`, `bucket`, `urgency`, `code`, `kind`, `category`, `slug`) in any user-facing position — `status` appears in `role="status"` (an ARIA attribute, not a visible string) and in the JavaScript function names (`chinaRecord(value)`, `chinaNumber(value)`, etc., not user-facing copy); `state` and `regime` do not appear; the manifest references to `prophet` are file paths under `mockups/evidence/prophet-p0b-zero-fouc/...` (already in `origin/main`, not introduced by this PR).
- 0 hits for "proved", "proven", "guaranteed", "certified", "ships", "active" (in the promotive sense), "alpha", "edge", "outperformance", "signal" (in the trade sense), "trade" (in the trade sense), "buy", "sell" in any user-visible fragment of the diff. The `controller.signal` hits are JavaScript object property names (an internal abort-controller signal), not visible strings.
- 0 hits for any falsifier / refutation vocabulary (`falsifier fired`, `thesis refuted`, `证伪`, `破灭`) in the diff — the PR is a data-correctness repair, not a thesis update.

### 1.2 Pass — bilingual parity preserved and extended

Pre-existing bilingual mechanisms preserved AND extended:

| EN | ZH |
|---|---|
| Broader scope chip: pre-existing `<div class="hx-bscope">` | (same `<div>` element, content inside is `t(..., ...)` bilingual) |
| **NEW** Coverage chip (numbers): `{{ N }} / {{ M }} names have observed endpoint pairs · {{ K }} unavailable.` | **NEW** `{{ N }} / {{ M }} 个标的具备有效区间行情 · {{ K }} 个不可用。` |
| **NEW** Coverage chip (null): `Observation coverage unavailable.` | **NEW** `观测覆盖率不可用。` |

Both pairs are real translations (`观测覆盖率不可用` is the canonical literal rendering of "observation coverage unavailable"; `N / M 个标的具备有效区间行情 · K 个不可用` is the canonical literal rendering of "N / M names have observed endpoint pairs · K unavailable" — `标的` is the canonical short rendering of `names` in finance / market-data ZH, `具备有效区间行情` is the canonical literal rendering of "have observed endpoint pairs", `不可用` is the canonical literal rendering of "unavailable"). `tests/test_bilingual_ui.py` (CI-guarded) will catch any inline EN-only render.

The chip is rendered only when `summary.observation_coverage` is present (China payload only) — no leakage to US / HK / Canada heatmaps.

### 1.3 Pass — null disclosure is the canonical form; no silent fall-throughs

The template's predicate is the second-tier null-receipt gate:

```
{%- if interval and oc.basis == 'current_membership' and oc.membership_count is integer and interval.denominator is integer and interval.denominator > 0 and interval.valid_count is integer and interval.valid_count >= 0 and interval.missing_count is integer and interval.missing_count >= 0 and interval.denominator == oc.membership_count and interval.valid_count + interval.missing_count == interval.denominator %}
```

— when the payload's accounting predicates all hold, the concrete-numbers chip renders; when any fails, `t('Observation coverage unavailable.', '观测覆盖率不可用。')` renders. There is no path that hides the chip, no path that renders a stale prior value, no path that fabricates a `0` on missing data. The JavaScript-side `validateChinaObservations()` throws on contract mismatch, and the surrounding `discardSnapshot()` returns the prior valid snapshot — so the user sees either a current-snapshot numbers chip, a prior-snapshot numbers chip (with the same wording), or the explicit "Observation coverage unavailable." chip. None of these three states is silent.

### 1.4 Pass — quiet-by-default; no copy or label claims a property the structural change doesn't deliver

The structural changes deliver exactly the properties the new copy claims:

- `N / M names have observed endpoint pairs · K unavailable.` only renders when `validateChinaObservations()` has passed AND the template's local predicates (which mirror the JS guard) hold — the numbers printed are the numbers validated.
- `Observation coverage unavailable.` renders when the accounting doesn't add up — the chip never claims a coverage that the JS guard would have rejected.
- The `role="status"` attribute means screen readers announce the chip on change — the structural `aria-live` contract is delivered by the pre-existing site-wide live-region mechanism (no new JS, no new polling, no `setInterval`).
- The `hm-observation-coverage` class is purely a hook for future per-page styling / targeting; it doesn't carry semantics beyond its name (which is descriptive, not a claim).

### 1.5 Pass — falsifier / refutation vocabulary correctly absent

No "falsifier fired / thesis refuted / 证伪 / 破灭" strings. The PR is a data-correctness repair, not a thesis update; the chip describes observed accounting, not a verdict on the underlying thesis.

### 1.6 Pass — no new internal-organ slug in visible strings

`prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier` appear in test names and in pre-existing file paths (`mockups/evidence/prophet-p0b-zero-fouc/...` is on `origin/main` before this PR), but **zero** appear in any user-facing string introduced by this PR.

## Theme findings

### 2.1 Pass — no new CSS, no new palette, no new font, no new token

The diff is **purely structural** for theme purposes. There is no new CSS file, no new `<style>` block, no new class definitions in the template. The new chip reuses the pre-existing `.hx-bscope` class (a pre-existing summary-chrome class on `origin/main` — verified by `grep -nE 'hx-bscope' templates/market_heatmap.html.j2 site/market_heatmap.html` → matches the existing broader-scope chip).

`.hm-observation-coverage` is a hook class only — it is **not styled** anywhere in the diff. It exists so future work can target the chip with per-page CSS if needed, without modifying the shared `.hx-bscope` rule. No new `--var` at root, no new palette hex, no new `font-family` declaration, no new `letter-spacing` value, no new breakpoint.

The `role="status"` ARIA attribute is an accessibility semantic, not a visual change.

### 2.2 Pass — explicit light / dark theme treatment is unchanged, no token swap

The PR body enumerates *"dark/light theme transition"* as a verified dimension of the browser proof. The chip is rendered inside the existing `.hx-bscope` chrome, which already has both dark (default) and light (`[data-theme="light"] .hx-bscope …`) treatments on `origin/main` (verified: `grep -nE '\[data-theme="light"\] .+hx-bscope' templates/theme.css site/theme.css` → matches both `templates/theme.css` and `site/theme.css`). The new chip inherits both treatments automatically — no token swap, no parallel palette, no new mechanism to maintain.

The PR is consistent with the standing theme law: dark and light share **information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law, and interaction behavior**. The new chip carries the same `N / M names have observed endpoint pairs · K unavailable.` text in both themes (only the colour/contrast of the surrounding `.hx-bscope` chrome differs). This is the canonical two-art-direction form — same content, different material, no parallel palette.

### 2.3 Pass — bilingual typography handling inherited

The chip inherits the pre-existing `[data-lang="zh"]` font stack / letter-spacing treatment that the surrounding `.hx-bscope` chrome already applies (verified by `grep -nE 'data-lang="zh"' templates/theme.css site/theme.css` → matches both files). The new ZH copy (`N / M 个标的具备有效区间行情 · K 个不可用。`) flows through the same CJK font stack and the same `letter-spacing:0` rule (the canonical CJK letter-spacing discipline). No new ZH-specific CSS rule needed; the pre-existing one covers it.

### 2.4 Pass — `prefers-reduced-motion` unaffected

The chip is static text. No animation, no transition, no transform. The existing `[data-theme] …` block already disables any motion on the surrounding `.hx-bscope` chrome under `prefers-reduced-motion: reduce`. No change required.

### 2.5 Pass — runtime-style-injection guard clean

`scripts/check_runtime_style_injection.py` is a no-arg scanner that walks the repo looking for `style.textContent = …` / `setAttribute('style', …)` / multi-kilobyte inline style payloads inside JS. PR body states the template↔site sync is clean (`99 pairs checked`). The diff contains:
- 12 lines of new Jinja in `templates/market_heatmap.html.j2` — no `style="…"` attributes, no inline `<script>` running JS, no inline CSS.
- 293 lines of new JS in `templates/heatmap.js` and `site/heatmap.js` — purely validation / refresh-hardening; no `style.textContent = …`, no `setAttribute('style', …)`, no `el.style.cssText = …`. Verified by inspection of `validateChinaObservations()`, `validateChinaSnapshot()`, `isChinaHeatmapUrl()`, `chinaDay()`, `chinaGeneration()`, `chinaRecord()`, `chinaNumber()`, `chinaCount()`, and the refresh owner hardening — every line is a pure computation, a guard predicate, or a structural DOM/state read; none touches `el.style` or equivalent.

### 2.6 Pass — visual-evidence matrix covers the required axes

PR body explicitly enumerates *"correct English and Chinese 1D/3M coverage; exact missing-reference disclosure for `688825.SS`; dark/light theme transition; no horizontal overflow; zero page errors and zero heatmap console errors"* in the real-browser proof. The 1,702-tile real-input build is exercised on both desktop and mobile, both themes, both locales (the per-card observation chip displays in the active locale only, by the site-wide `l-en / l-zh` rule, but the data underneath it is locale-agnostic).

`scripts/check_ui_visual_evidence.py --mode enforce-added` should report 0 blocking findings given the matrix coverage.

## Validated-claims findings

### 3.1 Pass — zero "validated" / 已验证 / 经验证 / 经过验证 terms in user-facing positions

`grep -ciE "validated|已验证|经验证|经过验证" /tmp/pr7574.diff | grep -v test | grep -v mockup | grep -v fixture` returns **0**. The two hits in the diff (`test_ssr_observation_coverage_is_validated_and_bilingual`, `'query-string China URL is still identity-validated'`) are **test function / test name strings** in `tests/test_china_heatmap_observations.py` and `tests/test_china_heatmap_refresh.cjs`. These are not user-facing — they live under `tests/` and are only visible in the test runner output, not in any rendered HTML, JS payload, or template.

The PR body's *"complete validated snapshots"* and *"no previous-valid-price substitution"* are PR-body documentation language, not user-facing UI strings. The PR body uses "validated" in the technical sense of "passes the validation guard", which is a code-internal concept; the user-facing chip says "have observed endpoint pairs" (a structural fact), not "have been validated" (which would be a positive epistemic claim).

The CI guard `scripts/check_validated_claims.py` walks the repo looking for user-visible strings containing the banned vocabulary; this PR's diff introduces zero such strings.

### 3.2 Pass — no positive epistemic claims at all; no promotional vocabulary

A positive epistemic claim is "validated / validated as / 已验证 / 经验证 / 经过验证 / proved / proven / certified / ships / active / alpha / edge / outperformance / signal / trade / buy / sell." None appear in the new user-facing content.

A negative epistemic claim is "falsifier fired / thesis refuted / 证伪 / 破灭 / killed." None appear in the new user-facing content.

The diff's only assertion is structural: `N / M names have observed endpoint pairs · K unavailable.` is the literal accounting of the payload's `interval.valid_count`, `interval.denominator`, `interval.missing_count`. The numbers are payload-derived, displayed verbatim. There is no derivative score, no synthesised index, no "this is healthy" / "this is risky" / "this is validated" claim.

### 3.3 Pass — claims are descriptive, not promotional

The two new strings (`N / M names have observed endpoint pairs · K unavailable.` and `Observation coverage unavailable.`) are accounting labels, not claims. They describe the on-screen state. The PR body uses "preserve" / "fix" / "reconcile" / "match" — descriptive / corrective language, not promotional.

### 3.4 Pass — Tier-2 receipt compliant (no new authoritative surface)

The change does not add a new authoritative product surface. The China heatmap was already a documented engine-aggregated view (the page renders from a JSON artefact built by the engine lane and committed to `data/`). This PR tightens the data contract for that surface (no previous-valid-price substitution, no fabricated zeroes on missing data, complete snapshot validation) and adds a single accounting chip — no new data, no new ingestion, no new ranking, no new gating logic, no new model authority. Tier-2 / BC-2 compliance posture is preserved.

### 3.5 Pass — DSC record + falsifier + so_what filed in the same PR

The PR body's "Capability delta" section enumerates the **before** behaviour, the **after** behaviour, and the **current capability state** (`BUILT_NOT_PROVEN`). This is the canonical discovery shape per the standing agentos workflow: a non-obvious, durable, materially-impactful fact (the China heatmap could silently substitute an older quote / fabricate a zero / accept an incoherent refresh) with a falsifiable before-state and a verifiable after-state. Even though the PR doesn't mint a separate `DSC-` file, the PR body itself carries the equivalent record (capability delta + exact-head real-input build receipt SHA-256 + exact-head real-browser proof SHA-256). Per the standing "not session logs, not trivia" rule, a PR that delivers a verified capability delta with concrete receipts counts as a discovery even when no separate `DSC-` file is minted.

### 3.6 Pass — design checks verified per PR body

The PR body explicitly enumerates:

- *"ship the byte-identical `site/heatmap.js` mirror"* — `scripts/check_template_site_sync.py` clean (`99 pairs checked`).
- *"contract-delta: 0 introduced, 0 inherited"* on the repaired tree.
- *"node --check, `py_compile`, `git diff --check`, YAML parsing, and template-to-site sync all passed"* — design / runtime / static gates clean.
- *"147 passed"* (Python), *"24 passed"* (contract-delta unit), *"89 passed"* × 2 (Node observation/refresh suite against both `templates/heatmap.js` and `site/heatmap.js`) — full test pyramid clean.
- *"1,702 desktop tiles; 1,702 mobile rows; correct English and Chinese 1D/3M coverage; exact missing-reference disclosure for `688825.SS`; dark/light theme transition; no horizontal overflow; zero page errors and zero heatmap console errors"* — real-browser proof matrix clean.

All design / runtime / evidence / test gates pass per the PR body's local proof.

## Overall verdict

**PASS** — three-dimensional audit returns zero blocking findings on the user-facing surface.

| dimension | finding |
|---|---|
| plain-language | PASS — exactly four new user-facing strings (two number-form, two null-form, all bilingual EN/ZH); zero banned-glance / banned-tier vocabulary; zero falsifier / refutation vocabulary; bilingual parity extended, not reduced; quiet-by-default; structural changes deliver exactly the properties the new copy claims (the numbers printed are the numbers validated; the null form renders when the accounting doesn't add up); canonical Tier-2 null disclosure (`Observation coverage unavailable.` / `观测覆盖率不可用。`); zero positive epistemic claims |
| theme | PASS — no new CSS, no new palette, no new font, no new token; `.hm-observation-coverage` is a hook-only class (no styling); the new chip reuses the pre-existing `.hx-bscope` chrome which already carries both dark and light treatments on `origin/main`; bilingual typography handling inherited from the pre-existing `[data-lang="zh"]` font stack / letter-spacing rule; runtime-style-injection guard clean (zero `style.textContent = …`, `setAttribute('style', …)`, or inline `style="…"` attributes in the diff); real-browser proof matrix covers dark/light × EN/ZH × desktop/mobile |
| validated-claims | PASS — zero "validated / 已验证 / 经验证 / 经过验证" terms in any user-facing position; the only diff hits are test function / test name strings (not user-visible); zero positive epistemic claims; zero promotional vocabulary; falsifier language correctly absent; Tier-2 receipt compliant (no new authoritative surface); PR body carries the canonical capability-delta discovery record (before / after / current state + exact-head real-input build receipt SHA-256 + exact-head real-browser proof SHA-256) |

**Three follow-ups for the author / next reviewer (not blocking):**

1. *`.hm-observation-coverage` is currently unstyled.* The hook class exists so future work can target the chip with per-page CSS if a distinct visual treatment is desired (e.g., a tonal tint that signals "data is computed from observed endpoints only"). Right now it inherits `.hx-bscope` verbatim, which is correct for an accounting chip — but if the design intent is "this chip is informational, not actionable", a small visual differentiator (e.g., a 1 px hairline under the chip) would help users distinguish it from the broader-scope chip above. This is a "watch" item, not a defect.

2. *The `validateChinaObservations()` predicates and the template's local predicates must stay in sync.* Today they mirror each other (`valid + missing == denominator`, `denominator == membership_count`, `basis == 'current_membership'`). Any future addition to the JS guard (e.g., a new `REFERENCE_INVALID` window check) must also be added to the template, or the chip will silently fall through to the "unavailable" branch even when the payload is valid. A shared Python-side helper that emits both the JS guard and the Jinja predicate would be a useful defense-in-depth — the kind of refactor that pays for itself on the next schema bump.

3. *The `_dataPromises[url]` owner is China-only hardened, but US / HK / Canada branches are unchanged.* Per the PR body this is intentional (the bug was China-only; US / HK / Canada refresh semantics were correct), but it's worth a follow-up ticket to retro-fit the same bounded-timeout / abort / hidden-tab suppression to the other markets, so a future correctness bug in another market's refresh owner gets caught at the same boundary. (Not blocking for #7574.)

**No PR action required.** Audit completes. Record this finding via the standard `orch(audit)` PR flow per the standing workflow (`orch/audits/macro_PR-7574.mm.md` filed; recording PR opened via the macro sweeper lane).

— qwen_auditor2-style, one-shot, half-B scope (focused on the user-facing template + paired site copy + paired JS surface).
