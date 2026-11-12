"""Isolated browser fixture built from the actual map/embedding source.

This is component evidence, not an authenticated or deployed page. The shared
builder, loader, renderer, styles, and iframe adapter run unchanged. The HTTP
handler used by tests maps /research-tools/ to the fixture donor page.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_fixture(destination: Path, graph: dict | None = None) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("theme.css", "neural-map.css", "neural-map.js"):
        shutil.copyfile(ROOT / "templates" / name, destination / name)
    source = (ROOT / "templates/committee.html.j2").read_text()
    start = source.index("  function mulberry32(")
    end = source.index("  // ── PR-4 M1: Today's Read", start)
    graph_source = source[start:end]
    (destination / "neuralwebdata").mkdir(exist_ok=True)
    if graph is None:
        shutil.copyfile(ROOT / "site/neuralwebdata/confluence_graph.json", destination / "neuralwebdata/confluence_graph.json")
    else:
        (destination / "neuralwebdata/confluence_graph.json").write_text(json.dumps(graph))
    appearance = """<script>
    var params = new URLSearchParams(location.search);
    document.documentElement.dataset.theme=params.get('theme')||localStorage.getItem('theme')||'dark';
    document.documentElement.dataset.lang=params.get('lang')||localStorage.getItem('lang')||'en';
    </script>"""
    (destination / "committee.html").write_text("""<!doctype html><html lang="en"><head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Neural Web — candidate component verification</title>""" + appearance + """
    <link rel="stylesheet" href="theme.css"><link rel="stylesheet" href="neural-map.css">
    <style>body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-ui)}
    main{max-width:1280px;margin:32px auto;padding:0 20px}
    @media(max-width:719px){main{margin:12px auto;padding:0 8px}}</style>
    <script src="neural-map.js"></script></head><body><main>
    <div class="graph-wrap neural-map" id="graph_wrap" aria-busy="true"></div></main>
    <script>(function(){""" + graph_source + """
    window.neuralFixture={reload:loadGraph};loadGraph();})();</script></body></html>""")
    admin = (ROOT / "admin/static/app.js").read_text()
    embed_source = admin[admin.index("function nwSynapseEmbed()"):admin.index("/* Radial dendrogram:")]
    (destination / "embed.html").write_text("""<!doctype html><html lang="en"><head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Observatory — candidate iframe verification</title>""" + appearance + """
    <link rel="stylesheet" href="theme.css"><style>body{margin:0;background:var(--bg)}main{max-width:1280px;margin:20px auto;padding:0 8px}</style>
    </head><body><main id="fixture-owner"></main><script>""" + embed_source + """
    const owner=document.getElementById('fixture-owner');
    owner.innerHTML=nwSynapseEmbed();nwWireSynapseFrame(owner);
    </script></body></html>""")
    return destination


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(write_fixture(args.destination))
