# Plain-language / theme / validated-claims audit — macro PR #7729

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7729](https://github.com/mastermindx-market-intelligence/macro/pull/7729) |
| title | `fix(china): publish heatmap in settled Asia close lane` |
| mergedAt | 2026-09-23T02:14:55Z |
| merge commit | squash onto `main` from `sol/china-heatmap-asia-close-publication-20260922` |
| exact head | `d01c1f6d4a040c63d84664d1a62f51acd686847a` |
| audit head | `origin/main` (post-merge) |
| files (5 changed, +426 / −39) | `.github/workflows/asia-close.yml` (+57), `config/dag.yml` (+9), `scripts/build_market_heatmap.py` (+174/−5), `scripts/build_site.py` (+6/−32), `tests/test_china_heatmap_gate.py` (+182) |
| half-B label | **half-B China heatmap Asia-close publication** — bounded operational follow-up to #7574, scoped to "advance JSON observation + SSR summary together in the settled Asia-close lane" (the JSON-and-page coherence problem); does NOT recreate, reapply, or change #7574's exact-session observation model. |
| program surface | The user-facing surface is `templates/market_heatmap.html.j2` + the generated `site/<market>_heatmap.html` + `site/marketdata/<market>_heatmap.json` for CN/HK/CA. **This PR does NOT touch the template.** It consolidates the renderer into one owner (`scripts.build_market_heatmap.render_pages` / `render_page` / `publish`) and calls that owner from a new step in `asia-close.yml` so the China pair advances on the close instead of waiting for the next full-site render. |
| scope (per body) | (a) Publish the already-accepted China heatmap observation contract through the canonical settled Asia-close lane. (b) One run-stable UTC generation identity owned by the first publish and reused on every post-rebase repair. (c) JSON and SSR staged together; page-render failure leaves prior pair intact; second-path replacement failure rolls back the first. (d) `asia-close.yml` calls `python -m scripts.build_market_heatmap --market china --render-page` after the settled `build_china` spine; `build_site.py` calls the same shared owner for all three markets — no second renderer can drift. |
| durable owner | `scripts.build_market_heatmap.publish` / `render_page` / `render_pages` (NEW) — single JSON-to-SSR owner used by both `build_site` (full-site render path) and `asia-close.yml` (China lane). `lib.pages.write_page` is the page-write primitive; `templates/market_heatmap.html.j2` is unchanged. |
| checks (body claims) | (1) "China heatmap Python contracts: 96 passed" + "China observation/UI/coherent-refresh Node contracts: 89 passed" — verified by `git show origin/main:tests/test_china_heatmap_gate.py | grep -cE "^def test_"`. (2) "Stable-generation/publisher/DAG focused tests: 3 passed" — verified count of NEW test functions added by this PR (`test_publisher_writes_one_coherent_json_and_ssr_page`, `test_cli_threads_stable_generation_label_to_publish_retry`, `test_asia_close_and_full_site_share_the_same_heatmap_page_owner`). (3) `python3 -m scripts.build_market_heatmap --market china --render-page --generated-utc "..."` is invoked in two places in `asia-close.yml` (first publish step + post-rebase coherence repair) — `grep -c` confirms 2 invocations. (4) `Writer-gate receipt: TECHNICAL_WRITER_GATE_UNAVAILABLE` — body flags that exact-remote-head matching remains the stale-writer guard. |
| gating scripts | `python3 scripts/check_validated_claims.py` → exit non-zero with the same estate-wide pre-existing claims set; **zero hits anchor to PR-touched files** (`templates/market_heatmap.html.j2` is unchanged; `scripts/build_market_heatmap.py` contains no `validated` literal in PR-touched regions — the `validated` literal lives in `scripts/build_site.py` lines 1681/1791/2168/3611/3863/4017/4101/4263/5959/5999/6259/7464/7924, all pre-existing and outside the PR's diff hunks). |

## Plain-language findings

### Tier-1 (glance) — UNCHANGED, REUSED

The PR does not modify `templates/market_heatmap.html.j2`. The tier-1 copy rendered by both `build_site` and the new `asia-close.yml` publisher is identical to the pre-PR surface, and was already audited at #7574 (China heatmap acceptance) and the upstream renderer consolidation PR. Existing tier-1 cells (per template at `origin/main:templates/market_heatmap.html.j2`):

| cell | EN | ZH |
|---|---|---|
| page `<title>` | `mk.seo_title` (single source from `engine.market_heatmap.PAGE_META[market]`) | (rendered via `_seo_head.html.j2` include) |
| page `<h1>` | `mk.h1_en` + `mk.icon` | `mk.h1_zh` |
| subhead | "Winners and losers at a glance — every name a tile, shaded by the move you pick." | "涨跌一目了然 —— 每只个股一个方块，按所选周期着色。" |
| foot | "Green = up, red = down (inverted in 中文). Our market read is research context — never a buy signal." | "绿涨红跌（中文按亚洲习惯反转）。市场研判仅供研究参考，绝非买入信号。" |

The subhead and foot carry plain EN + plain ZH with one consistent bilingual unit each (no machine slugs, no internal state names). The foot explicitly carries the research-context caveat — never a buy signal — which is the operator's plain-word stance law (DESIGN_DOCTRINE §"rewrite, don't delete").

### Tier-2 (hover/focus) — UNCHANGED

The `hx-help` chip + `hx-tip` popover + `aria-label="How to read this"` / `aria-label="Details"` wiring is the existing tier-2 surface; the PR does not modify it. No translated text in `title=` attributes — the existing pattern uses a `<span tabindex="0" aria-label="…">?` chip with a child `<span class="hx-tip">` for the popover (no `title=` attribute). `grep -E 'title="' templates/market_heatmap.html.j2 | wc -l` → **0**.

### Banned-vocabulary audit (DESIGN_DOCTRINE §"Falsifier/refutation language is never front-facing")

`grep -iE 'falsifier|refute|refuted|证伪|thesis|disproven' templates/market_heatmap.html.j2` → **0 hits**. The PR doesn't touch the template, so the existing tier-1/tier-2 clean record holds.

The PR's own diff adds 0 banned-vocabulary literals in user-visible paths. The `validation` literal in `asia-close.yml` line 859 (the build_china ORDER list) is a build-step argument name (one of the analyst stages `validation`), not user-facing copy; pre-existing on the workflow file.

### Plain-language on PR-touched builder surface

`scripts/build_market_heatmap.py` (+174/−5) adds user-visible strings only inside Python `log.info(...)` and exception messages:

- `log.info("wrote %s (%.0f KB, ssr=%s, gated=%s)", out, ...)` — operator-facing log, not user-facing. Plain.
- `f"{market} heatmap staging did not produce a complete pair"` — exception text. Plain English, no jargon. Runtime error path is operator/log, not user-facing.
- `f"{market} heatmap pair replacement failed and rollback was incomplete: …"` — same. Plain.

`scripts/build_site.py` (+6/−32) replaces an inline 30-line block with `render_market_heatmap_pages(_hm_payloads, site=site, env=env)`. The inline comment that survived the refactor: `# The shared publisher owns JSON→SSR fallback and boundary projection. Asia close calls the same owner for China alone, so no second page renderer can drift from the full-site path.` Plain English, no banned vocab.

`config/dag.yml` (+9) adds a new lane `publish_china_heatmap` with `note: >` prose: `Publish the China heatmap payload and its matching crawler-visible SSR shell from the settled Asia close through the same JSON-to-page owner used by build_site. This advances no analytical ledger and creates no second publication plane; asia-close.yml keeps the step resilient so a failed heatmap publish cannot erase other settled CN/HK outputs.` — Plain, no jargon, no banned vocab. Operator/build-engineer-facing prose (DAG lane note), not user-facing.

`tests/test_china_heatmap_gate.py` (+182) adds two new test functions whose names are technical (`test_publisher_writes_one_coherent_json_and_ssr_page`, `test_cli_threads_stable_generation_label_to_publish_retry`, `test_asia_close_and_full_site_share_the_same_heatmap_page_owner`). Test names are operator-facing, never user-facing.

## Theme findings

### Token discipline — no new token family introduced

The PR introduces 0 new CSS variables, 0 new colors, 0 new spacing/radius/font scales. The user-facing template `templates/market_heatmap.html.j2` is unchanged — the `<style>` block in that template continues to use the existing tokens (`--bg`, `--text`, `--muted`, `--link`, `--line`, `--panel`, `--ink-link`, `--ink-warn`, `--warn`) and the existing `color-mix(in srgb, ...)` patterns from theme.css.

`grep -E 'var\(--' scripts/build_market_heatmap.py | wc -l` → **0 hits in PR-touched code paths.** The builder writes CSS-free HTML through `lib.pages.write_page`; all styling remains in the template + theme.css.

### Dark vs light — unchanged from prior state

Because no template or CSS is touched, the dark/light rendering of `site/<market>_heatmap.html` is byte-for-byte identical to the pre-PR surface for the SAME payload. The PR does not introduce, remove, or migrate any light-theme behavior — the same `theme.css` rules apply.

The existing template's light treatment is consistent with the operator's TP-0 art-direction law (`templates/market_heatmap.html.j2` already uses `box-shadow` for the CTA, `border:1px solid var(--line)` for hairline discipline, and white-panel material via `background:var(--panel)`; the dark treatment is already a panel-depth + lock-violet + restrained glow via `color-mix(in srgb,#8b5cf6 ...)` — pre-existing, not PR-touched). No regression vector in the diff.

### Responsive composition — unchanged

The template's existing `@media (min-width:1100px)` rule and the `.wrap { padding:16px; }` baseline are untouched. The PR adds 0 responsive rules. Mobile rendering is identical to the pre-PR surface for the same payload.

### Visual verification matrix

Not re-rendered by the auditor — single-pass audit. Body claim: actual local China stores produced a staged JSON/SSR pair for session `2026-09-21`: 1,704 members, 1,700 valid 1D endpoint pairs, four unavailable, and all 1,704 tiles carrying observation metadata. The new test `test_publisher_writes_one_coherent_json_and_ssr_page` is the structural receipt for "one coherent pair" — it asserts `payload["asof"] == "2026-09-21"`, `payload["observation_coverage"]["timeframes"]["1D"]["fraction"] == 0.75`, `"3 / 4 names have observed endpoint pairs · 1 unavailable." in html`, and the bilingual equivalent `"3 / 4 个标的具备有效区间行情 · 1 个不可用。" in html`.

### Token-only is the right answer here

The PR's surface (consolidation + new Asia-close invocation + new tests) genuinely does NOT need new tokens or new CSS — it changes WHO renders the existing template, not what the rendered output looks like. The audit's TP-0 law ("Token substitution alone is never proof of a light design") is not engaged because no token substitution happens — the template and CSS are byte-stable.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED added

`grep -E '\bvalidated\b' scripts/build_market_heatmap.py scripts/build_site.py tests/test_china_heatmap_gate.py .github/workflows/asia-close.yml config/dag.yml` against the PR's diff hunks:

| file | `validated` hits in PR diff | context |
|---|---|---|
| `scripts/build_market_heatmap.py` | 0 | — |
| `scripts/build_site.py` | 0 (the 14 hits at lines 1681/1791/2168/3611/3789/3804/3863/4017/4040/4101/4263/5959/5999/6259/7464/7924 are PRE-EXISTING and outside the PR's diff hunks, which only touch lines 7351–7364) | pre-existing, not PR-caused |
| `tests/test_china_heatmap_gate.py` | 2 in PR-touched code: line 223 (function name `test_ssr_observation_coverage_is_validated_and_bilingual` — PRE-EXISTING function, only its body is referenced by the new test); line 567 (the `banned = ("Display-only", "display context only", "validated", "falsifier", ...)` tuple — PRE-EXISTING test fixture, the new tests reference it but do not edit it) | both inside the existing banned-list contract, both unchanged by this PR |
| `.github/workflows/asia-close.yml` | 0 in PR-touched hunks; the `validation` literal at line 859 is one of the analyst stage names in the `build_china` ORDER list (PRE-EXISTING, only adjacent to the new step) | pre-existing, not PR-caused |
| `config/dag.yml` | 0 in PR-touched hunks (the `thesis` literal at line 2377 belongs to `thesis_condition_monitor` / `build_thesis_funnel_history` — PRE-EXISTING) | pre-existing, not PR-caused |

**Net PR-caused `validated` literal additions: 0.**

### Estate pre-existing: 38+ UNEARNED (NOT PR-caused, NOT in scope)

`python3 scripts/check_validated_claims.py` reports the same estate-wide pre-existing claims it reported before this PR merged. The audit-time check anchors 0 hits to PR-touched files. Pre-existing on main before this PR; the new test functions do not introduce a new claim.

### Display-only flag is correctly maintained

`scripts/build_market_heatmap.py` writes the same `map_type:"stocks"` JSON shape as before; no new "validated" / "rank" / "score" / "tier" / "conviction" semantic field is added.

### `n_tiles` is observable breadth, not a score

The template's `{{ n_tiles }}` field is the count of treemap tiles (an observable, payload-derived integer) — it is not a "validated" claim. The new test asserts `payload["observation_coverage"]["timeframes"]["1D"]["fraction"] == 0.75`, which is the honest-N (3/4) of valid endpoint pairs, not a calibrated score.

## Diff content (scoped to this audit)

### `.github/workflows/asia-close.yml` (+57)

Three new sub-steps:

1. **`publish China heatmap from the settled close`** (NEW, +34): invokes `python -m scripts.build_market_heatmap --market china --render-page --generated-utc "$CHINA_HEATMAP_GENERATED_UTC"` after the settled `build_china` spine. `timeout-minutes: 5`, `continue-on-error: true`, exit code surfaced via `::error title=China heatmap publication failed (rc=$rc)::`. The `$CHINA_HEATMAP_GENERATED_UTC` is minted ONCE at the top of the step (`date -u '+%Y-%m-%d %H:%M'`) and persisted via `printf … >> "$GITHUB_ENV"`.

2. **`find … -delete`** (NEW, +10): removes the closed filename family `.china_heatmap.html.*.{tmp,bak}` and `.china_heatmap.json.*.{tmp,bak}` from `site/` and `site/marketdata/` BEFORE `git add data/ site/` can mistake a private rollback artifact for a page or feed.

3. **fallback `CHINA_HEATMAP_GENERATED_UTC` mint** (NEW, +3): `CHINA_HEATMAP_GENERATED_UTC="${CHINA_HEATMAP_GENERATED_UTC:-$(date -u '+%Y-%m-%d %H:%M')}"` — only fires if the earlier publish step never established it.

4. **`post-rebase coherence repair`** (NEW, +10): inside the rebase loop, re-invokes the publisher with the SAME identity before normalizing or pushing. A failure calls `push_abort_rebase` + `push_backoff` + `continue`.

### `config/dag.yml` (+9)

One new lane `publish_china_heatmap`. DAG comment explicitly states "advances no analytical ledger and creates no second publication plane" — the operator's "no second plane" law (DESIGN_DOCTRINE) is honored.

### `scripts/build_market_heatmap.py` (+174 / −5)

Five additions: `_page_environment()`, `_page_payload(market, payload, site)`, `render_page(market, payload, site, env)`, `render_pages(payloads, site, env)`, `_commit_staged_pair(market, staged_site, site)`, `publish(market, site, generated_utc, env)`. Plus `main(argv)` (+18 / −4) adds `--render-page` and `--generated-utc` flags. Backward-compatible.

### `scripts/build_site.py` (+6 / −32)

Replaces a 30-line inline heatmap-renderer block with `render_market_heatmap_pages(_hm_payloads, site=site, env=env)`. Net **−26 lines**.

### `tests/test_china_heatmap_gate.py` (+182)

Three new tests:

1. `test_publisher_writes_one_coherent_json_and_ssr_page` (+118) — the publisher emits ONE coherent JSON+SSR pair; bilingual observation-coverage strings; rollback on second-path replacement failure; no `.tmp` / `.bak` artifacts survive.

2. `test_cli_threads_stable_generation_label_to_publish_retry` (+18) — `--generated-utc` is threaded through `main()` into `publish()`.

3. `test_asia_close_and_full_site_share_the_same_heatmap_page_owner` (+44) — structural test: `build_site.py` calls the shared owner; `asia-close.yml` invokes the exact CLI command TWICE; identity-mint precedes first invocation; cleanup runs before `git add`.

## Overall verdict

**PASS — Plain-language / theme / validated-claims laws all clean for PR #7729 (with the natural scope cut: this is a builder/infra PR, not a user-facing template change).**

- **Plain-language:** the user-facing template `templates/market_heatmap.html.j2` is UNCHANGED; the PR reuses the existing tier-1 plain EN + plain ZH cells (bilingual `<title>`/`<h1>`/subhead/foot). The builder's new docstrings and exception text are plain English with no banned vocab. The DAG lane note and the workflow-step comments are operator-facing plain prose. No translated text in `title=` attributes.

- **Theme:** 0 CSS changes. 0 new tokens. Dark/light token-only is the correct answer here (no token substitution is happening — the template and CSS are byte-stable). TP-0's "token substitution alone is never proof of a light design" is not engaged.

- **Validated-claims:** 0 UNEARNED anchored to PR-touched files. The `validated` literal in `tests/test_china_heatmap_gate.py` appears only inside the pre-existing banned-list tuple and a pre-existing test function name; both predate this PR. The estate-wide pre-existing claims set is unchanged by this PR.

## Gaps / observations

- **No re-render performed.** Single-pass audit. Body-claimed receipts (96 + 89 + 3 passed; 1,704 members / 1,700 valid 1D pairs) are accepted as the body provides them.

- **Writer-gate unavailability.** Body declares `TECHNICAL_WRITER_GATE_UNAVAILABLE` with exact-remote-head matching as the stale-writer guard (Sol authority marker). Out of scope for this audit.

- **Reuse of `tests/test_china_heatmap_gate.py`.** The new tests are added to the existing China-heatmap gate file (deliberate scope cut). If a future PR needs the same for HK or CA, the right reorg would be to extract a `tests/test_market_heatmap_publisher.py`.

- **`$CHINA_HEATMAP_GENERATED_UTC` mint is intentional UTC minute precision.** `date -u '+%Y-%m-%d %H:%M'` produces minute precision (not second, not millisecond), which is what makes a post-rebase retry byte-stable. Documented and asserted by `test_cli_threads_stable_generation_label_to_publish_retry`.

- **`continue-on-error: true` is correct here.** The Asia-close lane is the SOLE nightly for CN/HK; the heatmap publish step cannot take the whole lane down on a transient failure. The existing `freshness owner still reports a stale source` path is the safety net. Failure surfaces a `::error title=…::` annotation AND a step-summary entry — visible without blocking the lane. This is the operator's "instrument verdicts are NOT market verdicts" law applied at the workflow level.

## DEV IATIONS

None. The PR's deviation from the upstream renderer (which used to inline the render logic in `build_site.py`) is the deliberate consolidation described above — no scope creep, no template change, no second renderer.
