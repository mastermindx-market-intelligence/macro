# FINDINGS — driver layer

Measured on the worker box `mini1` (macOS, Apple silicon), Python 3.14.7,
Playwright 1.64.1, bundled Chromium 156.0.8078.4, harness at
`/Users/mini1/macro/tools/xguerrilla`. The measurements in sections 1–5 came
from that box; none is an estimate. Date: 2026-11-07.
The subsequent pure-audit correction in section 6 is separately attributed to C3.

## 1. Typing lands, exactly, on a real page

`/tmp/xg_live_cdp.py` serves a real HTML page over loopback HTTP, launches real
Chromium, plans keystrokes with the shipped `typing.plan()`, dispatches them
through the shipped `CdpDriver`, and reads the field back with the page's own
`input_value()`. That read-back is the only evidence it accepts.

```
keys 70 (char 69, backspace 1)   type_wall_s 28.77   planned last offset 27960.6 ms
observed == text                  true   -> exact_match true
audit  ok true  n 69  median 248.7 ms  cv 1.17  skew 3.90  deletes_per_100 1.45
negative control (reload, type with nothing focused)
        raised: typed 70 keys but '#q' is still empty — nothing had focus
```

The negative control matters more than the positive one: it proves the driver
raises instead of reporting a successful keystroke run that landed nowhere.

Planner-level checks, no browser:

```
120 plans across 3 speed classes x 20 seeds x 2 lengths
        keys/deletes replay-equal to the source text: mismatch 0
        monotone median interval by speed class:    violations 0
```

## 2. Paste: the clipboard route does not work headless, and it fails silently

Three transports, each pasting `paste proof 4711` into its own `<textarea>` on
the same real page, each judged by reading the field back, with a JS listener
recording which native event the page observed.

| route | lands the text | event the page sees |
|---|---|---|
| A `pbcopy` + `Meta+V` (what the harness shipped) | **no** — field stays empty | `paste`, payload empty |
| B CDP `Input.insertText` into the focused element | **yes** | `input` |
| C `Meta+V` after granting `clipboard-read`/`clipboard-write` | **no** — field stays empty | `paste`, payload empty |

Confirmed again inside the end-to-end run on 2026-11-07:

```
paste_read_back "…first cold coffee"   paste_exact true      # insertText
clipboard_paste_read_back ""           clipboard_paste_lands false
```

A paste that fires the event but delivers no data is the worst failure shape
available: the page looks like it received a paste, the driver sees no exception,
and the pilot book would record a post that never existed. So:

- `CdpDriver.paste(text, target=None)` now uses `Input.insertText` and, when
  `target` is given, reads the field back and raises `DriverError` unless the
  observed value equals the payload exactly. Without `target` the old behaviour
  (dispatch, no verification) is kept for callers that do not need proof.
- `CdpDriver.clipboard_paste(text, target=None)` keeps the clipboard route for
  pages that only accept a genuine `paste` event, and returns what the field
  really holds instead of claiming success.
- `PeekabooDriver.paste(text, target=None)` raises when asked to verify: the
  accessibility CLI cannot read a field back, so it must not pretend.

Residual risk, stated plainly: `Input.insertText` is not a paste to a page that
inspects `event.type`. Where that matters, use `clipboard_paste` and check the
returned value; on this box it returns `""`.

## 3. Suite state

| box | tests | pass | fail | error | skip | wall |
|---|---|---|---|---|---|---|
| authoring laptop | 293 | 293 | 0 | 0 | 0 | 33.1 s |
| `mini1` | 293 | 293 | 0 | 0 | 0 | 16.4 s |

Both boxes now run the whole suite with nothing skipped. The former skip,
`test_live_pool_is_gitignored`, needed `/Users/mini1/macro` to be a repository;
it is now one (`git init` + one commit of the rsynced tree, no remote), so the
test asks its question and asserts. `mini1`'s live pool file is not present and
`git check-ignore -v tools/xguerrilla/proxies.yml` answers from the synced
`.gitignore` rule, so the policy is exercised without the credentials.
`test_drivers.py` alone is 30 tests,
including five that pin the paste contract above (insertText lands and reads
back; an empty field raises; no target means no read; the clipboard route
reports the empty field it really leaves; the GUI backend refuses to verify).
`test_ops.py` adds the three heartbeat cases described in section 5, and
`test_pilot_sim.py` adds the three keystroke cases described in section 8.

## 4. Changed in this pass

