#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/government-revenue-live.yml
# Original reviewed controls and same-carrier publisher guards.
set -euo pipefail
export GOVREV_NATIVE_SOURCE_STEP=govrev_guard_stage
if [ "${GITHUB_REPOSITORY:-}" = mastermindx-market-intelligence/macro ]; then
  umask 077
  native_code_root="${RUNNER_TEMP%/}/native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}"
  native_bootstrap="${RUNNER_TEMP%/}/native-publication-bootstrap-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}-${GOVREV_NATIVE_SOURCE_STEP}.sh"
  case "$(GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git ls-tree "$GITHUB_WORKFLOW_SHA" -- scripts/ci/native_publication_source.sh)" in
    100644*) : ;; *) exit 76 ;;
  esac
  (set -o noclobber; GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show "$GITHUB_WORKFLOW_SHA:scripts/ci/native_publication_source.sh" > "$native_bootstrap")
  . "$native_bootstrap"
  native_publication_prepare_source "$native_code_root" "$GITHUB_WORKFLOW_SHA"
  . "$native_code_root/scripts/ci/push_retry.sh"
else
  native_code_root="${GITHUB_WORKSPACE:-.}"
fi
set -euo pipefail
cat > "$RUNNER_TEMP/govrev-reviewed-source-guards.sh" <<'SH'
recipient_graph_path=data/government_revenue/recipient_entity_graph.json
historical_suppression_path=config/government_revenue/candidate_historical_suppressions.v1.json
historical_suppression_schema_path=contracts/government_revenue/government_revenue_candidate_historical_suppressions.v1.schema.json
issuance_correction_path=config/government_revenue/candidate_issuance_corrections.v1.json
issuance_correction_schema_path=contracts/government_revenue/government_revenue_candidate_issuance_corrections.v1.schema.json
reviewed_controls_fingerprint_path="$RUNNER_TEMP/govrev-reviewed-controls.sha256"

reviewed_control_paths() {
  printf '%s\n' \
    "$historical_suppression_path" \
    "$historical_suppression_schema_path" \
    "$issuance_correction_path" \
    "$issuance_correction_schema_path" \
    config/government_revenue/program_theme_assignments.v1.json \
    config/government_revenue/reviews/nato_policy_20250625.json
}

write_reviewed_controls_fingerprint() {
  local output_path=$1
  local path
  : > "$output_path"
  while IFS= read -r path; do
    if [ ! -f "$path" ] || ! git ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
      echo "::error title=reviewed control missing::required reviewed control is not a tracked file: $path"
      return 1
    fi
    if ! git diff --quiet -- "$path" || ! git diff --cached --quiet -- "$path"; then
      echo "::error title=reviewed control mutation::reviewed control is dirty or staged: $path"
      return 1
    fi
    printf '%s  %s\n' "$(git hash-object -- "$path")" "$path" >> "$output_path"
  done < <(reviewed_control_paths)
}

snapshot_reviewed_controls() {
  local snapshot_tmp="${reviewed_controls_fingerprint_path}.tmp"
  write_reviewed_controls_fingerprint "$snapshot_tmp"
  mv -f -- "$snapshot_tmp" "$reviewed_controls_fingerprint_path"
}

assert_reviewed_controls_unchanged() {
  local current_tmp="${reviewed_controls_fingerprint_path}.check"
  if [ ! -f "$reviewed_controls_fingerprint_path" ]; then
    echo "::error title=reviewed control snapshot missing::publication cannot proceed without the initial reviewed-control fingerprint"
    return 1
  fi
  write_reviewed_controls_fingerprint "$current_tmp"
  if ! cmp -s "$reviewed_controls_fingerprint_path" "$current_tmp"; then
    echo "::error title=reviewed control changed::a reviewed manifest or schema changed after this workflow began; a fresh workflow must own the new head"
    diff -u "$reviewed_controls_fingerprint_path" "$current_tmp" || true
    rm -f -- "$current_tmp"
    return 1
  fi
  rm -f -- "$current_tmp"
}

