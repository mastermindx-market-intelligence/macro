# Authenticated Radar and Copilot delivery evidence — 2026-10-17

**Programme verdict: incomplete.** Authentication is now verified. The existing Radar delivers useful source dates and uncertainty disclosures. One completed, ordinary Copilot request failed the requested market-intelligence job. The merged #9517 workspace is a separate source improvement whose existing publication path must finish before it receives live acceptance.

## Capture identity and scope

The user supplied the signed-in browser and asked Sol to continue. The root inspected the existing Chrome tab at `https://www.mastermind-x.com/macro.html`; no authentication credentials, allocation changes or trades were submitted. `capture_manifest.json` binds six original screenshot/text files by SHA256. It preserves original capture filenames without manufacturing an exact timestamp that was not separately recorded.

These captures attest the **incumbent served popup**, not the newly merged workspace. The DOM referenced `risk_state_live.js?v=2b9d32d5`, `risk_envelope_live.js?v=47a6eb04` and `mm_brain.js?v=3c737978`. A subsequent fresh reload still served the incumbent popup and did not reference `risk_radar_workspace.js`. Exact production backend source identity and a cryptographic source-to-paint binding are not established by these asset labels.

## Narrow delivered capabilities accepted

The authenticated dashboard showed measured Market State **RISK_OFF / 40** and Radar **83 / Partial read**. Expanded evidence retained:

| Native component | Displayed source date | Visible qualification |
|---|---|---|
| Measured Market State | 2026-10-16 | Required current-session reading |
| Leadership cohort | 2026-10-14 | Older than this session; CRACKING |
| Cross-asset scares | 2026-10-16 | CAUTION / 83 |
| Relative leadership | 2026-10-15 | Older than this session |

The popup said rotation evidence was unavailable and that this did not establish stability. It distinguished relative strength from fund flows and acknowledged shared price/breadth lineage. The native combined stage remained null with its reason; older sources were not silently restamped. These are useful delivered qualifications. They do not establish the original warning publisher, all-state expiry/fetch behavior, predictive competence, current Terminal acceptance or full backend-to-user latency.

## Incumbent guidance losses

The overview prominently displayed **21-day 22%**, **1.24×**, and a normal baseline of **18%**. The historical evidence was thin and overlapping. The source audit separately identifies 66 matched dates and 16 historical outcomes; its interval is a historical-cell interval, not automatically uncertainty around the current model output. No accepted allocation authority follows from the displayed number.

The incumbent popup contained three sizing claims: “Use both lenses to size risk,” “the response is sizing, not selection,” and “Advisory — sizes risk.” These conflict with the retained numerical-policy boundary. This finding is version-scoped: #9517 hides the legacy footer while moving the sentiment panel, so it is incorrect to assume that all three phrases survive visibly in its new layout.

The displayed Radar category, measured state, selected scare and strongest individual scare lacked a sufficiently direct explanation of their different meanings. A headline CAUTION alongside RISK_OFF is not by itself a computational contradiction; the user needs each owner, exposure, clock and selection rule. “Live rank” also overstated older leadership context. No user-facing exposure/recovery action contract was demonstrated.

After a later fresh reload, a legacy line read “Risk pressure · 7 issued sessions · since 2026-10-08.” This belongs to the warning-context clock. It does not establish legitimate W5 prospective pullback forecast issuance or maturation. Initial and reloaded page observations are separate, and the frozen historical census is unchanged.

## One real Copilot request: failed usefulness

The root submitted exactly one ordinary question through **Ask Mastermind**, default **Fast**:

> Is this just rotation out of technology, or is it becoming a broader risk-off move? What should I protect now, what would confirm spreading danger, and what would justify re-entry? Give the source dates and explain what the 21-day 22% figure means. No portfolio percentages or trades.

After **175 seconds / 4 checks**, the entire final visible answer was:

> Evidence caveat — portfolio: not covered (contradiction present).

The final assistant DOM contained only that paragraph; this was not merely text hidden by CSS. The screenshot and text capture agree. No explanation of the market reading, source dates, 22% definition/qualification, protection priorities or re-entry conditions was delivered. No regenerate or second query was submitted.

**Acceptance: FAIL for this request.** This does not imply every Copilot answer fails. A real portfolio limitation must remain scoped to conclusions that need portfolio evidence; it cannot itself satisfy a general market-intelligence question.

The exact string is generated in Macro `engine/neuralweb/brain_gateway.py`, not the separate Mastermind portfolio service. At reviewed descendant source `15bdaec7351dbe2f1bf1a227b6e7498a8b3c0ac7`, the final assembly uses a deterministic fallback for an empty answer only when `evidence_gate_issued` is true. Otherwise, `_append_evidence_coverage_disclosure` can turn an empty answer into a caveat. This is an identified source failure path; the actual request's backend provenance, routing, specific contradiction and synthesis outcome remain under investigation. No source or policy guard was changed on this evidence alone.

## Existing #9517 source review and release custody

