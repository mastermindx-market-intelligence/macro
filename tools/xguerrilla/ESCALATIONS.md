# Escalations — the file-based question channel

Workers run unattended: a subagent cannot ask the Chairman a question mid-run and
cannot message the supervisor. So policy questions go to disk, and the answer
comes back on disk. A worker that stops to wait is a broken worker; a worker that
invents policy is a worse one.

Ground: §26.2 (worker lifecycle), §27 (open items). Procedure for the events
below: `RUNBOOK.md` §2 (challenge), §3 (degraded), §4 (shadow run), §5 (restore).

## 1. Where it lives

    ~/.xguerrilla/escalations/
      open/         questions awaiting a human
      answered/     questions with a replied block
      superseded/   questions closed by later evidence or by a rule change
      ANSWERS.md    append-only index of every answer, newest first
      TEMPLATE.md   the block below, copy-pasted

One file per question: `open/Q-YYYYMMDD-HHMM-<handle-or-cohort>-<slug>.md`. The
`Q` is literal, `slug` is two or three hyphenated words. Never edit a question
after it is written — appends only, so the record shows what was actually asked.

## 2. Append format — exact

    ## Q: <one line, ends in a question mark>
    - **child:** <handle> | cohort | global
    - **state:** <ACTIVE|COOLING|QUARANTINED|DRAFT> · slot <pool-NN> · cell <CELL-01>
    - **attempted:** <what you were doing, one sentence, no backstory>
    - **evidence:** `<exact command>` → <exit code and the one line that matters>
      or `<path>:<line>` → <the line>
    - **options:**
      1. <option> — <cost, reversibility>
      2. <option> — <cost, reversibility>
      3. <option> — <cost, reversibility>
    - **recommend:** <n> because <one clause>
    - **stopgap:** <what you did so you are not blocked> · reversible: yes|no
    - **revisit by:** <YYYY-MM-DD> (default: +1 day for L1, +3 for L2, none for L3)

Rules for the fields: `evidence` carries the verbatim command and its real exit
code, never a summary of it. Options are three concrete actions, not a spectrum.
`stopgap` is mandatory; a question with no stopgap is a halt in disguise.

## 3. States

| State | Set by | Meaning | Worker may proceed? |
|---|---|---|---|
| `open` | worker, on write | waiting | yes, on the stopgap only |
| `answered` | human, reply block | decided | yes, per the directive |
| `superseded` | human or any worker | evidence or rules moved on | yes, per the newer thing |

Transitions: `open → answered` (answer block appended, file moved to `answered/`),
`open → superseded` (only if the question is provably overtaken — state by what).
`answered` never goes back to `open` — a wrong answer is a new question.
Move the file, update `ANSWERS.md`, then the index and the directory agree.

## 4. Who answers, and how answers arrive

The **Chairman** answers L2 and L3. The **desk operator** answers L1 alone and may
answer L2 if the Chairman is off the box. Nobody else. An answer is an appended
block, never an edit:

    ### A: <YYYY-MM-DDTHH:MMZ> — <asked-by-role> → <answerer-role>
    - **directive:** <the decision, imperative, unambiguous>
    - **why:** <one clause>
    - **scope:** <handle | cohort | global> · until <date or "rule change">
    - **follow-up:** <what to record or verify, or "none">

An answer without `directive` and `scope` is not an answer. Answers are picked up
on the worker's next start — every worker step begins by listing `answered/` and
reading the blocks for its own handles — and answers also land in `ANSWERS.md` so
a fresh worker that never saw the question still gets the rule.

    python3 -c "import glob,os; [print(p) for p in glob.glob(os.path.expanduser('~/.xguerrilla/escalations/answered/*.md'))]"

## 5. The non-blocking rule

1. Ship the **safest reversible option**, not the best one. Cooling beats
   activating, stub beats guess, no-write beats write.
2. Record it in `stopgap`, with `reversible: yes|no`. Any `no` is L2 minimum.
3. Keep working the rest of the queue. One open question never stops the run.
4. On an answer, carry out the directive even if it contradicts the stopgap, and
   note the switch in telemetry.
5. Never guess on: anything that changes a handle's identity, a persona's beat,
   the slot binding, or the action budget. Those four are policy, not judgement.

## 6. Triggers — interrupt a human for these

| Trigger | Level | Who | Default stopgap |
|---|---|---|---|
| Account challenge, lockout, or login interstitial | L1 | desk | `cool` 180 min, `verify`, `snapshot`, log a `challenge` row |
| Two consecutive replies fail `typing.assert_natural()` | L2 | Chairman | quarantine the child; do not post through the band |
| Follower delta that reads as a shadowban (flat or negative ≥ 3 days while actions hold) | L2 | Chairman | drop to rail-only, `shadow` run, hold writes |
| A proxy slot fails twice (two children, or twice for one child) | L2 | Chairman | `degrade --reason "slot <pool-NN>"`; bind the child to a spare slot only on answer |
| Anything that risks a parent's identity (bio, pinned, handle-adjacent change, first reply to a big account) | L3 | Chairman | hold the write; draft only |
| Gate criterion in §26.9 fails during the pilot | L3 | Chairman | freeze the cohort, keep the day's evidence |
| Supervisor reports a child `ACTIVE`, not cooling, not runnable | L1 | desk | `status`, then quarantine (never re-`activate` blind) |

`cool`/`quarantine`/`retire` are `Supervisor` calls, not new code:

    python3 -c "from tools.xguerrilla.supervisor import Supervisor; s=Supervisor('$HOME/.xguerrilla/state.db'); s.cool('kid.audit',180); s.close()"

Time to first answer: L1 same day, L2 within 24 h, L3 before the next write to
that handle. Nothing escalates faster by being resent — bump the file's
`revisit by` instead.

## 7. Not an escalation

Selector miss on one step, one `relogin_fraction` blip, a shadow-run step that
fails and is re-run green, a slow node, a persona wording change inside the beat.
Fix and record; do not open a question. `RUNBOOK.md` §2 and §4 already cover them.

## 8. Close-out

Day 14 of the pilot: every `open/` file is either answered or superseded, and the
gate verdict cites each answer it leaned on. A question still open at the gate is
an unanswered gate criterion, not a footnote.
