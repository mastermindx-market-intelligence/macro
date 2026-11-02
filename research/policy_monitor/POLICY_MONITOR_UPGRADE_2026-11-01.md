# Policy Monitor upgrade — Macro
Recorded: 2026-11-01 America/Chicago
Operation: policy-monitor-upgrade-20261101-sol-001
Owning repository: mastermindx-market-intelligence/macro
Task-tree path: research/policy_monitor/POLICY_MONITOR_UPGRADE_2026-11-01.md
Protected procedure: mastermindx-market-intelligence/Mastermind@19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec, Sol skillpack v1 / 1.0.1 / bootstrap 1.
Source baseline: 9af0a33eb38b08d902c3e593cb0e276d3f0d6a18
Workstream: NONE verified. The Agent OS workstream inventory has no Policy Monitor record. WS-MACRO-CONTEXT-INDEX is unrelated governed retrieval. Do not invent a workstream or copy task status into Agent OS.
Current assignment: Chairman asks to substantially revamp and upgrade the Policy Monitor in macro.html, both design and advanced robustness. Sol is accountable for this new bounded source operation. No predecessor source writer is taken over.

## Outcome and DONE_WHEN
An analyst can open the existing Policy Monitor card, understand the supported policy/repricing conditions and evidence limitations at a glance, inspect a properly labelled market rate path and separately comparable Fed projections, review dated policy developments and transmission conditions, and inspect evidence without ambiguous stance or fabricated certainty. Both themes and languages work on desktop and mobile. The existing macro page and stocks sibling retain their contracts.

Implementation is complete only with a working integrated candidate, discriminating tests, actual browser evidence, independent non-author source/visual review, required hosted CI, normal independent release and served-path proof. A plan, test count, open draft, green CI or source review alone is not production acceptance. No self-approval or manual self-merge.

## Current facts and architecture boundary
- macro.html is generated from templates/dashboard.html.j2 (1.4MB). Policy face is #sx-policy-v2; dialog is #dlg-policy; inner consumer anchor is #dlg-policy-lever-card.
- Existing data owners: scripts/build_policy_lever.py -> site/policy_lever.json; engine/fed_path.py; engine/fed_stance.py; existing latest view model; flip confirmation. Preserve those authorities. A stateless presentation normalizer is permitted; a new producer, store, queue, model, fetch/cache owner or scheduler is not.
- The current modal mixes absolute Fed stance, relative market-vs-Fed pricing and missing guidance. It uses default QUIET for absent state, literal light-invisible white chart axis colors, equally spaced 0/1/3/6/12m horizons, and places every current-year Fed dot in the m6 slot. n_30d uses truthiness so valid zero becomes an em dash. Missing arming defaults to Quiet. A policy alert about Russia sanctions is labelled alongside 'speeches'.
- Current policy snapshot at baseline is dated 2026-10-30. It has n_7d=0/n_30d=12, last policy alert 2026-10-17, and narrative copy dated 2026-07-18 with copy_stale=true. These are recorded source observations, not verified present-day market facts.
- Prior Policy Watch #8048 and #8081 concern the separate policy_watch page, official-event feed and a held Paper design operation. They are references only; this task does not reopen, replace or mutate them.
- Open dashboard PR #7626 changes tablet shared styles, not these policy sections. #7080 concerns AI Brief refresh. Preserve unrelated modal, navigation, AI Brief, risk, Fed and shared-shell code.
- DNR:KILL-POLICY-TIMING-PREDICTOR forbids administration timing/intent forecasting. DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION preserves the current main dashboard composition.

## Frozen product and design packet
Follow docs/DESIGN_DOCTRINE.md and research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md at the Macro baseline. Retain the established dashboard archetype and dialog primitive. Compose canonical panel, section, table, details, badge and button patterns. Tokens come from templates/theme.css. No parallel palette, new font, decorative colored container edge, heavy colored panel tint, or opaque runtime stylesheet.

