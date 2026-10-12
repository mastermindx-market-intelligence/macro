# Macro Alert Center — Market Changes Desk hardening candidate

**Status:** SPEC_ONLY / EXPERIENCE-ARCHITECTURE CANDIDATE. No Figma, product code, schema, score, notification, source, or production behavior is changed by this document.

**Current Chairman direction:** redesign the shared public Macro `alerts.html` page from first principles; preserve the useful Terminal Alert Center prototype as a separate product; harden product and intelligence architecture before visual design.

**Procedure pin:** Mastermind protected `master` `d07689b7737f324c16b142d03bffc89cdcf7a27d`, Skillpack 1.0.1. **Current Macro source pin used for this hardening:** `2e972811e82a56928e5f4871300ecb91daf0bed3`.

## 1. Product identity

The page keeps the customer-facing name **Alert Center**. Its product concept is a **Market Changes Desk**: the shared place where a user sees what materially changed across Mastermind's market evidence, understands why it deserves attention, inspects the evidence and limits, and returns to the change stream without opening every source dashboard.

This is the `monitor` archetype, not a second `command_center`. The estate's binding IA says Monitor means “maintain my attention loop,” and the design system assigns `alerts.html` to Archetype G. Therefore this redesign must not clone `start.html`'s two-column command-center identity or re-create `macro.html`'s regime hero. The Monitor identity device remains the **change-log timeline**.

The shared Macro page is not the private alert inbox. Holdings/watchlist/thesis relevance, explicit personal monitor definitions, read/archive state, quiet hours, email preferences and per-user delivery stay with existing F08/Terminal/account owners. Shared Watchlist Sentinel evidence remains excluded from public expansion. A future handoff to the personal monitor workflow may be added through the existing owner; Macro does not acquire that state.

## 2. Source truth that constrains the redesign

`engine.alert_triage.build_triage` remains the sole shared assembler. It already separates cross-source conviction (`act/watch/context`), post-governance severity, recency, cross-asset corroboration, source health, validation, recurrence, event/source/record clocks, deep links, and future-event quarantine. The public page and machine artifacts are projections of that owner. No second alert score, event registry, reader, persistence plane or scheduler is justified.

The current attention score is useful to machines but poor as a dominant visual encoding. Its weights are conviction 40/22/8, severity 30/18/6, recency 20/12/6/2, and cross-asset +10/0/-6. Thus a fresh neutral `watch + minor` observation is exactly `22 + 6 + 20 = 48`. The measured live page had 55/60 rows at priority 48. Score compression is a product reason to demote the number, not a reason to invent a new score.

Current source law also establishes several hard constraints:

- `priority` is an attention prioritizer, never P(correct), trade probability, or position size;
- unknown event time receives zero recency credit and is never called “today”;
- event time, source-as-of and recorded/build time are different clocks;
- a future-dated firing is quarantined rather than ranked;
- `re-fired N× across M days` is observed recurrence, not proof that the condition persisted between firings;
- a consequential source outage or unavailable backdrop withdraws the whole-tape score/stance instead of making the market appear calmer;
- a successful source read is not itself a freshness guarantee;
- a missing store/no coverage is different from a previously available source becoming unreadable;
- measured or documented null edge can demote severity, but absence of a return edge does not erase a valid descriptive event.

## 3. Measured live-page failure mode

A bounded live render/census on 14 Sep 2026 found 60 displayed rows: 55 minor, 57 watch-tier, 43 recurring; 30 rotation and 24 single-name, so 54/60 rows are those two clusters. Sources were altdata 24, themes 22, rotation 8, macro 3, commodity 2, vector 1. Priorities were 48 for 55 rows, 52 for two, then 76/78/82. The page included about 181 help-tip nodes.

At 390×900 the hero, pressure gauge, scoreboard and storyline cards consumed the initial viewport; no ranked alert row appeared before the fold. This is the central UX defect: the system exposes the machinery of triage before exposing the changes being triaged.

