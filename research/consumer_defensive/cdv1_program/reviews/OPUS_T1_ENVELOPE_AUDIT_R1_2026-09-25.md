# Opus audit: CDV-1 T1 F1-Q envelope build at c6bebf3a9d53e9eae814d6fc13e7b728c8857b86 (PR #7905)

Mode: READ_ONLY. Nothing in the repository was edited, committed or pushed, and PR state was not touched.
Bar: the review standard (a)–(f) in the commission, ruling R116–R121.
Probe file: `test_envelope_audit_probes.py`, in this directory. Each case asserts the correct outcome, so a failing case is a finding.

## STATUS: REJECT

The bar is breached on four of its letters:
- (a) wrong period: F-A1;
- (c) validator acceptance: F-C1 and F-C2;
- (d) wrapped body reaching the legacy reader: F-D1;
- (e) values in signatures and check order: F-E1 and F-E2.

It is also breached on (f): the bare-dash and spaced-digit parse (F-F1 and F-F2). This last breach is shared with the frozen suite's `literal()`, so the seat must adjudicate it.

The (b) finding F-B1 is on the injected-known-role path.

The positive work is sound:
- The frozen suite is 46 of 46 green on 3.12 and 3.14.
- S0 is invariant per test.
- Cross-table swaps, duplicate labels, header geometry, issuer and footnote-date probes all behave.

## Findings

| id | bar | sev | probe | observed | expected |
|---|---|---|---|---|---|
| F-D1 | d | blocker | `test_f5_wrapper_and_markup[crlf_whole_body, crlf_after_document_tag, lowercase_type_tag, no_type_line, no_text_tag, bom_before_document]` | Every row carries the LEGACY reader's details ("No unique heading, row label…", "The reconciliation paragraph…"). | The wrapper-led body is admitted or refused (`envelope_refused:<code>`). |
| F-C1 | c | blocker | `test_f9_validator_refuses_a_tampered_admitted_workspace[authority, subject, absence_schema, missing_fields, row_schema, present_plus_absence, extra_key, display_excerpt, text_sha, segment_bytes, segment_sha, locator, bool_value, nonmapping_fact]` (14 cases) | The validator ACCEPTS each tampered workspace. | `EconomicObservationError`, as the S0 path raises for every one. |
| F-C2 | c | blocker | `test_f9_refused_document_row_tampered[authority-authoritative, subject-pg_core_eps]` | Accepted on the refused document (Ex-99.2). | Refused. |
| F-A1 | a | blocker | `test_f7_primary_statement_titled_year_ago_is_never_bound_as_current_quarter[segment_drivers_title_year_ago, organic_reconciliation_title_year_ago, core_reconciliation_period_titles_swapped]` | 7 + 6 + 1 metrics are bound with `period=2026-03-31`, even though the pinned PRIMARY table now titles its column "January - March 2025" / "Three Months Ended March 31, 2025". | Not a present fact for the scope quarter. |
| F-E1 | e | blocker | `test_f10_headline_value_edit_keeps_admission`, `test_f10_guidance_range_edit_keeps_admission` | Changing the UNPINNED headline "$1.63" to "$1.64" gives `envelope_refused:unknown_table:t1`. Changing the guidance "+6%" to "+7%" gives `unknown_table:t13`. | Admitted with all 19 values, because R116 says values never enter a signature. |
| F-E2 | e | blocker | `test_f10_check_order_unknown_before_repeated` | `required_table_repeated:drivers` | R116 checks every table (4) before role multiplicity (5), so `unknown_table:t17`. |
| F-B1 | b (and pin law R117) | blocker | `test_f8_footnote_rule_follows_the_frozen_pins[q3_note_removed_plus_injected_q1_prior_core_table]` | FY26 Q3 with the footnote removed and FY26 Q1's prior-core table appended binds `pg_prior_core_eps = 1.54`. | Unlocated: the frozen Q3 pin is the core-rec GAAP (1) column plus the footnote. R117 says prior_core_reconciliation is "FY26 Q1 only". |
| F-F1 | f | blocker (shared with frozen `literal()`) | `test_f4_bare_em_dash_in_both_eps_cells_is_not_zero`, `…primary_with_zero_second_is_not_bound`, `…in_single_percent_cell_is_not_zero` | A bare "—" in a Diluted EPS cell ("$" beside it) binds `pg_diluted_eps = 0.0`. A bare "—" in the one-cell "% Chg" slot binds 0.0. | Unlocated. R118 makes a dash zero only as "—%" or as "—" beside a "%" unit cell. |
| F-F2 | f | blocker for "1 63"; minor for the others (shared with frozen `literal()`) | `test_f4_shared_with_frozen_literal_space_and_unicode_digits[1 63, + 2%, １.６３]` | "1 63" parses as 163.0, "+ 2%" as 2.0, and full-width digits as 1.63. | Unlocated. |
| F-B2 | b | minor | `test_f5_wrapper_and_markup[two_type_lines]` | A wrapper with `<TYPE>EX-99.1` then `<TYPE>EX-99.2` is admitted, and all values bind (the first TYPE line wins). | Refused. |
| F-M1 | — | minor | `test_f5_wrapper_and_markup[nested_table_in_orgrec]` | A nested table anywhere gives `issuer_not_pg`, because `_table_spans` returns `()` and the document appears to have no tables. | `unknown_table:t<n>`. It is still a refusal. |
| F-M2 | — | minor | `test_f10_label_free_table_is_unknown` | An injected label-free table gives `required_table_repeated:headline`, because headline has empty anchors. | `unknown_table:t7`. It is still a refusal. |
| F-M3 | — | minor | `test_f9_…[unknown_pg_metric]` | An extra row `pg_forged_metric` raises `KeyError` (economic_observations.py:122). | `EconomicObservationError`. It is still refused. |
| F-M4 | — | minor / coverage | `test_f8_…[q3_injected_q1_prior_core_table_note_present]` | `conflict` | 1.54. The failure is fail-closed, but it shows that pin selection is driven by table presence. |

