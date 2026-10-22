---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-w3-stage2-f255ab1707a7bacd"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-W3-PRODUCER-STAGE2"]
discoveries: ["DSC:NEWS-IMPACT-ADAPTER-RANGE-BOUND"]
mission: >
  Build stage two of the W3 producer: stage-one events in; fact_log.v1 records with
  rule-assigned novelty, thesis views and Prophet evidence out, through the owner
  modules only, written to an explicit output path and never to the shared fact log,
  with every row accounted for by code.
state_before: >
  Stage one (engine/news_impact/producer.py, ni-producer-1) was merged and landed in
  #9416 (squash 342a18772ab1), and its CI-authority freeze was cleared by main baseline
  38672145756. Its shadow single-family runs had produced events for 127 and 88 of the
  157 graded cases and 12 and 7 of the 12 queue cases. Nothing turned events into fact
  log records, views or Prophet evidence.
changed:
  - path: engine/news_impact/producer_facts.py
    what: >
      Stage two, PRODUCER_FACTS_VERSION ni-producer-facts-1. Keys each event to a
      fact_log.v1 fact_key, builds the leaf payload and owner quantity fingerprint,
      assigns novelty through cluster.assign_novelty, appends one record at a time
      through thesis.append_records, projects views with thesis.project and assembles
      Prophet evidence per event with prophet_adapter.adapt_batch. Rejects, defers,
      log rejects, adapter codes and owner adapter crashes are counted; the report holds
      counts and codes only. --out is required and refused under data/news_impact.
  - path: tests/test_news_impact_producer_facts.py
    what: 41 tests on synthetic events that validate_event accepts, with fictional issuers, covering the fact key, period tokens, leaf payloads, the evidence ladder, novelty cycles, log validity, projection, adapter accounting including the range crash, the output guard, shadow handling, report content and determinism.
  - path: .github/ci/legacy-jobs.yml
    what: The news-impact-contracts job also runs the stage-two tests.
  - path: agentos/decisions/DEC-NEWS-IMPACT-W3-PRODUCER-STAGE2.md
    what: The fact key, novelty by rule, per-record append, the evidence ladder, per-event adapter accounting with crash containment, and the projection failure rule.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-ADAPTER-RANGE-BOUND.md
    what: The owner adapter crashes on every contract-valid range quantity because it reads a bound the v1 range shape forbids.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: The w3 next_action names stage two and the adapter repair lane; a do_not_redo line for stage two and its shadow runs.
verified:
  - claim: The stage-two tests pass.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_producer_facts.py -q
    result: 41 passed.
  - claim: The whole news_impact suite passes on the branch base.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_*.py -q
    result: 1186 passed, 2 skipped on base f4da7548b6dd.
  - claim: Stage two completes on all four stage-one shadow event files with no rejects or defers.
    command: >
      PYTHONPATH=. python3.12 -m engine.news_impact.producer_facts --events
      <events_shadow_fam_a.jsonl | events_shadow_fam_b.jsonl, graded and queue> --out <scratch>
    result: >
      Graded fam_a 127 records (N2 126, N4 1), 127 views, adapter ok 91,
      adapter_crash:KeyError 34, adapter:SLOT_TOO_LONG 2. Graded fam_b 88 records (N2 87,
      N4 1), 88 views, ok 61, adapter_crash:KeyError 27. Queue fam_a 12 records, ok 11,
      crash 1; queue fam_b 7 records, ok 6, crash 1. All exit 0.
  - claim: No filing text, headline, entity name or dollar figure is committed.
    command: the DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE rights grep (dollar-digit, registrant cover line, body divider) on every new and changed file
    result: no matches.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0
unverified:
  - claim: The CI run on this pull request and its landing.
    what_would_verify: Concluded-green checks, gh pr merge --squash --match-head-commit, a per-path blob comparison against a freshly fetched origin/main, and a green ci.yml run on a main descendant to clear the CI-authority freeze from the legacy-jobs edit.
  - claim: Any adjudicated fact log or measured Prophet evidence.
    what_would_verify: A third family (GLM after 2026-10-19 05:16Z), stage one in adjudicated mode, then stage two on its events.
unresolved:
  - "The owner adapter crashes on every contract-valid range quantity (DSC:NEWS-IMPACT-ADAPTER-RANGE-BOUND); about a quarter of shadow events get no Prophet evidence until an owner repair lane fixes it."
  - "Almost every shadow fact is the first observation of its key (N2), so the novelty paths for manifestations and corrections are exercised by tests, not by the benchmark events."
  - "Owner notes for the next version: the adapter requires cluster_grain, which the event schema leaves optional; event span_id allows 128 characters but fact_log expects span_ plus 20 hex; object_name allows 120 in events and 80 in fact keys; the T2 baseline carries no evidence; append_records revalidates the whole log on each call."
next_actions:
  - Merge this PR on concluded green with --match-head-commit, verify landing per path, then clear the CI-authority freeze with one ci.yml baseline on main (preflight for an in-flight run first).
  - Commission an owner repair lane for the adapter range projection (read the range bound as absent, raise ProphetAdapterError with a code on unprojectable input), with its own review.
  - "After 2026-10-19 05:16Z: the GLM third family on the 12 queue and 157 graded cases, stage one in adjudicated mode, stage two on its events, and the section 11 quality/cost report."
  - "On or after 2026-10-20: gated_v3 exactly as frozen in issuer_fallback/README.md."
do_not_redo:
  - "Stage two and its rules are settled by DEC:NEWS-IMPACT-W3-PRODUCER-STAGE2; never add a bound to range events to suit the adapter, and never fail the run on one record or one event."
  - "The stage-two shadow runs are recorded here and in the DEC; re-run them only when the events, the producer or an owner module change."
danger_areas:
  - "Stage-two outputs (fact_log.json, thesis_views.jsonl, prophet_evidence.jsonl) carry event values and stay in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "Never pass thesis.DEFAULT_LOG_PATH or anything under data/news_impact as --out; only the nightly advances forward ledgers."
  - "prophet_adapter, thesis and cluster are owner modules; record their defects, repair them in their own lanes."
  - "Exception messages from the owner modules can carry values; print only the class or code and the path."
---

# PROPHET-NEWS-IMPACT handoff 2026-10-14 (w3 producer stage two)

Stage-one events now become fact log records, thesis views and Prophet evidence through
the owner modules, with every row accounted for and outputs only under an explicit
directory. On the real shadow events the stage completes with no rejects or defers. The
owner adapter crashes on contract-valid range quantities, about a quarter of events; the
producer counts those and continues, and the repair goes to an owner lane. Measured
packets still wait on the third family.
