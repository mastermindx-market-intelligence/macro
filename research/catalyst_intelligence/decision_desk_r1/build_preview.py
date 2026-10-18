"""Build the standalone contract replay; fixtures are never a production fallback."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def build() -> Path:
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    fixture_dir = here / "fixtures"
    receipt = json.loads((fixture_dir / "capture-receipt.json").read_text())
    data = {}
    for item in receipt["responses"]:
        raw = (fixture_dir / item["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError("Captured API bytes changed: " + item["file"])
        data[item["file"]] = json.loads(raw)
    html = (here / "preview_shell.html").read_text()
    for marker, content in {
        "/* THEME_TOKENS */": (here / "theme_excerpt.css").read_text(),
        "/* COMPONENT_CSS */": (root / "templates/biocatalyst_decision_desk.css").read_text(),
        "/* COMPONENT_JS */": (root / "templates/biocatalyst_decision_desk.js").read_text(),
        "/* FIXTURES */": json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    }.items():
        if html.count(marker) != 1:
            raise ValueError("Preview marker missing or repeated: " + marker)
        html = html.replace(marker, content)
    out = here / "Decision_Desk_Contract_Replay.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
