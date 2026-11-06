---
key: ACCEPTANCE-PROBE-CAN-FIRE-ON-THE-NEGATIVE-CASE
claim: >
  An acceptance probe whose trigger is a token COUNT, an exit status, or any other proxy for
  the question being asked can report SUCCESS while the system is in the negative state, and
  the failure is invisible because a passing probe is never re-read. Concrete instance,
  2026-09-29: a watcher waiting for the nightly to publish `session_anchor` onto a served OHLC
  document triggered on `[ "$out" != "0" ]`, where `$out` came from
  `ssh host 'grep -c "\"session_anchor\"" FILE || echo 0'`. `grep -c` PRINTS "0" and EXITS 1
  on zero matches, so the `|| echo 0` fallback appended a second token; the two lines
  whitespace-stripped to "00", which is not "0", and the watcher fired instantly against a
  completely unstamped file 85 minutes before the cron was due. Two further instances in the
  same 24 hours, different surfaces, identical shape: a mutation control that reported
  "1 passed" while silently never applying the mutation (the green measured a broken harness,
  not a strong test), and TERMINAL-02's DOM harness that reported the live-bar defect FIXED on
  a build containing none of the fix, because the EMA it polled was a render-time recompute
  rather than the chart's own series.
falsifier: >
  Show `grep -c` on a zero-match file exiting 0, or printing nothing, on the platform in use
  (`grep -c x /dev/null; echo "rc=$?"` prints `0` then `rc=1`). More generally: a probe whose
  trigger condition and whose reported evidence body are computed from the same read, so they
  cannot disagree, is not an instance of this. A probe that has been demonstrated to emit BOTH
  outcomes against known-positive and known-negative inputs before being armed is not an
  instance of this.
so_what: >
  Three rules, each of which would have caught one of the three instances alone. (1) Make the
  probe answer a SEMANTIC question and return exactly one token — ask the document for its
  anchor and print the JSON or the literal NONE, never count matches and never lean on an exit
  status that doubles as data. (2) Prove BOTH branches before arming: a watcher that has only
  ever been observed saying "not yet" has not been shown capable of saying "yes", and arming it
  converts an untested predicate into an unattended one. Run it against a known-stamped
  artifact and a known-unstamped one and check it flips. (3) Have the probe print the evidence
  that justifies its own trigger, so a contradiction is visible in the output — this is what
  actually caught the instance above: the "CRON STAMP LANDED" banner was immediately followed
  by its own body reporting `session_anchor: null`, and a probe that had only printed the
  banner would have ended the session on a fabricated observation. The general principle: a
  check that cannot physically observe the thing under test will report on whatever it CAN
  observe, and that reading is uncorrelated with the truth. Ask what this probe would print if
  the change had never been deployed; if the answer is "the same thing", it is not evidence.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Reproduced directly against the production VPS: the exact remote command returned the two
  bytes `0\n0` (`od -c` confirmed), stripping to "00". The watcher's own emitted report is
  retained and shows the banner "###### CRON STAMP LANDED — 2026-09-29T20:05:57Z ######"
  followed by "session_anchor: null" and "served session_anchor: null", with the box clock at
  20:05Z against a cron scheduled for 21:30Z. The replacement probe was then demonstrated on
  both branches before arming — a document stamped by mastermind-terminal #772 returns
  `{"v": 1, "date": "2021-06-28", "index": 0, "basis": "feed"}` and fires, a sidecar with no
  anchor returns NONE and does not.
scope:
  - any acceptance, deploy or CI watcher
  - mastermind-terminal
  - macro
confidence: verified
---

Worth a record rather than a comment because all three instances passed review as written. Each
one reads as correct: counting occurrences of a field IS how you check for a field, a mutation
harness that reports a test count IS reporting the test, and polling a rendered indicator value
IS observing the chart. What they share is that the quantity actually measured is one indirection
away from the claim, and every such indirection is a place where a true reading and a false one
produce the same output.

The asymmetry that makes this expensive: a probe that wrongly says "not yet" costs a retry and is
self-correcting, while a probe that wrongly says "done" ends the investigation. So the effort of
proving both branches is not symmetric either — it is almost entirely about establishing that the
positive branch means something.

Related: DSC-CANONICAL-SESSION-GRID-CHANGES-BAR-COUNT, DEC-CANONICAL-SESSION-BAR-IDENTITY.
