"""Refresh only the shared AI Brief fragment in an existing served page shell.

Called by the incumbent site deployment after its atomic mirror. This prevents
the new live reader from depending on another successful nightly full render.
Uses the SAME Jinja macro as build_aibrief and the API, and reads committed
briefs only: private live AI content must never be baked into public HTML.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from lib.aibrief_live import FILES, read_json
from scripts.vps_live_orchestrator import atomic_publish

PAGES = ("macro.html", "us_stocks.html", "china.html", "hk.html", "aibrief.html", "vector.html")


class Fragments(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text, self.offsets, self.rows = text, [0], []
        for line in text.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.current, self.depth, self.footer = None, 0, None
        self.feed(text)
        self.close()
        if self.current is not None:
            raise ValueError("unclosed AI Brief fragment")

    def absolute_position(self):
        line, col = self.getpos()
        return self.offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag != "div":
            return
        attr = dict(attrs)
        classes = (attr.get("class") or "").split()
        if self.current is None:
            if "aib2" in classes:
                lens = attr.get("data-lens")
                if lens not in FILES:
                    raise ValueError("unrecognized AI Brief lens")
                self.current = {"start": self.absolute_position(), "lens": lens, "footer": ""}
                self.depth = 1
        else:
            if self.depth == 1 and ("aib2-footer" in classes or any(
                    c in classes for c in ("isle-aibrief-footer", "cnx-receipt", "hkx-receipt"))):
                self.footer = self.absolute_position()
            self.depth += 1

    def handle_endtag(self, tag):
        if tag != "div" or self.current is None:
            return
        self.depth -= 1
        end = self.text.index(">", self.absolute_position()) + 1
        if self.depth == 1 and self.footer is not None:
            self.current["footer"] = self.text[self.footer:end]
            self.footer = None
        if self.depth == 0:
            self.current["end"] = end
            self.rows.append(self.current)
            self.current = None


def refresh_html(text: str, *, env: Environment, briefs: dict, css: str, version: str) -> str:
    rows = Fragments(text).rows
    if not rows:
        return text
    macro = env.get_template("_aibrief_body.html.j2").module.aibrief_body
    for row in reversed(rows):
        footer = row["footer"]
        # Avoid nesting the new explicit footer on subsequent deploys.
        if re.match(r'<div\s+class="aib2-footer"', footer):
            footer = footer[footer.index(">") + 1:footer.rfind("</div>")]
        body = str(macro(briefs.get(row["lens"]), row["lens"], show_catalysts=row["lens"] == "macro",
                         live={}, caller=lambda: Markup(footer))).strip()
        text = text[:row["start"]] + body + text[row["end"]:]
    # Only this owner's script/style are replaced. All other page bytes remain.
    text = re.sub(r'<script\b[^>]*\bsrc=["\']/?aibrief\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>\n?', "", text, flags=re.I)
    text = re.sub(r'<style data-aibrief-live-style="v1">.*?</style>\n?', "", text, flags=re.S)
    if "</head>" not in text or "</body>" not in text:
        raise ValueError("incomplete page shell")
    text = text.replace("</head>", '<style data-aibrief-live-style="v1">' + css + "</style>\n</head>", 1)
    return text.replace("</body>", '<script src="/aibrief.js?v=' + version + '" defer></script>\n</body>', 1)


def publish_shells(root: Path, served: Path) -> int:
    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True)
    briefs = {lens: read_json(root / "site" / filename) for lens, filename in FILES.items()}
    js_path = root / "templates/aibrief.js"
    version = hashlib.sha256(js_path.read_bytes()).hexdigest()[:16]
    css = env.get_template("_aibrief_css.j2").render()
    prepared = []
    try:
        # Validate every candidate before publication; a malformed page never
        # causes a partially rewritten HTML body to reach the existing mirror.
        for name in PAGES:
            target = served / name
            if not target.is_file():
                continue
            original = target.read_text()
            rendered = refresh_html(original, env=env, briefs=briefs, css=css, version=version)
            if rendered == original:
                continue
            fd, temporary = tempfile.mkstemp(prefix=".aibrief-shell-", suffix=".html", dir=served)
            with os.fdopen(fd, "w") as stream:
                stream.write(rendered)
            prepared.append((Path(temporary), target))
        # Script first; each subsequent HTML body points to these exact bytes.
        atomic_publish(js_path, served / "aibrief.js")
        for source, target in prepared:
            atomic_publish(source, target)
        return len(prepared)
    finally:
        for source, _ in prepared:
            source.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--served-dir", type=Path, required=True)
    args = parser.parse_args()
    count = publish_shells(Path(__file__).resolve().parents[1], args.served_dir)
    print(f"AI Brief live fragments published in {count} existing page shells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
