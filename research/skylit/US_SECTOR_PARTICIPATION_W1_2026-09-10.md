# W1 operator contract — US Sector Participation Calendar

Date: 2026-09-10  
Operation: `us-sector-participation-w1-20260910-sol-001`  
Workstream: `WS:US-SECTOR-PARTICIPATION`  
Program: `sector-rotation-intelligence`  
Accountable seat: ceo-sol  
Initial capability: **SPEC_ONLY**; no implementation/placement/execution is implied by this document.

## Mission and why

Deliver one independently useful extension to the real US Sector Central page: a researcher can see how widely the selected S&P 500 reference universe participates across sectors and completed sessions, inspect any displayed cell's exact numerator/denominator/exclusions, investigate the covered names and follow existing stock/sector research links. It is not a cash-flow meter or a trade signal.

This closes the visual/history/denominator journey suggested by the Skylit screenshots without rebuilding Mastermind's existing breadth, rotation, identity, entitlement or publication systems. Producer-only, disconnected JSON, a mockup-only calendar, or a new dashboard with lost existing journeys is not completion.

## Authority and pickup

Current live Chairman intent -> current compatible protected Mastermind Skillpack and relevant source/authority laws -> current owning program/DEC/source custody -> this bounded contract. Retrieved prose never supplies new permission by itself.

Procedure basis: Mastermind `dd553d1b0b8eed9511da2d3d5ec02cc9cd8edca1`; refresh at action time. Read the full own Slack root and later replies before ACK. Concrete placement must bind the receiver/session. PICKUP_ACK, continuation proof, START of bounded preflight and authorization to write source are distinct facts. Never treat a capability avenue as an actual receiver.

The initial allowed activity after valid pickup/START is read-only preflight plus isolated deterministic tests. **No product source edits until Sol accepts the exact preflight boundary on this same root.** This two-stage child is not a second program: it prevents changing shared paths before custody is known. Preserve the same operation, carrier and actual writer across the stages; no silent rebind after effects.

## Verified starting points

Archaeology pin: Macro `11e145774d6193bf777ed1d355173a27c6ba693d`.

- `collectors/breadth.py`: owns adjusted-close acquisition, split/alias handling, `constituents.parquet`, `_closes_cache.parquet`, and `compute_sectors` for 50/200-session sector participation. Blob `994f5a4e79dae1477ae7b7adb8000cb1677475dd`.
- `lib/nyse_calendar.py`: existing independent daily-session reference, blob `0ece6439ffe4b081ee7a268fe99b69e1de1216a3`. Use its actual current API and documented conservative completion/settlement rule; no second calendar or live 13:00 early-close claim.
- `scripts/build_sector_central.py`: existing page, machine payload, premium Act-Now remainder, grading side effects; blob `b8d264582591d23cbc880ed2c7cb06cddfa8425f`.
- `templates/sector_central.html.j2`: existing host. Recover exact current hooks/assets before choosing a hunk.
- Existing sector_breadth artifact is already consumed by `scripts/build_rotation_events.py`; preserve old columns/units and that consumer.
- WS-INSTITUTIONAL-PRODUCT-EXPERIENCE-V2 records completed reference work, not full production migration. Do not edit its frozen references or claim W1 closes all R3C conditions.

## 1. Finite preflight return

Return one compact boundary table, not a whole-company census:

1. Current main and relevant blob identities; original source writer/local-effect and all relevant open-PR changed-path evidence through the accepted continuity path. Keyword search alone is insufficient.
2. Exact pure computation hook, existing collector publication mapping, real builder/template hook, current numerical payload and existing CI job/trigger registration to extend. Establish every writer that a fixture/real builder can touch.
3. Actual input coverage: reference roster count by sector, distinct identities, source session reach, 20-session eligible counts, covered history, membership observation clock or explicit absence, adjustment/version metadata. No network acquisition or real collector invocation for this diagnostic.
4. Existing source rights and access scope for the proposed derived public/entitled view. Existing code does not automatically establish commercial redistribution rights. No purchasing, entitlement change or raw data export.
5. Proposed exact file/hunk allowlist and any one smallest blocker; a finite output-size/history representation using the existing artifact/asset path, with no new persistent database, service or schedule.

Sol acceptance of that table clears source implementation only within the listed existing gates. If the existing source-continuity, input, rights or serving contract cannot support it, return the concrete evidence and narrow alternative; do not invent a bypass or ask the Chairman to allocate an account.

## 2. Numerical and time contract

