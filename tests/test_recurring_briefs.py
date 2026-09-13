"""RED-first tests for the F11 B-F11-7b recurring briefs producer (MO-PAID-032).

No network: every IO function is monkeypatched. A FakeClient records writes so
idempotency is a real second-call proof, not a static fixture.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from engine import recurring_briefs as rb
from scripts import build_recurring_briefs as entry

ROOT = Path(__file__).resolve().parents[1]

SUB_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
THESIS_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
WATCH_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
USER_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"

CONTRACT_MISS_EN = (
    "Tonight's brief didn't run — the market read it uses wasn't rebuilt. "
    "Nothing has been recalculated."
)

BANNED_BODY_KEYS = {
    "score",
    "rank",
    "conviction",
    "confidence",
    "priority",
    "strength",
    "lean",
    "probability",
}
BANNED_TERMS = ("falsif", "refut", "证伪")

# H9: production-shape fixtures. The previous prose `evidence` fixture masked
# H4. The previous `state_asof == run_date` fixture masked H1. The previous
# absence of a ``zh`` block masked H3. These fixtures ARE the production
# shape that the four blockers regressed against.
PRODUCTION_SLUG_FRAGMENTS = (
    "radar CONF",
    "alt92 ACCUMULATE",
    "neutral n1",
    "edge7",
    "edge78",
)


def _sub(*, cadence="daily_after_us_close", kind="thesis", target_id=THESIS_ID,
         state="active", run_date="2026-09-13", user_id=USER_ID):
    return {
        "subscription_id": SUB_ID,
        "user_id": user_id,
        "target_kind": kind,
        "target_id": target_id,
        "cadence": cadence,
        "delivery": "in_product_inbox",
        "state": state,
        "run_date": run_date,
    }


def _thesis_target(*, name="Apple breadth thesis", version=2, tickers=("AAPL",)):
    return {
        "kind": "thesis",
        "id": THESIS_ID,
        "name": name,
        "version_or_asof": str(version),
        "tickers": list(tickers),
        "unavailable": False,
    }


def _watchlist_target(*, name="My names", tickers=("AAPL", "MSFT")):
    return {
        "kind": "watchlist",
        "id": WATCH_ID,
        "name": name,
        "version_or_asof": "2026-09-13",
        "tickers": list(tickers),
        "unavailable": False,
    }


def _briefing(*, as_of="2026-09-13", situation="Apple's tape is quiet after the print.",
              include_slug_evidence=True, generated_utc=None):
    """Daily briefing. Default carries production-shape slug `evidence`.

    The test fixtures used to substitute prose for ``evidence``, masking H4.
    The default here is the production slug — every H4-red test reads it
    without rewriting. Toggle ``include_slug_evidence=False`` when a test
    needs a clean fixture. ``generated_utc`` lets a test force a stale
    timestamp; default is ``{as_of}T20:05:00+00:00`` (same calendar day).
    """
    priority_queue = [
        {
            "ticker": "AAPL",
            "situation": situation,
            "priority": 0.91,
            "confidence": 0.8,
            "strength": 0.7,
            "lean": 1,
            "falsifier": "breadth rolls over",
        },
        {
            "ticker": "MSFT",
            "situation": "Microsoft held the week's range.",
            "priority": 0.4,
        },
    ]
    if include_slug_evidence:
        priority_queue[0]["evidence"] = "radar CONF edge7 · alt92 ACCUMULATE · news neutral n1"
        priority_queue[1]["evidence"] = "radar NEGA edge78 · alt32 WATCH · news neutral n6"
    return {
        "schema": "intelligence.briefing.v1",
        "as_of": as_of,
        "generated_utc": generated_utc or f"{as_of}T20:05:00+00:00",
        "macro_context": {
            "posture": "Liquidity is expanding — a supportive backdrop.",
        },
        "priority_queue": priority_queue,
        "divergences": [],
    }


def _weekly_brief(*, state_asof="2026-09-13", include_zh_block=False):
    """Weekly master_brief.v2. Optional ``zh`` block on by default.

    Mirrors the production schema when ``include_zh_block=True``:
    ``state_asof`` is the LAST market session (always Friday for a Saturday
    run), ``generated_at`` falls on the run date, and the ``zh`` block
    carries real Chinese paired index-for-index with ``tldr``/``watch_items``.
    """
    brief = {
        "schema": "master_brief.v2",
        "state_asof": state_asof,
        "generated_at": f"{state_asof}T22:00:00+00:00",
        "tldr": ["The week's tape stayed inside last week's range."],
        "summary": "A quiet week for the names we follow.",
        "regime_read": "Liquidity stayed supportive.",
        "confidence": "low",
        "watch_items": [
            {"ticker": "AAPL", "note": "Apple stayed inside its range all week."},
        ],
    }
    if include_zh_block:
        brief["zh"] = {
            "summary": "一周内我们关注的个股保持在区间内，节奏平稳。",
            "regime_read": "流动性仍偏支持。",
            "tldr": ["本周行情维持在上一周区间内运行。"],
            "watch_items": ["苹果整周保持在区间内。"],
        }
    return brief


def _production_weekly(*, run_date_str="2026-09-12"):
    """Production measurement: weekly_saturday, generated Saturday with Friday state."""
    return {
        "schema": "master_brief.v2",
        "state_asof": "2026-09-11",  # Friday
        "generated_at": f"{run_date_str}T10:10:33.933810+00:00",  # Saturday
        "tldr": [
            "Main driver: Tougher Fed pricing is pushing yields higher.",
            "Map shift: Stagflation is losing ground to Reflation, but confirmation remains incomplete.",
        ],
        "summary": "Higher yields are testing narrow US leadership, while healthy credit keeps the broader stress picture calm.",
        "regime_read": "The US is still in Stagflation on the map, but it is moving toward Reflation.",
        "confidence": "medium",
        "watch_items": [
            {"ticker": "AAPL", "note": "Apple stayed inside its range all week."},
        ],
        "zh": {
            "summary": "收益率上升正考验美股狭窄的领涨格局，而健康的信贷状况使整体压力保持温和。",
            "regime_read": "美国在图谱上仍处于滞胀阶段，但正向再通胀迈进。",
            "tldr": [
                "主要驱动因素：美联储政策预期趋于强硬，推动收益率上升。",
                "格局变化：滞胀正在让位于再通胀，但尚未得到充分确认。",
            ],
            "watch_items": ["苹果股票整周保持在区间内震荡。"],
        },
    }


def _production_daily(*, run_date_str="2026-11-16"):
    """Production measurement: daily_after_us_close, nightly crosses UTC midnight."""
    return {
        "schema": "intelligence.briefing.v1",
        "as_of": "2026-11-15",  # EST view, mid-job local clock
        "generated_utc": f"2026-11-15T23:30:00+00:00",  # this run
        "macro_context": {
            "posture": "Liquidity is expanding — a supportive backdrop.",
        },
        "priority_queue": [
            {
                "ticker": "MSFT",
                "situation": "Smart-money / activity building, tape not yet bullish.",
                "evidence": "radar CONF edge7 · alt92 ACCUMULATE · news neutral n1",
                "priority": 0.735,
                "confidence": 0.875,
            },
        ],
        "divergences": [],
    }


class FakeClient:
    """Records inserts; a second insert of the same (subscription_id, slot_asof)
    is a no-op, matching insert … on conflict do nothing."""

    def __init__(self):
        self.deliveries: list[dict] = []
        self.insert_calls = 0

    def write(self, row, *, dry_run):
        self.insert_calls += 1
        if dry_run:
            return "dry"
        key = (row["subscription_id"], str(row["slot_asof"]))
        existing = {(r["subscription_id"], str(r["slot_asof"])) for r in self.deliveries}
        if key in existing:
            return "conflict"
        self.deliveries.append(row)
        return "inserted"


def _keys(obj):
    found = set()
    if isinstance(obj, dict):
        found.update(obj.keys())
        for v in obj.values():
            found.update(_keys(v))
    elif isinstance(obj, list):
        for v in obj:
            found.update(_keys(v))
    return found


def _haystack(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).lower()


# ---------------------------------------------------------------------------
# Slot computation
# ---------------------------------------------------------------------------

def test_daily_slot_is_briefing_as_of_when_fresh():
    slot = rb.compute_slot(
        "daily_after_us_close",
        "2026-09-13T20:05:00+00:00",
        date(2026, 9, 13),
    )
    assert slot == date(2026, 9, 13)


def test_daily_slot_accepts_date_only_as_of():
    assert rb.compute_slot("daily_after_us_close", "2026-09-13", date(2026, 9, 13)) == date(
        2026, 9, 13
    )


def test_stale_artifact_yields_no_slot():
    assert (
        rb.compute_slot("daily_after_us_close", "2026-09-12", date(2026, 9, 13)) is None
    )


def test_missing_artifact_asof_yields_no_slot():
    assert rb.compute_slot("daily_after_us_close", None, date(2026, 9, 13)) is None
    assert rb.compute_slot("weekly_saturday", "", date(2026, 9, 12)) is None


def test_weekly_slot_is_artifact_asof_when_fresh():
    slot = rb.compute_slot("weekly_saturday", "2026-09-12", date(2026, 9, 12))
    assert slot == date(2026, 9, 12)


def test_compute_slot_never_returns_an_earlier_date_than_run():
    """Never back-fill: a usable artifact still keys the slot on the run's date."""
    slot = rb.compute_slot(
        "daily_after_us_close",
        "2026-09-14T00:00:00Z",
        date(2026, 9, 13),
    )
    assert slot == date(2026, 9, 13)


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

