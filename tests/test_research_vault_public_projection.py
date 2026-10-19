"""Regression: the internal ``producer_generation`` block never leaves the vault.

``producer_generation`` is an OPTIONAL top-level catalog field carrying internal
production metadata (producer/report cohort ids + content hashes). It must exist
in the canonical private catalog — and in ``summary['catalog_bytes']`` as PUT to
R2 — byte-for-byte, but it must never reach:

  * the authenticated full ``GET /api/research/catalog`` (Pro) response;
  * the anonymous / free / essential preview of that route;
  * any direct ``_catalog_preview`` caller (e.g. the search preview narrowing);
  * the committed repo mirror ``data/research_vault/catalog.json``.

The tests are CAUSAL: each one fails on the unpatched sources for exactly the
reason its name states (the field, or a sentinel buried inside it, is exposed
somewhere public) and passes once the projection strips it. They assert on
observable outputs (returned dicts, mirror bytes) — never on implementation
text — and they pin the invariants that must survive the strip: public field
set/order, preview count + selection, institutions, summaries, deep-equality of
the canonical input, and the legacy no-field byte path.

The actual app.research and scripts.ingest_research modules are imported and
exercised. API dependencies are required; import failures fail the gate. Engine
collaborators are synthetic and no production store is accessed.
RV_PROJECTION_ROOT may identify an isolated artifact composition for review.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(os.environ.get("RV_PROJECTION_ROOT")
            or Path(__file__).resolve().parent.parent)

INTERNAL_FIELD = "producer_generation"

# Distinctive markers planted inside the internal block. If ANY of these reach a
# public surface — as a key, a value, or a serialised fragment — the vault has
# leaked member/report cohort or content-hash metadata.
INTERNAL_SENTINELS = (
    "gen-2026-10-13-INTERNAL",
    "member-7f3a",
    "member-9d21",
    "rv-internal-alpha",
    "deadbeefdeadbeef",
    "INTERNAL ONLY",
)


# ===========================================================================
# shared fixtures — the canonical catalog, with and without the internal field
# ===========================================================================

def _item(i: int, *, points: bool = True, institution: str | None = None) -> dict:
    return {
        "id": f"a-{i:06d}",
        "title": f"Report {i}",
        "institution": institution or f"Inst {i}",
        "published_at": f"2026-10-0{i}T00:00:00Z",
        "summary_points": ["bullet one", "bullet two"] if points else [],
    }


def _internal_block() -> dict:
    """The internal payload: cohort ids + content hashes, never for the public."""
    return {
        "generation": "gen-2026-10-13-INTERNAL",
        "member_cohort": ["member-7f3a", "member-9d21"],
        "report_cohort": ["rv-internal-alpha"],
        "source_sha256": {"a-000001": "deadbeefdeadbeef" * 4},
        "operator_notes": "INTERNAL ONLY — never publish",
    }


def _canonical_catalog(*, with_internal: bool = True) -> dict:
    """A closed v1 catalog: schema/generated_at/count/items (+ optional internal).

    Item 4 carries no summary_points, so the public preview selects items 1-3
    while ``count`` retains the full inventory — the exact selection rule the
    preview must keep while dropping the internal block.
    """
    catalog = {
        "schema": "research_vault.catalog.v1",
        "generated_at": "2026-10-13T04:00:00Z",
        "count": 4,
        "items": [_item(1), _item(2), _item(3), _item(4, points=False)],
    }
    if with_internal:
        catalog[INTERNAL_FIELD] = _internal_block()
    return catalog


def _serialize(doc: dict) -> bytes:
    """The engine's serializer conventions (ensure_ascii=False, indent=2, \\n)."""
    return (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _assert_no_internal(payload) -> str:
    """Serialize ``payload`` and fail if any internal sentinel appears in it."""
    text = json.dumps(payload, ensure_ascii=False, default=repr)
    for token in INTERNAL_SENTINELS:
        assert token not in text, (
            f"internal sentinel {token!r} leaked into a public surface")
    return text


# ===========================================================================
# app.research — actual module OR AST-extracted real source (labelled)
# ===========================================================================

_FAKE_PUBLIC_SUMMARY = {"report_count": 4, "headline": "Café Institute — über report"}


def _fake_catalog_mod() -> types.SimpleNamespace:
    from engine.research_vault import catalog as canonical_catalog
    return types.SimpleNamespace(
        public_summary=lambda cat: dict(_FAKE_PUBLIC_SUMMARY),
        PUBLIC_PREVIEW_COUNT=canonical_catalog.PUBLIC_PREVIEW_COUNT,
        preview_items=canonical_catalog.preview_items,
    )


def _import_actual_research():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app.research as mod
    return mod


@pytest.fixture
def research(monkeypatch):
    """Actual router import is mandatory; import errors fail this API gate."""
    ctl = {"tier": "anon", "catalog": None}
    mod = _import_actual_research()
    monkeypatch.setattr(mod, "catalog_mod", _fake_catalog_mod(), raising=False)

    def _set(name, value):
        monkeypatch.setattr(mod, name, value, raising=False)

    mode = "actual-module"
    route = lambda: mod.research_catalog(authorization="Bearer stub")
    preview = lambda cat, limit=3: mod._catalog_preview(cat, limit)

    handle = SimpleNamespace(mode=mode, ctl=ctl, set=_set, route=route,
                             preview=preview)
    handle.set("_load_catalog", lambda: ctl["catalog"])
    handle.set("_optional_tier", lambda authorization: ctl["tier"])
    return handle


def test_full_pro_catalog_omits_producer_generation(research):
    research.ctl["tier"] = "pro"
    research.ctl["catalog"] = _canonical_catalog()
    body = research.route()
    assert isinstance(body, dict)
    assert INTERNAL_FIELD not in body
    # The full catalog keeps every public field AND the complete item inventory
    # — only the internal block is gone (closed v1 shape, not remapped).
    assert body["preview"] is False
    assert [it["id"] for it in body["items"]] == ["a-000001", "a-000002",
                                                  "a-000003", "a-000004"]
    assert body["count"] == 4
    assert body["summary"] == _FAKE_PUBLIC_SUMMARY
    _assert_no_internal(body)


def test_anonymous_preview_omits_producer_generation(research):
    for tier in ("anon", "free", "essential"):
        research.ctl["tier"] = tier
        research.ctl["catalog"] = _canonical_catalog()
        body = research.route()
        assert INTERNAL_FIELD not in body, f"tier={tier}"
        assert body["preview"] is True
        assert [it["id"] for it in body["items"]] == ["a-000001", "a-000002",
                                                      "a-000003"]
        assert body["count"] == 4
        assert body["institutions"] == ["Inst 1", "Inst 2", "Inst 3"]
        _assert_no_internal(body)


def test_direct_catalog_preview_omits_producer_generation(research):
    """Direct _catalog_preview callers (e.g. the search preview narrowing) too."""
    catalog = _canonical_catalog()
    body = research.preview(catalog)
    assert INTERNAL_FIELD not in body
    _assert_no_internal(body)


def test_internal_sentinels_absent_from_every_catalog_surface(research):
    """Member/report cohort ids and hashes must not survive even nested/serialised."""
    research.ctl["catalog"] = _canonical_catalog()
    for tier in ("pro", "anon"):
        research.ctl["tier"] = tier
        _assert_no_internal(research.route())
    _assert_no_internal(research.preview(research.ctl["catalog"]))


def test_route_does_not_mutate_the_canonical_catalog(research):
    """The private catalog (and its cache) keeps the exact field after serving."""
    research.ctl["catalog"] = _canonical_catalog()
    snapshot = copy.deepcopy(research.ctl["catalog"])
    for tier in ("pro", "anon"):
        research.ctl["tier"] = tier
        research.route()
    assert research.ctl["catalog"] == snapshot, (
        "the canonical catalog object was mutated while serving")
    assert INTERNAL_FIELD in research.ctl["catalog"]
    assert research.ctl["catalog"][INTERNAL_FIELD] == snapshot[INTERNAL_FIELD]


def test_preview_selection_public_fields_and_key_order_unchanged(research):
    """The strip removes ONE key: order of the remaining keys, selection, facets
    and summary are untouched."""
    research.ctl["tier"] = "anon"
    research.ctl["catalog"] = _canonical_catalog()
    body = research.route()
    expected_keys = ["schema", "generated_at", "count", "items",
                     "preview", "summary", "institutions"]
    assert list(body.keys()) == expected_keys
    assert body["schema"] == "research_vault.catalog.v1"
    assert body["generated_at"] == "2026-10-13T04:00:00Z"
    # Item objects are carried through unchanged (no tightening/remapping).
    assert body["items"][0] == _item(1)
    assert body["items"][2] == _item(3)


def test_catalog_without_internal_field_is_served_unchanged(research):
    """Legacy catalog (field absent): nothing added, nothing dropped, no churn."""
    legacy = _canonical_catalog(with_internal=False)
    legacy_keys = list(legacy.keys())

    for tier in ("pro", "anon"):
        research.ctl["tier"] = tier
        research.ctl["catalog"] = copy.deepcopy(legacy)
        body = research.route()
        assert INTERNAL_FIELD not in body
        assert list(body.keys())[:len(legacy_keys)] == legacy_keys, f"tier={tier}"
        for key in legacy_keys:
            if tier != "pro" and key == "items":
                continue  # the preview legitimately narrows items to the newest 3
            assert body[key] == legacy[key], f"tier={tier}, key={key}"
        if tier != "pro":
            assert [it["id"] for it in body["items"]] == \
                [it["id"] for it in legacy["items"]][:3]


# ===========================================================================
# scripts.ingest_research — repo mirror projection (real CLI main, fake engine)
# ===========================================================================

class _FakeStore:
    def __init__(self):
        self.puts = []

    def put_bytes(self, key, data, content_type=None):
        self.puts.append((key, data))


def _install_fake_engine(monkeypatch, summary):
    """Inject an ``engine.research_vault`` whose run() returns ``summary``.

    The CLI executes for real (argparse, the publication gate, the mirror and
    excerpt writes); only the engine pass is faked, exactly enough to hand the
    CLI a controlled ``catalog_bytes``.
    """
    store = _FakeStore()

    def _mod(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        return m

    vault = _mod("engine.research_vault")
    ingest = _mod("engine.research_vault.ingest",
                  run=lambda store_, corpus_path, dry_run=False: summary)
    r2s = _mod("engine.research_vault.r2_store", build_store=lambda local_dir=None: store)
    catalog = _mod("engine.research_vault.catalog", coverage_lines=lambda cov: ([], []))
    excerpt = _mod("engine.research_vault.excerpt",
                   snapshot=lambda conn, ids: [],
                   write_repo_snapshot=lambda rows, path: True)
    vault.ingest = ingest
    vault.r2_store = r2s
    vault.catalog = catalog
    vault.excerpt = excerpt
    engine = _mod("engine", research_vault=vault)
    for name, mod in [("engine", engine),
                      ("engine.research_vault", vault),
                      ("engine.research_vault.ingest", ingest),
                      ("engine.research_vault.r2_store", r2s),
                      ("engine.research_vault.catalog", catalog),
                      ("engine.research_vault.excerpt", excerpt)]:
        monkeypatch.setitem(sys.modules, name, mod)
    return store


def _cli_summary(**over) -> dict:
    base = {
        "ingested": 1, "skipped": 0, "failed": 0, "needs_metadata": 0,
        "corpus_published": True, "catalog_published": True,
        "catalog_state": "fresh",
        "catalog_bytes": _serialize(_canonical_catalog()),
    }
    base.update(over)
    return base


@pytest.fixture()
def cli(monkeypatch, tmp_path):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import scripts.ingest_research as cli_mod  # real CLI source, stdlib-only import

    state = SimpleNamespace(summary=None, store=None,
                            repo_dir=tmp_path / "repo", corpus=tmp_path / "c.sqlite")

    def run(summary, *extra):
        state.summary = summary
        state.store = _install_fake_engine(monkeypatch, summary)
        state.corpus.write_bytes(b"")  # empty corpus file: excerpt step degrades
        monkeypatch.setattr(sys, "argv", [
            "ingest_research", "--local", str(tmp_path / "store"),
            "--corpus", str(state.corpus),
            "--repo-dir", str(state.repo_dir), *extra])
        return cli_mod.main()

    return SimpleNamespace(mod=cli_mod, run=run, state=state)


def test_repo_mirror_strips_field_but_canonical_bytes_keep_it(cli):
    summary = _cli_summary()
    canonical = summary["catalog_bytes"]
    rc = cli.run(summary)
    assert rc == 0
    mirror_path = cli.state.repo_dir / "catalog.json"
    assert mirror_path.is_file()
    mirror = mirror_path.read_bytes()
    # The PUBLIC mirror lost the internal block...
    mirror_doc = json.loads(mirror.decode("utf-8"))
    assert INTERNAL_FIELD not in mirror_doc
    # ...and nothing else: deep-equal to the canonical document minus one key.
    expected = json.loads(canonical.decode("utf-8"))
    expected.pop(INTERNAL_FIELD)
    assert mirror_doc == expected
    # ...while summary['catalog_bytes'] — what was PUT to R2 — kept it verbatim.
    assert summary["catalog_bytes"] == canonical
    assert b"producer_generation" in summary["catalog_bytes"]
    assert (json.loads(summary["catalog_bytes"].decode("utf-8"))[INTERNAL_FIELD]
            == _internal_block())
    _assert_no_internal(mirror_doc)


def test_mirror_keeps_key_order_indent_and_non_ascii(cli):
    """Strip one key; order, ensure_ascii=False and indent=2 + newline survive."""
    doc = _canonical_catalog()
    doc["items"][1]["title"] = "Café Institut — über Sichtweise"  # non-ASCII body
    summary = _cli_summary(catalog_bytes=_serialize(doc))
    assert cli.run(summary) == 0
    text = (cli.state.repo_dir / "catalog.json").read_text(encoding="utf-8")
    assert "Café Institut — über Sichtweise" in text, "ensure_ascii must stay off"
    assert text.endswith("\n")
    assert '\n  "schema"' in text, "indent=2 conventions must be preserved"
    order = [k for k, _ in json.loads(text, object_pairs_hook=lambda pairs: pairs)]
    # Canonical key order minus exactly the internal block — nothing reordered.
    assert order == ["schema", "generated_at", "count", "items"], (
        f"mirror key order churned: {order}")
    assert INTERNAL_FIELD not in text


def test_nested_same_named_item_key_is_catalog_content_and_is_kept(cli):
    """Only the TOP-LEVEL internal block is stripped — an item carrying a
    same-named key is catalog content and must survive the projection."""
    doc = _canonical_catalog()
    doc["items"][0][INTERNAL_FIELD] = {"note": "item-level provenance is public"}
    summary = _cli_summary(catalog_bytes=_serialize(doc))
    assert cli.run(summary) == 0
    mirror = json.loads((cli.state.repo_dir / "catalog.json").read_text("utf-8"))
    assert INTERNAL_FIELD not in mirror
    assert mirror["items"][0][INTERNAL_FIELD] == {
        "note": "item-level provenance is public"}


def test_mirror_without_internal_field_is_byte_identical(cli):
    """Legacy catalog (field absent): the mirror is EXACTLY the input bytes —
    no re-serialisation churn, no whitespace or order drift."""
    canonical = _serialize(_canonical_catalog(with_internal=False))
    summary = _cli_summary(catalog_bytes=canonical)
    assert cli.run(summary) == 0
    mirror = (cli.state.repo_dir / "catalog.json").read_bytes()
    assert mirror == canonical
    assert summary["catalog_bytes"] == canonical


def test_malformed_catalog_bytes_never_advance_the_mirror(cli, caplog):
    """Unparseable canonical bytes: warn, keep the last fully published mirror —
    never fabricate a clean-looking empty output."""
    sentinel = b'{"schema": "research_vault.catalog.v1", "sentinel": true}\n'
    mirror = cli.state.repo_dir / "catalog.json"
    mirror.parent.mkdir(parents=True)
    mirror.write_bytes(sentinel)
    summary = _cli_summary(catalog_bytes=b'{"not json at all')
    with caplog.at_level(logging.WARNING, logger="ingest_research"):
        rc = cli.run(summary)
    assert rc == 0, "a mirror projection failure must not fail the plane"
    assert mirror.read_bytes() == sentinel, "the old mirror must be kept"
    assert any("not valid JSON" in rec.getMessage() or "NOT advanced" in rec.getMessage()
               for rec in caplog.records), "the failure must be LOUD"
    assert summary["catalog_bytes"] == b'{"not json at all'


def test_failed_publication_keeps_the_repo_mirror(cli):
    """Freeze §B preserved: no canonical publish, no mirror advance (strip or not)."""
    sentinel = b'{"sentinel": true}\n'
    mirror = cli.state.repo_dir / "catalog.json"
    mirror.parent.mkdir(parents=True)
    mirror.write_bytes(sentinel)
    summary = _cli_summary(catalog_published=False, error="catalog PUT failed")
    rc = cli.run(summary)
    assert rc == 1
    assert mirror.read_bytes() == sentinel


def test_dry_run_publishes_no_mirror(cli):
    summary = _cli_summary()
    rc = cli.run(summary, "--dry-run")
    assert rc == 0
    assert not (cli.state.repo_dir / "catalog.json").exists()
    assert cli.state.store.puts == [], "--dry-run must publish nothing to the store"
    assert summary["catalog_bytes"].startswith(b"{"), "input bytes untouched"


def test_preview_ids_match_the_app_envelope_and_the_frozen_oracle():
    # Consumer parity belongs to the API suite; keep backend tests app-independent.
    import json
    from app import research as research_app
    from engine.research_vault import catalog as catalog_mod
    from tests.test_research_vault_read_runtime import _preview_catalogs, _catalog_preview
    for catalog in _preview_catalogs():
        new = research_app._catalog_preview(catalog)
        old = _catalog_preview(catalog)
        assert json.dumps(new, sort_keys=True) == json.dumps(old, sort_keys=True)
        got = [
            str((item or {}).get("id") or "")
            for item in new["items"]
        ]
        assert got == catalog_mod.preview_ids(catalog)
        assert new["count"] == len(list(catalog.get("items") or []))
        assert new["preview"] is True
        assert set(new) >= {"items", "count", "preview", "summary", "institutions"}
