"""Build synthetic component fixtures using the existing held observer, without adoption.

Run from repository root with an explicit local reference commit. No network,
market-data writes, ref changes, new observer, or production publisher is used.
The canonical capture_page_evidence.py subsequently captures these local fixtures.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

from jinja2 import Environment, FileSystemLoader
from lib import cn_calendar, nyse_calendar
from lib.illus import illus

ROOT = Path(__file__).resolve().parents[2]


def reference_module(ref: str, path: str, name: str):
    raw = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT,
                         capture_output=True, check=True).stdout
    module = types.ModuleType(name)
    module.__file__ = f"{ref}:{path}"
    sys.modules[name] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    return module, {"ref": ref, "path": path, "git_blob": blob,
                    "sha256": hashlib.sha256(raw).hexdigest()}


def build(output: Path, ref: str) -> dict:
    observer, observer_source = reference_module(ref, "lib/pullback_observation.py", "lib.pullback_observation")
    presenter, presenter_source = reference_module(ref, "lib/china_pullback_view.py", "_held_china_presenter")
    now = datetime.now(timezone.utc)
    prices = [100.0] * 63 + [99.5,98.8,99.1,98.0,97.5,96.8,97.1,95.4,94.8,94.0,93.3,92.6,93.2]
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
    fragment = env.from_string('{% import "_risk_radar_pullback_depth.html.j2" as p %}{{ p.detail(market, view) }}')
    css = (ROOT / "templates/theme.css").read_text() + "\n" + (ROOT / "templates/illus.css").read_text() + "\n" + (ROOT / "templates/_risk_radar_pullback_depth.css.j2").read_text()
    expiry = subprocess.run(["git", "show", f"{ref}:templates/_pullback_observation.js.j2"], cwd=ROOT, capture_output=True, check=True).stdout.decode()
    illustration_js = (ROOT / "templates/illus.js").read_text()
    output.mkdir(parents=True, exist_ok=True)
    # Serve the already-vendored shared dependencies locally. They are not part
    # of the source/evidence publication or any downloadable user attachment.
    asset_names = ['product-nav-icons.css'] + [f'fonts/Inter-{w}.woff2' for w in (400,500,600,700,800,900)]
    asset_hashes = {}
    for name in asset_names:
        raw = (ROOT / 'templates' / name).read_bytes()
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        asset_hashes[name] = hashlib.sha256(raw).hexdigest()
    fixtures = []
    for market, calendar, benchmark, en, zh, zone in (
        ("cn", cn_calendar, "000001.SS", "Shanghai Composite", "上证综指", cn_calendar.CST),
        ("us", nyse_calendar, "SPY", "SPY", "SPY", nyse_calendar.ET),
    ):
        expected = calendar.expected_last_session(now)
        day = expected
        days = []
        while len(days) < len(prices):
            if calendar.is_session(day):
                days.append(day)
            day -= timedelta(days=1)
        rows = [(d.isoformat(), p) for d, p in zip(reversed(days), prices)]
        observed = observer.observe(rows, expected_session=expected, is_session=calendar.is_session)
        assert observed["available"], observed
        next_day = expected + timedelta(days=1)
        while not calendar.is_session(next_day):
            next_day += timedelta(days=1)
        expiry_at = datetime.combine(next_day, calendar._CLOSE_PLUS_SETTLE, tzinfo=zone).astimezone(timezone.utc)
        observed.update(market=market, benchmark=benchmark, benchmark_en=en, benchmark_zh=zh,
                        clock="settled_close", produced_at=now.isoformat(), valid_until=expiry_at.isoformat())
        if market == "cn":
            view = presenter.present(observed)
            view_path = "held China present()"
        else:
            # Fixture-only projection. The production US adapter is NOT implemented here.
            view = {"observation": observed, "phase": observed["phase"],
                    "detail_chart_html": illus(observed["price_path"], kind="drawdown", height=188,
                        reference=0, accent="var(--down)", value_fmt="{:.1f}%", aria_en="SPY observed closing drawdown")}
            view_path = "synthetic US fixture shape + native observer + shared illus; not a production adapter"
        body = fragment.render(market=market, view=view)
        preview_css = 'body{margin:0;background:var(--bg)}main{max-width:1240px;margin:auto;padding:24px}h1{font:600 14px var(--font-ui);color:var(--muted);margin:0 0 18px}@media(max-width:680px){main{padding:12px}}'
        html = '<!doctype html><html data-theme="dark" data-lang="en" lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Risk Radar component fixture</title><style>'+css+'\n'+preview_css+'</style></head><body><main><h1><span class="l-en">ILLUSTRATIVE FIXTURE · NO LIVE MARKET DATA</span><span class="l-zh">设计测试示例 · 非真实市场数据</span></h1>'+body+'</main><script>'+illustration_js+'</script><script>'+expiry+'</script></body></html>'
        path = output / f"{market}.html"
        path.write_text(html)
        (output / f"{market}-view.json").write_text(json.dumps(view, ensure_ascii=False, indent=2)+'\n')
        fixtures.append({"market":market, "view_path":view_path, "observed_phase":observed["phase"],
                         "asof":observed["asof"], "valid_until":observed["valid_until"],
                         "synthetic_prices":True, "path":str(path), "sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    files = ["templates/_risk_radar_pullback_depth.html.j2", "templates/_risk_radar_pullback_depth.css.j2", "lib/pullback_depth_projection.py", "tests/test_risk_radar_pullback_depth_template.py"]
    proof = {"kind":"synthetic_component_integration_not_production", "generated_at":now.isoformat(),
             "local_asset_hashes":asset_hashes, "reference_status":"HELD_SOURCE_NOT_ADOPTED", "reference_sources":[observer_source,presenter_source],
             "sources":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}, "fixtures":fixtures}
    (output / "fixture-receipt.json").write_text(json.dumps(proof, indent=2)+'\n')
    return proof


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-ref", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args=parser.parse_args()
    receipt=build(args.output_dir, args.reference_ref)
    print(json.dumps({"kind":receipt["kind"],"fixtures":receipt["fixtures"]},indent=2))
