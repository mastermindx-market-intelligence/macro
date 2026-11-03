---
workstream: WS:MARKETING-X-CATALYST-LOOP
session: ce215fa3-31dc-4e76-a4e6-662daeddca8b
model: opus
ended_because: complete
mission: >
  CEO seat ce215fa3 shipping the Catalyst A3 live SEC source (scheduled writer + exact-document
  grant reader), the carried gaps G1–G7 and the SEC rights decision D1–D5 in one reviewed PR
  (#10379), then arming the writer timer in production with the public flags left OFF.
state_before: >
  #10257 (the integrated catalyst loop) was MERGED with PRODUCTION_PROOF of the OFF state; the
  anonymous scan had no admitted SEC source, so even with flags ON it could only refuse. No
  rights family covered SEC issuer earnings releases.
changed:
  - path: research/marketing_dockets/catalyst_fable_20261031/SEC_ISSUER_EARNINGS_RELEASE_PUBLIC_FACTS.json
    what: rights family sec_issuer_earnings_release_facts (EX-99.1 only), DEC:MX-CATALYST-SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS D1–D5
  - path: engine/marketing/catalyst_source_cycle.py
    what: bounded 150-GET writer over the 20-issuer pilot; 8-K/8-K/A Item 2.02 EX-99.1 in memory, sha256 + incumbent figure binder, no SEC bytes persisted (D4); exit codes 0/2/3/4/5/6
  - path: engine/marketing/catalyst_source_store.py
    what: namespaced store under marketing/catalyst-sec-source/v1/; the Filing Forensics pointer is never written
  - path: engine/marketing/catalyst_source_adapter.py
    what: reader that mints one public grant per issuer-own EX-99.1; 10-minute freshness bound, 60 s cache, fail closed
  - path: app/catalyst_source_wiring.py
    what: flag-gated wiring mounted from app/main.py; nothing configured while CATALYST_PUBLIC_ENABLED is unset
  - path: app/deploy/macro-catalyst-source-cycle.service, app/deploy/macro-catalyst-source-cycle.timer, app/deploy/update.sh
    what: oneshot writer every 5 minutes, installed and enabled by the deploy; SuccessExitStatus=3 4
  - path: engine/marketing/catalyst_admission.py, config/theme_sources.yml
    what: admission asserts the sec_issuer_earnings_release_facts family (never a bare sec_edgar family); only the scoped family row added
  - path: engine/marketing/catalyst_scan.py, engine/marketing/catalyst_partner_pack.py, app/catalyst_integration.py, app/catalyst_optin.py, app/catalyst_scan_ui.js, templates/catalyst_scan.*, templates/catalyst_partner.html.j2
    what: gaps G1–G7 (NO_QUALIFIED_EVENT pill, SEC acceptance clock, submit focus, update.sh restart fences, partner route F3, opt-in guard order, 320px card fit) under DEC:MX-CATALYST-GAPS-SEAT-RULINGS-20261101
  - path: .github/ci/legacy-jobs.yml
    what: legacy catalyst job scope covers the A3 modules and tests
verified:
  - claim: catalyst and deploy suites pass on the reviewed code
    command: pytest tests/test_catalyst_*.py tests/test_deploy_update_self_heal.py (one staged-UI test deselected)
    result: 1124 passed on bcd86bd9; the final docs-only head 76a595a7 re-ran the source suites, 78 passed
  - claim: the merged head is green on CI
    command: PR #10379 checks on head 0cb95b76 (catalyst-loop-integrated now installs Chromium and executes)
    result: every check green except the standing ci-authority/codex/merge-queue-pilot; one infra rerun of ci-pack-11 (git unpack-objects fault)
  - claim: the writer works against live SEC EDGAR
    command: scripts/run_catalyst_source_cycle.py --local-store against the pilot universe (head 6f1a7c53)
    result: recorded in the PR body
  - claim: independent review accepted the merged head
    command: read-only reviewer rounds recorded in the PR #10379 body
    result: rights REVISE -> repaired; 2a REVISE -> repaired; 2b, re-review, delta and scoped re-check ACCEPT_WITH_FINDINGS -> repaired; final wording ACCEPT on 76a595a7; CI delta 1be5c59f ACCEPT; the 0cb95b76 import-pin delta is recorded on the PR
  - claim: production writer timer runs and publishes the namespaced index
    command: ssh macro-api host — systemctl is-enabled/is-active, list-timers, journal JSON line
    result: >-
      2026-11-01, counts/states only: timer enabled + active (5-minute cadence); first two cycles
      COMPLETE exit 0, 20/20 issuers ok, 6 events, snapshot published, 32 then 26 SEC GETs; macro-api
      on 636abe2a66d with all four catalyst flags absent and /api/catalyst, scan and nojs at 503
unverified:
  - claim: the anonymous scan returns a qualified catalyst end to end on mastermind-x.com
    what_would_verify: operator sets CATALYST_PUBLIC_ENABLED=1, restarts macro-api, then the hosted A2 live-scan proof
  - claim: per-user digest dedup (B04) holds
    what_would_verify: the strict xfail B04 dedup test passing; MAIL_CATALYST_ENABLED stays OFF until then
unresolved:
  - Snapshot pruning — the timer writes about 288 immutable snapshots a day with no retention policy (owner decision)
  - Figure yield — engine/earnings_release/figures.py binds no figures on 5 of 6 live releases; a silent parser break publishes PARTIAL (4), not a failure (follow-up g)
  - Consent RPC review needs PostgreSQL
next_actions:
  - Operator decision — flags ON (CATALYST_PUBLIC_ENABLED, CATALYST_OPTIN_ENABLED, CATALYST_UX_ENABLED) then restart macro-api; rollback is unset + restart
  - After flags ON — hosted A2 live-scan proof on mastermind-x.com
  - Figure-yield follow-up in engine/earnings_release/figures.py, with a failure signal for a zero-figure parse
do_not_redo:
  - The SEC rights decision D1–D5 and the sec_issuer_earnings_release_facts family — recorded and merged
  - The A3 writer, store, adapter, wiring and units — merged in #10379 after the review rounds above
  - Gaps G1–G7 — merged with their tests
danger_areas:
  - FAILED (6) publishes nothing and leaves the prior pointer; the reader goes dark 10 minutes after the last good cycle_started_at
  - The writer must never persist SEC document bytes (D4) or write the Filing Forensics namespace
  - The user agent comes only from --user-agent or SEC_USER_AGENT; never from config.yml
prs: [10379, 10257, 10349]
decisions: [DEC:MX-CATALYST-SEC-ISSUER-EARNINGS-RELEASE-PUBLIC-FACTS, DEC:MX-CATALYST-GAPS-SEAT-RULINGS-20261101]
---

# Marketing X Catalyst — A3 live SEC source merged (636abe2a66d2)

PR #10379 merged as `636abe2a66d2`. The writer timer is armed in production and publishes the
namespaced index; the public reader stays dormant until the operator's flags-ON decision.

Observed 2026-11-01 on the macro-api host (counts and states only; no env values):

- Deploy: macro-api restarted 22:00:34Z on 636abe2a66d (`/healthz` commit and checkout both 636abe2a66d). The cron deploy tick installed both catalyst units (reviewed bytes) and armed the timer.
- Flags OFF in production: `CATALYST_PUBLIC_ENABLED`, `CATALYST_OPTIN_ENABLED`, `CATALYST_UX_ENABLED`, `MAIL_CATALYST_ENABLED` all absent from the service env. `/api/catalyst` 503; `/api/catalyst/scan` GET (`?tickers=AAPL`) and POST both 503 "Catalyst scan is not publicly enabled"; `/api/catalyst/nojs` 503.
- Writer env names present: `SEC_USER_AGENT` and the four `R2_RESEARCH_*` names; `RESEARCH_LOCAL_STORE` absent.
- Timer at 22:09:06Z: `macro-catalyst-source-cycle.timer` enabled + active; last trigger 22:08:28Z, next 22:13:28Z (5-minute cadence). Service is a timer-driven oneshot (inactive between runs): Result=success, ExecMainStatus=0, NRestarts=0.
- First two cycles (22:03:59Z and 22:08:41Z finished): both COMPLETE exit 0; issuers ok 20 / incomplete 0 / failed 0 / not_checked 0; events 6; snapshot published both runs. SEC GETs 32 on the bootstrap cycle, 26 on the next (inside the 150 budget).
