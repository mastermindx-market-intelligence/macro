---
workstream: "WS:LEADERSHIP-PERSISTENCE-INTELLIGENCE"
session: "Web Sol / admins-Mini-652 / sol/rotation-persistence-rph0-20260910"
model: sol
ended_because: ci_handoff
mission: >
  Continue Map Stock Rotation Regimes by measuring how the existing published US theme ordering,
  score and breadth states persist across exact NYSE-session horizons. Preserve current Sector
  Pulse, Rotation Events, Subsector Turn, GMI/ThemeState, Signal Commons, Temporal Grain and Prophet
  Entry Truth ownership; create no duplicate regime, identity, membership, half-life or trading
  authority. Freeze and execute one deterministic research-only RPH-0 vertical, adversarially review
  the real archive result, and publish one Draft/HOLD source carrier with exact evidence.
state_before: >
  Mastermind had useful current theme/sector state and theme membership work, but no source-pinned
  cross-sectional study of published theme-leadership memory. The available keep-first baskets
  archive had 41 valid snapshots from 2026-06-18 through 2026-09-09, interrupted by missing sessions
  and changing theme counts. Earlier analysis risked collapsing current rank, rank persistence,
  strict-leader residency and score pressure into one regime label. No canonical RPH workstream or
  output contract existed.
changed:
  - path: research/rotation_persistence/LEADERSHIP_PERSISTENCE_RPH0_ARCHITECTURE_FREEZE_2026-09-10.md
    what: >
      Freezes the research question, exact source, horizons, windows, null rules, bootstrap,
      transitions, censoring, authority and no-rebuild boundaries. A post-run amendment records that
      the 20-session/eight-pair temporal-shape geometry cannot mature two long cells and may not be
      post-hoc widened.
  - path: scripts/research/rotation_persistence/ and scripts/research/run_rotation_persistence_rph0.py
    what: >
      Adds strict keep-first archive normalization; exact NYSE-session pair measurements; moving-
      block intervals; honest-null rank half-life; quartile transition and censored leader-residency
      analysis; structural estimability; atomic deterministic JSON/Markdown output; and explicit
      refusal to write into existing production owner roots.
  - path: tests/test_rotation_persistence_archive.py, tests/test_rotation_persistence_metrics.py, tests/test_rotation_persistence_survival.py, tests/test_rotation_persistence_cli.py
    what: >
      Adds 50 focused cases over malformed source data, source SHA binding, exchange-session horizons,
      common-universe floors, breadth nulls, deterministic bootstrap, no forward fill, half-life
      refusal, transition continuity, left/right censoring, output authority and byte determinism.
  - path: research/rotation_persistence/results/ and research/rotation_persistence/RPH0_FINDINGS_2026-09-10.md
    what: >
      Preserves the deterministic real-archive result and bounded interpretation. Whole-ranking
      memory, strict top-quartile residency and published-score pressure remain separate dimensions;
      no output is represented as expected return, alpha, entry availability or a trade instruction.
  - path: research/rotation_persistence/evidence/
    what: >
      Preserves the complete open-PR path census, isolated mutation kills and verification receipts.
      Local contract-delta infrastructure refusal is recorded separately from any semantic verdict.
  - path: agentos/decisions/DEC-LEADERSHIP-PERSISTENCE-CROSS-OWNER-BOUNDARY.md
    what: >
      Rules that persistence stays a zero-authority research projection and that any estimable 23+
      session shape study is a separately preregistered operation rather than a relabelled RPH-0.
  - path: agentos/workstreams/WS-LEADERSHIP-PERSISTENCE-INTELLIGENCE.md
    what: >
      Creates the durable owner for this research surface, names adjacent canonical owners and holds
      RPH1 until exact-head RPH0 review is accepted.
verified:
  - claim: "The exact published source head exposes the bounded RPH-0 capability and its focused behavior is green."
    command: >
      PYTHONDONTWRITEBYTECODE=1 /Users/chriswong/lanes/venv/bin/python -m pytest
      tests/test_rotation_persistence_archive.py tests/test_rotation_persistence_metrics.py
      tests/test_rotation_persistence_survival.py tests/test_rotation_persistence_cli.py -q
      --tb=short -p no:cacheprovider
    result: "50 passed in 6.01s at source head 254641cbbe2017bd57e2ae7018417b42964cf956."
  - claim: "The real archive run is byte deterministic with one injected clock."
    command: >
      Run scripts/research/run_rotation_persistence_rph0.py twice against
      data/signal_archive/baskets.parquet with produced_at=2026-09-10T21:00:00Z; cmp result.json and
      report.md.
    result: >
      Both comparisons passed. result.json sha256
      eb6eaa16896c1582e6e8b1c6cb9d8fc03cd30cc69f145156fab2228749286b19; report.md sha256
      15e5c9142257a96cd44df3bd5542787e9a735e5a4bfe7a77b877e5f57b433c1c.
  - claim: "The focused tests kill five load-bearing false-green mutations."
    command: "PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 /tmp/rph0_mutation_runner.py"
    result: >
      5/5 mutations returned the named targeted pytest failure at exact source head
      254641cbbe2017bd57e2ae7018417b42964cf956: calendar-day horizons, missing-endpoint forward fill,
      forced non-monotone half-life, rank authority, and data-owner-root output.
  - claim: "Agent OS source records compose under the current store."
    command: "PYTHONDONTWRITEBYTECODE=1 /Users/chriswong/lanes/venv/bin/python scripts/agentos.py validate"
    result: "1,093 records, 0 errors, 45 warnings before this handoff record."
