"""scripts.build_research_screener — research-priority-only screener page.

Reads site/stockdata/*.json (security_state.v1 + valuation_scenario.v1).
Writes site/research_screener.json and site/research_screener.html.

Zero network. Fail-soft on a missing stockdata tree: an empty, honest list.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from engine.research_screener import compile_research_screener  # noqa: E402

JSON_NAME = "research_screener.json"
HTML_NAME = "research_screener.html"


def _load_stockdata(root: Path) -> tuple[list[dict], list[dict], dict[str, str], str | None]:
    stockdir = root / "site" / "stockdata"
    states: list[dict] = []
    postures: list[dict] = []
    names: dict[str, str] = {}
    as_of: str | None = None
    if not stockdir.is_dir():
        return states, postures, names, as_of
    for path in sorted(stockdir.glob("*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(rec, dict):
            continue
        ss = rec.get("security_state")
        if not isinstance(ss, dict) or ss.get("schema") != "security_state.v1":
            continue
        states.append(ss)
        ticker = str(ss.get("ticker_display") or rec.get("ticker") or "")
        listing_key = str(ss.get("listing_key") or "")
        name = str(rec.get("name") or ss.get("name") or ticker)
        if listing_key:
            names[listing_key] = name
        if ticker:
            names[ticker] = name
        vs = rec.get("valuation_scenario")
        blob = None
        if isinstance(vs, dict):
            blob = vs.get("v1") if isinstance(vs.get("v1"), dict) else vs
        if isinstance(blob, dict) and blob.get("schema") == "valuation_scenario.v1":
            if ticker and not blob.get("ticker"):
                blob = {**blob, "ticker": ticker}
            postures.append(blob)
        market_at = None
        as_of_block = ss.get("as_of")
        if isinstance(as_of_block, dict):
            market_at = as_of_block.get("market_at")
        if not market_at:
            market_at = rec.get("asof")
        if isinstance(market_at, str) and market_at:
            if as_of is None or market_at[:10] > as_of:
                as_of = market_at[:10]
    return states, postures, names, as_of


def build_payload(root: Path) -> dict[str, Any]:
    states, postures, names, as_of = _load_stockdata(root)
    return compile_research_screener(
        states,
        postures,
        as_of=as_of,
        names=names,
    )


def render_html(root: Path, payload: dict[str, Any]) -> str:
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n

    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=True,
    )
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    tpl = env.get_template("research_screener.html.j2")
    return tpl.render(payload=payload, as_of=payload.get("as_of"))


def render(root: Path) -> dict[str, Any]:
    t0 = time.perf_counter()
    payload = build_payload(root)
    html = render_html(root, payload)
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    json_path = site / JSON_NAME
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    from lib.pages import write_page

    write_page(site / HTML_NAME, html)
    elapsed = time.perf_counter() - t0
    n = len(payload.get("rows") or [])
    print(f"research_screener::rows={n} elapsed_s={elapsed:.3f}", flush=True)
    if elapsed >= 60:
        print(
            f"::warning title=research_screener::local runtime {elapsed:.1f}s "
            "exceeded the 60s ceiling",
            flush=True,
        )
    return payload


def main() -> int:
    render(_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
