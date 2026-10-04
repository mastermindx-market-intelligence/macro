"""Tests for publish_vault — sidecar_for mapping + VaultPublisher (mocked R2).

No network / no live bucket: the pure ``sidecar_for`` mapping needs nothing, and
the publisher tests inject a fake boto3-style client. The module imports with only
stdlib + pydantic (boto3 is lazy).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from marketdesk_extractor import publish_vault
from marketdesk_extractor.config import Config
from marketdesk_extractor.publish_vault import (
    INSTITUTION_DISPLAY,
    SIDECAR_SCHEMA,
    VaultPublisher,
    display_institution,
    extra_title,
    looks_truncated,
    side_for,
    sidecar_for,
    vault_id,
)

# vault ids are lowercase + a 6-hex hash of the ORIGINAL blob id (case-safe).
VID = vault_id("blob42")
PKEY = f"research_inbox/{VID}.pdf"
JKEY = f"research_inbox/{VID}.json"


# ---------------------------------------------------------------------------
# helpers / fixtures
# ---------------------------------------------------------------------------

def _paper(**overrides):
    """A MarketDesk-paper-like object (attribute access) with sane defaults."""
    base = dict(
        blob_id="blob42",
        title="Equinix: datacenter demand inflecting",
        institution="GS",
        published_at=datetime(2026, 7, 21, 14, 0, 0, tzinfo=timezone.utc),
        marketdesk_summary=(
            "We upgrade to Buy. Datacenter leasing is accelerating into 2H. "
            "Pricing power supports margin expansion."
        ),
        breadcrumb=["2026", "July", "Jul 21", "Goldman", "S&T"],
        is_top_pick=False,
        is_saved=False,
        local_priority_score=40,
        page_count=12,
        pdf_filename="2026-07-21_goldman_equinix_blob42.pdf",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture()
def vault_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Config with the vault ENABLED + credentials + bucket set."""
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct123")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("R2_BUCKET", "marketdesk-main")
    monkeypatch.setenv("VAULT_ENABLED", "true")
    monkeypatch.setenv("VAULT_R2_BUCKET", "research-vault-private")
    monkeypatch.setenv("VAULT_R2_PREFIX", "research_inbox")
    monkeypatch.setenv("VAULT_TOP_PICK_MIN_SCORE", "85")
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "db" / "t.sqlite"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RAW_PDF_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("MARKDOWN_DIR", str(tmp_path / "md"))
    monkeypatch.setenv("METADATA_DIR", str(tmp_path / "meta"))
    monkeypatch.setenv("MANIFEST_DIR", str(tmp_path / "manifests"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    return Config.from_env()


class FakeS3:
    """Minimal boto3-S3 stand-in: records put_object; head_object per a set."""

    def __init__(self, existing: set[tuple[str, str]] | None = None,
                 main_objects: dict[tuple[str, str], bytes] | None = None):
        self.existing = existing or set()          # {(bucket, key)} that "exist"
        self.main_objects = main_objects or {}      # {(bucket, key): bytes} to GET
        self.puts: list[dict] = []

    def head_object(self, Bucket, Key):  # noqa: N803 — boto3 kwarg names
        if (Bucket, Key) in self.existing:
            return {}
        err = Exception("404")
        err.response = {"Error": {"Code": "404"}}
        raise err

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) in self.main_objects:
            body = SimpleNamespace(read=lambda: self.main_objects[(Bucket, Key)])
            return {"Body": body}
        err = Exception("NoSuchKey")
        err.response = {"Error": {"Code": "NoSuchKey"}}
        raise err

    def put_object(self, Bucket, Key, Body, ContentType):  # noqa: N803
        self.puts.append(
            {"Bucket": Bucket, "Key": Key, "Body": Body, "ContentType": ContentType}
        )
        self.existing.add((Bucket, Key))


def _publisher_with(cfg: Config, fake: FakeS3) -> VaultPublisher:
    """Build a VaultPublisher then swap its client for the fake (skips boto3)."""
    pub = VaultPublisher.__new__(VaultPublisher)
    pub._cfg = cfg
    pub._log = publish_vault.get_logger("publish_vault_test")
    pub._client = fake
    pub._main_client = fake  # main-bucket fallback reads use the same fake
    return pub


# ===========================================================================
# sidecar_for — the pure mapping
# ===========================================================================

def test_id_shape_lowercase_hashed_and_deterministic():
    vid = vault_id("abc-123")
    assert vid.startswith("marketdesk-abc-123-")
    assert vid == vid.lower()
    assert len(vid.rsplit("-", 1)[-1]) == 6          # 6-hex disambiguator
    assert vault_id("abc-123") == vid                 # deterministic -> idempotent
    sc = sidecar_for(_paper(blob_id="abc-123"))
    assert sc["id"] == vid


def test_id_case_fold_cannot_collide():
    # MarketDesk blob ids are case-sensitive base62; after lowercasing, the hash
    # of the ORIGINAL id keeps two case-variants distinct.
    a, b = vault_id("AbC"), vault_id("abc")
    assert a != b
    assert a.startswith("marketdesk-abc-") and b.startswith("marketdesk-abc-")


def test_schema_tag():
    assert sidecar_for(_paper())["schema"] == SIDECAR_SCHEMA == "research_vault.sidecar.v1"


def test_side_defaults_to_sell():
    assert sidecar_for(_paper())["side"] == "sell"


def test_institution_display_name():
    assert sidecar_for(_paper(institution="GS"))["institution"] == "Goldman Sachs"
    assert sidecar_for(_paper(institution="JPM"))["institution"] == "J.P. Morgan"
    assert sidecar_for(_paper(institution="MS"))["institution"] == "Morgan Stanley"
    assert sidecar_for(_paper(institution="DB"))["institution"] == "Deutsche Bank"


def test_institution_fallback_when_unmapped():
    sc = sidecar_for(_paper(institution="Some Boutique LLP"))
    assert sc["institution"] == "Some Boutique LLP"


def test_institution_none_stays_none():
    assert sidecar_for(_paper(institution=None))["institution"] is None


def test_display_institution_helper_case_insensitive():
    assert display_institution("gs") == "Goldman Sachs"
    assert display_institution("  Goldman  ") == "Goldman Sachs"
    assert display_institution("") is None
    assert display_institution(None) is None
    # unmapped -> trimmed raw
    assert display_institution("  Foo Bank ") == "Foo Bank"


def test_desk_is_last_non_institution_breadcrumb_segment():
    sc = sidecar_for(_paper(breadcrumb=["2026", "July", "Jul 21", "Goldman", "S&T"]))
    assert sc["desk"] == "S&T"


def test_desk_skips_trailing_institution_segment():
    # breadcrumb ends on the institution -> desk falls back to the previous crumb
    sc = sidecar_for(
        _paper(institution="GS",
               breadcrumb=["2026", "July", "Jul 21", "Equity Research", "Goldman"])
    )
    assert sc["desk"] == "Equity Research"


def test_desk_none_when_no_breadcrumb():
    assert sidecar_for(_paper(breadcrumb=[]))["desk"] is None


def test_tags_include_desk():
    sc = sidecar_for(_paper(breadcrumb=["2026", "Jul 21", "Goldman", "S&T"]))
    assert "S&T" in sc["tags"]


# --- summary_points splitting ----------------------------------------------

def test_summary_points_multi_sentence_to_bullets():
    sc = sidecar_for(_paper(
        marketdesk_summary="First point here. Second point follows. Third and last."
    ))
    pts = sc["summary_points"]
    assert pts == ["First point here.", "Second point follows.", "Third and last."]
    assert 2 <= len(pts) <= 5


def test_summary_points_empty_when_absent():
    assert sidecar_for(_paper(marketdesk_summary=None))["summary_points"] == []
    assert sidecar_for(_paper(marketdesk_summary=""))["summary_points"] == []
    assert sidecar_for(_paper(marketdesk_summary="   "))["summary_points"] == []


def test_summary_points_strip_markdown_markers():
    sc = sidecar_for(_paper(
        marketdesk_summary="- upgrade to buy\n* margin expansion\n# rates tailwind"
    ))
    pts = sc["summary_points"]
    assert pts == ["upgrade to buy", "margin expansion", "rates tailwind"]
    assert all(not p.startswith(("-", "*", "#")) for p in pts)


def test_summary_points_capped_at_five():
    long = " ".join(f"Sentence number {i}." for i in range(1, 9))
    pts = sidecar_for(_paper(marketdesk_summary=long))["summary_points"]
    assert len(pts) == 5


def test_summary_points_single_sentence_is_one_bullet():
    pts = sidecar_for(_paper(marketdesk_summary="Only one thing to say"))["summary_points"]
    assert pts == ["Only one thing to say"]


# --- top_pick logic --------------------------------------------------------

def test_top_pick_true_from_is_top_pick_flag():
    sc = sidecar_for(_paper(is_top_pick=True, local_priority_score=10))
    assert sc["top_pick"] is True


def test_top_pick_true_from_score_at_threshold():
    sc = sidecar_for(_paper(is_top_pick=False, local_priority_score=85),
                     top_pick_min_score=85)
    assert sc["top_pick"] is True


def test_top_pick_true_from_score_above_threshold():
    sc = sidecar_for(_paper(is_top_pick=False, local_priority_score=90),
                     top_pick_min_score=85)
    assert sc["top_pick"] is True


def test_top_pick_false_below_threshold_and_no_flag():
    sc = sidecar_for(_paper(is_top_pick=False, local_priority_score=84),
                     top_pick_min_score=85)
    assert sc["top_pick"] is False


def test_top_pick_flag_accepts_int_from_db():
    # sqlite stores bools as 0/1
    assert sidecar_for(_paper(is_top_pick=1, local_priority_score=0))["top_pick"] is True
    assert sidecar_for(_paper(is_top_pick=0, local_priority_score=0))["top_pick"] is False


# --- pages / source_filename / language / tickers --------------------------

def test_pages_from_page_count():
    assert sidecar_for(_paper(page_count=12))["pages"] == 12


def test_source_filename_from_pdf_filename():
    sc = sidecar_for(_paper(pdf_filename="2026-07-21_goldman_equinix_blob42.pdf"))
    assert sc["source_filename"] == "2026-07-21_goldman_equinix_blob42.pdf"


def test_language_defaults_to_en():
    assert sidecar_for(_paper())["language"] == "en"


def test_tickers_default_empty():
    assert sidecar_for(_paper())["tickers"] == []


def test_tickers_passed_through_when_present():
    sc = sidecar_for(_paper(tickers=["EQIX", "DLR"]))
    assert sc["tickers"] == ["EQIX", "DLR"]


def test_published_at_normalized_to_z_suffix():
    sc = sidecar_for(_paper(
        published_at=datetime(2026, 7, 21, 14, 0, 0, tzinfo=timezone.utc)
    ))
    assert sc["published_at"] == "2026-07-21T14:00:00Z"


# --- defaults for missing fields (robustness) ------------------------------

def test_missing_fields_do_not_raise_and_yield_defaults():
    sparse = SimpleNamespace(blob_id="onlyid")
    sc = sidecar_for(sparse)
    assert sc["id"] == vault_id("onlyid")
    assert sc["title"] == ""
    assert sc["institution"] is None
    assert sc["desk"] is None
    assert sc["summary_points"] == []
    assert sc["tags"] == []
    assert sc["tickers"] == []
    assert sc["pages"] is None
    assert sc["top_pick"] is False
    assert sc["side"] == "sell"
    assert sc["language"] == "en"


def test_sidecar_is_json_serializable():
    # the whole contract must round-trip through json (no datetimes leaking)
    sc = sidecar_for(_paper())
    round_tripped = json.loads(json.dumps(sc))
    assert round_tripped["id"] == VID


def test_works_on_dict_input():
    d = {
        "blob_id": "d1", "title": "T", "institution": "UBS",
        "marketdesk_summary": "One. Two.", "local_priority_score": 90,
        "is_top_pick": 0, "page_count": 3,
    }
    sc = sidecar_for(d)
    assert sc["id"] == vault_id("d1")
    assert sc["institution"] == "UBS"
    assert sc["top_pick"] is True  # 90 >= 85
    assert sc["summary_points"] == ["One.", "Two."]


def test_side_classification():
    assert side_for("Goldman Sachs") == "sell"
    assert side_for("KKR") == "buy"
    assert side_for("Apollo") == "buy"
    assert side_for("Zero Hedge") == "independent"
    assert side_for("TS Lombard") == "independent"
    assert side_for(None) == "sell"
    # flows through sidecar_for
    assert sidecar_for(_paper(institution="KKR"))["side"] == "buy"
    assert sidecar_for(_paper(institution="Zero Hedge"))["side"] == "independent"


def test_paren_institution_splits_into_desk():
    # "Bernstein (Data Centers)" -> institution Bernstein, desk Data Centers
    sc = sidecar_for(_paper(institution="Bernstein (Data Centers)", breadcrumb=[]))
    assert sc["institution"] == "Bernstein"
    assert sc["desk"] == "Data Centers"
    assert sc["side"] == "sell"
    # breadcrumb desk still wins when present
    sc2 = sidecar_for(_paper(institution="Bernstein (Data Centers)",
                             breadcrumb=["2026", "Jul 21", "Bernstein", "S&T"]))
    assert sc2["desk"] == "S&T"
    # a breadcrumb crumb that is ITSELF "Inst (Desk)" yields just the desk
    sc3 = sidecar_for(_paper(institution="Bernstein (Data Centers)",
                             breadcrumb=["2026", "Jul 21", "Bernstein (Data Centers)"]))
    assert sc3["institution"] == "Bernstein"
    assert sc3["desk"] == "Data Centers"
    assert sc3["tags"][0] == "Data Centers"


def test_vault_creds_prefer_vault_account(tmp_path, monkeypatch):
    # VAULT_R2_* (own Cloudflare account) wins; blank falls back to main R2_*.
    monkeypatch.setenv("R2_ACCOUNT_ID", "mainacct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "main-ak")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "main-sk")
    monkeypatch.setenv("VAULT_ENABLED", "true")
    monkeypatch.setenv("VAULT_R2_BUCKET", "research")
    monkeypatch.setenv("VAULT_R2_ACCOUNT_ID", "vaultacct")
    monkeypatch.setenv("VAULT_R2_ACCESS_KEY_ID", "vault-ak")
    monkeypatch.setenv("VAULT_R2_SECRET_ACCESS_KEY", "vault-sk")
    _set_paths(monkeypatch, tmp_path)
    cfg = Config.from_env()
    pub = VaultPublisher.__new__(VaultPublisher)
    pub._cfg = cfg
    assert pub._vault_account_id() == "vaultacct"
    assert pub._vault_key() == "vault-ak"
    assert pub._vault_secret() == "vault-sk"
    monkeypatch.setenv("VAULT_R2_ACCOUNT_ID", "")
    monkeypatch.setenv("VAULT_R2_ACCESS_KEY_ID", "")
    monkeypatch.setenv("VAULT_R2_SECRET_ACCESS_KEY", "")
    cfg2 = Config.from_env()
    pub2 = VaultPublisher.__new__(VaultPublisher)
    pub2._cfg = cfg2
    assert pub2._vault_account_id() == "mainacct"
    assert pub2._vault_key() == "main-ak"


def test_institution_display_covers_config_important_keys():
    # every IMPORTANT_INSTITUTIONS-style code we care about resolves to a display name
    for code in ("GS", "JPM", "MS", "BofA", "Citi", "UBS"):
        assert display_institution(code) in INSTITUTION_DISPLAY.values()


# ===========================================================================
# VaultPublisher — enabled gating (no boto3 client built when disabled)
# ===========================================================================

def test_enabled_true_when_configured(vault_cfg: Config, monkeypatch):
    # avoid importing real boto3 in __init__
    import sys
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *a, **k: FakeS3()))
    pub = VaultPublisher(vault_cfg)
    assert pub.enabled is True


