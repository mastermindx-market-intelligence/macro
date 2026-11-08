---
key: GMI-RELATIONSHIP-ENVELOPE-CONTRACT
question: >
  How does the GMI program accept descriptive, source-backed economic relationships
  (acceptance boundary 2 of the 2026-10-21 Fable execution handoff) without a new graph,
  identity master, scorer or control plane — what is the measuring instrument, what did
  it measure on the first integrated package, and what do the master plan's 0.80
  precision/recall targets bind?
answer: >
  The §8.2 relationship ENVELOPE (E1 issuer relation coverage, E2 role/species cells,
  E3 source processing, E4 extraction recall, E5 positive precision, E6 natural
  operations latency, E7 investor answerability, E8 correction demo) is the acceptance
  instrument for boundary 2. It is measurement only: scripts/relationship_m2_envelope.py
  reads the committed package, edges, judging ledger and recall report and PRINTS every
  measure with its state (MEASURED / OWED / NOT_MEASURABLE / ABSENT); it never recomputes
  a judgment and never promotes anything. Two domains are adopted (D1, D2 of the pinned
  coverage_20261019 universe) on the incumbent company-intelligence producer
  (scripts/build_relationship_observations.py -> observation_package.v2 + edges.v1). The
  first positive end-to-end witness is M1 SWKS->AAPL (three pinned filings, committed
  extraction, tests/test_relationship_m1_swks_aapl.py). On integ head 8a1fee67 the
  package holds 1589 observations (482 edge / 1107 non_edge; 8 refused provider_unnamed),
  248 edges, 1107 non-edges, 283 coverage rows; E4 recall 83/238 = 0.349 [0.291, 0.411]
  (D1 0.442, D2 0.171); E5 precision 49/100, weighted 0.498 [0.390, 0.607], 25 decoys 0
  accepted, read by a glm-5.3 blind re-reader, NOT an owner. The master plan's 0.80
  targets are NOT met and are NOT ratified by this record. Ruling: those targets bind
  PROMOTION — any use of an edge as an asserted fact without its "filings we read"
  framing, as a rank/size/gate input, or outside display tier — not display-tier
  descriptive publication, which ships with the envelope printed (house epistemics:
  display-tier ships freely, nulls printed; the gauntlet is a promotion gate). The
  package stays adoption_state=proposed; purpose.source_purpose_permission stays
  NOT_ESTABLISHED; redistribution is not_granted (dataset registry rows
  company_intelligence.relationship_observation_package / .relationship_edges).
rationale: >
  The handoff's boundary 2 asked for descriptive economic intelligence with a
  relationship-envelope contract, zero hard errors, and separate verdicts — not for a
  precision level the first pass could not honestly reach. Measuring and printing the
  envelope on the real package answers the acceptance question truthfully (0.349 / 0.498)
  where an unmeasured claim or a hidden sample would not; ratifying 0.80 as met would be a
  "validated" claim the CI guard forbids. Binding 0.80 to promotion keeps the product
  useful now (S3 relationships surface, investor answerability E7 with ANSWERED_NONE_FOUND
  printed) while refusing authority to a 50%-precision edge. The cap-fix ruling of
  2026-10-22 (per-filing cap keyed by accession; judged rows STAND; only the delta
  re-judged; one integration PR supersedes the five leaf PRs) is folded here. The
  direction fix (judge._observation_row never wrote subject_role; 706 rows gained the key;
  to-side rows were inverted in 603c3551) is why 603c3551 is never shipped and why the
  precision population was re-derived (1597 -> 1589 admitted by package).
alternatives:
  - option: Ratify the 0.80 targets as met or waive them for boundary 2
    why_not: >
      Rejected. Measured 0.349 / 0.498; a waiver would relabel a first pass as accepted
      and the precision reader is a model, not the owner reviewer the handoff names.
  - option: Hold the whole relationship package unpublished until 0.80 is reached
    why_not: >
      Rejected. Display-tier context never waits on the promotion gauntlet; the S3 surface
      prints the envelope and the "filings we read" framing, and E7 shows the honest
      ANSWERED_NONE_FOUND answers are themselves useful.
  - option: Build a separate relationship graph / scorer / ThemeState feed for edges
    why_not: >
      Rejected by Gate #8 and the handoff (no new universal graph, identity master,
      propagation scorer or evaluation authority). Edges stay a fold of the package on the
      incumbent producer.
  - option: Re-judge every row after the per-filing cap defect instead of only the delta
    why_not: >
      Rejected 2026-10-22 (seat cap-fix ruling): judged rows stand; 600 earlier judgment
      ids byte-unchanged in r2; only the 3205 delta rows were harvested and judged.
