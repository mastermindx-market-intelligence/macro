#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/government-revenue-live.yml
# Original source guards/proof/rebuild loop; native seals before its first effect.
set -euo pipefail
export GOVREV_NATIVE_SOURCE_STEP=native_publication_stage
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
. "$native_code_root/scripts/ci/push_retry.sh"
native_publication_verify_govrev_guards "$native_code_root" "$GITHUB_WORKFLOW_SHA"
. "$RUNNER_TEMP/govrev-reviewed-source-guards.sh"
PUSH_LABEL="government-revenue evidence"
if ! push_on_main_ok; then exit 0; fi
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
award_event_bundle_paths=(
  data/government_revenue/award_event_snapshots.parquet
  data/government_revenue/award_action_versions.parquet
  data/government_revenue/award_event_projection_state.json
)
award_event_receipt_path=data/government_revenue/collection_receipts.jsonl
subaward_bundle_paths=(
  data/government_revenue/subaward_snapshots.parquet
  data/government_revenue/subaward_collection_receipts.jsonl
  data/government_revenue/subaward_projection_state.json
  data/government_revenue/subaward_ingest_status.json
)
subaward_heartbeat_path=data/government_revenue/subaward_collector_heartbeat.parquet
idv_bundle_paths=(
  data/government_revenue/idv_relationship_snapshots.parquet
  data/government_revenue/idv_collection_receipts.jsonl
  data/government_revenue/idv_projection_state.json
  data/government_revenue/idv_ingest_status.json
)
idv_heartbeat_path=data/government_revenue/idv_collector_heartbeat.parquet
dod_budget_bundle_paths=(
  data/government_revenue/dod_budget_line_snapshots.jsonl
  data/government_revenue/dod_budget_collection_receipts.jsonl
  data/government_revenue/dod_budget_projection_state.json
)
fq() { PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.check_fms_bundle "$1"; }

assert_award_event_source_clean() {
  if ! git diff --quiet -- "${award_event_bundle_paths[@]}" "$award_event_receipt_path"; then
    echo "::error title=award-event source mutation::the SAM fast path cannot publish a locally changed USAspending award-event source bundle"
    return 1
  fi
  if ! git diff --cached --quiet -- "${award_event_bundle_paths[@]}" "$award_event_receipt_path"; then
    echo "::error title=award-event source staged::the SAM fast path cannot stage a USAspending award-event source mutation"
    return 1
  fi
}

assert_subaward_source_clean() {
  if ! git diff --quiet -- "${subaward_bundle_paths[@]}" "$subaward_heartbeat_path"; then
    echo "::error title=subaward source mutation::the SAM fast path cannot publish a locally changed USAspending subaward source bundle"
    return 1
  fi
  if ! git diff --cached --quiet -- "${subaward_bundle_paths[@]}" "$subaward_heartbeat_path"; then
    echo "::error title=subaward source staged::the SAM fast path cannot stage a USAspending subaward source mutation"
    return 1
  fi
}

assert_idv_source_clean() {
  if ! git diff --quiet -- "${idv_bundle_paths[@]}" "$idv_heartbeat_path"; then
    echo "::error title=idv source mutation::the SAM fast path cannot publish a locally changed USAspending IDV source bundle"
    return 1
  fi
  if ! git diff --cached --quiet -- "${idv_bundle_paths[@]}" "$idv_heartbeat_path"; then
    echo "::error title=idv source staged::the SAM fast path cannot stage a USAspending IDV source mutation"
    return 1
  fi
}

assert_dod_budget_source_clean() {
  if ! git diff --quiet -- "${dod_budget_bundle_paths[@]}"; then
    echo "::error title=dod-budget source mutation::the SAM fast path cannot publish a locally changed DoD budget source bundle"
    return 1
  fi
  if ! git diff --cached --quiet -- "${dod_budget_bundle_paths[@]}"; then
    echo "::error title=dod-budget source staged::the SAM fast path cannot stage a DoD budget source mutation"
    return 1
  fi
}

