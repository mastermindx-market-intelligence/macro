# Seat ruling — CDV-1 Tasks 2 and 3, parallel dispatch (r3), 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. Authority: Sol release ruling on #7905, comment 5902318060 (2026-09-30T01:33:57Z): "T2 source-currentness and T3 deterministic interpretation may advance under their existing packets and dependency law." Task 1 merged as squash `cdce3023fbbac95b1d2f3c51cd04903ecb2db1dc` at the released head `1c3e2215ee395217f2d8349b4e9e41eb028bd497`.

The binding lane commissions are committed next to this record:
- `packets/CDV1_T2_R3_PACKET_2026-09-30.md`
- `packets/CDV1_T3_R3_PACKET_2026-09-30.md`

Each commission is the 09-25 r2 packet, re-based on merged main, plus the rulings below. Each file is byte-identical to the `ruling` field the lane driver sent.

## Why an r3 was needed

- The r2 packets stacked on the unmerged Task 1 branch. Task 1 is now on main, so both lanes branch from fresh `origin/main` and open their PR against `main`.
- In r2, both packets appended to `tests/earnings_economic_fixtures.py` and both wired their suite into the same `earnings-economic-dossier` job. The plan's dependency law allows Tasks 2 and 3 to overlap "only with disjoint file grants", so the two lanes could not run in parallel on those grants.
- The T3 packet said the interpretation shape had "twelve" top-level keys. The plan (lines 144–145) and the packet's own list both name fourteen: `schema interpretation_id issuer event_id build selection observations comparisons findings missing_context next_evidence quality clocks authority`. That was a seat counting error, now corrected.

## Grants

| | Task 2 (`cdv1_t2_source_currentness_r3`) | Task 3 (`cdv1_t3_interpretation_r3`) |
|---|---|---|
| Source | `scripts/refresh_event_workspaces.py` (acquisition helper only); `engine/company_intelligence/pg_profile.py`, one appended section (pure addition) | new `engine/earnings_narrative/economic_interpretation.py` |
| Fixtures | `tests/earnings_economic_fixtures.py`, one appended section (pure addition), as the plan places it | new `tests/earnings_economic_interpretation_fixtures.py`, importing the Task 1 helpers read-only |
| Tests | new `tests/test_pg_economic_source_selection.py` | new `tests/test_earnings_economic_interpretation.py` |
| CI inventory | a new exclusive job `earnings-economic-source-selection`, inserted directly above `  earnings-economic-dossier:` | the dossier job only: new `paths:` lines after `"tests/fixtures/pg_envelope/**"`, and the suite inserted before the `run:` line's trailing ` -q` |
| `tests/test_ci_pack.py` | one `CURATED_EXCLUSIVE` entry, after `"earnings-economic-dossier",` | never touched |

The only file both lanes edit is `.github/ci/legacy-jobs.yml`. At the dispatch base, T2 inserts before line 14419 (`  earnings-economic-dossier:`). T3 inserts after line 14488 (`      - "tests/fixtures/pg_envelope/**"`) and edits the `run:` line at 14499. The 70 unchanged lines from 14419 to 14488 separate the two hunks, so neither change touches the other. The seat checks this with `git merge-tree` of the two heads before the second merge.

## T2 ruling R5 (added to R1–R4)

- The plan's placement stands. `prepare_pg_workspace` goes in `pg_profile.py`, and `fixture_http_get`/`fixture_accession` go in the Task 1 helper module. Both are pure additions: `git diff -U0 origin/main -- <both> | grep -c '^-[^-]'` must print 0.
- The preparation seam takes the acquisition result as data. It never imports `scripts.*` and never touches the network.
- CI gets its own exclusive job, because `scripts/refresh_event_workspaces.py` imports `engine.neuralweb.company_intelligence_reader` and, through it, `requests`. Putting that closure in the dossier job would widen a 20-minute suite to every PR in that import graph. The worked example for the closure is `industrials-result-cash`.
- The appends to `pg_profile.py` and to the fixture module still trigger the whole dossier job on the Task 2 PR. That job is the Task 1 invariance proof.
- n-B2 consequence: Task 2 is the producer of the release entry's `filing_key`, `source_sha256`, `form` and `url`. Each value comes from the actual acquisition, never from a constant, a fixture literal or a copy from `prior`. A test must show that changed received bytes at the same URL change the entry's digest.

## T3 ruling R2 (added to R1)

- Placement differs from the plan's "test helper in the Task-1 module", and only placement: Task 2 appends to that module in parallel. The helper's contract is unchanged. It is small and reviewer-visible, calls the real builder with real Task 1 inputs and an explicit `fiscal_scope`, and never hardcodes findings. The two plan tests stay verbatim apart from their import line.
- n-B1 consequence: the current/prior fiscal pair comes from the explicit `fiscal_scope` dates and the facts' own `period` fields, never from `fiscal_period` text fields. A test must show that altered `fiscal_period` text yields identical comparison rows or a typed refusal.
- n-B2 consequence: the release entry's metadata never selects, pairs or validates anything.

## Common precedence (both packets)

- Task 1 is frozen for both lanes: `pg_envelope.py`, `economic_observations.py`, `issuer_profiles.py`, every `tests/test_pg_envelope_f1*.py` and `tests/test_pg_economic_observations*.py`, `tests/fixtures/pg_envelope/**` and `research/**`. A failing frozen test is reported, never edited.
- Typed envelope outcomes are consumed as given.
- Environment note from Sol 5902318060: with the default 8 MiB stack, CPython 3.12 can SIGSEGV in teardown of the frozen R9 nested-deque probe. Lanes therefore run every dossier command under `ulimit -s hard`.
- Frozen-probe trap: `test_private_rights_token_is_the_single_registry_entry` scans every `engine/company_intelligence/*.py` for the private rights-profile literal. The constant is imported, never re-typed.
- Pre-push: `git fetch origin main`, then `git merge --no-ff` if main moved; never rebase. Both sides are kept on a conflict, and a conflict outside the owned files is BLOCKED.
- The PR opens as DRAFT against `main` and is never edited, labelled or marked ready by the lane. The seat owns review, readiness and the merge.

## Dispatch

| Lane | Host | Engine | Admitted | Executor start |
|---|---|---|---|---|
| `cdv1_t2_source_currentness_r3` | mb | glm-codex / glm-5.3, fix_timeout 10800 s, 1 round, seat review | 02:07:56Z at main `ef749400` | new-packet mode 02:09:08Z; executor process confirmed running |
| `cdv1_t3_interpretation_r3` | mini2 | glm-codex / glm-5.3, fix_timeout 10800 s, 1 round, seat review | 02:08:15Z at main `ef749400` | new-packet mode 02:09:22Z; executor process confirmed running |

Acceptance of each task stays with the seat's verification, an independent read-only Opus review and concluded CI. A lane's own PASS is a report, not acceptance.
