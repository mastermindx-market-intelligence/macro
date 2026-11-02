# AI Brief v2 — program spec (ABX)

Chartered 2026-07-19 by operator order: "Conduct a complete AI brief upgrade for all 3
briefs." One PR. Owner: main loop (Fable) — prompts + this spec; sonnet builder — engine
mechanics; opus designer — surfaces. Doctrine: `docs/DESIGN_DOCTRINE.md` binds every
user-visible string, INCLUDING the LLM's own output (the prompt is now a Tier-1
copywriter contract).

## 0. The seven operator complaints → the seven fixes

| Complaint | Root cause found | Fix |
|---|---|---|
| Machine text everywhere ("growth_score -0.143", "-2.5σ", "panel: hk.sector_rs", "cross_asset_confirm", "FR007") | State JSON keys leak straight into prose; prompts even *ask* for citations | VOICE law in every prompt + deterministic style lint + one rewrite retry (§4) |
| Rotation thesis parroted in every brief | `DEFAULT_THESIS` injected every run + `rotation_check` is a REQUIRED schema field | Field becomes conditional; "never restate the thesis wording" rule (§3) |
| "Q1 Goldilocks" black-and-white labels; blind to the reflation drift | `_macro_summary` passes only `transition_state:"TRANSITIONING"` — no direction, no drift, though the engine computes flip_condition/flip_margin/dwell + regime_history.parquet | `regime_path` context block + REGIME=POSITION law (§5a) |
| Transmission / Disagreements incomprehensible | No format contract | "If X → then Y" plain-chain contract, ≤2 items, word caps (§2) |
| Wall-of-paragraph top; What-to-watch too long | Schema has no glance tier | `tldr` bullets (3–5, capped) + stance line; watch items "Trigger: meaning" ≤16 words (§2) |
| No permanent illustration components | All content is free prose | `key_facts` deterministic chip rail — engine-computed, bilingual, tone-tinted (§6) |
| BTC daily is wasteful; US/China/BTC UIs inconsistent | Global `interval_days`; three renderers diverged | Per-lens interval (btc=3) + ONE shared body renderer for all four surfaces (§7) |

## 1. Files & ownership

| Area | Files | Owner |
|---|---|---|
| Prompts + schema constants | `engine/master_brain.py` (constants only) | main loop — ALREADY EDITED, do not rewrite the prompt strings |
| Engine mechanics | `engine/master_brain.py` (functions), `engine/neuralweb/brief_context.py`, `config.yml` | builder |
| Surfaces | `templates/dashboard.html.j2` (dlg-aibrief), `templates/china.html.j2` (cnx-dlg-aibrief), `templates/hk.html.j2` (hkx-dlg-aibrief), `templates/aibrief.html.j2`, NEW `templates/_aibrief_body.html.j2`, `templates/aibrief.js` (+ paired `site/aibrief.js`), `templates/masterbrief.js` (retire if orphaned — verify), `scripts/build_aibrief.py` | designer |
| Tests | `tests/test_master_brain*.py`, `tests/test_brief_context.py`, `tests/test_aibrief_page.py`, `tests/test_aibrief_w4_panels.py` | builder (after both lanes land) |

PAIRED-ASSET LAW: `templates/aibrief.js` ships as `site/aibrief.js` — byte-match in the
same PR (`python -m scripts.check_template_site_sync --fix`). Same for masterbrief.js if
touched. NO other site/ or data/ churn in this PR (source-only; restore any local build
artifacts before commit).

## 2. Schema — `master_brief.v2` (additive; every v1 key retained)

LLM-emitted, zh-translated by the existing `_translate_brief` pipeline:

| key | type | contract |
|---|---|---|
| `tldr` | list[str], 3–5 | NEW. Point-form glance. Each item "Head: rest", head ≤3 words, rest ≤14 words. Item 1 = the single most important thing today. LAST item MUST start "What to do:" + stance vocab (§3 stance law). |
| `summary` | str | kept. ONE sentence ≤22 words, plain words (face teaser). |
| `regime_read` | str | kept. ≤2 short paragraphs; MUST narrate position-within-regime + drift direction (§3 regime law). |
| `conflicts` | list[str], 1–3 | kept. Each "Head: A says X, B says Y — what it implies", ≤30 words. |
| `transmission` | list[str], 0–2 | kept. Each "If <thing that is happening> keeps up → <what follows next>", ≤24 words, zero acronyms. |
| `rotation_check` | str, OPTIONAL | kept key, new semantics: emitted ONLY when evidence meaningfully moved for/against the standing playbook; NEVER restates the thesis wording; ≤40 words. Omitted → UI section absent. |
| `watch_items` | list[str], 2–4 | kept. Each "Trigger: what it means", ≤16 words. |
| `confidence` | low/medium/high | unchanged |
| `theses`, `forward_watch`, `forward_read` | | unchanged (macro only; existing hard rules stand) |

Engine-emitted (deterministic — never from the LLM):

| key | type | contract |
|---|---|---|
| `key_facts` | list[obj], ≤6 | `{key, label_en, label_zh, value_en, value_zh, tone}` — tone ∈ good/warn/bad/neutral/info. Built per lens from calibrated state (§6). Fail-open: missing source → chip omitted, never raises. |
| `refresh_days` | int | the lens's interval (1 or 3) — UI renders the cadence chip honestly |
| `style_flags` | list[str] | banned tokens that survived the rewrite retry (observability; NOT rendered on user tiers) |
| `served_by` | str \| None | NEW (provider ladder). The rung that actually served this brief — `"codex"` / `"oauth"` / `"anthropic"` / `"deepseek"` — or `"cache"` on a reply-cache hit, or `None` on a degraded call. `model` is now the model id of THAT rung (falls back to the configured `llm_model` on a cache hit, a degraded call, or a `call`/`_call_model` stub that ignores the new `served` out-param). Makes the load balancer verifiable from the artifact itself instead of every brief always reading as `deepseek-v4-pro`. Same treatment applies to `ai_desk.v1`'s `model`/`served_by`. |

Two consequences of routing this lane onto the shared ladder, recorded because
neither is visible in the field table and both change what a brief actually is:

- **DeepSeek serves this lane with reasoning mode OFF.** `build_providers` wraps the
  DeepSeek rung in `_deepseek_no_thinking()`, which the old hand-built client did not.
  So on a DeepSeek-served night the briefs are non-reasoning completions, while
  `model` still reads `deepseek-v4-pro`. The `max_tokens: 8000` note in `config.yml`
  budgets for thinking tokens and now applies only to the Claude rungs. Quality impact
  is **unmeasured** — this is a disclosure, not a verdict.
- **The writer translates its own brief** (operator 2026-08-27; supersedes the
  "zh half is still DeepSeek-only" note recorded here a day earlier).
  `_translate_brief` used to build a hardcoded DeepSeek V4-Flash `tcfg` for
  `engine.translate`, which has no ladder — so a DeepSeek balance exhaustion left the
  English brief standing and silently dropped `brief["zh"]` on all three lenses, and
  every zh pass was billed to the one metered provider even on nights Codex or Claude
  wrote the English for free. It now goes through `_call_model`: same
  codex → oauth → anthropic → deepseek waterfall, same lane, same cooling policy, with
  the lens `usage_stage` suffixed `-zh` so the cost ledger still separates the two
  passes. Batched at 6 items; a malformed or truncated reply fails ITS BATCH closed
  (a short array would shift every later field onto the wrong key) and the remaining
  batches still land. `engine/translate.py` itself is unchanged and still ladderless —
  it is shared by `catalyst_stock` and `scripts/translate_profiles`, which are separate
  lanes and out of scope here.

`schema` field bumps to `"master_brief.v2"`. Builder greps every consumer of the literal
`master_brief.v1` and fixes string-matches (renderers are `get()`-based fail-open;
`engine/neuralweb/cortex.py` + `brain_gateway.py` read briefs — verify they don't pin).

zh translation: extend `_ZH_SCALARS`/`_ZH_LISTS` with `tldr` (list). `key_facts` is
bilingual at build time from the §6 vocab — never sent to the translator.

## 3. Prompt architecture (constants already written by main loop — wire, don't rewrite)

Shared blocks composed into all three system prompts:
- `_VOICE_LAW` — the no-machine-text writing contract (bans snake_case, σ/z/percentile,
  panel citations, quad codes; number ration; acronym policy; "taxi-driver test").
- `_REGIME_MAP_LAW` — regime = position on a map, drift is the story.
- `_STANCE_LAW` — final tldr line restates the DETERMINISTIC system posture in the
  doctrine stance vocabulary (Act · Get ready · Watch — don't chase · Protect gains ·
  Stand aside · Ignore); may soften, never escalate. (Epistemics: the LLM never
  originates a stance — it translates the system's own posture keys.)
- `_THESIS_RULE` — playbook mentioned ONLY in optional `rotation_check`, only on
  meaningful movement, never restated verbatim, never in tldr/regime_read/conflicts.
- `_SCHEMA_TAIL_V2` — the field contract of §2 with hard word budgets.
- Same-tape rule compressed to 3 lines; stale/absent honesty, no-fabrication,
  no-sizes/no-trades, small-sample honesty all retained.
- `_FORWARD_TAIL` + `_MACRO_THESES_TAIL` retained verbatim (ledger contracts).

## 4. Style lint (deterministic, engine)

`_style_violations(text: str) -> list[str]` over every LLM string field (tldr items,
summary, regime_read, conflicts, transmission, rotation_check, watch_items,
forward_read):
- snake_case token: `\b[A-Za-z]+_[A-Za-z0-9_]+\b`
- sigma/z/percentile: `σ`, `\bz[- ]?scores?\b`, `[+-]?\d+(?:\.\d+)?\s*σ`, `%ile`, `\bpctile\b`, `\bpercentile\b`
- panel citations: `\bpanels?\s*:`, `\bdashboards?\s*:` (colon form only)
- quad codes: `\bQ[1-4]\b` (regime quads; calendar quarters like "Q2 GDP" are a rare
  loss — acceptable, the model is told to write "second-quarter GDP")
- hard-banned tokens (case-insensitive): `cross_asset_confirm, neural_web, nw_synthesis,
  tape_family, cphase, mvrv_z, funding_z, etf_flow_z, oi_mcap, hy_oas, ntfs, display-tier,
  display_only`
- paren-gated tokens (allowed ONLY inside parentheses following plain words, e.g.
  "China's 7-day interbank rate (FR007)"): `FR007, MVRV, NUPL, SSR, DVOL, EBP, SOFR, IORB, LPR, RRR`

Pipeline in `_call_model` (or a wrapper): reply → parse → collect violations across
fields → if any, ONE rewrite call (small system prompt listing the offending tokens,
original reply as user content, "same JSON, same claims, plain language") → re-parse; if
violations persist, keep the reply and record `style_flags`. The reply cache stores the
FINAL post-lint text (cache key unchanged: model‖system‖user of the ORIGINAL call).
Degrade-never-raise everywhere.

## 5. Context integration

a) **`regime_path` (macro state)** — new block in `_macro_summary` output:
   - from `data/regime/latest.json`: `transition_state`, `transition_state_raw`,
     `transition_dwell_remaining`, `flip_condition` (verbatim), `flip_margin`,
     `transition_flags` (names only).
   - from `data/regime/regime_history.parquet` (fail-open if unreadable): growth/inflation
     scores now vs 5 and 20 rows back + plain drift strings the builder composes
     deterministically, e.g. `"growth −0.07 now vs +0.14 20d ago (cooling toward the
     Reflation border)"` — direction word from sign of delta only; no new thresholds.
   - china lens: pass `pending_quad`/`pending_days` (already in state) + same-shape
     drift from china history parquet if one exists under `data/china_regime/`
     (builder verifies; omit silently if absent).
b) **`btc_slice()`** in `engine/neuralweb/brief_context.py` (cap 4 096 bytes, same
   fail-open/stale contract): blocks `market_core`, `liquidity_plumbing`,
   `cross_asset_flows`, `contagion` (when present), `attention` (only items whose text
   mentions btc/bitcoin/crypto, ≤3), `cortex` (tail). Drop order (first-dropped →):
   attention, contagion, cross_asset_flows, cortex, liquidity_plumbing, market_core.
   Wire: `gather_btc_state` sets `state["neural_web"] = btc_slice(root)` (lazy import,
   never fatal). No synapse registration (reads existing artifacts only).
c) BTC prompt already instructs use of the NW block + stale honesty (main-loop edit).

