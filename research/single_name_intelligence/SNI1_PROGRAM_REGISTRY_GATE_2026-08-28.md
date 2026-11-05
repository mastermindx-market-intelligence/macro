# SNI-1 Canonical Program Registry Gate

**Date:** 2026-08-28  
**State:** OPEN ARCHITECTURE GATE  
**Authority:** records only; no implementation or runtime effect  

## Finding

The SNI-0 and SNI-1 research architecture establishes a coherent new cross-owner product and research program, provisionally named `single-name-intelligence`. The canonical semantic registry inspected on 2026-08-28, `config/mastermind_programs.yml`, did not contain that program key. The receiver must inspect the actual registry at future execution and derive its then-current keys/counts; this dated observation is not proof of current absence or an instruction to duplicate an existing owner.

Agent OS workstreams hard-fail when their `program` key is absent from the canonical registry. Registering the new SNI workstream under `market-timing-intelligence`, `fundamental-forensics`, `earnings-intelligence`, `china-system`, or another convenient existing key would be semantically false:

- SNI does not own only tactical timing;
- SNI does not own only filings/fundamentals;
- SNI does not own only earnings;
- SNI is not limited to China/Hong Kong;
- SNI is a composition/research/product layer over all of those owners.

Therefore the draft `WS:SINGLE-NAME-INTELLIGENCE-OS` and its dependent handoff were removed from the SNI-1 carrier before PR review rather than forcing an invalid program mapping.

## Required decision after SNI-1 written-spec approval

Before creating the durable Agent OS workstream or beginning SNI-1A implementation, Sol must make one explicit semantic-registry ruling:

### Recommended

Register `single-name-intelligence` as a new **project-scope intelligence program** whose role is:

- reference-twin composition over canonical issuer and instrument owners;
- single-name experience architecture;
- stock-specific residual/response/forecast research;
- forecast-memory projection through existing qledger/Evaluation OS;
- no upstream truth-plane ownership and no trade authority.

It should consume from, not contain or replace:

- `fundamental-forensics`;
- `earnings-intelligence`;
- `capital-structure-intelligence`;
- `market-timing-intelligence` / Stock Identity;
- `china-system`;
- `options-intelligence`;
- `neural-web` / graph/context owners;
- `terminal-market-data` and `terminal-charting` for product composition.

### Alternative

If the canonical semantic-system review finds an already-existing program whose stated purpose genuinely includes issuer + instrument twin composition, premium single-name product ownership, and cross-horizon learning, SNI should be an explicit subprogram/extension of that owner rather than minting a new key.

No such existing owner was found in the 2026-08-28 SNI-1 inspection. Reconcile any later accepted registration or owner amendment before choosing either path.

## Acceptance evidence

The program-key decision is complete only when:

1. `config/mastermind_programs.yml` contains the accepted key and boundaries;
2. generated semantic-system validation passes;
3. `scripts/agentos.py validate` accepts the new SNI workstream;
4. the registry entry names canonical consumers/owners without duplicating their stores or authority;
5. the SNI-1 implementation plan cites the accepted program key.

## Non-goals

This gate does not block Chairman review of the SNI-1 architecture. It blocks only:

- pretending the organizational workstream is valid before registration;
- implementation planning that cannot name its canonical program owner;
- routing SNI under an architecturally false existing program.

The SNI research/spec files and `DSC:SNI-HK-MULTI-COUNTER-IS-NOT-MULTI-SECURITY` remain durable and independently valid while this gate is open.
## Current continuation boundary

The 2026-11-05 repair folds the existing identity amendment within PR #6613's nine
paths. It does not register a program or create a live workstream. First verify
actual protected-main acceptance of the qualified #6613 head, then resolve this
registry decision and the existing stacked #6615 carrier under current custody.
A PRECOMMISSION plan is not START; preserve actual live writers and uncertain
effects without turning an old named seat into an approval requirement. Written
architecture review remains independent of registration.