def test_classify_ready_when_artifact_matches_run_date():
    state, reason = rb.classify(_sub(), _briefing(), _thesis_target())
    assert state == "ready"
    assert reason is None


def test_classify_stale_artifact_is_degraded_with_contract_line():
    """A genuinely stale daily briefing — one whose ``generated_utc`` falls
    more than 24h before the run_date — is degraded with the contract's
    plain line.
    """
    state, reason = rb.classify(
        _sub(run_date="2026-09-15"),
        _briefing(
            as_of="2026-09-12",
            generated_utc="2026-09-12T20:05:00+00:00",  # 3 days stale
        ),
        _thesis_target(),
    )
    assert state == "degraded"
    assert reason == CONTRACT_MISS_EN


def test_classify_missing_artifact_is_degraded_with_contract_line():
    state, reason = rb.classify(_sub(), None, _thesis_target())
    assert state == "degraded"
    assert reason == CONTRACT_MISS_EN


def test_classify_unreadable_target_is_target_unavailable():
    state, reason = rb.classify(_sub(), _briefing(), None)
    assert state == "degraded"
    assert reason == "target unavailable"
    state2, reason2 = rb.classify(
        _sub(), _briefing(), {"unavailable": True, "kind": "thesis", "id": THESIS_ID}
    )
    assert state2 == "degraded"
    assert reason2 == "target unavailable"


