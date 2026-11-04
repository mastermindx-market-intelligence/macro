# Independent bounded runtime adjudication

**Verdict: ACCEPT the scoped Data & tools / nested-link navigation repair at source commit `ca4efe7b36a47887c18746ffa9d931e15b97e5f2`. Retain the full parent focus-restoration hold.**

The terminal v9 evidence closes the actual-parent navigation and saved-scroll gates for this repair. It does **not** make the complete parent integration green: the saved-focus assertion still fails, the overall observation remains `failed`, and the driver exits with code **1**. No additional blocker to the bounded navigation repair was found in this review.

Reviewer: `/root/intl_shell_acceptance_review`, independent read-only principal review. I read retained source and evidence; I did not modify files, execute tests, launch or poll servers, dispatch work, or perform an acceptance/publication action.

## Evidence and custody

Evidence directory:

`/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022`

I reviewed `TOOLS_RUNTIME_SUMMARY.json` and the complete `candidate_parent_full_v9/observation.json`, together with its archived driver, `runtime.json`, `driver_execution.json`, `shutdown.json`, and the referenced ordinary-build receipt.

| Binding | Verified identifier |
|---|---|
| Macro source and ordinary-build source | `ca4efe7b36a47887c18746ffa9d931e15b97e5f2` |
| Actual supported parent | `e45bde2cac07ac3b29285ff70c40d68900fad62c` |
| Archived v9 driver SHA-256 | `3e44887001838518275b5da52a007b4c26a4495832d614c85db8504f3075f403` |
| Complete observation SHA-256 | `af6930e50da1f95673414f57fdfa79fcb8839c36837452db1ede68cf9c622d7e` |
| Built and served HTML SHA-256 | `4d72ef803ae4c8a6e729d32df2fd8599fb3d405874079df6f289e5c549bdfa62` |
| Approved controller SHA-256 | `1ba7eb423077e23142260eb77064afb076f9d8670cdc11d1925b18ebd9323042` |
| Approved paired bridge SHA-256 | `31b150d8335f7abafa6210bcaf26d98a9e7e2251e34a09ce69f4524c59720e30` |

I independently recomputed the observation, archived-driver, runtime-receipt and build-receipt digests from the read content; each matches the retained binding. The executed archived driver also matches the v9 source previously reviewed.

The build receipt identifies an ordinary build from the exact subject, with no source overlays, no source reacquisition and no production mutation. The runtime receipt identifies the actual local supported parent and reports its tracked source clean at startup. The shutdown receipt reports it clean at shutdown and records the owned child exiting on termination (`-15`) and parent exiting `0`. The execution receipt retains the driver’s exit code `1`.

## Terminal results and supported behavior

I recomputed the case totals from the complete observation rather than relying solely on its summary.

| Result | Count |
|---|---:|
| Contexts | 17 |
| Passing assertions | 816 |
| Failing assertions | 1 |
| Known baseline failures | 1 |
| Repair-scope failures | 0 |
| Matching observed HTML/bridge/shell-CSS response bindings | 153 |
| Page errors / console errors | 0 / 0 |

Coverage comprises widths **1440, 768, 390 and 320**, each in English/Chinese and dark/light presentation, plus the separate raw-query preservation context. The 153 response bindings comprise 119 HTML responses, 17 bridge responses and 17 shell-CSS responses; all match their expected bytes.

The recorded journeys support acceptance of:

- First and repeated projected Data & tools activation, including a repeat that reopens a manually closed disclosure without another accepted navigation, history entry or generation.
- Activation after a real Library query change, preserving the currently accepted business query despite the older projected link representation.
- First and repeated activation of the same real Library Leadership link, with the required nested disclosures reopened and the target visible.
- Genuine parent Back/Forward traversal, with exact destinations, fresh child generations and unchanged history length during traversal.
- Raw-query preservation, including the deliberately demanding encoding, duplicate-key and empty-segment fixture.
- The real mobile prerequisite: selecting the existing `leaders` Library group, receiving its accepted `group=leaders` location and additional history entry, and using that settled state for subsequent assertions. All eight mobile group-selection checks pass.

These conclusions rest on the actual parent’s messages and browser history behavior, not fabricated acceptance events or a modeled parent.

