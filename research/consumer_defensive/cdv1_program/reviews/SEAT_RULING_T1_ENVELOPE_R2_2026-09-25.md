# Seat ruling — T1 envelope, audit round 2 (R132–R142)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus re-audit of the repaired envelope at `5add1e2eefc` (PR #7905). The audit was READ_ONLY and its verdict was **REJECT**. The full report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R2_2026-09-25.md`.
- It ran 68 probes and 42 failed. The seat re-ran the probe file at `5add1e2eefc` and reproduced 42 failed, 26 passed.
- The findings:
  - blockers by letter: B1–B9;
  - two findings left to the seat's severity ruling: B10 and B11;
  - M1 (minor) and M2 (major);
  - code-quality notes.
- The audit confirmed the positive work:
  - All thirteen round-1 findings are closed. The round-1 probe file now gives 4 failed, 99 passed: three are the probe artefacts round 1 already named, and the fourth is a white-box control that corroborates B2.
  - Both frozen suites are green on Python 3.12 and 3.14: 46 and 125 passed.
  - The gate line gives 995 passed and 174 skipped, and `curated_exclusive` passes.
  - The a5a and capital-structure suites match the `f8e4af5aa4c` baseline test by test (213 passed).
  - No absence reason was minted, and the runtime imports only the standard library and engine modules.

This record amends R116–R131 only where it says so. Everything else there stands.
- `tests/test_pg_envelope_f1.py`, `tests/test_pg_envelope_f1_probes_r1.py` and `tests/fixtures/pg_envelope/` stay byte-identical.
- The rulings below are enforced by the new frozen suite `tests/test_pg_envelope_f1_probes_r2.py` (R142).
- The seat grounded every factual premise below in its own census of the three F1-Q originals, run in memory with the engine's reader.

## Rulings

- **R132 (a title names exactly the pin's period; B1, B3).** This amends R124's two form tests.
  - **Month/day form.** "Three Months Ended <Month> <D>[, <YYYY>]" names the pin's period only when:
    - its month and its day are the period end's;
    - its year is the period end's. The year comes from the title when printed, and otherwise from a year column header over the cell. A growth column is still compared on month and day only.
  - B3 was a missed comparison: the day was never compared when the year was printed.
  - **Range form.** "<Month> - <Month> <YYYY>" names the pin's period only when:
    - its end month and year are the period end's;
    - its start month is the first month of that three-month quarter, two months before the end month. In the originals that gives July–September, October–December and January–March.
  - Other ranges name another period:
    - a year-to-date or six-month range, such as "July - March 2026", "October - March 2026", "July - December 2025" or "April - September 2025";
    - a start word that is not a month, such as "Foo - March 2026".
  - R124's range test named only the end month and year. That gap was the seat's, and this ruling closes it.
  - **Failure.** The outcome is unchanged: the metric is `envelope_unlocated` (R117).

- **R133 (the duration word is part of the title; B2).**
  - **Folding.** R125 already keeps the duration word, and the build folded it away (`pg_envelope.py:113-118`).
    - Both title forms keep it, with or without a printed year.
    - A six-, nine- or twelve-month title never folds to the token of a three-month title.
    - No pinned role's vocabulary carries a duration word other than "three".
  - **Governance.** Every period title over a cell governs it, whether it names the pin's period, another period, or none.
    - A period title is any text that contains the whole word "ended" (case-insensitive), or that has the range shape "<word> - <word> <YYYY>".
    - The table's other titles are consulted only when no period title sits over the cell (R124's fallback). The fallback collects period titles by the same definition.
    - A "Nine Months Ended …" title over the earnings EPS cells therefore cannot be bypassed by a "Three Months Ended …" title moved to another row.
    - The frozen control still binds: when the table's only title is moved to a bottom row, it still governs.
  - **Census of the period titles** in the three originals. These are the only texts in any of their tables that contain "ended" or have the range shape.

    | role | FY26 Q1 | FY26 Q2 | FY26 Q3 |
    |---|---|---|---|
    | segment drivers, organic reconciliation (label column) | July - September 2025 | October - December 2025 | January - March 2026 |
    | earnings (year in the column header) | Three Months Ended September 30 | Three Months Ended December 31 | Three Months Ended March 31 |
    | drivers, segment results, cash flow, cash-flow reconciliation | Three Months Ended September 30, 2025 | Three Months Ended December 31, 2025 | Three Months Ended March 31, 2026 |
    | core reconciliation | current-quarter title | current title, plus the year-ago title over the year-ago columns | current title, plus the year-ago title over the year-ago columns |
    | prior-core reconciliation (FQ1 only) | Three Months Ended September 30, 2024 | — | — |
    | cash flows (known, unread) | Three Months Ended September 30 | Six Months Ended December 31 | Nine Months Ended March 31 |

    The cash-flow statements' six- and nine-month tokens are census, so that role's vocabulary carries them.

