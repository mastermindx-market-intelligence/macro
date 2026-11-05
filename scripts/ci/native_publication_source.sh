# Source this file from the ORIGINAL protected workflow Git object before
# mutating the candidate checkout. No credential, provider or data is captured.
# This private original-job code frame is not a controller or installation.
native_publication_capture_source() {
  local code_root="$1" protected_source="$2" source_path mode
  case "$protected_source" in *[!0-9a-f]*|'') return 76 ;; esac
  [ "${#protected_source}" -eq 40 ] || return 76
  [ "$protected_source" = "${GITHUB_WORKFLOW_SHA:-}" ] || return 76
  [ "$protected_source" = "${GITHUB_SHA:-}" ] || return 76
  case "${RUNNER_TEMP:-}" in /*) : ;; *) return 76 ;; esac
  [ -d "$code_root" ] && [ ! -L "$code_root" ] || return 76
  [ -O "$code_root" ] || return 76
  [ "${code_root%/*}" = "${RUNNER_TEMP%/}" ] || return 76
  [ "${code_root##*/}" = "native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}" ] || return 76
  # Repository-owned executable/import closure. The existing provisioned
  # interpreter/stdlib/Git remain the runner runtime; no environment install.
  for source_path in \
    scripts/__init__.py \
    scripts/ci/push_retry.sh \
    scripts/ci/native_queue_push.py \
    scripts/ci/native_publication.py \
    scripts/ci/native_publication_origin.py \
    scripts/ci/qledger_publication.py \
    engine/__init__.py \
    engine/qledger_store.py \
    engine/qledger_store_protocol.py \
    engine/qledger_store_sources.py \
    scripts/ci_authority.py \
    scripts/ci_admission_stages.py \
    scripts/ci_native_review_policy.py \
    scripts/ci_proof_admission.py \
    scripts/merge_on_green.py \
    .github/workflows/ci.yml \
    .github/workflows/fences.yml \
    .github/workflows/ci-authority.yml \
    .github/workflows/trusted-ci-executor.yml \
    .github/workflows/merge-on-green.yml; do
    mkdir -p -- "$code_root/$(dirname -- "$source_path")" || return 76
    GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show \
      "$protected_source:$source_path" > "$code_root/$source_path" || return 76
    mode=$(GIT_NO_REPLACE_OBJECTS=1 git ls-tree "$protected_source" -- "$source_path") || return 76
    case "$mode" in
      100644*) chmod 400 "$code_root/$source_path" || return 76 ;;
      100755*) chmod 500 "$code_root/$source_path" || return 76 ;;
      *) return 76 ;;
    esac
  done
  chmod 400 "$code_root/scripts/ci/native_publication_source.sh" || return 76
}