### Information order
1. Sticky, properly named dialog header with title, concise context, close control and a snapshot date. One controlled scroll body. No stacked generic warnings.
2. An assessment band that separates the existing conditions state from evidence condition. State UNKNOWN is explicit. Never rename ARMED as observed market repricing unless the data actually proves it. Use short supported summary and 'What to watch' language; no trade or timing advice.
3. Rates as the main analytical panel: market path with visible axes, percent units, horizon labels, legend and an equivalent accessible values table. A compact supporting rail shows source-qualified current rate, supported market horizon and Fed comparison. The chart can retain valid partial observations; missing points are gaps and never zero. Time geometry must reflect 0/1/3/6/12m spacing or explicitly use categorical horizons; do not misleadingly pretend equal spacing is elapsed time.
4. Distinct stance and guidance fields. Unknown guidance is 'Guidance unavailable', never 'Hawkish — unknown'. Market below a Fed projection is a relative comparison, not absolute dovish policy. No literal number-of-hikes assertion from an approximate rate-change equivalent.
5. Policy developments/recorded activity, with counts labelled for what the producer actually collects. Separate last alert from Fed communication. Preserve observed zero and distinguish incomplete/unknown coverage. Do not invent event-source links or a complete event feed when the payload only provides a last alert.
6. Transmission watch rows: asset, observed setup state or unavailable, dated explanatory hypothesis, stale-copy warning next to old narrative, and relevant existing context. Keep observed technical state separate from geopolitical inference. Unknown arming must not become Quiet; clamp valid gauge geometry and reject malformed values.
7. Existing repricing/flip/calendar context where present, with missing vs empty distinctions and stale/reference-date treatment. No stale election countdown presented as a live clock. No claim of 'no active channels' when the field is absent.
8. Sources/methodology disclosure with per-input source/date/basis/quality, real source URLs only when present/validated, and one concise contextual boundary. Do not hide a material limitation only inside this disclosure.

Use anchored sections or concise progressive disclosures if necessary; avoid tabbing away the essential rates/assessment. The summary and primary chart should fit a useful desktop first viewport. On narrow screens stack the rail below the chart, preserve close control and all essential content, and prevent page overflow.

### DARK TREATMENT
Graphite material using existing panel/panel2, calm luminance separation and hairlines. High-contrast neutral titles/numerals; restrained blue for interaction/series and labelled amber for uncertainty. No neon purple chart or glow as ornament. Subordinate evidence and details without unreadable microcopy.

### LIGHT TREATMENT
Cool canvas, clean white panel, neutral secondary surfaces, crisp hairlines and modest existing shadow. Axis labels and muted text use text-grade tokens, never translucent white. Use material/shadow distinction deliberately instead of inverting dark fill values. Status, hierarchy and semantics match dark.

### Bilingual and accessibility
EN/ZH labels and null states must have semantic parity; no untranslated new hard-coded English in Chinese mode. Retain full keyboard focus rings. Name the dialog with aria-labelledby, use real headings, announce meaningful status without noisy updates, provide chart title/description/text table, preserve Escape/backdrop/close and trigger focus restoration through the existing modal controller. Repeated opens must not duplicate instances/listeners. Check reduced motion, zoom and 390px width.

## Robustness contract
A small pure presentation normalization layer may project existing payloads into safe display values and typed availability. It must never mutate raw payloads or alter scoring. Use strict mapping/sequence/finite-number/date validation; reject bool-as-number, NaN, infinity, malformed nested values and unsafe URLs. Keep zero valid. Preserve unknowns. Bound array/text sizes at the display boundary where needed. Let one bad section degrade independently.

Rate comparisons require compatible measure, unit, horizon and source dates. Preserve qualified producer gap semantics and limitations. If a reliable same-basis comparison cannot be established, show observations separately and state comparison unavailable; do not invent a precise spread. Year-end dots may be placed at actual date geometry only when justified, otherwise place them in a separate year-labelled table. No hardcoded year or m6 placement. Never derive publication recency from a newer unrelated snapshot. Use existing source freshness owner where available; any local age calculation is display-only and explicitly references its evaluation date.

The generated-page architecture does not justify a new refresh subsystem. If no existing monitor refresh owner exists, retain server rendering and tell the truth about snapshot age. Do not add a dummy Refresh control or make unsupported live claims.

## Ordered task tree
| ID | Parent/dependencies | Editorial label | Capability / acceptance | Intended lane / review |
|---|---|---|---|---|
| P1 | none | accepted | Recover target, producer boundaries, prior work and defects above at immutable baseline. | Sol reasoning; source facts checked |
| P2 | P1 | ready | Implement safe display normalization and production wiring over existing inputs. Discriminating malformed/missing/zero/date/comparison tests pass; no scoring/source expansion. | Admitted C2 Fabric builder; independent source review |
| P3 | P2 | ready | Replace only policy face/dialog presentation with frozen composition and governed stylesheet/fragment. Functional real template render, both themes/languages and mobile. | Same sole builder; independent visual review |
| P4 | P2,P3 | proposed | Real browser proof of open/close/reopen, keyboard, chart table, navigation/disclosures, missing/stale/malformed cases; focused existing regressions. | Builder proves; independent reviewer challenges |
| P5 | P4 | proposed | Integrate exact candidate, resolve independent findings, hosted CI and normal independent release; verify served macro.html path. | Sol acceptance/release coordination; non-author approval required |