evidence:
  - "Integ head claude/gmi-rel-m2-integ-20261022 = 8a1fee67bbc3eac74cd22d1b485b174b301044b9 (merge-base d18dbe33); seat merged it into claude/ssd-gmi-rel-integ-seat-f3e02a9dd8326680 with no conflicts; 11 suites 210 passed (python3 -m pytest tests/test_relationship_*.py, 2026-11-01)."
  - "research/theme_graph/gmi_relationships_20261021/m2_integration/envelope_print.txt: M0 join 1597/1597/1597; E1 D1 146 (114/31/1), D2 137 (72/64/1); E2 2830 cells; E4 value=0.3487 wilson_95=[0.291,0.4113] jackknife_95=[0.2429,0.4545]; E5 state=OWED without --precision-dir; E6 p50 5707h clock_violations=0; package_lag NOT_MEASURABLE; D2 parse_outcomes ABSENT."
  - "E5 from the ORCH-REL-2 return (seat transcript, 2026-10-23): 49/100 [0.394,0.587], weighted 0.498 [0.390,0.607], decoys 0/25, reader glm-5.3; precision_report.json was NOT committed and its scratch copy was lost on 2026-11-01 — the salt, manifest and sample_key are never committed by rule."
  - "m2_integration/precision_population.md: admitted iff source_state=verified and disposition in (edge, non_edge); Counter verified/non_edge 1107, verified/edge 482, verified/refused 8 (provider_unnamed)."
  - "m2_integration/direction_fix.md: 31 direction errors in a 100-item blind sample, all filer-on-to-side rows; fixed in judge._observation_row (be599c5e), re-pinned 770909e8 -> 5b442662; 603c3551 superseded."
  - "m2_recall/recall_report_v1.json sha256 915de3481ec77f4702d0dad0d842862809491b6f024a409598b6ba690a2237a8; tests/test_relationship_m2_envelope.py::test_committed_recall_report_equals_fresh_compare regenerates and requires byte equality."
  - "Cap fix b316e4e1 (tests 7 failed -> 8 passed); delta rows P 86 / D1a 1085 / D1b 1027 / D2a 521 / D2b 486 = 3205; judging r2 52578762 byte-inclusion proof, 600 earlier ids unchanged, replay 1138 sources 0 failures, 480 accepted rows spot-checked 0 mismatches."
  - "A25: .github/ci/legacy-jobs.yml job company-intelligence-relationships (scope exclusive, 69 paths = union of the lanes' ci_registration_proposal*.yml closures plus the m2 extraction suites, 11 test files over 12 pytest steps; corrected 2026-11-02 from '63 paths, 11 suites' after O5 re-counted the committed job). A26: config/dataset_registry.yml rows for the package and edges (tests/test_dataos_registry.py 60 passed)."
affects:
  - "WS:GMI-THEME-GRAPH"
  - "engine/company_intelligence/relationships/**"
  - "scripts/build_relationship_observations.py"
  - "scripts/relationship_m2_*.py"
  - "scripts/relationship_m3_describe.py"
  - "data/company_intelligence/relationships/**"
  - "research/theme_graph/gmi_relationships_20261021/**"
  - "contracts/company_intelligence/relationship_*.schema.json"
  - "scripts/gmi_explorer/model.py (S3 relationships surface, PR #10099)"
confidence: medium
reversibility: easy
decided_by: "GMI Meta-CEO seat 6f14c2da (Fable) as current receiver under the Chairman leadership-continuity ruling 2026-10-24; ORCH-REL-2 (Opus a986c453) delivered the measurements"
decided_at: 2026-11-01
review_by: 2026-12-01
---

## What is owed before any edge leaves display tier

| # | Obligation | Owner (role) |
|---|---|---|
| O1 | Human owner review of the 100-item precision sample (the model re-reader is evidence of process, not of precision) | Company-intelligence owner reviewer — a fresh, non-authoring reviewer; never this seat |
| O2 | Ratify-or-replace the 0.80 precision/recall targets as PROMOTION gates, with the replacement measured on this envelope | Chairman / Sol, asked once with this record as the brief |
| O3 | Re-measure E4/E5 on every package re-fold; a package whose E5 is OWED prints OWED on S3, never a number | Producer lane via tests/test_relationship_m2_envelope.py |
| O4 | D2 `parse_outcomes` (ABSENT) and `package_lag` (NOT_MEASURABLE by construction) stay printed as nulls, never filled | Envelope |
| O5 | Battery case 10 (relationship rendering) belongs to the GMI Explorer S3 surface (#10099) | UI integration |

Superseded leaf PRs (heads contained in 8a1fee67): #10083, #10082, #10040, #10045, #10051, #10059, #10041, #10015, #10018, #10005, #10030, #10031. Never ship 603c3551.
