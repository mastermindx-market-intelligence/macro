# B4 — routing verdicts for the 40 gated_v3 cases that are NEW vs gated_v2

Census-classed by Fabric lane NEWS-ORCH3-ROUTE (glm-5.3), run news-orch3-route-r2, 2026-10-31, under seat 602cd180. The cards were built with the `results_w2/tools/build_v2_routing.py` card logic over the r3 gated_v3 bodies; classes are the existing v2 routing taxonomy verbatim; `authority: context_only`.

## Strict separation

600 registration cases / gated_v2 99 drawn of which 74 routed MATCH (scorable) / gated_v3 135 drawn / 40 NEW cases routing-pending / 0 prospective. The 135 drawn are not 135 scored or gold cases. A shared group id does not transfer a label, a verdict or independence across versions, assets, clocks or horizons. Cluster/group ids are never evidence of independence.

## Taxonomy and rule

- **MATCH** — The headline reports an event of the routed template family at the resolved issuer, and at least one attached filing reports that event.
- **NO_EVENT** — The headline reports no issuer event of the template family (market report, commentary, list, quote page, solicitation).
- **OTHER_EVENT** — The headline event is real and the resolved issuer is its subject, but no attached filing reports it.
- **WRONG_ISSUER** — The resolved issuer is not the subject of the headline.

Rule (verbatim from the v2 routing decision): A case already in gated_v2 keeps its routing verdict and grade. A case new to gated_v3 needs a routing verdict from a census card before it scores, and only MATCH scores. Every scored case keeps its own routing verdict and only MATCH scores. The seat's commission also named MATCH/NO_MATCH/AMBIGUOUS/NEEDS_BODY; that is not this taxonomy and is not used here. `kind` reuses the v2 vocabulary printed from `sorted(set(kind))` across `results_w2/audit/{routing_verdicts,gate_verdicts,gates2_verdicts,paired_verdicts,v2_routing_verdicts}.json` (`"", commentary, common_word_ticker, event_filing_absent, graded_body_lacks_report, listicle, market_report, name_collision_private, other_company_subject, partner_named, private_subject, quote_page, single_letter_ticker, solicitation, template_family_mismatch`); kind `""` is the v2 MATCH convention. No new kind was minted (`new_kind: false` on every case).

## Counts

| class | cases |
|---|---|
| MATCH | 31 |
| NO_EVENT | 4 |
| OTHER_EVENT | 3 |
| WRONG_ISSUER | 2 |
| UNREADABLE_CARD | 0 |

| template | MATCH | NO_EVENT | OTHER_EVENT | WRONG_ISSUER | total |
|---|---|---|---|---|---|
| T1 | 20 | 3 | 0 | 0 | 23 |
| T2 | 6 | 1 | 1 | 2 | 10 |
| T3 | 5 | 0 | 2 | 0 | 7 |

Reconciliation: `40 = 31 MATCH + 4 NO_EVENT + 3 OTHER_EVENT + 2 WRONG_ISSUER + 0 UNREADABLE_CARD` — n_new 40 = len(cases) 40 = sum(class_counts) 40 (+ unreadable 0); per template 23 + 10 + 7 = 40.

## Per-case table