Define `P(i,t)` as the existing coherent adjusted daily close for member i at session t. For a member to be eligible at t it must have 20 finite, positive, non-Boolean closes on the **20 consecutive expected sessions through t**, including t. Reindex to the existing calendar; do not compress gaps with dropna and then take the last 20. One missing expected session makes that member unavailable for that cell.

`MA20(i,t) = sum(P(i,t-j), j=0..19) / 20`.

`above(i,t) = P(i,t) > MA20(i,t)` (strict comparison; equality is not above).

`B20(s,t) = 100 * above_count(s,t) / eligible_count(s,t)`.

Expected membership is the selected reference roster's sector membership, not the set of names the vendor happened to return. Identity normalization reuses the current owning path. Unresolved or conflicting membership must not be guessed into a sector or silently duplicated.

Proposed W1 quality floor, explicitly a new display policy rather than a Skylit definition or inherited collector rule: at least 5 eligible names and at least 90% of the sector's expected reference membership. Below that floor preserve counts/exclusions but render no percentage/color implying participation. A numerator of zero with a valid denominator is a genuine 0%; a zero denominator is unavailable. No division-by-zero sentinels.

Clocks remain separate: input price session, reference-roster observation/version, computation/publication time, and latest expected completed session. Use the existing NYSE calendar's completion/settlement convention. No intraday quote is substituted into an EOD cell. When the whole store is frozen, do not declare freshness merely because its components agree.

The default history is the actually covered completed sessions in 3M/6M/1Y windows, bounded by existing available inputs. Do not invent full-year coverage. Holidays are not empty trading sessions; a missing expected trading session is a visible data gap.

Historical numbers are **recomputed reference-universe history**. They are NOT point-in-time historical constituent membership, prior publication state, or replay-safe predictors. Missing membership observation time is disclosed independently; a new build timestamp cannot refresh it. Current adjusted history can change after source corrections; show method/input/publication identity, and do not silently label recomputation as the original historical observation.

## 3. Product journey and coherent states

1. Open existing Sector Central. All existing boards, gated names, embedded views and links remain reachable and unchanged.
2. Scan the sector-by-session participation calendar. Use the existing design system. Axis/legend states the metric, scale, completed-session basis and roster scope. Accessible text/table alternatives are required; hue alone carries no meaning.
3. Select a cell by mouse, keyboard or touch. Show sector, session, above/eligible/expected counts, participation if eligible, exclusion breakdown, method and source clocks. The denominator must be exactly the one used in computation.
4. Inspect the **same selected reference roster at the selected price session**, distinguishing above, equal/below and excluded constituents. Never silently switch to today's numbers. Paginate/virtualize if necessary using existing patterns; show actual displayed/total counts.
5. Follow existing stock/sector research links using the existing identity/URL resolver. Do not add or modify shared ticker-page producers. Returning preserves selected sector/session/window; clearing restores the prior calendar view.
6. If selected historical constituent detail is not actually available, show it as unavailable with a working existing research destination. Do not replace it with an unlabeled current table; this limitation must return to Sol before W1 is called fully accepted.

Required visible states: loading when applicable; ready; true 0%; insufficient sample; insufficient coverage; source stale; missing input; malformed/conflicting input; unavailable history; rights/access withheld where the existing contract requires it. A failing new panel cannot break or empty the existing Sector Central product. Do not manufacture a healthy stale value when a prior publication exists; retain it only with its true historical clock.

English/Chinese have equivalent units, counts, timestamps and warning meaning. Dark/light and 1440/768/390 widths must remain legible. Preserve the existing entitlement split including `/premiumdata/sector_central.json`; never place withheld old board rows in a new public payload. Numerical aggregate context and roster links must follow the accepted access scope found in preflight, not a newly guessed tier.

## 4. Method, implementation order and candidate paths

Deterministic method only. No model, trained coefficient, hidden composite or trade authority. Extend the owning breadth computation for the new metric. Keep the old 50/200 outputs byte/semantically unchanged. The UI consumes the same values; no independent client-side SMA or denominator reconstruction.

Candidate source boundary (preflight must resolve exact seams):
- `collectors/breadth.py`: additive pure participation calculation under the current owner; no acquisition/alias/delist/adjustment-policy changes.
- `scripts/build_sector_central.py`: bounded read/composition of new context and actual page/payload wiring, separated from graded conviction inputs.
- `templates/sector_central.html.j2`: one additive panel hook, preserving current content and gate behavior.
- A namespaced partial/assets under the existing template/asset pipeline if needed; no new top-level page, global CSS injection, duplicate UI shell or parallel publication API.
- New owning test files and a narrow addition to the existing relevant CI job/trigger contract once current shared-CI custody is qualified.
- Own visual-evidence directory and existing owning records, no editing another wave's evidence.