The existing five storyline cards are broad taxonomy. They are not event identity, independent confirmation, causal situations or current directional state. They must not be promoted into an AI-looking narrative layer merely because the old page gave them cards.

## 4. Hardened information architecture

Use three task tabs, preserving hash/share state:

1. **Now** — the current shared change timeline. This is the default product.
2. **Explore** — the complete accessible grouped observation population, with search and filters.
3. **History** — actual observed firings and corrections, with explicit history-cap disclosure.

Do not ship a `Situations` primary tab yet. Same-source subject bundles may appear as **Related observations** in Explore/inspector, clearly labeled as grouping rather than independent corroboration. Reserve **Situation** for a future cross-domain object that has accepted event/identity/relationship/correction contracts and can preserve contrary evidence.

### Archetype-G compatibility

The previous brainstorming drifted too close to Archetype A by proposing a permanent 2/3 + 1/3 command rail. Reject that. `alerts.html` stays visually and behaviorally distinct from the command center.

The canonical G sequence becomes:

**session/since header → change timeline → Explore managed list → quiet/coverage states**.

`What Matters Now` is not a giant separate hero. It is the **lead group inside the change timeline**, followed immediately by other recent changes. Compact market context is one inline contextual strip or inspector material, not a full dashboard rail.

On mobile, the timeline remains the identity. Context and methodology never push the first meaningful change out of the first viewport/single swipe.

## 5. What Matters Now — exact v1 presentation policy

`What Matters Now` is a pure display projection. It changes no alert ID, source tier, severity, canonical priority, outbound push decision or source order. It contains **0–3 underlying canonical observations**, one observation per item in v1. It creates no durable `development_id` and performs no LLM grouping.

### Coverage gate

Before selection:

- if consequential coverage/backdrop is partial, suppress any whole-market directional summary and label the lead area **Market read incomplete**;
- still show useful source-specific observations from sources that were successfully read;
- never treat unavailable evidence as zero or neutral;
- do not print a healthy green “all current” claim merely because reads succeeded; freshness and read health are separate.

### Eligibility

An observation may enter `What Matters Now` only when all applicable conditions hold:

- usable known event board date; unknown-time observations remain inspectable but cannot be promoted as “now”;
- existing recency class is `fresh` (`age_days <= 2`, reusing the current canonical recency threshold rather than minting another freshness definition);
- `act` tier is eligible after the freshness/coverage checks;
- `watch` tier is eligible only when its **post-governance** severity is `major` or `critical` and it is fresh;
- `context` tier is not eligible for the lead group in v1;
- future events are already quarantined and cannot enter;
- cross-asset confirm/diverge may change canonical ordering/explanation but cannot make an otherwise ineligible lower-authority row eligible;
- a backtest/IC verdict is never required merely to state that an observed event happened. Negative/null validation must remain visible where relevant and may already have demoted the source band.

### Selection and wording

Among eligible observations, retain their existing canonical attention order and take at most three. Do not fill empty slots, add a source-diversity quota, or synthesize an aggregate merely because three cards look better. One important development is a valid page state; zero is a valid quiet state.

A recurring observation with a fresh latest firing may qualify, but its lead copy must say **re-fired / observed again**, never “still active” or “persisting” unless its source has a continuity contract. A lifecycle-first new observation may say new only when the underlying lifecycle supports that statement. Header counts should say **observations/firings today**, not “new developments,” unless the count explicitly filters to first observations.

The lead group is intentionally stricter than the complete priority queue. A ten-day-old act-tier event may remain high in canonical attention priority and remain inspectable, but it is not `What Matters Now` without a fresh occurrence.

## 6. Timeline and ordering

The Monitor identity should look like a change log rather than a score leaderboard.

