---
workstream: "WS:GMI-THEME-GRAPH"
session: claude/ssd-gmi-robotics-reland-hold-17c9f82c
model: opus
ended_because: blocked
mission: >
  Principal (Fable Meta-CEO seat) record for operation
  gmi-robotics-fable-ceo-e2e-20260923-chairman-001: deliver the first production-proven
  granular Robotics theme-intelligence vertical (Precision Motion + Perception) inside the
  existing Theme Tracker / basket/robotics_automation.html workflow by CONSUMING the shared
  GMI foundation on #7870, building only the Robotics-specific composition, evidence
  qualification, facets, non-regression and real-path acceptance. Canonical packet: #7773 at
  325be052aa5892f21a399ec0eebc1bd5c65b995a, file
  agentos/handoffs/GMI-ROBOTICS-MASTER-FABLE-CEO-HANDOFF-2026-09-23.md.
state_before: >
  This operation had NO durable record on main. Its working checkpoint,
  agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-robotics-implementation.md, was one of the 35
  paths the revert #8013 removed, so the knowledge record was collateral damage of a revert
  aimed at code. A successor reading main found nothing: not the revert's cause, not the
  no-split-re-land ruling, not the merge-order dependency on #7870. Everything below lived
  only in account-local session memory, which is explicitly not company memory. Implementation
  carrier #7908 merged 2026-09-25T07:27:34Z (70b3c9f1f8f0) and was reverted the same day by
  #8013 (e5512ef66a74). #7870, the shared foundation the re-land waits on, is still an open
  draft.
changed:
  - path: "agentos/handoffs/GMI-THEME-GRAPH-2026-09-27-robotics-reland-hold.md"
    what: "One of THREE paths on this carrier; the two DEC records below are the others, and an earlier version of this field listed only this file while next_actions already said the DECs were done in the same change. Restores the operation's durable org memory after the revert removed its predecessor, updated to post-revert truth rather than re-adding a superseded document: the twelve architecture rulings, the corrected gate taxonomy (Gate C is a compound predicate - neither a bare exit code nor the script's own marker line), the re-land runbook with its two amendments, the cross-sector triage rule, the held lanes, and the reason MISSION_COMPLETE is not claimable. Documentation only - zero code paths, no partial re-land."
