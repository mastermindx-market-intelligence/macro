"""Executable spec for the current-pinned Research Vault browser read API.

Target: ``GET /api/research/read/{doc_id}`` (NEW route on ``app.research.router``).

These tests are the test-first contract for revision-pinned browser reads. They
run against a HERMETIC FastAPI app that mounts ``app.research.router`` with:

  * ``require_user`` replaced via ``app.dependency_overrides`` (no Supabase, no
    auth-policy change — the real dependency is never invoked);
  * the server module's ``_resolve_tier`` / ``_load_catalog`` / ``_build_store``
    monkeypatched;
  * the incumbent ``view_ratelimit.allow`` monkeypatched (consulted, never
    file-backed);
  * a fake PRIVATE store exposing only ``get_bytes_strict_bounded`` (the one
    method ``fulltext_store`` reads through) — no live R2 ever.

Derivatives are REAL: ``fulltext.build_extracted_text`` records encoded with
``fulltext_store.encode_record`` and seeded at the canonical receipt/derivative
keys, so every served segment must be a canonical ``fulltext.build_segments``
record of that same stored record.

Contract under test (red-team framing):

  * gates in order: 401 auth → 402 non-pro (before ANY store read) →
    400/404 doc validation (before any content read) → 429 rate limit → store;
  * optional pins ``source_pdf_sha256`` + ``extracted_text_sha256`` occur
    together, are lower hex64, and ``segment_start > 0`` requires both;
  * ``segment_start`` >= 0; ``max_segments`` in 1..4 (default 2), slicing the
    canonical segment list (segment_max_bytes fixed at 4000);
  * unpinned reads intentionally open the CURRENT revision; a pinned reopen of
    an unchanged revision replays byte-identically; a stale pin NEVER silently
    substitutes the latest revision — it refuses 409
    ``selected_revision_unavailable`` without leaking the newer text;
  * missing receipt / missing or corrupt or mismatched derivative → 503
    ``research text unavailable`` with no internal details; incumbent
    ``fulltext_store.EXTRACTOR_VERSION`` only (a v2-stamped object is unreadable);
  * a correction landing between the receipt read and the current-source
    recheck refuses with a safe error envelope — source text is never served;
  * ``text_layer_state`` is served honestly (``none`` → zero segments,
    ``thin`` → verbatim short text, ``unavailable`` is never served as text).

Future historical access is intentionally NOT tested: a stale pin must refuse,
so there is no assertion that an old revision stays retrievable.

Requires fastapi + httpx (TestClient); skips cleanly if either is absent.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import pytest

pytest.importorskip("fastapi", reason="browser-read contract tests need fastapi")
pytest.importorskip("httpx", reason="TestClient needs httpx")

from fastapi import FastAPI, Header, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _repo_root() -> Path:
    """Locate the repo root (the directory holding ``app/research.py``)."""
    seen: list[Path] = [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
    seen += [Path(p) for p in sys.path if p]
    seen.append(Path.cwd())
    for cand in seen:
        try:
            if (cand / "app" / "research.py").is_file():
                return cand
        except OSError:  # pragma: no cover - unreadable path entries
            continue
    raise RuntimeError("repo root with app/research.py not found; run from the repo")


ROOT = _repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import research as research_mod  # noqa: E402
from engine.research_vault import fulltext  # noqa: E402
from engine.research_vault import fulltext_store  # noqa: E402


# ===========================================================================
# hermetic fixtures
# ===========================================================================

_DOC_ID = "bernstein-2026-07-21-dc-pipeline"
_DOC_ID_OTHER = "msci-2026-08-04-grid-capex"
_UNKNOWN_ID = "goldman-2026-01-01-not-ingested"

_PDF_V1 = b"%PDF-1.4\nrevision-one original vault pdf bytes\n%%EOF\n"
_PDF_V2 = b"%PDF-1.7\nrevision-two corrected vault pdf bytes\n%%EOF\n"

_CATALOG_GENERATED_AT = "2026-10-20T06:00:00Z"
_READ_SCHEMA = "research_vault.browser_read.v1"
_SEGMENT_MAX_BYTES = 4000  # frozen by the read contract
_AUTH = {"Authorization": "Bearer stub-token"}

# Body/detail tokens that must never leak out of a 503.
_FORBIDDEN_DETAIL = (
    "research_inbox",
    "fulltext/v1",
    "traceback",
    "boto",
    "fakeprivatestore",
    "r2_",
    ".pdf",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rev_text(label: str) -> str:
    """Multi-segment revision text (~28 KB → >4 segments at 4000 bytes)."""
    unit = f"Revision {label} payload sentence for the browser reader. "
    return unit * 500 + f"Terminal {label} paragraph with naïve résumé and straße characters."


def _catalog(*doc_ids: str) -> dict:
    """Planted ``_load_catalog`` return: items + the health projection."""
    return {
        "schema": "research_vault.catalog.v1",
        "generated_at": _CATALOG_GENERATED_AT,
        "count": len(doc_ids),
        "items": [
            {
                "id": doc_id,
                "title": f"Desk note {doc_id}",
                "institution": "Bernstein",
                "side": "sell",
                "published_at": "2026-10-20T00:00:00Z",
                "summary_points": ["catalog summary"],
            }
            for doc_id in doc_ids
        ],
        "catalog_health": {
            "state": "fresh",
            "generated_at": _CATALOG_GENERATED_AT,
            "age_seconds": 30,
            "reason": "",
        },
        "stale": False,
    }


class FakePrivateStore:
    """Test double for the PRIVATE bucket: exactly the reader the server uses.

    ``fulltext_store`` reads strictly through ``get_bytes_strict_bounded`` and
    nothing else, so this double implements ONLY that method (plus test-side
    ``seed``). Oversized objects read as absent, mirroring the bounded read.
    """

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self.read_keys: list[str] = []

    def seed(self, key: str, blob: bytes) -> None:
        self._objects[key] = blob

    def get_bytes_strict_bounded(self, key, max_bytes):
        self.read_keys.append(key)
        blob = self._objects.get(key)
        if blob is None or len(blob) > max_bytes:
            return None
        return blob

    @property
    def read_count(self) -> int:
        return len(self.read_keys)


class CorrectionRaceStore(FakePrivateStore):
    """Receipt that flips to the corrected digest only AFTER the old derivative.

    Models a correction landing in the window between the endpoint's derivative
    load (bound to the old receipt digest) and its current-source recheck: every
    receipt read before the old-revision derivative is bound still reports the
    old digest (so the load itself stays self-consistent), and every receipt
    read after that reports the corrected one. An endpoint that never rechecks
    never sees the drift; one that rechecks must refuse.
    """

    def __init__(self, receipt_key: str, derivative_key: str, corrected_receipt: bytes) -> None:
        super().__init__()
        self._receipt_key = receipt_key
        self._derivative_key = derivative_key
        self._corrected_receipt = corrected_receipt
        self._derivative_bound = False

    def get_bytes_strict_bounded(self, key, max_bytes):
        if key == self._derivative_key:
            self._derivative_bound = True
            return super().get_bytes_strict_bounded(key, max_bytes)
        if key == self._receipt_key and self._derivative_bound:
            self.read_keys.append(key)
            if len(self._corrected_receipt) > max_bytes:
                return None
            return self._corrected_receipt
        return super().get_bytes_strict_bounded(key, max_bytes)


def _build_record(doc_id: str, *, text: str | None, layer: str, pdf: bytes) -> dict:
    """Real canonical derivative record bound to ``pdf``'s identity."""
    return fulltext.build_extracted_text(
        report_id=doc_id,
        source_pdf_sha256=_sha(pdf),
        text=text,
        extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION,
        page_count=None,
        text_layer_state=layer,
    )


