# R7 Wave A slice A1 — adversarial review (PR #9954)

- **Reviewer seat**: ROUTE review / C1 / routine-bounded, fresh checkout at BASE `b1130262307aa10ebe71c3547d7cb48d274c7337`
- **Artifact**: `git diff 526ce826f0898d8724e79acf3a884f9cec6f3096..HEAD` — 4 files, **422 insertions(+), 0 deletions**
- **Date**: 2026-10-21
- **Verdict**: **STATUS: PASS_WITH_NOTES**

```
.github/ci/legacy-jobs.yml                 |   3 +
templates/_us_prophet_plan_cards.html.j2   |  20 ++
templates/theme.css                        |  10 +
tests/test_prophet_r7_wave_a_plan_cards.py | 389 +++++++++++++++++++++++++++++
4 files changed, 422 insertions(+)
```

## Commands run (exact scope)

| # | command | tail | exit |
|---|---------|------|------|
| 1 | `python3 -m pytest -q -p no:cacheprovider tests/test_prophet_r7_wave_a_plan_cards.py` | `27 passed in 2.86s` | 0 |
| 2 | `python3 -m pytest -q -p no:cacheprovider tests/test_prophet_card_shared.py tests/test_prophet_plan_relation.py tests/test_prophet_lifecycle_state.py tests/test_prophet_surface_net.py tests/test_prophet_card_added_date.py tests/test_prophet_candidate_added_date_surfaces.py` | `24 failed, 290 passed, 2 skipped in 45.73s` | 1 |
| 3 | `python3 -m pytest -q -p no:cacheprovider tests/test_ci_pack.py -k "exclusive or washout or narrow"` | `7 passed, 197 deselected in 117.02s (0:01:57)` | 0 |

**Command 2 failures — all 24 identical at `526ce826`** (rerun in the throwaway copy; every failing
test ID at HEAD also fails at base; zero regressions). Attribution via `--tb=line`:

- 21 × `bs4.exceptions.FeatureNotFound: Couldn't find a tree builder with the features you requested: html5lib` (`test_prophet_card_shared.py`) — environment (missing parser lib).
- 1 × `ModuleNotFoundError: No module named 'rjsmin'` (`test_prophet_candidate_added_date_surfaces.py:874`) — environment per packet rule.
- 2 × pre-existing assertion drift, byte-identical at base:
  - `tests/test_prophet_lifecycle_state.py:501` — `At index 0 diff: 'templates/_prophet_setup_detail.html.j2' != 'templates/_us_prophet_plan_cards.html.j2'` (a second lifecycle consumer the gate test doesn't know; **not a file in this PR**).
  - `tests/test_prophet_candidate_added_date_surfaces.py:89` — `assert 0 == 1` (`len([])`: the pv_card-call extractor finds no calls at either revision).

The base-revision rerun showed 2 extra failures (`test_evidence_manifest_is_bound_to_the_captured_ui_head_and_fixture_bytes`, `test_plv_evidence_states_are_distinct_for_every_shell_cell`, both `@pytest.mark.needs_full_checkout("mockups")` hitting `FileNotFoundError` on `mockups/evidence/...`): the throwaway copy has no `.git`, so the marker's skip detection could not see the sparse state and ran them. In the lane worktree at HEAD these are exactly the "2 skipped". Copy artifact, not repo behavior.

## Surface 1 — Record-state truth: **PASS**

New template hunks (`templates/_us_prophet_plan_cards.html.j2:53-62`):

```jinja
{%- if p.get('origination_mode') is string and p.get('origination_mode').startswith('outage_backfill') -%}
  {%- set _rdt = p.get('recorded_at') -%}
  {%- set _rd_ok = _rdt is string and _rdt|length == 10 and _rdt[4] == '-' and _rdt[7] == '-' and _rdt[:4].isdigit() and _rdt[5:7].isdigit() and _rdt[8:10].isdigit() and 1 <= _rdt[5:7]|int <= 12 and 1 <= _rdt[8:10]|int <= 31 -%}
  {%- set _marks.rows = _marks.rows + [{'k':'lane',
    'en': ('Reconstructed from the ' ~ _MON_EN[(_rdt[5:7]|int) - 1] ~ ' ' ~ (_rdt[8:10]|int) ~ ' plan')|e if _rd_ok else 'Reconstructed plan, original date not supplied',
    'zh': ('依据 ' ~ (_rdt[5:7]|int) ~ '月' ~ (_rdt[8:10]|int) ~ '日计划重建')|e if _rd_ok else '重建的计划，原始日期未提供'}] -%}
{%- endif -%}
{%- if p.get('signal_date_basis') == 'legacy_formation_alias' and _candidate is not mapping -%}
  {%- set _marks.rows = _marks.rows + [{'k':'nck', 'en':'Older signal only', 'zh':'仅有旧信号'}] -%}
{%- endif -%}
```

- **Cannot fire spuriously**: the guard is `is string AND startswith('outage_backfill')`. Render-level proof (throwaway copy, HEAD template): `origination_mode` absent → no mark; `12345` (int) → no mark; `{"m":"outage_backfill"}` (dict) → no mark; `"nightly_outage_backfill"` (suffix, not prefix) → no mark. It mirrors `engine/prophet_integrity.py:38-45` exactly (`RECONSTRUCTED_ORIGINATION_PREFIX = "outage_backfill"` at l.35, verified).
- **Date gate**: `_rd_ok` is the strict YYYY-MM-DD check — length 10, `_rdt[4]=='-'`, `_rdt[7]=='-'`, all three groups `.isdigit()`, month `1..12`, day `1..31` — the same shape as the pre-existing screen-clock gate at `templates/_us_prophet_plan_cards.html.j2:34`. Malformed `recorded_at` → fallback pair `'Reconstructed plan, original date not supplied'` / `'重建的计划，原始日期未提供'`; render proof for `"2026-1x-17"`: fallback EN+ZH present, dated copy absent (`计划重建` not rendered). The dated branch's month/day slicing only evaluates when `_rd_ok` (Jinja conditional short-circuits), so a non-string `_rdt` never reaches `_rdt[5:7]`.
- **`recorded_at` provenance**: `engine/prophet_bridge.py::origination_note` (l.1435+) reads exactly `row.get("recorded_at")` — "the origination day being replayed" — confirming the comment's claim that this field names the original plan's date.
- **Older signal only cannot fire with a candidate attached**: `_candidate = cand_map.get(p.asset)` (l.16); the mark requires `_candidate is not mapping` (l.60). Render proof with `cand_map={"TEST":{...}}` and `signal_date_basis='legacy_formation_alias'` → no mark.
- **No buy-type class or glyph**: marks carry `'k':'lane'` (plain muted history chip, same `k` the row already uses at l.35/40) and `'k':'nck'` (the shared dashed absence chip). They render through `templates/_prophet_card.html.j2:650` as `<span class="pv-mk-i pv-mk-{{k}}">` text chips — `pv-mk-lane` (muted) / `pv-mk-nck` (transparent bg, muted ink, dashed outline, pre-existing rule at `_prophet_card.html.j2:415-417`). No `pv-buy/pv-near/pv-wait/...`, no `pv-dot on/pa` glyph; asserted by test Guard 5 (`tests/...:302-312`), passing.
- **No invented signal**: both conditions read existing producer fields (`origination_mode`, `recorded_at`, `signal_date_basis`, `cand_map`) — no new fetch or computation.

NOTE (non-blocking): the day gate caps at 31 without per-month validation (e.g. `2026-02-30` passes), mirroring the pre-existing `_screen_ok` shape the spec mandates; the field is engine-produced ISO output. Same strictness as the accepted screen clock, so NOTE, not BLOCKING.

## Surface 2 — Copy: **PASS** (with GAPS caveat on the spec file)

Template output vs packet-quoted spec copy, side by side:

| spec copy (packet) | template line (l.57-58, 61) | test assertion |
|---|---|---|
| `Reconstructed from the <Mon D> plan` / `依据 <M>月<D>日计划重建` | `'Reconstructed from the ' ~ _MON_EN[(m)|int - 1] ~ ' ' ~ (d)\|int ~ ' plan'` / `'依据 ' ~ m\|int ~ '月' ~ d\|int ~ '日计划重建'` | `"Reconstructed from the Oct 17 plan"`, `"依据 10月17日计划重建"` (tests l.186-187) |
| `Reconstructed plan, original date not supplied` / `重建的计划，原始日期未提供` | fallback branch l.57-58 | tests l.232-233 |
| `Older signal only` / `仅有旧信号` | literal l.61 | tests l.245-246 |

- **Month rendering**: `_MON_EN = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']` (l.14), indexed `int(month)-1` → all twelve months covered, Jan at index 0 correct for the gate's `1..12`. Double-digit: `Oct 17` / `10月17日` (test l.186-187). Single-digit day: leading zero dropped — `Mar 5` / `3月5日` (test l.207-211 asserts `"Mar 05 plan" not in html`), and `Jan 2` / `1月2日` for a different replay date (test l.200-204). `2027-01-02` proves the month index is parsed from the string, not fixed.
- **No lens stance word** (OQ2): the only new reader-visible strings are the four above — record-state facts, no verb/stage/lens word; test Guard 4 asserts `Buy/买入/Near/临近` never appear as visible text (l.295-299), passing.
- **OQ9**: no dash is used in any new ZH string (the fallback uses the fullwidth comma `，`), so the spaced-em-dash rule is vacuously satisfied.

GAPS: `research/prophet_v4/r7_design/R7_DESIGN_SPEC_2026-10-21.md` is **unreachable on this host** — not tracked at BASE (or any reachable ref; see GAPS §deviations for the corrupt-ref limitation), absent from the primary checkout and every reachable lane worktree, and no mirror exists in `r7_program/source|intel` or the worklog. Copy was therefore verified against the packet's verbatim quoted spec copy plus the test file's byte-exact assertions. The two `--line-quiet` values do match the tracked `R7_DESIGN_WORKLOG.md:43` (`--mx-light-line-quiet #E2E6EC`, `--mx-dark-line-quiet #272C35` — the worklog's mockup-namespace names for the same values).

## Surface 3 — theme.css add-only: **PASS** (one NOTE)

- **Zero deleted lines**: `git diff --stat` = `templates/theme.css | 10 +` with no `-`; every hunk line is `+`.
- **Every `--line`-defining block carries `--line-quiet`**. `grep -n -- '--line:' templates/theme.css` finds exactly two definitions (all other hits are `var(--line)` usages or the distinct `--ff-tint-*-line` tokens):

```css
:root {                                   /* dark default, l.69-70 */
  --line: #3a4150;
  --line-quiet: #272C35;
...
html[data-theme="light"] {                /* l.225-226 */
  --line: color-mix(in srgb, #1c2430 16%, #eaecf0);
  --line-quiet: #E2E6EC;
```

  There is **no** `prefers-color-scheme` block at all (`grep -c 'prefers-color-scheme' templates/theme.css` → `0`) and no other `data-theme` variant defining `--line`. No block is missing `--line-quiet`.
- **OQ8 rules scoped with fallback kept** (l.3452-3453):

```css
body.page-macro .mx5-sc-vw .sx-vw-row.sx-vw-row--elevated .sg-wx{color:var(--ink-warn, var(--warn));}
body.page-macro .mx5-sc-vw .sx-vw-row.sx-vw-row--elevated .sx-vw-tier{color:var(--ink-warn, var(--warn));}
```

  The originals stay byte-identical at l.3254 / l.3290 (`...{color:var(--warn,#f59e0b);}`); the overrides repeat the same selectors later in the file, winning at equal specificity in both themes. The light-theme `.sx-vw-tier` recolor at l.3293 (`html[data-theme="light"] body.page-macro .mx5-sc-vw .sx-vw-tier`, specificity 4 classes + 2 types) loses to the override (5 classes + 1 type), so the elevated tier paints from the ink token in light too. `--ink-warn` is defined at l.380. The test pins originals + later-override ordering (`tests/...:353-364`), passing.
- **`.nowrap` collides with nothing**: the only `.nowrap` selector anywhere in `templates/` (and `site/`) is the new `theme.css:3454` rule; every other hit is a `white-space:nowrap` *property* inside unrelated selectors, and `receipt-nowrap`/`flex-wrap:nowrap` are different identifiers. NOTE: no markup in this diff (or anywhere in `templates/`) carries `class="nowrap"` — the utility is added-unused: no behavior change on any existing page, evidently staged for a later Wave A slice.

## Surface 4 — Design doctrine: **PASS**

`git diff 526ce826..HEAD | grep -n 'border-left\|border-inline-start\|inset\|box-shadow\|border:'` → **zero matches**. The only added lines containing `color`/`border` are the two OQ8 text-ink rules and four string literals inside the test file's OQ8 constants. No container edge, stripe, or inset shadow is introduced; the new marks reuse neutral chip classes and text ink.

## Surface 5 — Test realism (mutation runs in throwaway copy): **PASS — both mutations caught**

- **Mutation (i)** — dropped the guard to `{%- if p.get('origination_mode') is string -%}` (any string mode fires the mark):
  ```
  1 failed, 26 passed in 2.37s — exit 1
  FAILED tests/test_prophet_r7_wave_a_plan_cards.py::test_live_rows_never_say_reconstructed[nightly]
  >       assert "Reconstructed" not in html
  E       assert 'Reconstructed' not in '\n<article ...article>\n\n'
  E         'Reconstructed' is contained here:
  E           ss="l-en">Reconstructed from the Oct 17 plan</span><span class="l-zh">依据 10月17日计划重建</span></span></div>
  ```
- **Mutation (ii)** — ZH older-signal copy `'仅有旧信号'` → `'旧信号'`:
  ```
  1 failed, 26 passed in 2.39s — exit 1
  FAILED tests/test_prophet_r7_wave_a_plan_cards.py::test_older_signal_only_when_basis_is_legacy_and_ticker_not_a_candidate
  E       assert '仅有旧信号' in '\n<article class="pvcard pv-noread pv-record" data-record-only="1" id="pv-TEST-BULL-20260901" data-ticker="TEST" data..."><span class="l-en">Creation date unavailable</span><span class="l-zh">建立日期暂缺</span></span>\n  </div>\n</article>\n\n'
  ```

Both mutations are caught by the new file with precise, named assertions; no uncaught mutation.

## Surface 6 — CI registration: **PASS**

Manifest hunks (`.github/ci/legacy-jobs.yml`):

```yaml
@@ -27140,6 +27140,7 @@ jobs:
       - "tests/test_prophet_plan_postmortem.py"
+      - "tests/test_prophet_r7_wave_a_plan_cards.py"
       - "tests/test_prophet_strategy_definition.py"
@@ -27255,6 +27256,8 @@ jobs:
       - name: Prophet B05 same-read contract (candidate state and runtime entry availability read the same B4 snapshot)
         run: python -m pytest tests/test_prophet_b4_same_read.py -q
+      - name: Prophet R7 Wave A plan-card record states (A1)
+        run: python -m pytest tests/test_prophet_r7_wave_a_plan_cards.py -q
       - name: Prophet B4 producer basis and disclosed freshness guards
```

- **Job identity**: `washout-turn-organ:` at l.26196; the next job key (`prophet-anticipation-intake:`) is at l.27264 — both hunks (l.27143, l.27259-27260) sit inside 26196–27263. The step runs under `washout-turn-organ`. ✓
- **Paths coverage**: the test opens `templates/_us_prophet_plan_cards.html.j2` (jinja loader), imports `templates/_prophet_card.html.j2` (template l.9; that file imports nothing further), and reads `templates/theme.css`. All three are declared in this job's `paths:` (verified in the dumped list: `_prophet_card.html.j2`, `_us_prophet_plan_cards.html.j2`, `theme.css`), plus the new test path itself. Remaining imports are stdlib + `jinja2`/`pytest` (external packages). Nothing opened or imported by the test is missing from `paths:`. The repo's own manifest validator agrees: command 3 (`test_ci_pack.py -k "exclusive or washout or narrow"`) → 7 passed.

## Surface 7 — Custody: **PASS**

`git diff --stat 526ce826..HEAD` names exactly the four files above (422 insertions, 0 deletions). Untouched, as required: `templates/_prophet_card.html.j2`, `templates/_us_board_cards.html.j2`, `templates/_prophet_setup_detail.html.j2`, `templates/dashboard.html.j2`, `engine/prophet_bridge.py`, the nav family (`_site_nav/_public_nav/_navlinks/navigation-refresh.css/nav_market.js/theme.js` — note `templates/theme.js` vs the edited `templates/theme.css` are distinct paths, and only `theme.css` is in the diff), and nothing under `.github/workflows/` (only `.github/ci/legacy-jobs.yml`, the manifest, is edited).

## RESULT

1. Record-state truth — **PASS** (guards proven at render level; engine mirror + `recorded_at` provenance verified; NOTE: day gate allows month-impossible days, same as the mandated screen-clock gate).
2. Copy — **PASS** against packet-quoted spec copy + test assertions; spec file itself unreachable (GAPS).
3. theme.css add-only — **PASS**; both `--line` blocks carry `--line-quiet`, no `prefers-color-scheme` variant exists; OQ8 rules scoped with fallback; NOTE: `.nowrap` currently unused (no collision, no behavior change).
4. Doctrine — **PASS** (zero edge-accent matches in the diff).
5. Test realism — **PASS** (both mutations caught, failing assertions quoted above).
6. CI registration — **PASS** (step + path under `washout-turn-organ`; all opened/imported paths declared).
7. Custody — **PASS** (exactly the four files; no protected path touched).

## EVIDENCE

- Diff hunks quoted in surfaces 1, 3, 6; `git diff --stat` quoted at top.
- Pytest tails + exit codes in the command table; failure-set diff vs base (`comm`): only-at-HEAD = ∅, only-at-BASE = the 2 mockups-marker skip artifacts.
- Mutation failure text quoted verbatim in surface 5.
- Render-level guard proofs: surface 1 (absent/int/dict/suffix-not-prefix/malformed-date/candidate-attached).
- Throwaway copy: `/tmp/r7a1copy` (byte-verified copy of this checkout's working tree, `.git` excluded; base state produced by restoring the four changed files from `git show 526ce826:path`).

## GAPS

- **Design spec unreachable**: `research/prophet_v4/r7_design/R7_DESIGN_SPEC_2026-10-21.md` is not tracked at BASE and does not exist on disk in this worktree, the primary checkout, or any reachable lane/g2 worktree; `git log --all` is blocked by a pre-existing corrupt worktree ref (`worktrees/contract-delta-base-cqkuuipv/HEAD`) in the shared object store, left untouched per read-only scope. Copy verification therefore rests on the packet's verbatim quoted copy table and the test file's byte-exact assertions — the two sources agree with the template everywhere they overlap.
- **No browser render performed**: the slice is browser-free by design (test docstring); doctrine checked at source/CSS level (grep evidence), not against rendered pixels.
- **Base-comparison method**: `git -C <copy> checkout` was replaced by byte-restoring the four changed files (the only tracked difference between the two revisions) inside a `.git`-less copy — a full clone fell back to pack transport over the 32 GiB object store and was killed. The restored tree is byte-equivalent to a base checkout of the sparse profile; the only observed side effect is the `needs_full_checkout` marker artifact documented above.

## DEVIATIONS

- Throwaway-copy construction as described in GAPS (clone → killed; working-tree copy + `git show` restore). Lane worktree untouched throughout; the copy is deleted after use.
- No other deviations: no edits to reviewed files, no push/PR/label/merge, no network, forbidden paths untouched.