## Source scope
Expected changed paths: templates/dashboard.html.j2 only policy face/dialog and narrow includes; a scoped policy template/stylesheet; a pure display helper in lib/ or engine/ if needed; narrow scripts/build_site.py view-model wiring; focused existing/new policy UI tests; governed visual-evidence receipt and images; this plan.
Do not edit policy scoring, policy_watch producers/UI, RIC, other page composition, auth, providers, CI policy/budgets, deployment settings or generated site artifacts by hand. Honor repo-specific test enrollment/build rules. If a mandatory gate needs a protected out-of-scope path, return the exact need rather than waive/rename it.

## Acceptance falsifiers
- Rising market path and lower same-horizon market-vs-Fed projection render coherently.
- All-null, partial, invalid types, nonfinite values, valid zero, stale dates, unknown guidance and missing arming never crash or fabricate a calm/current/zero claim.
- Year rollover and non-midyear snapshots do not misplace Fed dots.
- Source gap basis ambiguity suppresses the unsupported comparison, while valid observations remain useful.
- Recorded policy alert counts are never relabelled Fed speeches without evidence.
- Both themes x EN/ZH x desktop 1440/mobile 390 are visibly reviewed; no colored edge, clipped value, invisible label or duplicate id.
- Actual dashboard template and existing dialog controller are exercised, not only a mockup.
- No source/production acceptance claim without its actual receipt.

## Routing and reserved decisions
This is a consequential single-domain product capability with frozen authority/data boundaries. Direct CEO -> C2 paid Fabric builder is the shortest capable route; Sol retains product semantics, independent-result adjudication and final acceptance. WHY NOT FABLE: implementation is bounded and checkable; no new cross-system architecture is needed. Native consultation is limited to independent product judgment, not implementation labor. Fabric chooses eligible provider/host and conserves this original operation root. Record actual START/result/acceptance separately; Executive read is currently backend_unavailable and is not a requirement for independent source work on this admitted attended adapter.

## Evidence
Initial source readback: this file's Git commit is the task-tree revision; later evidence must cite exact implementation/review revisions and browser artifacts. No construction, tests, worker START, deployment or acceptance is claimed by this initial plan.

## Revision R2 — existing-producer integrity (2026-11-01 America/Chicago)
Previous task-tree revision: fdbcd947556dc768d5428ebdfe8cfeb08e86d11d. This revision preserves the P2/P3 presentation assignment and extends the existing producer boundary in response to reproduced defects. It does not change policy scoring, introduce a new producer, or retarget an active source writer.

Principal source probe against scripts/build_policy_lever.py at baseline reproduced: a valid JSON array raises AttributeError; wholly malformed JSON returns numeric zero counts; a future-dated record enters both observed windows and becomes the last event. These are defects in the source aggregates that a renderer cannot repair reliably. Empty readable files and valid old records must remain distinguishable from an unusable source, without claiming complete feed coverage.

| ID | Parent/dependencies | Editorial label | Capability / acceptance | Intended lane / review |
|---|---|---|---|---|
| P2.T1 | P1 | ready | Repair the existing jawboning reader: strict object/timestamp/text validation, one evaluation instant, future exclusion, eligible last event, independent rejection diagnostics and honest unavailable counts. Preserve existing output keys and recorded-zero behavior where justified. | Separate admitted C2 Fabric producer writer; independent source review |
| P2.T2 | P2.T1 | ready | Give the existing calendar structured event/evaluation dates and upcoming/today/past semantics; add genuine computation and component timestamps without relabelling source age. | Same producer writer; deterministic date tests |
| P4.T1 | P2,P3,P2.T1,P2.T2 | proposed | Integrate the producer and presentation branches only after both writer effects are reconciled; make the monitor consume source-quality and date metadata; run adversarial records through the real generated-page consumer. | Sole authorized integration writer; independent exact-head review |

### Bounded producer source scope
scripts/build_policy_lever.py, its directly affected tests (primarily tests/test_policy_lever.py), and this same task tree only. Read all existing consumers before changing optional/null behavior. Do not touch the active presentation branch, templates, build_site, the new presentation normalizer, policy scoring/thresholds, feed collection/writing, generated site output, runtime, CI policy, auth or unrelated source.

