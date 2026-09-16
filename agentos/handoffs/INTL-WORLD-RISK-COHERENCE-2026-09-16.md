---
workstream: "WS:INTL-WORLD-RISK-COHERENCE"
session: "Sol / claude/intl-risk-consistency-20260916"
model: "GPT-5.6 Sol Pro"
status: "PR_OPEN_PRODUCTION_PROOF_PENDING"
skillpack_repo: "mastermindx-market-intelligence/Mastermind"
skillpack_sha: "11101d420179525678449820cbfd6228191c37ee"
mission: >
  Make intl.html semantically truthful when the slow world-risk composite remains
  elevated but broad/fast market evidence is deteriorating, and prevent China's
  world-market tile from saying Quiet / Nothing to do while the canonical China
  leading-risk radar is loud.
why_it_matters: >
  A green world headline and an all-clear China tile can cause the primary persona
  to add risk while the same product is warning them to defend capital. This is a
  coherence and customer-safety defect, not merely a copy issue.
authority_precedence:
  - "Continuous world score remains the descriptive output of engine/intl_performance.py."
  - "Per-market price-turn enum remains engine/intl_market_state.py authority."
  - "CN/HK leading-risk context remains engine/risk_radar_intl.py plus its own scorecard authority."
  - "Nightly remains the sole forward-ledger and tuner advancer."
  - "The new layer changes display semantics only; it creates no score, radar, state, ledger, or gate."
verified_state:
  - "PR #7202: Fix false-green world risk and China quiet contradiction."
  - "Head at handoff creation: 0d69494acb829c83fa3f47d3fd1d2eedcdb527f8."
  - "Full international suite after rebase: 302 passed, 6 skipped."
  - "Risk-radar international profile suite: 12 passed."
  - "Market-score authority suite: 16 passed."
  - "Fences and CI authority passed; Vercel preview is externally rate-limited."
recent_prs:
  - "#7202 (open at handoff creation)"
scope:
  - "Risk-on label confirmation using breadth, median 20-session momentum, stressed dial weight, and fresh loud-risk weight."
  - "Read-only attachment of existing CN/HK radar context before world verdict composition."
  - "Contradiction-safe per-market display overlay and explicit stale/undated-radar behavior."
  - "Bilingual hero/tile copy and regression tests."
non_goals:
  - "Do not change the continuous 0-100 score formula."
  - "Do not change portfolio sizing, ranking, entry gates, or trade authority."
  - "Do not grant can_force to any radar or bypass its forward-validation gate."
  - "Do not create a second world-risk or China market-state system."
user_journey:
  - "User opens intl.html and sees the raw world score with a verdict that matches the visible breadth and fast tape."
  - "When the score is high but confirmation is weak or stress is material, the hero reads Split tape in amber and states why."
  - "China retains its price-state read, but a loud current radar prevents a bare Quiet / Nothing to do all-clear."
  - "Hover receipts disclose price state, radar state, authority status, and freshness without promoting advisory context into a forecast."
data_time_null_correction_behavior:
  - "All price and radar inputs remain causal owner-native inputs already used by the page."
  - "Freshness compares radar asof against the page as-of date; age >4 calendar days is stale."
  - "Missing or unparsable radar asof with a known page date is unresolved/stale, never implicitly fresh."
  - "Stale radar cannot hide an active breaking/crash price state and stale probability receipts are suppressed."
  - "Missing radar context fails open to the canonical price state; missing page date avoids manufacturing a false age."
  - "Corrections arrive through the existing nightly owners and are reflected on the next canonical render."
deterministic_vs_model:
  deterministic: >
    Score label confirmation, stress shares, freshness, overlay precedence,
    bilingual display fields, and all tests are deterministic Python/Jinja logic.
  model: "None in the runtime decision path."
failures_and_findings:
  - "Previous label boundary treated score >=60 as Risk-on even at exactly 60 with 6/10 breadth and flat momentum."
  - "Previous split warning only counted crash/breaking raw-cap share; topping/downtrend and loud radar context could not deny green."
  - "China was outside the seven record-owned markets and never received its canonical radar on intl.html."
  - "Previous global sentence duplicated the risk phrase in English and Chinese."
  - "Local combined country-dialog test attempt under Python 3.12 failed because that interpreter lacks Plotly; targeted suites and CI use valid dependency environments."
implementation_order:
  - "Add configurable confirmation thresholds without changing the score."
  - "Attach record-owned and CN/HK owner radars through read-only scorecards before performance composition."
  - "Synthesize additive risk-context display fields while preserving machine enums and authority."
  - "Render coherent hero/tile/table/JS states and suppress stale odds."
  - "Add discriminating unit, integration, builder-order, freshness, and bilingual-copy tests."
acceptance_and_production_proof:
  tests:
    - "302 international tests pass; 6 skipped."
    - "12 international radar-profile tests pass."
    - "16 market-score authority tests pass."
  required_live_proof:
    - "PR #7202 merged onto current main."
    - "Canonical international render/deploy lane succeeds."
    - "Served intl.html does not label the current stressed tape Risk-on."
    - "Served hero exposes breadth, 20-day momentum, and stressed/fresh-risk receipts coherently."
    - "Served China tile is not a bare Quiet / Nothing to do while its radar is caution/elevated/risk-off."
    - "Browser/DOM proof confirms the visible customer journey, not only embedded JSON."
stop_condition: >
  Stop only after merge, canonical render/deploy, served-page data proof, browser-visible
  proof, and durable recording of the production SHA/run. If a required check or deploy
  is red, repair on the same carrier; if effect is unknown, reconcile before retrying.
continuation_handoff: >
  Poll PR #7202 CI. Inspect any real failure; ignore only explicitly non-binding
  inactive-context or external preview-rate-limit checks. Merge when required checks
  pass, dispatch the narrowest canonical international render/deploy workflow, then
  verify served intl.html JSON and browser UI. Record merge SHA, workflow run, render
  commit, and production observations in this handoff or an append-only closeout.
do_not_redo:
  - "Do not rewrite the raw score to force a preferred verdict."
  - "Do not consume stale radar probabilities as current evidence."
  - "Do not call snapshot_and_grade or tuner code from build_intl's extra-market path."
  - "Do not interpret can_force=false as permission to hide advisory risk context."
---
