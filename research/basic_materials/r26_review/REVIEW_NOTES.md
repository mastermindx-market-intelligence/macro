# Basic Materials dossier review — current through R27

Operation: `gmi-basic-materials-research-20260923-sol-001`  
Carrier: research-only Macro #7796; product economics remain on #7984.  
Disposition: **RESEARCH_PROTOTYPE / NOT_APPLIED_TO_PAPER / NOT_DEPLOYED / VISUAL_REVIEW_PENDING**.  
MISSION_COMPLETE: false.

This updates the existing R26 artifact in place. The complete preceding review notes remain at this path in `8f66fc1e5f0de93ab2cb051656e57aec88ee5dbb`, blob `07dedfcece43e62938b880c5cc0a03359ca30d95`. Do not rebuild the mockup or repeat the R24/R25 scope experiments.

## Current artifacts

| File | Immutable receipt |
|---|---|
| `materials_dossier_review.html` | R27 commit `c2aefb6bc14f8d4d62fa52d7ba5c207d781e3cfb`; blob `479b97af3c0b31b82437c64d29603fd55e89d698`; 40,684 UTF-8 bytes; SHA256 `ca400ead3ee896b6499bf8951c95cc7fa42c16b94e467e05b7e60b77f685ef21` |
| `verify_static.py` | R27 commit `c187abc84aa7f9711a4cd45688ea2dbde90b7786`; blob `125c6de957752be745e98b8f9e6b5b4e4d849399`; SHA256 `d10c6e066c641573a3e4d411ee9677afd2ab0dd64506c38c7226bdde2a7350fd` |

The exact commit readbacks matched the locally tested complete-file Git blobs. Both changes use the existing research branch and compare-and-swap against the original file blobs; no product worktree was acquired or changed.

## Source-level repairs

- The three formerly English-only accessibility names now have English/Chinese copy bindings. Review controls declare a labelled group; the task panel declares a keyboard focus target.
- The comparison renderer now constructs a native table with a caption, column headers and company row headers. Its container is labelled and focusable, with in-container horizontal overflow instead of the old visual-only row/card treatment. Whether it actually fits and remains usable at narrow widths is still unverified.
- Mobile review controls and family filters declare 44px minimum height and 14px text. These are CSS declarations, not measured target dimensions or visual acceptance.
- Task changes append history instead of overwriting it. One closed hash parser is shared by initialization and restoration, including default/unknown hashes. The skip-to-content anchor remains outside tab restoration. Hash-driven task changes close an open dialog before repainting and explicitly target the active tab afterward. Actual Back/Forward, focus and scroll behavior still require a permitted browser.
- The status message names the current task, count and selected journey where appropriate. Empty-family text does not invent coverage; denied, unavailable and unknown simulated states omit the selected-company name. This is copy logic, not access-control proof.
- Script-disabled viewing has an explicit bilingual notice instead of depending on populated JavaScript labels.

The complete four-journey data and every pre-existing EN/ZH copy value were compared with R26 and are unchanged. Nutrien unit-margin scope, NOVONIX's two separate originals, Wheaton/Antamina financial participation and Weyerhaeuser actual investment cash remain distinct. No current conclusion, source body, evidence identity, market figure, calculation, score or signal was added.

## Verification actually executed

Run `python verify_static.py` beside the HTML, with Python and Node installed. No dependency installation, DOM environment, browser or URL access is used.

Before repair, the expanded verifier exited 1 against exact R26 HTML: **20 passed, 33 failed**. After the targeted repairs, fresh execution exited 0: **53 passed, 0 failed**. Python compilation also passed.

The 53 reported checks comprise the original 20, 15 additional source-declaration/wiring checks and 18 individual pure hash/announcement cases. The original six visible/total-count examples remain included inside the original 20, not counted again. Intermediate source repair results were 28/53 and 31/53 before the navigation/copy helper changes. One lexical check initially matched the word `fetch` in a comment; that inaccurate API-name comment was corrected without relaxing the no-network check.

The final generated `structure_verification.json` SHA256 is `a46949ea5c3f80c5b26ba7aaeb16194ad1c98b091295167965e9916ae05c0c3c`. The report binds the exact HTML hash above. Portable copies include the original failing report, final report and preservation result.

These are **non-browser research-prototype checks**. The verifier parses source, checks declarations and executes only the data/pure-helper prefix in Node. It does not construct a DOM or a stand-in, execute event handlers, exercise browser history/focus, measure layout, test a screen reader or verify real authorization. Browser checks 0; screenshots 0; assistive-technology checks 0; production tests 0; native source admissions 0. No full accessibility or browser acceptance is claimed.

## Visual and integration holds

R26's first local-file browser navigation was explicitly administrator-blocked, with `URLBlocklist:["*"]`. R27 did not retry navigation, change policy, substitute a browser/host, use `set_content`, or simulate a DOM to evade it. The earlier missing bundled browser and later explicit policy denial remain different facts.

Paper was read-only in R26 and not revisited or edited in R27. Its observed concurrent page movement did not establish exclusive canvas custody. The shared-shell reference remains file `01M2WGNCX9475G79JRKJTCM08P`, page `p-D-0`, artboard `UBT-0`, token hash `bba69475`; it is not an approved exact JSX port. Production must consume the incumbent shell and theme tokens, not adopt this self-contained prototype as another navigation/token system.

The bounded R27 read of Mastermind #539 comments after the existing consumer request `5850091253` returned no newer response. No new request, canary mutation, target context or worker was created. That absence is not a platform-wide capability finding. The existing shared scope/ref/K1/P5 proposal and sector identity/private-reader questions also remain unaccepted; they were not re-probed or changed by these UI repairs.

## Exact next review

Obtain a positively permitted source-bound visual context or exclusive Paper assignment through the existing owners, then review **this exact revised artifact** in the eight combinations of 1440/390 width, EN/ZH and light/dark. Exercise task hash/Back/Forward, skip link, focus return, screen-reader announcements, table headers/scrolling, family empty states and all simulated unavailable states. Verify actual font delivery, contrast, target dimensions and overflow. The original system-font fallback remains; no font file is distributed.

The three English-only labels, visual-only comparison rows and 12px mobile review controls are no longer outstanding source defects; the new semantics and styles still need rendered and assistive-technology proof. No wholesale design restart or additional scope-fragment exercise is the next step.

Full product acceptance still requires all five real documents/four real company journeys, retention/review/current rights, native company/source navigation, private negative-path proof and independent release review. #7984's denied cash action and frozen test-first sequence remain held. No product/shared schema, source record, identity, rights, publisher, CI workflow, worker, release or deployment changed.
