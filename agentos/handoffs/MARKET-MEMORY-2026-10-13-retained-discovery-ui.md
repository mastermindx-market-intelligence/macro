---
workstream: "WS:MARKET-MEMORY-W2C"
session: claude/ssd-market-memory-retained-ui-01a1333c-5d535132744300fd
model: codex
ended_because: ci_handoff
mission: Deliver exact retained-capture discovery and three-mode source inspection through the existing Market Memory page and Brain.
state_before: The retained API required exact references but the existing page and Brain had no admitted catalog to discover them.
changed:
  - path: engine/neuralweb/market_memory_retained_catalog.py
    what: Add current-user and installed-source admission before bounded identity/ancestry/receipt/payload discovery, exact generation paging, whole-generation final revocation and actual source-clock cutoff.
  - path: app/market_memory.py
    what: Add one shared catalog helper and private authenticated GET route with strict references, rate limits, two shared slots and typed refusals.
  - path: engine/neuralweb/brain_gateway.py
    what: Expose and dispatch the same catalog for the genuine server user; no invented references or alternate authority.
  - path: engine/neuralweb/brain_analogues.py
    what: Preserve original sealed comparator components and IDs for source inspection.
verified:
  - claim: Independent source review accepts the exact six-file discovery implementation.
    command: U1_CATALOG_SOURCE_REVIEW_MANIFEST_V2.json and U1_CATALOG_INDEPENDENT_REVIEW.json.
    result: PASS_NARROW; review SHA256 a6d47048e131324606d893b643a61aa9dde7685d24e6d0bc882bd490e4ddd8f1. Typed method-mismatch failure and wrong-store-before-ancestry repairs are covered.
  - claim: Actual trusted-owner discovery, API, Brain and retained consumers preserve exact identities and current rights.
    command: Catalog, retained-consumer, Brain-analogue and playback-API tests, followed by the affected catalog suite after final ordering hardening.
    result: 78 owner regressions passed; all 20 affected catalog cases passed after the final repair. Real writer fixtures cover exact paging, maximum source clocks, revocation of unreturned captures, byte budgets, shared slots, actual source and store identity, private headers and genuine dispatcher consumption.
  - claim: Catalog entitlement visibility and API restart reachability inherit the reviewed consumer repair.
    command: Tool economics, exact label whitelist, actual API import closure and catalog owner tests.
    result: 84 passed in10.37seconds. Both retained schemas remain site-full conditional; absent guest schemas preserve Fast narrowing. Catalog module joins the API restart list.
unverified:
  - claim: The existing UI consumes the new three-mode catalog and source inspector.
    what_would_verify: Returned frontend artifact integration, current source tests, all required visual cells and real entitled journey.
  - claim: This source is installed and accepted live.
    what_would_verify: Exact hosted checks, protected merge, installed-byte parity and actual nonempty API, Brain and page evidence.
unresolved:
  - The design preview is illustrative and grants no live acceptance.
  - Later outcomes remain separately qualified and visibly not attached until L0 delivery.
next_actions:
  - Integrate the retained original Fabric frontend result through its assigning parent.
  - Complete three modes, source inspection, state/race/auth tests and dual-theme bilingual visual evidence.
  - Deliver through protected CI, merge and the existing installation path; verify real entitled use.
do_not_redo:
  - Preserve original root01a1333c-a475-7052-95a8-72c623fb12e1 and all Fabric carriers.
  - Preserve repaired legacy issuer request ownership and exact original source bytes.
  - Preserve accepted August MM-G0 ABSTAINED and STOPPED results.
danger_areas:
  - Discovery identity reads do not establish external timestamp or economic truth authentication.
  - Selected case count is not independent sample count or forecast efficacy.
prs: [6528, 9140, 9170]
---
