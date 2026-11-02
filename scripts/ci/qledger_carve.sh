#!/usr/bin/env bash
# QLedger GH001 carve-out — shared by every nightly committer that stages
# data/ wholesale (engine "commit engine outputs" + its core checkpoint,
# collect_tail "commit tail data", stock_briefs). SOURCED, never executed.
#
# WHY. GitHub rejects a push whose commits introduce any blob larger than
# 104,857,600 B (GH001). data/qledger/claims.jsonl is an append-only ledger
# (merge=union) that sits at exactly that limit on main (committed 2026-10-21
# by the last engine commit that landed) and grows on every nightly runner.
# Staging it sinks the WHOLE commit: on 2026-10-29/30 (run 40803269874) the
# engine's regime update, the curated US candidate tier, the rendered site,
# collect_tail's accrual and the stock briefs were all rejected with
#   "File data/qledger/claims.jsonl is 146.50 MB; this exceeds GitHub's file
#    size limit of 100.00 MB" / "GH001 large-file rejection".
# PR #9556 carved the ledger out of the `collect` market commit only; this
# helper extends the SAME accepted semantics to the other wholesale committers.
# The ledger's own publication is NOT repaired here — that stays with the
# qledger publication program (#8756 / #9450 / #9452 / #10079).
#
# CONTRACT (mirrors #9556 + its review 5566188238 / 5570764032):
#   qledger_carve_staged
#     measures every STAGED blob under data/qledger + site/qledger. When none is
#     within QLEDGER_CARVE_MARGIN of the limit (or unmeasurable) it is a no-op:
#     returns 0, QLEDGER_CARVED=false, and the ledger publishes as before.
#     Otherwise it (1) takes a CUSTODY SNAPSHOT — an unreachable, runner-local
#     commit of the full staged index (parent = HEAD; no ref names it, nothing
#     pushes it), (2) unstages both qledger planes, (3) PARKS the worktree copies
#     at HEAD so the caller's `rebase --autostash` never carries the dirty bytes,
#     (4) VERIFIES the parked state (a restore exit code is not evidence) and
#     (5) arms qledger_carve_restore on EXIT. Returns 0 with QLEDGER_CARVED=true
#     and QLEDGER_SNAPSHOT=<oid>. Unstage only — never revert or delete.
#     If the snapshot or the verified park cannot be secured it returns 2 after
#     a ::error; the CALLER must withhold the publication (collect: exit 0 and
#     stay green; engine: exit 1, a lost engine commit must red the run).
#   qledger_carve_restore
#     puts the carved bytes back byte-identical from the snapshot (the steps
#     after a mid-job checkpoint read the ledger this job wrote) and verifies.
#     Runner-local only; never published here.
#
# Tests: tests/test_qledger_carve.py (unit + a real rebase/push against a bare
# origin whose pre-receive hook enforces the GH001 blob limit).

# shellcheck disable=SC2086  # QLEDGER_CARVE_PATHS is a deliberate word list
QLEDGER_CARVE_LIMIT=104857600
QLEDGER_CARVE_MARGIN=1048576
QLEDGER_CARVE_PATHS="data/qledger site/qledger"
QLEDGER_CARVED=false
QLEDGER_SNAPSHOT=""
QLEDGER_CARVE_OVER=""

_qledger_carve_summary() {
  [ -n "${GITHUB_STEP_SUMMARY:-}" ] || return 0
  printf '%s\n' "$@" >> "$GITHUB_STEP_SUMMARY" 2>/dev/null || true
}

# Staged qledger blobs within the margin (or unmeasurable), as " path=size" words.
_qledger_carve_oversize_staged() {
  local qpath qsize over=""
  while IFS= read -r -d '' qpath; do
    qsize=$(git cat-file -s ":$qpath" 2>/dev/null || echo unmeasured)
    case "$qsize" in
      ''|*[!0-9]*) over="$over $qpath=unmeasured" ;;
      *) if [ "$qsize" -gt $((QLEDGER_CARVE_LIMIT - QLEDGER_CARVE_MARGIN)) ]; then over="$over $qpath=${qsize}B"; fi ;;
    esac
  done < <(git diff --cached --name-only -z --no-renames --diff-filter=d -- $QLEDGER_CARVE_PATHS)
  printf '%s' "$over"
}

