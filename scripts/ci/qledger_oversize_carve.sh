#!/usr/bin/env bash
# EXTRACTED-FROM: .github/workflows/daily.yml collect job (2026-10-17 carve, #9556)
# Sourced (never executed) by scripts/ci/daily_engine_commit_outputs.sh and
# scripts/ci/daily_collect_tail_commit.sh before their commit/push bands; the
# three functions mirror the collect job's carve/park/restore blocks line for
# line (daily.yml at f2efb8ba: carve 763-815, park 895-920, restore 1011-1050).
# Test-only override: QLEDGER_CARVE_LIMIT / QLEDGER_CARVE_MARGIN replace the
# frozen 104857600 / 1048576 ONLY when QLEDGER_CARVE_TEST_OVERRIDE=1; without
# that flag both env vars are ignored. Publication of data/qledger + site/qledger
# stays owned by the qledger publication program (#10079): nothing here publishes,
# truncates or rewrites the ledger — carved bytes remain byte-identical in the
# runner workspace under an unreachable runner-local snapshot commit.

qledger_carve_staged() {
  # The collect job's carve, line for line: measure every staged qledger blob;
  # when any sits within the margin of GitHub's hard file limit, snapshot the
  # full staged index, then unstage BOTH planes (one plane: published together
  # or not at all). Unstage only, never revert — the ledger's size belongs to
  # the qledger publication program.
  local lane
  local qledger_limit qledger_margin
  local qledger_over qpath qsize qledger_snapshot
  lane="$1"
  qledger_limit=104857600
  qledger_margin=1048576
  if [ "${QLEDGER_CARVE_TEST_OVERRIDE:-0}" = "1" ]; then
    qledger_limit="${QLEDGER_CARVE_LIMIT:-$qledger_limit}"
    qledger_margin="${QLEDGER_CARVE_MARGIN:-$qledger_margin}"
  fi
  qledger_over=""
  while IFS= read -r -d '' qpath; do
    qsize=$(git cat-file -s ":$qpath" 2>/dev/null || echo unmeasured)
    case "$qsize" in
      ''|*[!0-9]*) qledger_over="$qledger_over $qpath=unmeasured" ;;
      *) if [ "$qsize" -gt $((qledger_limit - qledger_margin)) ]; then qledger_over="$qledger_over $qpath=${qsize}B"; fi ;;
    esac
  done < <(git diff --cached --name-only -z --no-renames --diff-filter=d -- data/qledger site/qledger)
  export QLEDGER_LANE="$lane"
  if [ -z "$qledger_over" ]; then
    # Nothing oversize staged: touch nothing.
    export QLEDGER_CARVED=false
    return 0
  fi
  # Custody snapshot BEFORE the unstage: an unreachable, runner-local commit of
  # the full staged index (parent = this HEAD). No ref names it and nothing
  # pushes it — the same object class as git's own autostash entry. The push
  # loop's --autostash can discard dirty bytes on a conflicted re-apply, so the
  # caller parks these paths at HEAD and restores them from this snapshot at
  # EXIT (#9556 review 5566188238).
  qledger_snapshot=$(git commit-tree "$(git write-tree)" -p HEAD -m "qledger carve custody snapshot (runner-local; never pushed)" 2>/dev/null) || qledger_snapshot=""
  if [ -z "$qledger_snapshot" ]; then
    # FAIL CLOSED ON PUBLICATION: with no snapshot, park/restore cannot run and
    # the push loop's --autostash would carry the dirty qledger bytes
    # unprotected. Withhold the whole commit (the caller exits 0 before its
    # commit band), leave index + worktree untouched, keep the job green.
    export QLEDGER_WITHHELD=true
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
      echo "qledger_withheld=true" >> "$GITHUB_OUTPUT" || true
    fi
    echo "::error title=${lane} publication withheld (qledger carve snapshot failed)::could not snapshot the carved qledger bytes:${qledger_over}; NEITHER ${lane} data NOR data/qledger + site/qledger is published by this run (no ${lane} commit, no push). The collected bytes are left untouched in this runner workspace (runner-local; gone at the next clean checkout)."
    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
      {
        echo "### ${lane} publication withheld: qledger carve snapshot failed"
        echo ""
        echo "- oversize qledger blob(s):${qledger_over}"
        echo "- ${lane} data: NOT committed and NOT pushed by this run"
        echo "- data/qledger + site/qledger: NOT published; collected bytes left untouched in this runner workspace (runner-local)"
        echo "- owner: qledger publication program"
      } >> "$GITHUB_STEP_SUMMARY" || true
    fi
    return 0
  fi
  git reset -q -- data/qledger site/qledger
  export QLEDGER_CARVED=true
  export QLEDGER_SNAPSHOT="$qledger_snapshot"
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
      echo "qledger_carved=true"
      echo "qledger_snapshot=$qledger_snapshot"
    } >> "$GITHUB_OUTPUT" || true
  fi
  echo "::warning title=qledger carved out of ${lane} commit::staged qledger blob(s) within ${qledger_margin}B of GitHub's ${qledger_limit}B file limit:${qledger_over}; this run's data/qledger + site/qledger are NOT published (owner: qledger publication program); the ${lane} commit, if any, excludes them."
  return 0
}