## 6. `key_facts` vocab (deterministic chips; EXACT strings — builder implements tables as data)

Tone: `good`(green) `warn`(amber) `bad`(red) `neutral`(muted) `info`(accent/blue).
Rule: unknown/missing source value → omit the chip (≤6 shown, order below). Labels are
fixed; values come from the maps below; NEVER pass raw enum text through.

**macro** (sources: regime latest / bonds backdrop / cross_asset_confirm / market_drivers):
1. `regime` — label "Regime/市场格局". value = quad_name EN + (transition_state=="TRANSITIONING" → " · shifting"/" · 转换中"). quad_name zh map: Goldilocks→金发姑娘(不冷不热), Reflation→再通胀, Stagflation→滞胀, Deflation→通缩/放缓. tone: Goldilocks good, Reflation info, Stagflation warn, Deflation bad; any+shifting → warn.
2. `risk` — "Market risk/市场风险". macro_risk.label: low→"Low/低" good; moderate→"Moderate/中等" neutral; elevated→"Elevated/偏高" warn; severe→"Severe/严重" bad.
3. `money` — "Money/资金面". liquidity_overlay contains expand→"Expanding/扩张" good; contract→"Tightening/收紧" warn; else "Neutral/中性" neutral.
4. `bonds` — "Bonds vs stocks/债股关系". cross_asset_confirm.verdict: confirm→"Agree/一致" good; diverge→"Disagree — bonds worried/分歧 — 债市担忧" warn; mixed→"Mixed/好坏参半" neutral.
5. `credit` — "Credit/信用". bonds.credit.distress_band + direction: calm+widening→"Calm, but widening/平静但走宽" warn; calm→"Calm/平静" good; stressed→"Stressed/紧张" bad; else band prettified, neutral.
6. `driver` — "What's moving markets/当前主导". market_drivers.primary_label + direction arrow word ("down"→"— down/走弱", "up"→"— up/走强"). tone info.

**china** (sources: china/hk regime latest, china_intel policy):
1. `cn_regime` — "China regime/A股格局". quad_name map as macro + pending_quad non-null → " · shifting/ · 转换中" warn.
2. `policy` — "Policy/政策". policy impulse easing→"Cutting rates/在降息" info; tightening→"Tightening/在收紧" warn; else "On hold/按兵不动" neutral.
3. `cn_money` — "System money/系统流动性". liquidity_overlay map as macro `money`.
4. `hk_risk` — "Hong Kong/香港". hk risk_state: risk_on→"Risk-on/偏积极" good; risk_off→"Risk-off/避险" warn; else prettified neutral.
5. `peg` — "HK dollar/港元". peg_state normal/mid→"Steady/稳定" good; strong side→"At strong edge/贴近强方" info; weak side→"At weak edge — watching/贴近弱方 — 需留意" warn.
6. `cn_leader` — "Leading sector/领涨板块". top of sector_rs by rank (display name EN; zh via existing sector zh names if trivially available, else same EN name). tone info.

**btc** (sources: `_btc_signals_row` rich columns):
1. `system` — "System stance/系统姿态". composite_state: ACCUMULATE→"Accumulate/系统偏多" good; HOLD/NEUTRAL→"Hold/持有" neutral; DISTRIBUTE→"Distribute/系统减持" warn; + when alloc_optimal==0 → value suffix " · allocation 0%/ · 仓位 0%" and tone bad. override_active true → append " (override)/（人工覆盖）".
2. `cycle` — "Cycle clock/周期时钟". cycle_phase markup/markdown/accumulation/distribution → "Early rise/上行早段" good, "Late decline/下行后段" warn (markdown), "Bottoming/筑底" info, "Topping/筑顶" warn; + cphase_pct present → " · ~{pct}% through/ · 约{pct}%进度" (integer).
3. `value` — "On-chain value/链上估值". valuation_state cheap→"Cheap/偏便宜" good; fair→"Fair/中性" neutral; rich→"Expensive/偏贵" warn.
4. `leverage` — "Leverage/杠杆". leverage_stress high or funding_z>2 → "Crowded longs/多头拥挤" warn; low→"Light/清淡" good; else "Normal/正常" neutral.
5. `etf` — "ETF flows/ETF资金". etf_flow_state inflow→"Money coming in/资金流入" good; outflow→"Money leaving/资金流出" warn; else "Flat/持平" neutral.
6. `liquidity` — "Global money/全球流动性". global_liq_regime expanding→"Expanding/扩张" good; contracting→"Contracting/收缩" warn; else neutral.

Builder: implement as `LENS_KEY_FACTS: dict[str, callable]`, pure functions over the
gathered state dict (so tests can feed fixtures), attached in `run()` after `synthesize`
(brief["key_facts"] = ...). Value-map misses → prettify (`str.replace('_',' ').title()`)
+ neutral tone, never raise, never block.

## 7. Cadence

- config.yml `master_brain:` gains `interval_days_by_lens: {btc: 3}` (global
  `interval_days: 1` stays the default for macro/china).
- `run()` resolves `_interval_for(lens, cfg)` = by-lens override → global → 1, clamp 1..7.
  The existing `_brief_age_days` gate logic is reused unchanged.
- Brief payload gains `refresh_days`. All surfaces show the cadence chip:
  "Updated daily/每日更新" or "Updated every 3 days/每3天更新" — plus the existing as-of.
- Page copy updates (aibrief.html header, tab help text, dialog helpers): stop claiming
  "regenerated each day" for BTC; per-lens truthful copy.

## 8. UI contract (designer lane — doctrine + frontend-design skill both loaded)

ONE shared renderer: NEW `templates/_aibrief_body.html.j2` exposing
`{% macro aibrief_body(brief, lens, labels_ctx) %}` used by ALL FOUR surfaces
(macro dlg-aibrief, china cnx-dlg-aibrief, hk hkx-dlg-aibrief, aibrief.html tabs —
aibrief.html moves to SERVER-rendered bodies; `build_aibrief.py` loads the three brief
JSONs and passes them in; `aibrief.js` slims to the cortex panel only).
`masterbrief.js`: grep its `#master-brief` mount — if no live page mounts it, delete
template+site copies and drop any build copy references; if something mounts it, port
that surface to the shared macro instead.

