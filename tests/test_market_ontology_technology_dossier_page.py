"""Company-first fragment for a technology_economic_change dossier dict.

The dossier is built in the test. Nothing here calls the composer, a quote
path, or a network. Identifiers are synthetic.
"""
from __future__ import annotations

import inspect
import json
import re
from collections.abc import Mapping
from pathlib import Path

from engine.market_ontology.technology_dossier_page import (
    render_technology_dossier_page,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "templates" / "_technology_economic_change_page.html.j2"

_FALSE_AUTHORITY = {
    "rank": False,
    "gate": False,
    "size": False,
    "veto": False,
    "originate": False,
    "open_entry": False,
}
_TICKER_TOKEN = re.compile(
    r"(?<![A-Za-z0-9])[A-Z0-9][A-Z0-9.\-]{0,11}(?![A-Za-z0-9])"
)
_THEME_FIRST = "technology/economic-change/workload-theme/index.html"
_COMPANY_FIRST = "technology/economic-change/workload-theme/acme.html"
_UNBOUND_COMPANY_FIRST = "technology/economic-change/workload-theme/synth-unbound.html"


def _dossier(
    *,
    display_ticker: str | None,
    binding_state: str,
    company_first: str,
    business: Mapping[str, object],
    enrichment_reason: str,
) -> dict[str, object]:
    return {
        "navigation": {
            "company_first": company_first,
            "theme_first": _THEME_FIRST,
        },
        "authority": dict(_FALSE_AUTHORITY),
        "classification": {"issuer_pure_play_claimed": False},
        "identity": {
            "entities": [
                {
                    "entity_id": "co:us:synth-entity",
                    "binding_state": binding_state,
                    "display_ticker": display_ticker,
                }
            ],
            "views": {
                "security_enrichment_view": {
                    "refused": True,
                    "reason_code": enrichment_reason,
                    "explanation": "synthetic sealed refusal",
                }
            },
        },
        "business": dict(business),
    }


def _refusal_business() -> dict[str, object]:
    return {
        "refused": True,
        "reason_code": "shared_contract_unavailable",
        "explanation": "synthetic sealed refusal",
    }


def _render(dossier: Mapping[str, object]) -> str:
    return render_technology_dossier_page(dossier, TEMPLATE)


def _flag_text(html: str, flag: str) -> str:
    match = re.search(
        rf'data-authority-flag="{flag}"[^>]*>([^<]*)</',
        html,
    )
    assert match is not None, flag
    return match.group(1).strip()


def test_company_first_fragment_shows_display_ticker_and_refusal() -> None:
    company_first = _COMPANY_FIRST
    dossier = _dossier(
        display_ticker="ACME",
        binding_state="bound",
        company_first=company_first,
        business=_refusal_business(),
        enrichment_reason="enrichment_out_of_first_unit_scope",
    )
    html = _render(dossier)

    assert "ACME" in html
    assert "shared_contract_unavailable" in html
    assert Path(company_first).name in html
    assert f'href="{company_first}"' in html
    assert f'href="{_THEME_FIRST}"' in html
    assert "enrichment_out_of_first_unit_scope" in html
    assert 'data-field="issuer_pure_play_claimed"' in html
    pure_play = re.search(
        r'data-field="issuer_pure_play_claimed"[^>]*>([^<]*)</',
        html,
    )
    assert pure_play is not None
    assert pure_play.group(1).strip() == "false"
    for flag in _FALSE_AUTHORITY:
        assert _flag_text(html, flag) == f"{flag} false"
    assert not re.search(r"<(button|input|select|textarea|form)\b", html, re.I)
    anchor_text = re.findall(r"<a\b[^>]*>(.*?)</a>", html, re.I | re.S)
    assert anchor_text
    assert all(text.strip() != "rank" for text in anchor_text)
    lowered = html.lower()
    assert "price" not in lowered
    assert "conviction" not in lowered
    assert "pure-play" not in lowered
    assert "pure play" not in lowered


def test_unbound_entity_has_no_invented_ticker() -> None:
    dossier = _dossier(
        display_ticker=None,
        binding_state="unbound",
        company_first=_UNBOUND_COMPANY_FIRST,
        business=_refusal_business(),
        enrichment_reason="security_binding_missing",
    )
    html = _render(dossier)
    ticker = re.search(r'data-field="display_ticker"[^>]*>([^<]*)</p>', html)
    assert ticker is not None
    assert ticker.group(1).strip() == ""
    assert 'data-field="binding_state">unbound<' in html
    assert 'data-field="entity_id">co:us:synth-entity<' in html
    invented = set(_TICKER_TOKEN.findall(html)) - set(
        _TICKER_TOKEN.findall(json.dumps(dossier))
    )
    assert invented == set()


def test_business_rows_render_when_the_dossier_has_rows() -> None:
    dossier = _dossier(
        display_ticker="ACME",
        binding_state="bound",
        company_first=_COMPANY_FIRST,
        business={
            "rows": [
                {
                    "row_id": "tecrow_0123456789ab",
                    "predicate": "product_workload_role",
                    "statement": "synthetic workload role",
                }
            ],
            "cards": [],
            "relationships": [],
            "ordering": "identifier_lexicographic",
        },
        enrichment_reason="enrichment_out_of_first_unit_scope",
    )
    html = _render(dossier)
    assert 'data-field="predicate">product_workload_role<' in html
    assert 'data-field="statement">synthetic workload role<' in html
    assert "shared_contract_unavailable" not in html
    assert _flag_text(html, "rank") == "rank false"


def test_fragment_does_not_read_files(monkeypatch) -> None:
    signature = inspect.signature(render_technology_dossier_page)
    assert list(signature.parameters) == ["dossier", "template_path"]
    dossier_annotation = str(signature.parameters["dossier"].annotation)
    path_annotation = str(signature.parameters["template_path"].annotation)
    assert "Mapping" in dossier_annotation
    assert "Path" in path_annotation

    dossier = _dossier(
        display_ticker="ACME",
        binding_state="bound",
        company_first=_COMPANY_FIRST,
        business=_refusal_business(),
        enrichment_reason="enrichment_out_of_first_unit_scope",
    )
    assert isinstance(dossier, Mapping)
    reads: list[Path] = []
    real_read_bytes = Path.read_bytes

    def _spy(self: Path, *args: object, **kwargs: object) -> bytes:
        reads.append(Path(self))
        return real_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", _spy)
    html = render_technology_dossier_page(dossier, TEMPLATE)
    assert "ACME" in html
    assert len(reads) == 1
    assert reads[0].resolve() == TEMPLATE.resolve()
    for path in reads:
        parts = {part.lower() for part in path.parts}
        assert "site" not in parts
        assert "data" not in parts
