# Seat ruling — T1 envelope, audit round 8 (R187–R191)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus re-audit of the round-7 repair at `e6f49ceccb85` (PR #7905), which R186 required. The audit was READ_ONLY and ran as four independent groups, and all four returned **REJECT**. The report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R8_2026-09-28.md`, with each group's report verbatim.
- The findings:
  - five blockers: G1-R8-B1, G2-R8-B1, G2-R8-B2, G3-R8-B1 and G4-R8-B1;
  - the nit G1-R8-n1, the coverage note G3-R8-c1, and the observations G1-R8-O1 and O-R8-1;
  - G4-O1, re-examined, which stands; and the hosted-CI gap at `e6f49ceccb85`.
- The seat found one more blocker of its own. S-R8-1: a release body holding a lone surrogate makes `bind_release_document` raise `UnicodeEncodeError` when it encodes the body to hash it. The seat found it while tracing where G2-R8-B2's surrogate is encoded (R189).
- Every round-7 blocker is closed on its construction and on the audit's variants:
  - G1-B1, G1-B2, G1-m1 and S-R7-3 (G1);
  - G2-B3, G2-B4, G2-B5, G2-m2 and S-R7-1 (G2);
  - G3-R7-B1 and G3-R7-m1 (G3);
  - G4-B1 and G4-m1 (G4), and S-R7-2 (G1).
- Three of this round's blockers are round-7 classes that survived at sites the round-7 repair did not reach:
  - G1-R8-B1 is S-R7-3's class. R181 bounded the digits the release parser converts in a span. But `html.unescape` converts a character reference's digits whole at ten sites in three modules, and so does the stdlib `HTMLParser` under the release parser.
  - G4-R8-B1 and G2-R8-B2 are R183's class. R183 refused the fields and kinds of value its findings named, and round 8 found three more fields and two more kinds.
  - G3-R8-B1 is R179's class. R179 listed the marks that make a `20dd` a figure, and round 8 found letters and words the list did not name.
- This round's brief requires a design correction for a class that survives, not another literal special case. It is the Chairman's operating brief of 2026-09-29, and Sol's direction on the carrier (comment 5894879516) bars an unbounded synonym or grammar accumulation loop. So none of the three is repaired at the site the audit named:
  - **R187** routes every character reference the engine reads through one reader, which cannot raise;
  - **R188** replaces R179's open list of figure marks with a closed word grammar: a year is named only where the grammar names one, and everything else is a figure, so the list can no longer grow;
  - **R189** replaces field-by-field guards with one walk at the validator's entry, bounding every value the validator prints or encodes.
  - G2-R8-B1 is a new class. **R190** follows the tree builder's own rule for end tags rather than listing tag contexts.
- The seat re-ran each group's probe file at `e6f49ceccb85` and with the repair, on Python 3.12.13 (with only pytest and pyyaml) and 3.14.7.

  | group | cases | at `e6f49ceccb85` | with the repair |
  |---|---|---|---|
  | G1 | 701 | 23 failed, 678 passed, on both | 15 failed, 686 passed, on both; accounted for below |
  | G2 | 78 | 33 failed, 45 passed, on both: G2-R8-B1's 24 and G2-R8-B2's 9 | 78 passed, on both |
  | G3 | 315 | 54 failed, 251 passed and 10 skipped, on both: G3-R8-B1's 54 | 305 passed and 10 skipped, on both |
  | G4 | 167; the file's nine integrity cases read the audited worktree's git state and do not run on a copy | 9 failed, 149 passed, on both: G4-R8-B1's 9 | 158 passed, on both |

  - G1's 23 failures at `e6f49ceccb85` are G1-R8-B1's 21 (15 on the public path, 3 at admission, 3 in the validator) and G1-R8-n1's 2 linearity probes.
  - With the repair, 15 remain. All are `test_g1_r8_B1_a_long_decimal_reference_never_raises_on_the_public_path`, G1's five placements on Q1–Q3.
    - The probe states its expectation as "refuses or builds, never raises; the workspace validates". The build no longer raises, which is the finding.
    - Each fails on the probe's first assertion, that no value binds around the reference: `assert not {m for m, v in r1.numeric(ws).items() if isinstance(v, float)}`.
    - R187 reads the reference as a reader does: `&#0…049;` prints `1`. The document is the page a reader sees, and its values bind.
    - The R8 suite runs the same five placements and pins that outcome. Every value binds its frozen value, except the pinned cell's, and the workspace validates.
    - The first assertion encodes a refusal design, which R187 rejects.

