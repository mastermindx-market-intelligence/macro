# All tools admitted-pilot browser proof

This is a manual, bounded Chrome/Playwright acceptance harness for the three default-OFF pilot pages. It is not a new CI workflow, route owner, test lifecycle, browser service or deployment gate.

From the repository root, serve the committed static tree in one terminal:

```sh
python3 -m http.server 8877 --bind 127.0.0.1 --directory site
```

Then run:

```sh
SHARED_SHELL_BASE_URL=http://127.0.0.1:8877 \
SHARED_SHELL_EVIDENCE_DIR=/private/tmp/shared-shell-browser-evidence \
research/market_os/all_tools_adoption/browser/run.sh
```

The runner uses an existing npm cache when present and otherwise performs one bounded `@playwright/test@1.62.0` bootstrap. Chrome is the default channel. Override `SHARED_SHELL_BROWSER_CHANNEL` only when deliberately qualifying another installed browser.

Covered real-browser behaviors:

- one mounted host, dialog and trigger on `macro.html`, `sector_central.html` and `reports.html`;
- desktop dark English opening, search, honest no-match recovery, Escape and focus return;
- mobile 390×844 light Chinese sheet, heading focus, translated labels, close affordance and viewport bounds;
- current shared theme/account/navigation asset responses;
- refusal to stack over another live modal;
- fail-closed behavior when a projected source destination is withdrawn while open.

This harness does not prove deployment, CDN cache headers, authenticated/personal state, Safari/Firefox, assistive-technology output, 200% text or physical-device behavior. Those remain separate release evidence where owed.

## R38 narrow-screen resilience plan

Goal: keep the existing menu readable, scrollable and dismissible at 320px,
in landscape, and with application typography enlarged to twice its normal size.
Architecture: extend the existing pilot harness and repair only the incumbent
navigation CSS if a real clipping/scroll failure is reproduced. No new overlay,
route catalogue, account state or test workflow. The original eight cases stay.

1. Add reachability checks for the close control, search, destination rows and
   footer on all three pilots; use actual element bounds after scrolling.
2. Run the added cases against unchanged production assets and retain failures.
3. Repair only the demonstrated shared-layout cause, preserving tokens and
   dark/light parity. Keep template/site copies and pilot cache stamps coherent.
4. Rerun the new cases and original browser suite; inspect changed-state images.
5. Publish source, tests and exact evidence on PR7949; keep Draft/HOLD.

The enlarged-text case doubles the existing --fs-* application tokens in the
browser. It is a text-layout stress test, not physical-device or screen-reader
certification, and not evidence of native browser text-zoom behavior.
Review emphasis: long translated labels, clipping at 320px, short-height scroll,
keyboard focus/return, and preserving the complete source-driven directory.

R38 status: nine additional scenarios are authored (three pilots × three
conditions). Node syntax and unchanged-original-suite-prefix checks pass.
The new browser invocation was platform-blocked before dispatch; none of these
nine scenarios has executed and there are no R38 browser screenshots/results.
Do not count them as passes, retry the held invocation through another carrier,
or infer a CSS repair from an unexecuted test. Existing R35 evidence remains
historical exact-tree evidence, not proof of these additional cases.
