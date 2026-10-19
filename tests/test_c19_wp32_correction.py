"""C19 WP32 P5 — integrated-answer generation-correction pins (tests only).

BASE: ``origin/main`` 4f52d22596545cbd67b5143e188baf5660237024.

Rung P5 of the WP32 rollout ladder for ``GET /api/integrated-answer/v1/{ticker}``
(``app/integrated_answer.py``): when the company-theme-exposure (CTE) published
generation is corrected from G1 to G2, the very next response must cite G2 in
every identity it exposes — the leg ``ref``, the consumed receipt and the
consumed-receipts header entry — and its page SHA must change.  No single
response may mix G1 and G2 identities.

Every generation on disk here is written by the real
``engine.company_theme_exposure.views.write_generation`` into a ``tmp_path`` root
that only ``MACRO_CTE_DIR`` points at (``app/integrated_answer.py:366``), so
nothing under ``data/`` is opened.  Tickers are synthetic and outside the
preregistered exposure universe: ZZWP is the published member, ZZWQ is a second
member that is deliberately not in the generation.  No production code is
modified by this file.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import app.integrated_answer as integrated_answer
from app.integrated_answer import CONSUMED_RECEIPTS_HEADER
from engine.company_intelligence.views import build_bundle as build_company_bundle
from engine.company_intelligence.views import write_generation as write_company_generation
from engine.company_theme_exposure.contracts import company_filename
from engine.company_theme_exposure.views import build_bundle as build_cte_bundle
from engine.company_theme_exposure.views import load_company_generation
from engine.company_theme_exposure.views import write_generation as write_cte_generation
from tests.test_company_theme_exposure import _crosswalk, _state
from tests.test_integrated_answer_v0 import _client, _leg_by_id, _patch_all_seams

TICKER = "ZZWP"
SECOND = "ZZWQ"
CTE_LEG = "company_theme_exposure"
PATH = f"/api/integrated-answer/v1/{TICKER}"
NOW = "2026-02-03T00:00:00Z"
SUMMARY_G1 = "wp32 synthetic primary summary, first publication"
SUMMARY_G2 = "wp32 synthetic primary summary, corrected republication"


def _membership() -> dict[str, Any]:
    """Mirror of ``tests.test_company_theme_exposure._membership`` with synthetic tickers only."""
    return {
        "version": "wp32-fixture",
        "curated": "2026-02-02",
        "baskets": {
            "mapped": {"members": [{"ticker": TICKER, "added": "2025-01-01", "removed": None}]},
            "unmapped": {"members": [{"ticker": TICKER, "added": "2025-01-01", "removed": None}]},
        },
    }


def _publish(root: Path, *, source_dir: Path, summary: str) -> dict[str, Any]:
    """Publish one real CTE generation into ``root`` with the real writer; return the marker.

    Mirrors ``tests/test_integrated_answer_consumer_receipt.py::_write_cte_generation`` (which is
    hard-wired to a universe ticker) with the synthetic ZZWP member instead.  Writing G2 into the
    same ``root`` leaves ``root/generations/<G1>/`` in place: ``write_generation`` only ever adds
    ``generations/<gid>/`` and re-points ``root/manifest.json``
    (``engine/company_theme_exposure/views.py:432-470``; the module contains no
    ``shutil``/``rmtree``/``unlink``/``rmdir`` call), which is what makes the rollback pin possible.
    """
    history = [
        {
            "document_ticker": TICKER, "fiscal_year": 2026, "fiscal_quarter": 1,
            "call_date": "2026-01-29", "updated_at": "2026-02-01T00:00:00Z",
            "summary": summary, "raw_source_url": "https://issuer.example/wp32-synthetic",
        },
    ]
    contexts, descriptor = build_company_bundle(
        history,
        tx_index={"schema": "mastermind.tx-index/v1", "documents": []},
        generated_at="2026-02-02T00:00:00Z",
        as_of="2026-02-02",
    )
    write_company_generation(source_dir, contexts, descriptor)
    company_contexts, company_manifest = load_company_generation(source_dir)
    exposures, manifest = build_cte_bundle(
        company_contexts,
        company_manifest=company_manifest,
        membership=_membership(),
        crosswalk=_crosswalk(),
        theme_state=_state(),
        as_of="2026-02-02",
    )
    write_cte_generation(root, exposures, manifest)
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))


def _receipts(response) -> dict[str, Any]:
    return json.loads(response.headers[CONSUMED_RECEIPTS_HEADER])


def _cte_entry(response) -> dict[str, Any]:
    for entry in _receipts(response)["entries"]:
        if entry["leg"] == CTE_LEG:
            return entry
    raise KeyError(CTE_LEG)


def _exposed_generation_ids(response) -> set[str]:
    """Every CTE generation identity one response exposes: body ref, consumed receipt, header entry."""
    ids: set[str] = set()
    ref = _leg_by_id(json.loads(response.content), CTE_LEG).get("ref")
    if isinstance(ref, dict) and ref.get("generation_id"):
        ids.add(str(ref["generation_id"]))
    receipt = _cte_entry(response).get("receipt") or {}
    if receipt.get("producer_generation_id"):
        ids.add(str(receipt["producer_generation_id"]))
    return ids


def _get(monkeypatch, root: Path, *, ticker: str = TICKER):
    """One route-level GET: every non-CTE seam patched, the clock frozen, MACRO_CTE_DIR at ``root``.

    The clock is frozen (the idiom of ``tests/test_integrated_answer_consumer_receipt.py:110``) so a
    changed page SHA proves a content change, never a second rolling over.
    """
    monkeypatch.setenv("MACRO_CTE_DIR", str(root))
    _patch_all_seams(monkeypatch, ticker=ticker)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    return _client(monkeypatch).get(f"/api/integrated-answer/v1/{ticker}")


def test_p5_published_generation_is_cited_in_every_identity(monkeypatch, tmp_path) -> None:
    """P5 CORRECTION (T3a): a published G1 is cited identically by the leg ref, the consumed
    receipt and the consumed-receipts header entry; the receipt bytes hash equals the marker file
    receipt, and X-Integrated-Answer-SHA256 binds the body."""
    marker1 = _publish(tmp_path, source_dir=tmp_path / "src-g1", summary=SUMMARY_G1)
    gid1 = marker1["generation_id"]
    rel = company_filename(TICKER)

    response = _get(monkeypatch, tmp_path)
    assert response.status_code == 200
    leg = _leg_by_id(json.loads(response.content), CTE_LEG)
    assert leg["status"] in {"ok", "stale"}
    assert leg["ref"]["generation_id"] == gid1

    entry = _cte_entry(response)
    assert entry["status"] == "RECORDED"
    assert entry["receipt"]["producer_generation_id"] == gid1
    assert entry["receipt"]["bytes_sha256"] == marker1["files"][rel]["sha256"]

    digest = response.headers["X-Integrated-Answer-SHA256"]
    assert digest == hashlib.sha256(response.content).hexdigest()
    assert _receipts(response)["page_sha256"] == digest
    assert _exposed_generation_ids(response) == {gid1}


def test_p5_correction_to_a_new_generation_replaces_every_identity(monkeypatch, tmp_path) -> None:
    """P5 CORRECTION (T3b): after the published generation is corrected G1 -> G2 in place, the very
    next response cites G2 in ref, receipt and header entry, cites G1 nowhere in the body or the
    consumed-receipts header, and its page SHA differs from the pre-correction SHA."""
    marker1 = _publish(tmp_path, source_dir=tmp_path / "src-g1", summary=SUMMARY_G1)
    gid1 = marker1["generation_id"]
    rel = company_filename(TICKER)
    before = _get(monkeypatch, tmp_path)
    assert before.status_code == 200

    marker2 = _publish(tmp_path, source_dir=tmp_path / "src-g2", summary=SUMMARY_G2)
    gid2 = marker2["generation_id"]
    assert gid2 != gid1
    assert marker2["files"][rel]["sha256"] != marker1["files"][rel]["sha256"]

    after = _get(monkeypatch, tmp_path)
    assert after.status_code == 200
    body_text, header_text = after.text, after.headers[CONSUMED_RECEIPTS_HEADER]
    assert gid1 not in body_text
    assert gid1 not in header_text

    leg = _leg_by_id(json.loads(after.content), CTE_LEG)
    assert leg["status"] in {"ok", "stale"}
    assert leg["ref"]["generation_id"] == gid2
    entry = _cte_entry(after)
    assert entry["receipt"]["producer_generation_id"] == gid2
    assert entry["receipt"]["bytes_sha256"] == marker2["files"][rel]["sha256"]
    assert _exposed_generation_ids(after) == {gid2}
    assert after.headers["X-Integrated-Answer-SHA256"] != before.headers["X-Integrated-Answer-SHA256"]


def test_p5_no_response_ever_mixes_two_generation_identities(monkeypatch, tmp_path) -> None:
    """P5 CORRECTION (T3c): across repeated responses before and after one correction, every 200
    exposes exactly one CTE generation identity, and that one identity is the marker's current one."""
    marker1 = _publish(tmp_path, source_dir=tmp_path / "src-g1", summary=SUMMARY_G1)
    gid1 = marker1["generation_id"]
    for _ in range(2):
        response = _get(monkeypatch, tmp_path)
        assert response.status_code == 200
        ids = _exposed_generation_ids(response)
        assert len(ids) == 1
        assert ids == {gid1}

    marker2 = _publish(tmp_path, source_dir=tmp_path / "src-g2", summary=SUMMARY_G2)
    gid2 = marker2["generation_id"]
    for _ in range(2):
        response = _get(monkeypatch, tmp_path)
        assert response.status_code == 200
        ids = _exposed_generation_ids(response)
        assert len(ids) == 1
        assert ids == {gid2}
        assert gid1 not in response.headers[CONSUMED_RECEIPTS_HEADER]


