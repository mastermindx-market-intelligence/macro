"""Tests for engine.cash_runway — RED-first per frozen spec constraint 2.

RED: these tests must fail against origin/main bytes of the touched modules
(swap git show origin/main:<path> copies into place — NEVER git stash) and
pass at HEAD.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cash_runway"


def _load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


AAPL = _load(FIXTURE_DIR / "aapl_cash_trimmed.json")
SYNTH = _load(FIXTURE_DIR / "synthetic_burn.json")


class TestExtractCashRunway:
    """RED-first: ImportError / assertion failures at origin/main."""

    def test_import_engine_cash_runway(self):
        """Must be importable as a module."""
        import engine.cash_runway  # noqa: F401

    def test_extract_cash_runway_function_exists(self):
        from engine.cash_runway import extract_cash_runway
        assert callable(extract_cash_runway)

    def test_aapl_reported_status(self):
        """AAPL has all three facts in the most recent FY → status reported."""
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(AAPL, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["status"] == "reported"

    def test_aapl_cash_value_present(self):
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(AAPL, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["cash_usd"] is not None
        assert result["cash_display"] is not None

    def test_aapl_free_cash_flow_computed(self):
        """FCF = operating cash flow - equipment spend."""
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(AAPL, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["free_cash_flow_usd"] is not None
        # AAPL is self-funding (OCF > capex)
        assert result["free_cash_flow_usd"] >= 0

    def test_aapl_self_funding_display(self):
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(AAPL, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["runway_display"] == "self_funding"
        assert result["runway_months"] is None
        assert result["monthly_burn_usd"] is None
        assert result["annual_burn_usd"] is None
        assert result["annual_burn_display"] is None
        assert result["monthly_burn_display"] is None

    def test_synthetic_burn_case(self):
        """Synthetic: OCF=10M, capex=40M → FCF=-30M, cash=50M → ~20 months.

        Round 2: runway_display is the closed enum value ``months`` (not a
        user-facing English phrase); burn amounts are exposed as display
        strings via ``_usd_dollars``.
        """
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(SYNTH, cik="0000099999", as_of=date(2025, 6, 1))
        assert result["status"] == "reported"
        assert result["free_cash_flow_usd"] == -30_000_000
        assert result["monthly_burn_usd"] == 2_500_000
        assert result["annual_burn_usd"] == 30_000_000
        assert result["annual_burn_display"] == "$30.0M"
        assert result["monthly_burn_display"] == "$2.5M"
        assert result["runway_months"] == 20.0
        assert result["runway_display"] == "months"

    def test_synthetic_near_term_cover_with_ladder(self):
        """near_term_cover_pct computed when ladder y1 > 0."""
        from engine.cash_runway import extract_cash_runway
        ladder = {
            "status": "reported",
            "buckets": [
                {"reported": True, "usd": 10_000_000},  # y1
                {"reported": True, "usd": 5_000_000},
            ],
        }
        result = extract_cash_runway(
            SYNTH, cik="0000099999", as_of=date(2025, 6, 1), ladder=ladder
        )
        # cash = 50M, y1 = 10M → 500%
        assert result["near_term_cover_pct"] == 500

    def test_no_filings_status(self):
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(None, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["status"] == "no_filings"

    def test_identity_mismatch_status(self):
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(AAPL, cik="0000999999", as_of=date(2025, 6, 1))
        assert result["status"] == "identity_mismatch"

    def test_no_cash_facts_when_missing_tag(self):
        """Fixture with only cash (no ocf/capex) → no_cash_facts with drop_reasons."""
        partial = {
            "cik": 320193,
            "facts": {
                "us-gaap": {
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2024-09-28", "val": 50_000_000,
                                    "accn": "0000320193-24-000123", "fy": 2024,
                                    "fp": "FY", "form": "10-K", "filed": "2024-11-01",
                                }
                            ]
                        }
                    }
                }
            },
        }
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(partial, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["status"] == "no_cash_facts"
        assert "drop_reasons" in result
        tags_with_drops = {r[0] for r in result["drop_reasons"]}
        assert "ocf" in tags_with_drops
        assert "capex" in tags_with_drops

    def test_schema_is_cash_runway_v1(self):
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(AAPL, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["schema"] == "cash_runway.v1"

    def test_period_has_form_and_end(self):
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(AAPL, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["period"] is not None
        assert result["period"]["form"] in ("10-K", "10-K/A", "20-F", "40-F")
        assert result["period"]["end"] is not None

    def test_stale_flag_when_old(self):
        """A filing with end date > 550 days ago should be flagged stale."""
        old_filing = {
            "cik": 320193,
            "facts": {
                "us-gaap": {
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2020-09-26", "val": 50_000_000,
                                    "accn": "old-accn", "fy": 2020,
                                    "fp": "FY", "form": "10-K", "filed": "2020-11-01",
                                }
                            ]
                        }
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2020-09-26", "val": 10_000_000,
                                    "accn": "old-accn", "fy": 2020,
                                    "fp": "FY", "form": "10-K", "filed": "2020-11-01",
                                }
                            ]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2020-09-26", "val": 5_000_000,
                                    "accn": "old-accn", "fy": 2020,
                                    "fp": "FY", "form": "10-K", "filed": "2020-11-01",
                                }
                            ]
                        }
                    },
                }
            },
        }
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(old_filing, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["status"] == "reported"
        assert result["period"]["stale"] is True

    def test_cash_must_match_period_end(self):
        """Cash fact's end must equal the FY period end — mismatch → no_cash_facts."""
        wrong_end = {
            "cik": 320193,
            "facts": {
                "us-gaap": {
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {
                            "USD": [
                                {
                                    # different end date — not the same period
                                    "end": "2023-09-30", "val": 50_000_000,
                                    "accn": "accn1", "fy": 2024,
                                    "fp": "FY", "form": "10-K", "filed": "2024-11-01",
                                }
                            ]
                        }
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2024-09-28", "val": 10_000_000,
                                    "accn": "accn1", "fy": 2024,
                                    "fp": "FY", "form": "10-K", "filed": "2024-11-01",
                                }
                            ]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2024-09-28", "val": 5_000_000,
                                    "accn": "accn1", "fy": 2024,
                                    "fp": "FY", "form": "10-K", "filed": "2024-11-01",
                                }
                            ]
                        }
                    },
                }
            },
        }
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(wrong_end, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["status"] == "no_cash_facts"

    def test_runway_display_more_than_10_years(self):
        """Cash / monthly_burn > 120 → 'more than 10 years'."""
        big_cash = {
            "cik": 1,
            "facts": {
                "us-gaap": {
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2024-12-31", "val": 1_200_000_000,
                                    "accn": "big-1", "fy": 2024,
                                    "fp": "FY", "form": "10-K", "filed": "2025-01-01",
                                }
                            ]
                        }
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2024-12-31", "val": 10_000_000,
                                    "accn": "big-1", "fy": 2024,
                                    "fp": "FY", "form": "10-K", "filed": "2025-01-01",
                                }
                            ]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [
                                {
                                    "end": "2024-12-31", "val": 100_000_000,
                                    "accn": "big-1", "fy": 2024,
                                    "fp": "FY", "form": "10-K", "filed": "2025-01-01",
                                }
                            ]
                        }
                    },
                }
            },
        }
        # FCF = 10M - 100M = -90M → monthly_burn = 7.5M
        # cash = 1.2B / 7.5M = 160 months → > 10 years
        from engine.cash_runway import extract_cash_runway
        result = extract_cash_runway(big_cash, cik="0000000001", as_of=date(2025, 6, 1))
        assert result["status"] == "reported"
        assert result["runway_display"] == "more_than_10_years"
        assert result["runway_months"] == 160.0
        # M3: the spent-more amount is the annual burn ($90.0M), not cash ($1.2B).
        assert result["annual_burn_usd"] == 90_000_000
        assert result["annual_burn_display"] == "$90.0M"
        assert result["monthly_burn_display"] == "$7.5M"


