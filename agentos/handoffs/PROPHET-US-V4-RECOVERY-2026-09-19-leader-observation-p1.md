---
workstream: WS:PROPHET-US-V4-RECOVERY
session: chatgpt/sol-prophet-leader-observation-p1-20260919
model: sol
ended_because: ci_handoff
mission: >
  Make existing leader-pullback observations visible on the real US Prophet
  surface without weakening anti-chase safety, changing candidate/plan authority,
  or creating a second access, event, publication, or lifecycle plane.
state_before: >
  The leader-pullback publisher and context consumer existed, but Prophet loaded
  leader context only after buy-board selection. Leaders omitted from buy[] were
  therefore invisible as product intelligence. The prior source-recovery carrier
  #7187 remained the stacked availability dependency.
implementation_head: a245d693b9f58a2307805992b0d075d66d692efd
pull_request: 7457
stacked_on:
  pull_request: 7187
  head: 3501db113f11273281cc72ee2db0addd06eff566
changed:
  - path: engine/us_leader_pullback_coverage.py
    what: >
      Adds one strict display-only projection and loader for LEADER, PULLBACK,
      RESET_TURN, and RESUMED rows; alphabetical no-rank ordering; typed source
      availability; casefold duplicate-identity refusal; and detached ticker-free
      summaries for the Prophet index.
  - path: scripts/build_prophet.py
    what: >
      Publishes only source/status/count summary into site/prophet/index.json.
      No leader ticker row enters candidate selection, plans, lifecycle counts, or
      plan ordering.
  - path: scripts/build_site.py, templates/dashboard.html.j2, templates/_us_leader_observation_rows.html.j2
    what: >
      Loads the same source into a separate bilingual Leaders / waiting for entry
      shelf, uses the incumbent server-side preview split and existing protected US
      payload, and rebuilds the paid hydrated grid so the existing three-row
      progressive reveal remains truthful.
  - path: config/site_access.yml, app/deploy/Caddyfile, templates/plans.html.j2
    what: >
      Reuses the existing site_full entitlement, early-enforces the raw ticker-keyed
      source, and keeps the Daily stock signals pricing statement aligned with the
      anonymous-one / Free-three / paid-full boundary.
  - path: tests/test_us_leader_observation_projection.py, tests/test_prophet_leader_observation_shelf.py, tests/test_paywall.py, tests/test_regwall_json_gate.py
    what: >
      Pins source clocks, absent/empty/degraded states, no-authority fields,
      duplicate identity, detached summaries, server-side gating, hydration density,
      pricing/access parity, and plan/candidate invariance.
verified:
  - claim: >
      The projection, product integration, identity, detached-summary, and paid
      density changes were observed RED before implementation and are green on the
      exact implementation head.
    command: >
      python3 -m pytest -q tests/test_us_leader_observation_projection.py
      tests/test_prophet_leader_observation_shelf.py
    result: 22 passed, 32 warnings in 11.62s
  - claim: >
      The wider producer, Prophet publisher, shell, candidate-board, dashboard,
      paywall, and registration-boundary regression owners remain green.
    command: >
      python3 -m pytest -q tests/test_us_leader_observation_projection.py
      tests/test_prophet_leader_observation_shelf.py
      tests/test_us_leader_pullback_coverage.py
      tests/test_prophet_anticipation_intake.py
      tests/test_p_mp1_shell_repair_round.py
      tests/test_p0_prophet_candidate_board.py
      tests/test_dashboard_template_render.py tests/test_paywall.py
      tests/test_regwall_json_gate.py
    result: 268 passed, 52 warnings in 145.71s
  - claim: Agent OS and DAG declarations remain structurally valid.
    command: >
      python3 scripts/agentos.py validate; python3
      scripts/check_dag_conformance.py --verbose
    result: >
      Agent OS: 1140 records, 0 errors, 51 pre-existing review warnings. DAG:
      27 lanes checked, OK, with two inherited documented suspect drifts.
current_state: BUILT_NOT_PROVEN
blockers:
  - >
    PR #7457 is draft and stacked on #7187. Independent submitted review and
    terminal exact-head CI remain required.
  - >
    #7187 semantic pack 5 is red only on two HK/Canada browser-receipt asset hash
    assertions that reproduce after CI resets to tested base c9d4b5626b; this is
    inherited baseline debt and is not owned by P1 or #7187.
  - >
    Production acceptance still requires authenticated anonymous/Free/paid and
    public-R2 source-serving proof plus one natural completed-session browser journey.
unresolved:
  - PR #7457 exact-head hosted CI and submitted independent review are not yet complete.
  - #7187 acceptance and the natural production journey remain dependencies.
  - Contract-delta validation is still running and is not pre-claimed.
unverified:
  - Anonymous, Free, paid, and public-R2 source-serving behavior on the deployed origin.
  - Natural completed-session source-to-shelf/payload/browser parity.
danger_areas:
  - Treating leader context as candidate, rank, lifecycle, or plan authority.
  - Exposing the raw ticker roster or hydrated paid rows outside the existing tier boundary.
  - Absorbing inherited HK/Canada receipt-hash debt into either Prophet carrier.
next_actions:
  - >
    Consume #7457 exact-head CI and independent review; repair only attributable
    findings on the same carrier.
  - >
    Integrate only after #7187 acceptance, then run authenticated source-serving
    and natural source-to-protected-payload-to-browser proof.
  - Do not promote this draft from local tests alone.
do_not_redo:
  - Do not weaken not_topped_veto or inject leader observations into buy[] or plans[].
  - Do not create another leader store, episode ledger, endpoint, entitlement, queue, or watcher.
  - Do not repeat #7187's consumed main merge.
  - Do not repair the inherited HK/Canada receipt-hash baseline debt inside either Prophet carrier.
  - Do not call PR creation, green unit tests, merge, or deployment production acceptance.
---
