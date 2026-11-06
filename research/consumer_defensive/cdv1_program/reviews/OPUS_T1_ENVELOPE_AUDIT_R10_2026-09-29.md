# Opus acceptance audit R10: CDV-1 T1 F1-Q envelope at 6caa2ffc1a954c3d9ce39a8237d3cbc84527b2c5 (PR #7905)

MODE: READ_ONLY. R194 required one independent acceptance audit of the exact head that carries R192–R194. It ran as two independent Opus auditors on the same head. Group A took the reading side: round 9's group A file, R192's class, and the originals with the real-release demonstration. Group B took the validator side and integrity: round 9's group B file, R193's class, the freeze and the gate, and hosted CI.
- Each group's report follows verbatim, A then B. Probe files and raw outputs stayed in the seat's scratch directory. Nothing was written inside the worktree.
- Both groups record `git rev-parse HEAD` at the head and an empty `git status --porcelain`, before their first run and after their last.

## STATUS: REJECT (group B); group A ACCEPT

| group | families | status | blocking | other findings |
|---|---|---|---|---|
| A | A0 (round 9's group A file), A1 (R192's class), A2 (originals, real release) | ACCEPT | none | n-A1, n-A2 (non-blocking) |
| B | B0 (round 9's group B file), B1 (R193's class), B2 (integrity), B3 (hosted CI) | REJECT | B-R10-B1, B-R10-B2 | n-B1, n-B2, n-B3 (non-blocking) |

The seat's ruling on every finding is in `SEAT_RULING_T1_ENVELOPE_R10_2026-09-29.md`, beside this record.

---

## Group A: reading side (verbatim)

# Opus T1 envelope acceptance audit, round 10, group A (A0, A1, A2)

Head audited: 6caa2ffc1a954c3d9ce39a8237d3cbc84527b2c5 (R192 dfc26df12f9a, R193 6caa2ffc1a95 over freeze fdf9bd327177). READ_ONLY on $WT.
Before the first run and after the last: `git rev-parse HEAD` = 6caa2ffc1a95..., `git status --porcelain` empty.
Mutable trees: `$MY/audit_t1_envelope_r10/a/tree` (cp -R config engine lib tests from $WT; engine diff -r identical) and
`r9tree` (same, with `economic_observations.py` from `git show 11bd3dea8879:`; engine/lib/config otherwise identical
between R9HEAD and HEAD per `git diff --stat 11bd3dea8879 HEAD -- engine lib config` = that one file).

## STATUS: ACCEPT (group A families) — no blocker, major or minor finding.

## A0 — round 9's group A file, unchanged copy at $HEAD
- `r9a_copy.py` (byte copy of `audit_t1_envelope_r9/a/test_envelope_audit_probes_r9_a.py`), 3.12.13 (venv312_min) and 3.14.7:
  `1 failed, 86 passed` on each. The one failure is `test_a1_the_validators_reference_reader_never_raises_on_a_named_run_cut_mid_character[amp_prefix]`
  at its first assertion `html.unescape(s) == s`.
- Checked against the bytes: `html.unescape("&amp" + "b"*28 + "é")` = `"&" + "b"*28 + "é"`. The charref regex takes the 32-character run
  `amp`+28 b+`é`, no entity of that name exists, and the longest legacy prefix `amp` is replaced. The premise is false, so R194 is confirmed.
  The case's engine assertion holds on all four forms: `_drops_a_reference(...) is False` with whole-character units
  (probe `test_a0_engine_assertion_holds_on_all_four_cut_forms`, which passes at HEAD and fails at R9HEAD).
- Every other outcome passes. That covers G1's line-40 accounting, the 640-limit readers, the eight A-R9-B1 cut-run cases (now refused or accepted, never raised) and their ASCII control, and the R188 notes.

## A1 — R192's class
Direct sweep, `a1_direct.py` (run from tree, both interpreters, identical counts, **0 failures in every category**):
- Constructions: name lengths 1..64; 10 characters (2-, 3- and 4-byte, CJK, a combining mark, ZWJ, ZWNJ, BOM, NBSP, U+00FF) at the begin, middle and end of the name and as every character of it; prefixes `&`, `&amp`, `&nbsp` and `&not`; 12 terminators (`;`, `<`, `&`, space, `\n`, `\t`, `\f`, `#`, end, `1.63`, `;1.63`, `<b>`); 9 contexts (p text, bare, comment, attribute, inside a tag, script, style, textarea, title).
  That gives 1,105,920 sources.
