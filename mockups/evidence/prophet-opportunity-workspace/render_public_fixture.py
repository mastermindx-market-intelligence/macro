"""Render an offline public Prophet fixture for capture_page_evidence.py."""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import build_site as build
from tests.test_dashboard_template_render import _base_vm, _env


def render(out):
    site = ROOT / "site"
    out.mkdir(parents=True, exist_ok=False)
    board = json.loads((site / "factordata/us_standouts.json").read_bytes())
    actions = json.loads((site / "basketdata/action_board.json").read_bytes())[
        "action_board"
    ]
    book, book_error = build._read_us_prophet_book(site / "prophet/index.json")
    vm = _base_vm()
    vm.update(
        latest={"date": board.get("as_of"), "quad_name": None, "base_effect": None},
        generated_utc=board.get("as_of"),
        market_state=None,
        us_standouts=board,
        action_board=actions,
        us_prophet_book=book,
        us_prophet_book_error=book_error,
        us_today_source_binding=None,
        top_setups=None,
        pb=None,
    )
    cfg = build._us_board_gate_cfg()
    shell, gate, _ = build._split_us_board(
        board, cfg["preview_rows"], gated=cfg["gated"]
    )
    plans, plan_gate, withheld = build._split_us_prophet_board(
        book,
        cfg["preview_rows"],
        gated=build._us_life_gate_cfg(),
        withheld=build._us_withheld_names(vm, cfg["panel_preview_rows"]),
    )
    repair = build._us_life_repair_context(vm, plans, plan_gate, cfg["preview_rows"])
    panels, panel_gate, _ = build._split_us_panels(
        vm, cfg["panel_preview_rows"], gated=cfg["panels"]
    )
    shell, repair = build._us_apply_panel_withholding(
        vm, shell, repair, panels, cfg["preview_rows"]
    )
    relations = build._plan_relations_for(book, book_error)
    vm.update(
        plan_rel={"state": relations[0], "plans": []},
        plan_rel_by_ticker=build._plan_relations_for_shell(relations, withheld),
    )
    env = _env()
    env.autoescape = True
    html = env.get_template("dashboard.html.j2").render(
        **{
            **vm,
            **panels,
            **repair,
            "us_standouts": shell,
            "gate": gate,
            "pgate": panel_gate,
            "us_today_native_emit": None,
            "us_prophet_book": plans,
            "life_gate": plan_gate,
            "us_prophet_episodes": build._us_prophet_episode_map(
                (book or {}).get("plans") or []
            ),
        },
        mode="stocks"
    )
    # The fixture server exposes only this public render and local static assets.
    # Browser contexts are anonymous. External services and frames are not part of this proof.
    policy = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-src 'none'; form-action 'none'"
    html = html.replace(
        "<head>",
        '<head><meta http-equiv="Content-Security-Policy" content="' + policy + '">',
        1,
    )
    assert "Content-Security-Policy" in html
    doc = BeautifulSoup(html, "html.parser")
    assert doc.select_one("#stocks-header .prophet-section-nav") and doc.select(
        "#us-today-grid .po-card"
    )
    assert all(not row.get("id") or row["id"] not in html for row in withheld)
    (out / "us_stocks.html").write_text(html)
    for name in ("assets", "fonts"):
        if (site / name).is_dir():
            shutil.copytree(
                site / name,
                out / name,
                ignore=shutil.ignore_patterns("*.json", "*.html", "*.js", "*.map"),
            )
    for asset in site.iterdir():
        if asset.is_file() and asset.suffix in {
            ".css",
            ".js",
            ".svg",
            ".woff2",
            ".ico",
        }:
            shutil.copyfile(asset, out / asset.name)
    return {
        "fixture": "public dashboard using native board, Plan and panel preview splits",
        "board_as_of": board.get("as_of"),
        "rows": [c.get("data-ticker") for c in doc.select("#us-today-grid .po-card")],
        "html_sha256": hashlib.sha256(html.encode()).hexdigest(),
        "source_sha256": {
            str(f.relative_to(ROOT)): hashlib.file_digest(
                f.open("rb"), "sha256"
            ).hexdigest()
            for f in (
                site / "factordata/us_standouts.json",
                site / "basketdata/action_board.json",
                site / "prophet/index.json",
                site / "theme.js",
            )
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(json.dumps(render(parser.parse_args().output), indent=2))
