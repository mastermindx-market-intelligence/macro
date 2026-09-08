# Committee → Neural Web Dashboard
## Evidence-backed assessment and proposed experience architecture

**Date:** 2026-09-08  
**Author:** Sol, for Chairman Chris  
**Status:** Assessment / proposed design. No architecture freeze, implementation acceptance, deployment, or production proof is asserted.  
**Scope:** Transform the existing Committee experience into a full-width visual entry point to Mastermind's market-intelligence suite while preserving its useful investigations and evidence.  
**Operation:** `committee-neural-web-dashboard-assessment-20260908-sol-001`  
**Durable home:** Macro `research/`; this document is not an Executive Job, queue, new workstream, or grant of execution authority.

## 0. Acceptance gates for the eventual implementation

These are proposed release gates, not tests that have already passed.

1. A user can open the authenticated existing Committee route, understand the current market read and its material limitations, select a real graph node or disagreement, inspect its evidence, open the retained Committee or desk view, and return to the same exploration state.
2. The primary desktop experience is graph-led and uses the available width. At 1440 × 900, the initial viewport contains the orientation/answer, the explorer, and at most two supporting modules—not a wall of prose. At wider desktop sizes it deliberately expands rather than remaining a centered reading column.
3. Every existing useful Committee capability has a named destination. Old deep links resolve to the appropriate new view. A capability is not removed merely because its text is removed from the overview.
4. Graph identities, relations, source status, market readings, and authority come from their existing owners. No second graph database, signal score, registry, chat transcript, research queue, auth scheme, or publication system is introduced.
5. A structural connection is distinguishable from observed agreement, disagreement, and a validated predictive relationship. Agreement is not synonymous with bullish; disagreement is not synonymous with bearish. The graph cannot grant trade authority.
6. Missing, stale, mixed-vintage, partial, corrected, inaccessible, and failed states remain understandable beside the affected claim. A healthy latest model run cannot turn all input sources green. Unknown is never zero or neutral.
7. Dark/light × EN/ZH × 1440/390 screenshots, plus a wide-desktop view, are reviewed against the approved references. Keyboard and touch users have a usable alternative to tiny canvas targets. Reduced-motion and hidden-tab behavior are tested.
8. Authenticated browser evidence shows the real production journey and the actual served source vintages. A successful HTTP response, screenshot mockup, merged PR, or green CI alone is insufficient.
9. Product research activity is distinct from internal software-worker activity. Internal Executive OS or provider-session information is not exposed to subscribers simply because the page is hosted on an admin domain.

## 1. Recommendation and intended outcome

**Recompose the existing route into a Neural Web workspace; do not fork a second dashboard or start a new backend.**

The Chairman's mockup is a strong spatial and aesthetic reference: a dominant map, coherent clusters, compact context, restrained surrounding panels, and an immediate impression of one connected suite. Its best property is not the number of stars. It gives the intelligence system a comprehensible shape.

The current Committee page should become the entry point for that experience. Committee itself remains a first-class, evidence-rich investigation view within the same workspace. Dense explanatory prose, methodology, calibration details, and operational diagnostics move to clearly named secondary destinations.

**Primary user job:** understand what Mastermind is seeing, where that reading comes from, what disagrees, and where to investigate next without traversing an encyclopedia of pages.

**Machine/intelligence job:** project existing, typed, permission-safe relationships and source readings into one coherent exploration context. Preserve entity identity, evidence references, dates, correction state, and authority when navigating between the map, a desk, a ticker, and the existing Brain experience.

**Moat:** the useful combination of proprietary first-party or licensed research outputs, connected evidence, cross-market context, and accountable analysis—not the galaxy animation itself. The interface should reveal that combination rather than replace it with ornamental counters.

**10/10 end state:** a user starts with a readable whole-suite map, follows a specific observation into a dated evidence trail, compares conflicting readings, and reaches the existing research or security workflow with the investigation context intact. The overview remains calm even when the underlying suite grows.

## 2. Evidence basis and limits

### Immutable source pins

