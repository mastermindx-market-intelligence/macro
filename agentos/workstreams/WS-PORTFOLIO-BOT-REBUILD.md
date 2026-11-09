---
schema: agentos.workstream.v1
key: PORTFOLIO-BOT-REBUILD
title: Portfolio Bot Rebuild (PBR) — economic truth, reliable management, evidence-first product
objective: >
  Rebuild the autonomous, china and hk paper books into an engineered paper system
  whose numbers can be defended. The program is complete only when all three active
  books carry qualified current economics, every manager cycle is accountable, execution
  assumptions are realistic, lineage from snapshot to claim to target to outcome is
  reliable, the product is proven in an authenticated browser, experiments run in
  isolation, and incidents have a documented rollback path. The investment upgrade is a
  separate result. It is accepted only for its tested scope and only when its
  predeclared evidence criteria are met. Tilts that fail are removed or narrowed, and
  specialists that add nothing are removed. If no credible edge is proven, the product
  says so and limits its claim to supported research, disciplined simulation and
  decision accountability (masterplan section 12.2).
status: active
program: portfolio-desk
# No strategic-state P0 names the paper books directly. PRODUCT_TRUST_COHERENCE is the
# closest active objective: the program's user-facing failure is a product that shows
# numbers it cannot defend. The seat may re-point this field.
p0: PRODUCT_TRUST_COHERENCE
repos: [mastermind]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - mastermind:research/commission_pbr_fable_masterplan/
artifacts:
  - mastermind:research/commission_pbr_fable_masterplan/2026-10-22/FABLE_START_HERE.md
  - mastermind:research/commission_pbr_fable_masterplan/2026-10-22/MASTERPLAN.md
  - mastermind:research/commission_pbr_fable_masterplan/2026-10-22/WORK_PACKAGES.md
  - mastermind:research/commission_pbr_fable_masterplan/2026-10-22/ORCHESTRATION.md
  - macro:agentos/handoffs/WS-PORTFOLIO-BOT-REBUILD-2026-10-22.md
