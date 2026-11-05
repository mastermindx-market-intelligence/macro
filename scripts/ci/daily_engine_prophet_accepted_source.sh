#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# engine original prophet_accepted_source; size headroom, business body unchanged.
set -e
set -euo pipefail
EVENT_REF="${GITHUB_REF:-}"
SOURCE_BRANCH="$(git symbolic-ref --short -q HEAD || true)"
if [ "$EVENT_REF" != "refs/heads/main" ] \
  || [ "$SOURCE_BRANCH" != "main" ]; then
  echo "::warning title=Prophet downstream source withheld::off-main event/checkout cannot advance Prophet-derived ledgers"
  exit 0
fi
git fetch origin +refs/heads/main:refs/remotes/origin/main
ACCEPTED_PROPHET_SHA="$(git rev-parse origin/main)"
git checkout "$ACCEPTED_PROPHET_SHA" -- \
  site/prophet \
  data/prophet \
  data/prophet_arena \
  data/prophet_stage_shadow
# checkout does not remove generated additions absent from the accepted
# tree. Plans/states/arena are closed builder-owned roots, so remove
# only those additions; data/prophet correction ledgers are never
# cleaned and were restored from accepted main above.
git clean -fd -- \
  site/prophet \
  data/prophet/origination_receipts \
  data/prophet/origination_sources \
  data/prophet_arena \
  data/prophet_stage_shadow
RESTORE_MISMATCH=false
if ! git diff --cached --quiet "$ACCEPTED_PROPHET_SHA" -- \
    site/prophet data/prophet data/prophet_arena data/prophet_stage_shadow \
  || ! git diff --quiet -- \
    site/prophet data/prophet data/prophet_arena data/prophet_stage_shadow \
  || [ -n "$(git ls-files --others --exclude-standard -- data/prophet)" ]; then
  RESTORE_MISMATCH=true
fi
# Keep accepted bytes in the worktree for downstream readers, but do
# not leave them staged against this job's older checkout-time HEAD.
# This reset must follow verification: a checkpoint can legitimately
# add plans/receipts/Arena ledgers that do not exist in HEAD, and an
# earlier reset makes those accepted paths look deleted/untracked.
git reset -q -- \
  site/prophet \
  data/prophet \
  data/prophet_arena \
  data/prophet_stage_shadow
if [ "$RESTORE_MISMATCH" = "true" ]; then
  echo "::error title=Prophet downstream source mismatch::engine worktree could not be made byte-equivalent to accepted main; derived ledgers withheld"
  exit 1
fi
echo "ready=true" >> "$GITHUB_OUTPUT"
echo "accepted_sha=$ACCEPTED_PROPHET_SHA" >> "$GITHUB_OUTPUT"
