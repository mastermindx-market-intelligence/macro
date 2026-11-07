# xguerrilla operator runbook

This is the page you read at 7am, or at the moment something looks wrong. It
covers the harness in `tools/xguerrilla/`: the typing model, the persona rows,
the proxy slots, the profile store, and the supervisor that decides whether a
child may run. Everything here is a procedure you can do with the CLI and a
terminal; nothing requires the web UI.

Two rules sit above every procedure below, so they are first:

1. **A quarantined step quarantines the step, not the child.** When a shadow run
   cannot resolve a selector, the step is written to the profile store's
   quarantine log and the child keeps running every other step. Do not cool,
   quarantine or retire a child because one selector drifted. Fix or drop the
   step, then clear it. Retiring a child over a moved button throws away the
   only thing in this system that cannot be regenerated.

2. **The typing model is a statistical claim, not a delay setting.** If you are
   tempted to "just slow it down" by adding a fixed pause, stop: a fixed delay
   with jitter has near-zero skew and is exactly the shape the naturalness audit
   rejects. Change `speed_class`, `pause_mult` or `typo_rate_mult` and let the
   generator produce the shape. The regression suite in `tests/test_typing.py`
   pins this: the broken generator written into that file fails `assert_natural`
   on skew and cv, and it must keep failing.

All commands run from the repo root (`/Users/chriswong/Mastermind/macro`).
The subcommands are `status`, `personas`, `net-check`, `shadow`, `snapshot`,
`restore`, `verify`, `degrade` and `recover`. Their options belong to the
subcommand, not to the program: `--store` and `--db` wherever state or profiles
are touched, `--personas` on `degrade`, `--proxies` on `net-check`, `--driver`
on `shadow`. Handles and archives are positional — `verify kid.audit`, `restore
kid.audit <archive>.tar.gz` — and `--handle` is only a `shadow` flag. Defaults
are `$XG_PROFILE_STORE` (`~/.xguerrilla/profiles`), `$XG_STATE_DB`
(`~/.xguerrilla/state.db`), the packaged `personas/` dir and `proxies.yml`.

**The proxy file is not in Git.** `proxies.yml` holds the BartProxies user and
password on every slot line, so it is gitignored; what is committed is
`proxies.example.yml`, which is the same sixteen slots with `${BART_USER}` and
`${BART_PASS}` in place of the credentials. On a new box: `cp
tools/xguerrilla/proxies.example.yml tools/xguerrilla/proxies.yml`, then either
export both variables or write them into that file. `net.load()` expands
`${VAR}` from the environment, `Slot.public()` and `Slot.__repr__` both withhold
the password, and `tests/test_proxies_template.py` fails if a literal credential
ever reaches the template or if the live file becomes tracked.

Every subcommand prints exactly one JSON document on stdout. Exit codes: `0` ran
and clean, `1` ran and found a problem, `2` usage error, `3` the requested
driver is unavailable.

---

## 1. Daily checks

Three commands, in this order, before you touch anything.

### Status

    python3 -m tools.xguerrilla.cli status --db ~/.xguerrilla/state.db

Read `health.status` and `health.effective` first. `healthy` means children may
run; `degraded` means lead and conversation children still run but broadcast
children are paused; `stale` means the health row has not been written in
`STALE_HEALTH_S` (900s) and you should not trust the rest of the document until
you know why nothing has updated it.

Then read `counts.runnable` against `counts.children`. A child that is ACTIVE
but not runnable is not a bug — `why` on each child row says so in plain words:
`cooling until 2026-11-07T12:36:42Z`, `degraded: broadcast child paused (drill)`,
`quarantined`, `retired`. If a child is ACTIVE, not cooling, and still not
runnable, that is the one thing in `status` worth investigating immediately.

### Telemetry summary

    python3 -c "from tools.xguerrilla import telemetry; \
      import json; print(json.dumps(telemetry.summarise('$HOME/.xguerrilla/telemetry.jsonl'), indent=2))"

`summarise` returns per-kind counts (`kinds`), the inter-keystroke interval shape
(`iki_median`, `iki_cv`, `iki_skew`, and `iki.n` as the sample count), the label
histogram (`labels`), `challenges`, `sessions` and `relogin_fraction`.

What to look at:

- `relogin_fraction` — the share of sessions that needed a re-login or came back
  `ok: false`. This is the earliest signal that a profile is being challenged.
  A handful of sessions gives a noisy number; treat it as a trend, not a verdict.
