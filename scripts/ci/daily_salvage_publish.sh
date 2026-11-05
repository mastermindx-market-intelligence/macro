#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job collect, original salvage publication; same original generation.
set -e
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
SAFE=$(python -m scripts.ci.chain_snapshot_salvage . 2>/dev/null) || SAFE=""
if [ -z "$SAFE" ]; then
  echo "no salvageable chain snapshots on disk"; exit 0
fi
echo "$SAFE" | while IFS= read -r f; do [ -n "$f" ] && git add -- "$f"; done
if git diff --cached --quiet; then
  echo "chain snapshots already committed — nothing to salvage"; exit 0
fi
SAVED=$(git diff --cached --name-only | tr '\n' ' ')
git commit -m "data: salvage unrecoverable cboe chain snapshots $(date -u +%F)" || exit 0
# Bare line-start print: a logger/indent would push "::" off column 0 and
# GitHub would drop the annotation (tests/test_gh_annotation_line_start.py).
printf '::warning title=chain-snapshot-salvage::%s\n' "collect was red so the night's data commit was skipped; salvaged the unbackfillable delayed-chain snapshots only: $SAVED"
if [ "${GITHUB_REPOSITORY:-}" = mastermindx-market-intelligence/macro ]; then
  umask 077
  native_code_root="${RUNNER_TEMP%/}/native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}"
  native_bootstrap="${RUNNER_TEMP%/}/native-publication-bootstrap-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}-${NATIVE_PUBLICATION_PUBLISHING_STEP}.sh"
  case "$(GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git ls-tree "$GITHUB_WORKFLOW_SHA" -- scripts/ci/native_publication_source.sh)" in
    100644*) : ;; *) exit 76 ;;
  esac
  (set -o noclobber; GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show "$GITHUB_WORKFLOW_SHA:scripts/ci/native_publication_source.sh" > "$native_bootstrap")
  . "$native_bootstrap"
  native_publication_prepare_source "$native_code_root" "$GITHUB_WORKFLOW_SHA"
  . "$native_code_root/scripts/ci/push_retry.sh"
else
  . "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
fi
PUSH_ALARM=420
push_retry_init "salvaged chain snapshots"
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
while push_attempt; do
  perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin main || true
  if perl -e 'alarm 420; exec @ARGV or die' -- git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    if push_do; then echo "pushed salvaged chain snapshots"; push_won; exit 0; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
printf '::warning title=chain-snapshot-salvage::%s\n' "could not push the salvaged chain snapshots after $PUSH_ATTEMPT attempts ($PUSH_STOP) — they exist only on this runner and the next checkout will delete them"
