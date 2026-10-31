---
key: EDGAR-SUBMISSIONS-ACCEPTANCE-DATETIME-IS-TRUE-UTC
claim: >
  The EDGAR submissions-JSON `acceptanceDateTime` (for example
  `2026-01-28T21:04:38.000Z`) is true UTC: it equals the SGML header
  `<ACCEPTANCE-DATETIME>` (America/New_York wall time) converted to UTC. It is
  not New York wall time labelled `Z`, which is what WP31 prereg §10 A2 assumed.
falsifier: >
  For a non-universe filing, read
  data.sec.gov/submissions/CIK##########.json `filings.recent.acceptanceDateTime`
  and the html-unescaped `<ACCEPTANCE-DATETIME>` in the filing's
  `-index-headers.html`. The claim is disproved if the JSON value minus the
  header read as New York time is not zero, for example +4 h (EDT) or +5 h
  (EST). Reference case: MSFT CIK 789019, accession 0001193125-26-027198, has
  JSON `2026-01-28T21:04:38.000Z` and header `20260128160438`, so the
  difference is 0. A2 pinned the JSON value at `2026-01-29T02:04:38Z`, which
  is the true instant plus 5 h.
so_what: >
  Read the JSON clock as given and do not subtract the New York offset. WP31's
  A2 correction makes t_rel 4-5 h early. No data leaks from this, but C(e), the
  cost exit, the K window and the A0 filter can each land one session early.
  Prereg §10 is append-only, so the correction is withdrawn prospectively by
  §10 A5 (Macro #10302) for clocks at or after its E (2026-11-16T00:00Z), and
  clocks before E keep A2. Do not build a shared reader-side correction on
  A2's premise; Macro #10295 is closed unmerged for that reason. Check a stored
  capture's vintage against the headers before trusting its clock: the
  2026-07-05 8-K store capture held New York wall time labelled `Z` for 27
  non-universe issuers, and the 2026-10-04 capture does not.
kind: data
verified_at: 2026-10-31
verified_by: >
  The C19 seat read live SEC data on non-universe filers only, reading headers
  only. A2's four cited filings (MSFT, JPM) agreed 4/4. A census of 9 filers
  (Berkshire, Bridgewater, Renaissance, Citadel, JPMorgan, Walmart, Microsoft,
  Lennar and one more) across forms 10-K, 10-Q, 13F-HR, 4 and 8-K, 2015-2026,
  EST and EDT, agreed 117/117, with 2 index-headers 404s excluded. A sample of
  the October 2026 8-K store capture agreed 76/76. The evidence table is in
  Macro #10302 (prereg §10 A5).
scope:
  - macro
  - research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md
  - scripts/c19_wp31_sources.py
  - collectors/edgar_8k.py
  - WS:COMMISSION-19-DATA-INTELLIGENCE
confidence: verified
---

The cause of A2's readings is not established. No capture the seat could read
shows A2's direction for these filings.

The SGML header half of A2 is correct: `<ACCEPTANCE-DATETIME>` is New York wall
time, and it must be converted with the zone offset in force at that wall time.

(unverified) DSC:FF-1R-ANGO-ACCEPTANCE-DATETIME-CONFLICT records a prior-manifest
versus current-Submissions acceptance_datetime conflict. That conflict may be
the same representational vintage shift. It has not been checked, and nothing
here changes that record's stop rule.
