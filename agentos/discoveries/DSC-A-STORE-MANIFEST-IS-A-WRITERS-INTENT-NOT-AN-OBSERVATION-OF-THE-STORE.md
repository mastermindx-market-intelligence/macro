---
key: A-STORE-MANIFEST-IS-A-WRITERS-INTENT-NOT-AN-OBSERVATION-OF-THE-STORE
claim: >
  The ThetaData T1 store's `_manifest.json` records what its writer BELIEVED it had written, and
  nothing re-reads the store to confirm it. Measured 2026-09-29 on the store-bearing M1: the
  manifest advertised `status: healthy`, `complete_t1_roots: 372`, `finished_at: 2026-09-25` while
  every tier (`eod`, `oi`, `greeks`) held ZERO roots. A manifest therefore survives the
  disappearance of the very bytes it describes — whether they were reclaimed, were never flushed,
  or the volume they lived on went away — and it will keep advertising health indefinitely,
  because nothing in the write path invalidates it.
falsifier: >
  Find any code path that re-reads the store and rewrites or invalidates `_manifest.json` when the
  observed roots disagree with `complete_t1_roots`. `git grep -n '_manifest' -- engine scripts app admin`
  over the macro repo at 942956ea69f6 finds writers and readers of the field but no reconciler; if
  one is added, or if a manifest is observed self-correcting after a drain, this is refuted.
so_what: >
  Never use `_manifest.json` as a liveness, freshness, or coverage signal, and never add a health
  gate that reads it — such a gate passes on a completely empty store, which is the exact case a
  health gate exists to catch. A future session tempted to "just check the manifest says healthy"
  before building would ship the same false green that
  [[A-DRAINED-STORE-PASSES-A-SHAPE-CHECK-AND-PUBLISHES-A-BLANK-BOARD]] describes, one layer up.
  Coverage questions must be answered by enumerating the store (`roots()`), and any disagreement
  between the manifest and the enumeration should be reported as a DATA fault owned by the store's
  writer, never repaired by a reader.
kind: landmine
verified_at: 2026-09-29
verified_by: "#8203; ssh m1 'for t in eod oi greeks; do print $t $#{$P/$t/*(N/)}; done' -> 0/0/0 against _manifest.json complete_t1_roots=372 status=healthy finished_at=2026-09-25, same-host control data/yahoo=728; no reconciler found by git grep -n '_manifest' -- engine scripts app admin; enumeration site engine/thetadata_store.py:roots()"
scope:
  - macro
  - engine/thetadata_store.py
  - WS:ADVANCED-DATA-OPTIONS
confidence: verified
---

## Why the control matters

A null result from a remote host is worth nothing without a positive control taken at the same
moment through the same access path (engineering doctrine §3.4). Here the control was a sibling
directory on the same host, `data/yahoo`, which returned 728 entries in the same session that
returned 0/0/0 for the store tiers. Without it, "the store looks empty" is indistinguishable from
a glob that did not expand, a permissions denial, or a sparse checkout.

## What this does not claim

It does not claim the data is lost — only that the manifest is not evidence either way. Recovering
or refilling the store is owned by its writer and is outside the reader's remit.
