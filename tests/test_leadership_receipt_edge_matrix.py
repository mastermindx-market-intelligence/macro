"""Leadership receipt (mi.leadership_receipt.v1) — edge-behavior matrix.

Characterization pins for engine/leadership_receipt.py, carried forward by
the B4-macro lane: the two defects the base matrix pinned as strict xfails
(a datetime OBJECT as_of silently losing its date; a future-dated
theme_state reading fresh) are FIXED in the engine, the stale prose now
derives from _THEME_STATE_MAX_AGE_DAYS, and breadth carries a label_zh
sibling. Every test here pins behavior the module exhibits today.

Facts pinned by this matrix:

* _state_from_rel: the ±0.01 dead-band edges are INCLUSIVE toward the
  directional state (rel == +0.01 -> "leading", rel == -0.01 -> "lagging").
* Theme-state freshness, checked in order: either date unparsable ->
  "missing"; a theme_state as_of at least one calendar day AFTER the
  theme_intel as_of -> "invalid" (there is no "future" status); age in
  days strictly greater than _THEME_STATE_MAX_AGE_DAYS -> "stale" (exactly
  5 days old is fresh, 6 is stale); else "fresh". The stale prose names
  the constant's value, so copy and gate cannot drift apart.
* _parse_date: None -> None; a datetime OBJECT -> its LOCAL date (equal to
  parsing dt.isoformat(), whose first 10 chars carry the local date — no
  UTC normalization); a date that is not a datetime -> itself; a str ->
  date.fromisoformat(value[:10]) or None on ValueError; anything else —
  int, float — -> None.
* _roster_changed: True only when a member's curated_added (else added)
  date is STRICTLY after the basket created date; equal does not count.
* build_receipt is fail-soft: malformed inputs never raise; clearly
  malformed ones return the unavailable receipt (reason "receipt_error"
  or an observation reason).
* breadth: label / label_zh pair — every producer value (broad, narrow;
  engine/group_flow.py _leadership emits nothing else) maps to plain-word
  ZH, None and unknown labels give label_zh None (no English slug is
  echoed into the ZH field), and available and unavailable receipts share
  the same breadth key set.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import engine.leadership_receipt as lr_mod
from engine.leadership_receipt import (
    _DEAD_BAND,
    _THEME_STATE_MAX_AGE_DAYS,
    _WINDOW_SESSIONS,
    _parse_date,
    _roster_changed,
    _state_from_rel,
    build_receipt,
)

SCHEMA_KEYS = {
    "schema",
    "state",
    "stance_en",
    "stance_zh",
    "reason_en",
    "reason_zh",
    "window_sessions",
    "rel_5d",
    "rel_20d",
    "rel_60d",
    "benchmark",
    "as_of",
    "sample",
    "roster_changed",
    "breadth",
    "leaders",
    "split",
    "theme_state",
    "authority",
    "rows",
}

ROW_KEYS = ["interval", "benchmark", "measure", "sample", "freshness", "authority"]

# Banned vocabulary for any string the receipt returns (lane constraint 3).
_BANNED_EN = re.compile(r"\b(score|confidence|validated|buy|sell)\b", re.I)
_BANNED_ZH = ("评分", "置信", "买入", "卖出")

# One CJK ideograph is enough to call a string Chinese.
_CJK = re.compile(r"[一-鿿]")


# ---------------------------------------------------------------------------
# Fixture builders — copied from tests/test_leadership_receipt.py.
# ---------------------------------------------------------------------------


def _base_basket(**perf20) -> dict:
    rel20 = perf20.get("rel_20d", 0.02)
    return {
        "id": "test_basket",
        "created": "2020-01-01",
        "perf": {
            "5d": {"rel": 0.01},
            "20d": {"rel": rel20},
            "60d": {"rel": 0.03},
        },
        "observation": {
            "effective_as_of": "2026-10-02",
            "configured_n": 10,
            "observed_n": 10,
            "coverage": 1.0,
            "status": "complete",
            "basis": "exact_close_at_effective_as_of",
            "aggregate_eligible": True,
            "min_members": 3,
            "min_coverage": 0.6,
        },
        "members": [],
    }


def _theme_intel(as_of: str = "2026-10-02") -> dict:
    return {
        "as_of": as_of,
        "bench_label": "S&P 500",
        "bench_label_zh": "标普500",
    }


def _theme() -> dict:
    return {
        "breadth": {"pct50": 0.5, "pct200": 0.4, "n": 10},
        "leadership": {
            "breadth": "broad",
            "top": [{"ticker": "AAA", "ret_20d": 0.1}],
        },
        "leadership_split": False,
    }


def _theme_state_file(
    site: Path,
    *,
    as_of: str = "2026-10-02",
    basket_id: str = "test_basket",
    stale_legs: list | None = None,
) -> None:
    payload = {
        "schema": "neuralweb.theme_state.v1",
        "as_of": as_of,
        "stale_legs": stale_legs or [],
        "themes": [
            {
                "theme_id": "t1",
                "basket_ids": [basket_id],
                "subsector_rotation": {"rollup_quadrant": "leading"},
            }
        ],
    }
    dest = site / "neuralwebdata" / "theme_state.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload), encoding="utf-8")


def _b_rel(rel) -> dict:
    b = _base_basket()
    b["perf"]["20d"] = {"rel": rel}
    return b


def _receipt_by_kind(kind: str, tmp_path: Path) -> dict:
    """One receipt per interesting shape, for walk-the-dict tests."""
    site = tmp_path / "site"
    if kind == "leading":
        return build_receipt(_base_basket(rel_20d=0.012), _theme(), _theme_intel(), "us", site)
    if kind == "lagging":
        return build_receipt(_base_basket(rel_20d=-0.03), _theme(), _theme_intel(), "us", site)
    if kind == "mixed":
        return build_receipt(_base_basket(rel_20d=0.004), _theme(), _theme_intel(), "us", site)
    if kind == "unavailable-panel":
        return build_receipt(_b_rel(None), _theme(), _theme_intel(), "us", site)
    if kind == "unavailable-partial":
        b = _base_basket()
        b["observation"]["status"] = "partial"
        return build_receipt(b, _theme(), _theme_intel(), "us", site)
    if kind == "unavailable-eligible":
        b = _base_basket()
        b["observation"]["aggregate_eligible"] = False
        b["observation"]["min_members"] = 5
        return build_receipt(b, _theme(), _theme_intel(), "us", site)
    if kind == "unavailable-coverage":
        b = _base_basket()
        b["observation"]["coverage"] = 0.5
        b["observation"]["min_coverage"] = 0.6
        return build_receipt(b, _theme(), _theme_intel(), "us", site)
    if kind == "unavailable-error":
        return build_receipt({"perf": "x"}, {}, {}, "us", None)
    if kind == "not-published":
        return build_receipt(_base_basket(), _theme(), _theme_intel(), "china", site)
    if kind == "fresh-theme-state":
        _theme_state_file(site, as_of="2026-10-08")
        return build_receipt(
            _base_basket(), _theme(), _theme_intel(as_of="2026-10-10"), "us", site
        )
    if kind == "stale-theme-state":
        _theme_state_file(site, as_of="2026-10-01")
        return build_receipt(
            _base_basket(), _theme(), _theme_intel(as_of="2026-10-10"), "us", site
        )
    raise AssertionError(f"unknown receipt kind: {kind}")


RECEIPT_KINDS = [
    "leading",
    "lagging",
    "mixed",
    "unavailable-panel",
    "unavailable-partial",
    "unavailable-eligible",
    "unavailable-coverage",
    "unavailable-error",
    "not-published",
    "fresh-theme-state",
    "stale-theme-state",
]


# ---------------------------------------------------------------------------
# 1. Dead-band edges.
# ---------------------------------------------------------------------------


class TestDeadBand:
    @pytest.mark.parametrize(
        ("rel", "expected"),
        [
            pytest.param(0.01, "leading", id="plus-band-edge-inclusive"),
            pytest.param(-0.01, "lagging", id="minus-band-edge-inclusive"),
            pytest.param(0.0100001, "leading", id="just-above-band"),
            pytest.param(-0.0100001, "lagging", id="just-below-band"),
            pytest.param(0.0, "mixed", id="zero"),
            pytest.param(0.0099999, "mixed", id="just-inside-band-plus"),
            pytest.param(-0.0099999, "mixed", id="just-inside-band-minus"),
        ],
    )
    def test_state_from_rel_band_edges(self, rel, expected):
        """Both dead-band edges are INCLUSIVE toward the directional state:
        the comparison is rel >= +0.01 for "leading" and rel <= -0.01 for
        "lagging", so exactly ±0.01 is directional, not mixed."""
        assert _DEAD_BAND == 0.01
        assert _state_from_rel(rel) == expected


# ---------------------------------------------------------------------------
# 2. Theme-state freshness.
# ---------------------------------------------------------------------------


class TestThemeStateFreshness:
    TI_AS_OF = "2026-10-07"

    def _receipt(self, tmp_path: Path, ts_as_of: str, **kw) -> dict:
        site = tmp_path / "site"
        _theme_state_file(site, as_of=ts_as_of, **kw)
        return build_receipt(
            _base_basket(), _theme(), _theme_intel(as_of=self.TI_AS_OF), "us", site
        )

    def test_exactly_5_days_old_is_fresh(self, tmp_path: Path):
        """Stale requires days > 5 (strictly): a theme state exactly 5 days
        older than the theme-intel as_of is still fresh."""
        assert _THEME_STATE_MAX_AGE_DAYS == 5
        assert (date(2026, 10, 7) - date(2026, 10, 2)).days == 5
        r = self._receipt(tmp_path, "2026-10-02", stale_legs=["us_10y", "copper"])
        assert r["theme_state"]["status"] == "fresh"
        assert r["theme_state"]["as_of"] == "2026-10-02"
        assert r["theme_state"]["stale_legs_n"] == 2
        assert r["theme_state"]["quadrant"] == "leading"

    def test_6_days_old_is_stale(self, tmp_path: Path):
        assert (date(2026, 10, 7) - date(2026, 10, 1)).days == 6
        r = self._receipt(tmp_path, "2026-10-01")
        assert r["theme_state"]["status"] == "stale"

    def test_stale_copy_follows_max_age_constant(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """The stale freshness row names _THEME_STATE_MAX_AGE_DAYS, so the
        copy tracks the gate: at 7 an 8-day-old state is stale and the prose
        says 7 days; at the production value 5 the rendered text is
        byte-identical to the base commit's hardcoded copy."""
        monkeypatch.setattr(lr_mod, "_THEME_STATE_MAX_AGE_DAYS", 7)
        assert (date(2026, 10, 7) - date(2026, 9, 29)).days == 8
        r = self._receipt(tmp_path, "2026-09-29")
        assert r["theme_state"]["status"] == "stale"
        row = next(row for row in r["rows"] if row["key"] == "freshness")
        assert "more than 7 days old" in row["text_en"]
        assert "超过7天" in row["text_zh"]

        monkeypatch.setattr(lr_mod, "_THEME_STATE_MAX_AGE_DAYS", _THEME_STATE_MAX_AGE_DAYS)
        assert (date(2026, 10, 7) - date(2026, 10, 1)).days == 6
        r5 = self._receipt(tmp_path, "2026-10-01")
        assert r5["theme_state"]["status"] == "stale"
        row5 = next(row for row in r5["rows"] if row["key"] == "freshness")
        assert row5["text_en"] == (
            "Theme state as of 2026-10-01 — more than 5 days old; read with care."
        )
        assert row5["text_zh"] == "主题状态截至2026-10-01——超过5天；请谨慎阅读。"

    def test_future_theme_state_as_of_is_invalid(self, tmp_path: Path):
        """A theme-state as_of AFTER the theme-intel as_of gives negative
        (ti - ts).days and now reads "invalid" — never "fresh"."""
        assert (date(2026, 10, 7) - date(2026, 10, 12)).days == -5
        r = self._receipt(tmp_path, "2026-10-12")
        assert r["theme_state"]["status"] == "invalid"

    def test_future_theme_state_as_of_should_not_read_fresh(self, tmp_path: Path):
        """The #8967 strict xfail, flipped: a future-dated theme_state
        must not read fresh (it reads invalid)."""
        r = self._receipt(tmp_path, "2026-10-12")
        assert r["theme_state"]["status"] != "fresh"
        assert r["theme_state"]["status"] == "invalid"

    def test_future_dated_theme_state_is_invalid(self, tmp_path: Path):
        """A theme_state as_of at least one calendar day after the read is
        "invalid" (1 day and 5 days ahead alike), and the freshness row
        carries plain-word invalid copy in EN and ZH naming the date."""
        r1 = self._receipt(tmp_path, "2026-10-08")  # 1 day ahead of TI
        assert r1["theme_state"]["status"] == "invalid"
        r5 = self._receipt(tmp_path, "2026-10-12")  # 5 days ahead of TI
        assert r5["theme_state"]["status"] == "invalid"
        row = next(row for row in r5["rows"] if row["key"] == "freshness")
        assert "2026-10-12" in row["text_en"]
        assert "after this read" in row["text_en"]
        assert "unreliable" in row["text_en"]
        assert "2026-10-12" in row["text_zh"]
        assert "晚于本次判读" in row["text_zh"]
        assert "谨慎看待" in row["text_zh"]

    def test_same_day_theme_state_is_fresh(self, tmp_path: Path):
        """The invalid branch needs at least one full calendar day: a
        same-day theme_state is fresh. The pre-existing stale boundary is
        unchanged — 5 days old is fresh, 6 is stale."""
        r0 = self._receipt(tmp_path, "2026-10-07")  # same day as TI
        assert r0["theme_state"]["status"] == "fresh"
        r5 = self._receipt(tmp_path, "2026-10-02")  # exactly 5 days old
        assert r5["theme_state"]["status"] == "fresh"
        r6 = self._receipt(tmp_path, "2026-10-01")  # 6 days old
        assert r6["theme_state"]["status"] == "stale"

    def test_missing_when_theme_state_as_of_unparseable(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site, as_of="not-a-date")
        r = build_receipt(
            _base_basket(), _theme(), _theme_intel(as_of="2026-10-07"), "us", site
        )
        assert r["theme_state"]["status"] == "missing"
        assert r["theme_state"]["as_of"] is None

    def test_missing_when_theme_intel_as_of_absent(self, tmp_path: Path):
        """Either missing date -> "missing"; the receipt itself is unaffected
        (as_of falls back to observation.effective_as_of)."""
        site = tmp_path / "site"
        _theme_state_file(site, as_of="2026-10-02")
        r = build_receipt(
            _base_basket(), _theme(), _theme_intel(as_of=None), "us", site
        )
        assert r["theme_state"]["status"] == "missing"
        assert r["theme_state"]["as_of"] == "2026-10-02"
        assert r["state"] == "leading"


