# F03-W2-4c · Skew source-break sentence — research note

Packet: `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md`
(merged #7770, 2026-09-23) rules: "Ship one plain-language sentence about
the source break on the options page."  This note is the implementation
record for A-F03-W2-4c.

## What the sentence says

`engine/options_skew.py::emit_from_ledger` now publishes three additive
keys: `source_windows`, `source_break`, and `history_dates`.  When
`source_break` is True AND at least one ThetaData window AND at least one
Polygon window exist, `scripts/build_options_command.py::skew_source_note`
returns one bilingual sentence the templates/options.html.j2 Directional
read panel renders inside `.oew-pfoot`:

> Put-skew history comes from two sources: ThetaData end-of-day option
> chains for 22 Jun 2026–13 Aug 2026 and 22 Sep 2026–23 Sep 2026, and the
> earlier Polygon feed for 14 Aug 2026–18 Sep 2026. A skew change that
> crosses one of those boundaries is not like-for-like.

> 认沽偏度历史来自两个来源：2026年6月22日–2026年8月13日和
> 2026年9月22日–2026年9月23日使用 ThetaData 日终期权链，
> 2026年8月14日–2026年9月18日使用较早的 Polygon 数据。
> 跨越这些边界的偏度变化不可直接比较。

The sentence never fabricates a "second source" claim on a single-source
ledger — `skew_source_note` returns `None` unless BOTH vendors are
present in the windows.  The Directional read panel already covers skew
through its own cards when there is no break to explain.

## Why it is data-driven

Three pieces of fact feed the sentence:

1. **The windows** are computed by `engine/options_skew.py::source_windows`,
   a pure helper that groups the normalised ledger by `date`, assigns each
   date its majority source (rows without a `source` column → `polygon_gex`,
   the legacy read), and returns the ascending list of maximal contiguous
   runs.  Session-only dates: weekend as-of rows are excluded before
   grouping, the same way `emit_from_ledger` already excludes them when
   it picks the latest session — the helper reuses the W2-4b rule by
   construction.

2. **The break flag** is the simplest possible derivation: `len(windows)
   > 1`.  It is `True` whenever the ledger crosses a source boundary and
   `False` otherwise; nothing about the gate, the names list, or the dated
   payload touches it.

3. **The sentence text** is a frozen template — see
   `_SKEW_NOTE_EN` / `_SKEW_NOTE_ZH` in
   `scripts/build_options_command.py`.  Vendor names "ThetaData" and
   "Polygon" are allowed on the face; the source *slugs* `thetadata` and
   `polygon_gex` MUST NEVER reach the page (the test
   `test_render_with_note_emits_one_element` pins both halves of that
   contract — the sentence is present AND no slug leaks).

## Three windows measured today

The seat ran the one-time backfill today (2026-09-23) on the live ledger
(restored from R2 on the render hosts).  The receipt on the ledger's
backfill row says: 38 dates 2026-06-22..2026-08-13 recomputed from the
ThetaData store, 3,965 rows replaced, 1,212 added, 2026-07-03 not in
store.  The mixed-source picture the consumer now prints is:

| source     | first_date  | last_date   | sessions |
|------------|-------------|-------------|----------|
| thetadata  | 2026-06-22  | 2026-08-13  | 37       |
| polygon_gex| 2026-08-14  | 2026-09-19  | 27       |
| thetadata  | 2026-09-22  | 2026-09-23  | 2        |

(2026-07-03 is skipped per the backfill receipt — it is not in store, and
the backfill receipt does not move a missing date onto a neighbour.)

## How it retires when the polygon window is ever recomputed

The sentence disappears on its own the moment `source_break` flips to
False — that is, when a future backfill rewrites the legacy Polygon gap
under the same canonical-wins rule (`engine/options_skew.py::snapshot`)
the W2-4a engine already ships.  At that point the three windows collapse
to one thetadata window and `skew_source_note(...)` returns None; the
Directional read panel renders no element because the template branch is
`{% if skew_source_note_en %}`, and the per-candidate "Skew evidence"
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