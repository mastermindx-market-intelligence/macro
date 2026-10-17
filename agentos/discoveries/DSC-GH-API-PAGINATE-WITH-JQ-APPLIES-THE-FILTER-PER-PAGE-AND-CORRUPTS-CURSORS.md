---
key: GH-API-PAGINATE-WITH-JQ-APPLIES-THE-FILTER-PER-PAGE-AND-CORRUPTS-CURSORS
claim: >
  `gh api --paginate --jq '<filter>'` applies the jq filter SEPARATELY to each fetched page rather
  than once to the concatenated result. An aggregate filter therefore emits one value PER PAGE, so
  `gh api --paginate --jq '[.[].created_at] | max'` on a multi-page comment list prints N lines, not
  one. Captured with `VAR=$(...)`, the shell variable becomes a multi-line string whose FIRST line
  is the oldest page's maximum. Any polling watcher that uses that value as its "since" cursor then
  compares against an early timestamp and silently re-admits days of already-consumed history.
  `gh api --paginate --slurp` collects all pages into a single JSON array of pages, so
  `gh api --paginate --slurp <path> | jq -r '[.[][].created_at] | max'` yields exactly one value.
falsifier: >
  Any of these refutes it: `gh api --paginate --jq '[.[].created_at] | max'` on a resource with more
  than one page printing exactly one line; the `--slurp` form printing more than one line for the
  same resource; or a watcher built on the `--paginate --jq` aggregate form holding a monotonically
  advancing cursor across a page boundary.
so_what: >
  The failure is silent, delayed and looks like a different bug: the watcher runs correctly for
  hours, then after the comment list crosses a page boundary it re-emits a block of old events, so
  the operator concludes the cursor "reset", blames GitHub's `since=` semantics, or kills a healthy
  watcher. Two independent defects commonly ride together in these watchers — the second being an
  author-exclusion filter that happens to name the operator's OWN posting login, which silently
  hides genuine peer comments written from that same account. Cursor state must be derived from a
  single-value aggregate (`--slurp`, or the emitted rows themselves), advanced only when the new
  value validates as a timestamp AND is strictly greater than the current one, and self-echo must
  be suppressed by COMMENT ID, never by author.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Fable delivery principal, 2026-09-25 01:53Z-01:56Z, while repairing the Mastermind #600 carrier
  watcher. Measured first-hand on `repos/mastermindx-market-intelligence/Mastermind/issues/600/comments`
  (4 pages): the `--paginate --jq '[.[].created_at] | max'` form printed 4 lines beginning
  `2026-09-20T01:28:01Z`, and `2026-09-20` is exactly the date from which the stale watcher had
  resumed re-emitting consumed comments; the `--paginate --slurp` form piped to one jq printed the
  single correct value `2026-09-25T01:52:14Z`. The stopped watcher's recorded command confirmed the
  aggregate-capture pattern, and `gh api .../issues/comments/5825377687 --jq .user.login` confirmed
  its excluded author `chriswong6031-creator` was the operator's own posting identity — the same
  login under which a Chairman comment (`5824751617`) had arrived and been hidden.
scope:
  - Mastermind
  - gh CLI
  - carrier watcher cursors
confidence: verified
---

# `gh api --paginate --jq` filters per page and silently corrupts polling cursors

An aggregate jq filter under `--paginate` emits one value per page, so a captured "max timestamp"
cursor becomes multi-line and reads as the OLDEST page's maximum. Use `--paginate --slurp` piped to a
single jq, advance the cursor only on a validated strictly-greater value, and suppress self-echo by
comment ID rather than by author login.
