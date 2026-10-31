---
key: NEWS-IMPACT-W3-PRODUCER-STAGE2
question: >
  Stage one of the W3 producer emits validated news_impact_event.v1 rows. Stage two must
  turn them into fact_log.v1 records with rule-assigned novelty, thesis views and Prophet
  evidence, using the owner modules (cluster, thesis, prophet_adapter) only, without
  writing to the shared fact log. The owner modules are read-only and some of their
  behaviour does not match the frozen v1 event contract. How does stage two key facts,
  account for every row, and handle an owner module that fails on a contract-valid event?
answer: >
  (1) ONE MODULE, OWN OUTPUT PATH. engine/news_impact/producer_facts.py
  (PRODUCER_FACTS_VERSION ni-producer-facts-1) reads stage-one events*.jsonl rows and
  writes fact_log.json, thesis_views.jsonl, prophet_evidence.jsonl and facts_report.json
  only under a required --out directory. An --out at or under the directory of
  thesis.DEFAULT_LOG_PATH is refused with exit 2. It does not import stage one; it reads
  stage one's output contract.
  (2) FACT KEY. company_id and template come from the event. T1 keys on action_type and
  on whether the primary amount is executed, plus a lossless fiscal-period token for the
  horizon when one is stated. T2 keys on metric, the fiscal-period token and one
  counterparty CIK or null. T3 keys on event_kind, object_name and one counterparty CIK or
  null. A counterparty array, an object_name over the fact_log limit of 80, an absent
  object_name and a quarter without a quarter number are rejected with a code; nothing is
  truncated or remapped.
  (3) NOVELTY BY RULE. Each event becomes a cluster.FactObservation whose quantity is the
  owner quantity_fingerprint of the leaf payload; cluster.assign_novelty decides, events
  in (observed_at, fact_id) order. A same-value repeat becomes a manifestation that
  reports the latest equal-valued revision; everything else is a fact_revision.
  Commentary with no live same-key revision is deferred.
  (4) APPEND ONE RECORD AT A TIME. Each record goes through thesis.append_records on its
  own, so a record the owner log validator refuses is rejected as log_<code> and the run
  continues. This refines the frozen spec, which failed the whole run on an append
  error: one bad record should not hide the accounting of the rest.
  (5) EVIDENCE LADDER. The record's owner_span_ref is the action span for T1 and T3. For
  T2 it is the stated amount's span, then the option ceiling, then the prior amount, and
  otherwise a FieldAbsence. A span without a span_id is rejected evidence_span_unbound.
  (6) ADAPTER PER EVENT, NEVER FATAL. The adapter input is a deep copy of the event with
  novelty, supersedes_fact_id and cluster_grain taken from the log record. A
  ProphetAdapterError is counted as adapter:<code>. A KeyError, TypeError or ValueError
  from the owner adapter on an event that passed validate_event is counted as
  adapter_crash:<class>; neither stops the run.
  (7) PROJECTION. thesis.project runs once on the whole log with as_of from --as-of or
  the latest observed_at. A ThesisError there is reported as project_error with exit 1,
  because it means the producer built a log the owner cannot read.
  (8) SHADOW STAYS SHADOW. All rows of one run must agree on the shadow flag; shadow rows
  produce shadow outputs and the report mode is shadow. The report holds counts and
  codes only.
rationale: >
  The section 12 exit asks for validated claims, novelty deltas and issuer facts with
  full accounting. Per-record append and per-event adapter accounting keep one failure
  from erasing the counts of every other row. The adapter containment is needed because
  the owner range projection reads a bound field that the frozen v1 range shape forbids,
  so every contract-valid range quantity raised a bare KeyError and the first real
  shadow run stopped before writing any output. The adapter is owner code and read-only
  here, so the producer counts the crash by class and the defect goes to an owner repair
  lane.
alternatives:
  - option: Fail the whole run on any append or adapter error, as the frozen spec said for append.
    why_not: >
      On the real shadow files every run failed before producing any output, because
      every range quantity crashed the adapter. A run-level failure hides how many rows
      were fine.
  - option: Add a bound to range quantities before calling the adapter.
    why_not: >
      That is a remap of a contract-valid event to suit an owner defect. The v1 range
      shape has no bound and stays byte-frozen (DEC:NEWS-IMPACT-PHASE0-FREEZE).
  - option: Patch prophet_adapter's range projection in this PR.
    why_not: >
      prophet_adapter is owner code accepted in W1B; its defects go to a repair lane with
      its own review, as in DEC:NEWS-IMPACT-W1C-DESIGN-RULINGS.
  - option: Write the log to data/news_impact/fact_log.jsonl.
    why_not: >
      That is a forward ledger only the nightly advances, and a benchmark run is not a
      production event.
evidence:
  - "tests/test_news_impact_producer_facts.py: 41 passed on synthetic events checked by validate_event, including a range quantity that the adapter crashes on while the rest of the batch completes."
  - "Shadow fam_a graded events (127 rows): 127 fact_revision records, rules N2 126 and N4 1, 0 rejected, 0 deferred, 127 views, adapter ok 91, adapter_crash:KeyError 34, adapter:SLOT_TOO_LONG 2."
  - "Shadow fam_b graded events (88 rows): 88 fact_revision records, rules N2 87 and N4 1, 0 rejected, 0 deferred, 88 views, adapter ok 61, adapter_crash:KeyError 27."
  - "Shadow queue events: fam_a 12 records, ok 11, adapter_crash:KeyError 1; fam_b 7 records, ok 6, adapter_crash:KeyError 1."
  - "Before the containment, all four shadow runs exited 1 with a KeyError raised in prophet_adapter._project_quantity on the range branch, and wrote no report."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/producer_facts.py"
  - "tests/test_news_impact_producer_facts.py"
  - "DEC:NEWS-IMPACT-W3-PRODUCER"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# Stage two keys facts by rule, appends one record at a time and contains owner adapter crashes

The second stage of the W3 producer turns stage-one events into fact_log.v1 records,
thesis views and Prophet evidence through the owner modules, writing only to an explicit
output directory. Novelty is assigned by rule, every row is recorded, deferred or rejected
with a code, and a record the owner log refuses or an event the owner adapter fails on is
counted rather than stopping the run. On the real shadow events the stage completes with
no rejects; about a quarter of events carry a range quantity, and the owner adapter
crashes on those because it reads a bound the frozen range shape forbids. That defect is
counted and goes to an owner repair lane (DSC:NEWS-IMPACT-ADAPTER-RANGE-BOUND).
