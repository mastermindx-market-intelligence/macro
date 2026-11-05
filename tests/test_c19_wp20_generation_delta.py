"""C19-WP20 offline pins for company-intelligence generation semantics.

Everything here is deterministic: fixed inputs, a fixed ``as_of``, the ``tmp_path``
fixture and no network, wall clock or randomness.  Generation ids are content
hashes, so no test hard-codes one.
"""

import hashlib, json
from pathlib import Path

import pytest

from engine.company_intelligence.contracts import ContractError, canonical_json_bytes
from engine.company_intelligence.views import build_bundle, write_generation
from scripts.publish_company_intelligence_r2 import publish
from tests.test_publish_company_intelligence_r2 import _FakeR2

AS_OF = "2026-02-02"
TICKERS = ("AAPL", "MSFT")


def _rows(msft_sentiment: float) -> list[dict]:
    """One history row per ticker; AAPL is fixed, MSFT carries the component delta."""
    rows = []
    for ticker in TICKERS:
        sentiment = 0.2 if ticker == "AAPL" else msft_sentiment
        rows.append({
            "document_ticker": ticker,
            "fiscal_year": 2026,
            "fiscal_quarter": 1,
            "call_date": "2026-01-29",
            "updated_at": "2026-02-01T00:00:00Z",
            "earnings_call_sent": sentiment,
            "earnings_call_perf": sentiment / 2,
            "management_confidence_score": sentiment + 0.1,
            "earnings_call_combined": sentiment / 3,
            "level1_tags": "demand",
            "positive_highlights": "demand held; services grew; ignored fourth",
            "negative_highlights": "fx headwind",
            "raw_source_url": "https://example.test/document",
        })
    return rows


TX = {
    "schema": "mastermind.tx-index/v1",
    "generation_id": "t" * 24,
    "documents": [
        {
            "ticker": ticker,
            "fiscal_year": 2026,
            "fiscal_quarter": 1,
            "present": True,
            "source_hash": f"hash-{ticker}",
        }
        for ticker in TICKERS
    ],
}


def _bundle(msft_sentiment: float):
    return build_bundle(_rows(msft_sentiment), tx_index=TX, as_of=AS_OF)


# Generation A: MSFT sentiment 0.3.  Generation B: the same inputs with MSFT
# moved to 0.7, so exactly one company component changed between them.
A = _bundle(0.3)
B = _bundle(0.7)


def _agnostic_digest(ctx) -> str:
    """Component digest that ignores the generation address embedded in every context."""
    return hashlib.sha256(
        canonical_json_bytes({k: v for k, v in ctx.items() if k != "generation_id"})
    ).hexdigest()


def _files(gen_dir: Path) -> dict[str, bytes]:
    return {
        rel: (gen_dir / rel).read_bytes()
        for rel in ("companies/AAPL.json", "companies/MSFT.json", "manifest.json")
    }


def test_build_generation_A_writes_immutable_dir_and_marker(tmp_path: Path) -> None:
    contexts, manifest = A
    generation_id = manifest["generation_id"]

    gen_dir = write_generation(tmp_path, contexts, manifest)

    assert gen_dir == tmp_path / "generations" / generation_id
    for rel in ("companies/AAPL.json", "companies/MSFT.json", "manifest.json"):
        assert (gen_dir / rel).is_file()
    # The mutable root marker is written last with bytes identical to the
    # generation manifest it names.
    root_body = (tmp_path / "manifest.json").read_bytes()
    assert root_body == (gen_dir / "manifest.json").read_bytes()

    receipts = json.loads(root_body)["files"]
    assert set(receipts) == {"companies/AAPL.json", "companies/MSFT.json"}
    for rel, block in receipts.items():
        body = (gen_dir / rel).read_bytes()
        assert block["sha256"] == hashlib.sha256(body).hexdigest()
        assert block["bytes"] == len(body)


def test_generation_B_with_one_changed_company_becomes_current_and_A_remains_byte_reproducible(
    tmp_path: Path,
) -> None:
    contexts_a, manifest_a = A
    dir_a = write_generation(tmp_path, contexts_a, manifest_a)
    snapshot_a = _files(dir_a)

    contexts_b, manifest_b = B
    dir_b = write_generation(tmp_path, contexts_b, manifest_b)

    gid_a, gid_b = manifest_a["generation_id"], manifest_b["generation_id"]
    assert gid_a != gid_b
    assert dir_b == tmp_path / "generations" / gid_b
    root = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert root["generation_id"] == gid_b
    # Promoting B never rewrites the older immutable generation.
    assert _files(dir_a) == snapshot_a

    # A is byte-reproducible in a fresh tree: same address, same bytes.
    rebuild_dir = tmp_path / "rebuild"
    rebuilt_contexts, rebuilt_manifest = _bundle(0.3)
    rebuilt_dir = write_generation(rebuild_dir, rebuilt_contexts, rebuilt_manifest)
    assert rebuilt_manifest["generation_id"] == gid_a
    assert rebuilt_dir == rebuild_dir / "generations" / gid_a
    assert _files(rebuilt_dir) == snapshot_a


