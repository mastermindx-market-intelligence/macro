**Verdict: blockers — no PASS.** The diff is directionally right (fail-closed, gate strictly tightened) but admits two numeric-hiding bypasses and one wrong-year bypass, and it re-opens the same false-rejection class it was written to close.

**Method And Scope**
- Parent commit `e7112006` is not checked out anywhere locally (no tree contains `_quantity_anchors`/`_fact_quantity_pool`/`_NAMED_DATE_RE`), so I read the nearest ancestor `lanes/repos/macro/engine/press/validators.py:280` (`extract_numbers` masks ISO internally), `:456` (`check_fact_anchor`, `generic_integer_max=12`, the 1900–2100 year exemption), `:422` (`_row` → `metrics`), `:767`/`:782` (`_anchored_values`, `check_our_value`).
- All findings below were executed in self-contained Python replicating the diff's regex/masker plus those ancestor semantics. No repo edits, no git, no network. The diff's own 21 controls reproduce as written; this is not a test-visibility problem.

**Confirmed Sound**
- Full-month-only, `IGNORECASE`, ordinal-tolerant; `set[date]` dedups duplicate vintages (two facts both `2026-10-13` still resolve); `date.fromisoformat` rejects `2026-02-30`/`31 April`; run date and `raw_documents` do not authorize; ISO dates inside `facts.text` do.
- Non-resolution returns the original span, so digits stay in the quantity pool; `ok` is strictly conjunctive and quotes still match against unmasked prose — no overlap/receipt/freshness/editorial gate is softened.
- No catastrophic backtracking: 4,400-char adversarial input masks in 0.4 ms.

**Blocker 1 — Denylist lookahead lets a month name swallow a real quantity**
The guard `(?![\w%]|\.\d|\s*(?:percent|million|billion|trillion|thousand|bps|bn)\b)` omits `,\d`, `-\d`, `/\d`, `:` and every unit word outside that list. Slot for all repros: one fact, `dated="2026-10-13"`, `values=["50"]`, `text="The measured composite is 50."`
- `"Wheat exports reached October 13,000 tonnes, and the composite was 50."` → masked to `␀ ,000 tonnes` → `,000` parses as value `0.0`, a bare int ≤ 12, so it is exempt → `fact_anchor ok=True` with 13,000 never checked.
- `"Stocks of March 5,000,000 bushels were reported; the composite was 50."` (`dated="2026-03-05"`) → `,000,000` → 0.0 → exempt; 5,000,000 hidden.
- `"The spread widened October 13 basis points to 4.2%."` (fact value 4.2) → `basis points` is not in the denylist → `October 13` masked → unsupported 13 disappears.
- `"The October 13-week moving average was 50."` → 13 (> `generic_integer_max`) hidden.
- Fix: make the right boundary an allowlist (clause punctuation, end, or a bound 4-digit year), and refuse when the day is followed by `[,.\-/:]` or any word; or reject a match whose pre-image window overlaps a `_NUM_RE` span.

**Blocker 2 — Masking runs on flattened prose, so blocks synthesize a date**
`strip_tags` replaces tags with a space (`lanes/repos/macro/engine/press/validators.py:146`), and `_mask_anchored_named_dates` sees the joined result.
- Body `<p>Export sales for the week ended October</p><p>13,000 tonnes were shipped; the composite was 50.</p>` → `"…ended October  13,000 tonnes…"` → masked → `ok=True`, 13,000 hidden. Each block is grammatical alone.
- Fix: mask per block/sentence using the existing `blocks()`/`sentences()` helpers, never across the join.

