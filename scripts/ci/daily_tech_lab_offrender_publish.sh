#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job tech_lab_offrender, original publishing step; native graph added in the SAME candidate.
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
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
git add site/factordata/tech_screener.json site/factordata/tech_lab.json
if [ -f site/factordata/tech_confluence.json ]; then
  git add site/factordata/tech_confluence.json
fi
if [ -f site/factordata/m2_profiles.json ]; then
  git add site/factordata/m2_profiles.json
fi
# tech_events is written by a sibling PR (TLT-W3); pick it up once present.
if [ -d site/factordata/tech_events ]; then
  git add site/factordata/tech_events
fi
if [ -f site/confluence_screener.html ]; then
  git add site/confluence_screener.html
fi
if [ -f site/premiumdata/confluence_screener.json ]; then
  git add site/premiumdata/confluence_screener.json
fi
if [ -f site/og/confluence_screener.png ]; then
  git add site/og/confluence_screener.png
fi
if git diff --cached --quiet; then echo "no tech-lab artifact changes"; exit 0; fi
git commit -m "tech-lab: nightly 64-signal screener + lab refresh $(date -u +%F)"
# best-effort rebase-push (own files → clean rebases; no other job writes these paths)
PUSH_ALARM=420
push_retry_init "tech-lab artifacts"
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
while push_attempt; do
  # pre-sync collision sweep (render.yml / #2252): a mid-run commit on origin/main can
  # TRACK a path this job wrote as an UNTRACKED side-effect — the rebase checkout then
  # refuses ("untracked working tree files would be overwritten") and --autostash can't
  # clear it (it parks tracked modifications only), so every retry dies identically.
  # Everything this step publishes is already committed above, so a path untracked HERE
  # but tracked on origin/main is a throwaway local write — origin/main is authoritative.
  # Gitignored files and untracked paths origin/main doesn't track never enter the
  # intersection (runner-local stores and caches are untouched).
  perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin main || true
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  if perl -e 'alarm 420; exec @ARGV or die' -- git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    if push_do; then echo "pushed tech-lab artifacts on attempt $PUSH_ATTEMPT"; push_won; exit 0; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::warning::could not push tech-lab artifacts after $PUSH_ATTEMPT attempts ($PUSH_STOP) (non-fatal)"
