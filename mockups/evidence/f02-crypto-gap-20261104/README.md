# F02 crypto producer gap proof

This evidence covers the actual crypto producer and shared illustration paths on
explicitly synthetic inputs. **81 existing tests pass, 24 browser cells pass,
and all eight final screenshots were visually accepted by the root session.**
It does not establish live-data correctness, an authenticated crypto route,
deployment, or full-route acceptance.

## What was exercised

The fixture uses normal imports of the actual `engine.crypto_universe` and
`scripts.build_crypto` modules. The deep-history cases supply dated synthetic
frames at the existing store-read boundary and call `_enrich_universe`. The
legacy case writes the retained Parquet input, calls `load_universe_snapshot`,
and passes the resulting row through `_enrich_universe`. The actual shared
renderer produces the resulting chart markup; producer outputs are retained in
`producer-results.json`.

| Synthetic case | Available observations | Retained date slots | Missing slots | Connected runs | Latest supplied slot |
| --- | ---: | ---: | ---: | ---: | --- |
| Deep history, internal gap | 90 | 93 | 3 | 2 | Available |
| Deep history, unavailable tail | 90 | 94 | 4 | 1 | Unavailable; last observation October 31 |
| Legacy Parquet, invalid-value gap | 90 | 94 | 4 | 2 | Available |
| Complete baseline | 90 | 90 | 0 | 1 | Available |

The exact synthetic frames are in `fixtures.json`; the actual legacy input is
`inputs/legacy-invalid-gap/market_f02alt.parquet`. Each producer output is shown
at 96, 140 and 240px widths with a 42px chart height: 12 charts per page. Missing
slots retain their date positions and separate the line runs. An unavailable
tail retains the complete supplied date window and identifies the last observed
value/date. Compact visible status stays outside the plot and switches between
English and Chinese; the full metadata remains in the accessible chart name.

## Source identity

The fixture's source base remains
`6e245059af5870d35eb48e34d641e50f38617cc1`. This is a **base revision**, not a claim
that the modified implementation already existed at that commit. Exact current
implementation bytes are bound by `source-provenance.json` and the fixture's
loaded-source hashes. No unknown future containing commit is embedded in this
receipt.

- All 11 source publication candidates match the preparation record's byte
  lengths, SHA-256 hashes and Git blob IDs.
- All 20 loaded module hashes, four generated page hashes and ten asset hashes
  match the actual local fixture inputs. Template and site illustration CSS are
  byte-identical.
- `fixture-manifest.json` is preserved unchanged, SHA-256
  `367681171ee8bb049e7372eb07673e7b0d6b10b06a022d811082255b1ed89810`.
- `producer-results.json` is preserved unchanged, SHA-256
  `f274ece2c7c57510786607f23c46b49235bb08755e8355029a50e88b32e2a937`.
- The fixture manifest retains its preparation-time browser-readiness field.
  The later complete browser report and root visual review supply the finished
  observations; historical preparation fields were not rewritten.

Generated HTML is retained in `rendered-pages/`. Its styles, JavaScript and six
existing Inter font dependencies remain bound in the fixture manifest and can
be materialized by the existing generator. The HTML archive alone is not a
standalone server or a live route.

## Completed browser and visual observations

The actual Chromium browser was **151.0.7922.34** on macOS 26.5 arm64. The
temporary fixture origin was `http://127.0.0.1:53430`. The canonical capture
tool was `scripts/capture_page_evidence.py` v1.4.0, SHA-256
`9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`.
The capture was generated at **2026-11-04T20:27:19Z**.

The capture manifest's actual parsed fields are preserved, including the null
origin commit resolution. An HTTP origin does not disclose its serving commit;
the separate source hashes provide the binding. All eight PNG files retain
their exact transferred bytes, manifest SHA-256 values and dimensions.

