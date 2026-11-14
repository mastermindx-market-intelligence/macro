#!/bin/bash
set -euo pipefail
umask 027

cache=${1:-/var/cache/mastermind-ci/macro.git}
lock=${2:-/run/lock/mastermind-ci-cache.lock}

main_ref=refs/heads/main
remote_main_ref=refs/remotes/origin/main
validated_ref=refs/mastermind/cache-validated-main
candidate_ref=refs/mastermind/cache-update-candidate
last_ok=$cache/.last-update-ok

fail() {
  local status=$1
  shift
  printf 'mastermind-ci-cache-update: %s\n' "$*" >&2
  exit "$status"
}

git_cache() {
  git --git-dir="$cache" "$@"
}

exec 9>"$lock"
flock -w 120 9 || fail 75 "could not acquire update lock within 120 seconds"

test -f "$cache/.mastermind-cache-identity.json" || fail 66 "cache identity marker is missing"
test "$(git_cache rev-parse --is-bare-repository)" = true || fail 66 "cache is not bare"
git_cache config gc.auto 0
git_cache config maintenance.auto false

# The candidate is never published directly by fetch. If validation or the process
# fails, active main and its durable validation boundary remain byte-for-byte intact.
cleanup_candidate() {
  git_cache update-ref -d "$candidate_ref" >/dev/null 2>&1 || true
}
trap cleanup_candidate EXIT
cleanup_candidate

old_main=$(git_cache rev-parse --verify "$main_ref^{commit}") || \
  fail 66 "active main ref is missing or is not a commit"
old_origin=$(git_cache show-ref --verify --hash "$remote_main_ref" 2>/dev/null || true)
if test -n "$old_origin" && test "$old_origin" != "$old_main"; then
  fail 66 "remote-tracking main $old_origin does not match active main $old_main"
fi

validated_oid=$(git_cache show-ref --verify --hash "$validated_ref" 2>/dev/null || true)
test -n "$validated_oid" || \
  fail 66 "validation boundary is missing; bootstrap the audited cache before enabling updates"
validated_main=$(git_cache rev-parse --verify "$validated_ref^{commit}") || \
  fail 66 "validation boundary is not a commit"
if test "$validated_main" != "$old_main"; then
  fail 66 "validation boundary $validated_main does not match active main $old_main"
fi

# Fetch into a private staging ref. Publication happens only after the delta from the
# durable boundary has been enumerated with lazy fetching disabled and every listed
# object has been resolved locally.
git_cache fetch --no-auto-maintenance --no-tags --no-write-fetch-head --refmap= origin \
  "+refs/heads/main:$candidate_ref"
candidate=$(git_cache rev-parse --verify "$candidate_ref^{commit}") || \
  fail 66 "fetched candidate is missing or is not a commit"

checked=0
if test "$candidate" != "$validated_main"; then
  if ! git_cache merge-base --is-ancestor "$validated_main" "$candidate"; then
    fail 65 "non-fast-forward main candidate $candidate from validated boundary $validated_main"
  fi
  validation=$(
    GIT_NO_LAZY_FETCH=1 git_cache rev-list --objects --no-object-names \
      "$candidate" "^$validated_main" |
      GIT_NO_LAZY_FETCH=1 git_cache cat-file --batch-check |
      awk '
        { checked += 1 }
        $2 == "missing" { missing += 1 }
        END { print checked + 0, missing + 0 }
      '
  )
  read -r checked missing <<<"$validation"
  test "$missing" -eq 0 || fail 66 "candidate delta contains $missing missing objects"
fi

# Git's ref transaction makes active main, the remote-tracking ref, the durable
# validation boundary and candidate cleanup one indivisible publication event.
{
  echo start
  printf 'update %s %s %s\n' "$main_ref" "$candidate" "$old_main"
  if test -n "$old_origin"; then
    printf 'update %s %s %s\n' "$remote_main_ref" "$candidate" "$old_origin"
  else
    printf 'create %s %s\n' "$remote_main_ref" "$candidate"
  fi
  printf 'update %s %s %s\n' "$validated_ref" "$candidate" "$validated_oid"
  printf 'delete %s %s\n' "$candidate_ref" "$candidate"
  echo prepare
  echo commit
} | git_cache update-ref --stdin
trap - EXIT

touch "$last_ok"
printf 'CI_CACHE_UPDATE old=%s new=%s checked=%s boundary=explicit\n' \
  "$old_main" "$candidate" "$checked"