# ---------------------------------------------------------------------------
# 3. _parse_date.
# ---------------------------------------------------------------------------


class TestParseDate:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(None, None, id="none"),
            pytest.param(20261012, None, id="int-falls-through"),
            pytest.param("not-a-date", None, id="garbage-string"),
            pytest.param("", None, id="empty-string"),
            pytest.param(
                "2026-10-12T07:00:00Z",
                date(2026, 10, 12),
                id="datetime-string-sliced-to-10",
            ),
            pytest.param(date(2026, 10, 12), date(2026, 10, 12), id="date-object"),
            pytest.param(
                datetime(2026, 10, 12, 7, 30),
                date(2026, 10, 12),
                id="datetime-object-date-taken",
            ),
        ],
    )
    def test_parse_date_matrix(self, value, expected):
        """A datetime STRING parses (only value[:10] is handed to
        date.fromisoformat); a datetime OBJECT parses to its local date via
        the datetime-first isinstance branch."""
        assert _parse_date(value) == expected

    def test_parse_date_datetime_object_parses(self):
        """The #8967 strict xfail, flipped: a datetime object no longer
        silently loses its date."""
        assert _parse_date(datetime(2026, 10, 12, 7, 30)) == date(2026, 10, 12)

    @pytest.mark.parametrize(
        "dt",
        [
            pytest.param(datetime(2026, 10, 12, 7, 30), id="naive"),
            pytest.param(
                datetime(2026, 10, 12, 7, 30, tzinfo=timezone.utc), id="utc-aware"
            ),
            pytest.param(
                datetime(2026, 10, 12, 23, 30, tzinfo=timezone(timedelta(hours=8))),
                id="utc-plus-8-at-2330",
            ),
            pytest.param(
                datetime(2026, 10, 12, 3, 0, tzinfo=timezone(timedelta(hours=8))),
                id="utc-plus-8-at-0300-local-and-utc-dates-differ",
            ),
        ],
    )
    def test_datetime_object_as_of_parses(self, tmp_path: Path, dt):
        """_parse_date(dt) == _parse_date(dt.isoformat()) for naive and
        tz-aware datetimes: the LOCAL date wins (no UTC normalization). The
        03:00 UTC+08:00 case is the one a UTC-normalizing implementation
        gets wrong (its UTC date is 2026-10-11); 23:30 UTC+08:00 is the
        same-date control. build_receipt reads the same theme_state status
        for a datetime-object theme_intel as_of as for the isoformat string."""
        assert _parse_date(dt) == _parse_date(dt.isoformat())
        assert _parse_date(dt) == dt.date()
        site = tmp_path / "site"
        _theme_state_file(site, as_of="2026-10-05")
        r_obj = build_receipt(
            _base_basket(), _theme(), _theme_intel(as_of=dt), "us", site
        )
        r_str = build_receipt(
            _base_basket(),
            _theme(),
            _theme_intel(as_of=dt.isoformat()),
            "us",
            site,
        )
        assert r_obj["theme_state"]["status"] == r_str["theme_state"]["status"]
        assert r_obj["theme_state"]["status"] == "stale"


