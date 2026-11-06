#!/usr/bin/env python3
"""Build an offline F02 illustration specimen from the actual shared renderer.

This produces review fixtures only: no collection, publication, or live data.
Run from a qualified source checkout, then serve the output on loopback for
dark/light x EN/ZH x 1440/390 browser verification. Source hashes bind the
rendered inputs; screenshots and visual acceptance must be recorded separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from html import escape
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.illus import illus  # noqa: E402

INPUTS = (
    "lib/illus.py", "templates/illus.css", "templates/illus.js",
    "templates/theme.css", "templates/product-nav-icons.css",
)


def bilingual(en: str, zh: str) -> str:
    return f'<span class="l-en">{escape(en)}</span><span class="l-zh">{escape(zh)}</span>'


def series(values: list, count: int = 8) -> dict:
    start = date(2026, 10, 26)
    return {"dates": [(start + timedelta(days=i)).isoformat() for i in range(count)], "vals": values}


def chart(values: list, *, height: int = 190, count: int = 8, title: str, **kwargs) -> str:
    return illus(series(values, count), height=height, unit_en="%", unit_zh="%",
                 aria_en=title + "; synthetic fixture", **kwargs)


def card(key: str, en: str, zh: str, note_en: str, note_zh: str, body: str) -> str:
    return (f'<section class="fixture-card" data-case="{key}" aria-labelledby="{key}-title">'
            f'<h2 id="{key}-title">{bilingual(en, zh)}</h2>'
            f'<p>{bilingual(note_en, note_zh)}</p>{body}</section>')


def page(theme: str, lang: str, source_head: str) -> str:
    examples = [
        card("complete", "Complete history", "完整历史", "All eight dates contain an observation.",
             "八个日期均有观测值。", chart([1, 3, 2, 4, 6, 5, 7, 8], title="Complete history")),
        card("internal-gap", "A visible gap", "缺失处断开", "The line never bridges an unavailable observation.",
             "缺失的观测值之间不连线。", chart([1, 3, 2, None, 6, 5, 7, 8], title="Internal missing observation")),
        card("missing-tail", "Latest unavailable", "最新值缺失", "The supplied date window stays intact.",
             "保留完整的给定日期区间。", chart([1, 3, 2, 8], title="Short value array; four unavailable tail slots")),
        card("isolated-zero", "Zero is observed", "零值有效", "Isolated observations stay visible; missing slots stay empty.",
             "独立观测点仍可见，缺失位置保持空白。",
             chart([None, 2, None, 0, 4, None, 6, 7], title="Leading gaps, isolated point and real zero", reference=0)),
        card("sampled", "Sparse long history", "稀疏长历史", "Sampling keeps extremes without reconnecting separate runs.",
             "采样保留极值，不跨缺失区间连线。",
             chart([10 if i == 77 else -5 if i == 150 else None if i in (55, 56, 130) else 2 + (i % 11) / 4
                    for i in range(221)], count=221, max_points=8, title="Sampled discontinuous history")),
        card("honest-null", "Not enough history", "历史不足", "Too few observations produce an honest empty state.",
             "观测值不足时明确显示暂无历史。", chart([1, None, None, 2], title="Insufficient history")),
    ]
    compact = []
    for key, width, values, en, zh in [
        ("compact-gap-96", 96, [1, 3, 2, None, 6, 5, 7, 8], "96px · Gap", "96px · 缺失"),
        ("compact-tail-96", 96, [1, 3, 2, 8], "96px · Tail missing", "96px · 尾部缺失"),
        ("compact-tail-140", 140, [1, 3, 2, 8], "140px · Tail missing", "140px · 尾部缺失"),
        ("compact-zero-240", 240, [1, 3, None, 4, 6, 5, 7, 0], "240px · Latest zero", "240px · 最新值为零"),
    ]:
        compact.append(f'<div class="compact-case" data-case="{key}" style="width:{width}px">'
                       f'<h3>{bilingual(en, zh)}</h3>'
                       + chart(values, height=42, title=en) + '</div>')
    other_theme = "light" if theme == "dark" else "dark"
    other_lang = "zh" if lang == "en" else "en"
    return f'''<!doctype html>
<html lang="{"zh-CN" if lang == "zh" else "en"}" data-theme="{theme}" data-lang="{lang}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F02 · Illustration gaps · {theme} · {lang}</title>
<link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="illus.css">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text); }}
.fixture {{ max-width: 1360px; margin: auto; padding: var(--sp-6, 24px); }}
.fixture h1 {{ margin: 8px 0 12px; font-size: var(--fs-h1, 28px); line-height: 1.2; }}
.fixture p {{ color: var(--muted); line-height: 1.5; }}
.fixture .intro {{ max-width: 70ch; margin: 0 0 20px; }}
.fixture-controls {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0 24px; }}
.fixture-controls a {{ padding: 10px 14px; min-height: 44px; border: 1px solid var(--line);
  border-radius: var(--r-ctl, 8px); color: var(--text); background: var(--panel); text-decoration: none; }}
.fixture-controls a:focus-visible {{ outline: 2px solid var(--ink-link, var(--link)); outline-offset: 3px; }}
.fixture-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--sp-4, 16px); }}
.fixture-card {{ min-width: 0; padding: var(--sp-5, 20px); background: var(--panel);
  border: 1px solid var(--line); border-radius: var(--r-card, 12px); }}
.fixture-card h2 {{ margin: 0 0 8px; font-size: var(--fs-h2, 17px); line-height: 1.35; }}
.fixture-card p {{ min-height: 44px; margin: 0 0 18px; font-size: var(--fs-body, 14px); }}
.compact-panel {{ margin-top: 16px; }}
.compact-grid {{ display: flex; align-items: flex-start; flex-wrap: wrap; gap: 28px; }}
.compact-case {{ max-width: 100%; min-width: 0; }}
.compact-case h3 {{ min-height: 36px; margin: 0 0 12px; font-size: 12px; line-height: 1.5; color: var(--text); }}
.fixture footer {{ margin-top: 20px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
@media (max-width: 980px) {{ .fixture-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
@media (max-width: 600px) {{ .fixture {{ padding: 16px; }} .fixture-grid {{ grid-template-columns: minmax(0, 1fr); }} }}
</style><script src="illus.js" defer></script>
<script>
// This is a settled component specimen. Use the production reveal API so the
// full-page capture also includes figures below the initial viewport. Natural
// scroll entry and reduced motion are verified separately in browser checks.
window.addEventListener("load", function () {{
  if (!new URLSearchParams(location.search).has("natural")) window.ilxReveal(document);
}});
</script></head>
<body><main class="fixture">
<div class="eyebrow">F02 · {bilingual("Component verification", "组件验证")}</div>
<h1>{bilingual("Missing means missing", "缺失就应明确显示")}</h1>
<p class="intro">{bilingual("Synthetic examples rendered by the shared production component. Gaps, historical values and real zero remain distinct.", "使用共享生产组件渲染的合成示例。缺失、历史值与真实零值明确区分。")}</p>
<nav class="fixture-controls" aria-label="Fixture display">
<a href="{other_theme}-{lang}.html">{bilingual("Switch theme", "切换主题")}</a>
<a href="{theme}-{other_lang}.html">{bilingual("中文", "English")}</a>
<a href="#compact">{bilingual("Compact charts", "紧凑图表")}</a>
</nav><div class="fixture-grid">{"".join(examples)}</div>
<section id="compact" class="fixture-card compact-panel" aria-labelledby="compact-title">
<h2 id="compact-title">{bilingual("Compact · 42px", "紧凑 · 42px")}</h2>
<p>{bilingual("A separate status row keeps missing-data messages off the chart.", "独立状态行使缺失提示不遮挡图表。")}</p>
<div class="compact-grid">{"".join(compact)}</div></section>
<footer>{bilingual("Synthetic fixture · no live data, collectors or publication", "合成测试示例 · 无实时数据、采集或发布")}
<br>Source: {escape(source_head)}</footer></main></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name in ("illus.css", "illus.js", "theme.css", "product-nav-icons.css"):
        shutil.copyfile(ROOT / "templates" / name, output / name)
    fonts = ROOT / "templates/fonts"
    if fonts.is_dir():
        shutil.copytree(fonts, output / "fonts", dirs_exist_ok=True)
    pages = []
    for theme in ("dark", "light"):
        for lang in ("en", "zh"):
            name = f"{theme}-{lang}.html"
            (output / name).write_text(page(theme, lang, args.source_head), encoding="utf-8")
            pages.append(name)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source_inputs = (*INPUTS, *(str(p.relative_to(ROOT)) for p in sorted(fonts.glob("Inter-*.woff2"))))
    manifest = {"source_head": args.source_head, "synthetic": True,
                "collectors": False, "publish": False,
                "input_sha256": {name: digest(ROOT / name) for name in source_inputs},
                "generator_sha256": digest(Path(__file__)),
                "page_sha256": {name: digest(output / name) for name in pages},
                "required_viewports": [1440, 390],
                "capture_preparation": "Production ilxReveal(document) on load; ?natural=1 leaves reveal-on-scroll unchanged",
                "browser_acceptance": "NOT_RUN"}
    (output / "fixture-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "pages": pages, "browser_acceptance": "NOT_RUN"}))


if __name__ == "__main__":
    main()
