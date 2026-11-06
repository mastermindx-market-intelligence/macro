# G0-S selection record — the three E0 reference gaps (pack 1.1.0)

Lane G0-S (SPEC_G0 Rev 2 §3): select `whk_replacement_issuer`,
`foreign_issuer_f3_witness` and `held_out_pattern_witness` from the served
universe, requalify the six archetypes, and seal the held-out answer. Base
`e568e13820a9d88daca57bb4bf0058038d7a659e`. Candidate lists are built exactly
per §3: issuers with a filing of the named form with `filing_date` inside
2025-10-01..2026-10-15 in `data/capital_structure/source_manifest.jsonl` +
`source_manifest.part-0002.jsonl` (read via `git show`, never materialized),
one entry per CIK at its first qualifying accession, ordered by accession
ascending, excluding the six archetype CIKs (AIR 0000001750, CLNN 0001822791,
QNCX 0001662774, WHK 0001921603, LPTH 0000889971, EDBL 0001809750) and every
CIK already chosen for another gap. Candidates are tested in list order
against SEC primary documents only (submissions JSON + the named filing's
primary documents); the first candidate passing every criterion of its row is
chosen; taste is not a criterion.

- Window: 2025-10-01..2026-10-15 (filing_date).
- Candidate counts: whk_replacement_issuer 293 (S-3 | S-3/A), foreign_issuer_f3_witness 114 (F-3, exact form string),
  held_out_pattern_witness 458 (424B5).
- Budget: at most 60 candidates tested per gap; pacing 1 req/s; user agent
  `MastermindMarketIntelligence-ResearchSeat/1.0 (+https://www.mastermind-x.com)`.
- Reference pack after this lane: sha256 `7ccbf198dceb12174f1ed8239ecf73dda2932eff42d2a5e0f787a60febc66f0e` (pinned into the L0 pack).

## Gap: whk_replacement_issuer — OPEN (budget stop, failure list below)

Selection rule: domestic issuer listed on Nasdaq; S-3 or S-3/A whose exhibit
index files at least one form of warrant, pre-funded warrant or convertible
note (EX-4.x), plus a 424B takedown under that S-3. Numerical path: exercisable
shares under the filed warrant terms (exercise price, share count, holder cap)
with each operand's span.

**Result: OPEN.** 293 candidates; 60 tested against SEC primary documents (submissions index for each,
EX-4.x exhibit documents read where the earlier criteria passed); 183 failed the exhibit criterion
straight from the accession inventory in the served universe (no EX-4.x document at the first qualifying
accession); 50 not tested (budget). First-failure tally over the 60 fetch-tested candidates:
`c1_nasdaq_domestic_issuer`=16, `c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note`=21 (document-read;
183 more via the inventory), `c3_424b_takedown_under_that_s3`=22,
`c4_operand_spans_exercisable_shares_terms`=1. No candidate passed every criterion, so the gap stays open in the
pack with this failure list; WHK keeps `replacement_owed: true` with no replacement named and none guessed.

Criteria were evaluated per candidate in the order c1 (Nasdaq + domestic, from the submissions index), c3 (424B
takedown under the same file number, same index), c2 (EX-4.x exhibit document content), c4 (operand spans in the
filed exhibit) — the row is a conjunction, so the first proven failure ends the candidate and any not-yet-evaluated
criterion is named in its row. The nearest miss was #45 Aquestive Therapeutics (AQST, 0001140361-26-026568): its
only EX-4.x exhibit is a blank Form of Common Stock Purchase Warrant (exercise price `$[•]`, Warrant Shares
`[_____]`), so no exercise price or share count can be sourced from the issuer's own filed text and c4 counts as
failed per the seat law (a criterion that cannot be verified from a primary SEC document is failed).

### Candidate table (all 293 entries in accession order; fetch-tested rows carry their first failed criterion)

