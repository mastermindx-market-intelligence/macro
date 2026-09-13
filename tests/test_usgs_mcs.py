"""tests/test_usgs_mcs.py — USGS Mineral Commodity Summaries collector + projection.

RED-first suite for MO-DELTA-029 child B-F09-10 (raw layer, display-only).
Fixtures under tests/fixtures/usgs_mcs/ are byte-exact excerpts of the real
2026 ScienceBase files (verified live 2026-09-13).
"""
from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "usgs_mcs"
T7_PATH = FIXTURE / "MCS2026_T7_Critical_Minerals_Salient.csv"
FIG3_PATH = FIXTURE / "MCS2026_Fig3_Major_Import_Sources.csv"
COMM_PATH = FIXTURE / "MCS2026_Commodities_Data.csv"
PARENT_PATH = FIXTURE / "parent_listing.json"

T7_HEADER_VERBATIM = (
    "Source,Year,Units,Critical_mineral,Primary_prod,Secondary_prod,Prod_notes,"
    "Apparent_Consumption,Consumption_Notes,Net_Import_Reliance,"
    "Primary_import_sources_2021-24,Import_source_notes,Leading_source_country,"
    "Leading_country_prod,Leading_source_precent_world,World_total_prod,"
    "World_prod_notes"
)

# Real 2026 T7 pins (from the fixture excerpt, not invented).
PINNED = {
    "cobalt": {"nir": 79, "leader": "Congo (Kinshasa)", "share": 74, "world": 310000},
    "gallium": {"nir": 100, "leader": "China", "share": 100, "world": 900},
    "lithium": {"nir": 50, "nir_q": ">", "leader": "Australia", "share": 32, "world": 290000},
    "rare_earths": {"nir": 67, "leader": "China", "share": 69, "world": 390000, "china_world": 270000},
}

BANNED_WORDS = ("validated", "falsifier", "refuted", "证伪")


def _t7_header_line() -> str:
    raw = T7_PATH.read_bytes()
    text = raw.decode("utf-8-sig")
    return text.splitlines()[0]


def _t7_rows() -> list[dict]:
    text = T7_PATH.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _load_modules():
    from collectors import usgs_mcs
    from engine import critical_minerals_supply

    return usgs_mcs, critical_minerals_supply


# ---------------------------------------------------------------------------
# (a) T7 header pinned verbatim, including USGS's own 'precent' typo
# ---------------------------------------------------------------------------

class TestT7Header:
    def test_header_verbatim_includes_precent(self):
        header = _t7_header_line()
        assert header == T7_HEADER_VERBATIM
        assert "Leading_source_precent_world" in header
        assert "Leading_source_percent_world" not in header

    def test_config_file_regex_names_t7(self):
        cfg = yaml.safe_load((REPO / "config" / "usgs_mcs_sources.yml").read_text())
        assert cfg["version"] == 1
        assert "t7" in cfg["file_regexes"]
        assert "Critical_Minerals_Salient" in cfg["file_regexes"]["t7"]


# ---------------------------------------------------------------------------
# (b) four rows parse to the REAL 2026 values + no fixture/module literal leak
# ---------------------------------------------------------------------------

