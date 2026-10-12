---
workstream: WS:CONSUMER-DEFENSIVE-CDV1
session: claude/cdv1-seat-wave1
model: fable
ended_because: ci_handoff
mission: >-
  Wave-1 checkpoint of the Fable Meta-CEO CDV-1 program (seat 251f88c8):
  T7 re-scoped to a CONTENT + CONTRACT spec under the Semiconductors-owned
  base, foundation integration map and release census merged, T1 in
  fabric repair against a frozen reviewer probe suite.
state_before: >-
  Ledger + seam audit merged (#7880), Agent OS records merged (#7906).
  T1 lane #7905 had shipped a first head that two Opus read-only rounds
  rejected (fixture-only vocabulary, replay compared value only, drivers
  by position, calendar-quarter arithmetic, fact_id = fact_{metric}); GLM
  repair rounds discharged rulings with self-written co-varying tests.
  No T7 spec, no foundation map, no release census existed.
changed:
  - path: research/consumer_defensive/cdv1_program/README.md
    what: Wave-1 ledger — per-task states, merged records, T1 rulings R1–R16 summary, lane incidents, CI wiring, next steps.
  - path: agentos/workstreams/WS-CONSUMER-DEFENSIVE-CDV1.md
    what: wave status in_progress, next_action, artifacts, DEC:CDV1-FOUNDATION-INTEGRATION, foundation-integration boundary section.
  - path: agentos/decisions/DEC-CDV1-FOUNDATION-INTEGRATION.md
    what: NEW — CDV-1 integrates into the Semiconductors-owned base instead of building a shell.
  - path: agentos/handoffs/WS-CONSUMER-DEFENSIVE-CDV1-2026-09-24.md
    what: NEW — this handoff.
verified:
  - claim: "#7904, #7910, #7917 are merged on main"
    command: "gh pr view <n> --json state,mergedAt"
    result: "MERGED 2026-09-24 09:59Z / 09:59Z (issued) / 09:56Z"
  - claim: "the T1 probe suite has one author and was committed RED"
    command: "git log --format=%an origin/claude/cdv1-t1-pg-profile-facts -- tests/test_pg_economic_observations_probes.py | sort -u; venv/bin/python -m pytest tests/test_pg_economic_observations_probes.py -q at 7804e24a"
    result: "one author; 20 failed in 2.85s at 7804e24a; 10 passed / 10 failed at b8bb513e93"
  - claim: "main lacks the foundation rights gate the Q6 fold binds to"
    command: "git show origin/main:engine/theme_graph/rights.py | grep -nE '^def (load_registry_snapshot|assert_current_emission_allowed)'; git show origin/main:config/theme_sources.yml | grep -c sec_edgar"
    result: "no matches; 0"
unverified:
  - claim: "the wired gate job runs both suites green on a repaired T1 head"
    what_would_verify: "ci-pack run on the exact head of #7905 after round 5 (job earnings-economic-dossier)"
unresolved:
  - "T1 #7905 repair round 5 (MiniMax-M3, mini2) — 16 failures grouped G1–G6 remain at b8bb513e93."
  - "Real PG source admission through earnings-public-wire.yml needs credentials (likely EXACT_HUMAN_GATE at T8)."
  - "Operator item: exclude /Users/mini2/lanes from Spotlight (mds indexing drove load to 19–22 and refused a lane admission)."
next_actions:
  - "Consume round 5 of cdv1_t1_pg_facts (seat log remote_lane_v8_mini2_cdv1_t1_pg_facts_r5.log): both suites green in a clean venv (pip install pytest pyyaml), grep gate empty, probe file single-author."
  - "Final Opus READ_ONLY round on #7905 bounded to rulings R7–R16; CI on the exact head; gh pr ready 7905; merge-on-green; merge."
  - "Dispatch cdv1_t2_source_currentness ∥ cdv1_t3_interpretation off fresh main (args in the kit carry the CI dependency law, the T7 contract block and the Q6 fold); then T4, then T5 ∥ T6."
  - "T7 UI build and T8 release gates wait for #7870; re-census its head before either."
do_not_redo:
  - "Do not build a CDV-1 shell, slot, evidence vocabulary or rights profile — the base is #7870 (DEC:CDV1-FOUNDATION-INTEGRATION)."
  - "Do not re-review T1 dimensions R1–R16; the probe suite tests/test_pg_economic_observations_probes.py is the frozen spec."
  - "Do not re-run the release census or the foundation map; both are merged with STATUS: ANSWERED."
  - "Do not re-ACK the program on #7792 (PICKUP_ACK comment 5807883214) and never put implementation on #7792."
danger_areas:
  - "A repair lane that edits the probe file or rewrites original-suite assertions without citing a ruling id is a rejected round."
  - "A test added to the gate job's run: line without its paths: entry reds contract-delta on every later PR."
  - "glm-5.3 fix lanes on this task have collapsed 3× into gibberish with rc=0 and a dirty worktree — read r1_fix.out.md and salvage the worktree before relaunching."
  - "Sparse worktree: never write data/ or site/; never git add -A."
prs: [7880, 7904, 7905, 7906, 7910, 7917]
decisions:
  - "DEC:CDV1-PLAN-SEAM-RULINGS"
  - "DEC:CDV1-FOUNDATION-INTEGRATION"
---

Cold-stranger summary: the CDV-1 vertical is built one PR per plan task on the
external fabric; the seat adjudicates, merges and keeps this ledger. Wave 1
merged the T7 content+contract spec, the foundation integration map and the
release census, and pinned T1's acceptance to a frozen 20-probe suite that a
repair lane must turn green without touching.
