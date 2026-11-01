# Independent source review of pivotal guidance packets

Review date: 2026-10-21. Scope: `guidance_packets.json` and `GUIDANCE_PILOT.md`, with independent primary-source checks of Microsoft July/October 2022, Caterpillar October 2022, and Duke Energy November 2022. This is a source-based review of existing provisional labels, not a second blinded annotation or a review of all 12 events. No market prices, returns, charts, or study outcomes were inspected.

## Disposition

**ACCEPT the four focal release-body classifications, with the two clarifications below.** No checked source establishes a comparable aggregate remaining-period operating revision in those release bodies. This is a finding about the specified information stage, not absence of forward information from the issuer. The Microsoft call context contains explicit forward changes and must remain separate.

Root accepted the clarifications before this review was saved and owns the packet edits. This review did not modify the packets or report.

## Accepted source findings

### Microsoft — July 26, 2022

The [FY22 Q4 release](https://www.microsoft.com/en-us/investor/earnings/fy-2022-q4/press-release-webcast), “Business Outlook,” defers guidance to the call; its annual results are completed FY2022 actuals. Its adverse-quarter bridge uses the April guidance baseline. The [June 2 SEC exhibit](https://www.sec.gov/Archives/edgar/data/789019/000119312522165839/d295016dex991.htm), slide 3, concerns FY22 Q4 FX, not FY2023; starred totals are issuer-calculated and rounding is expressly qualified.

The [April call](https://www.microsoft.com/en-us/investor/events/fy-2022/earnings-fy-2022-q3), CFO closing outlook, supplies earlier FY2023 double-digit revenue/operating-income commentary. The [July call](https://www.microsoft.com/en-us/investor/events/FY-2022/earnings-fy-2022-q4), CFO full-year outlook, reiterates double-digit growth in USD and constant currency, but includes a depreciation-estimate benefit of approximately $3.7 billion for FY2023 and $1.1 billion for Q1. The four-to-six-year life extension specifically covers server/network equipment in cloud infrastructure. Roughly flat USD margin therefore does not establish unchanged underlying operating assumptions. The packet's accounting/basis qualification is supported.

### Microsoft — October 25, 2022

The [FY23 Q1 release](https://www.microsoft.com/en-us/investor/earnings/fy-2023-q1/press-release-webcast), “Business Outlook,” again defers guidance. Its removal of the prior-year intangible-property tax benefit adjusts the historical earnings comparison; it is not a forward revision.

The [October call](https://www.microsoft.com/en-us/investor/events/fy-2023/earnings-fy-2023-q1), CFO full-year outlook, supports the mixed-driver label: USD operating margin is expected down approximately one percentage point year on year; constant-currency double-digit growth is reiterated. Management explicitly lowers expected remaining-year Windows OEM revenue. Its conditional flat constant-currency margin statement adds a lower-OEM exclusion to the depreciation exclusion, so it is not a like-for-like unchanged-margin assertion. A single aggregate remaining-period profit revision is not quantified.

**Clarification accepted by root:** in the same call's Mark Murphy energy-cost Q&A, management places some of the greater-than-$800-million annual energy-cost increment in Q1, most in Q2–Q4, and approximates the remaining quarterly increment at $250 million. Preserve that timing in later-call context. It does not make the entire annual margin change a future demand change or make the whole energy increment prospective.

### Caterpillar — October 27, 2022

The [Q2 SEC release](https://www.sec.gov/Archives/edgar/data/18230/000001823022000178/ex991toformcat2q2022earnin.htm) and [Q3 SEC release](https://www.sec.gov/Archives/edgar/data/18230/000001823022000216/ex991toformcat3q2022earnin.htm), each “Other Profit/Loss and Tax Items,” support a current-year estimated annual global tax rate moving from approximately 24% to 23%. Q3 records a $20 million tax benefit from the estimate decrease, separately from the $41 million discrete IRS-settlement tax benefit. These are distinct from a remaining-period operating outlook; no comparable annual operating range was located in the inspected release.

**Clarification accepted by root:** replace the ambiguous JSON `annual_headline: not_stated_in_inspected_release` with `annual_operating_outlook_not_stated_in_inspected_release`. The annual tax estimate is explicitly stated. This aligns the JSON with the report and leaves the unresolved operating-revision classification intact. Do not recast the $20 million recognized benefit as a separately stated future-quarter profit forecast.

### Duke Energy — November 4, 2022

The [August release](https://www.sec.gov/Archives/edgar/data/1326160/000132616022000244/er-20220630xearningsreleas.htm) reaffirms FY2022 adjusted EPS of $5.30–$5.60. The [November release](https://www.sec.gov/Archives/edgar/data/1326160/000132616022000277/er-20220930xearningsreleas.htm), opening guidance bullets, gives $5.20–$5.30 excluding Commercial Renewables. A lower/narrower raw range is observable, but a same-scope Q4 operating revision is not established by subtracting completed EPS. The $5.55–$5.75 FY2023 initiation is a different target year.

The November release's reconciliation footnote attributes the $1.81 reported versus $1.78 adjusted Q3 EPS difference to a tax-liability reduction involving the International Disposal Group. This is separate from prospective removal of Commercial Renewables. The packet correctly keeps the scope change and historical tax adjustment distinct.

## Timing and source-unknown qualifications

- [Caterpillar's October SEC filing index](https://www.sec.gov/Archives/edgar/data/18230/000001823022000216/0000018230-22-000216-index.htm) confirms the raw acceptance value `2022-10-27 06:30:50`. The displayed page does not state a timezone. This is an SEC acceptance observation, not verified earliest issuer dissemination.
- [Duke's advance notice](https://news.duke-energy.com/releases/duke-energy-to-announce-third-quarter-2022-financial-results-on-nov-4) schedules the November release for 07:00 ET and the call for 09:00 ET. Intended timing does not establish actual first publication.
- Microsoft's checked release pages schedule calls for 14:30 Pacific/17:30 Eastern. The call transcripts describe planned posting of prepared remarks after the call, but neither that plan nor a call start time proves exact statement or transcript-publication time. Preserve unknown timestamps and no intraday-execution qualification.
- [Microsoft's January availability notice](https://news.microsoft.com/source/2022/01/25/microsoft-earnings-press-release-available-on-investor-relations-website-13/) explicitly acknowledges an update to that notice's text/link. This supports version caution; it does not by itself prove that the underlying earnings release was revised. Current issuer pages do not independently establish unchanged original versions.
- This bounded review did not complete the intervening-disclosure census or independently resolve January transcript retrieval gaps. Retrieval failure is not proof that a source did not exist. Four focal packets checked here do not constitute independent verification of every event or an inter-rater agreement study.

## Reviewed input versions

SHA-256 before root's accepted packet clarifications:

- `guidance_packets.json`: `ad6d4d5cc4052ea88a4b8358d825ddc9b06495b66a4980307f538583dcfafc7c`
- `GUIDANCE_PILOT.md`: `d8f6f9249107f193d310da8e4a9e9e9f0e0205c4fb67a6d81f5e20252fd07900`

All URLs above were reopened during this review on 2026-10-21. Sources are issuer documents or issuer material filed with the SEC. The review supports the measurement distinctions and explicit unknowns; it supplies no predictive-performance qualification or trading authorization.
