# MarketOntology R23/R24 Current-Route Extraction Plan

> **Execution owner:** Sol on the existing Macro ontology carrier. Apply TDD task-by-task; do not create a replacement route, renderer, graph, chat host, state store, permission plane, retry plane, queue, or lifecycle.

**Goal:** Extract the accepted R23 desktop and R24 mobile experience into the existing `/ontology.html` route while preserving the current F04 owner model, exact owner truth, typed degradation, the existing Mastermind Brain, and zero request-time owner mutation.

**Architecture:** Extend the current read-only composition and paired `templates/site` ontology assets in place. The page continues to consume `ontology_explorer_snapshot.v1`; scenario/session behavior, when later enabled, remains within the four canonical F04 objects. Selected-path AI context uses the existing `MM_BRAIN_CFG.getAiContext` host seam and existing Brain widget. The implementation must never hard-code the current WTI values; all user-facing readings come from the served snapshot.

**Protected design authority:** Paper file `01M3P1X4FR6BRTB13KA736Y1HT`, page `p-1-0`; R22 `3VC-0`; R23 `44L-0`; R24 `4F5-0`; snapshot `b8e49fdf32f4ddfe5c879efd6519ce943ff2ba1314c94f0aca4c7b35da9b3813`.

**Current implementation base:** Macro `6e7ef32c1ee53f1f559035cbdd35bcdab1364d81`; ontology composer blob `387a6d9d826ede82b2cd09855b6cf030887fc354`; template HTML blob `48057ec518ca2df8e707fd250d562281961e46e4`; template JS blob `44721af35241071454b3e57a601dd221d5afd486`; template CSS blob `0998c1362f6092782343c1dbb27e5dc62a6bf785`.

---

## Task 1 — Preserve exact route and focus through sign-in

**Files**
- Modify: `tests/test_ontology_explorer_shell.py`
- Modify: `templates/ontology.js`
- Generated pair: `site/ontology.js`

1. Add a failing test that requires the sign-in `ret` value to contain `location.pathname + location.search + location.hash` while retaining the same-origin root-relative guard.
2. Run the single test and confirm the expected failure.
3. Change `signinHref()` minimally so the valid selected-leg hash survives sign-in.
4. Run the single test, route shell tests, and paired-asset sync.
5. Commit only after the slice is green.

## Task 2 — Add answer-first current-state semantics without duplicating truth

**Files**
- Modify: `tests/test_ontology_explorer_shell.py`
- Modify: `templates/ontology.js`
- Modify: `templates/ontology.css`
- Generated pairs: `site/ontology.js`, `site/ontology.css`

1. Add tests for one answer-first hero hierarchy: owner state, met/total coverage, first blocker, downstream contradiction, comparison-unavailable, source-verification state.
2. Render from `ontology_explorer_snapshot.v1` only; no fixed market values.
3. Preserve ordered path law and current typed degraded states.
4. Verify dark/light, English/Chinese, 1440/tablet/390px, visible focus, reduced motion, and 200% zoom locally.

## Task 3 — Bind selected path to the existing Mastermind Brain

**Files**
- Modify: `tests/test_ontology_explorer_shell.py`
- Modify: `tests/test_chat_widget.py` or the narrow existing Brain contract test selected after source inspection
- Modify: `templates/ontology.js`
- Modify: `templates/ontology.html.j2` only if an explicit host hook is required
- Modify: `templates/mm_brain.js` only for a generic existing-host close callback if no current return hook exists
- Generated pairs: corresponding `site/*`

1. Add failing tests for a bounded `ai_context_client.v1` block using the existing `MM_BRAIN_CFG.getAiContext` seam.
2. Bind chain id/revision, selected leg, selected receipt/value references, source revision, and return focus; never source bytes or a new persisted object.
3. Add one native Ask Mastermind action to the selected path/detail state.
4. Open the existing lazy-loaded Brain, keep one existing conversation thread, and preserve current permission handling.
5. On close, restore focus to the exact invoking leg without introducing another lifecycle system.
6. Prove no `mo_*`/ontology navigation context enters thesis/history persistence.

