#!/usr/bin/env python3
"""Render synthetic crypto inputs through the actual repaired producer paths.

This is a local producer/component proof fixture, not a live data or full-route
proof. Reuses render_illus_gap_fixture's presentation and the production assets.
Browser screenshots and acceptance are separate from successful generation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import math
import re
import shutil
import sys
from datetime import date, timedelta
from html import escape
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (96, 140, 240)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")


def fixture_specs() -> list[dict]:
    dates = [(date(2026, 8, 1) + timedelta(days=i)).isoformat() for i in range(96)]
    prices = [round(65000 + 45 * i + 950 * math.sin(i / 9) + 120 * math.cos(i / 3), 2)
              for i in range(96)]
    snapshot = {
        "symbol": "BTC", "as_of": dates[-1], "state": "Firm", "tone": "bull",
        "price": prices[-1], "change_24h": 2.0, "change_30d": 8.0,
        "history_days": 0, "history_chip": "Building",
        "spark_dates": [], "spark_values": [],
    }
    internal = list(prices)
    for i in (37, 38, 39):
        internal[i] = None
    tail = list(prices)
    tail[-4:] = [None] * 4
    legacy_prices = [str(round(250 + 0.3 * i + 9 * math.sin(i / 9), 4)) for i in range(96)]
    for i, value in [(37, "0"), (38, "-1"), (39, "inf"), (40, None)]:
        legacy_prices[i] = value
    return [
        {
            "id": "deep-internal-gap", "producer": "deep_history",
            "title_en": "Deep history · internal gap", "title_zh": "深度历史 · 中间缺失",
            "note_en": "Three supplied unavailable closes stay disconnected.",
            "note_zh": "给定收盘价中的三个缺失位置保持断开。",
            "dates": dates, "columns": {"close": internal}, "snapshot_row": dict(snapshot),
            "expected_slots": 93, "expected_observations": 90, "expected_missing": 3,
            "expected_runs": 2, "expected_tail": False,
        },
        {
            "id": "deep-unavailable-tail", "producer": "deep_history",
            "title_en": "Deep history · unavailable tail", "title_zh": "深度历史 · 尾部缺失",
            "note_en": "The final four supplied dates remain unavailable; the last point is historical.",
            "note_zh": "最后四个给定日期仍然缺失；最后一个观测点属于历史数据。",
            "dates": dates, "columns": {"close": tail}, "snapshot_row": dict(snapshot),
            "expected_slots": 94, "expected_observations": 90, "expected_missing": 4,
            "expected_runs": 1, "expected_tail": True,
        },
        {
            "id": "legacy-invalid-gap", "producer": "legacy_parquet",
            "title_en": "Legacy parquet · invalid prices", "title_zh": "历史 Parquet · 无效价格",
            "note_en": "Zero, negative, nonfinite and null prices keep their supplied dates as gaps.",
            "note_zh": "零值、负值、非有限值与空价格均保留原始日期，并显示为缺失。",
            "dates": dates,
            "columns": {
                "current_price": legacy_prices, "coin_id": "f02alt-fixture",
                "source": "fixture-market", "symbol": "F02ALT", "name": "Synthetic F02 asset",
                "market_cap_rank": 1, "change_24h_pct": 2.0, "change_7d_pct": 4.0,
                "change_30d_pct": 8.0, "market_cap": 1000000.0, "total_volume": 50000.0,
            },
            "expected_slots": 94, "expected_observations": 90, "expected_missing": 4,
            "expected_runs": 2, "expected_tail": False,
        },
        {
            "id": "complete-baseline", "producer": "deep_history",
            "title_en": "Deep history · complete baseline", "title_zh": "深度历史 · 完整基线",
            "note_en": "The existing last-90-observation window stays continuous.",
            "note_zh": "原有最近 90 个有效观测值构成的区间保持连续。",
            "dates": dates, "columns": {"close": prices}, "snapshot_row": dict(snapshot),
            "expected_slots": 90, "expected_observations": 90, "expected_missing": 0,
            "expected_runs": 1, "expected_tail": False,
        },
    ]


def produce(spec: dict, output: Path, crypto, universe, pd) -> tuple[dict, str | None]:
    frame = pd.DataFrame(spec["columns"], index=pd.to_datetime(spec["dates"]))
    parquet_file = None
    if spec["producer"] == "legacy_parquet":
        parquet_root = output / "inputs" / spec["id"]
        parquet_root.mkdir(parents=True, exist_ok=True)
        parquet_path = parquet_root / "market_f02alt.parquet"
        frame.to_parquet(parquet_path, engine="pyarrow")
        parquet_file = str(parquet_path.relative_to(output))
        snapshot = universe.load_universe_snapshot(root=parquet_root)
        if snapshot["excluded"] or len(snapshot["rows"]) != 1:
            raise RuntimeError(f"Legacy fixture was not admitted: {snapshot}")
        rows = snapshot["rows"]
    else:
        rows = [dict(spec["snapshot_row"])]

    def fixture_read(group, name):
        if spec["producer"] == "deep_history" and (group, name) == ("coinbase", "btc_daily"):
            return frame
        return pd.DataFrame()

    with patch.object(crypto.store, "read", side_effect=fixture_read):
        row = crypto._enrich_universe(rows)[0]
    values = row["spark_values"]
    dates = row["spark_dates"]
    missing_dates = [day for day, value in zip(dates, values) if value is None]
    observed = [(day, value) for day, value in zip(dates, values) if value is not None]
    path_match = re.search(r'class="ilx-path" d="([^"]+)"', row["spark"])
    runs = path_match.group(1).count("M") if path_match else 0
    actual = {
        "slots": len(dates), "observations": len(observed), "missing": len(missing_dates),
        "runs": runs, "tail": bool(values and values[-1] is None),
    }
    expected = {key: spec[f"expected_{key}"] for key in actual}
    if actual != expected or row["history_days"] != len(observed):
        raise RuntimeError(f"{spec['id']} contract mismatch: {actual} != {expected}")
    if ("Latest missing" in row["spark"]) != actual["tail"]:
        raise RuntimeError(f"{spec['id']} latest-observation disclosure mismatch")
    return {
        "id": spec["id"], "producer": spec["producer"], **actual,
        "first_date": dates[0], "last_date": dates[-1],
        "last_observed_date": observed[-1][0], "missing_dates": missing_dates,
        "chart_case_ids": [f"{spec['id']}-{width}" for width in WIDTHS],
        "row": row,
    }, parquet_file


def case_card(spec: dict, result: dict, presentation) -> str:
    bilingual = presentation.bilingual
    missing = ", ".join(result["missing_dates"]) or "—"
    metadata = (
        f'<div class="crypto-case-id"><code>{escape(spec["id"])}</code></div>'
        '<dl class="crypto-meta">'
        f'<div><dt>{bilingual("Supplied display window", "给定显示区间")}</dt>'
        f'<dd>{result["first_date"]} → {result["last_date"]}</dd></div>'
        f'<div><dt>{bilingual("Last observed", "最后有效观测")}</dt>'
        f'<dd>{result["last_observed_date"]}</dd></div>'
        f'<div><dt>{bilingual("Missing dates", "缺失日期")}</dt><dd>{missing}</dd></div>'
        f'<div><dt>{bilingual("History / display slots", "有效历史 / 显示位置")}</dt>'
        f'<dd>{result["observations"]} / {result["slots"]}</dd></div></dl>'
    )
    compact = []
    for width in WIDTHS:
        chart_id = f'{spec["id"]}-{width}'
        compact.append(
            f'<div id="{chart_id}" class="compact-case" data-chart-case="{chart_id}" '
            f'data-width="{width}" style="width:{width}px">'
            f'<h3>{bilingual(f"{width}px width · 42px chart", f"宽 {width}px · 图高 42px")}</h3>'
            f'{result["row"]["spark"]}</div>'
        )
    return presentation.card(
        spec["id"], spec["title_en"], spec["title_zh"],
        spec["note_en"], spec["note_zh"],
        metadata + '<div class="compact-grid">' + "".join(compact) + "</div>",
    )


def page(theme: str, lang: str, source_head: str, specs, results, presentation) -> str:
    # The existing specimen owns the shell, asset links, responsive styling,
    # theme/language behavior and production reveal preparation.
    shell = presentation.page(theme, lang, source_head)
    head, separator, _body = shell.partition("<body>")
    if not separator:
        raise RuntimeError("The shared fixture presentation has no body boundary")
    head = head.replace("Illustration gaps", "Crypto producer gaps")
    extra_style = """
