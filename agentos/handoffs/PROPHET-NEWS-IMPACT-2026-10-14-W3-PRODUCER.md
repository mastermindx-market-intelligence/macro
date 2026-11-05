---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/prophet-ni-w3-producer"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-W3-PRODUCER"]
discoveries: ["DSC:NEWS-IMPACT-LABEL-CONTRACT-COHERENCE"]
mission: >
  Start wave w3: a Phase 1 producer that turns real documents and labeler returns into
  validated news_impact_event.v1 candidates with full emit, defer and reject accounting,
  through the owner modules only, without remapping labels, editing the frozen contract or
  writing to the shared fact log.
state_before: >
  origin/main carried the nine Phase 1 leaf modules (agreement, validate, the documents
  span binder, cluster, thesis, prophet_adapter and the rest), the frozen v1 contract and the
  w2 benchmark: 74 scorable cases, 157 graded cases and a 12-case label queue with
  two-family labels in scratch, and no third family until GLM returns on 2026-10-19 05:16Z.
  Nothing connected label returns to events.
changed:
  - path: engine/news_impact/producer.py
    what: >
      Stage one, PRODUCER_VERSION ni-producer-1. Parses each family return, ties it to the
      bundle's source sha256, replays spans, routes the two families through
      agreement.route_case, binds spans through the documents module, assembles the event and
      sends it through validate.validate_event. Every case is emitted, deferred or rejected
      with a code; the report holds counts and codes only. --shadow-single-family reads one
      family as if accepted and marks rows shadow true. --out is required.
  - path: tests/test_news_impact_producer.py
    what: 33 tests on synthetic documents and fictional issuers, covering every outcome code, the issuer tie on the routed value and the report shape.
  - path: .github/ci/legacy-jobs.yml
    what: The news-impact-contracts job runs the producer tests.
  - path: agentos/decisions/DEC-NEWS-IMPACT-W3-PRODUCER.md
    what: The two-stage split, fail closed and never remap, the issuer tie on the routed value, and the adjudicated versus shadow claims.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-LABEL-CONTRACT-COHERENCE.md
    what: The per-family shadow counts and the three reject groups (enums, cross-field conditionals, recalled issuer CIKs).
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: w3 moved to in_progress with its next_action; a do_not_redo line for stage one and its shadow runs.
verified:
  - claim: The producer tests and the whole news_impact suite pass on the current base.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_*.py -q
    result: 1145 passed, 2 skipped (33 of them in test_news_impact_producer.py), base d771d4881625.
  - claim: In adjudicated mode every graded and queue case defers to a third family; none is rejected.
    command: >
      PYTHONPATH=. python3.12 -m engine.news_impact.producer --bundles <graded bundles>
      --labels <canonical labels> --out <scratch>; the same on the 12 queue bundles
    result: 157 deferred pending_third_family, 0 emitted, 0 rejected; queue 12 deferred.
  - claim: Shadow single-family runs give the counts recorded in DSC:NEWS-IMPACT-LABEL-CONTRACT-COHERENCE.
    command: The same command with --shadow-single-family fam_a, then fam_b.
    result: graded fam_a 127 emitted (T1 44, T2 62, T3 21), fam_b 88 (T1 34, T2 36, T3 18); queue fam_a 12, fam_b 7.
  - claim: The CI pack that carries news-impact-contracts still validates.
    command: python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 4 --pack-count 12 --validate-only
    result: rc 0, 31 jobs, news-impact-contracts included.
  - claim: No filing text, headline, entity name or dollar figure is committed.
    command: grep -nE '[$][0-9]|Exact name of registrant|=== V' on every new and changed file
    result: no matches.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0
unverified:
  - claim: The CI run on this pull request and its landing.
    what_would_verify: Concluded-green checks, gh pr merge --squash --match-head-commit, a per-path blob comparison against a freshly fetched origin/main, and a green ci.yml run on a main descendant to clear the CI-authority freeze from the legacy-jobs edit.
  - claim: Any adjudicated measured packet.
    what_would_verify: A third family (GLM after 2026-10-19 05:16Z) on the 157 graded and 12 queue cases, then the producer in adjudicated mode.
unresolved:
  - "The adjudicated mode emits nothing yet: with two families, every case has at least one disputed slot and waits on a third family."
  - "Stage two is not built: rule novelty through cluster.assign_novelty, thesis append, validate_log and project to an explicit path, and the prophet_adapter assembly."
  - "The prompt does not carry the contract's enum lists or allOf rules, so single-family emit rates stay at 127 and 88 of 157 until the next prompt version."
next_actions:
  - Merge this PR on concluded green with --match-head-commit, verify landing per path, then clear the CI-authority freeze with one ci.yml baseline on main (preflight for an in-flight run first).
  - Build stage two in its own PR, writing thesis outputs only to the --out path.
  - "After 2026-10-19 05:16Z: the GLM third family on the 12 queue and 157 graded cases, then the producer in adjudicated mode and the section 11 quality/cost report."
  - "On or after 2026-10-20: gated_v3 exactly as frozen in issuer_fallback/README.md."
do_not_redo:
  - "Stage one and its rules are settled by DEC:NEWS-IMPACT-W3-PRODUCER; never add a remapping of near-miss labels or a per-family issuer reject."
  - "The shadow runs on the 157 graded and 12 queue cases are recorded; re-run them only when the labels or the producer change."
  - "The w2 labels are not relabeled; a third family extends them."
danger_areas:
  - "Producer outputs (events*.jsonl), label bundles and returns hold filing excerpts and stay in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "Never pass thesis.DEFAULT_LOG_PATH (data/news_impact/fact_log.jsonl) as an output; only the nightly advances forward ledgers."
  - "The v1 event contract is byte-frozen (DEC:NEWS-IMPACT-PHASE0-FREEZE); contract gaps go to the next version as candidates."
  - "Validation exception messages can carry label values; print only their code and path."
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w3 producer stage one)

Label returns now reach the frozen event contract through one producer that uses only
the owner modules and accounts for every case. With two families, the adjudicated mode
defers all 169 cases to a third family, which is the honest state until GLM returns.
Read one family at a time, the labels yield 127 and 88 valid events of 157; the rest miss
the contract on enums, cross-field rules and, for one family, a recalled issuer CIK. The
next prompt version is the lever for those, and stage two adds novelty, the thesis log and
the Prophet adapter.
