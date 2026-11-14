# Group Reads benchmark observation coverage — #11077

## Outcome

The benchmark loader now preserves missing SPY observations on the existing member session grid. It resolves the existing keep-last identity before qualifying missing/nonfinite values, then aligns without forward filling. A missing reaction or fifth-session endpoint withholds the unsupported drift comparison; an interior gap does not change the endpoint-based horizon.

The detailed earnings section and compact tile now describe complete member/SPY comparisons and qualifying report observations in English and Chinese. They do not infer a specific missing cause from the frozen v1 schema. A null sympathy ratio no longer falsely asserts that too few report days occurred, and numeric event counts no longer masquerade as independent dates.

**159 native tests pass, zero skips.** Expanded tests against the original engine/template produce **33 failures /126 passes**, including the intentional replacement of false copy expectations. Failure count is not a count of independent defects.

This source repair is prepared as Draft/unarmed. Natural CI and full-page/browser acceptance remain separate obligations.

## Source and ownership

Source/data pin: `16e874433e0ff0fb0ad863b839deb1d16f824005`.

Publication parent: `8d6a5e115a72ef93cfa779e15c1689957c27cc9e`. Exact root/subtree comparisons show all source, tests, templates, configuration, scripts, CI definitions and the five relevant data subtrees are identical between these commits. Only generated `site` and unrelated `data/marketing` trees changed. The complete-tree checks supersede the compare endpoint's capped 300-file listing; accepted tests and data proof are reused by exact object identity.