| case_id | template | cell | fold | group | v2_overlap | class | kind | note |
|---|---|---|---|---|---|---|---|---|
| 00fbc0439f95b43f | T2 | negative | f1 | grp:d46757f8d0f91b14 | none | WRONG_ISSUER | other_company_subject | Guidance-hike headline about the parcel carrier; the resolved issuer appears only as the party whose delivery cutback drove the move. |
| 0bfe0de4daacf678 | T2 | positive | f2 | grp:81845d680f0306c7 | none | MATCH | — | Results headline with a raised profitability outlook; the attached results release reports both. |
| 0cb9995f45d1263b | T3 | positive | f4 | grp:642f98192d4eb76a | none | MATCH | — | Proposed-combination platform headline; the attached filing furnishes the same term-sheet announcement. |
| 0dd90619c05a78c1 | T1 | positive | f4 | grp:c35ca0490b786f5b | none | MATCH | — | Preferred-stock offering headline; the attached filing reports the announced offering. |
| 0e10bbddc088fe56 | T1 | ambiguous | f5 | grp:647a932dede73007 | none | NO_EVENT | commentary | Steadiness question piece on dividend stalwarts; the headline reports no capital-return event, a routine declaration aside. |
| 127c769f84a9a105 | T1 | positive | f2 | grp:b469121080d8cf05 | none | MATCH | — | Registered-direct pricing headline; the attached filing reports the purchase agreement and the pricing. |
| 1f97c92013bda92b | T1 | negative | f2 | grp:2de8ad3535c5210b | none | NO_EVENT | commentary | Sector watch piece citing the issuer's earlier base-dividend reduction; the headline reports no new capital-return event. |
| 20d3fd3b4df231c4 | T1 | positive | f1 | grp:d48a21e38e64d9d1 | none | MATCH | — | Reverse-split headline; the attached filings report the split and its charter amendment. |
| 20d89273ab193880 | T1 | positive | f2 | grp:9dfe798882aaeb70 | none | MATCH | — | Private-placement pricing headline; the attached filing reports the purchase agreement and pricing. |
| 24f36f3187f6dda1 | T1 | positive | f3 | grp:5b31d9bf68893211 | none | MATCH | — | Reverse-split headline; the attached filing reports the split amendment and the same announcement. |
| 2efd29a51585bc8d | T1 | positive | f1 | grp:e839b9830898a883 | none | MATCH | — | Shareholder-approval headline on a deadline extension and redemption reversals; the same-session filings report the approval and charter amendment, a share-structure event at the capital family's borderline. |
| 42ac98edfe0d93b1 | T1 | positive | f5 | grp:a1d5f66bbd3f2adb | none | MATCH | — | Registered-direct pricing headline; the attached filing furnishes the same pricing release. |
| 42be09305ed34365 | T1 | positive | f4 | grp:e1805d45a92bafa0 | none | MATCH | — | Offering-pricing headline; an attached filing reports the underwriting agreement and the pricing release. |
| 4b22413b0bc8bd7c | T1 | positive | f3 | grp:cac9fbccbe81dbab | none | MATCH | — | Buyback-authorization headline; the attached filing reports the board authorization. |
| 4ebd7e5286323806 | T2 | positive | f2 | grp:a044e9e5fd944477 | same_group:ac46e1ff6b122b6c | MATCH | — | Earnings headline on cloud strength and steady capital-spending plans; the attached results filing reports the results event. |
| 4ec17f189d0724c3 | T2 | positive | f5 | grp:4f9542f9995aaec6 | none | WRONG_ISSUER | other_company_subject | The headline's outlook and robotics subject is the technology company known by that name; the resolved drilling issuer behind the symbol is not the subject. |
| 5519b8850c1df944 | T1 | positive | f5 | grp:15a61fa9f86c6b3c | none | MATCH | — | Buyback increase-and-extension headline; the same-session filing reports the expanded authorization. |
| 5b5e076f6f4c5c25 | T1 | positive | f3 | grp:55d5f366087a9c5f | none | MATCH | — | Placement-agent offering headline; the same-session filing reports the agency and purchase agreements for the offering. |
| 5dfe220924a401f5 | T3 | positive | f4 | grp:4def8a39218d53ac | none | OTHER_EVENT | event_filing_absent | Launch-mission headline; the attached filing reports acquisition-financing updates, not the mission. |
| 67e5571ab44a68af | T3 | negative | f3 | grp:d7eb86225e17825c | none | MATCH | — | Partnership-rally headline; the attached filing reports the multi-year data-center partnership with credit support announced in the same window. |
| 6e212636947aab91 | T2 | positive | f5 | grp:9aa3364e247f4a51 | none | MATCH | — | Results headline with a raised outlook; the attached release reports the results and the updated outlook. |
| 788a5b3081ccf72c | T2 | negative | f5 | grp:6929c586cc61f36f | none | MATCH | — | Guidance-reiteration headline alongside an executive change; the attached release reports the reaffirmed full-year guidance. |
| 79eab39d952b9aef | T3 | positive | f3 | grp:0723347bceceb56b | none | OTHER_EVENT | event_filing_absent | Technology-unveiling claim in a watch piece; the attached filings report results, merger steps and an equity program, not an unveiling. |
| 803084e99a2cbe60 | T1 | positive | f3 | grp:b134567794386ef7 | none | MATCH | — | Reverse-split headline; the attached filings report the split amendment and the same-titled release. |
| 853f5d2f9f43c3a6 | T2 | positive | f5 | grp:1990cef3f7833819 | none | MATCH | — | Backlog-addition headline from new and converted awards; an attached filing reports the same backlog announcement. |
| 9b1b6db61b46eb60 | T2 | positive | f2 | grp:2efc8697fa384b6a | none | OTHER_EVENT | event_filing_absent | Contract-award headline; the only attached filing is the quarterly results release, which reports records but not this award. |
| a251a893e10f4130 | T1 | positive | f3 | grp:601a231c339c21ab | none | MATCH | — | Reverse-split headline; an attached filing reports the split alongside the special-meeting vote. |
| a34346473b7ff19a | T1 | positive | f1 | grp:61d365785b2fcf05 | none | MATCH | — | Quarterly-dividend headline; the attached filing reports the declaration. |
| a81a872f1696d9c6 | T1 | positive | f2 | grp:09f695e8df59772f | none | NO_EVENT | commentary | Dividend-durability question piece; the headline reports no capital-return event though the attached release declares the regular dividend. |
| b1f8439867c811b6 | T1 | positive | f4 | grp:5a2dcc6190cfc62f | none | MATCH | — | Common-and-preferred dividend headline; the attached filing reports both declarations. |
| b6f83832faa0fee9 | T2 | positive | f1 | grp:beb48738e4bd3f99 | none | NO_EVENT | template_family_mismatch | Regulatory product-approval headline routed to the demand family; the attached filing reports the approval, a product milestone, not a demand or guidance event. |
| b8c881960abce66c | T1 | positive | f4 | grp:5a3714f7d156008a | none | MATCH | — | Reverse-split headline tied to a merger step; the attached filing furnishes the same corrected split release. |
| b9119cfb98ad0aa6 | T1 | positive | f3 | grp:c070745e126e88bc | same_group:bea9e4ca79450a7a | MATCH | — | Bond-sale headline; the attached filing reports the closed senior-notes offering. |
| bc29e5e48c80378a | T1 | positive | f2 | grp:4c6ab37f77127765 | none | MATCH | — | Reverse-split headline; the attached filing reports the split and furnishes the same release. |
| c5e8d851d7c5756a | T1 | positive | f4 | grp:70f05d17197195b2 | none | MATCH | — | Notes-offering launch headline; an attached filing reports the same offering's pricing. |
| c6690b067520bdfc | T2 | positive | f3 | grp:73fe9ebe6fe62bc3 | same_group:eff279aeb30a6267 | MATCH | — | First year-ahead outlook given with results; the attached results filing and commentary carry the results event. |
| d0ca522fc4b1e0b5 | T3 | positive | f5 | grp:ec7eb86b9730799b | none | MATCH | — | New business-line launch headline; the attached filing furnishes the same subsidiary-launch release. |
| d1eeb29c475402b4 | T3 | positive | f3 | grp:08cf2d3e95b71798 | none | MATCH | — | Regulatory-approval headline; the attached filing reports the same approval. |
| d9cc14d215da6b7a | T3 | positive | f4 | grp:de8dbf7cd3017456 | none | MATCH | — | Exclusive distribution agreement headline; the attached filing reports entering the agreement. |
| e464be3a287f284a | T1 | positive | f3 | grp:39add6e7a467d485 | none | MATCH | — | Proposed-offering headline; the attached filings report the underwriting agreement, pricing and closing. |