- The audit confirmed the positive work:
  - G1's family 16 compared the engine's character tests code point by code point on 3.11 (Unicode 14.0), 3.12 (15.0) and 3.14 (16.0), over all 1,112,064 code points outside the surrogates. The digests are identical.
  - G1 wrapped `build_event_workspace` while the eight frozen suites ran (971 passed in each run). Against html5lib 1.1 it found:
    - 0 exceptions and 1,073 documents admitted;
    - 0 grid, title or receipt divergences;
    - 23 note divergences, all fail-closed: the engine leaves the note absent where a reader prints it.
  - G2's families:
    - 95,252 tampers on 3.14 over Q1–Q3 and five row kinds. 140 were accepted, all JSON-invisible (R176); 108 raised, every one of them G2-R8-B2.
    - 4,124 shift and relocation runs, with 0 exceptions. None of 429 one-byte shifts, widenings and narrowings was accepted.
    - 6,633 fuzz documents and 65,169 present rows on both interpreters, with 0 exceptions and 0 divergences.
  - G3's sweeps:
    - 8,462 rows of pointer forms, with 0 wrong binds;
    - 3,232 unit-rule cases, with no real finding;
    - 331 banners that name the title's own year, another year or two years, with 0 wrong judgements.
  - G4's integrity checks hold:
    - the eight frozen suites pass on 3.12 and 3.14 (971);
    - `test_pg_envelope_f1.py`, the `_r1` to `_r4` and `_r6` suites and the fixtures are byte-identical;
    - the seven round-7 mutations G4 re-ran are all still killed;
    - reverted alone, R179's title hunk fails 0 of 272 cases, as R179 said.
- Hosted CI at `e6f49ceccb85`: there is none to read.
  - The PR conflicts with `main` in `.github/ci/legacy-jobs.yml`, and GitHub creates no `pull_request` run for a conflicted PR. So only `ci-authority` ran at that head, and no ci-pack or `ci-gate` conclusion exists (G4, family 12).
  - This candidate merges `origin/main` and resolves that file (R191), so ci.yml and fences.yml run on the integrated head.

This record amends R116–R186 only where it says so. Everything else there stands.
- One frozen file changes. `tests/test_pg_envelope_f1_probes_r7.py` drops `("2025x", [2025])` and `("No. 2025", [2025])` from R179's table of values that name their years. A comment names where they moved. R188 reads no year in either, and nothing else in that file changes.
- `SEAT_RULING_T1_ENVELOPE_R7_2026-09-28.md` carries an at-source mark under R179's grammar, pointing here.
- `tests/test_pg_envelope_f1.py`, the `_r1` to `_r6` suites and `tests/fixtures/pg_envelope/` stay byte-identical.
- The new frozen suite `tests/test_pg_envelope_f1_probes_r8.py` enforces the rulings below, and the gate job `earnings-economic-dossier` runs it (R191).
- The seat grounded every factual premise below in its own runs on the six originals, in memory, on both interpreters. No finding is ruled on the audit's word alone.

## Severity

The bars are the commission's review standard: (a) wrong bind, (b) present fact outside F1-Q, (c) validator acceptance of a tampered workspace, (d) integrity, and (e) positional or literal admission.