verified:
  - claim: "The operation's prior handoff is absent from main, and the revert #8013 is what removed it."
    command: "gh api repos/{o}/{r}/contents/agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-robotics-implementation.md?ref=main >/dev/null 2>&1 (exit-code test, with agentos/README.md as positive control and a nonsense path as negative control); gh api repos/{o}/{r}/pulls/8013/files --paginate --jq 'select(.filename|test(\"agentos\"))'"
    result: "Subject ABSENT (non-zero exit); positive control PRESENT 11115B; negative control correctly absent. #8013's own file list carries `removed agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-robotics-implementation.md`. Zero robotics handoffs among the 524 on main."
  - claim: "All 35 paths the revert removed are retrievable at the pre-revert commit and none has been re-added to main."
    command: "gh api repos/{o}/{r}/pulls/8013/files --paginate --jq '.[] | select(.status==\"removed\") | .filename' then, for each, gh api contents/<path>?ref=36efe9c92b96 and contents/<path>?ref=main by EXIT CODE"
    result: "35 removed paths; retrievable_at_36efe9c92b96=35, not_retrievable=0, present_on_main=0. Instrument positively controlled at the same ref. Read-only retrieval, so the no-split-re-land ruling is untouched."
  - claim: "The revert's sole parent is the pre-revert tree, so one commit id recovers the whole carrier."
    command: "gh pr view 7908 --json state,mergedAt,mergeCommit; gh api repos/{o}/{r}/commits/e5512ef66a74 --jq .parents"
    result: "#7908 MERGED 2026-09-25T07:27:34Z, mergeCommit 70b3c9f1f8f0. Revert e5512ef66a74 has exactly one parent, 36efe9c92b96, subject 'Revert \"Merge #7908: Robotics Theme Intelligence implementation carrier\" (#8013)'."
  - claim: "#7870 is caught up and textually mergeable; DRAFT status is the only remaining blocker, and it is the shell owner's call."
    command: "gh pr view 7870 --json state,isDraft,mergeable,mergeStateStatus,headRefOid,updatedAt"
    result: "state=OPEN draft=true mergeable=MERGEABLE mergeStateStatus=UNSTABLE head=a0d7b054ff23 (behind_by 0 when last compared). UNKNOWN mergeability means recomputing and is never a verdict - re-poll. An earlier record of this carrier as '323 behind' and CONFLICTING is superseded."
  - claim: "No single signal from the contracts script is a sound Gate C. A bare exit code is hollow without --strict, AND the script's own marker line is unreachable on a materialised store, so gating on either one is unsound in opposite directions."
    command: "gh api contents/scripts/check_theme_graph_contracts.py?ref=a0d7b054ff23 | base64 -d, then an ast.parse walk building a parent chain per notices.append/breaches.append call site, plus sed -n on the selftest; gh api contents/data/theme_graph/identity_resolution.parquet --jq .size at a0d7b054ff23 and main with a nonexistent sibling as negative control; gh api contents/docs/HOUSE_LAW_CI_GUARD_SUITE.md?ref=main | grep -n check_theme_graph_contracts"
    result: "87600B at this head. Line 1099 prints 'theme graph contracts OK ...' only when `not breaches` (1097) AND `not notices` (1098); 1101 returns 0; 1102 prints '::warning title=theme graph contract breach::'; 1109 returns `1 if strict else 0`; 1582 documents 'default is advisory rc 0'. The advisory default is DESIGNED: the house-law row gives the reason (display-tier, must not take the collect lane down) and states '--strict is what CI runs', and the same comment sits at the nightly call site scripts/ci/daily_engine_regional_desk_builders.sh:118-120 whose brun line passes NO --strict. But that row's LANE MAP IS STALE, verified against the workflows rather than the doc: the --strict invocation exists at .github/ci/legacy-jobs.yml:11456, in job unrun-intl-libraries which is `if: false` (11341) and `gate: data` (11342), executed only via scripts/run_ci_pack.py whose selector is `job.gate == gate` (:1690); across all 99 workflow files `--gate data` appears ONLY in data-health.yml, triggered by schedule / workflow_run on daily / dispatch and NEVER pull_request. So NO pull-request lane runs this guard and a carrier PR gets no theme-graph contract verdict from CI at all - which makes the local compound predicate the only Gate C a PR will ever have, not a supplement to one. The marker line is NOT the fix: the `[identity resolution census]` notice at 1044 is guarded only by `if idres is not None` (856) under `if idres_path.exists()` (850), with no content condition, and data/theme_graph/identity_resolution.parquet is committed (203378B at a0d7b054ff23, 204044B at main; negative control absent). So on any materialised store notices is non-empty, 1098 is False and the marker never prints, clean or not. The script's own selftest says so at 1229-1232 ('a designed, always-on notice ... printed every run, never an incident') and asserts it at 1334. Notices mix designed output with real incidents and must be triaged by printed class title. TESTIMONY, not observation, and labelled as such after review flagged that I had promoted it: the shared script's owner reported on #7780 that a run on materialised data found 1168 identity_resolution rows violating the `state<->ids` biconditional - a breach (a0d7 960 / main 924) - exiting 0 anyway. I did not witness that run and did not read its output back. It is the only EMPIRICAL support for the hollow-exit-code claim; the rest is read from the source. Do not attribute it to #7870's owner (\"the shell owner\"), who is a different lane. Controls: 21 'def ' hits, 0 nonsense-token hits; the blobs at 1e38d5c955dc and a0d7b054ff23 are byte-identical, so reading both is ONE observation."
  - claim: "Gate C cannot gate the re-land, established by measurement rather than by assertion: 0 of the revert's 35 paths lie under either of the guard's read roots, and the guard performs no directory enumeration at all, so on a purely additive carrier its verdict is identical with and without the change."
    command: "gh api repos/{o}/{r}/pulls/8013/files --paginate --jq '.[].filename' | awk -F/ '{print $1\"/\"$2}' | sort | uniq -c  (top-two-segment census of all 35); then grep -cE 'glob|rglob|os\\.walk|iterdir|listdir' on scripts/check_theme_graph_contracts.py at ref main; then --jq '[.[].additions]|add' on the same files endpoint"
    result: "35 paths, and the only contracts/ path is contracts/market_ontology/robotics_theme_research.v1.schema.json (525 deletions) - NOT under contracts/theme_graph/. Paths under contracts/theme_graph/: 0. Under data/theme_graph/: 0. Under .github/: 0. Under scripts/: 0. Directory-enumeration calls in the guard: 0. Sum of additions across all 35: 0. An earlier draft said the re-land 'writes neither' read root, which asserted the conclusion while a contracts/ path sat in the manifest; the measurement is what settles it, and the zero-enumeration plus zero-additions pair is what makes it hold in principle rather than by luck - every restored path is a NEW file a non-enumerating guard cannot reach."
  - claim: "'--strict is what CI runs' is the stale config row's testimony about itself, not a fact about CI. No lane runs this guard with teeth in any mode, so the hollow exit code was CI's too, not only this seat's local run."
    command: "sed -n '2824,2860p' on config/house_law_checks.yml at ref main (the theme_graph.edge_contract row, its check_script, ci_wiring and known_limits); then resolve each declared lane: grep -n 'unrun-intl-libraries' .github/ci/legacy-jobs.yml; sed -n on .github/workflows/daily.yml around job engine; then grep -n check_theme_graph_contracts on scripts/ci/daily_engine_regional_desk_builders.sh"
    result: "known_limits at 2853-2857 asserts '--strict is' what CI runs (:2857). ci_wiring at 2843-2849 declares two lanes. The pr_ci one (:2844-2846, legacy-jobs.yml job unrun-intl-libraries) is STALE. The scheduled one (:2847-2849) resolves only INDIRECTLY: daily.yml job engine (header :1895) runs bash scripts/ci/daily_engine_regional_desk_builders.sh (:3244), and that script invokes the guard at :118-120 with NO --strict. check_theme_graph_contracts appears nowhere in daily.yml itself. The only --strict invocation in the repo sits in a job carrying if: false. So the one live invocation is advisory and the retraction in the PR body is correct."
  - claim: "#7870's head carries a lazy-import refactor of the shared assertion module, and the Robotics-side fix that depends on it is unaffected."
    command: "gh api contents/engine/theme_graph/curation_assertion.py?ref=<head> --jq .size at 1e38d5c955dc and a0d7b054ff23; direct file diff of the three dependency files across heads"
    result: "27838B -> 28610B. Module-level `import jsonschema` plus an eager Draft202012Validator became a `_validator()` accessor with a deferred import, because the module sits in the shared app.main import closure and a hard import made an unprovisioned app import raise ModuleNotFoundError instead of degrading. Robotics symbols survive at shifted lines (_revision_of, validate_assertion, curation_revision_mismatch, source_ref_for); the dependent Robotics commit imports symbols, not line numbers, so it is unaffected. A `gh api compare/A...B` over this range is void for absence claims - it returned ahead_by 608 with commits capped at 250 AND files_listed capped at 300."
  - claim: "Robotics is neither DECLARED nor ENROLLED in the shared registry at #7870's head; only the semiconductor vertical is."
    command: "gh api contents/engine/market_ontology/theme_research_mounts.py?ref=a0d7b054ff23 | base64 -d | grep -n 'anchor_theme_id=\"'; same for theme_research_registry.py | grep -n '_MOUNTS\\['"
    result: "DECLARED: mounts.py:135 anchor_theme_id=\"ai_semiconductors\" - the only literal. ENROLLED: registry.py:169 _MOUNTS[\"ai_semiconductors\"] - the only enrolment. The registry's own line 172 is `anchor_theme_id=_SEMICONDUCTOR_MOUNT.anchor_theme_id`, an ATTRIBUTE reference, which is why an `anchor_theme_id=\"...\"` pattern finds nothing there and a naive grep reads as 'no anchors registered'. Track DECLARED and ENROLLED separately or the instrument lies."
  - claim: "Both Robotics modules are free of third-party imports entirely, not merely at top level; and each carries TWO first-party imports that execute at import time, one of which is wrapped in a module-level try and is therefore invisible to a column-anchored grep."
    command: "gh api contents/<path>?ref=36efe9c92b96 | base64 -d, then ast.parse and classify every Import/ImportFrom by whether its parent chain contains a FunctionDef/AsyncFunctionDef/ClassDef (deferred) or not (executes at import time), recording enclosing Try/If nodes; the column-anchored `grep -c '^from \\|^import '` reproduced as a control on the same bytes"
    result: "Re-measured 2026-09-27 by AST, correcting a 2026-09-26 undercount. Composer (60749B): import-time = 8 stdlib/__future__ plus TWO first-party - engine.theme_graph.curation_assertion at :45 AND engine.market_ontology.semiconductor_theme_research at :123 inside a module-level try at :122; deferred = engine.theme_graph.identity at :68. Owner bundle (12407B): import-time = 3 stdlib plus TWO first-party - engine.market_ontology.robotics_theme_research at :156 AND engine.market_ontology.theme_research_binding at :162 inside a module-level try at :161; deferred = engine.theme_graph.rights at :197 'lazy by design'. THIRD-PARTY anywhere in either file, deferred sites included: zero. The earlier entry reported ONE first-party import per file because its instrument was `grep -c '^from \\|^import '`, which anchors at column 0 and cannot see an indented import inside a top-level try; reproduced on the same bytes it still returns 9 and 4, the exact figures that were published. A try/except does not exempt an import from the repo's static sweep, and BOTH missed sites are named in #8013's own body among the four absences that broke main. Fixing the awk-stops-at-^def blind spot while keeping the column-0 blind spot is why a positive control proves only that a scan found something, never that it found everything."
  - claim: "The two outbound executive-contract comments on this operation carry their intended content, not a file path."
    command: "gh api repos/{o}/{r}/issues/comments/<id> then compare in-process: json.load(...)['body'] == open(src, encoding='utf-8').read()"
    result: "5852920768 (2877B) and 5853205639 (3235B), both on #7780, both byte-identical to source, trailing newline included. Both were first posted with the body `@/private/tmp/...` because `gh api -f body=@file` sends a static string - file reading is -F, or build JSON and pipe to --input -. An earlier note of a '1-byte trailing-newline delta' was a command-substitution artifact; there is no delta."
  - claim: "The #7870 ordering is a HARD COMPILE-LEVEL dependency, not a sequencing preference. Four first-party symbols the Robotics modules import do not exist on main; all four exist at #7870's head. This is the mechanical cause of #7908's CI failure and therefore of the revert."
    command: "gh api repos/{o}/{r}/actions/runs?head_sha=d259ec08d58c7e6762151e84959dbf8f80870fbf then gh run view --repo {o}/{r} --job 107985021309 --log; then for each symbol gh api contents/<path>?ref=a0d7b054ff23 and ?ref=main by EXIT CODE with agentos/README.md as positive control, plus base64 -d and grep -c on engine/theme_graph/rights.py at both refs"
    result: "#7908's own ci run 36107534349 on head d259ec08d58c is completed/FAILURE - 12 packs, ci-pack-4 FAILED, contract-delta FAILED, ci-gate FAILED - and it merged anyway via merge-on-green. ci-pack-4's failing step is tests/test_first_party_import_names.py::test_every_first_party_import_resolves, a STATIC AST guard, reporting: robotics_theme_research.py:45 engine.theme_graph.curation_assertion does not exist; :123 engine.market_ontology.semiconductor_theme_research does not exist; robotics_owner_bundle.py:162 engine.market_ontology.theme_research_binding does not exist; :197 engine.theme_graph.rights defines no load_registry_snapshot. Probed at both refs: all three modules EXIST at a0d7b054ff23 and are ABSENT on main; rights.load_registry_snapshot is defined at a0d7b054ff23:156 and has 0 definitions on main; positive control agentos/README.md present at both refs, so the absences are real and not a broken probe. Consequence: ruling 10 is vindicated mechanically - there is no safe half to split off, because BOTH modules carry unresolvable imports. These are the same four absences #8013's body named; this entry is the first to verify them and to identify #7870 as their supplier."
  - claim: "All six Robotics test suites were wired into no workflow job and therefore NEVER EXECUTED; the repo's own contract-delta gate detected exactly this and named all six. A re-land of only the 35 reverted paths reproduces the defect."
    command: "gh run view --repo {o}/{r} --job 107983974666 --log with sed to strip terminal colour before grepping; then scripts/check_contract_delta.py and scripts/audit_unrun_tests.py at ref=main; then a yaml.safe_load census of .github/ci/legacy-jobs.yml counting gate values and jobs naming an explicit tests path"
    result: "contract-delta emitted, for each of the six: '<suite> is a new pytest suite named by no run: step in any workflow - wire it into the job that owns its scope', summary 'contract-delta: 6 introduced, 4 inherited (base 92e2f19513fb)'. Corroborated independently in pack4.log: every Robotics filename there comes from the static guard's own report, zero pytest invocations, zero collection errors, and test_robotics_theme_non_regression.py appears nowhere at all - and 'ran and passed' was impossible with curation_assertion absent while the other 11 packs were green. ci-plan also flagged '7 unowned path(s) did not widen (tests/robotics_research_helpers.py)'. The revert's 35-path manifest contains no .github/ file, and that absence WAS the defect. Gate predicate: check_contract_delta.py calls audit_unrun_tests.gated_unrun_suites() = census minus baseline minus waivers, and coverage is _named_by_a_run_step at audit_unrun_tests.py:591 - a plain substring match of the FULL relative path against the concatenated body of every workflow run: step, with the basename fallback disabled for basenames shared by two suites. So a glob such as tests/test_robotics_*.py does NOT satisfy it; all six full paths must appear literally. The scanned file set is WORKFLOWS.glob('*.yml') PLUS an explicit append of CI_MANIFEST = .github/ci/legacy-jobs.yml (:450-451, :127), so wiring in legacy-jobs.yml DOES count; a step body extracted to scripts/ci/<name>.sh is resolved back to its shell source, so naming a suite inside an extracted script counts too. main carries 237 legacy jobs, 165 gate:code and 72 gate:data, and 160 of the code ones name an explicit tests path - do NOT quote #7908's '159', which was its base."
  - claim: "The two other red lanes on #7908's merge commit are NOT caused by the Robotics content, so the re-land must not widen scope for either."
    command: "gh api repos/{o}/{r}/actions/workflows --paginate to resolve ids, then actions/workflows/<id>/runs?branch=main&per_page=30 --jq .conclusion for each; then gh run view --job 107985040911 --log for the integration-baseline failure text"
    result: "engine-render on main is 19 cancelled, 8 failure, 2 success of its last 30 runs - the chronic render-lane outage, pre-existing and unrelated. integration-baseline on main is 27 success, 2 failure, 1 cancelled, i.e. healthy, so its red needed explaining: the failure is tests/test_ci_pack.py::test_derived_scopes_are_startable_by_the_ci_workflow asserting on ('p0b-receipt-closure', 'mockups/evidence/prophet-p0b-zero-fouc/**') - another team's Prophet P0B job, with zero Robotics content anywhere in the log. So the revert's causal set is exactly these two defects plus the ci-gate adjudicator that enforces them. That same test is wired into legacy job ci-control-plane-contracts at gate:code, so it RUNS PRE-MERGE in the pack matrix even though the integration-baseline workflow itself is push:main only - which is what makes the ci.yml path-ownership entries mandatory rather than cosmetic."
  - claim: "Every earlier reading of the contracts guard in this record was of #7870's version, not main's. The Gate C substance survives on main's version; the line citations did not."
    command: "gh api contents/scripts/check_theme_graph_contracts.py?ref=main and ?ref=a0d7b054ff23 --jq .size, then diff, then a repeat of the ast.parse notices/breaches census and the marker/strict/census greps against main's bytes"
    result: "main 85824B, a0d7b054ff23 87600B, 36 differing lines - and the per-construct offsets are MONOTONIC INSERTION, a0d7 having 36 lines main lacks: -28 by the store-incomplete notice, -35 by the licensing and capability titles, -36 from the census guards through the return block and selftest. That monotonicity is why no single offset works, and it also refutes the -37 an earlier draft of DEC2 claimed: -37 came from pairing a0d7's breach line 960 against main's CONDITIONAL at 923 rather than against the breaches.append at 924. Both refs this record ever read (a0d7b054ff23 and 1e38d5c955dc) are #7870-lineage, and the note that those two are byte-identical was true but concealed that neither is main. main's version does NOT import engine.theme_graph.curation_assertion - that import is #7870's addition, which is also why the guard could not have run on a main lacking the module. Re-verified on main's bytes point by point: --strict present, the census present, the marker line present, CONTRACTS = ROOT / 'contracts' / 'theme_graph', the same `if not breaches:` then `if not notices:` return block, zero glob/rglob/os.walk/iterdir/listdir, zero market_ontology or robotics mentions, 6 notices.append and 33 breaches.append sites, and the census at L1008 guarded only by idres_path.exists() with the sidecar committed on main at 204044B. So the compound predicate holds unchanged. Corrected main-version citations: marker print :1063, `return 1 if strict else 0` :1073, --strict help :1546, census notice :1008, census-excluded-from-incidents :1196, selftest census assertion :1298, CONTRACTS :78, audit() :336."
