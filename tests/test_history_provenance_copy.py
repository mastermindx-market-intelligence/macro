"""P12.T45 copy-only provenance guards for the US Regime History page.

Guards ``templates/history.html.j2`` (rendered with the real shared
``templates/_seo_head.html.j2`` include) after the copy-only provenance
repair:

  * the SEO description scalar and the first-chart ``help()`` EN/ZH strings
    carry exactly the authorized reconstruction/recalculation wording,
  * the page never claims recorded contemporaneous regime calls ("on the
    record", "what was said", "how it played out", "actually behaved", ...),
  * everything else — markup, style, chart placeholders, dates, table,
    canonical, links, the two untouched tooltips, the already-repaired
    since-2007 removal — renders byte-for-byte as before.

Rendering is real Jinja2 with ``autoescape=True``: the template's own
``{{ chart_regime | safe }}`` / ``{{ chart_axes | safe }}`` filters are only
meaningful under autoescape, so this mirrors the serving path.  The
unrelated ``_site_nav.html.j2`` / ``_plotly_head.html.j2`` includes are
replaced by controlled stubs; no ``build_site``, classifier, financial
renderer, provider, env override, git or network access is involved.  All
chart, date and table content comes from explicit synthetic sentinels
(``FIXTURE_CONTEXT``) and is asserted back verbatim — a synthetic-fixture
boundary, not evidence about real site data.

Parent RED control (exact-original replay, no repository needed)::

    from test_history_provenance_copy import (
        render_history, assert_history_provenance, normalize_authorized,
        EXPECTED_RENDER_COUNTS,
    )
    old_html = render_history(ORIGINAL_TEMPLATE_SOURCE, SEO_SOURCE)
    try:
        assert_history_provenance(old_html)        # must raise AssertionError
        raise SystemExit("RED control did not fail")
    except AssertionError:
        pass
    normalized, counts = normalize_authorized(old_html)
    assert counts == EXPECTED_RENDER_COUNTS        # seo 3 / help_en 1 / help_zh 1
    assert normalized == render_history(CANDIDATE_SOURCE, SEO_SOURCE)
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from jinja2 import DictLoader, Environment

ROOT = Path(__file__).resolve().parents[1]
HISTORY_TEMPLATE = ROOT / "templates" / "history.html.j2"
SEO_INCLUDE = ROOT / "templates" / "_seo_head.html.j2"

# --- authorized replacement copy (constraint 1, verbatim) ---
NEW_SEO_DESC = (
    "Reconstructed US regime history with S&P 500 overlays and regime "
    "durations. Earlier classifications may change when recalculated."
)
NEW_HELP_EN = (
    "The S&P 500 with reconstructed regime history from the classifier "
    "used for that calculation. Recalculating the history can change "
    "earlier classifications."
)
NEW_HELP_ZH = "标普500走势及当次计算所用分类器重建的周期历史。重新计算可能改变早期分类。"

# --- pre-repair copy (exact-original RED control / normalization) ---
OLD_SEO_DESC = (
    "Every US market regime call on the record — when regimes flipped, "
    "what was said, and how it played out."
)
OLD_HELP_EN = (
    "The S&P 500 with the regime active at each time shaded behind it — "
    "how the classifier actually behaved in real conditions."
)
OLD_HELP_ZH = (
    "标普500 走势，并以底色标出每个时段所处的周期 — "
    "展示分类器在真实环境中的实际表现。"
)

# --- untouched tooltips that must survive verbatim (copy-only boundary) ---
AXES_HELP_EN = (
    "History of the growth (green) and inflation (red) scores. Zero-line "
    "crossings are where regimes change; persistent readings near ±0.5 are "
    "strong regimes; hovering near zero = mixed, choppy environment."
)
AXES_HELP_ZH = (
    "增长（绿）与通胀（红）评分的历史走势。穿越零轴处即周期切换；"
    "持续接近 ±0.5 的读数代表强周期；徘徊在零附近 = 混杂、震荡的环境。"
)
LIFESPAN_HELP_EN = (
    "Every regime period in this classifier: how many there were, how long "
    "they typically lasted, and where they went when they ended. These are "
    "the base rates the front page's odds come from."
)
LIFESPAN_HELP_ZH = (
    "本分类器中的每一个周期时段：共出现多少次、通常持续多久，"
    "以及结束后转向何处。首页的概率即来自这些基准概率。"
)

AUTHORIZED_PAIRS = (
    ("seo_desc", OLD_SEO_DESC, NEW_SEO_DESC, 3),
    ("help_en", OLD_HELP_EN, NEW_HELP_EN, 1),
    ("help_zh", OLD_HELP_ZH, NEW_HELP_ZH, 1),
)
EXPECTED_RENDER_COUNTS = {"seo_desc": 3, "help_en": 1, "help_zh": 1}

FORBIDDEN_CLAIMS = (
    "on the record",
    "what was said",
    "how it played out",
    "actually behaved",
    "in real conditions",
    "every us market regime call",
)

SITE_NAV_STUB = (
    "<!-- controlled unrelated stub: _site_nav.html.j2 -->"
    '<nav data-stub="site-nav">SITE-NAV-STUB</nav>'
)
PLOTLY_HEAD_STUB = (
    "<!-- controlled unrelated stub: _plotly_head.html.j2 -->"
    "<script data-stub=\"plotly-head\">/*PLOTLY-HEAD-STUB*/</script>"
)

# Synthetic sentinels: explicit fixture, never build_site/model/provider data.
FIXTURE_DATE = "2026-10-30"
FIXTURE_GENERATED = "2026-11-03 00:00:00"
FIXTURE_CONTEXT = {
    "latest": {
        "date": FIXTURE_DATE,
        "playbook": {
            "regime": "Goldilocks",
            "regime_age_note": "Fixture regime-age note sentinel",
            "regime_age_note_zh": "周期时长备注哨兵",
            "progress": {
                "age_days": 12,
                "median_days": 90,
                "pct_longer": 41.6,
                "median_remaining_days": 25,
                "n_history": 45,
                "phase": "mid",
            },
        },
    },
    "chart_regime": '<div id="chart-regime">REGIME-CHART-SENTINEL</div>',
    "chart_axes": '<div id="chart-axes">AXES-CHART-SENTINEL</div>',
    "lifespan_rows": [
        {"name": "Goldilocks", "n": 7, "median": 88,
         "next": "Reflation", "next_zh": "再通胀"},
        {"name": "Stagflation", "n": 4, "median": 61,
         "next": "Growth scare", "next_zh": "增长恐慌"},
    ],
    "generated_utc": FIXTURE_GENERATED,
    # the template calls a ``td`` callable for the lifespan name cell
    "td": lambda s: s,
}


def _escaped(text: str) -> str:
    """Rendered form of *text* under the same autoescape rules as render_history."""
    return Environment(autoescape=True).from_string("{{ text }}").render(text=text)


def render_history(template_source: str, seo_source: str) -> str:
    """Render the History page from source strings (controlled replay).

    The supplied SEO include source is used verbatim; the unrelated
    ``_site_nav.html.j2`` / ``_plotly_head.html.j2`` includes resolve to
    controlled stubs.  Autoescape mirrors the ``| safe`` filters in the
    template itself.
    """
    env = Environment(
        loader=DictLoader({
            "history.html.j2": template_source,
            "_seo_head.html.j2": seo_source,
            "_site_nav.html.j2": SITE_NAV_STUB,
            "_plotly_head.html.j2": PLOTLY_HEAD_STUB,
        }),
        autoescape=True,
    )
    return env.get_template("history.html.j2").render(**FIXTURE_CONTEXT)


def normalize_authorized(html: str):
    """Rewrite the three pre-repair copy strings (rendered form) to the
    authorized copy.

    Returns ``(normalized_html, counts)`` where ``counts`` are the numbers of
    pre-repair occurrences found: ``EXPECTED_RENDER_COUNTS`` on the
    exact-original render, all-zero on an already-repaired render.  Normalized
    original vs. repaired render must then be byte-identical — the copy-only
    proof.
    """
    normalized = html
    counts = {}
    for key, old, new, _expected in AUTHORIZED_PAIRS:
        needle, replacement = _escaped(old), _escaped(new)
        counts[key] = normalized.count(needle)
        normalized = normalized.replace(needle, replacement)
    return normalized, counts


class _ProvenanceHTMLParser(HTMLParser):
    """Collect metas, links, <title> and the actual help()/t() EN+ZH slots."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metas = []
        self.links = []
        self.title = []
        self.tips = []      # one {"en": [...], "zh": [...]} per .tip, doc order
        self.en_slots = []  # every .l-en text (help() and t() slots)
        self.zh_slots = []  # every .l-zh text
        self.texts = []
        self._open = []     # ("tip", bucket) | ("lang", key) | ("span", None)
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attr = {}
        for key, value in attrs:
            attr[key] = value or ""
        if tag == "meta":
            self.metas.append(attr)
        elif tag == "link":
            self.links.append(attr)
        elif tag == "title":
            self._in_title = True
        elif tag == "span":
            classes = attr.get("class", "").split()
            if "tip" in classes:
                bucket = {"en": [], "zh": []}
                self.tips.append(bucket)
                self._open.append(("tip", bucket))
            elif "l-en" in classes:
                self._open.append(("lang", "en"))
            elif "l-zh" in classes:
                self._open.append(("lang", "zh"))
            else:
                self._open.append(("span", None))

    def handle_endtag(self, tag):
        if tag == "span" and self._open:
            self._open.pop()
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        self.texts.append(data)
        if self._open and self._open[-1][0] == "lang":
            lang = self._open[-1][1]
            (self.en_slots if lang == "en" else self.zh_slots).append(data)
            for kind, bucket in reversed(self._open):
                if kind == "tip":
                    bucket[lang].append(data)
                    break


