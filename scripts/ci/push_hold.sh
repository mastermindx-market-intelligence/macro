#!/usr/bin/env bash
# push_hold.sh — custody for staged rows that cannot land in one GitHub blob.
#
# Ruling R-33: a hold must never destroy an unpublished row. Before local bytes
# are reverted, the exact held bytes are pushed to a custody ref that outlives
# the runner. The next run of the same job fetches that ref and reconciles it.
# A source file and its derived site/ projection are one group: hold every
# staged member of a group that has an over-limit blob, or none of that group.
# If a staged path belongs to no declared group, membership is not proved and
# every staged path is held.
#
# Knobs (default in parentheses):
#   PUSH_BLOB_LIMIT   (104857600)  over when staged size is greater than this
#   PUSH_HOLD_PART    (52428800)   chunk size for over-limit custody parts
#   PUSH_HOLD_PREFIX  (refs/heads/push-hold/)
#   PUSH_HOLD_SCOPE   (${GITHUB_JOB:-local})  recover only this job's refs
#   PUSH_HOLD_TRIES   (3)
#
# State: ${RUNNER_TEMP:-${TMPDIR:-/tmp}}/push_hold.${GITHUB_RUN_ID:-0}.${PUSH_HOLD_SCOPE}
#   held, recovered, unreconciled — one item per line.
#
# Custody ref:
#   ${PUSH_HOLD_PREFIX}${PUSH_HOLD_SCOPE}/${GITHUB_RUN_ID:-0}-${GITHUB_RUN_ATTEMPT:-1}-<12 hex>
#
# Bash 3.2 (macOS runner): no mapfile, no associative arrays, no stat -c,
# no split -d, no cmp -n, no timeout. Sizes and bytes come from git cat-file,
# git hash-object, head -c, tail -c and dd.
#
# Sourced by scripts/ci/us_board_commit.sh (defines functions, runs nothing).
#   bash scripts/ci/push_hold.sh recover <group>...