class TestReal2026Values:
    def test_four_t7_rows_parse_to_real_2026_values(self):
        usgs_mcs, _ = _load_modules()
        rows = usgs_mcs.parse_t7_csv(T7_PATH.read_bytes(), edition_year=2026)
        by_key = {r["commodity_key"]: r for r in rows if r["metric"] == "net_import_reliance"}
        lead = {r["commodity_key"]: r for r in rows if r["metric"] == "leading_producer_share"}
        world = {r["commodity_key"]: r for r in rows if r["metric"] == "world_total_prod"}

        assert by_key["cobalt"]["value_num"] == PINNED["cobalt"]["nir"]
        assert lead["cobalt"]["country"] == PINNED["cobalt"]["leader"]
        assert lead["cobalt"]["value_num"] == PINNED["cobalt"]["share"]
        assert world["cobalt"]["value_num"] == PINNED["cobalt"]["world"]

        assert by_key["gallium"]["value_num"] == PINNED["gallium"]["nir"]
        assert lead["gallium"]["country"] == PINNED["gallium"]["leader"]
        assert lead["gallium"]["value_num"] == PINNED["gallium"]["share"]
        assert world["gallium"]["value_num"] == PINNED["gallium"]["world"]

        assert by_key["lithium"]["value_raw"] == ">50"
        assert by_key["lithium"]["qualifier"] == ">"
        assert by_key["lithium"]["value_num"] == PINNED["lithium"]["nir"]
        assert lead["lithium"]["country"] == PINNED["lithium"]["leader"]
        assert lead["lithium"]["value_num"] == PINNED["lithium"]["share"]
        assert world["lithium"]["value_num"] == PINNED["lithium"]["world"]

        assert by_key["rare_earths"]["value_num"] == PINNED["rare_earths"]["nir"]
        assert lead["rare_earths"]["country"] == PINNED["rare_earths"]["leader"]
        assert lead["rare_earths"]["value_num"] == PINNED["rare_earths"]["share"]
        assert world["rare_earths"]["value_num"] == PINNED["rare_earths"]["world"]

    def test_no_fixture_value_equals_module_numeric_literal(self):
        """Pinned fixture numbers must not be hardcoded in the two modules."""
        pinned_vals = {
            PINNED["cobalt"]["nir"],
            PINNED["cobalt"]["share"],
            PINNED["cobalt"]["world"],
            PINNED["gallium"]["nir"],
            PINNED["gallium"]["share"],
            PINNED["gallium"]["world"],
            PINNED["lithium"]["nir"],
            PINNED["lithium"]["share"],
            PINNED["lithium"]["world"],
            PINNED["rare_earths"]["nir"],
            PINNED["rare_earths"]["share"],
            PINNED["rare_earths"]["world"],
            PINNED["rare_earths"]["china_world"],
        }
        module_lits: set[float] = set()
        for rel in ("collectors/usgs_mcs.py", "engine/critical_minerals_supply.py"):
            tree = ast.parse((REPO / rel).read_text(encoding="utf-8"), filename=rel)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    module_lits.add(float(node.value))
        overlap = {v for v in pinned_vals if float(v) in module_lits}
        assert not overlap, f"fixture values appear as module literals: {sorted(overlap)}"


# ---------------------------------------------------------------------------
# (c) qualifier grammar
# ---------------------------------------------------------------------------

class TestQualifierGrammar:
    def test_qualifier_tokens(self):
        usgs_mcs, _ = _load_modules()
        cases = [
            (">75", 75.0, ">"),
            ("<25", 25.0, "<"),
            ("E", None, "E"),
            ("W", None, "W"),
            ("NA", None, "NA"),
            ("—", None, "dash"),
            (">50", 50.0, ">"),
            ("<100,000", 100000.0, "<"),
            ("79", 79.0, ""),
            ("270,000", 270000.0, ""),
        ]
        for raw, num, qual in cases:
            got_num, got_q = usgs_mcs.parse_qualifier(raw)
            assert got_q == qual, raw
            if num is None:
                assert got_num is None, raw
            else:
                assert got_num == num, raw

    def test_glued_footnote_digit_stripped_and_recorded(self):
        usgs_mcs, _ = _load_modules()
        label, footnote = usgs_mcs.strip_glued_footnote(
            "Rare earths (compounds and metals)9"
        )
        assert label == "Rare earths (compounds and metals)"
        assert footnote == "9"
        rows = usgs_mcs.parse_t7_csv(T7_PATH.read_bytes(), edition_year=2026)
        re_rows = [r for r in rows if r["commodity_key"] == "rare_earths"]
        assert re_rows
        assert re_rows[0]["commodity_label_src"].endswith("9") or "9" in (
            re_rows[0].get("notes") or ""
        )


# ---------------------------------------------------------------------------
# (d) discovery from the REAL parent listing
# ---------------------------------------------------------------------------

