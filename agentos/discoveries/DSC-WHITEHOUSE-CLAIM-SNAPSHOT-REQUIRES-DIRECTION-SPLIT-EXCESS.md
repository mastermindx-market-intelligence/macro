---
key: WHITEHOUSE-CLAIM-SNAPSHOT-REQUIRES-DIRECTION-SPLIT-EXCESS
claim: The 2026-10-15T17:46:25Z production claim snapshot binds whitehouse uniquely to scripts/build_whitehouse.py::whitehouse-desk
  by canonical registry rule 2 and contains 210 positive-direction and 90 negative-direction non-placebo
  claims. The T12 consumer rejects interpreting a pooled raw signed excess_mean over this mixed-direction
  snapshot as forecasting skill. This is an intended-report legality finding, not evidence of a published
  invalid report or observed returns.
falsifier: Run python3 scripts/check_qledger_metric_validity.py --project-findings /Volumes/Mastermind/evidence/intelligence-evaluation-os-20261012-01a1333d/integration/a1-refresh-recovery-20261015/t12-claims-only-consumer-input.json
  against the retained input hash cf6c0f6e92e79d5c4069249a13306b07c27bf94e876691bc7c73c998cb8ee03f and
  show that the unique rule-2 binding, both claim directions, or the owner raw-excess contract is absent.
  A different later snapshot does not falsify this dated snapshot claim.
so_what: Before presenting a whitehouse excess mean as skill, split it by direction or choose a metric
  whose semantics match the claim family. Preserve not_assessed, do not infer an earned tier or change
  a gate, producer, priority, clock or lifecycle from this finding.
kind: data
verified_at: '2026-10-15'
verified_by: research/evidence/eval-os-tier-query-20261014/t12-real-claim-consumer.json:1; actual scripts/check_qledger_metric_validity.py
  --project-findings consumed first-party claim metadata and the canonical installed registry; engine/qledger_validity.py
  owns the raw-excess interpretation.
scope:
- macro
- WS:EVAL-OS-EVIDENCE-VIEW
- scripts/build_whitehouse.py
- engine/qledger_validity.py
confidence: verified
evaluation_finding:
  engine: scripts/build_whitehouse.py::whitehouse-desk
  metric: excess_mean
  observed_change: 'Snapshot of intended-report metric validity: family holds directions [-1, 1]; grades.excess
    is raw (not direction-signed), so a pooled signed excess_mean measures universe drift, not skill.
    Report hit_rate, mean |excess|, or split the mean per direction.'
  segment: whitehouse
  evidence_link: /Volumes/Mastermind/evidence/intelligence-evaluation-os-20261012-01a1333d/integration/a1-refresh-recovery-20261015/t12-claims-only-consumer-source.json
  suggested_tier: T0
---

# Claim metadata consumer

The parent independently supplied the claim, falsifier, consequence, provenance, scope
and confidence required by normal Discovery admission. The typed evaluation finding
came unchanged from the actual CLI result. Its suggested T0 is an investigation
requirement, not an earned scientific tier or an automatic promotion.

Only first-party claim identifiers, family, direction, declared horizon and placebo
metadata were retained. No grade file, sealed outcome, supplier payload or model
response was read. Empty supplied grades mean outcomes were deliberately unobserved;
they do not mean that no grades exist. Source endpoint identity was checked but is
not an atomic snapshot guarantee.

This proves a real local source consumer on the owned follow-on checkout and the
existing Discovery drafter/validator. Protected publication, installed CLI execution
and subsequent Discovery consumption remain separate release obligations. No
producer, metric gate, source clock, priority, routing or lifecycle changed.
