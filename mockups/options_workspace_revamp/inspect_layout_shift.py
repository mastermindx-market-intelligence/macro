"""Observe one desktop EN/light fixture load without changing production code.

Run on the existing M2 workspace/server:
    python3 mockups/options_workspace_revamp/inspect_layout_shift.py

Uses capture_canonical_evidence.py's exact fixture router and the repository's
real Playwright driver. It preserves the canonical pre-load state seed, timing
observer, post-load state reapplication, and two 1300 ms settle windows. The
extra observer records individual layout-shift sources and timing milestones.
It does not edit canonical evidence/metrics or judge production Web Vitals.
An existing output is refused; use --output <another-local-json-name> for a
separately identified follow-up, rather than overwriting an observation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import capture_canonical_evidence as fixture_capture


TRACE_SCRIPT = r"""
(() => {
  const trace = window.__oewLayoutShiftAudit = {
    shifts: [], milestones: [], mutations: [], observerErrors: [],
    clsWithoutRecentInput: 0, shiftCount: 0,
    shiftDetailsTruncated: false, mutationDetailsTruncated: false
  };
  const nodeInfo = node => {
    let el = node && (node.nodeType === 1 ? node : node.parentElement);
    if (!el) return null;
    const own = item => ({
      tag: (item.tagName || '').toLowerCase(),
      id: item.id || '',
      class: (item.getAttribute && item.getAttribute('class') || '').slice(0, 320)
    });
    const value = own(el);
    value.ancestors = [];
    for (let i = 0, p = el.parentElement; p && i < 3; p = p.parentElement, i++) {
      value.ancestors.push(own(p));
    }
    return value;
  };
  const rectInfo = rect => rect ? {
    x: rect.x, y: rect.y, width: rect.width, height: rect.height,
    top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left
  } : null;
  const snapshot = name => {
    const html = document.documentElement, body = document.body;
    const selectors = [
      '.site-nav', '#options-workspace', '.oew-chrome', '#mode-brief',
      '.oew-availability', '#oew-index-structure', '#oew-history',
      '#oew-sources', '#mmb-boot', '#mmb-launch'
    ];
    const positions = {};
    selectors.forEach(selector => {
      const el = document.querySelector(selector);
      positions[selector] = el ? {node: nodeInfo(el), rect: rectInfo(el.getBoundingClientRect()),
        display: getComputedStyle(el).display, position: getComputedStyle(el).position} : null;
    });
    positions.indexCards = [...document.querySelectorAll('.oew-ic')].map(el => ({
      node: nodeInfo(el), rect: rectInfo(el.getBoundingClientRect())
    }));
    const computed = body ? getComputedStyle(body) : null;
    const value = {
      name, time: performance.now(), readyState: document.readyState,
      theme: html && html.getAttribute('data-theme'),
      locale: html && html.getAttribute('data-lang'),
      htmlClass: html && html.getAttribute('class'),
      viewport: {width: innerWidth, height: innerHeight, scrollX, scrollY},
      documentHeight: html && html.scrollHeight,
      fontsStatus: document.fonts && document.fonts.status,
      bodyStyle: computed ? {fontFamily: computed.fontFamily, fontSize: computed.fontSize,
        lineHeight: computed.lineHeight, paddingTop: computed.paddingTop,
        backgroundColor: computed.backgroundColor, color: computed.color} : null,
      positions
    };
    trace.milestones.push(value);
    return value;
  };
  window.__oewLayoutShiftSnapshot = snapshot;
  try {
    new PerformanceObserver(list => {
      for (const entry of list.getEntries()) {
        trace.shiftCount++;
        if (!entry.hadRecentInput) trace.clsWithoutRecentInput += entry.value;
        if (trace.shifts.length >= 100) { trace.shiftDetailsTruncated = true; continue; }
        trace.shifts.push({
          startTime: entry.startTime, duration: entry.duration,
          value: entry.value, hadRecentInput: entry.hadRecentInput,
          lastInputTime: entry.lastInputTime,
          sources: [...(entry.sources || [])].map(source => ({
            node: nodeInfo(source.node),
            previousRect: rectInfo(source.previousRect),
            currentRect: rectInfo(source.currentRect)
          }))
        });
      }
    }).observe({type: 'layout-shift', buffered: true});
  } catch (error) { trace.observerErrors.push(String(error)); }
  const recordMutation = item => {
    if (trace.mutations.length < 300) trace.mutations.push(item);
    else trace.mutationDetailsTruncated = true;
  };
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'attributes') {
        const el = record.target;
        if (el !== document.documentElement && el !== document.body &&
            !(el.matches && el.matches('.site-nav'))) continue;
        recordMutation({time: performance.now(), kind: 'attribute', node: nodeInfo(el),
          attribute: record.attributeName, oldValue: record.oldValue,
          newValue: el.getAttribute(record.attributeName)});
      } else {
        for (const node of record.addedNodes) {
          if (node.nodeType !== 1 || !['STYLE', 'LINK', 'SCRIPT'].includes(node.tagName)) continue;
          recordMutation({time: performance.now(), kind: 'asset-node-added', node: nodeInfo(node),
            src: node.getAttribute('src'), href: node.getAttribute('href'),
            rel: node.getAttribute('rel')});
        }
      }
    }
  }).observe(document, {subtree: true, childList: true, attributes: true,
    attributeOldValue: true, attributeFilter: ['class', 'style', 'data-theme', 'data-lang']});
  document.addEventListener('DOMContentLoaded', () => {
    snapshot('DOMContentLoaded-listener-before-later-registered-handlers');
    requestAnimationFrame(() => snapshot('first-frame-after-DOMContentLoaded'));
  }, {once: true});
  window.addEventListener('load', () => snapshot('window-load'), {once: true});
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => snapshot('document-fonts-ready'));
    document.fonts.addEventListener('loadingdone', () => snapshot('document-fonts-loadingdone'));
  }
})();
"""


def fingerprint(path: Path):
    if not path.is_file():
        return {"present": False}
    data = path.read_bytes()
    return {"present": True, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="layout_shift_report.json",
                        help="New JSON filename directly in this diagnostic's directory")
    args = parser.parse_args(argv)
    output = (HERE / args.output).resolve()
    if output.parent != HERE or output.suffix != ".json":
        parser.error("--output must name a JSON file directly in this diagnostic's directory")
    if output.exists():
        parser.error("output already exists; preserve it and choose a new --output name")

    payloads = fixture_capture.load_current_fixture()
    from scripts import capture_page_evidence as canonical

    url = fixture_capture.ORIGIN + "/mockups/options_workspace_revamp/fixtures/published/workspace.html"
    report = {
        "schema": "mastermind.options.layout_shift_diagnostic.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "outcome": "pending",
        "url": url,
        "viewport": {"width": 1440, "height": 900},
        "requested_state": {"theme": "light", "locale": "en"},
        "source_pin_for_shared_code_review": "ba7947223ae58f436d4cfadbedc28454b10483fc",
        "restrictions": {"fresh_anonymous_context": True, "authentication_supplied": False,
                         "external_requests": "aborted by unchanged published fixture router",
                         "service_workers": "block", "canonical_reports_modified": False},
        "interpretation": "One instrumented lab load; no production Web Vitals or acceptance verdict implied.",
        "source_fingerprints": {
            name: fingerprint(ROOT / name) for name in (
                "templates/options.html.j2", "templates/theme.css", "site/theme.css",
                "templates/theme.js", "scripts/build_options_command.py",
                "scripts/capture_page_evidence.py",
                "mockups/options_workspace_revamp/capture_canonical_evidence.py",
                "mockups/options_workspace_revamp/fixtures/published/workspace.html",
            )
        },
        "console_errors": [], "page_errors": [], "failed_responses": [],
    }
    driver = context = page = None
    try:
        driver = fixture_capture.fixture_driver_factory(canonical, payloads)(
            headless=True, settle_ms=1300)
        context = driver._browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=canonical.USER_AGENT, locale="en-US", color_scheme="light",
            device_scale_factor=1, accept_downloads=False,
        )
        state = report["requested_state"]
        context.add_init_script(canonical.state_seed_source(state))
        context.add_init_script(canonical.timing_init_source())
        context.add_init_script(TRACE_SCRIPT)
        page = context.new_page()
        page.on("console", lambda msg: report["console_errors"].append(
            {"text": msg.text, "location": msg.location}) if msg.type == "error" else None)
        page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
        page.on("response", lambda response: report["failed_responses"].append(
            {"url": response.url, "status": response.status}) if response.status >= 400 else None)
        response = page.goto(url, wait_until="load", timeout=30000)
        if response is None or not response.ok:
            raise RuntimeError("Fixture navigation failed: " + str(response.status if response else None))
        page.evaluate("window.__oewLayoutShiftSnapshot('goto-load-resolved')")
        page.wait_for_timeout(1300)
        page.evaluate("window.__oewLayoutShiftSnapshot('before-canonical-state-reapply')")
        report["applied_state"] = page.evaluate(canonical._APPLY_STATE_SCRIPT.strip(), state)
        canonical._wait_transient_fx_gone(page)
        page.wait_for_timeout(1300)
        page.evaluate("window.__oewLayoutShiftSnapshot('after-canonical-state-reapply')")
        report["canonical_timing_snapshot"] = page.evaluate(canonical._TIMING_SNAPSHOT_SCRIPT.strip())
        report["trace"] = page.evaluate("window.__oewLayoutShiftAudit")
        report["outcome"] = "observed"
    except Exception as error:
        report["outcome"] = "failed"
        report["error"] = type(error).__name__ + ": " + str(error)
        if page is not None:
            try:
                report["trace"] = page.evaluate("window.__oewLayoutShiftAudit || null")
            except Exception:
                pass
    finally:
        if context is not None:
            try:
                context.close()
            except Exception as error:
                report.setdefault("cleanup_errors", []).append("context: " + str(error))
        if driver is not None:
            try:
                driver.close()
            except Exception as error:
                report.setdefault("cleanup_errors", []).append("driver: " + str(error))

    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    trace = report.get("trace") or {}
    print(json.dumps({"outcome": report["outcome"], "report": str(output),
                      "shift_count": trace.get("shiftCount"),
                      "observed_sum_without_recent_input": trace.get("clsWithoutRecentInput"),
                      "canonical_timing_snapshot": report.get("canonical_timing_snapshot"),
                      "console_error_count": len(report["console_errors"]),
                      "page_error_count": len(report["page_errors"])}))
    return 0 if report["outcome"] == "observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