# A debt-maturity block that opens #debt-maturity so the runway (M2) can
# render inside it. Status is not_applicable's inverse; the body is unused
# by the runway assertions.
_DM_OPEN = {
    "schema": "debt_maturity.v1",
    "status": "not_loaded",
    "cik": "0000320193",
    "buckets": [],
    "total_reported_usd": None,
    "total_display": None,
    "near_share_pct": None,
    "buckets_reported": 0,
    "buckets_total": 6,
    "period": None,
    "as_of": None,
}


def _render_partial(debt_maturity: dict, cash_runway: dict | None = None) -> str:
    from jinja2 import Environment, FileSystemLoader

    from engine import i18n

    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["t"] = i18n.t
    tmpl = env.get_template("_debt_maturity.html.j2")
    return tmpl.render(debt_maturity=debt_maturity, cash_runway=cash_runway)


def _zh_text(html: str) -> str:
    return "".join(re.findall(r'<span class="l-zh">(.*?)</span>', html, re.DOTALL))


def _en_text(html: str) -> str:
    return "".join(re.findall(r'<span class="l-en">(.*?)</span>', html, re.DOTALL))


class TestCashRunwayRender:
    """Three template renders named by the round-2 ruling, plus M2/M3/M5."""

    def test_render_aapl_self_funding_attributed(self):
        from engine.cash_runway import extract_cash_runway

        result = extract_cash_runway(
            AAPL,
            cik="0000320193",
            as_of=date(2025, 6, 1),
            ladder={
                "status": "reported",
                "buckets": [{"reported": True, "usd": 11_128_000_000}],
            },
        )
        html = _render_partial(_DM_OPEN, result)
        en, zh = _en_text(html), _zh_text(html)
        assert "In the year ending 2025-09-27 (10-K) it brought in more cash than it spent, including equipment — no burn to measure." in en
        assert "截至 2025-09-27 的财年（10-K）其现金流入多于支出（包括设备支出），暂无可衡量的消耗。" in zh
        assert "In the year ending 2025-09-27 (10-K) cash on hand covers 323% of the debt coming due in the next 12 months." in en
        assert "截至 2025-09-27 的财年（10-K）现金可覆盖未来12个月内到期债务的 323%。" in zh
        assert "Last year" not in en
        assert "去年" not in zh
        assert "months" not in zh
        assert "most recent annual filing" not in en

    def test_render_synthetic_burn_composed_months(self):
        from engine.cash_runway import extract_cash_runway

        result = extract_cash_runway(SYNTH, cik="0000099999", as_of=date(2025, 6, 1))
        html = _render_partial(_DM_OPEN, result)
        en, zh = _en_text(html), _zh_text(html)
        assert "Cash on hand: $50.0M." in en
        assert "In the year ending 2024-12-31 (10-K) it spent $2.5M more per month than it brought in after buying equipment — at that pace the cash lasts about 20 months." in en
        assert "现金及现金等价物：$50.0M。" in zh
        assert "截至 2024-12-31 的财年（10-K）每月购买设备后的支出超过现金流入约 $2.5M，按此速度现金可支撑约 20 个月。" in zh
        assert "0.0025" not in html
        assert "20.0 months" not in html
        assert "months" not in zh
        assert "Last year" not in en

    def test_render_not_loaded(self):
        html = _render_partial(
            _DM_OPEN,
            {
                "schema": "cash_runway.v1",
                "status": "not_loaded",
                "cik": "0000320193",
                "period": None,
            },
        )
        en, zh = _en_text(html), _zh_text(html)
        assert "Cash runway not loaded yet." in en
        assert "现金跑道尚未加载。" in zh
        assert "This panel is still catching up to the SEC filings for this listing. Check back soon — nothing is being estimated in its place." in en

    def test_runway_sits_inside_section_before_footer(self):
        from engine.cash_runway import extract_cash_runway

        result = extract_cash_runway(SYNTH, cik="0000099999", as_of=date(2025, 6, 1))
        html = _render_partial(_DM_OPEN, result)
        assert 'id="debt-maturity"' in html
        runway = html.index('class="dmw-runway"')
        footer = html.index('class="mod-ft"')
        section_end = html.index("</section>")
        assert runway < footer < section_end

    def test_more_than_10_years_prints_annual_burn_not_cash(self):
        from engine.cash_runway import extract_cash_runway

        big_cash = {
            "cik": 1,
            "facts": {
                "us-gaap": {
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {
                            "USD": [{
                                "end": "2024-12-31", "val": 1_200_000_000,
                                "accn": "big-1", "fy": 2024, "fp": "FY",
                                "form": "10-K", "filed": "2025-01-01",
                            }]
                        }
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [{
                                "end": "2024-12-31", "val": 10_000_000,
                                "accn": "big-1", "fy": 2024, "fp": "FY",
                                "form": "10-K", "filed": "2025-01-01",
                            }]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [{
                                "end": "2024-12-31", "val": 100_000_000,
                                "accn": "big-1", "fy": 2024, "fp": "FY",
                                "form": "10-K", "filed": "2025-01-01",
                            }]
                        }
                    },
                }
            },
        }
        result = extract_cash_runway(big_cash, cik="0000000001", as_of=date(2025, 6, 1))
        html = _render_partial(_DM_OPEN, result)
        en = _en_text(html)
        assert "Cash on hand: $1.2B." in en
        assert "it spent $90.0M more than it brought in after buying equipment — at that pace the cash lasts more than 10 years." in en
        assert "it spent $1.2B more" not in en

    def test_stale_period_uses_ladder_stale_phrase(self):
        from engine.cash_runway import extract_cash_runway

        old_filing = {
            "cik": 320193,
            "facts": {
                "us-gaap": {
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {
                            "USD": [{
                                "end": "2020-09-26", "val": 50_000_000,
                                "accn": "old-accn", "fy": 2020, "fp": "FY",
                                "form": "10-K", "filed": "2020-11-01",
                            }]
                        }
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [{
                                "end": "2020-09-26", "val": 10_000_000,
                                "accn": "old-accn", "fy": 2020, "fp": "FY",
                                "form": "10-K", "filed": "2020-11-01",
                            }]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [{
                                "end": "2020-09-26", "val": 5_000_000,
                                "accn": "old-accn", "fy": 2020, "fp": "FY",
                                "form": "10-K", "filed": "2020-11-01",
                            }]
                        }
                    },
                }
            },
        }
        result = extract_cash_runway(old_filing, cik="0000320193", as_of=date(2025, 6, 1))
        assert result["period"]["stale"] is True
        html = _render_partial(_DM_OPEN, result)
        en, zh = _en_text(html), _zh_text(html)
        assert "In the year ending 2020-09-26 (10-K) it brought in more cash than it spent, including equipment — no burn to measure." in en
        assert "截至 2020-09-26 的财年（10-K）其现金流入多于支出（包括设备支出），暂无可衡量的消耗。" in zh
        assert "most recent annual filing" in en
        assert "最近一期年度文件" in zh


