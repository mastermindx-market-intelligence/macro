# CATALYST — Special Situations Horizontal Integration — Web CEO R2 Handoff

**Date:** 2026-09-27  
**Authority:** Chairman-directed web research/design continuation  
**Lifecycle:** CHECKPOINTED_CONTINUATION / DRAFT-HOLD  
**Production effect:** none  
**Paper effect:** none  
**Forecast/live recommendation authority:** unchanged / held

## Exact frontier

### Protected procedure
- Mastermind protected commit: `429bf720788f8c68e76a576b7b3fedd8f8ad423a`
- INDEX blob: `94d1af402598894372858793a5b1931019c5fa77`
- Skillpack: `mastermind.sol_skillpack.v1` 1.0.1, bootstrap 1
- Same-commit procedures read: COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, Paper workflow + connection reference.

### Macro
- Source base: `170456b0013bf833a952498daf6a44a2153d70c6`
- Web-CEO branch: `sol/special-situations-horizontal-catalyst-r2-20260927`
- Durable research:
  - `research/SPECIAL_SITUATIONS_HORIZONTAL_CATALYST_R2_2026-09-27.md`
  - `research/SPECIAL_SITUATIONS_HORIZONTAL_CATALYST_IMPLEMENTATION_PLAN_2026-09-27.md`
  - `research/special_situations_horizontal_reference.py`
  - `tests/test_special_situations_horizontal_reference.py`
- Related incumbents:
  - Catalyst design PR #8061 head observed `902e63be2278ec76147885268c7f89152b8cee76`, Draft/unmerged.
  - F09 PR #6793 head `ff71a149a7d8f61b072b563f16ca874f0ac08d9d`, Draft/unmerged and 3,198 commits behind current main at reconciliation. Do not revive wholesale.
  - Commission source PR #8079 head `72c966f92fbb5bba468c83780ccf6f127145ac06`.

## Mission

Revamp and connect the **existing** Special Situations system as a horizontal Catalyst Intelligence input. Do not create another generic catalyst platform. The target user outcome is investment judgment after correct event identity, economic translation, expectations and accepted policy—not an event calendar or technical setup list.

## Proven current structural defects

At the current main blob inspected for `engine/special_situations.py`:

1. `lifecycle()` groups by `(cik, category)`.
2. Terminal signals are derived issuer-wide: any Deal Termination can mark a deal arc terminated; Item 2.01 / Form 15 can mark it closed.
3. Snapshot cross-source merging uses ticker/category rather than transaction identity.
4. `mastermind_emit()` keeps only the newest situation per ticker.
5. `collectors/special_situations.py` drops an 8-K missing from a nonempty EFTS response while preserving unknowns only on a total EFTS outage.
6. The current user-facing template/build path is setup-first: top setups, grade/tier, oversold/momentum and setup-score sort precede event role/economic consequence.

These observations are source facts, not proof that every generated record is wrong.

## First real vertical — MGLD / USCF

M2 current local Special Situations store:
- `data/special_situations/events.parquet`
- 48,057 rows
- date range 2021-01-20 through 2026-09-25.

Primary source:
- USL SEC 8-K: https://www.sec.gov/Archives/edgar/data/1405528/000207187626000222/i26397_usl-8k.htm
- UGA SEC 8-K: https://www.sec.gov/Archives/edgar/data/1396878/000207187626000220/i26393_uga-8k.htm

The filings state The Marygold Companies (TMC/MGLD) entered the take-private agreement with Madison Dearborn. TMC owns USCF Investments; USCF Investments owns the fund general-partner/sponsor chain. TMC becomes private/delists. The funds are affected through control/change-of-control relationships.

Observed generated projection on M2:
- UNL, USL, BNO, CPER, UGA, UNG and USO each appeared as `Going-Private` Special Situations.
- each received its own `special_situation` Alt-Data channel at weight 0.20.
- current context also attached Going-Private historical priors/setup context to these rows.

**Ruling:** this is one canonical TMC transaction with many typed affected relationships, not seven independent fund take-privates or seven independent confirmations. Preserve affected-fund evidence; correct the direct-target role and source-origin independence.

## Frozen architecture

```
source change
 -> existing source/event owner
 -> canonical transaction + source-origin lineage
 -> typed parties and affected relationships
 -> transaction-specific lifecycle
 -> affected asset/program/security cases
 -> bounded specialist research
 -> financial/economic translation
 -> accepted recommendation review
 -> coherent publication snapshot
 -> prospective outcome/evaluation
```

No page-request research. No new queues. No duplicate identity/event/publication plane.

### Required semantic distinctions
- direct target vs acquirer/seller vs indirect affected security;
- transaction identity vs issuer;
- source evidence count vs independent confirmation;
- event completion vs durable economics vs stock profit vs benchmark outperformance;
- per-share offer terms vs aggregate asset-sale/licensing/financing economics;
- current publication vs immutable historical known-at snapshot.

### MGLD/USCF target relation
- MGLD: direct target.
- USCF Investments: controlled operating holding company affected by parent control change.
- United States Commodity Funds LLC: GP/sponsor control relation.
- USO/USL/UNG/UGA/BNO/CPER/UNL: affected securities/funds, not direct transaction targets.
- change-of-control consents and post-close strategy are material research questions.
- fund-level expected value remains unavailable until owner-native economic implications are resolved.

## Reference/TDD evidence

A pure research-only reference was written with **no IO/scoring/ranking/publication authority**.

