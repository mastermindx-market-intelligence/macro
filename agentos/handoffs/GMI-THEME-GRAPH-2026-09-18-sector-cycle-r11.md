---
workstream: WS:GMI-THEME-GRAPH
session: sol/sector-cycle-r11-identity-gate-20260918
model: sol
ended_because: ci_handoff
mission: >
  Prevent remaining typed identity nulls from unnecessarily blocking the first real
  Atlas while preserving Data OS as canonical security/issuer authority and refusing
  ticker-string overlap, guessed identities or issuer laundering.
state_before: >
  R10 measured 695/701 complete identities before the FI/FISV repair. #7299 healed
  Fiserv but initially left the derived GMI sidecar stale. #7284 remains the candidate
  upstream membership repair and P1 release remains held pending that source truth.
changed:
  - path: research/sector_cycle_revamp/R11_IDENTITY_GATED_ATLAS_ADMISSION_2026-09-18.md
    what: >
      Split group/member measurement admission from identity-dependent feature admission;
      quantify the five unresolved identities and make overlap/drill-through semantics
      fail closed without removing groups from the source measurement population.
  - path: agentos/handoffs/GMI-THEME-GRAPH-2026-09-18-sector-cycle-r11.md
    what: >
      Preserve the exact input carriers, product-law ruling, remaining typed identity
      failures, derived GMI sidecar closure and post-source-gate implementation frontier.
verified:
  - claim: >
      Corrected 701-symbol candidate has 696 complete owner-composed identities and
      1,015/1,020 resolved membership appearances after the FI/FISV repair.
    command: >
      Run scripts.security_state_producer::_read_security_state_identity_rows over the
      #7284 candidate active union using #7299 Data OS artifacts at decision date
      2026-09-18.
    result: >
      696/701 distinct symbols resolved (99.2867%); 1015/1020 appearances resolved
      (99.5098%); failures are ANGPY, B, CBOE, IMPUY, RHHBY; post-FI evidence receipt
      SHA256 571317a64ce278252c6cf293a195ce7d3494e0f73fb8ef3b8bb9c96874985c17.
  - claim: >
      Identity completeness is representation-local: all but four groups have complete
      identity coverage, while source-member breadth remains defined independent of
      issuer identity.
    command: >
      Join corrected active membership appearances to the existing owner-composed
      identity results without changing the population.
    result: >
      pgm_miners=2/4, gold_miners=11/12, obesity_glp1=13/14,
      us_sector_financials=75/76; every other group=100% identity.
  - claim: >
      Security count and issuer count are materially different even with full identity.
    command: >
      Group resolved security IDs by canonical issuer ID inside the corrected candidate.
    result: >
      us_sector_comm has 24 resolved member securities but 21 unique issuers because
      FOX/FOXA, GOOG/GOOGL and NWS/NWSA share issuer IDs.
  - claim: >
      #7299's Data OS heal is consumed by the canonical GMI identity bridge without
      rewriting graph topology.
    command: >
      Directly re-derive identity_resolution from committed nodes and healed Data OS
      for graph belief-time 2026-09-17; run reproducibility/strict/seam tests.
    result: >
      One 2807-row sidecar generation appended; nodes/edges/evidence/capability/_meta
      hashes unchanged; FI/FISV issuer resolved; reproducibility pass; 53 relevant GMI
      identity tests + 55 seam/contract tests pass; strict graph contract exits 0.
unverified:
  - claim: #7284 source truth is accepted/protected-main.
    what_would_verify: >
      Exact-head/current-base CI and required review/release complete on the same PR;
      current candidate head is 4c36666287eb36721b258ff55ccf53a04bc52dc5.
  - claim: #7299 FI/FISV identity repair is accepted/protected-main.
    what_would_verify: >
      Exact-head/current-base hosted CI and independent source review complete on
      b405ad51f94d019ffd5ea10eb81c90d97f40f0ee, then protected merge/readback.
  - claim: Current P1 proof is valid for the corrected 701-symbol source.
    what_would_verify: >
      #7252 reconciles accepted #7284 on its existing carrier and regenerates only
      population-dependent P1 evidence without reopening completed semantic work.
unresolved:
  - >
    ANGPY, IMPUY and RHHBY remain typed no-current-store/security-master identity cases.
  - >
    B remains the existing fail-closed ticker-reuse/identity-continuation problem.
  - >
    CBOE has current listing/CIK evidence but BATS venue code Z is outside the closed
    Data OS MIC vocabulary; the natural owner path currently source-collides with #6712.
  - >
    #7284, #7278, #7299, #7252 and #7211 remain independent open carriers with hosted
    execution/release gates; no rerun/cancel/new runner is authorized by R11.
  - >
    Current Macro base carries unrelated stale Data OS/GMI fixture assertions; do not
    repair them opportunistically inside FI/FISV or Atlas product work.
next_actions:
  - >
    Consume #7284 and #7299 hosted exact-head returns through GitHub; do not manually
    rerun stable workflows.
  - >
    After #7284 acceptance, regenerate only #7252 population-dependent evidence and
    refresh the R9 compact projection from the accepted 701-symbol source.
  - >
    After P1/publication acceptance, build one existing-owner compact Macro projection
    plus signed-in Terminal consumer using the R11 identity-local gating rules.
  - >
    Keep CBOE, B and ADR/OTC identity repairs independent; none may invent an Atlas-local
    identity plane or block truthful group-level representations.
do_not_redo:
  - R1-R10 competitor/product research, cap archaeology and population/identity censuses.
  - P1 source/math/visual review already completed before the membership invalidator.
  - #4622 FI/FISV stable-key adjudication and #7299 RED/GREEN/adversarial tests.
  - The 701-symbol identity coverage census and the 2807-row GMI sidecar re-derivation.
  - Any second identity resolver, membership authority, cap cache, publisher or CI queue.
danger_areas:
  - >
    Group Pulse/P1 breadth is member-security-grain. Canonical issuer identity must not
    silently deduplicate or change its denominator.
  - >
    A 100% resolved ticker list can still contain fewer issuers than securities; label
    member count and issuer count separately.
  - >
    Incomplete identity may disclose known overlaps with coverage denominators but may
    not produce a full independence/diversification scalar.
  - >
    R11 is research law, not Atlas implementation admission; upstream source/publication
    gates remain real.
prs: [7234, 7284, 7278, 7299, 7252, 7211]
---

## Continuation boundary

Protected procedure at this ruling: Mastermind
`61a2ff79aba4e8a5685e779707ad5c4426cf5cc5`, Skillpack 1.0.1.

R11 changes product admission semantics only. It does not modify membership, Data OS,
P1, publication, Terminal, cap data, trade authority or provider rights.

The next implementation vertical remains held until the accepted source/P1/publication
chain is coherent. Once those gates clear, typed identity nulls gate only the exact
identity-dependent features named above, not the complete group/member map.