def _parse_document(html: str) -> dict:
    parser = _ProvenanceHTMLParser()
    parser.feed(html)
    parser.close()
    meta_name, meta_prop = {}, {}
    for meta in parser.metas:
        if meta.get("name"):
            meta_name[meta["name"]] = meta.get("content", "")
        if meta.get("property"):
            meta_prop[meta["property"]] = meta.get("content", "")
    links = {}
    for link in parser.links:
        links.setdefault(link.get("rel", ""), []).append(link.get("href", ""))
    return {
        "meta_name": meta_name,
        "meta_prop": meta_prop,
        "links": links,
        "title": "".join(parser.title),
        "tips": [{k: "".join(v) for k, v in tip.items()} for tip in parser.tips],
        "en_slots": parser.en_slots,
        "zh_slots": parser.zh_slots,
        "text": " ".join(" ".join(parser.texts).split()),
    }


def assert_history_provenance(html: str) -> None:
    """Semantic + preservation guards for the rendered History page.

    Fails on the exact-original (pre-repair) render — the parent's RED
    control — and passes only on the authorized copy-only repair.
    """
    doc = _parse_document(html)

    # Static SEO stays the existing EN description, consistent across slots.
    seo_slots = (
        doc["meta_name"].get("description", ""),
        doc["meta_prop"].get("og:description", ""),
        doc["meta_name"].get("twitter:description", ""),
    )
    for desc in seo_slots:
        assert desc == NEW_SEO_DESC, f"meta description not authorized copy: {desc!r}"
        assert "reconstructed" in desc.lower(), desc
        assert "may change" in desc.lower() and "recalculat" in desc.lower(), desc
        assert not any("一" <= ch <= "鿿" for ch in desc), (
            f"static SEO description must stay EN, got CJK: {desc!r}"
        )

    # First-chart help(): both language slots render the authorized copy.
    tips = doc["tips"]
    assert len(tips) == 3, f"expected 3 help() tooltips, got {len(tips)}"
    assert tips[0]["en"] == NEW_HELP_EN, repr(tips[0]["en"])
    assert tips[0]["zh"] == NEW_HELP_ZH, repr(tips[0]["zh"])
    assert "reconstructed" in tips[0]["en"].lower(), tips[0]["en"]
    assert "recalculating" in tips[0]["en"].lower(), tips[0]["en"]
    assert "重建" in tips[0]["zh"] and "重新计算" in tips[0]["zh"], tips[0]["zh"]
    assert "可能改变" in tips[0]["zh"], tips[0]["zh"]
    assert tips[0]["zh"] != tips[0]["en"]

    # Untouched tooltips survive verbatim.
    assert tips[1]["en"] == AXES_HELP_EN, repr(tips[1]["en"])
    assert tips[1]["zh"] == AXES_HELP_ZH, repr(tips[1]["zh"])
    assert tips[2]["en"] == LIFESPAN_HELP_EN, repr(tips[2]["en"])
    assert tips[2]["zh"] == LIFESPAN_HELP_ZH, repr(tips[2]["zh"])

    # No claim of recorded contemporaneous regime calls, anywhere rendered.
    for needle in FORBIDDEN_CLAIMS:
        assert needle not in doc["text"].lower(), f"forbidden claim {needle!r}"
        for desc in seo_slots:
            assert needle not in desc.lower(), f"forbidden claim {needle!r} in SEO"

    # EN/ZH parity of the actual t() language slots.
    for en_text, zh_text in (
        ("Three years of regimes over the S&P 500", "标普500 三年周期叠加"),
        ("Regime history & charts", "周期历史与图表"),
        ("data through", "数据截至"),
    ):
        assert en_text in doc["en_slots"], en_text
        assert zh_text in doc["zh_slots"], zh_text

    # Sentinel chart/date/table preservation.
    assert "REGIME-CHART-SENTINEL" in html, "chart_regime sentinel lost"
    assert "AXES-CHART-SENTINEL" in html, "chart_axes sentinel lost"
    assert doc["title"] == f"Regime History — {FIXTURE_DATE}", doc["title"]
    assert "data through" in doc["text"] and FIXTURE_DATE in doc["text"]
    assert "Generated" in doc["text"] and FIXTURE_GENERATED in doc["text"]
    for row_marker in ("<td>Goldilocks</td><td>7</td><td>88</td>",
                       "<td>Stagflation</td><td>4</td><td>61</td>"):
        assert row_marker in html, f"lifespan row lost: {row_marker}"
    assert "Growth scare" in doc["en_slots"] and "增长恐慌" in doc["zh_slots"]
    for legend in ("Goldilocks", "Reflation", "Stagflation", "Growth scare",
                   "理想增长（金发女孩）", "再通胀", "滞胀", "增长恐慌"):
        assert legend in html, f"legend entry lost: {legend}"

    # Head/canonical/link preservation (shared SEO include behaviour intact).
    canonical = "https://www.mastermind-x.com/history.html"
    assert doc["links"].get("canonical") == [canonical], doc["links"].get("canonical")
    assert doc["meta_prop"].get("og:url") == canonical
    assert doc["meta_prop"].get("og:title") == "US Regime History — Mastermind"
    assert doc["meta_prop"].get("og:image") == (
        "https://www.mastermind-x.com/apple-touch-icon.png"
    )
    assert doc["meta_name"].get("twitter:card") == "summary"
    assert doc["links"].get("icon") == ["favicon.svg", "favicon.ico"]
    assert doc["links"].get("apple-touch-icon") == ["apple-touch-icon.png"]
    assert doc["links"].get("stylesheet") == ["theme.css"]
    for script_tag in ('<script src="theme.js"></script>',
                       '<script src="chart_i18n.js"></script>',
                       '<script src="charts.js"></script>'):
        assert script_tag in html, f"script tag lost: {script_tag}"

    # Controlled stubs were actually the includes used.
    assert "SITE-NAV-STUB" in html and "PLOTLY-HEAD-STUB" in html

    # The already-repaired since-2007 statement stays corrected.
    assert "2007" not in html


