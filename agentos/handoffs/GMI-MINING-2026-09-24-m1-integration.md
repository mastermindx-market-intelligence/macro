---
workstream: "WS:GMI-MINING-M1-INTEGRATION"
session: claude/mining-seat-wave1
model: fable
ended_because: blocked
mission: >
  Live seat checkpoint for gmi-mining-fable-ceo-m1-integration-20260924-chairman-001: deliver
  the first Mining release (real signed-in Freeport W-C and MP Materials W-R economic dossiers)
  on the Semiconductor-led shared foundation by shipping plan tasks T01'-T08 as fabric-built PRs
  in dependency order. Effects behind held gates G1 (exact shared profile/callable), G2 (native
  source bytes), G5/G6 (private route, mount) stay frozen while source-independent synthetic and
  incumbent-owner lanes continue; the seat session is still running.
state_before: >
  Research/design/plan/packet prepared on #7795 @ eb6f05c0 (PREPARED_FOR_REVIEW_AND_PLACEMENT,
  BUILD_READY false, no receiver). Semiconductor B #7870 DRAFT @ dd5076fa: mount + theme-research
  UI landed after the packet pin c6c67c87, composition schema still semiconductor-only, no reply
  to Mining request 5809893850. CDV-1 T1 #7905 open on the issuer_profiles seam (accepted
  pg_profile idiom). No app/theme_research.py route on main.
changed:
  - path: agentos/workstreams/WS-GMI-MINING-M1-INTEGRATION.md
    what: "Workstream minted: objective, owned paths, five waves, do_not_redo, landmines."
  - path: agentos/handoffs/GMI-MINING-2026-09-24-m1-integration.md
    what: "Seat pickup checkpoint: state, gates, fabric/hosts, wave plan."
  - path: research/mining/m1_integration_program/rulings/R-MIN-2026-09-24-wave1.md
    what: "R-MIN-00..09 wave-1 rulings plus seam rulings R-MIN-10..28 consumed from the two Opus read-only seam audits (A: Company/receipts -> T02/T03/T07; B: shared-base/ontology -> T01'/T04/T06)."
  - path: research/mining/m1_integration_program/reviews/
    what: "OPUS_SEAM_AUDIT_A_COMPANY, OPUS_SEAM_AUDIT_B_ONTOLOGY (26 findings; 4 blockers) and OPUS_T04A_CONTENT_REVIEW_R1 (ACCEPT-WITH-FIXES on #7922)."
