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

# Whole-source rsync also ships these shared Python packages; rollback must restore them.
DIRS="app brain bot portfolio data_layer loop bridge control_plane scripts config ops common integrations .claude .codex"
FILES="pyproject.toml DOCTRINE.md README.md AGENTS.md .deployed_git_sha"
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

RAW="$(rsync -azn --delete --out-format='%n' -e "$RSYNC_SSH" \
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

FORWARD_START_STATE="$("${SSH[@]}" "$BOXHOST" \
  "if [ -e '$LIVE_DATA_PATH/portfolio_forward_evaluation/start.json' ]; then printf present; else printf missing; fi" \
  2>/dev/null || true)"
if [[ "$FORWARD_START_STATE" != "present" && "$FORWARD_START_STATE" != "missing" ]]; then
  log "deploy failed: could not resolve forward evaluation marker state"
  exit 1
fi
FORWARD_START_CREATED=0

"${SSH[@]}" "$BOXHOST" \
  "cd '$DPATH' &&
   rm -rf .deploy_prev &&
   mkdir -p .deploy_prev &&
   for d in $DIRS; do [ ! -e \"\$d\" ] || cp -a \"\$d\" .deploy_prev/; done &&
   for f in $FILES; do [ ! -e \"\$f\" ] || cp -a \"\$f\" .deploy_prev/; done"

# From this point forward the remote release tree is mutable. Every failure—including a partial
# rsync, marker write, or restart transport error—must take the identical bounded restore path.
# Otherwise the next service restart could boot a mixture of old and new code that never reached a
# health probe. The backup directory itself is excluded from rsync, so it survives partial copies.
rollback_release() {
  local reason="$1"
  local restore_status=0
  log "deploy failed: $reason; rolling back"
  if [[ "$FORWARD_START_CREATED" -eq 1 ]]; then
    if ! "${SSH[@]}" "$BOXHOST" \
      "rm -f '$LIVE_DATA_PATH/portfolio_forward_evaluation/start.json'"; then
      restore_status=1
      log "rollback could not remove the pending forward evaluation marker"
    fi
  fi
  if ! "${SSH[@]}" "$BOXHOST" \
    "cd '$DPATH' &&
     restore_failed=0
     for d in $DIRS; do
       if [ -e \".deploy_prev/\$d\" ]; then
         rm -rf \"\$d\" && cp -a \".deploy_prev/\$d\" \"\$d\" || restore_failed=1
       else
         # A directory introduced by the failed release has no previous snapshot. Remove that
         # bounded release path so rolled-back code cannot observe a mismatched agent policy.
         rm -rf \"\$d\" || restore_failed=1
       fi
     done
     for f in $FILES; do
       if [ -e \".deploy_prev/\$f\" ]; then
         cp -a \".deploy_prev/\$f\" \"\$f\" || restore_failed=1
       else
         rm -f \"\$f\" || restore_failed=1
       fi
     done
     if [ -f "/etc/systemd/system/$SVC.d/80-datadog.conf" ]; then
       if [ -n '$PREVIOUS_SHA' ]; then
         printf '[Service]\nEnvironment=DD_VERSION=%s\n' '$PREVIOUS_SHA' > "/etc/systemd/system/$SVC.d/81-datadog-version.conf" || restore_failed=1
       else
         rm -f "/etc/systemd/system/$SVC.d/81-datadog-version.conf" || restore_failed=1
       fi
       systemctl daemon-reload || restore_failed=1
     fi
     systemctl restart '$SVC'
     restart_status=\$?
     [ \"\$restore_failed\" -eq 0 ] && [ \"\$restart_status\" -eq 0 ]"; then
    restore_status=1
    log "rollback transport or restore command failed"
  fi
  sleep 4
  CODE="$(probe_health "$PREVIOUS_SHA" 0)"
  log "rollback complete; health returned $CODE"
  return "$restore_status"
}

fail_release() {
  rollback_release "$1" || true
  exit 1
}

if ! rsync -az --delete --out-format='%n' -e "$RSYNC_SSH" \
  "${EXC[@]}" "$SRC" "$BOXHOST:$DPATH/" >>"$LOG" 2>&1; then
  fail_release "rsync did not complete"
fi

# The application resolves this marker once at startup. Write it before the restart so the
# first health response can attest the exact code archive that was just synchronized.
if ! "${SSH[@]}" "$BOXHOST" \
  "printf '%s\n' '$EXPECTED_SHA' > '$DPATH/.deployed_git_sha'"; then
  fail_release "release marker write failed"
fi
if ! "${SSH[@]}" "$BOXHOST" \
  "if [ -x '$DPATH/scripts/refresh_datadog_release_tag.sh' ]; then
     '$DPATH/scripts/refresh_datadog_release_tag.sh' '$EXPECTED_SHA';
   fi"; then
  fail_release "Datadog release tag refresh failed"
fi

# Freeze durable portfolio writers before taking the one-time legacy baseline.  pending_health is
# deliberately inert, so target schedulers may start for the health probe without emitting an
# evaluation snapshot.  Exact-SHA health below is the only operation that activates the cohort.
if ! "${SSH[@]}" "$BOXHOST" "systemctl stop '$SVC'"; then
  fail_release "service stop before forward evaluation baseline failed"
fi

# Receipt v2 strengthens the immutable settlement preimage.  A pre-release WAL or older receipt
# must be finalized by the currently deployed code before the runtime reader changes; deploying
# across one would strand a committed book behind an intentionally fail-closed schema boundary.
SETTLEMENT_STATE_GATE=""
if ! SETTLEMENT_STATE_GATE="$("${SSH[@]}" "$BOXHOST" \
  "set -e
   for book in autonomous china hk; do
     book_dir='$LIVE_DATA_PATH/portfolios/'\"\$book\"
     if [ -e \"\$book_dir/paper_transaction.json\" ]; then
       printf 'unresolved_wal:%s\\n' \"\$book\"
       exit 21
     fi
     if [ -d \"\$book_dir/settlement_receipts\" ] \
        && find \"\$book_dir/settlement_receipts\" -maxdepth 1 -type f -name '*.json' \
             -print -quit | grep -q .; then
       printf 'unfinalized_receipt:%s\\n' \"\$book\"
       exit 22
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

# Bind the pending cohort to the exact canonical US account/fill bytes observed while no service
# writer can run.  Missing or unreadable authority artifacts are a release failure, never an empty
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
if [[ "$FORWARD_START_STATE" == "missing" ]]; then
  FORWARD_START_CREATED=1
fi
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
if [[ "$FORWARD_START_CREATED" -eq 1 ]] \
    && ! printf '%s' "$FORWARD_INIT_OUTPUT" | grep -Eq '"initialized"[[:space:]]*:[[:space:]]*true'; then
  # A concurrent valid initializer won the create-once race; it is not ours to remove on rollback.
  FORWARD_START_CREATED=0
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
  # The canonical book lock spans compare -> finalize -> status, preventing a service writer from
  # slipping between byte verification and activation. finalize is idempotent for an active marker.
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
     MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT='$LIVE_DATA_PATH' \
       python3 -m portfolio.forward_evaluation finalize --deployment-sha '$EXPECTED_SHA' &&
     MASTERMIND_FORWARD_EVALUATION_RELEASE_STATE_ROOT='$LIVE_DATA_PATH' \
       python3 -m portfolio.forward_evaluation status >/dev/null" \
    >>"$LOG" 2>&1; then
    log "forward evaluation authority bytes changed, missing, unreadable, or lock verification failed"
    fail_release "forward evaluation activation/status verification failed"
  fi
  log "deploy OK: $SVC healthy at commit $EXPECTED_SHA"
  exit 0
fi

fail_release "health check returned $CODE"