- Checks:
  - `_printed_units` covers the source contiguously with whole-character units and never raises.
  - For every text run, the per-unit `receipts.unescape` join equals `receipts.unescape` and `html.unescape` of the run, and each reference unit equals `html._charref`'s match at the same position.
  - `_drops_a_reference` equals the `html.unescape` oracle on markup-free sources.
  - `_drops_a_reference` never raises on 7,680,000 char-aligned prefixes and suffixes, which model gaps and spans. The length subset is {1,2,3,15,16,30..34,63,64} in 4 contexts.
  - On 1,175,040 misaligned cut points, both halves raise `EconomicObservationError`, never another exception.
  - `_whole_printed_token` never raises on 10,590,564 char-aligned spans.
- Logs: `logs/a1_direct_312.log` and `logs/a1_direct_314.log`, each ending `"counts": {}, "first": {}`.

Public path, `a1_public.py` (3.14.7 only; see GAPS):
- Every present literal of Q1–Q3 (57): 6 core runs × {pre_glued, post_glued, pre_space}. Q3 DIL: 15 runs × 6 joins. That gives 1,098 constructions.
- V1 puts the construction in the pinned cell itself, with no seam, and builds through the product path. V2 puts a `<p>` copy before `</TEXT>` and relocates the metric's receipt onto it through R143's seam (`r4.reseat`), with the seam active through validation.
- Oracle: the reader prints the literal as a whole token only if `html.unescape(pre + lit + post)` equals the concatenation of the three pieces, and the neighbouring printed characters are layout space or absent.
- Result: raise 0, v1_wrong_bind 0 (4 bound, all whole-token), v1 refused-untampered 0, v2 accepted 5, v2 accepted-not-whole **0**.
  422 V2 relocations onto whole tokens are refused: the gap rule "span is not a whole literal" refuses any printed text between `>` and the span. That is a fail-closed coverage limit (non-blocking).

## A2 — originals and the real-release demonstration
- `a2_census.py` on tree and r9tree, on 3.12 and 3.14. The four JSON outputs are byte-identical (`cmp`), and 3.12 equals 3.14. Each holds the six originals': admission code, workspace sha256, every present value/period/span/unit/basis, the validation outcome, and a sha256 of `_printed_units` over each source.
  - Q1, Q2 and Q3: F1-Q, 19 present values each, accepted.
  - FY25Q4 and FY26Q4: `unknown_table:t1`. CL2Q26: `not_ex_99_1`. All accepted as typed absences.
- Demonstration script: extracted from HEAD's `T1_REAL_RELEASE_DEMONSTRATION_2026-09-29.md` lines 111–300. Its sha256 is `8dafb2c3…71c52c3`, as the document states.
  - Run on tree and r9tree, on 3.12 and 3.14: `sources 6/6 | Q1/Q2/Q3 20/20 accepted | 4 refused, 0 present, accepted | tampered refused 9/9 | failures 0`, rc=0.
  - The four JSON outputs are identical once `tree`/`python` are removed. The refusal and tamper details equal §3 and §4 of the document.
- Table §2 against the bytes: all 57 present cells were parsed from the markdown. Each literal equals `source_bytes[start:end]`, the offsets equal the census receipt, the period matches, and engine = oracle = census value. 0 mismatches.

## Probe file
`test_envelope_audit_probes_r10_a.py` holds controls and regression pins only; there is no blocking finding to reproduce.
- At HEAD: 305 passed on 3.12.13 and on 3.14.7.
- At R9HEAD (r9tree, 3.12.13): 200 failed and 106 passed. The failures are the 192 R192 unit/agreement cases, the 4 A0 cut forms, the misaligned-fragment refusal, and 3 relocations that raise `UnicodeDecodeError`. Those are A-R9-B1, closed at HEAD.

