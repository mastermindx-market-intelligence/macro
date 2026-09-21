"""User-visible contract for the Portfolio snapshot page on the Macro site."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "mastermind.html.j2"
JS = ROOT / "templates" / "mastermind.js"
SITE_ACCESS = ROOT / "config" / "site_access.yml"
CADDY = ROOT / "app" / "deploy" / "Caddyfile"


def _node(expression: str):
    if shutil.which("node") is None:
        pytest.fail("node is required to execute the Mastermind page contract")
    script = (
        f"const mm = require({json.dumps(str(JS))});\n"
        f"const value = ({expression});\n"
        "process.stdout.write(JSON.stringify(value));\n"
    )
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_static_chrome_does_not_claim_a_current_daily_cadence() -> None:
    text = TEMPLATE.read_text(encoding="utf-8").lower()
    assert "daily snapshot" not in text
    assert "pushed twice" not in text
    assert "refreshed twice" not in text


def test_live_dashboard_fallback_uses_the_public_https_product() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="mm-live" href="https://bot.mastermind-x.com"' in text
    assert "http://localhost:8000" not in text


def test_snapshot_cannot_override_the_live_link_with_loopback() -> None:
    assert _node('mm.safeLiveUrl("http://localhost:8000")') == "https://bot.mastermind-x.com"
    assert _node('mm.safeLiveUrl("https://bot.mastermind-x.com")') == "https://bot.mastermind-x.com"
    assert _node('mm.safeLiveUrl("https://evil.example")') == "https://bot.mastermind-x.com"


def test_structured_market_status_formats_as_human_text() -> None:
    assert _node('mm.formatMarketStatus({open:false, venue:"HKEX"}, "en")') == "HKEX · Closed"
    assert _node('mm.formatMarketStatus({open:true, venue:"NASDAQ"}, "en")') == "NASDAQ · Open"
    assert _node('mm.formatMarketStatus("After hours", "en")') == "After hours"


def test_snapshot_freshness_distinguishes_current_and_stale_bytes() -> None:
    fresh = _node(
        'mm.snapshotFreshness("2026-09-19T12:00:00Z", Date.parse("2026-09-21T12:00:00Z"))'
    )
    stale = _node(
        'mm.snapshotFreshness("2026-09-18T11:59:59Z", Date.parse("2026-09-21T12:00:00Z"))'
    )
    unknown = _node('mm.snapshotFreshness("not-a-date", Date.parse("2026-09-21T12:00:00Z"))')
    assert fresh["state"] == "fresh"
    assert stale["state"] == "stale"
    assert stale["ageHours"] > 72
    assert unknown["state"] == "unknown"


def test_access_failures_keep_the_shell_truthful() -> None:
    signin = _node('mm.accessState(401, {signin_url:"/?signin=1"}, "en")')
    upgrade = _node('mm.accessState(403, {upgrade_url:"/plans.html?plan=pro"}, "en")')
    unavailable = _node('mm.accessState(500, {}, "en")')
    assert signin == {"kind": "signin", "href": "/?signin=1"}
    assert upgrade == {"kind": "upgrade", "href": "/plans.html?plan=pro"}
    assert unavailable == {"kind": "unavailable", "href": ""}


def test_archived_books_are_explicitly_classified() -> None:
    archived = _node(
        'mm.bookLifecycle({archived:true,status:"archived",superseded_by:"autonomous"}, "en")'
    )
    active = _node('mm.bookLifecycle({active:true,status:"active"}, "en")')
    assert archived["archived"] is True
    assert archived["label"] == "Archived"
    assert archived["supersededBy"] == "autonomous"
    assert active["archived"] is False
    assert active["label"] == "Active"


def test_presentation_script_is_public_but_snapshot_payload_remains_gated() -> None:
    config = yaml.safe_load(SITE_ACCESS.read_text(encoding="utf-8"))
    public_exact = set(config["public"]["exact"])
    assert "/mastermind.js" in public_exact
    assert "/mastermind/mastermind_snapshot.json" not in public_exact

    caddy = CADDY.read_text(encoding="utf-8")
    assert caddy.count("/mastermind.js") >= 4
    assert "/mastermind/mastermind_snapshot.json" not in caddy


def test_committed_snapshot_carries_current_lifecycle_and_safe_default() -> None:
    payload = json.loads(
        (ROOT / "site" / "mastermind" / "mastermind_snapshot.json").read_text(encoding="utf-8")
    )
    books = {book["id"]: book for book in payload["books"]}

    assert payload["live_url"] == "https://bot.mastermind-x.com"
    assert payload["default_book"] == "autonomous"
    for book_id in {"flagship", "heavyweight", "etf"}:
        assert books[book_id]["active"] is False
        assert books[book_id]["status"] == "archived"
        assert books[book_id]["archived"] is True
        assert books[book_id]["superseded_by"] == "autonomous"
    for book_id in {"autonomous", "china", "hk", "self_directed"}:
        assert books[book_id]["active"] is True
        assert books[book_id]["status"] == "active"
        assert books[book_id]["archived"] is False
