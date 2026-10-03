# Opus acceptance audit R9: CDV-1 T1 F1-Q envelope at 11bd3dea88795ac43ed0f356599efa08fc6ad36c (PR #7905)

MODE: READ_ONLY. R191 required one independent acceptance audit of the exact integrated head. It ran as two independent Opus auditors on the same head: group A took the reading side (the round-8 G1 and G3 files, R187's and R188's classes, the six originals and the real release), and group B took the validator side and integrity (the round-8 G2 and G4 files, R189's and R190's classes, the frozen suites, the merge, hosted CI).
- Each group's report follows verbatim, A then B. Probe files and raw outputs stayed in the seat's scratch directory. Nothing was written inside the worktree.
- Both groups record `git rev-parse HEAD` at the head and an empty `git status --porcelain`, before their first run and after their last.
- Each group reached its per-run turn limit once and was resumed with the same brief. Both reports are complete.

## STATUS: REJECT (both groups)

| group | families | status | blocking | other findings |
|---|---|---|---|---|
| A | A0 (round-8 G1 and G3 files), A1 (R187's class), A2 (R188's class), A3 (six originals, real release) | REJECT | A-R9-B1 | n1, n2, n3 (non-blocking) |
| B | B0 (round-8 G2 and G4 files), B1 (R189's class), B2 (R190's class), B3 (integrity), B4 (integration), B5 (hosted CI) | REJECT | B-R9-B1, B-R9-B2 | N1, N2, N3 (non-blocking) |

The seat's ruling on every finding is in `SEAT_RULING_T1_ENVELOPE_R9_2026-09-29.md`, beside this record.

---

## Group A: reading side (verbatim)

# OPUS T1 envelope audit R9 — group A (reading side: A0, A1, A2, A3)

