# R1 implementation handoff — post-MO-J1 continuity deltas

Research identity: `marketontology-parity-workflow-research-20260926-sol-r1`
Parent: `macro#6819`
Return revision: `20260926-sol-r1`
Acceptance: `accepted:false`

## Gate 0 — MO-J1 remains first

No packet below starts before Sol Meta-CEO accepts R1 and MO-J1 reaches its existing joined-journey acceptance or exposes a concrete failing seam.

Current order:
1. release/reconcile Terminal #746;
2. run merged #744 signed-in Phase B proof when lawful authenticated session is available;
3. release/reconcile Macro #7781 through its existing merge-on-green owner;
4. MO-J1A only after #7781 is accepted/merged + fresh source-collision read;
5. MO-J1B only after #746 closes;
6. prove complete signed-in joined journey.

No substitute PR, identity plane, store, scheduler, monitor, or ontology graph.

## P1 — Portfolio transmission-change continuity

**User job:** when transmission changes, show which actual holdings entered/left an armed chain since the prior review.

**Admission:** existing F04 private Portfolio/Watchlist overlay + `MO-PAID-085`; display/research context only.

**Reuse owners:** TXI chain state; `scripts/build_portfolio_ctx.py`; `templates/watchlist_risk.js`; `engine/portfolio_changes.py`; `/api/portfolio/changes`; existing digest owner.

**Observed gap:** current risk UX knows armed-chain membership; `portfolio_state_digest.v1` does not retain it.

**Smallest packet after preflight:**
- new additive digest schema version, not silent v1 mutation;
- bounded display-only chain projection already present in `portfolio_ctx.v2`;
- neutral entered/left/state-changed diff lines;
- preserve safe-text/cardinality rules;
- preserve TWO-ORGANISMS law: no shares/cost basis/weights/account ids/user-activity timestamps; never log digest/change lines;
- missing/unavailable chain context cannot become false “cleared”;
- reuse existing consumers; no new alert engine.

**Likely files:** `engine/portfolio_changes.py`, `tests/test_portfolio_changes.py`, plus exact current consumer discovered immediately before build.

**Acceptance:** pure transition/malformed/missing tests + ordinary signed-in consumer proof showing a fixture-held name enter/leave an armed chain with continuation to existing transmission surface.

**Owner split:** A/Macro data+diff; B only if Terminal is current consumer; Sol integration acceptance.

**Falsifier:** skip if post-MO-J1 source already retains chain membership canonically. If privacy rejects chain ids in client digest, proof/UX only.

## P2 — F07 valuation-event → Thesis amendment continuity

**User job:** when source-grounded evidence changes a valuation assumption, expose the evidence/model revision and let it become a proposed update to the existing Thesis without silent publication.

**Admission:** `MO-PAID-022` + `MO-PAID-046` + `MO-PAID-054`; later `MO-PAID-047` for existing monitor continuation.

### P2A — F07 evidence-pointer projection preflight + contract

Owner: A / current F07 source owner.

Resolve:
1. current canonical route/artifact for projecting `assumption_change_proposal.v1` / scenario to Terminal;
2. whether source/model/correction identity fits existing K1 EvidenceRef;
3. rights-safe display fields.

Closed output only: issuer/security identity through existing owners; proposal vs abstention; bounded assumption metadata; source/model revision/clocks; K1 pointers; authority/rights state.

Forbidden: confidence/probability/rank/size/target/score, copied raw source payload, Thesis/user identity, new store.

Acceptance: proposed, abstained, stale/corrected, source-unavailable, rights-blocked, identity-mismatch contract tests.

### P2B — Terminal proposal composition

Owner: B / Terminal Thesis owner after P2A acceptance.

From existing Company Intelligence/Thesis context, create one ordinary `thesis_amendment_proposals` row against the current Thesis version using only P2A K1 pointers.

Rules:
- user owns Thesis;
- Company Intelligence security/lineage matches Thesis through current identity authority;
- `amended_from` is current read version; stale version fails closed;
- F07 abstention never manufactures a proposal;
- body remains words-only under existing judgement-key ban;
- accepting loads/marks accepted only;
- human publishes through ordinary revise;
- no DB migration.

Acceptance journey:
`Company Intelligence evidence → F07 delta → amendment proposal + K1 refs → accept into editor → human publish revise → reopen immutable version delta`.

Negative proof: wrong user/company, stale generation/version, malformed pointer, rights block, F07 abstention.

**Falsifier:** if post-MO-J1 source already projects F07 through Company Intelligence/K1, delete P2A. If K1 cannot represent source/correction identity, stop at K1 owner.

## P3 — Issuer-event continuity is proof-first

Primitives already exist under `MO-PAID-046/047/053/054`, plus #742 navigation, #744 journey prover and #746 What-changed UX.

Decision: no new issuer-event engine, RMS store, or monitor.

After #746 release + lawful signed-in session:
1. run #744 Phase B on served release;
2. run MO-J1 through Company Intelligence → Thesis create/revise → reopen/What changed → existing condition → supported later return;
3. exercise wrong-user, stale/corrected evidence, identity-missing, monitor-unavailable states;
4. record exact served release/receipts;
5. commission code only for a concrete failed seam.

Falsifier: successful real-path proof closes P3 with no implementation.

## Meta-CEO acceptance checklist

- MO-J1 remains first.
- No recommendation creates a second identity, ontology, portfolio-risk, valuation, Thesis, evidence, scheduler, or monitor plane.
- P1 extends existing transmission context + portfolio change/digest owners.
- P2 preserves human Thesis publication authority.
- P3 may close through proof alone.
- Rights/correction identity remain explicit gates.
- Competitor numeric fields do not become Mastermind authority merely for parity.

`accepted:false`
