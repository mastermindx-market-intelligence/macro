#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/asia-close.yml
# Original asia/commit engine outputs business body; staged native route preserves original budget.
set -e
export NATIVE_PUBLICATION_PUBLISHING_STEP=native_publication_engine_stage
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
publisher_source_root="${native_code_root:-${GITHUB_WORKSPACE:-.}}"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
# normalize the EXACT tree this always() commit stages (P0 2026-08-04,
# 9a997e9da3f — daily.yml's identical always() shape): a timeout-cancel
# skips every success()-gated step including the shim/externalize step
# above (this job's ONLY normalize pass) while this step still commits,
# shipping raw CN/HK pages sitewide. Normalize here so the staged tree is
# normalized by construction; all three passes are idempotent (~35s no-op
# when the step above already ran them).
python -m scripts.inject_data_base || echo "data-base shim inject skipped (additive)"
python -m scripts.externalize_css || echo "::warning::pre-commit css externalize FAILED — pages may ship un-externalized (9a997e9da3f)"
python -m scripts.optimize_assets || echo "::warning::asset optimize FAILED — ?v= stamps may be stale"
# pre-commit template↔site re-sync (ui.template_site_sync): the shim/externalize
# step above rewrites the site/ copies of the ~48 templates/-paired plain-copy
# assets, and only the post-rebase --fix in the push loop heals the divergence —
# a cancellation/failure between this commit and that heal ships it (engine-render
# 2026-07-24: run 30057066815 cancelled mid-push-loop landed b6386adb4af, sync gate
# red on every PR until #3358; this lane's own instance was 2026-07-23 commit
# 4b356dd6b1a, pre-#3285). Heal BEFORE staging so the first commit is never
# diverged; the post-rebase --fix stays for the -X theirs mid-render-merge case.
python -m scripts.check_template_site_sync --fix || true
# templates/ too, and ONLY for the plain-copy HTML pairs (index.html, chat.html):
# optimize_assets re-stamps their templates/ side because the --fix above rewrites
# their site copy FROM templates/ — a stamp staged site-only is reverted before it
# reaches main (#3617's fix never reached one returning browser), and staging site/
# alone would land the pair diverged and red the publish gate. Nothing else in the
# build path writes templates/. See render.yml.
# A hard step timeout can interrupt the publisher between preparing a
# same-filesystem temp/rollback copy and its finally cleanup. Those
# private pair artifacts are never product output and are not ignored;
# remove only this publisher's closed filename family before broad
# `git add site/` can mistake one for a page or feed.
find site site/marketdata -maxdepth 1 -type f \
  \( -name '.china_heatmap.html.*.tmp' -o -name '.china_heatmap.html.*.bak' \
     -o -name '.china_heatmap.json.*.tmp' -o -name '.china_heatmap.json.*.bak' \) \
  -delete
# refuse stash/rebase wreckage (2026-08-01 d29e4dd44d: a conflicted
# autostash apply was staged wholesale — 1,704 pages shipped markers)
bash "$publisher_source_root/scripts/ci/strip_conflict_markers.sh"
# Asia must not acquire the Options PIT/campaign narrow roots owned by the
# dedicated narrow publishers; the helper restores/cleans them around the
# broad `git add` so the engine commit cannot smuggle an Options artifact
# onto the Asia lane.
NATIVE_PUBLICATION_CODE_ROOT="${native_code_root:-}" bash "$publisher_source_root/scripts/ci/options_signal_nightly.sh" exclude-broad
git add data/ site/
NATIVE_PUBLICATION_CODE_ROOT="${native_code_root:-}" bash "$publisher_source_root/scripts/ci/options_signal_nightly.sh" exclude-broad
# separate + tolerant: `git add site/ templates/` exits 128 when a pathspec
# matches nothing, and this step runs under `-eo pipefail` — a missing
# templates/ would abort the commit and lose the whole render rather than
# just the stamp. Staging site/ keeps its hard-fail semantics.
git add templates/ 2>/dev/null || true
# QLEDGER CARVE-OUT tail guard (#9556 port): the restore step above put the
# carved data/qledger + site/qledger bytes back in this worktree, and the
# broad add above just swept them into the index again. Un-stage them
# after the broad add (daily.yml's engine-commit idiom) so the oversized
# blob cannot ride THIS commit and die on GH001 all over again.
if [ "$QLEDGER_CARVED" = 'true' ]; then
  git reset -q -- data/qledger site/qledger 2>/dev/null || true
