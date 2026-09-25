from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent
SITE = ROOT / "site"
THEME_ID = "cn_pharma_cxo"
ACTION_HEAD = "6e0beeec8f720333dd72ab47a9e7c39fed6238a1"
ACTION_PATH = "engine/china_act_now.py"
ACTION_SHA256 = "fcb9c8996294e1f9cf0fe5e6835c27785ef4006cf43b9aba58cebff0b05cc8f7"
INPUT_HEAD = "88a3f1cfd18f391d2802e9086dc00f6fe5545607"
INPUT_PATH = "site/chinabasketdata/baskets.json"
INPUT_SHA256 = "69c46ef1ec0c60f450dfe6c443d2d01c70da81a91f34c8763c04f747edbb4040"
INPUT_DETAIL_PATH = f"site/basket_china/{THEME_ID}.html"
INPUT_DETAIL_SHA256 = "69a2d8f9bfb49552e01da251bf7e30d8cc778f0dcdcfa8e0c67570dc492282a6"
OBSERVED_AT = datetime(2026, 9, 23, 5, 0, tzinfo=timezone.utc)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(ref: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{ref}:{path}"])


def parse_detail(page: str) -> dict:
    marker = "const DETAIL = "
    assert page.count(marker) == 1
    detail, _ = json.JSONDecoder().raw_decode(page.split(marker, 1)[1])
    return detail


def load_action_assembler(temp_root: Path):
    archive = temp_root / "action-source.tar"
    with archive.open("wb") as stream:
        subprocess.run(
            [
                "git", "-C", str(ROOT), "archive", "--format=tar", ACTION_HEAD,
                "engine/__init__.py", "engine/china_act_now.py", "engine/i18n.py",
                "lib/__init__.py", "lib/cn_calendar.py",
            ],
            check=True,
            stdout=stream,
        )
    with tarfile.open(archive) as bundle:
        bundle.extractall(temp_root, filter="data")
    sys.path.insert(0, str(temp_root))
    from engine.china_act_now import assemble_act_now
    return assemble_act_now


def render_exact_input(detail: dict, source_page: str) -> str:
    stamps = re.findall(
        r"<span>([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} UTC)</span>",
        source_page,
    )
    assert len(stamps) == 1, stamps
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    template = env.get_template("basket_detail.html.j2")
    raw = json.dumps(
        detail, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).replace("</", "<\\/")
    return template.render(
        detail_json=raw,
        basket_name=detail["basket"].get("name", THEME_ID),
        generated_utc=stamps[0],
        back_href=detail["back"],
        back_label_en="China Sector Intelligence",
        back_label_zh="中国行业智慧",
    )


def browser_proof(page_html: str, detail: dict) -> list[dict]:
    output = EVIDENCE / "browser-cross-component"
    output.mkdir(parents=True, exist_ok=True)
    for old in output.glob("*.png"):
        old.unlink()

    entry_checks = detail.get("act_now", {}).get("entry_checks") or []
    expected_qualified = sum(1 for row in entry_checks if row.get("eligible"))
    records: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for theme in ("dark", "light"):
            for language in ("en", "zh"):
                for width in (1440, 390):
                    context = browser.new_context(
                        viewport={"width": width, "height": 1000}, device_scale_factor=1
                    )
                    context.add_init_script(
                        "localStorage.setItem('theme',"
                        + json.dumps(theme)
                        + ");localStorage.setItem('lang',"
                        + json.dumps(language)
                        + ");"
                    )
                    page_errors: list[str] = []
                    request_failures: list[str] = []
                    unavailable_live_requests: list[str] = []

                    def serve(route):
                        url = urlsplit(route.request.url)
                        if url.hostname != "continuation-contract.local":
                            route.fulfill(status=204, body="")
                            return
                        path = unquote(url.path)
                        if path == f"/basket_china/{THEME_ID}.html":
                            route.fulfill(status=200, content_type="text/html", body=page_html)
                            return
                        if path.startswith(("/live/", "/api/", "/premiumdata/")):
                            unavailable_live_requests.append(path)
                            route.fulfill(
                                status=401,
                                content_type="application/json",
                                body='{"error":"not_part_of_local_proof"}',
                            )
                            return
                        target = (SITE / path.lstrip("/")).resolve()
                        if target.is_relative_to(SITE.resolve()) and target.is_file():
                            route.fulfill(
                                status=200,
                                content_type=mimetypes.guess_type(str(target))[0]
                                or "application/octet-stream",
                                body=target.read_bytes(),
                            )
                        else:
                            route.fulfill(status=404, body="Unavailable in local proof")

                    context.route("**/*", serve)
                    page = context.new_page()
                    page.on("pageerror", lambda error: page_errors.append(str(error)))
                    page.on(
                        "requestfailed",
                        lambda request: request_failures.append(request.url),
                    )
                    response = page.goto(
                        f"http://continuation-contract.local/basket_china/{THEME_ID}.html",
                        wait_until="networkidle",
                    )
                    assert response and response.status == 200
                    applied = page.evaluate(
                        "({theme:document.documentElement.dataset.theme,"
                        "language:document.documentElement.dataset.lang})"
                    )
                    assert applied == {"theme": theme, "language": language}, applied
                    hero = page.locator(".panel.hero")
                    hero_text = hero.inner_text()
                    rating = "ACCUMULATE" if language == "en" else "加仓"
                    initial_context = (
                        "Initial entry context:"
                        if language == "en"
                        else "初始入场条件："
                    )
                    assert rating in hero_text, (language, hero_text)
                    assert initial_context in hero_text, (language, hero_text)
                    assert "WAIT FOR ENTRY" not in hero_text
                    assert "等待入场" not in hero_text
                    stock_link = page.locator("[data-stock-entry-link]")
                    stock_checks_opened = False
                    if entry_checks:
                        assert stock_link.count() == 1
                        stock_link.focus()
                        page.keyboard.press("Enter")
                        stock_panel = page.locator("#stock-entry-checks")
                        assert stock_panel.evaluate("element => element.open")
                        stock_text = stock_panel.inner_text()
                        stock_checks_opened = True
                        if expected_qualified == 0:
                            assert (
                                "0 qualified" in stock_text
                                if language == "en"
                                else "0 只通过" in stock_text
                            )
                    else:
                        assert stock_link.count() == 0
                    geometry = page.evaluate(
                        "({scroll:document.documentElement.scrollWidth,viewport:innerWidth})"
                    )
                    assert geometry["scroll"] <= geometry["viewport"] + 1, geometry
                    hero.scroll_into_view_if_needed()
                    filename = f"exact-continuation-{theme}-{language}-{width}.png"
                    screenshot = output / filename
                    hero.screenshot(path=str(screenshot))
                    assert not page_errors, page_errors
                    assert not request_failures, request_failures
                    records.append(
                        {
                            "theme": theme,
                            "language": language,
                            "width": width,
                            "http_status": response.status,
                            "rating_visible": True,
                            "initial_context_visible": True,
                            "blanket_wait_absent": True,
                            "stock_checks_opened": stock_checks_opened,
                            "qualified_count": expected_qualified if entry_checks else None,
                            "page_overflow": False,
                            "page_errors": page_errors,
                            "request_failures": request_failures,
                            "unavailable_live_requests": sorted(
                                set(unavailable_live_requests)
                            ),
                            "screenshot": f"browser-cross-component/{filename}",
                            "screenshot_sha256": sha256(screenshot.read_bytes()),
                        }
                    )
                    context.close()
        browser.close()
    return records


def main() -> int:
    action_source = git_bytes(ACTION_HEAD, ACTION_PATH)
    input_bytes = git_bytes(INPUT_HEAD, INPUT_PATH)
    input_page_bytes = git_bytes(INPUT_HEAD, INPUT_DETAIL_PATH)
    assert sha256(action_source) == ACTION_SHA256
    assert sha256(input_bytes) == INPUT_SHA256
    assert sha256(input_page_bytes) == INPUT_DETAIL_SHA256

    input_data = json.loads(input_bytes)
    input_page = input_page_bytes.decode()
    detail = parse_detail(input_page)

    with tempfile.TemporaryDirectory(prefix="mmx-7567-action-contract-") as temp:
        assembler = load_action_assembler(Path(temp))
        try:
            action = assembler(
                [], input_data["theme_intel"], None, observed_at=OBSERVED_AT
            )
        finally:
            assert sys.path[0] == str(Path(temp))
            sys.path.pop(0)

    matches = [
        (lane, row)
        for lane, rows in (action.get("display_lanes") or {}).items()
        for row in rows
        if row.get("id") == THEME_ID
    ]
    assert len(matches) == 1, matches
    lane, row = matches[0]
    source_lanes = [source.get("lane") for source in row.get("source_reads", [])]
    assert lane == "buy_now"
    assert row.get("entry_route") == "continuation"
    assert row.get("theme_decision", {}).get("status") == "CURRENT"
    assert row.get("theme_decision", {}).get("final_reco") == "accumulate"
    assert row.get("theme_decision", {}).get("source_conflict") is False
    assert row.get("observed_lanes") == ["wait_pullback"]
    assert source_lanes == ["wait_pullback"]
    assert "bottoming_watch" not in source_lanes

    theme = detail["theme"]
    clean_entry = ((theme.get("textures") or {}).get("clean_entry") or {}).get("flag")
    assert detail["basket"]["id"] == THEME_ID == theme["id"] == row["id"]
    assert detail["as_of"] == row["theme_decision"]["source_as_of"]
    assert theme.get("reco") == row["theme_decision"]["final_reco"] == "accumulate"
    assert theme.get("label") == row["theme_decision"]["final_label"] == "dominant"
    assert clean_entry is False
    entry_checks = detail.get("act_now", {}).get("entry_checks") or []
    qualified = [entry for entry in entry_checks if entry.get("eligible")]
    assert not qualified

    rendered = render_exact_input(detail, input_page)
    assert "const recoChip = t => badge(" in rendered
    assert "Initial entry context:" in rendered
    assert "初始入场条件：" in rendered
    assert "WAIT FOR ENTRY" not in rendered
    assert "等待入场" not in rendered
    browser_records = browser_proof(rendered, detail)
    assert len(browser_records) == 8

    template_bytes = (ROOT / "templates/basket_detail.html.j2").read_bytes()
    receipt = {
        "schema": "theme_continuation_detail_contract.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "theme_id": THEME_ID,
        "action_card": {
            "source_head": ACTION_HEAD,
            "source_path": ACTION_PATH,
            "source_sha256": ACTION_SHA256,
            "input_head": INPUT_HEAD,
            "input_path": INPUT_PATH,
            "input_sha256": INPUT_SHA256,
            "observed_at": OBSERVED_AT.isoformat(),
            "display_lane": lane,
            "entry_route": row["entry_route"],
            "observed_lanes": row["observed_lanes"],
            "source_read_lanes": source_lanes,
            "theme_decision": row["theme_decision"],
            "recommendation": row["reco"],
            "recommendation_en": row["reco_en"],
            "recommendation_zh": row["reco_zh"],
            "score": row["score"],
        },
        "detail": {
            "input_page_head": INPUT_HEAD,
            "input_page_path": INPUT_DETAIL_PATH,
            "input_page_sha256": INPUT_DETAIL_SHA256,
            "template_path": "templates/basket_detail.html.j2",
            "template_sha256": sha256(template_bytes),
            "source_as_of": detail["as_of"],
            "recommendation": theme["reco"],
            "recommendation_en": theme["reco_en"],
            "recommendation_zh": theme["reco_zh"],
            "label": theme["label"],
            "clean_entry": clean_entry,
            "entry_checks": len(entry_checks),
            "qualified_count": len(qualified) if entry_checks else None,
            "stock_entry_checks_available_on_frozen_input": bool(entry_checks),
            "blanket_wait_literal_absent": True,
            "native_rating_preserved": True,
            "initial_entry_context_separate": True,
        },
        "identity": {
            "same_theme_id": True,
            "same_source_session": True,
            "same_final_recommendation": True,
            "continuation_without_bottoming_event": True,
            "stock_entry_permission_widened": False,
        },
        "browser": {
            "captures": len(browser_records),
            "records": browser_records,
        },
        "scope": {
            "production": False,
            "trade_authority": False,
            "description": (
                "Exact accepted action-card source and exact immutable input are "
                "executed, then the same input's compiled detail payload is rendered "
                "through the candidate template. This is a cross-component software "
                "contract proof, not a current recommendation or production proof."
            ),
        },
    }
    (EVIDENCE / "cross-component-receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        json.dumps(
            {
                "theme_id": THEME_ID,
                "display_lane": lane,
                "entry_route": row["entry_route"],
                "source_session": detail["as_of"],
                "clean_entry": clean_entry,
                "qualified_count": len(qualified) if entry_checks else None,
                "browser_captures": len(browser_records),
                "template_sha256": receipt["detail"]["template_sha256"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