- `drivers/cdp.py` — `paste()` rewritten onto `Input.insertText` with exact
  read-back verification; `clipboard_paste()` added, returning the observed
  value; proxy credential parsing via `urlsplit`/`unquote`; `goto()` rejects
  non-2xx, error-page and blank responses; screenshot via raw
  `Page.captureScreenshot`; `type_plan(expect=)` verifies the field; `_locate`
  does a two-pass match.
- `drivers/base.py` — protocol for `paste` carries the optional `target` and the
  observed-value return.
- `drivers/peekaboo.py` — cached `--pid` target resolver; widened
  `DISPATCHED_UNVERIFIED`; `snapshot()` retries with `check=False` (the retries
  were dead code while `_run` raised on attempt 1), 4 attempts with backoff,
  focus only on odd attempts; `start()` pkills a stale tree still holding the
  profile, because a windowless leftover answers `app focus` with
  `target_unavailable` forever.
- `typing.py` — typo branch rewritten: `depth = rng.randint(1, 3)` wrong
  characters, each after its own lognormal interval, then exactly `depth`
  backspaces, each after its own interval, so typed and deleted counts always
  balance; trailing correction floor `while letters and deletes*100 < typed`
  keeps delete density above the naturalness floor without breaking replay
  equality.
- `tests/test_typing.py` — both xfail markers removed; strict monotonicity now
  asserted over every speed class x 20 seeds x two lengths instead of a single
  positivity check; `_fold()` replay-equality gate added.
- `conftest.py` — `FLOOR_MULT` flattened to 1.0 for every class: measured delete
  means are 9.1 / 5.6 / 3.8 per 235-character post, already ordered by class, and
  the old 2.0/3.0 boost inverted that ordering.
- `tests/test_drivers.py` — 25 tests before this pass, 30 after.

## 5. Still flaky or unproven

- **`peekaboo` against a live window** was not re-run in this pass. The driver
  path is unit-tested against a fake CLI and the stale-tree fix is reasoned from
  the `target_unavailable` behaviour, not observed here. Treat the first
  `peekaboo` run in the pilot as the test.
- **`snapshot()` retry timings** (4 attempts, backoff, focus on odd attempts)
  are unmeasured under real GUI contention; numbers were chosen, not fitted.
- **`textdrift.audit(window<3)` was corrected in the subsequent C3 source pass**
  described in section 6. Invalid windows now raise; insufficient comparison
  evidence cannot produce a clear audit. This does not qualify a live pilot.
- **~~`Supervisor` has no `heartbeat`~~ — closed.** `SimulationSupervisor`
  wrote the health row only from `degrade`/`recover`, and `pilot_sim` re-stamped
  the row by reaching into `sup.conn`, so a dry run could paper over a broken
  product-level writer. `SimulationSupervisor.heartbeat(now=None)` now owns the
  stamp: it moves `updated_at` and leaves `status`/`reason` untouched, so an
  injected outage survives the beat that proves liveness, and it raises
  `RuntimeError("simulation health row missing: a heartbeat is not a recovery")`
  instead of inserting a row, because an insert would manufacture health out of
  no evidence. `pilot_sim.heartbeat(sup, when)` delegates to it.
- **Clipboard route stays unusable headless.** If a real page must observe a
  `paste` event, the pilot has to run that step with the window shown, and
  verify by reading the value.

## 6. Subsequent C3 correction: unavailable audit evidence is not success

This source pass changes only `textdrift.py`, its focused tests and this record.
It preserves the similarity calculation, same-cell scope and MIN_POSTS=3.
The audit retains its existing result fields and adds `status`,
`compared_pairs` and per-child `excluded` reasons. Status is `clear`, `drift`
or `insufficient_data`; `ok` is true only when every supplied history is
covered by real same-cell comparisons and no pair reaches the threshold.
Observed drift remains reported when another history is unavailable.

Windows must be integers at least three; thresholds must be finite values in
[0, 1]. Malformed recent histories or cell assignments raise rather than being
coerced into evidence. Each child needs three informative text posts in the
actual window and an eligible sibling. Missing cells, short or uninformative
histories and isolated cells are explicitly excluded. Processing exceptions
propagate; they cannot manufacture a successful report.