fi
# force-add the gitignored per-market search libraries + reconstructed candles
if git diff --cached --quiet; then echo "no engine output changes"; exit 0; fi
# Fail-closed conflict gate (P0 2026-08-01, d29e4dd44d / #4167): the broad
# `git add data/ site/` above stages a conflicted-autostash tree VERBATIM
# (the "commit collected asia data" push loop earlier in this job pulls
# while later-rendered paths are still dirty — the same shape that baked
# 1,707 marker pages into the US nightly). Refuse to commit one.
push_staged_heal data/ site/ templates/ || exit 1
# GITHUB_ENV normally supplies the identity minted by the first publish.
# Fall back once per commit/push step only when that earlier step never
# established it; the shell variable then remains fixed across all retries.
CHINA_HEATMAP_GENERATED_UTC="${CHINA_HEATMAP_GENERATED_UTC:-$(date -u '+%Y-%m-%d %H:%M')}"
git commit -m "engine: asia dashboards $(date -u +%F)"
PUSH_BUDGET_SECS=600   # sole nightly for CN/HK — an unpushed commit is a silently-dropped day (2026-07-22)
PUSH_MAX_ATTEMPTS=20   # let the 600s DEADLINE stop this loop, not the attempt count: 10 contention
                       # retries burn only ~2 min, so the raised budget above would never bind
push_retry_init "asia engine outputs"
native_candidate=""
NATIVE_PUBLICATION_CANDIDATE_UNQUALIFIED=1
if perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin +refs/heads/main:refs/remotes/origin/main; then
  native_parent=$(git merge-base HEAD origin/main) || native_parent=""
  if [ -n "$native_parent" ] && native_candidate=$(push_metadata_replay_commit "$native_parent" origin/main HEAD \
      "$(git log -1 --format=%B HEAD)" "${RUNNER_TEMP}/asia-engine-native-${NATIVE_PUBLICATION_PUBLISHING_STEP:-local}.idx"); then
    NATIVE_PUBLICATION_CANDIDATE_UNQUALIFIED=0
  fi
