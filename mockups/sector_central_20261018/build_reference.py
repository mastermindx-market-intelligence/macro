#!/usr/bin/env python3
"""Build the review-only standalone reference from canonical theme and fixture."""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
html = (HERE / "index.html").read_text()
css = (HERE / "reference.css").read_text()
js = (HERE / "reference.js").read_text()
theme = (ROOT / "templates/theme.css").read_text()
fixture = json.loads((ROOT / "tests/fixtures/leadership_rotation/measured_read_v1.json").read_text())
archive = json.loads((HERE / "archive_sources.json").read_text())
assert fixture["schema"] == "leadership_rotation_context.measured_group_read/v1"
theme = re.sub(r"/\*[\s\S]*?\*/", "", theme)
rules = []
for match in re.finditer(r"(?:^|\n)\s*(:root|html(?:\[[^\]]+\])*)\s*\{([^{}]*)\}", theme):
    declarations = re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", match[2])
    rules.append((match[1], declarations))
needed = set(re.findall(r"var\((--[\w-]+)", css))
changed = True
while changed:
    previous = set(needed)
    for _, declarations in rules:
        for key, value in declarations:
            if key in needed:
                needed.update(re.findall(r"var\((--[\w-]+)", value))
    changed = previous != needed
tokens = []
for selector, declarations in rules:
    keep = [(key, value.strip()) for key, value in declarations if key in needed]
    if keep:
        tokens.append(selector + "{" + "".join(key + ":" + value + ";" for key, value in keep) + "}")
fetch_block = """  const response=await fetch('../../tests/fixtures/leadership_rotation/measured_read_v1.json');
  if(!response.ok)throw new Error('Fixture unavailable');
  const raw=await response.json();"""
assert js.count(fetch_block) == 1, "Fixture loading changed; update this review exporter explicitly."
js = js.replace(fetch_block, "  const raw=JSON.parse(document.getElementById('reference-fixture').textContent);")
archive_fetch = """  const archiveResponse=await fetch('archive_sources.json');
  if(!archiveResponse.ok)throw new Error('Archive unavailable');
  archive=await archiveResponse.json();"""
assert js.count(archive_fetch) == 1, "Archive loading changed; update this review exporter explicitly."
js = js.replace(archive_fetch, "  archive=JSON.parse(document.getElementById('reference-archive').textContent);")
styles = '<link rel="stylesheet" href="../../templates/theme.css"><link rel="stylesheet" href="reference.css">'
assert html.count(styles) == 1
html = html.replace(styles, "<style>\n/* Canonical root tokens; built from templates/theme.css. */\n" + "\n".join(tokens) + "\n" + css + "\n</style>")
fixture_text = json.dumps(fixture, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
archive_text = json.dumps(archive, ensure_ascii=False, indent=1).replace("<", "\\u003c")
assert html.count('<script src="reference.js"></script>') == 1
html = html.replace('<script src="reference.js"></script>', '<script id="reference-fixture" type="application/json">' + fixture_text + '</script>\n<script id="reference-archive" type="application/json">' + archive_text + '</script>\n<script>' + js + '</script>')
assert not re.search(r"<(?:script|link)\b[^>]*(?:src|href)=", html), "Standalone export retained an external asset."
destination = HERE / "preview.html"
destination.write_text(html)
print(json.dumps({"artifact": str(destination.relative_to(ROOT)), "bytes": destination.stat().st_size, "fixture_schema": fixture["schema"], "fixture_groups": len(fixture["groups"]), "live": False, "applied_to_paper": False}))