## Task 4 — Complete deterministic receipt, interpretation, and mobile contracts

**Files**
- Modify: ontology shell tests and current route assets only

1. Preserve VALUE/SOURCE/CALC/ABSENCE semantics through current snapshot fields and existing evidence owners.
2. Keep missing, denied, stale, unreadable, comparison-unavailable, and source-incoherent distinct.
3. Provide equivalent nonvisual values and mobile full-width actions with >=44px targets.
4. Preserve exact focus/scroll return after evidence and Brain surfaces close.

## Task 5 — Build, verify, review, and release

1. Run targeted ontology and Brain tests.
2. Run `python3 -m scripts.check_template_site_sync --fix`, then verify sync without `--fix`.
3. Run `python3 -m scripts.build_ontology_explorer`.
4. Run design-system and runtime-style-injection guards.
5. Run production-shaped local browser proof for desktop, tablet, 390px, EN/ZH, dark/light, keyboard, reduced motion, and 200% zoom.
6. Use an existing authorized browser session for production observation when available; never acquire or copy an entitlement token. On 2026-10-02 the Chairman waived waiting for an inaccessible signed-in journey, not the truthfulness of production claims or any authentication boundary. Mini2's existing Chrome session was observed to open the current WTI path without an access gate; that older served route does not prove this candidate.
7. Commit, push and continue the single PR. The Chairman assigned self-review to the active Sol session on 2026-10-02; a separate independent reviewer is not a prerequisite for this commission. Repair concrete findings and consume concluded required CI. Actual repository-protected approvals, merge authority and production-deployment controls remain gates; no self-review is represented as independent approval and no unserved candidate is called live.

## Release blockers

- Exact owner readings and first-blocker/downstream-contradiction semantics must come from the served snapshot.
- Comparison unavailable must never render as “no change.”
- 401/403/503/source-incoherent behaviors must remain typed and non-leaking.
- Brain context must be bounded, permission-preserving, nonpersistent, and exact-return capable.
- GET/request-time rendering must produce zero owner mutation.
- `templates/` and `site/` paired assets must be byte-identical at acceptance.
- Portfolio exposure remains out of this carrier until an accepted Graph-1 relationship owner exists.


## 2026-10-02 — exact-generation repair of REVIEW_8260_R1

The client now carries one transient `context.ontology_selection` reference through the existing Brain request. Its closed fields are `chain`, integer `revision`, `asof`, canonical `sha256:`-prefixed `manifest_hash`, and exact `node_id`. They are references, not source bytes, authorization or a fifth persisted F04 object. The host getter returns a copy; normal close clears it. Chart `timeframe` is no longer overloaded with an ontology revision.

Before supplying selected evidence, the gateway applies the existing `site_full` permission and existing route `ACCEPTED_CHAINS`, then compares the current composer's chain, revision, as-of time, source manifest and exact selected node. Node identifiers are not transformed or truncated for matching. A missing, malformed, denied, unadmitted or changed reference stops that selected-evidence answer and returns a deterministic bilingual refresh notice through the existing reply/SSE channel without a model call or numerical fallback. Matching definition revisions alone do not suffice.

The verified scope is the selected evidence read at that turn's start; it is not a claim that every later research tool or future turn uses a permanently frozen market state. No owner evaluation or mutation occurs. Frontend, shared widget and gateway must ship as the same accepted release, not independently copied into production.

The existing ontology CI job must explicitly run the browser suite with Chromium installed and `MM_REQUIRE_BROWSER=1`; missing browser dependencies cannot silently pass as skips. A shared `site/theme.js` change also requires actual remint of the existing HK/Canada P0b mobile-layout receipts through their current renderer and verifier. Neither gate may be waived or repaired by merely substituting hash text.
