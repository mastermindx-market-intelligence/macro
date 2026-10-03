#!/bin/bash
set -euo pipefail

runner_root=${1:?runner root is required}
guard_root=${2:?guard root is required}

if ! "$guard_root/runner_disk_guard.py" --path "$runner_root" --mode lightweight; then
  # Disk pressure must not become a tight launchd crash loop. The listener remains
  # absent while this bounded backoff runs; launchd can retry after the host recovers.
  sleep 900
  exit 75
fi

"$guard_root/runner_log_maintenance.py" --diag "$runner_root/_diag"

# launchd, not the runner's nested Node service wrapper, owns restart semantics.
# Keeping Runner.Listener as the plist's final process makes a controlled listener
# crash observable as one launchd run transition instead of an invisible child retry.
if [ -f "$runner_root/.path" ]; then
  export PATH
  PATH=$(cat "$runner_root/.path")
fi
if [ -f "$runner_root/.env" ]; then
  while IFS='=' read -r key value; do
    case "$key" in
      ''|*[!A-Za-z0-9_]*) continue ;;
    esac
    export "$key=$value"
  done < "$runner_root/.env"
fi
# ── AD-1T2 PROFILE BINDING (fail-closed trusted-local-identity) ────────────
# Profile binding is driven by the *configured* agentName written into
# `.runner` by the official `config.sh` registration — NEVER by the directory
# basename. The canary default binding is preserved for every existing M1
# listener; the new m1-nightly-2 binding activates only when the canonical
# runner root AND the configured agentName both match the production pair.
# A misrouted, missing, unreadable, malformed or mismatched `.runner` exits
# 78 (EX_CONFIG) BEFORE Runner.Listener starts, so launchd can retry after
# the host operator fixes the real fault rather than launching a listener
# that has silently lost its admission surface. No workflow-injected env
# override and no friendly-directory-name assumption — see
# `ops/runner-host/common/runner_binding.py` for the (root, agentName)
# canonical table the wrapper consults.
binding_line=$("$guard_root/runner_binding.py" "$runner_root") \
  || {
    # runner_binding already printed ::error title=runner-binding::… and exited 78.
    exit 78
  }
export RUNNER_BINDING="$binding_line"
# Pull the profile out of the JSON the helper emitted. python3 is the only
# portable JSON parser on the M1 host (no jq, no jq -e at the wrapper
# boundary); the helper contract pins the schema field so this stays cheap.
# The helper emits `RUNNER_BINDING=<json>`; its `--extract-profile`
# subcommand expects the bare JSON payload plus the field key (rawjson +
# key, both required — see runner_binding.py main()), so we validate the
# exact prefix here, strip it into `binding_payload`, and pass the key
# explicitly. A missing prefix, malformed line, or extraction failure all
# exit 78 BEFORE Runner.Listener starts, so launchd can retry after the
# host operator fixes the real fault rather than launching a listener that
# has silently lost its admission surface. The original `RUNNER_BINDING=...`
# line is preserved verbatim for `_diag` forensics.
case "$binding_line" in
  RUNNER_BINDING=*)
    binding_payload=${binding_line#RUNNER_BINDING=}
    ;;
  *)
    echo "::error title=runner-binding::expected RUNNER_BINDING= prefix, got: $binding_line" >&2
    exit 78
    ;;
esac
profile=$("$guard_root/runner_binding.py" --extract-profile "$binding_payload" profile) \
  || {
    echo "::error title=runner-binding::could not extract profile from $binding_payload" >&2
    exit 78
  }
case "$profile" in
  m1-nightly-2)
    export ACTIONS_RUNNER_HOOK_JOB_STARTED="$guard_root/runner_admission_m1_nightly_2.js"
    export MASTERMIND_CI_PROFILE=m1-nightly-2
    ;;
  m1-canary)
    export ACTIONS_RUNNER_HOOK_JOB_STARTED="$guard_root/runner_admission_m1_canary.js"
    export MASTERMIND_CI_PROFILE=m1-canary
    ;;
  *)
    echo "::error title=runner-binding::unknown profile $profile from $binding_line" >&2
    exit 78
    ;;
esac
cd "$runner_root"
exec "$runner_root/bin/Runner.Listener" run --startuptype service
