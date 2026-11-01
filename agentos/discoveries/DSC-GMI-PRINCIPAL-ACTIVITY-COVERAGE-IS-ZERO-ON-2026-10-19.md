---
key: GMI-PRINCIPAL-ACTIVITY-COVERAGE-IS-ZERO-ON-2026-10-19
claim: >
  Measured on source_commit 0221d6e1 by scripts/gmi_coverage_proof.py (PR #9745), the
  explicit U.S. core universe is 1939 securities, 1935 eligible, 1927 issuers resolved and
  1925 eligible issuers (6 unresolved; exclusions ETHA, IBIT, SPY, VMRK), and the China
  universe is 1019 listings with 0 issuers resolved. Qualified principal-activity
  coverage is 0 on both markets. The U.S. remainder is closed-enum and additive across
  securities: IDENTITY_NOT_QUALIFIED 726, NOT_IN_GRAPH 721, VENDOR_MEMBERSHIP_ONLY 1201,
  NO_ACTIVITY_EVIDENCE 4, NO_ISSUER_EVIDENCE 3, ISSUER_EVIDENCE_CONFLICT 2, DEFERRED 1.
  Canada is NOT_IN_MASTER 167 and other markets UNSUPPORTED_MARKET 233. The 68 micro
  themes are all scope-versioned and none is owner-reviewed.
falsifier: >
  Re-run python3 scripts/gmi_coverage_proof.py on a later origin/main (it refuses to write
  data/ or site/; output goes to research/theme_graph/coverage_<date>/). Any non-zero
  qualified principal-activity count, a non-closed-enum remainder, or a change in the
  U.S. denominators without a security-master change refutes the specific numbers; the
  structural claim (zero until the history fold is wired and a curator ratifies PROPOSED
  rows) is refuted by a qualified activity row that arrived by any other path.
so_what: >
  The zero is a wiring and ownership fact, not a data-collection gap to be filled by
  scraping or by admitting vendor memberships: 1201 U.S. securities already carry
  vendor-only membership that gate 2 forbids promoting, and 726 are identity-unqualified
  on the Data OS side. The first non-zero reading requires, in order, the A2 history fold
  wired into the nightly build, PROPOSED rows ratified by a named curator, and Data OS
  identity qualification; no GMI-side shortcut closes it. Report coverage as this
  closed-enum table, never as a percentage alone.
kind: data
verified_at: 2026-10-19
verified_by: >
  Fable Meta-CEO seat 6f14c2da: read of research/theme_graph/coverage_20261019/
  COVERAGE_REPORT.md and coverage_report.json at PR #9745 head
  ed4188cfb94aaf18fbd3e5fb538caf73a93e71f1 (report_version 0cd3e337…, manifest
  2373df79…), judged against the step-7 packet before READY.
scope:
  - macro
  - research/theme_graph/coverage_20261019/
  - scripts/gmi_coverage_proof.py
  - data/reference/security_master.parquet
confidence: verified
cited_by:
  - WS:GMI-THEME-GRAPH
  - DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19
---

The proof script runs as its own legacy-jobs.yml step ("GMI step-7 coverage proof (measurement
only; refuses data/ and site/ output)"), so the numbers are re-measurable in CI without touching
the render path.