def test_p5_correction_published_mid_compose_never_mixes_identities(monkeypatch, tmp_path) -> None:
    """P5 CORRECTION (T3d): if G2 is published immediately AFTER this response has read the G1
    marker, the response is still single-generation — either fully G1 (G1's directory survives the
    G2 write) with G1 bytes, or an honest absent leg with a generation_* degraded_reason.  It is
    never a G1 identity carrying G2 bytes."""
    marker1 = _publish(tmp_path, source_dir=tmp_path / "src-g1", summary=SUMMARY_G1)
    gid1 = marker1["generation_id"]
    rel = company_filename(TICKER)
    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path))
    _patch_all_seams(monkeypatch, ticker=TICKER)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)

    marker_path = tmp_path / "manifest.json"
    real_read_text = Path.read_text
    state: dict[str, Any] = {"published": False, "gid2": None}

    def _spy(self, *args, **kwargs):  # noqa: ANN001 - Path.read_text wrapper
        data = real_read_text(self, *args, **kwargs)
        if not state["published"] and self.resolve() == marker_path.resolve():
            state["published"] = True
            state["gid2"] = _publish(
                tmp_path, source_dir=tmp_path / "src-g2", summary=SUMMARY_G2
            )["generation_id"]
        return data

    monkeypatch.setattr(Path, "read_text", _spy)
    response = _client(monkeypatch).get(PATH)

    assert state["published"] is True
    gid2 = state["gid2"]
    assert gid2 is not None and gid2 != gid1
    assert response.status_code == 200
    leg = _leg_by_id(json.loads(response.content), CTE_LEG)
    ids = _exposed_generation_ids(response)
    assert len(ids) <= 1
    if leg["status"] in {"ok", "stale"}:
        assert ids == {gid1}
        assert gid2 not in response.text
        assert gid2 not in response.headers[CONSUMED_RECEIPTS_HEADER]
        # a G1 identity must be paired with the G1 bytes the marker receipt names, never G2's
        assert _cte_entry(response)["receipt"]["bytes_sha256"] == marker1["files"][rel]["sha256"]
        assert (tmp_path / "generations" / gid1).is_dir()
    else:
        assert leg["status"] == "absent"
        assert leg["degraded_reason"] is not None
        assert leg["degraded_reason"].startswith("generation_")
        assert ids == set()


