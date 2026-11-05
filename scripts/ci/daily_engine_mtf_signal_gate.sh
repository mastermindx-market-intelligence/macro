#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# engine original MTF buy-filter signals + §7 contract gate (build_signal_quality → validate_signals); size headroom, business body unchanged.
set -e
set +e
echo "::group::build + validate MTF signals"
python -m scripts.build_signal_quality > "$RUNNER_TEMP/sigq.log" 2>&1; bq=$?
cat "$RUNNER_TEMP/sigq.log"
if [ "$bq" -ne 0 ]; then
  echo "::error title=build_signal_quality failed (rc=$bq)::signal compute failed — leaf left at last-good"
fi
python -m scripts.validate_signals > "$RUNNER_TEMP/sigv.log" 2>&1; vrc=$?
cat "$RUNNER_TEMP/sigv.log"
echo "::endgroup::"
if [ "$vrc" -ne 0 ]; then
  # Discard the drifted/malformed write so neither the commit-to-main nor the Pages
  # artifact can ship it. Leaf AND per-ticker files are tracked on main (per-ticker
  # tracked since 2026-06-28 via the render lane) -> restore last-good committed
  # copies; git clean sweeps only untracked strays (e.g. a new ticker's first write).
  # NEVER `rm` the tracked per-ticker files here: the 226 staged deletions ride the
  # broad `git add site/` into the engine commit and modify/delete-conflict with the
  # intraday render lane's signal commits — the rebase-push then fails every retry
  # and the WHOLE nightly engine commit (regime update + forward ledgers) is dropped
  # (2026-07-12 incident: pick-lab ledgers lost).
  git checkout -- data/signal_archive/mtf_signals_latest.json 2>/dev/null || true
  git checkout -- site/signals/ 2>/dev/null || true
  git clean -fq -- site/signals/ 2>/dev/null || true
  echo "::error title=signal §7 contract gate FAILED::malformed/drifted signal write discarded (leaf + per-ticker files restored to last-good committed copies); see data/quality/signals_audit.json"
  { echo "### ❌ signal §7 contract gate failed — bad write discarded";
    echo '<details><summary>validator output</summary>'; echo; echo '```';
    tail -n 40 "$RUNNER_TEMP/sigv.log"; echo '```'; echo '</details>'; } >> "$GITHUB_STEP_SUMMARY"
fi
exit 0
