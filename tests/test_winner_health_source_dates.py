"""D03 T43/W07: source failures publish a truthful, typed unavailable state.

The design-fixture path intentionally bypasses freshness. These regressions use
the normal data/top_maturation/latest.json path, including build() and main(),
so a date-parser exception cannot leave the previously published board in place.
"""
from __future__ import annotations

import datetime
import json
from html import unescape
from pathlib import Path

import pytest

from scripts import build_winner_health_page as bwh


REPO = Path(__file__).resolve().parent.parent
_REAL_DATE = datetime.date
_TODAY = _REAL_DATE(2026, 11, 4)
INVALID_DATES = (
    "2026-99-01",
    "2026-00-10",
    "2026-02-30",
    "2025-02-29",
    "2100-02-29",
    "2026-01-00",
    "0000-01-01",
)


@pytest.fixture(autouse=True)
def fixed_calendar_day(monkeypatch):
    """Keep calendar-boundary cases deterministic across midnight and hosts."""
    class FixedDate(_REAL_DATE):
        @classmethod
        def today(cls):
            return cls(_TODAY.year, _TODAY.month, _TODAY.day)

    monkeypatch.setattr(datetime, "date", FixedDate)


def _live_artifact(data_dir: Path, payload: object) -> Path:
    path = data_dir / "top_maturation" / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _isolated_root(tmp_path: Path, monkeypatch, asof: str) -> Path:
    from lib import config, pages

    root = tmp_path / "repo"
    root.mkdir()
    (root / "templates").symlink_to(REPO / "templates", target_is_directory=True)
    # write_page also copies shared assets via config.ROOT, not only its output
    # argument. Keep those writes in the same disposable publication root.
    monkeypatch.setattr(config, "ROOT", root)
    monkeypatch.setattr(pages, "_shim_checked", False)
    assert pages._site_root() == root / "site"
    monkeypatch.setattr(bwh, "_data_dir", lambda r: r / "data")
    _live_artifact(root / "data", {"asof": asof})
    # A failed build used to leave this previous board unmodified.
    previous = root / "site" / "winner_health.html"
    previous.parent.mkdir()
    previous.write_text("PREVIOUS_BOARD_MUST_NOT_SURVIVE", encoding="utf-8")
    return root


@pytest.mark.parametrize("asof", INVALID_DATES)
def test_impossible_calendar_dates_are_unusable(asof):
    assert bwh._is_stale({"asof": asof}) is True


@pytest.mark.parametrize("asof", [None, "", "not-a-date", 20261104, [], {}])
def test_malformed_date_shapes_remain_unusable(asof):
    assert bwh._is_stale({"asof": asof}) is True


def test_missing_date_remains_unusable():
    assert bwh._is_stale({}) is True


@pytest.mark.parametrize("age, stale", [(0, False), (1, False), (5, False),
                                        (6, False), (7, True), (30, True)])
def test_existing_six_calendar_day_cutoff_is_unchanged(age, stale):
    asof = (_TODAY - datetime.timedelta(days=age)).isoformat()
    assert bwh._is_stale({"asof": asof}) is stale


def test_timestamp_prefix_keeps_existing_date_semantics():
    assert bwh._is_stale({"asof": "2026-10-29T23:59:59Z"}) is False
    assert bwh._is_stale({"asof": "2026-10-28T23:59:59Z"}) is True


def test_valid_leap_day_is_parsed_then_judged_by_age():
    assert bwh._is_stale({"asof": "2024-02-29"}) is True


@pytest.mark.parametrize("asof", ["2026-99-01", "2026-02-30", "2025-02-29"])
def test_live_loader_returns_warm_context_for_impossible_dates(tmp_path, asof):
    _live_artifact(tmp_path, {"asof": asof})
    assert bwh._load_context(tmp_path) is None


@pytest.mark.parametrize("age, accepted", [(6, True), (7, False)])
def test_live_loader_preserves_freshness_boundary(tmp_path, age, accepted):
    payload = {"asof": (_TODAY - datetime.timedelta(days=age)).isoformat(),
               "source_marker": "unchanged"}
    _live_artifact(tmp_path, payload)
    assert bwh._load_context(tmp_path) == (payload if accepted else None)


@pytest.mark.parametrize("asof", ["2026-99-01", "2026-02-30", "2025-02-29"])
def test_live_build_publishes_warm_page_instead_of_leaving_old_board(
    tmp_path, monkeypatch, asof
):
    root = _isolated_root(tmp_path, monkeypatch, asof)
    out = bwh.build(root)
    assert out == root / "site" / "winner_health.html"
    html = out.read_text(encoding="utf-8")
    assert "Read date is unavailable" in unescape(html)
    assert "判读日期不可用" in html
    assert "PREVIOUS_BOARD_MUST_NOT_SURVIVE" not in html
    assert asof not in html


