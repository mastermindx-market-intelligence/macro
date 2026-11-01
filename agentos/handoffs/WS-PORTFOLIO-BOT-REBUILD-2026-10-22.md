---
workstream: "WS:PORTFOLIO-BOT-REBUILD"
session: "pbr-product, an Opus native domain orchestrator under the Fable seat session ed665c78-1bca-45e2-ba40-bc78b8444002 (Macro worktree pbr-agentos-f2c34d411c9f31cb)"
model: opus
ended_because: complete
mission: >
  The Fable seat's PBR commission (2026-10-22) told the PRODUCT owner to create this
  workstream in Agent OS. The goal is that the next session finds the program here
  without reading chat: what was commissioned, where the ledger is, who owns which
  files, and which holds are in force.
state_before: >
  Agent OS had no workstream for the Portfolio Bot Rebuild. The commission existed only
  in the seat's Mastermind branch: the commission directory under
  research/commission_pbr_fable_masterplan/2026-10-22/, draft PR 1695, and issue 1693.
  The closest records are WS:WATCHLIST-PORTFOLIO-CEO and WS:MARKET-OS. Both belong to
  terminal-user-services, and neither owns the paper books or the Mastermind
  app/portfolio/brain paths.
changed:
  - path: agentos/workstreams/WS-PORTFOLIO-BOT-REBUILD.md
    what: >
      New workstream on program portfolio-desk, repos [mastermind], owner
      fable-meta-ceo. Its objective restates masterplan section 12.2. It has waves W0
      to W11 with dependencies taken from WORK_PACKAGES.md (W0 done on Mastermind PR
      1695). do_not_redo holds the facts verified at commissioning and the July
      cycle-veto finding. The first landmine points to risk register A01-A16 rather
      than copying it.
  - path: agentos/handoffs/WS-PORTFOLIO-BOT-REBUILD-2026-10-22.md
    what: "This handoff."
verified:
  - claim: "Program carrier PR 1695 is OPEN and draft at head 4aa1ff76d. Issue 1693 (integrated issue + risk register) is OPEN."
    command: >
      gh pr view 1695 --repo mastermindx-market-intelligence/Mastermind --json
      state,isDraft,headRefOid; gh issue view 1693 --repo
      mastermindx-market-intelligence/Mastermind --json state,title
  - claim: "The commission's MASTERPLAN.md is the pinned copy, sha256 4c7a0d449f02de08..."
    command: "shasum -a 256 research/commission_pbr_fable_masterplan/2026-10-22/MASTERPLAN.md (Mastermind branch of PR 1695)"
  - claim: >
      The live books are under /opt/mastermind-live-data/portfolios/{autonomous,china,hk}/
      in the host namespace. mastermind.service bind-mounts that directory over
      /opt/mastermind/data, so a plain ssh listing of /opt/mastermind/data shows a
      stale July copy.
    command: "ssh -i ~/.ssh/macro_dashboard_deploy_v2 root@146.190.142.17 'systemctl cat mastermind.service' (read-only; BindPaths in the authoritative.conf drop-in)"
  - claim: >
      A read-only capture of the three books was taken for local product proof at
      07:33:06Z. The remote and local sha256 of every file agree. Nothing was written on
      the host, and no credentials were copied.
    command: "cat /Volumes/Mastermind/evidence/pbr/product-capture-20261022T073304Z/MANIFEST.json (schema pbr.product_capture.v1)"
  - claim: "Both records validate."
    command: "MACRO_MASTERMIND_REPO=<seat worktree on PR 1695 head> python3 scripts/agentos.py validate"
unverified:
  - claim: "Every figure in the risk register A01-A16 (cash residuals, the HK quantity bridge, NAV cost-as-market)."
    what_would_verify: >
      W1 and W2 under pbr-econ, re-derived from the live ledger, with each agreement or
      disagreement recorded in ORCHESTRATION.md. The audit's companion archive is not on
      the fleet.
  - claim: "Gate G0 (owned baseline) is closed."
    what_would_verify: "An ACK row from each of pbr-econ, pbr-runtime, pbr-research and pbr-product in ORCHESTRATION.md."
unresolved:
  - >
    FABLE_START_HERE.md section 1 still has a bullet saying the autonomous book uses the
    legacy data/portfolio/ storage. portfolio/registry.py data_dir() maps autonomous to
    data/portfolios/autonomous, and the live autonomous files sit under
    /opt/mastermind-live-data/portfolios/autonomous/. The seat owns that file, so the
    correction belongs to the seat.
  - >
    The p0 field is set to PRODUCT_TRUST_COHERENCE because no strategic-state P0 names
    the paper books. The seat may re-point it or propose a portfolio P0 through the
    strategic-state owner.
next_actions:
  - "Seat: close G0 once all four owner ACK rows are in ORCHESTRATION.md, then set W0's note to cite the closing ledger row."
  - "Seat: review and merge this Macro PR. It is reserved for the seat; the PRODUCT owner does not merge it."
  - "Each domain owner updates its wave status and next_action at wave boundaries only (1-2 fields)."
do_not_redo:
  - >
    Do not create a second workstream for this program or per-domain workstreams. The
    four owners are rows in ORCHESTRATION.md and waves here, not separate Agent OS
    records.
  - >
    Do not copy the A01-A16 register into Agent OS. It has one home: masterplan section
    4 and issue 1693.
danger_areas:
  - >
    Wave pr numbers in the workstream are Mastermind PRs (1695, 824, 726-728, 1147, 673,
    1357). The status view's PR index is built from Macro build data, so a Macro PR with
    the same number could be misread as this wave's carrier. Read state with
    gh pr view N --repo mastermindx-market-intelligence/Mastermind.
  - >
    The commission directory exists only on the PR 1695 branch until it merges. Validate
    with MACRO_MASTERMIND_REPO pointing at a checkout of that head, or the artifact paths
    warn as phantoms.
prs:
  - "mastermindx-market-intelligence/Mastermind#1695"
---

# Summary

PBR was commissioned on 2026-10-22. The Fable seat holds judgment and acceptance. Four
Opus domain orchestrators hold the write families:

- **pbr-econ:** W1 and W2.
- **pbr-runtime:** W4.
- **pbr-research:** W5 and W6.
- **pbr-product:** W9 and this record.

Labor runs on admitted pool lanes. The ledger is ORCHESTRATION.md in the commission
directory on Mastermind PR 1695.

Standing holds: live data is read-only, with no reset, balancing fill or repair trade.
The V2 marker, the August-11 cohort and pending targets are preserved. Shadow work stays
in isolated storage. Merged, installed and accepted are reported separately, and
installed identity is proven only by blob comparison. Every checkpoint reports three
verdicts: operationally correct NOT YET, economically qualified NOT YET, and investment
value INCONCLUSIVE.
