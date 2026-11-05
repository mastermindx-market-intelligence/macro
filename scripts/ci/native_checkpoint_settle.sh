#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# Final original checkpoint readback; no second intent or publication retry.
set -euo pipefail
umask 077
if [ -z "${NATIVE_ORIGINAL_RECORD:-}" ]; then
  # Legacy checkpoint already performed its guarded publication and R2 fence.
  if [ "${LEGACY_R2_READY:-}" = true ]; then
    [[ "$LEGACY_SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
    [[ "$NATIVE_INDEX_SHA256" =~ ^[0-9a-f]{64}$ ]]
    printf 'r2_ready=true\ncheckpoint_sha=%s\nindex_sha256=%s\n' \
      "$LEGACY_SOURCE_SHA" "$NATIVE_INDEX_SHA256" >> "$GITHUB_OUTPUT"
  fi
  exit 0
fi
native_code_root="${RUNNER_TEMP%/}/native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}"
native_bootstrap="${RUNNER_TEMP%/}/native-publication-final-bootstrap-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}-${NATIVE_PUBLICATION_PUBLISHING_STEP}.sh"
case "$(GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git ls-tree "$GITHUB_WORKFLOW_SHA" -- scripts/ci/native_publication_source.sh)" in
  100644*) : ;; *) exit 76 ;;
esac
(set -o noclobber; GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show "$GITHUB_WORKFLOW_SHA:scripts/ci/native_publication_source.sh" > "$native_bootstrap")
. "$native_bootstrap"
native_publication_prepare_source "$native_code_root" "$GITHUB_WORKFLOW_SHA"
args=(--root "$GITHUB_WORKSPACE" --record "$NATIVE_ORIGINAL_RECORD" --deadline "$NATIVE_ORIGINAL_DEADLINE")
if [ -z "${CHECKPOINT_ROOT:-}" ]; then
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.native_queue_push settle "${args[@]}" --write-output
  exit 0
fi
[ -z "${NATIVE_INDEX_SHA256:-}" ] || args+=(--index-sha256 "$NATIVE_INDEX_SHA256")
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.native_checkpoint "${args[@]}"
# The API settlement above is read-only. Reclaim ONLY the exact same original
# clean checkpoint worktree after actual protected publication, never on pending
# or UNKNOWN. This is local caller-owned temporary source, not a Fabric lease.
python3 -I - "$NATIVE_ORIGINAL_RECORD" "$CHECKPOINT_ROOT" "$CHECKPOINT_DIR" "$CHECKPOINT_BRANCH" <<'PYCLEAN'
import json,os,re,stat,subprocess,sys
from pathlib import Path
record,root,directory,branch=sys.argv[1:]
temp=Path(os.environ['RUNNER_TEMP']).resolve();root=Path(root);directory=Path(directory)
try:
 if root.parent.resolve()!=temp or directory!=root/'tree':raise ValueError('checkpoint scope')
 if not re.fullmatch(r'(?:leader|prophet|prophet-stage)-checkpoint\.[A-Za-z0-9]+',root.name):raise ValueError('checkpoint namespace')
 profile={'leader':'leader','prophet':'prophet','prophet-stage':'prophet_stage'}[root.name.split('-checkpoint.',1)[0]]
 if branch!='_'+profile+'_checkpoint_'+os.environ['GITHUB_RUN_ID']+'_'+os.environ['GITHUB_RUN_ATTEMPT']:raise ValueError('checkpoint branch')
 for p in (root,directory):
  info=p.lstat()
  if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid!=os.getuid():raise ValueError('checkpoint ownership')
 candidate=json.loads(Path(record).read_text())['producer_origin']['published_source_head']
 def git(*args):return subprocess.run(['git','-C',str(directory),*args],check=True,capture_output=True,text=True).stdout.strip()
 if git('rev-parse','HEAD')!=candidate or git('symbolic-ref','--short','HEAD')!=branch or git('status','--porcelain','--untracked-files=all'):raise ValueError('checkpoint changed')
 workspace=os.environ['GITHUB_WORKSPACE']
 def remove(*args):subprocess.run(['git','-C',workspace,*args],check=True)
 remove('worktree','remove',str(directory))
 # Exact old-object CAS protects a concurrently changed ref, including squash
 # publication where the original candidate is not main ancestry.
 remove('update-ref','-d','refs/heads/'+branch,candidate)
 root.rmdir()
except (OSError,ValueError,KeyError,subprocess.SubprocessError):sys.exit(76)
PYCLEAN
