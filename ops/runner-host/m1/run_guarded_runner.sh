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
# ── AD-1T2 PROFILE BINDING ───────────────────────────────────────────────────
# Each runner root carries the runner's canonical name (the basename of its
# directory — e.g. `m1-canary` or `m1-nightly-2`). The admission hook profile
# is derived from THAT name, never from the host's hostname, so the canary
# root preserves its existing profile and only the new m1-nightly-2 root
# receives the AD-1T2 producer-lane profile. This is the binding the ruling
# pins: profile m1-nightly-2 is allowed ONLY on the runner named m1-nightly-2,
# preserving every other runner's profile intact.
case "$(basename "$runner_root")" in
  m1-nightly-2)
    export ACTIONS_RUNNER_HOOK_JOB_STARTED="$guard_root/runner_admission_m1_nightly_2.js"
    export MASTERMIND_CI_PROFILE=m1-nightly-2
    ;;
  *)
    export ACTIONS_RUNNER_HOOK_JOB_STARTED="$guard_root/runner_admission_m1_canary.js"
    export MASTERMIND_CI_PROFILE=m1-canary
    ;;
esac
cd "$runner_root"
exec "$runner_root/bin/Runner.Listener" run --startuptype service
