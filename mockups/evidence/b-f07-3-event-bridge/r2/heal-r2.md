# Heal h3c_7134 (2026-09-19) — round 2 preservation and scope result

Status: PARTIAL. CODE_HEAD: `8dc43cbf5bd393506a481f566881320fb72b3891`. The PR remains Draft.
No application, template, test, or CI source was changed in this round.

## Findings and exact scope boundary

- Latest BLOCKER 1 remains: the builder only admits AAPL; its committed data gives a null bridge. NSA renders `post_effective_amendment` through the production producer and template, but is outside `_VS_TICKERS`.
- The ruling permits `scripts/build_stock_library.py` edits **“ONLY at the controls_blob(_vs_v1…) call site … ≤5 lines, passing what the engine needs; nothing else in that file.”** The needed cohort assignment at line 2917 is outside that grant. Changing another issuer's identity or bypassing the cohort at the call site would violate its purpose. The existing exact proposal is retained, unapplied, pending a scope amendment.
- Latest MAJOR 1 remains: the downloaded hosted log for run 35421325082 / job 105839492389 reports **62 introduced, 0 inherited (base 5332d876e758)**. This is branch-caused, not an identical main failure.
- Ruling 2 permits workflow edits **“ONLY inside the conviction-profile job's paths: list”**, adding the six named paths, and says **“Nothing else in that file.”** Those six declarations are already present; the remaining eight-job closure needs the exact-path proposal outside this grant. No dependency-analysis bypass or unauthorized workflow edit was made.
- Latest MINOR 1: the PR body will replace its stale IN_PROGRESS claim for the previous head with the concluded FAILURE and separately state the new head's measured checks.
- Latest MINOR 2: merged current fetched main `936e1b65a1b2a9e5de9039162219ebe419d37d1e` as real two-parent commit `8dc43cbf5bd393506a481f566881320fb72b3891`. Ancestry exits 0.

## Preserved commit 2509328e review

The subsequent repair `26f63cae402c` is retained after reading all four original diffs:

- `.github/ci/legacy-jobs.yml`: keep the later replacement of `engine/**` with the six explicit authorized paths. The broad wildcard did not meet the ruling.
- `engine/valuation_assumptions.py`: keep removal of the false No IO claim and `controls_blob(v1)`; keep the later owner-resolved Chronicle/SEC readers and latest non-null selection instead of the preserved hard-coded incomplete producer.
- `engine/valuation_event_bridge.py`: keep the later removal of the 16 preserved additions, which invented vocabulary keys or duplicated typed-null keys.
- `tests/test_valuation_event_bridge.py`: keep production-call intent and the later owner-path fixtures, exact vocabulary union, validated Parquet and newer-null regressions.

No history was rewritten. The earlier MiniMax broad workflow change and restoration remain in history.

## Tests and real data

`PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH" python3 -c 'import sys,pytest;print(sys.executable,sys.version.split()[0],pytest.__version__)'`

```text
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 3.12.10 9.1.1
```

`TMPDIR="$PWD/.heal-7134" PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH" python3 -m pytest tests/test_valuation_event_bridge.py -q -p no:cacheprovider --basetemp .heal-7134/r2/pytest`

```text
..........................                                               [100%]
26 passed in 21.12s
```

No new behavioral fix was claimed. Existing RED receipts at `6e391cf1` (3 failed, 1 passed, 22 deselected) and `2509328e` (4 failed, 22 deselected) remain in the evidence root; the tested source bytes are preserved.

Real producer/template command: the `python3 -c` command in `../heal-h4.md`, rerun under 3.12, plus the same call for AAPL:

```text
NSA:post_effective_amendment
FY 2025 reported SEC statements
Latest filing on file (Post-Effective Amendment) usually presses margin.最新备案（生效后修正）通常压缩利润率。
AAPL: None
```

The local `scripts/check_contract_delta.py --base origin/main` command was not run: its `materialize_base_tree()` creates a second checkout and runs Git there, contrary to the hard work-only-in-cwd law. The hosted differential result above is actual evidence; neither a local 0-introduced nor a green final-head check is claimed.