unverified:
  - claim: "The final record head passes hosted semantic CI and contract-delta."
    what_would_verify: >
      The normal GitHub workflows for Draft/HOLD PR #7064 conclude on the exact final head. The local
      contract-delta attempt produced no semantic verdict because a full detached base checkout hit
      ENOSPC with only 6.7 GiB available; its exact partial temp path/registration was cleaned.
  - claim: "An independent reviewer accepts the exact final head and the bounded statistical claims."
    what_would_verify: >
      A separate read-only reviewer checks the immutable PR head, source/result hashes, estimability
      proof, null/censoring semantics, owner boundaries, tests and hosted CI, then returns an exact-
      head verdict without modifying this branch.
  - claim: "Leadership persistence improves investment decisions or product outcomes."
    what_would_verify: >
      A separately preregistered downstream consumer study with point-in-time replay, defined utility
      metric and existing Entry Truth authority. RPH-0 itself makes no such claim.
unresolved:
  - >
    The frozen recent temporal-shape classifier is structurally unestimable: with recent_sessions=20
    and minimum_pair_count=8, horizons 10/15/20 can mature at most 10/5/0 anchors. Preserve
    INSUFFICIENT_HISTORY plus the structural reason; do not widen RPH-0 after seeing the data.
  - >
    Archive coverage is 41 of 57 expected sessions. Missing sessions reduce pair counts and censor
    episodes. The result describes existing published outputs, not complete historical raw theme
    membership or economic returns.
  - >
    Whole-ranking half-life is 14.15 sessions while strict top-Q Kaplan-Meier median residency is 3
    sessions and recent published-score pressure is negative. These are distinct measurements, not
    contradictory estimates of one hidden scalar.
next_actions:
  - >
    Finish exact final-record-head local verification and let PR #7064 hosted CI, including
    contract-delta, conclude without retry/cancel games.
  - >
    Obtain one independent immutable-head semantic/adversarial review; repair only introduced
    blockers on this same carrier and rerun exact-head evidence.
  - >
    Keep the PR Draft/HOLD. Do not mark Ready, merge, deploy or attach the result to a product,
    Prophet, Oracle or portfolio consumer in RPH-0.
  - >
    After RPH-0 is accepted, preregister RPH1 before reading its result: either an estimable recent
    window of at least 23 sessions or deeper point-in-time reconstruction stratified by breadth,
    dispersion, lifecycle and hierarchy level through existing owners.
do_not_redo:
  - "Do not create another RPH-0 branch, PR, workstream, score, state store, event plane or half-life authority."
  - "Do not reuse sol/rph0-leadership-persistence-20260910; it is a separate carrier and was not touched."
  - "Do not forward-fill archive gaps, infer missing theme rows, force a half-life, or turn missing breadth into zero."
  - "Do not relabel published-score continuation IC as economic return, alpha or a buy/sell signal."
  - "Do not post-hoc widen the frozen RPH-0 recent window or present a new label as confirmatory RPH-0 evidence."
  - "Do not move source writes off admins-Mini-652 or force-push/recreate PR #7064."
danger_areas:
  - >
    A high whole-ranking rho can coexist with fast crossing of the top-quartile boundary. Product copy
    that says a theme is stable or unstable from either number alone would be misleading.
  - >
    The moving-block interval is over eligible published-pair observations. Missing metric values are
    omitted; no claim is made that archive collection gaps are missing completely at random.
  - >
    The local Mini has about 6.7 GiB free while the repository includes a very large parquet estate.
    check_contract_delta.py currently materializes a full detached base worktree, so local ENOSPC is
    reproducible infrastructure pressure, not evidence about the candidate's contract delta.
prs: [7064]
---

# Summary

RPH-0 now has one source carrier and one Draft/HOLD PR. The real archive supports persistent broad
ordering, shorter strict-leader residence and recent score compression as separate facts. It also
falsified the estimability of the frozen temporal-shape long side before any shape label was promoted.
The research harness and records are built; exact-head hosted CI and independent review remain the
release boundary. No product or trading authority exists.