### Code evidence (file:line at the head)

- **F-D1.** `engine/company_intelligence/pg_envelope.py:197-204`. `_wrapped` requires the literal `"<DOCUMENT>\n"` prefix, a `<TEXT>` tag, and an upper-case `<TYPE>…\n` line. Any other wrapper-led body returns False. The extractor then falls through to the legacy grammar at `pg_profile.py:2172`, and the validator falls through to S0 at `economic_observations.py:290`. Note also that `bind_release_document` does not normalise CRLF: the bound source starts `'<DOCUMENT>\r\n'`.
- **F-C1 / F-C2.** `economic_observations.py:90-183`, the wrapped branch, which returns early at line 290. That branch omits every structural check the S0 path makes:
  - the row `schema`;
  - the exact `PRESENT_KEYS`/`ABSENT_KEYS` key sets (line 325);
  - the `TYPED_ABSENCE_KEYS`, schema, `authority == "context_only"`, subject and missing_fields checks;
  - `segment_sha256`, `segment_bytes` and `text_sha256`;
  - `display_excerpt == replayed bytes`;
  - the bool/finite value check (line 409);
  - the non-Mapping facts check.

  The absent branch (lines 170-179) checks only reason, detail, event_id and document_id. So a present row can carry a forged `display_excerpt` ("9.99" beside value 1.63) or `value=True` for 1.0, and an absent row can claim `authority="authoritative"`. The validator returns such rows as validated.
- **F-A1.**
  - `pg_envelope.py:216-221`: the quarter is read only from the `drivers` table's first "Three Months Ended …".
  - `pg_envelope.py:111-113`: every label year folds to `<period>`, so "january-march<period>" matches either year.
  - The primary statements `segment_drivers`, `organic_reconciliation` and `core_reconciliation` are never period-checked.
  - `pg_envelope.py:685`: the period stamped is `current_end`.