| finding | audit | seat | ruling |
|---|---|---|---|
| G1-R8-B1, a decimal reference past the interpreter's digit limit raises `ValueError` in the release parser, at admission and in the validator | BLOCKER (d) | BLOCKER; S-R7-3's class, at every reader of references | R187 |
| G3-R8-B1, a year glued to a letter (`2026M`, `x2026`) or beside a mark R179 did not list (`A-2026`) is named, and CORE and PCORE bind under it | BLOCKER (e) | BLOCKER, on Q1–Q3; R179's class | R188 |
| G1-R8-n1, `_named_years` re-scans the value for each year, which is quadratic in the value's year count | nit | repaired by R188's single pass | R188 |
| G4-R8-B1, a period, a fiscal-period field or an absence subject too long or nested too deep to print raises in `str()` | BLOCKER (c/d), inherited | BLOCKER (d); R183's class | R189 |
| G2-R8-B2, a lone surrogate in the `event_id` or a present row's period raises `UnicodeEncodeError` | BLOCKER (d) | BLOCKER (d); R183's class | R189 |
| S-R8-1 (seat), a release body holding a lone surrogate raises in `bind_release_document` | — | BLOCKER (d) | R189 |
| G2-R8-B1, an end tag a tree builder ignores sets a token off, so a literal glued to printed text is accepted through R143's seam | BLOCKER (c) | BLOCKER (c) | R190 |
| G3-R8-c1; G1-R8-O1 and O-R8-1; G4-O1; the hosted-CI gap | coverage; observations; gap | disposed of below | R191 |

- **G1-R8-B1, G4-R8-B1, G2-R8-B2 and S-R8-1 are integrity (d).** An exception escaping the build or the validator is not a refusal. That is R176's rule for G2-B2, and R183's.
- **G3-R8-B1 is (e).** A pin binds to a year no reader reads, which R147's positional rule forbids.
- **G2-R8-B1 is (c).** The validator accepts a relocated literal whose printed token is not the value: a reader prints `-1.63`, and the check read `1.63`. That breaks R174's rule.

## Rulings

- **R187 (G1-R8-B1; amends R181 and R185). Every character reference the engine reads goes through one reader, which cannot raise.**
  - **The class.** Python converts a decimal reference's digits with `int()`. That refuses a run longer than the interpreter's integer string-conversion limit, which is 4,300 digits by default and may be set as low as 640. So whether a document raised depended on the process, not on the document.
    - R181 bounded the one conversion S-R7-3 named, the release parser's reading of a span.
    - The same conversion ran in `html.unescape`, which the engine called at ten sites, and in the stdlib `HTMLParser` that the release parser builds on.
  - **The reader.** `receipts.unescape` reads each decimal reference at its limit, then lets `html.unescape` resolve it.
    - Leading zeros carry no value and are dropped.
    - A run of more than seven significant digits is past U+10FFFF, and every value there resolves to U+FFFD. So the run is read as 1114112 (0x110000), which resolves exactly as the full value did.
    - Hexadecimal references convert without a limit and are left alone.
    - So the reader returns what `html.unescape` returns wherever `html.unescape` returns at all, and it never raises.
  - **Every site reads through it:**
    - `receipts.visible_text`;
    - the envelope's reference tokens and its unassigned-character check at admission (`pg_envelope.py`, two sites);
    - the span check's seven readings of printed text (`economic_observations.py`).

    The `html` import is removed from both modules.
  - **The release parser.** `disclosure_diff.py` reads blocks with the stdlib `HTMLParser`. That parser converts a reference in an attribute value itself, with an unbounded `int()`, before any engine code sees the text.
    - So the parser reads no blocks at all from a source holding a decimal reference longer than 640 digits, the least limit an interpreter may set. It does not guess at a partial reading.
    - A shorter reference converts under every limit.
  - **Rejected: refusing the document.** G1's probe expects the public path to leave every value unlocated around such a reference.
    - A reader prints the reference as one character, so the document is the page the reader sees. Refusing it would be another refusal keyed to one written form.
    - The reader instead removes the conversion everywhere the engine reads a reference, so a document reads the same under every interpreter limit.
  - **The witnesses (55), on Q1–Q3:**
    - **Placements (15).** A 4,302-digit reference to `1` sits in text, a comment, a script, an attribute, or at the start of the pinned cell.
      - At `e6f49ceccb85`, `ValueError` escaped `build_event_workspace`.
      - Now the document is admitted and every value binds as before. The exception is the pinned cell's value: it prints `1` glued to its literal and is refused. The workspace validates.
    - **A changed source (3).** The extractor's own workspace is validated against a source that also carries the reference in a comment.
      - At `e6f49ceccb85`, `ValueError` escaped the validator.
      - Now the workspace is refused: the source is not the one its receipts were minted against.
    - **The validator's own reading (18).** A 4,302-digit reference spells the literal's first digit, or prints a space before or after it. This covers reported sales growth and diluted EPS.
      - With only the envelope's sites repaired, `ValueError` escaped the span check.
      - Now every value binds as before and validates.
    - **The reader itself (19).** It agrees with `html.unescape` on 14 forms, and reads 5 long forms without converting their digits.
      - These cases call `receipts.unescape`, which `e6f49ceccb85` lacks, so they fail there by construction. They pin the reader.
  - **By hunk:**

    | reverted alone | cases failed | notes |
    |---|---|---|
    | the release parser's guard | 27 | |
    | the envelope's two sites | 36 | includes the parser guard's 27 |
    | the validator's seven sites | 18 | the spelled literals; each also fails under the other two reverts |
  - **Equivalence.** `receipts.unescape` returns exactly what `html.unescape` returns over 200,204 strings, on 3.12 and 3.14:
    - 200,000 random strings of up to 14 fragments of reference syntax;
    - 204 boundary forms around 0x10FFFF, the surrogates and zero padding.
  - **The cost.** The release parser reads no blocks from a source holding a decimal reference longer than 640 digits. Every document `html.unescape` could read reads exactly as before.

