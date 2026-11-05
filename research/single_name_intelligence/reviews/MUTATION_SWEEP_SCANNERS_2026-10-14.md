# MUT6/M6J mutation sweep — acceptance scanners, 2026-10-14

SNI-local DRAFT contract review (commission 8659, lane M6J). It consumes
owner-supplied scanner code and committed registry text only; it does not
mint, derive, or guess canonical HK/US issuer or security identifiers
(identity ids are caller-supplied opaque strings owned by Stock Identity /
Data OS; unknown identity stays UNRESOLVED / null). Nothing here feeds a
ranker, gate, sizer, signal, escalation, or trade path; every authority
flag stays literal false. Fixtures in the killing tests are synthetic.

Swept modules (read-only, not edited): `acceptance/ticker_branch_scan.py`
(all functions, 755 lines) and `acceptance/sni_copy_guard.py` (all
functions, 421 lines) at base commit `831e5f638e9`.

Existing tests used (every `tests/test_sni_*.py` importing either module):
`tests/test_sni_copy_guard.py`, `tests/test_sni_mutation_branch_copy.py`,
`tests/test_sni_no_ticker_branches.py` — 50 tests, unmutated baseline
green in 5.52 s (< 20 s, so the 15-mutant cap was NOT triggered; the full
40-per-module / 60-total budget applied).

## Summary

| metric | count |
|---|---:|
| mutants generated | 60 (ticker_branch_scan 40, sni_copy_guard 20) |
| killed before (existing suite) | 46 |
| survived before | 14 |
| killed after (new tests) | 13 |
| equivalent | 1 |
| timeout / timeout-unsafe | 0 / 0 |
| score before | 46/60 = 76.7 % (46/59 = 78.0 % excl. equivalent) |
| score after | 59/60 = 98.3 % (59/59 = 100 % excl. equivalent) |

## Operator set and seed

Operators (frozen method): comparison flip (`<`<->`>=`, `>`<->`<=`,
`<=`<->`>`, `>=`<->`<`, `==`<->`!=`); arithmetic swap (`+`<->`-`,
`*`<->`/`); constant perturbation (int n -> n+1, float x -> x*1.001,
`True`<->`False`); `return x` -> `return None` on one return per
function; `and`<->`or`; deletion of one `if ...: raise` guard (raise
replaced by `pass`). Selection: `random.Random(20261014)` over candidate
sites, stratified by innermost enclosing function (module-level
statements form one `<module>` stratum, following the MUT3B precedent),
per-stratum shuffle then round-robin in first-line order; caps 40 per
module and 60 total, so `ticker_branch_scan` (233 candidates) filled 40
and `sni_copy_guard` (93 candidates) took the remaining 20.

Harness (scratch, `~/lanes/scratch/m6j/harness2.py`, not committed):
one newline-free textual mutation per run (file line count preserved and
asserted, so file:line citations stay valid), `ast.parse` validity check,
then `python3 -m pytest <the 3 importer test files> -x -q -p
no:cacheprovider` under a 60 s timeout, then original bytes restored and
sha256 verified before the next mutant. Safety: `git status --porcelain
-- research/ tests/` after every mutant; only the mutated module was
ever allowed to appear — no other change occurred (0 timeout-unsafe).

## Per-module table

| module | candidates | selected | killed-before | survived | killed-after | equivalent | timeout |
|---|---:|---:|---:|---:|---:|---:|---:|
| acceptance/ticker_branch_scan.py | 233 | 40 | 29 | 11 | 10 | 1 | 0 |
| acceptance/sni_copy_guard.py | 93 | 20 | 17 | 3 | 3 | 0 | 0 |
| total | 326 | 60 | 46 | 14 | 13 | 1 | 0 |

Module sha256 before/after the sweep (restored byte-identical):
`ticker_branch_scan.py` `48b8a1e1dc9212b87b7f955376045ed399833837eeec3c266712cd5a685c1d83`;
`sni_copy_guard.py` `0f5cd66234b5f4183dbd8a47a5e70f2711bc5b7f28dbe0043e0d81d71fa30252`.

## Surviving mutants and killing tests

All killed-after claims were re-verified by re-applying the exact mutant
and running only `tests/test_sni_mut6_scanners.py` (each re-run FAILED,
13/13).

