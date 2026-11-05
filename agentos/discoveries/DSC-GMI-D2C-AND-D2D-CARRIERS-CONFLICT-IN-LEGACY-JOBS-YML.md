---
key: GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML
claim: >
  The two Sol-held GMI carriers D2C (#8432, head 54d17ebcb1c1) and D2D (#8435, head
  7429a3e5f6da) each merge clean against origin/main 20eb503a09 but conflict with EACH OTHER in
  `.github/ci/legacy-jobs.yml` (one content conflict; merge-base 4294fd498e8c). Both add a
  theme-graph test step to the same CI block, so whichever lands second must rebase that block
  before its checks are meaningful.
falsifier: >
  `git merge-tree --write-tree 54d17ebcb1c11471fffbbdea6888f97db6c9fbbb
  7429a3e5f6da9b66787ead24119a238a2a36858d` exiting 0 with no CONFLICT line, or the three heads
  (main, #8432, #8435) composing clean in a scratch merge.
so_what: >
  D2E acceptance cannot be censused on main+#8432+#8435 as a single composition until one of
  them lands and the other rebases; the 2026-10-05 pre-census therefore covered main+#8432 only.
  The release order is Sol's; the second carrier owes a legacy-jobs.yml rebase and a fresh
  merge-ref CI run, and because a legacy pack is ONE check the resulting heal must stay in that
  carrier, never split into a side PR.
kind: landmine
verified_at: 2026-10-05
verified_by: >
  Seat command in a macro worktree: `git merge-tree --write-tree 54d17ebc… 7429a3e5…` ->
  tree 33cb5df820f3, `CONFLICT (content): Merge conflict in .github/ci/legacy-jobs.yml`;
  independently reproduced by the D2E pre-census lane (PR #8488, C0(b): scratch merge of #8435
  onto main+#8432 aborted on the same path).
scope:
  - macro
  - .github/ci/legacy-jobs.yml
  - engine/theme_graph/
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

Both carriers were cut from main before the other existed and each appends its own test job to
the legacy job list, which is why neither conflicts with main yet they conflict with each other.