def _receipt_bytes(doc_id: str, source_pdf_sha256: str) -> bytes:
    return json.dumps(
        {"id": doc_id, "content_sha256": source_pdf_sha256}, separators=(",", ":")
    ).encode("utf-8")


def _seed_revision(store: FakePrivateStore, doc_id: str, *, text, layer="full", pdf=_PDF_V1) -> dict:
    """Publish one revision: ingest receipt + revision-bound derivative."""
    rec = _build_record(doc_id, text=text, layer=layer, pdf=pdf)
    store.seed(fulltext_store.receipt_key(doc_id), _receipt_bytes(doc_id, rec["source_pdf_sha256"]))
    store.seed(
        fulltext_store.derivative_key(
            doc_id, rec["source_pdf_sha256"],
            extractor_version=fulltext_store.EXTRACTOR_VERSION,
        ),
        fulltext_store.encode_record(rec),
    )
    return rec


def _get(client, doc_id: str = _DOC_ID, **params):
    return client.get(f"/api/research/read/{doc_id}", headers=_AUTH, params=params or None)


def _pinned_params(selection: dict) -> dict:
    return {
        "source_pdf_sha256": selection["source_pdf_sha256"],
        "extracted_text_sha256": selection["extracted_text_sha256"],
    }


def _header_tokens(response, name: str) -> set[str]:
    return {part.strip().lower() for part in response.headers.get(name, "").split(",") if part.strip()}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Hermetic read API: mounted router, stubbed auth/tier/catalog/limiter/store."""
    # Isolate any incidental file-backed state (the limiter is patched anyway).
    monkeypatch.setenv("MACRO_API_STATE_DIR", str(tmp_path / "state"))

    store = FakePrivateStore()
    catalog = _catalog(_DOC_ID, _DOC_ID_OTHER)
    ctl = {
        "tier": "pro",
        "rate_limited": False,
        "user": {"id": "u-test", "email": "buyer@example.com"},
    }
    allow_calls: list[tuple] = []

    monkeypatch.setattr(research_mod, "_build_store", lambda: store)
    monkeypatch.setattr(research_mod, "_load_catalog", lambda: catalog)
    monkeypatch.setattr(research_mod, "_resolve_tier", lambda user_id: ctl["tier"])

    def _fake_allow(user_id, ip, *args, **kwargs):
        allow_calls.append((user_id, ip))
        if ctl["rate_limited"]:
            return False, {"limit": 30, "remaining": 0}
        return True, {"limit": 30, "remaining": 29}

    monkeypatch.setattr(research_mod.view_ratelimit, "allow", _fake_allow)

    def _stub_require_user(authorization: str | None = Header(default=None)) -> dict:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token")
        return dict(ctl["user"])

    app = FastAPI()
    app.include_router(research_mod.router)
    app.dependency_overrides[research_mod.require_user] = _stub_require_user

    def _set_store(new_store) -> None:
        monkeypatch.setattr(research_mod, "_build_store", lambda: new_store)

    return SimpleNamespace(
        client=TestClient(app),
        store=store,
        catalog=catalog,
        ctl=ctl,
        allow_calls=allow_calls,
        set_store=_set_store,
    )


# ===========================================================================
# gate ordering — auth → tier → doc validation → rate limit → store
# ===========================================================================


class TestGateOrdering:
    def test_missing_bearer_is_401_and_touches_nothing(self, env):
        r = env.client.get(f"/api/research/read/{_DOC_ID}")
        assert r.status_code == 401
        assert env.store.read_count == 0
        assert env.allow_calls == []

    @pytest.mark.parametrize("tier", ["free", "essential"])
    def test_non_pro_tier_is_402_before_any_store_read(self, env, tier):
        env.ctl["tier"] = tier
        r = _get(env.client)
        assert r.status_code == 402
        assert r.json()["error"] == "paid_required"
        assert env.store.read_count == 0
        assert env.allow_calls == []

    def test_tier_gate_precedes_doc_existence(self, env):
        env.ctl["tier"] = "free"
        r = _get(env.client, _UNKNOWN_ID)
        assert r.status_code == 402
        assert env.store.read_count == 0

    def test_revoked_entitlement_blocks_a_previously_selected_revision(self, env):
        _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        selected = _get(env.client).json()["selection"]
        reads_before = env.store.read_count
        env.ctl["tier"] = "free"
        response = _get(env.client, **_pinned_params(selected))
        assert response.status_code == 402
        assert env.store.read_count == reads_before

    def test_catalog_retraction_during_composition_exposes_no_source_body(self, env, monkeypatch):
        _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        calls = 0

        def catalog():
            nonlocal calls
            calls += 1
            return env.catalog if calls == 1 else {**env.catalog, "items": []}

        monkeypatch.setattr(research_mod, "_load_catalog", catalog)
        response = _get(env.client)
        assert response.status_code == 404
        assert response.json() == {"error": "document not found"}
        assert _rev_text("one")[:80] not in response.text

    def test_unknown_doc_is_404_without_any_content_read(self, env):
        r = _get(env.client, _UNKNOWN_ID)
        assert r.status_code == 404
        assert env.store.read_count == 0

    @pytest.mark.parametrize(
        "bad",
        [
            "Bad-Upper",
            "has_underscore",
            "-leads-hyphen",
            "a" * 150,
            quote(f"{_DOC_ID}\n", safe=""),  # \Z anchor: trailing newline never clears
        ],
    )
    def test_malformed_doc_id_is_400_without_any_content_read(self, env, bad):
        r = env.client.get(f"/api/research/read/{bad}", headers=_AUTH)
        assert r.status_code == 400
        assert env.store.read_count == 0

    def test_rate_limited_429_before_any_store_read(self, env):
        env.ctl["rate_limited"] = True
        r = _get(env.client)
        assert r.status_code == 429
        assert r.json()["error"] == "rate_limited"
        assert len(env.allow_calls) == 1  # the incumbent limiter was consulted
        assert env.store.read_count == 0


# ===========================================================================
# selection + pagination parameter contract
# ===========================================================================


class TestParameterContract:
    def test_pins_must_occur_together(self, env):
        rec = _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        r_src = _get(env.client, source_pdf_sha256=rec["source_pdf_sha256"])
        r_txt = _get(env.client, extracted_text_sha256=rec["extracted_text_sha256"])
        assert r_src.status_code == 400
        assert r_txt.status_code == 400

    @pytest.mark.parametrize(
        "src,txt",
        [
            ("A" * 64, "b" * 64),  # uppercase hex is not lower hex64
            ("a" * 63, "b" * 64),  # short
            ("z" * 64, "b" * 64),  # non-hex
            ("a" * 64, "B" * 64),  # uppercase text pin
        ],
    )
    def test_pin_format_enforced_lower_hex64(self, env, src, txt):
        _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        r = _get(env.client, source_pdf_sha256=src, extracted_text_sha256=txt)
        assert r.status_code == 400

    def test_segment_start_must_be_nonnegative(self, env):
        _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        # FastAPI's declared query bounds reject before the handler/store.
        assert _get(env.client, segment_start=-1).status_code == 422
        assert env.store.read_count == 0

    @pytest.mark.parametrize("max_segments", [0, 5])
    def test_max_segments_bounds(self, env, max_segments):
        _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        r = _get(env.client, max_segments=max_segments)
        assert r.status_code == 422
        assert env.store.read_count == 0

    def test_segment_start_requires_both_pins(self, env):
        _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        r = _get(env.client, segment_start=1)
        assert r.status_code == 400

    def test_max_segments_accepted_bounds_slice_the_window(self, env):
        rec = _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        body1 = _get(env.client, max_segments=1).json()
        body4 = _get(env.client, max_segments=4).json()
        assert len(body1["segments"]) == 1
        assert body4["segment_count_total"] >= 4
        assert len(body4["segments"]) == 4
        # both windows are prefixes of the canonical segment list
        expected = fulltext.build_segments(
            rec,
            segmenter_version=body4["selection"]["segmenter_version"],
            max_bytes=_SEGMENT_MAX_BYTES,
        )
        assert [s["segment_index"] for s in body1["segments"]] == [0]
        assert [s["segment_index"] for s in body4["segments"]] == [0, 1, 2, 3]
        assert body4["segments"][-1]["end_byte"] == expected[3]["end_byte"]


# ===========================================================================
# unpinned selection — the current revision, canonically segmented
# ===========================================================================


class TestUnpinnedSelection:
    def test_envelope_contract_and_headers(self, env):
        rec = _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        r = _get(env.client)
        assert r.status_code == 200
        assert _header_tokens(r, "Cache-Control") == {"private", "no-store"}
        assert _header_tokens(r, "X-Robots-Tag") == {"noindex", "noimageindex"}

        body = r.json()
        assert body["schema"] == _READ_SCHEMA
        assert body["report_id"] == _DOC_ID

        sel = body["selection"]
        assert sel["source_pdf_sha256"] == rec["source_pdf_sha256"]
        assert sel["extracted_text_sha256"] == rec["extracted_text_sha256"]
        assert sel["extractor_version"] == fulltext_store.EXTRACTOR_VERSION
        assert sel["segmenter_version"] == fulltext.SEGMENTER_VERSION
        assert sel["segment_max_bytes"] == _SEGMENT_MAX_BYTES

        assert body["source"]["catalog_generated_at"] == _CATALOG_GENERATED_AT
        assert body["source"]["catalog_health"] == env.catalog["catalog_health"]

        assert body["text_layer_state"] == "full"
        assert body["segment_count_total"] >= 4
        assert len(body["segments"]) == min(2, body["segment_count_total"])  # default

        # the read went through the canonical receipt → incumbent derivative path
        assert env.store.read_keys[0] == fulltext_store.receipt_key(_DOC_ID)
        assert (
            fulltext_store.derivative_key(_DOC_ID, rec["source_pdf_sha256"])
            in env.store.read_keys
        )

    def test_segments_are_canonical_records_of_the_selected_record(self, env):
        rec = _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        body = _get(env.client).json()

        expected = fulltext.build_segments(
            rec,
            segmenter_version=body["selection"]["segmenter_version"],
            max_bytes=body["selection"]["segment_max_bytes"],
        )
        assert body["segment_count_total"] == len(expected)
        for served, want in zip(body["segments"], expected):
            for key, value in want.items():
                assert served[key] == value, f"segment field {key} is not canonical"

        # selection identity is bound to the SAME real record as the segments
        first = body["segments"][0]
        assert body["selection"]["source_pdf_sha256"] == first["source_pdf_sha256"]
        assert body["selection"]["source_pdf_sha256"] == rec["source_pdf_sha256"]
        assert body["selection"]["extracted_text_sha256"] == first["extracted_text_sha256"]
        assert body["selection"]["extracted_text_sha256"] == rec["extracted_text_sha256"]
        assert body["selection"]["extractor_version"] == first["extractor_version"]


# ===========================================================================
# pinned reopen — unchanged replays, stale refuses, unpinned opens the new
# ===========================================================================


class TestPinnedReopen:
    def test_unchanged_revision_reopens_with_identical_window(self, env):
        _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        first = _get(env.client)
        assert first.status_code == 200
        b1 = first.json()

        again = _get(env.client, **_pinned_params(b1["selection"]))
        assert again.status_code == 200
        b2 = again.json()
        assert b2["schema"] == _READ_SCHEMA
        assert b2["selection"] == b1["selection"]
        assert b2["segments"] == b1["segments"]
        assert b2["segment_count_total"] == b1["segment_count_total"]

    def test_stale_pin_rejected_409_without_leaking_the_newer_revision(self, env):
        rec1 = _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        sel1 = _get(env.client).json()["selection"]

        rec2 = _seed_revision(env.store, _DOC_ID, text=_rev_text("two"), pdf=_PDF_V2)
        assert rec2["source_pdf_sha256"] != rec1["source_pdf_sha256"]

        r = _get(env.client, **_pinned_params(sel1))
        assert r.status_code == 409
        data = r.json()
        assert data["error"] == "selected_revision_unavailable"
        assert data["report_id"] == _DOC_ID
        # the refusal must not serve the LATEST revision either
        served = r.text
        assert _rev_text("two")[:80] not in served
        assert rec2["source_pdf_sha256"] not in served
        assert _rev_text("one")[:80] not in served
        assert "segments" not in data
        assert "selection" not in data

    def test_mismatched_text_pin_is_refused_409(self, env):
        rec = _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        r = _get(
            env.client,
            source_pdf_sha256=rec["source_pdf_sha256"],
            extracted_text_sha256="0" * 64,
        )
        assert r.status_code == 409
        data = r.json()
        assert data["error"] == "selected_revision_unavailable"
        assert data["report_id"] == _DOC_ID

    def test_unpinned_read_intentionally_opens_the_newer_revision(self, env):
        rec1 = _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        sel1 = _get(env.client).json()["selection"]

        rec2 = _seed_revision(env.store, _DOC_ID, text=_rev_text("two"), pdf=_PDF_V2)
        body = _get(env.client).json()

        assert body["schema"] == _READ_SCHEMA
        assert body["selection"]["source_pdf_sha256"] == rec2["source_pdf_sha256"]
        assert body["selection"]["extracted_text_sha256"] == rec2["extracted_text_sha256"]
        assert body["selection"] != sel1
        assert body["segments"][0]["text"].startswith("Revision two payload sentence")
        assert rec1["extracted_text_sha256"] != rec2["extracted_text_sha256"]


# ===========================================================================
# derivative availability — 503 without internal details
# ===========================================================================


class TestDerivativeAvailability:
    def _assert_unavailable(self, r: TestClient.response) -> dict:  # type: ignore[valid-type]
        assert r.status_code == 503
        data = r.json()
        assert data["error"] == "research text unavailable"
        low = r.text.lower()
        for token in _FORBIDDEN_DETAIL:
            assert token not in low, f"internal detail leaked: {token}"
        return data

    def test_missing_receipt_is_503(self, env):
        # doc is in the catalog but the vault holds nothing for it
        r = _get(env.client)
        data = self._assert_unavailable(r)
        assert env.store.read_count >= 1  # the receipt read itself happened
        assert data == {"error": "research text unavailable"} or set(data) == {"error"}

    def test_receipt_without_derivative_is_503(self, env):
        rec = _build_record(_DOC_ID, text=_rev_text("one"), layer="full", pdf=_PDF_V1)
        env.store.seed(
            fulltext_store.receipt_key(_DOC_ID),
            _receipt_bytes(_DOC_ID, rec["source_pdf_sha256"]),
        )
        self._assert_unavailable(_get(env.client))

    @pytest.mark.parametrize(
        "receipt",
        [
            b"{broken json",
            json.dumps({"id": "x", "other": "y"}).encode("utf-8"),  # no digest
            json.dumps({"id": "other-doc", "content_sha256": "a" * 64}).encode("utf-8"),
        ],
    )
    def test_unreadable_receipt_is_503(self, env, receipt):
        env.store.seed(fulltext_store.receipt_key(_DOC_ID), receipt)
        self._assert_unavailable(_get(env.client))

    @pytest.mark.parametrize(
        "label, blob_for",
        [
            ("garbage", lambda rec: b"not json at all"),
            (
                "wrong_schema",
                lambda rec: json.dumps(dict(rec, schema="research_vault.extracted_text.v9")).encode("utf-8"),
            ),
            (
                "tampered_text",
                lambda rec: json.dumps(dict(rec, text=rec["text"] + " smuggled tail")).encode("utf-8"),
            ),
            (
                "v2_extractor_record",
                lambda rec: json.dumps(
                    dict(rec, extractor_version=fulltext.EXTRACTOR_VERSION_READING_ORDER_V2)
                ).encode("utf-8"),
            ),
        ],
    )
    def test_corrupt_or_foreign_derivative_is_503(self, env, label, blob_for):
        rec = _seed_revision(env.store, _DOC_ID, text=_rev_text("one"))
        env.store.seed(
            fulltext_store.derivative_key(
                _DOC_ID, rec["source_pdf_sha256"],
                extractor_version=fulltext_store.EXTRACTOR_VERSION,
            ),
            blob_for(rec),
        )
        self._assert_unavailable(_get(env.client))

    def test_revision_mismatched_derivative_is_503(self, env):
        """Receipt names revision 1 but the object at that key binds revision 2."""
        rec_other = _build_record(_DOC_ID, text=_rev_text("two"), layer="full", pdf=_PDF_V2)
        env.store.seed(
            fulltext_store.receipt_key(_DOC_ID),
            _receipt_bytes(_DOC_ID, _sha(_PDF_V1)),
        )
        env.store.seed(
            fulltext_store.derivative_key(
                _DOC_ID, _sha(_PDF_V1),
                extractor_version=fulltext_store.EXTRACTOR_VERSION,
            ),
            fulltext_store.encode_record(rec_other),
        )
        self._assert_unavailable(_get(env.client))

    @pytest.mark.parametrize("pinned", [False, True])
    def test_correction_race_refuses_without_source_body(self, env, pinned):
        rec1 = _build_record(_DOC_ID, text=_rev_text("one"), layer="full", pdf=_PDF_V1)
        rec2 = _build_record(_DOC_ID, text=_rev_text("two"), layer="full", pdf=_PDF_V2)
        receipt_key = fulltext_store.receipt_key(_DOC_ID)
        deriv1_key = fulltext_store.derivative_key(
            _DOC_ID, rec1["source_pdf_sha256"],
            extractor_version=fulltext_store.EXTRACTOR_VERSION,
        )

        race = CorrectionRaceStore(
            receipt_key, deriv1_key, _receipt_bytes(_DOC_ID, rec2["source_pdf_sha256"])
        )
        race.seed(receipt_key, _receipt_bytes(_DOC_ID, rec1["source_pdf_sha256"]))
        race.seed(deriv1_key, fulltext_store.encode_record(rec1))
        # the corrected revision is fully published too — serving ANY of it on
        # this read would still violate the refuse-on-race contract
        race.seed(
            fulltext_store.derivative_key(
                _DOC_ID, rec2["source_pdf_sha256"],
                extractor_version=fulltext_store.EXTRACTOR_VERSION,
            ),
            fulltext_store.encode_record(rec2),
        )
        env.set_store(race)

        params = _pinned_params(rec1) if pinned else {}
        r = _get(env.client, **params)

        # Initial selection has no pin to discard; only pinned continuation is409.
        assert r.status_code == (409 if pinned else 503)
        assert r.json() == (
            {"error": "selected_revision_unavailable", "report_id": _DOC_ID}
            if pinned else {"error": "research text unavailable"}
        )
        assert "no-store" in _header_tokens(r, "cache-control")
        assert _rev_text("one")[:80] not in r.text
        assert _rev_text("two")[:80] not in r.text
        # the recheck really re-read the receipt after binding the derivative
        assert race.read_keys.count(receipt_key) >= 2


# ===========================================================================
# honest text-layer labels
# ===========================================================================


class TestLayerLabels:
    def test_none_layer_reports_zero_segments_honestly(self, env):
        rec = _seed_revision(env.store, _DOC_ID, text="", layer="none")
        r = _get(env.client)
        assert r.status_code == 200
        body = r.json()
        assert body["schema"] == _READ_SCHEMA
        assert body["text_layer_state"] == "none"
        assert body["segment_count_total"] == 0
        assert body["segments"] == []
        assert body["selection"]["source_pdf_sha256"] == rec["source_pdf_sha256"]
        assert body["selection"]["extracted_text_sha256"] == rec["extracted_text_sha256"]

    def test_thin_layer_label_is_served_verbatim(self, env):
        thin_text = "Short thin-layer teaser text for the vault."
        _seed_revision(env.store, _DOC_ID, text=thin_text, layer="thin")
        body = _get(env.client).json()
        assert body["text_layer_state"] == "thin"
        assert body["segment_count_total"] == 1
        assert body["segments"][0]["text"] == thin_text

    def test_unavailable_layer_is_never_served_as_text(self, env):
        # the reader's layer vocabulary is {full, thin, none}: a derivative whose
        # extraction was unavailable is unreadable, so the API must refuse rather
        # than fabricate an empty-text success.
        _seed_revision(env.store, _DOC_ID, text=None, layer="unavailable")
        r = _get(env.client)
        assert r.status_code == 503
        assert r.json()["error"] == "research text unavailable"
