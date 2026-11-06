---
key: GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19
question: >
  After recovery steps 2 through 7 landed (native issuer economic context, activity
  membership admission and history, generation-specific ThemeState applicability, the
  cohort delivery contract, API parity, the measured coverage proof, the diagnostic strata
  and the operating-proof tests), which of the 2026-10-16 descriptive-product acceptance
  thresholds are closed with exact source, runtime and consumer evidence, which remain
  open, who owns each remainder, and where do the predictive candidates go?
answer: >
  Accept the full descriptive product as a MEASURED, OPEN record, not as a pass. Exactly
  one §7 threshold is closed by evidence: denominator honesty (100% of the explicit
  universe carries a status, closed-enum remainders, no OTHER). Principal activity is
  measured FAIL at 0 of [1926, 1931] eligible U.S. issuers and 0 of [1, 1019] China
  listings; taxonomy is FAIL on owner_reviewed (68 of 68 micros scope-versioned, none
  owner-reviewed); correctness, freshness, corrections and failed-fetch removal are proven
  as operating properties of the history fold and owner readers only where the tests in
  the step-7 operating-proof lane PASS, and are owed where they are strict xfail naming an
  owner; automatic admission is NOT ESTABLISHED (no admission is automatic; the one-sided
  95% lower bound at 95% precision has no measured sample); product usefulness and the
  actual Terminal explanation remain OPEN behind the Terminal #868 integration safety
  hold; predictive claims receive no promotion and are routed to their existing owners.
  MISSION_COMPLETE stays false. Each open threshold is bound to one named owner act
  below; no new producer, store, owner or control plane is created to close it.
rationale: >
  The 2026-10-16 recovery record set numeric thresholds as prospective criteria. Steps 2
  through 7 produced the first measurements against them. Reporting the measured zeros
  honestly, with the closed-enum reasons that explain them (IDENTITY_NOT_QUALIFIED 726,
  NOT_IN_GRAPH 721, VENDOR_MEMBERSHIP_ONLY 1201 in the U.S. core; no resolved China
  issuers; 167 Canadian securities NOT_IN_MASTER), is the deliverable. The zeros are not
  a defect of the lane: activity admission lands PROPOSED and stays PROPOSED until a named
  curation act, the history fold is a pure function not yet wired into the nightly build,
  and the current shadow generation is D2E_UNSEALED. Each of those is an incumbent-owner
  act, and the program gates forbid closing them by laundering vendor membership
  (finviz_themes, ths_concepts, ltheme:*) into activity, by minting a new ThemeState
  owner or rights resolver, or by retrying the refused Terminal #868 and #8793 effects.
alternatives:
  - option: Declare the descriptive product accepted because every planned PR merged
    why_not: >
      Merged source is not coverage. The measured principal-activity coverage is zero on
      both markets and the taxonomy has no owner review, so an acceptance would be false.
  - option: Close principal activity by admitting the 103 micro candidates and 46 addendum activities
    why_not: >
      Admission is a named curation act under DEC:GMI-INVESTABLE-ECONOMY-RECOVERY-ACCEPTANCE
      and gate 5; the seat may not ratify candidates, and automatic admission has no
      measured precision sample.
  - option: Wire the history fold and flip the GRAPH_SHADOW_STATE mode inside this records wave
    why_not: >
      That is source work with a production effect (oracle_offrender job, generation
      family lock) owned by the ThemeState producer path and the D2E owner; a records PR
      must not carry it, and the engine step stays LEGACY byte for byte
      (DSC:GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION).
  - option: Bypass the Terminal #868 hold to obtain the actual-explanation proof
    why_not: >
      The hold is an explicit Sol/Chairman integration safety decision. EFFECT_NONE,
      retained; no retry through another tool, account, worker, branch or direct merge.
  - option: Promote predictive candidates (RS proxies, transmission, opportunity) alongside the descriptive acceptance
    why_not: >
      §7 forbids promotion from descriptive acceptance. Those candidates belong to the
      existing evaluator, F04 MarketOntology and K3-D owners and are routed, not promoted.