def test_p5_ticker_absent_from_the_generation_is_honest_and_leaks_no_identity(monkeypatch, tmp_path) -> None:
    """P5 CORRECTION (T3e): a second synthetic ticker that is not in the marker's files map gets an
    honest absent leg with degraded_reason ticker_not_in_generation, a NO_REF header entry, and no
    generation identity of the published ZZWP file leaks into that leg's ref, receipt or entry."""
    marker1 = _publish(tmp_path, source_dir=tmp_path / "src-g1", summary=SUMMARY_G1)
    gid1 = marker1["generation_id"]
    assert company_filename(SECOND) not in marker1["files"]

    response = _get(monkeypatch, tmp_path, ticker=SECOND)
    assert response.status_code == 200
    body = json.loads(response.content)
    assert body["ticker"] == SECOND

    leg = _leg_by_id(body, CTE_LEG)
    assert leg["status"] == "absent"
    assert leg["degraded_reason"] == "ticker_not_in_generation"
    assert leg["ref"] is None
    entry = _cte_entry(response)
    assert entry["status"] == "NO_REF"
    assert entry["receipt"] is None
    assert _exposed_generation_ids(response) == set()
    assert gid1 not in json.dumps(leg)
    assert gid1 not in json.dumps(entry)


def test_p5_re_pointing_the_marker_at_the_surviving_generation_restores_that_identity(monkeypatch, tmp_path) -> None:
    """P5 / T2 ROLLBACK: the G1 generation directory survives the G2 write, so re-writing
    root/manifest.json from the saved G1 marker bytes makes the next response cite G1 again —
    byte-for-byte the pre-correction body and page SHA (the clock is frozen, so equality is
    content equality, not a clock artifact)."""
    marker1 = _publish(tmp_path, source_dir=tmp_path / "src-g1", summary=SUMMARY_G1)
    gid1 = marker1["generation_id"]
    g1_marker_bytes = (tmp_path / "manifest.json").read_bytes()
    first = _get(monkeypatch, tmp_path)
    assert _exposed_generation_ids(first) == {gid1}

    marker2 = _publish(tmp_path, source_dir=tmp_path / "src-g2", summary=SUMMARY_G2)
    gid2 = marker2["generation_id"]
    assert (tmp_path / "generations" / gid1).is_dir()
    corrected = _get(monkeypatch, tmp_path)
    assert _exposed_generation_ids(corrected) == {gid2}

    (tmp_path / "manifest.json").write_bytes(g1_marker_bytes)
    rolled_back = _get(monkeypatch, tmp_path)
    assert rolled_back.status_code == 200
    assert _exposed_generation_ids(rolled_back) == {gid1}
    assert _leg_by_id(json.loads(rolled_back.content), CTE_LEG)["ref"]["generation_id"] == gid1
    assert gid2 not in rolled_back.text
    assert rolled_back.content == first.content
    assert rolled_back.headers["X-Integrated-Answer-SHA256"] == first.headers["X-Integrated-Answer-SHA256"]


