"""Exercise the candidate against checked-out Macro source data; no publication."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import re
from urllib.parse import urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
source_path = ROOT / "site/sectordata/sector_central.json"
before = hashlib.sha256(source_path.read_bytes()).hexdigest()
doc = json.loads(source_path.read_text())
spec = importlib.util.spec_from_file_location(
    "sector_paper_probe_tests", ROOT / "tests/test_sector_central_paper.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = {lang: module._coverage(doc, lang) for lang in ("en", "zh")}
assert all(result["status"] == doc["measured_read"]["status"] for result in results.values())
assert all(result["sourceUnchanged"] for result in results.values())
html_path = OUT / "sector_central.html"
html = html_path.read_text()
coverage_source = (ROOT / "templates/_sector_central_coverage.js.j2").read_text()
payload = re.search(r'<script\b[^>]*\bsrc="sector_central_data.js"[^>]*>', html)
assert payload and "data-sync" in payload.group()
assert html.count(coverage_source) == 1
assert html.index(coverage_source) > payload.end()
for identity in ("si-brief-coverage", "si-brief-coverage-title", "si-brief-coverage-note", "si-measured"):
    assert len(re.findall(r'\bid="' + re.escape(identity) + r'"', html)) == 1
assert 'href="#si-measured"' in html
assert 'href="us_stocks.html"' in html
# Drive the actual selected-record detail into the same shipped Prophet receiver.
panel_spec = importlib.util.spec_from_file_location(
    "sector_measured_probe_tests", ROOT / "tests/test_sector_central_measured_panel.py")
panel = importlib.util.module_from_spec(panel_spec)
panel_spec.loader.exec_module(panel)
selected = doc["measured_read"]["groups"][0]["group_id"]
native = panel._run(fixture=doc["measured_read"], cfg={
    "search": "?g=" + selected, "hash": "#map", "as_of": doc["as_of"]})
handoff = re.search(r'href="(us_stocks.html\?si_sector=[A-Z]+#sector-prophet-context)"', native["detail"])
assert handoff, "The real selected sector has no native Prophet handoff"
destination = urlsplit(handoff.group(1))
receiver = module._prophet_receiver("?" + destination.query, fragment="#" + destination.fragment)
state = receiver["states"][0]
assert state["status"] == "selected"
assert state["back"] == "sector_central.html?g=" + selected + "#map"
assert receiver["boardUnchanged"]
# Exercise the current US preview rows through the actual native US controller.
stocks_path = ROOT / "site/us_stocks.html"
stocks_before = hashlib.sha256(stocks_path.read_bytes()).hexdigest()
stocks_html = stocks_path.read_text()
stocks_script = re.search(r'<script\b[^>]*id="us-stocktable-data"[^>]*>(.*?)</script>', stocks_html, re.S)
assert stocks_script, "Checked-out native US stocktable payload is absent"
stocks_doc = json.loads(stocks_script.group(1))
stock_rows = stocks_doc["rows"]
clicked = module._prophet_receiver("?" + destination.query, ready=True, events=[{"type": "click"}])
assert len(clicked["calls"]) == 1
canonical_sector = clicked["calls"][0]
screener = module._screener_flow(stock_rows, [{"type": "select", "value": canonical_sector}])
native_before, native_after = screener["states"]
assert screener["results"] == [True]
assert native_before["sourceCalls"] == [] and native_before["sector"] == "all"
assert native_after["sector"] == canonical_sector
assert native_after["view"] == "table" and native_after["mode"] == "candidates"
assert native_after["inputUnchanged"] and native_after["dataRows"] == stock_rows
expected_tickers = [row["ticker"] for row in stock_rows if row.get("sector") == canonical_sector]
assert native_after["visible"] == expected_tickers
assert native_after["counts"] == {"loaded": len(stock_rows), "matched": len(expected_tickers)}
assert hashlib.sha256(stocks_path.read_bytes()).hexdigest() == stocks_before
native_receipt = {
    "scope": "Shipped US source/view owner and native selection/filter/render functions with checked-out public preview rows in a DOM harness; not browser acceptance",
    "us_page_input_sha256": stocks_before,
    "stocktable_source_sha256": hashlib.sha256((ROOT / "templates/stocktable.js").read_bytes()).hexdigest(),
    "sector_id": selected, "canonical_sector": canonical_sector,
    "loaded_rows": len(stock_rows), "matched_loaded_rows": len(expected_tickers),
    "registered_sector_choices": len(native_after["options"]),
    "context_requires_explicit_click": native_before["sourceCalls"] == [],
    "source_mode": native_after["mode"], "view": native_after["view"],
    "empty_loaded_result_message": native_after["emptyMessage"],
    "input_unchanged": native_after["inputUnchanged"],
    "fetched_additional_rows": False, "browser_acceptance": False,
}
(OUT / "screener-source-probe.json").write_text(json.dumps(native_receipt, indent=2, ensure_ascii=False) + "\n")

after = hashlib.sha256(source_path.read_bytes()).hexdigest()
assert before == after
receipt = {
    "scope": "Actual checked-out sector payload in shipped coverage, selected measured detail and Prophet context controllers; DOM harness and actual template composition, not browser acceptance",
    "input_sha256": before,
    "source_as_of": doc.get("as_of"),
    "generation": doc["measured_read"]["generation"],
    "coverage": {key: doc["measured_read"]["cohort"].get(key) for key in ("expected_n", "measured_n", "horizon", "window_sessions", "missing")},
    "render_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest(),
    "controller_sha256": hashlib.sha256(coverage_source.encode()).hexdigest(),
    "results": results,
    "coverage_after_synchronous_payload": True,
    "unique_hosts_and_native_evidence_target": True,
    "canonical_prophet_link_present": True,
    "basket_initializer_required": False,
    "input_unchanged": before == after,
    "selected_sector_handoff": {"sector_id": selected, "native_link": handoff.group(1),
        "prophet_subject": state["subject"], "return_href": state["back"],
        "board_unchanged": receiver["boardUnchanged"], "measurements_or_clock_from_url": False},
    "native_screener_handoff": native_receipt,
    "browser_acceptance": False,
    "production_published": False,
}
(OUT / "coverage-source-probe.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(receipt, indent=2, ensure_ascii=False))