unverified:
  - claim: "The re-land will pass its gates once #7870 has merged AND the six suites are wired. The 35-paths-only form is not merely unverified, it is REFUTED - it reproduces the unwired-suite defect."
    what_would_verify: "After #7870 merges: restore the 35 paths as they stand at 36efe9c92b96 (NOT a cherry-pick of that commit - see danger_areas), add the CI wiring, and then require the four gates that actually bite, in-flight on the carrier PR rather than locally: tests/test_first_party_import_names.py::test_every_first_party_import_resolves; scripts/check_contract_delta.py reporting 0 introduced; tests/test_ci_pack.py::test_derived_scopes_are_startable_by_the_ci_workflow; and ci-gate adjudicating those. Gates A (136) / B (623) / D (20 passed, 116 xfailed) still need re-establishing rather than assuming. Gate C is NOT among the re-land gates - see the scope note in DEC:THEME-GRAPH-CONTRACTS-GATE-IS-A-COMPOUND-PREDICATE."
  - claim: "The shared owner's Q1 can be satisfied by the R1 corpus."
    what_would_verify: "Their own adjudication. Measured fact they need: all 21 R1 fixtures are `synthetic: true` (every one checked 2026-09-26), so if Q1 requires real retained evidence the re-land will never deliver it - that is the held R5 lane, not the re-land."
  - claim: "The gate A / B / D counts quoted in this record (136, 623, and 20 passed with 116 xfailed) still hold."
    what_would_verify: "A run on the re-landed tree. These are the pre-revert local figures from the #7908 build, carried here as the target to re-establish; no command in this record measures them, and the reverted code is not on main to re-measure. Treat them as the expected shape, not as a verified result."
  - claim: "Any Robotics live path exists."
    what_would_verify: "R4 nonce proof by the store owner, real assertions admitted through the shared admission path into the private key space, entitled API returning them, anonymous negative, deployed browser proof. None of this is built."