On original C3, Python 3.12 with pytest 9.1.1, the same private synthetic cases
produced **17 passed / 48 failed** against original module blob
`7d3508ac6235126a1a1412098ec558bbe8b26d34`, then **65 passed / 0 failed / 0 skipped**
against candidate module blob `8c08d5387e0a1d5bc510c1c071473df36c5fc97f`.
Two existing real-persona fixture cases were deliberately deselected; global
runtime conftest was not loaded. Only the package initializer and text audit
module were imported. All three fixture files remained unchanged during both
runs, with zero network, subprocess, runtime-import or outside-write violations.
This is focused source proof, not a rerun of the full harness or the mini1
measurements above. See [the original-carrier source receipt](https://github.com/mastermindx-market-intelligence/Macro/pull/10837#issuecomment-6711766522).

No drivers, proxy configuration, account/profile state, typing, scheduling,
supervisor, simulation or external service ran or changed in this pass.
The real fourteen-day pilot, platform/identity permissions and production
acceptance remain open. Parent #10829 merged to `main` on 2026-11-07
(`f55fa485e`), so the retargeting blocker is gone; PR #10837 carries that
content itself and was merged forward onto current `main` (`005baca8b`), with
the single conflict — `tests/test_ci_pack.py` — resolved by composing this
lane's measured +20 planner-weight enrollment onto the ceilings `main` already
carries: 5920/5939/5678 -> **5940/5959/5698**.

## 7. Where the suite runs, and what must never be synced there

`test_live_pool_is_gitignored` asserts on repository state: the live pool file
`tools/xguerrilla/proxies.yml` must be ignored and untracked. On a machine that
is not a repository the test cannot ask its question, so a plain `rsync` of
`tools/` produces a skip that hides the policy it exists to check. The worker
box therefore holds a real repository: `git init` over the synced tree plus one
commit, with no remote configured (it has no GitHub credentials and does not
need any — code arrives by `rsync`, which stays the only transport).

The pool file itself never belongs on the worker box. Sync with
`--exclude 'proxies.yml'` and keep the root `.gitignore`: an rsync of `tools/`
alone drops the root ignore file, and a `git add -A` in that state commits the
live credential pool into the worker's local history. The pool is read where the
harvest runs, from the environment, not copied to a second host.

The committed `proxies.example.yml` is a template in the strict sense: sixteen
inventory lines, `${BART_USER}`/`${BART_PASS}` placeholders, and RFC 5737
documentation addresses. Earlier it carried the purchased host:port list with the
credentials templated out, which is still inventory — the address block
identifies the pool, and nothing an operator needs lives in it.
`test_template_exists_and_is_not_the_live_pool` now refuses any line whose host is
outside the documentation ranges, and refuses the vendor name, so the next person
who pastes a real response body into the template fails a test instead of
shipping the pool. Ports and addresses in the template therefore say nothing
about the live allocation; read `proxies.yml` for the real order.

## 8. Keystroke evidence: a post count is not proof that anything was typed

Until this pass the pilot reported `typed_posts` / `pasted_posts` but nothing
counted the keys. A driver whose paste silently became an insert, or whose
"typing" was one programmatic write, produced the same report as a driver that
typed every character: the composer text matched either way. That is the same
class of defect as the empty-payload paste in section 2 — a successful post
hiding an interaction that never happened.

Three changes close it:

- `pilot_sim` snapshots `drv.keystrokes` before and after the composer write and
  compares the delta to what it asked for. The paste route must report exactly
  zero keystrokes; any non-zero count raises
  `DriverError("pasted post recorded N keystroke(s): the paste route and the
  typing route are not interchangeable")`. The typing route must report exactly
  `len(keys)`, and any other number raises.
- The report now carries `keystrokes`, `typed_chars` and `paste_chars` next to
  the post counts, so an operator can read the evidence rather than infer it.
- `keystroke_counts` is a verdict criterion, not a log field: a run with no
  typed posts, or with fewer keystrokes than typed characters, fails the pilot
  gate with the numbers in the reason.

The three cases in `test_pilot_sim.py` pin all three: the clean run carries the
counts it claims, a driver that lands the exact text while reporting one
keystroke per post fails with `planned keystrokes`, and a paste that reports
keystrokes fails with `pasted post recorded`. The middle case is the reason the
criterion exists — the buffer check passes it, only the count does not.

What this still does not prove: that a keystroke reached the operating system.
`FakeDriver` counts what the plan asked for. The real evidence for the CDP path
is section 1's live run (70 planned keystrokes, the page's own `input_value()`
matching exactly, 28.77 s wall against a planned last offset of 27.96 s); the
counter here makes the pilot refuse to claim typed work it cannot show, it does
not make the simulation a live measurement.
