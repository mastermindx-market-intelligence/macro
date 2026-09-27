# Special Situations Horizontal Catalyst Integration — Implementation Plan

> **For agentic workers:** implement task-by-task with red→green tests and independent review. This plan extends incumbent owners; it does not authorize a parallel event, identity, lifecycle, ranking or publication plane.

**Goal:** correct transaction/affected-security semantics and connect existing Special Situations events into Catalyst Intelligence without duplicate events or recommendations.

**Spec:** `research/SPECIAL_SITUATIONS_HORIZONTAL_CATALYST_R2_2026-09-27.md`

**Current base at plan freeze:** Macro `170456b0013bf833a952498daf6a44a2153d70c6`; protected Mastermind procedure `429bf720788f8c68e76a576b7b3fedd8f8ad423a`. Executors must fresh-read current protected procedure and reconcile current source before modifying.

## Global constraints

- Preserve existing Special Situations event history and source provenance.
- No new collector/event store/identity service/lifecycle authority/ranker/queue/publication plane.
- No automatic recommendation, sizing or trade authority.
- Treat PR #6793 as incumbent F09 work requiring reconciliation; do not wholesale revive a branch that was 3,198 commits behind at plan freeze.
- Source-origin deduplication and transaction identity precede “confirmation” counting.
- One security may have multiple event cases; one transaction may affect many securities.
- Missing enrichment/identity/economics is unavailable or pending, never zero/negative.
- Preserve known-at clocks and old published snapshots.
- Paper mutation remains blocked until the guarded catalog is accepted; no cross-carrier bypass.
- Use least-scarce capable workers for mechanical implementation; preserve principal review for semantic/financial decisions.

## Review focus

1. **Parent/control events:** indirect fund/subsidiary exposure must not turn the affected security into the transaction target.
2. **Several transactions at one issuer:** close/termination of one agreement must not terminalize another.
3. **Repeated source origin:** press release + several registrant 8-Ks must not become independent confirmations.
4. **Partial EFTS enrichment:** authoritative discovered filings with missing metadata must remain in measurable pending coverage.
5. **Historical revision:** a corrected/revised source invalidates only dependent cases and never rewrites an earlier known-at-time publication.

---

## Task 1 — Freeze the real MGLD/USCF regression

**Primary files:**
- Test: `tests/test_special_situations.py`
- Test: `tests/test_special_sits_intel.py`
- Fixture: reuse existing test-fixture conventions; do not commit proprietary full filing bodies.

**Consumes:** current `classify/build_situations/snapshot/mastermind_emit` behavior.

**Produces:** failing tests demonstrating:
- source says TMC/MGLD is direct target;
- USO/USL/UNG/UGA/BNO/CPER/UNL are indirect affected registrants;
- one source-origin transaction cannot yield seven independent direct-target Going-Private rows;
- affected registrants remain visible as context rather than disappearing.

- [ ] Add an authored fixture distilled from the SEC relationship chain: TMC → USCF Investments → United States Commodity Funds LLC → funds.
- [ ] Write a RED test asserting direct-target identity is MGLD while a fund row is `affected_through_general_partner_control` or equivalent owner-approved semantic.
- [ ] Write a RED test asserting source-origin confirmation count stays one for the transaction.
- [ ] Write a RED test asserting affected fund context remains inspectable.
- [ ] Run the narrow test selections and retain failure text proving current behavior, not fixture syntax, causes RED.

**Failure gate:** if current identity/event owner lacks an accepted relation interface, stop implementation at an explicit owner decision request. Do not mint a local global identity.

---

## Task 2 — Add a bounded relation-aware projection through incumbent ownership

**Candidate paths, subject to owner adjudication:**
- existing Special Situations projection module(s), preferably a focused helper rather than more logic in the large engine file;
- current Company/Event/GMI adapter path if it already owns event→entity relations;
- tests from Task 1.

**Consumes:** source-native event/filing rows and incumbent entity/security identities.

**Produces conceptually:**
```
event_ref
event_family
direct_parties[]
affected_relationships[]
source_origin_group
relationship_status
known_at
```
Exact persisted fields belong to incumbent semantic owners.

