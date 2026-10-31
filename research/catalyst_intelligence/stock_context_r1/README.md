# Catalyst Intelligence: stock context research consumer R1

## Capability and state

This implementation connects a supplied peer research cohort to the existing NewsImpact thesis projector and Prophet B4 validator. It answers how the focal stock moved relative to the observed peers, which peers have shared or comparable owner-classified events, what the existing news owner reports changed, and what the existing entry owner currently says.

**State: built research consumer, not activated or source-admitted.** The CLI is a real consumer, and its integration fixture invokes actual owner code. The membership, prices, source cuts and rights references in that fixture are synthetic. This implementation does not prove authentic historical membership, source-use rights, live delivery, causal spillover or a profitable entry policy.

Baseline: Macro `97261c2a319e62faec05690c04e6fae180540235`. Governing Mastermind source pin: `bcf4a2f72538682f2fbe4902f6417e59cd038678`. User mandate expanded on 2026-10-19 to backend research, implementation, technical/entry integration, changing drivers, sector context and competitor behavior.

## Run

Use Python 3.12 with `pytest jsonschema pandas pyarrow pyyaml requests` for the owner import closure.

```sh
python -m pytest tests/test_catalyst_stock_context.py -q
python -m engine.catalyst_intelligence < research/catalyst_intelligence/stock_context_r1/fixtures/owner_request.json > /tmp/catalyst-stock-assessment.json
```

The executable reads at most 4 MiB of JSON from stdin and writes a derived JSON packet to stdout. It performs no network operation, publication-pointer update, source-store write, selection, portfolio operation or trade. Existing NewsImpact code reads its checked-in schema files.

## Implemented behavior

- `engine/catalyst_intelligence/peer_context.py`: exact supplied identity bindings; frozen formation-time membership; synchronized return endpoints; currency/basis agreement; decision-time availability; whole-focal-issuer exclusion; explicit treatment of other share-class ambiguity; observed-subset and complete-cohort aggregates; breadth, dispersion and source-linked exclusions.
- The eligible issuer denominator survives missing prices. The full-cohort aggregate stays null on incomplete coverage. Exact duplicate graph-path rows collapse; contradictory bindings require reconciliation.
- Catalyst comparisons use explicit owner namespaces and owner-supplied comparison keys. Same native text under different owners does not establish event identity or economic similarity.
- All decision-visible revisions are reconciled before the price-window filter. Conflicting current revisions, including an out-of-window current/terminal conflict, refuse. Observed superseded or withdrawn history remains visible and cannot become an assertion that no event was observed.
- `assessment.py`: validates and attaches the original B4 projection unchanged, binding security, identity epoch, evaluation cut and strategy/horizon. Missing or different-cut B4 never creates a positive replacement. The current accepted strategy's `CONTROL_ONLY` / `SHADOW_ONLY` scope is disclosed.
- News changes invoke `engine.news_impact.thesis.project` with explicit current **and historical** owner bundles. The current bundle cannot stand in for the prior one. Owner triggers retain their original meanings; there is no new news sentiment scorer or parallel correction fold.
- Every derived packet has deterministic input/content digests and detached JSON values. All authority flags remain false. Source references and digests establish supplied-input consistency only.

The demonstration has an invented +12% focal return, +1% mean across three observed peers, two advancing peers and one declining peer. Its real B4 fixture evaluates to `RAN_DONT_CHASE`; increasing peer returns cannot alter that state. NewsImpact produces its own thesis and change triggers. These are fixture outputs, not findings about current stocks.

## Owner boundaries

| Concern | Owner | R1 relationship |
| --- | --- | --- |
| Company and security identities | Data OS / existing issuer and listing owners | Supplied explicit identity references; no joins inferred here |
| Theme identity, hierarchy and membership | GMI `engine/theme_graph` | Supplied research cohort only; native formation/source admission is not yet connected |
| Qualified economic exposure | Existing company/theme and relationship owners | Required for later economic read-through; thematic paths alone are insufficient |
| News facts, revisions, thesis changes | `engine/news_impact/thesis.py` | Actual projector called with separate cuts |
| Entry availability | `engine/prophet_entry_availability.py` | Existing validator called; source output preserved |
| Live Radar catalyst context | `engine/entry_radar/catalyst_context.py` | Existing future episode attachment seam retained |
| Sector attention | Existing Catalyst-to-Opportunity #9552 | Future admitted input; its source/publication is not duplicated |
| Bio event and WMN publication | Existing #6712 | Existing source/holds/dirty work preserved |

GMI `ontology.py::RepositoryStore` / `compose_neighborhood` and `structural_navigation.py::hierarchy_paths` expose existing recorded relations. They do not establish economically comparable all-subtheme membership. A finalized selection cohort must be read through `selection_cohort_publication.py::read_finalized_cohort` or `consume_us_source`, preserving its rights and generation checks. It remains a selected-board cohort, not every stock in a subtheme.

## Verification and limits

The 43 focused tests cover self/issuer exclusion, ambiguous listings, frozen and future membership, mismatched clocks/basis/currency/identity, missing coverage, nonfinite prices, common moves, separate event namespaces, shared versus distinct comparable catalysts, correction conflicts outside the price window, retained withdrawn history, owner absence, historical snapshots, B4 immutability and the real CLI replay.

Independent principal review found two catalyst revision defects before acceptance; both were repaired with discriminating tests. See `verification.json` for the exact source hashes and commands. Hosted checks and release state belong to the PR's current head, not this static count.

R1 accepts strictly positive endpoint values. A zero terminal value refuses; a future historical-loss study must add a source-qualified terminal/delisting representation and preserve those issuers in its population. It must never silently omit bankrupt or delisted outcomes. R1 has no market-calendar synchronization adapter, authenticated acquisition, live invalidation graph, source-rights resolver, all-market peer discovery, factor residual, predictive lead/lag or causal attribution. See `PROGRAM_PLAN.md` for the completion path.

## Execution custody

The root principal is the sole writer of this operation. Exact discovery exposed read-only Fabric projections but no callable pre-effect worker-request route; no paid worker was started or left with uncertain effects. Bounded direct implementation proceeded under `NO_ELIGIBLE_PRE_EFFECT_WORKER`. Native children supplied C3 scientific/ownership review only, without source changes or routine execution. The managed workspace was acquired through `mmx-workspace` as `catalyst-stock-context-r1-20261019`; no incumbent worktree was modified for this package.

Release remains separate from this research implementation. No source or display admission flag may be changed because the arithmetic or tests pass.
