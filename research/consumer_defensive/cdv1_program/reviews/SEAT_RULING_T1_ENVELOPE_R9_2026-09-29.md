# Seat ruling — T1 envelope, audit round 9 (R192–R194)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus acceptance audit of the exact integrated head `11bd3dea8879` (PR #7905), which R191 required. The audit was READ_ONLY and ran as two independent groups, and both returned **REJECT**. The report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R9_2026-09-29.md`, with each group's report verbatim.
- The findings:
  - three blockers: A-R9-B1, B-R9-B1 and B-R9-B2;
  - the non-blocking notes n1, n2 and n3 (group A) and N1, N2 and N3 (group B).
- All three blockers are inherited. Each auditor re-ran its probes on the round-8 head `e6f49ceccb85`, and they fail there the same way. Round 8 did not reach them.
- Two of the three sit inside a class a round-8 ruling claimed to close:
  - A-R9-B1 is R187's class. R187 routed every character reference's digits through one reader, but the validator's span check still read references with a tokenizer that counted bytes.
  - B-R9-B1 is R189's class. R189's walk refused three kinds of value, but it reached them only through the containers it listed, and every other type passed it untouched.
- The operating brief of 2026-09-29 requires a bounded design correction when a class survives, not another literal special case. Sol's direction on the carrier (comment 5894879516) asks for the exact blocking constructions and the smallest ruled repair. So neither class is repaired at the site the audit named:
  - **R192** makes the span check read characters, as the reader does, so no unit can end inside a character;
  - **R193** makes the validator's entry admit a closed set of types by exact type, so no type is left for a later site to meet.
  - B-R9-B2 is closed by R193's closed set, with no repair of its own.
- **R194** disposes of the notes, corrects one probe's premise, freezes the round-9 witness and sets round 10.

## Severity

The bars are the commission's review standard: (a) wrong bind, (b) present fact outside F1-Q, (c) validator acceptance of a tampered workspace, (d) integrity, (e) positional or literal admission, and (f) loose literal parse.

| finding | audit | seat | ruling |
|---|---|---|---|
| A-R9-B1, a named-reference-shaped run of 31 letters and a multi-byte character is cut inside the character by the span check's byte pattern, and decoding the cut raises `UnicodeDecodeError` out of `validate_selected_facts` | BLOCKER (d) (and (c)) | BLOCKER (d); R187's class | R192 |
| B-R9-B1, a value of a type R189's walk did not list (`range`, `slice`, `deque`, `SimpleNamespace`, `UserList`, `UserString`, `PurePosixPath`, an exception) carries a digit run past the limit, a deep nest or a lone surrogate to `str()` or `encode()`, which raise | BLOCKER (d) | BLOCKER (d); R189's class | R193 |
| B-R9-B2, `Decimal("sNaN")` in a receipt's `segment_bytes` or the event ids raises `InvalidOperation` in a comparison of the non-envelope branch | BLOCKER (d) | BLOCKER (d); closed by R193's closed set | R193 |
| n1, n2, n3; N1, N2, N3; the probe premise of `amp_prefix` | notes | disposed of below | R194 |

- **All three blockers are integrity (d).** An exception escaping the validator is not a refusal. That is R176's rule, R183's and R189's.
- None of them binds a wrong value. A-R9-B1 needs a tampered workspace and a relocated receipt, and B-R9-B1 and B-R9-B2 need a tampered workspace. The auditors found no untampered source that reaches them.

## Rulings

