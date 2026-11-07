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
    r"\b(intraday|validated|falsif\w*|refut\w*|signals?|probabilit\w*|forecast\w*)",
    re.I,
)

ROW_KEYS = ["interval", "benchmark", "measure", "sample", "freshness", "authority"]


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


def _assert_no_banned(text: str) -> None:
    if "not a forecast" in text.lower() or "不是预测" in text:
        return
    assert not BANNED.search(text), text


def _receipts_for_budget_matrix(tmp_path: Path) -> list[dict]:
    site = tmp_path / "site"
    out: list[dict] = []
    out.append(build_receipt(_base_basket(rel_20d=0.012), _theme(), _theme_intel(), "us", site))
    out.append(build_receipt(_base_basket(rel_20d=-0.03), _theme(), _theme_intel(), "us", site))
    out.append(build_receipt(_base_basket(rel_20d=0.004), _theme(), _theme_intel(), "us", site))
    b = _base_basket()
    b["perf"]["20d"] = {"rel": None}
    out.append(build_receipt(b, _theme(), _theme_intel(), "us", site))
    b = _base_basket()
    b["observation"]["status"] = "partial"
    out.append(build_receipt(b, _theme(), _theme_intel(), "us", site))
    b = _base_basket()
    b["observation"]["aggregate_eligible"] = False
    out.append(build_receipt(b, _theme(), _theme_intel(), "us", site))
    b = _base_basket()
    b["observation"]["coverage"] = 0.5
    b["observation"]["min_coverage"] = 0.6
    out.append(build_receipt(b, _theme(), _theme_intel(), "us", site))
    _theme_state_file(site, as_of="2026-10-08")
    out.append(
        build_receipt(
            _base_basket(),
            _theme(),
            _theme_intel(as_of="2026-10-10"),
            "us",
            site,
        )
    )
    _theme_state_file(site, as_of="2026-10-01")
    out.append(
        build_receipt(
            _base_basket(),
            _theme(),
            _theme_intel(as_of="2026-10-10"),
            "us",
            site,
        )
    )
    out.append(build_receipt(_base_basket(), _theme(), _theme_intel(), "us", site))
    out.append(build_receipt(_base_basket(), _theme(), _theme_intel(), "china", site))
    return out


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
    def test_banned_regex_positive_control(self):
        assert BANNED.search("falsified")
        assert BANNED.search("signals")

    def test_budgets_and_banned_words(self, tmp_path: Path):
        for r in _receipts_for_budget_matrix(tmp_path):
            assert len((r["stance_en"] or "").split()) <= 14
            for row in r["rows"]:
                assert len((row["label_en"] or "").split()) <= 4
                assert len((row["text_en"] or "").split()) <= 40
            for text in _all_user_strings(r):
                _assert_no_banned(text)