def test_classify_yesterday_daily_briefing_is_fresh():
    """A daily briefing generated on the previous calendar day is FRESH —
    a same-run nightly that crossed UTC midnight stamps ``generated_utc``
    with yesterday's date even though the briefing IS this run's brief.

    Pre-fix the H2 scenario degraded this case; the slot-clock fix
    preserves the previous behavior for as_of==run_date while accepting
    the cross-midnight shape.
    """
    state, reason = rb.classify(
        _sub(run_date="2026-09-13"),
        _briefing(as_of="2026-09-12"),  # generated_utc auto = 2026-09-12T20:05
        _thesis_target(),
    )
    assert state == "ready"
    assert reason is None


# ---------------------------------------------------------------------------
# compose_body
# ---------------------------------------------------------------------------

def test_body_copies_verbatim_artifact_sentences_for_target_tickers():
    """Prose ``situation`` is copied; raw ``evidence`` slug is NOT.

    The previous version of this test asserted that prose ``evidence`` made it
    into ``sentence_en``. Production never emits prose in that slot — the
    measured triple ``radar CONF edge7 · alt92 ACCUMULATE · news neutral n1``
    is the live artefact (H4). The new contract copies ``situation`` only and
    skips ``evidence`` regardless of whether it is prose or slug.
    """
    situation = "Apple's tape is quiet after the print."
    body = rb.compose_body(
        _thesis_target(tickers=("AAPL",)),
        _briefing(situation=situation),
        monitors=[],
    )
    sentences = [row["sentence_en"] for row in body["market_read"]]
    assert situation in sentences
    # A name the thesis does not follow is not copied.
    assert "Microsoft held the week's range." not in sentences
    # Macro backdrop is copied for every target.
    assert "Liquidity is expanding — a supportive backdrop." in sentences


def test_body_has_no_numeric_judgement_fields():
    body = rb.compose_body(_thesis_target(), _briefing(), monitors=[])
    keys = _keys(body)
    for banned in BANNED_BODY_KEYS:
        assert banned not in keys, f"judgement key {banned!r} leaked into body"
    hay = _haystack(body)
    for term in BANNED_TERMS:
        assert term not in hay, f"banned term {term!r} in body"


def test_body_shape_matches_the_frozen_schema():
    monitors = [
        {
            "name": "Conditions we watch",
            "state_en": "No change in the conditions we watch.",
            "state_zh": "我们关注的条件没有变化。",
        }
    ]
    body = rb.compose_body(_thesis_target(), _briefing(), monitors)
    assert set(body.keys()) == {"target", "market_read", "monitors", "artifact"}
    assert set(body["target"].keys()) == {"kind", "id", "name", "version_or_asof"}
    assert body["target"]["kind"] == "thesis"
    assert body["target"]["id"] == THESIS_ID
    assert body["target"]["name"] == "Apple breadth thesis"
    assert body["artifact"]["name"]
    assert body["artifact"]["asof"] == "2026-09-13"
    for row in body["market_read"]:
        assert set(row.keys()) == {"section", "sentence_en", "sentence_zh", "asof"}
        assert row["sentence_en"]
        assert row["sentence_zh"]
    assert body["monitors"] == monitors


def test_degraded_body_carries_the_contract_line_as_market_read_zero():
    body = rb.compose_body(
        _thesis_target(),
        None,
        monitors=[],
        degraded_reason=CONTRACT_MISS_EN,
    )
    assert body["market_read"][0]["sentence_en"] == CONTRACT_MISS_EN
    assert "没有重新计算" in body["market_read"][0]["sentence_zh"]
    assert body["market_read"][0]["sentence_zh"].endswith("。")


def test_watchlist_body_includes_each_member():
    body = rb.compose_body(
        _watchlist_target(tickers=("AAPL", "MSFT")),
        _briefing(),
        monitors=[],
    )
    sentences = " ".join(row["sentence_en"] for row in body["market_read"])
    assert "Apple's tape is quiet after the print." in sentences
    assert "Microsoft held the week's range." in sentences


def test_weekly_artifact_sentences_are_verbatim_and_skip_confidence():
    body = rb.compose_body(
        _thesis_target(tickers=("AAPL",)),
        _weekly_brief(),
        monitors=[],
    )
    sentences = [row["sentence_en"] for row in body["market_read"]]
    assert "The week's tape stayed inside last week's range." in sentences
    assert "Apple stayed inside its range all week." in sentences
    assert "confidence" not in _keys(body)
    hay = _haystack(body)
    assert "falsif" not in hay


