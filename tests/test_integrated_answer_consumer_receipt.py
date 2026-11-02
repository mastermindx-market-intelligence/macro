"""Consumer-receipt binding for the integrated-answer composer (C19 WP08)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import app.integrated_answer as integrated_answer
from engine.company_theme_exposure.contracts import company_filename
from engine.company_theme_exposure.views import build_bundle, write_generation
from engine.fundamental_forensics import query_service
from tests.test_company_theme_exposure import _company_tree, _crosswalk, _membership, _state
from tests.test_integrated_answer_v0 import REF_KEYS, TOP_LEVEL_KEYS, _client, _leg_by_id, _page, _patch_all_seams

NOW = "2026-10-11T12:00:00Z"


def _write_cte_generation(tmp_path, *, theme_state=None):
    contexts, ci_manifest = _company_tree(tmp_path / "ci-src")
    exposures, manifest = build_bundle(
        contexts,
        company_manifest=ci_manifest,
        membership=_membership(),
        crosswalk=_crosswalk(),
        theme_state=theme_state,
        as_of="2026-02-02",
    )
    write_generation(tmp_path, exposures, manifest)
    return json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))


def test_reread_hash_substitution_is_detected(monkeypatch, tmp_path) -> None:
    marker = _write_cte_generation(tmp_path)
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path))
    rel = company_filename("AAPL")
    exposure_path = tmp_path / "generations" / marker["generation_id"] / rel
    bytes_a = exposure_path.read_bytes()
    bytes_b = bytes_a + b"\nTAMPERED"
    real_read_bytes = Path.read_bytes

    def _spy(self):
        data = real_read_bytes(self)
        if self.resolve() == exposure_path.resolve():
            exposure_path.write_bytes(bytes_b)
        return data

    monkeypatch.setattr(Path, "read_bytes", _spy)
    leg = integrated_answer._leg_company_theme_exposure("AAPL", NOW)
    assert leg["status"] in {"ok", "stale"}
    consumed_sha = leg["ref"].consumed_receipt["receipt"]["bytes_sha256"]
    assert consumed_sha == hashlib.sha256(bytes_a).hexdigest()
    assert consumed_sha == marker["files"][rel]["sha256"]
    current = real_read_bytes(exposure_path)
    assert consumed_sha != hashlib.sha256(current).hexdigest()
    assert current == bytes_b


def test_missing_receipt_is_not_reported_as_unused(monkeypatch, tmp_path) -> None:
    # Pin the CTE root to an absent dir so the NO_REF leg never depends on ambient host data.
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path / "absent"))
    _patch_all_seams(monkeypatch)
    page, entries = integrated_answer._compose_page_with_receipts("AAPL")
    by_leg = {entry["leg"]: entry for entry in entries}
    financial = _leg_by_id(page, "financial_facts")
    missing = by_leg["financial_facts"]
    assert missing["status"] == "MISSING"
    assert missing["receipt"] is None
    assert missing["ref_content_hash"] == financial["ref"]["content_hash"]
    unused = by_leg["company_theme_exposure"]
    assert unused["status"] == "NO_REF"
    assert unused["receipt"] is None
    assert unused["null_reasons"] == {}
    assert unused["ref_content_hash"] is None
    assert missing["status"] != unused["status"]


def test_denominator_drift_is_surfaced(monkeypatch, tmp_path) -> None:
    marker = _write_cte_generation(tmp_path, theme_state=_state(as_of="2026-02-02"))
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path))
    positive = integrated_answer._leg_company_theme_exposure("AAPL", NOW)
    assert positive["status"] in {"ok", "stale"}
    pos_receipt = positive["ref"].consumed_receipt
    assert pos_receipt["receipt"]["denominator"] == marker["coverage"]
    assert "denominator" not in pos_receipt["null_reasons"]

    gid = marker["generation_id"]
    immutable_path = tmp_path / "generations" / gid / "manifest.json"
    immutable = json.loads(immutable_path.read_text(encoding="utf-8"))
    drifted_coverage = dict(immutable["coverage"])
    drifted_coverage["active_membership_count"] = drifted_coverage["active_membership_count"] + 1
    immutable["coverage"] = drifted_coverage
    immutable_path.write_text(json.dumps(immutable), encoding="utf-8")

    negative = integrated_answer._leg_company_theme_exposure("AAPL", NOW)
    assert negative["status"] in {"ok", "stale"}
    neg_receipt = negative["ref"].consumed_receipt
    assert neg_receipt["receipt"]["denominator"] is None
    assert neg_receipt["null_reasons"]["denominator"] == "DRIFT_AT_CONSUME"


def test_fresh_transport_does_not_rescue_stale_bytes(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    monkeypatch.setattr(
        integrated_answer,
        "_theme_context",
        lambda: {
            "schema": "theme_context.v1",
            "as_of": None,
            "region": "us",
            "display_only": True,
            "leadership": [],
        },
    )
    tape = integrated_answer._leg_theme_tape()
    assert tape["status"] == "stale"
    assert tape["degraded_reason"] == "no_owner_clock"
    assert tape["ref"]["as_of"] == NOW
    tape_receipt = tape["ref"].consumed_receipt
    assert tape_receipt["receipt"]["contract_watermark"] is None
    assert tape_receipt["null_reasons"]["contract_watermark"] == "NOT_EXPOSED_BY_PRODUCER"

    marker = _write_cte_generation(tmp_path, theme_state=_state(as_of="2026-02-02"))
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path))
    rel = company_filename("AAPL")
    exposure_path = tmp_path / "generations" / marker["generation_id"] / rel
    os.utime(exposure_path, None)
    exposure = integrated_answer._leg_company_theme_exposure("AAPL", NOW)
    rec = exposure["ref"].consumed_receipt["receipt"]
    assert rec["bytes_sha256"] == marker["files"][rel]["sha256"]
    assert rec["contract_watermark"]["watermark"] == integrated_answer._normalize_clock("2026-02-02")
    assert rec["contract_watermark"]["watermark"] != NOW

    _patch_all_seams(monkeypatch)
    client = _client(monkeypatch)
    page = _page(client)
    cte = _leg_by_id(page, "company_theme_exposure")
    assert cte["status"] == "stale"
    assert cte["degraded_reason"] == "older_than_page_stamp"
    response = client.get("/api/integrated-answer/v1/AAPL")
    header = json.loads(response.headers[integrated_answer.CONSUMED_RECEIPTS_HEADER])
    cte_entry = next(item for item in header["entries"] if item["leg"] == "company_theme_exposure")
    assert cte_entry["receipt"]["bytes_sha256"] == marker["files"][rel]["sha256"]
    assert cte_entry["receipt"]["contract_watermark"]["watermark"] == integrated_answer._normalize_clock("2026-02-02")


def test_each_of_six_refs_carries_receipt_or_null_reason(monkeypatch, tmp_path) -> None:
    real_financial = integrated_answer._leg_financial_facts
    _patch_all_seams(monkeypatch)
    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", real_financial)
    monkeypatch.setattr(integrated_answer, "_financial_provider", lambda: object())

    envelope = {
        "receipt": {
            "query_hash": "q" * 64,
            "nodes": [
                {
                    "cell_id": "cell-1",
                    "provenance": {
                        "source_snapshot_at": "2026-08-01T00:00:00Z",
                        "recorded_cutoff_at": "2026-08-23T12:00:00Z",
                        "accepted_at": "2026-08-23T11:00:00Z",
                        "recorded_at": "2026-09-15T00:00:00Z",
                    },
                },
            ],
        },
        "delivery": {},
    }
    result_body = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    result_sha = hashlib.sha256(result_body).hexdigest()

    def _fake_execute(*, body: bytes, provider: object):
        del body, provider
        return query_service.FinancialQueryResult(
            body=result_body,
            sha256=result_sha,
            envelope=envelope,
        )

    monkeypatch.setattr(query_service, "execute_financial_query", _fake_execute)
    marker = _write_cte_generation(tmp_path, theme_state=_state(as_of="2026-02-02"))
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path))

    client = _client(monkeypatch)
    response = client.get("/api/integrated-answer/v1/AAPL")
    assert response.status_code == 200
    header = json.loads(response.headers[integrated_answer.CONSUMED_RECEIPTS_HEADER])
    assert set(header) == {"version", "page_sha256", "entries"}
    digest = hashlib.sha256(response.content).hexdigest()
    assert header["page_sha256"] == response.headers["X-Integrated-Answer-SHA256"] == digest
    entries = header["entries"]
    assert [item["leg"] for item in entries] == list(integrated_answer.RECEIPT_LEGS)
    receipt_keys = {
        "bytes_sha256",
        "producer_generation_id",
        "data_interval",
        "contract_watermark",
        "denominator",
        "consumer_version",
    }
    for entry in entries:
        assert entry["status"] == "RECORDED"
        receipt = entry["receipt"]
        assert set(receipt) == receipt_keys
        assert receipt["consumer_version"] == integrated_answer.CONSUMER_RECEIPT_VERSION
        for field in integrated_answer.RECEIPT_FIELDS:
            if receipt[field] is None:
                assert entry["null_reasons"][field] in integrated_answer.RECEIPT_NULL_REASONS
            else:
                assert field not in entry["null_reasons"]
    by_leg = {item["leg"]: item for item in entries}
    assert by_leg["financial_facts"]["receipt"]["bytes_sha256"] == result_sha
    assert by_leg["company_theme_exposure"]["receipt"]["producer_generation_id"] == marker["generation_id"]
    assert "consumed_receipt" not in response.text
    page = json.loads(response.content)
    assert set(page) == TOP_LEVEL_KEYS
    for leg in page["legs"]:
        if leg["ref"]:
            assert set(leg["ref"]) == REF_KEYS