The root session reported direct visual inspection of **all eight final images**:
both themes, EN/ZH, and desktop/mobile were clean, with no clipping or overlap.
`visual-review.json` attributes this review to the root and does not invent a
separate review timestamp. No independent review ceremony is claimed.

| Capture | Exact PNG | Dimensions |
| --- | --- | --- |
| Desktop / EN / dark | [d2b75f830368fc16.png](evidence/d2b75f830368fc16.png) | 1440 × 1072 |
| Desktop / EN / light | [0dbe1b5390d15946.png](evidence/0dbe1b5390d15946.png) | 1440 × 1072 |
| Desktop / ZH / dark | [0e5a646c9657a8bc.png](evidence/0e5a646c9657a8bc.png) | 1440 × 1060 |
| Desktop / ZH / light | [f2996d910e97a457.png](evidence/f2996d910e97a457.png) | 1440 × 1060 |
| Mobile / EN / dark | [5aea1ce908190a8b.png](evidence/5aea1ce908190a8b.png) | 390 × 2574 |
| Mobile / EN / light | [4f45cf742371d940.png](evidence/4f45cf742371d940.png) | 390 × 2574 |
| Mobile / ZH / dark | [15f2ffad44b692ac.png](evidence/15f2ffad44b692ac.png) | 390 × 2409 |
| Mobile / ZH / light | [bd06d399e01cb498.png](evidence/bd06d399e01cb498.png) | 390 × 2409 |

The complete `browser-checks.json` was recovered from the existing remote result:
**14,659 lines, zero remaining**. It records **24/24 passed** at widths
1440/390/320 × dark/light × EN/ZH × normal/reduced motion, with **288 chart
observations** and no recorded failures. The browser checks use the natural
reveal-on-scroll variant rather than the settled-image preparation. They check
loaded fonts, no horizontal overflow, accessible names, producer missing-slot
and line-run semantics, retained historical endpoint position, localized status,
compact status geometry and settled/reduced-motion ink.

The report was generated at **2026-11-04T20:29:01.366941+00:00**, checker SHA-256
`ed76c50e12db029c2318f760398618b3927a950a754f30f5e13a00be22526b3b`.
Its complete saved SHA-256 is
`4d740c483b83dd300989324f212d33c0bdae8e64fa145fac6d604a3bd61c1f21`.

`smells.json` reports zero console errors, no elements wider than the viewport,
and no horizontal overflow. The capture manifest records no failed responses.
Its repeated heading labels are the deliberate 96/140/240px specimen headings;
its missing page-level source/as-of heuristics concern the synthetic comparison
page. These are lab observations, not production telemetry or live feed proof.

## Existing test result

`test-results.xml` is the unchanged combined JUnit result: **81 passed, zero
failures, errors or skips**. Its SHA-256 is
`450ee6ee566d40c10b4750441039f1842fcb96cc4efc5c704f72ccd8953e774d`.

| Module | Passed |
| --- | ---: |
| `tests/test_illus.py` | 62 |
| `tests/test_crypto_chart_gaps.py` | 7 |
| `tests/test_crypto_legacy_chart_gaps.py` | 12 |

`producer-test-provenance.json` retains normal-import origins, exact dependency
and source hashes, package versions and the original test command. Evidence
assembly did not rerun tests or browser checks. No separate saved differential
baseline receipt was found in the bounded local evidence paths; no such result
is claimed.

## Remaining limits

This package proves the scoped synthetic producer/component behavior. Authenticated
access tiers and loading/empty/stale/error page states are explicitly uncaptured
in the capture manifest. Full live crypto-route journeys, production data,
deployment, and broader F02 acceptance remain separate. The 320px browser checks
are not a claim of 400% browser-zoom testing.

The existing three-key `EVIDENCE.yml` contract points to the actual capture
manifest and names the five changed production paths. `assembly-verification.json`
records the local hash/count checks without adding a new runtime or approval
ledger. Root remains responsible for publishing the source and evidence together
and reading back the resulting immutable commit.
