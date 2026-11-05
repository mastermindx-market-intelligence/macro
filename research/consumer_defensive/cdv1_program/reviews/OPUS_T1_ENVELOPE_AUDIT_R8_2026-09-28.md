# Opus re-audit R8: CDV-1 T1 F1-Q envelope at e6f49ceccb85ca1feedab0876f947a042224992f (PR #7905)

MODE: READ_ONLY. The round ran as four independent Opus auditors, one per family group, all on the same head.
- Each group's report follows verbatim, in group order. Probe files and raw outputs stayed in the seat's scratch directory. Nothing was written inside the worktree.
- G2, G3 and G4 each record `git rev-parse HEAD` at the head and an empty `git status --porcelain`, before their first run and after their last. G1 records the pre-run check. Its closing line defers the post-run check to its return, which is not part of the report.
- **Two reports were written incrementally.** The verdicts in both are complete.
  - G1's header still reads "INTERIM". It says the report was written early by instruction. Its "Verdict for G1's families" section records the verdict, the blocker and what closed.
  - G2's status line says it was written incrementally. Its run ended at its turn limit. The report's "Family status" table records what finished in each family, and both blockers are complete: code, construction, reader evidence, expectation and controls.
- After the round, the seat confirmed the worktree at `e6f49ceccb85…` with an empty `git status --porcelain`.

## STATUS: REJECT (all four groups)

| group | families | status | blocking | other findings |
|---|---|---|---|---|
| G1 | 0 (round-7 G1 findings), 3, 9, 15, 16 | REJECT | G1-R8-B1 | G1-R8-n1 (nit); G1-R8-O1 (observation) |
| G2 | 0 (round-7 G2 findings), 4, 5, 10, 11 | REJECT | G2-R8-B1, G2-R8-B2 | none |
| G3 | 0 (round-7 G3 findings), 1, 2, 6 (units), 8 (years), the Q1–Q3 sweep | REJECT | G3-R8-B1 | G3-R8-c1 (coverage, non-blocking) |
| G4 | 0 (integrity), 12, 13, 14 | REJECT | G4-R8-B1 | O-R8-1 (observation); G4-O1 re-examined, which stands; the hosted-CI gap at this head |

The seat's ruling on every finding is in `SEAT_RULING_T1_ENVELOPE_R8_2026-09-29.md`, beside this record.

---

## Group G1: families 0, 3, 9, 15 and 16 (verbatim)

# OPUS T1 envelope audit, round 8, group G1 (families 0-G1, 3, 9, 15, 16) at e6f49ceccb85ca1feedab0876f947a042224992f

Status at writing: INTERIM (written early by instruction; sections are appended as families finish).

## Pre-run state
- `$WT`: `git rev-parse HEAD` = e6f49ceccb85ca1feedab0876f947a042224992f; `git status --porcelain` empty (before first run).
- Mutable tree: `g1/tree/` = `cp -R` of `config/ engine/ tests/` from `$WT`.

## G1-R8-B1 (BLOCKER, bar d; S-R7-3's class beyond the seat's sweep) -- a long decimal character reference raises ValueError on the public path, in the envelope's admission, and in the validator
- Construct: `&#` + 4,300 zeros + `49;` (4,302 digits). By the WHATWG numeric-character-reference state a browser accumulates the value (zeros add nothing) and prints `1`; a large non-zero run is
  capped and prints U+FFFD. html5lib 1.1 itself raises the same ValueError (its tokenizer calls `int()`, `_tokenizer.py:93`), so the Python reader is no oracle here; the browser argument is. `html.unescape` converts the digit run with `int()` and raises
  `ValueError: Exceeds the limit (4300 digits) for integer string conversion` on 3.11, 3.12 and 3.14 (stdlib `html/__init__.py:98 _replace_charref`).
  The hex form (`&#x` + 5,000 digits) does not raise (stdlib reads hex without the limit).
- The seat's sweep (R181) enumerated the engine's own `int()` calls over bounded regex runs and missed every `html.unescape` call, each of which
  runs an unbounded `int()` over source digits.
- Raising sites at HEAD (3.12 venv312_min, Q1-Q3, all 3 quarters identical):
  - release parser, public path: `engine/fundamental_forensics/disclosure_diff.py:905` `handle_charref` -> `html.unescape(f"&#{name};")` (text anywhere, the pinned cell included);
    attribute values: stdlib `HTMLParser.parse_starttag` (parser.py:435) unescapes attribute values;
  - envelope admission: `engine/company_intelligence/pg_envelope.py:745` `_unassigned_character` -> `html.unescape(source)` over the WHOLE source, so the construct inside a
    comment or `script` (which the release parser never decodes) still raises in `admit()`;
  - validator: `validate_selected_facts` -> `_validate_envelope_rows` -> `_pg_envelope.admit` (economic_observations.py:379) raises ValueError instead of refusing.
    Also `_units` (pg_envelope.py:148), `_drops_a_reference`/`_whole_printed_token`/`_validate_envelope_span` (economic_observations.py:275, 289, 343-355) call `html.unescape` on source fragments.
- Provenance: the release parser's `handle_charref` exists at the merge base 8a8ecbe868ff (`disclosure_diff.py:700-701`), so the release-parser half is inherited
  by the public path; `_unassigned_character` (R178), the span check (R174/R185) and the validator's admission call are this PR's code and raise independently of it.
  The bar (d) wording covers both: "An exception escapes build_event_workspace, the release parser on the public path, or the validator (R134, R176, R181, R183)."
- Probes: `test_g1_r8_B1_*` (21 cases: 15 public path over 5 placements x Q1-Q3, 3 admission, 3 validator). Observed: ValueError in each. Expected: a refusal (or a build), never an exception.
- Command: `cd g1/tree && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. $MY/venv312_min/bin/python -m pytest -p no:cacheprovider -q g1/test_envelope_audit_probes_r8_g1.py`

