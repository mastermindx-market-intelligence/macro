#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/asia-close.yml
# Original asia/commit collected asia data business body; staged native route preserves original budget.
set -e
export NATIVE_PUBLICATION_PUBLISHING_STEP=asia_commitdata
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
publisher_source_root="${native_code_root:-${GITHUB_WORKSPACE:-.}}"
echo "committed=false" >> "$GITHUB_OUTPUT"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
# Stage collected data + the qledger grader's tracked
# site/qledger/track_record.json. The --autostash on the rebase below is the
# real guard, though: scripts.collect also dirties OTHER tracked files (e.g.
# reports/*.md graders) that no `git add` here covers — left unstaged they
# abort `git pull --rebase` ("unstaged changes") and the push silently dies
# after 5 retries, discarding the whole collection (froze 2026-07-02..07).
# Asia must not acquire the Options PIT/campaign narrow roots owned by the
# dedicated narrow publishers; the helper restores/cleans them around the
# broad `git add` so neither the collect commit nor the engine commit below
# can smuggle an Options artifact onto the Asia lane.
NATIVE_PUBLICATION_CODE_ROOT="${native_code_root:-}" bash "$publisher_source_root/scripts/ci/options_signal_nightly.sh" exclude-broad
git add data/ site/qledger/
NATIVE_PUBLICATION_CODE_ROOT="${native_code_root:-}" bash "$publisher_source_root/scripts/ci/options_signal_nightly.sh" exclude-broad
# QLEDGER OVERSIZE CARVE-OUT (2026-10-17). data/qledger/claims.jsonl is an
# append-only monolith; once it crossed GitHub's 100 MiB file limit, GH001
# rejected this WHOLE commit and the market plane (data/baskets/ohlcv,
# data/stocks, breadth, macro) stopped publishing on 2026-10-16 and 10-17
# (jobs 116748357565, 117262684428). When any staged qledger blob is within
# 1 MiB of the limit (headroom for the rebase onto a moving main), unstage ALL
# of data/qledger + site/qledger (one plane: published together or not at
# all) and warn. Unstage only, never revert; the ledger's size belongs to the
# qledger publication program.
qledger_limit=104857600
qledger_margin=1048576
qledger_over=""
while IFS= read -r -d '' qpath; do
  qsize=$(git cat-file -s ":$qpath" 2>/dev/null || echo unmeasured)
  case "$qsize" in
    ''|*[!0-9]*) qledger_over="$qledger_over $qpath=unmeasured" ;;
    *) if [ "$qsize" -gt $((qledger_limit - qledger_margin)) ]; then qledger_over="$qledger_over $qpath=${qsize}B"; fi ;;
  esac
done < <(git diff --cached --name-only -z --no-renames --diff-filter=d -- data/qledger site/qledger)
if [ -n "$qledger_over" ]; then
  # Custody snapshot BEFORE the unstage: an unreachable, runner-local commit of
  # the full staged index (parent = this HEAD). No ref names it and nothing
  # pushes it — the same object class as git's own autostash entry. The push
  # loop's --autostash can discard dirty bytes on a conflicted re-apply, so
  # the steps around `push market data` park these paths at HEAD and restore
  # them from this snapshot afterwards (#9556 review 5566188238).
  qledger_snapshot=$(git commit-tree "$(git write-tree)" -p HEAD -m "qledger carve custody snapshot (runner-local; never pushed)" 2>/dev/null) || qledger_snapshot=""
  if [ -z "$qledger_snapshot" ]; then
    # FAIL CLOSED ON PUBLICATION: with no snapshot, park/restore cannot run and the
    # push loop's --autostash would carry the dirty qledger bytes unprotected. So
    # withhold the WHOLE market commit (committed stays false: neither push step
    # runs), leave index + worktree untouched, and keep collect green.
    echo "qledger_withheld=true" >> "$GITHUB_OUTPUT"
    echo "::error title=market publication withheld (qledger carve snapshot failed)::could not snapshot the carved qledger bytes:${qledger_over}; NEITHER market data NOR data/qledger + site/qledger is published by this run (no market commit, no push). The collected bytes are left untouched in this runner workspace (runner-local; gone at the next clean checkout)."
    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
      {
        echo "### Market publication withheld: qledger carve snapshot failed"
        echo ""
        echo "- oversize qledger blob(s):${qledger_over}"
        echo "- market data: NOT committed and NOT pushed by this run"
        echo "- data/qledger + site/qledger: NOT published; collected bytes left untouched in this runner workspace (runner-local)"
        echo "- owner: qledger publication program"
      } >> "$GITHUB_STEP_SUMMARY" || true
    fi
    exit 0
  fi
  git reset -q -- data/qledger site/qledger
  echo "qledger_carved=true" >> "$GITHUB_OUTPUT"
  echo "qledger_snapshot=$qledger_snapshot" >> "$GITHUB_OUTPUT"
  echo "::warning title=qledger carved out of market commit::staged qledger blob(s) within ${qledger_margin}B of GitHub's ${qledger_limit}B file limit:${qledger_over}; this run's data/qledger + site/qledger are NOT published (owner: qledger publication program); the market commit, if any, excludes them."
fi
if git diff --cached --quiet; then echo "no asia data changes"; else
  git commit -m "data: asia collection $(date -u +%F)"
  echo "committed=true" >> "$GITHUB_OUTPUT"
fi
