---
workstream: "WS:GMI-THEME-GRAPH"
session: "claude-code 6f14c2da-02a9-467e-9f37-7c2ebaccfe09 (GMI Meta-CEO seat, Fable 5.1 main loop with Opus 5.5 orchestrators over the GLM/MiniMax fabric, recovery steps 2 to 8, 2026-10-16 to 2026-10-19, Chairman commission: complete the GMI remainder end to end)"
model: fable
ended_because: complete
mission: >
  Finish research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md §9 steps 2 to 8: land the
  native economic-context repair, activity admission and PIT history, generation-specific
  ThemeState applicability readers, API parity, the cohort delivery contract, the measured
  coverage proof, the diagnostic strata and operating-proof tests, then accept the full
  descriptive product with exact evidence, reconcile the Neural Web state authority and
  route predictive candidates to their existing owners.
state_before: >
  origin/main at 9629927bfc7a held the 2026-10-16 recovery record with prospective §7
  thresholds and an unmerged #9423 at cedae32cf414. The graph had 3,975 nodes and 25,643
  edges; all 103 micro candidates and 46 addendum activities were unadmitted; the shadow
  generation bd084373e896 read 663 UNAVAILABLE / NOT_QUALIFIED. No coverage had been
  measured against an explicit universe.
changed:
  - path: engine/theme_graph/materialize.py
    what: "ACTIVITY_HISTORY_* event/state schemas and the pure PIT history fold (#9644); not called by any nightly job"
  - path: contracts/theme_graph/activity_membership_history.v1.schema.json
    what: "activity membership history contract (#9644)"
  - path: engine/theme_graph/theme_state_owner_readers.py
    what: "StateQualificationReader: generation-specific, read-only qualification reads (#9670)"
  - path: engine/theme_graph/theme_state.py
    what: "publication_applicability diagnostic (SUBJECT_NOT_QUALIFIED / D2E_UNSEALED reasons), no publication authority (#9670)"
  - path: scripts/gmi_coverage_proof.py
    what: "explicit-universe coverage measurement; refuses data/ and site/ output (#9745)"
  - path: research/theme_graph/coverage_20261019/
    what: "UNIVERSE_MANIFEST.json, coverage_report.json, COVERAGE_REPORT.md at source_commit 0221d6e1 (#9745)"
  - path: research/theme_graph/diagnostic_20261019/
    what: "STRATA_DESIGN.md, cases.jsonl, ADJUDICATION_LOG.md, SOURCES.md (lane 7d, PR 9754)"
  - path: tests/test_gmi_operating_proof.py
    what: "five operating properties, each PASS or xfail(strict) naming an owner (lane 7e, PR 9753)"
  - path: .github/ci/legacy-jobs.yml
    what: "run lines for the new GMI suites and the coverage-proof step (CI-authority change; one main baseline dispatched after landing)"
  - path: agentos/
    what: "DEC-GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19, two DSC records, WS waves RECOVERY-S2..S8, this handoff"
