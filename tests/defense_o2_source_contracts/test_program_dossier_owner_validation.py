"""Theme consumers must retain the composed dossier owner's content identity."""
import json
from pathlib import Path

import pytest

from engine.government_revenue import program_theme_context as themes
from engine.government_revenue.program_dossier import dossier_content_id


FIXTURE = Path(__file__).parent / "fixtures" / "program_dossier.json"


def snapshot(payload):
    return themes.OwnerSnapshot(
        "program_dossier", json.dumps(payload).encode(),
        max(themes._clocks(payload)).isoformat(),
        "existing:program_dossier.json", "qualified_public_display",
    )


def test_legacy_dossier_owner_preserves_bytes_and_identity():
    payload = json.loads(FIXTURE.read_bytes())
    owner = snapshot(payload)
    before = owner.raw_bytes
    assert owner.payload() == payload
    assert owner.raw_bytes == before


@pytest.mark.parametrize("mutation", ["content_id", "material_row"])
def test_schema_valid_dossier_with_stale_content_identity_is_refused(mutation):
    payload = json.loads(FIXTURE.read_bytes())
    if mutation == "content_id":
        payload["content_id"] = "gpd1-" + "0" * 24
    else:
        payload["dossiers"][0]["program_identity"]["name"] = "Changed reviewed program name"
    with pytest.raises(ValueError):
        snapshot(payload).payload()


@pytest.mark.parametrize("mutation", ["unknown_version", "undeclared_field"])
def test_rehashed_dossier_still_requires_its_owner_contract(mutation):
    payload = json.loads(FIXTURE.read_bytes())
    if mutation == "unknown_version":
        payload["schema_version"] = "1.9.0"
    else:
        payload["dossiers"][0]["public_capacity_unversioned"] = []
    payload["content_id"] = dossier_content_id(payload)
    with pytest.raises(ValueError):
        snapshot(payload).payload()
