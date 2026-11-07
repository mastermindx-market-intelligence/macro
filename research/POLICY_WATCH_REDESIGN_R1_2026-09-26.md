# Policy Watch — Decision Desk redesign study

Date: 2026-09-26  
Owner: Sol, bounded design/research commission from the Chairman  
Operation: `policy-watch-redesign-20260926-sol-001`  
Status: **DRAFT STUDY. Paper scaffold only. Not design acceptance, implementation completion, or deployment.**

## 1. Commission and evidence boundary

Redesign `policy_watch.html` into a production-quality, user-first policy intelligence experience: advanced but immediately understandable, consistent with Mastermind's design system, and useful for deciding what deserves attention. The user requested Paper MCP on the M1 Studio, with M2 as a technical fallback.

Bootstrap authority was read from protected Mastermind/master commit `763ec8f920177fdf48b18df1b8e37b61ab482ef0`: `docs/sol_skills/INDEX.md`, its required cold-start/execution/delegation/closeout packs, and the Paper workflow/connection references. Source inspection in Macro was pinned to `a240da85dde8eacf2efb27f3416e19176b91b787` throughout this study. That Macro branch was not reported as protected. These are observation pins, not assertions about future tips.

Evidence inspected at the Macro pin:

- `docs/DESIGN_DOCTRINE.md`: glance/reveal/study hierarchy, plain language, honesty, bilingual and light-mode obligations.
- `scripts/build_policy_watch.py`, lines 1–250: existing capability charter, source labels, typed UK states, analysis clock and lifecycle-date formatting.
- `templates/policy_watch.html.j2`, lines 1–230, 260–430 and 500–650: copy, visual idioms, actual section navigation, UK desk and analysis disclosures.
- `templates/_policy_watch_current.html.j2`, lines 1–160: current-source state distinctions, recorded versus historical decisions, feed acquisition conditions and comparison inputs.
- `site/policy_intent.json`, lines 1–115: context-only flag, Sep 22 analysis snapshot, thesis/dissent and structured falsifier examples.

The live URL returned HTTP 200 to a header-only check. Web retrieval timed out. **There is no completed live browser interaction audit or full-page visual baseline in this packet.** Source-derived observations below must not be described as measured production usability failures. Current policy statements in the research substrate have not been independently revalidated against today's official sources; they are not republished here as current financial facts.

## 2. Product thesis

**Policy Watch should explain the path from an official change to a market consequence, and show what would confirm or invalidate that interpretation.**

It is not another news feed. It is not an automated buy/sell engine. It should preserve the existing context-only role while making the next research action obvious.

The four user questions are:

1. What changed, and is it actually in effect?
2. Why might it matter to the markets or themes I follow?
3. What should I watch next, and when?
4. What is evidence, what is interpretation, and how did past calls turn out?

Proposed comprehension targets, to be tested rather than claimed: a first-time reader identifies the principal change and its status within five seconds; within thirty seconds they can locate an affected theme, the next checkpoint, and an official source. Depth remains one deliberate interaction away.

## 3. What to preserve; what to improve

### Existing strengths

The builder already has a rich mandate: official records, a coordinated-regime thesis explicitly separated from proof, Fed reform task forces, administration levers, a capital-rotation map, an accountable prediction ledger and monitoring sources. The current template already separates historical background from official dated material and labels the analysis snapshot. The UK desk already distinguishes quiet periods, stale information, source outages, disabled coverage and unavailable interpretation. Preserve these capabilities instead of replacing them with generic headlines.

### Source-visible design opportunities

The local navigation presently exposes up to nine destinations: Quick take, Background research, UK desk, Market views, The Fed, Policy stages, Market impact, Calls & results and Sources. A research-organizational hierarchy is competing with the user's task sequence. Consolidate navigation, not information.

Repeated panels, colored rails, pills, card grids and explanatory footnotes are prominent in the source styling. The redesign should test a calmer, more editorial hierarchy: a small number of material changes on an open surface, structured rows for routine content, and focused detail views for deep work. This is a hypothesis to validate against the live baseline, not a claim that every existing card is defective.

The source CSS still contains literal page backgrounds, several page-specific accent colors, pervasive card rails, and small text styles. Its light canvas uses `#e8ebf1`, whereas the house doctrine names `#f7f8fa` as the superseding value. Reconcile with current canonical tokens during implementation; do not perform a blind global replacement or change other pages.

The official comparison capability already exists in the current panel. The opportunity is to make useful changes easier to discover, not to claim statement comparison must be invented from scratch.

### Additional correctness review to open

Some `policy_intent.json` narrative falsifiers combine relative performance with policy or geopolitical conditions. The visible structured `check` objects use `rel_return`, a threshold and a horizon, without those qualitative conditions. For example, the XLE/XLI examples contain additional real-world conditions in their text but expose relative-return checks in the inspected objects.

