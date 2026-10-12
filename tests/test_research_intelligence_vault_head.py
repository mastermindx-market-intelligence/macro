"""Pins for the bounded Research Vault deep-read head.

Each test names the assertion that must fail if that behavior is removed.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.press.research_triage import shortlist
from engine.research_intelligence import vault_head as vault_head_mod
from engine.research_intelligence.schema import SCHEMA
from engine.research_intelligence.store import (
    ResearchIntelligenceEffectUnknown,
    ResearchIntelligenceStoreError,
    load_latest_research_intelligence,
)
from engine.research_intelligence.vault_head import (
    DEFAULT_HEAD_SIZE,
    MAX_HEAD_SIZE,
    deep_read_candidate,
    deep_read_head,
    rank_vault_head,
    read_canonical_text,
    select_ranked_head,
)
from engine.research_vault import catalog as catalog_mod
from engine.research_vault.ingest import VAULT_PREFIX
from engine.research_vault.r2_store import LocalStore


REPORT_ID = "fixture-research-2026-09-18-amd-demand"
CLAIM = "ZZF9SOURCECLAIMZZ server demand accelerated by 35% year over year."
BODY_TOKEN = "ZZF9BODYTOKENZZ"
QUOTE = CLAIM
BODY = (
    CLAIM
    + " Management expects supply to normalize by the December quarter."
    + f" The private marker {BODY_TOKEN} appears only in the source."
)
ITEM = {
    "id": REPORT_ID,
    "institution": "Fixture Research",
    "desk": "Semiconductors",
    "title": "AMD server demand",
    "published_at": "2026-09-18T12:00:00Z",
    "summary_points": ["AMD demand strengthened.", "Supply should normalize."],
    "tags": ["semiconductors"],
    "tickers": ["AMD"],
    "top_pick": False,
    "pages": 8,
    "language": "en",
    "needs_metadata": False,
}
PDF_BYTES = b"%PDF-1.4\nfixture canonical bytes\n"


def _candidate(item=None, rank=1, **extra):
    chosen = dict(item or ITEM)
    row = {
        "item": chosen,
        "triage": {
            "report_id": chosen["id"],
            "rank": rank,
            "w_score": 0.91,
            "status": "selected" if rank == 1 else "skipped",
            "tier": "flagship" if rank == 1 else "none",
        },
    }
    row.update(extra)
    return row


def _model_call(system, user, *, model_id, max_tokens):
    identity_text = user.split("DOCUMENT IDENTITY:\n", 1)[1].split(
        "\n\nOUTPUT SHAPE:", 1
    )[0]
    identity = json.loads(identity_text)
    rio = {
        "schema": SCHEMA,
        "document": identity,
        "claims": [
            {
                "statement": CLAIM,
                "evidence": [{"quote_span": CLAIM}],
                "numbers": ["35%"],
                "entities": ["AMD"],
                "horizon": "current",
                "explicit": True,
            }
        ],
        "analysis": {
            "thesis": {
                "summary": "The note argues cloud ordering is strengthening server demand.",
                "direction": "bullish",
                "mechanism": ["stronger cloud ordering supports server demand"],
                "conviction": "moderate",
                "support_claim_indices": [0],
            },
            "assumptions": [],
            "forecasts": [],
            "catalysts": [],
            "falsifiers": [],
            "counterarguments": [],
            "implications": [],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
            "uncertainties": [],
        },
        "authority": "descriptive_research_only",
    }
    return json.dumps(rio), "fixture-provider", f"served-{model_id}"


def _counting_call(counter):
    def call(system, user, *, model_id, max_tokens):
        counter["n"] += 1
        counter["user"] = user
        return _model_call(system, user, model_id=model_id, max_tokens=max_tokens)

    return call


def _seed_pdf(store, report_id=REPORT_ID, pdf=PDF_BYTES):
    assert store.put_bytes(
        f"{VAULT_PREFIX}{report_id}.pdf",
        pdf,
        "application/pdf",
    )


def _provider(extractor, reads=None):
    def provider(store, report_id, *, pdf_max_bytes, body_max_bytes, expected_pdf_sha256=None):
        if reads is not None:
            reads.append(report_id)
        return read_canonical_text(
            store,
            report_id,
            pdf_max_bytes=pdf_max_bytes,
            body_max_bytes=body_max_bytes,
            extractor=extractor,
            expected_pdf_sha256=expected_pdf_sha256,
        )

    return provider


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert_no_private_text(value):
    dumped = _dump(value)
    assert BODY_TOKEN not in dumped
    assert QUOTE not in dumped
    assert "quote_span" not in dumped
    assert '"rio"' not in dumped


def test_t1_ranked_head_is_independent_of_press_publish_tier():
    """T1 pin: skipped/none rows stay in the cognition head and out of the flagship shortlist."""
    second = dict(ITEM)
    second["id"] = "fixture-research-2026-09-18-second"
    third = dict(ITEM)
    third["id"] = "fixture-research-2026-09-18-third"
    triage = {
        "rows": [
            {
                "report_id": ITEM["id"],
                "rank": 1,
                "w_score": 0.90,
                "status": "selected",
                "tier": "flagship",
            },
            {
                "report_id": second["id"],
                "rank": 2,
                "w_score": 0.80,
                "status": "skipped",
                "tier": "none",
            },
            {
                "report_id": third["id"],
                "rank": 3,
                "w_score": 0.70,
                "status": "skipped",
                "tier": "none",
            },
        ]
    }
    selected = select_ranked_head([ITEM, second, third], triage, limit=3)
    assert shortlist(triage, "flagship") == [ITEM["id"]]
    assert [row["item"]["id"] for row in selected] == [
        ITEM["id"],
        second["id"],
        third["id"],
    ]
    assert [row["triage"]["tier"] for row in selected] == ["flagship", "none", "none"]


def test_t2_head_bound_rejects_zero_bool_and_over_max():
    """T2 pin: 0, True, and 51 are rejected; the default take is 20; 51 candidates raise."""
    assert DEFAULT_HEAD_SIZE == 20
    items = []
    rows = []
    for index in range(DEFAULT_HEAD_SIZE + 5):
        report_id = f"fixture-research-2026-09-18-item-{index:02d}"
        items.append({**ITEM, "id": report_id})
        rows.append(
            {
                "report_id": report_id,
                "rank": index + 1,
                "w_score": 1.0,
                "status": "ranked",
                "tier": "none",
            }
        )
    selected = select_ranked_head(items, {"rows": rows})
    assert len(selected) == DEFAULT_HEAD_SIZE
    assert selected[-1]["item"]["id"] == "fixture-research-2026-09-18-item-19"

    for bad in (0, MAX_HEAD_SIZE + 1, True):
        with pytest.raises(ValueError):
            select_ranked_head(items, {"rows": rows}, limit=bad)

    def must_not_read(*_args, **_kwargs):
        raise AssertionError("oversized batch must fail before any source read")

    with pytest.raises(ValueError):
        deep_read_head(
            [_candidate() for _ in range(MAX_HEAD_SIZE + 1)],
            store=object(),
            model_id="fixture-model-a",
            text_provider=must_not_read,
        )


def test_rank_vault_head_refuses_unreconciled_denominator():
    original = vault_head_mod.research_triage.rank
    vault_head_mod.research_triage.rank = lambda *args, **kwargs: {
        "rows": [{"report_id": REPORT_ID, "rank": 1, "w_score": 0.9, "status": "selected"}],
        "reconciled": False,
    }
    try:
        rank_vault_head([ITEM], as_of=__import__("datetime").date(2026, 9, 18), limit=1)
    except ValueError as exc:
        assert "reconcile" in str(exc)
    else:
        raise AssertionError("unreconciled triage must not produce a cognition head")
    finally:
        vault_head_mod.research_triage.rank = original


def test_t3_missing_pdf_spends_no_model_call_and_writes_nothing(tmp_path):
    """T3 pin: a missing PDF is pdf_missing, with zero model calls and an unchanged key set."""
    store = LocalStore(tmp_path / "vault")
    before = set(store.list_prefix(""))
    counter = {"n": 0}
    result = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_counting_call(counter),
    )
    assert result["state"] == "pdf_missing"
    assert counter["n"] == 0
    assert set(store.list_prefix("")) == before
    assert "body" not in result
    _assert_no_private_text(result)


def test_t4_missing_extractor_and_form_feed_text_make_no_model_call(tmp_path):
    """T4 pin: None is extractor_unavailable; form-feed-only text is no_text_layer; neither calls the model."""
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    counter = {"n": 0}

    missing = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_counting_call(counter),
        text_provider=_provider(lambda _pdf: None),
    )
    assert missing["state"] == "extractor_unavailable"
    assert counter["n"] == 0

    blank = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_counting_call(counter),
        text_provider=_provider(lambda _pdf: "\f\f\f"),
    )
    assert blank["state"] == "no_text_layer"
    assert counter["n"] == 0
    assert "body" not in blank
    assert BODY_TOKEN not in _dump(blank)


def test_t5_persisted_text_hash_is_not_the_pdf_hash_and_is_not_truncated(tmp_path):
    """T5 pin: stored source hash equals the full extracted text, and the PDF hash is separate."""
    store = LocalStore(tmp_path / "vault")
    pdf = b"%PDF-1.4\nlong-fixture\n"
    _seed_pdf(store, pdf=pdf)
    padding = "Desk context remains descriptive and adds no new figure. "
    text = CLAIM + "\n" + (padding * 1200)
    assert len(text) > 60000
    past = text[60000:60080]
    token = "ZZF9PAST60KTOKENZZ"
    text = text + token + " remains visible past the old truncation point."
    assert token in text[60000:]
    counter = {"n": 0, "user": ""}
    result = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_counting_call(counter),
        text_provider=_provider(lambda _pdf: text),
    )
    assert result["state"] == "persisted"
    assert result["write_state"] == "created"
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    pdf_sha = hashlib.sha256(pdf).hexdigest()
    stored = load_latest_research_intelligence(store, REPORT_ID)
    assert stored is not None
    assert stored.source_content_sha256 == text_sha == result["extracted_text_sha256"]
    assert result["source_pdf_sha256"] == pdf_sha
    assert result["source_pdf_sha256"] != result["extracted_text_sha256"]
    assert result["source_content_sha256"] == text_sha
    assert past in counter["user"]
    assert token in counter["user"]
    assert token not in _dump(result)
    _assert_no_private_text(result)


def test_t6_exact_rerun_is_already_current_and_spends_no_model_call(tmp_path):
    """T6 pin: the same PDF, text, prompt, model, and document make zero model calls on rerun."""
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    counter = {"n": 0, "user": ""}
    first = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_counting_call(counter),
        text_provider=_provider(lambda _pdf: BODY),
    )
    assert first["state"] == "persisted"
    assert counter["n"] == 1
    counter["n"] = 0
    second = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_counting_call(counter),
        text_provider=_provider(lambda _pdf: BODY),
    )
    assert second["state"] == "already_current"
    assert second["artifact_sha256"] == first["artifact_sha256"]
    assert counter["n"] == 0

    real_load = vault_head_mod.load_latest_research_intelligence

    def stale_contract(store_arg, document_id):
        latest = real_load(store_arg, document_id)
        receipt = dict(latest.receipt)
        receipt["prompt_contract_sha256"] = "0" * 64
        return dataclasses.replace(latest, receipt=receipt)

    vault_head_mod.load_latest_research_intelligence = stale_contract
    try:
        third = deep_read_candidate(
            _candidate(),
            store=store,
            model_id="fixture-model-a",
            call=_counting_call(counter),
            text_provider=_provider(lambda _pdf: BODY),
        )
    finally:
        vault_head_mod.load_latest_research_intelligence = real_load
    assert third["state"] == "persisted"
    assert counter["n"] == 1
    assert third["previous_artifact_sha256"] == first["artifact_sha256"]


def test_t7_model_change_corrects_against_exact_predecessor(tmp_path):
    """T7 pin: a requested-model change persists with previous_artifact_sha256 equal to the first artifact."""
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    first = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        text_provider=_provider(lambda _pdf: BODY),
    )
    second = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-b",
        call=_model_call,
        text_provider=_provider(lambda _pdf: BODY),
    )
    assert first["state"] == "persisted"
    assert second["state"] == "persisted"
    assert second["write_state"] == "corrected"
    assert second["previous_artifact_sha256"] == first["artifact_sha256"]
    assert second["artifact_sha256"] != first["artifact_sha256"]


def test_t8_catalog_title_change_corrects_against_predecessor(tmp_path):
    """T8 pin: a catalog title change is not current and corrects against the predecessor."""
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    first = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        text_provider=_provider(lambda _pdf: BODY),
    )
    changed = dict(ITEM)
    changed["title"] = "AMD server demand corrected title"
    second = deep_read_candidate(
        _candidate(changed),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        text_provider=_provider(lambda _pdf: BODY),
    )
    assert first["state"] == "persisted"
    assert second["state"] != "already_current"
    assert second["state"] == "persisted"
    assert second["write_state"] == "corrected"
    assert second["previous_artifact_sha256"] == first["artifact_sha256"]


def test_t9_corrected_source_changes_pdf_hash_and_corrects(tmp_path):
    """T9 pin: different PDF bytes and extracted text correct against the predecessor and change source_pdf_sha256."""
    store = LocalStore(tmp_path / "vault")
    pdf_a = b"%PDF-1.4\nfixture-revision-a\n"
    pdf_b = b"%PDF-1.4\nfixture-revision-b-rewritten\n"
    text_b = BODY + " A revised paragraph changes the source."
    _seed_pdf(store, pdf=pdf_a)
    first = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        text_provider=_provider(lambda _pdf: BODY),
    )
    _seed_pdf(store, pdf=pdf_b)
    second = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        text_provider=_provider(lambda _pdf: text_b),
    )
    assert first["state"] == "persisted"
    assert second["state"] != "already_current"
    assert second["state"] == "persisted"
    assert second["write_state"] == "corrected"
    assert second["previous_artifact_sha256"] == first["artifact_sha256"]
    assert first["source_pdf_sha256"] == hashlib.sha256(pdf_a).hexdigest()
    assert second["source_pdf_sha256"] == hashlib.sha256(pdf_b).hexdigest()
    assert second["source_pdf_sha256"] != first["source_pdf_sha256"]
    assert second["extracted_text_sha256"] == hashlib.sha256(text_b.encode("utf-8")).hexdigest()
    assert second["extracted_text_sha256"] != first["extracted_text_sha256"]


def test_t10_expected_pdf_hash_mismatch_skips_extractor_and_model(tmp_path):
    """T10 pin: a mismatched expected_pdf_sha256 is source_revision_mismatch and never calls the extractor."""
    store = LocalStore(tmp_path / "vault")
    pdf = b"%PDF-1.4\nexpected-hash-fixture\n"
    _seed_pdf(store, pdf=pdf)
    calls = {"extractor": 0, "model": 0}

    def extractor(_pdf):
        calls["extractor"] += 1
        return BODY

    def model(*_args, **_kwargs):
        calls["model"] += 1
        raise AssertionError("model must not run after a PDF revision mismatch")

    result = deep_read_candidate(
        _candidate(expected_pdf_sha256="0" * 64),
        store=store,
        model_id="fixture-model-a",
        call=model,
        text_provider=_provider(extractor),
    )
    assert result["state"] == "source_revision_mismatch"
    assert calls["extractor"] == 0
    assert calls["model"] == 0
    assert result["source_pdf_sha256"] == hashlib.sha256(pdf).hexdigest()
    assert "body" not in result


def test_t11_effect_unknown_halts_the_batch_before_later_source_reads(tmp_path):
    """T11 pin: the first effect_unknown stops the batch with unattempted == 2 and one model call."""
    store = LocalStore(tmp_path / "vault")
    ids = [
        REPORT_ID,
        "fixture-research-2026-09-18-second",
        "fixture-research-2026-09-18-third",
    ]
    candidates = [_candidate({**ITEM, "id": report_id}, rank=index + 1) for index, report_id in enumerate(ids)]
    reads = []
    counter = {"n": 0}

    def provider(store_arg, report_id, *, pdf_max_bytes, body_max_bytes, expected_pdf_sha256=None):
        reads.append(report_id)
        text_sha = hashlib.sha256(BODY.encode("utf-8")).hexdigest()
        return {
            "state": "ok",
            "report_id": report_id,
            "body": BODY,
            "body_bytes": len(BODY.encode("utf-8")),
            "source_pdf_sha256": hashlib.sha256(b"provider-pdf").hexdigest(),
            "extracted_text_sha256": text_sha,
            "text_layer_state": "full",
            "page_count": 1,
            "extractor_name": "pdftotext",
            "extractor_version": "research_vault.ingest.extract_pdf_text.v1",
        }

    def explode(*_args, **_kwargs):
        raise ResearchIntelligenceEffectUnknown(
            "pointer_effect_unknown",
            "simulated lost reply",
            write_error=OSError("reply lost"),
        )

    original = vault_head_mod.persist_analysis
    vault_head_mod.persist_analysis = explode
    try:
        batch = deep_read_head(
            candidates,
            store=store,
            model_id="fixture-model-a",
            call=_counting_call(counter),
            text_provider=provider,
        )
    finally:
        vault_head_mod.persist_analysis = original

    assert batch["halted"] == "effect_unknown"
    assert batch["unattempted"] == 2
    assert counter["n"] == 1
    assert reads == [REPORT_ID]
    assert len(batch["results"]) == 1
    assert batch["results"][0]["state"] == "effect_unknown"
    assert batch["schema"] == vault_head_mod.DEEP_READ_SCHEMA + ".batch"


def test_t12_latest_read_failure_spends_no_model_call(tmp_path):
    """T12 pin: a store error from load_latest is latest_read_failed and does not call the model."""
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    counter = {"n": 0}

    def broken(_store, _document_id):
        raise ResearchIntelligenceStoreError("artifact_read_failed", "simulated latest outage")

    original = vault_head_mod.load_latest_research_intelligence
    vault_head_mod.load_latest_research_intelligence = broken
    try:
        result = deep_read_candidate(
            _candidate(),
            store=store,
            model_id="fixture-model-a",
            call=_counting_call(counter),
            text_provider=_provider(lambda _pdf: BODY),
        )
    finally:
        vault_head_mod.load_latest_research_intelligence = original
    assert result["state"] == "latest_read_failed"
    assert result["error_code"] == "artifact_read_failed"
    assert counter["n"] == 0


def _load_cli():
    path = Path(__file__).resolve().parents[1] / "scripts" / "research_intelligence_vault_head.py"
    spec = importlib.util.spec_from_file_location("research_intelligence_vault_head_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _publish_catalog(store):
    catalog = catalog_mod.empty()
    catalog_mod.upsert_item(catalog, ITEM)
    published = catalog_mod.publish(store, catalog, now=datetime.now(timezone.utc))
    assert published.published


def test_t13_results_and_cli_streams_omit_body_and_quote(tmp_path, capsys, monkeypatch):
    """T13 pin: no result dict or CLI stream contains the body token or the RIO quote."""
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store, pdf=b"%PDF-1.4\n" + BODY_TOKEN.encode("ascii") + b"\n")
    result = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        text_provider=_provider(lambda _pdf: BODY),
    )
    assert result["state"] == "persisted"
    _assert_no_private_text(result)

    cli_store = LocalStore(tmp_path / "cli")
    _publish_catalog(cli_store)
    _seed_pdf(cli_store, pdf=b"%PDF-1.4\n" + BODY_TOKEN.encode("ascii") + b"\n")
    bounded_reads = []
    original_bounded = LocalStore.get_bytes_strict_bounded

    def spy_bounded(self, key, *args, **kwargs):
        bounded_reads.append(key)
        return original_bounded(self, key, *args, **kwargs)

    monkeypatch.setattr(LocalStore, "get_bytes_strict_bounded", spy_bounded)
    model_calls = {"n": 0}

    def forbid_model(*_args, **_kwargs):
        model_calls["n"] += 1
        raise AssertionError("selection-only must not call a model")

    monkeypatch.setattr(
        "engine.research_intelligence.extractor._default_call",
        forbid_model,
    )
    cli = _load_cli()
    code = cli.main(
        [
            "--model",
            "fixture-model-a",
            "--local",
            str(cli_store.root),
            "--selection-only",
            "--as-of",
            "2026-09-18",
            "--config",
            str(Path(__file__).resolve().parents[1] / "config" / "press.yml"),
            "--limit",
            "1",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert model_calls["n"] == 0
    assert not any(str(key).endswith(".pdf") for key in bounded_reads)
    combined = captured.out + captured.err
    assert BODY_TOKEN not in combined
    assert QUOTE not in combined
    assert "quote_span" not in combined


def test_t14_text_provider_injection_is_used_and_extractor_is_not(tmp_path, monkeypatch):
    """T14 pin: an injected ok record is what W1 receives, and the canonical extractor is not called."""
    store = LocalStore(tmp_path / "vault")
    token = "ZZF9INJECTEDBODYZZ"
    text = CLAIM + " " + token + " stays in the injected record."
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    pdf_sha = hashlib.sha256(b"injected-not-a-file").hexdigest()
    used = {"provider": 0}

    def provider(store_arg, report_id, *, pdf_max_bytes, body_max_bytes, expected_pdf_sha256=None):
        used["provider"] += 1
        assert expected_pdf_sha256 is None
        return {
            "state": "ok",
            "report_id": report_id,
            "body": text,
            "body_bytes": len(text.encode("utf-8")),
            "source_pdf_sha256": pdf_sha,
            "extracted_text_sha256": text_sha,
            "text_layer_state": "full",
            "page_count": 2,
            "extractor_name": "pdftotext",
            "extractor_version": "research_vault.ingest.extract_pdf_text.v1",
        }

    def explode_reader(*_args, **_kwargs):
        raise AssertionError("injected text_provider must replace read_canonical_text")

    def explode_extractor(*_args, **_kwargs):
        raise AssertionError("extractor must not run when text_provider is injected")

    monkeypatch.setattr(vault_head_mod, "read_canonical_text", explode_reader)
    monkeypatch.setattr(vault_head_mod, "extract_pdf_text", explode_extractor)
    counter = {"n": 0, "user": ""}
    result = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_counting_call(counter),
        text_provider=provider,
    )
    assert used["provider"] == 1
    assert result["state"] == "persisted"
    assert token in counter["user"]
    assert result["source_pdf_sha256"] == pdf_sha
    assert result["extracted_text_sha256"] == text_sha
    stored = load_latest_research_intelligence(store, REPORT_ID)
    assert stored is not None
    assert stored.source_content_sha256 == text_sha
    assert token not in _dump(result)
