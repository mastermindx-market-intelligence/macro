"""Render the actual Macro template from the checked-out snapshot for visual review.

This does not call Sector Central compute, grade calls, write a premium payload, or publish.
The canonical nightly builder remains scripts/build_sector_central.py.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import i18n
from scripts import build_sector_central as builder

SITE = ROOT / "site"
OUT = Path(__file__).resolve().parent
SOURCES = [
    "basketdata/baskets.json", "basketdata/action_board.json",
    "basketdata/si_handoff.json", "sectordata/sector_central.json",
    "premiumdata/sector_central.json",
]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
before = {rel: digest(SITE / rel) for rel in SOURCES}
ctx = json.loads((SITE / "basketdata/si_handoff.json").read_text())
baskets = json.loads((SITE / "basketdata/baskets.json").read_text())
action_doc = json.loads((SITE / "basketdata/action_board.json").read_text())
data = json.loads((SITE / "sectordata/sector_central.json").read_text())
board = action_doc.get("action_board")
gate_cfg = builder._gate_cfg()
pgate, _ = builder.split_actnow(board, gate_cfg["preview_rows"], gated=gate_cfg["gated"])
bottoming = builder.build_bottoming_context(
    (baskets.get("theme_intel") or {}).get("act_now"), board)
rows, universe = builder._accumulation_rows()
source_as_of = (
    action_doc.get("as_of") or (baskets.get("theme_intel") or {}).get("as_of")
    or baskets.get("as_of") or data.get("as_of") or ""
)
env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
html = env.get_template("sector_central.html.j2").render(
    flows_html=builder._flows_section_html(), pgate=pgate, bottoming=bottoming,
    theme_context=ctx.get("theme_context"), factor_season=ctx.get("factor_season"),
    flow=ctx.get("flow"), basket_member_syms=ctx.get("basket_member_syms") or [],
    action_board=board, source_as_of=source_as_of,
    baskets_sha256=before["basketdata/baskets.json"],
    action_board_sha256=before["basketdata/action_board.json"],
    accumulation=rows, accumulation_universe_n=universe,
    theme_tape=builder._theme_tape_view(SITE),
    generated_utc=ctx.get("generated_utc") or data.get("as_of") or "",
)
after = {rel: digest(SITE / rel) for rel in SOURCES}
assert before == after, "Review rendering changed an incumbent source payload"
(OUT / "sector_central.html").write_text(html)
receipt = {
    "scope": "Actual Macro template; checked-out snapshot; review render only",
    "canonical_url": "https://www.mastermind-x.com/sector_central.html",
    "basket_as_of": baskets.get("as_of"), "sector_as_of": data.get("as_of"),
    "source_generation_as_of": source_as_of,
    "render_sha256": hashlib.sha256(html.encode()).hexdigest(),
    "render_bytes": len(html.encode()), "input_sha256": before,
    "inputs_unchanged": before == after, "sector_central_compute_called": False, "grader_called": False,
    "premium_payload_written": False, "production_published": False,
}
(OUT / "render-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
