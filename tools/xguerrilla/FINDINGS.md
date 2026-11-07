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
| authoring laptop | 205 | 205 | 0 | 0 | 0 | 68.3 s |
| `mini1` | 205 | 204 | 0 | 0 | 1 | 29.9 s |

The one skip is `test_live_pool_is_gitignored`: `/Users/mini1/macro` is an rsync
copy with no `.git`, so it has nothing to ask. `test_drivers.py` alone is 30
tests, including five that pin the paste contract above (insertText lands and
reads back; an empty field raises; no target means no read; the clipboard route
reports the empty field it really leaves; the GUI backend refuses to verify).

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
- **`Supervisor` has no `heartbeat`**, so `pilot_sim` re-stamps child health
  itself. The dry run therefore cannot catch a health-stamp bug.
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
The absent heartbeat, real fourteen-day pilot, platform/identity permissions
and production acceptance remain open. PR #10837 remains Draft on its existing
parent stack; parent #10829 must actually merge before retargeting/admission.
