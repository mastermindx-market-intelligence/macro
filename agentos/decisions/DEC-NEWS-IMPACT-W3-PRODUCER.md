---
key: NEWS-IMPACT-W3-PRODUCER
question: >
  Wave w3 needs a Phase 1 producer: real documents and labeler returns in, validated
  news_impact_event.v1 candidates out, with full processing, defer and reject accounting
  (masterplan section 12). The owner modules already exist (agreement, validate, the
  documents span binder, cluster, thesis, prophet_adapter) and the v1 contract is
  byte-frozen. How does the producer turn label returns into events without remapping
  labels, without writing to the shared fact log, and without overstating what a
  two-family run can certify while the third family is unavailable?
answer: >
  (1) TWO STAGES, TWO PULL REQUESTS. Stage one (engine/news_impact/producer.py,
  PRODUCER_VERSION ni-producer-1) parses each family's return through
  agreement.parse_label_return, ties it to the bundle's source sha256, replays every span
  with agreement.replay_return_spans, routes the two families through
  agreement.route_case, binds spans through documents.text_span/verify_span, and sends
  the assembled event through validate.validate_event. Stage two adds rule-assigned
  novelty (cluster.assign_novelty), thesis append/validate_log/project into an explicit
  output path, and the prophet_adapter assembly.
  (2) EVERY CASE LANDS IN EXACTLY ONE OUTCOME WITH A CODE. Emitted, deferred
  (family_return_missing, injection_flagged, pending_third_family, adjudication_needed,
  resolved_by_third_unbound) or rejected (parse, replay, span binding, period, quantity,
  enum, issuer and validation codes; a validation code folds array indices to /N). The
  report holds counts and codes only, never values. Deferred and rejected are states of
  one run, not verdicts on a case: a third family or a later contract version can move a
  case.
  (3) FAIL CLOSED, NEVER REMAP. A label value outside the contract enum, a missing enum,
  or a field set that breaks a contract cross-field conditional is rejected with its
  code. The producer never maps a near-miss value onto a contract value and never edits
  the v1 contract. Normalisation is limited to shape conversions the contract defines
  (absence objects, a calendar quarter-end, a dropped range bound, a currency carried in
  the unit), and each one is counted in the report.
  (4) THE ISSUER TIE APPLIES TO THE ROUTED VALUE. company_id must equal the bundle's CIK
  on the value routing accepts, and in shadow mode on the one family read. A single
  family that names another issuer is a field disagreement, which route_case sends to a
  third family; the producer does not reject the case before the owner router sees it.
  (5) ADJUDICATED AND SHADOW MODES ARE DIFFERENT CLAIMS. The adjudicated mode emits only
  cases route_case accepts; with two families and no third, every disputed case defers
  pending_third_family. --shadow-single-family reads one family as if accepted. Shadow
  output is a coverage and contract-coherence diagnostic for the labels, never measured
  packets, and its rows carry shadow true.
  (6) CONTEXT ONLY. Authority is context_only, may_rank, may_size, may_gate and
  prophet_authority are false, and novelty in stage one is the labeler's value, marked
  novelty_source label_provisional. The output directory is a required argument; the
  producer never writes to thesis.DEFAULT_LOG_PATH.
rationale: >
  The section 11 thresholds (critical-numeric correctness, routing recall, complete
  accounting, no unsupported supplier assertions) are measured on what the producer
  emits, so it cannot hide a case or improve a label. Remapping would turn labeler
  errors into emitted events that look validated. The issuer rule was first written as
  a per-family reject; on the graded set it rejected 10 cases in adjudicated mode that
  the owner router would have sent to a third family, which put a producer rule in front
  of the owner's dispute path. Moving the check to the routed value restores the owner's
  semantics and still rejects a wrong issuer wherever a value is accepted. Splitting the
  stages keeps the first pull request to the gates and the accounting that every later
  stage depends on.
alternatives:
  - option: Map near-miss enum values and malformed amount forms onto contract values.
    why_not: >
      It would emit events whose labels the contract rejects, and the benchmark would then
      score the mapping, not the labeler. Prompt and contract gaps are recorded as
      next-version candidates instead (DSC:NEWS-IMPACT-LABEL-CONTRACT-COHERENCE).
  - option: Reject a case when any one family names another issuer.
    why_not: >
      route_case already treats a field disagreement as a third-family dispute. Measured
      on the graded set, the per-family reject turned 10 pending_third_family cases into
      rejects in adjudicated mode.
  - option: Append emitted events to the shared fact log at data/news_impact/fact_log.jsonl.
    why_not: >
      The fact log is a forward ledger; only the nightly advances forward ledgers, and a
      benchmark run is not a production event. Stage two writes thesis outputs to an
      explicit output path only.
  - option: Treat shadow single-family output as the measured packet set.
    why_not: >
      One family's value is not an accepted value under the agreement rules. Shadow runs
      measure label coverage and contract coherence; measured packets wait for a third
      family or adjudication.
evidence:
  - "Graded set (157 cases), adjudicated mode: 0 emitted, 157 deferred pending_third_family, 0 rejected; before the issuer change it was 147 deferred and 10 rejected company_id_mismatch."
  - "Graded set, shadow fam_a: 127 emitted (T1 44, T2 62, T3 21), 30 rejected; shadow fam_b: 88 emitted (T1 34, T2 36, T3 18), 69 rejected (DSC:NEWS-IMPACT-LABEL-CONTRACT-COHERENCE)."
  - "gated_v2 label queue (12 cases): adjudicated 12 deferred pending_third_family; shadow fam_a 12 emitted; shadow fam_b 7 emitted, 5 rejected on contract conditionals."
  - "tests/test_news_impact_producer.py: 33 passed; tests/test_news_impact_*.py: 1145 passed, 2 skipped."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/producer.py"
  - "tests/test_news_impact_producer.py"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# The W3 producer gates label returns into events, fails closed and never remaps

Stage one of the Phase 1 producer turns label returns into news_impact_event.v1
candidates through the owner modules only: return parsing, source and issuer ties, span
replay, two-family routing, owner span binding and the validate_event chokepoint. Every
case is emitted, deferred or rejected with a code, and the report carries counts and codes
only. Labels outside the contract are rejected, not mapped. The issuer tie applies to the
value routing accepts, so a single family's wrong issuer goes to the owner's third-family
path. With two families and no third, the adjudicated mode emits nothing yet; shadow
single-family runs are diagnostics, not packets. Novelty, the fact log and the Prophet
adapter are stage two.
