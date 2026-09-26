# Seat ruling — T1 envelope, audit round 1 (R122–R131)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source: the independent Opus audit of the envelope build at `c6bebf3a9d53` (PR #7905). The audit was READ_ONLY and its verdict was **REJECT**. The full report is committed beside this record as `OPUS_T1_ENVELOPE_AUDIT_R1_2026-09-25.md`.
- It ran 103 probes and 43 failed. Four of the failures are probe artefacts, which the audit itself marks as lawful fail-closed refusals.
- The findings:
  - nine blockers: F-D1, F-C1, F-C2, F-A1, F-E1, F-E2, F-B1, F-F1 and F-F2;
  - four minors: F-B2, F-M1, F-M2 and F-M3;
  - one coverage note, F-M4;
  - code-quality notes.
- The audit confirmed the positive work:
  - The frozen suite is 46 of 46 green on Python 3.12 and 3.14.
  - The unwrapped (S0) behaviour is invariant, test by test.
  - Cross-table swaps, duplicate labels, header geometry, issuer probes and footnote-date probes all behave.

This record amends R116–R121 (`SEAT_RULING_T1_ENVELOPE_2026-09-25.md`) only where it says so. Everything else there stands.
- `tests/test_pg_envelope_f1.py` and `tests/fixtures/pg_envelope/` stay byte-identical.
- The rulings below are enforced by the new frozen suite `tests/test_pg_envelope_f1_probes_r1.py` (R131).
- The seat grounded every factual premise below in its own census of the three F1-Q originals, run in memory with the frozen suite's engine-free reader.

- **R122 (wrapper detection and routing; F-D1, F-B2).**
  - **Scope.** The routing lives inside the P&G private profile only: `extract_pg_release_facts`, and the `pg_` rows of `validate_selected_facts`. Other issuers' profiles and non-`pg_` rows keep their current behaviour, wrapped or not.
    - The DHI and PHM Ex-99.1 fixtures of `tests/test_issuer_profiles_a5a.py` are EDGAR-wrapped too, and so is the capital-structure corpus.
    - Their suites must pass unchanged.
  - **Wrapped.** A body is wrapped if, after an optional byte-order mark and leading whitespace, it begins with `<DOCUMENT>`, compared case-insensitively.
    - Every wrapped body is admitted to F1-Q or refused.
    - No wrapped body reaches the legacy grammar reader by any path, including an exception fallback. An exception inside the envelope is a defect, never a route.
  - **Check 1, amended.**
    - The wrapper header is the text before the first `<TEXT>` tag, found case-insensitively.
    - The header holds exactly one `<TYPE>` line, counted case-insensitively. That line reads exactly `<TYPE>EX-99.1`; a trailing carriage return is tolerated.
    - Anything else is `not_ex_99_1`: two TYPE lines, a lower-case tag, no TYPE line, or no `<TEXT>` tag.
  - **The source is never rewritten.** There is no line-ending or byte-order-mark normalisation, so every span indexes the original bytes.
- **R123 (the validator is complete; F-C1, F-C2, F-M3).**
  - **Structural checks.** The wrapped branch keeps R120 and adds every structural check the S0 path makes, through the S0 path's own helpers, never a copy. The checks cover:
    - the row schema and exact key sets, and the typed-absence keys;
    - `authority`, `subject`, `schema` and `missing_fields`;
    - the receipt's `segment_sha256`, `segment_bytes` and `text_sha256`, and `display_excerpt`;
    - booleans, finite numbers, and non-mapping entries.
  - **Field equality.** Every field the envelope determines must equal the outcome re-derived from the bytes, on the rows of a refused document too. The fields are value, unit, period, basis, the receipt span, and every typed-absence key.
  - **Unknown metrics.** An unknown `pg_` metric raises `EconomicObservationError`, never `KeyError`.
  - **The receipt span covers exactly the printed literal's characters** inside the primary cell. That tightens R117's "inside that cell".
    - No markup lies inside or around the span. An entity counts as a character.
    - `display_excerpt` is the span's text, exactly as the S0 helper replays it.
    - A literal interrupted by markup is not located. By census, every pinned literal in the three originals is contiguous, so the originals are unaffected.