@pytest.mark.parametrize("asof", ["2026-99-01", "2026-02-30", "2025-02-29"])
def test_live_cli_succeeds_when_warm_page_was_written(
    tmp_path, monkeypatch, capsys, asof
):
    root = _isolated_root(tmp_path, monkeypatch, asof)
    assert bwh.main(["--root", str(root)]) == 0
    html = (root / "site" / "winner_health.html").read_text(encoding="utf-8")
    assert "Read date is unavailable" in unescape(html)
    assert "PREVIOUS_BOARD_MUST_NOT_SURVIVE" not in html
    assert "render failed" not in capsys.readouterr().out


def test_explicit_fixture_still_bypasses_live_freshness_policy(tmp_path):
    payload = {"asof": "2000-01-01", "source_marker": "historical design fixture"}
    path = _live_artifact(tmp_path, payload)
    assert bwh._load_context(tmp_path, fixture=path) == payload


# W07 extends the same source boundary. No producer or cohort policy changes.
COPY = {
    "missing": ("No read is available", "暂无可用判读"),
    "unreadable": ("Latest read could not be loaded", "无法载入最新判读"),
    "invalid_artifact": ("Latest read is not usable", "最新判读无法使用"),
    "invalid_date": ("Read date is unavailable", "判读日期不可用"),
    "stale": ("Latest read is out of date", "最新判读已过期"),
    "producer_unavailable": ("Latest read did not complete", "最新判读未完成"),
}


def _available_context(**changes):
    result = {"asof": _TODAY.isoformat(), "null_state": False,
              "schema": "winner_health.v2", "universe_n": 1,
              "states": {"extended_healthy": [], "extended_watch": [],
                         "thinning": [], "breaking": [], "no_read": []}}
    result.update(changes)
    return result


def _failure_source(root, code):
    path = root / "data" / "top_maturation" / "latest.json"
    if code == "missing":
        path.unlink()
    elif code == "unreadable":
        path.write_bytes(b"\xff\xfe")
    elif code == "invalid_artifact":
        path.write_text('{"unclosed":', encoding="utf-8")
    else:
        _live_artifact(root / "data", _available_context(
            asof="2026-02-30" if code == "invalid_date" else
                 "2026-10-28" if code == "stale" else _TODAY.isoformat(),
            null_state=code == "producer_unavailable",
            null_reason="SECRET_DIAGNOSTIC /private/store <script>bad()</script>",
            data_last_day="SHOULD_NOT_LOOK_PRICED", tape_lag_sessions=99,
            macro_backdrop={"stage3_count": 98765}))


@pytest.mark.parametrize("code", COPY)
def test_live_failure_publishes_distinct_copy_without_recovery_promise(
    tmp_path, monkeypatch, code
):
    root = _isolated_root(tmp_path, monkeypatch, _TODAY.isoformat())
    _failure_source(root, code)
    assert bwh.main(["--root", str(root)]) == 0
    html = (root / "site" / "winner_health.html").read_text(encoding="utf-8")
    assert f'data-wh-availability="{code}"' in html
    assert all(text in unescape(html) for text in COPY[code])
    assert 'aria-labelledby="wh-source-title"' in html
    assert 'id="wh-source-title"' in html
    for forbidden in ("PREVIOUS_BOARD_MUST_NOT_SURVIVE", "has not landed yet",
                      "as soon as the nightly read finishes", "SECRET_DIAGNOSTIC",
                      "SHOULD_NOT_LOOK_PRICED", "98765", "Re-read every night",
                      "a name you cannot find anywhere on this page did not clear"):
        assert forbidden not in html
    assert ('class="source-asof"' in html) is (code == "stale")
    if code == "stale":
        assert "2026-10-28" in html
    else:
        assert "2026-02-30" not in html


@pytest.mark.parametrize("payload", [None, [], 42, "SECRET_SHAPE"])
def test_non_object_sources_are_invalid_not_empty(tmp_path, payload):
    _live_artifact(tmp_path, payload)
    ctx, receipt = bwh._load_context_result(tmp_path)
    assert ctx is None
    assert receipt == {"code": "invalid_artifact", "source_asof": None}


@pytest.mark.parametrize("raw, code", [(b"{", "invalid_artifact"),
                                       (b"\xff\xfe", "unreadable")])
def test_invalid_bytes_have_loader_owned_causes(tmp_path, raw, code):
    path = _live_artifact(tmp_path, {})
    path.write_bytes(raw)
    ctx, receipt = bwh._load_context_result(tmp_path)
    assert ctx is None
    assert receipt == {"code": code, "source_asof": None}


@pytest.mark.parametrize("error, code", [(FileNotFoundError, "missing"),
                                         (PermissionError, "unreadable"),
                                         (OSError, "unreadable")])
def test_disappearance_and_read_failures_never_escape_as_market_copy(
    tmp_path, monkeypatch, error, code
):
    path = _live_artifact(tmp_path, _available_context())
    original = Path.read_text

    def failing_read(self, *args, **kwargs):
        if self == path:
            raise error("SECRET_PATH /private/producer")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read)
    ctx, receipt = bwh._load_context_result(tmp_path)
    assert ctx is None
    assert receipt == {"code": code, "source_asof": None}
    assert "SECRET_PATH" not in json.dumps(receipt)


