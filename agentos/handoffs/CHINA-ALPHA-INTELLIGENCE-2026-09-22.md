---
workstream: "WS:CHINA-ALPHA-INTELLIGENCE"
session: "claude/china-selective-synthesis-checkpoint-20260922"
model: sol
ended_because: context_budget
mission: >
  Continue the Chairman-directed China macro dashboard restoration and selective-synthesis program:
  keep the restored pre-Archetype-D deep dashboard as the canonical information-architecture
  skeleton, integrate only bounded capabilities that are materially better from the rejected
  compressed concept, and require substantial end-to-end superiority before any future wholesale
  design replacement. This handoff covers the China macro dashboard product surface only; it does
  not change China Alpha scoring, candidate ranking, trade authority, or the WS program's model
  architecture.
state_before: >
  The destructive Archetype-D 14-to-6 compression had already been rejected and the old/deep China
  dashboard restored to production. The selective-synthesis design threshold was durably recorded,
  but the follow-on synthesis work was still mid-flight across several PRs: the first synthesis
  layer was merged/published, the anonymous China live client/Lens repair was pending, the compact
  causal-driver rail existed on a now-closed unmerged carrier, and the non-destructive mobile
  section-index carrier had not yet merged or been production-proven.
changed:
  - path: agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md
    what: >
      Chairman product law now explicitly says the deep pre-#7054 dashboard is canonical, selective
      synthesis is the default evolution path, and a future wholesale wipe requires substantial
      end-to-end superiority rather than cleanliness, novelty, parity, or fewer modules.
  - path: templates/china.html.j2
    what: >
      Through merged PR #7607, the restored deep dashboard gained bounded synthesis features without
      losing the four deep rows: a reconciled plain-language hero read, concise What To Do reasons,
      What Changed framing, keyboard activation for incumbent role-button cards, higher-impact-first
      event ordering, and preservation of the full deep dialogs. The current open carrier #7657 adds
      a causal Why-this-regime rail, signal-only regime-watch copy, a Flow Velocity landing, subtle
      section labels, and a mobile-only section index while keeping the same deep architecture.
  - path: site/china.html
    what: >
      PR #7607 published the selective-synthesis artifact through the existing China publication
      path. Current public proof at checkpoint still serves the deep dashboard and the merged
      selective-synthesis markers, with no Archetype-D L1-4 production shell.
  - path: config/site_access.yml
    what: >
      PR #7629 promoted only the presentation client /china_risk_state_live.js to the reviewed public
      static-asset boundary so the anonymous-public China shell no longer receives a 401 for its own
      live risk-state client. No graded JSON payload or premium data prefix was opened.
  - path: app/deploy/Caddyfile
    what: >
      PR #7629 aligned the matching Caddy public/static path lists with site_access.yml for
      /china_risk_state_live.js; this was a serving-boundary repair, not a new publication plane.
  - path: tests/test_china_archetype_d_s1.py
    what: >
      The China publication contract now pins the restored deep rows, the selective-synthesis
      boundaries, shared Lens ownership, quiet-by-default degradation behavior, the additive causal
      driver rail, regime-watch gating, mobile section index, and non-duplicative deep links.
  - path: mockups/evidence/china-selective-synthesis-20260922/
    what: >
      Open PR #7657 carries the current anonymous visual-evidence pack: eight screenshots covering
      desktop/mobile x dark/light x EN/ZH, plus manifest and heuristic smell receipts. The pack is
      candidate evidence only until the carrier merges and the real production path is re-proven.
  - path: agentos/handoffs/CHINA-ALPHA-INTELLIGENCE-2026-09-22.md
    what: >
      This cumulative continuation checkpoint. It records the product decision, immutable merged
      receipts, the current open carrier, production truth, what remains unverified, the ordered
      continuation, and the do-not-redo boundary.
prs: [7456, 7463, 7485, 7534, 7607, 7629, 7631, 7657]
decisions:
  - DEC:CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION
verified:
  - claim: "The canonical product law requires selective synthesis rather than another destructive China dashboard wipe."
    command: "git show main:agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md"
    result: >
      The record states that the pre-#7054 deep China dashboard is the canonical published default;
      selective synthesis is the default evolution path; and a wholesale design replacement requires
      substantial overall improvement across the real user job, not visual simplification or parity.
  - claim: "PR #7607 is merged and is the merged selective-synthesis publication carrier."
    command: "gh pr view 7607 --repo mastermindx-market-intelligence/macro --json state,mergedAt,mergeCommit,headRefOid,baseRefOid,title"
    result: >
      CLOSED/MERGED at 2026-09-21T11:35:45Z; merge commit
      8eaf4eda03c92fceba8760694c0c34e013e75055; title
      'Publish China selective synthesis and unify reason Lens'.
  - claim: "PR #7629 is merged and its exact product purpose was the anonymous China live-client plus shared-Lens repair."
    command: "gh pr view 7629 --repo mastermindx-market-intelligence/macro --json state,mergedAt,mergeCommit,headRefOid,baseRefOid,title"
    result: >
      CLOSED/MERGED at 2026-09-22T01:36:20Z; merge commit
      2a5d60d0d358cfe5216515f24b129250c4287707; title
      'Fix China public live client and shared reason Lens'.
  - claim: "The public China page at checkpoint is the deep dashboard with merged selective synthesis, not the rejected Archetype-D shell."
    command: "python3 cache-busted urllib proof against https://www.mastermind-x.com/china.html?handoff-proof=20260922"
    result: >
      HTTP 200; 261299 bytes; SHA-256
      b41b0f3ef218d29b9448df8ff747f13447d3b06c8da6eb48a62e3526bd07e983;
      ROW 4 deep marker=true; cnx-playbook-context=true; What changed=true;
      data-cn-driver-rail=false; cnx-mobile-index=false; L1-4 Why-four-drivers shell=false.
      Therefore #7657's later driver/mobile additions are not yet claimed live.
  - claim: "The formerly blocked China live presentation client is publicly retrievable after #7629."
    command: "python3 cache-busted urllib proof against https://www.mastermind-x.com/china_risk_state_live.js?handoff-proof=20260922"
    result: >
      HTTP 200; 12267 bytes; SHA-256
      73275593956850cd50b7af9f6eb8c73bc04389b8b53dba10e1e389c1886096b1.
  - claim: "PR #7631 is closed without merge and must not be treated as an accepted effect."
    command: "gh pr view 7631 --repo mastermindx-market-intelligence/macro --json state,mergedAt,headRefOid,baseRefOid,title"
    result: >
      CLOSED; mergedAt null; head 710c092c52b3760ab62ade1fbaee7c63a6f9405c.
      Its useful driver-rail delta was carried forward into #7657 rather than accepted from #7631.
  - claim: "PR #7657 is the current continuation carrier and already contains the driver-rail work plus the mobile-index/evidence work."
    command: "gh pr view 7657 --repo mastermindx-market-intelligence/macro --json state,headRefOid,baseRefOid,mergeable,title; gh pr diff 7657 --repo mastermindx-market-intelligence/macro"
    result: >
      OPEN at checkpoint; head 3cdb7279ca92d15f56d194c32d178340907ec20c;
      base f98f57f4ec7c2cc30cbd90d9a7a759d5ea69144c; mergeable true at read time.
      The patch includes data-cn-driver-rail / Why-this-regime synthesis, signal-only regime-watch
      copy, Flow Velocity deep link, mobile-only cnx-mobile-index, Action/Markets/Drivers/Deep
      Context section labels, tests, and the china-selective-synthesis-20260922 visual evidence pack.
  - claim: "The #7657 evidence pack captured all eight anonymous theme/locale/viewport combinations without a page-level horizontal overflow flag."
    command: "gh pr diff 7657 --repo mastermindx-market-intelligence/macro -- mockups/evidence/china-selective-synthesis-20260922/manifest.json"
    result: >
      manifest schema mastermind.p0_evidence.v2; states_captured=8/8 across desktop/mobile x
      dark/light x EN/ZH; console_error_count=0; horizontal_overflow=false in desktop and mobile
      metrics. The manifest also records one mobile element wider than viewport and explicit gaps
      for authenticated and forced loading/empty/stale/error states.