- **R188 (G3-R8-B1, G1-R8-n1; amends R179). A header value is read as words, and a year is named only where the word grammar names one.**
  - **The class.** R179 named a `20dd` unless a listed mark touched it: a sign, a bracket, a point or a percent. It allowed any letter or digit on either side, so that `FY2026` and `2026E` stayed years.
    - The list was open. Some forms were none of the listed figures:
      - a letter glued to the year: `2026M`, `2026k`, `2026B`, `2025x`, `x2026`;
      - a word or mark beside it: `A-2026`, `2026-A`, `No. 2025`.
    - So the year was named and a pin under it bound. G3 bound CORE and PCORE on Q1–Q3 this way.
  - **The correction inverts the rule.** The value is split into words and single marks; a word is a run of ASCII letters and digits with an optional trailing point. Then:
    - A year word is `20dd`, optionally prefixed `FY` or `CY` and optionally suffixed `E`. No other word holding those digits is a year.
    - A run of year words joined by `,`, `/`, `-` or `and` is read whole.
    - The run names its years only if both of these hold:
      - it opens the value, or it follows a period word: a month or its abbreviation, with or without a point, or `Fiscal`, `Year`, `Calendar`, `FY` or `CY`;
      - it ends the value, or it follows a period word and is followed past a space by another word (`Fiscal 2025 Results`).
    - Every other `20dd` stays in the rest of the value, and a numeric character there makes the years unreadable (R170, R178).
    - So a form no one has tried yet leaves its pin unlocated rather than bound. The accepted forms are a closed set.
  - **One pass.** Each word is read once, so the reading is linear in the value's length. G1-R8-n1's two linearity probes pass.
  - **The witnesses (65):**
    - **Through the public path (54).** This is R179's construction: the title's year is removed and a banner runs across the table. The banner prints the year in each of G3's nine forms: `2026M`, `2026m`, `2026k`, `2026K`, `2026B`, `2026x`, `x2026`, `A-2026` and `2026-A`.
      - The cases cover CORE and PCORE, on Q1–Q3.
      - Each bound at `e6f49ceccb85`. Now each is unlocated.
    - **The grammar (11).** The nine forms name no year, and neither do `2025x` and `No. 2025`.
  - **The controls** are R179's, in the R7 suite:
    - the same banner printing the plain year binds CORE and PCORE (6);
    - thirteen values still name exactly their years, among them `2025 (1)`, `(1) 2025`, `Fiscal 2025`, `2025 and 2026`, `CY2025`, `2025E` and `Sept. 2025`.
  - **The cost:**
    - `2025x` and `No. 2025` named their year under R179 and name none now. They leave R179's table in the R7 suite, which is this round's one amendment to a frozen file.
    - On the six originals, one header value changes. It is FY26 Q1's cell 15:3:12, which begins `2017 U.S. Tax Act Payments`. Its years read [2017, 2025] and now read none.
    - The six workspaces' sha256 are unchanged, so no pin read under that cell. Admission is unchanged too, on both interpreters (the census, R191).

