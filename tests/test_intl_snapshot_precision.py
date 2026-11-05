"""INTL-GS X5: the snapshot bar must not LOSE the declared source precision.

The native adapter declares one precision per clock (exact | upper_bound |
session_date) and supplies it correctly. The mount used to keep only the
instant, and the display printed every instant as if it were exact: a
session date came out as "2 Nov 00:00 UTC" and a publication bound came out
as an unqualified exact stamp.

These are the focused tests for that one loss, end to end over the native
modules: the mount carries the precision, the display names it, the macro
shows it, and no path invents a time the source never declared. The
qualification law itself (who is qualified, which value, which arithmetic)
is untouched and is not re-audited here.
"""
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from lib.intl_gs_display import snapshot_display  # noqa: E402
from lib.intl_surveillance_mount import _snapshot_clocks  # noqa: E402

CLOCKS = ("observation", "source_publication", "ingestion", "computation")


# ------------------------------------------------------------ small fixtures

def _clocks(observation=("2026-11-02T00:00:00Z", "session_date"),
            source=("2026-11-03T09:30:00Z", "upper_bound"),
            ingestion=("2026-11-03T09:31:00Z", "exact"),
            computation=("2026-11-03T10:00:00Z", "exact")):
    """One four-clock moment set: four DIFFERENT instants, so a copied or a
    fabricated timestamp cannot pass unnoticed."""
    return {name: {"at": at, "precision": precision}
            for name, (at, precision) in (
                ("observation", observation), ("source_publication", source),
                ("ingestion", ingestion), ("computation", computation))}


def _entry(clocks, state="qualified"):
    entry = {"state": state, "clocks": clocks}
    if state == "abstain":
        entry["abstain_reasons"] = ["clock_missing"]
    return entry


def _observations(bases):
    return {"contract_version": "intl-global-observation-v1", "status": "admitted",
            "source_reference": "intl-supplied-close:sha256:abc", "bases": bases}


def _compose(observations):
    """The production composition path: the mount's projection, then the one
    display path (lib.intl_gs_display.snapshot_display)."""
    return snapshot_display(_snapshot_clocks(observations))


class _Scan(HTMLParser):
    """Visible text nodes and attribute pairs, kept apart."""

    def __init__(self):
        super().__init__()
        self.text = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is not None:
                self.attrs.append((name, value))

    def handle_data(self, data):
        self.text.append(data)


def _render(snapshot, basis="local"):
    from jinja2 import Environment, FileSystemLoader
    from engine import i18n
    env = Environment(loader=FileSystemLoader(str(REPO / "templates")), autoescape=False)
    env.globals.update(t=i18n.t, tr=i18n.tr, td=i18n.td)
    horizon = {"id": "1m", "en": "1M", "zh": "1月"}
    return env.from_string(
        '{% import "intl_workspace/_gs_macros.html.j2" as gs %}'
        '{{ gs.gs_snapshot(snapshot, basis, horizon) }}').render(
            snapshot=snapshot, basis=basis, horizon=horizon)


def _visible(html):
    scan = _Scan()
    scan.feed(html)
    return scan, " ".join(scan.text)


# ------------------------------------------------- the precision is carried

def test_the_mount_always_emits_its_precision_map():
    snapshot = _compose(None)
    assert set(snapshot["local"]) == {"clocks", "clock_precisions", "clock_display",
                                      "qualified", "total"}
    for basis in ("local", "usd_unhedged", "usd_hedged"):
        assert set(snapshot[basis]["clock_precisions"]) == set(CLOCKS)
        assert snapshot[basis]["clock_precisions"] == {clock: None for clock in CLOCKS}


def test_the_selected_precision_travels_with_its_instant():
    snapshot = _compose(_observations({"local": [_entry(_clocks())]}))
    assert snapshot["local"]["clock_precisions"] == {
        "observation": "session_date", "source_publication": "upper_bound",
        "ingestion": "exact", "computation": "exact"}


def test_raw_clocks_and_counts_are_untouched_by_the_precision_carry():
    snapshot = _compose(_observations({"local": [_entry(_clocks())]}))
    assert snapshot["local"]["clocks"] == {
        "observation": "2026-11-02T00:00:00Z",
        "source_publication": "2026-11-03T09:30:00Z",
        "ingestion": "2026-11-03T09:31:00Z",
        "computation": "2026-11-03T10:00:00Z"}
    assert snapshot["local"]["qualified"] == 1 and snapshot["local"]["total"] == 1


def test_an_abstained_observation_supplies_neither_a_clock_nor_a_precision():
    payload = _observations({"local": [
        _entry(_clocks()),
        _entry(_clocks(observation=("2026-12-31T00:00:00Z", "exact")),
               state="abstain")]})
    snapshot = _compose(payload)
    assert snapshot["local"]["qualified"] == 1 and snapshot["local"]["total"] == 2
    assert snapshot["local"]["clocks"]["observation"] == "2026-11-02T00:00:00Z"
    assert snapshot["local"]["clock_precisions"]["observation"] == "session_date"
    assert snapshot["local"]["clock_display"]["observation"]["en"] == "2 Nov 2026"


def test_a_tie_never_upgrades_precision():
    exact_and_session = _observations({"local": [
        _entry(_clocks(observation=("2026-11-02T00:00:00Z", "exact"))),
        _entry(_clocks(observation=("2026-11-02T00:00:00Z", "session_date")))]})
    snapshot = _compose(exact_and_session)
    assert snapshot["local"]["clocks"]["observation"] == "2026-11-02T00:00:00Z"
    assert snapshot["local"]["clock_precisions"]["observation"] == "session_date"
    assert snapshot["local"]["clock_display"]["observation"]["en"] == "2 Nov 2026"

    exact_and_bound = _observations({"local": [
        _entry(_clocks(source=("2026-11-03T09:30:00Z", "exact"))),
        _entry(_clocks(source=("2026-11-03T09:30:00Z", "upper_bound")))]})
    snapshot = _compose(exact_and_bound)
    assert snapshot["local"]["clock_precisions"]["source_publication"] == "upper_bound"
    assert snapshot["local"]["clock_display"]["source_publication"]["en"] \
        == "Available by 3 Nov 09:30 UTC"