assert_recipient_graph_source_clean() {
  # Recipient attribution is a separately reviewed exact-ID input.
  # Neither collectors nor builders may infer or stage it.
  if [ ! -f "$recipient_graph_path" ] || ! git ls-files --error-unmatch -- "$recipient_graph_path" >/dev/null 2>&1; then
    echo "::error title=recipient graph missing::the canonical reviewed recipient graph must be committed before publication"
    return 1
  fi
  if ! git diff --quiet -- "$recipient_graph_path" || ! git diff --cached --quiet -- "$recipient_graph_path"; then
    echo "::error title=recipient graph mutation::collectors and projection builders cannot write or stage the curated recipient graph"
    return 1
  fi
}

assert_historical_suppression_source_clean() {
  # This is an operator-reviewed exact non-issuance decision. The
  # builder validates and binds it, but must never author or stage it.
  if [ ! -f "$historical_suppression_path" ] || ! git ls-files --error-unmatch -- "$historical_suppression_path" >/dev/null 2>&1; then
    echo "::error title=historical suppression missing::the reviewed candidate suppression manifest must be committed before publication"
    return 1
  fi
  if ! git diff --quiet -- "$historical_suppression_path" || ! git diff --cached --quiet -- "$historical_suppression_path"; then
    echo "::error title=historical suppression mutation::collectors and projection builders cannot write or stage the reviewed suppression manifest"
    return 1
  fi
}

assert_issuance_correction_source_clean() {
  # This is an operator-reviewed exact correction to an append-only
  # issuance incident. Builders may validate it, but must never
  # author, weaken, or stage it.
  if [ ! -f "$issuance_correction_path" ] || ! git ls-files --error-unmatch -- "$issuance_correction_path" >/dev/null 2>&1; then
    echo "::error title=issuance correction missing::the reviewed candidate issuance correction must be committed before publication"
    return 1
  fi
  if ! git diff --quiet -- "$issuance_correction_path" || ! git diff --cached --quiet -- "$issuance_correction_path"; then
    echo "::error title=issuance correction mutation::collectors and projection builders cannot write or stage the reviewed issuance correction"
    return 1
  fi
}
assert_subaward_bundle() {
  local present=0 tracked=0 path
  for path in "${subaward_bundle_paths[@]}"; do
    [ -f "$path" ] && present=$((present + 1))
    git ls-files --error-unmatch -- "$path" >/dev/null 2>&1 && tracked=$((tracked + 1))
  done
  if [ "$present" -eq 0 ]; then
    if [ "$tracked" -ne 0 ]; then
      echo "::error title=subaward bundle missing::tracked receipt-bound subaward artifacts disappeared from the checkout; refusing a partial projection"
      return 1
    fi
    # Empty-first is an explicit public state until the daily collector
    # establishes its first complete receipt-bound generation.
    SUBAWARD_BUNDLE_PRESENT=false
    echo "receipt-bound subaward bundle not initialized yet; publishing an unavailable zero-row dossier"
    return 0
  fi
  if [ "$present" -ne "${#subaward_bundle_paths[@]}" ] || [ "$tracked" -ne "${#subaward_bundle_paths[@]}" ]; then
    echo "::error title=subaward bundle incomplete::subaward snapshots, receipts, activation state, and ingest status must arrive as one committed bundle"
    return 1
  fi
  python - \
    data/government_revenue/subaward_projection_state.json \
    data/government_revenue/subaward_snapshots.parquet <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from collectors.usaspending_subawards import subaward_projection_generation_matches

try:
    state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    snapshots = pd.read_parquet(Path(sys.argv[2]))
except Exception as exc:
    raise SystemExit("subaward source generation could not be read") from exc
if not isinstance(state, dict) or not subaward_projection_generation_matches(state, snapshots):
    raise SystemExit("subaward source snapshot does not match its activation generation")
PY
  SUBAWARD_BUNDLE_PRESENT=true
}

