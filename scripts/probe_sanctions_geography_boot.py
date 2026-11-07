#!/usr/bin/env python3
"""Exercise the real sanctions page boot with delayed or failed topology.

The committed projection and shards remain unchanged. Only delivery of the
existing topology response is delayed or aborted. The unresolved-register case
uses a labelled synthetic topology with one known boundary omitted; the original
projection, shards and topology file stay unchanged. These are controlled browser
conditions, not a claim of a live source outage or sanctions-screening authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.capture_sanctions_geography_states import serve

SCENARIOS = ("selected-filter", "excluded-selection", "unresolved-register", "topology-failure")
WIDTHS = (1440, 390)
LOCALES = ("en", "zh")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_case(browser, site: Path, port: int, output: Path, scenario: str,
             width: int, locale: str, projection: dict, topology: dict) -> dict:
    context = browser.new_context(viewport={"width": width, "height": 900 if width == 1440 else 844})
    context.add_init_script(
        "localStorage.setItem('theme','dark'); localStorage.setItem('lang', %s);"
        % json.dumps(locale)
    )
    page = context.new_page()
    page.set_default_timeout(15000)
    held = []
    requests = []
    errors = []
    page.on("request", lambda request: requests.append(request.url))
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route("**/world-110m.json", lambda route: held.append(route))
    effective_topology = topology
    observations: dict = {}
    checks: dict[str, bool] = {}
    try:
        with page.expect_request(lambda request: request.url.endswith("/world-110m.json")):
            page.goto(f"http://127.0.0.1:{port}/sanctions-geography.html",
                      wait_until="domcontentloaded")
        row = page.locator("[data-sg-tbody] tr[data-geo-id]").first
        row.wait_for(state="attached")
        checks["topology_is_held"] = len(held) == 1
        checks["register_usable_before_topology"] = page.locator("[data-sg-tbody] tr[data-geo-id]").count() > 0
        checks["no_paths_before_topology"] = page.locator(".sg-geo").count() == 0
        checks["normal_boot_without_test_seam"] = page.evaluate(
            "window.__SANCTIONS_GEOGRAPHY_TEST__ !== true && !window.__sanctionsGeographyBehavior"
        )
        checks["initial_locale_applied"] = page.locator("html").get_attribute("data-lang") == locale
        if not all(checks.values()):
            raise AssertionError("boot precondition did not execute the intended ordering")
        geo_id = row.get_attribute("data-geo-id")
        country = row.locator("td").first.inner_text()
        observations["initial_country"] = country
        observations["initial_geo_id"] = geo_id

        if scenario in ("selected-filter", "excluded-selection"):
            row.focus()
            page.keyboard.press("Enter")
            page.locator("[data-sg-entries] .sg-entry").first.wait_for(state="attached")
            checks["selection_works_before_topology"] = page.locator(
                f'[data-sg-tbody] tr[data-geo-id="{geo_id}"].is-on'
            ).count() == 1
            page.locator("[data-sg-search]").fill(
                country if scenario == "selected-filter" else "__no_matching_country_6834__"
            )
            if scenario == "selected-filter":
                page.locator(f'[data-sg-tbody] tr[data-geo-id="{geo_id}"]').focus()
        elif scenario == "unresolved-register":
            page.locator("[data-sg-view]").select_option("unresolved")
            effective_topology = json.loads(json.dumps(topology))
            geometries = effective_topology["objects"]["countries"]["geometries"]
            retained = [item for item in geometries if str(item.get("id", "")) != geo_id]
            checks["fixture_omits_one_known_boundary"] = len(retained) == len(geometries) - 1
            effective_topology["objects"]["countries"]["geometries"] = retained
            observations["topology_fixture"] = (
                "SYNTHETIC: omit one existing boundary locally to exercise an off-map country; "
                "the committed topology, projection and shards are unchanged"
            )
            observations["omitted_boundary"] = {"geo_id": geo_id, "country": country}
            checks["synthetic_topology_fixture_declared"] = observations["topology_fixture"].startswith("SYNTHETIC:")

        shard_count_before = sum("/sanctions-geography-entries/" in url for url in requests)
        if scenario == "topology-failure":
            held.pop().abort("failed")
            page.locator('[data-sg-map-degraded="true"]').wait_for(state="visible")
            checks["map_failure_is_disclosed"] = page.locator('[data-sg-map-degraded="true"]').count() == 1
            checks["map_stays_hidden"] = page.locator("[data-sg-map]").get_attribute("hidden") is not None
            row = page.locator("[data-sg-tbody] tr[data-geo-id]").first
            row.focus()
            page.keyboard.press("Enter")
            page.locator("[data-sg-entries] .sg-entry").first.wait_for(state="attached")
            checks["register_selection_survives_map_failure"] = page.locator(
                "[data-sg-tbody] tr[data-geo-id].is-on"
            ).count() == 1
            checks["detail_survives_map_failure"] = page.locator("[data-sg-entries] .sg-entry").count() > 0
        else:
            if scenario == "unresolved-register":
                held.pop().fulfill(body=json.dumps(effective_topology), content_type="application/json")
            else:
                held.pop().fulfill(path=str(site / "world-110m.json"), content_type="application/json")
            page.locator("[data-sg-map]:not([hidden])").wait_for(state="visible")
            checks["map_becomes_visible"] = page.locator(".sg-geo").count() > 0
            checks["initial_accessible_names_are_localized"] = page.locator(".sg-geo.is-pick").evaluate_all(
                """(nodes, locale) => nodes.length > 0 && nodes.every(node =>
                node.getAttribute('aria-label') === node.getAttribute(locale === 'zh' ? 'data-name-zh' : 'data-name-en'))""",
                locale,
            )
            if scenario == "selected-filter":
                checks["focused_country_row_stays_connected"] = page.evaluate(
                    """id => !!document.activeElement && document.activeElement.isConnected &&
                    document.activeElement.getAttribute('data-geo-id') === id""", geo_id
                )
                selected = page.locator(f'.sg-geo[data-geo-id="{geo_id}"]')
                checks["selection_projects_to_new_map"] = (
                    page.locator(".sg-geo.is-on").count() == 1
                    and "is-on" in (selected.get_attribute("class") or "")
                    and selected.get_attribute("aria-pressed") == "true"
                )
                snapshot = page.evaluate("""() => {
                    const visible = new Set(Array.from(document.querySelectorAll('[data-sg-tbody] tr[data-geo-id]'),
                        row => row.getAttribute('data-geo-id')));
                    const paths = Array.from(document.querySelectorAll('.sg-geo.is-pick'));
                    const excluded = paths.filter(path => !visible.has(path.getAttribute('data-geo-id')));
                    return {
                        excludedCount: excluded.length,
                        filteredCorrectly: excluded.length > 0 && paths.every(path => {
                            const kept = visible.has(path.getAttribute('data-geo-id'));
                            return path.classList.contains('is-off') === !kept &&
                                path.getAttribute('tabindex') === (kept ? '0' : '-1') &&
                                path.getAttribute('aria-disabled') === (kept ? 'false' : 'true');
                        }),
                        excludedIds: excluded.map(path => path.getAttribute('data-geo-id'))
                    };
                }""")
                checks["latest_filter_controls_map_and_keyboard"] = snapshot["filteredCorrectly"]
                observations["excluded_boundaries"] = snapshot["excludedCount"]
                checks["map_reconciliation_does_not_refetch_detail"] = (
                    sum("/sanctions-geography-entries/" in url for url in requests) == shard_count_before == 1
                )
                page.locator("[data-sg-map]").scroll_into_view_if_needed()
                target = page.evaluate("""ids => {
                    for (const id of ids) {
                        const node = document.querySelector('.sg-geo[data-geo-id="' + id + '"]');
                        const box = node.getBoundingClientRect(), x = box.x + box.width / 2, y = box.y + box.height / 2;
                        if (box.width < 2 || box.height < 2 || x < 0 || x >= innerWidth || y < 0 || y >= innerHeight) continue;
                        const hit = document.elementFromPoint(x, y);
                        if (hit && hit.closest('.sg-geo.is-pick:not(.is-off)') && hit !== node) continue;
                        return { id, x, y, pointerEvents: getComputedStyle(node).pointerEvents };
                    }
                    return null;
                }""", snapshot["excludedIds"])
                checks["excluded_pointer_target_observed"] = target is not None
                if target:
                    checks["excluded_pointer_is_disabled"] = target["pointerEvents"] == "none"
                    page.mouse.click(target["x"], target["y"])
                    checks["excluded_mouse_cannot_change_selection"] = page.locator(
                        f'[data-sg-tbody] tr[data-geo-id="{geo_id}"].is-on'
                    ).count() == 1
                    excluded = page.locator(f'.sg-geo[data-geo-id="{target["id"]}"]')
                    excluded.focus()
                    checks["negative_keyboard_test_reaches_target"] = excluded.evaluate(
                        "node => document.activeElement === node"
                    )
                    page.keyboard.press("Enter")
                    enter_unchanged = page.locator(
                        f'[data-sg-tbody] tr[data-geo-id="{geo_id}"].is-on'
                    ).count() == 1
                    page.keyboard.press("Space")
                    checks["excluded_enter_and_space_cannot_change_selection"] = (
                        enter_unchanged and page.locator(
                            f'[data-sg-tbody] tr[data-geo-id="{geo_id}"].is-on'
                        ).count() == 1
                    )
            elif scenario == "excluded-selection":
                checks["excluded_selection_remains_cleared"] = (
                    page.locator(".sg-geo.is-on").count() == 0
                    and page.locator('.sg-geo[aria-pressed="true"]').count() == 0
                    and page.locator("[data-sg-tbody] tr[data-geo-id].is-on").count() == 0
                )
                checks["empty_filter_disables_all_named_boundaries"] = page.locator(".sg-geo.is-pick").evaluate_all(
                    """nodes => nodes.length > 0 && nodes.every(node =>
                    node.classList.contains('is-off') && node.getAttribute('tabindex') === '-1' &&
                    node.getAttribute('aria-disabled') === 'true')"""
                )
                checks["cleared_selection_does_not_refetch_detail"] = (
                    sum("/sanctions-geography-entries/" in url for url in requests) == shard_count_before == 1
                )
            else:
                drawable = {str(row["id"]) for row in effective_topology["objects"]["countries"]["geometries"]
                            if row.get("id") is not None and str(row["id"])}
                missing = [row for row in projection["countries"] if str(row["geo_id"]) not in drawable]
                expected_count = len(projection.get("unresolved_geography", [])) + len(missing)
                observations["newly_known_off_map_countries"] = len(missing)
                checks["fixture_contains_topology_only_off_map_rows"] = len(missing) > 0
                checks["pending_unresolved_view_reconciles_all_rows"] = (
                    page.locator("[data-sg-tbody] tr").count() == expected_count
                )
                table_rows = page.locator("[data-sg-tbody] tr").evaluate_all(
                    "nodes => nodes.map(node => Array.from(node.cells, cell => cell.innerText.trim()))"
                )
                expected_reason = ("已计数，但 110m 地图中没有该边界" if locale == "zh"
                                   else "Counted, but this boundary is not in the 110m map")
                checks["new_off_map_countries_are_visible"] = all(
                    any(len(cells) == 3 and cells[0] == row["country"] and cells[2] == expected_reason
                        for cells in table_rows) for row in missing
                )
                checks["unresolved_view_keeps_map_unselectable"] = page.locator(".sg-geo.is-pick").evaluate_all(
                    """nodes => nodes.length > 0 && nodes.every(node =>
                    node.classList.contains('is-off') && node.getAttribute('tabindex') === '-1' &&
                    node.getAttribute('aria-disabled') === 'true')"""
                )
                checks["unresolved_view_does_not_request_detail"] = shard_count_before == 0 and not any(
                    "/sanctions-geography-entries/" in url for url in requests
                )

        checks["projection_fetched_once"] = sum(url.endswith("/sanctions-geography-data.json") for url in requests) == 1
        checks["no_page_errors"] = not errors
        checks["no_horizontal_document_overflow"] = page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth + 1"
        )
        observations["page_errors"] = errors
        observations["shard_requests"] = sum("/sanctions-geography-entries/" in url for url in requests)
        filename = f"{scenario}-{width}-{locale}.png"
        page.screenshot(path=str(output / filename), full_page=True)
        return {"scenario": scenario, "width": width, "locale": locale, "theme": "dark",
                "file": filename, "forced_language_events": 0, "checks": checks,
                "observations": observations, "passed": all(checks.values())}
    finally:
        context.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument("--width", type=int, choices=WIDTHS)
    parser.add_argument("--locale", choices=LOCALES)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = (args.output or repo / "mockups/evidence/sanctions-geography/boot").resolve()
    output.mkdir(parents=True, exist_ok=True)
    site = repo / "site"
    projection = json.loads((site / "sanctions-geography-data.json").read_text(encoding="utf-8"))
    topology = json.loads((site / "world-110m.json").read_text(encoding="utf-8"))
    artifacts = {key: file_hash(repo / path) for key, path in {
        "data_sha256": "site/sanctions-geography-data.json",
        "page_sha256": "site/sanctions-geography.html",
        "css_sha256": "site/sanctions-geography.css",
        "js_sha256": "site/sanctions-geography.js",
        "driver_sha256": "scripts/probe_sanctions_geography_boot.py",
    }.items()}
    from playwright.sync_api import sync_playwright

    server, port = serve(site)
    results = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for scenario in (args.scenario,) if args.scenario else SCENARIOS:
                    for width in (args.width,) if args.width else WIDTHS:
                        for locale in (args.locale,) if args.locale else LOCALES:
                            result = run_case(browser, site, port, output, scenario, width, locale, projection, topology)
                            results.append(result)
                            print(json.dumps({"scenario": scenario, "width": width, "locale": locale,
                                              "passed": result["passed"],
                                              "failed_checks": [key for key, ok in result["checks"].items() if not ok]}),
                                  flush=True)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    receipt = {
        "schema": "f02x1.boot_evidence.v1",
        "driver": "scripts/probe_sanctions_geography_boot.py",
        "artifacts": artifacts,
        "projection_id": projection["projection_id"],
        "source_identity": projection["source_identity"],
        "note": "Real normal boot and frozen committed projection/shards. Topology delivery is delayed or failed locally; the explicitly labelled unresolved-register fixture omits one existing boundary without changing committed topology. No live source outage, forced later language event or test seam is asserted.",
        "results": results,
    }
    (output / "observations.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if results and all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