## G1-R8-n1 (nit, cost; R179) [downgraded from minor after the public-path measurement] -- `_named_years` is quadratic in a header value's year count
- `pg_envelope.py:943`: `_YEAR_BEFORE.search(text, 0, match.start())` re-scans from position 0 for every `20dd`. Measured (3.12): 1,000 years 0.19 s, 2,000 0.80 s, 4,000 3.11 s (a 20 KB header cell).
  Not an exception, not a wrong bind. On the public path the cost did not materialise: 500/2,000/4,000 plain years prepended to the header cell over the Q3 diluted EPS
  build in 0.4 s and validate in 0.2-0.3 s (the pin is unlocated before the quadratic loop dominates). Code-quality nit only. Probe `test_g1_r8_m1_named_years_is_linear[*]` (fails by design: it pins the helper's complexity).

## Family 0 (G1 part): round-7 G1 probe file re-run at HEAD
- Command (from `g1/tree`): `F16_OUT=g1/f16_31x.tsv <py> -m pytest -p no:cacheprovider -q -rf --tb=line $MY/audit_t1_envelope_r7/g1/test_envelope_audit_probes_r7_g1.py`
- 3.12 (`venv312_min`): **5 failed, 909 passed in 661.78s** (`g1/p7_312.log`). 3.14.7 with html5lib (`/opt/homebrew/bin/python3`): **5 failed, 909 passed in 635.76s** (`g1/p7_314.log`).
- The five are exactly the seat's R7-record table: `test_f0_B2_odd_character_beside_a_pinned_literal_is_refused[&#11-before-{Q1 SALES, Q2 CORE, Q3 PDIL}]`
  (R7-G1's own construction: `&#11` + `1.63` reads `&#111` = `o`, the pin is unlocated and the workspace validates -- the probe's `not pres` is over all
  metrics, the targeted metric is unlocated; no wrong value) and the `title`/`iframe` note controls R180 prices as coverage cost (PCORE unlocated, fail-closed).
  No outcome differs from the seat's table.
- G1-B1 (R7, raw text in the note) and G1-B2 (R7, dropped reference in the note) closed on their constructions (`test_g1_B1_r7_*`, `test_g1_B2_r7_*` pass on both).
  Variants: fuzz8's `note` weight (15%) places raw text in each spelling, mixed-case `SCRIPT`/`Style`, unclosed `script`, `plaintext`, `&nbsp` without
  semicolon, hidden `div`, comment-held `<table>`, and every reference in CONSTRUCTS into the note region of Q1-Q3 (family 15 below).
- G1-m1 / S-R7-3 closed on their constructions (seven-thousand-digit and ten-digit colspan: R7 suite, 971 passed in capture8's run). **But S-R7-3's CLASS is open: G1-R8-B1 above.**
- S-R7-2 (R185): see family 3.

## Family 16: R179 / R180 / R184 readers across interpreters
- Script `g1/f16_r8.py`, output `g1/f16_r8.out`: every code point 0..0x10FFFF except surrogates (1,112,064), on 3.11.10 (Unicode 14.0), 3.12.13 (15.0), 3.14.7 (16.0).
  Readers hashed: `_ODD_CHARACTER` (78 hits), `_YEAR_BEFORE` after `FY<c>`, `_YEAR_AFTER` on `<c>x`, `_named_years("2025<c>2026")`, `html.unescape` of `&#N;` and `&#xN`,
  `_drops_a_reference(&#N;)` (94 hits), `_LAYOUT_SPACE` membership, `str.isspace` (29), `_parse_period_title` with the character in the day, `_units`, `html.entities.html5`.
  **All digests identical on the three interpreters.** (A first run hashed `repr()`, which differs by interpreter through `str.isprintable`; harness artefact, replaced by JSON.)
- Later-Unicode argument: R179's grammar (`[A-Za-z0-9]`, space), R184's layout set and R185's `_LAYOUT_SPACE` are closed ASCII/fixed sets and cannot move.
  Two readers can: `_ODD_CHARACTER`'s `[^\S ...]` (regex White_Space) and the span check's `str.isspace` (economic_observations.py:343, 353).
  White_Space is not a Unicode-stable property (U+180E left it in 6.3). A code point assigned in 3.2 that a later Unicode makes White_Space would move from
  admitted to `character`-refused (fail-closed, but an interpreter-dependent outcome, bar d, only on a document carrying it). No such change occurred in 14.0->16.0
  (the 29/78 counts are equal). Recorded as an observation (G1-R8-O1), not a finding: it is unreachable on every installed interpreter and R178 already names the class.

## Family 3: tokenizer, characters and receipts (R143, R154, R172, R175, R184, R185)
- R8 probe file, family-3 cases (`test_g1_r8_f3_*`, 46 cases), all through R143's seam on the Q3 diluted-EPS receipt, as the frozen suites build them:
  - 41 glued forms, each of which a WHATWG reader prints inside a longer token: legacy named references without semicolon before/after the literal
    (`&copy1.63`, `&amp1.63`, `&not1.63`, `1.63&copy`, `1.63&not`), across a comment or a tag (`&amp<!-- -->1.63`, `&copy<b></b>1.63`, `1.63<!-- -->&amp`),
    `&#11.63`, RCDATA/RAWTEXT forms (`<textarea>&not1.63`, `<title>&amp1.63`, `<xmp>&nbsp;1.63`, `<xmp>1.63&nbsp;`, `<xmp>&#32;1.63`, `<iframe>&amp;1.63`,
    `<noscript>1.63&nbsp`), the 13 Zs/format characters of the R184 pointer (U+1680, U+2000, U+2002, U+2007, U+2009, U+200A, U+202F, U+205F, U+3000,
    U+180E, U+200B, U+FEFF, U+2060) after `-`, six of them across markup, and six references to them (`&#x2007;`, `&numsp;`, `&ZeroWidthSpace;`, `&#x200B;`, `&NoBreak;`, `&#133;`).
    **All refused on 3.12 and 3.14** (none accepted).
  - 6 controls a reader prints as a whole token (`&#x31;.63`, `&#0049;.63`, `&Tab;1.63`, `&NewLine;1.63`, `-<b></b>&Tab;1.63`, `&nbsp 1.63`): accepted (inside R176/R182).
    (A first draft of two controls put `-` in R155's gap -- `<p>-&Tab;1.63</p>` -- which R155 refuses correctly; harness error, corrected.)
- R185's five checks read every glued form alike with a WHATWG reader; no acceptance outside R182 was constructed. html.unescape's tables (numeric remaps 0x80-0x9F,
  0x00/0x0D/surrogates/>0x10FFFF -> U+FFFD, legacy-name longest prefix) agree with the WHATWG tokenizer in text for every code point (family 16 digests), except:
  - **the digit-count limit (G1-R8-B1)**: WHATWG accumulates any number of digits; Python's `int()` refuses > 4,300, and every `html.unescape` call in the engine and the
    release parser raises. This is the only html.unescape/reader divergence found, and it is an exception, not a reading.
- R181 pointers (leading zeros `0000001`, `+1`, `1%`, `1px`, `" 1 "`, 999/1001, 65534/65535, `rowspan="0"`/`"00"`, `1e3`, `1.5`, `-1`, `\t2`, 10-digit, `0065534`)
  are in fuzz8's ATTRS on the pinned cells' start tags; every such document is refused `span`/`grid` or admitted with 0 grid divergences (family 15).
- The seat's sweep bounds (S-R7-3 class): every `int(`/`float(` in pg_envelope.py, pg_profile.py, economic_observations.py and disclosure_diff.py was re-read
  (`grep -n 'int(\|float('`): the engine's own conversions are bounded by their patterns as the seat says (`_spans_read_alike` `[1-9][0-9]{0,4}`, R181's
  six-digit clamp, `20[0-9]{2}`, `[0-9]{1,2}`, `[0-9]{4}`, heading `[1-6]`), and `float()` reads infinity (a 400-digit comma figure in the Q3 diluted-EPS cell is
  unlocated and the workspace validates). **The sweep's bound is wrong in one place: it did not count stdlib conversions -- `html.unescape` (and html.parser's
  attribute unescaping) call `int()` on an unbounded source digit run. G1-R8-B1.**
- Surrogates: a Python `str` carrying a lone surrogate raises UnicodeEncodeError in `normalize_filing` (release binding). Not reachable from source BYTES
  (no UTF-8 decode yields one); recorded, not a finding.

## Family 9: labels and tables (R148, R149, R158, R163, R171)
- R8 probe file `test_g1_r8_f9_*`: 15 constructs (`<table>`, stray `</table>`, nested unclosed `<table><tr><td>9.99`, a table split mid-row, `</table>` and a row
  inside comments in five comment forms incl. `<!--->`/`--!>`/`<!-->`, CDATA and PI holding cell tags, an unclosed `<td>`, `</td><td>9.99</td><td>`, `<tbody>`)
  x value and label position x 7 pinned metrics (SALES, ORG, DIL, CORE, PDIL, PCORE, BEAUTY) x Q1-Q3 = 630 cases.
  Bar: every present value equals the original's; a refused document carries no present fact; the workspace validates; nothing raises.
  **630 passed on 3.12** (and 3.14 below). Round-7 G1's family-9 cases (`test_f9_r171_tags_in_comments`, `test_f9_fiscal_year_transplant_into_every_pinned_role`)
  pass at HEAD on both interpreters (inside the 909).

## Family 15: the grammar and characters against html5lib 1.1 (/opt/homebrew/bin/python3, 3.14.7, lxml 6.1.3)
- Tools: `$MY/audit_t1_envelope_r6/g1/g1lib.py` (engine grid vs reader grid by the HTML table model, itertext collapsed) plus `g1/g8.py` (new this round: the
  prior-year note region as html5lib prints it between the core reconciliation and the next table, script/style dropped; and every present row's decoded
  receipt against the whitespace tokens of the reader's cell).
- (i) The six originals: F1-Q notes agree (Q1 absent/absent, Q2 and Q3 present/present), 0 receipt divergences, 0 grid divergences.
- (ii) `g1/capture8.py` + `g1/capture8b.py`: build_event_workspace wrapped in-process while the EIGHT frozen suites ran (**971 passed** in each run, 421 s and 706 s);
  **680 distinct sources**, 518 admitted F1-Q. Grid/title: **0 divergences** on the 518. One harness exception: g1lib's own `int()` on R181's 7,000-digit colspan
  (not the engine; the engine refuses that document `span`). Note: 415 present/present, 96 absent/absent, 7 engine-absent/reader-present (R180's priced costs:
  the frozen `title`/`iframe`/`noscript`-style and odd-character witnesses outside the sentence). Receipts: **0 divergences**. Exceptions: 0.
- (iii) `g1/fuzz8.py` (fuzz7's list plus every R8 pointer: R185 references and legacy names, the R184 Zs/format set, R179 year forms, R180 note constructs,
  R181 span values; new weight `note` 15% on the note region), **seed 20260928**, 5,000 documents in 2 shards (`g1/fuzz8_0.jsonl`, `g1/fuzz8_1.jsonl`, aggregate `g1/fuzz8_agg.txt`):
  - **0 exceptions**; **1,073 admitted**; admitted grid/title divergences **0** (pinned 0, other 0); receipt divergences **0**; note divergences 23, all engine-absent /
    reader-present (fail-closed: U+3000, U+2000, U+1680, U+2028, \x00, `&#011;`, `&#xFFFE;`, `<title>`, `<noscript>`, `<noembed>` placed in the note REGION);
    **0 engine-present / reader-absent**.
  - Refused 3,927: table 1,014, tag 431, span 430, element 411, character 313, unknown_table (t2..t12) ~1,100, comment 70, lt 56, gt 20, grid 4, others
    (issuer/exhibit gates). 3,025 of 3,927 have the reader's grid equal to the original on the pinned cells (coverage cost, see below).
- Coverage findings (non-blocking): R180 leaves the note absent when an odd character, a dropped reference or printed raw text sits ANYWHERE in the region
  (not only in the sentence); the region is the whole gap to the next table. In SEC EX-99 exhibits U+3000/U+2028/`&#011;`/`<title>` in body prose are rare
  (my estimate well under 1% of Workiva-generated exhibits); stray U+00A0 is common and is correctly treated as layout. The `span` refusals with an equal
  reader grid are R163's ASCII grammar on `colspan="+1"`/`" 1 "`/`0000001`/`1px` (the reader reads 1): rare in Workiva output (it prints `colspan="3"`),
  estimate < 0.1%.

## Verdict for G1's families
- **REJECT** on G1-R8-B1 (bar d): a decimal character reference longer than 4,300 digits raises ValueError out of build_event_workspace (release parser
  `disclosure_diff.py:905` and HTMLParser attribute unescaping), out of the envelope's `admit()` (`pg_envelope.py:745`, R178), and out of `validate_selected_facts`
  (`economic_observations.py:379` via `admit`), on 3.12 and 3.14, Q1-Q3, wherever the reference sits (text, cell, attribute, comment, script).
- Closed: G1-B1, G1-B2, G1-m1 and S-R7-3 on their constructions; S-R7-2 (R185) on 41 new glued forms and 6 controls; family 9 on 630 cases; family 16 over all 1,112,064
  code points on 3.11/3.12/3.14. Nit G1-R8-n1 (quadratic `_named_years`), observation G1-R8-O1 (White_Space is not Unicode-stable).
- Post-run: `` HEAD and status re-checked (see the RETURN evidence).

---

## Group G2: families 0, 4, 5, 10 and 11 (verbatim)

# G2 — round-8 audit of PR #7905 at e6f49ceccb85 (families 0, 4, 5, 10, 11)

STATUS (G2 scope): **REJECT** — bar (c) G2-R8-B1; bar (d) G2-R8-B2. (Written incrementally; see the "Family status" section for what finished.)

Pre-run: `git rev-parse HEAD` = e6f49ceccb85ca1feedab0876f947a042224992f, `git status --porcelain` empty (0 lines).
Probe file: `test_envelope_audit_probes_r8_g2.py` (78 cases). At HEAD: **33 failed, 45 passed on 3.12 (venv312_min) and on 3.14 (venv_t1)**.
The 33 failures are exactly the findings: 24 G2-R8-B1 + 9 G2-R8-B2. All 45 controls pass.

## Static read (family 4 independence)
- `_validate_envelope_span` (`economic_observations.py:318-363`) and `_whole_printed_token` (`:280-315`) read only the source bytes, the row,
  `html.unescape`, the regex `_PRINT_UNIT` (`:236`), and from the engine only the constant `_pg_envelope._RAW_TEXT_CLOSE` names (`:242`) and the
  literal grammar `_pg_envelope._literal` (`:360`). No call to receipts, tokenizer, cell reader, `_document`, `admit`, `extract` or replay. Independent.
- But its separator set `_SEPARATING = {td, th, tr, table, p, div, br}` (`:241`) counts **every** such tag, start or end, as a token boundary,
  whether or not an HTML5 tree builder acts on it. That is G2-R8-B1.

## Findings

### G2-R8-B1 (BLOCKING, bar c; R176 as R182 restates it): a relocation glued to printed text through a tag a reader ignores is accepted
- A stray end tag with no element in scope (`</div>`, `</td>`, `</th>`, `</tr>`, `</table>`, any case/whitespace) is ignored by the HTML5
  tree builder ("parse error; ignore the token"), so the characters on either side land in ONE DOM text node. `_whole_printed_token`'s
  `separated()` (`:293-304`) returns True as soon as it meets a unit of kind `separator` (`:297`), so the span check calls the literal set off.
- Construction: Q3 original, insert `<p>-</div>1.63</p>` after the text (outside the tables), reseat PDIL's receipt onto `1.63`.
  Document admitted `F1-Q`. **Validator through the seam: `ok`**, value 1.63. html5lib 1.1 (`/opt/homebrew/bin/python3`): the `<p>`'s text
  node is `-1.63` — a reader prints the token `-1.63`, not `1.63`. Same for `<p>Zq</div>1.63</p>` (reader node `Zq1.63`) and trailing
  `<p>1.63</div>Zq</p>`.
- Without the seam, replay refuses every one ("selected observation does not replay from source bytes") — so this is the "not whole as a
  reader prints it" arm of the bar, not the replay arm.
- Scope: Q1, Q2, Q3; `</div>`, `</td>`, `</th>`, `</tr>`, `</table>`, `</DIV >`; after a minus, after a letter, before a letter.
  Explorer `x_stray.py` (3.14 + html5lib, Q1 and Q3): 10 of 10 stray-tag forms admitted F1-Q and accepted, all glued in html5lib's DOM.
  Controls: `</p>` stray (the builder inserts an empty `<p>`), `<br>`, `</br>` and `<p>…</p><p>…</p>` are real boundaries and are rightly accepted.
  Stray *start* tags (`<td>`, `<th>`, `<tr>` outside a table) and `<select>`/`<plaintext>` contexts are refused at admission (`table`/`element`).
- Probe: `test_g2_r8_b1_relocation_glued_through_a_tag_a_reader_ignores_is_refused[*]` (8 forms × Q1–Q3 = 24). All 24 fail at HEAD on
  3.12 and 3.14 with `assert 'ok' != 'ok'`. Expected: refused (e.g. "not a whole printed token"). Controls
  `test_ctl_g2_r8_b1_*` (9) pass.
- Repair direction (for the seat): a separator counts only where the tree builder creates or closes an element — at minimum an end tag
  counts only if a matching element is open; or drop end tags other than `</p>`/`</br>` from `_SEPARATING`.

### G2-R8-B2 (BLOCKING, bar d; R183 pointer names lone surrogates): a lone surrogate raises UnicodeEncodeError out of the validator
- JSON-carriable: `json.loads('"\\ud800"')` yields `'\ud800'`.
- Workspace `event_id = '\ud800'`: it passes R183's `isinstance(event_id, str)` (`:377-378`), replay calls `extract` (`:388`) →
  `pg_envelope.py:1256` → `pg_profile.py:1913`, which encodes the identity: `UnicodeEncodeError` escapes `validate_selected_facts` (`:573`).
- A present row's `period = '\ud800'` (with or without its `fact_id` recomputed): `_fact_id` (`:100-102`) `.encode('utf-8')` raises;
  R183's handler at `:168-171` catches only `RecursionError`. Traceback `:435 → :216 → :169 → :102`.
- Q1, Q2, Q3; 3.12 and 3.14 identical.
- Probe: `test_g2_r8_b2_a_lone_surrogate_is_refused_not_raised[*]` (3 × Q1–Q3 = 9). All fail. Expected: `EconomicObservationError`.

## Family 0 — round-7 G2 findings (re-probed at HEAD)
- R7 G2 file `audit_t1_envelope_r7/g2/test_envelope_audit_probes_r7_g2.py`: **18 failed, 23 passed on 3.12 and on 3.14** — the seat's table.
  The 18 are G2-B1's relocations, now ruled accepted by R182 (verified: each is refused by replay without the seam, R182's condition).
- Variants (`x_f0.py`, Q1–Q3, both interpreters), all refused, 0 raised, except the surrogates (G2-R8-B2):
  - G2-B3: value `10**309`, `-Fraction(10**400,7)`, `Decimal('sNaN')`, `Decimal('1e400')`, `Decimal('NaN')`, on the first and last present row: refused.
  - G2-B4: event_id `7.0`, `True`, `{"a":1}`, `""`: refused. `'\ud800'`: **raises (G2-R8-B2)**.
  - G2-B5: sources `"abc"`, `{}`, `[]`, `[None]`, `[["x"]]`: refused.
  - G2-m2: `source_span` list-nested 100,000 deep, period dict-nested 100,000 deep, absent row's `typed_absence` 100,000 deep, unit 1,001 deep: refused on both.
  - S-R7-1: period set, `[(1,2)]`, dict, list (fact_id recomputed): refused. Surrogate: **raises (G2-R8-B2)**.
- G2-B3, G2-B4 (non-string types), G2-B5, G2-m2 and S-R7-1 are closed on their constructions and the variants above.

## R166's limit (pointer)
- `<p><!-- x>1.63<y --></p>` outside the tables: accepted through the seam, refused by replay without it (Q1–Q3; control
  `test_ctl_g2_r8_r166_limit_*`). A plain `<p><!-- 1.63 --></p>` is refused by R155's gap (the gap reads `<!-- `).
- R182 covers it only by enumeration ("inside a comment within a table"); a reader prints nothing there, so "a whole token … as a reader prints
  it" does not literally hold. Not counted as a finding because R182 names the comment case explicitly; the seat should say so in R182's text.

## Family 4 — past the gate
- `test_ctl_g2_r8_a_workspace_built_past_the_gate_is_refused[*]`: every `r5.UNREADABLE` construction plus `span` (colspan 1001, rowspan 70000)
  and `character` (raw U+0378, `&#x378;`), built with `_unreadable_markup` and `_unassigned_character` replaced: every one binds present rows and
  the validator refuses every one, on 3.12 and 3.14, 0 exceptions.

## Family 10 — replay completeness (`fam10.py` driven by `fam10m.py`)
- Harness: `fam10m.py` memoises `bind_release_document` and `extract` on their full argument identity (`memo.py`), a speed-up only
  (both are pure; family 5 below measures the determinism this relies on). Without it one case took >1 h.
- Tamper set per leaf of every `pg_` row (present, conflict, excluded; unlocated via `mut:note_removed`; refused-document via `refused:comment`):
  `add_key`, `del_key`, `mut` (+1 / +0.5 / +"x" / not), `mut_case`, int→float, float→int, bool→int, **int→bool (`True` for 1)**, list→tuple, and
  the R183 set on every leaf on every quarter: `10**400`, `-(10**400)`, `-0.0`, `2**63`, `True`, `False`, `"\ud800"`, `{1: 2}`,
  list nested 999 and 1,001 deep, `bytearray`, `inf`, `""`, plus 5, None, {}, [5], Decimal, set, bytes, NaN.
- **3.14, Q1 + Q3 (`fam10full_Q3,Q1_14.jsonl`): 30,634 tampers, 40 accepted, 38 raised.**
  - The 38 raised are all `period := "\ud800"` on the 19 present rows of each quarter — **G2-R8-B2** (`UnicodeEncodeError`).
  - The 40 accepted are all invisible to JSON and inside R176's rule: `source_span.unreplayable_reason` null→null (`x_none`, the value is
    already null) on each present row, and `typed_absence.missing_fields` list→tuple on the excluded row.
  - No int↔float, int↔bool, `-0.0`, `2**63` or non-string-key acceptance. Every other tamper refused with `EconomicObservationError`.
