---
key: A-PROTECTIVE-CONFIG-KEY-DEFAULTS-TO-UNPROTECTED-FOR-EVERY-CONFIG-THAT-PREDATES-IT
claim: >
  A config loader shaped `dict(DEFAULTS).update(<file>)` resolves a NEWLY ADDED protective key
  from the defaults while every key the file already carried — including `armed` — comes from the
  file. So a config written before the protective key existed yields arming from one era of the
  schema and protection from another, and the natural default for a new deny-list (empty) is
  exactly the unprotected value. Measured in `scripts/worktree_gc.py`: invoked DIRECTLY it
  resolves its config from the PRIMARY checkout, which the workspace law keeps every session out
  of and which therefore nobody fast-forwards — found on branch `feature` at a 2026-09-04 commit,
  7,450 behind `origin/main`, loading `armed: true` with `human_driven_roots: []`, while
  `origin/main` and every worktree carried all three entries.
falsifier: >
  Run `python3 -c "import sys; sys.path.insert(0,'scripts'); import worktree_gc as g;
  p=g.resolve_primary_root(); c=g.load_config(p,None); print(c['armed'], c['human_driven_roots'])"`.
  If the deny-list is non-empty for a config file that does not contain the key, the default is
  not the unprotected value and this is false. Measured 2026-09-29: it printed `True []` before
  the fix and the three roots after. The mutation control is the proof the test is real — restore
  `DEFAULT_CONFIG["human_driven_roots"] = []` and the identical config loads `armed=True deny=[]`.
so_what: >
  Make a protective default a FLOOR, not an empty placeholder: put the real entries in the
  built-in defaults so an ABSENT key inherits protection, and let an EXPLICIT `[]` still override
  so the config keeps policy authority. And distrust the reasoning "the built-in defaults are the
  disarmed fallback" wherever a loader merges a file over defaults — it holds only when NO file
  exists; it is false for every file written before the key existed, which is every file on a
  checkout that has not fast-forwarded. Separately: an instrument that reports a policy verdict
  must NAME the file the policy came from. `human-driven protection: NONE configured` was
  perfectly honest about what it had loaded and still misled, because the reader cannot tell a
  fact about the fleet from a fact about which checkout supplied the config.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  `scripts/worktree_gc.py` `load_config` (`cfg = dict(DEFAULT_CONFIG)` then `cfg.update(...)`) and
  `config_path_for`; the primary checkout at `/Users/chriswong/Documents/Cluade/Macro Dashboard`
  on `refs/heads/feature` = `0f62daf545719e641036be9e5b88101c3af7ab5f` (2026-09-04), `git
  rev-list --count 0f62daf54571..origin/main` = 7450; `config/worktree_gc.json` on `origin/main`
  carrying all three `human_driven_roots` entries; `tests/test_worktree_gc.py` items 22-24,
  36 passed.
scope:
  - macro
  - scripts/worktree_gc.py
  - config/worktree_gc.json
confidence: verified
---

## The part that makes this expensive rather than merely wrong

Every surface an operator or a session would check said the protection was live. `origin/main`
carried the three entries. Every worktree carried them. The PR that added them was merged and
byte-verified in main. The launchd wrapper — production — genuinely does honour them, because it
re-extracts both the tool and the config from `origin/main` and passes `--config`.

The one path that did not was the one a human or a session actually types:
`python3 scripts/worktree_gc.py`. That resolves `primary / config/worktree_gc.json`, and `primary`
is the main working tree — the folder `CLAUDE.md` forbids opening as a workspace. The prohibition
is what guarantees it is never fast-forwarded: nobody works there, so nobody pulls there.

So the safeguard's own coverage had a hole shaped exactly like the rule that protects the repo.

## Why the empty default looked correct when it was written

The comment said: *"Empty here on purpose: the built-in defaults are the disarmed fallback, and
the real list lives in config/worktree_gc.json."* That reasoning pairs the empty deny-list with
`"armed": False` in the same dict and concludes the pair is harmless — nothing can be deleted, so
nothing needs protecting.

`dict.update()` breaks the pairing. The two keys stop travelling together the moment a real file
supplies one and not the other, and a file that predates the protective key supplies `armed` and
not the deny-list *by construction*. The defence was never reachable in the case that mattered.

This generalizes past this repo: **any protective key added to an existing config schema starts
life absent from every deployed config**, so its default is not a fallback for the empty case —
it is the live value for the entire installed base until each config is rewritten.

## The reporting half

`protection_line` printed `human-driven protection: NONE configured`. That was TRUE of the config
it had loaded, and it is the line a previous wave added precisely so that absence would not read
as presence. It still misled, because the report named no config file: a reader cannot separate
"the fleet has no deny-list" from "this invocation read a different checkout's config."

An instrument that states its reach over *worktrees* and not over its own *inputs* is only half
instrumented. `policy_source_line` now names the file and flags the implicit primary path.

Related: `DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT` (the other place where a
protection and the thing it protects are wired through different code paths).
