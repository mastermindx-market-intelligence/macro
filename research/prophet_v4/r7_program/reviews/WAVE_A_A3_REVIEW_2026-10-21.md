# Wave A slice A3 review — refusal-receipt disclosure + Today count (PR #9955)

- Reviewer lane: `lane/pro-wavea-receipts-review-20261021-r1` (read-only; this file is the only write)
- BASE under review: `21a95484becdc5c5671e9a3f5586cc5890840e06` (single commit over `2d50943eb154`)
- Diff reviewed: `git diff 2d50943eb154430efda02ffc117bb37b5addc242..HEAD` (three files)
- Date: 2026-10-21
- Verdict: **PASS_WITH_NOTES** — no blocking finding; five notes and one evidence gap, none of which gate the slice.

## Commands run (SCOPE)

```
$ python3 -m pytest -q -p no:cacheprovider tests/test_prophet_r7_wave_a_guards.py tests/test_prophet_whynot_receipts.py
86 passed in 6.90s                                    # exit 0

$ python3 -m pytest -q -p no:cacheprovider tests/test_ci_pack.py -k "exclusive or washout or narrow"
7 passed, 197 deselected in 116.25s (0:01:56)         # exit 0
```

No `ModuleNotFoundError`. Mutation runs (surface 6) happened in a throwaway copy at
`/tmp/a3_mut` (lane worktree untouched; `git status` clean before and after).

## Attack surface 1 — Add-only: PASS

`git diff --numstat 2d50943eb154..HEAD`:

```
5	0	.github/ci/legacy-jobs.yml
128	0	templates/_prophet_receipts.html.j2
359	0	tests/test_prophet_r7_wave_a_guards.py
```

`git diff 2d50943eb154..HEAD -- templates/_prophet_receipts.html.j2 | grep -c '^-[^-]'`
→ **0** removed lines. An insertion-only unified diff preserves every pre-existing
line byte-for-byte in order, so `t()` (`templates/_prophet_receipts.html.j2:40`),
`pvr_copy` (`:48-65`), `pvr_css`'s pre-existing rules and `pvr_shelf` (`:147-263`) are
byte-identical; OQ5's set is intact, and the whynot pin test in the run above keeps
`pvr_copy == engine.prophet_bridge.REFUSAL_COPY` (engine file not in the diff). The
template's two hunks are: (a) 26 CSS lines inserted inside `pvr_css()`'s `<style>`
block before `</style>` (`:118-143`) and (b) the two macros appended (`:265-365`):

```diff
@@ -115,6 +115,32 @@ html[data-theme="light"] .pvr-g.is-near .pvr-tk{color:var(--text)}
 @media (max-width:640px){.pvr-why{font-size:12px}}
+{# ═ R7 WAVE A (R7-24) — see-all refusal receipts (pvr_receipts) + the Today count
+   (pvr_today_count). Neutral surfaces only (Chairman rule 2026-10-18): hairline
+   dividers, even borders, ink via --text/--muted/--ink-* — no container edge accent,
+   no box-shadow. The summary focus ring is the only accent, and it is an outline. #}
+.pvr-rcs{margin:0}
...
+.pvr-tc-a{font-size:11.5px}
+@media (max-width:640px){.pvr-rc-why{margin-left:0;text-align:left;flex-basis:100%}}
 </style>
 {% endmacro %}
@@ -235,3 +261,105 @@ ...
+{% macro pvr_receipts(cx, limit=4, next_build_en=none, next_build_zh=none, sample=false) -%}
...
+{% macro pvr_today_count(cx, href, sample=false) -%}
```