verified:
  - claim: "Every packet member byte-matches the research carrier; README blobs (master packet, addendum, plan, design, canonical P05) resolve on origin/sol/mining-principal-research-20260923 @ eb6f05c0."
    command: "git hash-object <member> vs git rev-parse origin/sol/mining-principal-research-20260923:<path> for all 11 members"
    result: "match=11 mismatch=0; five README blobs OK."
  - claim: "The packet's own handoff checker runs clean from the extracted root."
    command: "python3 research/mining/check_mining_handoff.py"
    result: "receipt written; checker_blob 6b815443 as stated in README."
  - claim: "Semiconductor B has no shared POST route on main and its composition schema is still semiconductor-only."
    command: "git ls-tree -r --name-only refs/remotes/pr/7870 | grep -E 'app/theme_research|theme_research.*schema'"
    result: "only contracts/market_ontology/semiconductor_theme_research.v1.schema.json and engine/market_ontology/semiconductor_theme_research.py."
  - claim: "No shared-owner return to Mining request 5809893850 exists on #7870."
    command: "gh api repos/.../issues/7870/comments | select(.id > 5809893850)"
    result: "seven later comments, all sibling-sector notices (Finance, Industrials, Energy, Robotics, Consumer, GMI Wave1, Tech ex-Semis)."
  - claim: "T01' consumption harness is on origin/main and green: binding module (limit 1..100, import_module shared-contract probe), casebook, suite + frozen Opus probes, gate:code job mining-economic-dossier with CURATED_EXCLUSIVE entry."
    command: "git cat-file -e origin/main:<path> for the five artifacts; TZ=UTC python -m pytest tests/test_mining_shared_contract.py tests/test_mining_shared_contract_probes.py -q in a venv built from `pip install pytest jsonschema pyyaml`"
    result: "PR #7932 merged ee908cb8f0b5 2026-09-24T12:52:49Z on 26 concluded checks / 0 red; 67 passed at ee908cb8."
  - claim: "The Opus R1 red-team of #7932 was consumed by freeze-then-repair, not by self-written tests."
    command: "git log --oneline origin/main -- tests/test_mining_shared_contract_probes.py"
    result: "probe freeze commit (9/10 RED at a27a7262) precedes the repair commit; report at research/mining/m1_integration_program/reviews/OPUS_T01_PR_REVIEW_R1_2026-09-24.md."
  - claim: "The T04a round-3 fabric delivery is real work, not a self-verdict: the frozen oracles were untouched by the repair lane and the whole Mining gate is green at the pushed head."
    command: "git log --oneline a848ad54..HEAD -- tests/test_mining_composition_probes.py tests/test_mining_composition_probes_r2.py tests/test_mining_composition_truth_table.py tests/fixtures/mining_economic_dossier/ (empty); git diff --name-only a848ad54..HEAD; venv(pytest jsonschema pyyaml) -m pytest -q on the six Mining suites; python -m pyflakes on the module + both changed tests"
    result: "frozen-file log EMPTY (lane owned only engine/market_ontology/mining_theme_research.py and tests/test_mining_composition.py); 160 passed, 0 failed at 94e74dd8; pyflakes clean. The lane's own LANE_DONE said verdict PASS 0/0/0 - that is a self-verdict and was NOT taken as proof."
  - claim: "The R1 BLOCKER-1 probe premise was false about the casebook, so the seat amended the probe instead of letting the module fabricate legs (R-MIN-32)."
    command: "python3 -c on tests/fixtures/mining_economic_dossier/copper_complete.json economics block; grep -n financial_packets tests/mining_casebook.py"
    result: "casebook line 76 builds financial_packets from fixture['economics']; copper's economics is {measure, value, basis, stream_threshold, positive_witness} with no earlier_point_estimate/later_actual. Two comparison rows were not composable without fabricating both legs. Amended at 4a6a70f68bd with every original assertion kept and leg-value/polarity pins added."
  - claim: "The module genuinely composes real pairs: two in-test R-MIN-31 packets yield two distinct rows with numeric legs and polarity derived from the numbers."
    command: "compose_mining_research on copper_complete with financial_packets=(mev('sales',1700,1680,'Mlbs'), mev('unit_net_cash_cost',1.55,1.62,'USD/lb'))"
    result: "2 rows; metrics management_issued_copper_sales_estimate/consolidated_copper_sales and the unit_net_cash_cost pair; values 1700/1680 -> below_estimate and 1.55/1.62 -> above_estimate; is_range and is_consensus both false. Round 2's string \"quarter\" leg is gone."
  - claim: "The one contract-delta 'introduced' on this branch is a stale-base artifact, not a defect of this PR."
    command: "python3 scripts/check_contract_delta.py --base origin/main; git cat-file -e origin/main:tests/test_render_dead_ref_targets.py; git grep -c test_render_dead_ref_targets origin/main -- .github/ci/legacy-jobs.yml; git rev-list --count HEAD..origin/main"
    result: "the named file is NOT in this branch's own diff, exists on origin/main AND is wired there; the branch was 469 commits behind. Merged origin/main (clean, no conflicts) so CI and the checker read true."
  - claim: "PR #7870's shared module has still not landed, so the Mining typed-degrade path is the live path."
    command: "ls engine/theme_graph/curation_assertion.py at 94e74dd8 (post-merge of origin/main)"
    result: "absent; the importlib try/except ImportError degrade is exercised, and the shared-contract suites pass on it."
