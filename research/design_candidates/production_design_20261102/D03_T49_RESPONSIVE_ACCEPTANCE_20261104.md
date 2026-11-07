# D03 / T49 — Prophet responsive and real-path acceptance contract

Status: **PARTIAL SOURCE EVIDENCE; NOT ACCEPTED**  
Date: 2026-11-04 UTC  
Programme: [D03 Phase 2A](D03_US_PROPHET_PHASE_2A.md), capability T49; 78 bounded capabilities / T01–T53.  
Commission: `D03-us-prophet.md` at immutable Macro `6e1862867193ec6486a22001a0e4fb515da20448`.  
Protected Mastermind source pin used for this return: `7aefe3fa3917faecf9b074a3033d37f6a4e7838a` (`mastermind.sol_skillpack.v1`, bootstrap major 1).

## Outcome sought

At 768/1024 physical CSS pixels and 1280px with *real* browser 400% zoom, a person can scan Prophet candidates, compare **two identities**, inspect full evidence and dates, view related Sources, and return to the same candidate. Navigation, the inspector, and the Ask Mastermind control must not obscure the action. No fixed desktop rail may silently consume the useful tablet content slot; tables/charts may have **scoped** horizontal scroll, but the document may not.

An offline card-width check is **not** this acceptance. Preserve both normal and missing/degraded market source states, unknown quote timestamps, entitlement boundaries, EN/ZH text and light/dark contrast. This is an evidence contract; it neither creates a new ranking/trading instruction nor authorizes release.

## Existing evidence to reuse — DO_NOT_REDO

