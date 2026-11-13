# X editorial quality and publishing upgrade

Operation: `marketing-x-editorial-upgrade-20261112-c2`.
Repository: `mastermindx-market-intelligence/macro`.
Initial source: `54465f90b32b39f704ece828638eccb5f079c397`.
Protected procedure: `Mastermind@c0b30b422d2310e614f91faed49a4adbce4291f0`, skillpack 1.0.1 / bootstrap 1.
Owner: current Chairman-assigned ChatGPT2 session; source authoring through this isolated GitHub branch. This document is a delivery companion to the existing marketing suite/content-studio plans, not another runtime or workstream registry.

Latest qualification is P13 below. Earlier next-action notes and CI/browser snapshots describe their recorded phase, not current release admission.

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

## P10 — credit events receive credit evidence before the fact cap

The parent acceptance check found one remaining source-selection gap. `_named_prints()` stopped after three builders in its general order: claims, GDPNow and median CPI. The event adapter used that selection before reading its declared driver. A credit-spread event could therefore lead with jobless claims while the valid spread and observed comparison were excluded from the writer's three facts.

For exactly the two existing widening/compressing credit-driver labels, the adapter now prefers the existing `print_hy_spread` before applying the same three-print cap. Stable ordering preserves the other prints and ordinary macro behavior. A missing preferred value retains the existing fallback; an absent/nonfinite comparison remains absent. No new data source, classifier, model route, ledger, post kind or publication flag is introduced.

The regression uses a full synthetic regime with the previously higher-ranked series present. A 3.6% spread and observed 30-basis-point change reach `event_facts()`, the actual writer context, and the unchanged numeric/copy/queued-voice checks. Displaced CPI and unselected Michigan figures do not enter the numeric whitelist. Both recognized directions, normalized label casing, missing/nonfinite level and comparison values, generic ordering and unknown-driver fallback are covered. These are fixture values, not current market claims.

Verification: **35 anchor-law tests passed**; the unchanged exact primary code-owner command passed **586 tests, zero skips**, one existing dependency deprecation. This hermetic suite is already enrolled in that owner, so no additional CI job, command, budget or dependency declaration is needed. Source diff/whitespace checks passed. The bounded source review found no additional blocker in the selector; the remaining demonstrated acceptance is live model/output/media, actual UI, release/deployment and prospective engagement proof.

P9 source and descriptions were published and read back at primary `6709dfb4300a256402bb76707d96b1a68486ecdc` and original compiler `eeafeffb442f948b0c127e890abbf7a64c6bdf8e`. Primary PR #11196 had no native review records or release labels; compiler #7493 remained `merge-blocked`. Natural exact-head CI was running; no duplicate workflow or observer was created.

The same browser tool's later access diagnostic now explicitly requires the originating browser context: “Open ChatGPT in the browser with the connected extension and try again.” No page read or browser action resulted. The completion call returned the same access error; no alternate browser/device was used. Resume UI verification in that connected browser context, completing/dismissing its earlier open extension panel if still present.

Next: publish/read back this final bounded source correction, consume its concluded binding CI through the existing GitHub run, and apply only the incumbent release admission when permitted. Preserve the compiler's review/merge hold and every original private/provider/publication effect fence. Parent completion remains false; the source milestone is not production acceptance.

## P11 — resume delivery and repair the admin restart contract

The Chairman resumed the same mission on 2026-11-13 and explicitly strengthened the natural-writing requirement. Existing source and accepted P1-P10 evidence are retained. The source carriers remain #11196 and original held compiler #7493; no replacement queue, provider, publication path or source carrier is introduced.

Natural CI run [43364581156](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43364581156) concluded for `0b4f1be063aef16fbb625576174164ac115bdfe7`. Contract-delta passed. Pack 1 identified a real deployment gap: the Intelligence approval and delivery-evidence paths now import `breaking_summary`, `chart_render`, `telemetry` and `marketing_media_backfill`, but the existing admin restart regex omitted those cached modules. The narrow existing rule now includes those four paths. Its existing positive/negative restart cases move chart rendering from the old no-admin assumption to the actual request-handler contract; unrelated API and nightly-only paths retain their exclusions.

The exact affected BioCatalyst deployment integration command passed **514 tests, three skipped**, with one existing dependency deprecation. The independently derived import-closure test passes inside that command. This is local source proof, not a service restart or deployment receipt. No production service was manually restarted.