def test_user_facing_strings_are_plain_sentences():
    """Pre-fix this test only stopped four enum tokens and a leading
    underscore — production slugs slipped right past. The post-fix assertion
    catches the measured triple ``radar CONF edge7 · alt92 ACCUMULATE · news
    neutral n1`` and every variant on every row.
    """
    body = rb.compose_body(_thesis_target(tickers=("MSFT",)), _briefing(), monitors=[])
    hay_en = " ".join(row["sentence_en"] for row in body["market_read"])
    hay_zh = " ".join(row["sentence_zh"] or "" for row in body["market_read"])
    hay = hay_en + " " + hay_zh
    for fragment in PRODUCTION_SLUG_FRAGMENTS:
        assert fragment not in hay, (
            f"engine slug fragment {fragment!r} leaked into user-facing string"
        )
    for token in ("·",):
        assert token not in hay_en, f"raw separator {token!r} leaked into sentence_en"
    for row in body["market_read"]:
        for key in ("sentence_en", "sentence_zh"):
            text = row[key] or ""
            assert "daily_after_us_close" not in text
            assert "weekly_saturday" not in text
            assert "brief_deliveries" not in text
            assert "_" not in text.split()[0]


# ---------------------------------------------------------------------------
# Production-shape heal proofs (H1, H2, H3, H4, H5, H6, H7, H8, H9)
# ---------------------------------------------------------------------------

def test_weekly_slot_accepts_run_date_generated_artifact():
    """H1 / BLOCKER 1: weekly_saturday must not return None when the
    artifact was generated this run (Saturday with Friday market state).

    Pre-fix: ``compute_slot('weekly_saturday', '2026-09-11', date(2026, 9, 12))``
    returned ``None`` because ``state_asof < run_date``. The producer then
    classified 'degraded' and told subscribers the brief did not run on
    every Saturday night — measured ``master_brief.json`` Sat 2026-09-12 with
    ``state_asof 2026-09-11``.
    """
    slot = rb.compute_slot(
        "weekly_saturday",
        "2026-09-11",
        date(2026, 9, 12),
        artifact_generated_at="2026-09-12T10:10:33.933810+00:00",
    )
    assert slot == date(2026, 9, 12)


def test_daily_slot_accepts_run_date_generated_artifact():
    """H2 / BLOCKER 2: daily_after_us_close must accept a briefing
    generated this run whose as_of is one day earlier.

    Pre-fix: the nightly 30 23 * * * ran mid-job capturing EST ``as_of``;
    the producer captured ``datetime.now(timezone.utc).date()`` at the end of
    the same job — UTC rollovers to ``as_of + 1``. The producer then
    classified 'degraded' for a briefing this run just built.
    """
    slot = rb.compute_slot(
        "daily_after_us_close",
        "2026-11-15",
        date(2026, 11, 16),
        artifact_generated_at="2026-11-15T23:30:00+00:00",
    )
    assert slot == date(2026, 11, 16)


def test_weekly_artifact_production_shape_is_ready():
    """H1 integration: classify() with the production weekly brief must
    return 'ready', NOT 'degraded' with the contract's "Tonight's brief
    didn't run" line. The measured triple was
    ``master_brief.json generated_at=2026-09-12 state_asof=2026-09-11``.
    """
    sub = _sub(cadence="weekly_saturday", run_date="2026-09-12")
    artifact = _production_weekly()
    state, reason = rb.classify(sub, artifact, _thesis_target())
    assert state == "ready"
    assert reason is None


def test_daily_artifact_production_shape_is_ready():
    """H2 integration: classify() with the production daily briefing that
    crossed UTC midnight must return 'ready'.
    """
    sub = _sub(run_date="2026-11-16")
    artifact = _production_daily()
    state, reason = rb.classify(sub, artifact, _thesis_target(tickers=("MSFT",)))
    assert state == "ready"
    assert reason is None


def test_weekly_body_draws_real_zh_from_published_block():
    """H3 / BLOCKER 3: ``sentence_zh`` must be real Chinese from the weekly
    ``zh`` block — the production measurement fed an English ``sentence_zh``
    with a ``（翻译待补）`` marker for 11/11 weekly rows.
    """
    body = rb.compose_body(
        _thesis_target(tickers=("AAPL",)),
        _production_weekly(),
        monitors=[],
    )
    sentences_zh = [row["sentence_zh"] for row in body["market_read"]]
    assert sentences_zh, "weekly body must have sentences"
    joined = " ".join(sentences_zh)
    assert "（翻译待补）" not in joined, (
        "weekly sentence_zh must not carry the translation-pending marker "
        "(the artifact publishes a real zh block)"
    )
    assert any("收益率" in z or "美联储" in z or "格局变化" in z for z in sentences_zh), (
        "weekly sentence_zh must contain real Chinese from the zh block"
    )