**NOTE 1:** the packet describes the change as "appends two macros"; the CSS hunk is an
insertion into the shared `pvr_css()` macro (not a file-end append, and not one of
OQ5's named byte-unchanged macros). Still add-only — zero removed lines — and CSS for
the new classes belongs in the shared style macro. Cosmetic description gap only.

## Attack surface 2 — Ordering and degradation: PASS (one note)

The sort (`templates/_prophet_receipts.html.j2:289-318`), quoted:

```jinja
{%- if cx is mapping %}
...
{%- for g in (cx.groups or []) %}
  {%- for nm in (g.names or []) %}
    {%- if g.reason == 'validation_failed' %}
      {%- set _ = _vf.append({'nm': nm, 'reason': 'validation_failed'}) %}
    {%- else %}
      {%- set _ = _rest.append({'nm': nm, 'reason': g.reason}) %}
    {%- endif %}
  {%- endfor %}
{%- endfor %}
...
{%- set _ordered = _vf + (_num|sort(attribute='nm.score', reverse=true)) + _tail %}
```

- **validation_failed always precedes**: `_vf` is prepended unconditionally, so the
  plan-data refusals lead regardless of score or group position — `test_display_order_is_r7_24_and_cx_is_untouched`
  feeds them mid-board (scores 12/11 among 70/50/30) and asserts VFA1→VFB2→SC70→SC50→SC30→NOSCORE.
  Non-numeric scores are partitioned to `_tail` (original order) instead of raising.
- **Ties stable**: Jinja `sort` delegates to Python `sorted` (stable, including
  `reverse=true`). Independently probed with equal scores (T70a,T70b=70.0; T50a,T50b=50.0):
  render indices `[202, 699, 1196, 1693]` — original order preserved.
- **Degradation**: gate at `:289` (`cx is mapping`). Renders `""` for `None`, `7`,
  `"not-a-mapping"`, `{}`, `{"groups": []}`, empty-`names` groups, and `groups` as a
  string (probed directly and via `test_receipts_degrade_to_empty_without_names`).
  `pvr_today_count` gates harder at `:357` — `{%- if cx is mapping and cx.passed is integer and cx.passed > 0 %}` —
  probed: `{"passed": 0}`, `{"passed": True}`, `{"passed": "3"}`, `{}`, `{"passed": 3.5}`
  all render `""` (bool is excluded by Jinja's `integer` test, matching the macro's
  "True is not a count" comment). `cx` is never mutated or re-counted
  (`test_..._and_cx_is_untouched` deep-copies and compares; header shows `cx.passed`,
  and the capped case keeps `Showing 4 of 20` while the overflow counts names present,
  `Show 2 more`, never `passed − limit`).

**NOTE 2:** one malformed shape does not render empty: a mapping with well-formed
groups+names but a *missing required* `passed` key renders the heading with a blank
count — `<p class="pvr-rc-hd"><span class="l-en"> names</span><span class="l-zh"> 只</span></p>`
(probed; permissive `Undefined` stringifies to `''` in the `~` concat). `passed` is a
documented required key of the receipts contract (file header, `:28-32`), and the
accepted `pvr_shelf` has the identical permissive characteristic for its required keys
(`cx.declined`, `cx.considered`), so this is parity, not a regression. Not blocking.

## Attack surface 3 — Copy: PASS (one gap, one note)

- **The binding pair (OQ5)** — parsed with `ast` from the template's `pvr_copy` and
  from `engine.prophet_bridge.REFUSAL_COPY`; byte-equal element-wise, and equal to the
  seat's binding quote (straight apostrophes; spaced em dash in both languages):

  ```
  template pvr_copy['validation_failed'][0] == "Passed the board's checks — tonight's plan data didn't verify"
  template pvr_copy['validation_failed'][1] == '通过了榜单检查 — 但今晚的计划数据未能核验'
  engine  REFUSAL_COPY['validation_failed']  == same pair (byte-equal)
  ZH spaced em dash ' — ': present
  ```

  The macro reads the title from `pvr_copy` at `:324`
  (`{%- set _cp = pvr_copy.get(it.reason) or pvr_copy['unknown'] %}`) and never retypes
  it; `test_validation_failed_title_is_mains_pair_byte_for_byte` also pins exactly one
  literal of each string in the file (`SRC.count(VF_EN) == 1`).
- **OQ4 — plain count link, no chevrons**: `:361` renders
  `{{ t('See all ' ~ cx.passed ~ ' passed names', '查看全部 ' ~ cx.passed ~ ' 只未纳入标的') }}`
  inside one `<a>`; grep of the whole new-macro region finds no `›` `»` `→` `❯` `chevron`;
  the test asserts the glyphs absent. The Today label `t('Passed on tonight', '今晚未纳入')`
  byte-reuses `pvr_shelf`'s existing heading (2 occurrences in file) — no invented label.
- **Sample footnote opt-in**: `{%- if sample %}` gates in both macros (`:348`, `:362`);
  `test_sample_footnote_is_opt_in_in_both_macros` asserts the exact EN/ZH line on when
  `sample=true` and absent otherwise, in both macros.
- **OQ9**: the ZH title keeps ` — `; the other new ZH strings carry no dash positions
  where the ruling applies.

**GAP:** the packet's named design source
`research/prophet_v4/r7_design/R7_DESIGN_SPEC_2026-10-21.md` **does not exist at BASE**
— not tracked, not on disk, and `research/` is not excluded by
`config/sparse_worktree.json` (only `data/ site/ mockups/ verify_shots/` are). The
r7_design tree holds only `R7_DESIGN_WORKLOG.md` + `variants/`; the handoff, census and
prior `RECEIPT_TRUTH_REVIEW_2026-10-21.md` do not carry the A3 copy rows. The remaining
new strings ("Show N more"/"再显示 N 只", the "Showing X of Y…" cap line, "Open
research"/"查看研究", "What didn't verify"/"未能核实的内容", the reassurance sentence,
the sample footnote) were therefore verified against the seat rulings quoted in the
packet, byte-consistency with the file's existing copy, and the receipt-shelf variant
(`variants/receipt-shelf/1.html`, whose label matches) — **not** verbatim against the
spec. If the spec exists elsewhere (e.g. a Paper page), a follow-up can diff it; nothing
in the bytes suggests drift (all copy is composed through `t()` in EN/ZH pairs and
reuses the established wording family).

**NOTE 3:** mixed apostrophe style *within* the new body copy: curly `’` in
"What didn’t verify" and "Tonight’s plan data", straight `'` in "Because the plan data
didn't verify" — against the file's all-straight convention (`pvr_copy`, shelf lede).
Invisible to nearly all readers; a one-byte-class cleanup when the spec text is located.

## Attack surface 4 — Escaping and links: PASS

The rendered contract rides the same env shape as
`tests/test_prophet_whynot_receipts.py` — `jinja2.Environment(loader=FileSystemLoader,
autoescape=True)` (test `:73-77`). All interpolations (`it.nm.ticker`, `it.nm.name`,
`it.nm.sector`, `_cp` strings) therefore pass MarkupSafe escaping. Hostile probe
(`test_no_title_attribute_and_hostile_strings_stay_escaped`, `:285-297`):

```python
_name("X<b>Y", name="Foo<b>Bar Ltd", ...)
assert "title=" not in out
assert "&lt;b&gt;" in out          # ticker AND name escaped where they render
assert "<b>" not in out            # nothing reopens as markup
assert 'href="stock.html#X&lt;b&gt;Y"' in out     # fragment cannot carry unescaped markup
assert 'href="a&lt;b&gt;.html"' in out            # today-count href too
```

The research href (`:339`, `:343`) builds `stock.html#{{ it.nm.ticker }}`; under
autoescape the fragment cannot break out of the attribute (`"`, `<`, `>`, `&`, `'` all
escaped — verified in the rendered probe). No `title=` attribute anywhere in either
macro (grep of the new region clean; asserted in both outputs). `pvr_today_count`'s
`href` is caller-supplied and escaped for attribute breakout; scheme trust is the
caller's contract, identical to every other href the site templates render.

## Attack surface 5 — Doctrine and accessibility: PASS (two notes)

Census of every CSS declaration in the added lines: one `border-top` (hairline divider,
`:124`), two `outline`, one `outline-offset`. **No** `border-left`, `border-inline-start`,
`inset`, `box-shadow` (the only "box-shadow" hit is the word inside the explanatory
comment), no hex colors, and no `var(--up`/`var(--down`/`var(--warn` text ink — the OQ7
guard plus manual grep are both clean. Full even border, neutral ink, no accent stripe:

```css
.pvr-rc,.pvr-rc-more{border-top:1px solid var(--line-quiet, var(--line))}
.pvr-rc-sum:focus-visible{outline:2px solid var(--ink-link);outline-offset:2px}
```

- **Focus**: `:127` is a complete four-side outline (2px, 2px offset) on every
  `<summary class="pvr-rc-sum">` — per-name and the overflow summary share the class.
  Both themes: `--ink-link` is `color-mix(... var(--link) ..., var(--text))`
  (`templates/theme.css:382`), and every other new color rides theme-flipping vars
  (`--text`, `--muted`, `--line`) with no literal colors, so light/dark both hold with
  no explicit `html[data-theme="light"]` overrides (which the pre-existing rules need
  only because they hardcode `#fff`).
- **`<details>`/`<summary>` vs the spec's `<button aria-expanded>`**: the deviation is
  packet-ruled and documented in the template comment (`:279-281`). Judgment: native
  disclosure is keyboard-operable (Enter/Space), exposes expanded state to AT without
  JS, and the summary's text content (ticker, name, sector, why) is its accessible
  name — equal semantics, less machinery. ACCEPTED.
- **NOTE 4:** `--line-quiet` is referenced at `:124` but defined nowhere in `templates/`
  (sole occurrence repo-wide); it always falls back to `var(--line)`. Harmless dangling
  token — either define it or drop the indirection at integration.
- **NOTE 5:** `.pvr-rc-a`/`.pvr-tc-a` links get no explicit focus rule and are not in
  theme.css's `:where(...):focus-visible` allowlist (`templates/theme.css:684-688`);
  they currently rely on the UA default outline (no global reset strips it — the
  `outline:none` hits at theme.css:1061/1120/1618 are component-scoped). Fine while the
  partial is included nowhere; the integration slice should confirm the host page's
  link-focus treatment.

## Attack surface 6 — Guard realism (mutations in a throwaway copy): PASS

Throwaway copy at `/tmp/a3_mut` (tree copied, `.git` pointer removed; lane untouched).
Each mutation applied alone, then `python3 -m pytest -q -p no:cacheprovider
tests/test_prophet_r7_wave_a_guards.py`:

**(i) `border-left:3px solid var(--warn)` appended to the `.pvr-rc,.pvr-rc-more` rule —**

```
FAILED tests/test_prophet_r7_wave_a_guards.py::test_guard2_no_container_edge_accent_in_the_receipts_estate
>       assert not violations, violations
E       AssertionError: ['_prophet_receipts.html.j2: border-left:3px solid var(--warn)']
tests/test_prophet_r7_wave_a_guards.py:342: AssertionError
1 failed, 23 passed in 0.90s
```

**(ii) ZH validation_failed title swapped to `通过了榜单检查 — 但今晚的数据未能核验` (one word dropped) —**

```
FAILED tests/test_prophet_r7_wave_a_guards.py::test_validation_failed_title_is_mains_pair_byte_for_byte
>       assert VF_ZH in out
E       assert '通过了榜单检查 — 但今晚的计划数据未能核验' in '<div class="pvr-rcs">\n  <p class="pvr-rc-hd">...'
tests/test_prophet_r7_wave_a_guards.py:134: AssertionError
1 failed, 23 passed in 0.89s
```

Both mutations are caught by the *new* file alone, each by a failing assertion that
names the exact offending bytes (guard 2) or the exact expected string (OQ5). No
uncaught mutation. (Mutation (ii) would additionally break the whynot engine pin.)

## Attack surface 7 — CI registration: PASS

`.github/ci/legacy-jobs.yml` hunk (all four additions; job `washout-turn-organ:` opens
at `:26210`, next job `prophet-anticipation-intake:` at `:27280`, so `:27111`, `:27129`,
`:27152` and `:27268` all sit inside it):

```diff
@@ -27111,6 +27111,7 @@ jobs:
       - "templates/_prophet_card.html.j2"
+      - "templates/_prophet_receipts.html.j2"
       - "templates/_prophet_workspace.css.j2"
@@ -27128,6 +27129,7 @@ jobs:
       - "templates/theme.js"
+      - "templates/watchlist.html.j2"
       - "tests/test_build_live_quotes.py"
@@ -27150,6 +27152,7 @@ jobs:
       - "tests/test_prophet_journey_reconcile.py"
+      - "tests/test_prophet_r7_wave_a_guards.py"
       - "tests/test_prophet_live_evaluator.py"
@@ -27265,6 +27268,8 @@ jobs:
       - name: Prophet detector, organ and disposition contracts (one native process)
         run: python -m pytest ... -q
+      - name: Prophet R7 Wave A refusal receipts and design guards (A3)
+        run: python -m pytest tests/test_prophet_r7_wave_a_guards.py -q
```

Load closure vs `paths:` — the suite's declared closure (test docstring `:32-34`, `SRC`
dict `:58-62`; no glob/walk/subprocess, no scripts import) is exactly four repo files:
`templates/_prophet_receipts.html.j2` (added), `templates/watchlist.html.j2` (added),
`templates/_us_prophet_plan_cards.html.j2` (pre-existing at `:27122`), and the test file
itself (added). Imports are `jinja2`, `pytest`, stdlib — all already in the job.
`tests/test_ci_pack.py -k "exclusive or washout or narrow"`: `7 passed` — the
registration obeys the pack contract.

