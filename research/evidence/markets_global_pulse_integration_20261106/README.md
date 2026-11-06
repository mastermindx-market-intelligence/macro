# Markets pulse current-main integration — November 6, 2026

PR #7594 retains original publication branch
sol/markets-global-regime-compact-20260921. This packet qualifies original head
b0b5bcc40f29584669577f1c4eca29a1036f5986 against accepted main
1d7068eb12b810c5aa9b0439468fdccaa5a512c6. The separate managed qualification
branch is not a publication branch.

## Source composition

A genuine merge found exactly two conflicts: site/markets_data.js and generated
site/markets.html. Seven other feature files composed normally. Only the
contaminated global curation asOf changes to null; evaluated JavaScript proves
every other global field, all five market phases and all eleven current market
objects unchanged. No new curation date was invented.

The existing Jinja renderer, make_optimizer, page writer and single-page CSS
externalizer reproduced accepted main byte for byte before rendering the candidate.
The second optimizer pass retains the canonical preload ordering. All current
US/HK/CN strip inputs and caveats remain. Current November 6 engine artifact
85cb00a77529e39746f8a757e31cdc78a748223b is unchanged. The page has 22 local
references to 20 distinct assets; every content-hash reference matches its final
bytes. The existing cycle.css?v=4 reference and its bytes remain exactly main's
legacy version contract. The page rebuild called no data producer or price refresh.

Two inherited feature test files had terminal blank lines flagged by git diff
--check; only those EOF blank lines were removed, with identical Python ASTs.

## Actual qualification

The existing two-module markets-regime-strip command ran 82 cases: 81 passed,
including the available Playwright browser cases, with zero skips. Its sole
failure was the sparse-omitted persisted US input. The existing worktree owner
then materialized the committed data tree; source and current engine bytes stayed
unchanged. Only the failed live-tree case was rechecked and passed against exact
committed US, HK and CN snapshots. All 82 distinct cases are therefore qualified
across the recorded phases; this is not represented as one 82-pass rerun.

US snapshot is November 5; Hong Kong and China snapshots are November 4. All three
are RISK_OFF. These input dates are retained, not described as live November 6
observations. Logs and exact snapshot blobs accompany the receipts. All feature
files remained unchanged during qualification and the feature diff passes its
whitespace check. Existing CI ownership, dependency declarations and budgets were
not changed.

## Remaining delivery boundary

Natural new-head hosted CI, source-hold disposition and the incumbent merge
controller remain required. This packet does not claim merge, deployment or the
served production Markets journey. Historical #7595/#7617 acceptance and
#9296/#9309 enrollment custody remain separate. Prior evidence stays in the
existing Git history.

The initial pytest log is stored as focused-qualification.log.gz. Decompression reproduces the original log byte for byte, including diagnostic whitespace; its decoded SHA-256 remains the hash in the qualification receipt.
