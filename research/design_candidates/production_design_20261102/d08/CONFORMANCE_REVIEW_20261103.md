# D08 — repaired integration specimen and foundation reconciliation

**3 November 2026. Existing Draft #10649; design/research only.** The semantic common interface remains **D08-OPTIONS/1.0.0**, frozen at `d0516e1bad9cb5982d43d20c4167d0355cb70e2c`. This continuation corrects the detached review specimen against that interface. It does not release the joint foundation, finalize D08A–D08D, implement product code or change their owners.

## Actual result

The earlier ten static checks were insufficient to establish prototype conformance. A new regression run against the original attachment produced **3 passes and 15 failures** across the initial 18 function/source assertions. The repaired specimen now passes **50/50 function/source checks**. A separate foundation calculation passes **22 assertions across 23 width cases**, including assertions that detect the still-unresolved F01/F02 differences. JavaScript syntax and exact gzip round-trip also pass. Node version: **22.16.0**.

These are **Node VM function tests, static source checks and geometry calculations**, not DOM/browser behavior. The VM executes the specimen's actual data/formatting/route functions using minimal string-output element stubs; it does not simulate browser layout, focus or accessibility. Full browser interaction remains unverified. This continuation does not retry the earlier `ERR_BLOCKED_BY_ADMINISTRATOR` navigation or bypass it with another route.

## Repairs made in the detached specimen

| Defect in the earlier specimen | Corrected behavior |
| --- | --- |
| Selecting NVDA relabeled SPY rows and evidence | The fixture is explicitly SPY-only. Another root withholds its rows/metrics and reports that no matching fixture exists. A root change invalidates inconsistent origin context. |
| Reported zero was treated as missing; null could throw | Finite zero remains `0.0M`; null, NaN and Infinity are unavailable without an invented suffix. Missing comparison legs never become zero. |
| Every selected strike used the same previous value | Each row carries its own earlier/current observations. Signed change is calculated only from two finite values. |
| “15 views” omitted Surface, Positioning and Levels | All 15 true native panes are represented with exact page keys. Plan, nested 3D and the two replay destinations are separate task/destination entries, not substitute panes. |
| Screener/volatility and aliases could be conflated | `vol` and `screener` resolve to Screener; `volatility` remains separate; `prism` resolves to GEX; unknown native tabs default to Tape. No speculative Plan route is created. |
| Table control only dimmed chart bars | It now emits a real exact-value table with caption, scoped headers, selected-row evidence buttons, all seven fixture rows and explicit unavailable cells. |
| Evidence could outlive an invalid state | Loading, no results and permission loss withhold affected values. Refresh failure retains only same-root, explicitly dated observations. |
| Arbitrary bars and inconsistent sample counts | One disclosed absolute scale is derived from finite values. Five matched pairs out of seven fixture rows are reconciled; zero and missing marks remain distinct. |
| Fixed viewport docking and stale focus references | The specimen measures usable host width and docks only at C >= 984. Source logic restores by stable strike identity and reconciles modal/inert state on presentation changes. Those source rules still need real browser tests. |
| Plan authoring implied an exact contract when only a coordinate existed | Draft creation and Save remain disabled without an admitted contract identity and the incumbent native Investigation/D23 persistence path. |

All values are **illustrative design fixtures**, not current market observations or trading advice. Current/earlier research, chain/book, spot, transport and hypothetical inputs remain separately labeled. The seven-strike sample is not a full options book, and a matrix coordinate is not a uniquely identified option contract.

## Actual source retention

The pane catalog and aliases were read from Terminal `3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9`:

- `terminal/lib/optionsIa.ts`, Git blob `385821bff793ca49c62a7308e564b2a990c4d60a`.
- `terminal/components/workspaces/OptionsWorkspace.tsx`, Git blob `9ba9883fb5a37da7d0bf785eefd2a1f35f1cdcc1`.

The canonical panes are desk, tape, tide, zero_dte, largest, surface, screener, tickers, gex, positioning, levels, structure, volatility, statistics and prophet. Stable page keys preserve `0dte` and `vol`. Nested research remains a GEX seam. Equity replay carries only its admitted symbol key; futures does not infer ES/NQ from a stock root. Existing leaders/radar/fundamentals relocations remain in the frozen source ledger.

A retained specialist entry provides its actual incumbent route and states that the prototype selection is not transferred. It does not pretend to implement the domain-owned workflow or append an unsupported query key.

## F01/F02 differences that prevent a joint freeze

F01 **F01-F02-SHELL/1.0.0-candidate.1** was read at `b2d00ddc7e2dfbffdc3c5855e1a4dffe8c4226a5`. F02's concurrence was read at `f7c25c4b9870cff260c2a4b998be18d6c04d36d0`. Candidate concurrence is useful but is not a qualified joint release.