**Now timeline:** group by actual board day (Today / Yesterday / earlier date), newest day first; within a day retain canonical attention ordering. Remove exact lead-group items from the lower timeline so Tier 1 never repeats the same fact. Show at most eight non-lead rows initially, followed by a counted `See all N`/Explore action.

This is a presentation order only. The existing `alerts` array, its machine order, scores and outbound consumers remain unchanged. Explore can expose the canonical attention sort and optional time/source facets without changing source authority.

Rows use one disciplined glance anatomy:

`source · event date` → **plain headline** → one short meaning/limitation line → `Investigate`.

No giant numeric score column. No pill forest. Severity, priority components, validation receipts, recurrence detail, provenance and methodology move to inspector/Tier 2. If a row lacks a trustworthy plain meaning line, render the source headline and a neutral `Open evidence` action rather than generating unsupported explanation.

## 7. Research-attention vocabulary, not trade authority

The existing engine's `act/watch/context` and PM action fields remain canonical machine/source facts. The shared page may translate them into **research attention**, never a new trading authority:

- fresh eligible `act` → **Review now**;
- cross-asset divergence on a qualifying row → **Confirm first**;
- qualifying `watch` → **Watch closely**;
- lower-authority rows → **For context**.

These are presentation translations. They do not overwrite `tier`, `severity`, source action, Prophet availability, risk sizing or trading instructions. Avoid presenting generic `high-conviction` as a trade claim on Tier 1; the inspector can show the underlying canonical triage receipt and why the item ranked where it did.

## 8. Context and pressure-score disposition

Remove the large `RISK-OFF / pressure XX/100` hero, giant gradient gauge, four-number scoreboard and permanent storyline taxonomy strip from Tier 1.

Do **not** delete their underlying evidence. The whole-tape pressure/read may live in `Market context`/methodology only when coverage permits, with its existing caveat that it is calculated from the capped review queue and is descriptive rather than probabilistic. If coverage is partial, withhold it exactly as the engine already does.

The always-visible context should be a compact line/strip at most: regime · cross-asset backdrop · next scheduled catalyst, plus a warning only when evidence is missing. Normal source health stays quiet. A coverage problem earns prominence because it changes what the page may safely claim.

## 9. Inspector contract

The inspector is the study surface and preserves the user's timeline position. Desktop uses a large side sheet/dialog; mobile uses a full-screen sheet with exact return state.

Order:

1. **What changed** — source-grounded plain description.
2. **Why it matters** — deterministic/source-owned explanation when available; optional bounded model context later.
3. **Original evidence** — source, exact relevant clocks, source link, original details.
4. **Current read** — ONLY if that source has an accepted independent current-state contract. Never infer current state from a recurrence count or from the original firing.
5. **Context** — relevant regime/cross-asset/catalyst facts with explicit basis.
6. **Validation / why ranked** — canonical tier, severity, priority components and measured validation/NO-GO/null limitations in plain language; exact numbers/receipts belong here rather than Tier 1.
7. **Observed history** — actual firings, first/last occurrence, recurrence and corrections; no interpolated persistence.
8. **Investigate further** — exact source-owned dashboard/evidence deep link.

A missing historical observation is not replaced with today's latest value. Unknown time remains unknown. An unavailable source link or invalid selection names what failed and what remains usable.

## 10. Explanation fallback and AI ceiling

The shared page must be fully useful with all model synthesis disabled.

For the one-line meaning and inspector explanation, use this hierarchy:

1. source-owned plain detail/edge/alert-view copy;
2. deterministic family-specific presentation copy under the existing view/assembler owner;
3. source headline + neutral evidence action when no lawful explanation exists;
4. later optional model explanation, citation/evidence-bound and clearly downstream of selection.

A model cannot select/promote an item into `What Matters Now`, mint event identity, assert current persistence, create cross-source causality, convert news sentiment into urgency, alter canonical priority, or issue a trade. A model wording update is not another market development and must not produce another alert/firing.

## 11. Grouping and future Situation Intelligence

