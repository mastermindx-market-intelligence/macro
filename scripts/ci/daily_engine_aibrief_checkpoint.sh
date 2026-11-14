#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# New workflow-owned helper; the marker enrolls it in the existing DAG source
# resolver's whole-step script contract, not an assertion of prior deployment.
# The existing engine job's EARLY, JSON-only publication cut. It uses the
# same push_retry/main writer as the later broad commit, never partial pages.
# The render owner rebuilds standalone HTML and regional modals from accepted JSON.
set -euo pipefail

ROOT="${GITHUB_WORKSPACE:-}"
if [ -z "$ROOT" ] || [ ! -d "$ROOT/.git" ] || [ ! -d "${RUNNER_TEMP:-}" ]; then
  echo "::error title=AI Brief checkpoint environment::requires an Actions checkout and RUNNER_TEMP"
  exit 1
fi
. "$ROOT/scripts/ci/push_retry.sh"
if [[ "${GITHUB_REF:-}" != "refs/heads/main" ||
      ! "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ ||
      ! "${GITHUB_RUN_ATTEMPT:-1}" =~ ^[0-9]+$ ]]; then
  echo "::error title=AI Brief checkpoint authority::requires a main-branch Actions execution"
  exit 1
fi
SOURCE_HEAD="$(git -C "$ROOT" rev-parse HEAD)"
SOURCE_BRANCH="$(git -C "$ROOT" symbolic-ref --short -q HEAD || true)"
if [ "$SOURCE_BRANCH" != main ] || [ -z "${GITHUB_SHA:-}" ]; then
  echo "::error title=AI Brief checkpoint authority::not an authorized main checkout"
  exit 1
fi

# Guard the exact inputs/consumers as well as the narrow outputs. An unrelated
# writer can advance main, but a same-input/source change must never accept a
# narrative derived from a superseded source epoch.
FENCED=(
  data/regime/latest.json data/china_regime/latest.json data/hk_regime/latest.json
  data/commodity/latest.json data/forex/latest.json
  data/regime/master_brief.json data/regime/china_brief.json data/regime/btc_brief.json
  site/master_brief.json site/china_brief.json site/btc_brief.json
  engine/master_brain.py config.yml
)

git -C "$ROOT" fetch origin +refs/heads/main:refs/remotes/origin/main
if ! git -C "$ROOT" merge-base --is-ancestor "$SOURCE_HEAD" origin/main ||
   ! git -C "$ROOT" diff --quiet "$SOURCE_HEAD" origin/main -- "${FENCED[@]}"; then
  echo "::error title=AI Brief checkpoint epoch drift::source changed since this run's checkout; no older brief may overwrite it"
  exit 1
fi

TMP_ROOT="$(mktemp -d "$RUNNER_TEMP/aibrief-checkpoint.XXXXXX")"
BRIEF_MANIFEST="$TMP_ROOT/brief-manifest.tsv"
CHECKPOINT_DIR="$TMP_ROOT/tree"
CHECKPOINT_BRANCH="_aibrief_checkpoint_${GITHUB_RUN_ID}_${GITHUB_RUN_ATTEMPT:-1}"
WORKTREE_OWNED=false
cleanup_aibrief_checkpoint() {
  cd "$ROOT" || return
  if [ "$WORKTREE_OWNED" = true ]; then
    git worktree remove --force "$CHECKPOINT_DIR" 2>/dev/null || true
    git branch -D "$CHECKPOINT_BRANCH" 2>/dev/null || true
  fi
  rm -f "$BRIEF_MANIFEST"
  rmdir "$TMP_ROOT" 2>/dev/null || true
}
trap cleanup_aibrief_checkpoint EXIT

# No generated output is staged or published before the pair/freshness witness.
python3 "$ROOT/scripts/ci/aibrief_checkpoint_manifest.py" \
  --root "$ROOT" --source-head "$SOURCE_HEAD" --manifest "$BRIEF_MANIFEST"
if [ ! -s "$BRIEF_MANIFEST" ]; then
  echo "::notice title=AI Brief checkpoint::no newly generated healthy briefs; last-good published copy unchanged"
  exit 0
fi

