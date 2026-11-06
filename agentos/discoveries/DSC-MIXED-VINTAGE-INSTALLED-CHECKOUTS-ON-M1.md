---
key: MIXED-VINTAGE-INSTALLED-CHECKOUTS-ON-M1
claim: >
  As of 2026-09-29, the m1studio production checkouts that back launchd producers are
  NOT clean at any single commit — they are mixed vintage, file by file. Measured on
  `/Users/chriswong/flow-ops-wt` (working dir of `com.macro.optionsmatrix`):
  `engine/options_matrix.py` was byte-identical to `origin/main`
  (sha256 11146402f340c559...2883a, 48456 B), while `lib/nyse_calendar.py` in the same
  tree was 10291 B / 229 lines against main's 29814 B and was missing the last ten
  functions main defines, and `scripts/build_options_matrix.py` carried a +35 B local
  divergence (sha256 a00934e1b2a6424c...5bdd at 10436 B) matching no committed revision.
  The 2026-09-16 ADVANCED-DATA-OPTIONS handoff independently found the same shape on the
  sibling `/Users/chriswong/liveflow-ops-wt` (HEAD 2026-08-20, pre-#6585), so this is a
  recurring property of these hosts and not a one-off.
falsifier: >
  A builtin-only probe (see [[FORK-STARVED-HOST-NEEDS-BUILTIN-ONLY-SSH-PROBE]]) comparing
  byte lengths and sha256 of the installed files against `git show origin/main:<path>`
  locally. If every installed file matches one commit, the tree has been made clean and
  this no longer holds.
so_what: >
  Never install a repair onto these hosts as a file-level copy of only the files the PR
  changed, and never derive a rollback preimage from the assumption that the tree sits at
  some known commit. A change whose new code imports a symbol at module top level can fail
  closed at import — not degrade — because the installed sibling module predates that
  symbol. Measured exactly that on 2026-09-29: macro #7861's repair imports
  `sessions_apart` from `lib.nyse_calendar` at `engine/options_matrix.py:56`, and the
  installed calendar module had zero occurrences of it, so copying the two changed files
  would have stopped the producer entirely. Before any install: probe the installed bytes,
  hash them, check every module the change imports from, and reconcile any local divergence
  with its owner first — a preimage that matches no committed revision cannot be trusted
  for rollback. Installation remains an owner act, outside the producer's active window.
kind: landmine
verified_at: 2026-09-29
verified_by: "builtin-only ssh probe + shasum on m1; macro PR #7861 comment 5895153520; agentos/handoffs/ADVANCED-DATA-OPTIONS-2026-09-16-integration-amendment-packet-delivery.md"
scope:
  - macro
  - ops/launchd/**
  - engine/options_matrix.py
  - scripts/build_options_matrix.py
  - hosts/m1studio
confidence: verified
---

# Installed producer checkouts are mixed vintage, file by file

The dangerous inference is the reasonable one: "the producer file matches main, so the tree
is at main." It was not. In the same directory one module sat exactly at `origin/main`,
another was many revisions behind, and a third carried uncommitted local edits.

That combination defeats both halves of a normal release. It defeats *installation*, because
the minimal install — copy the files the PR touched — can leave a new top-level import
pointing at a module that predates the symbol, which is an `ImportError` at import time
rather than a degraded run. And it defeats *rollback*, because the preimage you would restore
matches no revision anyone can name.

Related: [[FORK-STARVED-HOST-NEEDS-BUILTIN-ONLY-SSH-PROBE]] — how to measure it at all.
