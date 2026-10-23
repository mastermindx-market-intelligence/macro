"""Build explicit R4 candidate routes from existing published crypto contracts.

This entry point never overwrites crypto.html/vector.html and never collects data.
The existing builders remain the source owners. Candidate acceptance precedes cutover.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.crypto_intelligence_view import build_view, finite
from lib.illus import illus


INPUTS = ("crypto_cockpit.json", "crypto_class_state.json", "crypto_asset_states.json", "vector_risk_strategy.json")


def read_contract(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def money(value) -> str:
    number = finite(value)
    if number is None:
        return "—"
    return "$" + format(number, ",.2f" if abs(number) < 1000 else ",.0f")


def pct(value) -> str:
    number = finite(value)
    if number is None:
        return "—"
    return ("+" if number > 0 else "") + format(number, ".1f") + "%"


def render_view(view: dict, site: Path) -> list[Path]:
    site.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    env.globals.update(td=lambda value: value, tr=lambda value: value, t_pctile=lambda value: str(value))
    source_names = ("crypto_intelligence_r4.html.j2", "crypto_intelligence_r4.css", "crypto_intelligence_r4.js")
    version = hashlib.sha256(b"".join((ROOT / "templates" / name).read_bytes() for name in source_names)).hexdigest()[:12]
    history = view["history"]
    charts = {}
    if history["state"] == "ready":
        for days in (30, 90):
            series = {"dates": history["dates"][-days:], "vals": history["vals"][-days:]}
            charts[str(days)] = illus(
                series, kind="line", accent="var(--info)", height=250,
                value_fmt="$" + "{:,.0f}",
                aria_en=f"Bitcoin daily closing prices in US dollars, latest available {days}-day window.",
                aria_zh=f"比特币美元日收盘价，最近可用的{days}天窗口。",
            )
    outputs = []
    for filename, default_view in (("crypto-r4.html", "overview"), ("vector-r4.html", "bitcoin")):
        rendered = env.get_template("crypto_intelligence_r4.html.j2").render(
            view=view, charts=charts, money=money, pct=pct, default_view=default_view, version=version,
        )
        # Jinja-only lines can otherwise emit indentation as trailing whitespace.
        # Do not collapse content or block boundaries: preserve each original line.
        rendered = "\n".join(line.rstrip(" \t") for line in rendered.split("\n"))
        destination = site / filename
        destination.write_text(rendered, encoding="utf-8")
        outputs.append(destination)
    for filename in ("crypto_intelligence_r4.css", "crypto_intelligence_r4.js"):
        shutil.copyfile(ROOT / "templates" / filename, site / filename)
    (site / "crypto_intelligence_r4.json").write_text(
        json.dumps(view, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8",
    )
    scorecard = read_contract(ROOT / "research" / "CRYPTO_INTELLIGENCE_R4_SCORECARD.json")
    (site / "crypto-r4-scorecard.html").write_text(
        env.get_template("crypto_intelligence_r4_scorecard.html.j2").render(scorecard=scorecard),
        encoding="utf-8",
    )
    return outputs


def build(site: Path, source: Path | None = None) -> dict:
    source = source or site
    contracts = [read_contract(source / name) for name in INPUTS]
    view = build_view(*contracts)
    history = view["history"]
    history["segment_observations"] = len(history["dates"])
    history["dates"], history["vals"] = history["dates"][-180:], history["vals"][-180:]
    outputs = render_view(view, site)
    return {
        "outputs": [str(path) for path in outputs],
        "as_of": view["as_of"], "market_as_of": view["market_as_of"],
        "chart": view["history"]["state"], "supported_assets": len(view["assets"]),
        "source": str(source), "display_only": True,
        "production_routes_replaced": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "site")
    parser.add_argument("--source-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.site_dir, args.source_dir), ensure_ascii=False))