## Same-group cases

Exactly 3 of the 40 NEW cases share a group id with a gated_v2 case (CENSUS.md §7), as asserted in the build. A group id shares no label, verdict or independence across versions: the v2 member keeps its v2 verdict and grade, the NEW member keeps this routing verdict, and at most one scored case per group is allowed at scoring time.

- `4ebd7e5286323806` (T2, positive, f2) — group `grp:a044e9e5fd944477`, v2_overlap `same_group:ac46e1ff6b122b6c`, class **MATCH** (kind —).
  - issuer_same: True · template_same: True
  - seendate_v3: 2026-07-30T08:16:00Z · seendate_v2: 2026-07-29T23:22:47Z
  - window_v3: ['2026-07-29', '2026-07-30', '2026-08-05'] · window_v2: None (no v2 bodies file exists on this host; recorded null)
  - label_transfer: none — a group id shares no label, verdict or independence across versions
- `b9119cfb98ad0aa6` (T1, positive, f3) — group `grp:c070745e126e88bc`, v2_overlap `same_group:bea9e4ca79450a7a`, class **MATCH** (kind —).
  - issuer_same: True · template_same: True
  - seendate_v3: 2026-08-06T11:55:00Z · seendate_v2: 2026-08-07T18:11:51Z
  - window_v3: ['2026-08-05', '2026-08-06', '2026-08-12'] · window_v2: None (no v2 bodies file exists on this host; recorded null)
  - label_transfer: none — a group id shares no label, verdict or independence across versions
