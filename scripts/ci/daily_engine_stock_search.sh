#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# engine original rebuild stock-search libraries (resilient — guarantees the analyzers ship); size headroom, business body unchanged.
set -e
set +e
libdir() {
  case "$1" in
    scripts.build_china_library) echo site/chinastockdata;;
    scripts.build_hk_library) echo site/hkstockdata;;
    scripts.build_canada_library) echo site/canadastockdata;;
    scripts.build_intl_library) echo site/intlstockdata;;
  esac
}
for mod in scripts.build_canada_library scripts.build_intl_library; do
  idx="$(libdir "$mod")/index.json"
  # Skip a market whose dashboard step already built its library FRESH this run
  # (index.json newer than the job-start marker). This rebuild is a FAILURE-PATH
  # safety net — on the success path the same heavy analyze() over the whole
  # universe already ran, so rebuilding is pure duplicate work. A dashboard that
  # swallowed an error leaves an older (pulled) index.json => marker is newer =>
  # we still rebuild and the library ships.
  if [ -f "$RUNNER_TEMP/engine_libs_marker" ] && [ "$idx" -nt "$RUNNER_TEMP/engine_libs_marker" ]; then
    echo "::notice::$mod — already built fresh this run ($idx); skipping redundant rebuild"
    continue
  fi
  echo "::group::$mod"; python -m "$mod" > "$RUNNER_TEMP/lib.log" 2>&1; rc=$?; cat "$RUNNER_TEMP/lib.log"; echo "::endgroup::"
  if [ "$rc" -ne 0 ]; then
    echo "::error title=$mod failed (rc=$rc)::$(tail -n 2 "$RUNNER_TEMP/lib.log" | tr '\n' ' ' | tail -c 600)"
    { echo "### ❌ $mod failed (rc=$rc)"; echo '```'; tail -n 40 "$RUNNER_TEMP/lib.log"; echo '```'; } >> "$GITHUB_STEP_SUMMARY"
  fi
done
exit 0
