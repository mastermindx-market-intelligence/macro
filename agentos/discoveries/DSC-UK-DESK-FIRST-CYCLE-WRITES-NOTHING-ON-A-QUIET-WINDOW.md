---
key: UK-DESK-FIRST-CYCLE-WRITES-NOTHING-ON-A-QUIET-WINDOW
claim: >
  On main 148d1bfec8, engine.uk_policy_brain.run() treats a reachable GOV.UK
  feed whose every item is older than max_age_days as an empty feed. With no
  prior site/uk_policy.json it returns None and writes nothing, so the first
  whitehouse-sentinel cycle on a quiet window leaves the Policy Watch card
  unrendered.
falsifier: >
  git show 148d1bfec8:engine/uk_policy_brain.py and read run(). This claim is
  false if the empty-items branch persists state no_new when latest() is None,
  or if run 35819272085 committed site/uk_policy.json. A live re-check is
  python -c "from engine import uk_policy_brain as u; print(len(u.collect(4.0, window=False)), len(u.collect(4.0)))"
  — the 2026-09-23 05:04Z probe was 20 parsed and 0 inside the window.
so_what: >
  Do not read a missing site/uk_policy.json after a successful sentinel cycle
  as "the desk is off". A quiet window must persist state no_new (newest item,
  or the prior headline) and log uk_policy: state=no_new. Only a feed that
  returns nothing from search and atom may write nothing, and that path must
  log a warning. Keep tests/test_uk_policy_brain.py on the gate:code
  uk-policy-desk job; outcome-spine and unrun-register-honesty are gate:data
  and do not run in a pull-request pack.
kind: landmine
verified_at: 2026-09-23
verified_by: >
  git show 148d1bfec8:engine/uk_policy_brain.py (run() empty-items branch) and
  scripts/build_policy_watch.py:380. Seat probe of GOV.UK at 2026-09-23 05:04Z
  (search 46227 bytes, 20 items, newest 2026-09-18T13:53:43Z, collect(4.0) == 0).
  GitHub Actions run 35819272085 committed 86904927 with no uk_policy artifact.
  grep -rl uk_policy agentos/ lists handoffs only, no DEC file.
scope:
  - macro
  - engine/uk_policy_brain.py
  - scripts/build_policy_watch.py
  - .github/workflows/whitehouse-sentinel.yml
confidence: verified
---

# A quiet first cycle of the UK policy desk writes nothing

#7351 turned the desk on. The first sentinel cycle after that merge still
wrote no `site/uk_policy.json`. The feed was reachable. Every HM Treasury
item was older than four days, `collect(4.0)` returned nothing, and `run()`
with no prior record returned None without a log line. Policy Watch only
draws the card when that file exists, so the page looked as if the desk
were off.

That is a display gap, not a signal change. The owner decision for this
second-country desk is DEC:F02-POLICY-GEO-OWNER-MAP (MO-PAID-023 mirrors the
whitehouse desk). `grep -rl uk_policy agentos/` does not list that file or
any other `agentos/decisions/` record. It lists three handoffs only
(`MARKET-OS-2026-09-10-policy-watch-adoption`,
`MARKET-ONTOLOGY-META-CEO-B-2026-09-13`,
`MARKET-OS-2026-09-13-policy-watch-r2`). Activation itself is commit
`12784c0fcf` / #7351, whose message names no DEC key.

After this packet, a quiet reachable feed persists `no_new` and the sentinel
log shows the verdict. An empty feed warns. The card can render.