verified:
  - claim: "Steps 2 to 6 are ancestors of origin/main"
    command: "git merge-base --is-ancestor <squash> 04cc542a51d8 for 072822093ccd d47f5b14d246 b04a9d898b0d cea783c92a86 82e854321c8c e5d6f40157e2"
    result: "6/6 rc 0"
  - claim: "Lane B coverage proof is merged and landed"
    command: "git fetch origin main; git ls-tree -r --name-only origin/main | grep -E 'gmi_coverage_proof|coverage_20261019'"
    result: "squash 1e08b9237fac is origin/main tip at 14:3xZ 2026-10-19; 5 paths present (scripts/gmi_coverage_proof.py + research/theme_graph/coverage_20261019/{UNIVERSE_MANIFEST.json,coverage_report.json,COVERAGE_REPORT.md,...})"
  - claim: "Lane 7d diagnostic strata and lane 7e operating-proof tests are merged and landed"
    command: "git ls-tree -r --name-only origin/main | grep -E 'diagnostic_20261019|test_gmi_operating_proof'"
    result: "PR 9754 squash 0ad974a90978 (15:08Z) and PR 9753 squash f70d7cdf3f62 (15:2xZ) are both origin/main ancestors after explicit git fetch origin main; 5 paths present: research/theme_graph/diagnostic_20261019/{ADJUDICATION_LOG.md,SOURCES.md,STRATA_DESIGN.md,cases.jsonl} and tests/test_gmi_operating_proof.py; legacy-jobs.yml names the test on 2 lines (paths + run)"
  - claim: "Lane 7e operating properties: 25 PASS, 2 xfail(strict) each naming WS:GMI-THEME-GRAPH as owner"
    command: "python3 -m pytest tests/test_gmi_operating_proof.py -q -p no:cacheprovider (seat reproduction at PR 9753 head 480ee0e277ed)"
    result: "25 passed, 2 xfailed; xfails = test_curated_withhold_of_an_existing_belief (no WITHHOLD action in the v1 contract, v2 owed) and test_fold_is_wired_into_build_so_publication_marks_corrections_and_routing_is_measured (ACTIVITY_HISTORY fold not called by materialize.build); 48h freshness is computed from fixture clocks only, production freshness unmeasured"
  - claim: "Lane 7d casebook integrity"
    command: "python3.12 read of research/theme_graph/diagnostic_20261019/cases.jsonl at PR 9754 head 460fbec9de69"
    result: "27 cases, store_mutation false on all 27, 15 hard negatives, DX-01/DX-02 counterparties anonymous with issuer_id UNRESOLVED (ANONYMOUS_BY_DISCLOSURE) at magnitude shares 0.22/0.14; 26 of 27 human_disposition fields await a human; the lane is a 27-case strata casebook, not the 120-issuer design (WP02 NOT_READY), and CN/HK issuer cells are unfillable until Data OS resolves China issuers"
  - claim: "Neural Web registry is unchanged by steps 2 to 7 and its suites pass"
    command: "python3 -m pytest tests/test_synapse_registry.py tests/test_synapse_registry_contract.py tests/test_synapse_read_gate.py -q -p no:cacheprovider (sparse records worktree at 04cc542a51d8)"
    result: "52 passed, 42 warnings; config/synapse.yml theme-state producer scripts/build_thematic_state.py, known_extra_writers []"
  - claim: "Coverage verdicts are the measured values, not restated thresholds"
    command: "read research/theme_graph/coverage_20261019/coverage_report.json at ed4188cfb94a"
    result: "us 1939/1935/1927/1925, principal activity 0, cn 1019 listings 0 issuers, taxonomy 68/68 versioned owner_reviewed false"
  - claim: "One CI-authority main baseline was dispatched for the #9753 legacy-jobs.yml change over a clear field"
    command: "gh run list --workflow ci.yml --branch main --json databaseId,status --jq '[.[]|select(.status!=\"completed\")]' -> []; gh workflow run ci.yml --ref main"
    result: "run 39277589795 dispatched 15:23Z 2026-10-19 on main f70d7cdf3f62; concluded SUCCESS at 16:33Z (70 min, status-only watcher; the jobs endpoint returned 502 to the built-in watcher twice); never re-dispatched over it; main is proven under the #9753 CI authority"
  - claim: "Agent OS records validate"
    command: "python3 scripts/agentos.py validate"
    result: "exit 0: 1885 records (99 workstreams, 507 decisions, 543 discoveries, 736 handoffs), 0 errors, 169 pre-existing warnings (2026-10-19 15:2xZ, this records worktree)"
unverified:
  - claim: "The operating properties hold in production after the history fold is wired"
    what_would_verify: "first nightly that emits activity_membership_history rows; re-run tests/test_gmi_operating_proof.py with the xfail markers removed by their owners and re-run scripts/gmi_coverage_proof.py"
  - claim: "F04 consumes the C01-grain economic context without a code change"
    what_would_verify: "F04 exposure walk against the post-wiring graph with no duplicate exposure rows; coordinated with the MarketOntology owner under a new DEC"
  - claim: "Predefined EN/ZH product-usefulness tasks reach 90% on the served Terminal"
    what_would_verify: "release of the Terminal #868 hold by its holding authority, then the task panel against production"
unresolved:
  - "Principal-activity coverage is 0 on both markets; closes only through the ThemeState producer wiring the A2 fold, a named curator ratifying PROPOSED rows, and Data OS identity/China resolution (DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19)"
  - "68/68 micros lack an owner-reviewed disposition"
  - "C01 rights row owed to #7870 in config/theme_sources.yml (never edit it from this workstream)"
  - "Current shadow generation is D2E_UNSEALED; reader custody/auth, shadow-writer wiring and the t9 pin amendment owed to the D2E owner; shadow recovery run 38340204231 failed and was not re-dispatched"
  - "Terminal #868 integration safety hold and #8793 platform refusal: EFFECT_NONE retained, never retried"
  - "Fabric hosts (GLM pool quota, bailian lease refusals) intermittently unavailable during step 7; lanes completed on ubuntu1 GLM with repairs; the 7d repair commit 460fbec9 was authored by orchestrator A directly after every fabric lane refused pre-START (GLM disk floor, MiniMax refusing a new macro worktree, no Cursor/Grok host)"
  - "Kit defect, not edited from this workstream: remote_sub.sh --out captured a 1-byte .out for both step-7 lanes; read the lane's launch log and the PR, never the .out, until the kit owner repairs it"