Candidate: `$HEAD` = 11bd3dea88795ac43ed0f356599efa08fc6ad36c (PR #7905). Read-only on `$WT`; mutable copy under `a/tree/`, `$R8HEAD` comparison tree under `a/r8tree/` (198 config/engine/lib/tests files restored from `e6f49ceccb85` blobs, added files removed).
Pre-run check: `git rev-parse HEAD` = 11bd3dea8879…, `git status --porcelain` empty.

## A0 — round 8 G1 and G3 probe files, unchanged, from a copy at $HEAD
- G1 (`r8/g1/test_envelope_audit_probes_r8_g1.py`): 3.12.13 `15 failed, 686 passed in 232.31s`; 3.14.7 `15 failed, 686 passed in 227.19s`. Failure sets identical. All 15 are `test_g1_r8_B1_a_long_decimal_reference_never_raises_on_the_public_path[{attribute,comment,pinned_cell,script,text_after_body}-Q1..Q3]`, each at line 40 (`assert not {present floats}`): the build no longer raises and binds values. The probe's refusal expectation is R187's rejected design; accounting (values and validation) under A1 below.
- G3 (`r8/g3/test_envelope_audit_probes_r8_g3.py`): 3.12.13 `305 passed, 10 skipped in 97.05s`; 3.14.7 `305 passed, 10 skipped in 95.49s`. Matches the seat's claim.

A0 accounting (probe file `test_a0_*`, 15 cases, pass on both interpreters): the four out-of-table forms (text, comment, script, attribute) bind exactly the frozen present values of an unedited build and validate; the pinned-cell form (a reader prints `1` glued to the literal, e.g. `11.95`) never binds the frozen value and validates. The seat's disposition of G1's 15 failures (line 40 encodes the refusal design R187 rejects) holds against the bytes.

## Verdict: REJECT (one blocker, A-R9-B1)

### A-R9-B1 — BLOCKER, bar (d) (and (c): a tampered workspace raises instead of being refused), class R187
The validator reads character references on BYTES: `_PRINT_UNIT`'s named branch `[^\t\n\f <&#;]{1,32}` (engine/company_intelligence/economic_observations.py:238-241) counts bytes where `html.unescape` counts characters, so a named-reference-shaped run of `&` + 31 ASCII letters + a multi-byte character is cut inside the character, and `_drops_a_reference` decodes the cut group (economic_observations.py:281, `match.group(5).decode("utf-8")`) -> `UnicodeDecodeError`, which is not `EconomicObservationError` and escapes `validate_selected_facts` (trace: :620 -> `_validate_envelope_rows` :456 -> `_validate_envelope_span` :356 -> `_drops_a_reference` :280/:281). `html.unescape` returns such a run unchanged, so by R187's class test ("a character reference, in any form ... the span check, that raises") this is blocking. Pre-existing: the same 8 probes fail at `$R8HEAD` (`8 failed, 79 deselected`), i.e. R187's one-reader repair routed the digits through `receipts.unescape` but left the validator's byte-level reference tokenizer.
- Probes: `test_a1_the_validators_reference_reader_never_raises_on_a_named_run_cut_mid_character[e_acute|rsquo|math_bold|amp_prefix]` (unit) and `test_a1_a_relocation_beside_a_cut_named_run_is_refused_not_raised[...]` (public path: Q3 diluted-EPS receipt relocated through R143's seam, `r6.relocated`, onto `<p>&aaaa…aé 1.63</p>`).
- Observed: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc3 in position 32: unexpected end of data` (and the 2- and 3-byte analogues). Expected: `EconomicObservationError` (refused). Control `test_a1_control_the_same_relocation_with_an_ascii_run_is_refused_cleanly` passes (refused).
- Reproduce: `cd a/tree && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. <py> -m pytest -p no:cacheprovider -q ../test_envelope_audit_probes_r9_a.py -k cut` -> `8 failed` on 3.12.13 and 3.14.7.
- Not reachable by an untampered source in my probes (a bound literal's gap is layout only), so no wrong bind; it is an exception on the public validator from a tampered workspace plus source bytes.

## A1 — R187 class (search bounds)
- `test_a1_unescape_equals_html_unescape_wherever_it_returns`: 3,504 forms (29 code points incl. 0, C1 range, U+D800/DFFF, U+10FFFF/110000, 10^7..10^8; decimal/`x`/`X`; pads 0/1/7/700/4200 zeros; `;`, none, `x`, space terminators) + 23 edge forms (`&#`, `&amp;#49;`, `&notit;`, non-ASCII digits, signs): 0 mismatches.
- `test_a1_nothing_raises_past_the_least_limit_in_every_reader` (limit set in-process to 640; 641/4300/4301/20000 digits; `unescape`, `visible_text`, `_unassigned_character`, `_units`, `_drops_a_reference`): pass.
- `test_a1_public_path_under_the_least_limit_binds_the_frozen_values` (limit 640, 641 and 2000 digits, text/comment/attribute/script, Q1-Q3, 24 cases): frozen values, validates, admission returns a code: pass.
- Release parser: covered by the build path above; the `&#[0-9]{641}` guard (disclosure_diff.py:1119) makes a >640-digit decimal reference read as no blocks - fail-closed, note only.
- Remaining `int()` of source digits on the public path (pg_envelope.py:271, :336, :396, :857-866, :977): all regex-bounded to <=6 digits. None unbounded.

## A2 — R188 class (search bounds)
- Sweep `a2_sweep.py` (logs/a2_sweep_314.log): 46 banner values x {CORE, PCORE} x Q1-Q3 under R179's construction (title year removed, banner across the table) = 276 builds. 72 bind; every binding value is letterless apart from `{y}E` and names exactly the pinned year (`2025`, `2025 (1)`, `(1) 2025`, `2025, 2025`, `2025/2025`, `2025-2025`, `2025 - 2025`, `2025 ,2025`, NBSP/`&nbsp;` padded, `2025E`). Every other worded form (`Fiscal`, `FY`, `CY`, month words, `Year`, `Pre-Fiscal`, `Not Fiscal`, `… Guidance`, `Y2025`, `2025 2025`, `2025EE`, `{y}&#46;`, …) leaves the pin unlocated.
- Fiscal-year probe (the bytes: FY26 Q1 prose says "first quarter of fiscal year 2026" and "fiscal 2025 core EPS of $6.83"): `test_a2_a_fiscal_year_banner_naming_another_fiscal_year_never_binds` (20 cases, Q1/Q2, 5 fiscal forms) pass - no wrong-period bind.
- Probe file A2: 34 cases, all pass on both interpreters. No R188 blocker.

## A3 — six originals and the real release
- Census `a3_census.py` (admission code, sha256 of the sorted-JSON workspace, every present value/period/receipt span) at `$HEAD` (a/tree) and `$R8HEAD` (a/r8tree), 3.12.13 and 3.14.7: all four outputs identical. FY26 Q1/Q2/Q3 admit `F1-Q` with 19 present values each (sha256 prefixes ec2e1f13004b / 5cd20ac62fa4 / 59788fe39e21); FY25Q4 and FY26Q4 `unknown_table:t1`, CL2Q26 `not_ex_99_1`, 0 present.
- Demonstration: extracted script sha256 `8dafb2c3…71c52c3` = the file's stated sha256. Runs: 3.12.13 at HEAD, 3.14.7 at HEAD, 3.14.7 at R8HEAD: each `sources 6/6 | admitted 20/20 x3 accepted | refused 4 cases 0 present | tampered refused 9/9 | failures 0`, rc=0; JSON identical across interpreters and to R8HEAD (tree/python fields excluded). The published table (57 present cells) matches the JSON value, EDGAR literal, byte span and period in every cell: 0 mismatches.

## Non-blocking notes (one line each)
- n1: `{y}E` banners bind (R188 names E-suffixed years by design); a reader reads an estimate column - a basis question for seat adjudication, not a year-naming failure under the class test.
- n2: `Fiscal 2026` / `FY2026` (P&G's own name for the Sep/Dec 2025 quarters) leave CORE/PCORE unlocated under R179's construction - fail-closed coverage limit.
- n3: disclosure_diff reads no blocks for a >640-digit decimal reference - fail-closed coverage limit (R187's stated cost).

## Counts
- A0: G1 15F/686P, G3 305P/10S, each on 3.12.13 and 3.14.7.
- R9 probe file (87 cases): 8 failed / 79 passed on 3.12.13 (33.76s) and 3.14.7 (33.09s); identical failure sets, all A-R9-B1.
- Post-run check: `git rev-parse HEAD` = 11bd3dea88795ac43ed0f356599efa08fc6ad36c, `git status --porcelain` empty.

---

## Group B: validator side and integrity (verbatim)

# OPUS T1 envelope audit, round 9, group B (validator side + integrity) — PR #7905 @ 11bd3dea8879

Status: REJECT — two bar (d) blockers (B-R9-B1 in R189's class, B-R9-B2 other); B0, B2, B3, B4 clean; hosted CI green on $HEAD except one non-pack status context.

Probe file: `test_envelope_audit_probes_r9_b.py` (87 cases: 57 findings, 30 controls). Run from `b/tree` (copy of
config/ engine/ lib/ tests/ at $HEAD) with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. <py> -m pytest -p no:cacheprovider -q`.
- 3.12.13 venv312_min: `57 failed, 30 passed in 18.30s`; 3.14.7 venv_t1: `57 failed, 30 passed in 12.83s` (probes_r9_b_head.log).
- Same file on a tree with the five R187-R190 engine files restored from $R8HEAD (b/tree_r8), 3.14: `63 failed, 24 passed`
  = the same 57 + 6 surrogate/str controls R189 fixed. So both findings are INHERITED in form, but they sit inside the class R189 claims to close.

## Blocking findings

### B-R9-B1 — bar (d), class R189 — the walk is a closed list of containers, so non-listed carriers still raise
`_unprintable` (economic_observations.py:540-558) descends only `str`, `Rational`, `Mapping`, `list/tuple/set/frozenset`.
Any other value passes untouched, and the validator then prints/encodes it:
- `str(fiscal_period["quarter"|"year"])` at economic_observations.py:589 / :591 (no handler);
- `_fact_id` str()+encode at :100-102, whose only guard (:168-170) catches `RecursionError`.
Probes `test_b_r9_b1_fiscal_period_unwalked_value_is_refused[*]` (36/interp) and
`test_b_r9_b1_present_period_unwalked_value_is_refused[*]` (15/interp), Q1-Q3, both interpreters:
| value (stdlib, no user code) | site | observed | expected |
|---|---|---|---|
| `range(10**5000)`, `slice(10**5000)`, `deque([10**5000])`, `SimpleNamespace(x=10**5000)` | :589/:591, and :102 via present `period` | `ValueError: Exceeds the limit (4300 digits) for integer string conversion` | EconomicObservationError |
| `deque`/`UserList` nested 100,000 deep | :589/:591 | `RecursionError` | EconomicObservationError |
| `PurePosixPath("\udc80")`, `UserString("\ud800")`, `ValueError("\ud800")` as a present row's `period` | :102 (G2-R8-B2's own site) | `UnicodeEncodeError: surrogates not allowed` | EconomicObservationError |
R189's text claims "After the walk, nothing the validator prints or encodes can meet any of the three"; these are the
three forms (digit limit, depth, lone surrogate) at the ruling's named sites, carried by types the walk does not visit.
Class-level fix direction (not prescribed): refuse at the entry any value whose type is not in the JSON-shaped set, rather than descend a list of containers.

### B-R9-B2 — bar (d), other (a comparison, R189-adjacent) — signalling Decimal NaN raises in the non-envelope branch
Rename the workspace's release `document_id` (so `release_text` is not the wrapped envelope and the validator takes the
legacy branch), then set a present receipt's `segment_bytes` or the event ids to `Decimal("sNaN")`.
Observed: `decimal.InvalidOperation` escapes at economic_observations.py:754 (`segment_bytes != len(...)`) or :656
(`row.get("event_id") != event_id`). Expected: EconomicObservationError. Probe `test_b_r9_b2_signalling_nan_is_refused[*]`
(6/interp). The envelope branch is not affected (json.dumps TypeError and hash TypeError are caught there).

## Families
### B0 — round 8's G2 and G4 files, unchanged, from a copy at $HEAD (b0.log)
- G2 (78): 3.12 `78 passed in 45.56s`; 3.14 `78 passed in 34.29s` — matches the seat's claim.
- G4 (167, worktree cases run read-only against $WT): 3.12 `1 failed, 166 passed in 84.32s`; 3.14 `1 failed, 166 passed in 82.66s`.
  The one failure is `test_i1_head_and_clean`: `assert '11bd3dea8879…' == 'e6f49ceccb85…'` — its pinned constant is the
  round-8 head; expected once HEAD moved. Seat claimed 158 passed with the worktree cases not run; running them gives 166/1, fully accounted.

### B1 — R189 class (b1_explore.py, b1_explore_Q3.out; probe file)
Q3 exploration, 23 values x 5 fields + 8 legacy-branch cases, both interpreters: every JSON-shaped and walk-listed type
(bool, None, Decimal NaN/1, Fraction incl. 10**400, complex, bytes, NaN, +/-inf, 10**639, set, tuple, non-str key) was refused;
the 23 EXC per interpreter are exactly B-R9-B1 and B-R9-B2. The probe file extends these to Q1-Q3 (57 finding cases, 30 controls).
Lone-surrogate source texts / release bodies: covered by the R8 suite's R189 witnesses (which pass in the gate run) and not re-searched.
Not searched (bounded round): every one of the 1,699 leaves per workspace; only fiscal_period, event_id, the first present row's period/value, and one receipt field.

### B2 — R190 class (b2_explore.py, b2_reader.py; html5lib 1.1 on /opt/homebrew python3 3.14.7)
Relocation through the R143 seam (round 8's G2 `reseat` construction) of the diluted-EPS literal onto a copy placed
beside 36 tag forms (start/end/void tags, `</p>`, `</br>`, upper/mixed case, whitespace, `/>`, comments, PI, `<plaintext>`,
table-section tags) x before/after x 9 contexts (p, div, svg, math, select, template, table cell, button, font), Q1-Q3, on 3.14:
1,944 records; admission F1-Q 552; `_whole_printed_token` true 240; accepted through the seam 240; **glued as html5lib prints: 0**.
Accepted tags are only `<p>`, `<P >`, `<div>`, `<DiV\n>`, `<br>`, `<BR/>`, `</p>`, `</P >`, `</br>`, `</BR >`.
Stray table start tags in body and every foreign/select/template context are refused by admission (`markup_unreadable:*`).
Reader sanity: html5lib prints `<p>Zq</div>1.50</p>` and `<p>Zq<td>1.50</p>` as `Zq1.50` (glued), `<p>Zq<br>1.50</p>` as separate.
No R190 finding.

### B3 — integrity (b3_b4_git.txt, b3_b5_raw_turn2.txt) — PASS
- `git log --first-parent --name-only $R8HEAD..$HEAD`: 26b4262a5172 merge -> 3d4986ee12be (`.github/ci/legacy-jobs.yml` only)
  -> 2a839e943504 freeze (legacy-jobs.yml, R8 audit, R7 ruling mark, R8 ruling, r7 amendment, r8 suite) -> 628b51cab635 R187
  (receipts.py, pg_envelope.py, economic_observations.py, disclosure_diff.py) -> 15271a4b072b R188 (pg_envelope.py)
  -> 0329e946aa1f R189 (economic_observations.py, binding.py) -> 4278ae834fa5 R190 (economic_observations.py)
  -> 11bd3dea8879 receipt (research/…/T1_REAL_RELEASE_DEMONSTRATION_2026-09-29.md only). All authored `Sol CEO`.
- `git diff --stat $R8HEAD $HEAD -- tests/ .github/`: 161 files, +39,904/-810 — all but two test files arrive with the
  merge of $MAIN; the PR's own test delta is `test_pg_envelope_f1_probes_r7.py | 3 +-` and `test_pg_envelope_f1_probes_r8.py | 356 +`.
- Frozen drift (`test_pg_envelope_f1.py`, `_r1`..`_r6`, `tests/fixtures/pg_envelope/`): empty.
- R7 amendment: exactly `"2025x"` and `"No. 2025"` leave `NAMED` plus one comment naming R8's file.
- Freeze's legacy-jobs hunk: adds the R8 suite to the dossier job's paths and run line; `timeout-minutes` 15 -> 20. Nothing else.

### B4 — integration (b3_b4_git.txt) — claims PASS; runs below
- Merge parents = $R8HEAD, $MAIN; merge-base($R8HEAD,$MAIN) = $BASE.
- PR files ($BASE..$R8HEAD) = 92; files differing $MAIN..$MERGE = 92, the identical set. Touched by both sides: `legacy-jobs.yml`, `tests/test_ci_pack.py`.
  The other 90 are blob-identical between $MERGE and $R8HEAD.
- legacy-jobs.yml: $MAIN->$MERGE numstat `85 0`, $BASE->$R8HEAD `85 0`, and the 85 added lines are identical; 0 removed.
- test_ci_pack.py: `1 0` both ways, identical line `"earnings-economic-dossier",`.
- $INT: exactly two added path lines (`pg_envelope.py`, `pg_profile.py`) under `industrials-result-cash`'s paths.

### B2 addendum — every present literal (b2_full_314.jsonl, 3.14)
Contexts p, div, font x the same 36 tags x before/after, all 19 present literals of each of Q1, Q2, Q3: `records 12312 secs 2017.5`;
admission F1-Q 7,866; accepted through the seam 3,420 (receipt moved in each); html5lib reader: `accepted 3420 glued 0`.

### B4 runs at $HEAD
- Gate job run line (25 files) in $WT, venv312_min 3.12.13: `1960 passed, 174 skipped, 47 warnings in 505.69s`; wall 508 s vs `timeout-minutes: 20` (1,200 s). Matches the seat.
- `tests/test_ci_pack.py -k curated_exclusive`: 3.12 `2 passed, 143 deselected in 158.67s`; 3.14 `2 passed, 143 deselected in 109.60s`.
- Nine envelope suites, 3.14 venv_t1: `1136 passed in 434.27s` (3.12 covered inside the gate line).
- Six release-parser neighbours, /opt/homebrew/bin/python3.12: `2 failed, 287 passed in 111.03s`; the 2 are
  `test_capital_structure_document_terms.py::test_clean_preimport_forged_{stdlib_method,html_helper}_*[cpython-3.12.2-python-org]`,
  the same interpreter-provenance pair G4 recorded at $R8HEAD (rp_head_wt.txt). Not caused by this PR.

### B5 — hosted CI (b5_read1_checks.txt, b5_read2.txt; 2 gh reads)
- Read 1 (19:03:37Z) and read 2 (19:48:19Z): `headRefOid 11bd3dea88795ac43ed0f356599efa08fc6ad36c` = $HEAD, `isDraft true`;
  mergeStateStatus `UNKNOWN` then `UNSTABLE` (not DIRTY).
- Identical on both reads: ci-pack-0..11, ci-gate, ci-plan, contract-delta, fence-pack, ci-authority, ci-authority/main,
  capability-broker, grader-manifest, self-mod-fence = pass (run 36609120801 / 36609120589); trusted-ci and three fork-only jobs skipping;
  `ci-authority/codex/merge-queue-pilot` = **fail** (status context, 0 s). Nothing pending.

### Confirmations
$WT: `git rev-parse HEAD` = $HEAD and `git status --porcelain` empty before the first run and after the last.

## Non-blocking notes (one line each)
- N1: `ci-authority/codex/merge-queue-pilot` fails on $HEAD and is what makes the PR UNSTABLE; it is not a ci.yml pack. Whether it binds is Sol's call.
- N2: G4's `test_i1_head_and_clean` pins the round-8 head, so it now fails by construction.
- N3: `_unprintable`'s bound is on `Rational` only; a Decimal is not walked. It is harmless on the envelope branch (json.dumps refuses it) and is the carrier of B-R9-B2 on the legacy branch.
