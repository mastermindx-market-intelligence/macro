---
key: F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE
question: >
  Who commissions the options payoff and structure consumer now that the
  Options Intelligence C0 program is terminal?
answer: >
  The Meta-CEO A seat charters W2-5 as normal Market Ontology packets.
  W2-5a is the producer on the store host (this change). W2-5b is the
  consumer surface and ships after the producer is live. Issue 6604 is
  removed as a dependency, under the 2026-09-06 charter clause A-F03-1/2.
rationale: >
  engine/options_payoff.py landed in pull request 6935 and had no consumer.
  The rows MO-DELTA-034 and MO-PAID-077 had been marked absorbed by issue
  6604. That program is terminal: the 2026-08-28 consolidated masterplan
  is records only and starts no implementation wave. Render hosts do not
  hold the ThetaData store, so the same split already used for the skew
  ledger applies here. The store host computes the frozen index-ETF catalog
  and publishes the JSON to R2. Render hosts only read that file. The
  artifact is display-tier research expression. It has zero entry authority.
  The plist can be installed and removed by the seat.
alternatives:
  - option: Wait for a successor to the C0 program
    why_not: >
      No successor is chartered. Leaving the payoff engine with zero
      consumers keeps MO-DELTA-034 at built-but-not-proven.
  - option: Compute the payoff catalog on the render hosts
    why_not: >
      Render hosts do not hold the ThetaData store. Hydrating it there
      repeats the failure mode the skew lane already rejected
      (DEC:SKEW-ACCRUAL-ON-THE-STORE-HOST).
  - option: A live or intraday payoff surface
    why_not: >
      That surface belongs to WS:INTRADAY-FLOW-P0-RECOVERY and is out of
      scope for this end-of-day catalog.
evidence:
  - "MO-DELTA-034: Structure Builder strategies plus P and L, scenario, and
    Greeks drift were built but not proven. engine/options_payoff.py landed
    in pull request 6935 with zero consumers."
  - "MO-PAID-077: the P and L surface was partial, and both rows had been
    marked absorbed by issue 6604."
  - "DEC:OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL and
    research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md:
    the C0 program is records only and starts no implementation wave."
  - "research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md clause
    A-F03-1/2: if issue 6604 is stale or terminal, A converts the rows into
    normal packets, removes 6604 as a dependency, and records that choice
    as a DEC."
  - "DEC:SKEW-ACCRUAL-ON-THE-STORE-HOST: the store host computes and
    publishes; render hosts hydrate and emit. This packet follows that split."
affects:
  - "engine/options_payoff_lab.py"
  - "scripts/build_options_payoff_lab.py"
  - "ops/launchd/com.macro.payofflab.plist"
  - "ops/launchd/run_options_payoff_lab.sh"
  - "scripts/publish_r2.py"
confidence: high
reversibility: easy
decided_by: "META-CEO A seat, packet A-F03-W2-5a, 2026-09-23"
decided_at: 2026-09-23
---

The seat installs the launchd agent on the store host after merge. Until
that install, the plist is only a file in the repo. W2-5b, the page that
reads `site/options_payoff_lab/latest.json`, is a later packet.