- `iki_median`, `iki_cv`, `iki_skew` — these should look like the class the child
  is placed in. `cv` near zero is the tell that something upstream is emitting a
  fixed delay (a test hook left on, a replay path, a stub driver). Skew should be
  positive: real typing has a long right tail of slow keystrokes and a hard floor
  on fast ones. Symmetric jitter around a constant has skew ≈ 0 and will fail the
  audit even though the median looks right.
- `challenges` — count of challenge rows. One is normal life. A step change is a
  persona or a slot problem, not bad luck.

### Label histogram

The histogram is the `labels` object from the same `summarise` call, not a
separate command. Read it as an engagement shape: a healthy week has the
follow/reply bands moving and the like band saturating. If the histogram
collapses onto a single label, the selector for the others drifted — go to the
shadow run (§4) before you change any persona. If it goes flat across all
children at once, check `status` for a degraded state before you touch a persona
row.

---

## 2. A challenge

A challenge is a wall the child hit: an interstitial, a verification prompt, a
session that came back logged out. It is not an emergency, and the wrong reflex —
retrying immediately in the same profile — is what turns one challenge into a
dead account.

**Cool the child.** Stop it from running before you investigate:

    python3 -c "from tools.xguerrilla.supervisor import Supervisor; s = Supervisor('$HOME/.xguerrilla/state.db'); s.cool('kid.audit', 180); s.close()"

`can_run` will then report `(False, 'cooling until ...')`, `pick()` will skip it,
and nothing else has to know. 180 minutes is the default response for a single
challenge; the point is that the child is quiet while a human looks. `cool` takes
a handle and a duration only — it stores no reason, so the reason belongs in the
challenge telemetry row below. That row is the record.

**Verify by hand.** Three checks, all cheap:

    python3 -m tools.xguerrilla.cli verify kid.audit
    python3 -m tools.xguerrilla.cli snapshot kid.audit

`verify` compares the profile tree against its manifest and returns `ok`,
`expected`/`actual` tree hashes, plus `changed`, `missing` and `extra` file
lists. A challenge that only wrote cookies will show `changed` entries and still
be recoverable. `missing` is the serious one: a profile that lost files is a
profile you restore rather than repair. Then open the profile once by hand — a
real browser, the real proxy slot — and look at what the child sees. If you can
log in by hand, the child can too, and the challenge was transient. If you
cannot, the slot or the account is the problem, not the harness.

Take the snapshot *before* any manual login. Manual use is the thing you will
want to roll back.

**Log it.** Write a row so the challenge is in the record and not just in your
head:

    python3 -c "from tools.xguerrilla import telemetry; \
      telemetry.record('$HOME/.xguerrilla/telemetry.jsonl', 'challenge', handle='kid.audit', note='interstitial on login; cooled 180m; verified by hand')"

Then, and only then, `activate` the child again and watch `relogin_fraction` for
the next day. If the same child challenges twice inside a week, do not cool it a
second time and hope: treat it as a persona problem (hours, action rate, beat) or
a slot problem, and change one of them.

---

## 3. Degraded mode

`degrade` is a global switch on the supervisor, not a per-child state. It exists
so that a partial outage — a proxy region down, a selector broken for one flow,
an upstream API wobbling — does not force you to stop every child.

    python3 -m tools.xguerrilla.cli degrade --reason "proxy region us-16 flapping"
    python3 -m tools.xguerrilla.cli status          # health.effective == "degraded"
    python3 -m tools.xguerrilla.cli recover

What degraded does: children whose role is in `DEGRADED_ROLES` (`lead`,
`conversation`) keep running; every other child — `broadcast` and anything
unroled — is reported `runnable: false` with `why: "degraded: broadcast child
paused (<reason>)"`. So the posting cadence drops but the accounts stay warm and
the conversations stay answered.

Drill it quarterly, and drill it at a bad time on purpose:

1. `degrade --reason "drill"` and confirm `status` shows every broadcast child
   `runnable: false` with the reason string carried through to `why`.
2. Confirm at least one `lead` and one `conversation` child is still
   `runnable: true`. If none is, degraded mode has silently become a full stop
   and you have found the failure worth fixing.
3. `recover`, then confirm `health.effective` is `healthy` and `counts.runnable`
   is back to what it was before the drill. A recover that leaves children
   non-runnable means someone cooled them during the drill; the reason will be
   in each child's `why`.