unresolved:
  - "BLOCKER (owner's call, not this seat's): #7870 is OPEN, MERGEABLE, mergeStateStatus UNSTABLE, and DRAFT. Draft status is the only blocker THIS SEAT can name, and that is weaker than 'the only blocker': mergeStateStatus UNSTABLE in the same reading means its checks are not green, which is a second unresolved condition this record did not diagnose and does not own. Both values are a point-in-time poll - re-read the carrier before relying on either. The Robotics re-land is sequenced entirely behind it. The draft/blocking-dependency topic is already well covered on that thread, including a receipt and its own correction, so re-raising it would spend the owner's attention on what their merge box already shows."
  - "STANDING JOINT OBLIGATION (v1.1): object.subject_role in {acquirer, seller, party} plus a JOINT DEFINITION_VERSION bump, owed with #7870's owner. Confirmed live and unbuilt on both sides - V1_1 is PROPOSED_NOT_BUILT and the registry still imports the unbumped _SEMICONDUCTOR_DEFINITION_VERSION. Shared-contract compatibility is a principal decision, not a lane decision."
  - "RULED, no split re-land (ruling 10): the carrier re-lands whole, behind #7870, or not at all. Read-only retrieval of the reverted paths for measurement does not violate this; adding any subset of them to main does."
  - "RULED, registration is POST-MERGE (ruling 6): the shared registry imports a vertical's composer eagerly at registry-import time, so the Robotics registry entry cannot land before the carrier's modules are on main. Corroborated by four independent sources including the shell owner's own statement that the registry resolves to ['ai_semiconductors']."
  - "RULED, merge is not acceptance (ruling 7): a green main is not acceptance either. This is why MISSION_COMPLETE is not claimable on a merge, and why the completion criterion is the real-path law in the master packet section 3."
  - "RULED, retention is by design (ruling 11): RBV-18 is a designed retention contract, not a defect. The design-vs-defect test that settled it: is there a contract statement (docstring or comment) AND a pin whose name states it? Contract plus pin = design. Neither = defect."
  - "CONFIRMED DEFECT (ruling 12): the cross-scope _correction_lineage walk. Distinct from ruling 11 by the same test - no contract statement, no pin."
  - "RULED, the Robotics mount partial is RETIRED (ruling 5); scope.canonical_theme_id carries theme:<slug> (ruling 8); ruling 9 is VOID and any law derived from it is withdrawn."
  - "NOT THIS OPERATION'S WORK - three sector dependency clarifications adjudicated out of scope (Materials #7773 comment 5809093547, Communications #7870 comment 5846455819, Semiconductor B to Communications #7870 comment 5852703250), each addressed to the shared owner with no receiver assigned. 5852703250 is authored by the same GitHub login this seat writes under, which is shared across operations on this account - Semiconductor B is a different operation, so common authorship is not common ownership. Reusable triage rule so a successor need not re-adjudicate: not mine when (a) the addressee is the shared or incumbent owner or another sector's operation, (b) it names no Robotics coordinate - Robotics is a canonical THEME with slice_keys, while sector dossiers, rosters and issuer sets are a different coordinate, and (c) any fact this lane could contribute is already on that thread from its owner."
  - "OPEN OFFER, no reply: the #8011 seat owns the CI baseline. No word received."
