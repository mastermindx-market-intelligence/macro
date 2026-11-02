---
workstream: WS:MARKETING-X-CATALYST-LOOP
session: claude/mx-catalyst-flags-on-20261102
model: fable
ended_because: ci_handoff
decisions:
  - DEC:MX-CATALYST-FLAGS-ON-20261102
mission: >
  CEO seat turning the Catalyst public surface on in production under the Chairman's
  2026-11-02 delegation ("get this project finished autonomously end to end without requiring me
  to do anything, u have full authority"), proving the hosted A2 journey, and clearing the two
  defects that kept the opt-in (B1) path unreachable: receipts minted only for the v1 scan shape,
  and a staged UX banner that claimed source rights were not admitted.
state_before: >
  #10379 (A3 writer + reader + gaps + rights) and #10466 (records) were MERGED; the writer timer
  published COMPLETE cycles every five minutes with every catalyst flag absent from the host, so
  /api/catalyst answered 503 and nothing public consumed the index. The figure-yield follow-up
  #10468 was armed merge-on-green and waiting for CI capacity in the repo sweeper.
changed:
  - path: /etc/macro-api.env (host, NAMES only; backup .pre-catalyst-public-20261102)
    what: CATALYST_PUBLIC_ENABLED=1, CATALYST_UX_ENABLED=0, CATALYST_OPTIN_ENABLED=0, CATALYST_SCAN_RECEIPT_SECRET generated on-host; MAIL_CATALYST_ENABLED absent; macro-api restarted 2026-11-02T06:12Z
  - path: app/catalyst_scan_authority.py
    what: receipts are minted and verified for the contract v1 scan and the live Stage A v2 scan alike (schema/version pair must match; same receipt body; verify still re-reads the producer)
  - path: app/catalyst_scan_ui.js, templates/catalyst_scan.js
    what: both browser UIs keep the receipt on either validated schema pair instead of dropping v2 tokens; an absent token keeps the opt-in form hidden
  - path: app/catalyst_integration.py, app/catalyst_optin.py
    what: receipts are minted only while the opt-in funnel is reachable (_optin_ready = switch on AND catalyst_optin.configured()), so no UI invites an email for a request that would answer 503 (independent review finding, round 1)
  - path: tests/test_catalyst_scan_authority.py, tests/test_catalyst_integration.py
    what: v2 receipt mint/verify witness, v2 route receipt witness, banner copy witnesses for both opt-in states
  - path: research/MARKETING_X_CATALYST_CONTINUATION_HANDOFF_20261101.md
    what: Flags ON section — host state, hosted proof, rollback, why UX and OPTIN stay 0, CATALYST_SCAN_RECEIPT_SECRET name
verified:
  - claim: >-
      Hosted A2 journey (rung: hosted user journey) answers on the public host with the public
      flag on: the catalyst reader returns 200 for a covered and an uncovered ticker, the scan
      GET/POST return 200 PARTIAL (covered ticker SUPPORTED with an SEC 8-K Item 2.02 source and a
      rights receipt; the unknown ticker NOT_COVERED), the no-JS page serves the viewport meta,
      the 420px media query, focus-visible rules, the noscript fallback and a hidden opt-in
      section; no scan_receipt is emitted while the opt-in funnel is unreachable.
    command: "curl -sS 'https://www.mastermind-x.com/api/catalyst?tickers=V,ZZZQ'; curl -sS -X POST .../api/catalyst/scan; curl -sS .../catalyst/scan (served HTML grep)"
    result: "200 / 200 PARTIAL / HTML checks all present; scan_receipt absent; mastermindx.ai names answer 525 at the edge so www.mastermind-x.com is the hosted URL"
  - claim: >-
      The v2 receipt mint/verify path and the state-accurate banner are covered by tests on the
      PR head; the full catalyst integration suite passes on a sparse tree except the known
      theme.css 503 case that only a full checkout serves.
    command: "python3 -m pytest tests/test_catalyst_scan_authority.py tests/test_catalyst_integration.py -q -p no:cacheprovider"
    result: "139 passed, 1 failed (test_staged_session03_primary_ui_and_fallback: sparse-tree theme.css 503; CI full checkout covers it)"
  - claim: "Two independent read-only Opus review rounds on PR #10522: round 1 returned the _optin_ready finding (fixed in 088dbc2179dc), round 2 returned PASS."
    command: "gh pr view 10522 --comments (review comments 6571229333 and 6571304674)"
    result: "PASS; label merge-on-green armed"
unverified:
  - claim: "The browser-rendered PUBLIC PREVIEW banner with the 'not yet enabled' copy on the hosted page under CATALYST_UX_ENABLED=1."
    what_would_verify: "After this PR deploys: set CATALYST_UX_ENABLED=1 on the host, restart macro-api, curl the hosted page and count the banner strings (scratch script host_ux_flag_on.sh)."
unresolved:
  - "CATALYST_UX_ENABLED stays 0 until this change deploys (then set 1, restart macro-api, re-check the PUBLIC PREVIEW banner)."
  - "CATALYST_OPTIN_ENABLED stays 0: on main build_existing_owner_service has no caller (503 CATALYST_INTEGRATION_NOT_READY); the B1 wiring lane is PR #10532 (reviewed PASS, pending CI); the Supabase consent RPCs catalyst_consent_* (contract v2) are not provisioned and the SQL is REVIEW ONLY (security review NO until fixes F1-F5 land)."
  - "MAIL_CATALYST_ENABLED stays OFF while the B04 strict xfail stands (consolidated per-user message is B2 sender-wave work)."
  - "#10468 (figure yield) is owned by the repo sweeper: proof went stale when main fd27c31a changed the check definitions; refresh deferred for CI capacity."
  - "Snapshot pruning for marketing/catalyst-sec-source/v1/ still needs an owner decision (no-reclaim law)."
next_actions:
  - "Sweeper merges #10522 on green; the 3-minute deploy picks it up; set CATALYST_UX_ENABLED=1, restart macro-api, re-check the hosted page and record the banner proof."
  - "B1: merge #10532 (wiring seam under CATALYST_OPTIN_ENABLED), then provision the catalyst_consent_* RPCs through the established Management-API migration path after the fixed SQL is re-reviewed, witness one real OTP request, and only then set the opt-in flag."
do_not_redo:
  - "The flags-ON decision is recorded (DEC:MX-CATALYST-FLAGS-ON-20261102) and was delegated by the Chairman; never re-ask it."
  - "#10379, #10466 are MERGED and live-proven; the public flag, the receipt secret and the host restart of 2026-11-02T06:12Z are done; do not regenerate the secret or re-run the host change."
  - "PR #10522 has two independent review rounds (PASS); records-only commits need no third round."
danger_areas:
  - "Never print or record the values of CATALYST_SCAN_RECEIPT_SECRET, SUPABASE_* or any host env; names, counts and booleans only. The host env backup stays (no-reclaim law)."
  - "MAIL_CATALYST_ENABLED and CATALYST_OPTIN_ENABLED are not to be set without their recorded gates (B04 xfail; consent RPCs provisioned and reviewed; one real OTP witnessed)."
  - "Never stage data/ or site/; the seat tree is sparse. Never checkout a non-claude/* branch in the seat tree."
---

# Flags ON — hosted A2 proven, B1 path cleared

The public Catalyst surface is live on www.mastermind-x.com with `CATALYST_PUBLIC_ENABLED=1`;
the UX and opt-in switches stay 0 until this PR deploys and the B1 owner gates are met. The
body of the proof and the rollback recipe live in
`research/MARKETING_X_CATALYST_CONTINUATION_HANDOFF_20261101.md` (Flags ON section).
