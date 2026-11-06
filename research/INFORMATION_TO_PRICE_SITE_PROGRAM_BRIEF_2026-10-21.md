# ITP SITE MATERIALIZATION — frozen program brief (seat 2fc05761, 2026-10-21)

Chairman directive 2026-10-21: complete Information→Price fully; design-perfected front end
(Paper mockup upgraded to masterpiece before implementation); orchestrate for quality AND
token efficiency (Opus orchestrators commission GLM fabric lanes; no Opus labor); fix or
sidestep blockers; do not wait for orphaned owners; best possible site materialization,
useful to users and valuable to backend systems.

## Landed science (DO_NOT_REDO)
- SRC-A1 collector `collectors/equity_revisions.py` → `data/revisions/expectation_observations.parquet`
  (473,200 obs on origin/main 562fc7dd02a95792c1a3f59dee2e147f5ffddf20; columns incl.
  attempt_id, collection_session_id, provider, provider_record_class, ticker_compat,
  issuer_ref, security_ref, metric {EPS,revenue}, horizon_label_raw, period_end,
  fiscal_period, fiscal_year, observation_type {average,median,high,low,
  covering_analyst_count,growth,year_ago}, value, unit, source_effective_at,
  source_published_at, provider_observed_at, attempted_at, missingness_reason)
  + `expectation_attempts.parquet`; aliases `data/reference/vendor_aliases.parquet`.
  Lanes MUST inspect the real parquet dtypes before coding (sparse tree:
  `python3 scripts/worktree_sparse.py add data/revisions` and `add data/reference`).
- EXP-1 reader `engine/k3e_expectation_surface.py::inspect_expectation_surface`
  (schema k3e.declared_capture_inspection.v1); MKT-1 `engine/price_pressure/response_export.py`;
  CPL-1 `engine/k3e_coupling.py::compose_descriptive_coupling`.
- R1 identity = COMPLETE_DEGRADED (DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07): 724 unresolved
  names, 777 undated aliases excluded. D57 DEC:ITP-R5-NO-DURABLE-APPEND-2026-10-07: no new
  ledger/store/queue — site JSON is a regenerated render artifact, never a ledger.

## Reserved controls (bind every lane)
No rank/gate/size/trade/capital authority; `financial_influence:false`,
`k3e_admissible:false` on every emitted record; no invented signals; EVAL-1 never read;
no LLM-originated numbers; identity/source-clock safeguards preserved; nightly law:
render lanes never write data/; ZH uses 披露 for filings (the reserved alternative term is banned by check_zh_filing_term.py); no colored left-edge accent stripes
(CLAUDE.md permanent rule); dual theme; EN/ZH via `t()`; `templates/_navlinks.html.j2`
NOT touched in wave 1 (41 suites pin it); `data/` and `site/` never committed on the branch.

## Product (frozen for wave 1)
Page `site/expectation_surface.html` ("Expectation Surface" — the consensus layer of
Information→Price), builder `scripts/build_expectation_surface.py` (pattern:
`scripts/build_finance_intelligence_page.py` / `scripts/build_intel_hub.py`;
`from lib.pages import write_page`; registered additively in `scripts/build_site.py`
inside try/except like `_render_finance` near line 8403), template
`templates/expectation_surface.html.j2` (uses the authenticated header family exactly
like `templates/intelligence_hub.html.j2`), JSON under `site/expectation_surface/`.

Sections (DOM ids frozen so UI and data lanes do not collide):
- `#es-hero` title + one-line promise + status chips: Descriptive · not a signal | Identity
  COMPLETE_DEGRADED | Source snapshot <latest collection session UTC> | Rendered <UTC>.
- `#es-census` tiles: observations, securities, metrics, horizons, sessions, date span,
  median covering analysts, identity (resolved / unresolved 724 / undated 777 from aliases).
- `#es-breadth` revision breadth per collection session (up / down / flat counts of
  `average` consensus changes across the universe, per metric) — chart + table.
