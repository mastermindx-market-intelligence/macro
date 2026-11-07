# Independent public-navigation repair and R7 source review

**Disposition: SOURCE PASS for the bounded repair and R7 delta. No concrete blocker found. Actual R7 browser acceptance remains pending.**

Reviewer: `/root/bridge_release_critic`. Date: 2026-10-19 UTC. Scope: exact local parent-transferred candidate/source/evidence bytes, selector topology, existing publication ownership, and R7 assertion/source/effect continuity. This is independent reasoning and local byte verification, not independent retrieval from M2. No browser, server, remote operation, application edit, Git operation, or publication was performed in this review.

## Exact reviewed identities

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Product `source-repair.patch` | 3683 | `3803a2109784c8dedc83b527424a08f769df42da4693b7cd2469a1018e53bd19` |
| Product `handoff-manifest.json` | 2673 | `599af6bdc9b47abeda40bd0938d1bf898d77af688c7cb034829ae9882ff40e5f` |
| Canonical and emitted `shared_shell.css` | 509 each | `8c102aa390969828d0d82c9b2f58d88cf9078c227259c1eae5fcd4ac10cc6c86` |
| R7 `transfer-manifest.json` | 2781 | `f22a4315265052b768326777e99a216356d422761f88bc64e6d87c2cc0106678` |
| R7 `kit/qualify-shared-shell.cjs` | 52762 | `37ce15a42591830aa6ae4ecb29fb16a3a80dfd084939daf6a0ee961676979de4` |
| R7 `wrapper/attend-qualification.py` | 12333 | `9e9324f347f582d7baee41d0132c5d0535befd1798f3b9b9b91f013680149de7` |
| R7 `kit/README.md` | 21154 | `b739553f0afa2736132f0e204b35071e0f1e1696995b206d751d1ae05c75b63d` |

Product root: `/workspace/scratch/867a035678c0/shared-shell-public-nav-suppression-repair-20261019`.

R7 root: `/workspace/scratch/867a035678c0/shared-shell-local-browser-review-r7-20261019`.

Actual R6 evidence root: `/workspace/scratch/867a035678c0/shared-shell-r6-actual-diagnosis-20261019`.

## Findings

### 1. The product change addresses the observed component without broadening suppression to page landmarks

The complete four-path source patch was independently reconstructed from `original/` and `work/` and matched the frozen patch byte-for-byte. The CSS change is exactly one added selector; removing that line recreates the original stylesheet. Both canonical and emitted CSS copies have the same 509 bytes.

At `work/templates/shared_shell.css` line 6, the selector is `html[data-mmx-shared-shell="1"] body > nav.nav[aria-label="Main"]`. It requires the existing shell activation flag, a direct body child, the `nav` element and class, and the exact Main label. The existing `display: none !important` rule remains at line 8. No bridge lifecycle or JavaScript change accompanies it.

An independent lxml parse of the exact About source found precisely one match at `work/templates/about.html` line 152, with parent `body`. The breadcrumb at line 251 is `nav.ab-crumb[aria-label="Breadcrumb"]`; the content at line 259 is `main.ab-main`; the article header at line 261 is `header.ab-sec.ab-mast`. All three are outside the matched navigation element and cannot match the added selector. The rule remains dormant without the existing html flag.

I also viewed the retained R6 failure PNG locally. It visibly contains the marketing navigation row below the persistent Terminal top bar and above the separate breadcrumb and About content. The actual R6 evidence records a content READY and visible `main.ab-main`, but an empty observer chrome union. This supports a real product/observer coverage omission; R7 does not reinterpret that failed case as a pass.

### 2. Publication and test ownership remain intact

The thirteen other original snapshot paths are byte-identical to their candidate counterparts, including the bridge and publication helpers. Existing `work/lib/shared_shell.py` lines 79–85 copy both governed assets and clear their version caches. Lines 102–137 replace only the owned capability block and retain stylesheet-before-blocking-bridge ordering. Existing `work/scripts/optimize_assets.py` lines 152 and 182–215 copy the asset, update paired templates first, and process retained documents. `work/scripts/inject_shared_shell.py` lines 16–50 likewise verifies/copies the assets and updates the paired source and retained document blocks.