## Fresh captures

`PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH" python3 mockups/evidence/b-f07-3-event-bridge/generate_hosts.py`

All three hosts regenerated after the merge and were byte-identical to the preserved hosts.
`TMPDIR="$PWD/.heal-7134" python3 mockups/evidence/b-f07-3-event-bridge/capture.py`
used the existing Python 3.14 Playwright installation (no engine imports or pytest); no package installation was needed. Python 3.12 lacks Playwright on this seat. All engine imports and pytest used 3.12.

```text
24 cells captured sequentially; 0 page errors; 11px < 11.5px; no line overflow.
```

Representative tender-offer/dark/EN/mobile, restructuring/light/ZH/mobile, and null/light/EN/desktop crops were visually inspected. No machine slugs or overflow observed; independent taste approval is not claimed.

## Merge preservation

The initial merge attempt refused because `origin/main` was a shallow boundary. It changed no files or history. `git fetch --deepen=10 origin main` supplied the common ancestor, after which ordinary `ort` merged cleanly. No allow-unrelated-histories or whole-file side selection was used.

Before, at `7c1d1f7a6c7d1b151f2e644dd7754e36e6592477`, `git diff --stat $(git merge-base HEAD origin/main) HEAD`:

```text
 .github/ci/legacy-jobs.yml                         |   29 +
 engine/valuation_assumptions.py                    |   74 +-
 engine/valuation_event_bridge.py                   |  318 +++
 mockups/evidence/b-f07-3-event-bridge/EVIDENCE.yml |   46 +
 .../b-f07-3-event-bridge/capture-metrics.json      |  317 +++
 mockups/evidence/b-f07-3-event-bridge/capture.py   |   42 +
 .../b-f07-3-event-bridge/contract-head.json        |   83 +
 .../b-f07-3-event-bridge/generate_hosts.py         |   32 +
 .../evidence/b-f07-3-event-bridge/green-final.log  |    2 +
 mockups/evidence/b-f07-3-event-bridge/heal-h4.md   |  200 ++
 .../hosts/valuation-event-bridge-null.html         | 2691 ++++++++++++++++++++
 .../valuation-event-bridge-restructuring.html      | 2691 ++++++++++++++++++++
 .../hosts/valuation-event-bridge-tender-offer.html | 2691 ++++++++++++++++++++
 .../evidence/b-f07-3-event-bridge/manifest.json    |   39 +
 .../evidence/b-f07-3-event-bridge/post-merge.stat  |   21 +
 .../evidence/b-f07-3-event-bridge/post-merge2.stat |   21 +
 .../evidence/b-f07-3-event-bridge/pre-merge.stat   |   21 +
 .../evidence/b-f07-3-event-bridge/pre-merge2.stat  |   21 +
 .../proposed-scope-amendment.patch                 |  139 +
 .../b-f07-3-event-bridge/real-issuer-final.log     |    3 +
 .../evidence/b-f07-3-event-bridge/red-2509328e.log |  147 ++
 .../evidence/b-f07-3-event-bridge/red-6e391cf1.log |   97 +
 .../evidence/b-f07-3-event-bridge/red_replay.py    |   16 +
 mockups/evidence/b-f07-3-event-bridge/smells.json  |   13 +
 mockups/evidence/b-f07-3-event-bridge/smells.md    |   30 +
 ...valuation-event-bridge-null_desktop_dark_en.png |  Bin 0 -> 2506 bytes
 ...valuation-event-bridge-null_desktop_dark_zh.png |  Bin 0 -> 2186 bytes
 ...aluation-event-bridge-null_desktop_light_en.png |  Bin 0 -> 2567 bytes
 ...aluation-event-bridge-null_desktop_light_zh.png |  Bin 0 -> 2265 bytes
 .../valuation-event-bridge-null_mobile_dark_en.png |  Bin 0 -> 2435 bytes
 .../valuation-event-bridge-null_mobile_dark_zh.png |  Bin 0 -> 2069 bytes
 ...valuation-event-bridge-null_mobile_light_en.png |  Bin 0 -> 2388 bytes
 ...valuation-event-bridge-null_mobile_light_zh.png |  Bin 0 -> 2100 bytes
 ...-event-bridge-restructuring_desktop_dark_en.png |  Bin 0 -> 3264 bytes
 ...-event-bridge-restructuring_desktop_dark_zh.png |  Bin 0 -> 4001 bytes
 ...event-bridge-restructuring_desktop_light_en.png |  Bin 0 -> 3327 bytes
 ...event-bridge-restructuring_desktop_light_zh.png |  Bin 0 -> 4016 bytes
 ...n-event-bridge-restructuring_mobile_dark_en.png |  Bin 0 -> 3265 bytes
 ...n-event-bridge-restructuring_mobile_dark_zh.png |  Bin 0 -> 3770 bytes
 ...-event-bridge-restructuring_mobile_light_en.png |  Bin 0 -> 3244 bytes
 ...-event-bridge-restructuring_mobile_light_zh.png |  Bin 0 -> 3719 bytes
 ...n-event-bridge-tender-offer_desktop_dark_en.png |  Bin 0 -> 4028 bytes
 ...n-event-bridge-tender-offer_desktop_dark_zh.png |  Bin 0 -> 5067 bytes
 ...-event-bridge-tender-offer_desktop_light_en.png |  Bin 0 -> 4102 bytes
 ...-event-bridge-tender-offer_desktop_light_zh.png |  Bin 0 -> 5102 bytes
 ...on-event-bridge-tender-offer_mobile_dark_en.png |  Bin 0 -> 4043 bytes
 ...on-event-bridge-tender-offer_mobile_dark_zh.png |  Bin 0 -> 4779 bytes
 ...n-event-bridge-tender-offer_mobile_light_en.png |  Bin 0 -> 3978 bytes
 ...n-event-bridge-tender-offer_mobile_light_zh.png |  Bin 0 -> 4705 bytes
 templates/_valuation_assumptions.html.j2           |   35 +-
 tests/test_valuation_event_bridge.py               |  583 +++++
 51 files changed, 10399 insertions(+), 3 deletions(-)
```

