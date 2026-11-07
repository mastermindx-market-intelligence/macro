# Portfolio brief snapshot producer — run evidence

Run: `portfolio-brief-snapshot-producer-20261102-c2-001` (worker leaf, no
descendants). Date: 2026-11-02.

This records what was actually run, what was actually observed, and what is
still open. It does not claim parent acceptance, independent review, merge,
deployment or production proof — none of those happened here.

## Source identity

| | |
|---|---|
| Repository | `mastermindx-market-intelligence/macro` |
| Branch | `sol/web-portfolio-brief-snapshot-20261102` |
| App base (PR base commit) | `f125051fdb37cad7758a18833b76223146fed9d4` |
| Pickup plan head (branch head at pickup) | `6fd89c4fa10eaef68469ff1043eacf7527cfaba1` |
| Remote branch head at pickup | `6fd89c4fa10eaef68469ff1043eacf7527cfaba1` (matches) |
| Implementation commit | `7bdf40c6c4650f73b5f833a29bd6da576a6ae797` |
| Implementation tree | `5bd737a725732598dd7f7746097e48c048d9e5e3` |
| PR | #10551 — OPEN, DRAFT, `mergeable: MERGEABLE`, base `main` |

The PR was left DRAFT and unarmed. Nothing was merged, deployed, Ready-ed,
labelled, armed or released. The existing `merge-on-green` / hold labels were
not touched.

## Procedure and role loading

Protected Mastermind was loaded at the pinned commit
`ae3fc6fce8f704b32b01664f1b0d1c0d52a1c8ed`, `docs/sol_skills/INDEX.md`
`skillpack_version: 1.0.1`, `minimum_bootstrap_major: 1` — the atomic-load
law was honoured: every procedure below came from that SAME commit SHA.

Loaded and applied:

- `docs/sol_skills/INDEX.md` (1.0.1) — skill selection, canonical source
  ownership, hard laws 15/16/17 (economical routing, tool-first capability
  discovery, no notification-only watcher).
- `docs/sol_skills/BOOTSTRAP_KERNEL.md` (bootstrap_major 1) — boot/source law,
  forward execution, finalization vocabulary.
- `docs/sol_skills/ACTIVE_EXECUTION.md` — the active-turn owner and the
  finalization gate.
- `docs/sol_skills/REVIEW_RETURN.md` — review against the original outcome
  (the parent's job, not this worker's).
- `skills/mastermind-worker-bootstrap/SKILL.md` + `references/*` — the Fabric
  WORKER role: bounded task, one method, scoped edits, return the actual
  artifact/revision/tests/limits/next action, never claim parent consumption.
- `docs/EXECUTIVE_WORKER_ROUTING_CHAIRMAN_ADDENDUM.md` and
  `docs/AGENT_DIALOGUE_SESSION_CLOSE_LAW.md` are the universal companions for
  a delegation/return; this run's `WHY NOT FABLE` basis is recorded below.

Repository instructions read before authoring: `CLAUDE.md` (macro) and
`AGENTS.md` (macro), plus the STANDING guides they link (workspace
completion, model routing, spawn-handoff, Agent OS, house laws) as they
applied to this run.

### Role and routing

- Role: **worker leaf** under Sol (WS:MARKET-OS), no descendants, no child
  spawned, no watcher armed, no dialogue opened.
- Task class: `C2_COMPLEX_BOUND` / `fix_build` — a consequential single-domain
  data contract with explicit design and moderate bounded risk.
- Route: the admitted paid AUTO route (economical admitted paid route, per
  the assignment). `WHY NOT FABLE`: this is a bounded implementation of an
  already-adjudicated endpoint/witness contract with concrete falsifiers;
  the parent Sol retains semantic adjudication and independent review, and
  Fable (the scarce principal pool) would add an operator layer without
  changing what is proved. No extra operator layer was used.
- `FRONTIER_WITNESS`: NONE.

## Source custody

Harness-owned isolated custody — never the shared primary checkout:

```
/home/ubuntu0/lanes/wt/pbs-20261102-c2-001   (git worktree, sparse, lane script
                                              ~/lanes/bin/mk_macro.sh)
```

The lane lease `portfolio-brief-snapshot-producer-20261102-c2-001` was live
under `/home/ubuntu0/lanes/ext/active/` for the whole run (pid 735507). No
other writer touched this branch during the run; the remote head was re-read
immediately before the push and matched.

## Collision census (fresh, before authoring)

Open PRs seen: **905** (paged over GitHub GraphQL, 46 pages of 20).

