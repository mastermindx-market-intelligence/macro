#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job stock_briefs, original publishing step; native graph added in the SAME candidate.
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
# site/stockbrief is gitignored for local-dev cleanliness but must be TRACKED
# on main so the committed-tree deploy ships it (-f overrides the ignore).
git add -f site/stockbrief 2>/dev/null || true
git add data/catalyst/stockbrief_cache 2>/dev/null || true
# stock_desk (T9): the accountable-lean notes + the graded track record are written
# by build_stock_briefs in THIS job (after the engine job's force-add of site/stockdata
# already ran), so they must be force-added HERE or they never land on main → the
# aidesk_lean.js panel 404s. The ledger (data/stock_desk, NOT gitignored) must also be
# committed or the track record can never accumulate past-due leans. (Same gitignore/
# force-add trap as the per-market stock libraries.)
git add data/stock_desk 2>/dev/null || true
# Eval OS E1: stock_desk's qledger registration (P3 anchor-at-registration,
# #6598) writes claims.jsonl + evidence_clock_start/stock_desk.json under
# data/qledger IN THIS JOB — the only lane that runs this producer. Without
# this add, an accepted claim and the write-once evidence clock live only in
# the runner checkout and the next job's clean checkout destroys them.
# data/qledger's one committed-file fence (the CONTROL clock, #5970) is a
# .gitignore rule, so a plain add here can never re-commit it.
git add data/qledger 2>/dev/null || true
# GH001 carve (scripts/ci/qledger_carve.sh, #9556 parity): an oversize staged qledger blob sank this whole commit nightly from 10-21; withhold stays green.
. "${GITHUB_WORKSPACE:-.}/scripts/ci/qledger_carve.sh"; qledger_carve_staged || exit 0
if git diff --cached --quiet; then echo "no stock-brief changes"; exit 0; fi
git commit -m "stock-briefs: AI research briefs + accountable leans $(date -u +%F)"
# best-effort push (own files → rebases clean against engine/factor_series)
PUSH_ALARM=420
push_retry_init "stock briefs"
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
    if push_do; then echo "pushed stock briefs on attempt $PUSH_ATTEMPT"; push_won; exit 0; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::warning::could not push stock briefs after $PUSH_ATTEMPT attempts ($PUSH_STOP) (non-fatal — the stock page falls back to the last committed briefs)"