unverified:
  - claim: "PR #7657 is accepted, merged, and production-proven."
    what_would_verify: >
      Re-read its current head/base/checks/reviews; obtain latest-base integrated proof or equivalent;
      merge under normal governance; rebake/publish through the existing China path; then verify the
      served page from the public HTTPS path with browser proof. Merge or screenshots alone do not verify this.
  - claim: "The #7657 visual evidence is tied to the exact future production release commit."
    what_would_verify: >
      After merge/release, capture a real-path evidence pack or browser matrix whose target can be
      reconciled to the served release. The current manifest explicitly says a live origin does not
      disclose the commit it is serving.
  - claim: "Authenticated Free/Essential/Pro states and forced loading/empty/stale/error states remain correct after #7657."
    what_would_verify: >
      Approved authenticated fixtures for access tiers plus explicit state fixtures/capture against
      the exact accepted candidate or production release. The current manifest records those states
      as gaps rather than inferring them.
  - claim: "Protected main will remain path/dependency-disjoint from #7657 until merge."
    what_would_verify: >
      Immediately before acceptance, compare then-current protected main against #7657's owned paths,
      material dependencies, current Skillpack/decision law, and the current GitHub merge ref.
unresolved:
  - "PR #7657 is open and is the only current product continuation carrier. It is not yet a production effect."
  - "PR #7631 is closed/unmerged. Do not reopen it merely to recover the four-driver idea; #7657 already carries that useful delta."
  - "The current #7657 anonymous evidence pack reports one mobile element wider than the viewport while also reporting no document-level horizontal overflow. Treat that as a review target, not as proven breakage or proven harmlessness."
  - "The #7657 evidence pack does not cover authenticated or forced degraded states; those remain explicit proof gaps."
  - "Protected main is moving frequently. Current compatibility must be refreshed from the then-current main before any merge/release action."
next_actions:
  - "START HERE: re-pin protected Mastermind master, read the current Skillpack from one exact commit, then re-read DEC:CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION before modifying."
  - "Reconcile macro main and PR #7657 from GitHub. Freeze the current #7657 semantic head and its owned paths; compare protected-main movement against templates/china.html.j2, tests/test_china_archetype_d_s1.py, and its evidence pack plus material dependencies."
  - "Review the current #7657 merge ref/checks/reviews and the one-mobile-element-wider-than-viewport evidence. If the issue is a real user-visible overflow, repair it on #7657; if it is contained inside the intentional horizontal mobile jump rail, record that discriminating proof rather than changing layout blindly."
  - "If #7657 remains semantically compatible and all required gates are green, merge it under normal governance. Do not resurrect #7631."
  - "After merge, use the existing China build/render/VPS publication path only. If the shared render queue is clogged, reuse the already-established offline/site-artifact repair mechanics from #7463/#7463 lineage and #7607; do not create a second publication plane."
  - "Production-proof the exact served release: cache-busted HTTPS + browser matrix for desktop/mobile x dark/light x EN/ZH; verify the deep ROW 4, Market Sentiment, Policy Monitor, Connect Flows, Macro News, driver rail, mobile index, shared reason Lens, live client HTTP 200, and absence of the Archetype-D L1 replacement shell."
  - "Only after production proof, decide whether another bounded synthesis slice is materially useful. Prefer one useful capability at a time; do not keep adding layers merely because the old experiment contains more visual ideas."
do_not_redo:
  - "Do not restore the Archetype-D six-block/L1 composition to production. PR #7054 is incubation history, not current publication authority."
  - "Do not replace the restored deep China information architecture unless a future explicit Chairman product decision accepts a candidate that is substantially better end-to-end."
  - "Do not reopen or replay PR #7631. Its useful causal-driver delta already moved forward into #7657."
  - "Do not remove the accepted deep rows, dialogs, Market Sentiment, Policy Monitor, Connect Flows, Macro News, Property, AI Brief, Alerts Centre, or established drill-down landings merely to make the page shorter."
  - "Do not create a second China render, VPS deploy, state, lifecycle, tooltip, or publication control plane. Reuse the existing owners."
  - "Do not turn UI summaries, sentiment, freshness, driver pills, or model headlines into new scores, rankings, trade sizing, origination, or promotion gates."
  - "Do not recreate the China-local tooltip plane removed by #7607/#7629; reason receipts use the shared Lens owner."
  - "Do not duplicate News/Alerts navigation in the footer when those destinations already have first-class incumbent cards; Flow Velocity was the bounded missing landing worth adding."
  - "Do not claim #7657 live from its evidence screenshots or an eventual green CI run. Production acceptance requires the real served path."
