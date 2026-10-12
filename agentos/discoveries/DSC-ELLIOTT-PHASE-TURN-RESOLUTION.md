---
key: ELLIOTT-PHASE-TURN-RESOLUTION
claim: >
  At macro commit 4b1f8fddcc4eb6f36133fca4d42018678b74d30b, the existing
  detect_turns output has date-only timestamps and month/kind turn identifiers;
  it cannot, without an owner-approved representation change, serve as distinct
  timestamped intraday wave endpoints merely by reducing its reversal threshold.
falsifier: >
  Reproduce the frozen function ASTs from Git blob
  9e726868f6c218a84cd50a9f976c77c3a347ac6c and run the synthetic contract fixtures.
  Distinct intraday timestamps and collision-free IDs in those exact outputs
  would disprove the claim. A subsequent owner change may supersede this
  version-scoped finding but does not alter the historical result.
so_what: >
  Reuse the existing turn owner and its turn-epoch law, but do not plug the coarse
  payload directly into a four-hour Elliott confirmation or event-alignment
  study. Preserve source-bar precision, provisional status, initialization and
  actual availability in the existing owners' contracts. Do not create another
  swing, event, identity, replay or trial plane. This discovery is absorbed into
  WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE W1/W2-0; it admits no market effect test,
  and generic Elliott/Fibonacci triage and protected studies stand.
kind: constraint
verified_at: 2026-09-11
verified_by: >
  engine/cycle_ontology.py:592-711 at
  4b1f8fddcc4eb6f36133fca4d42018678b74d30b; full source blob checked on the
  authorized Mac; isolated TurnParams/_yf/detect_turns AST hashes matched;
  research/technical_opportunity/elliott_phase/source_contract_probe.py and
  research/technical_opportunity/elliott_phase/source_contract_probe_results_2026-09-11.json;
  full characterization archive retained with the conversation research packet.
scope:
  - engine/cycle_ontology.py
  - research/technical_opportunity/elliott_phase/**
  - WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE
confidence: verified
---

## Evidence and limits

The dense daily fixture contains 29 confirmed turns but only two distinct IDs.
The list retains all rows; mapping it by ID would retain two. This is NOT a
finding that a current production consumer loses 27 observations. No production
impact was measured and no shared source or identity migration was applied.

The intraday fixture contains distinct five-minute observations whose serialized
pivot/confirmation dates are identical. The detector is a broader-cycle primitive,
not a full Elliott parser. Its completed geometry was stable across the synthetic
prefix-extension checks. That existing causal capability should be retained.

Structural endpoints can differ from price extrema under the published wave
method. A full wave interpretation additionally needs its own supporting
subdivision and parent evidence, each with a truthful available-at time. A
necessary six-point constraint is not a complete wave count.

## Continuation

See:

- `research/technical_opportunity/elliott_phase/ELLIOTT_SOURCE_COMPATIBILITY_FINDING_2026-09-11.md`
- `research/technical_opportunity/elliott_phase/ELLIOTT_E0_ADMISSION_PROPOSAL_2026-09-11.md`

The sole current proposal is anticipation-first and remains
`NOT_ADMITTED / HOLD_FOR_TOI_W1_AND_W2_0`. Continuation and entry are separate
future trials. TOI W1 must qualify the method and local estate; TOI W2-0 must
qualify data, clocks, corrections, coverage, rights, identity, and Terminal
parity. Compression Release remains TOI's first proving vertical. No predictive
outcome read, source refresh, standalone Elliott workstream, or signal authority
is created by this discovery.