| # | CIK | accession | filing date | ticker | first failed criterion / result |
|---|---|---|---|---|---|
| 4 | 0001818644 | 0000947871-26-000565 | 2026-05-19 | LIDR | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 2 EX-4.x exhibit documents read (['ss6342442_ex0413.htm', 'ss6342442_ex0414.htm']); none is a warrant/pre-funded warrant/convertible note |
| 11 | 0001408443 | 0001104659-26-060391 | 2026-05-13 | MIST | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 16 | 0001533615 | 0001104659-26-074685 | 2026-06-16 | XRN | c1_nasdaq_domestic_issuer — exchanges=['NYSE', 'NYSE', 'NYSE'] fpi_or_no_state_of_incorporation |
| 18 | 0001325670 | 0001104659-26-077825 | 2026-06-25 | FRST | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 22 | 0002046042 | 0001104659-26-080303 | 2026-07-02 | JCAP | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 24 | 0001009759 | 0001104659-26-081266 | 2026-07-07 | CEPL | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 2 EX-4.x exhibit documents read (['tm2619464d2_ex4-7.htm', 'tm2619464d2_ex4-8.htm']); none is a warrant/pre-funded warrant/convertible note |
| 30 | 0001875558 | 0001104659-26-099717 | 2026-08-21 | NVCT | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 33 | 0001650664 | 0001104659-26-103906 | 2026-08-31 | EDIT | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 38 | 0001082324 | 0001140361-26-021703 | 2026-05-15 | VHC | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ny20073543x1_ex4-3.htm']); none is a warrant/pre-funded warrant/convertible note |
| 39 | 0000803164 | 0001140361-26-022543 | 2026-05-22 | COFS | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 43 | 0000911147 | 0001140361-26-024930 | 2026-06-11 | CNTY | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 45 | 0001398733 | 0001140361-26-026568 | 2026-06-26 | AQST | c4_operand_spans_exercisable_shares_terms — the only EX-4.x exhibit (ny20076831x1_ex4-2.htm, Form of Common Stock Purchase Warrant) is a blank form: Exercise Price $[•], Warrant Shares [_____]; no exercise price or share cou |
| 49 | 0001130713 | 0001140361-26-031312 | 2026-08-05 | BBBY | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ny20078361x1_ex4-3.htm']); none is a warrant/pre-funded warrant/convertible note |
| 63 | 0001840233 | 0001193125-26-218212 | 2026-05-12 | XLO | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 68 | 0001738827 | 0001193125-26-224308 | 2026-05-14 | KLXE | c1_nasdaq_domestic_issuer — exchanges=['Nasdaq'] fpi_or_no_state_of_incorporation |
| 78 | 0000931148 | 0001193125-26-236861 | 2026-05-22 | EAF | c1_nasdaq_domestic_issuer — exchanges=['NYSE'] fpi_or_no_state_of_incorporation |
| 87 | 0001419041 | 0001193125-26-253668 | 2026-06-02 | FBRX | c1_nasdaq_domestic_issuer — exchanges=[] fpi_or_no_state_of_incorporation |
| 93 | 0001500881 | 0001193125-26-275933 | 2026-06-18 | EU | c1_nasdaq_domestic_issuer — exchanges=['Nasdaq'] fpi_or_no_state_of_incorporation |
| 95 | 0002000046 | 0001193125-26-281283 | 2026-06-24 | FETH | c1_nasdaq_domestic_issuer — exchanges=['CBOE'] fpi_or_no_state_of_incorporation |
| 96 | 0001661998 | 0001193125-26-282783 | 2026-06-25 | QTTB | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 2 EX-4.x exhibit documents read (['d142257dex42.htm', 'd142257dex43.htm']); none is a warrant/pre-funded warrant/convertible note |
| 102 | 0001055726 | 0001193125-26-294457 | 2026-07-02 | INO | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 4 EX-4.x exhibit documents read (['d141328dex45.htm', 'd141328dex47.htm', 'd141328dex48.htm', 'd141328dex49.htm']); none is a warrant/pre-funded warrant/convertible note |
| 107 | 0001534133 | 0001193125-26-316100 | 2026-07-24 | CALC | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 109 | 0001720265 | 0001193125-26-327131 | 2026-07-31 | ZCSH | c1_nasdaq_domestic_issuer — exchanges=['NYSE'] fpi_or_no_state_of_incorporation |
| 112 | 0001817241 | 0001193125-26-338453 | 2026-08-06 | ARTV | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 113 | 0000750558 | 0001193125-26-340365 | 2026-08-07 | QNBC | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 2 EX-4.x exhibit documents read (['qnbc-ex4_1.htm', 'qnbc-ex4_2.htm']); none is a warrant/pre-funded warrant/convertible note |
| 115 | 0001501796 | 0001193125-26-344699 | 2026-08-11 | AURA | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 116 | 0001609809 | 0001193125-26-349330 | 2026-08-13 | MCRB | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 118 | 0001794546 | 0001193125-26-352226 | 2026-08-14 | CARL | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 122 | 0001590976 | 0001193125-26-372426 | 2026-08-28 | MBUU | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['d143643dex42.htm']); none is a warrant/pre-funded warrant/convertible note |
| 123 | 0001701108 | 0001193125-26-374702 | 2026-08-28 | SPRO | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 124 | 0001869105 | 0001193125-26-378637 | 2026-09-01 | BBOT | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 128 | 0001808898 | 0001193125-26-390758 | 2026-09-14 | BNTC | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 134 | 0000778164 | 0001213900-26-053961 | 2026-05-08 | ALTO | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 3 EX-4.x exhibit documents read (['ea028939101ex4-1.htm', 'ea028939101ex4-2.htm', 'ea028939101ex4-3.htm']); none is a warrant/pre-funded warrant/convertible note |
| 135 | 0001832483 | 0001213900-26-054207 | 2026-05-11 | SERV | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ea028980701ex4-9.htm']); none is a warrant/pre-funded warrant/convertible note |
| 146 | 0001766140 | 0001213900-26-065819 | 2026-06-05 | UNCY | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 147 | 0001819493 | 0001213900-26-065915 | 2026-06-05 | XOS | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 4 EX-4.x exhibit documents read (['ea029352201ex4-3.htm', 'ea029352201ex4-5.htm', 'ea029352201ex4-6.htm', 'ea029352201ex4-7.htm']); none is a warrant/pre-funded warrant/conve |
| 151 | 0001616262 | 0001213900-26-071160 | 2026-06-23 | RMCF | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 2 EX-4.x exhibit documents read (['ea029516201ex4-2.htm', 'ea029516201ex4-3.htm']); none is a warrant/pre-funded warrant/convertible note |
| 153 | 0001840317 | 0001213900-26-072701 | 2026-06-26 | VEEA | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ea029595401ex4-4.htm']); none is a warrant/pre-funded warrant/convertible note |
| 155 | 0001386570 | 0001213900-26-072796 | 2026-06-29 | NAGE | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 3 EX-4.x exhibit documents read (['ea029479701ex4-4.htm', 'ea029479701ex4-7.htm', 'ea029479701ex4-8.htm']); none is a warrant/pre-funded warrant/convertible note |
| 156 | 0002028293 | 0001213900-26-073796 | 2026-06-30 | RAIN | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ea029618201ex4-6.htm']); none is a warrant/pre-funded warrant/convertible note |
| 158 | 0001996192 | 0001213900-26-076449 | 2026-07-08 | LSH | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 168 | 0001865506 | 0001213900-26-092746 | 2026-08-24 | ZEO | c1_nasdaq_domestic_issuer — exchanges=['Nasdaq', 'Nasdaq'] fpi_or_no_state_of_incorporation |
| 169 | 0001734005 | 0001213900-26-094595 | 2026-08-28 | NIKI | c1_nasdaq_domestic_issuer — exchanges=['Nasdaq'] fpi_or_no_state_of_incorporation |
| 170 | 0001930021 | 0001213900-26-095090 | 2026-08-28 | HOVR | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ea030294001ex4-9.htm']); none is a warrant/pre-funded warrant/convertible note |
| 172 | 0001734750 | 0001213900-26-097710 | 2026-09-04 | MOVE | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 2 EX-4.x exhibit documents read (['ea030366301ex4-5.htm', 'ea030366301ex4-6.htm']); none is a warrant/pre-funded warrant/convertible note |
| 179 | 0001275158 | 0001275158-26-000053 | 2026-08-21 | NDLS | c1_nasdaq_domestic_issuer — exchanges=['Nasdaq'] fpi_or_no_state_of_incorporation |
| 181 | 0001411690 | 0001411690-26-000021 | 2026-05-08 | BNGO | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 203 | 0000093314 | 0001477932-26-004265 | 2026-07-10 | VNRX | c1_nasdaq_domestic_issuer — exchanges=['NYSE'] fpi_or_no_state_of_incorporation |
| 206 | 0001692415 | 0001493152-26-022504 | 2026-05-12 | CODX | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ex4-1.htm']); none is a warrant/pre-funded warrant/convertible note |
| 207 | 0001357459 | 0001493152-26-022548 | 2026-05-12 | PALI | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 212 | 0002026353 | 0001493152-26-025038 | 2026-05-22 | ATHR | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ex4-5.htm']); none is a warrant/pre-funded warrant/convertible note |
| 216 | 0001818274 | 0001493152-26-026624 | 2026-06-01 | ARAI | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 1 EX-4.x exhibit documents read (['ex4-1.htm']); none is a warrant/pre-funded warrant/convertible note |
| 218 | 0001788230 | 0001493152-26-026907 | 2026-06-02 | IPST | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 222 | 0001963088 | 0001493152-26-027729 | 2026-06-08 | ATCH | c1_nasdaq_domestic_issuer — exchanges=['NYSE', 'OTC'] fpi_or_no_state_of_incorporation |
| 226 | 0001582554 | 0001493152-26-028881 | 2026-06-16 | MTNB | c1_nasdaq_domestic_issuer — exchanges=['NYSE'] fpi_or_no_state_of_incorporation |
| 229 | 0001269026 | 0001493152-26-029991 | 2026-06-25 | SINT | c3_424b_takedown_under_that_s3 — no 424B3/424B4/424B5 with the S-3's fileNumber on/after the S-3 date in the recent index |
| 234 | 0001541157 | 0001493152-26-031967 | 2026-07-02 | AKTX | c1_nasdaq_domestic_issuer — exchanges=['Nasdaq'] fpi_or_no_state_of_incorporation |
| 236 | 0001289340 | 0001493152-26-033396 | 2026-07-15 | STXS | c1_nasdaq_domestic_issuer — exchanges=['NYSE'] fpi_or_no_state_of_incorporation |
| 240 | 0001906364 | 0001493152-26-034828 | 2026-07-27 | BXBL | c2_s3_exhibit_files_ex4_warrant_prefund_or_convertible_note — first 2 EX-4.x exhibit documents read (['ex4-1.htm', 'ex4-1.htm']); none is a warrant/pre-funded warrant/convertible note |
| 243 | 0001878313 | 0001493152-26-039679 | 2026-08-21 | MAIA | c1_nasdaq_domestic_issuer — exchanges=['NYSE'] fpi_or_no_state_of_incorporation |
| 244 | 0001661053 | 0001493152-26-039696 | 2026-08-21 | NVNO | not tested (budget) |
| 245 | 0000027093 | 0001493152-26-039732 | 2026-08-21 | USAU | not tested (budget) |
| 246 | 0001892492 | 0001493152-26-040277 | 2026-08-27 | ORBS | not tested (budget) |
| 247 | 0001712762 | 0001493152-26-040412 | 2026-08-27 | BIAF | not tested (budget) |
| 248 | 0001449792 | 0001493152-26-041392 | 2026-09-03 | PPSI | not tested (budget) |
| 249 | 0002019793 | 0001493152-26-042026 | 2026-09-10 | SAFX | not tested (budget) |
| 250 | 0001725430 | 0001493152-26-042775 | 2026-09-15 | INBS | not tested (budget) |
| 251 | 0001862463 | 0001493152-26-046837 | 2026-10-13 | AMOD | not tested (budget) |
| 252 | 0001598981 | 0001493152-26-047035 | 2026-10-14 | SKYX | not tested (budget) |
| 253 | 0001580149 | 0001520138-26-000244 | 2026-06-18 | BIVI | not tested (budget) |
| 254 | 0001537435 | 0001537435-26-000073 | 2026-08-31 | TGEN | not tested (budget) |
| 255 | 0001570562 | 0001570562-26-000071 | 2026-06-05 | EOLS | not tested (budget) |
| 256 | 0001603978 | 0001603978-26-000098 | 2026-10-13 | AQB | not tested (budget) |
| 257 | 0001859392 | 0001628280-26-032968 | 2026-05-08 | GLXY | not tested (budget) |
| 258 | 0000785557 | 0001628280-26-040791 | 2026-06-04 | DLHC | not tested (budget) |
| 259 | 0001290900 | 0001628280-26-040865 | 2026-06-04 | CVGI | not tested (budget) |
| 260 | 0001587987 | 0001628280-26-045593 | 2026-06-25 | NEWT | not tested (budget) |
| 261 | 0001253689 | 0001628280-26-046544 | 2026-07-01 | CBIO | not tested (budget) |
| 262 | 0001360604 | 0001628280-26-051463 | 2026-07-31 | HR | not tested (budget) |
| 263 | 0001805833 | 0001628280-26-052737 | 2026-08-04 | SST | not tested (budget) |
| 264 | 0001736730 | 0001628280-26-054389 | 2026-08-06 | CAMP | not tested (budget) |
| 265 | 0001699350 | 0001628280-26-054836 | 2026-08-07 | SI | not tested (budget) |
| 266 | 0001434728 | 0001628280-26-054889 | 2026-08-07 | GWRS | not tested (budget) |
| 267 | 0001737287 | 0001628280-26-056232 | 2026-08-12 | ALLO | not tested (budget) |
| 268 | 0001378325 | 0001628280-26-056802 | 2026-08-13 | CV | not tested (budget) |
| 269 | 0001842279 | 0001628280-26-060724 | 2026-09-04 | OPAL | not tested (budget) |
| 270 | 0001819438 | 0001628280-26-060945 | 2026-09-08 | GWH | not tested (budget) |
| 271 | 0001664710 | 0001628280-26-061321 | 2026-09-10 | KROS | not tested (budget) |
| 272 | 0001621221 | 0001640334-26-000867 | 2026-05-14 | ARTL | not tested (budget) |
| 273 | 0001842566 | 0001654954-26-004667 | 2026-05-11 | AISP | not tested (budget) |
| 274 | 0000829323 | 0001654954-26-007037 | 2026-07-30 | INUV | not tested (budget) |
| 275 | 0001141197 | 0001654954-26-007871 | 2026-08-25 | PED | not tested (budget) |
| 276 | 0001665300 | 0001665300-26-000005 | 2026-05-21 | PHUN | not tested (budget) |
| 277 | 0001729427 | 0001683168-26-004123 | 2026-05-19 | CNSP | not tested (budget) |
| 278 | 0001462223 | 0001683168-26-004356 | 2026-05-28 | NIXX | not tested (budget) |
| 279 | 0001756180 | 0001683168-26-005364 | 2026-07-08 | NCRA | not tested (budget) |
| 280 | 0001748137 | 0001683168-26-006169 | 2026-08-11 | NEOV | not tested (budget) |
| 281 | 0001787740 | 0001683168-26-007707 | 2026-10-08 | VBIO | not tested (budget) |
| 282 | 0001830072 | 0001683168-26-007759 | 2026-10-09 | IPW | not tested (budget) |
| 283 | 0001706946 | 0001706946-26-000071 | 2026-05-14 | SPCE | not tested (budget) |
| 284 | 0002038439 | 0001731122-26-001005 | 2026-08-03 | VWAV | not tested (budget) |
| 285 | 0001734342 | 0001734342-26-000054 | 2026-06-11 | AMTB | not tested (budget) |
| 286 | 0000840715 | 0001753926-26-001050 | 2026-06-25 | CLRO | not tested (budget) |
| 287 | 0001758766 | 0001758766-26-000054 | 2026-06-02 | STEM | not tested (budget) |
| 288 | 0001808805 | 0001808805-26-000040 | 2026-09-11 | NAUT | not tested (budget) |
| 289 | 0001828536 | 0001828536-26-000091 | 2026-07-17 | NRGV | not tested (budget) |
| 290 | 0001467761 | 0001829126-26-005625 | 2026-05-22 | FIEE | not tested (budget) |
| 291 | 0001479419 | 0001829126-26-006442 | 2026-06-12 | KALA | not tested (budget) |
| 292 | 0001979414 | 0001829126-26-006487 | 2026-06-15 | NTHI | not tested (budget) |
| 293 | 0001832511 | 0001832511-26-000039 | 2026-10-15 | PIII | not tested (budget) |

