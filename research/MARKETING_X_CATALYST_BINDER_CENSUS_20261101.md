# Marketing X Catalyst — figure-binding failure census (2026-11-01)

Follow-up "g" of the Catalyst A3 live SEC source (#10379): raise the yield of
`engine/earnings_release/figures.py` and make a silent parser break visible.
This page is the census that scopes the binder changes. Every change in the
same PR answers a failure class named here, and each class has its own test.

## Method

- **Universe.** The 20 issuers in the pilot universe. For each one, the two
  latest 8-K filings carrying Item 2.02, with the EX-99.1 exhibit from each:
  40 releases in all.
- **Binding.** Each exhibit was fetched from the SEC archive and bound in
  memory with `bind_release_document`. **D4 holds:** no SEC document bytes
  were written anywhere. The census output keeps only the sha256 of the
  exhibit, its archive URL, block and table counts, bound concept names and
  absence-reason counts. The output is scratch and is not committed.
- **Before vs after.** The same 40 exhibits were bound with the binder at the
  base (`0b441ec2523f`) and with this branch. The sha256 and URL of every
  exhibit match between the two runs, so the before/after difference comes
  from the binder alone. The table below records those hashes.
- **Re-run after the second review.** The final re-run (2026-11-01, after the
  N1–N8 fixes) received every one of the 40 exhibits 2 bytes longer than the
  eight earlier runs, each now ending in `</DOCUMENT>\n`. The census script
  was unchanged, so the bytes changed on the SEC side. The URLs are the same,
  and the bound figures, statuses and projections are identical on all 40.
- **Projection.** A projected figure is what the Catalyst cycle
  (`project_release_figures`) would carry to a public card. Only
  `eps_actual` (GAAP diluted EPS) and `rev_actual` (reported revenue) are
  projected, and both must replay against the exact bytes.

## Totals

| Measure (40 releases) | Base | This branch |
|---|---:|---:|
| `parsed` (≥ 1 projected figure) | 10 | **31** |
| Releases with ≥ 1 bound figure | 13 | 32 |
| Bound figures (all concepts and bases) | 60 | 208 |
| Projected public figures | 14 | 54 |
| — `eps_actual` | 8 | 29 |
| — `rev_actual` | 6 | 25 |

These are the final run, after classes T and K and the review hardening
below. No figure bound at the base is lost or changes value on this branch. Values
gained were checked against their own statements. For example, KO revenue in
each release reads from that release's income statement, with the
prior-year comparative bound to its own period end.

## Per release

"Before" and "After" give the cycle status, the number of bound figures, and
the projected public concepts. Class tags name the failure classes below that
the release exhibited. "residual" means it is still unparsed; see
[Residuals](#residuals).

| Ticker | Accession | Filed | EX-99.1 sha256 | Before | After | Class |
|---|---|---|---|---|---|---|
| AAPL | [0000320193-26-000018](https://www.sec.gov/Archives/edgar/data/320193/000032019326000018/a8-kex991q3202606272026.htm) | 2026-07-30 | `ed1ab52e06f6fdccc362870ae4004cdd6a28d9db03b65832cd2cf0d52ad6e53a` | parsed 12/eps+rev | parsed 13/eps+rev | S |
| AAPL | [0000320193-26-000011](https://www.sec.gov/Archives/edgar/data/320193/000032019326000011/a8-kex991q2202603282026.htm) | 2026-04-30 | `3a2116c1a23059ae7d5ecc22fd888c57777d2eec3b19c111c663ab67d330f9a7` | parsed 12/eps+rev | parsed 13/eps+rev | S |
| MSFT | [0001193125-26-436122](https://www.sec.gov/Archives/edgar/data/789019/000119312526436122/msft-ex99_1.htm) | 2026-10-28 | `b83db6a9a1837f23f37a39055b140ef147cd59469096937c671f242b375df9cd` | no_figures 0/— | parsed 6/eps+rev | A·E·G·T |
| MSFT | [0001193125-26-323632](https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/msft-ex99_1.htm) | 2026-07-29 | `42fe73a927cacb3e91f973640fb7defeff8945995486411cd9d2eddce5e07b22` | no_figures 0/— | parsed 6/eps+rev | A·E·G·S |
| AMZN | [0001018724-26-000038](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000038/amzn-20260930xex991.htm) | 2026-10-29 | `10c8c00a2d6199b091f0a86731f4da049d4f0c1ce358520787310421bd8ffc45` | no_figures 0/— | parsed 6/eps+rev | A·T |
| AMZN | [0001018724-26-000024](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000024/amzn-20260630xex991.htm) | 2026-07-30 | `a7dc40594ed93298068d4e149834f88aac743c10290aab17d8366a5991ad3ce0` | no_figures 0/— | parsed 6/eps+rev | A·T |
| GOOGL | [0001652044-26-000080](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000080/googexhibit991q32026.htm) | 2026-10-28 | `02f6caf32710c39c5d8d27474b49652da859c9c294cf33aae96b96e1b376b01c` | no_figures 0/— | parsed 7/eps+rev | A·B |
| GOOGL | [0001652044-26-000066](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000066/googexhibit991q22026.htm) | 2026-07-22 | `f40b58327d6404344f1346b2874b5f843e4ee8b0df613962ae044b177452fbd6` | no_figures 0/— | parsed 7/eps+rev | A·B |
| META | [0001628280-26-066700](https://www.sec.gov/Archives/edgar/data/1326801/000162828026066700/meta-09302026xexhibit991.htm) | 2026-10-21 | `b894b80a76556b64a3ea4351ddaeb0b8da7b52c1aed3f94d2b67f851ad5e1377` | no_figures 0/— | parsed 9/eps+rev | A·B |
| META | [0001628280-26-050596](https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/meta-06302026xexhibit991.htm) | 2026-07-29 | `e57cf08176a3b3f1e344d0f92ba15eb68f17d2b40c0f8ae6612d3e205451abd2` | no_figures 0/— | parsed 9/eps+rev | A·B |
| NVDA | [0001045810-26-000073](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/q2fy27pr.htm) | 2026-08-26 | `28efd0e3376762fb982d949700d039f7ec4cd54331a8244965a751e9956146ac` | no_figures 0/— | parsed 7/eps+rev | A·C |
| NVDA | [0001045810-26-000051](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000051/q1fy27pr.htm) | 2026-05-20 | `47db53e66161a3df68cec6c3a62d0bb18f414d97b278a366bfbe51c9c639c1f7` | no_figures 0/— | parsed 7/eps+rev | A·C |
| TSLA | [0001628280-26-066738](https://www.sec.gov/Archives/edgar/data/1318605/000162828026066738/exhibit9914.htm) | 2026-10-21 | `f22b4acc1e21a6b253792c501382d147ad663cce3d5a38fdfb176c453dfd018e` | no_figures 0/— | no_figures 0/— | F (residual) |
| TSLA | [0001628280-26-064366](https://www.sec.gov/Archives/edgar/data/1318605/000162828026064366/exhibit991111111.htm) | 2026-10-02 | `6c7b09b30653556b2922c0b8cd70f54db312e4a723ed8b8d1554c8b5b1ec64bd` | no_figures 0/— | no_figures 0/— | F (residual) |
| JPM | [0001628280-26-065582](https://www.sec.gov/Archives/edgar/data/19617/000162828026065582/a3q26erfexhibit991narrative.htm) | 2026-10-13 | `ce9882d22a25eba945e2c50142b333a39931278ebb72efdf39f9d11d035e3852` | no_figures 0/— | no_figures 0/— | residual |
| JPM | [0001628280-26-048078](https://www.sec.gov/Archives/edgar/data/19617/000162828026048078/a2q26erfexhibit991narrative.htm) | 2026-07-14 | `1a591b869820d64f525ca855739bfc58309e5c57af6425c30548f4bddb09564b` | no_figures 0/— | no_figures 0/— | residual |
| V | [0001403161-26-000126](https://www.sec.gov/Archives/edgar/data/1403161/000140316126000126/q42026earningsrelease.htm) | 2026-10-27 | `0bdbb53f100572d19c118303a37fe213378d41386e1605777336bbed6b547217` | parsed 3/rev | parsed 7/eps+rev | A·S·K |
| V | [0001403161-26-000103](https://www.sec.gov/Archives/edgar/data/1403161/000140316126000103/q32026earningsrelease.htm) | 2026-07-28 | `4feb24dd5d42e6c09ac6ac3a7f7e443405adcf27be8760346dcd08091a28d595` | parsed 3/rev | parsed 7/eps+rev | A·S·K |
| MA | [0001141391-26-000122](https://www.sec.gov/Archives/edgar/data/1141391/000114139126000122/ma09302026-exx991xearnings.htm) | 2026-10-29 | `c4ec0c55be46aa0d4607ae05a42d5cbdfe0e2d041568a1fe754866bdfb183b86` | no_figures 0/— | parsed 7/eps+rev | A·B·D·S |
| MA | [0001141391-26-000081](https://www.sec.gov/Archives/edgar/data/1141391/000114139126000081/ma06302026-exx991xearnings.htm) | 2026-07-30 | `8810370e1207f420e072c25441f3be468382a25a40bcb28751d66aac04d46f06` | no_figures 0/— | parsed 7/eps+rev | A·B·D·S |
| WMT | [0000104169-26-000145](https://www.sec.gov/Archives/edgar/data/104169/000010416926000145/earningsreleasefy27q2.htm) | 2026-08-20 | `2cf3dce9ae9d4dd77bf317fa64c9db29076b13212a0b224e8598cc25f51a7957` | no_figures 0/— | parsed 5/eps | B·T |
| WMT | [0000104169-26-000095](https://www.sec.gov/Archives/edgar/data/104169/000010416926000095/earningsreleasefy27q1.htm) | 2026-05-21 | `65bfea1f87b0d4d1323595b45b4279d9617407d4e81138ad39784e1f9e58f88d` | no_figures 0/— | parsed 5/eps | B·T |
| JNJ | [0000200406-26-000189](https://www.sec.gov/Archives/edgar/data/200406/000020040626000189/a2026q3exhibit991.htm) | 2026-10-13 | `a11efa1b84180d094aa826d93c19c84b495911a31998ed5ce31ffd0672604b91` | no_figures 0/— | no_figures 0/— | residual |
| JNJ | [0000200406-26-000146](https://www.sec.gov/Archives/edgar/data/200406/000020040626000146/a2026q2exhibit991.htm) | 2026-07-15 | `9ba8856b1c3fd39e45401f51d3744a671546a3b171b865e8b18a497464a9f2ff` | no_figures 0/— | no_figures 0/— | residual |
| PG | [0000080424-26-000250](https://www.sec.gov/Archives/edgar/data/80424/000008042426000250/fy2627q1jas8-kexhibit991.htm) | 2026-10-22 | `c41023c49a80ae2a6eab99485cc7cb3708b88f2a3f7b8ac4f807fa0cb9a123ba` | no_figures 0/— | parsed 8/eps+rev | A·B·E |
| PG | [0000080424-26-000093](https://www.sec.gov/Archives/edgar/data/80424/000008042426000093/fy2526q4amj8-kexhibit991.htm) | 2026-07-29 | `3836c42bb84e382bc1ca6833c32f1a7cfe03bad4f3f279d1149f79fa18129e55` | no_figures 0/— | no_figures 0/— | residual |
| HD | [0000354950-26-000145](https://www.sec.gov/Archives/edgar/data/354950/000035495026000145/hd_exhibit991x08022026.htm) | 2026-08-18 | `389fb475bde328f8d93eaf81bd1111f1e6b300d1e7417464dd27583d5bf19ae8` | no_figures 0/— | parsed 6/eps+rev | A·E |
| HD | [0000354950-26-000101](https://www.sec.gov/Archives/edgar/data/354950/000035495026000101/hd_exhibit991x05032026.htm) | 2026-05-19 | `fce8a679403e383b0b812574574ca645151f54ebff6a9af1d40caa305a2b6e11` | no_figures 0/— | parsed 6/eps+rev | A·E |
| KO | [0001628280-26-067403](https://www.sec.gov/Archives/edgar/data/21344/000162828026067403/a2026q3earningsreleaseex-9.htm) | 2026-10-27 | `9a95dd6e0210e7a72959dea87aefd849c04487c0f6882115e608050d801bf309` | no_figures 1/— | parsed 6/eps+rev | D·S |
| KO | [0001628280-26-049922](https://www.sec.gov/Archives/edgar/data/21344/000162828026049922/a2026q2earningsreleaseex-9.htm) | 2026-07-28 | `96d5779f5ac95f30a0bc5b29a796ea97f3e509c810a14279436bf7d670fa1f6c` | no_figures 1/— | parsed 6/eps+rev | D·S |
| PEP | [0000077476-26-000050](https://www.sec.gov/Archives/edgar/data/77476/000007747626000050/q320268-kxexhibit991.htm) | 2026-10-08 | `a60f05cc8266151625c749e4b49da5296506718d31c23f4239e207199c8abd72` | no_figures 0/— | parsed 4/rev | A·D·S |
| PEP | [0000077476-26-000037](https://www.sec.gov/Archives/edgar/data/77476/000007747626000037/q220268-kxexhibit991.htm) | 2026-07-09 | `506293176df57d0d77c1816ba0ea608a6a37f0f17902d72211222eab927faf06` | no_figures 0/— | parsed 4/rev | A·D·S |
| COST | [0000909832-26-000084](https://www.sec.gov/Archives/edgar/data/909832/000090983226000084/costex9918-k92426.htm) | 2026-09-24 | `37c29701f614c20b5af2094509ce9e49a37d4495d7715fa1df32ba5322651a0a` | parsed 4/eps | parsed 5/eps | S |
| COST | [0000909832-26-000046](https://www.sec.gov/Archives/edgar/data/909832/000090983226000046/costex9918-k52826.htm) | 2026-05-28 | `a2bbab6fc1dbe2cfaa593a0f60d8678ba770147948d4267fea24b0e6c6dbcaca` | parsed 4/eps | parsed 5/eps | S |
| NFLX | [0001065280-26-000290](https://www.sec.gov/Archives/edgar/data/1065280/000106528026000290/ex991_q326.htm) | 2026-10-20 | `9da7eea667d9028d796e933a7c1595bc6760e7c23c91d6348e78ebcaf2bd2324` | parsed 7/eps+rev | parsed 8/eps+rev | — |
| NFLX | [0001065280-26-000211](https://www.sec.gov/Archives/edgar/data/1065280/000106528026000211/ex991_q226.htm) | 2026-07-16 | `efc30484b1480418bff085407b6b435f6e7b89ff4b4de15219ce46c7b2e05e94` | parsed 7/eps+rev | parsed 8/eps+rev | — |
| AMD | [0000002488-26-000121](https://www.sec.gov/Archives/edgar/data/2488/000000248826000121/q22026991.htm) | 2026-08-04 | `95cc308e90d0a37bcd12664e6b571799f794e66dbafab26dd8c56d41be43867a` | parsed 2/eps | parsed 3/eps | — |
| AMD | [0000002488-26-000072](https://www.sec.gov/Archives/edgar/data/2488/000000248826000072/q12026991.htm) | 2026-05-05 | `00784741ec1ecdc232c7385df1a517156b50888b3af5698950ab9343999fccac` | parsed 2/eps | parsed 3/eps | — |
| UNH | [0000731766-26-000255](https://www.sec.gov/Archives/edgar/data/731766/000073176626000255/earningsrelease3q26unh.htm) | 2026-10-13 | `c12181a7af1802279444740b374fb180d1f64d758feba92d96b74762008ab1e9` | no_figures 0/— | no_figures 0/— | F (residual) |
| UNH | [0000731766-26-000191](https://www.sec.gov/Archives/edgar/data/731766/000073176626000191/earningsrelease2q26_7152.htm) | 2026-07-16 | `ecb5e6632a79ff8a0a8d915a488737ac1e5cc9b06f2c57e0b8d2f684e199253b` | no_figures 2/— | no_figures 2/— | F (residual) |

## Failure classes

Every class is a layout the binder misread at the base. Each one names its
test in `tests/test_earnings_release_binding.py`. Each fix is scoped to the
shape the census found and refuses anything wider.

| Class | Failure at the base | Change | Test(s) |
|---|---|---|---|
| **A** — period headers | A dated column header was missed when it was typeset as (1) a year row under a "Three Months Ended" row, (2) a header whose date tail sits in its own cell, or (3) a slash date. The table bound no period columns. | Header reading recognises these three shapes and still names a single dated period per column. | `test_class_a_a_dated_header_in_any_census_shape_names_the_period` (year-row, date-tail, slash-date) |
| **B** — units captions | A caption led by a currency sign ("$ in millions") declared neither units nor currency, so every amount was refused as unitless. | A `$`-led caption declares both units and currency. | `test_class_b_a_dollar_led_units_caption_declares_units_and_currency` |
| **C** — value cells | A currency sign inside the value cell, or a negative typeset across two cells (an opening parenthesis in one cell and the number in the next), was not read as one value. | A currency in the cell is read as a currency. A split negative is joined into one value. | `test_class_c_a_currency_symbol_inside_the_value_cell_is_a_currency`, `test_class_c_a_negative_typeset_across_two_cells_reads_as_one_value` |
| **D** — label variants | Common statement labels did not name their roster concept, so the row was not a candidate. | The roster label patterns are widened to the census variants only. | `test_class_d_census_label_variants_name_their_concept` |
| **E** — basis scoping | A statement title did not declare GAAP. A basis named in prose kept governing later tables. A basis declared inside one table leaked to the next. | Statement titles declare GAAP. Prose that names a basis closes the section it follows. A basis declared inside a table governs that table only. | `test_class_e_census_statement_titles_declare_gaap`, `test_class_e_prose_mentioning_a_basis_closes_the_section_it_follows`, `test_class_e_a_basis_declared_inside_a_table_speaks_for_that_table_only`; regression guard `test_class_e_a_title_typeset_as_a_table_governs_like_a_caption` (the base already read a table-typeset title; the guard keeps class E from breaking it) |
| **G** — split columns | Two columns under one dated header read as two disagreeing values. Sometimes these are a reconciliation (as reported / adjusted); sometimes an amount and its percent change. | A reconciliation split of one period is **refused** (`value_ambiguous`), never guessed. An amount-and-percent split narrows to the amount. | `test_class_g_a_reconciliation_split_of_one_period_is_refused`, `test_class_g_an_amount_and_percent_split_narrows_to_the_amount` |
| **S** — span rule | A quarter column and a year-to-date column ending on the same date were refused as a restatement conflict, so net income was lost (AAPL, MSFT, V, MA, KO, PEP, COST). | In `_resolve_restatements`, readings for one (concept, basis, period end) that disagree are resolved to the shortest span only if **every** reading declares a span. Weeks round to months: 13 weeks count as 3 months and 52 weeks as 12. Otherwise the readings are refused as before. | `test_the_quarter_wins_over_the_year_on_one_period_end` (months, weeks, mixed), `test_disagreeing_readings_without_a_shorter_declared_span_are_refused` (undeclared, one-declared, same-span) |
| **F** — silent empties | An empty figure list looked the same whether the release reported nothing or the binder could not read its layout. | `ReleaseFigureSet.outcome` names why (see below). | `test_class_f_an_empty_figure_list_names_why_it_is_empty` (prose, no-roster-row, undated, refused, bound) |
| **T** — segment footing | A statement listed segment lines above their total, every one matching the revenue (or operating income, gross profit) label, so the readings disagreed and were refused (AMZN revenue and operating income, MSFT …-436122 revenue and operating income, WMT gross profit). | Among disagreeing readings of one concept, basis and period end, the one that the others sum to exactly binds. Footing is checked per period end over every reading, so two segments with the same amount both count. It must hold on one scale, with no elimination row and one total amount (a total stated twice is one total). Otherwise the readings stay `value_ambiguous`. | `test_a_segment_breakdown_binds_the_line_its_segments_sum_to`, `test_a_breakdown_that_does_not_cleanly_foot_stays_ambiguous` (no-footing, two-amounts, elimination, mixed-scale), `test_footing_counts_every_reading_not_every_distinct_amount`, `test_a_total_stated_twice_still_foots` |
| **K** — share-class EPS | EPS was stated per share class ("Class A common stock" and others) with no plain EPS row, so no EPS bound (V). | A share-class row binds as EPS only when the release's headline EPS names exactly one class whose value matches it. A direct EPS row always wins. A headline EPS alone binds nothing. | `test_the_headline_eps_names_which_share_class_is_the_release_eps`, `test_share_class_eps_without_one_matching_class_is_refused` (no-headline, two-classes-match, classes-disagree), `test_a_direct_eps_row_wins_over_share_class_rows`, `test_a_headline_eps_alone_binds_neither_basic_nor_diluted` |

The live diagnosis also needed two narrower header rules: a bare "GAAP"
heading opens a GAAP section (`test_a_bare_gaap_heading_opens_a_gaap_section`,
V), and a "USD | YoY Change" sub-header narrows to the amount
(`test_an_amount_and_change_split_narrows_to_the_amount`, MSFT).

### Fail-closed hardening (first independent review)

The first review attacked the new acceptance paths with synthetic tables and
found shapes that bound a wrong basis or value. Each is now refused or read
correctly, with a test. None of these changes the census yield.

| Finding | Shape | Now | Test |
|---|---|---|---|
| 1, 2 | An EPS label with words after "EPS" ("Diluted EPS excluding special items", "Diluted EPS growth") bound as GAAP EPS. | The label tail is a closed list: a basis tag, an attribution to the parent or its holders (see N1), or a colon. Anything else is not EPS. | `test_an_eps_label_naming_a_different_number_is_not_eps`, `test_an_eps_label_with_an_attribution_or_basis_tag_is_still_eps` |
| 3 | A row with more values than period columns was mapped by position. | The row is refused. | `test_a_row_with_more_values_than_period_columns_is_refused` |
| 4 | A statement title qualified as adjusted ("Adjusted …", "As Adjusted", "Excluding Special Items", "Pro Forma") declared GAAP. | The title declares no basis (see N4). | `test_a_statement_title_qualified_as_adjusted_declares_no_basis` |
| 5 | A small negative after a currency cell ("$ \| (5)") was skipped as a footnote, so the prior-year value shifted into the current period (also at the base). | A parenthesised value after a currency cell is a negative. | `test_a_parenthesized_value_after_a_currency_cell_is_negative` |
| 6 | A placeholder ("—") or unclosed value in the current period dropped the row, so the outcome said `no_candidate_rows`. | The row is a refused candidate with a typed absence, and the outcome is `all_refused` (see N5). | `test_a_placeholder_in_the_current_period_is_a_refused_roster_row` |
| 7 | "Two Quarters Ended", "Q3 YTD" and "Three and Nine Months Ended" declared the wrong span. | A quarter count declares its span. A header that names two spans or a year to date declares none, so the span rule refuses rather than picks. | `test_a_quarter_count_header_declares_its_span`, `test_a_header_that_declares_no_single_span_is_never_the_longer_period` (two-spans, year-to-date) |
| 8 | A class E test passed at the base. | Relabelled a regression guard (see class E). | — |
| 9 | Short prose comparing against GAAP ("Compared with GAAP results") read as a GAAP caption. | Comparison prose is not a caption. | `test_prose_comparing_against_gaap_is_not_a_gaap_caption` |

### Fail-closed hardening (second independent review)

The re-review of the first fixes found eight more shapes (N1–N8). N7 is yield
that now fails closed and needs no change. Every other finding has a fix and a
test. None of these changes the census yield or the live six.

| Finding | Shape | Now | Test |
|---|---|---|---|
| N1 | The EPS attribution slot took any text: "Diluted EPS attributable to discontinued operations", "… to continuing operations", "… to the Tax Act", "… to Acme - pro forma" and, under a reconciliation caption, "… to restructuring charges" all bound as EPS. | The attribution is a closed list: the parent's holders ("common stockholders", optionally "of Acme, Inc."), the Company itself, or a proper name of at most five words with an optional corporate suffix, optionally followed by its holders. A component word (operations, charges, tax, pro forma, adjusted, items, noncontrolling interests and others) refuses. The third review found the proper-name slot still too wide; see NF2. | `test_an_eps_attributed_to_anything_but_the_parent_is_not_eps` (7 labels), `test_an_eps_attributed_to_the_parent_or_its_holders_is_eps` (10 controls) |
| N2 | Narrowing a split beside a "Change" column ignored the amount column's own sub-header, so "Adjusted \| Change" and "Constant Currency \| Reported Change" bound the adjusted column as GAAP. | A split narrows only when the remaining sub-header names a plain amount (USD, $, Amount, As Reported, GAAP, in millions) or a declared non-GAAP basis, which then governs the figure. Any other sub-header is refused. | `test_a_split_whose_remaining_column_is_another_measure_is_refused` (Adjusted, Constant Currency, As Adjusted with % Change), `test_a_split_that_names_its_non_gaap_amount_narrows_to_a_non_gaap_figure` |
| N3 | Segment footing summed the distinct amounts, so segments of 1,000 / 2,000 / 2,000 bound 3,000 as the total. | Footing sums every reading (a multiset), and a total stated twice still counts as one total. | `test_footing_counts_every_reading_not_every_distinct_amount`, `test_a_total_stated_twice_still_foots` |
| N4 | The finding-4 fix declared "As Adjusted", "excluding discontinued operations" and "Pro Forma" titles non-GAAP, so their figures published as adjusted EPS. | A qualified statement title is neither the GAAP statement nor a declared non-GAAP measure: it declares no basis. A units qualifier ("excluding per share data") does not qualify the statement. | `test_a_statement_title_qualified_as_adjusted_declares_no_basis` (5 titles), `test_a_units_qualifier_does_not_qualify_the_statement` |
| N5 | Finding 6 still dropped "Total net sales \| — \| 12%" under "Amount \| % Change" as `no_candidate_rows`, and an unclosed "(0.12" was described as a placeholder. | A placeholder beside a change column is a refused roster row. An unclosed parenthesis is `value_ambiguous` with the detail "the current-period cell opens a parenthesis it never closes; its sign cannot be read". | `test_a_placeholder_beside_a_change_column_is_a_refused_roster_row`, `test_an_unclosed_parenthesis_is_a_value_whose_sign_cannot_be_read` |
| N6 | A comparison of periods ("Q3 2025 vs. Q3 2024", "Q4 FY25 versus Q4 FY24") or "Compared with GAAP results" under a GAAP caption closed the GAAP section. | Only a comparison whose object is a basis is read as one. The section keeps its basis when that basis is the one compared against and nothing else in the text names a basis; otherwise the basis is unknown. | `test_a_comparison_of_periods_or_of_the_same_basis_keeps_the_section` (periods-vs, periods-versus, gaap-compared-with-gaap) |
| N8 | Span leftovers: "Fourth Quarter and Fiscal Year Ended" and "Q4 and Full Year" read as a quarter, "Twelve Weeks and Forty Weeks" read 3 months, "Twenty-Six Weeks" could read "Six Weeks", and "Two Quarters" beat "Twelve Months". | A header joining two periods declares no span. A hyphenated count is never read from its second half. The shortest span wins only when it is a quarter (at most four months). | `test_a_header_joining_two_periods_or_an_unread_count_declares_no_span` (4 headers), `test_the_shortest_span_wins_only_when_it_is_a_quarter`. The third review found more spellings of both shapes; see NF3. |

N7 (fails closed, recorded as residual yield): "Diluted EPS, as reported" is
`no_candidate_rows`; three bare values in two dated slots are refused; and
`$ | (1) | 8,412 | $ | 7,900` is refused. A ten-word statement title such as
"Consolidated Statements of Income (In millions, excluding per share data)" is
not caption-shaped (at most nine words), so it declares no basis; this is
fail-closed and predates N4.

### Fail-closed hardening (third review)

The third review, of the N1–N8 fixes, found four more shapes (NF1–NF4). Each
fix is a union with the check it extends, so nothing that refused before the
fix can bind after it. A new test fails on the previous head (`c6bf2b2e3f07`)
for every shape it names and passes now; its controls pass on both.

| Finding | Shape | Now | Test |
|---|---|---|---|
| NF1 | The N6 fix kept a GAAP section open across "Core Results Compared With GAAP Results", so core EPS and revenue bound as GAAP. The base refused this. | A comparison keeps the section's basis only when every other word in it is a period, a filler word or the same basis. Any other word ("Core", "Comparable", "Pro Forma", "Excluding Special Items", "Underlying") means the comparison names another measure, so the basis is unknown. The N6 check still applies as well. | `test_a_comparison_that_names_another_measure_leaves_the_section` (6 captions), `test_a_comparison_of_only_periods_and_the_same_basis_keeps_the_gaap_section` (3 controls) |
| NF2 | Any Title Case words passed as the parent: "Diluted EPS attributable to Goodwill Impairment" bound as reported EPS, and "… to Class A Common Stock" skipped the share-class rule K. | A proper name is the parent only when the release itself names a company by it with a corporate form ("Walmart Inc.", "The Coca-Cola Company"); the trailing words of that name also count ("Procter & Gamble"). Any other proper name refuses, whether or not the release names a different issuer. Holders and "the Company" need no name. The third review found the check accepted a company named anywhere in the release; see F3. | `test_an_eps_attributed_to_a_name_the_release_gives_no_company_is_not_eps` (22 names × with and without another issuer), `test_an_eps_attributed_to_the_issuer_needs_the_release_to_name_the_issuer` |
| NF3 | A count joined by an en dash, an em dash or a space ("Twenty–Six Weeks") was read from its second half, and two periods joined by `&`, `/`, a comma or two "Ended" clauses escaped the two-period rule. | Every such count declares no span, and so does every such join. The third review found more dash spellings and joins; see F1 and F2. One period with two dates ("Three Months Ended December 28, 2025 and December 29, 2024") still reads as one quarter. | `test_a_header_joining_periods_or_counting_in_an_unread_form_declares_no_span` (9 headers), `test_a_single_period_header_still_declares_its_span` (6 controls) |
| NF4 | "Pro-Forma" (hyphenated) was not a qualifier in titles or in the EPS tail. | The qualifier list reads "pro forma" with a space, a hyphen or neither, and adds "comparable", "core", "underlying" and "recast". | `test_a_statement_title_qualified_as_another_basis_declares_no_basis` (6 titles). The EPS tail had no test of its own: NF2 refuses "Acme Pro-Forma" and "Proforma" before the tail is read. See F5. |

NOTE (fails closed, recorded as residual yield): a segment restated across
two tables now refuses where the base bound it. A company whose name contains
"Core" also fails closed under NF4.

### Fail-closed hardening (fourth review)

The third review of the NF1–NF4 fixes (`203f5e7d9524`) traced most of its
findings to one cause: the binder read only the ASCII hyphen as a hyphen. It
also found that the NF2 issuer check accepted any company the release named
anywhere. Each new test fails on `203f5e7d9524` for every shape it names and
passes now. The exceptions are two controls (layout table, self-reference
first), which pass on both and guard the shape Walmart's releases use.

**Dash fold.** Where a row label, a caption or a period header enters the
binder, U+2010–U+2015, U+2212, U+FE63 and U+FF0D read as "-" and a soft
hyphen (U+00AD) is dropped. Value cells are never folded, so every receipt
still replays its literal against the raw source. `units_source`,
`basis_source` and concept slugs keep the printed text.

| Finding | Shape | Now | Test |
|---|---|---|---|
| BLOCKER (in the base) | A caption written "Non‑GAAP" (U+2011), "Non–GAAP", "NON&#8209;GAAP" or "Non GAAP" was not read as non-GAAP, so its revenue and EPS bound as GAAP. | After the fold, "non" followed by any dash, a space or nothing, then "GAAP", is non-GAAP when no letter precedes "non". | `test_a_non_gaap_caption_spelled_with_any_dash_declares_non_gaap` (6 spellings × alone and after a GAAP caption) |
| F1, F1b | "Twenty‑Six Weeks" with U+2010, U+2011, U+00AD, U+2012 or U+2212, or with a spaced hyphen or en dash, read as one month. | The fold turns each into the hyphenated count NF3 already refuses; a spaced hyphen closes up before the count is read. | 7 headers added to `test_a_header_joining_periods_or_counting_in_an_unread_form_declares_no_span` |
| F2 | Two periods joined by "/ FY2025", "& FY25", "and FY2025", an en dash, ";", "\|" or "Plus" read as one quarter. | A join may also be ";", "\|", any dash or "plus", and the second period may be written "FY", "FY25" or "FY2025". Each such header declares no span. | 7 headers added to the same test |
| F3 | The issuer check accepted a company named anywhere: the EPS row's own label ("Diluted EPS attributable to Goodwill Impairment Co." bound), a subsidiary, a spin-off or an operating company. | The issuer is the first company the release names with a corporate form, in prose or in a layout table. "The Company" and "Our Company" name no one and are skipped. A name given in an attribution is skipped too, so an EPS line cannot vouch for itself. A company named after the issuer is not the issuer. | `test_an_eps_line_cannot_name_its_own_issuer` (2 labels × 2 openings), `test_only_the_first_company_the_release_names_is_the_issuer` (subsidiary, other company first), `test_the_issuer_is_named_in_a_layout_table_after_a_self_reference_or_with_ampersand_co` (3 controls) |
| F4 | "Consolidated Statements of Operations - Pro–Forma" (en dash or U+2011) bound as GAAP. | The fold makes it the hyphenated qualifier NF4 reads, so the title declares no basis. | 2 titles added to `test_a_statement_title_qualified_as_another_basis_declares_no_basis` |
| F5 | Reverting the EPS-tail lookahead to `pro\s+forma` broke no test. | The new test names the issuer "Acme Pro-Forma Inc.", so NF2 accepts the name and only the tail can refuse. Reverting the lookahead fails both of its cases. | `test_an_issuer_named_pro_forma_still_refuses_a_pro_forma_attribution` (hyphen, U+2011) |
| F6 | Since the NF2 fix, lowercase "attributable to the company" binds; `c6bf2b2e3f07` refused it. | This binding is intended: "the company" is the issuer's self-reference in either case. | a lowercase control added to `test_an_eps_attributed_to_the_parent_or_its_holders_is_eps` |

One change makes a line bind that refused on `203f5e7d9524`. "JPMorgan Chase
& Co." now names "JPMorgan Chase", because a trailing "&" is dropped with the
suffix, so "Diluted earnings per share attributable to JPMorgan Chase" binds
(the `ampersand-co` control). One existing control in
`test_an_eps_attributed_to_the_parent_or_its_holders_is_eps` changed: "… to
common stockholders of Acme, Inc." now needs the release to open on "Acme,
Inc.", because under F3 a name in the label cannot vouch for itself.

NOTE (fails closed, recorded as residual yield):

- An issuer whose corporate form the rule does not read names no one, so its
  attributed EPS lines refuse. Examples are "Johnson & Johnson" (no suffix),
  "Mastercard Incorporated" ("Incorporated" is not a listed suffix) and
  "Bank of America Corporation" (registers as "america").
- A release that names another company first (an adviser, a co-issuer) refuses
  its attributed EPS lines rather than bind another company's.
- "Fiscal Year 2026 - Fourth Quarter" now reads as a dash join and declares no
  span. "Fourth Quarter, Fiscal 2026" already declared none after NF3.
- Guidance sentences are not folded. A guidance figure binds only when its
  sentence names non-GAAP, so a guidance sentence spelling it with a Unicode
  hyphen refuses as `basis_undeclared`.

The census rerun on this head equals the NF baseline exactly: 31 parsed, 54
projected, 29 with EPS, 25 with revenue, 208 figures bound, and no figure
changed. The live six bind the same values.

A release that truly does not state EPS still fails closed on EPS:
`test_a_release_that_states_no_eps_fails_closed_on_eps` (no-eps-row,
eps-placeholder) in the binder suite, and
`test_projection_publishes_no_eps_a_release_does_not_state` in
`tests/test_catalyst_source_cycle.py` (projects revenue only).

### Fail-closed hardening (fifth review)

The fifth review (of `3a70bd6b81a5`) found that an EPS label could still
vouch for its own issuer, and that a per-share scope row's attribution was
never checked. 37 of the new or changed test cases fail on `3a70bd6b81a5`;
the other 59 selected cases are controls that pass on both.

| Finding | Shape | Now | Test |
|---|---|---|---|
| M1 | In Title Case or all caps ("Diluted EPS Attributable To Goodwill Impairment Co.") the label named its own issuer, because the name pattern began at "EPS" and the attribution sat outside the 120-character look-back window. A company named first without being the reporter (an advisor, a merger partner, "Co-Founder", "a Delaware corporation") was also taken as the issuer. | The issuer is the first company named by its corporate form, as a company sets it (no case folding), and named as the reporter. That means an exchange ticker ("(NYSE: WMT)") or a reports/announces/posts verb, optionally after "today". The attribution check now spans the name itself, not only the 120 characters before it. | `test_an_eps_line_in_any_case_cannot_name_its_own_issuer` (4 labels × 2 openings), `test_a_company_named_without_a_ticker_or_reporting_verb_is_not_the_issuer` (advisor, co-founder, Delaware corporation), `test_only_the_first_company_the_release_names_is_the_issuer` (now 3 cases, each opening cued) |
| M2 (in the base) | A bare "Diluted" row under a scope such as "Earnings per share attributable to discontinued operations:", "… noncontrolling interests:", "… Acme Operating LLC:", "… excluding special items:" or "Pro forma earnings per share:" bound as the issuer's GAAP EPS. | A scope row whose tail says "attributable to" is held to the same closed tail as a full EPS label, and its attribution must name the issuer or its holders. A component, an exclusion or a pro forma names another number and refuses. The sixth review showed that scopes naming another entity or another measure still bound; the whole scope row is closed below. | `test_a_bare_diluted_row_under_a_component_or_foreign_scope_is_not_eps` (7 scopes), `test_a_bare_diluted_row_under_the_issuers_eps_scope_is_eps` (6 controls), `test_a_scope_attributed_to_the_issuer_needs_the_release_to_name_the_issuer` |
| m1 | The fold kept zero-width characters, so "Non\u200b-GAAP", "Non&#8203;-GAAP" and "Non\ufeffGAAP" read as GAAP, and "Twenty\u200bSix Weeks" read as one month. | The zero-width space, non-joiner, joiner, word joiner and byte-order mark are dropped with the soft hyphen. | 4 captions added to `test_a_non_gaap_caption_spelled_with_any_dash_declares_non_gaap`, 3 headers added to `test_a_header_joining_periods_or_counting_in_an_unread_form_declares_no_span`, `test_a_per_share_line_holding_a_zero_width_character_is_eps` |
| m2 | "Q4-FY26", "Q4 - Fiscal 2026" and "Fourth Quarter - Fiscal 2026" read as two joined periods, so they declared no span. | A quarter dashed to a numbered fiscal year is one quarter. "Q4 FY26 and FY25", "Q4 FY26 / FY25" and "Fourth Quarter - Fiscal Year 2026" still name two periods and still declare none: they join two periods, so the over-refusal the review listed for them stands by design. | `test_a_quarter_dashed_to_its_numbered_fiscal_year_is_one_quarter` (5), `test_a_quarter_dashed_to_a_second_period_still_names_two` (6), `test_a_quarter_dashed_to_its_fiscal_year_wins_over_the_year` |
| m3 | Removing the fold from `_basis_for`, `_concept_for`, `_issuer_names`, `_observed_kind` or `_row_is_header`, or the `(?<![a-z])` lookbehind, broke no test. | Each of 12 mutants now fails at least one test: the fold removed from the caption, the issuer block, the header label, the period header, and separately from the label and the scope in `_observed_kind`, `_concept_for` and `_basis_for`; and the `(?<![a-z])` lookbehind removed from the caption and the inline check. Two constructs had no effect and were removed: the lookbehind in `_BASIS_COMPARISON_RE` (its alternative already requires the word "non") and the fold in `_normalize_issuer` (every caller folds first). | `test_a_non_gaap_eps_label_with_a_non_breaking_hyphen_is_non_gaap`, `test_an_issuer_and_its_attribution_match_across_hyphen_spellings`, `test_a_year_valued_row_with_a_hyphenated_roster_label_is_data_not_a_header`, `test_a_non_gaap_scope_row_with_a_non_breaking_hyphen_is_non_gaap`, `test_the_non_of_a_word_ending_in_non_is_not_non_gaap` |
| m4 | "Co-" in "Co-Founder" read as the suffix "Co", and "a Delaware corporation" as a company named Delaware. | The form must stand as its own word and be followed by the reporter cue. | `co-founder` and `delaware-corporation` cases above |

Every existing test that opened a release on a bare company name now opens
with `_opening()` ("Acme Holdings, Inc. (NYSE: XYZ) today reported
results."), because a name without that cue is no longer the issuer.

The census rerun on this head equals the NF baseline exactly: 31 parsed, 54
projected, 29 with EPS, 25 with revenue, 208 figures bound. No figure changed
on any of the 40 releases, and every sha256 matched. The live six bind the
same values.

### Fail-closed hardening (sixth review)

The sixth review (of `e4b89cfac4d9`) found that a scope row was closed only
when its tail said "attributable to". Under a scope naming another entity or
another measure, a bare "Diluted" row still bound as the issuer's GAAP EPS.
It also found three minor gaps. 36 of the 50 new test cases fail on
`e4b89cfac4d9`; the other 14 are controls that pass on both.

| Finding | Shape | Now | Test |
|---|---|---|---|
| M2 remainder | A bare "Diluted" row bound 1.23 GAAP under "Earnings per share of SpinCo Inc.:", "SpinCo Inc. earnings per share:", "Core", "Operating", "Cash", "Comparable", "Underlying" or "Distributable earnings per share:", "FFO per share:", "Earnings per share - Class B:", "Earnings per share (Predecessor):", "Earnings per share guidance:", "Dividends declared per share:" and "Book value per share:". | The whole scope row is closed. Before "per share" it may carry only a basis (GAAP, non-GAAP, adjusted), basic or diluted, and net income, earnings or loss. After it, it may carry only "data", "amounts", "information" or "of common stock", basic or diluted, and the closed EPS tail, whose attribution must name the issuer or its holders. A trailing footnote mark ("(1)", "*", "†", "‡", a digit glued to the word, or a superscript) is stepped over first. | `test_a_bare_diluted_row_under_a_component_or_foreign_scope_is_not_eps` (27 scopes, 20 new), `test_a_bare_diluted_row_under_the_issuers_eps_scope_is_eps` (18 controls, 12 new) |
| Minor 1 (regression in `e4b89cfac4d9`) | "NEW YORK--(BUSINESS WIRE)--Acme Corp. (NYSE: ACM) …" named no issuer, because the name lookbehind rejected every name after a hyphen. | Only a name glued to a hyphenated word is rejected ("Acme e-Commerce Co." does not name "Commerce"). A name after dateline dashes is read. | `test_the_issuer_is_named_directly_after_a_wire_dateline` (Business Wire, PR Newswire), `test_a_name_glued_to_a_hyphenated_word_is_not_the_issuer` |
| Minor 2 | The fifth-review dash rewrite stripped the joiner from "Q4-FY26 vs Q4-FY25", "… compared to …" and similar headers, so they read as 3 months. | "vs", "vs.", "versus", "compared to" and "compared with" join two periods, so these headers declare no span. | 5 cases added to `test_a_quarter_dashed_to_a_second_period_still_names_two` |
| Minor 3 | Other invisible format characters survived the fold: the left-to-right and right-to-left marks, the bidirectional isolates and embeddings, the invisible operators and the combining grapheme joiner. | Every format (Cf) character in the BMP, in U+1D173–U+1D17A and in the tag block (U+E0000–U+E007F), and U+034F, is dropped with the soft hyphen. Format characters in other supplementary blocks are kept (see the residuals). | 3 captions (6 cases, alone and after a GAAP caption) added to `test_a_non_gaap_caption_spelled_with_any_dash_declares_non_gaap`, 3 headers to `test_a_header_joining_periods_or_counting_in_an_unread_form_declares_no_span` |
| Note (header time) | The existing two-period header pattern took about 8.4 s on a 50,000-character header, and the dash rewrite now reached it from the dashed form too. | A header label longer than 300 characters declares no span. | `test_a_header_longer_than_a_period_name_declares_no_span` |

The census caught a regression in the first version of the closed scope row.
Both NFLX releases carry a footnote mark on their EPS scope row, which the
closed tail read as an unknown word. Each release fell from 8 bound figures
to 6 and lost its projected GAAP EPS actual. The footnote step now covers
asterisks, daggers, glued digits and superscripts as well as "(n)". Removing
the step fails 6 controls: the 5 footnote marks and "(1)".

The census rerun on this head equals the census at `e4b89cfac4d9` exactly: 31
parsed, 54 projected, 29 with EPS, 25 with revenue, 208 figures bound. No
figure changed on any of the 40 releases, and every sha256 matched. The live
six bind the same values.

## Live releases that production showed UNAVAILABLE

Production bound these six with the binder on `main`. Re-fetched in memory
through the writer's own path (`_Cycle._bounded_get`, the EX-99.1 row of the
filing index, `project_release_figures`); D4 holds and only hashes and URLs
were kept. On this branch every one is `parsed` / `figures_projected`.

| Ticker | Accession | Production (main) | This branch: `eps_actual` | `rev_actual` | Classes |
|---|---|---|---|---|---|
| AMZN | 0001018724-26-000038 | EPS and revenue missing | 1.89 | 201,944M | A·T |
| MA | 0001141391-26-000122 | EPS and revenue missing | 5.28 | 9,807M | A·B·D·S |
| MSFT | 0001193125-26-436122 | EPS and revenue missing | 4.92 | 92,279M | A·E·G·T |
| GOOGL | 0001652044-26-000080 | EPS and revenue missing | 2.12 | 127,577M | A·B |
| KO | 0001628280-26-067403 | EPS and revenue missing | 0.93 | 13,380M | D·S |
| V | 0001403161-26-000126 | EPS missing | 3.19 | 12,139M | A·S·K |

Ablation (disable one rule, re-bind) confirms the attribution: without
footing, AMZN and MSFT lose revenue; without share classes, V loses EPS.

## Outcome codes (follow-up "g")

`extract_release_figures` now returns `outcome` together with `table_count`,
`period_table_count` and `candidate_row_count`. The outcome is decided from
the structure the binder actually walked:

| Binder outcome | Meaning |
|---|---|
| `figures_bound` | At least one figure bound. |
| `no_blocks` | The body normalised to nothing. |
| `no_tables` | Prose only; there is nothing tabular to read. |
| `no_candidate_rows` | There are tables, but no row names a roster concept. |
| `no_period_columns` | There are roster rows, but none sits under a dated header. |
| `all_refused` | Roster rows sit under dated headers, but every one was refused. |

The Catalyst cycle carries the code to the public index as `figure_outcome`.
`FIGURE_OUTCOMES` in `engine/marketing/catalyst_packets.py` maps each code to
the one `parse_status` it is consistent with:

- `parsed`: `figures_projected`.
- `no_figures`: `figures_not_projectable` (figures bound, but none
  projectable) and the five empty binder outcomes.
- `parse_failed`: `document_not_utf8`, `binder_exception`, `replay_failed`.

A digest mismatch carries an empty code, and the release is skipped before
publish exactly as before.

- **Index validator** (`catalyst_source_store.py`): when the field is present,
  it must agree with `parse_status`. An event published before the field
  existed is still accepted.
- **Adapter** (`catalyst_source_adapter.py`): passes the code through to the
  document observation only when it agrees with `parse_status`.
- **Packets** (`catalyst_packets.py`): when figures are missing, the packet's
  `missing_data` names `source_figure_outcome_<code>`. A binder error is
  therefore distinguishable from a release with nothing to project.

Tests:

- `tests/test_catalyst_source_cycle.py`:
  - `test_projection_names_why_a_release_has_no_figures`
  - `test_cycle_publishes_the_figure_outcome`
  - `test_index_validates_the_figure_outcome`
- `tests/test_catalyst_packet_public.py`:
  - `test_v2_missing_figures_name_the_source_figure_outcome`
  - `test_figure_outcomes_cover_every_binder_outcome`
  - `test_pinned_observation_names_a_binder_failure`
- `tests/test_catalyst_source_adapter.py`:
  - `test_32_figure_outcome_reaches_the_observation`

## Residuals

The 9 releases still `no_figures`, with the binder outcome observed on this
branch (re-bound in memory, sha256 re-checked). Counts are tables / dated
tables / candidate rows.

| Release | Outcome | Counts | Why (from the census diagnostics) |
|---|---|---|---|
| TSLA …-066738 | `no_tables` | 0 / 0 / 0 | The exhibit body has no table, so no roster concept is present. |
| TSLA …-064366 | `no_candidate_rows` | 1 / 0 / 0 | Its one table has no roster row and no dated header. |
| JPM ×2 | `no_period_columns` | 17 / 0 / 8–9 | Roster rows exist, but no table has a header the binder can date. 8–9 basis-undeclared refusals. |
| JNJ ×2 | `no_period_columns` | 7–8 / 0–1 / 1 | Its one roster row sits under an undated header. 2 period-undeclared refusals and 1 basis-undeclared refusal. |
| PG …-000093 | `all_refused` | 21 / 13 / 25 | 13 `value_ambiguous` refusals: readings for one period end disagree and no single shortest declared span exists, so the span rule refuses rather than picks. There are also 12 basis-undeclared and 4 period-undeclared refusals. |
| UNH …-000255 | `no_tables` | 0 / 0 / 0 | The exhibit body has no table. |
| UNH …-000191 | `figures_bound` → `figures_not_projectable` | 0 / 0 / 0 | Only non-GAAP guidance EPS (low/high) bound; nothing is projectable. |

Other partial gaps on parsed releases:

- MSFT …-436122: class G reconciliation splits are still refused by design,
  but no concept is left unbound by them now; revenue and operating income
  bind through segment footing (class T).

Recorded after the fifth review:

- **Issuer cue (fails closed, no census loss).** A release whose reporter
  sentence carries neither an exchange ticker nor a reports/announces/posts
  verb names no issuer, so its attributed EPS lines refuse. All 40 census
  releases bind the same figures as before the cue was required.
- **First cued company is not the filer (open).** A release whose first
  company named with a ticker or reporting verb is not the filer (a co-issuer,
  a partner announcing first) vouches for that company's attributions. Binding
  the issuer to the filer's CIK name closes this and is a follow-up.
- **Names the form rule does not read (fails closed).** "UnitedHealth Group"
  (no suffix), "Johnson & Johnson", "Mastercard Incorporated" and "Bank of
  America Corporation" name no issuer, so their attributed EPS lines refuse.
- **Single-quarter joins (open, n1).** A header joining two periods with "+",
  "·", "•", ":" or "with" still reads as one quarter.
- **Undated quarter headers (pre-existing).** "Q4 Ended December 28, 2025",
  "Q4 2025" and "Q4-FY26 Ended …" declare no period end, so their columns
  refuse as `period_undeclared`. Beside a twelve-month cash-flow statement the
  annual net income then binds alone for that date, exactly as it does on
  `3a70bd6b81a5`. Net income is not projected. "Fourth Quarter Ended …" is read.
- **Removed constructs.** The lookbehind in `_BASIS_COMPARISON_RE` and the
  fold in `_normalize_issuer` had no effect and were removed. No result
  changed.

Recorded after the sixth review:

- **Basis after a dash or comma (fails closed).** "Earnings per share -
  GAAP:" and "Earnings per share, GAAP:" scope rows refuse. The basis is read
  only before "per share" ("GAAP earnings per share:"). No census release lost
  a figure.
- **Attribution before "per share" (fails closed).** "Net income attributable
  to <issuer> per share:" refuses even when it names the issuer, because the
  closed head does not read an attribution. "Earnings per share attributable
  to <issuer>:" binds.
- **Em dash glued to the dateline (fails closed).** "NEW YORK—Acme Corp." folds
  to a hyphenated word, so it names no issuer. The doubled "--" of a wire
  dateline and a spaced en or em dash are read.
- **A later mention can steer the issuer (open, as at `e4b89cfac4d9`).** An
  "attributable to holders" window that swallows the first name, or the noun
  "reports" read as the reporter verb, can still pick a later company.
- **Row-label footnote marks (fails closed, as at `e4b89cfac4d9`).** A full
  EPS row label ending in "*", "†", a superscript or a glued digit ("Diluted
  EPS*") refuses, and so does a bare "Diluted*" row under a scope. Row labels
  step over "(n)" footnotes only.

Recorded after the seventh review (of `bea61a0b7d34`, PASS):

- **Scope rows the closed head and tail do not read (fails closed).**
  "Reported earnings per share:", "Earnings per share (in dollars):", "… ($):",
  "… (unaudited):", "… (a):" (a letter footnote), "… (1)*:" (stacked marks;
  only the last is stepped over), "Earnings per share, as reported:" and "Per
  share data (unaudited):" refuse. Each bound the issuer's GAAP EPS at
  `e4b89cfac4d9`. No census release lost a figure.
- **Supplementary-plane format characters (open, as at `e4b89cfac4d9`).**
  U+110BD and U+1BCA0–U+1BCA3 are not folded, so "Twenty", one of them and
  "Six Weeks Ended …" reads as one month. No filing is known to carry them.
- **Unlisted two-period joiners (open, as at `e4b89cfac4d9`).** "v.",
  "against", "relative to" and "over" still read as one quarter, like the n1
  joiners. The span only settles a conflict between columns.
- **One basis in the scope, the other in the row (open, as at
  `e4b89cfac4d9`).** Under "Basic earnings per share:", a bare "Diluted" row
  binds diluted EPS.
- **Two slow paths on adversarial input (no wrong figure).** A block of
  50,000 characters made of glued "--Abc" takes about 12 s in issuer
  detection, and a scope row padded with tens of thousands of invisible
  characters takes about 8 s in the scope tail. A length cap like the
  300-character header cap would close both.

These are follow-ups, not regressions. None of them is fixed by widening a
pattern; each needs its own evidence, and some need a source other than the
table body. See the handoff's follow-up list.