class TestCashRunwayWiring:
    def test_ticker_pages_passes_cash_runway_into_template_context(self):
        src = Path("scripts/build_ticker_pages.py").read_text()
        assert '"cash_runway": (blob or {}).get("cash_runway")' in src

    def test_runway_source_sits_inside_section_before_footer(self):
        src = Path("templates/_debt_maturity.html.j2").read_text()
        runway = src.index('class="dmw-runway"')
        footer = src.index('class="mod-ft"')
        section_end = src.index("</section>")
        assert runway < footer < section_end
        guard = src.index("cash_runway and cash_runway.status != 'not_applicable'")
        assert guard < footer


_RESOLVER_KEYS = {
    "schema", "status", "cik", "cash_usd", "cash_display",
    "ocf_usd", "capex_usd", "free_cash_flow_usd", "monthly_burn_usd",
    "runway_months", "runway_display", "near_term_cover_pct", "period", "as_of",
}


class TestResolveCashRunway:
    """Seven direct unit tests for _resolve_cash_runway (Grok h_7451_rv1 minor 1)."""

    def test_resolve_cash_runway_not_applicable_for_crypto_and_etf(self, monkeypatch):
        """Crypto ticker and ETF sector short-circuit to not_applicable without calling the loader."""
        import scripts.build_stock_library as bsl

        def fake_loader(ticker):
            raise AssertionError("loader must not be called")

        monkeypatch.setattr(bsl, "_dm_load", fake_loader)

        result = bsl._resolve_cash_runway("BTC-USD", "Technology", date(2026, 9, 20), None)
        assert result == {"schema": "cash_runway.v1", "status": "not_applicable"}

        result = bsl._resolve_cash_runway("SPY", "ETF / macro", date(2026, 9, 20), None)
        assert result == {"schema": "cash_runway.v1", "status": "not_applicable"}

    def test_resolve_cash_runway_unresolved_shape(self, monkeypatch):
        """When the loader finds no CIK the status is unresolved with a 14-key shape."""
        import scripts.build_stock_library as bsl

        monkeypatch.setattr(bsl, "_dm_load", lambda t: (None, None, "unresolved"))

        cr_asof = date(2026, 9, 20)
        result = bsl._resolve_cash_runway("AAPL", "Technology", cr_asof, None)

        assert result["status"] == "unresolved"
        assert result["schema"] == "cash_runway.v1"
        assert result["cik"] is None
        assert result["as_of"] == cr_asof.isoformat()
        assert set(result.keys()) == {
            "schema", "status", "cik", "cash_usd", "cash_display",
            "ocf_usd", "capex_usd", "free_cash_flow_usd", "monthly_burn_usd",
            "runway_months", "runway_display", "near_term_cover_pct", "period", "as_of",
        }
        for key in result:
            if key not in ("schema", "status", "as_of"):
                assert result[key] is None, f"{key} should be None"

    def test_resolve_cash_runway_not_loaded_keeps_cik(self, monkeypatch):
        """When the loader resolves a CIK but has no cache the status is not_loaded and CIK is preserved."""
        import scripts.build_stock_library as bsl

        monkeypatch.setattr(bsl, "_dm_load", lambda t: ("0000320193", None, "not_loaded"))

        cr_asof = date(2026, 9, 20)
        result = bsl._resolve_cash_runway("AAPL", "Technology", cr_asof, None)

        assert result["status"] == "not_loaded"
        assert result["schema"] == "cash_runway.v1"
        assert result["cik"] == "0000320193"
        assert result["as_of"] == cr_asof.isoformat()
        assert set(result.keys()) == {
            "schema", "status", "cik", "cash_usd", "cash_display",
            "ocf_usd", "capex_usd", "free_cash_flow_usd", "monthly_burn_usd",
            "runway_months", "runway_display", "near_term_cover_pct", "period", "as_of",
        }

    def test_resolve_cash_runway_confirmed_no_filings_calls_extract_with_none(
        self, monkeypatch
    ):
        """Confirmed no filings passes None as facts to the extract function, preserving CIK."""
        import engine.cash_runway as cr_mod
        import scripts.build_stock_library as bsl

        recorded_args = {}

        sentinel = {"schema": "cash_runway.v1", "status": "sentinel_no_filings"}

        def fake_extract(facts, cik=None, as_of=None, ladder=None):
            recorded_args["facts"] = facts
            recorded_args["cik"] = cik
            recorded_args["as_of"] = as_of
            recorded_args["ladder"] = ladder
            return sentinel

        # Swap the function in the engine.cash_runway module itself so that when
        # _resolve_cash_runway does its local "from engine.cash_runway import
        # extract_cash_runway as _cr_extract", the name resolves to our fake.
        original_extract = cr_mod.extract_cash_runway
        cr_mod.extract_cash_runway = fake_extract
        monkeypatch.setattr(bsl, "_dm_load", lambda t: ("0000320193", None, "confirmed_no_filings"))

        try:
            cr_asof = date(2026, 9, 20)
            result = bsl._resolve_cash_runway("AAPL", "Technology", cr_asof, None)

            assert result is sentinel
            assert recorded_args["facts"] is None
            assert recorded_args["cik"] == "0000320193"
            assert recorded_args["as_of"] == cr_asof
            assert recorded_args["ladder"] is None
        finally:
            cr_mod.extract_cash_runway = original_extract

    def test_resolve_cash_runway_loaded_passes_facts_and_ladder(self, monkeypatch):
        """Loaded state passes the facts dictionary and ladder sentinel to the extract function."""
        import engine.cash_runway as cr_mod
        import scripts.build_stock_library as bsl

        recorded_args = {}
        facts_marker = {"facts": "marker"}
        ladder_sentinel = object()

        sentinel = {"schema": "cash_runway.v1", "status": "loaded_sentinel"}

        def fake_extract(facts, cik=None, as_of=None, ladder=None):
            recorded_args["facts"] = facts
            recorded_args["cik"] = cik
            recorded_args["as_of"] = as_of
            recorded_args["ladder"] = ladder
            return sentinel

        original_extract = cr_mod.extract_cash_runway
        cr_mod.extract_cash_runway = fake_extract
        monkeypatch.setattr(
            bsl, "_dm_load", lambda t: ("0000320193", facts_marker, "loaded")
        )

        try:
            cr_asof = date(2026, 9, 20)
            result = bsl._resolve_cash_runway("AAPL", "Technology", cr_asof, ladder_sentinel)

            assert result["status"] == "loaded_sentinel"
            assert recorded_args["facts"] is facts_marker
            assert recorded_args["cik"] == "0000320193"
            assert recorded_args["as_of"] == cr_asof
            assert recorded_args["ladder"] is ladder_sentinel
        finally:
            cr_mod.extract_cash_runway = original_extract

    def test_resolve_cash_runway_loader_fault_degrades_to_not_loaded_with_warning(
        self, monkeypatch, capsys
    ):
        """A loader RuntimeError degrades to not_loaded with a warning and no CIK."""
        import scripts.build_stock_library as bsl

        monkeypatch.setattr(bsl, "_dm_load", lambda t: (_ for _ in ()).throw(RuntimeError("boom")))

        cr_asof = date(2026, 9, 20)
        result = bsl._resolve_cash_runway("AAPL", "Technology", cr_asof, None)

        assert result["status"] == "not_loaded"
        assert result["schema"] == "cash_runway.v1"
        assert result["cik"] is None
        assert result["as_of"] == cr_asof.isoformat()
        assert set(result.keys()) == _RESOLVER_KEYS
        for key in result:
            if key not in ("schema", "status", "as_of"):
                assert result[key] is None, f"{key} should be None on the fault path"
        out = capsys.readouterr().out
        assert "::warning title=stock-library cash-runway producer fault::" in out
        assert "AAPL" in out

    def test_resolve_cash_runway_import_failure_degrades_to_not_loaded(self, monkeypatch):
        """A None loader (import failure) degrades to not_loaded, never not_applicable.

        A candidate SEC filer must never silently degrade to not_applicable,
        which is reserved for structural non-filers (crypto tickers, ETF/macro
        sectors).  When the loader itself is None the module-level import
        failed; the ticker is still a real filer identity, so the degraded
        state must be not_loaded.
        """
        import scripts.build_stock_library as bsl

        monkeypatch.setattr(bsl, "_dm_load", None)

        result = bsl._resolve_cash_runway("AAPL", "Technology", date(2026, 9, 20), None)

        assert result["status"] == "not_loaded"
        assert result["status"] != "not_applicable"
        assert result["schema"] == "cash_runway.v1"
        assert result["cik"] is None
        assert result["as_of"] == date(2026, 9, 20).isoformat()
        assert set(result.keys()) == _RESOLVER_KEYS
        for key in result:
            if key not in ("schema", "status", "as_of"):
                assert result[key] is None, f"{key} should be None when the loader import failed"