def test_disabled_when_vault_flag_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VAULT_ENABLED", "false")
    monkeypatch.setenv("VAULT_R2_BUCKET", "research-vault-private")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "sk")
    _set_paths(monkeypatch, tmp_path)
    cfg = Config.from_env()
    pub = VaultPublisher(cfg)  # must NOT import boto3
    assert pub.enabled is False
    assert pub.publish(_paper()) is None  # clean no-op


def test_disabled_when_bucket_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VAULT_ENABLED", "true")
    monkeypatch.setenv("VAULT_R2_BUCKET", "")  # no bucket -> disabled
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "sk")
    _set_paths(monkeypatch, tmp_path)
    cfg = Config.from_env()
    pub = VaultPublisher(cfg)
    assert pub.enabled is False


def test_disabled_when_credentials_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VAULT_ENABLED", "true")
    monkeypatch.setenv("VAULT_R2_BUCKET", "research-vault-private")
    monkeypatch.setenv("R2_ACCOUNT_ID", "")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "")
    # Also clear the own-account VAULT_R2_* creds — otherwise a developer's real
    # .env leaks them and `enabled` resolves True (each falls back to R2_* only
    # when its VAULT_R2_* value is empty). Keep this test hermetic.
    monkeypatch.setenv("VAULT_R2_ACCOUNT_ID", "")
    monkeypatch.setenv("VAULT_R2_ACCESS_KEY_ID", "")
    monkeypatch.setenv("VAULT_R2_SECRET_ACCESS_KEY", "")
    _set_paths(monkeypatch, tmp_path)
    cfg = Config.from_env()
    assert VaultPublisher(cfg).enabled is False


