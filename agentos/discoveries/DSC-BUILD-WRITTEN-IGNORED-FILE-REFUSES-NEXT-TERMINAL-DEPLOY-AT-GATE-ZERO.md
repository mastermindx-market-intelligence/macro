---
key: BUILD-WRITTEN-IGNORED-FILE-REFUSES-NEXT-TERMINAL-DEPLOY-AT-GATE-ZERO
claim: >
  A Terminal build step that writes a git-ignored or untracked file into the live checkout
  /opt/terminal/terminal, with no exact release-preflight allowance for that path, does not
  break its own deploy. It breaks the NEXT one. Gate 0 in ops/terminal-build.sh audits the
  OUTGOING live checkout before fetch, so the release that adds the step passes (the file
  does not exist yet). Every later release then finds an IGNORED_IMPLEMENTATION_CANDIDATE,
  returns UNKNOWN_STOP and is refused with "recovery finding is not CANONICAL_HEAD_MISMATCH",
  whatever that later release contains. Merging the missing allowance does not fix it by
  itself either. Gate 0 selects its preflight script, policy and audit package from the
  executing script's own ops/ directory or the deployed /opt/terminal/.gitsrc/ops
  (`select_preflight_artifacts 0 "$AUTHORING_OPS_DIR" "$SRC/ops"`). Both are the outgoing
  generation, which lacks the allowance. The fix ships only through the documented
  first-adoption path: run ops/terminal-build.sh from one exact protected ops/ archive of
  the merged commit, and compare the logged policy digest before trusting CLEAN.
  Measured 2026-10-18: train 3 (#960, 98b9e664a) added the scripts/dist/gen_fundamental_scan.mjs
  install and deployed CLEAN; the next release (E07 #954, 3816d3926) was refused at 17:07Z
  with exactly that one finding.
falsifier: >
  Any of these would disprove it:
  (1) a normal deploy after a release that installs a new ignored path with no allowance,
  whose gate 0 logs `source preflight CLEAN` while the file is present;
  (2) a normal deploy run from /opt/terminal/terminal-build.sh after the allowance merged
  but before first adoption, whose `preflight bundle selected:` line carries the NEW
  policy_digest, which would show gate 0 reads the incoming policy.
  Check with `grep -h -E 'preflight bundle selected|source preflight CLEAN|recovery finding'
  /opt/terminal/deploy-*.log` and the receipts in
  /var/lib/mastermind-terminal/release-preflight/. Note that the E07 refusal's bundle line
  carries policy_digest=1f2e1bdc..., master's pre-fix policy, not the fix's 0d0ec2da....
so_what: >
  Three consequences for future work.
  First, any PR that makes terminal-build.sh or the nightly write a new ignored/untracked
  path into the live checkout must ship the exact allowance in the SAME PR.
  test_every_bundle_the_build_installs_has_an_exact_preflight_allowance
  (tests/test_terminal_release_preflight.py) now enforces this for scripts/dist bundles
  only; any other path still needs a person to think of it.
  Second, when a deploy is refused at gate 0 with an IGNORED_IMPLEMENTATION_CANDIDATE, look
  at what the PREVIOUS release installed, not at the release being refused. The refused
  release is usually innocent.
  Third, a change to the preflight policy, script or audit package cannot reach production
  through a normal deploy, because the outgoing generation judges it. Plan the
  first-adoption run, and its digest comparison, as part of that PR's release.
kind: landmine
verified_at: 2026-10-18
verified_by: >
  the Terminal VPS (address in the ops runbook):
  - /opt/terminal/deploy-train3.log logs `source preflight CLEAN accepted=9f26d3a00...`;
  - /opt/terminal/deploy-e07.log is two lines: the bundle line with
    policy_digest=1f2e1bdcc9b72561afe15a5cd79ed6550162498a43f3b2427da5e0e64d6123d5, then
    `recovery finding is not CANONICAL_HEAD_MISMATCH`;
  - the receipt
    /var/lib/mastermind-terminal/release-preflight/20261018T170759Z-98b9e664a0a3387a72f7bf360f5159235c1d8eb6-70ca556f2871e3d7b23b51d27f7371060f15eedda5095c9a7fc761fc6deb220d.json
    is UNKNOWN_STOP with one finding, IGNORED_IMPLEMENTATION_CANDIDATE terminal-app
    scripts/dist/gen_fundamental_scan.mjs.
  Code at master 3816d3926:
  - the bundle install is at ops/terminal-build.sh:1299-1308;
  - bundle selection is at ops/terminal-build.sh:40 and :1056;
  - first adoption is described at ops/TERMINAL_RELEASE_PREFLIGHT.md:54 and :80.
  Fixed in mastermindx-market-intelligence/mastermind-terminal#1053: a test that fails
  against master's policy, plus a read-only dry run of the new policy against the live
  checkout that was CLEAN with digest 0d0ec2da....
  First adoption: /opt/terminal/deploy-chart-context-20261018-e1c66d0b137b-protected-ops.log
  carries the bundle line with policy_digest=0d0ec2da..., `source preflight CLEAN
  accepted=98b9e664a...`, and `DONE — live = origin/master @ e1c66d0b137b`. The live
  wire marker read e1c66d0b1 afterwards.
scope:
  - mastermind-terminal
  - ops/terminal-build.sh
  - ops/terminal_source_audit.production.json
  - any build or nightly step that writes into /opt/terminal/terminal
confidence: verified
---

## Why it hides

The failure is displaced by one release, so neither diff shows a cause:

- The PR that adds the install step deploys CLEAN.
- The PR that gets refused touched nothing in `ops/`.

The refusal message is about recovery: "recovery finding is not CANONICAL_HEAD_MISMATCH". It says nothing about allowances. The useful line is in the receipt, not the log.

Related: `DSC:PYCACHE-RESIDUE-ABORTS-TERMINAL-DEPLOY-AT-GATE-ZERO` is the same gate refusing on derived state. That record also explains why custody (`trusted_stat`), not the digest, is the security boundary of the selected bundle.

## How first adoption was run

The release followed `ops/TERMINAL_RELEASE_PREFLIGHT.md` ("For first adoption…"):

1. `git -c tar.umask=0022 archive <merged sha> ops` was extracted with `--no-same-owner` into a fresh root-owned `mktemp -d /root/terminal-adopt.XXXXXX`.
2. Before launch, the copy was checked for root ownership, no group or other write, no symlinks, and only `.py` files in `terminal_audit`. The policy digest and the preflight-script sha were compared with the merged commit.
3. The run was `<dir>/ops/terminal-build.sh --target-sha <sha>`.
4. Its `preflight bundle selected:` line had to carry the merged commit's `script_sha256` and `policy_digest` before CLEAN counted as evidence.

The script's self-install step installs from `$SRC/ops`, so every later deploy runs the merged generation from `/opt/terminal` as usual. The temp dir was removed once no process ran from it.