assert_idv_bundle() {
  local present=0 tracked=0 path
  for path in "${idv_bundle_paths[@]}"; do
    [ -f "$path" ] && present=$((present + 1))
    git ls-files --error-unmatch -- "$path" >/dev/null 2>&1 && tracked=$((tracked + 1))
  done
  if [ "$present" -eq 0 ]; then
    if [ "$tracked" -ne 0 ]; then
      echo "::error title=idv bundle missing::tracked receipt-bound IDV artifacts disappeared from the checkout; refusing a partial projection"
      return 1
    fi
    echo "receipt-bound IDV bundle not initialized yet; publishing an unavailable relationship dossier"
    return 0
  fi
  if [ "$present" -ne "${#idv_bundle_paths[@]}" ] || [ "$tracked" -ne "${#idv_bundle_paths[@]}" ]; then
    echo "::error title=idv bundle incomplete::IDV snapshots, receipts, activation state, and ingest status must arrive as one committed bundle"
    return 1
  fi
  python - \
    data/government_revenue/idv_projection_state.json \
    data/government_revenue/idv_relationship_snapshots.parquet <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from collectors.usaspending_idv_graph import idv_projection_generation_matches

try:
    state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    snapshots = pd.read_parquet(Path(sys.argv[2]))
except Exception as exc:
    raise SystemExit("IDV source generation could not be read") from exc
if not isinstance(state, dict) or not idv_projection_generation_matches(state, snapshots):
    raise SystemExit("IDV source snapshot does not match its activation generation")
PY
}

assert_award_event_bundle() {
  local present=0 tracked=0 path
  for path in "${award_event_bundle_paths[@]}"; do
    [ -f "$path" ] && present=$((present + 1))
    git ls-files --error-unmatch -- "$path" >/dev/null 2>&1 && tracked=$((tracked + 1))
  done
  if [ "$present" -eq 0 ]; then
    if [ "$tracked" -ne 0 ]; then
      echo "::error title=award-event bundle missing::tracked receipt-bound award artifacts disappeared from the checkout; refusing a partial projection"
      return 1
    fi
    # Initial deployment before the collector establishes its first baseline.
    AWARD_EVENT_BUNDLE_PRESENT=false
    echo "receipt-bound award-event bundle not initialized yet; keeping forward events unavailable"
    return 0
  fi
  if [ "$present" -ne "${#award_event_bundle_paths[@]}" ] || [ "$tracked" -ne "${#award_event_bundle_paths[@]}" ]; then
    echo "::error title=award-event bundle incomplete::receipt-bound award artifacts must arrive as one committed bundle; refusing a partial projection"
    return 1
  fi
  if [ ! -f "$award_event_receipt_path" ] || ! git ls-files --error-unmatch -- "$award_event_receipt_path" >/dev/null 2>&1; then
    echo "::error title=award-event receipts missing::a receipt-bound award bundle requires the committed canonical receipt ledger"
    return 1
  fi
  # Positional contract is STATE SNAPSHOTS ACTIONS — NOT the bundle
  # array order (snapshots, actions, state): passing the array fed the
  # snapshots parquet to json.loads and killed the lane with
  # "activation state is unreadable" (first surfaced 2026-08-08, the
  # first run ever to reach this step). Wiring pinned by
  # tests/test_government_revenue_award_validator_wiring.py.
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.validate_government_revenue_award_event_bundle \
    data/government_revenue/award_event_projection_state.json \
    data/government_revenue/award_event_snapshots.parquet \
    data/government_revenue/award_action_versions.parquet
  AWARD_EVENT_BUNDLE_PRESENT=true
}

