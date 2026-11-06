---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/ssd-prophet-ni-phase0-freeze-ed5ab44bd8bbc1c4"
model: fable
ended_because: complete
prs: [8777, 8873]
decisions: ["DEC:NEWS-IMPACT-PHASE0-FREEZE"]
mission: >
  Phase 0 of the Prophet news-to-business-impact masterplan: recover the program
  from the closed DRAFT PR #8533, census the owners it reuses, commission three
  independent template designs plus adversarial reviews on the fabric, adjudicate a
  judge panel in the seat, and freeze three closed event templates as one contract
  file with worked cases, counterexamples, a hermetic test and a CI job entry.
state_before: >
  Nothing of the program existed in origin/main except the masterplan landed by
  PR #8777 (squash 91e3a379a0f1). contracts/news_impact/ and engine/news_impact/ did
  not exist. PR #6514 (company-intelligence spine, DRAFT, Sol-held) was the only
  neighbouring lane and stayed untouched. The ubuntu2 lane clone
  /home/ubuntu2/lanes/repos/macro had an empty working tree at HEAD 57f3041e22, so
  every fabric lane read owner code through the object store, never a checkout.
changed:
  - path: contracts/news_impact/news_impact_event.v1.schema.json
    what: >
      NEW frozen contract: three templates (capital_allocation_event.v1,
      demand_guidance_contract_event.v1, strategic_product_partnership_event.v1)
      sharing one set of $defs; every node that declares properties is closed;
      evidence is the owner source_span.v1 payload or field_absence.v1; grafts
      G-OC1 (integer table index) and F3 (const basis on stated_amount) applied.
  - path: contracts/news_impact/cases/
    what: >
      NEW worked cases (ACCEPT), counterexamples (REJECT, including near-duplicates
      and the four owner-conflict probes), the 443-row adversarial battery and the
      154-row benign set used as the freeze gate.
  - path: tests/test_news_impact_contracts.py
    what: >
      NEW hermetic test: schema check, closedness walk, forbidden-name grep, field
      budget, worked/counter cases, attack battery admits zero, benign set rejects
      zero, live owner payloads built with text_span/address_only_span/TypedAbsence.
  - path: .github/ci/legacy-jobs.yml
    what: NEW job news-impact-contracts scoped to the contract, cases, test and the two owner modules.
  - path: research/prophet_v4/news_to_business_impact_20261006/PHASE0_FREEZE_2026-10-11.md
    what: Phase 0 freeze record; gates 1-6 with outcomes, judge panel, reuse matrix, not-verified list.
  - path: agentos/decisions/DEC-NEWS-IMPACT-PHASE0-FREEZE.md
    what: The freeze decision and the four owner-conflict rulings R1-R4.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: Wave p0 marked done; next_action moved to Phase 1 (sampler + projector).
verified:
  - claim: The contract test passes hermetically in the freeze worktree.
    command: python -m pytest tests/test_news_impact_contracts.py -q
    result: 46 passed in 16.29s
  - claim: The adversarial battery admits nothing and the benign set rejects nothing under the frozen contract.
    command: python3 R_D1r_harness.py (fabric review harness) run on the seat PYTHONPATH against the final contract bytes
    result: adversarial rows=443 admitted_by_base=356 still_admitted_by_copy=0; benign rows=154 false_rejects=0
  - claim: The legacy-jobs entry parses and lands in a pack.
    command: python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 0 --pack-count 12 --validate-only
    result: "Validated 277 legacy jobs; 277 in scope; pack weights=[1400, 875, 797, 797, 797, 797, 797, 797, 797, 797, 796, 797]; selected pack 0 (1 jobs; ci-control-plane-contracts)"
  - claim: Owner constructors produce payloads the contract accepts, including an integer table index and a projected URL-bearing excerpt.
    command: python -m pytest tests/test_news_impact_contracts.py -q -k owner
    result: 5 passed, 41 deselected in 2.72s
  - claim: Agent OS records validate.
    command: python3 scripts/agentos.py validate
    result: "1620 records (91 workstreams, 430 decisions, 480 discoveries, 619 handoffs), 0 errors, 151 warnings; rc=0"
unverified:
  - claim: The four C3 census citations marked DRIFT (line numbers moved between 57f3041e22 and HEAD) still point at the same statements.
    what_would_verify: re-run the V_C3 verifier script against the freeze worktree HEAD
  - claim: RS11 (low <= high on bounded quantities) holds for every producer.
    what_would_verify: the Phase 1 projector test suite; it is a runtime check, not a schema constraint
unresolved:
  - Phase 1 projector engine/news_impact/validate.py (R1/R2 null-excerpt projection, R4 locator_key_not_in_contract) is commissioned, not built.
  - The benchmark sampler and the 600-case graded benchmark (masterplan section 11) are Phase 1/2 work.
  - PR #6514 ownership: the company-intelligence spine stays Sol-held; this program consumes its constructors and never edits it.
next_actions:
  - Phase 1 (wave w1): engine/news_impact/validate.py projector with hostile fixtures, implementing R1/R2 excerpt projection and R4 locator rejection, plus the benchmark candidate sampler, as seat-launched Grok (grok-4.6) and GLM (glm-5.3 build / glm-5.3-flash mechanical) fabric lanes via remote_sub.sh on ubuntu0/ubuntu2/ubuntu3/mb; no native Claude children (Chairman directive 2026-10-12); the seat judges by artifact, integrates and ships.
  - Keep contracts/news_impact/news_impact_event.v1.schema.json byte-frozen; any change is a versioned v2 with its own DEC.
  - Re-run the C3 verifier against HEAD before Phase 1 cites any owner line number.
do_not_redo:
  - The Phase 0 census, the three-candidate judge panel and the four owner-conflict rulings (DEC:NEWS-IMPACT-PHASE0-FREEZE); a fresh session is not an invalidator.
  - Minting a second span, absence, period or evidence object beside the owner's source_span.v1 / field_absence.v1 / FiscalPeriod.
  - Widening a locator key set or stripping unknown keys in a projector.
  - Touching PR #6514 (repair, rebase, arm, comment).
danger_areas:
  - The ubuntu2 lane clone has an empty working tree; a packet that says "read file X" without the object-store fallback reports the file missing.
  - The contract test imports owner constructors from engine/company_intelligence; a signature change there is a contract break, which is why the CI job scopes both owner modules.
  - Research prose and PR bodies must not carry a DNR hold key or the sweeper's merge-barrier phrase.
  - display_excerpt is nullable by owner design; a consumer that assumes a string will crash on a projected span.
---

# Phase 0 handoff — Prophet news-to-business-impact

Program state at resumption grain:
research/PROPHET_NEWS_IMPACT_CONTINUATION_HANDOFF_2026-10-11.md. Freeze record:
research/prophet_v4/news_to_business_impact_20261006/PHASE0_FREEZE_2026-10-11.md.
Lane records: handoff kit orch/fabric/reviews/PROPHET_NI_W1_r1.md, PROPHET_NI_W1c_r1.md,
PROPHET_NI_W1d_r1.md. Seat scratch artifacts are not durable; everything a
successor needs is in the files above and in the Phase 0 pull request #8873.
