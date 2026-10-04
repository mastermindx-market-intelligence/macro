"""Lane E direct consumer of theme_intelligence.consumer.v1."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/theme_intelligence_consumer_v1.json"
JS_SOURCE = ROOT / "templates/theme_opportunity_context.js"
JS_SITE = ROOT / "site/theme_opportunity_context.js"
CSS_SOURCE = ROOT / "templates/theme_opportunity_context.css"
CSS_SITE = ROOT / "site/theme_opportunity_context.css"


def _node(body: str) -> dict:
    script = (
        "const fs=require('fs');"
        "const api=require('./templates/theme_opportunity_context.js');"
        "const p=JSON.parse(fs.readFileSync('tests/fixtures/theme_intelligence_consumer_v1.json','utf8'));"
        + body
    )
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def test_fixture_is_explicitly_non_publishable() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["_fixture_only"] is True
    assert "Never publish" in payload["_note"]


def test_source_and_site_assets_are_byte_identical() -> None:
    assert JS_SOURCE.read_bytes() == JS_SITE.read_bytes()
    assert CSS_SOURCE.read_bytes() == CSS_SITE.read_bytes()
    js = JS_SOURCE.read_text(encoding="utf-8")
    assert "displayState" not in js
    assert "quality_score" not in js
    assert "confidence_pct" not in js
    assert "lib/theme_opportunity_card.py" not in js


def test_direct_reader_preserves_all_five_owner_dimensions_without_summary_state() -> None:
    out = _node(
        "const m=api.readContext(p,{themeId:'ai_semiconductors',name:'AI Semiconductors',nameZh:'AI半导体'});"
        "console.log(JSON.stringify({valid:m.contractValid,keys:Object.keys(m.dimensions),states:Object.fromEntries(Object.entries(m.dimensions).map(([k,v])=>[k,v.state])),hasSummary:Object.prototype.hasOwnProperty.call(m,'displayState'),name:m.name,nameZh:m.nameZh}));"
    )
    assert out["valid"] is True
    assert out["keys"] == ["leadership", "thesis", "crowding", "entry", "health"]
    assert out["states"] == {
        "leadership": "OBSERVED",
        "thesis": "INVALIDATED",
        "crowding": "NOT_DETECTED",
        "entry": "UNAVAILABLE",
        "health": "STALE",
    }
    assert out["hasSummary"] is False
    assert out["name"] == "AI Semiconductors"
    assert out["nameZh"] == "AI半导体"


def test_basket_crosswalk_and_canonical_routes_use_existing_identity() -> None:
    out = _node(
        "const m=api.readContext(p,{basketId:'power_grid'});"
        "console.log(JSON.stringify({theme:m.themeId,basket:m.basketId,routes:api.routesForContext(m)}));"
    )
    assert out == {
        "theme": "grid_electrification",
        "basket": "power_grid",
        "routes": {
            "tracker": "state_of_themes.html#theme-grid_electrification",
            "foresight": "foresight.html#theme-grid_electrification",
            "radar": "radar.html#theme-grid_electrification",
            "sector": "sector_central.html#theme-power_grid",
        },
    }


def test_unsafe_authority_fails_closed_instead_of_rendering_owner_state() -> None:
    out = _node(
        "const q=JSON.parse(JSON.stringify(p));"
        "q.theme_context.memory_storage.authority.may_rank=true;"
        "const m=api.readContext(q,{themeId:'memory_storage'});"
        "console.log(JSON.stringify({valid:m.contractValid,reason:m.contractReason,states:Object.fromEntries(Object.entries(m.dimensions).map(([k,v])=>[k,v.state]))}));"
    )
    assert out["valid"] is False
    assert out["reason"] == "CONTRACT_AUTHORITY_OR_IDENTITY_INVALID"
    assert set(out["states"].values()) == {"UNAVAILABLE"}


def test_missing_contract_and_unknown_owner_fields_never_become_quiet_or_zero() -> None:
    out = _node(
        "const partial=api.readContext(p,{themeId:'copper_steel_electrify'});"
        "const legacy=JSON.parse(JSON.stringify(p));delete legacy.consumer_contract_schema;delete legacy.theme_context;"
        "const missing=api.readContext(legacy,{themeId:'ai_semiconductors'});"
        "console.log(JSON.stringify({partial:api.renderHtml(partial,'tracker'),missing:api.renderHtml(missing,'tracker')}));"
    )
    for html in out.values():
        assert "Unavailable" in html
        assert "Quiet" not in html
        assert ">0<" not in html
        assert "Score" not in html
        assert "Confidence" not in html


def test_rendered_visibility_is_bilingual_and_has_no_trade_authority() -> None:
    out = _node(
        "const m=api.readContext(p,{themeId:'memory_storage'});"
        "console.log(JSON.stringify({html:api.renderHtml(m,'foresight')}));"
    )["html"]
    assert "Leadership" in out and "领导力" in out
    assert "Qualified setup" in out and "合格结构" in out
    assert 'aria-current="page"' in out
    lower = out.lower()
    assert "may_trade" not in lower
    assert "buyable" not in lower
    assert "confidence" not in lower
    assert "member entries still require" in lower


def test_rejected_python_card_plane_is_absent() -> None:
    assert not (ROOT / "lib/theme_opportunity_card.py").exists()
    assert not (ROOT / "templates/_theme_opportunity_card.html.j2").exists()
    assert not (ROOT / "site/theme_opportunity_card.js").exists()