danger_areas:
  - "templates/china.html.j2 is a large multi-owner surface with substantial legacy design debt. Forward-ratchet checks can report added-line violations if a patch mechanically re-adds inherited CSS; keep synthesis changes minimal and token-native."
  - "Protected main moves quickly; a stale base SHA is not a compatibility receipt. Use path/dependency/material-source comparison and current merge-ref proof immediately before merge."
  - "The China page is bilingual and direction colors flip under zh conventions in several market-direction surfaces. Do not 'normalize' colors without re-reading the established China direction-color law."
  - "The dashboard's public HTML shell depends on public presentation assets while graded payloads remain gated. Serving-boundary edits must keep config/site_access.yml and every Caddy mirror aligned and must never widen a data prefix by convenience."
  - "Visual evidence can be truthful yet incomplete: the current pack is anonymous-only and does not force loading/empty/stale/error states."
---

# China macro dashboard selective-synthesis checkpoint — 2026-09-22

**FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION**  
**MISSION_COMPLETE: false**

## Capability delta at this boundary

**Before:** the China dashboard had been restored from the destructive Archetype-D replacement, but
the useful ideas inside that rejected experiment were not yet consistently transplanted into the
canonical deep surface, and the anonymous live client had a serving-boundary defect.

**After:** the real production page is still the restored deep dashboard, now with the accepted first
selective-synthesis layer from #7607; the China live risk-state client is publicly retrievable after
#7629; the destructive L1 shell remains absent; and the next bounded synthesis candidate is
consolidated in #7657 rather than spread across duplicate carriers.

This is not parent completion. #7657 remains an open candidate and has not been accepted or
production-proven.

## Authority and product thesis

The highest-authority product rule is
`agentos/decisions/DEC-CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION.md`.
Its governing thesis is simple:

1. the deep pre-#7054 dashboard is the production skeleton;
2. the newer Archetype-D concept is an incubation source, not publication authority;
3. selective synthesis is preferred;
4. another wholesale wipe requires substantial end-to-end superiority across the actual user job.

The current Chairman scope authorizes continuing this selective-synthesis program. It does not
authorize deleting accepted depth to make the page visually simpler.

## Current carrier map

- **#7607 — MERGED:** accepted first selective-synthesis publication carrier.
- **#7629 — MERGED:** anonymous live-client boundary + shared reason-Lens repair.
- **#7631 — CLOSED / NOT MERGED:** old compact-driver carrier. Historical only; useful delta moved
  forward.
- **#7657 — OPEN:** current continuation. It carries the compact causal driver rail, regime-watch
  gating, Flow Velocity deep link, mobile section index, subtle deep-row labels, tests, and the
  current anonymous visual-evidence pack.

A cold session should treat #7657 as the sole current product continuation carrier unless GitHub shows
a later superseding effect.

## Production truth at checkpoint

Cache-busted public proof on 2026-09-22 returned:

- `/china.html`: HTTP 200, 261299 bytes, SHA-256
  `b41b0f3ef218d29b9448df8ff747f13447d3b06c8da6eb48a62e3526bd07e983`;
- deep ROW 4 marker present;
- selective-synthesis `cnx-playbook-context` present;
- What Changed framing present;
- rejected L1-4/Four Drivers production shell absent;
- #7657-only driver rail and mobile index absent, which is correct because #7657 has not shipped;
- `/china_risk_state_live.js`: HTTP 200, 12267 bytes, SHA-256
  `73275593956850cd50b7af9f6eb8c73bc04389b8b53dba10e1e389c1886096b1`.

## What the next session must not confuse

A clean screenshot is not the mission. A short page is not the mission. A new visual language is not
the mission. The user job is to get a deep but legible China macro decision surface where glance-level
orientation leads into trustworthy underlying evidence without destroying the existing intelligence
workspace.

The open candidate #7657 is valuable precisely because it tries to improve orientation without
compressing away capability. Its acceptance still depends on current-base review, required CI/security
gates, exact-merge proof, and real-path production verification.

## Resume pointer

Resume from **macro PR #7657** after refreshing current protected main and current Skillpack. Do not
start by replaying #7054, #7456, #7463, #7607, #7629, or #7631. Those are history/accepted effects or
superseded carriers. The first material question is whether the latest #7657 head is still compatible
with current main and whether its mobile evidence's one wider-than-viewport element is intentional and
contained or is a real user-visible overflow.