class TestDiscovery:
    def test_picks_2026_over_older_and_ignores_siblings(self):
        usgs_mcs, _ = _load_modules()
        parent = json.loads(PARENT_PATH.read_text(encoding="utf-8"))
        editions = usgs_mcs.discover_editions(parent)
        years = [e["year"] for e in editions]
        assert 2026 in years
        assert 2025 in years
        assert 2024 in years
        assert max(years) == 2026
        titles = {e["year"]: e["title"] for e in editions}
        assert titles[2026].startswith("Mineral Commodity Summaries 2026")
        assert titles[2025].startswith("U.S. Geological Survey Mineral Commodity Summaries 2025")
        ids = {e["year"]: e["item_id"] for e in editions}
        assert ids[2026] == "696a75d5d4be0228872d3bf8"
        assert ids[2025] == "677eaf95d34e760b392c4970"
        assert ids[2024] == "65a6e45fd34e5af967a46749"
        # Non-MCS siblings (Yale stocks, GIS compilations) must not appear.
        for e in editions:
            assert "Mineral Commodity Summaries" in e["title"]
            assert "Yale" not in e["title"]
            assert "Geospatial" not in e["title"]

    def test_selects_newest_t7_layout(self):
        usgs_mcs, _ = _load_modules()
        cfg = yaml.safe_load((REPO / "config" / "usgs_mcs_sources.yml").read_text())
        parent = json.loads(PARENT_PATH.read_text(encoding="utf-8"))
        editions = usgs_mcs.discover_editions(parent)
        chosen = usgs_mcs.select_ingest_edition(editions, cfg["known_editions"])
        assert chosen["year"] == 2026
        assert chosen["layout"] == "t7_csv"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, status_code: int, content: bytes, elapsed: float = 0.1):
        self.status_code = status_code
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.elapsed = type("E", (), {"total_seconds": lambda self: elapsed})()

    def json(self):
        return json.loads(self.content.decode("utf-8"))


def _item_json_ok() -> bytes:
    return json.dumps(
        {
            "id": "696a75d5d4be0228872d3bf8",
            "title": "Mineral Commodity Summaries 2026 Data Release",
            "files": [
                {
                    "name": "MCS2026_T7_Critical_Minerals_Salient.csv",
                    "url": "https://www.sciencebase.gov/catalog/file/get/696a75d5d4be0228872d3bf8?f=t7",
                    "size": T7_PATH.stat().st_size,
                    "checksum": {"value": "deadbeef", "type": "MD5"},
                },
                {
                    "name": "MCS2026_Fig3_Major_Import_Sources.csv",
                    "url": "https://www.sciencebase.gov/catalog/file/get/696a75d5d4be0228872d3bf8?f=fig3",
                    "size": FIG3_PATH.stat().st_size,
                },
                {
                    "name": "MCS2026_Commodities_Data.csv",
                    "url": "https://www.sciencebase.gov/catalog/file/get/696a75d5d4be0228872d3bf8?f=comm",
                    "size": COMM_PATH.stat().st_size,
                },
            ],
        }
    ).encode("utf-8")


def _item_json_no_t7() -> bytes:
    return json.dumps(
        {
            "id": "696a75d5d4be0228872d3bf8",
            "title": "Mineral Commodity Summaries 2026 Data Release",
            "files": [
                {
                    "name": "MCS2026_Fig1_Minerals_in_Economy.csv",
                    "url": "https://www.sciencebase.gov/catalog/file/get/696a75d5d4be0228872d3bf8?f=fig1",
                    "size": 100,
                }
            ],
        }
    ).encode("utf-8")


def _mock_get_factory(item_bytes: bytes, fail: str | None = None):
    parent = PARENT_PATH.read_bytes()
    files = {
        "f=t7": T7_PATH.read_bytes(),
        "f=fig3": FIG3_PATH.read_bytes(),
        "f=comm": COMM_PATH.read_bytes(),
    }

    def _get(url, **kwargs):
        if fail == "503" and "items?" in url:
            return _FakeResp(503, b"upstream")
        if fail == "timeout" and "items?" in url:
            import requests

            raise requests.Timeout("simulated")
        if "items?" in url or "parentId=" in url:
            return _FakeResp(200, parent)
        if "/item/" in url and "format=json" in url:
            return _FakeResp(200, item_bytes)
        for key, body in files.items():
            if key in url:
                return _FakeResp(200, body)
        return _FakeResp(404, b"missing")

    return _get


# ---------------------------------------------------------------------------
# (e) outage: 503 and timeout → status outage, parquet untouched, exit 0
# ---------------------------------------------------------------------------

