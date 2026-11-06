---
key: GMI-THEME-GRAPH-STORE-NON-STRICT-READ-MASKS-CORRUPTION
claim: >
  engine/theme_graph/store.py `_read(path, columns, strict=False)` returns an empty frame
  with the expected columns both when the parquet is MISSING and when it is CORRUPT (it logs
  a warning and swallows the exception). Only `strict=True` distinguishes them: it re-raises
  FileNotFoundError, raises ValueError("unreadable graph input: …") for a corrupt file and
  ValueError for missing columns.
falsifier: >
  Point a non-strict store reader at a truncated nodes.parquet. If it raises instead of
  returning an empty frame, the claim is false.
so_what: >
  A consumer on the default non-strict path cannot tell "no graph yet" from "graph
  destroyed", and will report a corrupt store as valid emptiness. Readers whose output can
  be mistaken for truth must call the store with strict=True, as the lifecycle and
  value_chain axis readers do (read_nodes(current=False, strict=True),
  read_node_lifecycle(latest=False, strict=True)), and map the error to
  unavailable/owner_degraded.
kind: landmine
verified_at: 2026-10-12
verified_by: >
  GMI Meta-CEO seat 6f14c2da: read of store.py `_read` (line 211) and of the strict calls in
  engine/classification_axes/lifecycle.py and value_chain.py on origin/main d89fdf72f85d.
scope:
  - macro
  - engine/theme_graph/store.py
  - engine/classification_axes/
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
---

The non-strict default is deliberate for the nightly producer, where an unreadable store
must not crash the bake. The landmine is for new consumers that copy the default.