- [ ] Locate the current canonical event/entity relationship interface at execution head.
- [ ] Extend only the incumbent interface if necessary; no second registry.
- [ ] Map `target/acquirer/seller/controller/general_partner/sponsor/affected_security` separately.
- [ ] Preserve unresolved relationships with explicit status.
- [ ] Make Task 1 tests GREEN.
- [ ] Add negative tests: similarly named entity; retired ticker; missing security identity; foreign parent; several affected funds.

**Acceptance:** one canonical transaction can project to multiple typed affected securities without copying target role.

**Rollback:** disable/read past the additive relation projection; preserve raw events.

---

## Task 3 — Transaction-specific lifecycle

**Primary files:**
- `engine/special_situations.py` or a narrowly extracted incumbent helper
- `tests/test_special_situations.py`

**Consumes:** event_ref/transaction grouping from Task 2.

**Produces:** lifecycle state attached to transaction identity, not `(cik, category)`.

- [ ] Write RED fixture with Issuer X / Deal A plus unrelated Deal B completion.
- [ ] Assert Deal A remains nonterminal when only Deal B closes.
- [ ] Write RED fixture with later Deal A termination and assert only A terminates.
- [ ] Add amendment lineage and source-known ordering.
- [ ] Replace issuer-wide terminal propagation only after RED is observed.
- [ ] Verify existing single-deal cases retain their old correct result.

**Required lifecycle states:** family-specific states may differ, but terminal semantics must distinguish closed/completed, terminated/withdrawn and unresolved/delayed.

**Failure gate:** an unlinked terminal filing cannot be guessed onto a transaction. Preserve it as unmatched terminal evidence.

---

## Task 4 — Preserve partial enrichment coverage

**Primary files:**
- `collectors/special_situations.py`
- collector tests associated with Special Situations

**Consumes:** daily-index authoritative candidates plus EFTS per-accession metadata.

**Produces:** three distinct cases:
1. enriched and qualifying;
2. enriched and explicitly nonqualifying;
3. discovered but enrichment unavailable/unknown.

- [ ] RED test: two discovered 8-Ks, EFTS returns metadata for only one.
- [ ] Assert the missing accession remains a pending unknown candidate with first-seen provenance.
- [ ] Assert an explicitly observed non-special Item is still dropped.
- [ ] Assert a total EFTS outage preserves all unknown candidates as today.
- [ ] Add observable pending/coverage counts.
- [ ] GREEN with no duplicate network path or retry plane.

**Budget:** no page-request network; use existing collector cadence and caps.

---

## Task 5 — Security projection with multiple event cases

**Primary files:**
- `engine/special_situations.py::mastermind_emit` or successor owner-native projection
- brain/context consumer tests
- Company Intelligence / Catalyst projection adapter only if current owner approves

**Consumes:** transaction-specific cases from Tasks 2–3.

**Produces:** one security projection containing multiple material event references plus an explicitly selected lead case when justified.

- [ ] RED test: one ticker with two simultaneous material events; both survive.
- [ ] RED test: newest low-materiality event does not erase older active high-materiality case.
- [ ] Add source-origin/dependency references to prevent double counting.
- [ ] Keep compatibility fields only where current consumers need them; mark derived lead selection.
- [ ] Trace through actual current brain/Catalyst readers.

**Acceptance:** no browser or downstream model needs to reconstruct hidden event multiplicity from prose.

---

## Task 6 — Alt-Data deduplication and role semantics

**Primary files:**
- existing Special Situations → Alt-Data handshake owner
- `engine/altdata.py` / models only if incumbent owner agrees
- tests for exact consumer

**Consumes:** event_ref, source_origin_group, security_role.

**Produces:** a context channel that can distinguish one event affecting many securities from independent evidence.

- [ ] RED test on the MGLD/USCF fixture: seven affected funds do not create seven independent confirmations of the same transaction.
- [ ] Preserve per-security presence when useful to a fund user.
- [ ] Ensure the parent target and affected funds do not share merger-arb economics.
- [ ] Ensure channel score/weight is not multiplied by source duplicates.
- [ ] Keep current context-tier authority until evaluation explicitly promotes anything.

