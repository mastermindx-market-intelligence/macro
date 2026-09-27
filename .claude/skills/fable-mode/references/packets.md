# Packets and templates — copy these, do not paraphrase them

Every artifact the seat loop names has a shape here. Shapes are load-bearing: a commission missing its `NOT DONE UNLESS` returns the clean half; a return missing its `GAPS` hides what was skipped; a ruling missing its alternatives gets relitigated. Section labels are exact — in this fleet several are hook-checked (`.claude/agent-routing.json` lists the required labels per route; the return guard checks the return packet); in another harness use the same labels so packets stay portable across seats and models.

Contents: 1 Commission packet · 2 The turn-ending clause · 3 Return packet · 4 Adjudication scorecard · 5 REQUEST_REPAIR · 6 Lane matrix · 7 Program file · 8 Ledger block · 9 Wave plan and pre-mortem · 10 Ruling and discovery records · 11 Handoff · 12 Hold note, watcher line, session-end line

---

## 1. Commission packet

Generic skeleton of the labels most routes share. Then **add every label the per-route table below lists for your route** — in this fleet the routing hook denies a commission that is missing any of them (a `review` needs `ARTIFACT TO ATTACK` and `REVIEW STANDARD`; a `census` needs `QUESTIONS`; a `design` needs `USER JOB`, `FROZEN CONSTRAINTS`, `REFERENCES`, `VISUAL VERIFICATION`). Keep every label you include; write "none" rather than omit.

```
ROUTE: <extract|census|research|draft|analysis|debug|build|review|design|orchestration>
MODEL/TIER: <explicit — never inherited; a prompt label for the record — the harness's own model parameter is what a guard checks, so set both>
OPERATION KEY: <program / wave / lane id>

MISSION: <one sentence: the deliverable, as a noun>
WHY: <what decision or downstream lane this feeds; what happens if it is late or wrong>
SCOPE: <exactly what is in>
OUT OF SCOPE: <what is adjacent and must not be touched, by name>
FROZEN SPEC: <interface, names, types, units, ordering, behavior — pasted, not pointed to>
OWNED FILES: <exact paths this lane may write; nothing else>
INPUTS: <exact paths or pasted content; reference images as committed file paths>
TESTS: <named tests to add or make pass; the narrow gate; the baseline count handed down>
NOT DONE UNLESS:
  - <observable criterion 1 — "the new test fails on the old code and passes on the new">
  - <observable criterion 2 — counts: "11 tests added", "3 files created">
  - <observable criterion 3 — evidence to attach: command + output>
EVIDENCE REQUIRED: <the receipts the return must carry: commands, shas, run ids, paths, counts>
BUDGET: <turns / time / tokens; what to do when exhausted: return a partial packet>
ANSWER FIRST: <the one question whose answer decides the seat's next act>
ROUTE-SPECIFIC LABELS: <every label the table below lists for this route, each with content>
RETURN: STATUS / RESULT / EVIDENCE / GAPS / DEVIATIONS  (+ NEXT SEAT ACT for orchestration lanes — recommended, not guard-enforced)
<the turn-ending clause, section 2, verbatim>
```

Per-route required labels in this fleet (the hook checks these exact words):

| route | required sections |
|---|---|
| extract | MISSION · SCOPE · NOT DONE UNLESS · RETURN |
| census | MISSION · WHY · SCOPE · OUT OF SCOPE · QUESTIONS · NOT DONE UNLESS · EVIDENCE REQUIRED · RETURN |
| research | MISSION · WHY · SCOPE · OUT OF SCOPE · QUESTIONS · SOURCE STANDARD · NOT DONE UNLESS · EVIDENCE REQUIRED · RETURN |
| draft | MISSION · AUDIENCE · INPUTS · OWNED FILES · CONSTRAINTS · NOT DONE UNLESS · RETURN |
| analysis | MISSION · DECISION SUPPORTED · SCOPE · OUT OF SCOPE · ASSUMPTIONS · NOT DONE UNLESS · EVIDENCE REQUIRED · RETURN |
| debug | MISSION · SYMPTOM · SCOPE · OUT OF SCOPE · NOT DONE UNLESS · EVIDENCE REQUIRED · RETURN |
| build | MISSION · WHY · SCOPE · OUT OF SCOPE · FROZEN SPEC · OWNED FILES · TESTS · NOT DONE UNLESS · RETURN |
| review | MISSION · ARTIFACT TO ATTACK · REVIEW STANDARD · SCOPE · NOT DONE UNLESS · EVIDENCE REQUIRED · RETURN |
| design | MISSION · USER JOB · SCOPE · OUT OF SCOPE · FROZEN CONSTRAINTS · REFERENCES · OWNED FILES · VISUAL VERIFICATION · NOT DONE UNLESS · RETURN |
| orchestration | MISSION · WHY · SCOPE · OUT OF SCOPE · NOT DONE UNLESS · RETURN |