Open PRs touching the owned or frozen paths: **26**. The three named foreign
writers were re-read live and confirmed still open, still draft, with the
stated heads:

| PR | head | touches |
|---|---|---|
| #8687 | `4df6828f4c5b9aa94088f8439c805e0ee7542a30` | `app/main.py`, `engine/neuralweb/brain_gateway.py`, `engine/portfolio_brief.py` |
| #7658 | `4005b0c24080d377315957b93248d135c001c22b` | `app/main.py`, `engine/neuralweb/brain_gateway.py` |
| #10203 | `1bac98552de0740e056747be1c6bc9c29696dfe3` | `engine/portfolio_brief.py`, `engine/portfolio_changes.py` |

**No foreign hunk was taken, imported or rewritten.** The change is purely
ADDITIVE beside the frozen functions:

- `engine/neuralweb/brain_gateway.py`: `+100` lines, `-0`. `_sb_get` is
  byte-identical (asserted by a test). The new code is three new functions
  below `_sb_get`: `_parse_content_range`, `_redact_owner`,
  `_sb_get_count_aware`.
- `app/main.py`: the brief endpoint gained a bound-mode branch; the legacy
  loader, cache key, cache lookup, cache write and response are untouched.
  The only legacy-path edit is the extraction of the ctx read into
  `_portfolio_load_ctx` — the same five lines, the same 503 and the same
  detail, now shared by both modes.

Frozen and untouched, byte-for-byte: `_sb_get`, `_portfolio_load_holdings`,
`_holdings_fingerprint`, `_tool_get_portfolio_brief`, `engine/portfolio_brief.py`,
`engine/portfolio_changes.py`, the changes endpoint, all auth/entitlement,
and all Terminal source.

## Changed paths

| path | change |
|---|---|
| `app/main.py` | brief endpoint: opt-in header + bound-mode branch + narrow import wiring |
| `app/portfolio_brief_context.py` | NEW — capture, completeness proof, projection gate, witness |
| `engine/neuralweb/brain_gateway.py` | ADDITIVE — count-aware private read beside `_sb_get` |
| `tests/test_portfolio_brief_context.py` | NEW — 245 tests |
| `tests/fixtures/portfolio_brief_context/projection_cases.json` | NEW — 64 shared adversarial cases |
| `tests/fixtures/portfolio_brief_context/README.md` | NEW — fixture contract for consumer reuse |
| `docs/verification/portfolio-brief-snapshot-20261102/WIRE_SCHEMA.md` | NEW — the exact wire fields |
| `docs/verification/portfolio-brief-snapshot-20261102/EVIDENCE.md` | NEW — this file |

No other path was modified. No dependency, schema, DDL, migration, store,
grant, provider CLI or SSH path was touched.

### Digests (sha256 of the file at the implementation commit)

```
ddd3b89c2a683e1d1bdec7eae7827ca23dec56c42db80add3b1224c3eab92b81  app/main.py
2f430f8bb6b9db5701eaf62fcce140084032a809b66efd86c03d28fdbf083af5  app/portfolio_brief_context.py
457cf1286e14a901e6a48e2e8a5726d15bc06a326ace2793167a3e245e60e9b1  engine/neuralweb/brain_gateway.py
916c9cc6af888dc951cde0c31cb23a5ce1cba076ac623a9c0215c5aa3d580daa  tests/test_portfolio_brief_context.py
0dc420ae46edb02c83ce8f2dc0a82b36a4a7198a2d173bc0801537f3812d784e  tests/fixtures/portfolio_brief_context/projection_cases.json
5a536ffee55a52f1070e7ba56016b08c2f38586281f694564e5d5ec0e354e4f4  tests/fixtures/portfolio_brief_context/README.md
ee0199774e0ff7e6e0ee11ee5d823493e9f19d1a4d2cd93438140b71d44b26f7  docs/verification/portfolio-brief-snapshot-20261102/WIRE_SCHEMA.md
```

## Baseline falsifiers (captured BEFORE the implementation was judged)

The base tree `6fd89c4fa10eaef68469ff1043eacf7527cfaba1` was materialised as a
second isolated worktree and probed with the SAME probe script used against
the implementation.

**At the base (6fd89c4f):**

```json
{
  "count_aware_helper": false,
  "endpoint_opted_has_context": false,
  "endpoint_opted_same_as_ordinary": true,
  "endpoint_opted_status": 200,
  "producer_module": false,
  "producer_module_error": "ModuleNotFoundError: No module named 'app.portfolio_brief_context'"
}
```

