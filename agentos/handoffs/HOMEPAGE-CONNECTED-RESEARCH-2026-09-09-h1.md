---
workstream: WS:HOMEPAGE-CONNECTED-RESEARCH
session: claude/homepage-connected-research-20260909-sol
model: sol
ended_because: ci_handoff
mission: >
  H1 only: make the existing homepage readable at narrow mobile widths while
  recording the approved larger connected-research direction.
state_before: >
  At source base a4d33f32dad140acdfa081b21f55ad6d8dcb94d4 the footer produced
  a 406px document at 390px; correcting only it left a 354px situation row at
  320px. Both defects were browser-reproduced. No redesign was deployed.
changed:
  - path: templates/landing.css
    what: Reflow footer columns and allow long situation statuses to wrap at the existing mobile breakpoint.
  - path: site/landing.css
    what: Byte-identical source projection, not a new stylesheet family.
  - path: templates/index.html
    what: Refresh the existing landing.css hash only; marketing copy remains unchanged in H1.
  - path: site/index.html
    what: Byte-identical homepage projection and matching CSS stamp.
  - path: tests/test_landing_navigation.py
    what: Regression for both CSS copies, observed failing before implementation.
  - path: research/HOMEPAGE_CONNECTED_RESEARCH_ROLLOUT_2026-09-09.md
    what: Approved end-state, no-rebuild boundaries, waves and release proof requirements.
  - path: mockups/evidence/homepage-mobile-reflow-20260909/
    what: Canonical eight-cell page capture, 24-case browser regression and narrow-screen detail images.
verified:
  - claim: The paired templates and published source assets agree.
    command: python3 -m scripts.check_template_site_sync
    result: 98 pairs checked, exit 0.
  - claim: Narrow layout retains footer links and full situation status text.
    command: python3 mockups/evidence/homepage-mobile-reflow-20260909/verify_mobile.py
    result: 24 cases passed across 320, 360, 390, 430, 768 and 1440 pixels; English and Chinese, both stored theme preferences.
  - claim: The canonical visual-capture tool recorded the required state matrix.
    command: python3 scripts/capture_page_evidence.py --site-dir site --routes /index.html --viewports desktop,mobile --locales en,zh --themes light,dark --max-pages 1
    result: Eight of eight states captured; see the EVIDENCE.yml receipt and manifest in the evidence directory.
unverified:
  - claim: H1 is live in production.
    what_would_verify: Concluded CI, reviewed exact-head merge, natural publication and a fresh production browser run verifying the served CSS hash and layout.
  - claim: The homepage redesign or conversion improvement is complete.
    what_would_verify: H2-H5 product journeys, source/entitlement agreement, analytics proof and mature cohort evidence.
unresolved:
  - Existing held macro 6842 has a failed pack-7 check and requires same-carrier review; do not replace it.
  - Public-logo macro 6988 still owns that source work; H1 does not change its logo hunks.
next_actions:
  - Complete exact-head source review and CI for H1; verify normal publication before marking H1 done.
  - Reconcile the existing trust repair and public entitlement discrepancies before implementing the connected example.
do_not_redo:
  - Do not re-audit the downsampled attachment as evidence of live font size or a permanently broken AI demo.
  - Do not create a new preview data, experiment, analytics or publication authority.
  - Do not infer a source-writer transfer or deployment acceptance from this record.
danger_areas:
  - Refresh both homepage CSS stamps whenever the paired stylesheet bytes change.
  - The homepage remains deliberately light-only under both browser preferences.
  - H2 and H3 can overlap index markup and existing ad-registry identity; reconcile before writing.
decisions: [DEC:HOMEPAGE-CONNECTED-RESEARCH-DIRECTION]
---

This is the same source carrier, not a replacement worker commission. The broader direction is approved, but H1 changes only layout and its cache stamp. The existing institutional-logo assertion, live/demo honesty defects and pricing disagreements remain explicitly open under H2. The static PNGs prove layout states, not motion, data truth, paid access or conversion.

Owner workspace: `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/homepage-connected-research-20260909-sol`. Procedure pin: `Mastermind@f3f2d9155796876009f2d427bfdecc7ee7b63e74`. No Executive production dispatch or unattended continuation is claimed. Sol must preserve this branch/PR and exact effects through CI and release reconciliation.

## Timeout continuation — fresh verification, 2026-09-10 UTC

The current live user explicitly asked this conversation to continue Landing Page Revamp Analysis. The recovered source remained on this same carrier. No source, hold, or release state of macro #6842 or #6988 was modified.

Fresh checks in the continuation:
- `python3 -m pytest tests/test_landing_navigation.py tests/test_public_chrome.py tests/test_landing_pricing_cta.py tests/test_template_site_sync_tokens.py -q`: **59 passed**.
- `python3 -m scripts.check_template_site_sync`: **98 pairs, exit 0**.
- `verify_mobile.py`: **24/24 browser cases passed**; all footer links and full status labels stayed within their viewport.
- `verify_negative_controls.py`: all four controls passed. Original CSS made the document **406px** wide at 390px; a footer-only probe fixed 390px but still produced **354px** at 320px; the complete patch produced exactly **390px / 320px** respectively. CSS substitution was confined to a loopback browser; repository and production CSS were not altered by this test.
- `git diff --check`: exit 0. Visual-evidence gate: exit 0. Design enforce-added gate: **0 blocking findings**, with inherited estate findings reported separately.
- `python3 scripts/agentos.py validate`: **0 errors, 85 warnings**; the warnings concern existing store joins/state, not this workstream's schema.

Freshly fetched compatibility reference: `macro@16b6c14cd4791dde7cd7217a6945987805b0fa16`. Compared against the source base for the changed CSS/index/navigation-test paths, related public-chrome/pricing tests, template-sync/visual-evidence checkers and AGENTS/CLAUDE/design doctrine: **no changes in those paths**. This is material-source compatibility evidence, not a merge-ref CI pass or production proof, and no ancestry-only merge was made.

Added reproducible negative controls and their JSON receipt under the existing H1 evidence directory. The first exploratory control callback failed because Playwright supplied a request argument over a default CSS argument; that failed probe created no result receipt and changed no source. The committed verification uses a one-argument callback and completed successfully.

Current stylesheet SHA-256: `dea45992eb94ef4f5eb8e33a109f9d0deedd44c7f2b50d9e6b30945cc0c92602`. The existing index cache stamp is `dea45992` in both copies.

Local verification is not SHIPPED. Required next proof remains exact-head PR/CI review, permitted merge and observed normal production publication. No unattended worker, watcher, runtime job or paid action was started by this continuation.

### Source-overlap checkpoint

A bounded read also found an uncommitted, overlapping footer/situation patch in `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/sol-homepage-mobile-20260909` at base `61cb600c966a`. Its footer breakpoint is 900px, while this carrier's verified fix preserves the existing layout until 680px. The sibling patch's existence is not proof of a current active worker, nor proof it is abandoned. No sibling source, ref, index, or process was modified. Preserve this carrier and publish only as a DRAFT review candidate until the overlap is adjudicated; do not silently combine, supersede, arm or release either implementation. The negative controls above establish this candidate's behavior, not ownership of the sibling.
