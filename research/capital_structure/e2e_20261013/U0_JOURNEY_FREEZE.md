# U0 — Capital Structure journey freeze (current · then-known · scenario)

Status: FROZEN design specification (masterplan §13 task U0, owner O5; deps C0 #9159 and
E0 #9244, both merged). Authored by the Capital Structure V2 Meta-CEO seat, 2026-10-14.

This document freezes *what the user sees and does*. It writes no page code. U1 implements it
over one verified state family (deps S0, U0, P0). U2 adds saved scenarios, monitors and
export. A change to a frozen choice needs a seat ruling or a `DEC:` record. A builder who finds
the spec silent or contradictory stops and escalates. The builder does not invent the missing
treatment.

## 0. Acceptance gates for the implementing unit (not done unless)

U1 is not done unless every gate below holds on a fresh end-to-end run, with zero manual
workarounds:

1. **A31 (three modes are distinct).**
   - The page shows three modes: the current state, the original then-known state, and a user
     scenario.
   - Each mode is distinct in **structure**: a different DOM region or attribute, and a
     different request identity.
   - Each mode is also distinct in **appearance**: a different line treatment (§3), not
     merely a different colour or label.
   - Test: a screenshot of any one panel identifies its mode in greyscale and without its
     heading.
2. **A38 (state survives navigation).**
   - A direct link restores issuer, mode, cutoff, clock, scenario and focus anchor. So do
     back/forward and a language change.
   - Keyboard alone completes every journey in §5.
   - This holds at 1440, 768 and 390 px.
3. **A33 (honest no-path answers).** No-active-path renders only with a positive coverage
   denominator. Unexamined or unavailable routes render as unknown or unsupported (§4).
4. **A34 (no stale identity).** A response renders only if its echoed view identity equals the
   current request key (§2.3). This applies across issuer, mode, cutoff and scenario changes,
   pagination and the evidence drawer.
5. **A37 (exact sources).**
   - Every number and every changed fact drills down to its exact permitted evidence span and
     to the calculation operands (§6).
   - A generic SEC page is a failure.
   - A source the viewer may not see renders as withheld. It is never replaced by a generic
     link.
6. **A40 (private reads).**
   - Scenario reads are entitlement-checked before any private read.
   - Scenario URLs are not cacheable by shared caches.
   - A scenario the viewer does not own renders as unavailable. It never silently falls back
     to current.
7. **A48 (no recommendation).**
   - No recommendation anywhere: no "should", no probability, score, rank or sizing, and no
     price target.
   - Copy is checked against §7.4.
8. **Both themes, judged as designs.**
   - Dark and light are each judged as a design (§8).
   - The evidence matrix in §9 is posted in the PR body.
   - A packet missing the light treatment or its captures is PARTIAL, never PASS.

## 1. Scope and boundaries

- **Surface.** The existing `capital_structure.html`, its templates, the existing theme and the
  authenticated `/api/capital-structure/v1/*` routes. No new page shell, header family or
  palette family (navigation source-of-truth law).
- **Archetype.** E, Intelligence Desk: a desk header with one as-of, a lead brief, at most 6
  dated cards with source chips, a watch table and a methodology band. The issuer dossier keeps
  the C-company decision-header-plus-tabs shape for depth.
- **Held work stays held.**
  - P0 (#8673, HELD DRAFT) owns `templates/capital_structure.js`, `site/capital_structure.js`
    and the runtime harness. U1 builds on #8673's issuer-generation guard after it merges. U1
    does not ship a competing rewrite.
  - The recorded W3/W4 hold is **not** lifted by this freeze. It is lifted only by the W2
    natural-chain proof or an explicit authority ruling. This document is the path-disjoint
    preparation that masterplan §13 permits during the hold.
- **Never in scope.**
  - Offering probability, issuance likelihood, transaction advice, price targets, sizing,
    ranks or scores (A48).
  - Any second calculation path in the browser. The page renders server envelopes only.

## 2. State model

### 2.1 Modes

The three modes come from `issuer_state_contracts.VIEW_MODES`. The UI never shows the raw
slug.

| Mode (contract) | Name on screen (EN / ZH) | What it answers |
|---|---|---|
| `current` | As known today / 截至今日所知 | What the record shows now, including later corrections |
| `then_known` | As known on {date} / 截至 {date} 当时所知 | What a reader could have known at that cutoff, nothing later |
| `scenario` | Your scenario / 您的情景 | What the rules allow under assumptions **you** chose; facts are unchanged |

A scenario is anchored to either the current state or a then-known state. This anchor is the
contract's `FinancingScenario.view` (`then_known` | `counterfactual`). The scenario mode line
always names its anchor. For example: "Your scenario, built on the record as known on 12 Mar
2024".

### 2.2 URL state (one source of truth)

```
?issuer=<issuer_id>&mode=current|then_known|scenario
 &cutoff=<ISO-8601 UTC>      # then_known, and scenario anchored to then_known
 &clock=system|public        # default system; public is labelled research mode
 &scenario=<scenario_id>     # scenario only; the digest of every assumption
 &focus=<anchor>             # optional: route, constraint, event or evidence anchor
```

- **Defaults.** `mode=current` is omitted from the URL. `clock=system` is omitted.
- **Mode changes.** Changing mode, cutoff or scenario is a `pushState` (one history entry).
  Moving focus between drilldowns is a `replaceState` of `focus` only.
- **Invalid combinations render an interim state.** They never silently fall back.
  - `mode=then_known` without `cutoff` renders "Pick a date to see what was known then".
  - `mode=scenario` without `scenario` opens the assumption editor with nothing computed.
  - An unparseable `cutoff` renders as **failed request**, with the bad value quoted.
- **Cutoff from the date picker.**
  - Picking a date means the end of that day in New York time. It is converted to UTC and
    shown in full ("end of 12 Mar 2024, New York time").
  - An exact time is an advanced field.
- **The clock (point-in-time law).**
  - The cutoff applies to `system_available_at`.
  - `clock=public` is labelled on screen ("filing-time view, for research") wherever the mode
    line appears.
  - The UI never substitutes a filing date for a missing acceptance time.

### 2.3 Request identity and the stale-response rule (A34)

- **The request key** is the tuple `(issuer_id, mode, cutoff, clock, scenario_id)`.
- **The echoed view.** Every envelope U1 renders must carry a server-echoed view:
  `view: {mode, as_of, clock, state_id, scenario_id?, generation_id}`.
- **Render guard.** The page renders a response **only if** the echoed view matches the
  current request key. A response that does not match is discarded silently.
  - This extends #8673's issuer-generation guard to the full tuple. It is not a second guard.
- **Scope.** The rule applies to the dossier, events pagination, the scenario result and the
  evidence drawer.
- **Unrevived panels.** A panel whose data has not yet arrived for the new key keeps the new
  key's mode treatment and shows the loading state. Old numbers are never shown under the new
  label.

## 3. Signature: line style carries epistemic status

The memorable device on this surface is **how a panel is drawn**, not what colour it is.

- **Fact (as known today): solid material.**
  - Panels are filled surfaces with a solid hairline edge. They are raised by shadow (light)
    or luminance (dark).
  - Numbers are full ink.
- **Then-known: stamped.**
  - The mode line carries a date stamp: an outlined chip with the exact cutoff and clock.
  - Every timeline and list carries a **cutoff rule**: one vertical (timeline) or horizontal
    (list) 2px rule in `--cs-line-strong`, labelled with the date.
  - Nothing after the rule is rendered in the state.
  - A separate, collapsed disclosure **outside** the stamped region counts what came later and
    links to the current view: "3 filings and 1 correction came after this date". It never
    inlines their content. Inlining would leak post-cutoff information into a then-known
    reading.
- **Scenario: drafted.**
  - Result panels are drawn with a 1px dashed outline. The fill is transparent with a faint
    `--cs-cyan` tint (≤6% mix). There is no shadow and no glow: an assumption must never look
    more alive than a fact.
  - Assumption values are underlined with the same dash, wherever they appear.
  - Every scenario result carries the line "Facts unchanged · assumptions are yours" / "事实未变 · 假设由您设定".
- **Supply and cash are separate rows.**
  - Potential supply (shares, or registered dollar room) and actual cash proceeds (after fees,
    dated) are two rows, with two units, and are never summed.
  - The cash row only ever appears in scenario mode or on a dated, filed transaction.
  - "Potential new shares" / "潜在新增股份" and "Cash to the company, after fees" /
    "公司实收现金（扣除费用后）" are fixed labels.

**Why line style.**
- The semantic hues on this page (`--cs-green` ok, `--cs-gold` warn, `--cs-red` act,
  `--cs-cyan` info) already mean things. Encoding mode in hue would collide with them.
- Hue encoding also fails greyscale and colour-vision checks.
- Line style survives both, and translates without words.

**Rejected defaults** (recorded so U1 does not re-propose them):

- **Hue-coded mode tabs.** Rejected for the collision and accessibility reasons above.
- **One card that swaps its numbers when a tab changes.** This makes the modes structurally
  identical, which violates A31.
- **A time-scrubber slider for then-known.** It invites reading history as an animation and
  tempts the page to show post-cutoff data.
- **A big hero number for "capacity".** The aggregate is often honestly unknown. Leading with
  it puts the least certain number in the most prominent position. The lead is the
  **limiting condition** (§5.1).

## 4. Honest result states

Each state below has its own copy and treatment. One generic "no data" state is a failure.
Copy is GLANCE tier: ≤14 words, plain words, and no internal slugs on screen.

| State | Contract trigger | EN (glance) | ZH (glance) | Treatment |
|---|---|---|---|---|
| loading | request in flight for the current key | Loading {issuer}, {mode name} | 正在加载 {issuer}（{mode name}） | Skeleton inside the mode's line treatment; no prior numbers |
| unsupported | `SUPPORT_STATES` `not_built` / form family not covered | We don't cover this yet | 暂未覆盖 | Muted panel with a link to coverage |
| partial | `SUPPORT_STATES` `partial` | Partly covered: {n} of {m} sources read | 部分覆盖：已读取 {m} 项中的 {n} 项 | Denominator always shown |
| unknown | quantity `unknown` | Not established: {what is missing} | 尚未确定：{缺失项} | Names the missing fact; never 0 or blank |
| no-active-path | every route `ineligible` **and** coverage complete | No open financing route under these rules ({m} of {m} checked) | 按现行规则暂无可用融资途径（已核查 {m}/{m}） | Allowed only with a complete denominator (A33) |
| conflict | quantity `contradicted` / share basis `conflict` | Sources disagree | 来源相互矛盾 | Both values side by side, each with its source chip; no pick |
| stale | generation older than the family freshness window | Data from {date}; newer filings may exist | 数据截至 {date}，可能已有更新的申报文件 | Dated chip on the mode line |
| failed-source | attempts-ledger failure for a needed source | Couldn't read the {form} filed {date} | 无法读取 {date} 提交的 {form} | Names the filing; links to the exact attempt receipt |
| scenario-only | result depends on a user-supplied unknown resolution | Depends on your assumption: {assumption} | 取决于您的假设：{假设} | Drafted treatment plus an assumption underline |
| withheld | quantity `withheld` / entitlement | Not shown on your plan | 您的方案不含此项 | No value, no hint of magnitude |
| not applicable | quantity `not_applicable` | Doesn't apply to this issuer | 不适用于该发行人 | Quiet; excluded from counts |
| failed request | bad URL parameter / server refusal | Couldn't open this view: {reason} | 无法打开此视图：{原因} | Names the parameter; offers the current view |

**Rules for these states.**
- **Unknown is a value.** An aggregate that depends on an unknown says what is unknown. For
  example, "Can't total: authorized shares not established". It never shows a sum of the
  known parts as the total.
- **Pre-cutoff gaps.** In then-known mode, a fact that existed before the cutoff but was first
  observed after it is **unknown at that date**, never "absent". The copy reads "Not yet
  observed on {date}".
- **Standing phrase.** "Registration observed; programme usage not established" /
  "已见注册文件；计划使用情况尚未确定" is the standing phrase for a shelf without takedown
  evidence.

## 5. Journeys (frozen)

Layout: the existing rail plus dossier. The dossier gains a **mode bar** directly under the
issuer title. It is a three-option radio group: Today · On a date · Scenario.

### 5.1 Overview (Tier 1, at most 6 items — the archetype E budget)

1. **Mode line.** The mode name, as-of, clock, and freshness chip.
2. **Lead brief: the main limiting condition, in one sentence.**
   - Examples: "Shelf room is the limit: about $10.0M across both routes." / "The authorized
     share count is not established, so capacity can't be totalled."
   - The lead brief is a statement about the state, never about a trade.
3. **Documented routes.** A count and their status words: open, conditional, closed, unknown.
4. **Supply and funding.** The supply row and the cash row, separate (§3). Cash appears only
   when dated or in scenario.
5. **Most consequential change.** Dated, with a source chip and a one-line plain consequence.
6. **Largest unresolved fact.** The named unknown, plus what would resolve it ("what we're
   watching").

Depth sits below, in tabs: Routes and limits · Funding schedule · Changes and filings
(the existing change and event lists) · Method.

### 5.2 The seven required journeys (masterplan §11)

| # | Journey | Path | Frozen behaviour |
|---|---|---|---|
| J1 | Recent change → exact source | Overview item 5 or the change list → change row → evidence drawer | Drawer opens at the exact accession, document, section and span; focus moves to the drawer heading; Esc returns focus to the row |
| J2 | Issuer → financing route → limiting constraint | Rail → dossier → Routes and limits → route row → constraint | Constraint row names the rule class in words (binding rule / staff interpretation / issuer assertion / proposed reform) and links its operands |
| J3 | Instrument → scenario share/cash effect | Routes and limits → instrument row → "Try a scenario" | Opens scenario mode anchored to the current view, with that instrument's action preselected; result shows the supply and cash rows separately |
| J4 | Funding gap → dated uses and assumptions | Overview item 4 → Funding schedule | Each period lists dated uses with certainty words (contractual, conditional, assumed); assumptions are drafted-style, never mixed into facts |
| J5 | Current vs then-known | Mode bar → On a date → pick date | Stamped treatment, cutoff rule, and the "came after" disclosure; switching back is one back-press |
| J6 | Correction explains a prior answer | Then-known view → "came after" disclosure → correction | Shows prior value (stamped) beside current value (solid), with the correction's own source and available-at time; never edits the prior |
| J7 | Saved monitor and authorized export | Scenario or issuer → Save / Export (U2) | U0 freezes only the identity: a saved item restores the exact URL key in §2.2; behaviour belongs to U2 |

### 5.3 Scenario editor

- **Inputs.** All inputs are in one disclosure, "Assumptions ({n})":
  - price: a fixed price, or a dated path;
  - horizon start and end;
  - fee rate;
  - the selected actions (routes);
  - resolutions for named unknowns.
- **A new identity per edit.** Each committed edit computes a new `scenario_id`. The page
  pushes a history entry and recomputes from the server.
  - The previous scenario stays reachable with Back.
  - Editing never mutates the anchor state.
- **Results.** Results always sit above the fold, before the inputs on mobile:
  - per-route bounds;
  - the binding constraints in words;
  - the aggregate, or the named unknown;
  - the jointly feasible witness ("one way the room could be used");
  - supply and cash rows.
- **No recommendation.** The witness is labelled as illustrative of feasibility, not a
  recommendation: "One allocation that fits every limit — not advice" / "满足全部限制的一种分配方式——并非建议".
- **Scenario names.** A scenario is named by its user label or an auto label ("Scenario, 14
  Oct, 3 assumptions"). The raw id appears only in the Method receipt.

## 6. Source drilldowns (A37)

- **Hover tier.** Every number and changed fact has a popover (≤80 words,
  `data-tip-en`/`data-tip-zh`, never `title=`) that answers three things:
  - what it is;
  - how it was computed, in words;
  - a source chip: source class, date and grade word.
- **The evidence drawer** (activated by click or Enter) is the existing drawer. It shows:
  - the evidence ref (accession, document, section and span, plus an excerpt where permitted);
  - the calculation receipt: each operand with its own source chip, the rule reference and its
    class, the rule-pack version, and the input generation ids;
  - which clock made the source available.
- **Permitted links only.** A source link points to the exact permitted filing document
  anchor. If that is not available to the viewer, the drawer says "Source not available on
  your plan". There is no fallback link.
- **Navigation inside the drawer** does not change the request key. Opening and closing it
  updates `focus` only.

## 7. Copy law

### 7.1 Tiers
- **Glance:** a title of ≤4 words and a subtitle of ≤14 words.
- **Hover:** ≤80 words.
- **Study:** the Method tab.

### 7.2 Parity and attributes
- EN and ZH strings ship together. The ZH glance line is never longer than 1.4× the EN width at
  390 px; check the longest three states.
- No translated text goes in `title=`.

### 7.3 Never on screen
These items never appear on screen: `then_known`, `counterfactual`, `binding_rule`,
`state_id`, `generation_id`, `scenario_id`, and rule-pack digests. Each has an on-screen word,
or lives in the Method receipt only.

### 7.4 Banned phrases
These are banned in every mode, in EN and ZH equivalents:
- likely to raise / 可能融资;
- should / 应当 (as advice);
- recommend / 建议 (except inside "not advice");
- probability / 概率;
- score / 评分;
- rank / 排名;
- size the position / 仓位;
- target price / 目标价;
- dilution risk score.

### 7.5 The "what we're watching" line
The "what we're watching" line names a condition, never an action. For example: "Watching for
a takedown under the March shelf" / "关注三月份储架注册项下的实际发行".

## 8. Theme art direction

Both themes keep the same IA, states, actions and §3 mapping. They differ in material
treatment.

| Element | Dark — command center | Light — research workspace |
|---|---|---|
| Fact panel | `--cs-raised` with luminance lift, solid `--cs-line` edge, no glow | White material, hairline `--cs-line`, the soft `--cs-shadow` lift (facts have weight) |
| Then-known stamp | Outlined chip in `--cs-line-strong`, ink text, cutoff rule at 2px `--cs-line-strong` | Ink-outlined "paper stamp" chip, cutoff rule at 2px ink at 22% |
| After-cutoff disclosure | Muted text on transparent, outside the stamped region | Same, with a hairline top border |
| Scenario panel | 1px dashed `--cs-cyan` at 70%, 6% cyan tint, no shadow | 1px dashed cyan ink, a cool 4% tint, no shadow (drafted, not built) |
| Supply vs cash rows | Two rows, a hairline between them, tabular numbers, units right of value | Same, with the unit in `--cs-muted` |
| Unknown value | "Not established" text in `--cs-muted`, no dash or zero | Same |
| Conflict | Two values in two solid sub-panels, a `--cs-gold` edge on the pair | Same, gold hairline |

**Token law.**
- New mode tokens are derived from theme tokens: `--cs-mode-fact-*`, `--cs-mode-stamp-*`,
  `--cs-mode-draft-*`, each a `color-mix` of `--text`, `--panel` or `--info`.
- They live in `templates/capital_structure.css`.
- No runtime-injected stylesheet and no parallel palette.
- The `.cs-*` MIGRATE ratchet (rebinding local tokens to theme tokens) continues independently.
  U1 must not deepen local-token debt.

**Motion.**
- Mode change gets one 160 ms cross-fade of the dossier body. That is the only motion.
- Under `prefers-reduced-motion` it is none.
- There is no animated scrubbing.

## 9. Keyboard, focus, responsive, evidence

### 9.1 Mode bar and date picker
- The mode bar is a radio group: arrow keys move, and Space/Enter selects.
- The date picker is reachable by Tab.
- Selecting a mode moves focus to the mode line (`tabindex=-1`), and an `aria-live=polite`
  region announces "Showing the record as known on 12 Mar 2024" / "正在显示截至 2024年3月12日 当时所知的记录".

### 9.2 Back navigation and language changes
- On back or forward, the page restores the mode, cutoff, clock, scenario and the element named
  by `focus`. If `focus` is absent, focus goes to the mode line.
- A language change keeps every URL parameter and the focused element.

### 9.3 Breakpoints

```
1440                                        390
┌ rail ┬ dossier ─────────────────────┐     ┌ dossier ───────────────┐
│ list │ Issuer · CIK                 │     │ Issuer                 │
│      │ [Today|On a date|Scenario]   │     │ [Today|On date|Scen.]  │
│      │ mode line ── stamp/freshness │     │ mode line              │
│      │ lead brief (limit)           │     │ lead brief             │
│      │ routes │ supply/cash         │     │ routes                 │
│      │ change │ unresolved          │     │ supply / cash          │
│      │ tabs: routes·funding·changes │     │ change                 │
└──────┴──────────────────────────────┘     │ (unresolved in tabs)   │
                                            └────────────────────────┘
```

- **768 px.** The rail collapses to the existing search drawer. The overview is one column.
- **390 px.** The mode bar is full-width with short labels. The overview shows the lead plus 3
  items (the archetype E mobile rule). Scenario results come before the assumptions.

### 9.4 Evidence matrix (posted in the U1 PR body)

The core matrix covers all three modes (current, then-known, scenario):
- dark and light;
- EN and ZH;
- 1440 and 390 px;
- 24 captures in total.

Additional captures:
- the twelve §4 states in dark and light at 1440 EN;
- the three longest-copy states in ZH at 390;
- one 768 capture per mode;
- a keyboard-only recording of J1, J5 and J3, plus a back/forward and language-change replay.

## 10. Hand-off to U1 (contract expectations, not frozen API)

- **View identity.** The dossier, events and scenario routes accept the §2.2 key. They echo
  `view` (§2.3). The server, not the browser, computes every number.
- **Entitlement first.** Entitlement is checked before any scenario or private read.
  Scenario responses carry `Cache-Control: private, no-store`.
- **Tests U1 owns.**
  - Request-key mismatch discards the response.
  - No-active-path requires a complete denominator.
  - No banned phrase appears in rendered EN or ZH.
  - Then-known renders nothing after the cutoff.
  - Supply and cash are never summed in one row.
- **Lane order.** Each of these ships in the existing `capital-structure-intelligence` CI job,
  after P0 (#8673) merges and the W3 hold is reconciled.
