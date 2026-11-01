---
workstream: "WS:MARKET-OS"
session: "codex/01a128b5-e26b-7b12-94b5-231bfe0b8036"
model: codex
ended_because: ci_handoff
mission: >-
  Preserve Git ancestry required by F04 native private-intelligence revision
  validation, then continue actual API and Terminal delivery in the original root.
state_before: >-
  The original GMI publication was accepted, but installed depth-one update
  acquisition severed its revision from later installed HEAD. Native Git ancestry
  refused the pair despite both commit objects being present. Existing-store
  repair remains separate from preventing future truncation.
changed:
  - path: app/deploy/update.sh
    what: "Remove depth-one fetch while preserving locks, strict-mode failure, reset guards and service policy."
  - path: app/deploy/bootstrap_repo.sh
    what: "Preserve connected history on ordinary fetch; use a connected single-branch fresh clone with existing deploy-key authentication."
  - path: app/deploy/setup.sh
    what: "Align the authenticated bootstrap recipe and description with connected main history."
  - path: tests/test_deploy_git_history.py
    what: "Exercise real local Git acquisition, later updates, refusal and historical-object preservation; pin selected-branch behavior with remote defaults main, unselected and unborn without requiring an advisory remote HEAD alias."
  - path: .github/ci/legacy-jobs.yml
    what: "Use one exclusive deploy-git-history code job for its three deploy inputs and test; preserve all original job definitions, including self-heal and existing private-bootstrap coverage."
  - path: tests/test_ci_pack.py
    what: "Register the new curated job in the existing exact-set guard without changing packing ceilings."
verified:
  - claim: "Installed ancestry refusal and canonical ancestry disagree at the observed source pair."
    command: "Original read-only Git v4 exec48214; exact GitHub compare a13962ee...82c29a6a; later inventory exec13689 and exact a13962ee...ff11a33f comparison"
    result: >-
      Installed merge-base returned1 with shallow=true. Canonical comparisons
      establish a139 as ancestor, respectively24 and30 commits ahead. Root
      f217d5b2 and109a9b63 receipts retain complete observed streams and scope;
      this does not establish the cause or termination of earlier HTTP524.
  - claim: "The source repair has meaningful red-to-green regression evidence."
    command: "python3 -m pytest tests/test_deploy_git_history.py tests/test_deploy_bootstrap_private.py tests/test_deploy_update_self_heal.py -q; targeted reruns after review; pytest against pristine c754 source fixture"
    result: >-
      Initial integrated suites297pass; reviewed history/bootstrap34pass; last
      protected-membership test correction17pass. Pristine depth-one source
      yielded10fail/7pass, including actual disconnected ancestry. Tests execute
      acquisition in temporary local repositories, never the production updater.
      Git-input checks are not full native application acceptance.
  - claim: "The original candidate enrollment was checked before hosted CI exposed its packing regression."
    command: "load_legacy_jobs, infer_job_scopes and select_jobs against actual .github/ci/legacy-jobs.yml; bash -n on three scripts; git diff --check"
    result: >-
      Historical52002125 had290 logical jobs as c754 protected base; only existing
      biocatalyst-deploy-integration definition changes. All six relevant paths
      select it. Three shell syntax checks and whitespace validation pass.
  - claim: "Original hosted CI identified two candidate test/enrollment defects; the local clone assertion repair passes."
    command: "Original run38337802132 contract-delta115101754893, pack0/115102694176 and pack7/115102694272 logs; python3 -m pytest tests/test_deploy_git_history.py -q"
    result: >-
      Hosted tested merge3ba873064 of52002125 into9977280d exceeded the unchanged
      build_free_content packing weight5600 with5602 versus base5598. Pack7
      had1fail/296pass solely because the connected single-branch clone lacked
      optional origin/HEAD. Its fixture already pinned remote HEAD to main;
      a default-master explanation is superseded. The revised selected-ref,
      exact-refspec, tip and ancestry assertions pass19cases locally in74.19s.
      The earlier290job enrollment evidence is historical, not acceptance of
      the revised291job design or its current CI.
  - claim: "The revised enrollment preserves all existing jobs and the new resource flags compose with the retained graph fixture."
    command: "Retained enrollment-proof.json; curated exact-set guard; parent test_resource_graph_composition.py; test_owned_settlement.py"
    result: >-
      All290 base job definitions are conserved and deploy-git-history is the
      sole new job. The c754 and997 manifests have identical Git blob334d4d6a.
      Four positive inputs select it and three ordinary probes do not; exact-set
      guard1pass. Changed resource/graph composition1pass49.09s on local Git2.46.1
      removes30cuts under configured FSIZE while preserving HEAD, both indices
      and a persistent reader. It adds pack/idx despite zero new object IDs.
      Existing supervisor tests3pass21.39s prove local bounded capture and lock
      retention through natural, residual-child and timeout settlement. These
      are local fixtures, not Linux installation or production admission.
  - claim: "Local sparse closure and ordinary-code packing checks passed before hosted tracked-inventory evidence exposed a missing declaration."
    command: "python3 -u -m pytest tests/test_ci_pack.py -vv -k 'curated_exclusive_scopes_cover_their_own_import_closure or exclusive_curation_narrows_ordinary_code_prs'"
    result: >-
      Original resumed local exec21350 completed naturally at04:38:57UTC with
      2pass/166deselected in1259.24s; all four source/runner pins stayed identical.
      Log17a89fa46f48 retains both actual pass records within that sparse local
      scope. Later c4 hosted tracked inventory exposed site/index.html, which
      plain sparse existence omitted; the earlier closure PASS does not discharge
      that introduced finding. Original local packing evidence remains scoped.
  - claim: "The next same-carrier correction adds the single conservative tracked fixture-leaf dependency."
    command: "Original c4 CI38348708047 contract-delta115135959478 log; retained site-native-inventory-proof.json and site-enrollment-proof.json"
    result: >-
      Hosted tested merge76e8b7a0 on21652b3a reports only one introduced miss:
      deploy-git-history reaches site/index.html. The suite uses that literal in
      synthetic temporary repositories; conservative exact-tree analysis still
      owns the tracked leaf. Add only that exact path, preserving the previous
      four inputs, all290 other definitions, commands, test sources, weights and
      unchanged ceilings. Native tracked inventory of c4 reproduces the old miss
      and checks the corrected five-file closure. Exact site/index.html matches
      none of the three ordinary packing probes; retained c4 hosted rows are
      5795/5598/5558 weight and10packs, not next-head CI acceptance.

