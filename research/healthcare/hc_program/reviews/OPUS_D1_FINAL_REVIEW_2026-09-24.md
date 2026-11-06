# OPUS D1 FINAL REVIEW — PR #7930 @ 28b986d4de696f0087ad760eabe95c09cdd695f1

MODE: READ_ONLY. No repo file was edited. Probes ran from the scratch dir.
Probe file: `.../scratchpad/review/test_fda_supply_probes_final.py` (1 GREEN pin + 3 RED findings).

## VERDICT

**REJECT @ 28b986d4** — 3 blockers (B), 1 major (M), 5 minor (m).

The collector half (T02) is sound: the sweep qualification, the `NO_SOURCE_GENERATION`
seam, the predecessor fence, the non-destructive failed refresh, the retention clock
and the drip receipt all behave as claimed and my end-to-end probe pins them GREEN.
The **consumer half (T01) is not truthful at the real seam**. All three blockers share
one root cause:

`engine/fda_scarcity.py:273-285 _observation_capture()` never emits a `qualified` key.
`summarize_supply()` reads `qualified = observation.get("qualified")` (`:177`), so on
EVERY production read path `qualified is None`:

* `:215 if qualified is False:` — the ONLY door to `_UNAVAILABLE` — is unreachable from
  `compute_fda_scarcity()` except via the bare-exception branch at `:307`. A torn pair
  and a never-collected cold start therefore fall through to `:217 elif not closed:` and
  render **"FDA: no matching records"** — a positive claim that the source WAS read.
* `:159 if capture_qualified is None:` fires on every chip, so a perfectly qualified
  observation is labelled **"capture time unknown"** two tokens after it printed
  **"captured 0 d ago"**, in EN and ZH, and `freshness.capture_qualified` is `null`
  for a capture that is known-qualified.

The frozen probes do not catch this because every T01 probe hand-builds a `capture`
dict containing `{"qualified": True|False}` and calls `summarize_supply` directly
(e.g. `tests/test_fda_supply_probes_t01r.py:44-54`, `:117-119`). Nothing in the merged
suites drives `compute_fda_scarcity()` off a real on-disk observation written by
`save_shortage_observation()`. Unit-pinned, seam-unpinned.

Baseline check (so these are NEW, not inherited): `git show origin/main:engine/fda_scarcity.py`
docstring + body — *"Missing cache → ALL entries are None (honest degradation; caller
surfaces as missing)"*, `if df is None or df.empty: return {t: None for t in themes_touched}`.
On main a cold start renders **no chip at all**. At this head it renders a false records claim.

## END-TO-END TRUTH TABLE (executed at 28b986d4)

collect_shortage_sweep → save_shortage_observation → read_shortage_observation →
compute_fda_scarcity → format_theme_feed_chip → _compute_tier, synthetic molecule
`zetamide` mapped to `synthetic_theme` (no real molecule names, no network, tmp_path only).

| # | step | label EN | label ZH | rationale | tone | source_status | tier |
|---|------|----------|----------|-----------|------|---------------|------|
| 1 | cold start, no parquet + no sidecar | `FDA: no matching records · capture time unknown` | `FDA：无匹配记录 · 采集时间未知` | `No FDA records match this configured theme.` | mute | `NO_MATCHING_RECORDS` **(false — nothing was read; main rendered no chip)** | P |
| 2 | qualified sweep, 1 `Current` row, gen 2026-09-23 | `FDA shortage: current (1) · captured 0 d ago · source generation 2026-09-23 · capture time unknown` | `FDA短缺：当前（1） · 采集于0天前 · 来源生成日期2026-09-23 · 采集时间未知` | `The FDA reports a current shortage for this theme.` | warn | `CURRENT_REPORTED` | P |
| 3 | failed refresh `FIRST_PAGE_OUTAGE` over #2 | `FDA shortage: current (1) · captured 0 d ago · source generation 2026-09-23 · refresh failed 2026-09-24 · capture time unknown` | `FDA短缺：当前（1） · 采集于0天前 · 来源生成日期2026-09-23 · 刷新失败 2026-09-24 · 采集时间未知` | same | warn | `CURRENT_REPORTED` (retained evidence survives — correct) | P |
| 4 | generation-less page over #3 | identical to #3 with `refresh failed 2026-09-24` | identical to #3 | same | warn | `CURRENT_REPORTED`; sweep refused `qualified=False / NO_SOURCE_GENERATION`, `promoted=False` — correct | P |
| 5 | torn pair (parquet digest ≠ sidecar) | `FDA: no matching records · refresh failed 2026-09-24 · capture time unknown` | `FDA：无匹配记录 · 刷新失败 2026-09-24 · 采集时间未知` | `No FDA records match this configured theme.` | mute | `NO_MATCHING_RECORDS` **(false — `read_shortage_observation` reports `inconsistent=True, rows=None`)** | P |