## Non-blocking notes (one line each)
- n-A1: a relocation onto a whole token that follows other printed text in the same element is refused by the gap rule (422 of 1,098 V2 cases): fail-closed coverage limit, by R155.
- n-A2: `_print_matches` refuses a misaligned fragment with EconomicObservationError. No public-path caller can produce one (span decoded first, gaps cut at ASCII `>`/`<`). Observation only.

## GAPS
- A1 public sweep (`a1_public.py`, 862 s) ran on 3.14.7 only. It has no interpreter-specific code: str regex, no Unicode categories, and `html.entities` is the same on both. The same relocation shapes ran on 3.12.13 through the probe file's 6 relocation cases (pass), and the direct sweep ran on both interpreters.
- No html5lib or lxml cross-check was run. The public-path oracle is `html.unescape` over markup-free `<p>` content, which is exactly what an HTML5 reader prints for text-only content.
- A1 contexts on the public path covered only text in `<p>`. The comment, attribute and raw-text contexts ran on the direct functions only, because relocations there fall under R176/R182's accepted rule.
- The 3.11 interpreter was not used; it is not required for group A.

## DEVIATIONS
- The first two probe-file runs failed: one scoped the seam out before validation, and one expected acceptance where the gap rule refuses. Both were probe errors, corrected before the recorded runs, which were 305/305 on both interpreters. The earlier logs were overwritten.
- The agent-level rule against writing report files was set aside because the commission's RETURN explicitly requires this file.

---

## Group B: validator side and integrity (verbatim)

# Round-10 acceptance audit, group B (validator side and integrity) — PR #7905 at 6caa2ffc1a95

(written incrementally; final STATUS at the end of this file)

## Setup
- $WT HEAD = 6caa2ffc1a954c3d9ce39a8237d3cbc84527b2c5, `git status --porcelain` empty before the first run.
- Mutable copy: `b/{config,engine,lib,tests}` (cp -R from $WT at HEAD). R9HEAD copy: `b/r9tree/` = same tree with
  `engine/company_intelligence/economic_observations.py` from `git show 11bd3dea8879:…` (the only engine/lib/config file
  that differs between R9HEAD and HEAD: `git diff --stat R9HEAD HEAD -- engine/ lib/ config/` = 1 file, +47/-23).

## B0 — round 9's group B probe file, unchanged, from the copy at HEAD
- `b0.sh` -> `b0.log`: venv312_min 3.12.13: **87 passed**; venv_t1 3.14.7: **87 passed**. (At R9HEAD these were
  the B-R9-B1/B2 reds; every one now passes, and the controls pass.) No outcome to account for beyond "all pass".

## B1 — R193's class (findings)
### B-R10-B1 — BLOCKER (d), class R193: an exact `Fraction` is admitted as a leaf; its parts are never checked
- Code: economic_observations.py:573-575 (`elif kind is int or kind is Fraction: if abs(item.numerator) >= … or
  item.denominator >= …`). R193 admits `Fraction` "by its exact type", but a Fraction is a two-slot container
  (`_numerator`, `_denominator`, writable) and the walk never checks that either part is an exact int.
- (i) non-numeric part -> TypeError raised INSIDE the entry walk, :574 (`bad operand type for abs(): 'NoneType'`, or
  `'>=' not supported … 'NoneType' and 'int'`) — at any depth, even in a field the validator never reads (`claims`).
- (ii) denominator 0 passes the walk and raises `ZeroDivisionError` at `_finite` :96 (`float(Fraction)`), reached via
  :457 -> :217 -> :204 for a present row's `value`. `_finite` catches only OverflowError.
- (iii) an int-subclass part with a hostile `__str__` passes the walk (abs() returns a plain int) and raises at
  `str(fiscal_period.get("quarter"))` :613 / :615.
- Probes: `test_b_r10_b1_fraction_with_non_int_part_is_refused` (36), `…_zero_denominator_value_is_refused` (3),
  `…_hostile_int_subclass_part_is_refused` (6). Expected: EconomicObservationError. Observed: TypeError /
  ZeroDivisionError / RuntimeError escapes validate_selected_facts. Fails at HEAD and at R9HEAD (inherited; R189's
  `isinstance(item, Rational)` branch read the same two attributes).

