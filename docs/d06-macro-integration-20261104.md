# D06 Macro — integrated implementation and final locale proof

## Outcome

The original D06 branch integrates protected main **a8a5d3523614777d88eb2579d6efab52cd862e33** at merge commit **4ac468b3a552559ec20afa14e71b19ea3a1ae680**, with parents D06 **ede62cbbc69441aca64973ee638c55be544cfc4d** and that protected main. The typed publisher accepted the prepared tree **cd20a7b86184173ab4836d406d8f890b7643dece** and returned APPLIED with a clean, synchronized worktree.

The two generated-page conflicts were resolved through their existing builders. That integration left the D06 templates and generators unchanged. Final visual inspection then identified a separate locale-color defect in Market Structure: the Chinese long and short dealer regimes used two red shades. A one-line template repair now uses the existing shared `--down` token, with the prior local token as fallback. Market Structure was rebuilt through its existing owner; the generators, shared theme, data, calculations, observations and regime classifications are unchanged.

[Composed verification](pr-crops/d06-macro-integration-20261104/verification.json) · [Integration phase before the color repair](pr-crops/d06-macro-integration-20261104/integration-before-locale-fix.json) · [Final locale proof](pr-crops/d06-macro-integration-20261104/market-locale-fix/verification.json) · [Artifact inventory](pr-crops/d06-macro-integration-20261104/manifest.json).

## Integration and data scope

Main advanced while the branch was being prepared. The integration carries 4,884 changed paths relative to the preceding D06 head, primarily main's generated data and site outputs. Only Market Structure and S&P Vector required generated-page conflict resolution. Stage Analysis HTML is byte-identical to the prior D06 output. The CI registry merged cleanly to retain main's existing Agent OS checks and all three D06 test registrations.

The page inputs were first bound to **eb312bea9cbbc7550b157c071fbb41dea990321b**. The subsequent Oracle update at **079ba10fe079ddf947cb446afeae65ff2908046e** and Agent OS update at the final protected base changed none of the 415 checked page inputs. The Agent OS change belongs to its existing exclusive CI owner; the three packing probes do not select it. D06's three measured weight-ceiling calibrations remain exactly +4 each; job membership, job count, pack count, runtime limits and selectors remain unchanged.

A partial clone lacked 48 incoming Oracle blobs. Their exact bytes were recovered through the existing GitHub read connector and every Git blob identity was verified. A slow preparation process was terminated and its two applied files reconciled before continuation. A later process-start transport timeout was reconciled at the original host: no active session, cache or result existed. The retained recovery receipts distinguish these events from publication. The existing branch, operation and typed commit/push carrier remain the owners.

Market Structure renders the incoming artifact's **2026-11-03** observation date and **2026-11-04 08:22 UTC** build timestamp. Net GEX is −44.185835bn, supplied spot is 7568.9199, flip is 7654.546915, and COR1M is 16.39. The supplied weekly locked close of 7580.07 and independent 1σ/2σ bands are unchanged. Incomplete gamma coverage remains explicit.

S&P Vector's existing page-only builder produces score **33**, mechanical equity weight **100%**, cash weight **0%**, and contributor/allocation dates **2026-11-03**. The recorded shadow log contains **435 records across 81 model dates**, ending November 3, with no recorded veto. Page-only mode performs no new shadow evaluation and displays that no current shadow assessment is available. The recorded shadow output does not change allocation, score or backtest.

The 398-file S&P input closure remains complete. Only regime history and the recorded overlay log differ from the earlier 52abe2e snapshot; price data is unchanged. All 415 checked inputs retain their hashes through integration rendering, browser proof and the final locale repair. No auxiliary producer output was written.

## Verification by phase

| Phase | Verified result |
|---|---|
| Integrated Market and S&P suites | 27 passed; overlaps the earlier 253-test phase |
| Both regenerated pages | Executable inline scripts and handlers parse |
| Merged CI registry | Existing validator exits 0 |
| Integrated Market browser matrix | Six contexts and two gap/zero/missing-data cases passed |
| Integrated S&P actual data | Desktop EN and phone ZH passed, including score, allocation, dates, shadow summary and synchronized Plotly ranges |
| Integrated Stage published data | Desktop EN and phone ZH passed; all 12 independent readers requested once per context |
| Final locale regression | 85 affected Market tests passed; overlaps the earlier suites |
| Final Market browser matrix | The same six contexts and two edge cases passed after the color change |
| Final locale-color probe | Four contexts; all 75 bars match their locale palette in each context |
| Final canonical Market captures | 24 cells: 8 rest, 8 hover, 8 focus; desktop/phone × EN/ZH × dark/light |

The locale probe first reproduced the defect against the integrated source: 50 long bars used the correct Chinese red, while 25 short bars used the legacy local red instead of the shared Chinese green. An initial diagnostic incorrectly expected a single red shade; its failed assertion is retained. The corrected baseline records both red shades. After the repair, every one of the 50 long and 25 short classifications is retained and matches the shared locale colors in all four probed contexts. No observations were removed or reclassified.

The final color probe covers desktop dark EN/ZH and phone light EN/ZH. The separate canonical matrix covers both themes at both viewports in both locales. The canonical hover/focus records establish trigger application; settled phone-help visibility remains supported by the prior dedicated viewport observations and unchanged help CSS. These forms of evidence are not interchangeable.

Root visual QA inspected the integrated desktop/phone samples of all three pages and the final Chinese desktop and phone color screenshots. The final chart retains its observations, zero line, price/flip distinction and readable layout. Emulated-browser reflow and interaction assertions passed. The final design-token and visual-evidence guard receipts are recorded with the composed verification.

## Evidence integrity and limits

The integration phase's 12 runtime screenshots and source binding are retained as historical evidence. The final Market screenshots and 24 canonical captures bind the repaired source separately. The original 63-member implementation proof and 204-member CI/visual proof remain byte-identical, including the earlier 72 canonical captures and settled phone-help observations. Test counts and repeated captures overlap; no combined unique-test total is claimed.

The first CI-manifest invocation omitted its required workflow argument and exited 2 before validation. The corrected invocation supplies `.github/ci/legacy-jobs.yml` and exits 0. Both results are retained. Whitespace diagnostics report generated blank-line indentation inherited from existing templates plus historical log whitespace; this work makes no whitespace-clean claim. No repository guard or behavioral assertion was disabled.

These are local browser journeys and emulated viewports bound to the recorded source and inputs. They do not establish physical-device behavior, live-feed completeness, production acceptance or model/backtest recertification. The broader 75-case migration ledger remains only partially exercised.

[Draft PR10734](https://github.com/mastermindx-market-intelligence/macro/pull/10734) remains the sole implementation publication carrier. Its final published head and exact hosted-CI readback are maintained in the PR body and canonical D06 return. Local checks do not imply hosted-CI success. Ready/enqueue/PR-merge/deployment and joint-shell rollout remain held. The ancestry integration did not merge the PR or deploy a site; original F01/F02 uncertain effects remain untouched.