Implementation must reject valid non-object JSON before .get; reject unusable timestamp types/values; use the established UTC convention for naive source timestamps; count only records within a window and <= the single evaluation instant; select the last eligible observed event; safely bound display summaries to strings; distinguish missing/unreadable, empty-readable, wholly unusable, and partially usable files through additive quality metadata. Diagnostics classify malformed JSON, invalid structure, invalid timestamp, future records and valid records. Read success does not prove collection completeness. Future-only/all-invalid input must not become a confident zero. Valid older records may support zero recorded activity with coverage explicitly unknown.

Preserve top-level as_of as the existing market-input date. Add a separate actual computed/evaluated timestamp; do not claim it is feed freshness. Calendar must carry 2026-11-03 as an event date and evaluated date plus event state. Retain compatibility fields where reasonable but never output perpetual live zero-days after the event as the authoritative display. Do not change the frozen PS-R9 scoring policy.

### Custody and integration
Presentation branch claude/policy-monitor-upgrade-20261101 remains exclusively assigned to the original UI builder. Producer branch claude/policy-monitor-integrity-20261101 is isolated from the same common plan revision and has a distinct sole writer. The source paths are disjoint except for plan evidence, which will be deliberately consolidated by the later integration writer. Producer author commits and pushes this branch and returns exact commit/diff/test receipts; no second PR, no merge, no approval, no release. The original single presentation PR remains the final carrier if one is created. No result/checkpoint alone transfers or releases source custody.

### Required falsifiers
- JSON [], null, strings and numeric scalars cannot crash the producer.
- Wrong-type, missing, invalid, naive and offset timestamps have explicit deterministic handling.
- All malformed or all invalid-time inputs produce unavailable counts; future alerts are excluded from counts and last observed event.
- Valid older data plus a future record yields zero in the applicable recent window and the older last observed event, with partial-source qualification.
- Empty readable source remains distinct from absent/unreadable and wholly invalid source; no unsupported complete-coverage claim.
- Last-event summaries with malformed nested types cannot crash or inject raw markup.
- Calendar before/on/after 2026-11-03 has deterministic correct state; evaluation date is distinct from old semis source date.
- Existing complete, partial-basket, stale-copy, arming and PS-R9 state regressions retain their current semantics.

R2 is a source-bound extension for P2.T1/P2.T2 and P4.T1; P1 acceptance and P2/P3 design semantics are preserved. No worker START, implementation completion, independent acceptance or release is claimed by this revision.

## Revision R3 — P2.T1/P2.T2 producer implementation (2026-11-01 America/Chicago)

Producer branch: `claude/policy-monitor-integrity-20261101`. Implementation commit: `a7761c6aa11`. Base of this revision: `3fc5105db74beef4e04069bf6d4970981e72b065` (the R2 plan revision). Common source baseline unchanged: `9af0a33eb38b08d902c3e593cb0e276d3f0d6a18`.
Changed paths: `scripts/build_policy_lever.py`, `tests/test_policy_lever.py`, and this plan. No template, no `scripts/build_site.py`, no normalizer, no generated output, no feed collection, no scoring threshold, no auth, no CI policy or budget was touched. The presentation branch `claude/policy-monitor-upgrade-20261101` was not read-modified-pushed and remains exclusively assigned to its own writer.

### What was implemented

P2.T1 — the existing jawboning reader (`scripts/build_policy_lever.py::_compute_jawboning`):
- Strict per-record validation. A line must decode to a JSON **object**. JSON scalars, arrays and null are rejected as `invalid_structure` and never reach `.get`.
- Strict timestamp validation. `published` then `generated_at`, string only. A wrong type, a missing field and an unparseable string are classified and rejected; they never raise. Naive source timestamps keep the established UTC convention; offset timestamps are converted to UTC before any comparison.
- **One evaluation instant** for the whole build (`_utc_now()`, threaded through `now=`). Both windows are exactly `[cutoff, evaluation]` on both ends. A record is observed only when `published <= evaluation`, so a future-dated record no longer enters either window and no longer becomes the last observed event.
- Honest counts. Absent, unreadable, wholly unusable and all-future sources expose **unavailable counts** (`None`), not a confident zero. A readable empty file still reports 0 recorded events.
- Source-quality metadata: `source_status` (`missing` / `unreadable` / `empty` / `unusable` / `partial` / `usable`), `coverage` (always `"unknown"`), and `diagnostics` classifying malformed JSON, invalid structure, invalid timestamp (with missing / wrong_type / unparseable sub-reasons), future records and eligible observed records.
- Display copy is string-typed and bounded to 140 chars. A list / dict / number summary is rejected rather than sliced or injected; bilingual `banner_title`/`summary` and `banner_title_zh`/`summary_zh` behaviour is preserved for valid input.

