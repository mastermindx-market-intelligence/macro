---
key: A-DRAINED-STORE-PASSES-A-SHAPE-CHECK-AND-PUBLISHES-A-BLANK-BOARD
claim: >
  An existence check that tests a store's CONTAINER cannot tell a healthy store from a drained
  one, and the failure is a false GREEN rather than a missing one. `_has_store_content()` in the
  canonical ThetaData resolver returned True as soon as one of `eod/` `oi/` `greeks/` existed as a
  DIRECTORY, never asking whether a tier held a root — so a store whose tiers are intact and whose
  roots are all gone resolved exactly like a full one. The consumer then runs to completion on
  nothing: measured 2026-09-29 against `scripts/build_options_intel_brief.py --require-store`, the
  drained store resolves, the producer exits rc=0, and it OVERWRITES the last-good
  `site/options_intel_brief.json` with an empty `board_state: DEGRADED` / `board_reason:
  MIXED_VINTAGE` payload (`as_of_session` empty, `eligibility.present=0`). The mode built
  specifically to refuse a missing store could not see a drained one, because emptiness was never
  what it measured. This is the `options_witness 0/18 empty-store` shape that
  `scripts/build_options_hub_nightly.py:1092` already refuses by hand; the canonical resolver was
  the one place that did not.
falsifier: >
  Revert `_has_store_content()` in `engine/thetadata_store.py` to `p.is_dir() and any((p / t).is_dir()
  for t in _STORE_TIERS)` and run `python3 -m pytest tests/test_thetadata_resolver.py::TestDrainedStoreIsNotAStore -q`.
  Measured on base 942956ea69f6: 4 failed, 1 passed with the revert; 25 passed with the fix (incl.
  `tests/test_index_gex_history.py::TestStorePathRoutesThroughTheResolver`). The single test that
  passes BOTH ways is the positive control — `test_one_real_root_is_thinness_and_still_resolves` —
  and it is what proves the predicate refuses emptiness rather than thinness. If a future change
  makes a one-root store fail to resolve, this claim's fix has overshot and is refuted.
so_what: >
  Two things a future session must not redo. First, when an options/ThetaData product goes stale,
  do NOT diagnose it as placement ("the job is on the wrong host") from a `resolved store=NONE`
  line alone — that message was identical for a missing store and a drained one, which need
  opposite remedies: re-placing the job fixes the first and cannot touch the second, whose owner is
  the store's own writer. `_drained_store()` now separates them in the log; read which one fired.
  Second, when adding any new "does this data source exist" gate anywhere in this repo, assert on
  CONTENT, not on the presence of a container — and pin it with a test that also proves a
  minimally-populated source still passes, or the tightening will refuse thin-but-valid data.
  A root is required to be a directory because the real enumerators do the same — `universe()`
  and `iv_coverage()` in `engine/thetadata_store.py` count `is_dir()` children, and
  `_load_parquets()` then globs inside a root. (An earlier draft of this record cited a `roots()`
  function; no such function exists — the claim held, the citation did not.) THIRD, and the part
  an adversarial review caught before merge: a content check is a `readdir`, whereas the shape
  check it replaces was a `stat`. On the ops host the three tier dirs are SYMLINKS onto an
  external volume, and listing them is exactly the operation that hangs or is denied under
  launchd — `scripts/build_options_hub_nightly.py::preflight_store` exists solely to bound it,
  and it runs AFTER resolution. So any emptiness check inside the resolver must be BOUNDED and
  must FAIL OPEN: only a provably drained store may be refused, while denied/blocked/errored
  resolves exactly as it did before the check existed. Fail-closed here would report an intact
  store as missing across every nightly lane — a far worse failure than the one being fixed.
kind: landmine
verified_at: 2026-09-29
verified_by: "PR #8203; RED/GREEN on base 942956ea69f6 — python3 -m pytest tests/test_thetadata_resolver.py tests/test_index_gex_history.py::TestStorePathRoutesThroughTheResolver -q (25 passed; 4 failed + 1 control passed with engine/thetadata_store.py reverted)"
scope:
  - macro
  - engine/thetadata_store.py
  - scripts/build_options_intel_brief.py
  - WS:ADVANCED-DATA-OPTIONS
confidence: verified
---

## How it was found

Reproducing MACRO-04 ("options brief runs on the wrong host"). The brief was 38 days stale
(`built_at_utc=2026-08-22T19:10:32Z`, `as_of_session=2026-08-19`) and the accepted story was
placement: the producer's only scheduled invocation is a step in `daily.yml`'s `engine` job, which
runs on store-less M2 runners, so the resolver returns `None`, the producer takes its documented
off-host self-skip, and the step records `success`.

That story is true and incomplete. Checking the store on the store-bearing host before proposing
to move the job there found it **drained**, which inverts the fix: moving the job would have
activated a producer that publishes a blank board instead of one that skips.

## The state that produced it

| observation | value |
|---|---|
| `eod` / `oi` / `greeks` root counts | 0 / 0 / 0 |
| `_manifest.json` `status` | `healthy` |
| `_manifest.json` `complete_t1_roots` | 372 |
| `_manifest.json` `finished_at` | 2026-09-25 |
| same-host control (`data/yahoo` entries) | 728 |

The control is load-bearing: it rules out a glob, permissions, or sparse-checkout artifact at the
point of measurement. The null is real. See
[[A-STORE-MANIFEST-IS-A-WRITERS-INTENT-NOT-AN-OBSERVATION-OF-THE-STORE]] for why the manifest
disagreed.

## Corroboration in a second product

`site/options_skew/latest.json` on `main` carries a fresh `generated_utc` (2026-09-29T05:03Z)
against `ledger_asof: 2026-09-23`, `accrual_state: ledger_only`, `n=372` — the same 372 roots the
manifest claims. A second options product publishing fresh timestamps off the ledger because the
store returns nothing. Neither product was red anywhere.