- **R192 (A-R9-B1; amends R187). The span check reads characters, as the reader does, and reports each unit at its bytes.**
  - **The class.** `html.unescape` reads a named reference's name as up to 32 characters. The span check's `_PRINT_UNIT` was a bytes pattern, so its `[^\t\n\f <&#;]{1,32}` counted up to 32 bytes. A run of 31 letters and a two-byte character is 32 characters and 33 bytes, so the byte pattern ended inside the character, and `_drops_a_reference` decoded half of it.
    - R187's one reader resolves each reference correctly. The defect is the unit the span check counts in before it asks the reader, so any repair that keeps counting bytes leaves the class open at the next boundary.
  - **The repair.** `_PRINT_UNIT` becomes a `str` pattern, and one helper, `_print_matches`, decodes each byte fragment once, runs the pattern over the characters, and reports each match at the byte offsets its characters encode to.
    - `_printed_units` and `_drops_a_reference` read their units through that helper, so no unit boundary can fall inside a character, and the separator and raw-text sets become `str` sets.
    - The byte interfaces stay: both functions still take bytes, and `_printed_units` still returns byte offsets. The frozen R7 and R8 suites call them that way.
    - A fragment that is not whole characters is refused: "present envelope observation text is not UTF-8 aligned". The public path cannot produce one, because `_validate_envelope_span` refuses a receipt span that is not UTF-8 aligned before it reads the span's text, and every gap it cuts runs from an edge of that span to an ASCII `>` or `<` or to an end of the source.
  - **Rejected.**
    - Catching `UnicodeDecodeError` in `_drops_a_reference` would stop the exception at the one site the audit named while the tokenizer kept counting a different unit from the reader.
    - A UTF-8-aware byte class, a pattern that counts a multi-byte character as one, would be a second grammar of characters written in bytes, beside the reader's own.
  - **Cost.** One decode of the source per call to `_printed_units`, which is cached, and one per gap. No original's units, workspace or admission changes: the six originals' census is identical before and after.

- **R193 (B-R9-B1 and B-R9-B2; amends R189). The validator's entry admits a closed set of types, each by its exact type, and refuses every other value.**
  - **The class.** R189's walk descended `str`, `Rational`, `Mapping` and four container types, and passed every value of any other type without looking at it. The three kinds of value R189 refuses reach the same sites inside a `range`, a `deque`, a path or an exception. B-R9-B2's `Decimal` is the same gap: a `Decimal` is not a `Rational`, so R189 never walked it, and a signalling NaN raises when it is compared.
    - Adding the auditors' types to the walk would be another open list, and the next type the list does not name would reach the same sites. That is the construction R189 replaced, one level down.
  - **The repair.** The walk admits nine types, each by `type(value) is ...`, and refuses every other value, including a subclass of one of the nine, with "workspace holds a value it cannot print: a type it does not admit, ...".
    - The nine are the seven a JSON document parses to (`dict`, `list`, `str`, `int`, `float`, `bool` and `None`), `tuple` and `Fraction`.
    - A `tuple` is admitted because R136 and R176 admit it. R176's frozen control holds a refused row's `missing_fields` as a tuple, which serialises as the list it replays to, and requires the workspace to validate.
    - A `Fraction` is admitted because R134 and R183 read it as a real number. R183's frozen case gives a present row a `Fraction` too large for a float and requires the value check's own refusal, "numeric observation must be finite".
    - The walk descends a `dict`'s keys and values, a `list` and a `tuple`. The three bounds stay: depth 32, 100,000 values, and a numerator or denominator of 641 digits or more. That last bound now reads an `int` or a `Fraction` by exact type instead of any `Rational`.
    - The lone-surrogate check on text stays.
    - `source_texts` must be a `dict` whose keys and values are `str`, by exact type, with no lone surrogate: "source_texts must map document ids to text".
    - **Exact type, not `isinstance`.** A subclass carries its own `__str__`, `__eq__`, `encode` and `get`, so admitting one would admit behaviour the walk cannot bound. A `Mapping` other than a `dict` may return from `get` what its `items` did not yield.
  - **Why these nine.** The seat's first draft admitted only the seven JSON types. Run against the frozen suites, it failed four tests on both interpreters: R176's tuple control in the R6 suite, and R183's fraction case for each of Q1, Q2 and Q3 in the R7 suite. The set is taken from what earlier rulings already admit, not from the JSON grammar alone, and no frozen test changes.
  - **What it refuses that R189 did not.** Every value outside the nine, and every subclass of one of them. Among others: a `set`, a `frozenset`, a `Mapping` that is not a `dict`, a `Decimal`, `bytes`, `complex`, a `range`, a `deque`, a path and an exception. R189 descended the first three and passed the rest unvisited. R193 refuses all of them at the entry, under one message.
  - **What it admits.** Everything the product builds. On the product's own path, `build_event_workspace` under the P&G profile, the six originals' workspaces hold only `dict`, `list`, `str`, `int`, `float`, `bool` and `None`, with `str` keys. Each FY26 workspace also validates after `json.dumps` and `json.loads`. No caller of `validate_selected_facts` exists outside the tests and the demonstration.
  - **Rejected.** Catching `ValueError`, `RecursionError`, `UnicodeEncodeError` and `InvalidOperation` at `str()`, `_fact_id` and the comparisons would be three more site patches, and a fourth type would reach a fifth site.