P2.T2 — the existing calendar (`_compute_calendar`): the event is dated. `event_date` `2026-11-03`, `evaluation_date`, `evaluated_at`, and an explicit `event_state` of `upcoming` / `today` / `past`. After the event there is no permanent live zero-day countdown: `days_to_midterm` becomes `null` and `days_since_midterm` carries the elapsed days; the legacy key stays present for consumers that key on it.

P2.T2 — genuine timestamps: `computed_at` (top level and `favored_complex`) and `evaluated_at` (`jawboning`, `calendar`) are UTC generation/evaluation instants, distinct from evidence time. Top-level `as_of` keeps its price-date meaning; `as_of_basis` records whether it is the price date or the build-date fallback.

Unchanged and asserted by test: the frozen PS-R9 scoring rule, the `-15%` drawdown threshold, the technical-arming owner, the stale-copy rules, source collection, and every existing output key for valid input.

### Defect receipts — same fixture, same injected instant (2026-11-01T12:00:00Z)

Baseline read from a detached worktree at `3fc5105db74`; this branch from `a7761c6aa11`. Both were given the identical fixture file and the identical evaluation instant.

| Fixture | Baseline `3fc5105db74` | This branch `a7761c6aa11` |
|---|---|---|
| mixed: valid + future + JSON array + garbage + wrong-type ts + no ts + naive ts | `AttributeError: 'list' object has no attribute 'get'` | `n_7d=1, n_30d=2`, last = the valid record, `source_status=partial`, `_skipped_lines=4` |
| valid record + future record | `n_7d=2, n_30d=2`, last = the **future** record | `n_7d=1, n_30d=1`, last = the valid record, `source_status=partial` |
| all malformed (garbage lines only) | `n_7d=0, n_30d=0` — a confident zero | `n_7d=null, n_30d=null`, `source_status=unusable` |
| JSON array line only | `AttributeError` | `invalid_structure=1`, counts unavailable, no raise |
| committed `data/whitehouse/alerts.jsonl` (81 records) | `n_7d=0, n_30d=11`, last `2026-10-17T00:34:24+00:00` | **identical** `n_7d=0, n_30d=11`, last `2026-10-17T00:34:24+00:00`; 81 read / 81 eligible / 0 rejected |

The last row is the compatibility proof: for valid input the counts and the last observed event are byte-identical to the baseline. The calendar defect is likewise structural — the baseline clamped `days_to_midterm` to 0 forever after 2026-11-03; this branch returns `null` plus `event_state="past"` and `days_since_midterm`.

### Additive output schema and nullability migration notes

Every addition is **additive**. No key was removed or renamed, and the artifact schema string stays `policy_lever.v1`.

- `jawboning.n_7d`, `jawboning.n_30d`: `int` → `int | None`. `null` already existed for an absent file and both consumers already null-guard it (`templates/dashboard.html.j2:14227` dialog, `:15633` card). The new null states are: unreadable source, wholly unusable source, all-invalid-time source, all-future source.
- `calendar.days_to_midterm`: `int` → `int | None`. The consumer already null-guards it (`templates/dashboard.html.j2:14334`). The new null state is "the 2026-11-03 event has passed"; `days_since_midterm` and `event_state` carry the truth instead.
- `jawboning.last_alert_ts`, `last_alert_summary`, `last_alert_summary_zh`: still `str | None`, now guaranteed to be a **string** when present (the baseline could emit a non-string timestamp or summary). `last_alert_ts` keeps the raw source string; `last_alert_ts_utc` is the normalised UTC instant.
- New keys: top-level `computed_at`, `as_of_basis`; `favored_complex.computed_at`; `jawboning.last_alert_ts_utc`, `source_status`, `coverage`, `evaluated_at`, `evaluated_date`, `diagnostics`; `calendar.days_since_midterm`, `event_date`, `event_state`, `evaluation_date`, `evaluated_at`, `computed_at`.
- Consumer contracts re-read before the change and preserved: `templates/dashboard.html.j2` (jawboning counts, `last_alert_ts[:10]`, `last_alert_summary`, `days_to_midterm`), `templates/basket_detail.html.j2`, `templates/allocation.html.j2`, `templates/sector_central.html.j2` (these three read `state` / `framing` / `framing_zh` only), and `scripts/build_site.py::_policy_lever_view` (schema check `policy_lever.v1`, unchanged).

