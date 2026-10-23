---
key: SPLIT-CROSS-SURFACE-CSS-BY-REMINT-MECHANISM
question: "PR #8291 (freshness-chip language invariant R1-R3, head 44c52ce67480) swapped --up-family tokens to the status plane across 13 template/site files and showed FIVE non-inherited red packs: fix forward in one PR, or split?"
answer: "SPLIT. L1 lands the stronger matcher TEST-ONLY with a KNOWN_OFFENDERS ratchet (keys `path::selector`, never line numbers; a new offender fails, a stale entry fails). L2-L6 fix surfaces one PR per REMINT MECHANISM: L2 theme.css pair + hk (P0B browser receipts + research_screener `?v=` re-pin); L3 china_news/committee/news/heatmap/dashboard (source-only); L4 basket_detail (re-fingerprinted site/assets/css/<digest>.css projected across every committed site/basket*/ page); L5/L6 _cn_theme_tape + _theme_tape + sector_central (new EVIDENCE.yml receipts; hover/focus force-state recapture). Each lane deletes exactly its keys from the baseline; the baseline reaches EMPTY when L5/L6 lands."
rationale: "The five gates are per-artefact PINS, each re-minted by a different mechanism on a different host: P0B receipts pin site/theme.css + hk.html.j2; the FTR test pins the basket stylesheet digest across 50+ committed pages the nightly rewrites; the screener golden pins the theme hash; the evidence guard pins receipts per changed template path; the first-frame/ftr-tape tests pin CSS blocks. One PR carrying four remint mechanisms depends on hundreds of site/** files that move nightly \u2014 a moving target no single lane can hold green. Splitting by mechanism makes each PR's pin set re-mintable on one host in one run, and the ratchet keeps the invariant honest between lanes."
alternatives:
  - option: "Fix forward inside #8291"
    why_not: "four hosts/mechanisms in one PR against a nightly-rewritten site/** tree: the R2->R3 round already showed the pin set shifting under the lane"
  - option: "Drop the surface swaps and ship the matcher as an exemption list"
    why_not: "leaves the ZH red-live defect (.dtp-chip--live painting var(--ink-up) under html[data-lang=zh]) live; an exemption list never shrinks \u2014 the ratchet fails on stale entries so it must"
  - option: "One PR per template file"
    why_not: "mechanism, not file, is the unit of re-minting: three files sharing the basket fingerprint must land together or the digest test fails twice"
evidence:
  - "Opus analyst packet 21:3xZ (m1 reproduction at 44c52ce6): ftr 1 failed/88 passed at tests/test_basket_detail_glance_copy.py:132; screener ?v=4a7e3297 vs d6d52074; first-frame 3 failed/112 passed; p0b 4 PINNED PATH errors; visual-evidence 3 errors"
  - "L1 #8293 MERGED e6416bee9552 21:51:45Z (16 keys baseline); L2 #8294 MERGED 692bf4f89057 22:39:29Z (-3 keys, P0B remint + screener re-pin); L3 #8295 MERGED e85878c6a9d1 23:13:03Z (-8 keys); L4 #8297 MERGED c5601f35e105 23:36:33Z (-1 key, f2599f8e->3e1c191f across 121 pages; served css byte-identical 23:43Z); L5/L6 #8296 (-4 keys -> EMPTY) in final CI on head 37b8d565c0dd at record time"
  - "#8291 CLOSED as superseded, head 44c52ce67480831beea42a0d596497fc7ec5ae63 preserved on origin"
  - "precedents #7237, #7712, #7962, #7412; program file ruling D45"
affects:
  - "WS:MARKET-OS"
  - "tests/test_freshness_chips_language_invariant.py"
  - "templates/theme.css"
  - "templates/basket_detail.html.j2"
  - "site/assets/css/*.css"
  - "site/basket*/"
  - "mockups/evidence/f01-live-chip-*/"
confidence: high
reversibility: easy
decided_by: "CEO A seat 587e986f-b055-4df2-a9ed-ca3a709fcc5b (Claude Fable 5.1), single F00 writer under the Astra handoff on macro#6819"
decided_at: 2026-10-02
---

## Standing rule for cross-surface CSS/token changes

Before fanning a token or CSS change across surfaces, enumerate the pinned-artefact gates it
will trip and group the work by the MECHANISM that re-mints each pin (browser receipts,
fingerprinted projections, golden hashes, evidence receipts). One PR per mechanism; a
test-only ratchet first if the invariant must land before the surfaces.
