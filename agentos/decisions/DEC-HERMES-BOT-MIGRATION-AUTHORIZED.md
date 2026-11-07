---
key: HERMES-BOT-MIGRATION-AUTHORIZED
question: >
  Should Grok Secretary's role-bot duties (ping scan, overnight sweep, blocked
  wake, returns) migrate from the incumbent Slack bot onto two Hermes harness
  profiles (mmmeta, mmsecretary) via the WP5 shadow package?
answer: >
  Yes, in principle only: the migration is authorized to proceed through
  evidence, not through cutover. Shadow parity runs against read-only Slack
  data (7 days retrospective on #dotsandgroksecretary plus a 3-day forward
  shadow overlap with Grok Secretary still live). Live posting, cron install,
  profile enrollment and any cutover step remain unauthorized by this record
  and require a separate explicit Chairman grant after parity evidence.
rationale: >
  The Chairman's 2026-11-06 directive on Mastermind #2082 authorizes the
  migration in principle and fixes the evidence bar. The WP5 package
  (mastermind:integrations/hermes_secretary at ad6275a) is
  SOURCE-ONLY / SHADOW / PRODUCTION_INERT: its shadow runner enforces
  would_post=false on every decision, its Slack client rejects any write
  surface, and CUTOVER_AND_ROLLBACK.md states the package does not authorize
  cutover. Recording the decision now, with the gates named, keeps the role
  change answerable and outlives the session that issued it.
alternatives:
  - option: Keep Grok Secretary as the permanent role bot.
    why_not: >
      Single-provider dependency the organization has already decided to
      retire; the Hermes harness was qualified for exactly this role surface
      (PR #1865) and the port exists.
  - option: Direct cutover without a parity window.
    why_not: >
      No parity evidence exists yet; the runbook and the directive both
      require measured parity before any cutover grant, and Grok Secretary
      must stay live throughout.
  - option: Run a second Slack polling daemon in parallel.
    why_not: >
      README forbids inserting another Slack polling daemon or reusing Grok
      Secretary's token; a client-facing transport needs distinct per-role
      app credentials and the approved incumbent owner.
evidence:
  - "Mastermind #2082 Chairman directive comment, 2026-11-06, author chriswong6031-creator: migration authorized in principle; 7-day retrospective parity plus 3-day forward shadow; cutover is a separate grant; outcome ref hermes-bot-migration-20261106-c1. https://github.com/mastermindx-market-intelligence/Mastermind/issues/2082"
  - "Host-local handoff packet HERMES_BOT_MIGRATION_HANDOFF_2026-11-06.md, SHA256 1e7e9d9bdefaa410b95f03c3ecef43babaf0594ccd168c102185ecbd6d78f6ed (not committed; Phases A-E)."
  - "mastermind:integrations/hermes_secretary/CUTOVER_AND_ROLLBACK.md at ad6275a (#2157): the runbook; shadow parity on fixtures or read-only export allowed any time; live posting, cron install, profile enrollment out of its authority."
  - "mastermind:integrations/hermes_secretary/README.md at ad6275a: status SOURCE-ONLY / SHADOW / PRODUCTION_INERT; upstream pin NousResearch/hermes-agent@1c0cd667746d3395fe9e1b6c74f8f85952486f18."
  - "WP5 suite at ad6275a on the Chairman's Mac: 74 of 75 green; the single red (test_cancun_fire_times_match_source_wall_clocks, job m2studio-browser-tab-sweep, window start 2026-11-02) is a host-tzdata divergence — local zoneinfo still applies Vancouver DST fallback (UTC-8) while jobs.json wall_clock_intent is computed against tzdata 2026e (fixed UTC-7); environment artifact, not port logic. Reported, not patched."
  - "Host-local fixture shadow evidence ~/hermes-migration/shadow/ (runner run_shadow_evidence.py mirrors tests/test_shadow.py): ping_scan 12 decisions all would_post=false with second-pass dedupe; overnight_sweep exact 10-decision sequence; blocked_trigger fires BLOCKED_WAKE on the dispatch thread only; parity checker classifies matched/mismatched_kind/shadow_only/withheld/secretary_only exactly as the unit test asserts."
affects:
  - "mastermind:integrations/hermes_secretary/*"
  - "mastermind:integrations/hermes_runtime/*"
  - "mastermind:integrations/hermes_models/*"
  - "mastermind:integrations/hermes_delegate/*"
  - "mastermind:integrations/session_bridge/*"
  - "agentos/*"
confidence: high
reversibility: medium
decided_by: chairman-chris
decided_at: 2026-11-06
review_by: 2026-11-13
---

# Hermes bot migration authorized (evidence-gated)

The Chairman authorized the Grok Secretary → Hermes (mmmeta / mmsecretary)
role migration **in principle only** on 2026-11-06, on Mastermind #2082.
This record is the provenance anchor so the decision outlives any single
session.

## Gates named by the directive

1. **Shadow first.** 7-day retrospective parity against a read-only Slack
   export of #dotsandgroksecretary, then a 3-day forward shadow with Grok
   Secretary still live and posting.
2. **Cutover is a separate grant.** Nothing in this record authorizes live
   posting, cron install, profile enrollment, or arming `mmsecretary` /
   `mmmeta`. CUTOVER_AND_ROLLBACK.md stays the procedure document, not the
   permission.
3. **Secrets discipline unchanged.** Per-unit `0600` secrets files on the
   host; tokens never through chat, repo, prompt, or checked-in profile env.
4. **Grok Secretary stays live** throughout; rollback is removing the new
   units, never re-pointing the incumbent token.

## Current state at record time

- WP5 package merged at `ad6275a` (#2157), status PRODUCTION_INERT.
- Fixture shadow evidence green (see `evidence`); live retrospective export
  not yet collected.
- One environment-red in the suite (host tzdata vs tzdata 2026e) — reported
  for qualification review, not patched in place.
- `mmmeta` / `mmsecretary` profiles do not yet exist on the host; creation
  and enrollment ride the qualification lane, not this record.
