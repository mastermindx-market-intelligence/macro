"""Contract between the public rendered board and its native Terminal reader."""
import json

from jinja2 import Template

from scripts.build_macro_context import _build_view_model, _native_weather_publication


def test_publication_preserves_source_clocks_and_display_scope(tmp_path):
    snapshot = {"asof": "2026-10-17", "labels": {"us": {"us_quad": "Q2", "unknown": None}},
                "sources": {"data/regime/latest.json": "2026-10-16"}}
    transitions = [{"asof": "2026-10-17", "domain": "market", "field": "verdict",
                    "from_value": "mixed", "to_value": "risk_off"}]
    vm = _build_view_model(snapshot, {"private_probe": "private-only"}, transitions, "2026-11-14", tmp_path)
    pub = _native_weather_publication(vm, "2026-11-14 10:49 UTC")
    assert (pub["published"], pub["snapshot"]) == ("2026-11-14 10:49 UTC", "2026-10-17")
    us, intl = pub["domains"]
    assert us["id"] == "us" and us["observed"] == "2026-10-16"
    assert us["fields"][0]["value"]["en"] == "Q2"
    assert us["fields"][1]["value"] is None
    assert intl["observed"] is None and intl["fields"] == []
    assert pub["changes"][0]["date"] == "2026-10-17"
    assert pub["changes"][0]["before"]["en"].lower() == "mixed"
    assert set(pub) == {"schema", "snapshot", "published", "headline", "domains", "changes"}
    serialized = json.dumps(pub)
    assert "private-only" not in serialized and "history" not in serialized


def test_missing_snapshot_and_safe_inert_serialization(tmp_path):
    vm = _build_view_model(None, None, [], "2026-11-14", tmp_path)
    pub = _native_weather_publication(vm, "</script>")
    assert pub["snapshot"] is None and pub["domains"] == [] and pub["changes"] == []
    block = Template("{{ data | tojson }}").render(data=pub)
    assert "</script>" not in block and json.loads(block) == pub