The new Python test at `work/tests/test_shared_shell_injection.py` lines 83–105 uses those real owner functions. It requires the Main component and all three page landmarks, verifies canonical/emitted CSS equality and its content digest, proves that restamping changes only the owned CSS reference, and retains idempotence and CSS-before-bridge assertions. The Node change at `work/tests/js/shared_shell_bridge.test.cjs` lines 361–364 admits only this exact scoped nav selector while retaining the prohibition on other generic nav selectors and the existing header guard.

The expected paired About outputs were independently compared with the original: the sole difference is `shared_shell.css?v=6a3f8fe8` becoming `shared_shell.css?v=8c102aa3`; the paired outputs are equal. This establishes the expected local owner result, not full repository publication. The candidate `work/` About copies intentionally still carry the old stamp; they must not be treated as the completed R7 fixture. The parent owns canonical regeneration and the new complete commit.

### 3. R7 strengthens observation and preserves the existing acceptance conditions

I independently reversed only the new CSS hash and the added snapshot selector in the entire runner. The result is exact R6 SHA256 `b35ce8bfeb5fc9fc6940f5e47cbc17ece746051bf73d4900602fc94b6f9713f8`. Reversing only the runner and README pins in the wrapper reproduces exact R6 SHA256 `3ae4a32933bbf45f6091114cfdcbd009af789322f1830187e006a3529f55cbd2`. The manifest helper, fixture server, Next launcher and wrapper effects document match their unchanged R6 hashes.

The added observer selector is at runner line 460. `ready()` lines 485–508 remains unchanged: actual current-generation READY, route and context matching, positive chrome presence, every observed node having `display:none` and zero rectangles, the unique visible retained region with at least 200 characters and positive geometry, HTML language, and actual INIT catalog evidence are still required. There is no zero-chrome exemption.

The unchanged journey also retains real bridge navigation, generation/document changes, parent shell/header/iframe/WindowProxy persistence, history return, and the missing-CSS failure followed by real Retry. Source preparation still pins full supplied HEADs, compares admitted fixture bytes with committed bytes, requires the exact repaired emitted/template asset bytes and document digests, and rechecks source at completion. See runner lines 197–265 and 759–769. Old asset bytes or stale document stamps fail preparation.

The HTTP/response/WebSocket boundary and wrapper process code are byte-identical to R6. The inspected code retains exact loopback document scope, GET/HEAD restrictions, response-stage rejection before original response continuation, actual owned HMR identity, provisional acceptance followed by late-error/context cleanup checks, and the four-case receipt requirement. The wrapper still uses prepare/inspect/explicit run, live owned server handles and receipts, and bounded owned shutdown; it does not gain a new kill, network, authentication or publication effect.

## Checks actually performed in this review

- Verified all 12 files in the product handoff manifest and all 12 runtime/review files in the R7 transfer manifest against their declared lengths and SHA256 values.
- Verified all four product changed-path before/after byte lengths, SHA256 and Git blob IDs; reconstructed the exact patch; verified thirteen other snapshot paths unchanged.
- Verified the one-line CSS delta, About selector topology, expected paired About output, and complete runner/wrapper reverse continuity independently.
- Ran `node --check kit/qualify-shared-shell.cjs`: exit 0.
- Ran `node kit/qualify-shared-shell.cjs --self-check`: 18 HTTP admission cases, 16 WebSocket cases, 15 response-gate cases, two native-navigation scope cases and query redaction passed. This branch exits before source preparation, networking or browser loading.
- Parsed the manifest helper, read-only server and attended wrapper with Python AST: all three passed without importing or executing them.
- Read the added product tests and the author's retained 70/70 candidate and 69/70 old-CSS regression results. I did not rerun that suite or pytest; the parent owns the actual repository regression gate.

## Boundary of this disposition

The candidate is suitable for the parent's canonical publication and new source-bound R7 run. Actual suppression and all four browser cases must still be earned using the newly committed Macro bytes and unchanged reviewed Terminal bindings. This review supplies no R7 runtime pass, full-site publication proof, public beta acceptance, authentication acceptance or design verdict. No candidate, original R6 evidence or previous review file was edited.
