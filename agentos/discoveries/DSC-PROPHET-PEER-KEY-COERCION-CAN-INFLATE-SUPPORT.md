---
key: PROPHET-PEER-KEY-COERCION-CAN-INFLATE-SUPPORT
claim: >
  The independent peer observation and continuity helpers at Macro base5913c230
  stringify and trim roster keys before reading the original mappings. A B plus
  padded-B roster can count the same positive observation twice while hiding a
  missing member, and integer/string collisions can shrink the denominator.
falsifier: >
  python3 -m pytest tests/test_group_flow.py -q -k roster_keys_reject on
  the recorded preimage refuses ambiguous source keys
  before any roster measurement or retains each exact input without key coercion.
so_what: >
  Refuse malformed roster/focal keys in the existing group_flow owner before
  measuring or comparing snapshots. Never manufacture independent confirmation
  by silently normalizing identity; keep valid-input formulas, missingness and
  all five authority flags unchanged. Existing source owners still resolve aliases.
kind: landmine
verified_at: 2026-10-19
verified_by: >
  python3 -m pytest tests/test_group_flow.py -q; native group_flow preimage
  af0d5f671edded697c03a827976d207bb2b7e7a3,
  red-first 29 failed/6 passed assertions, corrected 96 passed/2 skipped;
  adjacent consumer battery279 passed/8 skipped; 400 exact valid-input comparisons.
scope: [macro]
confidence: verified
---

This is software input-boundary evidence from synthetic values, not a measured
production incident, new rights decision, experiment admission or predictive result.
Published #8240/#8091 and their source-custody/release holds remain independent.

Receipt: research/prophet_v4/leadership_evidence_v1/roster_integrity_20261019/verification.json