evidence:
  - "Measured gates: research/theme_graph/coverage_20261019/COVERAGE_REPORT.md and coverage_report.json (report_version 0cd3e337…, manifest 2373df79…, source_commit 0221d6e1), PR #9745 head ed4188cfb94aaf18fbd3e5fb538caf73a93e71f1."
  - "U.S. core denominators: 1939 securities, 1935 eligible securities, 1927 issuers resolved, 1925 eligible issuers, 6 unresolved; 4 explicit exclusions (ETHA, IBIT ETFs; SPY entity conflict; VMRK duplicate). China: 1019 listings, 0 issuers resolved, CN_LISTED_COUNTS_NOT_AVAILABLE."
  - "Step 2 #9423 squash 072822093ccd; step 3 #9645 d47f5b14d246 and #9644 b04a9d898b0d; step 4 #9670 cea783c92a86; step 5 #9652 82e854321c8c; step 6 #9641 e5d6f40157e2; all ancestors of origin/main 04cc542a51d8 (2026-10-19)."
  - "Landed source on origin/main: contracts/theme_graph/activity_membership_history.v1.schema.json; engine/theme_graph/materialize.py ACTIVITY_HISTORY_* fold; engine/theme_graph/theme_state_owner_readers.py StateQualificationReader; engine/theme_graph/theme_state.py publication_applicability (diagnostic-only)."
  - "CI carriers: .github/ci/legacy-jobs.yml run lines for tests/test_gmi_history_integrity.py, tests/test_gmi_activity_membership_admission.py, tests/test_theme_graph_activity_membership_history.py, tests/test_theme_state_owner_adapter.py, tests/test_theme_state_generation_applicability.py and tests/test_gmi_operating_proof.py (#9753, CI-authority; main baseline run 39277589795 SUCCESS 16:33Z)."
  - "Neural Web reconciliation: python3 -m pytest tests/test_synapse_registry.py tests/test_synapse_registry_contract.py tests/test_synapse_read_gate.py -q on 04cc542a51d8: 52 passed; config/synapse.yml theme-state still names scripts/build_thematic_state.py as sole producer with known_extra_writers [] (DSC:GMI-NEURAL-WEB-THEME-STATE-REGISTRY-UNCHANGED-THROUGH-STEP-7)."
  - "Step 7 lanes: Lane B coverage proof PR #9745; lane 7d diagnostic strata PR 9754; lane 7e operating proof PR 9753 (per-property PASS/xfail list in the 2026-10-19 handoff)."
  - "Orchestrator A GAPS, retained verbatim as owed: C01 rights row owed to #7870 config/theme_sources.yml; history fold not wired into the build and the edges.v1 projection owed; reader custody/auth and shadow-writer wiring with the t9 pin amendment owed; current generation D2E_UNSEALED; shadow recovery run 38340204231 failed; fabric hosts intermittently broken."
affects:
  - "WS:GMI-THEME-GRAPH"
  - "research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md"
  - "research/theme_graph/coverage_20261019/"
  - "research/theme_graph/diagnostic_20261019/"
  - "engine/theme_graph/"
  - "MarketOntology F04, Data OS security master, Terminal #868 integration, K3-D owner interfaces"
confidence: high
reversibility: easy
decided_by: "Fable Meta-CEO seat 6f14c2da-02a9-467e-9f37-7c2ebaccfe09 (Chairman commission 2026-10-19, GMI remainder end to end)"
decided_at: 2026-10-19
---

## Relationship to prior decisions

This decision supplements DEC:GMI-INVESTABLE-ECONOMY-RECOVERY-ACCEPTANCE and
DEC:GMI-THEME-GRAPH-END-TO-END-COMPLETION-OWNERSHIP-SEQUENCING. It does not supersede either:
the three acceptance boundaries (original D2/W3, expanded descriptive coverage, predictive
promotion) stand, and this record is the first measured reading of the second boundary.
Original accepted D2E selected-generation P2/P3, immutable C01 generation 040b, Taxonomy V2
and the merged steps 2 through 7 are DO_NOT_REDO.