Degraded mode never changes a child's state — it only masks `can_run`. Cooling,
quarantining and retiring are separate operations and they survive `recover`.

---

## 4. The weekly shadow run

A shadow run resolves every step's selector against a live driver, read-only:
only `locate` and `screenshot` are called, so no cookies, session or composer
state can be mutated. It is how a moved button is discovered before it costs a
post.

    python3 -m tools.xguerrilla.cli shadow \
      --handle kid.audit \
      --steps steps.json \
      --screenshots /tmp/shadow-kid.audit \
      --dry-run

`--dry-run` validates the step file and lists the step names it would check. Run
it once after any edit to `steps.json`; it needs no driver and cannot fail for
operational reasons.

For the real run, pass a driver:

    python3 -m tools.xguerrilla.cli shadow \
      --handle kid.audit --steps steps.json \
      --screenshots /tmp/shadow-kid.audit \
      --driver tools.xguerrilla.drivers.peekaboo:driver

Exit `0` means every selector resolved; `1` means drift was found; `3` means the
driver was unavailable — which is not a drift result and must not be logged as
one.

On drift, the CLI writes one quarantine record per drifted step, naming the step
and the reason `shadow: selector did not resolve (<handle>)`, and leaves a
screenshot per drift in the screenshots dir. Then:

- Read `quarantined_steps(store, handle)` to see what the child is currently
  missing.
- Fix the selector, then re-run shadow for that one handle. Clear the step only
  when it resolves again.
- Do **not** cool, quarantine or retire the child. The child is fine; one step is
  broken. This is the rule stated at the top of this page, and the shadow path is
  where it gets violated in practice.

Monthly, run shadow across every handle in one pass and diff the drift sets week
over week. A selector that drifts repeatedly is a sign the upstream UI changed
shape, not that the child is unlucky.

---

## 5. Profile snapshot and restore

The profile store keeps a manifest per handle (tree hash plus per-file hashes)
and tarballs under `<store>/snapshots/`.

    python3 -m tools.xguerrilla.cli verify   kid.audit
    python3 -m tools.xguerrilla.cli snapshot kid.audit
    # -> {"ok": true, "handle": "kid.audit", "archive": ".../snapshots/kid.audit-20261107T120656636187Z.tar.gz"}

    python3 -m tools.xguerrilla.cli restore kid.audit \
      ~/.xguerrilla/profiles/snapshots/kid.audit-20261107T120656636187Z.tar.gz

`restore` prints the archive it used and the `verify` result immediately after
unpacking, so a restore that did not land is visible in the same document. Never
report a restore as done from the exit code alone — read the `verify` block.

Take a snapshot before: any manual login, any `Store.init` re-run, any change to
a persona row that alters action rate, and before a challenge response. Snapshots
are cheap; a lost profile is a lost account.

Restore is for missing or corrupt files. If `verify` shows `changed` only, the
profile is intact and the change is just cookies — restore is the wrong tool and
will cost you a valid session.

---

## 6. Adding a child

Four steps, in order. Do not skip the login-by-hand step; automation that walks
into a fresh profile and immediately acts is the single most common way a new
account dies.

**Slot.** A child's address is its reputation, so slots are allocated, not
generated. Load the inventory and take one that no other handle is using:

    python3 -m tools.xguerrilla.cli net-check
    python3 -c "from tools.xguerrilla import net; \
      slots = net.load(); print(net.assign(slots, 'kid.new').name)"

`net-check` prints the 16 slots with their public fields — `slot`, `host`,
`port`, `user`, and never the password; `assign` is stable for a
handle across calls, so re-running it is safe and always returns the same slot.
Assign 16 distinct handles to the pool exactly once — the 17th must raise, and
the regression suite asserts that it does. Never hand-edit `proxies.yml` to add a
slot.

**Persona row.** Add a YAML file under `personas/`, one row per child, shaped
like the existing ones:

    handle: kid.new
    cell: ATX-04
    role: conversation        # lead | conversation | broadcast
    beat: <what this account actually talks about>
    city: Austin
    tz: America/Chicago
    speed_class: slow         # slow | average | fluent
    typo_rate_mult: 1.0
    revision_prob: 0.3
    pause_mult: 1.0
    hours: [9, 23]
    idle_day_p: 0.1
    casing: lower_sometimes   # lower | sentence | mixed | lower_sometimes
    max_chars: 130
    links_per_week: 0
    hashtags_max: 0
    pet_phrases: [...]
    opinions: [...]
    doesnt_care_about: [...]
    actions_per_day: 14
    seed: 4106