def test_republishing_equivalent_inputs_is_a_local_noop_and_an_r2_canonical_noop(
    tmp_path: Path,
) -> None:
    contexts_b, manifest_b = B
    dir_b = write_generation(tmp_path, contexts_b, manifest_b)
    snapshot_b = _files(dir_b)
    root_body = (tmp_path / "manifest.json").read_bytes()

    # Equivalent inputs rebuild to the identical generation and write nothing new.
    rebuilt_contexts, rebuilt_manifest = _bundle(0.7)
    assert rebuilt_manifest["generation_id"] == manifest_b["generation_id"]
    again = write_generation(tmp_path, rebuilt_contexts, rebuilt_manifest)

    assert again == dir_b
    assert _files(dir_b) == snapshot_b
    assert (tmp_path / "manifest.json").read_bytes() == root_body

    # The canonical R2 no-op: the remote root already names this generation.
    fake = _FakeR2(remote_manifest=json.loads(root_body.decode("utf-8")))
    assert publish(tmp_path, s3=fake, bucket="bucket") == 0
    assert fake.puts == []


def test_changed_company_component_visible_via_files_manifest_receipts(tmp_path: Path) -> None:
    contexts_a, manifest_a = A
    dir_a = write_generation(tmp_path, contexts_a, manifest_a)
    contexts_b, manifest_b = B
    dir_b = write_generation(tmp_path, contexts_b, manifest_b)

    receipts_a = json.loads((dir_a / "manifest.json").read_text(encoding="utf-8"))["files"]
    receipts_b = json.loads((dir_b / "manifest.json").read_text(encoding="utf-8"))["files"]
    # Pin the finding: generation_id is embedded in every company context, so BOTH
    # per-file sha256s move — the files receipts are not a component discriminator.
    for rel in ("companies/AAPL.json", "companies/MSFT.json"):
        assert receipts_a[rel]["sha256"] != receipts_b[rel]["sha256"]

    contexts_read_a = {
        ticker: json.loads((dir_a / f"companies/{ticker}.json").read_text(encoding="utf-8"))
        for ticker in TICKERS
    }
    contexts_read_b = {
        ticker: json.loads((dir_b / f"companies/{ticker}.json").read_text(encoding="utf-8"))
        for ticker in TICKERS
    }
    # The unchanged component's digest does not move; the changed one does.
    assert _agnostic_digest(contexts_read_a["AAPL"]) == _agnostic_digest(contexts_read_b["AAPL"])
    assert _agnostic_digest(contexts_read_a["MSFT"]) != _agnostic_digest(contexts_read_b["MSFT"])

    for ticker in TICKERS:
        assert contexts_read_a[ticker]["generation_id"] == manifest_a["generation_id"]
        assert contexts_read_b[ticker]["generation_id"] == manifest_b["generation_id"]


def test_older_generation_remains_loadable_after_a_newer_promotion(tmp_path: Path) -> None:
    contexts_a, manifest_a = A
    dir_a = write_generation(tmp_path, contexts_a, manifest_a)
    gid_a = manifest_a["generation_id"]
    contexts_b, manifest_b = B
    write_generation(tmp_path, contexts_b, manifest_b)

    older = json.loads((tmp_path / "generations" / gid_a / "manifest.json").read_text(encoding="utf-8"))
    assert older["generation_id"] == gid_a
    for rel, block in older["files"].items():
        body = (dir_a / rel).read_bytes()
        assert block["sha256"] == hashlib.sha256(body).hexdigest()
        assert block["bytes"] == len(body)


def test_tampered_immutable_file_rewrite_is_a_hard_collision(tmp_path: Path) -> None:
    contexts_a, manifest_a = A
    dir_a = write_generation(tmp_path, contexts_a, manifest_a)
    company = dir_a / "companies" / "AAPL.json"
    original = company.read_bytes()
    company.write_bytes(original + b" ")

    with pytest.raises(ContractError, match="immutable generation collision"):
        write_generation(tmp_path, *A)

    # The tampered bytes are never silently overwritten by the rewrite attempt.
    assert company.read_bytes() == original + b" "
