#!/usr/bin/env bash
# push_hold.sh — custody for staged rows that cannot land in one GitHub blob.
#
# Ruling R-33: a hold must never destroy an unpublished row. Before local bytes
# are reverted, the exact held bytes are pushed to a custody ref that outlives
# the runner. The next run of the same job fetches that ref and reconciles it.
# A source file and its derived site/ projection are one group: hold every
# staged member of a group that has an over-limit blob, or none of that group.
# If a staged path belongs to no declared group, membership is not proved and
# every staged path is held. A group that was held earlier in the same run is
# held again in full, so a second commit step cannot publish part of it.
#
# Knobs (default in parentheses):
#   PUSH_BLOB_LIMIT          (104857600)  over when staged size is greater than this
#   PUSH_HOLD_PART           (52428800)   chunk size for over-limit custody parts
#   PUSH_HOLD_PREFIX         (refs/heads/push-hold/)
#   PUSH_HOLD_SCOPE          (${GITHUB_JOB:-local})  recover only this job's refs
#   PUSH_HOLD_TRIES          (3)
#   PUSH_HOLD_KEEP_WORKTREE  (0)  1: unstage held paths but keep their worktree bytes
#   PUSH_HOLD_LIST_MAX       (20) annotations per kind; the step summary has the rest
#   PUSH_HOLD_PUSH_ALARM     (120 s + 1 s per 4 MiB held)
#
# State: ${RUNNER_TEMP:-${TMPDIR:-/tmp}}/push_hold.${GITHUB_RUN_ID:-0}.${PUSH_HOLD_SCOPE}
#   held ("ref<TAB>path"), recovered ("ref<TAB>path"), unreconciled (ref).
#
# Custody ref:
#   ${PUSH_HOLD_PREFIX}${PUSH_HOLD_SCOPE}/${GITHUB_RUN_ID:-0}-${GITHUB_RUN_ATTEMPT:-1}-<12 hex>
# Custody tree: MANIFEST, blobs/<i> (an under-limit row, its own blob and mode),
# parts/<i>/base + parts/<i>/NNN (an over-limit row that extends its HEAD blob)
# or parts/<i>/NNN (any other over-limit row).
#
# Every git call works on the whole staged set at once (one diff, one
# cat-file batch, one update-index, one reset), so a hold of thousands of
# engine paths costs seconds. A staged deletion in a held group is unstaged
# and reported; it is not custody, because there are no bytes to keep.
#
# Bash 3.2 (macOS runner): no mapfile, no associative arrays, no stat -c,
# no split -d, no cmp -n, no timeout. awk uses FILENAME == ARGV[1], never
# NR == FNR (an empty first file breaks that).
#
# Sourced by scripts/ci/us_board_commit.sh and
# scripts/ci/daily_engine_commit_outputs.sh (defines functions, runs nothing).
#   bash scripts/ci/push_hold.sh recover <group>...

_push_hold_defaults() {
  : "${PUSH_BLOB_LIMIT:=104857600}"
  : "${PUSH_HOLD_PART:=52428800}"
  : "${PUSH_HOLD_PREFIX:=refs/heads/push-hold/}"
  : "${PUSH_HOLD_SCOPE:=${GITHUB_JOB:-local}}"
  : "${PUSH_HOLD_TRIES:=3}"
  : "${PUSH_HOLD_KEEP_WORKTREE:=0}"
  : "${PUSH_HOLD_LIST_MAX:=20}"
}

_push_hold_state_var() {
  _push_hold_defaults
  local base run
  base=${RUNNER_TEMP:-${TMPDIR:-/tmp}}
  run=${GITHUB_RUN_ID:-0}
  case "$base" in
    /*) ;;
    *) base="$(pwd)/$base" ;;
  esac
  PUSH_HOLD_STATE="${base}/push_hold.${run}.${PUSH_HOLD_SCOPE}"
  return 0
}

_push_hold_prepare_state() {
  _push_hold_state_var || return 1
  mkdir -p "$PUSH_HOLD_STATE" || return 1
  return 0
}

# Scratch under the state dir. Never removes held, recovered, or unreconciled.
_push_hold_work_reset() {
  _push_hold_prepare_state || return 1
  case "$PUSH_HOLD_STATE" in
    *push_hold.*) ;;
    *) return 1 ;;
  esac
  rm -rf "$PUSH_HOLD_STATE/work"
  mkdir -p "$PUSH_HOLD_STATE/work" || return 1
  PUSH_HOLD_WORK="$PUSH_HOLD_STATE/work"
  PUSH_HOLD_INDEX="$PUSH_HOLD_WORK/index"
  return 0
}

_push_hold_summary() {
  [ -n "${GITHUB_STEP_SUMMARY:-}" ] || return 0
  printf '%s\n' "$1" >> "${GITHUB_STEP_SUMMARY}" || true
  return 0
}

_push_hold_summary_file() {
  [ -n "${GITHUB_STEP_SUMMARY:-}" ] || return 0
  [ -s "$1" ] || return 0
  cat "$1" >> "${GITHUB_STEP_SUMMARY}" || true
  return 0
}

_push_hold_filesize() {
  local n
  n=$(wc -c < "$1") || return 1
  n=${n#"${n%%[![:space:]]*}"}
  n=${n%"${n##*[![:space:]]}"}
  printf '%s' "$n"
}

# Group members, one "group<TAB>member" line each, in $PUSH_HOLD_WORK/members.
# A path is in a group when it equals a member or is under member/.
_push_hold_members() {
  local i=0 g m noglob=0 IFS=$' \t\n'
  case $- in
    *f*) noglob=1 ;;
  esac
  set -f
  if ! : > "$PUSH_HOLD_WORK/members"; then
    [ "$noglob" -eq 1 ] || set +f
    return 1
  fi
  for g in "$@"; do
    i=$((i + 1))
    for m in $g; do
      while :; do
        case "$m" in
          */) m=${m%/} ;;
          *) break ;;
        esac
      done
      [ -n "$m" ] || continue
      printf '%s\t%s\n' "$i" "$m" >> "$PUSH_HOLD_WORK/members"
    done
  done
  [ "$noglob" -eq 1 ] || set +f
  printf '%s\n' "$i" > "$PUSH_HOLD_WORK/group.count"
  return 0
}