next_actions:
  - "WAIT on #7870. Do not re-land, do not split, do not register. Two watchers are the attention path; they are session-local and die with the session, so a successor re-arms rather than inherits."
  - "WHEN #7870 MERGES: re-land in ONE carrier, and the carrier is 35 paths PLUS CI wiring. Restore the 35 paths to their state AT 36efe9c92b96 - do NOT cherry-pick that commit, which is a one-line append to data/ops/nightly_timings/tech_lab_offrender.jsonl and contains no Robotics at all; the RESTORATION list is the revert e5512ef66a74's own file list inverted, and its additions:0/deletions:14404 proves the carrier was purely additive - but the CARRIER MANIFEST is that list PLUS the CI wiring below, and conflating the two is the mistake this runbook exists to prevent. Then WIRE THE SIX SUITES or contract-delta fails exactly as it did on #7908: add a gate:code job to .github/ci/legacy-jobs.yml naming all six FULL paths literally in run: steps - tests/test_market_ontology_robotics_theme_research.py, tests/test_robotics_owner_bundle.py, tests/test_robotics_research_composition.py, tests/test_robotics_research_inputs.py, tests/test_robotics_research_temporal.py, tests/test_robotics_theme_non_regression.py - because the matcher is a substring test on the full path and a glob satisfies nothing; plus ci.yml path-ownership entries so the owning pack starts, which test_ci_pack.py::test_derived_scopes_are_startable_by_the_ci_workflow enforces pre-merge. Do NOT instead add them to the unrun baseline (that is the grandfathering path for pre-existing debt, which is why these blocked as newly introduced) and do NOT waive them in the waivers file (that would re-land 3729 lines of tests designed never to run - 3729 measured, not recalled: the six suites' deletions in pulls/8013/files sum 957+293+814+749+410+506). The four gates to require are the import resolver, contract-delta at 0 introduced, the startability test, and ci-gate. Gates A/B/D re-established rather than assumed. BEFORE asserting that a 35-paths-only re-land still reproduces D2, RE-CHECK the unrun baseline and the waivers file at the re-land head: the gate is gated_unrun_suites() = census MINUS baseline MINUS waivers (audit_unrun_tests.py:745), so if the seat that owns the CI baseline (#8011, open offer, no reply as of this record) enrolled these six paths during the hold, contract-delta would report 0 introduced and D2 would NOT reproduce. That would not make a 35-paths-only re-land correct - it would mean the tests are recorded as permanently unrun instead of failing loudly - but it changes what the gate tells you, so measure it rather than assuming. Note also the sound form of the test: the defect is not 'the manifest contains no .github/ file' but 'no path in the manifest lies in the GATE'S SCANNED SET' - the workflows glob, legacy-jobs.yml, and a step body resolved back to its scripts/ci/*.sh shell source. Measured on the manifest: 0 paths under .github/ AND 0 under scripts/, so the conclusion holds on the correct test. Gate C is NOT a re-land gate: the guard's read roots are contracts/theme_graph/ and data/theme_graph/, 0 of the 35 reverted paths lie under either (the one contracts/ path is contracts/market_ontology/robotics_theme_research.v1.schema.json), and the guard does zero glob/rglob/os.walk/iterdir/listdir while the revert is additions:0 - so every restored path is a NEW file a non-enumerating guard cannot read. It belongs to the post-merge enrolment step, once the mount actually writes to the store."
  - "THEN, as a separate post-merge additive commit: the Robotics registry entry. It MUST use the lazy loader wrapper pattern (a module-level function that defers `from engine.market_ontology.robotics_owner_bundle import ...` inside its body, with a noqa PLC0415 and a stated reason), never a top-level import - the registry sits in the shared app.main import closure and the shell owner already took 4-of-7 pack failures from exactly one hard top-level import there. The composer must also stay third-party-free at top level, because the registry imports it eagerly."
  - "Before any substantive reciprocal write: fresh-read the exact bound carrier in the same turn, and include an abort guard comparing the latest comment id. Class-M default interval is 60 minutes, hard floor 15."
  - "DONE in this same change: the two highest-consequence ruling clusters are now DEC records - DEC:GMI-ROBOTICS-RELAND-ORDERING-AND-REGISTRATION (rulings 5, 6, 7, 10 plus the lazy-wrapper requirement) and DEC:THEME-GRAPH-CONTRACTS-GATE-IS-A-COMPOUND-PREDICATE (the withdrawn exit-code gate, and why the script's own success line is not its replacement). The convention in this program is one DEC per coherent cluster, not one per ruling, following DEC:IND-FIRST-VERTICAL-CARRIER-AND-ORDERING. Rulings 8, 11 and 12 remain prose in this record; ruling 9 is void and needs none. Promote 11 and 12 together if a later lane re-opens the design-versus-defect question, since the test that separates them is the reusable part."
  - "Held lanes, in dependency order once the re-land clears: R5 real evidence qualification through the shared admission and private adapter (also the likely content of the shared owner's Q1); R5 rights seam; R6 remaining halves (registration post-merge, served API is the shell owner's file); live admission; browser and production acceptance."