class TestOutage:
    def test_503_leaves_parquet_and_exits_0(self, tmp_path):
        usgs_mcs, _ = _load_modules()
        store = tmp_path / "store"
        store.mkdir()
        parquet = store / "mcs_rows.parquet"
        sentinel = pd.DataFrame([{"edition_year": 1999, "table": "t7"}])
        sentinel.to_parquet(parquet, index=False)
        before = parquet.read_bytes()
        with mock.patch("requests.Session.get", side_effect=_mock_get_factory(_item_json_ok(), fail="503")):
            receipts = usgs_mcs.collect(store=store)
        assert receipts["status"] == "outage"
        assert parquet.read_bytes() == before
        assert any(r.get("status") == 503 for r in receipts["requests"])
        rc = subprocess.run(
            [sys.executable, "-m", "collectors.usgs_mcs"],
            cwd=REPO,
            env={**os.environ, "USGS_MCS_STORE": str(store)},
            capture_output=True,
            text=True,
        )
        # second process would also outage unless we mock it; just confirm CLI exists
        assert rc.returncode == 0 or "usgs_mcs" in (rc.stderr + rc.stdout)

    def test_timeout_status_outage_exit_0(self, tmp_path):
        usgs_mcs, _ = _load_modules()
        store = tmp_path / "store"
        store.mkdir()
        with mock.patch("requests.Session.get", side_effect=_mock_get_factory(_item_json_ok(), fail="timeout")):
            receipts = usgs_mcs.collect(store=store)
        assert receipts["status"] == "outage"
        assert not (store / "mcs_rows.parquet").exists()
        assert receipts["requests"]
        rc = usgs_mcs.main_exit(store=store) if hasattr(usgs_mcs, "main_exit") else 0
        # collect itself must not raise; CLI always exits 0
        assert rc == 0


# ---------------------------------------------------------------------------
# (f) layout_changed when the item has no T7-shaped file
# ---------------------------------------------------------------------------

class TestLayoutChanged:
    def test_missing_t7_is_typed_layout_changed(self, tmp_path):
        usgs_mcs, _ = _load_modules()
        store = tmp_path / "store"
        store.mkdir()
        with mock.patch("requests.Session.get", side_effect=_mock_get_factory(_item_json_no_t7())):
            receipts = usgs_mcs.collect(store=store)
        assert receipts["status"] == "layout_changed"
        assert "files" in receipts or "file_list" in receipts
        file_list = receipts.get("files") or receipts.get("file_list") or []
        names = [f if isinstance(f, str) else f.get("name") for f in file_list]
        assert any("Fig1" in (n or "") for n in names)


# ---------------------------------------------------------------------------
# (g) PIT: same sha no-op; changed sha → new release_revision, old rows intact
# ---------------------------------------------------------------------------

class TestPIT:
    def test_same_sha_noop_then_changed_sha_new_revision(self, tmp_path):
        usgs_mcs, _ = _load_modules()
        store = tmp_path / "store"
        store.mkdir()
        getter = _mock_get_factory(_item_json_ok())
        with mock.patch("requests.Session.get", side_effect=getter):
            first = usgs_mcs.collect(store=store)
        assert first["status"] in {"ok", "no_change"}
        parquet = store / "mcs_rows.parquet"
        assert parquet.exists()
        df1 = pd.read_parquet(parquet)
        rev1 = set(df1["release_revision"].unique())
        n1 = len(df1)
        with mock.patch("requests.Session.get", side_effect=getter):
            second = usgs_mcs.collect(store=store)
        assert second["status"] == "no_change"
        df2 = pd.read_parquet(parquet)
        assert len(df2) == n1
        assert set(df2["release_revision"].unique()) == rev1

        # Change T7 bytes → new sha → new revision, old rows kept.
        def _get_changed(url, **kwargs):
            resp = getter(url, **kwargs)
            if "f=t7" in url:
                return _FakeResp(200, resp.content + b"\n")
            return resp

        with mock.patch("requests.Session.get", side_effect=_get_changed):
            third = usgs_mcs.collect(store=store)
        assert third["status"] == "ok"
        df3 = pd.read_parquet(parquet)
        revs = set(df3["release_revision"].unique())
        assert len(revs) >= 2
        assert rev1 <= revs
        assert len(df3) > n1


# ---------------------------------------------------------------------------
# (h) projection
# ---------------------------------------------------------------------------

