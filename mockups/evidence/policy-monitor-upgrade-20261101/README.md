# Policy Monitor — canonical visual evidence

Source commit: `df0680156a3a75dbe97a3eca2aaadb8823f90242`. Source changes are in the original Policy Monitor PR #10493.

This directory contains the existing repository's `mastermind.p0_evidence.v2` manifest, unmodified PNG bytes emitted by `scripts/capture_page_evidence.py`, and the three-key `EVIDENCE.yml` ownership receipt. No evidence gate, schema, timeout, budget or test was weakened.

## What was captured

**24 of 24 real browser states**: desktop/mobile × English/Chinese × light/dark, each at rest and with actual hover and focus on a Policy Monitor disclosure. The manifest records requested and applied states, the real capture module hash, PNG digests, byte counts and dimensions. All new-receipt shape, PNG integrity and required hover/focus validations returned zero findings.

The rest view is scrolled to the corrected combined-stance section. Hover/focus uses `#dlg-policy summary` and the browser's real interaction methods. [Full-page controller proof](../../../research/evidence/policy_monitor_upgrade_20261101/receipt.json) separately covers fourteen populated/degraded views, open/close/reopen, Escape, focus restoration, keyboard disclosure activation, reverse focus wrap and page/dialog overflow.

## Scope and provenance

The capture target is an **anonymous local component preview**, built by `tests.probe_policy_monitor_browser.render('populated')` and staged with that probe's existing `_stage` helper. It uses the actual dashboard template and committed `site/policy_lever.json` and `data/regime/latest.json` payloads. It supplies no credentials or access-tier stub and exercises no live authentication.

A preview-only style hides unrelated siblings while preserving the dialog's real grid/panel ancestors. A preview-only script sets the existing open/entrance/scroll-lock classes and scrolls the combined-stance section into view. Product markup, Policy Monitor CSS and source values are unchanged. This makes a bounded component screenshot; it does not pretend to exercise the access controller. The separate fourteen-view probe drives that controller with its explicitly disclosed signed-in preview fixture.

The canonical capture tool truthfully reports no git directory above its temporary served fixture. `fixture.json` supplies the clean source commit and the SHA-256 of the rendered fixture bytes. No live release is claimed. The initial incorrect preview hid a parent grid, produced blank images, and was stopped; **none of those failed-attempt images is included here**.

## Reproduction

From the source checkout, render and stage the populated page with `tests.probe_policy_monitor_browser`. Before `</body>`, append this preview-only shell:

```html
<style id="policy-evidence-shell">
body > :not(.grid):not(script):not(style),
body > .grid > :not(.mx5-rack-panel),
body > .grid > .mx5-rack-panel > :not(#dlg-policy):not(script):not(style){display:none !important}
body{height:100vh;min-height:0;overflow:hidden}
</style>
<script>
(function(){
  var d=document.getElementById('dlg-policy');
  d.classList.add('open','mx5-dlg-in');
  d.setAttribute('aria-modal','true');
  document.body.classList.add('mx5-dlg-open');
  document.documentElement.classList.add('mx5-dlg-lock');
  var s=d.querySelector('.plm-split');
  if(s)s.scrollIntoView({block:'start'});
})();
</script>
```

Use the committed registry and the canonical capture command (substitute your temporary fixture/output paths):

```bash
python3 scripts/capture_page_evidence.py \\
  --registry /tmp/policy-monitor-r6-canonical-fixture/registry.json \\
  --site-dir /tmp/policy-monitor-r6-canonical-fixture --routes /macro.html \\
  --output-dir /tmp/policy-monitor-r6-canonical-evidence-v2/images \\
  --manifest /tmp/policy-monitor-r6-canonical-evidence-v2/manifest.json \\
  --smells /tmp/policy-monitor-r6-canonical-evidence-v2/smells.json \\
  --viewports desktop,mobile --locales en,zh --themes light,dark \\
  --max-pages 1 --settle-ms 1400 --delay-ms 0 \\
  --force-state 'disclosure_hover:hover(#dlg-policy summary)' \\
  --force-state 'disclosure_focus:focus(#dlg-policy summary)'
```

The full hosted design-governance check remains the integration gate; local receipt validation alone is not a claim that hosted CI passed.
