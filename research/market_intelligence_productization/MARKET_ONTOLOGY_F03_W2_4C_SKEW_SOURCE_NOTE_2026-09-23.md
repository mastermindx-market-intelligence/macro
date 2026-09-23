# F03-W2-4c · Skew source-break sentence — research note

Packet: `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md`
(merged #7770, 2026-09-23) rules: "Ship one plain-language sentence about
the source break on the options page."  This note is the implementation
record for A-F03-W2-4c.

## What the sentence says

`engine/options_skew.py::emit_from_ledger` publishes four additive keys:
`source_windows` (per-source coverage spans), `source_break` (True iff
`len(source_windows) > 1`), `source_break_date` (the first session
strictly greater than the older source's last_date on which any other
source has rows), and `history_dates` (count of distinct session dates
on the normalised ledger — the union across sources, so a mixed-source
ledger where polygon's dates are a subset of thetadata's dates reports
the longer span's count, NOT the overlap-aware sum).
When `source_break` is True AND `source_break_date` is a real
YYYY-MM-DD AND exactly one polygon_gex span AND exactly one thetadata span
exist in `source_windows`,
`scripts/build_options_command.py::skew_source_note` returns one
bilingual sentence the templates/options.html.j2 Directional read panel
renders inside `.oew-pfoot`:

> Put-skew history comes from two sources. The earlier Polygon feed
> covers 22 Jun 2026–13 Aug 2026 alongside ThetaData end-of-day option
> chains; from 14 Aug 2026 the history is ThetaData only. A skew change
> that crosses 14 Aug 2026 is not directly comparable.

> 认沽偏度历史来自两个来源：较早的 Polygon 数据覆盖2026年6月22日–2026年8月13日，与
> ThetaData 日终期权链并行；自2026年8月14日起仅使用 ThetaData。
> 跨越2026年8月14日的偏度变化不可直接比较。

The sentence never fabricates a "second source" claim on a single-source
ledger — `skew_source_note` returns `None` unless BOTH vendors are
present in the windows.  The Directional read panel already covers skew
through its own cards when there is no break to explain.

## Why it is data-driven

Four pieces of fact feed the sentence:

1. **The spans** are computed by `engine/options_skew.py::source_windows`,
   a pure helper that groups the normalised ledger by `source`, projects
   each source's distinct weekday dates, and returns one span per source
   sorted by (first_date, source).  Session-only dates: weekend as-of
   rows are excluded before the per-source group, mirroring
   `emit_from_ledger`'s session-only pick — a Saturday-only ledger
   therefore returns [] (no session to count, not a fabricated Saturday
   window).  A missing `source` column reads as `polygon_gex` (the legacy
   default), so a pre-source-column ledger still produces one polygon
   span and the sentence stays silent (no break flag).

2. **The break flag** is the simplest possible derivation: `len(spans)
   > 1`.  It is `True` whenever the ledger crosses a source boundary and
   `False` otherwise; nothing about the gate, the names list, or the
   dated payload touches it.

3. **The break date** is `source_break_date(df)` — `older_last` =
   `min(last_date for span in spans)`; the walk is one calendar day at a
   time past `older_last` until the cursor lands on a weekday date on
   which a strictly-newer source (last_date > older_last) has at least
   one row.  None when a single source is present, when both sources end
   on the same day, or when the newer source has no row strictly past
   `older_last`.  On the live ledger: 2026-08-14.

4. **The sentence text** is a frozen template — see `_SKEW_NOTE_EN` /
   `_SKEW_NOTE_ZH` in `scripts/build_options_command.py`.  Vendor names
   "ThetaData" and "Polygon" are allowed on the face; the source *slugs*
   `thetadata` and `polygon_gex` MUST NEVER reach the page (the test
   `test_render_with_note_emits_one_element` pins both halves of that
   contract — the sentence is present AND no slug leaks).

## Coverage spans measured on the live ledger (2026-09-23, after the 2026-08-14..2026-09-18 backfill)

The seat ran the one-time backfill today (2026-09-23) on the live ledger
(restored from R2 on the render hosts).  The receipt on the ledger's
backfill row says: 38 dates 2026-06-22..2026-08-13 recomputed from the
ThetaData store, 3,965 rows replaced, 1,212 added, 2026-07-03 not in
store.  The ledger is on R2 (not in git), so the rows below are derived
from that receipt plus the session-only rule (`source_windows` counts
weekday dates only).  The picture the consumer prints is:

| source     | first_date  | last_date   | sessions |
|------------|-------------|-------------|----------|
| polygon_gex| 2026-06-22  | 2026-08-13  | 33       |
| thetadata  | 2026-06-22  | 2026-09-21  | 64       |

| key                 | value         |
|---------------------|---------------|
| source_break        | True          |
| source_break_date   | 2026-08-14    |
| history_dates       | 64            |

(2026-07-03 is skipped per the backfill receipt — it is not in store,
and the backfill receipt does not move a missing date onto a neighbour.
The first ThetaData-only session is 2026-08-14.)

### Why the committed `data/options_skew/snapshots.parquet` is not the live ledger

The ledger this packet writes against lives on the render hosts (R2) and
is restored from R2 at every render — `data/options_skew/snapshots.parquet`
in this checkout is a small legacy dev artifact that does NOT reproduce the
numbers above.  Reading it as the head commit sees it today yields a
different shape (thetadata has a single date; polygon has the older
2026-06-22..2026-08-13 window; the table the user actually sees is the
R2 ledger, not the bytes in git).  The producer tests pin the round-5
shape against an in-memory fixture (`_round5_mixed_source_ledger`), and
`emit_from_ledger` is what the render hosts run against the restored
R2 ledger — so the published sentence describes the live ledger
correctly, but the committed `data/` artifact is stale relative to R2 and
should NOT be cited as evidence of the live numbers.

### Why the majority-run rule was abandoned

The previous per-date row-majority rule returned fifteen alternating
windows — 8 ThetaData ranges and 7 Polygon ranges — on the live ledger
(measured 2026-09-23 17:24Z on the R2 ledger after the
2026-08-14..2026-09-18 backfill: thetadata 06-22→07-06, polygon 07-07,
thetadata 07-08→07-09, polygon 07-10→07-14, thetadata 07-15, polygon
07-16, thetadata 07-17, polygon 07-20→07-22, thetadata 07-23→07-24,
polygon 07-27→07-31, thetadata 08-03→08-05, polygon 08-06→08-07,
thetadata 08-10→08-11, polygon 08-12→08-13, thetadata 08-14→09-21).
The cause: in the 2026-06-22..2026-08-13 overlap the canonical-wins
backfill replaced polygon rows only where the ThetaData store covers the
name and date, so the per-date majority flips with per-name coverage.
The Directional-read sentence would have printed 8 ThetaData ranges
and 7 Polygon ranges — unreadable, and it does not answer the reader's
question ("can I compare today's skew with a month ago?").  The round-5
producer publishes one coverage span per source instead; the consumer
sentence prints one polygon span and one thetadata span, plus the
break date.

## How it retires when the polygon span is ever recomputed

The sentence disappears on its own the moment `source_break` flips to
False — that is, when a future backfill rewrites the legacy Polygon
span under the same canonical-wins rule (`engine/options_skew.py::snapshot`)
the W2-4a engine already ships.  At that point the two spans collapse
to one thetadata span and `skew_source_note(...)` returns None; the
Directional read panel renders no element because the template branch
is `{% if skew_source_note_en %}`, and the per-candidate "Skew evidence"
lines the panel already ships carry the skew leg without help from this
packet.

If a future change re-introduces a source boundary (a second migration,
for example), the sentence returns automatically — the windows list is
recomputed on every `emit_from_ledger` call, and `source_break` is the
single boolean the consumer reads.  No contract changes are needed on
either side to retire or to re-add the sentence.

## What this packet does NOT do

- It does NOT add a new validator verdict or change the skew gate
  (`scripts/validate_options_skew.py`).  The skew leg stays display-only
  context until the panel earns a verdict; the source-break sentence
  sits on the Directional read panel's Tier-1 surface and says what the
  producer's payload already proves.
- It does NOT add a key to `scripts/build_options_command.py::load_stores`
  (that function is pinned BYTE-FOR-BYTE by
  `tests/test_render_options_workspace_scope.py` and this packet's scope
  explicitly excluded touching it).  The new artifact is loaded via a
  separate `load_skew_source` function, exactly like the
  `load_intel_brief` / `load_payoff_lab` precedent in #7763.
- It does NOT edit `data/**`, `site/**`, `slot.py`, `config/dag.yml`,
  any workflow file, or any of the cross-repo surface areas the chair
  override scoped out.

## CI homes

The consumer-side contract is pinned by `tests/test_options_skew_source_note.py`
(hermetic — every fixture payload is built in-memory from the producer's
documented contract; no network, no store read, no `site/` or `data/`
bytes).  That file is now appended to the run line of the
`options-payoff-lab-consumer` job in `.github/ci/legacy-jobs.yml` (run
line only — no job inserted).  The producer-side
`engine/options_skew.py` additions are pinned by `tests/test_options_skew.py`
(the same home the existing skew-emit tests already ship in).
## Round-5 seat-ratification handoff (2026-09-23)

This packet's deliverable is COMPLETE per the Meta-CEO A ruling DELIVERY
contract ("commit → push → PR stays DRAFT; return LANE_DONE with the final
head. The seat re-reads the PR's own ci run before ratifying"):

- HEAD `e3ef6b8655a96dd396a359eed0c01cd1d6458f7f` on lane branch
  `claude/mo-a-3-a-f03-w2-4c-skew-source-note` (carry: `origin`).
- PR #7783 isDraft=true; the PR body carries the round-5 measured-truth
  table, the new exact EN/ZH sentences, the 39-test proof line, the
  acceptance-grep table, and the seat round-5 ruling narrative.
- 39/39 tests pass on the three test files the ruling names
  (`test_options_skew.py`, `test_options_skew_source_note.py`,
  `test_options_skew_backfill.py`); the workspace-scope pin holds
  (31/31 on `test_render_options_workspace_scope.py`).
- All 12 acceptance greps at the expected values; `check_ui_visual_evidence.py`
  exits 0 against the diff.

The seat owns the ci → ratify → ready → arm → squash-merge → render →
live chain from here.