### B-R10-B2 — BLOCKER (d), class R193: an admitted list/dict where a document id belongs (non-envelope route)
- Route: when the release's `document_id` names no caller-held text, `validate_selected_facts` skips the envelope
  branch (:633) and runs the non-envelope checks (:646+). For a present row, :767 `source = source_texts.get(document_id)`
  runs BEFORE :768's `isinstance(document_id, str)`; an exact `list` or `dict` passes the entry walk and raises
  `TypeError: unhashable type` (3.14: `cannot use 'list' as a dict key`).
- Probe: `test_b_r10_b2_legacy_route_unhashable_document_id_is_refused` (12). Expected: EconomicObservationError
  (the control with a str id is refused "present observation belongs to another document"). Observed: TypeError.
  Fails at HEAD and at R9HEAD (inherited).

## Probe file results (`test_envelope_audit_probes_r10_b.py`, 72 cases: 57 finding + 15 controls)
- HEAD, venv312_min 3.12.13: 57 failed, 15 passed. HEAD, venv_t1 3.14.7: 57 failed, 15 passed.
- R9HEAD (r9tree), venv312_min: 57 failed, 15 passed.
- Traceback sites observed (Q3 sample, --tb=short): :574 in _unprintable; :96 in _finite (via :204/:217/:457/:644);
  :767 in validate_selected_facts.
- (iii) confirmed: RuntimeError("hostile __str__") at :613 (quarter) and :615 (year), 3 each.

## B1 — systematic walk (b1_walk.py; search bounds)
- Values per path (~70): the nine admitted types misplaced (Fraction 1/3, 3, 10**639, 1/10**639; tuples incl. 31-deep;
  float nan/inf/-inf/-0.0/1.0; True/False; None; ints incl. 10**639-1; str; list; dict keyed by int, tuple, None,
  Fraction, float, NaN, bool, mixed), subclasses of str/int/float/list/tuple/dict/Fraction, Decimal (incl. sNaN),
  complex, bytes, set, frozenset, range, deque, hostile objects raising in __eq__/__hash__/__str__/__repr__/__index__/
  __float__/__len__/__abs__/__lt__/__ge__/__bool__/__iter__, and exact Fractions with non-int parts; plus extra keys and
  renamed keys of each hashable admitted type on every dict. Paths: every node under event_id, fiscal_period, the
  release source entry, and every pg_ fact row, at every depth (676 paths per Q3 workspace).
- Q3 non-envelope route (release id redirected), 3.12 and 3.14: 45,074 runs each; 43,705 refused, 1,369 raised,
  **0 accepted**. Every raise is B-R10-B1 (frac_num_none 676, frac_num_str 676, frac_num_subint_boomstr 3,
  frac_den_zero 1, frac_den_nan 2 [ValueError/TypeError]) or B-R10-B2 (11 list/dict values at source_span.document_id).
- Q3 envelope route, 3.14: PARTIAL — killed for budget after 315 of 676 paths (through facts[9].source_span.receipt).
  Raises: 658, all B-R10-B1 constructions (frac_num_none 315, frac_num_str 314, frac_num_subint_boomstr 11,
  frac_den_zero 9, frac_den_nan 9 ValueError). Accepted-and-not-JSON-equal: 235 runs, all in fields the validator does
  not read or bind — extra keys in fiscal_period, `Fraction(3)` as fiscal_period.quarter (str() compares "3"=="3"),
  and the release source entry's unread fields — no facts[*] path accepted a non-JSON-equal tamper.
- Every hostile object, every subclass and every non-admitted stdlib type was refused at the entry on every path
  reached: R193's type gate itself holds; the two holes are the Fraction leaf and the pre-isinstance dict lookup.

