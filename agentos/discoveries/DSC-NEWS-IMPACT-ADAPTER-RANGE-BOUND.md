---
key: NEWS-IMPACT-ADAPTER-RANGE-BOUND
claim: >
  engine/news_impact/prophet_adapter.py cannot project a quantity_range that satisfies
  the frozen news_impact_event.v1 contract. The v1 quantity_range shape requires form,
  low, high, unit, currency, basis, period, negated and evidence and forbids any other
  field, so it has no bound. The adapter's _project_quantity reads raw["bound"] on its
  range branch, so adapt_batch raises a bare KeyError, not a ProphetAdapterError, for
  every contract-valid event that carries a range quantity in a field the adapter
  projects. On the W3 shadow events this is 34 of 127 graded fam_a events, 27 of 88
  graded fam_b events, and 1 event in each queue run. The adapter's own tests carry no
  range quantity at all, which is why it was not caught.
falsifier: >
  Build a T1 event with incremental_amount as a quantity_range without bound, confirm
  validate.validate_event accepts it, and call prophet_adapter.adapt_batch on it with
  novelty and cluster_grain set. A ProphetAdapterError or a successful projection
  instead of a KeyError would refute the claim. tests/test_news_impact_producer_facts.py
  pins the current behaviour through the producer.
so_what: >
  (1) Until the adapter is repaired, Prophet evidence is missing for every event whose
  amount is a range, about a quarter of the shadow events, and the producer report counts
  them as adapter_crash:KeyError. (2) The repair belongs in the owner module through a
  W1C-style repair lane with its own review, reading the range bound as absent; it must
  not be fixed by adding a bound to events, because the v1 contract is byte-frozen
  (DEC:NEWS-IMPACT-PHASE0-FREEZE). (3) The adapter raising a bare KeyError means its
  error contract is incomplete: input it cannot handle should raise ProphetAdapterError
  with a code.
kind: landmine
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=. python3.12 -m engine.news_impact.producer_facts --events
  <stage-one shadow events> --out <scratch> on the four shadow files. Before the
  producer containment every run exited 1 with a KeyError traceback ending in
  prophet_adapter._project_quantity; after it, the reports count adapter_crash:KeyError
  34, 27, 1 and 1, and leaf_range_carried 35, 27, 1 and 1.
scope:
  - "engine/news_impact/prophet_adapter.py"
  - "engine/news_impact/producer_facts.py"
  - "contracts/news_impact/"
confidence: verified
---

# The Prophet adapter crashes on contract-valid range quantities

The owner adapter reads a bound field on range quantities that the frozen v1 contract
forbids, so every contract-valid range amount raises a bare KeyError. Stage two of the
producer counts these by class and continues. The repair is an owner change in its own
lane.