- **R134 (no exception inside the envelope; B8).** R122 already says that an exception inside the envelope is a defect.
  - **Title reading compares components; it never builds a date from title text.**
    - The month word is looked up by exact membership in the twelve English month names, through a mapping, never `list.index`.
    - The day and the year are compared as integers with the pin's period end.
    - An unknown month or an impossible date names no period. Examples are "Marhc 31", "February 30" and "Foo 1". Such a title still governs, fails to match, and the metric is unlocated.
  - **No `try`/`except` and no sentinel year.**
    - There is no `try`/`except` in the envelope's reading (R130).
    - The no-year form carries no year (`None`), never the year 2000.
  - **Literal location never raises.**
    - A literal interrupted by markup is unlocated (R123).
    - A literal holding an entity is read on its decoded characters, and an entity counts as one character. It binds with its span over exactly the printed characters: `1&#46;63` binds 1.63, and the span covers those eight bytes.
  - A `ReceiptError`, `ValueError`, `IndexError` or `KeyError` escaping `build_event_workspace` on any input is a defect.

- **R135 (the receipt span is computed in raw coordinates; B7).**
  - The engine maps each decoded character of the cell text back to its raw extent:
    - an entity maps to its whole `&…;` run;
    - collapsed whitespace maps to its raw run;
    - a tag maps to nothing.
  - The span runs from the raw start of the literal's first character to the raw end of its last character.
  - No arithmetic mixes decoded and raw offsets, and no literal shape is hard-coded. The build hard-coded `&#…;%` at `pg_envelope.py:924-938`.
  - The extractor's own output always validates. A workspace the extractor built from some bytes passes `validate_selected_facts` against those bytes. B7 violated that: the build refused its own output once an `&#160;` preceded the dash.

- **R136 (the validator is a replay; B4, B5, B6).** This replaces R123's field-by-field list with one mechanism.
  - **First, the structural checks.**
    - Every facts entry passes the S0 path's structural checks, through the S0 helpers, exactly as the S0 path runs them. That holds for `pg_` and other entries alike, and for admitted and refused documents alike.
    - These checks run before any filtering.
    - An entry that names no metric is refused as S0 refuses it (B6).
  - **Then the replay.** The validator re-derives the rows from the source bytes, with the same extractor and the same fiscal scope.
    - Each workspace `pg_` row must equal its re-derived counterpart by deep equality over every key and value, after JSON normalisation. Lists and tuples compare equal, and no key may be added or dropped.
    - Deep equality covers `subject` (B5) and the whole `source_span` and receipt (B4). A span one byte wider or narrower differs from the re-derived span even when its hashes and excerpt were recomputed consistently.
    - It also covers `display_excerpt`, `text_sha256`, every typed-absence key, `value`, `unit`, `period`, `basis`, `authority` and `schema`.
  - **Unknown metrics and multiplicity.**
    - An unknown `pg_` metric raises `EconomicObservationError`.
    - Row multiplicity and order keep the treatment the frozen suites pin.
  - **No field is exempt.** If the lane finds a key that the bytes and the scope do not determine, it stops and reports it as a deviation. It never exempts that key silently.