next_actions:
  - "ThemeState producer owner: wire the ACTIVITY_HISTORY fold under its own narrow --mode in an off-render job (DSC:GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION) and emit the edges.v1 projection"
  - "Named GMI curator: ratify PROPOSED activity memberships row by row with evidence; taxonomy owner: record a disposition per micro"
  - "Data OS: China issuer resolution and listed counts; U.S. identity qualification for the 726 IDENTITY_NOT_QUALIFIED securities"
  - "D2E owner: seal the current shadow generation; #7870: C01 rights row"
  - "After the first nightly with history rows: re-run scripts/gmi_coverage_proof.py and update the DEC's measured column"
  - "Route L13 micro RS proxy, transmission and opportunity candidates to the existing evaluator, F04 and K3-D owners; no promotion from this acceptance"
do_not_redo:
  - "Steps 2 to 8 (#9423, #9645, #9644, #9670, #9652, #9641, #9745, 9754, 9753, 9757): accepted, do not re-spec or re-implement"
  - "Do not admit the 103 micro candidates or 46 addendum activities by code or by seat ratification"
  - "Do not flip the default build_thematic_state mode or call publish_generation from the engine step"
  - "Do not add a synapse.yml entry for the history fold until a job writes it"
  - "Do not bypass the Terminal #868 hold or retry #8793; do not recreate #796/#847/#959/#960"
  - "Do not edit COVERAGE_REPORT.md by hand; re-run the proof script"
danger_areas:
  - "Owned by #7870, never edit: engine/theme_graph/{rights,admission,curation_assertion}.py, config/theme_sources.yml, contracts/theme_graph/{README.md,curation_assertion.v1.schema.json,evidence.v1.schema.json}; engine/classification_axes/ and engine/theme_graph/identity_resolution.py read-only"
  - "Gate 2: finviz_themes, ths_concepts, china_ths.parquet, ltheme:* and basket:baskets_china_ths:* are internal-only and never a subject, input or output of activity coverage"
  - "Gate 7: never lower mini2 min_free_gb 50; gate 8: no new producer, selection store, ThemeState owner, rights resolver or publication control plane"
  - "Every new test file must be named by a run: step in .github/ci/legacy-jobs.yml, which is a CI-authority change: one main baseline after landing, never over an in-flight main run"
  - "DSC:GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML"
  - "DSC:DAILY-ENGINE-RESULT-IS-FAILURE-AFTER-ITS-COMMIT"
  - "Known inherited reds on main during this wave: reference-integrity RIG (Sol #9592), sni-program-guards seal tests; attribute by job log before calling a red yours"
prs: [9423, 9645, 9644, 9670, 9652, 9641, 9745, 9754, 9753, 9757]
decisions:
  - "DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19"
discoveries:
  - "DSC:GMI-NEURAL-WEB-THEME-STATE-REGISTRY-UNCHANGED-THROUGH-STEP-7"
  - "DSC:GMI-PRINCIPAL-ACTIVITY-COVERAGE-IS-ZERO-ON-2026-10-19"
---

## Cold-stranger summary

The GMI recovery plan of 2026-10-16 is executed through step 8. Source for native issuer
economic context, activity admission, point-in-time activity history, generation-specific
ThemeState readers, API parity and the cohort contract is merged. A measurement script now
reports coverage against an explicit universe, and the first reading is honest and poor:
every security has a status, but no issuer on either market has a qualified principal
activity, and none of the 68 micro themes has an owner-reviewed disposition.

That zero is structural, not a scraping gap. Activity candidates land as PROPOSED and only a
named curator may ratify them. The history fold that would carry ratified rows into the
nightly graph exists as a pure function that no job calls yet. China has no resolved issuers
until Data OS supplies them. Closing each remainder is an incumbent owner's act, listed in the
decision record with the exact evidence that would flip its row.

Nothing in this wave created a second ThemeState producer or store: the registry suites pass
unchanged and the legacy display organ stays the display organ. The Terminal integration hold
remains in force and was not touched. Predictive candidates were routed, not promoted. The
program's mission flag stays false on purpose.