- **R194 (the notes, the probe premise, the freeze and round 10).**
  - **n1**, an E-suffixed year banner (`2025E`) binds CORE and PCORE. R188 names `2025E` as a year on purpose, and the R8 suite freezes it. Whether a column headed with an estimate year may ever be read as a reported figure is a basis question, not a year-naming one. The seat returns it to Sol as a residual; it is not ruled here, and no admitted release carries such a column.
  - **n2**, `Fiscal 2026` or `FY2026` leaves CORE and PCORE unlocated. That fails closed: a coverage limit, recorded.
  - **n3**, the release parser reads no blocks from a document holding a decimal reference longer than 640 digits. That is R187's stated cost, and it fails closed.
  - **N1**, `ci-authority/codex/merge-queue-pilot` fails on the head. It is not a `ci.yml` pack, and whether it binds is Sol's decision. The seat does not re-run it or code around it.
  - **N2**, round 8's G4 file pins the round-8 head, so its head check fails once the head moves. That is by construction.
  - **N3**, R189's bound read only a `Rational`, and a `Decimal` was never walked. R193 closes it.
  - **The premise of `amp_prefix`.** Group A's direct probe asserted `html.unescape(s) == s` for all four of its cut forms. For `"&amp" + "b" * 28 + "é"` that is false: a reader reads the legacy `&amp` without its semicolon and prints `&`. Under R192 the probe's own engine assertion holds for that form too. The frozen witness asserts what R187's class test requires, for all four: the one reader agrees with `html.unescape`, and the span check reads the run without raising and finds no dropped reference.
  - **Freeze.** `tests/test_pg_envelope_f1_probes_r9.py` holds 131 cases:
    - A's eight findings and their control;
    - B's 57 findings and 30 controls. The seat sharpened two of B's controls without changing their constructions:
      - the untampered control also validates each workspace after `json.dumps` and `json.loads`;
      - the refusal control asserted only that each value is refused. The witness asserts where: R189's own witnesses, a `Decimal`, `complex` and `bytes` at the entry, and a `float` infinity, a `Fraction` and a tuple-keyed `dict`, which are in the set, by the row checks;
    - the seat's 35: R192's sweep over every run of 1 to 40 letters followed by a 2-, 3- or 4-byte character, and a fragment that is not whole characters; R193's six subclasses of admitted types, a workspace that is a `dict` subclass, and four `source_texts` cases.
    - It joins the `earnings-economic-dossier` gate.
  - **Round 10.** One independent READ_ONLY acceptance audit of the exact head that carries R192–R194, judged on release-blocking findings only:
    - R192's class: every unit the span check reads, against the reader, on the public path and on its own functions;
    - R193's class: every input the validator's entry takes;
    - the frozen suites' and fixtures' drift, the gate and the real-release demonstration on that head;
    - hosted CI concluded on that same head.
    - Nits, observations and fail-closed coverage limits are recorded, not ruled. If a blocker falls in R192's or R193's class, the seat corrects the class, not the site.
  - **Hold.** #7905 stays Draft under Sol's HOLD (comment 5894879516; R114). This record asks for no Ready, merge or deployment.
    - After an independent ACCEPT and concluded hosted CI on the same head, the seat returns the candidate to Sol for the hold decision.

