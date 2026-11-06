---
workstream: WS:MARKET-OS
session: codex/01a128b5-e26b-7b12-94b5-231bfe0b8036; claude/ssd-f04-private-runtime-01a128b5-6341b87053fe5e35
model: codex
ended_because: ci_handoff
mission: Prepare the existing Macro API deployment boundary for GMI private Company Intelligence and Terminal F04; source checkpoint while the original CEO A mission continues.
state_before: The existing macro-api unit has no private issuer store boundary. GMI owns native producer/admission source in Macro8810; A owns the private consumer in Terminal944.
changed:
  - path: app/deploy/company-intelligence-private-roots.py
    what: Provision seven empty root-owned0700 directories through nofollow directory descriptors, refusing unsafe existing nodes without adoption or repair.
  - path: app/deploy/macro-api.service
    what: Add nonoptional read-only state/artifacts mounts and inaccessible publisher mount.
  - path: app/deploy/update.sh
    what: Invoke the same fixed-root provisioner before first API unit validation, including no-op updates; preserve existing guards.
  - path: app/deploy/api-setup.sh
    what: Invoke the same provisioner before fresh-install unit validation/install/start.
  - path: tests/test_company_intelligence_private_roots.py
    what: Exercise empty creation/idempotence, every unsafe private slot, higher symlink/writable ancestors, foreign UID/GID, creation-time replacement, fixed CLI and both actual guarded shell fragments.
  - path: .github/ci/legacy-jobs.yml
    what: Enroll the new suite in one code-gated job scoped to the four deployment inputs and its test.
verified:
  - claim: The helper and deployment ordering pass discriminating isolated tests.
    command: python3 -m pytest -q tests/test_company_intelligence_private_roots.py
    result: 43 passed in2.69s; one pre-existing pytest temporary-directory cleanup warning. No production paths or services modified.
  - claim: Existing deployment behavior remains covered.
    command: python3 -m pytest -q tests/test_deploy_update_self_heal.py
    result: 263 passed in19.15s; one pre-existing pytest temporary-directory cleanup warning. Bash syntax is also covered by the focused suite.
  - claim: Independent source review accepts the repaired five-file increment.
    command: Sol coordinator read-only review of exact source hashes and additive-block removal against c50af4eb04217376dbed228bddd1b632b06bf4ae
    result: PASS; review receipt2ac2334b2ed6cc9c8b61507b58952c1fc207d6a286c1f30f74408a11fa8aa1e1. Removing only added provisioner blocks restores both shell files exactly to base.
  - claim: Protected main movement introduces no overlap with the five owned implementation/test paths.
    command: git fetch origin main; git diff --name-only c50af4eb04217376dbed228bddd1b632b06bf4ae..b79cd12239e576b1a6364167d03dc6e283c9b41d -- app/deploy/update.sh app/deploy/api-setup.sh app/deploy/macro-api.service app/deploy/company-intelligence-private-roots.py tests/test_company_intelligence_private_roots.py
    result: No path changes.
  - claim: The exact GMI runtime layout agrees with the repaired source.
    command: gh api contents at d55a1b97d6a111fbc9c0b646d88c8444de9aa4e1; base64 decode and SHA256; compare PRIVATE_RUNTIME_LAYOUT.md with helper and unit
    result: Layout SHA256 b3f14a3a8ce1882bdcd3d46f63cf9c9b425c6a319f915496ae1c5753460eab0a matched; state/artifacts readonly and publisher inaccessible, fixed root and empty provisioning agree.
  - claim: The inherited calendar-scope CI blocker has a protected repair and a successful natural main baseline.
    command: gh api repos/mastermindx-market-intelligence/macro/actions/runs/38187866979; gh api repos/mastermindx-market-intelligence/macro/actions/jobs/114614031931; canonical integration_baseline_state
    result: PR8870 merged as de0c202a016502ce521db66a70e5905b76e0c9c2; exact push baseline and job concluded success at 2026-10-12T00:36Z. Receipt SHA256 16ff9bb2f48352d94ecb169dc4a51a2d11e1b8cfbc279001bba01537885ccce4. No watcher was launched; one permitted terminal snapshot supplied the result.
  - claim: The normal main refresh preserves this PR's provisioning boundary and the complete protected updater and CI registry.
    command: git merge --no-ff --no-commit 1f25c4abd1eae583d4166c7b970e70aabea95377; compare complete updater after removing only the original provisioning block, registry after removing only the private-runtime job, and inventory after removing only its item with git show at that main revision
    result: All three complete comparisons match protected main byte-for-byte. Four runtime files are unchanged; update.sh incorporates only protected PR8864 W2C lane-freeze behavior and the unchanged original guard. Its new SHA256 is 91e8db62d40670b0bb1f710be5481b39644a22474ae580411b33d8c3d6c77cc6. Eight PR-owned paths remain; no conflict or sibling rewrite.
  - claim: The affected checks pass on the integrated updater and current protected CI definitions.
    command: python3 -m pytest tests/test_company_intelligence_private_roots.py tests/test_deploy_update_self_heal.py tests/test_market_memory_experience_deploy.py tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared -q
    result: 333 passed in 67.89s. Receipt SHA256 471544b1560aca2fad9850bbca06f45485d3adfb9e855b347ff9bdbf940372e6 binds prepared tree 600342ec7bd186802948adab969bfba096fe68d5; this later continuity-only handoff update changes the final tree, not the tested source. Prior 306-test results above remain historical.
