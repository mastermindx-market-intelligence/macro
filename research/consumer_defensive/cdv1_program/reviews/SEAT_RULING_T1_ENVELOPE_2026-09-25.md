# Seat ruling — T1 first-release envelope, family F1-Q (R116–R121)

Adjudicator: the CDV-1 Meta-CEO seat (session 251f88c8, running Opus 5.5 under the fable-mode doctrine).

Source of the change: the GMI Meta-CEO direction on #7905 (comment 5825632041, 2026-09-25T02:22:28Z), which the seat adopted as R114 (`SEAT_RULING_T1_PR_R16_2026-09-24.md`). T1 now completes on a finite first-release source/layout envelope, not on a universal reading of synthetic markup.

This record freezes the envelope's first family, **F1-Q**, before any engine code is written. The frozen witness suite is `tests/test_pg_envelope_f1.py`. It is RED at freeze for behavioural reasons only (R121).

- **R116 (families and structural admission).**
  - **Families.**

    | family | definition | status in v1 |
    |---|---|---|
    | F1-Q | P&G (CIK 80424) 8-K Ex-99.1 quarterly results release, Q1–Q3 layout, Workiva-rendered, as the EDGAR archive serves it | admitted; witnesses FY26 Q1, Q2 and Q3 |
    | F2-A | the same issuer and template, Q4 plus fiscal-year layout | refused in v1 (as `unknown_table`); next increment |
    | S0 | a body with no EDGAR SGML wrapper (the synthetic corpus of the fifteen frozen suites) | unchanged; the existing reader and validator |

  - **Admission reads source bytes only**, so the validator re-derives it without the extractor. A body that begins with the EDGAR `<DOCUMENT>` wrapper is admitted to F1-Q or refused. The checks run in this order, and the first failure is the refusal code:
    1. `<TYPE>EX-99.1` in the wrapper, or `not_ex_99_1`.
    2. The exact generator comment `<!-- Document created using Wdesk -->`, or `generator_not_workiva`. The Workiva copyright comment alone does not satisfy it.
    3. The masthead table (the body's first table) names "The Procter & Gamble Company", or `issuer_not_pg`. Mentions elsewhere in the body (the dateline, loose divs) do not count.
    4. Every table in the body matches the signature of a known F1-Q table role. Otherwise `unknown_table:t<ordinal>`, where the ordinal is that of the first unmatched table in document order among all `<table` start tags.
    5. Each required role appears exactly once: `required_table_missing:<role>` or `required_table_repeated:<role>`.
    6. The quarter the release reports, read from its bytes, equals the admitted fiscal scope, or `quarter_mismatch`.
  - **Role signatures.** Roles are found by signature, never by position, so a dropped, repeated or injected table yields the codes above.
    - A signature is built from the table's label cells (row labels and column headers) only.
    - It is **order-invariant within the table**. The frozen swap mutations (R117) keep every label and must stay admitted.
    - It is drawn from a **closed label vocabulary**. A table whose labels fall outside it, such as the frozen injected "Pro Forma Combined Company" table, is unknown.
    - Period tokens are read as a class, never as literal years. Values never enter a signature.
    - Every table in an F1-Q release has a role. Most roles are known but unread (masthead, headline, balance sheet, cash flow and the like). The pinned roles are required.
  - **A refused document.** Every metric is a typed absence, reason `no_span_addressable_evidence`, detail `envelope_refused:<code>`. It is the same detail on every row, and no present fact is allowed. No absence vocabulary is minted, and `ABSENCE_REASONS` stays closed.
  - **Frozen refusal witnesses** (the `REFUSED` table):
    - on FY26 Q3: `type_ex_99_2`, `generator_removed`, `masthead_other_issuer`, `table_injected` (→ `unknown_table:t7`), `drivers_removed`, `drivers_repeated`, and `q3_under_q2_scope`;
    - both F2-A releases (→ `unknown_table:t<n>`);
    - the near neighbour, Colgate-Palmolive Q2 2026 Ex-99 on the same template: as filed (→ `not_ex_99_1`), and relabelled Ex-99.1 (→ `issuer_not_pg`).
- **R117 (the pinned table; primary and second statements).**
  - Each numeric metric has a primary printed statement and a second printed statement. They sit in different tables under different labels. The roles:
    - `highlights`, `segment_drivers`, `earnings`, `drivers`, `core_reconciliation`, `change_versus_year_ago` and `organic_reconciliation`;
    - `prior_core_reconciliation`, FY26 Q1 only.

    The suite's `pins()` is the frozen table.
  - **A present fact.** Both statements are each located exactly once and agree. The value is the literal parse of the primary cell. The receipt's byte span lies inside that cell, and the literal parse of the span text equals the value.
  - **An absent fact.**
    - The statements disagree: `cross_check_conflict`, detail prefix `envelope_conflict`.
    - Either statement is located zero or several times: `no_span_addressable_evidence`, detail prefix `envelope_unlocated`.
  - **Year-ago Core EPS in FY26 Q2 and Q3.** The second statement is the core reconciliation's "As Reported (GAAP)" column. It counts only when the release prints, between that table and the next, the footnote: "(1) For the three months ended <year-ago quarter end>, there were no adjustments to or reconciling items for Core EPS." Whitespace is ignored, because the release sets the "(1)" marker in its own element. This footnote is the only text outside a table that v1 reads. Without it the metric is unlocated (mutation `note_removed`).
  - **Excluded.** `pg_core_reconciliation_context` is outside the first release: `no_span_addressable_evidence`, detail `envelope_excluded:pg_core_reconciliation_context`. No prose reading is reopened.
  - **Swap mutations on FY26 Q3.** Each swaps the whole content of two cells of one statement:
    - period: the earnings statement's year headers;
    - row: "Total Company" and "Beauty";
    - column: "Price" and "Mix";
    - basis: "As Reported (GAAP)" and "Core(Non-GAAP)";
    - plus the footnote removal.

    A swap in one statement yields a conflict. The same swap in both statements binds the swapped values. Binding the pre-mutation value fails. The frozen deltas are the suite's `MUTATIONS`, and every delta follows from the pins on the mutated bytes (`test_frozen_mutation_outcomes_follow_from_the_pins`).
- **R118 (dash is zero in F1-Q; narrows plan line 206 for this family only).**
  - An em dash printed where a number belongs, either "—%" or "—" beside a "%" unit cell, is 0.0 in F1-Q.
  - The oracle spec stated this convention before the oracle read the releases. The releases mark not-applicable separately ("n/a" in the highlights table) and print no dash-means-zero sentence.
  - It is therefore a family convention pinned by the envelope, not a universal reading. Plan line 206 ("dash is zero only when the fixture supplies an explicit neutral convention") stays the rule everywhere else.
  - Flagged to the decision owner on #7905.
- **R119 (the independent oracle, and the seat's adjudication of it).**
  - **The oracle.** The expected values are an independent read authored from the five P&G originals alone.
    - It ran on a remote fabric lane on mb, receipt `rs_20260925T030518Z_53323`, rc=0.
    - The lane's working directory held only the spec and the five originals: no repository, and no engine code read or run.
    - The oracle files are committed byte-exact as the lane returned them: `oracle_f1.json`, `oracle_f1_notes.md` and `oracle_f1_spec.md`.
  - **The adjudication.** The seat's overlay is `seat_adjudication.json`. It changes **no value**.
    - Every numeric oracle value agrees with the seat's own second-statement reading of the same bytes: 95 of 95 comparisons across the five releases.
    - The frozen pins reproduce all 57 F1-Q values.
  - **Eight locator corrections**, all in the highlights table. For FY26 Q1 and Q2 EPS, the oracle labelled the fiscal-year columns one year early ("2025" for the FY2026 column).
  - **One unit-label deviation.** The four contribution metrics are defined in percentage points; the oracle labelled them percent. No value is affected.
  - **Not used in v1.** Five F2-A `also_found` entries: four fiscal-year headline lines quoted for quarterly growth rates, and one two-cell hit.
  - **Independence of the suite.** Every table/row/column locator in the suite is resolved by its own stdlib grid reader, which imports nothing from the engine package. The engine is only the system under test.
- **R120 (the validator: re-derive, never accept by replay).**
  - For an EDGAR-wrapped body, `validate_selected_facts` re-derives admission from the source text. For an admitted document it then checks every row against the frozen pin data and the bytes:
    - **refused document:** every row is an absence carrying the re-derived `envelope_refused:<code>`. A present fact (V3) or a code the bytes do not support (V6) is refused.
    - **present fact:** the receipt span lies in the metric's own primary cell; a span moved to another metric's cell with the same printed value is refused (V1). The value is that cell's literal (V2). The second statement agrees (V4: the primary cell prints the forged value, but the other statement contradicts it).
    - **absent fact:** its kind is the re-derived kind. An absence that hides an agreed value is refused, whether plain or dressed as a conflict (V5).
  - An S0 body keeps the existing validation, unchanged.
  - **What the validator is not.** The validator and the extractor share one frozen pin table, which is declarative data. Their correctness is not proven by the validator agreeing with the extractor. It is proven by the pins reproducing the independent oracle through the suite's engine-free reader (R119). The validator's job is narrower: the workspace must be exactly what that frozen data says about these bytes, so a tampered, forged or mis-spanned row cannot pass.
- **R121 (freeze, gate and rights).**
  - **The freeze.** One seat commit holds the suite, its fixtures and this record. The suite stays byte-identical from here, and a repair never edits it.
  - **RED at freeze:** 46 cases, 28 failed and 18 passed.
    - The 18 passes are the 16 engine-free self-consistency checks, plus V3 and V4, which the current head already refuses. All 18 must stay green after the build.
    - The 28 failures are behavioural:
      - the three positives, nine mutations and eleven refusals, which bind nothing or carry the current extractor's details;
      - V1, V2, V5 (both variants) and V6, whose preconditions need a bound or envelope-refused workspace.
  - **The gate.** The suite joins the gate job `earnings-economic-dossier` in its paths and its run line, with `tests/fixtures/pg_envelope/**` in its paths. The build adds the new engine module to the same paths.
    - The contract-delta curated-closure check reports no uncovered path for any curated job with the suite wired.
    - It adds about 44 s to the job; the existing run takes about 63 s locally, within the job's 6-minute timeout.
  - **Rights basis.** The six fixtures are exact public SEC EDGAR exhibits. They are committed gzipped (`gzip -9`, mtime 0) and pinned by the sha256 and size of the bytes EDGAR serves (`tests/fixtures/pg_envelope/SOURCES.md`).
    - They are committed under the decision owner's direction on #7905, on the same basis as `tests/fixtures/capital_structure/document_terms/real_edgar_*`.
    - They are test inputs only: nothing read from them is rendered or published.
  - **Merge.** #7905 stays DRAFT, with no labels, no Ready and no merge, until the envelope build is green and the carrier's hold is released.

**Known limit, stated rather than hidden.** v1 reads no prose beyond the one pinned footnote. A basis change declared only in prose, with no change to any table, is not detected. The structural mitigation is admission: every table in the body must match a known signature.