That is the falsifier: **at the base the opt-in header has NO effect at all** —
the opted-in response was byte-identical to the ordinary response and carried
no witness. A client asking for a witness would have silently received an
unwitnessed brief.

The new test suite also does not even COLLECT at the base
(`ImportError: cannot import name 'portfolio_brief_context' from 'app'`),
which is the absence proof for the module itself.

**At the implementation (7bdf40c6):**

```json
{
  "count_aware_helper": true,
  "endpoint_opted_detail": {"error": "portfolio_snapshot_unavailable",
                            "reason": "store_not_configured"},
  "endpoint_opted_has_context": false,
  "endpoint_opted_same_as_ordinary": false,
  "endpoint_opted_status": 503,
  "has_capture": true,
  "producer_module": true,
  "witness_schema": "portfolio_snapshot_witness.v1"
}
```

The header is no longer ignored, and a capture that cannot be proved fails
CLOSED (503 with a reason) instead of answering 200 without a witness. The
probe runs with no Supabase configured, so 503/`store_not_configured` is the
correct outcome there; the witnessed 200 path is covered by the 245-test suite
against a synthetic reader.

## Commands actually run (exit codes and counts)

All commands were run from the isolated worktree. `--basetemp` is used
because this sandbox's pytest temp-dir cleanup raises a pre-existing
`RecursionError` at session finish — it reproduces identically on the
untouched base tree and on `tests/test_portfolio_brief.py` alone (see
"Environmental noise" below), so it is not caused by this change.

| # | command | exit | result |
|---|---|---|---|
| 1 | `python3 -m pytest tests/test_portfolio_brief_context.py -q` | 0 | **245 passed**, 101 warnings, 2.64s |
| 2 | `python3 -m pytest tests/test_portfolio_brief.py tests/test_portfolio_changes.py tests/test_portfolio.py tests/test_brief_context.py tests/test_admin_brief_gate.py -q` | 0 | **154 passed**, 85 warnings, 16.09s |
| 3 | `python3 -m pytest tests/test_portfolio_state_js.py tests/test_portfolio_truth_a1a_js.py tests/test_portfolio_auth_transition_js.py tests/test_portfolio_import_a1b_js.py -q` | 1 | 166 passed, **2 failed** — pre-existing, see below |
| 4 | `python3 -m py_compile app/main.py app/portfolio_brief_context.py engine/neuralweb/brain_gateway.py tests/test_portfolio_brief_context.py` | 0 | OK |
| 5 | `python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --gate code --pack-count 12 --plan-only --changed-from f125051f…` | 0 | 97/305 jobs; plan sha256 `f50bef19474d222f2a77bf628d383155c1666dfbc2c379a46fb34bdb5843a7c1` |
| 6 | same, `--gate data` | 0 | 57/72 jobs; `portfolio-ctx` selected; plan sha256 `c0ac787f832217740dac1e9eca4668ebcbabfbe90727ea1e2cc9bcd36e1b1471` |
| 7 | `python3 scripts/run_ci_pack.py … --changed-files-file` with ONLY `tests/test_portfolio_brief_context.py` | 0 | 57/72 data-gate jobs, `portfolio-ctx` selected — the new path DOES trigger the portfolio CI job |
| 8 | `python3 scripts/run_ci_pack.py … --changed-files-file` with ONLY `app/portfolio_brief_context.py` | 0 | 58/72, `portfolio-ctx` selected |

The repo has no ruff/flake8/pylint/mypy configuration and no lint job, so
"required lint" for this repo is the syntax check plus the scoped pytest
suites above (commands 1–4). The unrelated full-data suite was NOT run: there
is no concrete gate that needs it, and the change touches no data path.

## Environmental noise (not caused by this change)

- `tests/test_portfolio_import_a1b_js.py` — 2 failures:
  `FileNotFoundError: site/portfolio_import.css`, `site/watchlist.js`. These
  files are not checked out in the SPARSE worktree. The SAME two failures
  reproduce on the untouched base tree `6fd89c4f` (2 failed, 29 passed), so
  they are a sparse-checkout artifact, not a regression. The full-tree CI
  checkout (`sparse-checkout: /*\n!/site/\n!/data/`) does have `site/`.
- pytest's temp-dir cleanup raises `RecursionError` at session finish in this
  sandbox. It reproduces on `tests/test_portfolio_brief.py` alone on the
  untouched base tree. Every command above therefore passes an explicit
  `--basetemp`, which avoids it; the test RESULTS are unaffected.

## What the 245 tests prove

The suite discriminates original intent, not a helper's own behaviour.