unverified:
  - claim: The private directory boundary is installed and enforced in the running API namespace.
    what_would_verify: Protected source landing followed by existing updater/setup, exact installed helper/unit bytes, API process generation, read-only state/artifacts and inaccessible publisher probes under the actual service namespace.
  - claim: The entitled user can read an admitted private fact through the product.
    what_would_verify: GMI protected producer/current-generation release and admission, exact permitted publication, Terminal944 shared-host integration and the actual authenticated positive/negative browser journey.
unresolved:
  - The source is independently reviewed and GMI layout is pinned; required CI, release and runtime proof remain open.
  - Original Fabric operation mo-a-f04-runtime-install-01a128b5-v1 was accepted on the corrected derivative after independent review and verified GMI pin; its rejected raw draft remains preserved. Usage/served model/cost remain unknown. Later review of the normal main refresh has its own bounded operation and does not replace the original worker.
  - The repaired helper creates no current.json, generation record, artifact, retained source or journal; directory existence conveys no publication or serving authority.
next_actions:
  - Requalify the released GMI source before installation; preserve GMI8810 source custody and its staged/adopted distinction.
  - Complete exact-head CI and normal review/release on this carrier; no automatic production readiness claim.
  - Coordinate one normal installation/adoption with the existing updater owner, then verify the actual process namespace and the native admitted-data path.
do_not_redo:
  - Do not retry or replace the original Fabric worker, apply its malformed hunks, or restore its obsolete state-hidden layout.
  - Do not chmod/chown unsafe existing directories, follow symlinks, fabricate source or current pointers, or reuse Research R2 authority.
  - Do not relax W2C, Options, Market Memory or BioCatalyst guards, start their writers manually, or use a second updater.
  - Do not treat the separately completed complimentary account grant or isolated Terminal fixtures as private production proof.
danger_areas:
  - The privileged producer runs outside the API namespace; API uid0 alone is not read-only proof.
  - Nonoptional mounts require safe directories before restart. An unsafe existing layout must stop deployment without normalizing it.
  - Shared Terminal hosts remain separately coordinated with the E20 incumbent; this source does not edit them.
prs: [8842, 8810]
---

The agreed root is `/var/lib/macro-company-intelligence`. `state/current.json` and
`state/generations/<sha256>.json` are API-readable metadata; `artifacts/` is the
immutable private object store. Both are read-only in the API namespace.
`publisher/source/<sha256>.html` and `publisher/operations/<id>.json` belong to
the privileged native producer and are inaccessible in that namespace. The
provisioner creates directories only; GMI owns all file0600 and publication checks.

The existing updater and first-install script invoke the fixed helper with their
existing API Python. The CLI has no path override and requires effective UID0.
The internal descriptor seam exists for isolated tests, not as a deployed bypass.
All pre-existing private nodes are checked before creating a missing sibling.

Raw worker output, two independent RED security probes, repaired source review,
and test logs are retained under
`/Volumes/Mastermind/evidence/marketontology-fabric-repair-01a128b5/f04-private-adoption/runtime-install/`.
Original worker raw SHA256: `6f0dc2085216385578c81ab7c33ee5a85f9477b1fff3af7c6ef9b260fb161648`.

The current refresh follows PR8870's calendar-scope repair. Protected main
`1f25c4abd1eae583d4166c7b970e70aabea95377` includes PR8864's W2C lane freeze;
the updater is therefore deliberately not described as byte-identical to the
previous PR8842 head. Its complete protected behavior is preserved, with only
this PR's original empty-directory provisioning guard added. A frozen W2C lane
and the private directory boundary remain independent controls. No deployment,
directory creation, service restart, STAGE, adoption or publication occurred.

Installation sequencing remains: protected GMI8803 then8810 and independent
runtime8842 release; existing updater installs the released PROPOSED owner with
safe empty roots; GMI executes its exact STAGE intent; actual observed members
remain unadmitted until protected PRODUCED adoption and normal updater adoption;
GMI then issues a new adoption-bound PROMOTE intent. The resulting API namespace
and authenticated Terminal workflow still require live verification.

MISSION_COMPLETE: false. This handoff records source continuity, not session termination.
