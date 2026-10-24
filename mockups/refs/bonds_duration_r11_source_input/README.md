# Bonds R11 exact-candidate review input

**INPUT ONLY — NOT BROWSER EVIDENCE, NOT DEPLOYED, NOT LIVE MARKET DATA.**

The actual Bonds route is rendered from source commit `d3b11fe9be0e67e56ecff40bf25d5e09e85d3d1e` with the existing `tests/test_bonds_divergence_gate.py::_base_ctx` synthetic fixture. The unchanged duration controller is embedded once. The renderer is the existing Jinja template, `lib.pages.write_page`, then `scripts.externalize_css.externalize`; this is not a replacement prototype.

R16 corrects the two source-input findings in PR #8241 comment5928315553: the directly referenced `apple-touch-icon.png` is now included, and the complete reconstruction is executable. The original HTML remains SHA256 `6f99fcb52332dd57ed78b1b8477e8e977ca78370806a7615fe41da41d8614d3d`. All27 previously supplied rendered files remain byte-identical; the icon is the28th. Product code, component CSS and controller have not changed.

## Rebuild without a browser or server

Use an existing trusted repository checkout containing the source commit's Git objects and Python render/test dependencies. A descendant checkout is accepted only when its recorded source dependencies and imported repository modules match the immutable source. Do not reset an occupied checkout or fetch through this utility. The observed dependency versions are recorded in `SOURCE.json`; no dependency installation is performed.

From the repository root, choose an output path that does **not** exist:

```sh
python3 mockups/refs/bonds_duration_r11_source_input/rebuild.py \
  --repo . --output /path/to/new-bonds-review-input
python3 /path/to/new-bonds-review-input/verify_input.py
```

The rebuilt directory contains `site/`, the source manifest, these instructions, both utility scripts and a deterministically ordered `candidate.zip`. To check the already-published package without rebuilding it:

```sh
python3 mockups/refs/bonds_duration_r11_source_input/verify_input.py
```

For an extracted copy, invoke `python3 verify_input.py` alongside its `SOURCE.json` and `candidate.zip`; alternatively run its `rebuild.py --repo /path/to/the/existing/checkout --output /another/new/output`. The ZIP intentionally does not recursively contain itself, so retain the original candidate.zip beside the extracted files when running its archive verifier.

The rebuilder verifies listed source dependencies, checks imported repository Python modules against the source commit, renders only into the new output root and copies each non-generated asset from the recorded immutable Git object. `GIT_NO_LAZY_FETCH=1` and `GIT_TERMINAL_PROMPT=0` prohibit the utility from fetching missing objects or requesting authentication. It never changes a Git ref, starts a server/browser or writes production `site/` output. Source/object mismatch or nonempty output fails closed. A failure after output creation leaves that new directory available for diagnosis; it does not overwrite or delete another directory.

`verify_input.py` checks archive integrity, unique safe paths, all28 rendered hashes, unchanged HTML identity, exact icon provenance, direct HTML/CSS resource accounting, matching embedded instructions, and false acceptance flags. These are **review-input checks**, not tests of browser behavior or authentication. The functions are not a replacement build, asset, publication or evidence service.

## Fonts and runtime remain explicit prerequisites

No font binaries are redistributed. Six existing Inter font references are recorded under `font_assets_not_bundled` with exact paths, hashes and sizes. A permitted operator must supply the existing trusted fonts separately from the same source if typography is being qualified. Fallback-font screenshots are not typography-parity evidence. Neither script reads or copies those font binaries.

The shared runtime scripts retain external Supabase/analytics references and dynamic API/session behavior. Static resource accounting is not a runtime network trace, offline-closure claim, login grant or authorization to call external services. Linked pages and dynamic requests are outside this package. The unresolved `.supabase.js` string in the bundled vendor code is not fabricated as a local file. Browser admission, allowed fixture/network behavior, sessions and trusted fonts require the existing operator's separate review.

Do not use a different browser, profile, host or scheme to route around the recorded administrator restriction. No browser navigation, screenshot, accessibility scanner, server, EVIDENCE.yml or deployment is performed by preparation or reconstruction.

## Acceptance still owed

Source review PASS5926458015 and input receipt5928315553 are separate from browser/visual acceptance. After genuine browser admission is restored and the accepting operator is recorded, qualify desktop1440×900, mobile390×844 and tablet820×1180, EN/ZH, dark/light; actual open/edit, +50bp, +350bp invalid clearing, correction, fractional slider input, reset, return/reopen and no-JavaScript/unsupported states. Check real focus order/containment/return, Escape, announcements, contrast, overflow, reduced motion and enlarged text.

Use the existing `capture_page_evidence.py` and accepted evidence schema/guard for real receipts. The current entry fixture does not cover all those states. This package intentionally contains **no passing visual-evidence receipt** and cannot close the parent mission.


## Lazy-import provenance correction

The pre-import source manifest now pins `scripts/check_template_site_sync.py` as well as the externalizer. The externalizer imports that helper lazily; a post-import audit or byte-identical rendered output alone cannot reject a comment-only change before execution. A changed helper must fail the existing dependency guard before any output directory is created. This correction changes only review-input provenance, not the product, financial calculations or rendered page bytes. Browser and release acceptance remain unproven.