A review commission's `REVIEW STANDARD` names the stance: for make-or-break calls, *"Your stance is REFUTE. Find every reason this should not be approved. Do not play devil's advocate — actually look for disqualifying defects."*

**Design packets carry the two-theme law.** For any user-facing surface, `VISUAL VERIFICATION` and `FROZEN CONSTRAINTS` must name: DARK TREATMENT and LIGHT TREATMENT as two art directions (shared information architecture, semantics, spacing and type scales; material treatment may differ — depth and restrained glow in dark, white material and hairline discipline with shadow in light), which mechanisms intentionally differ, the reference or baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390) posted as committed image paths. Token substitution alone is never proof of a light design. A design return missing the light art direction or its evidence is `PARTIAL` or `BLOCKED`, never `PASS`, and a builder stops and escalates rather than inventing a translation. Read the repository's design doctrine (`docs/DESIGN_DOCTRINE.md` in this fleet) before writing the packet; design *choices* stay with the design tier, and a builder implements only a fully specified spec.

## 2. The turn-ending clause (append verbatim to every commission)

```
Do not end a turn until you are emitting the return packet. If you catch yourself writing
"now let me…" or "next I'll…", either keep going in the same turn or stop and return what
you have. A partial packet with honest, specific GAPS is useful and I can act on it; another
status note is not. Answer the ANSWER FIRST question before anything else.
```

## 3. Return packet (the worker's final message IS the packet)

```
STATUS: <PASS | PARTIAL | BLOCKED | FAIL>          # exactly one of these words
RESULT: <what was delivered, as facts with counts: "10/10 items; 11/11 tests; 3 files">
EVIDENCE: <receipts: commands run with output tails, shas, run ids, paths, screenshots by path>
GAPS: <what was NOT done or NOT verified, specifically; "none" only if true>
DEVIATIONS: <where the work departed from the packet and why; "none" only if true>
NEXT SEAT ACT: <orchestration lanes only — the exact seat-only act recommended, with its gates already verified>
```

`EVIDENCE: none` is not a packet. `GAPS` has two kinds of entry, and the packet should say which: a **criterion gap** (a `NOT DONE UNLESS` item not met or not verified) and a **disclosure** (something adjacent that was noticed but was outside scope, or a bound on what was searched). A `PASS` may carry disclosures — honest scope statements are wanted, never punished — but a `PASS` may not carry a criterion gap; that is a `PARTIAL`. The seat issues repairs only against criterion gaps.

## 4. Adjudication scorecard (the seat fills this for every DELIVERED return)

```
LANE: <id>   ROUND: <n>   ARTIFACT OPENED: <paths/commands actually read by the seat>
COUNTS: items <k>/<n> · tests <k>/<n> · files <k>/<n> · other <…>
NOT DONE UNLESS: [ ] c1 <evidence or gap>  [ ] c2 …  [ ] c3 …
LENS 1 (what it was told to look for): <…>      LENS 2 (bounds it actually searched): <…>
SUB-REVIEWS COMMISSIONED BY THE LANE: <each: CONCLUDED with verdict | OPEN — resume before accepting>
LADDER RUNG REACHED: <DELIVERED | CI | MERGED | PRODUCTION_PROOF>
DECISION: <ACCEPT | REQUEST_REPAIR (→ section 5) | REJECT | ESCALATE>   REASON: <one line>
```

## 5. REQUEST_REPAIR

```
REQUEST_REPAIR — lane <id>, round <n> of max 2 identical rounds
DEFECTS:
  1. <defect> — CLOSES WHEN: <exact re-check, command, expected output/count>
  2. …
UNCHANGED: <what must not be touched in the repair>
RETURN: the full packet (section 3), with the re-check outputs under EVIDENCE
```