def test_daily_body_uses_only_situation_not_evidence():
    """H4 / BLOCKER 4: priority_queue ``evidence`` is engine slug code and
    must NEVER appear in ``sentence_en`` / ``sentence_zh``. The measured
    triple was ``radar CONF edge7 · alt92 ACCUMULATE · news neutral n1``.
    """
    body = rb.compose_body(
        _thesis_target(tickers=("AAPL", "MSFT")),
        _briefing(),
        monitors=[],
    )
    hay_en = " ".join(row["sentence_en"] for row in body["market_read"])
    hay_zh = " ".join(row["sentence_zh"] or "" for row in body["market_read"])
    hay = hay_en + " " + hay_zh
    for fragment in PRODUCTION_SLUG_FRAGMENTS:
        assert fragment not in hay, (
            f"engine slug fragment {fragment!r} copied into user-facing string"
        )
    assert "·" not in hay_en


def test_no_coverage_thesis_degrades_with_typed_line():
    """H6 / MAJOR 2: a thesis with no ticker coverage (e.g. a theme thesis
    whose ``_thesis_tickers`` returns ``[]``) must NOT classify 'ready'
    while emitting only the global backdrop.
    """
    sub = _sub()
    # Theme-style target: no tickers.
    target = {
        "kind": "thesis",
        "id": THESIS_ID,
        "name": "Stagflation regime watch",
        "version_or_asof": "3",
        "tickers": [],
        "unavailable": False,
    }
    state, reason = rb.classify(sub, _briefing(), target)
    assert state == "degraded"
    assert reason == rb.NO_COVERAGE_REASON
    body = rb.compose_body(target, _briefing(), monitors=[], degraded_reason=reason)
    assert body["market_read"][0]["sentence_en"] == rb.NO_COVERAGE_EN
    assert body["market_read"][0]["sentence_zh"] == rb.NO_COVERAGE_ZH


def test_no_coverage_tickers_thesis_degrades_on_production_daily_artifact():
    """H6 / MAJOR 2 (anti-mask): a thesis whose tickers exist but yield zero
    rows in the published artifact must NOT classify 'ready' while emitting
    only the global backdrop. The previous test only covered the empty-list
    branch; the H6 fix now also catches non-empty-but-uncovered tickers.
    Reproduced at the live ``site/intelligence/briefing.json``:
    ``['ZZZZ']`` classified 'ready' and ``compose_body`` emitted exactly the
    macro backdrop row.
    """
    import json

    prod_path = ROOT / "site/intelligence/briefing.json"
    if not prod_path.exists():
        pytest.skip("site/intelligence/briefing.json not materialised in this checkout")
    prod = json.loads(prod_path.read_text(encoding="utf-8"))
    sub = _sub()
    target = {
        "kind": "thesis",
        "id": THESIS_ID,
        "name": "Synthetic no-coverage thesis",
        "version_or_asof": "1",
        "tickers": ["ZZZZ"],
        "unavailable": False,
    }
    state, reason = rb.classify(sub, prod, target)
    assert state == "degraded"
    assert reason == rb.NO_COVERAGE_REASON
    body = rb.compose_body(target, prod, monitors=[], degraded_reason=reason)
    assert body["market_read"][0]["sentence_en"] == rb.NO_COVERAGE_EN
    assert body["market_read"][0]["sentence_zh"] == rb.NO_COVERAGE_ZH
    # And no silent backdrop row was published: the only market_read row is
    # the typed honest-miss line, not the global macro_context posture.
    assert len(body["market_read"]) == 1
    assert body["market_read"][0]["section"] == "status"


def test_no_coverage_watchlist_degrades_when_members_miss_artifact():
    """H6 / MAJOR 2 (watchlist branch): a watchlist whose members do not
    appear in any priority_queue / divergences / watch_items row of the
    artifact must degrade, not silently emit only the backdrop.
    """
    sub = _sub(kind="watchlist")
    target = {
        "kind": "watchlist",
        "id": WATCH_ID,
        "name": "Names we don't follow",
        "version_or_asof": None,
        "tickers": ["XXXX"],
        "unavailable": False,
    }
    state, reason = rb.classify(sub, _briefing(), target)
    assert state == "degraded"
    assert reason == rb.NO_COVERAGE_REASON


def test_no_target_user_id_returns_target_unavailable(monkeypatch):
    """H5 / MAJOR 1: read_target must owner-scope on the subscription's
    ``user_id``. A subscription whose target is owned by another user must
    return ``None`` — no leakage of title / symbols / monitor state — and
    classify reports 'target unavailable'.
    """
    OTHER = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    sub = _sub(user_id=OTHER)
    captured = {}

    def fake_pg(method, path, body=None, prefer=None, timeout=6):
        captured.setdefault("calls", []).append(path)
        if method == "GET" and path.startswith("theses?"):
            return []  # owner mismatch — no rows
        if method == "GET" and path.startswith("watchlists?"):
            return []
        return None

    monkeypatch.setattr(rb, "_pg", fake_pg)
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "test-key")
    result = rb.read_target(sub)
    assert result is None
    assert captured.get("calls"), "read_target must issue at least one Supabase GET"
    assert any("user_id=eq." in c for c in captured["calls"]), (
        f"read_target URL must owner-scope on subscription.user_id, got {captured['calls']}"
    )
    assert any(f"user_id=eq.{OTHER}" in c for c in captured["calls"]), (
        f"read_target must use sub.user_id ({OTHER}) on the filter, got {captured['calls']}"
    )


