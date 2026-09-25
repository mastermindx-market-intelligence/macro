# Dark Pool participation trust — denominator quality and physical bound

## Source identity
Original implementation pin: `mastermindx-market-intelligence/Mastermind@0497e28864752e3ab70fa5aa2f1567bc3c9c6aca` (Skillpack 1.0.1 / bootstrap 1), from Macro `4597dd8e72a64aa86d1e07ae1a76924ce9a7b5ae`. Current-base reconciliation and exact-byte proof were performed under protected Mastermind `605cd056c3463c992d85ba76dbcc90fbb758da75` against merge parent `b9b714b75c4c1e28f99481229fc98fd5c151c409`; later main movement was verified path-disjoint from the Dark Pool closure before commit.

## User failure
The Dark Pool desk publicly rendered off-exchange shares above 100%, and those impossible values fed the own-history z-score and standout ordering. The accepted browse-control UI was working; the numbers underneath it were not trustworthy enough to rank.

At pickup, the committed/public-shaped page had 372 rows and 105 impossible participation values; all 16 displayed standouts came from that bad cohort. The worst visible examples were several hundred percent.

## Root cause
`FINRA total_vol / consolidated daily volume` is the intended participation definition. FINRA facility volume is a subset of total market volume, so a value above 1.0 is physically impossible.

The regular Yahoo collector runs early in the long serial collection phase. The baskets OHLCV refresh runs later. For the current-session failure cohort the early Yahoo volume was materially smaller than the later same-day basket OHLCV volume; preferring the later value rescues all 66 current-session impossible ratios in the reproduction while preserving Yahoo as an exact-date fallback. Historical data still contains 971 impossible observations, including a broad 224-name event on 2026-09-22, so source precedence alone is insufficient.

## Repair
1. `scripts/build_darkpool_desk.py` prefers `data/baskets/ohlcv/<ticker>.parquet` volume on dates present there, with the existing Yahoo volume as exact-date fallback. Close/price semantics stay on the existing Yahoo `close` series.
2. `engine/darkpool_signals.compute_name_metrics()` rejects participation observations outside `(0, 1]` before split-history selection, z-score, streak, trend, sparkline or pattern classification.
3. An invalid latest denominator never silently backfills yesterday: all participation-derived current fields remain null.
4. Coverage records how many historical/current observations were quarantined. If a future current row is withheld, the methodology panel explains in plain language that impossible percentages are never ranked.
5. The generated HTML, `site/darkpool_eod.json`, and `data/darkpool/context/latest.json` contain no participation above 1.0. The prospective forward ledger was restored to HEAD because nightly owns ledger advancement.

No FINRA source row, Yahoo/basket source parquet, ATS data, filter threshold, pattern threshold, ranking formula, authentication rule, endpoint, or shared JS/CSS is changed.

## Evidence
- Dark Pool suites: 89 passed.
- Mirror/freshness suites: 40 passed.
- Existing native browse verifier: 16/16 desktop/tablet/mobile/narrow × EN/ZH × dark/light cases passed.
- Trust browser probe: desktop/mobile/narrow in both language/theme directions showed max rendered participation 86.8%, zero page overflow, and zero JS exceptions.
- Current-data candidate: 372 rows, 372 participation values, max valid participation 86.75%, zero >100% in HTML, pane, or context; current invalid count 0; 971 impossible historical observations filtered from baselines; HTML SHA-256 `bd29fc087ac0584384465394e990c8ea48376f0db304ce00e2ea1f5bf63b543f`.
- Candidate context has 24 tagged names / 16 displayed standouts on the current session rather than rankings dominated by impossible denominators.

Local fixture banner 404s in the inherited native verifier are fixture limitations already documented by that verifier; they are not production claims.

## Rerun
```bash
python3 -m pytest -q tests/test_darkpool_signals.py tests/test_darkpool_desk.py
python3 -m pytest -q tests/test_mirror_terminal_context.py tests/test_check_surface_freshness.py
python3 research/evidence/uiux-darkpool-native-desk-20260923/verify_desk.py --site-dir site --output-dir /tmp/darkpool-native-proof
python3 research/evidence/uiux-darkpool-participation-trust-20260924/verify_participation_trust.py --site-dir site --output /tmp/darkpool-trust.json
```

Public acceptance must run both verifiers against `https://www.mastermind-x.com` after the normal VPS static publisher serves the accepted merge. No Vercel path is part of this repair.