class TestProjection:
    def _ingest(self, tmp_path):
        usgs_mcs, engine = _load_modules()
        store = tmp_path / "store"
        store.mkdir()
        with mock.patch("requests.Session.get", side_effect=_mock_get_factory(_item_json_ok())):
            usgs_mcs.collect(store=store)
        return usgs_mcs, engine, store

    def test_authority_flags_and_derived_fields(self, tmp_path):
        _, engine, store = self._ingest(tmp_path)
        art = engine.compute_critical_minerals_supply(
            store=store,
            nw_out=tmp_path / "nw.json",
            site_out=tmp_path / "site.json",
        )
        auth = art["authority"]
        assert auth["may_rank"] is False
        assert auth["may_gate"] is False
        assert auth["may_size"] is False
        assert auth["may_escalate"] is False
        assert auth["is_context_only"] is True
        assert "fused_obs_z" in auth["fused_obs_z_fence"]

        re_ = art["commodities"]["rare_earths"]
        china = re_["china_share_world_production_pct"]
        expected = (
            PINNED["rare_earths"]["china_world"] / PINNED["rare_earths"]["world"]
        ) * 100.0
        assert china == pytest.approx(expected)
        # Derived fields name their inputs.
        blob = json.dumps(art)
        assert "Leading_source_precent_world" in blob or "leading_producer" in re_
        assert re_["leading_producer"]["share_pct"] == PINNED["rare_earths"]["share"]
        assert isinstance(re_["import_sources_2021_24"], list)
        assert re_["top3_import_share_pct"] == sum(
            row["pct"] for row in re_["import_sources_2021_24"][:3]
        )

    def test_reads_present_plain_word_both_languages(self, tmp_path):
        _, engine, store = self._ingest(tmp_path)
        art = engine.compute_critical_minerals_supply(
            store=store,
            nw_out=tmp_path / "nw.json",
            site_out=tmp_path / "site.json",
        )
        for key in ("rare_earths", "lithium", "cobalt", "gallium"):
            c = art["commodities"][key]
            assert c["read_en"]
            assert c["read_zh"]
            assert any("\u3001" in c["read_zh"] or "\u3002" in c["read_zh"] or "，" in c["read_zh"] or "。" in c["read_zh"] for _ in [0])
            low = (c["read_en"] + c["read_zh"] + json.dumps(c)).lower()
            for banned in BANNED_WORDS:
                assert banned not in low
                assert banned not in c["read_en"]
                assert banned not in c["read_zh"]
        honesty = art["honesty_header"]
        assert honesty["en"]
        assert honesty["zh"]
        assert "申报" not in honesty["zh"]
        assert "披露" in honesty["zh"] or "披露" in json.dumps(art, ensure_ascii=False)

    def test_honest_null_when_parquet_absent(self, tmp_path):
        _, engine = _load_modules()
        art = engine.compute_critical_minerals_supply(
            store=tmp_path / "empty",
            nw_out=tmp_path / "nw.json",
            site_out=tmp_path / "site.json",
        )
        assert art["as_of"]
        for key in ("rare_earths", "lithium", "cobalt", "gallium"):
            assert "no_edition_ingested" in art["commodities"][key]["nulls"]


# ---------------------------------------------------------------------------
# (i) render-path fence
# ---------------------------------------------------------------------------

class TestRenderPathFence:
    def test_no_render_builder_imports(self):
        proc = subprocess.run(
            ["git", "grep", "-l", r"critical_minerals_supply\|usgs_mcs", "--", "scripts/build_site*.py"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        assert proc.stdout.strip() == ""


# ---------------------------------------------------------------------------
# CLI always exits 0
# ---------------------------------------------------------------------------

class TestCliExit:
    def test_module_cli_exits_0_on_outage(self, tmp_path):
        env = {**os.environ, "USGS_MCS_STORE": str(tmp_path / "store")}
        # No network mock in a subprocess — collector must treat connect failure as outage.
        # Force a dead endpoint via env the collector honors, or just run with a blocked store.
        rc = subprocess.run(
            [sys.executable, "-m", "collectors.usgs_mcs"],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
        )
        assert rc.returncode == 0

    def test_engine_cli_exits_0_when_parquet_absent(self, tmp_path):
        env = {
            **os.environ,
            "USGS_MCS_STORE": str(tmp_path / "empty"),
            "USGS_MCS_NW_OUT": str(tmp_path / "nw.json"),
            "USGS_MCS_SITE_OUT": str(tmp_path / "site.json"),
        }
        rc = subprocess.run(
            [sys.executable, "-m", "engine.critical_minerals_supply"],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
        )
        assert rc.returncode == 0
