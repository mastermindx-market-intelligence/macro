# Opus re-audit R4: CDV-1 T1 F1-Q envelope at 2a8d1eb1a9c7d2e0820adeb3e6fc62194d486580 (PR #7905)

Mode: READ_ONLY. Nothing in the repository was edited, committed or pushed. The only `gh` calls were the two family-12 reads, each made once.
Probes: `test_envelope_audit_probes_r4.py` (1133 cases). Logs: `probesA.log`, `probesB.log`, and `old_r{1,2,3}_probes.log`. Exploration: `ex1.py`–`ex3.py`, `tok.py`, `dump.py`.

## STATUS: REJECT

Four blockers, three majors for the seat to rule on, and one gap: hosted `ci` has not run.

## RESULT
| id | bar / sev | probe | observed | expected |
|---|---|---|---|---|
| P1 | a (+R135) BLOCKER | `test_p1_glued_nbsp_reference_never_enters_the_span[*]` (4) | `>&nbsp1&#46;63` binds DIL 1.63 with span `&nbsp1&#46;63` (the same on Q2 CORE and Q1 SALES `&nbsp3&#37;`); the validator refuses the extractor's own workspace | span `1&#46;63`, or unlocated; the workspace validates |
| P2 | c BLOCKER | `test_p2_one_byte_seam_tamper_is_refused[*-narrow_r]` (32 of 342) | a span narrowed by one byte through the R143 seam (`7%`->`7`, `(1)%`->`(1)`) is ACCEPTED on every non-zero percent row of Q1, Q2 and Q3 | refused |
| P3 | e (R147) BLOCKER | `test_f8_core_recon_title_year_contradicted_by_a_year_row`, `test_f8_highlights_primary_year_contradicted` | Q3 CORE binds 1.59 under years {2026 (title), 2025 (row)}; Q3 PCORE and PDIL bind 1.54 and 1.54 under years {2025, 2026} in highlights | unlocated |
| P4 | a (+R135) BLOCKER | `test_p4_...infinity`, `test_f11_fuzz...[True-17-*]` (6) | a 400-digit figure in both statements binds `value = inf`; the validator refuses the extractor's own workspace ("must be finite") | never a non-finite present fact; self-validates |
| M1 | c MAJOR, seat to rule | `test_f14_relocation_into_a_comment_is_refused`, `..._attribute_value_is_refused` | a seam relocation of DIL onto `1.63` inside a comment, or inside `title="1.63"`, is ACCEPTED | refused (text that is not printed is not "another literal printing the same value", which is the scope of R153's limit) |
| M2 | a/b MAJOR, seat to rule (shared with witness) | `test_f9_close_tag_in_comment_inside_earnings_never_binds_a_hidden_row` | `<!-- </table> -->` closes the earnings table in `_table_spans`, so a second Diluted row (9.99) that a browser prints is invisible to the engine, and DIL binds 1.63 | unlocated (R130: two candidate rows) |
| M3 | a (unit) MAJOR, seat to rule | `test_f6_OBSERVE_per_share_value_beside_percent_unit_cells_in_both_statements` | both statements print Diluted EPS as `% | 1.63` (a separate unit cell), and it binds 1.63 usd_per_share | not present as usd_per_share |

### P1: R143's start-boundary rule is not implemented (`engine/company_intelligence/pg_envelope.py:979`)
- The stdlib reference grammar (`_UNIT`, `:29`) lets `&nbsp` without a semicolon absorb the following name characters. `&nbsp1` is one unit that decodes to `"\xa0"+"1"`, and both decoded characters carry the same extent (`:963`).
- `span_start = extents[first][0]` (`:973`) is therefore the start of the reference.
- The guard at `:979` requires `extents[first-1][0] < extents[first][0]`, and that is never true for two characters of one unit, whose extents are identical. Under the unit model, the line is dead code.
- The other checks all pass:
  - contiguity (`:974-976`), because `.` comes from `&#46;`;
  - raw whitespace (`:983`);
  - the `_text` re-read (`:985`), which strips the decoded space.
- R143 breached: "a span boundary falls inside a unit whose decoding extends past the literal" and "the span holds whitespace" must both make the literal unlocated. The receipt is not the printed literal (bar a), and the extractor's output does not self-validate (`economic_observations.py:249` refuses it correctly).
- A single-character literal needs no `&` terminator, so `&nbsp7` followed by a separate `%` cell is the same construction.

### P2: the independent check accepts a sub-span of the literal (`engine/company_intelligence/economic_observations.py:246-256`)
- `7` parses as percent 7.0, which equals the row's value. It holds no `<`, no whitespace and no `$`.
- The R136 replay shares the seam, so it agrees with the narrowed span.
- The sweep covered 57 present rows × 6 one-byte moves = 342 tampers:
  - 32 were accepted, all of them `narrow_r` on percent rows;
  - every per-share row and every `&#8212;%` row was refused.
- R143 defines the span as "first raw byte of the literal's first unit to the last raw byte of its last unit". A span without the `%` unit is not the literal.
- Family 4 of the commission requires every one-byte narrow to be refused. R153's recorded limit covers "another literal printing the same value", not a sub-span of the same literal.
- Closable within R143's constraints (it reads only the source and the grammar): require the span to be maximal. The byte after it must not be `%`, `)`, a digit or `.`, and the byte before it must not be `$`, `+`, `(` or a digit.

### P3: R147 is bypassed in two places (`pg_envelope.py:748-749` and `:756`)
- `year = title.year if title.year is not None else header_year` (`:756`): a period title that carries a year overrides the R147 agreement test, so `_matching_header` returning `None` (`:765-766`) has no effect on title-bearing tables such as core_reconciliation.
  - Construction: a row `<td colspan="30">2025</td>` under the 2026 title. It is year-only, so it changes no signature.
  - Result: CORE binds 1.59.
- `if not titles: return not required` (`:748-749`): highlights has no period title, so its year-header pins never reach `_matching_header`.
  - Construction: a row printing `2026` over both of the highlights 2025 columns.
  - Result: PCORE (highlights is the primary statement) and PDIL (highlights is the second) both bind.
- R147: "Collect the years ... period titles included. With two or more, the cell has no header year ... any pin that needs a year cannot locate it." The bound values happen to equal the originals, so the bar is (e) "a year is bound from contradictory headers (R147)".

### P4: float overflow is bound as a present value (`pg_envelope.py:863-864`, `:925-929`)
- `float("9"*400)` is `inf`, both statements agree, and `extract` emits `value: inf` (`:1031-1033`), with no finiteness check on the wrapped path. S0 has one at `pg_profile.py:1986`.
- The printed figure is finite, so `inf` is a wrong value (bar a), and the validator (`economic_observations.py:189-190`) refuses the extractor's own workspace (R135).
- `_validate_envelope_span` reuses the engine's `_literal` (`:254`), so this `_literal` defect is shared, and only the structural `isfinite` check catches it.

### M1–M3 (seat to rule)
- M1: R153's limit, as recorded, is "a seam shift onto another literal printing the same value". The check (`economic_observations.py:246`) also accepts text that is not printed: a comment interior, or an attribute value inside a start tag, because those bytes hold no `<`.
  - Rejecting them needs a local scan of the source, with no engine call. Relocation onto the printed highlights `1.63` (`test_f14_OBSERVE_same_value_relocation_accepted_limit`) is the recorded limit, and it is accepted.
  - Judgment: that limit is consistent with R143's text. Bar (c)'s "a span shifted through the seam" is broader than any check R143 permits. The seat should narrow bar (c) explicitly, or require location evidence in the independent check.
- M2: `_TABLE_OPEN`, `_TABLE_CLOSE`, `_ROW` and `_CELL` (`:18-21`) scan through comments, while R143's tokenizer treats a comment as markup that is not printed. The witness `tables()` has the same behaviour, so this is shared (R131-class). The seat should rule whether R149's "end tag" excludes comment contents.
- M3: R145 and R152 speak only of a marker inside the cell. A separate `%` unit cell beside a per-share value in both statements is admitted as usd_per_share.

## Family results (run / failed; artefacts excluded from findings)
| family | run | failed | notes |
|---|---|---|---|
| P1 (3: tokenizer) | 4 | 4 | P1 |
| 4 validator independence / seam ±1 | 342 | 32 | P2; the independent check has no engine call except `_literal` (confirmed by reading `:220-256`) |
| 3 layout variants (19 edits × 8 targets, Q1–Q3, both statements) | 152 | 8 | all 8 are `&aaaa…(33);`, which prints letters, so the lawful result is `unknown_table` (probe artefact) |
| 3 references inside the literal (digits, `.`, `%`, dash, `(`, no-semicolon) | 45 | 0 | 27 skipped where the literal lacks the character; printed twice in a cell -> unlocated (1 pass) |
| 0 N3 / 5 determinism (Q1–Q3 × orig/drop3/rep3/drop_rep; seeds 0,1,4,7 × C/de_DE/fr_FR/tr_TR; built in one process, validated in two others) | 12 + 1 | 0 | one code per body; every cross-process validation passed; no `strftime`/`%B`/`%b`, and no iteration over a role set |
| 6 unit rule (entity/named markers on either statement, `<span>%</span>`, `—%` per share, disagreeing pairs = witness) | 11 | 1 | M3 |
| 7 TYPE/marker lines (CR inside the value, lone CR, lowercase tag, marker substring, CRCR) | 6 | 0 | |
| 8 R147 | 5 | 2 | P3; year-in-comment controls pass on Q1–Q3 |
| 9 R148/R149 (13 FY/duration spellings, 10 duration relabels over 4 quarter roles, comment `</table>`, phantom cells in a comment, 4 table-markup variants, R148-amended round-1 control) | 30 | 1 | M2; FY spellings `FY&#160;2026`, `FY26`, `Fiscal Year 2025/26`, `F2026` and `fiscal-year 2026` never fold to `<period>` |
| 10 refused-document leaf tamper, Q1/Q2/Q3 | 3 | 0 | every leaf tamper and deletion refused (R151 floor met) |
| 11 fuzz (42 edits × 6 targets × one/both statements) + differential | 504 | 6 | P4. No exception escaped `build_event_workspace` or the validator. Differential `html.unescape(span) == _text(span)` and parse over every present row: 0 divergences outside P1/P4 |
| 11 title fuzz (Q1 earnings) | 10 | 3 | all 3 are lawful `unknown_table:t4` refusals (probe artefact); no exception |
| 13 accession | 1 | 0 | the `_source_only_accession` value never reaches a row, the workspace or a validator result |
| 14 amendments | 4 | 3 | (ii) passes; (iii) is the recorded limit, plus M1 ×2 |

## Earlier probe files re-run at HEAD (3.14)
- Round 1: 4 failed, 99 passed.
  - Three are the named artefacts, unchanged.
  - The fourth is `test_f10_control_q4...`, as originally written. Under R148's amended reading, the r4 probe `test_f9_r148_amended_round1_control_table14_matches_no_role` passes: table 14 of FY25Q4 and FY26Q4 matches no role.
- Round 2: 1 failed, 67 passed. The failure is B11, which R139 supersedes.
- Round 3: 4 failed, 220 passed, 1 skipped (687 s), against 36 failed at 80bd14fce4a.
  - `test_n4...[Q3-DIL-0-1.63%-second:1.64]` now gives a conflict, which R152 sanctions.
  - The three display:none failures are the recorded artefacts (R151).
  - N1–N8 are closed on every original construction.

## Family 14
- (i) The R3 suite went from 92 to 95 cases:
  - the fifth R145 parameter became the agreeing primary-side case;
  - `test_r152_*` added 2 cases;
  - `test_r153_*` added 1.
  - No other case changed; the diff is limited to those hunks. R152 is the minimal order that satisfies the round-0 witness: compare with markers ignored first, then apply the unit rule to an agreeing pair.
  - The only outcome that moves is from unlocated to conflict on a disagreeing marked pair. Both are absences, so no present fact is newly reachable. That is confirmed by family 6, where no marker-bearing cell reached a present fact.
- (ii) With the inline R153 rule removed in memory (in a subprocess, by an exec of the cut function), exactly `test_r153_validator_parses_the_span_for_the_rows_unit` fails. The R153 rule makes no engine call (`economic_observations.py:251-253`).
- (iii) See M1.

## Code review (non-blocking)
- `pg_envelope.py:979` is dead code, the cause of P1. `:981` fires only on identical extents.
- Pre-existing vocabulary tokens that no F1-Q original label produces:
  - `'<period>,<period>'`, in 6 roles;
  - `earnings:'<period>'`;
  - `cash_flows:'<period>'`;
  - `prior_core_reconciliation:'othernon-operatingincome/(expense),net'`.
  - They were present at 36beacf3da1 and 80bd14fce4a. None appears in any frozen probe. They widen admission, and they could be pruned.
- The R150 cleanups are all confirmed in the diff:
  - `derive_outcomes`, `_year_over`, the `ReceiptError` import, the unreachable `missing` loop and the third branch of `_headers_over` are deleted;
  - an empty `_eps_row` label short-circuits (`:803`);
  - the accession literal is replaced by the source-derived value (`economic_observations.py:274`).
- `_receipt`'s `decoded.index` (`:971`) cannot raise: `words == [cell.text]` guarantees the substring, and `len(extents) == len(decoded)`. Confirmed over 504 fuzz bodies, 152 layout bodies and 45 reference bodies with no exception.

## EVIDENCE
- HEAD is 2a8d1eb1a9c7d2e0820adeb3e6fc62194d486580, and the porcelain is empty.
- `git diff --stat 1167670bf2d 2a8d1eb1a9c -- tests/ research/ .github/` is empty.
- `git log d5e42eb4ddf..2a8d1eb1a9c -- tests/ research/` lists `1167670bf2d` and `8f312130a80`.
- Suites (`runs.sh`):

| suite | 3.12 (venv312_min) | 3.14 (venv_t1) |
|---|---|---|
| F1 | 46 passed | 46 passed |
| R1 | 125 passed | 125 passed |
| R2 | 70 passed | 70 passed |
| R3 | 95 passed | 95 passed |
| gate line | `1160 passed, 174 skipped` (119 s) | `1160 passed, 174 skipped` (115 s) |

- `curated_exclusive` on 3.12: `2 passed, 119 deselected`.
- a5a and capital-structure on /opt/homebrew python3.12: `213 passed`, and the per-test diff against `baseline_a5a_cs_f8e4af5.txt` is empty (rc=0).
- The r4 probe runs: batch A gave `3 failed, 17 passed`; batch B gave `57 failed, 1027 passed, 27 skipped`; the follow-up gave 2 failed (M3 and P4).
- Hosted CI for 2a8d1eb1a9c, 10 check-runs:
  - fence-pack, ci-authority and ci-authority/main: success;
  - ci-authority/codex/merge-queue-pilot: failure (known, non-binding).
  - No `ci-pack-*` and no `ci-gate` check-run exists: `ci` run 36152784715 is `pending`, and the d5e42eb4ddf `ci` run 36140847440 is still `in_progress`.

## GAPS
- Hosted `ci` at the head has not started, so there is no `ci-pack-*`, no `ci-gate` and no earnings-economic-dossier pack conclusion. I did not poll.
- Family 9 duration relabels ran on Q3 only; the FY labels ran on the Q3 organic reconciliation only.
- Family 10 swept refused-document rows. Present, unlocated and conflict rows were not re-swept this round; the round-3 sweep of them passed, and the replay code is unchanged apart from the accession.
- The families 3 and 11 fuzz used 6 targets, not every pinned cell.
- M1–M3 depend on seat rulings.

## DEVIATIONS
- The first continuation hit the turn limit before the report was written, and the report was then written incrementally.
- 14 probe failures are artefacts, not findings: 8 × `long_named_ref_33` and 3 × title fuzz, where the probes did not allow a lawful `unknown_table` refusal; and 3 × round-3 display:none. One M3 probe first errored for want of a `$` cell and was corrected, then re-run.