landmines:
  - >
    Risk register A01-A16 lives in masterplan section 4 (MASTERPLAN.md, "Defect and
    hypothesis register") and in mastermindx-market-intelligence/Mastermind#1693. It is
    not copied here, so it has one writer. Every A-row is the audit's claim until a
    domain owner re-derives it from the live ledger.
  - >
    One writer per artifact family (FABLE_START_HERE.md section 3). ECON (pbr-econ)
    owns portfolio/paper_account.py, portfolio/marks.py, portfolio/price_evidence.py,
    bot/settle.py and portfolio/benchmark*.py. RUNTIME (pbr-runtime) owns provider,
    scheduler and manager-cycle lifecycle. RESEARCH (pbr-research) owns
    brain/decision_context.py, brain/decision_submission.py and the thesis, claims and
    shadow modules. PRODUCT (pbr-product) owns app/web.py, app/static/**, app/account.py,
    app/pfolio.py and app/decision_availability*.py. A change outside a family is a
    contract request, never a competing write.
  - >
    The VPS (root@146.190.142.17) is production and the authoritative writer of the
    books. Every lane reads it read-only. Never rsync or scp toward it, and never run
    the bot against live data.
do_not_redo:
  - >
    Do not treat data/deploy_lag.json as installed identity. At commissioning it named
    head 131290a0, which is 985 commits behind origin/master. /opt/mastermind is not a
    git checkout, so installed identity is proven only by comparing installed file blobs
    against origin/master (FABLE_START_HERE.md section 1).
  - >
    Do not report Mastermind PR 1614 (merged 43f83e068) as installed. On 2026-10-22,
    portfolio/price_evidence.py was absent from the VPS tree. Merged, installed and
    accepted are three separate claims.
  - >
    Do not read the books from /opt/mastermind/data over plain ssh. That path shows a
    stale July copy. mastermind.service carries
    BindPaths=/opt/mastermind-live-data:/opt/mastermind/data, so the live books are at
    /opt/mastermind-live-data/portfolios/{autonomous,china,hk}/ in the host namespace.
    portfolio/ there is the Aug-10 legacy flagship directory, not the autonomous book
    (verify with: ssh root@146.190.142.17 systemctl cat mastermind.service).
  - >
    Do not reset an account, rewrite a seed, post a balancing fill or place a repair
    trade. An adjustment is an event with a type, reason, evidence, effective time,
    recorded time and reviewer. Book ids, the V2 marker (sha256 75d5182d...), the
    August-11 cohort, baseline exclusions, lessons, archived books and pending
    targets/receipts are preserved.
  - >
    Do not repeat the full audit archaeology. Carriers were census-verified at their
    audit heads on 2026-10-22 (#1357, #673, #1147, #824, #726, #727, #728, #1432,
    #1434; issue #1433). Re-read a carrier only when its head moves. The audit's
    companion archive (R1-R9 JSON, reproduce_audit.py) is not on the fleet, so W1
    re-derives every figure from the live ledger and records whether it agrees.
  - >
    Do not revive the July sector-peak cycle veto as a default exit rule. Its reported
    test reduced the leadership strategy's CAGR and Sharpe. The July defensive-
    outperformance comparison rested on three trading days. Reopening the veto requires
    a new preregistered hypothesis and independent evidence (MASTERPLAN.md section 5.1).
waves:
  - id: W0
    title: Commission and baseline — audit adopted, owners and heads reconciled, issue and risk register published
    status: done
    pr: 1695
    # Mastermind PR 1695 is the docs/ledger carrier (draft at 2026-10-22); issue 1693
    # holds the integrated risk register. Gate G0 closes when all four domain owners
    # ACK their scopes in ORCHESTRATION.md.
  - id: W1
    title: Account truth — HK quantity bridge, dated cash residuals, seed and corporate-action history
    status: in_progress
    depends_on: [W0]
    next_action: "pbr-econ: per-book quantity/cash/wealth bridge from the live ledger; no balancing trades."
  - id: W2
    title: Prices and replay — close cost-as-market NAV, direction-aware known-at, reconcile 824, prove 1614 consumption
    status: in_progress
    pr: [824, 726, 727, 728]
    depends_on: [W0]
  - id: W3
    title: Economic simulator — native-currency cash and cost events, corporate actions, venue lots, feasible fills
    status: todo
    depends_on: [W1, W2]
  - id: W4
    title: Reliable management — no-submission failure chain, lifecycle disposition projection, installed-identity proof
    status: in_progress
    pr: 1147
    depends_on: [W0]
  - id: W5
    title: V3-S0 evidence — immutable point-in-time snapshot bound to the actual account and pending effects
    status: in_progress
    pr: [673, 1357]
    depends_on: [W0]
  - id: W6
    title: PM views and claims — typed fact checks, durable thesis and amendments, evidence-conditioned risk budget
    status: in_progress
    pr: 1357
    depends_on: [W5]
  - id: W7
    title: Construction — risk anchor, uncertainty-conditioned budgets, bounded tilts, feasibility, stability (shadow only)
    status: todo
    depends_on: [W3, W5, W6]
  - id: W8
    title: Outcomes and experiments — fill/episode/source attribution, trial registry, paired evaluation
    status: todo
    depends_on: [W1, W3, W5]
  - id: W9
    title: Coherent product — actual, decision, pending, performance, opportunities, position-review and operations views
    status: in_progress
    depends_on: [W0]
    next_action: "pbr-product: route/API/field census, then frozen seven-view spec for seat design acceptance; truthful partial views may ship earlier."
  - id: W10
    title: Prospective shadow — challenger and frozen incumbent through the same qualified simulator, zero live effects
    status: todo
    depends_on: [W3, W4, W5, W6, W7, W8, W9]
  - id: W11
    title: Investment review and cutover — decide limited paper-policy authority, migrate only the qualified version
    status: todo
    depends_on: [W10]
next_action: >
  Close gate G0: each of pbr-econ, pbr-runtime, pbr-research and pbr-product ACKs its
  scope in mastermind:research/commission_pbr_fable_masterplan/2026-10-22/ORCHESTRATION.md
  (Mastermind PR 1695). Then run W1, W2, W4, W5, W6 and W9 in parallel under their
  owners. Three verdicts at every checkpoint: operationally correct NOT YET,
  economically qualified NOT YET, investment value INCONCLUSIVE.
---

# Portfolio Bot Rebuild

The Chairman commissioned this program on 2026-10-22 to the Fable Meta-CEO seat. It
adopts the 2026-10-21 portfolio audit and rebuild masterplan as its baseline. The
masterplan is MASTERPLAN.md in the commission directory, sha256 4c7a0d44..., 804 lines.

The seat keeps strategic judgment, cross-domain arbitration and final acceptance. Four
domain owners hold the write families. Bounded labor runs on admitted fabric lanes through
the pool kit, because Executive MCP ingress needs OAuth this session.

Where to look:

- **Program issue and risk register:** mastermindx-market-intelligence/Mastermind#1693.
- **Docs and ledger carrier:** mastermindx-market-intelligence/Mastermind#1695.
- **Packet owners and status:** WORK_PACKAGES.md.
- **Run ledger:** ORCHESTRATION.md.
- **Lane packets and review verdicts:** `lanes/<DOMAIN>/` beside them.