| id | site (file:line, original -> mutated) | killing test |
|---|---|---|
| M02 | ticker_branch_scan.py:84, `key != canonical` -> `==` | `test_m6j_ticker_branch_scan_refuse_authority_override_1` |
| M07 | ticker_branch_scan.py:204, `i + 1` -> `i + 2` | `test_m6j_ticker_branch_scan__split_key_value_1` |
| M10 | ticker_branch_scan.py:269, `i + 1 < n` -> `i + 2 < n` | `test_m6j_ticker_branch_scan_parse_map_1` |
| M11 | ticker_branch_scan.py:298, `return _minimal_yaml_load(text)` -> `return None` | `test_m6j_ticker_branch_scan__load_yaml_text_1` |
| M12 | ticker_branch_scan.py:306, `and` -> `or` | `test_m6j_ticker_branch_scan__collect_profile_fields_1` |
| M16 | ticker_branch_scan.py:385, `and` -> `or` | `test_m6j_ticker_branch_scan__folded_set_1` |
| M23 | ticker_branch_scan.py:453, `limit: int = 160` -> `161` | `test_m6j_ticker_branch_scan__snippet_1` |
| M31 | ticker_branch_scan.py:656, `return True` -> `return False` | `test_m6j_ticker_branch_scan__rel_matches_1` |
| M34 | ticker_branch_scan.py:717, `return False` -> `return True` | `test_m6j_ticker_branch_scan_allowlist_matches_1` |
| M35 | ticker_branch_scan.py:734, `used[i] = True` -> `= False` | `test_m6j_ticker_branch_scan_partition_allowlist_1` |
| M45 | sni_copy_guard.py:213, `(best[1] - best[0])` -> `(best[1] + best[0])` | `test_m6j_sni_copy_guard__first_match_1` |
| M49 | sni_copy_guard.py:310, `i += 1` -> `i += 2` | `test_m6j_sni_copy_guard_split_sentences_1` |
| M53 | sni_copy_guard.py:369, `a30[0]` -> `a30[1]` | `test_m6j_sni_copy_guard_check_text_1` |
| M09 | ticker_branch_scan.py:241, `i += 1` -> `i += 2` | EQUIVALENT (see below) |

Notable semantic holes the survivors exposed, now pinned: an allowlist
entry with a wrong `kind` silently matched (M34) and a consumed entry was
reported stale (M35) — together they could have hidden a real ticker
branch from `check_allowlist`; the PyYAML-rejects-text fallback (M11) and
the no-space YAML `key:value` split (M07) were unexercised; the A30
subject/claim recording (M53) and the table-cell split (M49) were
unpinned in the copy guard.

## Equivalent arguments

- M09 (ticker_branch_scan.py:241, `i += 1` -> `i += 2` in `parse_list`):
  the branch is dead code — it runs only when a stripped list item is
  empty, but items come from `lines.append((indent, line.strip()))`, and
  `"-" ` cannot survive `.strip()` (a bare `-` fails the
  `startswith("- ")` loop guard), so no input reaches the mutated
  counter.

## Excluded QF lines

`reviews/QF_QUARANTINE_FENCE_2026-10-13.md` pins fence points only in
`residual/` and `event_response/` files (s1_manifest.py:26/133/144,
s2_seal.py:177/416/419, s2_splits.py:40/64, s1_prereg.py:188/192,
run_s1.py:309/341/349/353/486/643/650, run_s2.py:319/941,
s1_report.py:417). Zero pinned lines fall in the two swept modules, so
no mutant was excluded.

## What this does NOT prove

A mutation score measures test strength against this operator set and
this 60-mutant sample, not statistical validity of any SNI estimate; it
says nothing about coverage of operator kinds outside the frozen set
(e.g. statement deletion, argument swaps). No acceptance row moves to
DONE as a result of this sweep; the acceptance matrix and the sealed run
trees are untouched. The 46 mutants the existing suite killed and the 13
new kills re-verified here are evidence about the scanner tests only.

## Environment note (pre-existing, not caused by this lane)

`python3 research/single_name_intelligence/evaluation/seal_full_check.py
--study all --strict-bytes` on this worktree at the pinned base commit —
run before committing, with and without this lane's untracked files —
ends `SEAL FULL CHECK: DIFFERS`: s1 `results/P03.json` and the nine
`observations/P03_*.json` byte-differ (48 compared, 11 failures), s2
compared=23 failures=0. This reproduces on the pristine tree before any
of this lane's changes (this lane writes only the two owned files), so
it is a host-regeneration difference of the sealed P03 family, not a
change made here; the committed diff contains zero bytes under
`residual/` and `event_response/`.
