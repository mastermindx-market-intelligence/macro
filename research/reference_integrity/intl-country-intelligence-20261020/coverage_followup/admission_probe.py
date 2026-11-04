"""Read-only local proof against a snapshot obtained through read_file.

No network, remote process, production import, source acquisition, or data write.
Synthetic inputs demonstrate current code behavior; they are not acquired data.
"""
import ast
from datetime import date
from hashlib import sha256
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
source = (ROOT / "collector_snapshot.py").read_text()
tree = ast.parse(source)
names = {
    "_finite", "_month", "_mapping", "_source_clock", "_valid_incoming",
    "parse_taiwan_release",
}
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
assert {node.name for node in nodes} == names
namespace = {
    "date": date, "math": math, "re": re, "sha256": sha256,
    "TW_PAGE": "https://eng.dgbas.gov.tw/News_Content.aspx?n=4438&s=236587",
    "TW_PUBLISHED": "2026-08-14",
}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "collector_snapshot.py", "exec"), namespace)
validate = namespace["_valid_incoming"]

base = {
    "metric": "gdp", "value": 7.8, "unit": "% y/y", "period": "2026-Q2",
    "status": "provisional", "provider": "Synthetic test provider",
    "source_url": "https://example.gov/synthetic-gdp",
}
checks = []
assert validate(base, cc="IN", metric="gdp") is False
checks.append("Current validator rejects a quarterly GDP y/y receipt.")
assert validate({**base, "period": "2026-06"}, cc="IN", metric="gdp") is False
checks.append("Changing only the period does not repair the wrong GDP unit rule.")
assert validate({**base, "unit": "%"}, cc="IN", metric="gdp") is False
checks.append("Changing only the unit does not repair the monthly-only period rule.")
assert validate({**base, "unit": "%", "period": "2026-06"}, cc="IN", metric="gdp") is True
checks.append("Widening only the merge allowlist would admit an incorrectly typed monthly GDP record.")

merge = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "merge_country_inputs")
allowlists = [
    tuple(item.value for item in node.comparators[0].elts)
    for node in ast.walk(merge)
    if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "key"
    and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn)
    and isinstance(node.comparators[0], ast.Tuple)
    and all(isinstance(item, ast.Constant) for item in node.comparators[0].elts)
]
assert ("inflation", "policy") in allowlists
checks.append("Merge's explicit metric allowlist excludes GDP.")

synthetic_html = """<main><p>August 14, 2026</p>
<p>Preliminary Estimate of Real GDP in 2026Q2: real GDP expanded 12.93% year-over-year.</p>
<p>Real GDP is predicted to grow 1.23% and 4.56% in 2026 and 2027.</p></main>"""
parsed = namespace["parse_taiwan_release"](synthetic_html, retrieved_at="2026-10-20T00:00:00+00:00")
assert parsed["TW"]["kind"] == "sourced_forecast"
assert parsed["TW"]["values"] == {"2026": 1.23, "2027": 4.56}
assert "metric" not in parsed["TW"] and "gdp" not in parsed["TW"]
checks.append("Existing Taiwan parser extracts forecasts and omits the observed quarterly GDP text.")

print(json.dumps({
    "scope": "local diagnostic against read-tool snapshot; synthetic inputs; no acquisition",
    "checks_passed": len(checks),
    "checks": checks,
    "snapshot_text_sha256": sha256(source.encode()).hexdigest(),
    "source_wire_sha256": None,
}, indent=2))
