"""The freshness client must be inserted at the document's real closing body tag."""
from __future__ import annotations

from pathlib import Path

from scripts.optimize_assets import _attach_aibrief_freshness


def test_injection_uses_final_body_close_not_literal_inside_script(tmp_path: Path) -> None:
    site = tmp_path / "site"
    asset = site / "assets" / "js" / "aibrief-freshness.js"
    asset.parent.mkdir(parents=True)
    asset.write_text("window.__aibriefFreshness = true;\n")

    source = (
        '<html><body><script>const marker = "</body>";</script>'
        '<div class="aib2" data-lens="macro"></div></body></html>'
    )
    out = _attach_aibrief_freshness(source, site, site)

    assert out.index("aibrief-freshness.js") > out.index("</script>")
    assert out.index("aibrief-freshness.js") < out.rindex("</body>")
    assert 'const marker = "</body>";' in out
