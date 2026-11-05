---
key: A-PRS-PACK-INDEX-DIFFERS-FROM-MAINS
claim: "run_ci_pack.py rebalances packs per diff, so the same logical job can sit in a different ci-pack-N on a PR than on main's proof (#8288: market-os-macro-suite-pages ran in ci-pack-4 on the PR, ci-pack-10 on main) \u2014 name-matched inherited-red rules in the sweeper and in watchers miss it."
falsifier: "`python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-count 12 --validate-only` placing market-os-macro-suite-pages in the same ci-pack-N for a PR diff and for main across several PRs with different diffs."
so_what: "Attribute an inherited red by LOGICAL job + failing test + tuple (read the job log), never by pack name; a watcher that tolerates only 'ci-pack-10' is blind; hand-merge on concluded checks with --match-head-commit when the red is provably main's."
kind: constraint
verified_at: 2026-10-02
verified_by: "#8288 checks 18:5xZ: all packs green except ci-pack-4 = market-os-macro-suite-pages -> test_zh_l_zh_spans_are_translated -> ('macro_national_debt_liabilities.html','Recession'), the identical tuple red on main's 37043074910 in ci-pack-10"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "scripts/run_ci_pack.py"
  - "scripts/merge_on_green.py"
confidence: verified
---

Pack indices are an artefact of balancing, not identity. The sweeper's base-inherited-red refresh matches job NAMES, so a rebalanced pack hides an inherited red from it; the seat must attribute by content.