- **F-E1.** `pg_envelope.py:346-354` (headline vocabulary: "dilutedeps$1.63,+6%;coreeps$1.59,+3%", "netsales+7%;organicsales3%", …) and `pg_envelope.py:362-369` (guidance "+1%to+5%", "+3%to+9%", …). These are per-release VALUE literals inside a signature vocabulary, which R116 forbids. They also mean that the refusal of the F2-A releases at `t1` rests on a headline value mismatch. Only the masthead of F2-A matches any role (control `test_f10_control_q4_tables_match_no_f1q_role_beyond_masthead` passes, so this is not an admission leak).
- **F-E2.** `pg_envelope.py:456-463`: the repeat check runs inside the step-4 loop and returns before later tables are signature-checked. The same line mislabels non-required repeats (e.g. `required_table_repeated:balance_sheet`).
- **F-B1.** `pg_envelope.py:644-645` and `673-674`: `has_prior` comes from the presence of an admitted `prior_core_reconciliation` role, and forces `prior_note=True`. `pg_envelope.py:571-573` then switches the second statement. The quarter never decides it, although R117 fixes it to FY26 Q1.
- **F-F1 / F-F2.** `pg_envelope.py:538-546`. `_literal` treats `"—"` as 0.0 with no beside-"%" condition, strips inner spaces (`replace(" ", "")`), and uses `\d`, which matches any Unicode Nd. The validator reuses it (`economic_observations.py:163`). The suite's `literal()` (tests/test_pg_envelope_f1.py) is byte-for-byte the same logic, so the frozen suite cannot detect this. The seat must rule whether R118's text or the suite helper governs. Under the bar as written, R118 governs.
- **Other code-quality items** (non-blocking):
  - dead code: `admit()` builds a `Document` it discards (line 439); `_document` never returns None, so the checks at lines 434, 699 and `pg_profile.py:2174` are dead; `_visible_text` and `_anchor` are unused; `_ANCHORS["__cash_flow_reconciliation"]`;
  - `_ANCHORS`/`_VOCABULARIES` for `cash_flow_reconciliation` are reassigned three times (lines 404-415);
  - `other_core_reconciliation` duplicates the `prior_core_reconciliation` vocabulary and is resolved by an ad-hoc set rule (lines 425-428);
  - `_eps_row` raises `ValueError` (line 534); it was not reached by the probe;
  - the receipt span covers the whole cell markup, so `display_excerpt` is raw `<font …>1.63&#160;</font>`, not the literal;
  - the engine grid reader (lines 137-189) is a verbatim copy of the suite's "independent" reader, so shared reader defects cannot be seen by the witness. R119 independence still holds for values through the oracle.

## Probes run / failed, per attack family (103 run, 43 failed)

| family | run | failed | notes |
|---|---|---|---|
| 1 cross-table swaps | 5 | 0 | Each swap → conflict; engine equals the witness. |
| 2 duplicate labels | 8 | 0 | All unlocated; no first-match. |
| 3 header geometry (colspan, empty-cell shift, rowspan) | 6 | 0 | No other value bound; engine equals the witness; the validator accepts. |
| 4 cell-text variants | 24 | 8 | 3 = F-F1. 3 = F-F2. 2 are probe artefacts: "2.0 pts" and "— per share" carry letters, become labels and refuse the document as `unknown_table:t2`, which is lawful fail-closed. |
| 5 wrapper / markup | 11 | 8 | 6 = F-D1, 1 = F-B2, 1 = F-M1. Upper-case tags and a comment in a cell are clean. |
| 6 issuer | 3 | 0 | |
| 7 quarter | 6 | 4 | 3 = F-A1. 1 probe artefact: removing the drivers year gives `unknown_table:t6`, which is correct R116 order. |
| 8 footnote | 5 | 2 | F-B1 and F-M4. A moved note, a changed date, and a GAAP disagreement are clean. |
| 9 validator | 28 | 17 | 14 + 2 = F-C1/F-C2; 1 = F-M3. V1/V2-style, prior-year column, period, unit, basis, sha, missing and duplicate rows, conflict-as-present and unlocated-as-conflict are all refused. Reorder is accepted (control). |
| 10 code review | 7 | 4 | F-E1 ×2, F-E2, F-M2. Role-order-is-not-positional and the Q4-signature controls pass. |