**Blocker 3 — A stated year is silently downgraded to month/day**
`(?:(?:,\s*|\s+)(?P<year>\d{4}))?` is optional, so a year that is not positionally adjacent is dropped instead of failing. Slot: one fact, `dated="2025-10-13"`, `text="The 2026 wheat composite is 50."`, `values=["50"]`.
- `"As of October 13 of 2026 the composite was 50."` → resolves to `2025-10-13` with `year=None` → `ok=True`. Also `in 2026`, `during 2026`, `13 October of 2026`.
- Same slot with the correct form `"As of October 13, 2026 …"` → `unanchored_dates=['October 13, 2026']` → correctly fails. So the check is weaker for the *less* precise spelling.
- Conditionality: the stray `2026` escapes only via the ancestor year exemption (`str(int(v)) in source_text`) or the pool; with text lacking "2026" it fails (`unanchored=['2026']`). Still a wrong-year admission whenever the year digits are otherwise exempt.
- Fix: if a 4-digit year token occurs in the same clause after the day, bind it mandatorily and require equality with the resolved year; otherwise record `unanchored_dates`.

**Blocker 4 — Year binding is brittle, re-creating the original false rejection**
`,\s*` disallows whitespace *before* the comma, and only `,`/space bind a year.
- `"… on October 13 , 2026."` → year dropped → `unanchored=['2026']` → FAIL.
- `"… on October 13 (2026)."` → FAIL.
- `"… on October 13–14, 2026."` and `"… October 13 - 14, 2026."` → year dropped, both endpoints and year unanchored → FAIL. Ranges are ordinary in USDA/ag copy.
- Fix: `(?:\s*,\s*|\s+|\s*\()` for the year; handle ranges as one span (resolve both endpoints or refuse without leaving stray digits).

**Blocker 5 — Non-date "month + integer" prose now hard-fails**
Any month name followed by 1–2 digits is date-tested, and an unresolved date is fatal.
- `"The September 3-month Treasury bill yield was 4.2%."` → `unanchored_dates=['September 3']` → FAIL, although 4.2% anchors and `3` was previously exempt under `generic_integer_max=12`.
- `"The October 12-month moving average was 4.2%."` → FAIL. `"The 10 March contract settled at 4.2%."` → FAIL (day-first form).
- `re.IGNORECASE` also makes the modal `may` a month token, so `may <digits>` is date-tested.
- Fix: same boundary allowlist as Blocker 1; additionally skip when the digits are immediately followed by `-`+word.

**Limitations (stated, not invented as support)**
- Only exact full-month names resolve. Verified non-coverage: `Oct 13, 2026` → `unanchored=['13','2026']`; `10/13/2026` → same; `October 2026` → `unanchored=['2026']`; `October thirteenth` → unmatched. Consistent with constraint (4), but the October-13 false-rejection class survives those renderings.
- Masking is local to `check_fact_anchor`. `check_our_value`/`_anchored_values` still treat named dates as numbers: `"The report was published on October 13, 2026."` classifies `other` (nums `['13','2026']`) while the ISO form `"…on 2026-10-13."` classifies `neutral`. Date-only sentences therefore still dilute the our-value share (0.40 floor) and are excluded from receipts; the diff does not propagate. Overlap, freshness and editorial gates are untouched, as required.
- Date authorization ignores tier/approval/freshness — every dict in `slot["facts"]` contributes vintages, including facts `check_claim_scope` would reject. This mirrors `source_number_pool` in the ancestor, but I could not read the parent's `_fact_quantity_pool`; if it tier-filters, the date path is more permissive than the quantity path. Verify against `e7112006`.
- Vintage parse is prefix-only: `^\d{4}-\d{2}-\d{2}(?!\d)` accepted `"2026-10-13T09:30:00Z-extra"` in my run (trailing junk ignored). Lenient but low impact.
- Ordinal suffixes are unvalidated (`"October 13st, 2026"` passes). Cosmetic.
- Minor: `"October 13:30"` leaves `30` unanchored; `"October 13, 20265"` masks the date and leaves `20265` unanchored (fails safely); `"October 135"` never matches (fails safely).

**Bottom Line**
Blockers 1–3 are genuine numeric/date bypasses; 4–5 are strictness regressions of the very class this follow-on targets. Minimal hardening set: boundary allowlist instead of the magnitude denylist, per-block masking, mandatory in-clause year binding, and whitespace-tolerant `,`/`(` year separators plus range handling. No acceptance or retry is implied, and the quarantined draft's three overlap failures and editorial padding are unaffected by this diff.