### Test and gate receipt (actual commands, actual results)

- `python3 -m pytest tests/test_policy_lever.py -q -p no:randomly` at base `3fc5105db74` → **68 passed** (baseline).
- `python3 -m pytest tests/test_policy_lever.py -q` at `a7761c6aa11` → **125 passed**. The suite grows from 68 to 125 cases: scalar/list/null JSON, invalid/missing/wrong-type timestamps, UTC/offset/naive dates, exact window boundaries at ±1 microsecond, future-only, mixed valid+future, all-invalid, empty vs absent vs unreadable, malformed summary values, independent valid record retention, before/on/after calendar date, and unchanged scoring/basket/arming/stale-copy regressions. The clock is injected through the producer's own `now=` argument, so the production default is untouched.
- `python3 -m pytest tests/test_policy_lever.py tests/test_whitehouse_build.py -q` → **161 passed, 2 failed, 1 skipped**. The 2 failures are `tests/test_whitehouse_build.py::test_render_page_emits_current_asset_stamps` and `::test_source_capture_refuses_permissive_existing_directory`; both fail **identically at base `3fc5105db74`** in this environment (they need committed `site/` artifacts that the sparse session profile excludes). They are not a regression of this change.
- Consumer suites `tests/test_whitehouse_build.py tests/test_dashboard_template_render.py tests/test_ftr_w1_template_markup.py tests/test_mag7_panel.py tests/test_ts_u3_dashboard_surfaces.py tests/test_mag7_tape_strip.py -q` → **5 failed, 201 passed, 1 skipped**; the same 5 fail identically at base `3fc5105db74` in a detached base worktree, so they are pre-existing environment failures, not this change.
- `python3 -m scripts.build_policy_lever` → wrote `site/policy_lever.json` (`state=ELEVATED`, `as_of=2026-10-30`, `as_of_basis=price_date`, 81 records read / 81 eligible, `source_status=usable`, `coverage=unknown`, `event_state=upcoming`, `days_to_midterm=1`). The generated site artifact was restored afterwards and is **not** in the commit.
- Gates: `scripts/check_conflict_markers.py` → OK; `scripts/check_ci_trigger_closure.py` → OK, 0 trigger gaps; `scripts/audit_unrun_tests.py` → exit 0, `tests/test_policy_lever.py` not flagged (already enrolled in the `commodities / forex / rates / news / policy panels` CI step); `scripts/check_dag_conformance.py`, `scripts/check_trial_registration.py`, `scripts/check_reliability_contract.py` → exit 0. CI path coverage confirmed: `scripts/build_policy_lever.py` and `tests/test_policy_lever.py` are both in `ci.yml`'s `on.pull_request.paths`, so this change starts the workflow that runs the suite.

### Unresolved integration requirement (P4.T1)

The producer change does **not** change the rendered dashboard on its own: the live surface still reads the artifact with the legacy semantics until the presentation result and this producer result are reconciled by the sole authorized integration writer. Reconciliation points the producer now makes available:

1. The jawboning count row must read unavailable (not an em dash and not 0) when `source_status` is `missing` / `unreadable` / `unusable`; `coverage` is `"unknown"` in every case and the disclosure must say so.
2. The countdown must not present a live zero after 2026-11-03. `days_to_midterm` is `null` past the event and the current template's political-runway row is guarded by `is not none`, so that row will simply disappear; the new surface may prefer the past-tense `context_note` plus `days_since_midterm`.
3. `computed_at` / `evaluated_at` are generation instants, not feed freshness. Nothing may present them as "as of" source recency; `as_of` remains the price date and `as_of_basis` says which basis was used.
4. `event_state` and `event_date` are the calendar's truth; the surface should stop inferring countdown semantics from a date it does not own.

The only path shared with the presentation branch is this plan file, and it is consolidated deliberately by the later integration writer.

### Not claimed by this revision

No PR, no merge, no approval, no ready state, no release, no deployment, no hosted-CI result, no independent source review, no production proof and no acceptance is claimed. The producer result is a source result on its own branch; source custody stays with this operation until the root reconciles it under normal law. No presentation branch, template, generated output, feed writer, scoring threshold, auth path or CI budget was altered.
