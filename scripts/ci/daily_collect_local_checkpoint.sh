#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# Original collect/commitdata body; workflow-size headroom, no business change.
set -e
echo "committed=false" >> "$GITHUB_OUTPUT"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
# site/qledger: the qledger grader (scripts/collect.py -> grade_qledger)
# writes the TRACKED site/qledger/track_record.json (un-ignored by #1139).
# Left unstaged it blocks `git pull --rebase` ("unstaged changes") and the
# whole data push silently dies after 5 attempts — 07-03/07-04 collections
# were lost exactly this way (the sentinel staging-gap pattern). The
# --autostash on the rebase below is the durable guard: it survives ANY
# stray tracked write collect leaves outside data/+site/qledger/ (e.g.
# reports/*.md graders), not just the qledger paths we happen to stage here.
# (site/basketdata moved with the TIL steps to collect_tail's commit —
# 2026-07-14 split; nothing left in this job writes site/basketdata.)
git add data/ site/qledger/
# W0b (2026-07-08 stale-HK incident): US collect job must NOT commit asia-owned
# data that it never produced. The GHA cache restore steps above may lay stale
# data/hk_stocks (restore-keys: hk-stocks-ohlc-) and breadth caches on top of
# the fresh files asia-close already committed.  After the broad `git add data/`
# above, unstage every asia-close-owned path so -X theirs on the rebase-push
# cannot clobber asia's fresh commit with this job's stale copy.
# Derived from asia-close.yml: collect --group asia = adapters starting with
# `china` or `hk` (scripts/collect.py group_members), so excludes cover all
# data/china*, data/hk*, and data/hkma (adapter key `hkma` starts with `hk`).
git reset -q -- data/hk data/hk_* data/hkma data/china data/china_* 2>/dev/null || true
# Capital-structure SCOPE CARVE-OUT — same idiom as the asia unstage above.
# UNCONDITIONAL since the 2026-08-06 split: none of the five capital-structure
# steps has run yet at this point, so there is no outcome to test and nothing
# here could be a complete generation. `run collectors`
# (sec_capital_structure) has already rewritten the TRACKED
# source_manifest.jsonl, which the broad `git add data/` above swept in — a
# source ledger no compiler has accepted. Drop it; the second checkpoint
# commits it once the whole chain has validated it.
#
# `git reset` ONLY — never `git checkout`. The pre-2026-08-06 carve-out fired
# AFTER a failed chain and restored the clean committed ledger (#4600's
# self-heal). Here the chain has not run, and that freshly-collected ledger is
# its INPUT: reverting it would feed the spine yesterday's manifests every
# single night. Unstage, do not revert.
git reset -q -- data/capital_structure site/capital-structure-data 2>/dev/null || true
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
if git diff --cached --quiet; then echo "no market data changes to commit"; exit 0; fi
git commit -m "data: daily collection $(date -u +%F)"
echo "committed=true" >> "$GITHUB_OUTPUT"