Layout order (v2 body):
1. Header row (existing aib-hdr pattern) + NEW cadence micro-chip + as-of. The mandatory
   badge text "A read-through of existing signals — not a signal source /
   仅为现有信号的汇总解读 — 非独立信号源" is HOUSE LAW — never delete or alter.
2. **The gist / 要点** — tldr tick-list, large type (≥14.5px), "Head" bold-split on
   first ":" (reuse watch-row splitting idiom). The final "What to do:" item renders as
   a STANCE PILL (accent-tinted container, stance word bold) — this is the signature
   element; spend the boldness here, keep everything else quiet.
3. **Key readings / 关键读数** — the key_facts chip rail. Tone tints via
   color-mix with --up/--down/amber/--info/--muted (match existing chip idioms; light+dark
   theme safe). Chips wrap; 390 px bleed-checked.
4. Confidence meter (existing 3-seg) + as-of (ONE as-of per panel — remove dupes).
5. The full read / 完整解读 — regime_read prose (unchanged type scale).
6. Two-up grid ≥760px: "Where signals disagree/信号分歧" (amber left border) ·
   "Chain reactions/连锁反应" (blue left border) — items bold-split on first ":".
7. "Playbook check/剧本对照" full-width card — ONLY when rotation_check present.
8. "What to watch/关注事项" checklist (existing marker rows, bold-split).
9. Upcoming catalysts (macro only — existing chips; keep).
10. Footer: degraded notice (existing), disclaimer line, link-out (existing per surface).