- **R189 (G4-R8-B1, G2-R8-B2, S-R8-1; amends R183). The validator refuses, at its entry, every value it could not print or encode.**
  - **The class.** The validator prints and encodes what a workspace carries: `str()` of its fields, the fact identity's bytes, and the replay's event identity.
    - R183 refused the fields and kinds of value its findings named:
      - a float past its range;
      - an `event_id` that is not a string;
      - `sources` that are not a list;
      - nesting past the interpreter;
      - a period that is a list or a mapping.
    - Round 8 found more:
      - an integer past the digit limit as a present row's period, which raises in the fact identity (`_fact_id`), or as the fiscal period's quarter or year (G4);
      - nesting 100,000 deep in the fiscal period or in a typed absence's subject, which raises `RecursionError` in `str()` (G4);
      - a lone surrogate as the `event_id` or as a present row's period, which raises `UnicodeEncodeError` where the identity is encoded (G2);
      - a release body holding a lone surrogate, which raises when `bind_release_document` encodes it to hash it (S-R8-1).
    - G4 classes its three forms as inherited from before this PR.
  - **The correction is one walk, not three more fields.** `_unprintable` visits the workspace iteratively, so it cannot recurse itself. It refuses the workspace when any of these holds:
    - nesting passes depth 32, or the workspace holds more than 100,000 values;
    - an integer or a fraction has a numerator or denominator of 10^640 or more. 640 digits is the least limit an interpreter may set, so anything smaller prints under every limit;
    - text holds a lone surrogate, which no bytes decode to.

    After the walk, nothing the validator prints or encodes can meet any of the three.
    - `source_texts` keys and values holding a lone surrogate are refused along with the other malformed sources.
    - `bind_release_document` refuses a body holding one, along with the other bodies that are not text.
  - **Against the real workspaces.** Each of FY26 Q1–Q3's workspaces nests 6 deep and holds 1,699 values. Its largest integer is at most 308,066. The limits are 32 and 100,000.
  - **The witnesses (27):**

    | witness | cases |
    |---|---|
    | a present row's period of 10^5000, Q1–Q3 | 3 |
    | the fiscal quarter or year, 10^5000 or nested 100,000 deep, Q3 | 4 |
    | a typed absence's subject nested 100,000 deep, Q1 and Q3 | 2 |
    | an integer past the least limit, under a limit of 640, Q1–Q3 | 3 |
    | a lone surrogate as the `event_id` or a present row's period, Q1–Q3 | 6 |
    | a lone surrogate in a source text, Q1–Q3 | 3 |
    | a release body holding a lone surrogate in a comment or in text, Q1–Q3 | 6 |

    Each raised at `e6f49ceccb85` and is now refused.
  - **The controls (6).** A number just under the least limit is left to the row checks (3). A character past the basic plane is text, not a surrogate (3).
  - **By hunk.** Reverted alone:
    - the walk fails 18 cases;
    - the source-text check fails 3;
    - the binding's check fails 6.
  - **The cost.** A workspace nested past depth 32 or holding more than 100,000 values is refused even where it would print. The real workspaces sit far inside both limits.