@pytest.mark.parametrize("asof", [None, "", [], {}, "2026-02-30", "0000-01-01"])
def test_invalid_source_day_has_no_display_date(tmp_path, asof):
    _live_artifact(tmp_path, _available_context(asof=asof))
    ctx, receipt = bwh._load_context_result(tmp_path)
    assert ctx is None
    assert receipt == {"code": "invalid_date", "source_asof": None}


@pytest.mark.parametrize("age, code", [(6, "available"), (7, "stale"),
                                      (-1, "available")])
def test_typed_result_preserves_existing_date_policy_including_future(
    tmp_path, age, code
):
    # Future-date acceptance is pre-existing behavior, not a new admission rule.
    day = (_TODAY - datetime.timedelta(days=age)).isoformat()
    payload = _available_context(asof=day + "T23:59:59Z")
    _live_artifact(tmp_path, payload)
    ctx, receipt = bwh._load_context_result(tmp_path)
    assert receipt == {"code": code, "source_asof": day}
    assert ctx == (payload if code == "available" else None)


@pytest.mark.parametrize("reason", [None, "", "store unreadable", 7, [], {},
                                    "SECRET_REASON /private/store",
                                    '<script>SECRET_REASON()</script>'])
def test_producer_null_uses_flag_not_untyped_exception_reason(
    tmp_path, monkeypatch, reason
):
    root = _isolated_root(tmp_path, monkeypatch, _TODAY.isoformat())
    payload = _available_context(null_state=True, null_reason=reason)
    _live_artifact(root / "data", payload)
    ctx, receipt = bwh._load_context_result(root / "data")
    assert ctx == payload  # compatibility wrapper still returns admitted payload
    assert bwh._load_context(root / "data") == payload
    assert receipt == {"code": "producer_unavailable", "source_asof": "2026-11-04"}
    html = bwh.render(root)
    assert COPY["producer_unavailable"][0] in html
    assert "SECRET_REASON" not in html and "store unreadable" not in html


def test_stale_reason_precedes_producer_null(tmp_path):
    _live_artifact(tmp_path, _available_context(asof="2026-10-28", null_state=True))
    ctx, receipt = bwh._load_context_result(tmp_path)
    assert ctx is None
    assert receipt == {"code": "stale", "source_asof": "2026-10-28"}


@pytest.mark.parametrize("flag", ["false", "true", 1, [1], {"reason": "unknown"}])
def test_truthy_malformed_null_flag_never_becomes_available(tmp_path, flag):
    _live_artifact(tmp_path, _available_context(null_state=flag))
    _, receipt = bwh._load_context_result(tmp_path)
    assert receipt["code"] == "invalid_artifact"


@pytest.mark.parametrize("flag", [False, None, 0, "", []])
def test_existing_falsey_null_flag_compatibility_is_retained(tmp_path, flag):
    payload = _available_context(null_state=flag)
    _live_artifact(tmp_path, payload)
    ctx, receipt = bwh._load_context_result(tmp_path)
    assert ctx == payload and receipt["code"] == "available"


@pytest.mark.parametrize("age, lag, board, warning", [(6, 6, True, True),
                                                      (6, 5, True, False),
                                                      (6, None, True, False),
                                                      (7, 6, False, False)])
def test_empty_board_and_tape_clock_remain_independent(
    tmp_path, monkeypatch, age, lag, board, warning
):
    root = _isolated_root(tmp_path, monkeypatch, _TODAY.isoformat())
    day = (_TODAY - datetime.timedelta(days=age)).isoformat()
    _live_artifact(root / "data", _available_context(asof=day, tape_lag_sessions=lag))
    html = bwh.render(root)
    assert ('data-wh-availability="stale"' not in html) is board
    assert ("No name is in this group tonight" in html) is board
    assert ('<span class="lag"' in html) is warning


@pytest.mark.parametrize("asof", ["2000-01-01", "2026-02-30"])
def test_explicit_fixtures_still_bypass_date_admission(tmp_path, asof):
    payload = _available_context(asof=asof)
    path = _live_artifact(tmp_path, payload)
    ctx, receipt = bwh._load_context_result(tmp_path, fixture=path)
    assert ctx == payload and receipt["code"] == "available"


def test_renderer_reads_source_once_for_context_and_availability(tmp_path, monkeypatch):
    root = _isolated_root(tmp_path, monkeypatch, _TODAY.isoformat())
    path = _live_artifact(root / "data", _available_context())
    original = Path.read_text
    reads = []

    def recording_read(self, *args, **kwargs):
        if self == path:
            reads.append(self)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", recording_read)
    html = bwh.render(root)
    assert 'data-wh-availability=' not in html
    assert reads == [path]


def test_direct_template_without_typed_result_has_safe_fallback():
    env = bwh.Environment(loader=bwh.FileSystemLoader(str(REPO / "templates")),
                          autoescape=True)
    env.globals.update(td=lambda text: text, tr=lambda text: text)
    html = env.get_template("winner_health.html.j2").render(wh=None)
    assert 'data-wh-availability="unavailable"' in html
    assert "Read unavailable" in html and "判读不可用" in html
    assert "as soon as the nightly read finishes" not in html
