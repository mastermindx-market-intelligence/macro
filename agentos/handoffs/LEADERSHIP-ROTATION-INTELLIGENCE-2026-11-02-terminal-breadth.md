---
workstream: WS:LEADERSHIP-ROTATION-INTELLIGENCE
session: sol/web-sector-breadth-endpoints-20261102-c3
model: sol
ended_because: ci_handoff
mission: Deliver sector breadth leaders, laggards, expansion, contraction, velocity and descriptive leadership changes in Terminal Discover.
state_before: The production breadth view used source-order cards fed by one-month returns among movers. The 1D matrix URL setting did not change those counts.
changed:
- path: engine/sector_breadth_close.py
  what: Compute six daily advancing and declining counts on a fixed sample with seven exact US session closes, using existing sector classification and publication.
- path: engine/sp500_heatmap.py
  what: Add the optional historical sector projection to the existing heatmap payload.
verified:
- claim: Missing sessions and changing coverage cannot silently create a daily change in the tested examples.
  command: python3 -m pytest -q -p no:cacheprovider tests/test_sp500_heatmap_intraday_clock.py
  result: 25 passed on producer source 2e302aba8ccff549b68a8b70ef5182954708b51e.
- claim: The paired Terminal route ranks the historical producer output, measures velocity and preserves sector drilldown.
  command: npm run test:e2e:responsive -- e2e/sector-breadth.spec.ts --project=desktop --project=tablet --project=mobile --workers=2
  result: Nine local Chromium cases passed, including an October 22 replay with 497 of 499 names matched across 11 heatmap sectors. Fixture carries source hashes.
- claim: Both Terminal files also touched by live Discover PR 1231 merge textually on the shared base.
  command: git merge-file -p OURS BASE THEIRS for SectorCentralDiscovery.tsx and sectorCentralDiscovery.test.tsx
  result: Both returned zero for Terminal 088038e5 and 357d1cb5 versus ed2e6338. Combined release testing is still required.
unverified:
- claim: Both candidates have shipped and the authenticated production route consumes a naturally published daily observation.
  what_would_verify: Independent protected release, deployed commit, owner payload and signed-in board agreement on the same close and sample.
- claim: Intraday sector rotation is operational across all eleven sectors.
  what_would_verify: Qualified and entitled per-name observations, comparable same-session endpoints from the existing retention owner, cohort identities, fresh coverage and naturally updating signed-in browser readings.
unresolved:
- The old production route showed zero sectors and connection errors in this browser on November 2 after refresh. Earlier user screenshot shows eleven. Cause and scope remain unverified.
- The independent Fabric review request returned host-temperature admission refusal. No review ran. MastermindX1 was requested through GitHub on both draft PRs.
next_actions:
- Review producer PR 10604 and Terminal PR 1232 at the latest heads, qualify required CI, and route protected release to a non-author. Check the production data route before claiming completion.
- Deploy the accepted producer and Terminal through their incumbent paths. Compare observed date, matched counts, one- and five-session changes, peer ties and drilldown against a naturally emitted source.
- For intraday continuation, reconcile Macro 10212, 10227 and Terminal 1231. Reuse the existing per-member quote qualifier and publisher. Demonstrate eligible all-sector coverage and two comparable, source-timestamped same-session observations before enabling velocity. Keep delayed quotes visibly dated.
do_not_redo:
- Preserve the prior quote qualifier in Macro 10227 and the active-sector regular quote reader in Terminal 1231. Keep original Macro 10212 and 10213 drafts in their own custody.
- Retain the existing breadth publisher, close cache, heatmap classification, access gateway, rotation owner and exchange calendar.
danger_areas:
- Today's sector membership reconstructed over six dated readings is unsuitable for historical point-in-time or predictive claims. Unchanged names belong in the daily sample. The monthly fallback excludes them.
- A higher daily breadth rank does not measure capital flow. A single crossover, missing quote or later generated timestamp cannot qualify a sustained intraday move.
prs: [10604]
---

# Terminal sector breadth

The Chairman assigned this session the Terminal integration and its daily producer. The four summary readings compare participation levels and changes across measured sectors. The initial comparison is five sessions. The one-session option exposes the most recent move. Velocity is average percentage-point change per trading session. The selected sector names peers whose ordering reversed from five sessions earlier and held across the last two closes.

[Daily producer](https://github.com/mastermindx-market-intelligence/macro/pull/10604) · [Terminal board and visual evidence](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1232) · [Market-wide intraday qualification](https://github.com/mastermindx-market-intelligence/macro/pull/10227) · [Active-sector live quote reader](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1231)