Pack 0 also hit the expired October 12 forensics fixture. This is already repaired on main by merged [PR #11210](https://github.com/mastermindx-market-intelligence/macro/pull/11210), commit `892c65bf77218071c4f11b577e765814a45372bc`. At inspected descendant `6fd13af3fffa1b40787fa7d201ea3ae5da7aa4d6`, the test derives a fresh source day and checks both languages. No duplicate forensics patch is included. The next ordinary PR merge-input CI must consume that accepted mainline fix. The old incomplete embedded replay supplies no pass/fail verdict; its preserved checkout is not reused or cleaned.

The original compiler's separate pack-9 failure is a theme fixture missing its measured session. Its correction is being qualified on #7493, with the existing no-session refusal, actual chart requirement, prior review/merge hold and private execution fences intact. It is not migrated here.

Browser access has materially changed from P10: the connected Chrome API is now reachable. The tab bound to this conversation shows the admin sign-in form. Two other open control-room tabs are explicitly owned by other browser sessions, so they were not taken over or accessed through an alternate surface. The Chairman was told that sign-in in the available marketing tab would enable live inspection. No current queue read, approval, X send, account activation, or new inference spending resulted. The user-provided post screenshots remain examples of the writing defect, not fresh production receipts.

Next: publish/read back this restart repair, consume its fresh binding CI, and use the incumbent release controller only when qualified. In parallel, align the original writer's contradictory consequence/caption instructions and active persona examples on the compiler carrier. Full model-output, admin, release and prospective engagement acceptance remains open.

## P12 — natural-writing source published on the original compiler

The strengthened writing assignment is published and exactly read back on original [compiler PR #7493](https://github.com/mastermindx-market-intelligence/macro/pull/7493) at `e70cb16b2f5d9188c2de75cae6d6d90719f39495`, tree `178c1ea42663363bae65e595792a6f7334d80840`. Its [complete source/consumer brief](https://github.com/mastermindx-market-intelligence/macro/blob/e70cb16b2f5d9188c2de75cae6d6d90719f39495/research/marketing_dockets/X_THEME_QUALITY_RECOVERY_20261113.md) records the active prompt, configuration, shape/media, persona-example and Kelly cognitive-card alignment; explicit machine-disclaimer rejection; narrow duration-as-price protection; and the original pack-9 session-fixture repair.

The unchanged compiler code owner passed **903 tests, 2 existing skips**. The affected publisher owner passed **805 tests, zero skips**. Actual configured writer requests, parser/validators, outbox composition/readback, shape preservation and real queue voice gates execute, with explicit provider-output fixtures. Longer shapes are exercised across unknown, text-only and image-present states; the image case actually persists its synthetic attachment. This is source/consumer proof, not a live generated-post or engagement verdict. The genuine prior CHANGES_REQUESTED review, `merge-blocked` and every original private/provider/publication fence remain on #7493. Its natural exact-head CI is running, without a duplicate dispatch.

## P13 — revalidate evidence and the final approval representation

### Material acceptance findings before release

P11 head `f23648f4ed863f2fd41412da5e9d1387ef2113f5` completed natural [CI run 43390020954](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43390020954) successfully: all four packs, contract-delta and ci-gate passed. During the required release qualification, two existing consumer-acceptance comments exposed material gaps still present on that exact head:

- [Frozen snapshot expiry, comment 6842615994](https://github.com/mastermindx-market-intelligence/macro/pull/11196#issuecomment-6842615994): producer-side serve-time expiry did not protect an approval click reading an old JSON file after the producer stopped.
- [Reconciled winner's value check, comment 6843482084](https://github.com/mastermindx-market-intelligence/macro/pull/11196#issuecomment-6843482084): the winning persisted row could replace the checked candidate after enqueue without receiving its own current value check.

Both were reproduced against the unchanged production preimage by the new real-consumer regressions: the 30m01s frozen analysis and the uncited, measured-withheld race winner each returned `ok: true` when the required result was refusal (**2 failed**). These are not a claim that either race or stale approval occurred in production. The PR was returned to Draft and remained unarmed while this session repaired its original source. No release label was added or cleared.

### Reuse the existing policy at the approval boundary

`intelligence_approve` now resolves the current UTC approval clock and the existing `config/press_sources.yml → wire.intelligence` configuration, then reprojects the selected story with the producer's `_served_packet` before selecting its draft. The canonical strict `age > market_stale_min` rule, missing/bad market-stamp behavior and editorial coherence check remain the sole policy. There is no second TTL, cache or stale-data registry.

A draft removed by that projection is refused before media preparation, enqueue or delivery. A policy/import/configuration evaluation error refuses rather than passing. The stored public snapshot is unchanged. Non-market analysis is not assigned an unrelated market TTL; its ordinary language, value, source and publishing gates still apply.

New outbox rows preserve `market_as_of`, `draft_updated_at`, `story_first_seen`, `story_updated_at` and matched `evidence_published_at` in their existing source metadata. They also retain the source headline used for value comparison. `created_at` and `as_of` continue to describe queue creation. Missing source timestamps remain null, never filled with the click time. This is provenance retention, not a new freshness gate for every already queued item.

The existing value evaluation is factored into `_intel_check_value`. It evaluates the row's exact text, kind, own citation, source headline and currently resolvable media. A legacy row can retain the existing selected-story headline comparison, but a current candidate's citation or hosted card cannot give proof credit to another persisted row. The canonical outbox value policy and its enforced/shadow behavior are unchanged.

After duplicate reconciliation, a changed winning representation or changed media resolution gets the same current evaluation before delivery. An identical already checked representation reuses its result. The winner's original source, stored verdict and media bytes remain untouched; the new check is transient. The endpoint does not replace, delete, repair or re-enqueue the winner to force it through. A refusal can therefore leave the existing row on disk while withholding delivery, which is the intended preservation of its original effect.

### Executed source and consumer proof

The existing primary code-owner command completed with **608 passed, zero skipped**, one dependency deprecation, in 13.35 seconds:

```text
python -m pytest tests/test_marketing_earnings_call_lane.py tests/test_marketing_copy_auditor.py tests/test_admin_marketing.py tests/test_admin_marketing_floor.py tests/test_market_facts.py::test_credit_comparison_uses_source_precision_and_real_copy_gates tests/test_market_facts.py::test_missing_credit_comparison_does_not_claim_flat tests/test_market_facts.py::test_observed_zero_credit_change_is_distinct_from_missing tests/test_market_facts.py::test_curve_comparison_keeps_signed_spread_units tests/test_market_facts.py::test_missing_curve_change_keeps_only_the_level tests/test_marketing_anchor_law.py tests/test_marketing_intelligence_desk.py tests/test_chart_director.py -q --tb=short
```

The new tests use native story packets, canonical analysis-draft binding, SQLite storage, public JSON export, the actual approval endpoint and persisted outbox readback. Frozen snapshots are tested at 29m, exactly 30m, 30m01s, 3h, 24h and 49h. They cover a configured 10-minute boundary, missing/bad market stamps, comparison with regenerated snapshots, original clock readback, missing-clock wire compatibility and an unavailable freshness policy. Expired cases perform no media preparation or delivery and write no new row; snapshot bytes remain unchanged. A separate non-market quantified-news control passes its ordinary armed value gate without inheriting the market clock.

The eight-case winner matrix crosses pre-existing/racing arrival, hosted/measured-withheld media and citation present/absent. Winners are created through the native approval path under shadow enforcement, then encountered under armed enforcement. The losing current draft has stronger evidence, which ensures neither its citation nor its hosted card can be borrowed. Insufficient winners receive the same refusal in either timing; hosted winners and cited withheld winners remain accepted. Every case preserves the canonical winning row, and permitted delivery contains exactly that row. Rendering/hosting receipts and the final delivery boundary are isolated fixtures; no live media upload or X action is qualified.

A bounded read-only source review found no additional material stale-data, identity or compatibility regression in these repairs. Its assessment is not formal GitHub approval and ran no tests or effects; the root session owns the executed commands and publication.

### Deployment and CI dependency closure

The approval path now caches the existing Intelligence Desk and phrasing-fingerprint modules during requests. Both are added to the current admin restart expression and its explicit positive cases. The existing deployment integration command passed **516 tests, 3 existing skips**, one dependency warning, in 34.09 seconds:

```text
python -m pytest tests/test_deploy_update_self_heal.py tests/test_caddy_autosave_driver.py tests/test_macro_caddy_overlay.py tests/test_macro_caddy_publication.py -q --tb=short
```

The incumbent bounded tracked-inventory/static analyzer derives **386 named dependencies** from the changed admin module. Four exact declarations are added to the existing exclusive `eval-os-a1` owner: `intelligence_desk.py`, `intelligence_llm.py`, `tape_stamp.py` and the tracked `site/live/quotes.json` input reached through that module's static closure. The recheck reports **zero uncovered named paths**. Its **115 opaque annotations** remain limitations, not proof of complete dynamic coverage. Semantic manifest comparison confirms all **401 owners**, commands, budgets, ordering and other definitions remain identical; only those four paths change. No broad glob, new CI job, timeout increase or packing-headroom change is introduced. Fresh hosted contract-delta remains the broader exact-head proof.

### Current frontier and production return path

Publish/read back this P13 source on the same #11196 branch with expected-head CAS, restore Ready after qualification, and consume the new natural binding CI before any incumbent release opt-in. The earlier green f236 run does not qualify a changed head. The source-writing and compiler review/private-effect fences remain separate.

The incumbent post-merge path is `vps-main-sync-wake.yml` job `wake`, with the existing three-minute VPS updater as fallback. A successful wake is not served proof: it can return while the existing updater lock is held. Owed read-only production evidence is the actual merge SHA, installed descendant, current runtime snapshot/service state, served admin JS/CSS bytes matching the accepted source, and the real outbox's delivery-evidence payload. The admin runtime SHA is not inferred from the separate macro-api SHA. These source-traced interfaces do not themselves establish that a deployment occurred.

The available browser tab still requires sign-in; other open admin tabs retain their existing browser-session custody. Authenticated desktop/mobile and dark/light review, actual generated-model/media quality and prospective engagement outcomes remain unproven. No live post, queue approval, provider activation, model call or manual deployment is authorized by these test results. Parent completion remains false; continue qualified source/release and genuine consumer proof on the original carriers.