assert_idv_dossier_twins() {
  local canonical=data/government_revenue/idv_dossiers.json
  local public=site/government-revenue-data/idv-dossiers.json
  if [ ! -f "$canonical" ] || [ ! -f "$public" ]; then
    echo "::error title=idv dossier twin missing::the build must publish both canonical and public IDV dossier bytes"
    return 1
  fi
  if ! cmp -s "$canonical" "$public"; then
    echo "::error title=idv dossier twin mismatch::canonical and public IDV dossier bytes differ"
    return 1
  fi
}

assert_candidate_twins() {
  local canonical=data/government_revenue/candidate_queue.json
  local public=site/government-revenue-data/candidates.json
  if [ ! -f "$canonical" ] || [ ! -f "$public" ]; then
    echo "::error title=candidate queue twin missing::the live build must publish both canonical and public candidate queue bytes"
    return 1
  fi
  if ! cmp -s "$canonical" "$public"; then
    echo "::error title=candidate queue twin mismatch::canonical and public candidate queue bytes differ"
    return 1
  fi
}

assert_optional_budget_graph_twins() {
  local canonical=data/government_revenue/budget_program_graph.json
  local public=site/government-revenue-data/budget-program.json
  if [ ! -e "$canonical" ] && [ ! -e "$public" ]; then
    return 0
  fi
  if [ ! -f "$canonical" ] || [ ! -f "$public" ]; then
    echo "::error title=budget graph twin incomplete::DoD budget graph must be absent or present as exact canonical/public twins"
    return 1
  fi
  if ! cmp -s "$canonical" "$public"; then
    echo "::error title=budget graph twin mismatch::canonical and public DoD budget graph bytes differ"
    return 1
  fi
}

assert_award_event_bundle
assert_award_event_source_clean
assert_subaward_bundle
assert_subaward_source_clean
assert_idv_bundle
assert_idv_source_clean
assert_dod_budget_bundle
assert_dod_budget_source_clean
fq p
assert_recipient_graph_source_clean
assert_historical_suppression_source_clean
assert_issuance_correction_source_clean
assert_reviewed_controls_unchanged
assert_idv_dossier_twins
assert_candidate_twins
assert_optional_budget_graph_twins
fq t

stage_candidates=(
  data/government_revenue/opportunities.parquet
  data/government_revenue/opportunity_revisions.parquet
  data/government_revenue/opportunity_documents.parquet
  data/government_revenue/opportunity_ingest_status.json
  data/government_revenue/sam_opportunity_heartbeat.parquet
  data/government_revenue/latest.json
  data/government_revenue/workspace.json
  data/government_revenue/dossiers.json
  data/government_revenue/subaward_dossiers.json
  data/government_revenue/idv_dossiers.json
  data/government_revenue/sbir_progression.json
  data/government_revenue/identity_atlas.json
  data/government_revenue/program_dossier.json
  data/government_revenue/budget_program_graph.json
  data/government_revenue/fms_case_graph.json
  data/government_revenue/recipient_resolution_coverage.json
  data/government_revenue/candidate_ledger.jsonl
  data/government_revenue/candidate_queue.json
  data/government_revenue/candidate_projection_state.json
  data/government_revenue/candidate_projection_status.json
  site/government-revenue-data/latest.json
  site/government-revenue-data/workspace.json
  site/government-revenue-data/dossiers.json
  site/government-revenue-data/subaward-dossiers.json
  site/government-revenue-data/idv-dossiers.json
  site/government-revenue-data/sbir-progression.json
  site/government-revenue-data/identity-atlas.json
  site/government-revenue-data/program-dossier.json
  site/government-revenue-data/budget-program.json
  site/government-revenue-data/fms-cases.json
  site/government-revenue-data/candidates.json
  data/government_revenue/defense_economics.json
  data/government_revenue/program_theme_context.json
  data/government_revenue/program_theme_public_disclosure.json
  site/government-revenue-data/program-theme-context.json
  site/government-revenue-data/theme-context.json
  data/government_revenue/candidate_research_state.json
  site/government-revenue-data/defense-economics.json
  site/government-revenue-data/research-state.json
  site/government-revenue-investor.js
  site/government-revenue-investor-start.js
  site/government-revenue-page.js
  site/government-revenue-critical-theme.css
  site/theme.js
  site/government-revenue-investor.css
  site/government-revenue-theme-context.js
  site/government-revenue-theme-context.css
  site/government-revenue-sbir.js
  site/government-revenue-sbir.css
  site/government-revenue-briefcase.js
  site/government-revenue-briefcase-ui.js
  site/government-revenue-parity.css
  site/government-revenue-dossiers.js
  site/government-revenue-candidate-radar.js
  site/government_revenue.html
)
if [ "$AWARD_EVENT_BUNDLE_PRESENT" = true ]; then
  stage_candidates+=("${award_event_bundle_paths[@]}")
