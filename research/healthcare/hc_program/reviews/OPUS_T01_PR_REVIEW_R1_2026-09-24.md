# OPUS T01 ADVERSARIAL REVIEW — Healthcare D1 / PR #7930 @ 604a3755c3ff1b3ed7bcf0d50e2716e5ee0b4f98

Scope: T01 only (`engine/fda_scarcity.py`, `engine/foresight_cascade.py` chip/tier seam,
`templates/foresight.html.j2:581`, `tests/test_foresight_cascade.py`). Collector lane
(`collectors/fda_shortages.py`, t02r/t02r2, generation suite) NOT reviewed. READ-ONLY: no repo
file touched. Probe file: `test_fda_supply_probes_t01r.py` (this directory), 7 RED + 1 GREEN PIN.

## VERDICT

**REJECT @604a3755** — 2 blockers (B), 2 majors (M), 4 minors (m).
The chip is genuinely display-only (tier/stage/entry are not moved by source status — verified,
GREEN PIN below), the bilingual seam is correct, and no banned substring reaches any visible
string. It is rejected on truthfulness: the production cold-cache path prints a Python `None` to
users in both languages, and a failed refresh over a good cache erases a retained current
shortage from the visible copy and flips the legacy band.

## GLM CLAIM ADJUDICATION

| Claim | Verdict | Evidence |
|---|---|---|
| GLM-B1 (`None` in visible copy) | **CONFIRMED (B)** | `engine/fda_scarcity.py:129-130`; rendered `FDA source unavailable — last qualified None, refresh failed` / `FDA来源不可用——上次合格为None，刷新失败`. Probe `test_t01r_b1_*` RED ×3. |
| GLM-B2 (enum name as visible EN copy) | **REFUTED** | `engine/fda_scarcity.py:36-42` define `_CURRENT_REPORTED = "CURRENT_REPORTED"` etc. as *dict keys*; `:117-125` `labels = {_CURRENT_REPORTED: ("FDA shortage: current ({current})", "FDA短缺：当前（{current}）"), ...}` and `:126 english, chinese = labels[status]`. The identifier's value reaches only `source_status` (permitted). Render table below shows no status name in any `label`/`label_zh`/`rationale`. No enum name is visible. |
| GLM-M1 (cache-absent tier test) | **CONFIRMED as a gate gap, DOWNGRADED to m** | `tests/test_foresight_cascade.py:682-701` (`test_fda_scarcity_none_on_missing_cache`) asserts only `v["source_status"] == "UNAVAILABLE"` — it never formats a chip and never reads a tier; the tier comparison at `:1336-1341` is `run("CURRENT_REPORTED")` vs `run("RESOLVED_REPORTED")`. So the law is NOT pinned for the UNAVAILABLE / NO_MATCHING_RECORDS axis. But the **code obeys the law**: `engine/foresight_cascade.py:430-435` formats a chip for every non-None scarcity row and `compute_fda_scarcity` returns a row per *configured* theme regardless of acquisition, so `_compute_tier` (`:59-74`) returns `P` for all seven statuses. No RED probe is possible; I supply the missing pin GREEN (`test_t01r_pin_tier_unchanged_when_the_source_is_unavailable`). Severity m (missing acceptance gate), not a defect. |
| GLM-M2 (no label abstraction) | **DOWNGRADED to m, subsumed** | Judged on the law, not style. The ad-hoc mutation at `:128-131` (`if status == _UNAVAILABLE: english_parts[0] = f"... {generation} ..."`) is the *mechanism* of B1; repairing B1 fixes the only wrong string it produces. No independent finding. |
| GLM-m1 (`NO_MATCHING_RECORDS` lacks generation suffix) | **CONFIRMED but generalised into M2** | The omission is not status-specific: `:132-134` appends the generation only `elif generation:`, so ANY status with an absent/unparseable generation silently drops it (see M2, which is the stronger, reachable form). As stated (no generation known → no suffix) it is correct behaviour in isolation; the defect is the *silence*. |

## SEVEN-STATUS RENDER TABLE (summarize_supply + format_theme_feed_chip, now=2026-09-23T12:00Z)