def _integrated_sources():
    return (
        HISTORY_TEMPLATE.read_text(encoding="utf-8"),
        SEO_INCLUDE.read_text(encoding="utf-8"),
    )


def test_integrated_source_uses_authorized_copy_only():
    template_source, _ = _integrated_sources()
    assert template_source.count(NEW_SEO_DESC) == 1
    assert template_source.count(NEW_HELP_EN) == 1
    assert template_source.count(NEW_HELP_ZH) == 1
    for old in (OLD_SEO_DESC, OLD_HELP_EN, OLD_HELP_ZH):
        assert old not in template_source, old
    # preserved scalars and untouched single-line tooltip copy
    assert '{% set seo_title = "US Regime History — Mastermind" %}' in template_source
    assert '{% set seo_path = "history.html" %}' in template_source
    assert AXES_HELP_EN in template_source
    assert AXES_HELP_ZH in template_source
    assert "2007" not in template_source


def test_render_provenance_and_preservation():
    template_source, seo_source = _integrated_sources()
    assert_history_provenance(render_history(template_source, seo_source))


def test_authorized_render_counts_and_normalization_idempotent():
    template_source, seo_source = _integrated_sources()
    html = render_history(template_source, seo_source)
    assert html.count(_escaped(NEW_SEO_DESC)) == EXPECTED_RENDER_COUNTS["seo_desc"]
    assert html.count(_escaped(NEW_HELP_EN)) == EXPECTED_RENDER_COUNTS["help_en"]
    assert html.count(_escaped(NEW_HELP_ZH)) == EXPECTED_RENDER_COUNTS["help_zh"]
    for _key, old, _new, _expected in AUTHORIZED_PAIRS:
        assert html.count(_escaped(old)) == 0, old
    normalized, counts = normalize_authorized(html)
    assert counts == {"seo_desc": 0, "help_en": 0, "help_zh": 0}
    assert normalized == html