This is **a contract/scoring review question, not yet a confirmed scoring bug**: the scoring implementation and any separate qualitative adjudication were not inspected. Before the new ledger labels a thesis correct or wrong, trace whether the result means market performance alone, the policy proposition alone, or both. Display distinct outcomes where they differ. Also make the numeric threshold match the plain-language condition; a material underperformance threshold must not be paraphrased as any underperformance.

A recently generated analysis can still rely on older evidence. `state_asof` is the analysis clock, not proof that every cited fact was refreshed. Preserve evidence dates individually in the detail layer.

## 4. Design alternatives and recommendation

| Direction | Advantage | Limitation | Decision |
|---|---|---|---|
| Headline-first feed | Fast scan; familiar; easy to add sources | Recency can overwhelm materiality and implementation status | Keep as a secondary source view |
| Full analyst workbench | Maximum comparison and research depth | High initial reading cost; too many simultaneous controls | Use inside detail views |
| Decision-led briefing | Directly answers change, consequence and next checkpoint | Requires explicit editorial/ranking rules and honest missing states | Recommended default |

Retain the familiar page name **Policy Watch**. “Decision Desk” describes the experience, not a mandatory rebrand.

## 5. Proposed information architecture

Use four local destinations beneath the existing site shell. Preserve the current shared navigation owner; the Paper header is a reference scaffold, not permission to replace global chrome.

### Briefing

Top-of-page: title, one plain subtitle, desk/theme filters and a compact source-health control. Do not stack a separate large hero, KPI strip, chip strip and tab bar above the actual information.

The principal area presents at most three material changes, not three arbitrary newest headlines. Each item gives a short headline, official status, a one-line change summary, one market implication clearly labeled as interpretation, and one next action such as compare wording, review an exposed theme, or inspect the next decision. A neutral/quiet state is a valid lead when nothing material changed.

A narrower side column holds the next few dated checkpoints and the highest-priority outstanding review. Avoid turning it into a second feed. Research requiring review should remain visible but must not dominate fresh official records.

### Policy map

A searchable, filterable catalog grouped by desk, theme and implementation status. Each row answers what the measure changes, its documented state, the date/precision of that state and the affected transmission channel. Use a list or compact matrix rather than a decorative network diagram.

Open a policy detail view for official wording, the before/after change, lifecycle, expected transmission, counterarguments, affected canonical entities and history. Preserve existing historical Fed task-force and administration-lever material here, clearly dated.

### Calendar

A short chronological agenda for decisions, known implementation dates and research checkpoints. Distinguish an official scheduled event from a model's review deadline. Preserve original timezone and source precision. A date-only record must not become a fabricated midnight timestamp or a countdown timer.

Use the existing calendar data path. The UK Treasury desk does not, by itself, establish a Bank of England calendar integration. Additional coverage requires a verified contract, not a mockup-only promise.

### Calls & evidence

An accountable research ledger, with unresolved and overdue calls easy to find. Show the original proposition, horizon, benchmark, known-at date, current status, result and evidence. A reader can see the original and the revision without losing the original forecast.

Keep the official document/source view within this destination and within each contextual detail. Sources should be one click away, not a mandatory separate navigation stop for every claim.

## 6. Capability migration map

| Existing destination/capability | Proposed home | Preservation requirement |
|---|---|---|
| Quick take / official records / statement comparison | Briefing; expanded official comparison | Keep recorded/historical/awaiting distinctions |
| Background research / coordinated-regime thesis | Policy detail; dated research shelf | Preserve context-only and evidence basis |
| UK desk | Desk selector; independent UK briefing/detail | Do not collapse its typed failure states into US health |
| Market views | Briefing implications; Calls & evidence | Keep dissent, horizon, conviction and analysis clock |
| Fed reform/task-force research | Policy map/detail | Preserve dated milestones and sources |
| Policy stages | Policy map/detail | Preserve gaps and day/month/undated precision |
| Market impact / capital-rotation proxies | Transmission section; canonical theme links | Proxy association is not measured portfolio exposure |
| Calls & results | Calls & evidence | Preserve original predictions and revisions |
| Sources and monitors | Contextual evidence drawer; source registry view | Preserve URLs, publisher and acquisition provenance |

## 7. Visual and interaction specification

Mood: editorial and institutional, with restrained signal color. Reuse the existing Paper/Mastermind token family and Inter. Dark uses graphite canvas and slightly raised panels; light uses a cool light canvas and genuinely white panels with sufficient boundary contrast. Neither needs ornamental glow. Avoid repeated colored left borders and badges that do not communicate a meaningful state.