1. **The shared fixture is a contract between two independent authorities.**
   `tests/fixtures/portfolio_brief_context/projection_cases.json` carries, for
   each of 64 synthetic rows, the Terminal's REAL `rowToPosition` output
   (generated by running the Terminal's own `terminal/lib/portfolio.ts` at
   `70ebc639e0a6795f8bc100008fa609406db72f3f` under
   `node --experimental-strip-types`) and the frozen composer's own reading
   (generated against the real `engine/portfolio_brief.py`, and cross-checked
   against that composer's OWN output weights by a two-row differential that
   recovers `float(entry_price)` and `float(shares)` exactly). The verdict in
   the fixture is derived from those two blocks, so the producer is checked
   against the Terminal and the composer — not against itself.
   46 cases are compatible, 18 are refused.

2. **The gate reproduces both readers exactly** (parametrized over all 64
   cases) and accepts exactly the compatible ones with the expected reason.

3. **The completeness proof.** Missing count, a count that disagrees with the
   rows returned (truncation), a non-zero start range, an invalid range, an
   over-limit book (1001 rows) and a transport failure are all unavailable.
   Exactly 1000 rows are witnessed. Duplicate ids are unavailable. A
   non-finite value is unavailable (and the witness is strict JSON).

4. **One read supplies both sides.** A spy on the unchanged `compose_brief`
   records its real arguments: the composer is called with exactly the
   selected source rows, and those rows equal the witness's `composer_inputs`.
   The reader records exactly ONE positions read.

5. **The cache cannot interfere.** A primed legacy cache is not served to an
   opted-in request, and the cached object is neither replaced nor mutated
   (identity and deep equality asserted). A bound request leaves
   `_PORTFOLIO_CACHE` empty. An ordinary request still uses the legacy cache
   and still serves its own hit.

6. **A same-count mutation is witnessed fresh.** Two bound requests with an
   unchanged count and a changed share value produce two different witnesses,
   and the FIRST response object is unchanged — a fresh witness is never
   stamped onto an earlier brief.

7. **The gates come first.** An unauthenticated request and a non-Pro
   request both perform ZERO positions reads (asserted on the reader's call
   log), and the Pro gate still answers 403 `pro_required`.

8. **Closed rows stay in the witness**, with their original values; only a
   trimmed+lowercased `closed` is closed, so `CLOSED` and `" open "` behave
   canonically.

9. **The watchlist fallback stays distinct**: explicit `watchlist_union`,
   `selected_position_ids` empty, `composer_input_source` recorded, and
   exactly ONE positions read. It is never produced from an unknown positions
   read (an incomplete capture fails instead), and a failed watchlist read is
   unavailable rather than an empty union.

10. **The witness never leaks**: no captured ticker appears in any log record
    or in any requested URL; the read path carries the owner filter only, and
    the transport helper REDACTS the owner id out of its debug log line (a
    test asserts `user_id=eq.***`).

11. **The header grants no authority**: the owner in the witness is the
    session's, and a forged owner header does not change it.

## The wire schema

The exact final wire fields are in
`docs/verification/portfolio-brief-snapshot-20261102/WIRE_SCHEMA.md`, with a
captured real response. In short:

```jsonc
"portfolio_context": {
  "schema": "portfolio_snapshot_witness.v1",
  "owner_id": "<authenticated owner>",
  "population": "positions" | "watchlist_union",
  "rows": [ /* the complete captured raw rows, verbatim */ ],
  "selected_position_ids": [ /* open + positionable ids */ ],
  "composer_input_source": "positions" | "watchlist_union",
  "composer_inputs": [ /* the exact rows compose_brief was called with */ ],
  "completeness": {
    "source": "portfolio_positions",
    "exact_count": 3, "range_first": 0, "range_last": 2, "returned_count": 3,
    "open_count": 2, "selected_count": 2, "max_rows": 1000,
    "positions_reads": 1, "complete": true, "watchlist": null
  }
}
```

Two fields beyond the plan's list, both additive and both load-bearing:

- `composer_inputs` — the exact rows the unchanged composer was called with.
  Without it a consumer could only compare SELECTED IDS, which the contract
  explicitly says is not enough: the consumer must be able to check ACTUAL
  INPUT COMPATIBILITY against its own `rowToPosition`. Carrying the inputs
  verbatim lets it do that without either side emulating the other's numeric
  semantics. It carries nothing that is not already in `rows`.
- `composer_input_source` — which population the composer was actually called
  with, so a `watchlist_union` witness can never be read as a positions book.