do_not_redo:
  - "The 35 reverted paths are NOT lost and do NOT need rebuilding. Every one is retrievable at 36efe9c92b96, verified by exit-code test with a positive control. Re-authoring any of them is duplicated work."
  - "Do not re-adjudicate the three sector dependency clarifications listed in unresolved - the triage rule there settles them."
  - "Do not re-measure the R1 corpus for synthetic status: all 21 fixtures are synthetic: true, every one checked. tests/robotics_research_helpers.py states the contract and refuses any value whose synthetic flag is not explicitly True."
  - "Do not rebuild the source-rights qualification matrix. research/theme_graph/thematic_research_20260924/ROBOTICS_SOURCE_RIGHTS_QUALIFICATION_2026-09-24.md (56508B) exists at 36efe9c92b96: one row per publisher host by source class, terms actually inspected with timestamps, READ versus INFERRED per clause, a minimum positive witness, refusal behaviour, and gaps G1/G2/G4."
  - "Do not create another Theme Graph, a global Robotics product master, another evidence or correction system, another identity system, another private publication plane, another scheduler, queue or watcher, or another theme-detail dashboard. Do not create /api/themes/v1/robotics as a parallel route without an explicit architecture ruling. Do not create a Robotics-specific database, bucket, private store, publisher, evidence ledger or scheduler."
  - "Do not edit #7870, #7462 or #7669 paths from a Robotics carrier WHILE THOSE CARRIERS ARE IN FLIGHT. This stops applying to a given path the moment that carrier's modules are on main: the post-merge registry entry in next_actions edits theme_research_registry.py, which is a #7870 path today and a main path afterwards."
  - "Do not alter Robotics basket membership or weights, ThemeState, Theme Tracker recommendation/lane/stage, Prophet or member ranking, entry gates, sizing, alerts, or trading. Research coverage carries zero automatic decision authority."