## Continuation update — 2026-09-23

This section supersedes only the mutable carrier/proof facts in the 2026-09-22 checkpoint above.
The product law, do-not-redo rules, and selective-synthesis thesis remain unchanged.

**FINALIZATION_CLASSIFICATION: DURABLE_EXECUTION_RUNNING**  
**MISSION_COMPLETE: false**

### Material deltas since the prior checkpoint

- PR **#7667** has made the compact `Why this regime` causal-driver rail, signal-only regime watch,
  and Flow Velocity deep landing part of the accepted/live baseline. Do not recover those ideas by
  reopening #7631.
- Production proof on 2026-09-23: cache-busted `/china.html` returned HTTP 200 with deep ROW 4,
  `cnx-playbook-context`, one `data-cn-driver-rail`, Flow Velocity landing, no document horizontal
  overflow, and no rejected L1-4/Four-Drivers shell. A Chrome matrix across 1440/390 x dark/light x
  EN/ZH passed all 8 cells with zero page errors and zero failed requests; all four driver pills
  opened the incumbent Policy / Flows / Risk / Property dialogs and the shared Lens receipt opened
  through the site-wide `.lens-pop.open` owner and closed on Escape.
- The visual-evidence review target `mobile.elements_wider_than_viewport=1` is now discriminated:
  CURRENT PRODUCTION at 390px has the same single wider element, decorative `div.au-a3`
  (600px wide, clipped from x=-105 to 495), while `documentElement.scrollWidth == clientWidth == 390`.
  It is inherited decorative aurora geometry, not a #7657 horizontal-scroll regression.
- PR **#7657** remains the sole current product continuation carrier. GitHub refreshed the SAME branch
  onto current base `668237947e016f679782e41e61c91c9133a5ea99`, producing candidate head
  `db505dff26cc3895e4637148b48ab4b224e24dab`. The reviewed owned blobs did not change:
  `templates/china.html.j2` `b6409450adcf1cb44d663d5822d73d7371eeb2bf`,
  `tests/test_china_archetype_d_s1.py` `1e5b35db28d0a7e8fa6188658ff93bb00ccc3ba9`,
  evidence receipt `9f7dad08a6e140901be0d9f0e0b31bab23453771`, manifest
  `789928ba82f04a64b2704bec2578ebc41794ec2e`.
- Current GitHub merge-ref proof is
  `6bcba61bf6c350b7d153bcad1fc9408bd4f1ff1a` with parents current base
  `668237947e016f679782e41e61c91c9133a5ea99` + candidate
  `db505dff26cc3895e4637148b48ab4b224e24dab`. A clean detached worktree of that exact merge ref
  passed `git diff --check`, Jinja parse, the selective-synthesis/static publication slice
  (**22 passed / 6 runtime-only deselected**), and design-system `enforce-added` with **0 blocking**.
- The stale `merge-blocked` label from the old semantic-evidence base mismatch was cleared after the
  branch moved again, matching merge-on-green law. `merge-on-green` remains armed. Fresh full CI is
  STARTED/RUNNING on the refreshed head; do not poll it with a principal while unchanged.

### Current production / candidate boundary

- **Live now:** restored deep dashboard + first synthesis layer + public live risk-state client +
  causal driver rail + regime watch + Flow Velocity landing.
- **Still candidate-only in #7657:** mobile-only section index and the subtle section labels
  `Action & calendar`, `Markets & risk`, `Drivers & news`, `Deep context`.
- The current PR diff no longer needs to re-justify the causal driver rail as an unaccepted effect;
  that capability is already live. #7657 should be judged primarily on the remaining mobile
  orientation/section-label delta plus its evidence pack.

### Exact next action

1. Let the fresh #7657 semantic CI complete on head
   `db505dff26cc3895e4637148b48ab4b224e24dab`; do not create a replacement carrier.
2. If required gates are green and no new material main movement touches the owned/dependency paths,
   allow the already-armed merge-on-green path to merge #7657.
3. After merge, use the existing China build/render/VPS publication owner only.
4. Production-proof the mobile index + section labels on the real served release across
   desktop/mobile x dark/light x EN/ZH while rechecking deep ROW 4, driver rail, shared Lens,
   live client HTTP 200, and absence of the rejected L1 shell.
5. Only then decide whether another bounded synthesis slice is materially useful.