- Identity renames (R150): renaming `event_id` everywhere is refused ("fact_id does not follow …"); renaming the document id is refused
  ("does not replay"). So no field is exempt in this construction — stricter than R150 allows, not a finding.

## Family 11 — no-exception fuzz and differential (`fam11.py`, round-7 edit set)
- **3.12 (venv312_min), Q1–Q3, 2,400 s budget: 3,516 documents** (Q1 1,175, Q2 1,132, Q3 1,209); 1,920 admitted F1-Q; refused under every
  `markup_unreadable` kind (character 311, comment 198, table 115, span 96, element 69, tag 52, lt 35, gt 33, grid 4), `unknown_table` and
  `quarter_mismatch`. **0 exceptions from the build, 0 from the validator, 0 own outputs rejected, 0 divergences over 34,450 present rows**
  between `html.unescape(source[span])` and the cell literal after R118 normalisation.
- **3.14, Q2 + `mut:period_single` (conflict rows) + `mut:note_removed` (unlocated row) + `mut:basis_both` (conflict rows) + `refused:comment`
  (20 refused-document rows, detail `envelope_refused:markup_unreadable:comment`) (`fam10full_Q2,…_14.jsonl`): 64,618 tampers, 100 accepted, 70 raised.**
  - The 70 raised are all `period := "\ud800"` on present rows (Q2 19, period_single 17, note_removed 18, basis_both 16) — G2-R8-B2.
  - The 100 accepted: `unreplayable_reason` null→null on every present row (70) and `missing_fields` list→tuple on every absence row
    (conflict, unlocated, excluded, refused: 30). Both invisible to JSON; inside R176's rule.
  - Refused-document rows: 6,220 tampers, 0 raised, only list→tuple accepted. Renaming the document id on refused-document rows is
    accepted — exactly R150's exemption (`document_id` on absence rows); renaming `event_id` is refused (fact_id).
- **Total on 3.14 over all three quarters and all five row kinds: 95,252 tampers; 140 accepted (all JSON-invisible, R176); 108 raised, every one G2-R8-B2.**
- **3.14, Q1–Q3, 1,800 s budget (`fam11v3_Q1_Q2_Q3_14.jsonl`): 3,117 documents** (Q1 616, Q2 1,196, Q3 1,305), 1,712 admitted F1-Q.
  **0 build exceptions, 0 validator exceptions, 0 own outputs rejected, 0 divergences over 30,719 present rows.**
