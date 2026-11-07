# Intelligence Workspace 2.0 — research, thesis test and architecture decision

Research date: 2026-10-03. Read [the source/capability ledger](01_CENSUS_AND_SOURCES.md) before interpreting this as a current product claim. External capabilities below are first-party documentation observations, not hands-on paid-product benchmarks. Academic discussion is a targeted primary-literature synthesis, not a systematic review or a claim that laboratory results generalize automatically to investment work.

## 1. Executive product thesis

**An Investigation is an optional, durable research commitment: a question, its subject scope, the analyst's evolving argument, the evidence/revision references that support it, and enough explicit continuation state to resume responsibly. A Workspace is a view of that investigation, not its database.**

The desired loop is:

`notice a question → establish scope → inspect qualified facts → compare explanations → preserve belief and evidence references → leave → resume with a change account → revise deliberately → decide/close or continue`.

The product is not a universal replacement for quick charts, company pages, watchlists, Thesis, saved filters, alert management, portfolio decisions or Brain threads. A quick lookup must remain quick. An investigation begins only when a user chooses to retain research intent; opening a page is not consent to create a durable research object.

The strongest value hypothesis is **correct resumption**, not more panels. A returning analyst should recover the question, prior belief, unresolved contradiction, last reviewed evidence basis and next discriminating observation without reconstructing a chat transcript. This is an engineering/product hypothesis to test, not an established user-study result.

### What survives the challenge

Persistent intent is valuable when work spans sessions, sources or competing explanations. Layout identity alone cannot express it safely; existing Thesis versions demonstrate that durable authored research already matters, while the saved-view serializer proves that filter persistence is not question persistence. These are source-backed architectural distinctions, not proof of user demand. [I08,I15,I16,I25 in the source ledger]

### What is rejected or narrowed

* Not every page visit, security or chart set should become an Investigation. Existing layout-only use stays first-class.
* “Everything in one workspace” is not a coherent ownership rule. The object references facts, hypotheses, source documents, queries and alerts owned elsewhere.
* “Remember everything” is not the temporal contract. Retain meaningful authored revisions and owner-supported evidence references, not all market ticks, all UI events or opaque model memory.
* “Never freeze the answer” cannot mean deleting history. Old human beliefs and historical AI outputs may be preserved with their original basis and non-current status. Refreshing evidence does not rewrite them.
* A graph is a useful analytical projection, not automatic justification for a graph database or universal evidence lifecycle.
* A single confidence score would conflate source quality, freshness, evidence coverage, model uncertainty and the analyst's belief. Those remain separate.

## 2. Professional workflow research

### E01 — AlphaSense: direct counterevidence to novelty