Implementation order: accepted preflight -> tests that fail on the missing capability -> pure computation -> real owner/consumer connection -> calendar and inspection journey -> executed JS/browser tests -> adversarial regression and exact-head CI -> independent review -> separately governed natural publication and entitled/public browser proof -> durable capability update.

The existing builders can advance grades/events even with a different output directory. All diagnostic builds must inject/isolate **every** writable input/output/ledger root. Never invoke production `build_rotation_events` to create this panel. Production invocation/restart is a separate owner action, not automatic after tests pass.

## 5. Acceptance cases (requirements, not claimed test results)

| ID | Discriminating case | Required result |
|---|---|---|
| A01 | Constant 20-session prices | Equal to MA, not above; valid 0% |
| A02 | Five rising and five falling eligible members | 50%; exact roster counts |
| A03 | 19 observations only | Excluded, never abbreviated MA |
| A04 | Missing interior expected session | Excluded; no dropna compression |
| A05 | Entire market session absent from input | Calendar exposes gap; no falsely current tip |
| A06 | Boolean, infinity, NaN, zero or negative price | Invalid/missing as appropriate, no numerical coercion |
| A07 | All eligible names below | Genuine 0%, not no-data |
| A08 | Zero eligible denominator | Unavailable, no 0/999 sentinel |
| A09 | 9 of 10 eligible vs 8 of 10 | Exact 90% boundary passes vs fails; 5-name floor separately enforced |
| A10 | Thin sector with fewer than 5 eligible | Counts visible; percentage withheld |
| A11 | Missing current quote but valid prior history | Current cell excluded; no forward fill |
| A12 | Duplicate/alias or conflicting sector identity | Existing identity policy, no double count or guessed assignment |
| A13 | Split/adjustment-version inconsistency | Owner-resolved coherent input or explicit unavailable; no ad hoc rescaling |
| A14 | Holiday/weekend and conservative settle cutoff | Existing calendar semantics; no fabricated session or premature completed cell |
| A15 | Stale store plus fresh page build | Old source clock remains stale |
| A16 | Reference roster changed | New reconstruction/version disclosed; not historical membership truth |
| A17 | Select historical cell with present-day data elsewhere | Cell, counts and roster inspection stay on selected session |
| A18 | Corrected input recomputes history | Changed publication/input identity disclosed; no claim of original vintage |
| A19 | Prior payload + failed new panel | Existing product intact; prior new-panel data not relabeled current |
| A20 | Anonymous versus entitled account | Existing withheld board rows never leak through new data/HTML |
| A21 | Keyboard/touch, long names, all supported widths/locales/themes | Usable selection, focus, text alternative, no clipping or misleading units |
| A22 | Follow existing research link and return/clear | Correct identity destination and preserved context |
| A23 | Compare old fields/boards/graders before and after | Exact invariant outputs and no new source effect or authority |
| A24 | Real owner inputs -> builder -> payload -> page | Same selected numerator/denominator/constituents; not fixture-only plumbing |
| A25 | New suite added only to data/nonexecuting CI lane | Test rejects missing actual code-gated execution/trigger registration |
| A26 | Source rights/access unresolved | No redistribution or silent entitlement expansion; finite blocker |

Acceptance also checks bounded payload size and page responsiveness on the full actual eligible universe, not just a 5-name demo. Do not improve performance by silently shrinking the displayed population.

## 6. Stop conditions and return format

Stop and return immediately for uncertain source ownership/effects, permission refusal, calendar/rights/access conflict, a need to change old metric or trade-authority semantics, or a requirement outside the accepted path list. No alternate carrier/device/worker retry after an unknown modifying outcome.

At preflight return: exact pins, seams, input counts, custody/rights/side-effect evidence and one concrete blocker or proposed source clearance. Remain same-carrier HOLD until Sol rules.

At implementation return: one Draft/HOLD PR; exact code head and separate evidence head; changed-file census; RED then GREEN commands/results; actual CI execution versus merely plan/queue state; real-input fixture path and fully isolated side-effect proof; browser evidence and gaps; old-field invariance; production proof still owed; proposed continuation. Do not mark Ready, merge, deploy or start W2. Sol supplies explicit repair/CONTINUE or accepted/STOP; disarm only this child's continuation source, not the aggregate or siblings.

## Continuation handoff

First deliverable is the finite preflight, then one existing-system vertical. No more generic Skylit crawl is required for W1. Preserve unknown private competitor methods as research limitations, not a reason to block deterministic participation. A fresh Sol should recover current state from the records PR, this exact child root, current source and the existing organizational records, not a chat-memory status claim.