Probe run (worktree root, venv_t1 Python 3.14):

`python -m pytest -p no:cacheprovider -q -rfE --tb=line …/test_envelope_audit_probes.py` → `43 failed, 60 passed in 26.40s` (log: `probes.log`).

## Required evidence

- `git diff --stat e1dd9caa3fa c6bebf3a9d53e9eae814d6fc13e7b728c8857b86 -- tests/ research/` → empty. The frozen suite and fixtures are byte-identical.
- The full diff touches only `engine/company_intelligence/{pg_envelope.py (+701), pg_profile.py (+6), economic_observations.py (+104)}` and `.github/ci/legacy-jobs.yml (+4)`. The four build commits 8777ff0c81, ecc62b2e66, fe85d86d4a and c6bebf3a9d are confirmed in the log.
- Gate run line (`earnings-economic-dossier`, legacy-jobs.yml:13613) at the head on 3.14 → `870 passed, 174 skipped, 89 warnings in 37.28s` (`head_gate.log`).
- Frozen suite: 3.14 → `46 passed` (`env314.log`); **3.12.13** (fresh venv, pytest and pyyaml only) → `46 passed, 66 warnings in 11.11s` (`env312.log`).
- `tests/test_ci_pack.py -k curated_exclusive` → `2 passed, 119 deselected` (`cipack.log`).
- S0 invariance: the fifteen older suites run from `git archive e1dd9caa3fa` (`base/`) give `824 passed, 174 skipped`. The per-test junit comparison against the same fifteen at the head: 998 vs 998 test ids, **0 differences** (`cmp_junit.py`, `base15.xml`/`head_gate.xml`).
- The three extra job paths: `curated_exclusive_closure_findings` gives `{}` at the head. On a copy of the manifest without the three added lines (1223, 12630, 16860), it reports misses for exactly `conviction-profile`, `skew-accrual-lane` and `unrun-picks-boards`, each missing `engine/company_intelligence/pg_envelope.py` (`closure.log`). The additions are therefore required, because pg_profile now imports pg_envelope. They are harmless: widening path triggers is the safe direction.
- Runtime purity: pg_envelope imports only stdlib (`dataclasses, datetime, functools, html, re, typing`) and engine modules; there is no fixture, network or non-stdlib read. No absence reason was minted: `cross_check_conflict` and `no_span_addressable_evidence` are already in `ABSENCE_REASONS`.

## GAPS

- Rendering semantics are outside v1. The ruling defines cell text as tag-stripped text, so the following cells bind their tag-stripped digits in both the engine and the witness (not probed as findings):
  - comments that contain tags;
  - `display:none` spans.
- Footnote containment is a substring test: a negated or extended note still counts. The engine and the witness share this; a probe was not written.
- Removing a non-pinned table (e.g. balance_sheet) is admitted per R116's "required = pinned" wording; the decision owner should confirm that is intended under (b).
- The `_eps_row` ValueError path (two EPS rows) was not triggered by my construction.
- A Q2- or Q1-based mutation sweep was not run: all mutation probes are FY26 Q3 plus the Q1 prior table.
- CI itself (hosted 3.12 run) was not observed. Only a local 3.12 venv was used.

## DEVIATIONS

- The FY27-scope probe registers a synthetic `Release` in the imported suite module's `RELEASES` dict. This happens in memory only; no file was changed.
- 4 of the 43 failures are probe artefacts, marked above as lawful fail-closed refusals, not findings. The finding count excludes them.