# Staged rows of the index against HEAD (or against commit $1), in
# $PUSH_HOLD_WORK/meta:
#   status, blob, size, head blob ("-" when HEAD has no file), over, mode, path
# The blob and mode of a deletion are HEAD's. size is "?" when the object
# cannot be read; such a row counts as over. An unmerged row counts as over.
_push_hold_scan() {
  if [ -n "${1:-}" ]; then
    git diff --cached --raw -z --no-abbrev --no-renames "$1" -- > "$PUSH_HOLD_WORK/raw" || return 1
  else
    git diff --cached --raw -z --no-abbrev --no-renames > "$PUSH_HOLD_WORK/raw" || return 1
  fi
  perl -e '
    $/ = "\0";
    while (defined(my $m = <STDIN>)) {
      chomp $m;
      next if $m eq "";
      my $p = <STDIN>;
      exit 3 unless defined $p;
      chomp $p;
      $m =~ /^:([0-7]+) ([0-7]+) ([0-9a-f]+) ([0-9a-f]+) ([A-Z])[0-9]*$/ or exit 4;
      my ($om, $nm, $os, $ns, $st) = ($1, $2, $3, $4, $5);
      exit 5 if $p eq "" || $p =~ /[\t\n\r]/;
      my ($sha, $mode) = $st eq "D" ? ($os, $om) : ($ns, $nm);
      my $head = ($os =~ /^0+$/) ? "-" : $os;
      print "$st\t$sha\t$head\t$mode\t$p\n";
    }
  ' < "$PUSH_HOLD_WORK/raw" > "$PUSH_HOLD_WORK/rows" || return 1
  cut -f2 "$PUSH_HOLD_WORK/rows" \
    | git cat-file --batch-check='%(objectname) %(objecttype) %(objectsize)' \
    > "$PUSH_HOLD_WORK/objinfo" || return 1
  PUSH_BLOB_LIMIT="$PUSH_BLOB_LIMIT" awk -F'\t' '
    BEGIN { OFS = "\t"; limit = ENVIRON["PUSH_BLOB_LIMIT"] + 0 }
    FILENAME == ARGV[1] { n1++; info[n1] = $0; next }
    {
      n2++
      split(info[n2], o, " ")
      st = $1; sha = $2; head = $3; mode = $4; path = $5
      size = "?"
      if (o[2] != "missing" && o[3] != "") size = o[3]
      over = 0
      if (st == "U") over = 1
      else if (st != "D" && (mode == "100644" || mode == "100755")) {
        if (size == "?" || o[2] != "blob" || size + 0 > limit) over = 1
      }
      print st, sha, size, head, over, mode, path
    }
    END { if (n1 != n2) exit 1 }
  ' "$PUSH_HOLD_WORK/objinfo" "$PUSH_HOLD_WORK/rows" > "$PUSH_HOLD_WORK/meta" || return 1
  return 0
}

# 0 when the index has a staged blob over PUSH_BLOB_LIMIT (or one that cannot
# be read). With $1, the index is compared with commit $1 instead of HEAD, so
# blobs already committed since $1 count too. Fails closed: 0 when the staged
# set cannot be scanned.
push_hold_staged_over() {
  _push_hold_work_reset || return 0
  _push_hold_scan "${1:-}" || return 0
  awk -F'\t' '$5 == "1" { f = 1 } END { exit f ? 0 : 1 }' "$PUSH_HOLD_WORK/meta"
}

# 0 when this run has held a path.
push_hold_held() {
  _push_hold_state_var || return 1
  [ -s "$PUSH_HOLD_STATE/held" ]
}

# Rebuild one custody entry into $4. Layout is blob, prefix, or whole.
_push_hold_append_parts() {
  local treeish="$1" i="$2" dest="$3" name
  git ls-tree --name-only "${treeish}:parts/${i}" > "$PUSH_HOLD_WORK/partnames" || return 1
  LC_ALL=C sort -o "$PUSH_HOLD_WORK/partnames.sorted" "$PUSH_HOLD_WORK/partnames" || return 1
  while IFS= read -r name <&3; do
    [ -n "$name" ] || continue
    [ "$name" = "base" ] && continue
    git cat-file blob "${treeish}:parts/${i}/${name}" >> "$dest" || return 1
  done 3< "$PUSH_HOLD_WORK/partnames.sorted"
  return 0
}

_push_hold_rebuild_to() {
  local treeish="$1" i="$2" layout="$3" dest="$4"
  case "$layout" in
    blob)
      git cat-file blob "${treeish}:blobs/${i}" > "$dest" || return 1
      ;;
    prefix)
      git cat-file blob "${treeish}:parts/${i}/base" > "$dest" || return 1
      _push_hold_append_parts "$treeish" "$i" "$dest" || return 1
      ;;
    whole)
      : > "$dest"
      _push_hold_append_parts "$treeish" "$i" "$dest" || return 1
      ;;
    *)
      return 1
      ;;
  esac
  return 0
}

# Append PUSH_HOLD_PART chunks of $1 as $2/000, $2/001, ... to the private index.
_push_hold_add_chunks() {
  local src="$1" treepath="$2" total n offset sha name csize
  total=$(_push_hold_filesize "$src") || return 1
  [ "$total" -gt 0 ] || return 0
  n=0
  offset=0
  while [ "$offset" -lt "$total" ]; do
    name=$(printf '%03d' "$n")
    dd if="$src" of="$PUSH_HOLD_WORK/chunk" bs="$PUSH_HOLD_PART" skip="$n" count=1 2>/dev/null || true
    csize=$(_push_hold_filesize "$PUSH_HOLD_WORK/chunk") || return 1
    [ "$csize" -gt 0 ] || return 1
    sha=$(git hash-object -w "$PUSH_HOLD_WORK/chunk") || return 1
    GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git update-index --add --cacheinfo "100644,${sha},${treepath}/${name}" || return 1
    n=$((n + 1))
    offset=$((offset + csize))
  done
  [ "$offset" -eq "$total" ] || return 1
  return 0
}

# $1 commit, $2 ref, $3 alarm seconds.
_push_hold_push_ref() {
  local commit="$1" ref="$2" alarm="${3:-120}" try=1 line remote_sha
  while [ "$try" -le "$PUSH_HOLD_TRIES" ]; do
    if perl -e 'alarm shift; exec @ARGV or die' "$alarm" git push origin "${commit}:${ref}"; then
      line=$(git ls-remote origin "$ref" 2>/dev/null) || line=""
      remote_sha=${line%%$'\t'*}
      if [ -n "$remote_sha" ] && [ "$remote_sha" = "$commit" ]; then
        return 0
      fi
    fi
    try=$((try + 1))
  done
  echo "::error title=hold custody failed::${ref} was not verified on origin after ${PUSH_HOLD_TRIES} tries"
  return 2
}

# 0 when $2's bytes start with $1's bytes (the held row is already on HEAD).
_push_hold_file_is_prefix() {
  local pre="$1" full="$2" ps fs a b
  ps=$(_push_hold_filesize "$pre") || return 1
  fs=$(_push_hold_filesize "$full") || return 1
  [ "$fs" -ge "$ps" ] || return 1
  head -c "$ps" "$full" > "$PUSH_HOLD_WORK/hpfx" || return 1
  a=$(git hash-object "$PUSH_HOLD_WORK/hpfx") || return 1
  b=$(git hash-object "$pre") || return 1
  [ "$a" = "$b" ]
}

_push_hold_mark_unreconciled() {
  local ref="$1" reason="$2" msg
  printf '%s\n' "$ref" >> "$PUSH_HOLD_STATE/unreconciled"
  msg="${ref}: ${reason}. The ref is kept."
  echo "::error title=held rows not restored::${msg}"
  _push_hold_summary "$msg"
  return 0
}