- Both interpreters together: 6,633 documents, 65,169 present rows, 0 exceptions, 0 divergences. The fuzz edits are the round-7 set; the
  validator-side tamper classes (G2-R8-B2) and the relocation class (G2-R8-B1) are outside what this family edits, so its clean result does
  not contradict them.

## Family 10 (cont.) — the seven other refused-document kinds and past the gate (`fam10b.py`, 3.14)
- One construction per `markup_unreadable` kind (element, grid, gt, lt, span, table, tag): built normally → 20 refused-document rows each,
  validator `ok`; **16,240 tampers over their rows: 0 accepted, 0 raised.**
- The same seven built past the gate (`_unreadable_markup`/`_unassigned_character` replaced): 17–19 present rows each, and the validator
  refuses every one ("does not replay from source bytes"). With the probe file's past-gate controls this covers every admission kind,
  `character` and `span` included.

## Family 5 — determinism (R144, R178)
- Corpus: every distinct (source, scope) that reached `_admission` while the R5, R6 and R7 suites ran (`capture_plugin.py`; 495 passed):
  **405 documents**, 302 admitted F1-Q, the rest refused as character 23, table 21, span 11, element 10, comment 7, tag 5, lt 2, grid 2,
  `unknown_table` 11, `not_ex_99_1` 2 — so R156, R158, R159, R163 (refused and admitted), R164, R165 and R168–R185 constructions are all in it.
- Per document: admission code, sha256 of the `pg_` rows' JSON (sort_keys, ensure_ascii=False), row order, and the validator's verdict on
  the extractor's own output. Separate processes:
  PYTHONHASHSEED ∈ {0, 1, 42, 4294967295} × LC_ALL ∈ {C, tr_TR.UTF-8} × {3.12 venv312_min, 3.14 venv_t1} = **16 runs: all 16 result files
  identical** (so identical across interpreters too); validator `ok` on all 405 in every run.
- Interleaved in one process (`fam5run.py interleave`): 4 passes over the 405 documents in reversed/shuffled order, equal-but-distinct string
  objects, random `cache_clear()` of `_structure`, `_unreadable_markup`, `_cached_document` and `_printed_units` (405 ≫ maxsize 8/4, so every
  cache runs cold and warm): 3.14 **1,620 runs, 0 mismatches**.
