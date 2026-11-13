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

- Added read-only delivery projections over the incumbent telemetry owner. A strict public X permalink is a recorded destination, not confirmation. Buffer acceptance, provider-reported sending, actual visibility evidence, failure and incomplete checks remain distinct. The full folded history is counted once per item; publication time is not inferred from submission time.
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
- Expanded integrated run exposed one legacy publisher assertion that still expected raw provider URLs. The UI retains the uncertainty warning; its test now requires the validated recorded public permalink and rejects the raw provider URL path. A URL does not establish visibility.
- Fresh `main` at `23b56149d8adb65328c3c2999c3bbec43a1076ed` has no intervening changes in the owned marketing paths. Current rulesets do not impose a new requirement on this branch; no CODEOWNERS file exists at the standard tracked locations. Normal exact-head CI and `merge-on-green` admission still bind.
- Shared-file custody readback: [admin workspace #9074](https://github.com/mastermindx-market-intelligence/macro/pull/9074) changes app shell/status and appends navigation tests after the existing suite; this change stays in publishing renderers and the pre-existing publisher test. [Prophet #7174](https://github.com/mastermindx-market-intelligence/macro/pull/7174) changes its separate Prophet region. [Capacity #11194](https://github.com/mastermindx-market-intelligence/macro/pull/11194) does not share these edited paths. None of those carriers, reviews, holds or runtime effects is modified or adopted.
- The connected Chrome browser exists. Opening the documented `https://admin.mastermind-x.com` verification target was blocked by Chrome because another extension UI was open. No authenticated admin interaction, successful page read, approval, publication or production acceptance resulted. This requires that extension UI to be completed or dismissed in the connected browser; another browser/device is not a workaround for the block.
- Remaining: qualified source commit and Ready PR, concluded binding CI and normal release, then actual admin desktop/mobile and dark/light interaction proof, live generation/media proof and prospective quality/engagement measurement. No audio/TTS subsystem was found or upgraded. No new generative-illustration provider or spending path was introduced.

## P4/P6 follow-through — canonical delivery and actual code-gated coverage

Ready [PR #11196](https://github.com/mastermindx-market-intelligence/macro/pull/11196) was opened at `c8677914e615b3f1e5cb28bc8988e4eadf74c16d`. The following repair continues on that same unarmed carrier.

- The adapter now calls `telemetry.delivery_projection()` once per request. It retains the owner's historical send observation after a newer timeout and exposes stale-lookup details. It does not create another ledger or fold.
- Visibility requires a current posted receipt, matching Buffer identity, valid canonical send state, a strict destination link, an explicit boolean visibility observation and a distinct timezone-aware nonfuture observation time. A negative visibility claim needs the same dated evidence. Today's Buffer producer emits no visibility attestation, so its ordinary output remains provider-reported sending, never observed-on-X.
- Buffer-only metrics cannot attach another backend's URL or analytics through a coincident remote ID. Degraded observations cannot contribute an invalid provider URL; an independently recorded canonical receipt link can remain visible as a link.
- A newer draft/approval/notification state cannot borrow an old future booking and appear scheduled. Canonical provider status, mode, notification state and channel readiness are available in the review details.
- Recent-submission counts follow current posted status plus a provider receipt, independently of delivery classification. Learning that a provider sent a post no longer makes the submission disappear from the overview.
- Local end-to-end canonical outbox/metrics/API tests cover these cases. The exact new `unrun-marketing-desk` command executed with **566 passed, zero skipped**, one existing dependency deprecation. Node syntax and whitespace checks passed. The earlier combined exploratory candidate, including the unpublished mover phase below, passed **1,126 tests with 20 data-dependent skips**; that count is not presented as qualification of a different release tree.
- Exact-head CI found one introduced contract delta: `eval-os-a1` reached the new `admin/marketing_evidence.py` without declaring it. The path is now explicitly declared. The owned editorial/admin/chart regressions also join the existing code-gated marketing owner; live-data market-fact tests retain their nightly owner, while the new synthetic basis-point/missingness cases are named individually. No guard, timeout, provider budget or global scope is weakened.
- Catalogue custody was inspected at the current heads: #7493 changes the existing compiler-test command; #8302 appends its separate frontier step; #10656 does not modify either this marketing job or the `eval-os-a1` block. This change inserts its separate evidence step before the existing commands and adds the exact new import path. Those held changes are not adopted or overwritten.
- A full local planner probe was stopped before returning a verdict; no selection/admission result is claimed from it. Fresh hosted contract-delta and binding CI remain required on the published head. No label has been armed and no review has been self-issued.

## P7 — recover the deterministic mover/theme producer on its original compiler carrier

The latest committed plan at `23b56149d8adb65328c3c2999c3bbec43a1076ed`, produced `2026-11-12T14:53:12Z`, contains two mover candidates (CRWV/AZTA); both appear among the five auditor cuts. The CRWV producer repeats its move and appends “which is the context the number needs.” This is deterministic source behavior, not evidence of a model hallucination. The plan also records 102 validator drops and 48 overlapping number-soup reason hits; those reason hits are not a unique-candidate failure rate.

A pure reproduction with four names up 20% and twenty down 1% yields a positive 2.5% group average but only four advancers. The old theme tail can nevertheless claim that the whole group moved together. The correction measures distinct finite full-universe participation before leader selection, removes canned mover stances, and keeps exact member returns in the existing chart while the caption explains the participation.

The actual consumer trace matters: nightly `movers_desk` copy is preserved through outbox emission and send-time validation. The separate enabled `publisher_live_movers` generator still calls the old compiler banks. With the corrected breadth facts, those banks can contradict the participation and exceed the two-number gate. The shown live case is quarantined by the real queue gate; no public send was attempted or inferred.

Therefore the four-file mover/theme patch was **not published on #11196**. Its exact bytes were transferred to local staging of original [compiler PR #7493](https://github.com/mastermindx-market-intelligence/macro/pull/7493), at observed head `b38d3f8c5b73ef92510c8585d6e0f2e54fe3ae66`, to repair the producer and live compiler as one coherent source phase. The four preimages and repository AGENTS blob are identical at both staging bases. That PR remains Ready, `merge-blocked`, unarmed, with its genuine historical CHANGES_REQUESTED review intact.

Source-recovery ownership belongs to this currently assigned session. This takeover covers only the original public source carrier with expected-head publication. It does not settle, retry, restore, reuse, delete, relocate or inspect the private `ci-base-replay-wewjiqf8` execution effect (run 42597204752/job 129094800767), and it does not reopen refused controller 18876. Existing provider/B2/B3/publication holds remain. Runtime read-only roots showed no running marketing job in their bounded projection; that is not a claim of global session absence. Concurrent branch movement must be reconciled before any source publication.

The media PR #7489's Content Studio hunks are `_attach_chart_media` and the later claim-local media projection; the mover/theme caption hunk is disjoint. Its armed-plus-blocked release state is preserved. A fresh open-PR path search found no separate `publish_time_content.py` carrier; the exact changed-file inventory of #7489 does not include that helper. The theme-card subtitle's selected-count/full-universe-average mismatch can therefore be evaluated with the compiler consumer repair, without mutating the held publisher script, media transport or outbox.

Next actions: publish/read back the #11196 delivery/CI repair and observe binding CI while completing P7 on #7493; preserve every existing release hold. Actual browser acceptance remains blocked by the connected Chrome extension panel described above. Parent acceptance is still open.

## P6 exact-head dependency follow-through

Hosted contract-delta on `891ff3ba6cdc24211d2c1ffad2f402fea2bf89b5` reported one introduced uncovered path: `eval-os-a1` reaches `engine/marketing/telemetry.py` through the new adapter. [Job 131666897203](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43358671136/job/131666897203) reported zero inherited findings and unchanged packing probes. The exact existing telemetry owner is now declared beside the adapter; exclusive scope, commands, budgets and release gates remain intact. A bounded local single-owner inference probe could not derive a closure in the sparse checkout, so it supplies no admission verdict. Fresh hosted exact-head contract-delta is the remaining proof.

The latest observed `main` (`00f9f71d1f8a21ae7202cb41472d2a8eaaf6f068`) differs from the earlier checked main only in marketing ledgers and research-vault data, with no intervening owned-source change. No release label or manual publication has been applied.

## P8 — Intelligence approval and the publisher agree on media

The previous approval path queued every Intelligence Desk post with empty media and told operators that a ticker post would ship as text. The actual publisher includes `breaking` in its bare-cashtag rule, so a reviewed cashtag draft could be accepted into the queue and then quarantined for a missing picture. The old success fixture carried ticker metadata but no cashtag in the actual text, leaving that consumer mismatch untested.

The approval owner now reuses the existing renderer, card-value decision, media publisher and publisher media predicates. It preserves the exact reviewed copy. A useful card carries a hosted receipt; a successfully rendered but redundant card carries the incumbent scoped withholding receipt. Failed rendering/hosting cannot buy that exemption and refuses before enqueue/delivery. The decision scores the actual rendered headline and summary, keeps the source timestamp, adds no quote/model call and does not infer official-source status from the packet's human source-quality label. Asset identity binds the canonical item to its rendered content, so corrected source art cannot overwrite an older queued image.

Preflight uses the existing outbox owner. Exact duplicate delivery reuses the persisted original row without another render/upload; near-duplicate or prior-day candidates that were never persisted cannot be delivered. A competing enqueue is reconciled against its winning row. Legacy missing-media rows are reported for review, not rewritten into an exemption. Current resolved URLs, rather than the presence of a media entry, determine attachment status and visual-evidence credit; turning media off cannot still report an attached card.

Verification: the final exact `unrun-marketing-desk` owned evidence command passed **577 tests with zero skips**, one existing dependency deprecation. New cross-consumer cases cover the hosted, redundant, failed-render, failed-host, repeat-click, near-duplicate, competing-enqueue, legacy-row and disabled-media states. The actual card renderer's fit report and drawn SVG text are exercised, with hosting/delivery replaced by isolated receipts. No real upload, provider/model invocation or X send occurred.

A bounded static import-closure check used the incumbent tracked-path inventory and dependency analyzer at `fd51ffce95b6915a22af05d26cbf8f67020c502f`. It materialized 15 exact committed Python dependencies and found **382 named closure files, zero uncovered declared paths** for this admin module. Its 115 opaque-read annotations are retained, not treated as proof of no dynamic dependencies; fresh hosted contract-delta remains required. The earlier empty single-owner probe was caused by absent suite source in the partial checkout, not an empty dependency graph. No CI scope, timeout or guard is weakened.

P7 is saved/read back on original compiler PR #7493 at `886b0d7d6b4a5a9c5daa1f70d4ae29f3a9d382a6`; its `merge-blocked` label, prior genuine review and private effect fences remain. The connector interrupted immutable commit-object creation before any ref mutation; the original branch was read back unchanged and a bounded same-carrier object retry produced the verified parent/tree. Exactly one expected-head ref update published the source. Any unreferenced object from the interrupted call has no branch/publication effect. The private `ci-base-replay-wewjiqf8` uncertainty is separate and remains untouched.

Next: publish/read back this P8 source on #11196; finish the original compiler's one-file CI-test merge conflict against the observed current main without clearing its hold; continue exact-head CI and permitted release. Production UI/dispatch/engagement acceptance remains open.

## P9 — charge disabled desks only for observed queued posts

The screenshot's six-disabled-desks alert was a false production diagnosis. The actual plan and Sentinel report at `901d85675de4267b6e2bac74f09ac14f834ec3ba` contain 19 queued posts, the disabled roster `receipts`, `theme_desk`, `research_a`, `research_b`, `research_c`, `mastermind_research`, and zero queue entries on those disabled rows. The roster says which desks are configured off; it does not establish discarded posts or model spending.

The floor now reports an affected-post count only when a displayed plan row is disabled or its item carries the actual `account_disabled` gate reason. Sentinel stamps those reasons on the plan items. Separate reports have no immutable plan binding, and the planner reuses IDs across same-day rebuilds; even a matching account/ID and headline cannot establish identical body/source evidence. Report-only attribution is therefore refused. Multiple evidence paths count each queued post once. The remedy points to allocation and the existing Content Studio, without directing operators to activate intentionally disabled desks.

The real committed plan/report pair now produces zero disabled-desk blockers in the actual `_blockers()` consumer. Regression coverage includes an empty disabled roster, genuinely queued disabled posts, the actual plan-level gate reason, duplicate evidence, and a newer same-day report reusing the account/post ID for different copy. The final exact primary marketing code-owner command passed **582 tests, zero skips**; the final floor suite passed **41 tests**. One existing dependency deprecation remains. No config, provider, account or publishing state was changed.

A separate latent planner defect was confirmed: `enabled_rows` fell back to every row when all desks were disabled. Its one-line source repair and actual-planner regression belong to original compiler PR #7493 and are not duplicated here. That carrier's source merge is saved/read back at `7ddafc86c0fddeaed6e6b2c54455c4c4e89fe454`; GitHub reports it mergeable and ordinary PR CI has started. Its `merge-blocked` label, genuine prior review and private effect fences remain untouched.

Current next action: publish/read back P9 on the two existing source carriers, reconcile each new head's concluded binding checks, and admit #11196 to the incumbent release controller only when its required checks are clean and no hold applies. Browser acceptance still requires completion or dismissal of the open extension panel in the connected Chrome session. No production, X delivery or engagement improvement is claimed yet.