# Worktree + index of both qledger planes equal HEAD (untracked files are not
# autostash cargo and are left alone, same as #9556's park).
_qledger_carve_parked_ok() {
  git diff --quiet HEAD -- $QLEDGER_CARVE_PATHS \
    && git diff --cached --quiet -- $QLEDGER_CARVE_PATHS
}

# The snapshot id outlives this process: a step timeout or job cancel can
# SIGKILL the committer before its EXIT trap runs, so the workflow's
# `if: always()` restore step reads the id back from here (per run id; the
# runner's temp dir is job-scoped). Removed once a restore fully succeeds.
_qledger_carve_snapshot_file() {
  printf '%s/qledger_carve_snapshot.%s' "${RUNNER_TEMP:-${TMPDIR:-/tmp}}" "${GITHUB_RUN_ID:-local}"
}

_qledger_carve_arm_restore() {
  # Chain a pre-existing EXIT trap verbatim. `trap -p` prints it shell-quoted
  # (possibly multi-line), so it is re-parsed with `set --`, not a line regex.
  local prior_decl prior=""
  prior_decl=$(trap -p EXIT)
  if [ -n "$prior_decl" ]; then
    eval "set -- ${prior_decl#trap }"
    prior="${2:-}"
  fi
  if [ -n "$prior" ]; then
    # shellcheck disable=SC2064
    trap "qledger_carve_restore; $prior" EXIT
  else
    trap 'qledger_carve_restore' EXIT
  fi
}

qledger_carve_staged() {
  QLEDGER_CARVED=false
  QLEDGER_SNAPSHOT=""
  QLEDGER_CARVE_OVER=$(_qledger_carve_oversize_staged)
  [ -n "$QLEDGER_CARVE_OVER" ] || return 0
  local snapshot
  snapshot=$(git commit-tree "$(git write-tree)" -p HEAD -m "qledger carve custody snapshot (runner-local; never pushed)" 2>/dev/null) || snapshot=""
  if [ -z "$snapshot" ] || ! git cat-file -e "$snapshot^{commit}" 2>/dev/null; then
    echo "::error title=publication withheld (qledger carve snapshot failed)::could not snapshot the carved qledger bytes:${QLEDGER_CARVE_OVER}; index and worktree left untouched; the caller withholds this commit/push (owner of the ledger's size: qledger publication program)"
    _qledger_carve_summary "### Publication withheld: qledger carve snapshot failed" "" "- oversize qledger blob(s):${QLEDGER_CARVE_OVER}" "- nothing committed or pushed by this step" "- owner: qledger publication program"
    return 2
  fi
  printf '%s\n' "$snapshot" > "$(_qledger_carve_snapshot_file)" 2>/dev/null || true
  git reset -q -- $QLEDGER_CARVE_PATHS
  if ! _qledger_carve_parked_ok; then
    local qplane
    for qplane in $QLEDGER_CARVE_PATHS; do
      git restore --source=HEAD --worktree -- "$qplane" 2>/dev/null || true
    done
  fi
  if ! _qledger_carve_parked_ok; then
    QLEDGER_SNAPSHOT="$snapshot"
    _qledger_carve_arm_restore
    echo "::error title=publication withheld (qledger park failed)::could not park ${QLEDGER_CARVE_PATHS} at HEAD before the push; the carved bytes are restored from snapshot $snapshot on exit (runner-local); the caller withholds this commit/push"
    _qledger_carve_summary "### Publication withheld: qledger park failed" "" "- oversize qledger blob(s):${QLEDGER_CARVE_OVER}" "- nothing pushed by this step; carved bytes restored from snapshot \`$snapshot\` (runner-local)" "- owner: qledger publication program"
    return 2
  fi
  QLEDGER_CARVED=true
  QLEDGER_SNAPSHOT="$snapshot"
  _qledger_carve_arm_restore
  echo "::warning title=qledger carved out of this commit::staged qledger blob(s) within ${QLEDGER_CARVE_MARGIN}B of GitHub's ${QLEDGER_CARVE_LIMIT}B file limit:${QLEDGER_CARVE_OVER}; this step's data/qledger + site/qledger are NOT published (owner: qledger publication program); the commit, if any, excludes them; bytes parked at HEAD and restored from snapshot $snapshot on exit"
  _qledger_carve_summary "### qledger carved out of this commit (GH001 prevention)" "" "- oversize qledger blob(s):${QLEDGER_CARVE_OVER}" "- data/qledger + site/qledger: NOT published by this step; restored runner-local from snapshot \`$snapshot\`" "- owner: qledger publication program"
  return 0
}

