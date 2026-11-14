# Paper refinement — count scope, Dossier opening and evidence clarity

Date: 9 November 2026. Governance remains Mastermind `5c3d3885234358aefb97ecdbc59be0864df14f8b`.

This is the next owned design delta after [PR #10872](https://github.com/mastermindx-market-intelligence/macro/pull/10872), whose current frozen head is `376bc2cee3641eb7f55b113210be916a8a0f85d7`. That package and its CI remain independent. No previous accepted evidence is replaced.

## News source-filter recovery

[Paper · States and user help](https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH/p-1-0), artboard `QO-0`, frame `YN-0`.

The selected source is GlobeNewswire, the aggregate strip shows 13 reports in 24h, and the filtered story list is empty. The existing builder annotation correctly says the strip counts all accessible sources. The previous product basis line did not make that distinction explicit.

| Node | Previous | Applied |
| --- | --- | --- |
| `Z8-0` | Counted 02:35 AM · 2 sources | Counted 02:35 AM · all 2 sources |
| `ZC-0` | “· 2 sources” states the count basis while a filter narrows rows | Count basis stays across all accessible sources while the filter narrows stories. EN: “all 2 sources” · ZH: “全部 2 个来源”。 |

Only these two existing Text nodes changed. The exact JSX delta matches those replacements; all other frame bytes are unchanged. Both Text values were read back from node information, the 360px postimage was visually inspected, and `QO-0` was released. The product line fits on one line. The builder annotation is outside the product frame.

**Builder rule:** the source filter controls displayed story rows. Keep the aggregate count, its publication-time window, and its counted-source coverage under their existing owner. Localize the aggregate scope as “all N sources” / “全部 N 个来源” in this filtered recovery state. Do not relabel the aggregate as zero or infer that every included source supplied a report. No runtime copy, calculation, filtering, or review effect changed here.

**Preserved after bounded review:** current News Activity `3J1-0`, Counted sources EN/ZH `3LA-0`/`3OK-0`, and How counts work EN/ZH `3LV-0`/`3P2-0` already distinguish reports from stories, covered sources from contributing feeds, rolling 24h from daily UTC history, and no-record chart regions from the producer's zero-filled baseline. No change is justified on those destinations. This review does not independently verify the producer.

Options mobile candidate source details `B7-0` also remains unchanged: supplied record time, missing quote/receipt timing, tick-rule method, missing print count, calculations and the Contract activity return are coherent. It remains a design candidate, not a newly accepted primary view.

## Evidence

`before/` and `post/` retain exact inspected JSX. `proof/` contains the before and after Paper render. `EFFECTS.json` retains the original edit and release receipts; `VERIFICATION.json` records exact Text readback, scope and limitations. Paper proof does not establish browser behavior, accessibility-tree behavior, runtime acceptance or production deployment.

## Risk Radar desktop method horizon

[Paper · Main and Evidence](https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z/p-1-0), evidence artboard `8PS-0`, method Text `8QV-0`.

The top model explanation at `8QB-0` names the next 21 closing observations, but the method paragraph called it “21-day model risk.” The applied text now says “model risk over 21 closing observations.” The entire remainder is unchanged: 17.8% rounded to18%, the0.73× comparison rather than exposure size, unverified calibration and separate driver scales.

The exact JSX comparison contains this one Text replacement only. The full 1240px postimage is readable without clipping, and the original Text readback matches. The artboard was released. The current light-English `98K-0` and dark-Chinese `9AI-0` siblings already name closing observations and omit this method paragraph; no paired translation change was necessary. The previously accepted `8SH-0`/`8ZF-0` mobile corrections, `AZL` build reference, retained21D cohort, #8186/#7647 boundaries and every numeric fixture remain intact.

This correction uses the already accepted native-SPY target from F05/R5 of PR#10872; it makes no new model, calibration, market-risk, exposure, runtime or production claim. No extra diagram was added because the existing explanation already states the comparison and its limits.

## News review architecture and worked illustration

Added card `414-0` and original native SVG `417-0` to the existing `3H7-0` News Build reference. It explains the independently supplied report count, source-filtered story counts, review-filtered visible set, exact Mark shown targets, and the current-presented-page receipt. Seven Text nodes were read back exactly; all preexisting children and the complete previous JSX prefix were preserved. The 612px card was visually inspected and its parent released. `BUILD_EXTENSION.md` provides source links, implementation boundaries and a concrete acceptance fixture. Four source files were independently read at both pins and are byte-identical.

The follow-save references `AJV-0` remain future references. Their four language/theme variants correctly identify a lost reply as an unknown result, direct the user to inspect the original request, and offer return without automatic resubmission. No runtime capability was inferred and no patch was needed.

**This continuation:** twelve observed Paper operations, seventeen exact final Text readbacks, seven inspected renderings (six captures in the final manifest), no unresolved canvas effects. The original package's counts and files remain frozen in#10872.

## Sector Dossier opening contract

Added `HBL-0` to the existing `GYT-0` Build reference, with seven exact Text readbacks and an inspected1000px rendering. The previous child IDs and entire preexisting JSX prefix remain exact. The new contract distinguishes accepted Cycles navigation from an actually opened, qualified inline Dossier. It names the existing entry state, refreshDossier, selection/publication guards, onOpenCycles return and separate Central return. The Energy/Technology case requires the actual requested subject to appear, rejects stale/default substitution, and keeps GPL's ordered return as proposed work. Both dependency PRs remain draft/open/unmerged; none of their source, review or acceptance controls changed.

The News card's final scope wording now explicitly uses Feed total when a review-state filter is active, while a source-only recovery may use its existing all-N-sources basis. Its earlier inspected rendering remains at commit35cc0249ffd94b8a1ab88b210fa9e500cce34235; the current manifest retains the final rendering.