Clean across all five: no literal `None`, no `nan`, no banned substring
(`glut` / `tell` / `all-clear` / `catching up` / `demand exceeds supply` /
`supply constraint lifted`), EN ≠ ZH, tooltip ASCII-only. Drip receipt at step 5:
`fda_shortages: observation qualified=False failure_code=NO_SOURCE_GENERATION source_generation=unknown last_refresh=… legacy=False inconsistent=True` — the collector receipt tells the truth the chip does not.

## GLM CLAIM ADJUDICATION (lane reviewer @ e9f70840)

* **(a) t02r2 probe conflict — RESOLVED at 28b986d4.** The amendment is present; the
  file is green; the contradiction with the round-4 frozen probe is gone. See SEAT
  AMENDMENT VERDICTS below (LAWFUL, with m1).
* **(b) "no dark/light visual evidence for the template change" — DOES NOT APPLY.**
  The theme law's material-UI evidence matrix governs *material* UI packets. This diff
  contains **zero CSS** (`git diff --stat`: no `.css`, no `templates/*.css`), no new
  component, no runtime stylesheet, no JS. The change is one expression inside the
  pre-existing `fx-chip feed-{{ tone }}` span (`templates/foresight.html.j2:581`),
  swapping `{{ tfs.label }}` for `{{ t(tfs.label, tfs.label_zh) }}` — the template's own
  bilingual macro (`:2-3`), used by every other chip on the page. Hierarchy, material
  depth, semantic colour (`feed-warn/cool/mute`), spacing, type scale and responsive
  composition are untouched in BOTH themes. The only rendered delta is that the ZH
  locale now shows Chinese where it previously showed English — an EN/ZH **parity fix**,
  which is the very axis the law protects. Demanding a dark/light art-direction packet
  here would be evidence theatre. (Proportionate, non-blocking ask: one 390px ZH glance
  at the chip row, since the ZH string is longer than the EN one it replaces.)
* **(c) commit hygiene (three identically named commits) — COSMETIC, NOTHING HIDES.**
  `14a26e7cd6d` / `fe470bd33ae` / `e9f70840008` all carry the same subject; measured,
  they touch **only** `tests/test_fda_shortages_generation.py`
  (`git diff --stat 3e399bed77f e9f70840008` = 1 file, +29/-2). No source file, no CI
  file, no template. Squash-merge erases the history anyway. Not a finding.

## SEAT AMENDMENT VERDICTS

**t02r2 `test_t02r2_capture_without_a_source_generation_cannot_hide_an_absence` — LAWFUL.**
The original probe's *precondition* (`first = _t02r2_sweep(None, both, …)`) asserted the
DEFECT state: that a page without `meta.last_updated` still qualifies and promotes. Rulings
R-T02R3-06 / R-T02R4-02 made that sweep unqualified at the public seam, so the precondition
became unsatisfiable; a probe may not freeze a defect as its entry condition. The amended
test pins the intent by a **strictly stronger** mechanism — `second["qualified"] is False`,
`failure_code == "NO_SOURCE_GENERATION"`, `outcome["promoted"] is False`, and the sidecar's
`last_refresh.failure_code == "NO_SOURCE_GENERATION"` — because a sweep that can never
promote can never stamp an absence. Intent preserved. See m1 for the residue.

**t01r M1 (production staleness budget) removal — LAWFUL.**
`compute_fda_scarcity` calls `summarize_supply(..., max_capture_age=None)`
(`engine/fda_scarcity.py:328`) by design: R-T01-12 forbids inventing an age limit the
source does not publish. A probe demanding a production staleness budget would have forced
exactly that invented constant, and the D1 law's requirement is disclosure, not verdict —
which the label satisfies by printing `captured N d ago` + `source generation YYYY-MM-DD`,
with `source_generation_age_days` in the freshness contract. The removal deleted no truth
guarantee. Residue = m3.

## FINDINGS

