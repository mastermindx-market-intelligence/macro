"""Tests for the institution/topic EXCLUSION filter (filters.py).

Two layers:
  1. ``classify_exclusion`` — the PURE classifier. Blogs, daily-FX, and minor-geo
     hits must be tagged; every MAJOR economy and real FX strategy must stay
     downloadable (return ``None``).
  2. ``reclassify`` — the re-runnable DB pass. Must be idempotent (second run is a
     no-op) and must RESTORE previously-excluded rows when the list shrinks, while
     never touching COMPLETE/DOWNLOADED/etc.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from marketdesk_extractor import db
from marketdesk_extractor.filters import (
    DEFAULT_EXCLUDE_INSTITUTIONS,
    _MAJOR_GUARDED_REASONS,
    classify_exclusion,
    default_tagged_patterns,
    default_title_patterns,
    looks_german,
    reclassify,
)
from marketdesk_extractor.schemas import ArticleMeta, Status


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_PATTERNS = default_title_patterns()


def _classify(title: str | None, institution: str | None = None) -> str | None:
    return classify_exclusion(
        institution, title,
        exclude_institutions=DEFAULT_EXCLUDE_INSTITUTIONS,
        title_patterns=_PATTERNS,
    )


# ---------------------------------------------------------------------------
# classify_exclusion — EXCLUDE hits
# ---------------------------------------------------------------------------

def test_blog_institution_hit() -> None:
    assert _classify("Some macro note", institution="The Market Ear") == "institution"
    assert _classify("Whatever", institution="Zero Hedge") == "institution"
    # abbreviation + case/whitespace insensitivity
    assert _classify("Note", institution="  TME ") == "institution"
    assert _classify("Note", institution="the market EAR") == "institution"


def test_fx_daily_snapshot_hit() -> None:
    assert _classify("MUFG FX Daily Snapshot") == "fx_daily"
    assert _classify("Daily FX Snapshot — G10") == "fx_daily"
    assert _classify("ANZ FX Daily") == "fx_daily"


def test_minor_geo_czech_hit() -> None:
    assert _classify("ING Think czech economy — CNB on hold") == "minor_geo"


def test_minor_geo_malaysia_hit() -> None:
    assert _classify("Bank Negara Malaysia holds rates steady") == "minor_geo"


def test_minor_geo_australia_hit() -> None:
    assert _classify("Australian Macro Weekly — RBA watch") == "minor_geo"


@pytest.mark.parametrize(
    "title",
    [
        "New Zealand RBNZ preview",
        "South Africa CPI surprise",
        "Norway Norges Bank decision",
        "Swiss SNB balance sheet",
        "Turkey lira selloff",
        "Indonesia trade balance",
        "Thailand GDP beats",
        "Poland NBP minutes",
        "Hungary forint under pressure",
    ],
)
def test_minor_geo_various_hits(title: str) -> None:
    assert _classify(title) == "minor_geo"


# ---------------------------------------------------------------------------
# classify_exclusion — MAJOR economies must NEVER be excluded (critical)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "title",
    [
        "Goldman China PMI Preview",
        "Korea IP and GDP",
        "Taiwan Weekly Kickstart",
        "Japan BoJ decision",
        "US Week Ahead",
        "ECB hawkish hold",
        "FX Strategy: EUR/USD",   # FX strategy, NOT a daily snapshot
        "FX Insights: dollar smile",
        "United States jobs report",
        "USA payrolls preview",
        "India rate decision",
        "Indian rupee outlook",
        "United Kingdom GDP",
        "Britain inflation shock",
        "British gilts selloff",
        "Germany IFO survey",
        "German bund yields",
        "France CPI",
        "French OAT spread",
        "Italy budget",
        "Spain election",
        "Spanish bonos",
        "Eurozone PMI flash",
        "Europe outlook 2027",
        "European banks",
        "Fed minutes",
        "BoJ policy tweak",
        "PBOC RRR cut",
        "Singapore MAS statement",
        "Chinese equities rally",
        "Japanese yen weakness",
        "Korean won stabilises",
    ],
)
def test_major_economies_not_excluded(title: str) -> None:
    assert _classify(title) is None, f"{title!r} must stay downloadable"


def test_us_china_note_not_excluded() -> None:
    # both majors — must not fire minor_geo on any token
    assert _classify("US-China trade war escalates") is None


@pytest.mark.parametrize(
    "title",
    [
        "China-Australia iron ore",          # major + minor
        "Taiwan and Thailand chip supply",
        "India and Indonesia demographics",
        "Germany and Austria autos",
        "US and Thailand trade tensions",
        "ECB and SNB (Switzerland) divergence",
        "Japan vs Korea exports",
    ],
)
def test_major_vetoes_minor_geo_in_mixed_title(title: str) -> None:
    """A title naming a MAJOR economy stays downloadable even if it also mentions a
    minor one — the paper is about the major (highest-severity false-drop guard)."""
    assert _classify(title) is None, f"{title!r} names a major — must not be excluded"


def test_pure_minor_still_excluded_despite_guard() -> None:
    """The major-economy veto must NOT weaken pure single-minor exclusion."""
    assert _classify("Bank Negara Malaysia holds") == "minor_geo"
    assert _classify("Sweden Riksbank preview") == "minor_geo"


def test_blog_and_fx_reasons_ignore_major_veto() -> None:
    """The veto is geographic-only: a blog/fx_daily hit fires regardless of a major
    mention (a Zero Hedge post about the US is still noise)."""
    assert _classify("US stocks crash", institution="Zero Hedge") == "institution"
    assert _classify("USD FX Daily Snapshot", institution="MUFG") == "fx_daily"


def test_ticker_parens_vetoes_minor_geo() -> None:
    """A US-style parenthesised ticker marks a single-name note: it is about the
    COMPANY, so a minor-economy mention must not exclude it. Observed production
    false positive pinned here."""
    assert _classify(
        "The Brink's Co. (BCO) Updating estimates to reflect Malaysia business "
        "deconsolidation"
    ) is None
    # lowercase RIC-style tags are NOT US tickers and must not veto
    assert _classify("Sweden macro monthly (DB1Gn.DE) crossref") == "minor_geo"
    # the ticker veto is geographic-only: fx_daily still fires with a ticker
    assert _classify("FX Daily Snapshot (EUR)") == "fx_daily"


def test_plain_research_not_excluded() -> None:
    assert _classify("Semis upgrade to overweight", institution="Goldman Sachs") is None
    assert _classify("Rates outlook Q3", institution="JPM") is None


def test_none_inputs_are_safe() -> None:
    assert _classify(None, None) is None
    assert _classify("", "") is None


def test_default_patterns_compiled_shape() -> None:
    """Guard the shipped pattern list: language + fx_daily x2 + minor_geo x1."""
    tagged = default_tagged_patterns()
    tags = [t for t, _ in tagged]
    assert tags == ["language", "fx_daily", "fx_daily", "minor_geo"]
    # and none of the compiled patterns embeds a major-economy token as an
    # alternation member (spot-check the minor_geo alternation source)
    minor = [p.pattern for tag, p in tagged if tag == "minor_geo"][0].lower()
    for major in ("united states", "china", "japan", "korea", "taiwan", "india",
                  "germany", "france", "italy", "spain", "eurozone", "singapore"):
        assert major not in minor, f"{major!r} must not be in the minor_geo alternation"


# ---------------------------------------------------------------------------
# language (German) — unreadable to us, so never worth a download slot
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "title",
    [
        # real-shaped German notes
        "Aktienmarkt Schweiz: Ausblick für das zweite Halbjahr",
        "Konjunktur und Zinsen — Wochenausblick",
        "Über die Lage der Wirtschaft",
        "Märkte im Überblick",
        "Anleihen: Renditen bleibt unter Druck",
        "Der Handel bleibt schwach und die Nachfrage sinkt",  # two stopwords only
        # production ZKB title shapes (addendum): almost no grammar at all
        "Ersteinschätzung Calida Group EN 2026 07 24 316332",
        "Ersteinschätzung Orell Füssli EN 2026 07 24 317236",
        # ...and the same, ASCII-folded both ways by an inconsistent feed
        "Ersteinschatzung Calida Group EN 2026 07 24 316332",
        "Ersteinschaetzung Calida Group EN 2026 07 24 317236",
        # ß alone is decisive: the character does not occur in English
        "Strassenverkehr und Straße",
    ],
)
def test_german_titles_are_excluded(title: str) -> None:
    assert looks_german(title) is True, f"{title!r} is German"
    assert _classify(title) == "language"


@pytest.mark.parametrize(
    "title",
    [
        # ONE incidental German-looking token must never be enough
        "Zurich Insurance: upgrade to Buy",
        "Munich Re initiation — Outperform",
        "Über-bullish positioning in US semis",   # the umlaut IS the only signal
        "Fed outlook: rates und positioning",     # a single stray stopword
        "Von der Leyen speech: EU fiscal impulse",
        "MIT Sloan: the productivity puzzle",
        "Goldman China PMI Preview",
        "Semis upgrade to overweight",
        "Des Moines Fed regional survey",
    ],
)
def test_english_titles_with_incidental_hits_stay_downloadable(title: str) -> None:
    assert looks_german(title) is False, f"{title!r} is English — must stay"
    assert _classify(title) is None


@pytest.mark.parametrize(
    "title",
    [
        # REGRESSION: "börse" was briefly a strong single-hit word; its
        # ASCII-digraph spelling is a company name, and it false-flagged 9
        # English Goldman/Barclays notes in the 30k-row production corpus.
        "Deutsche Boerse AG (DB1Gn.DE) Updating estimates post 2Q results",
        "Barclays Deutsche Boerse AG Euronext NV Monthly snapshot June volumes",
        "Deutsche Börse AG (DB1Gn.DE) Estimate changes ahead of 1Q26",
        # English CEEMEA research using the native spelling of a country name:
        # an umlaut with NO German grammar around it is not German.
        "CEEMEA Economics Analyst Türkiye — Anatomy of an Export Slowdown",
        "Türkiye Corporate Days Turkish banks under pressure",
    ],
)
def test_english_notes_on_german_named_subjects_stay_downloadable(title: str) -> None:
    assert looks_german(title) is False, f"{title!r} is English research"


def test_language_is_not_under_the_major_economy_veto() -> None:
    """A German note ABOUT the Fed is still unreadable — the geographic veto must
    not rescue it. Guarded structurally as well as behaviourally."""
    assert _MAJOR_GUARDED_REASONS == frozenset({"minor_geo"})
    assert _classify("Die Fed und die US-Wirtschaft: Ausblick") == "language"
    assert _classify("Konjunktur in China und Europa — Wochenausblick") == "language"


def test_language_rides_with_the_title_pattern_flag() -> None:
    """Patterns OFF (the config flag passes an empty list) => language check off."""
    from marketdesk_extractor.filters import classify_exclusion_tagged

    assert classify_exclusion_tagged(
        "ZKB", "Ersteinschätzung Calida Group EN",
        exclude_institutions=set(), tagged_patterns=[],
    ) is None


def test_zkb_institution_is_excluded() -> None:
    """The production ``institution`` value is literally "ZKB", and several of its
    titles carry NO German words at all — the institution IS the only signal."""
    assert "zkb" in DEFAULT_EXCLUDE_INSTITUTIONS
    assert _classify("Schindler 20260724 en", institution="ZKB") == "institution"
    assert _classify("ZKB+Intraday Ypsomed 20260724 en", institution="ZKB") == "institution"
    assert _classify("SFS 20260724 en", institution="Zürcher Kantonalbank") == "institution"
    assert _classify("SFS 20260724 en", institution="Zurcher Kantonalbank") == "institution"
    # ...while a title with no German and no ZKB institution stays downloadable
    assert _classify("Schindler 20260724 en", institution="UBS") is None


def test_looks_german_handles_empty_input() -> None:
    assert looks_german(None) is False
    assert looks_german("") is False


# ---------------------------------------------------------------------------
# reclassify — DB pass (idempotence + restore + status safety)
# ---------------------------------------------------------------------------

def _meta(blob_id: str, title: str, institution: str | None = None) -> ArticleMeta:
    return ArticleMeta(
        blob_id=blob_id,
        article_url=f"https://marketdesk.ai/library/browse?item={blob_id}",
        blob_url=f"https://marketdesk.ai/files/{blob_id}/blob",
        title=title,
        institution=institution,
        published_at=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = db.connect(tmp_path / "t.sqlite")
    db.init_db(c)
    return c


def _seed(conn: sqlite3.Connection) -> None:
    # two exclude-worthy, two keepers, one already-COMPLETE excludable (must not move)
    db.upsert_discovered(conn, _meta("keep1", "Goldman China PMI Preview", "Goldman"))
    db.upsert_discovered(conn, _meta("keep2", "US Week Ahead", "JPM"))
    db.upsert_discovered(conn, _meta("drop_inst", "Random musings", "Zero Hedge"))
    db.upsert_discovered(conn, _meta("drop_geo", "Bank Negara Malaysia holds", "ING"))
    # a completed paper that WOULD match the exclusion — must be left untouched
    db.upsert_discovered(conn, _meta("done", "Thailand GDP", "UBS"))
    db.set_status(conn, "done", Status.COMPLETE)


def _status(conn: sqlite3.Connection, blob_id: str) -> str:
    return db.get_by_blob_id(conn, blob_id)["status"]


def test_reclassify_excludes_matching_downloadable(conn: sqlite3.Connection) -> None:
    _seed(conn)
    res = reclassify(conn)
    assert res.excluded_by_reason["institution"] == 1
    assert res.excluded_by_reason["minor_geo"] == 1
    assert res.total_excluded == 2
    assert _status(conn, "drop_inst") == Status.SKIPPED_EXCLUDED.value
    assert _status(conn, "drop_geo") == Status.SKIPPED_EXCLUDED.value
    # keepers stay downloadable; COMPLETE is untouched
    assert _status(conn, "keep1") == Status.DISCOVERED.value
    assert _status(conn, "keep2") == Status.DISCOVERED.value
    assert _status(conn, "done") == Status.COMPLETE.value


def test_reclassify_is_idempotent(conn: sqlite3.Connection) -> None:
    _seed(conn)
    reclassify(conn)
    before = {r["blob_id"]: r["status"] for r in conn.execute(
        "SELECT blob_id, status FROM papers"
    ).fetchall()}
    res2 = reclassify(conn)
    after = {r["blob_id"]: r["status"] for r in conn.execute(
        "SELECT blob_id, status FROM papers"
    ).fetchall()}
    assert before == after, "second run must be a no-op"
    # nothing newly excluded or restored on the second pass
    assert res2.total_excluded == 0
    assert res2.restored == 0


def test_reclassify_restores_when_list_shrinks(conn: sqlite3.Connection) -> None:
    _seed(conn)
    # first: exclude with the default list
    reclassify(conn)
    assert _status(conn, "drop_inst") == Status.SKIPPED_EXCLUDED.value
    # now shrink the exclude set (drop "zero hedge") + keep title patterns:
    # drop_inst no longer matches -> must be restored to DISCOVERED.
    smaller = {"the market ear", "tme"}
    res = reclassify(conn, exclude_institutions=smaller)
    assert res.restored == 1
    assert _status(conn, "drop_inst") == Status.DISCOVERED.value
    # the geo drop still matches (title-based) -> stays excluded
    assert _status(conn, "drop_geo") == Status.SKIPPED_EXCLUDED.value


def test_reclassify_reports_the_language_bucket(conn: sqlite3.Connection) -> None:
    """The new reason must be counted and sampled like every other bucket, and a
    German note must land SKIPPED_EXCLUDED rather than eating a download slot."""
    _seed(conn)
    db.upsert_discovered(
        conn, _meta("drop_de", "Konjunktur und Zinsen — Wochenausblick", "Vontobel")
    )
    db.upsert_discovered(
        conn, _meta("drop_zkb", "Ersteinschätzung Calida Group EN 2026 07 24", "ZKB")
    )
    res = reclassify(conn, dry_run=True)
    assert res.excluded_by_reason["language"] == 1          # the German title
    assert res.excluded_by_reason["institution"] == 2       # Zero Hedge + ZKB
    assert res.samples["language"] == ["Konjunktur und Zinsen — Wochenausblick"]
    assert "language=1" in res.summary()

    reclassify(conn)
    assert _status(conn, "drop_de") == Status.SKIPPED_EXCLUDED.value
    assert _status(conn, "drop_zkb") == Status.SKIPPED_EXCLUDED.value
    assert _status(conn, "keep1") == Status.DISCOVERED.value


def test_reclassify_dry_run_writes_nothing(conn: sqlite3.Connection) -> None:
    _seed(conn)
    before = {r["blob_id"]: r["status"] for r in conn.execute(
        "SELECT blob_id, status FROM papers"
    ).fetchall()}
    res = reclassify(conn, dry_run=True)
    after = {r["blob_id"]: r["status"] for r in conn.execute(
        "SELECT blob_id, status FROM papers"
    ).fetchall()}
    assert before == after, "dry-run must not write"
    assert res.dry_run is True
    assert res.total_excluded == 2
    # samples populated in dry-run
    assert res.samples["institution"], "expected sample titles in dry-run"
    assert res.samples["minor_geo"]
    # kept candidates = 5 candidates - 2 excluded (done is COMPLETE, not a candidate)
    # 3 candidates start (keep1/keep2/drop_inst/drop_geo are 4 candidates; done is COMPLETE)
    assert res.kept_candidates == 2  # 4 downloadable - 2 excluded


def test_reclassify_kept_per_day(conn: sqlite3.Connection) -> None:
    _seed(conn)
    res = reclassify(conn, dry_run=True)
    # all seeded rows share one published day (2026-07-07)
    assert res.distinct_published_days == 1
    assert res.kept_per_day == pytest.approx(res.kept_candidates / 1)


def test_reclassify_disabled_title_patterns_only_institutions(conn: sqlite3.Connection) -> None:
    _seed(conn)
    # patterns OFF => only the institution rule fires (geo drop stays a candidate)
    res = reclassify(conn, tagged_patterns=[])
    assert res.excluded_by_reason["institution"] == 1
    assert res.excluded_by_reason["minor_geo"] == 0
    assert _status(conn, "drop_geo") == Status.DISCOVERED.value
    assert _status(conn, "drop_inst") == Status.SKIPPED_EXCLUDED.value


# ---------------------------------------------------------------------------
# discovery integration — excluded papers get SKIPPED_EXCLUDED + skip /extra
# ---------------------------------------------------------------------------

def _cfg(tmp_path, monkeypatch):
    from marketdesk_extractor.config import Config
    for k, v in {
        "DATABASE_URL": str(tmp_path / "db" / "t.sqlite"),
        "OUTPUT_DIR": str(tmp_path / "data"),
        "RAW_PDF_DIR": str(tmp_path / "data" / "raw_pdfs"),
        "MARKDOWN_DIR": str(tmp_path / "data" / "markdown"),
        "METADATA_DIR": str(tmp_path / "data" / "metadata"),
        "MANIFEST_DIR": str(tmp_path / "data" / "manifests"),
        "LOG_DIR": str(tmp_path / "logs"),
        "MARKETDESK_PROFILE_DIR": str(tmp_path / "prof"),
        "R2_ENABLED": "false",
        "DROPBOX_ENABLED": "false",
        "PARSER_BACKEND": "none",
    }.items():
        monkeypatch.setenv(k, v)
    cfg = Config.from_env()
    cfg.ensure_dirs()
    return cfg


class _DiscoverClient:
    """Fake client: one keeper + one blog + one daily-FX paper. Records /extra calls."""

    T = 1782000000

    def __init__(self):
        self.extra_calls: list[str] = []

    PAPERS = [
        {"pathId": "keep", "name": "Goldman China PMI Preview",
         "type": "application/pdf", "t": T, "size": 100, "institution": "Goldman"},
        {"pathId": "blog", "name": "Daily musings on markets",
         "type": "application/pdf", "t": T, "size": 100, "institution": "Zero Hedge"},
        {"pathId": "fx", "name": "MUFG FX Daily Snapshot",
         "type": "application/pdf", "t": T, "size": 100, "institution": "MUFG"},
    ]

    def latest(self, institutions=None): return []
    def picks(self): return []
    def saved(self): return []
    def provision(self, ids): return []

    def walk_papers(self, *, since_unix=None, limit=None, max_days=None):
        yield from self.PAPERS

    def item_extra(self, item_id):
        self.extra_calls.append(item_id)
        return {"summary": "AI summary text"}


def test_discovery_excludes_and_skips_extra_fetch(tmp_path, monkeypatch) -> None:
    from marketdesk_extractor.discover import discover

    cfg = _cfg(tmp_path, monkeypatch)
    c = db.connect(cfg.database_url)
    db.init_db(c)
    client = _DiscoverClient()

    res = discover(cfg, c, client, limit=10)

    # one real new paper, two excluded
    assert res.discovered_new == 1
    assert res.excluded == 2
    assert "excluded=2" in res.summary()

    assert _status(c, "keep") == Status.DISCOVERED.value
    assert _status(c, "blog") == Status.SKIPPED_EXCLUDED.value
    assert _status(c, "fx") == Status.SKIPPED_EXCLUDED.value

    # CRITICAL: /extra (the AI-summary API call) is fetched ONLY for the keeper,
    # never for an excluded paper — that is the download-budget saving.
    assert client.extra_calls == ["keep"]

    # excluded rows recorded (exist in the DB) but keep no AI summary
    assert db.get_by_blob_id(c, "blog")["marketdesk_summary"] is None
    assert db.get_by_blob_id(c, "keep")["marketdesk_summary"] == "AI summary text"
