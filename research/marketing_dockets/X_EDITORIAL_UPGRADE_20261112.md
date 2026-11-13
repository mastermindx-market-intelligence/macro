# X editorial quality and publishing upgrade

Operation: `marketing-x-editorial-upgrade-20261112-c2`.
Repository: `mastermindx-market-intelligence/macro`.
Initial source: `54465f90b32b39f704ece828638eccb5f079c397`.
Protected procedure: `Mastermind@c0b30b422d2310e614f91faed49a4adbce4291f0`, skillpack 1.0.1 / bootstrap 1.
Owner: current Chairman-assigned ChatGPT2 session; source authoring through this isolated GitHub branch. This document is a delivery companion to the existing marketing suite/content-studio plans, not another runtime or workstream registry.

## Outcome and completion standard

Upgrade the existing X marketing system so its output is useful, coherent, evidence-grounded and naturally written; its visuals are readable in a phone feed; its admin suite makes editorial decisions and delivery evidence clear. Preserve the existing source, outbox, provider, approval, cadence and publication owners.

Completion requires the actual generation/review/media/admin consumer paths, affected automated checks, normal source release, and production/browser proof. A plan, passing fixture or merged PR alone does not complete the assignment. Engagement improvement is not claimed without prospective measurements.

## Source findings and existing boundaries

- `engine/marketing/earnings_call_lane.py` appends a generic research/trading disclaimer to every candidate, including an empty-content fallback. Other voice gates already reject disclaimer endings.
- `copy_critic.py` is the existing cold-reader owner; `copy_auditor.py` owns batch review. Extend these instead of adding a competing grading service.
- `admin/static/styles.css` constrains chart previews to 200px high. The phone preview must preserve legibility and offer a full-size view.
- `admin/marketing_floor.py` and `flrLine` mix counts from different populations into a conversion funnel. Missing cohort lineage must suppress yields/loss conclusions.
- Provider booking is not confirmed public delivery. Reuse existing receipt and metric evidence; do not rewrite publication history.
- PR #7493 owns the editorial compiler in `copywriter.py`, `config/marketing.yml`, and its v2 tests. PR #8302 owns its frontier/shadow consumer. PR #7489 owns outbox/media recovery and publisher mutations. Their holds, reviews, unsettled effects and original carriers remain untouched. This phase uses separate paths and does not reproduce their held effects.
- Catalyst activation and its held flags remain with the existing WS:MARKETING-X-CATALYST-LOOP; source expansion does not enable them.

## Delivery tree

| Node | Outcome | Input / scope | Acceptance |
| --- | --- | --- | --- |
| P1 | Useful earnings-call copy | Existing committed call-event schema and earnings-call projection | No automatic disclaimer, no empty-content fallback, coherent supported qualitative content; numeric/advice/provenance/freshness/dedupe guards preserved |
| P2 | Better editorial judgment | Existing critic/auditor and intelligence writer contracts | Explain reader value, distinguish inference from facts, actionable repair reasons, no fabricated personal experience or unsupported causes; current public APIs and provider routes retained |
| P3 | Readable visual review | Existing marketing chart/render and admin media path | Large readable preview, mobile-feed preview, exact aspect ratio and safe media handling; deterministic evidence charts retain exact data |
| P4 | Trustworthy publishing suite | Existing admin projection/API/frontend | No incomparable conversion percentage, booked vs confirmed distinguished, actionable current issues separated from history, source review visible, stale retry controls match existing backend guards |
| P5 | Broader high-value content | Existing qualified dashboard source adapters | Reuse evidence-rich source families, explicit support for interpretation and visual purpose; no new data rights, provider, scheduler, duplicate source store or publication activation |
| P6 | Qualification and release | Integrated owned diff | Focused tests, dark/light and desktop/mobile UI evidence, exact-head CI and permitted incumbent release; then live proof |

P1 and P2 can proceed independently of the held editorial/compiler carriers. P3 and P4 share one root writer and are composed before UI proof. P5 follows the source-contract audit. P6 consumes each stable coherent result without declaring the parent complete early.

## Product decisions

