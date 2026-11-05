_native_publication_source_paths() {
  # Closed CORE+supplier potential import closure; copying code activates no
  # deferred controller, CI executor or native QLedger mutation path.
  printf '%s\n' \
    .github/workflows/ci-authority.yml \
    .github/workflows/ci.yml \
    .github/workflows/fences.yml \
    .github/workflows/merge-on-green.yml \
    .github/workflows/trusted-ci-executor.yml \
    engine/__init__.py \
    engine/qledger_store.py \
    engine/qledger_store_native.py \
    engine/qledger_store_protocol.py \
    engine/qledger_store_sources.py \
    scripts/__init__.py \
    scripts/audit_unrun_tests.py \
    scripts/check_runner_policy.py \
    scripts/ci/fms_persist.py \
    scripts/ci/govrev_source_binding.py \
    scripts/ci/native_publication.py \
    scripts/ci/native_publication_origin.py \
    scripts/ci/native_queue_push.py \
    scripts/ci/push_retry.sh \
    scripts/ci/qledger_publication.py \
    scripts/ci_admission_stages.py \
    scripts/ci_apt_cold_acquisition.py \
    scripts/ci_apt_native_plan.py \
    scripts/ci_apt_native_stage.py \
    scripts/ci_apt_transaction_contract.py \
    scripts/ci_authority.py \
    scripts/ci_authority_paths.py \
    scripts/ci_browser_dependency_capture.py \
    scripts/ci_browser_dependency_inputs.py \
    scripts/ci_browser_native_setup.py \
    scripts/ci_native_review_policy.py \
    scripts/ci_proof_admission.py \
    scripts/ci_scope_dependencies.py \
    scripts/ci_semantic_proof.py \
    scripts/gh_path_filter.py \
    scripts/merge_on_green.py \
    scripts/resolve_ci_pr_admission.py \
    scripts/run_ci_pack.py \
    scripts/workflow_run_source.py \
    scripts/worktree_sparse.py
}

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
  for source_path in $(_native_publication_source_paths); do
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
  (set -o noclobber; printf '%s\n' "$protected_source" > "$code_root/original-source") || return 76
  chmod 400 "$code_root/original-source" || return 76
  native_publication_verify_source "$code_root" "$protected_source"
}

# Reuse only the COMPLETE exact original frame; never repair, overwrite or adopt
# a partial/unrecognized frame. This is local source verification, not a runtime
# receipt or proof that any held worker/lease is quiescent.
native_publication_verify_source() {
  local code_root="$1" protected_source="$2" source_path row expected actual
  case "$protected_source" in *[!0-9a-f]*|'') return 76 ;; esac
  [ "${#protected_source}" -eq 40 ] || return 76
  [ "$protected_source" = "${GITHUB_WORKFLOW_SHA:-}" ] || return 76
  [ "$protected_source" = "${GITHUB_SHA:-}" ] || return 76
  case "${RUNNER_TEMP:-}" in /*) : ;; *) return 76 ;; esac
  [ "${code_root%/*}" = "${RUNNER_TEMP%/}" ] || return 76
  [ "${code_root##*/}" = "native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}" ] || return 76
  python3 -I - "$code_root" "$protected_source" $(_native_publication_source_paths) <<'PYVERIFY' || return 76
import os,stat,sys
from pathlib import Path
root=Path(sys.argv[1]);source=sys.argv[2]
files=set(sys.argv[3:])|{'scripts/ci/native_publication_source.sh','original-source'}
dirs={'.'}|{str(parent) for name in files for parent in Path(name).parents}
def checked(path,mode):
 info=path.lstat()
 if info.st_uid!=os.getuid() or stat.S_ISLNK(info.st_mode) or stat.S_IMODE(info.st_mode) not in mode:
  raise ValueError('original code frame ownership/mode changed')
 return info
try:
 checked(root,{0o700})
 found=set()
 for directory,subdirs,names in os.walk(root,followlinks=False):
  relative=str(Path(directory).relative_to(root))
  if relative not in dirs:raise ValueError('unexpected code directory')
  checked(Path(directory),{0o700})
  for name in subdirs:
   if not stat.S_ISDIR(checked(Path(directory)/name,{0o700}).st_mode):raise ValueError('invalid code directory')
  for name in names:
   path=Path(directory)/name;relative=str(path.relative_to(root))
   if relative not in files:raise ValueError('unexpected import/code file')
   info=checked(path,{0o400,0o500})
   if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise ValueError('invalid original code file')
   found.add(relative)
 if found!=files or (root/'original-source').read_bytes()!=(source+'\n').encode():
  raise ValueError('incomplete original source frame')
except (OSError,ValueError):sys.exit(76)
PYVERIFY
  for source_path in $(_native_publication_source_paths) scripts/ci/native_publication_source.sh; do
    row=$(GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git ls-tree "$protected_source" -- "$source_path") || return 76
    case "$row" in
      100644*) [ ! -x "$code_root/$source_path" ] || return 76 ;;
      100755*) [ -x "$code_root/$source_path" ] || return 76 ;;
      *) return 76 ;;
    esac
    expected=$(GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git rev-parse "$protected_source:$source_path") || return 76
    actual=$(GIT_NO_REPLACE_OBJECTS=1 git hash-object --no-filters "$code_root/$source_path") || return 76
    [ "$expected" = "$actual" ] || return 76
  done
}

# A later publishing step in the SAME original job may reuse verified source;
# its candidate/origin/deadline remain separate original effects. The caller
# loads THIS bootstrap from the original Git object, never from rebased code.
native_publication_prepare_source() {
  local code_root="$1" protected_source="$2"
  case "$protected_source" in *[!0-9a-f]*|'') return 76 ;; esac
  [ "${#protected_source}" -eq 40 ] || return 76
  [ "$protected_source" = "${GITHUB_WORKFLOW_SHA:-}" ] || return 76
  [ "$protected_source" = "${GITHUB_SHA:-}" ] || return 76
  case "${RUNNER_TEMP:-}" in /*) : ;; *) return 76 ;; esac
  [ "${code_root%/*}" = "${RUNNER_TEMP%/}" ] || return 76
  [ "${code_root##*/}" = "native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}" ] || return 76
  if [ -e "$code_root" ] || [ -L "$code_root" ]; then
    native_publication_verify_source "$code_root" "$protected_source"
    return $?
  fi
  mkdir -m 700 -- "$code_root" || return 76
  mkdir -p -- "$code_root/scripts/ci" || return 76
  GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show \
    "$protected_source:scripts/ci/native_publication_source.sh" \
    > "$code_root/scripts/ci/native_publication_source.sh" || return 76
  native_publication_capture_source "$code_root" "$protected_source"
}
