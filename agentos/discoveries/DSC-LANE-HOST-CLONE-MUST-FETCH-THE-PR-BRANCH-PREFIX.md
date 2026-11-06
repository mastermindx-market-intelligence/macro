---
key: LANE-HOST-CLONE-MUST-FETCH-THE-PR-BRANCH-PREFIX
claim: >
  The shared external-lane clone on ubuntu1 (`~/lanes/repos/macro`, blobless) was a
  SINGLE-BRANCH clone whose only fetch refspec was `+refs/heads/main:refs/remotes/origin/main`,
  so the lane runtime's existing-PR mode - which checks out `origin/<branch>` after a
  fetch - failed every non-main lane with `fatal: invalid reference: origin/sol/...`
  before any work started, while the same packet launched cleanly on the Mac hosts whose
  clones fetch everything. Fixed 2026-10-05 by adding `+refs/heads/sol/*:refs/remotes/origin/sol/*`
  and `+refs/heads/claude/*:refs/remotes/origin/claude/*` to `remote.origin.fetch` on that host.
falsifier: >
  `ssh ubuntu1 git -C ~/lanes/repos/macro config --get-all remote.origin.fetch` printing
  only the `main` refspec, or an existing-PR lane on a `sol/*` or `claude/*` branch failing
  there with `invalid reference` after this date.
so_what: >
  An `invalid reference: origin/<branch>` refusal from a lane is HOST CLONE CONFIGURATION,
  never a property of the pull request: check the host's fetch refspecs before relaunching,
  retrying, or opening a second lane. Any new lane host must be provisioned with refspecs
  covering every branch prefix the fleet mints (`sol/*`, `claude/*`), not just `main`.
kind: runtime
verified_at: 2026-10-05
verified_by: >
  Research Vault seat 0e657eec: lane `rv_f4_lineage_u1` r1 on ubuntu1 died at checkout of
  `origin/sol/marketdesk-auth-health-f4-r2-20261005` with `invalid reference`; after the
  refspec change the relaunched lane checked out the branch, pushed
  4df909395c2e -> 74bc480e1d6a on PR #8472, and `git config --get-all remote.origin.fetch`
  on the host now prints the three refspecs.
scope: [macro, fleet-lane-hosts]
confidence: verified
---

## Detail

The blobless clone was minted single-branch to keep the host small, and nothing in the
launcher checks that the branch a packet names is fetchable on the host it targets. The
failure is silent at launch time: the launcher reports a lease and a remote pid, and the
lane's stdout carries only git's `invalid reference` line. Treat it as a provisioning
gate for every host added to `hosts.json`.