danger_areas:
  - "A local gate proof is never a substitute for an in-flight CI result - it is what tempts you not to wait for one. This operation's revert exists because a carrier was merged 2m22s after the correct CI run started against the correct base (run created 07:25:12Z, merge 07:27:34Z), and that run went red only AFTERWARDS - the first failure 9m47s post-merge and the import defect 27m35s post-merge, on a pack that had passed at the previous head. The window is not four minutes; it is long enough that waiting feels unreasonable, which is the whole trap. Check `gh pr checks` for anything PENDING, not merely for anything red."
  - "Importable is not served. A static import guard, a linter, a collection sweep and a coverage run all touch files nothing serves, so 'nothing uses it at runtime' is not 'nothing reads it'."
  - "Testimony is not observation, including an API's testimony about your own write. `gh api -f body=@file` posts the literal path (-f is a static string; file reading is -F, or build JSON and pipe to --input -), returns a normal id and exits 0. Read every outbound write back and compare in-process; keep the shell out of the comparison, because command substitution strips trailing newlines and jq appends one, and both manufacture phantom deltas on correct content."
  - "GitHub instruments under-report SILENTLY, so every absence claim from them needs a positive control: trees truncate, `gh pr diff --name-only` 406s over 300 files, `gh api compare` caps at 250 commits AND 300 files, issue comments paginate to page 1 only, and `gh api` prints a 404 body to STDOUT so presence must be tested by EXIT CODE. `?since=` on issue comments filters on updated_at, so it catches EDITS that a comment-id high-water mark misses, and a re-emitted id is correct behaviour rather than a duplicate bug."
  - "Full-fidelity real Robotics assertion bodies must never enter a public carrier, evidence.parquet, site/ or public R2. The repo is public; fixtures stay synthetic with example.invalid or already-public vendor pages."
  - "Builder is not reviewer, and this is mandatory. In-flight worker returns are not truth until reviewed and integrated."
prs: [7773, 7780, 7870, 7908, 8013]
decisions:
  - "DEC:GMI-ROBOTICS-RELAND-ORDERING-AND-REGISTRATION"
  - "DEC:THEME-GRAPH-CONTRACTS-GATE-IS-A-COMPOUND-PREDICATE"
---

# GMI Robotics - re-land hold, post-revert (2026-09-27)

This record exists because the revert that correctly removed this operation's *code* from main
also removed its *knowledge record*. A revert aimed at an import blocker is not a decision to
forget why the work existed, what was ruled, or what a successor must not redo. Nothing here
restores code.

## Where the operation actually stands

Implementation carrier #7908 merged and was reverted the same day. The cause was narrow and is
fully understood: modules living only in the unmerged #7870 became unresolvable first-party
imports on a main that does not have them, and the repo's static import sweep is not softened by
a try/except, because its own guard synthesises a try-wrapped import specifically to catch that.
The heal was a plain revert of the merge commit. The re-land waits on #7870 - which supplies four
first-party symbols the Robotics modules import and main lacks, so the dependency is a compile
dependency and not a courtesy - and on CI wiring for its six test suites, which the original
carrier never had and which is the second, independent reason it was reverted.

The shared foundation #7870 has moved for the first time in this hold: its head went
an earlier head (recorded here only as an 11-char abbreviation, so not re-verifiable and deliberately not restated) to 1e38d5c955dc to a0d7b054ff23, and its state went CONFLICTING to MERGEABLE with
behind_by 0. Draft status is now the only blocker, and that is its owner's decision.

## The twelve rulings, by number

Rulings 1 to 4 are carried in the packet and the predecessor record. The ones a successor is
most likely to trip over:

- **5** - the Robotics mount partial is RETIRED. Robotics mounts by REGISTERING in the shared
  shell, not by shipping its own partial.
- **6** - mount registration is POST-MERGE, because the shared registry imports a vertical's
  composer eagerly at registry-import time. Corroborated four independent ways.
- **7** - merge is not acceptance, and a green main is not acceptance.
- **8** - scope.canonical_theme_id carries `theme:<slug>`.
- **9** - VOID. Any law derived from it is withdrawn.
- **10** - no split re-land. Vindicated mechanically, not just by preference: both Robotics
  modules carry imports that cannot resolve on today's main, so there is no safe half.
- **11** - RBV-18 retention is a designed contract, not a defect.
- **12** - the cross-scope `_correction_lineage` walk is a CONFIRMED defect.

Rulings 11 and 12 look like the same shape and resolve opposite ways. The test that separates
them: is there a contract statement in a docstring or comment, AND a pin whose *name* states the
behaviour? Contract plus pin is design. Neither is a defect.

## Gate taxonomy, with Gate C corrected

Gate A is 136, Gate B is 623, Gate D is 20 passed and 116 xfailed - those three are the
pre-revert local figures to re-establish, not results this record verifies. **Gate C was hollow
and the earlier definition is WITHDRAWN.** It was recorded as `check_theme_graph_contracts.py`
exiting 0, and that script returns 0 on a real breach unless `--strict` is passed. That much is
read directly from the source. The one EMPIRICAL corroboration is testimony, not an observation of
mine, and now pinned to its source rather than recalled - #7780 comment `5853134369`
(2026-09-27T05:50:57Z) reports materialising `data/regime` and `data/theme_graph` (8.5 MiB) and
getting "1168 identity_resolution row(s) violate the state<->ids biconditional" plus a 2807-node
census, "and exits 0 anyway". I did not witness that run and did not read its output back. It sits
on #7780, the shared contracts carrier, NOT on #7870 - two different seats an earlier draft
collapsed into one "shell owner". Do not try to identify the seat from the comment's login: it is
`chriswong6031-creator`, shared across agents, so the lane is established by the carrier alone.