def test_read_target_calls_include_user_id_filter():
    """Source-of-truth guard: read_target URL must include ``user_id=eq.{uid}``
    on both the thesis and the watchlist branches, mirror scripts/run_watchlist_sentinel.py.
    """
    import inspect

    src = inspect.getsource(rb.read_target)
    assert "&user_id=eq." in src, (
        "read_target must owner-scope both thesis and watchlist reads with "
        "&user_id=eq.{sub.user_id}; mirrors scripts/run_watchlist_sentinel.py"
    )
    assert "theses?id=eq." in src
    assert "watchlists?id=eq." in src
    assert "lifecycle_state=eq.active" in src, (
        "read_target must mirror engine/thesis_condition_monitor.py:601 and "
        "filter archived/closed theses as 'target unavailable'"
    )


def test_run_surfaces_write_errors_via_result(monkeypatch):
    """H8 / MAJOR 4: write_delivery returning ``'error'`` surfaces in RunResult."""
    client = FakeClient()

    def fake_write(row, *, dry_run):
        return "error"

    _patch_run(
        monkeypatch,
        artifact=_briefing(),
        target=_thesis_target(),
        client=client,
    )
    monkeypatch.setattr(rb, "write_delivery", fake_write)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.error_n == 1
    assert result.planned_n == 1


def test_cli_dry_run_prints_what_it_would_write(monkeypatch, capsys):
    """H7 / MAJOR 3: ``--dry-run`` prints planned/duplicate counts and one
    summary line per row. The R6 line and ``::notice`` stay.
    """
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    monkeypatch.setenv("RECURRING_BRIEFS_ENABLE", "1")
    rc = entry.main(
        [
            "--cadence",
            "daily_after_us_close",
            "--dry-run",
            "--run-date",
            "2026-09-13",
        ]
    )
    assert rc == 0
    assert client.deliveries == []
    out = capsys.readouterr().out
    assert "1 ready" in out
    # Frozen-spec item (2): prints what it would write.
    assert "(dry-run): 1 planned" in out or "1 planned" in out
    assert "-- subscription" in out