- Facts remain traceable. Opinion means a conclusion supported by those facts, with a meaningful condition when needed. It never supplies a new price, catalyst, causal claim, target or probability.
- Remove boilerplate at its generating source; do not blindly strip quoted or deliberately required disclosures.
- Do not force every wire update into a contrarian opinion. Analytical content should answer a reader question.
- Reuse chart libraries and image machinery. Accurate charts/labels are deterministic; illustration generation must not invent quantitative evidence.
- Dark: calm graphite surfaces, restrained semantic ink. Light: cool canvas, white surfaces, clear hairlines. Both use incumbent admin/theme tokens and identical workflow semantics.
- Exact copy and media take priority; technical receipts and historical terminal records live in expandable detail. No decorative colored card edges.
- No new direct X sends, blanket approvals, account activation, spending or provider settings are part of source qualification.

## Execution and proof

Fabric capability read reports `adapter_available=false`; no worker request was submitted and no modifying worker started. Direct implementation reason: `NO_ELIGIBLE_PRE_EFFECT_WORKER` with lawful isolated GitHub source access. Native children are read-only editorial/systems architecture critics, not substitute implementation workers. WHY NOT FABLE: no additional principal or account is needed; the current assigned session integrates bounded judgment and source changes.

P1/P2 source milestone: removed the automatic earnings-call disclaimer, tone-only headline and empty-content fallback; long clauses are refused intact instead of truncated into false complete assertions. The existing cold-reader and batch auditor now distinguish a useful supported takeaway from a stat dump or slogan, with actionable reasons and a breaking-news exception. No extra model calls or provider changes were added.

Executed proof: `python -m pytest -q tests/test_marketing_earnings_call_lane.py tests/test_marketing_copy_auditor.py tests/test_marketing_copy_v2.py --tb=short` returned **376 passed, 2 skipped**. An initial sparse-source run lacked root `config.yml`; after materializing that committed dependency, the identical focused set passed. No provider/LLM call or live publication occurred. These tests prove source behavior and compatibility, not prospective post quality or engagement.

Next: compose P3/P4 admin delivery evidence, independent stage counts, review visibility and readable media, then validate their real UI consumer.


## P4 — admin evidence and review controls, local qualification

- Added read-only delivery projections: strict public X permalink, Buffer scheduled/accepted, in-flight and unconfirmed. The full folded history is counted once per item; publication time is not inferred from a provider submission timestamp.
- Removed cross-population funnel conversion/loss claims. Independent stage counts and current-plan workload are explicit.
- Carried bounded existing advisory review into the Outbox, expanded media previews, added keyboard lightbox focus/return, and retained isolated SVG-as-image rendering.
- Failed administrative retries now check the original source age before single/bulk approval or post-now dispatch. Existing lane freshness windows are reused; unscoped lanes keep their incumbent publisher checks. Old content is not rewritten or automatically resent.
- 309 admin/floor tests passed after materializing the existing app import closure. Includes strict URL parsing, full-history deduplication, no-write stale retry rejection and mixed-batch behavior. Node syntax check passed.
- Local Playwright browser launch was attempted on the isolated synthetic preview. Chromium's process singleton socket was refused by the execution environment (`Operation not permitted`); the process exited before navigation. No browser proof, user-account interaction or publication occurred. Do not repeat this launch with security-disabling flags or silently switch carriers to evade the restriction. Interface visual/interaction acceptance remains owed through an authorized execution surface.
- Existing held PR source/effect boundaries remain intact. No runtime activation, queue approval or X send was requested.

Next: qualify social chart readability and grounded analytical content, then current-head checks and normal release. Parent acceptance remains open.

## P3/P5 — social charts and evidence-grounded interpretation

