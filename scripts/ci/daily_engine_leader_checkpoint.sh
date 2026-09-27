#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# Narrow durability checkpoint for the existing US leader-pullback source artifact.
# This moves no computation and creates no second publisher: the preceding owner step
# writes the artifact; this step only prevents the long engine tail from stranding it.
set -euo pipefail
. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"

LEADER_PATH="site/anticipationdata/us_leader_pullback.json"

# Fail closed before touching git. A previous artifact may remain on disk when the
# publisher refuses a run-wide data failure; never mistake that last-good file for
# evidence that THIS run produced qualified current source truth.
python3 - "$LEADER_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit("leader checkpoint refused: source artifact is absent")
payload = json.loads(path.read_text(encoding="utf-8"))
coverage = payload.get("coverage") if isinstance(payload, dict) else None
coverage = coverage if isinstance(coverage, dict) else {}
contract = coverage.get("source_contract")
contract = contract if isinstance(contract, dict) else {}
qualified = contract.get("pass") is True and coverage.get("publishable") is True
if contract.get("schema") != "us_turn_watch.source_contract.v1" or not qualified:
    raise SystemExit("leader checkpoint refused: source contract is absent or failed")
if payload.get("data_session") != contract.get("modal_session"):
    raise SystemExit("leader checkpoint refused: artifact/session contract mismatch")
lag = contract.get("completed_session_lag")
cap = contract.get("max_completed_session_lag")
if not isinstance(lag, int) or not isinstance(cap, int) or lag > cap:
    raise SystemExit("leader checkpoint refused: completed-session freshness is outside contract")
authority = payload.get("authority") or {}
if authority.get("tier") != "display" or any(
    authority.get(key) is not False
    for key in ("may_rank", "may_gate", "may_size", "may_escalate")
):
    raise SystemExit("leader checkpoint refused: display-only authority drift")
PY

git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
EVENT_REF="${GITHUB_REF:-}"
EVENT_SHA="${GITHUB_SHA:-}"
SOURCE_BRANCH="$(git -C "${GITHUB_WORKSPACE:-.}" symbolic-ref --short -q HEAD || true)"
SOURCE_HEAD="$(git -C "${GITHUB_WORKSPACE:-.}" rev-parse HEAD)"
git fetch origin +refs/heads/main:refs/remotes/origin/main
if [ "$EVENT_REF" != "refs/heads/main" ] \
  || [ -z "$EVENT_SHA" ] \
  || [ "$SOURCE_BRANCH" != "main" ] \
  || ! git merge-base --is-ancestor "$SOURCE_HEAD" origin/main; then
  echo "::error title=Leader checkpoint source rejected::event and checkout must both be origin/main ancestry"
  exit 1
fi
# Same-path race: never overwrite a newer leader artifact that landed after checkout.
if ! git diff --quiet "$SOURCE_HEAD" origin/main -- "$LEADER_PATH"; then
  echo "::error title=Leader checkpoint same-path race::origin/main advanced $LEADER_PATH after checkout; preserving main"
  exit 1
fi

CHECKPOINT_ROOT="$(mktemp -d "${RUNNER_TEMP}/leader-checkpoint.XXXXXX")"
CHECKPOINT_DIR="${CHECKPOINT_ROOT}/tree"
CHECKPOINT_BRANCH="_leader_checkpoint_${GITHUB_RUN_ID}_${GITHUB_RUN_ATTEMPT:-1}"
cleanup_leader_checkpoint() {
  cd "${GITHUB_WORKSPACE:-.}"
  git worktree remove --force "$CHECKPOINT_DIR" 2>/dev/null || true
  git branch -D "$CHECKPOINT_BRANCH" 2>/dev/null || true
  rmdir "$CHECKPOINT_ROOT" 2>/dev/null || true
}
trap cleanup_leader_checkpoint EXIT

git worktree add -b "$CHECKPOINT_BRANCH" "$CHECKPOINT_DIR" origin/main
mkdir -p "$CHECKPOINT_DIR/$(dirname "$LEADER_PATH")"
cp -p "${GITHUB_WORKSPACE:-.}/$LEADER_PATH" "$CHECKPOINT_DIR/$LEADER_PATH"
cd "$CHECKPOINT_DIR"
git add -- "$LEADER_PATH"
if git diff --cached --quiet; then
  echo "Leader checkpoint: no source artifact change"
  exit 0
fi
if ! push_staged_clean "$LEADER_PATH"; then
  echo "::error title=Leader checkpoint refused::conflict-marker guard rejected source artifact"
  exit 1
fi
git commit -m "prophet-us: durable leader source checkpoint $(date -u +%F)"
CHECKPOINT_PARENT="$(git rev-parse HEAD^)"

PUSH_ALARM=120
PUSH_BUDGET_SECS=420
PUSH_MAX_ATTEMPTS=12
PUSH_MAIN_BRANCHES="$CHECKPOINT_BRANCH"
push_retry_init "Prophet leader source checkpoint"
push_on_main_ok || exit 0
while push_attempt; do
  if ! push_fetch_main_for_rebase; then
    push_abort_rebase
    push_backoff
    continue
  fi
  # Same-path race check is repeated after every fetch; unrelated main movement may rebase.
  if ! git diff --quiet "$CHECKPOINT_PARENT" origin/main -- "$LEADER_PATH"; then
    echo "::error title=Leader checkpoint same-path race::origin/main advanced $LEADER_PATH during publication; preserving main"
    exit 1
  fi
  if perl -e 'alarm 180; exec @ARGV or die' -- git rebase origin/main; then
    CHECKPOINT_PARENT="$(git rev-parse HEAD^)"
    if push_do origin HEAD:main; then
      echo "pushed leader source checkpoint on attempt $PUSH_ATTEMPT"
      push_won
      exit 0
    fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::error title=Leader checkpoint NOT pushed::$PUSH_ATTEMPT attempts failed ($PUSH_STOP); current source remains runner-local"
exit 1
