from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HK = (ROOT / "templates" / "hk.html.j2").read_text(encoding="utf-8")
CA = (ROOT / "templates" / "canada.html.j2").read_text(encoding="utf-8")


def test_hk_mobile_shell_standalone_controls_use_product_floor():
    assert re.search(
        r"body\.page-hk \.hkx-hbtn\{[^}]*min-height:40px[^}]*box-sizing:border-box",
        HK,
        re.S,
    )
    assert re.search(
        r"body\.page-hk \.hkx-tkr-btn\{[^}]*min-height:40px[^}]*box-sizing:border-box",
        HK,
        re.S,
    )


def test_canada_mobile_shell_standalone_controls_use_product_floor():
    assert re.search(
        r"body\.page-canada \.cax-hbtn\{[^}]*min-height:40px[^}]*box-sizing:border-box",
        CA,
        re.S,
    )
    assert re.search(
        r"body\.page-canada \.cax-tkr-btn\{[^}]*min-height:40px[^}]*box-sizing:border-box",
        CA,
        re.S,
    )


def test_canada_mobile_sector_rows_make_the_ticker_target_real_without_hit_slop():
    mobile = re.search(
        r"@media \(max-width:600px\)\{(?P<body>.*?)\n\s*\}",
        CA,
        re.S,
    )
    assert mobile, "Canada template needs a bounded <=600px mobile control rule"
    body = mobile.group("body")
    assert re.search(
        r"body\.page-canada \.cax-sorow\{[^}]*min-height:40px[^}]*align-items:center",
        body,
        re.S,
    )
    assert re.search(
        r"body\.page-canada \.cax-sotkr\{[^}]*display:inline-flex[^}]*align-items:center[^}]*align-self:stretch",
        body,
        re.S,
    )