- The existing chart director now opts into a 1000 × 1120 social layout. A complete evidence title, larger prices/dates and readable volume/streak values share the same original OHLCV. The longest supported title plus the one claim-specific pane preserves the price pane's 55% minimum. Unrelated MACD/profile decoration is omitted for claims that do not need it. Other render consumers retain their legacy default layout.
- Reference labels use a bounded placement search above and below occupied spans, with a leader back to the actual price when displaced. This fixes bottom-edge clamping that could obscure the last-price pill. Wide prices, title wrapping/escaping and both boundary cases have regressions; legacy SVG goldens remain unchanged.
- Chart metadata now carries a factual description and exact axis period. This is metadata only: the held media/publisher transport has not been changed, and delivered X alt text is not claimed.
- Intelligence phrasing asks for a useful supported comparison, tension or implication. It explicitly refuses invented causes, consensus, personal trade history and generic disclaimer endings. It may keep a factual wire update when no useful analytical relationship is supported.
- Copy and generated explanations are bound to their material source evidence and prompt version. A corrected brief under the same headline invalidates old analysis; repeated timestamps/source-arrival noise do not buy another call. Expired market context is also checked at serve time. The existing provider order, per-tick cap, one-call phrasing path and approval owner remain intact.
- Dashboard credit-spread facts now include their observed change, and yield-curve facts describe level and change with the correct basis-point units. Missing/nonfinite change data no longer asserts stability. These enrich the existing fact consumers; no desk, source family or publication flag has been enabled.

### Visual evidence

These are **synthetic layout examples**, not market intelligence or generated live posts. They exercise the actual director/renderer with 300 weekday bars and truthful constructed claims. The average example's last close equals its computed 50-day average; the volume example's last volume is the largest in the 90-session displayed window; the streak example has exactly five final sessions closing above their open, following a red session. Native Inkscape rendered the SVGs for visual inspection; no browser rasterizer or live X receipt is implied.

| Claim | Review artifact |
| --- | --- |
| Moving-average reference | [Average example](x_editorial_upgrade_20261112/average.svg) |
| Volume comparison | [Volume example](x_editorial_upgrade_20261112/volume.svg) |
| Consecutive sessions | [Streak example](x_editorial_upgrade_20261112/streak.svg) |

### Qualification and remaining acceptance

- Dedicated chart/regression suite: **149 passed**. JavaScript scope guard: clean; Node syntax and diff whitespace checks: clean.
- Final integrated owned-source run: **1,022 passed, 12 skipped**, one existing dependency deprecation. Command: `python -m pytest -q tests/test_marketing_earnings_call_lane.py tests/test_marketing_copy_auditor.py tests/test_marketing_copy_v2.py tests/test_admin_marketing.py tests/test_admin_marketing_floor.py tests/test_market_facts.py tests/test_marketing_anchor_law.py tests/test_marketing_intelligence_desk.py tests/test_chart_director.py tests/test_chart_render_grammar.py tests/test_chart_render_inline.py tests/test_chart_render_m2.py tests/test_admin_api_cache_recovery.py tests/test_admin_inline_handler_attrs.py tests/test_admin_js_no_undef.py tests/test_admin_navigation_ux.py --tb=short`. Skipped live-data fixtures remain unproven; no provider/model call or X send occurred.
- Expanded integrated run exposed one legacy publisher assertion that still expected raw provider URLs. The UI retains the uncertainty warning; its test now requires the validated confirmed public permalink and rejects the raw provider URL path. This preserves the original protection while checking the stronger consumer contract.
- Fresh `main` at `23b56149d8adb65328c3c2999c3bbec43a1076ed` has no intervening changes in the owned marketing paths. Current rulesets do not impose a new requirement on this branch; no CODEOWNERS file exists at the standard tracked locations. Normal exact-head CI and `merge-on-green` admission still bind.
- Shared-file custody readback: [admin workspace #9074](https://github.com/mastermindx-market-intelligence/macro/pull/9074) changes app shell/status and appends navigation tests after the existing suite; this change stays in publishing renderers and the pre-existing publisher test. [Prophet #7174](https://github.com/mastermindx-market-intelligence/macro/pull/7174) changes its separate Prophet region. [Capacity #11194](https://github.com/mastermindx-market-intelligence/macro/pull/11194) does not share these edited paths. None of those carriers, reviews, holds or runtime effects is modified or adopted.
- The connected Chrome browser exists. Opening the documented `https://admin.mastermind-x.com` verification target was blocked by Chrome because another extension UI was open. No authenticated admin interaction, successful page read, approval, publication or production acceptance resulted. This requires that extension UI to be completed or dismissed in the connected browser; another browser/device is not a workaround for the block.
- Remaining: qualified source commit and Ready PR, concluded binding CI and normal release, then actual admin desktop/mobile and dark/light interaction proof, live generation/media proof and prospective quality/engagement measurement. No audio/TTS subsystem was found or upgraded. No new generative-illustration provider or spending path was introduced.