Rows #1–293 not shown above with a fetch-test outcome failed the exhibit criterion on the accession inventory
(no EX-4.x document in the accession) or were not reached within the 60-candidate budget; the full ordered list
is in the lane scratch (decisions_whk_replacement_issuer.json) and every fetch is in the ledger below.

## Gap: foreign_issuer_f3_witness — CLOSED by EuroDry Ltd. (EDRY)

Selection rule: Nasdaq-listed FPI (files 20-F) with an F-3 (not F-3ASR) whose prospectus invokes General
Instruction I.B.5. Numerical path `foreign_f3.ib5_baby_shelf_cap` (rule `form_f3.I.B.5`): F-3 baby-shelf cap =
public float / 3 − trailing-12-month I.B.5 sales, from the F-3 public-float statement.

**CHOSEN: candidate #1 — EuroDry Ltd. (EDRY), CIK 0001731388, Nasdaq, Marshall Islands (state-of-incorporation
code 1T), 20-F filer.** Qualifying filing: F-3 accession `0000919574-26-005806`, filed 2026-08-27, primary
document `p15057625_f-3.htm`. The prospectus invokes General Instruction I.B.5 of Form F-3 and states, in its own
text: (operand span `public_float`, fixture `tests/fixtures/capital_structure/reference/g0/foreign_f3_witness_edry_f3.txt`,
span sha256 `69b5a6438f2b3b1760d1b027ac194881175a5bd5063b6831abe17cf94ea47adc`) the aggregate market value of
common stock held by non-affiliates as of August 25, 2026; and (operand span `ib5_trailing_sales`, span sha256
`6180d65085523758971eecc212266417bfb97092c61c62c22408ad3d401b5320`) that no securities have been offered under
I.B.5 in the trailing twelve calendar months (a stated zero). Computed cap (Decimal, half-even to cents):
65613529/3 = 21871176.33 USD, exact fraction 65613529/3. Values are recorded in the pack's EDRY identity
`g0_case` block; this gap is not sealed.