| Source | Pin / basis |
|---|---|
| Protected Mastermind procedure | `mastermindx-market-intelligence/Mastermind@2bf0266d5476c8e75dae4afa87cca67a8f12a838` |
| Loaded procedure | `docs/sol_skills/INDEX.md` and `COLD_START.md`, both from that same commit; schema `mastermind.sol_skillpack.v1`, version 1.0.1, bootstrap major 1 |
| Main implementation audit | `mastermindx-market-intelligence/macro@eb9e91961ddc4f3043d0dad358602525e66eccda` |
| Refreshed Macro main | `0b3d19941c031c310e776c653d099d70767b9640` |
| Difference at refresh | One research-vault catalog commit; only `data/research_vault/catalog.json` and `excerpts.json` changed. The audited Committee and governance sources were unchanged in that comparison. |
| Main source | `templates/committee.html.j2`; 5,226 lines; Git blob `418c5b2cacb6125e0b325b8ad363aff587948a23` |
| User's visual reference | Uploaded 1672 × 941 image; SHA-256 `583b2979dbdd6e5e1216fd2ed39f4e2964ab2af0c3d3e18f30407bb35f1653fa` |
| User's current-page screenshot | Uploaded 337 × 2048 image; SHA-256 `4df73fbc6922a7467d83a868dcc8ebc6ee441f38bf89bade4a57d32aae8800f3` |

The narrow screenshot is sufficient to establish the overall stacking problem, but it is not suitable for reliable fine-text measurement. Source inspection, not OCR, supplies the detailed feature inventory.

**Production limitation:** an unauthenticated GET to the supplied admin URL returned HTTP 401. The available Opera browser connection was not active. Therefore this assessment combines the Chairman's screenshots with immutable source and checked-in artifact inspection; it does not certify the currently authenticated production DOM, interactions, or served data freshness. The checked-in JSON observations below are repository snapshots, not live-service health claims.

### Source findings

| Finding | Evidence | Consequence |
|---|---|---|
| The desktop reading width is deliberately constrained. | Template lines 19–20 use horizontal body padding based on `(100vw - 1100px)/2` above 1100px. | Removing the cap is necessary, but not sufficient. This is a page-purpose/composition change. |
| The apparent tabs are chapter links. | Lines 493–533: anchors plus scroll-spy; all sections remain in the long document. | Replace the primary interaction with actual task views and URL state while preserving old anchors. |
| A substantial graph implementation already exists. | Graph controls at 666–705; `initGraph` at 2264; canvas rendering and interaction implementation; reduced-motion and visibility handling at 3263–3303. | Retain and improve the renderer first; do not commission another graph engine without measured need. |
| Hero counts do not all describe the same population. | Lines 2264–2283: curated default node count, curated-result synapse count, and engine count have distinct derivations. | Name denominators. Never substitute raw graph size, source-registry counts, or mockup numbers for one another. |
| The existing view is already connected to multiple real outputs. | Template fetch sites for graph, brief, health, market plane, Cortex memo, stockdata, liquidity, kernel families, half-life, governance and rebalance pulse. | Reuse these producers and consumers; architecture is recomposition, not invention of a new intelligence backend. |
| The current design constitution treats neural-web material as a research/editorial family. | `MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` §10, particularly the family mapping near line 488. | The proposed overview needs an explicit route-archetype amendment; the study views can retain their reading-column treatment. |
| A concurrent freshness-color change touches Committee. | Open PR #6987, head `4e689967751d8ccad3a1b9195c7e30ca171d188e`, read during this assessment. | Recheck before a source change and preserve its language-invariant health semantics. Do not overwrite another owner's fixes. |

### Checked-in artifact observations

| Artifact | Observed snapshot | Why it matters to design |
|---|---|---|
| `site/neuralwebdata/confluence_graph.json` | 281 raw nodes; 1,857 raw edges; `asof=2026-09-04`; produced 2026-09-06T07:43:19Z; graph contradiction summary 1; display-only. | These are raw artifact populations, not necessarily the curated on-screen counts and not the total intelligence estate. |
| `site/neuralwebdata/health.json` | Produced 2026-09-07T18:25:35Z, overall `warn`, `as_of=2026-09-04`. Summary: 132 registry entries, 105 fresh, 9 fresh-partial, 4 stale, 12 missing, 1 degraded, 1 not locally verifiable. | The mockup's universal-green status is not supported by this snapshot. Registry entries are also not the same thing as seven visual clusters. |
| `site/neuralwebdata/daily_brief.json` | Produced 2026-09-07T18:25:35Z; status `warn`; overall as-of September 4 with some September 7 components. Its contradiction entry has a blank ID and generic summary text. | A beautiful card cannot fix an uninformative upstream field. Preserve dates and repair the specific owner-to-consumer mapping separately if still present. |
| `site/neuralwebdata/market_plane.json` | September 7 context snapshot; options-structure fields include nulls and an explicit missing-payload gap. | Do not render unavailable options evidence as neutral or zero. |
| `site/neuralweb/cortex_memo.json` | September 7 memo; successful run; prose refers to two current tensions while the inspected graph summary reports one. | Do not silently choose the nicer number. Establish whether dates/populations differ, or whether a source mapping needs repair. |

