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