**Acceptance:** event reach expands; evidence independence does not.

---

## Task 7 — Economic invalidation into Catalyst Intelligence

**Owners involved:** Company/Event/GMI relation owner, Financial Intelligence/Capital Structure, specialist case owner, recommendation/entry, publication.

**Consumes:** material event revision and affected relationship.

**Produces:** scoped `needs_review/invalidated_dependency` behavior and eventually revised conditional equity scenarios through existing owners.

- [ ] Build a shadow fixture where a controller/licensing/divestiture change touches one economic assumption.
- [ ] Assert only dependent cases enter review.
- [ ] Assert independent scientific/procurement/project probabilities are unchanged.
- [ ] Assert old recommendation snapshot remains retrievable.
- [ ] Recompute conditional diluted equity values only after accepted financial inputs.
- [ ] Recommendation owner decides the new stance; Special Situations never self-promotes it.

**Acceptance:** a real corrected corporate event can change an affected investment case without creating a second recommendation.

---

## Task 8 — F09 transaction terms reconciliation

**Dependency:** semantic owner review of PR #6793 against current main.

- [ ] Compare its source-bound term observation semantics with current accepted contracts.
- [ ] Adopt only compatible bounded pieces through incumbent path ownership.
- [ ] Keep exact date/price/currency/source-byte requirements for precise spread math.
- [ ] Do not assign cash spread math to indirect USCF fund rows.
- [ ] Test cash, stock, mixed consideration, unknown exact close date and corrected terms separately.

**Acceptance:** one owner computes each premium/spread datum; no stale LLM-extracted precision or fabricated annualization.

---

## Task 9 — Evaluation / shadow qualification

**Consumes:** corrected event/role/lifecycle projections.

**Produces:** point-in-time frozen evaluation records under the existing evaluation owner.

- [ ] Reconstruct discovery denominator including pending enrichment.
- [ ] Freeze predictions before outcomes.
- [ ] Evaluate family × role × stage rather than one generic channel.
- [ ] Separate event outcome, durable economics, stock return and benchmark return.
- [ ] Test direct targets separately from indirectly affected securities.
- [ ] Control overlapping/common-cause events.
- [ ] Add data-family ablations for options/positioning/flow.
- [ ] Require prospective shadow evidence before any promotion.

**Baselines:** current event-family context; price-only/sector matched baselines where meaningful; no “best historical horizon” as automatic production selection.

**Release gate:** independent method review plus accepted evaluation owner decision. CI alone is not promotion.

---

## Task 10 — Product implementation after native design admission

**Current Paper identity:** file `01M2WGNCX9475G79JRKJTCM08P`; BioCatalyst page `p-K-0`.

At plan freeze, Paper server 0.5.12 was observed, but write schema was not accepted: current catalog `8cd27488...`, expected `ca90a537...`; a later catalog call returned upstream unavailable with retry disallowed. No edit was dispatched.

- [ ] Re-read current Paper procedure and inspect the exact file.
- [ ] Require accepted catalog/write schema before first mutation.
- [ ] Coordinate a distinct Special Situations page/artboard with the design owner; no competing global shell.
- [ ] Implement entry/list, event graph/timeline, economic scenarios, evidence/counter-evidence, expectations detail and decision-change states.
- [ ] Cover desktop/mobile, dark/light, keyboard/touch and loading/partial/stale/denied/error/review-pending states.
- [ ] Inspect actual Paper screenshots and record node IDs.
- [ ] Translate accepted design into existing production frontend only after source ownership is reconciled.
- [ ] Browser-test the served journey separately.

**Rollback:** existing Special Situations route remains available until representative real journeys pass.

## Required implementation return

Every slice returns:
- exact protected-procedure commit;
- repo/base/head and changed paths;
- owner/path lease and lifecycle state;
- RED evidence before implementation;
- GREEN targeted tests;
- broader relevant regression result;
- actual source/event/security/financial/publication receipts;
- independent review disposition;
- performance/freshness/coverage observations;
- external effects and effect-unknown state if any;
- rollback boundary;
- exact next dependency.

Do not call dispatch START, CI acceptance, merge production proof, or Paper output shipped software.
