#!/usr/bin/env bash
# Deploy only the exact current origin/master commit. This wrapper deliberately
# ignores the caller's working tree, so concurrent or uncommitted local edits
# cannot leak into production.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${MASTERMIND_GIT_REMOTE:-origin}"
BASE_BRANCH="${MASTERMIND_BASE_BRANCH:-master}"

command -v git >/dev/null
command -v tar >/dev/null

git -C "$REPO_ROOT" fetch "$REMOTE" "$BASE_BRANCH"
REMOTE_SHA="$(git -C "$REPO_ROOT" rev-parse "$REMOTE/$BASE_BRANCH^{commit}")"
REQUESTED="${1:-$REMOTE_SHA}"
TARGET_SHA="$(git -C "$REPO_ROOT" rev-parse "$REQUESTED^{commit}")"

if [[ "$TARGET_SHA" != "$REMOTE_SHA" ]]; then
  echo "Refusing deploy: requested $TARGET_SHA is not current $REMOTE/$BASE_BRANCH ($REMOTE_SHA)." >&2
  exit 2
fi

TMP_BASE="${TMPDIR:-/tmp}"
STAGE="$(mktemp -d "$TMP_BASE/mastermind-deploy.XXXXXX")"

cleanup() {
  case "$STAGE" in
    "$TMP_BASE"/mastermind-deploy.*)
      find "$STAGE" -mindepth 1 -delete
      rmdir "$STAGE"
      ;;
  esac
}
trap cleanup EXIT

git -C "$REPO_ROOT" archive "$TARGET_SHA" | tar -xf - -C "$STAGE"

if [[ ! -x "$STAGE/scripts/deploy_code_to_vps.sh" ]]; then
  echo "Release commit does not contain executable scripts/deploy_code_to_vps.sh." >&2
  exit 2
fi

echo "Deploying merged commit $TARGET_SHA from a clean git archive."
MASTERMIND_DEPLOY_SOURCE="$STAGE/" \
MASTERMIND_DEPLOY_EXPECT_SHA="$TARGET_SHA" \
  "$STAGE/scripts/deploy_code_to_vps.sh"
