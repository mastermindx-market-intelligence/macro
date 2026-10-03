# Opus re-audit R7: CDV-1 T1 F1-Q envelope at b6808dfcc166afd323ba4dabbb824fa30c1d9ee1 (PR #7905)

MODE: READ_ONLY. The round ran as four independent Opus auditors, one per family group, all on the same head.
- Each group's report follows verbatim, in group order. Probe files and raw outputs stayed in the seat's scratch directory. Nothing was written inside the worktree.
- G1, G2 and G3 each record `git rev-parse HEAD` at the head and an empty `git status --porcelain` before their first run and after their last.
- **Two reports did not reach a final draft.**
  - G1's header still reads "INTERIM"; its "Final state" section records the verdict, the head and a clean worktree after its last run.
  - G4's report is a working draft whose status line reads PENDING. Its run ended at the Opus weekly usage limit before a closing pass. Its blocker, G4-B1, is complete: code, construction, reader, expectation and controls. It also records G4-m1 (the root of G4-B1), a nit G4-n1 and an observation G4-O1, and leaves one note about the seat's round-6 testimony unclassified.
  - After the round, the seat confirmed the worktree at `b6808dfcc16…` with an empty `git status --porcelain`.

## STATUS: REJECT (G1, G2 and G3; G4's draft carries one blocker)

| group | families | status | blocking | other findings |
|---|---|---|---|---|
| G1 | 0 (round-6 G1 findings), 3, 9, 15, 16 | REJECT | G1-B1, G1-B2 | G1-m1 (minor) |
| G2 | 0 (round-6 G2 findings), 4, 5, 10, 11 | REJECT; family 5 and parts of 10 and 11 not concluded | G2-B1, G2-B3, G2-B4, G2-B5 | G2-m2 (minor); G2-O1 (observation) |
| G3 | 0 (round-6 G3 findings), 1, 2, 6 (units), 8 (years), the Q1–Q3 sweep | REJECT | G3-R7-B1 | G3-R7-m1 (minor); O1–O3 (observations) |
| G4 | 0 (integrity), 12, 13, 14 | PENDING (working draft) | G4-B1 | G4-m1 (minor); G4-n1 (nit); G4-O1 (observation); a testimony note, unclassified |

The seat's ruling on every finding is in `SEAT_RULING_T1_ENVELOPE_R7_2026-09-28.md`, beside this record.

---

## Group G1: families 0, 3, 9, 15 and 16 (verbatim)

# OPUS T1 envelope audit, round 7, group G1 (families 0-G1, 3, 9, 15, 16) at b6808dfcc166afd323ba4dabbb824fa30c1d9ee1

Status at writing: INTERIM. Items marked PENDING are background runs whose logs are named below; read them to close.

## Pre-run state
- `git rev-parse HEAD` = b6808dfcc166afd323ba4dabbb824fa30c1d9ee1; `git status --porcelain` empty (before first run).

## Family 0 (G1 part): round-6 G1 probe file re-run at HEAD (/opt/homebrew/bin/python3 3.14.7 + html5lib; the file imports html5lib at module level, so 3.12 cannot run it)
- non-f3 slice (1,034 cases): **122 failed, 912 passed** (log `r6_main.log`). Failure set = 114 structural-tag-in-`--!>`/unterminated-comment cases refused `unknown_table` before R163 (probe expects detail `comment`) + `b1_variant[Q3-segment_cell]` (unknown_table:t11) + `b1_variant[Q2-title_cell]` (StopIteration in the probe) + 6 `test_g1_B1_tbody...` label cases (precondition needs an admitted doc). This is exactly the R6 record's classification; none is a present fact.
- f3 Q1 slice: **1,615 passed** (log `r6_f3_q1.log`).
- f3 Q2+Q3 slice: PENDING (log `r6_f3_q23.log`). Seat testimony total 122 failed / 5,761 passed requires this slice to be all-pass.

## Family 16: readers over every code point Unicode 3.2 assigns (234,737 code points), 3.11 / 3.12 / 3.14
- Script `cmp_unicode.py`, diff `cmp_diff.py`. Readers compared: isnumeric/isdigit/isdecimal/isspace/isalnum/isprintable/isalpha, re `\d \s \w`, casefold/lower/upper, NFKC/NFC, re.I matches of k/s/i/t, `<table\b` word boundary, `str.split` count, `int()`, `ucd_3_2_0.category`, isidentifier, strip.
- 3.12 vs 3.14: only `isnumeric` on 两 京 俩 倆 拐 洞 皕 秭 鈎 钩 and `upper` on ƛ ɤ. **Seat comparison confirmed.** 3.11 vs 3.12: identical on every reader (digest 2271a26f566bf705 on both).
- Engine readers that depend on the interpreter's Unicode: `_figure_character` (isnumeric, pg_envelope.py:911), NFKC in `_seen` (1110), `\d` in `_literal` (1032/1035, guarded by the ASCII check at 1030), `_parse_period_title` (842/850, `\d` + int()), `_SPAN_PATTERNS` (25), `_ROW`/`_CELL`/`_TABLE_CLOSE` `\s` (21-23), casefold in `_norm` (155). None differs on a 3.2-assigned code point between 3.12 and 3.14 other than the ten ideographs, which the figure test reads alike via `Lo`.
- Later-Unicode argument: not machine-checkable (no interpreter > 16.0). The figure test only covers future numerics that are `Lo`; a 3.2-assigned non-`Lo` character given a numeric value later, or a White_Space change (precedent: U+180E was Zs in 3.2, Cf since 6.3), would not be caught by R178's rule. Recorded as GAP, not a finding.
- Documents placing 29 characters (the 12 differing, 財, U+180E, U+E000, ſ, K, ², ½, ①, Ⅻ, ٢, ２, U+0F33, U+09F4, 〇, 一, U+00AD, U+200B) in 7 read positions: PENDING (`test_f16_*`, digests in `f16_312.tsv` / `f16_314.tsv`, logs `p7_312.log` / `p7_314.log`).

