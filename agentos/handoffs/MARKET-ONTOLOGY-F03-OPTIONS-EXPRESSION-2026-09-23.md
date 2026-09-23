---
workstream: "WS:MARKET-OS"
session: claude/mo-a-3-a-f03-w3-1a-catalyst-links-producer
model: local
ended_because: complete
mission: >
  A-F03-W3-1a adds the first production caller of bind_events. The nightly
  builder binds one session of live-flow events to earnings and FOMC
  catalysts and writes a context-only histogram. The options page is not
  this packet. The pull request stays a draft until the seat ratifies it.
state_before: >
  engine/options_catalyst_link.py was on main with tests only. No script
  called bind_events. The episode step already read live_flow/events/{DATE}.jsonl.
  FOMC dates lived in a private list in engine/event_calendar.py.
changed:
  - path: scripts/build_options_catalyst_links.py
    what: Nightly builder. Reuses fetch_event_stage and discover_event_sessions. Calls bind_events. Writes site/options_catalyst_links/<session>.jsonl and latest.json. An earnings knowledge date is the business-day inverse of the age assess returns. A Saturday or Labor Day run of a Friday row stamps Friday.
  - path: engine/event_calendar.py
    what: Added fomc_decision_dates. Pure read of the existing FOMC list. Nothing removed.
  - path: .github/workflows/daily.yml
    what: One step, id options_catalyst_links, immediately after options_signal_episode_publish. continue-on-error true, timeout 5 minutes, same R2 env as the episode step.
  - path: .github/ci/legacy-jobs.yml
    what: gate code job options-catalyst-links running the three catalyst-link suites.
  - path: tests/test_build_options_catalyst_links.py
    what: Envelope, histogram sum, no stage, empty plane, earnings conversion, FOMC calendar, data-path refusal, authority block, pure FOMC accessor, and the age assess returns. A Saturday or Labor Day run of a Friday row stamps Friday. A Thursday event loses the earnings link.
  - path: tests/test_options_catalyst_links_nightly_shape.py
    what: Text check that the daily step and the gate code job match the packet.
  - path: agentos/decisions/DEC-F03-W3-1-CATALYST-BINDING-FIRST-PRODUCTION-CALLER.md
    what: Records why the caller is a nightly builder rather than a render-time bind, a store host, or a macro-free first cut.
  - path: research/market_intelligence_productization/MARKET_ONTOLOGY_F03_W3_1A_CATALYST_LINKS_PRODUCER_2026-09-23.md
    what: States what the producer is, what it is not, and the ten-percent rule for chartering the page.
decisions:
  - "DEC:F03-W3-1-CATALYST-BINDING-FIRST-PRODUCTION-CALLER"
verified:
  - claim: The producer suite, the existing binder suite, and the nightly shape suite pass.
    command: "/opt/homebrew/bin/python3.14 -m pytest tests/test_build_options_catalyst_links.py tests/test_options_catalyst_link.py tests/test_options_catalyst_links_nightly_shape.py -q"
    result: "58 passed in 1.85s"
  - claim: Agent OS records for this packet validate.
    command: "python3 scripts/agentos.py validate"
    result: "agentos: 1208 records (69 workstreams, 341 decisions, 302 discoveries, 496 handoffs) — 0 error(s), 90 warning(s)"
  - claim: The new step, the new job, the accessor, and the two calls are present, and this change does not edit templates, site, or data.
    command: "grep -c bind_events scripts/build_options_catalyst_links.py; grep -n fomc_decision_dates engine/event_calendar.py; grep -n options_catalyst_links .github/workflows/daily.yml; grep -n options-catalyst-links .github/ci/legacy-jobs.yml; git diff --stat HEAD -- templates site data"
    result: "bind_events is called; fomc_decision_dates is at engine/event_calendar.py:141; the daily step id is options_catalyst_links at line 3347; the job is options-catalyst-links at legacy-jobs.yml:5368 with gate code on the following lines; templates, site, and data are unchanged against HEAD."
unverified:
  - claim: GitHub Actions on the pushed head is green.
    what_would_verify: gh pr checks after the draft is open. This packet does not claim that.
unresolved:
  - GitHub checks on the pushed head are not claimed green.
  - The seat has not ratified, readied, or merged this draft.
  - W3-1b, the options page, is not chartered. The seat charters it only after reading three nightly histograms.
next_actions:
  - Read site/options_catalyst_links/latest.json after the first three nightlies. Charter the page only if BOUND plus STALE_CATALYST is at least 10 percent of the events that were bound.
  - Do not mark this pull request ready. The seat does that.
do_not_redo:
  - Do not add a second collector, a second R2 client, or a second event plane. Reuse fetch_event_stage and discover_event_sessions.
  - Do not bind at render time inside build_options_command.
  - Do not write under data/. write_links refuses that tree. The output directory is site/options_catalyst_links/.
  - Do not park these suites in a gate data job, and do not add a waiver row.
  - Do not build the options page in this packet.
danger_areas:
  - An availability receipt is not an event. Counting it as a dropped row inflates the histogram. Only decision events and bare event rows enter the binder.
  - known_symbols must be uppercase. The membership test is exact on the uppercased root.
  - stale false with no age is not fresh. fields_from_assessment turns that into no verdict, and the binder then treats the candidate as untrustworthy.
  - The earnings age is a business-day index step. Walking NYSE sessions back from the last session stamps Thursday for a Friday row when the run is Saturday or Labor Day. A Thursday event then keeps an earnings link that was not known yet. Invert the same index assess used.
  - Do not catch the drift ValueError from bind_events. A drifted record is the contract firing.
  - FOMC candidates belong on CalendarContext.macro_catalysts. Putting them in the per-root map double-counts them.
  - The shared calendar's third-Friday flags stay None. The binder computes those from each event's expiry.
---

# Handoff — catalyst links producer (A-F03-W3-1a)

Branch `claude/mo-a-3-a-f03-w3-1a-catalyst-links-producer`. Draft pull request. Base `main`. The seat ratifies, readies, and merges. Do not mark it ready from this handoff.

The nightly step `options_catalyst_links` sits immediately after `options_signal_episode_publish` in `.github/workflows/daily.yml`. It runs `python -m scripts.build_options_catalyst_links` and treats a failure as non-fatal. Output lands in `site/options_catalyst_links/`. The site commit already runs `git add data/ site/ reports/` in `scripts/ci/daily_engine_commit_outputs.sh`. The comment in daily.yml still says `git add site/ covers`. No staging edit was required. `site/options_catalyst_links/` is not gitignored.

`latest.json` is the histogram a later packet would read. The page is chartered only if, over the first three nightlies, `BOUND` plus `STALE_CATALYST` is at least 10 percent of the events that were bound (`counts.events` minus `counts.dropped_malformed`). The seat reads the numbers.
