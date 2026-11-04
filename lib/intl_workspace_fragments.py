"""Partition already-rendered International research into bounded static assets.

This is a presentation step, after all source/Inspector/Library binding passes.
It neither qualifies nor calculates data. Dossier assets contain one market's
existing markup across contexts; Scanner and Coverage use one asset per context.
The normal build owner publishes these stable slots before publishing the page.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile

SCHEMA = "intl-workspace-fragments.v1"
DEFERRED_VIEWS = frozenset({"dossier", "scanner", "coverage"})
_VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
_GENERATION = re.compile(r"im-workspace-generation:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,150}\Z")
_MARKET = re.compile(r"[A-Z]{2}\Z")
_COPY = {
    "dossier": ("Country dossiers", "国家档案"),
    "scanner": ("Market scanner", "市场扫描"),
    "coverage": ("Evidence coverage", "依据覆盖"),
}


@dataclass
class _Span:
    tag: str
    attrs: dict
    start: int
    open_end: int
    close_start: int = 0
    end: int = 0


@dataclass
class _Panel:
    root: _Span
    scopes: list[_Span] = field(default_factory=list)
    articles: list[_Span] = field(default_factory=list)
    markets: set[str] = field(default_factory=set)
    defaults: set[str] = field(default_factory=set)


class _Index(HTMLParser):
    """Keep offsets only for selected boundaries, not a second full-page DOM."""

    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0]
        self.lines.extend(m.end() for m in re.finditer("\n", source))
        self.stack: list[_Span] = []
        self.panels: list[_Panel] = []
        self.active: _Panel | None = None
        self.workspaces = 0
        self.workspace_depth: int | None = None

    def _offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        start = self._offset()
        span = _Span(tag, attrs, start, start + len(self.get_starttag_text()))
        if "data-im-workspace" in attrs:
            self.workspaces += 1
            if self.workspace_depth is not None or attrs.get("data-im-binding-version") != "2":
                raise ValueError("Deferred research requires one publication-bound workspace")
            self.workspace_depth = len(self.stack)
        if "data-im-panel" in attrs and attrs.get("data-view") in DEFERRED_VIEWS:
            if self.active or self.workspace_depth is None or len(attrs) != len(attributes):
                raise ValueError("Ambiguous deferred research panel")
            self.active = _Panel(span)
            self.panels.append(self.active)
        if self.active:
            if "data-gs-market-scope" in attrs:
                self.active.scopes.append(span)
            market = attrs.get("data-gs-market")
            if market is not None:
                if not _MARKET.fullmatch(market):
                    raise ValueError("Invalid emitted research market")
                self.active.markets.add(market)
                if "data-gs-market-default" in attrs:
                    self.active.defaults.add(market)
                if self.active.root.attrs["data-view"] == "dossier":
                    if tag != "article" or not self.stack or "data-gs-market-scope" not in self.stack[-1].attrs:
                        raise ValueError("Dossier market must be a direct scope article")
                    self.active.articles.append(span)
        if tag not in _VOID:
            self.stack.append(span)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            span = self.stack.pop()
            span.close_start = span.open_end
            span.end = span.open_end

    def handle_endtag(self, tag):
        matching = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i].tag == tag), None)
        if matching is None:
            if self.active:
                raise ValueError("Unbalanced deferred research markup")
            return
        if self.active and matching != len(self.stack) - 1:
            raise ValueError("Implicitly closed deferred research markup")
        span = self.stack[matching]
        span.close_start = self._offset()
        span.end = self.source.index(">", span.close_start) + 1
        del self.stack[matching:]
        if self.active and span is self.active.root:
            self.active = None
        if self.workspace_depth == matching:
            self.workspace_depth = None


@dataclass(frozen=True)
class PartitionedWorkspace:
    html: str
    assets: dict[str, bytes]
    panel_count: int


def _json(value, *, inline=False):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    # Only the inline manifest needs HTML script-delimiter escaping.
    return encoded.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029") if inline else encoded


def partition_workspace(source: str) -> PartitionedWorkspace:
    """Return an equivalent page and deterministic fragment slots; perform no I/O."""
    index = _Index(source)
    index.feed(source)
    index.close()
    if not index.panels:
        return PartitionedWorkspace(source, {}, 0)
    if index.active or index.workspaces != 1:
        raise ValueError("Incomplete or ambiguous deferred workspace")
    generations = {p.root.attrs.get("data-im-generation") for p in index.panels}
    if len(generations) != 1 or not _GENERATION.fullmatch(next(iter(generations)) or ""):
        raise ValueError("Mixed research publication generations")
    generation = next(iter(generations))
    ids: set[str] = set()
    contexts: set[tuple] = set()
    bundles: dict[str, dict] = {}
    descriptors = []
    for panel in index.panels:
        root, attrs = panel.root, panel.root.attrs
        panel_id, view = attrs.get("id", ""), attrs["data-view"]
        horizon, basis = attrs.get("data-horizon"), attrs.get("data-basis")
        context = (view, horizon, basis)
        if (not _ID.fullmatch(panel_id) or panel_id in ids or context in contexts
                or horizon not in {"1m", "3m", "6m", "12m", "ytd"}
                or basis not in {"local", "usd_unhedged"}
                or attrs.get("data-return-basis") != "price"
                or "data-source" not in attrs
                or not _ID.fullmatch(attrs.get("aria-labelledby", ""))
                or not root.end or len(panel.defaults) > 1):
            raise ValueError("Invalid deferred research context")
        ids.add(panel_id)
        contexts.add(context)
        identity = {"panel_id": panel_id, "generation": generation, "view": view,
                    "horizon": horizon, "basis": basis, "return_basis": "price",
                    "source": attrs["data-source"]}
        descriptor = {"schema": SCHEMA, **identity, "markets": sorted(panel.markets),
                      "default_market": next(iter(panel.defaults), None), "variants": {}}
        if view == "dossier":
            if (len(panel.scopes) != 1 or not panel.articles
                    or len(panel.articles) != len(panel.markets) or len(panel.defaults) != 1):
                raise ValueError("Dossier partition requires unique market articles and a default")
            scope = panel.scopes[0]
            if (not scope.end or source[scope.open_end:panel.articles[0].start].strip()
                    or source[panel.articles[-1].end:scope.close_start].strip()
                    or any(source[a.end:b.start].strip() for a, b in zip(panel.articles, panel.articles[1:]))):
                raise ValueError("Dossier scope contains unowned content")
            variants = [(a.attrs["data-gs-market"],
                         source[root.start:scope.open_end] + source[a.start:a.end] + source[scope.close_start:root.end])
                        for a in panel.articles]
        else:
            variants = [("default", source[root.start:root.end])]
        for market, markup in variants:
            slot = f"dossier-{market}" if view == "dossier" else f"{view}-{horizon}-{basis}"
            path = f"assets/intl-workspace/{slot}.json"
            bundle = bundles.setdefault(path, {"schema": SCHEMA, "generation": generation, "fragments": {}})
            if panel_id in bundle["fragments"]:
                raise ValueError("Duplicate research fragment identity")
            bundle["fragments"][panel_id] = {**identity, "market": market,
                "markets": [market] if view == "dossier" else sorted(panel.markets), "html": markup}
            descriptor["variants"][market] = path
        descriptors.append((panel, descriptor))
    assets = {path: (_json(bundle) + "\n").encode("utf-8") for path, bundle in sorted(bundles.items())}
    asset_refs = {path: {"url": path, "sha256": sha256(raw).hexdigest(), "bytes": len(raw)} for path, raw in assets.items()}
    replacements = []
    for panel, descriptor in descriptors:
        descriptor["variants"] = {key: asset_refs[path] for key, path in descriptor["variants"].items()}
        root = panel.root
        opening = source[root.start:root.open_end][:-1] + ' data-im-deferred="true" aria-busy="false"'
        if "hidden" not in root.attrs:
            opening += " hidden"
        opening += ">"
        title_en, title_zh = _COPY[descriptor["view"]]
        title_id = escape(root.attrs["aria-labelledby"], quote=True)
        fallback = (
            '<div class="intl-workspace__deferred" data-im-deferred-fallback>'
            '<span class="intl-workspace__deferred-kicker"><span class="l-en">RESEARCH WORKSPACE</span>'
            '<span class="l-zh" lang="zh">研究工作台</span></span>'
            f'<h2 id="{title_id}" tabindex="-1"><span class="l-en">{title_en}</span>'
            f'<span class="l-zh" lang="zh">{title_zh}</span></h2>'
            '<p data-im-deferred-status role="status"><span class="l-en">Open this view to load its research.</span>'
            '<span class="l-zh" lang="zh">打开此视图以加载研究内容。</span></p>'
            '<button type="button" data-im-deferred-retry hidden><span class="l-en">Try again</span>'
            '<span class="l-zh" lang="zh">重试</span></button>'
            '<a href="" data-im-deferred-reload hidden><span class="l-en">Reload this snapshot</span>'
            '<span class="l-zh" lang="zh">重新加载快照</span></a>'
            '<noscript><p><span class="l-en">Enable JavaScript to open this research view. Country summaries and evidence remain available above.</span>'
            '<span class="l-zh" lang="zh">启用 JavaScript 以打开此研究视图。上方仍可查看各国摘要与依据。</span></p></noscript></div>'
        )
        replacement = (opening + '<script type="application/json" data-im-deferred-manifest>'
                       + _json(descriptor, inline=True) + '</script>' + fallback + source[root.close_start:root.end])
        replacements.append((root.start, root.end, replacement))
    result = source
    for start, end, replacement in reversed(replacements):
        result = result[:start] + replacement + result[end:]
    return PartitionedWorkspace(result, assets, len(index.panels))


def publish_workspace_fragments(source: str, site: Path) -> str:
    """Publish through build_intl; stable slots cannot accumulate by generation."""
    result = partition_workspace(source)
    for relative, content in result.assets.items():
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".intl-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return result.html
