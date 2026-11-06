#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/engine-render.yml
# Original rendered-site publisher; DATA checkout remains independent.
set -e
if [ "${GITHUB_REPOSITORY:-}" = mastermindx-market-intelligence/macro ]; then
  # Capture repository-owned execution bytes from the original protected
  # workflow SHA BEFORE rebase can replace files in the candidate tree.
  umask 077
  [[ "$GITHUB_WORKFLOW_SHA" =~ ^[0-9a-f]{40}$ ]]
  native_code_root="${RUNNER_TEMP%/}/native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}"
  mkdir -m 700 -- "$native_code_root"
  mkdir -p -- "$native_code_root/scripts/ci"
  GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show \
    "$GITHUB_WORKFLOW_SHA:scripts/ci/native_publication_source.sh" \
    > "$native_code_root/scripts/ci/native_publication_source.sh"
  case "$(GIT_NO_REPLACE_OBJECTS=1 git ls-tree "$GITHUB_WORKFLOW_SHA" -- scripts/ci/native_publication_source.sh)" in
    100644*) : ;; *) exit 76 ;;
  esac
  . "$native_code_root/scripts/ci/native_publication_source.sh"
  native_publication_capture_source "$native_code_root" "$GITHUB_WORKFLOW_SHA"
  . "$native_code_root/scripts/ci/push_retry.sh"
else
  . "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
fi
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
# ONLY site/ — never data/ or reports/. engine.run + the builders touch data/ in the
# working tree (regime recompute, ledger appends, cache writes); committing NONE of it
# keeps the nightly the single advancer of every forward-accountability ledger.
# pre-commit template↔site re-sync (ui.template_site_sync): inject_data_base +
# externalize_css above rewrite the site/ copies of the ~48 templates/-paired
# plain-copy assets, so this FIRST commit always carried the divergence and only
# the post-rebase --fix inside the push loop below healed it, one follow-up commit
# later. Any cancellation/failure between the two ships the divergence: 2026-07-24
# run 30057066815 was cancelled mid-push-loop and landed b6386adb4af (externalized
# site/index.html + site/chat.html, no heal commit) — main's sync gate went red on
# every PR until #3358. Heal BEFORE staging so the first commit is never diverged;
# the post-rebase --fix below STAYS (it re-copies from fresh post-rebase templates/,
# guarding the -X theirs mid-render-merge reword case, 2026-07-07 incident).
python -m scripts.check_template_site_sync --fix || true
python3 scripts/check_conflict_markers.py --file site/start.html
# start runtimes single-instance (ui.start_runtime_single_instance): a stale-
# checkout render re-emits doubled live tags with ZERO markers (adad513bdfe),
# so the marker gate above can't see it — heal from HEAD (the last committed
# page, at most one render old) rather than forfeit the whole render.
python3 scripts/check_start_runtime.py --heal-from HEAD
# templates/ too, and ONLY for the plain-copy HTML pairs (index.html, chat.html):
# optimize_assets re-stamps their templates/ side because the --fix above rewrites
# their site copy FROM templates/ — a stamp staged site-only is reverted before it
# reaches main (#3617's fix never reached one returning browser), and staging site/
# alone would land the pair diverged and red the publish gate. Nothing else in the
# build path writes templates/. See render.yml.
# refuse stash/rebase wreckage (2026-08-01 d29e4dd44d: a conflicted
# autostash apply was staged wholesale — 1,704 pages shipped markers)
bash "${GITHUB_WORKSPACE:-.}/scripts/ci/strip_conflict_markers.sh"
git add site/
# separate + tolerant: `git add site/ templates/` exits 128 when a pathspec
# matches nothing, and this step runs under `-eo pipefail` — a missing
# templates/ would abort the commit and lose the whole render rather than
# just the stamp. Staging site/ keeps its hard-fail semantics.
git add templates/ 2>/dev/null || true
git add -f site/stockbrief 2>/dev/null || true
if git diff --cached --quiet; then echo "no rendered-site changes to commit"; exit 0; fi
# Fail-closed conflict gate (P0 2026-08-01, d29e4dd44d / #4167): refuse to
# commit staged `Updated upstream / Stashed changes` blocks or unmerged
# index entries — a conflicted autostash apply is the known source.
push_staged_heal site/ templates/ || exit 1
# The sync/runtime/marker heals above can replace pages after the standalone
# finalized-tree step. Validate the exact healed tree represented by the index.
python3 scripts/check_site_asset_refs.py site
python -m scripts.check_government_revenue_projection
python scripts/inject_shared_shell.py --check --site-dir site || exit 1
git commit -m "engine-render: regime recompute + re-render $(date -u +%F) (scope=${{ github.event.inputs.scope || 'all' }})"
# --autostash: we commit site/ ONLY, leaving the render's throwaway data/ writes
# unstaged; a plain `pull --rebase` refuses on a dirty tree and silently failed
# EVERY push. Autostash parks them, rebases, restores. This push is the only path
# to the live site (VPS serves committed main; no Pages-artifact fallback).
PUSH_BUDGET_SECS=600     # this push is the ONLY path to the live site — worth 10 min of waiting for the ref
PUSH_MAX_ATTEMPTS=20   # let the 600s DEADLINE stop this loop, not the attempt count: 10 contention
                       # retries burn only ~2 min, so the raised budget above would never bind
