---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-section11-report-d7e7a16e6c8d7299"
model: fable
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-SECTION11-REPORT"]
discoveries: ["DSC:NEWS-IMPACT-V1-REGISTRATION-INELIGIBLE-ON-MAIN"]
mission: >
  Write the section 11 report assembler that DEC:NEWS-IMPACT-SECTION11-REPORT clause 13
  requires (freeze, then assemble): a pure function from the committed registration and
  one scratch inputs file to the quality/cost report, graded through eval_grade and
  eval_receipt, with every value staying in scratch and every refusal carrying a code and
  an id, never a value.
state_before: >
  The registration was committed (#9443) and the 2026-10-15 handoff left the assembler
  unresolved. Since then Sol's #9732 bumped producer_facts to ni-producer-facts-2 and
  added require_registered_implementation, so the v1 registration refuses every consumer
  on main (DSC:NEWS-IMPACT-V1-REGISTRATION-INELIGIBLE-ON-MAIN). No other branch, PR or
  file on main carried an assembler; the news-estate seat (NE-B4 #10063, gated_v3) lists
  the assembler as frontier it watches, not work it started. Under the 2026-10-24
  leadership-continuity ruling this session, the recovered fork of the Prophet seat,
  took the assembler as current receiver and records that here.
changed:
  - path: engine/news_impact/section11_report.py
    what: >
      ni-section11-report-1. assemble(inputs, registration) checks schema, version and the
      required blocks, calls section11_registration.require_registered_implementation,
      and compares the a3 endpoints sha256 with eval_receipt's registry; validates system
      rows, gold slots, routing and transfer verdicts, costs, gold calibration and the W2
      table against the registered population, the 13-case frontier draw, the template
      critical fields, HISTORICAL_FOLDS and the registered routing sources; grades every
      system row against every scored gold slot through grade_critical_numeric_field into
      the auto-published, all-dispositions and gold-absent populations; derives group
      independence from the independence novelty on auto-published members of one group;
      builds six-way accounting per construction against the full manifest; calls
      build_receipt once over all five registry baselines and once per template stratum;
      and projects the section 11 view (bar, value, n, n_clusters, status, interval,
      crossing) with the reporting floor, too_small_at_600, the T3 stratum and the
      no-packet baselines null by name. The CLI never overwrites --out and prints only
      construction row counts and slot counts.
  - path: tests/test_news_impact_section11_report.py
    what: >
      45 synthetic tests on the committed registration with current_code_versions
      monkeypatched to HISTORICAL_V1_CODE_VERSIONS: the guard refuses drifted code and a
      mutated registration; a full-manifest happy path (142 slots, 74 clusters, measured,
      meets); the population split; group hold and violation; the T3 floor and the
      no-packet null reasons; the frontier manifest and OFF_AUDIT_SUBSET; calibration and
      W2; span-verifier failure; every refusal and duplicate code; value-free refusal
      messages; self_check; the CLI.
  - path: .github/ci/legacy-jobs.yml
    what: news-impact-contracts runs the new test file. A CI-authority edit.
  - path: research/prophet_v4/news_to_business_impact_20261006/benchmark/section11/README.md
    what: A Report section with the assembler command and the inputs file shape.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-V1-REGISTRATION-INELIGIBLE-ON-MAIN.md
    what: The v1 registration refuses on main after #9732; the route is a v2 registration plus a DEC.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: The w3 and top-level next_action name the v2 registration before the system-under-test run and the report.
verified:
  - claim: The new tests pass and the refusal codes discriminate.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_section11_report.py -q
    result: 45 passed.
  - claim: The adjacent news_impact suites still pass.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_section11_report.py tests/test_news_impact_section11.py tests/test_news_impact_eval_receipt.py tests/test_news_impact_eval_grade.py -q
    result: 305 passed.
  - claim: The v1 registration is ineligible on main.
    command: PYTHONPATH=. python3.12 -m engine.news_impact.section11_registration --check
    result: exit 1, REGISTERED_IMPLEMENTATION_MISMATCH producer_facts (registered -1, current -2) at origin/main d533508a.
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
  - claim: The assembler on real inputs.
    what_would_verify: >
      A v2 registration the guard accepts, the qwen run on the 74 v2_match cases, GLM
      gold on the 142 slots, then one CLI run into scratch.
unresolved:
  - "ni-section11-registration-2: same seeds, populations, critical slots and frontier draw, current code versions, with a DEC that records #9732 landing before any gold; until it exists no run, gold score or report is eligible on main."
  - "The system-under-test run (qwen3.7-plus, prompt-v1.2) on the 74 v2_match cases, GLM gold on all 142 slots, the third family on disagreements, seat adjudication, the gold-agreed draw (seed 20261022), stage one adjudicated, stage two, the report."
  - "gated_v3 is owned by the news-estate seat (NE-B4 #10063); its cases join section 11 only through a later registration version."
  - "A second auditor family, a MiniMax usage capture for the cost block, and a name rung for the 914 no-ticker rows."
next_actions:
  - Merge this PR on concluded green with --match-head-commit, verify landing per path, then dispatch one main baseline after the in-flight preflight.
  - "Write ni-section11-registration-2 and its DEC as a separate PR; then the qwen run into scratch; then GLM gold, the third family, adjudication and one assembler run."
do_not_redo:
  - "The assembler is written and tested; extend it through a new report_version, never by editing values into it."
  - "The v1 registration file is never regenerated in place; the guard's HISTORICAL_V1_SHA256 makes any edit a refusal."
  - "gated_v3 belongs to NE-B4 #10063; do not redraw it here."
danger_areas:
  - "System and gold outputs carry labeled values and stay in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE); the assembler's --out is a scratch path."
  - "eval_receipt's forbidden-key pattern is not word-bounded (operating, generating match); report keys avoid those words."
  - "Sol's PR #9422 touches producer.py and its tests; it is not this lane's."
---

# PROPHET-NEWS-IMPACT handoff 2026-10-30 (section 11 report assembler)

The section 11 report assembler is written and tested: registration-gated through Sol's
implementation guard, graded through eval_grade and eval_receipt, values in scratch only.
On main the v1 registration is ineligible since #9732, so the next PR is a v2 registration
with its DEC; the system-under-test run, GLM gold and the first real report follow it.
