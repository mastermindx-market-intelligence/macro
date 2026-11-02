"""Real page-projection publication must not strand new UI assets."""
from pathlib import Path
import shutil
from scripts import build_government_revenue as owner

def test_page_projection_copies_sbir_and_investor_assets(tmp_path: Path):
    templates=tmp_path/"templates"
    templates.mkdir()
    canonical = Path(__file__).resolve().parents[1] / "templates"
    for name in ("government-revenue-page.js.j2", "theme.css", "product-nav-icons.css",
                 "government-revenue-parity.css"):
        shutil.copyfile(canonical / name, templates / name)
    shutil.copytree(canonical / "fonts", templates / "fonts")
    (templates/"government_revenue.html.j2").write_text("<html>{{ payload_json|safe }}</html>")
    assets=("government-revenue-sbir.js","government-revenue-sbir.css","government-revenue-investor.js","government-revenue-investor.css","government-revenue-theme-context.js","government-revenue-theme-context.css")
    for asset in assets:
        (templates/asset).write_text("/* unique bytes for "+asset+" */\n")
    html,data=owner._write_site_projection(tmp_path,{"companies":[]},latest_raw="{}",workspace_raw="{}")
    assert html.is_file() and data.read_text()=="{}"
    for asset in assets:
        assert (tmp_path/"site"/asset).read_bytes()==(templates/asset).read_bytes()
