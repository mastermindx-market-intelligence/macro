# Financial output independent review and adjudication

## Exact reviewer custody

Run `brain-output-independent-review-20261022-01`, root `brain-intelligent-output-20261021`, parent `chatgpt-brain-intelligent-output-20261021`, controller62868. Terminal rc0, root verified. Complete adapter-response SHA256 `9b16418d6b75b75689f2520151dc6bf2bf661b497ee8a7393513840635f2d152`, 8190 bytes. This review targets published checkpoint `2d5401e68f717ae00c5c84400aa75afbff19e7e6`; it is not a blanket review of later edits or a deployment receipt.

## Principal adjudication

- F1: Resolved by completing the actual primary v2 loader and formula integration. The tests remain required and unskipped. The subsequent combined targeted run passed 34 tests, including all six primary-widget cases and six newly authored legacy-chart controls cases.
- F2: Accepted. The gateway now emits only a closed membership-required notice when a valid saved exact-quote card is withheld. Both chat surfaces render fixed localized copy; no entity, quote or receipt is included in the notice. Owner and current membership checks remain in place. Regression qualification is pending at this writing.
- F3: Accepted. A single financial_visual_id helper now owns both fresh and source-reference derivations. Regression qualification is pending.
- F4: Retained as an intentional fail-closed output-protocol defense. The broader incidental-markup availability tradeoff is recorded; this change does not widen accepted tool markup or weaken the leak screen.
- F5: Retained as low-cost schema selection noise, intersected with existing authorization. No new data permission is granted by keyword selection.
- Reviewer CI observation corrected: `.github/ci/legacy-jobs.yml` is the existing packed-CI definition. Its historical `if: false` wrappers are not proof that these tests are unexecuted. The owning pack and hosted result must still be qualified on the final candidate.

## Complete independent reviewer return

Review pass complete — all evidence gathered. Compiling the final report.

---

# Independent C3 Review — Macro `2d5401e68f717ae00c5c84400aa75afbff19e7e6`

**Reviewed exact source:** public repo `mastermindx-market-intelligence/macro` serves commit `2d5401e6` (tree `d8a66c1f33eef75a223464b55e7dc2fadba650d8`, parent = assigned base `a92ee6e9`). Fetched from the public remote into a scratch clone; local object store verified byte-identical. All file reads below are from that exact commit.

**Reads (PICKUP report):** Mastermind `0454ada03` SKILL.md + references/reviewer.md ✓ · Macro AGENTS.md (414 lines, at candidate) ✓ · checkpoint spec `docs/superpowers/specs/2026-10-21-brain-intelligent-output.md` ✓ · all 51 changed files (deep reads: both new engine modules, full gateway diff, renderer/presentation/markdown/math JS, vendor/build contracts, 7 test files, CI/access/deploy/build diffs) ✓. Independence: this lane authored none of the candidate and had no part in the minimax price worker.

## Verification results (witness dimensions)