- `#es-movers` consensus revision tape latest-vs-prior session: top up/down movers by
  |pct change| of `average`, per metric, with horizon, period_end, prior, latest, analysts,
  clocks; explicitly labeled "sorted by magnitude · descriptive".
- `#es-explorer` client-side ticker search over `tickers/index.json`; per-ticker panel loads
  `tickers/<T>.json`: consensus path per metric×horizon (average/median/high/low/analysts
  per session) + identity status.
- `#es-method` provenance: schema ids, source revision/blob ids, decisions (DEC keys),
  "what this is not" (no rank/gate/size/trade/capital), link to research program.

Data contract (frozen):
- `summary.json` {schema:"expectation_surface.page.v1", rendered_at, financial_influence:false,
  k3e_admissible:false, source:{observations_path, source_revision, latest_session:{id,at},
  prior_session:{id,at}}, identity:{state:"COMPLETE_DEGRADED", resolved, unresolved,
  undated_aliases}, census:{observations, securities, metrics[], horizons[], sessions,
  span:{first,last}, analysts_median}, breadth:[{session_id, at, metric, up, down, flat}],
  movers:{EPS:{up[],down[]}, revenue:{up[],down[]}} item {ticker, horizon, period_end,
  prior, latest, pct_change, analysts, prior_at, latest_at}, state:"LIVE"|"OFFLINE", reasons[]}
- `tickers/index.json` [{ticker, sessions, latest_at, identity_status}]
- `tickers/<T>.json` {ticker, identity_status, series:{EPS:{<horizon>:[{at, average, median,
  high, low, analysts}]}, revenue:{…}}}
Degrade-safe: missing parquet → state OFFLINE, empty arrays, page still renders with an
honest offline band; builder never raises into build_site. Render budget: builder < 60 s.

Wave 2 (after wave 1 merged): CPL-1 market coupling panel for movers (owner_state from
price_pressure), Intelligence Hub desk card + Research nav item (separate PRs with the
pinned-suite audit), per-security page link-out.

## Lanes
- ORCH-ITP-DESIGN (Opus orchestrator, native — Paper MCP is only reachable natively; design
  judgment is opus-tier by doctrine): Paper page in MASTERMIND PAGES
  (fileId 01M2WGNCX9475G79JRKJTCM08P) "Expectation Surface" 1440 + 390, dark + light,
  EN + ZH; returns frozen visual spec file + exported HTML/CSS in the seat scratchpad.
- ORCH-ITP-BUILD (Opus orchestrator): commissions glm-5.3-flash fabric lane BUILD-DATA
  (builder + JSON contract + tests + CI registration + semantic template skeleton), judges
  the return, then BUILD-UI lane from the design spec.
Seat keeps: merges, carrier posts, acceptance, memory/handoff writes.

## Registration facts (verified in-tree 2026-10-21)
- A root page emitted by `write_page(site / "expectation_surface.html", …)` from
  `scripts/build_expectation_surface.py` is auto-discovered as `generated` by
  `scripts/build_product_page_registry.py::scan_write_sites`; `lib/pages.py`
  `HAND_AUTHORED_PAGES` is only for committed-site-file pages and must NOT gain the page.
- The registry reads git-tracked `site/*.html`, so the page row appears after the nightly
  render commits the file (branch never commits `site/`).
- Every new test suite must be named by a `run:` step in `.github/ci/legacy-jobs.yml`
  (pattern: the finance_intelligence page job declaring template/builder/test/site paths);
  an uncovered registration reds every pack.

## Lane matrix (seat 2fc05761)
| lane | carrier | state at write |
|---|---|---|
| ORCH-ITP-DESIGN | native Opus orchestrator → Paper "Expectation Surface · R1" | RUNNING |
| ORCH-ITP-BUILD → BUILD-DATA | Opus orchestrator → glm-5.3-flash fabric lane `itp-es-build-data-20261021-r1`, branch `claude/itp-expectation-surface-2026-10-21` | RUNNING |
| BUILD-UI | fabric lane from the design spec, same branch, after both returns | NOT STARTED |