| # | CIK | accession | filing date | ticker | first failed criterion / result |
|---|---|---|---|---|---|
| 1 | 0001731388 | 0000919574-26-005806 | 2026-08-27 | EDRY | PASS |

(The initial walk of this gap used an over-narrow sales-statement regex requiring a digit `12`; the F-3
eligibility statements write `twelve calendar month`. That walk tested 60 candidates before the tool fix
(first-failure tally c1=7, c2=31, c3=22) and is superseded: under the corrected criterion the walk stops at
candidate #1, so no later candidate is reached. The superseded walk's c1/c2 criteria are identical to the final
ones; only its c3 verdicts are void. All of its requests are in the ledger below.)

## Gap: held_out_pattern_witness — CLOSED by Rapid Micro Biosystems, Inc. (RPID)

Selection rule: Nasdaq-listed domestic S-3 baby-shelf issuer (I.B.6) with BOTH an ATM programme AND a registered
direct takedown in the trailing 12 months, and a 424B5 supplement in the window whose text states both the
non-affiliate public float (with its measurement date) and the I.B.6 sales in the prior 12 calendar months.
Numerical path `held_out.ib6_headroom` (rule `form_s3.I.B.6`), cutoff = the supplement's filing date.

**CHOSEN: candidate #57 — Rapid Micro Biosystems, Inc. (RPID), CIK 0001380106, Nasdaq, Delaware.** Qualifying
filing: 424B5 accession `0001104659-26-063928`, filed 2026-05-19 (the cutoff), primary document
`tm2614072-1_424b5.htm`, under registration statement 333-276081 (S-3 `0001104659-23-126443`, filed 2023-12-15).
The supplement's own text binds all four evidence spans (fixture
`tests/fixtures/capital_structure/reference/g0/held_out_pattern_witness_rpid_424b5.txt`):

