#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job capital_structure, original publishing step; native graph added in the SAME candidate.
set -e
if [ "${GITHUB_REPOSITORY:-}" = mastermindx-market-intelligence/macro ] && [ "${GITHUB_REF:-}" = refs/heads/main ]; then
  # Capture repository-owned execution bytes from the original protected
  # workflow SHA BEFORE rebase can replace files in the candidate tree.
  umask 077
  [[ "$GITHUB_WORKFLOW_SHA" =~ ^[0-9a-f]{40}$ ]]
  native_code_root="${RUNNER_TEMP%/}/native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}"
  mkdir -m 700 -- "$native_code_root"
  mkdir -p -- "$native_code_root/scripts/ci"
  GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show \
    "$GITHUB_WORKFLOW_SHA:scripts/ci/native_publication_source.sh" \
    > "$native_code_root/scripts/ci/native_publication_source.sh"
  case "$(GIT_NO_REPLACE_OBJECTS=1 git ls-tree "$GITHUB_WORKFLOW_SHA" -- scripts/ci/native_publication_source.sh)" in
    100644*) : ;; *) exit 76 ;;
  esac
  . "$native_code_root/scripts/ci/native_publication_source.sh"
  native_publication_capture_source "$native_code_root" "$GITHUB_WORKFLOW_SHA"
  . "$native_code_root/scripts/ci/push_retry.sh"
else
  . "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
fi
# Same best-effort policy as the market push: losing a race for refs/heads/main
# must not red the job. (Pre-split this loop doubled as a second chance at a
# lost market push, because both commits sat in one workspace. It does not any
# more — that commit lives in `collect`'s workspace, and `collect`'s own
# salvage push is what covers it. This loop publishes the generation only.)
PUSH_ALARM=420
push_retry_init "capital-structure generation"
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
while push_attempt; do
  # pre-sync collision sweep — see the market push above for the full rationale
  # (a mid-run commit on origin/main tracking a path this job wrote untracked).
  perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin main || true
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  # Whole-generation append-only fence (DEC:CS-V2-WHOLE-GENERATION-APPEND-ONLY-FENCE).
  # Two overlapping capital_structure jobs can each compile from the ledger they
  # checked out; `-X theirs` below then REPLACES origin/main's coherent CS
  # generation. Runs after fetch and before rebase so a proven drop of
  # source_manifest.jsonl withholds data/capital_structure and
  # site/capital-structure-data together — never one file, never merge=union.
  # Collect cannot host this fence: collect unstages those paths.
  if ! push_append_only_fence origin/main; then push_backoff; continue; fi
  if perl -e 'alarm 420; exec @ARGV or die' -- git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    if push_do; then
      echo "pushed capital-structure generation on attempt $PUSH_ATTEMPT"
      push_won
      exit 0
    fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::warning::could not push the capital-structure generation after $PUSH_ATTEMPT attempts ($PUSH_STOP) (non-fatal — the market data is already published; the next night recompiles)"