fi
export NATIVE_PUBLICATION_CANDIDATE_UNQUALIFIED
native_initial_rc=0
push_native_do origin "${native_candidate:-HEAD}:refs/heads/main" || native_initial_rc=$?
unset NATIVE_PUBLICATION_CANDIDATE_UNQUALIFIED
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
while push_attempt; do
  # pre-sync collision sweep (render.yml / #2252): a mid-run commit on origin/main can
  # TRACK a path this job wrote as an UNTRACKED side-effect — the rebase checkout then
  # refuses ("untracked working tree files would be overwritten") and --autostash can't
  # clear it (it parks tracked modifications only), so every retry dies identically.
  # Everything this step publishes is already committed above, so a path untracked HERE
  # but tracked on origin/main is a throwaway local write — origin/main is authoritative.
  # Gitignored files and untracked paths origin/main doesn't track never enter the
  # intersection (runner-local stores and caches are untouched).
  git fetch origin main || true
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  # rename/rename on content-hashed site/assets/css/* is DETERMINISTIC across
  # retries (-X theirs settles content conflicts, never path conflicts) — run
  # 29904079071 (2026-07-22) burned all 5 attempts on the same conflict and
  # dropped the whole day's outputs under a green run (hk_regime stuck 07-21).
  # The autoresolver keeps BOTH sides' hashed files byte-pure and completes
  # the rebase (the next externalize_css prunes the orphan); on any other
  # conflict it exits nonzero, leaving the rebase for the abort+retry below.
  if { git pull --rebase --autostash -X theirs origin main || bash scripts/rebase_autoresolve_hashed_css.sh; } && push_autostash_ok; then
    # Rebuild the heatmap pair against the exact post-rebase tree before
    # normalizing or pushing. A concurrent render may update only one of
    # the generated files; the run-stable identity minted before the first
    # publish keeps every retry byte-stable even when main carries an older
    # session. A failure blocks this push attempt rather than silently
    # publishing a split observation session.
    if ! python -m scripts.build_market_heatmap --market china --render-page \
        --generated-utc "$CHINA_HEATMAP_GENERATED_UTC" \
        > "$RUNNER_TEMP/china_heatmap_republish.log" 2>&1; then
      cat "$RUNNER_TEMP/china_heatmap_republish.log"
      echo "::error title=post-rebase China heatmap coherence repair failed::the JSON/SSR pair was not pushed"
      push_abort_rebase
      push_backoff
      continue
    fi
    cat "$RUNNER_TEMP/china_heatmap_republish.log"
    # post-rebase template↔site re-sync (ui.template_site_sync): externalize_css
    # above lifts the plain-copy landing/chat pages' inline <style> to hashed files,
    # diverging site/index.html + site/chat.html from their templates — and this lane
    # (unlike render.yml/engine-render.yml/daily.yml) had no --fix, so it shipped the
    # divergence and reddened the sync gate on main (2026-07-23, commit 4b356dd6b1a).
    # -X theirs can also resurrect checkout-time copies over a reword that merged
    # mid-render. templates/ is now fresh post-rebase main — re-copy the plain-copy
    # page assets; the render-heal commit below folds the delta.
    # re-shim + re-externalize POST-rebase (P0 2026-08-04, 9a997e9da3f): the rebase
    # can inherit RAW pages from main (a cancelled nightly's always() commit); a
    # re-stamp-only heal re-stamps the fat inline page and pushes the poison
    # onward. Full normalize chain here = the next lane push self-heals the tree.
    python -m scripts.inject_data_base || echo "data-base shim inject skipped (additive)"
    python -m scripts.externalize_css || echo "::warning::post-rebase css externalize FAILED — inherited raw pages stay un-externalized (9a997e9da3f)"
    # re-stamp POST-rebase (ui.asset_stamp): the tree this loop PUSHES is not the tree
    # the normalizer step stamped — pages a sibling lane lands mid-run arrive here
    # un-stamped and unseen by that pass (2026-07-26 render 6260e5ac8c0 shipped
    # site/us_track_record.html with a bare `theme.css` this way). Idempotent, ~11s over
    # 3.2k pages, and BEFORE the --fix so the pairs heal from a re-stamped templates/.
    python -m scripts.optimize_assets || echo "::warning::post-rebase asset optimize FAILED — ?v= stamps may be stale"
    python -m scripts.check_template_site_sync --fix || true
    # ms-board coherence guard (ui.ms_board_coherence): this lane re-renders the
    # CN/HK dashboards, so -X theirs racing another render can stitch a hybrid
    # Market State board (see the 2026-07-07 macro.html incident, commit
    # 5bf116a3b3). Restore any incoherent page WHOLESALE from post-rebase
    # origin/main and fold it into a follow-up commit.
    python3 scripts/check_ms_board_coherence.py --heal-from origin/main \
      || echo "::warning::ms-board coherence heal incomplete (incoherent board may predate this run)"
    # refuse stash/rebase wreckage (2026-08-01 d29e4dd44d: a conflicted
    # autostash apply was staged wholesale — 1,704 pages shipped markers)
    bash "$publisher_source_root/scripts/ci/strip_conflict_markers.sh"
    if ! git diff --quiet -- site/ templates/; then
      # push_staged_clean: never bake conflict markers into the follow-up
      # commit (P0 d29e4dd44d/#4167); on a dirty scan push the guarded
      # engine commit alone.
      git add site/
      git add templates/ 2>/dev/null || true
      if push_staged_clean site/ templates/; then
        git commit -m "render-heal: restore coherent ms-board post-rebase (ui.ms_board_coherence)" \
          || echo "::warning::render-heal commit failed (non-fatal)"
      else
        git reset -q -- site/ templates/ || true
        # restore offenders' worktree bytes too (word-split safe:
        # no tracked path contains whitespace)
        for f in $PUSH_STAGED_OFFENDERS; do git checkout HEAD -- "$f" 2>/dev/null || true; done
        echo "::warning title=render-heal skipped::post-rebase site/templates scanned dirty (conflict markers) — follow-up commit skipped"
      fi
    fi
    if push_do; then echo "pushed asia engine outputs (attempt $PUSH_ATTEMPT)"; push_won; exit 0; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
# This lane is the SOLE nightly for CN/HK: an unpushed engine commit exists only
# on this runner and is wiped by the next checkout — a silently-dropped day
# (the 2026-07-22 incident). Fail the job: the gate grants one same-day retry
# after a real failure, so going red is exactly what re-lands the data. R2
# publish + freshness verify below still run (if: always()).
echo "::error title=asia engine outputs NOT pushed::$PUSH_ATTEMPT rebase/push attempts failed ($PUSH_STOP) — the day's CN/HK engine outputs (data/ forward ledgers incl. hk_regime + rendered site/) exist only on this runner and are lost at the next checkout. Failing the job so the gate's same-day retry re-collects and re-lands them. Check the per-attempt [class] tags above: repeated [contention] means main is simply busier than this budget, repeated [rebase-conflict] means a NEW deterministic conflict class — see scripts/rebase_autoresolve_hashed_css.sh."
echo "### ❌ asia engine outputs NOT pushed after $PUSH_ATTEMPT attempts — failing loudly; the gate grants one same-day retry" >> "$GITHUB_STEP_SUMMARY"
exit 1