- **R124 (a statement must be titled for the pin's period; F-A1).**
  - **Period-title forms** printed by the originals (seat census):

    | form | where it is printed |
    |---|---|
    | "Three Months Ended <Month> <D>, <YYYY>" | drivers, core reconciliation, prior-core reconciliation |
    | "Three Months Ended <Month> <D>" | earnings; the year sits in the column header |
    | "<Month> - <Month> <YYYY>" | segment drivers and organic reconciliation: one title, in the label column |

    The highlights and change-versus-year-ago tables print none.
  - **Governing titles.** A cell's governing titles are the period titles among the texts over it: the suite's `headers_over`. If there are none, they are the table's own period titles.
  - **Which period a pin names.**
    - The scope's current quarter, `scope[1]`.
    - The year-ago quarter, `scope[3]`, for `pg_prior_diluted_eps` and `pg_prior_core_eps`.
    - A growth column ("% Chg" or "% Change") names the current quarter.
  - **Tables that print titles in the originals** are the earnings, drivers, core reconciliation, prior-core reconciliation, segment drivers and organic reconciliation tables. A pinned cell in one of them is located only if it has exactly one governing title and that title names the pin's period.
    - **Month/day form.** Its month and day are those of the period end. The year must also be the period end's, taken from the title or from a year column header over the cell. A growth column has no year and is compared on month and day only.
    - **Range form.** Its end month and year are those of the period end.
  - **Tables that print no title.** In the highlights and change-versus-year-ago tables no title is required. Any title present over the cell must pass the same test.
  - **Failure.** Otherwise the statement is not located, and the metric is `envelope_unlocated` (R117).
  - **Frozen mutations.** `period_single` and `period_both` keep their outcomes. They swap the earnings year headers, and the swapped cell's title and year still name the current quarter, so it binds the swapped value exactly as R117 froze.
- **R125 (signatures carry no dates or values; F-E1, F-M2, the role tie).**
  - **Folding.**
    - Every numeric run folds to `<n>`: digits with signs, "$", "%", parentheses and separators.
    - The dash forms "—" and "—%" also fold to `<n>`.
    - The date part of every period-title form folds as one class. The duration word stays, so a twelve-month (F2-A) title never folds onto a three-month one.
  - **No literals in anchors or vocabularies.** Anchors and vocabularies hold no literal date, year or value.
    - The headline vocabulary folds, for example to `dilutedeps<n>,<n>;coreeps<n>,<n>`. Editing an unpinned headline or guidance figure therefore keeps admission.
    - By census, every role that matches an original has non-empty common folded tokens across FY26 Q1–Q3.
  - **Empty signatures.**
    - Every role has non-empty anchors.
    - A table with no label cells matches no role, so it is `unknown_table:t<ordinal>`.
  - **Ties.** A table matching more than one role matches none; there is no precedence rule.
    - Core and prior-core reconciliations are told apart by signature alone. The core reconciliation's anchors include a currency-impact row token that no prior-core table carries; by census, "currency impact to core gross margin" is in every core reconciliation. The distinction is never made by period or scope, which would move the frozen `q3_under_q2_scope` and `drivers_removed` codes.
    - `other_core_reconciliation` is removed. It matches no table in any original.
  - **Census obligation.** Each table of the three originals matches exactly one role. The frozen F2-A refusals (`unknown_table`) still hold.
- **R126 (check order and multiplicity; F-E2).**
  - **Order.** Check 4 runs over every table and reports the first unmatched ordinal before check 5 runs.
  - **Check 5 counts required roles only.** The admitted quarter is read from the month of the scope's current period end. P&G's fiscal year ends on June 30, so September is FQ1, December is FQ2 and March is FQ3.
    - In FQ1 the required roles are the seven pinned roles plus `prior_core_reconciliation`.
    - In any other quarter they are the seven.
    - Check 6 then refuses any quarter the bytes contradict.
  - **Unread roles.** Known roles that are not read may be absent or repeated.
  - **The audit's gap on bar (b), answered.** Removing or repeating an unread table, such as the balance sheet, stays admitted, as R116 already reads ("The pinned roles are required").
    - No pin reads such a table, so it cannot move a bound value.
    - Check 4 still refuses any table outside the vocabulary, and a missing, repeated or retitled pinned table still refuses or unlocates.
- **R127 (year-ago Core EPS follows the admitted quarter; F-B1, F-M4).**
  - The second statement of `pg_prior_core_eps` is chosen by the admitted quarter (R126), never by which tables happen to be present:
    - **FQ1:** the prior-core reconciliation's Core EPS cell.
    - **FQ2 and FQ3:** the core reconciliation's "As Reported (GAAP) (1)" EPS cell, together with the R117 footnote.
  - A prior-core table in an FQ2 or FQ3 release is known and unread. So FY26 Q3 with FY26 Q1's prior-core table appended keeps its frozen value while the footnote is present, and is unlocated without it.
- **R128 (literal parse: R118's text governs; F-F1, F-F2).**
  - **What governs.** The engine follows R118 as written. The suite's `literal()` helper is a witness convenience and stays frozen, unchanged.
    - No frozen case exercises the difference.
    - By census, every pinned literal in the originals is free of whitespace and non-ASCII digits.
    - The only bare dash in the originals is FY26 Q2's change-versus-year-ago Core EPS, printed "—" beside a "%" cell. That is R118's second form.
  - **The engine's grammar.**
    - After trimming, the text holds no whitespace and only ASCII digits, and it matches the frozen grammar: parentheses are negative, with optional "+", "$" and "%".
    - A dash is 0.0 only as "—%" in one cell, or as "—" whose next filled cell in the row is "%".
    - So "1 63", "+ 2%", "3 %", "— %", full-width digits and a bare "—" are not numbers.
  - **A located cell whose text does not parse** counts as not located. The metric is `envelope_unlocated`, never a conflict and never a bind.
- **R129 (nested tables; F-M1).** A table whose markup contains a nested `<table` matches no role. The code is `unknown_table:t<ordinal>`, counted among all `<table` start tags as R116 counts them, so a table nested in FY26 Q3's organic reconciliation gives `unknown_table:t11`.
- **R130 (code quality).**
  - Remove the dead code:
    - the unused `Document` that `admit` builds;
    - `_document`'s unreachable `None` branch and the checks on it;
    - `_visible_text` and `_anchor`;
    - the triple assignment of `cash_flow_reconciliation`, and the `"__cash_flow_reconciliation"` key;
    - `other_core_reconciliation` (R125).
  - `_eps_row` never raises. A core reconciliation with more than one diluted-EPS row, whatever its marker, leaves `pg_core_eps` and `pg_prior_core_eps` unlocated, with every other value kept.
  - No `try`/`except` wraps the envelope's own reading.
- **R131 (the round-1 freeze and gate).**
  - **The frozen suite.** `tests/test_pg_envelope_f1_probes_r1.py` is the auditor's probe file as adapted by the seat. It is byte-identical from this freeze, and a repair never edits it.
    - Probe artefacts now accept the lawful refusal codes.
    - The spaced-literal and wrapper expectations are exact.
    - The white-box Q4 control and the in-memory FY27 registration are removed.
    - The seat added:
      - the R123 receipt-span check on all three originals;
      - the R124 cross-release retitle sweep (four retitles × FY26 Q1–Q3) and the removed range title;
      - the R126 multiplicity and order cases;
      - the R128 spaced forms;
      - the R122 case and whitespace forms of the wrapper;
      - the R130 EPS-row cases.
  - **RED at freeze:** 125 cases, 58 failed and 67 passed at `c6bebf3a9d53`. The failures, by ruling:

    | ruling | failed | cases |
    |---|---|---|
    | R122 | 9 | the wrapper forms, including two TYPE lines |
    | R123 | 20 | 15 tampered admitted rows, 2 tampered refused rows, 3 receipt spans |
    | R124 | 13 | |
    | R125 | 3 | |
    | R126 | 2 | |
    | R127 | 2 | |
    | R128 | 8 | |
    | R129 | 1 | |

    The 67 passes are regression guards the repair must keep green: cross-table swaps, duplicate labels, header geometry, non-numbers, issuer, controls, and both EPS-row cases.
  - **The gate.** The suite joins `earnings-economic-dossier` in its paths and its run line.
    - At the freeze, the run line gives 58 failed (exactly this suite's reds), 937 passed and 174 skipped, in about 69 s locally. That is within the job's 6-minute timeout.
    - `tests/test_ci_pack.py -k curated_exclusive` gives 2 passed.
  - **Merge.** #7905 stays DRAFT with no labels. There is no Ready and no merge until the repair is green, an independent re-audit accepts it, and the carrier's hold is released.

**Known limits, stated rather than hidden.**
- **Rendering semantics.** Cell text is tag-stripped text. Hidden or styled content (`display:none`, or a comment holding tags) counts as printed in both the engine and the witness.
- **Footnote containment is a substring test**, shared by the engine and the witness.
- **The engine and the witness share one reading algorithm.** The oracle (R119) is the independent check, and it covers the originals only.
- **An unwrapped real body** is S0 and reaches the legacy path. Production exhibits are served wrapped.
- **The mutation sweep is not full.** The R124 retitles now cover FY26 Q1–Q3, but every other mutation family covers FY26 Q3 only. The re-audit carries a Q1/Q2 sweep.