| source_status | label (EN) | label_zh | rationale (= title) | tone |
|---|---|---|---|---|
| CURRENT_REPORTED | `FDA shortage: current (1) · captured 0 d ago · source generation 2026-09-23` | `FDA短缺：当前（1） · 采集于0天前 · 来源生成日期2026-09-23` | The FDA reports a current shortage for this theme. | warn |
| RESOLVED_REPORTED | `FDA shortage: resolved (1) — supply status only · captured 0 d ago · source generation 2026-09-23` | `FDA短缺：已解决（1）——仅供给状态 · 采集于0天前 · 来源生成日期2026-09-23` | The FDA reports the shortage as resolved. | cool |
| DISCONTINUATION_REPORTED | `FDA: formulation discontinuation reported (1) · captured 0 d ago · source generation 2026-09-23` | `FDA：已报告制剂停产（1） · …` | The FDA reports a formulation discontinuation. | mute |
| MIXED_REPORTED | `FDA: mixed — current 1 / resolved 1 · captured 0 d ago · source generation 2026-09-23` | `FDA：混合——当前1／已解决1 · …` | The FDA reports both current and resolved shortages. | warn |
| UNCLASSIFIED | `FDA: observed, status unclassified (1) · captured 0 d ago · source generation 2026-09-23 · 1 record unclassified` | `FDA：已观察到，状态未分类（1） · … · 1条记录未分类` | The FDA observation is present but its status is not classified. | mute |
| NO_MATCHING_RECORDS | `FDA: no matching records · captured 0 d ago · source generation 2026-09-23` | `FDA：无匹配记录 · …` | No FDA records match this configured theme. | mute |
| UNAVAILABLE (cold cache) | `FDA source unavailable — last qualified None, refresh failed` | `FDA来源不可用——上次合格为None，刷新失败` | The FDA source is unavailable after a failed refresh. | mute |
| UNAVAILABLE (stale cache, 1 current row retained) | `FDA source unavailable — last qualified 2026-09-20, refresh failed · captured 2 d ago` | `FDA来源不可用——上次合格为2026-09-20，刷新失败 · 采集于2天前` | (same) | mute |

All seven statuses render distinct EN and ZH copy; the *cold* and *stale* UNAVAILABLE variants
differ only by the date token (see B2). Generator: `t01r_scratch/render7.py`.

## FINDINGS

### T01R-B1 — literal `None` in visible EN and ZH copy (BLOCKER)
`engine/fda_scarcity.py:128-131` (blocker line **130**):
```
    if status == _UNAVAILABLE:
        english_parts[0] = f"FDA source unavailable — last qualified {generation}, refresh failed"
        chinese_parts[0] = f"FDA来源不可用——上次合格为{generation}，刷新失败"
```
`generation = _generation(observation.get("source_generation"))` (`:190`) returns `None` whenever
the key is missing or unparseable (`:64-69`). The production cold-cache path builds exactly that
capture: `compute_fda_scarcity` `:270-272` `except Exception as error: capture = {"qualified": False, "failure_code": str(error)}`
— no `source_generation` at all. Rendered: `FDA source unavailable — last qualified None, refresh failed`.
Law: every visible string is authored copy; the chip must never leak a Python repr. Also mis-names
the field — the source *generation* is not a "last qualified" timestamp.
RED: `test_t01r_b1_unavailable_label_never_renders_a_python_none[capture0..2]`
`E AssertionError: T01R-B1: visible label renders the literal None: 'FDA source unavailable — last qualified None, refresh failed'`

### T01R-B2 — a failed refresh erases retained evidence (BLOCKER)
`engine/fda_scarcity.py:246-252` (`_observation_capture`) overwrites the *selected capture's own*
qualification with the *refresh* outcome:
```
    elif observation.get("failed_refresh") or last_refresh.get("qualified") is False:
        reason = str(last_refresh.get("failure_code") or "refresh failed")
    if reason is not None:
        capture["qualified"] = False
```
`summarize_supply:183-184` then short-circuits `if qualified is False: source_status = _UNAVAILABLE`
*before* looking at the rows it just counted. Measured on the production seam (`df.attrs["fda_observation"]`
with a qualified 2026-09-20 capture + a failed 2026-09-22 refresh, one `Current` row):
`band= NONE | status= UNAVAILABLE | n_active= 1 | label= FDA source unavailable — last qualified 2026-09-20, refresh failed`.
So the chip simultaneously reports `n_active == 1` and tells the user the source is unavailable;
the legacy band drops `SHORTAGE_ACTIVE → NONE`; tone drops `warn → mute`. A live FDA current
shortage disappears from the card because a *fetch* failed. This is the exact inverse of the D1 law
(`fresh acquisition ≠ fresh evidence` ⇒ failed acquisition ≠ absent evidence), collapses `failed`
into `stale` (the seven statuses must be distinct and truthful), and contradicts the collector
contract the frozen probes pin — `tests/test_fda_supply_probes.py:450-478` (R8-A27) deliberately
*retains* the stale-but-qualified capture and its generation, which T01 then hides.
RED: `test_t01r_b2_failed_refresh_keeps_the_retained_shortage_visible`
`E AssertionError: T01R-B2: the chip counts a current record but hides it: 'FDA source unavailable — last qualified 2026-09-20, refresh failed · captured 2 d ago'`
RED: `test_t01r_b2_failed_refresh_does_not_erase_the_legacy_band`
`E AssertionError: T01R-B2: a failed refresh erased the legacy band: 'NONE'` (`assert 'NONE' == 'SHORTAGE_ACTIVE'`)