These observations do not prove that the entire production system is broken. They prove that the new presentation needs honest, source-specific status and a clear distinction between the time of a computation and the time of its evidence.

## 3. What to keep, improve, and decline from the mockup

**Keep:** the full-width desktop experience, dominant explorable network, stable visual territories, compact state strip, fine panel borders, restrained luminous emphasis, integrated research entry points, and a feeling of one connected product.

**Improve:** make selection—not animation—the main interaction; give each visible cluster and connection an intelligible meaning; replace duplicate metric panels with useful investigation context; make evidence and destination links obvious; keep a readable initial view rather than exposing every small node at once.

**Decline unless supported by their real owners:** enormous neuron/synapse counters, decorative trend sparklines, 99.97% uptime, seven-of-seven online status, six running research agents, or an active orchestration badge. A planned panel is not evidence that a corresponding runtime feed exists.

**Correct the legend:** agreement can support a bearish reading, and disagreement can challenge one. Use relationship labels such as “Supports this reading,” “Disagrees,” and “Feeds this capability.” Use market-direction color only when the datum actually describes direction. Health, relation type, and return direction are different semantic planes.

**Keep the scope public-safe:** subscriber research activity is not the same as software development, CI, provider sessions, or Executive OS workforce activity. Any privileged operational view needs its own existing, server-enforced audience contract. Client-side hiding is not authorization.

## 4. Proposed information architecture

Keep `committee.html` as the compatibility entry point. Use the product-facing identity **Neural Web** for the overall workspace. Do not create an independent `neural-web-v2` product that leaves Committee behind.

The proposed primary tasks are:

| View | Primary question | Main contents |
|---|---|---|
| **Overview** | What is Mastermind seeing, and how is it connected? | Compact read, graph, selected-context panel, concise changes/disagreements. |
| **Committee** | What supports or challenges this ticker's read? | Existing ticker search, evidence, provenance, maturity and freshness, expanded investigations. |
| **Desks** | What is the relevant specialist desk seeing? | Existing desk destinations, current briefs, liquidity/rebalance and specialist context. |
| **Research** | What is the reasoning, and what changed? | Full Today's Read, Cortex memo, cited research and investigation outputs. |
| **More / System** | How reliable is this view, and how is it governed? | Source-health detail, methodology, calibration/accountability and appropriately authorized diagnostics. |

“Explore” is a mode inside Overview rather than another competing page: selecting a node expands the map and inspector; selecting a ticker or desk carries the same context into the relevant task view. “Ask the Brain” is a contextual action using the existing Brain capability, not a second independent navigation tree or a new chat service.

A direct URL should restore the task view, selected entity, region and graph lens where supported. Existing section hashes must open their new destination rather than scroll to hidden content. Back/forward restores exploration state. Unsupported or retired identifiers receive an explanation and a safe overview path—not a fabricated replacement node.

### Desktop composition

The overall hierarchy is a short orientation band followed by a dominant explorer and one complementary evidence rail. At very wide widths, a compact intelligence-area navigation strip may appear within the explorer, creating the mockup's three-pane appearance without three equally dominant dashboards.

At approximately 1920px: use modest page gutters, an optional narrow area/context strip, a generous map, and a compact selected-context rail. At 1440px: collapse the optional strip before squeezing graph labels and evidence copy. The target is roughly two-thirds of the useful workspace for the map, not a graph trapped inside a 1100px reading column.

The rail has one clear state: initially “Where to explore”; after selection, “What you selected / why it matters / evidence / open destination.” It should not continue showing unrelated counters while the user is investigating something specific.