### D1F-B1 (blocker) — a torn observation renders as a claim about matching records
`engine/fda_scarcity.py:273-285` (`_observation_capture` sets only `failure_code`, never
`qualified`) → `:177` → `:215` unreachable → `:217`.
Failing input: qualified observation written, then the parquet corrupted under a valid
sidecar. `read_shortage_observation` → `inconsistent=True, rows=None`.
Wrong output: `source_status=NO_MATCHING_RECORDS`, label `FDA: no matching records · capture
time unknown`, rationale `No FDA records match this configured theme.`, tone `mute`.
Law broken: absence of a readable observation is not evidence of absence; the module's own
`_UNAVAILABLE` state exists for exactly this, and `tests/test_fda_supply_probes_t01r.py:160`
ratifies that UNAVAILABLE and NO_MATCHING_RECORDS must carry *different* labels.
RED probe: `test_d1f_b1_torn_pair_is_reported_unavailable_not_no_matching_records`.

### D1F-B2 (blocker) — a never-collected source renders as "no matching records"
Same lines. Failing input: no parquet, no sidecar (first run, or any host where
`data/fda/` is absent — including a sparse render tree).
Wrong output: the same false records claim, tone `mute`, tier `P`.
Regression vs baseline: `origin/main` returned `{theme: None}` → no chip, tier W.
Law broken: nulls are printed, never dressed as an observation. The collector's own
receipt for this state says `qualified=False … source_generation=unknown`
(`tests/test_fda_shortages_generation.py:484-487`), so the truth exists and the consumer drops it.
RED probe: `test_d1f_b2_cold_start_is_not_rendered_as_no_matching_records`.

### D1F-B3 (blocker) — every qualified chip is labelled "capture time unknown"
`collectors/fda_shortages.py` writes `selected_capture` = the sweep capture, which has no
`qualified` key; `engine/fda_scarcity.py:177` reads `None`; `:159` appends
`capture time unknown` / `采集时间未知`.
Failing input: the plain happy path (step 2 of the truth table) — i.e. every nightly render.
Wrong output: `FDA shortage: current (1) · captured 0 d ago · source generation 2026-09-23 ·
capture time unknown` (and the ZH mirror), plus `freshness.capture_qualified = null` for a
capture that is known and qualified.
Law broken: the chip contradicts itself in visible copy, and the published freshness contract
reports "unknown" for a known state — a consumer cannot distinguish qualified from unknown.
RED probe: `test_d1f_b3_qualified_capture_is_not_labelled_capture_time_unknown`.

### D1F-M1 (major) — the exclusive job's scope omits the template its own suite renders
`.github/ci/legacy-jobs.yml` `healthcare-fda-supply` `paths:` lists 30 entries and **not**
`templates/foresight.html.j2`, while its sole-owned suite renders that template in three
tests (`tests/test_foresight_cascade.py:806`, `:921`, `:1374`, including
`test_rendered_html_shows_zh_chip_and_no_banned_words`, the only test of the T01 template
change). Measured: **no job in the manifest declares `templates/foresight.html.j2`**
(`grep -n "templates/foresight.html.j2" .github/ci/legacy-jobs.yml` → no match). At the
exclusive tier declared paths REPLACE inference and the import-closure walker only follows
Python imports, so a revert of `t(tfs.label, tfs.label_zh)` → `tfs.label` triggers ZERO
gate:code runs — precisely the "silent false green" the tier's own comment warns about
(`scripts/run_ci_pack.py:1457-1462`). Repair: add `templates/foresight.html.j2` to `paths:`.

### m1 — the amended t02r2 assertion is now tautological
`tests/test_fda_supply_probes_t02r2.py:288-291`: `marks["T02R2-B"] is None or
marks["T02R2-B"] != marks["T02R2-A"]`. Under the amended fixture the second sweep can
never promote, so B's mark is always `None` and the first disjunct always holds. The
load-bearing pins are the four new asserts; the `marks` assertion carries no signal.

### m2 — the drip receipt line has no test
No run suite imports `scripts.build_foresight` (measured: only a prose mention at
`tests/test_fda_supply_probes_t02r2.py:73`), yet `scripts/build_foresight.py` is in the
job's `paths:`. The job triggers on drip edits and proves nothing about them. The line
itself is safe — `log.info(format_observation_receipt(read_shortage_observation(...)))`
sits inside the pre-existing `try/except Exception` (`scripts/build_foresight.py:108-119`),
so no read-path failure can raise into the nightly build; verified by reading the diff.

### m3 — `freshness.stale` is permanently null in production
`engine/fda_scarcity.py:328` hardwires `max_capture_age=None`, so `stale` is `None` on
every published chip. Lawful under R-T01-12, but it is a dead field in a shipped contract;
document it as intentionally inert or drop it.