_push_hold_defaults() {
  : "${PUSH_BLOB_LIMIT:=104857600}"
  : "${PUSH_HOLD_PART:=52428800}"
  : "${PUSH_HOLD_PREFIX:=refs/heads/push-hold/}"
  : "${PUSH_HOLD_SCOPE:=${GITHUB_JOB:-local}}"
  : "${PUSH_HOLD_TRIES:=3}"
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

_push_hold_filesize() {
  local n
  n=$(wc -c < "$1") || return 1
  n=${n#"${n%%[![:space:]]*}"}
  n=${n%"${n##*[![:space:]]}"}
  printf '%s' "$n"
}

# $1 path, $2 space-separated group members. 0 when path equals a member
# or is under member/.
_push_hold_path_in_group() {
  local path="$1" group="$2" member noglob=0
  case $- in
    *f*) noglob=1 ;;
  esac
  set -f
  for member in $group; do
    [ -n "$member" ] || continue
    if [ "$path" = "$member" ]; then
      [ "$noglob" -eq 1 ] || set +f
      return 0
    fi
    case "$path" in
      "$member"/*)
        [ "$noglob" -eq 1 ] || set +f
        return 0
        ;;
    esac
  done
  [ "$noglob" -eq 1 ] || set +f
  return 1
}

_push_hold_save_groups() {
  local i=0 g
  for g in "$@"; do
    i=$((i + 1))
    printf '%s\n' "$g" > "$PUSH_HOLD_WORK/g.$i"
  done
  printf '%s\n' "$i" > "$PUSH_HOLD_WORK/group.count"
  return 0
}

_push_hold_path_in_any() {
  local path="$1" n i g
  n=$(cat "$PUSH_HOLD_WORK/group.count" 2>/dev/null) || n=0
  [ -n "$n" ] || n=0
  i=1
  while [ "$i" -le "$n" ]; do
    g=$(cat "$PUSH_HOLD_WORK/g.$i") || return 1
    if _push_hold_path_in_group "$path" "$g"; then
      return 0
    fi
    i=$((i + 1))
  done
  return 1
}

_push_hold_index_blob() {
  # $1 sha, $2 path inside the custody tree
  GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git update-index --add --cacheinfo "100644,$1,$2"
}

# Append PUSH_HOLD_PART chunks of $1 as $2/000, $2/001, ...
# tail -c is 1-based; dd skip/count walks the same bytes.
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
    _push_hold_index_blob "$sha" "${treepath}/${name}" || return 1
    n=$((n + 1))
    offset=$((offset + csize))
  done
  [ "$offset" -eq "$total" ] || return 1
  return 0
}

_push_hold_append_parts() {
  local treeish="$1" i="$2" dest="$3" name
  git ls-tree --name-only "${treeish}:parts/${i}" > "$PUSH_HOLD_WORK/partnames" || return 1
  LC_ALL=C sort -o "$PUSH_HOLD_WORK/partnames.sorted" "$PUSH_HOLD_WORK/partnames" || return 1
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    [ "$name" = "base" ] && continue
    git cat-file blob "${treeish}:parts/${i}/${name}" >> "$dest" || return 1
  done < "$PUSH_HOLD_WORK/partnames.sorted"
  return 0
}

# Rebuild one custody entry into $4. Layout is blob, prefix, or whole.
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

_push_hold_verify_commit() {
  local commit="$1" line rest i path blob layout got dest
  dest="$PUSH_HOLD_WORK/rebuild"
  git cat-file blob "${commit}:MANIFEST" > "$PUSH_HOLD_WORK/MANIFEST.committed" || return 1
  while IFS= read -r line; do
    case "$line" in
      entry$'\t'*)
        rest=${line#entry$'\t'}
        i=${rest%%$'\t'*}
        rest=${rest#*$'\t'}
        path=${rest%%$'\t'*}
        rest=${rest#*$'\t'}
        blob=${rest%%$'\t'*}
        rest=${rest#*$'\t'}
        rest=${rest#*$'\t'}
        rest=${rest#*$'\t'}
        layout=$rest
        if ! _push_hold_rebuild_to "$commit" "$i" "$layout" "$dest"; then
          echo "::error title=hold verify failed::could not rebuild ${path} from ${commit}"
          return 1
        fi
        got=$(git hash-object "$dest") || return 1
        if [ "$got" != "$blob" ]; then
          echo "::error title=hold verify failed::${path} custody bytes hash ${got}, staged blob ${blob}"
          return 1
        fi
        ;;
    esac
  done < "$PUSH_HOLD_WORK/MANIFEST.committed"
  return 0
}

_push_hold_push_ref() {
  local commit="$1" ref="$2" try=1 line remote_sha
  while [ "$try" -le "$PUSH_HOLD_TRIES" ]; do
    if perl -e 'alarm 120; exec @ARGV or die' -- git push origin "${commit}:${ref}"; then
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

_push_hold_meta_size() {
  local path="$1" line p rest
  while IFS= read -r line; do
    p=${line%%$'\t'*}
    if [ "$p" = "$path" ]; then
      rest=${line#*$'\t'}
      printf '%s' "${rest%%$'\t'*}"
      return 0
    fi
  done < "$PUSH_HOLD_WORK/meta"
  return 1
}

# Entry line: i, path, blob, size, head blob, layout.
_push_hold_load_ent() {
  local line="$1" rest
  PH_I=${line%%$'\t'*}
  rest=${line#*$'\t'}
  PH_PATH=${rest%%$'\t'*}
  rest=${rest#*$'\t'}
  PH_BLOB=${rest%%$'\t'*}
  rest=${rest#*$'\t'}
  PH_SIZE=${rest%%$'\t'*}
  rest=${rest#*$'\t'}
  PH_HEAD=${rest%%$'\t'*}
  PH_LAYOUT=${rest#*$'\t'}
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

_push_hold_entry_landed() {
  local rebuilt="$1" path="$2"
  if ! git cat-file -e "HEAD:${path}" 2>/dev/null; then
    return 1
  fi
  git cat-file blob "HEAD:${path}" > "$PUSH_HOLD_WORK/headbytes" || return 1
  _push_hold_file_is_prefix "$rebuilt" "$PUSH_HOLD_WORK/headbytes"
}

# 0 when HEAD's blob id is the entry's base (`-` means the path is absent).
_push_hold_base_ok() {
  local path="$1" headblob="$2" cur
  if [ "$headblob" = "-" ]; then
    if git cat-file -e "HEAD:${path}" 2>/dev/null; then
      return 1
    fi
    return 0
  fi
  if ! git cat-file -e "HEAD:${path}" 2>/dev/null; then
    return 1
  fi
  cur=$(git rev-parse --verify "HEAD:${path}" 2>/dev/null) || return 1
  [ "$cur" = "$headblob" ]
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
  local n="$1" ref line
  ref=$(cat "$PUSH_HOLD_WORK/ref.$n") || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    _push_hold_load_ent "$line"
    printf '%s\t%s\n' "$ref" "$PH_PATH" >> "$PUSH_HOLD_STATE/recovered"
  done < "$PUSH_HOLD_WORK/ent.$n"
  return 0
}

_push_hold_delete_remote() {
  local ref="$1" line
  perl -e 'alarm 120; exec @ARGV or die' -- git push origin --delete "$ref" || return 1
  line=$(git ls-remote origin "$ref" 2>/dev/null) || return 1
  [ -z "$line" ] || return 1
  return 0
}

_push_hold_refs_share_path() {
  local a="$1" b="$2" la lb pa pb
  while IFS= read -r la || [ -n "$la" ]; do
    [ -n "$la" ] || continue
    _push_hold_load_ent "$la"
    pa=$PH_PATH
    while IFS= read -r lb || [ -n "$lb" ]; do
      [ -n "$lb" ] || continue
      _push_hold_load_ent "$lb"
      pb=$PH_PATH
      if [ "$pa" = "$pb" ]; then
        return 0
      fi
    done < "$PUSH_HOLD_WORK/ent.$b"
  done < "$PUSH_HOLD_WORK/ent.$a"
  return 1
}

_push_hold_parse_manifest() {
  local n="$1" line first=1 rest i path blob size headblob layout
  : > "$PUSH_HOLD_WORK/ent.$n"
  : > "$PUSH_HOLD_WORK/from.$n"
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$first" -eq 1 ]; then
      first=0
      if [ "$line" != "push-hold/v1" ]; then
        printf '%s\n' "manifest is not push-hold/v1" > "$PUSH_HOLD_WORK/why.$n"
        printf '%s\n' "bad" > "$PUSH_HOLD_WORK/st.$n"
        return 1
      fi
      continue
    fi
    case "$line" in
      entry$'\t'*)
        rest=${line#entry$'\t'}
        i=${rest%%$'\t'*}
        rest=${rest#*$'\t'}
        path=${rest%%$'\t'*}
        rest=${rest#*$'\t'}
        blob=${rest%%$'\t'*}
        rest=${rest#*$'\t'}
        size=${rest%%$'\t'*}
        rest=${rest#*$'\t'}
        headblob=${rest%%$'\t'*}
        layout=${rest#*$'\t'}
        if [ -z "$layout" ] || [ -z "$path" ] || [ -z "$blob" ]; then
          printf '%s\n' "manifest entry is incomplete" > "$PUSH_HOLD_WORK/why.$n"
          printf '%s\n' "bad" > "$PUSH_HOLD_WORK/st.$n"
          return 1
        fi
        if ! _push_hold_path_in_any "$path"; then
          printf '%s\n' "entry ${path} belongs to no declared group" > "$PUSH_HOLD_WORK/why.$n"
          printf '%s\n' "bad" > "$PUSH_HOLD_WORK/st.$n"
          return 1
        fi
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$i" "$path" "$blob" "$size" "$headblob" "$layout" >> "$PUSH_HOLD_WORK/ent.$n"
        ;;
      from$'\t'*)
        printf '%s\n' "${line#from$'\t'}" >> "$PUSH_HOLD_WORK/from.$n"
        ;;
      run$'\t'*|scope$'\t'*|head$'\t'*|"")
        ;;
      *)
        printf '%s\n' "manifest line not understood" > "$PUSH_HOLD_WORK/why.$n"
        printf '%s\n' "bad" > "$PUSH_HOLD_WORK/st.$n"
        return 1
        ;;
    esac
  done < "$PUSH_HOLD_WORK/man.$n"
  if [ "$first" -eq 1 ]; then
    printf '%s\n' "manifest is not push-hold/v1" > "$PUSH_HOLD_WORK/why.$n"
    printf '%s\n' "bad" > "$PUSH_HOLD_WORK/st.$n"
    return 1
  fi
  printf '%s\n' "ok" > "$PUSH_HOLD_WORK/st.$n"
  return 0
}

_push_hold_apply_ref() {
  local n="$1" ref localref line dest got all_landed can_apply why st path
  ref=$(cat "$PUSH_HOLD_WORK/ref.$n") || return 0
  localref=$(cat "$PUSH_HOLD_WORK/local.$n") || return 0
  if [ ! -s "$PUSH_HOLD_WORK/ent.$n" ]; then
    _push_hold_mark_unreconciled "$ref" "manifest has no entries"
    return 0
  fi
  mkdir -p "$PUSH_HOLD_WORK/rb.$n" || {
    _push_hold_mark_unreconciled "$ref" "could not stage rebuilt bytes"
    return 0
  }
  all_landed=1
  can_apply=1
  why=""
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    _push_hold_load_ent "$line"
    dest="$PUSH_HOLD_WORK/rb.$n/$PH_I"
    if ! _push_hold_rebuild_to "$localref" "$PH_I" "$PH_LAYOUT" "$dest"; then
      _push_hold_mark_unreconciled "$ref" "could not rebuild ${PH_PATH}"
      return 0
    fi
    got=$(git hash-object "$dest" 2>/dev/null) || got=""
    if [ "$got" != "$PH_BLOB" ]; then
      _push_hold_mark_unreconciled "$ref" "rebuilt bytes for ${PH_PATH} do not match ${PH_BLOB}"
      return 0
    fi
    if ! _push_hold_entry_landed "$dest" "$PH_PATH"; then
      all_landed=0
    fi
    if ! _push_hold_base_ok "$PH_PATH" "$PH_HEAD"; then
      can_apply=0
      [ -n "$why" ] || why="HEAD for ${PH_PATH} does not match the held base"
    fi
    st=$(git status --porcelain -- "$PH_PATH" 2>/dev/null) || st="dirty"
    if [ -n "$st" ]; then
      can_apply=0
      [ -n "$why" ] || why="worktree is dirty for ${PH_PATH}"
    fi
  done < "$PUSH_HOLD_WORK/ent.$n"
  if [ "$all_landed" -eq 1 ]; then
    if _push_hold_delete_remote "$ref"; then
      echo "hold ${ref} already landed on HEAD; deleted ${ref}"
    else
      echo "::warning title=hold ref remains::${ref} already landed on HEAD but the ref is still on origin"
    fi
    return 0
  fi
  if [ "$can_apply" -ne 1 ]; then
    _push_hold_mark_unreconciled "$ref" "$why"
    return 0
  fi
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    _push_hold_load_ent "$line"
    dest="$PUSH_HOLD_WORK/rb.$n/$PH_I"
    path=$PH_PATH
    mkdir -p -- "$(dirname -- "$path")" || {
      _push_hold_mark_unreconciled "$ref" "could not create ${path}"
      return 0
    }
    if ! cat "$dest" > "$path"; then
      _push_hold_mark_unreconciled "$ref" "could not write ${path}"
      return 0
    fi
    got=$(git hash-object "$path" 2>/dev/null) || got=""
    if [ "$got" != "$PH_BLOB" ]; then
      _push_hold_mark_unreconciled "$ref" "wrote ${path} but bytes do not match ${PH_BLOB}"
      return 0
    fi
  done < "$PUSH_HOLD_WORK/ent.$n"
  _push_hold_record_recovered "$n" || _push_hold_mark_unreconciled "$ref" "could not record recovery"
  return 0
}

_push_hold_recover_impl() {
  local ls_out line ref tail localref n i j fromref st why
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
  _push_hold_save_groups "$@" || return 0
  printf '%s\n' "$ls_out" > "$PUSH_HOLD_WORK/lsremote"
  n=0
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    ref=${line#*$'\t'}
    [ -n "$ref" ] || continue
    n=$((n + 1))
    printf '%s\n' "$ref" > "$PUSH_HOLD_WORK/ref.$n"
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
  done < "$PUSH_HOLD_WORK/lsremote"
  printf '%s\n' "$n" > "$PUSH_HOLD_WORK/ref.count"
  [ "$n" -gt 0 ] || return 0

  : > "$PUSH_HOLD_WORK/super_names"
  i=1
  while [ "$i" -le "$n" ]; do
    if [ "$(cat "$PUSH_HOLD_WORK/st.$i")" = "ok" ]; then
      while IFS= read -r fromref; do
        [ -n "$fromref" ] || continue
        printf '%s\n' "$fromref" >> "$PUSH_HOLD_WORK/super_names"
      done < "$PUSH_HOLD_WORK/from.$i"
    fi
    i=$((i + 1))
  done
  i=1
  while [ "$i" -le "$n" ]; do
    if [ "$(cat "$PUSH_HOLD_WORK/st.$i")" = "ok" ]; then
      ref=$(cat "$PUSH_HOLD_WORK/ref.$i")
      if grep -qxF "$ref" "$PUSH_HOLD_WORK/super_names"; then
        printf '%s\n' "super" > "$PUSH_HOLD_WORK/st.$i"
      fi
    fi
    i=$((i + 1))
  done

  i=1
  while [ "$i" -le "$n" ]; do
    if [ "$(cat "$PUSH_HOLD_WORK/st.$i")" != "ok" ]; then
      i=$((i + 1))
      continue
    fi
    j=$((i + 1))
    while [ "$j" -le "$n" ]; do
      if [ "$(cat "$PUSH_HOLD_WORK/st.$j")" = "ok" ]; then
        if _push_hold_refs_share_path "$i" "$j"; then
          printf '%s\n' "clash" > "$PUSH_HOLD_WORK/st.$i"
          printf '%s\n' "clash" > "$PUSH_HOLD_WORK/st.$j"
          printf '%s\n' "shares a path with $(cat "$PUSH_HOLD_WORK/ref.$j")" > "$PUSH_HOLD_WORK/why.$i"
          printf '%s\n' "shares a path with $(cat "$PUSH_HOLD_WORK/ref.$i")" > "$PUSH_HOLD_WORK/why.$j"
        fi
      fi
      j=$((j + 1))
    done
    i=$((i + 1))
  done

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

_push_hold_held_has() {
  local path="$1" line got
  [ -f "$PUSH_HOLD_STATE/held" ] || return 1
  while IFS= read -r line; do
    got=${line#*$'\t'}
    [ "$got" = "$path" ] && return 0
  done < "$PUSH_HOLD_STATE/held"
  return 1
}

push_hold_settle() {
  local before now line ref r p ok
  _push_hold_state_var || return 0
  [ -s "$PUSH_HOLD_STATE/recovered" ] || return 0
  : > "$PUSH_HOLD_STATE/pushed_names"
  if [ -f "$PUSH_HOLD_STATE/head_before" ]; then
    before=$(cat "$PUSH_HOLD_STATE/head_before") || before=""
    now=$(git rev-parse HEAD 2>/dev/null) || now=""
    if [ -n "$before" ] && [ -n "$now" ] && [ "$now" != "$before" ]; then
      git diff-tree --no-commit-id --name-only -r HEAD > "$PUSH_HOLD_STATE/pushed_names" || : > "$PUSH_HOLD_STATE/pushed_names"
    fi
  fi
  : > "$PUSH_HOLD_STATE/settle_refs"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    ref=${line%%$'\t'*}
    if ! grep -qxF "$ref" "$PUSH_HOLD_STATE/settle_refs"; then
      printf '%s\n' "$ref" >> "$PUSH_HOLD_STATE/settle_refs"
    fi
  done < "$PUSH_HOLD_STATE/recovered"
  while IFS= read -r ref; do
    [ -n "$ref" ] || continue
    ok=1
    while IFS= read -r line; do
      r=${line%%$'\t'*}
      p=${line#*$'\t'}
      [ "$r" = "$ref" ] || continue
      if grep -qxF "$p" "$PUSH_HOLD_STATE/pushed_names" 2>/dev/null; then
        continue
      fi
      if _push_hold_held_has "$p"; then
        continue
      fi
      ok=0
    done < "$PUSH_HOLD_STATE/recovered"
    if [ "$ok" -ne 1 ]; then
      echo "::warning title=hold ref kept::${ref} has a path that is neither in the pushed commit nor held again"
      continue
    fi
    if _push_hold_delete_remote "$ref"; then
      echo "hold settled ${ref}"
    else
      echo "::warning title=hold ref remains::${ref} delete did not verify"
    fi
  done < "$PUSH_HOLD_STATE/settle_refs"
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

push_hold_oversize_staged() {
  local staged_list path size over=0 ungrouped=0 line rest blob headblob overflag
  local n i g hot take layout head_size pfx_hash headsha tree commit ref
  local fromref frompath msg reset_failed=0
  _push_hold_state_var || return 2
  staged_list=$(git diff --cached --name-only --no-renames --diff-filter=d) || {
    echo "::error title=hold custody failed::could not list staged paths"
    return 2
  }
  if [ -n "$staged_list" ]; then
    while IFS= read -r path; do
      [ -n "$path" ] || continue
      size=$(git cat-file -s ":${path}" 2>/dev/null) || size=""
      if [ -z "$size" ] || [ "$size" -gt "$PUSH_BLOB_LIMIT" ]; then
        over=1
      fi
    done < <(printf '%s\n' "$staged_list")
  fi
  if [ "$over" -eq 0 ]; then
    if [ -s "$PUSH_HOLD_STATE/recovered" ]; then
      _push_hold_prepare_state || return 2
      git rev-parse HEAD > "$PUSH_HOLD_STATE/head_before" || return 2
    fi
    return 0
  fi
  _push_hold_work_reset || {
    echo "::error title=hold custody failed::could not create the hold state dir"
    return 2
  }
  git rev-parse HEAD > "$PUSH_HOLD_STATE/head_before" || {
    echo "::error title=hold custody failed::could not read HEAD"
    return 2
  }
  _push_hold_save_groups "$@" || return 2
  printf '%s\n' "$staged_list" > "$PUSH_HOLD_WORK/staged"
  : > "$PUSH_HOLD_WORK/meta"
  ungrouped=0
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    size=$(git cat-file -s ":${path}" 2>/dev/null) || size=""
    blob=$(git rev-parse --verify ":${path}" 2>/dev/null) || blob=""
    if [ -z "$size" ] || [ -z "$blob" ]; then
      size="?"
      overflag=1
    elif [ "$size" -gt "$PUSH_BLOB_LIMIT" ]; then
      overflag=1
    else
      overflag=0
    fi
    headblob="-"
    if git cat-file -e "HEAD:${path}" 2>/dev/null; then
      headblob=$(git rev-parse --verify "HEAD:${path}" 2>/dev/null) || headblob="-"
    fi
    printf '%s\t%s\t%s\t%s\t%s\n' "$path" "$size" "$blob" "$headblob" "$overflag" >> "$PUSH_HOLD_WORK/meta"
    if ! _push_hold_path_in_any "$path"; then
      ungrouped=1
    fi
  done < "$PUSH_HOLD_WORK/staged"

  if [ "$ungrouped" -eq 1 ]; then
    while IFS= read -r path; do
      [ -n "$path" ] || continue
      if ! _push_hold_path_in_any "$path"; then
        msg="${path} belongs to no declared group; holding every staged path"
        echo "::error title=hold membership not proved::${msg}"
        _push_hold_summary "$msg"
      fi
    done < "$PUSH_HOLD_WORK/staged"
    cp "$PUSH_HOLD_WORK/staged" "$PUSH_HOLD_WORK/hold_paths"
  else
    n=$(cat "$PUSH_HOLD_WORK/group.count")
    : > "$PUSH_HOLD_WORK/hot"
    i=1
    while [ "$i" -le "$n" ]; do
      g=$(cat "$PUSH_HOLD_WORK/g.$i") || return 2
      hot=0
      while IFS= read -r line; do
        [ -n "$line" ] || continue
        path=${line%%$'\t'*}
        rest=$line
        rest=${rest#*$'\t'}
        rest=${rest#*$'\t'}
        rest=${rest#*$'\t'}
        rest=${rest#*$'\t'}
        overflag=$rest
        if [ "$overflag" = "1" ] && _push_hold_path_in_group "$path" "$g"; then
          hot=1
        fi
      done < "$PUSH_HOLD_WORK/meta"
      if [ "$hot" -eq 1 ]; then
        printf '%s\n' "$i" >> "$PUSH_HOLD_WORK/hot"
      fi
      i=$((i + 1))
    done
    : > "$PUSH_HOLD_WORK/hold_paths"
    while IFS= read -r path; do
      [ -n "$path" ] || continue
      take=0
      i=1
      while [ "$i" -le "$n" ]; do
        if grep -qxF "$i" "$PUSH_HOLD_WORK/hot" && _push_hold_path_in_group "$path" "$(cat "$PUSH_HOLD_WORK/g.$i")"; then
          take=1
          break
        fi
        i=$((i + 1))
      done
      if [ "$take" -eq 1 ]; then
        printf '%s\n' "$path" >> "$PUSH_HOLD_WORK/hold_paths"
      fi
    done < "$PUSH_HOLD_WORK/staged"
  fi
  if [ ! -s "$PUSH_HOLD_WORK/hold_paths" ]; then
    echo "::error title=hold custody failed::an over-limit path produced an empty hold set"
    return 2
  fi

  : > "$PUSH_HOLD_WORK/from_refs"
  if [ -s "$PUSH_HOLD_STATE/recovered" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] || continue
      fromref=${line%%$'\t'*}
      frompath=${line#*$'\t'}
      [ "$fromref" != "$frompath" ] || continue
      if grep -qxF "$frompath" "$PUSH_HOLD_WORK/hold_paths"; then
        if ! grep -qxF "$fromref" "$PUSH_HOLD_WORK/from_refs"; then
          printf '%s\n' "$fromref" >> "$PUSH_HOLD_WORK/from_refs"
        fi
      fi
    done < "$PUSH_HOLD_STATE/recovered"
  fi

  rm -f "$PUSH_HOLD_INDEX"
  GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git read-tree --empty || {
    echo "::error title=hold custody failed::could not start a private index"
    return 2
  }
  : > "$PUSH_HOLD_WORK/entries"
  i=0
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    line=$(_push_hold_meta_line "$path") || {
      echo "::error title=hold custody failed::no metadata for ${path}"
      return 2
    }
    rest=$line
    rest=${rest#*$'\t'}
    size=${rest%%$'\t'*}
    rest=${rest#*$'\t'}
    blob=${rest%%$'\t'*}
    rest=${rest#*$'\t'}
    headblob=${rest%%$'\t'*}
    overflag=${rest#*$'\t'}
    if [ "$size" = "?" ] || [ -z "$blob" ]; then
      echo "::error title=hold custody failed::could not read the staged blob for ${path}"
      return 2
    fi
    if [ "$overflag" = "1" ]; then
      git cat-file blob ":${path}" > "$PUSH_HOLD_WORK/staged_bytes" || {
        echo "::error title=hold custody failed::could not read staged bytes for ${path}"
        return 2
      }
      layout=whole
      if [ "$headblob" != "-" ]; then
        head_size=$(git cat-file -s "HEAD:${path}" 2>/dev/null) || head_size=""
        if [ -n "$head_size" ] && [ "$size" -ge "$head_size" ]; then
          head -c "$head_size" "$PUSH_HOLD_WORK/staged_bytes" > "$PUSH_HOLD_WORK/pfx" || return 2
          pfx_hash=$(git hash-object "$PUSH_HOLD_WORK/pfx") || return 2
          if [ "$pfx_hash" = "$headblob" ]; then
            layout=prefix
          fi
        fi
      fi
      if [ "$layout" = "prefix" ]; then
        _push_hold_index_blob "$headblob" "parts/${i}/base" || return 2
        # Byte head_size+1 is the first byte of the suffix (tail -c is 1-based).
        tail -c "+$((head_size + 1))" "$PUSH_HOLD_WORK/staged_bytes" > "$PUSH_HOLD_WORK/suffix" || return 2
        _push_hold_add_chunks "$PUSH_HOLD_WORK/suffix" "parts/${i}" || {
          echo "::error title=hold custody failed::could not chunk ${path}"
          return 2
        }
      else
        _push_hold_add_chunks "$PUSH_HOLD_WORK/staged_bytes" "parts/${i}" || {
          echo "::error title=hold custody failed::could not chunk ${path}"
          return 2
        }
      fi
    else
      layout=blob
      _push_hold_index_blob "$blob" "blobs/${i}" || return 2
    fi
    printf 'entry\t%s\t%s\t%s\t%s\t%s\t%s\n' "$i" "$path" "$blob" "$size" "$headblob" "$layout" >> "$PUSH_HOLD_WORK/entries"
    i=$((i + 1))
  done < "$PUSH_HOLD_WORK/hold_paths"

  headsha=$(git rev-parse HEAD) || {
    echo "::error title=hold custody failed::could not read HEAD"
    return 2
  }
  {
    printf '%s\n' "push-hold/v1"
    printf 'run\t%s-%s\n' "${GITHUB_RUN_ID:-0}" "${GITHUB_RUN_ATTEMPT:-1}"
    printf 'scope\t%s\n' "$PUSH_HOLD_SCOPE"
    printf 'head\t%s\n' "$headsha"
    cat "$PUSH_HOLD_WORK/entries"
    if [ -s "$PUSH_HOLD_WORK/from_refs" ]; then
      while IFS= read -r fromref; do
        [ -n "$fromref" ] || continue
        printf 'from\t%s\n' "$fromref"
      done < "$PUSH_HOLD_WORK/from_refs"
    fi
  } > "$PUSH_HOLD_WORK/MANIFEST"
  blob=$(git hash-object -w "$PUSH_HOLD_WORK/MANIFEST") || {
    echo "::error title=hold custody failed::could not hash MANIFEST"
    return 2
  }
  _push_hold_index_blob "$blob" "MANIFEST" || return 2
  tree=$(GIT_INDEX_FILE="$PUSH_HOLD_INDEX" git write-tree) || {
    echo "::error title=hold custody failed::could not write the custody tree"
    return 2
  }
  commit=$(git commit-tree "$tree" -m "push-hold") || {
    echo "::error title=hold custody failed::could not write the custody commit"
    return 2
  }
  if ! _push_hold_verify_commit "$commit"; then
    return 2
  fi
  ref="${PUSH_HOLD_PREFIX}${PUSH_HOLD_SCOPE}/${GITHUB_RUN_ID:-0}-${GITHUB_RUN_ATTEMPT:-1}-${commit:0:12}"
  _push_hold_push_ref "$commit" "$ref" || return 2

  reset_failed=0
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    if ! git reset -q -- "$path"; then
      reset_failed=1
    fi
    if git cat-file -e "HEAD:${path}" 2>/dev/null; then
      if ! git checkout HEAD -- "$path"; then
        reset_failed=1
      fi
    fi
  done < "$PUSH_HOLD_WORK/hold_paths"
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    size=$(_push_hold_meta_size "$path") || size="?"
    printf '%s\t%s\n' "$ref" "$path" >> "$PUSH_HOLD_STATE/held"
    msg="${path} is ${size} B, over ${PUSH_BLOB_LIMIT} B. Withheld with its group; its bytes are kept at ${ref} and the next run restores them."
    echo "::error title=withheld, not lost::${msg}"
    _push_hold_summary "$msg"
  done < "$PUSH_HOLD_WORK/hold_paths"
  if [ "$reset_failed" -ne 0 ]; then
    echo "::error title=hold custody failed::${ref} is on origin but the worktree could not be restored"
    return 2
  fi
  return 0
}

_push_hold_meta_line() {
  local path="$1" line p
  while IFS= read -r line; do
    p=${line%%$'\t'*}
    if [ "$p" = "$path" ]; then
      printf '%s' "$line"
      return 0
    fi
  done < "$PUSH_HOLD_WORK/meta"
  return 1
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