- **R137 (the nested-table test is part of check 4; B9).** This amends where R129's test runs, not the code it gives.
  - Checks 1–3 run first, unchanged: exhibit, generator, issuer.
  - **Check 4** walks the tables in document order. It counts ordinals the way R116 and R129 count `<table` start tags.
    - A table that contains a nested `<table`, or that matches no role, gives `unknown_table:t<ordinal>`.
    - The first such table in document order decides the code.
  - The pinned outcomes:
    - generator line removed, plus a nested table: `generator_not_workiva`;
    - another issuer's masthead, plus a nested table: `issuer_not_pg`;
    - an injected unknown table at t7, plus a nested table later: `unknown_table:t7`;
    - a nested table in FY26 Q3's organic reconciliation, alone: still `unknown_table:t11` (R129).

- **R138 (wrapper whitespace and TYPE lines; B10, M1).** This amends R122's wrapper test and check 1.
  - **Wrapped.**
    - Strip an optional byte-order mark.
    - Then strip all leading whitespace as Python's `str.isspace` defines it, so form feed and vertical tab count.
    - Then the text must begin with `<DOCUMENT>`, compared case-insensitively.
    - The source is still never rewritten.
  - **B10 is a blocker.** R122's "leading whitespace" never meant only space, tab, carriage return and line feed.
  - **Check 1.**
    - Count every case-insensitive occurrence of `<TYPE>` in the header (the text before the first `<TEXT>`), wherever it sits on its line.
    - Exactly one is required. Its line, without a trailing carriage return, reads exactly `<TYPE>EX-99.1`.
    - An indented second TYPE line gives `not_ex_99_1` (M1).
    - A TYPE line after `<TEXT>` stays body text, which the frozen control pins.

- **R139 (the S0 `missing_fields` check; B11). Ratified.**
  - **The change.** The unwrapped path now refuses a typed absence whose `missing_fields` is not empty. The base accepted it.
  - **Evidence.** No engine emitter produces a non-empty `missing_fields`.
    - `grep -rn "missing_fields=" engine/ scripts/ app/ admin/` finds only `engine/company_intelligence/documents.py`.
    - There the only code that sets it is `absent_number`, which has no callers. Every other `TypedAbsence` constructor in `engine/company_intelligence/` passes keywords without `missing_fields`. The search covered those four trees.
    - So the check refuses only tampered workspaces, and the sixteen older suites pass unchanged.
  - **The seat's error.** R123 assumed that S0 already checked `missing_fields`. The base did not.
  - **Bar (d) amendment.** "The unwrapped (S0) behaviour changed" is replaced by three conditions:
    - S0 may tighten only against inputs that no S0 emitter produces.
    - S0 never loosens.
    - S0 accepts every output of the S0 extractors, as the sixteen older suites pin.

    Which error fires first on an entry with two defects is not behaviour.
  - **The frozen case.** `test_r139_s0_typed_absence_missing_fields_tamper_refused` pins the refusal. It replaces the audit's differential against a side-loaded base module.

