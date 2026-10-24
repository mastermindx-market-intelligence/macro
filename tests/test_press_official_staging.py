"""tests/test_press_official_staging.py — private official-feed staging rail.

Controls for ``scripts/stage_official_feed_press.py`` and the matching
``scripts/run_press.py`` emit guard.  The discriminating pairs:

  * bad hashes / clocks / unqualified source   → refuse, ZERO provider calls
  * existing staged or published source        → refuse, ZERO provider calls
  * full daily Brief cadence (all statuses)    → refuse, ZERO provider calls
  * same cadence booked YESTERDAY              → allowed (the ceiling is per DAY)
  * a slot both staged and published today     → counted once, not twice
  * a repeated slot                            → never a second provider call
  * writer failure                             → exactly ONE attempt, no regen
  * interrupted provider                       → retained exclusive checkpoint
  * successful private stage                   → exact source/ticker/fact-date
                                                 and receipt provenance, and the
                                                 ORDINARY (not 12k) token budget
  * run_emit on a passing official stage       → refusal, no content/site/ledger
                                                 write, provenance strip or not

Everything runs against a synthetic root under tmp_path.  Every test mocks the
writer at the module boundary — no test makes a network call, runs a provider,
or generates anything.  No CLI backdating exists to test: the flag is absent,
and that absence is itself pinned.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from engine.press import desk_planner as P  # noqa: E402
from engine.press import writer as W  # noqa: E402
from scripts import run_press as R  # noqa: E402
from scripts import stage_official_feed_press as S  # noqa: E402
from tests import press_fixtures as F  # noqa: E402

# The injected test clock.  The qualification's observed_at is 2026-10-14, so
# any real "today" before that date would refuse — which is exactly why the
# clock is an in-process parameter and never a CLI flag.
NOW = datetime(2026, 10, 14, 0, 25, 0, tzinfo=timezone.utc)

ITEM_URL = "https://www.occ.gov/news-issuances/news-releases/2026/nr-occ-2026-89.html"
FEED_URL = "https://www.occ.treas.gov/rss/occ_news.xml"

OCC_FEED_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<rss version="2.0">\n'
    "<channel>\n"
    "<title>OCC News</title>\n"
    "<link>https://www.occ.gov</link>\n"
    "<description>OCC enforcement news.</description>\n"
    "<item>\n"
    "<title>OCC Imposes $750 Million Assessment Against Bank of America for "
    "Deficient BSA/AML Compliance</title>\n"
    "<description>The Office of the Comptroller of the Currency (OCC) today "
    "announced a $750 million civil money penalty against Bank of America, N.A. "
    "(bank), for deficiencies in its Bank Secrecy Act compliance "
    "program.</description>\n"
    "<pubDate>13 Oct 2026 16:15:00 -0400</pubDate>\n"
    f"<link>{ITEM_URL}</link>\n"
    "<author>Office of the Comptroller of the Currency</author>\n"
    "</item>\n"
    "<item>\n"
    "<title>OCC Releases CRA Performance Evaluations</title>\n"
    "<description>The OCC today released a list of Community Reinvestment Act "
    "performance evaluations.</description>\n"
    "<pubDate>8 Oct 2026 17:30:00 -0400</pubDate>\n"
    "<link>https://www.occ.gov/news-issuances/news-releases/2026/nr-occ-2026-84.html</link>\n"
    "</item>\n"
    "</channel>\n"
    "</rss>\n"
)

MARKET_STATE = {
    "asof": "2026-10-13", "score": 56, "verdict": "MIXED",
    "components": [
        {"key": "trend", "label_en": "Trend & technicals", "score": 62, "weight": 0.24},
        {"key": "risk", "label_en": "Risk appetite", "score": 70, "weight": 0.18},
        {"key": "breadth", "label_en": "Breadth & participation", "score": 68, "weight": 0.16},
        {"key": "liquidity", "label_en": "Liquidity & credit", "score": 76, "weight": 0.14},
    ],
}
CONTEXT_FACT_IDS = (
    "market_state_score", "market_state_trend", "market_state_risk",
    "market_state_breadth", "market_state_liquidity",
)


def test_file_path_cli_prioritizes_own_repo_over_ambient_packages(tmp_path):
    """A later existing repo path must not leave a hostile package first."""
    import os
    import subprocess

    decoy = tmp_path / "ambient"
    for package in ("engine", "scripts"):
        package_dir = decoy / package
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text(
            'raise RuntimeError("foreign repository package imported")\n'
        )
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(decoy), str(_REPO))))
    result = subprocess.run(
        [sys.executable, str(_REPO / "scripts/stage_official_feed_press.py"), "--help"],
        cwd=tmp_path, env=env, text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--confirm-private-staging" in result.stdout


def _dump(path: Path, value) -> str:
    path.write_text(json.dumps(value, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _official_draft() -> dict:
    """A COMPLIANT draft for the fixture slot — validated, not invented.

    The numbers it carries are the fixture qualification's own reviewed source
    facts (the $750 million third-party claim and the reviewed market-state
    measurements), and the full real validator suite passes on it: the GREEN
    path in this file is genuinely exercised, never vacuous.
    """
    return {
        "title": "An enforcement test against a mixed backdrop",
        "description": ("A large banking agency action landed on a mixed reading "
                        "of our own measurements. Here is the level that would "
                        "change the picture."),
        "slug": "an-enforcement-test-against-a-mixed-backdrop",
        "body_html": (
            '<p class="press-byline">The Brief — Mastermind News desk</p>\n'
            "<p><a href=\"https://www.occ.gov/news-issuances/news-releases/2026/"
            "nr-occ-2026-89.html\">Office of the Comptroller of the Currency</a> "
            "moved against one of the largest American bank holding companies "
            "this week, and our own backdrop composite reads 56 of 100 as of the "
            "session before the announcement.</p>"
            "<p>Inside that composite, the trend component sits at 62 while risk "
            "appetite reads 70, which is a mixed posture rather than a stressed "
            "one, and it is the posture we carry into the enforcement read.</p>"
            "<p>Participation is still broader than credit is tight: breadth "
            "scores 68 against a liquidity reading of 76, so the system we are "
            "describing is one where money is moving and names are trading.</p>"
            "<p>The action itself is a penalty of 750, expressed in millions of "
            "dollars, and the agency describes it in its own summary as a civil "
            "money penalty tied to deficiencies in controls.</p>"
            "<p>Two things happened on the same afternoon and only one of them "
            "was priced, and the procedural one was the one everybody watched "
            "while the substantive one moved the number that actually matters "
            "for the names we follow here.</p>"
            "<p>Our own reading starts from what we can measure rather than from "
            "what the tape felt like, and on an afternoon like this one the "
            "difference between those two postures is the whole story, not a "
            "footnote to it.</p>"
            "<p>What would move our reading is the next composite print: the gap "
            "between 56 overall and 62 on trend is the spread we watch when an "
            "enforcement action lands on a systemically watched name.</p>"
            "<p>The obvious objection is that any single enforcement headline "
            "tells you very little on its own, and that objection is correct, "
            "which is exactly why the rest of this piece leans on measured "
            "levels instead of adjectives.</p>"
            "<p>Anyone who has watched this corner for a few years will "
            "recognise the shape of the day, and recognising a shape is not the "
            "same as knowing what comes next, so the honest version of this "
            "paragraph stops at the recognition.</p>\n"
            '<p class="press-footer">Educational content — not investment '
            "advice. Markets involve risk.</p>"
        ),
    }


def _stub_writer(monkeypatch, *, ok=True, reason="stubbed writer failure",
                 error: Exception | None = None) -> dict:
    """Mock engine.press.writer.write.  No LLM, no network, no generation."""
    calls = {"n": 0, "single_provider_attempt": [], "slots": []}

    def _write(slot, cfg, *, state=None, attempt=0, prior_failures=None,
               single_provider_attempt=False, admitted_token_cap=False):
        calls["n"] += 1
        calls["single_provider_attempt"].append(single_provider_attempt)
        calls["slots"].append(slot.get("id"))
        if error is not None:
            raise error
        if not ok:
            (state or W.RunState()).record_failure()
            return {"ok": False, "draft": None, "reason": reason, "provider": None,
                    "attempt": attempt, "state": (state or W.RunState()).snapshot()}
        return {"ok": True, "draft": _official_draft(), "reason": "",
                "provider": "stub", "model": "stub-model", "attempt": attempt,
                "state": (state or W.RunState()).snapshot()}

    monkeypatch.setattr(W, "write", _write)
    return calls


def _snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}


def _plan_offline(candidate: dict) -> dict:
    """The offline plan — no provider, no state.  Used to learn identities."""
    from engine.press.official_feed_candidate import plan_official_feed_candidate

    return plan_official_feed_candidate(
        feed_path=candidate["feed"], feed_sha256=candidate["feed_sha256"],
        qualification_path=candidate["qualification"],
        qualification_sha256=candidate["qualification_sha256"],
        root=candidate["root"], as_of=NOW.isoformat(), cfg=candidate["cfg"],
    )


def _stage(candidate: dict, monkeypatch=None, **kw) -> dict:
    if monkeypatch is not None:
        monkeypatch.delenv("PRESS_RUN_TOKEN_BUDGET", raising=False)
        monkeypatch.delenv("PRESS_CIRCUIT_BREAKER_FAILURES", raising=False)
    return S.stage_official_feed_candidate(
        candidate["root"], candidate["cfg"],
        feed_path=candidate["feed"], feed_sha256=candidate["feed_sha256"],
        qualification_path=candidate["qualification"],
        qualification_sha256=candidate["qualification_sha256"],
        now=NOW, **kw)


@pytest.fixture
def candidate(tmp_path) -> dict:
    """Hash-bound retained feed + qualification over a minimal repo root."""
    root = F.fixture_root(tmp_path / "root")
    (root / "site/stocks").mkdir(parents=True, exist_ok=True)
    (root / "site/stocks/BAC.html").write_text("<html>Bank of America</html>")

    measured = tmp_path / "market_state.json"
    digest = _dump(measured, MARKET_STATE)
    shutil.copyfile(measured, root / "data/market_state/latest.json")

    feed = tmp_path / "occ_news.xml"
    feed.write_bytes(OCC_FEED_XML.encode("utf-8"))
    feed_sha = hashlib.sha256(feed.read_bytes()).hexdigest()

    q = {
        "kind": "official_feed_editorial_qualification",
        "source_key": "occ_news", "feed_url": FEED_URL,
        "feed_sha256": feed_sha, "item_url": ITEM_URL,
        "published_at": "2026-10-13T20:15:00+00:00",
        "event_date": "2026-10-13",
        "observed_at": "2026-10-14T00:19:37+00:00",
        "rights_basis": {
            "qualification": "government_authored_factual_reporting",
            "scope": ("Original factual reporting of the agency assessment; "
                      "no imagery or endorsement."),
        },
        "review_result": "accepted_as_editorial_candidate_only",
        "reviewed_claims": [{"literal": "$750 million civil money penalty",
                             "quantity_literal": "$750 million"}],
        "reviewed_tickers": {"BAC": "Bank of America"},
        "allow_stage": False, "allow_emit": False, "publication_approved": False,
        "first_party_context": [
            {"id": fid, "artifact": "data/market_state/latest.json",
             "sha256": digest,
             "relevance": ("Dated broad backdrop only; not an explanation of "
                           "bank-specific price effects.")}
            for fid in CONTEXT_FACT_IDS
        ],
    }
    qpath = tmp_path / "qualification.json"
    return {"root": root, "feed": feed, "feed_sha256": feed_sha,
            "qualification": qpath, "qualification_sha256": _dump(qpath, q),
            "cfg": P.load_config(root), "market_state_sha256": digest}


# ─────────────────────────────────────────────────────────────────────────────
# GREEN: the successful private stage
# ─────────────────────────────────────────────────────────────────────────────


def test_successful_private_stage_keeps_exact_source_identity(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    root = candidate["root"]
    before = _snapshot(root)

    out = _stage(candidate, monkeypatch)

    assert out["staged"] is True
    assert out["public_article_approved"] is False and out["allow_emit"] is False
    assert out["status"] == "passed"
    assert calls["n"] == 1 and calls["single_provider_attempt"] == [True]

    # Nothing was written outside the canonical staging tree.
    new = _snapshot(root) - before
    assert new, "the stage produced nothing at all"
    assert all(p.startswith("data/press/staging/") for p in new), sorted(new)

    record = json.loads((root / "data/press/staging" / f"{out['staged_slot_id']}.json")
                        .read_text(encoding="utf-8"))
    assert record["desk"] == "brief" and record["as_of"] == "2026-10-14"
    assert record["source_revisions"][out["source_ref"]] == "sha256:" + candidate["feed_sha256"]
    assert record["source_revisions"]["artifact:data/market_state/latest.json"] == \
        "sha256:" + candidate["market_state_sha256"]
    # The source facts, their dates and the primary source are the plan's own.
    lead = record["slot"]["facts"][0]
    assert lead["text"] == "$750 million civil money penalty"
    assert lead["values"] == ["750"] and lead["tier"] == "third_party"
    assert lead["dated"] == "2026-10-13", "each fact date must be preserved"
    assert record["slot"]["primary_source"] == {
        "kind": "external", "name": "Office of the Comptroller of the Currency",
        "url": ITEM_URL,
    }
    assert record["slot"]["allowed_links"] == \
        ["https://www.mastermind-x.com/stocks/BAC.html"]
    # Explicit private-official provenance with public approval false.
    receipt = record["provenance"]["admission_receipt"]
    assert receipt["rail"] == "private_official_feed"
    assert receipt["public_article_approved"] is False
    assert receipt["feed_sha256"] == candidate["feed_sha256"]
    assert receipt["qualification_sha256"] == candidate["qualification_sha256"]
    # The ORDINARY Press budget — the earnings 12k contract is not borrowed.
    assert out["writer_state"]["token_budget"] == 240_000
    assert out["writer_state"]["token_budget"] != 12_000
    assert out["cadence"]["consumed_before"] == 0 and out["cadence"]["ceiling"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# RED: refusals — every one of them spends ZERO provider calls
# ─────────────────────────────────────────────────────────────────────────────


def test_bad_feed_hash_refuses_without_provider(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    candidate["feed"].write_bytes(candidate["feed"].read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash"):
        _stage(candidate, monkeypatch)
    assert calls["n"] == 0
    assert not (candidate["root"] / "data/press/staging" / "_run_summary.json").exists()


def test_changed_bytes_against_stale_qualification_refuse(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    candidate["feed"].write_bytes(candidate["feed"].read_bytes() + b" ")
    candidate["feed_sha256"] = hashlib.sha256(candidate["feed"].read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="identity mismatch"):
        _stage(candidate, monkeypatch)
    assert calls["n"] == 0


def test_bad_qualification_hash_refuses_without_provider(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    candidate["qualification_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        _stage(candidate, monkeypatch)
    assert calls["n"] == 0


@pytest.mark.parametrize("patch", [
    {"source_key": "cnbc_top"},
    {"allow_stage": True},
    {"allow_emit": True},
    {"publication_approved": True},
    {"review_result": "accepted_as_full_release"},
    {"published_at": "2026-10-13T21:15:00+00:00"},
    {"event_date": "2026-10-01"},
    {"reviewed_claims": [{"literal": "$950 million civil money penalty",
                          "quantity_literal": "$950 million"}]},
])
def test_unqualified_or_mutated_source_refuses_without_provider(candidate, monkeypatch, patch):
    calls = _stub_writer(monkeypatch)
    q = json.loads(candidate["qualification"].read_text())
    q.update(patch)
    candidate["qualification_sha256"] = _dump(candidate["qualification"], q)
    with pytest.raises(ValueError):
        _stage(candidate, monkeypatch)
    assert calls["n"] == 0


@pytest.mark.parametrize("days", [10, -1])
def test_stale_or_backdated_clock_refuses_without_provider(candidate, monkeypatch, days):
    calls = _stub_writer(monkeypatch)
    shifted = NOW + timedelta(days=days)
    with pytest.raises(ValueError, match="window|clock"):
        S.stage_official_feed_candidate(
            candidate["root"], candidate["cfg"],
            feed_path=candidate["feed"], feed_sha256=candidate["feed_sha256"],
            qualification_path=candidate["qualification"],
            qualification_sha256=candidate["qualification_sha256"],
            now=shifted)
    assert calls["n"] == 0


def test_existing_published_source_refuses_without_provider(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    plan = _plan_offline(candidate)
    ledger = candidate["root"] / "data/press/published.jsonl"
    row = {"id": "press-brief-prior", "ts": "2026-10-14T01:00:00Z", "desk": "brief",
           "slug": "prior-piece", "sources": [plan["source_ref"]]}
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    out = _stage(candidate, monkeypatch)
    assert out["staged"] is False
    assert "coverage" in out["reason"]
    assert calls["n"] == 0


def test_existing_staged_source_refuses_without_provider(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    plan = _plan_offline(candidate)
    stage_dir = candidate["root"] / "data/press/staging"
    (stage_dir / "prior.json").write_text(json.dumps(
        {"id": "press-brief-prior", "desk": "brief", "status": "in_progress",
         "staged_at": "2026-10-14T00:20:00Z", "sources": [plan["source_ref"]]}))
    out = _stage(candidate, monkeypatch)
    assert out["staged"] is False
    assert "canonical staging tree" in out["reason"]
    assert calls["n"] == 0


def _book_brief_attempt(root: Path, slot_id: str, *, staged_at: str,
                        status: str = "quarantined") -> None:
    stage_dir = root / "data/press/staging"
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / f"{slot_id}.json").write_text(json.dumps(
        {"id": slot_id, "desk": "brief", "status": status, "staged_at": staged_at,
         "as_of": staged_at[:10], "sources": [f"chronicle:{slot_id}"], "slug": ""}))


def test_full_daily_brief_cadence_refuses_without_provider(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    _book_brief_attempt(candidate["root"], "press-brief-d1-a",
                        staged_at="2026-10-14T00:05:00Z", status="quarantined")
    _book_brief_attempt(candidate["root"], "press-brief-d1-b",
                        staged_at="2026-10-14T00:10:00Z", status="in_progress")
    out = _stage(candidate, monkeypatch)
    assert out["staged"] is False
    assert "cadence" in out["reason"]
    assert calls["n"] == 0


def test_same_cadence_booked_yesterday_still_stages(candidate, monkeypatch):
    """The discriminating half of the ceiling: it counts TODAY, not the slot."""
    calls = _stub_writer(monkeypatch)
    _book_brief_attempt(candidate["root"], "press-brief-d0-a",
                        staged_at="2026-10-13T00:05:00Z")
    _book_brief_attempt(candidate["root"], "press-brief-d0-b",
                        staged_at="2026-10-13T00:10:00Z")
    out = _stage(candidate, monkeypatch)
    assert out["staged"] is True and calls["n"] == 1
    assert out["cadence"]["consumed_before"] == 0


def test_published_rows_count_and_double_counting_does_not(candidate, monkeypatch):
    """A slot both staged and published today is ONE attempt, not two."""
    calls = _stub_writer(monkeypatch)
    _book_brief_attempt(candidate["root"], "press-brief-dup",
                        staged_at="2026-10-14T00:05:00Z")
    ledger = candidate["root"] / "data/press/published.jsonl"
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": "press-brief-dup", "ts": "2026-10-14T02:00:00Z",
                             "desk": "brief", "slug": "dup",
                             "sources": ["chronicle:press-brief-dup"]}) + "\n")
    out = _stage(candidate, monkeypatch)
    assert out["staged"] is True
    assert out["cadence"]["consumed_before"] == 1, "staged+published must count once"
    assert calls["n"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# The slot discipline: replay, single attempt, interruption
# ─────────────────────────────────────────────────────────────────────────────


def test_repeated_slot_refuses_and_never_replays_the_provider(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    first = _stage(candidate, monkeypatch)
    assert first["staged"] is True and calls["n"] == 1

    # The live staged ref blocks the straight repeat.
    second = _stage(candidate, monkeypatch)
    assert second["staged"] is False and calls["n"] == 1
    assert "canonical staging tree" in second["reason"]

    # Even once the record is superseded (the reconciliation's audit state,
    # which no longer blocks by ref), the same slot identity can never
    # overwrite or replay its checkpoint.
    path = candidate["root"] / first["staging_path"]
    record = json.loads(path.read_text(encoding="utf-8"))
    record["status"] = "superseded"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    third = _stage(candidate, monkeypatch)
    assert third["staged"] is False and "replay" in third["reason"]
    assert calls["n"] == 1, "the same slot can never reach the provider twice"


def test_writer_failure_makes_exactly_one_attempt_and_no_regeneration(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch, ok=False, reason="provider_unavailable")
    out = _stage(candidate, monkeypatch)
    assert out["staged"] is True and out["status"] == "quarantined"
    assert calls["n"] == 1
    record = json.loads((candidate["root"] / "data/press/staging"
                         / f"{out['staged_slot_id']}.json").read_text(encoding="utf-8"))
    assert record["status"] == "quarantined"
    assert len(record["attempts"]) == 1


def test_interrupted_provider_retains_exclusive_checkpoint(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch, error=RuntimeError("provider socket died"))
    with pytest.raises(RuntimeError, match="socket died"):
        _stage(candidate, monkeypatch)
    assert calls["n"] == 1
    plan = _plan_offline(candidate)
    record = json.loads((candidate["root"] / "data/press/staging"
                         / f"{S._stable_slot_id(plan)}.json").read_text(encoding="utf-8"))
    assert record["status"] == "in_progress"
    assert record["progress"] == {"phase": "provider_started", "attempt": 0}
    assert record.get("draft") is None, "an interrupted slot retains no draft"

    # The retained reservation blocks any restage of the same source.
    calls2 = _stub_writer(monkeypatch)
    out = _stage(candidate, monkeypatch)
    assert out["staged"] is False
    assert "canonical staging tree" in out["reason"]
    assert calls2["n"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# The emit guard: fail closed, provenance strip or not
# ─────────────────────────────────────────────────────────────────────────────


def _emit_snapshot(root: Path) -> dict:
    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
    return {
        "tree": _snapshot(root),
        "ledger": _digest(root / "data/press/published.jsonl"),
    }


def test_emit_refuses_private_official_despite_passing_report(candidate, monkeypatch):
    _stub_writer(monkeypatch)
    out = _stage(candidate, monkeypatch)
    assert out["staged"] is True and out["status"] == "passed"

    before = _emit_snapshot(candidate["root"])
    result = R.run_emit(candidate["root"], candidate["cfg"])
    after = _emit_snapshot(candidate["root"])

    assert result["emitted"] == 0
    record = json.loads((candidate["root"] / out["staging_path"]).read_text(encoding="utf-8"))
    assert record["status"] == "approval_required"
    assert "public-article approval" in record["quarantine_reason"]
    assert "earnings" not in record["quarantine_reason"], \
        "the official refusal must be the official guard's, not the earnings guard's"
    # No content write, no site write, no ledger row — despite validator status
    # passed — and the audit record is retained, not consumed.
    assert after["ledger"] == before["ledger"]
    assert after["tree"] - before["tree"] == set()
    assert list((candidate["root"] / "content/seo/blog").glob("*.md")) == []
    assert not (candidate["root"] / "site" / "blog").exists()
    assert (candidate["root"] / out["staging_path"]).exists()


def test_emit_refusal_survives_a_provenance_strip(candidate, monkeypatch):
    _stub_writer(monkeypatch)
    out = _stage(candidate, monkeypatch)
    path = candidate["root"] / out["staging_path"]
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop("provenance")
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")

    before = _emit_snapshot(candidate["root"])
    result = R.run_emit(candidate["root"], candidate["cfg"])
    after = _emit_snapshot(candidate["root"])

    assert result["emitted"] == 0
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["status"] == "approval_required"
    assert after["ledger"] == before["ledger"]
    assert after["tree"] - before["tree"] == set()


def test_emit_guards_do_not_cross_label_the_rails():
    official = {"id": "press-external-abc123", "desk": "brief",
                "sources": ["official_feed:abc123"],
                "slot": {"id": "press-external-abc123",
                         "sources": ["official_feed:abc123"]}}
    assert R._is_private_official_stage(official) is True
    assert R._is_unverified_earnings_story_stage(official) is False
    earnings = {"id": "press-earnings-2026-x",
                "sources": ["chronicle:defeatbeta:AAPL:2026Q3"]}
    assert R._is_unverified_earnings_story_stage(earnings) is True
    assert R._is_private_official_stage(earnings) is False
    ordinary = {"id": "press-brief-2026-07-26-x",
                "sources": ["chronicle:risk_radar_forward_log#2026-07-24"]}
    assert R._is_private_official_stage(ordinary) is False
    assert R._is_unverified_earnings_story_stage(ordinary) is False


# ─────────────────────────────────────────────────────────────────────────────
# CLI: explicit authorization, and no backdating
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_refuses_without_the_explicit_private_staging_acknowledgement(tmp_path, capsys):
    rc = S.main(["--feed", "f.xml", "--feed-sha256", "0" * 64,
                 "--qualification", "q.json", "--qualification-sha256", "0" * 64])
    assert rc == 1
    # House law: the annotation is a bare line-start print BEFORE the JSON.
    printed = capsys.readouterr().out
    out = json.loads(printed[printed.index("{"):])
    assert out["staged"] is False and "confirm" in out["reason"]


def test_cli_offers_no_backdating_flag(candidate):
    with pytest.raises(SystemExit) as exc:
        S.main(["--feed", str(candidate["feed"]),
                "--feed-sha256", candidate["feed_sha256"],
                "--qualification", str(candidate["qualification"]),
                "--qualification-sha256", candidate["qualification_sha256"],
                "--as-of", "2026-10-01"])
    assert exc.value.code == 2, "an unknown flag must be an argparse error"


@pytest.mark.parametrize('payload', ['{', '[]', '{}'])
def test_corrupt_staging_accounting_refuses_before_provider(candidate, monkeypatch, payload):
    calls = _stub_writer(monkeypatch)
    (candidate['root'] / 'data/press/staging/unreadable.json').write_text(payload)
    with pytest.raises(ValueError, match='staging|accounting'):
        _stage(candidate, monkeypatch)
    assert calls['n'] == 0


@pytest.mark.parametrize('payload', ['{\n', '[]\n', '{}\n'])
def test_corrupt_published_accounting_refuses_before_provider(candidate, monkeypatch, payload):
    calls = _stub_writer(monkeypatch)
    (candidate['root'] / 'data/press/published.jsonl').write_text(payload)
    with pytest.raises(ValueError, match='ledger|accounting'):
        _stage(candidate, monkeypatch)
    assert calls['n'] == 0


def test_changed_guid_and_revision_cannot_replay_superseded_release(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    first = _stage(candidate, monkeypatch)
    path = candidate['root'] / first['staging_path']
    obj = json.loads(path.read_text())
    obj['status'] = 'superseded'
    path.write_text(json.dumps(obj))
    raw = candidate['feed'].read_text().replace('<item>', '<item><guid>changed-guid</guid>', 1)
    candidate['feed'].write_text(raw)
    candidate['feed_sha256'] = hashlib.sha256(candidate['feed'].read_bytes()).hexdigest()
    q = json.loads(candidate['qualification'].read_text())
    q['feed_sha256'] = candidate['feed_sha256']
    candidate['qualification_sha256'] = _dump(candidate['qualification'], q)
    second = _stage(candidate, monkeypatch)
    assert second['staged'] is False
    assert calls['n'] == 1


def test_cadence_normalizes_offset_timestamps_to_utc(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    for n in range(2):
        _book_brief_attempt(candidate['root'], f'offset-{n}',
                            staged_at='2026-10-13T20:05:00-04:00')
    out = _stage(candidate, monkeypatch)
    assert out['staged'] is False and calls['n'] == 0


def test_staging_path_cannot_escape_canonical_root(candidate, monkeypatch, tmp_path):
    calls = _stub_writer(monkeypatch)
    candidate['cfg']['paths']['staging_dir'] = str(tmp_path / 'elsewhere')
    with pytest.raises(ValueError, match='canonical'):
        _stage(candidate, monkeypatch)
    assert calls['n'] == 0


def test_emit_refusal_survives_source_metadata_strip(candidate, monkeypatch):
    _stub_writer(monkeypatch)
    out = _stage(candidate, monkeypatch)
    path = candidate['root'] / out['staging_path']
    record = json.loads(path.read_text())
    assert record['status'] == 'passed'
    for holder in (record, record['slot']):
        for key in ('provenance', 'sources', 'seed_refs', 'source_revisions'):
            holder.pop(key, None)
    path.write_text(json.dumps(record))
    before = _emit_snapshot(candidate['root'])
    result = R.run_emit(candidate['root'], candidate['cfg'])
    assert result['emitted'] == 0
    assert json.loads(path.read_text())['status'] == 'approval_required'
    assert _emit_snapshot(candidate['root']) == before


def test_published_slot_identity_blocks_replay_without_source_refs(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    slot_id = S._stable_slot_id(_plan_offline(candidate))
    row = {'id': slot_id, 'desk': 'brief', 'ts': '2026-10-13T21:00:00Z',
           'sources': [], 'seed_refs': [], 'slug': 'prior-official'}
    (candidate['root'] / 'data/press/published.jsonl').write_text(json.dumps(row)+'\n')
    out = _stage(candidate, monkeypatch)
    assert out['staged'] is False and calls['n'] == 0


def test_no_first_party_context_refuses_before_any_provider_or_checkpoint(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    q = json.loads(candidate['qualification'].read_text())
    q.pop('first_party_context')
    candidate['qualification_sha256'] = _dump(candidate['qualification'], q)
    before = _snapshot(candidate['root'])
    out = _stage(candidate, monkeypatch)
    assert out['staged'] is False and 'first-party' in out['reason']
    assert calls['n'] == 0 and _snapshot(candidate['root']) == before


@pytest.mark.parametrize('clock', ['', None, 0, False, ' '])
def test_explicit_empty_clock_cannot_fall_back_to_previous_date(candidate, monkeypatch, clock):
    calls = _stub_writer(monkeypatch)
    row = {'id': 'prior', 'desk': 'brief', 'staged_at': clock,
           'as_of': '2026-10-13', 'sources': []}
    (candidate['root'] / 'data/press/staging/prior.json').write_text(json.dumps(row))
    with pytest.raises(ValueError, match='clock'):
        _stage(candidate, monkeypatch)
    assert calls['n'] == 0


def test_official_facts_keep_private_guard_when_mutable_labels_are_removed(candidate, monkeypatch):
    _stub_writer(monkeypatch)
    monkeypatch.setattr(R, '_render_blog_subtree', lambda root: ([], []))
    out = _stage(candidate, monkeypatch)
    path = candidate['root'] / out['staging_path']
    record = json.loads(path.read_text())
    assert record['status'] == 'passed'
    for holder in (record, record['slot']):
        for key in ('provenance', 'sources', 'seed_refs', 'source_revisions'):
            holder.pop(key, None)
        holder['id'] = 'press-brief-renamed'
    path.write_text(json.dumps(record))
    before = _emit_snapshot(candidate['root'])
    result = R.run_emit(candidate['root'], candidate['cfg'])
    assert result['emitted'] == 0
    assert _emit_snapshot(candidate['root']) == before


def test_insufficient_distinct_receipts_refuses_before_spending_attempt(candidate, monkeypatch):
    calls = _stub_writer(monkeypatch)
    q = json.loads(candidate['qualification'].read_text())
    q['first_party_context'] = q['first_party_context'][:1]
    candidate['qualification_sha256'] = _dump(candidate['qualification'], q)
    before = _snapshot(candidate['root'])
    out = _stage(candidate, monkeypatch)
    assert out['staged'] is False and 'receipt' in out['reason']
    assert calls['n'] == 0 and _snapshot(candidate['root']) == before