def _set_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for env, sub in [
        ("DATABASE_URL", "db/t.sqlite"), ("OUTPUT_DIR", "data"), ("RAW_PDF_DIR", "raw"),
        ("MARKDOWN_DIR", "md"), ("METADATA_DIR", "meta"),
        ("MANIFEST_DIR", "manifests"), ("LOG_DIR", "logs"),
    ]:
        monkeypatch.setenv(env, str(tmp_path / sub))


# ===========================================================================
# VaultPublisher.publish — write + idempotency (mocked S3)
# ===========================================================================

def test_publish_writes_pdf_and_json_from_local_file(vault_cfg: Config, tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7 fake body")
    fake = FakeS3()
    pub = _publisher_with(vault_cfg, fake)

    paper = _paper(local_pdf_path=str(pdf))
    vid = pub.publish(paper)

    assert vid == VID
    keys = {p["Key"] for p in fake.puts}
    assert PKEY in keys
    assert JKEY in keys
    # content types
    ct = {p["Key"]: p["ContentType"] for p in fake.puts}
    assert ct[PKEY] == "application/pdf"
    assert ct[JKEY] == "application/json"
    # the json body is the sidecar contract
    body = next(p["Body"] for p in fake.puts
                if p["Key"].endswith(".json"))
    sc = json.loads(body.decode("utf-8"))
    assert sc["schema"] == "research_vault.sidecar.v1"
    assert sc["id"] == VID
    assert sc["institution"] == "Goldman Sachs"


def test_publish_idempotent_skips_when_both_keys_exist(vault_cfg: Config, tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7 fake body")
    existing = {
        ("research-vault-private", PKEY),
        ("research-vault-private", JKEY),
    }
    fake = FakeS3(existing=existing)
    pub = _publisher_with(vault_cfg, fake)

    vid = pub.publish(_paper(local_pdf_path=str(pdf)))
    assert vid == VID      # returns id (so caller can mark vaulted)
    assert fake.puts == []                 # but writes NOTHING


def test_publish_force_reuploads_even_if_exists(vault_cfg: Config, tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7 fake body")
    existing = {
        ("research-vault-private", PKEY),
        ("research-vault-private", JKEY),
    }
    fake = FakeS3(existing=existing)
    pub = _publisher_with(vault_cfg, fake)

    vid = pub.publish(_paper(local_pdf_path=str(pdf)), force=True)
    assert vid == VID
    keys = {p["Key"] for p in fake.puts}
    assert PKEY in keys
    assert JKEY in keys


def test_publish_falls_back_to_main_bucket_when_no_local(vault_cfg: Config):
    # no local file; PDF must be copied from the main bucket's r2_pdf_key object
    main_key = "marketdesk/raw_pdfs/2026-07-21/paper.pdf"
    fake = FakeS3(main_objects={("marketdesk-main", main_key): b"%PDF-main-copy"})
    pub = _publisher_with(vault_cfg, fake)

    paper = _paper(local_pdf_path=None, r2_pdf_key=main_key)
    vid = pub.publish(paper)

    assert vid == VID
    pdf_put = next(p for p in fake.puts if p["Key"].endswith(".pdf"))
    assert pdf_put["Body"] == b"%PDF-main-copy"


def test_publish_returns_none_when_no_pdf_source(vault_cfg: Config):
    fake = FakeS3()
    pub = _publisher_with(vault_cfg, fake)
    # no local path, no r2_pdf_key -> nothing to publish
    paper = _paper(local_pdf_path=None, r2_pdf_key=None)
    assert pub.publish(paper) is None
    assert fake.puts == []


def test_publish_never_raises_on_bad_paper(vault_cfg: Config):
    fake = FakeS3()
    pub = _publisher_with(vault_cfg, fake)
    # a paper with no blob_id — publish logs + returns None, does not raise
    assert pub.publish(SimpleNamespace()) is None


# ===========================================================================
# truncated-title detection + /extra recovery  (data-quality self-heal)
# ===========================================================================

def test_looks_truncated_flags_dropped_exchange_suffix():
    # MarketDesk drops the Reuters '.EX)' suffix → an unbalanced '('.
    assert looks_truncated("Alcon Inc. (ALCC") is True
    assert looks_truncated("Carrefour (CARR") is True
    assert looks_truncated("SAP (SAPG") is True
    assert looks_truncated("Carrefour (CARR(1)") is True   # 2 '(' vs 1 ')'
    # balanced / suffix-only titles are fine
    assert looks_truncated("Alcon Inc. (ALCC.US)") is False
    assert looks_truncated("South Africa SARB ... Consensus(1)") is False
    assert looks_truncated("Daily Asia en 1663849 1") is False
    assert looks_truncated("") is False
    assert looks_truncated(None) is False


def test_extra_title_recovers_full_title_when_truncated():
    # a balanced, at-least-as-long candidate under any known key wins
    assert extra_title({"title": "Alcon Inc. (ALCC.US)"}, "Alcon Inc. (ALCC") == "Alcon Inc. (ALCC.US)"
    assert extra_title({"name": "Carrefour (CARR.PA)"}, "Carrefour (CARR") == "Carrefour (CARR.PA)"
    # a trailing .pdf is stripped (but NOT via splitext — the inner dot survives)
    assert extra_title({"fileName": "SAP (SAPG.DE).pdf"}, "SAP (SAPG") == "SAP (SAPG.DE)"


def test_extra_title_never_regresses_a_good_title():
    # current title already balanced → no change even if /extra differs
    assert extra_title({"title": "Whatever else"}, "Alcon Inc. (ALCC.US)") is None
    # candidate itself truncated (MarketDesk's own name often is) → rejected
    assert extra_title({"name": "Carrefour (CARR"}, "Carrefour (CARR") is None
    # candidate shorter than the truncated stem → rejected
    assert extra_title({"title": "Carr"}, "Carrefour (CARR") is None
    # nothing usable in the payload → None (safe no-op)
    assert extra_title({"summary": "x", "images": []}, "Carrefour (CARR") is None
    assert extra_title({}, "Carrefour (CARR") is None


def test_republish_sidecar_writes_json_only_no_pdf(vault_cfg: Config):
    # both keys already exist (paper was vaulted); a metadata re-heal must rewrite
    # ONLY the .json — never touch/re-upload the .pdf (its bytes may be gone).
    fake = FakeS3(existing={("research-vault-private", PKEY), ("research-vault-private", JKEY)})
    pub = _publisher_with(vault_cfg, fake)
    vid = pub.republish_sidecar(_paper(marketdesk_summary="A late summary. Now present."))
    assert vid == VID
    assert len(fake.puts) == 1
    put = fake.puts[0]
    assert put["Key"] == JKEY and put["ContentType"] == "application/json"
    body = json.loads(put["Body"].decode("utf-8"))
    assert body["summary_points"] and body["schema"] == SIDECAR_SCHEMA


def test_republish_sidecar_none_without_blob_id(vault_cfg: Config):
    pub = _publisher_with(vault_cfg, FakeS3())
    assert pub.republish_sidecar(SimpleNamespace()) is None