- **Mathematical equivalence (source level):** all four vendored files (`fund.ts`, `finStatementMath.ts`, `finStatements.ts`, `markets.ts`) sha256-identical to `mastermind-terminal@38723cef63e87…` (recomputed from the Terminal repo at that commit, matching `terminal-sources.json`). Build enforces digests; the built `mm_brain_finance_math_v1.js` contains no `fetch/storage/URL` owner; KaTeX bundle carries `trust:!1, strict:"error", maxExpand:200, output:"mathml", throwOnError:!0`. All manifest asset hashes, `?v=` pins, and site/templates parity verified truthful. CN cumulative → discrete differencing, EPS-never-differenced, producer-receipt precedence, family fallback **before** normalization, full-snapshot normalization before period slicing — all exercised end-to-end in real Chromium by `test_brain_financial_browser.py:28-40` (passes).
- **Tool admission / forged reader:** `read_financial_statements` is schema-undisclosed, direct model calls always denied, nested dispatch requires both `render_financial_widget` and `get_fundamentals` admitted (brain_gateway.py:7507-7512). Probed directly: forged and unvalidated `source_ref`s fail closed (`financial_source_ref_unavailable`); refs resolve only against this-turn `financial_observations`; admission, template/entity identity, transcript_id/focus relabel and current membership are rechecked on the ref path (brain_gateway.py:10195-10231). Exact quotes additionally re-gated at execution by the existing `read_earnings_evidence` entitlement branch (7304-7318).
- **Receipt binding / privacy:** `call_id` = provider tool-use block id, required; `snapshot_id == sha256(data)` enforced on every replay; model sees only the compact receipt (tests assert no bulk arrays reach model context).
- **Numeric honesty:** strict `type in (int,float)` checks (bools rejected), None→dash (never zero), price/close must be >0, unordered/duplicate bar dates rejected, no synthetic OHLC exported; CSV export neutralizes `=+-@` text formulas, quotes all cells, labels units.
- **Lifecycle:** filtered/retracted turns strip visuals before persistence on both stream and non-stream paths (12329-12335, 13886-13887); standalone page epoch/abort/account-switch handling correct.
- **Reproduction:** `test_brain_financial_views+assets+fast_presentation` 56 ✓, `browser+standalone` 16 ✓, `fast_presentation+tool_economics+visuals_integration` 90 ✓ (author's claimed evidence reproduces). Fast eligibility repair, offered-vs-admitted drift fix (`read_inflation_intelligence`), restart/access/Caddy hooks all verified.

## Findings

**F1 · MEDIUM — Red acceptance-target suite committed without any seam marker.** `tests/test_brain_financial_widget.py:17,28,48` fail 3/4 at this commit (verified locally: 3 failed, 1 passed) because the primary shared-widget v2 loader and math delimiters are not integrated (`templates/mm_brain.js` has zero finance/presentation references). The spec discloses this ("acceptance targets for that remaining seam"), but the tests carry no `xfail`/skip/gate, are wired verbatim into the browser run line (`.github/ci/legacy-jobs.yml:30269` — job currently `if: false`), and the README instructs running the shared-widget suites before release. Impact: a plain `pytest tests/` is red at the checkpoint with nothing distinguishing "declared seam" from "regression"; invites deleting the tests instead of integrating them, or masking a real widget-path regression as known-failure. Repair: `xfail(strict=True, reason="shared-widget v2 loader pending")` (or an integration flag) on the three seam tests until the loader lands.

**F2 · MEDIUM — Member-downgrade replay silently deletes saved exact-quote evidence.** `brain_gateway.py:14570-14586` + `public_financial_visuals` (brain_financial_views.py:466-470) drop `read_earnings_evidence` wires when current membership is absent; nothing marks the absence, while the retained assistant prose still asserts the quote evidence. Spec requires "absent entitlements remain visible; no invented replacements" and replay/unavailable as first-class states. Tested-intentional (`test_brain_financial_views.py:254` expects the drop) and correctly fail-closed (no leak) — the gap is contract conformance on visibility. Repair direction: emit a bounded "membership required / evidence withheld" placeholder for dropped quote wires on replay, distinct from load failure.

**F3 · LOW — Two divergent `visual_id` derivations.** Compile path hashes `[identity, visual]` (brain_financial_views.py:382); the gateway ref-reuse path hashes `identity + json(visual)` with different separators (brain_gateway.py:10225-10227). Validation checks format only, so neither is verifiable downstream (tamper-evidence correctly rests on `snapshot_id`). Audit/maintainability risk only. Repair: one shared derivation helper.

**F4 · LOW — Whole-answer replacement on incidental tool-markup mention.** `_leak_screen` (12914-12917) replaces the entire answer whenever `<tool_calls`/`<invoke` appears anywhere, with visual-specific copy even for non-visual answers; `_StreamGate.feed` (11257) buffers everything once matched. Fail-closed and tested; availability/copy-accuracy cost when a legitimate answer quotes such markup. Acceptable deliberate anti-injection stance; noting the collateral.

**F5 · LOW (observation) — Fast eligibility regex breadth.** `_fast_visible_tool_schemas` (7751-7758) adds the finance tool on the bare word `price|quote` (and `comparison` for visuals). Intersection-with-authorized only — no permission widening — but a non-market message containing "price" surfaces the tool and can produce fail-closed identity errors. Recorded as surface noise, not a defect.

**No HIGH findings.** The cross-system authority chain (gateway admission → reader rights → same-turn receipt binding → immutable normalization → replay entitlement) is coherently enforced and fails closed at every probe I could construct.

## Confirmed open seams (disclosed in spec, verified absent — not findings)

Primary `templates/mm_brain.js` v2 loader + math delimiters not integrated (standalone chat renders finance; shared-widget surfaces do not until that seam closes); ubuntu2 price-worker terminal result not imported (nothing of it present); no active CI gate executes the new suites (all 349 legacy jobs `if: false`); no deployed-byte, live-model, or entitlement proof claimed — none exists in the commit.

## Limitations

One bounded read-only pass: no live provider/model turn, no deployed host, no account-tier behavior, visual-taste/dual-theme EN-ZH evidence not adjudicated beyond fixtures (dark, 390px default; widths parametrized), esbuild reproducibility of the committed bundle accepted via pinned digests + structural spot-check rather than a rebuild. Unit/browser passes are instrument verdicts, not live acceptance.

**Disposition:** findings to the assigned operator for routine adjudication/repair (F1/F2 own the checkpoint's seam bookkeeping; F3-F5 discretionary). Not deployment-blocking on their face; this review is not release acceptance.

SESSION END: PROVEN_OUTCOME

## Post-adjudication proof

The F2/F3 repair run concluded with 58 passing source/assets/shared-widget/standalone cases. The Fabric return was accepted by reviewer against exact response SHA `9b16418d6b75b75689f2520151dc6bf2bf661b497ee8a7393513840635f2d152`, explicitly limited to the checkpoint review and this adjudication, not deployment acceptance.

The earlier native `output_contract_review` consultation returned INCOMPLETE after a paged-source/tool interruption. It read the reader module but supplied no approval or verified high/medium defect. Its outstanding questions (current quote entitlement, same-turn reference identity, immutable replay, and raw-YTD model projection) are covered by the completed independent Fabric review and direct regression evidence above. Its native quote recommendation is preserved: no alternate refetch merely to decorate an unavailable native fact.


## October 22 combined candidate qualification

The primary shared widget and standalone chat now both render the governed v2 cards, retain history notices, and typeset explicit formula delimiters. The parent-authored legacy technical-chart repairs are integrated; the inaccessible worker artifact was never imported or accepted as code. The exact existing Brain source gate passed **1,938 tests** (Python 3.12, 73.56 seconds); its full browser gate passed **143 tests** (Chromium through the installed Python 3.14 runtime, 142.86 seconds). No test was skipped or marked expected-failure to close a seam.

Canonical financial-output evidence now contains **104/104 real browser captures** across nine specimens, dark/light, EN/ZH and 1440/390 viewports, including actual hover/focus states. All pages report no console errors or failed responses. Manifest SHA256: `7e3f9c0d064f363c468347d42dda6e39bfd2478fcd3f74ddbcb9559e2054e5c7`. The first capture attempt exposed the harness selecting a hidden mobile history row; the recipe was repaired to open the actual drawer before selecting the thread, then all states were captured again. The canonical visual-evidence gate passed. This is explicitly hermetic UI evidence, with a public AAPL snapshot and clearly illustrative non-statement fixtures; no live/provider or latency claim follows.

The design-system added-line ratchet and runtime-style-injection gate also passed without changing their rules or allowances. AgentOS validation passed with 0 errors (161 pre-existing warnings). A fresh-base integration and the existing stock-dashboard first-frame remint remain required because the changed shared theme loader is pinned by those receipts. Hosted gates, deployment and real Macro/Terminal model acceptance remain open at this checkpoint.


## Fresh-base and visual integration repair

Local feature commit `7a69f39eebd43343c37d581adef8b1ccfd71e485` was combined without conflicts with main `98da0dacfae8897ce5e4c556a14820668e5ba365`. The parent visual review then found a real standalone desktop defect: the old assistant flex item shrink-wrapped a short answer and its statement to about 239px. The assistant reading column and shared visual surface now consume the available width. Two regression cases assert the actual card geometry at 390/1440, desktop table visibility and mobile compact visibility; the standalone plus asset selection passed **16/16**.

The final working-tree financial-output matrix was actually recaptured after that repair and fresh-base integration: **104/104**, no console errors or failed responses, manifest SHA256 `3c6c07f1f5ad044d18bf5e21dea5c4ba82104f00cc50dfaf0de799ea9eb99084`. The older `7e3f9c…` matrix remains recoverable from commit `7a69f39e`; it is superseded by the current matrix. The parent inspected the corrected desktop and phone standalone screenshots as well as primary price, company, formula, technical, exact-quote and summary specimens. Design-system, runtime-style and canonical visual-evidence checks passed again without waivers.

The existing HK/Canada stock-dashboard verifiers both completed successfully after the shared theme loader changed (256.80s and 254.27s). Their original historical baselines remain intact. The current wrapper binds the actual new receipt and screenshot digests and retains its previous repair extension in history. No prior screenshot is relabeled as a new observation. The wrapper and closure regression gate is being run before publication.

The post-remint first-frame, receipt-closure and committed UI-evidence selection concluded with **204 passing tests** in 73.47 seconds. The exact changed-path receipt-closure command also passed. Current HK/Canada browser-return SHA256 values are `ab0fc6a91380c3a4bd9efb4da83c172232afa5e02263cdeb48dce18238128fde` and `3e9f45cd35d5ac9fd57134184b3081975695a9faa2ba4ad5a575b9729853e3e6` respectively.

## Final native C3 consultation and source identity

Two bounded native source consultations concluded PASS with no HIGH/MED findings against the final implementation. Child Studio calls did not return source; root relayed exact source excerpts into the shared local evidence workspace, which both reviewers successfully read. This is independent candidate-source judgment based on those disclosed copies, not an independent transport, browser or test run. Root compared exact Git bytes at `08dde0f3e416cf065be63c335334da02666bc4b5` and `ce012c36ff79c6f329c6fdb7fb7259464122c21d`: widget SHA256 `cd0d7b296f835b6e52497387b224b571b3e6c8a59afcce92f85fd5db43e84050`, financial-views SHA256 `50dcdefc980069a5a9226a2ff7b7ad2de21ab45507f3f20312a2094311ecad84`, gateway SHA256 `3c392f0db52680b3e9b1d874fd7573765b931a2b0b6269a5ba7dd85beb0b3d3b`; each pair is identical.

`primary_output_final_review` covered primary loaders/mount/cleanup (lines 39-120), Markdown/math (1270-1420), history (2353-2387), retraction/finalization (2873-2916), tail recovery (2996-3025), stop/retraction (3098-3163), financial compiler/validation/notices/ID/projection (347-512), gateway preparation (10186-10240), and history ownership/entitlement (14548-14591). It found no concrete stale-rendering, script-origin, currency/code, protected-notice or visual-ID defect. Its limits are explicit: not a fresh audit of the full account-change handler, presentation-module internals, streaming scheduler or retained assistant-text entitlement policy. Existing actual account-change/stop/history browser tests remain separate evidence.

`price_controls_adversarial_final` reviewed the candidate chart functions in widget lines 1595-2198, then the clear/disposal caller excerpts and adjacent `BAR_TTL_MS = 60000` declaration. It passed the date-range/width separation, full-history indicator warmup, Monday-UTC weekly/calendar-month aggregation, measured OHLC, unknown-volume propagation, cache expiry/failure recovery and late-callback disposal checks. The addendum verified `_chartDispose` before removal and stop/retraction/finalization/history callers. No code changes or tests were performed by either consultation. Baseline-delta attribution and source equivalence rely on root's retained Git verification. The earlier final-design consultation returned INCOMPLETE and is not counted as source approval; its earlier scoped presentation PASS remains valid.

## Public source readiness and payload measurement

At `2026-10-22T11:00:06Z`, the exact new public statement adapter and compiler successfully read and validated AAPL (as of 2026-10-21, USD, 4 annual / 5 quarterly), 600519.SS (as of 2026-10-22, CNY, 6 annual / 12 quarterly), and 0700.HK (as of 2026-10-22, CNY, 6 annual / 12 quarterly). These are real public-input readiness probes, not production Brain/model or entitlement proof. Read-plus-compile durations were 547 / 588 / 565 ms from the development host and are not end-to-end latency claims.

The retained public AAPL fixture serializes to 5,307 compact UTF-8 JSON bytes on the private wire; its model-visible receipt is 518 bytes, a 90.24% reduction for that result. This is a byte measurement, not a tokenizer measurement, overall token-savings estimate or provider benchmark.

## Hosted test-budget closure

Hosted CI run `39765765346` selected the full repository suite because the dependency lockfile is a global invalidator. Its `contract-delta` job `119780696050` found exactly three introduced packing-weight breaches, with no newly selected jobs: seven added Brain suite paths add 14 estimator units to the already selected owner. The existing guard explicitly permits a measured ceiling rebase for intended coverage. `tests/test_ci_pack.py` records the exact before/after measurements and increases only each existing weight ceiling by 14; all suites, commands, selectors, job counts, pack counts and timeouts remain intact. This is test-budget accounting for added regression coverage, not an execution-time claim or a skipped check. The existing absolute packing probe passed (1 test, 100.01 seconds). The next exact-head hosted gate must pass before merge.