Current cluster values (`stress`, `regime`, `rotation`, `single_name`, etc.) are **facets**, not stories. Use them for filters and perhaps compact counts in Explore, not five permanent narrative cards.

The #7022 `same_source_subject` projection is useful as `Related observations`: same source + explicit subject + multiple alert types. It does not establish independence, causality or cross-domain confirmation. It may never be labeled a true Situation merely because multiple rows exist.

A future Situation earns that label only after it can bind to existing canonical event/security/company/theme identities, retain source/correction clocks, name why each relationship belongs, preserve contrary evidence/unknowns, and survive correction without headline-key identity. It extends existing owners; it does not create a parallel event graph.

## 12. News and Prophet integration boundaries

### News

News does not enter `What Matters Now` because a headline was dramatic, tagged positive/negative or repeated widely. An accepted future news observation needs an event/subject identity, lawful source/use rights, event/source clocks, correction semantics and a bounded event class. Syndicated echoes are distribution evidence, not independent confirmation. Official/company/regulator events can become the first bounded bridge when their contracts support it.

### Prophet

Current shared `alert_triage` is not a customer Prophet opportunity feed. Do not draw Prophet cards into the v1 Macro mockup as though that integration already exists. A later Prophet adapter must consume owner-issued plan/current-state changes with plan identity, applicability and source-specific vintage; Alert Center cannot reconstruct availability or re-score a stock. Prophet remains the flagship elsewhere and can eventually contribute meaningful changes without surrendering its authority.

## 13. Design geometry and art direction

The page must feel like **calm institutional intelligence**, not flat fintech and not a NOC alarm console. Reuse Mastermind tokens/components; no page-local design system.

Dark: restrained graphite/navy depth, modest glass only for sticky navigation/filter chrome, achromatic rows, one brand-accent selection/action treatment. Light: cool paper canvas, white structured surfaces, hairlines/shadow rather than dark glass carried over. Use only the shared monoline icon set; no emoji as UI icons. Hue remains reserved for meaning.

Do not make a permanent right-side command rail; that would collapse Monitor into Command Center. Context remains compact and supporting. Nesting depth <=2.

### Measurable viewport targets

- 1440×900: page identity/session state + `What Matters Now` + **at least three ordinary change rows** visible without scroll when three lead items exist.
- 390×844/900: first meaningful lead/timeline item visible immediately after the header; first non-lead timeline row reachable within the first swipe; no horizontal page scrolling.
- header + compact context should stay roughly <=140px desktop / <=120px mobile before the first lead/timeline row.
- lead group uses row-like cards, not a 300px hero; maximum three.
- ordinary rows target ~64–76px desktop; mobile may use a two-line stack but must remain scan-first.
- inspector ~520–600px desktop or full-screen mobile; timeline does not lose its filter/scroll state on close.

## 14. Required design-state matrix before Figma acceptance

The eventual Figma is incomplete until it demonstrates, in source-shaped examples rather than generic placeholders:

1. complete coverage + 1–3 lead developments;
2. complete coverage + no lead development but ordinary observations (quiet lead state);
3. complete coverage + genuinely no observations in window;
4. blocking partial coverage (whole-market read withheld, surviving source changes usable);
5. nonblocking source unavailable (disclosed without falsely withdrawing unrelated evidence);
6. unknown event time (not promoted as current);
7. new vs re-fired row, with recurrence not persistence;
8. Explore search/filter + no results + reset;
9. history with actual firing and explicit truncation;
10. selected historical firing whose original detail/clocks differ from current projection;
11. correction/window roll where a deep-linked observation is no longer in the snapshot;
12. JS/interactive evidence failure with real source links still usable;
13. long EN and ZH copy;
14. dark/light desktop and 390px mobile;
15. keyboard/focus/Escape/focus-restoration and reduced-motion behavior.

## 15. Demotion/landing table