A compact lower tray may show Today's Read and current disagreements. Long descriptions do not sit between the title and the map. Layout should adapt to viewport height and browser zoom; do not enforce a brittle one-screen height that clips controls or evidence.

The shared global navigation remains the existing product navigation family. The page-content width changes; this project does not mint a third site header or locally resize its fonts and menus.

### Mobile composition

Do not shrink the entire desktop galaxy into a thumbnail and stack both rails underneath it. Lead with the current read and a clear exploration/search action. Present selectable intelligence groups and an accessible node list; a focused map is available on demand. Selecting a node opens its evidence as the main task. The same capabilities remain reachable through the task strip and named detail destinations.

### Art direction

**Dark:** graphite/navy depth, fine borders, restrained cluster glows, crisp labels, and atmospheric detail concentrated inside the visualization. Important evidence is bright and legible; inactive edges recede. The map feels alive through interaction, not through gratuitous motion everywhere.

**Light:** cool research canvas, white panels, precise line work, darker text, quiet colored grouping, and shadow rather than neon glow. It is deliberately designed, not merely the dark CSS with colors inverted.

Both use the existing theme token family, type scale, icon system, health semantics, and EN/ZH behavior. The user-supplied image is a style/composition reference, not an exception allowing a parallel palette or copied header.

## 5. Full retention and demotion map

| Existing capability | Proposed primary destination | Still visible at a glance |
|---|---|---|
| Neural Web introduction / long “plain English” preambles | Overview help and Research → About the web | One short orientation sentence. |
| Market-plane verdict, regime, volatility and liquidity | Overview state strip; details in the appropriate desk | Current reading plus a material uncertainty/gap. |
| Synapse map, zoom, fit, full-screen, all-nodes layer | Overview → Explore | The map itself and a compact legend. |
| Graph population and independence metrics | Explore → Coverage / evidence details | Only a count with a clear denominator when it helps the task; accruing/unknown stays honest. |
| Today's Read | Short Overview card; full Research view | Lead finding and a link to its supporting evidence. |
| Ticker search and committee table | Committee | Search or selected-ticker action, not a permanently expanded table. |
| Ticker source provenance and maturity | Committee evidence sections | A plain-language caveat beside a dependent claim. |
| Ask form | Existing Brain/Ask capability, reached contextually | “Ask about this” for the selected entity or reading. |
| Cortex memo and explanation | Research → Cortex read | A concise cited lead; degradation if it changes interpretation. |
| What disagrees | Overview alert/selection path; full disagreement detail | The relevant unresolved tension, not a decorative red count alone. |
| What changed overnight / daily brief | Overview change summary; Research → Changes | The most useful dated changes, without operational log noise. |
| Web Health and health history | More → Source health | Material missing/stale coverage beside affected content. |
| Kernel estimates and half-life | More → Evidence / calibration; contextual links from Committee | No raw IC table on the overview. |
| Liquidity plumbing | Desks → Liquidity | Its current read when relevant to the overview context. |
| Rebalance pulse | Desks → Market structure / rebalance | Relevant calendar context, explicitly not a directional signal. |
| Constitution/governance recent | More → Governance | Only a change that materially limits current use. |
| Policy-Put Doctrine | Research or More → Methodology, with contextual desk links | None by default. |
| Prophet Accountability | More → Track records / validation; existing regional labs | Plain limitations remain near any dependent claim. |

This is demotion with a named landing, not deletion. The objective is fewer visible explanations, not less analytical depth.

## 6. Make the graph useful, not merely larger

### One graph, several views

The same underlying owners should support several presentation lenses:

- **Suite:** product capabilities and their declared dependencies. This answers where an observation comes from and which existing experience consumes it.
- **Market evidence:** dated observations, theses, sectors and regimes, with their genuine typed relations and declared coverage.
- **Disagreements / changes:** focus on relevant current tensions or recorded changes without inventing causes, promotions, or a new ranking model.
- **Source health:** which evidence behind the selected reading is fresh, partial, stale or unavailable. This is not a market-direction lens.

The seven visual territories in the mockup are optional presentation groupings, not seven new canonical data objects. Grouping must reconcile with the existing registry and page identities. A whole-suite claim needs a coverage check that identifies omitted or unmapped capabilities; a larger drawing does not prove complete coverage.