`seed` is what makes the child's timing reproducible — keep it unique and never
change it once the child has history, or every statistical property you measured
becomes a measurement of a different child.

`typo_rate_mult` is not decoration. The audit requires at least one correction
per 100 characters typed, and `fluent` at 1.0 does not clear that on clean prose:
measured over the same 235-character paragraph, `slow` corrected itself on every
one of 20 seeds at 1.0, `average` on 19 of 20, and `fluent` on only 13 of 20 —
seven posts went out perfectly clean, which is itself a rhythm tell. So give a
`fluent` row `typo_rate_mult: 2.0` (or higher) and check the class with

    python3 -c "from tools.xguerrilla import typing as T, persona as P; \
      p = P.load_dir('tools/xguerrilla/personas')['kid.new']; \
      print(T.assert_natural(T.plan(open('/dev/stdin').read(), p), p))"

pasting a paragraph of that child's own prose on stdin. `ok` must be `true` and
`problems` empty before the child posts anything. If it is not, the row is
miscalibrated — fix the row, not the test. Validate the file by loading the
directory:

    python3 -m tools.xguerrilla.cli personas

**Login by hand.** Create the profile, then log in yourself:

    python3 -c "from tools.xguerrilla import profiles; \
      print(profiles.Store('$HOME/.xguerrilla/profiles').init('kid.new', \
        slot='bartproxies-us-16-07', chrome_version='131.0', notes='onboard 2026-11-07'))"
    python3 -m tools.xguerrilla.cli verify kid.new
    python3 -m tools.xguerrilla.cli snapshot kid.new

Then run one browser by hand through the assigned slot, log in, and leave the
session in the state the child will inherit. Take a second snapshot after that
login: the first is the empty-profile baseline, the second is the one you restore
to if onboarding goes wrong.

**Warm-up.** The child becomes runnable the moment the supervisor sees it, but
"runnable" is not "ready". For the first week, keep `actions_per_day` well under
the row's steady-state value (start near a third), keep `role: conversation`
until the account has answered a few threads, and watch `relogin_fraction` and
`challenges` in the daily summary. Move to the full action budget and to `lead`
only after a clean week — no challenge, no re-login, and the label histogram
showing the persona's own beat rather than one saturating like band.

---

## 7. When the suite runs

    python3 -m pytest tools/xguerrilla/tests -q

The suite encodes the laws, not snapshots. `tests/test_typing.py` checks that a
200+ character post passes `typing.assert_natural` with `ok: true` and an empty
`problems` list for every speed class across ten seeds; that the distributions
are right-skewed with positive intervals and no keystroke before t=0; that a plan
longer than 100 characters contains a deletion; that `to_cdp` emits one entry per
key with Backspace at `vk 8`; that `with_revision` fires near
`persona.revision_prob` and never touches the last 40 characters; and — as a
negative control — that a hand-built generator emitting a fixed 120 ms delay plus
uniform jitter *fails* `assert_natural` on skew and cv. If that negative control
ever starts passing, the audit has been defanged and the whole suite is worthless.

A law marked `xfail` is a real defect in shipped code, with the failure message
saying what will break in production. See them with `-rxX` rather than `-q`:

    python3 -m pytest tools/xguerrilla/tests -q -rxX

Run that from the repository root, never from inside `tools/xguerrilla`. The
package contains a file named `typing.py`, so a pytest started in that directory
imports the harness's module where the standard library's belongs and dies with
`partially initialized module 'typing' has no attribute 'ClassVar'`. From the
root the tests import `tools.xguerrilla.typing`, which is the module you meant.

Four are open today: `plan()` never emits the spaces between words, so the CDP
log replays to one unbroken string; the typo branch corrects at the same
timestamp it errs, so some intervals are exactly zero; `fluent` at the default
`typo_rate_mult` of 1.0 types long posts with no corrections at all; and a
proxy slot prints its password in its repr, so any traceback that mentions a
slot drags the secret into logs. None of them are the audit's fault, and none
should be silenced by loosening a test. When one flips to `XPASS`, fix the code
and delete the marker.