- Bound: the comparison is on the `pg_` rows, admission and verdict, not on the whole workspace JSON (non-`pg_` rows are G4's a5a comparison).
- 3.12 interleave: **1,620 runs, 0 mismatches**.

## Family 10 (cont.) — 3.12
- Q3 (`fam10full_Q3_12.jsonl`): 15,317 tampers with the full R183 set; 20 accepted (19 `unreplayable_reason` null→null, 1 list→tuple),
  **19 raised = G2-R8-B2** (`period := "\ud800"`). Identical classes to 3.14; the deep (999/1,001) values are refused on 3.12 too, so
  G2-m2's interpreter split is closed.
- `fam10b.py` on 3.12: 16,240 tampers, 0 accepted, 0 raised; the seven kinds past the gate refused, as on 3.14.

## Family 4 (cont.) — past the gate with relocation (`fam4g2.py`, 3.12 and 3.14)
- 33 constructions over the eight R163 kinds (comment 4, element 6, grid 2, gt 1, lt 2, span 6, table 7, tag 5), each built past the
  gate with PDIL relocated onto a new `<p>1.63</p>`: 31 bind the relocated literal; **0 accepted** on either interpreter.

## Family 4 (cont.) — shifts and relocations over all 57 present rows of Q1–Q3 (`fam4.py`, 3.14; `fam4full_Q1,Q2,Q3_14.jsonl`)
- **4,124 runs, 0 exceptions.** One-byte shifts, widenings and narrowings: 429 run, **0 accepted**.
- Relocations outside the tables (39 targets × 57): 2,223 run, **1,083 accepted**, 741 refused at admission, the rest refused by the check.
  Accepted targets (19 × 57): prose `<p>`, bare, spaced `<div>`, bracketed comment, script/style outside tables, title, textarea, xmp,
  iframe, noembed, noframes, noscript, `display:none`, `hidden`, `&nbsp`-prefixed (R185 control), wrapper description, after `</html>`. Every
  one is a whole token under R176/R182 and each is refused by replay without the seam (R7 G2 / seat). **The 57 `&#1;`-prefixed relocations
  (`dropped_cp`) now refuse** — R185 closes the misclassification the seat recorded; this reproduces the seat's re-run exactly (1,083 stand).
- Relocations into the tables (9 targets × 57): 513 run, 228 accepted (bracketed comment in the pinned cell, in the pinned row, between rows;
  new row cell) — **inside R182 as ruled**. Another cell printing the same literal: 958 of 959 accepted — inside R182.
- The fam4 target list does not contain the stray-end-tag form; G2-R8-B1 is the class it missed (`x_stray.py`, probe file).

## Family status and search bounds (probes run / failed)
| family | runs | findings |
|---|---|---|
| 0 | R7 G2 file 41 × 2 interpreters (18 fail = R182's accepted relocations, as tabled); 29 variants × Q1–Q3 × 2 | G2-R8-B2 (surrogate variant of G2-B4 / S-R7-1) |
| 4 | fam4 4,124 (3.14); x_stray 22 forms × Q1, Q3 (3.14 + html5lib); past gate: 33 relocated × 2 interp, 7 kinds (fam10b) × 2, probe controls 33 × 2 | G2-R8-B1 |
| 5 | 16 separate-process runs × 405 docs; 2 × 1,620 interleaved | none |
| 10 | 3.14: 95,252 tampers (Q1–Q3, conflict, unlocated, excluded, refused) + 16,240 (seven kinds); 3.12: 15,317 (Q3) + 16,240 | G2-R8-B2 (108 + 19 raises) |
| 11 | 3.12: 3,516 docs; 3.14: 3,117 docs; 65,169 present rows | none |

Probe file: 78 cases; **33 failed / 45 passed on 3.12 and 3.14**. Post-run: `git rev-parse HEAD` = e6f49ceccb85…, `git status --porcelain` empty.

## GAPS
- `fam4.py` (the 4,124-run shift/relocation sweep) ran on 3.14 only. The span check is bytes + regex + `html.unescape`; family 5 shows
  identical outputs on both interpreters over 405 documents, and the G2-R8-B1 probes fail identically on 3.12 and 3.14.
- Family 10 on 3.12 covered Q3 plus the seven refused kinds, not Q1/Q2 (each 3.14 case ~15k tampers; the 3.12 Q3 classes equal 3.14's).
- Family 11 is budget-bounded (6,633 documents across both interpreters), not exhaustive, and reuses round 7's edit set.
- Family 5 compares the `pg_` rows' JSON, admission, row order and verdict, not the whole workspace JSON.
- G2-R8-B1's reader evidence is html5lib 1.1's DOM (text-node level); no browser was run. The tree-construction rule cited (a stray end tag
  with no element in scope is ignored) is the WHATWG algorithm html5lib implements.

## DEVIATIONS
- Family 10 ran through `fam10m.py`/`memo.py`, which memoise `bind_release_document` and `extract` in-process (pure functions, keyed on
  every argument) — a harness speed-up; unmemoised, one case exceeded an hour. The probe file does not use the memo.
- The round-7 `fam10.py` tamper set was widened (the R183 pointer's values on every leaf of every quarter, int→bool); outputs carry the
  interpreter in their file names.
- A redundant second 3.14 interleave run inside the queued job was stopped after the equivalent early run had finished.

---

## Group G3: families 0, 1, 2, 6 and 8, and the Q1–Q3 sweep (verbatim)

# G3: Opus R8 audit (units, years, Q1/Q2/Q3 sweep), CDV-1 T1 envelope at e6f49ceccb85ca1feedab0876f947a042224992f (PR #7905)

## STATUS: REJECT. One blocking finding (G3-R8-B1, bar e). R179 closes G3-R7-B1's eight forms and their variants on all three quarters, but leaves the same class open: a year printed as an amount with a one-letter magnitude or multiple suffix.

Preconditions: in `$WT`, `git rev-parse HEAD` was `e6f49ceccb85ca1feedab0876f947a042224992f` and `git status --porcelain` was empty before the first run (the after-last check is at the end). Every run used a copy of `config/ engine/ tests/` in `g3/tree/`, with `PYTHONDONTWRITEBYTECODE=1` and pytest `-p no:cacheprovider`. Nothing was written in `$WT`.

## Findings

### G3-R8-B1: blocking (bar e; R179 as stated, "a year is named only where a reader reads one"; the class of G3-R7-B1). A year printed as an amount with a letter suffix still names the year.
- **Code.** In `engine/company_intelligence/pg_envelope.py:58`, `_YEAR_AFTER` accepts ` *[A-Za-z0-9]` after a `20dd`, and `_YEAR_BEFORE` (`:57`) accepts `[A-Za-z0-9] *` and `[A-Za-z0-9]-` before one. `_named_years` (`:937-948`) therefore names 2026 in `2026M`, `2026m`, `2026k`, `2026K`, `2026B`, `2026x`, `2026 million`, `2026 bn`, `2026 bps`, `2026 shares`, `2026 per share`, `USD 2026`, `2026 USD`, `x2026`, `A-2026`, `2026-A` and `Item 2026`. The rest holds no numeric character, so `_header_years` (`:918-934`) returns `{2026}`, and `_period_matches` accepts it. This was measured with a direct `_named_years` bank on 3.14; it is listed in the evidence below.
- **Construction.** The same as G3-R7-B1, on each quarter's own title year:
  - remove the year from the governing title (`Three Months Ended <M> <D>, 20dd` loses `, 20dd`);
  - add one banner row across the table whose only text is the form.
- **Observed.** CORE and PCORE are present at their original values, and the workspace validates. For `2026M`/`2026k`/`2026x` over the current title and `2025M` over the prior title, and so on:
  - Q1: CORE 1.99 and PCORE 1.93;
  - Q2: CORE 1.88 and PCORE 1.88;
  - Q3: CORE 1.59 and PCORE 1.54.
  - The probe `test_BLOCK_g3_r8_b1_year_printed_as_an_amount_with_a_letter_suffix_is_unlocated` fails in all 54 cases on 3.12 (`venv312_min`) and on 3.14. That is 9 forms (`{y}M`, `{y}m`, `{y}k`, `{y}K`, `{y}B`, `{y}x`, `x{y}`, `A-{y}`, `{y}-A`) × Q1–Q3 × CORE/PCORE, and the failure sets are identical on the two interpreters.
  - Sweep `g3lib8.sole8`, over Q1–Q3 on both interpreters, finds 28 bad judgements per quarter (84 per interpreter). Each is one of 14 forms × CORE and PCORE: the 9 above plus `{y}e`, `{y} - A`, `a, {y}`, `{y}/` and `{y},`.
- **Expected.** Unlocated. A reader reads `2026M`, `2026k`, `2026B` and `2026x` as amounts (2,026 million, 2,026 thousand, 2,026 billion, 2,026 times). That is exactly as it reads `$2026` and `2026%`, which R179 refuses. The table then states no year for the pin. `USD 2026`, bound, against `$2026`, refused, is the sharpest pair: the two print the same amount.
- **Scope of the claim.**
  - `2026,`, `2026/` and `a, 2026` are read by a reader as the year followed by punctuation. They are counted in the sweep but not argued as the defect.
  - `A-2026`, `2026-A`, `x2026` and `2026e` are identifiers or ambiguous. They are recorded as minor under the same heading.
  - The blocking core is the magnitude/multiple suffix forms (`M m k K B x`, and spelt `million`/`bn`, which the grammar also names but a word banner happens to leave unlocated through the table's signature). They are the G3-R7-B1 class that R179's finding covered (14(ii)-style: the ruling leaves open a construction its finding covered).
- **Plausibility.** Low for P&G, which prints plain years. The bar covers any byte-level edit, and G3-R7-B1 was ruled a blocker at the same plausibility.
- **Smallest repair.** Read a letter immediately after the year as naming it only for an enumerated suffix set (`E`, and whatever the originals print). Alternatively, treat a single trailing magnitude letter (`k K m M b B x X`) and a currency word/code before the year as a figure. Either repair moves toward unlocated.

## Family 0 (G3's part): the round-7 findings
- **Round-7 G3 probe file at HEAD** (`$MY/audit_t1_envelope_r7/g3/test_envelope_audit_probes_r7_g3.py`, `PYTHONPATH=.:tests:r6/g3:r7/g3`):
  - 3.12: `21 failed, 400 passed, 2 skipped in 156.52s`. 3.14: `21 failed, 400 passed, 2 skipped in 151.58s`. The failure sets are identical, and this matches the seat's table.
  - The 21 are:
    - 16 `test_BLOCK_g3_r7_b1…[*-Q1|Q2]` plus 2 `test_f8_core_year_restored…[Q1|Q2]`. These are round 7's harness error: it used FY 2026 as the title year where Q1/Q2 print calendar 2025, and the assertion is `('core_reconciliation', 2026)`.
    - 3 `test_f0_b3_controls_prior_year_pins_bind[Fiscal Year-*]`, which is O1 (coverage).
  - All 7 Q3 BLOCK cases now pass.
- **G3-R7-B1 closed** (my probe file, harness corrected to each quarter's own title year).
  - `test_f0_r7b1_year_only_as_a_figure_is_unlocated`: 150/150 pass on both interpreters. That is 25 forms × Q1–Q3 × CORE/PCORE:
    - the original eight and NONE;
    - `$ {y}`, `{y}.5`, `{y} %`, `( {y} )`, `{y}%%`, `&#36;{y}`, `{y}&#37;`, `&#40;{y}&#41;`, `{y}&#46;`, `US${y}`, `{y}(12)`, `{y}*`, `{y} (a)`, `Q3 {y}`, `{y}-27` and `2,0yy`.
  - Controls `{y}`, `{y} (1)`, `(1) {y}` and `{y}E` restore the original value and validate: 24/24.
  - Variant: the header year cells of highlights and earnings printed as `$2026`, `2026%`, `(2026)`, `2026.` or `2026M` unlocate every current-year pin under them. 20 pass, and 10 are skipped because Q1/Q2 earnings print no `2026` cell (calendar 2025 headers).
    - A first run of this variant replaced only the first of two `2026` cells in highlights, so CORE under the second stayed bound. That was a harness error, corrected; `2026M` then unlocates because the highlights signature refuses it, not by R179.
  - Sweep `sole8` finds every figure form (`$`, `%`, `()`, `.`, `.5`, `Q3 `, `3Q `, `-27`) bad 0 on Q1–Q3 on both interpreters.
- **G3-R7-m1 closed.** `test_f0_r7m1_title_non_ascii_digit_never_binds_another_value` is 12/12 on both interpreters: the day in full-width, Arabic-Indic and superscript digits, and the year's last digit full-width, on Q1–Q3. CORE is never present with another value.
- **G3-O1** (word banner over highlights), re-probed as OBSERVE ×9 (`Fiscal Year`, `Fiscal Year Ended June 30`, `Quarter` × Q1–Q3). It is unchanged and fail-closed (coverage).
- **G3-O2/O3.** Re-run through the round-7 `geo` sweep and the round-6 `fam6` sweep (see the sweep table).

## Family 1: rounds 1–6, one new variant each (my probe file, `test_f1_*`, all pass on 3.12 and 3.14)
The variants are new constructions:
- R1 F-B2: a lower-case second TYPE line on Q2.
- F-M1: a nested table inside a highlights cell on Q1.
- F-M2: a label-free table before drivers on Q3.
- F-M3: a `pg_zz_metric` row appended on Q2, refused without raising.
- R2 B1/B2: a `Nine Months Ended` / `Three and Nine Months Ended` core title on Q3.
- B3: the Q3 core title day 31→30.
- B4 and R4 P2: Q2 PCORE start+1 and CORE end−1.
- B6 and R6 G2-B2: `metric` deleted and `value` a dict, each refused without raising.
- B7, R3 N1 and R4 P1: `&nbsp;&nbsp;`, `\t \n` and `&#160;<!-- x -->` before the Q1 CORE literal; the span is exact and the workspace validates.
- B8 and R3 N2: a label-only Q2 PCORE row.
- M2 and R3 N4: `%` glued to the Q1 CORE second statement.
- R3 N6: a prior-year banner over Q3 earnings.
- N8: an unclosed table before the first table on Q2.
- R4 P4: a 400-digit literal in both CORE statements on Q2.
- R6 G3-B2: `&#x180E;%`, `%&#x61C;`, `%&#x2066;` and `&#xFE0F;%` beside Q2 CORE.
- G3-B3: `2025 and ٢٠٢٦`, `2025 / 2０26` and `2025 – 2026` banners on Q3.
- G3-B1: Q2 PDIL widened left over the current-year columns.
- G1-B1/B3: `</thead>`, `</tfoot>`, `<ISINDEX>` and `<caption>` inside the Q1 CORE cell.
- G1-B2: `&#0;`, `&#x81;` and `&#xD800;` before the Q2 DIL literal.
- G1-M1: the Q3 prior-year note wrapped in `<template>` or a comment, which leaves PCORE unlocated.

Not re-varied here, and left to their owning groups' families 4 and 10:
- R5 B3, R6 G2-B1 and G4-B1: seam relocations (G2 family 4);
- R2 B5, B11, R3 N3 and N5: validator, S0 and determinism (G2 and G4).

## Families 2, 6 and 8: sweeps over Q1–Q3 (probes run / bad)
The sweeps use the round-6 `g3lib.py` and round-7 `g3lib7.py` harnesses unchanged, run from `g3/tree` under 3.14 (`venv_t1`), plus the R8 `g3lib8.py`. "bad" means a present fact where the reader's reading requires unlocated, or a present value different from the original.

| family | run | bad | notes |
|---|---|---|---|
| 2: duration relabels (Three→Six/Nine/Twelve/Three and Six, Three Months→Fiscal Year/Year, quarter-name→First Half/Nine Months/Fiscal Year/Fourth Quarter, ranges), Q1–Q3 | 102 docs | 0 | 0 exceptions; no pinned-role fact present |
| 6: unit rule (R145/R152/R159/R164/R169), every pinned cell × both statements, own/neighbour/carried-above/spans-down, literal and entity-coded, agreeing/conflicting, Q1–Q3 | 3232 | 0 real | block 1715/0, conflict 228/0, invis 857/0; control 432/6 = G3-O3 (carried `%` allow controls on COREG unlocated, fail-closed, unchanged from rounds 6–7) |
| 8: round-6 years (banners, header dup/rm/swap, span2, title, title2 = non-governing title and `_period_titles` fallback), Q1–Q3 | 3314 | 0 real | banner 2958/0 (cover 622); hl_dup 12 and title 12 are the round-6 harness artefacts (correct values present, as recorded in rounds 6 and 7) |
| 8b: round-7 new banners / sole-year / sole-year in a data cell, Q1 (3.14 and 3.12) | 1262 each | 0 | banner 1088 (cover 154), sole 126 (cover 23), soledata 48 (cover 8). The round-7 harness's `sole` list treats `2026x` as a year, so it cannot see G3-R8-B1 |
| geo (R168): value spanning 1/2/3/6/7 columns, widened+rowspan, rowspan-carried year starting in another row, label from above / into next | 91 | 0 | Q1/Q2 earnings stop at `StopIteration` in the round-7 harness (the calendar-2025 headers carry no `2026` cell), as in round 7; highlights run on all three quarters and Q3 runs in full |
| sole8 (R8): the title year removed, one banner row as the only year, 60 forms, Q1–Q3 × 3.14/3.12 | 1593 per interpreter | 84 per interpreter | all G3-R8-B1 (14 letter-glued forms × CORE/PCORE × 3 quarters); the figure forms are 0 bad; the year forms (`FY2026`, `Fiscal 2026`, `Sept. 2026`, `March 2026`, `CY2026`) are cover (unlocated) because a word banner changes the signature (coverage, G3-O1's class) |
| contra (R8): the title keeps its year; a banner names the same, another, or two years (`2026 2025`, `2025/2024`, `2024 and 2025`, `FY2025`, `Fiscal 2027`, `2026E 2025`), every year-titled table, Q1–Q3 (3.14) and Q3 (3.12) | 331 | 0 | 0 exceptions |

Family 8's "two-year header values in each order and spelling" and "a title year that contradicts the header" are the `contra` sweep plus round-6 `banner`. "A year only in the governing title" is `sole8`/`8b` with NONE and the plain-year controls. "A non-governing title and the whole-table fallback" is round-6 `title`/`title2`. "Rowspan-carried year rows, values spanning year columns, labels spanning rows" is `geo` plus my `test_f1_r6_g3b1…`.

### Coverage (non-blocking)
- **G3-R8-c1** (R179 coverage cost). A word-bearing year banner (`FY2026`, `Fiscal 2026`, `Sept. 2026`, `March 2026`, `CY2026`) above the core reconciliation leaves CORE/PCORE unlocated even though R179 names the year. The cause is the signature, not R179. A legitimate EX-99 would print such a banner rarely in the reconciliation (P&G never does). Estimated under 5% of consumer-staples EX-99.1 quarterly tables.
- `Q3 2026`, `3Q 2026`, `Sept. 30, 2026` and `June 30 2026` in a header value are unreadable under R179 (the other digits stay in the rest), so a pin under them is unlocated. These are plausible header spellings in other issuers' exhibits (perhaps 10–20% print `Q3 2026` or a date-with-year column header), but they sit outside F1-Q's P&G layout. The result is fail-closed.
| 6b: round-7 R169 pointer forms (own/shield/carried/spans-down, forbidden `%`/`$` with 10 invisible characters, full-width, small-form, look-alikes), every pinned cell, Q1 complete, Q2/Q3 partial (see GAPS) | 8462 (Q1 2967, Q2 ~2750, Q3 ~2745) | 0 wrong binds | forb 5217/0 present; allow 339 and look 210 "changed" rows are all **absent** (fail-closed: an allowed unit carrying U+2064/ZWSP/full-width `$`, or a look-alike `€ £ ٪ ‰ %(1) %*`, unlocates the pin). There are 0 exceptions and 0 present-with-a-changed-value rows |

## Probe file `test_envelope_audit_probes_r8_g3.py`: 315 cases
- 3.14 (`venv_t1`): `54 failed, 251 passed, 10 skipped` (after the harness corrections below). 3.12 (`venv312_min`): the same, and the failure sets are identical.
  - The 54 are exactly `test_BLOCK_g3_r8_b1_*` (G3-R8-B1).
  - The 10 skips are Q1/Q2 earnings, which print no `2026` header cell.
- The first full run gave `173 failed, 142 passed` on both interpreters (107 s on 3.12, 93 s on 3.14). The excess 119 were my harness errors, now corrected:
  - PCORE's first pin sits in highlights, with no year title (`title_over` now tries both statements);
  - `loc[0]` is a table ordinal, not a role;
  - highlights prints two `2026` cells;
  - the note regex.
- After correction, a second full run gave `69 failed, 236 passed, 10 skipped` (145 s on 3.14, 149 s on 3.12): 54 G3-R8-B1 plus 15 highlights-variant harness errors. The rerun of that test alone gave `20 passed, 10 skipped` on both interpreters.

## Commands
- Round-7 file: `cd g3/tree; PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests:$MY/audit_t1_envelope_r6/g3:$MY/audit_t1_envelope_r7/g3 <py> -m pytest -p no:cacheprovider -q -rf $MY/audit_t1_envelope_r7/g3/test_envelope_audit_probes_r7_g3.py`. Logs: `logs/r7g3_312.log`, `logs/r7g3_314.log`.
- Round-6 file: the same, with `test_envelope_audit_probes_r6_g3.py`. `148 passed, 9 skipped` on 3.12 (67.17 s) and 3.14 (66.53 s), unchanged.
- R8 file: the same PYTHONPATH, with `g3/test_envelope_audit_probes_r8_g3.py`. Logs: `logs/r8g3_31{2,4}.log` (first run) and `logs/r8g3b_venv*.log`.
- Sweeps: `PYTHONPATH=. <py> $MY/audit_t1_envelope_r6/g3/g3lib.py {2,6,8} Q{1,2,3}`, `… r7/g3/g3lib7.py {6b,8b,geo} Q*` and `g3/g3lib8.py {sole8,contra} Q*`. The outputs are in `logs/*.jsonl`, summarised by `g3/summ8.py`.
- Reproduce G3-R8-B1: `… -m pytest -p no:cacheprovider -q g3/test_envelope_audit_probes_r8_g3.py -k BLOCK_g3_r8_b1` gives `54 failed` on both interpreters. Observed `AssertionError: (1.59, True)` (present, validates) against the expected not present.

## GAPS
- Round-7 `8b` on Q2/Q3 (3.14 and 3.12) and the round-7 `lone` sweep did not run. They were stopped for the host budget after about 90 minutes of sweeps at two to three processes. The R179 year surface they cover is covered on Q1–Q3 on both interpreters by `sole8` (1593 judgements per interpreter) and `contra`, and by the probe file's 150+24+30 year cases. `8b` Q1 ran on both interpreters with 0 bad.
- `6b` Q2/Q3 were stopped at about 92% (8462 of about 8931 rows); 0 wrong binds in what ran.
- The sweeps ran on 3.14 only, except `sole8`, `contra` Q3 and `8b` Q1, which also ran on 3.12. R179's grammar is ASCII-only regex and R178's figure test is unchanged, and the probe file ran on both.
- Family 1 does not re-vary the seam relocation findings (R5 B3, R6 G2-B1 and G4-B1), R2 B5/B11, or R3 N3/N5. Those are G2's families 4, 5 and 10 and G4's re-runs.
- The worktree check after the last run is recorded below.

## DEVIATIONS
- The round-7 harness's Q1/Q2 year was replaced by each quarter's own title year in my probe file (commission: "Re-probe each by its original construction").
- Sweep parallelism was lowered to two or three processes to stay within four.
- After the last run, `$WT` HEAD was `e6f49ceccb85ca1feedab0876f947a042224992f` and `git status --porcelain` was empty (0 lines).

## Corrections to the text above
- The figure `54 failed, 251 passed, 10 skipped` is derived, not a single run. It combines the second full run (`69 failed, 236 passed, 10 skipped`) with the separate rerun of the corrected highlights variant (15 failures became passes). No third full run was made after that last harness edit.
- `6b` stopped at 8594 rows (Q1 2967, Q2 2874, Q3 2753). 0 wrong binds and 0 exceptions were counted over the first 8462 rows.
- The `6b` table row sits after the Coverage subsection; it belongs to the Families 2/6/8 table.

---

## Group G4: families 0, 12, 13 and 14 (verbatim)

# OPUS T1 envelope audit, round 8, group G4 (integrity and the artifact): families 0 (G4), 12, 13, 14

Head audited: e6f49ceccb85ca1feedab0876f947a042224992f (PR #7905). READ_ONLY on $WT; writes only under $MY/audit_t1_envelope_r8/g4/.
Probe file: $MY/audit_t1_envelope_r8/g4/test_envelope_audit_probes_r8_g4.py

## STATUS: REJECT — one blocker (G4-R8-B1, bar c/d: str() of tampered workspace fields raises out of the validator; inherited, and left open by R183). Everything else in G4's families reproduces or holds.

## Integrity (family 0 / NOT DONE UNLESS) — all hold
- Before first run: `git rev-parse HEAD` = e6f49ceccb85…; `git status --porcelain` empty.
- `git diff --stat $FREEZE $HEAD -- tests/ research/ .github/`: empty.
- `git diff --stat $R6HEAD $FREEZE`: exactly .github/ci/legacy-jobs.yml (5 +-), OPUS_..._AUDIT_R7 (+673), SEAT_RULING_..._R5 (5 +-), SEAT_RULING_..._R7 (+302), tests/..._r5.py (6 +-), tests/..._r7.py (+629).
- `git diff $R6HEAD $FREEZE -- tests/test_pg_envelope_f1_probes_r5.py`: removes `code_point_unescape_drops` from INSIDE_LIMIT (replaced by a comment) and the docstring clause "or after a reference html.unescape drops" only. AST-checked by probe i5.
- R5 ruling record's change: two "withdrawn by R185" marks + one "Amended by R185" bullet (the mark at source). No other earlier record changed R6HEAD..HEAD (probe i6).
- `git log $R6HEAD..$HEAD --name-only`: freeze ad7dca26f01, then aa33b6206ad (R179: pg_envelope.py), 34c9a153fdd (R180: pg_envelope.py), 79bf5045159 (R181: pg_envelope.py + disclosure_diff.py), d4c8945e897 (R183: economic_observations.py), d734467f80d (R184: economic_observations.py), e6f49ceccb8 (R185: economic_observations.py). All authored "Sol CEO" (fleet identity). Probe i4.
- test_pg_envelope_f1.py, _r1–_r4, _r6 and tests/fixtures/pg_envelope/ byte-identical R6HEAD..HEAD (probe i6).
- CI wiring: r7 suite added to the job's paths and run line; timeout 12 -> 15. Nothing else in legacy-jobs.yml.

## Runs at HEAD
- Eight frozen envelope suites, 3.12 venv312_min: `971 passed, 70 warnings in 426.53s`.
- Eight frozen envelope suites, 3.14 venv_t1: `971 passed, 70 warnings in 412.89s`. Seat testimony (971 on both) REPRODUCED.
- a5a + four capital-structure suites (/opt/homebrew/bin/python3.12, in $WT): `213 passed, 70 warnings in 40.23s` (cs_head.raw). Per-test comparison with f8e4af5aa4c: PENDING below.
- Six release-parser files in $WT (python3.12): `2 failed, 287 passed in 143.28s` (rp_head_wt.raw). The 2 are `test_capital_structure_document_terms.py::test_clean_preimport_forged_*[cpython-3.12.2-python-org]` (interpreter-provenance tests). Per-test R6HEAD comparison: PENDING below.
- Gate line, curated_exclusive: PENDING below.

## FINDING G4-R8-B1 (BLOCKER, bar c/d; contradicts R183 "Refused, never raised", R134, R176) — inherited from R6HEAD, left open by R183
The validator prints workspace fields with `str()` in three places R183 did not guard, and `str()` raises for two kinds of JSON-representable values:
a nested list deeper than the interpreter's repr limit (RecursionError) and an int past 4,300 digits (ValueError, `sys.int_info.default_max_str_digits`).
R183 guards `_fact_id`'s str() for RecursionError only, not ValueError.
- `economic_observations.py:101` `_fact_id`: `"|".join(str(item) ...)` — a present row's `period = 10**5000` raises **ValueError** (R183's handler at :168-171 catches RecursionError only). Probe `test_b1_…[Q1|Q2|Q3]`.
- `economic_observations.py:542` and `:544`: `str(fiscal_period.get("quarter"))` / `str(fiscal_period.get("year"))` run before any R183 handler — `ws["fiscal_period"]["quarter"|"year"]` = list nested 100,000 deep raises **RecursionError**; = `10**5000` raises **ValueError**. Probe `test_b2_…[quarter|year-nested|big]` (4).
- `economic_observations.py:194`: `str(absence_payload.get("subject") or "")` — an absent row's `typed_absence.subject` nested 100,000 deep raises **RecursionError** (the TypedAbsence constructor at :182 accepts it). Probe `test_b4_…[Q1|Q3-nested]` (2); the `big` variant is refused.
- Observed at HEAD, 3.12 venv312_min and 3.14 venv_t1 alike: b1 3/3, b2 4/4, b4 2/4 raise (ValueError "Exceeds the limit (4300 digits) for integer string conversion"; RecursionError "maximum recursion depth exceeded while getting the repr of an object" on 3.12, "Stack overflow (used 16352 kB) …" on 3.14). Expected: `EconomicObservationError`.
- Controls pass: a scalar wrong quarter (9) is refused; `10**5000` as `event_id` and as a present row's `unit` is refused.
- Inherited: the same 9 cases (b1 ×3, b2 ×4, b4 ×2) fail identically in $G/trees/base (the $FREEZE = $R6HEAD engine). At base, `event_id = 10**5000` also raised (b3 control) — R183's event-identity check closes that one.
- Reproduce: `cd $G/trees/HEADcopy && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. $MY/venv312_min/bin/python -m pytest -p no:cacheprovider -q $G/test_envelope_audit_probes_r8_g4.py -k "b1 or b2 or b4"` -> 9 failed, 7 passed (same on venv_t1). At base: same 9 failed.
- Why blocking: bar (c) lists "a raised exception instead of a refusal (R176, R183, bar d)"; bar (d) "an exception escapes … the validator (R134, R176, R181, R183)". R183 was ruled as the closing of exactly this class (G2-m2 deep nesting, G2-B3 huge numbers); its sweep covered the value (float overflow) and _fact_id (recursion), not str() of an oversized int nor the two pre-handler str() sites. Minimal repair direction: refuse non-scalar/oversized `fiscal_period.quarter|year` and `typed_absence.subject` before printing them, and widen `_fact_id`'s handler to ValueError (or type-check `period` as a str before printing).

## Family 13 — code review (partial; in progress)
- New try nodes FREEZE..HEAD: four, all in economic_observations.py — `_finite` (OverflowError -> False, caller raises "numeric observation must be finite and non-boolean"), `_fact_id` nesting (RecursionError -> refusal), scope-key `hash` (TypeError/RecursionError -> refusal), and the JSON comparison's handler widened by RecursionError (a changed, not new, try). None of the try bodies names the source (`source`, `source_bytes`, `raw`, `body`, `fragment`, `region`); every handler ends in `raise EconomicObservationError` or `return False` to a refusing caller. Probe c1. The seat's "three new try nodes" is accurate if the widened JSON handler is counted as changed, not new.
- New refusal messages: exactly R183's four (probe c2). No new import; no new absence reason/admission kind string (probe c3).
- R181 grid clamp `pg_envelope.py:387-388`: `min(int(digits) if len(digits)<=6 else LIMIT, LIMIT)` is exactly R181's rule; `_SPAN_PATTERNS` (`:25`) uses `\d+` (Unicode digits) — a non-ASCII-digit span of >6 chars is read as the limit, ≤6 converts via int() (accepts Unicode digits); R163's `_spans_read_alike` (`:252-268`) refuses any value not `[1-9][0-9]{0,4}`, so no admitted document reaches either reading. Release parser `disclosure_diff.py:81-85`: `10**6` for >6 significant digits; R66 reads >64 as absurd, so no reading changes. Minimal.
- `_parse_year` (`pg_envelope.py:951`) still uses `\d` (Unicode) for the pin's header year; `_header_years` (R179 grammar, ASCII `_YEAR` + `_figure_character` rest check) returns None for any non-ASCII digit, so `_reads_under`'s `_header_years(rows, view) != {pin_year}` fails closed. Not a finding; noted for minimality.

## Batch update 2
- curated_exclusive (/opt/homebrew/bin/python3.12, $WT): `2 passed, 119 deselected, 70 warnings in 431.76s`.
- a5a + capital-structure per-test vs f8e4af5aa4c: 213 outcome lines at HEAD; `diff` against round-7 G4's f8e4af5aa4c run (`audit_t1_envelope_r7/g4/cs_f8e.txt`) = 0 lines, and against the seat's `baseline_a5a_cs_f8e4af5.txt` = 0 lines (cs_vs_r7f8e.diff, cs_vs_seatbaseline.diff). Not re-run at f8e4af5aa4c this round: that revision is unchanged and two independent recorded runs agree (DEVIATION noted).
- G4 probe file at HEAD (HEADcopy): 3.12 venv312_min `9 failed, 17 passed in 26.75s`; 3.14 venv_t1 `9 failed, 17 passed in 20.54s`. The 9 are G4-R8-B1's (b1 ×3, b2 ×4, b4 ×2). i1–i6 read $WT's git state and pass at HEAD.

## Family 14(vi) — G4-O1 re-examined: OBSERVATION stands, no frozen case moves
- Probe `test_o1_…[Basic|""]` (passes = divergence recorded): on R6's `spanning_the_blank_row(label)` document (the Q3 1.63 cell with rowspan=2 over a row labelled "Basic" or blank), the engine leaves DIL unlocated (R168, frozen R6 case) while `t.witness_outcome(body, FY26Q3)[DIL]` still reports a value, because `label_of` (tests/test_pg_envelope_f1.py:182) and `locate` (:221) read only the cell's starting row. Control (`"Diluted"`): both report 1.63 and every frozen value binds.
- `witness_outcome` is called only in test_pg_envelope_f1.py (3), _r1 (2), _r3 (2); none of those builds a label-rowspan document, and _r4–_r7 never call it. So no frozen case moves; the oracle simply does not encode R168's label half. The same holds for the note: `witness_outcome` (:298-301) reads the note by plain-text containment, not by R180's region rules — no frozen case feeds it an R180 document either. Non-blocking.

## Batch update 3
- Gate job line (earnings-economic-dossier run line from .github/ci/legacy-jobs.yml:13621, + `-p no:cacheprovider`), venv312_min (pytest+pyyaml only), in $WT: `1795 passed, 174 skipped, 21 warnings in 649.76s (0:10:49)`, WALL 656s. Seat testimony: 1,795 passed, 174 skipped in 414 s. Host load average ~31 on 24 cores during the run (other groups), so wall time is not comparable to the seat's; the hosted runner's time is family 12.
- Family 0, G4-B1 by construction and variants (probe `test_g0_b1_*`): every code point `str.isspace()` calls space that is not layout (23: \x0b, \x1c–\x1f, \x85, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, U+3000) × six placements (glued after a minus; across markup; in R155's gap; as a numeric reference across markup; glued after the literal; across markup after the literal), relocated through R143's seam on Q3 DIL: all 138 refused; controls (space across markup before and after, `&#32;`) accepted. 3.12: `141 passed in 132.73s`; 3.14: `141 passed in 201.61s`. G4-B1 and G4-m1 CLOSED.

## Batch update 4 — family 14(i) trees
- Trees under $G/trees/: HEADcopy (config/engine/tests of $WT), base ($FREEZE engine = $R6HEAD engine), m_R179…m_R185 (one ruling reverted), h_* (20 hunks: R179 grammar/title; R180 raw/ref/odd; R181 grid/rp; R183 identity/nesting/finite/json/scope/sources; R184 edge/gap; R185 cut/edge/written/raw/gap). Built by $G/mktrees.py; self-check: with every hunk reverted, the residue against $FREEZE's three engine files is only the dead added definitions (_YEAR_BEFORE/_YEAR_AFTER/_UNPRINTED_RAW_TEXT/_named_years, _finite/_LAYOUT_SPACE/_drops_a_reference), the R181 docstring and one line wrap — so the hunk table decomposes the diff completely.
- R7 suite, HEADcopy: 3.12 `272 passed, 74 warnings in 294.83s (0:04:54)`; 3.14 `272 passed, 74 warnings in 292.19s (0:04:52)`.
- R7 suite, base (-k "not ten_digits"): 3.12 `196 failed, 74 passed, 2 deselected, 27 warnings in 271.79s (0:04:31)`; 3.14 `193 failed, 77 passed, 2 deselected, 26 warnings in 271.58s (0:04:31)`. Seat testimony (196/74 on 3.12, 193/77 on 3.14) — see line above.

## Family 12 — hosted CI, read 1 of 2 (12:25:00Z, 27 min after the 11:57:51Z push)
- check-runs for e6f49ceccb85…: `total_count` 3 — ci-authority/main success, ci-authority success, `ci-authority/codex/merge-queue-pilot` failure (known non-binding). **No `ci-pack-*`, no `ci-plan`, no `ci-gate` check-run exists.** (gh_checkruns_1.txt)
- `gh run list --branch claude/cdv1-t1-pg-profile-facts`: at e6f49ceccb85 only `ci-authority` 36418816158 (success). No `ci` and no `fences` run was scheduled for this head; the prior head b6808dfcc166 has ci 36200249010, fences 36200248810, ci-authority 36200248202, all success. (gh_runs_1.json)
- Local plan (read-only, `scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-count 12 --validate-only --changed-from 8a8ecbe868ff --emit-plan-json`): 231 jobs in scope, full suite (legacy-jobs.yml is a global invalidator); `earnings-economic-dossier` falls in **pack 10** (22 jobs). The hosted plan may differ.
- Consequence: the gate's R7 wiring and the 12→15 min timeout are unexercised on the hosted runner at this head. The 15-min claim rests on the seat's extrapolation (416 s hosted at b6808dfcc16 × 1.5 ≈ 620 s). My local gate run took 650 s wall on a host at load ~31/24 cores, so it is no evidence either way. This is a GAP, not a finding under the bar; the merge path needs a `ci.yml` run (e.g. a `workflow_dispatch`, or a push event that schedules one) at this head before any merge.
- Base reproduces the seat's freeze testimony exactly on both interpreters (196 failed / 74 passed on 3.12; 193 / 77 on 3.14; two ten-digit cases deselected).
- Ruling trees (full R7 suite): m_R179 48 on both; m_R180 21 on both; m_R181 2 on both (ten-digit deselected); m_R183 27 on 3.12, 24 on 3.14. Every failure is inside base's set; no control/precondition fails.
- **R179's 76 vs 48 (observation O-R8-1, family 14(i)/(iv), non-blocking).** My R179 tree reverts the behaviour and keeps the added helper `_named_years` as dead code, so the 28 "grammar" cases (`test_r179_a_year_a_reader_reads_as_a_year_is_named` 15, `…_printed_as_a_figure_is_not_named` 11, `…_beside_a_marker_outside_the_grammar_is_not_named` 2) pass there. They call `pe._named_years` directly and fail at base only by AttributeError, as the ruling says ("they fail there by construction"). So 48 cases witness the engine's use of the grammar, and 28 pin the helper's table and would stay green if `_header_years` stopped calling it. The seat's 76 is reproduced as 48 behavioural + 28 by construction. The engine's use of each individual grammar row is witnessed only through the eight banner figure forms and the plain-year control.

## Family 14(i) — witness and hunk tables: REPRODUCED independently (minus_summary.py over $G/minus/*.log)
| reverted | 3.12 | 3.14 | seat |
|---|---|---|---|
| R179 (behaviour; helper kept) | 48 | 48 | 76 = 48 + 28 by construction (see O-R8-1) |
| R180 | 21 | 21 | 21 |
| R181 both hunks (ten-digit deselected) | 2 | 2 | 2 |
| R183 | 27 | 24 | 27 / 24 |
| R184 | 27 | 27 | 27 |
| R185 | 43 | 43 | 43 |
- Disjoint on both interpreters; union (168 on 3.12, 165 on 3.14) + the 28 helper-by-construction cases = base's 196 / 193 exactly; no minus-tree failure outside base; no control or precondition fails in any tree; HEADcopy 272/272 on both.
- Hunks (each ⊆ its ruling's set): R179 grammar 48, title 0 (defence in depth, unwitnessed); R180 raw 9, ref 6, odd 6; R181 grid 2 (own cases only, ten-digit deselected), release parser 1; R183 identity 9, nesting 1, finite 9, JSON 3 on 3.12 / 0 on 3.14, scope 2, sources 3; R184 edge 12, gap 6, and 9 fail only with both reverted; R185 cut 6, edge 6, gap 6, raw 6, written 7, and 12 fail only with all five reverted. All equal the seat's tables and its "both checks refuse each" accounting.
- Family 14(iii): with R185 reverted the amended R5 suite passes 60/60 on both; R6HEAD's R5 file run at HEAD fails exactly `test_r166_a_relocation_inside_the_restated_limit_is_accepted[code_point_unescape_drops]` (1 failed, 60 passed, both). And the eight suites pass 971/971 at HEAD. So the dropped case is the only change R185 needs to an earlier frozen file.
- Family 14(v): no R7 case contradicts an earlier frozen case: the eight suites pass jointly at HEAD on both interpreters, and the round-0 witness (`witness_outcome` on the originals, F1 suite) passes. The one frozen outcome R185 moves is removed, not inverted in place.
- Family 14(ii): R183's finding class (G2-m2 deep nesting, G2-B3 oversized numbers) stays open at three sites R183 did not reach — G4-R8-B1.
- Family 14(iv): R182's 18 relocations pass at base and HEAD (they pin R176/R182, which changes no code). R184's six letter-glued cases pass at base (refused through the letter by R155's gap check) and pin that outcome, not R184. Neither set claims to witness a hunk, and none does. R179's 28 grammar cases pin the helper only (O-R8-1).

## Earlier probe files at HEAD (run in $G/trees/HEADcopy; failed sets compared by case name)
| file | 3.12 venv312_min | 3.14 venv_t1 | vs round 7 / seat |
|---|---|---|---|
| r1 | 4 failed, 99 passed | same | failed set identical by name to round 7's (round-6 accounted) |
| r2 | 1 failed, 67 passed | same | identical (`test_d_s0_validator_missing_fields_tamper_outcome_unchanged`) |
| r5 | 4 failed, 11 passed | same | identical (3 B3 + 1 OBSERVE, round-6 G4-m1) |
| r6 g2 | 11 failed, 7 passed | same | = seat (R176's eleven accepted relocations) |
| r6 g3 | 148 passed, 9 skipped | same | = seat |
| r6 g4 | 5 failed, 14 passed | same | = seat: i1–i5 pin 135a67a3e12's head/diff |
| r7 g2 | 18 failed, 23 passed | same | = seat (G2-B1 relocations, inside R176/R182) |
| r7 g3 | 21 failed, 400 passed, 2 skipped | same | = seat: 18 Q1/Q2 params hit the harness's Q3-only precondition `AssertionError: ('core_reconciliation', 2026)`; 3 `test_f0_b3_controls_prior_year_pins_bind` are O1's fail-closed Fiscal Year controls (`None == 1.54/1.61/1.88`) |
| r7 g4 | 6 failed, 30 passed | same | i1, i2, i3, i5, i6, i7 pin b6808dfcc16's head/diff (expected to fail at a new head); i4 and the other 29 pass |
Failed sets are identical between 3.12 and 3.14 for every file above. r3, r4 and r7 g1: see below. r6 g1 (5,883 cases, ~45 min, G1's reader file): not run (GAP).
- Name checks: r3 (4 failed / 220 passed / 1 skipped) and r4 (13 / 1092 / 27): failed sets identical by name to round 7's logs (old_test_envelope_audit_probes_r3.log, old_r4.log). r7 g1 (/opt/homebrew/bin/python3, html5lib 1.1): 5 failed, 909 passed. The five are the seat's accounting exactly: `test_f0_B2_odd_character_beside_a_pinned_literal_is_refused[&#11-before-{Q1 sales growth, Q2 core_eps, Q3 prior_diluted_eps}]` (fail at R6HEAD too) and `test_r7_control_unprinted_raw_text_inside_the_note_is_blanked[<iframe>…|<title>…]` (R180's recorded cost).

## Release-parser suites, per test, R6HEAD vs HEAD (python3.12; trees rp_r6 / rp_head = engine scripts collectors lib contracts config app tests .github config.yml, with rp_r6's three engine files from R6HEAD)
- rp_head `13 failed, 276 passed`; rp_r6 `13 failed, 276 passed`; per-test diff over 289 outcomes = **0 lines**. The 13 failures in both scratch trees are interpreter-provenance and repo-state tests (`test_clean_preimport_forged_*`, `test_clean_unknown_interpreter_*`, `test_cold_tracked_source_export_import_is_repeatable_without_bytecode`). In $WT at HEAD the same six files give `2 failed, 287 passed`; the 2 are `test_clean_preimport_forged_*[cpython-3.12.2-python-org]`. The seat's "16 failed in scratch" differs from my 13 because the scratch contents differ; the R6HEAD↔HEAD equality is what the bar asks, and it holds.

## Family 13 — mutation re-run at HEAD (in-memory, g4r8_mut.py = round 7's harness; targets R4–R7 suites, 635 cases; venv312_min)
| mutation (rule removed) | failed of 635 |
|---|---|
| none (control) | 0 |
| r165 (header years = _parse_year of each header) | 80 |
| r174_off (_whole_printed_token → True) | 36 |
| s_r155 (seat's R155 mutation) | 14 |
| r178_fig (_figure_character = isnumeric) | 9 |
| sub_char_ref_empty (R172 dropped-reference admission) | 6 |
| r173_off (no raw-text blanking in the note) | 5 |
- All seven are still killed. So R179 has not made R165/R170/R178's figure rule unreachable, R184/R185 have not made R174 or R155 unreachable, and R180 has not made R173 unreachable. The other 55 of round 7's 62 mutations were not re-run at HEAD (GAP: host load ~70, turn budget). Round 7's survivors (s_raw, s_ws, sub_char_odd, sub_span_engine_agree, sub_span_engine_only, sub_span_other_attr) were already unwitnessed at R6HEAD, and the R7 suite does not target them.
- R179's title-digit hunk is unwitnessed defence in depth: reverted alone, it fails 0 of 272 (as the seat says).

## Family 12 — read 2 of 2 (13:39:56Z, 1 h 42 min after push)
- Unchanged: `total_count` 3 (ci-authority/main success, ci-authority success, ci-authority/codex/merge-queue-pilot failure, non-binding). Runs at e6f49ceccb85: only ci-authority 36418816158 (`pull_request_target`, success). No `ci` (`pull_request`) or `fences` run exists for this head; b6808dfcc166 had both. **No ci-pack-*, ci-plan or ci-gate result exists at $HEAD** → GAP. The local plan puts earnings-economic-dossier in pack 10.

## Final integrity
- After the last run: `git rev-parse HEAD` = e6f49ceccb85ca1feedab0876f947a042224992f; `git status --porcelain` empty.

## GAPS
- Hosted CI: no ci.yml run was scheduled for $HEAD, so no ci-pack/ci-gate conclusion exists, and the 15-min timeout is unverified on the runner. Read twice (the commission's maximum); never dispatched.
- Family 13 mutation sweep: 7 of round 7's 62 mutations re-run at HEAD, on 3.12 only (mutations are code-path, not Unicode-dependent). Not a full "remove every rule R143–R178" sweep.
- r6 g1 probe file (5,883 cases, ~45 min, html5lib reader): not run.
- a5a/cs at f8e4af5aa4c not re-run this round; compared against two recorded f8e runs (round-7 G4's and the seat's baseline), both 0-diff.
- Gate wall time (650 s) was measured on a host at load 31–72 on 24 cores; not comparable with the seat's 414 s or the runner's.

## DEVIATIONS
- Minus-one trees ran the full R7 suite in hunk trees, not only their own ruling's cases (a superset; the counts are unaffected).
- Trees revert behaviour hunks and keep newly added helpers as dead code. So m_R179 shows 48, not the seat's 76; the 28-case difference is the helper-only grammar cases (O-R8-1).
- Release-parser scratch trees include app/ scripts/ collectors/ lib/ contracts/ .github/ beyond config/engine/tests, so that the six files import.