qledger_park() {
  # The collect job's park: put both planes' worktree back at HEAD so the push
  # loop's --autostash cannot carry the dirty carved bytes, and VERIFY the
  # parked state itself — a restore exit code is not evidence (#9556 review
  # 5570764032). Label defaults to the one recorded by the last carve call.
  local lane
  lane="${1:-${QLEDGER_LANE:-unknown}}"
  if [ -z "${QLEDGER_SNAPSHOT:-}" ]; then
    export QLEDGER_PARKED=false
    return 0
  fi
  if ! git diff --quiet HEAD -- data/qledger site/qledger; then
    git restore --source=HEAD --worktree -- data/qledger site/qledger || true
  fi
  if git diff --quiet HEAD -- data/qledger site/qledger && git diff --cached --quiet -- data/qledger site/qledger; then
    export QLEDGER_PARKED=true
  else
    export QLEDGER_PARKED=false
    echo "::error title=${lane} publication withheld (qledger park failed)::could not park data/qledger + site/qledger at HEAD before the push; NEITHER ${lane} data NOR data/qledger + site/qledger is published by this run. The ${lane} commit stays runner-local and unpushed (no fetch, rebase or push runs against the dirty carved bytes); snapshot $QLEDGER_SNAPSHOT and the collected bytes stay in this runner workspace (runner-local; gone at the next clean checkout). Owner: qledger publication program."
    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
      {
        echo "### ${lane} publication withheld: qledger park failed"
        echo ""
        echo "- ${lane} data: committed locally but NOT pushed by this run"
        echo "- data/qledger + site/qledger: NOT published; restored from snapshot \`$QLEDGER_SNAPSHOT\` by the restore step (runner-local)"
        echo "- owner: qledger publication program"
      } >> "$GITHUB_STEP_SUMMARY" || true
    fi
  fi
  return 0
}

qledger_restore() {
  # The collect job's restore, EXACT: put the carved bytes back byte-identical
  # from the snapshot. Runner-local, never published; a path it cannot restore
  # is reported LOST, never as success. Installed as an EXIT trap, so EVERY
  # command that can fail is guarded and it ends with `return 0` — under the
  # caller's `set -e` an unguarded failure inside an EXIT-trap function would
  # replace the script's exit status. Idempotent: a second call with the same
  # snapshot changes nothing and still reports restored.
  local restored
  local lost
  local qpaths qpath want have
  restored=""
  lost=""
  if [ -z "${QLEDGER_SNAPSHOT:-}" ]; then
    return 0
  fi
  qpaths=$(git -c core.quotePath=false diff --name-only --no-renames "$QLEDGER_SNAPSHOT^" "$QLEDGER_SNAPSHOT" -- data/qledger site/qledger 2>/dev/null) || qpaths=""
  if [ -z "$qpaths" ]; then lost=" snapshot-unreadable:$QLEDGER_SNAPSHOT"; fi
  while IFS= read -r qpath; do
    [ -n "$qpath" ] || continue
    if git cat-file -e "$QLEDGER_SNAPSHOT:$qpath" 2>/dev/null; then
      want=$(git rev-parse "$QLEDGER_SNAPSHOT:$qpath" 2>/dev/null) || want=""
      have=$(git hash-object -- "$qpath" 2>/dev/null) || have=""
      if [ -n "$want" ] && [ "$have" != "$want" ]; then
        mkdir -p -- "$(dirname -- "$qpath")" 2>/dev/null || true
        git cat-file blob "$QLEDGER_SNAPSHOT:$qpath" > "$qpath" 2>/dev/null || true
        have=$(git hash-object -- "$qpath" 2>/dev/null) || have=""
      fi
      if [ -n "$want" ] && [ "$have" = "$want" ]; then restored="$restored $qpath"; else lost="$lost $qpath"; fi
    else
      rm -f -- "$qpath" 2>/dev/null || true
      if [ -e "$qpath" ]; then lost="$lost $qpath(deleted)"; else restored="$restored $qpath(deleted)"; fi
    fi
  done <<< "$qpaths"
  if [ -n "$lost" ]; then
    echo "::error title=qledger carve custody LOST::carved qledger bytes could not be restored in this workspace:${lost}; they survive only in the unreachable runner-local snapshot $QLEDGER_SNAPSHOT until git gc, and were NOT published (owner: qledger publication program)."
  fi
  if [ -n "$restored" ]; then
    echo "::warning title=qledger carve-out not published::NOT published by this run:${restored} — restored byte-identical in this runner's workspace from snapshot $QLEDGER_SNAPSHOT; runner-local only, gone at the next clean checkout (owner: qledger publication program)."
  fi
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    {
      echo "### QLedger carve-out — NOT published by this run"
      echo ""
      echo "- snapshot (runner-local, never pushed): \`$QLEDGER_SNAPSHOT\`"
      echo "- restored byte-identical in this workspace:${restored:- none}"
      echo "- LOST (not restorable here):${lost:- none}"
      echo "- owner: qledger publication program; this job does not durably retain these bytes"
    } >> "$GITHUB_STEP_SUMMARY" || true
  fi
  return 0
}