# ---------------------------------------------------------------------------
# 4. _roster_changed.
# ---------------------------------------------------------------------------


class TestRosterChanged:
    @pytest.mark.parametrize(
        ("basket", "expected"),
        [
            pytest.param(
                {"members": [{"added": "2020-02-01"}]}, False, id="no-created"
            ),
            pytest.param({"created": "2020-01-01"}, False, id="created-no-members"),
            pytest.param(
                {"created": "2020-01-01", "members": []},
                False,
                id="created-empty-members",
            ),
            pytest.param(
                {"created": "2020-01-01", "members": [{"added": "2019-06-01"}]},
                False,
                id="added-before-created",
            ),
            pytest.param(
                {"created": "2020-01-01", "members": [{"added": "2020-01-01"}]},
                False,
                id="added-on-created-not-strictly-after",
            ),
            pytest.param(
                {"created": "2020-01-01", "members": [{"added": "2020-02-01"}]},
                True,
                id="added-after-created",
            ),
            pytest.param(
                {
                    "created": "2020-01-01",
                    "members": [{"added": "2019-06-01", "curated_added": "2020-02-01"}],
                },
                True,
                id="curated-added-after-wins",
            ),
            pytest.param(
                {
                    "created": "2020-01-01",
                    "members": [{"added": "2020-02-01", "curated_added": "2019-06-01"}],
                },
                False,
                id="curated-added-before-overrides-added",
            ),
            pytest.param(
                {
                    "created": "2020-01-01",
                    "members": [{"added": "2020-02-01", "curated_added": None}],
                },
                True,
                id="falsy-curated-falls-back-to-added",
            ),
            pytest.param(
                {"created": "2020-01-01", "members": [{"added": "garbage"}]},
                False,
                id="malformed-added-skipped",
            ),
            pytest.param(
                {"created": "garbage", "members": [{"added": "2030-01-01"}]},
                False,
                id="malformed-created-short-circuits",
            ),
            pytest.param(
                {"created": "2020-01-01", "members": ["AAA", 5, None]},
                False,
                id="non-dict-members-skipped",
            ),
            pytest.param(
                {"created": "2020-01-01", "members": [{"added": "2020-02-01"}, "junk"]},
                True,
                id="non-dict-ignored-when-another-member-matches",
            ),
        ],
    )
    def test_roster_changed_matrix(self, basket, expected):
        """True only when a member's curated_added (else added) date parses
        and is STRICTLY after the basket created date; added == created does
        not count, and unparseable dates / non-dict members are skipped."""
        assert _roster_changed(basket) == expected

    def test_roster_changed_public_path(self, tmp_path: Path):
        b = _base_basket()
        b["members"] = [{"ticker": "AAA", "added": "2020-02-01"}]
        r = build_receipt(b, _theme(), _theme_intel(), "us", tmp_path)
        assert r["roster_changed"] is True

    def test_roster_changed_false_on_unavailable_receipt(self, tmp_path: Path):
        """The unavailable receipt hardcodes roster_changed=False and the
        reason path never recomputes it, even when a member was added after
        the created date."""
        b = _base_basket()
        b["members"] = [{"ticker": "AAA", "added": "2020-02-01"}]
        b["perf"]["20d"] = {"rel": None}
        r = build_receipt(b, _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "unavailable"
        assert r["roster_changed"] is False


# ---------------------------------------------------------------------------
# 5. Window sessions.
# ---------------------------------------------------------------------------


class TestWindowSessions:
    def test_window_sessions_constant(self):
        assert _WINDOW_SESSIONS == 20

    def test_fewer_sessions_than_window_reports_nominal_window(self, tmp_path: Path):
        """The receipt carries no observed-session-count field: when the
        panel cannot produce a 20-session rel at all (rel_20d None ->
        "price panel incomplete"), window_sessions still reports the nominal
        20 and the six-row layout is unchanged."""
        b = _base_basket()
        b["perf"]["20d"] = {"rel": None}
        b["observation"]["status"] = "partial"
        b["observation"]["effective_as_of"] = "2026-09-20"  # ~8 sessions in
        r = build_receipt(b, _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "unavailable"
        assert r["reason_en"] == "price panel incomplete"
        assert r["window_sessions"] == 20
        assert [row["key"] for row in r["rows"]] == ROW_KEYS

    def test_available_receipt_also_reports_nominal_window(self, tmp_path: Path):
        r = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == "leading"
        assert r["window_sessions"] == 20


# ---------------------------------------------------------------------------
# 6. Never-raises table.
# ---------------------------------------------------------------------------


def _never_raise_args(case: str):
    b = _base_basket()
    if case == "basket_none":
        return None, _theme(), _theme_intel(), "us", None
    if case == "theme_none":
        return b, None, _theme_intel(), "us", None
    if case == "theme_intel_none":
        return b, _theme(), None, "us", None
    if case == "region_none":
        return b, _theme(), _theme_intel(), None, None
    if case == "site_none":
        return b, _theme(), _theme_intel(), "us", None
    if case == "basket_empty":
        return {}, _theme(), _theme_intel(), "us", None
    if case == "theme_empty":
        return b, {}, _theme_intel(), "us", None
    if case == "theme_intel_empty":
        return b, _theme(), {}, "us", None
    if case == "basket_list":
        return [], _theme(), _theme_intel(), "us", None
    if case == "basket_str":
        return "x", _theme(), _theme_intel(), "us", None
    if case == "theme_list":
        return b, [], _theme_intel(), "us", None
    if case == "theme_intel_list":
        return b, _theme(), [], "us", None
    if case == "theme_intel_str":
        return b, _theme(), "x", "us", None
    if case == "observation_str":
        b["observation"] = "oops"
        return b, _theme(), _theme_intel(), "us", None
    if case == "perf_empty_list":
        b["perf"] = []
        return b, _theme(), _theme_intel(), "us", None
    if case == "members_not_dicts":
        b["members"] = ["AAA", 5, None]
        return b, _theme(), _theme_intel(), "us", None
    if case == "members_dict":
        b["members"] = {"AAA": {"added": "2099-01-01"}}
        return b, _theme(), _theme_intel(), "us", None
    if case == "rel_20d_nan":
        return _b_rel(float("nan")), _theme(), _theme_intel(), "us", None
    if case == "rel_20d_inf":
        return _b_rel(float("inf")), _theme(), _theme_intel(), "us", None
    if case == "rel_20d_neg_inf":
        return _b_rel(float("-inf")), _theme(), _theme_intel(), "us", None
    if case == "rel_20d_str":
        return _b_rel("0.02"), _theme(), _theme_intel(), "us", None
    raise AssertionError(f"unknown never-raise case: {case}")


class TestNeverRaises:
    @pytest.mark.parametrize(
        ("case", "unavailable"),
        [
            pytest.param("basket_none", True, id="basket-none"),
            pytest.param("theme_none", True, id="theme-none"),
            pytest.param("theme_intel_none", True, id="theme-intel-none"),
            pytest.param("region_none", False, id="region-none"),
            pytest.param("site_none", False, id="site-none"),
            pytest.param("basket_empty", True, id="basket-empty-dict"),
            pytest.param("theme_empty", False, id="theme-empty-dict"),
            pytest.param("theme_intel_empty", False, id="theme-intel-empty-dict"),
            pytest.param("basket_list", True, id="basket-list"),
            pytest.param("basket_str", True, id="basket-str"),
            pytest.param("theme_list", True, id="theme-list"),
            pytest.param("theme_intel_list", True, id="theme-intel-list"),
            pytest.param("theme_intel_str", True, id="theme-intel-str"),
            pytest.param("observation_str", True, id="observation-str"),
            pytest.param("perf_empty_list", True, id="perf-empty-list"),
            pytest.param("members_not_dicts", False, id="members-not-dicts"),
            pytest.param("members_dict", False, id="members-dict"),
            pytest.param("rel_20d_nan", False, id="rel-20d-nan"),
            pytest.param("rel_20d_inf", False, id="rel-20d-inf"),
            pytest.param("rel_20d_neg_inf", False, id="rel-20d-neg-inf"),
            pytest.param("rel_20d_str", False, id="rel-20d-str"),
        ],
    )
    def test_never_raises_table(self, tmp_path: Path, case, unavailable):
        """build_receipt is documented "Pure, fail-soft; never raises": every
        malformed input below returns a v1 dict; the clearly malformed ones
        return the unavailable receipt with a non-empty reason."""
        r = build_receipt(*_never_raise_args(case))
        assert isinstance(r, dict)
        assert r["schema"] == "mi.leadership_receipt.v1"
        if unavailable:
            assert r["state"] == "unavailable"
            assert isinstance(r["reason_en"], str) and r["reason_en"]
        else:
            assert r["state"] in {"leading", "lagging", "mixed"}

    def test_never_raise_table_pinned_details(self, tmp_path: Path):
        r = build_receipt(*_never_raise_args("region_none"))
        assert r["theme_state"]["status"] == "not_published"
        r = build_receipt(*_never_raise_args("site_none"))
        assert r["theme_state"]["status"] == "missing"
        r = build_receipt(*_never_raise_args("theme_intel_empty"))
        assert r["benchmark"] == {"label": "S&P 500", "label_zh": "标普500"}
        r = build_receipt(*_never_raise_args("members_not_dicts"))
        assert r["state"] == "leading"
        assert r["roster_changed"] is False
        r = build_receipt(*_never_raise_args("basket_empty"))
        assert r["reason_en"] == "price panel incomplete"

    @pytest.mark.parametrize(
        ("rel", "expected_state"),
        [
            pytest.param(
                float("nan"), "mixed", id="nan-fails-both-directional-comparisons"
            ),
            pytest.param(float("inf"), "leading", id="inf-is-leading"),
            pytest.param(float("-inf"), "lagging", id="-inf-is-lagging"),
            pytest.param("0.02", "leading", id="numeric-string-coerced-by-float"),
        ],
    )
    def test_non_finite_and_string_rels(self, tmp_path: Path, rel, expected_state):
        """NaN fails both band comparisons and lands "mixed"; infinities take
        the directional states; a numeric STRING rel is coerced by float()."""
        r = build_receipt(_b_rel(rel), _theme(), _theme_intel(), "us", tmp_path)
        assert r["state"] == expected_state
        assert isinstance(r["rel_20d"], float)


# ---------------------------------------------------------------------------
# 7. Key-set stability.
# ---------------------------------------------------------------------------


class TestKeySetStability:
    def test_available_unavailable_and_error_share_key_set(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site)
        r_ok = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", site)
        r_reason = build_receipt(_b_rel(None), _theme(), _theme_intel(), "us", site)
        r_error = build_receipt({"perf": "x"}, {}, {}, "us", None)
        assert r_ok["state"] == "leading"
        assert r_reason["state"] == "unavailable"
        assert r_error["state"] == "unavailable"
        assert set(r_ok) == set(r_reason) == set(r_error) == SCHEMA_KEYS


# ---------------------------------------------------------------------------
# 8. EN/ZH sibling parity.
# ---------------------------------------------------------------------------


def _iter_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_dicts(v)


class TestBilingualParity:
    @pytest.mark.parametrize("kind", RECEIPT_KINDS)
    def test_every_en_string_has_nonempty_zh_sibling(self, tmp_path: Path, kind):
        """Walk the whole receipt: every *_en field that carries a non-empty
        string must have a non-empty *_zh sibling, on available and
        unavailable shapes alike."""
        rec = _receipt_by_kind(kind, tmp_path)
        seen = 0
        for d in _iter_dicts(rec):
            for k, v in d.items():
                if isinstance(k, str) and k.endswith("_en") and isinstance(v, str) and v.strip():
                    zh = d.get(k[:-3] + "_zh")
                    assert isinstance(zh, str) and zh.strip(), (kind, k, zh)
                    seen += 1
        # stance (1) + six rows x (label + text) (12) at minimum everywhere.
        assert seen >= 13, (kind, seen)

    @pytest.mark.parametrize("kind", RECEIPT_KINDS)
    def test_benchmark_label_pair(self, tmp_path: Path, kind):
        """benchmark.label / benchmark.label_zh are the one unsuffixed EN/ZH
        copy pair; both must be non-empty on every shape."""
        rec = _receipt_by_kind(kind, tmp_path)
        bench = rec["benchmark"]
        assert isinstance(bench["label"], str) and bench["label"].strip()
        assert isinstance(bench["label_zh"], str) and bench["label_zh"].strip()


# ---------------------------------------------------------------------------
# 9. Determinism.
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_json_bytes_stable_across_calls_and_deepcopy(self, tmp_path: Path):
        site = tmp_path / "site"
        _theme_state_file(site)
        basket, theme, ti = _base_basket(), _theme(), _theme_intel()
        r1 = build_receipt(basket, theme, ti, "us", site)
        r2 = build_receipt(basket, theme, ti, "us", site)
        r3 = build_receipt(
            copy.deepcopy(basket), copy.deepcopy(theme), copy.deepcopy(ti), "us", site
        )
        dumps = lambda r: json.dumps(r, sort_keys=True, ensure_ascii=False)
        assert dumps(r1) == dumps(r2)
        assert dumps(r1) == dumps(r3)

    def test_unavailable_receipt_deterministic(self, tmp_path: Path):
        b = _b_rel(None)
        j1 = json.dumps(
            build_receipt(b, _theme(), _theme_intel(), "us", tmp_path),
            sort_keys=True,
            ensure_ascii=False,
        )
        j2 = json.dumps(
            build_receipt(b, _theme(), _theme_intel(), "us", tmp_path),
            sort_keys=True,
            ensure_ascii=False,
        )
        assert j1 == j2


# ---------------------------------------------------------------------------
# 10. Banned vocabulary.
# ---------------------------------------------------------------------------


def _all_strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                yield k
            yield from _all_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_strings(v)
    elif isinstance(obj, str):
        yield obj


class TestBannedWords:
    @pytest.mark.parametrize("kind", RECEIPT_KINDS)
    def test_no_banned_words_in_any_returned_string(self, tmp_path: Path, kind):
        """No string the receipt returns (keys or values, at any depth) may
        contain the banned EN whole words or ZH terms."""
        for s in _all_strings(_receipt_by_kind(kind, tmp_path)):
            assert not _BANNED_EN.search(s), (kind, s)
            for term in _BANNED_ZH:
                assert term not in s, (kind, s)

    def test_banned_regex_positive_control(self):
        assert _BANNED_EN.search("a score of 3")
        assert _BANNED_EN.search("high confidence")
        assert _BANNED_EN.search("validated read")
        assert _BANNED_EN.search("Buy now")
        assert _BANNED_EN.search("sell signal")
        assert not _BANNED_EN.search("rebalanced monthly")
        assert "置信" in "置信度"


# ---------------------------------------------------------------------------
# 11. Breadth label ZH.
# ---------------------------------------------------------------------------


class TestBreadthZh:
    @pytest.mark.parametrize(
        ("label", "expect"),
        [
            pytest.param("broad", "广泛", id="producer-broad"),
            pytest.param("narrow", "狭窄", id="producer-narrow"),
            pytest.param(None, None, id="producer-none"),
            pytest.param("mystery", None, id="unknown-not-echoed"),
        ],
    )
    def test_breadth_has_zh(self, tmp_path: Path, label, expect):
        """breadth.label_zh carries plain-word ZH for every producer value
        (engine/group_flow.py _leadership emits only broad / narrow / None):
        non-empty, contains CJK, contains no ASCII letters. None and any
        unknown value give label_zh None — a raw English slug is never
        echoed into the ZH field."""
        theme = _theme()
        theme["leadership"]["breadth"] = label
        r = build_receipt(_base_basket(), theme, _theme_intel(), "us", tmp_path / "site")
        assert r["state"] == "leading"
        assert r["breadth"]["label"] == label
        assert r["breadth"]["label_zh"] == expect
        if expect is not None:
            assert expect.strip()
            assert _CJK.search(expect)
            assert not re.search(r"[A-Za-z]", expect)

    def test_breadth_key_set_available_and_unavailable(self, tmp_path: Path):
        """Available and unavailable receipts carry the same breadth key
        set (label_zh included); the unavailable one is all-None."""
        site = tmp_path / "site"
        r_ok = build_receipt(_base_basket(), _theme(), _theme_intel(), "us", site)
        b = _base_basket()
        b["perf"]["20d"] = {"rel": None}
        r_bad = build_receipt(b, _theme(), _theme_intel(), "us", site)
        assert r_ok["state"] == "leading"
        assert r_bad["state"] == "unavailable"
        assert set(r_ok["breadth"]) == set(r_bad["breadth"])
        assert r_bad["breadth"] == {
            "pct50": None,
            "pct200": None,
            "n": None,
            "label": None,
            "label_zh": None,
        }
