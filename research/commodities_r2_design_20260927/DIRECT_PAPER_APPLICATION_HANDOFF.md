# Commodities R2 — Direct Paper Native Application Handoff

**Status:** CHECKPOINTED_CONTINUATION / MISSION_COMPLETE:false  
**Commission:** `commodities-r1-20260926` / R2  
**Canonical cumulative checkpoint:** Macro issue #8049  
**Current protected Mastermind procedure pin:** `deed35f6b0d8794987ab9692dd8d46b1549a720f`  
**INDEX blob:** `94d1af402598894372858793a5b1931019c5fa77`

## Why this handoff exists

The current Sol chat still exposes legacy Studio Direct gateway **0.1.7**, so its guarded Paper path remains fail-closed for native writes. The separate Ryan Business **Mastermind Paper** direct app has since completed a real write canary through runtime v6 and explicit-file binding. That path is now the fastest lawful native-application carrier, but it requires a fresh Ryan Business chat with the private Mastermind Paper app selected.

Direct-app acceptance evidence: Mastermind issue #1011 comment **5854808901**.  
Do not replay any historical canary operation IDs from #1011 and do not re-prove the scratch canary.

## Fresh-session carrier

Open a fresh ChatGPT chat in **Paper MCP Admin Ryan** / Ryan Business and explicitly select or @mention the installed **Mastermind Paper** app.

Expected direct tool family:
- `paper_inspect`
- `paper_catalog`
- `paper_read`
- `paper_prepare`
- `paper_edit`

Do not use Studio Direct or Desktop Commander as a fallback inside that direct-app application wave.

## Bootstrap before modifying

1. Re-fetch protected Mastermind `master`.
2. Read `docs/sol_skills/INDEX.md` and record the exact current protected SHA.
3. From that same SHA read `docs/sol_skills/ACTIVE_EXECUTION.md`, `skills/paper-design-workflow/SKILL.md`, and `skills/paper-design-workflow/references/connection.md`.
4. Fetch Macro issue **#8049** and consume its current body before editing.
5. Read this file from this branch/PR.
6. Do **not** rebuild R1/R2 or repeat completed native archaeology unless the canvas itself changed.

## Exact native target

Paper file: **MASTERMIND PAGES**  
fileId: `01M2WGNCX9475G79JRKJTCM08P`  
pageId: `p-L-0`

Preserve the existing **25 populated R2 artboards plus five retained R1 boards** and shared global tokens.

Direct runtime v6 supports explicit-file binding. Correct semantics do **not** require the user-active Paper document to switch. Use `paper_prepare` against the exact target fileId and use the returned **target snapshot** as the write guard.

Before every mutation:
- fresh direct `paper_inspect`;
- fresh `paper_catalog`, require `accepted_for_write=true`;
- direct `paper_prepare(fileId=01M2WGNCX9475G79JRKJTCM08P)`;
- require exact file identity and capture target snapshot;
- fresh read of the exact target node/group;
- one bounded edit with stable operation ID;
- same-carrier post-read and screenshot reconciliation;
- on `EFFECT_UNKNOWN`, stop writes and reconcile the original effect. Never replay.

## DO_NOT_REDO

Accepted/native archaeology already exists for:
- 01 overview `1HCJ-0`
- 02 Explore `1HD2-0`
- 03 signal map `1HD3-0`
- 04 Compare `1HD4-0`
- 05 Gold Brief `1HD5-0`
- 06 Price/Cycle `1HD6-0`
- 07 Physical `1HD7-0`
- 08 Positioning `1HD8-0`
- 09 Catalysts `1HD9-0`
- 10 Revision `1HDA-0`
- 11 Research workspace `1HDB-0`
- 12 Saved case `1HDC-0`
- 13 Evidence drawer `1HDD-0`
- 14 Monitor draft `1HDE-0`
- 15 Recovery/change semantics `1HDF-0`
- 16 Coverage `1HDG-0`
- 17 Light desktop overview `1HDH-0`
- 18 Mobile overview `1HDI-0`
- 19 Mobile Explore `1HDJ-0`
- 20 Mobile Compare `1HDK-0`
- 21 Mobile evidence `1HDL-0`
- 22 Chinese Gold mobile `1HDM-0`
- 23 Chinese light mobile overview `1HDN-0`
- 24 Tablet overview `1HDO-0`
- 25 Save checkpoint `1HDP-0`

Macro #8049 contains the cumulative product rulings, exact board IDs, preservation requirements, current-source audit, failure/effect semantics, and application order.

## First native application batch

Start with a bounded same-phase batch:

### A. Board 18 — Mobile Overview `1HDI-0`
Preserve current status bar and commodity cards. Bring it to desktop-semantic parity:
- six measures: complex source1M, 5/20/60 sessions, DBC1M, GSG1M;
- Model risk qualification;
- explicit 1M labels on investigated commodities;
- Explore all17;
- Oil physical-confirmation question;
- Start research case;
- separate runtime Quote layer for Gold/Silver/Copper/WTI with quote clock distinct from daily analysis;
- Oil→XEG context: 32 up-trend episodes, +1.9% avg next4 weeks, **tailwind not trigger**, downside underpowered;
- customer footer replaces builder/debug copy.

