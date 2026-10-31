"""C19 WP22: DHI (non-AAPL) through the integrated-answer composer on the real reader path.

The other integrated-answer tests stub ``_event_result``, so no test walked a
non-AAPL ticker through the production event-workspace reader. This one publishes
the DHI FY2026 Q3 workspace into a hermetic remote (tmp_path bytes behind a
monkeypatched fetch). The composer then traverses manifest -> alias selection ->
hash-verified workspace -> public glance -> consumed receipt.

Offline: no network and no production flag. ``financial_facts`` stays on its real
AAPL-only path; ``event_workspace`` uses the real ``_event_result``.
"""
from __future__ import annotations

import app.integrated_answer as integrated_answer
from tests.test_company_intelligence_event_workspace import _published_workspaces, _wire_remote
from tests.test_integrated_answer_v0 import REF_KEYS, _patch_all_seams
from tests.test_issuer_profiles_a5a import DHI_EXHIBIT, _build_dhi_workspace

LEG_ORDER = [
    "financial_facts",
    "earnings_expectation",
    "capital_structure",
    "publication_seam",
    "event_workspace",
    "theme_tape",
    "company_theme_exposure",
    "basket_labels",
    "theme_membership_file",
]
ALLOWED_STATUSES = frozenset({"ok", "stale", "absent", "held_unavailable"})
FIXED_ABSENT_REASON = "not_read_in_v0:owner_not_recorded;direct_site_json_reads_forbidden(I-R2)"


def _compose_dhi(tmp_path, monkeypatch):
    real_financial_facts = integrated_answer._leg_financial_facts
    real_event_result = integrated_answer._event_result
    _patch_all_seams(monkeypatch, ticker="DHI")
    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", real_financial_facts)
    monkeypatch.setattr(integrated_answer, "_event_result", real_event_result)

    workspace = _build_dhi_workspace(
        exhibit_body=DHI_EXHIBIT.read_text(encoding="utf-8"),
        prior_source_sha256=None,
    )
    assert workspace["lifecycle"]["state"] == "complete"
    _wire_remote(monkeypatch, _published_workspaces(tmp_path, workspace))
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path / "absent"))
    page, entries = integrated_answer._compose_page_with_receipts("DHI")
    return workspace, page, entries


def _leg(page, leg_id):
    matches = [item for item in page["legs"] if item["leg"] == leg_id]
    assert len(matches) == 1, leg_id
    return matches[0]


def test_dhi_page_shape_is_typed_and_honest(tmp_path, monkeypatch) -> None:
    _, page, _ = _compose_dhi(tmp_path, monkeypatch)

    assert page["schema"] == "integrated_answer.v0"
    assert page["ticker"] == "DHI"
    assert page["display_only"] is True
    assert [item["leg"] for item in page["legs"]] == LEG_ORDER
    assert {item["status"] for item in page["legs"]} <= ALLOWED_STATUSES
    assert _leg(page, "capital_structure")["status"] == "held_unavailable"

    financial_facts = _leg(page, "financial_facts")
    assert financial_facts["status"] == "absent"
    assert financial_facts["degraded_reason"] == "not_covered:golden_corpus_is_aapl_only"
    assert financial_facts["ref"] is None

    for leg_id in ("basket_labels", "theme_membership_file"):
        fixed = _leg(page, leg_id)
        assert fixed["status"] == "absent"
        assert fixed["degraded_reason"] == FIXED_ABSENT_REASON
        assert fixed["ref"] is None

    assert page["coverage_note"] == {
        "en": "Not everything below is published for every market.",
        "zh": "以下内容并非在所有市场均有发布。",
    }


def test_dhi_event_workspace_leg_comes_from_the_published_workspace(tmp_path, monkeypatch) -> None:
    workspace, page, _ = _compose_dhi(tmp_path, monkeypatch)
    leg = _leg(page, "event_workspace")

    assert leg["status"] == "ok"
    assert leg["degraded_reason"] is None
    payload = leg["payload"]
    assert payload["schema"] == "event_workspace_public_glance.v1"
    assert payload["available"] is True
    assert payload["ticker"] == "DHI"
    assert payload["plane"] == "event_workspace.v1"
    assert payload["authority"] == "context_only"
    assert payload["event_id"] == workspace["event_id"]
    assert payload["event_alias"] == "DHI/2026Q3"
    assert payload["fiscal_period"] == {"year": 2026, "quarter": 3}
    assert payload["lifecycle_state"] == "complete"
    assert payload["event_date"] == "2026-07-21"

    ref = leg["ref"]
    assert set(ref) == REF_KEYS
    assert ref["route"] == "/api/event-workspace/DHI"
    assert ref["content_hash"] == integrated_answer._content_hash(payload)


def test_dhi_consumed_receipt_records_the_event_workspace_leg(tmp_path, monkeypatch) -> None:
    _, page, entries = _compose_dhi(tmp_path, monkeypatch)
    by_leg = {entry["leg"]: entry for entry in entries}

    assert [entry["leg"] for entry in entries] == list(integrated_answer.RECEIPT_LEGS)
    assert by_leg["financial_facts"]["status"] == "NO_REF"
    assert by_leg["financial_facts"]["receipt"] is None

    leg = _leg(page, "event_workspace")
    entry = by_leg["event_workspace"]
    assert entry["status"] == "RECORDED"
    assert entry["ref_content_hash"] == leg["ref"]["content_hash"]

    receipt = entry["receipt"]
    assert receipt["consumer_version"] == integrated_answer.CONSUMER_RECEIPT_VERSION
    for field in ("bytes_sha256", "data_interval", "contract_watermark", "denominator"):
        assert receipt[field] is None, field

    expected_reasons = {
        "bytes_sha256": "NOT_READ_AT_CONSUME",
        "data_interval": "NOT_READ_AT_CONSUME",
        "contract_watermark": "NOT_READ_AT_CONSUME",
        "denominator": "NOT_APPLICABLE",
    }
    generation_id = leg["payload"].get("generation_id")
    if isinstance(generation_id, str) and generation_id:
        assert receipt["producer_generation_id"] == generation_id
        assert leg["ref"]["generation_id"] == generation_id
    else:
        assert receipt["producer_generation_id"] is None
        expected_reasons["producer_generation_id"] = "NOT_EXPOSED_BY_PRODUCER"
    assert entry["null_reasons"] == expected_reasons
    assert set(entry["null_reasons"].values()) <= integrated_answer.RECEIPT_NULL_REASONS
