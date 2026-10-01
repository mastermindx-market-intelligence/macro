---
workstream: WS:PROPHET-US-V4-RECOVERY
session: sol/prophet-earnings-semantics-v1-20260929
model: sol
ended_because: blocked
prs:
- 8189
mission: Advance Prophet investment quality through connected factual D5 detail and
  pre-result issuer-guidance revision/delivery algorithms. MISSION_COMPLETE:false.
state_before: 'The versioned earnings calculations existed on #8189 but the existing
  episode API did not present their source-qualified comparison.'
changed:
- path: engine/prophet_lab/earnings_dossier.py
  what: Exact native-vector/Q06-source-bound explanation, no ranking, new store or
    second reader.
- path: app/prophet_lab.py
  what: New authenticated earnings-detail resource reuses one existing B1/D5 read.
- path: tests/test_intelligence_vector_units.py
  what: Real-source span replay and selected-vintage comparison tests.
- path: tests/test_prophet_lab_api.py
  what: Actual API pipeline/auth/kill/absence and unchanged-native-endpoint proofs.
- path: tests/fixtures/prophet/q06_source_contract.v0_2.json
  what: Byte-identical test-only source record; production never loads the test path.
- path: research/prophet_v4/earnings_semantics_v1/D5_CONSUMER_2026-09-30.md
  what: Capability, exact proof and held deployment/source/UI gates.
- path: engine/sue.py
  what: Source-known issuer-guidance revision and latest-pre-release delivery, separate
    from consensus; existing dossier integration.
- path: tests/test_us_prophet_fusion.py
  what: 35 additional source-clock, guidance-vintage, range-change and dossier cases.
- path: research/prophet_v4/earnings_semantics_v1/ISSUER_GUIDANCE_2026-09-30.md
  what: Primary-source research, actual-vs-updated-guidance decomposition, limits
    and next experiment.
- path: research/prophet_v4/earnings_semantics_v1/MICRON_GUIDANCE_VINTAGE_CASE_2026-09-30.json
  what: Three verified public sources with exact amounts/dates and raw-capture hashes;
    historical system ingestion remains unknown.
verified:
- claim: Native earnings and D5/API tests pass with one-reader factual consumption.
  command: python3.12 -m pytest tests/test_us_prophet_fusion.py tests/test_intelligence_vector_units.py
    tests/test_prophet_lab_api.py -q
  result: 231 passed /12 warnings/0 skips; native earnings,D5/API with synthetic chronology
    and raw SEC/source-contract fixtures; logSHA256 9ee831836454bec19c58d2b2b56a79c30f5a2e530496a5fe7e6cd1d8d1ac43b1.
- claim: The tests distinguish wrong revision acceptance and a disconnected result
    path.
  command: python3 /Volumes/Mastermind/evidence/prophet-earnings-d5-20260930/fault_controls.py
  result: Two intended assertion failures; original bytes restored.
- claim: Issuer-guidance tests distinguish obsolete-forecast use and false history
    completeness.
  command: python3 /Volumes/Mastermind/evidence/prophet-earnings-d5-20260930/guidance_faults.py
  result: Two intended assertion failures; original source restored.
unverified:
- claim: Exact new-head CI/current-base release and ordinary served/UI proof.
  what_would_verify: Required concluded checks, Q06 source release, actual deployment,
    signed-in UI/read and ordinary refresh.
- claim: Improved selection/return/risk performance.
  what_would_verify: Separately accepted source and registered same-population experiment;
    none opened here.
unresolved:
- Q06 source method accepted but its existing CI registration/release remains outstanding.
- Frontend/CI-owner combined inspection and release-binding source inspection were
  refused before dispatch; no retry/proxy.
- 'Native clock/index #7426 and workspace feature #7870 remain incumbent work, untouched.'
- The new factual reconstruction is not an original as-run recommendation and cannot
  be backfilled into old grades.
- Public Micron source dates/amounts are verified; historical system ingestion/market
  execution and financial predictive value remain unproven.
next_actions:
- 'Consume exact-head CI on existing #8189; resolve only actual findings.'
- 'Close the existing #8069 source-release dependency and permitted ordinary frontend
  integration; prove paid read and refresh.'
- Continue earnings/sector/risk scientific units under existing source/outcome owners
  without new policy/identity/price stores.
- Qualify issuer-guidance source history and the existing B15 incremental experiment;
  do not count prior-public upgrades as new earnings surprises.
do_not_redo:
- 'Do not recreate #8069 source records or #7426 clock/index work.'
- Do not regrade prior C1/H1/Cycle outcomes or enable a ranking/entry policy.
- Do not retry the refused frontend/CI inspection or release-binding source read through
  another route.
danger_areas:
- Original source-vintage reconstruction must not be mislabeled an original as-run
  recommendation.
- Q06 source method acceptance and source release are separate; its canonical record
  is not yet installed on this base.
- D5 current-manifest event coverage and existing clock/index production limits are
  inherited, not repaired by this consumer.
---

# Earnings/D5 source checkpoint

MISSION_COMPLETE:false. User-selected Pro; served identity unverified. No new child, automatic wake, source-writer transfer or live financial authority. This checkpoint saves the current unit; it does not complete Prophet.