Original acceptance: [#4996 comment6806320343](https://github.com/mastermindx-market-intelligence/macro/pull/4996#issuecomment-6806320343). Assigned repair: [#11077 claim6806797162](https://github.com/mastermindx-market-intelligence/macro/issues/11077#issuecomment-6806797162).

Five source/test paths change:

- `engine/group_earnings.py`: loader and its coverage documentation only.
- `templates/basket_detail.html.j2`: sympathy copy in `grEarnTileBody` and drift/sympathy copy in `grEarningsSection` only.
- Existing contract, sympathy and shipped READ-surface suites: discriminating regressions.

All other producer source after the module documentation is unchanged. Every template byte outside those two functions is identical. Schema keys, floor constants, event mapping, fixed five-session arithmetic, membership, guidance, revisions, scoring/ranking/sizing restrictions and ledger implementation are unchanged.

The retained complete estate inventories plus exact merge-base/head comparisons covered the known surrounding template writers. The additional compact-tile hunk was separately checked at the unchanged heads of #10892, #10838, #10703, #10674, #7669, #7252, #10654 and #7060; its original 33 lines /2,692 UTF-8 bytes match main at every head. Seven incomplete-inventory head bindings were refreshed and their retained object comparisons still apply. The final publication delta checked 27 open PRs updated since 20:43 UTC: 16 exact-head complete inventories were reused; 11 fresh complete inventories covered 654 paths with zero target/rename hits. All final heads were stable at the 21:23:56–21:24:06 UTC readback. This clears these source hunks, not the other PRs' release holds.

## Admission and fixed-window semantics

The original loader dropped nulls before resolving duplicate dates, then carried the previous close onto missing member-grid sessions. That could both resurrect an earlier duplicate and turn a missing benchmark endpoint into an apparently measured return.

The repair:

1. Converts close values to numeric while retaining missing rows.
2. Normalizes date precision and retains the existing last row per date.
3. Treats nonfinite retained benchmark values as unavailable.
4. Reindexes onto the unchanged member grid without filling or removing sessions.

The outer sweep still refuses when the aligned benchmark has no usable observations. There is no new minimum-count gate or requirement for complete coverage of the entire grid. Drift retains the original reaction-close → plus-five-sessions endpoint definition. It never searches for a later usable quote.

Masking a source infinity matters for sympathy too: an infinity followed by a finite close can otherwise produce a finite negative-100-percent benchmark return. Filtering only the derived nonfinite returns would miss that case.

The keep-last claim concerns the order delivered by the existing shared store reader. The shared reader's earlier sort is unchanged; raw out-of-order duplicate ordering is not repaired. Duplicate fixtures use canonical monotonic date order so the retained identity is explicit. Nonpositive benchmark prices and invalid member-price operands are preexisting adjacent limitations outside this observed-date repair; this is not comprehensive price validation.

## Native test qualification

All three complete owning suites executed:

```text
python -m pytest tests/test_group_earnings_contract.py \
  tests/test_group_earnings_sympathy.py \
  tests/test_group_read_surface.py -q -rs
```

Environment: Python 3.14.7, Node v26.5.0, NumPy 2.5.2, pandas 3.0.5, PyArrow 25.0.1, PyYAML 6.0.3, pytest 9.1.1 and requests 2.34.2. No dependency installation or module stand-ins were used.

Final candidate: **159 PASS /0 SKIP**, 10.14 seconds reported by pytest. Original application with the same expanded tests: **33 FAIL /126 PASS**, 10.23 seconds. Three final tooltip regressions inspect the actual HTML attributes as well as visible translations, so a misleading tooltip cannot hide outside the language-span extractor. All preexisting cases remain enrolled; the one existing display test that required misleading words is intentionally corrected.

The initial native run found two test/proof issues that were resolved before final qualification: the compact earnings tile still emitted the old misleading copy, and an unsorted synthetic duplicate fixture invoked the shared reader's existing unstable sort before the scoped loader. The tile's separately cleared hunk is now repaired; the duplicate test explicitly fixes source ordering without changing or bypassing the shared reader.

Green log SHA-256: `78caf638aaf184b34aa32e4dc1b75c12c6604a759f8e5c551a50599f18ef52ec`.
Red log SHA-256: `d6d6470d7d722812f55743568063050498e105c71d92c87d75273ad32ac426e7`.

## Actual public writer and shipped consumer

The audit executes genuine temporary Parquets through native member, SPY, membership, earnings, guidance and revision readers, then `write_earnings_pulse`. It reads the actual emitted `earnings_pulse.json` back, verifies strict JSON and the v1 contract, assigns that parsed payload to `GRE`, and executes the whole shipped READ region's earnings section and compact tile under Node.

There are **14 drift-source shapes** and **five full-sweep sympathy shapes**, in both original and repaired trees. Together with the committed MAG7 replay, that is **40 combined section/tile HTML outputs and 80 extracted language outputs** across the two versions. All are included in the companion JSON.

This harness retains the existing surface suite's six documented page-helper substitutions. The harness executes each version's actual READ module, section and tile directly. This is section/tile execution, not browser/DOM/layout or complete page bootstrap proof.

Selected writer outcomes:

| Input | Original | Repaired |
|---|---|---|
| Complete endpoints: four members +1%, SPY +2% | share 0.0, n=4 | Identical measured zero |
| Missing or null fifth-session SPY close | share 1.0, n=4 | share null, n=0 |
| One old SPY quote | share 1.0, n=4 | share null, n=0 |
| Missing/null reaction close | Numeric share admitted, n=4 | share null, n=0 |
| Final missing/bad same-date duplicate | Earlier valid quote admitted, n=4 | share null, n=0 |
| Interior benchmark gap, endpoints observed | share 0.0, n=4 | Identical complete artifact |
| Last duplicate is valid | share 0.0, n=4 | Identical complete artifact |
| All benchmark values nonfinite | Populated drift, n=4 | Whole sweep unavailable |
| Absent/all-null benchmark | Whole sweep unavailable | Same refusal |

Season, results, guidance, revisions, schema, authority and analytical dates remain unchanged in the affected synthetic comparisons. Display text retains actual zero values and explains qualified endpoints without adding a cause field.

The convenience writer is a real public entry point. The full basket builder independently calls `compute_group_earnings` and writes the same JSON representation; this audit does **not** claim a full `scripts.build_baskets` run.

## Sympathy and ledger implications

A missing SPY close invalidates that day's benchmark return and the following return, which lacks its predecessor. The member session grid and trailing window are not compressed.

Native loader → return → sympathy cases prove:

- Missing report-day, preceding-day, quiet-day and final-null duplicate observations preserve only supported returns.
- An infinity at one report session cannot yield a false finite comparison on the next session.
- Unsupported events are omitted under the existing cohort gate; valid mixed events and their counts remain.
- Quiet-day gaps omit only unsupported baseline returns.
- A completely unusable baseline leaves the ratio null while independently supported beat/miss medians remain visible.
- Event counts are reporter-event rows; multiple reporters on one date are not represented as independent report days.

In the full eight-member public-writer fixture, a missing report-day or immediately preceding SPY quote reduces qualifying events **48 →47**, retains eight reporters and ratio **2.0**, and removes the unsupported new ledger row. The complete fixture and quiet-gap controls retain 48 events.

The actual append function is unchanged. Temporary-ledger tests preserve recorded rows and their values when newer admissible rows are added, retain a byte-identical no-op on repeat admission, and refuse advancement on express/intraday lanes even with a nightly legacy alias present. The public-writer audits explicitly set express after pytest's setup and verify no ledger was created. No production ledger was acquired, regenerated or rewritten.

## Committed MAG7 replay

Thirteen exact committed data objects, **6,190,211 bytes**, supply the complete seven-member MAG7 price slice and the real shared stores. All blobs, byte counts and SHA-256 values are verified. The complete registry remains intact, but only MAG7 has its entire price membership materialized.

The actual member-grid union contains **3,234 sessions, 2014-01-02 through 2026-11-10**. SPY is observed on all 3,234 of those sessions, including all **504** sessions in the current sympathy window. This extends the earlier reported 260-session spot check for this exact pinned slice; it does not establish universal live-store cleanliness.

The **entire frozen-clock MAG7 object is identical** before and after:

- Five-session drift: share **0.5**, **n=6**.
- Sympathy ratio **0.98**, **55** qualifying report observations, **7** reporters.
- Beat-day median **-0.00077**, 10 beat days; miss-day median null, three miss days.
- All other fields unchanged.

The emitted JSON file from this bounded materialization is byte-identical, SHA-256 `4f35e73d568437da70dbbf215fd9524e1745d0628594248ff751d80c3a519fb2`. Although the writer emits 49 basket keys, the other baskets can contain partial overlapping inputs; their emission is not all-49 data qualification.

This snapshot has **no observed incidence of the repaired SPY-gap defect**. Synthetic cases establish the changed behavior; the committed replay establishes preservation. Neither is a point-in-time study, backtest or trading authorization.

## Existing CI enrollment

No CI source, baseline or budget is changed.

- Existing CODE owner `group-earnings-pulse` runs both full producer suites with the genuine storage dependencies.
- Existing CODE owner `group-read-surface` runs the complete READ-surface suite and its existing sector siblings, with explicit Node setup.
- Existing command weights remain **6** and **8**. All three test files are already absent from the unrun baseline.
- Actual producer imports and template reads retain the incumbent inferred scope. No new owner, command, runner, installer, watcher or extra probe funding is introduced.

Natural CI owns full-tree selection, packing and terminal semantic proof. No local full-tree planner execution is claimed.

## Evidence and remaining acceptance

The companion JSON contains exact candidate and input manifests, native test receipts, both versions' complete synthetic payloads/HTML, committed MAG7 coverage and outputs, source ownership/self-check receipts and executable audit source.

Consumer-audit SHA-256: `3308e4ff3035362563de2202f70a2ef813522571ff1e878d4fc206fb98b62690`.

These native results establish the scoped source/data/consumer behavior. Browser interaction, responsive layout, full-page bootstrap, a production render and deployment remain unproved. No denied preview action is retried, no existing release hold is cleared, and no approval, merge-controller arming or native auto-merge is implied.