## Saved-scroll gate passes; saved-focus gate remains failed

The restoration probe is materially discriminating:

- Saved view: `{x: 0, y: 3299, focusId: "im-catalogue-library-search"}`.
- Fragment-heading document Y: `12436.796875`.
- Child viewport height: `836`.
- The heading therefore lies approximately **8,302 pixels below the saved viewport’s bottom**.

The real parent-observed `VIEW_STATE` contains that saved view. After genuine Back/Forward, the same history entry and URL return with a fresh child generation, and `INIT.restore` contains the identical view. Both late samples retain **x=0, y=3299**. This establishes that the repair does not ultimately replace this saved position with the hash-heading position.

Both late samples instead report focus on **BODY with an empty ID**. That exactly matches the retained unchanged-baseline outcome. The sole failing case is `restoration_focus_matches_saved_view`; it remains failed and contributes to the overall nonzero result.

The source-backed parent exposure-ordering explanation remains an inference, not a uniquely demonstrated cause. This evidence does not approve a child focus retry or establish a complete focus-restoration solution.

## Provenance of the independent driver reviews

My earlier **v8 review** accepted the real saved-entry → Back/Forward → fresh `INIT.restore` → late-scroll journey, while identifying three qualifications:

1. The half-viewport distance predicate did not by itself establish an offscreen hash target.
2. Exact build-commit identity needed an explicit check beyond controller/bridge content equality.
3. The mobile Library link requires its real group-selection prerequisite.

That review also confirmed that the BODY baseline annotation did not clear overall failure, and limited the focus observation to settled samples.

My subsequent **v9 delta review** found no blocker. I applied the retained seven-hunk delta to v8 in memory and reproduced the read v9 driver exactly, apart from terminal-newline normalization. The delta added the genuine mobile group journey and updated accepted baseline, retained the same group-specific link for both activations, strengthened the discriminator to `heading.y > saved.y + viewport + 64`, required exact build-subject equality, and accurately named the settled focus observation. Existing navigation assertions and failure accounting remained intact.

The terminal execution now binds to that same reviewed v9 driver and satisfies those qualifications.

## Screenshot and warning interpretation

Two points should remain explicit in the durable visual record.

**The target geometry proves the specific rank heading’s visibility.** For `390-zh-dark`, both first and repeated nested activation hit the exact `H3#intl-leadership-rotation`, whose text is “20d momentum — rotation rank” / “20日动能 — 轮动排名.” Its recorded child rectangle is Y `101.90625–122.046875`; the tested point is at parent Y `167.9765625`, with both child and parent hit tests passing. This supports visibility of that target heading. It does not assert that an enclosing, broader section title is at the top of the screenshot or visible.

**The retained “Invalid URL state restored” warning is not merely a consequence of the adversarial query fixture.** The ordinary `390-zh-dark` Tools snapshot has no business query; its child URL contains the internal `mmx_shell` and `mmx_generation` parameters. The unchanged workspace controller passes raw child `location.search` into its reducer at mount (`templates/intl_workspace.js`, line 1864). The workspace state parser allows only its declared business-query fields and rejects other keys (`intl_workspace_state.js`, lines 18 and 437–444). This supplies a source-backed explanation for the warning on a legitimate shell path: a pre-existing shell/workspace transport-query compatibility issue.

The previously read baseline workspace controller is byte-identical to the candidate’s manifest-bound controller dependency. This is therefore not evidence of a newly introduced Tools-navigation regression. It also must not be described as proof that the broader workspace URL state is healthy. Because invalid parsing restores initial workspace state, the warning is an additional reason not to elevate the earlier focus-ordering explanation into a uniquely proved root cause. The retained unavailable-return state likewise remains outside this navigation acceptance.

## Acceptance boundary

The approved source, discriminating regression evidence and completed actual-parent v9 run support **scoped acceptance of the Tools/nested-link navigation repair**. Preserve the failed overall result, the unchanged focus hold, the retained workspace warning, and the stated observation limits.

This review does not establish complete visual acceptance, complete parent focus restoration, production deployment readiness, or behavior beyond the local supported-parent fixture and contracts actually exercised.
