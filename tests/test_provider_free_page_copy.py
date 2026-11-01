"""Provider-neutral copy on the swept product pages.

Product rule: rendered copy never names a market-data vendor. Each surface below is
either rendered from a fixture or read with its Jinja comments stripped (a `{# #}`
comment never reaches a reader) and must carry zero vendor tokens. The only
allowances are code literals that never render as text: a data-id comparator in the
Mag 7 panel and the committee page's runtime label scrub, both removed by exact match
before the scan so any new occurrence still fails.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TEMPLATES = ROOT / "templates"

# The brief's hit regex: whole-word vendor names, not inside a tag name, not a call.
VENDOR = re.compile(
    r"(?i)(?<![<A-Za-z0-9])(?:yfinance|yahoo|tushare|polygon|massive)(?![A-Za-z0-9(])|雅虎"
)
# Surface-specific feed names, matched outside identifiers (`s.stocktwits` and
# `'stocktwits_bull'` are payload keys, not copy).
EXTRA = {
    "alt_data": re.compile(r"(?i)(?<![A-Za-z0-9_.'])(?:quiver|stocktwits|hugging ?face)(?![A-Za-z0-9_(])"),
    "flow_velocity": re.compile(r"(?i)(?<![A-Za-z0-9_.'])(?:tushare|eastmoney)(?![A-Za-z0-9_(])|东方财富"),
}
JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.S)

# Exact code-only literals removed before the scan.
CODE_ONLY = {
    "_mag7_panel": ["'polygon_mktcap'"],
    "committee": [r"/\b(?:yfinance|yahoo|tushare|polygon|massive)\b/gi"],
}

# Literal repo paths so the CI scope planner owns each template as a trigger.
SWEPT = [
    "templates/report_price_of_duration.html.j2",
    "templates/report_haven_audition.html.j2",
    "templates/report_warsh_fomc.html.j2",
    "templates/alt_data.html.j2",
    "templates/flow_velocity.html.j2",
    "templates/_mag7_panel.html.j2",
    "templates/committee.html.j2",
    "templates/market_heatmap.html.j2",
    "templates/_desk_grader_panel.html.j2",
]


def _hits(pattern: re.Pattern, text: str) -> list[str]:
    return [text[max(0, m.start() - 50):m.end() + 30].replace("\n", " ") for m in pattern.finditer(text)]


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=False)
    env.globals["t"] = lambda en, zh: f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'
    return env


@pytest.mark.parametrize("rel", SWEPT)
def test_swept_template_copy_names_no_vendor(rel: str) -> None:
    name = rel.removeprefix("templates/").removesuffix(".html.j2")
    src = JINJA_COMMENT.sub("", (ROOT / rel).read_text(encoding="utf-8"))
    for literal in CODE_ONLY.get(name, []):
        assert literal in src, f"allowance {literal!r} no longer in {name}; drop it from CODE_ONLY"
        src = src.replace(literal, "")
    hits = _hits(VENDOR, src)
    if name in EXTRA:
        hits += _hits(EXTRA[name], src)
    assert hits == [], f"{name} names a data vendor: {hits}"


def test_mag7_panel_render_shows_neutral_weight_label() -> None:
    d = {
        "as_of": "2026-07-10", "weights_basis": "polygon_mktcap", "trend_state": "running_narrow",
        "structure": {"dd_from_252d_high": -0.08, "chip": "recovering"},
        "run": {"start": "2026-06-26", "sessions": 11, "cw_ret": 0.09, "spy_ret": 0.02},
        "k7": {"trend": 4, "rs": 5},
        "cw": {"r2": 0.01, "r5": 0.03, "r10": 0.06, "r20": 0.04, "rel20": 0.02},
        "ew": {"r10": 0.04, "r20": 0.02},
        "members": [{"sym": "AAPL", "w": 0.18, "r5": 0.08, "r10": 0.06, "r20": 0.09, "rs20": 0.06,
                     "above50": True, "above200": True, "contrib10": 0.3, "mtf": "RUNNING"}],
    }
    html = _env().from_string(
        "{% from '_mag7_panel.html.j2' import mag7_panel %}{{ mag7_panel(d) }}"
    ).render(d=d)
    assert "Market-cap weights" in html
    assert "市值加权" in html
    assert _hits(VENDOR, html) == []


def test_desk_grader_panel_scrubs_legacy_ledger_note(tmp_path: Path) -> None:
    from engine import desk_grader

    # The literal seed row an existing append-only ledger still carries.
    legacy = {
        "date": "2026-07-04", "desk": "all", "author": "wave2",
        "note": "PRICE LESSON: grade off data/yahoo/<T>.parquet adjusted closes ONLY. The S&P-1500 "
                "breadth close cache (data/breadth/_closes_cache.parquet) is SPLIT-CORRUPTED — using "
                "it silently poisons every RS / forward-return number. A name missing from yahoo is a "
                "coverage skip here, never a wrong return.",
    }
    path = desk_grader._notes_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    notes = desk_grader._load_notes(tmp_path, "insider")
    assert len(notes) == 1
    assert "the daily price store's adjusted closes ONLY" in notes[0]["note"]
    assert "SPLIT-CORRUPTED" in notes[0]["note"]
    assert path.read_text(encoding="utf-8").count("data/yahoo/") == 1, "ledger must stay append-only"

    html = _env().from_string(
        "{% import '_desk_grader_panel.html.j2' as dg %}{{ dg.panel(G) }}"
    ).render(G={"n_snapshots_live": 1, "notes": notes})
    assert "Lessons logged" in html
    assert "SPLIT-CORRUPTED" in html
    assert _hits(VENDOR, html) == []


def test_desk_grader_seed_notes_name_no_vendor() -> None:
    from engine import desk_grader

    assert [n["date"] for n in desk_grader._SEED_NOTES if _hits(VENDOR, n["note"])] == []


def test_flow_source_tips_name_no_vendor() -> None:
    from engine.flow_observatory.contract import SOURCE_META

    text = json.dumps(SOURCE_META, ensure_ascii=False)
    assert _hits(VENDOR, text) == []
    assert _hits(EXTRA["flow_velocity"], text) == []


def test_altdata_feed_labels_name_no_vendor() -> None:
    from engine import altdata

    text = json.dumps(altdata.DATASETS, ensure_ascii=False)
    assert _hits(VENDOR, text) == []
    assert _hits(EXTRA["alt_data"], text) == []
    src = (ROOT / "engine" / "altdata.py").read_text(encoding="utf-8")
    assert '"source": "Alternative-data disclosures"' in src


def test_heatmap_feed_label_names_no_vendor() -> None:
    cfg = yaml.safe_load((ROOT / "config.yml").read_text(encoding="utf-8"))
    labels: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if str(k).startswith("feed_label") and isinstance(v, str):
                    labels.append(v)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(cfg)
    assert labels, "config.yml no longer carries a heatmap feed label"
    assert [s for s in labels if _hits(VENDOR, s)] == []


def test_committee_labels_neutralize_wiring_ids() -> None:
    src = (ROOT / "templates/committee.html.j2").read_text(encoding="utf-8")
    fn = re.search(r"function _neutralSource\(s\) \{(.*?)\n  \}", src, re.S)
    assert fn, "committee label scrub missing"
    scrubs = [(re.compile(p, re.I), r) for p, r in re.findall(r"\.replace\(/(.+?)/gi, '([a-z]+)'\)", fn.group(1))]
    assert len(scrubs) == 2

    def neutral(s: str) -> str:
        for pattern, repl in scrubs:
            s = pattern.sub(repl, s)
        return s

    for wiring in ("polygon intraday", "yahoo daily", "tushare moneyflow", "massive options", "quiver congress"):
        assert _hits(VENDOR, neutral(wiring)) == []
        assert "quiver" not in neutral(wiring).lower()
    # Every fallback label path runs through the scrub.
    assert "s = _neutralSource(s).replace(" in src
    seg = re.search(r"function _artifactSeg\(id\) \{(.*?)\n  \}", src, re.S).group(1)
    assert seg.count("return _neutralSource(") == 2
    # The zh word map never maps a wiring token to a vendor display name.
    zh_map = re.search(r"var ARTIFACT_WORD_ZH = \{(.*?)\n  \};", src, re.S).group(1)
    assert _hits(VENDOR, zh_map) == []
    assert "'quiver'" not in zh_map
