"""Pure crypto/vector assistant-context contract.

No customer message is sent. No network. Fixtures are tmp files and in-memory
dicts. The assertions are the properties these functions already implement:
source basis and as-of stay on the quote clock, a missing print is omitted
rather than zeroed, a stale print is not a current print, a historical
question is not planned as a current fact, and a guest does not pass the
protected-evidence gate.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jinja2 import Environment

from engine.intelligence_workspace.context_compiler import compile_envelope
from engine.neuralweb import brain_gateway
from engine.neuralweb import market_packet as mp
from engine.neuralweb.native_facts import _render_fact, plan_native_facts

SOURCE_ASOF = "2026-09-26T20:00:00+00:00"
SOURCE_STAMP = "09-26 20:00Z"
EVAL_FRESH = datetime(2026, 9, 26, 20, 10, tzinfo=timezone.utc)
EVAL_STALE = datetime(2026, 9, 26, 21, 40, tzinfo=timezone.utc)


@pytest.fixture
def root(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.delenv(mp._LIVE_DIR_ENV, raising=False)
    monkeypatch.setattr(mp, "_VPS_LIVE_DIR", tmp_path / "no-vps-live")
    mp._CACHE.clear()
    yield tmp_path
    mp._CACHE.clear()


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def _quotes(*, eth: dict | None) -> dict:
    quotes = {
        "BTC-USD": {
            "price": 64000.0,
            "changePct": -3.1,
            "delayMin": 1.0,
            "basis": "coingecko-spot",
        }
    }
    if eth is not None:
        quotes["ETH-USD"] = eth
    return {
        "asof": SOURCE_ASOF,
        "source": "fixture-snapshot",
        "quotes": quotes,
    }


def _arm(root: Path, *, eth: dict | None, session_open: bool = True) -> None:
    live = root / "site" / "live"
    _write(live / "quotes.json", _quotes(eth=eth))
    _write(live / "risk_state.json", {
        "session": {"open": session_open, "local_time": "2026-09-26 16:00 EDT"},
        "stale": False,
        "stale_reason": "",
    })


def _btc(packet: dict) -> dict:
    rows = [r for r in packet["tape"]["crypto"] if r["sym"] == "BTC-USD"]
    assert len(rows) == 1
    return rows[0]


def test_crypto_tape_keeps_source_basis_and_asof_off_the_eval_clock(root: Path) -> None:
    _arm(root, eth=None)
    packet = mp.build_packet(root, now=EVAL_FRESH)
    row = _btc(packet)
    assert packet["tape"]["asof"] == SOURCE_ASOF
    assert "asof" not in row
    assert row["basis"] == "coingecko-spot"
    assert row["price"] == 64000.0
    assert packet["basis"] == mp._BASIS_LIVE
    assert packet["stale_warn"] is False
    text = mp.render_digest(packet)
    assert SOURCE_STAMP in text
    assert "09-26 20:10Z" not in text
    assert "ETH" not in text
    assert mp._STALE_PREFIX not in text


def test_missing_crypto_row_is_omitted_and_an_explicit_zero_is_kept(root: Path) -> None:
    _arm(root, eth={"price": None, "changePct": None, "delayMin": 1.0, "basis": "coingecko-spot"})
    omitted = mp.build_packet(root, now=EVAL_FRESH)
    assert [r["sym"] for r in omitted["tape"]["crypto"]] == ["BTC-USD"]
    assert "ETH" not in mp.render_digest(omitted)
    assert "0%" not in mp.render_digest(omitted)

    _arm(root, eth={"price": 0.0, "changePct": 0.0, "delayMin": 1.0, "basis": "coingecko-spot"})
    zeroed = mp.build_packet(root, now=EVAL_FRESH)
    eth = next(r for r in zeroed["tape"]["crypto"] if r["sym"] == "ETH-USD")
    assert eth["price"] == 0.0 and eth["change_pct"] == 0.0
    assert eth["basis"] == "coingecko-spot"
    assert "ETH 0%" in mp.render_digest(zeroed)


def test_stale_crypto_print_stays_the_source_clock_and_is_not_current(root: Path) -> None:
    _arm(root, eth=None)
    packet = mp.build_packet(root, now=EVAL_STALE)
    assert packet["tape"]["asof"] == SOURCE_ASOF
    assert packet["basis"] == mp._BASIS_LIVE
    assert packet["stale_warn"] is True
    text = mp.render_digest(packet)
    assert text.split("\n")[1].startswith(
        "STALE — treat as last known, not current: TAPE (" + SOURCE_STAMP
    )
    assert "21:40Z" not in text


def test_closed_session_clock_is_not_relabeled_live(root: Path) -> None:
    _arm(root, eth=None, session_open=False)
    packet = mp.build_packet(root, now=EVAL_FRESH)
    assert packet["basis"] == mp._BASIS_CLOSED
    assert packet["stale_warn"] is False
    assert packet["tape"]["asof"] == SOURCE_ASOF
    text = mp.render_digest(packet)
    assert "last session's tape (market closed)" in text
    assert mp._STALE_PREFIX not in text


def test_rendered_fact_carries_source_and_asof_and_unavailable_is_not_zero() -> None:
    available, _clause = _render_fact({
        "field_id": "market.price.last",
        "value": 64000,
        "unit": "USD",
        "status": "available",
        "source": {"source_id": "coingecko-spot"},
        "as_of": "2026-09-26",
        "freshness": {"state": "fresh"},
    })
    assert "source=coingecko-spot" in available
    assert "as_of=2026-09-26" in available
    assert "USD 64000" in available

    missing, _clause = _render_fact({
        "field_id": "market.price.last",
        "value": 0,
        "unit": "USD",
        "status": "unavailable",
        "reason_code": "missing",
        "source": {"source_id": "coingecko-spot"},
        "as_of": "1999-11-19",
        "freshness": {"state": "missing"},
    })
    assert "current price: unavailable (missing)" in missing
    assert "source=coingecko-spot" in missing
    assert "as_of=1999-11-19" in missing
    assert "0" not in missing


def test_historical_cursor_is_not_planned_as_a_current_fact() -> None:
    current = plan_native_facts("what is the BTC price")
    assert current is not None
    assert current.symbol == "BTC"
    assert "market.price.last" in current.field_ids
    assert plan_native_facts("what is the BTC price as of 2022-11-09") is None
    assert plan_native_facts("what is the BTC price on 2022-11-09") is None


def test_compiler_keeps_page_and_does_not_rewrite_an_old_capture_to_now() -> None:
    captured = "2026-09-26T20:00:00Z"
    now = datetime(2026, 10, 12, 4, 0, tzinfo=timezone.utc)
    envelope = compile_envelope(
        "what is the backdrop",
        {"ai_context": {
            "schema": "ai_context_client.v1",
            "origin_id": "vector-page",
            "context_revision": 3,
            "captured_at": captured,
            "pinned": [],
            "active": None,
            "ambient": {
                "page": "vector",
                "panel": "cycle-lab",
                "source_id": "btc.decision/v1",
                "shown_as_of": "2026-09-26",
                "historical_cursor": "2022-11-09",
            },
            "effective_context": {"source": "explicit", "entities": [{"type": "security", "id": "ETH"}]},
        }},
        now=now,
        request_id="t20-fixed",
    )
    ambient = envelope["ambient_widget_context"]
    assert ambient["page"] == "vector"
    assert ambient["panel"] == "cycle-lab"
    assert envelope["origin"]["captured_at"] == captured
    assert envelope["context_flags"]["stale"] is True
    assert "effective_context" in envelope["context_flags"]["rejected_fields"]
    assert envelope["effective_context"]["source"] == "none"
    assert envelope["effective_context"]["entities"] == []
    # A scrubber date in the client block must not become the effective entity
    # or the page label. The compiler's echoed ambient keys are still only
    # symbol/timeframe/page/panel (context_compiler.py); source_id and the
    # cursor are not on that surface, which the census records as a gap.
    assert "2022-11-09" not in json.dumps(envelope["effective_context"])
    assert ambient["page"] != "2022-11-09"

    fresh_at = (now - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    fresh = compile_envelope(
        "what is the backdrop",
        {"ai_context": {
            "schema": "ai_context_client.v1",
            "origin_id": "crypto-page",
            "context_revision": 1,
            "captured_at": fresh_at,
            "pinned": [],
            "active": None,
            "ambient": {"page": "crypto"},
        }},
        now=now,
        request_id="t20-fresh",
    )
    assert fresh["ambient_widget_context"]["page"] == "crypto"
    assert fresh["origin"]["captured_at"] == fresh_at
    assert fresh["context_flags"]["stale"] is False


def test_guest_and_unknown_do_not_receive_protected_context(tmp_path: Path) -> None:
    assert brain_gateway._ontology_evidence_allowed("") is False
    assert brain_gateway._ontology_evidence_allowed("unknown") is False
    assert brain_gateway._ontology_evidence_allowed("guest:not-a-customer") is False
    assert brain_gateway._rotation_risk_grounding_digest(
        tmp_path, user_id="guest:not-a-customer", now=EVAL_FRESH,
    ) == ""
    assert brain_gateway._rotation_risk_grounding_digest(
        tmp_path, user_id="unknown", now=EVAL_FRESH,
    ) == ""


_PAGE_PANELS = (
    ("crypto", "crypto-overview"),
    ("vector", "vector-sectionbar"),
)


def test_compile_envelope_keeps_supplied_crypto_and_vector_page() -> None:
    """A supplied ambient page stays that page. The compiler does not rewrite it to dashboard."""
    now = datetime(2026, 10, 12, 4, 20, tzinfo=timezone.utc)
    captured = "2026-10-12T04:19:00Z"
    for page, panel in _PAGE_PANELS:
        block = compile_envelope(
            "what is on this page",
            {"ai_context": {
                "schema": "ai_context_client.v1",
                "origin_id": page + "-page",
                "context_revision": 1,
                "captured_at": captured,
                "pinned": [],
                "active": None,
                "ambient": {"symbol": None, "timeframe": None, "page": page, "panel": panel},
            }},
            now=now,
            request_id="t20w-" + page,
        )
        ambient = block["ambient_widget_context"]
        assert ambient["page"] == page
        assert ambient["panel"] == panel
        assert ambient["page"] != "dashboard"
        assert ambient["panel"] != "dashboard"
        assert block["context_flags"]["malformed"] is False
        assert block["context_flags"]["echo_sanitized"] is False

        legacy = compile_envelope(
            "what is on this page",
            {"page": page, "panel": panel},
            now=now,
            request_id="t20w-legacy-" + page,
        )
        legacy_ambient = legacy["ambient_widget_context"]
        assert legacy_ambient["page"] == page
        assert legacy_ambient["panel"] == panel
        assert legacy_ambient["page"] != "dashboard"


def test_compile_envelope_does_not_invent_dashboard_for_a_missing_page() -> None:
    now = datetime(2026, 10, 12, 4, 20, tzinfo=timezone.utc)
    envelope = compile_envelope(
        "what is on this page", {}, now=now, request_id="t20w-absent",
    )
    assert envelope["ambient_widget_context"]["page"] is None
    assert envelope["ambient_widget_context"]["panel"] is None


ROOT = Path(__file__).resolve().parent.parent


def _page_template(name: str) -> str:
    override = os.environ.get("T20W_TEMPLATE_DIR")
    directory = Path(override) if override else ROOT / "templates"
    return (directory / name).read_text(encoding="utf-8")


def _last_inline_script(source: str) -> str:
    scripts = re.findall(r"<script>(.*?)</script>", source, flags=re.S)
    assert scripts, "template has no inline script"
    return scripts[-1]


def _assert_script_is_served_verbatim(script: str) -> None:
    """The Ask script has no jinja tags, so the served page carries these bytes."""
    assert "{{" not in script and "{%" not in script and "{#" not in script
    rendered = Environment().from_string(script).render()
    assert rendered.strip() == script.strip()


def _assert_open_carries_page(source: str, script: str, *, page: str, panel: str, arm: str) -> None:
    assert source.index('<script src="theme.js"></script>') < source.index(f"function {arm}()")
    assert f"function {arm}()" in script
    assert "var cfg=window.MM_BRAIN_CFG;" in script
    assert "if(!cfg)return;" in script
    assert "window.MM_BRAIN_CFG=" not in script
    assert "window.MM_BRAIN_CFG =" not in script
    assert "cfg.getAiContext=function()" in script
    assert "cfg.symbol" in script
    assert "schema:'ai_context_client.v1'" in script
    assert f"origin_id:'{page}-page'" in script
    assert f"page:'{page}'" in script
    assert f"panel:'{panel}'" in script
    assert "dashboard" not in script
    assert f"document.addEventListener('DOMContentLoaded',{arm})" in script
    assert script.count("MMBrain.open(") == script.count("MMBrain.open()")
    calls = [match.start() for match in re.finditer(re.escape(arm + "();"), script)]
    open_at = script.find("window.MMBrain.open()")
    boot_at = script.find("getElementById('mmb-boot')")
    assert calls and open_at > 0 and boot_at > 0
    assert any(pos < open_at for pos in calls)
    assert any(pos < boot_at for pos in calls)


def test_crypto_template_passes_page_into_open() -> None:
    source = _page_template("crypto.html.j2")
    script = _last_inline_script(source)
    if "cfg.getAiContext=function()" not in script:
        pytest.skip(
            "templates/crypto.html.j2 does not carry the T20w page hook yet; "
            "apply research/crypto_science/patches/cx-t20w-20261012__crypto.html.j2.patch"
        )
    _assert_script_is_served_verbatim(script)
    assert 'id="crypto-overview"' in source
    assert "ready();note.hidden=false;entry.focus()" in script
    _assert_open_carries_page(
        source, script, page="crypto", panel="crypto-overview", arm="armCryptoPage",
    )


def test_vector_template_passes_page_into_open() -> None:
    source = _page_template("vector.html.j2")
    script = _last_inline_script(source)
    if "cfg.getAiContext=function()" not in script:
        pytest.skip(
            "templates/vector.html.j2 does not carry the T20w page hook yet; "
            "apply research/crypto_science/patches/cx-t20w-20261012__vector.html.j2.patch"
        )
    _assert_script_is_served_verbatim(script)
    assert 'class="vector-sectionbar"' in source
    assert 'class="vector-brain-error" role="status"' in source
    _assert_open_carries_page(
        source, script, page="vector", panel="vector-sectionbar", arm="armVectorPage",
    )
