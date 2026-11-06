# Seat ruling R6-B04-01 — the episode evidence dossier contract (B04) is adopted with amendments; build order fixed

Fable Meta-CEO seat (session 48cdfd56), operation `prophet-us-fable-meta-ceo-20260923-001`, 2026-09-24. Authority: DEC:PROPHET-US-FABLE-META-CEO-DELEGATION; work card B04 (owner scope `engine/prophet_lab/intelligence_vector.py`, `app/prophet_lab.py`, the D5/source-family adapters). Adjudicates `research/prophet_v4/r6_program/wave2/B04_EVIDENCE_DOSSIER_CONTRACT_CENSUS_2026-09-23.md` (lane `pu_w2_b04_census`, PASS 0B/0M/1m at c1c8657b). Binding prior: R6-D03-01 (history admissible only where a source-dated point-in-time row exists; UNKNOWN ≠ absent), R6-PREREG-01 B4 (`PUBLIC_INFO_REPLAY` is a named class, never pooled with observed-as-run), the rights register (`research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`), D07 (OPEN), the B04 release limit (no narrative gate waiver, no full-document duplication, no new evidence warehouse, no unlicensed prose leakage).

## Accepted from the census
1. Q2 coverage stands as measured: cases 1 and 6 COVERED, 2 and 4 PARTIAL, 3 and 5 BLIND. The two BLIND cases are the reason B04 exists and are built first.
2. Q6(a) wrapper `prophet.episode_evidence_dossier/v1` around the UNCHANGED all-false `prophet.intelligence_vector/v1`; the closed reason-code vocabulary (`NOT_CAPTURED_AT_DECISION`, `CORRECTED_LATER`, `HISTORICAL_EVENT_SET_UNAVAILABLE`, `IDENTITY_BINDING_CONFLICT`, `RIGHTS_INTERNAL_ONLY`, `RIGHTS_NOT_A_SOURCE`, `CONFLICTING_SOURCE_CLOCKS`, `EXACT_LINEAGE_UNAVAILABLE`, `UNKNOWN`) with the paired plain EN/ZH sentences adopted verbatim as the initial copy; codes are never rendered to users.
3. Q6(b) closure rule, Q6(c) dual-view rule, Q6(d) rights-gate rule, Q6(e) `evidence_class {state, value, basis}` with `NOT_ASSERTED / null / D07_OPEN` until D07 registers a per-study class.

## Amendments (binding on every B04 build unit)
A1. The rights posture map is machine-readable and versioned: `config/prophet_source_rights_postures.yml`, hand-derived from the register, one row per register family with `posture ∈ {USER_FACING, USER_FACING_WITH_LIMITS, INTERNAL_ONLY, NOT_A_SOURCE, ABSENT}`, `register_ref` (the register section), and `limits_code` where applicable; NO commercial terms, prices, or licence text. A test pins that every family named in the register has exactly one row and that no posture is wider than the register states.
A2. `evidence_class.basis` is closed: `D07_OPEN` or `D07_REG:<registration artifact path>`; `value ∈ {OBSERVED_AS_RUN, PUBLIC_INFO_REPLAY, RETROSPECTIVE, null}`; a `value` is set only when `basis` names a merged registration artifact.
A3. The `current` view carries `decision_admissibility=false` and `view_basis=RESEARCH_KNOWN_NOW` unconditionally; a build that lets `current` inherit any original admissibility flag fails its own tests.
A4. Every authority boolean (rank, gate, size, signal, entry, execution) stays false in both views; the wrapper adds no score, no confidence number and no narrative.
A5. The route-boundary rights test is mandatory in the same PR as the gate (Q6(d)4): an INTERNAL_ONLY family fixture must produce a lane-level typed reason and NO value, hash, document id, field path or prose anywhere in the serialized response (assert on the JSON text, not on a parsed field).
A6. The proof event is the one real dossier candidate the wave-0 C census found (AAPL FY2026 Q3) plus committed fixtures for each of the six cases; no `data/` write, no ledger/outcome artifact opened.

## Build order (each a separate fabric lane; each PR carries its own tests; no unit self-merges)
- **B04-A** = wrapper skeleton + reason-code map + `evidence_class` NOT_ASSERTED + `HISTORICAL_EVENT_SET_UNAVAILABLE` typed absence (census units B04-1, B04-2 stub, B04-4). Owned: `engine/prophet_lab/intelligence_vector.py`, `app/prophet_lab.py`, tests. Proves cases 1, 3, 4, 6 at the route.
- **B04-B** = rights posture map + route-boundary gate (unit B04-5; amendments A1, A5). Proves case 5.
- **B04-C** = `current` view + correction comparison + EN/ZH renderer (units B04-3, B04-6; amendment A3). Proves case 2 and the full six-case matrix end-to-end.
- **B04-D** (blocked on D07) = class propagation once a registration artifact exists (unit B04-2 proper; amendment A2).

## Reversibility
Additive wrapper over an unchanged vector; each unit reversible by revert; no data contract of any consumer changes until B04-C.