if git -C "$ROOT" show-ref --verify --quiet "refs/heads/$CHECKPOINT_BRANCH"; then
  echo "::error title=AI Brief checkpoint retained carrier::prior branch exists; reconcile original attempt, never replace it"
  exit 1
fi
git -C "$ROOT" worktree add -b "$CHECKPOINT_BRANCH" "$CHECKPOINT_DIR" origin/main
WORKTREE_OWNED=true
cd "$CHECKPOINT_DIR"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"

# Only the closed manifest crosses into the clean worktree. The dirty engine
# worktree keeps all source/provenance ledgers and half-built site pages intact.
while IFS=$'\t' read -r rel wanted; do
  case "$rel" in
    data/regime/master_brief.json|data/regime/china_brief.json|data/regime/btc_brief.json|\
    site/master_brief.json|site/china_brief.json|site/btc_brief.json) ;;
    *) echo "::error title=AI Brief checkpoint path::unowned path $rel"; exit 1 ;;
  esac
  src="$ROOT/$rel"
  [ -f "$src" ] && [ ! -L "$src" ] && [ ! -L "$CHECKPOINT_DIR/$rel" ] || {
    echo "::error title=AI Brief checkpoint source::missing or symlinked $rel"; exit 1;
  }
  actual="$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$src")"
  if [ "$actual" != "$wanted" ]; then
    echo "::error title=AI Brief checkpoint changed::source changed after the build witness: $rel"
    exit 1
  fi
  mkdir -p "$(dirname "$rel")"
  cp -p "$src" "$rel"
  git add -- "$rel"
done < "$BRIEF_MANIFEST"

if git diff --cached --quiet; then
  echo "::notice title=AI Brief checkpoint::main already has this narrow snapshot"
  exit 0
fi
if ! push_staged_clean; then
  echo "::error title=AI Brief checkpoint markers::refusing unclean generated snapshot"
  exit 1
fi
git commit -m "aibrief: durable early nightly snapshot $(date -u +%F)"
CHECKPOINT_PARENT="$(git rev-parse HEAD^)"

PUSH_ALARM=120
PUSH_BUDGET_SECS=420
PUSH_MAX_ATTEMPTS=6
PUSH_MAIN_BRANCHES="$CHECKPOINT_BRANCH"
push_retry_init "AI Brief early durable checkpoint"
push_on_main_ok || exit 1
while push_attempt; do
  if ! push_fetch_main_for_rebase; then
    push_abort_rebase
    push_backoff
    continue
  fi
  if ! git diff --quiet "$SOURCE_HEAD" origin/main -- "${FENCED[@]}"; then
    echo "::error title=AI Brief checkpoint race::a source/output changed on main; preserving the accepted tree"
    exit 1
  fi
  if ! git diff --quiet "$CHECKPOINT_PARENT" origin/main -- \
    data/regime/master_brief.json data/regime/china_brief.json data/regime/btc_brief.json \
    site/master_brief.json site/china_brief.json site/btc_brief.json; then
    echo "::error title=AI Brief checkpoint same-path race::main moved an owned brief path; no conflict-override allowed"
    exit 1
  fi
  if perl -e 'alarm 180; exec @ARGV or die' -- git rebase origin/main; then
    CHECKPOINT_PARENT="$(git rev-parse HEAD^)"
    if push_do origin HEAD:main; then
      ACCEPTED_SHA="$(git rev-parse HEAD)"
      push_won
      git fetch origin +refs/heads/main:refs/remotes/origin/main
      if ! git merge-base --is-ancestor "$ACCEPTED_SHA" origin/main ||
         ! git diff --quiet "$ACCEPTED_SHA" origin/main -- \
           data/regime/master_brief.json data/regime/china_brief.json data/regime/btc_brief.json \
           site/master_brief.json site/china_brief.json site/btc_brief.json; then
        echo "::error title=AI Brief checkpoint readback::push did not retain the proven brief bytes"
        exit 1
      fi
      echo "AI Brief accepted on main at $ACCEPTED_SHA"
      exit 0
    fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::error title=AI Brief checkpoint not accepted::no durable brief publication was proven"
exit 1