- `public_float_ib6` (span sha256 `824fc1c57976294497c6ff8a67cbb907e10f070d8c000cb781c9e2d0ad379169`): the
  non-affiliate public float statement with its measurement date;
- `ib6_trailing_sales` (span sha256 `b1460ac36ce821623e4980f2b7d43e4d9b23a5543cd39520fcbd9298e2a7e895`): the
  I.B.6 prior-12-calendar-month none-offered statement (a stated zero);
- `atm_programme` (span sha256 `144bfc9fa95785af5e493a38bf713e0023161dbd08de867f5721ea8370061e0e`): the active
  ATM programme (sales agreement with TD Securities (USA) LLC entered into on December 15, 2023, with sales
  through March 31, 2026 as stated);
- `registered_direct` (span sha256 `430ab359321d61548982d0a722b0c2d15562f67c0fcca956cd7a9b3eb2ec9413`): the
  concurrent registered direct offering to directors and officers (securities purchase agreement dated
  May 18, 2026), whose own 424B5 `0001104659-26-063933` was filed the same day under the same registration
  statement — the registered direct takedown inside the trailing 12 months.

Per SPEC §3.1 the expected answer computed from the two operand spans is **sealed out of the repository**
(`~/lanes/sealed/cs-v2-g0-held-out.json`, written before any G0-E work) and is NOT recorded here, in the pack, or
in any commit. The pack's held-out gold entry carries the identity, the source packet, the path id and the span
digests only. (An earlier tool pass had accepted this same candidate on mis-split sentence boundaries — the float
figure cut at a decimal point and the Baby-Shelf Limitation definition sentence read as the sales statement; the
corrected walk re-derived every verdict from cache, and the seal was written only after the corrected extraction.)

