from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "account.js").read_text(encoding="utf-8")
SITE = (ROOT / "site" / "account.js").read_text(encoding="utf-8")


def test_account_template_and_deployed_asset_stay_byte_identical():
    assert TEMPLATE == SITE


def test_account_shell_primary_controls_use_existing_product_floor():
    for selector in (
        r"\.mmacc-trigger\{",
        r"\.mmacc-x\{",
        r"\.mmacc-btn\{",
        r"\.mmacc-mini\{",
        r"\.mmacc-input\{",
    ):
        matches = re.findall(selector + r"([^}]*)\}", TEMPLATE, re.S)
        assert matches, selector
        joined = "\n".join(matches)
        if selector in (r"\.mmacc-trigger\{", r"\.mmacc-x\{"):
            assert "width:40px" in joined and "height:40px" in joined, selector
        else:
            assert "min-height:40px" in joined, selector
            assert "box-sizing:border-box" in joined, selector


def test_account_switch_keeps_compact_visual_with_coarse_pointer_hit_slop():
    assert ".mmacc-switch{width:34px;height:20px;" in TEMPLATE
    assert re.search(
        r"\.mmacc-switch\{[^}]*touch-action:manipulation",
        TEMPLATE,
        re.S,
    )
    assert re.search(
        r"@media \(hover:none\),\(pointer:coarse\)\{\.mmacc-switch::before\{"
        r"[^}]*width:40px[^}]*height:40px",
        TEMPLATE,
        re.S,
    )


def test_account_auth_endpoints_and_actions_remain_present():
    for token in (
        "/api/account/prefs",
        "send-link",
        "signout",
        "signout-all",
        "do-delete",
        "save-email",
        "save-pw",
    ):
        assert token in TEMPLATE