`selected_count` is added inside `completeness` so `open_count` (the rows the
canonical status rule calls open) cannot be confused with the number of
positions that actually qualify.

## What the producer deliberately does NOT do

- **No Python canonical hash.** The Terminal owns `portfolioBookKey`.
- **No currency re-interpretation.** The receipt is preserved verbatim; the
  Terminal derives the currency from the same bytes. The producer mirrors no
  ISO code list, so there is no second currency policy to drift.
- **No competing normalizer.** The Terminal reading exists only to COMPARE.
  A row whose two readings differ is REFUSED, never rewritten.
- **No second positions read**, no legacy loader call, no cached brief, no
  caller-supplied holdings or key, and no pagination stitched into a snapshot.
- **No mutation** of any production surface: no write, no DDL, no migration,
  no account, no database.

## GAPS — what is NOT done, and what the parent must decide

**1. The new test suite is not wired into CI (concrete gap, outside this
worker's owned paths).**

`tests/test_portfolio_brief_context.py` is a NEW file, and no CI job's
pytest command names it. The CI planner
(`scripts/run_ci_pack.py --gate data`) confirms the file DOES trigger the
`portfolio-ctx` job — that job is selected for this diff and
`tests/test_portfolio_brief.py` / `tests/test_portfolio_changes.py` will
re-run — but the job does not EXECUTE the new suite.

The fix is one line in `.github/ci/legacy-jobs.yml`, the `portfolio-ctx`
job's "portfolio-brief composer + endpoint tests" step (line 28721):

```diff
-        run: python -m pytest tests/test_portfolio_brief.py -q
+        run: python -m pytest tests/test_portfolio_brief.py tests/test_portfolio_brief_context.py -q
```

I VERIFIED this against a patched COPY of the manifest (`/tmp`, outside the
source workspace): the plan builds cleanly, `portfolio-ctx` stays selected,
and the data-gate scope grows to 62/72 jobs. I did NOT apply it — the CI
manifest is not in this worker's owned paths, and the parent owns that file.

**2. The gate's scope is the OPEN rows only.** A closed row never reaches the
composer, so the two readers cannot disagree about it; it is carried in the
witness verbatim and is not gated (beyond strict-JSON safety). If the parent
prefers every captured row to be gated, that is a one-line change to the gate
loop in `app/portfolio_brief_context.py` and it would refuse strictly more
books.

**3. The watchlist union carries its own completeness, but not a positions
book identity.** A `watchlist_union` witness has an empty
`selected_position_ids` and an explicit `composer_input_source`. There is no
Terminal-side book key for a watchlist union (the Terminal's
`portfolioBookKey` is positions-only), so the consumer must treat that
population as "no positions book" rather than looking for one. The parent
should confirm that reading before the Terminal consumer is written.

**4. No production-path exercise.** Everything here is synthetic. The
producer has never been run against the live Supabase project, so the
PostgREST `Content-Range` behaviour (the exact header form for a full, an
empty and an over-limit result set) is established from the documented
PostgREST contract and the unit tests, not from a live response. The first
live observation belongs to the parent's authenticated live-path acceptance,
after this lands and the Terminal consumer exists.

**5. The producer is a contract half.** The Terminal-side consumer is NOT
part of this run. Until it exists and validates the witness against its own
canonical read, nothing downstream binds a brief to a book.

## Generated artifacts

- The baseline worktree `/home/ubuntu0/lanes/tmp/pbs-baseline` (a detached
  worktree at `6fd89c4f`) was used for the baseline falsifiers and is
  REMOVED at the end of the run; the repo's worktree metadata is left clean.
- The fixture generators, the baseline probe and the Terminal-source harness
  live outside the source workspace, under
  `/home/ubuntu0/lanes/tmp/pbs-census/` and
  `/home/ubuntu0/lanes/tmp/pbs-terminal-check/`. They are tooling, not source.
- `.pytest_cache/` and `__pycache__/` produced by the test runs inside the
  source workspace are moved OUT of the workspace (not deleted in place, not
  gitignored) so canonical cleanliness — ignored files included — is
  preserved.

## Return

The artifact is the implementation commit on
`sol/web-portfolio-brief-snapshot-20261102`, pushed to the same branch with
an ordinary (non-force) push, PR #10551 still DRAFT and unarmed. The exact
head/tree, the changed paths, the commands and their exits, the baseline
falsifiers, the wire schema, the digests and the gaps are all recorded
above.

Next action for the parent: independent exact-head review, the CI-wiring
one-liner in gap 1, then the Terminal consumer against the wire schema in
`WIRE_SCHEMA.md`.
