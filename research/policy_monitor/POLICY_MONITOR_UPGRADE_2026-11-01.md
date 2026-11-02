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

## Implementation record (2026-11-01, branch claude/policy-monitor-upgrade-20261101)

Source revision: `4bcba1f0a5ed2a1db440b07a820c4dfc8df1c7e1` (this branch; base
`9af0a33eb38b08d902c3e593cb0e276d3f0d6a18`). Independent source/visual review,
hosted CI and release remain with the root — nothing here is a production or
acceptance claim.

### What was built

* `lib/policy_monitor_view.py` — the PURE display normalizer. It projects the
  existing payloads (`site/policy_lever.json`, `latest.fed_path`,
  `latest.fed_stance`, the existing flip-confirmation and event-window views)
  into safe display values: strict mapping/sequence/finite-number/date
  validation, bool-as-number refused, NaN/infinity refused, unsafe URLs
  refused, text and array sizes bounded at the display boundary, no raw
  payload mutated. One bad section degrades on its own.
* `scripts/build_site.py` — narrow wiring: the normalizer is registered as the
  template global `pm_view` and ONE view-model entry (`policy_monitor`) is
  added. The three existing policy inputs are read once, so the card and the
  dialog cannot disagree.
* `templates/_policy_monitor_face.html.j2`, `templates/_policy_monitor_dialog.html.j2`,
  `templates/_policy_monitor.css.j2` — the scoped markup and the token-only
  stylesheet. `templates/dashboard.html.j2` shrinks by ~35 KB: the policy
  markup and the `plx-*` rules leave the 1.4MB template for the fragments.
  The ids `sx-policy-v2`, `dlg-policy`, `dlg-policy-lever-card` and the
  `mx5OpenDlg` / `mx5CloseDlg` contract are unchanged.

### Falsifier outcomes

