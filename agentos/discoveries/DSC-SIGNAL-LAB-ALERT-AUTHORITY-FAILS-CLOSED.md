---
key: SIGNAL-LAB-ALERT-AUTHORITY-FAILS-CLOSED
claim: >
  BTC impulse history and current alert authority are separate facts: stable historical event IDs
  and original issue-time claims remain preserved, while present action/push/board authority is
  recomputed through one current validation resolver using independent gate, source, and event
  clocks; malformed leading measurements and missing typed direction fail closed.
falsifier: >
  On semantic head 7d67c8e640b2227883daeaf63e5ee15d289d8615, run the focused trust tests in
  tests/test_signal_evidence.py and tests/test_alert_trust_projection.py and inspect
  engine/btc_impulse_radar.py::resolve_leg_permission plus
  engine/alert_triage.py::pressure_effect. This discovery is false if a missing/malformed or
  threshold-failing leading receipt can return permitted=true, an impulse with no explicit typed
  direction contributes risk_on/risk_off, or a rebuild changes the stable historical event identity
  instead of withdrawing only current authority.
so_what: >
  Future Signal Lab, BTC impulse, and Alert Center work must not treat persisted tier/copy as current
  truth. Preserve raw historical observations and original_claim, but route current authority through
  the canonical resolver and explicit typed direction. A stale/unreadable/malformed current gate is
  observation-only, never a reason to resurrect historical action language.
kind: architecture
verified_at: 2026-09-14
verified_by: >
  `git show 7d67c8e640b2227883daeaf63e5ee15d289d8615 --stat`; project-venv `python -m pytest`
  over the affected trust surface (310 passed, 1 skipped) and the enrolled Alert Center CI command
  (192 passed, 1 skipped); `python scripts/check_contract_delta.py --base origin/main` (0 introduced,
  0 inherited on the exact semantic head); 16/16 isolated canonical-builder Chrome/CDP matrix;
  independent Sonnet read-only review APPROVE, output SHA256
  de59e41cab4ddce6c04d0d178e4f47ae62670d29fad805b2fa29283c910345a4.
scope:
  - macro
  - engine/btc_impulse_radar.py
  - engine/signal_evidence.py
  - engine/btc_alerts.py
  - engine/alert_triage.py
  - engine/signal_lab.py
  - templates/signal_lab.html.j2
confidence: verified
---

# Historical observation is not current alert authority

The trust boundary is intentionally asymmetric: history is retained, authority expires.
A future repair must not “clean up” historical fires by deleting them, and must not make them
current again by trusting an old `tier=act`, issue-time prose, alert type, or an incomplete gate row.
