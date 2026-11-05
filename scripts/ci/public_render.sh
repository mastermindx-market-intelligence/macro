#!/usr/bin/env bash
set -e
set -u
set -o pipefail

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

# Fast, data-free public-surface render. This intentionally does not invoke any
# market builder, restore a parquet cache, publish R2 data, or use a self-hosted
# runner. The PR already carries direct template/site pairs; this pass renders
# the four Jinja public pages and refreshes immutable asset stamps site-wide.
PUBLIC_OUTPUTS=(site/help.html site/plans.html site/support.html site/unsubscribe.html)

render_public() {
  python -m scripts.build_public_pages
  python -m scripts.inject_data_base
  python -m scripts.externalize_css
  python -m scripts.optimize_assets
  python -m scripts.check_template_site_sync --fix
}

guard_public_outputs() {
  # Only these four pages are rendered from Jinja in this lane. The other
  # site-wide transforms add an external data-base tag, lift CSS, and update
  # src/href attributes; none edits executable inline JS. PR CI already proved
  # the rest of the committed site. Re-scanning all ~3,263 pages took ~2m30s
  # after EVERY lost main-ref race and made the retry itself slower than the
  # repository's merge cadence (run 30505255868 exhausted 240s after two races).
  python3 scripts/check_inline_js.py "${PUBLIC_OUTPUTS[@]}"
  python3 scripts/check_ms_board_coherence.py
}

render_public
guard_public_outputs

git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
git add site/ templates/

if git diff --cached --quiet; then
  echo "public surfaces already current; nothing to commit"
  exit 0
fi

git commit -m "render-public: public pages + asset stamps"

PUSH_BUDGET_SECS=600
PUSH_MAX_ATTEMPTS=12
push_retry_init "public render"
# Route the already-guarded original generation before any legacy rebase.
# Native stage completion is pending, never ordinary publication success.
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac

while push_attempt; do
  PRE_SYNC_HEAD=$(git rev-parse HEAD)
  git fetch origin main || true
  if git pull --rebase -X theirs origin main \
      || bash scripts/rebase_autoresolve_hashed_css.sh; then
    # The common first attempt has no new upstream commit: push immediately.
    # Before this guard the lane needlessly repeated the whole site sweep and
    # full-tree JS scan even when `git pull` changed nothing, opening a new
    # multi-minute ref-race window after it had already synchronized.
    if [ "$(git rev-parse HEAD)" != "$PRE_SYNC_HEAD" ]; then
      # Main really advanced. Re-apply the deterministic transforms to that
      # exact tree, then validate only the four pages this lane renders.
      # Existing pages were proven before the rebase and the transforms do not
      # alter inline JS; a full-tree replay here caused the observed starvation.
      render_public
      guard_public_outputs
      git add site/ templates/
      if ! git diff --cached --quiet; then
        git commit --amend --no-edit
      fi
    else
      echo "main unchanged since the validated render; pushing without a redundant sweep"
    fi
    if push_do origin HEAD:main; then
      echo "pushed public render on attempt $PUSH_ATTEMPT"
      push_won
      exit 0
    fi
  fi
  push_abort_rebase
  push_backoff
done

push_lost
echo "::error title=public render NOT pushed::$PUSH_ATTEMPT attempts failed ($PUSH_STOP)"
exit 1
