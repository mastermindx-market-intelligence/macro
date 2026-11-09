---
key: HUB-EDGE-FALLBACK-NEEDS-COMPONENT-COVERAGE-20261109
claim: >
  At Macro b5674d8ef898e503d6164922654f5ff89be9981c, engine/intel_hub.py returns edge score 0.4 with zero components on its no-component branch while compact summaries omit the component count needed to identify that fallback.
falsifier: >
  Inspect engine/intel_hub.py:453 (no-component return), engine/intel_hub.py:665 (full-command edge_components) and engine/intel_hub.py:1101 (_compact) at Macro b5674d8ef898e503d6164922654f5ff89be9981c, or their equivalents at a later qualified change. Falsify the compact-coverage gap by showing a generation-matched compact field that establishes edge_components for the displayed score.
so_what: >
  Bind a default-value qualifier to the matching full command record and zero component count, never infer it from a displayed score of 40, and keep Opportunity, Edge, Stage and published order separate in the interface.
kind: landmine
verified_at: 2026-11-09
verified_by: >
  Exact-pin engine/intel_hub.py read: no-component return score0.4/n_components0/n_base0, command edge_components, _compact field selection and descending opportunity_score/composite_conviction sort; Paper Build 852-0.
scope:
  - engine/intel_hub.py
confidence: verified
---

# Numeric score alone does not establish coverage

An older source comment mentions neutral0.5, but the inspected executable branch returns0.4. The full command preserves edge_components; the compact hero omits it. A real calculated score can also round to40, so the value alone is not a missing-input indicator.

The command producer owns descending opportunity_score then composite_conviction. Edge is a separate remaining-opportunity reading, and Stage is categorical. Policy is context rather than a voting desk. Do not add local rescoring or a cross-market normalization to explain these values.

Paper now has an EN/ZH explanation and a Build contract requiring source-generation matching. Its generic customer wording does not attach a numeric fallback to an unbound historical generation. No ranking algorithm or live consumer was changed by this audit.

See [source ruling R7](../../research/design_candidates/paper_audit_20261108/followup/SOURCE_RULINGS.md) and build slice F07. This record is advisory knowledge and creates no runtime admission or release gate.