| # | CIK | accession | filing date | ticker | first failed criterion / result |
|---|---|---|---|---|---|
| 1 | 0000041091 | 0000041091-26-000002 | 2026-05-19 | GPJA | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 2 | 0000092487 | 0000092487-26-000021 | 2026-09-14 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=True |
| 3 | 0000720500 | 0000720500-26-000005 | 2026-06-01 | ASYS | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 4 | 0001731388 | 0000919574-26-006294 | 2026-09-11 | EDRY | c1_nasdaq_domestic_s3_issuer — exchanges=['Nasdaq'] domestic=False s3_family=False |
| 5 | 0001370238 | 0000929638-26-001790 | 2026-05-11 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=True |
| 6 | 0001654238 | 0000929638-26-001948 | 2026-05-21 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=False |
| 7 | 0002150254 | 0000929638-26-003269 | 2026-08-28 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=False |
| 8 | 0001844964 | 0000929638-26-003567 | 2026-09-17 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=False |
| 9 | 0002153325 | 0000929638-26-003875 | 2026-10-09 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=False s3_family=False |
| 10 | 0002099542 | 0000929638-26-003906 | 2026-10-14 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=False s3_family=False |
| 11 | 0001818644 | 0000947871-26-000869 | 2026-09-15 | LIDR | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 12 | 0001969373 | 0000950103-26-006920 | 2026-05-07 | VTMX | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=False s3_family=False |
| 13 | 0001920406 | 0000950103-26-008610 | 2026-06-05 | ASST | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 14 | 0000845982 | 0000950103-26-013643 | 2026-09-08 | SNN | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE', 'OTC'] domestic=False s3_family=False |
| 15 | 0001000275 | 0000950103-26-013664 | 2026-09-08 | RY | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE', 'OTC'] domestic=False s3_family=False |
| 16 | 0000844150 | 0000950103-26-015478 | 2026-10-13 | NWG | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE', 'OTC'] domestic=False s3_family=False |
| 17 | 0000033745 | 0000950157-26-000605 | 2026-05-13 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=False |
| 18 | 0001004155 | 0001004155-26-000008 | 2026-05-20 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=True |
| 19 | 0001130891 | 0001004155-26-000018 | 2026-09-09 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=True |
| 20 | 0001385849 | 0001062993-26-005309 | 2026-10-13 | UUUU | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=False s3_family=True |
| 21 | 0001976908 | 0001104659-26-056023 | 2026-05-06 | JDZG | c1_nasdaq_domestic_s3_issuer — exchanges=['Nasdaq'] domestic=False s3_family=False |
| 22 | 0001279704 | 0001104659-26-056031 | 2026-05-06 | CLRB | c2_atm_and_registered_direct_trailing_12m — float+sales stated but trailing-12m 424B filings show atm=0001104659-26-056031 registered_direct=None |
| 23 | 0001682639 | 0001104659-26-056233 | 2026-05-06 | HYPD | c2_atm_and_registered_direct_trailing_12m — float+sales stated but trailing-12m 424B filings show atm=0001104659-26-056233 registered_direct=None |
| 24 | 0001016281 | 0001104659-26-056241 | 2026-05-06 | CSV | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 25 | 0001534120 | 0001104659-26-056481 | 2026-05-07 | AVTX | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 26 | 0000820313 | 0001104659-26-056548 | 2026-05-07 | APH | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 27 | 0000890975 | 0001104659-26-056932 | 2026-05-07 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=False |
| 28 | 0001083199 | 0001104659-26-057001 | 2026-05-07 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=False |
| 29 | 0001888886 | 0001104659-26-057160 | 2026-05-07 | GPCR | c1_nasdaq_domestic_s3_issuer — exchanges=['Nasdaq'] domestic=False s3_family=True |
| 30 | 0000726728 | 0001104659-26-057437 | 2026-05-08 | O | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 31 | 0000004977 | 0001104659-26-058317 | 2026-05-11 | AFL | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 32 | 0001601548 | 0001104659-26-058322 | 2026-05-11 | VVX | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 33 | 0001868279 | 0001104659-26-058700 | 2026-05-11 | AVBP | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 34 | 0001821769 | 0001104659-26-058727 | 2026-05-11 | NVTS | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 35 | 0001679049 | 0001104659-26-058743 | 2026-05-11 | INSW | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 36 | 0001659166 | 0001104659-26-059059 | 2026-05-12 | FTV | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 37 | 0001243429 | 0001104659-26-059170 | 2026-05-12 | MT | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE', 'OTC', 'OTC'] domestic=False s3_family=False |
| 38 | 0000013372 | 0001104659-26-059414 | 2026-05-12 | NSARO | c1_nasdaq_domestic_s3_issuer — exchanges=['OTC', 'OTC'] domestic=True s3_family=True |
| 39 | 0000748268 | 0001104659-26-059502 | 2026-05-12 | RCAT | c1_nasdaq_domestic_s3_issuer — exchanges=['Nasdaq'] domestic=False s3_family=True |
| 40 | 0000811156 | 0001104659-26-060315 | 2026-05-13 | CMS | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE', 'NYSE', 'NYSE', 'NYSE', 'NYSE'] domestic=True s3_family=True |
| 41 | 0001649989 | 0001104659-26-060374 | 2026-05-13 | OTLK | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 42 | 0001849056 | 0001104659-26-060387 | 2026-05-13 | OKLO | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 43 | 0000882095 | 0001104659-26-060745 | 2026-05-14 | GILD | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 44 | 0001158114 | 0001104659-26-061146 | 2026-05-14 | AAOI | c3_supplement_states_float_and_ib6_sales — the supplement never references Instruction I.B.6 |
| 45 | 0001630805 | 0001104659-26-061195 | 2026-05-14 | BW | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE', 'NYSE'] domestic=True s3_family=True |
| 46 | 0001824502 | 0001104659-26-061198 | 2026-05-14 | ACHR | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=False s3_family=True |
| 47 | 0000821533 | 0001104659-26-061971 | 2026-05-15 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=False s3_family=False |
| 48 | 0001472246 | 0001104659-26-062016 | 2026-05-15 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=False s3_family=False |
| 49 | 0000740260 | 0001104659-26-062741 | 2026-05-15 | VTR | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 50 | 0001130310 | 0001104659-26-062746 | 2026-05-15 | CNP | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 51 | 0001379006 | 0001104659-26-063050 | 2026-05-18 | NNVC | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 52 | 0001679198 | 0001104659-26-063441 | 2026-05-19 |  | c1_nasdaq_domestic_s3_issuer — exchanges=[] domestic=True s3_family=False |
| 53 | 0001130464 | 0001104659-26-063508 | 2026-05-19 | BKH | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 54 | 0000031462 | 0001104659-26-063558 | 2026-05-19 | ECL | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=True s3_family=True |
| 55 | 0000930236 | 0001104659-26-063617 | 2026-05-19 | RWT | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE', 'NYSE', 'NYSE', 'NYSE', 'NYSE', 'NYSE', 'NYSE'] domestic=True s3_family=True |
| 56 | 0001766368 | 0001104659-26-063824 | 2026-05-19 | MEC | c1_nasdaq_domestic_s3_issuer — exchanges=['NYSE'] domestic=False s3_family=True |
| 57 | 0001380106 | 0001104659-26-063928 | 2026-05-19 | RPID | PASS |