unverified:
  - "Runtime liveness of any shared candidate component; deployed privacy; native source capture clocks."
unresolved:
  - "G1: exact Mining profile/callable/reported-economic-context interface unreturned by the shared owner."
  - "G2/G3/G4: native FCX/MP bytes, spans, identities and governed economic objects unqualified."
  - "G5/G6: private route/client/mount not on main; source custody with incumbents."
next_actions:
  - "T04a PR #7950 at head 94e74dd8 is DRAFT pending the Opus R3 READ_ONLY red-team (commissioned against that exact head). On ACCEPT: copy the report into research/mining/m1_integration_program/reviews/, gh pr ready 7950, add merge-on-green, watch at 600s, merge on concluded green (excluded reds: ci-authority/codex/merge-queue-pilot, Workers Builds: macro), verify on origin/main. On REJECT the SEAT repairs #7950 directly - the fabric has had three rounds."
  - "T03 (min_t03_economic_inputs, args pre-minted) is gated on T04a MERGING, not merely delivering: its preflight requires engine/market_ontology/mining_theme_research.py on origin/main, and it appends to the same mining-economic-dossier CI block. Retarget its engine off glm-codex (collapsed 3/3 on 09-24) to MiniMax-M3 before dispatch."
  - "T02 (min_t02_witness_profiles, args pre-minted) is gated on #7905, which seat 251f88c8 holds DRAFT under its own Opus R7 audit. Do NOT poll or re-arm watchers on it - it is another seat's PR; dispatch T02 when its content is on main."
  - "Shared-owner answer to the T06 mount/entry questions (#7870 comment 5811889498) gates T06; never re-ask."
  - "Then T04b integrated -> T07, each with an Opus red-team under the freeze-then-repair law; hold T05/T06/T08 for the shared route/mount on main and G2 admission."
  - "Operator items (surfaced, not actionable by the seat): mini2 WAN routing fix (needs mini2 sudo - a default route via bridge0 shadows the real gateway, so every lane there is REFUSED before start); mini2 MiniMax provisioning; mini2 keychain unlock for cursor-agent."
do_not_redo:
  - "R-MIN-31 + R-MIN-32 are tabled: an exact per-case truth table is required for every Mining composition task, and a frozen probe whose premise a fixture refutes is AMENDED in the open with intent preserved and assertions strengthened - never satisfied by fabricating module output."
  - "Do not re-measure financial_packets by looking for a top-level key in the fixture JSON: tests/mining_casebook.py SYNTHESISES that field from fixture['economics']. That measurement error cost one wrong ruling."
  - "Never re-ACK #7795 (pickup = comment 5811520293); never repeat 5809893850 on #7870."
  - "Never put implementation on #7795; never edit #7870's branch or any file it owns."
  - "T01' (#7932) is accepted work: do not rebuild the casebook, the binding validator or the CI job; extend them by appending (later Mining PRs append suites/paths to the ONE mining-economic-dossier block)."
  - "Never statically import a #7870-only module (engine.theme_graph.curation_assertion): tests/test_first_party_import_names.py reds ci-pack-5 on it — string-import through importlib.import_module inside try/except ImportError (R-MIN-29)."
danger_areas:
  - "legacy-jobs.yml / test_ci_pack.py are contested by many open PRs - append at END, rebase before push."
  - "A lane returning STATUS: PASS with tests it wrote itself is not proof; the Opus red-team + frozen probes are."
prs: [7795, 7921, 7922, 7932, 7944, 7950]
decisions: []
discoveries: []
---

# Mining M1 integration — seat checkpoint 2026-09-24

Pickup by deliberate Chairman delivery; Stage A reconciliation complete; Stage B synthetic units admitted
under addendum IR-06. This file is rewritten at every wave boundary.