# ------------------------------------------------- the precision is named

def test_a_session_date_shows_the_calendar_date_and_invents_no_time():
    snapshot = _compose(_observations({"local": [_entry(_clocks())]}))
    cell = snapshot["local"]["clock_display"]["observation"]
    assert cell["en"] == "2 Nov 2026"
    assert cell["zh"] == "2026年11月2日"
    assert "00:00" not in cell["en"] and "00:00" not in cell["zh"]
    # the raw machine clock is preserved separately from the visible value
    assert cell["datetime"] == "2026-11-02T00:00:00Z"


def test_an_upper_bound_is_named_as_a_bound_and_an_exact_instant_is_not():
    bound = _compose(_observations({"local": [
        _entry(_clocks(source=("2026-11-03T09:30:00Z", "upper_bound")))]}))
    cell = bound["local"]["clock_display"]["source_publication"]
    assert cell["en"] == "Available by 3 Nov 09:30 UTC"
    assert cell["zh"] == "至迟可得 11月3日 09:30 UTC"
    assert cell["datetime"] == "2026-11-03T09:30:00Z"

    exact = _compose(_observations({"local": [
        _entry(_clocks(source=("2026-11-03T09:30:00Z", "exact")))]}))
    cell = exact["local"]["clock_display"]["source_publication"]
    assert cell["en"] == "3 Nov 09:30 UTC"
    assert cell["zh"] == "11月3日 09:30 UTC"
    assert bound["local"]["clocks"]["source_publication"] \
        == exact["local"]["clocks"]["source_publication"]


def test_an_unknown_precision_is_closed_and_never_shown_as_exact():
    for precision in ("exactish", "EXACT", "", None):
        snapshot = _compose(_observations({"local": [
            _entry(_clocks(source=("2026-11-03T09:30:00Z", precision)))]}))
        assert snapshot["local"]["clock_precisions"]["source_publication"] is None
        cell = snapshot["local"]["clock_display"]["source_publication"]
        assert cell["en"] is None and cell["zh"] is None, precision
        html = _render(snapshot)
        assert "Precision not confirmed" in html and "精度未确认" in html
        assert "09:30" not in html, precision


# ------------------------------------------------- the macro shows it

def test_the_macro_renders_both_languages_without_an_invented_time():
    snapshot = _compose(_observations({"local": [_entry(_clocks())]}))
    scan, visible = _visible(_render(snapshot))
    assert "2 Nov 2026" in visible and "2026年11月2日" in visible
    assert "Available by 3 Nov 09:30 UTC" in visible
    assert "至迟可得 11月3日 09:30 UTC" in visible
    # each cell keeps its own instant — nothing is copied between clocks
    assert "3 Nov 09:31 UTC" in visible and "3 Nov 10:00 UTC" in visible
    # no invented time and no raw ISO-8601 in any visible text node
    assert "00:00" not in visible
    assert "2026-11-02T00:00:00Z" not in visible
    # the machine instant stays in the attribute
    assert ("datetime", "2026-11-02T00:00:00Z") in scan.attrs
    assert ("datetime", "2026-11-03T09:30:00Z") in scan.attrs


def test_the_macro_keeps_the_no_qualified_observation_copy_for_a_missing_cell():
    snapshot = _compose(_observations({"local": []}))
    scan, visible = _visible(_render(snapshot))
    assert "No qualified observation" in visible and "无合格观测" in visible
    assert "Precision not confirmed" not in visible


def test_a_snapshot_without_a_precision_map_keeps_the_legacy_display():
    legacy = {"local": {"clocks": {"observation": "2026-10-07",
                                    "source_publication": "2026-10-09T15:00:00+00:00",
                                    "ingestion": None, "computation": None},
                        "qualified": 1, "total": 1}}
    out = snapshot_display(legacy)
    assert out["local"]["clock_display"]["observation"] == {
        "datetime": "2026-10-07", "en": "7 Oct 2026", "zh": "2026年10月7日"}
    assert out["local"]["clock_display"]["source_publication"]["en"] == "9 Oct 15:00 UTC"
    assert out["local"]["clock_display"]["ingestion"] is None
    assert "clock_precisions" not in out["local"]


def test_mixed_session_date_and_bound_do_not_claim_a_known_day():
    # A bound and a day are different kinds of knowledge, not a total
    # precision order. Neither supplies the other's claim.
    snapshot = _compose(_observations({'local': [
        _entry(_clocks(source=('2026-11-03T00:00:00Z', 'session_date'))),
        _entry(_clocks(source=('2026-11-03T00:00:00Z', 'upper_bound')))]}))
    assert snapshot['local']['clock_precisions']['source_publication'] is None
    assert snapshot['local']['clock_display']['source_publication']['en'] is None


def test_tied_missing_precision_cannot_be_hidden_by_an_exact_peer():
    snapshot = _compose(_observations({'local': [
        _entry(_clocks(source=('2026-11-03T00:00:00Z', 'exact'))),
        _entry(_clocks(source=('2026-11-03T00:00:00Z', None)))]}))
    assert snapshot['local']['clock_precisions']['source_publication'] is None
    assert snapshot['local']['clock_display']['source_publication']['en'] is None
