---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-section11-reg-a0cfd19d0d0413c7"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-SECTION11-REPORT"]
discoveries: []
mission: >
  Commit the section 11 registration that DEC:NEWS-IMPACT-SECTION11-REPORT clause 13
  requires before any GLM output exists: the system under test, the gold families, the
  populations, the critical slots, both reserved draws, the A3 registration and the
  operator tap, as ids, enums, counts, seeds and sha256 pins only.
state_before: >
  The section 11 design was settled and merged (#9432, 094822ec) with seeds 20261021 and
  20261022 reserved, but nothing froze its inputs, so the GLM gold run could not start
  without a registration to score against.
changed:
  - path: engine/news_impact/section11_draws.py
    what: >
      ni-section11-draws-1. frontier_only_audit_draw takes ceil(10%) of each
      template-proxy_cell cell by sha256 rank (seed 20261021); gold_agreed_audit_draw takes
      about 40 gold-agreed slots stratified by template and agreement kind (seed
      20261022). Both are pure functions of their inputs and raise on bad input.
  - path: engine/news_impact/section11_registration.py
    what: >
      ni-section11-registration-1. Pins 22 inputs by sha256 (five must match the shas the
      code holds), joins the v2 census MATCH rows to gated_v2 cases, counts critical slots
      (queue cases from v2_queue, the rest from results_w2), draws the frontier subset,
      builds the A3 registration in confirm mode through eval_receipt.make_registration,
      copies the cascade operator tap, and refuses with a named code when a frozen count,
      id, field, key or word moves. --check compares a rebuild with the committed file.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/section11/registration.json
    what: >
      The generated registration: qwen3.7-plus prompt-v1.2 as the system under test,
      MiniMax-M3 and GLM as gold, the deepseek third-family order, v2_match 74 cases
      (T1 34, T2 36, T3 4) with the shortfall against 200, a 12-case queue, 142 critical
      slots, a frontier draw of 13 of 74, t_prospective 2026-10-15T00:00:00Z.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/section11/README.md
    what: What the registration freezes, the two commands, and how a change is made.
  - path: tests/test_news_impact_section11.py
    what: >
      33 tests on synthetic inputs: both draws (cell counts, determinism, seed dependence,
      nesting, bad input), the census join and slot-count refusal codes, the forbidden key
      and word checks, missing and changed pinned inputs, and the committed file against a
      rebuild with its seeds, populations, vendor disjointness and operator tap.
  - path: .github/ci/legacy-jobs.yml
    what: >
      news-impact-contracts runs the section 11 tests and triggers on benchmark/** so an
      edited pinned input fails the comparison. A CI-authority edit.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: The w2, w3 and top-level next_action say GLM gold covers all 142 critical slots and the registration is committed.
verified:
  - claim: The new tests pass and the refusal codes discriminate.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_section11.py -q
    result: 33 passed.
  - claim: The whole news_impact suite passes.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_*.py -q
    result: >
      1254 passed, 2 skipped. The skips are pre-existing: a raw-byte case invisible after
      json.loads, and the issuer ledger test that needs data/ in a sparse worktree.
  - claim: The committed registration equals a rebuild.
    command: PYTHONPATH=. python3.12 -m engine.news_impact.section11_registration --check
    result: "registration ok, exit 0."
  - claim: The CI job definition is valid.
    command: PYTHONPATH=. python3.12 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 0 --pack-count 12 --validate-only
    result: 319 jobs, exit 0.
  - claim: No filing text, headline, entity name or dollar figure is added.
    command: the DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE rights grep on every new file and on the added lines of every changed file
    result: no matches.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0
unverified:
  - claim: The CI run on this pull request and its landing.
    what_would_verify: >
      Concluded-green checks, gh pr merge --squash --match-head-commit, a per-path blob
      comparison against a freshly fetched origin/main, then one main ci.yml baseline
      because legacy-jobs.yml is a CI-authority path.
  - claim: Any system or gold score.
    what_would_verify: The qwen system-under-test run on the 74 v2_match cases, then GLM gold after 2026-10-19 05:16Z.
unresolved:
  - "The section 11 report assembler (pure, over eval_grade and eval_receipt.build_receipt, enforcing the registration's code versions) is not written."
  - "The gold-agreed audit draw (seed 20261022) waits on GLM and MiniMax agreement and is drawn before any system score is read."
  - "v2_match holds 74 of the 600 cases section 11 targets; gated_v3 (on or after 2026-10-20) and a name rung for the 914 no-ticker rows are the routes to more."
  - "A second auditor family and a MiniMax usage capture for the cost block."
next_actions:
  - Merge this PR on concluded green with --match-head-commit, verify landing per path, then dispatch one main baseline after the in-flight preflight.
  - "Run the system under test (qwen3.7-plus, prompt-v1.2) on the 74 v2_match cases into scratch, and write the report assembler."
  - "After 2026-10-19 05:16Z: GLM gold on all 142 slots, the registered third family on disagreements, seat adjudication, the gold-agreed draw, stage one adjudicated, stage two, and the report."
  - "On or after 2026-10-20: gated_v3 exactly as frozen in issuer_fallback/README.md."
do_not_redo:
  - "The registration's seeds, populations, critical slots and frontier draw are frozen. After GLM output exists a change needs a new registration_version and a DEC; never regenerate the committed file in place."
  - "The frontier_only_audit subset is 13 cases and is never widened."
danger_areas:
  - "System and gold outputs carry labeled values and stay in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "Editing any file under benchmark/ that the registration pins changes its sha256 and fails news-impact-contracts."
  - "Sol's PR #9422 touches producer.py and its tests; it is not this lane's."
---

# PROPHET-NEWS-IMPACT handoff 2026-10-15 (section 11 registration)

The section 11 registration is generated and tested: 74 MATCH cases, 142 critical slots,
a frontier-only audit of 13 cases and the A3 registration in confirm mode, all pinned
before any GLM output. The system-under-test run and the report assembler come next; gold
waits for GLM on 2026-10-19.
