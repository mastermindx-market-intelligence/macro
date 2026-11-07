"""Render the supporting Options design reference, never production market data."""
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
env = Environment(loader=FileSystemLoader([str(HERE), str(ROOT / "templates")]), autoescape=True)
try:
    import sys
    sys.path.insert(0, str(ROOT))
    from engine import i18n
    env.globals.update(td=i18n.td, tr=i18n.tr)
except ImportError:
    env.globals.update(td=lambda x, *a, **k: x, tr=lambda x, *a, **k: x)
html = env.get_template("reference.html.j2").render()
def local_asset(match):
    attr, asset = match.group(1), match.group(2)
    if (ROOT / "templates" / asset.split("?")[0]).is_file():
        return attr + '="../templates/' + asset + '"'
    return match.group(0)
html = re.sub(r'(src|href)="([A-Za-z0-9_-][A-Za-z0-9_./-]*[.](?:js|css|svg|png|woff2)(?:[?][^"]*)?)"', local_asset, html)
html = html.replace("</body>", '<script src="../templates/theme.js"></script></body>')
(HERE / "reference.html").write_text(html, encoding="utf-8")
print("Rendered supporting design reference: mockups/options_workspace_revamp/reference.html")
