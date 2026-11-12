# SUPN price defect: `data/yahoo/SUPN.parquet` is Indivior's series

**File.** `data/yahoo/SUPN.parquet` on Macro `main` (blob `c9a089a0`, last refreshed
by "data: daily collection 2026-11-07"; 3,652 rows, 2012-05-01 → 2026-11-06).

**Defect.** From 2014-12-29 — Indivior plc's (INDV) data inception — forward,
SUPN is Supernus Pharmaceuticals in name only: it is Indivior's series,
rescaled by a constant (measured factor 1.000, i.e. a verbatim copy; volume
identical on 100% of overlapping sessions). Sessions before 2014-12-29 are genuine Supernus.

**Evidence** (vs `data/yahoo/INDV.parquet`, 2,966 overlapping sessions):
price ratio SUPN/INDV mean 1.000000, sd 0.00e+00 over the entire overlap;
daily log-return correlation 1.000 in all 72 months 2020-01→2025-12 (≥15
sessions each); identical-return share 1.00. The 2022-06-01→06-07 stale run:
SUPN shows 20.75 flat for six sessions (then 20.00 on 06-08) — INDV's own stale
prices; genuine Supernus traded 27.98–28.66 that week (2026-10-15 refresh copy,
which is correct). An earlier note quoted "16.10 in the other": no checked copy
shows 16.10 in that window; the defect as shipped is the verbatim 20.75. Copies carrying the defect: `main` as of 2026-11-07, the
2026-11-05 custody snapshot, and the prophet-eval-cache / prophet-eval-rederive
copies. The 2026-10-15 refresh is genuine, so the defect entered a daily
collection between 2026-10-16 and 2026-11-05.

**Other SUSPECT_DEFECT series from the scan** (6,705 tickers, 2015–2026; full flag
table in `rotation-core/v4/panel/DUPSCAN_YAHOO.md`): 16 vendor alias/mirror pairs —
AIHS/VAI, AIXC/FFR, ANY/DRK, BBCQW/PSQLW, BCAR/XLAB, BNZI/PARA, BTLN/GGRP,
CHTRP/LBRDP, CYCN/KRSA, DOMO/HUCK, HCWC/HOST, HLX/HOS, MMC/MRSH, OPNW/VRME,
PSKY/SKYD, YFOR/YYGH — identical or near-identical returns and a constant price
ratio between two distinct symbols. None is a large-cap core-universe name, but
each double-counts one company in any breadth or member-level computation that
includes both symbols. SUPN/INDV itself does not flag in the 2026-10-15 clone
snapshot the scan reads — it was measured directly against `main`'s live bytes.

**Effect.** Any breadth or member-level computation using SUPN counts Indivior under
Supernus' name: duplicated sector exposure, false breadth, and a member whose daily
returns are another company's.

**Desk handling.** SUPN is treated unpriced in rotation-core v4 until the series is
replaced; a vendor replacement series is being checked.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