## Requalification of the six archetypes (2026-10-19)

- company_tickers.json re-fetched: AIR, CLNN, WHK, LPTH, EDBL names unchanged; **QNCX (CIK 0001662774) renamed to
  IRulya Therapeutics Inc.** (formerNames: Quince Therapeutics, Inc. to 2026-10-09; primary ticker now IRLA,
  QNCX retained). Recorded as label drift on the QNCX identity with the former name kept as a historical witness;
  EDRY and RPID verified present with matching titles.
- Submissions indices re-fetched for all six archetypes: in-policy anchors re-derived (AIR S-3ASR 2026-07-22,
  CLNN S-3 2025-09-05 / S-3/A 2023-09-29, QNCX S-3 2026-07-31 / S-3/A 2026-08-05 / S-3ASR 2020-06-01, LPTH S-3
  2025-11-21 / S-3/A 2025-12-05, EDBL S-3 2026-07-31 / S-3/A 2025-01-28 — all unchanged from E0; WHK remains
  unsupplied). New receipts recorded per source; E0 receipts retained (append-only).
- C&DI Securities Act Forms page re-fetched: the page's edition label now reads October 15, 2026 (was
  September 25, 2026) but all six question spans 116.21–116.26 re-extract word-for-word identical with the same
  per-span sha256, so the qualified edition of the spans is unchanged and edition_date 2026-09-25 is kept.