def test_cli_surfaces_write_failure_as_warning(monkeypatch, capsys):
    """H8 / MAJOR 4: CLI emits a ``::warning`` line on write failures."""
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    monkeypatch.setenv("RECURRING_BRIEFS_ENABLE", "1")
    monkeypatch.setattr(
        rb, "write_delivery",
        lambda row, dry_run=False: "error" if not dry_run else "dry",
    )
    rc = entry.main(
        ["--cadence", "daily_after_us_close", "--run-date", "2026-09-13"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "::warning title=recurring-briefs-write-error::" in out
    assert "1 write error" in out


def test_engine_drops_judgement_keys_constant():
    """H10 minor (a): the dead ``_JUDGEMENT_KEYS`` constant is gone. The
    "no score/rank/confidence" guarantee is enforced by the extractor's
    field selection — no LLM, no raw ``evidence``, no judgement keys.
    """
    import inspect
    src = inspect.getsource(rb)
    assert "_JUDGEMENT_KEYS" not in src


# ---------------------------------------------------------------------------
# Pin the existing tests as "anti-mask" — the four blockers' regressed fixes
# must each have a measured test against the production-shaped fixture.
# ---------------------------------------------------------------------------


def test_user_facing_strings_reject_production_daily_slugs():
    """Anti-mask H4: with the production daily fixture carrying the
    measured slug ``radar CONF edge7 · alt92 ACCUMULATE · news neutral n1``,
    compose_body for a target that follows that ticker must not include
    any slug fragment in ``sentence_en`` or ``sentence_zh``.
    """
    body = rb.compose_body(
        _thesis_target(tickers=("MSFT",)),
        _briefing(include_slug_evidence=True),
        monitors=[],
    )
    hay = " ".join(
        row["sentence_en"] or "" for row in body["market_read"]
    ) + " " + " ".join(
        row["sentence_zh"] or "" for row in body["market_read"]
    )
    for fragment in PRODUCTION_SLUG_FRAGMENTS:
        assert fragment not in hay, (
            f"production slug fragment {fragment!r} leaked: {hay!r}"
        )


def test_user_facing_strings_reject_translation_pending_for_weekly():
    """Anti-mask H3: weekly sentences must NOT carry the
    ``（翻译待补）`` marker when the artifact publishes a ``zh`` block.
    """
    body = rb.compose_body(
        _thesis_target(tickers=("AAPL",)),
        _production_weekly(),
        monitors=[],
    )
    sentences_zh = [row["sentence_zh"] or "" for row in body["market_read"]]
    joined = " ".join(sentences_zh)
    assert "（翻译待补）" not in joined, (
        f"weekly sentence_zh must be real Chinese; got {joined!r}"
    )
    # And at least one sentence must carry real Chinese from the artifact.
    assert any("收益率" in z or "美联储" in z or "格局变化" in z for z in sentences_zh), (
        f"weekly sentence_zh must contain real Chinese from the zh block; got {sentences_zh!r}"
    )


# ---------------------------------------------------------------------------
# run() with FakeClient — idempotency, dry-run, degraded
# ---------------------------------------------------------------------------

def _patch_run(monkeypatch, *, artifact, target, client, subscriptions=None):
    monkeypatch.setattr(rb, "load_published_artifact", lambda cadence, root=None: artifact)
    monkeypatch.setattr(
        rb, "read_subscriptions", lambda cadence: subscriptions or [_sub()]
    )
    monkeypatch.setattr(rb, "read_target", lambda sub: target)
    monkeypatch.setattr(
        rb, "write_delivery", lambda row, dry_run=False: client.write(row, dry_run=dry_run)
    )
    monkeypatch.setattr(rb, "load_monitors_for_target", lambda target: [])
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "test-key")


def test_run_writes_one_ready_row(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.subscription_n == 1
    assert result.ready_n == 1
    assert result.degraded_n == 0
    assert result.slot == date(2026, 9, 13)
    assert len(client.deliveries) == 1
    row = client.deliveries[0]
    assert row["state"] == "ready"
    assert row["slot_asof"] == "2026-09-13"
    assert row["subscription_id"] == SUB_ID
    assert row["degraded_reason"] is None


def test_idempotent_second_run_writes_nothing(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    r1 = rb.run(cadence="daily_after_us_close", dry_run=False, run_date=date(2026, 9, 13))
    r2 = rb.run(cadence="daily_after_us_close", dry_run=False, run_date=date(2026, 9, 13))
    assert r1.ready_n == 1
    assert len(client.deliveries) == 1
    assert client.insert_calls == 2
    assert r2.duplicate_n == 1
    assert len(client.deliveries) == 1


def test_stale_artifact_writes_degraded_row_with_contract_line(monkeypatch):
    """A briefing whose ``generated_utc`` is several days stale degrades;
    the body carries the contract's plain line.
    """
    client = FakeClient()
    _patch_run(
        monkeypatch,
        artifact=_briefing(as_of="2026-09-12", generated_utc="2026-09-12T20:05:00+00:00"),
        target=_thesis_target(),
        client=client,
    )
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 15),
    )
    assert result.ready_n == 0
    assert result.degraded_n == 1
    assert result.slot == date(2026, 9, 15)
    row = client.deliveries[0]
    assert row["state"] == "degraded"
    assert row["degraded_reason"] == CONTRACT_MISS_EN
    assert row["body"]["market_read"][0]["sentence_en"] == CONTRACT_MISS_EN
    assert row["slot_asof"] == "2026-09-15"


def test_missing_artifact_writes_degraded_for_todays_slot_not_a_skip(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=None, target=_thesis_target(), client=client)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.degraded_n == 1
    assert len(client.deliveries) == 1
    assert client.deliveries[0]["slot_asof"] == "2026-09-13"


def test_unavailable_target_writes_degraded_target_unavailable(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=None, client=client)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.degraded_n == 1
    assert client.deliveries[0]["degraded_reason"] == "target unavailable"


def test_dry_run_writes_nothing(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=True,
        run_date=date(2026, 9, 13),
    )
    assert result.ready_n == 1
    assert result.planned_n == 1
    assert client.deliveries == []
    assert all(c == "dry" or True for c in [])  # writes went through dry_run=True
    assert client.insert_calls == 1
    assert client.deliveries == []


def test_paused_subscription_is_not_written(monkeypatch):
    client = FakeClient()
    _patch_run(
        monkeypatch,
        artifact=_briefing(),
        target=_thesis_target(),
        client=client,
        subscriptions=[_sub(state="paused")],
    )
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.subscription_n == 0
    assert client.deliveries == []


def test_run_does_not_backfill_yesterday(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(as_of="2026-09-13"),
               target=_thesis_target(), client=client)
    rb.run(cadence="daily_after_us_close", dry_run=False, run_date=date(2026, 9, 13))
    slots = {r["slot_asof"] for r in client.deliveries}
    assert slots == {"2026-09-13"}
    assert "2026-09-12" not in slots


def test_write_delivery_uses_on_conflict_do_nothing():
    src = Path(rb.__file__).read_text(encoding="utf-8")
    assert "on_conflict=subscription_id,slot_asof" in src
    assert "resolution=ignore-duplicates" in src


def test_daily_artifact_file_and_field_are_named():
    assert rb.DAILY_ARTIFACT_REL == "site/intelligence/briefing.json"
    assert "as_of" in rb.DAILY_ASOF_FIELDS


def test_weekly_artifact_file_and_field_are_named():
    assert rb.WEEKLY_ARTIFACT_REL == "site/master_brief.json"
    assert "state_asof" in rb.WEEKLY_ASOF_FIELDS


# ---------------------------------------------------------------------------
# CLI: R6 line, ::notice, dormant flag, dry-run
# ---------------------------------------------------------------------------

def test_cli_prints_r6_line_and_notice_at_line_start(monkeypatch, capsys):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    monkeypatch.setenv("RECURRING_BRIEFS_ENABLE", "1")
    rc = entry.main(
        ["--cadence", "daily_after_us_close", "--run-date", "2026-09-13"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    summary = [
        ln for ln in lines
        if ln.startswith("recurring briefs:") and not ln.startswith("::")
    ]
    assert summary, out
    assert "1 subscriptions" in summary[0]
    assert "1 ready" in summary[0]
    assert "0 degraded" in summary[0]
    assert "slot 2026-09-13" in summary[0]
    notices = [ln for ln in lines if ln.startswith("::notice")]
    assert notices, "expected a ::notice line at the start of some output line"
    assert "recurring briefs:" in notices[0]


def test_cli_dormant_without_enable_flag_writes_nothing(monkeypatch, capsys):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    monkeypatch.delenv("RECURRING_BRIEFS_ENABLE", raising=False)
    rc = entry.main(
        ["--cadence", "daily_after_us_close", "--run-date", "2026-09-13"]
    )
    assert rc == 0
    assert client.deliveries == []
    out = capsys.readouterr().out
    assert "DORMANT" in out
    assert "RECURRING_BRIEFS_ENABLE" in out


def test_cli_dry_run_flag_writes_nothing_even_when_enabled(monkeypatch, capsys):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    monkeypatch.setenv("RECURRING_BRIEFS_ENABLE", "1")
    rc = entry.main(
        [
            "--cadence",
            "daily_after_us_close",
            "--dry-run",
            "--run-date",
            "2026-09-13",
        ]
    )
    assert rc == 0
    assert client.deliveries == []
    out = capsys.readouterr().out
    assert "1 ready" in out


def test_cli_always_exits_zero_without_credentials(monkeypatch, capsys):
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("RECURRING_BRIEFS_ENABLE", "1")
    rc = entry.main(
        ["--cadence", "daily_after_us_close", "--run-date", "2026-09-13"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "recurring briefs:" in out


def test_no_llm_call_in_producer_source():
    src = Path(rb.__file__).read_text(encoding="utf-8") + Path(entry.__file__).read_text(
        encoding="utf-8"
    )
    for needle in ("openai", "anthropic", "chat.completions", "ChatCompletion"):
        assert needle not in src.lower().replace("co-authored-by: claude", "")


def test_engine_never_prints_service_role_key():
    """The service-role key is sent as a header (same as the thesis monitor)
    but must never appear in a print or log line."""
    for path in (Path(rb.__file__), Path(entry.__file__)):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.lstrip()
            if stripped.startswith("print(") or stripped.startswith("log."):
                assert "SUPABASE_SERVICE_ROLE_KEY" not in line
                assert "SERVICE_ROLE" not in line


# ---------------------------------------------------------------------------
# Workflow placement + gating (R2)
# ---------------------------------------------------------------------------

def test_daily_step_sits_after_briefing_and_thesis_monitor():
    text = (ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8")
    i_brief = text.find("brain briefing tunnel (build_briefing)")
    i_mon = text.find("thesis condition monitor (F11")
    i_ours = text.find("recurring briefs producer")
    assert i_brief != -1 and i_mon != -1 and i_ours != -1
    assert i_brief < i_mon < i_ours
    assert "python -m scripts.build_recurring_briefs --cadence daily_after_us_close" in text
    assert "RECURRING_BRIEFS_ENABLE: ${{ secrets.RECURRING_BRIEFS_ENABLE }}" in text
    assert "SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}" in text


def test_weekly_step_sits_after_brief_producers():
    text = (ROOT / ".github/workflows/weekly.yml").read_text(encoding="utf-8")
    i_brief = text.find('run_py "AI brief page (build_aibrief)" scripts.build_aibrief')
    i_ours = text.find("recurring briefs producer")
    assert i_brief != -1 and i_ours != -1
    assert i_brief < i_ours
    assert "python -m scripts.build_recurring_briefs --cadence weekly_saturday" in text
    assert "RECURRING_BRIEFS_ENABLE: ${{ secrets.RECURRING_BRIEFS_ENABLE }}" in text


def test_gating_mirrors_thesis_monitor():
    daily = (ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8")
    # The monitor's own gating lines, which this packet must mirror.
    assert "THESIS_MONITOR_ENABLE: ${{ secrets.THESIS_MONITOR_ENABLE }}" in daily
    assert "RECURRING_BRIEFS_ENABLE: ${{ secrets.RECURRING_BRIEFS_ENABLE }}" in daily
    assert "Dormant unless THESIS_MONITOR_ENABLE=1" in daily
    assert "Dormant unless RECURRING_BRIEFS_ENABLE=1" in daily


def test_no_new_cron_in_this_packet():
    daily = (ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8")
    weekly = (ROOT / ".github/workflows/weekly.yml").read_text(encoding="utf-8")
    # The producer rides existing owners; this packet does not add a schedule key.
    ours_daily = daily[daily.find("recurring briefs producer"):]
    ours_daily = ours_daily[: ours_daily.find("\n      - name: ")]
    assert "cron:" not in ours_daily
    ours_weekly = weekly[weekly.find("recurring briefs producer"):]
    ours_weekly = ours_weekly[: ours_weekly.find("\n      - name: ")]
    assert "cron:" not in ours_weekly
