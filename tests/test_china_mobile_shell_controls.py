from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "templates" / "china.html.j2").read_text(encoding="utf-8")


def test_china_shell_standalone_controls_use_product_interaction_floor():
    assert re.search(
        r"body\.page-china \.cnx-hbtn\{[^}]*min-height:40px[^}]*box-sizing:border-box",
        SOURCE,
        re.S,
    )
    assert re.search(
        r"body\.page-china \.cnx-dlg-close\{[^}]*width:40px[^}]*height:40px",
        SOURCE,
        re.S,
    )
    assert re.search(
        r"\.cn-depth > summary\{[^}]*min-height:40px[^}]*box-sizing:border-box",
        SOURCE,
        re.S,
    )


def test_china_lens_keeps_compact_visual_but_has_coarse_pointer_hit_slop():
    assert re.search(
        r"\.cnx-wrap \.cnx-lens\{[^}]*touch-action:manipulation",
        SOURCE,
        re.S,
    )
    assert re.search(
        r"@media \(hover:none\),\(pointer:coarse\)\{\.cnx-wrap \.cnx-lens::before\{"
        r"[^}]*width:40px[^}]*height:40px",
        SOURCE,
        re.S,
    )


def test_china_dialog_close_buttons_are_named_buttons():
    tags = re.findall(
        r'<button\b[^>]*class="[^"]*cnx-dlg-close[^"]*"[^>]*>',
        SOURCE,
        re.S,
    )
    assert len(tags) >= 10
    for tag in tags:
        assert 'type="button"' in tag
        assert 'aria-label=' in tag
        assert "Close" in tag and "关闭" in tag