| Falsifier | Outcome |
|---|---|
| Rising market path and lower same-horizon market-vs-Fed projection render coherently | `tests/test_policy_monitor_view.py::TestRatesPanel` + the browser evidence (market path rises 3.88% → 4.44%; the qualified end-2026 comparison reads −14 bp) |
| All-null, partial, invalid types, nonfinite values, valid zero, stale dates, unknown guidance and missing arming never crash or fabricate a calm/current/zero claim | `tests/test_policy_monitor_view.py` (72 cases) + `tests/test_policy_monitor_ui.py::TestDegradation` |
| Year rollover and non-midyear snapshots do not misplace Fed dots | `tests/test_policy_monitor_view.py::TestFedDotPlacement` (Nov-2026 → 2.03m, Jun-2026 → 6.03m, Jan-2027 → 11.5m; a dot past the horizon or before the snapshot is tabulated, never plotted) |
| Source gap basis ambiguity suppresses the unsupported comparison, while valid observations remain useful | `tests/test_policy_monitor_view.py::TestComparisonBasis` (no `implied_source_meta` ⇒ no spread; `not_comparable` ⇒ no spread, the rule's reason is shown) |
| Recorded policy alert counts are never relabelled Fed speeches without evidence | `tests/test_policy_monitor_view.py::TestRecordedActivity` + `tests/test_policy_monitor_ui.py::TestHonesty` |
| Both themes x EN/ZH x desktop 1440/mobile 390 visibly reviewed; no coloured edge, clipped value, invisible label or duplicate id | `research/evidence/policy_monitor_upgrade_20261101/` (29 captures) + `tests/test_policy_monitor_ui.py::TestDomContract` |
| Actual dashboard template and existing dialog controller are exercised, not only a mockup | `tests/probe_policy_monitor_browser.py` renders `templates/dashboard.html.j2` with the real payloads and opens the dialog through the page's own `mx5OpenDlg` |
| No source/production acceptance claim without its actual receipt | this section; the browser receipt carries the resolved revision and blob hashes |

### Browser evidence

`research/evidence/policy_monitor_upgrade_20261101/` — 29 PNGs + `receipt.json`,
captured at revision `4bcba1f0a5ed2a1db440b07a820c4dfc8df1c7e1` with

```
CI=1 python3 tests/probe_policy_monitor_browser.py \
  --out research/evidence/policy_monitor_upgrade_20261101 \
  --states populated,partial,missing
```

12 shapes: the populated state across dark/light x EN/ZH x 1440/390 (card face,
dialog, and the mobile chart), plus the partial and missing states at one
desktop and one mobile shape each. Every shape records: the values-table row
count, the Fed-projection row count, a successful close/reopen through the
controller with a single dialog instance, Escape closing it, focus returning to
the trigger, and no page-level horizontal overflow at 390.

### Known boundaries (not resolved by this delivery)

* The macro page's detailed dialogs are the registration benefit: the page's
  own access preview sends an anonymous visitor to the sign-in sheet, so the
  probe resolves that preview as a signed-in tier before clicking the face.
  The markup and the controller are untouched.
* `site/policy_lever.json` is dated 2026-10-30, the lever narrative copy is
  dated 2026-07-18 (stale), and the recorded-alert windows do not record their
  end date. The panel reports those limits; it does not refresh them.
* The separate stocks-mode `policy-lever-card` fallback band is outside the
  named scope of this task. Its QUIET fallback and its malformed-row crash
  were hardened in passing; its layout and labels are unchanged.

## R3 — principal review corrections and integration (2026-11-01)

Owner: active Sol principal, original root `policy-monitor-upgrade-20261101-sol-001`.
Follow-on operation: `policy-monitor-r3-review-repair-20261101`.
Source: `claude/policy-monitor-upgrade-20261101`, recovered pushed head
`2184d1d12fcb5f662669b966a7ca76d87739a1ae`, draft PR #10493.

### Custody and routing

R1 reached VERIFIED_TERMINAL, rc=1 / provider turn_limit. Its retained response
digest is `d2683e6b9a81a08ff66695353c23fb1505344fdc7fcdac68eb0be2fa6f7f1816`.
This is a failed execution return, not accepted implementation evidence.
The original worker process chain is absent and its active lane lease is absent.
The pushed GitHub candidate and committed evidence are recoverable. The old
worktree is outside the device file-read boundary; it is preserved and is not
claimed clean. The last accessible /tmp diff additionally preserves a narrow
Fed-dialog chip style restoration; it will be reviewed before incorporation.
No retry, provider failover, lease mutation or overlapping writer is authorized.

Direct bounded principal repair reason: LOWER_TOTAL_OVERHEAD and
PRINCIPAL_JUDGMENT. The principal has reproduced specific semantic and parser
defects against the exact pushed candidate and already owns the interpretation
decision; another full builder dispatch would repeat that adjudication.
This is a corrective follow-on after terminal custody reconciliation, not
shadow implementation. Independent read-only Fabric source/product review of
the corrected integrated head remains required before acceptance; the principal
cannot independently approve their own changes.

The existing R2 producer run has acquired its lease and continues solely on
`claude/policy-monitor-integrity-20261101`. Do not alter its source branch or
producer paths while active. The two branches share the plan file and
tests/test_policy_lever.py: R1's test edits are limited to TestTemplateRender,
while R2 owns producer tests. Integrate their actual hunks deliberately after
R2 is terminal; do not overwrite either return.

### Confirmed blockers in the first candidate

- Padded valid state strings raise KeyError; mixed horizon keys, malformed
  missing-source metadata and finite-but-overflowing chart values can crash.
  ISO date strings with trailing junk are accepted.
- Raw QUIET without either predicate and raw ARMED with missing arming evidence
  retain authoritative complete headlines. Display qualification must preserve
  observed conditions without calculating a replacement producer score.
- Missing SEP vintage/publication evidence still permits the precise -14 bp
  comparison and a current chart marker. Require the existing qualified basis,
  horizon and source dates; keep unqualified observations separately useful.
- Current effective rate and target midpoint labels can be confused. A policy
  observation must not be joined into a SOFR futures curve. Rate geometry uses
  the rate observation date, not the semis snapshot date.
- Aggregate snapshot copy incorrectly dates independent activity/calendar
  components. Consume R2's explicit evaluation/source-quality fields.
- Desktop metric rail belongs beside the chart; remove repeated explanatory
  paragraphs, preserve a compact visible stale-evidence notice, complete
  bilingual labels and keyboard disclosure traversal, and prevent the floating
  assistant control from covering the mobile modal.

### Revised remaining task tree

| ID | Depends on | State | Acceptance |
|---|---|---|---|
| P3.R3 | R1 terminal/reconciled | active | Fix the reproduced display/parser defects and focused layout/accessibility findings; add regression cases that fail on R1. |
| P2.R2 | R2 existing run | active | Consume the original producer return; validate record filtering, zero/unknown semantics and component evaluation dates. |
| P4.I | P3.R3,P2.R2 | proposed | Integrate both exact heads, run meaningful existing regressions, capture and inspect the actual production template at the corrected head. |
| P4.R | P4.I | proposed | Separate qualified Fabric reviewer challenges source and real user-path evidence on the exact integrated head. |
| P5 | P4.R | proposed | Hosted gates and normal independent release, then served macro.html verification; no self-approval or manual self-merge. |

The implementation-record claims above describe R1's own reported results.
They are superseded where contradicted by this review. The candidate remains
NOT_ACCEPTED until these material findings and integrated proof are resolved.