[Getting Started with Workspaces](https://help.alpha-sense.com/hc/en-us/articles/51087728136979-Getting-Started-with-Workspaces), updated June 23, 2026, describes a research hub grouping questions/threads, curated knowledge, reports, grids and activity around a theme, company, event or deliverable. One-off questions do not require a workspace. Templates can expand the source set beyond curated workspace knowledge.

**Mastermind implication:** persistence around a question is no longer a differentiator by itself. Keep creation optional and make source expansion visible in Brain receipts. The distinctive target must be a testable combination of market-owner truth, changed evidence, historical belief and contradiction—not an unsupported claim that competitors lack research memory. This documentation does not establish their complete bitemporal or contradiction semantics; absence from this page is not proof of absence from the product.

### E02 — AlphaSense: explicit research-to-watch transition

[Saved searches and email alerts](https://help.alpha-sense.com/hc/en-us/articles/41815267178899-Save-Searches-and-Create-Email-Alerts-in-AlphaSense) separates a saved search from its configured email delivery. [iOS documentation](https://help.alpha-sense.com/hc/en-us/articles/42253345516435-AlphaSense-on-iOS) describes continuity for saved research access, watchlists and alerts.

**Implication:** a saved question can suggest a watch condition, but creating one remains a separate, visible owner action. Mobile continuity should preserve intent and evidence access, not merely shrink a desktop grid. These pages do not prove every desktop workspace interaction is available on mobile.

### E03 — TradingView: layouts are useful precisely because boundaries exist

[Layouts, charts, drawings and indicators](https://www.tradingview.com/support/solutions/43000692404-layouts-charts-drawings-indicators-and-their-interaction/) distinguishes layout composition from separately managed watchlists and alerts. [Chart synchronization](https://www.tradingview.com/support/solutions/43000629992-how-to-sync-the-charts-of-my-layout/) documents selectable synchronized attributes and symbol/interval groups.

**Implication:** reuse the user's mental model of deliberate linking, but expose the attribute being linked. Do not synchronize symbol, time, scenario and evidence merely because widgets have the same color. Keep independent lifecycle objects independent. Competitor drawing-sync behavior does not authorize changing Mastermind's existing symbol/drawing write semantics.

### E04 — TradingView Advanced Charts: save is not replay

[SDK saving/loading documentation](https://www.tradingview.com/charting-library-docs/latest/saving_loading/) describes chart-state persistence and separately configurable drawing storage; the default saved layout does not preserve the visible time range as historical data replay.

**Implication:** layout restoration, visual viewport restoration and point-in-time evidence reconstruction need distinct promises. This SDK is not the same product as TradingView's retail terminal; its documentation must not be used to claim retail limitations.

### E05 — Koyfin: configured context and reusable analytical lenses

[My Dashboards](https://www.koyfin.com/help/mydashboards-myd/) supports template/blank dashboards with tables, charts and news. [Linked-widget release documentation](https://www.koyfin.com/help/release-notes/release-v3-4/) shows selecting a table security to drive grouped charts; this is historical feature documentation, not a newly launched 2026 capability. [Financial-analysis templates](https://www.koyfin.com/help/financial-analysis-templates/) preserve reusable metric arrangements.

**Implication:** good defaults and deliberate links reduce setup cost. Separate a reusable analytical lens from the investigation to which it is applied; a template should not carry another user's thesis, rights or active alerts. Do not assume a dashboard alone remembers the reasoning behind it.

### E06 — LSEG Workspace: context integration without ownership merger

[Workspace SDK](https://developers.lseg.com/en/api-catalog/workspace-sdk/workspace-sdk) describes contextual integration and navigation between applications on web/desktop surfaces. [REDI on Workspace](https://www.lseg.com/en/data-analytics/products/workspace/redi-on-workspace-oems) illustrates a broader research-to-execution workflow.

**Implication:** interoperability can be achieved through explicit contracts instead of one giant object. Mastermind must deliberately stop research-context propagation from inheriting execution authority. A neighboring execution application remains a distinct permissioned lifecycle. These product pages are not a technical audit of LSEG's internal persistence architecture.

### E07 — FactSet IRN: capture belongs to the research owner

[FactSet Internal Research Notes extension](https://chromewebstore.google.com/detail/factset-internal-research/gdjhelljhafjooglnicibdboglddicfl), published by FactSet and updated June 10, 2026, describes capturing web material into authenticated Internal Research Notes and sharing through that research environment.

**Implication:** capture should route into an existing research/content owner with attribution and entitlements, then attach a reference to the investigation. It should not become a browser extension's private evidence silo. This narrow source supports the capture workflow, not every FactSet collaboration or versioning capability.

### E08 — Heptabase: views do not own knowledge objects

[Fundamental elements](https://wiki.heptabase.com/fundamental-elements) distinguishes cards from whiteboards: a card can participate in more than one board without the board owning it. [AI workflow](https://wiki.heptabase.com/work-with-ai) describes sourced interaction and explicit creation of cards from useful outputs. [Performance guidance](https://support.heptabase.com/en/articles/11430704-troubleshoot-performance-and-lag) identifies visible complexity as a practical cost.

**Implication:** layout-independent references are a credible interaction pattern; use graph views when they answer a relationship question, not as mandatory navigation. Explicit promotion of useful AI material is safer than treating every answer as research state. Lazy rendering and bounded default composition are product design decisions, not just later optimizations.

### E09 — Palantir Contour: analysis logic, data refresh and saved output differ

[Contour overview](https://www.palantir.com/docs/foundry/contour/overview) and [core concepts](https://www.palantir.com/docs/foundry/contour/core-concepts/) describe visual analysis paths, parameters and shareable dashboards. [Saving datasets](https://www.palantir.com/docs/foundry/contour/datasets-save) makes an important distinction: saved outputs use current inputs even when the interactive analysis has selected older input versions.

**Implication:** explicitly separate viewing an old state from reproducing an old result. Mastermind should refuse historical export/synthesis when required inputs cannot be reconstructed, rather than silently calculating against live data. Guided views can be generated from richer analysis without making every consumer operate a blank canvas. This is a semantic counterexample, not a claim that Contour conceals its documented behavior.

### Comparative synthesis

Across these products, useful persistence is layered: arrangement, source selection, reusable queries, authored knowledge and activity history are different objects. Mastermind should combine that separation with owner-specific financial semantics. The stronger loop proposed here is **question → qualified evidence → competing explanations → reviewed baseline → explicit change account**. No external documentation establishes that this exact combination is unique; the appropriate claim is a focused, measurable product direction.

The largest expected friction in our proposed design is bookkeeping. Reference pinning, comparison alignment and rights explanations could overwhelm ordinary research. Countermeasure: sensible templates, change-first summaries, progressive detail, and no demand to author a formal hypothesis before saving a question.

## 3. Primary research literature and limits

### L01 — Sensemaking is iterative, not a linear checklist

Pirolli and Card (2005), [The Sensemaking Process and Leverage Points for Analyst Technology](https://andymatuschak.org/files/papers/Pirolli,%20Card%20-%202005%20-%20The%20sensemaking%20process%20and%20leverage%20points%20for%20analyst%20technology%20as.pdf). Original paper text and a diagram page were inspected. The model distinguishes information gathering from representation/hypothesis development with repeated feedback. The authors caution against overgeneralizing across heterogeneous intelligence tasks.

**Design inference:** support movement from source to argument and back; preserve unresolved questions and discarded interpretations. Do not enforce a one-way research wizard. The paper does not prove that more panels or a particular Mastermind schema improves investment decisions.

### L02 — Coordinated views can expose relationships

Stasko, Görg and Liu (2008), [Jigsaw: Supporting Investigative Analysis through Interactive Visualization](https://journals.sagepub.com/doi/10.1057/palgrave.ivs.9500180). Publisher description explains coordinated views over entities in investigative documents.

**Design inference:** use typed entity/context links and relationship views for investigations where connections matter. A universal graph canvas is not warranted by a system designed around document/entity investigation. Prefer an optional argument/relationship lens beside a readable question-centered view.

### L03 — Provenance has several purposes

Ragan, Endert, Sanyal and Chen (2016), [Characterizing Provenance in Visualization and Data Analysis](https://ieeexplore.ieee.org/document/7192714/), DOI 10.1109/TVCG.2015.2467551. The original framework treats analytical provenance as more than a data-source citation and organizes it by information and purpose.

**Design inference:** distinguish evidence origin, transformation lineage, analyst action and output authorship. Capture the minimal record needed for replay, explanation or accountability; indiscriminate event logging is not automatically useful research memory. This framework is not a prescribed storage engine.

### L04 — Data, interpretation and knowledge generation must not collapse

Sacha and colleagues (2014), [Knowledge Generation Model for Visual Analytics](https://ieeexplore.ieee.org/document/6875967/), DOI 10.1109/TVCG.2014.2346481. The framework connects computational analysis and human reasoning in an iterative process.

**Design inference:** retain separate types for observation, qualified sourced fact, deterministic derivation, hypothesis, model inference and decision. A polished AI narrative is not a new Native Fact. This is a conceptual model rather than causal evidence for one user-interface design.

### L05 — Uncertainty is not one number

Sacha and colleagues (2016), [The Role of Uncertainty, Awareness, and Trust in Visual Analytics](https://pubmed.ncbi.nlm.nih.gov/26529704/), DOI 10.1109/TVCG.2015.2467591. The paper addresses uncertainty across an analytical process and its relationship to awareness and trust.

**Design inference:** display missingness, revision, source conflict, assumption dependence and model uncertainty separately. Numeric probabilities require an actual definition and calibration; an LLM's fluent confidence is insufficient. More uncertainty annotations could also impair comprehension, so progressive disclosure must be tested.

### L06 — Explanations can increase acceptance of wrong AI

Bansal and colleagues (2021), [Does the Whole Exceed its Parts? The Effect of AI Explanations on Complementary Team Performance](https://arxiv.org/abs/2006.14779), DOI 10.1145/3411764.3445717. Across the studied tasks, explanations did not improve complementary team performance and could increase acceptance of AI recommendations whether correct or wrong.

**Design inference:** evidence drawers alone are not an accuracy intervention. Test rejection of wrong-but-plausible synthesis; show counterevidence and unsupported conclusions. Avoid success metrics based only on answer acceptance or subjective trust. The studied tasks do not establish an investment-performance effect.

### L07 — Reasoning friction has benefits and costs

Buçinca, Malaya and Gajos (2021), [To Trust or to Think](https://www.iis.seas.harvard.edu/papers/2021/bucinca2021trust.shtml). The study of 199 participants found cognitive-forcing designs could reduce overreliance, while also bringing usability costs and differences across participants.

**Design inference:** require deliberate review at committing a belief, closing an investigation or creating an alert—not at every ordinary read. Provide an optional “form your view first” mode for consequential comparisons. Do not make constant friction the default or claim it benefits every user equally.

### L08 — Explicit cues can help resumption

Trafton, Altmann and Brock (2005), [Huh, What Was I Doing? How People Use Environmental Cues After an Interruption](https://doi.org/10.1177/154193120504900354). The study distinguished useful salient visual cues from subtler cues that did not provide the same resumption benefit.

**Design inference:** show the saved question, previous belief, unresolved issue and next step before asking a returning user to navigate panels. The evidence is about controlled interruption tasks, not a demonstrated months-long financial research effect; our longitudinal evaluation must test that transfer.

### L09 — Notebook reproducibility requires more than a saved screen

Rule and colleagues, [Ten Simple Rules for Reproducible Research in Jupyter Notebooks](https://arxiv.org/abs/1810.08055). The paper treats notebooks as workflows plus narrative, with reproducibility requiring documented computational context rather than only a result display. Rule's [2018 dissertation](https://escholarship.org/uc/item/0dc498tf) also frames the challenge of communicating iterative analysis.

**Design inference:** a scenario receipt must identify inputs, algorithm/version and assumptions; distinguish exploratory drafts from reviewed conclusions. Do not embed an arbitrary executable notebook system into Workspace 2.0 merely to obtain provenance.

### L10 — Standards are useful interoperability constraints

[W3C PROV-DM](https://www.w3.org/TR/prov-dm/) supplies concepts for entities, activities, agents and derivation. It does not require adopting RDF or a graph database. [WCAG reflow guidance](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) explains the 320 CSS-pixel requirement and limited exceptions for genuinely two-dimensional content.

**Design inference:** map versioned owner references and transformations to a provenance-compatible export; do not treat a provenance record as truth certification. Keep text, controls and evidence readable at 320px; isolate charts/tables rather than exempting the whole application. A screenshot is not an accessibility conformance test.

## 4. Architecture alternatives

### A. Layout-centric

Substantially extend `workspace_layout.v1` so it contains question, hypotheses, notes, evidence, scenarios and sharing. This initially reuses the menu and storage path, but conflates visual rearrangement with research revision, brings source rights into whole-config sharing, and makes non-chart/mobile investigations artificial. Strict current validators and migration rules mean this is not a cheap additive field change. [I08–I12]

Strongest argument for A: smallest visible concept count and direct backward familiarity. It remains appropriate for layout-only saves and for widget configuration. It loses when a single investigation has multiple views or a Thesis participates in several investigations.

### B. Investigation over existing owners and layout

Introduce a small research-intent aggregate in existing Terminal user services, referencing immutable layout revisions, Thesis versions, qualified evidence and owner-native query/alert objects. Existing storage technology, auth, tenancy and write conventions remain. The new identity is justified by a semantic gap, not by JSON size. It has no fact resolver, evidence-body store, model memory, scheduler or separate collaboration engine.

Strongest objection: a new aggregate still adds migration, permission and lifecycle complexity. It is justified only if the owner re-census confirms that no current durable question object already provides these semantics. The decision must be reversed or reduced to an adapter if such an owner is found.

### C. Graph/reference architecture as primary product

Make an investigation principally a typed graph of claims, evidence, context and relationships, with layouts as graph views. This can support competing explanations and reuse, but creates substantial risks: duplicate Evidence ownership, difficult permissions on edges and neighbors, opaque provenance propagation, mobile navigation overload and premature graph infrastructure.

Strongest argument for C: investigations often are networks, and a graph can expose connections a linear narrative misses. Retain graph projection and typed argument relations. Do not make graph traversal/storage the identity or release prerequisite without concrete use cases outperforming simpler views.

### Comparison

| Criterion | A: layout-centric | B: investigation-over-layout | C: graph-primary |
|---|---|---|---|
| Product coherence | Strong for chart work, weak for question history | Strong for question plus multiple views | Strong for relationship-heavy work, high learning cost |
| Existing owner reuse | Tempts copies into config | Explicit references and adapters | Good only with strict federation |
| Persistence/migration | Few initial seams, later oversized revisions | New small aggregate + layout history; explicit migration | Broad schema/query and projection burden |
| Duplicate-plane risk | High God-object/fact copy risk | Lowest if constrained to intent/references | Highest if a new universal evidence graph appears |
| Share/fork | Whole-config rights problem | Explicit head/revision and source entitlement checks | Edge/subgraph inheritance is complex |
| Temporal semantics | Visual and epistemic clocks collide | Separate revision vector and owner vintages | Powerful but costly bitemporal graph design |
| AI context | Easy to dump JSON, hard to qualify | Deterministic assembly from typed refs | Flexible retrieval, harder completeness/negative-evidence accounting |
| Performance | Bloated payloads/refetch risk | Bounded manifest + lazy owners | Query and neighborhood growth risk |
| Mobile | Grid-first constraints | Intent-first progressive views | Graph needs alternative linear rendering |
| Collaboration | Layout edits conflict with research | Owner-specific optimistic concurrency | Many concurrent nodes/edges and rights transitions |
| Thesis/Analysis compatibility | Duplication/renaming pressure | They remain referenced owner and entry/view | Requires careful semantic translation |
| Subject breadth | Current chart/security bias | Typed subjects through admitted adapters | High eventual breadth, more ontology burden |
| Delivery risk | Appears cheap; hidden semantic debt | Moderate, decomposable vertical slices | High early integration and adoption risk |

**Decision: B with a bounded C-style reference/argument projection.** Keep layout-only A as an existing user mode. This is an architecture recommendation for Astra to accept or amend after a bounded pickup delta review; publication alone is not a protected owner-law change.

## 5. Falsifiers and discriminating product evaluation

The thesis should be weakened if users mostly reopen only to recover chart settings, if research overhead outweighs resumption benefits, if source rights make most retained evidence unusable, or if existing Thesis plus layout references achieves equivalent results without a new identity. It should not survive merely because the mockup is attractive.

Proposed evaluation, not completed evidence:

1. Recruit 12–20 representative analysts/operators for formative work; this size is exploratory, not a statistical power claim. Compare current pages/layouts/Thesis against the thin Investigation prototype using matched security, theme and macro tasks.
2. Counterbalance task order. Include immediate interruption, 24-hour return and a one-week return. Measure time to correctly state the saved question, prior belief, evidence basis, new contradiction and next test. Record errors, not just speed.
3. Seed controlled counterevidence, a revised source, an unavailable source, a unit mismatch and a wrong AI explanation. Blind adjudicators score whether participants distinguish these. No fabricated live investment outcome is used.
4. Proposed acceptance direction: materially faster correct resumption with no increase in unsupported conclusions; demonstrably better detection of contradictions and historical contamination; tolerable creation effort. Set numeric success margins after baseline measurement and before evaluating the candidate—do not pick them afterward.
5. Instrument voluntary save/reopen, abandoned formalization, repeated baseline confusion and unwanted context-change reports. Low usage can reflect poor entry placement or weak demand; interview before assuming which.

The engineering gate remains deterministic correctness even if users prefer a more convenient misleading design. If the product hypothesis fails, retain useful owner-safe linking, evidence receipts and layout fixes rather than forcing the new aggregate everywhere.

## 6. Research-to-build decisions

The science and product evidence support bounded persistence, guided but revisable structures, explicit source scope, authored-history preservation and meaningful resumption cues. They do not establish that fully automatic contradiction resolution, universal confidence scores, graph-first navigation or unbounded AI memory are desirable.

Consequently the first commission is **private save → exact readback → cross-device reopen of a question with a versioned layout reference and truthful evidence state**, followed by generalized context and evidence comparison. It is not the entire old W2-B/W2-C backlog, a new dashboard shell, or a large standalone research platform. Full end-to-end completion still includes the later interaction, sharing, temporal, mobile and cross-product waves in the build program.