Typography: 28–32 px page title; 20–24 px lead statement; 17 px section headings; 14–15 px main copy; 12–13 px metadata. Prefer wrapping important names to ellipsis. Keep caption-scale text away from primary decisions. Use the established 4/8/12/16/24/32 spacing rhythm and 8–14 px component radii. Exact CSS remains subject to token reconciliation and visual proof.

Desktop: one compact shell, page heading plus four-view navigation, then roughly a two-thirds/one-third editorial split. Keep the principal change and next decision visible above the first major scroll. Routine rows align source/status/action lanes; avoid eight equally weighted cards.

Mobile: a single-column Briefing with the same information priority, a compact two-row local navigation if required, a filter sheet and full-width detail routes. Do not shrink the desktop matrix. Source evidence must be available by tap and keyboard, not only hover. Horizontal scrolling is permitted only for an explicitly labeled study matrix, never for the page body.

Selecting a material change opens a focused detail route or drawer, preserves filters and scroll position, supports a shareable policy identifier and returns focus to the triggering control on close. Use existing routing conventions; the choice between route and drawer is to be tested at mobile width.

Every concept screen must say that sample data are illustrative. Actual source timestamps, rates, probabilities and source-health counts cannot be fabricated to make a design look populated.

## 8. High-value features and dependency honesty

| Feature | User value | Current evidence / boundary |
|---|---|---|
| Change since prior statement | Separates new information from repeated language | Comparison inputs already exist; extend their presentation first |
| Documented lifecycle | Prevents treating a proposal as an effective measure | Lifecycle formatting exists; preserve unknown/missing stages |
| Policy-to-market explanation | Shows how costs, demand, financing or supply might change | Existing levers and proxy map; interpretation is not observed causality |
| What changes the view | Gives a concrete next research action | Dissent and falsifier fields exist; adjudication semantics require review |
| Review queue | Keeps overdue calls and stale analysis visible | Builder already prioritizes overdue/recently reviewed calls |
| Personal exposure lens | Makes changes relevant to a user's holdings/themes | Proposed; must join existing authorized workspace entities and current holdings data |
| Meaningful-change alerts | Avoids repeated headline notifications | Proposed; reuse existing alerts infrastructure, do not create a second scheduler |
| Since my last visit | Makes return visits valuable | Proposed; needs a trustworthy per-user baseline; otherwise compare two explicit known snapshots |
| Scenario comparison | Clarifies alternative paths and invalidators | Proposed; no made-up odds or causal certainty; use existing data owners |

No automated portfolio action is implied. A policy interpretation alone cannot upgrade a trading recommendation or override the canonical risk/entry systems.

## 9. Truth contract and failure-state design

Keep three different clocks: source publication/document state; acquisition/known-at; analysis snapshot. A fourth research review deadline is not a freshness clock. The glance layer shows the relevant one per panel; detail explains the rest. Do not hide a critical stale state merely to obey a visual word budget.

Facts, interpretation and scenario are distinct semantic fields, not colors applied by sentiment. “Official” describes provenance, not bullishness. “Source checked” requires the existing verified acquisition evidence; an aggregate ok flag is insufficient.

Required states to design and test:

| State | Reader-facing meaning | Behavior |
|---|---|---|
| Verified check, no new items | Nothing new from the checked coverage | Quiet state; retain latest dated record below |
| Source outage | A source did not respond | Scope warning to that source; label cached records |
| Stale source | Updates delayed | Display last successful acquisition; never say live |
| Invalid newest record | Latest update unusable | Earlier usable record may appear, explicitly dated |
| Awaiting latest decision | Latest decision not available here | Older statement remains historical, never current |
| Model unavailable | Official wording is available; interpretation is not | Do not fabricate a neutral stance |
| Desk off | Coverage not enabled | Do not imply no policy activity |
| Missing analysis date | Analysis date unavailable | Fail closed; no build-time substitution |
| No personal matches | No matched exposures in current scope | Keep public briefing available; explain coverage |
| No closed calls | No completed outcomes yet | No hit-rate badge or artificial zero-percent accuracy |
| Conflicting evidence | Sources or interpretation disagree | Present the disagreement; do not average it away |
| Filtered empty view | No results for these filters | Offer reset without claiming global inactivity |

Financial performance and policy implementation outcomes should be separately readable. Hit rates need their denominator, evaluated population, horizon and benchmark in the disclosure. Open/unknown/unscored cases are not silently counted as correct or omitted from context. Do not infer backtest authority from a small display ledger.

## 10. Production acceptance and proof

House-law acceptance: pass the five-second meaning/action test; use plain language; preserve uncertainty; reveal deep evidence; one coherent freshness disclosure; no raw internal enums; EN/ZH parity; genuine light/dark design; no fabricated values.

