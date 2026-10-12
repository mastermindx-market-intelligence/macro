---
key: A-VENUE-MOVING-RENAME-MISSES-THE-COMMITTED-LISTING-KEY
claim: >
  In scripts/build_security_master.py a corporate rename that also moves the listing venue
  (PSKY on Nasdaq -> SKYD on NYSE, 2026-10-06) re-derives the listing key from TODAY's MIC
  plus the inception code (US-XNYS-PSKY). That key misses the committed row (US-XNAS-PSKY),
  so the pending-transition mint fence refuses the new id and
  scripts/build_qbus_news_universe.py fails closed with membership_alias_unresolved: the
  ticker-news writer goes dark for the WHOLE universe, not just one name. A same-venue
  rename (EQR->VMRK) re-derives the identical key and joins for free, which is why the class
  never surfaced before. The merged fix (#8828, squash c50af4eb0421) dates the rename,
  bridges the two keys with a curated SecuritySupersession US-XNYS-PSKY -> SEC:US-XNAS-PSKY,
  and gates suppression (variant N: `is_root or (prior is None and not
  unratified_rename_member)`) on DATED-RenameEvent membership only, so notation variants
  (MOG-A, BRK-B, BF-B) and the undated FI/FISV pair keep main's behaviour.
falsifier: >
  On a tree carrying ONLY the RenameEvent (no SECURITY_SUPERSESSIONS entry for US-XNYS-PSKY
  and no supersession join), a regeneration that resolves ("membership", "SKYD", 2026-10-11)
  to SEC:US-XNAS-PSKY with no fence refusal falsifies the claim. Equivalently: revert the
  supersession and its join on the merged tree and observe that the fence does NOT fire and
  scripts/build_qbus_news_universe.py exits 0.
so_what: >
  Every venue-transfer rename (KHC is the next known case, already in the same wedge class)
  needs a curated SECURITY_SUPERSESSIONS entry (exact listing key -> canonical id, dated,
  evidenced) in the SAME PR as its RenameEvent, plus the committed data/reference
  regeneration. A RenameEvent alone is not enough: without the bridge the universe consumer
  stays fail-closed and production news goes dark. The security's store key stays the
  inception key (PSKY); migrating it is the separate follow-on under #4622, never a side
  effect of a rename PR.
kind: data
verified_at: 2026-10-11
verified_by: >
  ORCH-N review lane skyd-review-20261011-r1 (ubuntu3): F1 cause — the gate treated every
  key != inception_code as a chain member because _inception_code returns the directory DOT
  spelling for keys no rename mentions, so MOG-A/BRK-B/BF-B were misclassified; variant N
  fixed it; resolve("membership","SKYD",2026-10-11) == SEC:US-XNAS-PSKY re-run by the lane.
  Seat fd47d431 independent parquet diff of the fold head against origin/main:
  vendor_aliases 6046 -> 8924 rows, security_master 2384 -> 3103 rows, removed 0; MOG-A
  0 -> 4 rows, BRK-B/BF-B/FI/FISV byte-identical. Fold C2 counts: security_master added=719
  deleted=0 modified=0, vendor_aliases added=2876 deleted=0 modified=0, issuer_master
  added=716 deleted=0 aggregate_recomputed=1 other_modified=0. #8828 MERGED 2026-10-11 as
  c50af4eb0421 (`gh pr merge 8828 --squash --match-head-commit 005c81ed737e...`), 8/8 paths
  blob-identical on origin/main, needle `unratified_rename_member` present twice in
  origin/main; dataos-identity-seams (ci-pack-11) and ticker-news-qbus (ci-pack-9) SUCCESS
  on the fold head (run 38154035667).
scope:
  - macro
  - market-memory
  - scripts/build_security_master.py
  - scripts/build_qbus_news_universe.py
  - data/reference
confidence: verified
---

The boundary itself is `DSC:PSKY-SKYD-RENAME-IS-ONE-CIK-DATED-BOUNDARY` (one CIK, half-open
date). This record is about the KEY: a rename that moves venue changes the MIC half of the
listing key, so the re-derived key and the committed key disagree and the mint fence —
correctly — refuses to mint a second id for one security. The consumer stays fail-closed by
`DEC:TICKER-NEWS-UNIVERSE-STAYS-FAIL-CLOSED-ON-UNRESOLVED-ALIAS`; the bridge is a curated
cross-venue `SecuritySupersession`, not a writer special-case and not a relaxed fence. The
seat's SKYD FOLD ruling (C1–C4) and the review's F1 finding are recorded in
research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-11.md §4. Downstream
consumers of the rename (price-store key, baskets, Yahoo fetch symbol, WBD index exit) sit
with their owners (#4622 follow-on F-c).
