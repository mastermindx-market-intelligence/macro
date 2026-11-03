---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-adapter-range-f3e15d5e26cc5279"
model: opus
ended_because: ci_handoff
decisions: ["DEC:NEWS-IMPACT-ADAPTER-RANGE-BOUND"]
discoveries: ["DSC:NEWS-IMPACT-ADAPTER-RANGE-BOUND"]
mission: >
  Repair the owner Prophet adapter so a contract-valid news_impact_event.v1 range
  quantity becomes Prophet evidence instead of a bare KeyError, without changing either
  frozen contract, and make every quantity key the adapter reads fail with a code.
state_before: >
  Stage two of the W3 producer (#9427) counted the adapter's KeyError on every range
  quantity as adapter_crash:KeyError and continued: 34 of 127 graded fam_a events, 27 of
  88 graded fam_b events and 1 in each queue run got no Prophet evidence
  (DSC:NEWS-IMPACT-ADAPTER-RANGE-BOUND). The stage-two handoff named an owner repair lane
  with its own review as the next step.
changed:
  - path: engine/news_impact/prophet_adapter.py
    what: >
      ADAPTER_VERSION ni-prophet-adapter-2. A range with no bound key projects
      RANGE_BOUND ("exact"); a bound key present is carried as given and judged by output
      validation. Every quantity checks form (missing: MISSING_REQUIRED_FIELD, unknown:
      SCHEMA_VIOLATION), and range and point quantities check the keys they read and raise
      MISSING_REQUIRED_FIELD "<slot>.<key>".
  - path: tests/test_news_impact_prophet_adapter.py
    what: >
      Range quantities that validate_event accepts on every template slot: W1
      incremental_amount and remaining_authorization, executed_amount (T1_execution), the
      worked T2 ranges W3 and R2 with and without cluster_grain, T3 stated_quantity; low
      equal to high, a non-USD unit, negated and negative ranges, carried and invalid
      bounds, the build-time 48-character refusal and the render-time word-budget
      refusal, and coded errors for every missing or unknown key including form.
  - path: tests/test_news_impact_producer_facts.py
    what: >
      The stage-two range test now expects Prophet evidence for both events and no crash;
      crash containment keeps its own test, a monkeypatched owner crash counted by class
      for KeyError, TypeError and ValueError.
  - path: engine/news_impact/producer_facts.py
    what: Comment only; the crash-containment comment no longer names the range projection, which no longer crashes.
  - path: agentos/decisions/DEC-NEWS-IMPACT-ADAPTER-RANGE-BOUND.md
    what: Bound "exact" on a range, coded missing keys, the version bump, and the four rejected alternatives.
  - path: agentos/discoveries/DSC-NEWS-IMPACT-ADAPTER-RANGE-BOUND.md
    what: Rewritten from the crash to the contract gap and how the adapter closes it, with the adapter tests as its falsifier.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: The w3 and top-level next_action drop the repair lane; a do_not_redo line for the repair.
verified:
  - claim: The adapter tests pass, and the new tests discriminate.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_prophet_adapter.py -q, then the same file against the ni-prophet-adapter-1 module
    result: 109 passed; 12 of the 13 first-round tests fail on the previous adapter (the carried-bound test passes on both by design).
  - claim: The whole news_impact suite passes after merging origin/main.
    command: PYTHONPATH=. python3.12 -m pytest tests/test_news_impact_*.py -q
    result: >
      1221 passed, 2 skipped on the merge of origin/main 53750adc. The skips are
      pre-existing: a raw-byte case invisible after json.loads, and the issuer ledger test
      that needs data/ in a sparse worktree.
  - claim: Stage two on the four W3 shadow event files projects every range.
    command: >
      PYTHONPATH=. python3.12 -m engine.news_impact.producer_facts --events
      <events_shadow_fam_a.jsonl | events_shadow_fam_b.jsonl, graded and queue> --out <scratch>
    result: >
      Graded fam_a adapter ok 125 and SLOT_TOO_LONG 2 (was ok 91, crash 34); graded fam_b
      ok 88 (was 61, crash 27); queue fam_a ok 12 (was 11); queue fam_b ok 7 (was 6). The
      runs project 34, 27, 1 and 1 range quantities, all bound exact; the longest range
      amount slot is 29 characters against a limit of 48, and render_glance_copy refuses
      none of the 231 records (63 ranges). The shadow files stay in scratch and cannot be
      reproduced from the repository; the tests are the committed falsifier.
  - claim: An independent review of the diff, and the repairs it asked for.
    command: >
      Fabric review lane W3R_ADAPTER_RANGE_REVIEW_ubuntu1_v1 (review class, bailian
      qwen3.8-max, ubuntu1, read-only); the seat checked each defect against the code.
    result: >
      REQUEST_REPAIR with five change-attributable defects, all answered in the second
      commit: D1 a long-unit range refused at build or render is now a documented scoped
      refusal, pinned by tests, with the DEC's rejected-alternative wording corrected;
      D2 range tests added on every template slot and both worked T2 ranges; D3 a bound key
      present is carried as given and judged by output validation; D4 form is checked and
      coded; D5 the DEC says the shadow figures are scratch-held. Six pre-existing findings
      are recorded below as owner notes.
  - claim: No filing text, headline, entity name or dollar figure is added.
    command: the DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE rights grep on every new file and on the added lines of every changed file
    result: no matches.
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: exit 0
unverified:
  - claim: The CI run on this pull request and its landing.
    what_would_verify: Concluded-green checks, gh pr merge --squash --match-head-commit, and a per-path blob comparison against a freshly fetched origin/main. No CI-authority path changes, so no main baseline is owed.
  - claim: Any adjudicated fact log or measured Prophet evidence.
    what_would_verify: A third family (GLM after 2026-10-19 05:16Z), stage one in adjudicated mode, then stage two on its events.
unresolved:
  - "Next event-contract version: an optional bound on quantity_range so a hedged range keeps its hedge; until then every range renders without a hedge word."
  - "format_amount scales a range by its high value, so a low on a smaller scale than the high reads in the high's scale; the tests use same-scale ranges."
  - "Next prompt version: the enum lists, cross-field rules and executed_amount split (DSC:NEWS-IMPACT-LABEL-CONTRACT-COHERENCE)."
  - "Owner notes carried from stage two: the adapter requires cluster_grain, which the event schema leaves optional; event span_id allows 128 characters but fact_log expects span_ plus 20 hex; object_name allows 120 in events and 80 in fact keys; the T2 baseline carries no evidence; append_records revalidates the whole log on each call."
  - "Owner notes from the adapter review (pre-existing, not changed here): a negative amount renders with a doubled sign; a negated quantity renders as positive copy; SCHEMA_VIOLATION messages echo input values (producer_facts records codes and classes only); SUPERSEDED copy leaves a placeholder unfilled; a quantity's own evidence span never reaches source_spans; the five T2 worked cases lack cluster_grain, which the adapter requires."
  - "The copy word budget is enforced only in render_glance_copy, so build_prophet_evidence, adapt_batch and the stage-two producer accept a record whose copy is refused when rendered; none of the 231 shadow records hits it."
  - "A range repeats its unit per endpoint, so a long unit reaches the 48-character or word budget sooner than a point; a compact range format is a copy question for the A7 owner."
  - "Other notes: stage one (producer.py) drops a bound a labeler puts on a range and counts it range_bound_dropped, because v1 has no bound field, so that hedge is the one a later event version would keep; non-USD amounts render unscaled; the T1_authorization subtitle omits remaining_plain; T3 copy never renders the quantity."
next_actions:
  - Merge this PR on concluded green with --match-head-commit and verify landing per path.
  - "After 2026-10-19 05:16Z: the GLM third family on the 12 queue and 157 graded cases, stage one in adjudicated mode, stage two on its events, and the section 11 quality/cost report."
  - "On or after 2026-10-20: gated_v3 exactly as frozen in issuer_fallback/README.md."
do_not_redo:
  - "The adapter range projection is settled by DEC:NEWS-IMPACT-ADAPTER-RANGE-BOUND: bound exact unless the input carries one, coded missing keys; never add a bound to v1 events and never make bound optional in prophet_evidence.v1 to suit one producer."
  - "The stage-two shadow runs with ni-prophet-adapter-2 are recorded here and in the DEC; re-run them only when the events, the producer or an owner module change."
danger_areas:
  - "Stage-two outputs carry event values and stay in scratch (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE)."
  - "tests/test_news_impact_prophet_adapter.py already holds the A7 design's example figures; apply the rights grep to added lines, not the whole file."
  - "prophet_adapter, thesis and cluster are owner modules; repair them only in their own reviewed lanes."
---

# PROPHET-NEWS-IMPACT handoff 2026-10-15 (adapter range repair)

The owner adapter now turns a contract-valid range quantity into Prophet evidence with
bound "exact" and raises a coded error for a quantity missing a key it reads. On the W3
shadow events every range that used to crash now projects, and the stage-two crash count
is zero. Measured packets still wait on the third family.