## Unicode case folding / whitespace in re.I patterns (exploration `explore.py`, 3.12 and 3.14 identical)
- `_RAW_TEXT_CLOSE['script']` matches `</ſcript>`, `_SPAN_PATTERNS['colspan']` matches `colſpan`, `_TABLE_CLOSE` matches `</table\x85>` (the engine's patterns do fold/space-match), but R163's ASCII grammar refuses every such document at admission: `</ſcript>` -> tag, `</td\x85>` -> tag, `</td >` -> tag, `</tr\x1c>` -> tag, `colſpan` -> tag, `colspan="٢"` -> span. Seat claim confirmed on these.

## Findings so far
- **G1-m1 (minor, bar d robustness; pre-existing, not introduced by R168-R178).** `_grid` (pg_envelope.py:389-391, `for span_col in range(col, col + colspan): carry[span_col] = ...`, and `take_carried` 370-372) expands a `rowspan>1` cell's colspan into one dict entry per column before admission; R163's `_SPAN_LIMITS` check runs only at the end of `_admission`. Measured: colspan 1,000 -> 0.30 s, 100,000 -> 0.37 s, 1,000,000 -> 0.93-0.96 s (3.12 and 3.14), i.e. linear in the attribute's numeric value; a 10+-digit colspan exhausts time/memory before refusal. html5lib clamps colspan to 1000. Not demonstrated to raise (not run at a size that would load the shared host). Probe `test_g1_m1_an_oversized_colspan_is_refused_without_expanding_the_grid` (colspan 10^7 must refuse `span` in < 3 s): PENDING.
- Other family 0 / 3 / 9 probes (868 cases in `test_envelope_audit_probes_r7_g1.py`): PENDING.

## Family 15 (html5lib 1.1 differential)
- Corpus (iii): seeded fuzz `fuzz7.py`, seed 20260926, 5,000 documents, R6 constructs + 55 new (R171 end tags, isindex spellings, R172 characters/references, R178 characters incl. U+1CCF0/&#x1F4B2;/两/京/財/U+0870/&#x20C0;, ſ/K, `</ſcript>`, R175 `&amp;#36;`/`&amp;amp;`/`&amp;#160;`, U+180E, U+E000, U+00AD). Output `fuzz7.jsonl`, log `fuzz7.log`: PENDING. Aggregate with `agg7.py fuzz7.jsonl`.
- Corpus (ii): every source the seven frozen suites send to `build_event_workspace`, `capture7.py` (starts when the R6 re-run ends, via `after_r6.sh`), output `capture7.jsonl`, log `capture7.log`: PENDING.
- Corpus (i): the six originals are inside corpus (ii).

## Batch update (turn 23)
- HEAD re-checked: b6808dfcc166afd323ba4dabbb824fa30c1d9ee1, porcelain lines:        0.
- R7 G1 probes on 3.12 (venv312_min), log p7_312.log: `178 failed, 690 passed in 821.94s (0:13:41)`
- Failures on 3.12 (if any):
```
 test_f0_B2_odd_character_beside_a_pinned_literal_is_refused[&#11-before-Q1-pg_reported_sales_growth_pct]
 test_f0_B2_odd_character_beside_a_pinned_literal_is_refused[&#11-before-Q2-pg_core_eps]
 test_f0_B2_odd_character_beside_a_pinned_literal_is_refused[&#11-before-Q3-pg_prior_diluted_eps]
 test_f16_character_in_every_read_position_is_read_alike[\u4e24-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u4e24-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u4e24-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u4e24-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u4e24-note]
 test_f16_character_in_every_read_position_is_read_alike[\u4e24-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u4eac-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u4eac-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u4eac-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u4eac-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u4eac-note]
 test_f16_character_in_every_read_position_is_read_alike[\u4eac-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u4fe9-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u4fe9-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u4fe9-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u4fe9-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u4fe9-note]
 test_f16_character_in_every_read_position_is_read_alike[\u4fe9-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u5006-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u5006-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u5006-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u5006-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u5006-note]
 test_f16_character_in_every_read_position_is_read_alike[\u5006-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u62d0-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u62d0-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u62d0-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u62d0-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u62d0-note]
 test_f16_character_in_every_read_position_is_read_alike[\u62d0-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u6d1e-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u6d1e-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u6d1e-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u6d1e-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u6d1e-note]
 test_f16_character_in_every_read_position_is_read_alike[\u6d1e-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u7695-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u7695-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u7695-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u7695-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u7695-note]
 test_f16_character_in_every_read_position_is_read_alike[\u7695-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u79ed-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u79ed-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u79ed-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u79ed-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u79ed-note]
 test_f16_character_in_every_read_position_is_read_alike[\u79ed-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u920e-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u920e-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u920e-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u920e-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u920e-note]
 test_f16_character_in_every_read_position_is_read_alike[\u920e-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u94a9-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u94a9-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u94a9-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u94a9-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u94a9-note]
 test_f16_character_in_every_read_position_is_read_alike[\u94a9-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u019b-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u019b-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u019b-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u019b-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u019b-note]
 test_f16_character_in_every_read_position_is_read_alike[\u019b-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u0264-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u0264-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u0264-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u0264-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u0264-note]
 test_f16_character_in_every_read_position_is_read_alike[\u0264-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u8ca1-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u8ca1-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u8ca1-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u8ca1-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u8ca1-note]
 test_f16_character_in_every_read_position_is_read_alike[\u8ca1-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u180e-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u180e-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u180e-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u180e-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u180e-note]
 test_f16_character_in_every_read_position_is_read_alike[\u180e-outside]
 test_f16_character_in_every_read_position_is_read_alike[\ue000-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\ue000-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\ue000-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\ue000-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\ue000-note]
 test_f16_character_in_every_read_position_is_read_alike[\ue000-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u017f-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u017f-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u017f-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u017f-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u017f-note]
 test_f16_character_in_every_read_position_is_read_alike[\u017f-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u212a-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u212a-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u212a-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u212a-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u212a-note]
 test_f16_character_in_every_read_position_is_read_alike[\u212a-outside]
 test_f16_character_in_every_read_position_is_read_alike[\xb2-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\xb2-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\xb2-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\xb2-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\xb2-note]
 test_f16_character_in_every_read_position_is_read_alike[\xb2-outside]
 test_f16_character_in_every_read_position_is_read_alike[\xbd-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\xbd-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\xbd-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\xbd-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\xbd-note]
 test_f16_character_in_every_read_position_is_read_alike[\xbd-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u2460-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u2460-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u2460-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u2460-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u2460-note]
 test_f16_character_in_every_read_position_is_read_alike[\u2460-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u216b-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u216b-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u216b-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u216b-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u216b-note]
 test_f16_character_in_every_read_position_is_read_alike[\u216b-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u0662-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u0662-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u0662-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u0662-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u0662-note]
 test_f16_character_in_every_read_position_is_read_alike[\u0662-outside]
 test_f16_character_in_every_read_position_is_read_alike[\uff12-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\uff12-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\uff12-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\uff12-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\uff12-note]
 test_f16_character_in_every_read_position_is_read_alike[\uff12-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u0f33-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u0f33-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u0f33-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u0f33-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u0f33-note]
 test_f16_character_in_every_read_position_is_read_alike[\u0f33-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u09f4-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u09f4-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u09f4-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u09f4-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u09f4-note]
 test_f16_character_in_every_read_position_is_read_alike[\u09f4-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u3007-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u3007-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u3007-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u3007-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u3007-note]
 test_f16_character_in_every_read_position_is_read_alike[\u3007-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u4e00-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u4e00-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u4e00-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u4e00-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u4e00-note]
 test_f16_character_in_every_read_position_is_read_alike[\u4e00-outside]
 test_f16_character_in_every_read_position_is_read_alike[\xad-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\xad-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\xad-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\xad-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\xad-note]
 test_f16_character_in_every_read_position_is_read_alike[\xad-outside]
 test_f16_character_in_every_read_position_is_read_alike[\u200b-cell_before]
 test_f16_character_in_every_read_position_is_read_alike[\u200b-unit_neighbour]
 test_f16_character_in_every_read_position_is_read_alike[\u200b-banner_alone]
 test_f16_character_in_every_read_position_is_read_alike[\u200b-banner_after_year]
 test_f16_character_in_every_read_position_is_read_alike[\u200b-note]
 test_f16_character_in_every_read_position_is_read_alike[\u200b-outside]
 test_g1_m1_an_oversized_colspan_is_refused_without_expanding_the_grid
```
- R7 G1 probes on 3.14 (venv_t1), log p7_314.log: `......` (PENDING if not a summary line; digests in f16_314.tsv; compare with `diff <(cut -f1-3 f16_312.tsv|sort) <(cut -f1-3 f16_314.tsv|sort)`).
- R6 f3 Q2+Q3 slice (r6_f3_q23.log): `...................`
- fuzz7.jsonl lines so far:     3630 of 5,000 (PENDING; run `python3 agg7.py fuzz7.jsonl capture7.jsonl`).
- capture7.log tail: ``

## Batch update (resume, turn R1) -- 3.12 probe run classified (log p7_312.log: 178 failed, 690 passed in 821.94s)
- 174 x `test_f16_*`: PROBE BUG, not a finding. The assertion (no wrong bind, validates) passed; the digest writer then raised
  `TypeError: '<' not supported between 'str' and 'NoneType'` at probe line 293 (`sorted(det)` over a set holding None).
  The 29 `label` cases (refused unknown_table:t9, no None in det) wrote digests. Fixed writer (`sorted(map(str, det))`);
  f16 re-run on both interpreters: PENDING (logs p7f16_312.log / p7f16_314.log, digests f16_312.tsv / f16_314.tsv).
- 3 x `test_f0_B2[&#11-before-*]`: PROBE CONSTRUCTION, not a finding. A semicolon-less `&#11` placed before a literal that
  starts with a digit absorbs it (`&#111.63` -> `o.63`); html5lib reads it the same way; the engine leaves the metric
  unlocated (R154, fail-closed) and the workspace validates. Every other G1-m2 form (`&#x0B;`, `&#011;`, raw \x0b; and `&#11`
  after the literal) is refused `character`.
- 1 x `test_g1_m1_*`: EXPECTED failure at HEAD, see G1-m1 above.
- Everything else passed on 3.12: family 0 B1 (72), B3 (16), B2/m1/m2 (141 of 144), M1 (11), S1 (12), R178 (24);
  family 3 exact-extent binds, printed-twice, odd characters outside cells; family 9 R171-tags-in-comments (90) and the
  F2-A fiscal-year transplant (42 role x release cases, every annual table into every pinned role of Q1-Q3).
- 3.14 run (p7_314.log): PENDING. R6 f3 Q2+Q3 slice (r6_f3_q23.log): PENDING (~80%). fuzz7: 4,027 / 5,000 written, PENDING.
  capture7: waits for the R6 re-run to end, PENDING.

## Batch update (resume, turn R2)
- **G1-m1 measured at 10^7:** `test_g1_m1_*` failed on 3.12 with `({'envelope_refused:markup_unreadable:span'}, 7.94 s)` —
  the refusal is right, the cost is linear in the colspan's value (0.30 s at 10^3, 0.93 s at 10^6, 7.94 s at 10^7).
- **f16 re-run with the fixed digest writer, 3.12 (p7f16_312.log): 203 passed.** Nothing binds a wrong value and every
  workspace validates for 29 characters x 7 read positions. 3.14 re-run: PENDING (p7f16_314.log); digests f16_3xx.tsv.
- **R178 order by other characters (34 new cases, 3.12 and 3.14: 34 passed each).** With U+1CCF0, &#x11BF0;, U+0870 or a
  `&#x20C0;` comment added, `type_ex_99_2` and `generator_removed` keep their own codes and the five later frozen
  cases are refused `character`. A Sunuwar/outlined digit inside colspan/rowspan (which `\d` in `_SPAN_PATTERNS`,
  pg_envelope.py:25, reads on 3.14 and not on 3.12) is refused `character` alike on both, with no exception.
- **Decode sites (S1, R175) read structurally:** in pg_envelope.py `html.unescape` is called in `_units` (145, once per
  reference unit) and in R178's admission test (741, whole source, check only). Cell text is `_text` of the raw cell
  once (388); `_norm` (155) and `_parse_period_title` (841-851) no longer decode. No second decode path remains.
- **Family 15 fuzz (fuzz7.py, seed 20260926, 5,000 docs, /opt/homebrew/bin/python3 3.14.7 + html5lib 1.1), fuzz7_agg.txt:**
  0 exceptions; 797 admitted; **0 admitted documents with any divergence** (pinned 0, other 0, structural 0);
  0 admitted documents on which `_unreadable_markup` names a kind (R163 is never bypassed); 4,203 refused
  (markup_unreadable 2,621 by kind: table 953, tag 448, element 419, character 381, span 266, comment 70, lt 59, gt 22,
  grid 3; unknown_table 1,582). Every new R171/R172/R178/R175 construct that was admitted sat outside the cells
  (e.g. U+2028 x7, U+180E x8, ſ x4, K x5, U+E000 x6, U+00AD x6) and moved no cell. Refused-with-reader-equal-pins
  (coverage-cost candidates): 2,160 docs; single-edit top classes listed in fuzz7_agg.txt.
- Note-region differential (`note_diff.py`, seed 20260927): PENDING (note_diff.out).

## Batch update (resume, turn R3)
- **Round-6 G1 probe file at HEAD, complete** (/opt/homebrew/bin/python3 3.14.7; logs r6_main.log, r6_f3_q1.log, r6_f3_q23.log):
  non-f3 122 failed / 912 passed; f3 Q1 1,615 passed; f3 Q2+Q3 3,234 passed. **Total 122 failed, 5,761 passed of 5,883 —
  the seat's testimony reproduces exactly**, and the 122 are the R6 record's classes (114 comment-form exact-detail
  expectations refused `unknown_table` first, `b1_variant[Q3-segment_cell]`, `b1_variant[Q2-title_cell]` StopIteration,
  6 `test_g1_B1_tbody` label preconditions). No failure is a present fact. 3.12 cannot run it (module-level html5lib).
- **R7 probe file, full run on 3.14 (p7_314.log): 178 failed, 690 passed** — the identical failure set to 3.12
  (174 f16 digest-writer TypeErrors, 3 `&#11`-before-a-digit construction cases, 1 G1-m1). Both classified above.
- **f16 re-run 3.14 (p7f16_314.log): 203 passed. Digests identical on 3.12 and 3.14 for all 203 (character, position)
  cases** (`diff <(sort -u f16_312.tsv) <(sort -u f16_314.tsv)` empty; the 3.14 file holds 29 duplicate label rows the
  first full run appended). Outcome classes: 21 figure characters in a banner leave exactly the six EPS pins unlocated
  (alone) or the current-year ones (after `2025 `); the 8 non-figure characters (ƛ ɤ U+180E U+E000 ſ K U+00AD U+200B)
  bind; cell_before -> DIL unlocated; label -> unknown_table:t9; unit neighbour / note / outside -> bind.
- capture7 (corpus ii): first attempt failed after the suites ran (`ModuleNotFoundError: g1lib`, harness path bug);
  relaunched with an explicit sys.path, PENDING (capture7.log / capture7.jsonl).

## Batch update (resume, turn R4) -- NEW BLOCKING FINDINGS in the note the envelope reads
Search: `note_diff.py` (seed 20260927) inserted all 223 fuzz7 constructs at 8 positions around the Q3 prior-year note
(1,784 docs): refused 1,274; engine gate & reader note 450; neither 42; reader-only 1 (coverage cost);
**engine gate while the html5lib reader does not read R157's sentence: 17** — script/style/title/iframe/noscript/
noembed/noframes (7 forms: html5lib's itertext includes them but a browser does not print them, so these are reader
artefacts, consistent with R173) and **xmp, textarea (printed) and &#1;, &#127;, &#xFFFF;, &#xFDD0;, &#x10FFFF;, &#xFFFE;
(dropped by html.unescape, emitted by html5lib)**. Targeted probes then built:

- **G1-B1 (BLOCKER, bar b; introduced by R173).** R173 blanks the content of *every* raw-text element before reading the
  note (`_RAW_TEXT_ELEMENT`, pg_envelope.py:59, used at :1137), including `xmp` and `textarea`, whose content a reader
  prints (html5lib keeps it as text; a browser shows xmp as preformatted text and textarea as the control's value).
  Construction: in the Q3 original, `...reconciling items for Core EPS<xmp> except a $0.12 restructuring charge</xmp>.`
  The reader reads "...for Core EPS except a $0.12 restructuring charge." (verified with html5lib 1.1); the engine reads
  R157's sentence, the note gates PCORE's second statement, and PCORE binds 1.54 with the workspace validating, on 3.12
  and 3.14. Variants: textarea (same), `there were<xmp> not</xmp> no adjustments`, `no<textarea> material</textarea>`.
  Probe `test_g1_B1_r7_printed_raw_text_inside_the_note_is_not_blanked[4]` -- expected PCORE unlocated; observed bound.
  Controls (`test_r7_control_unprinted_raw_text_inside_the_note_is_blanked`, script/style/title/iframe): bind, pass.
  This is G1-M1's class mirrored: R173 closed "note read from text a reader never prints" and opened "note read without
  text a reader prints".
- **G1-B2 (BLOCKER, bar b; R172's class, outside R172's scope).** R172 refuses dropped references and odd characters only
  while `state == "cell"` (pg_envelope.py:281-286). The note is read outside every cell through `_text` -> `_units`
  (:145), where `html.unescape` returns '' for `&#1;`, `&#127;`, `&#xFFFF;`, `&#xFDD0;`, `&#x10FFFF;`, `&#xFFFE;`, and the
  html5lib reader emits the code point. `there were no&#1; adjustments` gates PCORE (binds 1.54, validates) on 3.12 and
  3.14. Probe `test_g1_B2_r7_a_dropped_reference_inside_the_note_does_not_gate[4]` -- expected PCORE unlocated or
  `character` refusal; observed bound. Severity follows the seat's R6 ruling of G1-B2 (a dropped reference beside a
  bound literal, likewise cosmetic in effect) as BLOCKER (b). Related, same scope gap, not separately probed as blocking:
  Python-whitespace-but-not-HTML-whitespace characters (\x0b, \x1c-\x1f, \x85, U+2028, U+3000) that R172 refuses in
  cells are admitted in the note and deleted by `_norm`'s `split()` (:155).

## Batch update (resume, turn R5) -- family 15 corpus (ii) and close-out
- **capture7 (seven frozen suites, 700 passed while captured; 488 distinct sources reaching build_event_workspace):**
  0 exceptions; 337 admitted; admitted / admitted-with-a-grammar-kind / admitted-with-any-divergence = 337 0 0.
  Refused 151 (by admission code in capture7_agg.txt). Corpus (i), the six originals, is inside it.
- Family-15 totals: 5,000 fuzz + 488 captured + 1,784 note-region docs = 7,272 documents; 1,134 admitted in fuzz+capture
  with 0 table/title divergences; the note region yields G1-B1/G1-B2 above (17 engine-gate/reader-no-note docs, 7 of
  which are reader artefacts for unprinted raw text).

## Final state
- HEAD after last run: b6808dfcc166afd323ba4dabbb824fa30c1d9ee1; porcelain lines: 0.
- Verdict for G1's families: **REJECT** on G1-B1 and G1-B2 (bar b, the prior-year note). Round-6 G1-B1, G1-B2, G1-B3,
  G1-M1 (by its original construction), G1-m1, G1-m2, S1 and R178's admission check are closed on their original
  constructions and on every variant built here. G1-m1 (R7, colspan cost) is minor.

---

## Group G2: families 0, 4, 5, 10 and 11 (verbatim)

# Opus T1 envelope audit — round 7, group G2 (families 0/G2, 4, 5, 10, 11)

Head `b6808dfcc166afd323ba4dabbb824fa30c1d9ee1`; `git rev-parse HEAD` = head and `git status --porcelain` empty before the
first run (confirmed). All runs from `$WT` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`, pytest `-p no:cacheprovider`,
at most four processes. Scripts and outputs live in this directory. Interpreters: `$MY/venv312_min` (3.12) and `$MY/venv_t1` (3.14.7).

STATUS (G2 scope): **REJECT** (bar c: G2-B1; bar d: G2-B3, G2-B4, G2-B5). Families 5 and parts of 10/11 not concluded; see GAPS sections below.

## Static read (family 4 independence)
- `_validate_envelope_span` (`economic_observations.py:287-332`), `_whole_printed_token` (`:257-284`) and `_printed_units`
  (`:233-254`) read only the source bytes, the row, `html.unescape`, `pg_envelope._literal` (literal grammar) and the constant
  name set `pg_envelope._RAW_TEXT_CLOSE` (`pg_envelope.py:44-47`, used only for its keys at `:229`). No call to the tokenizer,
  cell reader, receipt code, `_document`, `admit`, `extract` or the replay. **Independence holds.**
- The R176 handlers: `_validate_row_structure` `except (TypeError, ValueError)` (`:179`) wraps only `TypedAbsence(...)`;
  `_validate_envelope_rows` wraps only `json.dumps(dict(row), sort_keys=True)` (`:408-412`). Neither wraps source reading.
  Both end in `EconomicObservationError`. **But** three other raise paths remain unguarded (G2-B3/B4/B5).

## Family 0 (round-6 G2 findings)
- R6 probe file `$MY/audit_t1_envelope_r6/g2/test_envelope_audit_probes_r6_g2.py` at head: **11 failed, 7 passed** on 3.12
  (`11 failed, 7 passed in 9.96s`) and on 3.14 (`11 failed, 7 passed in 10.06s`). Matches the seat's testimony.
  - 11 FAILED = all eleven `test_g2_b1_relocation_outside_r166_list_is_refused[*]` (wrapper description, prose p, bare text,
    after `</html>`, title, textarea, xmp, iframe, noscript, noembed, noframes). These are the eleven R176 freezes as accepted.
  - 7 PASSED = the 3 G2-m1 cases and the 4 G2-B2 cases. **G2-m1 and G2-B2 closed on their original constructions.**
- Variants (`explore.py`, `explore_312.out`, `explore_314.out`; Q1, Q2, Q3; 187 lines each):
  - G2-m1 variants (int->float on `receipt.span_end_byte`, `locator.span_end_byte`, `receipt.segment_index`, last present row):
    refused on all three quarters, both interpreters. `value` NaN/inf/-0.0/True/Decimal/str: refused. Non-string nested
    keys (`source_span[1]`, `receipt[True]`): refused. Closed.
  - G2-B2 variants: **not closed** as a class — see G2-B3, G2-B4, G2-B5 (JSON-carriable tampers still raise).
  - G2-B1 (R176): the eleven are accepted per the rule; R176's *other half* (into/inside a table is blocking) fails — G2-B1 (r7).
  - G4-B1 (glued through markup) inside and outside tables: `tbl_glued_b_new_row`, `tbl_glued_comment_new_row` refused 18/18
    per quarter so far (fam4, final); R174's five witnesses pass in the frozen suite (G4 reports).

## Findings

### G2-B1 (BLOCKING, bar c): seam relocations into and inside tables are accepted
- R176 accepts only "a relocation onto such a token **outside the tables**"; the commission: "A relocation into or inside a
  table ... is blocking." The check (`:287-332`) has no notion of tables: `td/th/tr/table` are mere separators (`:229`), and a
  span wholly inside one comment passes unconditionally (`:261-262`).
- Accepted at head (fam4, 3.14, final 4,124 runs):
  - **another cell printing the same literal** (fam4C): 958/959 accepted;
  - a bracketed comment `<!-- x>LIT<y -->` **inside the pinned cell**, **inside the pinned row**, **between rows of the last
    table**: 57/57 each, all admitted F1-Q;
  - a **new row cell** `<tr><td>LIT</td></tr>` in the last table: 57/57, admitted F1-Q.
- Probes: `test_g2_b1_relocation_inside_a_table_is_refused[*]` (12: 4 constructions x Q1-Q3) and
  `test_g2_b1_relocation_onto_another_cell_is_refused[*]` (6). All 18 fail at head on 3.12 and 3.14 with `assert 'ok' != 'ok'`.
- Observed: validator accepts. Expected: refused (or the seat rules the class into R176 explicitly; the R6 ruling's own
  rationale concedes "a relocation from one cell to another would still pass" a containment check, but R176 does not freeze it).
- Impact: seam-only (replay pins placement under the real extractor), but it is exactly the bar's named blocking class.

### G2-B3 (BLOCKING, bar d / R134, R176): a huge numeric `value` raises OverflowError
- `_validate_row_structure` `math.isfinite(float(value))` at `economic_observations.py:192` is outside every `try`.
- `value = 10**400` (JSON-carriable: `json.loads("1"+"0"*400)` yields it), `-10**400`, `Fraction(10**400)`: `OverflowError`
  escapes `validate_selected_facts` on Q1, Q2, Q3, both interpreters. Traceback `:536 -> :401 -> :205 -> :192`.
- Inherited: same at `$R5HEAD` (`:189`) and at `e1dd9caa3fa` (legacy `:305`). Round 6 did not probe it.
- Probe: `test_g2_b3_a_huge_numeric_value_is_refused_not_raised[*]` (9). All fail. Expected `EconomicObservationError`.

### G2-B4 (BLOCKING, bar d / R134, R176): a non-string workspace `event_id` raises TypeError out of the replay
- `_validate_envelope_rows` passes `workspace["event_id"]` into `extract` (`:354`) before any row check; `pg_profile.py:1912`
  `"|".join((event_id, ...))` raises `TypeError` for `7`, `null`, `["e"]` (all JSON-carriable), also Decimal/set/bytes.
- Q1, Q2, Q3, both interpreters. Inherited from `$R5HEAD` (`:285` -> `pg_envelope.py:1179`); envelope-introduced (R136 replay).
- Probe: `test_g2_b4_a_non_string_workspace_event_id_is_refused_not_raised[*]` (9). All fail with TypeError.

### G2-B5 (BLOCKING by the bar's letter, bar d; inherited from the base): non-list `sources` raises TypeError
- `for source in workspace.get("sources", [])` at `economic_observations.py:513` (base `e1dd9caa3fa:181`). `sources` = `null`,
  `5`, `true` raise `TypeError`. Shared pre-envelope code, but bar (d) covers any exception escaping the validator.
- Probe: `test_g2_b5_a_non_list_sources_is_refused_not_raised[*]` (3). All fail.

### G2-m2 (minor, bar d; interpreter-dependent outcome): deep nesting raises RecursionError
- `period` = list nested 100,000 deep: `RecursionError` in `_fact_id`'s `str()` (`:94`) on both interpreters.
- `unit` / `rights_profile` / absent `detail` nested 100,000 deep: **3.12 raises `RecursionError`** from `json.dumps` at `:409`
  (not caught: only TypeError/ValueError); **3.14 refuses** ("does not replay"). An outcome that differs by interpreter.
- Minor because a workspace decoded by `json.loads` cannot reach that depth; but R176's own witnesses (Decimal, set) are
  equally in-memory-only, so the seat should decide. Probe: `test_g2_m2_*` (2): 3.12 2 fail; 3.14 1 fail (`period`), 1 pass.

### G2-O1 (observation, not a finding): workspace-level keys outside the facts are not validated
- 17 top-level keys (`schema`, `claims`, `guidance`, `generated_at`, ...) and every `sources[i]` field except
  kind/receipt_state/document_id accept a string tamper. The validator's contract is the selected `pg_` facts; recorded only.

## Family 4 — past the gate, `character` kind and R171 kinds (`fam4g_char.py`, 3.14)
- 8 constructions (`&#x378;`, raw U+0378, `&#1;`, `&#xFFFF;`, `&#127;`, raw U+0085, `</tbody>`, `<isindex>`) before each of 6
  pinned literals per quarter, Q1-Q3: **144 built past the gate (both `_unreadable_markup` and `_unassigned_character`
  replaced), every one binds present rows, validator refuses 144/144, 0 exceptions.**
- r6 `fam4g.py`/`fam4g2.py` (eight R163 kinds, with relocation) re-run: not run (driver stage 2 never reached).

## Family 4 — final counts (`fam4.py`, 3.14; all 57 present rows of Q1-Q3; 4,124 runs, 0 exceptions)
- One-byte shifts/widenings/narrowings: 429 run, **0 accepted**.
- Relocations outside tables (38 targets x 57 rows = 2,166 runs): **1,140 accepted, all within R176's rule** (whole tokens
  outside the tables: prose p/bare/div, after `</html>`, wrapper description, bracketed comment, script/style/title/textarea/
  xmp/iframe/noembed/noframes/noscript outside tables, hidden elements, `&nbsp`-prefixed, `&#1;`-prefixed). 1,026 refused
  (342 by the check on admitted F1-Q documents: plain comments, attribute values; 684 at admission).
- Relocations into/inside tables (9 targets x 57 = 513): **228 accepted = G2-B1** (bracketed comment in pinned cell, in pinned
  row, between rows of the last table; new row cell in the last table: 57/57 each). Refused: plain comment in the cell,
  G4-B1's glued `<b></b>` and glued comment in a table row (57/57 each), script/textarea in a cell (admission, element).
- Another cell printing the same literal (every such cell, not just 3): **958/959 accepted = G2-B1**.
- R176 classification of `&#1;`-prefixed (57 accepted, outside tables): `html.unescape` drops U+0001 while html5lib keeps it as
  an unprinted control; whole under R174's units, so inside R176's rule. Recorded, not a finding.

## Family 11 — no-exception fuzz and differential (`fam11.py`, 3.14)
- Corpus: every pinned primary and second cell, and every header and title cell over them, in Q1–Q3. Each gets round 6's 62 edits plus 26 new ones:
  - in cells: unassigned `&#x378;` and raw U+0378, `&#xFFFF;`, `&#128;`, `&#133;`, `&#x2028;`, `&#8203;`, a private-use character, 两, U+FF04, U+FE69, `</tbody>`, `<isindex>`, `</th>`, `&amp;#49;`, a literal glued through `<b></b>` and through `<wbr>`, and a 4,400-digit run;
  - in headers: superscript years, `FY2026`, `2026E`, `2025–26`, 两 and `&#x378;`.
- **Q2 finished**, final record: `n 3780, exc_build 0, exc_validate 0, rejected_own 0, divergence 0, present_rows 37600`.
- **Q1 and Q3 were still running at collection** (PIDs 39025/39027/39028, 33 min elapsed). Partial files: Q1 3,737 documents, Q3 3,658 documents. Every record so far has 0 exceptions, verdict `ok`, and no `div` field.
- **Total so far: 11,175 documents. 0 exceptions escaped the build or the validator. The validator rejected 0 of the extractor's own outputs. 0 divergences** between `html.unescape(source[span])` and the cell literal. The Q2 figure covers 37,600 present rows.
- Admission (snapshot) was about 55% F1-Q. The rest were refused under every `markup_unreadable` kind, `character` included (about 700), and under `unknown_table`.
- **The 3.12 fuzz run (`fam11v3_Q3_12.jsonl`) never started.** It sits in driver stage 2, which was never reached.

## Family 10 — replay completeness (`fam10.py`, 3.14): partial, still running or unfinished
- `fam10.log` has finished-case lines for Q1 (419 tampers) and Q2 (850). The `fam10full_*.jsonl` file has 18 logged records and no summary line, so the run had not finished.
- The logged records are 16 accepted and 2 refused, with 0 EXC:
  - 14 accepted records set a field that is already null to null (`x_none`, Q3);
  - 2 hold a list as a tuple (Q1, Q2).
  - Both are invisible to JSON and inside R176's rule.
- **No int↔float acceptance was logged**, so G2-m1 is closed at scale so far. Round 6 logged 627.
- **`fam10b.out` (the other seven refused-document kinds): not run.** It is in stage 2.
- **The R150 exempt set was not re-measured this round.** Round 6's measurement is the only one: `event_id`, and `document_id` on absence rows only.
- The exceptions that escape come from workspace-level and huge-value tampers outside fam10's tamper set. They are G2-B3, G2-B4 and G2-B5.

## Family 4 — past the gate for the eight R163 kinds (`fam4g.py`, `fam4g2.py`): not run
- These were stage-2 runs and were never reached.
- The `character` kind and R171's kinds were covered by `fam4g_char.py` (above): 144 builds past the gate, 0 accepted, 0 exceptions.

## Family 5 — determinism: not run
- The driver never reached stage 2 (corpus capture) or stage 3. Stage 3 was 16 separate-process runs: PYTHONHASHSEED 0, 1, 42 and 4294967295, crossed with LC_ALL C and tr_TR.UTF-8, on 3.12 and 3.14, plus an interleaved cache-clearing pass per interpreter.
- `capture.log`, `fam5_corpus.json` and `fam5_*.json` do not exist.
- **Evidence in hand is limited to this:**
  - (i) G2-m2 is an outcome that depends on the interpreter: 3.12 raises, 3.14 refuses;
  - (ii) every other probe in `explore.py` (187 lines per interpreter) and in the probe file gave identical outcomes on 3.12 and 3.14.
- Nothing was measured for PYTHONHASHSEED, the locale, or `lru_cache` state (cold against warm).

## Probes run and failed, per family (search bounds)
- **Family 0.**
  - The r6 probe file: 18 cases × 2 interpreters, 11 failing on each (the eleven R176 accepts, as the seat testified).
  - `explore.py` variants: 57 tampers per quarter × 3 quarters × 2 interpreters.
- **Family 4.**
  - `fam4.py`: 4,124 runs, 0 exceptions. 429 shifts, 0 accepted.
  - Outside tables: 1,140 accepted, all inside R176's rule.
  - Inside tables: 228 accepted, plus 958 of 959 other-cell relocations accepted. Both are G2-B1.
  - `fam4g_char.py`: 144 builds past the gate, 0 accepted.
- **Family 10.** Partial: 1,269 or more tampers on Q1 and Q2, 0 real tampers accepted, 0 EXC logged.
- **Family 11.** 11,175 documents, 0 exceptions, 0 self-rejections, 0 divergences. Q1 and Q3 are partial.
- **Family 5.** Not run.
- **Probe file `test_envelope_audit_probes_r7_g2.py`.** 41 cases.
  - 3.12: `41 failed in 24.73s`.
  - 3.14: `40 failed, 1 passed in 25.07s`.
  - Per finding:

| Finding | Cases | Failing on 3.12 | Failing on 3.14 |
|---|---|---|---|
| G2-B1 | 18 | 18 | 18 |
| G2-B3 | 9 | 9 | 9 |
| G2-B4 | 9 | 9 | 9 |
| G2-B5 | 3 | 3 | 3 |
| G2-m2 | 2 | 2 | 1 (`period`; `unit` passes on 3.14) |

## Background runs at collection time
- `driver.sh` (log `driver.log`) was still in stage 1:
  - fam11 Q1 and Q3: `fam11v3_Q1_14.jsonl`, `fam11v3_Q3_14.jsonl`;
  - fam10: `fam10.log`, `fam10full_*.jsonl`.
- Stages 2 and 3 are not reached: fam10b, the fam11 run on 3.12, fam4g, fam4g2, the capture and fam5.
- The seat may let it run, or kill PID 30695 (the driver) and its children. They write only under this directory.

Final check after the last foreground run: `git rev-parse HEAD` = b6808dfcc166afd323ba4dabbb824fa30c1d9ee1, and `git status --porcelain` is empty (0 lines).

---

## Group G3: units, years and the Q1–Q3 sweep (verbatim)

# G3 — Opus R7 audit (units, years, Q1/Q2/Q3 sweep), CDV-1 T1 envelope at b6808dfcc166afd323ba4dabbb824fa30c1d9ee1 (PR #7905)

## STATUS: REJECT — one blocking finding (G3-R7-B1, bar e). Every round-6 G3 finding is closed by its original construction and by variants.

HEAD `b6808dfcc166afd323ba4dabbb824fa30c1d9ee1` and an empty `git status --porcelain` were confirmed before the first run and after the last. All runs used `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.` and pytest `-p no:cacheprovider`, with at most four processes. Nothing was written in the worktree.

## Findings
### G3-R7-B1 — blocking (bar e; R170 as written): a year-bound pin binds when its only year is printed as a figure
- **Code.** `_FIGURE` (`engine/company_intelligence/pg_envelope.py:57`) = `\(?\$?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?\)?%?`. A four-digit figure without a separator never fullmatches it.
  - In `_header_years` (`:914-929`) such a value misses the figure skip (`:924`).
  - It passes the unreadable test (`:926`), because once `_YEAR` strips `2026`, only `$ % ( ) + - # .` remain, and none of them is numeric.
  - It reaches `years.update` (`:928`), and `_period_matches` (`:892-909`) accepts `years == {period.year}`.
- **R170 says** a single figure ("optionally in parentheses, with `$` or `%`") adds nothing. Bar (e) forbids a year bound from a header value that names another figure.
- **Construction.** Probe `test_BLOCK_g3_r7_b1_core_year_from_a_figure_only_is_unlocated`, sweep `g3lib7.fam8b` sub `sole`.
  - Drop the governing core-reconciliation title's year (`Three Months Ended March 31, 2026` becomes `…March 31`). CORE is then unlocated, which is correct (control `NONE`).
  - Add one banner row whose only text is `$2026`, `2026%`, `(2026)`, `$(2026)`, `+2026`, `-2026` or `#2026`. **CORE is present at 1.59** and the workspace validates, on Q3, on 3.12 and 3.14 (7 probe cases).
  - Sweep, Q3: those forms plus `2026.` bind CORE 1.59. The same forms with `2025` on the prior table bind **PCORE 1.54**. That is 16 bad of 126 `sole` judgements.
  - Controls: `2026` and `2026x` bind (a year). `2,026` and `2026 million` stay unlocated.
- **Expected.** Unlocated. A reader reads `$2026`, `2026%` and `(2026)` as amounts, so the table states no year.
- **Plausibility.** Low for P&G, which prints separators. The bar covers any byte-level edit.
- **Smallest repair.** Treat a `20dd` that carries a figure sign (`$ % ( ) + -`, a decimal point) as a figure. Either make it unreadable (fail-closed) or have it add nothing (R170's letter). Plain `20dd`, `20dd (d)` and `FY20dd` stay as they are.
- **Scope gap.** Q1 and Q2 are not realised. The harness took FY 2026 as the title year, but the Q1 and Q2 titles print calendar 2025. The probe's Q1/Q2 parameters fail with `AssertionError: ('core_reconciliation', 2026)`, which is a harness error, not the finding. The code path does not depend on the quarter.

### G3-R7-m1 — minor (bar e/f adjacent, value-correct): title years read Unicode digits
- `_parse_period_title` (`:842`, `:850`) matches the year with `\d`, so the governing title's year may be Arabic-Indic, fullwidth or mixed-script (`2٠26`).
- Probe `test_OBSERVE_f8_title_year_in_non_ascii_digits`: Q1 and Q2 bind CORE 1.99 and 1.88, which are the true values. Q3 is refused as `unknown_table:t9`.
- R170 makes the same forms unreadable in a header value, so title and header disagree. `2٠26` is a loose parse. Admission (R178) keeps it deterministic across 3.12 and 3.14.

### Observations (coverage, fail-closed)
- O1: a `Fiscal Year` banner over the highlights refuses the table (signature), so PDIL is unlocated. 3 probe controls fail for this reason, which is my expectation, not a bind. Round-6 sweep banner `cover` rose from 132 to 524, and new-form banners cover 140. All are fail-closed under R170.
- O2: a year cell carried by rowspan from a row above, with the year cells starting in different rows (`geo` `year_rowspan_from_row_above`, highlights and earnings, Q1–Q3), leaves every year pin unlocated, including the correct ones. It is fail-closed: a lone-own-cell row reads as over every column (`_headers_over` `:820`).
- O3: carried-`%` allow controls on COREG are unlocated (6), the same as round 6.

## Family 0 (G3's part): round-6 findings
- Round-6 probe file at HEAD: 3.12 gives `148 passed, 9 skipped in 51.32s` and 3.14 gives `148 passed, 9 skipped in 49.90s`, as the seat testified.
  - Every former `test_BLOCK_*` case passes: B1 5, B2 15, B3 21.
  - The 9 skips are B2 depth-2 variants whose layout has no same-extent cell two rows up (line 112), unchanged from round 6.
- **G3-B1 closed.** Original 5 cases, plus 17 new variants (Q1 CORE and PDIL, Q2 DIL and PDIL, Q3 PCORE, and value to the growth column ×9) pass. 2 are skipped because the prior column has no later year. `span2` 12/0 bad, `geo` widen 1/2/3/6/7 and widen+rowspan 33/0 bad, label-from-above and label-into-next 4/0 bad.
- **G3-B2 closed.** 117 new cases pass: U+2060, U+200C, U+200F, U+0301, U+E000, U+034F, U+FE69, raw ＄ and U+2064 before `$`, on SALES and FX for Q1–Q3; six invisible shields; `%`+Cf beside highlights EPS; allowed-unit controls. Sweep `invis` 857/0 bad (705 in round 6).
- **G3-B3 closed.** 156 new cases pass: raw en dash, super- and subscript digits, `2٠26`, Ⅱ, ②, ½, `FY25/26`, em dash, `CY2026`, `2026E`, `2025 & 2026` and `2025(12)`, over the highlights and earnings on Q1–Q3. Sweep banners 2958/0 bad (650 in round 6), plus new-form banners 2224/0 bad.
- **R178's figure test.** 两 京 財 〇 あ א banners unlocate PDIL/PCORE on Q1–Q3 on both interpreters (inside the 156). Over all 232,689 code points Unicode 3.2 assigns, `_figure_character`, `_seen` (char, `$`+char, char+`%`), `_YEAR` glue and `_FIGURE` show 0 differences between 3.12 and 3.14. `_seen` maps exactly U+0024, U+0025, U+FE69, U+FE6A, U+FF04 and U+FF05 to `$`/`%`.
  - A later Unicode is argued from the rule, not measured: `ucd_3_2_0.category` is frozen, and any new numeric that is not `Lo` has to pass `isnumeric`, which only adds constraints. NFKC is stable for assigned characters.
- **O1–O3** of round 6 are unchanged (fail-closed). O3 re-probed ×3 and passes.

## Family 1 (R1–R5 variants): 37 cases, 0 failed
New constructions:
- **R1.** Whole-document CRLF on Q3; metric renamed on the Q3 CORE row (3 ways); a non-pinned earnings value edited; highlights and segment-driver repeat and organic drop; `1.6３`, `1.63.`, `1..63`, `1,63`, `1.63&#8203;`, `+1.63%`, `1.63e0`; `-`, en, double-em and horizontal-bar dashes.
- **R2.** B3 on Q2 earnings and Q1 core recon; B4 ±2 on Q3; B5 reason tamper; B7 `<br>` prefixes; B8 CORE row; B10 CRLF/FF prefixes.
- **R3.** N3 over 10 sources compared as whole workspace JSON; N4 `$1.59%` on the second statement; N6 highlights on Q2; N8 unclosed value table.
- **R4.** P4 overflow to infinity; M2 a row inside a comment; P1 `&amp1.54`.
- **R5.** m2 `&#x7F;`, `&#2;` and `&#xFDEF;` refused as `character`; m3 on drivers.
- Family 7 (R146): 33 new TYPE-line variants refused (U+200B, NUL, BOM, fullwidth 1, Cyrillic Е, U+2010, U+2028, comment, `&#45;`, `EX-99.1.`, `EX-99.01`).

## Family 2, 6, 8 sweep (3.14; round-6 harness plus g3lib7), probes run / bad
| family | run | bad | notes |
|---|---|---|---|
| 2 duration relabels Q1–Q3 | 102 docs | 0 | 0 exceptions |
| 6 round-6 harness | 3232 | 0 real | 6 control = O3 |
| 8 round-6 harness | 3314 | 0 real | hl_dup 12 and title 12 are the round-6 harness artefacts (correct present) |
| 8b new banners | 2224 | 0 | cover 140 |
| 8b sole-year | 126 (Q3) | **16** | G3-R7-B1 |
| 8b sole-year in a data cell | 48 | 0 | cover 8 |
| geo (R168) | 43 | 0 | |
| lone-header | 21 | 0 | all fail-closed, controls too (GAP) |
| 6b R169 pointer forms | PENDING | | `f6b_Q{1,2,3}.jsonl` |

## Probe file `test_envelope_audit_probes_r7_g3.py`: 423 cases
- 3.14: `28 failed, 393 passed, 2 skipped in 201.85s`. 3.12: `28 failed, 393 passed, 2 skipped in 191.99s`. The failure sets are identical.
- The 28:
  - 7 real G3-R7-B1 (Q3);
  - 16 BLOCK plus 2 restore-control on Q1/Q2, harness year error;
  - 3 `Fiscal Year` controls (O1, coverage).

## GAPS
- G3-R7-B1 was realised on Q3 only (harness year error on Q1/Q2).
- `g3lib7.fam6b` (R169 pointer forms: own, shield, carried and spans-down) is still running under `chain.sh` (`chain.log`, `f6b_Q*.jsonl`, `chain.done`). The pytest B2 variants cover its forms on SALES, FX and DIL for Q1–Q3.
- The sweeps ran on 3.14 only. Justification: the per-character reader table shows 0 differences between 3.12 and 3.14, and the probe file ran on both.
- The lone-header construction unlocated its own control, so that attack is unproven either way.

---

## Group G4: integrity and the artifact, families 0, 12, 13 and 14 (verbatim working draft)

# OPUS T1 ENVELOPE AUDIT R7 — G4 (integrity and the artifact) — WORKING DRAFT

Head audited: b6808dfcc166afd323ba4dabbb824fa30c1d9ee1. READ_ONLY; all writes under $MY/audit_t1_envelope_r7/g4/.

## Status so far (updated per batch)

STATUS: PENDING

## Integrity (family 0 / NOT DONE UNLESS)
- Before first run: `git rev-parse HEAD` = b6808dfcc166afd323ba4dabbb824fa30c1d9ee1; `git status --porcelain` empty. After last run: PENDING.
- `git diff --stat $FREEZE $HEAD -- tests/ research/ .github/`: empty.
- `git diff --stat $R5HEAD $FREEZE`: exactly .github/ci/legacy-jobs.yml (3 +-, adds r6 suite to paths and the run line), OPUS_T1_ENVELOPE_AUDIT_R6 (+704), SEAT_RULING_T1_ENVELOPE_R6 (+301), tests/test_pg_envelope_f1.py (23 +-), tests/test_pg_envelope_f1_probes_r6.py (+660).
- `git diff $R5HEAD $FREEZE -- tests/test_pg_envelope_f1.py`: changes `headers_over` only (AST-checked by probe i3: every other top-level node identical).
- `git log $R5HEAD..$HEAD --name-only`: freeze 6b6448a5fd6 then exactly ten commits (5c750891924 R168 … b6808dfcc16 R178), each touching only pg_envelope.py or economic_observations.py (probe i2).
- r1–r5 suites and tests/fixtures/pg_envelope/ byte-identical R5HEAD..HEAD.

## Runs at HEAD
- Seven frozen suites, 3.12 venv312_min: `700 passed, 80 warnings in 315.48s`.
- Seven frozen suites, 3.14 venv_t1: `700 passed, 80 warnings in 300.22s`.
- curated_exclusive (/opt/homebrew/bin/python3.12): `2 passed, 119 deselected, 80 warnings in 252.93s`.
- Gate line: PENDING (first attempt extracted the wrong step — `pip install` — and ran nothing; re-run queued in runsB).
- a5a + capital-structure (/opt/homebrew/bin/python3.12): HEAD `213 passed, 80 warnings in 41.79s`; f8e4af5aa4c tree (git archive of engine scripts collectors config lib contracts schemas config.yml tests/conftest.py tests/fixtures + the five suites into $G/f8e) `213 passed, 80 warnings in 47.60s`. Per-test outcome diff (sorted PASSED/FAILED lines): 0 lines (cs.diff). Also 0 lines against the seat's baseline_a5a_cs_f8e4af5.txt.
- Earlier probe files (3.14 venv_t1): r1 `4 failed, 99 passed`; r2 `1 failed, 67 passed`; r3 `4 failed, 220 passed, 1 skipped`; r4 `13 failed, 1092 passed, 27 skipped`; r5 `4 failed, 11 passed`. All failed sets identical by case name to round 6's (see accounting below).
- R6 G4 probe file: 3.12 `1 failed, 18 passed`; 3.14 venv_t1 `1 failed, 18 passed`; 3.14.7+html5lib `1 failed, 18 passed`. The one failure is `test_i1_head_and_clean` (hard-codes HEAD=135a67a3e12, expected to fail at a new head). File holds 19 cases, not 14 as the seat's testimony says (G4-m? testimony, PENDING classification). The five G4-B1 cases now pass.

## G4 R7 probe file (test_envelope_audit_probes_r7_g4.py) — first run, both interpreters: 9 failed, 12 passed
- i4 failed only because my allowed-name set omitted `int` (the `index: int` annotation); fixed. i5 was rewritten to examine only the two try nodes that differ from FREEZE: `_validate_row_structure`'s TypedAbsence construction (:170–179, body builds `TypedAbsence.from_dict` from the row's absence payload) and `_validate_envelope_rows`' `json.dumps(dict(row), sort_keys=True)` (:409–411). Neither reads the source; both end in `raise EconomicObservationError(...) from exc`. i5 passes.
- b1 (x0b, x1c-x1f, x85): `eo._whole_printed_token(b"<p>-X1.63</p>", …)` returns True — the R174 check uses Python `str.isspace()` (economic_observations.py `separated` → `edge(printed).isspace()`), which calls these characters whitespace; HTML does not. Through the full seam (b2, glued by 'x'), all six relocations are REFUSED at head (b2 passes), and the control `<p>x 1.63</p>` is also refused — so the refusal comes from an earlier check, not R174. Classification PENDING.

## Family 13 / 14 — PENDING
- Minus-one trees built in $G/trees (m_R168..m_R178, m_R178adm, m_R178fig; frz = R5HEAD engine + R168 oracle). Clean reverse-apply for R168, R171, R174–R178; R169, R170, R172, R173 hand-resolved (only constant-block context conflicts caused by R178's `_NON_ASCII` line, plus R170's `_header_years` now carrying R178's `_figure_character`). Runs queued in runsB.
- Mutation harness g4r7_mut.py (62 mutations incl. seat R4 matrix, R163 kinds + 33 branches, R164, R165, R173/R174/R178 hunks); anchors verified; runs queued in runsB.

## Family 12 — hosted CI (read once; gh_checkruns.txt, gh_runs.json)
- check-runs for b6808dfcc16: total_count 25. ci-pack-0, 1, 2, 3, 4, 7, 8, 9, 10, 11: success. **ci-pack-5 and ci-pack-6: in_progress.** No `ci-gate` check-run exists yet. ci-plan, contract-delta, fence-pack, grader-manifest, capability-broker, self-mod-fence, ci-authority, ci-authority/main: success. `ci-authority/codex/merge-queue-pilot`: failure (known non-binding). trusted-ci and the three fork-guard checks: skipped.
- Runs: ci 36200249010 in_progress; fences 36200248810 and ci-authority 36200248202 success (all at b6808dfcc16, created 23:14:57Z).
- `earnings-economic-dossier`: the local plan (`scripts/run_ci_pack.py --validate-only --pack-count 12 --changed-from 8a8ecbe868f`, the merge-base with local origin/main; full suite because legacy-jobs.yml is a global invalidator) places it in **pack 7 — hosted ci-pack-7 concluded success**. Its `if: ${{ false }}` is the required legacy-job marker (run_ci_pack.py:82, :1387) and does not stop run_ci_pack from executing it.
- GAP: ci-pack-5, ci-pack-6 and ci-gate not concluded at my single read.

## FINDING G4-B1 (BLOCKER, bar c) — R174's whole-token check treats Python-only whitespace as a printed boundary; G4-B1's class stays open
- Code: `engine/company_intelligence/economic_observations.py:279` — `return edge(printed).isspace()`. `str.isspace()` is true for U+000B, U+001C–U+001F and U+0085 (and U+2028/2029, U+3000 etc.); HTML whitespace is only TAB LF FF CR SPACE. The R155 gap check at `:320` has the same root (`all(character.isspace() ...)`), so it lets the same characters through.
- Construction (probe test_b3_*): fragment `<p>-<b></b>X1.63</p>` inserted before Q3 `</TEXT>`, the Q3 diluted-EPS receipt relocated through R143's seam (r6.relocated) onto `1.63`. X in {\x0b, \x1c, \x1d, \x1e, \x1f, \x85}: R163 admits (`_unreadable_markup(body) is None`), the workspace receipt excerpt is `1.63`, and `r1.validates(ws, texts)` is True — ACCEPTED, 6/6, on 3.12 and 3.14. Letter-glue variant `<p>Q<i></i>X1.63</p>` accepted 2/2.
- Reader: html5lib 1.1 prints `'-\x1c1.63'` (and likewise for each X) — one token, the control invisible; i.e. a reader shows `-1.63`, exactly R174's own witness `<p>-<b></b>1.63</p>`. The engine's own `_text` collapses X to a space (`'- 1.63'`).
- Why it is outside R176's recorded limit: R174 is headed "the span check reads through markup the way a reader prints" and its witness is the reader-printed `-1.63`; R172, in the same ruling, defines "whitespace that HTML does not treat as whitespace" and C0/C1 controls as characters a reader does not print as layout. The commission (bar c): a relocation "onto a token that is not whole under R174 is blocking". Expected: refused ("span is not a whole printed token"). Observed: accepted.
- Direct unit probe test_b1_*: `eo._whole_printed_token(b"<p>-X1.63</p>", s, s+4)` returns True for all six X.
- Control test_b2_control_markup_space_relocation_is_accepted: `<p>-<b></b> 1.63</p>` accepted (passes) — the refusal the b3 probes demand is specific to non-HTML whitespace.
- Minimal repair direction: compare against HTML whitespace (`in " \t\n\r\f"`) in `separated` and in the R155 gap check; or refuse, outside cells too, the characters R172 refuses in cells. Not blocked by admission today because R172's `character` check runs only in `state == "cell"` (pg_envelope.py:282) and R178 skips ASCII/Cc.

## Family 13 — code review of the ten commits (read, with probes i2–i7, c1)
- Imports added (FREEZE..HEAD): economic_observations.py `bisect`, `functools`, `re`; pg_envelope.py `replace` (dataclasses), `unicodedata`. All stdlib. Matches testimony.
- Caches: one new, `_printed_units` (economic_observations.py:233, maxsize 4) — pure function of bytes; probe c1 (18 interleaved sources > 4: cold = warm = copies) passes on 3.12 and 3.14.
- Exception handling added: exactly two try nodes differ from FREEZE (probe i5): `_validate_row_structure` widened to `except (TypeError, ValueError)` (:179) and the R176 `json.dumps` try (:409–411). Both handlers end in `raise EconomicObservationError`, neither try body names `source`/`source_bytes`/`raw`/`body`. Testimony confirmed. (The pre-existing `try: raw = source_bytes[start:end].decode("utf-8") except UnicodeDecodeError` at :309 wraps a read of the source, ends in a refusal, and predates the ten commits.)
- New refusal messages: exactly R174's and R176's (probe i6). New admission kind literal: `markup_unreadable:character` only (probe i7); no new absence reason.
- No per-release literals, sentinels or probe-specific branches found in the +154/−33. `_SEPARATING` (td th tr table p div br) is R174's list verbatim; other block tags (li, h1–h6, section) are treated as inline markup — fail-closed (refuses more), coverage note only.
- Minimality: R168 (`_reads_under` per column + `occupied` label rows), R169 (`_seen`), R171 (`isindex` + unread end tag in a cell), R172 (cell character check), R173 (`_RAW_TEXT_ELEMENT` blanking), R175 (drop second unescape and literal `&#160;`/`<br/>` rewrites), R176 (JSON string compare + widened handler), R178 (`_unassigned_character` admission; `_figure_character`) each implement only their ruling. R170's `_period_matches` moves the `_header_years` call above the title check so `None` refuses before titles are read — needed by R170.
- Nit G4-n1: `_reads_under` recomputes `required`, `current_end`, `prior_end` and `period` once per spanned column (pg_envelope.py:~985–1000); `_locate` scans every row for identity per cell to find `occupied` (O(rows×cells) per cell). Harmless.
- Minor G4-m1 (code quality / defence in depth): the R155 gap check (economic_observations.py:320) and R174's `separated` (:279) both use Python `str.isspace()` rather than HTML whitespace; the blocking consequence is G4-B1 above.

## R176 JSON comparison (family 13 question) — probe c2, 3.12: 7 passed
- For every key path (top level, and nested in `source_span`/`typed_absence`, depth 3) of one present and one absent Q3 row, tampers: nested list 5,000 deep, NaN, `True` for 1, int↔float swap, `-0.0` for 0, `{1: "a", "b": 2}` (mixed key types), tuple for list. Every JSON-visible tamper refused (`validates` False); none raised anything but EconomicObservationError (r1.validates catches only that, so any other exception would error the case); tuple-for-list (JSON-invisible) raised nothing. R176 refuses what JSON can see and raises on nothing tried. Not exhaustive over row kinds (conflict/refused-document/excluded rows are G2's family 10).

## Earlier probe files — accounting vs round 6 (3.14 venv_t1)
- r1 file: 4 failed, 99 passed (r6: 4 failed, 99 passed). Failed set identical: test_f4_non_number_in_both_eps_statements_is_unlocated[2.0 pts], [— per share], test_f7_drivers_title_date_removed, test_f10_control_q4_tables_match_no_f1q_role_beyond_masthead.
- r2 file: 1 failed, 67 passed (r6 identical): test_d_s0_validator_missing_fields_tamper_outcome_unchanged.
- r3 file: `4 failed, 220 passed, 1 skipped in 1254.52s` (r6: 4 failed, 220 passed, 1 skipped) — failed set identical by name.
- r4 file: `13 failed, 1092 passed, 27 skipped, 80 warnings in 957.97s` (r6: 13 failed, 1092 passed, 27 skipped) — failed set identical by name.
- r5 file: `4 failed, 11 passed in 11.13s` (r6: 4 failed, 11 passed) — failed set identical by name (the 3 B3 + 1 OBSERVE `KeyError` cases of round-6 G4-m1).
- Net: no outcome of any of the five earlier probe files changed between 135a67a3e12 (round 6) and b6808dfcc16. Every failure is a case round 6 already accounted for.

## Family 14(iii) — the oracle
- `headers_over` (tests/test_pg_envelope_f1.py:192) now keeps a header only if it stands over every column the cell occupies; it reads only `rows`, `cell`, `norm` and builtins (probe i4) — engine-independent.
- The oracle's label side is NOT moved: `label_of` (test_pg_envelope_f1.py:182) and `locate` (:221) still read the label from the cell's first row only. R168's label half ("the pin's label in every row its rowspan reaches") is witnessed only by direct engine assertions (`unlocated(...)`, test_pg_envelope_f1_probes_r6.py:159, 165), never through `witness_outcome`. So `headers_over` is the only change the frozen cases need, but not the only change needed for the oracle to encode R168. Observation G4-O1 (non-blocking): on a label-rowspan document the oracle and the engine would disagree; no frozen case compares them there.

## Family 14(i) — the freeze tree (R5HEAD engine + FREEZE tests = R168 oracle)
- Tree `trees/frz` = `git archive 6b6448a5fd6` (engine byte-identical to 135a67a3e12: `git diff --quiet $R5HEAD $FREEZE -- engine` true). Seven suites: 3.12 `106 failed, 594 passed in 360.53s`; 3.14 `106 failed, 594 passed in 349.29s`; failed sets identical across interpreters.
- The 106 = 103 R6 cases + the round-1 geometry pair (`test_f3_header_geometry_edit_in_one_statement_never_binds_another_value[highlights_2026_colspan_plus1]`, `[segdrivers_price_colspan_plus1]`) + 1 harness artifact: `test_r139_s0_typed_absence_missing_fields_tamper_refused` failed with `ModuleNotFoundError: tests.earnings_economic_fixtures` because my archive omitted that helper (it passes at HEAD in the worktree, and the file is identical FREEZE..HEAD). Corrected count 105 failed / 595 passed on both interpreters — the seat's testimony is REPRODUCED, and the R6 suite is 103 failed / 60 passed at the freeze.
- The helper was added to every tree before the remaining minus-one runs; trees that had already started (m_R168 on both interpreters) will carry the same single artifact, discounted by name.