- **R190 (G2-R8-B1; amends R174). An end tag sets a token off only where a tree builder acts on it whatever else is open.**
  - **The finding.** The span check counted each `td`, `th`, `tr`, `table`, `p`, `div` and `br` tag as a separator, start or end.
    - An HTML5 tree builder ignores an end tag whose element is not open. So `<p>-</div>1.63</p>` prints `-1.63` as one run, while the check read `1.63` as a whole token.
    - With a receipt reseated there, the workspace was accepted through R143's seam (G2, 24 cases).
  - **The correction** follows the builder's rule without a second parse:
    - A start tag in the set still separates. It always opens its element, and admission already refuses the table start tags a builder would drop.
    - An end tag separates only if it is one of two:
      - `</p>`, which a builder reads as an empty paragraph when none is open;
      - `</br>`, which a builder reads as `<br>`.
    - Every other end tag is markup, so the text on either side of it is one run.
  - **Rejected: tracking which elements are open.** That needs a tree builder in the validator, a second reading of the document, which R176 rejected.
  - **The witnesses (9):**
    - The Q3 diluted-EPS receipt, reseated onto `1.63` with an ignored end tag beside it, is refused (8). The tags are `</div>`, `</td>`, `</th>`, `</tr>` and `</table>`, after a minus or a letter, before a letter, and in upper case with a space.
    - The separator set is pinned (1).
  - **The controls (5).** Each boundary still sets the literal off, and the relocation is accepted, inside R176's rule:
    - two paragraphs;
    - `<br>` and `</br>`;
    - `</p>` with no paragraph open;
    - a line feed after a closing `div`.
  - **The cost.** An end tag that closes an open element no longer separates on its own. So `<div>-</div>1.63` reads `-1.63` and is refused. On the six originals:
    - 0 of 7,703 digit runs in printed text change their whole-token verdict, on 3.12 and 3.14;
    - 2,143 are whole tokens under both rules, so no selected span moves;
    - the six workspaces' sha256 are unchanged (the census).