class TestSixRowContract:
    def test_row_keys_available_and_unavailable(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site)
        r_ok = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", site)
        assert [row["key"] for row in r_ok["rows"]] == ROW_KEYS
        b = _base_basket()
        b["perf"]["20d"] = {"rel": None}
        r_bad = build_receipt(b, _theme(), _theme_intel(), "us", site)
        assert [row["key"] for row in r_bad["rows"]] == ROW_KEYS

    def test_receipt_error_six_rows(self):
        r = build_receipt({"perf": "x"}, {}, {}, "us", None)
        assert r["state"] == "unavailable"
        assert r["reason_en"] == "receipt_error"
        assert [row["key"] for row in r["rows"]] == ROW_KEYS


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
        grep = subprocess.run(
            [
                "grep",
                "-nE",
                r"^ *[^{]*\.lrc[^{]*\{[^}]*(--ink-up|--ink-down|var\(--up\)|var\(--down\))",
                str(TEMPLATE),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [ln.split(":", 1)[1] for ln in grep.stdout.strip().splitlines()]
        assert lines == [
            "  .lrc-figure.up { color:var(--ink-up, var(--up)); }",
            "  .lrc-figure.down { color:var(--ink-down, var(--down)); }",
        ]

    def test_ts_chip_invalid_label_en_zh(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "const tsChip={" in text
        assert "}[tsStat]" in text
        block = text.split("const tsChip={", 1)[1].split("}[tsStat]", 1)[0]
        assert "invalid:L('Theme state dated after this read','主题状态日期晚于本次判读')" in block
        assert block.count("Theme state dated after this read") == 1
        assert block.count("主题状态日期晚于本次判读") == 1
        assert all(
            f"{key}:L(" in block
            for key in ("fresh", "stale", "missing", "not_published", "invalid")
        )
        assert "const tsChipCls=tsStat==='fresh'?'state-fresh':'state-stale';" in text


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


# ---------------------------------------------------------------------------
# P12.T54.S1 — truthful construction copy (HK) + no monthly-rebalance claim
# ---------------------------------------------------------------------------


class TestTruthfulConstruction:
    """The HK page inherited the membership file's construction line ("rebalanced
    monthly"), which does not describe the series: engine.baskets._ew_level compounds
    the DAILY arithmetic mean of the members active on each date."""

    def test_hk_wrapper_construction_is_truthful_and_core_is_untouched(self, monkeypatch):
        import copy

        import pandas as pd

        from engine import baskets_hk as bkhk
        from engine import baskets_region as reg

        idx = pd.date_range("2025-01-02", periods=40, freq="B")
        closes = pd.DataFrame(
            {
                "AAA": [100.0 + i for i in range(40)],
                "BBB": [200.0 + 2 * i for i in range(40)],
                "CCC": [50.0 + 3 * i for i in range(40)],
            },
            index=idx,
        )
        bench = pd.DataFrame({"close": [400.0 * (1.0006 ** i) for i in range(40)]}, index=idx)
        mem = {
            "benchmark": "_HSI",
            "benchmark_label": "HSI",
            "benchmark_label_zh": "恒生指数",
            "construction": "Equal-weight baskets, rebalanced monthly, measured against the Hang Seng Index.",
            "history_note": "h",
            "note": "n",
            "baskets": {
                "t": {
                    "name": "T", "name_zh": "T", "category": "C", "category_zh": "类",
                    "created": "2025-01-02",
                    "members": [
                        {"ticker": "AAA", "added": "2025-01-02", "name": "Aaa"},
                        {"ticker": "BBB", "added": "2025-01-02", "name": "Bbb"},
                        {"ticker": "CCC", "added": "2025-01-02", "name": "Ccc"},
                    ],
                }
            },
        }
        mem_before = copy.deepcopy(mem)

        monkeypatch.setattr(bkhk, "_closes", lambda: closes)
        monkeypatch.setattr(bkhk, "_membership", lambda: mem)
        monkeypatch.setattr(bkhk.store, "read", lambda g, n: bench if n == "_HSI" else None)

        out = bkhk.compute_hk_baskets()
        assert out is not None
        assert out["construction"] == (
            "Daily arithmetic mean of available active-member returns, compounded; "
            "membership follows the supplied added/removed dates."
        )
        assert "monthly" not in out["construction"].lower()

        # the shared core still reports the membership file's own wording
        generic = reg.compute_region_baskets(closes, mem, bench, lambda s: None, name_key="name")
        assert generic["construction"] == mem["construction"]

        # construction is the ONLY difference between the wrapper output and the core output
        assert {k: v for k, v in out.items() if k != "construction"} == \
               {k: v for k, v in generic.items() if k != "construction"}

        # the membership dict was not mutated
        assert mem == mem_before

    def test_hk_wrapper_still_returns_none_when_the_core_degrades(self, monkeypatch):
        from engine import baskets_hk as bkhk

        mem = {
            "benchmark": "_HSI",
            "baskets": {
                "t": {
                    "name": "T", "category": "C", "created": "2025-01-02",
                    "members": [
                        {"ticker": "AAA", "added": "2025-01-02"},
                        {"ticker": "BBB", "added": "2025-01-02"},
                        {"ticker": "CCC", "added": "2025-01-02"},
                    ],
                }
            },
        }
        monkeypatch.setattr(bkhk, "_membership", lambda: mem)
        monkeypatch.setattr(bkhk, "_closes", lambda: None)
        monkeypatch.setattr(bkhk.store, "read", lambda g, n: None)
        assert bkhk.compute_hk_baskets() is None

    def test_ew_level_compounds_a_daily_mean_not_fixed_weights(self):
        import pandas as pd

        from engine.baskets import _ew_level

        idx = pd.DatetimeIndex(["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"])
        closes = pd.DataFrame(
            {
                "A": [100.0, 100.0, 200.0, 200.0],   # daily returns 0, 1, 0
                "B": [100.0, 100.0, 100.0, 200.0],   # daily returns 0, 0, 1
                "C": [100.0, 100.0, 100.0, 100.0],   # daily returns 0, 0, 0
            },
            index=idx,
        )
        members = [
            {"ticker": "A", "added": "2026-01-02"},
            {"ticker": "B", "added": "2026-01-02"},
            {"ticker": "C", "added": "2026-01-02"},
        ]
        rets = closes.pct_change(fill_method=None)
        lvl = _ew_level(rets, members, idx)
        window = lvl.loc["2026-01-05":"2026-01-07"]
        assert abs(float(window.iloc[0]) - 1.0) < 1e-12
        assert abs(float(window.iloc[1]) - 4 / 3) < 1e-12
        assert abs(float(window.iloc[2]) - 16 / 9) < 1e-12

        # a fixed-equal-weight series (each name's own growth averaged, no daily re-weighting)
        # would read 5/3 at the end of this window; the daily-mean construction reads 16/9
        fixed = (closes / closes.iloc[0]).mean(axis=1)
        assert abs(float(fixed.loc["2026-01-07"]) - 5 / 3) < 1e-12
        assert abs(float(window.iloc[2]) - float(fixed.loc["2026-01-07"])) > 1e-6


class TestReceiptBenchmarkRow:
    """The benchmark row claimed a monthly rebalance. The row is shared by every region and
    the claim never described the series; it now states the weighting only."""

    @staticmethod
    def _bench_row(receipt: dict) -> dict:
        return next(r for r in receipt["rows"] if r["key"] == "benchmark")

    def test_ordinary_and_unavailable_rows_state_weighting_only(self, tmp_path: Path):
        ordinary = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", tmp_path)
        b = _base_basket()
        b["perf"]["20d"] = {"rel": None}
        unavailable = build_receipt(b, _theme(), _theme_intel(), "us", tmp_path)
        for rec in (ordinary, unavailable):
            row = self._bench_row(rec)
            assert "monthly" not in row["text_en"].lower()
            assert "按月" not in row["text_zh"]
            assert row["text_en"] == (
                "S&P 500, cap-weighted. The basket uses equal weighting, "
                "so part of any gap is weighting, not stock selection."
            )
            assert row["text_zh"] == (
                "标普500，市值加权。篮子采用等权，"
                "因此差距有一部分来自权重而非选股。"
            )
            assert [r["key"] for r in rec["rows"]] == ROW_KEYS


    def test_emergency_literal_fallback_has_no_monthly_claim(self, monkeypatch):
        import engine.leadership_receipt as lr

        def _boom(**_kw):
            raise RuntimeError("boom")

        monkeypatch.setattr(lr, "_build_rows", _boom)
        rec = lr.build_receipt({"perf": "x"}, {}, _theme_intel(), "us", None)
        assert rec["state"] == "unavailable"
        assert rec["reason_en"] == "receipt_error"
        row = self._bench_row(rec)
        assert row["text_en"] == (
            "S&P 500, cap-weighted. The basket uses equal weighting, "
            "so part of any gap is weighting, not stock selection."
        )
        assert row["text_zh"] == (
            "标普500，市值加权。篮子采用等权，"
            "因此差距有一部分来自权重而非选股。"
        )
        assert "monthly" not in row["text_en"].lower()
        assert "按月" not in row["text_zh"]
        assert [r["key"] for r in rec["rows"]] == ROW_KEYS


# P12.T54.S2: both exception paths retain only explicitly supplied benchmark identity.
@pytest.mark.parametrize("rows_also_fail", [False, True])
@pytest.mark.parametrize("context,expected", [
    ({"bench_label": " Hang Seng ", "bench_label_zh": " 恒生指数 "}, ("Hang Seng", "恒生指数")),
    ({"bench_label": "S&P 500", "bench_label_zh": "标普500"}, ("S&P 500", "标普500")),
    ({"bench_label": "HSI"}, ("HSI", "HSI")),
    ({"bench_label_zh": "恒生指数"}, ("恒生指数", "恒生指数")),
    ({}, None),
    ({"bench_label": "  ", "bench_label_zh": 42}, None),
    ({"bench_label": {"label": "wrong"}, "bench_label_zh": []}, None),
    (None, None),
    ([], None),
])
def test_s2_error_fallback_preserves_declared_benchmark_only(monkeypatch, rows_also_fail, context, expected):
    import engine.leadership_receipt as lr

    def fail(*_args, **_kwargs):
        raise RuntimeError("synthetic internal failure")

    monkeypatch.setattr(lr, "_build_receipt_core", fail)
    if rows_also_fail:
        monkeypatch.setattr(lr, "_build_rows", fail)
    rec = lr.build_receipt(_base_basket(), _theme(), context, "hk", None)
    assert rec["state"] == "unavailable" and rec["reason_en"] == "receipt_error"
    assert rec["as_of"] == "—" and rec["theme_state"]["status"] == "missing"
    assert rec["authority"]["display_only"] is True
    assert all(rec["authority"][key] is False for key in ["may_rank", "may_size", "may_gate", "may_escalate"])
    row = next(row for row in rec["rows"] if row["key"] == "benchmark")
    assert [row["key"] for row in rec["rows"]] == ROW_KEYS
    if expected:
        assert rec["benchmark"] == {"label": expected[0], "label_zh": expected[1]}
        assert expected[0] in row["text_en"] and expected[1] in row["text_zh"]
        if expected[0] != "S&P 500":
            assert "S&P" not in row["text_en"] and "标普" not in row["text_zh"]
    else:
        assert rec["benchmark"] == {"label": "Not published", "label_zh": "未发布"}
        assert "not published" in row["text_en"].lower() and "未发布" in row["text_zh"]
        assert "cap-weighted" not in row["text_en"] and "市值加权" not in row["text_zh"]
        assert "S&P" not in row["text_en"] and "wrong" not in row["text_en"]