push_retry_init "engine-rendered site"
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
while push_attempt; do
  # Fetch the named tracking ref explicitly. checkout fetch configuration can
  # otherwise leave origin/main stale; the accepted pin must be the rebase base.
  # The shared helper quarantines only collisions tracked by that exact target.
  if ! push_fetch_main_for_rebase; then
    push_abort_rebase
    push_backoff
    continue
  fi
  COMMODITY_ACCEPTED=$(git rev-parse 'origin/main^{commit}') || exit 1
  # rename/rename on content-hashed site/assets/css/* is deterministic across
  # retries (path conflict; -X theirs can't settle it — 2026-07-22 asia-close
  # run 29904079071 dropped a day's outputs this way). The autoresolver keeps
  # both sides' hashed files (next externalize_css prunes the orphan) and
  # finishes the rebase; anything else is left for the abort+retry below.
  if { git rebase --autostash -X theirs "$COMMODITY_ACCEPTED" || bash scripts/rebase_autoresolve_hashed_css.sh; } && push_autostash_ok; then
    # Preserve the accepted research workspace before asset normalization.
    python -m scripts.check_commodity_publication --heal-from "$COMMODITY_ACCEPTED" || exit 1
    # Prove the rebased render commit itself before any optional heal. If a
    # later follow-up commit is skipped, this is the exact HEAD we still push.
    python3 scripts/check_site_asset_refs.py site
    # Refresh from the post-rebase evidence generation so a long-running
    # express render cannot overwrite a newer SAM projection with its
    # checkout-time embedded bundle.
    python -m scripts.build_government_revenue --site-only
    if ! git diff --quiet -- \
      data/government_revenue/latest.json \
      data/government_revenue/workspace.json \
      data/government_revenue/dossiers.json \
      data/government_revenue/subaward_dossiers.json \
      data/government_revenue/idv_dossiers.json \
      data/government_revenue/budget_program_graph.json; then
      echo "::error title=government-revenue projection drift::post-rebase canonical and rebuilt procurement bundles differ"
      exit 1
    fi
    # post-rebase template↔site re-sync (ui.template_site_sync). -X theirs can
    # resurrect this run's checkout-time template copies over a reword that merged
    # MID-RENDER: 2026-07-07 incident — run 28835838497 (110 min, checkout
    # 9208ef4920) pushed 2ae709f9f0, whose site/sector_cycles.js was byte-identical
    # to the CHECKOUT-TIME template blob, reverting #1793's de-escalation merged
    # 20 min earlier. templates/ is now fresh post-rebase main — re-copy the
    # plain-copy page assets from it and fold any delta into a follow-up commit.
    # re-shim + re-externalize POST-rebase (P0 2026-08-04, 9a997e9da3f): the rebase
    # can inherit RAW pages from main (a cancelled nightly's always() commit shipped
    # 5,895 un-normalized pages; THIS lane's run 30873888298 then merged its small
    # deltas cleanly INTO those fat pages — no conflict, -X theirs never engaged —
    # and its re-stamp-only heal pushed the poison onward as f0deeabde39). With the
    # full chain here that same push would have healed the whole tree instead.
    python -m scripts.inject_data_base || echo "data-base shim inject skipped (additive)"
    python -m scripts.externalize_css || echo "::warning::post-rebase css externalize FAILED — inherited raw pages stay un-externalized (9a997e9da3f)"
    # re-stamp POST-rebase (ui.asset_stamp): the tree this loop PUSHES is not the tree
    # the normalizer step stamped — pages a sibling lane lands mid-render arrive here
    # un-stamped and unseen by that pass (2026-07-26 render 6260e5ac8c0 shipped
    # site/us_track_record.html with a bare `theme.css` this way). Idempotent, ~11s over
    # 3.2k pages, and BEFORE the --fix so the pairs heal from a re-stamped templates/.
    python -m scripts.optimize_assets || echo "::warning::post-rebase asset optimize FAILED — ?v= stamps may be stale"
    python -m scripts.check_template_site_sync --fix || true
    # ms-board coherence guard (ui.ms_board_coherence): -X theirs resolves whole
    # conflict REGIONS toward this run's replayed render, so racing another
    # mid-render lane can stitch a hybrid Market State board — 2026-07-07 commit
    # 5bf116a3b3 (render.yml racing THIS lane's 7a1c30ced4) baked upstream's
    # score 56/"Mixed" beside the replayed run's stale "Risk Radar forces
    # Risk-off." note. Restore any incoherent page WHOLESALE from post-rebase
    # origin/main (coherent, at most one render old).
    python3 scripts/check_ms_board_coherence.py --heal-from origin/main \
      || echo "::warning::ms-board coherence heal incomplete (incoherent board may predate this run)"
    # refuse stash/rebase wreckage (2026-08-01 d29e4dd44d: a conflicted
    # autostash apply was staged wholesale — 1,704 pages shipped markers)
    bash "${GITHUB_WORKSPACE:-.}/scripts/ci/strip_conflict_markers.sh"
    python3 scripts/check_conflict_markers.py --file site/start.html
    python3 scripts/check_start_runtime.py --heal-from origin/main
    # A rebase can combine this run's stale page with main's newer deletion of
    # its content-addressed asset (2026-08-01 crypto.html -> 94a4f2e3.css).
    # Recheck the actual post-rebase tree before creating a heal commit or push.
    python3 scripts/check_site_asset_refs.py site
    python -m scripts.check_government_revenue_projection
    python scripts/inject_shared_shell.py --check --site-dir site || exit 1
    if ! git diff --quiet -- site/ templates/; then
      # push_staged_clean: never bake conflict markers into the follow-up
      # commit (P0 d29e4dd44d/#4167). On a dirty scan: unstage and push the
      # guarded render commit alone — same forfeit as a failed render-sync.
      git add site/
      git add templates/ 2>/dev/null || true
      if push_staged_clean site/ templates/; then
        git commit -m "render-sync: post-rebase guards (re-stamp + template re-copy + ms-board coherence)" \
          || echo "::warning::render-sync commit failed (non-fatal — pages publish gate backstops divergence)"
      else
        git reset -q -- site/ templates/ || true
        # restore offenders' worktree bytes too (word-split safe:
        # no tracked path contains whitespace)
        for f in $PUSH_STAGED_OFFENDERS; do git checkout HEAD -- "$f" 2>/dev/null || true; done
        echo "::warning title=render-sync skipped::post-rebase site/templates scanned dirty (conflict markers) — follow-up commit skipped; pushing the guarded render commit only"
      fi
    fi
    if ! git diff --quiet HEAD -- \
      site/government_revenue.html \
      site/government-revenue-data/latest.json \
      site/government-revenue-data/workspace.json \
      site/government-revenue-data/dossiers.json \
      site/government-revenue-data/subaward-dossiers.json \
      site/government-revenue-data/idv-dossiers.json \
      site/government-revenue-data/budget-program.json; then
      echo "::error title=government-revenue projection uncommitted::refusing to push a HEAD older than the validated procurement projection"
      exit 1
    fi
    python -m scripts.check_government_revenue_projection
    # Verify the committed bytes, even when an optional render-sync commit failed.
    python -m scripts.check_commodity_publication --accepted-ref "$COMMODITY_ACCEPTED" --candidate-ref HEAD || exit 1
    # A skipped or failed optional heal commit must not leave the checker
    # proving working-tree pages while an older HEAD is pushed.
    if ! git diff --quiet HEAD -- site/ templates/; then
      echo "::error title=shared-shell publication uncommitted::refusing to push a HEAD older than the validated site/templates tree"
      exit 1
    fi
    python scripts/inject_shared_shell.py --check --site-dir site || exit 1
    if push_do; then echo "pushed engine-rendered site on attempt $PUSH_ATTEMPT"; push_won; exit 0; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::error title=engine-rendered site NOT pushed::$PUSH_ATTEMPT rebase/push attempts failed ($PUSH_STOP) — this push is the ONLY path to the live site (VPS serves committed main; no Pages-artifact fallback), so live pages stay stale until the next render lane re-lands. Check the per-attempt [class] tags above: repeated [contention] means main is simply busier than this budget, repeated [rebase-conflict] means a NEW deterministic conflict class — see scripts/rebase_autoresolve_hashed_css.sh."
echo "### ❌ engine-rendered site NOT pushed after $PUSH_ATTEMPT attempts — live site stale until the next render/nightly re-lands" >> "$GITHUB_STEP_SUMMARY"
