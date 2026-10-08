---
workstream: WS:MARKET-OS
session: sol/intl-risk-consistency-20260916
model: sol
ended_because: ci_handoff
mission: >
  Make intl.html semantically truthful when the slow world-risk composite remains
  elevated but broad/fast market evidence is deteriorating, and prevent China's
  world-market tile from saying Quiet / Nothing to do while the canonical China
  leading-risk radar is loud. Preserve the raw score and all authority boundaries.
state_before: >
  Production intl.html rendered 60/100 as green Risk-on with only 6/10 markets above
  their 200-day trend, flat three-month median momentum, Japan breaking, South Korea
  carrying unresolved crash damage, and Australia/Eurozone topping. China independently
  rendered Risk-off 35/100 with a roughly 95/100 Risk Radar on china.html, while its
  intl.html tile consumed only a price-turn `calm` state and printed Quiet / Nothing to do.
  The seven core international markets could receive record-owned radars, but CN/HK were
  extra markets and China received no canonical radar context before world composition.
changed:
  - path: config.yml
    what: >
      Added display-only Risk-on confirmation thresholds for breadth, median 20-session
      momentum, stressed dial weight, and fresh loud-risk weight.
  - path: engine/intl_performance.py
    what: >
      Preserved the continuous 0-100 score but denied the green Risk-on label unless
      breadth, fast momentum, stressed-weight and fresh-loud-risk confirmation all pass;
      emits Split tape plus bilingual receipts otherwise and fixes duplicated world copy.
  - path: engine/intl_market_state.py
    what: >
      Added an additive contradiction-safe risk-context view model that preserves the
      canonical price-state enum, attaches owner radar context, exposes advisory/binding
      authority honestly, and treats stale or undated radar context as unresolved.
  - path: scripts/build_intl.py
    what: >
      Joined the seven record-owned radars plus canonical CN/HK profiles through read-only
      scorecards before world verdict composition. It never calls snapshot_and_grade,
      tuner code, or a scorecard writer; nightly remains the sole ledger advancer.
  - path: templates/intl.html.j2
    what: >
      Rendered the confirmation receipt, amber/red split semantics, contradiction-safe
      tile/table/JS display labels, stale-risk disclosure, and suppression of stale odds.
  - path: tests/test_intl_performance.py
    what: >
      Added discriminating tests for stressed-weight false green, broad fast rollover,
      fresh loud-risk denial, stale-radar non-authority, branch ordering, and bilingual copy.
  - path: tests/test_intl_build.py
    what: >
      Added China quiet+risk-alert, freshness/null, stale-odds, active-break precedence,
      read-only attachment, builder-order, and rendered-surface regressions.
  - path: tests/test_intl_recovery_quality.py
    what: >
      Updated HK wiring assertions so the pre-attached owner radar is reused rather than
      recomputed through a second path.
verified:
  - claim: The complete international test family passes on the rebased branch.
    command: /usr/local/bin/python3 -m pytest -q tests/test_intl_*.py
    result: 302 passed, 6 skipped, 60 warnings in 27.75 seconds.
  - claim: International radar profiles remain compatible.
    command: /usr/local/bin/python3 -m pytest -q tests/test_risk_radar_intl_profiles.py
    result: 12 passed.
  - claim: Existing market-score authority law remains intact.
    command: /opt/homebrew/bin/python3 -m pytest -q tests/test_market_score_authority_2026_08_12.py
    result: 16 passed.
  - claim: Confirmation tests discriminate against an unconditional green verdict.
    command: >
      Temporarily mutate risk_on_confirmed=True; run the focused fast-rollover,
      stressed-weight and fresh-loud-risk tests; restore the committed file.
    result: Mutation turned the suite red with two expected failures; committed tree restored clean.
  - claim: Builder wiring test detects loss of CN/HK context before composition.
    command: >
      Temporarily replace _attach_extra_market_risk_context with a no-op; run the
      builder-order regression; restore the committed file.
    result: Mutation failed the regression as intended; committed tree restored clean.
  - claim: Stale-odds test detects re-exposure of old drawdown probabilities.
    command: >
      Temporarily remove the `not _rd_stale` Jinja guard; run the stale-radar receipt
      regression; restore the committed template.
    result: Mutation failed the regression as intended; committed tree restored clean.
  - claim: Current carrier and review identity are durable.
    command: git log -3 --oneline; gh pr view 7202
    result: >
      PR #7202 on branch claude/intl-risk-consistency-20260916; functional head
      0d69494acb829c83fa3f47d3fd1d2eedcdb527f8 before this record update.
unverified:
  - claim: PR #7202 is merged on current main.
    what_would_verify: GitHub mergedAt and immutable merge/squash SHA readback.
  - claim: Canonical render/deploy has baked the new source into served intl.html.
    what_would_verify: Successful owning workflow plus served-page content tied to post-merge code.
  - claim: The primary persona sees Split tape rather than Risk-on on the current stressed tape.
    what_would_verify: Served embedded payload and browser-visible hero at the same production revision.
  - claim: China no longer displays a bare Quiet / Nothing to do all-clear while its radar is loud.
    what_would_verify: Served tile DOM and visual browser proof with current radar freshness receipt.
unresolved:
  - PR #7202 still needs required CI reconciliation after this handoff record update.
  - The Vercel preview is externally rate-limited and carries no product-code conclusion.
  - The inactive ci-authority/codex/merge-queue-pilot context reports failure while its receipt says allowed=true and context_active=false; required main authority remains the governing check.
  - Production render, served-page readback, and browser proof remain outstanding.
next_actions:
  - Validate this handoff with `python3 scripts/agentos.py validate` and repair any schema issue on the same branch.
  - Reconcile PR #7202 CI; fix real failures, but do not treat inactive-context or external preview-rate-limit checks as product failures.
  - Rebase the same carrier if main moves and the PR becomes dirty; never mint a duplicate PR.
  - Merge only after required checks pass and exact-head review is complete.
  - Dispatch the narrowest canonical international render/deploy workflow, then prove served JSON and visible browser state.
  - Append merge SHA, workflow run, render commit and production observations here or in an append-only closeout handoff.
do_not_redo:
  - Do not rewrite or floor the raw 0-100 score to manufacture a preferred verdict.
  - Do not create a second world-risk, China state, radar, identity, event, ledger or retry plane.
  - Do not call snapshot_and_grade, a tuner, or a scorecard writer from build_intl's extra-market path.
  - Do not interpret can_force=false as permission to hide advisory risk context.
  - Do not consume stale or undated radar probabilities as current evidence.
  - Do not let stale context hide an active breaking/crash price state.
danger_areas:
  - A plausible high slow score can remain mathematically valid while the green label is operationally false; keep score and verdict semantics distinct.
  - Freshness must be judged against the page data clock, not file mtime or wall-clock checkout time.
  - Radar context is useful before it earns binding authority, but advisory visibility must never become implicit sizing/gating authority.
  - The world hero, market tiles, comparison table, leaderboard JS, and hover receipts must project the same synthesized display state.
  - A render commit or green CI is not production acceptance; require served-page and browser-visible proof.
---