Neo4j Bloom's Perspectives demonstrate the useful distinction between one underlying graph and different task-specific views. Linkurious' grouped-node exploration demonstrates how a collapsed whole can retain access to its members. These are interaction precedents, not recommendations to adopt their backend or copy their proprietary implementation. [E1, E2]

### Progressive detail

The initial graph shows major areas and legible anchor nodes. Selecting an area reveals its actual capabilities; selecting a capability reveals the immediate evidence neighborhood. Distant labels and edges recede. “All nodes” remains available, but it is not the default answer to complexity.

The existing renderer already has curated and wiring layers, seeded placement, node interaction, a cached wiring placement path, and reduced-motion/visibility behavior. Preserve that investment. Audit deficiencies with production-shaped fixtures and interaction traces before replacing the rendering stack.

Provide node and edge search, an accessible synchronized list, clear selection, a legend, and an obvious reset path. Do not require a user to click an eight-pixel glowing dot or drag accurately to access important evidence. WCAG's target-size guidance explicitly recognizes dense visualizations while retaining the need for usable alternatives. [E3]

### A complete investigation journey

Example target journey—not a claim that all proposed joins already exist:

**Overview → select a market/sector reading → highlight supporting and disagreeing evidence → inspect dates and gaps → open the associated ticker Committee or desk → ask about that selected evidence → return to the same map.**

Only observed or declared canonical relationships may be followed. If a market-to-sector or sector-to-ticker link is not available under the existing identity contract, show the gap or link to the appropriate independent desk; do not draw a plausible relationship from an LLM guess.

## 7. Data, time, correction and authority contracts

### Reuse before adding

Keep consuming the existing graph, market-plane, daily-brief, health, memo, ticker and desk artifacts. Consolidate repeated page fetches through a request-scoped presentation loader where useful. This is an in-memory consumer concern, not a new authoritative cache or publication plane.

For chat, the repository distinguishes the older `/api/ask` consumer from the shared Brain gateway. The first wave must not silently create a third route, transcript or grounding layer. Preserve the existing question capability while the owning Brain contract determines how selected-entity context is passed and how any later consumer migration is handled.

### Honest time

Each card has one concise visible freshness statement, with detailed source and production clocks in its receipt. A page's “viewed/refreshed” time must not overwrite the market observation time. Different market calendars and source cadences are legitimate; a mixed-vintage warning is needed when the difference changes the interpretation, not as a reason to blank the whole workspace.

A snapshot replacement should update the selected evidence coherently. Preserve selection by canonical ID. If an item is corrected, superseded or no longer present, explain that transition. Absence on the latest snapshot is not proof of resolution or a disproved thesis.

### Deterministic versus model work

**Deterministic presentation:** identity joins, field mapping, graph filtering/grouping, coverage counts, health states, timestamps, authority badges, safe links, and published ordering inherited from an owner.

**Model interpretation:** existing Cortex or Brain synthesis, with evidence references, observed gaps and its own run status. Model text must not silently change graph relation types, mint quantitative confidence, originate signals, or rank/size/gate trades.

The UI can make useful analysis more accessible without elevating descriptive context to trading authority. A “supports” edge remains within its declared evidential scope. No composite “brain strength” or “synapse health” score should be fabricated to fill a visual slot.

### Failure behavior

| State | Required presentation |
|---|---|
| Loading | Geometry-preserving skeleton for that module, not a misleading empty-success panel. |
| Valid empty result | Explain that there is no matching item and why; preserve navigation. |
| Missing/partial source | Explain what is missing and which parts remain usable. |
| Stale evidence | Keep its real date and a visible caveat; do not style it as current. |
| Source disagreement | Distinguish different dates/populations from a genuine unresolved mismatch. |
| Corrected/superseded | Retain evidence lineage and indicate the newer reading; do not imply history was always the new value. |
| Graph failure | Keep the state read and accessible list/other views available. |
| Brain failure or degraded response | Preserve deterministic evidence and existing conversation behavior; state the limitation without exposing provider internals. |
| Auth/rights failure | Preserve the existing access boundary and explain access state; never bypass with another host or a cached privileged payload. |

All source text and model text should pass through existing safe rendering helpers. Do not expose repository internals, private research artifacts, internal prompts, workforce sessions, or server-only identifiers in subscriber graph payloads or Brain grounding.

