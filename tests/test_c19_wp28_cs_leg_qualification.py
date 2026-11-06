"""C19/WP28 offline qualification pins for the capital-structure context leg.

The integrated answer's capital-structure leg reads the published state the
``/api/capital-structure/v1/issuers/{issuer_id}/state`` route serves, through that
route's own resolution function. It has to join two issuer-id forms that capital
structure mints today to the existing company-intelligence resolver. No bridge
module exists by design: a second identity plane is refused, so the join is
pinned here as a contract rather than built. Tested against the frozen offline
fixtures with no network, no wall clock and no randomness:

1. the event spine mints ``issuer:<10-digit CIK>`` when an observation carries
   only a CIK;
2. the manifest binds ``sec:cik:<10-digit CIK>`` to the retained SEC header and
   refuses the spine's form;
3. both forms carry the same CIK digits, which resolve to one ``cik:`` company
   id, and the resolver refuses either form whole rather than coercing it;
4. the leg takes (ticker, composed_at) and reads the published state through
   ``_state_view``. This pin states the released shape; it is updated
   deliberately with the leg it pins.
"""
from __future__ import annotations

import inspect
from copy import deepcopy
from pathlib import Path

import pytest

from app import capital_structure as cs
from app.integrated_answer import _leg_capital_structure
from engine.capital_structure.event_spine import build_event_version
from engine.capital_structure.source_identity import (
    ManifestIdentityError,
    manifest_id_for,
    validate_manifest_retained_bytes_binding,
)
from engine.company_intelligence.identity import IdentityError, company_id_for_cik
from tests.test_c19_wp14_capital_observation_pins import FIXTURE, _manifest
from tests.test_capital_structure_event_spine import _observation, _span


def _spine_issuer_id(cik: str) -> str:
    version = build_event_version(_observation(issuer_id=None, cik=cik), [_span()])
    return version["issuer"]["issuer_id"]


@pytest.mark.parametrize("cik", ["1", "0000000001"])
def test_spine_mints_issuer_form_from_a_bare_cik(cik):
    assert _spine_issuer_id(cik) == "issuer:0000000001"


def test_spine_keeps_a_supplied_issuer_id_verbatim():
    version = build_event_version(_observation(issuer_id="issuer:0000000042", cik="1"), [_span()])
    assert version["issuer"]["issuer_id"] == "issuer:0000000042"


def test_manifest_binds_sec_cik_form_and_refuses_the_spine_form():
    raw = FIXTURE.read_bytes()
    manifest = _manifest(raw)
    assert manifest["issuer"]["issuer_id"] == "sec:cik:0000000001"
    validate_manifest_retained_bytes_binding(manifest, raw)

    forged = deepcopy(manifest)
    forged["issuer"]["issuer_id"] = _spine_issuer_id("1")
    forged["manifest_id"] = manifest_id_for(forged)
    with pytest.raises(ManifestIdentityError, match="issuer_id is detached"):
        validate_manifest_retained_bytes_binding(forged, raw)


def test_both_forms_resolve_to_one_company_id_once_stripped():
    spine = _spine_issuer_id("1")
    manifest = _manifest(FIXTURE.read_bytes())["issuer"]["issuer_id"]
    assert spine != manifest
    assert company_id_for_cik(spine.removeprefix("issuer:")) == "cik:0000000001"
    assert company_id_for_cik(manifest.removeprefix("sec:cik:")) == "cik:0000000001"


@pytest.mark.parametrize("value", ["cik:0000320193", "320193", "0000320193"])
def test_resolver_accepts_only_cik_shaped_values(value):
    assert company_id_for_cik(value) == "cik:0000320193"


@pytest.mark.parametrize("value", ["issuer:0000320193", "sec:cik:0000320193"])
def test_resolver_refuses_capital_structure_forms_whole(value):
    with pytest.raises(IdentityError):
        company_id_for_cik(value)


def test_capital_structure_leg_takes_ticker_and_composed_at_and_fails_closed(monkeypatch):
    assert list(inspect.signature(_leg_capital_structure).parameters) == ["ticker", "composed_at"]
    monkeypatch.setattr(cs, "PROJECTION_PATH", Path("/nonexistent/capital_structure/projection.json"))
    cs._reset_cache()
    leg = _leg_capital_structure("AAPL", "2026-11-01T00:00:00Z")
    assert leg["leg"] == "capital_structure"
    assert leg["status"] == "absent"
    assert leg["degraded_reason"] == "state_unavailable"
    assert leg["payload"] is None
    assert leg["ref"] is None
    assert leg["copy"]["en"]
    assert leg["copy"]["zh"]