Rules: dual-span `l-en/l-zh` everywhere; NO translated text in `title=` (CI); no `t()`
inside `<svg><text>`; CSS lives in NEW shared include `templates/_aibrief_css.j2`
(namespace `.aib2-*`; may absorb/alias existing `.aib-*` where identical) included by
china/hk/aibrief templates; dashboard.html.j2 keeps its scoped block but MUST converge to
identical rules (designer's call: either include the shared block unscoped or update the
scoped copy to byte-similar rules — pick ONE and say so in the PR body).
Word budgets are enforced upstream by the prompt; the renderer never truncates with
ellipsis on Tier 1 (wrap, don't clip). Screenshots at 1280 and 390 px, light+dark, EN+ZH
before hand-back (browser-verified against the committed site/*.json payloads — which are
still v1-shaped; every v2 field must fail-open to absent so v1 payloads render cleanly
until the first nightly).

## 9. Back-compat & failure honesty

- v1 payloads (current committed briefs) MUST render correctly in the v2 UI (no tldr →
  glance section absent, falls back to summary lead; no key_facts → no rail; no
  refresh_days → no cadence chip). The first v2 payload appears on the first nightly.
- Degraded brief (`degraded_reason`, no regime_read) renders the existing explicit
  degraded state — unchanged behavior.
- Nothing in this PR may raise into the pipeline: every new engine path wraps in the
  existing degrade-never-raise idioms.
- LLM epistemics: unchanged — the brief never feeds a score/signal/allocation; stance is
  a restatement of deterministic posture keys; key_facts are engine-computed.

## 10. Verification gate (before PR)

1. `pytest tests/test_master_brain.py tests/test_master_brain_producer.py
   tests/test_brief_context.py tests/test_aibrief_page.py tests/test_aibrief_w4_panels.py
   tests/test_master_brain_policy.py` green.
2. Template render smoke over committed JSONs (v1 payloads) — all four surfaces.
3. `python -m scripts.check_template_site_sync --fix` clean.
4. If DEEPSEEK key present: one `persist=False` forced synthesis per lens; eyeball
   style-lint pass + tldr shape. (No data/ or site/ commits from this.)
5. `git status` shows SOURCE-ONLY diff.


## 11. Chairman revamp — 2026-11-01 (ABX3)

This is the current continuation task tree for the existing AI Daily Brief, operation `ai-daily-brief-revamp-20261101-sol-001`. The current Chairman asks for a substantially more powerful and robust brief and a much better design, explicitly removing colored left container edges. Sol accepts delivery leadership in this source-linked continuation; historical authors are not treated as live writers. This section supersedes the visual ordering and colored treatment in §7–8 only where specified below. Existing research/signal separation, provider policy, brief family, deterministic input owners and the ADB deep-wire programme remain intact. No new brief producer, schedule, data store, signal engine or authority plane is created.

### Source, custody and evidence

Protected procedure: Mastermind `19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec`, Skillpack `mastermind.sol_skillpack.v1` / 1.0.1, bootstrap major 1 compatible. Macro acquisition base: `9af0a33eb38b08d902c3e593cb0e276d3f0d6a18`. Managed branch: `sol/web-ai-daily-brief-revamp-20261101-sol-001`. The initially unqualified acquire was reconciled through the same operation: clean exact-base workspace confirmed by publisher status and mmx-workspace status. No unresolved acquisition effect remains.

Current committed Macro/China briefs were generated 2026-10-18 from 2026-10-16 state; Bitcoin was generated 2026-10-18 from 2026-10-17 state. The UI says Updated daily/every 3 days although those successful refreshes have not occurred. These are source observations, not current market forecasts. Never replace their dates with a render/build date.

Open Draft #10097 remains an independent unaccepted Options Pulse carrier at `263f05509b5bd71fc4248a17316e73a34b7fce43`. Preserve its branch and effects. Its small additive integration hunks are in gather_state(), the dedicated builder, outer template and CI manifest. The shared brief body/CSS are disjoint. This operation must preserve its future append points and must not consume that draft as accepted source. Shared source changes here are narrowly scoped to normalization/persistence/reading behavior, not the Options Pulse producer.

No dedicated ADB/ABX Agent OS workstream was established by the bounded canonical census. Do not invent affiliation or mark a draft source plan as accepted organizational state. Existing Agent OS decisions on Market Orientation projection, mandatory provider rung order, and empty replies remain controlling. This task tree is source-persisted; organizational affiliation remains unresolved.

### Outcome and frozen product/design contract

The primary reader should understand the interpretation, what changed, the strength and limits of its evidence, the conflicting signals, and the next observable conditions within a coherent editorial workflow. The machine job is to present and validate the existing synthesis and deterministic readings without creating trade authority. Preserve all three lenses, dashboard dialogs, source links, forward calendar, Morning Orientation, track-record/sample-floor rules, and optional Cortex.

1. **Editorial composition.** Keep the route's editorial archetype and shared `.aib2-*` renderer. Dedicated page: existing site navigation, a restrained title and lens selector, 70–74ch reading measure, optional compact TOC only at >=1200px. Brief content precedes auxiliary calendar/context/record modules. Mobile 390px: 16px gutters, one reading column, scrollable lens strip, no page overflow; text wraps. Modal surfaces keep their existing identities, one scroll region and their existing focus/close mechanisms.
2. **Opening.** Show lens, actual source date and generated time as distinct fields; say Scheduled daily/every N days, never Updated daily without successful freshness proof. Preserve the exact house-law badge in both languages. Remove the decorative AI square, green all-caps badge and ornamental bullets/gradients. Critical stale, unavailable, malformed or partial limitations precede the thesis.
3. **The market read / 今日判断.** One strong thesis/gist; concise supporting observations. Recognize a real What to do: stance item rather than blindly taking the final list item. Label it Research posture / 研究立场 with a neutral evenly bordered surface. Do not infer stance or turn model prose into authority. Show Synthesis confidence as a qualitative assessment; unrecognized confidence is unavailable, never a fabricated low reading. Preserve detailed regime_read in an accessible Read the reasoning disclosure.
4. **What changed / 与上期相比.** Show deterministic previous-to-current reading changes only when an actual comparable prior same-lens brief exists and chronology/fields are valid. Name both source dates. No comparison => explicit comparison unavailable, not No change. Existing payloads lacking this additive field remain supported.
5. **Underlying readings / 底层读数.** Replace the colorful pill rail with compact label/value rows using existing deterministic key_facts. Short semantic value text may use existing ink tokens; borders/backgrounds are neutral. Link to existing source dashboards only where verified. Do not invent a source citation, threshold, probability or coverage score.
6. **What to watch / 接下来关注.** Prioritized source-backed trigger/meaning rows before long detail; all existing watch items remain accessible. Keep AI watch interpretations separate from deterministic Scheduled events. Retain current countdown repair and actual date semantics. Preserve Morning Orientation at a useful named destination after the main brief.
7. **Test the thesis / 检验判断.** Explicit Where signals disagree, Possible spillovers and Playbook check as editorial subsections, separated by whitespace/hairlines rather than colored boxes. Missing disagreement does not imply agreement. Preserve useful thesis falsifiers and uncertainty.
8. **Record and sources / 记录与依据.** Existing source links, track record and optional Cortex remain accessible with honest dates/status and their sample floors. Technical diagnostic strings belong in details, not the opening sentence. Do not expose raw model output or internal provider/account information in user flows.
9. **DARK TREATMENT.** Existing --bg canvas, --panel reading surface, --panel2 secondary surfaces, --line even neutral borders, --text/--muted hierarchy. Quiet luminance separation; no static glow or accent wash. Semantic ink via --ink-* only. Existing --font-ui and --fs-* scales; spacing/radius tokens with documented forward-compatible fallbacks.
10. **LIGHT TREATMENT.** White reading surface on the cool canvas, crisp neutral hairlines, soft outer shadow only, quiet secondary fill; no translucent colored washes or hand-authored light green/red overrides. Contrast and density are adjudicated independently of dark. Selected tabs use neutral fill and stronger text with full focus outlines, never a colored edge.
11. **No accent-stripe substitutes.** No colored border on any container edge, inset stripe, pseudo-element rail or relocated underline. Preserve full focus outlines and real chart series. Check stance, conflict, transmission, playbook, degraded, selected, caller/footer and auxiliary containers. No parallel token root or opaque JS-authored stylesheet. Use semantic headings, keyboard-accessible native disclosures and existing EN/ZH spans. Shared macros remain context-free; no new t() dependency.
12. **All states.** Old content remains readable but explicitly old. Missing source time is unknown, not today. Future/invalid timestamps are not fresh. Missing sections never silently become healthy/normal. Wrong JSON types, nulls, malformed translated arrays, unknown tones, hostile markup and invalid URLs must fail safely without breaking any lens. A valid partial brief remains usable. Cortex failures distinguish actual absence/error/degraded status without inventing rate limiting or silently hiding every failure.

### Reliability and additive data contract

Use the existing producer and artifacts. Prefer a small pure normalization/comparison helper with meaningful tests; normalize untrusted model/JSON fields before rendering/persistence. Keep legacy fields compatible and existing source ownership intact. Arrays must contain usable strings/known rows, translations stay index-aligned, strings are escaped, and unknown confidence/tone values remain unknown/neutral. Preserve raw source dates separately from any new render observation.

Where a newly attempted generation is empty/malformed/degraded with no usable narrative and the same lens has an actual valid previous brief, retain that last valid brief in the same canonical artifact, retaining its original generated_at/state_asof and adding truthful last-attempt status metadata. Never relabel it fresh, silently overwrite it with an empty result, or replay its old thesis/ledger emissions. A successful valid new brief can replace it and compare its deterministic readings with the valid previous record. Do not create another cache, publication owner or fallback provider. Reuse established atomic-write helpers where available; qualify root-aware temporary paths. Explicitly test failure before/after writing and do not claim multi-file transaction atomicity without proof.

Source freshness display must work on the shared renderer in every host. It may use conservative server metadata and a small progressively enhanced client clock, but stale or missing metadata must never render as Current in the static/no-JS output. Respect existing cadence without treating it as evidence of source recency. Document exactly which timestamp governs which label.

### Task tree and DONE_WHEN

| ID | Task / dependencies | Initial status | DONE_WHEN and proof |
|---|---|---|---|
| ABX3-01 | Source/collision census and frozen design | DONE | Exact pins, shared renderer, #10097 boundary and current dated artifacts recorded here; current task tree committed and read back before builder START |
| ABX3-02 | Input, chronology, comparison and retained-brief robustness; depends 01 | TODO | Legacy/valid/partial/malformed/future/old cases pass discriminating tests; no false current/normal or duplicate old ledger writes; existing provider behavior unchanged |
| ABX3-03 | Integrated editorial redesign; depends 01/02 | TODO | Dedicated route and Macro/China/HK dialogs use the same improved body; all lenses/depth retained; no accent stripe in any state; desktop/mobile dark/light EN/ZH rendered and inspected |
| ABX3-04 | Current generation-path diagnosis; independent after 01 | TODO | Trace why committed briefs stopped Oct18 using exact config/workflow/artifact evidence; repair only an established in-scope source defect, otherwise preserve exact production gate; no fabricated regeneration |
| ABX3-05 | Independent adversarial review and bounded repairs; depends 02/03 | TODO | Qualified non-author review consumes exact head/diff/tests and real paths; findings repaired and rechecked, actual screenshots and coverage matrix retained |
| ABX3-06 | Draft publication, hosted checks and lawful release; depends 05 | TODO | Reviewable original-branch PR with exact evidence, CI and independent native review; normal merge path only; deployed/browser proof before PROVEN_OUTCOME |

Allowed implementation surfaces: shared brief body/CSS; existing dedicated page and behavior JS plus paired site asset; small brief contract helper; narrow master_brain synthesis/run/translation validation or persistence hooks; existing brief loaders/host script include points only where required; focused brief tests; this spec and bounded visual evidence. Preserve global navigation, unrelated styles, provider config, signal/calibration/allocation engines, #10097 carrier and unrelated generated data. CI manifest edits only if demonstrably required to enroll meaningful tests and with current contract/ancestor-init checks; never loosen a gate/ceiling or timeout blindly.

Routing: consequential single-product/domain upgrade; direct CEO -> paid Fabric C2 bounded worker is LOWER_TOTAL_OVERHEAD because the design/contract is frozen and one source writer can integrate it. WHY NOT FABLE: no unresolved cross-program architecture or scarce principal continuity is required. Reserve independent review/repair. Native consultations are reasoning only. Fabric owns code/test labor; root owns integration and acceptance. Require worker to load protected Fabric core plus worker role, retain true root/parent and granted limits, spawn no descendants and return exact bytes/commits/test results. Foreground handle consumption is required: current Fabric has no native parent wake/background execution.

Publication stays Draft/HOLD until real review and checks qualify it. No author self-approval, manual self-merge, new production schedule or unapproved account/provider action. Green CI, a worker PASS, a screenshot and a published PR are evidence rungs, not product acceptance. Continue useful in-scope work across milestones and save this same task tree at material boundaries.

### Interactive recovery and implementation ruling — 2026-11-02

Chairman explicitly resumed delivery. The original Fabric run is now TERMINAL, root verified and lineage VERIFIED_TERMINAL, rc=1. Its complete 190-byte return (sha256 d2683e6b9a81a08ff66695353c23fb1505344fdc7fcdac68eb0be2fa6f7f1816) contains provider unrecognized_model MiniMax-M3 followed by PROVIDER_TERMINAL kind=turn_limit. It contains no implementation artifact or success claim. No retry is authorized for that run. Original controller5170 is no longer present. Direct source inspection confirms the sole assigned workspace remains clean at7e09c5006473 with no implementation commits; the original branch and PR are unchanged. This reconciles the target source, not unobserved remote sandbox activity.

Sol resumes bounded direct source implementation under CRITICAL_PATH_SHORTCUT / NO_ELIGIBLE_PRE_EFFECT_WORKER for the failed commissioned route, without rerunning or accepting the failed Fabric task. Paid independent review remains separately required; this is not authority to self-approve or merge. All implementation stays on this original branch. Existing plan and design contract remain controlling, with ABX3-02 and03 now in_progress. Editorial task labels below supersede the initial TODO/DONE shorthand:01 implementation_complete (plan only),02 in_progress,03 in_progress,04 blocked on production regeneration proof,05 proposed,06 proposed.

### ABX3 implementation milestone — 2026-11-02

The original branch now contains the editorial shared renderer, neutral token-based styling, accessible lens navigation, source-date and generation-time separation, conservative client freshness labels, dated event labeling, optional-depth sources/calendar/record/review, safe narrative escaping, defensive input normalization, same-lens deterministic reading comparisons, and last-valid retention without old-ledger replay. The provider order, signals/allocations and Options Pulse #10097 are unchanged. A pure helper in lib/aibrief_contract.py serves the existing producer and dedicated loader; no extra publisher, model route, schedule or data store is created.

Verified local candidate evidence: 176 focused tests pass, including22 new ABX3 regressions first observed failing. The original broad run had173 passes and3 obsolete presentation assertions; those assertions now check the replacement truthful copy and native-disclosure structure without dropping their safety conditions. That first run also overlapped a deliberate preview build and reported its site/aibrief.html change; the final run was sequenced after exact-path preview cleanup and passed with the data guard active. This is not a claim that the estate-wide suite has run.

The canonical capture tool produced16/16 states for the actual locally built aibrief.html: desktop1440/mobile390 × EN/ZH × dark/light, at rest and with real keyboard focus. The final light/EN desktop and dark/ZH mobile shots were visually inspected; all eight rest states and their focus partners are retained in mockups/evidence/aibrief-abx3/manifest.json. Browser assertions passed14/14 across navigation, hash/ARIA, disclosures, overflow, neutral borders, explicit optional-review failure and five labeled synthetic malformed/hostile/retained fixture inputs. These fixtures do not represent market observations. The shared Macro/China/HK template script hooks are implemented, but full host-dialog builds and production-path browser proof are still outstanding. No production or live-generation acceptance is asserted.

Design-system enforce-added reports0 blocking findings, with inherited estate findings separately reported; the existing visual-evidence checker exits0 and paired-asset synchronization checks156 pairs successfully. Fresh main729fd695836c3f4b0002b72249f80792accb9802 has no change from the acquisition base in the owned brief source/test paths queried. Screenshot provenance is the candidate working-tree bytes before commit, not a claim that the preceding plan commit contains this implementation.

Action-scoped platform boundary: one additional append to tests/test_master_brain.py was blocked with "couldn't determine the safety status of the request." It attempted three new tests for unknown-state enum fallbacks and atomic-writer file modes; it was not applied and was not retried/repackaged through another carrier. Those tests are not included in the22/176 totals. Independent review must retain the unresolved enum-fallback and file-permission questions. This is not a blanket write denial or a claim those behaviors are repaired.

Task disposition: ABX3-02 and03 implementation_complete for the candidate scope described, with the named coverage/review gaps still open;04 remains blocked on current generation/publication proof;05 ready for independent read-only review of the published exact candidate;06 blocked until that review, required CI, genuine non-author native approval and the normal release path qualify it. Keep Draft/HOLD. No author self-approval, self-merge, invented START or unattended-completion claim.

### Host integration repair and proof — 2026-11-02

The published candidate38e4d16e93a4699d7bd40b6178f602ea916f0c90 had a real integration gap outside the shared macro: host dialogs and China/HK teasers dereferenced malformed payloads before reaching its defensive renderer. Two actual-source-fragment regression tests first failed with list/string .get errors. The same carrier now always routes dialog states through the shared body and type-checks/escapes the existing teaser fields. Macro's separate news fallback remains available in an explicitly separate disclosure, never passed off as a replacement AI brief. Research/context footers and full-page link-outs remain available.

Visual inspection then found an inherited blue left stripe on the HK dialog's introductory hkx-plain callout, outside the shared renderer. A third host regression failed on that exact wrapper. It is replaced by ordinary neutral explanatory text, retaining the copy. The browser edge assertion now checks every descendant block container in the dialog, not just selected .aib2 classes. No global modal, navigation, authentication or chat-widget behavior was changed.

Proof: the broader focused run including the existing dashboard-template regression suite passed248 tests (499.45s). After the final HK-only stripe repair, all18 ABX3 UI regressions passed (13.28s); do not add these overlapping counts together. The newly added tests in this continuation are3 frontend cases, bringing the ABX3 regression set to25 including the prior7 backend cases. The previously refused3 backend-test additions remain unperformed and are NOT counted.

The actual full Macro/China/HK templates were additionally rendered with their incumbent synthetic host view-model fixtures and real committed, dated brief JSONs. All24 combinations (3 hosts ×1440/390 ×EN/ZH ×dark/light) passed actual open/close/Escape, keyboard disclosure, stale metadata, symmetric container-side boundaries and zero modal horizontal overflow. No page errors were observed in that final matrix. These are explicitly integration fixtures, not full producer builds or production acceptance. Macro's anonymous gate was first asserted closed; a synthetic registered-reader display response was then supplied only inside the local test page. No real authentication or entitlement is claimed. Final Macro light desktop, China dark/ZH mobile and repaired HK light/mobile screenshots were visually inspected by the author, not an independent taste critic.

Reproducible script: research/aibrief_v2/verify_hosts.py. Exact24 PNGs/report/source fingerprints and UI pytest output: mockups/evidence/aibrief-abx3/host-fixtures/. The earlier dedicated-page16-state capture remains applicable because its renderer/CSS/page/JS bytes did not change in this host-only repair; its precommit provenance remains recorded separately. Production browser proof, independent review and native non-author approval remain owed.

External gates, last observed: the original paid read-only review aibrief-revamp-review-20261102-01 remains ACTIVE_OR_WAITING with unverified root/worker state, despite a controller launch record; no review result or START is inferred. Do not duplicate or accept that run. Native review request is the existing Secretary thread C0CBC6AEAQZ/1793600468.848809, source brief GitHub comment6570552881; the read found no pickup reply. The existing daily run41378879186 is queued: collect completed/cancelled and engine is queued (startedAt field06:28:12Z is not evidence of an executing step). Preserve that workflow; no duplicate refresh or cancellation. The released briefs have NOT been regenerated or redeployed by this operation.

The next source action is exact-head guarded publication of this host-only repair on the original branch, then update the SAME review brief/thread with its actual SHA. Preserve the original Fabric review's38e4 head binding and adjudicate any return only against that head before deciding a lawful delta review. No observer role transfer, no new watcher, no automatic release and no self-approval or self-merge.

### Review return, confidence repair, CI coverage and publication boundary — 2026-11-02

Paid independent review aibrief-revamp-review-20261102-01 returned TERMINAL rc0 with verified original root. Its exact retained response is10876bytes, SHA256733b6bafa7c6335ce81c58b3c4f96128d4eb4d84cb639530970ebab10c55fa24. Verdict REQUEST_CHANGES / NOT_ACCEPTED is bound only to published38e4d16e93a4699d7bd40b6178f602ea916f0c90. The reviewer inspected source,15/15 evidence hashes and5 dedicated-page screenshots, gave source-level product/taste support, and did not claim native GitHub approval, full176-test execution, release or production proof. The task was not fabric_accept-ed as code approval. Its reported file-mode probe is not relied upon as authorization or completion of the three previously refused tests; those exact additions remain unperformed.

The high-severity confidence finding was independently reproduced in two distinct newly added tests: an empty provider reply and an accepted plain-language rewrite omitting confidence both falsely returned low. Both tests failed first. The local repair sets the initial assessment to None and normalizes accepted rewritten JSON before copying it. A focused122-test producer, provider-ladder, translation and shared-page run now passes (17.66s). These cases do not recreate the refused enum/file-mode additions. Other open source questions remain explicit: unknown key-fact enum fallbacks, individual atomic replacement file modes, and provider usage telemetry during a nonpersistent dry run are not claimed repaired.

Hosted contract-delta on38e4 failed in run41398748468/job125125715304, base527dc17b436e116c2ca94b6df003337e65ff8bb9. Its log identifies34 introduced path-coverage gaps:33 named jobs need lib/aibrief_contract.py, while flow-surface needs scripts/build_aibrief.py. The existing .github/ci/legacy-jobs.yml is locally widened by exactly those34 explicit paths; a parsed before/after assertion proves no commands, conditions, timeouts, weights or gate ceilings changed. Ancestor-init census remains342 pairs before/after; the existing test_ancestor_init_census_does_not_grow passes (1passed,237deselected,33.41s). No inherited gmi-explorer gap was concealed or changed. Full differential/hosted CI on these unpublished bytes has NOT run and must qualify the eventual published successor.

PUBLICATION BLOCK: the managed original-operation commit returned REFUSED / NOT_APPLIED / TYPED_GIT_PRECHECK_REFUSED, and its one read-only status diagnostic returned the same. The gateway's source maps an internal gitPublisher exception to that generic result; the actual cause is unknown, not proven credentials, permission denial or user action. A read-only liveness probe succeeded at2026-11-02T07:02:02.738Z, gateway0.1.10, generation2d957ecc-bfbf-4d3e-b7a7-af8ff69d83b8, active0/queued0. Ordinary source reads/tests remain serviceable, but that does not authorize another publication carrier. No raw git commit, alternate GitHub source write, replacement branch, source cleanup, settings change or unchanged publisher retry was attempted.

Original-target readback confirms localHEAD remains38e4d16e93a4699d7bd40b6178f602ea916f0c90; GitHubPR10486 independently remains at the same head, Draft/open, native autoMergeRequest null. Host repair/evidence is staged in the original workspace; newer confidence tests/source and this CI-path repair remain additional local modifications. NOT_CANONICALLY_PERSISTED applies to all post38e4 repairs, NOT to the already-published redesign. This local specification/evidence is not a substitute for a committed revision or Agent OS checkpoint. Preserve every local change; do not release, clean, replace, re-home or duplicate this workspace.

Exact next action: recover the existing typed publication owner's precheck through an authorized read-only diagnosis and observed recovery, without retrying the refused effect or bypassing its carrier. Then reconcile the originalHEAD/index, qualify the accumulated exact local diff, commit/push via that same managed operation, and commission an exact-successor delta/native review. Keep the native review brief/comment6570552881 and Secretary thread1793600468.848809 updated; no reviewer may approve38e4 as though the local fixes were published. Production generation remains on existing daily41378879186 (last observed engine queued), never a duplicate refresh. The observer automation remains observer-only. Release, new-head hosted CI, actual native approval, full producer/live-path freshness and final acceptance remain held.

### Publication request-schema recovery — 2026-11-02

The generic precheck cause is now resolved by exact installed-source evidence, superseding the earlier unknown-cause hypothesis. Installed integrations/studio_direct_mcp/git-publish.mjs routes the original operation through its closed repository selector, then passes arguments unchanged. Its status validator accepts only operation_id; commit accepts operation_id/expected_head_sha/message/merge; push accepts operation_id/expected_head_sha. The published tool schema still offers repository, which those installed validators reject. This is request/schema drift, not a credential or permission denial.

After rediscovering the affected schema, the corrected READ-ONLY studio_git_publish_status request omitted the optional repository argument on the SAME original operation. It succeeded with schema v1, original sol/web-ai-daily-brief-revamp-20261101-sol-001 branch, local=remote38e4d16e93a4699d7bd40b6178f602ea916f0c90, clean=false and publication_state=APPLIED (the already-published38e4 only). The unique operation resolver preserves the original Macro binding; no alternate publisher/workspace/remote, security change or service restart was used. This observed recovery permits the next exact-head same-carrier commit/push using the installed accepted argument shape. It does not imply those pending effects have occurred. Retained earlier failure and unpublished-byte evidence remains historical, and the actual successor receipt/readback must establish publication separately.

### Active completion resumed — current-main evidence repair, 2026-11-02

Current outer Chairman instruction explicitly resumes implementation/hardening rather than observer-only status. Original operation/workspace/branch and ABX3 task tree remain controlling; source ownership continuation is recorded at PR10486 comment6589595483. Protected mission pin19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec remains compatible. No live writer or unknown source effect was displaced; original workspace was clean at511c.

Actual failed-run logs41404791369 were read. Candidate-related failures were P0B same-diff receipt closure and stock-dashboard construction fingerprints. The pack8 design-governance failure was an unavailable origin/main comparison after Git fetch errors. The inherited gmi-explorer path and daily workflow-size faults are already repaired on current protected main90e0644f9f08ab37115dfffedce2ba7939b0835d (daily482604bytes; explicit describe_premises_v1.json path). That material integration need, not a behind-count ritual, justified the conflict-free merge tree db7fc37580fd089eb3eadfc41af3f06944b44800. Original typed exact-head/tree/protected-base publication committed it locally as b5ea33ee0edb4982c3d121df084d21f665dae6f8. The producer/tests and shared renderer/CSS blobs remained byte-identical, preserving the new worker's immutable input.

Parent performed the pinned-Mac browser receipt repair under UNIQUE_APPROVED_ACCESS: exact darwin/arm64 Chromium149.0.7827.55 headless-shell digest11e393326c7d20a7c56641a7c65def33ea9c280da3b0b74cf8563b07989a0ee3 was verified locally. Exact Playwright1.61.1 was installed only in a disposable task-specific /tmp dependency cache (ignore-scripts); no source dependencies, browser/font pins, capture logic or gates changed. Existing scripts/render_stock_dashboard_fixture.py rebuilt both fixtures; existing scripts/verify_stock_dashboard_mobile_layout.cjs executed both actual browsers with committed fonts and the frozen historical3fb76ea8/b4dd8fd9 baseline. HK completed0 in262.14s; Canada completed0 in255.64s. Each receipt passed48primary+16degraded owner-projection cases and8captured watch-only images, alongside its existing first-frame/navigation/disclosure/desktop checks. No hash-only evidence minting occurred.

The existing P0B manifest's current repair_extension now binds those actual returned receipts and sixteen image bytes. Historical pages/baseline and prior extensions remain preserved; this is maintenance of the incumbent evidence owner, not a replacement plane or new production claim. Full tests/test_stock_dashboard_first_frame.py passed120tests in92.40s. Existing check_p0b_receipt_closure.py exited0 against the current PR changed-path list. Existing workflow file-size suite passed3tests. No ceiling, timeout, assertion, command, browser or font qualification was loosened. HK light/mobile capture was visually inspected; it is a stock-dashboard integration fixture, not a screenshot of the new brief or current market observations.

A separate paid bounded implementation is in flight: aibrief-producer-retention-hardening-20261102-03, original root/true parent, controller98258. It owns only an isolated patch for producer exception/invalid-result retention, same-lens usable interval-cache admission and optional metadata type safety in engine/master_brain.py and existing tests. The parent workspace is reserved and untouched by that worker. It is NOT a retry of refused delta-review02; held enum/file-mode test writes/probes remain excluded. Controller delivery/launch is not proven worker START, and no worker result is accepted yet. Parent continues independent evidence/integration work; do not duplicate this assigned patch.

Fresh original daily41378879186 readback now shows completed/cancelled, engine125129836476 cancelled. Regional cluster step47 and OIP step57 were cancelled; master-brain scorer74, generator75 and AI Brief render106 were skipped. Later always-run output steps do not imply those generators executed. Current repository briefs still retain October18 generation over October16/17 source state. This is source/workflow evidence, not a bypass of the previously denied production JSON read. No duplicate nightly, new schedule, provider-route or publication owner is introduced. Current generation, independent non-author approval, hosted checks, normal release and live-browser acceptance remain owed.