assert_dod_budget_bundle() {
  local present=0 tracked=0 path
  for path in "${dod_budget_bundle_paths[@]}"; do
    [ -f "$path" ] && present=$((present + 1))
    git ls-files --error-unmatch -- "$path" >/dev/null 2>&1 && tracked=$((tracked + 1))
  done
  if [ "$present" -eq 0 ]; then
    if [ "$tracked" -ne 0 ]; then
      echo "::error title=dod-budget bundle missing::tracked DoD budget source artifacts disappeared from the checkout; refusing a partial graph"
      return 1
    fi
    echo "DoD budget source bundle not initialized yet; keeping the optional graph unavailable"
    return 0
  fi
  if [ "$present" -ne "${#dod_budget_bundle_paths[@]}" ] || [ "$tracked" -ne "${#dod_budget_bundle_paths[@]}" ]; then
    echo "::error title=dod-budget bundle incomplete::DoD budget lines, receipts, and projection state must arrive as one committed bundle"
    return 1
  fi
  python - "${dod_budget_bundle_paths[@]}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

from collectors.dod_budget import projection_state_matches

try:
    lines = [json.loads(row) for row in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()]
    receipts = [json.loads(row) for row in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()]
    state = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit("DoD budget source generation could not be read") from exc
if not lines or not receipts or not isinstance(state, dict) or not projection_state_matches(state, lines, receipts):
    raise SystemExit("DoD budget source ledgers do not match their projection generation")
PY
}

restore_market_owner_snapshot() {
  python -m scripts.restore_defense_market_owner --root .
}

restore_financial_owner_snapshot() {
  python -m scripts.restore_event_workspace_owner --root . \
    --require-ticker LMT --require-ticker RTX --require-ticker NOC \
    --require-ticker LHX --require-ticker GD \
    --receipt "$RUNNER_TEMP/govrev-financial-owner-receipt.json"
}

govrev_push_same_carrier() {
  push_on_main_ok || return 76
  local rc=0 outcome_rc=0
  local prefix="$RUNNER_TEMP/govrev-candidate-proof.push-${PUSH_ATTEMPT}"
  GOVREV_PUSH_OBSERVATION="$prefix.observation.json"
  GOVREV_PUSH_IDENTITY="$prefix.identity.json"
  GOVREV_PUSH_STATUS=successful
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof push-identity \
    --root . --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json" \
    --attempt "$PUSH_ATTEMPT" --out "$prefix.identity.json" || return 75
  local raw_response
  raw_response="$(umask 077; mktemp "$RUNNER_TEMP/govrev-private-push-response.XXXXXX")" || return 75
  push_do origin HEAD:main > "$raw_response" 2>&1 || rc=$?
  local outcome_arg=""
  if [ "${PUSH_TERMINAL_RC:-0}" -ne 0 ]; then outcome_arg=--terminal-refusal; fi
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof push-outcome --root . \
    --exit-code "$rc" --log "$raw_response" --out "$prefix.outcome.json" ${outcome_arg:+--terminal-refusal} || outcome_rc=$?
  rm -f -- "$raw_response"
  case "$outcome_rc" in
    0) return 0 ;;
    1) return 1 ;;
    76) return 76 ;;
  esac
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof observe-push --root . \
    --identity "$prefix.identity.json" --out "$GOVREV_PUSH_OBSERVATION"; then
    GOVREV_PUSH_STATUS=successful_after_same_carrier_observation
    return 0
  fi
  return 75
}

prepare_candidate_research_state() {
  local generated_at
  generated_at="$(python -c 'import json; print(json.load(open("data/government_revenue/candidate_projection_state.json"))["generated_at"])')"
  python -m scripts.build_government_revenue_research_state --root . --generated-at "$generated_at"
}

SH
chmod 400 "$RUNNER_TEMP/govrev-reviewed-source-guards.sh"
native_publication_verify_govrev_guards "$native_code_root" "$GITHUB_WORKFLOW_SHA"
. "$RUNNER_TEMP/govrev-reviewed-source-guards.sh"
snapshot_reviewed_controls
