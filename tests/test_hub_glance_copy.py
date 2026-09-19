"""Signed-in hub glance tier stays truthful, plain, and compact."""

from __future__ import annotations

from pathlib import Path

from scripts import build_vector


def _vm(**over) -> dict:
    vm = {
        "risk_on": True,
        "risk_index": 73,
        "risk_word": "ON",
        "momentum": 0.42,
    }
    vm.update(over)
    return vm


def test_vector_cards_translate_machine_values_into_plain_glance_copy() -> None:
    html = build_vector._g_vectors(
        _vm(), {"label": "Goldilocks", "favored": ["Gold", "Silver"]},
        {"label": "Global reflation", "risk": "risk-on"}, {}, {}, {}, {}, {},
        latest_report=None,
        ipo={
            "present": True,
            "band": "OPEN",
            "verdict": "tracks",
            "next_lockup": "ACME",
            "next_lockup_date": "2026-10-03",
            "lockups_approaching": 3,
        },
    )

    assert "Risk on" in html
    assert "Momentum positive" in html
    assert "Risk ON · 73" not in html
    assert "Mom 0.42" not in html
    assert "Market state, flows & allocation" in html
    assert "class allocation" not in html
    assert "Read the latest research" in html
    assert "Cycle timing" in html and "Cycle clocks" not in html
    assert "Sector rotation" in html and "Rotation desk" not in html
    assert "50 major assets" in html and "50-asset board" not in html
    assert "Bond health" in html and "Health 73" not in html
    assert "Allocation & market shocks" in html and "shock detection" not in html
    assert "偏好：黄金, 白银" in html
    assert "全球再通胀 · 风险偏好" in html
    assert "research desk" not in html
    assert "Next shares unlock: ACME 10-03 · 3 coming soon" in html
    assert "Next un-lock" not in html
    assert "New-issue window & lock-up cliffs" not in html
    for emoji in ("🚀", "🏛️", "💱"):
        assert emoji not in html


def test_vector_card_momentum_copy_handles_down_flat_and_missing() -> None:
    params = ({"momentum": -0.1}, {"momentum": 0}, {"momentum": None})
    expected = ("Momentum negative", "Momentum flat", "Momentum unavailable")
    for over, phrase in zip(params, expected):
        html = build_vector._g_vectors(_vm(**over), {}, {}, {}, {}, {}, {}, {})
        assert phrase in html


def test_hub_hero_describes_a_snapshot_not_the_viewers_clock(monkeypatch) -> None:
    blob = [{"cc": "US", "macro_asof": "2026-09-18"}]
    monkeypatch.setattr(build_vector, "_globe_markets", lambda: blob)
    monkeypatch.setattr(build_vector, "_g_legend", lambda _blob: "")
    monkeypatch.setattr(build_vector, "_standout_tickers", lambda _key: [])
    monkeypatch.setattr(build_vector, "_latest_report_data", lambda: None)
    monkeypatch.setattr(build_vector, "_g_markets", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_g_vectors", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_g_alerts", lambda *_a, **_k: "")
    monkeypatch.setattr(build_vector, "_hub_product_nav_html", lambda: "")
    monkeypatch.setattr(build_vector, "_hub_footer_html", lambda: "")

    html = build_vector._hub_html(_vm(), {}, [])

    assert "Latest market snapshot" in html
    assert "最新市场快照" in html
    assert "Live ·" not in html
    assert "实时 ·" not in html
    assert "hub-clock" not in html
    assert "livepulse" not in html
    assert "background:var(--info)" in html
    assert '@media(max-width:560px){.h .eyebrow{display:none}}' not in html
    assert "setInterval(tick" not in html
    assert "live macro dashboard" not in html.lower()


def test_committed_start_artifact_matches_the_glance_contract() -> None:
    start = Path(__file__).resolve().parents[1] / "site" / "start.html"
    html = start.read_text(encoding="utf-8")
    for required in (
        "Latest market snapshot", "最新市场快照", "Explore",
        "Momentum positive", "Risk on", "Bond health",
        "Read the latest research", "Market state, flows & allocation",
        "偏好：黄金, 白银", "全球再通胀 · 风险偏好",
    ):
        assert required in html
    for banned in (
        "Live · <span class=\"hub-clock\"", "livepulse", "setInterval(tick",
        "Mom 0.39", "Risk ON · 16", "Health 89 · late",
        "Next un-lock", "class allocation", "research desk",
        "Dollar-smile currency board", "Allocation & shock detection",
        "🚀", "🏛️", "💱",
    ):
        assert banned not in html
