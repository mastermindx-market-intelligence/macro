---
key: NEWS-IMPACT-V1-REGISTRATION-INELIGIBLE-ON-MAIN
claim: >
  The committed section 11 registration (ni-section11-registration-1) no longer matches
  the code on main. PR #9732 bumped engine/news_impact/producer_facts.py to
  ni-producer-facts-2 (a quantity_terms leaf) and added
  section11_registration.require_registered_implementation, which compares every
  registered code version with the loaded code and refuses on any drift; on main at
  d533508a the guard exits 1 with REGISTERED_IMPLEMENTATION_MISMATCH on producer_facts
  (registered ni-producer-facts-1, current ni-producer-facts-2). The guard is also
  hard-bound to the v1 file's sha256, so a mutated or regenerated registration fails with
  HISTORICAL_REGISTRATION_CHANGED before any other check.
falsifier: >
  PYTHONPATH=. python3.12 -m engine.news_impact.section11_registration --check exiting 0
  on origin/main; or require_registered_implementation accepting a registration whose
  code_versions differ from current_code_versions().
so_what: >
  No system-under-test run, GLM gold scoring or section 11 report may be produced from
  main under the v1 registration: the assembler (engine/news_impact/section11_report.py)
  calls the same guard and refuses. The route is a separately admitted
  ni-section11-registration-2 with the same seeds, populations, critical slots and
  frontier draw and the current code versions, plus a DEC recording that #9732 landed
  before any gold existed; never a rewrite of the v1 file. Tests of consumers pass the
  guard by monkeypatching current_code_versions to HISTORICAL_V1_CODE_VERSIONS.
kind: constraint
verified_at: 2026-10-30
verified_by: >
  PYTHONPATH=. python3.12 -m engine.news_impact.section11_registration --check on
  origin/main d533508a4e66, exit 1 REGISTERED_IMPLEMENTATION_MISMATCH producer_facts;
  engine/news_impact/section11_registration.py require_registered_implementation and
  HISTORICAL_V1_SHA256; PR #9732.
scope:
  - "engine/news_impact/section11_registration.py"
  - "engine/news_impact/section11_report.py"
  - "engine/news_impact/producer_facts.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/section11/**"
confidence: verified
---

# The v1 section 11 registration is ineligible on main

#9732 moved producer_facts to version 2 and added a fail-closed implementation guard, so
the frozen v1 registration refuses every consumer on main. The fix is a v2 registration
with a DEC, not an edit of v1.