- The March 19, 2026 C&DI update page URL now returns HTTP 404 (soft not-found page). The E0 edition receipt is
  retained as the witness for the 2026-03-19 interpretation date; the same date is witnessed by the span 116.26
  bracket "[March 19, 2026]" on the main C&DI page (verified identical in this requalification).
- Release 33-11418 still Proposed (S7-2026-17); the 2026 rulemaking index still lists it as a Proposed Rule; the
  fair-access page still states 10 requests per second with a declared user agent.
- Nasdaq rulebook: rendered by the seat in a browser on 2026-10-19 (a non-browser GET returns 403; no fetch made
  in this lane). Page text changed since E0 (150607 -> 150424 chars) but the Rule 5635 section is byte-identical
  (45650 chars, sha256 25c790344f44c97acedca33ac085c5ffae077172479d9db0c9208106d01d2030); the new rendered receipt
  (page sha256 adbee39938f63d9e7680d067398cabf1f1304845679746d0600fb68da7b465c3) is recorded on the source with
  the E0 receipt kept beside it, and edition_date stays 2020-01-15. All five 5635 span digests are unchanged and
  still match the L0 pack's pinned_spans.
- Gold fixtures re-hashed: `verify_gold_fixtures` reports no mismatch — every E0 fixture hash is unchanged, so no
  gold change and no expectation update is owed. The two new G0 gold fixtures are new witnesses, not changes.

## Request ledger

- `request_policy.requests_made` = 297; failed requests = 1.
- User agent (verbatim, every request): `MastermindMarketIntelligence-ResearchSeat/1.0 (+https://www.mastermind-x.com)`.
- Pacing: at least 1.05 s between request starts; hosts limited to data.sec.gov and www.sec.gov.
- First request: 2026-10-19T07:47:33Z https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/securities-act-forms -> HTTP 200.
- Last request: 2026-10-19T08:15:23Z https://www.sec.gov/Archives/edgar/data/1682639/000110465925065877/tm2519916d1_424b5.htm -> HTTP 200.
- The one failure: request #2 2026-10-19T07:47:34Z https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/corporation-finance-interpretations-march-19-2026-update
  -> HTTP 404 (the March 2026 C&DI update page is no longer served; recorded on the source receipt).
