#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# Existing Prophet Stage-shadow durability checkpoint; body preserved.
set -euo pipefail
. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"

EVENT_REF="${GITHUB_REF:-}"
SOURCE_BRANCH="$(git -C "$GITHUB_WORKSPACE" symbolic-ref --short -q HEAD || true)"
if [ "$EVENT_REF" != "refs/heads/main" ] \
  || [ "$SOURCE_BRANCH" != "main" ] \
  || [ -z "${ACCEPTED_PROPHET_SHA:-}" ]; then
  echo "::error title=Prophet Stage checkpoint source rejected::only an accepted main Prophet projection may advance the Stage-shadow ledger"
  exit 1
fi
if [ ! -f "${STAGE_DELTA_MANIFEST:-}" ]; then
  echo "::error title=Prophet Stage manifest missing::no readable closed-output delta was supplied"
  exit 1
fi
if [ ! -s "$STAGE_DELTA_MANIFEST" ]; then
  echo "Prophet Stage checkpoint: no accrual changes"
  exit 0
fi

git -C "$GITHUB_WORKSPACE" fetch origin \
  +refs/heads/main:refs/remotes/origin/main
PROPHET_AUTHORITY_PATHS=(data/prophet data/prophet_arena site/prophet)
if ! git -C "$GITHUB_WORKSPACE" merge-base --is-ancestor \
    "$ACCEPTED_PROPHET_SHA" origin/main \
  || ! git -C "$GITHUB_WORKSPACE" diff --quiet \
    "$ACCEPTED_PROPHET_SHA" origin/main -- \
    "${PROPHET_AUTHORITY_PATHS[@]}" \
  || ! git -C "$GITHUB_WORKSPACE" diff --quiet \
    "$ACCEPTED_PROPHET_SHA" origin/main -- data/prophet_stage_shadow; then
  echo "::error title=Prophet Stage checkpoint superseded::Prophet authority or Stage-shadow history advanced after the accepted source snapshot; preserving main"
  exit 1
fi

STAGE_CHECKPOINT_ROOT="$(mktemp -d "${RUNNER_TEMP}/prophet-stage-checkpoint.XXXXXX")"
STAGE_CHECKPOINT_DIR="${STAGE_CHECKPOINT_ROOT}/tree"
STAGE_CHECKPOINT_BRANCH="_prophet_stage_checkpoint_${GITHUB_RUN_ID}_${GITHUB_RUN_ATTEMPT:-1}"
cleanup_stage_checkpoint() {
  cd "$GITHUB_WORKSPACE"
  git worktree remove --force "$STAGE_CHECKPOINT_DIR" 2>/dev/null || true
  git branch -D "$STAGE_CHECKPOINT_BRANCH" 2>/dev/null || true
  rmdir "$STAGE_CHECKPOINT_ROOT" 2>/dev/null || true
}
trap cleanup_stage_checkpoint EXIT
git worktree add -b "$STAGE_CHECKPOINT_BRANCH" \
  "$STAGE_CHECKPOINT_DIR" origin/main
cd "$STAGE_CHECKPOINT_DIR"