<style>
.fixture-grid.crypto-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); --tone: var(--ink-up, var(--up)); }
.crypto-case-id { margin: 0 0 12px; font-size: 12px; overflow-wrap: anywhere; color: var(--muted); }
.crypto-meta { margin: 0 0 20px; font-size: 12px; line-height: 1.5; }
.crypto-meta > div { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); gap: 12px; margin: 6px 0; }
.crypto-meta dt { color: var(--muted); }
.crypto-meta dd { margin: 0; overflow-wrap: anywhere; }
.crypto-grid .compact-grid { gap: 24px; }
@media (max-width: 1100px) { .fixture-grid.crypto-grid { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 360px) { .crypto-grid .fixture-card { padding: 16px; } }
</style>
"""
    head = head.replace("</head>", extra_style + "</head>")
    b = presentation.bilingual
    other_theme = "light" if theme == "dark" else "dark"
    other_lang = "zh" if lang == "en" else "en"
    cards = "".join(case_card(spec, result, presentation) for spec, result in zip(specs, results))
    return head + f"""<body><main class="fixture">
<div class="eyebrow">F02 · {b("Crypto producer verification", "加密资产生产路径验证")}</div>
<h1>{b("Missing prices retain their dates", "价格缺失，日期保留")}</h1>
<p class="intro">{b("Synthetic inputs pass through the actual deep-history and legacy-parquet producers and the shared production renderer. This fixture is local integration evidence; it is not live data or a full product-route claim.", "合成输入经过实际深度历史与历史 Parquet 生产路径及共享生产渲染器。此示例提供本地集成证据，不代表实时数据或完整产品页面验证。")}</p>
<nav class="fixture-controls" aria-label="Fixture display">
<a href="{other_theme}-{lang}.html">{b("Switch theme", "切换主题")}</a>
<a href="{theme}-{other_lang}.html">{b("中文", "English")}</a>
<a href="fixtures.json">{b("Synthetic inputs", "合成输入")}</a>
<a href="fixture-manifest.json">{b("Evidence manifest", "证据清单")}</a>
</nav><div class="fixture-grid crypto-grid">{cards}</div>
<footer>{b("Synthetic fixture · no collection, publication or live data · browser acceptance is recorded separately", "合成测试示例 · 无采集、发布或实时数据 · 浏览器验收单独记录")}
<br>{b("Source base", "源代码基线")}: {escape(source_head)}
<br>{b("Exact rendered source and fixture hashes are bound in fixture-manifest.json.", "实际渲染源文件与示例输入的哈希记录于 fixture-manifest.json。")}</footer>
</main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-head", required=True,
                        help="Source base revision; actual loaded source hashes bind local changes.")
    parser.add_argument("--dependency-root", type=Path,
                        help="Optional qualified dependency tree; must match local producer/renderer files.")
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    if args.dependency_root:
        sys.path.insert(0, str(args.dependency_root.resolve()))
    pd = importlib.import_module("pandas")
    crypto = importlib.import_module("scripts.build_crypto")
    universe = importlib.import_module("engine.crypto_universe")
    renderer = importlib.import_module("lib.illus")
    presentation = importlib.import_module("scripts.render_illus_gap_fixture")
    for module, relative_path in [
        (crypto, "scripts/build_crypto.py"), (universe, "engine/crypto_universe.py"),
        (renderer, "lib/illus.py"),
    ]:
        if digest(Path(module.__file__)) != digest(ROOT / relative_path):
            raise RuntimeError(f"Loaded source does not match the working source: {relative_path}")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    specs = fixture_specs()
    write_json(output / "fixtures.json", {
        "schema": "f02.crypto_gap_fixture/v1", "synthetic": True, "cases": specs,
    })
    results = []
    parquet_files = []
    for spec in specs:
        result, parquet_file = produce(spec, output, crypto, universe, pd)
        results.append(result)
        if parquet_file:
            parquet_files.append(parquet_file)
    receipt_results = []
    for result in results:
        row = result["row"]
        receipt_results.append({
            **{key: value for key, value in result.items() if key != "row"},
            "row": {key: value for key, value in row.items() if key != "spark"},
            "spark_sha256": hashlib.sha256(row["spark"].encode("utf-8")).hexdigest(),
        })
    write_json(output / "producer-results.json", receipt_results)

    assets = ("illus.css", "illus.js", "theme.css", "product-nav-icons.css")
    for name in assets:
        shutil.copyfile(ROOT / "templates" / name, output / name)
    fonts = ROOT / "templates" / "fonts"
    if fonts.is_dir():
        shutil.copytree(fonts, output / "fonts", dirs_exist_ok=True)
    pages = []
    for theme in ("dark", "light"):
        for lang in ("en", "zh"):
            name = f"{theme}-{lang}.html"
            (output / name).write_text(page(theme, lang, args.source_head, specs, results, presentation),
                                       encoding="utf-8")
            pages.append(name)
    loaded_sources = {}
    for name, module in sorted(sys.modules.items()):
        if name.split(".")[0] not in {"engine", "lib", "scripts"}:
            continue
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).suffix == ".py":
            path = Path(filename).resolve()
            loaded_sources[name] = {"path": str(path), "sha256": digest(path)}
    asset_files = [*assets, *(str(p.relative_to(output)) for p in sorted((output / "fonts").rglob("*"))
                              if p.is_file())]
    manifest = {
        "schema": "f02.crypto_gap_proof/v1",
        "source_head": args.source_head,
        "source_head_role": "base revision; loaded source hashes identify the rendered implementation",
        "synthetic": True, "collectors": False, "publish": False, "live_data": False,
        "full_route_proof": False,
        "generator_sha256": digest(Path(__file__)),
        "presentation_sha256": digest(Path(presentation.__file__)),
        "loaded_source_sha256": loaded_sources,
        "fixture_sha256": {name: digest(output / name) for name in
                           ["fixtures.json", "producer-results.json", *parquet_files]},
        "asset_sha256": {name: digest(output / name) for name in asset_files},
        "page_sha256": {name: digest(output / name) for name in pages},
        "packages": {name: importlib.metadata.version(name)
                     for name in ("pandas", "numpy", "jinja2", "PyYAML", "pyarrow")},
        "cases": [{key: value for key, value in result.items() if key != "row"} for result in results],
        "chart_selector": "[data-chart-case]",
        "chart_widths": list(WIDTHS), "chart_height": 42,
        "required_viewports": [1440, 390, 320],
        "capture_preparation": "Production ilxReveal(document) on load; ?natural=1 retains reveal-on-scroll",
        "browser_acceptance": "NOT_RUN",
    }
    write_json(output / "fixture-manifest.json", manifest)
    print(json.dumps({"output": str(output), "pages": pages,
                      "chart_cases": [case for result in results for case in result["chart_case_ids"]],
                      "browser_acceptance": "NOT_RUN"}))


if __name__ == "__main__":
    main()

