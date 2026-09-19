---
key: SIGNAL-LAB-D2-ROLLOVER-RETAINS-OUTCOME
claim: >
  A latest-row-only D2 projection hides completed research after daily rollover.
  The existing ledger must expose current observation and explicitly historical
  latest completed outcome separately; a non-fire is not a prediction miss.
falsifier: >
  Run tests/test_btc_d2_research_journey.py and tests/test_signal_lab_alert_trust.py
  on macro PR 7249. This finding is falsified if a pending new observation hides
  the prior completed outcome, no-fire renders as a miss, or a damaged current
  envelope silently becomes an older good observation.
so_what: >
  Continue the existing PR 7249 carrier, preserving source/outcome/correction
  generations in data/vector/impulse_ledger.jsonl. Reuse its saved source-hashed
  verification and browser evidence instead of reconstructing failed chats.
  Parent PR 7173, independent review, binding CI and installed admin proof remain
  separate release dependencies; research evidence never authorizes trades.
kind: architecture
verified_at: 2026-09-17
verified_by: >
  PR 7249; review_evidence/signal-lab-d2-20260917/verification.json binds all eight
  candidate source hashes; fresh recovery-verification.log reports 233 passed;
  browser/receipt.json records ten isolated canonical-builder cases, not production.
scope: [macro, engine/btc_d2_research.py, engine/btc_impulse_ledger.py, templates/signal_lab.html.j2]
confidence: verified
---

Capability remains BUILT_NOT_PROVEN. No new workstream or runtime owner is implied.
The retained-file guard and atomic replacement protect incumbent writes; they do
not claim authenticated external rollback detection or create a second store.

## Release frontier

Child semantic source is frozen at bdd5ed2226f9299475685d3c0ea31cf0259bd12f.
Parent PR 7173 has completed binding CI, but newer integrated dependencies still
require independent review. The exact parent integration passed 192 tests with one
skip and manifest validation; its immutable receipt is in the existing PR evidence.
The independent-review lane is WAITING_CAPACITY / needs_placement: no callable
approved reviewer admission is available in this session, and no START is claimed.
Do not replace this gate with self-approval, raw provider spawning, or Chairman
account-selection work. Parent release, child supported-base CI and installed
authenticated-admin proof remain distinct and unaccepted.