## 8. Alternatives considered

| Approach | Benefit | Assessment |
|---|---|---|
| Widen the page and collapse a few paragraphs | Fast cosmetic improvement. | Insufficient as the end state: retains the long-scroll task model and weak cross-view continuity. Useful only as part of a complete first slice. |
| Recompose the existing route and consumers into a graph-led workspace | Preserves working data and workflows while fixing the central experience. | Recommended. Lowest architectural duplication; supports progressive expansion. |
| New SPA, graph backend and orchestration service | Maximum freedom for a clean-room build. | Not justified by this audit. Adds migration, authority, auth and continuity risks before proving the existing renderer is the limiting factor. |

## 9. Bounded delivery sequence after design approval

### Design reference and freeze

Adjudicate the route's new overview purpose against the current editorial mapping. Prepare approved dark and light reference layouts, with real populated and degraded states. Preserve the original mockup's visual intent and the named retention table. A prose packet alone is not a pixel specification; references must be available to the actual implementation session through the permitted artifact path.

This assessment does not freeze exact markup/CSS or assert that the architecture is approved.

### Wave 1 — A usable Neural Web overview with retained Committee

**New capability:** see the suite overview, select real graph evidence, enter Committee, and return without losing context.

Scope: full-width page-content shell; true task views; existing graph and source hydration; a focused evidence rail; compact current-read/disagreement context; preserved ticker search and evidence; old-link handling; honest loading/error/freshness behavior; dark/light and EN/ZH.

Non-goals: new graph database, new model, scoring changes, broader Prophet authority, a new research queue, a third chat stack, estate-wide nav restyling, or an engine rewrite.

This is not a “layout foundation” PR with no usable journey. Its acceptance is the complete overview-to-evidence-to-Committee round trip.

### Wave 2 — Better exploration and source coverage

**New capability:** focus the suite by task/region/evidence type, understand exactly what a connection means, and reach a specific evidence neighborhood without navigating noise.

Scope: source-backed lenses, searchable node/list parity, progressive group detail, stable focus behavior, coverage disclosure, and any strictly necessary producer-to-consumer fields under existing owner contracts. Performance work follows measured traces, not an assumed need for WebGL or 3D.

### Wave 3 — Integrated desk and research investigations

**New capability:** continue an investigation through a specialist desk, full cited read, and the existing Brain experience with consistent entity and evidence context.

Use actual published research and existing activity feeds. A “running research” panel enters this wave only after its product-facing source, audience, lifecycle meanings, and freshness contract are verified. Otherwise show useful completed research rather than simulated work in progress.

Any upstream blank-contradiction mapping or multi-source discrepancy that persists should be repaired as a bounded producer-plus-consumer vertical, not covered over by nicer copy.

## 10. Verification and learning

**Functional:** real authenticated route; initial load; graph/list selection; evidence inspection; ticker search; old deep links; back/forward; open existing desk; ask about selected context; recover from a failed individual feed without a page-wide failure.

**Visual:** compare approved references with dark/light × EN/ZH × desktop/mobile plus wide desktop; inspect initial hierarchy, label legibility, selected-node state, long bilingual names, scrolling, zoom and degraded states. The requested visual ambition is part of acceptance, not optional decoration after functional tests.

**Performance:** retain reduced motion and hidden-tab pause; profile actual curated/all-nodes fixtures and visible interaction paths; record initial layout and selection latency on the declared test hardware. Do not claim an achieved frame rate or supported graph size from this assessment.

**Safety and authority:** verify that stale inputs remain stale even when Cortex succeeds; unavailable options data stays unavailable; graph relations do not change score or signal authority; unauthorized users cannot retrieve hidden operator data; old source and new source clocks are not conflated.

**Learning:** use the existing analytics system to measure task completion and friction—whether users open relevant evidence, reach the intended ticker/desk, return successfully, and need fewer steps to understand a disagreement. Compare against the old journey. Do not claim improved trading returns from a more attractive map or from engagement alone.

## 11. Continuation and exact next action

This is a research/design proposal, not a worker commission or a shipped capability. No Executive Job, Linear state transition, worker assignment, runtime watcher, or source branch ownership is inferred from it.