| Current Tier-1 element | New home |
|---|---|
| RISK-OFF hero word + pressure gauge | Market context/methodology; hidden if partial coverage |
| Act / Watch / Live / Re-fired scoreboard | derived counts only where needed; Explore/History, not a hero |
| five storyline cards | Explore facets; no narrative authority |
| giant numeric priority column | inspector `Why ranked` receipt |
| repeated severity/validation badges | inspector; one restrained attention translation on row |
| repeated recurrence chips | History/one subtle recurrence note |
| Signal Lab link on every row | inspector validation section |
| tooltip forest | one LENS receipt/help entry per relevant section |
| full methodology block | `How this works` detail/Tier 3 |
| 60 equally heavy cards | first 0–3 lead observations + <=8 timeline rows; full population in Explore |

Every capability retains a named landing. This is compression, not deletion of evidence.

## 16. Adversarial acceptance cases

These are design/implementation requirements, not executed tests:

- **A. 55 rows tie at priority 48.** Page remains useful because Tier 1 does not rely on numeric discrimination; no replacement magic score appears.
- **B. Ten-day-old act event outranks newer watch event globally.** Old event remains discoverable/priority-ranked but cannot enter `What Matters Now` without a fresh firing.
- **C. Act event re-fires today after first firing weeks ago.** May enter the lead group as `re-fired today`; never `still active for weeks`.
- **D. Bonds reader fails while surviving stress reads are calm.** Whole-market summary is withheld; outage cannot buy a calmer headline.
- **E. Forex source fails.** Disclose the source loss, but do not falsely withdraw the whole-market read when current authority says it is nonblocking.
- **F. Event date unknown but recorded_at is fresh.** No `today`, no lead promotion, no recency bonus.
- **G. Future scheduled catalyst leaks into a fired feed.** It remains quarantined; upcoming catalyst context is separate from event occurrence.
- **H. Three rows share a cluster.** Cluster is a facet only; no claim that they confirm each other.
- **I. Multiple alert types share exact source+asset.** Related-observation bundle may render with `not independent confirmation`; no Situation identity.
- **J. Signal family has documented/measured null edge.** Event may remain useful context but cannot regain severity/promotion by decorative synthesis.
- **K. Model synthesis is unavailable.** Selection, rows, evidence, history and source navigation remain fully functional.
- **L. Model rewrites explanation with unchanged source evidence.** No new unread item/firing/development.
- **M. News story is repeated by 30 publishers.** Echo count cannot become thirty confirmations or automatic lead priority.
- **N. Prophet source is absent from current alert-triage contract.** Mockup does not imply a live Prophet alert bridge; future integration uses its owner contract.
- **O. User opens Macro signed out.** Shared evidence works; no private watchlist/holding/read state leaks into HTML.

## 17. Implementation/no-rebuild boundary after design approval

Extend the existing owner and the #7022 pure-projection pattern rather than restarting:

- `build_triage` remains sole source assembler;
- preserve existing `alerts` array, alert IDs/order/scores, coverage, push semantics and machine JSON;
- reconcile/port the useful uncapped `explorer` projection, actual-firing history, URL state, inspector and failure-state ideas from #7022 onto fresh main rather than merging the stale branch by inertia;
- add only a pure `presentation` projection for lead eligibility/timeline display if needed; no new score or persistence;
- keep all private monitor/delivery state outside the shared static page;
- prove with real assembler → real renderer → browser in dark/light × EN/ZH × desktop/mobile, plus the negative state matrix above.

Figma, implementation, CI, merge, deployment and production browser acceptance remain separate states.

## 18. Exact next action

Chairman/Sol reviews this hardened contract. If accepted, write the concise Macro-specific experience freeze and **only then** enter Figma. Create a clearly named Macro Alert Center design target so it cannot again be confused with the preserved Terminal prototype. First mock up the Now timeline and its complete/quiet/partial states, then inspector, Explore and History. Do not reproduce the current page before redesigning it.