## Per-threshold verdicts and owner acts

| §7 threshold | Measured verdict | Evidence | Owner act that closes it |
|---|---|---|---|
| Denominator honesty (100% explicit status) | PASS | coverage_report.json: every security in UNIVERSE_MANIFEST carries exactly one closed-enum status; 0 OTHER | none; keep the proof lane in CI |
| Principal activity ≥95% eligible core U.S. issuers | FAIL 0 / [1926, 1931] | us remainders IDENTITY_NOT_QUALIFIED 726, NOT_IN_GRAPH 721, VENDOR_MEMBERSHIP_ONLY 1201, NO_ACTIVITY_EVIDENCE 4, NO_ISSUER_EVIDENCE 3, ISSUER_EVIDENCE_CONFLICT 2, DEFERRED 1 | ThemeState producer owner wires the A2 history fold into the nightly build and emits the edges.v1 projection; the named GMI curator ratifies PROPOSED activity memberships one evidenced row at a time (gate 5); Data OS qualifies identities |
| Principal activity ≥95% eligible core China issuers | FAIL 0 / [1, 1019] | cn NO_ISSUER_EVIDENCE 1019, IDENTITY_NOT_QUALIFIED 1019, CN_LISTED_COUNTS_NOT_AVAILABLE | Data OS security master supplies China issuer resolution and listed counts; no GMI-side China master (gate 8) |
| Taxonomy: 68 micros versioned scope + owner-reviewed disposition | FAIL (68/68 versioned, owner_reviewed false) | coverage_report.json taxonomy block; all 68 RESEARCH_UNADMITTED | the named GMI taxonomy owner records a disposition per micro in config/theme_crosswalk.yml provenance; a seat may not self-review |
| Correctness (zero hard merges, fabricated anonymous customers, unauthorized promotion, future leakage, failed-fetch removals, species conflations) | PROVEN where lane 7e tests PASS; OWED where xfail(strict) | tests/test_gmi_operating_proof.py per-property list in the 2026-10-19 handoff; 7d cases.jsonl keeps NVIDIA's 22% and 14% customers ANONYMOUS and splits BABA/9988/89988 as one issuer | the owner named in each xfail reason (history-fold wiring, edges.v1 projection) |
| Automatic admission: none until one-sided 95% LCB ≥95% precision | NOT ESTABLISHED (no automatic admission exists; sample 0 of the 59 independent all-correct cases needed) | admission lands PROPOSED (#9645); no ratifier in code | stays manual until a reviewed sample reaches the bound; the bound is computed from independent episodes, never fires |
| Freshness ≥95% within 48h with visible stale status | PROVEN as a reader property only (status surfaced, threshold reported not asserted) where 7e PASSES; production freshness UNMEASURED | 7e property 5; no nightly history rows exist yet | measured on the first nightly after the history fold is wired |
| Corrections withheld/corrected by next publication, original reproducible, latency measured | PROVEN as a fold property where 7e PASSES; production UNMEASURED | 7e property 2 | same owner act as freshness |
| Product usefulness ≥90% on predefined EN/ZH tasks; actual Terminal explanation | OPEN | Terminal #868 integration safety hold (Sol/Chairman), EFFECT_NONE retained; API parity on the C01 grain pinned by #9652; private API delivery by #9423 | release of the #868 hold by its holding authority, then the predefined EN/ZH task panel against the served Terminal |
| Predictive claims: no promotion from descriptive acceptance | HELD | no rank, size, gate or trade key emitted by any step-2..7 reader | candidates (micro RS proxy L13, transmission, opportunity composition) routed to the existing evaluator, F04 MarketOntology and K3-D owners |

## What this decision does not do

It grants no source rights, ratifies no candidate, publishes no generation, releases no hold,
wires no producer, and confers no predictive or trading authority. It names the Terminal #868
hold once as the exact external gate for the actual-explanation proof and does not ask for it
again. Reconsider when the history fold is wired and a nightly emits history rows, when Data OS
supplies China issuer resolution, when the taxonomy owner records dispositions, or when the
#868 hold is released.
