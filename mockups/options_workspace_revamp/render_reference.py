"""Render the supporting Options design reference, never production market data."""
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
(HERE / "reference.html").write_text(env.get_template("reference.html.j2").render(), encoding="utf-8")
print("Rendered supporting design reference: mockups/options_workspace_revamp/reference.html")