fi
stage_paths=()
for path in "${stage_candidates[@]}"; do
  if [ -e "$path" ] || git ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
    stage_paths+=("$path")
  fi
done
git add -- "${stage_paths[@]}"
if git diff --cached --quiet; then
  echo "no material Government Revenue artifacts to publish"
  exit 0
fi
# Seal outputs.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof verify \
  --root . --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json"
push_staged_clean \
  data/government_revenue/opportunities.parquet \
  data/government_revenue/opportunity_revisions.parquet \
  data/government_revenue/opportunity_documents.parquet \
  data/government_revenue/opportunity_ingest_status.json \
  data/government_revenue/sam_opportunity_heartbeat.parquet \
  data/government_revenue/award_event_snapshots.parquet \
  data/government_revenue/award_action_versions.parquet \
  data/government_revenue/award_event_projection_state.json \
  data/government_revenue/latest.json \
  data/government_revenue/workspace.json \
  data/government_revenue/dossiers.json \
  data/government_revenue/subaward_dossiers.json \
  data/government_revenue/idv_dossiers.json \
  data/government_revenue/sbir_progression.json \
  data/government_revenue/identity_atlas.json \
  data/government_revenue/program_dossier.json \
  data/government_revenue/budget_program_graph.json \
  data/government_revenue/fms_case_graph.json \
  data/government_revenue/recipient_resolution_coverage.json \
  data/government_revenue/candidate_ledger.jsonl \
  data/government_revenue/candidate_queue.json \
  data/government_revenue/candidate_projection_state.json \
  data/government_revenue/candidate_projection_status.json \
  site/government-revenue-data/latest.json \
  site/government-revenue-data/workspace.json \
  site/government-revenue-data/dossiers.json \
  site/government-revenue-data/subaward-dossiers.json \
  site/government-revenue-data/idv-dossiers.json \
  site/government-revenue-data/sbir-progression.json \
  site/government-revenue-data/identity-atlas.json \
  site/government-revenue-data/program-dossier.json \
  site/government-revenue-data/budget-program.json \
  site/government-revenue-data/fms-cases.json \
  site/government-revenue-data/candidates.json \
  data/government_revenue/defense_economics.json \
  data/government_revenue/program_theme_context.json \
  data/government_revenue/program_theme_public_disclosure.json \
  site/government-revenue-data/program-theme-context.json \
  site/government-revenue-data/theme-context.json \
  data/government_revenue/candidate_research_state.json \
  site/government-revenue-data/defense-economics.json \
  site/government-revenue-data/research-state.json \
  site/government-revenue-investor.js \
  site/government-revenue-investor-start.js \
  site/government-revenue-page.js \
  site/government-revenue-critical-theme.css \
  site/theme.js \
  site/government-revenue-investor.css \
  site/government-revenue-theme-context.js \
  site/government-revenue-theme-context.css \
  site/government-revenue-sbir.js \
  site/government-revenue-sbir.css \
  site/government-revenue-briefcase.js \
  site/government-revenue-briefcase-ui.js \
  site/government-revenue-parity.css \
  site/government-revenue-dossiers.js \
  site/government-revenue-candidate-radar.js \
  site/government_revenue.html
git commit -m "govrev: SAM opportunity evidence $(date -u +%FT%H:%MZ)"

