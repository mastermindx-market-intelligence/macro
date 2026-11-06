"""Emit fresh DOM-test input from the real read contract and Jinja renderer."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from lib.aibrief_live import SCHEMA, view


def main(path: Path) -> None:
    now = datetime.now(timezone.utc)
    brief = {"schema": "master_brief.v2", "lens": "macro", "summary": "Current qualified read",
             "state_asof": now.date().isoformat(), "generated_at": now.isoformat(),
             "refresh_days": 1, "confidence": "medium", "degraded_reason": None}
    old = {**brief, "summary": "October retained read", "state_asof": "2026-10-16",
           "generated_at": "2026-10-18T06:50:33+00:00"}
    root = Path(__file__).resolve().parents[1]
    render = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True).get_template(
        "_aibrief_body.html.j2").module.aibrief_body
    projection = view({"schema": SCHEMA, "lens": "macro", "sequence": 2, "last_good": brief,
                       "attempt": {"state": "succeeded"}}, None, lens="macro", now=now)
    wire = {key: projection[key] for key in
            ("schema", "lens", "sequence", "revision", "server_time", "status", "valid_until")}
    wire["html"] = str(render(brief, "macro", live=projection))
    path.write_text(json.dumps({"old": str(render(old, "macro")), "fresh": wire}))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