After, at `8dc43cbf5bd393506a481f566881320fb72b3891`, `git diff --stat origin/main...HEAD`:

```text
 .github/ci/legacy-jobs.yml                         |   29 +
 engine/valuation_assumptions.py                    |   74 +-
 engine/valuation_event_bridge.py                   |  318 +++
 mockups/evidence/b-f07-3-event-bridge/EVIDENCE.yml |   46 +
 .../b-f07-3-event-bridge/capture-metrics.json      |  317 +++
 mockups/evidence/b-f07-3-event-bridge/capture.py   |   42 +
 .../b-f07-3-event-bridge/contract-head.json        |   83 +
 .../b-f07-3-event-bridge/generate_hosts.py         |   32 +
 .../evidence/b-f07-3-event-bridge/green-final.log  |    2 +
 mockups/evidence/b-f07-3-event-bridge/heal-h4.md   |  200 ++
 .../hosts/valuation-event-bridge-null.html         | 2691 ++++++++++++++++++++
 .../valuation-event-bridge-restructuring.html      | 2691 ++++++++++++++++++++
 .../hosts/valuation-event-bridge-tender-offer.html | 2691 ++++++++++++++++++++
 .../evidence/b-f07-3-event-bridge/manifest.json    |   39 +
 .../evidence/b-f07-3-event-bridge/post-merge.stat  |   21 +
 .../evidence/b-f07-3-event-bridge/post-merge2.stat |   21 +
 .../evidence/b-f07-3-event-bridge/pre-merge.stat   |   21 +
 .../evidence/b-f07-3-event-bridge/pre-merge2.stat  |   21 +
 .../proposed-scope-amendment.patch                 |  139 +
 .../b-f07-3-event-bridge/real-issuer-final.log     |    3 +
 .../evidence/b-f07-3-event-bridge/red-2509328e.log |  147 ++
 .../evidence/b-f07-3-event-bridge/red-6e391cf1.log |   97 +
 .../evidence/b-f07-3-event-bridge/red_replay.py    |   16 +
 mockups/evidence/b-f07-3-event-bridge/smells.json  |   13 +
 mockups/evidence/b-f07-3-event-bridge/smells.md    |   30 +
 ...valuation-event-bridge-null_desktop_dark_en.png |  Bin 0 -> 2506 bytes
 ...valuation-event-bridge-null_desktop_dark_zh.png |  Bin 0 -> 2186 bytes
 ...aluation-event-bridge-null_desktop_light_en.png |  Bin 0 -> 2567 bytes
 ...aluation-event-bridge-null_desktop_light_zh.png |  Bin 0 -> 2265 bytes
 .../valuation-event-bridge-null_mobile_dark_en.png |  Bin 0 -> 2435 bytes
 .../valuation-event-bridge-null_mobile_dark_zh.png |  Bin 0 -> 2069 bytes
 ...valuation-event-bridge-null_mobile_light_en.png |  Bin 0 -> 2388 bytes
 ...valuation-event-bridge-null_mobile_light_zh.png |  Bin 0 -> 2100 bytes
 ...-event-bridge-restructuring_desktop_dark_en.png |  Bin 0 -> 3264 bytes
 ...-event-bridge-restructuring_desktop_dark_zh.png |  Bin 0 -> 4001 bytes
 ...event-bridge-restructuring_desktop_light_en.png |  Bin 0 -> 3327 bytes
 ...event-bridge-restructuring_desktop_light_zh.png |  Bin 0 -> 4016 bytes
 ...n-event-bridge-restructuring_mobile_dark_en.png |  Bin 0 -> 3265 bytes
 ...n-event-bridge-restructuring_mobile_dark_zh.png |  Bin 0 -> 3770 bytes
 ...-event-bridge-restructuring_mobile_light_en.png |  Bin 0 -> 3244 bytes
 ...-event-bridge-restructuring_mobile_light_zh.png |  Bin 0 -> 3719 bytes
 ...n-event-bridge-tender-offer_desktop_dark_en.png |  Bin 0 -> 4028 bytes
 ...n-event-bridge-tender-offer_desktop_dark_zh.png |  Bin 0 -> 5067 bytes
 ...-event-bridge-tender-offer_desktop_light_en.png |  Bin 0 -> 4102 bytes
 ...-event-bridge-tender-offer_desktop_light_zh.png |  Bin 0 -> 5102 bytes
 ...on-event-bridge-tender-offer_mobile_dark_en.png |  Bin 0 -> 4043 bytes
 ...on-event-bridge-tender-offer_mobile_dark_zh.png |  Bin 0 -> 4779 bytes
 ...n-event-bridge-tender-offer_mobile_light_en.png |  Bin 0 -> 3978 bytes
 ...n-event-bridge-tender-offer_mobile_light_zh.png |  Bin 0 -> 4705 bytes
 templates/_valuation_assumptions.html.j2           |   35 +-
 tests/test_valuation_event_bridge.py               |  583 +++++
 51 files changed, 10399 insertions(+), 3 deletions(-)
```

All 51 prior paths remain in the post-merge PR diff with byte-identical content (`git diff <pre-head> <merge-head> -- <each prior path>` is empty). Both stats are identical. SUPERSEDED: none. The merge only brings five base-owned data files.

## Evidence-head law

(a) `EVIDENCE.yml resolved_sha_or_none` is `8dc43cbf5bd393506a481f566881320fb72b3891`, equal to CODE_HEAD.
(b) The final evidence-only commit changes only `mockups/evidence/b-f07-3-event-bridge/`; the exact path list and exit result are pasted in the PR body after commit.
(c) `git diff --quiet 8dc43cbf5bd393506a481f566881320fb72b3891 HEAD -- templates/` exits 0.

## Deviations

The binding edit limits win over the reviewer requests outside those limits; BLOCKER 1 and MAJOR 1 remain open. No Ready/label/merge/production action was performed. The next action is a scoped amendment for the existing exact proposal, not an inferred authorization or a fabricated positive AAPL event.
