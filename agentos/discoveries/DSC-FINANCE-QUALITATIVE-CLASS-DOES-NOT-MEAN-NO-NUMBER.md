---
key: FINANCE-QUALITATIVE-CLASS-DOES-NOT-MEAN-NO-NUMBER
claim: >-
  In the Finance read model, metric.measurement_class QUALITATIVE does not mean the record
  carries no number. The T2 composer (engine/sector_intelligence/finance_projection.py,
  metric.setdefault("measurement_class", "QUALITATIVE") right after it copies obs["value"])
  gives every classless observation the class QUALITATIVE, value included, and the schema's
  $defs/metric puts no condition between measurement_class and value. The dossier spec's §D.0
  rule 1 renders "No metric on file" for any QUALITATIVE metric. When T11 round 3b reused that
  formatter for the evidence drawer's Value row, the receipt denied numbers the page's own
  composer publishes. The independent round-3c re-review found this as its only MAJOR: a
  record with value 3.5, unit x and class QUALITATIVE read "No metric on file" (暂无可用指标).
falsifier: >-
  Compose a document with compose_finance_projection over an observation that carries a value
  and no measurement_class, and read the emitted metric. The claim is false if the class is
  anything but QUALITATIVE while the value survives. Separately, restore the unconditional
  QUALITATIVE short-circuit in fmtMetric (templates/finance_intelligence.js): the claim's
  consequence is false if
  test_the_receipt_prints_every_stated_number_in_plain_digits[metric0-3.5 x] stays green.
so_what: >-
  Any renderer or consumer of finance_intelligence_read_model.v1 that treats QUALITATIVE as
  "no value" hides stated numbers. A receipt surface (the drawer, an export, an audit view)
  prints metric.value whenever it is a number, whatever the class. Only a glance tier may
  apply §D.0's QUALITATIVE rule, and only because it is a display choice, not a fact about
  the data. When the integration wave adapts the shared foundation's records, keep the class
  as stated by the owner and never infer "no number" from it.
kind: landmine
verified_at: 2026-09-27
verified_by: "grep -n 'setdefault(\"measurement_class\"' engine/sector_intelligence/finance_projection.py (line 778); PR #8009 round-3c re-review F1 probe; round-3d red-proof row F1_receipt_hides_a_qualitative_number RED (2 failed)"
scope:
  - macro
  - engine/sector_intelligence/finance_projection.py
  - templates/finance_intelligence.js
  - contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json
confidence: verified
---
