"""Reproduce the R3 UI on exact accepted bytes; reconstruct display-only physical context.

This review renderer never invokes build_commodities.main, collectors, alerts or
calibration. Only the existing physical-balance display owner reads accepted EIA
series; this observation-date reconstruction is not a historical release vintage. The normal builder owns future publication; this tool pairs its new
consumer UI with the last accepted legacy HTML for a source-review artifact.
"""
from __future__ import annotations

import argparse
import io
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.commodity_decision_workspace import SOURCE_PATHS, build_workspace
from engine.commodity_workspace_adapter import attach_company_continuations
from engine.commodity_supply_context import SERIES, build_physical_context


def git_bytes(base: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{base}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


class WrapSpan(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.start = self.end = None
        self.depth = 0
        self.feed(source)

    def absolute_offset(self):
        line, col = self.getpos()
        return self.offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag != "div" or self.end is not None:
            return
        if self.start is None and "wrap" in dict(attrs).get("class", "").split():
            self.start = self.absolute_offset() + len(self.get_starttag_text())
            self.depth = 1
        elif self.start is not None:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "div" and self.start is not None and self.end is None:
            self.depth -= 1
            if self.depth == 0:
                self.end = self.absolute_offset()


def render_review(base: str) -> tuple[str, dict, str]:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined

    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("Review base must be an exact 40-character Git commit")
    docs, identities = {}, {}
    for key, path in SOURCE_PATHS.items():
        raw = git_bytes(base, path)
        docs[key] = json.loads(raw)
        identities[key] = {"repository": "mastermindx-market-intelligence/macro", "commit": base,
                           "path": path, "file_sha256": sha256(raw).hexdigest()}
    alias_path = "data/reference/vendor_aliases.parquet"
    alias_bytes = git_bytes(base, alias_path)
    identities["company_aliases"] = {"repository": "mastermindx-market-intelligence/macro", "commit": base,
                                     "path": alias_path, "file_sha256": sha256(alias_bytes).hexdigest()}
    import pandas as pd
    import yaml

    config_raw = git_bytes(base, "config.yml")
    supply_cfg = yaml.safe_load(config_raw)["eia"]["supply"]
    physical_series, physical_identities = {}, {}
    for name in SERIES:
        path = f"data/eia/{name}.parquet"
        try:
            raw = git_bytes(base, path)
            frame = pd.read_parquet(io.BytesIO(raw))
            physical_series[name] = None if frame.empty else frame.iloc[:, 0]
            physical_identities[name] = {
                "repository": "mastermindx-market-intelligence/macro", "commit": base,
                "path": path, "file_sha256": sha256(raw).hexdigest(),
            }
        except (subprocess.CalledProcessError, ValueError, OSError):
            physical_series[name] = None
    physical = build_physical_context(
        physical_series, as_of=docs["commodities"]["asof"],
        years=supply_cfg.get("seasonal_years", 5), dos_weeks=supply_cfg.get("dos_window_weeks", 4),
        source_identities=physical_identities)
    identities["physical"] = {
        "repository": "mastermindx-market-intelligence/macro", "commit": base,
        "files": physical_identities,
        "configuration": {"path": "config.yml", "file_sha256": sha256(config_raw).hexdigest()},
        "method_revision": physical["method_revision"],
        "reconstruction": "display_only_from_accepted_series", "release_vintage_verified": False,
    }
    workspace = build_workspace(docs["commodities"], transmission=docs["rates"], fx=docs["fx"],
                                chain_state=docs["chains"], commodity_latest=docs["ratios"],
                                source_identities=identities, physical_context=physical)
    # Materialize only this exact immutable input, independently of sparse checkout.
    with TemporaryDirectory(prefix="commodity-review-aliases-") as folder:
        alias_root = Path(folder)
        alias_file = alias_root / alias_path
        alias_file.parent.mkdir(parents=True)
        alias_file.write_bytes(alias_bytes)
        workspace = attach_company_continuations(workspace, docs["chains"], alias_root)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True, undefined=StrictUndefined)
    macro = '{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}'
    component = env.from_string(macro + '{% include "_commodity_decision_workspace.html.j2" %}').render(commodity_workspace=workspace)
    component = re.sub(r"(?m)^[ \t]+$", "", component)
    opening = env.from_string(macro + '''<details id="commodity-advanced" class="cw-advanced">
<summary>{{ t('Advanced analytics · published evidence and model readings','高级分析 · 已发布证据与模型判断') }}</summary>
<div class="cw-return-bar"><span>{{ t('Full published analytics','完整已发布分析') }}</span><button type="button" id="cw-return" class="gbtn">← {{ t('Return to my commodity research','返回当前品种研究') }}</button></div>
<p class="cw-legacy-note">{{ t('These are the existing publishers’ detailed readings. Their dates, horizons and model judgements remain distinct from the research interpretation above.','以下为现有发布来源的详细判断；其日期、时间窗口及模型结论，与上方研究解释分别呈现。') }}</p>''').render()
    html = git_bytes(base, "site/commodities.html").decode("utf-8")
    original_sha = sha256(html.encode()).hexdigest()
    # Frozen CSS assets were pruned before this new consumer existed. Restore the
    # exact canonical theme before those assets, matching the normal template order.
    theme_path = "templates/theme.css"
    theme_bytes = git_bytes(base, theme_path)
    theme_css = theme_bytes.decode("utf-8")
    if "</style" in theme_css.lower():
        raise ValueError("Canonical theme cannot be embedded safely")
    first_style = re.search(r'<style\b|<link\b[^>]*rel=[\"\']stylesheet[\"\']', html, re.I)
    if first_style is None:
        raise ValueError("Accepted page has no stylesheet anchor")
    html = html[:first_style.start()] + "<style data-cw-canonical-theme>\n" + theme_css + "\n</style>\n" + html[first_style.start():]
    identities["canonical_theme"] = {"repository": "mastermindx-market-intelligence/macro", "commit": base,
                                     "path": theme_path, "file_sha256": sha256(theme_bytes).hexdigest()}
    span = WrapSpan(html)
    if span.start is None or span.end is None:
        raise ValueError("Accepted page has no unique main wrap")
    html = html[:span.start] + component + opening + html[span.start:span.end] + "</details>" + html[span.end:]
    html = html.replace('<body class="page-commod">', '<body class="page-commod cw-enabled">', 1)
    legacy_h1 = re.search(r"<h1>.*?</h1>", html[html.index(opening) + len(opening):], re.S)
    if legacy_h1 is None:
        raise ValueError("Accepted legacy heading not found")
    html = html.replace(legacy_h1.group(), '<h2><span class="l-en">Detailed commodity analytics</span><span class="l-zh">商品详细分析</span></h2>', 1)
    html = html.replace('<div class="section-title"><span class="l-en">Upcoming events', '<div class="section-title" id="commodity-catalysts"><span class="l-en">Upcoming events', 1)
    # Drop whitespace-only template lines without changing meaningful text nodes.
    html = re.sub(r"(?m)^[ \t]+$", "", html)
    css = (ROOT / "templates/commodity-workspace.css").read_text()
    js = (ROOT / "templates/commodity-workspace.js").read_text()
    html = html.replace("</head>", f"<style>\n{css}\n</style></head>", 1)
    html = html.replace("</body>", f"<script>\n{js}\n</script></body>", 1)
    report = {"schema": "mmx.commodities.review_receipt.v1", "accepted_base": base,
              "research_as_of": workspace["as_of"], "workspace_fingerprint": workspace["fingerprint"],
              "accepted_page_sha256": original_sha, "review_page_sha256": sha256(html.encode()).hexdigest(),
              "assets": len(workspace["assets"]), "chains": len(workspace["chains"]),
              "source_files": identities, "economic_recomputation": True,
              "recomputation_scope": "display_only_petroleum_balance_from_accepted_EIA_series",
              "collectors_run": False, "scoring_run": False, "forecasts_run": False,
              "release_vintage_verified": False, "physical_classification": workspace["physical"]["classification"],
              "production_acceptance": False}
    return html, report, component


class WorkspaceSpan(WrapSpan):
    """Locate the existing workspace without consuming its legacy sibling."""

    def handle_starttag(self, tag, attrs):
        if tag != "section" or self.end is not None:
            return
        if self.start is None and dict(attrs).get("id") == "commodity-workspace":
            self.start = self.absolute_offset()
            self.depth = 1
        elif self.start is not None:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "section" and self.start is not None and self.end is None:
            self.depth -= 1
            if self.depth == 0:
                self.end = self.absolute_offset() + len("</section>")


def render_published_workspace(base: str) -> tuple[str, dict, str]:
    """Recompose only presentation from a published workspace; never recompute data."""
    from jinja2 import Environment, FileSystemLoader, StrictUndefined

    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("Review base must be an exact 40-character Git commit")
    original = git_bytes(base, "site/commodities.html").decode("utf-8")
    data_pattern = r'<script\b[^>]*\bid="cw-data"[^>]*>(.*?)</script>'
    payloads = re.findall(data_pattern, original, re.S)
    if len(payloads) != 1 or original.count('id="commodity-workspace"') != 1:
        raise ValueError("Accepted page must contain exactly one published workspace")
    workspace = json.loads(payloads[0])
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True, undefined=StrictUndefined)
    macro = '{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}'
    component = env.from_string(macro + '{% include "_commodity_decision_workspace.html.j2" %}').render(commodity_workspace=workspace)
    generated_payloads = re.findall(data_pattern, component, re.S)
    if len(generated_payloads) != 1 or generated_payloads[0] != payloads[0]:
        raise ValueError("Presentation review changed the published payload bytes")
    span = WorkspaceSpan(original)
    if span.start is None or span.end is None:
        raise ValueError("Published workspace section could not be bounded")
    html = original[:span.start] + component + original[span.end:]

    # Replace the exact standalone consumer script, preserving all other scripts.
    previous_js = git_bytes(base, "templates/commodity-workspace.js").decode("utf-8").strip()
    js = (ROOT / "templates/commodity-workspace.js").read_text()
    scripts = [m for m in re.finditer(r"<script\b[^>]*>(.*?)</script>", html, re.S)
               if m.group(1).strip() == previous_js]
    if len(scripts) != 1 or "</script" in js.lower():
        raise ValueError("Published workspace script binding is not unique or safe")
    match = scripts[0]
    html = html[:match.start()] + "<script>\n" + js + "\n</script>" + html[match.end():]

    # Existing asset freezing owns the rest of the cohort. Locate this consumer's
    # exact frozen stylesheet, then leave its replacement inline for the same owner.
    previous_css = git_bytes(base, "templates/commodity-workspace.css").decode("utf-8").strip()
    css = (ROOT / "templates/commodity-workspace.css").read_text()
    candidates = []
    for match in re.finditer(r'<link\b[^>]*\bhref="([^"]+)"[^>]*>', html):
        target = urlsplit(match.group(1))
        if target.scheme or target.netloc or not target.path.endswith(".css"):
            continue
        if target.path.startswith("/") or ".." in Path(target.path).parts:
            continue
        body = git_bytes(base, "site/" + target.path).decode("utf-8")
        if body.strip() == previous_css:
            candidates.append(match)
    if len(candidates) != 1 or "</style" in css.lower():
        raise ValueError("Published workspace stylesheet binding is not unique or safe")
    match = candidates[0]
    html = html[:match.start()] + "<style>\n" + css + "\n</style>" + html[match.end():]
    if html.count('id="commodity-workspace"') != 1 or html.count('id="cw-data"') != 1:
        raise ValueError("Review created duplicate workspace mounts")
    report = {
        "schema": "mmx.commodities.review_receipt.v1", "accepted_base": base,
        "mode": "published_payload_presentation_only", "research_as_of": workspace["as_of"],
        "workspace_fingerprint": workspace["fingerprint"],
        "accepted_page_sha256": sha256(original.encode()).hexdigest(),
        "review_page_sha256": sha256(html.encode()).hexdigest(),
        "payload_sha256": sha256(payloads[0].encode()).hexdigest(),
        "payload_bytes_unchanged": True, "legacy_content_preserved": True,
        "assets": len(workspace["assets"]), "chains": len(workspace["chains"]),
        "economic_recomputation": False, "collectors_run": False,
        "scoring_run": False, "forecasts_run": False, "production_acceptance": False,
    }
    return html, report, component


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--component", type=Path)
    parser.add_argument("--reuse-published-workspace", action="store_true",
                        help="Recompose only UI from the exact published payload; no economic recomputation")
    args = parser.parse_args()
    renderer = render_published_workspace if args.reuse_published_workspace else render_review
    html, report, component = renderer(args.base)
    for path, content in [(args.output, html), (args.receipt, json.dumps(report, indent=2) + "\n"), (args.component, component)]:
        if path:
            path.resolve().relative_to(ROOT)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "source_files"}, indent=2))


if __name__ == "__main__":
    main()

