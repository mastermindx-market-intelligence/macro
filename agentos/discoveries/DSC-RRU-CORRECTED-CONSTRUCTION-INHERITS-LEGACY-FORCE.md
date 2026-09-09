---
key: RRU-CORRECTED-CONSTRUCTION-INHERITS-LEGACY-FORCE
claim: >
  Against Macro eb9e91961ddc4f3043d0dad358602525e66eccda, attaching the existing
  runner-shaped can_force grant to the corrected, unreviewed Risk Radar candidate
  lets the actual international override impose a 26-point ceiling and forced
  Risk-off message. The forward-entry serializer also drops composition and method.
falsifier: >
  Run python3 research/grey_deer/RRU_DOWNSTREAM_ACCEPTANCE_2026_09_09.py --scope authority
  and python3 research/grey_deer/RRU_CONSTRUCTION_SERIALIZATION_2026_09_09.py.
  A corrected-construction payload remaining unbound and retaining its composition
  through the actual serializer would close the respective counterexamples.
so_what: >
  Do not release corrected arithmetic behind a card-only calibration disclaimer.
  The existing audit/eligibility owner must bind evidence to the assessed construction;
  the existing policy owner must adjudicate any transition of established restrictions.
  Do not globally clear permission, silently grant it, or create another policy store.
kind: landmine
verified_at: 2026-09-09
verified_by: >
  research/grey_deer/RRU_DOWNSTREAM_AUTHORITY_RED_2026_09_09.txt;
  research/grey_deer/RRU_CONSTRUCTION_SERIALIZATION_RED_2026_09_09.txt;
  engine/intl_run.py:118,143 and engine/market_state.py:682 at eb9e919.
scope: ["WS:GREY-DEER-RISK-INTELLIGENCE", "engine/risk_radar_intl_audit.py", "engine/market_state.py", "engine/intl_run.py"]
confidence: verified
---
# Evidence boundary

Two separate two-test probes each returned one expected assertion failure and one
legacy control pass, zero errors. Numerical candidate tests separately passed 20/20.
The force probe used synthetic market inputs and a synthetic old-grant attachment;
it did not query the real scorecard, grant authority, or prove a current live cap.
The serialization probe called only the actual pure entry constructor, with ledger
path/read functions guarded against use. No forward log was opened or advanced.

At current-main read aa902f88d746bbc92279bc41903fc8bfa37ff11e, the corresponding
engine, audit, runner and three affected consumer source blobs matched the fixture.
This is source-comparison evidence, not whole-PR source custody or production proof.
The candidate remains uninstalled; these two release counterexamples remain open.
