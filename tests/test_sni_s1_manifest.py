"""test_sni_s1_manifest.py — grid spacing (h+1), purge, quarantine, canonical
bytes, and the index-only loader spy (D5)."""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

from s1_data import IndexOnlySpy  # noqa: E402  # noqa: E402
from s1_manifest import (build_rows, canonical_line,  # noqa: E402
                         episode_key_for, first_anchor, label_unit, manifest_bytes,
                         session_n_forward, split_digests, time_split)
from s1_synth import PATHS, sessions_us  # noqa: E402


def _store_for(dates):
    class S:
        def index_dates(self, path):
            return dates

        def schema(self, path):
            return ["close"]

        def list_dir(self, prefix):
            return []

        def frame(self, path, columns):  # pragma: no cover - must never be called
            raise AssertionError("manifest builder requested a price/volume column")

    return S()


def test_grid_spacing_is_h_plus_one_sessions():
    dates = sessions_us(1400)
    store = _store_for(dates)
    for h in (5, 21, 63):
        rows = build_rows("P01", "alibaba", "adr_baba", "SEC:US-XNYS-BABA", "US", h,
                          dates, dates[-1])
        anchors = [date.fromisoformat(r["anchor_session_date"]) for r in rows]
        assert anchors == sorted(anchors) and len(set(anchors)) == len(anchors)
        for a, b in zip(anchors, anchors[1:]):
            gap = session_n_forward(_is_us, a, h + 1)
            assert b == gap, (h, a, b, gap)   # h+1 sessions apart -> no shared endpoints


def _is_us(d):
    from lib import nyse_calendar
    return nyse_calendar.is_session(d)


def test_first_anchor_needs_252_bars_and_starts_at_the_bar_not_the_clock_floor():
    dates = sessions_us(400)
    s0 = first_anchor(_is_us, dates, date(2012, 10, 31))
    d_s = s0
    from s1_manifest import last_session_before
    d_s = last_session_before(_is_us, s0)
    assert sum(1 for x in dates if x <= d_s) >= 252
    prev = dates[251]  # the 252nd bar
    assert s0 > prev


def test_purge_and_quarantine_labels():
    assert time_split(date(2023, 12, 29)) == "TRAIN"
    assert time_split(date(2024, 1, 2)) == "TUNE"
    assert time_split(date(2026, 10, 1)) == "QUARANTINE"
    # TRAIN whose coverage reaches 2024 -> PURGED_TRAIN, never moved
    assert label_unit(date(2023, 12, 20), date(2024, 1, 3)) == "PURGED_TRAIN"
    assert label_unit(date(2023, 12, 20), date(2023, 12, 30)) == "TRAIN"
    # TUNE whose coverage reaches 2026-10-01 -> PURGED_TUNE
    assert label_unit(date(2026, 9, 4), date(2026, 10, 1)) == "PURGED_TUNE"
    assert label_unit(date(2026, 9, 4), date(2026, 9, 30)) == "TUNE"


def test_episode_key_formula():
    want = hashlib.sha256(
        b"alibaba|rolling_anchor|2024-03-04|adr_baba").hexdigest()
    assert episode_key_for("alibaba", date(2024, 3, 4), "adr_baba") == want


def test_manifest_bytes_are_canonical_and_sorted():
    dates = sessions_us(1400)
    rows = build_rows("P01", "alibaba", "adr_baba", "SEC:US-XNYS-BABA", "US", 5,
                      dates, dates[-1])
    raw = manifest_bytes(rows)
    lines = raw.decode("utf-8").splitlines()
    keys = [json.loads(l) for l in lines]
    assert keys == sorted(keys, key=lambda r: (r["horizon"], r["episode_key"]))
    for line, row in zip(lines, keys):
        assert line == json.dumps(row, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False)
    assert raw == manifest_bytes(list(reversed(rows)))  # order-independent bytes
    for row in keys:
        assert set(row) == {"protocol_id", "version", "horizon", "episode_key",
                            "issuer_key", "counter", "security_id", "unit",
                            "anchor_session_date", "coverage_date", "split"}
        assert row["version"] == "v1" and row["unit"] == "rolling_anchor"


def test_split_digests_are_sha_of_split_lines_in_order():
    dates = sessions_us(1400)
    rows = build_rows("P01", "alibaba", "adr_baba", "SEC:US-XNYS-BABA", "US", 5,
                      dates, dates[-1])
    ordered = sorted(rows, key=lambda r: (r["horizon"], r["episode_key"]))
    digests = split_digests(rows)
    for sp in ("TRAIN", "TUNE", "QUARANTINE", "PURGED_TRAIN", "PURGED_TUNE"):
        lines = [canonical_line(r) for r in ordered if r["split"] == sp]
        if not lines:
            assert sp not in digests
            continue
        assert digests[sp]["count"] == len(lines)
        assert digests[sp]["membership_sha256"] == \
            hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def test_builder_requests_no_non_index_column():
    dates = sessions_us(1400)
    spy = sessions_us(1400)
    frames = {PATHS["adr_baba"]: {"Date": dates, "close": [1.0] * len(dates)},
              PATHS["SPY"]: {"Date": spy, "close": [1.0] * len(spy)}}
    base = _store_for(dates)  # frame() raises if touched
    spy_store = _store_for(spy)
    spy_store.index_dates = lambda path: dates if "BABA" in path else spy
    wrapped = IndexOnlySpy(spy_store)
    rows = build_rows("P01", "alibaba", "adr_baba", "SEC:US-XNYS-BABA", "US", 21,
                      wrapped.index_dates(PATHS["adr_baba"]), dates[-1])
    assert rows and set(wrapped.calls) <= {"schema", "index_dates"}
    assert wrapped.calls.count("index_dates") >= 1


def test_hk_pre_floor_anchors_abstain_in_the_manifest():
    """0700-like history: bars well before the HK clock floor enter the grid and
    are listed ABSTAIN_RESOLVER_NONE, never silently skipped."""
    from datetime import timedelta

    from lib import hk_calendar

    cur, out = date(2004, 6, 16), []
    while len(out) < 5600:                    # 2004 -> past the 2014 clock floor
        if hk_calendar.is_session(cur):
            out.append(cur)
        cur += timedelta(days=1)
    rows = build_rows("P02", "tencent", "hkd_0700", "SEC:HK-XHKG-00700", "HK", 5,
                      out, out[-1])
    abstain = [r for r in rows if r["split"] == "ABSTAIN_RESOLVER_NONE"]
    live = [r for r in rows if r["split"] in ("TRAIN", "TUNE", "QUARANTINE",
                                              "PURGED_TRAIN", "PURGED_TUNE")]
    assert abstain, "pre-floor anchors must be listed"
    assert all(r["coverage_date"] is None for r in abstain)
    assert live and all(r["coverage_date"] for r in live)
    first_live = date.fromisoformat(live[0]["anchor_session_date"])
    assert first_live >= date(2014, 1, 1)