_push_hold_record_recovered() {
  local n="$1" ref
  ref=$(cat "$PUSH_HOLD_WORK/ref.$n") || return 1
  awk -F'\t' -v ref="$ref" '$2 != "" { print ref "\t" $2 }' "$PUSH_HOLD_WORK/ent.$n" \
    >> "$PUSH_HOLD_STATE/recovered" || return 1
  return 0
}

_push_hold_delete_remote() {
  local ref="$1" line
  perl -e 'alarm 120; exec @ARGV or die' -- git push origin --delete "$ref" || true
  line=$(git ls-remote origin "$ref" 2>/dev/null) || return 1
  [ -z "$line" ] || return 1
  return 0
}

# Checks the MANIFEST of ref $1 into ent.$1 ("i path blob size head layout")
# and from.$1. On a bad manifest: st.$1 = bad, why.$1 = the reason.
_push_hold_parse_manifest() {
  local n="$1" why
  : > "$PUSH_HOLD_WORK/ent.$n"
  : > "$PUSH_HOLD_WORK/from.$n"
  why=$(PH_ENT="$PUSH_HOLD_WORK/ent.$n" PH_FROM="$PUSH_HOLD_WORK/from.$n" awk -F'\t' '
    function bad(r) {
      if (!failed) print r
      failed = 1
      exit 1
    }
    function hex(s) { return s ~ /^[0-9a-f]+$/ && length(s) >= 40 }
    function plain(p,   a, c, k, lc) {
      if (p == "" || substr(p, 1, 1) == "/" || substr(p, length(p), 1) == "/") return 0
      if (index(p, "//") || index(p, "\r")) return 0
      c = split(p, a, "/")
      for (k = 1; k <= c; k++) {
        lc = tolower(a[k])
        if (lc == "." || lc == ".." || lc == ".git") return 0
      }
      return 1
    }
    function grouped(p,   k, m) {
      for (k = 1; k <= nm; k++) {
        m = gm[k]
        if (p == m || substr(p, 1, length(m) + 1) == m "/") return 1
      }
      return 0
    }
    FILENAME == ARGV[1] { gm[++nm] = $2; next }
    {
      ln++
      if (ln == 1) {
        if ($0 != "push-hold/v1") bad("manifest is not push-hold/v1")
        next
      }
      if ($1 == "entry") {
        if (NF != 7 || $2 == "" || $3 == "" || $4 == "" || $7 == "") bad("manifest entry is incomplete")
        if ($2 !~ /^[0-9]+$/ || $5 !~ /^[0-9]+$/ || !hex($4) || ($6 != "-" && !hex($6))) bad("manifest entry is malformed")
        if ($7 != "blob" && $7 != "prefix" && $7 != "whole") bad("manifest entry is malformed")
        if (!plain($3)) bad("entry " $3 " is not a plain repository path")
        if (($2 in seen_i) || ($3 in seen_p)) bad("manifest repeats an entry")
        seen_i[$2] = 1
        seen_p[$3] = 1
        if (!grouped($3)) bad("entry " $3 " belongs to no declared group")
        print $2 "\t" $3 "\t" $4 "\t" $5 "\t" $6 "\t" $7 > ENVIRON["PH_ENT"]
        next
      }
      if ($1 == "from") {
        if (NF != 2 || $2 == "") bad("manifest line not understood")
        print $2 > ENVIRON["PH_FROM"]
        next
      }
      if ($1 == "run" || $1 == "scope" || $1 == "head" || $0 == "") next
      bad("manifest line not understood")
    }
    END {
      if (failed) exit 1
      if (ln == 0) { print "manifest is not push-hold/v1"; exit 1 }
    }
  ' "$PUSH_HOLD_WORK/members" "$PUSH_HOLD_WORK/man.$n")
  if [ -n "$why" ]; then
    printf '%s\n' "$why" > "$PUSH_HOLD_WORK/why.$n"
    printf '%s\n' "bad" > "$PUSH_HOLD_WORK/st.$n"
    return 1
  fi
  printf '%s\n' "ok" > "$PUSH_HOLD_WORK/st.$n"
  return 0
}

# Restore ref $1's rows when HEAD is still each row's held base and the
# worktree there is clean; delete the ref when every row is already on HEAD.
_push_hold_apply_ref() {
  local n="$1" ref localref W why line i blob layout path dest got
  ref=$(cat "$PUSH_HOLD_WORK/ref.$n") || return 0
  localref=$(cat "$PUSH_HOLD_WORK/local.$n") || return 0
  W="$PUSH_HOLD_WORK/rb.$n"
  if [ ! -s "$PUSH_HOLD_WORK/ent.$n" ]; then
    _push_hold_mark_unreconciled "$ref" "manifest has no entries"
    return 0
  fi
  mkdir -p "$W" || {
    _push_hold_mark_unreconciled "$ref" "could not stage rebuilt bytes"
    return 0
  }
  # 1. Custody bytes. A blob entry is checked against the tree (the tree
  # entry id is the hash of its bytes); a chunked entry is rebuilt and hashed.
  if ! git ls-tree -r "$localref" -- blobs > "$W/tree"; then
    _push_hold_mark_unreconciled "$ref" "could not rebuild $(head -n 1 "$PUSH_HOLD_WORK/ent.$n" | cut -f2)"
    return 0
  fi
  why=$(awk -F'\t' '
    FILENAME == ARGV[1] { split($1, a, " "); got[$2] = a[3]; mode[$2] = a[1]; next }
    $6 == "blob" {
      k = "blobs/" $1
      if (!(k in got)) { print "could not rebuild " $2; exit }
      if (got[k] != $3) { print "rebuilt bytes for " $2 " do not match " $3; exit }
    }
  ' "$W/tree" "$PUSH_HOLD_WORK/ent.$n")
  if [ -n "$why" ]; then
    _push_hold_mark_unreconciled "$ref" "$why"
    return 0
  fi
  awk -F'\t' '$6 != "blob" { print $1 "\t" $3 "\t" $6 "\t" $2 }' "$PUSH_HOLD_WORK/ent.$n" > "$W/chunked"
  while IFS=$'\t' read -r i blob layout path <&3; do
    dest="$W/$i"
    if ! _push_hold_rebuild_to "$localref" "$i" "$layout" "$dest"; then
      _push_hold_mark_unreconciled "$ref" "could not rebuild ${path}"
      return 0
    fi
    got=$(git hash-object "$dest" 2>/dev/null) || got=""
    if [ "$got" != "$blob" ]; then
      _push_hold_mark_unreconciled "$ref" "rebuilt bytes for ${path} do not match ${blob}"
      return 0
    fi
  done 3< "$W/chunked"

  # 2. HEAD for every entry, one batch: base check and landed check.
  awk -F'\t' '{ print "HEAD:" $2 }' "$PUSH_HOLD_WORK/ent.$n" \
    | git cat-file --batch-check='%(objectname) %(objecttype) %(objectsize)' > "$W/headinfo" 2>/dev/null || {
    _push_hold_mark_unreconciled "$ref" "HEAD for $(head -n 1 "$PUSH_HOLD_WORK/ent.$n" | cut -f2) does not match the held base"
    return 0
  }
  awk -F'\t' '
    FILENAME == ARGV[1] { h++; info[h] = $0; next }
    {
      e++
      c = split(info[e], o, " ")
      present = (c >= 3 && o[c - 1] == "blob")
      hsha = present ? o[1] : ""
      hsize = present ? o[3] + 0 : -1
      if (c >= 2 && o[c] == "missing") present = 0
      if ($5 == "-") base = (o[c] == "missing")
      else base = (present && hsha == $5)
      if (present && hsha == $3) landed = "yes"
      else if (present && hsize > $4 + 0) landed = "maybe"
      else landed = "no"
      print $1 "\t" $3 "\t" $6 "\t" base "\t" landed "\t" $2
    }
    END { if (h != e) exit 1 }
  ' "$W/headinfo" "$PUSH_HOLD_WORK/ent.$n" > "$W/state" || {
    _push_hold_mark_unreconciled "$ref" "HEAD for $(head -n 1 "$PUSH_HOLD_WORK/ent.$n" | cut -f2) does not match the held base"
    return 0
  }
  if ! awk -F'\t' '$5 == "no" { f = 1 } END { exit f ? 0 : 1 }' "$W/state"; then
    # No entry is plainly unlanded: check the extended ones byte for byte.
    local all_landed=1
    awk -F'\t' '$5 == "maybe" { print $1 "\t" $2 "\t" $3 "\t" $6 }' "$W/state" > "$W/maybe"
    while IFS=$'\t' read -r i blob layout path <&3; do
      dest="$W/$i"
      if [ "$layout" = "blob" ]; then
        git cat-file blob "$blob" > "$dest" 2>/dev/null || { all_landed=0; break; }
      fi
      git cat-file blob "HEAD:${path}" > "$W/headbytes" 2>/dev/null || { all_landed=0; break; }
      if ! _push_hold_file_is_prefix "$dest" "$W/headbytes"; then
        all_landed=0
        break
      fi
    done 3< "$W/maybe"
    if [ "$all_landed" -eq 1 ]; then
      if _push_hold_delete_remote "$ref"; then
        echo "hold ${ref} already landed on HEAD; deleted ${ref}"
      else
        echo "::warning title=hold ref remains::${ref} already landed on HEAD but the ref is still on origin"
      fi
      return 0
    fi
  fi
  why=$(awk -F'\t' '$4 != "1" { print "HEAD for " $6 " does not match the held base"; exit }' "$W/state")
  if [ -n "$why" ]; then
    _push_hold_mark_unreconciled "$ref" "$why"
    return 0
  fi

  # 3. Clean worktree and index at every entry: a tracked path holds HEAD's
  # bytes in a regular file, an untracked one is absent.
  awk -F'\t' '{ print $2 }' "$PUSH_HOLD_WORK/ent.$n" > "$W/paths"
  perl -ne 'chomp; print(((-l $_) ? "L" : (-f $_) ? "F" : (-e $_) ? "O" : "N"), "\n")' "$W/paths" > "$W/kind" || {
    _push_hold_mark_unreconciled "$ref" "worktree is dirty for $(head -n 1 "$W/paths")"
    return 0
  }
  awk -F'\t' 'FILENAME == ARGV[1] { k++; kind[k] = $0; next } { e++; if ($5 != "-" && kind[e] == "F") print $2 }' \
    "$W/kind" "$PUSH_HOLD_WORK/ent.$n" > "$W/hashpaths"
  : > "$W/hashes"
  if [ -s "$W/hashpaths" ]; then
    git hash-object --no-filters --stdin-paths < "$W/hashpaths" > "$W/hashes" 2>/dev/null || : > "$W/hashes"
  fi
  git diff-index --cached --name-only -z HEAD 2>/dev/null | tr '\0' '\n' > "$W/indexdirty" || true
  why=$(awk -F'\t' '
    FILENAME == ARGV[1] { k++; kind[k] = $0; next }
    FILENAME == ARGV[2] { hp++; hpath[hp] = $0; next }
    FILENAME == ARGV[3] { hh++; hash[hpath[hh]] = $0; next }
    FILENAME == ARGV[4] { staged[$0] = 1; next }
    {
      e++
      dirty = 0
      if ($2 in staged) dirty = 1
      else if ($5 == "-") dirty = (kind[e] != "N")
      else if (kind[e] != "F") dirty = 1
      else if (!($2 in hash) || hash[$2] != $5) dirty = 1
      if (dirty) { print "worktree is dirty for " $2; exit }
    }
  ' "$W/kind" "$W/hashpaths" "$W/hashes" "$W/indexdirty" "$PUSH_HOLD_WORK/ent.$n")
  if [ -n "$why" ]; then
    _push_hold_mark_unreconciled "$ref" "$why"
    return 0
  fi

  # 4. Write. Blob entries through a private index (mode from the custody
  # tree), chunked entries from their rebuilt files; then hash every path.
  awk -F'\t' '
    FILENAME == ARGV[1] { split($1, a, " "); mode[$2] = a[1]; next }
    $6 == "blob" { m = mode["blobs/" $1]; if (m != "100755") m = "100644"; print m " " $3 "\t" $2 }
  ' "$W/tree" "$PUSH_HOLD_WORK/ent.$n" > "$W/indexinfo"
  why=""
  if [ -s "$W/indexinfo" ]; then
    rm -f "$W/idx"
    if ! GIT_INDEX_FILE="$W/idx" git read-tree --empty \
      || ! GIT_INDEX_FILE="$W/idx" git update-index --index-info < "$W/indexinfo" \
      || ! GIT_INDEX_FILE="$W/idx" git checkout-index -a -f; then
      why="could not write $(head -n 1 "$W/indexinfo" | cut -f2)"
    fi
  fi
  if [ -z "$why" ]; then
    while IFS=$'\t' read -r i blob layout path <&3; do
      mkdir -p -- "$(dirname -- "$path")" 2>/dev/null || true
      if ! cat "$W/$i" > "$path"; then
        why="could not write ${path}"
        break
      fi
    done 3< "$W/chunked"
  fi
  if [ -z "$why" ]; then
    git hash-object --no-filters --stdin-paths < "$W/paths" > "$W/written" 2>/dev/null || : > "$W/written"
    why=$(awk -F'\t' '
      FILENAME == ARGV[1] { w++; got[w] = $0; next }
      { e++; if (got[e] != $3) { print "wrote " $2 " but bytes do not match " $3; exit } }
    ' "$W/written" "$PUSH_HOLD_WORK/ent.$n")
  fi
  if [ -n "$why" ]; then
    # Put back what HEAD had, so a failed restore leaves no half-written rows.
    awk -F'\t' '$5 != "-" { print $2 }' "$PUSH_HOLD_WORK/ent.$n" | tr '\n' '\0' > "$W/back.nul"
    if [ -s "$W/back.nul" ]; then
      git --literal-pathspecs checkout -q HEAD --pathspec-from-file="$W/back.nul" --pathspec-file-nul 2>/dev/null || true
    fi
    while IFS= read -r path <&3; do
      rm -f -- "$path" || true
    done 3< <(awk -F'\t' '$5 == "-" { print $2 }' "$PUSH_HOLD_WORK/ent.$n")
    _push_hold_mark_unreconciled "$ref" "$why"
    return 0
  fi
  _push_hold_record_recovered "$n" || _push_hold_mark_unreconciled "$ref" "could not record recovery"
  return 0
}

_push_hold_recover_impl() {
  local ls_out line ref tail localref n i a b st why
  _push_hold_state_var || return 0
  ls_out=$(git ls-remote origin "${PUSH_HOLD_PREFIX}${PUSH_HOLD_SCOPE}/*" 2>/dev/null) || {
    _push_hold_prepare_state || return 0
    printf '%s\n' "ls-remote" >> "$PUSH_HOLD_STATE/unreconciled"
    echo "::error title=held rows not restored::ls-remote failed for ${PUSH_HOLD_PREFIX}${PUSH_HOLD_SCOPE}. The ref is kept."
    _push_hold_summary "ls-remote failed for ${PUSH_HOLD_PREFIX}${PUSH_HOLD_SCOPE}. The ref is kept."
    return 0
  }
  [ -n "$ls_out" ] || return 0
  _push_hold_work_reset || return 0
  _push_hold_members "$@" || return 0
  printf '%s\n' "$ls_out" > "$PUSH_HOLD_WORK/lsremote"
  n=0
  while IFS= read -r line <&3; do
    [ -n "$line" ] || continue
    ref=${line#*$'\t'}
    [ -n "$ref" ] || continue
    n=$((n + 1))
    printf '%s\n' "$ref" > "$PUSH_HOLD_WORK/ref.$n"
    : > "$PUSH_HOLD_WORK/ent.$n"
    : > "$PUSH_HOLD_WORK/from.$n"
    case "$ref" in
      refs/heads/*) tail=${ref#refs/heads/} ;;
      *) tail=$ref ;;
    esac
    localref="refs/${tail}"
    printf '%s\n' "$localref" > "$PUSH_HOLD_WORK/local.$n"
    if ! git fetch -q --no-tags origin "+${ref}:${localref}"; then
      printf '%s\n' "bad" > "$PUSH_HOLD_WORK/st.$n"
      printf '%s\n' "fetch failed" > "$PUSH_HOLD_WORK/why.$n"
      continue
    fi
    if ! git cat-file blob "${localref}:MANIFEST" > "$PUSH_HOLD_WORK/man.$n" 2>/dev/null; then
      printf '%s\n' "bad" > "$PUSH_HOLD_WORK/st.$n"
      printf '%s\n' "MANIFEST unreadable" > "$PUSH_HOLD_WORK/why.$n"
      continue
    fi
    _push_hold_parse_manifest "$n" || true
  done 3< "$PUSH_HOLD_WORK/lsremote"
  printf '%s\n' "$n" > "$PUSH_HOLD_WORK/ref.count"
  [ "$n" -gt 0 ] || return 0

  # A ref named by another good ref's `from` line is superseded by it.
  : > "$PUSH_HOLD_WORK/super_names"
  i=1
  while [ "$i" -le "$n" ]; do
    if [ "$(cat "$PUSH_HOLD_WORK/st.$i")" = "ok" ]; then
      cat "$PUSH_HOLD_WORK/from.$i" >> "$PUSH_HOLD_WORK/super_names"
    fi
    i=$((i + 1))
  done
  i=1
  while [ "$i" -le "$n" ]; do
    if [ "$(cat "$PUSH_HOLD_WORK/st.$i")" = "ok" ]; then
      ref=$(cat "$PUSH_HOLD_WORK/ref.$i")
      if grep -qxF -- "$ref" "$PUSH_HOLD_WORK/super_names"; then
        printf '%s\n' "super" > "$PUSH_HOLD_WORK/st.$i"
      fi
    fi
    i=$((i + 1))
  done

  # Two live refs that hold the same path cannot both be restored.
  : > "$PUSH_HOLD_WORK/allent"
  i=1
  while [ "$i" -le "$n" ]; do
    if [ "$(cat "$PUSH_HOLD_WORK/st.$i")" = "ok" ]; then
      awk -F'\t' -v n="$i" '{ print n "\t" $2 }' "$PUSH_HOLD_WORK/ent.$i" >> "$PUSH_HOLD_WORK/allent"
    fi
    i=$((i + 1))
  done
  awk -F'\t' '
    {
      if (($2 in owner) && owner[$2] != $1) {
        k = owner[$2] "\t" $1
        if (!(k in seen)) { seen[k] = 1; print k }
      } else if (!($2 in owner)) owner[$2] = $1
    }
  ' "$PUSH_HOLD_WORK/allent" > "$PUSH_HOLD_WORK/clashes"
  while IFS=$'\t' read -r a b <&3; do
    [ -n "$a" ] && [ -n "$b" ] || continue
    printf '%s\n' "clash" > "$PUSH_HOLD_WORK/st.$a"
    printf '%s\n' "clash" > "$PUSH_HOLD_WORK/st.$b"
    printf '%s\n' "shares a path with $(cat "$PUSH_HOLD_WORK/ref.$b")" > "$PUSH_HOLD_WORK/why.$a"
    printf '%s\n' "shares a path with $(cat "$PUSH_HOLD_WORK/ref.$a")" > "$PUSH_HOLD_WORK/why.$b"
  done 3< "$PUSH_HOLD_WORK/clashes"

  i=1
  while [ "$i" -le "$n" ]; do
    st=$(cat "$PUSH_HOLD_WORK/st.$i")
    ref=$(cat "$PUSH_HOLD_WORK/ref.$i")
    case "$st" in
      super)
        _push_hold_record_recovered "$i" || _push_hold_mark_unreconciled "$ref" "could not record a superseded ref"
        ;;
      ok)
        _push_hold_apply_ref "$i"
        ;;
      *)
        why=$(cat "$PUSH_HOLD_WORK/why.$i" 2>/dev/null) || why=""
        [ -n "$why" ] || why="unreconciled"
        _push_hold_mark_unreconciled "$ref" "$why"
        ;;
    esac
    i=$((i + 1))
  done
  return 0
}

# Always returns 0. set -e is restored to whatever the caller had.
push_hold_recover() {
  local flags
  flags=$-
  set +e
  _push_hold_recover_impl "$@"
  case "$flags" in
    *e*) set -e ;;
  esac
  return 0
}

# Delete each recovered ref whose every path is either in the pushed range or
# held again in this run. With $1, the pushed range is $1..HEAD; without it,
# the files of HEAD's own commit when HEAD moved since the hold check.
push_hold_settle() {
  local base="${1:-}" before now b ref ok
  _push_hold_state_var || return 0
  [ -s "$PUSH_HOLD_STATE/recovered" ] || return 0
  : > "$PUSH_HOLD_STATE/pushed_names"
  now=$(git rev-parse HEAD 2>/dev/null) || now=""
  if [ -n "$base" ]; then
    b=$(git rev-parse --verify -q "${base}^{commit}" 2>/dev/null) || b=""
    if [ -n "$b" ] && [ -n "$now" ] && [ "$b" != "$now" ]; then
      git diff --name-only -z --no-renames "$b" "$now" 2>/dev/null | tr '\0' '\n' > "$PUSH_HOLD_STATE/pushed_names" \
        || : > "$PUSH_HOLD_STATE/pushed_names"
    fi
  elif [ -f "$PUSH_HOLD_STATE/head_before" ]; then
    before=$(cat "$PUSH_HOLD_STATE/head_before") || before=""
    if [ -n "$before" ] && [ -n "$now" ] && [ "$now" != "$before" ]; then
      git diff-tree --no-commit-id --name-only -z -r HEAD 2>/dev/null | tr '\0' '\n' > "$PUSH_HOLD_STATE/pushed_names" \
        || : > "$PUSH_HOLD_STATE/pushed_names"
    fi
  fi
  [ -f "$PUSH_HOLD_STATE/held" ] || : > "$PUSH_HOLD_STATE/held"
  awk -F'\t' '
    FILENAME == ARGV[1] { pushed[$0] = 1; next }
    FILENAME == ARGV[2] { held[$2] = 1; next }
    $1 != "" {
      if (!($1 in ok)) { order[++n] = $1; ok[$1] = 1 }
      if (!(($2 in pushed) || ($2 in held))) ok[$1] = 0
    }
    END { for (i = 1; i <= n; i++) print order[i] "\t" ok[order[i]] }
  ' "$PUSH_HOLD_STATE/pushed_names" "$PUSH_HOLD_STATE/held" "$PUSH_HOLD_STATE/recovered" \
    > "$PUSH_HOLD_STATE/settle_refs" || return 0
  while IFS=$'\t' read -r ref ok <&3; do
    [ -n "$ref" ] || continue
    if [ "$ok" != "1" ]; then
      echo "::warning title=hold ref kept::${ref} has a path that is neither in the pushed commit nor held again"
      continue
    fi
    if _push_hold_delete_remote "$ref"; then
      echo "hold settled ${ref}"
    else
      echo "::warning title=hold ref remains::${ref} delete did not verify"
    fi
  done 3< "$PUSH_HOLD_STATE/settle_refs"
  return 0
}

# 0 (true) when this run held a path or left a ref unreconciled.
push_hold_red() {
  _push_hold_state_var || return 1
  if [ -s "$PUSH_HOLD_STATE/held" ] || [ -s "$PUSH_HOLD_STATE/unreconciled" ]; then
    return 0
  fi
  return 1
}

# Hold every staged member of each group that has an over-limit blob, that
# was held earlier in this run, or that shares a held lineage with a held
# path. Returns 0 when nothing needed holding or the hold is in custody on
# origin and unstaged; 2 when custody could not be secured (nothing reverted).
push_hold_oversize_staged() {
  local W i sha size head path layout head_size pfx_hash headsha tree commit ref
  local blob total alarm bad nheld reset_failed=0
  _push_hold_work_reset || {
    echo "::error title=hold custody failed::could not create the hold state dir"
    return 2
  }
  W=$PUSH_HOLD_WORK
  _push_hold_members "$@" || {
    echo "::error title=hold custody failed::could not record the groups"
    return 2
  }
  if ! _push_hold_scan; then
    echo "::error title=hold custody failed::could not read the staged paths (a path with a tab or newline, an unreadable index, or a git error)"
    return 2
  fi
  [ -f "$PUSH_HOLD_STATE/held" ] || : > "$PUSH_HOLD_STATE/held"
  [ -f "$PUSH_HOLD_STATE/recovered" ] || : > "$PUSH_HOLD_STATE/recovered"
  if ! awk -F'\t' '$5 == "1" { f = 1 } END { exit f ? 0 : 1 }' "$W/meta" && [ ! -s "$PUSH_HOLD_STATE/held" ]; then
    if [ -s "$PUSH_HOLD_STATE/recovered" ]; then
      git rev-parse HEAD > "$PUSH_HOLD_STATE/head_before" || return 2
    fi
    return 0
  fi
  {
    awk -F'\t' '$1 != "" && $1 != "-" { print "r\t" $1 "\t" $2 }' "$PUSH_HOLD_STATE/recovered"
    awk -F'\t' '$1 != "" && $1 != "-" { print "h\t" $1 "\t" $2 }' "$PUSH_HOLD_STATE/held"
  } > "$W/lineage"

  # One pass picks the held set. take: i, status, blob, size, head, over,
  # mode, cause, path (i is "-" for a deletion, which has no custody entry).
  PUSH_HOLD_LIST_MAX="$PUSH_HOLD_LIST_MAX" PH_TAKE="$W/take" PH_FROM="$W/from_refs" PH_MSG="$W/premsg" PH_SUM="$W/presum" awk -F'\t' '
    function groups_of(p,   k, m, s) {
      s = ""
      for (k = 1; k <= nm; k++) {
        m = gm[k]
        if (p == m || substr(p, 1, length(m) + 1) == m "/") s = s " " gg[k]
      }
      return s
    }
    function heat(gs, cause,   c, a, k) {
      c = split(gs, a, " ")
      for (k = 1; k <= c; k++) {
        if (!(a[k] in hot)) { hot[a[k]] = cause; changed = 1 }
      }
    }
    function is_hot(gs,   c, a, k) {
      c = split(gs, a, " ")
      for (k = 1; k <= c; k++) if (a[k] in hot) return a[k]
      return ""
    }
    BEGIN { max = ENVIRON["PUSH_HOLD_LIST_MAX"] + 0; if (max < 1) max = 1 }
    FILENAME == ARGV[1] { nm++; gg[nm] = $1; gm[nm] = $2; next }
    FILENAME == ARGV[2] {
      nl++; lk[nl] = $1; lr[nl] = $2; lp[nl] = $3
      if (!($2 in lseen)) { lseen[$2] = 1; lorder[++nr] = $2 }
      next
    }
    {
      n++
      st[n] = $1; sha[n] = $2; size[n] = $3; head[n] = $4; over[n] = $5; mode[n] = $6; path[n] = $7
      at[$7] = n
      grp[n] = groups_of($7)
      if (grp[n] == "") ung[++nu] = $7
    }
    END {
      for (l = 1; l <= nl; l++) {
        lg[l] = groups_of(lp[l])
        if (lg[l] == "" && lk[l] == "h") ung[++nu] = lp[l]
      }
      if (nu > 0) {
        for (i = 1; i <= n; i++) { take[i] = 1; cause[i] = "its group membership is not proved" }
        for (u = 1; u <= nu && u <= max; u++)
          print "::error title=hold membership not proved::" ung[u] " belongs to no declared group; holding every staged path" > ENVIRON["PH_MSG"]
        if (nu > max)
          print "::error title=hold membership not proved::" (nu - max) " more paths belong to no declared group; holding every staged path" > ENVIRON["PH_MSG"]
        for (u = 1; u <= nu; u++)
          print "- `" ung[u] "` belongs to no declared group; holding every staged path" > ENVIRON["PH_SUM"]
      } else {
        for (i = 1; i <= n; i++) if (over[i] == "1") heat(grp[i], path[i] " is over the limit")
        for (l = 1; l <= nl; l++) if (lk[l] == "h") heat(lg[l], lp[l] " was withheld earlier in this run")
        changed = 1
        while (changed) {
          changed = 0
          for (i = 1; i <= n; i++) {
            if (take[i]) continue
            g = is_hot(grp[i])
            if (g != "") { take[i] = 1; cause[i] = hot[g] }
          }
          for (l = 1; l <= nl; l++) {
            if (!(lp[l] in at) || !take[at[lp[l]]]) continue
            for (m = 1; m <= nl; m++)
              if (lr[m] == lr[l]) heat(lg[m], lp[m] " shares a held lineage with " lr[l])
          }
        }
      }
      k = 0
      for (i = 1; i <= n; i++) {
        if (!take[i]) continue
        if (st[i] == "D") idx = "-"
        else { idx = k; k++ }
        printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", idx, st[i], sha[i], size[i], head[i], over[i], mode[i], cause[i], path[i] > ENVIRON["PH_TAKE"]
      }
      for (r = 1; r <= nr; r++) {
        ref = lorder[r]; all = 1; some = 0
        for (l = 1; l <= nl; l++) {
          if (lr[l] != ref) continue
          if ((lp[l] in at) && take[at[lp[l]]]) some = 1
          else all = 0
        }
        if (some && all) print ref > ENVIRON["PH_FROM"]
        else if (some) print "::warning title=hold lineage split::" ref " has rows that are not held again; it is kept, and the next recovery reports both refs as sharing a path" > ENVIRON["PH_MSG"]
      }
    }
  ' "$W/members" "$W/lineage" "$W/meta" || {
    echo "::error title=hold custody failed::could not pick the held set"
    return 2
  }
  [ -f "$W/take" ] || : > "$W/take"
  [ -f "$W/from_refs" ] || : > "$W/from_refs"
  [ -f "$W/premsg" ] && cat "$W/premsg"
  if [ ! -s "$W/take" ]; then
    if awk -F'\t' '$5 == "1" { f = 1 } END { exit f ? 0 : 1 }' "$W/meta"; then
      echo "::error title=hold custody failed::an over-limit path produced an empty hold set"
      return 2
    fi
    if [ -s "$PUSH_HOLD_STATE/recovered" ]; then
      git rev-parse HEAD > "$PUSH_HOLD_STATE/head_before" || return 2
    fi
    return 0
  fi
  git rev-parse HEAD > "$PUSH_HOLD_STATE/head_before" || {
    echo "::error title=hold custody failed::could not read HEAD"
    return 2
  }
  bad=$(awk -F'\t' '
    $2 == "D" { next }
    $4 == "?" { print "could not read the staged blob for " $9; exit }
    $7 != "100644" && $7 != "100755" { print "cannot keep " $9 ": mode " $7; exit }
    $6 == "1" && $7 != "100644" { print "cannot keep " $9 ": mode " $7; exit }
  ' "$W/take")
  if [ -n "$bad" ]; then
    echo "::error title=hold custody failed::${bad}"
    return 2
  fi

  ref="-"
  if awk -F'\t' '$2 != "D" { f = 1 } END { exit f ? 0 : 1 }' "$W/take"; then
    rm -f "$PUSH_HOLD_INDEX"
    GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git read-tree --empty || {
      echo "::error title=hold custody failed::could not start a private index"
      return 2
    }
    awk -F'\t' '$2 != "D" && $6 != "1" { print $7 " " $3 "\tblobs/" $1 }' "$W/take" > "$W/blobinfo"
    if [ -s "$W/blobinfo" ]; then
      GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git update-index --index-info < "$W/blobinfo" || {
        echo "::error title=hold custody failed::could not index the held blobs"
        return 2
      }
    fi
    awk -F'\t' '$2 != "D" && $6 == "1" { print $1 "\t" $3 "\t" $4 "\t" $5 "\t" $9 }' "$W/take" > "$W/overs"
    : > "$W/layouts"
    while IFS=$'\t' read -r i sha size head path <&3; do
      git cat-file blob "$sha" > "$W/staged_bytes" || {
        echo "::error title=hold custody failed::could not read staged bytes for ${path}"
        return 2
      }
      layout=whole
      if [ "$head" != "-" ]; then
        head_size=$(git cat-file -s "$head" 2>/dev/null) || head_size=""
        if [ -n "$head_size" ] && [ "$size" -ge "$head_size" ]; then
          head -c "$head_size" "$W/staged_bytes" > "$W/pfx" || return 2
          pfx_hash=$(git hash-object "$W/pfx") || return 2
          if [ "$pfx_hash" = "$head" ]; then
            layout=prefix
          fi
        fi
      fi
      if [ "$layout" = "prefix" ]; then
        GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git update-index --add --cacheinfo "100644,${head},parts/${i}/base" || return 2
        # Byte head_size+1 is the first byte of the suffix (tail -c is 1-based).
        tail -c "+$((head_size + 1))" "$W/staged_bytes" > "$W/suffix" || return 2
        _push_hold_add_chunks "$W/suffix" "parts/${i}" || {
          echo "::error title=hold custody failed::could not chunk ${path}"
          return 2
        }
      else
        _push_hold_add_chunks "$W/staged_bytes" "parts/${i}" || {
          echo "::error title=hold custody failed::could not chunk ${path}"
          return 2
        }
      fi
      rm -f "$W/staged_bytes" "$W/suffix" "$W/pfx"
      printf '%s\t%s\n' "$i" "$layout" >> "$W/layouts"
    done 3< "$W/overs"
    awk -F'\t' '
      FILENAME == ARGV[1] { lay[$1] = $2; next }
      $2 != "D" { l = ($1 in lay) ? lay[$1] : "blob"; print "entry\t" $1 "\t" $9 "\t" $3 "\t" $4 "\t" $5 "\t" l }
    ' "$W/layouts" "$W/take" > "$W/entries"
    headsha=$(git rev-parse HEAD) || {
      echo "::error title=hold custody failed::could not read HEAD"
      return 2
    }
    {
      printf '%s\n' "push-hold/v1"
      printf 'run\t%s-%s\n' "${GITHUB_RUN_ID:-0}" "${GITHUB_RUN_ATTEMPT:-1}"
      printf 'scope\t%s\n' "$PUSH_HOLD_SCOPE"
      printf 'head\t%s\n' "$headsha"
      cat "$W/entries"
      awk '$0 != "" { print "from\t" $0 }' "$W/from_refs"
    } > "$W/MANIFEST"
    blob=$(git hash-object -w "$W/MANIFEST") || {
      echo "::error title=hold custody failed::could not hash MANIFEST"
      return 2
    }
    GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git update-index --add --cacheinfo "100644,${blob},MANIFEST" || return 2
    tree=$(GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git write-tree) || {
      echo "::error title=hold custody failed::could not write the custody tree"
      return 2
    }
    commit=$(git commit-tree "$tree" -m "push-hold") || {
      echo "::error title=hold custody failed::could not write the custody commit"
      return 2
    }
    # Verify the commit before it leaves: MANIFEST, every blob entry by id
    # and mode, every chunked entry rebuilt and hashed.
    if [ "$(git rev-parse --verify -q "${commit}:MANIFEST" 2>/dev/null)" != "$blob" ]; then
      echo "::error title=hold verify failed::MANIFEST in ${commit} is not the one written"
      return 2
    fi
    git ls-tree -r "$commit" -- blobs > "$W/tree.ls" || {
      echo "::error title=hold verify failed::could not list ${commit}"
      return 2
    }
    bad=$(awk -F'\t' '
      FILENAME == ARGV[1] {
        if ($2 != "D" && $6 != "1") { want["blobs/" $1] = $7 " blob " $3; wp["blobs/" $1] = $9; nw++ }
        next
      }
      {
        if (!($2 in want) || want[$2] != $1) { print "custody tree entry " $2 " is not the staged blob"; exit }
        ok++
      }
      END { if (ok != nw && !printed) print "custody tree has " ok " of " nw " held blobs" }
    ' "$W/take" "$W/tree.ls")
    if [ -n "$bad" ]; then
      echo "::error title=hold verify failed::${bad}"
      return 2
    fi
    while IFS=$'\t' read -r i layout <&3; do
      sha=$(awk -F'\t' -v i="$i" '$1 == i { print $3; exit }' "$W/take")
      path=$(awk -F'\t' -v i="$i" '$1 == i { print $9; exit }' "$W/take")
      if ! _push_hold_rebuild_to "$commit" "$i" "$layout" "$W/rebuild"; then
        echo "::error title=hold verify failed::could not rebuild ${path} from ${commit}"
        return 2
      fi
      blob=$(git hash-object "$W/rebuild") || return 2
      rm -f "$W/rebuild"
      if [ "$blob" != "$sha" ]; then
        echo "::error title=hold verify failed::${path} custody bytes hash ${blob}, staged blob ${sha}"
        return 2
      fi
    done 3< "$W/layouts"
    total=$(awk -F'\t' '$2 != "D" { t += $4 } END { printf "%.0f", t }' "$W/take")
    alarm=${PUSH_HOLD_PUSH_ALARM:-$((120 + total / 4194304))}
    ref="${PUSH_HOLD_PREFIX}${PUSH_HOLD_SCOPE}/${GITHUB_RUN_ID:-0}-${GITHUB_RUN_ATTEMPT:-1}-${commit:0:12}"
    _push_hold_push_ref "$commit" "$ref" "$alarm" || return 2
  fi

  # Custody is on origin (or nothing but deletions is held). Unstage every
  # held path; put HEAD's bytes back unless the caller keeps the worktree.
  awk -F'\t' '{ print $9 }' "$W/take" | tr '\n' '\0' > "$W/all.nul"
  if ! git --literal-pathspecs reset -q --pathspec-from-file="$W/all.nul" --pathspec-file-nul; then
    reset_failed=1
  fi
  if [ "$PUSH_HOLD_KEEP_WORKTREE" != "1" ]; then
    awk -F'\t' '$5 != "-" { print $9 }' "$W/take" | tr '\n' '\0' > "$W/tracked.nul"
    if [ -s "$W/tracked.nul" ]; then
      git --literal-pathspecs checkout -q HEAD --pathspec-from-file="$W/tracked.nul" --pathspec-file-nul || reset_failed=1
    fi
  fi
  if git diff --cached --name-only -z --no-renames > "$W/still.z"; then
    tr '\0' '\n' < "$W/still.z" > "$W/still"
    if awk -F'\t' 'FILENAME == ARGV[1] { s[$0] = 1; next } ($9 in s) { f = 1 } END { exit f ? 0 : 1 }' "$W/still" "$W/take"; then
      reset_failed=1
    fi
  else
    reset_failed=1
  fi
  awk -F'\t' -v ref="$ref" '{ print ref "\t" $9 }' "$W/take" >> "$PUSH_HOLD_STATE/held"

  nheld=$(awk 'END { print NR }' "$W/take")
  PUSH_BLOB_LIMIT="$PUSH_BLOB_LIMIT" PUSH_HOLD_LIST_MAX="$PUSH_HOLD_LIST_MAX" PH_REF="$ref" awk -F'\t' '
    BEGIN { max = ENVIRON["PUSH_HOLD_LIST_MAX"] + 0; if (max < 1) max = 1; limit = ENVIRON["PUSH_BLOB_LIMIT"]; ref = ENVIRON["PH_REF"] }
    {
      if ($2 == "D") { t = "deletion withheld"; m = $9 " is deleted in a held group; the deletion is not published"; pri = 2 }
      else if ($6 == "1") { t = "withheld, not lost"; m = $9 " is " $4 " B, over " limit " B. Withheld with its group; its bytes are kept at " ref " and the next run restores them."; pri = 0 }
      else { t = "withheld, not lost"; m = $9 " is " $4 " B, under the limit. Withheld with its group because " $8 "; its bytes are kept at " ref " and the next run restores them."; pri = 1 }
      line[pri, ++c[pri]] = "::error title=" t "::" m
    }
    END {
      shown = 0
      for (p = 0; p <= 2; p++)
        for (k = 1; k <= c[p]; k++) {
          if (shown < max) { print line[p, k]; shown++ }
          else rest++
        }
      if (rest > 0) print "::error title=withheld, not lost::" rest " more paths are withheld with their groups at " ref "; the step summary and the MANIFEST there list them"
    }
  ' "$W/take"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    PUSH_BLOB_LIMIT="$PUSH_BLOB_LIMIT" PH_REF="$ref" PH_N="$nheld" awk -F'\t' '
      BEGIN {
        ref = ENVIRON["PH_REF"]; limit = ENVIRON["PUSH_BLOB_LIMIT"]; cap = 600000
        print "### Withheld, not lost: " ENVIRON["PH_N"] " staged paths held at `" ref "`"
        print ""
        print "Nothing in a held group is published by this step. The next run of this job restores the rows from that ref."
        print ""
        print "<details><summary>held paths</summary>"
        print ""
      }
      {
        if ($2 == "D") m = "- `" $9 "` deleted; the deletion is not published"
        else if ($6 == "1") m = "- `" $9 "` " $4 " B, over " limit " B"
        else m = "- `" $9 "` " $4 " B, held because " $8
        if (bytes + length(m) + 1 > cap) { rest++; next }
        bytes += length(m) + 1
        print m
      }
      END {
        if (rest > 0) print "- and " rest " more; the MANIFEST at `" ref "` lists every held row"
        print ""
        print "</details>"
      }
    ' "$W/take" > "$W/summary"
    _push_hold_summary_file "$W/presum"
    _push_hold_summary_file "$W/summary"
  fi
  if [ "$reset_failed" -ne 0 ]; then
    echo "::error title=hold custody failed::${ref} is on origin but the worktree could not be restored"
    return 2
  fi
  return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  set -e
  case "${1:-}" in
    recover)
      shift
      push_hold_recover "$@"
      ;;
    *)
      echo "usage: bash scripts/ci/push_hold.sh recover <group>..." >&2
      exit 2
      ;;
  esac
fi
