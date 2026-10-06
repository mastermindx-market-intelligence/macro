"""Leadership receipt (mi.leadership_receipt.v1) — display tier on theme detail."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from engine.leadership_receipt import _THEME_STATE_MAX_AGE_DAYS, build_receipt
from lib import config

ROOT = config.ROOT
TEMPLATE = ROOT / "templates" / "basket_detail.html.j2"
BUILDER = ROOT / "scripts" / "build_theme_detail.py"
VIEWS = ROOT / "engine" / "company_theme_exposure" / "views.py"

SCHEMA_KEYS = {
    "schema",
    "state",
    "stance_en",
    "stance_zh",
    "reason_en",
    "reason_zh",
    "window_sessions",
    "rel_5d",
    "rel_20d",
    "rel_60d",
    "benchmark",
    "as_of",
    "sample",
    "roster_changed",
    "breadth",
    "leaders",
    "split",
    "theme_state",
    "authority",
    "rows",
}

BANNED = re.compile(
    r"\b(intraday|validated|falsif|refut|signal|probability|forecast)\b",
    re.I,
)


def _base_basket(**perf20) -> dict:
    rel20 = perf20.get("rel_20d", 0.02)
    return {
        "id": "test_basket",
        "created": "2020-01-01",
        "perf": {
            "5d": {"rel": 0.01},
            "20d": {"rel": rel20},
            "60d": {"rel": 0.03},
        },
        "observation": {
            "effective_as_of": "2026-10-02",
            "configured_n": 10,
            "observed_n": 10,
            "coverage": 1.0,
            "status": "complete",
            "basis": "exact_close_at_effective_as_of",
            "aggregate_eligible": True,
            "min_members": 3,
            "min_coverage": 0.6,
        },
        "members": [],
    }


def _theme_intel(as_of: str = "2026-10-02") -> dict:
    return {
        "as_of": as_of,
        "bench_label": "S&P 500",
        "bench_label_zh": "标普500",
    }


def _theme() -> dict:
    return {
        "breadth": {"pct50": 0.5, "pct200": 0.4, "n": 10},
        "leadership": {
            "breadth": "broad",
            "top": [{"ticker": "AAA", "ret_20d": 0.1}],
        },
        "leadership_split": False,
    }


def _theme_state_file(
    site: Path,
    *,
    as_of: str = "2026-10-02",
    basket_id: str = "test_basket",
    stale_legs: list | None = None,
) -> None:
    payload = {
        "schema": "neuralweb.theme_state.v1",
        "as_of": as_of,
        "stale_legs": stale_legs or [],
        "themes": [
            {
                "theme_id": "t1",
                "basket_ids": [basket_id],
                "subsector_rotation": {"rollup_quadrant": "leading"},
            }
        ],
    }
    dest = site / "neuralwebdata" / "theme_state.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload), encoding="utf-8")


class TestS8Matrix:
    def test_rel_20d_none(self, tmp_path: Path):
        b = _base_basket()
        b["perf"]["20d"] = {"rel": None}
        r = build_receipt(b, _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "unavailable"
        assert r["reason_en"] == "price panel incomplete"

    def test_observation_partial(self, tmp_path: Path):
        b = _base_basket()
        b["observation"]["status"] = "partial"
        r = build_receipt(b, _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "unavailable"

    def test_aggregate_ineligible(self, tmp_path: Path):
        b = _base_basket()
        b["observation"]["aggregate_eligible"] = False
        b["observation"]["min_members"] = 5
        r = build_receipt(b, _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "unavailable"
        assert "5" in (r["reason_en"] or "")

    def test_coverage_below_min(self, tmp_path: Path):
        b = _base_basket()
        b["observation"]["coverage"] = 0.5
        b["observation"]["min_coverage"] = 0.6
        r = build_receipt(b, _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "unavailable"
        assert "60%" in (r["reason_en"] or "")

    def test_mixed_dead_band(self, tmp_path: Path):
        r = build_receipt(_base_basket(rel_20d=0.004), _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "mixed"

    def test_leading(self, tmp_path: Path):
        r = build_receipt(_base_basket(rel_20d=0.012), _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "leading"

    def test_lagging(self, tmp_path: Path):
        r = build_receipt(_base_basket(rel_20d=-0.03), _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "lagging"

    def test_china_not_published(self, tmp_path: Path):
        r = build_receipt(_base_basket(), _theme(), _theme_intel(), "china", tmp_path)
        assert r["theme_state"]["status"] == "not_published"

    def test_theme_state_file_missing(self, tmp_path: Path):
        r = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", tmp_path)
        assert r["theme_state"]["status"] == "missing"

    def test_theme_state_stale(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site, as_of="2026-10-01")
        r = build_receipt(
            _base_basket(),
            _theme(),
            _theme_intel(as_of="2026-10-10"),
            "us",
            site,
        )
        assert r["theme_state"]["status"] == "stale"

    def test_theme_state_fresh(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site, as_of="2026-10-08")
        r = build_receipt(
            _base_basket(),
            _theme(),
            _theme_intel(as_of="2026-10-10"),
            "us",
            site,
        )
        assert r["theme_state"]["status"] == "fresh"

    def test_basket_not_in_theme_state(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site, basket_id="other_basket")
        r = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", site)
        assert r["theme_state"]["status"] == "missing"

    def test_malformed_theme_state_json(self, tmp_path: Path):
        site = tmp_path / "site"
        dest = site / "neuralwebdata" / "theme_state.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("{not json", encoding="utf-8")
        r = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", site)
        assert r["theme_state"]["status"] == "missing"
        assert r["state"] == "leading"


def _all_user_strings(receipt: dict) -> list[str]:
    out = [
        receipt.get("stance_en") or "",
        receipt.get("stance_zh") or "",
        receipt.get("reason_en") or "",
        receipt.get("reason_zh") or "",
    ]
    for row in receipt.get("rows") or []:
        out.extend(
            [
                row.get("label_en") or "",
                row.get("label_zh") or "",
                row.get("text_en") or "",
                row.get("text_zh") or "",
            ]
        )
    return [s for s in out if s]


class TestCopyBudgets:
    def test_budgets_and_banned_words(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site)
        r = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", site)
        assert len((r["stance_en"] or "").split()) <= 14
        for row in r["rows"]:
            assert len((row["label_en"] or "").split()) <= 4
            assert len((row["text_en"] or "").split()) <= 40
        for text in _all_user_strings(r):
            if "not a forecast" in text.lower() or "不是预测" in text:
                continue
            assert not BANNED.search(text), text


class TestSchema:
    def test_keys_and_authority(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site)
        r = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", site)
        assert set(r.keys()) == SCHEMA_KEYS
        assert r["schema"] == "mi.leadership_receipt.v1"
        auth = r["authority"]
        assert auth["display_only"] is True
        assert auth["may_rank"] is False
        assert auth["may_size"] is False
        assert auth["may_gate"] is False
        assert auth["may_escalate"] is False


class TestTemplate:
    def test_template_wiring_and_css(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "function leadershipReceiptHtml(" in text
        assert "leadershipReceiptHtml(DETAIL.leadership_receipt)" in text
        assert "receipt row keys: interval benchmark measure sample freshness authority" in text
        assert 'data-key="${esc(r.key)}"' in text
        css_block = text.split(".lrc {", 1)[1].split(".tlabel {", 1)[0]
        hex_colors = re.findall(r"#[0-9a-fA-F]{3,8}", css_block)
        assert not hex_colors


class TestParity:
    def test_theme_state_max_age_days(self):
        assert _THEME_STATE_MAX_AGE_DAYS == 5
        grep = subprocess.run(
            ["grep", "-E", r"THEME_STATE_MAX_AGE_DAYS *= *5", str(VIEWS)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert grep.returncode == 0


class TestBuilderAttach:
    def test_three_s5_lines(self):
        src = BUILDER.read_text(encoding="utf-8")
        assert "from engine import basket_history, basket_score, leadership_receipt" in src
        assert "lr = leadership_receipt.build_receipt(b, th, ti, region, site)" in src
        assert '"leadership_receipt": lr,' in src
