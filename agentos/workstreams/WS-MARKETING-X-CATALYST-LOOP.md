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
  - templates/catalyst_scan.css
  - templates/catalyst_partner.html.j2
  - tests/test_catalyst_*.py
  - tests/catalyst_scan_browser.js
  - tests/fixtures/catalyst_*.json
  - research/MARKETING_X_CATALYST_CONTINUATION_HANDOFF_*.md
  - research/marketing_dockets/catalyst_fable_20261031/RIGHTS_CLASSIFICATION_REQUEST.md
  - research/marketing_dockets/catalyst_fable_20261031/D1_READINESS_NOTE.md
  - research/marketing_dockets/catalyst_fable_20261031/SEC_ISSUER_EARNINGS_RELEASE_PUBLIC_FACTS.json
  - engine/marketing/catalyst_source_adapter.py
  - engine/marketing/catalyst_source_cycle.py
  - scripts/run_catalyst_source_cycle.py
  - engine/marketing/catalyst_source_store.py
  - config/catalyst_pilot_universe.json
  - app/deploy/macro-catalyst-source-cycle.service
  - app/deploy/macro-catalyst-source-cycle.timer
waves:
  - id: A1-INT
    title: Integrate the verified Session00/01/02 catalyst loop onto main
    status: done
    next_action: >
      Merged to main in PR #10257 (ab29a89eb4bd, 2026-10-31): base 55dc7cab judged 75caf025, three mechanical conflict resolutions kept both sides, producer bytes unchanged. DO_NOT_REDO.
  - id: A2-WITNESS
    title: Anonymous-journey witnesses A01/A02/A04/A05/A07
    status: done
    depends_on: [A1-INT]
    next_action: >
      Merged to main in PR #10257: witness head 5a0079da, tests only (+1108/-0). Browser-dependent A07(c)/(d) remain recorded gaps, never faked. DO_NOT_REDO.
  - id: B-NEG
    title: Consent negatives B01–B04
    status: done
    depends_on: [A1-INT]
    next_action: >
      Merged to main in PR #10257 (B01–B04 appended to the enrolled suites). B04-DEDUP stays a carried gap on the producer side. DO_NOT_REDO.
  - id: C1-PACK
    title: Editorial asset factory adopted from Session04 with a producer→pack adapter
    status: done
    next_action: >
      Merged to main in PR #10257: #8683 blob 6b4e3b88 adopted, adapter + enrollment + grant-binding fixtures; F3/F4/F5 partner-pack gaps carried. DO_NOT_REDO.
  - id: RIGHTS-REQ
    title: Exact SEC EDGAR document-rights classification request for the GMI/source steward
    status: done
    next_action: >
      Merged to main in PR #10257; delivered ONCE to the steward carrier PR #7870 (comment 6549466894, marker MX-CAT-RIGHTS-REQUEST-7870-ab29a89eb4bd). The steward decides D1–D5; never re-post.
  - id: SHIP
    title: One draft PR to main, independent review, merge, deploy observation
    status: done
    depends_on: [A1-INT, A2-WITNESS, B-NEG, C1-PACK]
    next_action: >
      PR #10257 merged to main ab29a89eb4bd (2026-10-31 21:36:49Z, squash, --match-head-commit 94f2a79a; ci run 41239170455 SUCCESS; independent read-only review ACCEPT_WITH_FINDINGS recorded in the PR body). Deploy observed 22:03Z: API process = merge commit, /api/catalyst 503, /optin/request 503, /scan?tickers=AAPL 503; flags OFF. Rung: MERGED + PRODUCTION_PROOF of the OFF state. DO_NOT_REDO.
  - id: RIGHTS-DEC
    title: Record the SEC issuer earnings-release public-facts rights decision (D1–D5)
    status: done
    depends_on: [RIGHTS-REQ]
    next_action: >
      Recorded by the seat under leadership continuity (steward #7870 absent): family
      sec_issuer_earnings_release_facts in config/theme_sources.yml, basis
      SEC_ISSUER_EARNINGS_RELEASE_PUBLIC_FACTS.json, DEC:MX-CATALYST-SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS.
      Ships with A3-SOURCE behind independent review. DO_NOT_REDO.
  - id: A3-SOURCE
    title: Live pinned SEC source cycle (writer) + exact-document grant adapter (reader)
    status: in_progress
    depends_on: [RIGHTS-DEC]
    next_action: >
      Writer catalyst_source_cycle + timer and reader catalyst_source_adapter.build_admitted_source;
      the adapter mints one grant per issuer EX-99.1 URL + sha with the D4 expiry and D5 owner_ref/receipt_id.
      Integrate, independently review, merge, then install the writer timer on the production host.
  - id: GAPS
    title: Carried engineering gaps G1–G7 from the 2026-10-31 merge handoff
    status: in_progress
    depends_on: [SHIP]
    next_action: >
      NO_QUALIFIED_EVENT pill, A04 clock render, A07(c)/(d) browser witnesses, update.sh restart fence,
      partner pack F3/F4, B04-DEDUP/F1, consent RPC review on PostgreSQL. Each lands with its test.
  - id: OWNER-GATES
    title: Owner acts outside the seat — flags ON, hosted proofs, acceptance
    status: todo
    depends_on: [A3-SOURCE, GAPS]
    next_action: >
      (1) The flag operator (Chris) turns CATALYST_PUBLIC_ENABLED / CATALYST_OPTIN_ENABLED / CATALYST_UX_ENABLED
      on; (2) hosted A2 live-scan proof; (3) B2 opt-in return needs a sender, C2 external cohort a partner
      editor, D1 live conversions the Website/D07 UTM join, E1 the Chairman decision.
decisions:
  - DEC:ENTRY-RADAR-CATALYST-LIVE-READ-IS-OPT-IN
  - DEC:MX-CATALYST-SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS
  - DEC:MX-CATALYST-GAPS-SEAT-RULINGS-20261101
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
    config/theme_sources.yml admits sec_issuer_earnings_release_facts (2026-11-01) for the
    issuer EX-99.1 only; it is not a family-level allow-all. Every displayed fact needs a
    runtime exact-document grant from catalyst_source_adapter, and the hosted A2 proof cannot
    be claimed until the flags are turned on by their operator.
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
  - research/marketing_dockets/catalyst_fable_20261031/SEC_ISSUER_EARNINGS_RELEASE_PUBLIC_FACTS.json
next_action: >
  #10257 is MERGED + PRODUCTION_PROOF (OFF state). The seat recorded the SEC rights decision D1–D5
  (DEC:MX-CATALYST-SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS) and is shipping A3-SOURCE (live pinned
  SEC source cycle + exact-document grant adapter) and GAPS G1–G7 in one reviewed PR, then installs
  the writer timer. After that, only the operator's flags-ON and the hosted proofs remain.
---

# Marketing X — Catalyst Loop acquisition engine

The engine turns one public SEC event into a reader-first scan (`/api/catalyst`), an
explicit-consent return path, a rights-gated editorial asset and an opaque-attribution
commercial bridge. The docket at immutable `9651a77e` holds the census, acceptance matrix
(A01–A07, B01–B05, C01–C03, D01–D02) and proof ladder; this record tracks delivery.

Delivery ladder reported per wave, never higher than the evidence:
`ACK → QUEUED → START → RUNNING → DELIVERED → CI → MERGED → PRODUCTION_PROOF → ACCEPTANCE`.