### T01R-M1 — staleness is never adjudicated on the production path (MAJOR)
`engine/fda_scarcity.py:293`: `summary = summarize_supply(rows, capture=capture, now=now, max_capture_age=None)`.
With `max_capture_age=None`, `:193-196` forces `stale = None` for every theme, always. The visible
consumer therefore has no staleness verdict at all: a 90-day-old qualified capture renders
`FDA shortage: current (1) · captured 90 d ago · source generation …` with `tone="warn"` and
`freshness.stale=None`, indistinguishable in kind from a capture taken an hour ago. The parameter
exists and the frozen probes exercise it (`timedelta(days=2)`), but production never passes it.
Law: `stale` must be a distinct, decided state, not permanently unknown.
RED: `test_t01r_m1_production_path_adjudicates_staleness`
`E AssertionError: T01R-M1: the production path never adjudicates staleness (stale is None)` (`assert None is not None`)

### T01R-M2 — an unparseable source generation is dropped in silence, leaving only the fetch clock (MAJOR)
`engine/fda_scarcity.py:64-69` `_generation` returns `None` on any `ValueError`, and Python's
`date.fromisoformat` rejects ISO *datetime* forms (verified: `'2026-09-23T00:00:00+00:00'` → ValueError,
`'2026-09-23 00:00:00'` → ValueError). `:132-134` then appends the generation only `elif generation:`,
while `:135-138` appends `captured {N} d ago` unconditionally. Result for a qualified capture whose
generation is a datetime string: `FDA shortage: current (1) · captured 0 d ago` — the ONLY time token
in the visible label is the acquisition clock, `freshness.source_generation` is `None`, and
`source_generation_age_days` is `None`, with no disclosure anywhere. This is the D1 failure mode
verbatim ("labels must name the source generation, never the fetch/render clock"; "nulls printed,
not hidden"). The frozen probe R9-A07 (`tests/test_fda_supply_probes.py:223-252`) only covers the
*parseable* case, so this is a new failing input. GLM-m1 is the `NO_MATCHING_RECORDS` instance of it.
RED: `test_t01r_m2_unparseable_generation_is_disclosed_not_silently_dropped`
`E AssertionError: T01R-M2: generation dropped in silence, only the fetch clock survives: 'FDA shortage: current (1) · captured 0 d ago'`

### T01R-m1 — the ruling-mandated cache-absent tier gate is missing (minor; GLM-M1)
See adjudication table. Supplied GREEN PIN `test_t01r_pin_tier_unchanged_when_the_source_is_unavailable`
(passes at this head) compares CURRENT vs UNAVAILABLE vs NO_MATCHING_RECORDS on tier, stage and entry
and asserts the two null-ish chips still render *different* labels.

### T01R-m2 — a resolved+discontinued mixture hides the resolved count (minor)
`engine/fda_scarcity.py:191-192`: `elif counts["resolved"] and counts["discontinued"]: source_status = _DISCONTINUATION_REPORTED`.
Rendered for 1 resolved + 1 discontinued: `FDA: formulation discontinuation reported (1)` — the
resolved record is invisible (`counts` carries `resolved: 1`). Not an all-clear and not false, so m,
but it is evidence loss in a mixture and `_MIXED_REPORTED`'s own label template
(`current {current} / resolved {resolved}`) cannot express a discontinuation either.

### T01R-m3 — dead conditional and count-agnostic grammar (minor/nit)
`engine/fda_scarcity.py:137`: `english_parts.insert(1 if status == _UNAVAILABLE else 1, ...)` — both
arms are `1`; the conditional is dead and reads as an intended-but-unimplemented ordering rule.
`:308-312` rationale renders `regulator status: discontinuation reported (1 records)` for a single row
(the label helper pluralises correctly at `:141-146`; the rationale does not).

### T01R-m4 — the tooltip seam has no translation guard for the next feed (minor)
`templates/foresight.html.j2:581` `title="{{ tfs.rationale or '' }}"` is safe today only because
`format_theme_feed_chip:394-402` always *overwrites* `rationale` from an English-only constant map
keyed by status (it never reads `scarcity_row["rationale"]`). The module docstring `:8-9` advertises
`theme_feed_summary` as the generic seam for future feeds (Pink Sheet, LBNL); the first feed that
populates a localized rationale puts Chinese into a `title=` attribute, which is CI-forbidden.

## TEMPLATE / TITLE CHECK

- `templates/foresight.html.j2:581` is the ONLY visible consumer of the chip (grep across
  `templates/`, `scripts/`, `engine/`): it renders `t(tfs.label, tfs.label_zh)` (correct bilingual
  seam, both keys always populated by `_label`) and `title="{{ tfs.rationale or '' }}"`.
- **Can `title` ever carry Chinese at this head? NO.** `rationale` is assigned unconditionally from
  the English-only `rationales` dict in `format_theme_feed_chip` for all seven statuses; the
  row-level `rationale` built in `compute_fda_scarcity:307-315` is never read by the chip. The
  tooltip is therefore EN-only for ZH readers — the CI-mandated form, not a defect. Forward risk = m4.
- `details` (`compute_fda_scarcity:300-304`, contains raw `generic_name`) and
  `coverage.molecules_checked` are NOT fields of the chip and reach no template.

## BANNED SUBSTRING CHECK

Swept `label`, `label_zh` and `rationale` for all seven statuses plus the cold/stale UNAVAILABLE and
no-generation variants against `("glut", "tell", "all-clear", "catching up", "demand exceeds supply",
"supply constraint lifted")`: **zero hits** (`render7.py`, `"banned": []` on every row).
The `MOLECULE_THEME_MAP` keys `semaglutide`/`liraglutide` (`engine/fda_scarcity.py:24,26`) DO contain
`glut`, but they can only surface through `details` / `molecules_checked`, neither of which is in the
chip dict or in any template — so no visible string can carry `glut` via the map at this head. That
containment is currently incidental, not enforced; a future chip field carrying `details` would
break it silently.

## REPAIR SPEC (one executable sentence per confirmed finding)

1. **B1** — In `_label` (`engine/fda_scarcity.py:128-131` (blocker line **130**)), branch on `generation`: emit
   `FDA source unavailable — no qualified generation on file, refresh failed` /
   `FDA来源不可用——无合格来源生成日期，刷新失败` when `generation` is falsy, and keep the dated form
   otherwise, so no code path can interpolate `None`.
2. **B2** — Stop letting a failed *refresh* re-qualify a good *capture*: in `_observation_capture`
   (`:246-252`) leave `capture["qualified"]` untouched and carry the failure as a separate
   `refresh_failed` flag, and in `summarize_supply` (`:183-184`) reserve `_UNAVAILABLE` for the case where
   there is no qualified capture at all — a qualified-but-stale capture keeps its evidence-derived
   `source_status`, its legacy band and its counts, with the failed refresh disclosed as a suffix
   (`… · refresh failed 2026-09-22` / `… · 刷新失败 2026-09-22`).
3. **M1** — Pass a real budget from `compute_fda_scarcity:293`
   (`max_capture_age=timedelta(days=<configured>)`) so `freshness["stale"]` is a decided bool on the
   production path, and surface the true case in the label as a stale suffix.
4. **M2** — Make `_generation` (`:64-69`) accept ISO datetime input by falling back to
   `datetime.fromisoformat(text).date()`, and in `_label` append an explicit
   `source generation unknown` / `来源生成日期未知` whenever `generation` is falsy on a qualified
   capture, so the acquisition clock never stands alone as the label's only freshness token.
5. **m1** — Add the cache-absent tier/stage/entry comparison (body of
   `test_t01r_pin_tier_unchanged_when_the_source_is_unavailable`) to `tests/test_foresight_cascade.py`
   next to `:682`.
6. **m2** — Give a resolved+discontinued mixture its own label template naming both counts, or route
   it to `_MIXED_REPORTED` with a discontinuation-aware format string.
7. **m3** — Delete the dead conditional at `:137` and pluralise the rationale counts at `:308-312`.
8. **m4** — Wrap the tooltip as an English-only contract (assert in `format_theme_feed_chip` that
   `rationale` is ASCII, or add a `rationale_en` field the template reads) before a second feed lands.