Accessibility target: WCAG 2.2 AA, verified rather than asserted. In particular, the W3C specifies a 24-by-24 CSS-pixel minimum target rule with defined exceptions; adopt a stricter 44-pixel product target for primary mobile controls. Test keyboard operation, visible/unobscured focus, text/non-text contrast, dialog focus restoration, zoom and reflow. Color cannot be the only status cue. Sources: `https://www.w3.org/TR/WCAG22/` and `https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum`.

Required proof matrix: EN and ZH × dark and light × desktop and mobile = eight core views, plus tablet/reflow and critical failure states. At minimum inspect 320, 390, 768, 1024 and 1440 CSS-pixel layouts; include long translated names and missing fields. Automated checks do not replace visible screenshot review or keyboard interaction.

Functional proof must include source-to-view lineage, stable filtering/back navigation, explicit timezone handling, healthy-versus-no-new-versus-outage cases, latest-decision absence, per-desk isolation, evidence links, and ledger outcome semantics. Test against production-shaped fixtures and then the actual deployed page before claiming completion. No new bundle-weight or latency promise is made without measuring the baseline.

## 11. Bounded delivery sequence

**R0 — Source and experience inventory.** Finish the live-browser baseline, inspect existing shared shell/components, trace the complete data contract and verify the falsifier scoring question. Preserve current producers and adoption owners. This packet is a partial R0 with a concrete proposed direction.

**R1 — Paper design.** Complete the desktop Briefing, then policy detail, ledger and critical states. Design and inspect the mobile and light/ZH variants. Produce the eight-view matrix and named interaction/failure boards. Use explicit file/page IDs and current tokens; other redesign sessions are active in the same file.

**R2 — First implementation slice.** After design review, implement the Briefing with existing official records, statement comparison, a clear dated analysis shelf and source-health disclosure. Keep existing builder/template/committed-site delivery conventions. Retain deep links and existing research access. Do not change scoring while changing presentation.

**R3 — Depth and integrations.** Add the policy explorer/detail and accountable ledger presentation. Only then integrate authorized personal exposure and alerts using canonical owners. Expand calendar/source coverage only after evidence contracts exist.

These phases are proposed work, not dispatched workers or a promise of unattended execution. No production files were edited and no deployment was triggered in this turn.

## 12. Paper checkpoint and exact recovery boundary

Actual host: M1 Studio (`m1studio`), through Remote Desktop Commander and the verified guarded Paper runtime v4. M2 was not used as a fallback for the blocked content write.

Paper file: `MASTERMIND PAGES`, ID `01M2WGNCX9475G79JRKJTCM08P`.  
Page: `Policy Watch · Decision Desk · R1 Study · 2026-09-26`, ID `p-J-1`.  
Page URL: `https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-J-1`.  
Artboard: `01 · Briefing · Dark · Desktop · Illustrative`, ID `1AF7-1`, 1440×1040.  
Applied content: one global-navigation reference group, ID `1AJT-1`. The body is empty. **This is a scaffold, not a completed mockup.**

Applied operations: `policy-watch-redesign-20260926-sol-001-page`, `policy-watch-20260926-board01`, `policy-watch-20260926-header01`. Screenshot observation confirmed the header and empty body. Review verdict: header spacing/alignment/contrast render cleanly; page content and complete design remain unreviewable. The working indicator on this artboard was released by `policy-watch-20260926-finish01` with an observed successful response.

The platform blocked a composite host-analysis request, a foreground helper invocation for three Paper reads, and the later page-heading/local-navigation argument-file write. Those denied actions were not retried on another host or carrier. The refused content mutation is not queued for automatic replay. Capability limitations must be respected; a future continuation should inspect this checkpoint and use only currently permitted operations, not treat a user 'continue' as permission to bypass a platform block.

M1 receipts and scratch material: `/Users/chriswong/.local/share/mastermind/ops/policy-watch-redesign-20260926-sol-001/`. The only screenshot captured here is the scaffold JPEG under its `screenshots/` directory, SHA-256-like filename `e514680cf14750686d9a12c7d1546bd6f9d1502c7d0b45d4ac0c62dfb9c2422a.jpg`. Shared token content hash changed from `5ae876bc` to `bba69475` during other ongoing design work; re-read tokens before any later permitted design changes. Do not overwrite or 'restore' the shared file to the earlier token set.

## 13. Completion ledger

Completed: pinned bootstrap, bounded source audit, design alternatives, proposed four-view architecture, preservation map, high-value feature/dependency register, failure-state and acceptance specification, M1 Paper page/artboard/header creation, screenshot inspection and own-indicator release.

Not completed: full live-site audit; complete Paper mockups; eight-view visual matrix; source-level factual revalidation of current policy theses; scoring-engine adjudication audit; production code; tests; merge; deployment; any watcher or delegated worker.
