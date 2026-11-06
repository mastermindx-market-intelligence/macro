# Historical US cash calendar evidence — 2026-10-14

Root independently checked the complete official NYSE/ICE annual tables for 2014–2023. `US_CALENDAR_NOTICE_FACTS.json` stores the dated facts and exact primary URLs; it is a research evidence fixture, not another runtime calendar or a historical receipt. Its SHA256 is `e5effb08e7c43dbefa442f3994d9ce08a4e518f3fe7030038ba0b05adbbcde0b`. No prices, returns, holdout labels or collectors were accessed.

The first Fabric census `rf-us-calendar-notices-01a1333c-v1` remains unaccepted. Its retained SHA256 is `87949e8966350857003b734ec6814c1df8fb5ed1282c4f874d45efbf5baebc99`. Root reproduced three material errors against the actual notices: 2014 was present in the 2013 release, July 2 2020 was not a published early close, and the older 2020 release omitted Juneteenth that the later 2021 release adds for 2022 and 2023. Inconsistent year/count annotations in the return are not adopted. The current primary-source reads support the corrected fixture separately.

The existing historical fallback matches every regular closure in the ten corrected annual tables. The current official-notice adapter still classifies all ten years unverified and omits their 20 published early closes. An external prepared patch extends the existing `lib.exchange_holidays` table and provenance only. An in-memory comparison against the actual `lib.us_cash_calendar` adapter verified the annual facts, retained one-off closures, shortened sessions remaining sessions, the 14:00 ET settlement boundary, and July 2 2020 retaining its full-day close. CN/HK/JP/CA data and original verification dates remain unchanged in that prepared candidate.

The shared calendar source is unchanged. Open PR #8721 at `1f93cf99d4cfabaec91c4646c8856e6d242b6f04` contains an incumbent CN extension and per-year provenance change in the same file. The prepared US patch must be reconciled with that existing source ownership before application; it must not replace, copy or release the held CN change. Evidence and candidate are under `methods-review/t01-provenance/prepared-us-calendar-v1/` in the root evidence directory. Candidate SHA256: `cab82a13fbf05ac5aebbd91c307ae49fd7ffe82033676124f22d0929305738e3`.

2010–2013 complete NYSE annual tables remain unqualified by this bounded census. The supplementary SEC evidence below qualifies only the named closure facts; it does not promote those years to complete annual coverage. The immutable registered `lib.nyse_calendar.py` stays byte-identical at SHA256 `7c9167fd416babb64c3067ae7e6237615011ad79e26d826e57005486496410ce`. The 2018 Bush one-off has separate December 1 2018 primary notice support. The 2022/2023 facts use the later December 27 2021 release; the December 28 2020 release is used only for 2021.

These current public notices do not authenticate historical availability, Yahoo rights, provider revision completeness or a candidate input contract. The direct HTML capture returned HTTP403 and was not retried or replaced through another downloader. The fixture cites the already-permitted browser-tool reads; no raw HTML retention/hash is asserted. Calendar source/CI/merge/installation and full 2010–2023 qualification are still open.


## Supplementary NYSE-authored SEC evidence

[SEC release 34-68137, November 1, 2012](https://www.sec.gov/rules/sro/nyse/2012/34-68137.pdf), pages 2–3, publishes NYSE's account that its market closed on October 29 and 30 because of Hurricane Sandy and reopened October 31. This closes the missing primary corroboration for those two extraordinary closures. It is a retrospective notice, not proof of advance knowledge or a contemporaneous input receipt.

[SEC release 34-68243, November 15, 2012](https://www.sec.gov/rules/sro/nyse/2012/34-68243.pdf), page 2, states that NYSE announced 1 p.m. closes on July 3, the day after Thanksgiving, and December 24 for 2012–2014. The six dates for 2012–2013 are stored under `partial_year_facts`; Thanksgiving dates are explicitly derived from the fourth Thursday of November. The same statement corroborates the already-qualified 2014 dates. The notice does not establish the original announcement timestamp, and it postdates the July 2012 close.

These facts are deliberately separate from the ten complete annual tables. A 2011 press-release reprint found during search listed only Thanksgiving early closes for 2012–2013; that incomplete reprint was not accepted as a complete early-close calendar. European cash-market, Liffe futures and clearing-service calendars were excluded because they describe different markets. Complete 2010–2013 NYSE annual closure coverage remains missing.

Both SEC documents were read through the public web tool. Subsequent direct PDF captures returned HTTP403 and were not retried, so no raw PDF retention/hash is asserted. The prepared runtime patch, immutable legacy calendar and incumbent CN source remain unchanged. No prices, returns, holdout labels or historical collector were accessed.


## Compatibility preparation against the incumbent CN source

On2026-10-14, PR8721 remained OPEN/DRAFT at `1f93cf99d4cfabaec91c4646c8856e6d242b6f04`. A new external candidate combines its exact CN calendar source with the previously checked US2014–2023addition. The two textual conflicts were the coverage prose and per-year verification-date mapping; both are resolved only in the external candidate. CN dates retain2026-10-11verification and the US historical rows retain2026-10-14verification. Full coverage dictionaries, yearly tables and daily early-close/EN/ZH names over2010–2030 match the prior US candidate for US and the exact CN owner for all other markets. This is compatibility evidence, not new notice qualification or source-write custody.

Candidate SHA256`a9d5cc2ee56e9472039e94bf9a869d2e551404c0b599c45f3c852ed3debefefc`; patch SHA256`8d76ecc9a0e1e97e638143a76bc069cac276845f888b4f7cb044e04e6920be98`. Reproduction and adjudication are in `methods-review/t01-provenance/prepared-us-calendar-cn-compatible-v1/` under the programme evidence root. The canonical calendar file and PR8721 branch remain unchanged; the historical ChatGPT handoff was not treated as an active source owner.