PR [#9517](https://github.com/mastermindx-market-intelligence/macro/pull/9517), head `ed4e02eb00bb7677a62cad1a84ab978eb1dbfc12`, merged at **11:42:43Z** as `9cfa8918b55a1c4735a90f4ca133506baa9d7966`. Its original operation retains release custody; do not duplicate its frontend or dispatch another render.

Independent read-only review of descendant `e8cb76a6cd742690584f7a16b92ca195a151a71a` used source bundle SHA256 `d4090b89b86659d0db1ec0f89cc5e34d0c6d0c7b480bb80776341611fecfb7fd`. The bounded review is accepted and closed. The new workspace explicitly identifies SPY, the ≥5% event, trading-day horizons and signal-index semantics; puts “Limited history” next to odds; explains overlapping observations; preserves native owners/nulls; and adds no polling or policy owner. It improves the existing experience.

Its `reading()` projection still drops `precision_grade`, vintage/reconstruction status, historical-cell interval, prospective qualification and independent episode support. An unmodified pure helper slice (SHA256 `179116dbf764db5337f3c96f22374cdd5551288c601ab9ce9cad591c1642a6c1`) displayed the current thin case as 22% / “Limited history · 66 observations.” A synthetic matched, non-thin case with `precision_grade:false` displayed 22% / “View evidence” without the warning class. The latter is a source-level counterexample, not an observed production packet. Qualification must come from the existing source owner, not a frontend-invented sample threshold.

At **12:50Z**, covering render `39029743025` remained in progress; successor `39032477826` was pending. The newly merged workspace had not been observed in the fresh authenticated page. Source review and sibling isolated-browser tests therefore do not constitute current production acceptance.

## #9515 integration checkpoint

The prior `126c9fa0ab67c05d970c78e91bc196ff13a24e45` CI run `39027676490` ended in failure at 11:59:03Z on the two shared recurring-briefs tests. Other scheduled packs and active main authority passed. Their source-faithful test repair had already landed in #9517; no CI exemption or authority edit was needed for this mission.

On the clean, unarmed, owned #9515 branch, root merged fetched main `e8cb76a6cd742690584f7a16b92ca195a151a71a` normally, producing `15bdaec7351dbe2f1bf1a227b6e7498a8b3c0ac7`. The sole overlap was `.github/ci/legacy-jobs.yml`; Git merged it without conflict. Original protocol and outcome commits remain ancestors. There was no rebase or census rerun.

`python3 -m pytest -q -p no:cacheprovider tests/test_recurring_briefs.py tests/test_grey_deer_exposure_census.py` passed **90 tests in 11.20 seconds**. The output SHA256 is `ac9aa77cff8415dab094bdbd3b872ceac6139bf805ee4b7e6f4ea35eacfadef2`. Two cleanup warnings concern unrelated old pytest Chromium temporary directories; those directories were not touched. Current enclosing-head hosted gates and normal source merge remain required.

## Acceptance sequence

1. Finish #9515's current source checks and ordinary expected-head merge; fetch main separately and compare owned blobs.
2. Observe #9517's existing publication and verify the changed authenticated surface, preserving prior GD-3 acceptance and sibling release custody.
3. Bind the failed Copilot request to its existing backend response record; reproduce the defect and fix it under reconciled writer custody, retaining real uncertainty and policy guards.
4. Carry native probability qualification and source-date wording through the existing presentation owner; add a supported exposure/recovery review through its existing contracts.
5. Continue the existing T13 exact-input/sample/source-purpose admission before any outcome join, fitting or trial registration. No new predictive claim or numerical policy is accepted.

The separate Mastermind #1567 clock repair remains source-merged and absent from the previously observed runtime. Its full-release qualification and canonical production decision remain separate from this Macro evidence.


## Exact backend response binding — subsequent October17 read

The existing immutable response record `68d6442e07c446ac96a8fd7fc33eaf7a`, timestamp **12:36:33Z**, contains the exact question and the same entire caveat-only answer as the browser. Its original object SHA256 is `251677488ec8cd9cfedb987bfb6668f71a1986c199b4db88db949c780771b540` (18,291 bytes). The [bounded evidence projection](runtime_response_record.json) excludes user identifiers and provider reasoning. This binds the failure to backend output, not a frontend rendering loss.

The record reports Fast/chat, model `deepseek-v4-pro`, latency **174,532ms**, and four completed read tools: `read_world_state`, `read_contradictions`, `read_factor_state` and `get_market_events`. Its synthesis phase took **104,921ms**. The same-timestamp service journal records an **EMPTY synthesis** from that model. The response ledger nevertheless records `filtered:false`, `degraded:false`, `error:false`, `screened:false`. Its top-level tools list is empty despite the four reads in latency metadata. These are additional observability and final-answer acceptance gaps. The specific portfolio classification, contradiction attribution and condition that skipped the empty-answer fallback remain under source investigation.

A later read found the Macro service active and source checkout `6a6261dff4120a690caccbba723e96f445705efe`, installed gateway SHA256 `78f4d3b320d25ff1b6b86c933fbac725fb0fe1784fe3ec7c4874564a08e926bf`. That later checkout is not automatically the exact source identity at request execution; the response log omits that binding. No service restart or production mutation was performed by this mission.