### m4 — the chip label moved from autoescaped to `|safe`
`templates/foresight.html.j2:2-3` (`macro t`) emits both spans with `|safe`. The label is
engine-composed from fixed strings, integer counts and an ISO-validated generation
(`_generation()` at `engine/fda_scarcity.py:70-79` returns `None` for anything unparseable),
so nothing external reaches the output today. It is a standing constraint on future label content.

### m5 — tier P for a theme whose source was never read
`_compute_tier` (unchanged from main) returns `P` whenever `theme_feed_summary is not None`,
and `format_theme_feed_chip` never returns `None`. Tier invariance across supply states is a
ratified ruling (`tests/test_fda_supply_probes_t01r.py:155-159`), so this is not a finding in
itself — but at cold start it promotes a theme W→P versus main on the strength of a chip that
says nothing. It resolves automatically once D1F-B2 is repaired.

## CI CLOSURE (measured, not assumed)

* `git diff --numstat origin/main...28b986d4 -- .github/ci/legacy-jobs.yml` → `51  0  .github/ci/legacy-jobs.yml`.
  One hunk, entirely the new `healthcare-fda-supply` block. **Hunks outside the job block: 0.**
* `if: ${{ false }}` is the manifest-required `DISABLED_IF` (`scripts/run_ci_pack.py:1387-1389`);
  19 sibling jobs carry it. Not a defect.
* `scope: exclusive` present; `paths:` non-empty (30 entries); registered in
  `tests/test_ci_pack.py:3539 CURATED_EXCLUSIVE`.
* Every test named in the two `run:` lines appears in `paths:` (7/7, checked by eye against the block).
* Import closure, measured: `scripts.run_ci_pack.curated_exclusive_closure_findings(...)` returns
  **no entry for `healthcare-fda-supply`** → zero uncovered Python closure paths. The seven suites'
  direct imports (grep-measured) are `collectors.fda_shortages`, `engine.fda_scarcity`,
  `engine.foresight_cascade`, `engine.foresight_score`, `engine.foresight_health`, `lib.config`,
  plus third-party (`pandas`, `numpy`, `jinja2`, `pytest`) — all declared or external.
  **No suite imports `scripts.build_foresight`** (m2).
* The closure walker does not see non-Python reads → D1F-M1 (template omitted).

## POLICY INVARIANTS

* No ranking / entry / sizing / trading change: `engine/foresight_cascade.py` is **byte-identical
  to `origin/main`** at this head (`git diff origin/main 28b986d4 -- engine/foresight_cascade.py`
  → empty), so `_compute_tier`, stage and entry logic are untouched by this PR.
  `tests/test_fda_supply_probes_t01r.py:156-158` asserts `stage` and `entry` equality across
  CURRENT / UNAVAILABLE / NO_MATCHING_RECORDS.
* No `data/` or `site/` bytes: `git diff --name-only origin/main...28b986d4` → 13 files, none
  under `data/` or `site/`.
* No protected research made public; no new network call outside the existing keyless drip.
* Display-only contract intact: the chip feeds `theme_feed_summary` only.

## REPAIR SPEC

1. **B1+B2+B3 (one repair).** Make `_observation_capture` (`engine/fda_scarcity.py:273`) emit an
   explicit `qualified`: `True` when the selected capture exists, is not `inconsistent`, is not
   `legacy`, and carries a non-empty `source_generation`; `False` otherwise (torn pair, legacy
   cache, no sidecar, no parquet, exception). Then:
   - torn pair and cold start reach `:215` → `_UNAVAILABLE` → `FDA source unavailable — no
     qualified generation on file, refresh failed` (already authored, already probe-covered);
   - the happy path stops appending `capture time unknown` (`:159`) and publishes
     `freshness.capture_qualified = True`.
   Keep `:159` for the genuinely-unknown case (legacy cache).
2. **B2 wording.** Confirm the cold-start label reads as *no observation*, not *refresh failed*,
   since nothing was attempted — the `_UNAVAILABLE` branch at `:143-147` currently hardcodes
   `refresh failed`. Either add a no-attempt variant or state the ruling.
3. **M1.** Add `templates/foresight.html.j2` to the `healthcare-fda-supply` `paths:` block.
4. **m1..m5.** Records-level; m1 and m2 are worth one line each in the handoff.
5. Adopt `test_fda_supply_probes_final.py` into `tests/` once B1–B3 are repaired: all four
   probes must then be green, and `test_final_end_to_end_truth_path` is the regression guard
   for the seam nothing else covers.