- **R191 (the round-8 freeze, the gate, the integration, the repair, the witness, the dispositions, the R9 audit and the hold).**
  - **The freeze.** `tests/test_pg_envelope_f1_probes_r8.py` holds 167 cases, all authored by the seat.
    - They come from the audit's findings, widened by the seat to each rule's controls, and from its own finding S-R8-1.
    - By ruling: R187 has 55, R188 65, R189 33 (6 of them controls) and R190 14 (5 of them controls).
    - At `e6f49ceccb85`, 156 fail and the 11 controls pass, on 3.12 and 3.14. Each of the 156 fails for its finding's reason, or, for R187's reader cases, by construction.
  - **The R7 amendment.** Two values leave R179's table, as R188 records.
    - The R7 suite now holds 270 cases.
    - The nine envelope suites with the repair pass 1,136 cases, on 3.12 and 3.14: the R8 suite's 167 plus the 971 before it, less the two moved cases.
  - **The gate.** The `earnings-economic-dossier` job in `.github/ci/legacy-jobs.yml` adds the suite to its paths and to its run line. Its `timeout-minutes` rises from 15 to 20.
    - The CI runner holds each logical job to its own `timeout-minutes`, dependency install included.
    - The job's last hosted run, at `b6808dfcc166`, took 416.30 s for the files it then held. The same files take 341.4 s locally, a factor of 1.22.
    - The whole line, with the R7 and R8 suites, takes 529 s locally on 3.12, so about 645 s hosted. That leaves 28% of 15 minutes, and 46% of 20.
  - **The integration.** `main` had moved 855 commits past the PR's merge base `8a8ecbe868ff`, to `942956ea69f6`.
    - The only conflict is `.github/ci/legacy-jobs.yml`. Both sides inserted a job at the same point, and git split the two insertions into three hunks along their shared lines.
    - The seat merged `origin/main` into the branch. It resolved the file by taking main's side of every hunk and inserting this PR's own job, `earnings-economic-dossier`, whole after main's. The result is main's file plus exactly the PR's 85 added lines, and no line of main's is removed.
    - On the merged tree, only the PR's 92 files differ from `main`. The 90 that `main` did not touch are byte-identical to the PR head. `tests/test_ci_pack.py` auto-merged as main's file plus the PR's one line.
    - The resolution is its own merge commit, before the round-8 commits, so the audit reads the repair against the current base.
    - The merged tree failed one of `main`'s own checks, `test_curated_exclusive_scopes_cover_their_own_import_closure`, on 3.12 and 3.14.
      - `industrials-result-cash`, a job the merge brought, names `issuer_profiles.py` in its paths. On this branch that module imports `pg_profile.py` (line 1308), which imports `pg_envelope.py`.
      - One commit after the merge adds those two modules to the job's paths, as the PR already does for three other jobs. The job then runs on more edits, never fewer.
  - **The repair.** The rulings fix the code to the line, so the seat writes it itself, one commit per ruling:
    - R187 touches `engine/earnings_release/receipts.py`, `engine/company_intelligence/pg_envelope.py`, `engine/company_intelligence/economic_observations.py` and `engine/fundamental_forensics/disclosure_diff.py`;
    - R188 touches `pg_envelope.py`;
    - R189 touches `economic_observations.py` and `engine/earnings_release/binding.py`;
    - R190 touches `economic_observations.py`.
  - **The witness.** Each ruling is load-bearing in the frozen suite.
    - The seat reverted one ruling at a time in scratch copies, never in the worktree, and ran the R8 suite on 3.12 and 3.14.
    - With nothing reverted, all 167 cases pass on both.

    | reverted | R8 cases failed on 3.12 | on 3.14 |
    |---|---|---|
    | R187 | 55 | 55 |
    | R188 | 65 | 65 |
    | R189 | 27 | 27 |
    | R190 | 9 | 9 |

    - The four sets are disjoint. Together they are the 156 witnesses that fail at `e6f49ceccb85`.
    - No control fails in any run.
    - The per-hunk splits are under each ruling above.
  - **The census.** On the six originals, on 3.12 and on 3.14, admission and each workspace's sha256 are byte-identical to the census at `e6f49ceccb85`. The header years over every printed cell differ in one value only: R188's cost above.
  - **The neighbouring suites.** The seat ran six suites in scratch copies, at `e6f49ceccb85` and with the repair: disclosure diff, release binding, event workspace, refresh, capital-structure terms and the a5a issuer profiles.
    - They gave 289 outcomes, identical test by test.
    - 16 fail in both copies for reasons of the scratch copy: checks that read the workflow files, or that pin particular CPython builds.
    - The integrated worktree's own results are in the evidence below.
  - **The real-release demonstration.** `release/T1_REAL_RELEASE_DEMONSTRATION_2026-09-29.md` runs P&G's own EDGAR exhibits through the product path, on the integrated head:
    - Admitted: each value against the independent oracle and against the bytes at its receipt's span.
    - Refused: every refused document and every tampered workspace.

    It gives the same output at `e6f49ceccb85`, so the repair changes nothing on a real release.
  - **G3-R8-c1 (coverage).** A word-bearing year banner over the core reconciliation leaves CORE and PCORE unlocated, even though R188 names the year. Examples are `FY2026`, `Fiscal 2026`, `Sept. 2026`, `March 2026` and `CY2026`.
    - The table's signature refuses the banner row, not the grammar.
    - It is fail-closed, and P&G prints no such banner.
    - G3's other note is also fail-closed and outside F1-Q's P&G layout: `Q3 2026`, `3Q 2026`, `Sept. 30, 2026` and `June 30 2026` in a header value are unreadable, so a pin under them is unlocated.
    - Both are recorded as coverage limits for later issuers. No change.
  - **G1-R8-O1 (observation).** Two character tests in the span check read White_Space from the interpreter's Unicode database, which a later Unicode version could move.
    - Family 16's digests are identical on 3.11, 3.12 and 3.14 over every code point.
    - R178 names the class, and no installed interpreter reaches it.
    - No change.
  - **O-R8-1 (observation).** G4 is right about R179's 76 witnesses. 28 of them call `_named_years` directly, fail at the older base only by `AttributeError`, and would stay green if `_header_years` stopped calling the helper. R179's record already said they "fail there by construction".
    - R188 is witnessed through the public path as well.
    - Its 54 banner cases fail at `e6f49ceccb85` by binding, not by a missing name, and so do its 11 grammar cases.
  - **G4-O1 stands.** The witness oracle `witness_outcome` reads only a cell's starting row, and reads the note by plain containment.
    - No frozen case feeds it an R168 or R180 document, so no frozen case moves.
    - No change.
  - **The hosted-CI gap.** A conflicting pull request gets no `pull_request` runs of `ci.yml` or `fences.yml`; at `e6f49ceccb85` only ci-authority ran. The integration removes that cause.
    - Whether the hosted checks ran and concluded on the integrated head is evidence for the round-8 return, not for this record.
  - **The R9 audit.** Sol's direction (comment 5894879516) and the Chairman's brief bound the next round.
    - It is one independent READ_ONLY acceptance audit of the exact integrated head, the round-8 repair merged with `origin/main`.
    - It judges the five bars on release-blocking findings only: wrong binds, crashes, integrity and authority defects. Nits, observations and fail-closed coverage limits are recorded, not ruled.
    - It confirms:
      - that the frozen suites and fixtures did not drift;
      - that the merge carried main's changes to `.github/ci/legacy-jobs.yml` intact;
      - that hosted CI concluded on that same head.
    - If a round-9 blocker falls in a class R187–R190 corrected, the seat corrects the class, not the site.
  - **Hold.** #7905 stays Draft under Sol's HOLD (comment 5894879516; R114). This record asks for no Ready, merge or deployment.
    - After an independent ACCEPT and concluded hosted CI on the same head, the seat returns the candidate to Sol for the hold decision.