## Evidence

Each line names the command or script that produced it. The scratch scripts are the seat's and are not part of the product. "Both interpreters" means Python 3.12.13 with only pytest and pyyaml, as CI runs it, and 3.14.7.

- The group probe files: the auditors' files, run unchanged from a scratch copy of the tree, `python -m pytest -q -p no:cacheprovider <file>`, on both interpreters.
  - With R192 and R193, group B's file: 87 passed. At `11bd3dea8879`: 57 failed, 30 passed.
  - With R192 and R193, group A's file: 86 passed and 1 failed. The failure is `amp_prefix`'s premise assertion, `html.unescape(s) == s`, which stops that case before its engine assertion. The witness runs the engine assertion on the same string, and it holds. At `11bd3dea8879`: 8 failed.
- The R9 witness, `python -m pytest -q -p no:cacheprovider tests/test_pg_envelope_f1_probes_r9.py`, on both interpreters, with each ruling reverted alone in a scratch tree:
  - at `11bd3dea8879`, 106 failed and 25 passed;
  - with R192 alone, 96 failed: every R193 case, and no R192 case;
  - with R193 alone, 10 failed: every R192 case, and no R193 case;
  - with both, 131 passed.
  - The two failing sets are disjoint, and together they are exactly the 106. The 25 that pass at `11bd3dea8879` are A's ASCII control, B's untampered control, R189's own three witnesses, the three admitted values, and a `UserString` in `source_texts`, which R189 already refused; each but the first runs on Q1, Q2 and Q3.
- The six originals' census: admission, each workspace's sha256, the validation outcome and a digest of `_printed_units` over each source text. Identical at `11bd3dea8879` and with the repair, on both interpreters, and identical between them.
- The census of the product's workspace types: every value and key type in the six originals' workspaces, built through `bind_release_document` and `build_event_workspace` under the P&G profile. Only `dict`, `list`, `str`, `int`, `float`, `bool` and `None`, with `str` keys, and `source_texts` a `dict` of `str` to `str`. Each workspace equals its `json.dumps`/`json.loads` round trip and validates after it, on both interpreters.
- No caller of `validate_selected_facts` outside `tests/` and the demonstration: `git grep -n validate_selected_facts -- ':!tests'`.
- The runs below are on the worktree of #7905 with this round's files in place and nothing else changed, before the three commits were cut. The commits reproduce that tree byte for byte, except this record, whose evidence lines were written from these runs.
  - The gate, the `earnings-economic-dossier` job's 26 test files with the R9 witness: 2091 passed and 174 skipped on each interpreter; none failed.
  - `tests/test_ci_pack.py -k curated_exclusive`: 2 passed on each interpreter.
  - The six release-parser neighbours, under `/opt/homebrew/bin/python3.12` with pandas and jsonschema: 287 passed and 2 failed, the same 289 outcomes, test for test, as at `11bd3dea8879`. The two are `test_clean_preimport_forged_html_helper_imports_but_parser_fails_closed` and `test_clean_preimport_forged_stdlib_method_imports_but_parser_fails_closed` for the host's python.org 3.12.2 interpreter, and both fail at `11bd3dea8879` too.
  - The real-release demonstration, the script in `release/T1_REAL_RELEASE_DEMONSTRATION_2026-09-29.md`: on each interpreter, 6 of 6 sources match their `SOURCES.md` pins; Q1, Q2 and Q3 each bind 20 of 20 facts and the validator accepts each workspace; the four refused documents bind none, and the validator accepts their typed absences; 9 of 9 tampered workspaces are refused; 0 failures. The two interpreters' JSON outputs are identical.
  - Frozen drift: `git diff --name-status 11bd3dea8879 -- tests/` is empty: no suite or fixture under `tests/` changed. The R9 witness is the one new file there.