## Attack surface 8 — Custody: PASS

```
$ git diff --stat 2d50943eb154430efda02ffc117bb37b5addc242..HEAD
 .github/ci/legacy-jobs.yml             |   5 +
 templates/_prophet_receipts.html.j2    | 128 ++++++++++++
 tests/test_prophet_r7_wave_a_guards.py | 359 +++++++++++++++++++++++++++++++++
 3 files changed, 492 insertions(+)
```

Exactly the three declared files, all insertions; one commit in range
(`21a95484becd`). `engine/prophet_bridge.py`, `tests/test_prophet_whynot_receipts.py`,
`templates/dashboard.html.j2`, `templates/_prophet_card.html.j2`, the nav family
(`_site_nav/_public_nav/_navlinks`, `navigation-refresh.css`, `nav_market.js`,
`theme.js`) and `.github/workflows/` are untouched (absent from the diff). No consumer
includes the new macros anywhere (`grep -rn 'pvr_receipts\|pvr_today_count'` over
`*.py *.j2 *.html` hits only the partial and the new test) — "not included anywhere
yet" holds.

## Notes register

| # | Note | Severity |
|---|------|----------|
| 1 | CSS lives in `pvr_css()`'s style block, not literally a file-end append; still add-only | cosmetic |
| 2 | Missing required `passed` (with well-formed groups) renders a blank-count heading — parity with `pvr_shelf`'s permissive access to its required keys | low |
| 3 | Mixed curly/straight apostrophes within the new body copy | cosmetic |
| 4 | `--line-quiet` referenced but undefined; falls back to `--line` | low |
| 5 | New link classes rely on UA-default focus (not in theme.css focus allowlist) until integration | low |
| GAP | Named spec file absent at BASE; copy verified against seat rulings + internal consistency instead | evidence |

## GAPS

- Spec file `research/prophet_v4/r7_design/R7_DESIGN_SPEC_2026-10-21.md` does not exist
  at BASE (detail under surface 3). Everything adjudicable from the packet's quoted
  rulings was checked; the verbatim spec diff of the non-binding new strings is the one
  thing this review could not do.
- No visual/browser verification (out of scope by packet; assertions are markup-level,
  same as the whynot suite).

## DEVIATIONS

- None. Read-only beyond this report; mutations confined to `/tmp/a3_mut` (deleted after
  the runs); no network, installs, push, PR, label or merge; protected paths
  (`.claude/`, `engine/news_impact/`, `scripts/build_turn_watch.py`,
  `data/prophet/ledger*.jsonl`) never read or touched; no `R2_*`/`*_KEY`/`*_SECRET`/
  `*_TOKEN` file opened.

SESSION END: PROVEN_OUTCOME
