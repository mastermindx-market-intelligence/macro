#!/usr/bin/env bash
# Transactional deployment of a clean Git archive to the authoritative VPS.
# Call through deploy_from_git.sh; arbitrary local working trees are refused.
set -euo pipefail

LOG="${MASTERMIND_DEPLOY_LOG:-/tmp/mm_vps_deploy.log}"
log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"
}

case "$(printf '%s' "${MASTERMIND_SERVE_ONLY:-}" | tr '[:upper:]' '[:lower:]')" in
  1|true|yes) log "deploy refused: serve-only mode"; exit 2 ;;
esac
if [[ "${MASTERMIND_VPS_CODE_DEPLOY:-1}" == "0" ]]; then
  log "deploy refused: MASTERMIND_VPS_CODE_DEPLOY=0"
  exit 2
fi

SRC="${MASTERMIND_DEPLOY_SOURCE:-}"
EXPECTED_SHA="${MASTERMIND_DEPLOY_EXPECT_SHA:-}"
if [[ -z "$SRC" || ! -d "$SRC" ]]; then
  echo "Use scripts/deploy_from_git.sh; a clean archive source is required." >&2
  exit 2
fi
if [[ ! "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "A full merged git SHA is required for deployment provenance." >&2
  exit 2
fi
SRC="${SRC%/}/"

BOXHOST="${MASTERMIND_VPS_HOST:-root@146.190.142.17}"
DPATH="${MASTERMIND_VPS_PATH:-/opt/mastermind}"
LIVE_DATA_PATH="${MASTERMIND_VPS_LIVE_DATA_PATH:-/opt/mastermind-live-data}"
KEY="${MASTERMIND_VPS_KEY:-/Users/chriswong/.ssh/macro_dashboard_deploy_v2}"
SVC="${MASTERMIND_VPS_SERVICE:-mastermind.service}"
HEALTH="${MASTERMIND_VPS_HEALTH:-http://127.0.0.1:8001/health}"

# Remote command parameters are literal identifiers/absolute paths in this helper.
# Refuse ambiguous override text rather than interpolate it into privileged shell commands.
for path in "$DPATH" "$LIVE_DATA_PATH"; do
  if [[ ! "$path" =~ ^/[a-zA-Z0-9_./:-]+$ || "$path" == / || "$path" == *'/../'* || "$path" == */.. ]]; then
    log "deploy refused: ambiguous remote root"
    exit 2
  fi
done
if [[ "$DPATH" == "$LIVE_DATA_PATH" || "$LIVE_DATA_PATH" == "$DPATH/"* || "$DPATH" == "$LIVE_DATA_PATH/"* ]] \
    || [[ ! "$SVC" =~ ^[a-zA-Z0-9_.@-]+$ ]]; then
  log "deploy refused: overlapping remote roots or invalid service identity"
  exit 2
fi

if [[ ! -f "$KEY" ]]; then
  log "deploy failed: SSH key is missing at $KEY"
  exit 1
fi

SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=20)
RSYNC_SSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=20"

# HTTP 200 alone is insufficient for a reasoning service: a stale environment could boot cleanly
# while silently reverting every nightly portfolio to a direct Claude backend, or an old process
# could answer after a failed restart. The open health contract exposes only non-secret policy and
# release state, so require both the Codex-first waterfall and the exact expected commit. Codex
# availability itself remains observable but is not a hard gate because the shared Claude OAuth rung
# is the authorized capacity fallback. Passing an empty SHA is reserved for verifying a rollback
# from a legacy deployment that had no valid provenance marker.
probe_health() {
  local expected_sha="${1:-}"
  local require_scheduler="${2:-1}"
  local probe
  if [[ "$expected_sha" =~ ^[0-9a-f]{40}$ ]]; then
    probe="$("${SSH[@]}" "$BOXHOST" \
      "body=\$(curl -fsS -m 6 '$HEALTH') &&
       printf '%s' \"\$body\" | grep -Eq '\"reasoning_policy_ok\"[[:space:]]*:[[:space:]]*true' &&
       { [ '$require_scheduler' != '1' ] || printf '%s' \"\$body\" | grep -Eq '\"scheduled_runtime_ok\"[[:space:]]*:[[:space:]]*true'; } &&
       printf '%s' \"\$body\" | grep -Eq '\"commit\"[[:space:]]*:[[:space:]]*\"$expected_sha\"' &&
       printf '200'" 2>/dev/null || true)"
  else
    probe="$("${SSH[@]}" "$BOXHOST" \
      "body=\$(curl -fsS -m 6 '$HEALTH') &&
       printf '%s' \"\$body\" | grep -Eq '\"reasoning_policy_ok\"[[:space:]]*:[[:space:]]*true' &&
       { [ '$require_scheduler' != '1' ] || printf '%s' \"\$body\" | grep -Eq '\"scheduled_runtime_ok\"[[:space:]]*:[[:space:]]*true'; } &&
       printf '200'" 2>/dev/null || true)"
  fi
  if [[ "$probe" == "200" ]]; then
    printf '200'
  else
    printf '503'
  fi
}

# A healthy code process is not a complete v2 release until the immutable cohort marker is active.
# The CLI exits non-zero for both a missing marker and pending_health, so interrupted/no-op deploys
# are forced back through the bounded release transaction instead of silently staying not_started.
probe_forward_evaluation() {
  "${SSH[@]}" "$BOXHOST" \
    "cd '$DPATH' &&
     MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT='$LIVE_DATA_PATH' \
       python3 -m portfolio.forward_evaluation status >/dev/null" \
    >>"$LOG" 2>&1
}

# One filter policy for transfer, complete snapshot and restoration.
EXC=(
  --exclude='.git' --exclude='.github'
  --exclude='.worktrees' --exclude='.venv' --exclude='venv'
  --exclude='data' --exclude='vendor' --exclude='vendor_*'
  --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo'
  --exclude='node_modules' --exclude='*.sqlite' --exclude='*.sqlite-*'
  --exclude='*.db' --exclude='*.log' --exclude='.DS_Store' --exclude='*.lock'
  --exclude='.pytest_cache' --exclude='.mypy_cache' --exclude='.ruff_cache'
  --exclude='.env' --exclude='.env.*' --exclude='tmp' --exclude='catboost_info'
  --exclude='{_DB}' --exclude='tests' --exclude='.deploy_prev'
  --exclude='.deployed_git_sha'
)

if ! "${SSH[@]}" "$BOXHOST" \
  "[ -d '$DPATH' ] && [ -d '$LIVE_DATA_PATH' ] &&
   [ \"\$(cd '$DPATH' && pwd -P)\" = '$DPATH' ] &&
   [ \"\$(cd '$LIVE_DATA_PATH' && pwd -P)\" = '$LIVE_DATA_PATH' ]"; then
  log "deploy refused: remote roots are missing or noncanonical"
  exit 2
fi

RAW="$(rsync -azcn --delete --out-format='%n' -e "$RSYNC_SSH" \
  "${EXC[@]}" "$SRC" "$BOXHOST:$DPATH/")" || {
    log "deploy failed: VPS dry-run/SSH check failed"
    exit 1
  }
CHANGED="$(printf '%s\n' "$RAW" | grep -vE '/$|^$' || true)"
N="$(printf '%s\n' "$CHANGED" | grep -c . || true)"

if [[ "${N:-0}" -eq 0 ]] && [[ "$(probe_health "$EXPECTED_SHA")" == "200" ]] \
    && probe_forward_evaluation; then
  log "deploy no-op: $EXPECTED_SHA already in sync and healthy"
  exit 0
fi

if [[ "${N:-0}" -eq 0 ]]; then
  log "code is in sync but release attestation or policy is stale; refreshing $EXPECTED_SHA"
else
  log "deploying $EXPECTED_SHA ($N changed path(s))"
fi
printf '%s\n' "$CHANGED" | sed 's/^/    /' | tee -a "$LOG"

PREVIOUS_SHA="$("${SSH[@]}" "$BOXHOST" \
  "cat '$DPATH/.deployed_git_sha' 2>/dev/null || true" 2>/dev/null || true)"
if [[ ! "$PREVIOUS_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  PREVIOUS_SHA=""
fi

# The same filters govern live replacement, snapshot and restoration. In particular,
# --delete must never remove excluded live data, including excluded descendants.
printf -v REMOTE_EXCLUDES ' %q' "${EXC[@]}"
SNAPSHOT_PATH=""
SNAPSHOT_READY=0
TREE_MUTATION_STARTED=0
RECOVERY_NEEDED=0
RELEASE_COMMITTED=0
FAILURE_REASON="unexpected shell failure"
FORWARD_START_ACTIVE=0
FORWARD_VERIFICATION_FAILED=0

read_forward_marker_identity() {
  "${SSH[@]}" "$BOXHOST" \
    "path='$LIVE_DATA_PATH/portfolio_forward_evaluation/start.json'
     if [ -f \"\$path\" ] && [ ! -L \"\$path\" ]; then
       sha256sum -- \"\$path\" | awk '{print \$1}'
     elif [ ! -e \"\$path\" ] && [ ! -L \"\$path\" ]; then
       printf missing
     else
       exit 1
     fi"
}

# Observe before retrying a stop whose reply was lost. Always issue the explicit
# stop as well: Restart=always may have a queued restart even when no PID is live.
# This covers the configured service, not detached writers or another deployer.
stop_service() {
  "${SSH[@]}" "$BOXHOST" \
    "set -e
     before=\$(systemctl show '$SVC' --property=ActiveState --property=MainPID)
     [ -n \"\$before\" ]
     systemctl stop '$SVC'
     state=\$(systemctl show '$SVC' --property=ActiveState --property=MainPID)
     printf '%s\\n' \"\$state\" | grep -Eq '^ActiveState=(inactive|failed)$' &&
     printf '%s\\n' \"\$state\" | grep -Eq '^MainPID=0$'" >>"$LOG" 2>&1
}

rollback_release() {
  local reason="$1"
  local current_marker=""
  local forward_state_changed=0
  log "deploy failed: $reason; rolling back"
  if ! stop_service; then
    log "recovery incomplete: service stop is unverified; source was not restored"
    return 1
  fi
  if [[ "$TREE_MUTATION_STARTED" -eq 1 ]]; then
    if [[ "$SNAPSHOT_READY" -ne 1 ]]; then
      log "recovery incomplete: no verified snapshot; leaving service stopped"
      return 1
    fi
    # Checksum comparison avoids the size+mtime quick-check collision. Verification
    # must succeed before restarting; an incomplete restore never boots a mixed tree.
    if ! "${SSH[@]}" "$BOXHOST" \
      "set -e
       rsync -ac --delete $REMOTE_EXCLUDES '$SNAPSHOT_PATH/tree/' '$DPATH/'
       difference=\$(rsync -acn --delete --itemize-changes $REMOTE_EXCLUDES '$SNAPSHOT_PATH/tree/' '$DPATH/')
       [ -z \"\$difference\" ]
       if [ -f '$SNAPSHOT_PATH/deployed_git_sha' ]; then
         cp -a '$SNAPSHOT_PATH/deployed_git_sha' '$DPATH/.deployed_git_sha'
       elif [ -f '$SNAPSHOT_PATH/deployed_git_sha.absent' ]; then
         rm -f '$DPATH/.deployed_git_sha'
       else
         exit 1
       fi
       if [ -f '$SNAPSHOT_PATH/datadog.enabled' ]; then
         tag='/etc/systemd/system/$SVC.d/81-datadog-version.conf'
         if [ -f '$SNAPSHOT_PATH/datadog_version' ]; then
           cp -a '$SNAPSHOT_PATH/datadog_version' \"\$tag\"
         elif [ -f '$SNAPSHOT_PATH/datadog_version.absent' ]; then
           rm -f \"\$tag\"
         else
           exit 1
         fi
         systemctl daemon-reload
       fi" >>"$LOG" 2>&1; then
      log "recovery incomplete: source/metadata restoration failed verification; leaving service stopped"
      return 1
    fi
  else
    log "recovery: live tree was not changed; incomplete snapshots are not used"
  fi
  # Never delete or rewind start.json: earlier absence, a matching release SHA,
  # and even a lost init response do not establish exclusive transition ownership.
  if ! current_marker="$(read_forward_marker_identity 2>>"$LOG")"; then
    current_marker="unknown"
  fi
  if [[ "$current_marker" != "$FORWARD_START_IDENTITY" ]]; then
    forward_state_changed=1
    log "forward evaluation state reconciliation required (marker retained)"
  fi
  if [[ "$FORWARD_VERIFICATION_FAILED" -eq 1 ]]; then
    forward_state_changed=1
    log "forward evaluation authority/state reconciliation required (runtime data retained)"
  fi
  if ! "${SSH[@]}" "$BOXHOST" "systemctl restart '$SVC'" >>"$LOG" 2>&1; then
    log "recovery incomplete: restored service restart failed"
    return 1
  fi
  sleep 4
  CODE="$(probe_health "$PREVIOUS_SHA")"
  if [[ "$CODE" != "200" ]]; then
    log "recovery incomplete: restored health returned $CODE"
    return 1
  fi
  if [[ "$forward_state_changed" -eq 1 ]]; then
    log "recovery incomplete: code health restored; forward evaluation authority/state reconciliation required (runtime data retained)"
    return 1
  fi
  log "code rollback verified; health returned $CODE; runtime data retained"
}

finish_release() {
  local status="$1"
  trap - EXIT INT TERM
  if [[ "$RELEASE_COMMITTED" -ne 1 && "$RECOVERY_NEEDED" -eq 1 ]]; then
    rollback_release "$FAILURE_REASON" || true
    [[ "$status" -ne 0 ]] || status=1
  fi
  exit "$status"
}
fail_release() {
  FAILURE_REASON="$1"
  exit 1
}
trap 'finish_release $?' EXIT
trap 'FAILURE_REASON="interrupted by SIGINT"; exit 130' INT
trap 'FAILURE_REASON="interrupted by SIGTERM"; exit 143' TERM

FORWARD_START_IDENTITY="$(read_forward_marker_identity)" || {
  log "deploy failed: could not resolve forward evaluation marker identity"
  exit 1
}
if [[ "$FORWARD_START_IDENTITY" != "missing" && ! "$FORWARD_START_IDENTITY" =~ ^[0-9a-f]{64}$ ]]; then
  log "deploy failed: invalid forward evaluation marker identity"
  exit 1
fi
if [[ "$FORWARD_START_IDENTITY" != "missing" ]] && probe_forward_evaluation; then
  FORWARD_START_ACTIVE=1
fi
RECOVERY_NEEDED=1
if ! stop_service; then
  fail_release "service stop before source replacement failed"
fi

# Receipt v2 strengthens the immutable settlement preimage.  A pre-release WAL or older receipt
# must be finalized by the currently deployed code before the runtime reader changes; deploying
# across one would strand a committed book behind an intentionally fail-closed schema boundary.
# Match the reader's top-level *.json glob, including invalid directories or symlinks;
# an unreadable receipt entry is a refusal, not evidence of an empty outbox.
SETTLEMENT_STATE_GATE=""
if ! SETTLEMENT_STATE_GATE="$("${SSH[@]}" "$BOXHOST" \
  "set -e
   for book in autonomous china hk; do
     book_dir='$LIVE_DATA_PATH/portfolios/'\"\$book\"
     if [ -e \"\$book_dir/paper_transaction.json\" ]; then
       printf 'unresolved_wal:%s\\n' \"\$book\"
       exit 21
     fi
     if [ -d \"\$book_dir/settlement_receipts\" ]; then
       if ! receipt_entry=\$(find -H \"\$book_dir/settlement_receipts\" -mindepth 1 -maxdepth 1 \
                              -name '*.json' -print -quit); then
         printf 'receipt_scan_failed:%s\\n' \"\$book\"
         exit 23
       fi
       if [ -n \"\$receipt_entry\" ]; then
         printf 'unfinalized_receipt:%s\\n' \"\$book\"
         exit 22
       fi
     fi
   done
   printf 'clean\\n'" 2>&1)"; then
  printf '%s\n' "$SETTLEMENT_STATE_GATE" >>"$LOG"
  fail_release "unresolved paper settlement state blocks receipt-schema upgrade"
fi
printf '%s\n' "$SETTLEMENT_STATE_GATE" >>"$LOG"
if [[ "$SETTLEMENT_STATE_GATE" != "clean" ]]; then
  fail_release "paper settlement state gate returned an invalid result"
fi

# Bind the pending cohort to the exact canonical US account/fill bytes observed while the configured
# service is stopped. Missing or unreadable authority artifacts are a release failure, never an empty
# baseline.  The hashes stay in the deploy process only; runtime state remains on the VPS.
FORWARD_BASELINE_HASHES=""
if ! FORWARD_BASELINE_HASHES="$("${SSH[@]}" "$BOXHOST" \
  "set -e
   account_path='$LIVE_DATA_PATH/portfolios/autonomous/account.json'
   fills_path='$LIVE_DATA_PATH/portfolios/autonomous/fills.jsonl'
   [ -f \"\$account_path\" ] && [ -r \"\$account_path\" ]
   [ -f \"\$fills_path\" ] && [ -r \"\$fills_path\" ]
   sha256sum -- \"\$account_path\" \"\$fills_path\"" 2>&1)"; then
  printf '%s\n' "$FORWARD_BASELINE_HASHES" >>"$LOG"
  fail_release "forward evaluation authority-byte baseline failed"
fi
printf '%s\n' "$FORWARD_BASELINE_HASHES" >>"$LOG"
FORWARD_ACCOUNT_SHA="$(printf '%s\n' "$FORWARD_BASELINE_HASHES" | sed -n '1s/[[:space:]].*//p')"
FORWARD_FILLS_SHA="$(printf '%s\n' "$FORWARD_BASELINE_HASHES" | sed -n '2s/[[:space:]].*//p')"
if [[ ! "$FORWARD_ACCOUNT_SHA" =~ ^[0-9a-f]{64}$ ]] \
    || [[ ! "$FORWARD_FILLS_SHA" =~ ^[0-9a-f]{64}$ ]]; then
  fail_release "forward evaluation authority-byte baseline was invalid"
fi
# Preserve the previous complete backup until this attempt has a verified snapshot.
# These directories are ordinary artifacts of the existing helper, not a release queue.
if ! SNAPSHOT_PATH="$("${SSH[@]}" "$BOXHOST" \
  "[ ! -L '$DPATH/.deploy_prev' ] && mkdir -p '$DPATH/.deploy_prev' && mktemp -d '$DPATH/.deploy_prev/snapshot.XXXXXX'")"; then
  fail_release "snapshot directory creation failed"
fi
if [[ "$SNAPSHOT_PATH" != "$DPATH/.deploy_prev/snapshot."* ]] \
    || [[ ! "$SNAPSHOT_PATH" =~ ^/[a-zA-Z0-9_./:-]+$ ]]; then
  fail_release "snapshot directory identity was invalid"
fi
if ! "${SSH[@]}" "$BOXHOST" \
  "set -e
   mkdir '$SNAPSHOT_PATH/tree'
   rsync -ac --delete $REMOTE_EXCLUDES '$DPATH/' '$SNAPSHOT_PATH/tree/'
   difference=\$(rsync -acn --delete --itemize-changes $REMOTE_EXCLUDES '$DPATH/' '$SNAPSHOT_PATH/tree/')
   [ -z \"\$difference\" ]
   if [ -f '$DPATH/.deployed_git_sha' ] && [ ! -L '$DPATH/.deployed_git_sha' ]; then
     cp -a '$DPATH/.deployed_git_sha' '$SNAPSHOT_PATH/deployed_git_sha'
   elif [ ! -e '$DPATH/.deployed_git_sha' ] && [ ! -L '$DPATH/.deployed_git_sha' ]; then
     touch '$SNAPSHOT_PATH/deployed_git_sha.absent'
   else
     exit 1
   fi
   if [ -f '/etc/systemd/system/$SVC.d/80-datadog.conf' ]; then
     touch '$SNAPSHOT_PATH/datadog.enabled'
     tag='/etc/systemd/system/$SVC.d/81-datadog-version.conf'
     if [ -f \"\$tag\" ] && [ ! -L \"\$tag\" ]; then
       cp -a \"\$tag\" '$SNAPSHOT_PATH/datadog_version'
     elif [ ! -e \"\$tag\" ] && [ ! -L \"\$tag\" ]; then
       touch '$SNAPSHOT_PATH/datadog_version.absent'
     else
       exit 1
     fi
   fi
   touch '$SNAPSHOT_PATH/complete'" >>"$LOG" 2>&1; then
  fail_release "complete code snapshot failed"
fi
SNAPSHOT_READY=1

# Mark possible mutation before rsync; failure or transport loss may be partial.
TREE_MUTATION_STARTED=1
if ! rsync -azc --delete --out-format='%n' -e "$RSYNC_SSH" \
  "${EXC[@]}" "$SRC" "$BOXHOST:$DPATH/" >>"$LOG" 2>&1; then
  fail_release "rsync did not complete"
fi
if ! "${SSH[@]}" "$BOXHOST" \
  "set -e
   tmp=\$(mktemp '$DPATH/.deployed_git_sha.tmp.XXXXXX')
   trap 'rm -f \"\$tmp\"' EXIT
   printf '%s\n' '$EXPECTED_SHA' > \"\$tmp\"
   chmod 0644 \"\$tmp\"
   mv -f \"\$tmp\" '$DPATH/.deployed_git_sha'"; then
  fail_release "release marker write failed"
fi
if ! "${SSH[@]}" "$BOXHOST" \
  "if [ -x '$DPATH/scripts/refresh_datadog_release_tag.sh' ]; then
     MASTERMIND_SERVICE='$SVC' '$DPATH/scripts/refresh_datadog_release_tag.sh' '$EXPECTED_SHA'
   fi"; then
  fail_release "Datadog release tag refresh failed"
fi

# An established cohort is immutable across upgrades. Do not silently recreate it
# if it disappears after the preimage was observed; init/finalize are no-ops for it.
if [[ "$FORWARD_START_ACTIVE" -eq 1 ]]; then
  if [[ "$(read_forward_marker_identity 2>>"$LOG" || true)" != "$FORWARD_START_IDENTITY" ]]; then
    fail_release "established forward evaluation marker changed; reconciliation required"
  fi
else
  FORWARD_INIT_OUTPUT=""
  if ! FORWARD_INIT_OUTPUT="$("${SSH[@]}" "$BOXHOST" \
    "cd '$DPATH' &&
     MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT='$LIVE_DATA_PATH' \
       python3 -m portfolio.forward_evaluation init \
         --deployment-sha '$EXPECTED_SHA' --asof \"\$(date -u +%F)\"" 2>&1)"; then
    printf '%s\n' "$FORWARD_INIT_OUTPUT" >>"$LOG"
    fail_release "forward evaluation pending start initialization failed"
  fi
  printf '%s\n' "$FORWARD_INIT_OUTPUT" >>"$LOG"
fi

if ! "${SSH[@]}" "$BOXHOST" "systemctl restart '$SVC'"; then
  fail_release "service restart failed"
fi
CODE="000"
for _ in 1 2 3 4 5 6 7 8; do
  sleep 3
  CODE="$(probe_health "$EXPECTED_SHA")"
  [[ "$CODE" == "200" ]] && break
done

if [[ "$CODE" == "200" ]]; then
  # Activate only after the exact commit, provider policy, and scheduled runtime pass health.
  # The canonical book lock spans compare -> finalize -> status for cooperating book writers.
  # finalize is idempotent for an active marker; unrelated writers remain outside this lock.
  if ! "${SSH[@]}" "$BOXHOST" \
    "set -e
     cd '$DPATH'
     lock_path='$LIVE_DATA_PATH/locks/book:autonomous.lock'
     account_path='$LIVE_DATA_PATH/portfolios/autonomous/account.json'
     fills_path='$LIVE_DATA_PATH/portfolios/autonomous/fills.jsonl'
     mkdir -p \"\$(dirname \"\$lock_path\")\"
     exec 9>>\"\$lock_path\"
     flock -x -w 30 9
     [ -f \"\$account_path\" ] && [ -r \"\$account_path\" ]
     [ -f \"\$fills_path\" ] && [ -r \"\$fills_path\" ]
     account_sha=\$(sha256sum -- \"\$account_path\" | awk '{print \$1}')
     fills_sha=\$(sha256sum -- \"\$fills_path\" | awk '{print \$1}')
     [ \"\$account_sha\" = '$FORWARD_ACCOUNT_SHA' ]
     [ \"\$fills_sha\" = '$FORWARD_FILLS_SHA' ]
     if [ '$FORWARD_START_ACTIVE' != '1' ]; then
       MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT='$LIVE_DATA_PATH' \
         python3 -m portfolio.forward_evaluation finalize --deployment-sha '$EXPECTED_SHA'
     fi
     MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT='$LIVE_DATA_PATH' \
       python3 -m portfolio.forward_evaluation status >/dev/null" \
    >>"$LOG" 2>&1; then
    FORWARD_VERIFICATION_FAILED=1
    log "forward evaluation authority bytes changed, missing, unreadable, or lock verification failed"
    fail_release "forward evaluation activation/status verification failed"
  fi
  if [[ "$FORWARD_START_ACTIVE" -eq 1 ]] \
      && [[ "$(read_forward_marker_identity 2>>"$LOG" || true)" != "$FORWARD_START_IDENTITY" ]]; then
    fail_release "established forward evaluation marker changed; reconciliation required"
  fi
  RELEASE_COMMITTED=1
  log "deploy OK: $SVC healthy at commit $EXPECTED_SHA"
  exit 0
fi

fail_release "health check returned $CODE"