## Evidence

Each line names the command or script that produced it. The scratch scripts are the seat's and are not part of the product.

- The group probe files: the auditors' files, run unchanged from a scratch copy on each tree, `python -m pytest -q -p no:cacheprovider <file>`, on 3.12.13 and 3.14.7.
- The R8 suite and its reverts: `python -m pytest -q -p no:cacheprovider -rf tests/test_pg_envelope_f1_probes_r8.py`, on the repaired tree, on `e6f49ceccb85`, and on eleven scratch trees. Each scratch tree reverts one ruling or one hunk.
- The reader's equivalence: 200,000 random strings seeded 187, plus 204 boundary forms, compared with `html.unescape`. The result was `checked 200204 mismatches 0` on both interpreters.
- The census: admission, each workspace's sha256 and the header years over every printed cell, for the six originals, on each tree and interpreter.
- R190's cost: every digit run in every text unit of the six originals, with its whole-token verdict under both separator sets, and the selected rows' spans.
- The real workspaces' shape: an iterative walk counting depth, values and the largest integer.
- The gate line, on the integrated tree the round-8 commits carry: its 25 files, `python -m pytest -q -p no:cacheprovider`.
  - On 3.12.13, 1,960 passed and 174 skipped in 532 s. On 3.14.7, the same in 484 s.
  - No case failed, and the nine envelope suites hold 1,136 of the cases.
- `tests/test_ci_pack.py -k curated_exclusive`, on 3.12.13 and 3.14.7: on the merge commit's own tree, 1 failed and 1 passed on each interpreter, and the failure names only `industrials-result-cash` with `pg_envelope.py` and `pg_profile.py`. With the integration commit, 2 passed on 3.14.7, and the whole of `tests/test_ci_pack.py` gives 143 passed and 2 skipped on 3.12.13. The job's own two test files, `tests/test_industrials_dependency_binding.py` and `tests/test_industrials_result_cash.py`, pass 119 cases on 3.12.
- The six neighbouring suites, in the integrated worktree: 289 outcomes, identical test by test to G4's run in its worktree at `e6f49ceccb85`. 287 pass, and the same two fail in both: the two `test_clean_preimport_forged_*` cases of `tests/test_capital_structure_document_terms.py` parametrized on `cpython-3.12.2-python-org`.
- The real-release demonstration, on the integrated head: `release/T1_REAL_RELEASE_DEMONSTRATION_2026-09-29.md`.
