"""Schema child for MO-PAID-006: rights-gated country-dossier plane (ruling D18).

The dossier plane ships a small head/top-press set next to `policy` and `events`
on the international-macro country view. Items must come from
VERIFIED_PUBLIC_REUSE wires only (engine.europe_news_intel for EZ/UK;
engine.uk_policy_brain for the UK stance). Leadership is a printed null —
storing release prose or fabricating a policy decision is forbidden by the
owner's data contract (docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md :70-71, :86-88).
JP / KR / IN are state `no_coverage` by design.

These tests pin:
  T1: EZ view has dossier.schema + items whose rights_state is
      VERIFIED_PUBLIC_REUSE.
  T2: JP / KR / IN views are state `no_coverage` with items=[] and stance=None.
  T3: validate_view REJECTS each violation with a distinct message — one
      assertion per rule (wrong schema id, bad state, UNVERIFIED item,
      empty rights_basis, prose key, covered-with-empty-items, authoritative
      stance, wrong leadership literal).
  T4: A view without a `dossier` key still passes (backward compatible).
  T5: A source whose read model is missing or unreadable degrades to
      `source_outage`, never raises.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import international_macro_dashboard as imd
from engine.international_macro_dashboard import (
    DOSSIER_LEADERSHIP_NULL,
    DOSSIER_SCHEMA,
    REGIONS,
    build_country_view,
    validate_dossier,
    validate_view,
)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _record(cc: str) -> dict:
    spec = REGIONS[cc]
    return {
        "cc": cc,
        "name": {
            "JP": "Japan",
            "KR": "South Korea",
            "EZ": "Euro Area",
            "GB": "United Kingdom",
            "IN": "India",
        }[cc],
        "name_zh": spec.scope_zh[:2],
        "flag": "🌐",
        "date": "2026-10-02",
        "quad": "Q2",
        "quad_name": "Reflation",
        "growth_score": 0.4,
        "inflation_score": 0.25,
        "confidence": 0.55,
        "liquidity": "neutral",
        "recession_score": 20.0,
        "recession_band": "low",
        "data_limited": False,
        "macro": {
            "cpi_yoy": 2.4,
            "gdp_yoy": 1.8,
            "unemployment": 4.1,
            "yield_10y": 3.2,
            "policy_rate": 2.5,
            "curve": 0.7,
            "fx": 100.25,
            "fx_strength_3m": -1.2,
            "drawdown": -5.0,
            "realvol": 18.0,
        },
        "macro_asof": {
            "cpi_yoy": "2026-06",
            "gdp": "2026-04",
            "unemployment": "2026-06",
            "yield_10y": "2026-07",
        },
        "equity": {"drawdown_risk": 32.0},
        "risk_radar": {
            "state": "caution",
            "top_score": 62,
            "dominant_label_en": "Rate shock",
            "dominant_label_zh": "利率冲击",
            "drawdown_prob": {
                "h21": 0.21,
                "measure": ">=5% pullback within 21 business days",
            },
            "scares": [],
        },
    }


_TODAY = datetime.date(2026, 10, 2)


def _view(cc: str) -> dict:
    view = build_country_view(_record(cc), today=_TODAY)
    validate_view(view)
    return view


# --------------------------------------------------------------------------- #
# T1 — EZ view carries the dossier plane with VERIFIED_PUBLIC_REUSE items
# --------------------------------------------------------------------------- #
def test_t1_ez_view_has_dossier_with_verified_public_reuse_items() -> None:
    view = _view("EZ")
    dossier = view["dossier"]
    assert dossier["schema"] == DOSSIER_SCHEMA
    assert dossier["state"] == "covered"
    assert dossier["items"], "EZ view expected at least one ec_presscorner item"
    for item in dossier["items"]:
        assert item["rights_state"] == "VERIFIED_PUBLIC_REUSE", item
        assert item["source_key"] == "ec_presscorner"
        assert item["jurisdiction"] == "EU"
        assert item["publisher"], item
        assert item["url"].startswith(("https://", "http://")), item
        assert item["title"], item
        assert item["published"], item
        assert item["known_at"], item
        assert item["rights_basis"], item


# --------------------------------------------------------------------------- #
# T2 — JP / KR / IN views are no_coverage, stance None
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cc", ["JP", "KR", "IN"])
def test_t2_no_coverage_countries_carry_empty_dossier_and_none_stance(cc: str) -> None:
    view = _view(cc)
    dossier = view["dossier"]
    assert dossier["schema"] == DOSSIER_SCHEMA
    assert dossier["state"] == "no_coverage", dossier
    assert dossier["items"] == []
    assert dossier["stance"] is None
    assert dossier["leadership"] == DOSSIER_LEADERSHIP_NULL


# --------------------------------------------------------------------------- #
# T3 — validate_dossier rejects each violation separately
# --------------------------------------------------------------------------- #
def _ok_dossier() -> dict:
    return {
        "schema": DOSSIER_SCHEMA,
        "state": "covered",
        "items": [
            {
                "publisher": "European Commission",
                "source_key": "ec_presscorner",
                "jurisdiction": "EU",
                "title": "Statement by President von der Leyen",
                "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1",
                "published": "2026-09-30T10:00:00+00:00",
                "known_at": "2026-09-30T10:01:30+00:00",
                "rights_basis": "CC BY 4.0",
                "rights_state": "VERIFIED_PUBLIC_REUSE",
            }
        ],
        "stance": None,
        "leadership": DOSSIER_LEADERSHIP_NULL,
    }


def test_t3_wrong_schema_id_is_rejected() -> None:
    d = _ok_dossier()
    d["schema"] = "intl_country_dossier.v0"
    with pytest.raises(ValueError, match="schema"):
        validate_dossier(d)


def test_t3_bad_state_is_rejected() -> None:
    d = _ok_dossier()
    d["state"] = "covered_with_audio"
    with pytest.raises(ValueError, match="state"):
        validate_dossier(d)


def test_t3_unverified_item_is_rejected() -> None:
    d = _ok_dossier()
    d["items"][0]["rights_state"] = "UNVERIFIED_EXCLUDED"
    with pytest.raises(ValueError, match="rights_state"):
        validate_dossier(d)


def test_t3_empty_rights_basis_is_rejected() -> None:
    d = _ok_dossier()
    d["items"][0]["rights_basis"] = "   "
    with pytest.raises(ValueError, match="rights_basis"):
        validate_dossier(d)


def test_t3_prose_key_is_rejected() -> None:
    d = _ok_dossier()
    d["items"][0]["body"] = "an invented summary the desk never stored"
    with pytest.raises(ValueError, match="prose"):
        validate_dossier(d)


def test_t3_covered_with_empty_items_is_rejected() -> None:
    d = _ok_dossier()
    d["state"] = "covered"
    d["items"] = []
    with pytest.raises(ValueError, match="non-empty"):
        validate_dossier(d)


def test_t3_authoritative_stance_is_rejected() -> None:
    d = _ok_dossier()
    d["stance"] = {
        "label": "supportive",
        "provider_label": "assistant",
        "authoritative": True,
    }
    with pytest.raises(ValueError, match="authoritative"):
        validate_dossier(d)


def test_t3_wrong_leadership_literal_is_rejected() -> None:
    d = _ok_dossier()
    d["leadership"] = "Mr. Akazawa, BoJ Governor"
    with pytest.raises(ValueError, match="leadership"):
        validate_dossier(d)


# --------------------------------------------------------------------------- #
# T4 — view without a dossier key still passes validate_view
# --------------------------------------------------------------------------- #
def test_t4_view_without_dossier_key_still_passes() -> None:
    view = _view("EZ")
    view.pop("dossier")
    # Should NOT raise.
    validate_view(view)
    assert "dossier" not in view


# --------------------------------------------------------------------------- #
# T5 — missing / unreadable read model → source_outage, not raise
# --------------------------------------------------------------------------- #
def test_t5_missing_read_model_degrades_to_source_outage(monkeypatch) -> None:
    """The europe_news_intel read accessor raises; _build_dossier must catch
    and return a typed source_outage instead of bubbling up."""

    def _boom(_asof):  # mirrors europe_news_intel.read_events signature
        raise FileNotFoundError("events.parquet missing")

    # Stub inside the europe_news_intel module so the dossier read raises.
    from engine import europe_news_intel

    monkeypatch.setattr(europe_news_intel, "read_events", _boom)
    # Force the GB (UK) dossier so the ec_presscorner / boe_news read paths run.
    view = build_country_view(_record("GB"), today=_TODAY)
    # Must not raise here, either:
    validate_view(view)
    assert view["dossier"]["schema"] == DOSSIER_SCHEMA
    assert view["dossier"]["state"] == "source_outage", view["dossier"]
    assert view["dossier"]["items"] == []
    assert view["dossier"]["stance"] is None
    assert view["dossier"]["leadership"] == DOSSIER_LEADERSHIP_NULL


def test_t5_no_coverage_with_europe_news_intel_unavailable(monkeypatch) -> None:
    """JP has no rights-cleared wires at all — losing the europe_news_intel
    module entirely must NOT break JP / KR / IN (they are state no_coverage
    by design)."""
    import sys as _sys

    real_modules = {
        name: _sys.modules[name]
        for name in list(_sys.modules)
        if name.startswith("engine.europe_news_intel")
    }
    # Drop europe_news_intel from sys.modules so the import inside the helper
    # raises — except we also need to keep engine itself importable for the
    # international_macro_dashboard module.
    for name in list(real_modules):
        _sys.modules.pop(name, None)

    try:
        for cc in ("JP", "KR", "IN"):
            view = build_country_view(_record(cc), today=_TODAY)
            validate_view(view)
            d = view["dossier"]
            assert d["state"] == "no_coverage", (cc, d)
            assert d["items"] == []
            assert d["stance"] is None
            assert d["leadership"] == DOSSIER_LEADERSHIP_NULL
    finally:
        # Restore sys.modules — these tests must not pollute later ones.
        for name, mod in real_modules.items():
            _sys.modules[name] = mod


def test_uk_stance_reads_the_published_artifact_as_data(tmp_path) -> None:
    """The dossier's UK stance is a DATA contract over the desk's published
    artifact (site/uk_policy.json) — never a module import of the LLM desk."""
    site = tmp_path / "site"
    site.mkdir()
    art = site / "uk_policy.json"
    art.write_text(json.dumps({"stance": "restrictive", "provider_label": "anthropic:x"}))
    assert imd._uk_stance(root=tmp_path) == {
        "label": "restrictive",
        "provider_label": "anthropic:x",
        "authoritative": False,
    }
    # A label outside the display vocabulary degrades to None, never to a wrong label.
    art.write_text(json.dumps({"stance": "bullish", "provider_label": "x"}))
    assert imd._uk_stance(root=tmp_path) is None
    # Malformed / missing artifact -> None (degrade, never raise).
    art.write_text("[]")
    assert imd._uk_stance(root=tmp_path) is None
    art.unlink()
    assert imd._uk_stance(root=tmp_path) is None


def test_dossier_module_never_imports_the_uk_desk() -> None:
    """Local pin of the desk's single-importer fence
    (tests/test_uk_policy_brain.py::test_no_scoring_path_imports_this_desk):
    the dossier reads the artifact as DATA. Measured red on #8276 ci-pack-5
    (2026-10-02) when two lazy imports slipped in; this pin also closes the
    `from engine.uk_policy_brain import ...` form the pack fence does not match."""
    import re

    src = (ROOT / "engine" / "international_macro_dashboard.py").read_text()
    assert not re.search(
        r"^\s*(from engine import uk_policy_brain|import engine\.uk_policy_brain"
        r"|from engine\.uk_policy_brain import)",
        src,
        re.M,
    )
    assert imd._UK_STANCES_FROZEN == frozenset({"supportive", "restrictive", "mixed", "routine"})