- **R140 (the unit marker; M2).** This amends R128's grammar, per metric unit.
  - A literal read for a `usd_per_share` metric contains no `%`.
  - A literal read for a `percent` or `percentage_points` metric contains no `$`.
  - Otherwise the literal does not parse for that metric, and the metric is `envelope_unlocated` (R128's last bullet).
  - **Census.** The display excerpts bound on the three originals are nine per-share literals (no `%`, no `$`), eleven percent literals and three percentage-point literals (no `$`).
  - **Severity: blocker.** A per-share figure printed as a percentage is not in the metric's unit (bar a).

- **R141 (core and prior-core are told apart by anchors alone; a code-quality note, escalated to a blocker).**
  - **The rule and the deviation.** R125 tells the two apart by signature alone, with a currency-impact anchor that no prior-core table carries. The build does two other things:
    - It swaps the core anchor set when `currencyimpacttocoreeps` is present.
    - It excludes prior-core by a currency-token rule (`pg_envelope.py:584-602`).

    Meanwhile the prior-core vocabulary still lists ten currency tokens. That is a role rule outside the signature, and in effect a precedence rule (bar e).
  - **Mechanism.** The core anchors are one fixed set that includes `currencyimpacttocoregrossmargin`.
    - By census, that token is in the core reconciliation (t9) of each of FY26 Q1–Q3, and in no prior-core table.
    - The prior-core vocabulary holds only tokens that prior-core tables print. FY26 Q1's prior-core table (t11) prints no currency row.
    - There is no conditional anchor set and no exclusion rule.
  - **Satisfiable.** The seat simulated exactly this mechanism in memory, in its scratchpad. Both frozen suites stay green (171 passed), and both seat-authored R141 cases pass.
  - **Probes.** Both are seat-authored and frozen in R2:

    | construction on FY26 Q1's prior-core table | expected | at `5add1e2eefc` |
    |---|---|---|
    | add "Currency impact to earnings" and "Currency-neutral EPS" | `unknown_table:t11` | `required_table_repeated:core_reconciliation` |
    | add "Currency impact to core gross margin" | refused | admitted |

- **R142 (code quality, known limits, and the round-2 freeze and gate).**
  - **Required cleanups.** Review checks these; they carry R130 forward.
    - Remove the `Document` that `admit()` builds and discards (`:611`).
    - Remove `_labels` (`:232`), `_OTHER_ROLES` (`:52`) and the unused `_scope` import (`:891`).
    - Keep month names out of every vocabulary and anchor. The balance-sheet entries such as `'march<n>,<period>'` must fold the month (R125).
    - Remove the dead range entries such as `'january-march<period>'`.
    - Replace `strftime("%B %-d, %Y")` with a format that does not depend on the platform.
  - **Known limit: the header reader.** This is recorded, not blocking.
    - The engine's `_headers_over` has diverged from the suite's `headers_over`. It reads own cells only, and it adds a branch for a row with a single filled cell.
    - R124's standard is still the suite's `headers_over`. The R2 suite now pins title semantics black-box.
    - The R3 audit runs an engine-versus-witness differential over every pinned cell of the originals and their frozen mutations. A divergence that changes a governing title is a finding.
    - Two areas are not yet probed: tag-stripped text (hidden text, comments that hold tags) and rowspan-carried headers. They join the R3 audit's floor.
  - **The freeze.** `tests/test_pg_envelope_f1_probes_r2.py` holds 70 cases:
    - the auditor's 68, with the B11 differential replaced by the R139 refusal case;
    - the two seat-authored R141 cases.

    At `5add1e2eefc` it gives 43 failed and 27 passed, on Python 3.12 with only pytest and pyyaml installed.
  - **What stays out of the freeze.** The round-1 white-box control `test_f10_control_q4_tables_match_no_f1q_role_beyond_masthead` is not frozen, because R131 keeps white-box controls out of frozen suites. The R2 suite pins B2 black-box, and the R3 audit re-runs the round-1 file.
  - **The gate.** The suite joins the `earnings-economic-dossier` job's paths and run line in `.github/ci/legacy-jobs.yml`.
  - **Scope of the next repair.** It changes only three files: `engine/company_intelligence/pg_envelope.py`, `pg_profile.py` and `economic_observations.py`. Everything else must hold:
    - every frozen file stays byte-identical;
    - all three frozen envelope suites pass;
    - the gate line and `curated_exclusive` pass;
    - the a5a and capital-structure suites match the baseline test by test.
  - **Hold.** #7905 stays Draft/HOLD under Sol's direction (comment 5825632041).
