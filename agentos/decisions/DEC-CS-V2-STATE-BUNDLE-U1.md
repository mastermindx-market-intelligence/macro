---
key: CS-V2-STATE-BUNDLE-U1
question: >
  Masterplan task U1 (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  frozen spec SPEC_U1_API) must put the Capital Structure V2 state contract
  (engine/capital_structure/issuer_state_contracts.py, CapitalState) in front
  of a reader for the first time. Where is a CapitalState built, what does
  one nightly run publish, how does the entitled API serve the current and
  the then-known view without re-deriving facts at request time, and in
  which order does this land relative to S0 (scenario assembly)?
answer: >
  (1) An offline producer builds the state. scripts/build_capital_structure_state.py
  reads the verified compiler generation, the health horizon bound to that
  generation and the projection.json written in the same job, and publishes
  data/capital_structure/state_bundle.json (schema
  capital_structure.state_bundle.v1): one CapitalState per covered issuer,
  registration family only, all bound to the same input generations, rule
  pack and projection generation id, plus an issuer index (counts, coverage,
  dated ticker observations, path evidence keys, registration receipt) and
  an evidence index keyed manifest_id/span_id. The registration family is
  integrated by the existing registration_integration module, never
  re-implemented. (2) Whole generation or nothing: a projection generation
  mismatch, a health horizon that does not bind the verified generation or a
  failed validation refuses the run and leaves the last good bundle in
  place (atomic write shared with the projection builder). The step cs_state
  runs after cs_projection in the capital_structure job of
  .github/workflows/daily.yml and is a named producer in that job's
  checkpoint gate, so a refused state bundle also holds that night's
  capital-structure commit. (3) The API (app/capital_structure.py) only
  reads. It serves the bundle's current state, and derives the then-known
  view at a cutoff by filtering the same verified generation on the system
  available_at clock through the producer's own then_known_state function,
  after checking the issuer's inputs against the published input digest. The
  served projection generation is checked again at read time. Evidence is
  served from the bundle's evidence index by exact manifest_id and span_id;
  a text hash mismatch is a 409 and an excerpt is returned only for a grade
  that permits it and only when a retained text exists. (4) U1 is split:
  U1a (this record) serves observed facts, coverage denominators, rule
  status and history only; U1b serves scenario views and needs S0, so U1a
  lands ahead of S0.
rationale: >
  The contract already defines what a state is; what was missing is one
  place that builds it under the same generation discipline as the
  projection. Building it offline keeps the request path a transport
  boundary, as the projection API already is, and gives every issuer in one
  night the same bindings, so two responses can be compared. Re-deriving the
  then-known view through the producer's own function, on the inputs the
  bundle's digest binds, means the past view cannot drift from what the
  producer would have published. Gating the checkpoint on the state step is
  the same all-or-nothing rule every other step in that job follows. U1a
  needs nothing from S0, so holding it behind S0 would only delay the first
  reader of the contract.
alternatives:
  - option: Publish a byte-identical public static twin of the state bundle under site/, as the projection does
    why_not: Issuer research is an entitled surface. A public twin would make
      every issuer's state readable without site_full and would add a second
      publication path for the same generation.
  - option: Integrate the registration family inside the API at request time
    why_not: It would re-run the integrator on every request, make two
      responses in the same night depend on when they were asked, and move
      fact derivation into a transport module that is meant to only read.
  - option: Copy the projection's identity block into each state record
    why_not: Two copies of issuer identity can disagree. The state bundle
      binds the projection by generation id and the API reads identity from
      the projection; dated ticker history is the only identity data the
      bundle adds, because the projection has none.
  - option: Hold U1 until S0 lands and ship current, then-known and scenario views together
    why_not: Only the scenario view needs S0. Facts, coverage and history
      are ready on the merged registration family, so U1a ships them now and
      U1b adds scenario views on S0.
evidence:
  - SPEC_U1_API §0 gates 1-25, §1-§7 and §10 (frozen spec of the Fable seat a9559a4c)
  - engine/capital_structure/issuer_state_contracts.py CapitalState, CapitalInputs, AUTHORITY, INHERITED_UNAVAILABLE_CAPABILITIES (base 7e19218b)
  - engine/capital_structure/registration_integration.py integrate_registration_paths (consumed, not edited)
  - scripts/build_capital_structure_projection.py _read_bound_health and _atomic_write_one (imported by the state script, not re-implemented)
  - tests/test_capital_structure_state_bundle.py gates 1-11, tests/test_capital_structure_state_api.py gates 13-23 and 25, tests/test_capital_structure_api.py gate 24, tests/test_daily_capital_structure_job.py gate 12
affects:
  - WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
  - engine/capital_structure/state_bundle.py
  - contracts/capital_structure_state_bundle.v1.schema.json
  - scripts/build_capital_structure_state.py
  - app/capital_structure.py
  - .github/workflows/daily.yml
  - data/capital_structure/state_bundle.json
  - masterplan tasks U1b and U2 (read the state bundle; never rebuild state in the API)
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-17
---

# The state bundle is built offline once a night and the API only reads it (U1a)

Each night, after the projection is published, one offline step builds the
Capital Structure V2 state for every covered issuer, for the registration
family only, and writes it as a single file. Every state in that file uses
the same inputs, so any two issuers can be compared. If anything does not
match, the step refuses and the previous file stays in place. The entitled
API reads that file. It can also show what was known on an earlier date,
using the same inputs and the same code as the nightly step, and it serves
each piece of evidence by its exact identity. Scenario views come later
(U1b), once scenario assembly (S0) has landed. Recorded by the ORCH-U1A
orchestrator (Opus 5.5) under the Fable seat a9559a4c.