GOVREV_REPROOFS=0
PUSH_MAX_ATTEMPTS=2
PUSH_BUDGET_SECS=2700
PUSH_ALARM=90
push_retry_init "government-revenue evidence"
# Seal the ORIGINAL generation before the first native publication effect.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof verify --committed --root . --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json"
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  77)
    # One existing GovRev identity binds this already-confirmed original intent;
    # it does not mint admission or declare its publication successful.
    GOVREV_PUSH_IDENTITY="$RUNNER_TEMP/govrev-candidate-proof.push-native.identity.json"
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof push-identity --root . --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json" \
      --attempt native --out "$GOVREV_PUSH_IDENTITY"
    printf 'govrev_push_identity=%s\n' "$GOVREV_PUSH_IDENTITY" >> "$GITHUB_OUTPUT"
    echo "publication=pending" >> "$GITHUB_OUTPUT"
    exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
while push_attempt; do
  git fetch origin main || true
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  # Recheck freshness.
  # Refuse proven withholding.
  if ! push_append_only_fence origin/main --amend; then push_backoff; continue; fi
  if git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    # Rebuild after rebase.
    assert_award_event_bundle
    assert_award_event_source_clean
    assert_subaward_bundle
    assert_subaward_source_clean
    assert_idv_bundle
    assert_idv_source_clean
    assert_dod_budget_bundle
    assert_dod_budget_source_clean
    fq p
    assert_recipient_graph_source_clean
    assert_historical_suppression_source_clean
    assert_issuance_correction_source_clean
    assert_reviewed_controls_unchanged
    restore_financial_owner_snapshot
    restore_market_owner_snapshot
    python -m scripts.build_government_revenue --live-materialization
    prepare_candidate_research_state
    assert_recipient_graph_source_clean
    assert_historical_suppression_source_clean
    assert_issuance_correction_source_clean
    assert_reviewed_controls_unchanged
    assert_idv_dossier_twins
    assert_candidate_twins
    assert_optional_budget_graph_twins
    fq t
    git add \
      data/government_revenue/latest.json \
      data/government_revenue/workspace.json \
      data/government_revenue/dossiers.json \
      data/government_revenue/subaward_dossiers.json \
      data/government_revenue/idv_dossiers.json \
      data/government_revenue/sbir_progression.json \
      data/government_revenue/identity_atlas.json \
      data/government_revenue/program_dossier.json \
      data/government_revenue/recipient_resolution_coverage.json \
      data/government_revenue/candidate_ledger.jsonl \
      data/government_revenue/candidate_queue.json \
      data/government_revenue/candidate_projection_state.json \
      data/government_revenue/candidate_projection_status.json \
      site/government-revenue-data/latest.json \
      site/government-revenue-data/workspace.json \
      site/government-revenue-data/dossiers.json \
      site/government-revenue-data/subaward-dossiers.json \
      site/government-revenue-data/idv-dossiers.json \
      site/government-revenue-data/sbir-progression.json \
      site/government-revenue-data/identity-atlas.json \
      site/government-revenue-data/program-dossier.json \
      site/government-revenue-data/candidates.json \
      data/government_revenue/defense_economics.json \
      data/government_revenue/program_theme_context.json \
      data/government_revenue/program_theme_public_disclosure.json \
      site/government-revenue-data/program-theme-context.json \
      site/government-revenue-data/theme-context.json \
      data/government_revenue/candidate_research_state.json \
      site/government-revenue-data/defense-economics.json \
      site/government-revenue-data/research-state.json \
      site/government-revenue-investor.js \
      site/government-revenue-investor-start.js \
      site/government-revenue-page.js \
      site/government-revenue-critical-theme.css \
      site/theme.js \
      site/government-revenue-investor.css \
      site/government-revenue-theme-context.js \
      site/government-revenue-theme-context.css \
      site/government-revenue-sbir.js \
      site/government-revenue-sbir.css \
      site/government-revenue-briefcase.js \
      site/government-revenue-briefcase-ui.js \
      site/government-revenue-parity.css \
      site/government-revenue-dossiers.js \
      site/government-revenue-candidate-radar.js \
      site/government_revenue.html
    if [ -f data/government_revenue/budget_program_graph.json ]; then
      git add -- \
        data/government_revenue/budget_program_graph.json \
        site/government-revenue-data/budget-program.json
    fi
    if ! PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof verify \
      --root . --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json"; then
      if [ "$GOVREV_REPROOFS" -ge 1 ]; then
        echo "::error::changed generation exceeds the bounded reproof budget; refusing publication"
        exit 1
      fi
      GOVREV_REPROOFS=$((GOVREV_REPROOFS + 1))
      PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof prove \
        --root . --install-missing \
        --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json" \
        --log "$RUNNER_TEMP/govrev-candidate-proof.log"
    fi
    fq s
    push_staged_clean \
      data/government_revenue/award_event_snapshots.parquet \
      data/government_revenue/award_action_versions.parquet \
      data/government_revenue/award_event_projection_state.json \
      data/government_revenue/latest.json \
      data/government_revenue/workspace.json \
      data/government_revenue/dossiers.json \
      data/government_revenue/subaward_dossiers.json \
      data/government_revenue/idv_dossiers.json \
      data/government_revenue/sbir_progression.json \
      data/government_revenue/identity_atlas.json \
      data/government_revenue/program_dossier.json \
      data/government_revenue/budget_program_graph.json \
      data/government_revenue/fms_case_graph.json \
      data/government_revenue/recipient_resolution_coverage.json \
      data/government_revenue/candidate_ledger.jsonl \
      data/government_revenue/candidate_queue.json \
      data/government_revenue/candidate_projection_state.json \
      data/government_revenue/candidate_projection_status.json \
      site/government-revenue-data/latest.json \
      site/government-revenue-data/workspace.json \
      site/government-revenue-data/dossiers.json \
      site/government-revenue-data/subaward-dossiers.json \
      site/government-revenue-data/idv-dossiers.json \
      site/government-revenue-data/sbir-progression.json \
      site/government-revenue-data/identity-atlas.json \
      site/government-revenue-data/program-dossier.json \
      site/government-revenue-data/budget-program.json \
      site/government-revenue-data/fms-cases.json \
      site/government-revenue-data/candidates.json \
      data/government_revenue/defense_economics.json \
      data/government_revenue/program_theme_context.json \
      data/government_revenue/program_theme_public_disclosure.json \
      site/government-revenue-data/program-theme-context.json \
      site/government-revenue-data/theme-context.json \
      data/government_revenue/candidate_research_state.json \
      site/government-revenue-data/defense-economics.json \
      site/government-revenue-data/research-state.json \
      site/government-revenue-investor.js \
      site/government-revenue-investor-start.js \
      site/government-revenue-page.js \
      site/government-revenue-critical-theme.css \
      site/theme.js \
      site/government-revenue-investor.css \
      site/government-revenue-theme-context.js \
      site/government-revenue-theme-context.css \
      site/government-revenue-sbir.js \
      site/government-revenue-sbir.css \
      site/government-revenue-briefcase.js \
      site/government-revenue-briefcase-ui.js \
      site/government-revenue-parity.css \
      site/government-revenue-dossiers.js \
      site/government-revenue-candidate-radar.js \
      site/government_revenue.html
    if ! git diff --cached --quiet; then
      git commit --amend --no-edit
    fi
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof verify --committed \
      --root . --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json"
    govrev_push_rc=0
    govrev_push_same_carrier || govrev_push_rc=$?
    if [ "$govrev_push_rc" -eq 0 ]; then
      PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$native_code_root" python3 -P -m scripts.ci.govrev_candidate_proof publication-witness \
        --root . --receipt "$RUNNER_TEMP/govrev-candidate-proof.receipt.json" \
        --commit "$(git rev-parse HEAD)" --push-status "$GOVREV_PUSH_STATUS" \
        --push-observation "$GOVREV_PUSH_OBSERVATION" \
        --push-identity "$GOVREV_PUSH_IDENTITY" \
        --out "$RUNNER_TEMP/govrev-candidate-proof.publication.json"
      echo "pushed Government Revenue evidence on attempt ${PUSH_ATTEMPT}"
      push_won
      exit 0
    elif [ "$govrev_push_rc" -ne 1 ]; then
      echo "::error title=government-revenue-live::original push refused or effect unknown; same-carrier reconciliation required before any new publication"
      exit "$govrev_push_rc"
    fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::warning title=government-revenue-live::could not publish complete evidence after ${PUSH_ATTEMPT} attempts; prior live projection remains authoritative"
exit 0