RED:
- tests initially failed because the reference implementation was absent.
- RED receipt SHA256: `44c7c1c516e4d357ce187a4b1c105c6aee3e22bfaae5d7ec7ad6ee53536d2d4c`.

GREEN:
- 6/6 tests passed on the exact repository-style import shape.
- covers parent target vs indirect fund role;
- seven registrant rows = one independent source origin;
- unrelated deal completion cannot close another transaction;
- partial enrichment preserves unknown discovery;
- observed nonqualifying enrichment is dropped;
- event revision invalidates only dependent cases.
- GREEN receipt SHA256: `0e72646438f8ec62ad952f2a5707ef851c2d7486ca7544e3c55e355d0238f572`.

These are research contract tests, not production tests or alpha validation.

## Design direction and Paper

Current production design is technical-setup-first. R2 direction is investment-impact-first:
1. security + exact event role;
2. prepared judgment / Researching state;
3. catalyst and next decision/window;
4. conditional economic consequence;
5. primary risk/unknown;
6. affected structures and source-origin independence;
7. evidence/timeline/economics/expectations/decision history as deeper tabs.

Fallback local prototype:
- conversation artifact: `special_situations_horizontal_r2_reference.html`
- SHA256 `c349ea16175088d34f19afeb2fcaf09821e04d5452fcc80d47e2056ef40f6521`
- eight static semantic/responsive/theme checks passed.
- Chromium screenshot attempts hung in the container and were stopped by bounded timeout; do not claim browser/visual acceptance.

Paper:
- exact central file observed: `01M2WGNCX9475G79JRKJTCM08P`
- BioCatalyst page exists: `p-K-0`
- server observed: Paper 0.5.12
- file snapshot observed: `75ecb842cfeab45db7bf13179d42885c8053db3cc497d02e479e1f7da7a82340`
- write schema block: current catalog `8cd27488a3adfc19c6c36d4349b75feebc71c159253c47f8a0f8d50c27043deb`; expected `ca90a537ee97f3e371ac945a8a3b9a928ba7fac9ffaeb67e31491075a0790570`; `accepted_for_write:false`.
- later catalog call returned `UPSTREAM_UNAVAILABLE`, `retry_allowed:false`.
- no Paper edit was dispatched. Do not switch to Desktop Commander/RDC to bypass this admission block.

## DO_NOT_REDO

- Do not restart the generic Special Situations roadmap or competitor census.
- Do not recreate lifecycle/identity/event/publication systems.
- Do not create another cash-deal spread owner; reconcile F09.
- Do not infer fund takeover economics from parent ownership alone.
- Do not rerun Paper catalog on unchanged state after its explicit no-retry response.
- Do not call the local HTML a native Paper deliverable.
- Do not promote current generic Special Situations drift evidence; July report was contrary/negative for robust post-filing positive drift.

## Dependency-ordered implementation

Use `research/SPECIAL_SITUATIONS_HORIZONTAL_CATALYST_IMPLEMENTATION_PLAN_2026-09-27.md`.

Order:
1. pin MGLD/USCF regression;
2. owner-adjudicated event/entity relationship projection;
3. transaction-specific lifecycle;
4. partial-enrichment unknown preservation;
5. multi-event security projection;
6. Alt-Data source-origin dedup;
7. scoped Catalyst economic invalidation;
8. F09 reconciliation;
9. family/role/stage prospective evaluation;
10. native Paper + served UI only after write admission.

Each implementation slice must use RED→GREEN, exact owner receipts, independent review, rollback boundary and served/shadow proof as applicable.

## Self-contained Codex Astra CEO continuation

Fresh-read current protected Mastermind INDEX and required procedures from one commit. Reconcile this branch against current Macro main and all active owners before modification. Treat the documents above as approved web-research decisions, not permission to change shared schemas without their owners.

Do **not** restart research. Start with the real MGLD/USCF vertical. Through the existing Company/Event/GMI identity/relationship owner, resolve the canonical MGLD transaction and affected USCF relationships. If the existing interface cannot express controller/general-partner impact, request/implement the smallest bounded incumbent extension. Never mint a parallel universal event or relationship store.

Then commission routine bounded implementation through the existing subagent fabric using the least-scarce capable workers. Serialize shared paths. Require actual delivery, PICKUP_ACK, gated START and result/acceptance where applicable; a prepared packet or dispatch is not START.

The first accepted vertical must prove:
- MGLD remains direct target;
- USO/USL/UNG/UGA/BNO/CPER/UNL remain discoverable as indirect affected cases;
- one source-origin transaction is not multiplied into independent evidence;
- direct-target merger-arb economics are not projected onto funds;
- only dependent Catalyst cases enter review;
- prior snapshots and unaffected cases survive;
- Alt-Data does not count repeated registrant disclosures as independent conviction;
- the user-facing read clearly states role, economic consequence, next decision and unknowns.

Preserve forecast/live recommendation holds while implementing shadow/evaluation capability. No sizing/trade/source purchase/destructive migration/release authority is created by this handoff.

## Readiness

- Research/design: **CHECKPOINTED_CONTINUATION** — material architecture and first real vertical are resolved; owner binding, native Paper and served journey remain.
- Forecast promotion: **NOT QUALIFIED**.
- Production acceptance: **NOT ACCEPTED / UNCHANGED**.
- EFFECT_UNKNOWN: none.
- Paper blocker: exact catalog/runtime admission only; mission continues on independent lanes.