Two rounds without observable delta → do not issue a third; change tier, split the packet, change owner, or take the bounded remainder under L.7, and say which in the ledger.

## 6. Lane matrix (one row per lane, in the program file; update at S.4 and S.6)

```
| lane | owner/tier | owned files | worktree/branch | sentinel/artifact | budget | state | last verified (UTC, how) | watcher id/cadence |
|------|-----------|-------------|-----------------|-------------------|--------|-------|--------------------------|--------------------|
| L1   | builder/cheap | engine/x.py, tests/test_x.py | wt-l1 / claude/l1 | $S/l1.out "L1: " | 90 min | RUNNING | 12:40Z pgrep+mtime | w-l1 / 150s |
```

States: `PLANNED · QUEUED · RUNNING · DELIVERED · REPAIR-n · SILENT · DEAD · THRASHING · ACCEPTED · MERGED · LIVE`.

## 7. Program file (continuation record) — skeleton

```
# <PROGRAM> — continuation (<YYYY-MM-DD>, seat <id>)
## 0 Mission and exit gate
<one sentence> — DONE WHEN: <rung + evidence>
## 1 Carrier
<where rulings arrive> — LAST CONSUMED EDGE: <timestamp / message id>
## 2 Wave plan
| wave | lanes | gate (written before launch) | status |
## 3 Lane matrix
<section 6>
## 4 Ledger
<section 8>
## 5 Open rulings / holds
<each: authority, release condition, what you did about it>
## 6 Do-not-redo
<accepted work with the sha/record that accepted it>
## 7 Danger areas
<what will bite the next session>
## 8 Next action (exact command or act)
```

## 8. Ledger block

```
DECIDED: <choice — one-line reason — date>  (reversed only by writing "reversing X because Y" with new evidence)
FACTS:   <observation — source: path:line or command — date>
OPEN:    <question — what would resolve it — who owns resolving it>
NEXT:    <single next action>
```

## 9. Wave plan row and pre-mortem

```
WAVE <n>: lanes <…>  CRITICAL PATH: <…>  FORK LANE: <…>
GATE (written before launch): <what merged / proven live / accepted, with evidence, by when>
PRE-MORTEM ("it failed a week later because…"):
  1. <mechanism> → TRIPWIRE: <packet clause | watcher | integration check>
  2. …  (4–6 entries)
```

## 10. Ruling and discovery records

```
RULING <KEY>
question: <…>
answer: <…>
rationale: <…>
alternatives rejected: <option — why not> ×n
evidence: <receipts>
reversibility: <easy | costly | irreversible> — what would reopen this
scope: <exactly what this binds; what it does not>
decided by / at: <…>
```

```
DISCOVERY <KEY>
fact: <…>
verified by: <command / observation, date>
falsifier: <the observation that would overturn it>
so_what: <what a session does differently because of it>
```

## 11. Handoff (leaving state another must resume)

```
workstream / operation: <…>     session: <…>     model: <…>     ended_because: <…>
mission: <…>
state_before: <…>
next_actions: [<exact, ordered>]
do_not_redo: [<accepted work + the sha/record that accepted it>]
danger_areas: [<…>]
unresolved: [<…>]
changed: [{path, what}]
verified: [{claim, command, result}]     # a claim without a command is not verified
```

## 12. One-liners

Hold note (the only lawful answer to harness pressure during a watched wait, once):
```
HOLD: waiting on <thing> at <head/id>; watcher <id> @ <cadence> owns it; re-invoked by <event>. No poll this turn.
```

Watcher registration line (in the lane matrix the moment it is armed):
```
WATCH_ARMED: <watcher id> on <endpoint> @ <cadence>, budget <…>, exits on <sentinel/condition>
```
If no real watcher could be registered: `WATCH_UNAVAILABLE: <surface checked> — <exact failure>` — never "waiting".

Session end (last line of a substantial session):
```
SESSION END: <PROVEN_OUTCOME | EXACT_HUMAN_GATE | EFFECT_UNKNOWN | ALL_SCOPED_LANES_BLOCKED | DURABLE_EXECUTION_RUNNING>
```
