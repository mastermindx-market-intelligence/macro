---
key: GRANULAR-REGIME-RULE-PINS
question: >
  The regime-outlook mapping reads owner verdicts by the rules in producer code. When a producer
  function it cites changes, how is that noticed, and what must happen to the mapping?
answer: >
  A pin file (`config/regime_outlook_rule_pins.json`) records, for every decision function and
  config value the mapping's rows cite, the file, the name and the sha256 of its source text at
  the mapping's pin commit. A test (`tests/test_rates_command_outlook_rule_pins.py`) recomputes
  them from the files without importing the producers and fails the pull request that changes
  one. A failing pin means the cited rows are re-read. If a row's tokens, bands, middle token,
  default or guard assumption changed, the mapping gets a new version and the contract a new
  revision. If none did, the pin is updated and the re-read is recorded in the pin file's
  `reviews` list. A pin is never updated without that record. First use: PR #8348 changed what
  the transmission owner publishes for a missing input, so the mapping is `VERDICT_MAPPING_V2`
  (contract revision 3.2).
rationale: >
  The contract's rule R-E said a changed producer rule means the mapping is re-read and
  re-versioned, but named no record, no test and no remedy. The first producer change after the
  freeze (#8348, merged by this programme) was found only because an independent pass compared
  every cited function between the version 1 pin and main. Without a test, the next change would
  be carried silently. Without a rule for a failing pin, the cheapest response is to paste the
  new hash. Without the "no row changed" branch, one 428-line producer function would force a
  new version on every unrelated edit and bury the versions that matter.
alternatives:
  - option: Keep version 1, because the reader already refuses a null it does not list.
    why_not: >
      The table would state an owner vocabulary the owner no longer publishes, and its
      zero-default list would mark a genuine 0.00 as possibly missing. R-E exists to stop a
      stale table being carried because it happens to behave.
  - option: Hash `ast.dump` of each function.
    why_not: The dump format differs between Python versions; source text located by line span does not.
  - option: Import the producers and compare their outputs on fixtures.
    why_not: >
      The suite is offline and standard-library only, and behaviour on a few fixtures cannot
      show that a band or a default moved.
  - option: Re-version the mapping on every pin failure.
    why_not: >
      `conditions_snapshot` decides two rows inside 428 lines. Most edits to it change no row.
evidence:
  - "macro PR #8348 (698f58a0c74b) — `current_state` publishes null for a missing input; the eight numbers publish null through `_num`"
  - "independent read-only comparison of every A.1 decision function between 5f20adbd6be6 and 698f58a0c74b: `current_state` is the only source change; `breakeven_decomposition` moved 41 lines unchanged"
  - "research/macro_regime_intelligence/STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md — §18 (change log V1–V8) and Appendix A rule R-E"
  - "tests/fixtures/regime_outlook/readings_golden_v2.json — every recorded reading is unchanged from version 1; only the header's version, pin and table hash differ"
affects:
  - WS:RATES-INFLATION-COMMAND
  - config/regime_outlook_mapping_v2.json
  - config/regime_outlook_rule_pins.json
  - engine/rates_command_outlook.py
  - engine/rate_inflation_transmission.py
  - research/macro_regime_intelligence/
confidence: medium
reversibility: easy
decided_by: "session 8fdb22b4-e16b-46d8-8948-ecfe95ec27fb (Fable programme lead, Chairman assignment in issue #8317)"
decided_at: 2026-10-03
---

## What is decided

1. **A cited producer rule is pinned by its source text.** One entry per function or config
   value, each naming the mapping rows it decides.
2. **The pull request that changes a pinned rule sees the red.** The producer files and
   `config.yml` are in the `regime-outlook-mapping` job's paths.
3. **A failing pin is answered by a re-read, never by a paste.** The outcome is one of two:
   a new mapping version, or a `reviews` entry (date, commit, functions, finding) with the new hash.
4. **Version 2 changes no reading.** It lists `null` as an owner token on the five transmission
   `state` rows (the reader refuses it as `missing`), empties the zero-default list, and re-cites
   line numbers. The path tables are the same.
5. **The wiring slice waits for a post-repair file.** It merges only when the committed
   `data/transmission/latest.json` was last written by a commit that descends from `698f58a0c74b`.

## What is not decided here

- Whether `conditions_snapshot`'s labour read and breadth divergence should move into small
  functions so their pins trip less often. That is a request to the conditions owner.
- Any change to a path, a condition or a family. None was made.