1. Current separate rich-Prophet [Macro PR #9495](https://github.com/mastermindx-market-intelligence/macro/pull/9495) at `464152a01a9de0e42a14734863a96a170470a1b5` already has `mockups/evidence/prophet-opportunity-workspace/compact-sizing/observations.json` with **16/16 isolated-public-build layout checks passing**: viewport 1440/1024/768/390 × light/dark × EN/ZH. The 768 grid is 732px wide, two 358px tracks with 16px gap; 1024 is 988px wide, three ~318.67px tracks with 16px gap. No whole-page horizontal overflow was reported in those cases. `full-page-20261103/after/observations.json` contains four 768 captures with `documentWidth=768`, from an older recorded build generation `5370b9f...`. These are **source-linked offline measurements**, not current live, current-head or authenticated proof.
2. Live anonymous `https://www.mastermind-x.com/us_stocks.html` observed 2026-11-04 in ~1363×936 browser viewport, document width ~1353: Screener → PWR Setup detail → Evidence & source details → Close was usable. The disclosure showed assessment date 2026-11-03 and quote time **Not supplied**; stage/source type present, strategy/horizon **Not supplied**. Focus returned to Setup detail upon Close. The five-lane market action board was cramped at this width. This is one **public desktop disclosure slice only**, not T49 tablet or T52 paired release acceptance; no immutable screenshot was saved.
3. D03 Paper file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, page `p-D-0`, 768 light EN artboard `11NP-0` was created with header and hero. The source-unjudgeable 320/390 matrix remains. New empty row `11OR-0` was observed. First candidate-card operation `d03-t49-tablet-candidate-a-20261104-c2-v1` returned **EFFECT_UNKNOWN**; no candidate card appeared in same-carrier readback, but absence does **not** settle the effect. **Do not retry, rehome, replace or repair that logical edit** before original-carrier settlement. This artboard is incomplete and not a canonical RIG reference. The separate T45 controller 88972 / lease `5fdb1eb59a1f` and T51 controller 77735 / lease `b3b3dcfc93a5` are also independent effect-unknown runs; neither is retried here.

## Required acceptance scenarios

| ID | Viewport/state | Real action | Pass condition / evidence |
| --- | --- | --- | --- |
| T49-A | 768 portrait, light EN, full shell | Open nav, find a candidate, open details, close/return | Drawer accessible without hiding scan; one/two useful card tracks; dialog/drawer fits height; same candidate and focus restored; no document horizontal overflow |
| T49-B | 768 dark ZH with long company and condition text | Scan two candidates → compare by question | Two identities persist in each comparison question; terms wrap or use a **labeled scoped** local scroller; no truncated entry/invalidation/date or obscured controls |
| T49-C | 768 public/entitled and source-unjudgeable states | Detail → Sources → related Plan/unavailable → return | Source/assessment/quote clocks separate; unavailable strategy/horizon remain unknown; protected data never leaks; return preserves candidate/context without inventing a Plan |
| T49-D | 1024 expanded-nav and compact-rail variants | Scan first useful cards while opening inspector/source tab | 3-column sizing is **only a starting measurement**; actual content slot and inspector must remain usable, without overlay occlusion or unreachable tabs |
| T49-E | 1280 at actual 400% browser zoom | Keyboard-only scan, detail, close, compare | Reflows to narrow/approximately 320-CSS-pixel mode based on **measured content width**; no whole-page horizontal scroll or hidden primary actions; focus and 44px-equivalent touch targets where applicable |
| T49-F | All above, updated quotes/source clocks, reduced motion | Observe updates while inspecting, then back/forward | No card reorder stealing focus, no announcement flood, no stale-as-current labels; deep link semantics restored without silently mutating saved objects |

Run real interaction tests on **served candidate generation**, with a recorded page URL, exact deployed source/build identity, theme/locale/auth state, effective `innerWidth`, `documentElement.scrollWidth`, candidate count/identity, screenshots or video, and focus/navigation trace. Pair public/protected observations only with appropriate entitlement and access. A browser screenshot without generation binding is useful for diagnosis but cannot sign T52.

## Evidence precedence and current gates

- **PASS, narrow:** #9495 offline isolated card grid tracks at 768/1024 and two extra widths, EN/ZH × light/dark, as above. This is not a new D03 proof.
- **PASS, narrow:** live public desktop disclosure open/expand/close and focus return on the dated 2026-11-03 Prophet board.
- **UNTESTED:** 768 full scan→two-object compare→detail→Sources→return, 1024 inspector, 1280@400% actual zoom, reduced motion, signed-in save/reopen, full paired public/protected generation.
- **NO PROOF:** editable T49 Paper content beyond header/hero, immutable Paper export, F01/F02 joint-v1 admission, QA01/RIG approval, complete D03 acceptance or production release.
- **Tool boundary:** a local Chrome responsive navigation attempt timed out with a blank tab. The separate cloud browser explicitly denied DevTools by organization policy; no DevTools bypass, equivalent zoom measurement or pass is claimed. Do not relabel the failure as an application bug.

## Ownership and next safe work

D03 current successor owns this test/evidence contract. Rich Prophet #9495 retains its existing implementation/release custody and explicit holds; do not mutate its writer paths or reissue its offline captures. Before another Paper write, reconcile exact `11OR-0` candidate edit under the original native Paper carrier and resolve the observed Rectangle/container mismatch. Next implementation/acceptance work after those gates: use existing rich-card artifacts, wire/verify a genuinely full T49 two-object tablet journey and real 1280@400% reflow, then record immutable result and carry it to QA01/RIG. Keep #10617 Draft/HOLD and all current merge/enqueue/Ready/un-draft/deploy/purchase restrictions.

**Canonical cumulative successor checkpoint:** [Macro #10617 comment 6630329488](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6630329488). Do not treat this addendum as acceptance of T49 or the parent D03 programme.

## November 4 recovery continuation — exact scoped readback (not acceptance)

This addendum updates the *status* of the evidence gates; it does not replace the immutable earlier tests or claim a current deploy.

- Macro rich-Prophet [#9495](https://github.com/mastermindx-market-intelligence/macro/pull/9495) was verified open **Draft/HOLD** at exact head `e5c288011f026cb74b2a2e265d6dfc767359565d`. Earlier `464152a` references in this document remain historical baselines. Save visual fixture receipt `22abd622`, P0B/G7 screenshot retention `76b5cb9`, and EW-P4 68-case recapture `e5c2880` are published, with preserved older history. The original Save Fabric run `d03-pr9495-save-visual-proof-20261104-c2-v1` is **TERMINAL rc=0 / formally ACCEPTED** after same-run response-digest and original evidence-file SHA comparison; its 128 cells are anonymous fixture evidence, not signed-in proof. Exact return: [#9495 status/acceptance](https://github.com/mastermindx-market-intelligence/macro/pull/9495#issuecomment-6639878644).
- The remaining native public/Essential pair is **NOT ACCEPTED**: November 2 `us_standouts.json` vs November 3 `signal_gate.json` have 103 ticker mismatches. The single original Fabric run `d03-pr9495-native-pair-publication-20261104-c2-v1` remains `ACTIVE_OR_WAITING`, worker state `UNKNOWN`, no terminal result, verified root or retry authorization as of the 19:35 UTC readback. The existing `D03 Native Pair Return` watches this original run. Do not duplicate dispatch, treat controller polling as proof of STARTED execution, copy unrelated pairs, or hand-restamp dates. Reconcile original result; then validate all required native modules, 12 integrity cases, build/source/Plan consistency and exact-head hosted CI.
- Direct exact-file Paper read on the existing PROPHET `01M3NT5Y3G5HTJHVR0K5W2MDJM` found T49 draft artboard `11NP-0` has exactly three immediate children (`11NQ-0`, `11O7-0`, `11OR-0`). `11OR-0` still reports `Rectangle`, `childCount=0`, `childIds=[]`, under `11NP-0`; read token hash `640746f9`. This is a *current visible absence* of the candidate-card child, **not settlement** of original operation `d03-t49-tablet-candidate-a-20261104-c2-v1` with `EFFECT_UNKNOWN`. No Paper edit or replay was performed. Keep the overlapping target held and preserve the source Paper R7 boards.
- `ci-authority/main` for `e5c2880` is successful; the inactive merge-queue-pilot context is expected-deny, not a main CI failure. Full binding exact-head CI/fences, served 768/1024/two-candidate, 1280 physical @400% zoom, auth Save/list/reopen, Sources→Plan→same candidate and final visual review are **still owed**. No release, Paper reference approval or T49 acceptance is inferred.

**Next exact actions:** (1) consume and verify the *original* native-pair carrier upon terminal/root-verified evidence; repair its documented 12-case/source consistency failures only if necessary, with one writer; (2) regenerate the coherent board/gate on the same native source and qualify full CI; (3) run served/browser T49 scenarios and signed-in round trip through an authorized carrier; (4) reconcile the original T49 Paper operation before any overlapping canvas edit, then obtain proper joint F01/F02/RIG qualification. Keep #9495 and #10617 Draft/HOLD, with no merge/enqueue/Ready/un-draft/deploy/purchase.
