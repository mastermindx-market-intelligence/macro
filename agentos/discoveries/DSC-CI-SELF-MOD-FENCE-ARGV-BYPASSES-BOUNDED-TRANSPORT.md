---
key: CI-SELF-MOD-FENCE-ARGV-BYPASSES-BOUNDED-TRANSPORT
claim: >
  A file-backed upstream list does not close execve risk if a terminal policy
  invocation rematerializes that list or another unbounded input in argv: at FF
  PR 5898 head 47d3b4b49e7191e72576ebc6e7495748ab1c8164, fences run 32546500471
  expanded both changed paths and full commit-message text into
  check_self_mod_fence.py argv and died with E2BIG before Python started, while
  the semantic CI and the fence test suite were green. The fork live path
  retained the same unbounded transport shape. The live check has a THIRD copy
  outside .github/workflows/, the self-mod-fence job in the ci-pack manifest
  .github/ci/legacy-jobs.yml, which the #6223 repair missed: ci-pack run
  36360866211 (job 108742915933, PR #8006) died there the same way, because
  run_ci_pack's exact tested-tree deepening to depth 32 left origin/main..HEAD
  carrying ~372 KB of commit messages (mostly main's own squash commits; the
  PR's own messages were ~12 KB and pass the fence) as one argv string, past
  Linux's 131,072-byte MAX_ARG_STRLEN.
falsifier: >
  Re-read run 32546500471 and show that check_self_mod_fence.py started and
  emitted its own policy verdict before exit 126, or inspect the workflow bytes
  used by that run and show that both live self-mod paths passed only bounded
  file, stream, or digest handles rather than expanding the complete changed-file
  or commit-message populations into argv. For the packed copy, show that job
  108742915933 of run 36360866211 printed a fence verdict before exit 126.
so_what: >
  Treat DSC:CI-CHANGED-FILES-ENV-HAS-AN-EXECVE-CEILING as the general transport
  law, but audit every workflow that independently recomputes or forwards an
  unbounded population, and find the copies by the checker's name
  (check_self_mod_fence.py), not by directory: a sweep of .github/workflows/
  never sees the ci-pack manifest. Changed files stay in the canonical JSON file
  representation, complete commit-message text stays file-backed, only bounded
  handles cross argv or the environment, and both source wiring and real
  process-launch regressions must forbid restoration of either population. The
  packed copy's commit range is also not PR-scoped: a Loop-Authored line in a
  recent main commit inside the deepened window would attribute a human
  CI-authority PR as loop-authored (none in main's newest 5,000 commits on
  2026-09-28).
kind: landmine
verified_at: 2026-09-28
verified_by: >
  GitHub fences run 32546500471 at subject
  47d3b4b49e7191e72576ebc6e7495748ab1c8164 (self-mod live exit 126,
  "Argument list too long", before checker output); source inspection of both
  live paths in .github/workflows/fences.yml; and python3 -m pytest
  tests/test_self_mod_fence.py tests/test_fence_checkout_contract.py -q
  (retired argv raises errno E2BIG, both file-backed workflow paths launch,
  and all 73 tests pass). Packed copy: ci-pack run 36360866211 job
  108742915933 log "bash: line 51: .../python3: Argument list too long";
  python3 -m pytest tests/test_self_mod_fence.py -k "packed_tail or
  oversized_commit_range or only_by_handle" reproduces the same line-51 exit
  126 on the unrepaired step (7 failed, positive control passed) and passes
  8/8 once the step is file-backed; git log origin/main -n 5000
  --grep='^[[:space:]]*Loop-Authored:' returned nothing.
scope:
  - macro
  - ci-merge-control-plane
  - ".github/workflows/fences.yml"
  - ".github/ci/legacy-jobs.yml"
  - "scripts/check_self_mod_fence.py"
  - "scripts/run_ci_pack.py"
confidence: verified
---
