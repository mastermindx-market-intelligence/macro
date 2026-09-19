---
key: CHINA-HEATMAP-LACKED-SETTLED-CLOSE-PUBLISHER
claim: >
  The public China A-share heatmap had no binding settled-close publisher:
  asia-close advanced data/china_search/closes.parquet but did not rebuild or
  validate site/marketdata/china_heatmap.json, while generic render lanes could
  stamp a new generated_utc over whatever close panel their checkout carried.
  On 2026-09-16 the canonical close panel was through 2026-09-15 while the
  public JSON and standalone SSR page still described 2026-09-09.
falsifier: >
  Run `git show 459eafb838d9944e58e6a65413e282f2a13826ef:.github/workflows/asia-close.yml`
  and identify a post-collection step that rebuilt the China heatmap and bound
  its JSON asof, current-membership coverage, standalone SSR session, and
  completed mainland-session clock before publication; or show that the cited
  source and public artifact dates were not 2026-09-15 and 2026-09-09.
so_what: >
  A green collection/render estate could silently serve old China tiles on both
  china_heatmap.html and the china.html markets modal. The settled-close lane
  must own the producer, recheck at every commit/rebase boundary, preserve
  unrelated China/HK outputs on a heatmap-only failure, and end red unless the
  source, JSON, SSR and exchange clock agree.
kind: runtime
verified_at: 2026-09-16
verified_by: >
  pandas readback of data/china_search/closes.parquet and
  data/china_search/members.parquet; JSON/HTML readback of the committed and
  live public artifacts; workflow archaeology at merge base 459eafb838d9;
  cache-busted HTTPS probes of /marketdata/china_heatmap.json,
  /china_heatmap.html and /china.html on 2026-09-16.
scope:
  - macro
  - .github/workflows/asia-close.yml
  - scripts/build_market_heatmap.py
  - scripts/check_china_heatmap_freshness.py
  - site/marketdata/china_heatmap.json
  - site/china_heatmap.html
  - tests/test_china_heatmap_freshness.py
confidence: verified
related:
  - PR:7193
---

## Current repair boundary

PR #7193 on `sol/china-heatmap-freshness-20260916-sol` establishes the
settled-close owner and fail-closed publication contract. It remains
`BUILT_NOT_PROVEN` until exact-head CI and independent review pass, the repair is
merged, a canonical asia-close run produces the current mainland session, and
both public surfaces are verified from deployed bytes in a real browser.

The whole-board breadth side-store was independently observed frozen at
2026-09-09. The heatmap producer already rejects a mismatched breadth row and
falls back to explicitly labelled map-sample breadth; that degradation is honest
but does not constitute recovery of the separate whole-board collector.

## Do not redo

Do not solve this by adding another event, state, publication or freshness
plane. Extend the existing asia-close producer, existing China close/membership
stores, existing market-heatmap payload, and existing page/modal consumers.
Do not treat generated_utc as a market-session receipt, and do not let a
heatmap-only failure suppress otherwise-valid China/Hong Kong outputs.