The next decision is the proposed product structure: **Neural Web as the graph-led overview; Committee, Desks and Research as retained task views; methodology and authorized system detail behind More.** Once accepted, create the governed visual reference packet and specify Wave 1 at component/interaction level before coding.

Before any implementation, refresh the protected procedure, current Macro main, route registry/design-factory packet, and the actual owner/worktree/PR collisions. PR #6987 is one observed collision, not an exhaustive claim about the fleet. The Agent OS searches in this assessment found adjacent Market OS and evaluation records but did not establish a dedicated current Committee-redesign workstream; do not borrow their identity or reopen their completed waves.

Do not repeat the backend build, invent mockup counters, delete useful Committee content, expose engineering sessions to customers, claim source snapshots are authenticated production proof, or call this document an implementation.

## 12. Source register

All repository paths below are grounded at Macro audit commit `eb9e91961ddc4f3043d0dad358602525e66eccda` unless otherwise stated. Repository source snapshots and historical handoff claims are not automatically current production truth.

- **S1:** `templates/committee.html.j2`: width at 19–20; chapter navigation 493–533; feature sections 548–1045; graph controls 666–705; `initGraph` and hero populations 2264–2283; visibility/reduced-motion handling 3263–3303; artifact fetches throughout the script.
- **S2:** `site/neuralwebdata/confluence_graph.json`: `nodes`, `edges`, `asof`, `produced_at`, `display_only`, `contradiction_summary`, `independence`, `gaps`.
- **S3:** `site/neuralwebdata/health.json`: `produced_at`, `as_of`, `overall_status`, `summary_counts`, `cortex`.
- **S4:** `site/neuralwebdata/daily_brief.json`, `market_plane.json`, and `site/neuralweb/cortex_memo.json`: clocks, gaps, contradiction content, and explanatory authority.
- **S5:** `docs/DESIGN_DOCTRINE.md`: glance/help/study distinction, plain-language honesty, light-mode design, and screenshot-first acceptance.
- **S6:** `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`: §9 density/disclosure, §10 archetypes and family mapping, §14 accessibility, §15 responsive behavior, §16 exceptions.
- **S7:** `AGENTS.md` / `CLAUDE.md`: canonical navigation, theme art directions, Brain gateway versus older Ask consumer, source ownership and evidence requirements.
- **S8:** `docs/ops/site-access.md`: access policy and protected asset behavior.
- **S9:** `research/DO_NOT_REBUILD.md`: especially `DNR:KILL-LLM-ORIGINATION`, `DNR:KILL-CAUSAL-DAG-ALPHA`, `DNR:KILL-PUBLIC-INTERNALS`, and the construction-specific composite/parallel-system restrictions. None is amended here.
- **S10:** `agentos/README.md` and `agentos/handoffs/MARKET-OS-2026-08-26-b1a-proven-live.md`: organizational knowledge versus runtime authority; historical warning that Committee's client-side stockdata consumer can have a different vintage from a rendered dossier. The latter requires fresh verification before being treated as a current data-plane defect.
- **S11:** PR #6987, observed open and unmerged at head `4e689967751d8ccad3a1b9195c7e30ca171d188e`: freshness/provenance tokens distinct from language-swapped market direction.
- **S12:** Protected Mastermind Skillpack at `2bf0266d5476c8e75dae4afa87cca67a8f12a838`: atomic procedure loading, authority boundaries, precise capability states, no duplicate planes, and durable source ownership.
- **E1:** Neo4j, Bloom User Guide, “Perspectives,” accessed 2026-09-08. `https://neo4j.com/docs/bloom-user-guide/current/bloom-perspectives/bloom-perspectives/`
- **E2:** Linkurious, User Manual, “Manipulating the graph: Node Grouping,” accessed 2026-09-08. `https://doc.linkurious.com/user-manual/latest///nodegrouping/`
- **E3:** W3C, Understanding WCAG 2.2, Success Criterion 2.5.8 “Target Size (Minimum),” accessed 2026-09-08. `https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html`
- **E4:** Nielsen Norman Group, “Progressive Disclosure,” original research guidance, accessed 2026-09-08. `https://www.nngroup.com/articles/progressive-disclosure/`

The external references inform interaction patterns only. No proprietary code, corpus, branding, or assets are incorporated.
