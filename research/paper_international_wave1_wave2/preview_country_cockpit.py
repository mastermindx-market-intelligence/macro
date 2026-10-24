"""Reproducible source-backed design preview; does not publish or edit Paper."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from os.path import relpath
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from collectors.intl_country_sources import collect_country_inputs, merge_country_inputs, BIS_CPI, BIS_POLICY, IMF_XLSX, TW_PAGE
from lib.intl_country_assessment import build_country_assessments
from engine import i18n
from jinja2 import Environment, FileSystemLoader

BASE = "1ed4b870a426ff3cafb439152072c5bf47858551"
NAMES = {BIS_CPI:"WS_LONG_CPI.zip", BIS_POLICY:"WS_CBPOL.zip",
         IMF_XLSX:"weojul2026.xlsx", TW_PAGE:"taiwan-20260814.html"}

DOCUMENT = """<!doctype html>
<html lang="en" data-theme="dark" data-lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>International markets — country intelligence preview</title>
<link rel="stylesheet" href="theme.css">
<link rel="stylesheet" href="navigation-refresh.css">
<style>body{margin:0;background:var(--bg);color:var(--text)}{% include 'intl_country_cockpit.css' %}</style>
</head><body>
{% include '_site_nav.html.j2' %}
<main>
{% include 'intl_country_cockpit.html.j2' %}
<details id="intl-analysis-tools"><summary>{{ t('Data & research tools','数据与研究工具') }} <span aria-hidden="true">+</span></summary>
<p><a href="intl.html#lb-board">{{ t('Performance and currency','表现与汇率') }}</a> ·
<a href="intl_cycles.html">{{ t('Country cycle research','地区周期研究') }}</a> ·
<a href="intl_stocks.html">{{ t('International stocks','国际股票') }}</a></p>
</details>
</main><script>{% include 'intl_country_cockpit.js' %}</script>
</body></html>"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reuse-inputs", action="store_true")
    args = parser.parse_args()
    args.source_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).isoformat()
    path = args.output_dir / "country_inputs.json"
    if args.reuse_inputs:
        inputs = json.loads(path.read_text())
    else:
        def fetch_bytes(url, *, max_bytes):
            cached = args.source_dir / NAMES.get(url, sha256(url.encode()).hexdigest()+".source")
            if cached.exists():
                blob = cached.read_bytes()
                if len(blob) > max_bytes:
                    raise ValueError("source_size_limit")
                return blob
            started = time.monotonic()
            request = urllib.request.Request(url, headers={"User-Agent":"Mastermind country research"})
            chunks, size = [], 0
            with urllib.request.urlopen(request, timeout=20) as response:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > max_bytes or time.monotonic()-started > 45:
                        raise ValueError("source_budget_exceeded")
            blob = b"".join(chunks)
            cached.write_bytes(blob)
            return blob
        inputs = collect_country_inputs(fetch_bytes, retrieved_at=retrieved)
        inputs.pop("cpi_series", None)
        path.write_text(json.dumps(inputs, ensure_ascii=False, indent=2)+"\n")
    inputs = merge_country_inputs(json.loads((ROOT/"config/intl_country_baseline.json").read_text()), inputs,
                                  preserve_custody=args.reuse_inputs)
    path.write_text(json.dumps(inputs, ensure_ascii=False, indent=2)+"\n")
    result = subprocess.run(["git", "show", BASE+":data/intl/latest.json"], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    latest = json.loads(result.stdout)
    replay_path = args.output_dir / 'market_replay.json'
    if replay_path.exists():
        replay = json.loads(replay_path.read_text())
        for record in latest['records']:
            if record['cc'] in replay:
                record['equity'] = replay[record['cc']]
    currency_replay_path = args.output_dir / "currency_replay.json"
    if currency_replay_path.exists():
        currency_replay = json.loads(currency_replay_path.read_text())
        for record in latest["records"]:
            if record["cc"] in currency_replay:
                record["currency_observation"] = currency_replay[record["cc"]]
    today = datetime.now(timezone.utc).date()
    assessment = build_country_assessments(latest, today=today,
                                          official=inputs["official"], forecasts=inputs["forecasts"],
                                          forecast_archive=inputs.get("forecast_archive"),
                                          policy_decisions=inputs.get("policy_decisions"),
                                          policy_reviews=inputs.get("policy_reviews"),
                                          commentary=json.loads((ROOT/"config/intl_country_commentary.json").read_text())["countries"])
    environment = Environment(loader=FileSystemLoader(ROOT/"templates"), autoescape=False)
    environment.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
    html = environment.from_string(DOCUMENT).render(intl_analysis=assessment)
    html = "\n".join(line if line.strip() else "" for line in html.split("\n"))
    (args.output_dir/"intl_country_preview.html").write_text(html)
    # Full existing template/publisher with an explicitly unknown legacy workspace.
    # Only the new country facts are source-backed; no synthetic return qualifies.
    from engine.intl_workspace_overview import build_workspace_overviews
    from lib.intl_library_mount import render_international_pages
    summary = latest["summary"]
    vm = {"latest":latest,"built":retrieved,"records":latest["records"],
          "summary":summary,"rankings":latest.get("rankings",{}),
          "heatmap":latest.get("heatmap",[]),"periphery":latest.get("periphery"),
          "sector_board":[],"setups":{},"perf":None,"rates":None,
          "risk_desk":None,"CGL":None,"turn_board":[],"turn_events":[],
          "rotation_ranks":[],"bench_note":None,"intl_analysis":assessment,
          "intl_workspace":build_workspace_overviews(None)}
    catalogue = json.loads((ROOT/"config/intl_library_catalogue.json").read_text())
    macro_html, stocks_html = render_international_pages(environment.get_template("intl.html.j2"),vm,catalogue=catalogue)
    macro_html = "\n".join(line if line.strip() else "" for line in macro_html.split("\n"))
    (args.output_dir/"intl_integrated_preview.html").write_text(macro_html)
    (args.output_dir/"intl_stocks_integrated_preview.html").write_text(stocks_html)

    (args.output_dir/"assessment.json").write_text(json.dumps(assessment, ensure_ascii=False, indent=2)+"\n")
    paper_receipt_path = ROOT / "research/paper_international_wave1_wave2/paper_r12_receipt.json"
    paper_receipt = json.loads(paper_receipt_path.read_text()) if paper_receipt_path.exists() else {}
    manifest = {"base":BASE, "kind":"SOURCE_BACKED_LOCAL_RENDER_NOT_PUBLISHED",
                "paper_design":{"receipt":relpath(paper_receipt_path, args.output_dir),
                                "applied":paper_receipt.get("finish_observed", False),
                                "scope":"Only effects bound by the named Paper receipt are asserted; later rendered content is not compared.",
                                "boards":paper_receipt.get("boards", {})},
                "html_sha256":{"intl_country_preview.html":sha256(html.encode()).hexdigest(),
                               "intl_integrated_preview.html":sha256(macro_html.encode()).hexdigest(),
                               "intl_stocks_integrated_preview.html":sha256(stocks_html.encode()).hexdigest()},
                "rendered_at":retrieved, "countries":assessment["count"],
                "forecasts":assessment["forecast_count"], "forecast_archive_count":assessment["forecast_archive_count"],
                "outlook_coverage":{c["cc"]:list(c["outlook"]["series"]) for c in assessment["countries"]}, "sources":inputs.get("sources"),
                "policy_coverage":{c["cc"]:c["policy_decision"]["state"] for c in assessment["countries"] if c["policy_decision"]},
                "world_brief":assessment["world_brief"],
                "currency_coverage":{c["cc"]:c["market"]["currency_observation"] for c in assessment["countries"]},
                "errors":inputs.get("errors"), "errors_observed_at":inputs.get("errors_observed_at"),
                "sha256":sha256(html.encode()).hexdigest()}
    (args.output_dir/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest), flush=True)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
