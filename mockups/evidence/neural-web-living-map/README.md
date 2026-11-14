# Neural Web candidate browser evidence

These are real Chromium screenshots of the shared map component, rendered from
the candidate committee graph builder/loader, `neural-map.js`, `neural-map.css`,
and the repository's theme. They are **candidate component evidence**, not a
production, authenticated session, or full-dashboard acceptance claim.

The data is the committed `site/neuralwebdata/confluence_graph.json` snapshot
from Macro baseline `e907472c31478649d0827b128da577dd05ee39c2`, dated 2026-10-15.
The fixture does not replace or simulate the graph builder or rendering engine.
`tests/neural_map_fixture.py` extracts those functions unchanged, isolates the
component from unrelated committee sections, and serves the same data locally.

The unmodified canonical `scripts/capture_page_evidence.py` emitted the v2
manifest: 24 of 24 captures, covering desktop 1440×900 and mobile width 390,
English/Chinese, dark/light, plus actual button hover and input focus states.
The `mobile` capture axis means a narrow viewport; actual touch behavior is
separately exercised with a touch-enabled Chromium context in the regression
suite. All PNG byte lengths and SHA-256 values were read back and
verified against the manifest in the candidate source snapshot.

Capture command, run in the isolated verification directory on Ubuntu0:

```sh
python scripts/capture_page_evidence.py --site-dir site --routes committee.html \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --output-dir evidence-final/png --manifest evidence-final/manifest.json \
  --smells evidence-final/smells.json \
  --force-state 'map_hover:hover(#gc_wire)' \
  --force-state 'map_focus:focus(#nm-search)' --settle-ms 500
```

Six real-browser regression journeys passed using Playwright 1.62.0 and its
installed Chromium. They verify source evidence retention, expanded-node
selection and clearing, keyboard focus, reduced-motion repainting, drag release
outside the canvas, paused animation, theme/language/resize continuity, repeated
mounts, mobile layout, the original Admin iframe adapter, attribute removal,
real touch pinch-to-pan transitions, offscreen animation suspension, and
failed/empty/retry states. The iframe fixture executes `nwSynapseEmbed` and
`nwWireSynapseFrame` from the Admin source, with its existing donor URL mapped to
the local component page. It does not impersonate an Admin login.

```sh
NEURAL_MAP_FIXTURE_DIR=/path/to/fixture/site \
  python -m pytest tests/test_neural_map_browser.py -q --tb=short
```

The Chairman explicitly approved publication of this reviewed source upgrade
and all 24 screenshots to the public Macro repository. All 24 exact PNGs were
uploaded as immutable GitHub objects before assembly of the candidate tree;
five original successful objects were reused. The captures and this manifest
are candidate evidence. Hosted CI and the repository's visual-evidence gate
must still qualify the actual PR head before merge-on-green is armed.

The resumed six-journey suite also passed with `MM_REQUIRE_BROWSER=1` (4.58s).
Its new bounded owner in `.github/ci/legacy-jobs.yml` installs Chromium, requires
browser support, and builds the fixture from the tested repository. Canonical
owner/schema/browser-setup/closure checks passed locally for the new job; hosted
CI has not run. All eight final resting matrix cells were visually inspected.

Production acceptance remains a separate release obligation. The local
connected browser could inspect the public Neural Web explainer, but an open
extension UI blocked the authenticated Admin tab. That observation is not
treated as production validation of this candidate.

The original source-tree publication was rejected before explicit approval.
This README travels with the approved candidate; final publication, CI, release
and served consumer evidence are recorded by their respective canonical owners.
