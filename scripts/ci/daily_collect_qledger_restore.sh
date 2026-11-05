#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# collect original restore carved qledger bytes (runner-local, never published here); size headroom, business body unchanged.
set -e
restored=""
lost=""
qpaths=$(git -c core.quotePath=false diff --name-only --no-renames "$QLEDGER_SNAPSHOT^" "$QLEDGER_SNAPSHOT" -- data/qledger site/qledger 2>/dev/null) || qpaths=""
if [ -z "$qpaths" ]; then lost=" snapshot-unreadable:$QLEDGER_SNAPSHOT"; fi
while IFS= read -r qpath; do
  [ -n "$qpath" ] || continue
  # Classify against the snapshot TREE, never against a lookup exit code
  # (#9556 post-merge findings 6285214966 + 6290288707): a readable tree
  # that lacks the path is a deferred deletion; an unreadable tree
  # (object store, lock, OOM) is LOST and the surviving bytes stay put.
  if ! entry=$(git ls-tree --name-only "$QLEDGER_SNAPSHOT" -- "$qpath" 2>/dev/null); then
    lost="$lost $qpath(lookup-failed)"; continue
  fi
  if [ -n "$entry" ]; then
    want=$(git rev-parse "$QLEDGER_SNAPSHOT:$qpath" 2>/dev/null) || want=""
    if [ -z "$want" ]; then lost="$lost $qpath(lookup-failed)"; continue; fi
    have=$(git hash-object -- "$qpath" 2>/dev/null) || have=""
    if [ "$have" != "$want" ]; then
      # A non-file at the path (a directory) cannot be swapped: POSIX `mv`
      # would move the temp INTO it and leak the blob. Report LOST, touch nothing.
      if [ -e "$qpath" ] && [ ! -f "$qpath" ]; then lost="$lost $qpath(not-a-file)"; continue; fi
      # Read into a sibling temp file and swap in only a hash-verified
      # copy: a failed blob read must never truncate the surviving file.
      mkdir -p -- "$(dirname -- "$qpath")" 2>/dev/null || true
      tmp=$(mktemp "$qpath.restore.XXXXXX" 2>/dev/null) || tmp=""
      if [ -n "$tmp" ] && git cat-file blob "$QLEDGER_SNAPSHOT:$qpath" > "$tmp" 2>/dev/null \
         && [ "$(git hash-object -- "$tmp" 2>/dev/null)" = "$want" ]; then
        chmod u=rw,go=r -- "$tmp" 2>/dev/null || true
        mv -f -- "$tmp" "$qpath" 2>/dev/null || true
      fi
      if [ -n "$tmp" ]; then rm -f -- "$tmp" 2>/dev/null || true; fi
      have=$(git hash-object -- "$qpath" 2>/dev/null) || have=""
    fi
    if [ "$have" = "$want" ]; then restored="$restored $qpath"; else lost="$lost $qpath"; fi
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