### B. Board 24 — Tablet Overview `1HDO-0`
- complete Research nav;
- six measures in 3×2 rhythm;
- quote layer + separate quote clock;
- same investigation reasons and 1M labels;
- Coverage, Catalyst, Research Case, and Oil→XEG actions without squeezing;
- preserve 768px legibility.

After A/B, take fresh native screenshots. Fix any visible hierarchy/overflow issue before moving on.

### C. Board 19 — Mobile Explore `1HDJ-0`
- keep all17 cards;
- add visible row selection separate from Open;
- max4 enforcement;
- selection tray with identities/remove/clear/Compare;
- selection survives filtering;
- all family filters and ordering/map choice;
- explicit horizon/date;
- empty-intersection/reset state.

If A/B/C reconcile cleanly and reserve remains, proceed to Evidence 13/21 next.

## Next native groups after 18/24/19

Evidence:
- desktop13 `1HDD-0`
- mobile21 `1HDL-0`
Explanation/limits before technical repository metadata. Exact artifact pointer for frozen Gold source uses immutable-blob-scoped `/members/0` with name assertion. Analysis-as-of is separate from unavailable provider/receipt time and method metadata.

Chinese:
- 22 `1HDM-0`: evidence-status colors are semantic info/warn/muted, not Chinese market-direction colors; add Compare/Save and missing evidence qualifier.
- 23 `1HDN-0`: six measures + quote layer + XEG context + research reasons/actions; Chinese red-up/green-down only for signed market direction.

Recovery/Coverage:
- 15 `1HDF-0`: split METHOD_NOT_VERIFIED from actual METHOD_CHANGED; add CLOSED_MARKET and PARTIAL_EVIDENCE.
- 16 `1HDG-0`: lead with canonical five-family build coverage; Energy prices+supply distinct from prices-only families and not-covered Tech materials.

Research/effect:
- 11/12/14/25: preserve write→readback→UI-commit semantics. Known failure preserves state/input. Unknown outcome disables replay and exposes read-only reconciliation. Saving monitor draft does not activate notifications.

Core discovery/detail:
- Overview preserves separate live quote layer and Oil→XEG context.
- Explore can expose existing Watch Signals producer without turning scores into return rankings.
- Compare keeps zero-centered same-horizon visualization and basis qualification.
- Gold model lean remains secondary producer evidence; legacy BUY/SELL labels are not instructions.
- Price/Cycle preserves MTF/long-cycle routing without invented indicator values.
- Physical leads with real Energy prices+supply coverage, then clearly separate synthetic curve/inventory fixtures.
- Positioning supports honest partial state plus exact qualified-raw-report state when available.
- Catalysts leads with current audited schedule + incumbent 60-day/84-alert history before synthetic lifecycle studies.
- Revision preserves original and corrected observations and returns to the saved case.

## Customer-reference cleanup

Current product artboards still include white `Builder · …` panels. Before final customer visual acceptance:

Create exactly one documentation-only appendix artboard named:
`R2 · Implementation notes · appendix`

Move the existing 25 builder-note frames there **without duplicating them**. Preserve their identity/text. Customer screenshots of boards01–25 should contain no white builder/debug panel.

Do not create a 26th product workflow or new lifecycle.

## Product invariants

- source1M != session horizons;
- trend != momentum;
- cycle coordinate != probability;
- futures proxy != spot;
- price coverage != physical confirmation;
- quote clock != daily-analysis clock;
- missing/unsupported/restricted/stale/partial/fetch-failed are distinct;
- missing is never zero/calm/green;
- corrections/revisions/method changes are not automatically market changes;
- saved research preserves original evidence;
- Gold China premium remains contextual/display-only and not an executable spread;
- XEG context is historical research, not a trade trigger;
- no new alert, workspace, calendar, score, lifecycle or publication owner.

## Current evidence anchors

Frozen analytical snapshot remains Macro:
`7150f29a765387f1c14fbae086314af6e0d6bddc`, analysis as-of 2026-09-25.

Current-product preservation audit is a separate capability source and must not silently refresh the frozen mock values. Read Macro #8049 for its latest pinned current-source SHA and blobs before modifying.

## Acceptance boundary

Paper-native visual acceptance is still not production acceptance. Production requires deployed/source parity, real backend workspace/calendar/alert integration, provider rights and freshness contracts, keyboard/focus/accessibility implementation, localization, performance, real browser negative states, rollback and release review.

## Exact stop/continue rule

Continue native edits while:
- next action is bounded/same-phase;
- exact target/effect is reconciled;
- write gate remains healthy;
- enough reserve remains for post-read + screenshot + checkpoint.

Checkpoint before a materially heavier phase, not merely because one board completed.