unverified:
  - claim: "This prevention change is released and installed."
    what_would_verify: "Exact current candidate checks, independent review, protected merge and actual next-invocation updater bytes."
  - claim: "The existing production shallow graph is repaired and F04 works live."
    what_would_verify: "Separately reviewed bounded additive operation with real resource/writer admission and retained readers, then fresh native, authenticated API and Terminal proof."
unresolved:
  - "Original additive91208 and resource46040 returns are accepted within their recorded bounded scopes. Resource root9695faf8 binds delivered code/report and changed local composition; worker12PASS Linux2.43 remains reported scope. Local settlement supplemente30ca0ef is separate. Aggregate storage, exact Linux application and live writer/resource admission remain open."
  - "Original9060 was visibly disarmed under comment6138485051 and same-branch c4af33b6 published04:54UTC. Current c4 remains unarmed/merge-blocked; its hosted tracked-closure red is retained. Finish only the exact site/index.html declaration correction and same-carrier publication, then current-head natural CI and executable arming/freshness. No merge-blocked removal, oldhead green reuse or release bypass."
  - "Audit20 reports no own active Macro Git maintenance reservation, not global writer absence. Existing destructive store exchange/history-expiry hold remains."
  - "Original Terminal944 awaits lawful shared CI repair through existing955/E20 owners. Preserve B/J1 and shared-host custody."
next_actions:
  - "Finish exact-source review and protected CI/release for this prevention patch, then qualify installed updater before repairing the existing graph."
  - "Complete aggregate receiver bounds and exact installed applicability for the accepted resource/graph mechanisms; coordinate the existing updater lock and other writers before any live additive operation."
  - "Keep original accepted publication immutable; verify actual native/private API and Terminal consumer only after required runtime gates."
do_not_redo:
  - "Do not reuse merged8842, adopt open7992 disk-maintenance work, or infer permission for destructive Git-store replacement."
  - "Do not treat this prevention patch as conversion of an existing shallow checkout or proof of native application/API acceptance."
  - "Preserve original Fabric runs, refusals and unknown HTTP/tablet effects; no replay, duplicate worker or duplicate CI observer."
danger_areas:
  - "Old depth-one cron can re-truncate a repaired graph unless accepted prevention bytes are installed first."
  - "Finite depth bounds commits, not bytes. Current free-space totals and process silence are not resource or writer admission."
prs:
  - "https://github.com/mastermindx-market-intelligence/macro/pull/9060"
---

# F04 Git-history prevention

This is a scoped source checkpoint in the original delivery chain, not F04 completion.
Original carrier: [Macro6819](https://github.com/mastermindx-market-intelligence/macro/issues/6819#issuecomment-6112033805).

Detailed original receipts, artifact manifests and review outcomes remain under
`/Volumes/Mastermind/evidence/marketontology-fabric-repair-01a128b5/f04-private-adoption/runtime-install/post-adoption-corrected-preparation-v1/`.
The `updater-ancestry-repair` directory binds original worker40455, delivered bytes,
parent corrections and actual test logs. `additive-history-offline-proof` retains
original91208. Fresh canonical returns supersede historical observations without
restamping them. No alternate lifecycle or authority store is introduced.