## B2 — integrity
- `git diff --stat R9HEAD HEAD -- tests/ .github/` : `.github/ci/legacy-jobs.yml | 3 +-`, `tests/test_pg_envelope_f1_probes_r9.py | 278 +`
  (2 files, +280/-1). name-status all: M legacy-jobs.yml, M economic_observations.py, A two reviews/*.md, A R9 suite.
- `git log R9HEAD..HEAD --name-only` (verbatim in b2_git.txt): fdf9bd327177 freeze = R9 suite + legacy-jobs.yml + the
  two round-9 records; dfc26df12f9a (R192) = economic_observations.py only; 6caa2ffc1a95 (R193) = economic_observations.py
  only. Linear: each commit's single parent is the previous; R9HEAD is an ancestor. Seat testimony confirmed.
- legacy-jobs.yml diff: dossier job adds the R9 suite to `paths` and to the run line (26 test files). timeout-minutes: 20.
- Gate run line, venv312_min 3.12.13, in $WT: **2091 passed, 174 skipped, 0 failed, 469 s wall** vs 1200 s timeout.
- `tests/test_ci_pack.py -k curated_exclusive`: 2 passed (3.12), 2 passed (3.14).
- Ten envelope suites (f1 + r1..r9): 3.12: **1267 passed** (442 s); 3.14: **1267 passed** (413 s). R9 suite alone:
  131 passed on each.
- Six release-parser neighbours, /opt/homebrew/bin/python3.12: **287 passed, 2 failed** — the two
  `test_clean_preimport_forged_{stdlib_method,html_helper}_imports_but_parser_fails_closed[cpython-3.12.2-python-org]`,
  the pre-existing pair round 9 recorded at R9HEAD (a cpython-3.12.2 fixture interpreter case; outside this diff, which
  touches only economic_observations.py). Matches the seat's 287/2.
- Final: `git rev-parse HEAD` = 6caa2ffc1a95…, `git status --porcelain` empty.

## B3 — hosted CI (two reads; b3_read1.txt verbatim, b3_read2.txt)
- Read 1 21:40:09Z and read 2 22:11:50Z identical: headRefOid = 6caa2ffc1a954c3d9ce39a8237d3cbc84527b2c5 (= $HEAD),
  isDraft true, mergeStateStatus UNSTABLE (not DIRTY). All 12 ci-pack, ci-gate, ci-plan, contract-delta, fence-pack,
  ci-authority, ci-authority/main, capability-broker, grader-manifest, self-mod-fence: pass. Skipping: trusted-ci and the
  three fork-* guards. Fail: ci-authority/codex/merge-queue-pilot only (N1, out of scope, Sol's call). None pending.

## Non-blocking notes (one line each)
- n-B1: fiscal_period.quarter/year compare by str(), so Fraction(3), "3" or 3 all pass; fields not bound, pre-existing.
- n-B2: extra keys of any admitted hashable type in fiscal_period / the release source entry are accepted (unread).
- n-B3: a hostile `__class__` property at the root of workspace/source_texts is refused, not raised (probed, clean).

## STATUS (group B): REJECT
Two release-blocking bar-(d) findings in R193's class, both reproducing at HEAD on 3.12 and 3.14 and inherited from
R9HEAD: B-R10-B1 (exact Fraction with non-int parts raises in/after the entry walk) and B-R10-B2 (admitted list/dict
as a present row's document_id raises at :767 on the non-envelope route). B0, B2 and B3 are clean.

## Addendum — B1 walk completed for Q1 and Q2 (3.14), after the verdict above
- The background loop kept running after the Q3-envelope kill and finished Q1 and Q2 on both routes (b1_walk_314.log,
  b1_walk_q1q2_summary.txt). All 676 paths each:
  - Q1 envelope: 43,344 refused, 1,413 raised, 234 accepted with a different workspace, 83 accepted JSON-equal.
    Q2 envelope: 43,346 / 1,413 / 234 / 81.
  - Q1 and Q2 non-envelope: 43,705 refused, 1,369 raised, 0 accepted (each).
- Every raise is a B-R10-B1 Fraction-part construction, or on the non-envelope route B-R10-B2's 11 list/dict values
  at facts[*].source_span.document_id. No other raise.
- Every accepted-different run is in fiscal_period (6) or the release source entry (228). None is under facts[*].
- The verdict is unchanged: REJECT on B-R10-B1 and B-R10-B2. The only walk gap left is Q3 envelope, which stopped at
  315 of 676 paths.
