---
key: LANE-HOST-ELIGIBILITY-DOES-NOT-MEASURE-GIT-EGRESS
claim: >
  The agent-pool host eligibility scorer (`ext/host_pick.py`) rates `roles`, `excluded`,
  `fresh`, `reachable` (SSH), `window`, `load`, `lane-ceiling`, `disk` and `tools` — and
  never whether the host can reach GitHub. A host can therefore rank FIRST while being
  structurally unable to run any lane that must fetch a carrier branch. Measured
  2026-09-24: `mini2` was the top ELIGIBLE host for every mode
  (`score=0.9479 load=1.25 lane-ceiling=0<2 reachable=PASS tools=PASS(all)`) while
  `git fetch origin <branch>` there failed with `Could not resolve host: github.com` under
  both a plain and a login shell with no proxy configured — although `nslookup github.com`
  resolved to 140.82.114.4 and ICMP to 1.1.1.1 was 100% loss. Its last successful macro
  fetch was 2026-09-23T21:59, so this was a regression rather than its configuration.
  Separately, eligibility is not a promise that placement succeeds: `mb` returned
  `LEASE_OK pool=glm` and then failed transport with `SUPPORT_STALE_ACTIVE_REFUSED
  active=2` / `SCP_FAILED rc=75`, because it was at its 2-lane ceiling and refuses to
  refresh a stale executor surface while lanes are active.
falsifier: >
  `ext/host_pick.py` gaining a probe that fails a host on git/HTTPS egress (a `git
  ls-remote`, a `curl` to github.com, or an equivalent gate appearing in the eligibility
  row); or `ssh mini2 'git -C ~/lanes/repos/macro fetch -q origin main'` succeeding, which
  would end the specific outage without touching the structural gap; or `pool hosts <mode>`
  ceasing to print `reachable=PASS` for a host whose git egress is down.
so_what: >
  Three things change. (1) Treat a green eligibility row as NECESSARY, never SUFFICIENT,
  for a branch-carrying lane: probe egress directly with
  `ssh <host> 'git -C ~/lanes/repos/macro fetch -q origin <branch> && echo OK'` BEFORE
  placing the packet, because the picker will otherwise keep routing such work to the one
  host guaranteed to fail, and the failure lands after a lease is already held. (2) Lane
  capacity is far thinner than the host list suggests — of seven hosts, `m2` is the seat
  (`roles=FAIL(seat)`), `bm1`/`bmb` are `lanes-shadow`, `m1`'s window is frequently
  `CLOSED`, and `pc` is ssh-unreachable, leaving `mb` and `mini2`. One busy host halves
  fleet lane capacity, so a lane plan that assumes many hosts will stall. (3) `remote_sub.sh`
  requires a `REMOTE_CWD` that already exists and neither fetches the branch nor mints a
  worktree; the working recipe is
  `git -C ~/lanes/repos/macro fetch origin <branch> && git worktree add --detach ~/lanes/wt/<id> FETCH_HEAD`,
  run on a host you pinned yourself, since `auto` gives you no host to prepare in advance.
kind: landmine
verified_at: 2026-09-24
verified_by: >
  `pool plan --class execute --need 2` -> `grant_now=2 wait_est=0s` on bailian, minimax,
  grok, cursor, glm and go, so capacity was not the constraint. `pool hosts minimax|glm|cursor`
  (POSITIONAL mode; `--mode` prints only an argparse usage string and a bare `pool hosts`
  dies with `line 42: 1: mode`) showed exactly `mb` and `mini2` ELIGIBLE. A worktree was
  successfully minted on `mb` at `c4bc7a4ce1` via
  `git -C ~/lanes/repos/macro fetch origin claude/consumer-cyclical-v1-lead` +
  `git worktree add --detach ~/lanes/wt/cc-v1-review FETCH_HEAD`, and
  `pool remote mb glm <packet> <cwd>` logged `LEASE_OK pool=glm` then
  `SUPPORT_STALE_ACTIVE_REFUSED active=2` / `SCP_FAILED rc=75`. The same worktree recipe on
  `mini2` failed at the fetch with `Could not resolve host: github.com`; `bash -lc` showed
  `HTTPS_PROXY`/`https_proxy`/`ALL_PROXY` all empty.
scope: [macro, mastermind]
confidence: verified
---

## Detail

The gap is that "reachable" means one thing to the scorer (SSH from the seat) and another
thing to the work (HTTPS to GitHub). Both are network reachability, so the row reads as
though it covers the question it does not cover — which is why a host with no egress can
sit at the top of the table with an unbroken column of `PASS`.

The honest sequencing lesson from the same session is separate and worth stating, because
it cost more than the outage did. The seat first reported to its commissioning authority
that delegation was unavailable from this host. That conclusion came from `pool hosts
--mode <x>`, which errors on argument parsing and prints a usage string — the seat read
the usage string's mode list as a finding about the fleet and never saw a host table at
all. Capacity had been available the whole time. **A null result from an instrument that
never ran is not evidence**; positive-control the instrument before reporting its silence.
Sibling record: DSC:A-UNIVERSAL-FALLBACK-BRANCH-IS-INVISIBLE-TO-A-VALUE-ONLY-SUITE.
