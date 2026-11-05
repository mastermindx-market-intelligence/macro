#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/government-revenue-live.yml
# Read ONLY the same original intent; no publication/proof retry.
set -euo pipefail
[ -n "${NATIVE_ORIGINAL_RECORD:-}" ] || exit 0
if [ "${GITHUB_REPOSITORY:-}" = mastermindx-market-intelligence/macro ]; then
  umask 077
  native_code_root="${RUNNER_TEMP%/}/native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}"
  native_bootstrap="${RUNNER_TEMP%/}/native-publication-bootstrap-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}-${NATIVE_PUBLICATION_PUBLISHING_STEP}.sh"
  case "$(GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git ls-tree "$GITHUB_WORKFLOW_SHA" -- scripts/ci/native_publication_source.sh)" in
    100644*) : ;; *) exit 76 ;;
  esac
  (set -o noclobber; GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show "$GITHUB_WORKFLOW_SHA:scripts/ci/native_publication_source.sh" > "$native_bootstrap")
  . "$native_bootstrap"
  native_publication_prepare_source "$native_code_root" "$GITHUB_WORKFLOW_SHA"
  . "$native_code_root/scripts/ci/push_retry.sh"
else
  . "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
fi
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_native_settle \
  --root "$GITHUB_WORKSPACE" --record "$NATIVE_ORIGINAL_RECORD" --deadline "$NATIVE_ORIGINAL_DEADLINE" \
  --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json" --identity "$GOVREV_ORIGINAL_PUSH_IDENTITY" \
  --out "$RUNNER_TEMP/govrev-candidate-proof.publication.json"
