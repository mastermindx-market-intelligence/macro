"""Reproduce the China summary/detail metric mismatch on immutable template bytes.
Renders the actual summary row against controlled inputs and compares its words
with the actual builder's deep-drawdown band map. No product or ledger writes.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[2]
PIN = "eb9e91961ddc4f3043d0dad358602525e66eccda"

def committed(path):
    proc = subprocess.run(["git", "show", f"{PIN}:{path}"], cwd=ROOT,
                          capture_output=True, check=True, timeout=30)
    return proc.stdout.decode()

def main():
    template = committed("templates/china.html.j2")
    builder = committed("scripts/build_china.py")
    assignments = [n for n in ast.walk(ast.parse(builder)) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "_DD_READ" for t in n.targets)]
    if len(assignments) != 1:
        raise RuntimeError("Deep-drawdown map is not uniquely identified.")
    words = ast.literal_eval(assignments[0].value)
    marker = "      <div class=\"cnx-kv\"><span class=\"k\">{{ t('Deep-drawdown gauge'"
    start = template.index(marker)
    end = template.index('      <div class="cnx-foot">', start)
    fragment = template[start:end]
    renderer = Environment(undefined=StrictUndefined, autoescape=True).from_string(fragment)
    cases = [
        ("screenshot_43_vs_17", 43, 17, "low"),
        ("high_drawdown_hidden_by_low_slowdown", 17, 84, "high"),
        ("same_scores_but_wrong_thresholds", 60, 60, "elevated"),
        ("missing_is_not_calm", None, None, None),
    ]
    rows = []
    for name, slowdown, drawdown, band in cases:
        conditions = {"recession": {"score": slowdown},
                      "drawdown_risk": {"score": drawdown, "band": band}}
        rendered = renderer.render(latest={"conditions": conditions}, t=lambda en, zh: en)
        text = " ".join(re.sub(r"<[^>]+>", " ", rendered).split())
        observed = text.split()[-1].lower()
        expected = words[band][0] if band in words and drawdown is not None else "unavailable"
        rows.append(dict(case=name, slowdown_score=slowdown, drawdown_score=drawdown,
                         drawdown_band=band, observed_summary=observed,
                         expected_detail_read=expected, mismatch=observed != expected))
    result = dict(source_pin=PIN, production_mutations=0, synthetic_render=True,
                  template_sha256=hashlib.sha256(template.encode()).hexdigest(),
                  builder_sha256=hashlib.sha256(builder.encode()).hexdigest(),
                  summary_fragment_sha256=hashlib.sha256(fragment.encode()).hexdigest(),
                  summary_start_line=template[:start].count("\n") + 1,
                  drawdown_band_map=words, cases=rows)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    if not all(row["mismatch"] for row in rows):
        raise SystemExit("An expected baseline mismatch did not reproduce; inspect the actual output.")

if __name__ == "__main__":
    main()