The first replacement written here was also wrong, and an independent audit caught it before it
landed. Gating on the script's own success line looks airtight - it prints on exactly one path -
but that path requires `notices` to be empty too, and the identity-resolution census (a0d7 1044 /
main 1009 - every four-digit number in this record is a0d7's unless dual-stated, and the full
offset table lives in DEC-THEME-GRAPH-CONTRACTS-GATE-IS-A-COMPOUND-PREDICATE)
is an unconditional notice whenever `data/theme_graph/identity_resolution.parquet` merely exists.
That file is committed. So the success line never prints on a materialised store, clean or not,
and a gate built on it is permanently red and indistinguishable from a real breach. So:

> Gate C := `--strict`, on a materialised `data/`, AND exit 0 AND no
> `::warning title=theme graph contract breach::` line AND every
> `::notice title=theme graph - <class>::` enumerated and triaged by class.

SEVEN classes, and the titles below are quoted with the source's EM-DASH (U+2014) because that is
what a successor must grep for; an ASCII hyphen returns a false absence. Designed and
non-blocking: `[identity resolution census]`, `[licensing snapshots — designed]`, and
`[additive columns pending rebuild]`. Blocking: `theme graph indeterminate` (store incomplete),
`[capability side-car MISSING — half-finished build]`, `[identity resolution side-car MISSING —
half-finished build]`, `[capability promoted itself]`. An independent review corrected this list
from six: `notices` is fed by 6 `notices.append` sites AND by 4 `notices += ...` merges
(main:366, 620, 777, 824), all from `_check_columns` (main:250), which emits its own designed class
at main:262. Six was the count of appends, never of classes, and an untriaged additive-columns
notice would have read as BLOCKING when it is designed — inverting the verdict on exactly the
pre-migration store the class exists to tolerate. The script's own comment (a0d7 1090 / main 1055)
states why the titles differ, which is what makes triage by title sound. Unmaterialised `data/` is
INDETERMINATE.

**Gate C is NOT a gate on the re-land.** It governs the post-merge enrolment step. The guard's read
roots are `contracts/theme_graph/` and `data/theme_graph/`; no reverted path lies under either
(measured: 0 of 35), the one `contracts/` path being
`contracts/market_ontology/robotics_theme_research.v1.schema.json`. The guard also does zero
`glob/rglob/os.walk/iterdir/listdir`, and the revert is `additions: 0`, so every restored path is a
NEW file that a guard without directory enumeration cannot read at all. Its verdict is therefore
identical with and without the carrier.

Two corrections to the framing earlier drafts carried, plus a third from independent review.
First, the advisory exit code is DESIGNED and documented — `config/house_law_checks.yml:2853-2857`
(`known_limits` on law `theme_graph.edge_contract`, :2824) gives the reason (display-tier, a breach
must not take the nightly collect lane down), and the same comment sits at the nightly call site
itself. Second, and found only by checking the workflows instead of trusting that row: **no
pull-request lane runs this guard.** Third, and this RETRACTS a claim earlier drafts made: that
same `known_limits` block asserts at :2857 that "`--strict` is what CI runs", and I repeated it as
if it exonerated CI. It does not, and it is refuted by the wiring I measured. The law's declared
`ci_wiring` (:2843-2849) names two lanes. The `scheduled` one (:2847-2849, `daily.yml` job
`engine`) IS live but reaches the guard indirectly — `daily.yml:1895` job `engine` runs
`bash scripts/ci/daily_engine_regional_desk_builders.sh` at :3244, and that script's invocation at
:118-120 passes **no `--strict`**. The `pr_ci` one (:2844-2846, `legacy-jobs.yml` job
`unrun-intl-libraries`) is STALE, for the reason below. So the only live invocation anywhere is
advisory, the only `--strict` invocation in the repo sits in an `if: false` job, and "the hollow
gate was this seat's local run, never CI's" — which an earlier draft of the PR body said — is
false. No measured lane runs this guard with teeth in any mode. The `--strict` invocation is real (`.github/ci/legacy-jobs.yml:11456`) but its job is
`gate: data` and `if: false`, executed only through `run_ci_pack.py`, whose selector is
`job.gate == gate`; the only `--gate data` caller is `data-health.yml`, triggered by schedule and
by `daily` completing, never by `pull_request`. The row's `lane: pr_ci` is stale.

So the local Gate C is not a belt-and-braces supplement to a CI gate. For a carrier PR it is the
only theme-graph contract verdict that will exist before merge, which is why getting its predicate
right was worth the correction rounds it took.

## DECLARED versus ENROLLED

Ruling 6 turns on a distinction that is easy to measure wrongly.
`theme_research_mounts.py` **declares** a mount with a literal
`anchor_theme_id="<id>"`. `theme_research_registry.py` **enrols** it with
`_MOUNTS["<id>"]`, and its own `anchor_theme_id=` line is an attribute reference, not a literal.
A grep for the literal pattern therefore returns nothing against the registry and reads exactly
like "no anchors are registered." Track the two sites separately, and control the instrument with
a positive, a negative and a teeth case before believing any answer it gives.

## Why MISSION_COMPLETE is not claimable

Ruling 7. The completion criterion is the real-path law in the master packet section 3: a
fixture-green composer, a 200 from the shared API, or a rendered shell is not the vertical. A
merge of the re-land would not be acceptance either. The target classification is
PROVEN_OUTCOME, and the honest current classification is BLOCKED, with the block outside this
seat's authority to clear.
