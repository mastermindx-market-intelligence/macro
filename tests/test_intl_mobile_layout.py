"""International destination must contain its risk-desk grid on narrow screens."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def test_international_desk_children_can_shrink_without_clipping_the_page():
    css = (ROOT / "templates/theme.css").read_text()
    rule = re.search(r"body\.page-intl \.ird-twocol\s*>\s*\*\s*\{([^}]+)\}", css)
    assert rule, "International grid children retain an overflowing automatic minimum"
    assert re.search(r"min-width\s*:\s*0\s*[;}]", rule.group(1) + "}"), rule.group(1)
    assert "overflow" not in rule.group(1), "Contain the grid; do not hide dashboard content"


def test_international_mobile_events_use_a_shrinkable_track():
    css = (ROOT / "templates/theme.css").read_text()
    assert re.search(r"body\.page-intl \.te-strip\s*\{\s*grid-template-columns\s*:\s*minmax\(0,\s*1fr\)", css), (
        "The inherited 340px event minimum overflows a 320px viewport"
    )


def test_international_mobile_controls_and_risk_labels_can_wrap():
    css = (ROOT / "templates/theme.css").read_text()
    for selector in ("body.page-intl .seg", "body.page-intl .ird-tx-row"):
        assert re.search(re.escape(selector) + r"\s*\{[^}]*flex-wrap\s*:\s*wrap", css), selector
    assert re.search(r"body\.page-intl \.rf-s\s*\{[^}]*overflow-wrap\s*:\s*anywhere", css)