| Concern | F01 candidate | F02 concurrence | Observable difference |
| --- | --- | --- | --- |
| Narrow/tablet content gutter | 16px below 768 | 16px through 600, then 20px | At 640px: usable content 608 versus 600. The 8px disagreement persists for 600 < width < 768. |
| Non-phone modal inspector | Up to 400px | 440px at represented 768/1024 widths | 40px different evidence compositions. |
| Middle rail interval | Literal 861–1199 | Continuous >860 and <1200 proposed | Fractional 860.5/1199.5 needs explicit F01 resolution. This is a contract ambiguity, not a measured production browser defect. |

Both agree on 224/196/72/0 rail roles, a 320px dock plus 24px gap, at least 640px primary content, user-selected compact navigation and measured usable C >= 984. Default expanded docking begins at1256; compact begins at1096 under these candidate gutters. Local reserved chrome must still be subtracted. The specimen uses **F01's gutter and 400px modal proposal provisionally**; this is not silent agreement by F02.

The exact consumer discrepancy was delivered to the incumbent F01 owner in [comment 6597852782](https://github.com/mastermindx-market-intelligence/macro/pull/10645#issuecomment-6597852782). F02's separately unresolved native request and first Product/Taste BLOCK verdicts remain in force; no D08 test clears them.

## Reproduce the source checks

Run from this `d08/` directory:

```sh
node checks/verify-prototype.mjs prototype/review-v2.html.gz
python3 checks/verify-foundation.py
python3 -c "import gzip,pathlib; pathlib.Path('review-v2.html').write_bytes(gzip.decompress(pathlib.Path('prototype/review-v2.html.gz').read_bytes()))"
```

The archive contains the complete, self-contained UTF-8 HTML review specimen; no network assets or production imports are needed. Compression is a source-artifact container, not a deployment or runtime dependency. The checker accepts either the archive or extracted HTML. Current gzip bytes are15,808; extracted HTML is54,492 bytes with SHA256 `491232457d61de737504fdcaee1432df1b6e7c5eb20bb19231cae4d0162694e6`.

[Machine receipt and exact artifact hashes](evidence/conformance-results.json) distinguish all evidence classes. The original failing attachment, its full red report and the extracted repaired HTML are included in the conversation's downloadable continuation bundle. The original attachment is not part of this Git commit; its SHA256 is pinned in the receipt. Current repaired-source verification and foundation comparison are independently reproducible from this branch alone.

## Remaining acceptance and exact successor actions

| Lane | Current evidence | Next action / owner |
| --- | --- | --- |
| D08 common interfaces and source retention | Published frozen contract; conformance repairs and repeatable checks now added | Existing D08 owner retains the same source branch and consumes only material domain/foundation changes. No D08A–D08D session is launched by this return. |
| Joint foundation | Concrete F01 candidate and F02 concurrence, but two incompatible dimensions and fractional interval ambiguity | Existing F01/F02 authors resolve those exact values in a versioned joint record, then provide final native artifact/review identity. |
| Native D08 composition | Last confirmed target remains an empty1440×900 frame: Terminal file `01M3NSZGE8JWN2EZCSF0DT05RM`, page `p-2-0`, artboard `1N2L-0` | The prior content operation `d08-paper-shell-desktop-20261103-02` was safety-refused. No retry, alternate carrier, equivalent replacement or delegated bypass is permitted. No native content was attempted in this continuation. |
| Separately owned slices | Common input/output contract frozen; no new slice return consumed here | When legitimately assigned, D08A/B/C/D return their own retained-feature compositions, failures, source contracts and exact evidence. Their finalization is not delegated or performed by D08. |
| Browser, locale and access | Source handlers and EN/ZH candidate labels exist; paid normal-path, keyboard/touch, contrast, 400% and full copy proof are absent | QA01 and the authorized product/access owners qualify the actual assembled reference. English-only supporting copy still needs locale review. A static source PASS is not an accessibility verdict. |
| Persistence and actions | Plan remains disabled; no backend save or trade effect | Native Investigation/D23 demonstrate exact owner-bound save/readback/reopen and uncertain-outcome reconciliation; D22 holds personal positions. |
| Reference review / release | No D08 independent design approval; PR remains Draft | Freeze actual native/composed artifacts and obtain the existing independent reference/QA01 decision before any separately authorized production implementation. |
| Hosted CI | Earlier frozen-head run41590374570 failed `unsupported_base_ref` on the stacked programme base | Preserve stack and held controls. Do not use local50/22 checks as hosted CI or retarget for cosmetic green. A later lawful release-base integration needs fresh exact-head CI. |

**Acceptance remains PARTIAL.** The source-conformance repair is evidenced; full native design, cross-slice composition, implementation, deployment and user-path acceptance are not claimed. The shared return ledger and other source/canvas writers are untouched.