def test_p5_the_cte_leg_is_never_cached_and_re_reads_the_marker_each_compose(monkeypatch, tmp_path) -> None:
    """P5 (source fact behind T3b): ``_leg_company_theme_exposure`` holds no cache — every compose
    re-reads root/manifest.json exactly once, which is what lets a correction land on the very next
    response.  A cached leg would read the marker fewer times than there are responses."""
    marker1 = _publish(tmp_path, source_dir=tmp_path / "src-g1", summary=SUMMARY_G1)
    gid1 = marker1["generation_id"]
    marker_path = tmp_path / "manifest.json"
    real_read_text = Path.read_text
    counts = {"marker": 0}

    def _spy(self, *args, **kwargs):  # noqa: ANN001 - Path.read_text wrapper
        data = real_read_text(self, *args, **kwargs)
        if self.resolve() == marker_path.resolve():
            counts["marker"] += 1
        return data

    monkeypatch.setenv("MACRO_CTE_DIR", str(tmp_path))
    _patch_all_seams(monkeypatch, ticker=TICKER)
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: NOW)
    monkeypatch.setattr(Path, "read_text", _spy)

    client = _client(monkeypatch)
    for expected in range(1, 4):
        response = client.get(PATH)
        assert response.status_code == 200
        assert counts["marker"] == expected
        assert _exposed_generation_ids(response) == {gid1}