- `c6690b067520bdfc` (T2, positive, f3) — group `grp:73fe9ebe6fe62bc3`, v2_overlap `same_group:eff279aeb30a6267`, class **MATCH** (kind —).
  - issuer_same: True · template_same: True
  - seendate_v3: 2026-08-27T00:39:00Z · seendate_v2: 2026-08-27T20:36:00Z
  - window_v3: ['2026-08-25', '2026-08-26', '2026-09-01'] · window_v2: None (no v2 bodies file exists on this host; recorded null)
  - label_transfer: none — a group id shares no label, verdict or independence across versions

## What this is not

- Not gold labels: these are routing verdicts under `authority: context_only`, produced by one census auditor classing one card per case.
- Not scored: nothing here grades a case, and a non-MATCH verdict removes nothing from gated_v3 — the draw is the draw; the verdict only records whether a card shows the routed event at the resolved issuer reported by an attached filing.
- Not a redraw: no case was added, dropped or reselected; the 40 NEW ids are exactly `gated_v3/cases.jsonl` minus `gated_v2/cases.jsonl`.
- Not independence: a shared group id (the 3 same-group cases above) transfers no label, verdict or independence across versions, assets, clocks or horizons.
- Only a MATCH case may later enter the labeling queue, through the existing section-11 process; at most one scored case per group.

## Evidence

- gated_v3 source: `git fetch origin 01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2` (PR #10063 head), read with `git show FETCH_HEAD:research/prophet_v4/news_to_business_impact_20261006/benchmark/gated_v3/cases.jsonl` (135 rows) and `.../gated_v3/CENSUS.md` (§6: both 95 / NEW 40 / dropped 4, NEW per template T1 23, T2 10, T3 7; §7: the 3 shared groups).
- gated_v2 source: `research/prophet_v4/news_to_business_impact_20261006/benchmark/gated_v2/cases.jsonl` at lane head (99 rows). ids_v3 135, ids_v2 99, NEW 40, BOTH 95, DROPPED 4 — asserted in code.
- Bodies (read-only lane dir R3): `/home/ubuntu3/lanes/tmp/ne-b4-gated-v3-20261022-r3/bodies_v3/bodies.jsonl`, sha256 `59bbeb2251d4e1577003d2eb118672592651b6428904256b098039a04b98c86c` (verified); texts under `.../bodies_v3/texts/`; candidates `.../candidates_all.jsonl` (2,837 rows; all 40 NEW ids present, body status `available`).
- Cards: `$W/cards.py` copies the `cards()` logic of `results_w2/tools/build_v2_routing.py` (helpers `jl`, `clean`, `ITEM_CHARS`, `EX_CHARS` from `results_w2/tools/build_gate_validation.py`), adapted to R3 inputs, order = sorted NEW ids, graded = none (mark `-`); `PYTHONPATH=.:results_w2/tools python3 cards.py > cards.txt` -> 40 `=== R` headers, 0 missing rows. Cards are scratch-only and never committed.
- Classing: cards read in chunks of 10; every verdict applies the four definitions verbatim and the v2 rule "every scored case keeps its own routing verdict and only MATCH scores"; calibration precedents used exactly as the v2 census auditor ruled them (reverse split reported in the attached filing -> MATCH; a filing-reported event outside the routed family -> NO_EVENT/template_family_mismatch; dividend question and watch pieces -> NO_EVENT/commentary; a results release that lacks the headline event -> OTHER_EVENT/event_filing_absent; headline about another company -> WRONG_ISSUER/other_company_subject).
- Verdicts artifact: `$W/verdicts.jsonl` (40 lines) -> `research/news_intelligence_estate_20261021/b4_v3_new_case_routing.json` (schema `news-estate.b4-v3-new-case-routing.v1`; no headline text, no filing text, no URLs).
- Lane: worktree at `/home/ubuntu3/lanes/wt/news-orch3-route-r2` on branch `lane/news-orch3-route-r2`, base `6135e2c3c64cd62258f176b234c6bb27960e3adb`; both owned files committed there; scratch under `/home/ubuntu3/lanes/tmp/news-orch3-route-r2/`.