while IFS=$'\t' read -r rel before_sha after_sha; do
  [ -n "$rel" ] || continue
  case "$rel" in
    data/prophet_stage_shadow/ledger.jsonl|\
    data/prophet_stage_shadow/revisions.jsonl|\
    data/prophet_stage_shadow/summary.json) ;;
    *)
      echo "::error title=Prophet Stage path rejected::$rel is outside the closed Stage-shadow output set"
      exit 1
      ;;
  esac
  if [ ! -f "$GITHUB_WORKSPACE/$rel" ] || [ -L "$GITHUB_WORKSPACE/$rel" ]; then
    echo "::error title=Prophet Stage output rejected::$rel is missing or symlinked; deletions are forbidden"
    exit 1
  fi
  current_after="$(python3 -c 'import hashlib,os,sys; p=sys.argv[1]; print(f"{os.stat(p).st_mode & 0o7777:04o}:"+hashlib.sha256(open(p,"rb").read()).hexdigest())' "$GITHUB_WORKSPACE/$rel")"
  if [ "$current_after" != "$after_sha" ]; then
    echo "::error title=Prophet Stage source changed::$rel changed after its validated projection; checkpoint withheld"
    exit 1
  fi
  if [ -L "$STAGE_CHECKPOINT_DIR/$rel" ]; then
    echo "::error title=Prophet Stage main symlink rejected::$rel"
    exit 1
  elif [ -f "$STAGE_CHECKPOINT_DIR/$rel" ]; then
    main_before="$(python3 -c 'import hashlib,os,sys; p=sys.argv[1]; print(f"{os.stat(p).st_mode & 0o7777:04o}:"+hashlib.sha256(open(p,"rb").read()).hexdigest())' "$STAGE_CHECKPOINT_DIR/$rel")"
  else
    main_before="MISSING"
  fi
  if [ "$main_before" != "$before_sha" ]; then
    echo "::error title=Prophet Stage same-path race::origin/main changed $rel; preserving its append-only history"
    exit 1
  fi
  mkdir -p "$(dirname "$rel")"
  cp -p "$GITHUB_WORKSPACE/$rel" "$rel"
  git add -- "$rel"
done < "$STAGE_DELTA_MANIFEST"

if git diff --cached --quiet; then
  echo "Prophet Stage checkpoint: no staged changes"
  exit 0
fi
push_staged_clean || exit 1
git commit -m "prophet-stage: durable nightly accrual $(date -u +%F)"
STAGE_CHECKPOINT_PARENT="$(git rev-parse HEAD^)"
PUSH_ALARM=120
PUSH_BUDGET_SECS=420
PUSH_MAX_ATTEMPTS=12
PUSH_MAIN_BRANCHES="$STAGE_CHECKPOINT_BRANCH"
push_retry_init "Prophet Stage-shadow durable checkpoint"
push_on_main_ok || exit 0
while push_attempt; do
  if ! push_fetch_main_for_rebase; then
    push_abort_rebase
    push_backoff
    continue
  fi
  if ! git merge-base --is-ancestor "$ACCEPTED_PROPHET_SHA" origin/main \
    || ! git diff --quiet "$ACCEPTED_PROPHET_SHA" origin/main -- \
      "${PROPHET_AUTHORITY_PATHS[@]}" \
    || ! git diff --quiet "$ACCEPTED_PROPHET_SHA" origin/main -- \
      data/prophet_stage_shadow; then
    echo "::error title=Prophet Stage authority race::Prophet inputs or Stage-shadow history advanced during publish; preserving main"
    exit 1
  fi
  same_path=""
  while IFS=$'\t' read -r rel _ _; do
    [ -n "$rel" ] || continue
    if ! git diff --quiet "$STAGE_CHECKPOINT_PARENT" origin/main -- "$rel"; then
      same_path="${same_path}${same_path:+, }${rel}"
    fi
  done < "$STAGE_DELTA_MANIFEST"
  if [ -n "$same_path" ]; then
    echo "::error title=Prophet Stage same-path race::origin/main advanced $same_path; no conflict override is allowed"
    exit 1
  fi
  if perl -e 'alarm 180; exec @ARGV or die' -- git rebase origin/main; then
    STAGE_CHECKPOINT_PARENT="$(git rev-parse HEAD^)"
    if push_do origin HEAD:main; then
      echo "pushed Prophet Stage-shadow checkpoint on attempt $PUSH_ATTEMPT"
      push_won
      exit 0
    fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::error title=Prophet Stage checkpoint NOT pushed::$PUSH_ATTEMPT attempts failed ($PUSH_STOP); the broad engine commit is fenced from these unaccepted bytes"
exit 1