# Per-path delta restore — #9556's restore step semantics, verbatim: only the
# paths THIS run's snapshot changed against its parent are written back (or
# removed), so a qledger file that origin/main added or changed underneath
# (HEAD has moved by the post-push rebase) is left exactly as main has it.
# Idempotent: the EXIT trap and the workflow's always() step may both run it.
# A path it cannot restore is reported LOST (::error), never as success.
qledger_carve_restore() {
  local snapshot="${1:-${QLEDGER_SNAPSHOT:-}}"
  [ -n "$snapshot" ] || return 0
  QLEDGER_SNAPSHOT=""
  local restored="" lost="" qpaths qpath want have
  qpaths=$(git -c core.quotePath=false diff --name-only --no-renames "$snapshot^" "$snapshot" -- $QLEDGER_CARVE_PATHS 2>/dev/null) || qpaths=""
  if [ -z "$qpaths" ]; then lost=" snapshot-unreadable:$snapshot"; fi
  while IFS= read -r qpath; do
    [ -n "$qpath" ] || continue
    if git cat-file -e "$snapshot:$qpath" 2>/dev/null; then
      want=$(git rev-parse "$snapshot:$qpath" 2>/dev/null) || want=""
      have=$(git hash-object -- "$qpath" 2>/dev/null) || have=""
      if [ -n "$want" ] && [ "$have" != "$want" ]; then
        mkdir -p -- "$(dirname -- "$qpath")" 2>/dev/null || true
        git cat-file blob "$snapshot:$qpath" > "$qpath" 2>/dev/null || true
        have=$(git hash-object -- "$qpath" 2>/dev/null) || have=""
      fi
      if [ -n "$want" ] && [ "$have" = "$want" ]; then restored="$restored $qpath"; else lost="$lost $qpath"; fi
    else
      rm -f -- "$qpath" 2>/dev/null || true
      if [ -e "$qpath" ]; then lost="$lost $qpath(deleted)"; else restored="$restored $qpath(deleted)"; fi
    fi
  done <<< "$qpaths"
  if [ -n "$lost" ]; then
    echo "::error title=qledger carve custody LOST::carved qledger bytes could not be restored in this workspace:${lost}; they survive only in the unreachable runner-local snapshot $snapshot until git gc, and were NOT published (owner: qledger publication program)"
    return 0
  fi
  echo "qledger carve: restored byte-identical from snapshot $snapshot:${restored} (runner-local; not published)"
  rm -f -- "$(_qledger_carve_snapshot_file)" 2>/dev/null || true
  return 0
}

# The workflow's `if: always()` safety net after each committer step: restore
# from the snapshot id the carve recorded, if the committer's own EXIT trap
# never got to (SIGKILL on timeout/cancel). Quiet no-op when nothing is owed.
qledger_carve_restore_from_file() {
  local file snapshot
  file=$(_qledger_carve_snapshot_file)
  if [ ! -s "$file" ]; then
    echo "qledger carve: no runner-local snapshot recorded for this run (nothing to restore)"
    return 0
  fi
  snapshot=$(head -n1 "$file" | tr -d '[:space:]')
  if [ -z "$snapshot" ] || ! git cat-file -e "$snapshot^{commit}" 2>/dev/null; then
    echo "::error title=qledger carve custody LOST::recorded snapshot '$snapshot' is unreadable in this workspace; carved qledger bytes were NOT published and could not be restored (owner: qledger publication program)"
    return 0
  fi
  qledger_carve_restore "$snapshot"
}
