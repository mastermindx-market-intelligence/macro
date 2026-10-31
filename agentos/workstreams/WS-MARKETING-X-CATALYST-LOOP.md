---
key: MARKETING-X-CATALYST-LOOP
title: Marketing X — Catalyst Loop acquisition engine (source-to-reader, consent, editorial asset, commercial bridge)
objective: >
  Deliver the Marketing X docket (immutable 9651a77e, research/marketing_dockets/
  catalyst_fable_20261031/) as a robust engine: a trustworthy SEC-event source-to-reader
  composition that gives first value without identification (A1/A2), a consent path that
  never grants, sends or discloses outside its gates (B1/B2), a rights-gated editorial asset
  factory with correction lineage (C1/C2), and a commercial bridge that passes only opaque
  attribution (D1), each proven to the rung its evidence reaches and never reported higher.
status: active
program: marketing-intelligence
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - app/catalyst_integration.py
  - app/catalyst_scan_ui.js
  - app/catalyst_optin.py
  - engine/marketing/catalyst_admission.py
  - engine/marketing/catalyst_lifecycle.py
  - engine/marketing/catalyst_packets.py
  - engine/marketing/catalyst_partner_pack.py
  - scripts/build_catalyst_partner_pack.py
  - templates/catalyst_scan.js
  - templates/catalyst_partner.html.j2
  - tests/test_catalyst_*.py
  - tests/catalyst_scan_browser.js
  - tests/fixtures/catalyst_*.json
  - research/MARKETING_X_CATALYST_CONTINUATION_HANDOFF_*.md
waves:
  - id: A1-INT
    title: Integrate the verified Session00/01/02 catalyst loop onto main
    status: awaiting_ci
    next_action: >
      Merge lane/mx-cat-a1-base (55dc7cab = Session00 head ed1ceabd + verified Stage-A v2
      six-file patch + verified Stage-B consent repair) onto fresh main; resolve the three
      mechanical conflicts (app/deploy/update.sh restart-fence regex union, tests/test_ci_pack.py
      owner-set union, .github/ci/legacy-jobs.yml path-list union); eight catalyst suites and
      tests/test_ci_pack.py green; producer-owned bytes unchanged.
  - id: A2-WITNESS
    title: Anonymous-journey witnesses A01/A02/A04/A05/A07
    status: awaiting_ci
    depends_on: [A1-INT]
    next_action: >
      Hermetic tests written by a non-author lane: supported-plus-unsupported ticker, four
      distinct empty truth-states, nullable official publication never relabeled, revoked grant
      retires the claim, no-JS fallback tells the same truth. Browser/Chromium availability is
      reported honestly, never faked.
  - id: B-NEG
    title: Consent negatives B01–B04
    status: awaiting_ci
    depends_on: [A1-INT]
    next_action: >
      Append-only negatives in the enrolled lifecycle/optin suites: no grant without a signed,
      fresh, consented scan; operator-OFF or rights-revoked during the OTP window leaves no
      durable grant; email-denied and mid-batch expiry suppress; pre-send outage and post-invoke
      exception are distinct non-sent states, never auto-replayed.
  - id: C1-PACK
    title: Editorial asset factory adopted from Session04 with a producer→pack adapter
    status: in_progress
    next_action: >
      Adopt the four #8683 source files by exact blob (6b4e3b88); adapt to catalyst.public_event/v1
      with rights gating (link-only without rehost right, PackRejected without grant), correction
      lineage, opaque-attribution CTA, five distinct clocks; hermetic tests; enroll the suite in
      catalyst-loop-integrated on the A1 head.
  - id: RIGHTS-REQ
    title: Exact SEC EDGAR document-rights classification request for the GMI/source steward
    status: awaiting_ci
    next_action: >
      Record (not a grant): exact document identity the producer binds, today's default-deny
      behavior, the exact registry entry shape a steward would add, opaque attribution keys the
      scan/pack may pass, remaining unknowns. The steward decides; the Chairman's data-rights
      attestation does not cover SEC EDGAR.
  - id: SHIP
    title: One draft PR to main, independent review, merge, deploy observation
    status: in_progress
    depends_on: [A1-INT, A2-WITNESS, B-NEG, C1-PACK]
    next_action: >
      Seat integrates the judged lane heads into its claude/ branch, opens ONE draft PR to main,
      CI green, fresh non-authoring review, merge with --match-head-commit, observe the macro-update
      deploy with every catalyst flag still OFF.
decisions:
  - DEC:ENTRY-RADAR-CATALYST-LIVE-READ-IS-OPT-IN
discoveries: []
landmines:
  - >-
    PR #8678 (sol/mmx-acq-catalyst-int-20261008, head ed1ceabd) is the historical Session00
    carrier. It stays Draft/HOLD and nothing is pushed to sol/* branches; the leadership
    takeover is recorded there once (comment 6540346973, 2026-10-31).
  - >-
    The eight Stage-A/Stage-B files are producer-owned bytes. An integrator resolves merge
    mechanics around them; a semantic change needs its own finding, review and seat decision.
  - >-
    config/theme_sources.yml has no sec_edgar entry on main. A family entry is not an
    issuer-exhibit grant; the hosted A2 proof cannot be claimed until a steward grants rights
    and the flags are turned on by their owner.
  - >-
    CATALYST_PUBLIC_ENABLED / CATALYST_OPTIN_ENABLED / CATALYST_UX_ENABLED default OFF and
    fail closed; no wave enables them. The consent RPC review script needs PostgreSQL and is
    reported as not run when absent.
  - >-
    examples/catalyst_partner_previews/** (fictional packs) and mockups/evidence/** (PNG) from
    #8683 are not adopted; fictional packs are not evidence.
do_not_redo:
  - "Do not re-verify or re-apply the Stage-A v2 / Stage-B patches; lane/mx-cat-a1-base = 55dc7cab is the verified materialization (eight blob ids checked)."
  - "Do not re-measure the main-vs-55dc7cab conflict set from scratch; it is exactly three single-hunk files with frozen resolution rules."
  - "Do not treat if: ${{ false }} on legacy-jobs.yml jobs as a defect; it is the pack-planner convention."
artifacts:
  - research/marketing_dockets/catalyst_fable_20261031/README.md
  - research/marketing_dockets/catalyst_fable_20261031/EVIDENCE.md
  - research/marketing_dockets/catalyst_fable_20261031/DESIGN.md
  - research/marketing_dockets/catalyst_fable_20261031/PILOT.md
  - research/marketing_dockets/D07_FUNNEL_LIFECYCLE_MNZ.md
next_action: >
  Seat ce215fa3 (Fable 5.1) orchestrates two Opus orchestrators over the Subagent Fabric for
  waves A1-INT/A2-WITNESS/B-NEG (ORCH-A) and C1-PACK/RIGHTS-REQ (ORCH-B); on their judged
  returns the seat ships SHIP. The docket documents themselves live on planning PR #10241.
---

# Marketing X — Catalyst Loop acquisition engine

The engine turns one public SEC event into a reader-first scan (`/api/catalyst`), an
explicit-consent return path, a rights-gated editorial asset and an opaque-attribution
commercial bridge. The docket at immutable `9651a77e` holds the census, acceptance matrix
(A01–A07, B01–B05, C01–C03, D01–D02) and proof ladder; this record tracks delivery.

Delivery ladder reported per wave, never higher than the evidence:
`ACK → QUEUED → START → RUNNING → DELIVERED → CI → MERGED → PRODUCTION_PROOF → ACCEPTANCE`.
