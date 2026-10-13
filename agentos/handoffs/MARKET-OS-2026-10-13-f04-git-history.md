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
    what: "Exercise real local Git acquisition, two later updates, unchanged tick, refusal and historical-object preservation."
  - path: .github/ci/legacy-jobs.yml
    what: "Enroll private-bootstrap and history suites in the existing deployment integration job; retain self-heal coverage."
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
  - claim: "The affected deployment job executes the tests and is selected by each relevant source/test path."
    command: "load_legacy_jobs, infer_job_scopes and select_jobs against actual .github/ci/legacy-jobs.yml; bash -n on three scripts; git diff --check"
    result: >-
      Same290 logical jobs as c754 protected base; only existing
      biocatalyst-deploy-integration definition changes. All six relevant paths
      select it. Three shell syntax checks and whitespace validation pass.
unverified:
  - claim: "This prevention change is released and installed."
    what_would_verify: "Exact current candidate checks, independent review, protected merge and actual next-invocation updater bytes."
  - claim: "The existing production shallow graph is repaired and F04 works live."
    what_would_verify: "Separately reviewed bounded additive operation with real resource/writer admission and retained readers, then fresh native, authenticated API and Terminal proof."
unresolved:
  - "Original additive experiment mo-a-f04-additive-git-floor-offline-v1/exec91208 remains pending at this source checkpoint; no live command follows from its commission."
  - "Audit20 reports no own active Macro Git maintenance reservation, not global writer absence. Existing destructive store exchange/history-expiry hold remains."
  - "Original Terminal944 awaits lawful shared CI repair through existing955/E20 owners. Preserve B/J1 and shared-host custody."
next_actions:
  - "Finish exact-source review and protected CI/release for this prevention patch, then qualify installed updater before repairing the existing graph."
  - "Consume original91208 artifacts, review finite-depth behavior and resource bounds, and coordinate the existing updater lock and other writers before any live additive operation."
  - "Keep original accepted publication immutable; verify actual native/private API and Terminal consumer only after required runtime gates."
do_not_redo:
  - "Do not reuse merged8842, adopt open7992 disk-maintenance work, or infer permission for destructive Git-store replacement."
  - "Do not treat this prevention patch as conversion of an existing shallow checkout or proof of native application/API acceptance."
  - "Preserve original Fabric runs, refusals and unknown HTTP/tablet effects; no replay, duplicate worker or duplicate CI observer."
danger_areas:
  - "Old depth-one cron can re-truncate a repaired graph unless accepted prevention bytes are installed first."
  - "Finite depth bounds commits, not bytes. Current free-space totals and process silence are not resource or writer admission."
prs: []
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
